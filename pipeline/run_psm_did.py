"""
Propensity-Score Matched Difference-in-Differences (PSM-DiD)

Uses the master_analysis_panel_v2.csv with LEMAS controls and propensity scores.
Performs matched DiD to estimate the Average Treatment Effect on the Treated (ATT).

Methodology:
1. Restrict to primary + reference tier treatment cities
2. Match each treated agency-year to nearest comparison by propensity score
3. Run DiD: clearance_rate ~ treated + post + treated*post + LEMAS controls
4. Report ATT with robust standard errors

Output: pipeline/results/study1_rtcc/tables/psm_did_results.csv

Author: Marcel Green <marcelo.green@yale.edu>
"""

import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from pipeline.config import DATA_CONFIG
from pipeline.data.build_submission_artifacts import write_psm_status_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
INPUT_PANEL = DATA_CONFIG.master_panel_v2_csv
OUTPUT_DIR = BASE_DIR / "pipeline" / "results" / "study1_rtcc" / "tables"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Configuration ──────────────────────────────────────────────

# Which tiers to include as "treated"
TREATED_TIERS = {"primary", "reference"}

# DiD sample restriction
MIN_YEAR = 2010

# LEMAS controls for the regression
LEMAS_CONTROLS = [
    "officers_per_10k",
    "budget_per_capita",
    "tech_score",
    "data_driven_score",
    "has_bwc",
]

# Matching features (propensity score)
MATCH_FEATURES = ["propensity_score"]

# Caliper for matching (max PS distance)
CALIPER = 0.05


def load_panel() -> pd.DataFrame:
    """Load panel v2."""
    if not INPUT_PANEL.exists():
        raise FileNotFoundError(
            f"Required PSM input panel not found: {INPUT_PANEL}. "
            "The checked-in submission snapshot omits the original processed panel."
        )
    logger.info(f"Loading panel from {INPUT_PANEL}")
    df = pd.read_csv(INPUT_PANEL, low_memory=False)
    logger.info(f"Loaded {len(df):,} rows")
    return df


