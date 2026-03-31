# RTCC Effectiveness Thesis Pipeline

**Yale CGSC 4910 — Marcelo Green**

Private repository for thesis research evaluating Real Time Crime Center effectiveness on homicide clearance rates.

## Overview

This pipeline implements the analysis for Study 1 of my thesis, examining whether RTCCs improve homicide clearance rates in 8 target cities compared to 371 mid-sized comparison cities (2010-2023).

## Target Cities (RTCC Adopters)

| City | ORI Code | RTCC Year |
|------|----------|-----------|
| Hartford | CT0030100 | 2016 |
| Miami | FL0130200 | 2016 |
| St. Louis | MO0640000 | 2015 |
| Newark | NJ0071400 | 2018 |
| New Orleans | LA0360000 | 2017 |
| Albuquerque | NM0010100 | 2020 |
| Fresno | CA0190200 | 2018 |
| Chicago | IL0160000 | 2017 |

## Data Sources

- **FBI Crime Data Explorer API** — Homicide counts by agency
- **BJS NIBRS API** — Clearance rates
- **ICPSR** — UCR, NIBRS datasets
- **LEMAS** — Agency characteristics

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Test API connectivity
python pipeline/data/fbi_api_client.py --test

# Fetch crime data
python pipeline/data/fbi_api_client.py --fetch

# Train models
python pipeline/models/clearance_classifier.py

# Causal inference
python pipeline/models/causal_forest.py

# Bass diffusion forecast
python pipeline/models/bass_diffusion.py
```

## Results

See `results/` for outputs.

## Status

🚧 Work in progress — DO NOT SHARE EXTERNALLY
