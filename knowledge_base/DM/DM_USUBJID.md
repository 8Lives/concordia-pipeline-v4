# DM Variable Specification: USUBJID

**Variable:** USUBJID
**Domain:** Demographics (DM)
**Order:** 12
**Required:** Optional
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** Unique Subject IDentifier — a concatenated identifier that uniquely identifies a subject across all trials in the harmonized dataset. If a source dataset explicitly provides USUBJID, use it. If not, derive USUBJID by concatenating TRIAL + "-" + SUBJID per DM_domain_rules.md Section 4.3. This variable enables subject-level tracking across multi-trial analyses.

**SDTM Reference:** DM.USUBJID — CDISC standard unique subject identifier (concatenated study + subject IDs)

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.USUBJID | Unique subject ID across studies; format typically STUDYID-SUBJID |
| HL7 FHIR | Patient.identifier | Patient ID with assigning authority |

**Note:** USUBJID is derived (usually) but still documented as a standard variable. The derivation rule is defined in DM_domain_rules.md and is immutable across all variable specs.

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | Notes |
|-------|-----------|-------|
| Explicit USUBJID | Source dataset provides a USUBJID column | Use as-is if validation passes |
| Derived format: TRIAL-SUBJID | Concatenation of NCT ID and subject ID (e.g., "NCT00673205-183") | Use when source does not provide USUBJID |
| Derived format: STUDYID-SUBJID | Alternative concatenation using sponsor protocol ID (e.g., "CASO0024-183") | Only if TRIAL cannot be reliably extracted; document fallback |
| Unknown | No valid combination of TRIAL and SUBJID available for derivation | confidence = UNMAPPED |

**Source Priority List:** USUBJID, UNIQUESUBJECTID

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Format | Notes |
|---------|--------------|-------------|--------|-------|
| AZ_205 | (not present) | Derive as NCT00673205-{trials_d} | N/A | Must derive; no explicit USUBJID |
| AZ_229 | (not present) | Derive as NCT00554229-{SUBJ} | N/A | Must derive; no explicit USUBJID |
| Amgen_265 | (not present) | Derive as NCT00460265-{SUBJID} | N/A | Must derive; no explicit USUBJID |
| EMD_221 | USUBJID | Numeric (1, 175-187) | explicit | Explicit USUBJID present; validate against TRIAL+SUBJID |
| Lilly_568 | USUBJID | "I2V-MC-CXAC-9000-0007" | explicit | Explicit USUBJID in STUDYID-SITEID-SUBJID format |
| Merck_188 | USUBJID | Numeric (1, 336-348) | explicit | Explicit USUBJID present; validate against TRIAL+SUBJID |
| Pfizer_374 | (not available) | — | — | No SUBJID or USUBJID available |
| Sanofi_323 | (not available) | — | — | No SUBJID or USUBJID available |

---

## 3. Mapping Decision Principles

1. **Prefer explicit USUBJID if available and valid.** If the source provides USUBJID, use it directly (confidence = HIGH) provided it is non-empty and non-null.

2. **Derive USUBJID from TRIAL + "-" + SUBJID if not present.** This is the standard derivation rule per DM_domain_rules.md Section 4.3. Concatenate with a hyphen separator.

3. **Validate explicit USUBJID against derived format.** If source provides USUBJID, verify it matches the expected format (either NCT-based or STUDYID-based). If format deviates, flag for review.

4. **Do not attempt reverse-engineering of USUBJID.** If USUBJID is present but TRIAL and SUBJID are not, do not attempt to parse the USUBJID to extract component IDs. Instead, flag as a data quality issue.

5. **Fallback to STUDYID-SUBJID if TRIAL extraction fails.** Only if TRIAL cannot be reliably extracted from the filename should derivation use STUDYID + "-" + SUBJID. This should be documented in provenance.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| Explicit USUBJID column: "NCT00673205-183" | NCT00673205-183 | HIGH | Use as-is; matches expected format |
| Explicit USUBJID column: "I2V-MC-CXAC-9000-0007" | I2V-MC-CXAC-9000-0007 | HIGH | Sponsor-specific multi-part format; acceptable |
| No USUBJID; TRIAL="NCT00673205", SUBJID="183" | NCT00673205-183 | HIGH | Derivation per domain rules |
| No USUBJID; no TRIAL; STUDYID="CASO0024", SUBJID="183" | CASO0024-183 | MEDIUM | Fallback derivation; document in provenance |
| NULL, "", "N/A" | Unknown | UNMAPPED | Missing USUBJID and cannot derive |

