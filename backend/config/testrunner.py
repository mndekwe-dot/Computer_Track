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

import unittest

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings

from config import requestcache


class EtrackerTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        from django.conf import settings

        caches = dict(settings.CACHES)
        caches["derived"] = {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}
        # `override_settings` rather than assigning to settings.CACHES: it
        # fires the setting_changed signal, which is what actually rebuilds
        # the already-instantiated cache handler.
        self._test_isolation = override_settings(CACHES=caches)
        self._test_isolation.enable()

    def teardown_test_environment(self, **kwargs):
        self._test_isolation.disable()
        super().teardown_test_environment(**kwargs)

    def get_resultclass(self):
        """Clear the per-thread rule memo before every test.

        The memo holds the policy rules for five seconds per thread, and it
        earns its place: without it a page of thirty computers costs thirty
        extra queries, which `tests.test_performance` asserts. So it cannot
        simply be switched off for the suite.

        But a test that changes a rule has its database write rolled back at
        the end, and a rollback fires no signal, so nothing clears the memo.
        The next test to start inside those five seconds reads the previous
        test's rules.

        That is invisible on a slow machine, where tests are further apart
        than the TTL, and reliable on a fast one. It is why
        test_university_property passed locally in 254 seconds and failed in
        CI in 53, asserting HOLD and getting PASS because test_rules had set
        gate.university_property_needs_pass to False moments earlier.
        """
        base = super().get_resultclass() or unittest.TextTestResult

        class ResultClearingTheRuleMemo(base):
            def startTest(self, test):
                requestcache.clear()
                super().startTest(test)

        return ResultClearingTheRuleMemo
