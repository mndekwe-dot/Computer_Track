"""The read audit log, and the middle-of-word search fallback."""

from django.test import TestCase

from accounts.audit import AccessLog, AuditAction
from search.indexer import filter_students

from .factories import api_client, make_device, make_student, make_user
from students.models import Student

LOG = "/api/auth/access-log/"


class AuditRecordingTests(TestCase):
    def setUp(self):
        self.guard = make_user("guard1", role="GUARD")
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.client = api_client(self.guard)
        self.student = make_student("218001234", first_name="Aline", last_name="Uwase")
        make_device(self.student, "HP12345678")

    def test_a_gate_lookup_is_recorded_with_who_was_looked_up(self):
        self.client.get("/api/checkpoint/lookup/", {"q": "218001234"})
        entry = AccessLog.objects.get()
        self.assertEqual(entry.action, AuditAction.GATE_LOOKUP)
        self.assertEqual(entry.username, "guard1")
        self.assertEqual(entry.query, "218001234")
        self.assertEqual(entry.subject_reg_number, "218001234")

    def test_a_failed_lookup_is_recorded_too(self):
        """A run of misses is exactly what fishing looks like."""
        self.client.get("/api/checkpoint/lookup/", {"q": "999999999"})
        entry = AccessLog.objects.get()
        self.assertEqual(entry.query, "999999999")
        self.assertEqual(entry.subject_reg_number, "")

    def test_the_typeahead_is_recorded(self):
        self.client.get("/api/search/suggest/", {"q": "uwa"})
        self.assertEqual(AccessLog.objects.get().action, AuditAction.SUGGEST)

    def test_searching_the_student_list_is_recorded(self):
        api_client(self.registrar).get("/api/students/", {"search": "uwase"})
        entry = AccessLog.objects.get()
        self.assertEqual(entry.action, AuditAction.LIST_STUDENTS)
        self.assertEqual(entry.result_count, 1)

    def test_idle_browsing_is_not_recorded(self):
        """Only searches; logging every page would bury the real signal."""
        api_client(self.registrar).get("/api/students/")
        self.assertEqual(AccessLog.objects.count(), 0)

    def test_exporting_the_gate_log_is_recorded(self):
        self.client.get("/api/checkpoint/scans/export/")
        self.assertEqual(AccessLog.objects.get().action, AuditAction.EXPORT)

    def test_the_ip_address_is_captured(self):
        self.client.get(
            "/api/checkpoint/lookup/", {"q": "218001234"}, HTTP_X_FORWARDED_FOR="10.1.2.3, 10.9.9.9"
        )
        # The left-most entry is the original client, not the proxy.
        self.assertEqual(AccessLog.objects.get().ip_address, "10.1.2.3")

    def test_auditing_never_breaks_the_request(self):
        from unittest.mock import patch

        with patch(
            "accounts.audit.AccessLog.objects.create", side_effect=RuntimeError("db full")
        ):
            response = self.client.get("/api/checkpoint/lookup/", {"q": "218001234"})
        self.assertEqual(response.status_code, 200)


class AuditAccessTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", role="ADMIN")
        self.guard = make_user("guard1", role="GUARD")
        self.registrar = make_user("registrar", role="REGISTRAR")
        make_student("218001234")
        api_client(self.guard).get("/api/checkpoint/lookup/", {"q": "218001234"})

    def test_an_admin_can_read_the_log(self):
        response = api_client(self.admin).get(LOG)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["count"], 1)

    def test_a_guard_cannot_read_the_log(self):
        self.assertEqual(api_client(self.guard).get(LOG).status_code, 403)

    def test_a_registrar_cannot_read_the_log(self):
        self.assertEqual(api_client(self.registrar).get(LOG).status_code, 403)

    def test_the_log_cannot_be_edited_or_deleted_by_anyone(self):
        """An audit log the audited can tidy up is not an audit log."""
        entry = AccessLog.objects.first()
        client = api_client(self.admin)
        self.assertEqual(client.delete(f"{LOG}{entry.id}/").status_code, 405)
        self.assertEqual(client.patch(f"{LOG}{entry.id}/", {"query": "x"}).status_code, 405)
        self.assertEqual(client.post(LOG, {"action": "EXPORT"}).status_code, 405)

    def test_it_can_be_filtered_by_who_and_by_what(self):
        client = api_client(self.admin)
        self.assertEqual(client.get(LOG, {"user": self.guard.id}).json()["count"], 1)
        self.assertEqual(client.get(LOG, {"action": "EXPORT"}).json()["count"], 0)
        self.assertEqual(client.get(LOG, {"q": "218001234"}).json()["count"], 1)

    def test_the_summary_shows_the_busiest_accounts(self):
        response = api_client(self.admin).get(f"{LOG}summary/")
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["total_reads"], 1)
        self.assertEqual(body["busiest_accounts"][0]["username"], "guard1")


class ContainsFallbackTests(TestCase):
    """Prefix search cannot match mid-word; the fallback can.

    On PostgreSQL this runs against the pg_trgm GIN index; elsewhere it
    degrades to a scan, which is acceptable because it only ever runs when the
    indexed prefix search already came back empty.
    """

    def setUp(self):
        self.aline = make_student("218001234", first_name="Aline", last_name="Mugisha")
        self.bosco = make_student("218009999", first_name="Bosco", last_name="Uwase")

    def find(self, query):
        return set(
            filter_students(Student.objects.all(), query).values_list("pk", flat=True)
        )

    def test_a_prefix_still_wins_and_stays_exact(self):
        self.assertEqual(self.find("mugi"), {self.aline.id})

    def test_a_middle_fragment_is_found_by_the_fallback(self):
        # "gish" is nobody's prefix, but it is inside "MUGISHA".
        self.assertEqual(self.find("gish"), {self.aline.id})

    def test_a_trailing_fragment_is_found(self):
        self.assertEqual(self.find("wase"), {self.bosco.id})

    def test_very_short_fragments_do_not_trigger_the_fallback(self):
        """Two characters would match half the register - not useful."""
        self.assertEqual(self.find("gi"), set())

    def test_nonsense_still_finds_nothing(self):
        self.assertEqual(self.find("qqzzxx"), set())
