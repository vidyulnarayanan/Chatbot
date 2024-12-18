"""URL configuration for the django_chatgpt_clone project.

This module defines the URL routing for the Django project, mapping URL paths
to the appropriate app-level URL configurations. It acts as the entry point 
for directing HTTP requests to the corresponding views within the project."""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', include('chatbot.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
