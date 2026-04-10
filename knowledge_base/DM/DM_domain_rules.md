# DM Domain Rules

**Domain:** Demographics (DM)
**Version:** 1.1
**Last Updated:** 2026-04-09
**Controlling Standard:** CDISC SDTM v3.4, DM domain

These rules apply to all variables within the Demographics domain. They inherit from and may override system-level rules (see `system_rules.md`). Individual variable specs may override domain defaults with documented justification.

---

## 1. Domain Scope and Grain

**Scope:** One record per subject per trial. The DM domain captures subject-level demographic and administrative information at a single point in time (typically screening or enrollment).

**Grain:** Subject-level. If the source data contains multiple records per subject (e.g., longitudinal visits), use the earliest record or the record marked as the baseline/screening visit. If records conflict, apply the longitudinal conflict resolution rules defined in each variable spec.

**SDTM Alignment:** The harmonized DM domain maps to CDISC SDTM DM (Demographics) as defined in the SDTM Implementation Guide. SDTM is the controlling mapping standard, including for datasets not originally in SDTM format.

## 2. Output Schema

The harmonized DM dataset contains the following 18 variables in the specified order:

| Order | Variable | Data Type | Required | Description |
|-------|----------|-----------|----------|-------------|
| 1 | TRIAL | String | Yes | Clinical trial identifier (NCT format) |
| 2 | SUBJID | String | Yes | Subject identifier within the trial |
| 3 | SEX | String (categorical) | Yes | Biological sex of the subject |
| 4 | RACE | String (categorical) | Yes | Race of the subject (OMB categories) |
| 5 | AGE | Numeric | Conditional | Age in years at reference date. Required if derivable. |
| 6 | AGEU | String (categorical) | Conditional | Age units. Required when AGE is populated. |
| 7 | AGEGP | String | Conditional | Age group category. Used only when AGE is not available. |
| 8 | ETHNIC | String (categorical) | Optional | Ethnicity (Hispanic/Latino indicator) |
| 9 | COUNTRY | String (categorical) | Optional | Country of the investigational site |
| 10 | SITEID | String | Optional | Investigational site identifier |
| 11 | STUDYID | String | Optional | Study/protocol identifier |
| 12 | USUBJID | String | Optional | Unique subject identifier (derived if not present) |
| 13 | ARMCD | String | Optional | Treatment arm code |
| 14 | ARM | String | Optional | Treatment arm description |
| 15 | BRTHDTC | Date (ISO 8601) | Optional | Date of birth |
| 16 | RFSTDTC | Date (ISO 8601) | Optional | Reference start date (first dose or enrollment) |
| 17 | RFENDTC | Date (ISO 8601) | Optional | Reference end date (last dose or study completion) |
| 18 | DOMAIN | String | Yes | Domain identifier, constant "DM" |

**Required vs. Conditional vs. Optional:**
- **Required:** Must be populated for every record. If the source value is missing, map to the variable's defined missing value (e.g., "Unknown" for SEX).
- **Conditional:** Required when the source data provides the information or it is derivable from other variables. See cross-variable dependency rules below.
- **Optional:** Populated when present in the source data. Left as the variable's missing value when not available.

## 3. Column Mapping Conventions

When mapping source columns to the output schema, apply the following priority order:

1. **Exact name match** (case-insensitive): Source column name matches the target variable name exactly (e.g., source "SEX" → target SEX).
2. **Source priority list:** Each variable spec defines a list of known source column names in priority order (e.g., for SEX: SEX, SEXCD, GENDER, SEXC, GENDERCD). Use the first match found.
3. **Label match:** If no column name matches, check column labels in the data dictionary for semantic matches (e.g., a column labeled "Sex" or "Gender" regardless of its coded name).
4. **Semantic similarity:** As a last resort, use LLM-based semantic matching. Report confidence as LOW for any mapping made via semantic similarity alone.

**Ambiguity resolution:** If multiple source columns could map to the same target variable (e.g., both SEXCD and SEX exist), prefer the decoded/labeled version over the coded version. If both contain the same information at different levels of decode, use the more decoded version and note the other in provenance.

## 4. Cross-Variable Dependencies

These rules govern relationships between variables within the DM domain. They are enforced during harmonization and validated during QC.

### 4.1 AGE / AGEGP Conditional Logic

```
IF AGE is present and numeric in source:
    → Populate AGE (convert to numeric years if needed)
    → Populate AGEU = "Years"
    → Leave AGEGP empty (or populate from source if available, for reference)

ELSE IF AGE is derivable from BRTHDTC and RFSTDTC:
    → Derive AGE = floor((RFSTDTC - BRTHDTC) / 365.25)
    → Populate AGEU = "Years"
    → Leave AGEGP empty

ELSE IF AGEGP (or AGECAT, AGEGRP) is present in source:
    → Leave AGE empty
    → Populate AGEGP with the categorical value
    → Leave AGEU empty

ELSE:
    → AGE = empty, AGEGP = empty, AGEU = empty
    → Flag: MISSING_AGE_AND_AGEGP in QC report
```

**Rationale:** AGE as a continuous numeric variable is always preferred over categorical AGEGP because it enables more flexible downstream analysis. AGEGP is a fallback for de-identified datasets where continuous age was removed.

### 4.2 RACE / ETHNICITY Independence

