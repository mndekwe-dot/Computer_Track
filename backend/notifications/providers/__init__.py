"""Delivery providers.

Each one is a thin adapter over somebody else's HTTP API, and each is written
so it can be exercised without a network: the transport is a module-level
function the tests replace, not a client constructed at import time.

Nothing in here decides *whether* to send. That is the outbox's job, in
notifications/service.py. These modules only know how to hand one message to
one provider and say plainly whether it left.
"""
