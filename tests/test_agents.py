"""
Test suite for v4 Agents (Phase 2).

Tests:
    1. Agent initialization with SpecRegistry
    2. MapAgent spec-driven mapping
    3. HarmonizeAgent coded value resolution
    4. QCAgent spec-driven checks
    5. Race/ethnicity separation logic
"""

import pytest
import pandas as pd
from pathlib import Path

from concordia_pipeline_v4.spec_registry import SpecRegistry
from concordia_pipeline_v4.agents.base import PipelineContext
from concordia_pipeline_v4.agents.map_agent import MapAgent
from concordia_pipeline_v4.agents.harmonize_agent import HarmonizeAgent
from concordia_pipeline_v4.agents.qc_agent import QCAgent
from concordia_pipeline_v4.agents.review_agent import ReviewAgent
from concordia_pipeline_v4.agents.race_ethnicity import (
    separate_race_ethnicity,
    is_conflated_field,
)


KB_DIR = Path(__file__).parent.parent / "knowledge_base"


@pytest.fixture
def registry():
    return SpecRegistry(spec_base_dir=KB_DIR, domain="DM")


# ---------------------------------------------------------------------------
# 1. Agent Initialization with SpecRegistry
# ---------------------------------------------------------------------------

class TestAgentInitialization:

    def test_map_agent_with_registry(self, registry):
        agent = MapAgent(spec_registry=registry)
        assert agent.spec_registry is not None

    def test_harmonize_agent_with_registry(self, registry):
        agent = HarmonizeAgent(spec_registry=registry)
        assert agent.spec_registry is not None
        assert agent.provenance is not None

    def test_qc_agent_with_registry(self, registry):
        agent = QCAgent(spec_registry=registry)
        assert agent.spec_registry is not None

    def test_review_agent_with_registry(self, registry):
        agent = ReviewAgent(spec_registry=registry)
        assert agent.spec_registry is not None

    def test_agents_work_without_registry(self):
        """All agents should be instantiable without a registry."""
        MapAgent()
        HarmonizeAgent()
        QCAgent()
        ReviewAgent()


# ---------------------------------------------------------------------------
# 2. MapAgent Spec-Driven Mapping
# ---------------------------------------------------------------------------

class TestMapAgentSpecDriven:

    def test_output_schema_from_registry(self, registry):
        agent = MapAgent(spec_registry=registry)
        schema = agent._get_output_schema()
        assert len(schema) == 18
        assert schema[0] == "TRIAL"
        assert schema[-1] == "DOMAIN"

    def test_source_priority_from_registry(self, registry):
        agent = MapAgent(spec_registry=registry)
        sex_sources = agent._get_source_priority("SEX")
        assert "SEX" in sex_sources
        assert len(sex_sources) >= 2  # Should have synonyms from spec

    def test_mapping_with_sample_data(self, registry):
        agent = MapAgent(spec_registry=registry)
        df = pd.DataFrame({
            "SUBJID": ["001", "002", "003"],
            "SEX": ["M", "F", "M"],
            "RACE": ["White", "Asian", "Black"],
            "AGE": [45, 62, 38],
        })
        ctx = PipelineContext()
        ctx.set("df", df)
        ctx.set("trial_id", "NCT00554229")
        ctx.set("ingest_metadata", {})

        result = agent.execute(ctx)
        assert result.success
        mapped_df = ctx.get("df")
        assert len(mapped_df.columns) == 18
        assert "SEX" in mapped_df.columns
        assert "DOMAIN" in mapped_df.columns


# ---------------------------------------------------------------------------
# 3. HarmonizeAgent Coded Value Resolution
# ---------------------------------------------------------------------------

class TestHarmonizeCodedValues:

    def test_sex_synonym_resolution(self, registry):
        agent = HarmonizeAgent(spec_registry=registry, use_llm_fallback=False)
        lookup = agent._get_synonym_lookup("SEX")
        assert lookup.get("m") == "Male"
        assert lookup.get("f") == "Female"

    def test_race_allowed_values_no_other(self, registry):
        agent = HarmonizeAgent(spec_registry=registry, use_llm_fallback=False)
        allowed = agent._get_allowed_values("RACE")
        assert "White" in allowed
        assert "Other" not in allowed  # v4: no "Other" per OMB

    def test_sex_allowed_values_has_undifferentiated(self, registry):
        agent = HarmonizeAgent(spec_registry=registry, use_llm_fallback=False)
        allowed = agent._get_allowed_values("SEX")
        assert "Undifferentiated" in allowed  # v4 addition

    def test_ethnic_allowed_values(self, registry):
        agent = HarmonizeAgent(spec_registry=registry, use_llm_fallback=False)
        allowed = agent._get_allowed_values("ETHNIC")
        assert len(allowed) == 3
        assert "Hispanic or Latino" in allowed

    def test_harmonize_simple_data(self, registry):
        """End-to-end harmonize with simple pre-mapped data."""
        agent = HarmonizeAgent(spec_registry=registry, use_llm_fallback=False)
        df = pd.DataFrame({
            "TRIAL": ["NCT00554229", "NCT00554229"],
            "SUBJID": ["001", "002"],
            "SEX": ["Male", "Female"],
            "RACE": ["White", "Asian"],
            "AGE": [45, 62],
            "AGEU": ["Years", "Years"],
            "AGEGP": [None, None],
            "ETHNIC": ["Not Hispanic or Latino", "Unknown"],
            "COUNTRY": ["United States", "Japan"],
            "SITEID": ["101", "102"],
            "STUDYID": ["STUDY001", "STUDY001"],
            "USUBJID": ["STUDY001-001", "STUDY001-002"],
            "ARMCD": ["TRT", "PBO"],
            "ARM": ["Treatment", "Placebo"],
            "BRTHDTC": ["1979-01-15", "1962-06-20"],
            "RFSTDTC": ["2024-01-01", "2024-01-01"],
            "RFENDTC": ["2024-06-01", "2024-06-01"],
            "DOMAIN": ["DM", "DM"],
        })

        mapping_log = [
            {"output_variable": var, "source_column": var, "operation": "Copy"}
            for var in df.columns
        ]

        ctx = PipelineContext()
        ctx.set("df", df)
        ctx.set("mapping_log", mapping_log)
        ctx.set("dictionary", {})
        ctx.set("trial_id", "NCT00554229")

        result = agent.execute(ctx)
        assert result.success

        harmonized = ctx.get("harmonized_df")
        assert harmonized is not None
        assert len(harmonized) == 2
        assert agent.provenance.record_count > 0


