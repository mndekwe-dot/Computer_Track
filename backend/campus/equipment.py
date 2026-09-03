"""The list of equipment types, read from the database and cached.

`Device.device_type` stores a code rather than a foreign key. That is on
purpose: a scan log written in 2026 has to still read correctly in 2031, after
somebody has renamed or deleted the type. The code is the fact; the label is
presentation, and is looked up through here.
"""

from django.conf import settings

from config import requestcache
from config.cache import derived

CACHE_KEY = "campus.equipment_types.v1"

# The list a fresh database starts with. Seeded by `manage.py seed_reference`
# and by the migration, then owned by the registration office - it is a
# starting point, not a constraint.
SEED = [
    ("LAPTOP", "Laptop", "", True, 10),
    ("TABLET", "Tablet", "", True, 20),
    ("DESKTOP", "Desktop / tower", "", True, 30),
    ("MONITOR", "Monitor", "", False, 40),
    ("PROJECTOR", "Projector", "", False, 50),
    ("OTHER", "Other equipment", "Anything not covered above.", True, 90),
]


def _rows():
    """Read once per device rendered, so it gets the same two-layer treatment
    as the rules. See config/requestcache.py."""
    return requestcache.get(CACHE_KEY, _load_rows)


def _load_rows():
    rows = derived().get(CACHE_KEY)
    if rows is None:
        from .models import EquipmentType

        rows = list(
            EquipmentType.objects.values(
                "code", "label", "description", "is_active", "offered_to_students", "sort_order"
            )
        )
        derived().set(CACHE_KEY, rows, getattr(settings, "CACHE_TIMEOUT_RULES", 600))
    return rows


def all_types():
    return _rows()


def active_types():
    return [row for row in _rows() if row["is_active"]]


def student_choices():
    """What the public form offers. Ordering is the registrar's."""
    return [
        {"value": row["code"], "label": row["label"], "description": row["description"]}
        for row in _rows()
        if row["is_active"] and row["offered_to_students"]
    ]


def staff_choices():
    return [
        {"value": row["code"], "label": row["label"], "description": row["description"]}
        for row in active_types()
    ]


def label_for(code):
    """Human label for a stored code, falling back to the code itself.

    A device whose type was later deleted still has to render. Showing the raw
    code is honest and readable; showing an empty cell is neither.
    """
    if not code:
        return ""
    for row in _rows():
        if row["code"] == code:
            return row["label"]
    return code


def is_valid(code, for_students=False):
    for row in _rows():
        if row["code"] == code and row["is_active"]:
            return row["offered_to_students"] if for_students else True
    return False


def invalidate():
    derived().delete(CACHE_KEY)
    requestcache.clear(CACHE_KEY)
