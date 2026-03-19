"""
Embedding Management for CONTEXTUAL PRODUCT SEARCH

Handles:
1. Loading product family data from harvested.db
2. Generating embeddings using qwen3-embedding:8b (via Ollama)
3. Loading embeddings to Chroma vector DB (database/vector_index/embeddings.db)
4. Verification and semantic search
"""

import os
import sys
import json
import sqlite3
import argparse
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import logging

# Configure logging to both console and file
log_dir = Path(__file__).parent.parent / "config" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler(
    log_dir / "embeddings.log",
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', 
                                    datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database.db_utils import get_db_connection
from Layer_2_Agentic_Reasoning.config.config_loader import load_config


class EmbeddingManager:
    """Manages embedding generation and Chroma DB operations"""
    
    def __init__(self, model_name: str = "qwen3-embedding:8b", debug: bool = False):
        """
        Initialize embedding manager
        
        Args:
            model_name: Model to use for embeddings (default: qwen3-embedding:8b via Ollama)
            debug: Enable debug logging
        """
        self.model_name: str = model_name
        self.debug: bool = debug
        self.model: Any = None
        self.chroma_client: Any = None
        self.embeddings_collection: Any = None
        
        if debug:
            logger.setLevel(logging.DEBUG)
    
    def load_model(self) -> bool:
        """
        Load embedding model (with fallbacks)
        
        Returns:
            True if model loaded successfully
        """
        models_to_try = [
            ("ollama", "qwen3-embedding:8b"),
            ("ollama", "nomic-embed-text"),
            ("ollama", "embeddinggemma:latest"),
        ]
        
        for source, model in models_to_try:
            try:
                if source == "ollama":
                    import ollama
                    logger.info(f"Testing Ollama model: {model}...")
                    # Test connectivity
                    response = ollama.embed(model, "test")
                    logger.info(f"[OK] Ollama model available: {model}")
                    self.model = ollama
                    self.model_name = model
                    return True
                    
            except Exception as e:
                logger.debug(f"Failed to load {source}/{model}: {str(e)}")
                continue
        
        logger.error("[FAIL] No embedding model available. Ensure Ollama is running and at least one model is available.")
        return False
    
    def initialize_chroma(self) -> bool:
        """
        Initialize Chroma DB (in database/vector_index/embeddings.db)
        
        Returns:
            True if successful
        """
        try:
            import chromadb
            
            # Ensure vector_index folder exists
            vector_index_folder = Path(__file__).parent.parent.parent / "database" / "vector_index"
            vector_index_folder.mkdir(parents=True, exist_ok=True)
            
            embeddings_path = str(vector_index_folder / "embeddings.db")
            logger.info(f"Initializing Chroma at: {embeddings_path}")
            
            self.chroma_client = chromadb.PersistentClient(path=str(vector_index_folder))
            
            # Get or create collection for embeddings
            self.embeddings_collection = self.chroma_client.get_or_create_collection(
                name="product_families",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"[OK] Chroma initialized with collection 'product_families'")
            return True
            
        except Exception as e:
            logger.error(f"[FAIL] Failed to initialize Chroma: {e}")
            return False
    
    def load_families_from_db(self) -> List[Dict]:
        """
        Load all product families from harvested.db
        
        Returns:
            List of family dictionaries with id, name, applications, construction_details
        """
        try:
            conn = get_db_connection("database/harvested.db")
            cursor = conn.cursor()
            
            query = """
            SELECT 
                id,
                family_code,
                name,
                subtitle,
                applications,
                construction_details,
                description,
                page_number
            FROM product_families
            ORDER BY id
            """
            
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            families = []
            for row in rows:
                family = dict(zip(columns, row))
                families.append(family)
            
            conn.close()
            logger.info(f"[OK] Loaded {len(families)} families from harvested.db")
            return families
            
        except Exception as e:
            logger.error(f"[FAIL] Failed to load families: {e}")
            return []
    
    def prepare_text_for_embedding(self, family: Dict) -> str:
        """
        Combine family fields into single text for embedding
        
        Args:
            family: Family dictionary
            
        Returns:
            Combined text string
        """
        parts = []
        
        # Family name (important)
        if family.get('name'):
            parts.append(f"Product Family: {family['name']}")
        
        # Family code
        if family.get('family_code'):
            parts.append(f"Code: {family['family_code']}")
        
        # Subtitle
        if family.get('subtitle'):
            parts.append(f"Subtitle: {family['subtitle']}")
        
        # Description
        if family.get('description'):
            parts.append(f"Description: {family['description']}")
        
        # Applications (most important for semantic search)
        if family.get('applications'):
            parts.append(f"Applications: {family['applications']}")
        
        # Construction details (JSON)
        if family.get('construction_details'):
            try:
                if isinstance(family['construction_details'], str):
                    details = json.loads(family['construction_details'])
                else:
                    details = family['construction_details']
                
                details_text = ", ".join([
                    f"{k}: {v}" for k, v in details.items() if v
                ])
                if details_text:
                    parts.append(f"Construction: {details_text}")
            except:
                pass
        
        return "\n".join(parts)
    
    def generate_embeddings(self, families: List[Dict]) -> List[Tuple[str, List[float], Dict]]:
        """
        Generate embeddings for all families
        
        Args:
            families: List of family dictionaries
            
        Returns:
            List of (id, embedding, metadata) tuples
        """
        embeddings_data = []
        
        logger.info(f"Generating embeddings for {len(families)} families...")
        start_time = time.time()
        
        for i, family in enumerate(families):
            try:
                # Prepare text
                text = self.prepare_text_for_embedding(family)
                
                if not text or len(text.strip()) < 3:
                    logger.warning(f"Skipping family {family.get('id')}: insufficient text for embedding")
                    continue
                
                # Generate embedding from Ollama
                response = self.model.embed(self.model_name, text)  # type: ignore
                
                # Extract embedding vector from response
                if not hasattr(response, 'embeddings') or response.embeddings is None:
                    logger.error(f"No embeddings attribute in response for family {family.get('id')}")
                    continue
                
                if len(response.embeddings) == 0:
                    logger.error(f"Empty embeddings list in response for family {family.get('id')}")
                    continue
                
                embedding = response.embeddings[0]  # Get first (and only) embedding
                
                # Prepare metadata
                metadata = {
                    "family_id": str(family['id']),
                    "family_code": family.get('family_code', ''),
                    "name": family.get('name', ''),
                    "applications": family.get('applications', '')[:500] if family.get('applications') else '',
                }
                
                embeddings_data.append((
                    str(family['id']),
                    embedding,
                    metadata
                ))
                
                # Progress
                if (i + 1) % 20 == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    logger.info(f"  {i + 1}/{len(families)} embeddings generated ({rate:.1f}/sec)")
                
            except Exception as e:
                logger.error(f"Failed to embed family {family.get('id')}: {type(e).__name__}: {e}")
                continue
        
        elapsed = time.time() - start_time
        logger.info(f"[OK] Generated {len(embeddings_data)} embeddings in {elapsed:.1f}s")
        
        return embeddings_data
    
    def load_to_chroma(self, embeddings_data: List[Tuple[str, List[float], Dict]]) -> bool:
        """
        Load embeddings to Chroma collection
        
        Args:
            embeddings_data: List of (id, embedding, metadata) tuples
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Loading {len(embeddings_data)} embeddings to Chroma...")
            
            # Batch insert (Chroma has limits on batch size)
            batch_size = 100
            for i in range(0, len(embeddings_data), batch_size):
                batch = embeddings_data[i:i+batch_size]
                
                ids = [item[0] for item in batch]
                embeddings = [item[1] for item in batch]
                metadatas = [item[2] for item in batch]
                documents = [
                    f"{m['name']} - {m['applications'][:100]}" 
                    for m in metadatas
                ]
                
                self.embeddings_collection.upsert(  # type: ignore
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
                
                logger.info(f"  Loaded batch {i//batch_size + 1}/{(len(embeddings_data)+batch_size-1)//batch_size}")
            
            logger.info(f"[OK] Successfully loaded {len(embeddings_data)} embeddings to Chroma")
            return True
            
        except Exception as e:
            logger.error(f"[FAIL] Failed to load embeddings to Chroma: {e}")
            return False
    
    def verify_embeddings(self) -> bool:
        """
        Verify embeddings are loaded and queryable
        
        Returns:
            True if verification successful
        """
        try:
            logger.info("Verifying embeddings in Chroma...")
            
            # Check collection count
            count = self.embeddings_collection.count()  # type: ignore
            logger.info(f"  Embeddings in collection: {count}")
            
            if count == 0:
                logger.error("[FAIL] No embeddings found in collection")
                return False
            
            # Test query with embedding from same model
            logger.info("  Testing semantic search...")
            query_text = "high pressure hoses"
            
            # Generate query embedding using same model as data
            response = self.model.embed(self.model_name, query_text)  # type: ignore
            query_embedding = response.embeddings[0]
            
            # Query by embedding instead of text (to avoid embedding mismatch)
            results = self.embeddings_collection.query(  # type: ignore
                query_embeddings=[query_embedding],
                n_results=3
            )
            
            if results and results['ids'] and len(results['ids'][0]) > 0:
                logger.info(f"[OK] Semantic search working! Found {len(results['ids'][0])} results")
                
                # Show top result
                top_id = results['ids'][0][0]
                top_score = results['distances'][0][0] if results['distances'] else None
                logger.info(f"  Top result: Family {top_id} (distance: {top_score})")
                
                return True
            else:
                logger.error("[FAIL] Semantic search returned no results")
                return False
                
        except Exception as e:
            logger.error(f"[FAIL] Verification failed: {e}")
            return False
    
    def semantic_search(self, query_text: str, top_k: int = 5, similarity_threshold: float = 0.3) -> List[Dict]:
        """
        Perform semantic search using vector embeddings.
        
        Finds the most semantically similar product families to the query text
        using cosine distance in the Chroma vector database.
        
        Args:
            query_text (str): Natural language query
            top_k (int): Number of top results to return
            similarity_threshold (float): Minimum similarity score (0-1, where 1 = identical)
        
        Returns:
            List of matching product families with metadata and similarity scores
        """
        try:
            # Ensure model and collection are initialized
            if not self.model:  # type: ignore
                if not self.load_model():
                    logger.error("[FAIL] Could not load embedding model")
                    return []
            
            if not self.embeddings_collection:  # type: ignore
                if not self.initialize_chroma():
                    logger.error("[FAIL] Could not initialize Chroma")
                    return []
            
            # Generate embedding for the query using same model
            logger.info(f"[...] Generating embedding for query: {query_text[:100]}...")
            response = self.model.embed(self.model_name, query_text)  # type: ignore
            query_embedding = response.embeddings[0]
            
            # Query Chroma collection
            logger.info(f"[...] Querying {self.model_name} embeddings (top_k={top_k}, threshold={similarity_threshold})")
            results = self.embeddings_collection.query(  # type: ignore
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            # Process results
            matched_items = []
            
            if results and results.get("metadatas") and len(results["metadatas"]) > 0:
                metadatas = results["metadatas"][0]
                distances = results.get("distances", [[]])[0]
                
                for i, metadata in enumerate(metadatas):
                    distance = distances[i] if i < len(distances) else 2.0
                    # Convert distance to similarity (cosine distance 0-2 -> similarity 0-1)
                    similarity = 1.0 - (distance / 2.0)
                    
                    # Apply threshold filtering
                    if similarity >= similarity_threshold:
                        matched_items.append({
                            "metadata": metadata,
                            "distance": distance,
                            "similarity": similarity
                        })
                        logger.info(
                            f"[OK] Match: {metadata.get('family_name', 'Unknown')} "
                            f"(similarity: {similarity:.4f}, distance: {distance:.4f})"
                        )
                    else:
                        logger.info(
                            f"[SKIP] Below threshold: {metadata.get('family_name', 'Unknown')} "
                            f"(similarity: {similarity:.4f} < {similarity_threshold})"
                        )
            
            logger.info(f"[OK] Found {len(matched_items)} matches above threshold {similarity_threshold}")
            return matched_items
            
        except Exception as e:
            logger.error(f"[FAIL] Semantic search error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def populate_embeddings(self) -> bool:
        """
        Run complete embedding population workflow
        
        Returns:
            True if successful
        """
        logger.info("=" * 70)
        logger.info("EMBEDDING POPULATION WORKFLOW")
        logger.info("=" * 70)
        
        # Step 1: Load model
        if not self.load_model():
            return False
        
        # Step 2: Initialize Chroma
        if not self.initialize_chroma():
            return False
        
        # Step 3: Load families
        families = self.load_families_from_db()
        if not families:
            return False
        
        # Step 4: Generate embeddings
        embeddings_data = self.generate_embeddings(families)
        if not embeddings_data:
            return False
        
        # Step 5: Load to Chroma
        if not self.load_to_chroma(embeddings_data):
            return False
        
        # Step 6: Verify
        if not self.verify_embeddings():
            return False
        
        logger.info("=" * 70)
        logger.info("[OK] EMBEDDING POPULATION COMPLETE")
        logger.info("=" * 70)
        
        return True


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Manage embeddings for CONTEXTUAL PRODUCT SEARCH"
    )
    
    parser.add_argument(
        "--action",
        choices=["populate", "verify", "clear"],
        default="populate",
        help="Action to perform"
    )
    
    parser.add_argument(
        "--model",
        default="multilingual-e5-base",
        help="Embedding model to use"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    manager = EmbeddingManager(model_name=args.model, debug=args.debug)
    
    if args.action == "populate":
        success = manager.populate_embeddings()
        sys.exit(0 if success else 1)
    
    elif args.action == "verify":
        manager = EmbeddingManager(model_name=args.model, debug=args.debug)
        if not manager.load_model():
            sys.exit(1)
        if not manager.initialize_chroma():
            sys.exit(1)
        success = manager.verify_embeddings()
        sys.exit(0 if success else 1)
    
    elif args.action == "clear":
        logger.warning("Clearing embeddings...")
        import chromadb
        vector_index_folder = Path(__file__).parent.parent.parent / "database" / "vector_index"
        client = chromadb.PersistentClient(path=str(vector_index_folder))
        try:
            client.delete_collection(name="product_families")
            logger.info("[OK] Embeddings collection cleared")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to clear: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()

