# DM Domain Data Extraction Summary

**Generated:** 2026-04-08

## 1. Per-Sponsor Summary

| Sponsor | NCT ID | Rows | Variables Found | Source Columns |
|---------|--------|------|-----------------|---|
| AZ | NCT00673205 | 1,805 | AGEGP, RACE, STUDYID, SUBJID | |
| AZ | NCT00554229 | 266 | AGEGP, ARM, ARMCD, COUNTRY, ETHNICITY, RACE, SEX, SITEID, STUDYID, SUBJID | |
| Amgen | NCT00460265 | 520 | AGE, AGEGP, ARM, ARMCD, RACE, SEX, SITEID, STUDYID, SUBJID | |
| EMD | NCT00689221 | 273 | AGE, AGEU, ARM, ARMCD, BRTHDTC, COUNTRY, DOMAIN, ETHNICITY, RACE, RFENDTC, RFSTDTC, SEX, SITEID, STUDYID, USUBJID | |
| Lilly | NCT01439568 | 130 | AGE, AGEU, ARM, ARMCD, BRTHDTC, COUNTRY, DOMAIN, ETHNICITY, RACE, RFENDTC, RFSTDTC, SEX, STUDYID, USUBJID | |
| Merck | NCT00409188 | 507 | AGE, AGEU, ARM, ARMCD, BRTHDTC, COUNTRY, DOMAIN, ETHNICITY, RACE, RFENDTC, RFSTDTC, SEX, SITEID, STUDYID, SUBJID, USUBJID | |
| Pfizer | NCT00699374 | 542 | AGE | |
| Sanofi | NCT00401323 | 282 | AGE, RACE, SEX | |

## 2. Cross-Sponsor Variable Analysis

### SEX

**Data Type:** object | **Type:** Categorical

**AZ_229** (SEX)

| Value | Count | % |
|-------|-------|---|
| 1 | 266 | 100.0% |

**Amgen_265** (SEXCD)

| Value | Count | % |
|-------|-------|---|
| M | 455 | 87.5% |
| F | 65 | 12.5% |

**EMD_221** (SEX)

| Value | Count | % |
|-------|-------|---|
| M | 143 | 52.4% |
| F | 130 | 47.6% |

**Lilly_568** (SEX)

| Value | Count | % |
|-------|-------|---|
| F | 67 | 51.5% |
| M | 62 | 47.7% |
| (blank) | 1 | 0.8% |

**Merck_188** (SEX)

| Value | Count | % |
|-------|-------|---|
| M | 345 | 68.0% |
| F | 162 | 32.0% |

**Sanofi_323** (SEX)

| Value | Count | % |
|-------|-------|---|
| MALE | 252 | 89.4% |
| FEMALE | 30 | 10.6% |

---

### RACE

**Data Type:** Mixed (numeric and categorical) | **Type:** Ordinal/Categorical

**AZ_205** (ORIGIN) — Numeric codes
- Min: 1.0 | Max: 7.0 | Mean: 1.19 | n_unique: 7
- Most common: 1.0 (1709/1805, 94.7%)

**AZ_229** (RACE) — New code system
- Code 11: 160 subjects (60.2%)
- Code 13: 99 subjects (37.2%)
- Code 99: 7 subjects (2.6%)

**Amgen_265** (RACE) — Multiple codes (6 unique values)

**EMD_221** (RACE) — Categorical (5 unique values)

**Lilly_568** (RACE) — Categorical (5 unique values)

**Merck_188** (RACE) — Categorical
- WHITE: 469 (92.5%)
- ASIAN / PACIFIC ISLANDER: 21 (4.1%)
- LATINO / HISPANIC: 8 (1.6%)
- BLACK OR AFRICAN AMERICAN: 5 (1.0%)
- OTHER: 4 (0.8%)

**Sanofi_323** (RACE) — Categorical
- CAUCASIAN: 257 (91.1%)
- OTHER: 25 (8.9%)

---

### ETHNICITY

**Data Type:** object | **Type:** Categorical

**AZ_229** (ETHGRP) — Numeric codes
- Code 98: 153 (57.5%)
- Code 10: 39 (14.7%)
- Code 9: 36 (13.5%)
- Code 8: 24 (9.0%)
- Code 1: 14 (5.3%)

**EMD_221** (ETHNIC) — Numeric codes
- Code 1: 252 (92.3%)
- Code 2: 17 (6.2%)
- Code 3: 4 (1.5%)

**Lilly_568** (ETHNIC) — Text
- Non-Hispanic: 122 (93.8%)
- Unknown: 5 (3.8%)
- Hispanic/Latino: 2 (1.5%)
- (blank): 1 (0.8%)

