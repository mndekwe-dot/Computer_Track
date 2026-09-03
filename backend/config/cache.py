"""Two caches, because two different things are being cached.

`default` holds state that *is* the truth while it lives there: rate-limit
counters, most of all. Losing it silently resets somebody's throttle window.

`derived` holds copies of things the database already knows - the policy
rules, the equipment types, the message templates, the dashboard totals.
Losing all of it costs a few queries and nothing else.

Keeping them apart matters in two places. In production they can be tuned
differently, or pointed at different Redis databases, without one evicting the
other under memory pressure. In tests, `derived` is a dummy cache so that one
test cannot serve another test's stale rules, while `default` stays real so
that the rate limiting under test actually rate limits.
"""

from django.core.cache import caches

DERIVED = "derived"


def derived():
    """The cache for data that can always be rebuilt from the database.

    Resolved on each call rather than held in a module global, so that
    `override_settings(CACHES=...)` in a test is actually honoured.
    """
    return caches[DERIVED]
