"""
Study 1 Master Orchestrator

Runs all RTCC analyses in sequence:
1. Bayesian ITS (or MLE fallback)
2. Classifier + SHAP
3. Prophet counterfactual
4. Monte Carlo simulation

Usage:
    python run_study1.py              # Run all
    python run_study1.py --step its   # Run only ITS
    python run_study1.py --step all   # Run all (default)

Author: Marcel Green <marcelo.green@yale.edu>
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from pipeline.config import DATA_CONFIG, PSM_CONFIG, RTCC_CONFIG
from pipeline.utils import validate_analysis_panel

RESULTS_BASE = Path(__file__).parent.parent / "results" / "study1_rtcc"


def run_preflight_validation() -> None:
    """Validate panel assumptions before running Study 1 models."""
    panel_path = DATA_CONFIG.analysis_ready_panel_csv
    if not panel_path.exists():
        panel_path = DATA_CONFIG.master_panel_csv

    if not panel_path.exists():
        logger.warning("No panel file found for preflight validation; skipping validation step.")
        return

    logger.info("Running preflight data validation on %s", panel_path)
    df = pd.read_csv(panel_path, low_memory=False)

    candidate_covariates = [*PSM_CONFIG.pscore_controls, *PSM_CONFIG.outcome_controls]
    available_covariates = [c for c in candidate_covariates if c in df.columns]

    validate_analysis_panel(
        df,
        {
            "clearance_rate_col": "clearance_rate",
            "homicide_col": "homicides",
            "covariates": available_covariates,
            "min_years": RTCC_CONFIG.pretreatment_years,
        },
    )


def step_its():
    """Step 1: Bayesian Interrupted Time Series."""
    logger.info("=" * 50)
    logger.info("STEP 1: Bayesian ITS")
    logger.info("=" * 50)
    from pipeline.models.bayesian_its import run
    run(str(RESULTS_BASE / "bayesian_its"))


def step_classifier():
    """Step 2: XGBoost/RF/LR Classifier + SHAP."""
    logger.info("=" * 50)
    logger.info("STEP 2: Classifier + SHAP")
    logger.info("=" * 50)
    from pipeline.run_classifier import run
    run(str(RESULTS_BASE))


def step_prophet():
    """Step 3: Prophet Counterfactual Forecasting."""
    logger.info("=" * 50)
    logger.info("STEP 3: Prophet Counterfactual")
    logger.info("=" * 50)
    from pipeline.models.prophet_forecast import run
    run(str(RESULTS_BASE / "prophet"))


def step_monte_carlo():
    """Step 4: Monte Carlo Simulation."""
    logger.info("=" * 50)
    logger.info("STEP 4: Monte Carlo Simulation")
    logger.info("=" * 50)
    from pipeline.models.monte_carlo import run
    run(str(RESULTS_BASE / "monte_carlo"))


STEPS = {
    "its": step_its,
    "classifier": step_classifier,
    "prophet": step_prophet,
    "monte_carlo": step_monte_carlo,
}


def main():
    parser = argparse.ArgumentParser(description="Study 1 RTCC Analysis Pipeline")
    parser.add_argument(
        "--step",
        choices=list(STEPS.keys()) + ["all"],
        default="all",
        help="Which step to run (default: all)",
    )
    args = parser.parse_args()

    if args.step == "all":
        steps_to_run = list(STEPS.keys())
    else:
        steps_to_run = [args.step]

    start_time = time.time()

    try:
        run_preflight_validation()
    except Exception as e:
        logger.error("Preflight validation failed: %s", e)
        raise

    for step_name in steps_to_run:
        step_start = time.time()
        try:
            STEPS[step_name]()
            elapsed = time.time() - step_start
            logger.info(f"Step '{step_name}' completed in {elapsed:.1f}s")
        except Exception as e:
            logger.error(f"Step '{step_name}' FAILED: {e}")
            import traceback
            traceback.print_exc()

    total = time.time() - start_time
    logger.info(f"\nPipeline complete. Total time: {total:.1f}s")
    logger.info(f"Results in: {RESULTS_BASE}")


if __name__ == "__main__":
    main()
