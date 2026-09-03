"""A very short-lived in-process memo, in front of the shared cache.

The policy rules and the equipment-type labels are read *per row*: rendering
thirty computers asks thirty times what the wording of a hold is, and thirty
times what "LAPTOP" is called. That is correct behaviour and unavoidable at
the call sites - it is what makes the wording editable at all.

The shared cache handles it when there is one. This layer handles the case
where there is not: a fresh deployment with no Redis, a cache that has just
been flushed, a test run. Without it, one of those turns a page of thirty
devices into thirty extra queries, which is exactly the N+1 the caching was
supposed to remove.

Two properties make it safe to hold data outside a transaction like this:

  It is per thread, so one request cannot see another's.

  It expires in seconds, not minutes. A worker thread that lives for days will
  pick up a rule change within `TTL`, and the shared cache plus its
  invalidation signal is still the mechanism that makes a change visible
  promptly. This is only a floor under the cost, not the cache itself.
"""

import threading
import time

from django.conf import settings

_state = threading.local()

# Long enough to cover one request, short enough that no operator will ever
# notice it. A rule saved in the portal reaches every process through the
# shared cache immediately; this bounds the worst case when there is none.
DEFAULT_TTL = 5


def _ttl():
    return getattr(settings, "REQUEST_MEMO_SECONDS", DEFAULT_TTL)


def get(key, build):
    """The memoised value for `key`, calling `build()` at most once per TTL."""
    ttl = _ttl()
    if ttl <= 0:
        return build()

    store = getattr(_state, "store", None)
    if store is None:
        store = {}
        _state.store = store

    now = time.monotonic()
    entry = store.get(key)
    if entry is not None and entry[0] > now:
        return entry[1]

    value = build()
    store[key] = (now + ttl, value)
    return value


def clear(key=None):
    """Drop one key, or everything, for this thread."""
    store = getattr(_state, "store", None)
    if not store:
        return
    if key is None:
        store.clear()
    else:
        store.pop(key, None)
