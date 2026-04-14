# RTCC Effectiveness Research - Data Collection Summary

**Date:** March 31, 2026
**Purpose:** Document all available data sources and findings on RTCC effectiveness

---

## ⚠️ CRITICAL DATA LIMITATIONS

**Primary Data Source (Washington Post Homicide Dataset):**
- Coverage: 2007-2017 **only**
- Ends BEFORE/shortly after most RTCC implementations
- Missing 5-8 years of critical post-implementation data
- This makes ANY definitive conclusion premature

---

## What the Data Actually Shows

### Cities with Declining Trends (often starting BEFORE RTCC)

| City | RTCC Year | Key Finding |
|------|-----------|-------------|
| **Chicago** | 2017 | Clearance declined from 31% (2010) to 14.4% (2016) BEFORE RTCC. 2017: 8.6% |
| **St. Louis** | 2015 | Decline from 60% (2011) to 41% (2014) BEFORE RTCC. Post-RTCC: 35% |
| **Miami** | 2016 | Decline from 51% (2010) to 33% (2014) BEFORE RTCC. Post-RTCC: 20-24% |
| **New Orleans** | 2017 | 2016: 26.7% → 2017: 29.4% (+2.7%) |

### Cities with High Clearance Rates (above national avg ~50%)

| City | Average (2010-2017) | Note |
|------|----------------------|------|
| **Fresno** | 71.1% | Well above national average |
| **Albuquerque** | 63.0% | Well above national average |
| **St. Louis (2011)** | 60.2% | Peak year, before decline |

---

## 🔍 Research Gaps - What We Need to Find

### Academic Studies on RTCC Effectiveness

| Question | Status | Notes |
|----------|--------|-------|
| Peer-reviewed studies on RTCC impact? | ⏳ | Need literature search |
| Municipal RTCC evaluation reports? | ⏳ | Check city websites |
| NIJ/DOJ funded evaluations? | ⏳ | Search justice.gov |
| RAND/Urban Institute studies? | ⏳ | Search think tanks |
| Police foundation evaluations? | ⏳ | Check Police Foundation |

### Missing Data

| Data Type | Years Needed | Source |
|-----------|--------------|--------|
| Post-2017 clearance rates | 2018-2024 | ICPSR 39066, Jacob Kaplan |
| Hartford/Newark data | All years | Not in Washington Post dataset |
| Vendor evaluation reports | Various | Motorola, ShotSpotter, etc. |

---

## 📊 National Context (Critical)

**National Homicide Clearance Rate Timeline:**
- 1960s: ~90%
- 1980s: ~70%
- 1990s: ~65%
- 2000s: ~60%
- 2010s: ~60%
- **Today: ~50-52%**

This multi-decade decline affects ALL cities, regardless of RTCC implementation.

---

## 🔬 What Would Constitute Valid Evidence?

To properly evaluate RTCC effectiveness, we need:

1. **Pre/post with adequate follow-up:** Minimum 5 years post-implementation
2. **Comparison group:** Similar cities without RTCC
3. **Controls for:**
   - Overall crime trends
   - Staffing levels
   - Budget changes
   - Other technology implementations
4. **Multiple outcome measures:**
   - Clearance rates (primary)
   - Response times
   - Case closure rates
   - Citizen satisfaction

---

## 📌 Current Data Status

| Source | Coverage | Limitation |
|--------|----------|------------|
| Washington Post | 2007-2017, 52K records | Ends before most RTCCs matured |
| Chicago Socrata | 2010-2023 | Chicago only |
| FBI CDE API | None | **Service retired** |
| ICPSR 39066 | 2022 | Need download |
| Jacob Kaplan | 1960-2024 | Need download |

---

## 🎯 Next Steps for Proper Analysis

1. **Download ICPSR 39066** - UCR clearance data for Hartford/Newark
2. **Download Jacob Kaplan** - Extended timeline (2018-2024)
3. **Literature review** - Find peer-reviewed RTCC studies
4. **Synthetic control method** - Build proper comparison group
5. **Interrupted time series** - Control for pre-existing trends

---

## ⚖️ Balanced Summary

The Washington Post data (2007-2017) is **insufficient** to determine RTCC effectiveness because:

1. **Data ends too early** - Most RTCCs implemented 2015-2018, data ends 2017
2. **Declining trends preceded RTCC** - Most cities showed declining clearance BEFORE RTCC
3. **Missing post-implementation period** - Need 2018-2024 data to see actual effects
4. **No control group** - Can't distinguish RTCC effects from national trends
5. **Confounding factors** - 2016 homicide spike in Chicago occurred BEFORE RTCC

**Neither "RTCCs work" nor "RTCCs fail" can be concluded from current data.**

---

## Sources Documented

1. Washington Post Homicide Dataset - https://github.com/washingtonpost/data-homicides
2. Chicago Data Portal - https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2
3. ICPSR 39066 - https://www.icpsr.umich.edu/web/NACJD/studies/39066
4. Jacob Kaplan Data - https://www.openicpsr.org/openicpsr/project/100707/version/V22/view
5. UCR Book - https://ucrbook.com/
6. FBI CDE API - **Retired** (confirmed via GitHub issues)

---

**Status:** EXPLORATORY ANALYSIS ONLY - NOT READY FOR CONCLUSIONS
