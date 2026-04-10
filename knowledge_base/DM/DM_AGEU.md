# DM Variable Specification: AGEU

**Variable:** AGEU
**Domain:** Demographics (DM)
**Order:** 6
**Required:** Conditional (required when AGE is populated)
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The unit of measurement for the subject's age. In adult clinical trials, this is almost always "Years". Units such as "Months" or "Days" appear only in pediatric or neonatal populations.

**SDTM Reference:** DM.AGEU — CDISC Controlled Terminology codelist C66781

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.AGEU | C66781 (AGEU codelist) |

**Note:** AGEU is optional per SDTM but becomes conditionally required when AGE is populated per DM_domain_rules.md Section 4.1.

---

## 2. Allowed Values

| Value | Definition | CDISC CT Code |
|-------|-----------|---------------|
| Years | Age measured in calendar years | C29848 |
| Months | Age measured in calendar months (pediatric populations) | C29849 |
| Days | Age measured in calendar days (neonatal populations) | C29850 |
| Unknown | Source value was missing or could not be determined | C17998 |

**Source Priority List:** AGEU, AGE_UNITS, AGEUNITS, AGEUCD

**Observed Source Patterns (from data extraction):**

| Sponsor | Source Column | Values Found | Notes |
|---------|--------------|-------------|-------|
| EMD_221 | AGEU | "YEARS" (207, 75.8%), blank (66, 24.2%) | Mixed presence; case normalized |
| Lilly_568 | AGEU | "Years" (130, 100.0%) | All populated, title case |
| Merck_188 | AGEU | "YEARS" (507, 100.0%) | All populated, uppercase |
| AZ_229 | — | *(not present)* | AGE present; AGEU absent |
| Amgen_265 | — | *(not present)* | AGE present; AGEU absent |
| Others | — | *(not applicable)* | No AGE variable or data not provided |

---

## 3. Mapping Decision Principles

1. **Prefer explicit source AGEU.** If the source dataset contains an AGEU or equivalent column, decode and map directly.

2. **Default to "Years" when AGE is present but AGEU is absent.** Adult clinical trial populations almost exclusively use years. This is a safe and well-justified default for this data domain.

3. **Assign confidence appropriately.**
   - HIGH: Source AGEU present and explicitly "Years" / "YEARS" / "Months" / "Days"
   - MEDIUM: Source AGE present, AGEU absent, defaulted to "Years"
   - LOW: Inferred from context (e.g., if BRTHDTC is present with year precision only, infer "Years" with LOW confidence)

4. **Do not infer units from age values.** Even if all ages in the source are < 24, do not assume "Months". Rely on explicit source data or apply the "Years" default.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "Years", "YEARS", "years" | Years | HIGH | Direct match, case-normalized |
| "Months", "MONTHS" | Months | HIGH | Direct match, pediatric context |
| "Days", "DAYS" | Days | HIGH | Direct match, neonatal context |
| NULL, "", "N/A" (AGE is present) | Years | MEDIUM | Default for adult trials |
| NULL, "", "N/A" (AGE is absent) | Unknown | HIGH | No age unit to assign |

---

## 4. Variable-Specific Business Rules

### 4.1 Conditional Requirement

AGEU is required when and only when AGE is populated (DM_domain_rules.md Section 4.1). This creates a logical pair:
- If AGE is present → AGEU must also be populated
- If AGE is absent → AGEU should be absent (or explicitly "Unknown" if needed)

### 4.2 Adult vs. Pediatric/Neonatal Populations

- **Adult trials (expected age range 18-100 years):** AGEU = "Years" (default and expected value)
- **Pediatric trials (age < 18):** AGEU may be "Years", "Months", or "Days" depending on the trial design
- **Neonatal trials (age < 1 year):** AGEU may be "Months" or "Days"

If the dataset contains age values that suggest pediatric or neonatal population (e.g., AGE values < 18) but AGEU = "Years", flag for manual review with a NOTE: age-units-mismatch. Do not auto-correct.

### 4.3 Case and Whitespace Normalization

Normalize source values to title case for consistency:
- "YEARS" → "Years"
- "years" → "Years"
- "MONTHS" → "Months"
- "days" → "Days"

Apply system whitespace rules (see system_rules.md): strip leading/trailing whitespace, collapse internal whitespace to single spaces.

---

## 5. Provenance Flags

In addition to standard provenance fields (system_rules.md):

| Field | Type | Description |
|-------|------|-------------|
| `ageu_source` | String | Source column name from which AGEU was mapped |
| `ageu_default` | Boolean | True if AGEU was defaulted to "Years" due to missing source value when AGE was present |
| `age_units_mismatch` | Boolean | True if AGEU suggests one unit (e.g., "Months") but AGE values suggest another (e.g., all > 18 years) |

---

## 6. Validation Criteria *(SME review required for pediatric thresholds)*

### Conformance
- All values must be in the allowed value set: {Years, Months, Days, Unknown}
- Case and whitespace normalized per Section 4.3

### Plausibility
- **In adult trial populations (expected):** AGEU = "Years" should account for ≥ 99% of records
- **In pediatric populations:** AGEU = "Years" is still acceptable; "Months" or "Days" indicates higher precision de-identification or specialized pediatric trial
- **Cross-check with AGE:**
  - If AGE is present, AGEU must be populated (not missing/Unknown)
  - If all AGE values are > 18, AGEU should be "Years" (or flag mismatch)
  - If any AGE values are < 1 (fractional, e.g., 0.5), AGEU should be "Years" with fractional year convention or flag for review

### Determinism
- Within a single source dataset, the same source value must always map to the same target value
- If a dataset has mixed case AGEU values (e.g., "Years" and "YEARS"), all must normalize to "Years"

---

## 7. Known Limitations

1. **EMD_221 has 24.2% blank AGEU values despite AGE being present.** These are defaulted to "Years" with confidence = MEDIUM. SME review of EMD_221 is recommended to confirm this is appropriate for the trial population.

2. **Lack of pediatric/neonatal trials in the prototype data.** This spec is designed for adult populations. If pediatric or neonatal data is encountered, the mapping logic should be reviewed with the study team.

3. **AGEU is optional in SDTM but conditionally required here.** This represents a domain-level tightening of the standard to ensure data integrity when AGE is present.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial spec; integrated data extraction patterns; marked SME review for pediatric logic |
