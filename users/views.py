"""This module contains the views for user registration, login, and logout functionality.

The module handles the essential user authentication features for a Django application, including:

- User registration with validation checks for email format and password strength.
- Login with email-based authentication.
- User logout and redirection to the login page.

Typical usage example:

    1. A user registers an account through `register_view()`, which checks for valid input and 
       saves the user to the database.
    2. The user logs in using `login_view()`, which authenticates based on their email and 
       password.
    3. The user logs out through `logout_view()`, which clears the session and redirects to 
       the login page.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

def validate_password_strength(password):
    """Checks if the password meets the minimum strength requirements."""
    if len(password) < 8:
        return False
    if not any(char.isupper() for char in password):
        return False
    if not any(char in '!@#$%^&*()_+' for char in password):
        return False
    return True

def register_view(request):
    """Handles user registration, including form display and form submission."""
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password_confirm = request.POST['password_confirm']

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Invalid email format.')
            return render(request, 'register.html', {'email': email, 'username': username})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email is already taken.')
            return render(request, 'register.html', {'email': email, 'username': username})
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username is already taken.')
            return render(request, 'register.html', {'email': email, 'username': username})

        if not validate_password_strength(password):
            messages.error(
                request, (
                    'Password must be at least 8 characters long, contain an uppercase letter, '
                    'and a special character.')
            )
            return render(request, 'register.html', {'email': email, 'username': username})

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'register.html', {'email': email, 'username': username})

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, 'Account created successfully. Please log in.')
        return redirect('login')

    return render(request, 'register.html')


def login_view(request):
    """Handles user login, including form display and form submission."""
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            user_obj = None
        if user_obj:
            user = authenticate(request, username=user_obj.username, password=password)
            if user is not None:
                login(request, user)
                return redirect('chatbot')
            messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'User does not exist.')
        return render(request, 'login.html', {'email': email})
    return render(request, 'login.html')


def logout_view(request):
    """Logs the user out and redirects to the login page."""
    logout(request)
    return redirect('login')
