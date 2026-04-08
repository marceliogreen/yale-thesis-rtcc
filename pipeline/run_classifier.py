"""
Run Classifier + SHAP Analysis

Orchestrator that feeds master_analysis_panel.csv into the existing
RTCCClearanceClassifier (XGBoost, RandomForest, LogisticRegression),
trains models with TimeSeriesSplit CV, and generates SHAP plots.

Author: Marcel Green <marcelo.green@yale.edu>
"""

import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Add pipeline to path
PIPELINE_DIR = Path(__file__).parent
sys.path.insert(0, str(PIPELINE_DIR))

from models.clearance_classifier import RTCCClearanceClassifier

# State-to-region mapping
STATE_TO_REGION = {
    "CT": "Northeast", "ME": "Northeast", "MA": "Northeast", "NH": "Northeast",
    "RI": "Northeast", "VT": "Northeast", "NJ": "Northeast", "NY": "Northeast",
    "PA": "Northeast",
    "IL": "Midwest", "IN": "Midwest", "IA": "Midwest", "KS": "Midwest",
    "MI": "Midwest", "MN": "Midwest", "MO": "Midwest", "NE": "Midwest",
    "ND": "Midwest", "OH": "Midwest", "SD": "Midwest", "WI": "Midwest",
    "FL": "South", "GA": "South", "AL": "South", "AR": "South", "DE": "South",
    "KY": "South", "LA": "South", "MD": "South", "MS": "South", "NC": "South",
    "OK": "South", "SC": "South", "TN": "South", "TX": "South", "VA": "South",
    "WV": "South", "DC": "South",
    "AZ": "West", "CA": "West", "CO": "West", "HI": "West", "ID": "West",
    "MT": "West", "NV": "West", "NM": "West", "OR": "West", "UT": "West",
    "WA": "West", "WY": "West", "AK": "West",
}

# RTCC cities with implementation years
RTCC_CITY_YEARS = {
    "Hartford": 2016,
    "Miami": 2016,
    "St. Louis": 2015,
    "Newark": 2018,
    "New Orleans": 2017,
    "Albuquerque": 2020,
    "Fresno": 2018,
    "Chicago": 2017,
}


def load_and_prepare_data(panel_path: str) -> pd.DataFrame:
    """Load master panel and prepare for classification."""
    df = pd.read_csv(panel_path)
    logger.info(f"Loaded panel: {len(df)} rows")

    # Filter to records with actual clearance data and homicides
    df = df[df["homicides"] >= 1].copy()
    df = df.dropna(subset=["clearance_rate"]).copy()
    logger.info(f"After filtering (homicides >= 1, clearance_rate not null): {len(df)} rows")

    # Add region
    df["region"] = df["state_abb"].map(STATE_TO_REGION).fillna("Unknown")

    # Add city name for RTCC cities (from rtcc_city flag)
    # The panel uses ori9 as identifier — map to city names where possible
    # For non-RTCC cities, use agency_name
    df["city"] = df["agency_name"].fillna("Unknown")

    # For the target: binary classification — clearance >= 50%
    df["clearance_binary"] = (df["clearance_rate"] >= 0.5).astype(int)
    logger.info(f"Positive class (clearance >= 50%): {df['clearance_binary'].mean():.1%}")

    # Log RTCC city coverage
    if "rtcc_city" in df.columns:
        rtcc_data = df[df["rtcc_city"] == True]
        logger.info(f"RTCC city observations: {len(rtcc_data)}")
        for city_name, year in RTCC_CITY_YEARS.items():
            # Match by various possible identifiers
            city_mask = df["city"].str.contains(city_name, case=False, na=False)
            if city_mask.any():
                logger.info(f"  {city_name}: {city_mask.sum()} observations")

    return df


def run(output_dir: str = "results/study1_rtcc"):
    """Run the full classifier pipeline."""
    # Search for the panel data in multiple locations
    candidates = [
        Path(__file__).parent.parent.parent / "thesis" / "data" / "master_analysis_panel.csv",
        Path(__file__).parent.parent / "data" / "master_analysis_panel.csv",
        Path("thesis/data/master_analysis_panel.csv"),
    ]
    panel_path = None
    for c in candidates:
        if c.exists():
            panel_path = c
            break
    if panel_path is None:
        raise FileNotFoundError(f"master_analysis_panel.csv not found in: {[str(c) for c in candidates]}")

    results_dir = Path(output_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    df = load_and_prepare_data(str(panel_path))

    # Initialize classifier
    classifier = RTCCClearanceClassifier(results_dir=results_dir)

    # Build feature matrix
    # The classifier expects a df with city, year, homicide_count, population, region, etc.
    feature_df = df.rename(columns={
        "homicides": "homicide_count",
        "state_abb": "state_fe",
    })

    # Ensure required columns
    for col in ["homicide_count", "population", "region", "state_fe"]:
        if col not in feature_df.columns:
            if col == "homicide_count":
                feature_df[col] = feature_df.get("homicides", 0)
            elif col == "population":
                feature_df[col] = 100000  # default mid-size
            else:
                feature_df[col] = "Unknown"

    logger.info("Building feature matrix...")
    X, y = classifier.build_feature_matrix(feature_df, RTCC_CITY_YEARS)

    logger.info(f"Feature matrix shape: {X.shape}, Target distribution: {np.bincount(y)}")

    # Train models
    logger.info("Training models (XGBoost, RandomForest, LogisticRegression)...")
    models = classifier.train_models(X, y)

    # Evaluate
    logger.info("Evaluating models...")
    metrics = classifier.evaluate(X, y)

    for name, m in metrics.items():
        print(f"  {name}: AUC={m.auc_roc:.3f}, F1={m.f1:.3f}, Precision={m.precision:.3f}, Recall={m.recall:.3f}")

    # SHAP analysis
    logger.info("Running SHAP analysis...")
    for model_name in ["xgboost", "random_forest"]:
        try:
            classifier.shap_analysis(X, model_name=model_name)
        except Exception as e:
            logger.warning(f"SHAP failed for {model_name}: {e}")

    # Save results
    classifier.save_results()
    classifier.report_data_coverage()

    logger.info(f"Results saved to {results_dir}")
    return metrics


if __name__ == "__main__":
    run()
