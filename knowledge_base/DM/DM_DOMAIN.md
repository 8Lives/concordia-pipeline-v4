# DM Variable Specification: DOMAIN

**Variable:** DOMAIN
**Domain:** Demographics (DM)
**Order:** 18
**Required:** Yes
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The domain code identifying the type of observation data. For all Demographics domain records, DOMAIN must be set to the constant value "DM". This variable is a structural requirement in CDISC SDTM datasets to enable parsing and routing of observations to domain-specific validation and analysis workflows.

**SDTM Reference:** DM.DOMAIN — Required constant "DM" for all Demographics domain records

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DOMAIN variable | M (Mandatory) constant for each domain; "DM" for Demographics |
| FDA Submission Standards | Domain Designation | Required for eCTD organization (Module 5.3.5) |

**Note:** DOMAIN is a pure structural/metadata variable with no semantic content from the source data. It is always derived as a constant.

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | Notes |
|-------|-----------|-------|
| "DM" | Demographics domain constant | Only valid value; applied to all records in the DM domain |
| Unknown | Should NOT occur in properly harmonized data | confidence = UNMAPPED indicates a pipeline error, not acceptable for DM |

**Source Priority List:** DOMAIN (if present), otherwise derived as constant

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Notes |
|---------|--------------|-------------|-------|
| AZ_205 | (not present) | — | No DOMAIN column; must derive as constant "DM" |
| AZ_229 | (not present) | — | No DOMAIN column; must derive as constant "DM" |
| Amgen_265 | (not present) | — | No DOMAIN column; must derive as constant "DM" |
| EMD_221 | DOMAIN | "DM" (273 records) | Explicit DOMAIN column present; all values "DM" |
| Lilly_568 | DOMAIN | "DM" (130 records) | Explicit DOMAIN column present; all values "DM" |
| Merck_188 | DOMAIN | "DM" (507 records) | Explicit DOMAIN column present; all values "DM" |
| Pfizer_374 | (not available) | — | No DOMAIN column in sparse extract |
| Sanofi_323 | (not available) | — | No DOMAIN column in sparse extract |

---

## 3. Mapping Decision Principles

1. **Always use the constant value "DM" for DM domain records.** No variation, no missing values, no alternative spellings (e.g., "Demographics", "DEM").

2. **If source provides DOMAIN, validate that it equals "DM".** If source has DOMAIN = "DM", use it (confidence = HIGH). If source has DOMAIN ≠ "DM" (data error), flag and override with "DM".

3. **If source lacks DOMAIN, derive as constant "DM".** All five sponsors without an explicit DOMAIN column must derive this value. This is the expected path.

4. **Do not attempt to infer domain from other variables.** If a record is in the DM extract, it must have DOMAIN = "DM" regardless of what other variables are present.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| Explicit DOMAIN = "DM" | DM | HIGH | Use source value as-is |
| Explicit DOMAIN ≠ "DM" | DM | LOW | Data quality issue; override and flag |
| No DOMAIN column | DM | HIGH | Derive as constant |
| NULL, "", "N/A" | DM | HIGH | Derive as constant; missing DOMAIN is not an error |

---

## 4. Variable-Specific Business Rules

### 4.1 Constant Derivation

For all DM domain records where DOMAIN is not explicitly provided:

```
DOMAIN := "DM"
```

This is applied unconditionally to every record in the DM extract.

### 4.2 Case Sensitivity

The value must be exactly "DM" (uppercase). Do not accept:
- "dm" (lowercase)
- "Dm", "dM" (mixed case)
- "Demographics" (spelled out)
- "D M" (with spaces)

### 4.3 Pipeline Bug: v3 DOMAIN = None

**Known Issue:** Version 3 of the harmonization pipeline has a documented bug where DOMAIN values show "None" instead of "DM" in output.

- **Root Cause:** Pipeline-level derivation issue (not a specification problem)
- **Impact:** All records show DOMAIN = "None" or missing in v3 output
- **Resolution:** This is a pipeline bug to be fixed in v4; do not reflect this in the variable spec
- **Validation:** QC should detect "None" values and flag as pipeline error, not data quality error

---

## 5. Provenance Flags

In addition to the standard provenance fields defined in system_rules.md:

| Field | Type | Description |
|-------|------|-------------|
| `domain_source` | String | Source of DOMAIN: "explicit" (from source column), "derived" (constant), or "pipeline_bug" (v3 issue) |
| `domain_override` | Boolean | True if source DOMAIN ≠ "DM" and was overridden to "DM" |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All DM domain records must have DOMAIN = "DM" (exactly)
- No NULL, blank, or "None" values are acceptable
- 100% of records must conform

### Plausibility
- No variation expected; all records in DM domain must have the same DOMAIN value
- If any record has DOMAIN ≠ "DM", this indicates:
  - Data corruption (data quality error)
  - Pipeline bug (v3 known issue)
  - Cross-domain merge error (data from multiple domains in same extract)

### Determinism
- Repeated extraction must yield DOMAIN = "DM" for all records
- No conditional logic applies; no exceptions exist

---

## 7. Known Limitations

1. **v3 pipeline bug: DOMAIN = "None".** The version 3 harmonization pipeline has a known defect where DOMAIN values are rendered as "None" or missing in the output. This is a pipeline implementation issue, not a spec problem. Expected fix in v4 release. *(SME review required)*
2. **Trivial variable.** DOMAIN is a structural constant with no semantic variance. It serves only to route records to domain-specific workflows in CDISC tools and does not carry information about the subject or the trial.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (standalone format) |
| 2.0 | 2026-04-08 | Revised for three-tier hierarchy; documented v3 pipeline bug (DOMAIN = "None"); clarified constant derivation rule; noted 3 sponsors with explicit DOMAIN and 5 sponsors requiring derivation; marked SME review for v3 bug resolution |