RACE and ETHNICITY are independent variables per OMB standards. Any combination is valid (e.g., RACE = "White", ETHNIC = "Hispanic or Latino"). When a source system combines race and ethnicity into a single field, the variable specs for RACE and ETHNICITY define the separation logic.

**Validation:** After harmonization, verify that ETHNIC = "Hispanic or Latino" appears across multiple RACE categories, not exclusively with RACE = "Unknown." If ETHNIC = "Hispanic or Latino" co-occurs with RACE = "Unknown" in more than 80% of cases, flag as a potential separation failure.

### 4.3 USUBJID Derivation

```
IF USUBJID is present in source:
    → Copy directly (normalize whitespace)

ELSE IF both STUDYID and SUBJID are populated:
    → Derive USUBJID = STUDYID + "-" + SUBJID

ELSE:
    → Leave USUBJID empty
    → Flag: MISSING_USUBJID in QC report (informational, not critical)
```

### 4.4 Date Ordering

When both RFSTDTC and RFENDTC are populated:
- RFENDTC must be on or after RFSTDTC
- If RFENDTC < RFSTDTC, flag as DATE_ORDER_INVALID in QC report
- Do not auto-correct. Preserve the source values and let downstream review resolve.

### 4.5 ARM / ARMCD Consistency

ARM and ARMCD form a 1:1 pair. When both are populated in a harmonized dataset, enforce the following:

1. **Bijectivity:** Each unique ARMCD must map to exactly one ARM, and vice versa. If a single ARMCD resolves to multiple ARM descriptions (or the reverse), flag as `ARM_ARMCD_INCONSISTENT` in the QC report.
2. **Co-population:** If ARMCD is populated, ARM should also be populated (decode from data dictionary if necessary). If ARM is populated but no ARMCD source exists, ARMCD is left empty — do not invent codes.
3. **Validation timing:** This check runs after all per-variable mapping is complete, as a domain-level QC step. It is not enforced during initial column mapping.

### 4.6 SEX / Clinical Plausibility

If the dataset also contains pregnancy-related flags (may be in a separate domain):
- PREGNANCY_STATUS = positive and SEX = "Male" → flag as DATA_QUALITY_ISSUE
- This is a cross-domain check and may not be applicable within the DM domain alone. Note for future multi-domain QC.

## 5. Domain-Level QC Checks

These checks apply to the DM domain as a whole, beyond the variable-specific validation defined in each variable spec.

### 5.1 Duplicate Subject Detection

**(TRIAL, SUBJID) must be unique.** If duplicate combinations exist after harmonization:
- Flag as DUPLICATE_SUBJECT
- If 100% of rows are duplicates → additional flag SUBJID_MAPPING_SUSPECT (likely indicates the wrong source column was mapped to SUBJID)

### 5.2 Required Variable Completeness

Check that all Required variables (TRIAL, SUBJID, SEX, RACE, DOMAIN) have non-missing values for every record. Missing values in these fields (mapped to "Unknown" or equivalent) are valid but should be counted and reported.

### 5.3 Coded Value Without Dictionary

If a variable contains numeric codes and no data dictionary was provided or the dictionary doesn't cover that variable:
- Flag as CODED_VALUE_NO_DICTIONARY
- Attempt LLM-based decoding with confidence = LOW
- Report all unresolved codes in the transformation report

### 5.4 Row Count Sanity

Compare the row count of the harmonized output to the source input:
- If harmonized rows > source rows → possible duplication introduced during processing
- If harmonized rows < source rows → possible data loss during processing
- Either case: flag for review. 1:1 row count is expected for subject-level DM data.

### 5.5 Stoplight Assessment

The overall quality of a harmonized DM dataset is assessed using a stoplight system:

| Grade | Criteria |
|-------|----------|
| **GREEN** | All 5 core variables present with substantive values (SEX, RACE, ETHNIC, AGE or AGEGP, COUNTRY) AND no critical QC issues |
| **YELLOW** | Missing ≤ 2 core variables OR formatting/plausibility issues detected |
| **RED** | Missing ≥ 3 core variables OR critical QC issues (duplicate subjects, SUBJID mapping suspect) |

"Present with substantive values" means the variable is populated with values other than "Unknown" for at least 50% of records. A variable that is technically populated but 95% "Unknown" should not count as substantively present.

## 6. Treatment Arm Conventions

When source data contains treatment arm information:

- **ARM** (description) is preferred over **ARMCD** (code) for the human-readable representation
- If only a coded treatment variable exists (e.g., TRTCD, TRTNUM), map to ARMCD and attempt to populate ARM from the data dictionary decode
- If only a description exists (e.g., TRT, TRTLONG), map to ARM and leave ARMCD empty unless a code can be derived
- Normalize ARM text: apply mixed case, expand common abbreviations (e.g., "PBO" → "Placebo"), remove trailing dosage-only text if a separate dose variable exists
- When multiple treatment-related columns exist (e.g., assigned treatment vs. actual treatment), prefer the randomized/assigned treatment for the DM record. Document the choice in provenance.

## 7. System Rule Overrides

The following system-level defaults are overridden at the DM domain level:

| System Rule | DM Override | Justification |
|-------------|------------|---------------|
| *None currently* | — | DM domain follows all system defaults in v1.0 |

This section is reserved for future domain-specific overrides as needs arise.
