
"""
Asynchronous processing utilities for improved performance.

Provides async wrappers around database operations and parallel function execution
to reduce blocking I/O and improve system responsiveness. Used by function_library
for table searches and batch operations.

Key Components:
- AsyncDatabaseManager: Async database operations with connection pooling
- Parallel function execution with concurrent.futures
- Performance monitoring and optimization utilities
"""

import asyncio
import logging
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from langchain_ollama import ChatOllama

from agentic_reasoning.config.config_loader import CONFIG
from agentic_reasoning.db.connection import get_output_connection

logger = logging.getLogger("ASYNC_HELPERS")


class AsyncDatabaseManager:
    """
    Async database operations for improved performance.
    
    Wraps synchronous SQLite operations in ThreadPoolExecutor to prevent
    blocking the event loop. Used for table searches and batch operations
    where performance is critical.
    """

    def __init__(self, db_path: str = None):
        """
        Initialize async database manager.
        
        Args:
            db_path: Path to SQLite database (defaults to harvested_db)
        """
        self.db_path = db_path or CONFIG["harvested_db"]
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def async_table_search(self, keywords: List[str]) -> List[Dict]:
        """
        Perform asynchronous table search across all tables for given keywords.
        
        Executes database query in thread pool to avoid blocking main thread.
        Used by func_table_search() for improved performance.

        Args:
            keywords: List of search terms to match against table data

        Returns:
            List of matching table records with metadata
        """
        loop = asyncio.get_event_loop()

        def _search_tables():
            """Synchronous database search wrapped for async execution"""
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()

                    # Get all tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]

                    results = []
                    for table_name in tables:
                        if table_name.startswith("sqlite_"):
                            continue

                        # Build search query for all text columns
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = [
                            col[1]
                            for col in cursor.fetchall()
                            if col[2] in ("TEXT", "VARCHAR")
                        ]

                        if not columns:
                            continue

                        # Create search conditions
                        search_conditions = []
                        search_params = []

                        for keyword in keywords:
                            for column in columns:
                                search_conditions.append(f"{column} LIKE ?")
                                search_params.append(f"%{keyword}%")

                        if search_conditions:
                            query = f"SELECT * FROM {table_name} WHERE {' OR '.join(search_conditions)}"
                            cursor.execute(query, search_params)

                            for row in cursor.fetchall():
                                results.append(
                                    {"table_name": table_name, "data": dict(row)}
                                )

                    return results

            except Exception as e:
                logger.error(f"Async table search error: {e}")
                return []

        return await loop.run_in_executor(self._executor, _search_tables)

    async def async_multiple_queries(
        self, queries: List[Tuple[str, List]]
    ) -> List[Any]:
        """
        Execute multiple database queries concurrently.

        Args:
            queries: List of (query_string, parameters) tuples

        Returns:
            List of query results in order
        """
        loop = asyncio.get_event_loop()

        def _execute_query(query_params):
            query, params = query_params
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute(query, params or [])
                    return [dict(row) for row in cursor.fetchall()]
            except Exception as e:
                logger.error(f"Query execution error: {e}")
                return []

        # Execute all queries concurrently
        tasks = [
            loop.run_in_executor(self._executor, _execute_query, query_params)
            for query_params in queries
        ]

        return await asyncio.gather(*tasks)

    def close(self):
        """Clean up thread pool executor"""
        self._executor.shutdown(wait=True)


class AsyncLLMManager:
    """Concurrent LLM call management for improved performance"""

    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def async_llm_call(
        self, llm_config: Dict, prompt: str, context: str = ""
    ) -> str:
        """
        Execute a single LLM call asynchronously with concurrency control.

        Args:
            llm_config: LLM configuration dict
            prompt: Input prompt for the LLM
            context: Optional context for logging

        Returns:
            LLM response string
        """
        async with self._semaphore:
            loop = asyncio.get_event_loop()

            def _make_llm_call():
                try:
                    # Create fresh LLM instance for this call
                    llm = ChatOllama(
                        model=llm_config["model"],
                        temperature=llm_config["temperature"],
                        num_ctx=4096,
                    )

                    response = llm.invoke(prompt)
                    return response.content

                except Exception as e:
                    logger.error(f"LLM call error ({context}): {e}")
                    return f"Error: {str(e)}"

            return await loop.run_in_executor(None, _make_llm_call)

    async def async_multiple_llm_calls(self, calls: List[Tuple[str, str]]) -> List[str]:
        """
        Execute multiple LLM calls concurrently with basic LLM.

        Args:
            calls: List of (prompt, context) tuples

        Returns:
            List of LLM responses in order
        """
        basic_config = CONFIG["llms"]["basic"]

        tasks = [
            self.async_llm_call(basic_config, prompt, context)
            for prompt, context in calls
        ]

        return await asyncio.gather(*tasks)

    async def async_reasoning_llm_calls(
        self, calls: List[Tuple[str, str]]
    ) -> List[str]:
        """
        Execute multiple reasoning LLM calls concurrently.

        Args:
            calls: List of (prompt, context) tuples

        Returns:
            List of LLM responses in order
        """
        reasoning_config = CONFIG["llms"]["reasoning"]

        tasks = [
            self.async_llm_call(reasoning_config, prompt, context)
            for prompt, context in calls
        ]

        return await asyncio.gather(*tasks)


