# DM Variable Specification: AGE

**Variable:** AGE
**Domain:** Demographics (DM)
**Order:** 5
**Required:** Conditional (required if present or derivable; see DM_domain_rules.md Section 4.1)
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The age of the subject in years at the reference date (typically screening, enrollment, or first dose date). This is a continuous numeric variable representing the most granular age information available.

**SDTM Reference:** DM.AGE — Numeric, age in units specified by AGEU

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.AGE | Numeric (integer or decimal) |
| CDISC SDTM | DM.AGEU | Age units (Years, Months, Days) |
| HL7 FHIR | Patient.birthDate (age derived) | Calculated from birth date |

**Relationship to AGEGP:** AGE is always preferred over AGEGP. If AGE is present or derivable, populate AGE and leave AGEGP empty. AGEGP is used only when continuous age is not available. See DM_domain_rules.md Section 4.1 for the conditional logic.

---

## 2. Allowed Values *(SME review required for plausibility range)*

| Property | Value |
|----------|-------|
| Data type | Numeric (integer preferred, decimal acceptable) |
| Units | Years (see AGEU spec) |
| Plausible range | 0–120 |
| Missing value | Empty (not "0", not "Unknown" — AGE is numeric; absence is represented by an empty cell, and AGEGP may be populated instead) |

**Note on missing value convention:** Unlike categorical variables which use "Unknown" for missing values, AGE uses an empty cell because a numeric "Unknown" sentinel (e.g., 999) would corrupt statistical calculations. The QC system checks whether at least one of AGE or AGEGP is populated per the cross-variable rule.

**Source Priority List:** AGE, APTS_AGE, AGE_YRS, AGEY, AGE_AT_ENROLLMENT

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Type | Values Found | Notes |
|---------|-------------|------|-------------|-------|
| AZ_205 | *(not present)* | — | — | Only categorical agegrp available |
| AZ_229 | *(unclear)* | — | — | AGEGRP and AGEGP present; no continuous AGE column |
| Amgen_265 | AGE | float64 | Range: 23–84, mean ~57, n=520 | Stored as float (e.g., "59.0") |
| EMD_221 | AGE | TBD | TBD | Expected numeric |
| Lilly_568 | AGE | TBD | TBD | Expected numeric |
| Merck_188 | AGE | TBD | TBD | Expected numeric |
| Pfizer_374 | AGE | float64 | Range: 31–88, mean ~62, n=542 | Only DM variable in this extract |
| Sanofi_323 | *(unclear)* | — | — | Not confirmed in data extraction |

---

## 3. Mapping Decision Principles

1. **Numeric conversion first.** If AGE is stored as character type (e.g., "59" as string), convert to numeric. If conversion fails (non-numeric characters like "59y" or "fifty-nine"), attempt to extract the numeric portion. If extraction fails, treat as missing.

2. **Float-to-integer.** If AGE is stored as float (e.g., 59.0), and all values are whole numbers, convert to integer. If fractional values exist (e.g., 0.5 for a 6-month-old infant), preserve the decimal.

3. **Unit conversion.** If the source AGE is in months (check AGEU or column label), convert to years by dividing by 12. If in days, divide by 365.25. Always document the conversion in provenance.

4. **Derivation from dates.** If AGE is not present but BRTHDTC and RFSTDTC are both available:
   - AGE = floor((RFSTDTC - BRTHDTC) / 365.25)
   - Report confidence as MEDIUM (derived, not directly observed)
   - Document derivation in provenance: "Derived from BRTHDTC and RFSTDTC"

5. **Partial birth dates.** If only birth year is available (e.g., "1955"), and RFSTDTC includes a full date, approximate AGE using July 1 of the birth year as a midpoint estimate. Report confidence as LOW.

6. **Do not derive from AGEGP.** If only categorical age groups are available (e.g., "65-69"), do NOT convert to a numeric AGE (e.g., midpoint). Leave AGE empty and populate AGEGP instead. The categorical information should be preserved as-is.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| 59 (numeric) | 59 | HIGH | Direct copy |
| "59" (character) | 59 | HIGH | Type conversion |
| 59.0 (float, whole number) | 59 | HIGH | Float-to-integer |
| 0.5 (float, infant) | 0.5 | HIGH | Preserve decimal |
| 720 (months, from AGEU context) | 60 | MEDIUM | Unit conversion |
| Derived: BRTHDTC=1960-03-15, RFSTDTC=2019-07-20 | 59 | MEDIUM | Date derivation |
| -1, 999, 9999 | *(empty)* | UNMAPPED | Sentinel values for missing |
| "65-69" (categorical) | *(empty — use AGEGP)* | — | Do not convert |

---

## 4. Variable-Specific Business Rules

### 4.1 Plausibility Checks

- AGE < 0: Flag as implausible. Likely a data error or sentinel value. Set to empty.
- AGE > 120: Flag as implausible. Set to empty.
- AGE = 0 with no infant context: Verify. Could be a valid neonate or a missing-value sentinel.

### 4.2 Consistency with Birth Date

If both AGE and BRTHDTC/RFSTDTC are present, validate:
- Derived age from dates should be within ±1 year of the reported AGE (accounting for partial dates and rounding)
- If discrepancy > 2 years, flag as AGE_DATE_INCONSISTENT

### 4.3 De-identified Age Data

Some datasets remove continuous age for de-identification, replacing it with categorical bands:
- AZ_205: Only `agegrp` available (5-year bands: "45-49", "50-54", ..., ">=90")
- AZ_229: `AGEGP` (categorical: ">=45<60", ">=60<65", ..., ">=80<100") and `AGEGRP` ("18-64 Years", "65-74 Years", ">=75 Years")

In these cases, AGE remains empty and AGEGP is populated. This is expected behavior, not a data quality issue.

---

## 5. Provenance Flags

In addition to the standard provenance fields:

| Field | Type | Description |
|-------|------|-------------|
| `age_derived` | Boolean | True if AGE was derived from BRTHDTC and RFSTDTC rather than directly from source |
| `age_unit_converted` | Boolean | True if the source age was in a different unit (months, days) and was converted to years |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- AGE must be numeric when present (not a string, not a category)
- AGE must be in range 0–120 (configurable per study population)

### Plausibility
- Mean AGE should be plausible for the study indication (e.g., oncology trials typically 50–70; pediatric trials < 18)
- Standard deviation should be reasonable (> 0 and < 30 for most adult populations)
- No negative values

### Completeness (in conjunction with AGEGP)
- At least one of AGE or AGEGP should be populated for each record
- If both are empty, flag MISSING_AGE_AND_AGEGP per DM_domain_rules.md Section 4.1

---

## 7. Known Limitations

1. **AZ_205 and AZ_229 have no continuous AGE.** Only categorical age groups are available due to de-identification. AGE will be empty for all records in these datasets.
2. **Partial birth dates limit derivation accuracy.** When only birth year is available, derived AGE has ±0.5 year uncertainty.
3. **Age at screening vs. age at randomization vs. age at first dose** may differ by weeks or months. The source may not specify which reference point was used. This ambiguity is inherent in the data and documented in provenance when detectable.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial draft in three-tier format |
