> **DEPRECATED:** This file has been renamed to `DM_ETHNIC.md` to align with the ETHNIC variable name in the output schema. Use `DM_ETHNIC.md` as the authoritative spec.

# DM Variable Specification: ETHNICITY

**Variable:** ETHNIC
**Domain:** Demographics (DM)
**Order:** 8
**Required:** Optional
**Version:** 2.1
**Last Updated:** 2026-04-09
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** Whether the subject identifies as Hispanic or Latino, independent of race. Per OMB standards, ethnicity is a binary classification separate from race, though some sources capture sub-categories (e.g., Mexican, Puerto Rican, Cuban).

**SDTM Reference:** DM.ETHNIC — CDISC Controlled Terminology codelist C66790

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.ETHNIC | C66790 |
| OMB (1997 Revised) | 2 ethnicity categories | Hispanic/Latino or Not |
| HL7 FHIR | us-core-ethnicity extension | OMB + detailed |
| OMOP CDM | ethnicity_concept_id (Person table) | 38003563 (H), 38003564 (NH) |

**Relationship to RACE:** Ethnicity is independent of race. A subject may be any race AND Hispanic or Latino, or any race AND Not Hispanic or Latino. See DM_domain_rules.md Section 4.2 and the RACE spec Section 3.2 for separation logic when source data combines these.

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | CDISC CT Code |
|-------|-----------|---------------|
| Hispanic or Latino | Subject identifies as Hispanic or Latino | C17459 |
| Not Hispanic or Latino | Subject does not identify as Hispanic or Latino | C41222 |
| Unknown | Missing, refused, not collected, or not interpretable | C17998 |

**Source Priority List:** ETHNIC, ETHGRP, ETHNICITY, ETHNIC_GROUP, ETHNICCD

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Dictionary Decode |
|---------|--------------|-------------|-------------------|
| AZ_205 | *(not present)* | — | No ethnicity variable |
| AZ_229 | ETHGRP | "98" (n=153), "10" (n=39), "9" (n=36), "8" (n=24), "1" (n=14) | 12-category system including de-identified codes. 1=White, 8=Hispanic/Latin American, 9=East Asian, 10=SE Asian, 98=Other/de-identified |
| Amgen_265 | *(not present)* | — | No ethnicity variable |
| EMD_221 | ETHNIC | Numeric codes | Format-dependent |
| Merck_188 | ETHNIC | Numeric codes | Format-dependent |
| Sanofi_323 | *(not present)* | — | No ethnicity variable |

**AZ_229 ETHGRP Note:** This field is labeled "Ethnic group" but uses a 12-category classification that conflates race and ethnicity (it includes "White," "East Asian," "SE Asian" alongside "Hispanic/Latin American"). This is NOT an OMB-aligned ethnicity field. During harmonization:
- Code 8 ("Hispanic/Latin American") → ETHNIC = "Hispanic or Latino"
- All other codes → ETHNIC = "Unknown" (the other codes are race categories, not ethnicity)
- Set `race_ethnicity_conflated = true`
- The race-like codes should also inform the RACE variable mapping where applicable

---

## 3. Mapping Decision Principles

1. **Ethnicity is binary per OMB.** Regardless of how many categories the source uses, the target has three values: Hispanic or Latino, Not Hispanic or Latino, or Unknown.

2. **Extract from combined fields.** When race and ethnicity are combined in a single source field, extract ethnicity values before mapping race. See the RACE spec Section 3.2 for the separation decision tree.

3. **Sub-categories roll up.** Source values like "Mexican," "Puerto Rican," "Cuban," "Central American," "South American" all map to "Hispanic or Latino." Preserve the sub-category in `source_value_raw`.

4. **Absence is not "Not Hispanic."** If the source has no ethnicity field at all, map all records to Unknown. Do not default to "Not Hispanic or Latino."

