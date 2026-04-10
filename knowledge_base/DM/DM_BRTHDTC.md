# DM Variable Specification: BRTHDTC

**Variable:** BRTHDTC
**Domain:** Demographics (DM)
**Order:** 15
**Required:** Optional
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The date of birth of the subject in ISO 8601 format (YYYY-MM-DD). This is the subject's full date of birth if available, or a partial date (YYYY-MM or YYYY) if precision is limited due to data source constraints or de-identification practices.

**SDTM Reference:** DM.BRTHDTC — CDISC SDTM DM domain, ISO 8601 format

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| ISO 8601 | Date format | YYYY-MM-DD (full) or YYYY-MM or YYYY (partial) |
| CDISC SDTM | DM.BRTHDTC | Date of birth |
| HL7 FHIR | Patient.birthDate | Date of birth |

---

## 2. Allowed Values

BRTHDTC accepts ISO 8601 date strings with varying precision levels:

| Format | Example | Notes |
|--------|---------|-------|
| Full date | 1955-03-15 | Year, month, and day |
| Year-month only | 1955-03 | Year and month; day unknown or de-identified |
| Year only | 1955 | Year only; month and day removed for de-identification |
| Unknown | (empty, NULL) | Source value missing or unable to determine |

**Source Priority List:** BRTHDTC, BIRTHDT, DOB, DATEOFBIRTH, BIRTHDAY, BIRTH_DATE

**Observed Source Patterns (from data extraction):**

| Sponsor | Source Column | Values Found | Format | Precision | Notes |
|---------|---|---|---|---|---|
| EMD_221 | BRTHDTC | Range 1940-1963 (47 unique years) | YYYY | Year-only | De-identified for privacy; 100% year precision |
| Lilly_568 | BRTHDTC | All blank (130 records) | — | Missing | No birth date information provided |
| Merck_188 | BRTHDTC | Range 1941-1962 (47 unique years) | YYYY | Year-only | De-identified for privacy; 100% year precision |
| AZ_205, AZ_229, Amgen_265, Pfizer_374, Sanofi_323 | — | *(not present)* | — | — | No BRTHDTC in extracted datasets |

---

## 3. Mapping Decision Principles

1. **Preserve source date precision.** Do not infer or fabricate missing components (month, day) if not present in the source. Store partial dates in the precision provided (YYYY-MM-DD, YYYY-MM, or YYYY).

2. **Convert SAS numeric dates to ISO 8601.** If the source is a SAS numeric date (days since 1960-01-01), convert using the formula:
   - ISO 8601 date = 1960-01-01 + (SAS_numeric_value days)
   - Per system_rules.md Section 5

3. **Validate date plausibility.** If the subject is enrolled in an adult clinical trial and BRTHDTC suggests an age > 120 years (or < 18 years for adult studies), flag for manual review but preserve the source value.

4. **Assign confidence based on precision.**
   - HIGH: Full date (YYYY-MM-DD) with validation
   - MEDIUM: Partial date (YYYY-MM) or year-only, known de-identification
   - LOW: Year-only from data extraction with no documentation of de-identification practice

5. **Mark de-identified dates explicitly.** If month/day are missing due to de-identification, set provenance.de_identified = true

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "1955-03-15", "15MAR1955" | 1955-03-15 | HIGH | Full date; case/format normalized |
| "1955-03", "MAR1955" | 1955-03 | MEDIUM | Partial; day removed or unknown |
| "1955", 1955 | 1955 | MEDIUM | Year-only; likely de-identified |
| 21549 (SAS numeric, 1959) | 1959-01-01 | MEDIUM | SAS date converted; approximated to 1960-01-01 anchor |
| NULL, "", "N/A", "." | (empty) | HIGH | Missing, not recorded |

---

## 4. Variable-Specific Business Rules

### 4.1 De-Identification and Partial Dates

Clinical trial data is frequently de-identified to remove specific birth dates and replace with year-only values. This is expected and valid:
- Year-only BRTHDTC (YYYY format) is not a data quality issue
- Do not flag year-only dates as incomplete; they are intentionally de-identified
- Set provenance.de_identified = true for all year-only dates
- Do not attempt to infer or impute missing month/day

### 4.2 SAS Numeric Date Conversion

If source data contains numeric dates (common in SAS-based trial systems):
- Use the system_rules.md formula: ISO date = 1960-01-01 + (SAS_numeric value days)
- Document the conversion in provenance.date_source_format = "SAS_numeric"
- For example: SAS 21549 = 1959-01-01 (assuming conversion from days since 1960-01-01)
- *(SME review required)* - Verify the epoch (1960-01-01 is standard but not universal)

