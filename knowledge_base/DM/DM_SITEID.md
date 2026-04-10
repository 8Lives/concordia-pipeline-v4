# DM Variable Specification: SITEID

**Variable:** SITEID
**Domain:** Demographics (DM)
**Order:** 10
**Required:** Optional
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The investigational site identifier assigned by the trial sponsor, uniquely identifying the clinical site (hospital, clinic, research center) where the subject was enrolled. SITEID may be numeric (with or without zero-padding) or alphanumeric. Format and encoding are sponsor-specific and must be preserved without normalization.

**SDTM Reference:** DM.SITEID — CDISC standard investigational site identifier

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.SITEID | Investigational site identifier within study |
| HL7 FHIR | Organization.identifier | Healthcare facility ID |
| ISO 21090 | II (Instance Identifier) | Site organization ID |

**Note:** SITEID is distinct from COUNTRY. A single site is located in one country but multiple sites may exist within a country. Sites are identified by sponsor-assigned codes, not by external standards (unlike ISO 3166 for countries).

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | Notes |
|-------|-----------|-------|
| Numeric (zero-padded) | Site ID as numeric string with leading zeros (e.g., "0003", "3105") | Preserve zero-padding; do not convert to integer |
| Numeric (unpadded) | Site ID as numeric string without padding (e.g., "3", "184") | Preserve as-is |
| Alphanumeric text | Site ID mixing letters and numbers (rare; not observed in prototype data) | Preserve exact format |
| Unknown | No valid SITEID could be extracted | confidence = UNMAPPED |

**Source Priority List:** SITEID, SITE, CENT, CENTER, INVSITE, CNTR

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Count | Range | Format | Notes |
|---------|--------------|-------------|-------|-------|--------|-------|
| AZ_205 | (not present) | — | 0 | — | — | No SITEID in dataset |
| AZ_229 | CENT | 3003-3105 (numeric) | 266 records | 3003-3105 | De-identified numeric | 134 unique sites; 4-digit numeric codes; appears to be de-identified site IDs |
| Amgen_265 | SITEID | 1101-4404 (numeric) | 520 records | 1101-4404 | Numeric with zero-padding | 93 unique sites; 4-digit codes; likely site numbers with padding |
| EMD_221 | SITEID | 5-113 (numeric) | 273 records | 5-113 | Numeric unpadded | 116 unique sites; 1-3 digit codes; minimal or no padding |
| Lilly_568 | (not present) | — | 0 | — | — | No SITEID in dataset |
| Merck_188 | SITEID | 3-184 (numeric) | 507 records | 3-184 | Numeric unpadded | 187 unique sites; 1-3 digit codes; minimal padding |
| Pfizer_374 | (not available) | — | 0 | — | — | No SITEID in sparse extract |
| Sanofi_323 | (not available) | — | 0 | — | — | No SITEID in sparse extract |

---

## 3. Mapping Decision Principles

1. **Preserve original format without normalization.** Do not zero-pad unpadded numeric IDs or remove zero-padding from padded IDs. Store as text strings to maintain leading zeros.

2. **Accept both numeric and alphanumeric formats.** While prototype data contains only numeric SITEIDs, alphanumeric formats are acceptable and must be preserved as-is.

3. **Do not attempt to decode or standardize site codes.** Sponsor-assigned site IDs may be de-identified, re-encoded, or follow internal naming conventions. Do not interpret, parse, or normalize these codes.

4. **Multiple SITEIDs per trial are expected.** Unlike STUDYID (one per file), SITEID varies across subjects. A typical trial has 50-200+ unique sites. This is normal and expected.

5. **Missing SITEID is acceptable.** Some datasets (AZ_205, Lilly_568, Pfizer_374, Sanofi_323) do not provide site information. Set SITEID to Unknown for these records; this is not a data quality error.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| 3105 (numeric, zero-padded) | 3105 | HIGH | Store as text to preserve padding |
| 1101 (numeric, zero-padded) | 1101 | HIGH | Store as text to preserve padding |
| 5 (numeric, unpadded) | 5 | HIGH | Store as text; do not pad |
| 3 (numeric, unpadded) | 3 | HIGH | Store as text; do not pad |
| NULL, "", "N/A" | Unknown | UNMAPPED | Missing site information |

---

## 4. Variable-Specific Business Rules

### 4.1 Format Preservation

Store SITEID as text string (not numeric):
- Preserves leading zeros (e.g., "0003" ≠ "3")
- Allows for alphanumeric formats if present in future datasets
- Prevents unintended numeric conversions

**Example:** AZ_229 CENT = 3105 → SITEID = "3105" (not 3105 as integer)

### 4.2 Within-Trial Uniqueness (Validation Only)

Each SITEID should be unique within a trial (one site per code). If a SITEID appears with conflicting metadata (e.g., same site ID in two different countries), flag for review but do not attempt to resolve.

### 4.3 Multi-Subject Sites

Multiple subjects may be enrolled at the same SITEID. This is expected:
- A single site typically enrolls 1-10+ subjects
- Distribution of subjects across sites is driven by trial design
- No validation should penalize repeated SITEID values

---

## 5. Provenance Flags

In addition to the standard provenance fields defined in system_rules.md:

| Field | Type | Description |
|-------|------|-------------|
| `siteid_source_column` | String | Source column name (SITEID, SITE, CENT, CENTER, INVSITE, CNTR) |
| `siteid_format_preserved` | Boolean | True if zero-padding or non-standard formatting was preserved as-is |
| `siteid_deidentified` | Boolean | True if site codes appear to be de-identified or re-encoded (e.g., AZ_229 CENT = 3003-3105 range) |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All SITEID values must be non-empty strings or "Unknown"
- No NULL or blank values (use "Unknown" instead)
- Values should match the source format exactly

### Plausibility
- Multiple SITEID values are expected within a trial
- Site count should be reasonable relative to subject count (e.g., 93 sites for 520 subjects in Amgen_265)
- No validation penalty if SITEID is Unknown (acceptable for sparse datasets)

### Determinism
- Repeated extraction of the same source file must yield identical SITEID values
- Format must be preserved consistently (no normalization between runs)

---

## 7. Known Limitations

1. **Site format variation.** No standardized SITEID format exists across sponsors. AZ uses 4-digit codes (3003-3105), Amgen uses 4-digit codes (1101-4404), EMD/Merck use 1-3 digit codes. Integration requires tolerating this variation.
2. **Site de-identification is opaque.** AZ_229's CENT column appears to use de-identified numeric codes (range 3003-3105). Without a site reference table, these codes cannot be mapped to actual clinical sites.
3. **No external validation.** SITEID codes cannot be validated against external registries (unlike TRIAL/NCT or country codes/ISO 3166). Validation depends entirely on sponsor-provided documentation.
4. **Four of eight sponsors lack SITEID.** AZ_205, Lilly_568, Pfizer_374, and Sanofi_323 provide no site information. This is acceptable for certain study designs (centralized lab studies, claims data) but limits site-level analysis capability.
5. **SITEID does not indicate country.** A sponsor may assign site codes that do not encode country information. Country must be obtained from the COUNTRY variable separately.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (standalone format) |
| 2.0 | 2026-04-08 | Revised for three-tier hierarchy; documented 4 sponsors with SITEID data (AZ_229: 134 sites 3003-3105, Amgen_265: 93 sites 1101-4404, EMD_221: 116 sites 5-113, Merck_188: 187 sites 3-184); clarified format preservation rules; noted 4 sponsors without SITEID; marked SME review for de-identification and external validation gaps |
