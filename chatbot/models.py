"""Chat Model which supports chatbot functionalities.

This module defines the `Chat` model used to store chat conversations
between users and the chatbot. Each chat instance contains the user 
who initiated the chat, a unique session ID, the user's message, the 
chatbot's response, and the timestamp when the chat was created.

Classes:
    Chat: Represents a single chat interaction with fields for the user, 
    session ID, message, response, and creation timestamp."""

import uuid
from django.db import models
from django.contrib.auth.models import User

class Chat(models.Model):
    """Chat model for storing user-chatbot interactions."""
    objects = models.Manager() # Explicitly mentioned here for pylint score in view functions
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f'Session {self.session_id} - '
            f'{getattr(self.user, "username", "Unknown User")}: '
            f'{self.message}'
        )
    