"""University-owned equipment on the same register as student laptops.

The question at the gate is different for the two. For a laptop it is "does
this belong to the person carrying it". For a projector it is "is this
authorised to leave at all", and that one depends on which way it is going.
"""

from django.test import TestCase
from django.utils import timezone

from campus.models import Department
from checkpoint.models import Direction, Verdict
from devices.models import Device, DeviceStatus, Ownership, TemporaryPermit

from .factories import api_client, make_device, make_gate, make_student, make_user


def make_equipment(**extra):
    defaults = {
        "serial_number": "PJ-1000-A",
        "brand": "Epson",
        "model_name": "EB-1795F",
        "device_type": "PROJECTOR",
        "ownership": Ownership.UNIVERSITY,
        "status": DeviceStatus.ACTIVE,
        "custodian_name": "Dr Habimana",
    }
    defaults.update(extra)
    return Device.objects.create(**defaults)


class OwnershipRulesTests(TestCase):
    def setUp(self):
        self.registrar = make_user("registrar-prop", role="REGISTRAR")
        self.client_api = api_client(self.registrar)
        self.department = Department.objects.create(name="Physics", code="PHY")

    def test_a_registrar_can_register_university_property_with_no_student(self):
        response = self.client_api.post(
            "/api/devices/",
            {
                "serial_number": "PJ-2000-B",
                "brand": "Epson",
                "model_name": "EB-2250U",
                "device_type": "PROJECTOR",
                "ownership": Ownership.UNIVERSITY,
                "department": self.department.pk,
                "custodian_name": "Dr Habimana",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data["owner"])
        self.assertEqual(response.data["department_name"], "Physics")

    def test_university_property_needs_a_department_or_a_custodian(self):
        """Otherwise a guard holding it at midnight has nobody to call."""
        response = self.client_api.post(
            "/api/devices/",
            {
                "serial_number": "PJ-3000-C",
                "brand": "Epson",
                "device_type": "PROJECTOR",
                "ownership": Ownership.UNIVERSITY,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("department", response.data)

    def test_a_student_device_still_requires_an_owner(self):
        response = self.client_api.post(
            "/api/devices/",
            {
                "serial_number": "LP-4000-D",
                "brand": "HP",
                "device_type": "LAPTOP",
                "ownership": Ownership.STUDENT,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("owner", response.data)

    def test_university_property_cannot_also_have_a_student_owner(self):
        student = make_student(reg_number="218004444")
        response = self.client_api.post(
            "/api/devices/",
            {
                "serial_number": "PJ-5000-E",
                "brand": "Epson",
                "device_type": "PROJECTOR",
                "ownership": Ownership.UNIVERSITY,
                "department": self.department.pk,
                "owner": student.pk,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("owner", response.data)


class GateRulesTests(TestCase):
    def setUp(self):
        self.guard = make_user("guard-prop", role="GUARD")
        self.client_api = api_client(self.guard)
        self.gate = make_gate()
        self.equipment = make_equipment()

    def test_it_is_held_on_the_way_out_without_a_pass(self):
        response = self.client_api.get(
            "/api/checkpoint/lookup/", {"q": "PJ-1000-A", "direction": Direction.OUT}
        )
        self.assertEqual(response.status_code, 200)
        device = response.data["devices"][0]
        self.assertEqual(device["recommendation"]["action"], "HOLD")
        self.assertTrue(any("gate pass" in r for r in device["recommendation"]["reasons"]))

    def test_it_passes_freely_on_the_way_in(self):
        """A projector coming back must not be stopped for want of a pass."""
        response = self.client_api.get(
            "/api/checkpoint/lookup/", {"q": "PJ-1000-A", "direction": Direction.IN}
        )
        device = response.data["devices"][0]
        self.assertEqual(device["recommendation"]["action"], "PASS")

    def test_a_valid_pass_lets_it_out(self):
        now = timezone.now()
        TemporaryPermit.objects.create(
            device=self.equipment,
            bearer_name="Dr Habimana",
            reason="Conference in Huye",
            valid_from=now - timezone.timedelta(hours=1),
            valid_to=now + timezone.timedelta(days=2),
        )
        response = self.client_api.get(
            "/api/checkpoint/lookup/", {"q": "PJ-1000-A", "direction": Direction.OUT}
        )
        device = response.data["devices"][0]
        self.assertEqual(device["recommendation"]["action"], "PASS")

    def test_the_server_refuses_a_plain_allowed_on_the_way_out(self):
        """Not a console rule: the offline queue is editable localStorage."""
        response = self.client_api.post(
            "/api/checkpoint/scans/",
            {
                "device": self.equipment.pk,
                "gate": self.gate.pk,
                "direction": Direction.OUT,
                "verdict": Verdict.ALLOWED,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("gate pass", str(response.data["verdict"]))

    def test_an_override_with_a_reason_is_still_allowed(self):
        response = self.client_api.post(
            "/api/checkpoint/scans/",
            {
                "device": self.equipment.pk,
                "gate": self.gate.pk,
                "direction": Direction.OUT,
                "verdict": Verdict.OVERRIDE,
                "override_reason": "Dean authorised by phone, pass to follow.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_bringing_it_back_in_records_without_a_pass(self):
        response = self.client_api.post(
            "/api/checkpoint/scans/",
            {
                "device": self.equipment.pk,
                "gate": self.gate.pk,
                "direction": Direction.IN,
                "verdict": Verdict.ALLOWED,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

    def test_a_scan_of_university_property_records_no_student(self):
        response = self.client_api.post(
            "/api/checkpoint/scans/",
            {
                "device": self.equipment.pk,
                "gate": self.gate.pk,
                "direction": Direction.IN,
                "verdict": Verdict.ALLOWED,
            },
            format="json",
        )
        self.assertIsNone(response.data["student"])
        self.assertIn("PJ-1000-A", response.data["device_label"])


class SearchTests(TestCase):
    def test_equipment_is_findable_by_department_and_custodian(self):
        department = Department.objects.create(name="Chemistry", code="CHM")
        make_equipment(serial_number="MC-77-Z", department=department, custodian_name="Uwase")
        guard = make_user("guard-search-prop", role="GUARD")

        for term in ["Chemistry", "Uwase", "MC-77-Z"]:
            response = api_client(guard).get("/api/search/suggest/", {"q": term})
            self.assertEqual(response.status_code, 200)
            serials = [item.get("serial_number") for item in response.data.get("devices", [])]
            self.assertIn("MC-77-Z", serials, f"{term} should find the projector")
