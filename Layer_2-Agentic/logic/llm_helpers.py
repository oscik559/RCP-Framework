# agentic_reasoning/logic/llm_helpers.py
"""
LLM integration utilities for the agentic reasoning system.

Provides standardized interfaces for Ollama model management with different
capability tiers (basic, reasoning, multimodal). Handles model configuration,
temperature settings, and provides factory methods for consistent LLM usage
across all workflow nodes.

Model Tiers:
- Basic: Fast models for simple tasks (llama3.2)
- Reasoning: Advanced models for complex analysis (phi4) 
- Multimodal: Models with image/document processing capabilities
"""

import logging
import time
from typing import Any, List, Dict

from config.config_loader import CONFIG

logger = logging.getLogger("LLM_HELPER")
# Note: RetrievalQA and Chroma imports for LangChain 1.x
# Optional imports - will fail at runtime if functions using them are called
RetrievalQA = None
Chroma = None
try:
    from langchain_classic.chains import RetrievalQA  # type: ignore
except ImportError:
    pass  # Will fail at runtime if RAG features are used

try:
    from langchain_chroma import Chroma  # type: ignore
except ImportError:
    pass  # Will fail at runtime if vector search is used

from langchain_core.tools import Tool  # type: ignore
from langchain_ollama import ChatOllama, OllamaEmbeddings  # type: ignore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings  # type: ignore


def get_ollama_model(model_name: str, temperature: float = 0.0, timeout: float = 60.0):
    """
    Create an Ollama chat model instance with specified parameters.
    
    Factory method for creating configured Ollama models with consistent
    settings. Used by other helper functions and workflow nodes.

    Args:
        model_name (str): Name of the Ollama model to use (e.g., "llama3.2:latest")
        temperature (float): Temperature setting for response randomness (0.0-1.0)
                           Lower values = more deterministic, higher = more creative
        timeout (float): Request timeout in seconds (default: 60.0)

    Returns:
        ChatOllama: Configured Ollama chat model instance ready for use
    """
    logger.info(f"Using Ollama model: {model_name} (timeout={timeout}s)")
    return ChatOllama(
        model=model_name, 
        temperature=temperature,
        timeout=timeout,
        num_ctx=4096,  # Limit context window to prevent memory issues
    )


