# backend/main.py
import os, json, csv
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np
import faiss
import openai

# ---------------------------
# Setup FastAPI
# ---------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production, replace with your website domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Root endpoint
# ---------------------------
@app.get("/")
def read_root():
    return {"status": "running"}

# ---------------------------
# Load environment & OpenAI
# ---------------------------
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in .env")
openai.api_key = OPENAI_API_KEY

# ---------------------------
# Paths
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "faiss_index.index"
META_PATH = BASE_DIR / "metadata.json"
LEADS_CSV = BASE_DIR / "leads.csv"

# ---------------------------
# Load FAISS index & metadata
# ---------------------------
if not INDEX_PATH.exists() or not META_PATH.exists():
    raise RuntimeError("Index or metadata not found. Run ingest.py first.")

index = faiss.read_index(str(INDEX_PATH))
with open(META_PATH, "r", encoding="utf-8") as f:
    METADATA = json.load(f)

DIM = index.d

# ---------------------------
# Models
# ---------------------------
class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str

class Lead(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    note: str | None = None

# ---------------------------
# Embedding Helper
# ---------------------------
def embed_text(text: str) -> np.ndarray:
    resp = openai.Embedding.create(model="text-embedding-3-small", input=text)
    vec = np.array(resp["data"][0]["embedding"], dtype=np.float32)
    faiss.normalize_L2(vec.reshape(1, -1))
    return vec

# ---------------------------
# Chat Endpoint
# ---------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    q = req.message.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty message")

    # embed & search
    vec = embed_text(q)
    D, I = index.search(vec.reshape(1, -1), k=3)  # top 3 matches
    idxs = I[0].tolist()

    contexts, sources = [], []
    for idx in idxs:
        m = METADATA[idx]
        contexts.append(f"FAQ #{m['id']} Q:{m['question']}\nA:{m['answer']}")
        sources.append(m["id"])
    context_text = "\n\n".join(contexts)

    system_prompt = (
        "You are Mitesh Khatri's support assistant. ALWAYS answer using ONLY the provided Context. "
        "If the user's question cannot be answered from the Context, say you don't know and suggest capturing their contact details for follow-up. "
        "Be concise and professional. Use Hindi if the user used Hindi."
    )

    user_prompt = f"CONTEXT:\n{context_text}\n\nUser question: {q}\n\nAnswer strictly based on the context."

    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=400,
    )

    answer = resp["choices"][0]["message"]["content"].strip()

    # detect if lead capture is needed
    lead_required = any(
        kw in answer.lower()
        for kw in ["i don't", "don't have", "i do not", "not sure", "can't find"]
    )

    return {"reply": answer, "sources": sources, "lead_required": lead_required}

# ---------------------------
# Lead Endpoint
# ---------------------------
@app.post("/lead")
async def save_lead(lead: Lead):
    first_write = not LEADS_CSV.exists()
    with open(LEADS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if first_write:
            writer.writerow(["name", "email", "phone", "note"])
        writer.writerow([lead.name, lead.email or "", lead.phone or "", lead.note or ""])
    return {"status": "ok"}

# ---------------------------
# Run manually
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
