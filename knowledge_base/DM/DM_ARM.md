# DM Variable Specification: ARM

**Variable:** ARM
**Domain:** Demographics (DM)
**Order:** 14
**Required:** Optional
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** A human-readable description of the treatment arm to which the subject was assigned or randomized. This is the label or long-form name for the arm, not the code. ARM provides the narrative label that appears in clinical trial reports and subject-facing documentation.

**SDTM Reference:** DM.ARM — CDISC SDTM DM domain

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.ARM | Treatment arm description |
| Protocol Coding | Randomization tables | Assigned treatment arm labels |

---

## 2. Allowed Values

ARM is a free-text string variable and does not use a fixed CDISC controlled terminology codelist. The set of allowed values is study-specific and derives from the trial's approved treatment arms. Common patterns include:

| Pattern | Example | Notes |
|---------|---------|-------|
| Drug + dose | "Treatment 100 mg", "Active Drug 50 mg BID" | Dosage detail included in ARM |
| Drug name only | "Placebo", "Active Comparator" | Generic arm labels |
| Comparison description | "Treatment A vs. Standard of Care" | Comparative language |
| Study-specific codes | "Arm A", "Arm B", "Control" | Abbreviated labels |

**Source Priority List:** ARM, TRT, TRTLONG, TRTSHORT, TREATMENT, ACTTRT, ACTTRTXT, ARMDESC

**Observed Source Patterns (from data extraction):**

| Sponsor | Source Columns | Values Found | Notes |
|---------|---|---|---|
| AZ_229 | TRTSHORT | "Placebo" (266, 100%) | Single arm; numeric code 1 in SEX suggests prostate cancer trial |
| Amgen_265 | TRT | "Panit. plus chemotherapy" (260, 50%), "Chemotherapy" (260, 50%) | Two-arm trial; abbreviation in full text |
| EMD_221 | ARM (direct) | "CONTROL GROUP" (273, 100%) | Pre-decoded, single-arm control |
| Lilly_568 | ARM (direct) | "LY2510924 Carboplatin/Etoposide(Arm A)" (48), "Carboplatin/Etoposide(Arm B)" (46), "SCREEN FAILURE" (36) | Multi-arm + screening failure classification |
| Merck_188 | ARM (direct) | "Placebo" (507, 100%) | Single-arm trial |
| AZ_205, Pfizer_374, Sanofi_323 | — | *(not available)* | No treatment arm variables in extracted data |

---

## 3. Mapping Decision Principles

1. **Prefer the most decoded/descriptive source.** If multiple treatment-related columns exist (e.g., TRTCD and TRTLONG), prefer the decoded/long-form version. Per DM_domain_rules.md Section 6, prefer the randomized/assigned treatment for the DM record.

2. **Normalize text: apply mixed case and expand abbreviations.**
   - Normalize to title case: "PLACEBO" → "Placebo", "placebo" → "Placebo"
   - Expand known abbreviations: "PBO" → "Placebo", "Panit." → "Panitumumab"
   - Preserve study-specific names (e.g., drug names, "Carboplatin/Etoposide" as-is)
   - Remove dosage-only text if redundant with other variables (e.g., if both ARM and a DOSE variable exist, remove dose from ARM)

3. **Handle multi-arm and screen-failure cases.** If the source includes "SCREEN FAILURE" or equivalent status values, include them as valid ARM values (subjects who screen-failed are valid DM records with assignment status = screening).

4. **Assign confidence based on source clarity.**
   - HIGH: Source has explicit ARM, TRTLONG, or TREATMENT column with clear decoded text
   - MEDIUM: Source has abbreviated text (TRT, TRTSHORT) that requires expansion
   - LOW: Source has only code (TRTCD, TRTNUM) and ARM is derived from a code table

5. **If only ARMCD is available, leave ARM empty.** Do not attempt to expand codes to text without a data dictionary.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "Placebo", "PLACEBO" | Placebo | HIGH | Direct match, case-normalized |
| "PBO", "Pbo" | Placebo | MEDIUM | Abbreviation expanded per standard convention |
| "Panitumumab plus chemotherapy" | Panitumumab plus chemotherapy | HIGH | Pre-decoded, case-normalized |
| "Panit. plus chemotherapy" | Panitumumab plus chemotherapy | MEDIUM | Abbreviation expanded |
| "CONTROL GROUP" | Control Group | HIGH | Case-normalized |
| "LY2510924 Carboplatin/Etoposide(Arm A)" | LY2510924 Carboplatin/Etoposide (Arm A) | HIGH | Pre-decoded, whitespace normalized |
| "SCREEN FAILURE" | Screen Failure | HIGH | Valid status, case-normalized |
| 1 (code, no dictionary) | — | — | ARMCD mapping; ARM left empty |