# ---------------------------------------------------------------------------
# 4. QCAgent Spec-Driven Checks
# ---------------------------------------------------------------------------

class TestQCAgentSpecDriven:

    def test_required_variables_from_registry(self, registry):
        agent = QCAgent(spec_registry=registry)
        required = agent._get_required_variables()
        assert "TRIAL" in required
        assert "SUBJID" in required

    def test_coded_variables_from_registry(self, registry):
        agent = QCAgent(spec_registry=registry)
        coded = agent._get_coded_variables()
        assert "SEX" in coded
        assert "RACE" in coded

    def test_coded_value_check_against_spec(self, registry):
        """QC should flag values not in the spec's allowed list."""
        agent = QCAgent(spec_registry=registry)
        df = pd.DataFrame({
            "SEX": ["Male", "Female", "Intersex"],  # "Intersex" not in spec
            "RACE": ["White", "Other", "Asian"],      # "Other" not in v4 spec
        })
        issues = agent._check_coded_values(df)
        # Should flag both "Intersex" for SEX and "Other" for RACE
        assert len(issues) >= 2
        sex_issues = [i for i in issues if i["variable"] == "SEX"]
        race_issues = [i for i in issues if i["variable"] == "RACE"]
        assert len(sex_issues) >= 1
        assert len(race_issues) >= 1


# ---------------------------------------------------------------------------
# 5. Race/Ethnicity Separation
# ---------------------------------------------------------------------------

class TestRaceEthnicitySeparation:

    @pytest.fixture
    def race_values(self, registry):
        return registry.get_valid_values("RACE")

    @pytest.fixture
    def ethnic_values(self, registry):
        return registry.get_valid_values("ETHNIC")

    @pytest.fixture
    def race_synonyms(self, registry):
        return registry.get_synonym_lookup("RACE")

    def test_white_hispanic(self, race_values, ethnic_values, race_synonyms):
        race, ethnic, rc, ec, conflated = separate_race_ethnicity(
            "White, Hispanic", race_values, ethnic_values, race_synonyms
        )
        assert race == "White"
        assert ethnic == "Hispanic or Latino"
        assert conflated is True

    def test_hispanic_only(self, race_values, ethnic_values, race_synonyms):
        race, ethnic, rc, ec, conflated = separate_race_ethnicity(
            "Hispanic", race_values, ethnic_values, race_synonyms
        )
        assert ethnic == "Hispanic or Latino"
        assert race == "Unknown"
        assert conflated is True

    def test_white_non_hispanic(self, race_values, ethnic_values, race_synonyms):
        race, ethnic, rc, ec, conflated = separate_race_ethnicity(
            "White, Non-Hispanic", race_values, ethnic_values, race_synonyms
        )
        assert race == "White"
        assert ethnic == "Not Hispanic or Latino"
        assert conflated is True

    def test_plain_race(self, race_values, ethnic_values, race_synonyms):
        race, ethnic, rc, ec, conflated = separate_race_ethnicity(
            "Asian", race_values, ethnic_values, race_synonyms
        )
        assert race == "Asian"
        assert conflated is False

    def test_null_value(self, race_values, ethnic_values, race_synonyms):
        race, ethnic, rc, ec, conflated = separate_race_ethnicity(
            None, race_values, ethnic_values, race_synonyms
        )
        assert race == "Unknown"
        assert ethnic == "Unknown"

    def test_is_conflated_field_detection(self):
        values = pd.Series(["White, Hispanic", "Asian, Not Hispanic"])
        assert is_conflated_field("RACE_ETHNICITY", values) is True

        values = pd.Series(["White", "Asian", "Black"])
        assert is_conflated_field("RACE", values) is False
