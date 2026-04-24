"""
Panel v2: City Tiers + Propensity Scoring + Data Quality Flags

Takes master_analysis_panel_with_lemas.csv (output of lemas_integration.py),
corrects ORI-to-city mappings, assigns city tiers, computes propensity scores,
and outputs master_analysis_panel_v2.csv.

City Tiers (based on UCR clearance data coverage 2010-2024):
  - primary:     Best data coverage, deep per-city analysis
  - robustness:  Secondary, pooled analysis
  - reference:   Hartford — kept for GVPA study reference, not primary ITS
  - dropped:     Insufficient data (Newark, New Orleans)
  - comparison:  All other agencies

Author: Marcel Green <marcelo.green@yale.edu>
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors

PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from pipeline.config import DATA_CONFIG, get_rtcc_city_metadata

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent.parent
INPUT_PANEL = DATA_CONFIG.master_panel_with_lemas_csv
OUTPUT_PANEL = DATA_CONFIG.master_panel_v2_csv

# ── Corrected City Mapping ─────────────────────────────────────
# Original panel had some wrong ORI-to-city assignments.
# This maps: city_name → {correct ORI, RTCC year, tier, notes}

CITY_CONFIG = {
    city: {
        "ori9": meta["ori"],
        "rtcc_year": meta["rtcc_year"],
        "tier": meta.get("tier", "comparison"),
        "state": meta.get("state"),
        "notes": meta.get("notes", ""),
    }
    for city, meta in get_rtcc_city_metadata().items()
}

# ── Propensity Score Features ──────────────────────────────────
# LEMAS features used to match RTCC cities to similar comparison agencies

PROPENSITY_FEATURES = [
    "officers_per_10k",
    "budget_per_capita",
    "tech_score",
    "data_driven_score",
    "has_lpr",
    "has_gunshot_detection",
    "has_gis",
    "has_bwc",
]


def load_panel(path: Path = INPUT_PANEL) -> pd.DataFrame:
    """Load the LEMAS-enhanced master panel."""
    logger.info(f"Loading panel from {path}")
    df = pd.read_csv(path, low_memory=False)
    logger.info(f"Loaded {len(df):,} rows, {df['ori9'].nunique()} unique ORIs")
    return df


def correct_rtcc_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Re-assign rtcc_city labels using corrected ORI mapping.
    Removes old (incorrect) labels first, then applies correct ones.
    """
    logger.info("Correcting RTCC city labels...")

    # Clear all existing RTCC labels — cast to object first for mixed types
    df["rtcc_city"] = pd.Series([np.nan] * len(df), dtype="object")
    df["rtcc_year_impl"] = pd.Series([np.nan] * len(df), dtype="float64")
    df["post_rtcc"] = 0
    df["years_since_rtcc"] = np.nan
    df["city_tier"] = "comparison"
    df["is_comparison"] = 1

    # Apply corrected labels
    for city_name, config in CITY_CONFIG.items():
        ori = config["ori9"]
        rtcc_year = config["rtcc_year"]
        tier = config["tier"]

        mask = df["ori9"] == ori
        n_rows = mask.sum()

        if n_rows == 0:
            logger.warning(f"  {city_name} ({ori}): NOT FOUND in panel")
            continue

        df.loc[mask, "rtcc_city"] = city_name
        df.loc[mask, "rtcc_year_impl"] = rtcc_year
        df.loc[mask, "post_rtcc"] = (df.loc[mask, "year"] >= rtcc_year).astype(int)
        df.loc[mask, "years_since_rtcc"] = df.loc[mask, "year"] - rtcc_year
        df.loc[mask, "city_tier"] = tier
        df.loc[mask, "is_comparison"] = 0

        # Data quality: count years with clearance data (2010-2024)
        sub = df[mask & (df["year"] >= 2010)]
        cr_count = sub["clearance_rate"].notna().sum()
        h_count = (sub["homicides"] > 0).sum()

        logger.info(
            f"  {city_name} ({ori}): {n_rows} rows, tier={tier}, "
            f"post-2010 clearance={cr_count}/{len(sub)}, homicides>0={h_count}/{len(sub)}"
        )

    return df