**Merck_188** (ETHNIC) — Text
- NOT HISPANIC OR LATINO: 499 (98.4%)
- HISPANIC OR LATINO: 8 (1.6%)

---

### AGE

**Data Type:** float64 | **Type:** Numeric

| Sponsor | Source Col | Count | Null | Min | Max | Mean | n_unique |
|---------|-----------|-------|------|-----|-----|------|---------|
| Amgen_265 | AGE | 520 | 0 | 50.0 | 65.0 | 57.73 | 47 |
| EMD_221 | AGE | 273 | 66 | - | - | - | 47 |
| Lilly_568 | AGE | 130 | 1 | 50.1 | 75.7 | 65.62 | 107 |
| Merck_188 | AGE | 507 | 0 | 52.0 | 70.0 | 62.53 | 46 |
| Pfizer_374 | AGE | 542 | 2 | 48.0 | 76.0 | 61.48 | 63 |
| Sanofi_323 | AGE | 282 | 0 | 50.0 | 65.0 | 57.09 | 42 |

---

### AGEGP

**Data Type:** object | **Type:** Categorical

**AZ_205** (agegrp) — 5-year intervals
- 65-69: 473 (26.2%)
- 70-74: 461 (25.5%)
- 60-64: 288 (16.0%)
- 75-79: 283 (15.7%)
- 55-59: 144 (8.0%)
- 80-84: 85 (4.7%)
- 50-54: 45 (2.5%)
- 85-89: 19 (1.1%)
- 45-49: 6 (0.3%)
- >=90: 1 (0.1%)

**AZ_229** (AGEGRP & AGEGP) — Two age grouping schemes
- AGEGRP: "65-74 Years" (111), ">=75 Years" (97), "18-64 Years" (58)
- AGEGP: >=70<75 (57), >=75<80 (54), >=65<70 (54), >=80<100 (43), >=60<65 (29), >=45<60 (29)

**Amgen_265** (AGECATCD) — Numeric with text labels
- 1.0 / "< 65 years": 427 (82.1%)
- 2.0 / ">=65 to <75 years": 85 (16.3%)
- 3.0 / ">=75 years": 8 (1.5%)

---

### COUNTRY

**Data Type:** object | **Type:** Categorical

**AZ_229** (COUNTRY) — Decoded full names (24 countries)
- Japan: 38 (15.8%)
- Canada: 30 (12.4%)
- China: 30 (12.4%)
- United States: 20 (8.3%)
- Australia: 14 (5.8%)
- Brazil: 14 (5.8%)
- Belgium: 13 (5.4%)
- India: 13 (5.4%)
- France: 12 (5.0%)
- Czech Republic: 11 (4.6%)
- Korea, Republic of: 11 (4.6%)
- Netherlands: 10 (4.1%)
- United Kingdom: 10 (4.1%)
- Denmark: 9 (3.7%)
- Sweden: 6 (2.5%)

**EMD_221** (COUNTRY) — Numeric codes (32 countries)
- Code 18: 57 (23.6%)
- Code 10: 29 (12.0%)
- Code 2: 24 (9.9%)
- Code 8: 20 (8.3%)
- Code 11: 19 (7.9%)

**Lilly_568** (COUNTRY) — Text
- UNITED STATES: 130 (100.0%)

**Merck_188** (COUNTRY) — ISO 3166-1 alpha-3 codes (32 countries)
- USA: 68 (16.2%)
- POL: 56 (13.3%)
- CAN: 44 (10.5%)
- DEU: 37 (8.8%)
- ESP: 31 (7.4%)
- CZE: 30 (7.1%)
- SWE: 24 (5.7%)
- ROU: 21 (5.0%)
- GBR: 19 (4.5%)
- FRA: 18 (4.3%)
- BRA: 17 (4.0%)
- BEL: 16 (3.8%)
- RUS: 15 (3.6%)
- AUS: 12 (2.9%)
- NLD: 12 (2.9%)

---

### SITEID

**Data Type:** Numeric (with formatting) | **Type:** Site Identifier

| Sponsor | Source Col | Count | Null | Min | Max | Mean | n_unique |
|---------|-----------|-------|------|-----|-----|------|---------|
| AZ_229 | CENT | 266 | 0 | 3003.0 | 3105.0 | 3053.61 | 134 |
| Amgen_265 | SITEID | 520 | 0 | 1101.0 | 4404.0 | 2976.33 | 93 |
| EMD_221 | SITEID | 273 | 0 | 5.0 | 113.0 | 64.73 | 116 |
| Merck_188 | SITEID | 507 | 0 | 3.0 | 184.0 | 97.48 | 187 |

