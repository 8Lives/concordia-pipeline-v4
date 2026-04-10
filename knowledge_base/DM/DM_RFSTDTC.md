# DM Variable Specification: RFSTDTC

**Variable:** RFSTDTC
**Domain:** Demographics (DM)
**Order:** 16
**Required:** Optional
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The reference start date of the subject's participation in the trial. This date represents the earliest of: first treatment/study drug administration date, randomization date, enrollment date, or screening start date, depending on trial design. RFSTDTC is captured in ISO 8601 format and is typically the anchor point for time-to-event analyses and visit scheduling.

**SDTM Reference:** DM.RFSTDTC — CDISC SDTM DM domain, ISO 8601 format with optional time

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| ISO 8601 | Date/time format | YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS |
| CDISC SDTM | DM.RFSTDTC | Reference start date/time |
| Clinical Trial Design | Baseline date | Enrollment, randomization, or first dose |

---

## 2. Allowed Values

RFSTDTC accepts ISO 8601 date and date/time strings:

| Format | Example | Notes |
|--------|---------|-------|
| Full date/time | 2009-07-18T14:40:00 | Year, month, day, hour, minute, second |
| Date/time (minutes) | 2009-07-18T14:40 | Year, month, day, hour, minute |
| Date only | 2009-07-18 | Year, month, and day |
| Censored | \*\*\*\*\*\* (variable length) | De-identified dates; treat as NULL |
| Unknown | (empty, NULL) | Source value missing or unable to determine |

**Source Priority List:** RFSTDTC, RFSTDT, STARTDT, FIRSTDOSEDT, RANDOMDT, ENROLLDT, SCRDT

**Observed Source Patterns (from data extraction):**

| Sponsor | Source Column | Format | Censoring | Range | Notes |
|---------|---|---|---|---|---|
| EMD_221 | RFSTDTC | YYYY-MM-DDTHH:MM | 50.0% censored (represented as "\*\*\*\*\*\*") | 2009-2015 | Half the data redacted for privacy |
| Merck_188 | RFSTDTC | YYYY-MM-DDTHH:MM | 44.4% censored | 2009-2015 | Partial censoring; identifiable dates remain |
| Lilly_568 | RFSTDTC | YYYY-MM-DD | 62.5%-70.2% blank | 2288-2289 (data quality concern) | Mostly missing; invalid year range when present |
| AZ_205, AZ_229, Amgen_265, Pfizer_374, Sanofi_323 | — | — | — | — | Not available in extracted data |

---

## 3. Mapping Decision Principles

1. **Preserve source date/time precision.** If the source provides date and time, map both. If only date is provided, map date only. Do not add time components that are not in the source.

2. **Convert SAS numeric dates to ISO 8601.** If the source is a SAS numeric date (days since 1960-01-01), convert using the formula:
   - ISO 8601 date = 1960-01-01 + (SAS_numeric_value days)
   - Per system_rules.md Section 5

3. **Handle censored dates:** If a date is censored (indicated by asterisks or other redaction markers):
   - Replace the entire value with NULL
   - Set confidence = UNMAPPED
   - Mark provenance.rfstdtc_censored = true
   - Do not attempt to reconstruct or infer the date

4. **Validate plausibility:** Cross-check against RFENDTC and other temporal landmarks:
   - RFSTDTC should be <= RFENDTC (per DM_domain_rules.md Section 4.4)
   - RFSTDTC should be after BRTHDTC (if both present)
   - RFSTDTC should be in a reasonable range for the trial (typically 2000-2025 for recent trials)

5. **Assign confidence based on data completeness.**
   - HIGH: Full date with time (YYYY-MM-DDTHH:MM), not censored
   - MEDIUM: Date-only (YYYY-MM-DD), not censored
   - LOW: Partial date (YYYY-MM or YYYY), or required time component missing
   - UNMAPPED: Censored or unable to determine

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "2009-07-18T14:40" | 2009-07-18T14:40 | HIGH | Full datetime; case/format normalized |
| "2009-07-18" | 2009-07-18 | MEDIUM | Date-only; time not provided in source |
| "18JUL2009" | 2009-07-18 | MEDIUM | Date parsed and converted to ISO 8601 |
| "\*\*\*\*\*\*" (censored) | (empty) | UNMAPPED | Redacted for privacy; cannot map |
| "2288-01-01" (invalid year) | — | — | Data quality issue; flag and leave empty |
| NULL, "", "N/A" | (empty) | HIGH | Legitimately missing |

---

## 4. Variable-Specific Business Rules

### 4.1 Reference Date Definition

RFSTDTC is a key reference date in clinical trials. The specific event it represents depends on trial design:

| Trial Phase | Definition | Priority |
|---|---|---|
| Randomized trial | Date of randomization | Prefer this if available |
| Open-label trial | Date of first treatment administration | Use if randomization not applicable |
| Enrollment study | Date of enrollment/screening visit | Use if treatment date not available |
| Post-hoc analysis | Date of screening start | Fallback |

If the source provides multiple candidate dates (e.g., RANDOMDT, FIRSTDOSEDT, ENROLLDT), apply the priority in the order above. Document which event was selected in provenance.rfstdtc_event = "randomization" | "first_dose" | "enrollment" | "screening"

