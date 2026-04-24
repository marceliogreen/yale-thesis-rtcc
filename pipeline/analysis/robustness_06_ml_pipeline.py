"""
Robustness 7: ML pipeline — XGBoost + SHAP for treatment effect heterogeneity.

Uses the 15-city RTCC panel with LEMAS covariates to estimate heterogeneous
treatment effects via XGBoost, then explains with SHAP values.

Outcome: log(homicides)
Treatment: post_rtcc
Covariates: LEMAS technology scores, staffing, population

Output: results/study1_rtcc/robustness/robustness_7_ml_pipeline.csv
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
OUT = BASE / "results/study1_rtcc" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)


def load_data():
    df = pd.read_csv(BASE / "results/study1_rtcc/rtcc_city_panel_enhanced.csv")

    # Features to use
    feature_cols = [
        "post_rtcc", "year", "est_population", "officers_per_10k_pe",
        "total_sworn", "homicides_per_sworn",
    ]

    # Add LEMAS features if available
    lemas_cols = ["tech_score", "data_driven_score", "has_bwc",
                  "budget_per_capita", "community_policing_score"]
    for c in lemas_cols:
        if c in df.columns:
            feature_cols.append(c)

    # Keep only available columns
    avail = [c for c in feature_cols if c in df.columns]
    df = df.dropna(subset=["log_homicides"])

    X = df[avail].copy()
    y = df["log_homicides"].values

    # Fill remaining NaNs with 0 for ML
    X = X.fillna(0)

    return X, y, avail, df


def run_xgboost(X, y, feature_names):
    """Train XGBoost and compute SHAP values."""
    try:
        import xgboost as xgb
    except ImportError:
        logger.warning("xgboost not installed, skipping")
        return None

    from sklearn.model_selection import cross_val_score

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )

    # Cross-validation R²
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    logger.info(f"XGBoost CV R²: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # Fit on full data
    model.fit(X, y)

    # Feature importance
    importance = model.feature_importances_
    imp_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importance,
    }).sort_values("importance", ascending=False)

    logger.info("\nFeature importance:")
    for _, row in imp_df.iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.4f}")

    # SHAP values
    try:
        import shap
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)

        # Mean absolute SHAP per feature
        shap_mean = np.abs(shap_values).mean(axis=0)
        shap_df = pd.DataFrame({
            "feature": feature_names,
            "shap_mean_abs": shap_mean,
        }).sort_values("shap_mean_abs", ascending=False)

        logger.info("\nSHAP mean |value|:")
        for _, row in shap_df.iterrows():
            logger.info(f"  {row['feature']}: {row['shap_mean_abs']:.4f}")

        # SHAP for post_rtcc specifically
        post_idx = feature_names.index("post_rtcc")
        shap_post = shap_values[:, post_idx]
        logger.info(f"\npost_rtcc SHAP: mean={shap_post.mean():.4f}, "
                   f"std={shap_post.std():.4f}")

        return {
            "model": "XGBoost",
            "cv_r2_mean": cv_scores.mean(),
            "cv_r2_std": cv_scores.std(),
            "feature_importance": imp_df.to_dict("records"),
            "shap_post_rtcc_mean": shap_post.mean(),
            "shap_post_rtcc_std": shap_post.std(),
        }
    except ImportError:
        logger.warning("shap not installed, skipping SHAP analysis")
        return {
            "model": "XGBoost",
            "cv_r2_mean": cv_scores.mean(),
            "cv_r2_std": cv_scores.std(),
            "feature_importance": imp_df.to_dict("records"),
        }


def run_random_forest(X, y, feature_names):
    """Random Forest comparison."""
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score

    model = RandomForestRegressor(
        n_estimators=500,
        max_depth=8,
        random_state=42,
    )

    cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    logger.info(f"\nRandom Forest CV R²: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    model.fit(X, y)
    importance = model.feature_importances_
    imp_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importance,
    }).sort_values("importance", ascending=False)

    logger.info("RF Feature importance:")
    for _, row in imp_df.head(5).iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.4f}")

    return {
        "model": "RandomForest",
        "cv_r2_mean": cv_scores.mean(),
        "cv_r2_std": cv_scores.std(),
    }


def run_lasso(X, y, feature_names):
    """LASSO regression for variable selection."""
    from sklearn.linear_model import LassoCV
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LassoCV(cv=5, random_state=42)
    model.fit(X_scaled, y)

    logger.info(f"\nLASSO alpha: {model.alpha_:.4f}")
    logger.info("LASSO coefficients:")
    coef_df = pd.DataFrame({
        "feature": feature_names,
        "coefficient": model.coef_,
    }).sort_values("coefficient", key=abs, ascending=False)

    for _, row in coef_df.iterrows():
        if abs(row["coefficient"]) > 0.001:
            logger.info(f"  {row['feature']}: {row['coefficient']:.4f}")

    return {
        "model": "LASSO",
        "alpha": model.alpha_,
        "post_rtcc_coef": coef_df[coef_df["feature"] == "post_rtcc"]["coefficient"].values[0],
    }


def main():
    X, y, feature_names, df = load_data()
    logger.info(f"Data: {X.shape}, features={feature_names}")
    logger.info(f"post_rtcc distribution: {X['post_rtcc'].value_counts().to_dict()}")

    results = []

    # XGBoost + SHAP
    xgb_result = run_xgboost(X, y, feature_names)
    if xgb_result:
        results.append(xgb_result)

    # Random Forest
    rf_result = run_random_forest(X, y, feature_names)
    if rf_result:
        results.append(rf_result)

    # LASSO
    lasso_result = run_lasso(X, y, feature_names)
    if lasso_result:
        results.append(lasso_result)

    # Save summary
    rows = []
    for r in results:
        row = {"model": r["model"]}
        if "cv_r2_mean" in r:
            row["cv_r2"] = f"{r['cv_r2_mean']:.3f} ± {r['cv_r2_std']:.3f}"
        if "shap_post_rtcc_mean" in r:
            row["shap_post_rtcc_mean"] = r["shap_post_rtcc_mean"]
            row["shap_post_rtcc_std"] = r["shap_post_rtcc_std"]
        if "post_rtcc_coef" in r:
            row["post_rtcc_coef"] = r["post_rtcc_coef"]
        if "alpha" in r:
            row["alpha"] = r["alpha"]
        rows.append(row)

    df_out = pd.DataFrame(rows)
    out_path = OUT / "robustness_7_ml_pipeline.csv"
    df_out.to_csv(out_path, index=False)
    logger.info(f"\nSaved: {out_path}")

    # Also save feature importance from XGBoost
    if xgb_result and "feature_importance" in xgb_result:
        imp_df = pd.DataFrame(xgb_result["feature_importance"])
        imp_path = OUT / "robustness_7_xgboost_importance.csv"
        imp_df.to_csv(imp_path, index=False)
        logger.info(f"Saved: {imp_path}")


if __name__ == "__main__":
    main()
