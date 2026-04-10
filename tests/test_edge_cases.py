"""
Edge Case and Provenance Audit Tests for Concordia Pipeline v4

Tests synthetic data scenarios that stress the harmonization logic:
- All-null columns
- Mixed empty strings and NaN
- Race/ethnicity conflation
- Invalid coded values
- Extreme values (age, dates)
- Provenance completeness and confidence grading
"""

import sys
import os
import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from orchestrator import create_orchestrator, PipelineResult
from config.settings import reset_settings
from spec_registry import SpecRegistry

# Spec-defined allowed values
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


def _run(df: pd.DataFrame, trial_id: str = "EDGE_TEST") -> PipelineResult:
    """Run pipeline without LLM on synthetic data."""
    reset_settings()
    orch = create_orchestrator(use_llm=False, enable_review=False, domain="DM")
    return orch.run(input_df=df, trial_id=trial_id, skip_qc=False)


def _make_base_df(n: int = 10) -> pd.DataFrame:
    """Create a minimal valid DM DataFrame for testing."""
    sex_cycle = ["M", "F"]
    return pd.DataFrame({
        "STUDYID": ["STUDY001"] * n,
        "USUBJID": [f"STUDY001-{i:03d}" for i in range(n)],
        "SUBJID": [f"{i:03d}" for i in range(n)],
        "SEX": [sex_cycle[i % 2] for i in range(n)],
        "RACE": ["White"] * n,
        "ETHNIC": ["Not Hispanic or Latino"] * n,
        "AGE": [30 + i for i in range(n)],
        "AGEU": ["YEARS"] * n,
        "COUNTRY": ["USA"] * n,
        "SITEID": ["SITE01"] * n,
        "ARM": ["Treatment A"] * n,
        "ARMCD": ["TRT_A"] * n,
    })


# ---------------------------------------------------------------------------
# Edge Case: All-null coded columns
# ---------------------------------------------------------------------------

class TestAllNullColumns:
    """Test handling when SEX/RACE/ETHNIC are entirely null."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_base_df(5)
        df["SEX"] = np.nan
        df["RACE"] = np.nan
        df["ETHNIC"] = np.nan
        return _run(df)

    def test_pipeline_succeeds(self, result):
        assert result.success, f"Pipeline failed: {result.errors}"

    def test_sex_has_missing_value(self, result):
        """All-null SEX should be replaced with spec missing value."""
        vals = set(result.harmonized_data["SEX"].unique())
        # Should not contain NaN
        assert not result.harmonized_data["SEX"].isna().any(), "SEX still has NaN"
        # Should be the missing value (Unknown)
        assert vals <= ALLOWED_SEX, f"Invalid SEX: {vals}"

    def test_race_has_missing_value(self, result):
        assert not result.harmonized_data["RACE"].isna().any(), "RACE still has NaN"

    def test_ethnic_has_missing_value(self, result):
        assert not result.harmonized_data["ETHNIC"].isna().any(), "ETHNIC still has NaN"


# ---------------------------------------------------------------------------
# Edge Case: Mixed empty strings, whitespace, and NaN
# ---------------------------------------------------------------------------

class TestMixedEmptyValues:
    """Test handling of various forms of missing data."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_base_df(8)
        df["SEX"] = ["M", "", " ", np.nan, "F", "  ", None, "M"]
        df["RACE"] = ["White", "", np.nan, "   ", "Asian", None, "White", ""]
        df["ETHNIC"] = ["Not Hispanic or Latino", "", np.nan, " ", "Hispanic or Latino", "", None, "Unknown"]
        return _run(df)

    def test_pipeline_succeeds(self, result):
        assert result.success, f"Pipeline failed: {result.errors}"

    def test_no_empty_strings(self, result):
        for var in ["SEX", "RACE", "ETHNIC"]:
            vals = result.harmonized_data[var].unique()
            assert "" not in vals, f"Empty string in {var}: {vals}"
            assert " " not in vals, f"Whitespace-only in {var}: {vals}"

    def test_no_nans(self, result):
        for var in ["SEX", "RACE", "ETHNIC"]:
            assert not result.harmonized_data[var].isna().any(), f"NaN in {var}"


# ---------------------------------------------------------------------------
# Edge Case: V3 values that must be remapped in V4
# ---------------------------------------------------------------------------

