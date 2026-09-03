"""Turning records into searchable tokens, and querying them back."""

import re

from django.db import transaction
from django.db.models import Q

from .models import SearchToken

# Anything that is not a letter or digit separates words. Reg numbers and
# serials therefore index both with and without their punctuation.
SPLIT = re.compile(r"[^A-Za-z0-9]+")
MAX_TOKEN = 64
MIN_PREFIX = 2


def _looks_like_identifier(text):
    """Reg numbers, serials and asset tags contain digits; names do not.

    Only identifiers get a punctuation-stripped form added to the index.
    Squashing "Aline Uwase" into "ALINEUWASE" would just be noise nobody will
    ever type, while "UNI-024/01" genuinely does get typed as "UNI02401".
    """
    return any(character.isdigit() for character in text)


def tokenise(*values):
    """The set of words a record should be findable by."""
    tokens = set()
    for value in values:
        text = str(value or "").strip().upper()
        if not text:
            continue
        parts = [part for part in SPLIT.split(text) if part]
        tokens.update(part[:MAX_TOKEN] for part in parts)
        if len(parts) > 1 and _looks_like_identifier(text):
            tokens.add("".join(parts)[:MAX_TOKEN])
    return {token for token in tokens if token}


def student_tokens(student):
    return tokenise(
        student.reg_number,
        student.reg_number_key,
        student.first_name,
        student.last_name,
        student.email,
        student.phone,
        student.national_id,
        student.programme,
    )


def device_tokens(device):
    return tokenise(
        device.serial_number,
        device.serial_key,
        device.asset_tag,
        device.brand,
        device.model_name,
        device.colour,
        # Indexed against the owner too, so "Mugisha laptop" style searches and
        # reg-number searches both reach the computer.
        device.owner.reg_number if device.owner_id else "",
        device.owner.first_name if device.owner_id else "",
        device.owner.last_name if device.owner_id else "",
        # University property has no student to search by, so the department
        # and the custodian take that job: a guard holding a projector at a
        # gate types "physics" or the name of whoever signed it out.
        device.department.name if device.department_id else "",
        device.custodian_name,
    )


@transaction.atomic
def reindex_student(student):
    wanted = student_tokens(student)
    _sync(SearchToken.objects.filter(student=student), wanted, student=student)


@transaction.atomic
def reindex_device(device):
    wanted = device_tokens(device)
    _sync(SearchToken.objects.filter(device=device), wanted, device=device)


def _sync(existing_qs, wanted, **owner):
    """Add what is missing, drop what is stale - never rewrite the whole set.

    Rewriting on every save would churn the index on unrelated edits (a phone
    number, a note) and make saves progressively slower as records grow.
    """
    current = set(existing_qs.values_list("token", flat=True))
    to_add = wanted - current
    to_remove = current - wanted

    if to_remove:
        existing_qs.filter(token__in=to_remove).delete()
    if to_add:
        SearchToken.objects.bulk_create(
            [SearchToken(token=token, **owner) for token in to_add],
            ignore_conflicts=True,
        )


def prefix_range(word):
    """Half-open range [word, successor) covering every token starting with `word`.

    This is the difference between the index working and not working.
    `LIKE 'MUGISH%'` looks like a prefix match, but SQLite's LIKE is
    case-insensitive by default, so it cannot use a plain B-tree index and
    degrades to scanning the whole token table - which is several times larger
    than the table it was meant to accelerate. (Postgres has the same problem
    under a non-C collation without `text_pattern_ops`.)

    An explicit `>= word AND < successor` is an ordinary ordered range scan,
    which every engine serves straight from the index. Tokens are stored
    uppercased and queries are uppercased before they get here, so this is
    exactly equivalent to a case-insensitive prefix match.
    """
    return word, word[:-1] + chr(ord(word[-1]) + 1)


def _token_subquery(word, field):
    """The ids whose tokens start with `word`, as a subquery - not a value set.

    Returning a subquery rather than a materialised set of ids matters too: if
    the caller pulls every matching id into Python, a common surname means
    shipping thousands of integers out of the database before the caller's own
    LIMIT can discard them.
    """
    queryset = SearchToken.objects.filter(**{f"{field}__isnull": False})
    if len(word) < MIN_PREFIX:
        # A one-character prefix matches most of the table and is not worth a
        # scan; require an exact hit instead.
        queryset = queryset.filter(token=word)
    else:
        low, high = prefix_range(word)
        queryset = queryset.filter(token__gte=low, token__lt=high)
    return queryset.values(f"{field}_id")


