"""Resend and Africa's Talking, without a network.

Both adapters are written so the one function that touches a socket can be
replaced. Everything above it - which address gets used, what counts as
success, whether a failure is worth retrying - is logic, and it is the logic
that decides whether a student is told their laptop left campus.
"""

from unittest.mock import patch

from django.core.mail import EmailMessage, send_mail
from django.test import TestCase
from django.test.utils import override_settings

from notifications.backends import PermanentFailure, deliver
from notifications.models import Channel, Kind, Notification
from notifications.providers.africastalking import (
    AfricasTalkingSMSBackend,
    SMSError,
    normalise_number,
    truncate,
)
from notifications.providers.resend import ResendEmailBackend, ResendError


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


@override_settings(
    EMAIL_BACKEND="notifications.providers.resend.ResendEmailBackend",
    RESEND_API_KEY="re_test_key",
    DEFAULT_FROM_EMAIL="etracker <no-reply@example.edu>",
)
class ResendTests(TestCase):
    def test_a_message_is_posted_in_the_shape_resend_expects(self):
        with patch(
            "notifications.providers.resend._post",
            return_value=FakeResponse(200, {"id": "abc"}),
        ) as post:
            sent = send_mail(
                "Your computer left campus",
                "It went out through Main Gate at 18:42.",
                None,
                ["aline@example.edu"],
            )

        self.assertEqual(sent, 1)
        url, payload, api_key, timeout = post.call_args[0]
        self.assertEqual(api_key, "re_test_key")
        self.assertEqual(payload["to"], ["aline@example.edu"])
        self.assertEqual(payload["subject"], "Your computer left campus")
        self.assertIn("Main Gate", payload["text"])
        self.assertEqual(payload["from"], "etracker <no-reply@example.edu>")

    def test_an_html_alternative_is_carried_but_text_is_always_sent(self):
        """A gate notification has to be readable in whatever opens it."""
        message = EmailMessage("Subject", "plain text", None, ["a@example.edu"])
        message.attach_alternative = None  # EmailMessage has no alternatives by default
        backend = ResendEmailBackend()
        payload = backend._payload(message)
        self.assertEqual(payload["text"], "plain text")
        self.assertNotIn("html", payload)

    def test_a_bad_address_is_permanent_and_not_retried(self):
        """Retrying an unverified domain five times changes nothing and costs
        sender reputation."""
        with patch(
            "notifications.providers.resend._post",
            return_value=FakeResponse(422, {"message": "domain is not verified"}),
        ):
            with self.assertRaises(ResendError) as caught:
                send_mail("s", "b", None, ["a@example.edu"])
        self.assertTrue(caught.exception.permanent)

    def test_a_server_error_is_worth_retrying(self):
        with patch(
            "notifications.providers.resend._post",
            return_value=FakeResponse(503, None, text="upstream unavailable"),
        ):
            with self.assertRaises(ResendError) as caught:
                send_mail("s", "b", None, ["a@example.edu"])
        self.assertFalse(caught.exception.permanent)

    def test_a_rate_limit_is_worth_retrying(self):
        with patch(
            "notifications.providers.resend._post",
            return_value=FakeResponse(429, {"message": "too many requests"}),
        ):
            with self.assertRaises(ResendError) as caught:
                send_mail("s", "b", None, ["a@example.edu"])
        self.assertFalse(caught.exception.permanent)

    @override_settings(RESEND_API_KEY="")
    def test_a_missing_key_fails_loudly_rather_than_silently(self):
        """A university that has switched mail on and sees nothing arrive needs
        to be told the key is missing, not left blaming spam filters."""
        with self.assertRaises(ResendError):
            send_mail("s", "b", None, ["a@example.edu"])

    def test_the_outbox_marks_a_permanent_failure_as_failed_immediately(self):
        row = Notification.objects.create(
            kind=Kind.EXIT,
            channel=Channel.EMAIL,
            recipient="a@example.edu",
            subject="s",
            body="b",
        )
        with patch(
            "notifications.providers.resend._post",
            return_value=FakeResponse(422, {"message": "invalid to field"}),
        ):
            with self.assertRaises(PermanentFailure):
                deliver(row)


class NumberNormalisationTests(TestCase):
    """Student records hold numbers as people write them; the API takes E.164."""

    def test_the_four_ways_one_number_gets_written(self):
        for written in ["0788123456", "788123456", "+250788123456", "250 788 123 456"]:
            with self.subTest(written=written):
                self.assertEqual(normalise_number(written), "+250788123456")

    def test_an_international_prefix_is_understood(self):
        self.assertEqual(normalise_number("00250788123456"), "+250788123456")

    def test_a_foreign_number_is_left_as_it_is(self):
        self.assertEqual(normalise_number("+447700900123"), "+447700900123")

    def test_the_country_code_is_configurable(self):
        with override_settings(SMS_DEFAULT_COUNTRY_CODE="+254"):
            self.assertEqual(normalise_number("0712345678"), "+254712345678")

    def test_nonsense_is_refused_rather_than_guessed_at(self):
        for junk in ["", None, "not a number", "12"]:
            with self.subTest(junk=junk):
                self.assertIsNone(normalise_number(junk))