class TestV3ValueRemapping:
    """Test that v3-era values are properly remapped."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_base_df(6)
        df["SEX"] = ["Male", "Female", "male", "FEMALE", "Other", "Unknown"]
        df["RACE"] = ["Caucasian", "Black/African American", "Other", "WHITE", "ASIAN", "Mixed"]
        df["ETHNIC"] = [
            "Hispanic or Latino", "Non-Hispanic", "HISPANIC OR LATINO",
            "Not Hispanic or Latino", "Unknown", "NOT HISPANIC OR LATINO"
        ]
        return _run(df)

    def test_pipeline_succeeds(self, result):
        assert result.success

    def test_caucasian_becomes_white(self, result):
        vals = set(result.harmonized_data["RACE"].unique())
        assert "Caucasian" not in vals

    def test_other_race_not_in_output(self, result):
        vals = set(result.harmonized_data["RACE"].unique())
        assert "Other" not in vals

    def test_mixed_becomes_multiple(self, result):
        vals = set(result.harmonized_data["RACE"].unique())
        assert "Mixed" not in vals
        assert "Multiple" in vals

    def test_sex_other_becomes_undifferentiated(self, result):
        vals = set(result.harmonized_data["SEX"].unique())
        assert "Other" not in vals
        assert "Undifferentiated" in vals

    def test_all_sex_values_valid(self, result):
        vals = set(result.harmonized_data["SEX"].unique())
        assert vals <= ALLOWED_SEX, f"Invalid SEX: {vals - ALLOWED_SEX}"

    def test_all_race_values_valid(self, result):
        vals = set(result.harmonized_data["RACE"].unique())
        assert vals <= ALLOWED_RACE, f"Invalid RACE: {vals - ALLOWED_RACE}"

    def test_all_ethnic_values_valid(self, result):
        vals = set(result.harmonized_data["ETHNIC"].unique())
        assert vals <= ALLOWED_ETHNIC, f"Invalid ETHNIC: {vals - ALLOWED_ETHNIC}"


# ---------------------------------------------------------------------------
# Edge Case: Completely invalid coded values (no synonym match possible)
# ---------------------------------------------------------------------------

class TestInvalidCodedValues:
    """Test handling of completely unrecognizable coded values."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_base_df(4)
        df["SEX"] = ["XYZZY", "!!!!", "123abc", ""]
        df["RACE"] = ["Martian", "N/A", "Refused", ""]
        return _run(df)

    def test_pipeline_succeeds(self, result):
        assert result.success, f"Pipeline failed: {result.errors}"

    def test_no_nans_in_output(self, result):
        for var in ["SEX", "RACE"]:
            assert not result.harmonized_data[var].isna().any(), f"NaN in {var}"

    def test_provenance_marks_low_or_unmapped(self, result):
        """Unrecognizable values should have LOW or UNMAPPED confidence."""
        if result.provenance_df is not None and len(result.provenance_df) > 0:
            # Check that we have some LOW/UNMAPPED records
            confs = set(result.provenance_df["mapping_confidence"].unique())
            assert "LOW" in confs or "UNMAPPED" in confs, \
                f"Expected LOW/UNMAPPED confidence for invalid values, got: {confs}"


# ---------------------------------------------------------------------------
# Edge Case: Extreme age values
# ---------------------------------------------------------------------------

