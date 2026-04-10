"""
Test suite for the Provenance Tracker.

Tests:
    1. Basic recording and export
    2. Batch recording
    3. Summary statistics
    4. Merge with harmonized DataFrame
    5. Filtering by variable
    6. Clear operations
"""

import pytest
import pandas as pd

from concordia_pipeline_v4.provenance.tracker import ProvenanceTracker
from spec_registry.models import ProvenanceRecord


class TestBasicRecording:

    def test_record_single(self):
        tracker = ProvenanceTracker()
        rec = tracker.record(
            variable="SEX",
            source_dataset_id="NCT00554229",
            source_field_name="SEX",
            source_value_raw="1",
            harmonized_value="Male",
            mapping_confidence="HIGH",
            flags={"sex_gender_conflated": False},
        )
        assert isinstance(rec, ProvenanceRecord)
        assert rec.variable == "SEX"
        assert rec.harmonized_value == "Male"
        assert tracker.record_count == 1

    def test_record_multiple(self):
        tracker = ProvenanceTracker()
        tracker.record(variable="SEX", harmonized_value="Male", mapping_confidence="HIGH")
        tracker.record(variable="SEX", harmonized_value="Female", mapping_confidence="HIGH")
        tracker.record(variable="RACE", harmonized_value="White", mapping_confidence="MEDIUM")
        assert tracker.record_count == 3

    def test_record_defaults(self):
        tracker = ProvenanceTracker()
        rec = tracker.record(variable="AGE")
        assert rec.source_dataset_id == ""
        assert rec.mapping_confidence == "HIGH"
        assert rec.flags == {}


class TestExport:

    def test_to_dataframe(self):
        tracker = ProvenanceTracker()
        tracker.record(variable="SEX", source_value_raw="M", harmonized_value="Male",
                       mapping_confidence="HIGH", flags={"sex_gender_conflated": False})
        tracker.record(variable="RACE", source_value_raw="Caucasian", harmonized_value="White",
                       mapping_confidence="MEDIUM", flags={"race_ethnicity_conflated": True})

        df = tracker.to_dataframe()
        assert len(df) == 2
        assert "variable" in df.columns
        assert "harmonized_value" in df.columns
        assert "flag_sex_gender_conflated" in df.columns
        assert "flag_race_ethnicity_conflated" in df.columns

    def test_to_dataframe_empty(self):
        tracker = ProvenanceTracker()
        df = tracker.to_dataframe()
        assert len(df) == 0
        assert "variable" in df.columns

    def test_to_dataframe_filtered(self):
        tracker = ProvenanceTracker()
        tracker.record(variable="SEX", harmonized_value="Male")
        tracker.record(variable="RACE", harmonized_value="White")
        tracker.record(variable="SEX", harmonized_value="Female")

        df = tracker.to_dataframe(variable="SEX")
        assert len(df) == 2
        assert all(df["variable"] == "SEX")


class TestSummary:

    def test_summary_counts(self):
        tracker = ProvenanceTracker()
        tracker.record(variable="SEX", mapping_confidence="HIGH")
        tracker.record(variable="SEX", mapping_confidence="HIGH")
        tracker.record(variable="RACE", mapping_confidence="MEDIUM")
        tracker.record(variable="RACE", mapping_confidence="UNMAPPED")

        summary = tracker.summary()
        assert summary["total_records"] == 4
        assert summary["by_variable"]["SEX"] == 2
        assert summary["by_variable"]["RACE"] == 2
        assert summary["by_confidence"]["HIGH"] == 2
        assert summary["by_confidence"]["MEDIUM"] == 1
        assert summary["by_confidence"]["UNMAPPED"] == 1
        assert summary["unmapped_count"] == 1
        assert summary["low_confidence_count"] == 0

    def test_summary_empty(self):
        tracker = ProvenanceTracker()
        summary = tracker.summary()
        assert summary["total_records"] == 0


class TestMerge:

    def test_merge_with_harmonized(self):
        tracker = ProvenanceTracker()
        tracker.record(variable="SEX", harmonized_value="Male", mapping_confidence="HIGH",
                       flags={"sex_gender_conflated": False})
        tracker.record(variable="SEX", harmonized_value="Female", mapping_confidence="HIGH",
                       flags={"sex_gender_conflated": False})

        harmonized_df = pd.DataFrame({
            "SEX": ["Male", "Female"],
            "RACE": ["White", "Asian"],
        })

        merged = tracker.merge_with_harmonized(harmonized_df)
        assert "SEX_confidence" in merged.columns
        assert "SEX_flag_sex_gender_conflated" in merged.columns
        assert list(merged["SEX_confidence"]) == ["HIGH", "HIGH"]


class TestClear:

    def test_clear_all(self):
        tracker = ProvenanceTracker()
        tracker.record(variable="SEX")
        tracker.record(variable="RACE")
        tracker.clear()
        assert tracker.record_count == 0

    def test_clear_variable(self):
        tracker = ProvenanceTracker()
        tracker.record(variable="SEX")
        tracker.record(variable="RACE")
        tracker.clear(variable="SEX")
        assert tracker.record_count == 1
        assert tracker.get_records()[0].variable == "RACE"
