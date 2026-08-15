from django.test import TestCase

from search.indexer import device_ids, student_ids, tokenise
from search.models import SearchToken

from .factories import api_client, make_device, make_student, make_user

SUGGEST = "/api/search/suggest/"


class TokeniserTests(TestCase):
    def test_words_are_split_and_uppercased(self):
        self.assertEqual(tokenise("Aline Uwase"), {"ALINE", "UWASE"})

    def test_punctuated_values_index_both_forms(self):
        tokens = tokenise("UNI-024/01")
        self.assertIn("UNI", tokens)
        self.assertIn("024", tokens)
        self.assertIn("UNI02401", tokens)

    def test_a_single_word_does_not_get_a_pointless_duplicate(self):
        self.assertEqual(tokenise("HP12345678"), {"HP12345678"})

    def test_blanks_are_ignored(self):
        self.assertEqual(tokenise("", None, "   "), set())


class IndexMaintenanceTests(TestCase):
    def test_saving_a_student_indexes_them(self):
        student = make_student("218001234", first_name="Aline", last_name="Uwase")
        tokens = set(SearchToken.objects.filter(student=student).values_list("token", flat=True))
        self.assertIn("ALINE", tokens)
        self.assertIn("UWASE", tokens)
        self.assertIn("218001234", tokens)

    def test_renaming_a_student_drops_the_old_token(self):
        student = make_student("218001234", first_name="Aline")
        student.first_name = "Chantal"
        student.save()
        tokens = set(SearchToken.objects.filter(student=student).values_list("token", flat=True))
        self.assertIn("CHANTAL", tokens)
        self.assertNotIn("ALINE", tokens)

    def test_a_device_is_findable_by_its_owner(self):
        student = make_student("218001234", first_name="Aline", last_name="Uwase")
        device = make_device(student, "HP12345678")
        tokens = set(SearchToken.objects.filter(device=device).values_list("token", flat=True))
        self.assertIn("UWASE", tokens)
        self.assertIn("HP12345678", tokens)

    def test_renaming_a_student_refreshes_their_computers_too(self):
        student = make_student("218001234", last_name="Uwase")
        device = make_device(student, "HP12345678")
        student.last_name = "Mugisha"
        student.save()
        tokens = set(SearchToken.objects.filter(device=device).values_list("token", flat=True))
        self.assertIn("MUGISHA", tokens)
        self.assertNotIn("UWASE", tokens)

    def test_deleting_a_record_removes_its_tokens(self):
        student = make_student("218001234")
        device = make_device(student, "HP12345678")
        # Django blanks .pk on delete(), so capture the ids first - filtering
        # on a None id would silently match the NULL-sided rows instead.
        student_pk, device_pk = student.pk, device.pk
        self.assertTrue(SearchToken.objects.filter(device_id=device_pk).exists())

        device.delete()
        self.assertEqual(SearchToken.objects.filter(device_id=device_pk).count(), 0)

        student.delete()
        self.assertEqual(SearchToken.objects.filter(student_id=student_pk).count(), 0)

    def test_repeated_saves_do_not_duplicate_tokens(self):
        student = make_student("218001234", first_name="Aline")
        before = SearchToken.objects.filter(student=student).count()
        student.save()
        student.save()
        self.assertEqual(SearchToken.objects.filter(student=student).count(), before)


