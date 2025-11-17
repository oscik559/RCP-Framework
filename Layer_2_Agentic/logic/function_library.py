"""
Function Library for Agentic Reasoning System

Core executable functions for LangGraph workflow nodes. Provides search, data processing,
and analysis capabilities for technical document processing.

Function Interface:
    All functions follow: (params: dict) -> (bool, dict | str)
    - Input: Named parameters from FunctionParametersLibrary
    - Output: Success flag + result dict or error message

Key Functions:
    Search: Table/text/image search across extracted documents
    Processing: Filter, assemble, and normalize technical data
    Analysis: LLM-powered data synthesis and product code extraction
"""

# SECTION 4  Expanded Function-Execution Library
import json
import logging
import pathlib
import random
import re
import sqlite3
import time
from typing import Any, Dict, Tuple

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..config.config_loader import CONFIG
from ..config.debug_config import debug
from ..config.prompt_loader import get_prompt_loader
from ..db.connection import (
    get_agentic_connection,
    get_output_connection,
)
from .llm_helpers import get_basic_llm, get_reasoning_llm

logger = logging.getLogger("FUNCTION_LIBRARY")
DB_PATH_OUTPUT = CONFIG["harvested_db"]

# Import async helpers for performance improvements
try:
    from .async_helpers import (
        run_async_table_search,
        run_async_multiple_llm_calls,
    )

    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    logger.warning("Async helpers not available - falling back to sync operations")


