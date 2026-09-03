"""Resolving whatever the guard typed or scanned into a person and a device."""

import uuid

from config.qr import strip_prefix
from devices import queries
from devices.models import normalise_serial
from students.models import Student, normalise_reg_number

from .models import LookupMethod


def _device_queryset():
    """The gate shape: flags, permits and the last movement, all prefetched.

    This is the query a guard waits on, several hundred times a shift, so it
    is the one place where an extra round trip per computer is actually felt.
    """
    return queries.for_gate()


def _student_queryset():
    return Student.objects.select_related("department")


def resolve_query(raw_query):
    """Return (resolved_as, student, devices, matched_device, method).

    Tried in the order that costs the guard the least time: a scanned QR is
    unambiguous, a reg number is what the student says out loud, and a serial
    is the fallback when a laptop turns up without its owner.
    """
    query = (raw_query or "").strip()
    if not query:
        return "NOT_FOUND", None, [], None, LookupMethod.MANUAL

    # 1. QR sticker - "<prefix>:<uuid>" or a bare UUID.
    candidate = strip_prefix(query)
    try:
        device_uid = uuid.UUID(candidate)
    except (ValueError, AttributeError):
        device_uid = None
    if device_uid:
        device = _device_queryset().filter(uid=device_uid).first()
        if device:
            return "DEVICE", device.owner, [device], device, LookupMethod.QR

    # 2. Registration number - the everyday path.
    student = _student_queryset().filter(reg_number_key=normalise_reg_number(query)).first()
    if student:
        devices = list(_device_queryset().filter(owner=student, is_archived=False))
        return "STUDENT", student, devices, None, LookupMethod.REG_NUMBER

    # 3. Serial number off the chassis.
    device = _device_queryset().filter(serial_key=normalise_serial(query)).first()
    if device:
        return "DEVICE", device.owner, [device], device, LookupMethod.SERIAL

    # 4. University asset tag sticker.
    device = _device_queryset().filter(asset_tag=query.upper()).first()
    if device:
        return "DEVICE", device.owner, [device], device, LookupMethod.ASSET_TAG

    return "NOT_FOUND", None, [], None, LookupMethod.MANUAL


def suggest(raw_query, limit=5):
    """Near matches for a mistyped query, so the guard can pick instead of retype.

    Runs off the inverted index, so this stays fast as the register grows.
    """
    from search.indexer import filter_devices, filter_students

    query = (raw_query or "").strip()
    if len(query) < 2:
        return {"students": [], "devices": []}

    students = filter_students(_student_queryset(), query)[:limit]
    devices = filter_devices(_device_queryset().filter(is_archived=False), query)[:limit]
    return {
        "students": [
            {"id": s.id, "reg_number": s.reg_number, "full_name": s.full_name} for s in students
        ],
        "devices": [
            {"id": d.id, "serial_number": d.serial_number, "label": d.label} for d in devices
        ],
    }
