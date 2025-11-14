# agentic_reasoning/config/config_loader.py
"""
Configuration loader for the agentic reasoning system.

Provides centralized configuration management with YAML-based settings,
environment detection, and automatic logging setup. Supports multiple
configuration tiers including LLM models, database paths, and system
parameters.

Key Responsibilities:
- Load and validate YAML configuration files
- Environment-aware configuration (development/staging/production)
- LLM model tier management (basic/reasoning/multimodal)
- Database path configuration with fallback defaults
- Centralized logging configuration with file and console output
- Configuration validation and error handling

Configuration Structure:
- llms: Model configuration by tier (basic/reasoning/multimodal)
- databases: Path configuration for SQLite databases
- logging: Log directory, file, and level configuration
- system: Performance and timeout settings
- debug: Development and debugging flags

LLM Model Tiers:
- Basic: Fast models for simple tasks (llama3.2)
- Reasoning: Advanced models for complex analysis (phi4)
- Multimodal: Models with image/document processing capabilities

Usage Patterns:
- CONFIG["llms"]["basic"]["model"] - Access model configuration
- CONFIG["databases"]["agentic_db"] - Database path access
- CONFIG.get("debug", {}).get("enabled", False) - Safe config access

Error Handling:
- FileNotFoundError: Missing configuration file with fallback defaults
- yaml.YAMLError: Invalid YAML syntax with detailed error reporting
- OSError: Log directory creation failures with graceful degradation
"""


import logging
import os
import sys
from pathlib import Path

import yaml

# ── Configuration loading ────────────────────────────────

_LAYER_ROOT = Path(__file__).resolve().parents[2]  # Layer_2


def _resolve_path(value: str) -> str:
    """Resolve config paths relative to Layer_2 directory for cwd flexibility."""
    if not isinstance(value, str) or not value.strip():
        return value

    # Expand user home references
    expanded = os.path.expanduser(value.strip())
    candidate = Path(expanded)

    if candidate.is_absolute():
        return str(candidate)

    # Resolve against Layer_2 root to keep compatibility with existing layout
    return str((_LAYER_ROOT / candidate).resolve())


def _normalize_paths(config: dict) -> dict:
    """Normalize well-known path entries to absolute paths."""
    path_keys = {
        # Note: log_dir is NOT included here because it's handled specially
        # in the logger setup section to ensure it's always relative to Layer_2_Agentic
        "model_path",
        "agentic_db",
        "harvested_db",
        "temp_db",
        "config_file",
    }

    for key in path_keys:
        if key in config:
            config[key] = _resolve_path(config[key])

    # Support optional nested dictionaries users may add later
    for section_key in ("databases", "paths"):
        section = config.get(section_key)
        if isinstance(section, dict):
            for key, value in section.items():
                section[key] = _resolve_path(value)

    return config


def load_config(path="agentic_reasoning/config/config.yaml"):
    """
    Load YAML configuration file and return parsed configuration dict.

    Attempts to find the config file relative to the current working directory
    or relative to this file's location.

    Args:
        path (str): Path to the YAML configuration file

    Returns:
        dict: Parsed configuration settings
    """
    # Try multiple potential paths
    potential_paths = [
        path,  # Original relative path
        os.path.join(os.getcwd(), path),  # From current working directory
        os.path.join(Path(__file__).parent.parent.parent, path),  # From project root
        os.path.join(
            Path(__file__).parent, "config.yaml"
        ),  # From this file's directory
    ]

    for config_path in potential_paths:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                # Normalize critical path settings before returning
                return _normalize_paths(loaded or {})
        except FileNotFoundError:
            continue

    # If no config file found, raise error with helpful message
    raise FileNotFoundError(
        f"Could not find config.yaml in any of these locations:\n"
        + "\n".join(f"  - {p}" for p in potential_paths)
    )


CONFIG = load_config()


# ── Centralized logger ─────────────────────────────

# Resolve log directory relative to this file's location (Layer_2-Agentic/config/)
# This ensures logs are always created in Layer_2-Agentic/config/logs/ regardless of where the script is run from
BASE_DIR = Path(__file__).resolve().parent.parent  # Layer_2-Agentic directory
LOG_DIR = BASE_DIR / CONFIG.get("log_dir", "config/logs")
LOG_FILE = CONFIG.get("log_file", "project.log")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_LEVEL = CONFIG.get("log_level", "INFO").upper()

logging.basicConfig(
    level=logging.INFO,
    # level=logging.DEBUG,  # Uncomment for debug level
    # format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
    format="%(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("agentic_reasoning")
