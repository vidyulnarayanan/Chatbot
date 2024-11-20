"""
This module defines the configuration for the 'users' app.

It sets up the default auto field type and app name for the Django application.
"""

from django.apps import AppConfig

class UsersConfig(AppConfig):
    """Configuration class for the 'users' application."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
