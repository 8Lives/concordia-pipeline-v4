# Project Concordia: DM Domain Specification Buildout Plan

**Date:** 2026-04-08
**Version:** 2.0
**Status:** Revised per SME review

---

## 1. Current State Assessment

### 1.1 What Exists Today

The v3-branded prototype relies on a single document — `DM_Harmonization_Spec_v1.4.docx` — as the source of truth for the entire DM domain. The RAG indexer (`rag/indexer.py`) parses this document into four chunk types stored in ChromaDB:

- **Variable Rules** (18 chunks): One per output variable with order, required status, source priority list, transformation rule, and validation/QC rule
- **General Rules** (5 chunks): Scope, schema, text normalization, date normalization, missing values, dictionary decoding
- **QC Rules** (9+ chunks): Individual validation checks (TRIAL validity, uniqueness, required fields, coded values, dates)
- **Valid Value Codelists** (4 chunks): SEX, RACE, COUNTRY, AGEU with code-to-value mappings

The agents (Map, Harmonize, QC, Review) retrieve these chunks via the Retriever API to guide their decisions, with hardcoded fallback dictionaries when RAG retrieval fails.

### 1.2 What's Missing

The current spec treats each variable as a single row in a table: one line for source priority, one line for transformation rule, one line for QC. This is insufficient for several reasons:

1. **No decision principles.** The spec tells the LLM *what* to do ("Trim; apply mixed case; expand abbreviations") but not *how to reason* when the source data doesn't match any expected pattern. The LLM falls back to its general training, which produces inconsistent results.

2. **No separation logic for conflated variables.** Race and ethnicity are routinely combined in source data. The current spec has no guidance for disentangling them.

3. **No cross-variable dependency rules.** The spec doesn't document that pregnancy_status conflicts with sex=M, or that AGEGP should only be populated when AGE is missing.

4. **No provenance requirements.** The pipeline tracks lineage mechanically (rows changed, source column), but there's no spec-driven requirement for semantic provenance (was sex/gender conflated? was race derived from free text?).

5. **No plausibility validation.** QC checks are structural (is the value in the codelist?) but not distributional (is 90% UNKNOWN race a signal of a mapping failure?).

6. **No confidence indicators.** The pipeline has no mechanism to report how confident it is in a mapping decision — whether the value was a clean coded match, an LLM inference, or an unresolvable ambiguity.

### 1.3 Guiding Principles (from specifications_guidelines_goals)

The following principles govern the specification design:

1. **Anonymized data with inherent ambiguity.** Datasets have been de-identified; ambiguity is expected, not exceptional.
2. **Prototype datasets are directionally representative only.** The 15–20 year old PDS datasets inform SME review but are not definitive of what production data will look like.
3. **Supporting documentation beyond data dictionaries.** Production architecture assumes Protocol, aCRF, CSR, and other documents are uploaded with each dataset. Specs should account for this richer context.
4. **SDTM is the controlling mapping** — including for datasets not originally in SDTM format.
5. **CRDSA SMEs define allowed values.** The specifications provide draft values; SMEs have final authority.
6. **No external enrichment.** Use source data and accompanying documentation only. Do not enrich from ClinicalTrials.gov, registries, or other external sources.
7. **No retained sponsor-specific mappings.** Mapping artifacts apply only during processing of a given dataset and are not retained across runs. Each dataset is processed independently using the specifications and its own accompanying documentation.
8. **Confidence indicators required.** Every mapping decision should carry a confidence signal (percentage or grade) so downstream consumers can assess reliability.

### 1.4 Data Inventory (8 Sponsors in dm_dev)

