"""
Spec Registry — The central lookup interface for all specification data.

Replaces the entire RAG layer (vector_store, embeddings, indexer, retriever)
from v3 with a simple in-memory registry backed by parsed markdown specs.

Usage:
    from spec_registry import SpecRegistry

    registry = SpecRegistry(spec_base_dir=Path("knowledge_base"), domain="DM")

    # Agent-facing lookups
    valid = registry.get_valid_values("SEX")          # ["Male", "Female", "Unknown", "Undifferentiated"]
    cols  = registry.get_source_columns("RACE")        # ["RACE", "RACECD", "RACEN", ...]
    ctx   = registry.get_llm_context("SEX")            # Formatted text for LLM prompt injection
    schema = registry.get_output_schema()              # ["TRIAL", "SUBJID", "SEX", ...]
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .loader import load_domain
from .models import (
    DomainSpec,
    SystemRules,
    VariableSpec,
    CrossVariableRule,
    DomainQCCheck,
    ValueSet,
)

logger = logging.getLogger(__name__)


class SpecRegistry:
    """
    Central registry for specification data. Loads and caches all specs
    at initialization time. Domain-parameterized for AE extensibility.
    """

    def __init__(self, spec_base_dir: Path, domain: str = "DM"):
        """
        Initialize the registry by loading all specs for the given domain.

        Args:
            spec_base_dir: Path to knowledge_base/ directory
            domain: Domain code (e.g., "DM", "AE")

        Raises:
            FileNotFoundError: If required spec files are missing
        """
        self.spec_base_dir = Path(spec_base_dir)
        self.domain = domain

        logger.info(f"Initializing SpecRegistry for domain '{domain}' "
                     f"from {spec_base_dir}")

        self._system_rules, self._domain_spec = load_domain(domain, self.spec_base_dir)

        logger.info(f"SpecRegistry ready: {len(self._domain_spec.variable_specs)} variables, "
                     f"{len(self._domain_spec.output_schema)} schema entries")

    # -------------------------------------------------------------------
    # Variable-level lookups
    # -------------------------------------------------------------------

    def get_variable_spec(self, variable: str) -> Optional[VariableSpec]:
        """Get the full VariableSpec for a given variable name."""
        return self._domain_spec.variable_specs.get(variable)

    def get_valid_values(self, variable: str) -> List[str]:
        """
        Get the list of allowed target values for a variable.
        Returns empty list for non-categorical variables (e.g., AGE).
        """
        spec = self.get_variable_spec(variable)
        if spec is None:
            logger.warning(f"No spec found for variable '{variable}'")
            return []
        return spec.get_allowed_value_list()

    def get_source_columns(self, variable: str) -> List[str]:
        """Get the ordered source column priority list for a variable."""
        spec = self.get_variable_spec(variable)
        if spec is None:
            return []
        return spec.source_priority

    def get_synonym_lookup(self, variable: str) -> Dict[str, str]:
        """
        Get a case-insensitive synonym lookup dict for a variable.
        Keys are lowercase source values, values are target values.
        """
        spec = self.get_variable_spec(variable)
        if spec is None:
            return {}
        return spec.build_synonym_lookup()

    def get_mapping_patterns(self, variable: str) -> List[Dict[str, str]]:
        """Get representative mapping patterns for a variable."""
        spec = self.get_variable_spec(variable)
        if spec is None:
            return []
        return [
            {"source": mp.source_value, "target": mp.target_value,
             "confidence": mp.confidence, "notes": mp.notes}
            for mp in spec.mapping_patterns
        ]

    def get_missing_value(self, variable: str) -> str:
        """Get the missing/unknown value for a variable (e.g., 'Unknown' or '')."""
        spec = self.get_variable_spec(variable)
        if spec is None:
            return "Unknown"
        return spec.missing_value

    def get_provenance_field_defs(self, variable: str) -> List[Dict[str, str]]:
        """Get variable-specific provenance field definitions."""
        spec = self.get_variable_spec(variable)
        if spec is None:
            return []
        return [
            {"name": pf.name, "type": pf.type, "description": pf.description}
            for pf in spec.provenance_fields
        ]

    def get_llm_context(self, variable: str) -> str:
        """
        Get formatted spec context for LLM prompt injection.
        Includes decision principles, representative patterns, and allowed values.
        """
        spec = self.get_variable_spec(variable)
        if spec is None:
            return f"No specification found for variable '{variable}'."
        return spec.get_llm_context()

    # -------------------------------------------------------------------
    # Domain-level lookups
    # -------------------------------------------------------------------

    def get_output_schema(self) -> List[str]:
        """Get the ordered list of output variable names."""
        return self._domain_spec.get_output_variable_order()

    def get_required_variables(self) -> List[str]:
        """Get list of variables marked as Required."""
        return self._domain_spec.get_required_variables()

    def get_output_schema_entries(self) -> List[Dict[str, Any]]:
        """Get full output schema with all metadata."""
        return [
            {"order": e.order, "variable": e.variable,
             "data_type": e.data_type, "required": e.required,
             "description": e.description}
            for e in sorted(self._domain_spec.output_schema, key=lambda x: x.order)
        ]

    def get_cross_variable_rules(self) -> List[CrossVariableRule]:
        """Get all cross-variable dependency rules."""
        return self._domain_spec.cross_variable_rules

    def get_domain_qc_checks(self) -> List[DomainQCCheck]:
        """Get all domain-level QC check definitions."""
        return self._domain_spec.domain_qc_checks

    def get_stoplight_criteria(self) -> str:
        """Get the stoplight assessment criteria text."""
        return self._domain_spec.stoplight_criteria

    def get_all_variables(self) -> List[str]:
        """Get list of all variable names with specs loaded."""
        return list(self._domain_spec.variable_specs.keys())

    def get_coded_variables(self) -> List[str]:
        """Get list of variables that have allowed value sets (categorical)."""
        coded = []
        for name, spec in self._domain_spec.variable_specs.items():
            if spec.get_allowed_value_list():
                coded.append(name)
        return coded

    # -------------------------------------------------------------------
    # System-level lookups
    # -------------------------------------------------------------------

    def get_system_rules(self) -> SystemRules:
        """Get the full SystemRules object."""
        return self._system_rules

    def get_domain_spec(self) -> DomainSpec:
        """Get the full DomainSpec object."""
        return self._domain_spec

    def get_confidence_definitions(self) -> Dict[str, str]:
        """Get confidence grade definitions from system rules."""
        return self._system_rules.get_confidence_definitions()

    # -------------------------------------------------------------------
    # Convenience
    # -------------------------------------------------------------------

    def get_domain_grain(self) -> str:
        """Get the domain grain description (e.g., 'One record per subject per trial')."""
        return self._domain_spec.grain

    def __repr__(self) -> str:
        return (f"SpecRegistry(domain='{self.domain}', "
                f"variables={len(self._domain_spec.variable_specs)}, "
                f"schema_entries={len(self._domain_spec.output_schema)})")
