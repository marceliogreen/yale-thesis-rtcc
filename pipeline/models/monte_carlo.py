"""
Monte Carlo Simulation for RTCC Treatment Effect Uncertainty

Quantifies uncertainty via:
1. Parametric bootstrap from pre/post clearance rates
2. Placebo test (random treatment assignment)
3. Sensitivity analysis (treatment year +/- 1)
4. Leave-one-out cross-validation

If Bayesian ITS posteriors available, samples from those.
Otherwise uses parametric bootstrap from clearance data.

Author: Marcel Green <marcelo.green@yale.edu>
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from pipeline.config import RTCC_CONFIG, get_rtcc_years

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RTCC_CITIES = {city: {"rtcc_year": year} for city, year in get_rtcc_years(RTCC_CONFIG.study1_cities).items()}

N_ITERATIONS = 10_000
RNG = np.random.default_rng(42)


def load_clearance_data(csv_path: str = "results/study1_rtcc/annual_clearance_rates.csv") -> pd.DataFrame:
    return pd.read_csv(csv_path)


def parametric_bootstrap(df: pd.DataFrame, n_iter: int = N_ITERATIONS) -> np.ndarray:
    """
    Bootstrap the average treatment effect across cities.

    For each iteration:
    1. Resample pre/post clearance rates within each city (with replacement)
    2. Compute mean pre and post
    3. Treatment effect = mean_post - mean_pre
    4. Aggregate across cities (weighted average)
    """
    effects = np.zeros(n_iter)

    for i in range(n_iter):
        city_effects = []
        city_weights = []

        for city in df["city"].unique():
            cdf = df[df["city"] == city]
            rtcc_year = RTCC_CITIES.get(city, {}).get("rtcc_year")
            if rtcc_year is None:
                continue

            pre = cdf[cdf["year"] < rtcc_year]["clearance_rate"].values
            post = cdf[cdf["year"] >= rtcc_year]["clearance_rate"].values

            if len(pre) < 2 or len(post) < 1:
                continue

            # Resample with replacement
            pre_sample = RNG.choice(pre, size=len(pre), replace=True)
            post_sample = RNG.choice(post, size=len(post), replace=True)

            effect = post_sample.mean() - pre_sample.mean()
            city_effects.append(effect)
            city_weights.append(len(pre) + len(post))

        if city_effects:
            effects[i] = np.average(city_effects, weights=city_weights)
        else:
            effects[i] = np.nan

    return effects[~np.isnan(effects)]


def placebo_test(df: pd.DataFrame, n_placebo: int = 1000, n_iter_per: int = 100) -> np.ndarray:
    """
    Placebo test: randomly assign treatment years and re-estimate effects.

    If the estimated effect from true treatment years is larger than
    placebo effects, the result is unlikely due to chance.
    """
    all_years = sorted(df["year"].unique())
    year_range = max(all_years) - min(all_years)
    placebo_effects = np.zeros(n_placebo)

    for i in range(n_placebo):
        city_effects = []

        for city in df["city"].unique():
            cdf = df[df["city"] == city]
            rtcc_year = RTCC_CITIES.get(city, {}).get("rtcc_year")
            if rtcc_year is None:
                continue

            # Random placebo year (same range as actual data)
            min_year = cdf["year"].min() + 2
            max_year = cdf["year"].max() - 2
            if min_year >= max_year:
                continue

            placebo_year = RNG.integers(min_year, max_year + 1)

            pre = cdf[cdf["year"] < placebo_year]["clearance_rate"].values
            post = cdf[cdf["year"] >= placebo_year]["clearance_rate"].values

            if len(pre) < 2 or len(post) < 1:
                continue

            city_effects.append(post.mean() - pre.mean())

        if city_effects:
            placebo_effects[i] = np.mean(city_effects)
        else:
            placebo_effects[i] = np.nan

    return placebo_effects[~np.isnan(placebo_effects)]


def sensitivity_analysis(df: pd.DataFrame, shift: int = 1) -> pd.DataFrame:
    """
    Test robustness by shifting treatment year +/- 1 year.
    """
    results = []

    for delta in [-shift, 0, shift]:
        city_effects = []

        for city in df["city"].unique():
            cdf = df[df["city"] == city]
            rtcc_year = RTCC_CITIES.get(city, {}).get("rtcc_year")
            if rtcc_year is None:
                continue

            shifted_year = rtcc_year + delta
            pre = cdf[cdf["year"] < shifted_year]["clearance_rate"].values
            post = cdf[cdf["year"] >= shifted_year]["clearance_rate"].values

            if len(pre) < 2 or len(post) < 1:
                continue

            effect = post.mean() - pre.mean()
            city_effects.append({"city": city, "effect_pp": effect * 100, "shift": delta})

        results.extend(city_effects)

    results_df = pd.DataFrame(results)

    # Aggregate by shift
    if not results_df.empty:
        summary = results_df.groupby("shift")["effect_pp"].agg(["mean", "std", "count"]).reset_index()
        summary.columns = ["shift_years", "mean_effect_pp", "std_effect_pp", "n_cities"]
        logger.info(f"\nSensitivity analysis:\n{summary.to_string(index=False)}")

    return results_df


def leave_one_out(df: pd.DataFrame) -> pd.DataFrame:
    """
    Leave-one-city-out: exclude each city and re-estimate pooled effect.
    """
    cities = [c for c in df["city"].unique() if c in RTCC_CITIES]
    results = []

    for excluded in cities:
        subset = df[df["city"] != excluded]
        remaining = [c for c in cities if c != excluded]

        city_effects = []
        for city in remaining:
            cdf = subset[subset["city"] == city]
            rtcc_year = RTCC_CITIES[city]["rtcc_year"]
            pre = cdf[cdf["year"] < rtcc_year]["clearance_rate"].values
            post = cdf[cdf["year"] >= rtcc_year]["clearance_rate"].values
            if len(pre) >= 2 and len(post) >= 1:
                city_effects.append(post.mean() - pre.mean())

        if city_effects:
            results.append({
                "excluded_city": excluded,
                "pooled_effect_pp": np.mean(city_effects) * 100,
                "n_cities": len(city_effects),
            })

    results_df = pd.DataFrame(results)

    if not results_df.empty:
        logger.info(f"\nLeave-one-out analysis:\n{results_df.to_string(index=False)}")

    return results_df


def run(output_dir: str = "results/study1_rtcc/monte_carlo"):
    """Run full Monte Carlo simulation."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    results_path = Path(output_dir)
    results_path.mkdir(parents=True, exist_ok=True)
    (results_path / "figures").mkdir(parents=True, exist_ok=True)

    df = load_clearance_data()
    logger.info(f"Loaded {len(df)} clearance observations for {df['city'].nunique()} cities")

    # 1. Parametric bootstrap
    logger.info("Running parametric bootstrap (10K iterations)...")
    effects = parametric_bootstrap(df)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(effects * 100, bins=60, color="steelblue", alpha=0.7, edgecolor="white")
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2)
    ax.axvline(x=np.mean(effects) * 100, color="black", linestyle="-", linewidth=2,
               label=f"Mean: {np.mean(effects)*100:.1f} pp")
    ci = np.percentile(effects * 100, [2.5, 97.5])
    ax.axvline(x=ci[0], color="gray", linestyle=":", label=f"95% CI: [{ci[0]:.1f}, {ci[1]:.1f}]")
    ax.axvline(x=ci[1], color="gray", linestyle=":")
    ax.set_title("Monte Carlo: Treatment Effect Distribution (Parametric Bootstrap)", fontweight="bold")
    ax.set_xlabel("Treatment Effect (percentage points)")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(results_path / "figures" / "treatment_effect_distribution.png", dpi=150, bbox_inches="tight")
    plt.close()

    pd.DataFrame({"effect_pp": effects * 100}).describe().to_csv(results_path / "bootstrap_summary.csv")

    # 2. Placebo test
    logger.info("Running placebo test (1K iterations)...")
    placebo = placebo_test(df)

    if len(placebo) > 0:
        true_effect = np.mean(effects) * 100
        p_value = np.mean(placebo * 100 <= true_effect)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(placebo * 100, bins=50, color="lightgray", alpha=0.7, edgecolor="white", label="Placebo effects")
        ax.axvline(x=true_effect, color="red", linestyle="-", linewidth=2,
                   label=f"True effect: {true_effect:.1f} pp (p={p_value:.3f})")
        ax.set_title("Placebo Test: Is the True Effect Larger Than Random?", fontweight="bold")
        ax.set_xlabel("Treatment Effect (pp)")
        ax.set_ylabel("Frequency")
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(results_path / "figures" / "placebo_distribution.png", dpi=150, bbox_inches="tight")
        plt.close()

        pd.DataFrame({
            "metric": ["true_effect_pp", "placebo_mean_pp", "placebo_std_pp", "p_value", "n_placebo"],
            "value": [true_effect, np.mean(placebo) * 100, np.std(placebo) * 100, p_value, len(placebo)],
        }).to_csv(results_path / "placebo_results.csv", index=False)

    # 3. Sensitivity
    logger.info("Running sensitivity analysis...")
    sensitivity = sensitivity_analysis(df)
    sensitivity.to_csv(results_path / "sensitivity_results.csv", index=False)

    # 4. Leave-one-out
    logger.info("Running leave-one-out analysis...")
    loo = leave_one_out(df)
    loo.to_csv(results_path / "leave_one_out_results.csv", index=False)

    # Convergence diagnostics
    rolling_mean = pd.Series(effects * 100).expanding().mean()
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(rolling_mean.values, linewidth=1)
    ax.axhline(y=np.mean(effects) * 100, color="red", linestyle="--")
    ax.set_title("Convergence: Rolling Mean Treatment Effect", fontweight="bold")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("Cumulative Mean Effect (pp)")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(results_path / "figures" / "convergence.png", dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"\n{'='*50}")
    logger.info("MONTE CARLO RESULTS")
    logger.info(f"{'='*50}")
    logger.info(f"Bootstrap treatment effect: {np.mean(effects)*100:+.1f} pp (95% CI: [{ci[0]:.1f}, {ci[1]:.1f}])")
    if len(placebo) > 0:
        logger.info(f"Placebo p-value: {p_value:.3f}")

    return {
        "effects": effects,
        "placebo": placebo,
        "sensitivity": sensitivity,
        "leave_one_out": loo,
    }


if __name__ == "__main__":
    run()
