# Study 1 Data Status Report

**Generated:** 2026-04-07

---

## Data Sources Inventory

### Primary Data - REAL (No Simulation)

| Source | Coverage | RTCC Cities | Status |
|--------|---------|-------------|--------|
| Washington Post Homicides | 2007-2017 | Chicago, St. Louis, Miami, New Orleans, Albuquerque, Fresno | ✅ ANALYZED |
| Kaplan UCR Return A | 1960-2024 | Hartford (city-level), others (county-level) | ✅ INGESTED |
| Hartford PD GVPA Report | 2022-2024 | Hartford | ✅ DOWNLOADED (demographics, not clearance) |
| FBI CDE API | Current | All 8 cities | ✅ KEY ACTIVE |

### Data Gaps Identified

| City | City-Level Data | County-Level Data | Notes |
|------|-----------------|-------------------|-------|
| Hartford | ✅ CT0006400 | N/A | In Kaplan yearly |
| St. Louis | ✅ MO0640000 | N/A | In Kaplan yearly |
| Chicago | ⚠️ NOT IN KAPLAN | Cook County IL0160000 | Need FBI API for city |
| Miami | ❌ | Dade County FL0130000 | County only in Kaplan |
| Newark | ❌ | Essex County NJ0070000 | County only in Kaplan |
| New Orleans | ❌ | Orleans Parish LA0360000 | Parish only in Kaplan |
| Albuquerque | ❌ | Bernalillo County NM0010000 | County only in Kaplan |
| Fresno | ❌ | Fresno County CA0190000 | County only in Kaplan |

---

## Real Clearance Rate Analysis (Washington Post 2007-2017)

### Pre/Post RTCC Results

| City | RTCC Year | Pre-RTCC Clearance | Post-RTCC Clearance | Change (pp) |
|------|-----------|-------------------|---------------------|-------------|
| Chicago | 2017 | 28.8% | 8.6% | **-20.2** |
| Miami | 2016 | 42.9% | 21.8% | **-21.0** |
| New Orleans | 2017 | 35.9% | 29.4% | **-6.4** |
| St. Louis | 2015 | 52.2% | 34.2% | **-18.0** |

**Average Change: -16.4 percentage points**

### Key Findings

1. **All 4 cities with pre/post data show DECLINING clearance rates post-RTCC**
2. This counter-intuitive finding requires deeper analysis:
   - RTCCs may have been implemented during crime spikes
   - Selection bias in which cases get RTCC attention
   - Need longer post-period (data ends 2017, only 1-2 years post for some cities)
   - Confounding factors (COVID, social unrest)

### Data Limitations

1. **Washington Post data ends 2017** - Limited post-RTCC period
2. **Albuquerque (RTCC 2020) and Fresno (RTCC 2018)** have NO post-RTCC data in Washington Post
3. **Hartford and Newark** not in Washington Post dataset
4. **Kaplan data** uses county-level for large metros, not city-level

---

## Output Files Generated

| File | Records | Description |
|------|--------|-------------|
| `results/study1_rtcc/annual_clearance_rates.csv` | 24 | Annual clearance by city (6 cities × years) |
| `results/study1_rtcc/pre_post_rtcc_summary.csv` | 4 | Pre/post RTCC comparison |
| `results/study1_rtcc/clearance_trends.png` | - | Visualization of trends |
| `thesis/data/rtcc_cities_yearly.csv` | 390 | Kaplan data for RTCC cities |
| `thesis/data/comparison_pool_yearly.csv` | 17,163 | Mid-sized city comparison pool |
| `thesis/data/master_analysis_panel.csv` | 17,553 | Combined analysis dataset |

---

## Next Steps Required

### High Priority

1. **Obtain NIBRS Extract Files (ICPSR 39270)** - Incident-level clearance data with city identifiers
2. **Download Kaplan SHR (OpenICPSR 100699)** - Supplementary Homicide Reports with solved/unsolved status
3. **Use FBI CDE API** - Pull current homicide/clearance data for all 8 cities

### Medium Priority

4. **Extend Washington Post analysis** - Find updated homicide data (2018-2024)
5. **Hartford-specific analysis** - Use Kaplan data (CT0006400) for longitudinal Hartford analysis
6. **Press release scraping** - Qualitative context for RTCC implementation dates

### For Discussion with Advisor

- Counter-intuitive finding: clearance rates declined post-RTCC
- Need to address selection bias and confounding
- Extend analysis period beyond 2017
- Consider synthetic control methods (Causal Forest)
