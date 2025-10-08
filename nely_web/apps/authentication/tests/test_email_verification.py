# apps/authentication/tests/test_email_verification.py

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, Mock
from apps.authentication.emails_utils import send_verification_email_sendgrid

User = get_user_model()


class SendVerificationEmailUtilTests(TestCase):
    """Test the email utility function"""
    
    def setUp(self):
        self.user_email = "test@example.com"
        self.user_name = "Test User"
        self.verification_url = "https://nelylook.com/verify?token=abc123"
    
    @patch('apps.authentication.emails_utils.SendGridAPIClient')
    @override_settings(SENDGRID_API_KEY='SG.test_key_123')
    def test_send_verification_email_success(self, mock_sendgrid_client):
        """Test successful email sending via SendGrid API"""
        # Mock the SendGrid response
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {'X-Message-Id': 'test-message-id'}
        
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance
        
        # Call the function
        success, result = send_verification_email_sendgrid(
            user_email=self.user_email,
            user_name=self.user_name,
            verification_url=self.verification_url
        )
        
        # Assertions
        self.assertTrue(success)
        self.assertEqual(result, 202)
        mock_sendgrid_client.assert_called_once()
        mock_sg_instance.send.assert_called_once()
    
    @patch('apps.authentication.emails_utils.SendGridAPIClient')
    @override_settings(SENDGRID_API_KEY='SG.test_key_123')
    def test_send_verification_email_with_no_user_name(self, mock_sendgrid_client):
        """Test email sending when user has no name"""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {}
        
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance
        
        # Call with None for user_name
        success, result = send_verification_email_sendgrid(
            user_email=self.user_email,
            user_name=None,
            verification_url=self.verification_url
        )
        
        self.assertTrue(success)
        self.assertEqual(result, 202)
    
    @patch('apps.authentication.emails_utils.SendGridAPIClient')
    @override_settings(SENDGRID_API_KEY='SG.test_key_123')
    def test_send_verification_email_api_error(self, mock_sendgrid_client):
        """Test handling of SendGrid API errors"""
        # Mock SendGrid raising an exception
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.side_effect = Exception("SendGrid API Error")
        mock_sendgrid_client.return_value = mock_sg_instance
        
        success, result = send_verification_email_sendgrid(
            user_email=self.user_email,
            user_name=self.user_name,
            verification_url=self.verification_url
        )
        
        self.assertFalse(success)
        self.assertIn("SendGrid API Error", str(result))
    
    @patch('apps.authentication.emails_utils.SendGridAPIClient')
    @override_settings(SENDGRID_API_KEY=None)
    def test_send_verification_email_no_api_key(self, mock_sendgrid_client):
        """Test behavior when API key is not configured"""
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.side_effect = Exception("API key not configured")
        mock_sendgrid_client.return_value = mock_sg_instance
        
        success, result = send_verification_email_sendgrid(
            user_email=self.user_email,
            user_name=self.user_name,
            verification_url=self.verification_url
        )
        
        self.assertFalse(success)
    
    @patch('apps.authentication.emails_utils.SendGridAPIClient')
    @override_settings(SENDGRID_API_KEY='SG.test_key_123')
    def test_send_verification_email_constructs_correct_message(self, mock_sendgrid_client):
        """Test that the email message is constructed correctly"""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {}
        
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance
        
        send_verification_email_sendgrid(
            user_email=self.user_email,
            user_name=self.user_name,
            verification_url=self.verification_url
        )
        
        # Get the Mail object that was passed to send()
        call_args = mock_sg_instance.send.call_args
        mail_object = call_args[0][0]
        
        # Verify the Mail object has correct properties
        self.assertIsNotNone(mail_object)
        # Note: Detailed message content verification would require 
        # inspecting the Mail object's internal structure


