# backend/ingest.py
import os
import json
import numpy as np
import faiss
import openai
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in .env or environment variables")
openai.api_key = OPENAI_API_KEY

BASE_DIR = Path(__file__).resolve().parent.parent
FAQS_PATH = BASE_DIR / "faqs" / "faqs.json"
META_PATH = Path(__file__).resolve().parent / "metadata.json"
INDEX_PATH = Path(__file__).resolve().parent / "faiss_index.index"

def load_faqs():
    with open(FAQS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_embedding(text):
    # Using OpenAI embedding endpoint
    resp = openai.Embedding.create(model="text-embedding-3-small", input=text)
    return np.array(resp["data"][0]["embedding"], dtype=np.float32)

def build_index(faqs):
    texts = []
    metas = []
    vectors = []
    for i, faq in enumerate(faqs):
        # Combine question + answer to give context
        text = faq.get("question","") + "\n\n" + faq.get("answer","")
        texts.append(text)
        metas.append({"id": i, "question": faq.get("question",""), "answer": faq.get("answer","")})
        vec = get_embedding(text)
        vectors.append(vec)

    vectors = np.vstack(vectors).astype('float32')
    # normalize for cosine similarity
    faiss.normalize_L2(vectors)

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product on normalized vectors = cosine similarity
    index.add(vectors)
    # save index and metadata
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(metas, f, ensure_ascii=False, indent=2)

    print(f"Saved index to {INDEX_PATH}, metadata to {META_PATH}")

if __name__ == "__main__":
    faqs = load_faqs()
    build_index(faqs)
