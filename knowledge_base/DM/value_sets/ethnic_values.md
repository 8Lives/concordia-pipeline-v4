# Value Set: ETHNIC

**Version:** 1.1
**Last Updated:** 2026-04-09
**Status:** Draft — SME review required
**CDISC CT Reference:** C66790
**Controlling Standard:** OMB Revised Standards (1997)

## Allowed Target Values

| Value | Definition | CDISC CT Code |
|-------|-----------|---------------|
| Hispanic or Latino | Subject identifies as Hispanic or Latino | C17459 |
| Not Hispanic or Latino | Subject does not identify as Hispanic or Latino | C41222 |
| Unknown | Missing, refused, not collected, or not interpretable | C17998 |

## Known Source Synonyms

| Source Value | Maps To | Confidence | Notes |
|-------------|---------|------------|-------|
| Hispanic or Latino | Hispanic or Latino | HIGH | Direct match |
| Hispanic, Latino, Latina, Latinx | Hispanic or Latino | HIGH | Common forms |
| Mexican, Puerto Rican, Cuban, Central American, South American | Hispanic or Latino | HIGH | Sub-category roll-up |
| 8 (AZ_229 ETHGRP) | Hispanic or Latino | HIGH | Dictionary decode: 8=Hispanic/Latin American |
| Not Hispanic or Latino | Not Hispanic or Latino | HIGH | Direct match |
| Non-Hispanic, Not Hispanic | Not Hispanic or Latino | HIGH | Common forms |
| 1 (AZ_229 ETHGRP) | Unknown | MEDIUM | Dictionary decode: 1=White. Race value, not ethnicity; route to RACE. |
| 9 (AZ_229 ETHGRP) | Unknown | MEDIUM | Dictionary decode: 9=East Asian. Race value, not ethnicity; route to RACE. |
| 10 (AZ_229 ETHGRP) | Unknown | MEDIUM | Dictionary decode: 10=SE Asian. Race value, not ethnicity; route to RACE. |
| 98 (AZ_229 ETHGRP) | Unknown | HIGH | Dictionary decode: 98=Other/de-identified |
| Prefer not to say, Declined | Unknown | HIGH | Explicit non-disclosure |
| NULL, "", N/A, Not Reported | Unknown | HIGH | Standard missing |
| *(field absent from source)* | Unknown | UNMAPPED | No source data |

## Notes

- AZ_229 ETHGRP is a 12-category "ethnic group" field that conflates race and ethnicity. Only code 8 (Hispanic/Latin American) maps to ETHNICITY. All other codes are race data and should inform the RACE variable, not ETHNICITY.
- Absence of a "Hispanic" indicator is NOT evidence of "Not Hispanic or Latino." Only explicit negative responses should map to "Not Hispanic or Latino."

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial draft |
| 1.1 | 2026-04-09 | Cleaned annotated synonyms: Maps To column now uses clean canonical values; annotations moved to Notes column. Renamed from ethnicity_values.md to ethnic_values.md to align with ETHNIC variable name. |
