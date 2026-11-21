"""Rules the registration office changes without a deployment.

Two different things get called "configuration" in a project like this, and
keeping them apart is the whole point of this module.

`config/settings.py` holds *deployment* configuration: database credentials,
an API key, a rate limit, where Redis lives. It changes when the software is
moved, and only a developer or a sysadmin touches it.

This module holds *policy*: how many computers one student may register,
whether a projector needs a gate pass to leave, the exact sentence a guard
reads when a computer is held. None of that is a technical question, none of
it is the same at two universities, and none of it should require an engineer
and a release. It lives in the database and is edited in the Registration
Office portal.

The registry below is code, and deliberately so - it declares *what* is
configurable, its type, its bounds and its default. The *values* are data. A
rule that is not in this registry cannot be set, which is what stops the
settings table turning into an unvalidated key-value dump.
"""

from django.conf import settings

from config import requestcache
from config.cache import derived

CACHE_KEY = "campus.rules.v1"


class Kind:
    BOOL = "BOOL"
    INT = "INT"
    TEXT = "TEXT"


class RuleSpec:
    """One configurable rule: what it is, what it may be, and what it starts as."""

    __slots__ = (
        "key",
        "kind",
        "default",
        "label",
        "help",
        "group",
        "minimum",
        "maximum",
        "public",
    )

    def __init__(
        self,
        key,
        kind,
        default,
        label,
        help="",
        group="general",
        minimum=None,
        maximum=None,
        public=False,
    ):
        self.key = key
        self.kind = kind
        self.default = default
        self.label = label
        self.help = help
        self.group = group
        self.minimum = minimum
        self.maximum = maximum
        # Public rules are readable without signing in, because the landing
        # page and the student form need them. Nothing operationally sensitive
        # may be marked public - see `public_rules()`.
        self.public = public

    def clean(self, value):
        """Coerce and bound-check a submitted value. Raises ValueError."""
        if self.kind == Kind.BOOL:
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in {"1", "true", "yes", "on"}:
                return True
            if text in {"0", "false", "no", "off"}:
                return False
            raise ValueError("Choose yes or no.")

        if self.kind == Kind.INT:
            try:
                number = int(str(value).strip())
            except (TypeError, ValueError):
                raise ValueError("Enter a whole number.")
            if self.minimum is not None and number < self.minimum:
                raise ValueError(f"Cannot be less than {self.minimum}.")
            if self.maximum is not None and number > self.maximum:
                raise ValueError(f"Cannot be more than {self.maximum}.")
            return number

        text = "" if value is None else str(value).strip()
        if self.maximum is not None and len(text) > self.maximum:
            raise ValueError(f"Keep this under {self.maximum} characters.")
        if self.minimum and len(text) < self.minimum:
            raise ValueError("This cannot be left empty.")
        return text

    def as_dict(self):
        return {
            "key": self.key,
            "kind": self.kind,
            "label": self.label,
            "help": self.help,
            "group": self.group,
            "default": self.default,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "public": self.public,
        }


GROUPS = {
    "branding": {
        "label": "Names and contact details",
        "blurb": "What the university is called, and who a student or a guard should contact.",
    },
    "gate": {
        "label": "Gate decisions",
        "blurb": "What stops a computer at a gate, and what the guard is told about it.",
    },
    "registration": {
        "label": "Student registration",
        "blurb": "The public form, and the checks that keep one student from registering another "
        "student's computer.",
    },
    "permit": {
        "label": "Gate passes",
        "blurb": "How long written permission to carry equipment can run for.",
    },
    "session": {
        "label": "Sessions",
        "blurb": "How long a signed-in console is left unattended before it locks itself.",
    },
}


