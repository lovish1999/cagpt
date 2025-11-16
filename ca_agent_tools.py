# ca_agent_tools.py
import os, json, uuid, argparse, textwrap, time
from typing import List, Dict, Optional
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import faiss
import numpy as np

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# ---------- Config ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
INDEX_FILE = "kb_index.faiss"
META_FILE = "kb_meta.json"
LAWS_FILE = "laws.json"   # small json of law sections you curate (see format below)
MEMORY_WINDOW = 6

if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in .env")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Load FAISS & Metadata ----------
if os.path.exists(INDEX_FILE) and os.path.exists(META_FILE):
    faiss_index = faiss.read_index(INDEX_FILE)
    with open(META_FILE, "r", encoding="utf-8") as f:
        kb_meta = json.load(f)
    # We assume index vectors were normalized at indexing time
    print("Loaded FAISS index and metadata.")
else:
    faiss_index = None
    kb_meta = []
    print("Index or metadata not found. Run build_kb_index.py first.")

# ---------- Load laws DB ----------
if os.path.exists(LAWS_FILE):
    with open(LAWS_FILE, "r", encoding="utf-8") as f:
        LAWS_DB = json.load(f)
    print("Loaded laws DB.")
else:
    LAWS_DB = {}
    print(f"Warning: {LAWS_FILE} not found. Create one for laws lookup.")

# ---------- In-memory session memory ----------
SESSION_MEMORY: Dict[str, List[Dict]] = {}

# ---------- Helpers: semantic search ----------
def semantic_search(query: str, top_k: int = 3):
    """Return top_k metadata chunks for the query (uses normalized vectors)."""
    if faiss_index is None:
        return []
    # Use OpenAI embeddings for high-quality semantic search
    resp = openai_client.embeddings.create(model=EMBED_MODEL, input=[query])
    q_vec = np.array(resp.data[0].embedding).astype("float32")
    faiss.normalize_L2(q_vec.reshape(1, -1))
    D, I = faiss_index.search(q_vec.reshape(1, -1), top_k)
    hits = []
    for idx in I[0]:
        if idx < 0 or idx >= len(kb_meta):
            continue
        hits.append(kb_meta[idx])
    return hits

# ---------- Tool: laws_lookup ----------
def laws_lookup(section: str):
    """Return exact law text from LAWS_DB if found."""
    s = section.strip()
    # Do simple normalization lookups
    for key in LAWS_DB:
        if key.lower() == s.lower():
            return {"found": True, "section": key, "text": LAWS_DB[key]}
    # fuzzy fallback: substring match
    for key in LAWS_DB:
        if s.lower() in key.lower():
            return {"found": True, "section": key, "text": LAWS_DB[key]}
    return {"found": False, "section": section, "text": "Section not found in local DB."}

# ---------- Prompt system ----------
SYSTEM_PROMPT = textwrap.dedent("""
You are CA-GPT, a helpful Chartered Accountant assistant for Indian accounting, GST, income tax, and company law.
- Answer concisely and accurately. If unsure, say you are unsure and ask clarifying questions.
- Do NOT hallucinate law text. If exact law text is needed, call the 'laws_lookup' tool.
- If local KB passages are provided, use them and cite filenames.
- For final answers that reference law sections, include a short 'Sources:' list.
""").strip()

# ---------- Orchestration: supporting function-call style interaction ----------
def build_base_messages(session_id: str, question: str, include_kb: bool = True):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # short-term memory
    mem = SESSION_MEMORY.get(session_id, [])
    if mem:
        tail = mem[-MEMORY_WINDOW:]
        messages.extend(tail)
    # semantic retrieval
    sources = []
    if include_kb and faiss_index is not None:
        hits = semantic_search(question, top_k=4)
        for h in hits:
            # inject as system/context messages (or tool return style)
            messages.append({"role": "system", "content": f"KB_FILE: {h['file']}\n{h['text'][:1200]}"})
            sources.append(h['file'])
    # user message
    messages.append({"role": "user", "content": question})
    return messages, sources

