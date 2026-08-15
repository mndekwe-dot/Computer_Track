from django.test import TestCase

from checkpoint.models import ScanEvent
from devices.models import DeviceFlag, DeviceStatus, FlagReason

from .factories import api_client, make_device, make_gate, make_student, make_user


class ScanRecordingTests(TestCase):
    def setUp(self):
        self.gate = make_gate()
        self.guard = make_user("guard1", role="GUARD", default_gate=self.gate)
        self.client = api_client(self.guard)
        self.student = make_student("218001234")
        self.device = make_device(self.student, "HP12345678")

    def post_scan(self, **overrides):
        payload = {
            "device": self.device.id,
            "gate": self.gate.id,
            "direction": "OUT",
            "verdict": "ALLOWED",
            "method": "REG_NUMBER",
        }
        payload.update(overrides)
        return self.client.post("/api/checkpoint/scans/", payload, format="json")

    def test_guard_can_record_a_clean_exit(self):
        response = self.post_scan()
        self.assertEqual(response.status_code, 201, response.content)
        scan = ScanEvent.objects.get()
        self.assertEqual(scan.guard, self.guard)
        self.assertEqual(scan.student, self.student)
        # Details are snapshotted so the log still reads correctly later.
        self.assertIn("HP12345678", scan.device_label)
        self.assertEqual(scan.claimed_reg_number, "218001234")

    def test_gate_defaults_to_the_guards_posting(self):
        response = self.post_scan(gate=None)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(ScanEvent.objects.get().gate, self.gate)

    def test_blocked_device_cannot_be_recorded_as_plain_allowed(self):
        self.device.status = DeviceStatus.STOLEN
        self.device.save()
        response = self.post_scan(verdict="ALLOWED")
        self.assertEqual(response.status_code, 400)
        self.assertIn("verdict", response.json())
        self.assertEqual(ScanEvent.objects.count(), 0)

    def test_override_demands_a_written_reason(self):
        self.device.status = DeviceStatus.STOLEN
        self.device.save()
        blank = self.post_scan(verdict="OVERRIDE", override_reason="   ")
        self.assertEqual(blank.status_code, 400)
        self.assertIn("override_reason", blank.json())

        allowed = self.post_scan(
            verdict="OVERRIDE", override_reason="Cleared by security control on the radio."
        )
        self.assertEqual(allowed.status_code, 201, allowed.content)
        self.assertEqual(ScanEvent.objects.get().verdict, "OVERRIDE")

    def test_active_flag_blocks_even_when_status_is_active(self):
        DeviceFlag.objects.create(
            device=self.device, reason=FlagReason.UNPAID_FEES, details="Finance hold"
        )
        response = self.post_scan(verdict="ALLOWED")
        self.assertEqual(response.status_code, 400)

    def test_resolving_the_flag_clears_the_block(self):
        flag = DeviceFlag.objects.create(device=self.device, reason=FlagReason.UNPAID_FEES)
        flag.resolve(self.guard, "Fees settled")
        self.device.refresh_from_db()
        self.assertFalse(self.device.is_blocked)
        self.assertEqual(self.post_scan(verdict="ALLOWED").status_code, 201)

    def test_unregistered_device_is_logged_without_a_device_record(self):
        response = self.post_scan(
            device=None,
            verdict="UNREGISTERED",
            claimed_serial="UNKNOWN9999",
            notes="No record found. Sent to the registrar.",
        )
        self.assertEqual(response.status_code, 201, response.content)
        scan = ScanEvent.objects.get()
        self.assertIsNone(scan.device)
        self.assertEqual(scan.claimed_serial, "UNKNOWN9999")

    def test_a_normal_verdict_still_requires_a_device(self):
        response = self.post_scan(device=None, verdict="ALLOWED")
        self.assertEqual(response.status_code, 400)
        self.assertIn("device", response.json())

    def test_scans_cannot_be_edited_or_deleted(self):
        self.post_scan()
        scan = ScanEvent.objects.get()
        self.assertEqual(
            self.client.patch(f"/api/checkpoint/scans/{scan.id}/", {"notes": "x"}).status_code, 405
        )
        self.assertEqual(self.client.delete(f"/api/checkpoint/scans/{scan.id}/").status_code, 405)


class OfflineSyncTests(TestCase):
    """A gate with no network still has to work; the queue flushes later."""

    def setUp(self):
        self.gate = make_gate()
        self.guard = make_user("guard1", role="GUARD", default_gate=self.gate)
        self.client = api_client(self.guard)
        self.device = make_device(make_student("218001234"), "HP12345678")

    def queued_scan(self, reference):
        return {
            "device": self.device.id,
            "gate": self.gate.id,
            "direction": "IN",
            "verdict": "ALLOWED",
            "method": "QR",
            "client_reference": reference,
            "client_timestamp": "2026-08-15T07:30:00Z",
        }

    def test_bulk_sync_creates_the_queued_scans(self):
        response = self.client.post(
            "/api/checkpoint/scans/bulk/",
            {"scans": [self.queued_scan("ref-1"), self.queued_scan("ref-2")]},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["synced"], 2)
        self.assertEqual(ScanEvent.objects.count(), 2)

    def test_replaying_the_same_queue_does_not_duplicate_rows(self):
        payload = {"scans": [self.queued_scan("ref-1")]}
        self.client.post("/api/checkpoint/scans/bulk/", payload, format="json")
        second = self.client.post("/api/checkpoint/scans/bulk/", payload, format="json")
        self.assertEqual(second.json()["synced"], 0)
        self.assertEqual(ScanEvent.objects.count(), 1)

    def test_client_timestamp_is_kept_as_the_real_decision_time(self):
        self.client.post(
            "/api/checkpoint/scans/bulk/", {"scans": [self.queued_scan("ref-1")]}, format="json"
        )
        scan = ScanEvent.objects.get()
        self.assertEqual(scan.happened_at, scan.client_timestamp)
        self.assertNotEqual(scan.happened_at, scan.created_at)


class DashboardTests(TestCase):
    def setUp(self):
        self.gate = make_gate()
        self.guard = make_user("guard1", role="GUARD", default_gate=self.gate)
        self.client = api_client(self.guard)
        self.device = make_device(make_student("218001234"), "HP12345678")

    def test_device_counts_as_on_campus_after_its_last_scan_is_an_entry(self):
        base = {"device": self.device.id, "gate": self.gate.id, "verdict": "ALLOWED"}
        self.client.post("/api/checkpoint/scans/", {**base, "direction": "IN"}, format="json")
        self.assertEqual(
            self.client.get("/api/checkpoint/dashboard/").json()["devices_on_campus"], 1
        )

        self.client.post("/api/checkpoint/scans/", {**base, "direction": "OUT"}, format="json")
        body = self.client.get("/api/checkpoint/dashboard/").json()
        self.assertEqual(body["devices_on_campus"], 0)
        self.assertEqual(body["today"]["total"], 2)
        self.assertEqual(body["today"]["entries"], 1)

    def test_csv_export_returns_a_downloadable_log(self):
        self.client.post(
            "/api/checkpoint/scans/",
            {"device": self.device.id, "gate": self.gate.id, "direction": "OUT", "verdict": "ALLOWED"},
            format="json",
        )
        response = self.client.get("/api/checkpoint/scans/export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertIn("HP12345678", response.content.decode())
