"""Audit retention, unusual-activity alerting, and two-factor for admins."""

from datetime import timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import TOTP

from accounts import twofactor
from accounts.alerting import find_unusual_activity, raise_alerts
from accounts.audit import AccessLog, AuditAction
from notifications.models import Kind, Notification

from .factories import api_client, make_student, make_user

TWO_FACTOR = "/api/auth/two-factor/"
LOGIN = "/api/auth/login/"


def write_log(user, count, when):
    AccessLog.objects.bulk_create(
        [
            AccessLog(
                user=user,
                username=user.username,
                action=AuditAction.GATE_LOOKUP,
                query="218001234",
            )
            for _ in range(count)
        ]
    )
    # created_at is auto_now_add, so it has to be moved afterwards.
    AccessLog.objects.filter(user=user, created_at__gt=when).update(created_at=when)


class RetentionTests(TestCase):
    def setUp(self):
        self.guard = make_user("guard1", role="GUARD")
        now = timezone.now()
        # 5 ancient, 3 middle-aged, 20 fresh - so a normal prune removes a
        # minority and does not collide with the safety check.
        write_log(self.guard, 5, now - timedelta(days=400))
        write_log(self.guard, 3, now - timedelta(days=40))
        write_log(self.guard, 20, now - timedelta(hours=2))

    def run_prune(self, *args):
        out = StringIO()
        call_command("prune_audit_log", *args, stdout=out, stderr=out)
        return out.getvalue()

    def test_dry_run_reports_but_deletes_nothing(self):
        output = self.run_prune("--dry-run")
        self.assertIn("Would delete 5", output)
        self.assertEqual(AccessLog.objects.count(), 28)

    def test_it_deletes_only_entries_past_the_retention_period(self):
        self.run_prune()
        self.assertEqual(AccessLog.objects.count(), 23)

    def test_the_period_can_be_overridden(self):
        self.run_prune("--days", "30")
        # Now the 40-day-old batch goes too.
        self.assertEqual(AccessLog.objects.count(), 20)

    @override_settings(AUDIT_RETENTION_DAYS=30)
    def test_it_honours_the_setting(self):
        self.run_prune()
        self.assertEqual(AccessLog.objects.count(), 20)

    def test_nothing_to_do_is_reported_cleanly(self):
        self.run_prune()
        self.assertIn("Nothing to prune", self.run_prune())

    def test_a_retention_of_zero_is_rejected(self):
        self.run_prune("--days", "0")
        self.assertEqual(AccessLog.objects.count(), 28)


class RetentionSafetyTests(TestCase):
    """A bad --days must not silently destroy the one record of who looked."""

    def setUp(self):
        self.guard = make_user("guard1", role="GUARD")
        # Everything is old, so any short retention would wipe the lot.
        write_log(self.guard, 30, timezone.now() - timedelta(days=400))

    def run_prune(self, *args):
        out = StringIO()
        call_command("prune_audit_log", *args, stdout=out, stderr=out)
        return out.getvalue()

    def test_it_refuses_to_wipe_almost_everything(self):
        output = self.run_prune("--days", "1")
        self.assertIn("Refusing", output)
        self.assertIn("100%", output)
        self.assertEqual(AccessLog.objects.count(), 30)

    def test_force_overrides_the_safety_check(self):
        self.run_prune("--days", "1", "--force")
        self.assertEqual(AccessLog.objects.count(), 0)

    def test_a_dry_run_still_reports_without_the_refusal(self):
        output = self.run_prune("--days", "1", "--dry-run")
        self.assertIn("Would delete 30", output)
        self.assertEqual(AccessLog.objects.count(), 30)