### 4.2 Censoring and De-Identification

The data extraction shows that EMD_221 (50%) and Merck_188 (44.4%) have censored dates. Censoring is typically applied to protect subject privacy when dates could identify individuals:

- Censored dates appear as asterisks (e.g., "\*\*\*\*\*\*", "\*\*\*\*\*\*\*\*\*\*\*\*\*\*")
- Do NOT attempt to reconstruct, estimate, or infer censored dates
- Map to NULL and set confidence = UNMAPPED
- Set provenance.rfstdtc_censored = true
- Count censored records in QC report

### 4.3 Cross-Variable: Date Ordering (RFSTDTC <= RFENDTC)

Per DM_domain_rules.md Section 4.4, when both RFSTDTC and RFENDTC are present:
- RFENDTC must be >= RFSTDTC
- If RFENDTC < RFSTDTC, flag as DATE_ORDER_INVALID in QC report
- Preserve both source values; do not auto-correct
- Example: if RFSTDTC = 2009-07-18 and RFENDTC = 2009-07-10, flag the mismatch but keep both dates

### 4.4 SAS Numeric Date Conversion

If source data contains numeric dates (SAS format):
- Use the system_rules.md formula: ISO date = 1960-01-01 + (SAS_numeric value days)
- Document the conversion in provenance.rfstdtc_source_format = "SAS_numeric"
- *(SME review required)* - Verify the epoch; 1960-01-01 is standard but not universal

### 4.5 Invalid or Out-of-Range Dates

If RFSTDTC contains an obviously invalid date:
- Example: year 2288 (observed in Lilly_568)
- Flag as DATE_IMPLAUSIBLE for manual review
- Do not map; leave empty
- Include details in transformation report

### 4.6 Relationship to BRTHDTC (Age Derivation)

If both RFSTDTC and BRTHDTC are present and AGE is not available:
- Derive AGE = floor((RFSTDTC - BRTHDTC) / 365.25) per DM_domain_rules.md Section 4.1
- RFSTDTC is critical for this derivation
- Document in provenance.age_derived_from_brthdtc_and_rfstdtc = true

---

## 5. Provenance Flags

In addition to standard provenance fields (system_rules.md):

| Field | Type | Description |
|-------|------|-------------|
| `rfstdtc_source_column` | String | Name of the source column from which RFSTDTC was mapped |
| `rfstdtc_source_format` | String | "ISO_8601", "SAS_numeric", "DDMONYYYY", etc. |
| `rfstdtc_event_type` | String | "randomization", "first_dose", "enrollment", "screening" |
| `rfstdtc_censored` | Boolean | True if the date was redacted/censored in the source |
| `rfstdtc_time_precision` | String | "YYYY-MM-DDTHH:MM:SS", "YYYY-MM-DDTHH:MM", "YYYY-MM-DD", or "partial" |
| `rfstdtc_date_order_checked` | String | "OK" (RFSTDTC <= RFENDTC), "INVALID" (RFSTDTC > RFENDTC), or "N/A" (RFENDTC not available) |
| `rfstdtc_sas_epoch_confirmed` | Boolean | True if SAS epoch was confirmed with SME (if applicable) |

---

## 6. Validation Criteria *(SME review required for event type confirmation)*

### Conformance
- RFSTDTC must be in ISO 8601 format: YYYY-MM-DD, YYYY-MM-DDTHH:MM, or YYYY-MM-DDTHH:MM:SS
- No leading/trailing whitespace
- All date components must be valid (month 1-12, day 1-31, hour 0-23, minute 0-59, second 0-59)

### Plausibility
- **Date range:** For contemporary trials, RFSTDTC should fall within 2000-2025 (or study-specific range)
- **Censoring rate:** Document the rate of censored RFSTDTC values. High censoring (>50%) indicates significant de-identification and limits downstream temporal analysis
- **Date ordering:** Compare to RFENDTC (if present). Flag if RFSTDTC > RFENDTC
- **Age plausibility:** If BRTHDTC is available, verify that (RFSTDTC - BRTHDTC) / 365.25 results in a reasonable age (18-120 for adult trials)

### Determinism
- Within a single source dataset, the same source value must always map to the same target RFSTDTC

---

## 7. Known Limitations

1. **Significant censoring in EMD_221 and Merck_188.** 44-50% of RFSTDTC values are redacted. This limits the utility of RFSTDTC for time-to-event analyses and requires SME decisions about how to handle missing data downstream.

2. **Lilly_568 has mostly missing RFSTDTC (70.2% blank) and invalid dates when present (year 2288).** This dataset cannot reliably contribute temporal data to the harmonized dataset.

3. **No explicit event-type documentation in the data extraction.** The source columns (RFSTDTC, STARTDT, FIRSTDOSEDT, RANDOMDT, ENROLLDT) suggest the event type, but validation requires protocol review for each study.

4. **SAS epoch assumption (1960-01-01) is not confirmed for any dataset.** If numeric dates are encountered, SME confirmation is mandatory before conversion.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial spec; documented censoring patterns, date ordering rules, and SAS conversion |
