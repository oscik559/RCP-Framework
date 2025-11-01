# agentic_reasoning/config/prompt_loader.py
"""
Centralized prompt template management system for the agentic reasoning system.

Provides structured loading, formatting, and management of LLM prompts with
template variable substitution, prompt inheritance, and category organization.
Designed for consistent prompt engineering across all workflow nodes.

Key Features:
- YAML-based prompt template storage with hierarchical organization
- Jinja2-style template variable substitution ({{variable_name}})
- Prompt category organization (goal_validation, strategy_selection, etc.)
- Template inheritance and composition for reusable prompt components
- JSON response cleaning utilities for robust LLM output parsing
- Singleton pattern for efficient prompt loading and caching
- Environment-aware prompt selection (development/production variants)

Prompt Categories:
- goal_validation: Goal definition and validation prompts
- strategy_selection: Strategy planning and selection prompts
- function_execution: Function parameter resolution prompts
- data_analysis: Data synthesis and answer generation prompts
- confidence_scoring: LLM judge confidence assessment prompts
- error_handling: Error recovery and fallback prompts

Template Features:
- Variable substitution: {{query}}, {{context}}, {{data}}
- Conditional blocks: {% if condition %}...{% endif %}
- Template inheritance: base prompts with specialized extensions
- Multi-part prompts: system, user, and assistant message components
- Format validation: Ensure required template variables are present

JSON Response Processing:
- Automatic code fence removal (```json...```)
- Robust JSON extraction from noisy LLM responses
- Multiple parsing strategies with fallback handling
- Structured data validation for expected response formats

Usage Patterns:
- loader = get_prompt_loader()  # Singleton instance
- prompt = loader.format_prompt("goal_validation", query="...", context="...")
- cleaned_json = loader.clean_json_response(llm_response)
- template = loader.get_template("strategy_selection")

Design Principles:
- Centralized prompt management for consistency
- Template-driven approach for maintainability
- Robust error handling for production reliability
- Performance optimization with caching and lazy loading
"""



import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger("PROMPT_LOADER")


class PromptLoader:
    """
    Centralized prompt template management with YAML loading and variable substitution.

    Manages prompt templates for all LLM interactions in the agentic reasoning system.
    Provides template loading, variable substitution, and response processing utilities.
    
    Key Responsibilities:
    - Load prompt templates from YAML configuration files
    - Perform template variable substitution with validation
    - Clean and parse JSON responses from LLM outputs
    - Cache templates for performance optimization
    - Provide categorized access to prompt templates
    
    Template Structure:
    Each prompt template contains:
    - system: System-level instructions for the LLM
    - user: User message template with variable placeholders
    - examples: Optional few-shot examples for consistency
    - format: Expected response format specification
    
    Variable Substitution:
    Supports {{variable_name}} syntax for dynamic content insertion.
    Validates that all required variables are provided before formatting.
    """

    def __init__(self):
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> Dict[str, Any]:
        """Load prompts from the YAML configuration file."""
        try:
            prompt_file = Path(__file__).parent / "prompts.yaml"
            with open(prompt_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load prompts.yaml: {e}")
            return {}

    def get_prompt(
        self, category: str, prompt_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Get a prompt from the configuration.

        Args:
            category: The main category (e.g., 'goal_validation', 'strategy_selection')
            prompt_type: Optional sub-category for specific prompt types

        Returns:
            Dictionary containing 'system' and 'user_template' keys

        Example:
            >>> loader = PromptLoader()
            >>> prompts = loader.get_prompt("goal_validation")
            >>> system_prompt = prompts["system"]
            >>> user_template = prompts["user_template"]
        """
        try:
            if prompt_type:
                return self.prompts[category][prompt_type]
            return self.prompts[category]
        except KeyError as e:
            logger.error(f"Prompt not found: {category}.{prompt_type or ''} - {e}")
            return {
                "system": "You are a helpful AI assistant.",
                "user_template": "{query}",
            }

    def format_prompt(
        self, category: str, prompt_type: Optional[str] = None, **kwargs
    ) -> Dict[str, str]:
        """
        Get and format a prompt with the provided variables.

        Args:
            category: The main category
            prompt_type: Optional sub-category
            **kwargs: Variables to substitute in the template

        Returns:
            Dictionary with formatted 'system' and 'user' messages
        """
        prompts = self.get_prompt(category, prompt_type)

        try:
            formatted_user = prompts.get("user_template", "").format(**kwargs)
            return {"system": prompts.get("system", ""), "user": formatted_user}
        except KeyError as e:
            logger.error(f"Missing template variable for {category}: {e}")
            return {
                "system": prompts.get("system", ""),
                "user": prompts.get("user_template", ""),
            }

    def get_template(self, template_name: str) -> str:
        """Get a common template by name."""
        return self.prompts.get("templates", {}).get(template_name, "")

    def get_json_pattern(self, pattern_name: str) -> str:
        """Get a JSON cleaning pattern by name."""
        return self.prompts.get("json_patterns", {}).get(pattern_name, "")

    def clean_json_string(self, text: str) -> str:
        """
        Clean common JSON formatting issues from LLM responses using patterns from config.

        Handles:
        - Code block markers (```json, ```)
        - Escape sequence issues (\n, control characters)
        - Unicode quote characters
        - Leading/trailing whitespace
        """
        import re

        # Remove code block markers
        code_block_pattern = self.get_json_pattern("code_block_removal")
        if code_block_pattern:
            text = re.sub(code_block_pattern, "", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Fix common escape issues
        text = re.sub(r"\\n", " ", text)  # Replace literal \n with space
        text = re.sub(r"\n+", " ", text)  # Replace actual newlines with space

        # Remove control characters
        control_pattern = self.get_json_pattern("control_chars")
        if control_pattern:
            text = re.sub(control_pattern, " ", text)

        # Fix smart quotes to regular quotes
        text = re.sub(r"[\u201c\u201d]", '"', text)

        return text


# Global instance for easy access
_prompt_loader = None


def get_prompt_loader() -> PromptLoader:
    """Get the global prompt loader instance."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


