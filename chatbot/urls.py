"""Defines URL patterns for Chatbot Working."""

from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('chatbot/', views.chatbot, name='chatbot'),
    path('create-new-chat/', views.create_new_chat, name='create_new_chat'),
    path('delete_session/<str:session_id>/', views.delete_session, name='delete_session'),
    path('upload-document/', views.upload_document, name='upload_document'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