class PrefixSearchTests(TestCase):
    def setUp(self):
        self.aline = make_student("218001234", first_name="Aline", last_name="Uwase")
        self.bosco = make_student("218009999", first_name="Bosco", last_name="Mugisha")
        self.device = make_device(self.aline, "HP12345678", brand="HP", model_name="EliteBook")

    def test_a_prefix_finds_the_student(self):
        self.assertEqual(student_ids("uwa"), {self.aline.id})
        self.assertEqual(student_ids("MUG"), {self.bosco.id})

    def test_search_is_case_insensitive(self):
        self.assertEqual(student_ids("uWaSe"), {self.aline.id})

    def test_multiple_words_narrow_rather_than_widen(self):
        # "Aline Mugisha" is nobody, even though both words exist separately.
        self.assertEqual(student_ids("aline uwase"), {self.aline.id})
        self.assertEqual(student_ids("aline mugisha"), set())

    def test_a_reg_number_typed_with_punctuation_still_matches(self):
        self.assertEqual(student_ids("218-001-234"), {self.aline.id})

    def test_a_device_is_found_by_serial_prefix_and_by_brand(self):
        self.assertEqual(device_ids("HP123"), {self.device.id})
        self.assertEqual(device_ids("elitebook"), {self.device.id})

    def test_a_device_is_found_by_its_owner_details(self):
        self.assertEqual(device_ids("uwase"), {self.device.id})
        self.assertEqual(device_ids("218001234"), {self.device.id})

    def test_an_empty_query_matches_nothing_rather_than_everything(self):
        self.assertIsNone(student_ids(""))
        self.assertIsNone(student_ids("   "))

    def test_no_match_returns_an_empty_set(self):
        self.assertEqual(student_ids("zzzz"), set())


class SuggestEndpointTests(TestCase):
    def setUp(self):
        self.guard = make_user("guard1", role="GUARD")
        self.client = api_client(self.guard)
        self.student = make_student("218001234", first_name="Aline", last_name="Uwase")
        make_device(self.student, "HP12345678", brand="HP")

    def test_it_suggests_students_and_devices(self):
        response = self.client.get(SUGGEST, {"q": "uwa"})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["students"][0]["reg_number"], "218001234")
        self.assertEqual(body["devices"][0]["serial_number"], "HP12345678")

    def test_one_character_is_ignored(self):
        """Otherwise every keystroke scans most of the register."""
        body = self.client.get(SUGGEST, {"q": "u"}).json()
        self.assertEqual(body["students"], [])
        self.assertEqual(body["devices"], [])

    def test_kinds_can_be_narrowed(self):
        body = self.client.get(SUGGEST, {"q": "uwa", "kinds": "students"}).json()
        self.assertTrue(body["students"])
        self.assertEqual(body["devices"], [])

    def test_it_requires_a_login(self):
        self.assertEqual(api_client().get(SUGGEST, {"q": "uwa"}).status_code, 401)


class ListSearchTests(TestCase):
    """The list endpoints must go through the index and still behave."""

    def setUp(self):
        self.registrar = make_user("registrar", role="REGISTRAR")
        self.client = api_client(self.registrar)
        self.aline = make_student("218001234", first_name="Aline", last_name="Uwase")
        self.bosco = make_student("218009999", first_name="Bosco", last_name="Mugisha")
        make_device(self.aline, "HP12345678", brand="HP")
        make_device(self.bosco, "DL99887766", brand="Dell")

    def test_student_list_search_uses_the_index(self):
        body = self.client.get("/api/students/", {"search": "mug"}).json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["reg_number"], "218009999")

    def test_device_list_search_by_owner_name(self):
        body = self.client.get("/api/devices/", {"search": "uwase"}).json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["serial_number"], "HP12345678")

    def test_search_combines_with_other_filters(self):
        body = self.client.get("/api/devices/", {"search": "dell", "status": "ACTIVE"}).json()
        self.assertEqual(body["count"], 1)
        body = self.client.get("/api/devices/", {"search": "dell", "status": "STOLEN"}).json()
        self.assertEqual(body["count"], 0)

    def test_an_unmatched_search_returns_nothing_not_everything(self):
        body = self.client.get("/api/students/", {"search": "zzzzz"}).json()
        self.assertEqual(body["count"], 0)

    def test_a_blank_search_still_lists_everyone(self):
        body = self.client.get("/api/students/", {"search": "  "}).json()
        self.assertEqual(body["count"], 2)
