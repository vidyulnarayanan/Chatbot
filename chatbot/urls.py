"""Defines URL patterns for Chatbot Working."""

from django.urls import path
from . import views

urlpatterns = [
    path('chatbot/', views.chatbot, name='chatbot'),
    path('create-new-chat/', views.create_new_chat, name='create_new_chat'),
    path('delete_session/<str:session_id>/', views.delete_session, name='delete_session'),
]
