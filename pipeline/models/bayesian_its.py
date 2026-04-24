"""
Bayesian Interrupted Time Series (ITS) for RTCC Evaluation

Hierarchical model with partial pooling across 8 RTCC cities.
Estimates level change (beta_2) and trend change (beta_3) post-RTCC.

Model:
  Y_it = alpha_i + beta_1 * time + beta_2 * post_rtcc + beta_3 * time_after + epsilon

Where:
  alpha_i ~ Normal(mu_alpha, sigma_alpha)  [hierarchical city intercepts]
  time = centered year (year - rtcc_year_i)
  post_rtcc = 1 if year >= rtcc_year for city i
  time_after = max(0, year - rtcc_year) * post_rtcc

If PyMC is unavailable, falls back to scipy MLE estimation.

Author: Marcel Green <marcelo.green@yale.edu>
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import sys
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from pipeline.config import DATA_CONFIG, RTCC_CONFIG, BAYESIAN_ITS_CONFIG, get_rtcc_years
from pipeline.utils import extract_bayesian_convergence, print_bayesian_convergence

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress noisy warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

RTCC_CITIES = {city: {"rtcc_year": year} for city, year in get_rtcc_years(RTCC_CONFIG.study1_cities).items()}


def prepare_its_data(
    clearance_csv: str = "results/study1_rtcc/annual_clearance_rates.csv",
    panel_csv: Optional[str] = str(DATA_CONFIG.master_panel_csv),
) -> pd.DataFrame:
    """
    Prepare analysis-ready dataset for ITS.

    Combines WaPo clearance data (best quality) with Kaplan panel data
    for cities not in WaPo dataset.
    """
    dfs = []

    # Load WaPo clearance data
    clearance_path = Path(clearance_csv)
    if clearance_path.exists():
        df_wapo = pd.read_csv(clearance_path)
        df_wapo["source"] = "washington_post"
        dfs.append(df_wapo)
        logger.info(f"Loaded WaPo data: {len(df_wapo)} rows, cities={df_wapo['city'].unique().tolist()}")

    # Load Kaplan panel for additional cities
    if panel_csv and Path(panel_csv).exists():
        df_panel = pd.read_csv(panel_csv)
        # Get RTCC cities from panel
        df_rtcc = df_panel[df_panel["rtcc_city"].notna() & (df_panel["homicides"] > 0)].copy()

        if not df_rtcc.empty:
            # Use agency_name as city proxy — map known ORIs
            df_rtcc["city"] = df_rtcc["rtcc_city"]
            df_rtcc = df_rtcc.dropna(subset=["city"])
            df_rtcc["source"] = "kaplan_ucr"
            df_rtcc = df_rtcc[df_rtcc["year"] >= 2000]

            # Standardize columns
            if "clearance_rate" in df_rtcc.columns:
                df_rtcc = df_rtcc[["city", "year", "homicides", "cleared", "clearance_rate", "source"]].copy()
                dfs.append(df_rtcc)

    if not dfs:
        raise FileNotFoundError("No clearance data found")

    df = pd.concat(dfs, ignore_index=True)

    # Add RTCC treatment variables
    df["rtcc_year"] = df["city"].map(lambda c: RTCC_CITIES.get(c, {}).get("rtcc_year"))
    df = df.dropna(subset=["rtcc_year"])
    df["time"] = df["year"] - df["rtcc_year"]  # centered time
    df["post_rtcc"] = (df["year"] >= df["rtcc_year"]).astype(int)
    df["time_after"] = np.maximum(0, df["time"]) * df["post_rtcc"]

    # Remove rows without clearance rate
    df = df.dropna(subset=["clearance_rate"])
    df = df[df["homicides"] > 0].copy()

    logger.info(f"ITS dataset: {len(df)} rows, {df['city'].nunique()} cities")
    logger.info(f"Cities: {df['city'].unique().tolist()}")

    return df


def run_bayesian_its_pymc(df: pd.DataFrame, results_dir: Path) -> Dict:
    """
    Run hierarchical Bayesian ITS using PyMC.

    Returns posterior summary statistics.
    """
    import pymc as pm
    import arviz as az

    cities = sorted(df["city"].unique())
    city_idx = {c: i for i, c in enumerate(cities)}
    df["city_idx"] = df["city"].map(city_idx)

    n_cities = len(cities)
    city_indices = df["city_idx"].values
    time = df["time"].values.astype(float)
    post = df["post_rtcc"].values.astype(float)
    time_after = df["time_after"].values.astype(float)
    y = df["clearance_rate"].values.astype(float)

    logger.info(f"Building PyMC model: {n_cities} cities, {len(y)} observations")

    with pm.Model() as its_model:
        # Hyperpriors for hierarchical intercepts
        mu_alpha = pm.Normal("mu_alpha", mu=0.4, sigma=0.2)
        sigma_alpha = pm.HalfNormal("sigma_alpha", sigma=0.2)

        # City-level random intercepts
        alpha = pm.Normal("alpha", mu=mu_alpha, sigma=sigma_alpha, shape=n_cities)

        # Fixed effects
        beta_1 = pm.Normal("beta_1", mu=0, sigma=0.05)    # pre-trend slope
        beta_2 = pm.Normal("beta_2", mu=0, sigma=0.2)     # level change post-RTCC
        beta_3 = pm.Normal("beta_3", mu=0, sigma=0.05)    # trend change post-RTCC

        # Observation noise
        sigma = pm.HalfNormal("sigma", sigma=0.15)

        # Expected value
        mu = (alpha[city_indices]
              + beta_1 * time
              + beta_2 * post
              + beta_3 * time_after)

        # Likelihood
        y_obs = pm.Normal("y_obs", mu=mu, sigma=sigma, observed=y)

        # Sample
        trace = pm.sample(
            BAYESIAN_ITS_CONFIG.draws,
            tune=BAYESIAN_ITS_CONFIG.tune,
            chains=4,
            target_accept=BAYESIAN_ITS_CONFIG.target_accept,
            return_inferencedata=True,
            random_seed=42,
        )

    # Summaries
    summary = az.summary(trace, var_names=["beta_1", "beta_2", "beta_3", "mu_alpha", "sigma"])
    logger.info(f"\nPosterior summary:\n{summary}")

    # Convergence diagnostics required for thesis reproducibility checks.
    convergence = extract_bayesian_convergence(
        trace,
        model_name="BayesianITS",
        rhat_threshold=BAYESIAN_ITS_CONFIG.rhat_threshold,
    )
    print_bayesian_convergence(convergence, rhat_threshold=BAYESIAN_ITS_CONFIG.rhat_threshold)

    # Per-city intercepts
    city_summary = az.summary(trace, var_names=["alpha"])
    city_summary.index = cities

    # Save
    results_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(results_dir / "its_posterior_summary.csv")
    city_summary.to_csv(results_dir / "city_intercepts.csv")
    trace.to_netcdf(str(results_dir / "its_trace.nc"))

    # Generate plots
    _plot_its_cities(trace, df, cities, city_idx, results_dir)
    _plot_forest(trace, cities, results_dir)

    return {
        "trace": trace,
        "summary": summary,
        "city_summary": city_summary,
        "convergence": convergence,
    }


def run_its_mle(df: pd.DataFrame, results_dir: Path) -> Dict:
    """
    Fallback: Run ITS using scipy MLE when PyMC unavailable.

    Uses OLS per city + pooled estimate via weighted average.
    """
    from scipy.optimize import minimize
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    results_dir.mkdir(parents=True, exist_ok=True)
    cities = sorted(df["city"].unique())
    city_results = []

    for city in cities:
        cdf = df[df["city"] == city].sort_values("year")
        if len(cdf) < 4:
            logger.warning(f"{city}: only {len(cdf)} observations, skipping")
            continue

        time = cdf["time"].values.astype(float)
        post = cdf["post_rtcc"].values.astype(float)
        time_after = cdf["time_after"].values.astype(float)
        y = cdf["clearance_rate"].values.astype(float)

        # OLS via numpy: y = alpha + beta1*time + beta2*post + beta3*time_after
        X = np.column_stack([np.ones(len(time)), time, post, time_after])
        beta, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)

        y_pred = X @ beta
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # Standard errors
        dof = max(len(y) - 4, 1)
        mse = ss_res / dof
        try:
            se = np.sqrt(np.diag(mse * np.linalg.inv(X.T @ X)))
        except np.linalg.LinAlgError:
            se = np.full(4, np.nan)

        city_results.append({
            "city": city,
            "alpha": beta[0],
            "beta_1_pre_trend": beta[1],
            "beta_2_level_change": beta[2],
            "beta_3_trend_change": beta[3],
            "se_beta_2": se[2],
            "se_beta_3": se[3],
            "r_squared": r_squared,
            "n_obs": len(y),
            "n_pre": int((post == 0).sum()),
            "n_post": int(post.sum()),
        })

        # Per-city ITS plot
        fig, ax = plt.subplots(figsize=(10, 6))
        rtcc_year = RTCC_CITIES[city]["rtcc_year"]

        ax.scatter(cdf["year"], y * 100, color="steelblue", s=50, zorder=5, label="Observed")

        # Pre-RTCC fit
        pre_mask = cdf["year"] < rtcc_year
        if pre_mask.any():
            pre_years = cdf.loc[pre_mask, "year"].values
            pre_pred = X[pre_mask] @ beta
            ax.plot(pre_years, pre_pred * 100, "b-", linewidth=2, label="Pre-RTCC fit")

        # Post-RTCC fit
        post_mask = cdf["year"] >= rtcc_year
        if post_mask.any():
            post_years = cdf.loc[post_mask, "year"].values
            post_pred = X[post_mask] @ beta
            ax.plot(post_years, post_pred * 100, "r-", linewidth=2, label="Post-RTCC fit")

            # Counterfactual: what if RTCC never happened?
            cf_X = np.column_stack([
                np.ones(len(post_years)),
                cdf.loc[post_mask, "time"].values,
                np.zeros(len(post_years)),  # no treatment
                np.zeros(len(post_years)),  # no time_after
            ])
            cf_pred = cf_X @ beta
            ax.plot(post_years, cf_pred * 100, "b--", linewidth=1.5, alpha=0.6, label="Counterfactual")

        ax.axvline(x=rtcc_year, color="red", linestyle=":", linewidth=1.5, alpha=0.7, label=f"RTCC ({rtcc_year})")
        ax.set_title(f"{city} — ITS Analysis", fontsize=13, fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Clearance Rate (%)")
        ax.legend(loc="best", fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(results_dir / "figures" / f"its_{city.lower().replace(' ', '_').replace('.', '')}.png",
                    dpi=150, bbox_inches="tight")
        plt.close()

    results_df = pd.DataFrame(city_results)
    results_df.to_csv(results_dir / "its_mle_results.csv", index=False)

    # Pooled estimate (weighted by inverse SE)
    if not results_df.empty and results_df["se_beta_2"].notna().any():
        weights = 1 / results_df["se_beta_2"] ** 2
        pooled_beta2 = np.average(results_df["beta_2_level_change"], weights=weights)
        pooled_se = np.sqrt(1 / weights.sum())
        logger.info(f"\nPooled level change (beta_2): {pooled_beta2*100:+.1f} pp (SE={pooled_se*100:.1f} pp)")

    logger.info(f"\nITS Results:\n{results_df.to_string(index=False)}")
    return {"results": results_df}


def _plot_its_cities(trace, df, cities, city_idx, results_dir):
    """Plot per-city ITS with posterior predictive."""
    import arviz as az
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = results_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    alpha_samples = trace.posterior["alpha"].values.reshape(-1, len(cities))
    b1_samples = trace.posterior["beta_1"].values.flatten()
    b2_samples = trace.posterior["beta_2"].values.flatten()
    b3_samples = trace.posterior["beta_3"].values.flatten()

    for city in cities:
        cdf = df[df["city"] == city].sort_values("year")
        idx = city_idx[city]
        rtcc_year = RTCC_CITIES[city]["rtcc_year"]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(cdf["year"], cdf["clearance_rate"] * 100, color="steelblue", s=50, zorder=5)

        # Posterior predictive lines
        time_range = np.arange(cdf["year"].min(), cdf["year"].max() + 1)
        n_draw = min(200, len(b1_samples))
        for j in range(n_draw):
            t = time_range - rtcc_year
            post_flag = (time_range >= rtcc_year).astype(float)
            t_after = np.maximum(0, t) * post_flag

            y_pred = alpha_samples[j, idx] + b1_samples[j] * t + b2_samples[j] * post_flag + b3_samples[j] * t_after
            ax.plot(time_range, y_pred * 100, color="gray", alpha=0.02)

        # Mean prediction
        t = time_range - rtcc_year
        post_flag = (time_range >= rtcc_year).astype(float)
        t_after = np.maximum(0, t) * post_flag
        y_mean = (alpha_samples[:, idx].mean() + b1_samples.mean() * t + b2_samples.mean() * post_flag + b3_samples.mean() * t_after)
        ax.plot(time_range, y_mean * 100, "k-", linewidth=2)

        # Counterfactual
        y_cf = alpha_samples[:, idx].mean() + b1_samples.mean() * t
        post_mask = time_range >= rtcc_year
        ax.plot(time_range[post_mask], y_cf[post_mask] * 100, "b--", linewidth=1.5, alpha=0.6, label="Counterfactual")

        ax.axvline(x=rtcc_year, color="red", linestyle=":", alpha=0.7, label=f"RTCC ({rtcc_year})")
        ax.set_title(f"{city} — Bayesian ITS", fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Clearance Rate (%)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(fig_dir / f"its_{city.lower().replace(' ', '_').replace('.', '')}.png",
                    dpi=150, bbox_inches="tight")
        plt.close()


def _plot_forest(trace, cities, results_dir):
    """Forest plot of treatment effects across cities."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Beta_2 (level change)
    ax = axes[0]
    b2 = trace.posterior["beta_2"].values.flatten()
    ax.hist(b2 * 100, bins=50, color="steelblue", alpha=0.7, edgecolor="white")
    ax.axvline(x=0, color="red", linestyle="--")
    ax.set_title("Posterior: Level Change (beta_2)", fontweight="bold")
    ax.set_xlabel("Percentage Points")
    ax.set_ylabel("Density")
    ci = np.percentile(b2 * 100, [2.5, 97.5])
    ax.axvline(x=ci[0], color="gray", linestyle=":")
    ax.axvline(x=ci[1], color="gray", linestyle=":")
    ax.text(0.02, 0.95, f"95% CI: [{ci[0]:.1f}, {ci[1]:.1f}] pp", transform=ax.transAxes, fontsize=10)
    ax.text(0.02, 0.88, f"Mean: {b2.mean()*100:.1f} pp", transform=ax.transAxes, fontsize=10)

    # Beta_3 (trend change)
    ax = axes[1]
    b3 = trace.posterior["beta_3"].values.flatten()
    ax.hist(b3 * 100, bins=50, color="coral", alpha=0.7, edgecolor="white")
    ax.axvline(x=0, color="red", linestyle="--")
    ax.set_title("Posterior: Trend Change (beta_3)", fontweight="bold")
    ax.set_xlabel("Percentage Points per Year")
    ax.set_ylabel("Density")
    ci = np.percentile(b3 * 100, [2.5, 97.5])
    ax.axvline(x=ci[0], color="gray", linestyle=":")
    ax.axvline(x=ci[1], color="gray", linestyle=":")
    ax.text(0.02, 0.95, f"95% CI: [{ci[0]:.1f}, {ci[1]:.1f}] pp/yr", transform=ax.transAxes, fontsize=10)
    ax.text(0.02, 0.88, f"Mean: {b3.mean()*100:.1f} pp/yr", transform=ax.transAxes, fontsize=10)

    plt.suptitle("Bayesian ITS — Treatment Effect Posteriors", fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(results_dir / "figures" / "forest_plot_treatment_effect.png", dpi=150, bbox_inches="tight")
    plt.close()


def run(output_dir: str = "results/study1_rtcc/bayesian_its"):
    """Run Bayesian ITS analysis."""
    results_path = Path(output_dir)
    (results_path / "figures").mkdir(parents=True, exist_ok=True)

    df = prepare_its_data()

    # Try PyMC first, fall back to MLE
    try:
        import pymc
        logger.info("Using PyMC for Bayesian ITS")
        return run_bayesian_its_pymc(df, results_path)
    except ImportError:
        logger.info("PyMC not available, using scipy MLE fallback")
        return run_its_mle(df, results_path)


if __name__ == "__main__":
    run()
