"""Keep the cached rule and equipment tables honest.

Both are read on the hot path - a gate lookup reads the rules, a device list
reads the labels - so both are cached. A stale rule is worse than a slow one:
a registrar who turns off a hold and watches the gate keep applying it has no
way to tell whether the system is broken or they misread the screen. So the
cache is cleared on write rather than left to expire.

`transaction.on_commit` rather than a plain call: clearing before the write
commits would let a concurrent read repopulate the cache from the old row.
"""

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from . import equipment, rules
from .models import EquipmentType, Rule


@receiver(post_save, sender=Rule)
@receiver(post_delete, sender=Rule)
def _clear_rules(sender, **kwargs):
    transaction.on_commit(rules.invalidate)


@receiver(post_save, sender=EquipmentType)
@receiver(post_delete, sender=EquipmentType)
def _clear_equipment(sender, **kwargs):
    transaction.on_commit(equipment.invalidate)
