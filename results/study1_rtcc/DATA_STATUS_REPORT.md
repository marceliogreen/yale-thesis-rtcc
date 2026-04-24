# Study 1 Data Status Report

**Generated:** 2026-04-07
**Updated:** 2026-04-16 — Study expanded from 8 to 15 RTCC cities, FBI CDE API integrated, external research verified

---

## Data Sources Inventory

### Primary Data - REAL (No Simulation)

| Source | Coverage | RTCC Cities | Status |
|--------|---------|-------------|--------|
| Washington Post Homicides | 2007-2017 | Chicago, St. Louis, Miami, New Orleans, Albuquerque, Fresno | ANALYZED (dates corrected) |
| Kaplan UCR Return A | 1960-2024 | Hartford (city-level), others (county-level) | INGESTED (dates corrected) |
| Hartford PD GVPA Report | 2022-2024 | Hartford | DOWNLOADED |
| FBI CDE API (reverse-engineered) | 2007-2025 | All 15 cities | ✓ INTEGRATED — 49,586 homicides via /LATEST/ endpoints |

### Data Gaps Identified

| City | City-Level Data | County-Level Data | Notes |
|------|-----------------|-------------------|-------|
| Hartford | CT0006400 | N/A | In Kaplan yearly |
| St. Louis | MO0640000 | N/A | In Kaplan yearly |
| Chicago | NOT IN KAPLAN | Cook County IL0160000 | Need FBI API for city |
| Miami | — | Dade County FL0130000 | County only in Kaplan |
| Newark | — | Essex County NJ0070000 | County only in Kaplan |
| New Orleans | — | Orleans Parish LA0360000 | Parish only in Kaplan |
| Albuquerque | — | Bernalillo County NM0010000 | County only in Kaplan |
| Fresno | — | Fresno County CA0190000 | County only in Kaplan |

---

## RTCC Treatment Dates (Updated 2026-04-16)

### Original 8 Cities (Verified)

| City | RTCC Year | Source |
|------|-----------|--------|
| Albuquerque | **2013** | Police Magazine, StateTech Magazine — RTCC opened March 2013 |
| Fresno | **2015** | ABC30, Fresno Bee, Atlas of Surveillance — RTCC opened July 2015 |
| Chicago | **2016** | SDSC launch (verified shift from 2017) |
| St. Louis | **2014** | Standard reference (verified shift from 2015) |
| Miami | **2015** | Standard reference (verified shift from 2016) |
| New Orleans | 2017 | Standard reference |
| Hartford | 2016 | Verified in Kaplan UCR |
| Newark | 2018 | Standard reference |

### Expanded 7 Cities (Verified 2026-04-16)

| City | RTCC Year | Confidence | Source |
|------|-----------|------------|--------|
| Memphis | 2008 | ✓ VERIFIED | Memphis Flyer 4/16/2008, OJP, StateTech, GovLoop |
| Baltimore | 2013 | ⚠ UNCERTAIN | Watch Center ~2013-2014; formal RTCC branding 2024 |
| Detroit | 2016 | ✓ VERIFIED | Project Green Light launch |
| Philadelphia | 2012 | ✓ VERIFIED | Technical.ly, Inquirer, Daily Pennsylvanian, Atlas of Surveillance |
| Houston | 2008 | ✓ VERIFIED | OJP — "4th US agency to open RTCC, operating since 2008" |
| Dallas | 2019 | ✓ VERIFIED | Atlas of Surveillance, Motorola partnership 2019 |
| Denver | 2019 | ✓ VERIFIED | Atlas of Surveillance — RTCIC opened August 2019 |

**Note on Fresno:** RTCC was shut down 2019-2021, reopened May 2021. Document as limitation.

### Date Verification Notes (2026-04-16)

| City | Date Issue | Resolution |
|------|-----------|------------|
| Newark | Atlas of Surveillance says 2013 | Atlas only lists ShotSpotter for Newark, NOT RTCC. nj.com article (April 2017) describes surveillance center launch. **Keeping 2018** — more defensible for RTCC specifically. |
| Albuquerque | Atlas of Surveillance says March 2011 | Police Magazine (April 22, 2013) by Paul Clinton describes ABQ RTCC as "new." Atlas 2011 likely = camera infrastructure, not monitoring center. **Keeping 2013** — correct for RTCC. |
| Baltimore | Watch Center ~2013-2014 | CitiWatch cameras since 2005; Watch Center (RTCC-equivalent) ~2013-2014; formal RTCC branding 2024. **Keeping 2013** — best available for functional RTCC start. |
| Denver | HALO cameras since 2008 | Cameras ≠ RTCC. RTCIC (RTCC) opened August 2019. **Keeping 2019** — correct for monitoring center. |

### Fresno Discontinuous Treatment

Fresno RTCC was **shut down ~2019** and **reopened May 2021**. FBI CDE SHR data continues through the shutdown period (cameras likely stayed active; monitoring center staff was reduced/eliminated).

