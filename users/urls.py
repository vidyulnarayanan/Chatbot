"""Defines URL patterns for user authentication views.

This module maps URL paths to their corresponding view functions to handle 
the core user authentication functionalities, including registration, login, 
and logout within a Django application."""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
