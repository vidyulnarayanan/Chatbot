"""
Unit tests for user authentication features in a Django application.

This module contains test cases for the core user authentication functionalities, including:

- User registration with validation checks for email format, uniqueness, and password strength.
- User login functionality, covering both valid and invalid login scenarios.
- User logout functionality, ensuring proper redirection after logging out.

Test scenarios include:

1. Testing user registration with invalid email format.
2. Testing user registration with an already taken email.
3. Testing successful user registration and redirection to the login page.
4. Testing user login with valid credentials.
5. Testing user login with invalid email.
6. Testing user login with invalid password.
7. Testing the logout functionality and ensuring proper redirection.

"""


from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages


class UserRegistrationTests(TestCase):
    """Class for Registration view functions test cases"""
    def test_register_user_invalid_email(self):
        """Test user registration with invalid email format."""
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid email format.")

    def test_register_user_email_taken(self):
        """Test user registration with an already taken email."""
        User.objects.create_user(
            username='existinguser',
            email='testuser@example.com',
            password='TestPass123!')
        data = {
            'username': 'newuser',
            'email': 'testuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        response = self.client.post(reverse('register'), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email is already taken.")

    def test_register_user_successful(self):
        """Test user registration with valid data."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
        }
        response = self.client.post(reverse('register'), data)
        self.assertRedirects(response, reverse('login'))
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]), 'Account created successfully. Please log in.')


class UserAuthenticationTests(TestCase):
    """Class for Login and Logout view functions test cases"""
    def setUp(self):
        """Set up a test user."""
        self.username = 'testuser'
        self.email = 'testuser@example.com'
        self.password = 'Password123!'
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password)
        self.user.save()

    def test_login_valid_user(self):
        """Test login with valid user credentials."""
        response = self.client.post(reverse('login'), {
            'email': self.email,
            'password': self.password
        })
        self.assertRedirects(response, reverse('chatbot'))
        self.assertEqual(str(self.user), str(response.wsgi_request.user))

    def test_login_invalid_email(self):
        """Test login with an invalid email."""
        response = self.client.post(reverse('login'), {
            'email': 'wrongemail@example.com',
            'password': self.password
        })
        self.assertContains(response, 'User does not exist.')
        self.assertEqual(response.status_code, 200)

    def test_login_invalid_password(self):
        """Test login with an invalid password."""
        response = self.client.post(reverse('login'), {
            'email': self.email,
            'password': 'WrongPassword123!'
        })
        self.assertContains(response, 'Invalid email or password.')
        self.assertEqual(response.status_code, 200)

    def test_logout_view(self):
        """Test logout functionality."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        response = self.client.get(reverse('chatbot'))
        self.assertRedirects(response, reverse('login') + '?next=' + reverse('chatbot'))
