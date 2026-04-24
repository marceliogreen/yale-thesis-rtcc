"""
Robustness 2: Matching balance diagnostics.

Computes SMDs between RTCC treatment group and comparison pool.
Generates Love-plot style data for visualization.

Output: results/study1_rtcc/robustness/matching_balance.csv
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
OUT = BASE / "results/study1_rtcc" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)


def smd(treated, control):
    """Standardized mean difference."""
    t_mean = np.nanmean(treated)
    c_mean = np.nanmean(control)
    pooled_sd = np.sqrt((np.nanvar(treated) + np.nanvar(control)) / 2)
    if pooled_sd == 0:
        return 0.0
    return (t_mean - c_mean) / pooled_sd


def main():
    rtcc = pd.read_csv(BASE / "results/study1_rtcc" / "rtcc_city_panel_enhanced.csv")
    comp = pd.read_csv(BASE / "thesis/data/comparison_pool_yearly.csv", low_memory=False)

    # RTCC treatment group: unique cities, using LEMAS 2020 cross-section
    rtcc_cross = rtcc[rtcc["year"] == 2020].copy()
    comp_cross = comp[comp["year"] == 2020].copy()

    logger.info(f"RTCC 2020 cross-section: {len(rtcc_cross)} cities")
    logger.info(f"Comparison 2020: {len(comp_cross)} cities")

    # Variables to compare
    balance_vars = {
        "est_population": "Population",
        "homicides": "Homicides (2020)",
        "officers_per_10k_pe": "Officers per 10K",
        "total_sworn": "Total Sworn Officers",
    }

    # Add comparison pool equivalents
    comp_cross["homicides"] = comp_cross.get("actual_murder", pd.Series(0, index=comp_cross.index)).fillna(0)
    comp_cross["est_population"] = comp_cross.get("population_1", pd.Series(np.nan, index=comp_cross.index))

    # Officers from comparison pool if available
    officer_cols = [c for c in comp_cross.columns if 'officer' in c.lower() or 'sworn' in c.lower()]
    if officer_cols:
        logger.info(f"Officer columns in comp pool: {officer_cols[:5]}")

    results = []
    for var, label in balance_vars.items():
        if var not in rtcc_cross.columns:
            logger.warning(f"  {var} not in RTCC panel")
            continue

        t_vals = rtcc_cross[var].dropna().values
        c_vals = comp_cross[var].dropna().values if var in comp_cross.columns else np.array([])

        if len(c_vals) == 0:
            logger.warning(f"  {var} not in comparison pool")
            continue

        s = smd(t_vals, c_vals)
        results.append({
            "variable": var,
            "label": label,
            "treated_mean": np.nanmean(t_vals),
            "treated_sd": np.nanstd(t_vals),
            "control_mean": np.nanmean(c_vals),
            "control_sd": np.nanstd(c_vals),
            "smd": s,
            "balance": "GOOD" if abs(s) < 0.1 else "MODERATE" if abs(s) < 0.5 else "SEVERE",
            "n_treated": len(t_vals),
            "n_control": len(c_vals),
        })
        logger.info(f"  {label}: SMD={s:.2f} ({results[-1]['balance']})")

    # Also check LEMAS variables if available
    lemas_vars = {
        "tech_score": "Technology Score",
        "data_driven_score": "Data-Driven Score",
        "has_bwc": "Body-Worn Camera",
        "budget_per_capita": "Budget Per Capita",
    }

    for var, label in lemas_vars.items():
        if var not in rtcc_cross.columns:
            continue
        # LEMAS only in RTCC panel, not in comparison pool
        results.append({
            "variable": var,
            "label": label,
            "treated_mean": rtcc_cross[var].mean(),
            "treated_sd": rtcc_cross[var].std(),
            "control_mean": np.nan,
            "control_sd": np.nan,
            "smd": np.nan,
            "balance": "NO COMPARISON DATA",
            "n_treated": rtcc_cross[var].notna().sum(),
            "n_control": 0,
        })

    df = pd.DataFrame(results)
    out_path = OUT / "matching_balance.csv"
    df.to_csv(out_path, index=False)
    logger.info(f"\nSaved: {out_path} ({len(df)} variables)")

    # Summary
    severe = df[df["balance"] == "SEVERE"]
    logger.info(f"\n=== BALANCE SUMMARY ===")
    logger.info(f"  SEVERE imbalance: {len(severe)} vars")
    for _, row in severe.iterrows():
        logger.info(f"    {row['label']}: SMD={row['smd']:.2f}")


if __name__ == "__main__":
    main()
