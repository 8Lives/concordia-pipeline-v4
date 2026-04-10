# Value Set: COUNTRY

**Version:** 1.0
**Last Updated:** 2026-04-08
**Status:** Draft — SME review required for preferred name forms
**Reference Standard:** ISO 3166-1

## Allowed Target Values

Country names per ISO 3166-1, presented in mixed case. This is not an exhaustive list — any valid ISO 3166-1 country is an allowed value. The table below documents countries observed in the prototype data and common variations that require normalization.

## Observed Countries (from AZ_229 — the only prototype dataset with decoded COUNTRY)

| Target Value | ISO Alpha-3 | ISO Alpha-2 | Frequency (AZ_229) |
|-------------|------------|------------|-------------------|
| Japan | JPN | JP | 38 |
| Canada | CAN | CA | 30 |
| China | CHN | CN | 30 |
| United States | USA | US | 20 |
| Australia | AUS | AU | 14 |
| Brazil | BRA | BR | 14 |
| Belgium | BEL | BE | 13 |
| India | IND | IN | 13 |
| France | FRA | FR | 12 |
| Czech Republic | CZE | CZ | 11 |
| South Korea | KOR | KR | 11 |
| Netherlands | NLD | NL | 10 |
| United Kingdom | GBR | GB | 10 |
| Denmark | DNK | DK | 9 |
| Sweden | SWE | SE | 6 |
| Taiwan | TWN | TW | 5 |
| Russia | RUS | RU | 4 |
| Poland | POL | PL | 3 |
| Hungary | HUN | HU | 3 |
| Finland | FIN | FI | 3 |
| Argentina | ARG | AR | 2 |
| Germany | DEU | DE | 2 |
| Norway | NOR | NO | 1 |
| Peru | PER | PE | 1 |
| Thailand | THA | TH | 1 |

## Name Normalization *(SME review required for preferred forms)*

| Source Variation | Target (Preferred Form) | Notes |
|-----------------|------------------------|-------|
| US, USA, United States of America | United States | Most common short form |
| UK, GBR, Great Britain, England | United Kingdom | ISO standard name |
| Korea, Republic of | South Korea | Common usage form. *(SME: confirm)* |
| Korea, Democratic People's Republic of | North Korea | Uncommon in clinical trials |
| Russian Federation | Russia | Common usage form. *(SME: confirm)* |
| Czechia | Czech Republic | Both are valid ISO names. *(SME: pick one)* |
| Taiwan, Province of China | Taiwan | ISO formal name includes qualifier. *(SME: confirm)* |
| Holland | Netherlands | Common informal name |
| Burma | Myanmar | Historical name |
| Swaziland | Eswatini | Name changed 2018 |

## Notes

- Missing value for COUNTRY is "Unknown" per the standard system rule.
- Country data in most prototype datasets is coded and requires data dictionary decoding. Only AZ_229 has pre-decoded country names.
- CDISC SDTM uses ISO 3166-1 alpha-3 codes (e.g., "USA"). Concordia uses full names for readability; the ISO code can be derived from the target value.
