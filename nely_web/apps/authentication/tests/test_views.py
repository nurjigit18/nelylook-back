# apps/authentication/tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from unittest.mock import patch

User = get_user_model()
signer = TimestampSigner(salt="email-verification")


class authenticationViewsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # create a test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="initialPassword123",
            first_name="Test",
        )

        # Example endpoints - adjust if your urls differ
        self.send_verif_url = "/auth/send-verification-email/"
        self.verify_email_url = "/auth/verify-email/"
        self.request_reset_url = "/auth/request-password-reset/"
        self.reset_password_url = "/auth/reset-password/"

    # -----------------------
    # SendVerificationEmailView
    # -----------------------
    @patch("apps.authentication.views.send_verification_email_sendgrid")
    def test_send_verification_email_success(self, mock_send):
        """authentication user should trigger send_verification_email_sendgrid and get 200 on success"""
        mock_send.return_value = (True, 202)

        # authentication without JWT complexity
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.send_verif_url, {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        mock_send.assert_called_once()
        # token present in the call args -> verify it's a proper string
        called_kwargs = mock_send.call_args.kwargs
        self.assertIn("verification_url", called_kwargs)
        self.assertIn("user_email", called_kwargs)
        self.assertEqual(called_kwargs["user_email"], self.user.email)

    @patch("apps.authentication.views.send_verification_email_sendgrid")
    def test_send_verification_email_failure(self, mock_send):
        """If email send fails, return 500 and error envelope"""
        mock_send.return_value = (False, "send-error-detail")
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.send_verif_url, {}, format="json")
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.data.get("status"), "error")
        self.assertIn("Failed to send verification email", resp.data.get("message"))

    # -----------------------
    # VerifyEmailView
    # -----------------------
    def test_verify_email_success(self):
        """Valid signed token should mark user.is_verified = True"""
        token = signer.sign(str(self.user.id))
        resp = self.client.get(self.verify_email_url, {"token": token})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        # reload user from DB
        u = User.objects.get(pk=self.user.pk)
        self.assertTrue(getattr(u, "is_verified", False))

    def test_verify_email_missing_token(self):
        resp = self.client.get(self.verify_email_url)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("status"), "error")

    @patch("apps.authentication.views.signer.unsign", side_effect=SignatureExpired())
    def test_verify_email_expired_token(self, mock_unsign):
        resp = self.client.get(self.verify_email_url, {"token": "dummy"})
        # your view returns status 400 with {"error": "Token expired"}
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Token expired", str(resp.data))

    @patch("apps.authentication.views.signer.unsign", side_effect=BadSignature())
    def test_verify_email_invalid_token(self, mock_unsign):
        resp = self.client.get(self.verify_email_url, {"token": "bad"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid token", str(resp.data) or "")

    # -----------------------
    # RequestPasswordResetView
    # -----------------------
    @patch("apps.authentication.views.send_password_reset_email_sendgrid")
    def test_request_password_reset_existing_user_calls_send(self, mock_send):
        """Requesting reset for an existing user should call send_password_reset_email_sendgrid"""
        mock_send.return_value = (True, 202)
        resp = self.client.post(self.request_reset_url, {"email": self.user.email}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        mock_send.assert_called_once()
        called_kwargs = mock_send.call_args.kwargs
        self.assertEqual(called_kwargs["user_email"], self.user.email)
        self.assertIn("reset_url", called_kwargs)

    @patch("apps.authentication.views.send_password_reset_email_sendgrid")
    def test_request_password_reset_non_existing_user_does_not_call_send(self, mock_send):
        """Should return generic 200 and not call send when email doesn't exist"""
        resp = self.client.post(self.request_reset_url, {"email": "notfound@example.com"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")
        mock_send.assert_not_called()

    def test_request_password_reset_missing_email(self):
        resp = self.client.post(self.request_reset_url, {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("status"), "error")

    # -----------------------
    # ResetPasswordView
    # -----------------------
    def test_reset_password_success(self):
        """Full reset flow: generate uid/token, post new password, assert password changed"""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        new_password = "NewStrongPassword123"

        resp = self.client.post(self.reset_password_url, {
            "uid": uid,
            "token": token,
            "new_password": new_password
        }, format="json")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data.get("status"), "success")

        # re-fetch and check password changed
        u = User.objects.get(pk=self.user.pk)
        self.assertTrue(u.check_password(new_password))

    def test_reset_password_invalid_token(self):
        """Invalid token should return error (400)"""
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        resp = self.client.post(self.reset_password_url, {
            "uid": uid,
            "token": "invalid-token",
            "new_password": "whatever123"
        }, format="json")
        # view returns 400 for invalid token
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("status"), "error")

    def test_reset_password_missing_fields(self):
        resp = self.client.post(self.reset_password_url, {
            "uid": "",
            "token": "",
            "new_password": ""
        }, format="json")
        # missing required fields -> 400
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("status"), "error")

    def test_reset_password_too_short(self):
        """Password shorter than 8 chars should be rejected"""
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        resp = self.client.post(self.reset_password_url, {
            "uid": uid,
            "token": token,
            "new_password": "short"
        }, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data.get("status"), "error")
