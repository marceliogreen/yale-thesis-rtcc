"""
Robustness 6: Extended ITS to all 15 RTCC cities using FBI CDE homicide data.

Since clearance rate data is only available for 6 WaPo cities (2007-2017),
this uses annual homicide counts from FBI CDE for all 15 cities (2006-2024).
Outcome: log(homicides) to handle scale differences across cities.

Output: results/study1_rtcc/robustness/robustness_6_extended_its.csv
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

# Verified treatment dates (from audit)
TREATMENT_DATES = {
    # Original 6 WaPo cities (verified dates from treatment_date_impact.csv)
    "Chicago": 2016,        # SDSC, verified shift from 2017
    "St. Louis": 2014,      # Verified shift from 2015
    "Miami": 2015,          # Verified shift from 2016
    "New Orleans": 2017,    # No change
    "Albuquerque": 2013,    # Police Magazine April 2013; RTCC opened March 2013
    "Fresno": 2015,         # ABC30, Fresno Bee; RTCC opened July 2015
    # Expanded cities (verified from DATA_STATUS_REPORT.md, 2026-04-16)
    "Hartford": 2016,       # Verified in Kaplan UCR
    "Newark": 2018,         # nj.com April 2017 surveillance center launch
    "Baltimore": 2013,      # CitiWatch Watch Center ~2013-2014
    "Dallas": 2019,         # Atlas of Surveillance, Motorola partnership 2019
    "Denver": 2019,         # Atlas of Surveillance; RTCIC opened August 2019
    "Detroit": 2016,        # Project Green Light launch
    "Houston": 2008,        # OJP — "4th US agency to open RTCC, operating since 2008"
    "Memphis": 2008,        # Memphis Flyer 4/16/2008, OJP, StateTech, GovLoop
    "Philadelphia": 2012,   # Technical.ly, Inquirer, Atlas of Surveillance
}


def load_fbi_cde():
    df = pd.read_csv(BASE / "results/study1_rtcc/fbi_cde/annual_homicides_fbi_cde.csv")
    df["rtcc_year"] = df["city"].map(TREATMENT_DATES)
    df["post"] = (df["year"] >= df["rtcc_year"]).astype(int)
    df["time"] = df["year"] - df["rtcc_year"]
    df["log_homicides"] = np.log1p(df["homicides"])
    return df


def ols_with_results(y, X, label):
    """Run OLS and return coefficient table."""
    n, k = X.shape
    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        resid = y - X @ beta
        sigma2 = np.sum(resid**2) / max(n - k, 1)
        cov = sigma2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return None

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


def run_pooled_its(df):
    """Pooled ITS across all 15 cities."""
    logger.info("\n=== POOLED ITS (15 cities) ===")

    y = df["log_homicides"].values
    time = df["time"].values.astype(float)
    post = df["post"].values.astype(float)

    X = np.column_stack([np.ones(len(y)), time, post, time * post])
    r = ols_with_results(y, X, "Pooled ITS: 15 cities")
    if r:
        logger.info(f"  level_change={r['coefficients'][2]:.3f}, p={r['p_values'][2]:.3f}")
    return r


def run_pooled_its_fe(df):
    """Pooled ITS with city fixed effects."""
    logger.info("\n=== POOLED ITS + CITY FE ===")

    cities = sorted(df["city"].unique())
    city_dummies = pd.get_dummies(df["city"], drop_first=True)

    y = df["log_homicides"].values
    time = df["time"].values.astype(float)
    post = df["post"].values.astype(float)

    X_cols = [np.ones(len(y)), time, post, time * post]
    for col in city_dummies.columns:
        X_cols.append(city_dummies[col].values.astype(float))
    X = np.column_stack(X_cols)

    r = ols_with_results(y, X, "Pooled ITS + City FE: 15 cities")
    if r:
        logger.info(f"  level_change={r['coefficients'][2]:.3f}, p={r['p_values'][2]:.3f}")
    return r


def run_city_its(df):
    """Per-city ITS for all 15 cities."""
    logger.info("\n=== PER-CITY ITS ===")
    results = []

    for city in sorted(df["city"].unique()):
        cdf = df[df["city"] == city].copy()
        rtcc_year = cdf["rtcc_year"].iloc[0]

        n_pre = (cdf["year"] < rtcc_year).sum()
        n_post = (cdf["year"] >= rtcc_year).sum()

        if n_pre < 3 or n_post < 2:
            logger.info(f"  {city}: pre={n_pre}, post={n_post}, skipping")
            continue

        y = cdf["log_homicides"].values
        t = cdf["time"].values.astype(float)
        p = cdf["post"].values.astype(float)
        X = np.column_stack([np.ones(len(y)), t, p, t * p])

        r = ols_with_results(y, X, f"ITS: {city}")
        if r:
            r["city"] = city
            r["rtcc_year"] = rtcc_year
            r["n_pre"] = n_pre
            r["n_post"] = n_post
            results.append(r)
            lc = r["coefficients"][2]
            tc = r["coefficients"][3]
            logger.info(f"  {city}: level={lc:.3f} (p={r['p_values'][2]:.3f}), "
                       f"trend={tc:.3f} (p={r['p_values'][3]:.3f}), N={r['n_obs']}")

    return results


def run_pre_post_comparison(df):
    """Simple pre/post mean comparison for each city."""
    logger.info("\n=== PRE/POST MEAN COMPARISON ===")
    results = []

    for city in sorted(df["city"].unique()):
        cdf = df[df["city"] == city].copy()
        rtcc_year = cdf["rtcc_year"].iloc[0]
        pre = cdf[cdf["year"] < rtcc_year]["log_homicides"]
        post = cdf[cdf["year"] >= rtcc_year]["log_homicides"]

        if len(pre) < 2 or len(post) < 2:
            continue

        t_stat, p_val = stats.ttest_ind(pre, post)
        diff = post.mean() - pre.mean()

        results.append({
            "specification": f"Pre/Post means: {city}",
            "level_change": diff,
            "level_change_se": np.sqrt(pre.var()/len(pre) + post.var()/len(post)),
            "level_change_p": p_val,
            "trend_change": np.nan,
            "intercept": pre.mean(),
            "time_coeff": np.nan,
            "r_squared": np.nan,
            "n_obs": len(pre) + len(post),
            "city": city,
            "rtcc_year": rtcc_year,
        })
        sig = "*" if p_val < 0.05 else ""
        logger.info(f"  {city}: pre={pre.mean():.2f}, post={post.mean():.2f}, "
                   f"diff={diff:.3f}, p={p_val:.3f}{sig}")

    return results


def main():
    df = load_fbi_cde()
    logger.info(f"Data: {df.shape}, cities={df['city'].nunique()}, "
               f"years={df['year'].min()}-{df['year'].max()}")

    all_results = []

    # Pooled models
    r_pooled = run_pooled_its(df)
    if r_pooled:
        all_results.append(r_pooled)

    r_fe = run_pooled_its_fe(df)
    if r_fe:
        all_results.append(r_fe)

    # Per-city
    city_results = run_city_its(df)
    all_results.extend(city_results)

    # Pre/post comparisons
    pp_results = run_pre_post_comparison(df)
    all_results.extend(pp_results)

    # Flatten for CSV
    rows = []
    for r in all_results:
        row = {
            "specification": r.get("specification", ""),
            "intercept": r.get("intercept", r["coefficients"][0] if "coefficients" in r else np.nan),
            "time_coeff": r.get("time_coeff", r["coefficients"][1] if "coefficients" in r else np.nan),
            "level_change": r.get("level_change", r["coefficients"][2] if "coefficients" in r else np.nan),
            "trend_change": r.get("trend_change", r["coefficients"][3] if "coefficients" in r else np.nan),
            "level_change_se": r.get("level_change_se", r["std_errors"][2] if "std_errors" in r else np.nan),
            "level_change_p": r.get("level_change_p", r["p_values"][2] if "p_values" in r else np.nan),
            "r_squared": r.get("r_squared", np.nan),
            "n_obs": r.get("n_obs", np.nan),
        }
        if "city" in r:
            row["city"] = r["city"]
            row["rtcc_year"] = r["rtcc_year"]
        rows.append(row)

    df_out = pd.DataFrame(rows)
    out_path = OUT / "robustness_6_extended_its.csv"
    df_out.to_csv(out_path, index=False)
    logger.info(f"\nSaved: {out_path} ({len(df_out)} specifications)")

    # Summary: how many cities show significant effects?
    city_its = [r for r in all_results if isinstance(r, dict) and "city" in r and "coefficients" in r]
    if city_its:
        sig_neg = sum(1 for r in city_its if r["coefficients"][2] < 0 and r["p_values"][2] < 0.05)
        sig_pos = sum(1 for r in city_its if r["coefficients"][2] > 0 and r["p_values"][2] < 0.05)
        ns = len(city_its) - sig_neg - sig_pos
        logger.info(f"\nPer-city ITS summary: {sig_neg} sig negative, {sig_pos} sig positive, {ns} not significant")


if __name__ == "__main__":
    main()
