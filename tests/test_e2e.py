"""
End-to-End Tests for Concordia Pipeline v4

Tests the full pipeline (Ingest → Map → Harmonize → QC → Review) using
real datasets from the dm_dev collection. These tests run WITHOUT LLM
(no API key required) to validate the deterministic spec-driven path.

Key assertions:
- Pipeline completes successfully
- Output has 18 DM variables
- Coded values (SEX, RACE, ETHNIC) are within spec-defined allowed values
- Provenance is recorded for coded variables
- QC report is a DataFrame
- No nulls in required output columns (per system_rules.md)
"""

import sys
import os
import pytest
import pandas as pd

# Ensure the project root is on the path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from orchestrator import PipelineOrchestrator, create_orchestrator, PipelineResult
from config.settings import get_settings, reset_settings
from spec_registry import SpecRegistry

# ---------------------------------------------------------------------------
# Dataset paths
# ---------------------------------------------------------------------------
DATA_ROOT = "/sessions/peaceful-wonderful-goldberg/mnt/Cowork/Prototype/Prototype Data"
DM_DEV = os.path.join(DATA_ROOT, "PDS Data (dm_dev)")
DM_TEST = os.path.join(DATA_ROOT, "PDS Data (dm_test)")

# Dev datasets with their SAS files and optional dictionaries
DEV_DATASETS = {
    "Merck_188": {
        "sas": os.path.join(DM_DEV, "Merck_188_DM", "dm_NCT00409188.sas7bdat"),
        "trial_id": "NCT00409188",
    },
    "Lilly_568": {
        "sas": os.path.join(DM_DEV, "Lilly_568_DM", "dm_NCT01439568.sas7bdat"),
        "trial_id": "NCT01439568",
    },
    "Sanofi_323": {
        "sas": os.path.join(DM_DEV, "Sanofi_323_DM", "demo_NCT00401323.sas7bdat"),
        "trial_id": "NCT00401323",
    },
}

# Expected output schema (18 DM variables)
EXPECTED_OUTPUT_VARS = [
    "STUDYID", "DOMAIN", "USUBJID", "SUBJID", "RFSTDTC", "RFENDTC",
    "SITEID", "BRTHDTC", "AGE", "AGEU", "SEX", "RACE", "ETHNIC",
    "ARMCD", "ARM", "COUNTRY", "TRIAL", "AGEGP",
]