---

### STUDYID

**Data Type:** object | **Type:** Categorical

**All sponsors** — Single unique study identifier per dataset
- AZ_205: CASO0024 (1805 subjects)
- AZ_229: D4320C00014 (266 subjects)
- Amgen_265: 20050251 (520 subjects)
- EMD_221: EMD121974011 (273 subjects)
- Lilly_568: I2V-MC-CXAC (130 subjects)
- Merck_188: EMR63325-001 (507 subjects)

---

### SUBJID / USUBJID

**Data Type:** Mixed (numeric and text) | **Type:** Subject Identifier

**SUBJID (numeric):**
- AZ_205 (trials_d): 1805 unique values (1.0-1242.0)
- AZ_229 (SUBJ): 266 unique values (1.0-183.0)
- Amgen_265: 520 unique values (221101001-223618005)
- Merck_188: 507 unique values (11-493)

**USUBJID (text, fully qualified):**
- EMD_221: Numeric identifiers (1, 175-187)
- Lilly_568: Formatted as STUDYID-SITEID-SUBJID (e.g., "I2V-MC-CXAC-9000-0007")
- Merck_188: Numeric identifiers (1, 336-348)

---

### ARM & ARMCD

**Data Type:** object | **Type:** Categorical

**AZ_229** (ARM: TRTSHORT, ARMCD: TRTCODE)
- Placebo: 266 (100.0%)

**Amgen_265** (ARM: TRT, ARMCD: TRTCD)
- "Panit. plus chemotherapy": 260 (50.0%)
- "Chemotherapy": 260 (50.0%)

**EMD_221** (ARM & ARMCD)
- ARM: "CONTROL GROUP" (273, 100%)
- ARMCD: "CONTRGRP" (273, 100%)

**Lilly_568** (ARM & ARMCD)
- ARM: "LY2510924 Carboplatin/Etoposide(Arm A)": 48 (36.9%)
- ARM: "Carboplatin/Etoposide(Arm B)": 46 (35.4%)
- ARM: "SCREEN FAILURE": 36 (27.7%)

**Merck_188** (ARM & ARMCD)
- ARM: "Placebo": 507 (100.0%)
- ARMCD: "PLACEBO": 507 (100.0%)

---

### BRTHDTC

**Data Type:** object | **Type:** Date (year-only in most cases)

**EMD_221** (BRTHDTC) — Year only (47 unique years)
- 1952: 14, 1948: 13, 1949: 13, 1956: 13, 1951: 12
- Range: 1940-1963

**Lilly_568** (BRTHDTC)
- All blank (130 records)

**Merck_188** (BRTHDTC) — Year only (47 unique years)
- 1944: 28, 1946: 25, 1947: 23, 1949: 22, 1956: 22
- Range: 1941-1962

---

### RFSTDTC & RFENDTC

**Data Type:** object | **Type:** ISO 8601 date/time strings with censoring

**EMD_221** (RFSTDTC)
- Censored: 15 records (50.0%)
- Format: YYYY-MM-DDTHH:MM (2009-2015 range)

**EMD_221** (RFENDTC)
- Censored: 15 records (30.6%)
- Format: YYYY-MM-DD (2010-2011 range)

**Lilly_568** (RFSTDTC & RFENDTC)
- Mostly blank (62.5%-70.2%)
- Dates where present: 2288-2289 year range (data quality issue?)

**Merck_188** (RFSTDTC)
- Censored: 12 records (44.4%)
- Format: YYYY-MM-DDTHH:MM (2009-2015 range)

**Merck_188** (RFENDTC)
- Censored: 92 records (75.4%)
- Format: YYYY-MM-DD (2010-2014 range)

---

### DOMAIN

**Data Type:** object | **Type:** Categorical

Appears in complete datasets only:
- EMD_221: "DM" (273 records)
- Lilly_568: "DM" (130 records)
- Merck_188: "DM" (507 records)

---

### AGEU

**Data Type:** object | **Type:** Categorical

**EMD_221** (AGEU)
- YEARS: 207 (75.8%)
- (blank): 66 (24.2%)

**Lilly_568** (AGEU)
- Years: 130 (100.0%)

**Merck_188** (AGEU)
- YEARS: 507 (100.0%)

---

## 3. Key Observations

### Sponsor-Specific Notable Findings

