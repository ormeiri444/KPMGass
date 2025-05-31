import streamlit as st
import requests
import json
from datetime import datetime
from typing import List, Dict
import subprocess
import threading
import time
import os
import sys

# Configure page
st.set_page_config(
    page_title="Medical HMO Chatbot",
    page_icon="🏥",
    layout="wide"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Function to start FastAPI backend
def start_fastapi_backend():
    """Start the FastAPI backend server in a separate process"""
    try:
        # Get the directory of the current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        main_py_path = os.path.join(current_dir, "main.py")
        
        # Start the FastAPI server
        subprocess.Popen([sys.executable, main_py_path], 
                        cwd=current_dir,
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        # Wait a bit for the server to start
        time.sleep(2)
        
        # Test if server is running
        for i in range(10):  # Try for 10 seconds
            try:
                response = requests.get(f"{API_BASE_URL}/health", timeout=1)
                if response.status_code == 200:
                    return True
            except:
                time.sleep(1)
        return False
    except Exception as e:
        st.error(f"Failed to start backend server: {e}")
        return False

# Check if backend is running, if not start it
if "backend_started" not in st.session_state:
    st.session_state.backend_started = False

if not st.session_state.backend_started:
    try:
        # First check if backend is already running
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            st.session_state.backend_started = True
    except:
        # Backend not running, start it
        with st.spinner("Starting backend server..."):
            if start_fastapi_backend():
                st.session_state.backend_started = True
                st.success("Backend server started successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to start backend server. Please check your setup.")
                st.stop()

# Initialize session state
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "user_info" not in st.session_state:
    st.session_state.user_info = {
        "first_name": None,
        "last_name": None,
        "id_number": None,
        "gender": None,
        "age": None,
        "hmo_name": None,
        "hmo_card_number": None,
        "insurance_tier": None
    }
if "current_phase" not in st.session_state:
    st.session_state.current_phase = "collection"
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "hebrew"


def reset_conversation():
    """Reset conversation and user info to start fresh"""
    st.session_state.conversation_history = []
    st.session_state.user_info = {
        "first_name": None,
        "last_name": None,
        "id_number": None,
        "gender": None,
        "age": None,
        "hmo_name": None,
        "hmo_card_number": None,
        "insurance_tier": None
    }
    st.session_state.current_phase = "collection"


def call_chat_api(message: str) -> Dict:
    """Call the FastAPI chat endpoint"""
    try:
        payload = {
            "message": message,
            "user_info": st.session_state.user_info,
            "conversation_history": st.session_state.conversation_history,
            "phase": st.session_state.current_phase,
            "language": st.session_state.selected_language
        }

        response = requests.post(f"{API_BASE_URL}/chat", json=payload, timeout=30)

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Backend server connection failed. Please refresh the page.")
        return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None


def add_message_to_history(role: str, content: str):
    """Add a message to conversation history"""
    st.session_state.conversation_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })


def display_chat_history():
    """Display the conversation history"""
    for msg in st.session_state.conversation_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        elif msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.write(msg["content"])


def main():
    # Header
    st.title("🏥 Medical HMO Chatbot")

    if st.session_state.selected_language == "hebrew":
        st.subheader("צ'אטבוט לשירותי בריאות - קופות החולים בישראל")
    else:
        st.subheader("Healthcare Services Chatbot - Israeli Health Funds")

    # Language selection
    col1, col2 = st.columns([1, 4])
    with col1:
        language = st.selectbox(
            "Language / שפה:",
            ["hebrew", "english"],
            index=0 if st.session_state.selected_language == "hebrew" else 1
        )
        if language != st.session_state.selected_language:
            st.session_state.selected_language = language
            # Reset conversation when language changes
            reset_conversation()
            st.rerun()

    # Sidebar with user info
    # display_user_info_sidebar()  # Removed sidebar

    # Phase indicator
    phase_text = "איסוף מידע" if st.session_state.current_phase == "collection" else "שאלות ותשובות"
    if st.session_state.selected_language == "english":
        phase_text = "Information Collection" if st.session_state.current_phase == "collection" else "Q&A"

    st.info(f"Current Phase / שלב נוכחי: {phase_text}")

    # Chat interface
    st.header("💬 Chat")

    # Display chat history
    if st.session_state.conversation_history:
        display_chat_history()
    else:
        # Initial message to start the collection process
        if st.session_state.selected_language == "hebrew":
            welcome_msg = "שלום! אני כאן לעזור לך עם שאלות בנוגע לשירותי קופת החולים שלך. בואו נתחיל!"
        else:
            welcome_msg = "Hello! I'm here to help you with questions about your health fund services. Let's get started!"

        with st.chat_message("assistant"):
            st.write(welcome_msg)

        # Automatically start the collection process
        if not st.session_state.conversation_history:
            with st.spinner("Starting information collection / מתחיל באיסוף מידע..."):
                start_msg = "בואו נתחיל באיסוף המידע" if st.session_state.selected_language == "hebrew" else "Let's start collecting the information"
                response = call_chat_api(start_msg)

                if response:
                    add_message_to_history("assistant", response["response"])
                    st.session_state.user_info = response["updated_user_info"]
                    st.session_state.current_phase = response["phase"]
                    st.rerun()

    # Chat input
    if prompt := st.chat_input("Type your message here / הקלד את הודעתך כאן"):
        # Add user message to history
        add_message_to_history("user", prompt)

        # Display user message
        with st.chat_message("user"):
            st.write(prompt)

        # Call API
        with st.spinner("Processing / מעבד..."):
            response = call_chat_api(prompt)

        if response:
            # Add assistant response to history
            add_message_to_history("assistant", response["response"])

            # Update user info if changed
            st.session_state.user_info = response["updated_user_info"]

            # Update phase if changed
            st.session_state.current_phase = response["phase"]

            # Display assistant response
            with st.chat_message("assistant"):
                st.write(response["response"])

            # Rerun to update sidebar
            st.rerun()

    # Clear conversation button
    if st.button("🔄 Start New Conversation / התחל שיחה חדשה"):
        reset_conversation()
        st.rerun()

    # Footer
    st.divider()
    if st.session_state.selected_language == "hebrew":
        st.caption("מערכת ייעוץ רפואי לקופות החולים בישראל - מכבי, מאוחדת, כללית")
    else:
        st.caption("Medical consultation system for Israeli health funds - Maccabi, Meuhedet, Clalit")

import subprocess


if __name__ == "__main__":
    main()