"""
Robustness 1: Event-study diagnostics with placebo leads.

Per-city OLS regressions with lead/lag dummies around treatment year.
Tests whether pre-trends are flat (parallel trends assumption).

Output: results/study1_rtcc/robustness/event_study_results.csv
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
OUT = BASE / "results" / "study1_rtcc" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)

# Verified treatment dates from audit
TREATMENT_DATES = {
    "Chicago": 2016,
    "St. Louis": 2014,
    "Miami": 2015,
    "New Orleans": 2017,
}


def load_wapo():
    df = pd.read_csv(BASE / "results/study1_rtcc" / "annual_clearance_rates.csv")
    logger.info(f"WaPo clearance: {df.shape}, cities={df['city'].unique().tolist()}")
    return df


def run_event_study(city, df, rtcc_year, max_leads=2, max_lags=3):
    """Run event-study regression with lead/lag dummies."""
    cdf = df[df["city"] == city].copy()
    cdf = cdf.dropna(subset=["clearance_rate"])
    cdf = cdf.sort_values("year")

    cdf["relative_time"] = cdf["year"] - rtcc_year
    available_times = sorted(cdf["relative_time"].unique())

    # Determine which leads/lags actually have data
    needed_times = set(range(-max_leads, max_lags + 1))
    usable_times = [t for t in sorted(needed_times) if t in available_times and t != -1]

    if len(usable_times) < 2:
        logger.warning(f"{city}: only {len(usable_times)} usable periods, skipping")
        return None

    for t in usable_times:
        cdf[f"tau_{t}"] = (cdf["relative_time"] == t).astype(int)

    tau_cols = [f"tau_{t}" for t in usable_times]

    if len(cdf) < len(tau_cols) + 2:
        logger.warning(f"{city}: {len(cdf)} obs < {len(tau_cols)+2} params, skipping")
        return None

    # OLS: clearance_rate = alpha + sum(tau_t * D_t) + epsilon
    X = cdf[tau_cols].values
    X = np.column_stack([np.ones(len(X)), X])
    y = cdf["clearance_rate"].values

    try:
        beta, residuals, rank, sv = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return None

    y_hat = X @ beta
    resid = y - y_hat
    n = len(y)
    k = X.shape[1]
    sigma2 = np.sum(resid**2) / max(n - k, 1)
    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return None

    se = np.sqrt(np.diag(cov))
    results = []
    for i, col in enumerate(tau_cols):
        t_val = col.split("_")[1]
        coef_idx = i + 1  # +1 for intercept
        coef = beta[coef_idx]
        std_err = se[coef_idx]
        t_stat = coef / std_err if std_err > 0 else 0
        p_val = 2 * stats.t.sf(abs(t_stat), df=max(n - k, 1))
        results.append({
            "city": city,
            "rtcc_year": rtcc_year,
            "relative_time": int(t_val),
            "coefficient": coef,
            "std_error": std_err,
            "p_value": p_val,
            "significant_05": p_val < 0.05,
            "n_obs": n,
        })

    # Pre-trend F-test: are lead coefficients jointly zero?
    lead_cols = [c for c in tau_cols if int(c.split("_")[1]) < 0]
    if lead_cols:
        lead_indices = [tau_cols.index(c) + 1 for c in lead_cols]
        R = np.zeros((len(lead_indices), k))
        for i, idx in enumerate(lead_indices):
            R[i, idx] = 1
        r = np.zeros(len(lead_indices))
        Rb = R @ beta - r
        try:
            F_stat = (Rb.T @ np.linalg.inv(R @ cov @ R.T) @ Rb) / len(lead_indices)
            p_pre = 1 - stats.f.cdf(F_stat, len(lead_indices), max(n - k, 1))
        except Exception:
            F_stat = np.nan
            p_pre = np.nan
    else:
        F_stat = np.nan
        p_pre = np.nan

    for r in results:
        r["pre_trend_F"] = F_stat
        r["pre_trend_p"] = p_pre

    return results


def main():
    df = load_wapo()
    all_results = []

    for city, rtcc_year in TREATMENT_DATES.items():
        if city not in df["city"].values:
            logger.warning(f"{city} not in WaPo data")
            continue
        logger.info(f"Running event study: {city} (RTCC={rtcc_year})")
        res = run_event_study(city, df, rtcc_year)
        if res:
            all_results.extend(res)
            logger.info(f"  {len(res)} coefficients, pre-trend F={res[0]['pre_trend_F']:.2f}, p={res[0]['pre_trend_p']:.3f}")

    if not all_results:
        logger.warning("No results produced — data may be insufficient")
        return

    results_df = pd.DataFrame(all_results)
    out_path = OUT / "event_study_results.csv"
    results_df.to_csv(out_path, index=False)
    logger.info(f"Saved: {out_path} ({len(results_df)} rows)")

    # Summary
    logger.info("\n=== EVENT STUDY SUMMARY ===")
    for city in TREATMENT_DATES:
        cr = results_df[results_df["city"] == city]
        if len(cr) == 0:
            continue
        pre = cr[cr["relative_time"] < 0]
        post = cr[cr["relative_time"] >= 0]
        logger.info(f"\n{city}:")
        logger.info(f"  Pre-trend F={cr['pre_trend_F'].iloc[0]:.2f}, p={cr['pre_trend_p'].iloc[0]:.3f}")
        if len(pre) > 0:
            logger.info(f"  Lead coeffs: {pre['coefficient'].tolist()}")
        if len(post) > 0:
            logger.info(f"  Lag coeffs: {post['coefficient'].tolist()}")


if __name__ == "__main__":
    main()
