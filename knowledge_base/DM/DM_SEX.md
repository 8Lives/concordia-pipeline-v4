# DM Variable Specification: SEX

**Variable:** SEX
**Domain:** Demographics (DM)
**Order:** 3
**Required:** Yes
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The biological sex of the subject as recorded or inferred from the source data. This variable captures chromosomal/anatomical sex, not gender identity or gender expression. Where the source conflates sex and gender (common in EHR and claims data), the value should be mapped as-is with the `sex_gender_conflated` provenance flag set.

**SDTM Reference:** DM.SEX — CDISC Controlled Terminology codelist C66731

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.SEX | C66731 |
| HL7 FHIR | AdministrativeSex value set | male, female, other, unknown |
| OMOP CDM | gender_concept_id (Person table) | 8507 (M), 8532 (F) |

**Note:** OMOP uses `gender_concept_id` but the intent in most implementations is biological sex. Our harmonized variable aligns with the biological sex interpretation.

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | CDISC CT Code |
|-------|-----------|---------------|
| Male | Male sex | C20197 |
| Female | Female sex | C16576 |
| Unknown | Source value was missing, ambiguous, or explicitly recorded as unknown | C17998 |
| Undifferentiated | Source explicitly records an intersex or non-binary biological designation, or the value cannot be resolved to Male or Female without clinical adjudication | C45908 |

**Source Priority List:** SEX, SEXCD, GENDER, GENDERCD, SEXC, SEX_CODE

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Dictionary Decode |
|---------|--------------|-------------|-------------------|
| AZ_205 | *(not present)* | — | No SEX variable in dataset |
| AZ_229 | SEX | "1" (n=266) | $SEX format: 1=Male, 2=Female |
| Amgen_265 | SEX / SEXCD | "Male" (n=387), "Female" (n=133) / 1, 2 | Both decoded and coded present |
| EMD_221 | SEX | Numeric codes | Format-dependent |
| Lilly_568 | SEX | TBD | TBD |
| Merck_188 | SEX | Numeric codes | Format-dependent |
| Pfizer_374 | *(not present)* | — | Only AGE in this DM extract |
| Sanofi_323 | SEX | "Male" (n=211), "Female" (n=71) | Pre-decoded |

---

## 3. Mapping Decision Principles

1. **Prefer explicit mappings over inference.** If the source has a field labeled "sex" or "biological sex" with coded values, decode via dictionary and map directly. Do not infer sex from names, titles (Mr./Mrs.), pronouns, or diagnosis codes.

2. **Do not resolve ambiguity by guessing.** If a source value could mean either Male or Female (e.g., corrupted code), map to Unknown rather than picking one.

3. **Flag conflation, don't correct it.** If the source field is labeled "gender" but contains values like "Male"/"Female" that function as biological sex proxies (the majority of clinical trial and EHR data), map the values and set `sex_gender_conflated = true`.

4. **Preserve the distinction between Unknown and Undifferentiated.** If the source distinguishes "Unknown" (not collected) from "Other/Intersex" (collected, not Male or Female), map accordingly. If the source lumps them, map to Unknown and note the loss of granularity in provenance.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "Male", "male", "MALE", "M", "m" | Male | HIGH | Direct match or standard abbreviation |
| "Female", "female", "FEMALE", "F", "f" | Female | HIGH | Direct match or standard abbreviation |
| 1 (with dictionary: 1=Male) | Male | HIGH | Code decode |
| 2 (with dictionary: 2=Female) | Female | HIGH | Code decode |
| 1 (no dictionary, context suggests sex) | Male | LOW | Convention-based inference |
| "Other", "Non-binary" | Undifferentiated | MEDIUM | Contextual mapping |
| "Prefer not to say", "Not Reported" | Unknown | HIGH | Explicit non-disclosure |
| NULL, "", "N/A", ".", "9", "99" | Unknown | HIGH | Standard missing codes |
| "Masculino", "Femenino" | Male / Female | MEDIUM | Non-English synonym |

---

## 4. Variable-Specific Business Rules

### 4.1 Longitudinal Conflict Resolution

When multiple records for the same subject contain conflicting sex values:
1. If one value is Unknown and the other is Male or Female, prefer the non-unknown value.
2. If values conflict between Male and Female, flag for manual review. Set value to Unknown with `sex_conflict = true`.
3. If the source provides a "most recent" or "verified" indicator, prefer that record.

### 4.2 All-Same-Value Datasets

Some clinical trials are sex-specific (e.g., prostate cancer = all male, ovarian cancer = all female). If the harmonized SEX column contains only one value for the entire dataset, this is expected and should NOT be flagged as an error. The data extraction confirmed AZ_229 (prostate cancer) is 100% Male.

---

## 5. Provenance Flags

In addition to the standard provenance fields defined in system_rules.md:

| Field | Type | Description |
|-------|------|-------------|
| `sex_gender_conflated` | Boolean | True if the source field was labeled "gender" or otherwise conflated sex and gender |
| `sex_conflict` | Boolean | True if longitudinal records had conflicting sex values |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All values must be in the allowed value set: {Male, Female, Unknown, Undifferentiated}

### Plausibility
- Distribution of Male/Female should generally be between 30/70 and 70/30 for most disease populations. **Exception:** Sex-specific diseases (prostate, ovarian, cervical cancers) will be 100% one sex. The stoplight system should not penalize this.
- Unknown should be < 5% for clinical trial data. For RWD, a higher threshold may apply.
- Undifferentiated is expected to be < 1%. Higher rates may indicate "Unknown" values were incorrectly mapped to Undifferentiated.

### Determinism
- Within a single source dataset, the same source value must always map to the same target value.

---

## 7. Known Limitations

1. **Sex vs. gender conflation is pervasive.** Most clinical trial and EHR systems use a single field for both concepts. The `sex_gender_conflated` provenance flag mitigates this but cannot resolve it.
2. **AZ_205 has no SEX variable at all.** This dataset will produce SEX = Unknown for all records with confidence = UNMAPPED.
3. **Pfizer_374 DM extract contains only AGE.** SEX will be Unknown for all records.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (standalone format) |
| 2.0 | 2026-04-08 | Revised for three-tier hierarchy; removed system/domain-level content; added prototype data observations; marked SME review points |