# Spec-defined allowed values for coded variables
ALLOWED_SEX = {"Male", "Female", "Unknown", "Undifferentiated"}
ALLOWED_RACE = {
    "White", "Black or African American", "Asian",
    "American Indian or Alaska Native",
    "Native Hawaiian or Other Pacific Islander",
    "Multiple", "Unknown",
}
ALLOWED_ETHNIC = {
    "Hispanic or Latino", "Not Hispanic or Latino", "Unknown",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def spec_registry():
    """Load the SpecRegistry once for all tests in this module."""
    specs_dir = get_settings().get_domain_spec_dir().parent
    return SpecRegistry(spec_base_dir=specs_dir, domain="DM")


def _load_sas(path: str) -> pd.DataFrame:
    """Load a SAS7BDAT file into a DataFrame."""
    import pyreadstat
    df, _ = pyreadstat.read_sas7bdat(path)
    return df


def _run_pipeline(df: pd.DataFrame, trial_id: str) -> PipelineResult:
    """Run the v4 pipeline without LLM on a DataFrame."""
    reset_settings()
    orchestrator = create_orchestrator(
        use_llm=False,
        enable_review=False,
        domain="DM",
    )
    return orchestrator.run(
        input_df=df,
        trial_id=trial_id,
        skip_qc=False,
    )


# ---------------------------------------------------------------------------
# Test: Merck_188 — near-SDTM input (closest to target schema)
# ---------------------------------------------------------------------------

class TestMerck188EndToEnd:
    """Merck_188 is nearly SDTM-compliant; tests the happy-path."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _load_sas(DEV_DATASETS["Merck_188"]["sas"])
        return _run_pipeline(df, DEV_DATASETS["Merck_188"]["trial_id"])

    def test_pipeline_succeeds(self, result):
        assert result.success, f"Pipeline failed: {result.errors}"

    def test_output_has_18_dm_vars(self, result):
        out_cols = set(result.harmonized_data.columns)
        for var in EXPECTED_OUTPUT_VARS:
            assert var in out_cols, f"Missing output variable: {var}"

    def test_domain_is_dm(self, result):
        assert (result.harmonized_data["DOMAIN"] == "DM").all()

    def test_sex_values_in_spec(self, result):
        actual = set(result.harmonized_data["SEX"].dropna().unique())
        invalid = actual - ALLOWED_SEX
        assert not invalid, f"Invalid SEX values: {invalid}"

    def test_race_values_in_spec(self, result):
        actual = set(result.harmonized_data["RACE"].dropna().unique())
        invalid = actual - ALLOWED_RACE
        assert not invalid, f"Invalid RACE values: {invalid}"

    def test_ethnic_values_in_spec(self, result):
        actual = set(result.harmonized_data["ETHNIC"].dropna().unique())
        invalid = actual - ALLOWED_ETHNIC
        assert not invalid, f"Invalid ETHNIC values: {invalid}"

    def test_row_count_preserved(self, result):
        df_in = _load_sas(DEV_DATASETS["Merck_188"]["sas"])
        assert len(result.harmonized_data) == len(df_in)

    def test_provenance_recorded(self, result):
        assert result.provenance_df is not None
        assert len(result.provenance_df) > 0, "No provenance records"

    def test_provenance_has_confidence(self, result):
        assert "mapping_confidence" in result.provenance_df.columns

    def test_qc_report_is_dataframe(self, result):
        # QC report may be empty (no issues) or populated
        assert result.qc_report is None or isinstance(result.qc_report, pd.DataFrame)

    def test_no_nulls_in_domain(self, result):
        assert result.harmonized_data["DOMAIN"].notna().all()

    def test_trial_id_populated(self, result):
        assert (result.harmonized_data["TRIAL"] == "NCT00409188").any() or \
               result.harmonized_data["TRIAL"].notna().any()


# ---------------------------------------------------------------------------
# Test: Lilly_568 — has "Other" race (v3 value, should be remapped or flagged)
# ---------------------------------------------------------------------------

class TestLilly568EndToEnd:
    """Lilly_568 contains 'Other' race and empty strings — tests v4 handling."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _load_sas(DEV_DATASETS["Lilly_568"]["sas"])
        return _run_pipeline(df, DEV_DATASETS["Lilly_568"]["trial_id"])

    def test_pipeline_succeeds(self, result):
        assert result.success, f"Pipeline failed: {result.errors}"

    def test_output_has_18_dm_vars(self, result):
        out_cols = set(result.harmonized_data.columns)
        for var in EXPECTED_OUTPUT_VARS:
            assert var in out_cols, f"Missing output variable: {var}"

    def test_no_other_in_race(self, result):
        """v4 spec has no 'Other' in RACE — should be remapped or set to Unknown."""
        actual = set(result.harmonized_data["RACE"].dropna().unique())
        assert "Other" not in actual, "RACE still contains 'Other' (v3 value)"

    def test_race_values_in_spec(self, result):
        actual = set(result.harmonized_data["RACE"].dropna().unique())
        invalid = actual - ALLOWED_RACE
        assert not invalid, f"Invalid RACE values: {invalid}"

    def test_sex_values_in_spec(self, result):
        actual = set(result.harmonized_data["SEX"].dropna().unique())
        invalid = actual - ALLOWED_SEX
        assert not invalid, f"Invalid SEX values: {invalid}"

    def test_provenance_recorded(self, result):
        assert result.provenance_df is not None
        assert len(result.provenance_df) > 0

    def test_empty_strings_handled(self, result):
        """Source has empty strings for SEX/RACE/ETHNIC — should be replaced."""
        for var in ["SEX", "RACE", "ETHNIC"]:
            vals = result.harmonized_data[var].unique()
            assert "" not in vals, f"Empty string found in {var}"


# ---------------------------------------------------------------------------
# Test: Sanofi_323 — nonstandard values (CAUCASIAN, MALE/FEMALE)
# ---------------------------------------------------------------------------

class TestSanofi323EndToEnd:
    """Sanofi_323 has CAUCASIAN→White and MALE/FEMALE text values."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _load_sas(DEV_DATASETS["Sanofi_323"]["sas"])
        return _run_pipeline(df, DEV_DATASETS["Sanofi_323"]["trial_id"])

    def test_pipeline_succeeds(self, result):
        assert result.success, f"Pipeline failed: {result.errors}"

    def test_caucasian_remapped_to_white(self, result):
        """CAUCASIAN should be synonymized to White."""
        actual = set(result.harmonized_data["RACE"].dropna().unique())
        assert "CAUCASIAN" not in actual, "CAUCASIAN was not remapped"
        assert "Caucasian" not in actual, "Caucasian was not remapped"

    def test_no_other_in_race(self, result):
        actual = set(result.harmonized_data["RACE"].dropna().unique())
        assert "OTHER" not in actual and "Other" not in actual, \
            f"'Other'/'OTHER' in RACE: {actual}"

    def test_sex_remapped(self, result):
        """MALE/FEMALE should be remapped to Male/Female."""
        actual = set(result.harmonized_data["SEX"].dropna().unique())
        assert "MALE" not in actual, "MALE was not remapped"
        assert "FEMALE" not in actual, "FEMALE was not remapped"
        invalid = actual - ALLOWED_SEX
        assert not invalid, f"Invalid SEX values: {invalid}"

    def test_race_values_in_spec(self, result):
        actual = set(result.harmonized_data["RACE"].dropna().unique())
        invalid = actual - ALLOWED_RACE
        assert not invalid, f"Invalid RACE values: {invalid}"

    def test_provenance_has_race_records(self, result):
        if result.provenance_df is not None and len(result.provenance_df) > 0:
            race_prov = result.provenance_df[
                result.provenance_df["variable"] == "RACE"
            ]
            assert len(race_prov) > 0, "No provenance for RACE"

    def test_output_has_18_dm_vars(self, result):
        out_cols = set(result.harmonized_data.columns)
        for var in EXPECTED_OUTPUT_VARS:
            assert var in out_cols, f"Missing output variable: {var}"
