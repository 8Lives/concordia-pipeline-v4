"""
Pipeline Orchestrator (v4) — Spec-Driven Pipeline Coordination

Coordinates the 5-agent pipeline: Ingest → Map → Harmonize → QC → Review

v4 Changes:
- No RAG initialization (no ChromaDB, embeddings, vector_store, indexer, retriever)
- SpecRegistry replaces all RAG infrastructure — loads at init in <0.3s
- ProvenanceTracker passed through the pipeline as first-class output
- Domain-parameterized (default "DM", extensible to AE)
- LLM service lazy-loaded as before (optional)
"""

import logging
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from agents.base import PipelineContext, AgentResult, AgentStatus
from agents.ingest_agent import IngestAgent
from agents.map_agent import MapAgent
from agents.harmonize_agent import HarmonizeAgent
from agents.qc_agent import QCAgent
from agents.review_agent import ReviewAgent
from spec_registry import SpecRegistry
from config.settings import get_settings, Settings

# LLM service import (optional)
try:
    from llm.service import LLMService
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    LLMService = None

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from a complete pipeline run."""
    success: bool
    harmonized_data: Optional[pd.DataFrame] = None
    qc_report: Optional[pd.DataFrame] = None
    review_result: Optional[Dict[str, Any]] = None
    mapping_log: Optional[List[Dict[str, Any]]] = None
    lineage: Optional[List[Dict[str, Any]]] = None
    provenance_df: Optional[pd.DataFrame] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stage_results: Dict[str, AgentResult] = field(default_factory=dict)
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# Type for progress callback: (stage_name, status, message, progress_pct)
ProgressCallback = Callable[[str, str, str, float], None]


class PipelineOrchestrator:
    """
    Orchestrates the harmonization pipeline.

    v4: SpecRegistry replaces the entire RAG stack. Initialization is
    near-instant (<0.3s) compared to seconds for ChromaDB + embedding init.

    Usage:
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run(input_file="path/to/data.csv")
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        progress_callback: Optional[ProgressCallback] = None,
        use_llm: bool = True,
        enable_review: bool = True,
        domain: str = "DM",
    ):
        """
        Initialize the orchestrator.

        Args:
            settings: Configuration settings (uses defaults if not provided)
            progress_callback: Optional callback for progress updates
            use_llm: Whether to use LLM for value resolution and review
            enable_review: Whether to run the LLM review stage
            domain: Target domain (default "DM", future: "AE")
        """
        self.settings = settings or get_settings()
        self.progress_callback = progress_callback
        self.use_llm = use_llm
        self.enable_review = enable_review
        self.domain = domain

        # SpecRegistry — loads synchronously at init
        self._spec_registry: Optional[SpecRegistry] = None
        self._spec_initialized = False

        # LLM service (lazy-loaded)
        self._llm_service = None
        self._llm_initialized = False

    def _update_progress(
        self, stage: str, status: str, message: str, progress: float
    ):
        if self.progress_callback:
            self.progress_callback(stage, status, message, progress)
        logger.info(f"[{stage}] {status}: {message} ({progress:.0%})")

    def _initialize_specs(self) -> bool:
        """
        Initialize the SpecRegistry. Fast — loads markdown specs in <0.3s.
        """
        if self._spec_initialized:
            return self._spec_registry is not None

        self._update_progress("init", "running", "Loading specifications...", 0.0)

        try:
            spec_base_dir = self.settings.get_domain_spec_dir()
            # SpecRegistry constructor expects the parent of the domain dir
            # e.g., knowledge_base/ which contains DM/
            spec_base_parent = spec_base_dir.parent

            self._spec_registry = SpecRegistry(
                spec_base_dir=spec_base_parent,
                domain=self.domain,
            )
            self._spec_initialized = True

            n_vars = len(self._spec_registry.get_all_variables())
            self._update_progress(
                "init", "success",
                f"SpecRegistry loaded: {n_vars} variables for {self.domain}",
                0.3,
            )
            return True

        except Exception as e:
            logger.exception(f"SpecRegistry initialization failed: {e}")
            self._spec_initialized = True
            self._spec_registry = None
            self._update_progress("init", "warning", f"Spec load failed: {e}", 0.3)
            return False

    def _initialize_llm(self) -> bool:
        """Initialize LLM service for value resolution and review."""
        if self._llm_initialized:
            return self._llm_service is not None and self._llm_service.is_configured

        self._update_progress("init", "running", "Initializing LLM service...", 0.4)

        if not LLM_AVAILABLE:
            logger.warning("LLM module not available")
            self._llm_initialized = True
            return False

        try:
            import os
            api_key = self.settings.anthropic_api_key
            if not api_key:
                api_key = os.environ.get("ANTHROPIC_API_KEY")

            self._llm_service = LLMService(api_key=api_key)
            self._llm_initialized = True

            if self._llm_service.is_configured:
                self._update_progress("init", "success", "LLM service initialized", 0.5)
                return True
            else:
                self._update_progress("init", "warning", "LLM not configured (no API key)", 0.5)
                return False

        except Exception as e:
            logger.warning(f"LLM initialization failed: {e}")
            self._llm_initialized = True
            self._llm_service = None
            self._update_progress("init", "warning", f"LLM unavailable: {e}", 0.5)
            return False

    def run(
        self,
        input_file: Optional[str] = None,
        input_df: Optional[pd.DataFrame] = None,
        trial_id: Optional[str] = None,
        output_dir: Optional[str] = None,
        skip_qc: bool = False,
        data_dict: Optional[Dict[str, Any]] = None,
        dictionary_file: Optional[str] = None,
    ) -> PipelineResult:
        """
        Run the complete harmonization pipeline.

        Args:
            input_file: Path to input CSV/Excel/SAS file
            input_df: Or provide DataFrame directly
            trial_id: Trial identifier (extracted from filename if not provided)
            output_dir: Output directory (uses default if not provided)
            skip_qc: Skip QC stage if True
            data_dict: Optional pre-parsed data dictionary
            dictionary_file: Optional path to dictionary file

        Returns:
            PipelineResult with harmonized data, provenance, and reports
        """
        start_time = time.time()
        result = PipelineResult(success=False)

        try:
            if input_file is None and input_df is None:
                raise ValueError("Either input_file or input_df must be provided")

            # Initialize SpecRegistry
            self._initialize_specs()

            # Initialize LLM if enabled
            if self.use_llm:
                self._initialize_llm()

            # Setup output directory
            if output_dir:
                output_path = Path(output_dir)
            else:
                output_path = self.settings.output_dir
            output_path.mkdir(parents=True, exist_ok=True)

            # Create pipeline context
            context = PipelineContext()
            context.set("output_dir", str(output_path))

            if data_dict:
                context.set("dictionary", data_dict)
                logger.info(f"Data dictionary loaded: {list(data_dict.keys())}")

            # --------------------------------------------------------
            # Stage 1: Ingest
            # --------------------------------------------------------
            self._update_progress("ingest", "running", "Loading data...", 0.1)
            ingest_result = self._run_ingest(
                context, input_file, input_df, trial_id, dictionary_file
            )
            result.stage_results["ingest"] = ingest_result

            if not ingest_result.success:
                result.errors.append(f"Ingest failed: {ingest_result.error}")
                return result

            source_df = context.get("df").copy()

            # --------------------------------------------------------
            # Stage 2: Map
            # --------------------------------------------------------
            self._update_progress("map", "running", "Mapping columns...", 0.3)
            map_result = self._run_map(context)
            result.stage_results["map"] = map_result

            if not map_result.success:
                result.errors.append(f"Map failed: {map_result.error}")
                return result

            result.mapping_log = context.get("mapping_log")

            # --------------------------------------------------------
            # Stage 3: Harmonize
            # --------------------------------------------------------
            self._update_progress("harmonize", "running", "Harmonizing values...", 0.5)
            harmonize_result = self._run_harmonize(context)
            result.stage_results["harmonize"] = harmonize_result

            if not harmonize_result.success:
                result.errors.append(f"Harmonize failed: {harmonize_result.error}")
                return result

            result.lineage = context.get("harmonize_lineage_log", [])

            # Extract provenance
            provenance_tracker = context.get("provenance_tracker")
            if provenance_tracker:
                result.provenance_df = provenance_tracker.to_dataframe()

            # --------------------------------------------------------
            # Stage 4: QC
            # --------------------------------------------------------
            if not skip_qc:
                self._update_progress("qc", "running", "Running quality checks...", 0.7)
                qc_result = self._run_qc(context)
                result.stage_results["qc"] = qc_result

                if not qc_result.success:
                    result.warnings.append(f"QC issues: {qc_result.error}")

                result.qc_report = context.get("qc_report")

            # --------------------------------------------------------
            # Stage 5: Review
            # --------------------------------------------------------
            llm_ready = (
                self.use_llm
                and self._llm_service is not None
                and self._llm_service.is_configured
            )
            if self.enable_review:
                self._update_progress("review", "running", "Running review...", 0.8)
                review_result = self._run_review(context)
                result.stage_results["review"] = review_result

                if review_result.success:
                    result.review_result = review_result.data
                else:
                    result.warnings.append(f"Review failed: {review_result.error}")

            # --------------------------------------------------------
            # Finalize
            # --------------------------------------------------------
            self._update_progress("finalize", "running", "Finalizing results...", 0.9)

            harmonized_df = context.get("harmonized_df")
            result.harmonized_data = harmonized_df if harmonized_df is not None else context.get("df")

            # Set DOMAIN to the target domain code
            if result.harmonized_data is not None and "DOMAIN" in result.harmonized_data.columns:
                result.harmonized_data["DOMAIN"] = self.domain

            # Append unmapped source columns
            if result.harmonized_data is not None and source_df is not None:
                mapping_log = context.get("mapping_log", [])
                mapped_sources = {
                    m.get("source_column")
                    for m in mapping_log
                    if m.get("source_column")
                }
                unmapped_cols = [
                    c for c in source_df.columns
                    if c not in mapped_sources
                    and c.upper() not in result.harmonized_data.columns
                ]
                if unmapped_cols:
                    for col in unmapped_cols:
                        result.harmonized_data[col] = source_df[col].values
                    logger.info(f"Appended {len(unmapped_cols)} unmapped source columns")

            result.success = True
            result.metadata = {
                "trial_id": context.get("trial_id"),
                "input_file": input_file,
                "output_dir": str(output_path),
                "spec_registry_loaded": self._spec_registry is not None,
                "llm_enabled": llm_ready,
                "review_enabled": self.enable_review,
                "domain": self.domain,
                "llm_model": self._llm_service.model if self._llm_service else "none",
                "llm_tokens_used": self._llm_service.total_tokens_used if self._llm_service else 0,
                "provenance_records": len(result.provenance_df) if result.provenance_df is not None else 0,
                "timestamp": datetime.now().isoformat(),
                "rows_processed": len(result.harmonized_data) if result.harmonized_data is not None else 0,
            }

            # Save outputs
            self._save_outputs(result, output_path, context.get("trial_id", "output"))

            self._update_progress("complete", "success", "Pipeline complete", 1.0)

        except Exception as e:
            logger.exception("Pipeline failed with unexpected error")
            result.errors.append(f"Unexpected error: {str(e)}")
            self._update_progress("error", "failed", str(e), 0.0)

        finally:
            result.execution_time_ms = int((time.time() - start_time) * 1000)

        return result

    # ------------------------------------------------------------------
    # Stage runners
    # ------------------------------------------------------------------

    def _run_ingest(
        self,
        context: PipelineContext,
        input_file: Optional[str],
        input_df: Optional[pd.DataFrame],
        trial_id: Optional[str],
        dictionary_file: Optional[str] = None,
    ) -> AgentResult:
        if input_df is not None:
            context.set("df", input_df)
            context.set("trial_id", trial_id or "UNKNOWN")
            context.set("ingest_metadata", {
                "source": "direct_dataframe",
                "rows": len(input_df),
                "columns": list(input_df.columns),
            })
            return AgentResult(success=True, data={"rows": len(input_df)})

        # File input
        context.set("data_file", input_file)
        if dictionary_file:
            context.set("dictionary_file", dictionary_file)
        if trial_id:
            context.set("trial_id", trial_id)

        agent = IngestAgent(spec_registry=self._spec_registry)
        return agent.run(context)

    def _run_map(self, context: PipelineContext) -> AgentResult:
        agent = MapAgent(spec_registry=self._spec_registry)
        return agent.run(context)

    def _run_harmonize(self, context: PipelineContext) -> AgentResult:
        agent = HarmonizeAgent(
            spec_registry=self._spec_registry,
            llm_service=self._llm_service,
            use_llm_fallback=self.use_llm and self._llm_service is not None,
            domain=self.domain,
        )
        return agent.run(context)

    def _run_qc(self, context: PipelineContext) -> AgentResult:
        agent = QCAgent(spec_registry=self._spec_registry)
        return agent.run(context)

    def _run_review(self, context: PipelineContext) -> AgentResult:
        agent = ReviewAgent(
            llm_service=self._llm_service,
            spec_registry=self._spec_registry,
            sample_size=10,
        )
        return agent.run(context)

    # ------------------------------------------------------------------
    # Output persistence
    # ------------------------------------------------------------------

    def _save_outputs(
        self, result: PipelineResult, output_dir: Path, trial_id: str
    ):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{trial_id}_{timestamp}"

        try:
            if result.harmonized_data is not None:
                f = output_dir / f"{prefix}_harmonized.csv"
                result.harmonized_data.to_csv(f, index=False)
                result.metadata["harmonized_file"] = str(f)

            if result.qc_report is not None and len(result.qc_report) > 0:
                f = output_dir / f"{prefix}_qc_report.csv"
                result.qc_report.to_csv(f, index=False)
                result.metadata["qc_file"] = str(f)

            if result.provenance_df is not None and len(result.provenance_df) > 0:
                f = output_dir / f"{prefix}_provenance.csv"
                result.provenance_df.to_csv(f, index=False)
                result.metadata["provenance_file"] = str(f)

            if result.mapping_log:
                f = output_dir / f"{prefix}_mapping_log.json"
                with open(f, "w") as fh:
                    json.dump(result.mapping_log, fh, indent=2, default=str)
                result.metadata["mapping_file"] = str(f)

            if result.lineage:
                f = output_dir / f"{prefix}_lineage.json"
                with open(f, "w") as fh:
                    json.dump(result.lineage, fh, indent=2, default=str)
                result.metadata["lineage_file"] = str(f)

            if result.review_result:
                f = output_dir / f"{prefix}_review.json"
                with open(f, "w") as fh:
                    json.dump(result.review_result, fh, indent=2, default=str)
                result.metadata["review_file"] = str(f)

        except Exception as e:
            logger.error(f"Error saving outputs: {e}")
            result.warnings.append(f"Failed to save some outputs: {e}")

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def spec_registry(self) -> Optional[SpecRegistry]:
        """Get the SpecRegistry instance."""
        if not self._spec_initialized:
            self._initialize_specs()
        return self._spec_registry


