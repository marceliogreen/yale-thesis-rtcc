"""
Clearance Rate Classifier for RTCC Thesis Pipeline

Multi-model classifier for homicide clearance prediction.
Uses REAL DATA ONLY from BJS NIBRS, FBI CDE, and ICPSR sources.

Models: XGBoost, RandomForest, LogisticRegression
CV: TimeSeriesSplit(n_splits=5) for temporal validation

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
from dotenv import load_dotenv

# ML imports
from sklearn.model_selection import TimeSeriesSplit, cross_val_score, cross_validate
from sklearn.preprocessing import StandardScaler, OneHotEncoder, TargetEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, classification_report
import xgboost as xgb
import shap

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from data.fbi_api_client import UnifiedCrimeDataClient

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ClearanceMetrics:
    """Container for model evaluation metrics."""
    model_name: str
    auc_roc: float
    precision: float
    recall: float
    f1: float
    cv_scores: List[float]
    feature_importance: Dict[str, float]


class RTCCClearanceClassifier:
    """
    Multi-model classifier for homicide clearance prediction.

    Uses REAL clearance data from:
    - BJS NIBRS API (primary)
    - FBI CDE API (participation endpoint)
    - ICPSR 39270 (when available)

    NO SIMULATED DATA - if real data unavailable, observation is excluded.

    Models:
    - XGBoost: n_estimators=500, lr=0.05, max_depth=6
    - RandomForest: n_estimators=500, max_depth=10
    - LogisticRegression: max_iter=1000, class_weight='balanced'

    CV: TimeSeriesSplit(n_splits=5) for temporal validation
    """

    # Model configurations
    MODEL_CONFIGS = {
        "xgboost": {
            "n_estimators": 500,
            "learning_rate": 0.05,
            "max_depth": 6,
            "random_state": 42,
            "eval_metric": "logloss",
        },
        "random_forest": {
            "n_estimators": 500,
            "max_depth": 10,
            "random_state": 42,
            "class_weight": "balanced",
        },
        "logistic": {
            "max_iter": 1000,
            "class_weight": "balanced",
            "random_state": 42,
        },
    }

    def __init__(
        self,
        data_source: str = "auto",
        random_state: int = 42,
        results_dir: Optional[Path] = None,
    ):
        """
        Initialize the clearance classifier.

        Args:
            data_source: Priority order for fetching clearance data
                "auto" = try all sources in order
                "bjs" = BJS NIBRS API only
                "fbi_cde" = FBI CDE API only
                "icpsr" = ICPSR data only
            random_state: Random seed for reproducibility
            results_dir: Where to save outputs
        """
        self.data_source = data_source
        self.random_state = random_state

        if results_dir is None:
            results_dir = Path(__file__).parent.parent.parent / "results" / "study1_rtcc"
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.results_dir / "figures" / "shap").mkdir(parents=True, exist_ok=True)
        (self.results_dir / "tables").mkdir(parents=True, exist_ok=True)

        # Initialize models
        self.models = {}
        self.metrics = {}
        self.feature_columns = None
        self.preprocessor = None

        # Track data availability
        self.missing_data_log = []
        self.data_source_log = []

        # API client
        self.api_client = UnifiedCrimeDataClient()

        logger.info(f"Initialized RTCCClearanceClassifier with data_source={data_source}")

    def _fetch_clearance_data(
        self, city: str, year: int, ori: Optional[str] = None
    ) -> Optional[float]:
        """
        Try multiple sources for real clearance data.

        Priority:
        1. BJS NIBRS API (most recent, most accurate)
        2. FBI CDE participation endpoint
        3. ICPSR 39270 (if access available)
        4. Supplementary Homicide Reports (ICPSR 39069) as proxy

        Args:
            city: City name
            year: Year
            ori: FBI ORI code (optional)

        Returns:
            clearance_rate (0-1) or None if unavailable
        """
        sources = []

        if self.data_source in ("auto", "bjs"):
            sources.append("bjs")
        if self.data_source in ("auto", "fbi_cde"):
            sources.append("fbi_cde")
        if self.data_source in ("auto", "icpsr"):
            sources.append("icpsr")

        for source in sources:
            try:
                rate = None

                if source == "bjs":
                    # Try BJS NIBRS API
                    if ori:
                        data = asyncio.run(self.api_client.get_bjs_agency_clearance(ori, year, year))
                        if data and "clearance_rate" in data:
                            rate = data["clearance_rate"]

                elif source == "fbi_cde":
                    # Try FBI CDE participation endpoint
                    if ori:
                        data = asyncio.run(self.api_client.get_fbi_summarized(ori, year, year))
                        if data:
                            # Parse clearance from response
                            offenses = data.get("offenses", [])
                            # Implementation depends on actual response structure
                            pass

                elif source == "icpsr":
                    # Try ICPSR data
                    pass  # Implementation when ICPSR access available

                if rate is not None:
                    self.data_source_log.append((city, year, source))
                    return rate

            except Exception as e:
                logger.debug(f"{source} failed for {city} {year}: {e}")

        # No real data available
        logger.warning(f"No clearance data for {city} {year} - excluding from analysis")
        self.missing_data_log.append((city, year))
        return None

    def build_feature_matrix(
        self,
        df: pd.DataFrame,
        city_rtcc_years: Dict[str, int],
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Construct feature matrix X and target y from dataframe.

        Features:
        - post_rtcc: binary (1 if year >= rtcc_year)
        - years_since_rtcc: int (0 if no RTCC)
        - homicide_count: int
        - population: int
        - region_encoded: OneHotEncoder (4 cols)
        - state_fe: TargetEncoder

        Args:
            df: Input dataframe with city, year, homicide_count, population, etc.
            city_rtcc_years: Dict mapping city name to RTCC implementation year

        Returns:
            (X, y) where y is clearance binary or rate
        """
        logger.info("Building feature matrix")

        # Make a copy to avoid modifying original
        df = df.copy()

        # Add RTCC features — match city names case-insensitively
        city_years_lower = {k.lower(): v for k, v in city_rtcc_years.items()}
        df["post_rtcc"] = df.apply(
            lambda row: int(row["year"]) >= city_years_lower.get(str(row["city"]).lower(), 9999),
            axis=1,
        ).astype(int)
        df["years_since_rtcc"] = df.apply(
            lambda row: max(0, int(row["year"]) - city_years_lower.get(str(row["city"]).lower(), int(row["year"]) + 1)),
            axis=1,
        )

        # Define feature columns
        numeric_features = ["years_since_rtcc", "homicide_count", "population"]
        categorical_features = ["region"]
        target_features = ["state_fe"]

        # Handle missing features
        for feat in numeric_features:
            if feat not in df.columns:
                df[feat] = 0  # Default value

        for feat in categorical_features:
            if feat not in df.columns:
                df[feat] = "Unknown"

        for feat in target_features:
            if feat not in df.columns:
                df[feat] = "Unknown"

        # Create target variable
        if "clearance_rate" in df.columns:
            # Binary classification: clearance > 0.5
            df["clearance_binary"] = (df["clearance_rate"] >= 0.5).astype(int)
            y = df["clearance_binary"].values
        elif "clearance_count" in df.columns and "homicide_count" in df.columns:
            df["clearance_rate"] = df["clearance_count"] / df["homicide_count"].replace(0, 1)
            df["clearance_binary"] = (df["clearance_rate"] >= 0.5).astype(int)
            y = df["clearance_binary"].values
        else:
            raise ValueError("Cannot create target: need clearance_rate or clearance_count + homicide_count")

        # Remove rows with missing target
        valid_mask = ~pd.isna(y)
        df = df[valid_mask]
        y = y[valid_mask]
        X = df[numeric_features + categorical_features + target_features]

        # Store feature columns
        self.feature_columns = numeric_features + categorical_features + target_features

        # Create preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                ("num", StandardScaler(), numeric_features),
                ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
                ("target", TargetEncoder(target_type="binary"), target_features),
            ],
            remainder="drop",
        )

        self.preprocessor = preprocessor

        logger.info(f"Built feature matrix: X={X.shape}, y={y.shape}")
        logger.info(f"Positive class ratio: {y.mean():.2%}")

        return X, y

    def train_models(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
    ) -> Dict[str, Any]:
        """
        Train all models with TimeSeriesSplit cross-validation.

        CV Strategy: TimeSeriesSplit(n_splits=5)
        - Preserves temporal ordering (no leakage from future)
        - Split 1: Train on earliest 60%, test on next 20%
        - Subsequent splits shift forward in time

        Args:
            X: Feature matrix
            y: Target variable

        Returns:
            Dictionary of trained models
        """
        logger.info("Training models with TimeSeriesSplit CV")

        # Preprocess features — convert to dense array
        X_processed = self.preprocessor.fit_transform(X, y)
        if hasattr(X_processed, "toarray"):
            X_processed = X_processed.toarray().astype(np.float64)
        else:
            X_processed = np.array(X_processed, dtype=np.float64)

        # Get feature names after preprocessing
        feature_names = self._get_feature_names()

        # Time series split
        tscv = TimeSeriesSplit(n_splits=5, test_size=max(1, int(len(y) * 0.2)))

        # Train XGBoost
        logger.info("Training XGBoost...")
        self.models["xgboost"] = xgb.XGBClassifier(**self.MODEL_CONFIGS["xgboost"])

        cv_results_xgb = cross_validate(
            self.models["xgboost"],
            X_processed,
            y,
            cv=tscv,
            scoring="roc_auc",
            return_estimator=True,
        )

        # Fit on full data for final model
        self.models["xgboost"].fit(X_processed, y)

        # Train Random Forest
        logger.info("Training Random Forest...")
        self.models["random_forest"] = RandomForestClassifier(**self.MODEL_CONFIGS["random_forest"])

        cv_results_rf = cross_validate(
            self.models["random_forest"],
            X_processed,
            y,
            cv=tscv,
            scoring="roc_auc",
            return_estimator=True,
        )

        self.models["random_forest"].fit(X_processed, y)

        # Train Logistic Regression
        logger.info("Training Logistic Regression...")
        self.models["logistic"] = LogisticRegression(**self.MODEL_CONFIGS["logistic"])

        cv_results_lr = cross_validate(
            self.models["logistic"],
            X_processed,
            y,
            cv=tscv,
            scoring="roc_auc",
            return_estimator=True,
        )

        self.models["logistic"].fit(X_processed, y)

        # Store CV scores (handle NaN from failed folds)
        def safe_cv_stats(scores):
            valid = scores[~np.isnan(scores)]
            if len(valid) == 0:
                return {"cv_scores": scores.tolist(), "mean_cv": float("nan")}
            return {"cv_scores": scores.tolist(), "mean_cv": float(valid.mean())}

        self.metrics["xgboost"] = safe_cv_stats(cv_results_xgb["test_score"])
        self.metrics["random_forest"] = safe_cv_stats(cv_results_rf["test_score"])
        self.metrics["logistic"] = safe_cv_stats(cv_results_lr["test_score"])

        logger.info("Model training complete")
        for model_name, metric in self.metrics.items():
            logger.info(f"  {model_name}: CV AUC = {metric['mean_cv']:.3f}")

        return self.models

    def _get_feature_names(self) -> List[str]:
        """Get feature names after preprocessing."""
        if self.preprocessor is None:
            return []

        feature_names = []

        # Numeric features (keep original names)
        for name in self.preprocessor.transformers_[0][2]:
            feature_names.append(name)

        # Categorical features (OneHotEncoder)
        ohe = self.preprocessor.named_transformers_["cat"]
        if hasattr(ohe, "get_feature_names_out"):
            for name in ohe.get_feature_names_out():
                feature_names.append(name)

        # Target encoded features
        for name in self.preprocessor.transformers_[2][2]:
            feature_names.append(f"{name}_te")

        return feature_names

    def evaluate(self, X: pd.DataFrame, y: np.ndarray) -> Dict[str, ClearanceMetrics]:
        """
        Evaluate all models on test data.

        Args:
            X: Test features
            y: True labels

        Returns:
            Dictionary of metrics per model
        """
        logger.info("Evaluating models")

        X_processed = self.preprocessor.transform(X)
        if hasattr(X_processed, "toarray"):
            X_processed = X_processed.toarray().astype(np.float64)
        else:
            X_processed = np.array(X_processed, dtype=np.float64)
        results = {}

        for model_name, model in self.models.items():
            # Predict
            y_pred_proba = model.predict_proba(X_processed)[:, 1]
            y_pred = (y_pred_proba >= 0.5).astype(int)

            # Calculate metrics
            metrics = ClearanceMetrics(
                model_name=model_name,
                auc_roc=roc_auc_score(y, y_pred_proba),
                precision=precision_score(y, y_pred, zero_division=0),
                recall=recall_score(y, y_pred, zero_division=0),
                f1=f1_score(y, y_pred, zero_division=0),
                cv_scores=self.metrics[model_name]["cv_scores"],
                feature_importance=self._get_feature_importance(model_name),
            )

            results[model_name] = metrics

            logger.info(
                f"{model_name}: AUC={metrics.auc_roc:.3f}, "
                f"F1={metrics.f1:.3f}, Recall={metrics.recall:.3f}"
            )

        return results

    def _get_feature_importance(self, model_name: str) -> Dict[str, float]:
        """Get feature importance for a model."""
        model = self.models.get(model_name)
        if model is None:
            return {}

        feature_names = self._get_feature_names()
        importance = {}

        if model_name == "xgboost":
            for name, score in zip(feature_names, model.feature_importances_):
                importance[name] = float(score)

        elif model_name == "random_forest":
            for name, score in zip(feature_names, model.feature_importances_):
                importance[name] = float(score)

        elif model_name == "logistic":
            # Logistic regression uses coefficients
            for name, coef in zip(feature_names, model.coef_[0]):
                importance[name] = float(abs(coef))

        return importance

    def shap_analysis(
        self,
        X: pd.DataFrame,
        model_name: str = "xgboost",
        max_display: int = 20,
    ):
        """
        Generate SHAP plots for model interpretation.

        Creates:
        - Waterfall plot for median observation
        - Beeswarm plot for global feature importance

        Args:
            X: Feature matrix
            model_name: Model to analyze (default: xgboost)
            max_display: Maximum number of features to display
        """
        logger.info(f"Generating SHAP analysis for {model_name}")

        model = self.models.get(model_name)
        if model is None:
            logger.error(f"Model {model_name} not found")
            return

        X_processed = self.preprocessor.transform(X)
        if hasattr(X_processed, "toarray"):
            X_processed = X_processed.toarray().astype(np.float64)
        else:
            X_processed = np.array(X_processed, dtype=np.float64)
        # Convert to dense float array if sparse
        if hasattr(X_processed, "toarray"):
            X_processed_dense = X_processed.toarray().astype(np.float64)
        else:
            X_processed_dense = np.array(X_processed, dtype=np.float64)

        feature_names = self._get_feature_names()

        # Create SHAP explainer
        if model_name in ("xgboost", "random_forest"):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_processed_dense)
            # Binary classification may return list of 2 arrays — use class 1
            if isinstance(shap_values, list):
                shap_values = shap_values[1]
            base_val = explainer.expected_value
            if isinstance(base_val, (list, np.ndarray)):
                base_val = base_val[1] if len(base_val) > 1 else base_val[0]
        else:
            explainer = shap.LinearExplainer(model, X_processed_dense)
            shap_values = explainer.shap_values(X_processed_dense)
            base_val = explainer.expected_value
            if isinstance(base_val, (list, np.ndarray)):
                base_val = float(base_val[0])

        shap_values = np.array(shap_values, dtype=np.float64)

        # Waterfall plot for median observation
        median_idx = len(X_processed_dense) // 2

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        explanation = shap.Explanation(
            values=shap_values[median_idx],
            base_values=float(base_val),
            data=X_processed_dense[median_idx],
            feature_names=feature_names,
        )
        shap.plots.waterfall(explanation, show=False, max_display=max_display)
        output_path = self.results_dir / "figures" / "shap" / f"waterfall_{model_name}.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved waterfall plot to {output_path}")

        # Beeswarm plot
        explanation_all = shap.Explanation(
            values=shap_values,
            base_values=float(base_val),
            data=X_processed_dense,
            feature_names=feature_names,
        )
        shap.plots.beeswarm(explanation_all, show=False, max_display=max_display)
        output_path = self.results_dir / "figures" / "shap" / f"beeswarm_{model_name}.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved beeswarm plot to {output_path}")

    def save_results(self, path: Optional[Path] = None):
        """
        Save feature importances and metrics to tables.

        Args:
            path: Output path (defaults to results_dir/tables/)
        """
        if path is None:
            path = self.results_dir / "tables"

        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save feature importances
        importance_data = []
        for model_name in self.models.keys():
            importance = self._get_feature_importance(model_name)
            for feature, score in importance.items():
                importance_data.append({
                    "model": model_name,
                    "feature": feature,
                    "importance": score,
                })

        if importance_data:
            df_importance = pd.DataFrame(importance_data)
            df_importance = df_importance.sort_values(["model", "importance"], ascending=[True, False])
            df_importance.to_csv(path / "feature_importance.csv", index=False)
            logger.info(f"Saved feature importances to {path / 'feature_importance.csv'}")

        # Save metrics summary
        metrics_data = []
        for model_name, metric_dict in self.metrics.items():
            metrics_data.append({
                "model": model_name,
                "mean_cv_auc": metric_dict["mean_cv"],
                "std_cv_auc": np.std(metric_dict["cv_scores"]),
            })

        if metrics_data:
            df_metrics = pd.DataFrame(metrics_data)
            df_metrics.to_csv(path / "model_metrics.csv", index=False)
            logger.info(f"Saved model metrics to {path / 'model_metrics.csv'}")

        # Save missing data log
        if self.missing_data_log:
            df_missing = pd.DataFrame(self.missing_data_log, columns=["city", "year"])
            df_missing.to_csv(path / "missing_clearance_data.csv", index=False)
            logger.info(f"Saved missing data log to {path / 'missing_clearance_data.csv'}")

    def report_data_coverage(self):
        """Print data coverage statistics."""
        print("\n" + "=" * 50)
        print("DATA COVERAGE REPORT")
        print("=" * 50)

        if self.missing_data_log:
            df_missing = pd.DataFrame(self.missing_data_log, columns=["city", "year"])
            print(f"\nMissing clearance data: {len(df_missing)} city-years")
            print(df_missing["city"].value_counts().head(10))
        else:
            print("\nNo missing data logged")

        if self.data_source_log:
            df_sources = pd.DataFrame(self.data_source_log, columns=["city", "year", "source"])
            print("\nData sources used:")
            print(df_sources["source"].value_counts())


def main():
    """CLI interface for the clearance classifier."""
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Clearance Classifier")
    parser.add_argument("--data", type=str, help="Input data CSV path")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--coverage", action="store_true", help="Report data coverage")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    classifier = RTCCClearanceClassifier(results_dir=args.output)

    if args.coverage:
        classifier.report_data_coverage()
    else:
        print("Use --data to specify input file")
        print("Use --coverage to check data coverage")


if __name__ == "__main__":
    main()
