import streamlit as st
import requests
import os

API_URL = os.environ.get("API_URL", "http://localhost:8080")

st.set_page_config(page_title="NEM Grid Co-Pilot", page_icon="⚡", layout="wide")

st.title("⚡ NEM Grid Co-Pilot")
st.markdown("Ask questions about Australian Energy Market Operator (AEMO) market notices.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is the latest capacity shortfall notice?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching AEMO notices..."):
            try:
                response = requests.post(f"{API_URL}/ask", json={"query": prompt})
                response.raise_for_status()
                answer = response.json().get("answer", "No answer received.")
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"Error querying the backend API: {e}")
