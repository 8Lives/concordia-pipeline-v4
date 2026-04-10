# DM Variable Specification: RFENDTC

**Variable:** RFENDTC
**Domain:** Demographics (DM)
**Order:** 17
**Required:** Optional
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The reference end date of the subject's participation in the trial. This date represents the latest of: last treatment/study drug administration date, study completion date, discontinuation date, or final follow-up visit date, depending on trial design. RFENDTC is captured in ISO 8601 format and marks the end of the subject's active trial participation.

**SDTM Reference:** DM.RFENDTC — CDISC SDTM DM domain, ISO 8601 format with optional time

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| ISO 8601 | Date/time format | YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS |
| CDISC SDTM | DM.RFENDTC | Reference end date/time |
| Clinical Trial Design | Last visit date | Last dose, study completion, or discontinuation |

---

## 2. Allowed Values

RFENDTC accepts ISO 8601 date and date/time strings:

| Format | Example | Notes |
|--------|---------|-------|
| Full date/time | 2010-12-15T15:30:00 | Year, month, day, hour, minute, second |
| Date/time (minutes) | 2010-12-15T15:30 | Year, month, day, hour, minute |
| Date only | 2010-12-15 | Year, month, and day |
| Censored | \*\*\*\*\*\* (variable length) | De-identified dates; treat as NULL |
| Unknown | (empty, NULL) | Source value missing or unable to determine |

**Source Priority List:** RFENDTC, RFENDT, ENDDT, LASTDOSEDT, COMPLDT, DISCDT, LASTVISITDT

**Observed Source Patterns (from data extraction):**

| Sponsor | Source Column | Format | Censoring | Range | Notes |
|---------|---|---|---|---|---|
| EMD_221 | RFENDTC | YYYY-MM-DD (date-only) | 30.6% censored (represented as "\*\*\*\*\*\*") | 2010-2011 | More complete than RFSTDTC |
| Merck_188 | RFENDTC | YYYY-MM-DD (date-only) | 75.4% censored | 2010-2014 | Heavily censored; high missing rate |
| Lilly_568 | RFENDTC | YYYY-MM-DD or blank | 70.2% blank | 2288-2289 (when present) | Mostly missing; invalid year range |
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
   - Mark provenance.rfendtc_censored = true
   - Do not attempt to reconstruct or infer the date

4. **Validate plausibility:** Cross-check against RFSTDTC and trial timeline:
   - RFENDTC should be >= RFSTDTC (per DM_domain_rules.md Section 4.4)
   - RFENDTC should be after RFSTDTC by a reasonable duration (trial length typically days to years)
   - RFENDTC should be in a reasonable range for the trial

5. **Assign confidence based on data completeness.**
   - HIGH: Full date with time (YYYY-MM-DDTHH:MM), not censored
   - MEDIUM: Date-only (YYYY-MM-DD), not censored
   - LOW: Partial date (YYYY-MM or YYYY), or time component missing
   - UNMAPPED: Censored or unable to determine

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "2010-12-15T15:30" | 2010-12-15T15:30 | HIGH | Full datetime; case/format normalized |
| "2010-12-15" | 2010-12-15 | MEDIUM | Date-only; time not provided in source |
| "15DEC2010" | 2010-12-15 | MEDIUM | Date parsed and converted to ISO 8601 |
| "\*\*\*\*\*\*" (censored) | (empty) | UNMAPPED | Redacted for privacy; cannot map |
| "2288-01-01" (invalid year) | — | — | Data quality issue; flag and leave empty |
| NULL, "", "N/A" | (empty) | HIGH | Legitimately missing |

---

## 4. Variable-Specific Business Rules

### 4.1 Reference End Date Definition

RFENDTC is the final date of a subject's trial participation. The specific event it represents depends on trial design:

| Trial Status | Definition | Priority |
|---|---|---|
| Completed | Date of final visit or last dose | Prefer this if available |
| Early discontinued | Date of discontinuation or last contact | Use if completion not applicable |
| Lost to follow-up | Date of last known visit | Use if discontinuation not documented |
| Still ongoing | Current/enrollment end date | Use if trial is still accruing |

If the source provides multiple candidate dates (e.g., LASTDOSEDT, COMPLDT, DISCDT, LASTVISITDT), apply the priority in the order above. Document which event was selected in provenance.rfendtc_event = "completion" | "discontinuation" | "lost_to_followup" | "last_contact"

### 4.2 Censoring and De-Identification

The data extraction shows that EMD_221 (30.6%) and Merck_188 (75.4%) have censored end dates. Censoring is typically applied to protect subject privacy or to obscure exact trial completion timelines:

- Censored dates appear as asterisks (e.g., "\*\*\*\*\*\*", "\*\*\*\*\*\*\*\*\*\*\*\*")
- Do NOT attempt to reconstruct, estimate, or infer censored dates
- Map to NULL and set confidence = UNMAPPED
- Set provenance.rfendtc_censored = true
- Count censored records in QC report
- *(SME review required)* for Merck_188: 75.4% censoring is unusually high; confirm this is intentional de-identification

### 4.3 Cross-Variable: Date Ordering (RFSTDTC <= RFENDTC)

