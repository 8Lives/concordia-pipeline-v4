# DM Variable Specification: COUNTRY

**Variable:** COUNTRY
**Domain:** Demographics (DM)
**Order:** 9
**Required:** Optional
**Version:** 1.1
**Last Updated:** 2026-04-09
**Inherits:** system_rules.md, DM_domain_rules.md

---

## 1. Semantic Identity

**Definition:** The country of the investigational site where the subject was enrolled. This is a site-level attribute assigned to the subject, not the subject's nationality or country of origin.

**SDTM Reference:** DM.COUNTRY — CDISC Controlled Terminology codelist C66733 (ISO 3166-1 alpha-3 codes)

**Important:** CDISC SDTM uses 3-letter ISO 3166-1 alpha-3 country codes (e.g., "USA", "JPN", "GBR"). However, Concordia harmonizes to the full country name in mixed case for readability, with the ISO code preserved in provenance. *(SME review: confirm whether target should be full name or ISO code.)*

---

## 2. Allowed Values *(SME review required)*

| Property | Value |
|----------|-------|
| Data type | String (categorical) |
| Value set | Full country names per ISO 3166-1 (mixed case) |
| Missing value | "Unknown" |

**Common values observed in prototype data (AZ_229 — the only sponsor with decoded COUNTRY):**

Japan (n=38), Canada (n=30), China (n=30), United States (n=20), Australia (n=14), Brazil (n=14), Belgium (n=13), India (n=13), France (n=12), Czech Republic (n=11), Korea Republic of (n=11), Netherlands (n=10), United Kingdom (n=10), Denmark (n=9), Sweden (n=6), Taiwan (n=5), Russia (n=4), Poland (n=3), Hungary (n=3), Finland (n=3), and others.

**Source Priority List:** COUNTRY, CTRY, CNTR, COUNTRY_CODE, SITECNTRY

**Observed Source Patterns:**

| Sponsor | Source Column | Values Found | Notes |
|---------|-------------|-------------|-------|
| AZ_229 | COUNTRY | Full country names (pre-decoded) | 20+ countries, mixed case, directly usable |
| Other sponsors | Coded | Numeric or alpha codes | Require decode via data dictionary |

---

## 3. Mapping Decision Principles

1. **Decode first, normalize second.** If the source contains numeric country codes, decode via the data dictionary supplied with the dataset. Then normalize to the standard full country name.

2. **ISO code expansion.** If the source uses ISO 3166-1 alpha-2 (e.g., "US", "JP") or alpha-3 (e.g., "USA", "JPN") codes, expand to the full country name. Preserve the original code in `source_value_raw`.

3. **Name normalization.** Apply mixed case per system rules. Standardize common variations:
   - "US", "USA", "United States of America" → "United States"
   - "UK", "GBR", "Great Britain" → "United Kingdom"
   - "Korea, Republic of" → "South Korea" *(SME review: confirm preferred form)*
   - "Russian Federation" → "Russia" *(SME review: confirm preferred form)*

4. **Do not infer country** from site ID patterns, investigator names, or language. Country must come from an explicit source field or the data dictionary.

5. **Multi-country trials are expected.** A single trial may have sites in many countries. Each subject's COUNTRY reflects their specific site.

**Representative patterns:**

| Source Value | Target | Confidence | Notes |
|-------------|--------|------------|-------|
| "United States" | United States | HIGH | Direct match |
| "US", "USA" | United States | HIGH | Standard ISO expansion |
| "Japan" | Japan | HIGH | Direct match |
| "JPN" | Japan | HIGH | ISO alpha-3 expansion |
| 1 (dictionary: 1=United States) | United States | HIGH | Code decode |
| "Korea, Republic of" | South Korea | MEDIUM | Name normalization (confirm with SME) |
| NULL, "" | Unknown | HIGH | Standard missing |

---

## 4. Variable-Specific Business Rules

### 4.1 Country Name Standardization

A reference list of country name normalizations is maintained in `value_sets/country_values.md`. When the source uses a non-standard name (e.g., "Czech Republic" vs. "Czechia"), map to the standard form in the reference file.

### 4.2 Historical Country Names

Some older datasets may reference countries that have since changed names (e.g., "Burma" → "Myanmar", "Swaziland" → "Eswatini"). Map to the current name. Preserve the original in `source_value_raw`.

### 4.3 Novel Countries (Not in Reference Value Set)

The `country_values.md` reference file covers countries observed in prototype development datasets (~25 entries). When processing a new dataset that contains a country not in the reference file:

1. **Decode first.** If the source uses a numeric or short code, decode via the data dictionary. If decoded to an ISO 3166-1 recognized country name, accept the value.
2. **Validate against ISO 3166-1.** If the decoded or raw value matches a recognized ISO 3166-1 country name (current or historical), pass through and normalize per Section 3.
3. **Flag for reference file expansion.** Log a `COUNTRY_NOT_IN_VALUE_SET` informational flag. The value is NOT rejected — it is passed through with confidence = MEDIUM.
4. **Do not default to Unknown.** A valid country name that is simply absent from the reference file is not an error. Unknown is reserved for genuinely missing or unresolvable values.

**Rationale:** The value set is a development convenience, not a controlled terminology gate. ISO 3166-1 is the authoritative source. The reference file should be expanded when new countries are encountered, but their absence must not cause silent data loss.

---

## 5. Provenance Flags

Standard provenance fields are sufficient for COUNTRY. No variable-specific provenance flags required.

---

## 6. Validation Criteria *(SME review required)*

### Conformance
- All values should be recognized country names from the ISO 3166-1 standard or "Unknown"

### Plausibility
- Number of unique countries should be plausible for the study (single-country studies = 1; global Phase III trials = 10–30+)
- No country should appear with a frequency that suggests a mapping error (e.g., > 90% of records from one country in a "global" trial may warrant verification)

### Determinism
- Within a single source dataset, the same source country code must always map to the same target country name

---

## 7. Known Limitations

1. **Country data requires dictionary decode for most sponsors.** AZ_229 is the only prototype dataset with pre-decoded country names. All other sponsors have coded values that depend on the data dictionary for decoding.
2. **Country name standardization is an ongoing task.** The "preferred" form of some country names (South Korea vs. Korea Republic of; Russia vs. Russian Federation) should be confirmed by SME review.
3. **Country may reflect enrollment site, not subject residence.** Subjects may travel to sites in other countries for enrollment, particularly for rare disease trials.

---

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial draft in three-tier format |
| 1.1 | 2026-04-09 | Added Section 4.3: novel country handling — passthrough with ISO validation, no silent default to Unknown. |