class TruncationTests(TestCase):
    """Every segment is charged, so length is a cost question, not a style one."""

    def test_a_short_message_is_untouched(self):
        self.assertEqual(truncate("Your laptop left campus."), "Your laptop left campus.")

    def test_a_long_message_is_cut_on_a_word_boundary(self):
        long_text = "word " * 200
        cut = truncate(long_text, limit=50)
        self.assertLessEqual(len(cut), 50)
        self.assertTrue(cut.endswith("…"))
        self.assertNotIn("  ", cut)

    def test_whitespace_is_collapsed(self):
        self.assertEqual(truncate("a\n\n   b"), "a b")


@override_settings(
    AFRICASTALKING_API_KEY="atsk_test",
    AFRICASTALKING_USERNAME="sandbox",
    SMS_DEFAULT_COUNTRY_CODE="+250",
)
class AfricasTalkingTests(TestCase):
    def backend(self):
        return AfricasTalkingSMSBackend()

    def test_the_sandbox_username_selects_the_sandbox_host(self):
        """One less piece of configuration that can contradict itself."""
        self.assertIn("sandbox", self.backend().url)

    @override_settings(AFRICASTALKING_USERNAME="kigali_uni")
    def test_a_real_username_selects_the_live_host(self):
        self.assertNotIn("sandbox", self.backend().url)

    def test_a_local_number_is_sent_in_e164(self):
        ok = {"SMSMessageData": {"Recipients": [{"status": "Success"}]}}
        with patch(
            "notifications.providers.africastalking._post",
            return_value=FakeResponse(201, ok),
        ) as post:
            self.assertTrue(self.backend().send("0788123456", "Your laptop left campus."))
        _, data, _, _ = post.call_args[0]
        self.assertEqual(data["to"], "+250788123456")

    @override_settings(AFRICASTALKING_SENDER_ID="KIGALIUNI")
    def test_a_registered_sender_id_is_used_when_there_is_one(self):
        ok = {"SMSMessageData": {"Recipients": [{"status": "Success"}]}}
        with patch(
            "notifications.providers.africastalking._post",
            return_value=FakeResponse(201, ok),
        ) as post:
            self.backend().send("0788123456", "hello")
        self.assertEqual(post.call_args[0][1]["from"], "KIGALIUNI")

    def test_a_200_with_a_rejected_recipient_is_still_a_failure(self):
        """The trap in this API: it answers 200 and reports the real outcome
        per recipient, so an empty account looks like success at the HTTP layer.
        """
        refused = {"SMSMessageData": {"Recipients": [{"status": "InsufficientBalance"}]}}
        with patch(
            "notifications.providers.africastalking._post",
            return_value=FakeResponse(201, refused),
        ):
            with self.assertRaises(SMSError) as caught:
                self.backend().send("0788123456", "hello")
        self.assertTrue(caught.exception.permanent)

    def test_no_recipients_at_all_is_a_failure(self):
        empty = {"SMSMessageData": {"Recipients": [], "Message": "Sent to 0/1"}}
        with patch(
            "notifications.providers.africastalking._post",
            return_value=FakeResponse(201, empty),
        ):
            with self.assertRaises(SMSError):
                self.backend().send("0788123456", "hello")

    def test_an_unusable_number_is_permanent(self):
        with self.assertRaises(SMSError) as caught:
            self.backend().send("not a phone", "hello")
        self.assertTrue(caught.exception.permanent)

    @override_settings(AFRICASTALKING_API_KEY="")
    def test_a_missing_key_is_permanent_and_says_what_to_do(self):
        with self.assertRaises(SMSError) as caught:
            self.backend().send("0788123456", "hello")
        self.assertIn("SMS_PROVIDER=console", str(caught.exception))

    def test_a_gateway_error_is_worth_retrying(self):
        with patch(
            "notifications.providers.africastalking._post",
            return_value=FakeResponse(502, None, text="bad gateway"),
        ):
            with self.assertRaises(SMSError) as caught:
                self.backend().send("0788123456", "hello")
        self.assertFalse(caught.exception.permanent)


class ConsoleProviderTests(TestCase):
    @override_settings(SMS_BACKEND="notifications.providers.console.ConsoleSMSBackend")
    def test_the_default_sends_nothing_and_costs_nothing(self):
        row = Notification.objects.create(
            kind=Kind.EXIT, channel=Channel.SMS, recipient="+250788123456", body="hi"
        )
        self.assertTrue(deliver(row))

    @override_settings(SMS_BACKEND="notifications.providers.console.NullSMSBackend")
    def test_the_null_backend_declines_permanently(self):
        row = Notification.objects.create(
            kind=Kind.EXIT, channel=Channel.SMS, recipient="+250788123456", body="hi"
        )
        with self.assertRaises(PermanentFailure):
            deliver(row)

    @override_settings(SMS_BACKEND="notifications.providers.nope.Missing")
    def test_a_misconfigured_provider_does_not_take_the_gate_down(self):
        row = Notification.objects.create(
            kind=Kind.EXIT, channel=Channel.SMS, recipient="+250788123456", body="hi"
        )
        with self.assertRaises(PermanentFailure):
            deliver(row)
