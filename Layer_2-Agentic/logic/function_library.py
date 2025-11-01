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

from agentic_reasoning.config.config_loader import CONFIG
from agentic_reasoning.config.debug_config import debug
from agentic_reasoning.config.prompt_loader import get_prompt_loader
from agentic_reasoning.db.connection import (
    get_agentic_connection,
    get_output_connection,
)
from agentic_reasoning.logic.llm_helpers import get_basic_llm, get_reasoning_llm

logger = logging.getLogger("FUNCTION_LIBRARY")
DB_PATH_OUTPUT = CONFIG["harvested_db"]

# Import async helpers for performance improvements
try:
    from agentic_reasoning.logic.async_helpers import (
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
        from agentic_reasoning.config.config_loader import CONFIG
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
        from agentic_reasoning.config.config_loader import CONFIG
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
        return (False, "Keyword Output parameter missing")

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
            like_clause = " OR ".join(["tablecontent LIKE ?"] * len(unique_keywords))
            cursor.execute(
                f"""
                SELECT id, filename, page_nr, heading_number, heading_name,
                    table_name, tablecontent
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
        from agentic_reasoning.logic.vector_helpers import VectorTableSearch

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
            like_clause = " OR ".join(["tablecontent LIKE ?"] * len(unique_keywords))
            doc_clause = " OR ".join(["filename = ?"] * len(doc_names))
            where_clause = f"({like_clause}) AND ({doc_clause})"
            query = f"""
                SELECT id, filename, page_nr, heading_number, heading_name,
                       table_name, tablecontent
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
    from agentic_reasoning.db.connection import get_temp_connection

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
    from agentic_reasoning.db.connection import get_temp_connection

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
    
    db_path = params.get("database_path", "data/database/harvested.db")
    category = params.get("category", "").strip()
    keywords = params.get("keywords", "").strip()
    specs = params.get("specs", {})
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
            "Count": len(products)
        })
        
    except Exception as e:
        return (False, f"Search error: {str(e)}")


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
    items = params.get("items", [])
    filters = params.get("filters", {})
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
    items = params.get("items", [])
    fields = params.get("fields", [])
    
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
    db_path = params.get("database_path", "data/database/harvested.db")
    
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
                SELECT p.product_code, p.product_name, p.description, p.family_id, f.family_name
                FROM Products p
                LEFT JOIN ProductFamilies f ON p.family_id = f.family_id
                WHERE p.description LIKE ? OR p.specifications LIKE ?
                LIMIT 20
            """
            cursor.execute(query, (f"%{item_id}%", f"%{item_id}%"))
            
        elif relationship_type == "alternative":
            # Find alternative products in same family
            query = """
                SELECT p.product_code, p.product_name, p.description, p.specifications
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


def func_semantic_search(params: dict) -> tuple[bool, dict | str]:
    """
    Natural language search with synonym expansion and fuzzy matching.
    
    Performs intelligent search that understands synonyms, related terms,
    and common variations. Expands queries automatically.
    
    Parameters:
        query (str): Natural language search query
        database_path (str, optional): Path to database
        limit (int, optional): Maximum results (default: 20)
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Results (list): Matching items with relevance scores
            - ExpandedTerms (list): Terms added through synonym expansion
            - Count (int): Number of results found
    """
    import sqlite3
    
    query = params.get("query", "").strip()
    db_path = params.get("database_path", "data/database/harvested.db")
    limit = params.get("limit", 20)
    
    if not query:
        return (False, "Missing required parameter: query")
    
    # Synonym expansion dictionary
    synonyms = {
        "hose": ["hose", "tube", "pipe", "line"],
        "hydraulic": ["hydraulic", "hydro", "pressure"],
        "coupling": ["coupling", "connector", "fitting", "adapter"],
        "sleeve": ["sleeve", "ferrule", "fitting"],
        "temperature": ["temperature", "temp", "thermal"],
        "pressure": ["pressure", "bar", "mpa", "psi"],
    }
    
    # Expand query terms
    query_terms = query.lower().split()
    expanded_terms = set(query_terms)
    
    for term in query_terms:
        for key, values in synonyms.items():
            if term in values:
                expanded_terms.update(values)
    
    expanded_list = list(expanded_terms)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Build search with expanded terms
        conditions = []
        params_list = []
        
        for term in expanded_list:
            conditions.append("(p.product_name LIKE ? OR p.description LIKE ? OR f.family_name LIKE ?)")
            params_list.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        
        query_sql = f"""
            SELECT p.product_code, p.product_name, p.description, f.family_name
            FROM Products p
            LEFT JOIN ProductFamilies f ON p.family_id = f.family_id
            WHERE {' OR '.join(conditions)}
            LIMIT ?
        """
        params_list.append(limit)
        
        cursor.execute(query_sql, params_list)
        rows = cursor.fetchall()
        
        results = [dict(row) for row in rows]
        conn.close()
        
        return (True, {
            "Results": results,
            "ExpandedTerms": expanded_list,
            "Count": len(results)
        })
        
    except Exception as e:
        return (False, f"Semantic search error: {str(e)}")