---

## 4. Variable-Specific Business Rules

### 4.1 Derivation Rule (Immutable)

Per DM_domain_rules.md Section 4.3:
```
IF USUBJID IS NOT NULL AND USUBJID != ""
  THEN use USUBJID as-is
ELSE IF TRIAL IS NOT NULL AND SUBJID IS NOT NULL
  THEN USUBJID := TRIAL + "-" + SUBJID
ELSE IF STUDYID IS NOT NULL AND SUBJID IS NOT NULL
  THEN USUBJID := STUDYID + "-" + SUBJID
ELSE
  USUBJID := "Unknown"
END
```

### 4.2 Uniqueness Constraint

USUBJID must be unique across the entire harmonized dataset:
- No two records (regardless of TRIAL) may have the same USUBJID
- If duplicates are detected after derivation, this indicates:
  - A subject enrolled in multiple trials (expected; TRIAL differs)
  - A data merge error (same TRIAL + SUBJID appearing twice — error)
- Flag duplicates for manual review

### 4.3 Validation Against Components

If USUBJID is explicit:
1. Extract the component parts (split on hyphen)
2. Validate that TRIAL (or STUDYID) and SUBJID match the corresponding columns
3. If mismatch occurs, flag with `usubjid_component_mismatch = true`

---

## 5. Provenance Flags

In addition to the standard provenance fields defined in system_rules.md:

| Field | Type | Description |
|-------|------|-------------|
| `usubjid_source` | String | Source of USUBJID: "explicit", "derived_trial", "derived_studyid" |
| `usubjid_component_mismatch` | Boolean | True if explicit USUBJID's components do not match TRIAL/SUBJID or STUDYID/SUBJID |
| `usubjid_derivation_separator` | String | Separator used in derivation: "-" (standard), or alternate if required |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All USUBJID values must be non-empty strings or "Unknown"
- No NULL or blank values (use "Unknown" instead)
- Format should be either:
  - NCT\d{8}-{SUBJID} (NCT-based derivation)
  - {STUDYID}-{SUBJID} (STUDYID-based fallback)
  - Explicit source format (if provider-specific)

### Plausibility
- USUBJID must be globally unique (across all trials in the harmonized dataset)
- Same TRIAL + SUBJID must always map to same USUBJID (determinism)
- Component extraction should match source TRIAL/STUDYID and SUBJID columns

### Determinism
- Repeated extraction must yield identical USUBJID values
- Derivation logic must be applied consistently across all records

---

## 7. Known Limitations

1. **Derivation depends on successful TRIAL extraction.** If TRIAL cannot be extracted from filename (all 8 sponsors), fallback to STUDYID-based derivation. This may create inconsistency if some datasets use TRIAL and others use STUDYID. *(SME review required)*
2. **Lilly's USUBJID format includes SITEID.** The explicit USUBJID "I2V-MC-CXAC-9000-0007" includes site (9000) and subject (0007) as separate components. This deviates from the standard two-component format. Validation logic must account for this.
3. **EMD and Merck USUBJID appear numeric.** Numeric-only USUBJID values (e.g., "1", "175") suggest either:
   - De-identified sequential numbering (not traceable to source IDs)
   - Incomplete extraction (TRIAL/SUBJID may be absent in the original source)
   - Validation and component matching will fail. *(SME review required)*
4. **Pfizer and Sanofi cannot derive USUBJID.** Both datasets lack SUBJID and explicit USUBJID; all records will be Unknown.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (standalone format) |
| 2.0 | 2026-04-08 | Revised for three-tier hierarchy; added immutable derivation rule reference; documented observed patterns (explicit USUBJID in EMD/Merck, multi-part format in Lilly); marked SME review points for numeric USUBJID and STUDYID fallback |
