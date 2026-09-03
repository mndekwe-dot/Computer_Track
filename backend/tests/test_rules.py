"""Policy the registration office owns, rather than the code.

The point of these tests is that changing a rule changes what happens at a
gate, immediately, with no deployment. A settings screen that saves a value
nobody reads is worse than no settings screen.
"""

from django.test import TestCase
from django.test.utils import override_settings

from campus import rules
from campus.models import Rule
from checkpoint.models import Direction, Verdict
from devices.models import DeviceStatus, Ownership

from .factories import api_client, make_device, make_gate, make_student, make_user

RULES_URL = "/api/campus/rules/"

LOCMEM = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "derived": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


class RegistryTests(TestCase):
    def test_every_default_survives_its_own_validation(self):
        """A default that its own spec would reject is a rule nobody can save."""
        for key, spec in rules.REGISTRY.items():
            with self.subTest(key=key):
                self.assertEqual(spec.clean(spec.default), spec.default)

    def test_every_rule_belongs_to_a_declared_group(self):
        """Otherwise it renders in no section of the screen and is unreachable."""
        for key, spec in rules.REGISTRY.items():
            with self.subTest(key=key):
                self.assertIn(spec.group, rules.GROUPS)

    def test_an_unknown_key_raises_rather_than_reading_as_false(self):
        """A typo must not silently disable a check.

        `rule("gate.block_pendign")` returning None would read as falsy at
        every call site, turning a misspelling into a gate that waves through
        every unapproved computer.
        """
        with self.assertRaises(KeyError):
            rules.rule("gate.no_such_rule")

    def test_numbers_are_bounded(self):
        spec = rules.REGISTRY["registration.max_devices_per_student"]
        self.assertEqual(spec.clean("4"), 4)
        with self.assertRaises(ValueError):
            spec.clean(-1)
        with self.assertRaises(ValueError):
            spec.clean("not a number")

    def test_booleans_accept_what_a_form_actually_sends(self):
        spec = rules.REGISTRY["gate.block_pending"]
        for truthy in [True, "true", "True", "1", "on", "yes"]:
            self.assertIs(spec.clean(truthy), True, truthy)
        for falsy in [False, "false", "0", "off", "no"]:
            self.assertIs(spec.clean(falsy), False, falsy)

    def test_a_corrupt_stored_value_falls_back_to_the_default(self):
        """A bad row must not take the gate down.

        Nothing should be able to write one - the API validates - but a hand
        edit in the Django admin can, and a gate lookup that raises is a queue
        that stops moving.
        """
        Rule.objects.create(key="registration.max_devices_per_student", value="banana")
        rules.invalidate()
        self.assertEqual(rules.rule("registration.max_devices_per_student"), 3)

    def test_a_rule_left_over_from_an_older_release_is_ignored(self):
        Rule.objects.create(key="gate.rule_that_no_longer_exists", value=True)
        rules.invalidate()
        self.assertNotIn("gate.rule_that_no_longer_exists", rules.all_rules())

    def test_placeholders_are_substituted_and_unknown_ones_left_alone(self):
        self.assertEqual(
            rules.text("gate.message_owner_inactive", status="Suspended"),
            "Owner status is Suspended, not active.",
        )

    def test_public_rules_never_include_operational_policy(self):
        """The signed-out form reads these. A thief should not learn the limits."""
        public = rules.public_rules()
        for leaky in [
            "registration.max_devices_per_student",
            "registration.velocity_max_attempts",
            "gate.block_pending",
        ]:
            self.assertNotIn(leaky, public)


