"""
Provenance Tracking — First-class output for every harmonized value.

Usage:
    from provenance import ProvenanceTracker

    tracker = ProvenanceTracker()
    tracker.record("SEX", source_dataset_id="NCT00554229",
                   source_field_name="SEX", source_value_raw="1",
                   harmonized_value="Male", mapping_confidence="HIGH",
                   flags={"sex_gender_conflated": False})

    prov_df = tracker.to_dataframe()
"""

from .tracker import ProvenanceTracker

__all__ = ["ProvenanceTracker"]
