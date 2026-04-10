"""
Phase 5 Tests — AE Hooks

Tests for:
    AE-01: Domain-parameterized verification
    AE-02: Multi-domain orchestration hook
    AE-03: Terminology interface (MedDRA stub)
    AE-04: Partial date utility
"""

import sys
import os
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from spec_registry.models import (
    NoOpTerminologyLookup,
    MedDRALookup,
    TerminologyLookup,
)
from utils.helpers import (
    parse_partial_date,
    impute_partial_date,
    get_date_precision,
)
from orchestrator import (
    PipelineOrchestrator,
    PipelineResult,
    MultiDomainOrchestrator,
    MultiDomainResult,
    create_orchestrator,
    create_multi_domain_orchestrator,
)


# =========================================================================
# AE-01: Domain-Parameterized Verification
# =========================================================================

class TestDomainParameterization:
    """Verify pipeline accepts and propagates arbitrary domain codes."""

    def test_orchestrator_accepts_domain(self):
        orch = create_orchestrator(use_llm=False, enable_review=False, domain="AE")
        assert orch.domain == "AE"

    def test_orchestrator_default_domain_is_dm(self):
        orch = create_orchestrator(use_llm=False, enable_review=False)
        assert orch.domain == "DM"

    def test_harmonize_agent_receives_domain(self):
        """HarmonizeAgent should use the domain from its constructor."""
        from agents.harmonize_agent import HarmonizeAgent
        agent = HarmonizeAgent(domain="AE")
        assert agent.domain == "AE"

    def test_harmonize_agent_default_domain(self):
        from agents.harmonize_agent import HarmonizeAgent
        agent = HarmonizeAgent()
        assert agent.domain == "DM"

    def test_domain_column_uses_registry_domain(self):
        """_harmonize_domain should use spec_registry.domain, not hardcoded 'DM'."""
        from agents.harmonize_agent import HarmonizeAgent

        mock_registry = MagicMock()
        mock_registry.domain = "AE"

        agent = HarmonizeAgent(spec_registry=mock_registry, domain="AE")
        df = pd.DataFrame({"DOMAIN": ["XX", "XX"]})
        lineage = {}
        result, _ = agent._harmonize_domain(df, lineage)
        assert list(result) == ["AE", "AE"]


# =========================================================================
# AE-02: Multi-Domain Orchestration
# =========================================================================

class TestMultiDomainOrchestrator:
    """Verify multi-domain orchestration hook works correctly."""

    def test_create_multi_domain_factory(self):
        mdo = create_multi_domain_orchestrator(
            domains=["DM", "AE"], use_llm=False, enable_review=False
        )
        assert isinstance(mdo, MultiDomainOrchestrator)
        assert mdo.domains == ["DM", "AE"]

    def test_multi_domain_result_properties(self):
        r = MultiDomainResult(success=True)
        r.domain_results["DM"] = PipelineResult(success=True)
        r.domain_results["AE"] = PipelineResult(success=False, errors=["test"])
        assert r.domains_succeeded == ["DM"]
        assert r.domains_failed == ["AE"]

    def test_multi_domain_missing_input(self):
        """Should report error for domain with no input file."""
        mdo = MultiDomainOrchestrator(
            domains=["DM", "AE"], use_llm=False, enable_review=False
        )
        result = mdo.run(domain_inputs={"DM": "/nonexistent.csv"})
        assert "No input file provided for domain 'AE'" in result.errors

    def test_multi_domain_result_empty(self):
        r = MultiDomainResult(success=False)
        assert r.domains_succeeded == []
        assert r.domains_failed == []


# =========================================================================
# AE-03: Terminology Interface
# =========================================================================

class TestNoOpTerminology:
    """Verify NoOp implementation works for DM domain."""

    def test_lookup_returns_none(self):
        t = NoOpTerminologyLookup()
        assert t.lookup("Headache", "MedDRA") is None

    def test_search_returns_empty(self):
        t = NoOpTerminologyLookup()
        assert t.search("Head", "MedDRA") == []

    def test_implements_abc(self):
        t = NoOpTerminologyLookup()
        assert isinstance(t, TerminologyLookup)


class TestMedDRALookup:
    """Verify MedDRA stub implementation."""

    @pytest.fixture
    def meddra(self):
        return MedDRALookup(preloaded_terms={
            "headache": {"pt": "Headache", "llt": "Headache", "soc": "Nervous system disorders"},
            "nausea": {"pt": "Nausea", "llt": "Nausea", "soc": "Gastrointestinal disorders"},
            "head pain": {"pt": "Headache", "llt": "Head pain", "soc": "Nervous system disorders"},
        })

    def test_implements_abc(self, meddra):
        assert isinstance(meddra, TerminologyLookup)

    def test_exact_lookup(self, meddra):
        result = meddra.lookup("headache", "MedDRA")
        assert result is not None
        assert result["pt"] == "Headache"
        assert result["match_type"] == "exact"

    def test_case_insensitive_lookup(self, meddra):
        result = meddra.lookup("HEADACHE", "MedDRA")
        assert result is not None
        assert result["pt"] == "Headache"

    def test_lookup_miss(self, meddra):
        result = meddra.lookup("rash", "MedDRA")
        assert result is None

    def test_wrong_dictionary(self, meddra):
        result = meddra.lookup("headache", "CTCAE")
        assert result is None

    def test_search_substring(self, meddra):
        results = meddra.search("head", "MedDRA")
        assert len(results) >= 2
        pts = {r["pt"] for r in results}
        assert "Headache" in pts

    def test_search_exact_scores_higher(self, meddra):
        results = meddra.search("headache", "MedDRA")
        # Exact match should be first
        assert results[0]["score"] == 1.0

    def test_search_max_results(self, meddra):
        results = meddra.search("head", "MedDRA", max_results=1)
        assert len(results) <= 1

    def test_search_wrong_dictionary(self, meddra):
        results = meddra.search("head", "CTCAE")
        assert results == []

    def test_empty_lookup(self):
        t = MedDRALookup()
        assert t.lookup("headache", "MedDRA") is None
        assert t.search("head", "MedDRA") == []

    def test_source_term_preserved(self, meddra):
        result = meddra.lookup("Headache", "MedDRA")
        assert result["source_term"] == "Headache"