5. **"Non-Hispanic" requires explicit evidence.** Only map to "Not Hispanic or Latino" when the source explicitly records this (e.g., a checkbox, a coded value). Absence of a "Hispanic" indicator in a combined field is Unknown, not "Not Hispanic."

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "Hispanic or Latino", "Hispanic", "Latino/Latina" | Hispanic or Latino | HIGH | Direct match |
| "Not Hispanic or Latino", "Non-Hispanic" | Not Hispanic or Latino | HIGH | Direct match |
| "Mexican", "Puerto Rican", "Cuban" | Hispanic or Latino | HIGH | Sub-category roll-up |
| 1 (dictionary: 1=Hispanic) | Hispanic or Latino | HIGH | Code decode |
| 2 (dictionary: 2=Not Hispanic) | Not Hispanic or Latino | HIGH | Code decode |
| "Prefer not to say", "Declined" | Unknown | HIGH | Explicit non-disclosure |
| Code 98 (AZ_229: Other/de-identified) | Unknown | HIGH | De-identification |
| *(field absent from source)* | Unknown | UNMAPPED | No source data |
| NULL, "", "N/A" | Unknown | HIGH | Standard missing |

---

## 4. Variable-Specific Business Rules

### 4.1 Longitudinal Conflict Resolution

1. If one value is Unknown and the other is substantive, prefer the substantive value.
2. If one record says Hispanic or Latino and another says Not Hispanic or Latino, flag for review. Prefer "Hispanic or Latino" as the more informative assertion unless the later record explicitly indicates a correction.

### 4.2 ETHGRP-style Fields (Multi-Category Ethnic Group)

Some datasets (notably AZ_229) use an "ethnic group" field with many categories that conflate race and ethnicity. For these fields:
- Extract the Hispanic/Latino category to ETHNICITY
- Extract race-like categories to inform RACE mapping
- Set `race_ethnicity_conflated = true` for all records from this source
- Map all non-Hispanic categories in the ethnicity field to Unknown for ETHNICITY (they are race data, not ethnicity data)

---

## 5. Provenance Flags

In addition to the standard provenance fields:

| Field | Type | Description |
|-------|------|-------------|
| `race_ethnicity_conflated` | Boolean | True if the source combined race and ethnicity (shared with RACE variable) |
| `ethnicity_conflict` | Boolean | True if longitudinal records had conflicting values |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All values must be in: {Hispanic or Latino, Not Hispanic or Latino, Unknown}

### Plausibility (US population benchmarks — adjust for study population)

| Category | Typical Range | Investigation Trigger |
|----------|--------------|----------------------|
| Hispanic or Latino | 10–25% (US general) | < 2% or > 40% |
| Not Hispanic or Latino | 60–85% | < 40% |
| Unknown | 0–10% (trial), 0–30% (RWD) | Above thresholds |

### Cross-Variable Check
- See DM_domain_rules.md Section 4.2 for the RACE/ETHNICITY independence validation

### Determinism
- Within a single source dataset, the same source value must always map to the same target value.

---

## 7. Known Limitations

1. **Three of 8 prototype sponsors have no ethnicity variable.** AZ_205, Amgen_265, and Sanofi_323 will produce Unknown for all records.
2. **AZ_229 ETHGRP conflates race and ethnicity** in a 12-category system with de-identification. Only code 8 maps to the Hispanic or Latino target value; codes 1, 9, 10 are race data that cannot be used for ethnicity.
3. **International trials may not capture ethnicity.** The Hispanic/Latino distinction is a US/OMB construct. Trials conducted entirely outside the Americas may have no ethnicity data, and Unknown is the expected value.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (combined with RACE, standalone format) |
| 2.0 | 2026-04-08 | Split from RACE; revised for three-tier hierarchy; added prototype data observations; added ETHGRP handling logic |
| 2.1 | 2026-04-09 | Renamed from DM_ETHNICITY.md to DM_ETHNIC.md to match variable name ETHNIC in output schema. Value set file similarly renamed to ethnic_values.md. |
