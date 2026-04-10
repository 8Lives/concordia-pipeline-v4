"""
LLM Module — Claude API integration and prompt templates.

Usage:
    from llm.service import LLMService
    from llm.prompts import build_value_resolution_prompt
"""

from .service import LLMService, LLMResponse, LLMModel
from .prompts import (
    SYSTEM_VALUE_RESOLUTION,
    SYSTEM_REVIEW,
    SYSTEM_RACE_ETHNICITY_SEPARATION,
    build_value_resolution_prompt,
    build_review_prompt,
    build_race_ethnicity_separation_prompt,
    build_batch_resolution_prompt,
)

__all__ = [
    "LLMService",
    "LLMResponse",
    "LLMModel",
    "SYSTEM_VALUE_RESOLUTION",
    "SYSTEM_REVIEW",
    "SYSTEM_RACE_ETHNICITY_SEPARATION",
    "build_value_resolution_prompt",
    "build_review_prompt",
    "build_race_ethnicity_separation_prompt",
    "build_batch_resolution_prompt",
]
