"""Keep the search index in step with the records without anyone remembering to."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from devices.models import Device
from students.models import Student

from .indexer import reindex_device, reindex_student


@receiver(post_save, sender=Student)
def index_student(sender, instance, **kwargs):
    reindex_student(instance)
    # A student's name and reg number are indexed against their computers too,
    # so renaming a student has to refresh those rows as well.
    for device in instance.devices.all():
        reindex_device(device)


@receiver(post_save, sender=Device)
def index_device(sender, instance, **kwargs):
    reindex_device(instance)


# Deletions need no handler: SearchToken cascades from both foreign keys, so
# the database removes the tokens with the record.