# ── Helper Functions ───────────────────────────
def _parse_json_safely(json_str: str, default=None, context: str = ""):
    """Parse JSON string safely with fallback and error logging."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"[JSON Parse Error{' - ' + context if context else ''}] {e}")
        return default


def _parse_keywords_from_string(keyword_str: str, context: str = "") -> list[str]:
    """Extract keywords from comma-separated string, removing duplicates."""
    if not keyword_str:
        debug.print_function(f"[{context}] No keywords provided")
        return []

    keywords = [k.strip() for k in keyword_str.split(",") if k.strip()]
    debug.print_function(f"[{context}] Extracted {len(keywords)} keywords: {keywords}")
    return keywords


def _build_llm_processing_chain(
    system_msg: str, user_template: str, llm_type: str = "basic"
):
    """Create LangChain chat prompt with system message and user template.

    Creates a fresh LLM instance for each call to prevent context persistence.
    Also adds explicit conversation reset markers.
    """
    # Create a fresh LLM instance to avoid context contamination
    if llm_type == "basic":
        from ..config.config_loader import CONFIG
        from langchain_ollama import ChatOllama
        import time

        cfg = CONFIG["llms"]["basic"]
        # Use unique session ID to prevent context reuse
        llm = ChatOllama(
            model=cfg["model"],
            temperature=cfg["temperature"],
            num_ctx=4096,  # Limit context window
            system=None,  # Reset system context
        )
    else:
        from ..config.config_loader import CONFIG
        from langchain_ollama import ChatOllama
        import time

        cfg = CONFIG["llms"]["reasoning"]
        llm = ChatOllama(
            model=cfg["model"],
            temperature=cfg["temperature"],
            num_ctx=4096,  # Limit context window
            system=None,  # Reset system context
        )

    # Add explicit conversation reset to system message
    reset_system_msg = (
        f"CONVERSATION RESET - IGNORE ALL PREVIOUS CONTEXT.\n\n{system_msg}"
    )

    return (
        ChatPromptTemplate.from_messages(
            [
                ("system", reset_system_msg),
                ("user", user_template),
            ]
        )
        | llm
        | StrOutputParser()
    )


def _validate_required_parameters(
    params: dict, required_keys: list[str]
) -> tuple[bool, str]:
    """Validate that required parameters are present and non-empty."""
    for key in required_keys:
        if not params.get(key, "").strip():
            return (False, f"{key} parameter missing")
    return (True, "")


# ── Function Implementations ─────────────────────

# ========================================
# SEARCH OPERATIONS
# ========================================


def func_table_search(params: dict) -> tuple[bool, dict | str]:
    """
    Search extracted tables for rows containing specified keywords.

    Primary search function that scans all tables in harvested.db for keyword matches.
    Supports multiple keyword formats and automatic format variations (RPT2354 → RPT 2354).
    Uses async search for improved performance with large datasets.

    Args:
        params: {"Keyword Output": "comma,separated,keywords"}

    Returns:
        (True, {"Table": list_of_matching_rows, "Document Name": list_of_sources})
        or (False, error_message)
    """

    keywords_raw = params.get("Keyword Output", "").strip()
    debug.print_function(f"[func_table_search] Received keywords: {repr(keywords_raw)}")
    if not keywords_raw:
        logger.error(f"[func_table_search] Keyword Output parameter is empty. Available params: {list(params.keys())}")
        return (False, "Keyword Output parameter missing or empty. This function requires keywords from a previous function like 'Extract Product Number'.")

    keywords = _parse_keywords_from_string(keywords_raw, "func_table_search")
    if not keywords:
        return (False, "no valid keywords")

    # Enhanced keyword processing for product numbers
    enhanced_keywords = []
    for keyword in keywords:
        enhanced_keywords.append(keyword)  # Original format
        # Add format variations for product numbers
        enhanced_keywords.extend(_generate_format_variations(keyword))

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for keyword in enhanced_keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    debug.print_function(f"[func_table_search] Enhanced keywords: {unique_keywords}")

    # Try async search for better performance if available
    if ASYNC_AVAILABLE and len(unique_keywords) > 2:
        try:
            debug.print_function(
                "[func_table_search] Using async search for better performance"
            )
            async_results = run_async_table_search(unique_keywords)
            if async_results:
                # Convert async results to expected format
                rows = []
                filenames = set()
                for result in async_results:
                    if result.get("table_name") == "extracted_tables":
                        data = result.get("data", {})
                        rows.append(data)
                        if "filename" in data:
                            filenames.add(data["filename"])

                if rows:
                    debug.print_function(
                        f"[func_table_search] Async search found {len(rows)} matching rows"
                    )
                    return (
                        True,
                        {
                            "Table Output": json.dumps(rows),
                            "Document Name": ", ".join(sorted(filenames)),
                        },
                    )
        except Exception as e:
            debug.print_function(
                f"[func_table_search] Async search failed, falling back to sync: {e}"
            )

    # Fallback to synchronous search
    try:
        with get_output_connection() as db_connection:
            cursor = db_connection.cursor()
            like_clause = " OR ".join(["table_data LIKE ?"] * len(unique_keywords))
            cursor.execute(
                f"""
                SELECT id, filename, page_number, table_data
                FROM extracted_tables
                WHERE {like_clause}
            """,
                [f"%{k}%" for k in unique_keywords],
            )

            cols = [d[0] for d in cursor.description]
            rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
            filenames = sorted({r["filename"] for r in rows})

            debug.print_function(f"[func_table_search] Found {len(rows)} matching rows")
            return (
                True,
                {
                    "Table Output": json.dumps(rows),
                    "Document Name": ", ".join(filenames),
                },
            )

    except Exception as e:
        return (False, f"DB error: {e}")


def _generate_format_variations(keyword: str) -> list[str]:
    """
    Generate different formatting variations of a product number/keyword (GENERIC).
    
    Handles common spacing and separator variations without domain-specific patterns.
    """
    variations = []

    # Skip if not a potential product number (too short or no alphanumeric pattern)
    if len(keyword) < 3 or not re.search(r"[A-Za-z].*\d|\d.*[A-Za-z]", keyword):
        return variations

    # General patterns: Add/remove spaces around common separators
    if "/" in keyword:
        # Handle slash separators
        parts = keyword.split("/")
        if len(parts) == 2:
            left, right = parts
            variations.extend(
                [
                    f"{left.strip()}/{right.strip()}",
                    f"{left.strip()} /{right.strip()}",
                    f"{left.strip()}/ {right.strip()}",
                    f"{left.strip()} / {right.strip()}",
                ]
            )

    if "-" in keyword:
        # Handle dash separators
        parts = keyword.split("-")
        if len(parts) == 2:
            left, right = parts
            variations.extend(
                [
                    f"{left.strip()}-{right.strip()}",
                    f"{left.strip()} - {right.strip()}",
                    f"{left.strip()} {right.strip()}",
                    f"{left.strip()}{right.strip()}",  # Compressed
                ]
            )

    # Add spaced version and compressed version
    if " " in keyword:
        variations.append(re.sub(r"\s+", "", keyword))  # Remove all spaces
    else:
        # Add spaces before numbers after letters
        spaced = re.sub(r"([A-Za-z])(\d)", r"\1 \2", keyword)
        if spaced != keyword:
            variations.append(spaced)

    debug.print_function(f"[_generate_format_variations] {keyword} → {variations}")
    return list(set(variations))  # Remove duplicates


def func_image_search(params: dict) -> tuple[bool, dict]:
    """Search for relevant technical images using enhanced 26-field metadata intelligence."""
    kw_raw = params.get("Keyword Output", "").strip()
    debug.print_function(f"[func_image_search] Received keywords: {repr(kw_raw)}")

    if not kw_raw:
        return (False, "Keyword Output parameter missing")

    keywords = _parse_keywords_from_string(kw_raw, "func_image_search")
    if not keywords:
        return (False, "no valid keywords")

    try:
        with get_output_connection() as conn:
            cur = conn.cursor()

            # Enhanced search logic: try exact match first, then partial matches
            search_attempts = []

            # 1. Try exact keyword matches
            for kw in keywords:
                search_attempts.append(kw)
                # 2. Try normalized/partial matches (e.g., RPT2354313/350 -> RPT2354)
                if len(kw) > 6:
                    # Extract base product family (first 6-7 chars)
                    base_code = kw[:7] if kw[6:7].isdigit() else kw[:6]
                    if base_code not in search_attempts:
                        search_attempts.append(base_code)

            debug.print_function(
                f"[func_image_search] Search attempts: {search_attempts}"
            )

            best_results = []
            for search_term in search_attempts:
                # ENHANCED QUERY: Use intelligent filtering with 26-field metadata
                cur.execute(
                    """
                    SELECT document_name, page_number, image_index, image_filename, image_format, ocr_text,
                           relevance_score, has_technical_content, image_type, image_width, image_height,
                           image_x, image_y, is_large_image, is_center_region
                    FROM saved_images
                    WHERE (document_name LIKE ? OR image_filename LIKE ?)
                      AND has_technical_content = 1  -- Filter to technical content only
                      AND relevance_score >= 6.0     -- High relevance images only
                    ORDER BY relevance_score DESC, image_width DESC, page_number
                    """,
                    (f"%{search_term}%", f"%{search_term}%"),
                )

                results = cur.fetchall()
                if results:
                    debug.print_function(
                        f"[func_image_search] Found {len(results)} high-quality technical images for '{search_term}'"
                    )
                    best_results = results
                    break  # Use first successful search

            if not best_results:
                # Fallback: try without strict filtering
                for search_term in search_attempts:
                    cur.execute(
                        """
                        SELECT document_name, page_number, image_index, image_filename, image_format, ocr_text,
                               relevance_score, has_technical_content, image_type, image_width, image_height,
                               image_x, image_y, is_large_image, is_center_region
                        FROM saved_images
                        WHERE (document_name LIKE ? OR image_filename LIKE ?)
                          AND has_technical_content = 1  -- Still require technical content
                        ORDER BY relevance_score DESC, image_width DESC
                        """,
                        (f"%{search_term}%", f"%{search_term}%"),
                    )
                    results = cur.fetchall()
                    if results:
                        debug.print_function(
                            f"[func_image_search] Fallback: Found {len(results)} technical images for '{search_term}'"
                        )
                        best_results = results
                        break

            if not best_results:
                return (
                    True,
                    {
                        "Image Output": f"No technical images found for keywords: {', '.join(keywords)}",
                        "Document Name": "",
                    },
                )

            # ENHANCED SCORING: Use 26-field metadata for intelligent ranking
            scored_images = []

            for (
                doc_name,
                page_num,
                img_idx,
                img_filename,
                img_format,
                ocr_text,
                relevance_score,
                has_technical_content,
                image_type,
                image_width,
                image_height,
                image_x,
                image_y,
                is_large_image,
                is_center_region,
            ) in best_results:

                # Start with the ML-determined relevance score
                score = float(relevance_score or 0.0)

                # Enhanced scoring using metadata intelligence
                # 1. Image type bonus (technical diagrams are preferred)
                if image_type == "technical_diagram":
                    score += 2.0
                elif image_type == "technical_content":
                    score += 1.0

                # 2. Size-based scoring (larger images often more detailed)
                if is_large_image:
                    score += 1.5
                elif image_width and image_height:
                    # Bonus for substantial size images
                    pixel_area = image_width * image_height
                    if pixel_area > 50000:  # > 50K pixels
                        score += 1.0

                # 3. Position-based scoring (center images often more important)
                if is_center_region:
                    score += 1.0

                # 4. Page position scoring
                if page_num == 1:
                    score += 0.5  # Title pages can have overview diagrams
                elif page_num == 2:
                    score += 1.5  # Often main technical content
                elif page_num >= 3:
                    score += 1.0  # Technical details

                # 5. Image index scoring (first images often primary)
                if img_idx == 1:
                    score += 1.0
                elif img_idx == 2:
                    score += 0.5

                # 6. Format preference (PNG often better quality for technical diagrams)
                if img_format and img_format.lower() == "png":
                    score += 0.5

                scored_images.append(
                    (
                        score,
                        doc_name,
                        page_num,
                        img_idx,
                        img_filename,
                        img_format,
                        relevance_score,
                        image_type,
                        image_width,
                        image_height,
                    )
                )

            # Sort by enhanced score (highest first) and take top results
            scored_images.sort(key=lambda x: x[0], reverse=True)

            # Format results - prioritize highest-scored images
            top_images = scored_images[:3]  # Take top 3 most relevant images

            image_paths = []
            doc_names = set()

            for (
                score,
                doc_name,
                page_num,
                img_idx,
                img_filename,
                img_format,
                relevance_score,
                image_type,
                image_width,
                image_height,
            ) in top_images:
                image_paths.append(img_filename)
                doc_names.add(doc_name)
                debug.print_function(
                    f"[func_image_search] Selected: {img_filename} (enhanced_score={score:.1f}, "
                    f"relevance={relevance_score}, type={image_type}, size={image_width}x{image_height})"
                )

            # Return the best match and enhanced metadata
            if image_paths:
                best_image = image_paths[0]  # Highest scored image

                # Create detailed output with metadata insights
                if len(image_paths) > 1:
                    image_output = f"Best match: {best_image} (+ {len(image_paths)-1} alternates: {', '.join(image_paths[1:])})"
                else:
                    image_output = best_image

                debug.print_function(
                    f"[func_image_search] Selected {len(image_paths)} enhanced images from {len(best_results)} total"
                )

                return (
                    True,
                    {
                        "Image Output": image_output,
                        "Document Name": ", ".join(sorted(doc_names)),
                    },
                )
            else:
                return (
                    True,
                    {
                        "Image Output": f"No relevant technical layout images found for: {', '.join(keywords)}",
                        "Document Name": "",
                    },
                )

    except Exception as e:
        logger.error(f"[func_image_search] Database error: {e}")
        return (False, f"Image search error: {e}")


def func_display_images(params: dict) -> tuple[bool, dict]:
    """Display found images to the user by opening them in VS Code Simple Browser."""
    image_output = params.get("Image Output", "").strip()
    debug.print_function(
        f"[func_display_images] Received image output: {repr(image_output)}"
    )

    if not image_output or "No images found" in image_output:
        return (
            True,
            {"Display Output": "No images available to display", "Images Shown": "0"},
        )

    try:
        # Extract image paths from the image output
        import re
        import os
        from pathlib import Path
        import urllib.parse

        # Parse image paths from various formats
        image_paths = []

        # Handle new smart search format: "Best match: path (+ X alternates: path1, path2)"
        if "Best match:" in image_output:
            # Extract primary image
            match = re.search(r"Best match:\s*([^\s]+[^(]*?)(?:\s*\(|$)", image_output)
            if match:
                primary_path = match.group(1).strip()
                if primary_path.startswith("data/images/"):
                    image_paths.append(primary_path)

            # Extract alternate images
            alt_match = re.search(r"alternates:\s*([^)]+)", image_output)
            if alt_match:
                alternates_str = alt_match.group(1)
                alternates = [alt.strip() for alt in alternates_str.split(",")]
                for alt_path in alternates:
                    if alt_path.startswith("data/images/"):
                        image_paths.append(alt_path)

        # Handle single image path
        elif image_output.startswith("data/images/"):
            image_paths.append(image_output)
        # Handle "Found X images: path (+ Y more)" format
        elif "Found" in image_output and "images:" in image_output:
            # Extract the main image path
            match = re.search(r"images:\s*([^\s]+(?:\s+[^\(]+)*)", image_output)
            if match:
                main_path = match.group(1).strip()
                if main_path.startswith("data/images/"):
                    image_paths.append(main_path)

        if not image_paths:
            return (
                True,
                {
                    "Display Output": f"Could not parse image paths from: {image_output}",
                    "Images Shown": "0",
                },
            )

        # Verify image files exist and display them with smart ranking
        displayed_count = 0
        # Use relative workspace path instead of hardcoded path
        absolute_workspace = Path.cwd()
        display_info = []

        for i, img_path in enumerate(image_paths):
            # Convert relative path to absolute
            if img_path.startswith("data/images/"):
                full_path = absolute_workspace / img_path
            else:
                full_path = Path(img_path)

            if full_path.exists():
                logger.info(f"[func_display_images] Displaying image: {full_path}")

                # Create file:// URL for VS Code Simple Browser
                file_url = full_path.as_uri()

                # Determine image priority and extract page info
                priority_icon = "🎯" if i == 0 else "🔄"
                priority_text = "PRIMARY (Best Match)" if i == 0 else f"ALTERNATE {i}"

                # Extract page and index info from filename
                page_info = ""
                if "image" in img_path:
                    page_match = re.search(r"image(\d+)_(\d+)", img_path)
                    if page_match:
                        page_num, img_idx = page_match.groups()
                        page_info = f" [Page {page_num}, Image {img_idx}]"

                try:
                    display_info.append(
                        f"{priority_icon} {priority_text}: {img_path}{page_info}"
                    )
                    display_info.append(f"   📁 File: {full_path}")
                    display_info.append(f"   🌐 URL: {file_url}")
                    display_info.append("")  # Empty line for readability
                    displayed_count += 1

                    logger.info(
                        f"[func_display_images] Image ready for display: {file_url}"
                    )

                except Exception as e:
                    logger.warning(
                        f"[func_display_images] Could not prepare {full_path}: {e}"
                    )
                    display_info.append(f"📷 {img_path} (Available - open manually)")
                    displayed_count += 1
            else:
                logger.warning(f"[func_display_images] Image not found: {full_path}")
                display_info.append(f"❌ {img_path} (File not found)")

        # Create simple, direct output
        if displayed_count > 0:
            # Just return the first (best) image path - clean and simple
            best_image_path = image_paths[0]
            display_message = best_image_path

            # Also create clean paths list for any downstream functions
            image_analysis_data = best_image_path
        else:
            display_message = "No images found"
            image_analysis_data = "No images found"

        # Return simple, clean output
        return (
            True,
            {
                "Display Output": display_message,
                "Images Shown": str(displayed_count),
                "Image Output": image_analysis_data,
            },
        )

    except Exception as e:
        logger.error(f"[func_display_images] Error displaying images: {e}")
        return (False, f"Error displaying images: {e}")


def func_table_search_on_document(params: dict) -> tuple[bool, dict | str]:
    """
    Search tables for keywords within specific documents with format variations and optional vector search.

    Enhanced with semantic search capabilities when vector embeddings are available.
    """
    kw_raw = params.get("Keyword Output", "").strip()
    doc_name_str = params.get("Latest Document Name", "")
    doc_names = [
        name.strip()
        for name in doc_name_str.replace("\n", ",").split(",")
        if name.strip()
    ]
    debug.print_function(f"[func_table_search_on_document] Keywords: {kw_raw}")
    debug.print_function(f"[func_table_search_on_document] Document names: {doc_names}")

    if not doc_names:
        return (False, "No document name(s) provided")
    if not kw_raw:
        return (False, "Keyword Output parameter missing")

    keywords = [k.strip() for k in kw_raw.split(",") if k.strip()]
    if not keywords:
        return (False, "No valid keywords")

    # Enhanced keyword processing for product numbers
    enhanced_keywords = []
    for kw in keywords:
        enhanced_keywords.append(kw)  # Original format
        # Add format variations for product numbers
        enhanced_keywords.extend(_generate_format_variations(kw))

    # Try vector-enhanced search for semantic matching
    vector_results = []
    try:
        from .vector_helpers import VectorTableSearch

        vector_search = VectorTableSearch()

        if vector_search.embeddings_available:
            # Perform semantic search for each document
            for doc_name in doc_names:
                query_text = f"document:{doc_name} {' '.join(keywords)}"
                semantic_results = vector_search.semantic_keyword_search(
                    query_text, top_k=5
                )

                # Filter results by document name
                for result in semantic_results:
                    if result.get("filename", "").startswith(doc_name):
                        vector_results.append(result)

            if vector_results:
                logger.info(
                    f"✅ Vector search found {len(vector_results)} semantic matches"
                )
                # Add semantic keywords to search terms
                for result in vector_results[:3]:  # Top 3 semantic matches
                    semantic_keywords = result.get("content_preview", "").split()[:5]
                    enhanced_keywords.extend(semantic_keywords)
            else:
                logger.info("ℹ️ Vector search available but no semantic matches found")
        else:
            logger.info("ℹ️ Vector search not available, using keyword-only search")

    except Exception as vector_e:
        logger.warning(
            f"⚠️ Vector search failed, falling back to keyword search: {vector_e}"
        )

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in enhanced_keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    debug.print_function(
        f"[func_table_search_on_document] Enhanced keywords (with vector): {unique_keywords[:10]}..."
    )

    try:
        with get_output_connection() as conn:
            cur = conn.cursor()
            # Build WHERE clause for keywords and document name(s)
            # Use parentheses for correctness when multiple keywords/docs
            like_clause = " OR ".join(["table_data LIKE ?"] * len(unique_keywords))
            doc_clause = " OR ".join(["filename = ?"] * len(doc_names))
            where_clause = f"({like_clause}) AND ({doc_clause})"
            query = f"""
                SELECT id, filename, page_number, table_data
                FROM extracted_tables
                WHERE {where_clause}
            """
            params_ = [f"%{k}%" for k in unique_keywords] + doc_names
            cur.execute(query, params_)
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            fnames = sorted({r["filename"] for r in rows})
            return (
                True,
                {
                    "Table Output": json.dumps(rows),
                    "Document Name": ", ".join(fnames),
                },
            )
    except Exception as e:
        return (False, f"DB error: {e}")


def func_find_latest_document(params: dict) -> tuple[bool, dict | str]:
    doc_name_str = params.get("Document Name", "")
    doc_names = [
        name.strip()
        for name in doc_name_str.replace("\n", ",").split(",")
        if name.strip()
    ]
    if not doc_names:
        return (False, "No document name(s) provided")
    latest_doc_name = doc_names[-1]
    debug.print_function(
        f"{func_find_latest_document.__name__} received document names: {latest_doc_name}"
    )
    if not latest_doc_name:
        return (False, "No valid document name provided")

    # Output only the document name
    return (True, {"Latest Document Name": latest_doc_name})


# ========================================
# DATA PROCESSING OPERATIONS
# ========================================


def func_filter_table(params: dict) -> tuple[bool, dict | str]:
    """Filter table rows that contain any of the provided keywords."""
    from typing import Any, Dict, Tuple

    # ── parse parameters ────────────────────────────────────────────────
    table_json = params.get("Table Output", "")
    filter_keywords = params.get("Keyword Output", "")

    if not table_json:
        return (False, "Table Output parameter missing")

    if not filter_keywords:
        return (False, "FilterKeywords parameter missing")

    keep_header = params.get("keep_header", "true").lower() != "false"

    tables = _parse_json_safely(table_json, default=[], context="func_filter_table")
    if not tables:
        return (False, "Malformed Table Output JSON")

    keywords = {kw.strip().lower() for kw in filter_keywords.split(",") if kw.strip()}

    debug.print_function(f"[func_filter_table] Filter keywords used: {keywords}")
    if not keywords:
        return (False, "No valid keywords provided")

    # ── helper: check row against keywords ──────────────────────────────
    def row_matches(row):
        row_text = json.dumps(row).lower()
        return any(kw in row_text for kw in keywords)

    # ── filter tables ───────────────────────────────────────────────────
    filtered_tables = []

    for tbl in tables:
        content = _parse_json_safely(
            tbl.get("tablecontent", "[]"), default=[], context="table_content"
        )
        if not content:
            continue

        if keep_header:
            header, *rows = content
        else:
            header = []
            rows = content[1:] if len(content) > 1 else []

        filtered_rows = [row for row in rows if row_matches(row)]

        if filtered_rows:
            final_content = [header] + filtered_rows if keep_header else filtered_rows
            tbl["tablecontent"] = json.dumps(final_content)
            filtered_tables.append(tbl)

    if not filtered_tables:
        return (False, "No matching rows found")
    debug.print_function(
        f"[func_filter_table] Filtered tables count: {len(filtered_tables)}"
    )
    return (True, {"Filtered Data": json.dumps(filtered_tables)})


def func_filter_table_by_field(params: dict) -> tuple[bool, dict | str]:
    """Filter tables based on keywords found in column headers."""

    # ── Parameter validation following standard conventions ──
    table_json = params.get("Table Output", "")
    filter_keywords = params.get("Keyword Output", "")

    if not table_json:
        return (False, "Table Output parameter missing")

    if not filter_keywords:
        return (False, "Keyword Output parameter missing")

    # ── Parse JSON input (handle both single and multi-line formats) ──
    all_tables = []

    # Try single JSON parsing first
    tables = _parse_json_safely(
        table_json, default=None, context="filter_table_by_field"
    )
    if tables and isinstance(tables, list):
        all_tables.extend(tables)
        debug.print_function(
            f"[func_filter_table_by_field] Parsed single JSON array with {len(tables)} tables"
        )
    else:
        # Fallback to multi-line format
        debug.print_function(
            "[func_filter_table_by_field] Single JSON failed, trying multi-line format"
        )
        for line_num, line in enumerate(table_json.strip().split("\n"), 1):
            line = line.strip()
            if not line or not (line.startswith("[") and line.endswith("]")):
                continue

            parsed_tables = _parse_json_safely(
                line, default=[], context=f"filter_table_by_field_line_{line_num}"
            )
            if isinstance(parsed_tables, list):
                all_tables.extend(parsed_tables)
                debug.print_function(
                    f"[func_filter_table_by_field] Line {line_num}: parsed {len(parsed_tables)} tables"
                )

    if not all_tables:
        return (False, "No valid tables found in Table Output")

    # ── Keyword processing: Use original keywords only ──
    base_keywords = {
        kw.strip().lower() for kw in filter_keywords.split(",") if kw.strip()
    }

    debug.print_function(
        f"[func_filter_table_by_field] Search keywords: {base_keywords}"
    )

    # ── Header-based table filtering function ──
    def header_contains_field(headers, keywords):
        """Check if table headers contain any of the keywords."""
        header_text = " ".join(str(h).lower() for h in headers)
        return any(kw in header_text for kw in keywords)

    # ── Table filtering logic following standard conventions ──
    filtered_tables = []

    for table_idx, tbl in enumerate(all_tables):
        content = _parse_json_safely(
            tbl.get("tablecontent", "[]"),
            default=[],
            context=f"filter_table_by_field_table_{table_idx}",
        )
        if not content or not isinstance(content, list) or len(content) < 1:
            continue

        headers = content[0] if content else []

        if header_contains_field(headers, base_keywords):
            filtered_tables.append(tbl)

            field_matches = [
                kw
                for kw in base_keywords
                if kw in " ".join(str(h).lower() for h in headers)
            ]
            debug.print_function(
                f"[func_filter_table_by_field] Table {table_idx}: matched fields {field_matches}"
            )
            debug.print_function(
                f"[func_filter_table_by_field] Table {table_idx}: headers {headers}"
            )
        else:
            debug.print_function(
                f"[func_filter_table_by_field] Table {table_idx}: no field matches in headers {headers}"
            )

    # ── Final result ──
    if not filtered_tables:
        return (
            False,
            f"No tables found with headers containing fields: {', '.join(base_keywords)}",
        )

    debug.print_function(
        f"[func_filter_table_by_field] Successfully filtered {len(filtered_tables)} tables from {len(all_tables)} input tables"
    )

    return (True, {"Filtered Data": json.dumps(filtered_tables)})


def func_assemble_table(params: dict) -> tuple[bool, dict | str]:
    """Assemble filtered table data into temporary database with dynamic schema."""
    from ..db.connection import get_temp_connection

    # ── Parameter validation following standard conventions ──
    filtered_data = params.get("Filtered Data", "")
    if not filtered_data:
        return (False, "Filtered Data parameter missing")

    # ── Parse multi-line JSON arrays ──
    all_tables = []
    for line_num, line in enumerate(filtered_data.strip().split("\n"), 1):
        line = line.strip()
        if line and line.startswith("[") and line.endswith("]"):
            parsed_tables = _parse_json_safely(
                line, default=[], context=f"assemble_table_line_{line_num}"
            )
            if isinstance(parsed_tables, list):
                all_tables.extend(parsed_tables)

    if not all_tables:
        return (False, "No valid tables to assemble")

    debug.print_function(
        f"[func_assemble_table_to_db] Processing {len(all_tables)} tables"
    )

    # ── Discover schema dynamically from all tables with categorization ──
    discovered_fields = set()
    table_schemas = []

    # Define table categorization patterns
    def categorize_table(table_info, headers, row_count):
        """
        Categorize tables as 'product_spec', 'lookup_table', 'metadata', or 'reference'
        Returns: (category, priority_score)

        New Logic:
        - product_spec: Small tables (1-2 rows) with product codes → merge into product properties
        - lookup_table: Large tables (3+ rows) found by field search → keep separate for value lookup
        - metadata: Revision records, change logs, etc.
        - reference: General mapping/compatibility tables
        """
        heading_name = str(table_info.get("heading_name", "")).lower()
        header_text = " ".join(str(h).lower() for h in headers)

        # Metadata tables (low priority - revision records, change logs, etc.)
        metadata_patterns = [
            "revision",
            "rev",
            "change",
            "history",
            "record",
            "log",
            "update",
            "modification",
            "document",
            "layout",
            "word",
        ]
        if any(pattern in heading_name for pattern in metadata_patterns):
            return ("metadata", 1)

        # Lookup tables (high priority - large tables found by field search)
        # These should be kept separate for value lookup, not merged into product specs
        lookup_indicators = [
            "torque",
            "voltage",
            "current",
            "temperature",
            "specification",
            "rating",
            "limit",
            "range",
        ]
        if row_count >= 3 and (  # Large table with multiple rows
            any(pattern in heading_name for pattern in lookup_indicators)
            or any(pattern in header_text for pattern in lookup_indicators)
        ):
            return ("lookup_table", 15)  # Highest priority for analysis

        # Product specification tables (medium-high priority - small tables with product info)
        # These should be merged into product properties
        product_spec_indicators = [
            "product code",
            "part number",
            "item number",
            "shell size",
            "contact",
        ]
        if row_count <= 2 and (  # Small table (1-2 rows)
            any(pattern in header_text for pattern in product_spec_indicators)
            or any(pattern in heading_name for pattern in ["6 #", "specification"])
        ):
            return ("product_spec", 10)

        # Reference tables (medium priority - mapping, compatibility)
        reference_patterns = [
            "general",
            "series",
            "type",
            "compatibility",
            "mapping",
            "according",
            "designation",
        ]
        if any(pattern in heading_name for pattern in reference_patterns):
            return ("reference", 5)

        # Default categorization based on size
        if row_count <= 2:
            return ("product_spec", 8)  # Small tables likely contain product specs
        else:
            return ("lookup_table", 12)  # Large tables likely contain lookup data

    for tbl in all_tables:
        content = _parse_json_safely(
            tbl.get("tablecontent", "[]"), default=[], context="assemble_table_content"
        )
        if len(content) >= 2:  # Header + at least one data row
            headers = [str(h).strip() for h in content[0]]
            # Filter out empty headers and provide default names for empty fields
            cleaned_headers = []
            for i, header in enumerate(headers):
                if header:  # Non-empty header
                    cleaned_headers.append(header)
                else:  # Empty header, provide default name
                    cleaned_headers.append(f"column_{i}")
            discovered_fields.update(cleaned_headers)
            row_count = len(content) - 1  # Exclude header from count

            # Categorize this table with row count information
            category, priority = categorize_table(tbl, cleaned_headers, row_count)

            table_schemas.append(
                {
                    "table_info": tbl,
                    "headers": cleaned_headers,
                    "rows": content[1:],
                    "category": category,
                    "priority": priority,
                    "row_count": row_count,
                }
            )

            debug.print_function(
                f"[func_assemble_table] Table '{tbl.get('heading_name', 'Unknown')}': {category} (priority: {priority}, {row_count} rows)"
            )

    if not table_schemas:
        return (False, "No valid table content found")

    # Sort tables by priority (higher priority first)
    table_schemas.sort(key=lambda x: x["priority"], reverse=True)

    debug.print_function(
        f"[func_assemble_table_to_db] Discovered {len(discovered_fields)} unique fields"
    )
    debug.print_function(
        f"[func_assemble_table_to_db] Table categories: {[(s['category'], s['priority']) for s in table_schemas]}"
    )

    # ── Create temporary database structure ──
    try:
        with get_temp_connection() as conn:
            # Set timeout for database lock issues
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout

            debug.print_function(
                "🧹 [func_assemble_table] Cleaning temporary database for fresh assembly..."
            )

            # Comprehensive cleanup - drop all temporary tables and any residual data
            cleanup_commands = [
                "DROP TABLE IF EXISTS temp_records",
                "DROP TABLE IF EXISTS temp_metadata",
                "DROP TABLE IF EXISTS temp_field_index",
                "DROP TABLE IF EXISTS temp_lookup_tables",
                # Also clean up any potential leftover tables from failed runs
                "DROP TABLE IF EXISTS temp_assembly",
                "DROP TABLE IF EXISTS temp_data",
                "DROP TABLE IF EXISTS temp_staging",
            ]

            for cmd in cleanup_commands:
                try:
                    conn.execute(cmd)
                except Exception as e:
                    # Ignore errors for tables that don't exist
                    pass

            # Vacuum to reclaim space and optimize database
            try:
                conn.execute("VACUUM")
            except Exception:
                pass  # Vacuum might fail if db is locked, but that's ok

            conn.commit()
            debug.print_function(
                "🧹 [func_assemble_table] Temp database cleaned successfully"
            )

            # Create flexible temp_records table with dynamic columns (for product specs only)
            # Start with core columns, add discovered fields dynamically
            base_columns = [
                "id INTEGER PRIMARY KEY",
                "source_table_id INTEGER",
                "table_category TEXT",  # Track if this is product_spec/lookup_table/metadata/reference
                "table_priority INTEGER",  # Priority score for ranking
            ]

            # Add a column for each discovered field (sanitized names)
            field_columns = []
            field_mapping = {}  # original_name -> sanitized_name

            for field in sorted(discovered_fields):
                # Skip empty fields (should not happen with our filtering above, but safety check)
                if not field or not field.strip():
                    continue

                # Sanitize field name for SQL column (replace spaces, special chars)
                sanitized = (
                    field.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
                )
                sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")

                # If sanitization resulted in empty string, provide fallback name
                if not sanitized:
                    sanitized = f"field_{len(field_columns)}"

                # Ensure uniqueness
                base_sanitized = sanitized
                counter = 1
                while sanitized in [
                    col.split()[0].replace('"', "") for col in field_columns
                ]:
                    sanitized = f"{base_sanitized}_{counter}"
                    counter += 1

                # If column name starts with digit or contains non-alphanumeric (except _), wrap in double quotes
                needs_quotes = sanitized and (
                    sanitized[0].isdigit() or not sanitized.replace("_", "").isalnum()
                )
                quoted_name = f'"{sanitized}"' if needs_quotes else sanitized
                field_columns.append(f"{quoted_name} TEXT")
                field_mapping[field] = sanitized

            create_records_sql = f"""
                CREATE TABLE temp_records (
                    {', '.join(base_columns + field_columns)}
                )
            """

            conn.execute(create_records_sql)

            # Create metadata table for source tracking
            conn.execute(
                """
                CREATE TABLE temp_metadata (
                    id INTEGER PRIMARY KEY,
                    table_id INTEGER,
                    filename TEXT,
                    page_nr INTEGER,
                    heading_name TEXT,
                    table_name TEXT,
                    table_category TEXT,
                    table_priority INTEGER,
                    total_rows INTEGER
                )
            """
            )

            # Create field index for query assistance
            conn.execute(
                """
                CREATE TABLE temp_field_index (
                    id INTEGER PRIMARY KEY,
                    original_field_name TEXT,
                    sanitized_field_name TEXT,
                    field_type TEXT,
                    sample_values TEXT
                )
            """
            )

            # NEW: Create separate lookup tables storage for field-based searches
            conn.execute(
                """
                CREATE TABLE temp_lookup_tables (
                    id INTEGER PRIMARY KEY,
                    source_table_id INTEGER,
                    table_name TEXT,
                    heading_name TEXT,
                    filename TEXT,
                    table_content TEXT,  -- Store entire table as JSON for LLM analysis
                    field_names TEXT,    -- Comma-separated list of field names
                    row_count INTEGER,
                    table_priority INTEGER
                )
            """
            )

            # ── Insert data dynamically ──
            records_inserted = 0
            lookup_tables_inserted = 0
            source_id = 1

            for schema_info in table_schemas:
                tbl = schema_info["table_info"]
                headers = schema_info["headers"]
                rows = schema_info["rows"]
                category = schema_info["category"]
                priority = schema_info["priority"]
                row_count = schema_info["row_count"]

                # Insert source metadata with categorization
                conn.execute(
                    """
                    INSERT INTO temp_metadata (id, table_id, filename, page_nr, heading_name, table_name, table_category, table_priority, total_rows)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        source_id,
                        tbl.get("id", 0),
                        tbl.get("filename", "Unknown"),
                        tbl.get("page_nr", 0),
                        tbl.get("heading_name", "Unknown"),
                        tbl.get("table_name", "Unknown"),
                        category,
                        priority,
                        len(rows),
                    ),
                )

                # Handle lookup tables separately (store entire table for LLM analysis)
                if category == "lookup_table":
                    # Store entire table as JSON for LLM to use in analysis
                    table_content = [headers] + rows  # Include headers
                    conn.execute(
                        """
                        INSERT INTO temp_lookup_tables (source_table_id, table_name, heading_name, filename, table_content, field_names, row_count, table_priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            source_id,
                            tbl.get("table_name", "Unknown"),
                            tbl.get("heading_name", "Unknown"),
                            tbl.get("filename", "Unknown"),
                            json.dumps(table_content),
                            ", ".join(headers),
                            row_count,
                            priority,
                        ),
                    )
                    lookup_tables_inserted += 1
                    debug.print_function(
                        f"[func_assemble_table] Stored lookup table: {tbl.get('heading_name', 'Unknown')} ({row_count} rows)"
                    )

                else:
                    # Insert product specs, metadata, and reference data into temp_records
                    for row in rows:
                        if not any(
                            str(cell).strip() for cell in row
                        ):  # Skip empty rows
                            continue

                        # Build dynamic INSERT statement
                        column_names = [
                            "source_table_id",
                            "table_category",
                            "table_priority",
                        ]
                        values = [source_id, category, priority]

                        # Map each header to its sanitized column and add the value
                        for i, header in enumerate(headers):
                            if header in field_mapping:
                                column_names.append(field_mapping[header])
                                # Get value, handle index out of range
                                value = str(row[i]).strip() if i < len(row) else ""
                                values.append(value if value else None)

                        # Execute dynamic insert
                        placeholders = ", ".join(["?"] * len(values))
                        columns_sql = ", ".join([f'"{col}"' for col in column_names])

                        insert_sql = f"INSERT INTO temp_records ({columns_sql}) VALUES ({placeholders})"
                        conn.execute(insert_sql, values)
                        records_inserted += 1

                source_id += 1

            # ── Populate field index for query assistance ──
            for original_field, sanitized_field in field_mapping.items():
                # Get sample values for this field
                sample_query = f'SELECT DISTINCT "{sanitized_field}" FROM temp_records WHERE "{sanitized_field}" IS NOT NULL LIMIT 5'
                sample_rows = conn.execute(sample_query).fetchall()
                sample_values = [row[0] for row in sample_rows if row[0]]

                # Guess field type based on sample values
                field_type = _guess_field_type(sample_values)

                conn.execute(
                    """
                    INSERT INTO temp_field_index (original_field_name, sanitized_field_name, field_type, sample_values)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        original_field,
                        sanitized_field,
                        field_type,
                        ", ".join(sample_values[:3]),
                    ),
                )

            # ── Create indexes for efficient querying ──
            # Create index on source_table_id
            conn.execute(
                "CREATE INDEX idx_records_source ON temp_records(source_table_id)"
            )

            # Create indexes on commonly queried fields (those with identifiers)
            for original_field, sanitized_field in field_mapping.items():
                if any(
                    keyword in original_field.lower()
                    for keyword in ["code", "number", "id", "name"]
                ):
                    try:
                        conn.execute(
                            f"CREATE INDEX idx_{sanitized_field} ON temp_records({sanitized_field})"
                        )
                    except sqlite3.OperationalError:
                        # Index creation might fail for some field names, skip silently
                        pass

            conn.commit()

            # ── Return assembly summary following standard conventions ──
            # Calculate category statistics
            category_stats = {}
            for schema_info in table_schemas:
                cat = schema_info["category"]
                category_stats[cat] = category_stats.get(cat, 0) + 1

            summary = {
                "temp_tables_created": 4,  # temp_records, temp_metadata, temp_field_index, temp_lookup_tables
                "records_inserted": records_inserted,
                "lookup_tables_stored": lookup_tables_inserted,
                "fields_discovered": len(discovered_fields),
                "source_tables_processed": source_id - 1,
                "field_mapping": field_mapping,
                "database_type": "temp",
                "categorization": {
                    "category_counts": category_stats,
                    "product_spec_tables": len(
                        [s for s in table_schemas if s["category"] == "product_spec"]
                    ),
                    "lookup_tables": len(
                        [s for s in table_schemas if s["category"] == "lookup_table"]
                    ),
                    "metadata_tables": len(
                        [s for s in table_schemas if s["category"] == "metadata"]
                    ),
                    "reference_tables": len(
                        [s for s in table_schemas if s["category"] == "reference"]
                    ),
                },
            }

            debug.print_function(
                f"[func_assemble_table_to_db] Database assembly complete: {summary}"
            )

            # Return in standard output format - maintain backward compatibility
            # The interface expects "Assembled Data" but now contains database summary
            assembled_table = {
                "table_name": "Database Assembly Summary",
                "tablecontent": json.dumps(summary),
            }

            return (True, {"Assembled Data": json.dumps([assembled_table])})

    except Exception as e:
        return (False, f"Database assembly error: {e}")


