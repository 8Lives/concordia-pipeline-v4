# DM Variable Specification: RACE

**Variable:** RACE
**Domain:** Demographics (DM)
**Order:** 4
**Required:** Yes
**Version:** 2.0
**Last Updated:** 2026-04-08
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The self-reported or administratively recorded racial category of the subject, aligned to the OMB revised standards (1997) as adopted by FDA and NIH. Where the source provides more granular categories (e.g., Census detailed race, UK ONS categories), values are rolled up to OMB categories with the granular value preserved in provenance.

**SDTM Reference:** DM.RACE — CDISC Controlled Terminology codelist C74457

**Related Standards:**

| Standard | Concept | Reference |
|----------|---------|-----------|
| CDISC SDTM | DM.RACE | C74457 |
| OMB (1997 Revised) | 5 minimum race categories | Federal Register 62 FR 58782 |
| HL7 FHIR | us-core-race extension | OMB categories + detailed |
| OMOP CDM | race_concept_id (Person table) | Mapped to OMB |

**Critical distinction:** Race and ethnicity are independent variables per OMB standards. The separation logic for combined race/ethnicity fields is defined in this spec (Section 3) and the ETHNICITY spec. Cross-variable validation is in DM_domain_rules.md Section 4.2.

---

## 2. Allowed Values *(SME review required)*

| Value | Definition | CDISC CT Code |
|-------|-----------|---------------|
| White | Origins in Europe, Middle East, or North Africa | C41261 |
| Black or African American | Origins in any of the Black racial groups of Africa | C16352 |
| Asian | Origins in the Far East, Southeast Asia, or the Indian subcontinent | C41260 |
| American Indian or Alaska Native | Origins in any of the original peoples of North and South America, maintaining tribal affiliation or community attachment | C41259 |
| Native Hawaiian or Other Pacific Islander | Origins in Hawaii, Guam, Samoa, or other Pacific Islands | C41219 |
| Multiple | Subject reported or was recorded as more than one race | C67236 |
| Unknown | Missing, refused, not collected, or not interpretable | C17998 |

**Design Decision — No "Other" category:** OMB does not include "Other" as a standard race category. Source values of "Other" should be resolved to a specific OMB category using accompanying free-text or documentation, or mapped to Unknown.

**Source Priority List:** RACE, RACECD, RACEN, RACESC, ORIGIN, RACE_CODE

**Observed Source Patterns (from prototype data):**

| Sponsor | Source Column | Values Found | Dictionary Decode |
|---------|--------------|-------------|-------------------|
| AZ_205 | ORIGIN | 1.0 (n=1709), 4.0 (n=34), 6.0 (n=32), 2.0 (n=13), 3.0 (n=9), 7.0 (n=7), 5.0 (n=1) | 1=Caucasian, 2=Afro-Caribbean, 3=Asian, 4=Hispanic, 5=Oriental, 6=Mixed, 7=Other |
| AZ_229 | RACE | "11" (n=160), "13" (n=99), "99" (n=7) | 11=White, 13=Asian, 99=De-identified (collapsed categories) |
| Amgen_265 | RACE | Numeric codes (520 records) | Format-dependent |
| EMD_221 | RACE | Numeric codes | Format-dependent |
| Sanofi_323 | RACE | "Caucasian" (n=269), "Black" (n=6), "Asian" (n=4), "Hispanic" (n=2), "Other" (n=1) | Pre-decoded |

---

## 3. Mapping Decision Principles

### 3.1 Core Principles

1. **Separate race from ethnicity first.** Before mapping any values, determine whether the source combines race and ethnicity into a single field. If combined, apply the separation logic below before mapping to the RACE allowed values.

2. **Hispanic/Latino is ethnicity, not race.** If "Hispanic" appears as a race option, extract it to the ETHNICITY variable. Set RACE based on other available information, or to Unknown if no other race indicator exists.

3. **Roll up, don't invent.** Detailed categories (e.g., "Chinese," "Filipino," "Japanese") roll up to their OMB parent ("Asian"). Preserve the detailed value in `source_value_raw`. Never expand a general category into a specific one.

4. **"Other" is not a valid target.** Source values of "Other" must be resolved: check for an associated free-text field that maps to an OMB category. If unresolvable, map to Unknown.

5. **Multi-race requires explicit evidence.** Only map to "Multiple" when the source explicitly captures multiple race selections or uses a value like "Two or More Races."

6. **Do not infer race** from names, geographic origin, language preference, or country of birth.

### 3.2 Separation Logic for Combined Race/Ethnicity Fields

When the source has a single combined field:

| Source Value Pattern | RACE | ETHNICITY | Confidence |
|---------------------|------|-----------|------------|
| "Hispanic" or "Latino" (no race qualifier) | Unknown | Hispanic or Latino | MEDIUM |
| "White Hispanic" or "Non-Hispanic White" | White | Hispanic or Latino / Not Hispanic or Latino | MEDIUM |
| Race-only value (e.g., "Black", "Asian") | Map to OMB category | Unknown | MEDIUM |
| Ambiguous or uninterpretable | Unknown | Unknown | LOW |

