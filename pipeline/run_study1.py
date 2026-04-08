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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PIPELINE_DIR = Path(__file__).parent
sys.path.insert(0, str(PIPELINE_DIR))

RESULTS_BASE = Path(__file__).parent.parent / "results" / "study1_rtcc"


def step_its():
    """Step 1: Bayesian Interrupted Time Series."""
    logger.info("=" * 50)
    logger.info("STEP 1: Bayesian ITS")
    logger.info("=" * 50)
    from models.bayesian_its import run
    run(str(RESULTS_BASE / "bayesian_its"))


def step_classifier():
    """Step 2: XGBoost/RF/LR Classifier + SHAP."""
    logger.info("=" * 50)
    logger.info("STEP 2: Classifier + SHAP")
    logger.info("=" * 50)
    from run_classifier import run
    run(str(RESULTS_BASE))


def step_prophet():
    """Step 3: Prophet Counterfactual Forecasting."""
    logger.info("=" * 50)
    logger.info("STEP 3: Prophet Counterfactual")
    logger.info("=" * 50)
    from models.prophet_forecast import run
    run(str(RESULTS_BASE / "prophet"))


def step_monte_carlo():
    """Step 4: Monte Carlo Simulation."""
    logger.info("=" * 50)
    logger.info("STEP 4: Monte Carlo Simulation")
    logger.info("=" * 50)
    from models.monte_carlo import run
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
