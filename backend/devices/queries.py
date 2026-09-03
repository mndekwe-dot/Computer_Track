"""Querysets shaped so a page of devices costs a fixed number of queries.

Every serializer field that reaches through a relation is a query per row
unless the queryset says otherwise, and the gate console reads six of them.
Left alone, showing a student's four computers took twenty-odd round trips;
these helpers make it four, whatever the page size.
"""

from django.db.models import OuterRef, Prefetch, Subquery

from .models import Device, DeviceFlag


def _last_scan(field):
    """The value of `field` on this device's most recent scan.

    A correlated subquery rather than a prefetch, because the last row is
    wanted and a prefetch cannot be sliced - prefetching every scan a device
    has ever had, to read one of them, is the more expensive mistake. The
    (device, -created_at) index makes each of these an index seek.
    """
    from checkpoint.models import ScanEvent

    return Subquery(
        ScanEvent.objects.filter(device=OuterRef("pk"))
        .order_by("-created_at")
        .values(field)[:1]
    )


def with_last_movement(queryset):
    return queryset.annotate(
        last_scan_at=_last_scan("created_at"),
        last_scan_direction=_last_scan("direction"),
        last_scan_verdict=_last_scan("verdict"),
        last_scan_gate=_last_scan("gate__name"),
    )


def base(queryset=None):
    """Everything a device list renders, in one round trip per relation."""
    queryset = Device.objects.all() if queryset is None else queryset
    return queryset.select_related("owner", "owner__department", "department", "registered_by")


def with_holds(queryset):
    """Flags and permits, prefetched so blocking_reasons() adds no queries.

    Only active flags are fetched. `Device.active_flags` filters the prefetched
    rows in Python, so narrowing here means the resolved flags of a device with
    a long history are never loaded at all.
    """
    return queryset.prefetch_related(
        Prefetch(
            "flags",
            queryset=DeviceFlag.objects.filter(is_active=True).select_related(
                "raised_by", "resolved_by", "device", "device__owner"
            ),
        ),
        "permits",
    )


def for_list(queryset=None):
    return with_holds(base(queryset))


def for_gate(queryset=None):
    """The heaviest shape: what the guard's screen needs, all of it."""
    return with_last_movement(with_holds(base(queryset)))
