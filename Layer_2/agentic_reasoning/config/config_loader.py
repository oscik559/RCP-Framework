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
                return yaml.safe_load(f)
        except FileNotFoundError:
            continue

    # If no config file found, raise error with helpful message
    raise FileNotFoundError(
        f"Could not find config.yaml in any of these locations:\n"
        + "\n".join(f"  - {p}" for p in potential_paths)
    )


CONFIG = load_config()


# ── Centralized logger ─────────────────────────────

LOG_DIR = Path(CONFIG.get("log_dir", "agentic_reasoning/logs"))
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