class AsyncWorkflowHelper:
    """High-level async operations for workflow integration"""

    def __init__(self):
        self.db_manager = AsyncDatabaseManager()
        self.llm_manager = AsyncLLMManager()

    async def async_product_search_and_analysis(self, product_codes: List[str]) -> Dict:
        """
        Search for multiple product codes and analyze results concurrently.

        Args:
            product_codes: List of product codes to search for

        Returns:
            Dict with search results and analysis
        """
        # Step 1: Concurrent database searches
        search_tasks = [
            self.db_manager.async_table_search([code]) for code in product_codes
        ]

        search_results = await asyncio.gather(*search_tasks)

        # Step 2: Concurrent LLM analysis of results
        analysis_prompts = []
        for i, (code, results) in enumerate(zip(product_codes, search_results)):
            if results:
                prompt = f"Analyze the technical specifications for product {code}: {results[:2]}"
                analysis_prompts.append((prompt, f"product_{code}"))

        if analysis_prompts:
            analyses = await self.llm_manager.async_multiple_llm_calls(analysis_prompts)
        else:
            analyses = []

        return {
            "product_codes": product_codes,
            "search_results": {
                code: results for code, results in zip(product_codes, search_results)
            },
            "analyses": {
                code: analysis for code, analysis in zip(product_codes, analyses)
            },
        }

    async def async_keyword_suggestion_and_search(
        self, base_query: str, num_suggestions: int = 3
    ) -> Dict:
        """
        Generate keyword suggestions and perform searches concurrently.

        Args:
            base_query: Original user query
            num_suggestions: Number of keyword suggestions to generate

        Returns:
            Dict with suggestions and search results
        """
        # Step 1: Generate keyword suggestions concurrently
        suggestion_prompts = [
            (
                f"Generate {i+1} relevant technical keywords for query: {base_query}",
                f"suggestion_{i}",
            )
            for i in range(num_suggestions)
        ]

        suggestions = await self.llm_manager.async_multiple_llm_calls(
            suggestion_prompts
        )

        # Step 2: Extract keywords and search concurrently
        all_keywords = []
        for suggestion in suggestions:
            keywords = [k.strip() for k in suggestion.split(",") if k.strip()]
            all_keywords.extend(keywords[:2])  # Take first 2 from each suggestion

        # Remove duplicates while preserving order
        unique_keywords = list(dict.fromkeys(all_keywords))

        # Step 3: Concurrent searches
        if unique_keywords:
            search_results = await self.db_manager.async_table_search(unique_keywords)
        else:
            search_results = []

        return {
            "base_query": base_query,
            "suggestions": suggestions,
            "keywords": unique_keywords,
            "search_results": search_results,
        }

    def cleanup(self):
        """Clean up resources"""
        self.db_manager.close()


# =================================================================
# 🚀 ASYNC WRAPPER FUNCTIONS FOR EXISTING WORKFLOW
# =================================================================


def run_async_table_search(keywords: List[str]) -> List[Dict]:
    """
    Wrapper to run async table search from synchronous code.

    Args:
        keywords: List of search keywords

    Returns:
        List of matching table records
    """

    async def _async_search():
        db_manager = AsyncDatabaseManager()
        try:
            results = await db_manager.async_table_search(keywords)
            return results
        finally:
            db_manager.close()

    # Run in new event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_async_search())
    finally:
        loop.close()


def run_async_multiple_llm_calls(
    prompts_and_contexts: List[Tuple[str, str]],
) -> List[str]:
    """
    Wrapper to run multiple LLM calls from synchronous code.

    Args:
        prompts_and_contexts: List of (prompt, context) tuples

    Returns:
        List of LLM responses
    """

    async def _async_llm_calls():
        llm_manager = AsyncLLMManager()
        return await llm_manager.async_multiple_llm_calls(prompts_and_contexts)

    # Run in new event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_async_llm_calls())
    finally:
        loop.close()


# =================================================================
# 🧪 TESTING AND BENCHMARKING
# =================================================================


async def benchmark_async_performance():
    """Benchmark async vs sync performance for common operations"""
    print("🚀 Benchmarking Async Performance")
    print("=" * 40)

    # Test data
    test_keywords = ["C0000268", "connector", "shell", "contact"]
    test_prompts = [
        ("Analyze connector specifications", "test_1"),
        ("Extract product numbers", "test_2"),
        ("Summarize technical data", "test_3"),
    ]

    # Benchmark async operations
    start_time = time.time()

    db_manager = AsyncDatabaseManager()
    llm_manager = AsyncLLMManager()

    try:
        # Concurrent operations
        search_task = db_manager.async_table_search(test_keywords)
        llm_task = llm_manager.async_multiple_llm_calls(test_prompts)

        search_results, llm_results = await asyncio.gather(search_task, llm_task)

        async_time = time.time() - start_time

        print(f"⚡ Async execution: {async_time:.2f}s")
        print(f"📊 Search results: {len(search_results)} records")
        print(f"🧠 LLM responses: {len(llm_results)} responses")

        return {
            "async_time": async_time,
            "search_results": len(search_results),
            "llm_responses": len(llm_results),
        }

    finally:
        db_manager.close()


if __name__ == "__main__":
    # Run benchmark
    async def main():
        await benchmark_async_performance()

    asyncio.run(main())