_SPECS = [
    # ------------------------------------------------------------ branding
    RuleSpec(
        "branding.university_name",
        Kind.TEXT,
        "the university",
        "University name",
        "Used in every message sent to a student. Write it the way it should be read in a "
        "sentence, for example 'the University of Kigali'.",
        group="branding",
        maximum=120,
        public=True,
    ),
    RuleSpec(
        "branding.system_name",
        Kind.TEXT,
        "etracker",
        "System name",
        "Shown in the browser tab, on the landing page and above every sign-in form.",
        group="branding",
        maximum=60,
        public=True,
    ),
    RuleSpec(
        "branding.office_name",
        Kind.TEXT,
        "the registration office",
        "Registration office name",
        "Where a student is sent when something cannot be settled online.",
        group="branding",
        maximum=120,
        public=True,
    ),
    RuleSpec(
        "branding.support_email",
        Kind.TEXT,
        "",
        "Support email address",
        "Shown to students who cannot complete the form. Leave blank to hide it.",
        group="branding",
        maximum=254,
        public=True,
    ),
    RuleSpec(
        "branding.support_phone",
        Kind.TEXT,
        "",
        "Registration office telephone",
        "Leave blank to hide it.",
        group="branding",
        maximum=40,
        public=True,
    ),
    RuleSpec(
        "branding.security_phone",
        Kind.TEXT,
        "",
        "Security control telephone",
        "The number a student is given when they report a theft. This is the one number worth "
        "getting right - it is read by somebody whose laptop has just gone.",
        group="branding",
        maximum=40,
        public=True,
    ),
    # ---------------------------------------------------------------- gate
    RuleSpec(
        "gate.block_pending",
        Kind.BOOL,
        True,
        "Hold computers that are still awaiting approval",
        "On by default, and the reason self-registration is safe to leave open: a submission "
        "is a request, not a fact, until an officer has seen the machine.",
        group="gate",
    ),
    RuleSpec(
        "gate.block_suspended_owner",
        Kind.BOOL,
        True,
        "Hold equipment belonging to a suspended or withdrawn student",
        group="gate",
    ),
    RuleSpec(
        "gate.university_property_needs_pass",
        Kind.BOOL,
        True,
        "University property needs a gate pass to leave campus",
        "Applies on the way out only. Equipment coming back in is never stopped for want of "
        "a pass.",
        group="gate",
    ),
    RuleSpec(
        "gate.require_override_reason",
        Kind.BOOL,
        True,
        "A guard must write a reason when overriding a hold",
        "Turning this off removes the only record of why a blocked computer was let through.",
        group="gate",
    ),
    RuleSpec(
        "gate.override_reason_min_length",
        Kind.INT,
        10,
        "Shortest override reason accepted",
        "Characters. Low enough not to be an obstacle at a busy gate, high enough that 'ok' "
        "does not count as a reason.",
        group="gate",
        minimum=0,
        maximum=500,
    ),
    RuleSpec(
        "gate.notify_owner_on_exit",
        Kind.BOOL,
        True,
        "Message the owner when their computer leaves campus",
        "The single most useful thing the system does for a theft: the owner finds out within "
        "seconds rather than at the end of the day.",
        group="gate",
    ),
    # ------------------------------------------------------ gate wording
    RuleSpec(
        "gate.message_pending",
        Kind.TEXT,
        "Registration is still pending approval by the registration office.",
        "Wording: awaiting approval",
        group="gate",
        maximum=300,
    ),
    RuleSpec(
        "gate.message_stolen",
        Kind.TEXT,
        "This device is reported STOLEN. Hold it and call security control.",
        "Wording: reported stolen",
        group="gate",
        maximum=300,
    ),
    RuleSpec(
        "gate.message_lost",
        Kind.TEXT,
        "This device is reported LOST by its owner.",
        "Wording: reported lost",
        group="gate",
        maximum=300,
    ),
    RuleSpec(
        "gate.message_retired",
        Kind.TEXT,
        "This device was retired from the register.",
        "Wording: retired",
        group="gate",
        maximum=300,
    ),
    RuleSpec(
        "gate.message_owner_inactive",
        Kind.TEXT,
        "Owner status is {status}, not active.",
        "Wording: owner not active",
        "{status} is replaced with the student's status.",
        group="gate",
        maximum=300,
    ),
    RuleSpec(
        "gate.message_needs_pass",
        Kind.TEXT,
        "University property. It needs a gate pass before it can leave campus. Issue one "
        "under Permits, or record an override with a reason.",
        "Wording: university property with no gate pass",
        group="gate",
        maximum=300,
    ),
    # -------------------------------------------------------- registration
    RuleSpec(
        "registration.public_form_enabled",
        Kind.BOOL,
        True,
        "Students may register a computer online",
        "Turn off during an incident, or out of term. The form then tells students to come in "
        "person instead of failing at them.",
        group="registration",
        public=True,
    ),
    RuleSpec(
        "registration.missing_report_enabled",
        Kind.BOOL,
        True,
        "Students may report their own computer lost or stolen online",
        group="registration",
        public=True,
    ),
    RuleSpec(
        "registration.max_devices_per_student",
        Kind.INT,
        3,
        "Most computers one student may have on the register",
        "The main brake on registering somebody else's machine. A student with a laptop, a "
        "tablet and a spare is ordinary; a student with nine is worth a conversation. Counts "
        "everything not archived, including submissions still awaiting approval. Set 0 for no "
        "limit.",
        group="registration",
        minimum=0,
        maximum=50,
    ),
    RuleSpec(
        "registration.require_photo",
        Kind.BOOL,
        True,
        "A photograph of the computer is required",
        "A guard compares the machine in front of them against this. Without it a written "
        "description is all that stands between two identical laptops.",
        group="registration",
        public=True,
    ),
    RuleSpec(
        "registration.require_ownership_proof",
        Kind.BOOL,
        False,
        "Ask where and when the computer was bought",
        "Not proof by itself, but somebody registering a machine they picked up an hour ago "
        "has to invent an answer, and the answer is on the record when the real owner reports "
        "it missing.",
        group="registration",
        public=True,
    ),
    RuleSpec(
        "registration.velocity_window_hours",
        Kind.INT,
        24,
        "Window for counting repeat submissions",
        "Hours.",
        group="registration",
        minimum=1,
        maximum=720,
    ),
    RuleSpec(
        "registration.velocity_max_attempts",
        Kind.INT,
        5,
        "Submissions from one student in that window before it is flagged for review",
        "Does not block the student. It puts the account in front of an officer, because "
        "repeated attempts on different serials is what working through a bag of stolen "
        "laptops looks like.",
        group="registration",
        minimum=1,
        maximum=100,
    ),
    # -------------------------------------------------------------- permit
    RuleSpec(
        "permit.max_duration_days",
        Kind.INT,
        30,
        "Longest gate pass that may be issued",
        "Days. A pass with no end date is a permanent hole in the register. Set 0 for no limit.",
        group="permit",
        minimum=0,
        maximum=3650,
    ),
    # ------------------------------------------------------------- session
    RuleSpec(
        "session.idle_minutes",
        Kind.INT,
        30,
        "Minutes of inactivity before a signed-in session ends",
        "The gate console runs on a shared terminal that is often left facing a queue, so this "
        "matters more here than in an ordinary admin system.",
        group="session",
        minimum=1,
        maximum=720,
        public=True,
    ),
    RuleSpec(
        "session.idle_warning_seconds",
        Kind.INT,
        60,
        "Warning shown before that happens",
        "Seconds. Any real interaction cancels it.",
        group="session",
        minimum=5,
        maximum=600,
        public=True,
    ),
]