def invoke_llm_with_retry(
    llm: ChatOllama, 
    messages: List[Dict[str, str]], 
    max_retries: int = 3,
    base_delay: float = 2.0
) -> Any:
    """
    Invoke LLM with exponential backoff retry logic for resilience.
    
    Handles transient Ollama failures by retrying with increasing delays.
    Logs all attempts and failures for debugging.
    
    Args:
        llm: Configured ChatOllama instance
        messages: List of message dicts with 'role' and 'content' keys
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 2.0)
        
    Returns:
        LLM response object
        
    Raises:
        Exception: If all retry attempts fail, raises the last exception
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"LLM invocation attempt {attempt + 1}/{max_retries}")
            response = llm.invoke(messages)
            logger.info(f"✅ LLM responded successfully on attempt {attempt + 1}")
            return response
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ LLM attempt {attempt + 1} failed: {error_msg}")
            
            # Check if it's a terminal error (don't retry)
            if "not found" in error_msg.lower() or "invalid" in error_msg.lower():
                logger.error("Terminal error detected, not retrying")
                raise
            
            # If not last attempt, wait with exponential backoff
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"⏳ Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logger.error(f"💥 All {max_retries} attempts failed")
                raise


def get_basic_llm():
    """
    Get the basic LLM configured for general purpose tasks.
    
    Returns the fast, lightweight model configured for:
    - Goal definition and parsing
    - Simple strategy selection
    - Basic text processing tasks

    Returns:
        ChatOllama: Basic LLM instance from configuration settings
    """
    cfg = CONFIG["llms"]["basic"]
    logger.info(f"Using basic LLM: {cfg['model']}")
    return ChatOllama(model=cfg["model"], temperature=cfg["temperature"])


def get_reasoning_llm():
    """
    Get the reasoning LLM configured for complex analytical tasks.

    Returns:
        ChatOllama: Reasoning LLM instance optimized for logical reasoning
    """
    cfg = CONFIG["llms"]["reasoning"]
    logger.info(f"Using reasoning LLM: {cfg['model']}")
    return ChatOllama(model=cfg["model"], temperature=cfg["temperature"])


def get_multimodal_llm():
    """
    Get the multimodal LLM configured for image and text processing.

    Returns:
        ChatOllama: Multimodal LLM instance capable of processing images and text
    """
    cfg = CONFIG["llms"]["multimodal"]
    logger.info(f"Using multimodal LLM: {cfg['model']}")
    return ChatOllama(model=cfg["model"], temperature=cfg["temperature"])


def get_embedding_model():
    """
    Get the embedding model configured for vector operations.

    Returns:
        OllamaEmbeddings: Embedding model instance for creating document embeddings
    """
    model_name = "nomic-embed-text:latest"
    logger.info(f"Using embedding model: {model_name}")
    return OllamaEmbeddings(model=model_name)


def get_retrieval_qa(llm, vectorstore):
    """
    Create a RetrievalQA chain using the provided LLM and vectorstore.

    Args:
        llm: Language model instance for generating answers
        vectorstore: Vector store containing embedded documents for retrieval

    Returns:
        RetrievalQA: Configured retrieval-augmented generation chain
    """
    logger.info("Creating RetrievalQA chain")
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(),
        return_source_documents=True,
    )


# ── Sanity check ────────────────────────────
if __name__ == "__main__":
    from pprint import pprint

    print("🔍 Running LLM sanity checks...")

    # --- BASIC LLM ---
    print("\n--- BASIC LLM ---")
    try:
        basic = get_basic_llm()
        print("✅ Basic LLM loaded:", basic.model)

        try:
            response = basic.invoke("Say something creatively in one sentence.")
            print("🧠 Basic LLM responded:", response.content)
        except Exception as e:
            print("❌ Failed to query basic LLM:", e)

    except Exception as e:
        print("❌ Failed to load basic LLM:", e)

    # --- REASONING LLM ---
    print("\n--- REASONING LLM ---")
    try:
        reasoning = get_reasoning_llm()
        print("✅ Reasoning LLM loaded:", reasoning.model)

        try:
            response = reasoning.invoke("Say something creatively in one sentence.")
            print("🧠 Reasoning LLM responded:", response.content)
        except Exception as e:
            print("❌ Failed to query reasoning LLM:", e)

    except Exception as e:
        print("❌ Failed to load reasoning LLM:", e)

    # --- MULTIMODAL LLM ---
    print("\n--- MULTIMODAL LLM ---")
    try:
        multi = get_multimodal_llm()
        print("✅ Multimodal LLM loaded:", multi.model)

        try:
            response = multi.invoke("Say something creatively in one sentence.")
            print("🧠 Multimodal LLM responded:", response.content)
        except Exception as e:
            print("❌ Failed to query multimodal LLM:", e)

    except Exception as e:
        print("❌ Failed to load multimodal LLM:", e)

    # --- EMBEDDING MODEL ---
    print("\n--- EMBEDDING MODEL ---")
    try:
        embeddings = get_embedding_model()
        print("✅ Embedding model loaded:", embeddings.model)

        try:
            # Test embedding generation
            test_text = "This is a test document for embedding."
            test_embedding = embeddings.embed_query(test_text)
            print(f"🧮 Test embedding generated: {len(test_embedding)} dimensions")
        except Exception as e:
            print("❌ Failed to generate test embedding:", e)

    except Exception as e:
        print("❌ Embedding model failed:", str(e)[:100])

    print("\n🎉 LLM sanity checks complete!")


