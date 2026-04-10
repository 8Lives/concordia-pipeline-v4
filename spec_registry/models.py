"""
Spec Registry Data Models

Dataclasses representing the three-tier specification hierarchy:
    System Rules → Domain Rules → Variable Specs + Value Sets

These models are domain-agnostic. VariableSpec and DomainSpec work
for any domain (DM, AE, etc.).
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


# ---------------------------------------------------------------------------
# Value Set Models
# ---------------------------------------------------------------------------

@dataclass
class AllowedValue:
    """A single allowed target value for a categorical variable."""
    value: str
    definition: str = ""
    cdisc_code: str = ""
    notes: str = ""


@dataclass
class SynonymMapping:
    """A known source-to-target synonym mapping from a value set file."""
    source_values: List[str]  # e.g., ["Male", "male", "MALE", "M", "m"]
    target_value: str         # e.g., "Male"
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    first_seen: str = ""
    notes: str = ""


@dataclass
class ValueSet:
    """
    A complete value set: allowed target values + known source synonyms.
    Loaded from value_sets/*.md files.
    """
    name: str                                # e.g., "sex_values"
    version: str = ""
    cdisc_reference: str = ""
    allowed_values: List[AllowedValue] = field(default_factory=list)
    synonym_mappings: List[SynonymMapping] = field(default_factory=list)

    def get_allowed_value_list(self) -> List[str]:
        """Return just the string values (e.g., ['Male', 'Female', 'Unknown', 'Undifferentiated'])."""
        return [av.value for av in self.allowed_values]

    def build_synonym_lookup(self) -> Dict[str, str]:
        """
        Build a case-insensitive lookup dict: normalized source value → target value.
        Handles comma-separated source values in synonym mappings.

        Spec "Maps To" values are expected to be clean canonical values.
        """
        lookup = {}
        for sm in self.synonym_mappings:
            for sv in sm.source_values:
                lookup[sv.strip().lower()] = sm.target_value
        return lookup


# ---------------------------------------------------------------------------
# Variable Spec Models
# ---------------------------------------------------------------------------

@dataclass
class MappingPattern:
    """A representative source→target mapping pattern from a variable spec."""
    source_value: str
    target_value: str
    confidence: str = "HIGH"
    notes: str = ""


@dataclass
class ProvenanceFieldDef:
    """Definition of a variable-specific provenance field."""
    name: str
    type: str = "Boolean"   # Boolean, String, String/Array, etc.
    description: str = ""


@dataclass
class ValidationRule:
    """A validation rule from Section 6 of a variable spec."""
    category: str      # "Conformance", "Plausibility", "Determinism", "Separation Check"
    description: str
    threshold: Optional[str] = None   # e.g., "< 5%", "30/70 to 70/30"
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlausibilityBenchmark:
    """A distribution plausibility benchmark for a specific value."""
    value: str
    min_pct: Optional[float] = None
    max_pct: Optional[float] = None
    investigation_trigger: str = ""


@dataclass
class VariableSpec:
    """
    Complete specification for a single harmonized variable.
    Loaded from DM_SEX.md, DM_RACE.md, etc.
    """
    # Identity
    variable: str               # e.g., "SEX"
    domain: str = ""            # e.g., "DM"
    order: int = 0
    required: str = "Optional"  # "Yes", "No", "Conditional", "Optional"
    version: str = ""
    definition: str = ""
    sdtm_reference: str = ""

    # Values
    data_type: str = "String (categorical)"  # or "Numeric", "Date (ISO 8601)", "String"
    allowed_values: List[AllowedValue] = field(default_factory=list)
    value_set: Optional[ValueSet] = None  # linked value set file if applicable
    missing_value: str = "Unknown"  # what to use when source is null/missing

    # Mapping
    source_priority: List[str] = field(default_factory=list)
    mapping_patterns: List[MappingPattern] = field(default_factory=list)
    decision_principles: str = ""  # raw text for LLM context injection

    # Business rules
    business_rules: str = ""  # raw text of Section 4

    # Provenance
    provenance_fields: List[ProvenanceFieldDef] = field(default_factory=list)

    # Validation
    validation_rules: List[ValidationRule] = field(default_factory=list)
    plausibility_benchmarks: List[PlausibilityBenchmark] = field(default_factory=list)

    # Known limitations
    known_limitations: str = ""

    # Full raw text for LLM context
    _raw_spec_text: str = field(default="", repr=False)

    def get_allowed_value_list(self) -> List[str]:
        """Return allowed values as a simple string list."""
        if self.value_set:
            return self.value_set.get_allowed_value_list()
        return [av.value for av in self.allowed_values]

    def build_synonym_lookup(self) -> Dict[str, str]:
        """Build synonym lookup from linked value set."""
        if self.value_set:
            return self.value_set.build_synonym_lookup()
        return {}

    def get_llm_context(self) -> str:
        """
        Build formatted context string for LLM prompt injection.
        Includes decision principles, representative patterns, and allowed values.
        """
        parts = [f"## Variable: {self.variable}"]
        parts.append(f"Definition: {self.definition}")

        # Allowed values
        avs = self.get_allowed_value_list()
        if avs:
            parts.append(f"\nAllowed target values: {avs}")

        # Decision principles
        if self.decision_principles:
            parts.append(f"\n### Mapping Decision Principles\n{self.decision_principles}")

        # Representative patterns
        if self.mapping_patterns:
            parts.append("\n### Representative Mapping Patterns")
            for mp in self.mapping_patterns:
                parts.append(f"- \"{mp.source_value}\" → {mp.target_value} (confidence: {mp.confidence}) {mp.notes}")

        # Business rules
        if self.business_rules:
            parts.append(f"\n### Business Rules\n{self.business_rules}")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Domain Spec Models
# ---------------------------------------------------------------------------

@dataclass
class CrossVariableRule:
    """A cross-variable dependency rule from domain rules."""
    name: str           # e.g., "AGE / AGEGP Conditional Logic"
    variables: List[str]  # e.g., ["AGE", "AGEGP", "AGEU"]
    rule_text: str      # raw rule text including any pseudocode
    section: str = ""   # e.g., "4.1"


@dataclass
class DomainQCCheck:
    """A domain-level QC check from domain rules."""
    name: str           # e.g., "Duplicate Subject Detection"
    check_id: str = ""  # e.g., "DUPLICATE_SUBJECT"
    description: str = ""
    section: str = ""


@dataclass
class OutputSchemaEntry:
    """A single entry in the domain output schema."""
    order: int
    variable: str
    data_type: str = ""
    required: str = "Optional"
    description: str = ""


@dataclass
class DomainSpec:
    """
    Domain-level specification (e.g., DM domain rules).
    Contains output schema, cross-variable dependencies, and domain QC.
    """
    domain: str                    # e.g., "DM"
    version: str = ""
    grain: str = ""                # e.g., "One record per subject per trial"
    controlling_standard: str = ""

    # Output schema
    output_schema: List[OutputSchemaEntry] = field(default_factory=list)

    # Cross-variable rules
    cross_variable_rules: List[CrossVariableRule] = field(default_factory=list)

    # Domain-level QC
    domain_qc_checks: List[DomainQCCheck] = field(default_factory=list)

    # Stoplight criteria
    stoplight_criteria: str = ""  # raw text of stoplight rules

    # Variable specs (populated by registry)
    variable_specs: Dict[str, VariableSpec] = field(default_factory=dict)

    def get_output_variable_order(self) -> List[str]:
        """Return variable names in schema order."""
        return [e.variable for e in sorted(self.output_schema, key=lambda x: x.order)]

    def get_required_variables(self) -> List[str]:
        """Return variables marked as Required."""
        return [e.variable for e in self.output_schema if e.required == "Yes"]


# ---------------------------------------------------------------------------
# System Rules Model
# ---------------------------------------------------------------------------

@dataclass
class SystemRules:
    """
    System-level rules that apply across all domains and variables.
    Loaded from system_rules.md.
    """
    version: str = ""
    text_normalization: str = ""     # Section 1 raw text
    null_handling: str = ""          # Section 2 raw text
    date_handling: str = ""          # Section 3 raw text
    numeric_handling: str = ""       # Section 4 raw text
    code_decoding: str = ""          # Section 5 raw text
    confidence_grading: str = ""     # Section 6 raw text
    standard_provenance: str = ""    # Section 7 raw text
    transformation_report: str = ""  # Section 8 raw text
    _raw_text: str = field(default="", repr=False)

    def get_confidence_definitions(self) -> Dict[str, str]:
        """Extract confidence grade definitions."""
        return {
            "HIGH": "Direct match or clean code decode via data dictionary. No ambiguity.",
            "MEDIUM": "Synonym resolution, case normalization, minor abbreviation expansion.",
            "LOW": "LLM inference from ambiguous, free-text, or non-standard source values.",
            "UNMAPPED": "Source value could not be resolved to any allowed target value.",
        }


# ---------------------------------------------------------------------------
# Provenance Record (output model, not a spec model)
# ---------------------------------------------------------------------------

@dataclass
class ProvenanceRecord:
    """
    Provenance record for a single harmonized value.
    Generated during harmonization, not loaded from specs.
    """
    variable: str
    source_dataset_id: str = ""
    source_field_name: str = ""
    source_value_raw: str = ""
    harmonized_value: str = ""
    mapping_confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, UNMAPPED
    mapping_notes: Optional[str] = None
    # Variable-specific flags (e.g., sex_gender_conflated, race_ethnicity_conflated)
    flags: Dict[str, Any] = field(default_factory=dict)

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flatten to a dict suitable for DataFrame row, expanding flags."""
        d = {
            "variable": self.variable,
            "source_dataset_id": self.source_dataset_id,
            "source_field_name": self.source_field_name,
            "source_value_raw": self.source_value_raw,
            "harmonized_value": self.harmonized_value,
            "mapping_confidence": self.mapping_confidence,
            "mapping_notes": self.mapping_notes or "",
        }
        for k, v in self.flags.items():
            d[f"flag_{k}"] = v
        return d


# ---------------------------------------------------------------------------
# AE-Readiness: External Terminology Interface (stub)
# ---------------------------------------------------------------------------

class TerminologyLookup(ABC):
    """
    Abstract interface for external coded terminology lookups.

    DM domain does not use external dictionaries beyond its own value sets,
    so the DM implementation is a no-op. AE domain will implement this for
    MedDRA (Medical Dictionary for Regulatory Activities) and potentially
    CTCAE (Common Terminology Criteria for Adverse Events).

    The interface is defined here to avoid rework when AE is added.
    """

    @abstractmethod
    def lookup(self, term: str, dictionary: str) -> Optional[Dict[str, Any]]:
        """
        Look up an exact term in an external dictionary.

        Args:
            term: The term to look up (e.g., "Headache")
            dictionary: Dictionary name (e.g., "MedDRA", "CTCAE")

        Returns:
            Dict with matched term info, or None if not found.
        """
        pass

    @abstractmethod
    def search(self, query: str, dictionary: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fuzzy search for a term in an external dictionary.

        Args:
            query: Search query
            dictionary: Dictionary name
            max_results: Maximum results to return

        Returns:
            List of matching terms with scores.
        """
        pass


class NoOpTerminologyLookup(TerminologyLookup):
    """No-op implementation for domains that don't use external dictionaries (e.g., DM)."""

    def lookup(self, term: str, dictionary: str) -> Optional[Dict[str, Any]]:
        return None

    def search(self, query: str, dictionary: str, max_results: int = 10) -> List[Dict[str, Any]]:
        return []


class MedDRALookup(TerminologyLookup):
    """
    MedDRA terminology lookup stub for AE domain.

    When fully implemented, this will connect to a MedDRA database or API
    to resolve adverse event terms to their Preferred Terms (PT),
    Lower Level Terms (LLT), High Level Terms (HLT), High Level Group
    Terms (HLGT), and System Organ Classes (SOC).

    The stub accepts an optional in-memory dict for testing and early
    development before a full MedDRA subscription is integrated.

    Usage:
        # With pre-loaded terms (for dev/testing)
        lookup = MedDRALookup(preloaded_terms={
            "headache": {"pt": "Headache", "soc": "Nervous system disorders", "llt": "Headache"},
        })
        result = lookup.lookup("headache", "MedDRA")

        # Empty stub (returns None for all lookups)
        lookup = MedDRALookup()
    """

    def __init__(self, preloaded_terms: Optional[Dict[str, Dict[str, Any]]] = None):
        """
        Args:
            preloaded_terms: Optional dict mapping lowercase term → MedDRA hierarchy.
                Expected value format: {"pt": str, "llt": str, "hlt": str, "hlgt": str, "soc": str}
        """
        self._terms: Dict[str, Dict[str, Any]] = {}
        if preloaded_terms:
            for key, val in preloaded_terms.items():
                self._terms[key.strip().lower()] = val

    def lookup(self, term: str, dictionary: str = "MedDRA") -> Optional[Dict[str, Any]]:
        """
        Exact-match lookup of a term in MedDRA.

        Returns dict with MedDRA hierarchy fields if found:
            {"pt": "Headache", "llt": "Headache", "hlt": "Headaches",
             "hlgt": "Headaches", "soc": "Nervous system disorders",
             "match_type": "exact"}
        """
        if dictionary.upper() != "MEDDRA":
            return None
        key = term.strip().lower()
        match = self._terms.get(key)
        if match:
            return {**match, "match_type": "exact", "source_term": term}
        return None

    def search(self, query: str, dictionary: str = "MedDRA", max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Fuzzy search for a term in MedDRA. Returns scored matches.

        Current stub: simple substring matching against preloaded terms.
        Full implementation would use Levenshtein distance or MedDRA's
        own search API.
        """
        if dictionary.upper() != "MEDDRA":
            return []
        query_lower = query.strip().lower()
        results = []
        for key, val in self._terms.items():
            if query_lower in key or key in query_lower:
                results.append({
                    **val,
                    "match_type": "substring",
                    "source_term": query,
                    "score": 1.0 if key == query_lower else 0.5,
                })
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:max_results]
