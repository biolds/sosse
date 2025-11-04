# Copyright 2025 Laurent Defert
#
#  This file is part of Sosse.
#
# Sosse is free software: you can redistribute it and/or modify it under the terms of the GNU Affero
# General Public License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Sosse is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
# the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with Sosse.
# If not, see <https://www.gnu.org/licenses/>.

import json
from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from .collection import Collection
from .document import Document


class JWTAuthenticationTest(TestCase):
    def setUp(self):
        self.client = Client(HTTP_USER_AGENT="Mozilla/5.0")
        self.user = User.objects.create_user(username="testuser", password="testpass123", is_superuser=False)
        permission = Permission.objects.get(codename="view_document")
        self.user.user_permissions.add(permission)

        self.superuser = User.objects.create_user(username="admin", password="admin123", is_superuser=True)
        self.collection = Collection.create_default()

        now = timezone.now()
        self.doc = Document.objects.wo_content().create(
            url="http://127.0.0.1/test",
            normalized_url="http test",
            title="Test Document",
            normalized_title="test document",
            content="Test content",
            normalized_content="test content",
            crawl_first=now,
            crawl_last=now,
            lang_iso_639_1="en",
            mimetype="text/html",
            collection=self.collection,
        )

    def test_obtain_token_pair(self):
        """Test obtaining JWT token pair with valid credentials."""
        response = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        data = json.loads(response.content)
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertTrue(len(data["access"]) > 0)
        self.assertTrue(len(data["refresh"]) > 0)

    def test_obtain_token_invalid_credentials(self):
        """Test token endpoint rejects invalid credentials."""
        response = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "wrongpassword"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_obtain_token_missing_credentials(self):
        """Test token endpoint requires both username and password."""
        response = self.client.post(
            "/api/token/",
            {"username": "testuser"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_refresh_token(self):
        """Test refreshing access token with valid refresh token."""
        # First obtain a token pair
        response = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        data = json.loads(response.content)
        refresh_token = data["refresh"]

        # Now refresh the access token
        response = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("access", data)
        self.assertTrue(len(data["access"]) > 0)

    def test_refresh_token_invalid(self):
        """Test refresh endpoint rejects invalid refresh token."""
        response = self.client.post(
            "/api/token/refresh/",
            {"refresh": "invalid.token.here"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_access_with_jwt(self):
        """Test accessing protected API endpoint with JWT token."""
        # Obtain token
        response = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        data = json.loads(response.content)
        access_token = data["access"]

        # Access API with JWT token
        response = self.client.get(
            "/api/document/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("results", data)

    def test_api_access_without_auth(self):
        """Test accessing protected API endpoint without authentication."""
        response = self.client.get("/api/document/")
        self.assertEqual(response.status_code, 401)

    def test_api_access_with_invalid_jwt(self):
        """Test accessing API with invalid JWT token."""
        response = self.client.get(
            "/api/document/",
            HTTP_AUTHORIZATION="Bearer invalid.jwt.token",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_access_with_expired_jwt(self):
        """Test accessing API with expired JWT token."""
        # Create an expired token
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token

        # Manually expire the token by setting exp claim to the past
        access_token.set_exp(lifetime=-timedelta(hours=1))

        response = self.client.get(
            "/api/document/",
            HTTP_AUTHORIZATION=f"Bearer {str(access_token)}",
        )
        self.assertEqual(response.status_code, 401)

    def test_jwt_with_superuser(self):
        """Test JWT authentication with superuser account."""
        response = self.client.post(
            "/api/token/",
            {"username": "admin", "password": "admin123"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        access_token = data["access"]

        # Access API with superuser JWT token
        response = self.client.get(
            "/api/document/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 200)

    def test_api_document_detail_with_jwt(self):
        """Test accessing specific document with JWT authentication."""
        # Obtain token
        response = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        data = json.loads(response.content)
        access_token = data["access"]

        # Access specific document
        response = self.client.get(
            f"/api/document/{self.doc.id}/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["url"], "http://127.0.0.1/test")
        self.assertEqual(data["title"], "Test Document")

    def test_session_auth_still_works(self):
        """Test that session authentication still works alongside JWT."""
        # Login with session authentication
        self.client.login(username="testuser", password="testpass123")

        # Access API without JWT token (using session)
        response = self.client.get("/api/document/")
        self.assertEqual(response.status_code, 200)

    def test_jwt_token_contains_user_info(self):
        """Test that JWT token is properly generated for the user."""
        response = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        data = json.loads(response.content)
        access_token = data["access"]

        # Decode and verify the token contains user information
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken(access_token)
        self.assertEqual(int(token["user_id"]), self.user.id)

    def test_multiple_token_requests(self):
        """Test obtaining multiple tokens for the same user."""
        # First token
        response1 = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        data1 = json.loads(response1.content)
        token1 = data1["access"]

        # Second token
        response2 = self.client.post(
            "/api/token/",
            {"username": "testuser", "password": "testpass123"},
            content_type="application/json",
        )
        data2 = json.loads(response2.content)
        token2 = data2["access"]

        # Both tokens should work
        response = self.client.get(
            "/api/document/",
            HTTP_AUTHORIZATION=f"Bearer {token1}",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            "/api/document/",
            HTTP_AUTHORIZATION=f"Bearer {token2}",
        )
        self.assertEqual(response.status_code, 200)
