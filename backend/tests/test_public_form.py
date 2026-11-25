"""The public student form is the only unauthenticated write in the system.

These tests exist mostly to prove what it *cannot* do.
"""

import json
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.throttling import SimpleRateThrottle

from devices.models import ApprovalEvidence, Device, DeviceStatus

from .factories import api_client, make_device, make_student, make_user, photo_bytes, set_rule

REGISTER = "/api/public/register-computer/"
STATUS = "/api/public/my-computers/"

# NOTE: `override_settings(REST_FRAMEWORK=...)` does NOT change throttle rates.
# SimpleRateThrottle.THROTTLE_RATES is bound to the settings dict at import
# time, so the class keeps pointing at the original object. Patch that dict
# directly, or the test silently runs at the real production rate.
def throttle_rate(rate):
    return patch.dict(SimpleRateThrottle.THROTTLE_RATES, {"public-form": rate})


class PublicRegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        # These tests are about what the form will and will not accept, not
        # about the photograph. The photo requirement has its own tests in
        # RegistrationDefenceTests, where it is the subject rather than a
        # prerequisite of every payload.
        set_rule("registration.require_photo", False)
        self.client = api_client()  # deliberately signed out
        self.student = make_student(
            "218001234",
            email="aline.uwase@student.university.edu",
            national_id="1199012345678",
        )

    def submit(self, **overrides):
        payload = {
            "reg_number": "218001234",
            "verification": "1199012345678",
            "serial_number": "DL99887766",
            "device_type": "LAPTOP",
            "brand": "Dell",
            "model_name": "Latitude 5420",
            "colour": "Silver",
        }
        payload.update(overrides)
        return self.client.post(REGISTER, payload, format="json")

    def test_a_student_can_register_without_signing_in(self):
        response = self.submit()
        self.assertEqual(response.status_code, 201, response.content)
        device = Device.objects.get()
        self.assertEqual(device.owner, self.student)
        self.assertEqual(device.brand, "Dell")
        self.assertIn("reference", response.json())

    def test_the_submission_is_pending_and_therefore_blocked_at_the_gate(self):
        self.submit()
        device = Device.objects.get()
        self.assertEqual(device.status, DeviceStatus.PENDING)
        # The whole safety of an open endpoint rests on this.
        self.assertTrue(device.is_blocked)

    def test_email_also_works_as_verification(self):
        response = self.submit(verification="ALINE.UWASE@student.university.edu")
        self.assertEqual(response.status_code, 201, response.content)

    def test_reg_number_is_matched_leniently(self):
        response = self.submit(reg_number="218 001-234")
        self.assertEqual(response.status_code, 201, response.content)

    def test_wrong_verification_is_refused(self):
        response = self.submit(verification="not-my-id")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Device.objects.count(), 0)

    def test_unknown_and_mismatched_reg_numbers_give_the_same_answer(self):
        """Otherwise the form becomes a way to discover who is enrolled."""
        unknown = self.submit(reg_number="999999999", verification="x")
        mismatch = self.submit(verification="x")
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(unknown.json()["verification"], mismatch.json()["verification"])

    def test_a_suspended_student_is_sent_to_the_office(self):
        self.student.status = "SUSPENDED"
        self.student.save()
        response = self.submit()
        self.assertEqual(response.status_code, 400)
        self.assertIn("registration office", str(response.json()).lower())

    def test_a_record_with_nothing_to_verify_against_is_refused(self):
        bare = make_student("218005555")
        response = self.submit(reg_number="218005555", verification="anything")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Device.objects.filter(owner=bare).count(), 0)

    def test_a_duplicate_serial_is_refused_without_naming_the_owner(self):
        other = make_student("218009999", first_name="Bosco", last_name="Mugisha")
        make_device(other, "DL99887766")
        response = self.submit(serial_number="dl-9988 7766")
        self.assertEqual(response.status_code, 400)
        body = str(response.json())
        self.assertNotIn("218009999", body)
        self.assertNotIn("Bosco", body)

    def test_the_form_cannot_set_its_own_status(self):
        response = self.submit(status="ACTIVE")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Device.objects.get().status, DeviceStatus.PENDING)

    def test_the_form_cannot_choose_an_owner(self):
        victim = make_student("218007777")
        response = self.submit(owner=victim.id)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Device.objects.get().owner, self.student)

    def test_the_form_cannot_award_itself_an_asset_tag(self):
        response = self.submit(asset_tag="UNI-00001")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(Device.objects.get().asset_tag)

    def test_the_public_surface_is_write_only(self):
        """No student list, no device list, no gate log without a login."""
        for path in ["/api/students/", "/api/devices/", "/api/checkpoint/scans/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)


class PublicStatusTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = api_client()
        self.student = make_student("218001234", national_id="1199012345678")
        self.device = make_device(self.student, "HP12345678", status=DeviceStatus.PENDING)

    def check(self, **overrides):
        payload = {"reg_number": "218001234", "verification": "1199012345678"}
        payload.update(overrides)
        return self.client.post(STATUS, payload, format="json")

    def test_a_student_can_see_their_own_computers_and_what_to_do_next(self):
        response = self.check()
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["student"]["reg_number"], "218001234")
        self.assertEqual(len(body["computers"]), 1)
        self.assertIn("Waiting for approval", body["computers"][0]["guidance"])

    def test_guidance_changes_once_approved(self):
        self.device.status = DeviceStatus.ACTIVE
        self.device.save()
        body = self.check().json()
        self.assertIn("may carry this through any gate", body["computers"][0]["guidance"])

    def test_it_cannot_be_used_to_read_another_student(self):
        other = make_student("218009999", national_id="1199099999999")
        make_device(other, "LN55554444")
        body = self.check().json()
        serials = [row["serial_number"] for row in body["computers"]]
        # Serials come back part-hidden, so the assertion is on the tail. The
        # point of the test is unchanged: one computer, and it is this
        # student's, not the other one's.
        self.assertEqual(len(serials), 1)
        self.assertTrue(serials[0].endswith("5678"), serials)
        self.assertNotIn("4444", json.dumps(body))

    def test_wrong_verification_reveals_nothing(self):
        response = self.check(verification="guessing")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("HP12345678", str(response.json()))


