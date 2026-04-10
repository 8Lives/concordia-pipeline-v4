# DM Variable Specification: ARMCD

**Variable:** ARMCD
**Domain:** Demographics (DM)
**Order:** 13
**Required:** Optional
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** A code or abbreviation that uniquely identifies the subject's assigned or randomized treatment arm. ARMCD is the coded representation of ARM; it is shorter, machine-readable, and suitable for cross-tabulations and statistical analysis.

**SDTM Reference:** DM.ARMCD — CDISC SDTM DM domain

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.ARMCD | Treatment arm code |
| Protocol Coding | Randomization tables | Assigned treatment arm codes |

---

## 2. Allowed Values

ARMCD is a code set specific to each study. There is no fixed CDISC controlled terminology codelist; each trial defines its own ARMCD values. Common patterns include:

| Pattern | Example | Notes |
|---------|---------|-------|
| Abbreviated drug name | "PBO", "LY2510", "PANIT" | Derived from drug name |
| Numbered arms | "ARM1", "ARM2", "ARM3" | Generic arm numbering |
| Protocol codes | "CONTRGRP", "TRT_A", "TRT_B" | Study-specific codes |
| Alphanumeric | "A", "B", "C", "SF" | Minimal codes |

**Source Priority List:** ARMCD, TRTCD, TRTCODE, TRTNUM, ATRTCD, TREATCD

**Observed Source Patterns (from data extraction):**

| Sponsor | Source Columns | Values Found | Notes |
|---------|---|---|---|
| AZ_229 | TRTCODE | (numeric, not shown in extraction summary) | Integer code; need to check dictionary |
| Amgen_265 | TRTCD | (numeric, not shown; multiple values inferred from ARM) | Paired with ARM "Panit. plus chemotherapy" and "Chemotherapy" |
| EMD_221 | ARMCD (direct) | "CONTRGRP" (273, 100%) | Pre-coded, all control |
| Lilly_568 | ARMCD (direct) | (implied from ARM text, not explicitly shown) | Multi-arm codes not detailed in extraction |
| Merck_188 | ARMCD (direct) | "PLACEBO" (507, 100%) | Single-arm code |
| AZ_205, Pfizer_374, Sanofi_323 | — | *(not available)* | No treatment arm variables in extracted data |

---

## 3. Mapping Decision Principles

1. **Prefer explicit ARMCD source columns.** If the source contains a column labeled ARMCD, TRTCD, TRTCODE, or TRTNUM with coded values, map directly. Do not remap or expand codes.

2. **If only ARM (description) is available, leave ARMCD empty.** Do not attempt to derive codes from text without a data dictionary or protocol specification.

3. **Do not invent codes.** If the source has ARM but no code, ARMCD remains empty. Downstream systems may derive codes during SDTM creation if needed, but harmonization at the source level should preserve only what is explicitly provided.

4. **Normalize codes consistently:** uppercase all ARMCD codes for consistency within a dataset
   - "arm1" → "ARM1"
   - "pbo" → "PBO"
   - "contrgrp" → "CONTRGRP"

5. **1:1 consistency with ARM.** If both ARM and ARMCD are present, ensure that the mapping is 1:1 and deterministic (same code always maps to the same description and vice versa).

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "PBO", "pbo", "PBO " | PBO | HIGH | Code present; case-normalized, whitespace trimmed |
| "CONTRGRP" | CONTRGRP | HIGH | Code present; no normalization needed |
| 1 (with dictionary: 1=PBO) | PBO | HIGH | Numeric code decoded via dictionary |
| 1 (no dictionary, context) | — | — | Code with no dictionary; leave empty if unmappable |
| "Placebo" (ARM text, no ARMCD) | — | — | Only description; ARMCD left empty |
| "SF", "SCREEN FAILURE" (status code) | SF | MEDIUM | Screen failure; may require special handling |

---

## 4. Variable-Specific Business Rules

### 4.1 Conditional Pairing with ARM