@override_settings(
    AUDIT_ALERT_RECIPIENTS=["security@university.edu"],
    AUDIT_ALERT_FLOOR=50,
    AUDIT_ALERT_MULTIPLIER=5.0,
    NOTIFY_DISPATCH="inline",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AlertingTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.busy = make_user("guard1", role="GUARD")
        self.normal = make_user("guard2", role="GUARD")
        self.now = timezone.now()

    def test_a_steady_heavy_user_does_not_alert(self):
        """The main gate guard is always busy - that is not a signal."""
        write_log(self.busy, 300, self.now - timedelta(hours=2))
        for day in range(1, 15):
            write_log(self.busy, 300, self.now - timedelta(days=day))
        self.assertEqual(find_unusual_activity(), [])

    def test_a_sudden_spike_alerts(self):
        for day in range(1, 15):
            write_log(self.busy, 20, self.now - timedelta(days=day))
        write_log(self.busy, 400, self.now - timedelta(hours=2))

        findings = find_unusual_activity()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["username"], "guard1")
        self.assertGreater(findings[0]["ratio"], 5)

    def test_low_volume_never_alerts_however_unusual(self):
        """Three lookups from a new account is not worth an email."""
        write_log(self.normal, 10, self.now - timedelta(hours=1))
        self.assertEqual(find_unusual_activity(), [])

    def test_an_alert_is_queued_to_the_security_office(self):
        write_log(self.busy, 400, self.now - timedelta(hours=1))
        raised = raise_alerts()
        self.assertEqual(len(raised), 1)

        notification = Notification.objects.get()
        self.assertEqual(notification.kind, Kind.AUDIT_ALERT)
        self.assertEqual(notification.recipient, "security@university.edu")
        self.assertIn("guard1", notification.body)
        # It must not read as an accusation.
        self.assertIn("not evidence of anything", notification.body)

    def test_the_same_account_is_not_alerted_repeatedly(self):
        write_log(self.busy, 400, self.now - timedelta(hours=1))
        self.assertEqual(len(raise_alerts()), 1)
        self.assertEqual(len(raise_alerts()), 0)
        self.assertEqual(Notification.objects.count(), 1)

    @override_settings(AUDIT_ALERT_RECIPIENTS=[])
    def test_with_no_recipients_it_does_nothing_rather_than_crash(self):
        write_log(self.busy, 400, self.now - timedelta(hours=1))
        self.assertEqual(raise_alerts(), [])
        self.assertEqual(Notification.objects.count(), 0)

    def test_the_command_dry_run_sends_nothing(self):
        write_log(self.busy, 400, self.now - timedelta(hours=1))
        out = StringIO()
        call_command("check_audit_alerts", "--dry-run", stdout=out, stderr=out)
        self.assertIn("guard1", out.getvalue())
        self.assertEqual(Notification.objects.count(), 0)


class TwoFactorTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", role="ADMIN")
        self.guard = make_user("guard1", role="GUARD")
        self.client = api_client(self.admin)

    def code_for(self, user, step_offset=0):
        """A valid TOTP code, optionally for a later time step.

        django-otp refuses a code whose time step is not newer than the last
        one accepted - replay protection. Enrolment therefore consumes the
        current step, and a subsequent login has to use the next one. Real
        users experience this as "wait for the number to change".
        """
        device = twofactor.get_device(user)
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits)
        totp.time = timezone.now().timestamp() + step_offset * device.step
        return str(totp.token()).zfill(device.digits)

    def enrol(self, user):
        client = api_client(user)
        client.post(TWO_FACTOR)
        return client.put(TWO_FACTOR, {"token": self.code_for(user)}, format="json")

    # ---- enrolment ----

    def test_setup_returns_a_qr_code_and_a_typeable_secret(self):
        response = self.client.post(TWO_FACTOR)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertTrue(body["qr_png_base64"].startswith("data:image/png;base64,"))
        self.assertTrue(body["secret"])
        self.assertIn("otpauth://totp/", body["otpauth_url"])

    def test_a_device_is_not_armed_until_a_valid_code_is_given(self):
        self.client.post(TWO_FACTOR)
        self.assertFalse(twofactor.has_2fa(self.admin))
        self.assertTrue(TOTPDevice.objects.filter(user=self.admin, confirmed=False).exists())

    def test_a_wrong_code_does_not_arm_it(self):
        self.client.post(TWO_FACTOR)
        response = self.client.put(TWO_FACTOR, {"token": "000000"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(twofactor.has_2fa(self.admin))

    def test_after_a_wrong_code_the_lockout_is_explained_not_disguised(self):
        """django-otp briefly locks the device after a failure.

        Reporting that as "wrong code" would send someone off resetting an
        authenticator app that was working perfectly well.
        """
        self.client.post(TWO_FACTOR)
        self.client.put(TWO_FACTOR, {"token": "000000"}, format="json")

        # A correct code, immediately afterwards, is still refused - but the
        # message has to say why.
        response = self.client.put(
            TWO_FACTOR, {"token": self.code_for(self.admin)}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("locked", str(response.json()).lower())
        self.assertFalse(twofactor.has_2fa(self.admin))

    def test_the_lockout_lifts_and_the_same_code_then_works(self):
        device_setup = self.client.post(TWO_FACTOR)
        self.assertEqual(device_setup.status_code, 201)
        self.client.put(TWO_FACTOR, {"token": "000000"}, format="json")

        # Rewind the throttle timestamp rather than sleeping in a test.
        device = twofactor.get_device(self.admin, confirmed=False)
        device.throttling_failure_timestamp = timezone.now() - timedelta(minutes=5)
        device.save(update_fields=["throttling_failure_timestamp"])

        response = self.client.put(
            TWO_FACTOR, {"token": self.code_for(self.admin)}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(twofactor.has_2fa(self.admin))

    def test_confirming_with_a_real_code_turns_it_on(self):
        response = self.enrol(self.admin)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(twofactor.has_2fa(self.admin))

    def test_status_reflects_the_state(self):
        self.assertFalse(self.client.get(TWO_FACTOR).json()["enabled"])
        self.enrol(self.admin)
        body = self.client.get(TWO_FACTOR).json()
        self.assertTrue(body["enabled"])
        self.assertTrue(body["required_at_login"])

    def test_the_profile_reports_it(self):
        self.enrol(self.admin)
        self.assertTrue(self.client.get("/api/auth/me/").json()["two_factor_enabled"])

    # ---- login enforcement ----

    def test_login_without_a_code_is_refused_once_enrolled(self):
        self.enrol(self.admin)
        response = api_client().post(
            LOGIN, {"username": "admin", "password": "passw0rd!"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()["otp_required"])

    def test_login_with_a_valid_code_succeeds(self):
        self.enrol(self.admin)
        response = api_client().post(
            LOGIN,
            {
                "username": "admin",
                "password": "passw0rd!",
                # Next time step: enrolment already used the current one.
                "otp_token": self.code_for(self.admin, step_offset=1),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access", response.json())

    def test_a_wrong_code_is_refused(self):
        self.enrol(self.admin)
        response = api_client().post(
            LOGIN,
            {"username": "admin", "password": "passw0rd!", "otp_token": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_a_wrong_password_never_reveals_that_2fa_is_on(self):
        """Otherwise the login form leaks which accounts are worth attacking."""
        self.enrol(self.admin)
        response = api_client().post(
            LOGIN, {"username": "admin", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("otp_required", str(response.json()))

    def test_a_code_cannot_be_replayed(self):
        """Someone who shoulder-surfs a code cannot reuse it seconds later."""
        self.enrol(self.admin)
        code = self.code_for(self.admin, step_offset=1)
        first = api_client().post(
            LOGIN, {"username": "admin", "password": "passw0rd!", "otp_token": code}, format="json"
        )
        self.assertEqual(first.status_code, 200, first.content)
        second = api_client().post(
            LOGIN, {"username": "admin", "password": "passw0rd!", "otp_token": code}, format="json"
        )
        self.assertEqual(second.status_code, 400)

    def test_an_admin_without_2fa_can_still_sign_in(self):
        """It rolls out account by account, not all at once."""
        response = api_client().post(
            LOGIN, {"username": "admin", "password": "passw0rd!"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_guards_are_unaffected(self):
        self.assertFalse(twofactor.is_required_for(self.guard))
        response = api_client().post(
            LOGIN, {"username": "guard1", "password": "passw0rd!"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)

    # ---- turning it off ----

    def test_disabling_needs_the_password(self):
        self.enrol(self.admin)
        refused = self.client.delete(TWO_FACTOR, {"password": "wrong"}, format="json")
        self.assertEqual(refused.status_code, 400)
        self.assertTrue(twofactor.has_2fa(self.admin))

        allowed = self.client.delete(TWO_FACTOR, {"password": "passw0rd!"}, format="json")
        self.assertEqual(allowed.status_code, 200, allowed.content)
        self.assertFalse(twofactor.has_2fa(self.admin))

    def test_one_admin_cannot_disable_another_admins_second_factor(self):
        other = make_user("admin2", role="ADMIN")
        self.enrol(other)
        # The endpoint only ever acts on the caller, so this turns off nothing
        # belonging to `other`.
        self.client.delete(TWO_FACTOR, {"password": "passw0rd!"}, format="json")
        self.assertTrue(twofactor.has_2fa(other))