def func_aggregate_data(params: dict) -> tuple[bool, dict | str]:
    """
    Grouping and statistical aggregations on datasets.
    
    Performs GROUP BY operations and calculates statistics:
    - Count, sum, average, min, max
    - Group by any field
    - Multiple aggregation functions
    
    Parameters:
        items (list): List of items to aggregate
        group_by (str): Field name to group by
        aggregations (dict): Aggregation operations {"field": "operation"}
            Operations: "count", "sum", "avg", "min", "max"
            
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Groups (dict): Aggregated results by group
            - TotalGroups (int): Number of groups
    """
    items = params.get("items", [])
    group_by = params.get("group_by", "")
    aggregations = params.get("aggregations", {})
    
    if not items:
        return (False, "No items provided")
    
    if not group_by:
        return (False, "Missing group_by parameter")
    
    try:
        from collections import defaultdict
        
        # Group items
        groups = defaultdict(list)
        for item in items:
            group_key = item.get(group_by, "Unknown")
            groups[group_key].append(item)
        
        # Calculate aggregations for each group
        results = {}
        for group_key, group_items in groups.items():
            group_result = {"count": len(group_items)}
            
            for field, operation in aggregations.items():
                values = [item.get(field) for item in group_items if item.get(field) is not None]
                
                if not values:
                    group_result[f"{field}_{operation}"] = None
                    continue
                
                # Convert to numeric if possible
                try:
                    numeric_values = [float(v) for v in values]
                except:
                    numeric_values = []
                
                if operation == "sum" and numeric_values:
                    group_result[f"{field}_sum"] = sum(numeric_values)
                elif operation == "avg" and numeric_values:
                    group_result[f"{field}_avg"] = sum(numeric_values) / len(numeric_values)
                elif operation == "min" and numeric_values:
                    group_result[f"{field}_min"] = min(numeric_values)
                elif operation == "max" and numeric_values:
                    group_result[f"{field}_max"] = max(numeric_values)
                elif operation == "count":
                    group_result[f"{field}_count"] = len(values)
            
            results[str(group_key)] = group_result
        
        return (True, {
            "Groups": results,
            "TotalGroups": len(results)
        })
        
    except Exception as e:
        return (False, f"Aggregation error: {str(e)}")


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


def func_extract_attributes(params: dict) -> tuple[bool, dict | str]:
    """
    LLM-powered intelligent attribute extraction.
    
    Handles complex extraction scenarios:
    - Unstructured text parsing
    - Regex patterns with fallback to LLM
    - JSON path navigation
    - Field mapping with normalization
    - Format standardization
    
    Parameters:
        items (list): Items to extract from
        extraction_type (str): Method ("regex", "json_path", "field_map", "intelligent")
        config (dict): Extraction configuration
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - extracted_data (list): Extracted attributes
            - extraction_type (str): Method used
            - count (int): Number of items extracted
    """
    items = params.get("items", [])
    extraction_type = params.get("extraction_type", "intelligent").lower()
    config = params.get("config", {})
    
    if not items:
        return (False, "Missing items parameter")
    
    # For intelligent extraction or when complex patterns needed, use LLM
    if extraction_type == "intelligent" or extraction_type == "llm":
        try:
            # Load prompts and build LLM chain
            prompt_loader = get_prompt_loader()
            prompts = prompt_loader.get_prompt("function_execution", "extract_attributes")
            
            system_msg = prompts["system"]
            user_template = prompts["user_template"]
            
            chain = _build_llm_processing_chain(system_msg, user_template, "basic")
            
            # Format items and config for prompt
            items_text = json.dumps(items, indent=2) if isinstance(items, list) else str(items)
            config_text = json.dumps(config, indent=2) if isinstance(config, dict) else str(config)
            
            # Invoke LLM for intelligent extraction
            result = chain.invoke({
                "extraction_type": extraction_type.upper(),
                "items": items_text,
                "config": config_text
            })
            
            debug.print_function(f"[func_extract_attributes] Type: {extraction_type}, Items: {len(items)}, Result: {result[:200]}...")
            
            # Try to parse LLM result as JSON array
            try:
                import re
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                else:
                    # Return raw result if not JSON
                    extracted_data = [{"raw_extraction": result}]
            except:
                extracted_data = [{"raw_extraction": result}]
            
            return (True, {
                "extracted_data": extracted_data,
                "extraction_type": extraction_type,
                "count": len(extracted_data)
            })
            
        except Exception as e:
            logger.error(f"[func_extract_attributes] Error: {e}")
            return (False, f"Extraction error: {str(e)}")
    
    else:
        # For simple extraction types, use basic logic
        import re
        extracted_data = []
        
        for item in items:
            if extraction_type == "regex":
                # Apply regex patterns from config
                patterns = config.get("patterns", {})
                extracted = {}
                item_str = str(item)
                for field, pattern in patterns.items():
                    match = re.search(pattern, item_str, re.IGNORECASE)
                    if match:
                        extracted[field] = match.group(1) if match.groups() else match.group(0)
                if extracted:
                    extracted_data.append(extracted)
                    
            elif extraction_type == "field_map":
                # Map fields from item
                field_map = config.get("field_map", {})
                if isinstance(item, dict):
                    extracted = {}
                    for target_field, source_field in field_map.items():
                        if source_field in item:
                            extracted[target_field] = item[source_field]
                    if extracted:
                        extracted_data.append(extracted)
        
        return (True, {
            "extracted_data": extracted_data,
            "extraction_type": extraction_type,
            "count": len(extracted_data)
        })


