"""CSV import, exit notifications and per-account lookup limits."""

import io
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.throttling import UserRateThrottle

from campus.models import Department
from checkpoint.models import ScanEvent
from notifications.models import Channel, Kind, Notification, Status
from students.models import Student

from .factories import api_client, make_device, make_gate, make_student, make_user

PREVIEW = "/api/students/import-preview/"
COMMIT = "/api/students/import-commit/"

HEADER = "reg_number,first_name,last_name,email,department,year_of_study\n"


def csv_file(body, name="students.csv"):
    return SimpleUploadedFile(name, body.encode("utf-8"), content_type="text/csv")


class CsvImportTests(TestCase):
    def setUp(self):
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.guard = make_user("guard1", role="GUARD")
        self.client = api_client(self.registrar)
        Department.objects.create(name="Computer Science", code="CS")

    def preview(self, body):
        return self.client.post(PREVIEW, {"file": csv_file(body)}, format="multipart")

    def commit(self, body, **extra):
        return self.client.post(COMMIT, {"file": csv_file(body), **extra}, format="multipart")

    def test_preview_reports_what_would_happen_and_writes_nothing(self):
        body = HEADER + "218001234,Aline,Uwase,a@u.edu,CS,2\n218009999,Bosco,Mugisha,b@u.edu,CS,3\n"
        response = self.preview(body)
        self.assertEqual(response.status_code, 200, response.content)
        summary = response.json()["summary"]
        self.assertEqual(summary["to_create"], 2)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(Student.objects.count(), 0)

    def test_commit_creates_the_students(self):
        body = HEADER + "218001234,Aline,Uwase,a@u.edu,CS,2\n"
        response = self.commit(body)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["created"], 1)
        student = Student.objects.get()
        self.assertEqual(student.reg_number, "218001234")
        self.assertEqual(student.department.code, "CS")
        self.assertEqual(student.year_of_study, 2)

    def test_imported_students_are_immediately_searchable(self):
        """bulk_create would skip the signals that maintain the index."""
        self.commit(HEADER + "218001234,Aline,Uwase,a@u.edu,CS,2\n")
        found = self.client.get("/api/students/", {"search": "uwase"}).json()
        self.assertEqual(found["count"], 1)

    def test_a_second_import_updates_rather_than_duplicates(self):
        self.commit(HEADER + "218001234,Aline,Uwase,a@u.edu,CS,2\n")
        self.commit(HEADER + "218 001 234,Aline,Uwase-Keza,new@u.edu,CS,3\n")
        self.assertEqual(Student.objects.count(), 1)
        student = Student.objects.get()
        self.assertEqual(student.last_name, "Uwase-Keza")
        self.assertEqual(student.year_of_study, 3)

    def test_blank_cells_do_not_erase_existing_data(self):
        self.commit(HEADER + "218001234,Aline,Uwase,keep@u.edu,CS,2\n")
        self.commit(HEADER + "218001234,Aline,Uwase,,CS,2\n")
        self.assertEqual(Student.objects.get().email, "keep@u.edu")

    def test_updates_can_be_turned_off(self):
        self.commit(HEADER + "218001234,Aline,Uwase,a@u.edu,CS,2\n")
        response = self.commit(
            HEADER + "218001234,Changed,Name,x@u.edu,CS,4\n", update_existing="false"
        )
        self.assertEqual(response.json()["updated"], 0)
        self.assertEqual(Student.objects.get().first_name, "Aline")

    def test_bad_rows_are_reported_with_their_line_numbers(self):
        body = HEADER + (
            "218001234,Aline,Uwase,a@u.edu,CS,2\n"
            ",Missing,Reg,c@u.edu,CS,1\n"
            "218007777,No,Dept,d@u.edu,ZZZ,1\n"
            "218008888,Bad,Year,e@u.edu,CS,99\n"
        )
        errors = self.preview(body).json()["errors"]
        self.assertEqual(len(errors), 3)
        lines = {error["line"] for error in errors}
        self.assertEqual(lines, {3, 4, 5})
        self.assertIn("ZZZ", str(errors))

    def test_duplicate_rows_inside_one_file_are_caught(self):
        body = HEADER + "218001234,A,One,a@u.edu,CS,1\n218-001-234,A,Two,b@u.edu,CS,1\n"
        errors = self.preview(body).json()["errors"]
        self.assertEqual(len(errors), 1)
        self.assertIn("Duplicate of line 2", str(errors))

    def test_alternative_header_spellings_are_accepted(self):
        body = "Registration Number,Surname,First Name\n218001234,Uwase,Aline\n"
        response = self.preview(body)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["summary"]["to_create"], 1)

    def test_a_file_missing_required_columns_is_rejected(self):
        response = self.preview("email,phone\na@u.edu,0788\n")
        self.assertEqual(response.status_code, 400)
        self.assertIn("reg_number", str(response.json()))

    def test_a_non_utf8_file_is_rejected_clearly(self):
        upload = SimpleUploadedFile("s.csv", b"\xff\xfe\x00bad", content_type="text/csv")
        response = self.client.post(PREVIEW, {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("UTF-8", str(response.json()))

    def test_a_guard_cannot_import(self):
        response = api_client(self.guard).post(
            COMMIT, {"file": csv_file(HEADER + "218001234,A,B,a@u.edu,CS,1\n")}, format="multipart"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Student.objects.count(), 0)

    def test_a_failing_row_rolls_the_whole_import_back(self):
        body = HEADER + "218001234,Aline,Uwase,a@u.edu,CS,2\n218009999,Bosco,Mugisha,b@u.edu,CS,3\n"
        with patch(
            "students.importer.Student.objects.create", side_effect=[None, RuntimeError("boom")]
        ):
            with self.assertRaises(RuntimeError):
                self.commit(body)
        self.assertEqual(Student.objects.count(), 0)


@override_settings(
    NOTIFY_ON_EXIT=True,
    NOTIFY_DISPATCH="inline",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SMS_BACKEND="notifications.backends.NullSMSBackend",
    UNIVERSITY_NAME="Test University",
)
class ExitNotificationTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.gate = make_gate()
        self.guard = make_user("guard1", role="GUARD", default_gate=self.gate)
        self.client = api_client(self.guard)
        self.student = make_student("218001234", email="aline@student.university.edu")
        self.device = make_device(self.student, "HP12345678")

    def scan(self, **overrides):
        payload = {
            "device": self.device.id,
            "gate": self.gate.id,
            "direction": "OUT",
            "verdict": "ALLOWED",
        }
        payload.update(overrides)
        # Inline dispatch deliberately runs on transaction.on_commit, so a
        # rolled-back scan sends nothing. TestCase wraps each test in a
        # transaction that never commits, so the callbacks have to be run here.
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post("/api/checkpoint/scans/", payload, format="json")

    def test_the_owner_is_emailed_when_their_computer_leaves(self):
        self.assertEqual(self.scan().status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["aline@student.university.edu"])
        self.assertIn("HP12345678", message.body)
        self.assertIn("Main Gate", message.body)
        self.assertIn("Test University", message.body)

    def test_entering_campus_is_not_announced(self):
        self.scan(direction="IN")
        self.assertEqual(mail.outbox, [])

    def test_a_denial_is_not_announced(self):
        self.scan(verdict="DENIED")
        self.assertEqual(mail.outbox, [])

    def test_an_override_is_announced(self):
        self.device.status = "STOLEN"
        self.device.save()
        self.scan(verdict="OVERRIDE", override_reason="Cleared by control.")
        self.assertEqual(len(mail.outbox), 1)

    def test_a_student_with_no_email_is_simply_skipped(self):
        self.student.email = ""
        self.student.save()
        self.assertEqual(self.scan().status_code, 201)
        self.assertEqual(mail.outbox, [])

    def test_a_mail_failure_never_fails_the_scan(self):
        """The gate record is what matters; the notification is best effort."""
        with patch("notifications.backends.send_mail", side_effect=RuntimeError("smtp down")):
            response = self.scan()
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(ScanEvent.objects.count(), 1)

    def test_a_failed_send_is_kept_for_retry_not_lost(self):
        with patch("notifications.backends.send_mail", side_effect=RuntimeError("smtp down")):
            self.scan()
        row = Notification.objects.get()
        # Still PENDING, because attempts remain - the worker will try again.
        self.assertEqual(row.status, Status.PENDING)
        self.assertEqual(row.attempts, 1)
        self.assertIn("smtp down", row.last_error)

    def test_it_gives_up_after_repeated_failures(self):
        from notifications.service import MAX_ATTEMPTS, dispatch_pending

        with patch("notifications.backends.send_mail", side_effect=RuntimeError("smtp down")):
            self.scan()
            for _ in range(MAX_ATTEMPTS):
                dispatch_pending()
        row = Notification.objects.get()
        self.assertEqual(row.status, Status.FAILED)
        self.assertGreaterEqual(row.attempts, MAX_ATTEMPTS)

    def test_a_recovered_mail_server_sends_the_queued_message(self):
        from notifications.service import dispatch_pending

        with patch("notifications.backends.send_mail", side_effect=RuntimeError("smtp down")):
            self.scan()
        self.assertEqual(mail.outbox, [])

        dispatch_pending()  # mail server is back
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notification.objects.get().status, Status.SENT)

    @override_settings(NOTIFY_ON_EXIT=False)
    def test_notifications_can_be_switched_off(self):
        self.scan()
        self.assertEqual(mail.outbox, [])
        self.assertEqual(Notification.objects.count(), 0)

    def test_sms_backend_is_called_when_a_phone_is_on_file(self):
        self.student.phone = "+250788000000"
        self.student.save()
        with patch("notifications.backends.get_sms_backend") as backend:
            backend.return_value.send.return_value = True
            self.scan()
            backend.return_value.send.assert_called_once()
            to, message = backend.return_value.send.call_args[0]
            self.assertEqual(to, "+250788000000")
            self.assertIn("HP12345678", message)


@override_settings(
    NOTIFY_DISPATCH="worker",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SMS_BACKEND="notifications.backends.NullSMSBackend",
)
class OutboxTests(TestCase):
    """The whole point: sending is not on the request path."""

    def setUp(self):
        mail.outbox = []
        self.gate = make_gate()
        self.guard = make_user("guard1", role="GUARD", default_gate=self.gate)
        self.client = api_client(self.guard)
        self.student = make_student("218001234", email="aline@student.university.edu")
        self.device = make_device(self.student, "HP12345678")

    def scan(self):
        return self.client.post(
            "/api/checkpoint/scans/",
            {
                "device": self.device.id,
                "gate": self.gate.id,
                "direction": "OUT",
                "verdict": "ALLOWED",
            },
            format="json",
        )

    def test_the_request_queues_but_does_not_send(self):
        self.assertEqual(self.scan().status_code, 201)
        self.assertEqual(Notification.objects.filter(status=Status.PENDING).count(), 1)
        # Nothing went out during the request - no SMTP on the gate's path.
        self.assertEqual(mail.outbox, [])

    def test_the_worker_command_drains_the_outbox(self):
        from django.core.management import call_command

        self.scan()
        call_command("process_notifications", verbosity=0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notification.objects.get().status, Status.SENT)

    def test_the_worker_is_idempotent(self):
        from django.core.management import call_command

        self.scan()
        call_command("process_notifications", verbosity=0)
        call_command("process_notifications", verbosity=0)
        self.assertEqual(len(mail.outbox), 1)

    def test_retry_failed_resets_and_resends(self):
        from django.core.management import call_command
        from notifications.service import MAX_ATTEMPTS, dispatch_pending

        with patch("notifications.backends.send_mail", side_effect=RuntimeError("down")):
            self.scan()
            for _ in range(MAX_ATTEMPTS):
                dispatch_pending()
        self.assertEqual(Notification.objects.get().status, Status.FAILED)

        call_command("process_notifications", "--retry-failed", verbosity=0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Notification.objects.get().status, Status.SENT)


@override_settings(
    NOTIFY_DISPATCH="inline",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SMS_BACKEND="notifications.backends.NullSMSBackend",
    UNIVERSITY_NAME="Test University",
)
class ApprovalNotificationTests(TestCase):
    """A student should be told the outcome, not have to keep checking."""

    def setUp(self):
        mail.outbox = []
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.client = api_client(self.registrar)
        self.student = make_student("218001234", email="aline@student.university.edu")
        self.device = make_device(self.student, "DL99887766", status="PENDING")

    def act(self, path, payload):
        # See the note in ExitNotificationTests.scan about on_commit.
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(path, payload, format="json")

    def test_approval_emails_the_owner(self):
        response = self.act(
            f"/api/devices/{self.device.id}/approve/", {"asset_tag": "UNI-00042"}
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["owner_notified"])
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("approved", body.lower())
        self.assertIn("DL99887766", body)
        self.assertIn("UNI-00042", body)
        self.assertEqual(Notification.objects.get().kind, Kind.APPROVED)

    def test_rejection_emails_the_owner_with_the_reason(self):
        response = self.act(
            f"/api/devices/{self.device.id}/reject/",
            {"reason": "Serial does not match the sticker."},
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Serial does not match the sticker.", mail.outbox[0].body)
        self.assertEqual(Notification.objects.get().kind, Kind.REJECTED)

    def test_a_student_with_no_contact_details_is_handled_quietly(self):
        self.student.email = ""
        self.student.phone = ""
        self.student.save()
        response = self.act(f"/api/devices/{self.device.id}/approve/", {})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(response.json()["owner_notified"])
        self.assertEqual(Notification.objects.count(), 0)

    def test_both_channels_are_queued_when_both_are_on_file(self):
        self.student.phone = "+250788000000"
        self.student.save()
        self.act(f"/api/devices/{self.device.id}/approve/", {})
        channels = set(Notification.objects.values_list("channel", flat=True))
        self.assertEqual(channels, {Channel.EMAIL, Channel.SMS})


class LookupThrottleTests(TestCase):
    """One guard login must not be able to walk the whole register."""

    def setUp(self):
        cache.clear()
        self.guard = make_user("guard1", role="GUARD")
        self.admin = make_user("admin", role="ADMIN")
        make_student("218001234")

    def tearDown(self):
        cache.clear()

    def test_a_guard_hits_the_burst_ceiling(self):
        client = api_client(self.guard)
        with patch.dict(UserRateThrottle.THROTTLE_RATES, {"lookup-burst": "3/min"}):
            codes = [
                client.get("/api/checkpoint/lookup/", {"q": "218001234"}).status_code
                for _ in range(5)
            ]
        self.assertEqual(codes.count(429), 2, codes)

    def test_the_limit_is_per_account_not_shared(self):
        guard_client = api_client(self.guard)
        other = api_client(make_user("guard2", role="GUARD"))
        with patch.dict(UserRateThrottle.THROTTLE_RATES, {"lookup-burst": "2/min"}):
            for _ in range(3):
                guard_client.get("/api/checkpoint/lookup/", {"q": "218001234"})
            # A different guard still has their own full budget.
            fresh = other.get("/api/checkpoint/lookup/", {"q": "218001234"})
        self.assertEqual(fresh.status_code, 200)

    def test_admins_are_exempt_from_the_daily_ceiling(self):
        client = api_client(self.admin)
        with patch.dict(UserRateThrottle.THROTTLE_RATES, {"lookup-daily": "2/day"}):
            codes = [
                client.get("/api/checkpoint/lookup/", {"q": "218001234"}).status_code
                for _ in range(4)
            ]
        self.assertNotIn(429, codes, codes)

    def test_the_typeahead_carries_the_same_ceiling(self):
        client = api_client(self.guard)
        with patch.dict(UserRateThrottle.THROTTLE_RATES, {"lookup-burst": "2/min"}):
            codes = [
                client.get("/api/search/suggest/", {"q": "218"}).status_code for _ in range(4)
            ]
        self.assertIn(429, codes, codes)
