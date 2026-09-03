"""Query counts, pinned.

An N+1 is not a slow query. It is a query count that grows with the data, and
it is invisible in development where the table has nine rows. These tests each
build a small set of records and then a larger one, and assert the number of
queries did not move.

That is the only assertion that actually catches the regression. Asserting a
fixed number would fail on any unrelated change and get relaxed until it meant
nothing; asserting the count is the *same* for one row and for ten is the
property that matters, and it is the property a careless `.filter()` on a
related manager breaks.
"""

from django.test import TestCase

from checkpoint.models import Direction, ScanEvent, Verdict
from devices.models import DeviceFlag, FlagReason, TemporaryPermit
from django.utils import timezone

from .factories import api_client, make_device, make_gate, make_student, make_user


def count_queries(test, callable_):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as captured:
        callable_()
    return len(captured)


class GateLookupQueryTests(TestCase):
    """The query a guard waits on, several hundred times a shift."""

    def setUp(self):
        self.guard = make_user("guard-perf", role="GUARD")
        self.client_api = api_client(self.guard)
        self.gate = make_gate()
        self.student = make_student("218001234")

    def add_device(self, serial):
        device = make_device(self.student, serial)
        # Everything the console renders per computer: a hold, a gate pass and
        # a last movement. Each was a separate query per device before.
        DeviceFlag.objects.create(
            device=device, reason=FlagReason.OTHER, details="Check the charger.", is_active=True
        )
        now = timezone.now()
        TemporaryPermit.objects.create(
            device=device,
            bearer_name="Bosco",
            valid_from=now - timezone.timedelta(hours=1),
            valid_to=now + timezone.timedelta(days=1),
        )
        ScanEvent.objects.create(
            device=device,
            student=self.student,
            gate=self.gate,
            direction=Direction.IN,
            verdict=Verdict.ALLOWED,
        )
        return device

    def lookup(self):
        response = self.client_api.get("/api/checkpoint/lookup/", {"q": "218001234"})
        assert response.status_code == 200, response.data
        # Touch the rendered body, so nothing is left lazy and uncounted.
        assert response.data["devices"]

    def test_a_lookup_costs_the_same_for_one_computer_as_for_six(self):
        self.add_device("AAA0001")
        self.lookup()  # warm anything cached on first use
        one = count_queries(self, self.lookup)

        for index in range(5):
            self.add_device(f"BBB000{index}")
        many = count_queries(self, self.lookup)

        self.assertEqual(
            one,
            many,
            f"a lookup cost {one} queries for one computer and {many} for six: "
            f"something is querying per device",
        )


class DeviceListQueryTests(TestCase):
    def setUp(self):
        self.registrar = make_user("registrar-perf", role="REGISTRAR")
        self.client_api = api_client(self.registrar)
        self.student = make_student("218001234")

    def add_devices(self, count, prefix):
        for index in range(count):
            device = make_device(self.student, f"{prefix}{index:04d}")
            DeviceFlag.objects.create(
                device=device, reason=FlagReason.OTHER, details="hold", is_active=True
            )

    def list_devices(self):
        response = self.client_api.get("/api/devices/", {"page_size": 100})
        assert response.status_code == 200, response.data
        assert response.data["results"]

    def test_the_register_costs_the_same_for_three_rows_as_for_thirty(self):
        self.add_devices(3, "AAA")
        self.list_devices()
        few = count_queries(self, self.list_devices)

        self.add_devices(27, "BBB")
        many = count_queries(self, self.list_devices)

        self.assertEqual(
            few,
            many,
            f"the device list cost {few} queries for 3 rows and {many} for 30: "
            f"blocking reasons or flag counts are querying per row",
        )


class DashboardQueryTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin-perf", role="ADMIN")
        self.client_api = api_client(self.admin)
        self.gate = make_gate()
        self.student = make_student("218001234")
        self.device = make_device(self.student, "AAA0001")

    def add_scans(self, count, verdict=Verdict.DENIED):
        for _ in range(count):
            ScanEvent.objects.create(
                device=self.device,
                student=self.student,
                gate=self.gate,
                direction=Direction.OUT,
                verdict=verdict,
            )

    def load(self):
        response = self.client_api.get("/api/checkpoint/dashboard/")
        assert response.status_code == 200, response.data

    def test_the_dashboard_costs_the_same_however_many_scans_there_are(self):
        """The recent-problems list reads through student and device on every
        row, which was ten extra queries for a ten-row list."""
        self.add_scans(3)
        self.load()
        few = count_queries(self, self.load)

        self.add_scans(20)
        many = count_queries(self, self.load)

        self.assertEqual(few, many, f"dashboard cost {few} then {many} queries")


class BulkScanQueryTests(TestCase):
    """The offline queue flush, which arrives with fifty scans at once."""

    def setUp(self):
        self.guard = make_user("guard-bulk-perf", role="GUARD")
        self.client_api = api_client(self.guard)
        self.gate = make_gate()
        self.student = make_student("218001234")
        self.device = make_device(self.student, "AAA0001")

    def payload(self, count, offset=0):
        return {
            "scans": [
                {
                    "device": self.device.id,
                    "gate": self.gate.id,
                    "direction": Direction.IN,
                    "verdict": Verdict.ALLOWED,
                    "client_reference": f"ref-{offset + index}",
                }
                for index in range(count)
            ]
        }

    def test_the_duplicate_check_is_one_query_for_the_whole_batch(self):
        """It was an `.exists()` per scan, on the one endpoint whose entire
        purpose is arriving with a batch."""
        first = count_queries(
            self,
            lambda: self.client_api.post(
                "/api/checkpoint/scans/bulk/", self.payload(2), format="json"
            ),
        )
        second = count_queries(
            self,
            lambda: self.client_api.post(
                "/api/checkpoint/scans/bulk/", self.payload(2, offset=100), format="json"
            ),
        )
        self.assertEqual(first, second)

        # Ten scans should not cost five times what two cost. Each scan still
        # needs its own INSERT - the snapshot in ScanEvent.save() is worth more
        # than a bulk_create - so the count grows, but the *lookup* half is
        # flat, and that is what is asserted here.
        ten = count_queries(
            self,
            lambda: self.client_api.post(
                "/api/checkpoint/scans/bulk/", self.payload(10, offset=200), format="json"
            ),
        )
        overhead_per_scan = (ten - second) / 8
        self.assertLessEqual(
            overhead_per_scan,
            2.0,
            f"each extra queued scan cost {overhead_per_scan:.1f} queries",
        )


class PublicStatusQueryTests(TestCase):
    def setUp(self):
        from .factories import set_rule

        set_rule("registration.require_photo", False)
        self.client = api_client()
        self.student = make_student(
            "218001234", email="a@example.edu", national_id="1199012345678"
        )

    def check(self):
        response = self.client.post(
            "/api/public/my-computers/",
            {"reg_number": "218001234", "verification": "1199012345678"},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.data["computers"] is not None

    def test_checking_your_own_computers_does_not_query_per_computer(self):
        """`guidance_for` asks whether each device is blocked, which reads its
        flags. Prefetching is what keeps that from being one query per row."""
        make_device(self.student, "AAA0001")
        self.check()
        one = count_queries(self, self.check)

        for index in range(4):
            make_device(self.student, f"BBB000{index}")
        many = count_queries(self, self.check)

        self.assertEqual(one, many, f"cost {one} queries for one, {many} for five")
