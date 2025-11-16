# build_kb_index.py
import os, glob, json
import numpy as np
import faiss
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
KB_FOLDER = "kb"
INDEX_FILE = "kb_index.faiss"
META_FILE = "kb_meta.json"
CHUNK_SIZE = 800  # chars per chunk, tune if desired

if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in .env")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

def chunk_text(text, size=CHUNK_SIZE):
    return [text[i:i+size] for i in range(0, len(text), size)]

def embed_texts(texts):
    """Generate embeddings using OpenAI API"""
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [r.embedding for r in resp.data]

def main():
    chunks = []
    meta = []
    for path in glob.glob(os.path.join(KB_FOLDER, "*.md")):
        name = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as fh:
            txt = fh.read()
        parts = chunk_text(txt)
        for p in parts:
            chunks.append(p)
            meta.append({"file": name, "text": p})
    print(f"Total chunks: {len(chunks)}")
    if not chunks:
        print("No files found in kb/*.md — create some first.")
        return
    embeddings = embed_texts(chunks)
    vecs = np.array(embeddings).astype("float32")
    dim = vecs.shape[1]
    # use IndexFlatIP with normalized vectors for cosine similarity
    faiss.normalize_L2(vecs)
    index = faiss.IndexFlatIP(dim)
    index.add(vecs)
    faiss.write_index(index, INDEX_FILE)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Written {INDEX_FILE} and {META_FILE}")

if __name__ == "__main__":
    main()