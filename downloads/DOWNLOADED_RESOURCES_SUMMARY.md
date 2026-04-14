# RTCC Research - Downloaded Resources Summary

**Date:** March 31, 2026
**Purpose:** Master list of all RTCC effectiveness research materials downloaded

---

## PDF Resources Downloaded (5 files, ~5.8MB)

| File | Size | Pages | Source | Key Content |
|------|------|-------|--------|-------------|
| `FIU_RTCC_Policing.pdf` | 2.9MB | 264 | FIU Digital Commons | RTCC configurations, functions, impact on practices |
| `RAND_Chicago_RTCC.pdf` | 3.2MB | 98 | RAND Corporation | Chicago SDSC evaluation, 3-17% crime reduction |
| `Chicago_RTCC_Clearance.pdf` | 650KB | 8 | Journal of Criminal Justice | Arietti 2024: +11% overall, +5% violent clearance |
| `NIJ_RTCC.pdf` | 42KB | - | National Institute of Justice | RTCC definition, activities, implementation |
| `UCF_RTCC_Thesis.pdf` | 932KB | - | UCF STARS Repository | Law enforcement motivations for RTCCs |

**Total:** 5 PDFs, ~5.8MB

---

## Key Findings Extracted

### Positive Evidence for RTCC Effectiveness

1. **Guerette & Przeszlowski (2023)** - Miami RTCC
   - 66% greater odds of clearance for RTCC-assisted cases
   - Sample: 648 violent crime cases
   - Journal: Justice Quarterly

2. **Arietti (2024)** - Chicago SDSCs
   - +11% overall crimes cleared (p<0.001)
   - +5% violent crimes cleared (p<0.01)
   - +12% property crimes cleared (p<0.01)
   - Journal: Journal of Criminal Justice 90

3. **Guerette et al. (2025)** - Miami Extended Evaluation
   - Extended 5+ year evaluation
   - RTCC effectiveness improved over time
   - Journal: Justice Evaluation Journal

4. **Hollywood et al. (2019)** - RAND Chicago
   - 3-17% crime reduction across districts
   - $10.6M setup + $600K annual cost

### Limitations Found

- No significant improvement in **conviction rates** (Guerette et al., 2025)
- Case adjudication unchanged despite improved clearances
- Most studies focus on clearance (arrests) rather than convictions
- Limited cost-benefit analysis data
- Few studies on disproportionate community impacts

---

## Academic Sources Identified (10 total)

| # | Title | Journal | Year | Status |
|---|-------|---------|------|--------|
| 1 | Extended Impact Evaluation of RTCC Technologies | Justice Evaluation Journal | 2025 | Paywall |
| 2 | Does Rapid Deployment Improve Crime Solvability? | Justice Quarterly | 2023 | Paywall |
| 3 | Do RTCCs improve case clearance? (Chicago) | Journal of Criminal Justice | 2024 | ✓ Downloaded |
| 4 | Real Time Crime Centers in Chicago | RAND Corporation | 2019 | ✓ Downloaded |
| 5 | RTCCs as Frontiers of Technology in Policing | FIU Dissertation | 2023 | ✓ Downloaded |
| 6 | Centralization of police IT | Police Quarterly | 2022 | Paywall |
| 7 | Documenting growth of RTCCs | FBI Law Enforcement Bulletin | 2023 | Paywall |
| 8 | Law enforcement motivations for RTCCs | UCF Thesis | 2020 | ✓ Downloaded |
| 9 | Real-Time Crime Centers info | NIJ | 2024 | ✓ Downloaded |
| 10 | RTCC integrating technology | CJTTec | 2025 | ✓ Scraped |

---

## Data Sources for Thesis Analysis

### Primary Sources (Real Data Available)
1. **FBI Crime Data Explorer API** - Homicide counts by ORI
2. **BJS NIBRS API** - Clearance rates by agency
3. **ICPSR 39069** - Supplementary Homicide Reports
4. **ICPSR 39063** - Arrests by Age/Sex/Race

### RTCC Treatment Cities (8 cities)
| City | State | ORI | RTCC Year |
|------|-------|-----|-----------|
| Hartford | CT | CT0030100 | 2016 |
| Miami | FL | FL0130200 | 2016 |
| St. Louis | MO | MO0640000 | 2015 |
| Newark | NJ | NJ0071400 | 2018 |
| New Orleans | LA | LA0360000 | 2017 |
| Albuquerque | NM | NM0010100 | 2020 |
| Fresno | CA | CA0190200 | 2018 |
| Chicago | IL | IL0160000 | 2017 |

### Comparison Pool
- Target: 371 mid-sized agencies (100K-300K population)
- Excludes: 8 RTCC treatment cities
- Years: 2010-2023

---

## Next Steps for Thesis Research

### 1. Full-Text Access Needed
- Guerette et al. (2025) Justice Evaluation Journal - **critical**
- Guerette & Przeszlowski (2023) Justice Quarterly
- Police Quarterly (2022) centralization study

### 2. Data to Extract from Papers
- Effect sizes (odds ratios, confidence intervals)
- Pre/post RTCC clearance rates
- Methodological approaches (synthetic control? ITS?)
- Time frames analyzed

### 3. API Integration Required
- Register for FBI CDE API key
- Register for ICPSR Researcher Passport
- Set up BJS NIBRS API access

### 4. Gaps to Address
- Conviction rates vs clearance rates
- Cost-benefit analysis
- Community impact assessment
- Long-term sustainability of effects

---

## Files Created

```
yale-thesis-rtcc/
├── downloads/
│   ├── RTCC_EFFECTIVENESS_RESEARCH.md  (comprehensive literature review)
│   └── DOWNLOADED_RESOURCES_SUMMARY.md (this file)
└── scraping-tools/
    ├── scraped_content/
    │   ├── FIU_RTCC_Policing.pdf (2.9MB)
    │   ├── RAND_Chicago_RTCC.pdf (3.2MB)
    │   ├── Chicago_RTCC_Clearance.pdf (650KB)
    │   ├── NIJ_RTCC.pdf (42KB)
    │   ├── UCF_RTCC_Thesis.pdf (932KB)
    │   ├── cjttec.md (scraped content)
    │   ├── scrape_summary.json
    │   └── source_availability.json
    ├── academic_sources.json
    ├── rtcc_scraper.py
    ├── scrape_sources.py
    ├── find_academic_sources.py
    └── find_open_access.py
```

---

**Status:** Literature review substantially complete with 4 key studies finding positive RTCC effects on clearance rates. Primary data sources identified. API integration pending.

**Last Updated:** March 31, 2026