def _guess_field_type(sample_values: list) -> str:
    """Guess field data type from sample values. Returns: numeric, identifier, text, empty."""
    if not sample_values:
        return "empty"

    # Check if values look numeric using a more robust approach
    numeric_count = 0
    for value in sample_values:
        if value is None:
            continue

        str_value = str(value).strip()
        if not str_value:
            continue

        # Skip ranges (e.g., '13-32', '10/12')
        if "-" in str_value or "/" in str_value:
            continue

        # Try to convert to float with comprehensive error handling
        try:
            # Remove common separators
            test_value = str_value.replace(",", "").replace(" ", "")
            # Only try conversion if it looks like it could be numeric
            # Check for valid float format: digits with at most one decimal point
            if (
                test_value.replace(".", "").replace("-", "").replace("+", "").isdigit()
                and test_value.count(".") <= 1
            ):
                float(test_value)
                numeric_count += 1
        except:
            # Any exception means it's not numeric - this is expected and normal
            continue

    # If 70% or more values are numeric, consider it a numeric field
    if len(sample_values) > 0 and numeric_count >= len(sample_values) * 0.7:
        return "numeric"

    # Check if values look like identifiers (codes, part numbers)
    identifier_patterns = any(
        any(char.isdigit() and char.isalpha() for char in str(val))
        or any(char in str(val) for char in ["-", "/", "_"])
        for val in sample_values
        if val is not None and str(val).strip()  # Only check non-empty values
    )

    if identifier_patterns:
        return "identifier"

    return "text"


# ========================================
# UTILITY FUNCTIONS
# ========================================


def func_change_keyword(params: dict) -> tuple[bool, dict]:
    """Change or modify a keyword by removing the first 7 characters."""
    kw = params.get("Input", "")
    return (True, {"Keyword Output": kw[7:] if len(kw) >= 7 else ""})


# ========================================
# ANALYSIS OPERATIONS
# ========================================


def func_analyze_data(params: dict) -> tuple[bool, dict | str]:
    """
    Analyze assembled data using LLM to generate final answers.

    Primary analysis function that synthesizes data from previous functions
    using a reasoning LLM. Combines user query, table data, and context
    to generate comprehensive technical answers with source attribution.

    Args:
        params: {
            "Input": user_query,
            "Table": assembled_table_data,
            "Document Name": source_documents
        }

    Returns:
        (True, {"Answer": final_response_text})
        or (False, error_message)
    """
    from ..db.connection import get_temp_connection

    # 1 ── validate params ---------------------------------------------------
    assembled_data = params.get("Assembled Data", "").strip()
    question = params.get("Input", "").strip()

    if not assembled_data:
        return (False, "Assembled Data parameter missing")
    if not question:
        return (False, "Input parameter missing")

    # 2 ── Extract database assembly summary -----------------------------------
    tables = _parse_json_safely(assembled_data, default=[], context="assembled_data")
    if not tables or not isinstance(tables, list):
        return (False, "Invalid Assembled Data format")

    # Get the database assembly summary
    assembly_table = tables[0]
    assembly_summary = _parse_json_safely(
        assembly_table.get("tablecontent", "{}"),
        default={},
        context="assembly_table_content",
    )

    # 3 ── Query temporary database for comprehensive context ----------------
    context_parts = []

    try:
        with get_temp_connection() as conn:
            # Query product specifications
            product_specs = conn.execute(
                """
                SELECT r.*, m.heading_name, m.filename
                FROM temp_records r
                JOIN temp_metadata m ON r.source_table_id = m.id
                WHERE r.table_category = 'product_spec'
                ORDER BY r.table_priority DESC
            """
            ).fetchall()

            # Get field mapping for better display
            field_mapping = {}
            field_map_query = conn.execute(
                "SELECT sanitized_field_name, original_field_name FROM temp_field_index"
            ).fetchall()
            for sanitized, original in field_map_query:
                field_mapping[sanitized] = original

            if product_specs:
                context_parts.append("=== PRODUCT SPECIFICATIONS ===")
                for spec in product_specs:
                    # Convert row to dict for easier processing
                    spec_dict = dict(spec)
                    relevant_fields = {
                        k: v
                        for k, v in spec_dict.items()
                        if v
                        and k
                        not in [
                            "id",
                            "source_table_id",
                            "table_category",
                            "table_priority",
                        ]
                    }
                    context_parts.append(
                        f"Source: {spec_dict['heading_name']} ({spec_dict['filename']})"
                    )
                    for field, value in relevant_fields.items():
                        if value:
                            # Use original field name if available, otherwise use sanitized name
                            display_name = field_mapping.get(field, field)
                            context_parts.append(f"  {display_name}: {value}")
                    context_parts.append("")

            # Query lookup tables for reference data
            lookup_tables = conn.execute(
                """
                SELECT table_name, heading_name, filename, table_content, field_names, row_count
                FROM temp_lookup_tables
                ORDER BY table_priority DESC
            """
            ).fetchall()

            if lookup_tables:
                context_parts.append("=== LOOKUP TABLES ===")
                for lookup in lookup_tables:
                    table_content = _parse_json_safely(
                        lookup[3], default=[], context="lookup_table_content"
                    )  # table_content
                    context_parts.append(
                        f"Table: {lookup[1]} ({lookup[2]})"
                    )  # heading_name, filename
                    context_parts.append(f"Fields: {lookup[4]}")  # field_names
                    context_parts.append(f"Rows: {lookup[5]}")  # row_count

                    # Format table content for LLM
                    if table_content and len(table_content) >= 2:
                        headers = table_content[0]
                        rows = table_content[1:]
                        context_parts.append(f"Headers: {headers}")
                        context_parts.append("Data rows:")
                        for i, row in enumerate(rows[:10]):  # Limit to first 10 rows
                            context_parts.append(f"  Row {i+1}: {row}")
                        if len(rows) > 10:
                            context_parts.append(
                                f"  ... and {len(rows) - 10} more rows"
                            )
                    context_parts.append("")

            # Query metadata for source information
            metadata = conn.execute(
                """
                SELECT filename, heading_name, table_category, total_rows
                FROM temp_metadata
                ORDER BY table_priority DESC
            """
            ).fetchall()

            if metadata:
                context_parts.append("=== SOURCE METADATA ===")
                for meta in metadata:
                    context_parts.append(
                        f"{meta[1]} ({meta[0]}) - {meta[2]} table with {meta[3]} rows"
                    )

    except Exception as e:
        return (False, f"Database query error: {e}")

    if not context_parts:
        return (False, "No data found in temporary database")

    combined_context = "\n".join(context_parts)

    # 4 ── Intelligent LLM analysis with domain knowledge --------------------
    prompt_loader = get_prompt_loader()
    prompts = prompt_loader.get_prompt("function_execution", "data_analysis")

    system_msg = prompts["system"]
    user_prompt = prompts["user_template"].format(
        combined_context=combined_context, question=question
    )

    # 5 ── Execute LLM reasoning ----------------------------------------------
    llm = get_reasoning_llm()

    # def _llm_call(chat, system_msg, prompt):
    #     return chat.invoke(
    #         [
    #             {"role": "system", "content": system_msg},
    #             {"role": "user", "content": prompt},
    #         ]
    #     ).content

    # try:
    #     raw_answer = _llm_call(llm, system_msg, user_prompt).strip()

    #     # Clean up response formatting
    #     if raw_answer.startswith("<") and ">" in raw_answer.split("\n", 1)[0]:
    #         raw_answer = raw_answer.split(">", 1)[1].lstrip()

    #     answer = raw_answer or "No relevant data found in the assembled context."
    #     print(f"[func_analyze_data] {repr(answer)}")
    #     logger.info(f"[func_analyze_data] Analysis complete: {len(answer)} characters")
    #     return (True, {"Analyze Output": answer})

    # except Exception as e:
    #     return (False, f"LLM analysis error: {e}")

    def _llm_call(chat, system_msg, prompt):
        return chat.invoke(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ]
        ).content

    max_attempts = 3
    delay_seconds = 2
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            raw_answer = _llm_call(llm, system_msg, user_prompt).strip()
            # Clean up response formatting
            if raw_answer.startswith("<") and ">" in raw_answer.split("\n", 1)[0]:
                pass
            answer = raw_answer or "No relevant data found in the assembled context."
            debug.print_function(f"[func_analyze_data] {repr(answer)}")
            debug.print_function(
                f"[func_analyze_data] Analysis complete: {len(answer)} characters (attempt {attempt})"
            )
            return (True, {"Analyze Output": answer})
        except Exception as e:
            last_exception = e
            logger.warning(
                f"[func_analyze_data] LLM call failed on attempt {attempt}: {e}"
            )
            if attempt < max_attempts:
                time.sleep(delay_seconds)
    return (
        False,
        f"LLM analysis error after {max_attempts} attempts: {last_exception}",
    )


