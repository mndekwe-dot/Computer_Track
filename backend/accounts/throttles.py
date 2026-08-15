"""Per-account limits on the endpoints that can read the whole register.

A signed-in guard can look up any student and any computer - that is the job.
But it also means one leaked guard password is enough to walk the entire
register, one query at a time. These throttles are keyed on the *account*, not
the IP, so a shared gate terminal does not pool its budget and a stolen login
cannot quietly enumerate the campus from anywhere.

Two windows, because they catch different things:
  burst - a script hammering the endpoint right now
  daily - a slow scrape spread over a shift to stay under the burst limit
"""

from rest_framework.throttling import UserRateThrottle


class LookupBurstThrottle(UserRateThrottle):
    """Generous enough for a rush-hour queue, far below scripted speed."""

    scope = "lookup-burst"


class LookupDailyThrottle(UserRateThrottle):
    """A whole shift of genuine gate work sits well inside this."""

    scope = "lookup-daily"

    def allow_request(self, request, view):
        # Administrators run reports and reconciliations; the daily ceiling is
        # aimed at gate accounts, so it does not apply to them.
        if request.user and request.user.is_authenticated and request.user.is_admin_role:
            return True
        return super().allow_request(request, view)
