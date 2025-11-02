"""
Vector Database Integration for Agentic Reasoning System

Provides semantic search capabilities using nomic-embed-text embeddings for
enhanced keyword suggestion and table content similarity matching. Integrates 
with existing workflow to improve query understanding through vector similarity.

Architecture:
- Primary: ChromaDB for persistent vector storage  
- Fallback: FAISS for in-memory operations (if available)
- Embeddings: nomic-embed-text model for text-to-vector conversion
- Integration: Used by func_suggest_keywords() and func_table_search_on_document()

Key Features:
- Semantic similarity search across table content and field names
- Enhanced keyword suggestion based on document context embeddings
- Vector indexing of extracted PDF table data for improved retrieval
- Automatic fallback to traditional search when vector search unavailable

Performance Notes:
- ChromaDB provides persistent storage across sessions
- FAISS offers faster in-memory search but requires rebuild per session
- Vector operations enhance but don't replace traditional SQL-based search
"""

import json
import logging
import os
import sqlite3
import time
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from langchain_chroma import Chroma
from langchain_core.documents import Document

try:
    from langchain_community.vectorstores import FAISS

    # Test if FAISS actually works by trying to access it
    try:
        _ = FAISS.__name__  # This will trigger import error if faiss module is missing
        FAISS_AVAILABLE = True
    except Exception:
        FAISS_AVAILABLE = False
except (ImportError, ModuleNotFoundError):
    # Fallback to Chroma if FAISS is not available
    FAISS_AVAILABLE = False

from config.config_loader import CONFIG
from db.connection import get_output_connection
from logic.llm_helpers import get_embedding_model

logger = logging.getLogger("VECTOR_DB")