REGISTRY = {spec.key: spec for spec in _SPECS}
DEFAULTS = {spec.key: spec.default for spec in _SPECS}


def all_rules():
    """Every rule value, stored ones layered over the declared defaults.

    Read once per row rendered - every computer on a page asks what the
    wording of a hold is - so it goes through two layers: a per-thread memo
    that expires in seconds, and the shared cache behind it. The memo is what
    keeps a page of thirty computers from costing thirty queries when there is
    no shared cache to hit. See config/requestcache.py.
    """
    return requestcache.get(CACHE_KEY, _load_rules)


def _load_rules():
    values = derived().get(CACHE_KEY)
    if values is None:
        values = dict(DEFAULTS)
        # Imported here rather than at module level: rules.py is imported by
        # models.py, and importing models from it at module scope would be a
        # circular import during app loading.
        from .models import Rule

        for key, value in Rule.objects.values_list("key", "value"):
            spec = REGISTRY.get(key)
            if not spec:
                # A rule left behind by an older release. Ignored rather than
                # served, so removing a rule from the registry is safe.
                continue
            try:
                values[key] = spec.clean(value)
            except ValueError:
                values[key] = spec.default
        derived().set(CACHE_KEY, values, getattr(settings, "CACHE_TIMEOUT_RULES", 600))
    return values


def rule(key):
    """One rule value. Unknown keys raise, because a typo must not read as False."""
    if key not in REGISTRY:
        raise KeyError(f"Unknown rule {key!r}")
    return all_rules()[key]


def text(key, **replacements):
    """A wording rule with its placeholders filled in.

    Placeholders are the registrar's to keep or drop. A typo that leaves an
    unknown `{name}` in the text must not raise at a gate, so an unmatched
    placeholder is left as written rather than blowing up the lookup.
    """
    raw = rule(key)
    for name, value in replacements.items():
        raw = raw.replace("{" + name + "}", str(value))
    return raw


def public_rules():
    """The subset a signed-out browser may read."""
    values = all_rules()
    return {key: values[key] for key, spec in REGISTRY.items() if spec.public}


def invalidate():
    derived().delete(CACHE_KEY)
    requestcache.clear(CACHE_KEY)
