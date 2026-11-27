import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from erp.models import InventoryItem


class ErpApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.member = user_model.objects.create_user(
            username="member",
            password="member-password-123",
        )
        cls.admin = user_model.objects.create_user(
            username="admin",
            password="admin-password-123",
            is_staff=True,
        )

    def test_api_requires_authentication(self):
        response = self.client.get("/api/data/")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_session_check_is_not_an_error(self):
        response = self.client.get("/api/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False})

    def test_protected_pages_redirect_to_login(self):
        response = self.client.get("/dashboard.html")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/index.html")
        self.assertEqual(self.client.get("/index.html").status_code, 200)

    def test_session_role_comes_from_django_user(self):
        self.client.force_login(self.member)
        response = self.client.get("/api/session/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["role"], "member")

    def test_login_requires_csrf_and_creates_server_session(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/index.html")
        csrf_token = client.cookies["csrftoken"].value
        response = client.post(
            "/api/session/login/",
            data=json.dumps({"username": "member", "password": "member-password-123"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "member")
        self.assertEqual(client.get("/api/session/").status_code, 200)

    def test_logout_requires_csrf_and_clears_session(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/index.html")
        csrf_token = client.cookies["csrftoken"].value
        login_response = client.post(
            "/api/session/login/",
            data=json.dumps({"username": "member", "password": "member-password-123"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, 200)
        csrf_token = client.cookies["csrftoken"].value
        response = client.post(
            "/api/session/logout/",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.get("/api/session/").json(), {"authenticated": False})

    def test_member_cannot_replace_inventory(self):
        self.client.force_login(self.member)
        response = self.client.put(
            "/api/data/inventory/",
            data=json.dumps([]),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_replace_inventory(self):
        self.client.force_login(self.admin)
        response = self.client.put(
            "/api/data/inventory/",
            data=json.dumps(
                [{"id": 25, "name": "New laptop", "category": "merchandise", "quantity": 3}]
            ),
            content_type="application/json",
            HTTP_IF_MATCH="0",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(InventoryItem.objects.values("id", "name", "category", "quantity")),
            [{"id": 25, "name": "New laptop", "category": "merchandise", "quantity": 3}],
        )

    def test_invalid_replacement_leaves_existing_data_unchanged(self):
        existing = InventoryItem.objects.create(
            name="Existing item",
            category="merchandise",
            quantity=1,
        )
        self.client.force_login(self.admin)
        response = self.client.put(
            "/api/data/inventory/",
            data=json.dumps(
                [
                    {"id": 1, "name": "Duplicate", "category": "merchandise", "quantity": 1},
                    {"id": 2, "name": " duplicate ", "category": "merchandise", "quantity": 2},
                ]
            ),
            content_type="application/json",
            HTTP_IF_MATCH="0",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list(InventoryItem.objects.values_list("id", "name")), [(existing.pk, "Existing item")])

    def test_data_endpoint_seeds_initial_collections_once(self):
        self.client.force_login(self.member)
        first = self.client.get("/api/data/")
        second = self.client.get("/api/data/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(first.json()["inventory"]), 6)

    def test_stale_revision_cannot_overwrite_saved_inventory(self):
        self.client.force_login(self.admin)
        initial = self.client.get("/api/data/").json()
        write = self.client.put(
            "/api/data/inventory/",
            data=json.dumps(
                [{"id": 1, "name": "Saved item", "category": "merchandise", "quantity": 5}]
            ),
            content_type="application/json",
            HTTP_IF_MATCH=str(initial["_revisions"]["inventory"]),
        )
        self.assertEqual(write.status_code, 200)

        stale_write = self.client.put(
            "/api/data/inventory/",
            data=json.dumps([]),
            content_type="application/json",
            HTTP_IF_MATCH=str(initial["_revisions"]["inventory"]),
        )
        self.assertEqual(stale_write.status_code, 409)
        self.assertEqual(list(InventoryItem.objects.values_list("name", flat=True)), ["Saved item"])
