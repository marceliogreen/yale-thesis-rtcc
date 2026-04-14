# RTCC Thesis - Uploads Folder

**Purpose:** Place downloaded datasets here for thesis agents to access.

---

## 📂 Folder Structure

```
uploads/
├── README.md                    # This file
├── raw_data/                    # Raw downloaded files (ZIP, PDF, etc)
├── processed/                    # Processed/converted files (CSV, Parquet)
└── documentation/                # Research papers, reports, docs
```

---

## 🎯 What to Upload Here

### 1. ICPSR Datasets
When you download from ICPSR, place files here:

```
uploads/raw_data/icpsr_39066/
├── 39066-0001-Data.txt         # Main data file
├── 39066-0002-Data.txt         # Additional files
└── codebook.txt                # Data documentation
```

### 2. Jacob Kaplan Data
```
uploads/raw_data/kaplan_1960_2024/
└── offenses_known_1960_2024.csv
```

### 3. Research Papers & Reports
```
uploads/documentation/
├── RTCC_effectiveness_study.pdf
├── municipal_evaluations/
└── academic_papers/
```

---

## 🤖 For Thesis Agents

When using `/thesis` skill, reference files like this:

```bash
# Point agents to this directory
/Users/marcelinho/GitHub/green-academic-md/yale-thesis-rtcc/uploads/

# Specific subdirectories
/Users/marcelinho/GitHub/green-academic-md/yale-thesis-rtcc/uploads/raw_data/
/Users/marcelinho/GitHub/green-academic-md/yale-thesis-rtcc/uploads/processed/
```

---

## 📥 Download Targets

### Priority 1: ICPSR 39066
- **URL:** https://www.icpsr.umich.edu/web/NACJD/studies/39066
- **Contains:** UCR Offenses Known & Clearances 2022
- **Why:** Agency-level clearance rates for Hartford/Newark

### Priority 2: Jacob Kaplan 1960-2024
- **URL:** https://www.openicpsr.org/openicpsr/project/100707/version/V22/view
- **Contains:** 64 years of pre-cleaned clearance data
- **Why:** Extended timeline, includes 2018-2024

### Priority 3: ICPSR 39069 (SHR)
- **URL:** https://www.icpsr.umich.edu/web/NACJD/studies/39069
- **Contains:** Supplementary Homicide Reports 2022
- **Why:** Incident-level homicide data

---

## 🔄 Processing Pipeline

1. **Upload raw files** to `uploads/raw_data/`
2. **Agents will convert** to `uploads/processed/` (CSV/Parquet)
3. **Documentation** saved to `uploads/documentation/`

---

## 📝 File Manifest Template

When uploading, edit this section:

```markdown
## Uploaded Files

| Date | File | Source | Status |
|------|------|--------|--------|
| 2026-03-31 | icpsr_39066.zip | ICPSR 39066 | ⏳ Pending processing |
```
