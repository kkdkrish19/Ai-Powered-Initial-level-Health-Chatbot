"""
Frontend for Ai Powerd Initial health Care
Streamlit interacting with FastAPI
"""
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Ai Powerd Initial health Care", page_icon="⚕️", layout="wide")

# =========================================================
# THEME & CSS
# =========================================================
st.markdown("""
<style>
    .stApp { background-color: #f0f8ff; }
    .main-header { font-size: 2.5rem; color: #0056b3; text-align: center; font-weight: bold; }
    
    /* Footer Styling */
    .footer { 
        position: fixed; 
        bottom: 10px; 
        right: 20px; 
        font-size: 14px; 
        color: #fff; 
        background-color: #0056b3; 
        padding: 8px 12px; 
        border-radius: 8px; 
        font-weight: bold; 
        z-index: 1000;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
</style>
<div class="footer">Created by: Krishna Kasabwala</div>
""", unsafe_allow_html=True)

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
    
    # Emergency button highlighted prominently
    if st.button("🚨 EMERGENCY MODE 🚨", use_container_width=True, type="primary"):
        st.session_state.mode = "Emergency"
        st.session_state.messages = []
        st.rerun()
        
    if st.button("🩺 Normal Chat", use_container_width=True):
        st.session_state.mode = "Normal Chat"
        if st.session_state.username:
            # Load history if logged in
            try:
                res = requests.get(f"{API_URL}/history/{st.session_state.username}")
                if res.status_code == 200:
                    st.session_state.messages = res.json()
            except:
                pass
        else:
            st.session_state.messages = []
        st.rerun()

    st.divider()
    
    # Show logout if logged in
    if st.session_state.mode == "Normal Chat" and st.session_state.username:
        st.success(f"Logged in as: {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.username = None
            st.session_state.messages = []
            st.rerun()

# Title
st.markdown('<p class="main-header">Ai Powerd Initial health Care</p>', unsafe_allow_html=True)

# =========================================================
# EMERGENCY MODE UI
# =========================================================
if st.session_state.mode == "Emergency":
    st.error("🚨 **EMERGENCY MODE ACTIVE** 🚨 - Immediate Assistance. YOU ALWAYS FIRST CALL 108 FOR SEVERE EMERGENCIES!")
    
    # Search Suggestions / Quick Action Buttons
    st.markdown("### Quick Suggestions:")
    cols = st.columns(3)
    suggestion = None
    if cols[0].button("🔥 Burn / Scald", use_container_width=True): 
        suggestion = "Someone just got a severe burn, what do I do?"
    if cols[1].button("🗣️ Choking", use_container_width=True): 
        suggestion = "Someone is choking and can't breathe, help!"
    if cols[2].button("💔 Heart Attack Symptoms", use_container_width=True): 
        suggestion = "I suspect someone is having a heart attack, what are the steps?"
    
    st.divider()
    
    # Display chat
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"])
        
    # Get input from text or suggestion button
    prompt = st.chat_input("Describe the emergency...")
    if suggestion: 
        prompt = suggestion
    
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing emergency..."):
                try:
                    # Emergency gives the whole answer together (not streaming)
                    res = requests.post(f"{API_URL}/chat/emergency", json={"message": prompt})
                    answer = res.json()["response"]
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error("Failed to connect to backend server. Make sure api.py is running.")

# =========================================================
# NORMAL MODE UI (REQUIRES LOGIN)
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
                res = requests.post(f"{API_URL}/login", json={"username": u_login, "password": p_login})
                if res.status_code == 200:
                    st.session_state.username = u_login
                    hist = requests.get(f"{API_URL}/history/{u_login}").json()
                    st.session_state.messages = hist
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
                    res = requests.post(f"{API_URL}/signup", json={"username": u_sign, "password": p_sign, "email": e_sign, "mobile": m_sign})
                    if res.status_code == 200:
                        st.success("Signup successful! Please login in the Login tab.")
                    else:
                        # Give suggestion if username exists
                        st.error(res.json().get("detail", "Signup failed."))
    
    else:
        # Display chat history for logged in user
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): 
                st.markdown(msg["content"])
            
        prompt = st.chat_input("Ask a health question...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): 
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                try:
                    # Normal mode answers line by line using streaming
                    response = requests.post(f"{API_URL}/chat/normal", json={"message": prompt, "username": st.session_state.username}, stream=True)
                    
                    def stream_generator():
                        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                            if chunk: 
                                yield chunk

                    # write_stream gives the typewriter effect line-by-line
                    answer = st.write_stream(stream_generator())
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                except Exception as e:
                    st.error("Error communicating with backend server. Make sure api.py is running.")