def _token_filter(queryset, words, text, field):
    """AND the words together over the token index.

    A punctuated identifier needs a second route. "218-001-234" splits into
    three fragments, but the reg number is stored as the single token
    "218001234", so ANDing "218" AND "001" AND "234" would find nothing. The
    squashed form is therefore ORed in.
    """
    if len(words) > 1 and _looks_like_identifier(text):
        all_words = Q()
        for word in words:
            all_words &= Q(pk__in=_token_subquery(word, field))
        return queryset.filter(
            all_words | Q(pk__in=_token_subquery("".join(words), field))
        )

    for word in words:
        queryset = queryset.filter(pk__in=_token_subquery(word, field))
    return queryset


def _identifier_query(text, words):
    """The squashed form, when the whole query reads as one identifier.

    "218 001 234" and "218001234" both qualify; "Aline 218" does not, because
    the name part has to go through the token index anyway.
    """
    squashed = "".join(words)
    if squashed and _looks_like_identifier(squashed) and squashed.isalnum():
        return squashed
    return None


def _supports_trigram():
    """Only PostgreSQL, and only when the extension actually installed."""
    from django.conf import settings
    from django.db import connection

    if not getattr(settings, "USING_POSTGRES", False):
        return False
    if connection.vendor != "postgresql":
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
            return cursor.fetchone() is not None
    except Exception:
        return False


def _contains_filter(queryset, words, field):
    """Middle-of-word fallback: find `gish` inside `MUGISHA`.

    Prefix search structurally cannot do this, so on PostgreSQL the trigram
    index handles it. Elsewhere this degrades to `icontains`, which is a scan,
    acceptable precisely because it only ever runs when the fast path already
    came back empty, which is rare.
    """
    for word in words:
        queryset = queryset.filter(
            pk__in=SearchToken.objects.filter(
                **{f"{field}__isnull": False, "token__icontains": word}
            ).values(f"{field}_id")
        )
    return queryset


def _with_contains_fallback(queryset, base_result, words, field):
    """Try the indexed prefix first; widen only if it found nothing."""
    if base_result.exists():
        return base_result
    # A one- or two-character fragment matches too much to be useful.
    if not words or max(len(word) for word in words) < 3:
        return base_result
    return _contains_filter(queryset, words, field)


def filter_students(queryset, query):
    """Narrow to students matching the query, cheapest route first.

    Reg numbers already live in their own unique index (`reg_number_key`), so a
    reg-number search is served by a direct range scan on that column and never
    touches the token table at all - the fastest path there is, and the one the
    gate uses all day. Names fall through to the inverted index.
    """
    text = (query or "").upper()
    words = [word for word in SPLIT.split(text) if word]
    if not words:
        return queryset

    identifier = _identifier_query(text, words)
    if identifier and len(identifier) >= MIN_PREFIX:
        low, high = prefix_range(identifier)
        return queryset.filter(reg_number_key__gte=low, reg_number_key__lt=high)

    prefixed = _token_filter(queryset, words, text, "student")
    return _with_contains_fallback(queryset, prefixed, words, "student")


def filter_devices(queryset, query):
    """As above, but serial numbers are the indexed column that matters."""
    text = (query or "").upper()
    words = [word for word in SPLIT.split(text) if word]
    if not words:
        return queryset

    identifier = _identifier_query(text, words)
    if identifier and len(identifier) >= MIN_PREFIX:
        low, high = prefix_range(identifier)
        # A digit-ish query is either a serial or the owner's reg number, and
        # the guard does not care which they typed.
        return queryset.filter(
            Q(serial_key__gte=low, serial_key__lt=high)
            | Q(owner__reg_number_key__gte=low, owner__reg_number_key__lt=high)
        )

    prefixed = _token_filter(queryset, words, text, "device")
    return _with_contains_fallback(queryset, prefixed, words, "device")


# Id-set helpers, for callers that genuinely need the ids rather than a
# queryset. Prefer the filter_* functions on any path that applies a limit.
def student_ids(query):
    from students.models import Student

    if not (query or "").strip():
        return None
    return set(filter_students(Student.objects.all(), query).values_list("pk", flat=True))


def device_ids(query):
    from devices.models import Device

    if not (query or "").strip():
        return None
    return set(filter_devices(Device.objects.all(), query).values_list("pk", flat=True))