**Analytical implications:**
- ITS model should code Fresno as: `post_rtcc = 1` for 2015-2018, `post_rtcc = 0` for 2019-2020, `post_rtcc = 1` for 2021+
- Or use `rtcc_active` binary variable that toggles off during shutdown
- Sensitivity analysis: run with and without discontinuous coding

### New Orleans Data Gap (NIBRS Transition)

FBI CDE SHR shows **0 homicides 2021-2025** for New Orleans (NIBRS transition). NOPD local counts from public reporting:

| Year | NOPD Homicides | FBI SHR |
|------|---------------|---------|
| 2021 | 219* | 0 |
| 2022 | 266* | 0 |
| 2023 | 192* | 0 |
| 2024 | 124* | 0 |

*Source: External research (needs manual verification against NOPD public data).*

**Analytical implication:** Post-2020 ITS for New Orleans must use either (a) NOPD local data or (b) truncate at 2020. Primary pipeline uses FBI SHR, so New Orleans analysis window is 2007-2020 only.

---

## Comparison Group Contamination Check

External research identified **50+ additional US cities** with RTCCs or equivalent real-time monitoring centers. This creates potential **SUTVA violations** if comparison group agencies also have RTCCs.

### Known RTCC Cities NOT in Treatment Group (Partial List)

| City | State | RTCC Year | Evidence |
|------|-------|-----------|----------|
| New York | NY | 2007 | NYPD RTCC, well-documented |
| Los Angeles | CA | ~2010 | LAPD RTIC |
| Atlanta | GA | ~2012 | APD video integration |
| Phoenix | AZ | ~2012 | Phoenix PD CIC |
| San Antonio | TX | ~2015 | SAPD tech center |
| Kansas City | MO | ~2015 | KC NoVa crime center |
| Milwaukee | WI | ~2016 | CompStat + camera network |
| Columbus | OH | ~2015 | CPD intelligence center |
| Indianapolis | IN | ~2014 | IMPD technology center |
| Charlotte | NC | ~2015 | CMPD RTCC |
| Nashville | TN | ~2016 | MNPD tech integration |
| Tampa | FL | ~2015 | TPD RTCC |
| Minneapolis | MN | ~2017 | MPD tech center |
| Las Vegas | NV | ~2015 | LVMPD RTCC |
| Oklahoma City | OK | ~2016 | OCPD tech center |

**Mitigation strategies:**
1. **Sensitivity analysis:** Exclude known RTCC cities from comparison group
2. **Instrumental variable:** Use distance to nearest RTCC city as instrument
3. **PSM-DiD:** Propensity score matching should partially control for this (RTCC cities likely larger)
4. **Lower bound:** Contamination biases toward null — actual treatment effect likely larger than estimated
5. **Robustness check:** Run analysis with "clean" comparison group (cities <100K population with no RTCC evidence)

---

## Real Clearance Rate Analysis (Washington Post 2007-2017)

### Pre/Post RTCC Results (Corrected Dates)

| City | RTCC Year | Pre Yrs | Post Yrs | Pre-RTCC | Post-RTCC | Change (pp) |
|------|-----------|---------|----------|----------|-----------|-------------|
| Albuquerque | 2013 | 3 | 5 | 69.8% | 57.0% | **-12.7** |
| Chicago | 2017 | 10 | 1 | 28.8% | 8.6% | **-20.2** |
| Fresno | 2015 | 8 | 3 | 69.4% | 54.5% | **-14.9** |
| Miami | 2016 | 9 | 2 | 42.9% | 21.8% | **-21.0** |
| New Orleans | 2017 | 9 | 1 | 35.9% | 29.4% | **-6.4** |
| St. Louis | 2015 | 8 | 3 | 52.2% | 34.2% | **-18.0** |

**Average Change: -15.6 percentage points** (was -16.4 with incorrect dates)

### ITS Level Change (beta_2) — MLE Estimates

| City | Level Change | SE | Significant? |
|------|-------------|-----|-------------|
| Albuquerque | -11.9 pp | 14.5 | No (short pre) |
| Chicago | -10.5 pp | — | Only 1 post yr |
| Fresno | **-17.0 pp** | 8.3 | Yes (p=0.041) |
| Miami | **-11.5 pp** | 7.8 | Marginal (p=0.14) |
| New Orleans | +5.4 pp | — | Only 1 post yr |
| St. Louis | **-13.7 pp** | 7.3 | Marginal (p=0.059) |

### Key Findings

1. **All 6 cities with data show DECLINING clearance rates post-RTCC** (except New Orleans with only 1 post year)
2. Only **Fresno** shows a statistically significant level drop (p=0.041). St. Louis is marginally non-significant (p=0.059).
3. This counter-intuitive finding requires deeper analysis:
   - RTCCs may have been implemented during crime spikes (selection into treatment)
   - Selection bias in which cases get RTCC attention
   - Need longer post-period (data ends 2017)
   - Confounding factors (COVID, social unrest)