**AZ_205** (NCT00673205)
- **Missing standard DM variables:** SEX, AGE, COUNTRY, ETHNICITY, SITEID
- **Only 4 target variables found:** STUDYID (PROTID), RACE (ORIGIN), AGEGP (agegrp), SUBJID (trials_d)
- **Age data available only as categorized groups** (10 categories from 45-49 to >=90)
- **Race coded as numeric** (1.0-7.0), with 1709/1805 subjects (94.7%) in code 1.0
- Largest dataset by row count (1,805 subjects)

**AZ_229** (NCT00554229)
- **COUNTRY already decoded to full names** (Japan, Canada, China, USA, Australia, Brazil, Belgium, India, France, Czech Republic, Korea, Netherlands, UK, Denmark, Sweden, etc.)
- **SEX is all "1"** (266/266 subjects) — appears to be all male (likely prostate cancer trial)
- **RACE uses only new code system** (codes 11, 13, 99) with no legacy codes present in data
- Code 11 represents 60.2% of subjects (160/266)
- **Treatment variables:** TRTLONG/TRTSHORT/TRTCODE (all subjects: Placebo)
- **Has SITEID:** 134 unique sites

**Amgen_265** (NCT00460265)
- **SEX available in multiple formats:** SEXCD (numeric: M/F), with human-readable labels also present
- **AGE is numeric float** (not integer), range 50-65 years, mean 57.73
- **RACE still stored as numeric codes** (multiple values, n=6 unique)
- **Multiple treatment arm variables:** TRT/TRTCD (plus ATRT/ATRTCD if available in full dataset)
- **AGECATCD:** 3-level categorization (< 65 years, >=65 to <75, >=75)
- **93 unique SITEIDs**

**EMD_221** (NCT00689221)
- **Most complete dataset:** All 15 standard DM variables present
- **Includes DOMAIN, USUBJID** (and implied SUBJID), reference dates (RFSTDTC/RFENDTC)
- RFSTDTC has 44.4% censored (represented as "\\*\\*\\*\\*\\*\\*")
- RFENDTC has 30.6% censored
- BRTHDTC year-only format (1940-1963 range)
- **116 unique SITEIDs** (1-113 range)
- **Mixed AGEU:** 75.8% "YEARS", 24.2% blank
- Gender nearly balanced (52.4% M, 47.6% F)

**Lilly_568** (NCT01439568)
- **Includes all 15 standard DM variables**
- **US-only study** (COUNTRY: UNITED STATES, 100%)
- **Mostly blank BRTHDTC and reference dates** (70.2% RFENDTC missing)
- **Reference dates with 2288-2289 year values** when present (data quality concern — year out of range)
- **Gender balanced** (51.5% F, 47.7% M, 0.8% blank)
- **No SITEID** in standard dataset (noted as missing)
- Smallest dataset (130 subjects)

**Merck_188** (NCT00409188)
- **Includes all 15 standard DM variables plus SUBJID**
- **507 subjects with 187 unique SITEIDs**
- **BRTHDTC year-only format** (1941-1962 range)
- **Heavily censored reference dates:** RFSTDTC 44.4% censored, RFENDTC 75.4% censored
- **Ethnic codes:** 98 (153 subjects, 57.5%), 10 (39), 9 (36), 8 (24), 1 (14)
- **Multi-country study:** ISO 3166 3-letter codes (USA, POL, CAN, DEU, ESP, CZE, SWE, ROU, GBR, FRA, BRA, BEL, RUS, AUS, NLD, etc.)
- **Gender split:** 68.0% M, 32.0% F
- **AGEU:** All "YEARS" (100%)

**Pfizer_374** (NCT00699374)
- **Severely sparse dataset:** Only AGE variable found (no STUDYID, RACE, SEX, etc.)
- **542 rows with 2 null values** in AGE
- **Age range:** 48-76 years, mean ~61.48
- **63 unique age values** in 542 subjects
- Cannot construct minimal CDISC DM dataset from this source alone

**Sanofi_323** (NCT00401323)
- **Only 3 variables found:** AGE, RACE, SEX
- **282 subjects, predominantly male:** 252/282 (89.4%) male, 30/282 (10.6%) female
- **Predominantly Caucasian:** 257/282 (91.1%), 25/282 (8.9%) other
- **Age range:** 50-65 years, mean ~57.09
- Missing critical variables: STUDYID, SUBJID, SITEID, COUNTRY, treatment arms

---

### Data Quality & Standardization Issues

1. **Variable Completeness:** Highly inconsistent range (1 to 15 variables across sponsors)
   - Minimal: Pfizer (1), Sanofi (3), AZ_205 (4)
   - Moderate: Amgen (9), AZ_229 (10)
   - Complete: EMD, Lilly, Merck (15 variables)

