"""
Configuration Settings for Concordia Pipeline v4

Centralizes all configuration including:
    - LLM configuration
    - Spec registry paths
    - Processing parameters

Ported from concordia_pipeline_v3_branded/config/settings.py
with RAG/embedding configuration removed.

Usage:
    from config import get_settings

    settings = get_settings()
    print(settings.spec_base_dir)
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """Application settings with defaults."""

    # === LLM Configuration ===
    anthropic_api_key: Optional[str] = None
    llm_model: str = "claude-sonnet-4-20250514"  # Default to Sonnet for cost efficiency
    llm_orchestrator_model: str = "claude-opus-4-5-20251101"  # Opus for orchestration

    # === Paths ===
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    spec_base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "knowledge_base")
    output_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "output")

    # === Domain Configuration ===
    target_domain: str = "DM"

    # === Processing Parameters ===
    agent_timeout_seconds: int = 120
    max_retries: int = 1
    batch_size: int = 100

    # === Feature Flags ===
    use_llm_fallback: bool = True
    enable_review_agent: bool = True
    verbose_logging: bool = False

    def __post_init__(self):
        """Initialize paths and load environment variables."""
        # Convert string paths to Path objects if needed
        if isinstance(self.base_dir, str):
            self.base_dir = Path(self.base_dir)
        if isinstance(self.spec_base_dir, str):
            self.spec_base_dir = Path(self.spec_base_dir)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        # Load API keys from environment if not set
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> bool:
        """Validate settings and return True if valid."""
        errors = []

        # Check spec directory exists
        if not self.spec_base_dir.exists():
            errors.append(f"Spec base directory not found: {self.spec_base_dir}")

        # Check domain spec directory exists
        domain_dir = self.spec_base_dir / self.target_domain
        if not domain_dir.exists():
            errors.append(f"Domain spec directory not found: {domain_dir}")

        # Check LLM configuration if LLM features enabled
        if self.use_llm_fallback and not self.anthropic_api_key:
            logger.warning("Anthropic API key not set - LLM fallback will be disabled")

        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False

        return True

    def get_domain_spec_dir(self) -> Path:
        """Get path to the domain specification directory."""
        return self.spec_base_dir / self.target_domain

    def get_system_rules_path(self) -> Path:
        """Get path to the system rules file."""
        return self.spec_base_dir / "system_rules.md"

    def get_domain_rules_path(self) -> Path:
        """Get path to domain-level rules file."""
        return self.get_domain_spec_dir() / f"{self.target_domain}_domain_rules.md"

    def get_value_sets_dir(self) -> Path:
        """Get path to value sets directory."""
        return self.get_domain_spec_dir() / "value_sets"


# Singleton instance
_settings: Optional[Settings] = None


def get_settings(**overrides) -> Settings:
    """
    Get the settings instance, creating if needed.

    Args:
        **overrides: Override any default settings

    Returns:
        Settings instance
    """
    global _settings

    if _settings is None or overrides:
        # Load from environment
        env_settings = {
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
            "verbose_logging": os.getenv("VERBOSE_LOGGING", "").lower() == "true",
        }

        # Remove None values
        env_settings = {k: v for k, v in env_settings.items() if v is not None}

        # Merge with overrides
        env_settings.update(overrides)

        _settings = Settings(**env_settings)

    return _settings


def reset_settings():
    """Reset the settings singleton (useful for testing)."""
    global _settings
    _settings = None