---

## 4. Variable-Specific Business Rules

### 4.1 Assignment vs. Actual Treatment

When the source dataset contains both assigned (randomized) and actual (received) treatment variables (e.g., ACTTRT vs. ARM):
- Prefer assigned treatment for the DM record
- Document the choice in provenance.treatment_type = "assigned" or "actual"
- If they differ, note the mismatch in a QC flag

### 4.2 Dosage Information

If the source ARM text includes dosage (e.g., "Treatment 100 mg BID") and a separate DOSE variable exists:
- Retain dosage in ARM if it is integral to the arm definition (e.g., "100 mg vs. 50 mg" is the design)
- Remove redundant dosage if ARM is a generic label and dosage is captured separately elsewhere (use domain context to decide)

### 4.3 Abbreviation Expansion

Common clinical trial abbreviations to expand (per system_rules.md text normalization):

| Abbreviation | Expansion |
|---|---|
| PBO | Placebo |
| QD | Once daily |
| BID | Twice daily |
| TID | Three times daily |
| QID | Four times daily |
| Panit. | Panitumumab |
| w/ | with |
| vs. | versus |
| HR | Human recombinant |

### 4.4 Screen Failure Status

Subjects who do not meet inclusion/exclusion criteria after enrollment but before randomization are recorded in DM with:
- ARM = "Screen Failure" or equivalent
- ARMCD = "SF" or equivalent
- This is a valid status for DM; do not filter these records out

### 4.5 Single-Arm and Observational Studies

In single-arm or observational cohorts:
- ARM may be uniform (all subjects have the same value, e.g., "Active treatment")
- This is expected and should not be flagged as an error
- Verify with the study team that the cohort is indeed single-arm

---

## 5. Provenance Flags

In addition to standard provenance fields (system_rules.md):

| Field | Type | Description |
|-------|------|-------------|
| `arm_source_column` | String | Name of the source column from which ARM was mapped |
| `arm_assigned_actual` | String | "assigned" if ARM represents randomized treatment, "actual" if received treatment, "unknown" if cannot determine |
| `arm_abbreviation_expanded` | Boolean | True if abbreviations were expanded (e.g., "PBO" → "Placebo") |
| `arm_dosage_retained` | Boolean | True if dosage information is retained in the ARM text |
| `arm_case_normalized` | Boolean | True if case was normalized (not unusual; expected behavior) |

---

## 6. Validation Criteria *(SME review required for each study)*

### Conformance
- ARM should be a non-empty string if populated
- All whitespace normalized per system_rules.md
- No leading/trailing whitespace

### Plausibility
- **Uniqueness:** Within a trial, the set of distinct ARM values should match the trial protocol's approved treatment arms (typically 2-4 distinct values for a randomized trial, 1 for observational)
- **Consistency across ARMCD:** If both ARM and ARMCD are present, the 1:1 mapping should be consistent (same ARMCD always maps to the same ARM)
- **Screen Failure handling:** If "Screen Failure" or equivalent appears in ARM, verify these subjects are also marked as screen failures in other data elements (if available)

### Determinism
- Within a single source dataset, the same source value must always map to the same target value (after normalization)

---

## 7. Known Limitations

1. **No single ARM value set across sponsors.** Each study defines its own treatment arms. This spec provides guidance for consistent mapping but cannot enforce a unified controlled terminology.

2. **Abbreviations are context-dependent.** "Panit." in Amgen_265 is expanded to "Panitumumab" based on pharmaceutical knowledge. If other abbreviations are encountered that are not in the standard expansion list, they should be flagged for manual review.

3. **Lilly_568 includes "SCREEN FAILURE" as a status value.** This is valid for DM but may require filtering in downstream efficacy analysis. Document this in the transformation report.

4. **AZ_205, Pfizer_374, Sanofi_323 lack treatment arm data entirely.** These datasets cannot be populated with ARM and should be flagged as incomplete for clinical trial analysis.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial spec; integrated data extraction patterns; documented abbreviation expansion and assignment vs. actual treatment logic |
