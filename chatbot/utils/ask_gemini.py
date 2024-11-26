"""
Module: ask_gemini
Description: Provides functionality to interact with the 
Gemini AI model using Google Generative AI API.
"""
import google.generativeai as genai
from django.conf import settings


genai_api_key = settings.API_KEY
genai.configure(api_key=genai_api_key)

def ask_gemini(message, history=None):
    """Interact with the Gemini model to generate content based on the input message."""
    try:
        if not history:
            history = []
        context = "\n".join(
            [
                f"You: {m['message']}\nAI Chatbot: {m['response']}"
                for m in history
                if isinstance(m, dict) and 'message' in m and 'response' in m
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
    