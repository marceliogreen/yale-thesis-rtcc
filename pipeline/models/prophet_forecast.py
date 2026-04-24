"""
Prophet Counterfactual Forecasting for RTCC Evaluation

For each RTCC city:
1. Fit Prophet to pre-RTCC clearance rates
2. Forecast counterfactual into post-RTCC period
3. Treatment effect = observed - counterfactual (with uncertainty)

Author: Marcel Green <marcelo.green@yale.edu>
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import logging
import sys
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from pipeline.config import RTCC_CONFIG, get_rtcc_years

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")

RTCC_CITIES = {city: {"rtcc_year": year} for city, year in get_rtcc_years(RTCC_CONFIG.study1_cities).items()}


def prepare_prophet_data(
    clearance_csv: str = "results/study1_rtcc/annual_clearance_rates.csv",
) -> Dict[str, pd.DataFrame]:
    """Load clearance data, return dict of city DataFrames in Prophet format."""
    df = pd.read_csv(clearance_csv)
    city_data = {}

    for city in df["city"].unique():
        cdf = df[df["city"] == city].sort_values("year").copy()
        rtcc_year = RTCC_CITIES.get(city, {}).get("rtcc_year")
        if rtcc_year is None:
            continue

        # Prophet format: ds (date), y (value)
        cdf["ds"] = pd.to_datetime(cdf["year"].astype(str) + "-01-01")
        cdf["y"] = cdf["clearance_rate"]
        cdf["rtcc_year"] = rtcc_year

        city_data[city] = cdf

    return city_data


def run_prophet(city_data: Dict[str, pd.DataFrame], results_dir: Path) -> pd.DataFrame:
    """
    Run Prophet counterfactual forecasting for each city.

    Fits on pre-RTCC data only, forecasts into post-RTCC period.
    Treatment effect = observed - counterfactual.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        from prophet import Prophet
    except ImportError:
        logger.error("Prophet not installed. Install with: pip install prophet cmdstanpy")
        return pd.DataFrame()

    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "figures").mkdir(parents=True, exist_ok=True)

    all_effects = []

    for city, df in city_data.items():
        rtcc_year = df["rtcc_year"].iloc[0]
        pre = df[df["year"] < rtcc_year].copy()
        post = df[df["year"] >= rtcc_year].copy()

        if len(pre) < 3:
            logger.warning(f"{city}: only {len(pre)} pre-RTCC observations, skipping")
            continue

        if len(post) < 1:
            logger.warning(f"{city}: no post-RTCC observations, skipping")
            continue

        logger.info(f"{city}: {len(pre)} pre, {len(post)} post observations")

        # Fit Prophet on pre-RTCC data only
        model = Prophet(
            growth="linear",
            changepoint_prior_scale=0.05,
            yearly_seasonality=False,  # annual data
            weekly_seasonality=False,
            daily_seasonality=False,
            uncertainty_samples=1000,
        )
        model.fit(pre[["ds", "y"]])

        # Forecast through post-RTCC period
        future = df[["ds"]].copy()
        forecast = model.predict(future)

        # Compute treatment effect
        merged = df.merge(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]], on="ds")

        for _, row in merged[merged["year"] >= rtcc_year].iterrows():
            observed = row["y"]
            counterfactual = row["yhat"]
            cf_lower = row["yhat_lower"]
            cf_upper = row["yhat_upper"]

            effect = observed - counterfactual
            # Approximate CI for effect
            effect_lower = observed - cf_upper  # worst case for effect
            effect_upper = observed - cf_lower   # best case for effect

            all_effects.append({
                "city": city,
                "year": row["year"],
                "observed": observed,
                "counterfactual": counterfactual,
                "cf_lower": cf_lower,
                "cf_upper": cf_upper,
                "effect": effect,
                "effect_lower": effect_lower,
                "effect_upper": effect_upper,
            })

        # Plot
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(df["year"], df["y"] * 100, color="steelblue", s=50, zorder=5, label="Observed")
        ax.plot(forecast["ds"].dt.year, forecast["yhat"] * 100, "k-", linewidth=2, label="Prophet forecast")
        ax.fill_between(
            forecast["ds"].dt.year,
            forecast["yhat_lower"] * 100,
            forecast["yhat_upper"] * 100,
            alpha=0.2, color="gray", label="95% CI"
        )
        ax.axvline(x=rtcc_year, color="red", linestyle=":", linewidth=1.5, alpha=0.7, label=f"RTCC ({rtcc_year})")
        ax.set_title(f"{city} — Prophet Counterfactual", fontweight="bold")
        ax.set_xlabel("Year")
        ax.set_ylabel("Clearance Rate (%)")
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

        plt.tight_layout()
        plt.savefig(results_dir / "figures" / f"counterfactual_{city.lower().replace(' ', '_').replace('.', '')}.png",
                    dpi=150, bbox_inches="tight")
        plt.close()

    # Summary
    effects_df = pd.DataFrame(all_effects)
    if not effects_df.empty:
        effects_df.to_csv(results_dir / "treatment_effects.csv", index=False)

        # Aggregate by city
        summary = effects_df.groupby("city").agg(
            mean_effect=("effect", "mean"),
            mean_observed=("observed", "mean"),
            mean_counterfactual=("counterfactual", "mean"),
        ).reset_index()
        summary["effect_pp"] = summary["mean_effect"] * 100

        logger.info(f"\nProphet Treatment Effects (post-RTCC avg):\n{summary.to_string(index=False)}")
        summary.to_csv(results_dir / "treatment_effects_summary.csv", index=False)

    return effects_df


def run(output_dir: str = "results/study1_rtcc/prophet"):
    results_path = Path(output_dir)
    city_data = prepare_prophet_data()
    logger.info(f"Loaded data for {len(city_data)} cities")
    return run_prophet(city_data, results_path)


if __name__ == "__main__":
    run()
