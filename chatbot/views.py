"""View functions for Django chatbot with persistent multi-session support.

This module contains view functions for handling a chatbot application built using Django. The 
main functionalities include:

- Starting new chat sessions.
- Managing existing chat sessions for authenticated users.
- Interacting with the Gemini model for AI-generated responses.
- Deleting chat sessions and handling user requests related to sessions.

Typical usage example:

    1. A user logs in and starts a chat session.
    2. The `chatbot()` function manages chat interactions and session history.
    3. The `create_new_chat()` function creates a new session upon user request.
    4. The `delete_session()` function deletes a specified chat session.

"""

import uuid
import google.generativeai as genai
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Min
from django_chatgpt_clone.settings import API_KEY
from .models import Chat

genai.configure(api_key=API_KEY)

def ask_gemini(message,history=None):
    """Interact with the Gemini model to generate content based on the input message."""
    try:
        context = "\n".join(
            [
                f"You: {m['message']}\nAI Chatbot: {m['response']}"
                for m in history
                if m['message']
            ]
        )
        prompt = f"{context}\nYou: {message}\nAI Chatbot:"
        model = genai.GenerativeModel("gemini-1.5-flash-002")
        response = model.generate_content(prompt)
        if response:
            return response.text
        return "Sorry, I didn't get a response. Please try again."
    except Exception as e:
        print(f"Error while interacting with Gemini API: {e}")
        return "An error occurred while processing your request. Please try again later."


@login_required
def chatbot(request):
    """Handle the core functionalities of the chatbot."""
    all_sessions = (
        Chat.objects.filter(user=request.user)
        .values('session_id')
        .annotate(first_message=Min('created_at'))
        .order_by('first_message')
    )
    current_session_id = None

    if request.method == 'POST':
        current_session_id = request.POST.get('session_id')
    else:
        if request.GET.get('new_chat'):
            current_session_id = str(uuid.uuid4())
            Chat.objects.create(
                user=request.user,
                session_id=current_session_id,
                message="",
                response=(f"Hi {request.user.username}, I'm your AI Chatbot."
                          "How can I help you today?"),
                created_at=timezone.now()
            )
        else:
            current_session_id = request.GET.get('session_id')
            if not current_session_id:
                if all_sessions.exists():
                    current_session_id = str(all_sessions.last()['session_id'])
                else:
                    current_session_id = str(uuid.uuid4())
                    welcome_msg = (f"Hi {request.user.username}, I'm your AI Chatbot."
                                   "How can I help you today?")
                    Chat.objects.create(
                        user=request.user,
                        session_id=current_session_id,
                        message="",
                        response=welcome_msg,
                        created_at=timezone.now()
                    )

    session_chats = Chat.objects.filter(
        user=request.user,
        session_id=current_session_id
    ).order_by('created_at')
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            chat_history = Chat.objects.filter(
                user=request.user,
                session_id=current_session_id
            ).order_by('created_at').values('message', 'response')
            response = ask_gemini(message, list(chat_history))
            Chat.objects.create(
                user=request.user,
                session_id=current_session_id,
                message=message,
                response=response,
                created_at=timezone.now()
            )
            return JsonResponse({
                'message': message,
                'response': response,
                'session_id': current_session_id
            })
    session_list = []
    for session in all_sessions:
        first_chat = Chat.objects.filter(
            user=request.user,
            session_id=session['session_id']
        ).exclude(message="").first()
        title = "New Chat"
        if first_chat and first_chat.message:
            title = (
                first_chat.message[:30] + "..."
                if len(first_chat.message) > 30
                else first_chat.message
            )

        session_list.append({
            'id': session['session_id'],
            'title': title,
            'timestamp': session['first_message']
        })

    return render(request, 'chatbot.html', {
        'chats': session_chats,
        'current_session_id': current_session_id,
        'all_sessions': session_list
    })


@login_required
def create_new_chat(request):
    """Create a new chat session for the user."""
    if request.method == 'POST':
        new_session_id = str(uuid.uuid4())
        welcome_msg = (f"Hi {request.user.username}, I'm your AI Chatbot."
                       "How can I help you today?")
        Chat.objects.create(
            user=request.user,
            session_id=new_session_id,
            message="",
            response=welcome_msg,
            created_at=timezone.now()
        )
        return JsonResponse({
            'session_id': new_session_id,
            'success': True,
            'message': 'New chat session created successfully'
        })

    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    }, status=400)


@login_required
def delete_session(request, session_id):
    """Delete a chat session for the user."""
    chat_session = Chat.objects.filter(user=request.user, session_id=session_id)
    if chat_session.exists():
        chat_session.delete()

        remaining_sessions = (
            Chat.objects.filter(user=request.user)
            .values('session_id')
            .annotate(first_message=Min('created_at'))
            .order_by('-first_message')
        )

        if remaining_sessions.exists():
            next_session = remaining_sessions.first()["session_id"]
            return redirect(f'/chatbot?session_id={next_session}')
    return redirect('chatbot')