Per DM_domain_rules.md Section 4.4, when both RFSTDTC and RFENDTC are present:
- RFENDTC must be >= RFSTDTC
- If RFENDTC < RFSTDTC, flag as DATE_ORDER_INVALID in QC report
- Preserve both source values; do not auto-correct
- Example: if RFSTDTC = 2009-07-18 and RFENDTC = 2009-07-10, flag the mismatch but keep both dates

### 4.4 Duration Plausibility (RFENDTC - RFSTDTC)

Calculate the trial duration: trial_duration_days = (RFENDTC - RFSTDTC)
- For typical clinical trials, this ranges from days (acute studies) to years (chronic disease trials)
- If trial_duration_days < 0, flag as DATE_ORDER_INVALID
- If trial_duration_days > 10 years, flag as LONG_TRIAL_DURATION for review (may be valid but unusual)
- If trial_duration_days < 1 day, flag as VERY_SHORT_DURATION for review (may indicate same-day enrollment and discharge)

### 4.5 SAS Numeric Date Conversion

If source data contains numeric dates (SAS format):
- Use the system_rules.md formula: ISO date = 1960-01-01 + (SAS_numeric value days)
- Document the conversion in provenance.rfendtc_source_format = "SAS_numeric"
- *(SME review required)* - Verify the epoch; 1960-01-01 is standard but not universal

### 4.6 Invalid or Out-of-Range Dates

If RFENDTC contains an obviously invalid date:
- Example: year 2288 (observed in Lilly_568)
- Flag as DATE_IMPLAUSIBLE for manual review
- Do not map; leave empty
- Include details in transformation report

### 4.7 Relationship to Trial Duration

Many clinical trials have a defined duration (e.g., 12 weeks, 6 months, 2 years). If available:
- Calculate expected_end_date = RFSTDTC + trial_duration
- Compare to RFENDTC
- If difference > 10% of trial duration, flag for review (may indicate early withdrawal, extended follow-up, or data recording issues)

---

## 5. Provenance Flags

In addition to standard provenance fields (system_rules.md):

| Field | Type | Description |
|-------|------|-------------|
| `rfendtc_source_column` | String | Name of the source column from which RFENDTC was mapped |
| `rfendtc_source_format` | String | "ISO_8601", "SAS_numeric", "DDMONYYYY", etc. |
| `rfendtc_event_type` | String | "completion", "discontinuation", "lost_to_followup", "last_contact" |
| `rfendtc_censored` | Boolean | True if the date was redacted/censored in the source |
| `rfendtc_time_precision` | String | "YYYY-MM-DDTHH:MM:SS", "YYYY-MM-DDTHH:MM", "YYYY-MM-DD", or "partial" |
| `rfendtc_date_order_checked` | String | "OK" (RFSTDTC <= RFENDTC), "INVALID" (RFENDTC < RFSTDTC), or "N/A" (RFSTDTC not available) |
| `rfendtc_trial_duration_days` | Integer | Duration in days between RFSTDTC and RFENDTC (if both present) |
| `rfendtc_sas_epoch_confirmed` | Boolean | True if SAS epoch was confirmed with SME (if applicable) |

---

## 6. Validation Criteria *(SME review required for censoring justification and trial duration)*

### Conformance
- RFENDTC must be in ISO 8601 format: YYYY-MM-DD, YYYY-MM-DDTHH:MM, or YYYY-MM-DDTHH:MM:SS
- No leading/trailing whitespace
- All date components must be valid (month 1-12, day 1-31, hour 0-23, minute 0-59, second 0-59)

### Plausibility
- **Date range:** For contemporary trials, RFENDTC should fall within 2000-2025 (or study-specific range)
- **Date ordering:** RFENDTC >= RFSTDTC when both are present. Flag if violated
- **Trial duration:** Should be consistent with the trial protocol (typically days to years). Flag if < 1 day or > 10 years
- **Censoring rate:** Document the rate of censored RFENDTC values
  - EMD_221: 30.6% censored (moderate; manageable)
  - Merck_188: 75.4% censored (very high; significant data loss for temporal analysis)
- **Consistency across records:** Within a single trial, most subjects should have similar trial durations (±10%). Outliers may indicate early withdrawals (valid) or data entry errors

### Determinism
- Within a single source dataset, the same source value must always map to the same target RFENDTC

---

## 7. Known Limitations

1. **Merck_188 has very high censoring (75.4%) in RFENDTC.** This severely limits the utility of this dataset for temporal analysis and trial duration calculations. SME clarification is needed on whether this is intentional de-identification.

2. **Lilly_568 has mostly missing RFENDTC (70.2% blank) and invalid dates when present (year 2288).** This dataset cannot reliably contribute temporal data to the harmonized dataset.

3. **No explicit event-type documentation in the data extraction.** The source columns (RFENDTC, LASTDOSEDT, COMPLDT, DISCDT) suggest the event type, but validation requires protocol review for each study.

4. **EMD_221 and Merck_188 provide date-only RFENDTC (no time component).** This limits precision for calculating trial duration in hours or minutes, though day-level precision is typically sufficient for trial analysis.

5. **SAS epoch assumption (1960-01-01) is not confirmed for any dataset.** If numeric dates are encountered, SME confirmation is mandatory before conversion.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial spec; documented censoring patterns, date ordering rules, and trial duration validation |