class VectorTableSearch:
    """Vector-based semantic search for table content"""

    def __init__(self, index_path: str = None):
        self.index_path = index_path or "data/vector_index"
        self.vector_store = None
        self.table_metadata = {}
        self.embeddings_available = False

        # Additional safety check - disable FAISS if index file doesn't exist
        global FAISS_AVAILABLE
        if FAISS_AVAILABLE and not os.path.exists(
            os.path.join(self.index_path, "index.faiss")
        ):
            logger.warning(
                "⚠️ FAISS index file not found, disabling FAISS for this session"
            )
            FAISS_AVAILABLE = False

        # Try to initialize embeddings with fallback
        try:
            self.embeddings = get_embedding_model()
            self.embeddings_available = True
            logger.info("✅ Vector embeddings initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️ Vector embeddings not available: {e}")
            self.embeddings = None
            self.embeddings_available = False

    def create_table_embeddings(self, force_rebuild: bool = False) -> bool:
        """
        Create vector embeddings for all table content in the database.

        Args:
            force_rebuild: Force recreation even if index exists

        Returns:
            Success status
        """
        # Check if embeddings are available
        if not self.embeddings_available:
            logger.warning(
                "❌ Vector embeddings not available - skipping vector index creation"
            )
            return False

        try:
            # Check if index already exists
            if not force_rebuild:
                try:
                    logger.info(f"🔍 FAISS_AVAILABLE check: {FAISS_AVAILABLE}")
                    # Only try FAISS if it's available and imported successfully
                    if FAISS_AVAILABLE:
                        logger.info("🔍 Attempting FAISS load...")
                        try:
                            # Double-check FAISS is actually usable
                            if "FAISS" in globals():
                                logger.info("🔍 FAISS found in globals, loading...")
                                # Additional safety check before loading
                                faiss_index_file = os.path.join(
                                    self.index_path, "index.faiss"
                                )
                                if not os.path.exists(faiss_index_file):
                                    logger.warning(
                                        f"⚠️ FAISS index file not found at {faiss_index_file}, skipping FAISS"
                                    )
                                    raise FileNotFoundError(
                                        f"FAISS index file not found: {faiss_index_file}"
                                    )

                                self.vector_store = FAISS.load_local(
                                    self.index_path,
                                    self.embeddings,
                                    allow_dangerous_deserialization=True,
                                )
                                logger.info("✅ Loaded existing FAISS vector index")
                                return True
                            else:
                                logger.warning("⚠️ FAISS not in globals, skipping")
                        except (
                            ImportError,
                            NameError,
                            AttributeError,
                        ) as faiss_import_e:
                            logger.warning(
                                f"⚠️ FAISS import/usage failed: {faiss_import_e}"
                            )
                            # Fall through to Chroma
                        except (
                            RuntimeError,
                            FileNotFoundError,
                            OSError,
                        ) as faiss_file_e:
                            logger.warning(
                                f"⚠️ FAISS index file not found or corrupted: {faiss_file_e}"
                            )
                            # Fall through to Chroma
                        except Exception as faiss_e:
                            logger.warning(
                                f"⚠️ FAISS load failed, trying Chroma: {faiss_e}"
                            )
                            # Fall through to Chroma
                    else:
                        logger.info("🔍 FAISS_AVAILABLE is False, skipping FAISS")

                    # Try Chroma regardless of FAISS availability
                    try:
                        self.vector_store = Chroma(
                            persist_directory=self.index_path,
                            embedding_function=self.embeddings,
                        )
                        logger.info("✅ Loaded existing Chroma vector index")
                        return True
                    except Exception as chroma_e:
                        logger.info(
                            f"No existing vector index found, creating new one: {chroma_e}"
                        )

                except Exception as load_e:
                    logger.info(
                        f"Vector index loading failed, creating new one: {load_e}"
                    )

            # Load table data from database
            with get_output_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, filename, table_name, tablecontent, heading_name
                    FROM extracted_tables
                    WHERE tablecontent IS NOT NULL
                """
                )

                rows = cursor.fetchall()

            if not rows:
                logger.warning("No table data found for vectorization")
                return False

            # Prepare documents for vectorization
            documents = []
            metadatas = []

            for row in rows:
                table_id, filename, table_name, content, heading = row

                # Create searchable text combining table name, heading, and content
                searchable_text = f"Table: {table_name or 'Unknown'}\n"
                searchable_text += f"Section: {heading or 'Unknown'}\n"
                searchable_text += f"Content: {content[:1000]}"  # Limit content length

                doc = Document(
                    page_content=searchable_text,
                    metadata={
                        "table_id": table_id,
                        "filename": filename,
                        "table_name": table_name,
                        "heading_name": heading,
                        "content_length": len(content),
                    },
                )

                documents.append(doc)
                metadatas.append(doc.metadata)

                # Store metadata for later retrieval
                self.table_metadata[table_id] = {
                    "filename": filename,
                    "table_name": table_name,
                    "heading_name": heading,
                    "full_content": content,
                }

            # Create vector store with robust fallback
            logger.info(
                f"Creating vector embeddings for {len(documents)} table records"
            )

            try:
                if FAISS_AVAILABLE:
                    try:
                        # Double-check FAISS is actually usable
                        if "FAISS" in globals():
                            self.vector_store = FAISS.from_documents(
                                documents, self.embeddings
                            )
                            # Save index
                            self.vector_store.save_local(self.index_path)
                            logger.info(
                                f"✅ FAISS vector index created and saved to {self.index_path}"
                            )
                            return True
                    except (ImportError, NameError, AttributeError) as faiss_import_e:
                        logger.warning(
                            f"⚠️ FAISS import/usage failed during creation: {faiss_import_e}"
                        )
                        # Fall through to Chroma
                    except (RuntimeError, FileNotFoundError, OSError) as faiss_file_e:
                        logger.warning(f"⚠️ FAISS file operation failed: {faiss_file_e}")
                        # Fall through to Chroma
                    except Exception as faiss_e:
                        logger.warning(
                            f"⚠️ FAISS creation failed, falling back to Chroma: {faiss_e}"
                        )
                        # Fall through to Chroma

                # Use Chroma as fallback
                try:
                    self.vector_store = Chroma.from_documents(
                        documents, self.embeddings, persist_directory=self.index_path
                    )
                    self.vector_store.persist()
                    logger.info(
                        f"✅ Chroma vector index created and saved to {self.index_path}"
                    )
                    return True
                except Exception as chroma_e:
                    logger.error(f"❌ Both FAISS and Chroma failed: {chroma_e}")
                    return False

            except Exception as e:
                logger.error(f"❌ Vector store creation completely failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Error creating table embeddings: {e}")
            return False

    def semantic_keyword_search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Perform semantic search to find relevant table content for keyword suggestions.

        Args:
            query: User query for semantic matching
            top_k: Number of top results to return

        Returns:
            List of relevant table records with similarity scores
        """
        # Check if embeddings are available
        if not self.embeddings_available:
            logger.warning(
                "❌ Vector embeddings not available - returning empty results"
            )
            return []

        if not self.vector_store:
            if not self.create_table_embeddings():
                logger.warning(
                    "❌ Failed to create vector embeddings - returning empty results"
                )
                return []

        try:
            # Perform semantic search
            results = self.vector_store.similarity_search_with_score(query, k=top_k)

            semantic_results = []
            for doc, score in results:
                table_id = doc.metadata.get("table_id")

                result = {
                    "similarity_score": float(
                        1 - score
                    ),  # Convert distance to similarity
                    "table_id": table_id,
                    "filename": doc.metadata.get("filename"),
                    "table_name": doc.metadata.get("table_name"),
                    "heading_name": doc.metadata.get("heading_name"),
                    "content_preview": doc.page_content[:200] + "...",
                    "full_content": self.table_metadata.get(table_id, {}).get(
                        "full_content", ""
                    ),
                }

                semantic_results.append(result)

            logger.info(
                f"✅ Semantic search found {len(semantic_results)} relevant tables"
            )
            return semantic_results

        except Exception as e:
            logger.error(f"❌ Error in semantic search: {e}")
            return []

    def extract_semantic_keywords(
        self, query: str, max_keywords: int = 10
    ) -> List[str]:
        """
        Extract relevant keywords from semantically similar table content.

        Args:
            query: User query for semantic matching
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of relevant keywords
        """
        # Check if embeddings are available
        if not self.embeddings_available:
            logger.warning(
                "❌ Vector embeddings not available - returning empty keyword list"
            )
            return []

        semantic_results = self.semantic_keyword_search(query, top_k=5)

        if not semantic_results:
            logger.warning(
                "❌ No semantic results found - returning empty keyword list"
            )
            return []

        # Extract keywords from similar table content
        keywords = set()

        for result in semantic_results:
            content = result.get("full_content", "")
            table_name = result.get("table_name", "")

            # Extract product codes (alphanumeric patterns)
            import re

            product_codes = re.findall(r"\b[A-Z][0-9]{6,}[A-Z0-9-]*\b", content)
            keywords.update(product_codes[:3])  # Take first 3 from each table

            # Extract technical terms (capitalized words)
            tech_terms = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", content)
            keywords.update([term for term in tech_terms if len(term) > 3][:2])

            # Add table name keywords
            if table_name and len(table_name) > 3:
                keywords.add(table_name)

        # Return top keywords sorted by potential relevance
        final_keywords = list(keywords)[:max_keywords]
        logger.info(f"Extracted {len(final_keywords)} semantic keywords")

        return final_keywords


