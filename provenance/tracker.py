"""
Provenance Tracker — Records the lineage of every harmonized value.

Every harmonized value carries:
    - source_dataset_id (trial / NCT ID)
    - source_field_name (original column name)
    - source_value_raw (original cell value)
    - harmonized_value (output value)
    - mapping_confidence (HIGH / MEDIUM / LOW / UNMAPPED)
    - mapping_notes (free-text explanation)
    - variable-specific flags (e.g., sex_gender_conflated, race_ethnicity_conflated)

The tracker accumulates ProvenanceRecord objects during harmonization
and can export them as a DataFrame for QC and audit.
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from spec_registry.models import ProvenanceRecord

logger = logging.getLogger(__name__)


class ProvenanceTracker:
    """
    Accumulates provenance records during harmonization.

    Usage:
        tracker = ProvenanceTracker()

        # Record each harmonized value
        tracker.record(
            variable="SEX",
            source_dataset_id="NCT00554229",
            source_field_name="SEX",
            source_value_raw="1",
            harmonized_value="Male",
            mapping_confidence="HIGH",
            flags={"sex_gender_conflated": False, "sex_conflict": False},
        )

        # Export for QC
        prov_df = tracker.to_dataframe()

        # Merge into harmonized output
        merged = tracker.merge_with_harmonized(harmonized_df)
    """

    def __init__(self):
        self._records: List[ProvenanceRecord] = []
        self._row_index: int = 0  # tracks current row for batch operations

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        variable: str,
        source_dataset_id: str = "",
        source_field_name: str = "",
        source_value_raw: str = "",
        harmonized_value: str = "",
        mapping_confidence: str = "HIGH",
        mapping_notes: Optional[str] = None,
        flags: Optional[Dict[str, Any]] = None,
        row_index: Optional[int] = None,
    ) -> ProvenanceRecord:
        """
        Record provenance for a single harmonized value.

        Args:
            variable: Target variable name (e.g., "SEX")
            source_dataset_id: Trial / NCT ID
            source_field_name: Original column name in source data
            source_value_raw: Original cell value (as string)
            harmonized_value: Output value after harmonization
            mapping_confidence: HIGH / MEDIUM / LOW / UNMAPPED
            mapping_notes: Free-text explanation of mapping decision
            flags: Variable-specific flags (e.g., sex_gender_conflated)
            row_index: Optional row index for traceability

        Returns:
            The created ProvenanceRecord
        """
        rec = ProvenanceRecord(
            variable=variable,
            source_dataset_id=source_dataset_id,
            source_field_name=source_field_name,
            source_value_raw=str(source_value_raw) if source_value_raw is not None else "",
            harmonized_value=str(harmonized_value) if harmonized_value is not None else "",
            mapping_confidence=mapping_confidence,
            mapping_notes=mapping_notes,
            flags=flags or {},
        )
        self._records.append(rec)
        return rec

    def record_batch(
        self,
        variable: str,
        source_dataset_id: str,
        source_field_name: str,
        source_values: pd.Series,
        harmonized_values: pd.Series,
        mapping_confidence: str = "HIGH",
        mapping_notes: Optional[str] = None,
        flags: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Record provenance for an entire column in one call.

        Efficient batch operation — creates one ProvenanceRecord per row.

        Args:
            variable: Target variable name
            source_dataset_id: Trial / NCT ID
            source_field_name: Original column name
            source_values: Series of raw source values
            harmonized_values: Series of harmonized values
            mapping_confidence: Default confidence for all rows
            mapping_notes: Default notes for all rows
            flags: Default flags for all rows

        Returns:
            Number of records created
        """
        count = 0
        flags = flags or {}

        for idx in source_values.index:
            raw = source_values.get(idx)
            harmonized = harmonized_values.get(idx)

            raw_str = str(raw) if pd.notna(raw) else ""
            harm_str = str(harmonized) if pd.notna(harmonized) else ""

            self.record(
                variable=variable,
                source_dataset_id=source_dataset_id,
                source_field_name=source_field_name,
                source_value_raw=raw_str,
                harmonized_value=harm_str,
                mapping_confidence=mapping_confidence,
                mapping_notes=mapping_notes,
                flags=dict(flags),  # copy to avoid shared mutation
                row_index=idx,
            )
            count += 1

        return count

    def record_variable_provenance(
        self,
        variable: str,
        source_dataset_id: str,
        source_field_name: str,
        df_source: pd.DataFrame,
        harmonized_series: pd.Series,
        confidence_series: Optional[pd.Series] = None,
        default_confidence: str = "HIGH",
        flags_per_row: Optional[List[Dict[str, Any]]] = None,
        default_flags: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None,
    ) -> int:
        """
        Record row-level provenance for a variable with per-row confidence.

        This is the primary method agents should use. It handles:
        - Per-row confidence grades (from confidence_series)
        - Per-row flags (from flags_per_row list)
        - Null handling (empty string for null values)

        Args:
            variable: Target variable name
            source_dataset_id: Trial / NCT ID
            source_field_name: Original column name
            df_source: Source DataFrame (reads source_field_name column)
            harmonized_series: Series of harmonized values (same index as df_source)
            confidence_series: Optional per-row confidence (same index)
            default_confidence: Fallback confidence when confidence_series is None
            flags_per_row: Optional list of per-row flag dicts
            default_flags: Default flags applied to all rows
            notes: Mapping notes for all rows

        Returns:
            Number of records created
        """
        count = 0
        default_flags = default_flags or {}

        # Get source values
        if source_field_name and source_field_name in df_source.columns:
            source_values = df_source[source_field_name]
        else:
            source_values = pd.Series([""] * len(df_source), index=df_source.index)

        for i, idx in enumerate(df_source.index):
            raw = source_values.get(idx)
            harmonized = harmonized_series.get(idx)

            # Per-row confidence
            if confidence_series is not None:
                conf = confidence_series.get(idx, default_confidence)
            else:
                conf = default_confidence

            # Per-row flags
            if flags_per_row and i < len(flags_per_row):
                row_flags = {**default_flags, **flags_per_row[i]}
            else:
                row_flags = dict(default_flags)

            self.record(
                variable=variable,
                source_dataset_id=source_dataset_id,
                source_field_name=source_field_name or "",
                source_value_raw=str(raw) if pd.notna(raw) else "",
                harmonized_value=str(harmonized) if pd.notna(harmonized) else "",
                mapping_confidence=str(conf),
                mapping_notes=notes,
                flags=row_flags,
                row_index=idx,
            )
            count += 1

        return count

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def get_records(self, variable: Optional[str] = None) -> List[ProvenanceRecord]:
        """
        Get all provenance records, optionally filtered by variable.

        Args:
            variable: If provided, return only records for this variable

        Returns:
            List of ProvenanceRecord objects
        """
        if variable:
            return [r for r in self._records if r.variable == variable]
        return list(self._records)

    def to_dataframe(self, variable: Optional[str] = None) -> pd.DataFrame:
        """
        Export provenance records as a flat DataFrame.

        Flag fields are expanded as flag_{name} columns.

        Args:
            variable: If provided, export only records for this variable

        Returns:
            DataFrame with one row per provenance record
        """
        records = self.get_records(variable)

        if not records:
            return pd.DataFrame(columns=[
                "variable", "source_dataset_id", "source_field_name",
                "source_value_raw", "harmonized_value", "mapping_confidence",
                "mapping_notes",
            ])

        rows = [r.to_flat_dict() for r in records]
        return pd.DataFrame(rows)

    def summary(self) -> Dict[str, Any]:
        """
        Generate a summary of provenance records for reporting.

        Returns:
            Dict with counts by variable and confidence grade.
        """
        total = len(self._records)

        by_variable: Dict[str, int] = {}
        by_confidence: Dict[str, int] = {}
        by_var_confidence: Dict[str, Dict[str, int]] = {}

        for rec in self._records:
            # By variable
            by_variable[rec.variable] = by_variable.get(rec.variable, 0) + 1

            # By confidence
            conf = rec.mapping_confidence
            by_confidence[conf] = by_confidence.get(conf, 0) + 1

            # By variable × confidence
            if rec.variable not in by_var_confidence:
                by_var_confidence[rec.variable] = {}
            by_var_confidence[rec.variable][conf] = (
                by_var_confidence[rec.variable].get(conf, 0) + 1
            )

        return {
            "total_records": total,
            "by_variable": by_variable,
            "by_confidence": by_confidence,
            "by_variable_confidence": by_var_confidence,
            "unmapped_count": by_confidence.get("UNMAPPED", 0),
            "low_confidence_count": by_confidence.get("LOW", 0),
        }

    def merge_with_harmonized(
        self,
        harmonized_df: pd.DataFrame,
        include_flags: bool = True,
    ) -> pd.DataFrame:
        """
        Merge provenance summary columns into the harmonized DataFrame.

        Adds per-variable confidence and flag columns to the output.
        This is used for the final output where each row needs its
        provenance metadata alongside the harmonized values.

        Args:
            harmonized_df: The harmonized DataFrame
            include_flags: Whether to include flag columns

        Returns:
            DataFrame with additional provenance columns
        """
        result = harmonized_df.copy()

        # Group records by variable
        var_records: Dict[str, List[ProvenanceRecord]] = {}
        for rec in self._records:
            if rec.variable not in var_records:
                var_records[rec.variable] = []
            var_records[rec.variable].append(rec)

        # For each variable with provenance, add confidence column
        for var_name, records in var_records.items():
            if var_name not in result.columns:
                continue

            n_rows = len(result)
            n_records = len(records)

            if n_records == n_rows:
                # One record per row — align by position
                conf_col = f"{var_name}_confidence"
                result[conf_col] = [r.mapping_confidence for r in records]

                if include_flags:
                    # Collect all flag names for this variable
                    all_flag_names = set()
                    for r in records:
                        all_flag_names.update(r.flags.keys())

                    for flag_name in sorted(all_flag_names):
                        flag_col = f"{var_name}_flag_{flag_name}"
                        result[flag_col] = [
                            r.flags.get(flag_name) for r in records
                        ]

            else:
                # Record count doesn't match row count — add summary only
                logger.warning(
                    f"Provenance record count ({n_records}) doesn't match "
                    f"DataFrame row count ({n_rows}) for variable '{var_name}'. "
                    f"Skipping per-row merge."
                )

        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def clear(self, variable: Optional[str] = None):
        """
        Clear provenance records.

        Args:
            variable: If provided, clear only records for this variable.
                      If None, clear all records.
        """
        if variable:
            self._records = [r for r in self._records if r.variable != variable]
        else:
            self._records = []

    @property
    def record_count(self) -> int:
        """Total number of provenance records."""
        return len(self._records)

    def __repr__(self) -> str:
        return f"ProvenanceTracker(records={len(self._records)})"
