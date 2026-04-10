"""
Pipeline Agents — 5-agent architecture for clinical data harmonization.

    Ingest → Map → Harmonize → QC → Review

All agents extend AgentBase and accept a domain-parameterized SpecRegistry.
"""

from .base import AgentBase, AgentConfig, AgentResult, PipelineContext, ProgressCallback
from .ingest_agent import IngestAgent
from .map_agent import MapAgent
from .harmonize_agent import HarmonizeAgent
from .qc_agent import QCAgent
from .review_agent import ReviewAgent

__all__ = [
    "AgentBase",
    "AgentConfig",
    "AgentResult",
    "PipelineContext",
    "ProgressCallback",
    "IngestAgent",
    "MapAgent",
    "HarmonizeAgent",
    "QCAgent",
    "ReviewAgent",
]
