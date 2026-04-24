# RTCC Thesis: Advancing Computational Perception toward Cognitive-Grounded Prediction

**Marcel J. Green** | Yale University | Cognitive Science Program | Class of 2026

Evaluating the efficiency of Real-Time Crime Centers and emerging technology across two studies: RTCC effectiveness on homicide clearance (Study 1) and drone-as-first-responder programs through a cognitive science lens (Study 2).

## Interactive Dashboard

**[dashboard-alpha-pearl-55.vercel.app](https://dashboard-alpha-pearl-55.vercel.app)**



All results, charts, methodology, and code traceability available interactively. No setup required.

## Repository Structure

```
yale-thesis-rtcc/
├── pipeline/
│   ├── run_study1.py              # Study 1 orchestrator
│   ├── run_psm_did.py             # PSM-DiD estimation
│   ├── run_classifier.py          # Classifier orchestrator
│   ├── run_shap_causal.py         # SHAP + causal forest
│   ├── clearance_analysis.py      # Clearance rate pipeline
│   ├── models/
│   │   ├── bayesian_its.py        # Bayesian ITS (PyMC)
│   │   ├── monte_carlo.py         # Monte Carlo bootstrap
│   │   ├── prophet_forecast.py    # Prophet counterfactual
│   │   ├── clearance_classifier.py # XGBoost/RF/LR + SHAP
│   │   ├── causal_forest.py       # EconML causal forest
│   │   └── bass_diffusion.py      # Bass diffusion forecast
│   ├── analysis/
│   │   ├── robustness_01_event_study.py
│   │   ├── robustness_02_matching_balance.py
│   │   ├── robustness_03_sensitivities.py
│   │   ├── robustness_04_covid_weighted_binomial.py
│   │   ├── robustness_05_extended_its.py
│   │   ├── robustness_06_ml_pipeline.py
│   │   └── video_benchmark.py     # Study 2 video analysis
│   ├── data/
│   │   ├── fbi_api_client.py      # FBI CDE / BJS / ICPSR
│   │   ├── comparison_pool.py     # 371 comparison cities
│   │   ├── build_panel_v2.py      # Master panel builder
│   │   └── lemas_integration.py   # LEMAS covariates
│   └── scrapers/
│       ├── rtcc_scraper.py        # RTCC launch date scraper
│       └── dfr_scraper.py         # DFR program data
├── results/
│   ├── study1_rtcc/               # All Study 1 outputs
│   └── study2_dfr/                # All Study 2 outputs
├── figures/                       # Thesis figures (PNG)
├── dashboard/                     # Interactive Next.js dashboard
├── appendix-code-summary.md       # Full code traceability
└── requirements.txt
```

## Key Findings

| Finding | Value | Method |
|---------|-------|--------|
| PSM-DiD ATT (primary) | -10.0 pp (p = 0.008) | Propensity-score matched DiD |
| Monte Carlo bootstrap mean | -17.7 pp | Parametric bootstrap (10,000 iter) |
| Pre-COVID reversal | +0.49 pp (p = 0.012) | COVID-weighted robustness |
| ITS pooled level change | -0.178 (p = 0.606) | Bayesian ITS (15 cities) |
| Cognitive predictions | 16 / 18 supported | Cross-city cognitive framework |

**No specification produces a statistically significant positive effect of RTCC adoption on clearance rates.**

## Reproduction

```bash
git clone https://github.com/greenmagic6/yale-thesis-rtcc.git
cd yale-thesis-rtcc
pip install -r requirements.txt
python pipeline/run_study1.py
```

See `appendix-code-summary.md` for full traceability of every figure, table, and numerical estimate.

## Data Sources

- **UCR Return A** — ICPSR 100707-V22 (Kaplan)
- **FBI CDE API** — Homicide counts by agency
- **LEMAS 2020** — Agency characteristics
- **ACS 5-Year** — Census demographics
- **Washington Post** — Homicide database (2007-2017)

## Methods

Bayesian ITS, PSM-DiD, Monte Carlo bootstrap, Prophet counterfactuals, XGBoost with SHAP, EconML causal forest, event study, and 10 robustness specifications.

## License

Research code. Contact author for data access inquiries.