### 4.3 Cross-Variable: AGE Derivation

Per DM_domain_rules.md Section 4.1, if AGE is not available in the source but both BRTHDTC and RFSTDTC are present:
- Derive AGE = floor((RFSTDTC - BRTHDTC) / 365.25)
- Set provenance.age_derived_from_brthdtc = true
- This is a critical dependency; document in the harmonization report

### 4.4 Plausibility Checks for Age-at-Enrollment

If both BRTHDTC and RFSTDTC (study start date) are available:
- Calculate implied age at RFSTDTC: (RFSTDTC - BRTHDTC) / 365.25
- If implied age < 18 in an adult trial, flag age-plausibility-mismatch for SME review
- If implied age > 120, flag as biologically implausible but preserve the value
- Do not auto-correct; preserve source data

### 4.5 Handling Censored or Invalid Dates

The data extraction identified censored dates (represented as asterisks, e.g., "\\*\\*\\*\\*\\*\\*") in RFSTDTC/RFENDTC but not in BRTHDTC. However:
- If BRTHDTC contains censored placeholders, replace with NULL and set confidence = UNMAPPED
- If BRTHDTC contains an obviously invalid date (e.g., year 2288), flag for manual review and do not map

### 4.6 Consistency with AGE

If both AGE and BRTHDTC are present in the source:
- Calculate the implied age from BRTHDTC and RFSTDTC
- Compare to the provided AGE value
- If difference > 1 year, flag age-brthdtc-mismatch for review
- This does not cause correction; it flags potential data quality issues

---

## 5. Provenance Flags

In addition to standard provenance fields (system_rules.md):

| Field | Type | Description |
|-------|------|-------------|
| `brthdtc_source_column` | String | Name of the source column from which BRTHDTC was mapped |
| `brthdtc_precision` | String | "YYYY-MM-DD" (full), "YYYY-MM" (partial), or "YYYY" (year-only) |
| `brthdtc_de_identified` | Boolean | True if month/day are missing due to de-identification |
| `brthdtc_date_source_format` | String | "ISO_8601", "SAS_numeric", "DDMONYYYY", etc. |
| `brthdtc_sas_epoch_confirmed` | Boolean | True if SAS numeric epoch (1960-01-01) was confirmed with SME |
| `brthdtc_age_derived` | Boolean | True if AGE was derived from BRTHDTC + RFSTDTC |
| `brthdtc_age_plausibility` | String | "OK", "flag_age_mismatch" (if AGE value conflicts), "flag_implausible_age" (if derived age > 120) |

---

## 6. Validation Criteria *(SME review required for SAS epoch confirmation)*

### Conformance
- BRTHDTC must be in ISO 8601 format: YYYY-MM-DD, YYYY-MM, or YYYY
- All dates must have valid year/month/day components (e.g., no month > 12, no day > 31)
- No leading/trailing whitespace

### Plausibility
- **Age range:** For adult trials (18+), derived age should be 18-120. Flag outliers but preserve values
- **De-identified dates:** Year-only BRTHDTC (YYYY) is expected and valid in most trial data
- **Consistency:** If both AGE and BRTHDTC are present, derived age should agree with AGE to within 1 year
- **Temporal ordering:** BRTHDTC should be before RFSTDTC (enrollment date) for all records

### Determinism
- Within a single source dataset, the same source value must always map to the same target BRTHDTC

---

## 7. Known Limitations

1. **Year-only dates dominate the available data.** EMD_221 and Merck_188 provide only birth year. While this is valid de-identification, it limits the precision of age calculations and downstream analyses.

2. **Lilly_568 has 100% missing BRTHDTC.** These records will have BRTHDTC empty and cannot use birth-date-based age derivation.

3. **SAS numeric date conversion requires epoch confirmation.** The standard epoch is 1960-01-01, but some legacy systems use different epochs. SME review is needed for each dataset to confirm the correct epoch.

4. **No full-date (YYYY-MM-DD) BRTHDTC observed in prototype data.** All populated BRTHDTC values are year-only, so high-precision validation cannot be performed until more complete datasets are available.

5. **Cross-validation with AGE is limited.** Most datasets with BRTHDTC lack numeric AGE values. This validation rule cannot be applied to EMD_221 or Merck_188 without access to their AGE variable.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial spec; documented de-identification practices, SAS conversion, and AGE derivation rules |
