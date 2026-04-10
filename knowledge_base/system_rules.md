# Concordia System Rules

**Version:** 1.0
**Last Updated:** 2026-04-08
**Scope:** All domains, all variables

These rules apply universally across all harmonization domains and variables. Domain-level rules may override system defaults with documented justification. Variable-level rules may override domain defaults with documented justification.

---

## 1. Text Normalization

- **Case:** Apply mixed case (title case) to all categorical string values unless the variable spec specifies otherwise. Examples: "Male" not "MALE" or "male"; "United States" not "UNITED STATES" or "united states."
- **Whitespace:** Trim all leading and trailing whitespace from every value.
- **Internal whitespace:** Collapse multiple consecutive internal spaces to a single space.
- **Special characters:** Preserve hyphens, apostrophes, and other meaningful punctuation. Do not strip diacritics unless the target value set requires ASCII-only values.

## 2. Null and Missing Value Handling

- **No nulls in harmonized output.** Every cell in the harmonized dataset must contain a value.
- **Missing value representation:** Each variable spec defines its own "unknown" or "not applicable" value (e.g., "Unknown" for categorical variables). If a source value is null, empty, whitespace-only, or explicitly coded as missing (e.g., "N/A", "Not Reported", ".", "NA", "-", "99", "999"), map to the variable's defined missing value.
- **Distinguish absence from refusal when possible.** If the source data distinguishes between "Unknown" (data not collected) and "Not Reported" (subject declined), preserve this distinction in the provenance metadata even though both map to the same harmonized value.

## 3. Date Handling

- **Target format:** ISO 8601 (YYYY-MM-DD) for all date variables.
- **SAS numeric dates:** SAS stores dates as the number of days since January 1, 1960. Convert using this epoch. A SAS date value of 0 = 1960-01-01.
- **Partial dates:** If only year is available (e.g., "1955"), store as "1955" (year only). If year and month are available (e.g., "1955-03"), store as "1955-03". Do not fabricate day or month values.
- **Date validation:** Reject dates before 1900-01-01 or after the current date as implausible unless the variable spec provides a different range.
- **De-identified dates:** Some datasets shift dates for de-identification. If the shift is documented, note it in provenance but do not attempt to reverse the shift. If dates appear implausible (e.g., birth dates in the future), flag rather than discard.

## 4. Numeric Handling

- **Integer presentation:** When a source numeric value represents a whole number stored as float (e.g., "1.0" for subject ID), convert to integer representation ("1") unless the variable spec requires decimal precision.
- **Precision:** Preserve the precision of the source data. Do not round or truncate unless the variable spec defines a precision rule.
- **Character-to-numeric conversion:** When a numeric variable is stored as character type in the source (common for AGE in some datasets), convert to numeric. If conversion fails (non-numeric characters), map to the variable's missing value and flag in provenance.

## 5. Code Decoding

- **Data dictionary first.** When a data dictionary is supplied with the dataset, use it to decode numeric or coded values before applying any transformation rules. The data dictionary is the authoritative source for the meaning of codes within that specific dataset.
- **Format catalogs.** If the data dictionary references SAS format catalogs (.sas7bcat), use the catalog to decode values. If the catalog is not available, attempt to decode using the variable spec's known code patterns. Report confidence as LOW for any decoding done without the catalog.
- **Decode before transform.** Always decode first, then apply normalization (case, whitespace). Never normalize coded numeric values directly (e.g., do not title-case "1" — decode "1" to "Male" first, then apply case rules).

## 6. Confidence Grading

Every mapping decision for a categorical variable carries a confidence indicator. The grade reflects how much inference was required, not how likely the mapping is to be correct.

| Grade | Criteria | Examples |
|-------|----------|----------|
| **HIGH** | Direct match to an allowed value, or clean code decode via data dictionary. No ambiguity. | Source "Male" → Target "Male"; Source code "1" with dictionary "1=Male" → "Male" |
| **MEDIUM** | Synonym resolution, case normalization, minor abbreviation expansion, or well-established equivalent. Mapping is confident but required a transformation step. | Source "Caucasian" → Target "White"; Source "M" → Target "Male"; Source "AA" → Target "Black or African American" |
| **LOW** | LLM inference from ambiguous, free-text, or non-standard source values. No data dictionary available for coded values. Cross-system mapping with known conceptual mismatch. | Source "brown" → Target "Unknown" (ambiguous); Source numeric code with no dictionary → LLM-inferred decode; UK ONS categories → OMB categories |
| **UNMAPPED** | Source value could not be resolved to any allowed target value. Mapped to the variable's unknown/missing value. | Source "human" → "Unknown"; Source garbled text → "Unknown" |

**Confidence is per-value, not per-row.** A single record may have HIGH confidence for SEX and LOW confidence for RACE.

**Reporting:** The transformation report must include, for each variable: the count and percentage of values at each confidence level. This gives downstream consumers a quality signal without requiring them to inspect individual records.

## 7. Provenance (Standard Fields)

Every harmonized record carries the following standard provenance metadata, regardless of domain or variable:

| Field | Type | Description |
|-------|------|-------------|
| `source_dataset_id` | String | Identifier of the originating dataset (e.g., NCT ID or filename) |
| `source_field_name` | String | Original field name in the source for each harmonized variable |
| `source_value_raw` | String | The exact value from the source, before any transformation |
| `mapping_confidence` | Enum | HIGH, MEDIUM, LOW, UNMAPPED — per the grading framework above |
| `mapping_notes` | String | Free-text explanation of any non-obvious mapping decisions |

Individual variable specs may define additional provenance fields specific to that variable (e.g., `sex_gender_conflated` for SEX).

## 8. Transformation Report

Each pipeline run produces a transformation report that includes:

- **Per-variable summary:** Source column matched, transformation applied, count of values changed, count at each confidence level
- **Unmapped values:** List of source values that could not be resolved, with frequency counts
- **New value encounters:** Source values not previously seen in the value set reference files, with the LLM's mapping decision and confidence grade. These are candidates for SME review and potential addition to the value set reference.
- **Data quality flags:** Any plausibility or consistency issues detected during validation

## 9. Supporting Documentation

In the production architecture, the following documents may be supplied with a dataset in addition to the data dictionary:

| Document | Abbreviation | Use in Harmonization |
|----------|-------------|---------------------|
| Protocol | — | Clinical context, study design, inclusion/exclusion criteria |
| Annotated Case Report Form | aCRF | Maps CRF fields to SDTM variables; authoritative for variable intent |
| Clinical Study Report | CSR | Study results, population description |
| Define.xml | — | Machine-readable dataset metadata (CDISC standard) |

When these documents are available, they should inform mapping decisions — particularly the aCRF, which provides the most direct link between source variables and SDTM intent. The data dictionary remains the primary source for code decoding; the aCRF provides semantic context for ambiguous mappings.

## 10. Processing Independence

Each dataset is processed independently using the specifications and its own accompanying documentation. Mapping decisions from one dataset run do not carry over to another, even for the same sponsor. This is a fundamental design principle:

- **No retained sponsor profiles.** Sponsor data varies between contributions (different dates, indications, data standards versions). Assumptions from one dataset may not apply to another from the same sponsor.
- **No cross-run mapping caches.** If a source value was resolved by the LLM in a prior run, that resolution is not automatically reused. The LLM re-evaluates each value against the specifications and the current dataset's documentation.
- **Value set reference files are the exception.** These are governed reference data (SME-approved allowed target values and known synonyms). They are versioned and updated through the SME governance cycle, not through pipeline runs.