def func_analyze_with_llm(params: dict) -> tuple[bool, dict | str]:
    """
    LLM-powered analysis for compatibility, recommendations, comparisons.
    
    Uses LLM for intelligent analysis tasks:
    - Compatibility checking (Will product A work with product B?)
    - Product recommendations (What's the best hose for X application?)
    - Technical advice (Should I use 2SN or 4SP for this?)
    - Requirement analysis
    
    Parameters:
        task (str): Analysis task ("compatibility", "recommendation", "comparison", "advice")
        context (dict): Context data for the task
        question (str): Specific question to answer
        
    Returns:
        tuple[bool, dict]: Success status and results dict with:
            - Analysis (str): LLM analysis result
            - Task (str): Task performed
            - Confidence (str): Confidence level if applicable
    """
    task = params.get("task", "").lower()
    context = params.get("context", {})
    question = params.get("question", "")
    
    if not task:
        return (False, "Missing task parameter")
    
    if not question:
        return (False, "Missing question parameter")
    
    # Validate task type
    valid_tasks = ["compatibility", "recommendation", "comparison", "advice"]
    if task not in valid_tasks:
        return (False, f"Invalid task '{task}'. Must be one of: {', '.join(valid_tasks)}")
    
    try:
        # Load prompts from yaml
        prompt_loader = get_prompt_loader()
        prompts = prompt_loader.get_prompt("function_execution", "analyze_with_llm")
        
        system_msg = prompts["system"]
        user_template = prompts["user_template"]
        
        # Build LLM chain
        chain = _build_llm_processing_chain(system_msg, user_template, "basic")
        
        # Format context for prompt
        context_str = json.dumps(context, indent=2) if isinstance(context, dict) else str(context)
        
        # Invoke LLM
        analysis = chain.invoke({
            "task": task.upper(),
            "context": context_str,
            "question": question
        })
        
        debug.print_function(f"[func_analyze_with_llm] Task: {task}, Analysis: {analysis[:200]}...")
        
        return (True, {
            "Analysis": analysis,
            "Task": task,
            "Context": context_str[:500] if len(context_str) > 500 else context_str
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
    db_path = params.get("database_path", "data/database/harvested.db")
    
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
                    SELECT product_code, product_name, description
                    FROM Products
                    WHERE family_id = (SELECT family_id FROM ProductFamilies WHERE family_name LIKE ?)
                    LIMIT 50
                """
                cursor.execute(query, (f"%{start_node}%",))
                
            elif direction == "parent":
                # Product → Family
                query = """
                    SELECT f.family_id, f.family_name, f.description
                    FROM ProductFamilies f
                    JOIN Products p ON p.family_id = f.family_id
                    WHERE p.product_code = ?
                """
                cursor.execute(query, (start_node,))
                
            elif direction == "siblings":
                # Other products in same family
                query = """
                    SELECT product_code, product_name, description
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
    db_path = params.get("database_path", "data/database/harvested.db")
    
    if not pattern:
        return (False, "Missing pattern parameter")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Convert wildcard pattern to SQL LIKE pattern
        sql_pattern = pattern.replace("*", "%")
        
        query = f"""
            SELECT product_code, product_name, description, family_id
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
    db_path = params.get("database_path", "data/database/harvested.db")
    
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
    
    # New generic Hydroscand functions (15 total)
    # Category 1: Search & Discovery (3)
    "Search Products": func_search_products,
    "Get Related Items": func_get_related_items,
    "Semantic Search": func_semantic_search,
    # Category 2: Data Processing (3)
    "Filter Items": func_filter_items,
    "Aggregate Data": func_aggregate_data,
    "Transform Data": func_transform_data,
    # Category 3: Comparison & Analysis (3)
    "Compare Items": func_compare_items,
    "Extract Attributes": func_extract_attributes,
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