class TestTerminologyInHarmonizeAgent:
    """Verify terminology lookup is wired into the harmonize resolution chain."""

    def test_agent_has_terminology_lookup(self):
        from agents.harmonize_agent import HarmonizeAgent
        agent = HarmonizeAgent()
        assert isinstance(agent.terminology_lookup, NoOpTerminologyLookup)

    def test_agent_accepts_custom_terminology(self):
        from agents.harmonize_agent import HarmonizeAgent
        meddra = MedDRALookup(preloaded_terms={
            "headache": {"pt": "Headache", "soc": "Nervous system disorders"}
        })
        agent = HarmonizeAgent(terminology_lookup=meddra)
        assert isinstance(agent.terminology_lookup, MedDRALookup)


# =========================================================================
# AE-04: Partial Date Utility
# =========================================================================

class TestParsePartialDate:
    """Verify parse_partial_date handles all expected formats."""

    def test_full_iso(self):
        r = parse_partial_date("2023-04-15")
        assert r == {"year": 2023, "month": 4, "day": 15, "precision": "day"}

    def test_year_month(self):
        r = parse_partial_date("2023-04")
        assert r == {"year": 2023, "month": 4, "day": None, "precision": "month"}

    def test_year_only(self):
        r = parse_partial_date("2023")
        assert r == {"year": 2023, "month": None, "day": None, "precision": "year"}

    def test_clinical_dd_mon_yyyy(self):
        r = parse_partial_date("15-APR-2023")
        assert r == {"year": 2023, "month": 4, "day": 15, "precision": "day"}

    def test_clinical_mon_yyyy(self):
        r = parse_partial_date("APR-2023")
        assert r == {"year": 2023, "month": 4, "day": None, "precision": "month"}

    def test_clinical_un_mon_yyyy(self):
        r = parse_partial_date("UN-APR-2023")
        assert r == {"year": 2023, "month": 4, "day": None, "precision": "month"}

    def test_clinical_unk_unk_yyyy(self):
        r = parse_partial_date("UNK-UNK-2023")
        assert r == {"year": 2023, "month": None, "day": None, "precision": "year"}

    def test_none_input(self):
        assert parse_partial_date(None) is None

    def test_empty_string(self):
        assert parse_partial_date("") is None

    def test_garbage(self):
        assert parse_partial_date("not-a-date") is None

    def test_sas_numeric_date(self):
        # 2023-01-01 = day 23011 from 1960-01-01 (approximately)
        r = parse_partial_date("23011")
        assert r is not None
        assert r["precision"] == "day"
        assert r["year"] == 2023

    def test_lowercase_month(self):
        r = parse_partial_date("apr-2023")
        assert r is not None
        assert r["month"] == 4


class TestImputePartialDate:
    """Verify date imputation follows CDISC AE rules."""

    # --- Start date imputation (earliest plausible) ---

    def test_start_full_date_unchanged(self):
        assert impute_partial_date("2023-04-15", "start") == "2023-04-15"

    def test_start_month_imputes_first(self):
        assert impute_partial_date("2023-04", "start") == "2023-04-01"

    def test_start_year_imputes_jan_first(self):
        assert impute_partial_date("2023", "start") == "2023-01-01"

    def test_start_clinical_format(self):
        assert impute_partial_date("APR-2023", "start") == "2023-04-01"

    # --- End date imputation (latest plausible) ---

    def test_end_full_date_unchanged(self):
        assert impute_partial_date("2023-04-15", "end") == "2023-04-15"

    def test_end_month_imputes_last_day(self):
        assert impute_partial_date("2023-04", "end") == "2023-04-30"

    def test_end_feb_non_leap(self):
        assert impute_partial_date("2023-02", "end") == "2023-02-28"

    def test_end_feb_leap(self):
        assert impute_partial_date("2024-02", "end") == "2024-02-29"

    def test_end_year_imputes_dec_31(self):
        assert impute_partial_date("2023", "end") == "2023-12-31"

    def test_end_clinical_format(self):
        assert impute_partial_date("APR-2023", "end") == "2023-04-30"

    # --- Edge cases ---

    def test_none_returns_none(self):
        assert impute_partial_date(None, "start") is None

    def test_empty_returns_none(self):
        assert impute_partial_date("", "end") is None

    def test_garbage_returns_none(self):
        assert impute_partial_date("not-a-date", "start") is None


class TestGetDatePrecision:
    """Verify precision detection."""

    def test_day_precision(self):
        assert get_date_precision("2023-04-15") == "day"

    def test_month_precision(self):
        assert get_date_precision("2023-04") == "month"

    def test_year_precision(self):
        assert get_date_precision("2023") == "year"

    def test_clinical_day(self):
        assert get_date_precision("15-APR-2023") == "day"

    def test_clinical_month(self):
        assert get_date_precision("APR-2023") == "month"

    def test_none(self):
        assert get_date_precision("garbage") is None
