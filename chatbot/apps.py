"""
This module defines the configuration for the 'chatbot' app in the Django project.
It specifies app-level settings and metadata.
"""
from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    """
    Configuration class for the 'chatbot' application.

    This class specifies default settings and metadata for the app, such as
    the default field type for auto-generated fields and the app name.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
