from django.test import TestCase

from .factories import api_client, make_gate, make_user


class AuthTests(TestCase):
    def setUp(self):
        self.gate = make_gate()
        self.guard = make_user(
            "guard1", role="GUARD", default_gate=self.gate, first_name="Emmanuel", last_name="N."
        )

    def test_login_returns_tokens_and_the_profile_in_one_call(self):
        response = api_client().post(
            "/api/auth/login/", {"username": "guard1", "password": "passw0rd!"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIn("access", body)
        self.assertIn("refresh", body)
        # The console needs the guard's gate immediately after sign-in.
        self.assertEqual(body["user"]["default_gate"], self.gate.id)
        self.assertEqual(body["user"]["role"], "GUARD")
        self.assertFalse(body["user"]["can_manage_records"])

    def test_bad_password_is_rejected(self):
        response = api_client().post(
            "/api/auth/login/", {"username": "guard1", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_access_token_works_against_the_api(self):
        login = api_client().post(
            "/api/auth/login/", {"username": "guard1", "password": "passw0rd!"}, format="json"
        )
        token = login.json()["access"]
        client = api_client()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)

    def test_guard_can_switch_their_own_gate_but_not_their_role(self):
        other = make_gate("West Gate", "WEST")
        client = api_client(self.guard)
        response = client.patch(
            "/api/auth/me/", {"default_gate": other.id, "role": "ADMIN"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.guard.refresh_from_db()
        self.assertEqual(self.guard.default_gate, other)
        self.assertEqual(self.guard.role, "GUARD")

    def test_password_change_requires_the_current_password(self):
        client = api_client(self.guard)
        wrong = client.post(
            "/api/auth/change-password/",
            {"current_password": "nope", "new_password": "newpassw0rd!"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)

        correct = client.post(
            "/api/auth/change-password/",
            {"current_password": "passw0rd!", "new_password": "newpassw0rd!"},
            format="json",
        )
        self.assertEqual(correct.status_code, 200)
        self.guard.refresh_from_db()
        self.assertTrue(self.guard.check_password("newpassw0rd!"))

    def test_health_endpoint_is_public(self):
        self.assertEqual(api_client().get("/api/health/").status_code, 200)
