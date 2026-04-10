# DM Variable Specification: STUDYID

**Variable:** STUDYID
**Domain:** Demographics (DM)
**Order:** 11
**Required:** Optional
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The sponsor-assigned study or protocol identifier uniquely identifying the clinical trial within the sponsor's internal systems. Distinct from TRIAL (the public NCT identifier). STUDYID captures how the sponsor refers to the trial in their operational data, regulatory submissions, and internal protocols. Format varies widely (alphanumeric, numeric-only, abbreviated).

**SDTM Reference:** DM.STUDYID — CDISC standard study identifier (sponsor-assigned protocol ID)

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.STUDYID | Sponsor protocol identifier |
| FDA Guidance | Study Identifier | Sponsor-assigned protocol number in regulatory submissions |
| EMA Guidelines | Protocol Number | Sponsor's internal study reference |

**Note:** STUDYID is distinct from TRIAL (NCT identifier). A single clinical trial may be referred to by multiple protocol IDs across different sponsors or regions (e.g., a multi-sponsor trial). STUDYID is required for USUBJID derivation fallback if TRIAL is unavailable.

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | Notes |
|-------|-----------|-------|
| Alphanumeric text | Sponsor protocol ID (e.g., "CASO0024", "D4320C00014", "I2V-MC-CXAC") | Preserve exact format and case from source |
| Numeric text | Numeric-only protocol ID (e.g., "20050251", "EMD121974011") | May include leading zeros or embedded codes |
| Single unique value per dataset | STUDYID is constant across all records in a file (one study per extract) | All 8 sponsor datasets have exactly one STUDYID value |
| Unknown | No valid STUDYID could be extracted | confidence = UNMAPPED |

**Source Priority List:** STUDYID, STUDY, PROTID, PROTOCOL, STUDYCODE

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Format | Notes |
|---------|--------------|-------------|--------|-------|
| AZ_205 | PROTID | "CASO0024" (1,805 records) | Alphanumeric | Single unique value; no variation |
| AZ_229 | STUDY | "D4320C00014" (266 records) | Alphanumeric | Single unique value; embedded code (D4320C = compound ID?) |
| Amgen_265 | STUDYID | "20050251" (520 records) | Numeric | Single unique value; 8-digit numeric code |
| EMD_221 | STUDYID | "EMD121974011" (273 records) | Alphanumeric | Single unique value; embedded source code (EMD = sponsor prefix?) |
| Lilly_568 | STUDYID | "I2V-MC-CXAC" (130 records) | Alphanumeric | Single unique value; hyphenated format (I2V = internal code, MC/CXAC = trial codes?) |
| Merck_188 | STUDYID | "EMR63325-001" (507 records) | Alphanumeric | Single unique value; hyphenated format (EMR = Merck prefix?, 63325 = compound ID, 001 = protocol revision?) |
| Pfizer_374 | (not available) | — | — | No STUDYID in sparse extract |
| Sanofi_323 | (not available) | — | — | No STUDYID in sparse extract |

---

## 3. Mapping Decision Principles

1. **Preserve source format exactly.** Do not normalize, abbreviate, or decode sponsor protocol IDs. Case sensitivity and punctuation (hyphens, underscores) must be preserved as-is.

2. **STUDYID is constant per file.** All records in a single extract must have the same STUDYID value. If multiple STUDYID values appear in a single file, flag as a data integrity issue and use the most frequent value with a confidence reduction.

3. **Do not attempt to parse encoded IDs.** Sponsor protocol IDs often embed codes (e.g., "D4320C" may encode compound + trial, "EMR63325-001" may encode Merck + compound + revision). Do not decompose or interpret these; preserve as-is.

4. **Map from source column with priority order.** Use the first available source column from the priority list: STUDYID, STUDY, PROTID, PROTOCOL, STUDYCODE.

