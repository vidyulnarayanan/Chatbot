"""
Admin configuration for the chatbot application.

This module registers the Chat model with the Django admin site.
"""

from django.contrib import admin
from . models import Chat

admin.site.register(Chat)
