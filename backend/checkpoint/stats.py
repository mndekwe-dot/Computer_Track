"""The dashboard numbers, computed once and cached.

This is the most expensive read in the system and the least urgent. It is a
wall screen in the security office: left open all day, refetched on a timer,
and read by several people at once. Every load used to run a dozen separate
aggregates over the whole scan table, several of which counted the same rows
again with a different filter.

Two changes, in order of how much they matter:

  The counts that share a filter are now one query with conditional
  aggregation. Four `.count()` calls over "today's scans" is four table scans
  to answer four questions about the same rows.

  The whole payload is cached for a short window and refreshed by a scheduled
  task, so the cost is paid by a background worker rather than by whichever
  guard happens to open the page after it expired.

The cache window is short on purpose. A dashboard thirty seconds behind is
fine; one five minutes behind will be disbelieved, and a number nobody trusts
is worse than no number.
"""

from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Max, Q
from django.utils import timezone

from campus.models import Gate
from config.cache import derived

from .models import Direction, ScanEvent, Verdict

CACHE_KEY = "checkpoint.dashboard.v1"


def _today_counts(today):
    """Every count about today's scans, in one query.

    `Count("id", filter=...)` is a conditional aggregate: the database walks
    the day's rows once and increments seven counters as it goes, instead of
    walking them seven times.
    """
    row = ScanEvent.objects.filter(created_at__date=today).aggregate(
        total=Count("id"),
        entries=Count("id", filter=Q(direction=Direction.IN)),
        exits=Count("id", filter=Q(direction=Direction.OUT)),
        allowed=Count("id", filter=Q(verdict=Verdict.ALLOWED)),
        denied=Count("id", filter=Q(verdict=Verdict.DENIED)),
        overrides=Count("id", filter=Q(verdict=Verdict.OVERRIDE)),
        unregistered=Count("id", filter=Q(verdict=Verdict.UNREGISTERED)),
    )
    return {key: value or 0 for key, value in row.items()}


def _devices_on_campus():
    """A device is on campus when its most recent scan was a successful entry.

    The subquery is passed to the filter rather than being pulled into Python
    first. `id__in=list(...)` materialised every device's latest scan id into
    a Python list and shipped it back as a literal IN clause, which on a
    register of any size is a query whose text grows with the data.
    """
    latest_ids = (
        ScanEvent.objects.filter(device__isnull=False)
        .values("device")
        .annotate(last_id=Max("id"))
        .values("last_id")
    )
    return ScanEvent.objects.filter(
        id__in=latest_ids,
        direction=Direction.IN,
        verdict__in=[Verdict.ALLOWED, Verdict.OVERRIDE],
    ).count()


def _by_gate(today):
    return list(
        Gate.objects.filter(is_active=True)
        .annotate(
            scans_today=Count("scan_events", filter=Q(scan_events__created_at__date=today)),
            denials_today=Count(
                "scan_events",
                filter=Q(
                    scan_events__created_at__date=today,
                    scan_events__verdict=Verdict.DENIED,
                ),
            ),
        )
        .values("id", "name", "code", "scans_today", "denials_today")
    )


def _trend(week_ago):
    """Seven days of entries and exits, with the gaps filled in.

    Days with no scans do not come back from the database at all. Charting
    only the days that exist draws a line that skips Sunday and misrepresents
    the shape, so the missing days are filled with zeroes here rather than
    left for the browser to guess at.
    """
    rows = (
        ScanEvent.objects.filter(created_at__date__gte=week_ago)
        .values("created_at__date")
        .annotate(
            total=Count("id"),
            entries=Count("id", filter=Q(direction=Direction.IN)),
            exits=Count("id", filter=Q(direction=Direction.OUT)),
        )
    )
    by_date = {row["created_at__date"]: row for row in rows}

    trend = []
    for offset in range(7):
        day = week_ago + timedelta(days=offset)
        row = by_date.get(day)
        trend.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%a"),
                "total": row["total"] if row else 0,
                "entries": row["entries"] if row else 0,
                "exits": row["exits"] if row else 0,
            }
        )
    return trend


def recent_problems(limit=10):
    """The denials and overrides worth a second look.

    `student` and `device` are selected because the serializer reads through
    both. Without them this was ten extra queries for a ten-row list.
    """
    return ScanEvent.objects.filter(
        verdict__in=[Verdict.DENIED, Verdict.OVERRIDE, Verdict.UNREGISTERED]
    ).select_related("gate", "guard", "student", "device")[:limit]


def build_dashboard():
    """Everything the wall screen shows. Uncached."""
    from .serializers import ScanEventSerializer

    now = timezone.now()
    today = timezone.localdate()
    week_ago = today - timedelta(days=6)

    counts = _today_counts(today)
    return {
        "generated_at": now,
        "today": counts,
        "devices_on_campus": _devices_on_campus(),
        "by_gate": _by_gate(today),
        "trend": _trend(week_ago),
        "recent_problems": ScanEventSerializer(recent_problems(), many=True).data,
    }


def dashboard(force=False):
    """The cached payload, rebuilt when it has gone."""
    if not force:
        cached = derived().get(CACHE_KEY)
        if cached is not None:
            return cached
    payload = build_dashboard()
    derived().set(CACHE_KEY, payload, getattr(settings, "CACHE_TIMEOUT_DASHBOARD", 30))
    return payload


def refresh_dashboard_cache():
    """Rebuild ahead of the next reader. Called from the scheduled task."""
    return dashboard(force=True)
