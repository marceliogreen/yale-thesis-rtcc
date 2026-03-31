"""
Causal Forest Model for RTCC Thesis Pipeline

Uses EconML CausalForestDML with double machine learning
to estimate heterogeneous treatment effects of RTCCs on clearance rates.

Treatment: post_rtcc (binary)
Outcome: clearance_rate (from BJS/FBI/ICPSR - real data only)
Covariates: population, region, pre_trend, years_since_rtcc, vendor

Author: Marcelo Green <marcelo.green@yale.edu>
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv

# EconML for causal inference
try:
    from econml.dml import CausalForestDML
    from econml.inference import BootstrapInference
    ECONML_AVAILABLE = True
except ImportError:
    ECONML_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("EconML not installed. Install with: pip install econml")

# Scikit-learn for ML models
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class CausalResults:
    """Container for causal inference results."""
    ate: float  # Average Treatment Effect
    ate_ci_lower: float  # 95% CI lower bound
    ate_ci_upper: float  # 95% CI upper bound
    ate_pvalue: float  # P-value for ATE
    cate_by_city: Dict[str, float]  # CATE per city
    cate_by_quartile: Dict[str, float]  # CATE by population quartile
    cate_by_vendor: Dict[str, float]  # CATE by vendor
    cate_df: pd.DataFrame  # Full CATE DataFrame
    n_observations: int
    model_converged: bool


class RTCCCausalForest:
    """
    Causal forest estimator for RTCC heterogeneous treatment effects.

    Uses EconML CausalForestDML with double machine learning.

    Model specification:
    - Treatment (T): post_rtcc binary (1 if year >= rtcc_year, 0 otherwise)
    - Outcome (Y): clearance_rate (real data from BJS/FBI/ICPSR)
    - Covariates (X): population, region, pre_trend, years_since_rtcc
    - Controls (W): Additional confounders (agency_budget, officer_count from LEMAS)

    Configuration:
    - n_estimators: 1000
    - max_depth: 10
    - min_samples_leaf: 10
    - max_samples: 0.8 (for honesty/subsampling)
    - discrete_treatment: True (binary treatment)
    - cv: 5 (5-fold DML)
    """

    def __init__(
        self,
        n_estimators: int = 1000,
        max_depth: int = 10,
        min_samples_leaf: int = 10,
        max_samples: float = 0.8,
        random_state: int = 42,
        results_dir: Optional[Path] = None,
    ):
        """
        Initialize the causal forest model.

        Args:
            n_estimators: Number of trees (default: 1000 for stable CATE)
            max_depth: Maximum tree depth (default: 10)
            min_samples_leaf: Min samples per leaf (default: 10)
            max_samples: Subsampling ratio for honesty (default: 0.8)
            random_state: Random seed
            results_dir: Where to save outputs
        """
        if not ECONML_AVAILABLE:
            raise ImportError(
                "EconML is required but not installed. "
                "Install with: pip install econml"
            )

        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.max_samples = max_samples
        self.random_state = random_state

        if results_dir is None:
            results_dir = Path(__file__).parent.parent.parent / "results" / "study1_rtcc"
        self.results_dir = Path(results_dir)

        # Create output directories
        (self.results_dir / "figures" / "causal").mkdir(parents=True, exist_ok=True)
        (self.results_dir / "tables").mkdir(parents=True, exist_ok=True)

        # Model placeholder
        self.model = None
        self.results = None

        # Feature names for interpretability
        self.feature_names = None

        logger.info(f"Initialized RTCCCausalForest with n_estimators={n_estimators}")

    def fit(
        self,
        Y: np.ndarray,
        T: np.ndarray,
        X: pd.DataFrame,
        W: Optional[pd.DataFrame] = None,
    ) -> None:
        """
        Fit causal forest using double ML estimation.

        Args:
            Y: Outcome variable (clearance_rate, 0-1 scale)
            T: Treatment variable (post_rtcc binary)
            X: Heterogeneity covariates (population, region, pre_trend, years_since_rtcc)
            W: Control variables (optional confounders)

        The model uses:
        - model_y: RandomForestRegressor (outcome model)
        - model_t: RandomForestClassifier (treatment model)
        """
        logger.info(f"Fitting causal forest with {len(Y)} observations")

        # Validate inputs
        assert len(Y) == len(T) == len(X), "Y, T, X must have same length"
        assert T.ndim == 1, "Treatment T must be 1-dimensional"
        assert np.isin(T, [0, 1]).all(), "Treatment T must be binary (0/1)"

        # Handle controls
        if W is None:
            W = np.empty((len(Y), 0))
        elif isinstance(W, pd.DataFrame):
            self.control_names = W.columns.tolist()
            W = W.values
        else:
            self.control_names = []

        # Store feature names
        if isinstance(X, pd.DataFrame):
            self.feature_names = X.columns.tolist()
            X = X.values
        else:
            self.feature_names = [f"X_{i}" for i in range(X.shape[1])]

        # Check for sufficient variation in treatment
        n_treated = T.sum()
        n_control = len(T) - n_treated
        logger.info(f"Treatment: {n_treated} treated, {n_control} control")

        if n_treated < 10 or n_control < 10:
            logger.warning("Very few treated or control units. Results may be unreliable.")

        # Define ML models for double ML
        model_y = RandomForestRegressor(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=5,
            random_state=self.random_state,
        )

        model_t = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            min_samples_leaf=5,
            random_state=self.random_state,
        )

        # Initialize and fit causal forest
        self.model = CausalForestDML(
            model_y=model_y,
            model_t=model_t,
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            min_samples_leaf=self.min_samples_leaf,
            max_samples=self.max_samples,
            discrete_treatment=True,
            random_state=self.random_state,
            cv=5,
        )

        # Fit the model
        self.model.fit(Y=Y, T=T, X=X, W=W)

        logger.info("Causal forest fitted successfully")

    def estimate_ate(
        self,
        alpha: float = 0.05,
        n_bootstrap: int = 2000,
    ) -> Tuple[float, Tuple[float, float], float]:
        """
        Compute Average Treatment Effect with confidence interval.

        Args:
            alpha: Significance level (default: 0.05 for 95% CI)
            n_bootstrap: Number of bootstrap samples for inference

        Returns:
            (ATE, (CI_lower, CI_upper), p_value)
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        logger.info(f"Estimating ATE with {n_bootstrap} bootstrap samples")

        # Get treatment effect
        treatment_effect = self.model.effect(X=None if self.feature_names is None else np.zeros((1, len(self.feature_names))))

        # Bootstrap inference
        self.model.inference = BootstrapInference(n_bootstrap_samples=n_bootstrap)
        te_interval = self.model.effect_interval(X=None, alpha=alpha)

        ate = float(treatment_effect[0])
        ate_ci_lower = float(te_interval[0][0])
        ate_ci_upper = float(te_interval[1][0])

        # Approximate p-value (two-sided)
        # Check if CI includes 0
        if ate_ci_lower <= 0 <= ate_ci_upper:
            p_value = 1.0  # Not significant
        else:
            # Rough approximation based on CI width
            se = (ate_ci_upper - ate_ci_lower) / (2 * 1.96)
            z_score = ate / se
            from scipy.stats import norm
            p_value = 2 * (1 - norm.cdf(abs(z_score)))

        logger.info(f"ATE: {ate:.4f} [{ate_ci_lower:.4f}, {ate_ci_upper:.4f}], p={p_value:.4f}")

        return ate, (ate_ci_lower, ate_ci_upper), p_value

    def compute_cate_by_city(
        self,
        X: pd.DataFrame,
        city_ids: np.ndarray,
    ) -> pd.Series:
        """
        Compute CATE for each city.

        Args:
            X: Covariates for each observation
            city_ids: Array of city names for each observation

        Returns:
            Series with city-level average CATE
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        logger.info("Computing CATE by city")

        # Get CATE for all observations
        if isinstance(X, pd.DataFrame):
            X_values = X.values
        else:
            X_values = X

        cate = self.model.effect(X=X_values)

        # Aggregate by city
        df = pd.DataFrame({"city": city_ids, "cate": cate})
        cate_by_city = df.groupby("city")["cate"].agg(["mean", "count", "std"])
        cate_by_city = cate_by_city.rename(columns={"mean": "cate", "count": "n"})

        logger.info(f"Computed CATE for {len(cate_by_city)} cities")

        return cate_by_city

    def compute_cate_by_quartile(
        self,
        X: pd.DataFrame,
        population: pd.Series,
    ) -> Dict[str, float]:
        """
        Compute CATE by population quartile.

        Args:
            X: Covariates for each observation
            population: Population values

        Returns:
            Dict mapping quartile to CATE
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        logger.info("Computing CATE by population quartile")

        # Get CATE
        if isinstance(X, pd.DataFrame):
            X_values = X.values
        else:
            X_values = X

        cate = self.model.effect(X=X_values)

        # Compute quartiles
        quartiles = pd.qcut(population, q=4, labels=["Q1", "Q2", "Q3", "Q4"])

        df = pd.DataFrame({"quartile": quartiles, "cate": cate})
        cate_by_quartile = df.groupby("quartile")["cate"].mean().to_dict()

        logger.info(f"CATE by quartile: {cate_by_quartile}")

        return cate_by_quartile

    def compute_cate_by_vendor(
        self,
        X: pd.DataFrame,
        vendor: pd.Series,
    ) -> Dict[str, float]:
        """
        Compute CATE by RTCC vendor.

        Args:
            X: Covariates for each observation
            vendor: Vendor names (Motorola, ShotSpotter, etc.)

        Returns:
            Dict mapping vendor to CATE
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        logger.info("Computing CATE by vendor")

        if isinstance(X, pd.DataFrame):
            X_values = X.values
        else:
            X_values = X

        cate = self.model.effect(X=X_values)

        # Filter to treated units only (where vendor is not null/unknown)
        df = pd.DataFrame({"vendor": vendor, "cate": cate})
        df = df[df["vendor"].notna() & (df["vendor"] != "Unknown")]

        cate_by_vendor = df.groupby("vendor")["cate"].agg(["mean", "count"])
        cate_by_vendor = cate_by_vendor.rename(columns={"mean": "cate", "count": "n"})

        logger.info(f"CATE by vendor:\n{cate_by_vendor}")

        return cate_by_vendor.to_dict()["cate"]

    def plot_cate_distribution(
        self,
        cate: np.ndarray,
        bins: int = 50,
    ) -> None:
        """
        Plot CATE distribution histogram.

        Args:
            cate: CATE values for all observations
            bins: Number of bins for histogram
        """
        logger.info("Plotting CATE distribution")

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.hist(cate, bins=bins, edgecolor="black", alpha=0.7)
        ax.axvline(cate.mean(), color="red", linestyle="--", label=f"Mean: {cate.mean():.3f}")
        ax.axvline(0, color="black", linestyle="-", linewidth=1)

        ax.set_xlabel("CATE (Treatment Effect on Clearance Rate)", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title("Distribution of Conditional Average Treatment Effects", fontsize=14)
        ax.legend()

        output_path = self.results_dir / "figures" / "causal" / "cate_distribution.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved CATE distribution plot to {output_path}")

    def plot_cate_by_feature(
        self,
        X: pd.DataFrame,
        cate: np.ndarray,
        feature_name: str,
        feature_label: Optional[str] = None,
    ) -> None:
        """
        Plot CATE vs continuous feature.

        Args:
            X: Covariates dataframe
            cate: CATE values
            feature_name: Column name in X
            feature_label: Label for plot (defaults to feature_name)
        """
        if feature_name not in X.columns:
            logger.warning(f"Feature {feature_name} not in X")
            return

        logger.info(f"Plotting CATE vs {feature_name}")

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.scatter(X[feature_name], cate, alpha=0.5, s=20)

        # Add trend line
        from scipy.stats import linregress
        slope, intercept, r_value, p_value, std_err = linregress(
            X[feature_name], cate
        )
        x_line = np.linspace(X[feature_name].min(), X[feature_name].max(), 100)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, "r-", label=f"Trend: r={r_value:.2f}")

        ax.set_xlabel(feature_label or feature_name, fontsize=12)
        ax.set_ylabel("CATE", fontsize=12)
        ax.set_title(f"CATE by {feature_label or feature_name}", fontsize=14)
        ax.legend()

        output_path = self.results_dir / "figures" / "causal" / f"cate_by_{feature_name}.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved plot to {output_path}")

    def save_results(
        self,
        cate_df: pd.DataFrame,
    ) -> None:
        """
        Save CATE results to CSV files.

        Args:
            cate_df: DataFrame with CATE values and metadata
        """
        logger.info("Saving CATE results")

        # Save full CATE dataframe
        output_path = self.results_dir / "tables" / "cate_all.csv"
        cate_df.to_csv(output_path, index=False)
        logger.info(f"Saved full CATE to {output_path}")

    def summarize(self) -> CausalResults:
        """
        Generate summary of causal inference results.

        Returns:
            CausalResults dataclass with all key findings
        """
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")

        # Estimate ATE
        ate, (ci_lower, ci_upper), p_value = self.estimate_ate()

        # Create placeholder results (would be populated by compute_cate_* methods)
        results = CausalResults(
            ate=ate,
            ate_ci_lower=ci_lower,
            ate_ci_upper=ci_upper,
            ate_pvalue=p_value,
            cate_by_city={},
            cate_by_quartile={},
            cate_by_vendor={},
            cate_df=pd.DataFrame(),
            n_observations=self.model.n_samples,
            model_converged=True,
        )

        self.results = results
        return results


def main():
    """CLI interface for the causal forest."""
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Causal Forest")
    parser.add_argument("--data", type=str, help="Input data CSV path")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    print("RTCC Causal Forest Model")
    print("=" * 50)
    print("\nTo use this model:")
    print("1. Prepare data with clearance_rate, post_rtcc, and covariates")
    print("2. Instantiate: model = RTCCCausalForest()")
    print("3. Fit: model.fit(Y, T, X)")
    print("4. Estimate: model.estimate_ate()")
    print("5. Heterogeneity: model.compute_cate_by_city()")


if __name__ == "__main__":
    main()
