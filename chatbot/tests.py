"""
Unit tests for the Django chatbot application.

This module contains test cases for the views of the chatbot application built using Django. 
It covers various functionalities including:

- Authenticating users and ensuring proper access to chat views.
- Creating new chat sessions and interacting with the chatbot.
- Sending and receiving messages within a chat session.
- Creating and deleting chat sessions through API endpoints.
- Testing the behavior of the chatbot when users are not authenticated.

Test scenarios include:

1. Testing that an authenticated user can access the chatbot and view chat sessions.
2. Testing the creation of a new chat session for a user.
3. Testing posting a message to the chatbot and receiving a response.
4. Testing the creation of a new chat session via the API endpoint.
5. Testing the deletion of a chat session.
6. Testing that unauthenticated users are redirected to the login page.
"""

import uuid
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Chat

class ChatbotViewTests(TestCase):
    """Test cases for chatbot views."""

    def setUp(self):
        """Set up a test user and test client."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            email='testuser@example.com'
        )
        self.session_id = str(uuid.uuid4())
        Chat.objects.create(
            user=self.user,
            session_id=self.session_id,
            message='Hello',
            response='Hello there!',
            created_at=timezone.now()
        )

    def test_chatbot_view_authenticated_user(self):
        """Test the chatbot view for an authenticated user."""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('chatbot'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chatbot.html')
        self.assertIn('chats', response.context)
        self.assertIn('current_session_id', response.context)

    def test_chatbot_view_create_new_session(self):
        """Test creating a new chat session."""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('chatbot') + '?new_chat=true')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Hi testuser', response.context['chats'][0].response)

    @patch('chatbot.views.ask_gemini')
    def test_post_message_to_chatbot(self, mock_ask_gemini):
        """Test posting a message to the chatbot."""
        mock_ask_gemini.return_value = "Hello to you too! How can I help you today!\n"
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('chatbot'), {
            'session_id': self.session_id,
            'message': 'Hello AI'
        })
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                'message': 'Hello AI',
                'response': 'Hello to you too! How can I help you today!\n',
                'session_id': self.session_id
            }
        )

    def test_create_new_chat_view(self):
        """Test the create new chat view."""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.post(reverse('create_new_chat'))
        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        self.assertTrue(response_json['success'])
        self.assertIn('New chat session created successfully', response_json['message'])

    def test_delete_session_view(self):
        """Test the delete session view."""
        self.client.login(username='testuser', password='testpassword')
        response = self.client.get(reverse('delete_session', args=[self.session_id]))
        self.assertRedirects(response, reverse('chatbot'))
        self.assertFalse(Chat.objects.filter(session_id=self.session_id).exists())

    def test_chatbot_redirect_if_not_authenticated(self):
        """Test that an unauthenticated user is redirected to the login page."""
        response = self.client.get(reverse('chatbot'))
        self.assertRedirects(response, '/login/?next=/chatbot/')
