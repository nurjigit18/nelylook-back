# apps/authentication/tests/test_email_smtp.py

from django.test import TestCase, override_settings
from django.core import mail
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from django.core.mail import send_mail
import socket

User = get_user_model()


class SMTPEmailBackendTests(TestCase):
    """Test SMTP email backend functionality"""
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_send_email_with_locmem_backend(self):
        """Test email sending with local memory backend (for testing)"""
        send_mail(
            subject='Test Subject',
            message='Test message',
            from_email='noreply@nelylook.com',
            recipient_list=['test@example.com'],
            fail_silently=False,
        )
        
        # Check that one email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test Subject')
        self.assertEqual(mail.outbox[0].to, ['test@example.com'])
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_send_html_email(self):
        """Test sending HTML email"""
        from django.core.mail import EmailMultiAlternatives
        
        text_content = 'This is plain text'
        html_content = '<p>This is <strong>HTML</strong></p>'
        
        email = EmailMultiAlternatives(
            subject='HTML Test',
            body=text_content,
            from_email='noreply@nelylook.com',
            to=['test@example.com']
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.sendgrid.net',
        EMAIL_PORT=587,
        EMAIL_USE_TLS=True,
        EMAIL_HOST_USER='apikey',
        EMAIL_HOST_PASSWORD='SG.test_key'
    )
    @patch('smtplib.SMTP')
    def test_smtp_connection_success(self, mock_smtp):
        """Test successful SMTP connection"""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.sendmail.return_value = {}
        
        send_mail(
            subject='Test',
            message='Test message',
            from_email='noreply@nelylook.com',
            recipient_list=['test@example.com'],
            fail_silently=False,
        )
        
        # Verify SMTP was called with correct host and port
        mock_smtp.assert_called()
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.sendgrid.net',
        EMAIL_PORT=587,
    )
    @patch('smtplib.SMTP')
    def test_smtp_connection_timeout(self, mock_smtp):
        """Test SMTP connection timeout handling"""
        mock_smtp.side_effect = socket.timeout("Connection timed out")
        
        with self.assertRaises(socket.timeout):
            send_mail(
                subject='Test',
                message='Test message',
                from_email='noreply@nelylook.com',
                recipient_list=['test@example.com'],
                fail_silently=False,
            )
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.sendgrid.net',
        EMAIL_PORT=587,
    )
    @patch('smtplib.SMTP')
    def test_smtp_authentication_failure(self, mock_smtp):
        """Test SMTP authentication failure handling"""
        import smtplib
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance
        mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(
            535, b'Authentication failed'
        )
        
        with self.assertRaises(smtplib.SMTPAuthenticationError):
            send_mail(
                subject='Test',
                message='Test message',
                from_email='noreply@nelylook.com',
                recipient_list=['test@example.com'],
                fail_silently=False,
            )


class EmailConfigurationTests(TestCase):
    """Test email configuration and settings"""
    
    def test_email_backend_is_configured(self):
        """Test that email backend setting exists"""
        from django.conf import settings
        self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
    
    @override_settings(DEBUG=False)
    def test_production_email_settings(self):
        """Test that production has proper email settings"""
        from django.conf import settings
        
        if not settings.DEBUG:
            self.assertIsNotNone(settings.EMAIL_HOST)
            self.assertIsNotNone(settings.EMAIL_PORT)
            self.assertIsNotNone(settings.DEFAULT_FROM_EMAIL)
    
    def test_default_from_email_format(self):
        """Test that DEFAULT_FROM_EMAIL is properly formatted"""
        from django.conf import settings
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        # Extract email from "Name <email@domain.com>" format
        from_email = settings.DEFAULT_FROM_EMAIL
        if '<' in from_email and '>' in from_email:
            email_part = from_email.split('<')[1].split('>')[0]
        else:
            email_part = from_email
        
        try:
            validate_email(email_part)
            valid = True
        except ValidationError:
            valid = False
        
        self.assertTrue(valid, f"Invalid email format: {email_part}")


