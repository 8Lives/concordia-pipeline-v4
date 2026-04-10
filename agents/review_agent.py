"""
Review Agent (v4) — Spec-Driven LLM Review with Stoplight Grading

Uses Claude to review harmonized data for quality and compliance.
Stoplight grade (GREEN/YELLOW/RED) is informational — does not halt pipeline.

v4 Changes:
- Stoplight criteria loaded from SpecRegistry (domain_spec.stoplight_criteria)
- Cross-variable rules loaded from SpecRegistry
- LLM prompts use structured templates from llm/prompts.py
- No RAG retriever dependency
- Provenance summary included in review context
"""

import logging
from typing import Any, Dict, List, Optional
import pandas as pd

from .base import AgentBase, AgentConfig, AgentResult, PipelineContext, ProgressCallback
from llm.prompts import SYSTEM_REVIEW, build_review_prompt

logger = logging.getLogger(__name__)


class ReviewAgent(AgentBase):
    """
    LLM-powered review agent for harmonized data validation.

    Uses SpecRegistry for:
    - Stoplight grading criteria
    - Cross-variable dependency rules
    - Variable-level quality expectations

    The stoplight grade is non-gating — it's informational for the user.
    """

    def __init__(
        self,
        llm_service=None,
        spec_registry=None,
        config: Optional[AgentConfig] = None,
        progress_callback: Optional[ProgressCallback] = None,
        sample_size: int = 10,
    ):
        super().__init__(
            name="review",
            config=config or AgentConfig(timeout_seconds=60, required=False),
            progress_callback=progress_callback
        )
        self.llm_service = llm_service
        self.spec_registry = spec_registry
        self.sample_size = sample_size

    def validate_input(self, context: PipelineContext) -> Optional[str]:
        if context.get("harmonized_df") is None and context.get("df") is None:
            return "No DataFrame found in context (harmonized_df or df)"
        return None

    def execute(self, context: PipelineContext) -> AgentResult:
        try:
            harmonized_df = context.get("harmonized_df")
            df = harmonized_df if harmonized_df is not None else context.get("df")
            qc_report = context.get("qc_report")
            provenance_tracker = context.get("provenance_tracker")

            self._update_status(self._status, "Starting review...", 0.1)

            # Check if LLM is available
            if not self.llm_service or not self.llm_service.is_configured:
                logger.info("LLM not configured, performing basic review")
                return self._basic_review(context, df, qc_report)

            # Prepare data for LLM review
            self._update_status(self._status, "Preparing review data...", 0.2)
            data_sample = self._prepare_sample(df)
            column_stats = self._compute_column_stats(df)
            qc_issues = self._format_qc_issues(qc_report)

            # Get spec context
            stoplight_criteria = ""
            cross_variable_rules = []
            if self.spec_registry:
                stoplight_criteria = self.spec_registry.get_stoplight_criteria()
                cv_rules = self.spec_registry.get_cross_variable_rules()
                cross_variable_rules = [r.rule_text[:200] for r in cv_rules]

            # Build prompt
            prompt = build_review_prompt(
                data_sample=data_sample,
                column_stats=column_stats,
                qc_issues=qc_issues,
                stoplight_criteria=stoplight_criteria,
                cross_variable_rules=cross_variable_rules,
            )

            # Call LLM
            self._update_status(self._status, "LLM reviewing data...", 0.4)
            response = self.llm_service.call(
                prompt,
                system=SYSTEM_REVIEW,
                json_mode=True,
                max_tokens=2048,
                temperature=0.0,
            )

            if not response.success:
                logger.warning(f"LLM review failed: {response.error}")
                return self._basic_review(context, df, qc_report)

            # Process review results
            self._update_status(self._status, "Processing review results...", 0.8)
            review_result = response.parsed_data or {}

            stoplight = review_result.get("stoplight") or review_result.get("approval", "UNKNOWN")
            stoplight = stoplight.upper() if stoplight else "UNKNOWN"
            overall_quality = review_result.get("overall_quality", "unknown")

            # Stoplight is non-gating
            approved = stoplight == "GREEN"

            review_data = {
                "stoplight": stoplight,
                "approval": stoplight,
                "overall_quality": overall_quality,
                "approved": approved,
                "core_variables_present": review_result.get("core_variables_present", []),
                "core_variables_missing": review_result.get("core_variables_missing", []),
                "core_variables_count": review_result.get("core_variables_count", 0),
                "formatting_issues": review_result.get("formatting_issues", []),
                "critical_issues": review_result.get("critical_issues", []),
                "recommendations": review_result.get("recommendations", []),
                "reason": review_result.get("reason", "Review completed"),
                "llm_tokens_used": response.usage,
                "review_type": "llm"
            }

            # Add provenance summary if available
            if provenance_tracker:
                review_data["provenance_summary"] = provenance_tracker.summary()

            context.set("review_result", review_data)
            context.set("review_metadata", {
                "sample_size": len(data_sample),
                "llm_model": response.model,
                "auto_approved": approved
            })

            return AgentResult(
                success=True,
                data=review_data,
                metadata=context.get("review_metadata")
            )

        except Exception as e:
            logger.exception("Review agent failed")
            return AgentResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__
            )

    def _basic_review(
        self, context: PipelineContext, df: pd.DataFrame, qc_report
    ) -> AgentResult:
        """Perform basic review without LLM using stoplight rules."""
        core_vars = ["SEX", "RACE", "ETHNIC", "COUNTRY"]
        age_vars = ["AGE", "AGEGP"]

        present = []
        missing = []

        for var in core_vars:
            if var in df.columns and df[var].notna().any():
                present.append(var)
            else:
                missing.append(var)

        age_present = False
        for age_var in age_vars:
            if age_var in df.columns and df[age_var].notna().any():
                present.append(age_var)
                age_present = True
                break

        if not age_present:
            missing.append("AGE/AGEGP")

        core_count = len(present)
        missing_count = 5 - core_count

        if missing_count == 0:
            stoplight = "GREEN"
            overall_quality = "good"
        elif missing_count <= 2:
            stoplight = "YELLOW"
            overall_quality = "acceptable"
        else:
            stoplight = "RED"
            overall_quality = "poor"

        approved = stoplight == "GREEN"

        review_data = {
            "stoplight": stoplight,
            "approval": stoplight,
            "overall_quality": overall_quality,
            "approved": approved,
            "core_variables_present": present,
            "core_variables_missing": missing,
            "core_variables_count": core_count,
            "formatting_issues": [],
            "critical_issues": [],
            "recommendations": [f"Add missing core variables: {', '.join(missing)}"] if missing else [],
            "reason": f"Basic review: {core_count}/5 core variables present",
            "review_type": "basic"
        }

        context.set("review_result", review_data)

        return AgentResult(
            success=True,
            data=review_data,
            metadata={"review_type": "basic", "llm_available": False}
        )

    def _prepare_sample(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if len(df) <= self.sample_size:
            sample = df
        else:
            n = self.sample_size
            indices = (
                list(range(min(n // 3, len(df)))) +
                list(range(len(df) // 2 - n // 6, len(df) // 2 + n // 6)) +
                list(range(max(0, len(df) - n // 3), len(df)))
            )
            indices = sorted(set(indices))[:n]
            sample = df.iloc[indices]

        return sample.to_dict(orient="records")

    def _compute_column_stats(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        stats = {}
        for col in df.columns:
            col_stats = {
                "non_null_count": int(df[col].notna().sum()),
                "null_count": int(df[col].isna().sum()),
                "null_pct": round(df[col].isna().sum() / len(df) * 100, 1) if len(df) > 0 else 0
            }

            if df[col].dtype == "object":
                unique_vals = df[col].dropna().unique()
                col_stats["unique_count"] = len(unique_vals)
                col_stats["sample_values"] = list(unique_vals[:5])
            elif pd.api.types.is_numeric_dtype(df[col]):
                col_stats["min"] = float(df[col].min()) if df[col].notna().any() else None
                col_stats["max"] = float(df[col].max()) if df[col].notna().any() else None

            stats[col] = col_stats

        return stats

    def _format_qc_issues(self, qc_report) -> List[Dict[str, Any]]:
        if qc_report is None or len(qc_report) == 0:
            return []
        return qc_report.head(20).to_dict(orient="records")
