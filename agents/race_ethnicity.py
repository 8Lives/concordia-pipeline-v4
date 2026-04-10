"""
Race / Ethnicity Separation Logic (v4)

Per DM_RACE.md Section 3.2, source data frequently conflates race and ethnicity
into a single field (e.g., "White, Hispanic" or "RACE_ETHNICITY"). This module
implements the separation logic as a reusable component.

Key rules (per OMB standards):
- Race and ethnicity are INDEPENDENT concepts
- "Hispanic" / "Latino" is an ETHNICITY, not a race
- A person can be "White" AND "Hispanic or Latino"
- When source conflates, separate deterministically where possible
- Flag race_ethnicity_conflated=True on provenance

Resolution order:
1. Deterministic keyword-based separation (no LLM needed)
2. LLM inference for ambiguous cases (with decision-principle context)
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


# Ethnicity keywords (case-insensitive)
_ETHNIC_KEYWORDS = [
    "hispanic", "latino", "latina", "latinx",
    "not hispanic", "non-hispanic", "non hispanic",
    "not latino", "non-latino",
]

# Known race→ethnicity conflations that can be deterministically split
_RACE_ETHNIC_PATTERNS = {
    # "White, Hispanic" → Race=White, Ethnic=Hispanic or Latino
    r"(?i)^(white|caucasian)\s*[,/;]\s*(hispanic|latino)": ("White", "Hispanic or Latino"),
    r"(?i)^(black|african\s*american)\s*[,/;]\s*(hispanic|latino)": ("Black or African American", "Hispanic or Latino"),
    r"(?i)^(asian)\s*[,/;]\s*(hispanic|latino)": ("Asian", "Hispanic or Latino"),
    # "Hispanic White" → Race=White, Ethnic=Hispanic or Latino
    r"(?i)^(hispanic|latino)\s*[,/;]?\s*(white|caucasian)": ("White", "Hispanic or Latino"),
    r"(?i)^(hispanic|latino)\s*[,/;]?\s*(black|african\s*american)": ("Black or African American", "Hispanic or Latino"),
    # "White, Non-Hispanic" → Race=White, Ethnic=Not Hispanic or Latino
    r"(?i)^(white|caucasian)\s*[,/;]\s*(not?\s*hispanic|non[\s-]?hispanic)": ("White", "Not Hispanic or Latino"),
    r"(?i)^(black|african\s*american)\s*[,/;]\s*(not?\s*hispanic|non[\s-]?hispanic)": ("Black or African American", "Not Hispanic or Latino"),
}


def is_conflated_field(field_name: str, values: pd.Series) -> bool:
    """
    Detect whether a source field conflates race and ethnicity.

    Heuristics:
    1. Field name contains both "race" and "eth"
    2. Values contain ethnicity keywords alongside race values
    """
    name_lower = field_name.lower()

    # Field name check
    if "race" in name_lower and "eth" in name_lower:
        return True
    if name_lower in ("race_ethnicity", "raceethnic", "race_ethnic"):
        return True

    # Value check: sample unique values for ethnicity keywords
    sample = values.dropna().unique()[:50]
    for val in sample:
        val_lower = str(val).lower()
        for keyword in _ETHNIC_KEYWORDS:
            if keyword in val_lower:
                return True

    return False


def separate_race_ethnicity(
    source_value: str,
    allowed_race_values: List[str],
    allowed_ethnic_values: List[str],
    race_synonym_lookup: Optional[Dict[str, str]] = None,
) -> Tuple[str, str, str, str, bool]:
    """
    Separate a conflated race/ethnicity value into independent RACE and ETHNIC.

    Returns:
        Tuple of (race_value, ethnic_value, race_confidence, ethnic_confidence,
                  race_ethnicity_conflated)
    """
    if not source_value or pd.isna(source_value):
        return "Unknown", "Unknown", "UNMAPPED", "UNMAPPED", False

    val = str(source_value).strip()
    val_lower = val.lower()
    race_synonym_lookup = race_synonym_lookup or {}

    # 1. Try deterministic pattern matching
    for pattern, (race, ethnic) in _RACE_ETHNIC_PATTERNS.items():
        if re.match(pattern, val):
            # Validate race against allowed values
            race = _validate_race(race, allowed_race_values, race_synonym_lookup)
            return race, ethnic, "HIGH", "HIGH", True

    # 2. Check if value is purely an ethnicity term
    if _is_ethnicity_only(val_lower):
        ethnic = _resolve_ethnicity(val_lower, allowed_ethnic_values)
        return "Unknown", ethnic, "UNMAPPED", "HIGH", True

    # 3. Check if value is purely a race term (no ethnicity component)
    if not _has_ethnicity_component(val_lower):
        race = _resolve_race(val, allowed_race_values, race_synonym_lookup)
        return race, "Unknown", "MEDIUM" if race != "Unknown" else "UNMAPPED", "UNMAPPED", False

    # 4. Attempt to split on common delimiters
    for delimiter in [",", "/", ";", " - "]:
        if delimiter in val:
            parts = [p.strip() for p in val.split(delimiter, 1)]
            race_part, ethnic_part = _classify_parts(
                parts, allowed_race_values, allowed_ethnic_values, race_synonym_lookup
            )
            if race_part and ethnic_part:
                return race_part, ethnic_part, "MEDIUM", "MEDIUM", True

    # 5. Unresolvable — flag for LLM or manual review
    race = _resolve_race(val, allowed_race_values, race_synonym_lookup)
    return race, "Unknown", "LOW", "UNMAPPED", True


def _is_ethnicity_only(val_lower: str) -> bool:
    """Check if value is purely an ethnicity term."""
    ethnicity_terms = [
        "hispanic", "latino", "latina", "latinx",
        "not hispanic", "non-hispanic", "non hispanic",
        "hispanic or latino", "not hispanic or latino",
    ]
    return val_lower in ethnicity_terms


def _has_ethnicity_component(val_lower: str) -> bool:
    """Check if value contains an ethnicity keyword."""
    for keyword in _ETHNIC_KEYWORDS:
        if keyword in val_lower:
            return True
    return False


def _resolve_ethnicity(val_lower: str, allowed: List[str]) -> str:
    """Resolve an ethnicity value to an allowed value."""
    if "not" in val_lower or "non" in val_lower:
        return "Not Hispanic or Latino"
    if any(kw in val_lower for kw in ["hispanic", "latino", "latina", "latinx"]):
        return "Hispanic or Latino"
    return "Unknown"


def _resolve_race(
    val: str,
    allowed: List[str],
    synonym_lookup: Dict[str, str],
) -> str:
    """Resolve a race value to an allowed value."""
    val_lower = val.strip().lower()

    # Synonym lookup
    if val_lower in synonym_lookup:
        return synonym_lookup[val_lower]

    # Case-insensitive direct match
    for av in allowed:
        if val_lower == av.lower():
            return av

    return "Unknown"


def _validate_race(
    race: str,
    allowed: List[str],
    synonym_lookup: Dict[str, str],
) -> str:
    """Validate a race value against allowed list, applying synonyms."""
    if race in allowed:
        return race

    race_lower = race.lower()
    if race_lower in synonym_lookup:
        return synonym_lookup[race_lower]

    for av in allowed:
        if race_lower == av.lower():
            return av

    return race  # Return as-is, will be flagged by QC


def _classify_parts(
    parts: List[str],
    allowed_race: List[str],
    allowed_ethnic: List[str],
    race_synonyms: Dict[str, str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Given two string parts, classify which is race and which is ethnicity.

    Returns (race_value, ethnic_value) or (None, None) if can't classify.
    """
    race_val = None
    ethnic_val = None

    for part in parts:
        part_lower = part.strip().lower()

        if _is_ethnicity_only(part_lower) or _has_ethnicity_component(part_lower):
            ethnic_val = _resolve_ethnicity(part_lower, allowed_ethnic)
        else:
            resolved = _resolve_race(part, allowed_race, race_synonyms)
            if resolved != "Unknown":
                race_val = resolved
            elif race_val is None:
                race_val = resolved

    return race_val, ethnic_val
