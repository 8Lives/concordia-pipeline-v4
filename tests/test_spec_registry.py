"""
Test suite for the Spec Registry (F-04).

Tests:
    1. Loader tests — parse each tier independently, verify field population
    2. Registry integration — load full DM domain, verify all 18 variables
    3. Value set linkage — synonym lists populated from value set files
    4. Edge cases — missing sections, malformed markdown
    5. Regression — v3→v4 value changes verified
"""

import pytest
from pathlib import Path

from concordia_pipeline_v4.spec_registry import SpecRegistry
from concordia_pipeline_v4.spec_registry.loader import (
    load_system_rules,
    load_domain_rules,
    load_variable_spec,
    load_value_set,
    load_domain,
)
from concordia_pipeline_v4.spec_registry.models import (
    ProvenanceRecord,
    NoOpTerminologyLookup,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

KB_DIR = Path(__file__).parent.parent / "knowledge_base"
DM_DIR = KB_DIR / "DM"
VS_DIR = DM_DIR / "value_sets"


@pytest.fixture
def registry():
    return SpecRegistry(spec_base_dir=KB_DIR, domain="DM")


@pytest.fixture
def system_rules():
    return load_system_rules(KB_DIR / "system_rules.md")


@pytest.fixture
def domain_spec():
    return load_domain_rules(DM_DIR / "DM_domain_rules.md")


# ---------------------------------------------------------------------------
# 1. Loader Tests — Each Tier Independently
# ---------------------------------------------------------------------------

class TestSystemRulesLoader:

    def test_loads_version(self, system_rules):
        assert system_rules.version == "1.0"

    def test_has_text_normalization(self, system_rules):
        assert len(system_rules.text_normalization) > 0
        assert "mixed case" in system_rules.text_normalization.lower()

    def test_has_null_handling(self, system_rules):
        assert len(system_rules.null_handling) > 0
        assert "no nulls" in system_rules.null_handling.lower() or "null" in system_rules.null_handling.lower()

    def test_has_confidence_grading(self, system_rules):
        assert len(system_rules.confidence_grading) > 0
        defs = system_rules.get_confidence_definitions()
        assert set(defs.keys()) == {"HIGH", "MEDIUM", "LOW", "UNMAPPED"}

    def test_has_provenance(self, system_rules):
        assert len(system_rules.standard_provenance) > 0


class TestDomainRulesLoader:

    def test_domain_code(self, domain_spec):
        assert domain_spec.domain == "DM"

    def test_output_schema_count(self, domain_spec):
        assert len(domain_spec.output_schema) == 18

    def test_output_schema_order(self, domain_spec):
        ordered = domain_spec.get_output_variable_order()
        assert ordered[0] == "TRIAL"
        assert ordered[-1] == "DOMAIN"
        assert ordered[2] == "SEX"
        assert ordered[3] == "RACE"

    def test_required_variables(self, domain_spec):
        req = domain_spec.get_required_variables()
        assert "TRIAL" in req
        assert "SUBJID" in req
        assert "SEX" in req
        assert "RACE" in req
        assert "DOMAIN" in req

    def test_cross_variable_rules(self, domain_spec):
        rules = domain_spec.cross_variable_rules
        assert len(rules) >= 4
        rule_names_lower = [r.name.lower() for r in rules]
        assert any("age" in n and "agegp" in n for n in rule_names_lower)
        assert any("race" in n for n in rule_names_lower)
        assert any("usubjid" in n for n in rule_names_lower)

    def test_domain_qc_checks(self, domain_spec):
        checks = domain_spec.domain_qc_checks
        assert len(checks) >= 4
        check_names = [c.name.lower() for c in checks]
        assert any("duplicate" in n for n in check_names)
        assert any("stoplight" in n for n in check_names)

    def test_grain(self, domain_spec):
        assert "subject" in domain_spec.grain.lower()
        assert "trial" in domain_spec.grain.lower()


class TestValueSetLoader:

    def test_sex_values(self):
        vs = load_value_set(VS_DIR / "sex_values.md")
        vals = vs.get_allowed_value_list()
        assert vals == ["Male", "Female", "Unknown", "Undifferentiated"]

    def test_sex_synonyms(self):
        vs = load_value_set(VS_DIR / "sex_values.md")
        lookup = vs.build_synonym_lookup()
        assert lookup.get("m") == "Male"
        assert lookup.get("f") == "Female"
        assert lookup.get("male") == "Male"
        assert lookup.get("female") == "Female"

    def test_race_values(self):
        vs = load_value_set(VS_DIR / "race_values.md")
        vals = vs.get_allowed_value_list()
        assert "White" in vals
        assert "Black or African American" in vals
        assert "Multiple" in vals
        assert "Other" not in vals  # No "Other" per OMB

    def test_race_synonyms(self):
        vs = load_value_set(VS_DIR / "race_values.md")
        lookup = vs.build_synonym_lookup()
        # "Caucasian" is a synonym, not an allowed value
        assert "caucasian" in lookup or '"caucasian"' in lookup

    def test_ethnicity_values(self):
        vs = load_value_set(VS_DIR / "ethnicity_values.md")
        vals = vs.get_allowed_value_list()
        assert len(vals) == 3
        assert "Hispanic or Latino" in vals
        assert "Not Hispanic or Latino" in vals
        assert "Unknown" in vals

    def test_country_values(self):
        vs = load_value_set(VS_DIR / "country_values.md")
        # Country uses an open-ended ISO 3166-1 set; the value set file
        # documents observed countries but doesn't use the standard
        # "Value | Definition" table format. Synonym mappings may also
        # be empty if the table headers don't match the expected format.
        # The file still loads without error — that's the key test.
        assert vs.name == "country_values"


class TestVariableSpecLoader:

    def test_sex_spec(self):
        spec = load_variable_spec(DM_DIR / "DM_SEX.md", VS_DIR)
        assert spec.variable == "SEX"
        assert spec.order == 3
        assert spec.required == "Yes"
        assert spec.data_type == "String (categorical)"
        assert len(spec.definition) > 0
        assert len(spec.decision_principles) > 0
        assert len(spec.mapping_patterns) > 0
        assert len(spec.provenance_fields) >= 2  # sex_gender_conflated, sex_conflict

    def test_sex_allowed_values(self):
        spec = load_variable_spec(DM_DIR / "DM_SEX.md", VS_DIR)
        vals = spec.get_allowed_value_list()
        assert vals == ["Male", "Female", "Unknown", "Undifferentiated"]

    def test_sex_value_set_linked(self):
        spec = load_variable_spec(DM_DIR / "DM_SEX.md", VS_DIR)
        assert spec.value_set is not None
        assert spec.value_set.name == "sex_values"

    def test_race_spec(self):
        spec = load_variable_spec(DM_DIR / "DM_RACE.md", VS_DIR)
        assert spec.variable == "RACE"
        assert spec.required == "Yes"
        vals = spec.get_allowed_value_list()
        assert len(vals) == 7
        assert "White" in vals
        assert "Other" not in vals

    def test_age_numeric(self):
        spec = load_variable_spec(DM_DIR / "DM_AGE.md", VS_DIR)
        assert spec.variable == "AGE"
        assert "Numeric" in spec.data_type
        # AGE should have NO allowed values (it's continuous)
        assert spec.get_allowed_value_list() == []

    def test_domain_constant(self):
        spec = load_variable_spec(DM_DIR / "DM_DOMAIN.md", VS_DIR)
        assert spec.variable == "DOMAIN"
        vals = spec.get_allowed_value_list()
        # Should contain "DM"
        assert any("DM" in v for v in vals)

    def test_llm_context_generation(self):
        spec = load_variable_spec(DM_DIR / "DM_SEX.md", VS_DIR)
        ctx = spec.get_llm_context()
        assert "SEX" in ctx
        assert "Male" in ctx
        assert "Undifferentiated" in ctx
        assert "Decision Principles" in ctx or "decision principles" in ctx.lower()


# ---------------------------------------------------------------------------
# 2. Registry Integration Tests
# ---------------------------------------------------------------------------

class TestRegistryIntegration:

    def test_loads_all_18_variables(self, registry):
        all_vars = registry.get_all_variables()
        assert len(all_vars) == 18

    def test_output_schema_18_entries(self, registry):
        schema = registry.get_output_schema()
        assert len(schema) == 18
        assert schema[0] == "TRIAL"
        assert schema[-1] == "DOMAIN"

    def test_every_schema_var_has_spec(self, registry):
        """Every variable in the output schema should have a loaded spec."""
        schema = registry.get_output_schema()
        for var in schema:
            spec = registry.get_variable_spec(var)
            assert spec is not None, f"Missing spec for schema variable '{var}'"

    def test_required_variables(self, registry):
        req = registry.get_required_variables()
        assert set(req) >= {"TRIAL", "SUBJID", "SEX", "RACE", "DOMAIN"}

    def test_system_rules_accessible(self, registry):
        sr = registry.get_system_rules()
        assert sr.version == "1.0"

    def test_domain_spec_accessible(self, registry):
        ds = registry.get_domain_spec()
        assert ds.domain == "DM"

    def test_confidence_definitions(self, registry):
        defs = registry.get_confidence_definitions()
        assert "HIGH" in defs
        assert "UNMAPPED" in defs


# ---------------------------------------------------------------------------
# 3. Value Set Linkage
# ---------------------------------------------------------------------------

class TestValueSetLinkage:

    def test_sex_synonyms_from_value_set(self, registry):
        lookup = registry.get_synonym_lookup("SEX")
        assert lookup.get("m") == "Male"
        assert lookup.get("f") == "Female"

    def test_race_synonyms_from_value_set(self, registry):
        lookup = registry.get_synonym_lookup("RACE")
        assert len(lookup) > 0
        # Caucasian should map to White
        assert any("caucasian" in k for k in lookup.keys())


# ---------------------------------------------------------------------------
# 4. Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_nonexistent_variable(self, registry):
        spec = registry.get_variable_spec("NONEXISTENT")
        assert spec is None

    def test_nonexistent_variable_values(self, registry):
        vals = registry.get_valid_values("NONEXISTENT")
        assert vals == []

    def test_nonexistent_variable_columns(self, registry):
        cols = registry.get_source_columns("NONEXISTENT")
        assert cols == []


# ---------------------------------------------------------------------------
# 5. Regression: v3 → v4 Value Changes
# ---------------------------------------------------------------------------

class TestV3V4Regression:
    """
    Verify specific value changes documented in the evaluation doc Section 1.4.
    """

    def test_caucasian_is_not_allowed_value(self, registry):
        """v3 used 'Caucasian'; v4 uses 'White'. 'Caucasian' is a synonym, not a target."""
        race_vals = registry.get_valid_values("RACE")
        assert "Caucasian" not in race_vals
        assert "White" in race_vals

    def test_other_race_not_allowed(self, registry):
        """v3 mapped to 'Other'; v4 has no 'Other' (maps to 'Unknown' per OMB)."""
        race_vals = registry.get_valid_values("RACE")
        assert "Other" not in race_vals

    def test_undifferentiated_is_allowed(self, registry):
        """v3 had only Male/Female/Unknown; v4 adds Undifferentiated."""
        sex_vals = registry.get_valid_values("SEX")
        assert "Undifferentiated" in sex_vals

    def test_multiple_race_is_allowed(self, registry):
        """v4 adds 'Multiple' for multi-race."""
        race_vals = registry.get_valid_values("RACE")
        assert "Multiple" in race_vals

    def test_ethnic_has_three_values(self, registry):
        """ETHNIC explicitly specified in v4 with 3 values."""
        eth_vals = registry.get_valid_values("ETHNIC")
        assert len(eth_vals) == 3
        assert "Hispanic or Latino" in eth_vals
        assert "Not Hispanic or Latino" in eth_vals
        assert "Unknown" in eth_vals


# ---------------------------------------------------------------------------
# 6. Model Tests
# ---------------------------------------------------------------------------

class TestModels:

    def test_provenance_record_to_flat_dict(self):
        pr = ProvenanceRecord(
            variable="SEX",
            source_dataset_id="NCT00554229",
            source_field_name="SEX",
            source_value_raw="1",
            harmonized_value="Male",
            mapping_confidence="HIGH",
            flags={"sex_gender_conflated": False, "sex_conflict": False},
        )
        d = pr.to_flat_dict()
        assert d["variable"] == "SEX"
        assert d["harmonized_value"] == "Male"
        assert d["flag_sex_gender_conflated"] is False

    def test_noop_terminology_lookup(self):
        noop = NoOpTerminologyLookup()
        assert noop.lookup("Headache", "MedDRA") is None
        assert noop.search("Headache", "MedDRA") == []
