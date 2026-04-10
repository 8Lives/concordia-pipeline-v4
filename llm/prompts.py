"""
LLM Prompt Templates — Spec-aware prompts for v4.

v4 prompts inject structured spec context (decision principles, allowed values,
mapping patterns) from the SpecRegistry rather than relying on RAG retrieval.

The LLM's role shifts from "resolve what RAG couldn't find" to "apply decision
principles to source data using full spec context."
"""

import json
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# System Prompts
# ---------------------------------------------------------------------------

SYSTEM_VALUE_RESOLUTION = """\
You are a clinical data standardization expert harmonizing source data values
to CDISC SDTM-aligned controlled terminology for the Demographics (DM) domain.

Rules:
1. ONLY map to values in the provided allowed_values list.
2. If the source value clearly matches one option, return that option.
3. If the source value is ambiguous but can be reasonably inferred using the
   decision principles, make the mapping and explain your reasoning.
4. If the value cannot be mapped with confidence, return null for resolved_value
   and set confidence to "UNMAPPED".
5. Use "HIGH" confidence for direct matches and clean code decodes.
6. Use "MEDIUM" for synonym resolution and minor normalization.
7. Use "LOW" for inferred or ambiguous mappings.
8. Use "UNMAPPED" when the value cannot be resolved.
"""

SYSTEM_REVIEW = """\
You are a senior clinical data manager reviewing harmonized trial data
for the Demographics (DM) domain.

IMPORTANT: Use the following stoplight grading rules, NOT generic SDTM rules.

## STOPLIGHT GRADING RULES:

**GREEN** — All 5 core variables are present and populated:
  1. SEX
  2. RACE
  3. ETHNIC
  4. AGE or AGEGP (at least one)
  5. COUNTRY

**YELLOW** — Missing no more than 2 of the 5 core variables, OR flagged
formatting issues with any core variable.

**RED** — Missing 3 or more of the 5 core variables.

Focus ONLY on the 5 core variables. Other variables should not affect the
stoplight grade. The stoplight is informational — it does not halt the pipeline.
"""

SYSTEM_RACE_ETHNICITY_SEPARATION = """\
You are a clinical data expert specializing in race/ethnicity data
harmonization per OMB (Office of Management and Budget) standards.

Race and ethnicity are INDEPENDENT concepts:
- RACE: Biological/social grouping — White, Black or African American, Asian,
  American Indian or Alaska Native, Native Hawaiian or Other Pacific Islander,
  Multiple, Unknown
- ETHNIC: Cultural/ethnic grouping — Hispanic or Latino, Not Hispanic or Latino,
  Unknown

Source data frequently conflates these. Your task is to SEPARATE them correctly.
"""


# ---------------------------------------------------------------------------
# User Prompt Builders
# ---------------------------------------------------------------------------

