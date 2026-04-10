# DM Variable Specification: TRIAL

**Variable:** TRIAL
**Domain:** Demographics (DM)
**Order:** 1
**Required:** Yes
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The NCT (National Clinical Trial) identifier uniquely identifying the clinical trial from which the subject's demographic data was extracted. Must match the format `^NCT\d{8}$` (NCT prefix followed by exactly 8 digits). This identifier bridges sponsor-specific protocols to the public clinical trial registry.

**SDTM Reference:** Custom harmonization variable (not in standard SDTM, analogous to STUDYID but pointing to NCT registry)

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| ClinicalTrials.gov | NCT identifier | https://clinicaltrials.gov/ |
| SDTM | STUDYID | Protocol identifier (sponsor-specific) |

**Note:** NCT IDs are distinct from sponsor protocol IDs (e.g., "D4320C00014", "CASO0024"). The TRIAL variable captures the public clinical trial registry ID, often derived from filename conventions or cross-referenced with sponsor documentation.

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | Notes |
|-------|-----------|-------|
| NCT\d{8} | Valid NCT identifier matching regex `^NCT\d{8}$` | Must have exactly 8 digits after "NCT" prefix |
| Unknown | Source data provided no valid NCT ID and could not be extracted from filename | confidence = UNMAPPED |

**Source Priority List:** TRIAL, NCTID, NCT_ID, CLINICALTRIALS_ID, filename pattern

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Derivation Method |
|---------|--------------|-------------|-------------------|
| AZ_205 | (not present) | Extracted from filename: `demog_NCT00673205.sas7bdat` | Filename regex: `NCT\d{8}` |
| AZ_229 | (not present) | Extracted from filename: `demog_NCT00554229.sas7bdat` | Filename regex: `NCT\d{8}` |
| Amgen_265 | (not present) | Extracted from filename: `demog_NCT00460265.sas7bdat` | Filename regex: `NCT\d{8}` |
| EMD_221 | (not present) | Extracted from filename: `demog_NCT00689221.sas7bdat` | Filename regex: `NCT\d{8}` |
| Lilly_568 | (not present) | Extracted from filename: `demog_NCT01439568.sas7bdat` | Filename regex: `NCT\d{8}` |
| Merck_188 | (not present) | Extracted from filename: `demog_NCT00409188.sas7bdat` | Filename regex: `NCT\d{8}` |
| Pfizer_374 | (not present) | Extracted from filename: `demog_NCT00699374.sas7bdat` | Filename regex: `NCT\d{8}` |
| Sanofi_323 | (not present) | Extracted from filename: `demog_NCT00401323.sas7bdat` | Filename regex: `NCT\d{8}` |

---

## 3. Mapping Decision Principles

1. **Filename extraction is the primary source.** If the source file conforms to the naming convention `[prefix]_NCT\d{8}\.[extension]`, extract the NCT ID via regex match.

2. **Do not confuse NCT IDs with sponsor protocols.** Sponsor protocol IDs like "D4320C00014" (AZ), "CASO0024" (AZ), "20050251" (Amgen), "EMD121974011" (EMD), "I2V-MC-CXAC" (Lilly), "EMR63325-001" (Merck) are stored in STUDYID or domain rules derivations, not in TRIAL.

3. **NCT IDs are constant within a dataset.** All records in a single extract file must have the same TRIAL value. If multiple NCT IDs appear in a single file (data error), flag for review.

4. **If NCT ID cannot be extracted, set to Unknown with confidence = UNMAPPED.** Do not attempt to infer the NCT ID from external sources without explicit mapping documentation.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| Filename: `demog_NCT00673205.csv` | NCT00673205 | HIGH | Standard extraction via regex |
| Column value: "NCT00554229" | NCT00554229 | HIGH | Explicit NCT column |
| Column value: "D4320C00014" | Unknown | UNMAPPED | Sponsor protocol, not NCT — do not map |
| Column value: NULL, "", "N/A" | Unknown | UNMAPPED | Missing NCT information |

---

## 4. Variable-Specific Business Rules

### 4.1 Filename Extraction Logic

When extracting TRIAL from the source filename:
- Apply regex pattern: `NCT\d{8}`
- Extract the first match from the filename
- If multiple matches exist (unlikely), use the first occurrence and flag for review

Example: `demog_NCT00673205_v2.sas7bdat` → extract `NCT00673205`

### 4.2 Constant-per-File Rule

All records in a single file must have the same TRIAL value. If a data extraction produces multiple distinct TRIAL values in a single file, this indicates:
- A data merge error (multiple studies combined incorrectly)
- Filename mislabeling
- Manual review is required

### 4.3 Immutability

TRIAL values are immutable once assigned. If a record's TRIAL value changes between extraction runs, this is a critical data integrity issue to be escalated.

---

## 5. Provenance Flags

In addition to the standard provenance fields defined in system_rules.md:

| Field | Type | Description |
|-------|------|-------------|
| `trial_source_method` | String | Source method: "filename_extraction", "column_explicit", "unmapped" |
| `trial_extraction_regex` | String | Regex pattern used to extract NCT ID (if derived from filename) |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All values must match regex `^NCT\d{8}$` or be "Unknown"
- No NULL or missing values (use "Unknown" instead)

### Plausibility
- TRIAL value must be constant across all records in a single extract file
- If multiple TRIAL values exist in a single file, flag for data integrity review

### Determinism
- Filename-extracted TRIAL must be reproducible: same filename → same TRIAL value

---

## 7. Known Limitations

1. **No TRIAL variable in source data.** All 8 sponsor datasets lack an explicit TRIAL or NCTID column; extraction depends entirely on filename conventions.
2. **Filename format variation risk.** If source files are renamed or reorganized without preserving NCT ID in the filename, TRIAL extraction will fail. *(SME review required)*
3. **Sponsor protocol confusion.** The prominence of sponsor-specific IDs (STUDYID column) in source data may lead to confusion with TRIAL. Documentation and data dictionaries must clarify this distinction.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (standalone format) |
| 2.0 | 2026-04-08 | Revised for three-tier hierarchy; added filename extraction guidance; noted all 8 sponsors require filename parsing; marked SME review points |
