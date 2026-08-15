from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from devices.models import Device, DeviceFlag, DeviceStatus, OwnershipTransfer

from .factories import api_client, make_device, make_student, make_user


class DevicePermissionTests(TestCase):
    """Guards must be able to look, and must not be able to touch."""

    def setUp(self):
        self.guard = make_user("guard1", role="GUARD")
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.student = make_student("218001234")
        self.device = make_device(self.student, "HP12345678")

    def test_guard_can_read_devices(self):
        response = api_client(self.guard).get(f"/api/devices/{self.device.id}/")
        self.assertEqual(response.status_code, 200)

    def test_guard_cannot_register_a_device(self):
        response = api_client(self.guard).post(
            "/api/devices/",
            {"serial_number": "DL99887766", "brand": "Dell", "owner": self.student.id},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_guard_cannot_change_ownership(self):
        other = make_student("218009999")
        response = api_client(self.guard).post(
            f"/api/devices/{self.device.id}/transfer/",
            {"to_student_reg_number": other.reg_number},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_registrar_can_register_a_device(self):
        response = api_client(self.registrar).post(
            "/api/devices/",
            {"serial_number": "DL99887766", "brand": "Dell", "owner": self.student.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Device.objects.get(serial_key="DL99887766").registered_by, self.registrar)

    def test_only_an_admin_can_manage_staff_accounts(self):
        self.assertEqual(api_client(self.registrar).get("/api/auth/users/").status_code, 403)
        admin = make_user("admin", role="ADMIN")
        self.assertEqual(api_client(admin).get("/api/auth/users/").status_code, 200)


class DeviceRegistrationTests(TestCase):
    def setUp(self):
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.client = api_client(self.registrar)
        self.student = make_student("218001234")
        self.device = make_device(self.student, "HP12345678")

    def test_duplicate_serial_is_rejected_and_names_the_current_owner(self):
        response = self.client.post(
            "/api/devices/",
            {"serial_number": "hp-1234 5678", "brand": "HP", "owner": self.student.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("218001234", response.json()["serial_number"][0])

    def test_serial_is_stored_normalised_for_lookup(self):
        device = Device.objects.create(
            owner=self.student, serial_number=" dl-9988 7766 ", brand="Dell"
        )
        self.assertEqual(device.serial_number, "DL-9988 7766")
        self.assertEqual(device.serial_key, "DL99887766")

    def test_qr_endpoint_returns_a_png(self):
        response = self.client.get(f"/api/devices/{self.device.id}/qr/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertTrue(response.content.startswith(b"\x89PNG"))

    def test_transfer_moves_the_device_and_records_the_history(self):
        new_owner = make_student("218009999", first_name="Bosco", last_name="Mugisha")
        response = self.client.post(
            f"/api/devices/{self.device.id}/transfer/",
            {"to_student_reg_number": "218 009 999", "reason": "Sold to classmate"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.device.refresh_from_db()
        self.assertEqual(self.device.owner, new_owner)

        transfer = OwnershipTransfer.objects.get()
        self.assertEqual(transfer.from_student, self.student)
        self.assertEqual(transfer.to_student, new_owner)
        self.assertEqual(transfer.transferred_by, self.registrar)

    def test_transfer_to_an_unknown_reg_number_fails(self):
        response = self.client.post(
            f"/api/devices/{self.device.id}/transfer/",
            {"to_student_reg_number": "000000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_report_stolen_sets_status_and_raises_a_flag(self):
        response = self.client.post(
            f"/api/devices/{self.device.id}/report_stolen/",
            {"details": "Taken from the library."},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.STOLEN)
        self.assertTrue(self.device.is_blocked)
        self.assertEqual(DeviceFlag.objects.filter(is_active=True).count(), 1)

    def test_resolving_a_theft_flag_also_reactivates_the_device(self):
        self.client.post(f"/api/devices/{self.device.id}/report_stolen/", {}, format="json")
        flag = DeviceFlag.objects.get()
        response = self.client.post(
            f"/api/devices/flags/{flag.id}/resolve/",
            {"resolution_note": "Recovered and returned to the owner."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.ACTIVE)
        self.assertFalse(self.device.is_blocked)


class TemporaryPermitTests(TestCase):
    def setUp(self):
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.client = api_client(self.registrar)
        self.device = make_device(make_student("218001234"), "HP12345678")
        self.now = timezone.now()

    def create_permit(self, valid_from=None, valid_to=None):
        # Windows are expressed relative to now so the result does not depend
        # on what time of day the suite happens to run.
        return self.client.post(
            "/api/devices/permits/",
            {
                "device": self.device.id,
                "bearer_name": "Patrick Habimana",
                "bearer_id_number": "216100045",
                "valid_from": (valid_from or self.now - timedelta(hours=1)).isoformat(),
                "valid_to": (valid_to or self.now + timedelta(days=5)).isoformat(),
            },
            format="json",
        )

    def gate_permits(self):
        guard = make_user("guard1", role="GUARD")
        body = api_client(guard).get("/api/checkpoint/lookup/", {"q": "218001234"}).json()
        return body["devices"][0]["valid_permits"]

    def test_permit_must_expire_after_it_starts(self):
        response = self.create_permit(
            valid_from=self.now + timedelta(hours=2), valid_to=self.now + timedelta(hours=1)
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("valid_to", response.json())

    def test_a_live_permit_shows_up_on_the_device_at_the_gate(self):
        self.assertEqual(self.create_permit().status_code, 201)
        permits = self.gate_permits()
        self.assertEqual(len(permits), 1)
        self.assertEqual(permits[0]["bearer_name"], "Patrick Habimana")

    def test_a_permit_that_has_not_started_yet_is_not_shown(self):
        self.create_permit(
            valid_from=self.now + timedelta(days=1), valid_to=self.now + timedelta(days=2)
        )
        self.assertEqual(self.gate_permits(), [])

    def test_an_expired_permit_is_not_shown(self):
        self.create_permit(
            valid_from=self.now - timedelta(days=2), valid_to=self.now - timedelta(days=1)
        )
        self.assertEqual(self.gate_permits(), [])

    def test_revoked_permit_disappears_from_the_gate_view(self):
        permit_id = self.create_permit().json()["id"]
        self.client.post(f"/api/devices/permits/{permit_id}/revoke/", {}, format="json")
        self.assertEqual(self.gate_permits(), [])
