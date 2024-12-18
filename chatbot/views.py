"""View functions for Django chatbot with persistent multi-session support.

This module contains view functions to handle the chatbot application built using Django.
The main functionalities include:

- Starting and managing chat sessions for authenticated users.
- Handling AI-generated responses using the Gemini model.
- Uploading and processing documents for query-based interactions.
- Querying documents using a Retrieval-Augmented Generation (RAG) pipeline.
- Managing session-based document associations.
- Deleting chat sessions and cleaning up associated data.

Typical usage example:

    1. A user logs in and starts a chat session.
    2. The chatbot() function manages chat interactions and session history.
    3. The upload_document() function processes user-uploaded documents for querying.
    4. The delete_session() function removes a specified chat session and associated files.
"""
import uuid
from pathlib import Path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Min
from django_chatgpt_clone.settings import API_KEY
from chatbot.utils.ask_gemini import ask_gemini
from .models import Chat,Document
from .utils.rag_utils import RAGProcessor

rag_processor = RAGProcessor(API_KEY)

@login_required
def upload_document(request):
    """Handle document upload and processing."""
    if request.method == 'POST' and request.FILES.get('document'):
        document = request.FILES['document']
        title = document.name
        session_id = request.POST.get('session_id')

        doc = Document.objects.create(
            user=request.user,
            session_id=session_id,
            title=title,
            file=document
        )
        try:
            vector_store_path = rag_processor.process_document(
                doc.file.path,
                str(doc.id),
            )
            doc.embedding_store = vector_store_path
            doc.processed = True
            doc.save()
            return JsonResponse({'success': True, 'message': 'Document processed successfully'})
        except Exception as e:
            doc.delete()
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'No document provided'})

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
        # time.sleep(1)
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
            try:
                user_docs = Document.objects.filter(
                    user=request.user,
                    session_id=current_session_id,
                    processed=True
                )
                vector_store_paths = [doc.embedding_store for doc in user_docs
                                      if doc.embedding_store]
                chat_history = Chat.objects.filter(
                    user=request.user,
                    session_id=current_session_id
                ).order_by('created_at').values('message', 'response')

                response = None
                if vector_store_paths:
                    try:
                        response = rag_processor.query_documents(
                            vector_store_paths,
                            message,
                            list(chat_history)
                        )
                    except Exception as doc_query_error:
                        print(f"Document query failed: {doc_query_error}")

                if not response:
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
            except Exception:
                error_response = "Service temporarily unavailable. Please try again later."
                return JsonResponse({
                    'message': message,
                    'response': error_response,
                    'session_id': current_session_id
                }, status=500)

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
        'all_sessions': session_list,
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
    if not chat_session.exists():
        return redirect('chatbot')

    try:
        user_documents = Document.objects.filter(user=request.user)
        for doc in user_documents:
            if doc.file:
                file_path = Path(doc.file.path)
                if file_path.exists():
                    try:
                        file_path.unlink()
                        print(f"Deleted document file: {file_path}")
                    except Exception as file_error:
                        print(f"Error deleting file {file_path}: {file_error}")

            if doc.embedding_store:
                try:
                    rag_processor.cleanup_vector_stores()
                except Exception as cleanup_error:
                    print(f"Error cleaning up vector store: {cleanup_error}")

            doc.delete()

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

    except Exception as general_error:
        print(f"General error during cleanup: {general_error}")

    return redirect('chatbot')
