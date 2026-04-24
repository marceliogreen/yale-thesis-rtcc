"""
Robustness 8+9+10: COVID moderation, homicide-weighted, binomial outcome.

8. RTCC x post-COVID interaction
9. Homicide-weighted analysis
10. Binomial outcome sensitivity (logit transformation)

All use WaPo clearance data (6 cities, 2007-2017).

Output: results/study1_rtcc/robustness/robustness_8_9_10.csv
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
OUT = BASE / "results/study1_rtcc" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)


def load_wapo():
    df = pd.read_csv(BASE / "results/study1_rtcc" / "annual_clearance_rates.csv")
    # Add verified treatment dates
    verified = {"Chicago": 2016, "St. Louis": 2014, "Miami": 2015,
                "New Orleans": 2017, "Albuquerque": 2013, "Fresno": 2015}
    df["rtcc_year_verified"] = df["city"].map(verified)
    df["post_verified"] = (df["year"] >= df["rtcc_year_verified"]).astype(int)
    df["time_verified"] = df["year"] - df["rtcc_year_verified"]
    return df


def ols_with_results(y, X, label):
    """Run OLS and return coefficient table."""
    n, k = X.shape
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    sigma2 = np.sum(resid**2) / max(n - k, 1)
    cov = sigma2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t_stats = beta / se
    p_vals = 2 * stats.t.sf(np.abs(t_stats), df=max(n - k, 1))
    r2 = 1 - np.sum(resid**2) / np.sum((y - y.mean())**2)
    return {
        "specification": label,
        "coefficients": beta.tolist(),
        "std_errors": se.tolist(),
        "p_values": p_vals.tolist(),
        "r_squared": r2,
        "n_obs": n,
    }


def test_covid_moderation(df):
    """Item 8: RTCC x post-COVID interaction (pre-COVID only sample)."""
    logger.info("\n=== ITEM 8: COVID MODERATION ===")

    # Full sample
    y = df["clearance_rate"].values
    post = df["post_verified"].values.astype(float)
    time = df["time_verified"].values.astype(float)

    # Full sample ITS
    X_full = np.column_stack([np.ones(len(y)), time, post, time * post])
    r_full = ols_with_results(y, X_full, "ITS: Full sample (2007-2017)")

    # Pre-COVID only (all WaPo data is pre-COVID since it ends 2017)
    # Since WaPo ends 2017, all data is pre-COVID. Show the pooled effect.
    # Instead, show heterogeneity: estimate per-city and compare
    results = [r_full]

    for city in df["city"].unique():
        cdf = df[df["city"] == city].copy()
        if len(cdf) < 5:
            logger.info(f"  {city}: only {len(cdf)} obs, skipping")
            continue
        y_c = cdf["clearance_rate"].values
        t_c = cdf["time_verified"].values.astype(float)
        p_c = cdf["post_verified"].values.astype(float)
        X_c = np.column_stack([np.ones(len(y_c)), t_c, p_c, t_c * p_c])
        try:
            r_c = ols_with_results(y_c, X_c, f"ITS: {city}")
            results.append(r_c)
            level_change = r_c["coefficients"][2]
            logger.info(f"  {city}: level_change={level_change:.3f}, p={r_c['p_values'][2]:.3f}")
        except np.linalg.LinAlgError:
            logger.info(f"  {city}: singular matrix, skipping")

    logger.info(f"  Note: WaPo data (2007-2017) is entirely pre-COVID. COVID moderation requires FBI CDE extension (item 6).")
    return results


def test_homicide_weighted(df):
    """Item 9: Homicide-weighted analysis."""
    logger.info("\n=== ITEM 9: HOMICIDE-WEIGHTED ===")

    df = df.dropna(subset=["clearance_rate", "homicides"])

    # Unweighted
    y = df["clearance_rate"].values
    post = df["post_verified"].values.astype(float)
    time = df["time_verified"].values.astype(float)
    X = np.column_stack([np.ones(len(y)), time, post, time * post])
    r_unwt = ols_with_results(y, X, "ITS: Unweighted")

    # Weighted by homicides (WLS)
    w = df["homicides"].values.astype(float)
    w = w / w.mean()  # normalize
    W = np.diag(w)

    Xw = W @ X
    yw = W @ y
    r_wt = ols_with_results(yw, Xw, "ITS: Homicide-weighted (WLS)")

    results = [r_unwt, r_wt]
    logger.info(f"  Unweighted: level_change={r_unwt['coefficients'][2]:.3f}, p={r_unwt['p_values'][2]:.3f}")
    logger.info(f"  Weighted:   level_change={r_wt['coefficients'][2]:.3f}, p={r_wt['p_values'][2]:.3f}")

    # Also weighted by city (equal weight per city)
    city_dfs = []
    for city in df["city"].unique():
        cdf = df[df["city"] == city].copy()
        cdf["_city_weight"] = 1.0 / len(cdf)
        city_dfs.append(cdf)
    df_eq = pd.concat(city_dfs)
    y_eq = df_eq["clearance_rate"].values
    w_eq = df_eq["_city_weight"].values
    W_eq = np.diag(w_eq / w_eq.mean())
    X_eq = np.column_stack([np.ones(len(y_eq)),
                            df_eq["time_verified"].values.astype(float),
                            df_eq["post_verified"].values.astype(float),
                            df_eq["time_verified"].values.astype(float) * df_eq["post_verified"].values.astype(float)])
    r_eq = ols_with_results(W_eq @ y_eq, W_eq @ X_eq, "ITS: Equal-weight per city")
    results.append(r_eq)
    logger.info(f"  Equal-weight: level_change={r_eq['coefficients'][2]:.3f}, p={r_eq['p_values'][2]:.3f}")

    return results


def test_binomial_outcome(df):
    """Item 10: Binomial/logit outcome sensitivity."""
    logger.info("\n=== ITEM 10: BINOMIAL OUTCOME ===")

    df = df.dropna(subset=["clearance_rate", "homicides", "cleared"])
    df = df[df["homicides"] > 0]

    # Logit transformation: log(cleared / (homicides - cleared))
    df["logit_cr"] = np.log(
        df["cleared"] / np.maximum(df["homicides"] - df["cleared"], 1)
    )

    # Linear on clearance_rate
    y_lin = df["clearance_rate"].values
    post = df["post_verified"].values.astype(float)
    time = df["time_verified"].values.astype(float)
    X = np.column_stack([np.ones(len(y_lin)), time, post, time * post])
    r_lin = ols_with_results(y_lin, X, "Linear: clearance_rate")

    # Logit-transformed
    y_logit = df["logit_cr"].values
    r_logit = ols_with_results(y_logit, X, "Logit: log(p/(1-p))")

    # Arcsine-square-root transformation (variance-stabilizing for proportions)
    df["asin_cr"] = np.arcsin(np.sqrt(np.clip(df["clearance_rate"], 0.001, 0.999)))
    y_asin = df["asin_cr"].values
    r_asin = ols_with_results(y_asin, X, "Arcsine-sqrt: asin(sqrt(p))")

    results = [r_lin, r_logit, r_asin]
    for r in results:
        lc = r["coefficients"][2]
        logger.info(f"  {r['specification']}: level_change={lc:.4f}, p={r['p_values'][2]:.3f}")

    return results


def main():
    df = load_wapo()
    logger.info(f"Data: {df.shape}, cities={df['city'].nunique()}")

    all_results = []
    all_results.extend(test_covid_moderation(df))
    all_results.extend(test_homicide_weighted(df))
    all_results.extend(test_binomial_outcome(df))

    # Flatten for CSV
    rows = []
    for r in all_results:
        row = {
            "specification": r["specification"],
            "intercept": r["coefficients"][0],
            "time_coeff": r["coefficients"][1],
            "level_change": r["coefficients"][2],
            "trend_change": r["coefficients"][3],
            "level_change_se": r["std_errors"][2],
            "level_change_p": r["p_values"][2],
            "r_squared": r["r_squared"],
            "n_obs": r["n_obs"],
        }
        rows.append(row)

    df_out = pd.DataFrame(rows)
    out_path = OUT / "robustness_8_9_10.csv"
    df_out.to_csv(out_path, index=False)
    logger.info(f"\nSaved: {out_path} ({len(df_out)} specifications)")


if __name__ == "__main__":
    main()
