"""A floor under every endpoint.

The tight limits are the scoped ones: the login form, the public student
form, the endpoints that can read the whole register. Those are set per view
and are the numbers that actually matter.

These two are different. They exist so that an endpoint nobody remembered to
throttle - the next one somebody adds - still has a ceiling. They are set
loose enough that no real person reaches them and a gate under rush-hour load
never does, which is the point: a baseline that fires during normal work is a
baseline that gets raised until it means nothing.

Both are skipped where a tighter scoped limit already applies, so a view does
not spend two buckets on one request.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


def _has_scope(view):
    return bool(getattr(view, "throttle_scope", None))


class BaselineAnonThrottle(AnonRateThrottle):
    """Per IP, for anything reachable without signing in."""

    scope = "anon"

    def allow_request(self, request, view):
        if _has_scope(view):
            return True
        return super().allow_request(request, view)


class BaselineUserThrottle(UserRateThrottle):
    """Per account, once signed in.

    Deliberately generous. A guard flicking between screens during a queue
    generates a surprising number of requests, and being rate limited at a
    gate is worse than the load it would have saved.
    """

    scope = "user"

    def allow_request(self, request, view):
        if _has_scope(view):
            return True
        # The lookup endpoints carry their own per-account ceilings from
        # accounts/throttles.py, which are the ones tuned for that traffic.
        if any(
            klass.__name__.startswith("Lookup") for klass in getattr(view, "throttle_classes", ())
        ):
            return True
        return super().allow_request(request, view)


class WriteThrottle(UserRateThrottle):
    """Applied to endpoints that change data.

    A gate records a handful of scans a minute and a registrar saves a few
    records an hour. Nothing legitimate writes hundreds, so this catches a
    client stuck in a retry loop as readily as anything hostile - and the
    stuck client is the case that actually happens.
    """

    scope = "write"

    def allow_request(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return super().allow_request(request, view)
