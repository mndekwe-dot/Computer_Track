"""Test runner that stops one test serving another test's stale data.

Django's local-memory cache lives for the whole process, not for one test. So
a rule cached by one test is still cached in the next, and a dashboard built
in one test is served to another - which is how a suite starts failing in an
order-dependent way that nobody can reproduce alone.

Only the `derived` cache is switched off. It holds copies of what the database
already knows, so removing it changes no behaviour, only the bleed.

`default` stays a real cache on purpose. It is where the rate limiting keeps
its counters, and a rate-limit test against a cache that forgets everything
passes without testing anything.

The caching itself is not left unexercised by this: the tests that are about
caching turn `derived` back on with `override_settings`, which makes them
explicit about what they are testing instead of relying on a global.
"""

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class ComputerTrackTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        from django.conf import settings

        caches = dict(settings.CACHES)
        caches["derived"] = {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
        # `override_settings` rather than assigning to settings.CACHES: it
        # fires the setting_changed signal, which is what actually rebuilds
        # the already-instantiated cache handler.
        self._no_derived_cache = override_settings(CACHES=caches)
        self._no_derived_cache.enable()

    def teardown_test_environment(self, **kwargs):
        self._no_derived_cache.disable()
        super().teardown_test_environment(**kwargs)