ARMCD and ARM form a logical pair when both are populated:
- Every unique ARMCD should map to exactly one ARM (1:1 relationship)
- If a dataset has multiple ARMCD values that all map to the same ARM, flag as a potential data quality issue
- If a dataset has one ARMCD mapping to multiple ARM values, flag for manual review

### 4.2 Numeric Code Decoding

If the source ARMCD is numeric (e.g., 1, 2, 3):
- Attempt to decode using the trial's data dictionary or codebook
- If successful, map to the decoded code (e.g., 1 → "PBO")
- If no dictionary is available or the code is not in the dictionary, report as unresolved and leave ARMCD empty with a LOW confidence mapping in provenance
- Do not retain numeric codes without decoding interpretation

### 4.3 Screen Failure and Other Special Codes

If a trial includes subjects with special status codes (e.g., "SCREEN FAILURE", "DROPOUT", "INELIGIBLE"):
- These are valid ARMCD values if they represent assignment status rather than treatment
- Include them in the ARMCD set with notation in provenance.arm_special_status = true
- Ensure these subjects are also marked appropriately in other DM data elements

### 4.4 Case Normalization

ARMCD codes are case-sensitive in many systems. Normalize all codes to uppercase for consistency:
- "pbo" → "PBO"
- "Placebo" → "PBO" (if decoded from ARM text; generally not done)
- "arm1" → "ARM1"

### 4.5 Empty ARMCD is Valid

If the source dataset has ARM but no ARMCD column:
- ARMCD is legitimately empty
- This is not a data quality issue; it is a completeness gap that may be resolved downstream by the SDTM team
- Do not attempt to derive ARMCD codes from ARM text without explicit study protocol guidance

---

## 5. Provenance Flags

In addition to standard provenance fields (system_rules.md):

| Field | Type | Description |
|-------|------|-------------|
| `armcd_source_column` | String | Name of the source column from which ARMCD was mapped |
| `armcd_decoded_from_numeric` | Boolean | True if ARMCD was decoded from a numeric code using a dictionary |
| `armcd_dictionary_used` | String | Name or reference of the codebook/dictionary used for decoding |
| `armcd_arm_consistency` | String | "consistent" if ARMCD:ARM mapping is 1:1, "inconsistent" if conflicts detected |
| `armcd_case_normalized` | Boolean | True if case was normalized to uppercase |
| `armcd_special_status` | Boolean | True if ARMCD represents special status (e.g., screen failure) rather than treatment assignment |

---

## 6. Validation Criteria *(SME review required for each study)*

### Conformance
- ARMCD should be a non-empty string if populated
- All values should be uppercase (or consistent with study convention)
- No leading/trailing whitespace
- No spaces within codes (compound codes use underscore or hyphen)

### Plausibility
- **Cardinality:** The number of distinct ARMCD values should match the number of distinct ARM values (1:1 mapping)
- **Consistency:** If a specific ARMCD appears in multiple records, it should always map to the same ARM text
- **Protocol alignment:** The set of ARMCD codes should match the trial protocol's treatment arms (typically 2-4 for randomized trials, 1 for observational)

### Determinism
- Within a single source dataset, the same source value must always map to the same target ARMCD (after normalization)
- If numeric codes are being decoded, the same code must always decode to the same ARMCD

---

## 7. Known Limitations

1. **No study-wide ARMCD codelist exists in the prototype data.** Each sponsor has its own codes (e.g., AZ_229: TRTCODE, Amgen_265: TRTCD, EMD_221: ARMCD). Mapping requires study-specific data dictionaries that may not always be available.

2. **Amgen_265 and AZ_229 have numeric ARMCD sources (TRTCD, TRTCODE).** Without the accompanying codebook, these cannot be decoded with HIGH confidence. SME input is needed to map numeric codes to their descriptions.

3. **Lilly_568 ARMCD derivation is not detailed in the data extraction.** If multi-arm codes exist, they should be explicitly identified and validated against the study protocol.

4. **ARMCD:ARM consistency across all 7 sponsors has not been validated.** Each dataset should be audited to ensure 1:1 mapping when both variables are present.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial spec; documented numeric code decoding, empty ARMCD validity, and pairing rules with ARM |
