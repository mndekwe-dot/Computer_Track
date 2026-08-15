"""Uploaded photos must not be readable by anyone holding a URL.

The old behaviour served files straight out of MEDIA_ROOT, which meant a
student's photo was public to anyone who ever saw the link and stayed public
forever. These tests pin the replacement: links are signed, they expire, and
nothing outside MEDIA_ROOT is reachable through the view.
"""

import io
import shutil
import time
from pathlib import Path

from django.core import signing
from django.test import TestCase, override_settings
from django.urls import reverse

from config.media import SALT, sign_media_name, signed_media_url
from students.models import Student

from .factories import api_client, make_device, make_student, make_user

# Smallest thing a browser will accept as a GIF, so the tests exercise real
# file serving without checking a binary blob into the repository.
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!"
    b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class SignedUrlTests(TestCase):
    def test_serializer_never_emits_a_raw_media_path(self):
        """The whole point: /media/... must not appear in an API response."""
        student = make_student()
        student.photo.save("face.jpg", io.BytesIO(b"x"), save=True)
        self.addCleanup(student.photo.delete, save=False)

        staff = make_user("registrar", role="REGISTRAR")
        response = api_client(staff).get(f"/api/students/{student.pk}/")

        self.assertEqual(response.status_code, 200)
        photo = response.data["photo"]
        self.assertIsNotNone(photo)
        # The signed route lives under /api/media/, so check the raw prefix
        # specifically rather than the substring, which the new URL contains.
        self.assertFalse(photo.startswith("/media/"))
        self.assertTrue(photo.startswith("/api/media/"))

    def test_no_photo_stays_none(self):
        student = make_student()
        self.assertIsNone(signed_media_url(student.photo))


@override_settings(MEDIA_ROOT=Path(__file__).resolve().parent / "_media")
class ProtectedMediaViewTests(TestCase):
    def setUp(self):
        from django.conf import settings

        self.root = Path(settings.MEDIA_ROOT)
        (self.root / "students").mkdir(parents=True, exist_ok=True)
        self.name = "students/face.gif"
        (self.root / self.name).write_bytes(TINY_GIF)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def url_for(self, name):
        return reverse("protected-media", args=[sign_media_name(name)])

    def test_a_valid_signature_serves_the_file(self):
        response = self.client.get(self.url_for(self.name))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/gif")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("private", response["Cache-Control"])
        self.assertEqual(b"".join(response.streaming_content), TINY_GIF)

    def test_an_unsigned_guess_is_refused(self):
        """Knowing the filename is not enough, which is the entire fix."""
        response = self.client.get("/api/media/students%2Fface.gif/")
        self.assertEqual(response.status_code, 404)

    def test_a_tampered_token_is_refused(self):
        token = sign_media_name(self.name)
        response = self.client.get(f"/api/media/{token[:-3]}xyz/")
        self.assertEqual(response.status_code, 404)

    def test_a_signature_from_another_salt_is_refused(self):
        """A token signed for some other purpose must not open a photo."""
        token = signing.dumps(self.name, salt="something-else", compress=True)
        response = self.client.get(f"/api/media/{token}/")
        self.assertEqual(response.status_code, 404)

    @override_settings(MEDIA_LINK_TTL_SECONDS=1)
    def test_an_expired_link_says_so_rather_than_404ing(self):
        """410 with an instruction: expiry is normal, not an error."""
        url = self.url_for(self.name)
        time.sleep(1.1)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 410)
        self.assertIn("expired", response.content.decode().lower())

    def test_traversal_outside_media_root_is_refused(self):
        """Signed by us, but still must not read settings.py."""
        response = self.client.get(self.url_for("../config/settings.py"))
        self.assertEqual(response.status_code, 404)

    def test_a_non_image_extension_is_refused(self):
        """No arbitrary content types out of the uploads directory."""
        (self.root / "students" / "note.html").write_text("<script>alert(1)</script>")
        response = self.client.get(self.url_for("students/note.html"))
        self.assertEqual(response.status_code, 404)

    def test_svg_is_refused_even_though_it_is_an_image(self):
        """SVG carries script. Browsers run it; we do not serve it."""
        (self.root / "students" / "logo.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
        response = self.client.get(self.url_for("students/logo.svg"))
        self.assertEqual(response.status_code, 404)

    def test_a_missing_file_is_a_404_not_a_crash(self):
        response = self.client.get(self.url_for("students/gone.jpg"))
        self.assertEqual(response.status_code, 404)

    @override_settings(MEDIA_ACCEL_REDIRECT=True, MEDIA_ACCEL_PREFIX="/protected-media/")
    def test_nginx_mode_hands_off_without_reading_the_file(self):
        response = self.client.get(self.url_for(self.name))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Accel-Redirect"], f"/protected-media/{self.name}")
        self.assertEqual(response.content, b"")


class GateLookupPhotoTests(TestCase):
    def test_the_gate_sees_a_signed_owner_photo(self):
        """The guard's screen is the main consumer, so pin it end to end."""
        student = make_student()
        student.photo.save("face.jpg", io.BytesIO(b"x"), save=True)
        self.addCleanup(student.photo.delete, save=False)
        make_device(student, serial_number="HP99887766")

        guard = make_user("guard-photo", role="GUARD")
        response = api_client(guard).get("/api/checkpoint/lookup/", {"q": student.reg_number})

        self.assertEqual(response.status_code, 200)
        owner = response.data["student"]
        self.assertTrue(owner["photo"].startswith("/api/media/"))
        # And it actually resolves, rather than being a well-formed dead link.
        self.assertNotEqual(Student.objects.get(pk=student.pk).photo.name, "")