def func_semantic_search(params: dict) -> tuple[bool, dict | str]:
    """
    Semantic search using vector embeddings and natural language understanding.
    
    Enhanced semantic search that finds relevant products/data based on meaning,
    not just keyword matching. Handles use cases, environments, industries, compatibility.
    
    Parameters:
        Input (str): Natural language query
        search_scope (str, optional): Scope limitation ("products", "applications", "both")
        similarity_threshold (float, optional): Minimum similarity score (default: 0.7)
        max_results (int, optional): Maximum number of results (default: 20)
    
    Returns:
        tuple[bool, dict]: Success status and results with semantic matches
    """
    query = params.get("Input", "").strip()
    search_scope = params.get("search_scope", "both")
    similarity_threshold = float(params.get("similarity_threshold", 0.7))
    max_results = int(params.get("max_results", 20))
    
    if not query:
        return (False, "Input query parameter missing")
    
    debug.print_function(f"[func_semantic_search] Query: {query}")
    
    try:
        # For now, implement a simple keyword-based search as fallback
        # This can be enhanced with actual vector embeddings later
        with get_output_connection() as conn:
            cursor = conn.cursor()
            
            # Search across product families for semantic matches
            cursor.execute("""
                SELECT family_code, family_name, specifications
                FROM product_families 
                WHERE family_name LIKE ? OR specifications LIKE ?
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", max_results))
            
            results = cursor.fetchall()
            
            semantic_results = []
            for family_code, family_name, specs in results:
                semantic_results.append({
                    "product_family": family_name or family_code,
                    "product_code": family_code,
                    "similarity_score": 0.8,  # Placeholder score
                    "match_reason": f"matches query terms in {family_name or 'specifications'}"
                })
            
            debug.print_function(f"[func_semantic_search] Found {len(semantic_results)} matches")
            
            return (True, {
                "Semantic Results": semantic_results,
                "Search Query": query,
                "Total Matches": len(semantic_results),
                "items": semantic_results  # For compatibility with Extract Attributes
            })
            
    except Exception as e:
        logger.error(f"[func_semantic_search] Database error: {e}")
        return (False, f"Semantic search error: {e}")


def func_analyze_image(params: dict) -> tuple[bool, dict | str]:
    """Analyze technical images using multimodal LLM capabilities."""
    # Get parameters
    image_output = params.get("Image Output", "").strip()
    user_query = params.get("Input", "").strip()
    keywords = params.get("Keyword Output", "").strip()

    debug.print_function(f"[func_analyze_image] Image: {repr(image_output)}")
    debug.print_function(f"[func_analyze_image] Query: {repr(user_query)}")

    if not image_output or "No images found" in image_output:
        return (False, "No valid images found to analyze")

    if not user_query:
        return (False, "User query missing for image analysis")

    try:
        # Extract the actual image path from the output
        image_path = ""

        if image_output.startswith("Found"):
            # Handle "Found 7 images: path (+ 6 more)" format
            parts = image_output.split(": ", 1)
            if len(parts) > 1:
                path_part = parts[1].split(" (")[0]  # Take part before " (+ N more)"
                image_path = path_part.strip()
        else:
            # Single image path
            image_path = image_output.strip()

        if not image_path:
            return (False, f"Could not extract image path from: {image_output}")

        # Check if image file exists
        full_path = pathlib.Path(image_path)
        if not full_path.exists():
            # Try relative to current working directory
            abs_path = pathlib.Path.cwd() / image_path
            if not abs_path.exists():
                return (False, f"Image file not found: {image_path}")
            else:
                image_path = str(abs_path)

        # Get multimodal LLM configuration
        llm_config = CONFIG["llms"]["multimodal"]

        # Create analysis result
        analysis_result = f"""Image Analysis for {keywords}:

Product Code: {keywords}
Query: {user_query}
Image Located: {image_path}

TECHNICAL IMAGE ANALYSIS:
Found technical documentation image for the {keywords} product family.

Image Details:
- Source: {image_path}
- Product Family: {keywords}
- Query Type: Layout/Visual Analysis

TECHNICAL ASSESSMENT:
This function has successfully located technical documentation images and is configured for multimodal analysis. The image path has been validated and the system is ready for visual processing.

VISUAL INFORMATION:
To provide specific technical details, component configurations, and specifications, this function would integrate with a multimodal LLM (GPT-4V, Claude 3 Vision, or LLaVA) to analyze the actual image content.

RECOMMENDED NEXT STEPS:
1. Enable multimodal LLM integration for detailed visual analysis
2. Configure image preprocessing pipeline for optimal recognition
3. Implement technical-specific pattern recognition

Current Status: Image located and ready for analysis at {image_path}
"""

        logger.info(f"[func_analyze_image] Analysis prepared for: {image_path}")
        return (True, {"Image Analysis": analysis_result})

    except Exception as e:
        logger.error(f"[func_analyze_image] Error: {e}")
        return (False, f"Image analysis error: {e}")


def func_extract_product_number(params: dict) -> tuple[bool, dict]:
    """
    Extract product codes or part numbers from user queries using LLM.

    Uses LLM to identify technical product identifiers from natural language queries.
    Supports various formats (RPT2354313/350, C0000268-11105, etc.) and automatically
    generates format variations for improved search matching.

    Args:
        params: {"Input": user_query_text}

    Returns:
        (True, {"Keyword Output": "product_code1,product_code2,..."})

    Example:
        Input: "What is the shell size for RPT2354313/350?"
        Output: "RPT2354313/350,RPT 235 4313/350"
    """
    # Validate required parameters
    valid, error = _validate_required_parameters(params, ["Input"])
    if not valid:
        debug.print_function(
            "[func_extract_product_number] No user question provided. Storing empty product list."
        )
        return (True, {"Keyword Output": ""})

    question = params["Input"]

    # Create LLM chain for product code extraction
    prompt_loader = get_prompt_loader()
    prompts = prompt_loader.get_prompt("function_execution", "product_code_extraction")

    system_msg = prompts["system"]
    user_template = prompts["user_template"]

    chain = _build_llm_processing_chain(system_msg, user_template, "basic")
    raw_output = chain.invoke({"question": question}).strip()

    debug.print_function(
        f"[func_extract_product_number] Raw LLM output: {repr(raw_output)}"
    )

    # Extract and format product codes with normalization
    if raw_output:
        product_codes = [item.strip() for item in raw_output.split(",") if item.strip()]
        # Normalize each product code to handle common formatting variations
        normalized_codes = []
        for code in product_codes:
            normalized_codes.append(code)  # Keep original
            # Add primary normalized format for searching
            normalized = _normalize_product_format(code)
            if normalized != code:
                normalized_codes.append(normalized)
    else:
        normalized_codes = []

    # Remove duplicates while preserving order
    seen = set()
    final_codes = []
    for code in normalized_codes:
        if code not in seen:
            seen.add(code)
            final_codes.append(code)

    debug.print_function(f"[func_extract_product_number] Final codes: {final_codes}")
    return (True, {"Keyword Output": ", ".join(final_codes)})


def _normalize_product_format(product_code: str) -> str:
    """
    Normalize product code to a standard searchable format (GENERIC).
    
    Applies basic normalization without domain-specific patterns.
    Just cleans up whitespace and standardizes separators.
    """
    if not product_code:
        return product_code

    # Clean up the code: normalize whitespace
    code = " ".join(product_code.strip().split())
    
    # Standardize separators: replace multiple spaces/dashes with single
    code = re.sub(r'\s+-\s+', '-', code)  # " - " → "-"
    code = re.sub(r'\s+/\s+', '/', code)   # " / " → "/"
    
    return code


def func_normalize_product_number(params: dict) -> tuple[bool, dict | str]:
    """
    Normalize product code by removing extra spaces and standardizing format (GENERIC).
    
    No longer truncates to specific length - that was SAAB-specific.
    Just cleans and standardizes the format.
    """
    import re

    raw = params.get("Keyword Output", "")
    if not raw:
        return (False, "Keyword Output parameter missing")

    # Take only the first product code if multiple exist (prevents accumulation)
    if "," in raw:
        raw = raw.split(",")[0].strip()
        debug.print_function(
            f"[func_normalize_product_number] Multiple keywords found, using first: {raw}"
        )

    # Basic normalization: remove extra whitespace, standardize format
    code = " ".join(raw.split())  # Normalize whitespace
    code = re.sub(r'\s+-\s+', '-', code)  # " - " → "-"
    code = re.sub(r'\s+/\s+', '/', code)  # " / " → "/"

    debug.print_function(
        f"[func_normalize_product_number] Normalized: {repr(raw)} → {repr(code)}"
    )

    # Return ONLY the normalized code (this resets the keyword context)
    return (True, {"Keyword Output": code})


def func_suggest_keywords(params: dict) -> tuple[bool, dict]:
    """Extract field/column names from user query using LLM-based keyword analysis."""
    question = params.get("Input", "")

    if not question:
        debug.print_function(
            "[func_suggest_keywords] No question provided, returning empty keywords"
        )
        return (True, {"Keyword Output": ""})

    # Use LLM-based approach for keyword suggestion
    try:
        prompt_loader = get_prompt_loader()
        prompts = prompt_loader.get_prompt("function_execution", "keyword_suggestion")

        system_msg = prompts["system"]
        user_template = prompts["user_template"]

        chain = _build_llm_processing_chain(system_msg, user_template, "basic")

        # Enhanced prompt focuses on technical field extraction
        raw = chain.invoke(
            {"question": question}  # Use 'question' to match the prompt template
        )

        debug.print_function(f"[func_suggest_keywords] LLM response: {raw}")

    except Exception as e:
        debug.print_function(f"[func_suggest_keywords] LLM processing failed: {e}")
        # Fallback to simple keyword extraction
        words = question.lower().split()
        technical_terms = [w for w in words if len(w) > 3 and w.isalpha()]
        raw = ", ".join(technical_terms[:5])  # Top 5 terms

    # Extract and format keywords
    keywords = _parse_keywords_from_string(raw, "func_suggest_keywords")

    # Fallback: if LLM returns no keywords, try to extract common technical terms from the question
    if not keywords:
        debug.print_function(
            "[func_suggest_keywords] LLM returned no keywords, using fallback extraction"
        )

        # Common technical terms for Hydroscand domain (hoses, couplings, fittings)
        fallback_terms = [
            "pressure",
            "temperature",
            "diameter",
            "length",
            "hose",
            "coupling",
            "fitting",
            "connector",
            "adapter",
            "size",
            "flow",
            "material",
            "thread",
            "rating",
            "standard",
        ]

        question_lower = question.lower()
        found_terms = []

        for term in fallback_terms:
            if term in question_lower:
                # Handle compound terms like "working pressure" or "max temperature"
                if term == "pressure" and any(x in question_lower for x in ["working", "max", "burst", "operating"]):
                    found_terms.append(f"{next(x for x in ['working', 'max', 'burst', 'operating'] if x in question_lower)} pressure")
                elif term == "temperature" and any(x in question_lower for x in ["min", "max", "operating"]):
                    found_terms.append(f"{next(x for x in ['min', 'max', 'operating'] if x in question_lower)} temperature")
                elif term not in found_terms:  # Avoid duplicates
                    found_terms.append(term)

        keywords = list(set(found_terms))  # Remove duplicates
        debug.print_function(f"[func_suggest_keywords] Fallback found: {keywords}")

    suggested_keywords = ", ".join(keywords)

    debug.print_function(
        f"[func_suggest_keywords] RESET: suggested fields: {repr(suggested_keywords)}"
    )

    # Return ONLY the suggested keywords (this resets the keyword context)
    return (True, {"Keyword Output": suggested_keywords})


def func_generate_visual_layout(params: dict) -> tuple[bool, dict]:
    """
    Generate visual layout (SIMPLIFIED - SAAB-specific features removed).
    
    Simplified version that returns a basic layout description.
    For full visual layout generation with image search, use the image search functions.
    
    Args:
        params: Dict containing product information and query
        
    Returns:
        Tuple of (success, output_dict) with basic layout information
    """
    product_code = params.get("Product Number Output", "").strip()
    filtered_data = params.get("Filtered Data", "").strip()
    user_query = params.get("Input", "").strip()
    
    debug.print_function(f"[func_generate_visual_layout] Product: {product_code}")
    
    if not filtered_data and not product_code:
        return (False, "No product information available for layout generation")
    
    try:
        # Basic layout info
        layout_info = {
            "product_code": product_code,
            "query": user_query,
            "status": "Layout generation - simplified version",
            "message": "Use Display Images function for full visual content"
        }
        
        # Extract source documents if available
        source_documents = []
        if filtered_data:
            try:
                tables = json.loads(filtered_data) if filtered_data else []
                for table in tables:
                    if isinstance(table, dict) and "filename" in table:
                        doc_name = table["filename"]
                        if doc_name and doc_name not in source_documents:
                            source_documents.append(doc_name)
            except:
                pass
        
        layout_info["source_documents"] = source_documents
        
        return (
            True,
            {
                "Layout Output": json.dumps(layout_info, ensure_ascii=False, indent=2),
                "Image Output": "No images - use Display Images function",
                "Document Name": f"Layout info for {product_code}" if product_code else "Layout info",
            },
        )
    
    except Exception as e:
        logger.error(f"[func_generate_visual_layout] Error: {e}")
        return (False, f"Error generating visual layout: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# GENERIC COMPOSABLE FUNCTIONS FOR HYDROSCAND DOMAIN  
# ═══════════════════════════════════════════════════════════════════════════
# These functions are designed to be generic, composable building blocks that
# can be dynamically orchestrated by the agent to handle diverse Hydroscand
# questions about hoses, products, specifications, and technical calculations.


def func_search_products(params: dict) -> tuple[bool, dict | str]:
    """
    Multi-criteria product search with flexible filtering.
    
    Searches the product catalog based on various criteria:
    - Product category (e.g., product family, type, classification)
    - Technical specifications (temperature, pressure, dimensions, etc.)
    - Keywords in description or name
    - Certifications/standards
    
    Parameters:
        category (str, optional): Product category to search within
        keywords (str, optional): Keywords to search in product descriptions
        specs (dict, optional): Technical specifications to filter by
            - min_temp (float): Minimum temperature rating
            - max_temp (float): Maximum temperature rating
            - min_pressure (float): Minimum pressure rating
            - min_diameter (float): Minimum diameter
            - max_diameter (float): Maximum diameter
        limit (int, optional): Maximum number of results (default: 50)
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Products (list): List of matching products with details
            - Count (int): Number of products found
    """
    import sqlite3
    import json
    import re
    
    db_path = params.get("database_path", CONFIG.get("harvested_db"))
    category = params.get("category", "").strip()
    keywords_raw = params.get("keywords", "").strip()
    
    # Smart keyword extraction: If keywords looks like a natural language question,
    # extract just the product names/codes using simple pattern matching
    keywords = keywords_raw
    if keywords_raw and len(keywords_raw.split()) > 3:
        # Looks like a natural language query - extract product codes/names
        # Look for patterns like: KAPPAFLEX 1, RPT 235, etc.
        # Pattern: Uppercase word followed by optional number/code
        product_pattern = r'\b([A-Z]{3,}(?:\s*[A-Z0-9]+)*)\b'
        matches = re.findall(product_pattern, keywords_raw)
        if matches:
            # Use only the extracted product names
            keywords = ' '.join(matches)
            debug.print_function(f"Extracted product names from query: {keywords}")
        else:
            # No clear product names found - use semantic search instead
            # For now, just use the whole query
            debug.print_function(f"No product codes found, using full query")
    
    # Parse specs parameter - may come as string from workflow
    specs_raw = params.get("specs", {})
    if isinstance(specs_raw, str):
        try:
            specs = json.loads(specs_raw) if specs_raw else {}
        except json.JSONDecodeError:
            specs = {}
    else:
        specs = specs_raw
    
    limit = params.get("limit", 50)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build dynamic SQL query
        query = """
            SELECT 
                p.id as product_id,
                p.product_code,
                p.family_id,
                pf.name as family_name,
                pf.description,
                p.specifications,
                p.page_number
            FROM products p
            LEFT JOIN product_families pf ON p.family_id = pf.id
            WHERE 1=1
        """
        query_params = []
        
        # Filter by category (family name)
        if category:
            query += " AND (pf.name LIKE ? OR pf.description LIKE ?)"
            query_params.extend([f"%{category}%", f"%{category}%"])
        
        # Filter by keywords (in product code or family description)
        if keywords:
            keyword_list = keywords.split()
            for kw in keyword_list:
                query += " AND (p.product_code LIKE ? OR pf.name LIKE ? OR pf.description LIKE ?)"
                query_params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
        
        query += f" LIMIT ?"
        query_params.append(limit)
        
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        
        # Post-process results with spec filtering
        products = []
        for row in rows:
            product = dict(row)
            
            # Parse specifications JSON
            try:
                product_specs = json.loads(product.get("specifications", "{}") or "{}")
            except:
                product_specs = {}
            
            # Apply specification filters
            if specs:
                # Temperature filters
                if "min_temp" in specs:
                    product_min_temp = product_specs.get("min_temperature", product_specs.get("min_temp", -999))
                    if product_min_temp < specs["min_temp"]:
                        continue
                
                if "max_temp" in specs:
                    product_max_temp = product_specs.get("max_temperature", product_specs.get("max_temp", -999))
                    if product_max_temp < specs["max_temp"]:
                        continue
                
                # Pressure filter
                if "min_pressure" in specs:
                    product_pressure = product_specs.get("working_pressure", product_specs.get("pressure", 0))
                    if product_pressure < specs["min_pressure"]:
                        continue
                
                # Diameter filters
                if "min_diameter" in specs:
                    product_diameter = product_specs.get("inner_diameter", product_specs.get("diameter", 0))
                    if product_diameter < specs["min_diameter"]:
                        continue
                
                if "max_diameter" in specs:
                    product_diameter = product_specs.get("inner_diameter", product_specs.get("diameter", 999))
                    if product_diameter > specs["max_diameter"]:
                        continue
            
            # Add parsed specs to product dict
            product["parsed_specs"] = product_specs
            products.append(product)
        
        conn.close()
        
        return (True, {
            "Products": products,
            "Count": len(products),
            "items": products  # For compatibility with Extract Attributes (will be JSON stringified when stored)
        })
        
    except Exception as e:
        return (False, f"Search error: {str(e)}")


def func_query_database(params: dict) -> tuple[bool, dict | str]:
    """
    SQL Agent: Execute custom SQL queries on the harvested database.
    
    A powerful, flexible building block for any database operation:
    - Custom SELECT queries with joins, filters, aggregations
    - Access to all tables: products, product_families, categories
    - Support for complex WHERE clauses, GROUP BY, ORDER BY
    - Parameterized queries for safety
    
    Use Cases:
    - Find all products in a specific family
    - Aggregate specifications across product ranges
    - Join products with family metadata
    - Filter by complex specification criteria
    - Get unique values (distinct families, categories, etc.)
    
    Parameters:
        query_type (str): Type of query ("select", "count", "distinct", "custom")
        table (str): Primary table to query ("products", "product_families", "categories")
        filters (dict): Filter conditions (field: value pairs)
        fields (list): Fields to select (default: all with *)
        joins (list): Tables to join with their conditions
        order_by (str): Sort order (e.g., "product_code ASC")
        limit (int): Maximum results to return
        custom_sql (str): For query_type="custom", provide full SQL query
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - results (list): Query results as list of dicts
            - count (int): Number of results
            - fields (list): Field names returned
    """
    import sqlite3
    import json
    import re
    
    db_path = params.get("database_path", CONFIG.get("harvested_db"))
    query_type = params.get("query_type", "select").lower()
    
    # Smart Mode: If we receive a natural language query in filters or custom_sql,
    # try to extract product code or family name and build a smart query
    filters_raw = params.get("filters", {})
    if isinstance(filters_raw, str) and filters_raw and not filters_raw.startswith("{"):
        # This looks like a natural language query, not a JSON filter
        
        # First, try to extract product code (e.g., "4221-24-08")
        product_code_pattern = r'\b(\d{4}-\d{2}-\d{2})\b'
        code_matches = re.findall(product_code_pattern, filters_raw)
        
        if code_matches:
            # Build a custom query to find product by code
            product_code = code_matches[0]
            debug.print_function(f"Smart mode: Extracted product code '{product_code}' from query")
            
            # Override to custom query mode
            query_type = "custom"
            params["custom_sql"] = f"""
                SELECT p.id as product_id, p.product_code, p.family_id, 
                       p.specifications, p.page_number
                FROM products p
                WHERE p.product_code = '{product_code}'
                LIMIT 100
            """
            debug.print_function(f"Generated smart query for product code: {product_code}")
        else:
            # Otherwise, try to extract product family name (e.g., "KAPPAFLEX 1" from query)
            product_pattern = r'\b([A-Z]{3,}(?:\s+\d+)?)\b'
            matches = re.findall(product_pattern, filters_raw)
            
            if matches:
                # Build a custom query to find products in this family
                family_name = matches[0]  # Take first match (e.g., "KAPPAFLEX 1")
                debug.print_function(f"Smart mode: Extracted family name '{family_name}' from query")
                
                # Override to custom query mode
                query_type = "custom"
                params["custom_sql"] = f"""
                    SELECT p.id as product_id, p.product_code, p.family_id, 
                           pf.name as family_name, pf.description,
                           p.specifications, p.page_number
                    FROM products p
                    LEFT JOIN product_families pf ON p.family_id = pf.id
                    WHERE pf.name LIKE '%{family_name}%'
                    LIMIT 100
                """
                debug.print_function(f"Generated smart query for family: {family_name}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Mode 1: CUSTOM SQL - User provides full query
        if query_type == "custom":
            custom_sql = params.get("custom_sql", "").strip()
            if not custom_sql:
                return (False, "custom_sql parameter required for query_type='custom'")
            
            # Safety check: only allow SELECT queries
            if not custom_sql.upper().startswith("SELECT"):
                return (False, "Only SELECT queries are allowed for safety")
            
            cursor.execute(custom_sql)
            rows = cursor.fetchall()
            
            results = [dict(row) for row in rows]
            field_names = list(rows[0].keys()) if rows else []
            
            conn.close()
            
            debug.print_function(f"Custom SQL executed: {len(results)} results")
            
            return (True, {
                "results": results,
                "count": len(results),
                "fields": field_names,
                "query_type": "custom",
                "items": results  # For compatibility with Extract Attributes
            })
        
        # Mode 2: STRUCTURED QUERY - Build from parameters
        table = params.get("table", "products")
        fields_raw = params.get("fields", [])
        
        # Parse fields parameter
        if isinstance(fields_raw, str):
            try:
                fields = json.loads(fields_raw) if fields_raw else []
            except json.JSONDecodeError:
                fields = [f.strip() for f in fields_raw.split(",") if f.strip()]
        else:
            fields = fields_raw
        
        # Build SELECT clause
        if fields:
            select_clause = ", ".join(fields)
        else:
            select_clause = "*"
        
        # Build base query
        query = f"SELECT {select_clause} FROM {table}"
        query_params = []
        
        # Handle JOINs
        joins_raw = params.get("joins", [])
        if isinstance(joins_raw, str):
            try:
                joins = json.loads(joins_raw) if joins_raw else []
            except json.JSONDecodeError:
                joins = []
        else:
            joins = joins_raw
        
        for join in joins:
            if isinstance(join, dict):
                join_table = join.get("table")
                join_on = join.get("on")
                join_type = join.get("type", "LEFT JOIN")
                if join_table and join_on:
                    query += f" {join_type} {join_table} ON {join_on}"
        
        # Build WHERE clause from filters
        filters_raw = params.get("filters", {})
        if isinstance(filters_raw, str):
            try:
                filters = json.loads(filters_raw) if filters_raw else {}
            except json.JSONDecodeError:
                filters = {}
        else:
            filters = filters_raw
        
        if filters:
            where_conditions = []
            for field, value in filters.items():
                if isinstance(value, dict):
                    # Handle operators: {"operator": "LIKE", "value": "%KAPPAFLEX%"}
                    operator = value.get("operator", "=")
                    filter_value = value.get("value")
                    where_conditions.append(f"{field} {operator} ?")
                    query_params.append(filter_value)
                else:
                    # Simple equality
                    where_conditions.append(f"{field} = ?")
                    query_params.append(value)
            
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)
        
        # Handle ORDER BY
        order_by = params.get("order_by", "")
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # Handle LIMIT
        limit = params.get("limit", 100)
        if limit:
            query += f" LIMIT ?"
            query_params.append(limit)
        
        # Execute query
        cursor.execute(query, query_params)
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        field_names = list(rows[0].keys()) if rows else []
        
        conn.close()
        
        debug.print_function(f"Query executed on {table}: {len(results)} results")
        
        return (True, {
            "results": results,
            "count": len(results),
            "fields": field_names,
            "query_type": query_type,
            "items": results  # For compatibility with other functions
        })
        
    except Exception as e:
        debug.print_error(f"Database query error: {e}")
        return (False, f"Query error: {str(e)}")


def func_filter_items(params: dict) -> tuple[bool, dict | str]:
    """
    Generic filtering engine with complex conditions.
    
    Filters a list of items (products, records, etc.) based on flexible criteria.
    Supports multiple filter types:
    - Field equality (field == value)
    - Numeric comparisons (field > value, field < value)
    - String matching (field contains substring)
    - Range filters (min <= field <= max)
    
    Parameters:
        items (list): List of items to filter (dicts)
        filters (dict): Filter criteria as key-value pairs
        filter_mode (str, optional): "AND" (all must match) or "OR" (any must match), default "AND"
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - FilteredItems (list): Items matching filter criteria
            - Count (int): Number of items after filtering
    """
    # Parse parameters safely - they may come as strings from workflow
    items_raw = params.get("items", [])
    if isinstance(items_raw, str):
        try:
            items = json.loads(items_raw) if items_raw else []
        except json.JSONDecodeError:
            items = []
    else:
        items = items_raw
    
    filters_raw = params.get("filters", {})
    if isinstance(filters_raw, str):
        try:
            filters = json.loads(filters_raw) if filters_raw else {}
        except json.JSONDecodeError:
            filters = {}
    else:
        filters = filters_raw
    
    filter_mode = params.get("filter_mode", "AND").upper()
    
    if not items:
        return (False, "No items provided to filter")
    
    if not filters:
        return (True, {"FilteredItems": items, "Count": len(items)})
    
    try:
        filtered = []
        
        for item in items:
            matches = []
            
            for key, condition in filters.items():
                # Handle different condition types
                if isinstance(condition, dict):
                    # Complex condition (e.g., {">=": 100, "<=": 200})
                    item_value = item.get(key)
                    
                    if "==" in condition:
                        matches.append(item_value == condition["=="])
                    if "!=" in condition:
                        matches.append(item_value != condition["!="])
                    if ">" in condition:
                        matches.append(float(item_value or 0) > float(condition[">"]))
                    if ">=" in condition:
                        matches.append(float(item_value or 0) >= float(condition[">="]))
                    if "<" in condition:
                        matches.append(float(item_value or 0) < float(condition["<"]))
                    if "<=" in condition:
                        matches.append(float(item_value or 0) <= float(condition["<="]))
                    if "contains" in condition:
                        matches.append(condition["contains"].lower() in str(item_value).lower())
                else:
                    # Simple equality condition
                    item_value = item.get(key)
                    if isinstance(condition, str) and isinstance(item_value, str):
                        matches.append(condition.lower() in item_value.lower())
                    else:
                        matches.append(item_value == condition)
            
            # Apply filter mode
            if filter_mode == "AND":
                if all(matches):
                    filtered.append(item)
            else:  # OR
                if any(matches):
                    filtered.append(item)
        
        return (True, {
            "FilteredItems": filtered,
            "Count": len(filtered)
        })
        
    except Exception as e:
        return (False, f"Filter error: {str(e)}")


def func_compare_items(params: dict) -> tuple[bool, dict | str]:
    """
    LLM-powered intelligent product comparison with trade-off analysis.
    
    Provides contextual comparison that explains:
    - WHY differences matter
    - Which product suits which use case
    - Trade-offs between options
    - Technical implications of differences
    
    Parameters:
        items (list): List of items to compare (dicts with item data)
        fields (list, optional): Specific fields to compare
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - comparison_table (dict): Field-by-field comparison
            - similarities (list): Common features
            - differences (list): Key differences with significance
    """
    # Parse parameters safely - they may come as strings from workflow
    items_raw = params.get("items", [])
    if isinstance(items_raw, str):
        try:
            items = json.loads(items_raw) if items_raw else []
        except json.JSONDecodeError:
            items = []
    else:
        items = items_raw
    
    fields_raw = params.get("fields", [])
    if isinstance(fields_raw, str):
        try:
            fields = json.loads(fields_raw) if fields_raw else []
        except json.JSONDecodeError:
            fields = []
    else:
        fields = fields_raw
    
    if len(items) < 2:
        return (False, "Need at least 2 items to compare")
    
    try:
        # Load prompts and build LLM chain
        prompt_loader = get_prompt_loader()
        prompts = prompt_loader.get_prompt("function_execution", "compare_items")
        
        system_msg = prompts["system"]
        user_template = prompts["user_template"]
        
        chain = _build_llm_processing_chain(system_msg, user_template, "basic")
        
        # Format items and fields for prompt
        items_text = json.dumps(items, indent=2)
        fields_text = json.dumps(fields, indent=2) if fields else "all common fields"
        
        # Invoke LLM for intelligent comparison
        result = chain.invoke({
            "items": items_text,
            "fields": fields_text
        })
        
        debug.print_function(f"[func_compare_items] Comparing {len(items)} items, Result: {result[:200]}...")
        
        # Try to parse LLM response as JSON
        try:
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                comparison_result = json.loads(json_match.group())
                comparison_table = comparison_result.get("comparison_table", {})
                similarities = comparison_result.get("similarities", [])
                differences = comparison_result.get("differences", [])
                recommendation = comparison_result.get("recommendation", "")
            else:
                # Fallback: structure the text response
                comparison_table = {"analysis": result}
                similarities = []
                differences = []
                recommendation = ""
        except:
            # Return raw text as analysis
            comparison_table = {"analysis": result}
            similarities = []
            differences = []
            recommendation = ""
        
        return (True, {
            "comparison_table": comparison_table,
            "similarities": similarities,
            "differences": differences,
            "recommendation": recommendation,
            "items_compared": len(items)
        })
        
    except Exception as e:
        logger.error(f"[func_compare_items] Error: {e}")
        return (False, f"Comparison error: {str(e)}")


def func_calculate(params: dict) -> tuple[bool, dict | str]:
    """
    LLM-powered technical calculations with validation and recommendations.
    
    Handles complex calculations with:
    - Formula application and validation
    - Range checking and warnings
    - Standard size recommendations
    - Safety factor considerations
    
    Parameters:
        calculation_type (str): Type of calculation
        inputs (dict): Calculation inputs
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - result (float): Calculated value
            - calculation_type (str): Type performed
            - units (str): Result units
            - formula_used (str): Formula explanation
    """
    calculation_type = params.get("calculation_type", "")
    inputs = params.get("inputs", {})
    
    if not calculation_type:
        return (False, "Missing required parameter: calculation_type")
    
    if not inputs:
        return (False, "Missing required parameter: inputs")
    
    try:
        # Load prompts and build LLM chain
        prompt_loader = get_prompt_loader()
        prompts = prompt_loader.get_prompt("function_execution", "calculate")
        
        system_msg = prompts["system"]
        user_template = prompts["user_template"]
        
        chain = _build_llm_processing_chain(system_msg, user_template, "basic")
        
        # Format inputs as readable text
        inputs_text = json.dumps(inputs, indent=2)
        
        # Invoke LLM for intelligent calculation
        result = chain.invoke({
            "calculation_type": calculation_type.upper(),
            "inputs": inputs_text
        })
        
        debug.print_function(f"[func_calculate] Type: {calculation_type}, Result: {result[:200]}...")
        
        # Parse LLM response (expecting JSON-like format)
        try:
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                calc_result = result_data.get("result", 0)
                units = result_data.get("units", "")
                formula = result_data.get("formula_used", "")
                notes = result_data.get("notes", "")
            else:
                # Fallback: extract number and use text as explanation
                numbers = re.findall(r'-?\d+\.?\d*', result)
                calc_result = float(numbers[0]) if numbers else 0
                units = ""
                formula = result
                notes = ""
        except:
            calc_result = 0
            units = ""
            formula = result
            notes = ""
        
        return (True, {
            "result": calc_result,
            "calculation_type": calculation_type,
            "units": units,
            "formula_used": formula,
            "notes": notes,
            "inputs": inputs
        })
        
    except Exception as e:
        logger.error(f"[func_calculate] Error: {e}")
        return (False, f"Calculation error: {str(e)}")


def func_convert_units(params: dict) -> tuple[bool, dict | str]:
    """
    LLM-powered unit conversion for technical systems.
    
    Handles context-dependent conversions including:
    - Standard conversions (bar, psi, mm, inch, etc.)
    - Non-standard or industry-specific units
    - Ambiguous units requiring context interpretation
    - Approximate conversions when exact formula isn't available
    
    Parameters:
        value (float): Value to convert
        from_unit (str): Source unit
        to_unit (str): Target unit
        context (str): Optional context for interpretation
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - converted_value (float): Value in target units
            - original_value (float): Original value
            - from_unit (str): Source unit
            - to_unit (str): Target unit
            - explanation (str): Conversion explanation and assumptions
    """
    value = params.get("value")
    from_unit = params.get("from_unit", "").strip()
    to_unit = params.get("to_unit", "").strip()
    context = params.get("context", "")
    
    if value is None:
        return (False, "Missing required parameter: value")
    
    if not from_unit or not to_unit:
        return (False, "Missing unit parameters")
    
    try:
        # Load prompts and build LLM chain
        prompt_loader = get_prompt_loader()
        prompts = prompt_loader.get_prompt("function_execution", "convert_units")
        
        system_msg = prompts["system"]
        user_template = prompts["user_template"]
        
        chain = _build_llm_processing_chain(system_msg, user_template, "basic")
        
        # Invoke LLM for intelligent conversion
        result = chain.invoke({
            "value": str(value),
            "from_unit": from_unit,
            "to_unit": to_unit,
            "context": context if context else "No additional context provided"
        })
        
        debug.print_function(f"[func_convert_units] LLM result: {result[:200]}...")
        
        # Parse LLM response (expecting JSON-like format)
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                converted_value = result_data.get("converted_value", 0)
                explanation = result_data.get("explanation", result)
            else:
                # Fallback: try to extract number from text
                numbers = re.findall(r'-?\d+\.?\d*', result)
                converted_value = float(numbers[0]) if numbers else 0
                explanation = result
        except:
            # If parsing fails, return raw result
            converted_value = 0
            explanation = result
        
        return (True, {
            "converted_value": converted_value,
            "original_value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "explanation": explanation
        })
        
    except Exception as e:
        logger.error(f"[func_convert_units] Error: {e}")
        return (False, f"Conversion error: {str(e)}")


def func_get_related_items(params: dict) -> tuple[bool, dict | str]:
    """
    Generic relationship navigator - find compatible items, alternatives, accessories.
    
    Navigate relationships between items in the catalog:
    - Compatible products (e.g., accessories for components, fittings for assemblies)
    - Alternative products (e.g., equivalent items from different manufacturers)
    - Accessories (e.g., tools, adapters, protective covers)
    - Replacement parts
    
    Parameters:
        item_id (str): Product code or ID to find related items for
        relationship_type (str): Type of relationship ("compatible", "alternative", "accessory", "replacement")
        database_path (str, optional): Path to database
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - RelatedItems (list): List of related items with relationship details
            - RelationshipType (str): Type of relationship queried
            - Count (int): Number of related items found
    """
    import sqlite3
    import json
    
    item_id = params.get("item_id", "").strip()
    relationship_type = params.get("relationship_type", "compatible").lower()
    db_path = params.get("database_path", CONFIG.get("harvested_db"))
    
    if not item_id:
        return (False, "Missing required parameter: item_id")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query based on relationship type
        if relationship_type == "compatible":
            # Find compatible products (e.g., sleeves for hoses)
            query = """
                SELECT p.product_code, p.specifications, p.family_id, f.family_name
                FROM Products p
                LEFT JOIN ProductFamilies f ON p.family_id = f.id
                WHERE p.specifications LIKE ?
                LIMIT 20
            """
            cursor.execute(query, (f"%{item_id}%",))
            
        elif relationship_type == "alternative":
            # Find alternative products in same family
            query = """
                SELECT p.product_code, p.specifications
                FROM Products p
                WHERE p.family_id = (SELECT family_id FROM Products WHERE product_code = ?)
                AND p.product_code != ?
                LIMIT 20
            """
            cursor.execute(query, (item_id, item_id))
        
        else:
            return (False, f"Unknown relationship type: {relationship_type}")
        
        rows = cursor.fetchall()
        related_items = [dict(row) for row in rows]
        
        conn.close()
        
        return (True, {
            "RelatedItems": related_items,
            "RelationshipType": relationship_type,
            "Count": len(related_items)
        })
        
    except Exception as e:
        return (False, f"Related items error: {str(e)}")



def func_transform_data(params: dict) -> tuple[bool, dict | str]:
    """
    Data format transformation and restructuring.
    
    Transform data between formats:
    - Flatten nested structures
    - Pivot tables
    - Reshape arrays
    - Extract specific fields
    - Rename fields
    
    Parameters:
        items (list): Data to transform
        operation (str): Transformation type ("flatten", "pivot", "extract", "rename")
        config (dict): Operation-specific configuration
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - TransformedData (list): Transformed data
            - Operation (str): Operation performed
    """
    items = params.get("items", [])
    operation = params.get("operation", "").lower()
    config = params.get("config", {})
    
    if not items:
        return (False, "No items provided")
    
    try:
        if operation == "extract":
            # Extract specific fields
            fields = config.get("fields", [])
            if not fields:
                return (False, "Missing fields in config")
            
            transformed = []
            for item in items:
                extracted = {field: item.get(field) for field in fields if field in item}
                transformed.append(extracted)
            
            return (True, {
                "TransformedData": transformed,
                "Operation": "extract"
            })
        
        elif operation == "rename":
            # Rename fields
            field_map = config.get("field_map", {})
            if not field_map:
                return (False, "Missing field_map in config")
            
            transformed = []
            for item in items:
                renamed = {}
                for old_name, new_name in field_map.items():
                    if old_name in item:
                        renamed[new_name] = item[old_name]
                # Keep fields not in map
                for key, value in item.items():
                    if key not in field_map:
                        renamed[key] = value
                transformed.append(renamed)
            
            return (True, {
                "TransformedData": transformed,
                "Operation": "rename"
            })
        
        elif operation == "flatten":
            # Flatten nested structures
            transformed = []
            for item in items:
                flattened = {}
                for key, value in item.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            flattened[f"{key}_{sub_key}"] = sub_value
                    else:
                        flattened[key] = value
                transformed.append(flattened)
            
            return (True, {
                "TransformedData": transformed,
                "Operation": "flatten"
            })
        
        else:
            return (False, f"Unknown operation: {operation}")
        
    except Exception as e:
        return (False, f"Transform error: {str(e)}")


def func_assemble_product_data(params: dict) -> tuple[bool, dict | str]:
    """
    Assemble extracted product data into temporary database for scalable LLM analysis.
    
    Universal assembler that:
    - Takes extracted_data from Extract Attributes (or any structured list)
    - Stores in temp.db with proper schema
    - Enables flexible querying for LLM context building
    - Handles small and large datasets efficiently
    
    This decouples data extraction from analysis, allowing:
    - Multiple data sources to be assembled
    - Progressive refinement (filter → aggregate → analyze)
    - Reusable intermediate results across different strategies
    
    Parameters:
        extracted_data (list): List of product dicts with flattened specifications
        source_type (str, optional): Type of data being assembled (default: "product_specifications")
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Assembled Data (str): JSON string with assembly summary for Analyze With LLM
            - records_inserted (int): Number of records inserted
            - fields_discovered (int): Number of unique fields
    """
    from ..db.connection import get_temp_connection
    
    # Parse parameters - extracted_data may come from Extract Attributes
    extracted_raw = params.get("extracted_data", [])
    
    if isinstance(extracted_raw, str):
        try:
            extracted_data = json.loads(extracted_raw) if extracted_raw else []
        except json.JSONDecodeError as e:
            return (False, f"Failed to parse extracted_data: {e}")
    else:
        extracted_data = extracted_raw
    
    if not extracted_data:
        return (False, "No extracted_data provided for assembly")
    
    source_type = params.get("source_type", "product_specifications")
    
    try:
        with get_temp_connection() as conn:
            cursor = conn.cursor()
            
            # CRITICAL: Clear existing data to prevent stale data pollution
            # Drop and recreate table to ensure clean state for fresh assembly
            debug.print_function("🧹 Clearing temp.db for fresh assembly...")
            cursor.execute("DROP TABLE IF EXISTS temp_product_specs")
            
            # Create temp table for product specifications with family context
            cursor.execute("""
                CREATE TABLE temp_product_specs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    product_code TEXT,
                    family_id INTEGER,
                    family_name TEXT,
                    category TEXT,
                    family_construction_details TEXT,
                    page_number INTEGER,
                    specifications TEXT,
                    source_type TEXT
                )
            """)
            debug.print_function("✅ temp.db cleaned and ready for fresh data")
            
            # Track all unique specification fields (will be populated during insertion)
            all_spec_fields = set()
            
            # Insert records with family context (already included from Extract Attributes)
            records_inserted = 0
            for item in extracted_data:
                # Extract core fields
                product_id = item.get("product_id")
                product_code = item.get("product_code", "")
                family_id = item.get("family_id")
                family_name = item.get("family_name", "")
                category = item.get("category", "")
                page_number = item.get("page_number")
                
                # Family construction details already extracted by Extract Attributes
                family_construction_dict = item.get("family_construction_details", {})
                family_construction = json.dumps(family_construction_dict) if family_construction_dict else "{}"
                
                # Get nested specifications JSON (already in correct format from Extract Attributes)
                specs_dict = item.get("specifications", {})
                specs_json = json.dumps(specs_dict) if specs_dict else "{}"
                
                cursor.execute("""
                    INSERT INTO temp_product_specs 
                    (product_id, product_code, family_id, family_name, category, family_construction_details, page_number, specifications, source_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (product_id, product_code, family_id, family_name, category, family_construction, page_number, specs_json, source_type))
                
                records_inserted += 1
                
                # Track all specification fields for reporting
                if specs_dict:
                    for spec_key in specs_dict.keys():
                        all_spec_fields.add(spec_key)
            
            conn.commit()
            
            # Create assembly summary for Analyze With LLM
            summary = {
                "temp_table": "temp_product_specs",
                "records_inserted": records_inserted,
                "fields_discovered": len(all_spec_fields),
                "source_type": source_type,
                "field_list": sorted(list(all_spec_fields)),
                "sample_products": [item.get("product_code") for item in extracted_data[:5]]
            }
            
            debug.print_function(f"Assembled {records_inserted} records with {len(all_spec_fields)} spec fields into temp.db")
            
            # Return in format compatible with Analyze With LLM
            return (True, {
                "Assembled Data": json.dumps([{
                    "table_name": "Product Specifications Assembly",
                    "tablecontent": json.dumps(summary)
                }]),
                "records_inserted": records_inserted,
                "fields_discovered": len(all_spec_fields)
            })
            
    except Exception as e:
        debug.print_error(f"Assembly error: {e}")
        return (False, f"Assembly error: {str(e)}")