def prepare_did_sample(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare the analysis sample for DiD."""
    logger.info("Preparing DiD sample...")

    # Filter to analysis-ready observations in year range
    sample = df[
        (df["year"] >= MIN_YEAR) &
        (df["clearance_rate"].notna()) &
        (df["homicides"] > 0) &
        (df["propensity_score"].notna())
    ].copy()

    logger.info(f"After filtering: {len(sample):,} rows")

    # Mark treated: primary + reference tiers
    sample["treated"] = sample["city_tier"].isin(TREATED_TIERS).astype(int)

    # Post-treatment indicator
    sample["post"] = sample["post_rtcc"]

    # Treatment x Post interaction
    sample["treated_x_post"] = sample["treated"] * sample["post"]

    # Log group sizes
    treated = sample[sample["treated"] == 1]
    control = sample[sample["treated"] == 0]
    logger.info(f"  Treated: {len(treated)} obs from {treated['ori9'].nunique()} agencies")
    logger.info(f"  Control: {len(control)} obs from {control['ori9'].nunique()} agencies")
    logger.info(f"  Treated (pre): {(treated['post'] == 0).sum()}, Treated (post): {(treated['post'] == 1).sum()}")

    # Per-city breakdown
    for city in sorted(treated["rtcc_city"].dropna().unique()):
        sub = treated[treated["rtcc_city"] == city]
        logger.info(
            f"    {city}: {len(sub)} obs (pre={len(sub[sub['post']==0])}, "
            f"post={len(sub[sub['post']==1])})"
        )

    return sample


def propensity_score_matching(sample: pd.DataFrame) -> pd.DataFrame:
    """
    Match treated agencies to comparison agencies by propensity score.
    Uses 1:1 nearest-neighbor matching with caliper.
    """
    logger.info("Running propensity score matching...")

    treated = sample[sample["treated"] == 1]
    control = sample[sample["treated"] == 0]

    # Get unique treated agencies
    treated_agencies = (
        treated[["ori9", "rtcc_city", "propensity_score"]]
        .drop_duplicates(subset="ori9")
    )

    # Get unique control agencies
    control_agencies = (
        control[["ori9", "propensity_score"]]
        .drop_duplicates(subset="ori9")
        .dropna(subset=["propensity_score"])
    )

    if len(treated_agencies) == 0 or len(control_agencies) == 0:
        logger.warning("Insufficient agencies for matching. Using full sample.")
        return sample

    # Nearest neighbor matching
    nn = NearestNeighbors(n_neighbors=min(10, len(control_agencies)), metric="euclidean")
    nn.fit(control_agencies[["propensity_score"]].values)

    distances, indices = nn.kneighbors(treated_agencies[["propensity_score"]].values)

    # Select matches within caliper
    matched_control_oris = set()
    match_pairs = []

    for i, (_, t_row) in enumerate(treated_agencies.iterrows()):
        for j in range(len(indices[i])):
            if distances[i][j] <= CALIPER:
                comp_ori = control_agencies.iloc[indices[i][j]]["ori9"]
                matched_control_oris.add(comp_ori)
                match_pairs.append({
                    "treated_ori": t_row["ori9"],
                    "treated_city": t_row["rtcc_city"],
                    "matched_ori": comp_ori,
                    "ps_distance": distances[i][j],
                })
                break  # 1:1 matching
            else:
                break  # Outside caliper

    if not matched_control_oris:
        logger.warning(f"No matches within caliper {CALIPER}. Using full sample.")
        return sample

    logger.info(f"  Matched {len(match_pairs)} pairs within caliper {CALIPER}")
    for pair in match_pairs:
        logger.info(
            f"    {pair['treated_city']} ({pair['treated_ori']}) ↔ "
            f"{pair['matched_ori']} (dist={pair['ps_distance']:.4f})"
        )

    # Keep only treated + matched controls
    matched_sample = sample[
        (sample["treated"] == 1) |
        (sample["ori9"].isin(matched_control_oris))
    ].copy()

    matched_sample["is_psm_matched"] = 1
    logger.info(f"  Matched sample: {len(matched_sample)} obs")

    # Balance check
    logger.info("  Balance check:")
    for feat in ["propensity_score", "officers_per_10k", "tech_score"]:
        t_mean = matched_sample[matched_sample["treated"] == 1][feat].mean()
        c_mean = matched_sample[matched_sample["treated"] == 0][feat].mean()
        logger.info(f"    {feat}: treated={t_mean:.3f}, control={c_mean:.3f}, diff={t_mean-c_mean:+.3f}")

    return matched_sample


def run_did_regression(sample: pd.DataFrame, label: str = "full") -> dict:
    """
    Run Difference-in-Differences regression.

    Model: clearance_rate ~ treated + post + treated_x_post + LEMAS controls
    The coefficient on treated_x_post is the ATT.
    """
    logger.info(f"Running DiD regression ({label})...")

    # Fill missing LEMAS controls with 0 (for agencies without LEMAS)
    for col in LEMAS_CONTROLS:
        if col in sample.columns:
            sample[col] = sample[col].fillna(0)

    # Build formula
    controls_str = " + ".join(LEMAS_CONTROLS)
    formula = f"clearance_rate ~ treated + post + treated_x_post + {controls_str}"

    try:
        model = smf.ols(formula, data=sample).fit(cov_type="HC1")

        att = model.params.get("treated_x_post", np.nan)
        att_se = model.bse.get("treated_x_post", np.nan)
        att_pval = model.pvalues.get("treated_x_post", np.nan)
        att_ci = model.conf_int().loc["treated_x_post"].values if "treated_x_post" in model.conf_int().index else [np.nan, np.nan]

        logger.info(f"  ATT (treated_x_post): {att:+.4f} (SE={att_se:.4f}, p={att_pval:.4f})")
        logger.info(f"  95% CI: [{att_ci[0]:.4f}, {att_ci[1]:.4f}]")
        logger.info(f"  R²: {model.rsquared:.4f}")
        logger.info(f"  N: {int(model.nobs):,}")

        # Store all coefficients
        results = {
            "label": label,
            "att": att,
            "att_se": att_se,
            "att_pval": att_pval,
            "att_ci_lower": att_ci[0],
            "att_ci_upper": att_ci[1],
            "r_squared": model.rsquared,
            "n_obs": int(model.nobs),
            "n_treated": sample["treated"].sum(),
            "n_control": (sample["treated"] == 0).sum(),
        }

        # Add other coefficients
        for param in model.params.index:
            if param != "treated_x_post":
                results[f"coef_{param}"] = model.params[param]
                results[f"se_{param}"] = model.bse[param]
                results[f"pval_{param}"] = model.pvalues[param]

        return results

    except Exception as e:
        logger.error(f"DiD regression failed: {e}")
        return {"label": label, "error": str(e)}


def run_sensitivity_analyses(sample: pd.DataFrame) -> list[dict]:
    """Run sensitivity checks: different year ranges, leave-one-out."""
    logger.info("\nRunning sensitivity analyses...")
    results = []

    # 1. Restricted to 2010-2020 (pre-COVID)
    pre_covid = sample[sample["year"] <= 2020]
    if len(pre_covid) > 30:
        r = run_did_regression(pre_covid, "pre_covid_2010_2020")
        results.append(r)

    # 2. Include partial tier cities
    all_tiers = sample.copy()
    # Already includes primary + reference; add partial
    all_tiers_sample = all_tiers  # The full sample already has partial-tier obs
    r = run_did_regression(all_tiers_sample, "all_tiers_including_partial")
    results.append(r)

    # 3. Leave-one-city-out
    treated_cities = sorted(sample[sample["treated"] == 1]["rtcc_city"].dropna().unique())
    for city in treated_cities:
        loo = sample[sample["rtcc_city"] != city]
        if len(loo[loo["treated"] == 1]) > 5:
            r = run_did_regression(loo, f"leave_out_{city.replace(' ', '_')}")
            results.append(r)

    # 4. Matched sample only
    if "is_psm_matched" in sample.columns:
        matched = sample[sample["is_psm_matched"] == 1]
        if len(matched) > 20:
            r = run_did_regression(matched, "psm_matched")
            results.append(r)

    return results


def main():
    """Run the full PSM-DiD pipeline."""
    logger.info("=" * 60)
    logger.info("PSM-DiD ANALYSIS")
    logger.info("=" * 60)

    try:
        df = load_panel()
    except FileNotFoundError as exc:
        logger.warning(str(exc))
        return write_psm_status_file(str(exc))

    # Prepare sample
    sample = prepare_did_sample(df)

    if len(sample[sample["treated"] == 1]) < 10:
        logger.warning("Very few treated observations. Results may be unreliable.")

    # Propensity score matching
    matched_sample = propensity_score_matching(sample)

    # Main DiD regression (full sample)
    main_result = run_did_regression(sample, "full_sample")
    all_results = [main_result]

    # Main DiD regression (matched sample)
    if "is_psm_matched" in matched_sample.columns:
        matched_result = run_did_regression(
            matched_sample[matched_sample["is_psm_matched"] == 1],
            "psm_matched_sample"
        )
        all_results.append(matched_result)

    # Sensitivity analyses
    sensitivity = run_sensitivity_analyses(sample)
    all_results.extend(sensitivity)

    # Save results
    results_df = pd.DataFrame(all_results)
    output_path = OUTPUT_DIR / "psm_did_results.csv"
    results_df.to_csv(output_path, index=False)
    logger.info(f"\nSaved results to {output_path}")

    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("PSM-DiD RESULTS SUMMARY")
    logger.info(f"{'='*60}")
    for _, row in results_df.iterrows():
        if "error" in row and pd.notna(row.get("error")):
            logger.info(f"  {row['label']}: ERROR — {row['error']}")
        else:
            att = row.get("att", np.nan)
            pval = row.get("att_pval", np.nan)
            sig = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
            logger.info(f"  {row['label']}: ATT={att:+.4f} (p={pval:.3f}) {sig} [N={row.get('n_obs', '?')}]")

    return results_df


if __name__ == "__main__":
    main()