2. **Country Coding:** Three different systems
   - AZ_229: Fully decoded country names
   - EMD_221: Numeric codes (1-32) — requires decoding
   - Merck_188: ISO 3166-1 alpha-3 codes (USA, POL, CAN, etc.)
   - Others: Missing entirely

3. **Sex Encoding:** Inconsistent value sets
   - Numeric: "1" (AZ_229 all-male), "1/2" (legacy)
   - Text: "M"/"F" (Amgen, EMD, Lilly, Merck), "MALE"/"FEMALE" (Sanofi)

4. **Race Coding:** Multiple incompatible systems
   - Numeric old codes: 1.0-7.0 (AZ_205)
   - Numeric new codes: 11, 13, 99 (AZ_229)
   - Text: "WHITE", "ASIAN / PACIFIC ISLANDER", "BLACK OR AFRICAN AMERICAN", "LATINO / HISPANIC", "OTHER" (Merck, Lilly)
   - Text: "CAUCASIAN", "OTHER" (Sanofi)
   - No single code set spans all sponsors

5. **Ethnicity Coding:** Multiple code systems
   - Numeric 1-3: EMD_221
   - Numeric 1, 8, 9, 10, 98: AZ_229
   - Text: "HISPANIC OR LATINO" / "NOT HISPANIC OR LATINO" (Merck)
   - Text: "Hispanic/Latino" / "Non-Hispanic" / "Unknown" (Lilly)
   - Blank/missing in AZ_205, Amgen, Pfizer, Sanofi

6. **Date Formats:** Multiple incompatible formats
   - ISO 8601 with time: "2009-07-18T14:40" (RFSTDTC in EMD, Merck)
   - ISO 8601 date-only: "2012-01-27" (RFENDTC in Merck, Lilly)
   - Year-only: "1944" (BRTHDTC in EMD, Merck)
   - Censored: "\\*\\*\\*\\*\\*\\*" (12-92% of records with dates in EMD, Merck)
   - Invalid years: 2288-2289 (Lilly — data quality issue)
   - Blank/missing: AZ_205, AZ_229, Amgen, Pfizer, Sanofi

7. **Site Identifiers:** Present but with different formats
   - 4-digit numeric with padding: 1101, 3903, 3614 (Amgen: 93 sites, 1101-4404)
   - 2-3 digit numeric: 3, 113 (EMD: 116 sites, 5-113)
   - 3-4 digit numeric with padding: 3003, 3105 (AZ_229: 134 sites)
   - 1-3 digit numeric: 3, 184 (Merck: 187 sites)
   - Inconsistent zero-padding makes direct comparison difficult

8. **Subject Identifiers:** Multiple formats
   - Simple numeric ranges: 1-1805, 1-266 (AZ sponsors)
   - Large numeric IDs: 221101001-223618005 (Amgen, appears to encode site+subject)
   - Qualified format: "I2V-MC-CXAC-9000-0007" (Lilly — STUDYID-SITEID-SUBJID pattern)
   - Missing in several sponsors

9. **Treatment/Arm Variables:** Inconsistent naming and structure
   - Single variables: ARM/ARMCD (most sponsors)
   - Multiple variants: TRT/TRTCD/ATRT/ATRTCD (Amgen), TRTLONG/TRTSHORT/TRTCODE (AZ_229)
   - Some datasets have arm information in columns other than standard ARM/ARMCD

10. **Age Representation:** Mixed numeric and categorical
    - Numeric only: Pfizer, Sanofi, Amgen, EMD, Lilly, Merck (float or int)
    - Categorical only: AZ_205 (5-year ranges, no numeric age)
    - Both: AZ_229 (numeric + multiple age group schemes)
    - **Missing in:** AZ_205, Pfizer, Sanofi (categorical only), Lilly (mostly numeric with null)

---

### Recommendations for Harmonization Spec

- **Establish a unified race/ethnicity code system** (consider CDISC or FDA standards)
- **Define reference code tables** for country codes (recommend ISO 3166-1 alpha-3)
- **Standardize date formats** (ISO 8601 without censoring, or establish censoring protocol)
- **Require STUDYID, SUBJID/USUBJID minimum set** for all source data
- **Site ID formatting:** Zero-pad all numeric codes to consistent width
- **Sex/gender values:** Standardize to single code set (M/F preferred, or 1/2 if numeric)
- **Age units (AGEU):** Standardize to "YEARS" with no blanks
- **Missing/censored dates:** Clarify handling of asterisks and invalid year ranges before harmonization