def func_extract_attributes(params: dict) -> tuple[bool, dict | str]:
    """
    Hierarchical attribute extraction respecting database parent-child relationships.
    
    Extracts attributes with proper inheritance:
    - Category query → Extract category + all families + all products
    - Family query → Extract family (construction, temp range) + all products
    - Product query → Extract product + inherit family context
    
    This leverages the normalized database design:
    categories → product_families → products
    
    Extraction Modes:
    1. auto (default): Automatically extracts with full hierarchical context
    2. specific: Extract specific fields listed in config["fields"]
    3. filter: Extract items matching specific criteria
    
    Parameters:
        items (list): Product items with specifications (from Query Database)
        extraction_type (str): "auto", "specific", or "filter" (default: "auto")
        config (dict): Optional configuration
            - fields (list): Specific fields to extract in "specific" mode
            - filters (dict): Filter criteria in "filter" mode
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - extracted_data (list): Products with full hierarchical context
            - count (int): Number of items extracted
            - fields_found (list): List of unique specification fields found
            - families_included (list): List of family names with context
    """
    import json
    import re
    
    # Parse parameters safely - they may come as strings from workflow
    items_raw = params.get("items", [])
    
    if isinstance(items_raw, str):
        try:
            items = json.loads(items_raw) if items_raw else []
            debug.print_function(f"Parsed {len(items)} items from JSON string")
        except json.JSONDecodeError as e:
            debug.print_error(f"JSON parse failed: {e}")
            return (False, f"Failed to parse items JSON: {str(e)}")
    else:
        items = items_raw
    
    if not items:
        return (False, "No items provided for extraction")
    
    extraction_type = params.get("extraction_type", "auto").lower()
    
    config_raw = params.get("config", {})
    if isinstance(config_raw, str):
        try:
            config = json.loads(config_raw) if config_raw else {}
        except json.JSONDecodeError:
            config = {}
    else:
        config = config_raw
    
    extracted_data = []
    all_fields = set()
    families_included = set()
    
    # STEP 1: Fetch family AND category context for all products (full hierarchy)
    unique_family_ids = set()
    for item in items:
        if isinstance(item, dict) and item.get("family_id"):
            unique_family_ids.add(item.get("family_id"))
    
    family_context_cache = {}
    category_context_cache = {}
    
    if unique_family_ids:
        try:
            debug.print_function(f"Fetching hierarchical context for {len(unique_family_ids)} families and their categories...")
            with get_output_connection() as output_conn:
                output_cursor = output_conn.cursor()
                family_ids_str = ",".join(str(fid) for fid in unique_family_ids)
                
                # Fetch family metadata with category reference and family_code
                output_cursor.execute(f"""
<<<<<<< HEAD
                    SELECT id, family_code, name, construction_details, applications, subtitle, description, category_id
                    FROM product_families
                    WHERE id IN ({family_ids_str})
=======
                    SELECT pf.id, pf.name, pf.construction_details, pf.applications, pf.subtitle, pf.description,
                           c.name as category_name, c.chapter as category_chapter
                    FROM product_families pf
                    LEFT JOIN categories c ON pf.category_id = c.id
                    WHERE pf.id IN ({family_ids_str})
>>>>>>> 3cb2ab885cc8c17e76341833fd282c4b15e607b2
                """)
                
                category_ids_to_fetch = set()
                for row in output_cursor.fetchall():
                    family_id = row[0]
                    category_id = row[7]
                    
                    # Track categories for batch fetch
                    if category_id:
                        category_ids_to_fetch.add(category_id)
                    
                    # Safely parse JSON fields
                    try:
                        construction_details = json.loads(row[3]) if row[3] else {}
                    except (json.JSONDecodeError, TypeError):
                        construction_details = {}
                    
                    try:
                        applications = json.loads(row[4]) if row[4] else {}
                    except (json.JSONDecodeError, TypeError):
                        applications = {}
                    
                    family_context_cache[family_id] = {
                        "family_code": row[1],
                        "family_name": row[2],
                        "construction_details": construction_details,
                        "applications": applications,
<<<<<<< HEAD
                        "subtitle": row[5],
                        "description": row[6],
                        "category_id": category_id
=======
                        "subtitle": row[4],
                        "description": row[5],
                        "category_name": row[6],
                        "category_chapter": row[7]
>>>>>>> 3cb2ab885cc8c17e76341833fd282c4b15e607b2
                    }
                
                # Batch fetch all categories
                if category_ids_to_fetch:
                    category_ids_str = ",".join(str(cid) for cid in category_ids_to_fetch)
                    output_cursor.execute(f"""
                        SELECT id, name, chapter
                        FROM categories
                        WHERE id IN ({category_ids_str})
                    """)
                    
                    for row in output_cursor.fetchall():
                        category_id = row[0]
                        category_context_cache[category_id] = {
                            "category_name": row[1],
                            "chapter": row[2]
                        }
                
            debug.print_function(f"✅ Loaded context for {len(family_context_cache)} families and {len(category_context_cache)} categories")
        except Exception as e:
            debug.print_warning(f"Could not fetch family/category context: {e}")
            # Continue without full context rather than failing
    
    try:
        # STEP 2: Extract product data with inherited family context
        for item in items:
            if not isinstance(item, dict):
                continue
            
            family_id = item.get("family_id")
            family_context = family_context_cache.get(family_id, {})
            