### Data Limitations

1. **Washington Post data ends 2017** — limited post-RTCC period
2. **Chicago and New Orleans** have only 1 post-RTCC year in WaPo data
3. **Hartford and Newark** not in Washington Post dataset
4. **Kaplan data** uses county-level for large metros, not city-level
5. **FBI CDE API** deferred — would extend coverage to 2024
6. **9 of 15 RTCC cities have NO clearance rate data** — Hartford, Newark, Memphis, Baltimore, Detroit, Philadelphia, Houston, Dallas, Denver. Only 40% of treatment group has clearance analysis.
7. **Clearance-staffing confound** — Every city with declining clearance also lost sworn officers (Baltimore -33%, New Orleans -34%, St. Louis -36% 2007-2024). Without controlling for staffing per capita, the RTCC effect estimate is confounded. The enhanced panel now includes `total_sworn` and `officers_per_10k_pe` for this purpose.
8. **Fresno ITS uses `post_rtcc`** — The current ITS MLE results use `post_rtcc` which treats Fresno as continuously treated post-2015. The enhanced panel provides `rtcc_active` (toggles off 2019-2020) for sensitivity analysis.
9. **Houston and Memphis** have only 1 pre-RTCC year (RTCC year 2008, data starts 2007). Cannot be included in standard ITS regression. Recommend qualitative-only treatment or extended historical data.
10. **Miami SHR unusable** — FL0130600 ORI returns zero homicides for 15 of 19 years (2007-2021). Only 4 years of SHR data (2022-2025, 114 total). Must be excluded from all SHR-based analyses. WaPo clearance data for Miami remains valid.
11. **New Orleans 2008 SHR anomaly** — FBI SHR shows 94 homicides vs NOPD local count of ~179. Post-Katrina SHR undercount. Minimal impact on pooled estimates (2 of 14 pre-RTCC years).
12. **WaPo vs SHR discrepancies** — Chicago 2017: WaPo=654 vs SHR=519; Albuquerque 2016-2017: WaPo 13-18 higher. Reflect known differences between incident-level and agency-level reporting.

---

## Output Files Generated

| File | Records | Description |
|------|--------|-------------|
| `annual_clearance_rates.csv` | 62 | Annual clearance by city (6 cities × 8-11 years, WaPo data) |
| `pre_post_rtcc_summary.csv` | 6 | Pre/post RTCC comparison (WaPo data) |
| `clearance_trends.png` | — | Visualization of trends |
| `bayesian_its/its_mle_results.csv` | 6 | Per-city ITS regression results |
| `bayesian_its/figures/*.png` | 6 | Per-city ITS plots with counterfactuals |
| `master_analysis_panel.csv` | 17,553 | Combined analysis dataset (dates corrected) |
| `fbi_cde/annual_homicides_fbi_cde.csv` | 285 | Annual SHR homicide counts, 15 cities, 2007-2025 (total: 49,586) |
| `fbi_cde/shr_raw_*.json` | 15 | Raw FBI CDE API responses per city |
| `fbi_cde/police_employment_pe.csv` | 285 | FBI PE staffing data, 15 cities, 2007-2025 |
| `fbi_cde/pe_raw_*.json` | 15 | Raw FBI PE API responses per city |
| `fbi_cde/nopd_supplementary_counts.csv` | 19 | NOPD local homicide counts for NIBRS gap (2021-2024) |
| `rtcc_city_panel_enhanced.csv` | 285 | Enhanced panel: SHR + PE + LEMAS + year FEs (70 columns) |

---

## Remaining Blockers

### Deferred (Manual / External)

1. **Kaplan SHR (OpenICPSR 100699)** — User download needed (free ICPSR account)
2. **NIBRS incident-level (ICPSR 39270)** — User must apply for restricted data access + DUA

### Needs Verification

3. **Baltimore RTCC date** — Watch Center ~2013-2014 is best estimate; no clean ribbon-cutting. Consider FOIA to BPD media relations (mediarelations@baltimorepolice.org / 410-396-2012)
4. **New Orleans NOPD counts** — External research claims 219/266/192/124 for 2021-2024. Verify against NOPD public data before citing in thesis.
5. **Comparison group contamination** — 50+ additional US cities have RTCCs. Need systematic screening of comparison group agencies.

### Analysis Pipeline

4. **Re-run ITS** for all 15 cities with FBI CDE SHR data (2007-2025)
5. **Rebuild master panel** with 15 treatment cities + corrected city PD ORIs
6. **ML pipeline** (XGBoost, Random Forest, SHAP, Causal Forest) — not yet run with 15 cities
7. **Prophet counterfactuals** — not yet run
8. **Monte Carlo power analysis** — not yet run