class PublicThrottleTests(TestCase):
    """The rate limit is the main defence against grinding reg numbers."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_repeated_guesses_are_cut_off(self):
        client = api_client()
        payload = {"reg_number": "218001234", "verification": "guess"}
        with throttle_rate("3/hour"):
            codes = [client.post(STATUS, payload, format="json").status_code for _ in range(5)]
        self.assertEqual(codes, [400, 400, 400, 429, 429], codes)

    def test_the_registration_form_is_throttled_too(self):
        client = api_client()
        payload = {"reg_number": "218001234", "verification": "guess", "brand": "X"}
        with throttle_rate("2/hour"):
            codes = [client.post(REGISTER, payload, format="json").status_code for _ in range(4)]
        self.assertEqual(codes.count(429), 2, codes)

    def test_the_real_configured_rate_is_restrictive(self):
        """Guards against someone loosening this to a useless number."""
        rate = SimpleRateThrottle.THROTTLE_RATES.get("public-form")
        self.assertIsNotNone(rate, "the public form must stay throttled")
        count, period = rate.split("/")
        self.assertLessEqual(int(count), 20, rate)
        self.assertIn(period, {"hour", "day"}, rate)


class ApprovalQueueTests(TestCase):
    def setUp(self):
        cache.clear()
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.guard = make_user("guard1", role="GUARD")
        self.client = api_client(self.registrar)
        self.student = make_student("218001234", national_id="1199012345678")
        self.device = make_device(self.student, "DL99887766", status=DeviceStatus.PENDING)

    def test_pending_queue_lists_submissions_oldest_first(self):
        response = self.client.get("/api/devices/pending/")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["count"], 1)

    def test_approving_puts_it_on_the_register_and_clears_the_block(self):
        response = self.client.post(
            f"/api/devices/{self.device.id}/approve/", {"asset_tag": "UNI-00042"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.ACTIVE)
        self.assertEqual(self.device.asset_tag, "UNI-00042")
        self.assertFalse(self.device.is_blocked)
        self.assertEqual(self.device.registered_by, self.registrar)

    def test_approving_can_skip_the_asset_tag(self):
        response = self.client.post(f"/api/devices/{self.device.id}/approve/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.ACTIVE)
        self.assertIsNone(self.device.asset_tag)

    def test_approval_records_the_evidence_checked(self):
        """FR 2.4: what the officer checked is stored with who checked it."""
        response = self.client.post(
            f"/api/devices/{self.device.id}/approve/",
            {
                "evidence": {
                    "identity_checked": True,
                    "device_unlocked": True,
                    "serial_matches": True,
                    "proof_of_purchase_seen": False,
                    "notes": "Receipt left at home; loan form seen instead.",
                }
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        evidence = ApprovalEvidence.objects.get(device=self.device)
        self.assertTrue(evidence.identity_checked)
        self.assertTrue(evidence.device_unlocked)
        self.assertTrue(evidence.serial_matches)
        self.assertFalse(evidence.proof_of_purchase_seen)
        self.assertEqual(evidence.checks_passed, 3)
        self.assertEqual(evidence.recorded_by, self.registrar)

        detail = self.client.get(f"/api/devices/{self.device.id}/").json()
        self.assertEqual(detail["approval_evidence"]["notes"], evidence.notes)
        self.assertTrue(detail["approval_evidence"]["serial_matches"])

    def test_approval_without_evidence_records_every_check_as_not_done(self):
        self.client.post(f"/api/devices/{self.device.id}/approve/", {}, format="json")
        evidence = ApprovalEvidence.objects.get(device=self.device)
        self.assertEqual(evidence.checks_passed, 0)

    def test_a_duplicate_asset_tag_is_refused(self):
        make_device(self.student, "LN11112222", asset_tag="UNI-00042")
        response = self.client.post(
            f"/api/devices/{self.device.id}/approve/", {"asset_tag": "UNI-00042"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_rejecting_needs_a_reason_and_archives_the_submission(self):
        blank = self.client.post(f"/api/devices/{self.device.id}/reject/", {}, format="json")
        self.assertEqual(blank.status_code, 400)

        response = self.client.post(
            f"/api/devices/{self.device.id}/reject/",
            {"reason": "Serial does not match the sticker on the machine."},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.device.refresh_from_db()
        self.assertTrue(self.device.is_archived)
        self.assertIn("Serial does not match", self.device.notes)

    def test_an_already_approved_device_cannot_be_approved_again(self):
        self.client.post(f"/api/devices/{self.device.id}/approve/", {}, format="json")
        again = self.client.post(f"/api/devices/{self.device.id}/approve/", {}, format="json")
        self.assertEqual(again.status_code, 400)

    def test_a_guard_cannot_approve_anything(self):
        response = api_client(self.guard).post(
            f"/api/devices/{self.device.id}/approve/", {}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.device.refresh_from_db()
        self.assertEqual(self.device.status, DeviceStatus.PENDING)
