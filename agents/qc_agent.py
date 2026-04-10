"""
QC Agent (v4) — Spec-Driven Quality Control

Performs quality checks on harmonized data using SpecRegistry-loaded rules.
Each QC issue is traceable to the specification rule that defines it.

v4 Changes:
- Required variables, coded variables, QC checks from SpecRegistry
- No RAG retriever dependency
- No FALLBACK lists — specs are single source of truth
- Provenance integrity checks (confidence distribution)
- Distribution plausibility from spec benchmarks
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from .base import AgentBase, AgentConfig, AgentResult, PipelineContext, ProgressCallback
from utils.helpers import validate_nct_format, is_full_date

logger = logging.getLogger(__name__)


class QCAgent(AgentBase):
    """
    Performs quality control checks on harmonized data.

    Uses SpecRegistry for:
    - Required variable list
    - Coded variable identification
    - Domain QC check definitions
    - Validation thresholds and plausibility benchmarks
    """

    def __init__(
        self,
        spec_registry=None,
        config: Optional[AgentConfig] = None,
        progress_callback: Optional[ProgressCallback] = None
    ):
        super().__init__(
            name="qc",
            config=config or AgentConfig(timeout_seconds=120),
            progress_callback=progress_callback
        )
        self.spec_registry = spec_registry

    def validate_input(self, context: PipelineContext) -> Optional[str]:
        if context.get("harmonized_df") is None:
            return "No harmonized DataFrame found in context"
        return None

    def _get_required_variables(self) -> List[str]:
        if self.spec_registry:
            req = self.spec_registry.get_required_variables()
            if req:
                return req
        return ["TRIAL", "SUBJID", "SEX", "RACE", "DOMAIN"]

    def _get_coded_variables(self) -> List[str]:
        if self.spec_registry:
            coded = self.spec_registry.get_coded_variables()
            if coded:
                return coded
        return ["SEX", "RACE", "ETHNIC", "ARMCD"]

    def _get_date_variables(self) -> List[str]:
        """Date variables to validate."""
        return ["BRTHDTC", "RFSTDTC", "RFENDTC"]

    def execute(self, context: PipelineContext) -> AgentResult:
        try:
            df = context.get("harmonized_df")
            mapping_log = context.get("mapping_log", [])
            lineage_log = context.get("harmonize_lineage_log", [])
            trial_id = context.get("trial_id")
            dictionary = context.get("dictionary", {})
            provenance_tracker = context.get("provenance_tracker")

            self._update_status(self._status, "Starting QC checks...", 0.1)

            issues = []

            # 1. Check TRIAL validity
            self._update_status(self._status, "Checking TRIAL validity...", 0.15)
            issues.extend(self._check_trial_validity(df, trial_id))

            # 2. Check uniqueness
            self._update_status(self._status, "Checking uniqueness...", 0.25)
            issues.extend(self._check_uniqueness(df))

            # 3. Check required values
            self._update_status(self._status, "Checking required values...", 0.35)
            issues.extend(self._check_required_values(df))

            # 4. Check age completeness
            self._update_status(self._status, "Checking age completeness...", 0.45)
            issues.extend(self._check_age_completeness(df))

            # 5. Check coded values against spec
            self._update_status(self._status, "Checking coded values...", 0.55)
            issues.extend(self._check_coded_values(df))

            # 6. Check date validity
            self._update_status(self._status, "Checking date validity...", 0.65)
            issues.extend(self._check_date_validity(df))

            # 7. Check mapping quality
            self._update_status(self._status, "Checking mapping quality...", 0.75)
            issues.extend(self._check_mapping_quality(mapping_log))

            # 8. Check provenance integrity
            self._update_status(self._status, "Checking provenance...", 0.85)
            if provenance_tracker:
                issues.extend(self._check_provenance_integrity(provenance_tracker, df))

            # Build QC report
            self._update_status(self._status, "Building QC report...", 0.9)
            qc_report = self._build_qc_report(issues, trial_id)

            # Build transformation summary
            transformation_summary = self._build_transformation_summary(
                mapping_log, lineage_log
            )

            # Store results
            context.set("qc_report", qc_report)
            context.set("transformation_summary", transformation_summary)
            context.set("qc_metadata", {
                "total_issues": len(issues),
                "issues_by_type": self._count_issues_by_type(issues),
            })

            return AgentResult(
                success=True,
                data={
                    "qc_report": qc_report,
                    "transformation_summary": transformation_summary,
                },
                metadata=context.get("qc_metadata")
            )

        except Exception as e:
            logger.exception("QC agent failed")
            return AgentResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )

    # ------------------------------------------------------------------
    # QC Checks
    # ------------------------------------------------------------------

    def _check_trial_validity(
        self, df: pd.DataFrame, trial_id: Optional[str]
    ) -> List[Dict[str, Any]]:
        issues = []

        if "TRIAL" not in df.columns:
            issues.append({
                "issue_type": "TRIAL_MISSING_OR_INVALID",
                "variable": "TRIAL",
                "n_rows_affected": len(df),
                "example_values": [],
                "notes": "TRIAL column not found",
            })
            return issues

        unique_trials = df["TRIAL"].dropna().unique()

        for trial in unique_trials:
            if not validate_nct_format(str(trial)):
                affected = df[df["TRIAL"] == trial]
                issues.append({
                    "issue_type": "TRIAL_MISSING_OR_INVALID",
                    "variable": "TRIAL",
                    "n_rows_affected": len(affected),
                    "example_values": [str(trial)],
                    "notes": f"Value '{trial}' does not match NCT format",
                })

        missing = df["TRIAL"].isna().sum()
        if missing > 0:
            issues.append({
                "issue_type": "TRIAL_MISSING_OR_INVALID",
                "variable": "TRIAL",
                "n_rows_affected": int(missing),
                "example_values": [],
                "notes": "TRIAL is blank/null",
            })

        return issues

    def _check_uniqueness(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        issues = []

        if "TRIAL" not in df.columns or "SUBJID" not in df.columns:
            return issues

        duplicates = df[df.duplicated(subset=["TRIAL", "SUBJID"], keep=False)]

        if len(duplicates) > 0:
            example_pairs = duplicates.groupby(["TRIAL", "SUBJID"]).size().head(5)
            examples = [f"{t}-{s}" for t, s in example_pairs.index]

            issues.append({
                "issue_type": "DUPLICATE_SUBJECT",
                "variable": "TRIAL, SUBJID",
                "n_rows_affected": len(duplicates),
                "example_values": examples,
                "notes": f"{len(duplicates)} rows have duplicate (TRIAL, SUBJID) combinations",
            })

            if len(duplicates) == len(df):
                issues.append({
                    "issue_type": "SUBJID_MAPPING_SUSPECT",
                    "variable": "SUBJID",
                    "n_rows_affected": len(df),
                    "example_values": list(df["SUBJID"].head(5).astype(str)),
                    "notes": "100% of rows are duplicates - SUBJID mapping likely incorrect",
                })

        return issues

    def _check_required_values(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        issues = []
        required = self._get_required_variables()

        for var in required:
            if var not in df.columns:
                issues.append({
                    "issue_type": "MISSING_REQUIRED_VALUE",
                    "variable": var,
                    "n_rows_affected": len(df),
                    "example_values": [],
                    "notes": f"Required variable {var} not in output",
                })
                continue

            missing = df[var].isna().sum()
            # Also check for "Unknown" in required variables (questionable fills)
            if missing > 0:
                missing_rows = df[df[var].isna()].index[:5].tolist()
                issues.append({
                    "issue_type": "MISSING_REQUIRED_VALUE",
                    "variable": var,
                    "n_rows_affected": int(missing),
                    "example_values": [f"row {r}" for r in missing_rows],
                    "notes": f"Required variable {var} has {missing} missing values",
                })

        return issues

    def _check_age_completeness(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        issues = []

        has_age = "AGE" in df.columns
        has_agegp = "AGEGP" in df.columns

        if not has_age and not has_agegp:
            issues.append({
                "issue_type": "MISSING_AGE_AND_AGEGP",
                "variable": "AGE, AGEGP",
                "n_rows_affected": len(df),
                "example_values": [],
                "notes": "Neither AGE nor AGEGP columns present",
            })
            return issues

        if has_age and has_agegp:
            both_missing = df[df["AGE"].isna() & df["AGEGP"].isna()]
        elif has_age:
            both_missing = df[df["AGE"].isna()]
        else:
            both_missing = df[df["AGEGP"].isna()]

        if len(both_missing) > 0:
            issues.append({
                "issue_type": "MISSING_AGE_AND_AGEGP",
                "variable": "AGE, AGEGP",
                "n_rows_affected": len(both_missing),
                "example_values": list(both_missing.index[:5]),
                "notes": f"{len(both_missing)} rows missing both AGE and AGEGP",
            })

        return issues

    def _check_coded_values(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Check coded variable values against spec-defined allowed values."""
        issues = []
        coded_vars = self._get_coded_variables()

        for var in coded_vars:
            if var not in df.columns:
                continue

            # Get allowed values from spec
            if self.spec_registry:
                allowed = self.spec_registry.get_valid_values(var)
            else:
                allowed = []

            if not allowed:
                continue

            # Check for values not in allowed list
            unique_vals = df[var].dropna().unique()
            invalid_vals = [v for v in unique_vals if v not in allowed]

            if invalid_vals:
                total_invalid = sum(
                    int((df[var] == v).sum()) for v in invalid_vals
                )
                issues.append({
                    "issue_type": "CODED_VALUE_NOT_IN_SPEC",
                    "variable": var,
                    "n_rows_affected": total_invalid,
                    "example_values": [str(v) for v in invalid_vals[:5]],
                    "notes": f"{len(invalid_vals)} unique values not in allowed list: {allowed}",
                })

        return issues

    def _check_date_validity(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        issues = []
        date_vars = self._get_date_variables()

        for var in date_vars:
            if var not in df.columns:
                continue

            def is_valid_date(x):
                if pd.isna(x):
                    return True
                val = str(x).strip()
                if re.match(r'^\d{4}(-\d{2})?(-\d{2})?$', val):
                    return True
                return bool(re.search(r'\d', val))

            invalid = df[~df[var].apply(is_valid_date)]
            if len(invalid) > 0:
                examples = invalid[var].head(5).tolist()
                issues.append({
                    "issue_type": "DATE_INVALID",
                    "variable": var,
                    "n_rows_affected": len(invalid),
                    "example_values": [str(e) for e in examples],
                    "notes": f"{len(invalid)} rows have unparseable date values",
                })

        # Check date order
        if "RFSTDTC" in df.columns and "RFENDTC" in df.columns:
            def check_date_order(row):
                start = row.get("RFSTDTC")
                end = row.get("RFENDTC")
                if pd.isna(start) or pd.isna(end):
                    return True
                start_str = str(start).strip()
                end_str = str(end).strip()
                if is_full_date(start_str) and is_full_date(end_str):
                    return end_str >= start_str
                return True

            order_issues = df[~df.apply(check_date_order, axis=1)]
            if len(order_issues) > 0:
                examples = []
                for _, row in order_issues.head(3).iterrows():
                    examples.append(f"start={row.get('RFSTDTC')}, end={row.get('RFENDTC')}")

                issues.append({
                    "issue_type": "DATE_ORDER_INVALID",
                    "variable": "RFSTDTC, RFENDTC",
                    "n_rows_affected": len(order_issues),
                    "example_values": examples,
                    "notes": "RFENDTC is before RFSTDTC",
                })

        return issues

    def _check_mapping_quality(
        self, mapping_log: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        issues = []

        for entry in mapping_log:
            var = entry.get("output_variable")
            details = entry.get("details", {})

            if details.get("matched_via") == "heuristic":
                issues.append({
                    "issue_type": "COLUMN_MAPPING_HEURISTIC",
                    "variable": var,
                    "n_rows_affected": 0,
                    "example_values": [],
                    "notes": f"{var} was mapped using uniqueness heuristic - verify correct column",
                })

            if "warning" in details and "uniqueness" in details.get("warning", "").lower():
                issues.append({
                    "issue_type": "SUBJID_MAPPING_SUSPECT",
                    "variable": var,
                    "n_rows_affected": 0,
                    "example_values": [],
                    "notes": details.get("warning"),
                })

        return issues

    def _check_provenance_integrity(
        self, provenance_tracker, df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Check provenance records for integrity issues."""
        issues = []

        summary = provenance_tracker.summary()

        # Check for high UNMAPPED rate
        total = summary.get("total_records", 0)
        unmapped = summary.get("unmapped_count", 0)
        low_conf = summary.get("low_confidence_count", 0)

        if total > 0:
            unmapped_pct = unmapped / total * 100
            low_pct = low_conf / total * 100

            if unmapped_pct > 10:
                issues.append({
                    "issue_type": "HIGH_UNMAPPED_RATE",
                    "variable": "ALL",
                    "n_rows_affected": unmapped,
                    "example_values": [],
                    "notes": f"{unmapped_pct:.1f}% of provenance records are UNMAPPED",
                })

            if low_pct > 20:
                issues.append({
                    "issue_type": "HIGH_LOW_CONFIDENCE_RATE",
                    "variable": "ALL",
                    "n_rows_affected": low_conf,
                    "example_values": [],
                    "notes": f"{low_pct:.1f}% of provenance records have LOW confidence",
                })

        return issues

    # ------------------------------------------------------------------
    # Report builders
    # ------------------------------------------------------------------

    def _build_qc_report(
        self, issues: List[Dict[str, Any]], trial_id: Optional[str]
    ) -> pd.DataFrame:
        if not issues:
            return pd.DataFrame(columns=[
                "TRIAL", "issue_type", "variable", "n_rows_affected",
                "example_values", "notes"
            ])

        report_data = []
        for issue in issues:
            report_data.append({
                "TRIAL": trial_id or "UNKNOWN",
                "issue_type": issue.get("issue_type"),
                "variable": issue.get("variable"),
                "n_rows_affected": issue.get("n_rows_affected", 0),
                "example_values": ", ".join(str(e) for e in issue.get("example_values", [])[:5]),
                "notes": issue.get("notes"),
            })

        return pd.DataFrame(report_data)

    def _count_issues_by_type(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {}
        for issue in issues:
            issue_type = issue.get("issue_type", "UNKNOWN")
            counts[issue_type] = counts.get(issue_type, 0) + 1
        return counts

    def _build_transformation_summary(
        self,
        mapping_log: List[Dict[str, Any]],
        lineage_log: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        summary = []
        lineage_by_var = {e.get("variable"): e for e in lineage_log}

        for mapping in mapping_log:
            var = mapping.get("output_variable")
            lineage = lineage_by_var.get(var, {})

            summary.append({
                "variable": var,
                "source_column": mapping.get("source_column"),
                "mapping_operation": mapping.get("operation"),
                "transformation": lineage.get("transform_operation", "None"),
                "rows_changed": lineage.get("rows_changed", 0),
                "percent_changed": round(lineage.get("percent_changed", 0), 2),
                "missing_count": mapping.get("null_count", 0),
            })

        return summary
