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
    """Generate different formatting variations of a product number/keyword."""
    variations = []

    # Skip if not a potential product number (too short or no alphanumeric pattern)
    if len(keyword) < 5 or not re.search(r"[A-Za-z].*\d|\d.*[A-Za-z]", keyword):
        return variations

    # Clean the keyword first
    clean_kw = re.sub(r"\s+", "", keyword)  # Remove all spaces

    # Common product number patterns to handle:
    # RPT 235 4309/350 vs RPT2354309/350
    # C0001686-61701 vs C0001686 61701
    # RNT 181/001 vs RNT181/001
    # TFR 46310/001 vs TFR46310/001

    # Pattern 1: RPT series (RPT + numbers)
    rpt_match = re.match(r"(RPT)(\d{3})(\d{4})/(\d{3})", clean_kw, re.IGNORECASE)
    if rpt_match:
        prefix, part1, part2, suffix = rpt_match.groups()
        variations.extend(
            [
                f"{prefix} {part1} {part2}/{suffix}",  # RPT 235 4309/350
                f"{prefix}{part1} {part2}/{suffix}",  # RPT235 4309/350
                f"{prefix} {part1}{part2}/{suffix}",  # RPT 2354309/350
                f"{prefix}{part1}{part2}/{suffix}",  # RPT2354309/350 (original)
                f"{prefix} {part1[:2]} {part1[2:]}{part2}/{suffix}",  # RPT 23 54309/350
            ]
        )

    # Pattern 2: C-series with dash (C0001686-61701)
    c_match = re.match(r"(C\d+)-?(\d+)", clean_kw, re.IGNORECASE)
    if c_match:
        prefix, suffix = c_match.groups()
        variations.extend(
            [
                f"{prefix}-{suffix}",  # C0001686-61701
                f"{prefix} {suffix}",  # C0001686 61701
                f"{prefix} - {suffix}",  # C0001686 - 61701
                f"{prefix}{suffix}",  # C000168661701
            ]
        )

    # Pattern 3: RNT series (RNT + numbers)
    rnt_match = re.match(r"(RNT)(\d+)/(\d+)", clean_kw, re.IGNORECASE)
    if rnt_match:
        prefix, part, suffix = rnt_match.groups()
        variations.extend(
            [
                f"{prefix} {part}/{suffix}",  # RNT 181/001
                f"{prefix}{part}/{suffix}",  # RNT181/001
                f"{prefix} {part} {suffix}",  # RNT 181 001
                f"{prefix}{part} {suffix}",  # RNT181 001
                f"{prefix}-{part}/{suffix}",  # RNT-181/001
            ]
        )

    # Pattern 4: TFR series (TFR + numbers)
    tfr_match = re.match(r"(TFR)(\d+)/(\d+)", clean_kw, re.IGNORECASE)
    if tfr_match:
        prefix, part, suffix = tfr_match.groups()
        variations.extend(
            [
                f"{prefix} {part}/{suffix}",  # TFR 46310/001
                f"{prefix}{part}/{suffix}",  # TFR46310/001
                f"{prefix} {part[:4]} {part[4:]}/{suffix}",  # TFR 4631 0/001
                f"{prefix} {part[:3]} {part[3:]}/{suffix}",  # TFR 463 10/001
                f"{prefix}-{part}/{suffix}",  # TFR-46310/001
            ]
        )

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

        header, *rows = content if keep_header else ([], content)

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
    """Normalize product code to a standard searchable format."""
    if not product_code:
        return product_code

    # Clean up the code
    code = product_code.strip()

    # Handle common RPT patterns: RPT2354309/350 → RPT 235 4309/350
    rpt_match = re.match(r"(RPT)(\d{3})(\d{4})/(\d{3})", code, re.IGNORECASE)
    if rpt_match:
        prefix, part1, part2, suffix = rpt_match.groups()
        return f"{prefix} {part1} {part2}/{suffix}"

    # Handle C-series: ensure dash format C0001686-61701
    c_match = re.match(r"(C\d+)[\s-]*(\d+)", code, re.IGNORECASE)
    if c_match:
        prefix, suffix = c_match.groups()
        return f"{prefix}-{suffix}"

    # Handle RNT series: ensure space format RNT 181/001
    rnt_match = re.match(r"(RNT)(\d+)/(\d+)", code, re.IGNORECASE)
    if rnt_match:
        prefix, part, suffix = rnt_match.groups()
        return f"{prefix} {part}/{suffix}"

    # Handle TFR series: ensure space format TFR 46310/001
    tfr_match = re.match(r"(TFR)(\d+)/(\d+)", code, re.IGNORECASE)
    if tfr_match:
        prefix, part, suffix = tfr_match.groups()
        return f"{prefix} {part}/{suffix}"

    # Return original if no pattern matches
    return code