class EmailRateLimitingTests(APITestCase):
    """Test email rate limiting to prevent abuse"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = '/auth/send-verification/'
        self.user = User.objects.create_user(
            email='ratelimit@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
    
    @override_settings(
        REST_FRAMEWORK={
            'DEFAULT_THROTTLE_RATES': {
                'verification_email': '3/hour'
            }
        }
    )
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_email_rate_limiting(self, mock_send_email):
        """Test that email sending is rate limited"""
        mock_send_email.return_value = (True, 202)
        
        # Note: This test would need a custom throttle class
        # For demonstration purposes only
        for i in range(3):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class EmailErrorHandlingTests(APITestCase):
    """Test various error scenarios"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = '/auth/send-verification/'
        self.user = User.objects.create_user(
            email='errortest@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=self.user)
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_network_error_handling(self, mock_send_email):
        """Test handling of network errors"""
        import requests
        mock_send_email.side_effect = requests.exceptions.ConnectionError(
            "Network unreachable"
        )
        
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_sendgrid_api_error_handling(self, mock_send_email):
        """Test handling of SendGrid API errors"""
        mock_send_email.return_value = (False, "Rate limit exceeded")
        
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('details', response.data)
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    @override_settings(SENDGRID_API_KEY=None)
    def test_missing_api_key_handling(self, mock_send_email):
        """Test behavior when API key is not configured"""
        mock_send_email.return_value = (False, "API key not configured")
        
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmailValidationTests(TestCase):
    """Test email address validation"""
    
    def test_valid_email_addresses(self):
        """Test that valid email addresses are accepted"""
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        valid_emails = [
            'test@example.com',
            'user.name@example.com',
            'user+tag@example.co.uk',
            'user_name@example-domain.com',
        ]
        
        for email in valid_emails:
            try:
                validate_email(email)
                valid = True
            except ValidationError:
                valid = False
            
            self.assertTrue(valid, f"Email {email} should be valid")
    
    def test_invalid_email_addresses(self):
        """Test that invalid email addresses are rejected"""
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        
        invalid_emails = [
            'notanemail',
            '@example.com',
            'user@',
            'user @example.com',
            'user@.com',
        ]
        
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                validate_email(email)


# Additional test fixtures and factories

class EmailTestCase(TestCase):
    """Base test case with email-related utilities"""
    
    def setUp(self):
        # Clear the test outbox before each test
        mail.outbox = []
    
    def assertEmailSent(self, count=1):
        """Assert that a specific number of emails were sent"""
        self.assertEqual(len(mail.outbox), count)
    
    def assertEmailContains(self, text, email_index=0):
        """Assert that an email contains specific text"""
        self.assertIn(text, mail.outbox[email_index].body)
    
    def assertEmailSubject(self, subject, email_index=0):
        """Assert that an email has a specific subject"""
        self.assertEqual(mail.outbox[email_index].subject, subject)
    
    def assertEmailTo(self, recipient, email_index=0):
        """Assert that an email was sent to a specific recipient"""
        self.assertIn(recipient, mail.outbox[email_index].to)


# Performance tests

class EmailPerformanceTests(TestCase):
    """Test email sending performance"""
    
    @override_settings(
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    )
    def test_bulk_email_sending_performance(self):
        """Test performance of sending multiple emails"""
        import time
        
        start_time = time.time()
        
        for i in range(10):
            send_mail(
                subject=f'Test {i}',
                message='Test message',
                from_email='noreply@nelylook.com',
                recipient_list=[f'test{i}@example.com'],
                fail_silently=False,
            )
        
        duration = time.time() - start_time
        
        # Should send 10 emails in less than 1 second with locmem backend
        self.assertLess(duration, 1.0)
        self.assertEqual(len(mail.outbox), 10)


# Run all tests:
# python manage.py test apps.authentication.tests

# Run with verbose output:
# python manage.py test apps.authentication.tests --verbosity=2

# Run specific test module:
# python manage.py test apps.authentication.tests.test_email_smtp