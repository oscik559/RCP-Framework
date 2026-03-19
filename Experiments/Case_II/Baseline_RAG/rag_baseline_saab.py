"""
B1: Naive RAG baseline for Saab Case II evaluation.

Chunks the text content of all extracted_tables, embeds them with
qwen3-embedding:8b (Ollama), retrieves top-5 chunks for each query,
and generates with llama3.2:latest.
"""

import json
import os
import sqlite3
import time
from pathlib import Path

import requests

# Set SAAB_DB_PATH environment variable to override the default location.
SAAB_DB = Path(os.environ.get("SAAB_DB_PATH", "database/saab_harvested.db"))
OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "qwen3-embedding:latest"
LLM_MODEL = "llama3.2:latest"
TOP_K = 5


# ── Ollama helpers ─────────────────────────────────────────────────────────────

def embed(text: str) -> list[float]:
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=120,
    )
    resp.raise_for_status()
    result = resp.json()
    # /api/embed returns {"embeddings": [[...]]} for single input
    embs = result.get("embeddings") or result.get("embedding")
    if isinstance(embs, list) and isinstance(embs[0], list):
        return embs[0]
    return embs


def generate(prompt: str, temperature: float = 0.0) -> str:
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": LLM_MODEL,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ── Build corpus ───────────────────────────────────────────────────────────────

def load_chunks() -> list[dict]:
    """Convert each row in extracted_tables to a text chunk."""
    con = sqlite3.connect(SAAB_DB)
    cur = con.cursor()
    cur.execute(
        "SELECT filename, heading_name, table_name, tablecontent FROM extracted_tables"
    )
    chunks = []
    for filename, heading, table_name, content_json in cur.fetchall():
        try:
            rows = json.loads(content_json)
            # Flatten all cells into a single text string
            text_parts = [f"Document: {filename}"]
            if heading:
                text_parts.append(f"Section: {heading}")
            text_parts.append(f"Table: {table_name}")
            for row in rows:
                text_parts.append(" | ".join(str(c) for c in row))
            text = "\n".join(text_parts)
            chunks.append(
                {
                    "source": f"{filename}/{table_name}",
                    "text": text,
                    "embedding": None,
                }
            )
        except Exception:
            pass
    con.close()
    return chunks


def build_index(chunks: list[dict]) -> list[dict]:
    print(f"[B1] Embedding {len(chunks)} chunks ...")
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = embed(chunk["text"][:2000])  # Truncate very long
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(chunks)}")
    return chunks


def retrieve(query: str, chunks: list[dict], top_k: int = TOP_K) -> list[dict]:
    q_emb = embed(query)
    scored = [(cosine_sim(q_emb, c["embedding"]), c) for c in chunks]
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


# ── Answer generation ──────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """\
You are a technical documentation assistant for Saab aerospace connector and cable products.
Answer the question using ONLY the information in the provided context.
If the answer is not in the context, say "Not found in documentation."
Be precise and include exact values with units.

Context:
{context}

Question: {question}

Answer:"""


def answer_query(query: str, chunks: list[dict]) -> tuple[str, float]:
    t0 = time.time()
    top = retrieve(query, chunks)
    context = "\n\n---\n\n".join(c["text"][:800] for c in top)
    prompt = PROMPT_TEMPLATE.format(context=context, question=query)
    answer = generate(prompt)
    return answer, time.time() - t0


# ── Public entry point ─────────────────────────────────────────────────────────

_CACHED_CHUNKS: list[dict] | None = None


def run_b1(query: str) -> tuple[str, float]:
    """Return (answer, latency_s). Builds/caches the embedding index on first call."""
    global _CACHED_CHUNKS
    if _CACHED_CHUNKS is None:
        chunks = load_chunks()
        _CACHED_CHUNKS = build_index(chunks)
    return answer_query(query, _CACHED_CHUNKS)


if __name__ == "__main__":
    ans, lat = run_b1("What is the jacket diameter of TFR4631015/030?")
    print(f"Answer: {ans}")
    print(f"Latency: {lat:.2f}s")
