"""
Build submission-safe fallback artifacts from checked-in local data.

This module reconstructs lightweight comparison-pool inputs used by several
robustness scripts when the original `thesis/data/...` intermediates are not
available in the repository snapshot.
"""

from pathlib import Path
import logging
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

import numpy as np
import pandas as pd

from pipeline.config import DATA_CONFIG

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = BASE_DIR / "results" / "study1_rtcc"
COMPARISON_POOL_OUT = DATA_CONFIG.master_panel_csv.parent / "comparison_pool_yearly.csv"
PSM_STATUS_OUT = RESULTS_DIR / "tables" / "psm_did_results.csv"


def build_comparison_pool_yearly(
    master_panel_path: Path = DATA_CONFIG.master_panel_csv,
    output_path: Path = COMPARISON_POOL_OUT,
) -> pd.DataFrame:
    """
    Reconstruct a comparison-pool yearly file from the checked-in master panel.

    The original project used a richer raw-Kaplan-derived file under
    `thesis/data/comparison_pool_yearly.csv`. For submission safety, this
    fallback preserves the columns required by the checked-in robustness
    scripts using the harmonized counts already present in `master_analysis_panel.csv`.
    """
    logger.info(f"Loading master panel from {master_panel_path}")
    df = pd.read_csv(master_panel_path, low_memory=False)

    comp = df[df["is_comparison"] == 1].copy()
    if comp.empty:
        raise ValueError("No comparison agencies found in master panel")

    comp["ori"] = comp["ori9"]
    comp["actual_murder"] = comp["homicides"].fillna(0)
    comp["actual_manslaughter"] = 0
    comp["total_cleared_murder"] = comp["cleared"].fillna(0)
    comp["total_cleared_manslaughter"] = 0
    comp["population_1"] = comp["population"]
    comp["census_name"] = comp["agency_name"]
    comp["crosswalk_agency_name"] = comp["agency_name"]
    comp["state"] = comp.get("state_abb")

    keep_cols = [
        "ori",
        "ori9",
        "agency_name",
        "crosswalk_agency_name",
        "census_name",
        "state",
        "state_abb",
        "year",
        "population_1",
        "population",
        "actual_murder",
        "actual_manslaughter",
        "total_cleared_murder",
        "total_cleared_manslaughter",
        "homicides",
        "cleared",
        "clearance_rate",
    ]
    keep_cols = [col for col in keep_cols if col in comp.columns]
    comp = comp[keep_cols].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    comp.to_csv(output_path, index=False)
    logger.info(f"Saved fallback comparison pool to {output_path} ({len(comp)} rows)")
    return comp


def write_psm_status_file(
    reason: str,
    output_path: Path = PSM_STATUS_OUT,
) -> pd.DataFrame:
    """
    Write a small status CSV when the original PSM panel is unavailable.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    status = pd.DataFrame(
        [
            {
                "label": "omitted_submission_snapshot",
                "status": "omitted",
                "reason": reason,
                "att": np.nan,
                "att_pval": np.nan,
                "n_obs": np.nan,
            }
        ]
    )
    status.to_csv(output_path, index=False)
    logger.info(f"Saved PSM status file to {output_path}")
    return status


if __name__ == "__main__":
    build_comparison_pool_yearly()
