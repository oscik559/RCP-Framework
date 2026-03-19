#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG Baseline Pipeline
=====================
Standard Retrieval-Augmented Generation baseline for evaluation.

Pipeline:
  1. Load all product data from harvested.db
  2. Chunk text content with configurable size/overlap
  3. Embed chunks using embeddinggemma:latest (Ollama)
  4. Store in in-memory ChromaDB
  5. For each query: retrieve top-k → generate with llama3.2:latest

This serves as the "RAG Baseline" in the paper's evaluation (Section 5).
"""

import json
import logging
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path setup – allow running from project root or from this directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("RAG_BASELINE")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_CONFIG = {
    # LLM
    "llm_model": "llama3.2:latest",
    "llm_temperature": 0.0,
    # Embeddings
    "embedding_model": "qwen3-embedding:latest",
    # Chunking
    "chunk_size": 800,
    "chunk_overlap": 100,
    # Retrieval
    "top_k": 5,
    # Database
    "harvested_db": str(PROJECT_ROOT / "database" / "harvested.db"),
}


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_documents_from_db(db_path: str) -> List[Document]:
    """
    Load all product data from harvested.db and convert to LangChain Documents.
    
    Sources:
      - product_families: name, applications, construction_details
      - products: product_code, specifications
      - product_knowledge: content (descriptions, assembly, standards, etc.)
      - categories: name, description
    """
    logger.info(f"Loading documents from {db_path}")
    documents: List[Document] = []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # ── Product Families ──────────────────────────────────────────
        cursor = conn.execute("""
            SELECT pf.id, pf.family_code, pf.name, pf.subtitle, pf.description,
                   pf.construction_details, pf.applications, pf.page_number,
                   c.name as category_name, c.chapter
            FROM product_families pf
            LEFT JOIN categories c ON pf.category_id = c.id
        """)
        
        for row in cursor:
            text_parts = []
            text_parts.append(f"Product Family: {row['name']}")
            text_parts.append(f"Family Code: {row['family_code']}")
            
            if row["category_name"]:
                text_parts.append(f"Category: {row['category_name']}")
            if row["subtitle"]:
                text_parts.append(f"Subtitle: {row['subtitle']}")
            if row["description"]:
                text_parts.append(f"Description: {row['description']}")
            if row["applications"]:
                text_parts.append(f"Applications: {row['applications']}")
            if row["construction_details"]:
                try:
                    cd = json.loads(row["construction_details"])
                    for k, v in cd.items():
                        if isinstance(v, dict):
                            text_parts.append(f"{k}: {json.dumps(v)}")
                        else:
                            text_parts.append(f"{k}: {v}")
                except (json.JSONDecodeError, TypeError):
                    text_parts.append(f"Construction: {row['construction_details']}")
            
            metadata = {
                "source": "product_families",
                "family_id": row["id"],
                "family_code": row["family_code"],
                "family_name": row["name"],
                "category": row["category_name"] or "",
                "page_number": row["page_number"] or 0,
            }
            
            documents.append(Document(
                page_content="\n".join(text_parts),
                metadata=metadata,
            ))
        
        family_count = len(documents)
        logger.info(f"  Loaded {family_count} product families")
        
        # ── Products (individual SKUs) ────────────────────────────────
        cursor = conn.execute("""
            SELECT p.id, p.product_code, p.variant_suffix,
                   p.configuration_type, p.specifications, p.page_number,
                   pf.family_code, pf.name as family_name,
                   c.name as category_name
            FROM products p
            LEFT JOIN product_families pf ON p.family_id = pf.id
            LEFT JOIN categories c ON pf.category_id = c.id
        """)
        
        product_count = 0
        for row in cursor:
            text_parts = []
            text_parts.append(f"Product Code: {row['product_code']}")
            text_parts.append(f"Family: {row['family_name']} ({row['family_code']})")
            
            if row["category_name"]:
                text_parts.append(f"Category: {row['category_name']}")
            if row["configuration_type"]:
                text_parts.append(f"Configuration: {row['configuration_type']}")
            
            if row["specifications"]:
                try:
                    specs = json.loads(row["specifications"])
                    for k, v in specs.items():
                        text_parts.append(f"{k}: {v}")
                except (json.JSONDecodeError, TypeError):
                    text_parts.append(f"Specifications: {row['specifications']}")
            
            metadata = {
                "source": "products",
                "product_code": row["product_code"],
                "family_code": row["family_code"] or "",
                "family_name": row["family_name"] or "",
                "category": row["category_name"] or "",
                "page_number": row["page_number"] or 0,
            }
            
            documents.append(Document(
                page_content="\n".join(text_parts),
                metadata=metadata,
            ))
            product_count += 1
        
        logger.info(f"  Loaded {product_count} individual products")
        
        # ── Product Knowledge ─────────────────────────────────────────
        cursor = conn.execute("""
            SELECT id, pdf_name, page_number, category, knowledge_type,
                   section_title, content
            FROM product_knowledge
        """)
        
        knowledge_count = 0
        for row in cursor:
            text_parts = []
            if row["section_title"]:
                text_parts.append(f"Section: {row['section_title']}")
            if row["category"]:
                text_parts.append(f"Category: {row['category']}")
            if row["knowledge_type"]:
                text_parts.append(f"Type: {row['knowledge_type']}")
            text_parts.append(row["content"])
            
            metadata = {
                "source": "product_knowledge",
                "knowledge_type": row["knowledge_type"] or "",
                "category": row["category"] or "",
                "pdf_name": row["pdf_name"] or "",
                "page_number": row["page_number"] or 0,
            }
            
            documents.append(Document(
                page_content="\n".join(text_parts),
                metadata=metadata,
            ))
            knowledge_count += 1
        
        logger.info(f"  Loaded {knowledge_count} knowledge entries")
        
    finally:
        conn.close()
    
    logger.info(f"  Total documents loaded: {len(documents)}")
    return documents


# ═══════════════════════════════════════════════════════════════════════════
# RAG PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

class RAGBaseline:
    """
    Standard RAG pipeline: chunk → embed → retrieve → generate.
    
    No structured validation, no relational state, no inter-step checks.
    This is the baseline comparison for the RCP framework.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}
        self.vectorstore: Optional[Chroma] = None
        self.llm: Optional[ChatOllama] = None
        self.embeddings: Optional[OllamaEmbeddings] = None
        self._total_tokens = 0
        
    def initialize(self) -> None:
        """Load data, chunk, embed, and prepare the vectorstore."""
        logger.info("=" * 60)
        logger.info("INITIALIZING RAG BASELINE")
        logger.info("=" * 60)
        
        # 1. Initialize models
        logger.info(f"LLM: {self.config['llm_model']}")
        logger.info(f"Embeddings: {self.config['embedding_model']}")
        
        self.llm = ChatOllama(
            model=self.config["llm_model"],
            temperature=self.config["llm_temperature"],
        )
        self.embeddings = OllamaEmbeddings(
            model=self.config["embedding_model"],
        )
        
        # 2. Load documents from harvested.db
        documents = load_documents_from_db(self.config["harvested_db"])
        
        if not documents:
            raise ValueError("No documents loaded from harvested.db")
        
        # 3. Chunk documents
        logger.info(
            f"Chunking with size={self.config['chunk_size']}, "
            f"overlap={self.config['chunk_overlap']}"
        )
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"],
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        chunks = splitter.split_documents(documents)
        logger.info(f"  Created {len(chunks)} chunks from {len(documents)} documents")
        
        # 4. Build vectorstore (in-memory ChromaDB)
        logger.info("Building in-memory ChromaDB vectorstore...")
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            collection_name="rag_baseline",
        )
        logger.info(f"  Vectorstore ready with {len(chunks)} vectors")
        logger.info("=" * 60)
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Run the standard RAG pipeline on a single question.
        
        Returns:
            Dict with keys: answer, sources, latency_s, token_estimate
        """
        if self.vectorstore is None or self.llm is None:
            raise RuntimeError("Pipeline not initialized. Call initialize() first.")
        
        start_time = time.perf_counter()
        
        # ── Retrieve ──────────────────────────────────────────────────
        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": self.config["top_k"]}
        )
        retrieved_docs = retriever.invoke(question)
        
        # ── Build context ─────────────────────────────────────────────
        context_parts = []
        sources = []
        for i, doc in enumerate(retrieved_docs, 1):
            context_parts.append(f"[Source {i}]\n{doc.page_content}")
            sources.append({
                "source": doc.metadata.get("source", ""),
                "product_code": doc.metadata.get("product_code", ""),
                "family_code": doc.metadata.get("family_code", ""),
                "family_name": doc.metadata.get("family_name", ""),
                "category": doc.metadata.get("category", ""),
                "page_number": doc.metadata.get("page_number", 0),
            })
        
        context = "\n\n".join(context_parts)
        
        # ── Generate ─────────────────────────────────────────────────
        prompt = (
            f"You are a helpful technical assistant for hydraulic engineering products. "
            f"Answer the question based ONLY on the provided context. "
            f"If the context does not contain the answer, say so clearly.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        prompt_tokens = len(prompt) // 4
        
        response = self.llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)
        
        response_tokens = len(answer) // 4
        total_tokens = prompt_tokens + response_tokens
        self._total_tokens += total_tokens
        
        elapsed = time.perf_counter() - start_time
        
        return {
            "answer": answer,
            "sources": sources,
            "retrieved_chunks": len(retrieved_docs),
            "latency_s": round(elapsed, 3),
            "token_estimate": total_tokens,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
        }
    
    @property
    def total_tokens(self) -> int:
        return self._total_tokens


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RAG BASELINE — Quick Smoke Test")
    print("=" * 60 + "\n")
    
    pipeline = RAGBaseline()
    pipeline.initialize()
    
    test_questions = [
        "Vilken gängstorlek har en 4201-16-16?",
        "What is the maximum temperature for hose 1071-00-16?",
        "Which products are approved for food use?",
    ]
    
    for q in test_questions:
        print(f"\nQ: {q}")
        result = pipeline.query(q)
        print(f"A: {result['answer'][:200]}...")
        print(f"   Latency: {result['latency_s']}s | Tokens: {result['token_estimate']}")
        print(f"   Sources: {len(result['sources'])} chunks retrieved")
        print("-" * 60)
    
    print(f"\nTotal tokens used: {pipeline.total_tokens}")