def build_value_resolution_prompt(
    variable: str,
    value: str,
    allowed_values: List[str],
    spec_context: str = "",
    decision_principles: str = "",
    mapping_patterns: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Build a prompt for resolving an ambiguous value using spec context.

    Args:
        variable: Target variable name (e.g., "RACE")
        value: The ambiguous source value
        allowed_values: List of valid target values from the spec
        spec_context: Full spec context from VariableSpec.get_llm_context()
        decision_principles: Decision principles text from the variable spec
        mapping_patterns: Representative mapping patterns from the spec

    Returns:
        Formatted user prompt string
    """
    parts = [f"Map the following source value to a standardized term.\n"]
    parts.append(f"Variable: {variable}")
    parts.append(f'Source Value: "{value}"')
    parts.append(f"Allowed Target Values: {json.dumps(allowed_values)}")

    if decision_principles:
        parts.append(f"\n## Decision Principles\n{decision_principles}")

    if mapping_patterns:
        parts.append("\n## Representative Mapping Patterns")
        for mp in mapping_patterns[:10]:
            parts.append(
                f'- "{mp["source"]}" → {mp["target"]} '
                f'(confidence: {mp.get("confidence", "HIGH")})'
            )

    if spec_context:
        parts.append(f"\n## Full Variable Specification\n{spec_context}")

    parts.append("""
Respond in JSON format:
{
    "resolved_value": "<matched value from allowed list, or null if unmappable>",
    "confidence": "HIGH|MEDIUM|LOW|UNMAPPED",
    "reasoning": "<brief explanation of mapping decision>"
}""")

    return "\n".join(parts)


def build_review_prompt(
    data_sample: List[Dict[str, Any]],
    column_stats: Dict[str, Dict[str, Any]],
    qc_issues: List[Dict[str, Any]],
    stoplight_criteria: str = "",
    cross_variable_rules: Optional[List[str]] = None,
) -> str:
    """
    Build a prompt for the Review Agent's stoplight assessment.

    Args:
        data_sample: Sample rows (5-10) from harmonized data
        column_stats: Per-column statistics (presence, completeness)
        qc_issues: Pre-identified QC issues
        stoplight_criteria: Raw stoplight criteria text from domain spec
        cross_variable_rules: Cross-variable dependency rules

    Returns:
        Formatted user prompt string
    """
    parts = ["Review this harmonized Demographics (DM) dataset.\n"]

    parts.append("## Data Sample:")
    parts.append(f"```json\n{json.dumps(data_sample[:5], indent=2, default=str)}\n```\n")

    parts.append("## Column Statistics:")
    parts.append(f"```json\n{json.dumps(column_stats, indent=2, default=str)}\n```\n")

    if qc_issues:
        parts.append(f"## Pre-identified QC Issues ({len(qc_issues)} total):")
        parts.append(f"```json\n{json.dumps(qc_issues[:10], indent=2, default=str)}\n```\n")

    if stoplight_criteria:
        parts.append(f"## Stoplight Criteria from Spec:\n{stoplight_criteria}\n")

    if cross_variable_rules:
        parts.append("## Cross-Variable Rules:")
        for rule in cross_variable_rules:
            parts.append(f"- {rule}")
        parts.append("")

    parts.append("""Provide your review in JSON:
{
    "stoplight": "GREEN|YELLOW|RED",
    "core_variables_present": ["list present core variables"],
    "core_variables_missing": ["list missing core variables"],
    "core_variables_count": 0,
    "formatting_issues": ["list formatting issues"],
    "overall_quality": "good|acceptable|needs_attention|poor",
    "critical_issues": [
        {"issue": "description", "severity": "critical|high|medium", "recommendation": "fix"}
    ],
    "approval": "GREEN|YELLOW|RED",
    "reason": "Brief explanation of stoplight grade",
    "recommendations": ["actionable improvements"]
}""")

    return "\n".join(parts)


def build_race_ethnicity_separation_prompt(
    source_value: str,
    source_field_name: str,
    allowed_race_values: List[str],
    allowed_ethnic_values: List[str],
    spec_context: str = "",
) -> str:
    """
    Build a prompt for separating combined race/ethnicity source fields.

    Per DM_RACE.md Section 3.2, combined fields like "White, Hispanic"
    need to be separated into independent RACE and ETHNIC values.

    Args:
        source_value: The raw source value (e.g., "White, Hispanic")
        source_field_name: Original column name (e.g., "RACE_ETHNICITY")
        allowed_race_values: Valid race values from spec
        allowed_ethnic_values: Valid ethnicity values from spec
        spec_context: Additional spec context

    Returns:
        Formatted user prompt string
    """
    parts = ["Separate the following combined race/ethnicity value.\n"]
    parts.append(f'Source Field: "{source_field_name}"')
    parts.append(f'Source Value: "{source_value}"')
    parts.append(f"\nAllowed RACE Values: {json.dumps(allowed_race_values)}")
    parts.append(f"Allowed ETHNIC Values: {json.dumps(allowed_ethnic_values)}")

    if spec_context:
        parts.append(f"\n## Separation Rules\n{spec_context}")

    parts.append("""
Race and ethnicity are INDEPENDENT per OMB standards:
- "Hispanic" is an ETHNICITY, not a race
- A person can be "White" AND "Hispanic or Latino"
- "African American" is a RACE, regardless of ethnicity

Respond in JSON:
{
    "race_value": "<extracted race from allowed list, or 'Unknown'>",
    "ethnic_value": "<extracted ethnicity from allowed list, or 'Unknown'>",
    "race_confidence": "HIGH|MEDIUM|LOW|UNMAPPED",
    "ethnic_confidence": "HIGH|MEDIUM|LOW|UNMAPPED",
    "race_ethnicity_conflated": true,
    "reasoning": "<brief explanation>"
}""")

    return "\n".join(parts)


def build_batch_resolution_prompt(
    variable: str,
    unique_values: List[str],
    allowed_values: List[str],
    synonym_lookup: Dict[str, str],
    decision_principles: str = "",
) -> str:
    """
    Build a prompt for batch-resolving multiple unique values at once.

    More efficient than one-by-one resolution when many unique values
    need LLM inference. Pre-filters values already in the synonym lookup.

    Args:
        variable: Target variable name
        unique_values: List of unique source values needing resolution
        allowed_values: Valid target values
        synonym_lookup: Pre-built synonym lookup (already checked)
        decision_principles: Decision principles from spec

    Returns:
        Formatted user prompt string
    """
    parts = [f"Map each source value for {variable} to a standardized term.\n"]
    parts.append(f"Allowed Target Values: {json.dumps(allowed_values)}")

    if decision_principles:
        parts.append(f"\n## Decision Principles\n{decision_principles}")

    parts.append("\n## Values to Resolve")
    for i, val in enumerate(unique_values[:50]):  # cap at 50
        parts.append(f"{i+1}. \"{val}\"")

    parts.append("""
For each value, respond in JSON array format:
[
    {
        "source_value": "<original>",
        "resolved_value": "<matched value or null>",
        "confidence": "HIGH|MEDIUM|LOW|UNMAPPED",
        "reasoning": "<brief>"
    },
    ...
]""")

    return "\n".join(parts)
