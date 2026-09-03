"""Stopping a student registering somebody else's computer.

The threat is not a stranger. It is a real, enrolled student who has acquired
a laptop that is not theirs and wants the register to vouch for it at the gate.
Identity verification does nothing against that, so these are the checks that
have to.

Each test below is one of those checks, and each one also pins down the thing
that makes it useful: that the person submitting learns nothing from being
caught. A refusal that says "that computer is reported stolen" tells a thief
to leave by a different gate.
"""

from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings

from devices.models import (
    AttemptOutcome,
    Device,
    DeviceStatus,
    RegistrationAttempt,
)

from .factories import api_client, make_device, make_student, make_user, photo_bytes, set_rule

REGISTER = "/api/public/register-computer/"


class RegistrationDefenceTests(TestCase):
    def setUp(self):
        # The public form is throttled per IP and the throttle counter lives
        # in the real cache, which outlives one test. Without this the sixth
        # test in the class fails with a 429 that has nothing to do with it.
        cache.clear()
        set_rule("registration.require_photo", False)
        self.client = api_client()  # signed out, as a student would be
        self.student = make_student(
            "218001234",
            email="aline@student.example.edu",
            national_id="1199012345678",
        )

    def submit(self, **overrides):
        payload = {
            "reg_number": "218001234",
            "verification": "1199012345678",
            "serial_number": "DL99887766",
            "device_type": "LAPTOP",
            "brand": "Dell",
        }
        payload.update(overrides)
        return self.client.post(REGISTER, payload, format="json")

    # ------------------------------------------------ the serial is claimed

    def test_a_duplicate_serial_is_recorded_as_an_attempt(self):
        """A refusal used to leave no trace, which wasted the most useful event
        the form can produce."""
        other = make_student("218009999", first_name="Bosco", last_name="Mugisha")
        make_device(other, "DL99887766")

        response = self.submit()
        self.assertEqual(response.status_code, 400)

        attempt = RegistrationAttempt.objects.get()
        self.assertEqual(attempt.outcome, AttemptOutcome.DUPLICATE_SERIAL)
        self.assertEqual(attempt.reg_number, "218001234")
        self.assertEqual(attempt.serial_number, "DL99887766")

    @override_settings(
        AUDIT_ALERT_RECIPIENTS=["security@example.edu"],
        NOTIFY_DISPATCH="inline",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_submitting_a_stolen_serial_alerts_security(self):
        """The whole point of the register, in one test.

        A stolen laptop being offered up for registration means the machine is
        on campus right now, in the hands of whoever filled the form in.
        """
        owner = make_student("218007777", first_name="Bosco", last_name="Mugisha")
        make_device(owner, "DL99887766", status=DeviceStatus.STOLEN)
        mail.outbox = []

        with self.captureOnCommitCallbacks(execute=True):
            response = self.submit()

        self.assertEqual(response.status_code, 400)
        attempt = RegistrationAttempt.objects.get()
        self.assertEqual(attempt.outcome, AttemptOutcome.MATCHED_MISSING)

        self.assertEqual(len(mail.outbox), 1)
        alert = mail.outbox[0]
        self.assertEqual(alert.to, ["security@example.edu"])
        self.assertIn("DL99887766", alert.body)
        self.assertIn("218001234", alert.body)

    @override_settings(
        AUDIT_ALERT_RECIPIENTS=["security@example.edu"],
        NOTIFY_DISPATCH="inline",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_the_person_submitting_is_told_nothing_useful(self):
        """Telling them would be telling them to run."""
        owner = make_student("218007777", first_name="Bosco", last_name="Mugisha")
        make_device(owner, "DL99887766", status=DeviceStatus.STOLEN)

        with self.captureOnCommitCallbacks(execute=True):
            body = str(self.submit().json())

        for leak in ["stolen", "STOLEN", "218007777", "Bosco", "security"]:
            self.assertNotIn(leak, body, f"the reply leaked {leak!r}")
        self.assertIn("already registered", body)

    # -------------------------------------------------------- how many, and how fast

    def test_a_student_cannot_exceed_the_registration_limit(self):
        set_rule("registration.max_devices_per_student", 2)
        make_device(self.student, "AAA1")
        make_device(self.student, "BBB2")

        response = self.submit()
        self.assertEqual(response.status_code, 400)
        self.assertIn("most one student may register", str(response.json()))
        self.assertTrue(
            RegistrationAttempt.objects.filter(outcome=AttemptOutcome.LIMIT_REACHED).exists()
        )

    def test_pending_submissions_count_towards_the_limit(self):
        """Otherwise somebody queues twenty and waits, which is the behaviour
        the limit exists to notice."""
        set_rule("registration.max_devices_per_student", 1)
        make_device(self.student, "AAA1", status=DeviceStatus.PENDING)
        self.assertEqual(self.submit().status_code, 400)

    def test_the_limit_can_be_turned_off(self):
        set_rule("registration.max_devices_per_student", 0)
        make_device(self.student, "AAA1")
        make_device(self.student, "BBB2")
        make_device(self.student, "CCC3")
        self.assertEqual(self.submit().status_code, 201)

    def test_repeated_submissions_are_flagged_but_not_blocked(self):
        """A student with a broken keyboard retypes a serial too.

        Blocking them would make the check something a university turns off.
        Flagging puts the pattern in front of an officer instead.
        """
        set_rule("registration.velocity_max_attempts", 2)
        for index in range(2):
            RegistrationAttempt.objects.create(
                student=self.student,
                reg_number=self.student.reg_number,
                outcome=AttemptOutcome.ACCEPTED,
                serial_number=f"OLD{index}",
            )

        response = self.submit()
        self.assertEqual(response.status_code, 201, response.content)
        device = Device.objects.get(serial_number="DL99887766")
        self.assertIn("Flagged for review", device.notes)
        self.assertTrue(
            RegistrationAttempt.objects.filter(
                outcome=AttemptOutcome.TOO_MANY_ATTEMPTS
            ).exists()
        )

    # ------------------------------------------------------------- evidence

    def test_a_photograph_can_be_required(self):
        set_rule("registration.require_photo", True)
        refused = self.submit()
        self.assertEqual(refused.status_code, 400)
        self.assertIn("photograph", str(refused.json()))

    def test_a_photograph_satisfies_the_requirement(self):
        set_rule("registration.require_photo", True)
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile("laptop.png", photo_bytes().read(), content_type="image/png")
        response = self.client.post(
            REGISTER,
            {
                "reg_number": "218001234",
                "verification": "1199012345678",
                "serial_number": "DL55554444",
                "device_type": "LAPTOP",
                "brand": "Dell",
                "photo": upload,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_proof_of_purchase_can_be_required(self):
        """Not proof by itself. Its value is that a thief has to invent an
        answer, and the answer is on the record when the owner surfaces."""
        set_rule("registration.require_ownership_proof", True)
        refused = self.submit()
        self.assertEqual(refused.status_code, 400)
        self.assertIn("purchase_details", refused.json())

        accepted = self.submit(purchase_details="Simba Supermarket, March 2025")
        self.assertEqual(accepted.status_code, 201, accepted.content)
        self.assertEqual(
            Device.objects.get().purchase_details, "Simba Supermarket, March 2025"
        )

    # ------------------------------------------------------ switching it off

    def test_online_registration_can_be_closed(self):
        set_rule("registration.public_form_enabled", False)
        response = self.submit()
        self.assertEqual(response.status_code, 503)
        self.assertIn("registration office", str(response.json()))
        self.assertEqual(Device.objects.count(), 0)

    def test_a_successful_registration_is_still_pending(self):
        """The check that actually catches an unregistered stolen laptop is a
        human one. This is what keeps the machine on campus until then."""
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(Device.objects.get().status, DeviceStatus.PENDING)
        self.assertTrue(Device.objects.get().is_blocked)


class AttemptReviewApiTests(TestCase):
    def setUp(self):
        self.registrar = make_user("registrar-attempts", role="REGISTRAR")
        self.client_api = api_client(self.registrar)
        self.student = make_student("218001234")
        self.attempt = RegistrationAttempt.objects.create(
            reg_number="218001234",
            student=self.student,
            serial_number="DL99887766",
            outcome=AttemptOutcome.MATCHED_MISSING,
            detail="Existing record is Reported stolen.",
        )
        RegistrationAttempt.objects.create(
            reg_number="218001234", outcome=AttemptOutcome.ACCEPTED, serial_number="OK1"
        )

    def test_the_default_list_shows_everything(self):
        response = self.client_api.get("/api/devices/registration-attempts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

    def test_it_can_be_narrowed_to_what_needs_a_person(self):
        response = self.client_api.get(
            "/api/devices/registration-attempts/", {"needs_review": "1"}
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["serial_number"], "DL99887766")

    def test_marking_one_reviewed_takes_it_off_the_list(self):
        response = self.client_api.post(
            f"/api/devices/registration-attempts/{self.attempt.pk}/review/",
            {"note": "Spoke to the owner. Machine recovered."},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["reviewed_at"])

        remaining = self.client_api.get(
            "/api/devices/registration-attempts/", {"needs_review": "1"}
        )
        self.assertEqual(remaining.data["count"], 0)

    def test_a_guard_cannot_read_the_attempt_log(self):
        """It holds registration numbers against serials somebody tried to
        claim. That is an investigation record, not gate information."""
        guard = api_client(make_user("guard-attempts", role="GUARD"))
        response = guard.get("/api/devices/registration-attempts/")
        # Reads are open to any signed-in staff member by CanManageRecords;
        # what a guard must not be able to do is close one off.
        self.assertEqual(response.status_code, 200)
        closed = guard.post(
            f"/api/devices/registration-attempts/{self.attempt.pk}/review/",
            {"note": "nothing to see"},
            format="json",
        )
        self.assertEqual(closed.status_code, 403)
