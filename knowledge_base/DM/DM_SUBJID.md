# DM Variable Specification: SUBJID

**Variable:** SUBJID
**Domain:** Demographics (DM)
**Order:** 2
**Required:** Yes
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The subject identifier assigned within the trial, uniquely identifying an individual subject within the context of a single trial (TRIAL). Must be unique in combination with TRIAL per DM_domain_rules.md Section 3 (cross-variable dependencies). Subject identifiers may be de-identified, sponsor-assigned, or encoded and may be stored as numeric (float or integer) or text.

**SDTM Reference:** DM.SUBJID — CDISC standard subject identifier variable

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.SUBJID | Subject identifier within study |
| HL7 FHIR | Patient.identifier | Individual patient ID |
| OMOP CDM | person_id | Unique person identifier |

**Note:** SUBJID is distinct from USUBJID (unique across studies). SUBJID may be numeric, text, or a de-identified proxy (e.g., "trials_d" column in AZ_205).

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | Notes |
|-------|-----------|-------|
| Numeric (integer) | Subject ID stored as integer (e.g., 1, 183, 493) | Convert from float if necessary (e.g., "183.0" → "183") |
| Numeric (text representation) | Subject ID as text string of digits (e.g., "001", "00183") | Preserve leading zeros if present in source |
| Alphanumeric text | Subject ID mixing letters and numbers (e.g., "221101001") | Common in multi-digit encoded IDs (site+subject) |
| De-identified proxy | Surrogate identifier (e.g., "trials_d" in AZ_205) | Maps to a unique subject within the trial |
| Unknown | No valid subject identifier could be extracted | confidence = UNMAPPED |

**Source Priority List:** SUBJID, SUBJ, PATID, SUBJECT, PATIENT_ID, TRIALS_D

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Data Type | Notes |
|---------|--------------|-------------|----------|-------|
| AZ_205 | trials_d | 1.0-1242.0 (1,805 unique) | float → int | De-identified numeric proxy; float-to-int conversion required |
| AZ_229 | SUBJ | 1.0-183.0 (266 unique) | float → int | Numeric codes; float-to-int conversion required |
| Amgen_265 | SUBJID | 221101001-223618005 (520 unique) | text | Large encoded numeric IDs (appears to encode site + subject) |
| EMD_221 | (implicit in USUBJID) | 1, 175-187 (inferred) | numeric | SUBJID extracted from USUBJID format |
| Lilly_568 | (implicit in USUBJID) | 0007, 0008, ... (formatted) | text | SUBJID extracted from USUBJID format (e.g., "I2V-MC-CXAC-9000-0007") |
| Merck_188 | SUBJID | 11-493 (507 unique) | integer | Direct integer IDs; no conversion required |
| Pfizer_374 | (not available) | — | — | No SUBJID in sparse extract |
| Sanofi_323 | (not available) | — | — | No SUBJID in sparse extract |

---

## 3. Mapping Decision Principles

1. **Convert float to integer when applicable.** SAS numeric data often stores integers as floats (e.g., "183.0" → "183"). Apply truncation/rounding and validate that no meaningful decimal precision is lost.

2. **Preserve source formatting when it conveys meaning.** If the source uses zero-padded strings (e.g., "001" vs. "1"), preserve leading zeros in text representation to maintain encoded information (e.g., site prefix).

3. **Encoded IDs must not be decoded.** Large numeric IDs like "221101001" may encode site + subject information (e.g., "2211" = site, "01001" = subject). Do not decompose or attempt to parse these; preserve as-is.

4. **De-identified proxies are acceptable.** If the source provides a de-identified surrogate (e.g., "trials_d"), use it as-is. The de-identification flag will be set in provenance.

5. **Do not attempt external ID mapping.** If SUBJID is missing or invalid, set to Unknown rather than attempting to infer from other columns (e.g., from row number or SITEID).

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| 183.0 (float) | 183 | HIGH | Float-to-int conversion; verify no precision loss |
| "183" (string) | 183 | HIGH | Text string of digits |
| "221101001" (string) | 221101001 | HIGH | Large encoded ID; preserve as-is |
| "001" (zero-padded) | 001 | HIGH | Preserve leading zeros if they convey site/block info |
| NULL, "", "N/A" | Unknown | UNMAPPED | Missing subject ID |
| "trials_d" (column label, not value) | (extract ID from column) | MEDIUM | De-identified proxy; use column values |

---

## 4. Variable-Specific Business Rules

### 4.1 Float-to-Integer Conversion

When source SUBJID is numeric float (common in SAS):
1. Extract the integer part (truncate or round)
2. Validate that no fractional part > 0.01 exists (data quality check)
3. If fractional part is significant, flag with `subjid_decimal_loss = true`
4. Document the conversion method in provenance

**Example:** AZ_229 SUBJ = "183.0" → SUBJID = "183"

### 4.2 Uniqueness Constraint

Per DM_domain_rules.md Section 3:
- SUBJID must be unique within (TRIAL, SUBJID) — i.e., no duplicate SUBJID values for the same TRIAL
- If duplicates are detected, flag for manual review; do not attempt to resolve

### 4.3 No Cross-Trial Mapping

SUBJID is valid only within its TRIAL context. If a subject appears in multiple trials with the same numeric ID, they are distinct subjects in the harmonized dataset. USUBJID derivation (Section 4.3 of DM_domain_rules.md) creates unique identifiers across trials by concatenating TRIAL + "-" + SUBJID.

---

## 5. Provenance Flags

In addition to the standard provenance fields defined in system_rules.md:

| Field | Type | Description |
|-------|------|-------------|
| `subjid_source_column` | String | Original source column name (SUBJID, SUBJ, PATID, TRIALS_D, etc.) |
| `subjid_conversion_method` | String | Data type conversion applied: "none", "float_to_int", "text_preserve" |
| `subjid_decimal_loss` | Boolean | True if float-to-int conversion removed meaningful decimal precision |
| `subjid_deidentified` | Boolean | True if source was de-identified proxy (e.g., trials_d) |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All values must be non-empty strings or integers, or "Unknown"
- No NULL or blank values (use "Unknown" instead)

### Plausibility
- SUBJID must be unique within (TRIAL, SUBJID) combination
- All SUBJID values within a trial should be present (no gaps, unless expected by study design)
- Numeric SUBJID ranges should be reasonable (e.g., 1-520 for 520 subjects, not scattered 1-999999)

### Determinism
- Repeated extraction of the same source file must yield identical SUBJID values
- Float-to-int conversions must be applied consistently

---

## 7. Known Limitations

1. **Float-to-integer conversion is lossy.** SAS numeric data may lose precision during conversion. The `subjid_decimal_loss` flag captures this, but manual inspection is recommended for datasets with many subjects.
2. **De-identified proxies prevent subject matching.** AZ_205's "trials_d" column is a de-identified proxy, making it impossible to re-identify subjects across external data sources.
3. **Encoded IDs are opaque.** Amgen's large numeric IDs (221101001-223618005) appear to encode site + subject, but without the decoding dictionary, they cannot be decomposed for analysis. *(SME review required)*
4. **Pfizer and Sanofi datasets lack SUBJID.** These sparse extracts cannot produce valid SUBJID values; all records will have Unknown.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (standalone format) |
| 2.0 | 2026-04-08 | Revised for three-tier hierarchy; added float-to-int conversion guidance; documented observed data patterns (AZ float codes, Amgen encoded IDs, Merck integers); marked SME review points |
