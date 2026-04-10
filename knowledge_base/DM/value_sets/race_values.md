# Value Set: RACE

**Version:** 1.1
**Last Updated:** 2026-04-09
**Status:** Draft — SME review required
**CDISC CT Reference:** C74457
**Controlling Standard:** OMB Revised Standards (1997), Federal Register 62 FR 58782

## Allowed Target Values

| Value | Definition | CDISC CT Code |
|-------|-----------|---------------|
| White | Origins in Europe, Middle East, or North Africa | C41261 |
| Black or African American | Origins in any of the Black racial groups of Africa | C16352 |
| Asian | Origins in the Far East, Southeast Asia, or the Indian subcontinent | C41260 |
| American Indian or Alaska Native | Origins in original peoples of North/South America with tribal affiliation | C41259 |
| Native Hawaiian or Other Pacific Islander | Origins in Hawaii, Guam, Samoa, or other Pacific Islands | C41219 |
| Multiple | More than one race reported | C67236 |
| Unknown | Missing, refused, not collected, de-identified, or unresolvable | C17998 |

## Known Source Synonyms

| Source Value | Maps To | Confidence | Notes |
|-------------|---------|------------|-------|
| White, white, WHITE | White | HIGH | |
| Caucasian | White | HIGH | Common synonym |
| 1 (AZ_205 ORIGIN) | White | HIGH | Dictionary decode: 1=Caucasian |
| 11 (AZ_229 RACE new code) | White | HIGH | Post-2006 code |
| Black, BLACK | Black or African American | HIGH | |
| Black or African American | Black or African American | HIGH | |
| Afro-Caribbean | Black or African American | HIGH | AZ_205 code 2 |
| African American, AA | Black or African American | HIGH | |
| 2 (AZ_205 ORIGIN) | Black or African American | HIGH | Dictionary decode: 2=Afro-Caribbean |
| Asian, ASIAN | Asian | HIGH | |
| Chinese, Japanese, Korean, Filipino, Vietnamese | Asian | HIGH | Detail roll-up |
| Indian (South Asian context) | Asian | HIGH | OMB classification |
| 3 (AZ_205 ORIGIN) | Asian | HIGH | |
| 13 (AZ_229 RACE new code) | Asian | HIGH | |
| Asian / Pacific Islander | Asian | MEDIUM | Compound category; split if source distinguishes NHOPI vs. Asian. Default to Asian if no further detail. |
| Oriental | Asian | MEDIUM | Outdated term |
| 5 (AZ_205 ORIGIN) | Asian | MEDIUM | Dictionary decode: 5=Oriental (outdated term) |
| American Indian, Alaska Native, Native American | American Indian or Alaska Native | HIGH | |
| Native Hawaiian, Samoan, Guamanian, Chamorro | Native Hawaiian or Other Pacific Islander | HIGH | |
| Mixed, Two or More Races, Multiracial | Multiple | HIGH | |
| 6 (AZ_205 ORIGIN) | Multiple | HIGH | Dictionary decode: 6=Mixed |
| Latino / Hispanic (in race field) | Unknown | MEDIUM | Not a race per OMB; extract to ETHNICITY. Set ETHNIC = "Hispanic or Latino". |
| Hispanic (in race field) | Unknown | MEDIUM | Not a race per OMB; extract to ETHNICITY. Set ETHNIC = "Hispanic or Latino". |
| 4 (AZ_205 ORIGIN) | Unknown | MEDIUM | Dictionary decode: 4=Hispanic. Conflated race/ethnicity; extract to ETHNICITY. |
| Other (no free-text) | Unknown | MEDIUM | Unresolvable without accompanying free-text |
| 7 (AZ_205 ORIGIN) | Unknown | MEDIUM | Dictionary decode: 7=Other |
| 99 (AZ_229 de-identified) | Unknown | HIGH | Explicit de-ID |
| NULL, "", Not Reported, Declined | Unknown | HIGH | Standard missing |

## Notes

- OMB is reviewing a potential MENA (Middle Eastern/North African) category. If adopted, White definition will narrow and a new category will be needed.
- "Hispanic" or "Latino / Hispanic" appearing in a race field triggers the race/ethnicity separation logic in the RACE variable spec. The value is extracted to ETHNICITY and RACE is set to Unknown.
- "Asian / Pacific Islander" is a pre-1997 OMB compound category still found in older datasets (e.g., Merck_188). Default mapping is to Asian. If the source provides additional detail distinguishing Native Hawaiian or Other Pacific Islander subjects, split accordingly.

## Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-04-08 | Initial draft |
| 1.1 | 2026-04-09 | Cleaned annotated synonyms: Maps To column now uses clean canonical values; annotations moved to Notes. Added compound categories "Asian / Pacific Islander" and "Latino / Hispanic" as known source synonyms. |