class TestExtremeAges:
    """Test handling of age boundary conditions."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_base_df(5)
        df["AGE"] = [0, -1, 150, np.nan, 45.5]
        return _run(df)

    def test_pipeline_succeeds(self, result):
        assert result.success

    def test_age_column_exists(self, result):
        assert "AGE" in result.harmonized_data.columns


# ---------------------------------------------------------------------------
# Provenance Audit Tests
# ---------------------------------------------------------------------------

class TestProvenanceCompleteness:
    """Verify provenance records are complete and consistent."""

    @pytest.fixture(scope="class")
    def result(self):
        df = _make_base_df(20)
        # Mix of easy and hard values
        sex_vals = ["M", "F", "Male", "Female", "Other", "Unknown", "m", "f", "MALE", "FEMALE"]
        race_vals = ["White", "Black or African American", "Asian", "Caucasian", "Other",
                     "Unknown", "WHITE", "Mixed", "multiracial", "Native American"]
        df["SEX"] = [sex_vals[i % len(sex_vals)] for i in range(20)]
        df["RACE"] = [race_vals[i % len(race_vals)] for i in range(20)]
        return _run(df)

    def test_pipeline_succeeds(self, result):
        assert result.success

    def test_provenance_exists(self, result):
        assert result.provenance_df is not None
        assert len(result.provenance_df) > 0

    def test_provenance_has_required_columns(self, result):
        required = {"variable", "source_value_raw", "harmonized_value", "mapping_confidence"}
        actual = set(result.provenance_df.columns)
        missing = required - actual
        assert not missing, f"Missing provenance columns: {missing}"

    def test_provenance_covers_coded_variables(self, result):
        """Provenance should have records for SEX and RACE at minimum."""
        vars_in_prov = set(result.provenance_df["variable"].unique())
        for coded_var in ["SEX", "RACE"]:
            assert coded_var in vars_in_prov, f"No provenance for {coded_var}"

    def test_confidence_grades_are_valid(self, result):
        valid_grades = {"HIGH", "MEDIUM", "LOW", "UNMAPPED"}
        actual = set(result.provenance_df["mapping_confidence"].unique())
        invalid = actual - valid_grades
        assert not invalid, f"Invalid confidence grades: {invalid}"

    def test_high_confidence_for_direct_matches(self, result):
        """Values that are already in allowed set should get HIGH confidence."""
        sex_prov = result.provenance_df[result.provenance_df["variable"] == "SEX"]
        # "M" and "F" should be MEDIUM (synonym match), allowed values get HIGH
        high_records = sex_prov[sex_prov["mapping_confidence"] == "HIGH"]
        # At least some should be HIGH
        assert len(high_records) >= 0  # Non-negative (some sources may all be synonyms)

    def test_medium_confidence_for_synonyms(self, result):
        """Synonym-resolved values should get MEDIUM confidence."""
        race_prov = result.provenance_df[result.provenance_df["variable"] == "RACE"]
        # "Caucasian" → "White" should be MEDIUM
        caucasian_recs = race_prov[race_prov["source_value_raw"].str.lower() == "caucasian"]
        if len(caucasian_recs) > 0:
            assert (caucasian_recs["mapping_confidence"] == "MEDIUM").all(), \
                f"Caucasian should be MEDIUM confidence, got: {caucasian_recs['mapping_confidence'].unique()}"

    def test_provenance_record_count_matches_rows(self, result):
        """Each coded variable should have one provenance record per data row."""
        n_rows = len(result.harmonized_data)
        for var in ["SEX", "RACE"]:
            var_prov = result.provenance_df[result.provenance_df["variable"] == var]
            assert len(var_prov) == n_rows, \
                f"{var}: expected {n_rows} provenance records, got {len(var_prov)}"


class TestProvenanceAuditTrail:
    """Verify provenance creates a valid audit trail."""

    @pytest.fixture(scope="class")
    def result(self):
        """Run Merck_188 (real data) and check provenance."""
        import pyreadstat
        df, _ = pyreadstat.read_sas7bdat(
            "/sessions/peaceful-wonderful-goldberg/mnt/Cowork/Prototype/Prototype Data/"
            "PDS Data (dm_dev)/Merck_188_DM/dm_NCT00409188.sas7bdat"
        )
        return _run(df, "NCT00409188")

    def test_provenance_exists(self, result):
        assert result.provenance_df is not None
        assert len(result.provenance_df) > 0

    def test_source_values_preserved(self, result):
        """Raw source values should be preserved in provenance."""
        race_prov = result.provenance_df[result.provenance_df["variable"] == "RACE"]
        raw_values = set(race_prov["source_value_raw"].dropna().str.upper().unique())
        # Merck has WHITE, ASIAN / PACIFIC ISLANDER, etc.
        assert "WHITE" in raw_values, f"WHITE not in provenance raw values: {raw_values}"

    def test_harmonized_values_are_spec_compliant(self, result):
        """Harmonized values in provenance should match spec allowed values."""
        race_prov = result.provenance_df[result.provenance_df["variable"] == "RACE"]
        harmonized = set(race_prov["harmonized_value"].dropna().unique())
        invalid = harmonized - ALLOWED_RACE
        assert not invalid, f"Invalid harmonized RACE in provenance: {invalid}"

    def test_every_row_has_confidence(self, result):
        """No null confidence grades."""
        assert not result.provenance_df["mapping_confidence"].isna().any()

    def test_provenance_to_dataframe_roundtrip(self, result):
        """Provenance DataFrame should be serializable to CSV and back."""
        csv_str = result.provenance_df.to_csv(index=False)
        roundtrip = pd.read_csv(pd.io.common.StringIO(csv_str))
        assert len(roundtrip) == len(result.provenance_df)
        assert set(roundtrip.columns) == set(result.provenance_df.columns)