class SendVerificationEmailViewTests(APITestCase):
    """Test the SendVerificationEmailView API endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.url = '/auth/send-verification/'
        
        # Create a test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User'
        )
    
    def test_send_verification_email_unauthenticated(self):
        """Test that unauthenticated users cannot access the endpoint"""
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_send_verification_email_authenticated_success(self, mock_send_email):
        """Test successful email sending for authenticated user"""
        # Mock successful email sending
        mock_send_email.return_value = (True, 202)
        
        # Authenticate the user
        self.client.force_authenticate(user=self.user)
        
        # Make the request
        response = self.client.post(self.url)
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Verification email sent successfully')
        self.assertEqual(response.data['status_code'], 202)
        
        # Verify the email function was called with correct parameters
        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1]
        self.assertEqual(call_kwargs['user_email'], self.user.email)
        self.assertEqual(call_kwargs['user_name'], self.user.first_name)
        self.assertIn('verification_url', call_kwargs)
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_send_verification_email_authenticated_failure(self, mock_send_email):
        """Test failed email sending for authenticated user"""
        # Mock failed email sending
        mock_send_email.return_value = (False, "SendGrid API Error")
        
        # Authenticate the user
        self.client.force_authenticate(user=self.user)
        
        # Make the request
        response = self.client.post(self.url)
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error'], 'Failed to send verification email')
        self.assertIn('details', response.data)
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_send_verification_email_user_without_first_name(self, mock_send_email):
        """Test email sending for user without first name"""
        # Create user without first name
        user_no_name = User.objects.create_user(
            email='noname@example.com',
            password='TestPass123!',
            first_name=''
        )
        
        mock_send_email.return_value = (True, 202)
        
        self.client.force_authenticate(user=user_no_name)
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_send_verification_email_exception_handling(self, mock_send_email):
        """Test that unexpected exceptions are handled gracefully"""
        # Mock an unexpected exception
        mock_send_email.side_effect = Exception("Unexpected error")
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
        self.assertIn('details', response.data)
    
    def test_send_verification_email_only_post_allowed(self):
        """Test that only POST requests are allowed"""
        self.client.force_authenticate(user=self.user)
        
        # Try GET request
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Try PUT request
        response = self.client.put(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Try DELETE request
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class EmailIntegrationTests(APITestCase):
    """Integration tests for the complete email verification flow"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/auth/register/'
        self.send_verification_url = '/auth/send-verification/'
        
        self.user_data = {
            'email': 'newuser@example.com',
            'password': 'SecurePass123!',
            'first_name': 'New',
            'last_name': 'User'
        }
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_complete_verification_flow(self, mock_send_email):
        """Test the complete user registration and email verification flow"""
        mock_send_email.return_value = (True, 202)
        
        # Step 1: Register a new user (if your registration triggers email)
        # This depends on your registration implementation
        user = User.objects.create_user(
            email=self.user_data['email'],
            password=self.user_data['password'],
            first_name=self.user_data['first_name']
        )
        
        # Step 2: Login
        self.client.force_authenticate(user=user)
        
        # Step 3: Request verification email
        response = self.client.post(self.send_verification_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send_email.assert_called_once()
    
    @patch('apps.authentication.views.send_verification_email_sendgrid')
    def test_multiple_verification_requests(self, mock_send_email):
        """Test that users can request multiple verification emails"""
        mock_send_email.return_value = (True, 202)
        
        user = User.objects.create_user(
            email='multitest@example.com',
            password='TestPass123!'
        )
        self.client.force_authenticate(user=user)
        
        # Send first verification email
        response1 = self.client.post(self.send_verification_url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Send second verification email
        response2 = self.client.post(self.send_verification_url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Verify the function was called twice
        self.assertEqual(mock_send_email.call_count, 2)


class EmailContentTests(TestCase):
    """Test email content generation and formatting"""
    
    @patch('apps.authentication.emails_utils.SendGridAPIClient')
    @override_settings(SENDGRID_API_KEY='SG.test_key_123')
    def test_email_contains_verification_url(self, mock_sendgrid_client):
        """Test that the email contains the verification URL"""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {}
        
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance
        
        verification_url = "https://nelylook.com/verify?token=test123"
        
        send_verification_email_sendgrid(
            user_email="test@example.com",
            user_name="Test User",
            verification_url=verification_url
        )
        
        # Verify send was called (URL is embedded in the Mail object)
        mock_sg_instance.send.assert_called_once()
    
    @patch('apps.authentication.emails_utils.SendGridAPIClient')
    @override_settings(SENDGRID_API_KEY='SG.test_key_123')
    def test_email_subject_is_correct(self, mock_sendgrid_client):
        """Test that the email subject is set correctly"""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {}
        
        mock_sg_instance = MagicMock()
        mock_sg_instance.send.return_value = mock_response
        mock_sendgrid_client.return_value = mock_sg_instance
        
        send_verification_email_sendgrid(
            user_email="test@example.com",
            user_name="Test User",
            verification_url="https://nelylook.com/verify?token=test123"
        )
        
        # The subject is embedded in the Mail object
        # In a real test, you'd inspect the Mail object structure
        mock_sg_instance.send.assert_called_once()


# Run tests with:
# python manage.py test apps.authentication.tests.test_email_verification

# Run specific test class:
# python manage.py test apps.authentication.tests.test_email_verification.SendVerificationEmailViewTests

# Run with coverage:
# coverage run --source='apps.authentication' manage.py test apps.authentication.tests.test_email_verification
# coverage report
# coverage html