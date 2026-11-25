"""The public "report my computer missing" endpoint.

This is the only unauthenticated write in the system that blocks something,
so the tests here are mostly about what it refuses to do.
"""

import json
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import SimpleRateThrottle

from devices.models import Device, DeviceFlag, DeviceStatus, FlagReason
from students.models import Student

from .factories import make_device, make_student, make_user

URL = "/api/public/report-missing/"


class PublicMissingReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = make_student(reg_number="218001234", email="aline@student.ac")
        self.device = make_device(self.student, serial_number="HP12345678")
        self.device.status = DeviceStatus.ACTIVE
        self.device.save(update_fields=["status"])

    def payload(self, **overrides):
        data = {
            "reg_number": "218 001 234",
            "verification": "aline@student.ac",
            "serial_number": "hp-12345678",
            "kind": FlagReason.STOLEN,
            "details": "Taken from the library reading room.",
        }
        data.update(overrides)
        return data

    def test_the_owner_can_block_their_own_computer(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(URL, self.payload(), format="json")

        self.assertEqual(response.status_code, 201)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.STOLEN)
        self.assertTrue(self.device.is_blocked)
        # A tolerant serial and a spaced reg number must both work: the person
        # filing this is upset and typing on a phone.
        flag = DeviceFlag.objects.get(device=self.device)
        self.assertEqual(flag.reason, FlagReason.STOLEN)
        self.assertIsNone(flag.raised_by, "nobody signed in raised this")

    def test_the_owner_is_told_a_hold_was_placed_in_their_name(self):
        """The only defence against a malicious report is that it is not quiet."""
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(URL, self.payload(), format="json")

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("HP12345678", body)
        self.assertIn("registration office", body)

    def test_wrong_verification_is_refused(self):
        response = self.client.post(
            URL, self.payload(verification="someone@else.ac"), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.ACTIVE)

    def test_cannot_report_a_computer_belonging_to_someone_else(self):
        other = make_student(reg_number="218009999", email="other@student.ac")
        theirs = make_device(other, serial_number="DL99887766")

        response = self.client.post(
            URL, self.payload(serial_number="DL99887766"), format="json"
        )

        self.assertEqual(response.status_code, 400)
        theirs.refresh_from_db()
        self.assertEqual(theirs.status, DeviceStatus.ACTIVE, "their computer must be untouched")
        self.assertFalse(DeviceFlag.objects.filter(device=theirs).exists())

    def test_an_unknown_serial_does_not_reveal_whether_it_exists(self):
        """Otherwise this becomes a tool for probing the register."""
        other = make_student(reg_number="218008888", email="third@student.ac")
        make_device(other, serial_number="LN55554444")

        existing = self.client.post(URL, self.payload(serial_number="LN55554444"), format="json")
        invented = self.client.post(URL, self.payload(serial_number="ZZ00000000"), format="json")

        self.assertEqual(existing.status_code, 400)
        self.assertEqual(invented.status_code, 400)
        self.assertEqual(
            existing.data["serial_number"],
            invented.data["serial_number"],
            "a registered serial and an invented one must be indistinguishable",
        )

    def test_reporting_twice_is_refused_rather_than_stacking_flags(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(URL, self.payload(), format="json")
        again = self.client.post(URL, self.payload(), format="json")

        self.assertEqual(again.status_code, 400)
        self.assertEqual(DeviceFlag.objects.filter(device=self.device).count(), 1)

    def test_lost_is_a_separate_outcome_from_stolen(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(URL, self.payload(kind=FlagReason.LOST), format="json")

        self.assertEqual(response.status_code, 201)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.LOST)

    def test_an_arbitrary_kind_is_refused(self):
        """The choice field must not accept any other flag reason."""
        response = self.client.post(URL, self.payload(kind="FINANCE"), format="json")
        self.assertEqual(response.status_code, 400)

    def test_the_endpoint_needs_no_authentication(self):
        """Stated explicitly, because it is the surprising part of the design."""
        self.assertNotIn("Authorization", self.client._credentials)

    def test_a_blocked_device_is_stopped_at_the_gate(self):
        """End to end: the point of the feature is the gate, not the flag."""
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(URL, self.payload(), format="json")

        guard = make_user("guard-missing", role="GUARD")
        gate = APIClient()
        gate.force_authenticate(user=guard)
        response = gate.get("/api/checkpoint/lookup/", {"q": "HP12345678"})

        self.assertEqual(response.status_code, 200)
        device = response.data["devices"][0]
        self.assertTrue(device["is_blocked"])
        self.assertTrue(any("STOLEN" in reason for reason in device["blocking_reasons"]))


class PublicStatusMaskingTests(TestCase):
    """The status page must not hand out a serial number.

    It is reached with a registration number and an email address or national
    ID. All three are semi-public inside a university, which is a fair bar for
    "has mine been approved yet" and far too low a bar for the one fact the
    ownership story rests on.
    """

    def setUp(self):
        self.student = make_student(reg_number="219100777", email="mask@student.university.edu")
        self.device = make_device(
            owner=self.student, serial_number="HP9876543210", asset_tag="UNI-09999"
        )

    def _status(self):
        # The real ceiling is 12/hour per address and three calls in one test
        # class would spend a quarter of it. Patching the rate table is the
        # only thing that works: SimpleRateThrottle binds THROTTLE_RATES at
        # import, so override_settings does not reach it.
        with patch.dict(SimpleRateThrottle.THROTTLE_RATES, {"public-form": "100/hour"}):
            return self._post()

    def _post(self):
        response = self.client.post(
            "/api/public/my-computers/",
            {"reg_number": self.student.reg_number, "verification": self.student.email},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_the_serial_is_not_returned_in_full(self):
        body = json.dumps(self._status())
        self.assertNotIn("HP9876543210", body)
        self.assertNotIn("UNI-09999", body)

    def test_enough_of_the_serial_remains_to_tell_two_computers_apart(self):
        shown = self._status()["computers"][0]["serial_number"]
        self.assertTrue(shown.endswith("3210"), shown)
        self.assertNotIn("HP98", shown)

    def test_a_short_identifier_is_hidden_completely(self):
        from students.public import mask_identifier

        # Keeping the last four of a four-character tag would reveal all of it.
        self.assertEqual(mask_identifier("AB12"), "••••")
        self.assertEqual(mask_identifier(""), "")
        self.assertEqual(mask_identifier(None), "")
