"""The gate lookup is the one endpoint that must never surprise a guard."""

from django.test import TestCase

from devices.models import DeviceStatus
from students.models import StudentStatus

from .factories import api_client, make_device, make_gate, make_student, make_user


class GateLookupTests(TestCase):
    def setUp(self):
        self.gate = make_gate()
        self.guard = make_user("guard1", role="GUARD", default_gate=self.gate)
        self.client = api_client(self.guard)
        self.student = make_student("218001234")
        self.device = make_device(self.student, "HP12345678")

    def lookup(self, query):
        return self.client.get("/api/checkpoint/lookup/", {"q": query})

    def test_finds_student_by_reg_number(self):
        response = self.lookup("218001234")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["resolved_as"], "STUDENT")
        self.assertEqual(body["student"]["reg_number"], "218001234")
        self.assertEqual(len(body["devices"]), 1)
        self.assertEqual(body["devices"][0]["recommendation"]["action"], "PASS")

    def test_reg_number_tolerates_spaces_dashes_and_case(self):
        for variant in ["218 001 234", "218-001-234", " 218001234 ", "218/001/234"]:
            with self.subTest(variant=variant):
                body = self.lookup(variant).json()
                self.assertEqual(body["resolved_as"], "STUDENT", variant)
                self.assertEqual(body["student"]["reg_number"], "218001234")

    def test_finds_device_by_serial_when_owner_is_absent(self):
        body = self.lookup("hp 1234 5678").json()
        self.assertEqual(body["resolved_as"], "DEVICE")
        self.assertEqual(body["matched_device_id"], self.device.id)
        self.assertEqual(body["student"]["reg_number"], "218001234")

    def test_finds_device_by_qr_payload(self):
        body = self.lookup(f"CTRACK:{self.device.uid}").json()
        self.assertEqual(body["resolved_as"], "DEVICE")
        self.assertEqual(body["method"], "QR")
        self.assertEqual(body["matched_device_id"], self.device.id)

    def test_finds_device_by_asset_tag(self):
        self.device.asset_tag = "UNI-02401"
        self.device.save()
        body = self.lookup("uni-02401").json()
        self.assertEqual(body["resolved_as"], "DEVICE")
        self.assertEqual(body["method"], "ASSET_TAG")

    def test_unknown_query_returns_guidance_and_suggestions(self):
        body = self.lookup("999999999").json()
        self.assertEqual(body["resolved_as"], "NOT_FOUND")
        self.assertTrue(body["message"])
        self.assertIn("suggestions", body)

    def test_stolen_device_is_recommended_for_hold(self):
        self.device.status = DeviceStatus.STOLEN
        self.device.save()
        body = self.lookup("218001234").json()
        recommendation = body["devices"][0]["recommendation"]
        self.assertEqual(recommendation["action"], "HOLD")
        self.assertIn("STOLEN", recommendation["reasons"][0])

    def test_suspended_student_raises_a_warning_on_every_device(self):
        self.student.status = StudentStatus.SUSPENDED
        self.student.save()
        body = self.lookup("218001234").json()
        self.assertTrue(body["warnings"])
        self.assertEqual(body["devices"][0]["recommendation"]["action"], "HOLD")

    def test_student_with_no_registered_computer_is_called_out(self):
        self.device.delete()
        body = self.lookup("218001234").json()
        self.assertEqual(body["devices"], [])
        self.assertTrue(any("no computer registered" in w for w in body["warnings"]))

    def test_lookup_requires_authentication(self):
        response = api_client().get("/api/checkpoint/lookup/", {"q": "218001234"})
        self.assertEqual(response.status_code, 401)