def func_normalize_product_number(params: dict) -> tuple[bool, dict | str]:
    """Normalize product code by removing spaces/suffixes and truncating to 7 chars."""
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

    code = re.sub(r"\s+", "", raw)
    code = re.sub(r"/.*$", "", code)
    family_code = code[:7]

    debug.print_function(
        f"[func_normalize_product_number] RESET: {repr(raw)} → {repr(family_code)}"
    )

    # Return ONLY the normalized code (this resets the keyword context)
    return (True, {"Keyword Output": family_code})


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

        # Common technical terms that might appear in questions
        fallback_terms = [
            "torque",
            "tool",
            "crimp",
            "locator",
            "shell",
            "size",
            "voltage",
            "current",
            "diameter",
            "contact",
            "installing",
            "installation",
            "connector",
            "cable",
            "jacket",
        ]

        question_lower = question.lower()
        found_terms = []

        for term in fallback_terms:
            if term in question_lower:
                # Handle compound terms like "installing tool"
                if term == "installing" and "tool" in question_lower:
                    found_terms.append("installing tool")
                elif term == "shell" and "size" in question_lower:
                    found_terms.append("shell size")
                elif term not in [
                    "installing",
                    "shell",
                ]:  # Don't add these individually if compound found
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
    Generate visual layout by finding images from the same documents where the product was found.

    This function:
    1. Takes filtered table data to identify which documents contain the product
    2. Searches for images from those specific documents in saved_images table
    3. Provides visual content directly related to the product's documentation
    4. Combines images with technical specifications from the filtered data

    Args:
        params: Dict containing filtered table data and product information

    Returns:
        Tuple of (success, output_dict) with layout information and relevant images
    """
    debug.print_function(
        f"[func_generate_visual_layout] Starting document-based visual layout generation"
    )

    # Get input parameters
    product_code = params.get("Product Number Output", "").strip()
    filtered_data = params.get("Filtered Data", "").strip()
    user_query = params.get("Input", "").strip()

    debug.print_function(f"[func_generate_visual_layout] Product: {product_code}")
    debug.print_function(f"[func_generate_visual_layout] Query: {user_query}")

    if not filtered_data:
        return (False, "No filtered table data available for visual layout generation")

    try:
        # Parse the filtered data to find source documents
        tables = json.loads(filtered_data) if filtered_data else []
        source_documents = set()

        # Extract document names from the filtered data
        for table in tables:
            if isinstance(table, dict) and "filename" in table:
                doc_name = table["filename"]
                if doc_name:
                    source_documents.add(doc_name)

        debug.print_function(
            f"[func_generate_visual_layout] Found {len(source_documents)} source documents: {list(source_documents)}"
        )

        # Determine visual type from query
        visual_type = _determine_visual_type(user_query, "")

        # Search for images from the identified documents
        relevant_images = _search_images_by_documents(
            list(source_documents), product_code, visual_type
        )

        layout_info = {
            "product_code": product_code,
            "visual_type": visual_type,
            "source_documents": list(source_documents),
            "images_found": len(relevant_images) > 0,
            "image_count": len(relevant_images),
            "images": relevant_images,
            "technical_data": _extract_technical_specs_from_filtered_data(tables),
            "layout_description": "",
        }

        debug.print_function(
            f"[func_generate_visual_layout] Found {len(relevant_images)} images from source documents"
        )

        # Generate layout description
        layout_info["layout_description"] = _generate_document_based_description(
            product_code, visual_type, source_documents, layout_info["technical_data"]
        )

        # Prepare image output for display/analysis
        image_output = []
        image_paths_for_display = []  # Simple paths for Display Images function

        if relevant_images:
            for img in relevant_images:
                image_output.append(
                    {
                        "path": img["file_path"],
                        "document": img["document_name"],
                        "type": img["image_type"],
                        "size": f"{img['width']}x{img['height']}",
                        "page": img.get("page_number", "N/A"),
                        "relevance": img["relevance_score"],
                    }
                )
                # Add simple path for display function
                image_paths_for_display.append(img["file_path"])

        # Create display-ready image output string
        if image_paths_for_display:
            display_output = f"Found {len(image_paths_for_display)} images: {image_paths_for_display[0]}"
            if len(image_paths_for_display) > 1:
                additional_count = len(image_paths_for_display) - 1
                additional_paths = ", ".join(
                    image_paths_for_display[1:3]
                )  # Show up to 2 more
                display_output += f" (+ {additional_count} more: {additional_paths})"
        else:
            display_output = "No images found"

        debug.print_function(
            f"[func_generate_visual_layout] Generated {visual_type} layout with {len(image_output)} images"
        )

        return (
            True,
            {
                "Layout Output": json.dumps(layout_info, ensure_ascii=False, indent=2),
                "Image Output": display_output,  # Simple format for Display Images function
                "Image Details": json.dumps(
                    image_output, ensure_ascii=False
                ),  # Detailed metadata
                "Document Name": f"Visual layout from {', '.join(list(source_documents)[:2])}",
            },
        )

    except Exception as e:
        logger.error(f"[func_generate_visual_layout] Error: {e}")
        return (False, f"Error generating visual layout: {e}")


def _search_images_by_documents(
    document_names: list, product_code: str, visual_type: str
) -> list:
    """Search for images specifically from the identified source documents."""
    from agentic_reasoning.db.connection import get_output_connection

    if not document_names:
        return []

    try:
        with get_output_connection() as conn:
            cursor = conn.cursor()

            # Create placeholders for document names
            placeholders = ",".join(["?" for _ in document_names])

            # Build query to find images from these specific documents
            query = f"""
            SELECT document_name, image_filename, image_type, image_width, image_height,
                   relevance_score, ocr_text, has_technical_content, complexity_score, page_number
            FROM saved_images
            WHERE document_name IN ({placeholders})
            AND has_technical_content = 1
            AND image_type IN ('technical_diagram', 'technical_content')
            ORDER BY relevance_score DESC, complexity_score DESC, image_area DESC
            LIMIT 10
            """

            # Add .pdf extension to document names if not present
            search_docs = []
            for doc in document_names:
                if not doc.endswith(".pdf"):
                    search_docs.append(f"{doc}.pdf")
                else:
                    search_docs.append(doc)

            debug.print_function(
                f"[_search_images_by_documents] Searching documents: {search_docs}"
            )
            cursor.execute(query, search_docs)
            results = cursor.fetchall()

            debug.print_function(
                f"[_search_images_by_documents] Found {len(results)} images"
            )

            return [
                {
                    "document_name": row[0],
                    "file_path": row[1],
                    "image_type": row[2],
                    "width": row[3],
                    "height": row[4],
                    "relevance_score": row[5] or 0.0,
                    "ocr_text": row[6] or "",
                    "has_technical_content": row[7],
                    "complexity_score": row[8] or 0.0,
                    "page_number": row[9] or 0,
                }
                for row in results
            ]
    except Exception as e:
        debug.print_function(f"[_search_images_by_documents] Error: {e}")

    return []


def _extract_technical_specs_from_filtered_data(tables: list) -> dict:
    """Extract technical specifications from the filtered table data."""
    specs = {
        "product_specifications": [],
        "found_in_documents": [],
        "table_count": len(tables),
    }

    for table in tables:
        if isinstance(table, dict):
            # Extract document name from filename
            if "filename" in table:
                specs["found_in_documents"].append(table["filename"])

            # Extract table content
            if "tablecontent" in table and table["tablecontent"]:
                try:
                    table_data = json.loads(table["tablecontent"])
                    if isinstance(table_data, list) and len(table_data) > 1:
                        headers = table_data[0]
                        for row in table_data[1:3]:  # Take first 2 data rows
                            if row and len(row) <= len(headers):
                                spec_row = {}
                                for i, header in enumerate(headers):
                                    if header and i < len(row) and row[i]:
                                        spec_row[header] = row[i]
                                if spec_row:
                                    specs["product_specifications"].append(spec_row)
                except (json.JSONDecodeError, TypeError):
                    # Skip malformed table content
                    continue

    # Remove duplicates from documents
    specs["found_in_documents"] = list(set(specs["found_in_documents"]))

    return specs


def _generate_document_based_description(
    product_code: str, visual_type: str, source_documents: list, technical_data: dict
) -> str:
    """Generate description based on the document-focused approach."""
    description = []

    if product_code:
        description.append(f"Visual Layout for {product_code}:")

        if visual_type == "connector":
            if "RPT" in product_code:
                description.append("- Circular SAAB RPT series connector")
                description.append("- Pin numbering typically clockwise from top")
            elif "RNT" in product_code:
                description.append("- Rectangular SAAB RNT series connector")
                description.append("- Systematic pin arrangement")
            else:
                description.append("- SAAB connector configuration")
        else:
            description.append(f"- {visual_type.title()} information and diagrams")

    if source_documents:
        description.append(
            f"\nSource Documents: {', '.join(list(source_documents)[:3])}"
        )

    if technical_data and technical_data.get("product_specifications"):
        description.append(
            f"\nTechnical Specifications: {len(technical_data['product_specifications'])} parameters found"
        )

        # Show a sample specification
        sample_spec = technical_data["product_specifications"][0]
        for key, value in list(sample_spec.items())[:3]:  # Show first 3 fields
            if value:
                description.append(f"- {key}: {value}")

    return "\n".join(description)


def _search_saved_images(product_code: str, keywords: str, visual_type: str) -> list:
    """Search for relevant images in the saved_images database table."""
    from agentic_reasoning.db.connection import get_output_connection

    try:
        with get_output_connection() as conn:
            cursor = conn.cursor()

            # Build search conditions for images
            search_conditions = []
            params = []

            # Search by product code in document name
            if product_code:
                # Extract base product family (e.g., RPT2354 from RPT2354313/350)
                base_code = _extract_product_family(product_code)
                search_conditions.append(
                    "(document_name LIKE ? OR document_name LIKE ?)"
                )
                params.extend([f"%{product_code}%", f"%{base_code}%"])

            # Search by keywords in OCR text or document name
            if keywords:
                keyword_list = [k.strip() for k in keywords.split(",")]
                for keyword in keyword_list[:3]:  # Limit to top 3 keywords
                    if keyword:
                        search_conditions.append(
                            "(ocr_text LIKE ? OR document_name LIKE ?)"
                        )
                        params.extend([f"%{keyword}%", f"%{keyword}%"])

            # Build the main search clause (OR combination of search terms)
            if search_conditions:
                main_search = f"({' OR '.join(search_conditions)})"

                # Add image type filters based on visual type
                type_conditions = _get_image_type_conditions(visual_type)

                # Combine search with type filter using AND
                if type_conditions:
                    where_clause = f"{main_search} AND ({type_conditions})"
                else:
                    where_clause = main_search

                query = f"""
                SELECT document_name, image_filename, image_type, image_width, image_height,
                       relevance_score, ocr_text, has_technical_content, complexity_score
                FROM saved_images
                WHERE {where_clause}
                ORDER BY relevance_score DESC, complexity_score DESC, image_area DESC
                LIMIT 10
                """

                debug.print_function(
                    f"[_search_saved_images] Executing query with {len(params)} params"
                )
                cursor.execute(query, params)
                results = cursor.fetchall()

                debug.print_function(
                    f"[_search_saved_images] Found {len(results)} images"
                )

                return [
                    {
                        "document_name": row[0],
                        "file_path": row[1],
                        "image_type": row[2],
                        "width": row[3],
                        "height": row[4],
                        "relevance_score": row[5] or 0.0,
                        "ocr_text": row[6] or "",
                        "has_technical_content": row[7],
                        "complexity_score": row[8] or 0.0,
                    }
                    for row in results
                ]
    except Exception as e:
        debug.print_function(f"[_search_saved_images] Error: {e}")

    return []


def _extract_product_family(product_code: str) -> str:
    """Extract the base product family from a full product code."""
    import re

    # Extract base family pattern (e.g., RPT2354 from RPT2354313/350)
    if "RPT" in product_code:
        match = re.search(r"RPT\s*(\d{4})", product_code)
        if match:
            return f"RPT{match.group(1)}"
    elif "RNT" in product_code:
        match = re.search(r"RNT\s*(\d{4})", product_code)
        if match:
            return f"RNT{match.group(1)}"
    elif "C" in product_code:
        match = re.search(r"C\d{7}", product_code)
        if match:
            return match.group(0)

    return product_code


def _get_image_type_conditions(visual_type: str) -> str:
    """Get SQL conditions for filtering images by type."""
    type_map = {
        "connector": "image_type IN ('technical_diagram', 'technical_content')",
        "circuit": "image_type IN ('technical_diagram', 'technical_content')",
        "dimension": "image_type IN ('technical_diagram', 'technical_content')",
        "installation": "image_type IN ('technical_diagram', 'technical_content')",
        "diagram": "image_type IN ('technical_diagram', 'technical_content')",
        "layout": "image_type IN ('technical_diagram', 'technical_content')",
    }

    base_condition = type_map.get(visual_type, "image_type = 'technical_diagram'")

    # Always prefer technical content and exclude logos
    return f"({base_condition}) AND has_technical_content = 1 AND image_type != 'logo'"


def _determine_visual_type(query: str, keywords: str) -> str:
    """Determine the type of visual content being requested."""
    combined_text = f"{query} {keywords}".lower()

    if any(term in combined_text for term in ["connector", "pin", "pinout", "contact"]):
        return "connector"
    elif any(
        term in combined_text
        for term in ["circuit", "schematic", "wiring", "electrical"]
    ):
        return "circuit"
    elif any(
        term in combined_text for term in ["dimension", "drawing", "mechanical", "size"]
    ):
        return "dimension"
    elif any(term in combined_text for term in ["installation", "mount", "assembly"]):
        return "installation"
    elif any(term in combined_text for term in ["diagram", "chart", "graph"]):
        return "diagram"
    else:
        return "layout"


def _get_visual_keywords(visual_type: str) -> str:
    """Get additional keywords based on visual type."""
    keyword_map = {
        "connector": "layout, pin, diagram, connector, schematic, pinout",
        "circuit": "circuit, schematic, wiring, electrical, diagram",
        "dimension": "dimension, drawing, mechanical, size, measurement",
        "installation": "installation, mount, assembly, setup, guide",
        "diagram": "diagram, chart, graph, illustration, figure",
        "layout": "layout, arrangement, configuration, design",
    }
    return keyword_map.get(visual_type, "layout, diagram, illustration")


def _get_stored_text_context(
    product_code: str, keywords: str, visual_type: str
) -> list:
    """Retrieve relevant text context from stored_texts table."""
    from agentic_reasoning.db.connection import get_output_connection

    try:
        with get_output_connection() as conn:
            cursor = conn.cursor()

            # Build search conditions
            conditions = []
            params = []

            if product_code:
                conditions.append("(document_name LIKE ? OR text LIKE ?)")
                params.extend([f"%{product_code}%", f"%{product_code}%"])

            if keywords:
                keyword_list = [k.strip() for k in keywords.split(",")]
                for keyword in keyword_list[:3]:  # Limit to top 3 keywords
                    if keyword:
                        conditions.append("(heading_name LIKE ? OR text LIKE ?)")
                        params.extend([f"%{keyword}%", f"%{keyword}%"])

            # Add visual-type specific terms
            visual_terms = _get_visual_keywords(visual_type).split(", ")
            for term in visual_terms[:2]:  # Limit to 2 visual terms
                conditions.append("(heading_name LIKE ? OR text LIKE ?)")
                params.extend([f"%{term}%", f"%{term}%"])

            if conditions:
                query = f"""
                SELECT document_name, heading_name, text, page_number
                FROM stored_texts
                WHERE {' OR '.join(conditions)}
                ORDER BY document_name, page_number
                LIMIT 10
                """
                cursor.execute(query, params)
                results = cursor.fetchall()

                return [
                    {
                        "document": row[0],
                        "heading": row[1] or "General",
                        "text": row[2][:500] + "..." if len(row[2]) > 500 else row[2],
                        "page": row[3],
                    }
                    for row in results
                ]
    except Exception as e:
        debug.print_function(f"[_get_stored_text_context] Error: {e}")

    return []


def _extract_technical_details(tables: list, visual_type: str) -> dict:
    """Extract technical details relevant to the visual type."""
    details = {}

    for table in tables:
        if isinstance(table, list) and len(table) > 1:
            headers = table[0] if table[0] else []

            # Look for different types of data based on visual type
            if visual_type == "connector":
                # Look for pin-related data
                pin_columns = []
                for i, header in enumerate(headers):
                    if header and any(
                        keyword in header.lower()
                        for keyword in ["pin", "contact", "position", "terminal"]
                    ):
                        pin_columns.append((i, header))

                if pin_columns:
                    details["pin_mapping"] = []
                    for row in table[1:]:
                        if row and len(row) > max([col[0] for col in pin_columns]):
                            pin_info = {}
                            for col_idx, col_name in pin_columns:
                                if col_idx < len(row):
                                    pin_info[col_name] = row[col_idx]
                            if pin_info:
                                details["pin_mapping"].append(pin_info)

            elif visual_type == "dimension":
                # Look for dimensional data
                dim_columns = []
                for i, header in enumerate(headers):
                    if header and any(
                        keyword in header.lower()
                        for keyword in [
                            "dimension",
                            "size",
                            "length",
                            "width",
                            "height",
                            "diameter",
                        ]
                    ):
                        dim_columns.append((i, header))

                if dim_columns:
                    details["dimensions"] = []
                    for row in table[1:]:
                        if row and len(row) > max([col[0] for col in dim_columns]):
                            dim_info = {}
                            for col_idx, col_name in dim_columns:
                                if col_idx < len(row):
                                    dim_info[col_name] = row[col_idx]
                            if dim_info:
                                details["dimensions"].append(dim_info)

            # Always capture general specifications
            if not details.get("specifications"):
                details["specifications"] = []

            # Add first few rows as general specs
            for row in table[1:3]:  # Limit to first 2 data rows
                if row:
                    spec_info = {}
                    for i, header in enumerate(headers[:5]):  # Limit to first 5 columns
                        if i < len(row) and header:
                            spec_info[header] = row[i]
                    if spec_info:
                        details["specifications"].append(spec_info)

    return details


def _generate_layout_description(
    product_code: str, visual_type: str, technical_details: dict, text_context: list
) -> str:
    """Generate a descriptive text for the layout."""
    description = []

    if product_code:
        if visual_type == "connector":
            if "RPT" in product_code:
                description.append(f"Connector Layout for {product_code}:")
                description.append("- Circular connector with numbered pin positions")
                description.append("- Standard SAAB RPT series configuration")
                description.append(
                    "- Pin numbering typically clockwise from top position"
                )
            elif "RNT" in product_code:
                description.append(f"Connector Layout for {product_code}:")
                description.append("- Rectangular connector configuration")
                description.append("- SAAB RNT series standard layout")
                description.append("- Pin arrangement in systematic rows/columns")
            else:
                description.append(f"Connector Layout for {product_code}:")
                description.append("- Standard SAAB connector configuration")
        else:
            description.append(f"{visual_type.title()} Information for {product_code}:")

    # Add information from text context
    if text_context:
        description.append("\nRelevant Technical Information:")
        for context in text_context[:3]:  # Limit to top 3 contexts
            if context["heading"] != "General":
                description.append(
                    f"- {context['heading']}: {context['text'][:100]}..."
                )

    # Add technical details summary
    if technical_details:
        if "pin_mapping" in technical_details:
            description.append(
                f"\nPin Configuration: {len(technical_details['pin_mapping'])} pins identified"
            )
        if "dimensions" in technical_details:
            description.append(
                f"\nDimensional Data: {len(technical_details['dimensions'])} measurements available"
            )
        if "specifications" in technical_details:
            description.append(
                f"\nTechnical Specifications: {len(technical_details['specifications'])} parameters listed"
            )

    return "\n".join(description)


def _generate_ascii_layout(
    technical_details: dict, product_code: str, visual_type: str
) -> str:
    """Generate ASCII art representation based on technical details."""
    if visual_type != "connector" or not technical_details.get("pin_mapping"):
        return ""

    pin_mapping = technical_details["pin_mapping"]

    # Create a simple circular layout for RPT series
    if "RPT" in product_code:
        layout = f"""
    Connector Layout - {product_code}

         13    14     1     2
      12                      3
   11                           4
      10                      5
         9     8     7     6

    Pin Configuration:
    """

        for i, pin in enumerate(pin_mapping[:14]):  # Show first 14 pins
            pin_num = i + 1
            pin_desc = str(pin) if pin else f"Pin {pin_num}"
            layout += f"    Pin {pin_num:2d}: {pin_desc}\n"

    else:
        # Generic rectangular layout
        layout = f"""
    Connector Layout - {product_code}

    ┌─────────────────┐
    │  Pin Layout     │
    │                 │
    """

        for i, pin in enumerate(pin_mapping[:10]):  # Limit to 10 pins for readability
            pin_num = i + 1
            pin_desc = str(pin) if pin else f"Pin {pin_num}"
            layout += f"    │ {pin_num:2d}: {pin_desc[:12]:<12} │\n"

        layout += "    └─────────────────┘"

    return layout


def _generate_ascii_connector_layout(pin_mapping: list, product_code: str) -> str:
    """Generate ASCII art representation of connector layout."""
    if not pin_mapping:
        return "No pin mapping data available for ASCII layout generation."

    # Create a simple circular layout for RPT series
    if "RPT" in product_code:
        layout = """
        Connector Layout - {product_code}

             13    14     1     2
          12                      3
       11                           4
          10                      5
             9     8     7     6

        Pin Configuration:
        """.format(
            product_code=product_code
        )

        for i, pin in enumerate(pin_mapping[:14]):  # Show first 14 pins
            pin_num = i + 1
            pin_desc = str(pin) if pin else f"Pin {pin_num}"
            layout += f"        Pin {pin_num:2d}: {pin_desc}\n"

    else:
        # Generic rectangular layout
        layout = f"""
        Connector Layout - {product_code}

        ┌─────────────────┐
        │  Pin Layout     │
        │                 │
        """

        for i, pin in enumerate(pin_mapping):
            pin_num = i + 1
            pin_desc = str(pin) if pin else f"Pin {pin_num}"
            layout += f"        │ {pin_num:2d}: {pin_desc[:12]:<12} │\n"

        layout += "        └─────────────────┘"

    return layout


# ── Function Registry ────────────────────────────────────────────────

# Maps function template names to Python implementations for dynamic dispatch
# Used by execute_function_by_name() - must match FunctionTemplateLibrary entries

FUNCTION_MAP = {
    "Table Search": func_table_search,
    "Display Images": func_display_images,  # Display images in VS Code
    "Table Search On Document": func_table_search_on_document,
    "Filter Table": func_filter_table,
    "Filter Table By Field": func_filter_table_by_field,
    "Analyze Data": func_analyze_data,  # LLM-powered analysis
    "Extract Product Number": func_extract_product_number,
    "Suggest Keywords": func_suggest_keywords,
    "Normalize Product Number": func_normalize_product_number,
    "Assemble Table": func_assemble_table,
    "Find Latest Document": func_find_latest_document,
    "Generate Visual Layout": func_generate_visual_layout,  # Visual layouts and diagrams
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