class EnhancedKeywordSuggester:
    """Enhanced keyword suggestion using both LLM and vector similarity"""

    def __init__(self):
        try:
            self.vector_search = VectorTableSearch()
            self.vector_available = self.vector_search.embeddings_available
        except Exception as e:
            logger.warning(f"⚠️ Vector search initialization failed: {e}")
            self.vector_search = None
            self.vector_available = False

    def suggest_enhanced_keywords(
        self, query: str, max_keywords: int = 5
    ) -> Tuple[bool, Dict]:
        """
        Enhanced keyword suggestion combining LLM reasoning and semantic similarity.

        Args:
            query: User query
            max_keywords: Maximum keywords to suggest

        Returns:
            (success, result_dict) with enhanced keyword suggestions
        """
        try:
            # Step 1: Get semantic keywords from vector search (if available)
            semantic_keywords = []
            if self.vector_available and self.vector_search:
                try:
                    semantic_keywords = self.vector_search.extract_semantic_keywords(
                        query, max_keywords * 2
                    )
                    logger.info(
                        f"✅ Vector search provided {len(semantic_keywords)} semantic keywords"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ Vector search failed, falling back to LLM only: {e}"
                    )
                    semantic_keywords = []
            else:
                logger.info("ℹ️ Vector search not available, using LLM-only approach")

            # Step 2: Get LLM-based keywords (existing functionality)
            from logic.llm_helpers import get_basic_llm
            from config.prompt_loader import get_prompt_loader

            prompt_loader = get_prompt_loader()
            try:
                prompt_template = prompt_loader.get_prompt("keyword_suggestion")
                llm_prompt = prompt_template.format(
                    user_query=query,
                    semantic_context=(
                        ", ".join(semantic_keywords[:3])
                        if semantic_keywords
                        else "None"
                    ),
                )
            except Exception as prompt_e:
                logger.warning(f"⚠️ Prompt template issue, using fallback: {prompt_e}")
                llm_prompt = f"""Extract ONLY field/column names from the user question.
Focus on technical properties and components like: torque, shell size, contact gender, tools, locator, crimp tool, installing tool, etc.
Return lowercase, comma-separated field names or empty string.

Question: {query}
Semantic context: {", ".join(semantic_keywords[:3]) if semantic_keywords else "None"}
Extract field names:"""

            llm = get_basic_llm()
            llm_response = llm.invoke(llm_prompt)
            llm_keywords_raw = llm_response.content.strip()

            # Parse LLM keywords
            llm_keywords = [k.strip() for k in llm_keywords_raw.split(",") if k.strip()]

            # Step 3: Combine and prioritize keywords
            combined_keywords = []

            # Add semantic keywords (high priority for product-specific queries)
            for keyword in semantic_keywords[: max_keywords // 2]:
                if keyword not in combined_keywords:
                    combined_keywords.append(keyword)

            # Add LLM keywords (good for conceptual terms)
            for keyword in llm_keywords[: max_keywords // 2]:
                if keyword not in combined_keywords:
                    combined_keywords.append(keyword)

            # Ensure we have the requested number of keywords
            final_keywords = combined_keywords[:max_keywords]

            logger.info(f"Enhanced keyword suggestion: {len(final_keywords)} keywords")

            return (
                True,
                {
                    "Keyword Output": ", ".join(final_keywords),
                    "semantic_keywords": semantic_keywords,
                    "llm_keywords": llm_keywords,
                    "method": "enhanced_vector_llm",
                },
            )

        except Exception as e:
            logger.error(f"Enhanced keyword suggestion failed: {e}")
            # Fallback to basic keyword extraction
            basic_keywords = [word for word in query.split() if len(word) > 3][
                :max_keywords
            ]
            return (
                True,
                {
                    "Keyword Output": ", ".join(basic_keywords),
                    "method": "fallback_basic",
                },
            )


# =================================================================
# 🔄 INTEGRATION FUNCTIONS FOR EXISTING WORKFLOW
# =================================================================


def create_vector_index_if_needed() -> bool:
    """
    Initialize vector index for semantic search if not already created.

    Returns:
        Success status
    """
    try:
        vector_search = VectorTableSearch()
        return vector_search.create_table_embeddings(force_rebuild=False)
    except Exception as e:
        logger.error(f"Failed to create vector index: {e}")
        return False


def enhanced_suggest_keywords_function(params: dict) -> tuple[bool, dict | str]:
    """
    Enhanced version of suggest keywords function using vector similarity.

    This can be used as a drop-in replacement for the existing suggest keywords function.
    """
    try:
        query = params.get("Input", "").strip()
        if not query:
            return (False, "Input parameter missing")

        suggester = EnhancedKeywordSuggester()
        return suggester.suggest_enhanced_keywords(query)

    except Exception as e:
        logger.error(f"Enhanced suggest keywords error: {e}")
        return (False, f"Enhanced suggestion failed: {e}")


# =================================================================
# 🧪 TESTING AND BENCHMARKING
# =================================================================


def test_vector_search():
    """Test vector search functionality"""
    print("🧪 Testing Vector Search Functionality")
    print("=" * 40)

    # Initialize vector search
    vector_search = VectorTableSearch()

    # Create embeddings
    start_time = time.time()
    success = vector_search.create_table_embeddings()
    creation_time = time.time() - start_time

    print(f"📊 Vector index creation: {success} ({creation_time:.2f}s)")

    if success:
        # Test semantic search
        test_queries = [
            "connector specifications",
            "torque requirements",
            "C0000268 shell size",
            "RPT panel mount",
            "contact plating",
        ]

        for query in test_queries:
            start_time = time.time()
            results = vector_search.semantic_keyword_search(query, top_k=3)
            search_time = time.time() - start_time

            print(f"🔍 Query: '{query}' → {len(results)} results ({search_time:.3f}s)")

            if results:
                best_match = results[0]
                print(
                    f"   Best match: {best_match['table_name']} (score: {best_match['similarity_score']:.3f})"
                )

    print("✅ Vector search testing complete")


if __name__ == "__main__":
    test_vector_search()