5. **Do not confuse STUDYID with TRIAL.** STUDYID is the sponsor's internal identifier; TRIAL is the public NCT identifier. Both are captured separately.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "CASO0024" | CASO0024 | HIGH | Direct match from PROTID column |
| "D4320C00014" | D4320C00014 | HIGH | Direct match from STUDY column; preserve embedded codes |
| "20050251" | 20050251 | HIGH | Numeric code; preserve as text string |
| "EMD121974011" | EMD121974011 | HIGH | Alphanumeric; likely EMD (sponsor) + protocol code |
| "I2V-MC-CXAC" | I2V-MC-CXAC | HIGH | Hyphenated format; preserve hyphens |
| "EMR63325-001" | EMR63325-001 | HIGH | Hyphenated format; possibly compound ID + revision |
| NULL, "", "N/A" | Unknown | UNMAPPED | Missing STUDYID |
| Multiple distinct values in same file | (most frequent) | MEDIUM | Data integrity issue; flag for review |

---

## 4. Variable-Specific Business Rules

### 4.1 One STUDYID per File

All records extracted from a single source file must have the same STUDYID:
- If all records match, proceed with confidence = HIGH
- If records differ (e.g., merged data from two trials), flag as data quality issue:
  - Use the most frequent STUDYID value
  - Set confidence = LOW
  - Document the multiple values in provenance

### 4.2 STUDYID in USUBJID Derivation

Per DM_domain_rules.md Section 4.3, STUDYID is used as a fallback for USUBJID derivation if TRIAL cannot be extracted:
```
IF TRIAL is NULL THEN
  USUBJID := STUDYID + "-" + SUBJID
ENDIF
```

This means STUDYID must be available and non-null for USUBJID derivation to succeed in the fallback case.

### 4.3 No Normalization

STUDYID must not be normalized (uppercased, lowercased, or reformatted) during extraction. Preserve the source value exactly, including:
- Case (e.g., "I2V-MC-CXAC" vs. "i2v-mc-cxac")
- Hyphens, underscores, periods
- Leading/trailing spaces (trim only if clearly formatting artifact)

---

## 5. Provenance Flags

In addition to the standard provenance fields defined in system_rules.md:

| Field | Type | Description |
|-------|------|-------------|
| `studyid_source_column` | String | Source column name (STUDYID, STUDY, PROTID, PROTOCOL, etc.) |
| `studyid_multiple_values_in_file` | Boolean | True if multiple distinct STUDYID values detected in same extract file |
| `studyid_embedded_codes` | String | Optional: documented embedded code structure (e.g., "EMD (sponsor) + protocol number") |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All values must be non-empty strings or "Unknown"
- No NULL or blank values (use "Unknown" instead)
- Must match one of the observed sponsor-specific formats

### Plausibility
- STUDYID must be constant across all records in a single extract file
- If multiple STUDYID values exist, document in provenance and use most frequent

### Determinism
- Same source file, extracted multiple times, must yield identical STUDYID values
- Source formatting must be preserved exactly (no normalization)

---

## 7. Known Limitations

1. **Sponsor-specific format variation.** No standardized STUDYID format exists across sponsors. Lilly uses "I2V-MC-CXAC", AZ uses "CASO0024", Merck uses "EMR63325-001". Analysis systems must accommodate this variation.
2. **Embedded codes are opaque.** Protocol IDs often encode sponsor/compound/trial information (e.g., "D4320C00014", "EMD121974011"). Without decoder documentation, these codes cannot be parsed for analysis. *(SME review required)*
3. **Pfizer and Sanofi datasets lack STUDYID.** Both sparse extracts do not provide STUDYID, only one cannot derive USUBJID via the STUDYID fallback route.
4. **No external validation reference.** Unlike TRIAL (which maps to ClinicalTrials.gov), STUDYID cannot be externally validated. Data quality assurance depends on sponsor documentation.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (standalone format) |
| 2.0 | 2026-04-08 | Revised for three-tier hierarchy; documented all 8 sponsor STUDYID formats (CASO0024, D4320C00014, 20050251, EMD121974011, I2V-MC-CXAC, EMR63325-001); clarified STUDYID vs. TRIAL distinction; noted one-value-per-file rule; marked SME review for embedded code semantics |
