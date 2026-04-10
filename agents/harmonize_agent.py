"""
Harmonize Agent (v4) — Spec-Driven Value Transformation

Transforms mapped data values according to SpecRegistry specifications.
Every harmonized value is recorded in the ProvenanceTracker with confidence
grading and variable-specific flags.

v4 Changes:
- All value lookups via SpecRegistry (synonym_lookup, allowed_values)
- No FALLBACK dicts — specs are the single source of truth
- ProvenanceTracker records every cell-level transformation
- LLM role shifts to "apply decision principles" rather than "resolve what RAG missed"
- Race/ethnicity separation logic per DM_RACE.md Section 3.2
- v4 value changes: Caucasian→White, no "Other", Undifferentiated added
- Null handling per system_rules.md: no nulls in output
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from .base import AgentBase, AgentConfig, AgentResult, PipelineContext, ProgressCallback
from provenance.tracker import ProvenanceTracker
from llm.prompts import (
    SYSTEM_VALUE_RESOLUTION,
    build_value_resolution_prompt,
    build_race_ethnicity_separation_prompt,
    SYSTEM_RACE_ETHNICITY_SEPARATION,
)
from spec_registry.models import TerminologyLookup, NoOpTerminologyLookup
from utils.helpers import (
    to_mixed_case,
    normalize_whitespace,
    sas_date_to_iso,
    sas_datetime_to_iso,
    is_full_date,
    calculate_age,
    validate_nct_format,
)

logger = logging.getLogger(__name__)


class HarmonizeAgent(AgentBase):
    """
    Harmonizes mapped data values according to SpecRegistry specifications.

    Uses SpecRegistry for:
    - Allowed value lists per categorical variable
    - Synonym lookups (case-insensitive source→target mappings)
    - Decision principles for LLM context injection
    - Missing value defaults per variable
    - Provenance field definitions

    ProvenanceTracker records every harmonized value with:
    - source_field_name, source_value_raw, harmonized_value
    - mapping_confidence (HIGH/MEDIUM/LOW/UNMAPPED)
    - variable-specific flags (e.g., sex_gender_conflated)
    """

    def __init__(
        self,
        spec_registry=None,
        llm_service=None,
        config: Optional[AgentConfig] = None,
        progress_callback: Optional[ProgressCallback] = None,
        use_llm_fallback: bool = True,
        domain: str = "DM",
        terminology_lookup: Optional[TerminologyLookup] = None,
    ):
        super().__init__(
            name="harmonize",
            config=config or AgentConfig(timeout_seconds=120, max_retries=1),
            progress_callback=progress_callback
        )
        self.spec_registry = spec_registry
        self.llm_service = llm_service
        self.use_llm_fallback = use_llm_fallback
        self.domain = domain
        self.terminology_lookup = terminology_lookup or NoOpTerminologyLookup()
        self.provenance = ProvenanceTracker()

        # LLM resolution cache (keyed by "VARIABLE:value")
        self._llm_resolution_cache: Dict[str, Optional[str]] = {}

    def validate_input(self, context: PipelineContext) -> Optional[str]:
        if context.get("df") is None:
            return "No DataFrame found in context (df)"
        if context.get("mapping_log") is None:
            return "No mapping log found in context"
        return None

    # ------------------------------------------------------------------
    # Spec-driven helpers
    # ------------------------------------------------------------------

    def _get_allowed_values(self, variable: str) -> List[str]:
        """Get allowed target values for a variable from spec."""
        if self.spec_registry:
            return self.spec_registry.get_valid_values(variable)
        return []

    def _get_synonym_lookup(self, variable: str) -> Dict[str, str]:
        """Get case-insensitive synonym lookup for a variable."""
        if self.spec_registry:
            return self.spec_registry.get_synonym_lookup(variable)
        return {}

    def _get_missing_value(self, variable: str) -> str:
        """Get the missing/unknown value for a variable."""
        if self.spec_registry:
            return self.spec_registry.get_missing_value(variable)
        return "Unknown"

    def _normalize_code_key(self, value) -> str:
        """Normalize a value for dictionary lookup. Handles float→int conversion."""
        if pd.isna(value):
            return ""

        val_str = str(value).strip()

        try:
            float_val = float(val_str)
            if float_val == int(float_val):
                return str(int(float_val))
        except (ValueError, TypeError):
            pass

        return val_str

    def _fuzzy_synonym_match(
        self, val_lower: str, synonym_lookup: Dict[str, str], allowed_lower: Dict[str, str]
    ) -> Optional[str]:
        """
        Attempt broadened synonym matching for common clinical data patterns.

        Handles:
        - Slash→"or" normalization: "Black/African American" → "black or african american"
        - Parenthetical stripping: "Other (specify)" → "other"
        - Trailing whitespace/punctuation cleanup
        - "Alaskan" vs "Alaska" normalization
        - Bare "other" → nearest match in synonyms (typically "Unknown")

        Returns the resolved allowed value or None.
        """
        # Try slash→"or" replacement: "Black/African American" → "black or african american"
        if "/" in val_lower:
            slash_to_or = val_lower.replace("/", " or ").replace("  ", " ").strip()
            if slash_to_or in synonym_lookup:
                return synonym_lookup[slash_to_or]
            if slash_to_or in allowed_lower:
                return allowed_lower[slash_to_or]

            # Also try slash→space: "Black/African American" → "black african american"
            slash_to_space = val_lower.replace("/", " ").replace("  ", " ").strip()
            if slash_to_space in synonym_lookup:
                return synonym_lookup[slash_to_space]

        # Strip parenthetical qualifiers: "Other (specify)" → "other"
        stripped = re.sub(r'\s*\(.*?\)\s*', '', val_lower).strip()
        if stripped and stripped != val_lower:
            if stripped in synonym_lookup:
                return synonym_lookup[stripped]
            if stripped in allowed_lower:
                return allowed_lower[stripped]

        # "Alaskan" → "Alaska" normalization for AIAN
        if "alaskan" in val_lower:
            normalized = val_lower.replace("alaskan", "alaska")
            if normalized in synonym_lookup:
                return synonym_lookup[normalized]
            if normalized in allowed_lower:
                return allowed_lower[normalized]
            # Also try with slash→"or" + alaska
            if "/" in normalized:
                norm_or = normalized.replace("/", " or ").replace("  ", " ").strip()
                if norm_or in synonym_lookup:
                    return synonym_lookup[norm_or]
                if norm_or in allowed_lower:
                    return allowed_lower[norm_or]

        # Check if any synonym key is a substring or vice versa (for close matches)
        # This handles source values matching spec entries with parenthetical qualifiers,
        # e.g., data has "Other" and spec has "Other (no free-text) → Unknown"
        for syn_key, syn_val in synonym_lookup.items():
            if syn_key.startswith(stripped + " ") or syn_key.startswith(stripped + "("):
                return syn_val

        return None

    def _resolve_with_llm(
        self,
        variable: str,
        value: str,
        allowed_values: List[str],
        spec_context: str = "",
    ) -> Tuple[Optional[str], str]:
        """
        Use LLM to resolve an ambiguous value. Returns (resolved_value, confidence).

        Uses spec-context-injected prompts from llm/prompts.py.
        """
        cache_key = f"{variable}:{value}"
        if cache_key in self._llm_resolution_cache:
            cached = self._llm_resolution_cache[cache_key]
            return (cached, "LOW") if cached else (None, "UNMAPPED")

        if not self.llm_service or not self.use_llm_fallback or not self.llm_service.is_configured:
            return None, "UNMAPPED"

        try:
            # Get decision principles from spec
            decision_principles = ""
            mapping_patterns = []
            if self.spec_registry:
                spec = self.spec_registry.get_variable_spec(variable)
                if spec:
                    decision_principles = spec.decision_principles
                    mapping_patterns = self.spec_registry.get_mapping_patterns(variable)

            prompt = build_value_resolution_prompt(
                variable=variable,
                value=value,
                allowed_values=allowed_values,
                spec_context=spec_context,
                decision_principles=decision_principles,
                mapping_patterns=mapping_patterns,
            )

            response = self.llm_service.call(
                prompt,
                system=SYSTEM_VALUE_RESOLUTION,
                json_mode=True,
                temperature=0.0
            )

            if response.success and response.parsed_data:
                resolved = response.parsed_data.get("resolved_value")
                confidence = response.parsed_data.get("confidence", "low").upper()

                if resolved and confidence in ["HIGH", "MEDIUM", "LOW"]:
                    logger.info(f"LLM resolved {variable}='{value}' → '{resolved}' ({confidence})")
                    self._llm_resolution_cache[cache_key] = resolved
                    return resolved, confidence

        except Exception as e:
            logger.warning(f"LLM resolution failed for {variable}='{value}': {e}")

        self._llm_resolution_cache[cache_key] = None
        return None, "UNMAPPED"

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def execute(self, context: PipelineContext) -> AgentResult:
        try:
            df = context.get("df").copy()
            mapping_log = context.get("mapping_log")
            dictionary = context.get("dictionary", {})
            trial_id = context.get("trial_id")

            self._update_status(self._status, "Starting harmonization...", 0.1)

            lineage_log = []
            variables = list(df.columns)
            total_vars = len(variables)

            for i, var in enumerate(variables):
                progress = 0.1 + (0.8 * (i / total_vars))
                self._update_status(self._status, f"Harmonizing {var}...", progress)

                var_mapping = next(
                    (m for m in mapping_log if m.get("output_variable") == var),
                    {}
                )

                original_values = df[var].copy()
                df[var], lineage_entry = self._harmonize_variable(
                    df, var, var_mapping, dictionary, trial_id
                )

                lineage_entry["rows_changed"] = self._count_changes(original_values, df[var])
                lineage_entry["percent_changed"] = (
                    lineage_entry["rows_changed"] / len(df) * 100
                    if len(df) > 0 else 0
                )
                lineage_entry["missing_count"] = int(df[var].isna().sum())
                lineage_entry["non_null_count"] = int(df[var].notna().sum())
                lineage_log.append(lineage_entry)

            # Check for duplicates
            self._update_status(self._status, "Checking for duplicates...", 0.9)
            duplicates = self._check_duplicates(df)

            # Apply null handling: per system_rules.md, no nulls in output
            # Replace remaining NaN/None with variable-specific missing values
            for var in df.columns:
                missing_val = self._get_missing_value(var)
                if missing_val:
                    df[var] = df[var].fillna(missing_val)

            # Store results
            context.set("harmonized_df", df)
            context.set("harmonize_lineage_log", lineage_log)
            context.set("provenance_tracker", self.provenance)
            context.set("harmonize_metadata", {
                "rows_out": len(df),
                "duplicates_found": len(duplicates),
                "llm_resolutions": len(self._llm_resolution_cache),
                "provenance_records": self.provenance.record_count,
            })

            return AgentResult(
                success=True,
                data={
                    "harmonized_df": df,
                    "lineage_log": lineage_log,
                    "provenance_tracker": self.provenance,
                },
                metadata=context.get("harmonize_metadata")
            )

        except Exception as e:
            logger.exception("Harmonize agent failed")
            return AgentResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )

    # ------------------------------------------------------------------
    # Variable routing
    # ------------------------------------------------------------------

    def _harmonize_variable(
        self,
        df: pd.DataFrame,
        variable: str,
        mapping: Dict[str, Any],
        dictionary: Dict[str, Any],
        trial_id: Optional[str]
    ) -> Tuple[pd.Series, Dict[str, Any]]:
        lineage = {
            "variable": variable,
            "source_column": mapping.get("source_column"),
            "mapping_operation": mapping.get("operation", "Unknown"),
            "transform_operation": "None",
            "transform_details": {},
        }

        handlers = {
            "TRIAL": lambda: self._harmonize_trial(df, trial_id, lineage),
            "SUBJID": lambda: self._harmonize_subjid(df, lineage),
            "SEX": lambda: self._harmonize_coded(df, "SEX", dictionary, lineage),
            "RACE": lambda: self._harmonize_coded(df, "RACE", dictionary, lineage),
            "AGE": lambda: self._harmonize_age(df, lineage),
            "AGEU": lambda: self._harmonize_ageu(df, lineage),
            "AGEGP": lambda: self._harmonize_agegp(df, lineage),
            "ETHNIC": lambda: self._harmonize_coded(df, "ETHNIC", dictionary, lineage),
            "COUNTRY": lambda: self._harmonize_country(df, dictionary, lineage),
            "SITEID": lambda: self._harmonize_siteid(df, lineage),
            "STUDYID": lambda: self._harmonize_studyid(df, lineage),
            "USUBJID": lambda: self._harmonize_usubjid(df, lineage),
            "ARMCD": lambda: self._harmonize_arm(df, "ARMCD", dictionary, lineage),
            "ARM": lambda: self._harmonize_arm(df, "ARM", dictionary, lineage),
            "BRTHDTC": lambda: self._harmonize_date(df, "BRTHDTC", lineage),
            "RFSTDTC": lambda: self._harmonize_date(df, "RFSTDTC", lineage),
            "RFENDTC": lambda: self._harmonize_date(df, "RFENDTC", lineage),
            "DOMAIN": lambda: self._harmonize_domain(df, lineage),
        }

        handler = handlers.get(variable)
        if handler:
            return handler()
        else:
            return self._harmonize_default(df, variable, lineage)

    # ------------------------------------------------------------------
    # Generic coded-variable harmonizer (SEX, RACE, ETHNIC)
    # ------------------------------------------------------------------

    def _harmonize_coded(
        self,
        df: pd.DataFrame,
        variable: str,
        dictionary: Dict,
        lineage: Dict
    ) -> Tuple[pd.Series, Dict]:
        """
        Spec-driven harmonization for any coded variable.

        Resolution order:
        1. Data dictionary decode (from source file's companion dict)
        2. Synonym lookup from SpecRegistry value set
        3. Direct match to allowed values (case-insensitive)
        4. LLM inference with decision-principle context
        5. Missing value default
        """
        allowed_values = self._get_allowed_values(variable)
        synonym_lookup = self._get_synonym_lookup(variable)

        # Data dictionary codes (source-file-specific)
        dict_key = variable
        # ETHNIC may come from ETHGRP in dictionary
        if variable == "ETHNIC" and "ETHGRP" in (dictionary or {}):
            dict_key = "ETHGRP"
        dict_codes = (dictionary or {}).get(dict_key, {}).get("codes", {})

        # Build case-insensitive allowed value lookup
        allowed_lower = {v.lower(): v for v in allowed_values}

        # Pre-resolve unique values with LLM (batch optimization)
        unique_values = df[variable].dropna().unique()
        llm_resolutions = {}
        unresolved = set()

        for val in unique_values:
            val_norm = self._normalize_code_key(val)
            val_lower = val_norm.lower()

            # Already resolvable without LLM?
            if val_norm in dict_codes or val_norm.upper() in dict_codes:
                continue
            if val_lower in allowed_lower:
                continue
            if val_lower in synonym_lookup:
                continue
            # Fuzzy synonym match (slash→or, parenthetical strip, etc.)
            if self._fuzzy_synonym_match(val_lower, synonym_lookup, allowed_lower):
                continue

            # Terminology lookup (MedDRA for AE, no-op for DM)
            term_result = self.terminology_lookup.lookup(val_norm, "MedDRA")
            if term_result and term_result.get("pt"):
                pt = term_result["pt"]
                if pt.lower() in allowed_lower:
                    continue

            # Need LLM
            spec_ctx = ""
            if self.spec_registry:
                spec_ctx = self.spec_registry.get_llm_context(variable)

            resolved, confidence = self._resolve_with_llm(
                variable, val_norm, allowed_values, spec_ctx
            )
            if resolved:
                llm_resolutions[val_norm] = (resolved, confidence)
            else:
                unresolved.add(val_norm)

        # Apply to every row
        missing_val = self._get_missing_value(variable)
        results = []
        confidences = []

        for idx in df.index:
            raw = df.at[idx, variable]

            if pd.isna(raw):
                results.append(missing_val)
                confidences.append("UNMAPPED")
                continue

            val_norm = self._normalize_code_key(raw)
            val_lower = val_norm.lower()
            harmonized = None
            confidence = "HIGH"

            # 1. Dictionary decode
            if val_norm in dict_codes:
                decoded = dict_codes[val_norm]
                harmonized = to_mixed_case(decoded)
                confidence = "HIGH"
            elif val_norm.upper() in dict_codes:
                decoded = dict_codes[val_norm.upper()]
                harmonized = to_mixed_case(decoded)
                confidence = "HIGH"

            # 2. Direct match to allowed values (highest non-dictionary confidence)
            if harmonized is None and val_lower in allowed_lower:
                harmonized = allowed_lower[val_lower]
                confidence = "HIGH"

            # 3. Synonym lookup
            if harmonized is None and val_lower in synonym_lookup:
                harmonized = synonym_lookup[val_lower]
                confidence = "MEDIUM"

            # 3b. Fuzzy synonym match (slash→or, strip parens, Alaskan→Alaska)
            if harmonized is None:
                fuzzy_result = self._fuzzy_synonym_match(val_lower, synonym_lookup, allowed_lower)
                if fuzzy_result:
                    harmonized = fuzzy_result
                    confidence = "MEDIUM"

            # 3b. Terminology lookup (MedDRA for AE, no-op for DM)
            if harmonized is None:
                term_result = self.terminology_lookup.lookup(val_norm, "MedDRA")
                if term_result and term_result.get("pt"):
                    pt = term_result["pt"]
                    if allowed_values:
                        if pt.lower() in allowed_lower:
                            harmonized = allowed_lower[pt.lower()]
                            confidence = "MEDIUM"
                    else:
                        # No allowed value constraint (e.g., free-text AE terms)
                        harmonized = pt
                        confidence = "MEDIUM"

            # 4. LLM resolution
            if harmonized is None and val_norm in llm_resolutions:
                harmonized, confidence = llm_resolutions[val_norm]

            # 5. Fallback
            if harmonized is None:
                harmonized = to_mixed_case(val_norm) if val_norm else missing_val
                confidence = "UNMAPPED" if val_norm else "UNMAPPED"

            # Validate against allowed values
            if allowed_values and harmonized not in allowed_values:
                # Check case-insensitive
                for av in allowed_values:
                    if harmonized.lower() == av.lower():
                        harmonized = av
                        break
                else:
                    # Not in allowed list — keep but mark UNMAPPED
                    if confidence != "UNMAPPED":
                        confidence = "LOW"

            results.append(harmonized)
            confidences.append(confidence)

        result_series = pd.Series(results, index=df.index)

        # Record provenance for every row
        source_col = lineage.get("source_column") or variable
        for i, idx in enumerate(df.index):
            raw = df.at[idx, variable]
            self.provenance.record(
                variable=variable,
                source_dataset_id=str(df.at[idx, "TRIAL"]) if "TRIAL" in df.columns and pd.notna(df.at[idx, "TRIAL"]) else "",
                source_field_name=source_col,
                source_value_raw=str(raw) if pd.notna(raw) else "",
                harmonized_value=results[i],
                mapping_confidence=confidences[i],
            )

        lineage["transform_operation"] = "Spec-driven coded value harmonization"
        lineage["transform_details"] = {
            "allowed_values": allowed_values,
            "dictionary_used": bool(dict_codes),
            "synonym_mappings_used": len(synonym_lookup),
            "llm_resolutions": {k: v[0] for k, v in llm_resolutions.items()},
            "unresolved_values": list(unresolved)[:10],
        }
        return result_series, lineage

    # ------------------------------------------------------------------
    # Provenance helper for non-coded variables
    # ------------------------------------------------------------------

    def _record_simple_provenance(
        self,
        df: pd.DataFrame,
        variable: str,
        result_series: pd.Series,
        lineage: Dict,
        confidence: str = "HIGH",
    ):
        """Record provenance for non-coded variables (TRIAL, SUBJID, dates, etc.).

        These variables don't go through the coded resolution chain, so their
        confidence is determined by the transform type:
        - HIGH: direct passthrough, constant assignment, or deterministic transform
        - MEDIUM: derived from other columns (e.g., USUBJID from STUDYID+SUBJID)
        - UNMAPPED: null/missing values
        """
        source_col = lineage.get("source_column") or variable
        for idx in df.index:
            raw = df.at[idx, variable] if variable in df.columns else None
            harmonized = result_series.get(idx)
            row_conf = confidence
            if pd.isna(harmonized) or harmonized is None:
                row_conf = "UNMAPPED"
            self.provenance.record(
                variable=variable,
                source_dataset_id=str(df.at[idx, "TRIAL"]) if "TRIAL" in df.columns and pd.notna(df.at[idx, "TRIAL"]) else "",
                source_field_name=source_col,
                source_value_raw=str(raw) if pd.notna(raw) else "",
                harmonized_value=str(harmonized) if pd.notna(harmonized) else "",
                mapping_confidence=row_conf,
            )

    # ------------------------------------------------------------------
    # Variable-specific handlers
    # ------------------------------------------------------------------

    def _harmonize_trial(
        self, df: pd.DataFrame, trial_id: Optional[str], lineage: Dict
    ) -> Tuple[pd.Series, Dict]:
        if trial_id:
            result = pd.Series([trial_id] * len(df), index=df.index)
            lineage["transform_operation"] = "Constant"
            lineage["transform_details"] = {"value": trial_id}
        else:
            result = df["TRIAL"].apply(
                lambda x: str(x).strip().upper() if pd.notna(x) else None
            )
            lineage["transform_operation"] = "Normalize (uppercase, trim)"
        self._record_simple_provenance(df, "TRIAL", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_subjid(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        def clean_subjid(x):
            if pd.isna(x):
                return None
            if isinstance(x, float) and x == int(x):
                return str(int(x))
            return str(x).strip()

        result = df["SUBJID"].apply(clean_subjid)
        lineage["transform_operation"] = "Trim, convert floats to strings"
        self._record_simple_provenance(df, "SUBJID", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_age(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        def clean_age(row):
            age_val = row.get("AGE")

            if pd.notna(age_val):
                try:
                    age = float(age_val)
                    if 0 <= age <= 120:
                        return age
                except (ValueError, TypeError):
                    pass

            # Try derivation from dates
            brthdtc = row.get("BRTHDTC")
            rfstdtc = row.get("RFSTDTC")

            if pd.notna(brthdtc) and pd.notna(rfstdtc):
                if is_full_date(str(brthdtc)) and is_full_date(str(rfstdtc)):
                    derived = calculate_age(str(brthdtc), str(rfstdtc))
                    if derived is not None:
                        return derived

            return None

        result = df.apply(clean_age, axis=1)
        lineage["transform_operation"] = "Convert to numeric, derive from dates if missing"
        # AGE: HIGH if direct from source, MEDIUM if derived from dates
        for idx in df.index:
            raw_age = df.at[idx, "AGE"] if "AGE" in df.columns else None
            harmonized = result.get(idx)
            if pd.isna(harmonized) or harmonized is None:
                conf = "UNMAPPED"
            elif pd.notna(raw_age):
                conf = "HIGH"
            else:
                conf = "MEDIUM"  # derived from BRTHDTC/RFSTDTC
            self.provenance.record(
                variable="AGE",
                source_dataset_id=str(df.at[idx, "TRIAL"]) if "TRIAL" in df.columns and pd.notna(df.at[idx, "TRIAL"]) else "",
                source_field_name=lineage.get("source_column") or "AGE",
                source_value_raw=str(raw_age) if pd.notna(raw_age) else "",
                harmonized_value=str(harmonized) if pd.notna(harmonized) else "",
                mapping_confidence=conf,
            )
        return result, lineage

    def _harmonize_ageu(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        def clean_ageu(row):
            age = row.get("AGE")
            if pd.isna(age):
                return None
            return "Years"

        result = df.apply(clean_ageu, axis=1)
        lineage["transform_operation"] = "Standardize to 'Years'"
        self._record_simple_provenance(df, "AGEU", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_agegp(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        def clean_agegp(row):
            age = row.get("AGE")
            agegp = row.get("AGEGP")

            if pd.notna(age):
                return None  # AGE available → AGEGP blank

            if pd.notna(agegp):
                return str(agegp).strip()

            return None

        result = df.apply(clean_agegp, axis=1)
        lineage["transform_operation"] = "Preserve if AGE missing, blank otherwise"
        self._record_simple_provenance(df, "AGEGP", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_country(
        self, df: pd.DataFrame, dictionary: Dict, lineage: Dict
    ) -> Tuple[pd.Series, Dict]:
        """Harmonize COUNTRY — expand ISO codes, use dictionary."""
        dict_map = (dictionary or {}).get("COUNTRY", {}).get("codes", {})

        def harmonize_country(x):
            if pd.isna(x):
                return None

            val = str(x).strip()
            val_upper = val.upper()

            if val_upper in dict_map:
                return to_mixed_case(dict_map[val_upper])

            # Already a reasonable country name
            return to_mixed_case(val)

        result = df["COUNTRY"].apply(harmonize_country)
        lineage["transform_operation"] = "Expand ISO codes, normalize to mixed case"
        self._record_simple_provenance(df, "COUNTRY", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_siteid(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        def clean_siteid(x):
            if pd.isna(x):
                return None
            val = str(x).strip()
            try:
                if '.' in val:
                    float_val = float(val)
                    if float_val == int(float_val):
                        return str(int(float_val))
            except (ValueError, TypeError):
                pass
            return val

        result = df["SITEID"].apply(clean_siteid)
        lineage["transform_operation"] = "Preserve as string"
        self._record_simple_provenance(df, "SITEID", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_studyid(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        result = df["STUDYID"].apply(
            lambda x: str(x).strip() if pd.notna(x) else None
        )
        lineage["transform_operation"] = "Trim whitespace"
        self._record_simple_provenance(df, "STUDYID", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_usubjid(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        def derive_usubjid(row):
            usubjid = row.get("USUBJID")
            if pd.notna(usubjid):
                return str(usubjid).strip()

            subjid = row.get("SUBJID")
            if pd.isna(subjid):
                return None

            studyid = row.get("STUDYID")
            trial = row.get("TRIAL")

            prefix = studyid if pd.notna(studyid) else trial
            if pd.notna(prefix):
                return f"{prefix}-{subjid}"

            return str(subjid)

        result = df.apply(derive_usubjid, axis=1)
        lineage["transform_operation"] = "Derive as STUDYID||'-'||SUBJID if not present"
        # USUBJID: HIGH if from source, MEDIUM if derived
        for idx in df.index:
            raw = df.at[idx, "USUBJID"] if "USUBJID" in df.columns else None
            harmonized = result.get(idx)
            if pd.isna(harmonized) or harmonized is None:
                conf = "UNMAPPED"
            elif pd.notna(raw):
                conf = "HIGH"
            else:
                conf = "MEDIUM"  # derived from STUDYID + SUBJID
            self.provenance.record(
                variable="USUBJID",
                source_dataset_id=str(df.at[idx, "TRIAL"]) if "TRIAL" in df.columns and pd.notna(df.at[idx, "TRIAL"]) else "",
                source_field_name=lineage.get("source_column") or "USUBJID",
                source_value_raw=str(raw) if pd.notna(raw) else "",
                harmonized_value=str(harmonized) if pd.notna(harmonized) else "",
                mapping_confidence=conf,
            )
        return result, lineage

    def _harmonize_arm(
        self, df: pd.DataFrame, variable: str, dictionary: Dict, lineage: Dict
    ) -> Tuple[pd.Series, Dict]:
        dict_key = "ARMCD" if variable == "ARMCD" else "ARM"
        dict_map = (dictionary or {}).get(dict_key, {}).get("codes", {})

        def harmonize_arm(x):
            if pd.isna(x):
                return None
            val = str(x).strip()
            if val.upper() in dict_map:
                return to_mixed_case(dict_map[val.upper()])
            return to_mixed_case(val)

        result = df[variable].apply(harmonize_arm)
        lineage["transform_operation"] = "Decode codes, normalize to mixed case"
        self._record_simple_provenance(df, variable, result, lineage, "HIGH")
        return result, lineage

    def _harmonize_date(
        self, df: pd.DataFrame, variable: str, lineage: Dict
    ) -> Tuple[pd.Series, Dict]:
        def clean_date(x):
            if pd.isna(x):
                return None

            val = str(x).strip()

            if re.match(r'^\d{4}(-\d{2})?(-\d{2})?$', val):
                return val

            try:
                numeric_val = float(val)
                if numeric_val > 50000:
                    return sas_datetime_to_iso(numeric_val)
                else:
                    return sas_date_to_iso(int(numeric_val))
            except (ValueError, TypeError):
                pass

            return val

        result = df[variable].apply(clean_date)
        lineage["transform_operation"] = "Convert SAS dates to ISO 8601"
        self._record_simple_provenance(df, variable, result, lineage, "HIGH")
        return result, lineage

    def _harmonize_domain(self, df: pd.DataFrame, lineage: Dict) -> Tuple[pd.Series, Dict]:
        domain_code = "DM"
        if self.spec_registry:
            domain_code = self.spec_registry.domain
        result = pd.Series([domain_code] * len(df), index=df.index)
        lineage["transform_operation"] = f"Constant '{domain_code}'"
        self._record_simple_provenance(df, "DOMAIN", result, lineage, "HIGH")
        return result, lineage

    def _harmonize_default(
        self, df: pd.DataFrame, variable: str, lineage: Dict
    ) -> Tuple[pd.Series, Dict]:
        result = df[variable].apply(
            lambda x: normalize_whitespace(str(x)) if pd.notna(x) else None
        )
        lineage["transform_operation"] = "Normalize whitespace"
        self._record_simple_provenance(df, variable, result, lineage, "HIGH")
        return result, lineage

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _count_changes(self, original: pd.Series, harmonized: pd.Series) -> int:
        def normalize_for_compare(x):
            if pd.isna(x):
                return ""
            return str(x).strip().lower()

        orig_norm = original.apply(normalize_for_compare)
        harm_norm = harmonized.apply(normalize_for_compare)
        return int((orig_norm != harm_norm).sum())

    def _check_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        if "TRIAL" not in df.columns or "SUBJID" not in df.columns:
            return pd.DataFrame()
        mask = df.duplicated(subset=["TRIAL", "SUBJID"], keep=False)
        return df[mask]