| Sponsor    | NCT ID        | Dataset File                  | Dictionary Format | SEX | RACE | ETHNIC | AGE | AGEGP | COUNTRY |
|------------|---------------|-------------------------------|-------------------|-----|------|--------|-----|-------|---------|
| AZ_205     | NCT00673205   | demog_NCT00673205.sas7bdat    | xlsx              | Yes (coded) | Yes (ORIGIN, 1-7) | No  | No  | Yes (AGEGRP) | Coded* |
| AZ_229     | NCT00554229   | rd_subj_NCT00554229.sas7bdat  | xlsx              | Yes ($SEX, 1/2) | Yes (dual old/new codes) | Yes (ETHGRP, 10+ codes, de-ID) | Unclear | Yes (AGEGP + AGEGRP) | Coded* |
| Amgen_265  | NCT00460265   | demo_NCT00460265.sas7bdat     | pdf               | Yes | Yes  | No     | Yes (Char/20) | Yes (AGECAT) | Coded* |
| EMD_221    | NCT00689221   | dm_NCT00689221.sas7bdat       | pdf               | Yes | Yes  | Yes    | Yes | No    | Coded* |
| Lilly_568  | NCT01439568   | dm_NCT01439568.sas7bdat       | docx              | TBD | TBD  | TBD    | TBD | TBD   | Coded* |
| Merck_188  | NCT00409188   | dm_NCT00409188.sas7bdat       | pdf               | Yes | Yes  | Yes    | Yes | No    | Coded* |
| Pfizer_374 | NCT00699374   | demog_NCT00699374.sas7bdat    | xlsx              | Yes | Yes  | TBD    | Yes | No    | Coded* |
| Sanofi_323 | NCT00401323   | demo_NCT00401323.sas7bdat     | xls               | Yes | Yes  | TBD    | TBD | TBD   | Coded* |

*\*COUNTRY is present in datasets as coded values; requires decoding via the data dictionary supplied with each dataset. This is a standard decode-then-normalize operation, not a missing-data problem.*

**Data limitations to keep in mind:**
- SAS format catalogs (.sas7bcat) may be needed to decode numeric values in some datasets
- AZ_205 and AZ_229 have de-identification data loss (age categorized, ethnicity codes collapsed to 99)
- AZ_229 has dual race code versioning (old codes 1-3, new codes 11-15)

---

## 2. Target Architecture: Three-Tier Specification Hierarchy

### 2.1 Design Decisions

**End-state specs, not ontology.** Each variable gets a specification document that defines the desired end state and provides decision principles for the LLM, rather than attempting to enumerate every possible source encoding.

**Three-tier instruction hierarchy.** To reduce duplication across variable specs and support multi-domain extensibility, instructions are organized at three levels:

| Level | Scope | Contains | Override Rules |
|-------|-------|----------|---------------|
| **System** | All domains, all variables | Universal normalization rules (text casing, whitespace trimming, date format, null handling conventions, confidence grading framework) | Defaults that any domain can override with justification |
| **Domain** | All variables within a domain (e.g., DM) | Domain scope and grain, output schema, column mapping conventions, domain-level QC checks, cross-variable dependency rules | Can override system defaults; cannot contradict system rules |
| **Variable** | Single variable (e.g., SEX) | Semantic identity, target allowed values, mapping decision principles, variable-specific validation, provenance requirements | Can override domain defaults; cannot contradict domain rules |

This means a variable spec for SEX does not need to repeat "apply mixed case to all string values" — that's inherited from the system level. The variable spec only contains what is unique to SEX: allowed values, conflation handling, code decoding patterns, etc.

### 2.2 Specification File Structure

```
knowledge_base/
├── system_rules.md                        ← Universal rules for all domains
├── domains/
│   └── DM/
│       ├── DM_domain_rules.md             ← DM-specific scope, schema, cross-variable rules
│       └── variables/
│           ├── DM_SEX.md
│           ├── DM_RACE.md
│           ├── DM_ETHNICITY.md
│           ├── DM_AGE.md
│           ├── DM_AGEU.md
│           ├── DM_AGEGP.md
│           ├── DM_COUNTRY.md
│           ├── DM_TRIAL.md
│           ├── DM_SUBJID.md
│           ├── DM_USUBJID.md
│           ├── DM_STUDYID.md
│           ├── DM_SITEID.md
│           ├── DM_ARM.md
│           ├── DM_ARMCD.md
│           ├── DM_BRTHDTC.md
│           ├── DM_RFSTDTC.md
│           ├── DM_RFENDTC.md
│           └── DM_DOMAIN.md
└── value_sets/
    ├── race_values.md                     ← SME-defined allowed values + known synonyms
    ├── ethnicity_values.md
    ├── country_values.md
    └── sex_values.md
```