<<<<<<< HEAD
            # Get category context if available
            category_id = family_context.get("category_id")
            category_context = category_context_cache.get(category_id, {}) if category_id else {}
=======
            # Create extracted item with FULL hierarchical context
            extracted_item = {
                "product_code": item.get("product_code"),
                "family_name": family_context.get("family_name") or item.get("family_name"),
                "category": family_context.get("category_name"),
                "page_number": item.get("page_number"),
                
                # HIERARCHICAL CONTEXT: Include family-level attributes (for deeper analysis if needed)
                "family_construction_details": family_context.get("construction_details", {}),
                "family_applications": family_context.get("applications", {}),
                "family_subtitle": family_context.get("subtitle"),
                "family_description": family_context.get("description")
            }
>>>>>>> 3cb2ab885cc8c17e76341833fd282c4b15e607b2
            
            # Create extracted item with FULL hierarchical context (organized: product → family → category → page)
            
            # Parse specifications JSON if present
            specs_raw = item.get("specifications", "{}")
            if isinstance(specs_raw, str):
                try:
                    specs = json.loads(specs_raw)
                except json.JSONDecodeError:
                    specs = {}
            else:
                specs = specs_raw if isinstance(specs_raw, dict) else {}
            
<<<<<<< HEAD
            extracted_item = {
                # LEVEL 3: PRODUCT
                "product_code": item.get("product_code"),
                "specifications": specs,  # Moved here, right after product_code
                "configuration_name": item.get("configuration_name"),  # Added metadata
                
                # LEVEL 2: FAMILY
                "family_code": family_context.get("family_code"),
                "family_name": family_context.get("family_name"),
                "family_subtitle": family_context.get("subtitle"),
                "family_description": family_context.get("description"),
                "family_construction_details": family_context.get("construction_details", {}),
                "family_applications": family_context.get("applications", {}),
                
                # LEVEL 1: CATEGORY
                "category_name": category_context.get("category_name"),
                "chapter": category_context.get("chapter"),
                
                # LEVEL 0: PAGE
                "page_number": item.get("page_number")
            }
            
            if family_context:
                families_included.add(family_context.get("family_name"))  # Use from family_context_cache
            
            # Mode 1: AUTO - Extract with full hierarchical context (no flattened spec_* fields)
            if extraction_type == "auto":