class RulesApiTests(TestCase):
    def setUp(self):
        self.registrar = make_user("registrar-rules", role="REGISTRAR")
        self.guard = make_user("guard-rules", role="GUARD")
        self.client_api = api_client(self.registrar)

    def test_a_registrar_can_read_every_rule_with_its_help_text(self):
        response = self.client_api.get(RULES_URL)
        self.assertEqual(response.status_code, 200)
        keys = {row["key"] for row in response.data["rules"]}
        self.assertEqual(keys, set(rules.REGISTRY))
        row = next(r for r in response.data["rules"] if r["key"] == "gate.block_pending")
        self.assertTrue(row["label"])
        self.assertTrue(row["is_default"])

    def test_a_guard_may_read_policy_but_not_change_it(self):
        """The console reads these - the idle timeout, the gate wording - so a
        guard has to be able to fetch them. Writing is the registrar's."""
        client = api_client(self.guard)
        self.assertEqual(client.get(RULES_URL).status_code, 200)
        self.assertEqual(
            client.post(
                RULES_URL, {"values": {"gate.block_pending": False}}, format="json"
            ).status_code,
            403,
        )
        self.assertIs(rules.rule("gate.block_pending"), True)

    def test_saving_a_rule_takes_effect_at_once(self):
        response = self.client_api.post(
            RULES_URL,
            {"values": {"registration.max_devices_per_student": 7}},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(rules.rule("registration.max_devices_per_student"), 7)

    def test_a_bad_value_is_refused_and_nothing_else_is_written(self):
        """All or nothing: a half-applied policy is worse than a rejected one."""
        response = self.client_api.post(
            RULES_URL,
            {
                "values": {
                    "gate.block_pending": False,
                    "registration.max_devices_per_student": -5,
                }
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIs(rules.rule("gate.block_pending"), True)

    def test_an_unknown_key_is_refused(self):
        response = self.client_api.post(
            RULES_URL, {"values": {"gate.make_me_a_sandwich": True}}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("no such setting", str(response.data).lower())

    def test_a_rule_can_be_put_back_to_its_default(self):
        self.client_api.post(
            RULES_URL, {"values": {"registration.max_devices_per_student": 9}}, format="json"
        )
        response = self.client_api.delete(
            RULES_URL, {"key": "registration.max_devices_per_student"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(rules.rule("registration.max_devices_per_student"), 3)


class RulesChangeGateBehaviourTests(TestCase):
    """The part that matters: a saved rule changes the answer at the gate."""

    def setUp(self):
        self.guard = make_user("guard-policy", role="GUARD")
        self.client_api = api_client(self.guard)
        self.gate = make_gate()
        self.student = make_student("218001234")
        self.device = make_device(self.student, "LP00001111", status=DeviceStatus.PENDING)

    def lookup(self):
        response = self.client_api.get("/api/checkpoint/lookup/", {"q": "218001234"})
        return response.data["devices"][0]["recommendation"]

    def test_a_pending_computer_is_held_by_default(self):
        self.assertEqual(self.lookup()["action"], "HOLD")

    def test_turning_the_pending_hold_off_lets_it_pass(self):
        from .factories import set_rule

        set_rule("gate.block_pending", False)
        self.assertEqual(self.lookup()["action"], "PASS")

    def test_the_wording_a_guard_reads_is_editable(self):
        from .factories import set_rule

        set_rule("gate.message_pending", "Not approved yet. Send them to Block C.")
        self.assertIn("Block C", self.lookup()["reasons"][0])

    def test_a_shorter_override_reason_can_be_accepted(self):
        from .factories import set_rule

        payload = {
            "device": self.device.id,
            "gate": self.gate.id,
            "direction": Direction.OUT,
            "verdict": Verdict.OVERRIDE,
            "override_reason": "Dean ok",
        }
        refused = self.client_api.post("/api/checkpoint/scans/", payload, format="json")
        self.assertEqual(refused.status_code, 400)
        self.assertIn("at least 10", str(refused.data))

        set_rule("gate.override_reason_min_length", 5)
        accepted = self.client_api.post("/api/checkpoint/scans/", payload, format="json")
        self.assertEqual(accepted.status_code, 201, accepted.data)

    def test_university_property_can_be_let_out_without_a_pass(self):
        from .factories import set_rule

        self.device.ownership = Ownership.UNIVERSITY
        self.device.owner = None
        self.device.status = DeviceStatus.ACTIVE
        self.device.custodian_name = "Dr Habimana"
        self.device.save()

        self.assertTrue(self.device.exit_restrictions())
        set_rule("gate.university_property_needs_pass", False)
        self.assertEqual(self.device.exit_restrictions(), [])


@override_settings(CACHES=LOCMEM)
class RuleCachingTests(TestCase):
    """The cache is switched back on here, because it is the subject.

    Everywhere else the suite runs against a dummy `derived` cache so one test
    cannot serve another test's stale rules. See config/testrunner.py.
    """

    def setUp(self):
        rules.invalidate()

    def tearDown(self):
        rules.invalidate()

    def test_rules_are_read_from_cache_after_the_first_time(self):
        rules.all_rules()
        with self.assertNumQueries(0):
            rules.all_rules()
            rules.rule("gate.block_pending")

    def test_saving_a_rule_clears_the_cache(self):
        """Through the model, so the signal is what does the clearing.

        A registrar who turns a hold off and watches the gate keep applying it
        has no way to tell whether the system is broken or they misread the
        screen, so staleness here is worse than the queries it saves.
        """
        self.assertIs(rules.rule("gate.block_pending"), True)
        # The signal clears on commit, not on save: clearing before the write
        # lands would let a concurrent read repopulate from the old row. A
        # TestCase transaction never commits, so the callbacks are run here.
        with self.captureOnCommitCallbacks(execute=True):
            Rule.objects.create(key="gate.block_pending", value=False)
        self.assertIs(rules.rule("gate.block_pending"), False)
