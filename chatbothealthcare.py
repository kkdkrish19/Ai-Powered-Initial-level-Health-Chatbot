"""
Ai Powerd Initial health Care
Streamlit + LangChain + Groq + SQLite (All-in-One)
"""

import os
import sqlite3
import streamlit as st
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# =========================================================
# CONFIGURATION
# =========================================================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

DB_PATH = "health_chat.db" 

MODEL = "llama-3.3-70b-versatile"

st.set_page_config(page_title="Ai Powerd Initial health Care", page_icon="⚕️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f0f8ff; }
    .main-header { font-size: 2.5rem; color: #0056b3; text-align: center; font-weight: bold; }
    .footer { position: fixed; bottom: 10px; right: 20px; font-size: 14px; color: #fff; background-color: #0056b3; padding: 8px 12px; border-radius: 8px; font-weight: bold; z-index: 1000; box-shadow: 2px 2px 5px rgba(0,0,0,0.3); }
</style>
<div class="footer">Created by: Krishna Kasabwala</div>
""", unsafe_allow_html=True)

# =========================================================
# DATABASE CONNECTION & INITIALIZATION
# =========================================================
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            mobile TEXT
        );
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

init_db()

# =========================================================
# DB HELPER FUNCTIONS
# =========================================================
def signup_user(username, password, email, mobile):
    conn = get_connection()
    user = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if user:
        conn.close()
        return False, "Username already exists. Suggestion: Try adding a number or changing your username."
    conn.execute("INSERT INTO users (username, password, email, mobile) VALUES (?, ?, ?, ?)", 
                 (username, password, email, mobile))
    conn.commit()
    conn.close()
    return True, "Signup successful! You can now login."

def login_user(username, password):
    conn = get_connection()
    user = conn.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
                        (username, password)).fetchone()
    conn.close()
    return bool(user)

def save_message(username, role, content):
    if not username: return
    conn = get_connection()
    conn.execute("INSERT INTO conversation_memory (username, role, content) VALUES (?, ?, ?)",
                 (username, role, content))
    conn.commit()
    conn.close()

def load_history_db(username):
    if not username: return []
    conn = get_connection()
    rows = conn.execute("SELECT role, content FROM conversation_memory WHERE username = ? ORDER BY id", (username,)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

def load_langchain_history(username):
    if not username: return []
    conn = get_connection()
    rows = conn.execute("SELECT role, content FROM conversation_memory WHERE username = ? ORDER BY id", (username,)).fetchall()
    conn.close()
    
    history = []
    for row in rows:
        if row["role"] == "user":
            history.append(HumanMessage(content=row["content"]))
        else:
            history.append(AIMessage(content=row["content"]))
    return history

def create_chain(system_prompt: str, streaming: bool = False):
    llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL, temperature=0.7, max_retries=3, streaming=streaming)
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]) | llm | StrOutputParser()

# =========================================================
# SESSION STATE
# =========================================================
if "mode" not in st.session_state:
    st.session_state.mode = "Normal Chat"
if "username" not in st.session_state:
    st.session_state.username = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
with st.sidebar:
    st.markdown("## Navigation")
    
    if st.button("🚨 EMERGENCY MODE 🚨", use_container_width=True, type="primary"):
        st.session_state.mode = "Emergency"
        st.session_state.messages = []
        st.rerun()
        
    if st.button("🩺 Normal Chat", use_container_width=True):
        st.session_state.mode = "Normal Chat"
        if st.session_state.username:
            st.session_state.messages = load_history_db(st.session_state.username)
        else:
            st.session_state.messages = []
        st.rerun()

    st.divider()
    if st.session_state.mode == "Normal Chat" and st.session_state.username:
        st.success(f"Logged in as: {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

st.markdown('<p class="main-header">Ai Powerd Initial health Care</p>', unsafe_allow_html=True)

# =========================================================
# EMERGENCY MODE
# =========================================================
if st.session_state.mode == "Emergency":
    st.error("🚨 **EMERGENCY MODE ACTIVE** 🚨 - Immediate Assistance. ALWAYS CALL TO EMERGENCY NUMBER FOR SEVERE EMERGENCIES!")
    st.error("108 — Medical & Disaster Helpline || 100 — Police Helpline || 101 — Fire Brigade (for fire accidents, explosions) || 102 — Ambulance Service (for medical emergencies, accidents) || 112 — National Emergency Number || 1962 — Animal Helpline || 139 — Railways Helpline")
        
    
    st.markdown("### Quick Suggestions:")
    cols = st.columns(3)
    suggestion = None
    if cols[0].button("🔥 Burn / Scald", use_container_width=True): suggestion = "Someone just got a severe burn, what do I do?"
    if cols[1].button("🗣️ Choking", use_container_width=True): suggestion = "Someone is choking and can't breathe, help!"
    if cols[2].button("💔 Heart Attack Symptoms", use_container_width=True): suggestion = "I suspect someone is having a heart attack, what are the steps?"
    st.divider()
    
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
    prompt = st.chat_input("Describe the emergency...")
    if suggestion: prompt = suggestion
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing emergency..."):
                try:
                    sys_prompt = "IN INDIA You are an Emergency First Aid AI. Provide clear, immediate, actionable steps. ALWAYS remind the user to call 911 or local emergency services."
                    chain = create_chain(sys_prompt, streaming=False)
                    answer = chain.invoke({"input": prompt, "history": []})
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# =========================================================
# NORMAL MODE
# =========================================================
elif st.session_state.mode == "Normal Chat":
    
    if not st.session_state.username:
        st.info("You must Login or Sign Up to access the Normal Health Chat and view your history.")
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.markdown("### Login")
            u_login = st.text_input("Username", key="l_user")
            p_login = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login", type="primary"):
                if login_user(u_login, p_login):
                    st.session_state.username = u_login
                    st.session_state.messages = load_history_db(u_login)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
                    
        with tab2:
            st.markdown("### Create an Account")
            u_sign = st.text_input("Choose Username")
            p_sign = st.text_input("Choose Password", type="password")
            e_sign = st.text_input("Email ID (Optional)")
            m_sign = st.text_input("Mobile Number (Optional)")
            if st.button("Sign Up", type="primary"):
                if not u_sign or not p_sign:
                    st.warning("Username and Password are required.")
                else:
                    success, msg = signup_user(u_sign, p_sign, e_sign, m_sign)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
    
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        prompt = st.chat_input("Ask a health question...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            
            with st.chat_message("assistant"):
                try:
                    sys_prompt = "IN INDIA You are a helpful Medical and Health Assistant. Provide accurate general health information. Remind users to consult a doctor for diagnosis."
                    chain = create_chain(sys_prompt, streaming=True)
                    history = load_langchain_history(st.session_state.username)
                    
                    # Using Streamlit's write_stream for typewriter effect directly from Langchain!
                    response = chain.stream({"input": prompt, "history": history})
                    answer = st.write_stream(response)
                    
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    # Save to DB
                    save_message(st.session_state.username, "user", prompt)
                    save_message(st.session_state.username, "assistant", answer)
                    
                except Exception as e:
                    st.error(f"Error communicating with AI: {str(e)}")