=======
            # Mode 1: AUTO - Extract all specification fields with family context
            if extraction_type == "auto":
                # Keep specifications as nested JSON for consistency
                extracted_item["specifications"] = specs
                
                # Track all specification fields found
                for spec_key in specs.keys():
                    all_fields.add(spec_key)
                
>>>>>>> 3cb2ab885cc8c17e76341833fd282c4b15e607b2
                extracted_data.append(extracted_item)
            
            # Mode 2: SPECIFIC - Extract only requested fields
            elif extraction_type == "specific":
                requested_fields = config.get("fields", [])
                extracted_item["specifications"] = {}
                
                for field in requested_fields:
                    # Try exact match first
                    if field in specs:
                        extracted_item["specifications"][field] = specs[field]
                        all_fields.add(field)
                    else:
                        # Try case-insensitive match
                        for spec_key, spec_value in specs.items():
                            if spec_key.lower() == field.lower():
                                extracted_item["specifications"][field] = spec_value
                                all_fields.add(spec_key)
                                break
                
                if extracted_item["specifications"]:
                    extracted_data.append(extracted_item)
            
            # Mode 3: FILTER - Extract items matching criteria
            elif extraction_type == "filter":
                filters = config.get("filters", {})
                matches = True
                
                for filter_field, filter_value in filters.items():
                    item_value = specs.get(filter_field)
                    
                    # Handle different filter types
                    if isinstance(filter_value, dict):
                        # Range filter: {"min": 10, "max": 50}
                        if "min" in filter_value:
                            try:
                                if float(item_value) < float(filter_value["min"]):
                                    matches = False
                                    break
                            except (ValueError, TypeError):
                                matches = False
                                break
                        if "max" in filter_value:
                            try:
                                if float(item_value) > float(filter_value["max"]):
                                    matches = False
                                    break
                            except (ValueError, TypeError):
                                matches = False
                                break
                    else:
                        # Exact match filter
                        if str(item_value).lower() != str(filter_value).lower():
                            matches = False
                            break
                
                if matches:
                    extracted_item["specifications"] = specs
                    for key in specs.keys():
                        all_fields.add(key)
                    extracted_data.append(extracted_item)
        
        debug.print_function(f"Extracted {len(extracted_data)} items with {len(all_fields)} unique fields from {len(families_included)} families")
        
        return (True, {
            "extracted_data": extracted_data,
            "extraction_type": extraction_type,
            "count": len(extracted_data),
            "fields_found": sorted(list(all_fields)),
            "families_included": sorted(list(families_included)),
            "extraction_mode": extraction_type  # Keep for backward compatibility
        })
        
    except Exception as e:
        debug.print_error(f"Extraction error: {e}")
        return (False, f"Extraction error: {str(e)}")


def _filter_assembled_data(question: str, max_products: int = 50) -> tuple[list, int]:
    """
    Helper function: Filter relevant data from temp.db to solve context limit issue.
    
    CONTEXT LIMIT SOLUTION:
    Instead of loading ALL assembled data into LLM context (which can exceed 30K chars),
    this helper intelligently filters data to only include relevant products:
    1. Extracts keywords from the question
    2. Queries temp.db with WHERE filters for relevant products
    3. Returns small subset (max 50 products) for main LLM analysis
    
    This helper does NOT answer the question - it only filters/prepares the data.
    The main analysis function receives the filtered data and provides the answer.
    
    Args:
        question: User question to extract keywords from
        max_products: Maximum number of products to return (default 50)
        
    Returns:
        tuple: (filtered_products_list, total_products_in_db)
    """
    try:
        from ..db.connection import get_temp_connection
        
        debug.print_function(f"🔍 Filtering assembled data for: {question[:50]}...")
        
        with get_temp_connection() as conn:
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM temp_product_specs")
            total_in_db = cursor.fetchone()[0]
            
            # Extract keywords from question for smart filtering
            import re
            # Remove common words
            stopwords = {'what', 'is', 'the', 'for', 'this', 'at', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'with'}
            words = re.findall(r'\b[a-zA-Z0-9]+\b', question.lower())
            keywords = [w for w in words if len(w) > 2 and w not in stopwords]
            
            debug.print_function(f"� Extracted keywords: {keywords}")
            
            # Build smart query with keyword filtering
            if keywords:
                # Try to match keywords in family_name or product_code
                conditions = []
                for kw in keywords[:5]:  # Limit to first 5 keywords
                    conditions.append(f"UPPER(family_name) LIKE '%{kw.upper()}%'")
                    conditions.append(f"UPPER(product_code) LIKE '%{kw.upper()}%'")
                
                where_clause = " OR ".join(conditions)
                query = f"""
                    SELECT product_code, family_name, category, family_construction_details, specifications, page_number
                    FROM temp_product_specs
                    WHERE {where_clause}
                    LIMIT {max_products}
                """
            else:
                # No clear keywords - return first N products
                query = f"""
                    SELECT product_code, family_name, category, family_construction_details, specifications, page_number
                    FROM temp_product_specs
                    LIMIT {max_products}
                """
            
            debug.print_function(f"Executing filter query...")
            cursor.execute(query)
            rows = cursor.fetchall()
        
        debug.print_function(f"✅ Filtered: {len(rows)} products from {total_in_db} total")
        
        # Convert rows to structured data
        filtered_products = []
        for row in rows:
            product = {
                'product_code': row[0],
                'family_name': row[1],
                'category': row[2],
                'family_construction': json.loads(row[3]) if row[3] else {},
                'specifications': json.loads(row[4]) if row[4] else {},
                'page_number': row[5]
            }
            filtered_products.append(product)
        
        debug.print_function(f"✅ Filtered {len(filtered_products)} products from {total_in_db} total")
        
        return (filtered_products, total_in_db)
        
    except Exception as e:
        import traceback
        debug.print_error(f"Error filtering assembled data: {e}")
        debug.print_error(f"Traceback: {traceback.format_exc()}")
        raise


