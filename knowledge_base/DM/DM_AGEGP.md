# DM Variable Specification: AGEGP

**Variable:** AGEGP
**Domain:** Demographics (DM)
**Order:** 7
**Required:** Conditional (used only when AGE is not available; see DM_domain_rules.md Section 4.1)
**Version:** 1.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** A categorical representation of the subject's age group. This variable is a fallback for when continuous AGE is not available (typically due to de-identification). It preserves whatever categorical age information the source provides.

**SDTM Reference:** Not a standard SDTM DM variable. SDTM uses AGE (continuous) and AGEU. Age groups in SDTM are typically handled as supplemental qualifiers or in analysis datasets (ADSL.AGEGR1). Concordia includes AGEGP in the DM schema to avoid losing age information from de-identified datasets.

**Relationship to AGE:** AGEGP is populated only when AGE is empty. If continuous AGE is present, AGEGP should be empty even if the source also provides a categorical age group. See DM_domain_rules.md Section 4.1.

---

## 2. Allowed Values *(SME review required)*

AGEGP is a **free-form string** that preserves the source's categorical encoding. Unlike other DM variables, there is no fixed enumerated value set because age group definitions vary by study and sponsor.

| Property | Value |
|----------|-------|
| Data type | String |
| Fixed value set | No — preserves source categories |
| Missing value | Empty (when AGE is populated instead, or when no age data exists) |

**Common patterns observed in prototype data:**

| Sponsor | Source Column | Categories |
|---------|-------------|------------|
| AZ_205 | agegrp | "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80-84", "85-89", ">=90" |
| AZ_229 | AGEGRP | "18-64 Years", "65-74 Years", ">=75 Years" |
| AZ_229 | AGEGP | ">=45<60", ">=60<65", ">=65<70", ">=70<75", ">=75<80", ">=80<100" |
| Amgen_265 | AGECAT | (present alongside continuous AGE — would not populate AGEGP) |

**Source Priority List:** AGEGP, AGEGRP, AGECAT, AGECATCD, AGE_GROUP, AGEBAND

---

## 3. Mapping Decision Principles

1. **Preserve the source representation.** Do not reformat, re-bin, or re-categorize age groups. If the source says "65-69", store "65-69". If the source says ">=75 Years", store ">=75 Years". The downstream analyst can re-categorize as needed.

2. **Prefer the most granular category.** If the source provides multiple age group columns at different granularities (e.g., AZ_229 has both AGEGRP with 3 categories and AGEGP with 6 categories), use the more granular one.

3. **Normalize formatting minimally.** Apply mixed case per system rules. Preserve comparison operators (>=, <, ≥, ≤) and range delimiters (-, to). Standardize "yrs" / "yr" / "years" to "Years" if a unit is appended.

4. **Do not convert to numeric AGE.** Never compute a midpoint or representative value from a categorical range. Categorical age data stays categorical.

5. **Skip if AGE is available.** If the source provides both continuous AGE and categorical age groups, map AGE (the continuous variable) and leave AGEGP empty. The categorical version adds no information when the continuous version exists.

---

## 4. Variable-Specific Business Rules

### 4.1 Multiple Age Group Columns

When the source contains multiple age group columns (common in AstraZeneca datasets):
- Check if continuous AGE is also present → if yes, skip AGEGP entirely
- If no continuous AGE, select the most granular age group column
- Document the choice in provenance, including which columns were available

### 4.2 Coded Age Groups

Some sources encode age groups as numeric codes (e.g., AGECATCD = 1, 2, 3). Decode using the data dictionary before populating AGEGP. The harmonized value should be the human-readable category, not the code.

---

## 5. Provenance Flags

In addition to the standard provenance fields:

| Field | Type | Description |
|-------|------|-------------|
| `agegp_source_granularity` | String | When multiple age group columns exist, records which was selected and why |

---

## 6. Validation Criteria

### Conformance
- AGEGP should be a non-empty string when populated
- AGEGP should not contain numeric-only values (that would suggest a continuous AGE was incorrectly placed here)

### Mutual Exclusivity with AGE
- If AGE is populated (non-empty), AGEGP should be empty
- If both are populated, log a warning (not a failure — the data is usable, but the convention is violated)

### Plausibility
- Age group labels should be parseable as age ranges (e.g., contain numbers, range delimiters)
- Categories should span a plausible range (e.g., not "0-5" in an adult oncology trial)

---

## 7. Known Limitations

1. **No standardized value set.** Age group categories are study-specific. Cross-study comparisons on AGEGP require re-categorization by the downstream analyst.
2. **Loss of precision.** AGEGP represents a known loss of precision from de-identification. A 67-year-old subject in the "65-69" band cannot be distinguished from a 65-year-old. This is irreversible.
3. **Inconsistent formatting.** Sources use varying formats: "65-69", "65 to 69", ">=65 <70", "65-69 Years". Minimal normalization is applied to preserve source intent.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial draft in three-tier format |
