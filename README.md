# Yale RTCC Thesis Repository

Marcel J. Green, Yale University (Cognitive Science), Class of 2026

This repository contains the full computational workflow for two linked studies:

1. Study 1: Real-Time Crime Centers (RTCCs) and homicide clearance outcomes.
2. Study 2: Drone-as-First-Responder (DFR) program analysis through a cognitive science framework.

The project is organized for thesis reviewers who want both fast orientation and full auditability.

## Dashboard

Interactive results explorer:

https://dashboard-alpha-pearl-55.vercel.app

## Reviewer Quick Start

If you only have 10-15 minutes, follow this order:

1. Read this README for design and reproducibility assumptions.
2. Open appendix-code-summary.md for figure/table traceability.
3. Inspect pipeline/config.py for centralized model and threshold settings.
4. Run the preflight-integrated orchestration command below.
5. Confirm generated outputs in results/study1_rtcc and results/study2_dfr.

## Reproducibility Setup

### Environment

Tested with Python 3.10+ on macOS/Linux.

```bash
git clone https://github.com/greenmagic6/yale-thesis-rtcc.git
cd yale-thesis-rtcc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Core Run Commands

Run Study 1 end-to-end:

```bash
python pipeline/run_study1.py
```

Run specific Study 1 step:

```bash
python pipeline/run_study1.py --step its
python pipeline/run_study1.py --step classifier
python pipeline/run_study1.py --step prophet
python pipeline/run_study1.py --step monte_carlo
```

Run PSM-DiD directly:

```bash
python pipeline/run_psm_did.py
```

Run test suite:

```bash
pytest -q
```

## Methodological Configuration (Centralized)

All major assumptions and thresholds are centralized in pipeline/config.py.

Examples:

1. RTCC treatment years and city metadata.
2. PSM caliper and covariate sets.
3. Bayesian sampling defaults and convergence threshold.
4. Output and data path conventions.

This design reduces hidden constants and makes replication checks explicit.

## Built-In Quality Gates

The pipeline now enforces diagnostics needed for defensible thesis review.

### 1) Preflight data validation

pipeline/run_study1.py runs a panel validation stage before modeling.

Validation coverage includes:

1. Clearance rate range checks (must be between 0 and 1).
2. RTCC flag/date alignment checks.
3. Zero-homicide frequency warnings.
4. Panel structure checks.
5. Minimum time-series length checks.
6. Covariate missingness checks (when covariates are available).

### 2) PSM balance diagnostics

pipeline/run_psm_did.py now computes standardized mean differences (SMD)
before and after matching and prints a balance table.

Criterion enforced: absolute SMD < 0.1 on matched sample covariates.

### 3) Bayesian convergence diagnostics

pipeline/models/bayesian_its.py now applies centralized sampling settings and
computes R-hat diagnostics from posterior traces.

Criterion enforced: R-hat <= 1.01.

If convergence fails, the pipeline raises a typed convergence exception.

## Repository Layout

```text
yale-thesis-rtcc/
	pipeline/
		run_study1.py
		run_psm_did.py
		run_classifier.py
		run_shap_causal.py
		models/
			bayesian_its.py
			prophet_forecast.py
			monte_carlo.py
			clearance_classifier.py
			causal_forest.py
			bass_diffusion.py
		data/
		analysis/
		scrapers/
		utils/
			validators.py
			diagnostics.py
			exceptions.py
	data/
	results/
		study1_rtcc/
		study2_dfr/
	figures/
	dashboard/
	tests/
	appendix-code-summary.md
	requirements.txt
```

## Data Sources

Primary inputs used across analyses:

1. UCR Return A (ICPSR / Kaplan integration).
2. FBI CDE API.
3. LEMAS 2020 agency-level covariates.
4. ACS 5-year socioeconomic covariates.
5. Washington Post homicide dataset.

Detailed source notes and caveats are in data/DATA_SOURCES.md.

## Key Outputs

Study 1 outputs are written to results/study1_rtcc, including:

1. Bayesian ITS summaries and figures.
2. PSM-DiD tables.
3. Counterfactual and robustness outputs.
4. Intermediate diagnostic artifacts.

Study 2 outputs are written to results/study2_dfr.

## Known Scope Limits

This repository is research-oriented, not a production package.

Some historical intermediate files referenced by legacy scripts may not be
committed in every snapshot. When that happens, scripts now fail with clearer
messages and status artifacts rather than silent degradation.

## Citation and Contact

If citing this work, reference the Yale undergraduate thesis and this repository commit.

For data access or replication clarification, contact the repository author.

## License

Research code for academic use.