@dataclass
class MultiDomainResult:
    """Result from running multiple domains through the pipeline."""
    success: bool
    domain_results: Dict[str, PipelineResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: int = 0

    @property
    def domains_succeeded(self) -> List[str]:
        return [d for d, r in self.domain_results.items() if r.success]

    @property
    def domains_failed(self) -> List[str]:
        return [d for d, r in self.domain_results.items() if not r.success]


class MultiDomainOrchestrator:
    """
    Orchestrates harmonization across multiple SDTM domains.

    Runs each domain through its own PipelineOrchestrator instance with
    domain-specific specs. Currently supports sequential execution;
    parallel execution can be added when multiple domain specs are ready.

    Usage:
        mdo = MultiDomainOrchestrator(domains=["DM", "AE"])
        result = mdo.run(domain_inputs={"DM": "dm.sas7bdat", "AE": "ae.sas7bdat"})
    """

    def __init__(
        self,
        domains: List[str],
        settings: Optional[Settings] = None,
        progress_callback: Optional[ProgressCallback] = None,
        use_llm: bool = True,
        enable_review: bool = True,
    ):
        self.domains = domains
        self.settings = settings or get_settings()
        self.progress_callback = progress_callback
        self.use_llm = use_llm
        self.enable_review = enable_review

    def run(
        self,
        domain_inputs: Dict[str, str],
        trial_id: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> MultiDomainResult:
        """
        Run the pipeline for each domain.

        Args:
            domain_inputs: Dict mapping domain code → input file path
            trial_id: Shared trial identifier
            output_dir: Shared output directory

        Returns:
            MultiDomainResult with per-domain PipelineResults
        """
        start_time = time.time()
        result = MultiDomainResult(success=False)

        for domain in self.domains:
            input_file = domain_inputs.get(domain)
            if input_file is None:
                result.errors.append(f"No input file provided for domain '{domain}'")
                continue

            try:
                orchestrator = PipelineOrchestrator(
                    settings=self.settings,
                    progress_callback=self.progress_callback,
                    use_llm=self.use_llm,
                    enable_review=self.enable_review,
                    domain=domain,
                )
                domain_result = orchestrator.run(
                    input_file=input_file,
                    trial_id=trial_id,
                    output_dir=output_dir,
                )
                result.domain_results[domain] = domain_result

            except Exception as e:
                logger.exception(f"Domain '{domain}' failed: {e}")
                result.errors.append(f"Domain '{domain}': {str(e)}")

        result.success = len(result.domains_succeeded) > 0
        result.execution_time_ms = int((time.time() - start_time) * 1000)
        return result


def create_orchestrator(
    use_llm: bool = True,
    enable_review: bool = True,
    domain: str = "DM",
    progress_callback: Optional[ProgressCallback] = None,
    **settings_overrides
) -> PipelineOrchestrator:
    """
    Factory function to create a configured orchestrator.

    Args:
        use_llm: Whether to use LLM for value resolution and review
        enable_review: Whether to run LLM review stage
        domain: Target domain (default "DM")
        progress_callback: Optional progress callback
        **settings_overrides: Override any settings

    Returns:
        Configured PipelineOrchestrator
    """
    settings = get_settings(**settings_overrides)
    return PipelineOrchestrator(
        settings=settings,
        progress_callback=progress_callback,
        use_llm=use_llm,
        enable_review=enable_review,
        domain=domain,
    )


def create_multi_domain_orchestrator(
    domains: List[str],
    use_llm: bool = True,
    enable_review: bool = True,
    progress_callback: Optional[ProgressCallback] = None,
    **settings_overrides
) -> MultiDomainOrchestrator:
    """
    Factory function to create a multi-domain orchestrator.

    Args:
        domains: List of domain codes to process (e.g., ["DM", "AE"])
        use_llm: Whether to use LLM for value resolution and review
        enable_review: Whether to run LLM review stage
        progress_callback: Optional progress callback
        **settings_overrides: Override any settings

    Returns:
        Configured MultiDomainOrchestrator
    """
    settings = get_settings(**settings_overrides)
    return MultiDomainOrchestrator(
        domains=domains,
        settings=settings,
        progress_callback=progress_callback,
        use_llm=use_llm,
        enable_review=enable_review,
    )