**Note on value_sets/**: These are reference files of SME-approved allowed target values and known source synonyms. They are *not* retained mapping artifacts from prior runs. They are versioned, governed reference data that the LLM maps *to*. When the pipeline encounters a new source value not in any reference file, it maps using the decision principles in the variable spec and reports the mapping with a confidence indicator in the transformation report. The new value is added to the value set reference file for future SME review.

### 2.3 Variable Specification Template (Revised)

With system and domain-level rules absorbing the common instructions, each variable spec is simplified to focus on what is unique to that variable:

| Section | Purpose | SME Input Required? |
|---------|---------|---------------------|
| 1. Semantic Identity | What the variable means; CDISC/SDTM alignment | No (reference) |
| 2. Allowed Values | Enumerated target values with definitions. **SME-defined.** | **Yes — primary SME input** |
| 3. Mapping Decision Principles | How to reason about source-to-target mapping; representative patterns | Review only |
| 4. Variable-Specific Business Rules | Rules unique to this variable (e.g., AGEGP conditional on AGE absence) | **Yes — SME validation** |
| 5. Provenance Flags | What metadata this variable requires beyond standard lineage | Review only |
| 6. Validation Criteria | Conformance checks, plausibility bounds | **Yes — SME sets thresholds** |
| 7. Known Limitations | Unresolvable ambiguities, standard-change risks | Informational |

### 2.4 System-Level Rules (Content Preview)

The `system_rules.md` file will contain rules that currently repeat across variable specs:

- **Text normalization:** Apply mixed case to all categorical string values unless the variable spec specifies otherwise
- **Whitespace:** Trim leading/trailing whitespace from all values
- **Null handling:** No nulls permitted in harmonized output; missing values map to the variable's defined unknown/missing value
- **Date format:** ISO 8601 (YYYY-MM-DD) for all date variables
- **SAS date conversion:** Numeric SAS dates (days since 1960-01-01) convert to ISO 8601
- **Code decoding:** When a data dictionary is provided, decode numeric codes to their labeled values before applying transformation rules
- **Confidence grading framework:** All mapping decisions carry a confidence indicator:
  - **HIGH** — Direct match to allowed value or clean code decode via data dictionary
  - **MEDIUM** — Synonym resolution, case normalization, or minor inference required
  - **LOW** — LLM inference from ambiguous or free-text source; no dictionary available
  - **UNMAPPED** — Source value could not be resolved; mapped to unknown/missing value
- **Column mapping convention:** Match source columns to target variables using the variable spec's source priority list; fall back to semantic similarity matching

### 2.5 Domain-Level Rules (Content Preview)

The `DM_domain_rules.md` file will contain:

- **Scope:** One record per subject per trial (subject-level grain)
- **Output schema:** The 18 DM output variables with order, data type, and required/optional status
- **Cross-variable dependencies:**
  - AGE ↔ AGEGP: Populate AGEGP only when AGE is not available or derivable
  - AGE derivation: If AGE is missing but BRTHDTC and RFSTDTC are present, derive AGE
  - RFENDTC ≥ RFSTDTC: Date ordering constraint
  - SEX ↔ pregnancy-related flags: Cross-domain plausibility check
  - RACE ↔ ETHNICITY: Independent variables; any combination is valid
  - USUBJID derivation: STUDYID + separator + SUBJID when not present in source
- **Domain-level QC checks:** Duplicate subject detection, required variable completeness, coded-value-without-dictionary flagging
- **Variables in scope:** Explicit list of the 18 variables with tier classification

---

## 3. Variable Specifications: Scope and Priority

### 3.1 Priority Tiers

**Tier 1 — Core Variables (Highest complexity, highest SME input needed)**

| Variable | Complexity | Key Challenge | Spec Status |
|----------|-----------|---------------|-------------|
| SEX      | Medium    | Code decoding, sex/gender conflation | Draft exists — needs revision for three-tier hierarchy |
| RACE     | High      | Multiple classification systems, OMB roll-up, de-ID data loss | Draft exists — needs revision |
| ETHNICITY| High      | Separation from race, combined fields, de-ID collapse | Draft exists — needs revision |
| AGE / AGEGP | High  | Conditional pair, derivation from dates, char→numeric, categorical de-ID | Not started |
| COUNTRY  | Medium    | Coded in source datasets; decode via data dictionary, then normalize | Not started |

**Tier 2 — Identity and Trial Structure Variables**

| Variable | Complexity | Key Challenge | Spec Status |
|----------|-----------|---------------|-------------|
| TRIAL    | Low       | Filename extraction, NCT format validation | Not started |
| SUBJID   | Medium    | Float-to-int conversion, heuristic uniqueness matching | Not started |
| USUBJID  | Medium    | Derivation rule (STUDYID + SUBJID concatenation) | Not started |
| STUDYID  | Low       | Protocol number normalization | Not started |
| SITEID   | Low       | String normalization, format preservation | Not started |
| DOMAIN   | Trivial   | Constant "DM" | Not started |

**Tier 3 — Treatment and Date Variables**

| Variable | Complexity | Key Challenge | Spec Status |
|----------|-----------|---------------|-------------|
| ARM      | Medium    | Free-text normalization, abbreviation expansion | Not started |
| ARMCD    | Low       | Code normalization, may need derivation from ARM | Not started |
| AGEU     | Trivial   | Standardize to "Years" in nearly all cases | Not started |
| BRTHDTC  | Medium    | SAS date conversion, de-ID (often missing/shifted) | Not started |
| RFSTDTC  | Medium    | SAS date conversion, ISO 8601 formatting | Not started |
| RFENDTC  | Medium    | SAS date conversion, must be ≥ RFSTDTC | Not started |

### 3.2 Supplementary Documents

| Document | Purpose | Priority |
|----------|---------|----------|
| system_rules.md | Universal rules across all domains (text normalization, date format, confidence grading, null handling) | Tier 1 — write first |
| DM_domain_rules.md | DM scope, schema, cross-variable dependencies, domain QC checks | Tier 1 — write second |
| Value set reference files (×4) | SME-approved allowed values for SEX, RACE, ETHNICITY, COUNTRY | Tier 1 — draft values, mark for SME review |

---

## 4. SME Input Template

### 4.1 Purpose

The specifications provide draft values and decision rules. CRDSA Subject Matter Experts have final authority over allowed values and validation thresholds. The SME input template is an Excel workbook designed to make SME review as efficient as possible: pre-populated with draft values, with clear markers showing where SME input is needed.

### 4.2 Workbook Structure

**Tab 1: Allowed Values** (one section per variable)

| Variable | Draft Value | Definition | CDISC CT Reference | SME Status | SME Notes |
|----------|-------------|------------|-------------------|------------|-----------|
| SEX | Male | ... | C66731 | ☐ Approve ☐ Modify ☐ Remove | |
| SEX | Female | ... | C66731 | ☐ Approve ☐ Modify ☐ Remove | |
| SEX | Unknown | ... | C66731 | ☐ Approve ☐ Modify ☐ Remove | |
| RACE | White | Origins in Europe, Middle East, North Africa | C74457 | ☐ Approve ☐ Modify ☐ Remove | |
| ... | ... | ... | ... | ... | ... |

**Tab 2: Validation Thresholds** (one row per plausibility check)

| Variable | Check | Draft Threshold | Rationale | SME Threshold | SME Notes |
|----------|-------|----------------|-----------|---------------|-----------|
| RACE | UNKNOWN rate (clinical trial) | < 5% | Well-curated trial data | | |
| RACE | UNKNOWN rate (RWD) | < 15% | EHR/claims typically higher | | |
| AGE | Plausible range | 0–120 years | Clinical plausibility | | |
| ... | ... | ... | ... | ... | ... |

**Tab 3: Decision Rules** (one row per mapping decision principle)

| Variable | Rule | Draft Logic | Example | SME Status | SME Notes |
|----------|------|-------------|---------|------------|-----------|
| RACE/ETHNICITY | Hispanic in race field | Extract to ETHNICITY; set RACE = Unknown | Source: "Hispanic" → ETH: "Hispanic or Latino", RACE: "Unknown" | ☐ Approve ☐ Modify | |
| AGE/AGEGP | Conditional population | AGEGP only when AGE unavailable | Source has AGECAT but no AGE → use AGEGP | ☐ Approve ☐ Modify | |
| ... | ... | ... | ... | ... | ... |

**Tab 4: Cross-Variable Rules**

| Rule | Variables Involved | Draft Logic | SME Status | SME Notes |
|------|-------------------|-------------|------------|-----------|
| Date ordering | RFSTDTC, RFENDTC | RFENDTC must be ≥ RFSTDTC | ☐ Approve ☐ Modify | |
| AGE derivation | AGE, BRTHDTC, RFSTDTC | Derive AGE from dates when AGE missing | ☐ Approve ☐ Modify | |
| ... | ... | ... | ... | ... |

### 4.3 SME Workflow

1. Pre-populated workbook delivered to SME
2. SME reviews each tab, marks status (Approve / Modify), adds notes
3. Returned workbook is reconciled into the markdown specification files
4. Changes are versioned in the spec change logs

---

## 5. Tools and Skills Needed

### 5.1 Immediate Needs (Before Spec Writing Can Proceed)

| Need | Purpose | How to Address |
|------|---------|---------------|
| **SAS dataset reader** | Read .sas7bdat files to inspect actual data values and produce frequency tables | Python `pyreadstat` in prototype environment |
| **SAS format catalog extractor** | Decode .sas7bcat files to understand numeric code meanings | Python `pyreadstat` reads catalogs; extract to CSV |
| **PDF data dictionary reader** | Parse Amgen_265, EMD_221, Merck_188 PDF dictionaries into structured format | PDF skill available in Cowork; alternatively `pdfplumber` in Python |
| **Excel workbook creator** | Produce the SME input template | xlsx skill available in Cowork |

### 5.2 Spec Authoring Support

| Need | Purpose | How to Address |
|------|---------|---------------|
| **CDISC CT reference** | Verify allowed value sets against current CDISC Controlled Terminology | Web reference or local copy of CDISC CT packages |
| **ISO 3166 country codes** | Reference for country value set | Publicly available; embed in value set reference file |

### 5.3 No Additional Connectors or Plugins Required

The specification authoring work is file-based (markdown + Excel). All tools needed are available in the current Cowork environment. Pipeline integration tooling (RAG indexer, test harness) is deferred to the architecture evaluation phase.

---

## 6. Execution Plan

### Phase 1: Foundation (Estimated: 1–2 sessions)

**Objective:** Establish the three-tier specification infrastructure, extract data intelligence from prototype datasets, and finalize the Tier 1 variable specs.

| Step | Deliverable | Dependency |
|------|-------------|------------|
| 1a | Extract and decode all 8 sas7bdat files to produce value frequency tables for all DM variables | pyreadstat |
| 1b | Parse all data dictionaries (xlsx, pdf, docx, xls) into a standardized reference format | PDF reader |
| 1c | `system_rules.md` — universal rules (text normalization, date format, confidence grading, null handling, code decoding) | None |
| 1d | `DM_domain_rules.md` — DM scope, output schema, cross-variable dependencies, domain QC | None |
| 1e | Revise SEX, RACE, ETHNICITY specs to the three-tier format (remove instructions now in system/domain rules; keep only variable-unique content) | 1a, 1b, 1c, 1d |

### Phase 2: Variable Specs and SME Template (Estimated: 2–3 sessions)

**Objective:** Complete all 18 variable specifications and produce the SME input workbook.

| Step | Deliverable | Dependency |
|------|-------------|------------|
| 2a | DM_AGE.md and DM_AGEGP.md (conditional pair) | Phase 1 data extraction |
| 2b | DM_AGEU.md | None |
| 2c | DM_COUNTRY.md (decode from data dictionary, then normalize) | Phase 1 data extraction |
| 2d | DM_TRIAL.md, DM_SUBJID.md, DM_USUBJID.md, DM_STUDYID.md, DM_SITEID.md, DM_DOMAIN.md | None |
| 2e | DM_ARM.md, DM_ARMCD.md | Phase 1 data extraction |
| 2f | DM_BRTHDTC.md, DM_RFSTDTC.md, DM_RFENDTC.md | Phase 1 data extraction |
| 2g | Value set reference files: sex_values.md, race_values.md, ethnicity_values.md, country_values.md | All Tier 1 variable specs |
| 2h | SME Input Template (Excel workbook with 4 tabs: Allowed Values, Validation Thresholds, Decision Rules, Cross-Variable Rules) | All variable specs |

### Phase 3: Architecture Evaluation (Scope TBD)

**Objective:** Evaluate prototype and production architectures accounting for the new specification structure and content.

*Details to be defined after Phase 2 completion. This phase will consider how the three-tier specification hierarchy, confidence indicators, provenance requirements, and multi-domain extensibility should be reflected in the pipeline architecture.*

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| SAS format catalogs not recoverable from all_domains | Medium | High — blocks accurate code decoding for some sponsors | Fall back to data-driven frequency analysis + LLM inference; report confidence as LOW |
| De-identification collapses make some source data unharmonizable | Confirmed | Medium — affects AZ_205 (age) and AZ_229 (ethnicity) | Map to Unknown with provenance flags; document in Known Limitations section of affected variable specs |
| Prototype datasets not representative of production data | Confirmed | Low for specs (specs are designed for general patterns, not prototype-specific); Medium for validation | Specs use decision principles, not enumerated mappings, so they adapt to unseen data patterns |
| SME review cycle delays Phase 2 completion | Medium | Medium — blocks finalization of allowed values and thresholds | Deliver workbook with draft values that are usable as-is; SME review can refine iteratively without blocking spec authoring |
| Three-tier hierarchy adds complexity | Low | Low — simpler variable specs offset the added structural complexity | Clear override rules documented in system_rules.md; each level is self-contained |

---

## 8. Success Criteria

1. **Completeness:** All 18 DM output variables have individual specifications. System and domain rule documents are complete.
2. **Hierarchy integrity:** Variable specs contain only variable-unique content; no duplication of system or domain rules.
3. **SME-readiness:** The Excel workbook is pre-populated with all draft values, thresholds, and decision rules, with clear markers for SME input.
4. **Multi-domain extensibility:** The three-tier structure supports adding a new domain (e.g., AE, LB) by creating a new domain_rules.md and variable specs without modifying system_rules.md.
5. **Confidence framework:** Every variable spec includes confidence calibration criteria that map to the system-level grading framework (HIGH / MEDIUM / LOW / UNMAPPED).
6. **Provenance:** Every variable spec defines what provenance metadata is required for that variable, beyond standard lineage tracking.

---

## 9. Resolved Questions

These questions from the v1.0 plan have been resolved per SME input in `specifications_guidelines_goals.md`:

| Question | Resolution |
|----------|------------|
| Spec format for stakeholders | Replace the .docx entirely. Markdown specifications are the primary format. |
| COUNTRY derivation strategy | COUNTRY is coded in source datasets. Decode via data dictionary supplied with dataset, then normalize. No external enrichment. |
| Sponsor-specific mapping retention | Do not retain. Mapping artifacts apply only during processing of a given dataset. Sponsor-specific adjustments should only be applied to the dataset being processed. |
| Multi-domain extensibility | Yes. Design the three-tier hierarchy now with extensibility in mind. System rules apply across all future domains. |
| Value set governance | New values are added to the value set reference file. The transformation report indicates the LLM-mapped value with a confidence indicator. SME review happens via the governance cycle, not inline. |
| Simplification via instruction hierarchy | Yes. System-level rules (mixed case, date format) and domain-level rules (column mappings, cross-variable dependencies) absorb common instructions, keeping variable specs focused. |