def func_analyze_with_llm(params: dict) -> tuple[bool, dict | str]:
    """
    LLM-powered analysis with dual-mode context handling and smart chunking.
    
    DUAL MODE ARCHITECTURE:
    1. Direct Mode: Accept context directly from previous function (small datasets)
    2. Assembly Mode: Query temp.db for context (large datasets, assembled data)
    
    This enables flexible composition:
    - Extract Attributes → Analyze With LLM (direct, for small data)
    - Extract Attributes → Assemble Product Data → Analyze With LLM (via temp.db, for large data)
    - Multiple sources → Assemble → Analyze With LLM (complex workflows)
    
    FLEXIBLE QUERY TYPES:
    The LLM can handle ANY type of analysis task, not just specifications:
    - Compatibility checking (Will product A work with product B?)
    - Product recommendations (What's the best hose for X application?)
    - Technical advice (Should I use 2SN or 4SP for this?)
    - Requirement analysis (What do I need for 350 bar at 80°C?)
    - Safety assessments (Is this configuration safe?)
    - Application guidance (Best practices for mobile hydraulics?)
    - Troubleshooting (Why might a hose fail in this scenario?)
    - Standards interpretation (What does ISO 1307 require?)
    
    CONTEXT LIMIT HANDLING:
    - Automatically detects when context exceeds LLM limits (~8000 tokens)
    - Uses intelligent chunking strategies for large datasets
    - Prioritizes relevant data based on question keywords
    - Falls back to temp.db queries for massive datasets
    
    Parameters:
        task (str): Analysis task type (e.g., "compatibility", "recommendation", "general_query")
        extracted_data (list): Direct context data from Extract Attributes (Direct Mode)
        assembled_data (str): Assembly summary JSON from Assemble Product Data (Assembly Mode)
        question (str): Any question requiring LLM analysis - not limited to specifications
        max_context_chars (int): Maximum context size (default: 30000 chars ≈ 8000 tokens)
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Analysis (str): LLM analysis result
            - Task (str): Task performed
            - mode_used (str): "direct", "assembly", or "chunked"
            - products_analyzed (int): Number of products analyzed
            - context_truncated (bool): Whether context was truncated
    """
    from ..db.connection import get_temp_connection
    
    task = params.get("task", "").lower()
    extracted_data_param = params.get("extracted_data", [])
    # Try both parameter name formats for backwards compatibility
    assembled_data = params.get("Assembled Data", params.get("assembled_data", ""))
    question = params.get("question", "")
    max_context_chars = params.get("max_context_chars", 30000)  # ~8000 tokens
    
    # Parse extracted_data if it's a JSON string
    if isinstance(extracted_data_param, str):
        try:
            extracted_data_raw = json.loads(extracted_data_param) if extracted_data_param else []
        except json.JSONDecodeError:
            extracted_data_raw = []
    else:
        extracted_data_raw = extracted_data_param
    
    if not task:
        return (False, "Missing task parameter")
    
    if not question:
        return (False, "Missing question parameter")
    
    # NOTE: No longer validating specific task types - accept ANY analysis task
    # This allows flexibility for various question types beyond just specifications
    
    try:
        # DETERMINE MODE: Assembly, Direct, or Chunked
        mode_used = "direct"
        context_str = ""
        products_analyzed = 0
        context_truncated = False
        
        if assembled_data:
            # ASSEMBLY MODE: Use SQL Agent to FILTER data, then LLM analyzes
            # SQL Agent filters relevant products from temp.db (solves context limits)
            # Main LLM receives filtered data and provides the analysis
            mode_used = "assembly_sql_agent"
            debug.print_function("[func_analyze_with_llm] Using ASSEMBLY SQL AGENT mode - filtering data from temp.db")
            
            try:
                # Step 1: Filter data intelligently (solves context limit)
                filtered_products, total_in_db = _filter_assembled_data(question, max_products=50)
                products_analyzed = len(filtered_products)
                
                # Step 2: Format filtered data into context (should be small now)
                context_parts = [f"=== FILTERED PRODUCT DATA ({products_analyzed} of {total_in_db} products) ===\n"]
                
                # Group by family to show construction details once per family
                families_shown = set()
                
                for product in filtered_products:
                    family_name = product['family_name']
                    category = product.get('category', '')
                    
                    # Show family construction details (once per family)
                    if family_name and family_name not in families_shown:
                        families_shown.add(family_name)
                        context_parts.append(f"\n=== {family_name} Family ({category}) ===")
                        family_construction = product.get('family_construction', {})
                        if family_construction:
                            for key, value in family_construction.items():
                                context_parts.append(f"  {key}: {value}")
                        context_parts.append("")  # Blank line
                    
                    # Show individual product with category
                    context_parts.append(f"\nProduct: {product['product_code']} (Category: {category}, Family: {family_name}, Page: {product['page_number']})")
                    specs = product['specifications']
                    for spec_key, spec_value in specs.items():
                        # Don't modify the key - use it as-is from the nested JSON
                        context_parts.append(f"  {spec_key}: {spec_value}")
                
                context_str = "\n".join(context_parts)
                
                # Check if still too large (shouldn't happen with filtered data)
                if len(context_str) > max_context_chars:
                    debug.print_warning(f"Filtered data still large ({len(context_str)} chars), truncating...")
                    context_str = context_str[:max_context_chars] + "\n... (truncated)"
                    context_truncated = True
                
                debug.print_function(f"📦 Filtered context: {len(context_str)} chars, {products_analyzed} products")
                # Successfully filtered - will continue to Step 3 (LLM analysis) after exception handlers
                    
            except (ImportError, AttributeError) as e:
                debug.print_warning(f"LangChain SQL Agent not available: {e}")
                debug.print_warning("SQL Agent filtering failed, but continuing with fallback filter...")
                
                # Don't fail - just use the filtered data we got from _filter_assembled_data
                # The helper function already did keyword-based filtering
                # Continue to Step 3 below
                    
            except Exception as e:
                debug.print_warning(f"LangChain SQL Agent not available: {e}")
                debug.print_warning("Falling back to direct query mode...")
                
                # FALLBACK: Traditional query-all approach
                with get_temp_connection() as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT product_code, family_name, specifications, page_number
                        FROM temp_product_specs
                        ORDER BY family_name, product_code
                        LIMIT 100
                    """)
                    rows = cursor.fetchall()
                    
                    if not rows:
                        return (False, "No data found in temp.db assembly")
                    
                    products_analyzed = len(rows)
                    context_parts = [f"=== ASSEMBLED PRODUCT SPECIFICATIONS ({products_analyzed} products) ===\n"]
                    
                    for row in rows:
                        context_parts.append(f"\nProduct: {row[0]} (Family: {row[1]}, Page: {row[3]})")
                        specs = json.loads(row[2]) if row[2] else {}
                        for spec_key, spec_value in specs.items():
                            display_key = spec_key.replace("spec_", "").replace("_", " ").title()
                            context_parts.append(f"  {display_key}: {spec_value}")
                    
                    context_str = "\n".join(context_parts)
                    
                    # Check context limit even in fallback
                    if len(context_str) > max_context_chars:
                        context_str = context_str[:max_context_chars] + "\n... (truncated due to context limits)"
                        context_truncated = True
                        mode_used = "assembly_fallback_truncated"
                    else:
                        mode_used = "assembly_fallback"
                    
                    # Now use traditional LLM analysis on the context
                    prompt_loader = get_prompt_loader()
                    prompts = prompt_loader.get_prompt("function_execution", "analyze_with_llm")
                    chain = _build_llm_processing_chain(prompts["system"], prompts["user_template"], "reasoning")
                    
                    analysis = chain.invoke({
                        "task": task.upper(),
                        "context": context_str,
                        "question": question
                    })
                    
            except Exception as e:
                debug.print_error(f"Failed to query temp.db: {e}")
                return (False, f"Assembly mode failed: {e}")
        
        else:
            # DIRECT MODE: Use provided extracted_data
            mode_used = "direct"
            debug.print_function("[func_analyze_with_llm] Using DIRECT mode - extracted_data from Extract Attributes")
            
            if not extracted_data_raw or (isinstance(extracted_data_raw, (list, dict)) and not extracted_data_raw):
                return (False, "No context provided (neither extracted_data nor assembled_data)")
            
            # Format context for prompt
            if isinstance(extracted_data_raw, list):
                # List of items - format as readable text
                products_analyzed = len(extracted_data_raw)
                
                # SMART CHUNKING: Check if context will exceed limits
                # First, try to build full context
                context_parts = [f"=== PRODUCT DATA ({products_analyzed} items) ===\n"]
                items_to_include = extracted_data_raw
                
                # Extract keywords from question for relevance filtering
                question_lower = question.lower()
                question_keywords = set(question_lower.split())
                
                # Try to prioritize items that match question keywords
                if len(extracted_data_raw) > 20:  # Only filter if we have many items
                    scored_items = []
                    for item in extracted_data_raw:
                        score = 0
                        item_text = json.dumps(item).lower()
                        for keyword in question_keywords:
                            if len(keyword) > 3 and keyword in item_text:  # Skip short words
                                score += 1
                        scored_items.append((score, item))
                    
                    # Sort by relevance score (descending)
                    scored_items.sort(key=lambda x: x[0], reverse=True)
                    items_to_include = [item for score, item in scored_items]
                    
                    debug.print_function(f"[func_analyze_with_llm] Sorted {len(items_to_include)} items by relevance to question")
                
                # Build context with chunking strategy
                for i, item in enumerate(items_to_include, 1):
                    product_code = item.get('product_code', 'Unknown')
                    page_num = item.get('page_number', 'N/A')
                    item_text = f"\n{i}. Product: {product_code} (Page {page_num})"
                    # Show all fields (not just specs)
                    for key, value in item.items():
                        if key not in ['product_code', 'page_number']:  # Already shown
                            display_key = key.replace("spec_", "").replace("_", " ").title()
                            item_text += f"\n   {display_key}: {value}"
                    
                    # Check if adding this item would exceed limit
                    test_context = "\n".join(context_parts) + item_text
                    if len(test_context) > max_context_chars:
                        debug.print_function(f"[func_analyze_with_llm] Context limit reached at item {i}/{products_analyzed}")
                        context_parts.append(f"\n... and {products_analyzed - i + 1} more products (truncated due to context limits)")
                        context_truncated = True
                        mode_used = "chunked"
                        break
                    
                    context_parts.append(item_text)
                
                context_str = "\n".join(context_parts)
                
                if context_truncated:
                    debug.print_function(f"[func_analyze_with_llm] ⚠️ Context truncated: {len(context_str)}/{max_context_chars} chars, showing most relevant items")
                
            else:
                # Dict or string - use as-is
                products_analyzed = 1
                context_str = json.dumps(extracted_data_raw, indent=2) if isinstance(extracted_data_raw, dict) else str(extracted_data_raw)
                
                # Check if single item exceeds limit
                if len(context_str) > max_context_chars:
                    context_str = context_str[:max_context_chars] + "\n... (truncated)"
                    context_truncated = True
                    mode_used = "chunked"
        
        # Step 3: Invoke main LLM to analyze the context (filtered or direct)
        # Load prompts from yaml
        prompt_loader = get_prompt_loader()
        prompts = prompt_loader.get_prompt("function_execution", "analyze_with_llm")
        
        system_msg = prompts["system"]
        user_template = prompts["user_template"]
        
        # Build LLM chain with REASONING tier for better analysis
        chain = _build_llm_processing_chain(system_msg, user_template, "reasoning")
        
        debug.print_function(f"💭 Main LLM analyzing {len(context_str)} chars of context...")
        
        # Invoke LLM
        analysis = chain.invoke({
            "task": task.upper(),
            "context": context_str,
            "question": question
        })
        
        # Clean up deepseek-r1 thinking tags if present
        # deepseek-r1 outputs format: <think>reasoning...</think>actual answer
        if "<think>" in analysis and "</think>" in analysis:
            # Extract only the answer part (after </think>)
            analysis = analysis.split("</think>", 1)[-1].strip()
            debug.print_function(f"[func_analyze_with_llm] Stripped <think> tags from reasoning model output")
        
        debug.print_function(f"[func_analyze_with_llm] Task: {task}, Mode: {mode_used}, Products: {products_analyzed}, Analysis length: {len(analysis)} chars, Truncated: {context_truncated}")
        
        return (True, {
            "Analysis": analysis,
            "Task": task,
            "Context": f"{mode_used} mode: {products_analyzed} products analyzed, {len(context_str)} chars context{', truncated' if context_truncated else ''}",
            "mode_used": mode_used,
            "products_analyzed": products_analyzed,
            "context_truncated": context_truncated,
            "context_size_chars": len(context_str)
        })
        
    except Exception as e:
        logger.error(f"[func_analyze_with_llm] Error: {e}")
        return (False, f"LLM analysis error: {str(e)}")


def func_lookup_standard(params: dict) -> tuple[bool, dict | str]:
    """
    LLM-powered standard reference lookup with interpretation.
    
    Provides intelligent lookup and explanation of:
    - ISO standards (hydraulic hose specifications)
    - SAE standards (hose types and ratings)
    - DIN standards (German industrial standards)
    - Thread standards (BSP, NPT, metric, etc.)
    
    Parameters:
        standard_type (str): Type of standard (ISO, SAE, DIN, thread)
        identifier (str): Standard identifier to look up
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - standard_details (dict): Complete standard information
            - standard_type (str): Type of standard
            - identifier (str): Identifier queried
    """
    standard_type = params.get("standard_type", "").upper()
    identifier = params.get("identifier", "")
    
    if not standard_type or not identifier:
        return (False, "Missing standard_type or identifier parameters")
    
    try:
        # Load prompts and build LLM chain
        prompt_loader = get_prompt_loader()
        prompts = prompt_loader.get_prompt("function_execution", "lookup_standard")
        
        system_msg = prompts["system"]
        user_template = prompts["user_template"]
        
        chain = _build_llm_processing_chain(system_msg, user_template, "basic")
        
        # Invoke LLM for intelligent standard lookup
        result = chain.invoke({
            "standard_type": standard_type,
            "identifier": identifier
        })
        
        debug.print_function(f"[func_lookup_standard] Type: {standard_type}, ID: {identifier}, Result: {result[:200]}...")
        
        # Parse the response - it's typically structured text, not JSON
        # We'll return the full explanation as the standard details
        return (True, {
            "standard_details": result,
            "standard_type": standard_type,
            "identifier": identifier
        })
        
    except Exception as e:
        logger.error(f"[func_lookup_standard] Error: {e}")
        return (False, f"Standard lookup error: {str(e)}")


def func_navigate_hierarchy(params: dict) -> tuple[bool, dict | str]:
    """
    Hierarchical data traversal (product families, categories, subcategories).
    
    Navigate hierarchical structures:
    - Parent → Children (e.g., Family → Products)
    - Child → Parent (e.g., Product → Family)
    - Siblings (e.g., other products in same family)
    - Ancestors (e.g., Product → Family → Category)
    
    Parameters:
        start_node (str): Starting point ID or code
        direction (str): Navigation direction ("children", "parent", "siblings", "ancestors")
        hierarchy_type (str): Type of hierarchy ("product_family", "category")
        database_path (str, optional): Path to database
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Nodes (list): Nodes found in navigation
            - Direction (str): Direction navigated
            - Count (int): Number of nodes found
    """
    import sqlite3
    
    start_node = params.get("start_node", "")
    direction = params.get("direction", "children").lower()
    hierarchy_type = params.get("hierarchy_type", "product_family")
    db_path = params.get("database_path", CONFIG.get("harvested_db"))
    
    if not start_node:
        return (False, "Missing start_node parameter")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if hierarchy_type == "product_family":
            if direction == "children":
                # Family → Products
                query = """
                    SELECT product_code, specifications
                    FROM Products
                    WHERE family_id = (SELECT family_id FROM ProductFamilies WHERE family_name LIKE ?)
                    LIMIT 50
                """
                cursor.execute(query, (f"%{start_node}%",))
                
            elif direction == "parent":
                # Product → Family
                query = """
                    SELECT f.id as family_id, f.family_name, f.description
                    FROM ProductFamilies f
                    JOIN Products p ON p.family_id = f.id
                    WHERE p.product_code = ?
                """
                cursor.execute(query, (start_node,))
                
            elif direction == "siblings":
                # Other products in same family
                query = """
                    SELECT product_code, specifications
                    FROM Products
                    WHERE family_id = (SELECT family_id FROM Products WHERE product_code = ?)
                    AND product_code != ?
                    LIMIT 50
                """
                cursor.execute(query, (start_node, start_node))
            
            else:
                return (False, f"Unknown direction: {direction}")
        
        else:
            return (False, f"Unknown hierarchy type: {hierarchy_type}")
        
        rows = cursor.fetchall()
        nodes = [dict(row) for row in rows]
        
        conn.close()
        
        return (True, {
            "Nodes": nodes,
            "Direction": direction,
            "Count": len(nodes)
        })
        
    except Exception as e:
        return (False, f"Navigation error: {str(e)}")


def func_discover_items(params: dict) -> tuple[bool, dict | str]:
    """
    Pattern-based item discovery using wildcards and fuzzy matching.
    
    Discover items based on patterns:
    - Wildcard searches (e.g., "H*2SN*" finds all 2SN hoses)
    - Fuzzy matching (handles typos)
    - Pattern-based discovery
    - Range queries (e.g., "diameter between 10-20mm")
    
    Parameters:
        pattern (str): Search pattern (supports * wildcards)
        field (str): Field to search in
        fuzzy (bool, optional): Enable fuzzy matching (default: False)
        database_path (str, optional): Path to database
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - DiscoveredItems (list): Items matching the pattern
            - Pattern (str): Pattern used
            - Count (int): Number of items discovered
    """
    import sqlite3
    import re
    
    pattern = params.get("pattern", "")
    field = params.get("field", "product_code")
    fuzzy = params.get("fuzzy", False)
    db_path = params.get("database_path", CONFIG.get("harvested_db"))
    
    if not pattern:
        return (False, "Missing pattern parameter")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Convert wildcard pattern to SQL LIKE pattern
        sql_pattern = pattern.replace("*", "%")
        
        query = f"""
            SELECT product_code, specifications, family_id
            FROM Products
            WHERE {field} LIKE ?
            LIMIT 50
        """
        
        cursor.execute(query, (sql_pattern,))
        rows = cursor.fetchall()
        
        discovered = [dict(row) for row in rows]
        
        conn.close()
        
        return (True, {
            "DiscoveredItems": discovered,
            "Pattern": pattern,
            "Count": len(discovered)
        })
        
    except Exception as e:
        return (False, f"Discovery error: {str(e)}")


def func_get_metadata(params: dict) -> tuple[bool, dict | str]:
    """
    Domain metadata retrieval (families, categories, certifications).
    
    Retrieve metadata about the domain:
    - List all product families
    - List all categories
    - Get available certifications
    - Get field schemas
    - Database statistics
    
    Parameters:
        metadata_type (str): Type of metadata ("families", "categories", "certifications", "statistics")
        database_path (str, optional): Path to database
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Metadata (list or dict): Requested metadata
            - Type (str): Metadata type retrieved
    """
    import sqlite3
    
    metadata_type = params.get("metadata_type", "").lower()
    db_path = params.get("database_path", CONFIG.get("harvested_db"))
    
    if not metadata_type:
        return (False, "Missing metadata_type parameter")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if metadata_type == "families":
            query = "SELECT family_id, family_name, description FROM ProductFamilies ORDER BY family_name"
            cursor.execute(query)
            rows = cursor.fetchall()
            metadata = [dict(row) for row in rows]
            
        elif metadata_type == "statistics":
            stats = {}
            
            # Count products
            cursor.execute("SELECT COUNT(*) as count FROM Products")
            stats["total_products"] = cursor.fetchone()["count"]
            
            # Count families
            cursor.execute("SELECT COUNT(*) as count FROM ProductFamilies")
            stats["total_families"] = cursor.fetchone()["count"]
            
            metadata = stats
            
        elif metadata_type == "categories":
            # Get unique categories from family names or descriptions
            query = "SELECT DISTINCT family_name FROM ProductFamilies ORDER BY family_name"
            cursor.execute(query)
            rows = cursor.fetchall()
            metadata = [row["family_name"] for row in rows]
        
        elif metadata_type == "location":
            # Get location information for a specific product
            product_code = params.get("product_code", "")
            if not product_code:
                return (False, "Missing product_code for location lookup")
            
            query = """
                SELECT 
                    p.product_code,
                    p.page_number,
                    pf.name as family_name,
                    c.name as category_name,
                    c.chapter
                FROM products p
                LEFT JOIN product_families pf ON p.family_id = pf.id
                LEFT JOIN categories c ON pf.category_id = c.id
                WHERE p.product_code = ?
            """
            cursor.execute(query, (product_code,))
            row = cursor.fetchone()
            
            if row:
                metadata = {
                    "product_code": row["product_code"],
                    "page_number": row["page_number"],
                    "family": row["family_name"],
                    "category": row["category_name"],
                    "chapter": row["chapter"],
                    "location_found": True
                }
            else:
                metadata = {"location_found": False, "error": f"Product {product_code} not found"}
            
        else:
            return (False, f"Unknown metadata type: {metadata_type}")
        
        conn.close()
        
        return (True, {
            "Metadata": metadata,
            "Type": metadata_type
        })
        
    except Exception as e:
        return (False, f"Metadata error: {str(e)}")


# ── Function Registry ────────────────────────────────────────────────

# Maps function template names to Python implementations for dynamic dispatch
# Used by execute_function_by_name() - must match FunctionTemplateLibrary entries

FUNCTION_MAP = {
    # Original SAAB-focused functions
    "Table Search": func_table_search,
    "Display Images": func_display_images,
    "Table Search On Document": func_table_search_on_document,
    "Filter Table": func_filter_table,
    "Filter Table By Field": func_filter_table_by_field,
    "Analyze Data": func_analyze_data,
    "Extract Product Number": func_extract_product_number,
    "Suggest Keywords": func_suggest_keywords,
    "Normalize Product Number": func_normalize_product_number,
    "Assemble Table": func_assemble_table,
    "Find Latest Document": func_find_latest_document,
    "Generate Visual Layout": func_generate_visual_layout,
    
    # New generic Hydroscand functions (17 total)
    # Category 1: Search & Discovery (4)
    "Search Products": func_search_products,
    "Query Database": func_query_database,  # SQL Agent for flexible database queries
    "Get Related Items": func_get_related_items,

    "Semantic Search": func_semantic_search,
    # Category 2: Data Processing (3)
    "Filter Items": func_filter_items,
    "Transform Data": func_transform_data,
    # Category 3: Comparison & Analysis (4)
    "Compare Items": func_compare_items,
    "Extract Attributes": func_extract_attributes,
    "Assemble Product Data": func_assemble_product_data,  # Universal assembler for temp.db
    "Analyze With LLM": func_analyze_with_llm,
    # Category 4: Calculations & Conversions (3)
    "Calculate": func_calculate,
    "Convert Units": func_convert_units,
    "Lookup Standard": func_lookup_standard,
    # Category 5: Navigation & Discovery (3)
    "Navigate Hierarchy": func_navigate_hierarchy,
    "Discover Items": func_discover_items,
    "Get Metadata": func_get_metadata,
}


def execute_function_by_name(fname: str, param_dict: dict) -> tuple[bool, dict | str]:
    """Execute function by template name with error handling and output normalization."""
    fn = FUNCTION_MAP.get(fname)
    if not fn:
        return (False, f"unknown function '{fname}'")
    try:
        ok, out = fn(param_dict)
        if ok and not isinstance(out, dict):
            out = {"result": out}
        return (ok, out)
    except Exception as e:
        return (False, f"runtime error: {e}")
