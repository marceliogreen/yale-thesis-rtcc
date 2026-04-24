# Appendix: Code and Reproducibility Guide

**Interactive Dashboard:** [dashboard-alpha-pearl-55.vercel.app](https://dashboard-alpha-pearl-55.vercel.app)

**One-command reproduction:**

```bash
git clone https://github.com/greenmagic6/rtcc_thesis_analysis.git
cd rtcc_thesis_analysis
conda env create -f environment.yml && conda activate rtcc_thesis
python -m rtcc_thesis_analysis.run_all_analyses
```

All 10 figures render to `figures/`. All numerical estimates print to stdout and are written to `results/estimates.json`.

---

## 1. Repository Architecture

```
rtcc_thesis_analysis/
├── thesis/
│   ├── Thesis Files/yale-thesis-rtcc/
│   │   └── pipeline/
│   │       ├── run_study1.py              # Study 1 orchestrator
│   │       ├── run_classifier.py           # Classifier orchestrator
│   │       ├── run_shap_causal.py          # SHAP + causal forest
│   │       ├── clearance_analysis.py       # Clearance rate pipeline
│   │       ├── models/
│   │       │   ├── bayesian_its.py         # Bayesian ITS
│   │       │   ├── monte_carlo.py          # Monte Carlo bootstrap
│   │       │   ├── prophet_forecast.py     # Prophet counterfactual
│   │       │   ├── clearance_classifier.py # XGBoost/RF/LR classifier
│   │       │   └── causal_forest.py        # EconML causal forest
│   │       ├── data/
│   │       │   └── fbi_api_client.py       # FBI CDE / BJS / ICPSR client
│   │       └── scrapers/
│   │           └── rtcc_scraper.py         # RTCC launch date scraper
│   └── data/
│       ├── rtcc_dates_verified.csv         # 8 treatment cities, verified dates
│       └── master_analysis_panel.csv       # Main analysis dataset
├── pipeline/
│   ├── run_psm_did.py                      # PSM-DiD estimation
│   ├── data/
│   │   └── comparison_pool.py              # 371 comparison cities
│   ├── analysis/
│   │   ├── robustness_01_event_study.py
│   │   ├── robustness_02_matching_balance.py
│   │   ├── robustness_03_sensitivities.py
│   │   ├── robustness_04_covid_weighted_binomial.py
│   │   ├── robustness_05_extended_its.py
│   │   ├── robustness_06_ml_pipeline.py
│   │   └── video_benchmark.py              # Study 2 video analysis
│   └── scrapers/
│       └── dfr_scraper.py                  # DFR program data collection
├── results/
│   ├── study1_rtcc/                        # All Study 1 outputs
│   └── study2_dfr/                         # All Study 2 outputs
├── dashboard/                              # Interactive Next.js dashboard
└── academic/thesis.md                      # Master thesis document
```

**Data flow:**

```
Raw Data (UCR, FBI CDE, LEMAS, ACS)
    → fbi_api_client.py / kaplan_ingestion
        → master_analysis_panel.csv
            → run_study1.py orchestrates:
                ├── bayesian_its.py      → Figure 4
                ├── monte_carlo.py        → Monte Carlo estimate
                ├── prophet_forecast.py   → Figure 3 (counterfactuals)
                ├── clearance_classifier.py → Figure 7 (SHAP)
                └── causal_forest.py      → CATE estimates
            → run_psm_did.py              → Figure 6, primary estimate
            → robustness_01-06.py          → Figure 8
            → clearance_analysis.py        → Figures 2, 3
```

---

## 2. Study 1 Pipeline Scripts

### 2.1 `run_study1.py` — Master Orchestrator

**File:** `thesis/Thesis Files/yale-thesis-rtcc/pipeline/run_study1.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Runs all RTCC analyses in sequence — Bayesian ITS, Classifier + SHAP, Prophet counterfactual, Monte Carlo simulation.

**Key functions:**

```python
def step_its()        # Run Bayesian ITS on all treatment cities
def step_classifier() # Run XGBoost/RF/LR classifier with SHAP
def step_prophet()    # Run Prophet counterfactual forecasts
def step_monte_carlo()# Run Monte Carlo bootstrap simulation
def main()            # Orchestrates all steps sequentially
```

**Outputs:** Figures 3, 4, 7; Monte Carlo estimate; Prophet counterfactuals.

### 2.2 `bayesian_its.py` — Bayesian Interrupted Time Series

**File:** `thesis/.../pipeline/models/bayesian_its.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Hierarchical partial-pooling ITS model with MCMC estimation via PyMC. Estimates city-specific level changes and trend breaks at RTCC adoption.

**Key function:**

```python
def prepare_its_data(panel_df: pd.DataFrame) -> dict:
    """Prepare city-level time series for ITS estimation.
    Returns dict keyed by city with pre/post split."""
```

**MCMC configuration:** 4 chains, 2000 draws each, `random_seed=[1, 2, 3, 4]`.

**Core algorithm (model specification):**

```python
with pm.Model() as hierarchical_its:
    # Hyperpriors for partial pooling
    mu_alpha = pm.Normal('mu_alpha', mu=0, sigma=10)
    sigma_alpha = pm.HalfNormal('sigma_alpha', sigma=5)

    # City-specific parameters
    alpha = pm.Normal('alpha', mu=mu_alpha, sigma=sigma_alpha, shape=n_cities)
    beta_1 = pm.Normal('beta_1', mu=0, sigma=1, shape=n_cities)  # pre-trend
    beta_2 = pm.Normal('beta_2', mu=0, sigma=1, shape=n_cities)  # level change
    beta_3 = pm.Normal('beta_3', mu=0, sigma=1, shape=n_cities)  # trend change

    # Likelihood
    mu = (alpha[city_idx] + beta_1[city_idx] * time
          + beta_2[city_idx] * post_treatment
          + beta_3[city_idx] * time * post_treatment)
    sigma = pm.HalfNormal('sigma', sigma=1)
    y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=clearance_rate)
```

**Thesis estimates produced:**
- ITS pooled level change: −0.178 (p = 0.606)
- Per-city level changes with 95% CIs

**Figure produced:** Figure 4 (Bayesian ITS forest plot)

### 2.3 `monte_carlo.py` — Monte Carlo Bootstrap Simulation

**File:** `thesis/.../pipeline/models/monte_carlo.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Quantifies treatment effect uncertainty via parametric bootstrap, placebo tests, and sensitivity analysis.

**Key functions:**

```python
def load_clearance_data(path: str) -> pd.DataFrame:
    """Load annual clearance rates for bootstrap."""

def parametric_bootstrap(
    data: pd.DataFrame,
    n_iter: int = 10_000,
    rng_seed: int = 42
) -> dict:
    """Parametric bootstrap drawing treatment effects from aggregate distribution.
    Returns dict with mean, median, CI, and full distribution."""
```

**Core algorithm:**

```python
rng = np.random.default_rng(42)
for i in range(n_iter):
    # Resample pre/post clearance rates with replacement
    pre_sample = rng.choice(pre_rates, size=len(pre_rates), replace=True)
    post_sample = rng.choice(post_rates, size=len(post_rates), replace=True)
    # Compute treatment effect for this iteration
    effect = np.mean(post_sample) - np.mean(pre_sample)
    effects.append(effect)
```

**Thesis estimate produced:** Monte Carlo mean −17.7 pp (10,000 iterations)

### 2.4 `prophet_forecast.py` — Prophet Counterfactual Forecasting

**File:** `thesis/.../pipeline/models/prophet_forecast.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Fits Facebook Prophet to pre-RTCC data, generates counterfactual post-RTCC clearance trajectories for each treated city.

**Key functions:**

```python
def prepare_prophet_data(panel_df: pd.DataFrame, city: str) -> pd.DataFrame:
    """Format clearance time series for Prophet (ds, y columns)."""

def run_prophet(city_data: pd.DataFrame, rtcc_year: int) -> dict:
    """Fit Prophet on pre-RTCC data, forecast post-RTCC counterfactual.
    Returns forecast, actuals, and gap (treatment effect estimate)."""
```

**Figure produced:** Figure 3 (event-study trajectories with counterfactual lines)

### 2.5 `clearance_classifier.py` — Multi-Model Classifier

**File:** `thesis/.../pipeline/models/clearance_classifier.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Multi-model classifier (XGBoost, Random Forest, Logistic Regression) for homicide clearance prediction with SHAP feature importance.

**Key function (class constructor):**

```python
class RTCCClearanceClassifier:
    def __init__(self, model_type: str = 'xgboost'):
        """Initialize classifier. model_type: 'xgboost' | 'random_forest' | 'logistic'."""

    def fit(self, X_train, y_train):
        """Train classifier with cross-validation."""

    def shap_analysis(self, X: pd.DataFrame) -> pd.DataFrame:
        """Compute SHAP values and return feature importance ranking."""
```

**Thesis estimates produced:**
- XGBoost CV R²: −1.080 ± 2.169
- Random Forest CV R²: −0.914 ± 1.956
- LASSO RTCC coefficient: −0.0 (regularized to zero)
- SHAP post_rtcc importance: 0.002

**Figure produced:** Figure 7 (XGBoost SHAP bar chart)

### 2.6 `causal_forest.py` — EconML Causal Forest

**File:** `thesis/.../pipeline/models/causal_forest.py`
**Author:** Marcelo Green <marcelo.green@yale.edu>
**Purpose:** Heterogeneous treatment effect estimation using EconML CausalForestDML. Estimates conditional average treatment effects (CATE) by city-level covariates.

**Thesis estimate produced:** City-specific CATE estimates (no significant positive effects found)

### 2.7 `run_psm_did.py` — Propensity-Score Matched DiD

**File:** `pipeline/run_psm_did.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** PSM-DiD estimation using master_analysis_panel_v2.csv with LEMAS controls. Primary causal estimate for the thesis.

**Key functions:**

```python
def load_panel(path: str) -> pd.DataFrame:
    """Load master analysis panel with LEMAS covariates."""

def prepare_did_sample(panel: pd.DataFrame) -> tuple:
    """Construct pre/post treatment indicators, match on propensity scores,
    return matched sample ready for DiD regression."""
```

**Core algorithm:**

```python
# Propensity score matching
ps_model = LogisticRegression().fit(X_covariates, treatment)
ps_scores = ps_model.predict_proba(X_covariates)[:, 1]
matched = NearestNeighborMatch().match(ps_scores, treatment)

# Difference-in-differences
did_model = smf.ols('clearance_rate ~ post * treated + controls', data=matched)
result = did_model.fit(cov_type='cluster', cov_kwds={'groups': matched['city']})
att = result.params['post:treated']
```

**Thesis estimate produced:** ATT = −10.0 pp (p = 0.008) — the primary finding

**Figure produced:** Figure 6 (PSM-DiD coefficient plot)

### 2.8 `clearance_analysis.py` — Clearance Rate Pipeline

**File:** `thesis/.../pipeline/clearance_analysis.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Real-data pipeline using Washington Post homicide data, Kaplan UCR Return A, and FBI CDE API to compute annual clearance rates.

**Key functions:**

```python
def load_washington_post_data(path: str) -> pd.DataFrame:
    """Load WaPo homicide database (2007–2017)."""

def compute_annual_clearance_rates(homicides_df: pd.DataFrame) -> pd.DataFrame:
    """Compute city-year clearance rates: cleared / reported.
    Drops city-years with zero reported homicides.
    Columns: city, year, homicides, cleared, clearance_rate, rtcc_year, post_rtcc"""
```

**Output:** `results/study1_rtcc/annual_clearance_rates.csv` (62 rows, 6 cities, 2007–2017)

**Figures produced:** Figure 2 (pre/post bar chart), Figure 3 (event-study trajectories)

**City-specific estimates produced:**

| City | Pre Clearance | Post Clearance | Change |
|---|---|---|---|
| Chicago | ~40% | ~20% | −20.24 pp |
| Miami | ~38% | ~17% | −21.03 pp |
| St. Louis | ~34% | ~16% | −18.02 pp |

### 2.9 `fbi_api_client.py` — Unified Crime Data Client

**File:** `thesis/.../pipeline/data/fbi_api_client.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Integrates FBI CDE, BJS NIBRS, and ICPSR LEMAS APIs into a single client for data retrieval.

**Data sources:** FBI CDE (`crime-data-explorer.fr.cloud.gov`), ICPSR 100707 (Kaplan UCR), LEMAS 2020

### 2.10 `rtcc_scraper.py` — RTCC Launch Date Scraper

**File:** `thesis/.../pipeline/scrapers/rtcc_scraper.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Scrapes web sources for RTCC launch announcements, news coverage, and vendor press releases to verify treatment dates.

**Output:** `thesis/data/rtcc_dates_verified.csv` — 8 treatment cities with multi-source verification

### 2.11 Robustness Scripts (6 specifications)

**File:** `pipeline/analysis/robustness_01_event_study.py` through `robustness_06_ml_pipeline.py`
**Author:** Marcel Green <marcelo.green@yale.edu>

| Script | Specification | Key Output |
|---|---|---|
| `robustness_01_event_study.py` | Event-study diagnostics | Pre-trend tests |
| `robustness_02_matching_balance.py` | PSM balance (Love plot) | Standardized mean differences |
| `robustness_03_sensitivities.py` | Contaminated controls, Fresno exclusion, mediator | Sensitivity bounds |
| `robustness_04_covid_weighted_binomial.py` | COVID moderation, WLS, logit | +0.49 pp reversal (p = 0.012) |
| `robustness_05_extended_its.py` | 15-city extended ITS | Pooled level change: −0.178 (p = 0.606) |
| `robustness_06_ml_pipeline.py` | XGBoost/RF/LASSO comparison | ML model comparison |

**Figure produced:** Figure 8 (robustness summary)

---

## 3. Study 2 Pipeline Scripts

### 3.1 `dfr_scraper.py` — DFR Data Collection

**File:** `pipeline/scrapers/dfr_scraper.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Scrapes DFR program data from Chula Vista CA, Elizabeth NJ, and Cincinnati OH public records and news sources.

**Output:** `results/study2_dfr/processed/dfr_cross_program_comparison.csv` (3 programs)

**Figure produced:** Figure 9 (DFR operational parameters table)

### 3.2 `video_benchmark.py` — Computational Perception Benchmark

**File:** `pipeline/analysis/video_benchmark.py`
**Author:** Marcel Green <marcelo.green@yale.edu>
**Purpose:** Runs mmaction2 video inference on surveillance footage to benchmark AI vs. human detection performance. Study 2 computational perception component.

### 3.3 Cross-City Cognitive Science Analysis

**Purpose:** Applies 6 cognitive science dimensions (sustained vigilance, change blindness, automaticity, intent attribution, situation awareness, procedural justice) across 3 DFR programs.

**Output:** `results/study2_dfr/processed/cross_city_cog_sci_comparison.csv` (6 dimensions × 3 cities)

**Thesis estimate produced:** 16/18 predictions supported

**Figure produced:** Figure 10 (cognitive framework heatmap)

---

## 4. Figure-to-Script Mapping

| Thesis Figure | Description | Producing Script(s) | Data Source |
|---|---|---|---|
| Figure 1 | Cognitive processing pipeline | Custom diagram construction | Literature synthesis |
| Figure 2 | Pre/post RTCC clearance bar chart | `clearance_analysis.py` | `annual_clearance_rates.csv` |
| Figure 3 | Event-study trajectories | `clearance_analysis.py` + `prophet_forecast.py` | `annual_clearance_rates.csv` |
| Figure 4 | Bayesian ITS forest plot | `bayesian_its.py` | `annual_clearance_rates.csv` |
| Figure 5 | Extended ITS (15 cities) | `robustness_05_extended_its.py` | `robustness_6_extended_its.csv` |
| Figure 6 | PSM-DiD coefficient plot | `run_psm_did.py` | `master_analysis_panel_v2.csv` |
| Figure 7 | XGBoost SHAP importance | `run_shap_causal.py` → `clearance_classifier.py` | `master_analysis_panel.csv` |
| Figure 8 | Robustness summary | `robustness_01-06.py` (aggregated) | Multiple CSVs |
| Figure 9 | DFR operational parameters | `dfr_scraper.py` + processing | DFR public records |
| Figure 10 | Cognitive framework heatmap | Cross-city cog-sci analysis | `cross_city_cog_sci_comparison.csv` |

---

## 5. Numerical Estimate Traceability

| Thesis Claim | Value | Script | Key Function | Output File |
|---|---|---|---|---|
| PSM-DiD ATT (primary) | −10.0 pp (p = 0.008) | `run_psm_did.py` | `prepare_did_sample()` + OLS | `psm_did_results.csv` |
| Monte Carlo bootstrap mean | −17.7 pp | `monte_carlo.py` | `parametric_bootstrap()` | (pipeline stdout) |
| Pre-COVID reversal | +0.49 pp (p = 0.012) | `robustness_04_covid_weighted_binomial.py` | `test_covid_moderation()` | `sensitivity_results.csv` |
| ITS pooled level change | −0.178 (p = 0.606) | `robustness_05_extended_its.py` | `run_extended_its()` | `robustness_6_extended_its.csv` |
| XGBoost SHAP post_rtcc | 0.002 | `run_shap_causal.py` | SHAP computation | `robustness_7_xgboost_importance.csv` |
| Chicago clearance change | −20.24 pp | `clearance_analysis.py` | `compute_annual_clearance_rates()` | `pre_post_rtcc_summary.csv` |
| Miami clearance change | −21.03 pp | `clearance_analysis.py` | `compute_annual_clearance_rates()` | `pre_post_rtcc_summary.csv` |
| St. Louis clearance change | −18.02 pp | `clearance_analysis.py` | `compute_annual_clearance_rates()` | `pre_post_rtcc_summary.csv` |
| XGBoost CV R² | −1.080 ± 2.169 | `clearance_classifier.py` | `fit()` with CV | `robustness_7_ml_pipeline.csv` |
| Random Forest CV R² | −0.914 ± 1.956 | `clearance_classifier.py` | `fit()` with CV | `robustness_7_ml_pipeline.csv` |
| LASSO RTCC coefficient | −0.0 (regularized) | `clearance_classifier.py` | L1-penalized regression | `robustness_7_ml_pipeline.csv` |
| Cognitive predictions | 16/18 supported | Cross-city cog-sci analysis | All dimension functions | `cross_city_cog_sci_comparison.csv` |

---

## 6. Environment and Reproduction

**Python:** 3.11
**Core dependencies:** `pymc`, `xgboost`, `scikit-learn`, `prophet`, `econml`, `shap`, `ruptures`, `pandas`, `numpy`, `matplotlib`
**Full pinned versions:** `environment.yml`

**Random seeds (fixed for reproducibility):**
- All analysis scripts: `utils.set_seeds()` called at top of every script
- Monte Carlo: `numpy.random.default_rng(42)` — 10,000 iterations
- MCMC chains: `random_seed=[1, 2, 3, 4]` — 4 chains × 2000 draws
- Classifiers: `random_state=42` in all scikit-learn estimators

**Data access:** Raw data is not committed (large files, some require accounts). See thesis Appendix B for access procedures for each source:
- UCR Return A: ICPSR 100707-V22 (Kaplan)
- FBI CDE: Free API key at `crime-data-explorer.fr.cloud.gov`
- LEMAS 2020: ICPSR download
- ACS 5-Year: Census API

**Simulated data:** Case-level analyses pending NIBRS access are clearly flagged in each script with a top-level comment:

```python
# SIMULATED DATA: This analysis uses synthetic clearance records pending
# acquisition of NIBRS Extract Files (ICPSR 39270). Real-data replacement
# is tracked in issue #XX.
```
