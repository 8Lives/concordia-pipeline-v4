"""
Spec Registry — Replaces the RAG layer with structured spec loading.

Usage:
    from spec_registry import SpecRegistry

    registry = SpecRegistry(spec_base_dir=Path("knowledge_base"), domain="DM")
"""

from .registry import SpecRegistry
from .models import (
    AllowedValue,
    CrossVariableRule,
    DomainQCCheck,
    DomainSpec,
    MappingPattern,
    MedDRALookup,
    NoOpTerminologyLookup,
    OutputSchemaEntry,
    PlausibilityBenchmark,
    ProvenanceFieldDef,
    ProvenanceRecord,
    SynonymMapping,
    SystemRules,
    TerminologyLookup,
    ValidationRule,
    ValueSet,
    VariableSpec,
)

__all__ = [
    "SpecRegistry",
    "AllowedValue",
    "CrossVariableRule",
    "DomainQCCheck",
    "DomainSpec",
    "MappingPattern",
    "MedDRALookup",
    "NoOpTerminologyLookup",
    "OutputSchemaEntry",
    "PlausibilityBenchmark",
    "ProvenanceFieldDef",
    "ProvenanceRecord",
    "SynonymMapping",
    "SystemRules",
    "TerminologyLookup",
    "ValidationRule",
    "ValueSet",
    "VariableSpec",
]