# ---------- Chat + tool call loop ----------
def call_agent(session_id: str, question: str, include_kb: bool = True, max_rounds: int = 3):
    """
    This function demonstrates a simple tool-calling loop:
    1. Call model with 'functions' capability described (we simulate function definitions).
    2. If model returns a function_call (function name + JSON args), we execute the tool (laws_lookup)
       and send the tool output back to the model for finalization.
    3. Otherwise, return the model answer.
    """
    messages, kb_sources = build_base_messages(session_id, question, include_kb=include_kb)

    # Define the function schema for the model (OpenAI function-calling)
    functions = [
        {
            "name": "laws_lookup",
            "description": "Look up exact text of a law section from local laws DB (use for exact quotes).",
            "parameters": {
                "type": "object",
                "properties": {"section": {"type": "string", "description": "Section identifier, e.g. '17(5) CGST' or 'Section 115BA'"}},
                "required": ["section"]
            }
        }
    ]

    # Step 1: ask model (it may choose to call the function)
    resp = openai_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        tools=[{"type": "function", "function": f} for f in functions],
        tool_choice="auto",   # let the model decide
        temperature=0.0,
        max_tokens=500
    )
    choice = resp.choices[0].message

    # If model wants to call a function:
    if choice.tool_calls:
        tool_call = choice.tool_calls[0]
        func_name = tool_call.function.name
        raw_args = tool_call.function.arguments or "{}"
        try:
            args = json.loads(raw_args)
        except Exception:
            args = {"section": raw_args}

        # Execute the tool
        if func_name == "laws_lookup":
            section = args.get("section", "")
            tool_result = laws_lookup(section)
        else:
            tool_result = {"error": f"Unknown tool {func_name}"}

        # Append model's function call and the tool result to the messages
        messages.append({"role": "assistant", "content": choice.content or "", "tool_calls": [{"id": tool_call.id, "type": "function", "function": {"name": func_name, "arguments": raw_args}}]})
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(tool_result)
        })

        # Ask model to finalize answer using the tool output
        followup = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=700
        )
        final = followup.choices[0].message.content
        # append to session memory
        SESSION_MEMORY.setdefault(session_id, []).append({"role": "user", "content": question})
        SESSION_MEMORY.setdefault(session_id, []).append({"role": "assistant", "content": final})
        return {"answer": final, "kb_sources": kb_sources, "tool_used": func_name, "tool_result": tool_result}
    else:
        # model answered directly (no tool)
        final = choice.content or ""
        SESSION_MEMORY.setdefault(session_id, []).append({"role": "user", "content": question})
        SESSION_MEMORY.setdefault(session_id, []).append({"role": "assistant", "content": final})
        return {"answer": final, "kb_sources": kb_sources, "tool_used": None, "tool_result": None}

# ---------- FastAPI endpoint ----------
app = FastAPI(title="CA-GPT Agent with FAISS + laws_lookup")

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Root route - serve the web interface
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

class AskRequest(BaseModel):
    session_id: str
    question: str
    use_kb: bool = True

class AskResponse(BaseModel):
    answer: str
    kb_sources: List[str]
    tool_used: Optional[str] = None
    tool_result: Optional[dict] = None

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    out = call_agent(req.session_id, req.question, include_kb=req.use_kb)
    return AskResponse(answer=out["answer"], kb_sources=out["kb_sources"], tool_used=out["tool_used"], tool_result=out["tool_result"])

# ---------- CLI for testing ----------
def cli():
    print("CA-GPT Agent CLI (type 'exit' to quit)")
    sid = "cli-session"
    while True:
        q = input("\nYou: ").strip()
        if not q or q.lower() in ("exit", "quit"):
            break
        print("...thinking...")
        res = call_agent(sid, q, include_kb=True)
        print("\nCA-GPT:", res["answer"])
        if res["kb_sources"]:
            print("\nKB Sources:", ", ".join(res["kb_sources"]))
        if res["tool_used"]:
            print("\nTool used:", res["tool_used"])
            print("Tool result summary:", (res["tool_result"].get("text")[:300] if res["tool_result"] else ""))
        # small delay to make CLI readable
        time.sleep(0.2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.cli:
        cli()
    else:
        print(f"Starting FastAPI on port {args.port} ...")
        uvicorn.run("ca_agent_tools:app", host="0.0.0.0", port=args.port, reload=True)