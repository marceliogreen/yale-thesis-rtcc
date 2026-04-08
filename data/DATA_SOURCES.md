# RTCC Thesis Data Sources - Complete Guide

**Updated:** 2026-03-31

---

## 🔴 CRITICAL - Primary Clearance Data

| Dataset | Contents | Years | Link |
|---------|----------|-------|------|
| **UCR: Offenses Known & Clearances 2022** | Agency-level clearance rates (homicide, assault, robbery) | 2022 | https://www.icpsr.umich.edu/web/NACJD/studies/39066 |
| **Jacob Kaplan: Offenses Known 1960-2024** | Pre-processed longitudinal clearance data | 1960-2024 | https://www.openicpsr.org/openicpsr/project/100707/version/V22/view |
| **Supplementary Homicide Reports 2022** | Incident-level homicide: demographics, weapons, circumstances | 1976-2022 | https://www.icpsr.umich.edu/web/NACJD/studies/39069 |

---

## 🟡 IMPORTANT - Secondary Data

| Dataset | Contents | Link |
|---------|----------|------|
| **NIBRS Extract Files 2023** | Incident-level crime with clearance status | https://www.icpsr.umich.edu/web/NACJD/series/128 |
| **LEMAS 2020** | Agency resources, staffing, technology, budgets | https://www.icpsr.umich.edu/web/NACJD/studies/38651 |
| **Jacob Kaplan: SHR 1976-2024** | 48 years cleaned homicide data | https://www.openicpsr.org/openicpsr/project/100699/version/V16/view |

---

## 🟢 SUPPLEMENTAL

| Resource | Type | Link |
|----------|------|------|
| **FBI Crime Data Explorer** | Interactive + bulk downloads | https://cde.ucr.cjis.gov/ |
| **BJS LEARCAT Tool** | NIBRS visualization | https://bjs.ojp.gov/learcat |
| **BJS NIBRS API** | Programmatic access | https://bjs.ojp.gov/nibrs |

---

## 📊 Already Downloaded

| File | Source | Records | Status |
|------|--------|---------|--------|
| `washington_post_homicides.csv` | Washington Post | 52,179 | ✅ Downloaded |
| `rtcc_homicide_washington_post.csv` | Processed RTCC cities | 112 rows | ✅ Generated |
| `chicago_homicide_full.csv` | Chicago Socrata API | 14 years | ✅ Downloaded |

---

## 🔑 Key Findings from Washington Post Data (2007-2017)

| City | Pre-RTCC Clearance | Post-RTCC Clearance | Change |
|------|-------------------|---------------------|---------|
| Chicago | 25.7% | 8.6% | **-17.2%** |
| St. Louis | 52.2% | 34.2% | **-18.0%** |
| Miami | 41.0% | 21.8% | **-19.1%** |
| New Orleans | 35.8% | 29.4% | **-6.4%** |

**Average decline: -15.2 percentage points**

---

## 📚 Documentation

| Resource | Link |
|----------|------|
| ICPSR Homicide Data Guide | https://www.icpsr.umich.edu/web/NACJD/cms/4871 |
| Decoding FBI Crime Data | https://ucrbook.com/offensesKnown.html |
| LEMAS Resource Guide | https://www.icpsr.umich.edu/web/NACJD/cms/4872 |

---

## 🎯 Recommended Download Order

1. **Jacob Kaplan Offenses Known 1960-2024** - Pre-cleaned longitudinal data
2. **ICPSR 39066** - Official FBI clearance rates
3. **ICPSR 39069** - Homicide incident details
4. **ICPSR 38651** - LEMAS for control variables
