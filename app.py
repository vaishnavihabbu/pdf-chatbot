import streamlit as st
import requests

# FastAPI backend URL
API_URL = "http://127.0.0.1:8000"

# Streamlit UI
st.set_page_config(page_title="PDF Chatbot", layout="wide")
st.title("📄💬 PDF Chatbot")

# File Upload Section
folder_path = st.text_input("Enter folder path containing PDFs:")
if st.button("Upload PDFs"):
    if folder_path:
        response = requests.post(f"{API_URL}/upload_folder/", params={"folder_path": folder_path})
        if response.status_code == 200:
            st.success("PDFs uploaded and processed successfully!")
        else:
            st.error(f"Error: {response.json().get('error', 'Unknown error')}")
    else:
        st.warning("Please enter a folder path.")

# Chat Interface
st.subheader("Chat with your PDFs")
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# User input
user_query = st.text_input("Ask a question about the PDFs:")
if st.button("Ask") and user_query:
    response = requests.get(f"{API_URL}/query/", params={"question": user_query})
    if response.status_code == 200:
        bot_response = response.json()["response"]
        st.session_state.chat_history.append(("You", user_query))
        st.session_state.chat_history.append(("Bot", bot_response))
    else:
        st.error("Error fetching response from the server.")

# Display Chat History
for sender, message in st.session_state.chat_history:
    with st.chat_message("user" if sender == "You" else "assistant"):
        st.markdown(f"**{sender}:** {message}")