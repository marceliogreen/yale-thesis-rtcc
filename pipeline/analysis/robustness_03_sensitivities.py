"""
Robustness 3+4+5: Contaminated controls sensitivity, mediator sensitivity, Fresno coding.

3. Contaminated controls: Exclude cities with known RTCC (not in treatment group) from comparison pool
4. Mediator sensitivity: DiD with/without potential mediators (tech_score, has_bwc, data_driven_score)
5. Fresno discontinuous coding: Use rtcc_active instead of post_rtcc

Design:
- Treatment group: WaPo annual clearance data (6 RTCC cities, each with post_rtcc indicator)
- Control group: comparison_pool_yearly.csv (non-RTCC cities, post_rtcc=0 always)
- DiD: OLS with interaction _treated * post_rtcc

Output: results/study1_rtcc/robustness/sensitivity_results.csv
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as spstats

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
OUT = BASE / "results/study1_rtcc" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)

# Known contaminated cities: RTCC cities NOT in our treatment group.
# These have RTCCs but are excluded from the WaPo treatment sample.
# We match on substrings to handle agency name formats like
# "las vegas metro police department" or "tampa police department".
CONTAMINATED_SUBSTRINGS = [
    "new york", "los angeles", "atlanta", "phoenix", "san antonio",
    "kansas city", "milwaukee", "columbus", "indianapolis", "charlotte",
    "nashville", "tampa", "minneapolis", "las vegas", "oklahoma city",
]


def _prepare_comparison_pool(comp, exclude_contaminated=False):
    """Prepare comparison pool for DiD: select columns, set _treated=0, post_rtcc=0.

    The comparison pool already has clearance_rate computed. For controls,
    post_rtcc is always 0 (never treated).
    """
    df = comp.copy()

    # Exclude contaminated cities by matching on census_name or crosswalk_agency_name
    if exclude_contaminated:
        name_col = "census_name" if "census_name" in df.columns else "crosswalk_agency_name"
        name_lower = df[name_col].str.lower().fillna("")
        mask = pd.Series(True, index=df.index)
        for substr in CONTAMINATED_SUBSTRINGS:
            mask &= ~name_lower.str.contains(substr, regex=False)
        n_before = len(df)
        df = df[mask]
        logger.info(f"  Excluded {n_before - len(df)} contaminated city-years "
                     f"({n_before} -> {len(df)})")

    # Ensure clearance_rate exists (comparison pool already has it, but guard)
    if "clearance_rate" not in df.columns:
        df["clearance_rate"] = np.where(
            df["homicides"].fillna(0) > 0,
            df["cleared"].fillna(0) / df["homicides"].fillna(0),
            np.nan,
        )

    df["_treated"] = 0
    df["post_rtcc"] = 0

    return df


def _prepare_treatment_group():
    """Load WaPo treatment cities with _treated=1."""
    wapo = pd.read_csv(BASE / "results/study1_rtcc" / "annual_clearance_rates.csv")
    wapo["_treated"] = 1
    return wapo


def ols_did(treated_df, control_df, treatment_col="post_rtcc", covariates=None):
    """OLS DiD: clearance_rate ~ constant + _treated + _treated*post [+ covariates].

    When controls are never-treated (post=0 always), post and _treated*post are
    perfectly collinear. We detect this and drop the post main effect, using:
        y ~ 1 + _treated + interaction [+ covariates]
    where interaction = post * _treated. The ATT is the interaction coefficient.

    Returns dict with ATT, SE, t-stat, p-value, sample sizes.
    """
    # Select only the columns we need to avoid conflicts from different schemas
    needed = ["clearance_rate", "_treated", treatment_col]
    if covariates:
        needed.extend(covariates)

    treated_sub = treated_df[[c for c in needed if c in treated_df.columns]].copy()
    control_sub = control_df[[c for c in needed if c in control_df.columns]].copy()

    df = pd.concat([treated_sub, control_sub], ignore_index=True)
    df = df.dropna(subset=["clearance_rate"])

    if len(df) == 0:
        logger.warning("  ols_did: no observations after dropping NaN clearance_rate")
        return None

    y = df["clearance_rate"].values
    post = df[treatment_col].values.astype(float)
    treated = df["_treated"].values.astype(float)
    interaction = post * treated

    # Check if post and interaction are collinear (happens when controls are
    # never-treated: post is nonzero only when treated=1, so post == interaction)
    include_post_main = False
    if np.var(post) > 0 and np.var(interaction) > 0:
        corr = np.corrcoef(post, interaction)[0, 1]
        if abs(corr) < 0.999:
            include_post_main = True

    # Design matrix
    if include_post_main:
        # Full DiD: y ~ 1 + treated + post + interaction
        X_cols = [np.ones(len(df)), treated, post, interaction]
        att_idx = 3
    else:
        # Reduced model (controls never-treated): y ~ 1 + treated + interaction
        X_cols = [np.ones(len(df)), treated, interaction]
        att_idx = 2

    if covariates:
        for c in covariates:
            if c in df.columns:
                vals = pd.to_numeric(df[c], errors="coerce").fillna(0).values
                X_cols.append(vals)
            else:
                logger.warning(f"  ols_did: covariate '{c}' not found, skipping")

    X = np.column_stack(X_cols)
    k = X.shape[1]

    # Verify full rank
    if np.linalg.matrix_rank(X) < k:
        logger.warning(f"  ols_did: design matrix rank {np.linalg.matrix_rank(X)} < {k}, "
                       f"cannot estimate")
        return None

    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        logger.warning("  ols_did: lstsq failed (LinAlgError)")
        return None

    resid = y - X @ beta
    n = len(y)
    sigma2 = np.sum(resid**2) / max(n - k, 1)

    try:
        cov = sigma2 * np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        logger.warning("  ols_did: singular X'X matrix")
        return None

    se = np.sqrt(np.diag(cov))
    att = beta[att_idx]
    att_se = se[att_idx]

    if att_se == 0:
        return None

    t_stat = att / att_se
    p_val = 2 * spstats.t.sf(abs(t_stat), df=max(n - k, 1))

    return {
        "att": att,
        "se": att_se,
        "t_stat": t_stat,
        "p_value": p_val,
        "n_obs": n,
        "n_treated": int(treated.sum()),
        "n_control": int((1 - treated).sum()),
    }


def load_data():
    rtcc = pd.read_csv(BASE / "results/study1_rtcc" / "rtcc_city_panel_enhanced.csv")
    comp = pd.read_csv(BASE / "thesis/data/comparison_pool_yearly.csv", low_memory=False)
    return rtcc, comp


def test_contaminated_controls(comp):
    """Item 3: DiD comparing RTCC cities vs comparison pool, excluding contaminated controls.

    Contaminated controls are cities known to have RTCC but not in the treatment group.
    If results are similar with and without exclusion, contamination bias is minimal.
    """
    logger.info("\n=== ITEM 3: CONTAMINATED CONTROLS ===")

    wapo = _prepare_treatment_group()
    logger.info(f"  Treatment group: {len(wapo)} city-years, "
                f"{wapo['city'].nunique()} cities")

    # Full comparison pool (controls always have post_rtcc=0)
    comp_full = _prepare_comparison_pool(comp, exclude_contaminated=False)
    comp_clean = _prepare_comparison_pool(comp, exclude_contaminated=True)
    logger.info(f"  Full pool: {len(comp_full)} city-years, "
                f"clean pool: {len(comp_clean)} city-years")

    results = []

    # DiD with full pool
    r_full = ols_did(wapo, comp_full, treatment_col="post_rtcc")
    if r_full:
        r_full["specification"] = "Full comparison pool"
        results.append(r_full)
        logger.info(f"  Full pool:  ATT={r_full['att']:.4f}, SE={r_full['se']:.4f}, "
                     f"p={r_full['p_value']:.4f}, N={r_full['n_obs']}")
    else:
        logger.warning("  Full pool DiD failed")

    # DiD excluding contaminated controls
    r_clean = ols_did(wapo, comp_clean, treatment_col="post_rtcc")
    if r_clean:
        r_clean["specification"] = "Excluding contaminated controls"
        results.append(r_clean)
        logger.info(f"  Clean pool: ATT={r_clean['att']:.4f}, SE={r_clean['se']:.4f}, "
                     f"p={r_clean['p_value']:.4f}, N={r_clean['n_obs']}")
    else:
        logger.warning("  Clean pool DiD failed")

    if not results:
        logger.error("  Item 3 produced no results")
    return results


def test_mediator_sensitivity(rtcc, comp):
    """Item 4: Mediator sensitivity analysis.

    Part A: DiD (WaPo treatment vs comparison pool) -- no mediators possible since
            comparison pool lacks LEMAS covariates. Runs as baseline DiD.

    Part B: Within-RTCC-panel regression of homicides on post_rtcc +/- mediators.
            This tests whether mediator inclusion changes the treatment effect
            estimate in the treatment-only panel (ITS-style).
            Note: mediators only exist for RTCC cities, not comparison pool.
    """
    logger.info("\n=== ITEM 4: MEDIATOR SENSITIVITY ===")

    wapo = _prepare_treatment_group()
    comp_base = _prepare_comparison_pool(comp, exclude_contaminated=True)
    results = []

    # --- Part A: DiD baseline (no mediators -- comparison pool doesn't have them) ---
    r_did = ols_did(wapo, comp_base, treatment_col="post_rtcc")
    if r_did:
        r_did["specification"] = "DiD baseline (no mediators)"
        results.append(r_did)
        logger.info(f"  DiD baseline: ATT={r_did['att']:.4f}, p={r_did['p_value']:.4f}")
    else:
        logger.warning("  DiD baseline failed")

    # --- Part B: RTCC-panel ITS with/without mediators ---
    # This uses the RTCC city panel (treatment-only) to see if mediator inclusion
    # changes the post_rtcc coefficient. Uses log(homicides) as outcome.
    # All cities are treated, so we do ITS (not DiD):
    #   y ~ 1 + year_centered + post_rtcc + year_centered*post_rtcc [+ mediators]

    logger.info("  RTCC-panel ITS (log homicides) with/without mediators:")

    # Use log_homicides if available, else compute
    if "log_homicides" in rtcc.columns:
        outcome_col = "log_homicides"
    else:
        rtcc = rtcc.copy()
        rtcc["log_homicides"] = np.log1p(rtcc["homicides"].fillna(0))
        outcome_col = "log_homicides"

    rtcc_sub = rtcc.dropna(subset=[outcome_col]).copy()
    if "year_centered" not in rtcc_sub.columns:
        rtcc_sub["year_centered"] = rtcc_sub["year"] - rtcc_sub["rtcc_year"]

    for with_med in [False, True]:
        med_vars = ["tech_score", "data_driven_score"] if with_med else []
        # Note: has_bwc is constant (=1) for all RTCC city-years, so excluded
        # to avoid collinearity with intercept.
        label = "WITH mediators" if with_med else "WITHOUT mediators"

        y = rtcc_sub[outcome_col].values
        time = rtcc_sub["year_centered"].values
        post = rtcc_sub["post_rtcc"].values.astype(float)
        time_post = time * post

        X_cols = [np.ones(len(y)), time, post, time_post]
        for c in med_vars:
            if c in rtcc_sub.columns:
                vals = pd.to_numeric(rtcc_sub[c], errors="coerce").fillna(0).values
                X_cols.append(vals)

        X = np.column_stack(X_cols)
        k = X.shape[1]
        n = len(y)

        try:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            resid = y - X @ beta
            sigma2 = np.sum(resid**2) / max(n - k, 1)
            cov = sigma2 * np.linalg.inv(X.T @ X)
            se = np.sqrt(np.diag(cov))

            # post_rtcc coefficient is index 2 (constant, time, post, time*post, ...)
            att = beta[2]
            att_se = se[2]
            t_stat = att / att_se if att_se > 0 else 0
            p_val = 2 * spstats.t.sf(abs(t_stat), df=max(n - k, 1))

            results.append({
                "att": att,
                "se": att_se,
                "t_stat": t_stat,
                "p_value": p_val,
                "n_obs": n,
                "n_treated": int(post.sum()),
                "n_control": int((1 - post).sum()),
                "specification": f"RTCC ITS: {outcome_col} {label}",
            })
            logger.info(f"    {label}: coeff={att:.4f}, SE={att_se:.4f}, "
                         f"t={t_stat:.3f}, p={p_val:.4f}")
        except Exception as e:
            logger.warning(f"    {label} failed: {e}")

    if not results:
        logger.error("  Item 4 produced no results")
    return results


def test_fresno_discontinuous(rtcc):
    """Item 5: Fresno discontinuous treatment coding."""
    logger.info("\n=== ITEM 5: FRESNO DISCONTINUOUS CODING ===")

    fresno = rtcc[rtcc["city"] == "Fresno"].copy()
    fresno = fresno.dropna(subset=["homicides"])

    results = []

    for treatment_var, label in [("post_rtcc", "Continuous (post_rtcc)"),
                                  ("rtcc_active", "Discontinuous (rtcc_active)")]:
        y = fresno["homicides"].values
        post = fresno[treatment_var].values
        time = fresno.get("year_centered", fresno["year"] - fresno["rtcc_year"].iloc[0]).values

        X = np.column_stack([np.ones(len(y)), time, post, time * post])
        try:
            beta = np.linalg.lstsq(X, y, rcond=None)[0]
            resid = y - X @ beta
            n, k = len(y), X.shape[1]
            sigma2 = np.sum(resid**2) / max(n - k, 1)
            cov = sigma2 * np.linalg.inv(X.T @ X)
            se = np.sqrt(np.diag(cov))

            results.append({
                "specification": f"Fresno ITS: {label}",
                "att": beta[2],
                "se": se[2],
                "t_stat": beta[2] / se[2],
                "p_value": 2 * spstats.t.sf(abs(beta[2] / se[2]), df=max(n - k, 1)),
                "n_obs": n,
                "n_treated": int(post.sum()),
                "n_control": int((1 - post).sum()),
            })
            logger.info(f"  {label}: level_change={beta[2]:.2f}, SE={se[2]:.2f}, "
                         f"p={results[-1]['p_value']:.3f}")
        except Exception as e:
            logger.warning(f"  Failed: {e}")

    return results


def main():
    rtcc, comp = load_data()

    all_results = []
    all_results.extend(test_contaminated_controls(comp))
    all_results.extend(test_mediator_sensitivity(rtcc, comp))
    all_results.extend(test_fresno_discontinuous(rtcc))

    if all_results:
        df = pd.DataFrame(all_results)
        out_path = OUT / "sensitivity_results.csv"
        df.to_csv(out_path, index=False)
        logger.info(f"\nSaved: {out_path} ({len(df)} specifications)")

        # Summary table
        logger.info("\n" + "=" * 70)
        logger.info("SENSITIVITY RESULTS SUMMARY")
        logger.info("=" * 70)
        for _, row in df.iterrows():
            sig = "***" if row["p_value"] < 0.01 else "**" if row["p_value"] < 0.05 else "*" if row["p_value"] < 0.1 else ""
            logger.info(f"  {row['specification']:45s}  ATT={row['att']:8.4f}  "
                         f"SE={row['se']:8.4f}  p={row['p_value']:.4f}{sig}  N={row['n_obs']}")
    else:
        logger.error("No results produced!")


if __name__ == "__main__":
    main()