### 3.3 Representative Mapping Patterns

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "White", "Caucasian" | White | HIGH | Standard synonym |
| "Black", "Black or African American", "Afro-Caribbean", "African American" | Black or African American | HIGH | Standard synonyms |
| "Asian", "Chinese", "Japanese", "Filipino", "Korean", "Indian" (South Asian context) | Asian | HIGH | Roll up to OMB parent |
| "Oriental" | Asian | MEDIUM | Outdated term, well-established mapping |
| "Native Hawaiian", "Samoan", "Guamanian" | Native Hawaiian or Other Pacific Islander | HIGH | Roll up to OMB |
| "American Indian", "Alaska Native", "Native American" | American Indian or Alaska Native | HIGH | Standard synonyms |
| "Hispanic" (in race field) | Unknown (extract to ETHNICITY) | MEDIUM | Not a race per OMB |
| "Mixed", "Two or More Races", "Multiracial" | Multiple | HIGH | Explicit multi-race |
| "Other" (no free-text) | Unknown | MEDIUM | Unresolvable without additional info |
| "Other" (with free-text "Lebanese") | White | MEDIUM | MENA classified as White per current OMB |
| Code "99" (de-identified) | Unknown | HIGH | Explicit de-identification |
| NULL, "", "Not Reported" | Unknown | HIGH | Standard missing |

### 3.4 AZ_205 ORIGIN Code 4 ("Hispanic")

This is a concrete example of the separation problem. AZ_205 uses ORIGIN code 4 = "Hispanic" as a race category. During harmonization:
- RACE → Unknown (Hispanic is not a race per OMB)
- ETHNICITY → Hispanic or Latino
- Set `race_ethnicity_conflated = true`

---

## 4. Variable-Specific Business Rules

### 4.1 Longitudinal Conflict Resolution

1. If one value is Unknown and the other is substantive, prefer the substantive value.
2. If a later record adds additional races, update to Multiple with both values in `race_source_detail`.
3. If values directly conflict (e.g., White vs. Asian), flag for review. Set to Unknown with `race_conflict = true`.

### 4.2 De-identified Race Data

Some datasets collapse race categories for de-identification (e.g., AZ_229 code 99 = collapsed categories). Map to Unknown with provenance documenting the de-identification. Do not attempt to infer the original race.

### 4.3 OMB MENA Classification

The 1997 OMB standards classify Middle Eastern and North African (MENA) populations as White. An OMB revision has been under review since 2023. This spec follows the current standard. If OMB finalizes a MENA category, this spec requires a version update.

---

## 5. Provenance Flags

In addition to the standard provenance fields:

| Field | Type | Description |
|-------|------|-------------|
| `race_ethnicity_conflated` | Boolean | True if the source combined race and ethnicity into a single field |
| `race_source_detail` | String/Array | For "Multiple": the individual race values. For roll-ups: the detailed source category. |
| `non_us_classification` | Boolean | True if the source used a non-US classification system (e.g., UK ONS) |
| `race_conflict` | Boolean | True if longitudinal records had conflicting values |

---

## 6. Validation Criteria *(SME review required for thresholds)*

### Conformance
- All values must be in the allowed value set (Section 2)

### Plausibility (US population benchmarks — adjust for study population)

| Category | Typical Range | Investigation Trigger |
|----------|--------------|----------------------|
| White | 40–80% | Outside range |
| Black or African American | 5–30% | Outside range |
| Asian | 2–15% | Outside range |
| American Indian or Alaska Native | 0–5% | > 10% |
| Native Hawaiian or Other Pacific Islander | 0–2% | > 5% |
| Multiple | 1–10% | > 15% (may indicate "Other" mis-mapped) |
| Unknown | 0–10% (trial), 0–25% (RWD) | Above thresholds |

### Separation Check
- If Unknown race > 40%, check whether "Hispanic" was treated as a race without extracting to ETHNICITY
- Verify that "Hispanic or Latino" ethnicity co-occurs with multiple race categories (see DM_domain_rules.md Section 4.2)

### Determinism
- Within a single source dataset, the same source value must always map to the same target value.

---

## 7. Known Limitations

1. **MENA classification is under OMB review.** Current spec maps MENA populations to White per the 1997 standard.
2. **De-identification data loss is unrecoverable.** AZ_229 codes 1, 4, 5, 6, 7 collapsed to 99 cannot be reversed.
3. **Multi-race granularity varies.** Some sources report "Two or More Races" without specifying which races. The detail is lost.
4. **AZ_205 ORIGIN code 4 ("Hispanic") conflates race and ethnicity.** Handled by separation logic but produces Unknown race for those 34 subjects.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-07 | Initial draft (combined with ETHNICITY, standalone format) |
| 2.0 | 2026-04-08 | Split from ETHNICITY; revised for three-tier hierarchy; added prototype data observations; marked SME review points |
