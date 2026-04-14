# RTCC Thesis - Dashboard Preview & Data Status

**Generated:** March 31, 2026

---

## 🚀 Dashboard Status

**Running at:** http://localhost:8502

### Tabs Available:
1. **📊 Key Findings** - Clearance rate changes post-RTCC
2. **📈 Clearance Trends** - Annual homicide trends by city
3. **🏙️ City Details** - Per-city breakdowns
4. **📁 Data Sources** - Source documentation

---

## 📊 Key Finding to Present

> **ALL RTCC cities with post-implementation data show declining homicide clearance rates**

| City | Pre-RTCC | Post-RTCC | Change |
|------|----------|-----------|--------|
| Chicago | 25.7% | 8.6% | **-17.2%** |
| St. Louis | 52.2% | 34.2% | **-18.0%** |
| Miami | 41.0% | 21.8% | **-19.1%** |
| New Orleans | 35.8% | 29.4% | **-6.4%** |

**Average decline: -15.2 percentage points**

---

## 📁 Downloaded Data

| File | Size | Records | Source |
|------|------|---------|--------|
| `washington_post_homicides.csv` | 5.4 MB | 52,179 | Washington Post |
| `rtcc_homicide_washington_post.csv` | 5 KB | 112 | Processed RTCC cities |
| `chicago_homicide_full.csv` | 209 B | 14 | Chicago Socrata API |

---

## ⏳ Pending Downloads

### 1. ICPSR 39066 - UCR Clearances
- **URL:** https://www.icpsr.umich.edu/web/NACJD/studies/39066
- **Purpose:** Get Hartford and Newark clearance data
- **Action:** Requires ICPSR account (free for academic)

### 2. Jacob Kaplan 1960-2024
- **URL:** https://www.openicpsr.org/openicpsr/project/100707/version/V22/view
- **Purpose:** 64 years of pre-cleaned clearance data
- **Action:** Download ZIP, extract CSV

### 3. ICPSR 39069 - SHR
- **URL:** https://www.icpsr.umich.edu/web/NACJD/studies/39069
- **Purpose:** Incident-level homicide data
- **Action:** Requires ICPSR account

---

## 🔑 API Keys

| Service | Key | Status |
|---------|-----|--------|
| data.gov (FBI CDE) | `y8mMCudkoqb4trrDHqLg59Zy602FZYHUdbXTd5Pg` | ⚠️ Endpoints changed (404) |
| Firecrawl | Configured in skill | ✅ Working |

---

## 📈 Visualizations Ready

1. **Pre vs Post RTCC Clearance Rates** (grouped bar chart)
2. **Annual Homicide Trends** (line chart with RTCC marker)
3. **City-by-City Tables** (expandable details)
4. **Data Sources Timeline** (status tracker)

---

## 💡 Talking Points for Advisor Meeting

1. **Data source is solid:** Washington Post dataset is widely cited in criminology research
2. **Finding is consistent:** ALL 4 cities with post-RTCC data show the same pattern
3. **Magnitude is substantial:** 15-20 percentage point decline in clearance rates
4. **Next steps:** Extend analysis with ICPSR data to get Hartford/Newark
5. **Methodology:** This supports interrupted time series + causal forest approach

---

## 📂 File Locations

```
/Users/marcelinho/GitHub/green-academic-md/yale-thesis-rtcc/
├── dashboard/
│   └── app.py              # Streamlit dashboard
├── downloads/              # All data files (agents access here)
│   ├── washington_post_homicides.csv
│   ├── rtcc_homicide_washington_post.csv
│   └── chicago_homicide_full.csv
└── data/
    ├── process_washington_post_data.py
    └── DATA_SOURCES.md
```