def add_data_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add data quality flags for each agency-year."""
    # Has clearance data
    df["has_clearance"] = df["clearance_rate"].notna().astype(int)

    # Has LEMAS data
    df["has_lemas"] = df["ft_sworn"].notna().astype(int)

    # Homicide count > 0
    df["has_homicides"] = (df["homicides"] > 0).astype(int)

    # Analysis-ready: has clearance AND homicides > 0
    df["analysis_ready"] = (
        (df["clearance_rate"].notna()) & (df["homicides"] > 0)
    ).astype(int)

    return df


def compute_propensity_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute propensity scores: P(RTCC | LEMAS features).

    Uses logistic regression on agency-level LEMAS features.
    Treatment = any non-dropped, non-comparison RTCC city.
    """
    logger.info("Computing propensity scores...")

    # Get agency-level features (one row per ORI, using LEMAS 2020 data)
    # Use the most recent year with data for each agency
    agency_features = (
        df[df["ft_sworn"].notna()]
        .sort_values("year", ascending=False)
        .drop_duplicates(subset="ori9", keep="first")
        [["ori9", "rtcc_city", "city_tier"] + PROPENSITY_FEATURES]
        .copy()
    )

    # Drop agencies missing all propensity features
    agency_features = agency_features.dropna(subset=PROPENSITY_FEATURES, how="all")
    agency_features[PROPENSITY_FEATURES] = agency_features[PROPENSITY_FEATURES].fillna(0)

    # Treatment: primary + reference + partial tiers (not dropped, not comparison)
    treated_tiers = {"primary", "reference", "partial"}
    agency_features["treated"] = agency_features["city_tier"].isin(treated_tiers).astype(int)

    n_treated = agency_features["treated"].sum()
    n_control = len(agency_features) - n_treated
    logger.info(f"  Treated agencies: {n_treated}, Control agencies: {n_control}")

    if n_treated < 3:
        logger.warning("Too few treated agencies for propensity scoring. Skipping.")
        df["propensity_score"] = np.nan
        return df

    # Fit logistic regression
    X = agency_features[PROPENSITY_FEATURES].values
    y = agency_features["treated"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    lr = LogisticRegression(max_iter=1000, C=1.0, penalty="l2")
    lr.fit(X_scaled, y)

    # Predict propensity scores
    agency_features["propensity_score"] = lr.predict_proba(X_scaled)[:, 1]

    # Map back to full panel
    prop_map = agency_features.set_index("ori9")["propensity_score"].to_dict()
    df["propensity_score"] = df["ori9"].map(prop_map)

    # Log distribution
    logger.info(f"  Propensity score range: [{df['propensity_score'].min():.4f}, {df['propensity_score'].max():.4f}]")
    treated_ps = df[df["rtcc_city"].notna()]["propensity_score"]
    if len(treated_ps) > 0:
        logger.info(f"  Treated mean PS: {treated_ps.mean():.4f}")
    comp_ps = df[df["is_comparison"] == 1]["propensity_score"].dropna()
    if len(comp_ps) > 0:
        logger.info(f"  Comparison mean PS: {comp_ps.mean():.4f}")

    # Log coefficients
    logger.info("  Logistic regression coefficients:")
    for feat, coef in zip(PROPENSITY_FEATURES, lr.coef_[0]):
        logger.info(f"    {feat}: {coef:+.4f}")

    return df


def find_matched_comparisons(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each treated agency, find the nearest comparison match by propensity score.
    """
    logger.info("Finding matched comparisons...")

    # Get unique treated agencies
    treated = df[df["rtcc_city"].notna() & (df["city_tier"] != "dropped")]
    treated_agencies = treated[["ori9", "rtcc_city", "propensity_score"]].drop_duplicates(subset="ori9")

    # Get unique comparison agencies
    comp = df[df["is_comparison"] == 1]
    comp_agencies = comp[["ori9", "propensity_score"]].drop_duplicates(subset="ori9")
    comp_agencies = comp_agencies.dropna(subset=["propensity_score"])

    if len(treated_agencies) == 0 or len(comp_agencies) == 0:
        logger.warning("Insufficient agencies for matching.")
        df["matched_comparison_ori"] = np.nan
        return df

    # Nearest neighbor matching on propensity score
    nn = NearestNeighbors(n_neighbors=min(5, len(comp_agencies)), metric="euclidean")
    nn.fit(comp_agencies[["propensity_score"]].values)

    distances, indices = nn.kneighbors(treated_agencies[["propensity_score"]].values)

    # Map: treated ORI → best comparison ORI
    match_map = {}
    for i, (_, row) in enumerate(treated_agencies.iterrows()):
        best_idx = indices[i][0]
        match_map[row["ori9"]] = comp_agencies.iloc[best_idx]["ori9"]

    # Mark matched comparisons
    matched_comp_oris = set(match_map.values())
    df["is_matched_comparison"] = df["ori9"].isin(matched_comp_oris).astype(int)

    logger.info(f"  Matched {len(match_map)} treated agencies to comparisons")
    for treated_ori, comp_ori in match_map.items():
        city = treated[treated["ori9"] == treated_ori]["rtcc_city"].iloc[0]
        logger.info(f"    {city} ({treated_ori}) → {comp_ori}")

    return df


def compute_analysis_sample(df: pd.DataFrame) -> pd.DataFrame:
    """
    Define the analysis sample: agencies with sufficient data for DiD.
    Requires: clearance_rate not null, homicides > 0, LEMAS data.
    """
    # Core sample: analysis_ready == 1 and year >= 2010
    df["in_did_sample"] = (
        (df["analysis_ready"] == 1) &
        (df["year"] >= 2010) &
        (df["propensity_score"].notna())
    ).astype(int)

    # Narrower sample for primary analysis (primary + reference tiers only)
    primary_tiers = {"primary", "reference"}
    df["in_primary_sample"] = (
        (df["in_did_sample"] == 1) &
        (df["city_tier"].isin(primary_tiers) | (df["is_comparison"] == 1))
    ).astype(int)

    # Log sample sizes
    logger.info(f"\nAnalysis sample sizes:")
    logger.info(f"  Total panel: {len(df):,}")
    logger.info(f"  Analysis-ready (CR + homicides > 0): {df['analysis_ready'].sum():,}")
    logger.info(f"  DiD sample (2010+, has LEMAS): {df['in_did_sample'].sum():,}")
    logger.info(f"  Primary sample (primary/ref + comp): {df['in_primary_sample'].sum():,}")

    # Treated obs by tier
    for tier in ["primary", "reference", "partial", "dropped"]:
        n = df[(df["city_tier"] == tier) & (df["in_did_sample"] == 1)].shape[0]
        logger.info(f"  {tier} tier in DiD sample: {n} obs")

    return df


def build_panel_v2(input_path: Path = INPUT_PANEL, output_path: Path = OUTPUT_PANEL) -> pd.DataFrame:
    """Build the enhanced panel v2 with city tiers and propensity scores."""
    logger.info("=" * 60)
    logger.info("PANEL V2: City Tiers + Propensity Scoring")
    logger.info("=" * 60)

    # Load
    df = load_panel(input_path)

    # Correct RTCC labels
    df = correct_rtcc_labels(df)

    # Data quality flags
    df = add_data_quality_flags(df)

    # Propensity scores
    df = compute_propensity_scores(df)

    # Matched comparisons
    df = find_matched_comparisons(df)

    # Analysis sample definitions
    df = compute_analysis_sample(df)

    # Save
    df.to_csv(output_path, index=False)
    logger.info(f"\nSaved panel v2 to {output_path}")
    logger.info(f"Columns ({len(df.columns)}): {list(df.columns)}")

    # Final summary
    logger.info(f"\n{'='*60}")
    logger.info("PANEL V2 SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total rows: {len(df):,}")
    logger.info(f"Unique ORIs: {df['ori9'].nunique()}")
    logger.info(f"Year range: {df['year'].min():.0f}-{df['year'].max():.0f}")

    logger.info(f"\nCity tiers:")
    for tier in ["primary", "reference", "partial", "dropped", "comparison"]:
        cities = sorted(df[df["city_tier"] == tier]["rtcc_city"].dropna().unique())
        n_oris = df[df["city_tier"] == tier]["ori9"].nunique()
        n_rows = df[df["city_tier"] == tier].shape[0]
        if tier == "comparison":
            logger.info(f"  {tier}: {n_oris} agencies, {n_rows:,} rows")
        else:
            logger.info(f"  {tier}: {cities} ({n_rows} rows)")

    logger.info(f"\nDiD sample by city:")
    did = df[df["in_did_sample"] == 1]
    for city in sorted(did[did["rtcc_city"].notna()]["rtcc_city"].unique()):
        sub = did[did["rtcc_city"] == city]
        pre = sub[sub["post_rtcc"] == 0]
        post = sub[sub["post_rtcc"] == 1]
        logger.info(
            f"  {city}: {len(sub)} obs (pre={len(pre)}, post={len(post)}), "
            f"mean CR={sub['clearance_rate'].mean():.1%}"
        )

    return df


if __name__ == "__main__":
    build_panel_v2()
