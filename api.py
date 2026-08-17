"""
Backend API for Ai Powerd Initial health Care
FastAPI + LangChain + Groq + SQLite
"""

import os
import sqlite3
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DB_PATH = "health_chat.db"
MODEL = "llama-3.3-70b-versatile"

app = FastAPI(title="Ai Powerd Initial health Care API")

# =========================================================
# DATABASE CONNECTION & INITIALIZATION
# =========================================================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    # Create Users table for authentication
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

# =========================================================
# MODELS
# =========================================================

class SignupRequest(BaseModel):
    username: str
    password: str
    email: str
    mobile: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    username: Optional[str] = None

# =========================================================
# ENDPOINTS
# =========================================================

@app.on_event("startup")
def startup():
    init_db()

@app.post("/signup")
def signup(req: SignupRequest):
    conn = get_connection()
    # Check if username already exists
    user = conn.execute("SELECT id FROM users WHERE username = ?", (req.username,)).fetchone()
    if user:
        conn.close()
        # Give suggestion to change username if it exists
        raise HTTPException(status_code=400, detail="Username already exists. Suggestion: Try adding a number or changing your username.")
    
    # Store user data including email and mobile
    conn.execute("INSERT INTO users (username, password, email, mobile) VALUES (?, ?, ?, ?)", 
                 (req.username, req.password, req.email, req.mobile))
    conn.commit()
    conn.close()
    return {"message": "Signup successful"}

@app.post("/login")
def login(req: LoginRequest):
    conn = get_connection()
    # Basic password check for the sake of example
    user = conn.execute("SELECT id FROM users WHERE username = ? AND password = ?", 
                        (req.username, req.password)).fetchone()
    conn.close()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"message": "Login successful"}


def save_message(username, role, content):
    if not username:
        return
    conn = get_connection()
    conn.execute("INSERT INTO conversation_memory (username, role, content) VALUES (?, ?, ?)",
                 (username, role, content))
    conn.commit()
    conn.close()

def load_history(username):
    if not username:
        return []
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

@app.get("/history/{username}")
def get_history(username: str):
    conn = get_connection()
    rows = conn.execute("SELECT role, content FROM conversation_memory WHERE username = ? ORDER BY id", (username,)).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in rows]

# =========================================================
# CHAT ENDPOINTS (STREAMING & NON-STREAMING)
# =========================================================

def create_chain(system_prompt: str, streaming: bool = False):
    llm = ChatGroq(api_key=GROQ_API_KEY, model=MODEL, temperature=0.7, max_retries=3, streaming=streaming)
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]) | llm | StrOutputParser()

@app.post("/chat/emergency")
def chat_emergency(req: ChatRequest):
    # Emergency mode: Give whole answer together (no streaming), no username needed
    prompt = "In India You are an Emergency First Aid AI. Provide clear, immediate, actionable steps. ALWAYS remind the user to call 911 or local emergency services."
    chain = create_chain(prompt, streaming=False)
    reply = chain.invoke({"input": req.message, "history": []})
    return {"response": reply}

@app.post("/chat/normal")
async def chat_normal(req: ChatRequest):
    # Normal mode: Answer give line by line (Streaming)
    prompt = "In India You are a helpful Medical and Health Assistant. Provide accurate general health information. Remind users to consult a doctor for diagnosis."
    
    async def generate():
        chain = create_chain(prompt, streaming=True)
        history = load_history(req.username)
        save_message(req.username, "user", req.message)
        
        full_reply = ""
        # Async stream from LangChain
        async for chunk in chain.astream({"input": req.message, "history": history}):
            full_reply += chunk
            yield chunk
            
        save_message(req.username, "assistant", full_reply)

    return StreamingResponse(generate(), media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
