"""
Standalone SHAP + Causal Forest Analysis

Runs directly on master_analysis_panel.csv without the classifier class overhead.
Produces SHAP plots and CATE estimates.

Author: Marcel Green <marcelo.green@yale.edu>
"""

import sys
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PIPELINE_DIR = Path(__file__).parent
sys.path.insert(0, str(PIPELINE_DIR))

# ── Config ──────────────────────────────────────────────────────

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

RTCC_CITY_YEARS = {
    "Hartford": 2016, "Miami": 2016, "St. Louis": 2015,
    "Newark": 2018, "New Orleans": 2017, "Albuquerque": 2020,
    "Fresno": 2018, "Chicago": 2017,
}

RESULTS_DIR = Path(__file__).parent / "results" / "study1_rtcc"


# ── Data Loading ────────────────────────────────────────────────

def load_data():
    """Load and prepare the master analysis panel."""
    candidates = [
        Path(__file__).parent.parent.parent / "thesis" / "data" / "master_analysis_panel.csv",
        Path(__file__).parent.parent / "data" / "master_analysis_panel.csv",
    ]
    panel_path = next((p for p in candidates if p.exists()), None)
    if panel_path is None:
        raise FileNotFoundError("master_analysis_panel.csv not found")

    df = pd.read_csv(panel_path)
    logger.info(f"Loaded panel: {len(df)} rows")

    # Filter
    df = df[df["homicides"] >= 1].copy()
    df = df.dropna(subset=["clearance_rate"]).copy()
    df["clearance_rate"] = df["clearance_rate"].clip(upper=1.0)
    logger.info(f"After filter: {len(df)} rows, clearance mean={df['clearance_rate'].mean():.3f}")

    # Features
    df["region"] = df["state_abb"].map(STATE_TO_REGION).fillna("Unknown")
    df["is_rtcc"] = df["rtcc_city"].notna().astype(int)

    # Treatment: actual RTCC cities post-implementation
    df["treated"] = 0
    for city, year in RTCC_CITY_YEARS.items():
        mask = (df["rtcc_city"] == city) & (df["year"] >= year)
        df.loc[mask, "treated"] = 1

    df = df.sort_values("year").reset_index(drop=True)

    logger.info(f"RTCC city obs: {df['is_rtcc'].sum()}, Treated: {df['treated'].sum()}")
    return df


def build_features(df):
    """Build feature matrix for ML models."""
    # One-hot encode region
    region_dummies = pd.get_dummies(df["region"], prefix="region", dtype=float)

    feature_cols = ["population", "homicides", "years_since_rtcc", "is_rtcc", "treated"]
    X = pd.concat([df[feature_cols].reset_index(drop=True), region_dummies.reset_index(drop=True)], axis=1)
    y_binary = (df["clearance_rate"] >= 0.5).astype(int).values
    y_continuous = df["clearance_rate"].values

    # Standardize numeric features
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    numeric_cols = ["population", "homicides", "years_since_rtcc"]
    X[numeric_cols] = scaler.fit_transform(X[numeric_cols])

    # Fill any NaN/inf from standardization
    X = X.fillna(0).replace([np.inf, -np.inf], 0)

    feature_names = list(X.columns)
    X = X.values.astype(np.float64)

    logger.info(f"Features: {feature_names}")
    logger.info(f"X shape: {X.shape}, y_binary positive: {y_binary.mean():.1%}")

    return X, y_binary, y_continuous, feature_names, scaler


# ── SHAP Analysis ───────────────────────────────────────────────

def run_shap(X, y, feature_names):
    """Train XGBoost + RF and generate SHAP plots."""
    import xgboost as xgb
    from sklearn.ensemble import RandomForestClassifier
    import shap

    logger.info("=" * 50)
    logger.info("SHAP ANALYSIS")
    logger.info("=" * 50)

    # Train XGBoost
    xgb_model = xgb.XGBClassifier(
        n_estimators=500, learning_rate=0.05, max_depth=6,
        random_state=42, eval_metric="logloss",
    )
    xgb_model.fit(X, y)
    logger.info(f"XGBoost train accuracy: {xgb_model.score(X, y):.3f}")

    # Train Random Forest
    rf_model = RandomForestClassifier(
        n_estimators=500, max_depth=10, random_state=42, class_weight="balanced",
    )
    rf_model.fit(X, y)
    logger.info(f"RF train accuracy: {rf_model.score(X, y):.3f}")

    # Feature importance
    importance_data = []
    for name, score in zip(feature_names, xgb_model.feature_importances_):
        importance_data.append({"model": "xgboost", "feature": name, "importance": float(score)})
    for name, score in zip(feature_names, rf_model.feature_importances_):
        importance_data.append({"model": "random_forest", "feature": name, "importance": float(score)})

    importance_df = pd.DataFrame(importance_data).sort_values(["model", "importance"], ascending=[True, False])
    importance_df.to_csv(RESULTS_DIR / "tables" / "feature_importance.csv", index=False)
    logger.info(f"Saved feature importances:\n{importance_df.to_string(index=False)}")

    # SHAP for XGBoost
    output_dir = RESULTS_DIR / "figures" / "shap"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Background sample for explainers
    bg_size = min(200, len(X))
    bg = shap.sample(X, bg_size, random_state=42)

    for model_name, model in [("xgboost", xgb_model)]:  # RF SHAP too slow with PermutationExplainer
        logger.info(f"Computing SHAP for {model_name}...")

        # Use PermutationExplainer to avoid XGBoost 3.x / TreeExplainer bug
        explainer = shap.Explainer(model.predict, bg, algorithm="permutation")
        sv = explainer(X[:500])  # subsample for speed
        sv_values = np.array(sv.values, dtype=np.float64)
        if sv_values.ndim > 1 and sv_values.shape[1] == 2:
            sv_values = sv_values[:, 1]  # class 1
            base_val = float(sv.base_values[0, 1]) if isinstance(sv.base_values, np.ndarray) and sv.base_values.ndim > 1 else float(sv.base_values[0])
        else:
            base_val = float(sv.base_values[0]) if isinstance(sv.base_values, np.ndarray) else float(sv.base_values)

        # Save SHAP values
        shap_df = pd.DataFrame(sv_values, columns=feature_names)
        shap_df.to_csv(output_dir / f"shap_values_{model_name}.csv", index=False)

        # Beeswarm plot
        exp = shap.Explanation(
            values=sv_values,
            base_values=np.full(len(sv_values), base_val),
            data=X[:len(sv_values)],
            feature_names=feature_names,
        )
        shap.plots.beeswarm(exp, show=False, max_display=15)
        plt.title(f"SHAP Feature Importance — {model_name.upper()}")
        plt.tight_layout()
        plt.savefig(output_dir / f"beeswarm_{model_name}.png", dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved beeswarm_{model_name}.png")

        # Waterfall for median observation
        median_idx = len(sv_values) // 2
        shap.plots.waterfall(exp[median_idx], show=False, max_display=15)
        plt.tight_layout()
        plt.savefig(output_dir / f"waterfall_{model_name}.png", dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved waterfall_{model_name}.png")

        # Bar plot (mean |SHAP|)
        shap.plots.bar(exp, show=False, max_display=15)
        plt.title(f"Mean |SHAP| — {model_name.upper()}")
        plt.tight_layout()
        plt.savefig(output_dir / f"bar_{model_name}.png", dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Saved bar_{model_name}.png")

    return xgb_model, rf_model


# ── Causal Forest ───────────────────────────────────────────────

def run_causal_forest(X, y_continuous, feature_names, df):
    """Run EconML CausalForestDML for heterogeneous treatment effects."""
    from econml.dml import CausalForestDML
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

    logger.info("=" * 50)
    logger.info("CAUSAL FOREST ANALYSIS")
    logger.info("=" * 50)

    # Setup treatment and outcome
    T = df["treated"].values
    Y = y_continuous

    # Heterogeneity covariates (everything except treatment)
    treat_idx = feature_names.index("treated")
    X_covariates = np.delete(X, treat_idx, axis=1)
    covariate_names = [f for f in feature_names if f != "treated"]

    n_treated = T.sum()
    n_control = len(T) - n_treated
    logger.info(f"Treatment: {n_treated} treated, {n_control} control")

    if n_treated < 20:
        logger.warning(f"Only {n_treated} treated observations — CATE estimates may be unreliable")

    # Fit causal forest
    model_y = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
    model_t = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)

    cf = CausalForestDML(
        model_y=model_y,
        model_t=model_t,
        n_estimators=1000,
        max_depth=10,
        min_samples_leaf=10,
        max_samples=0.45,
        discrete_treatment=True,
        random_state=42,
        cv=5,
    )

    logger.info("Fitting causal forest...")
    cf.fit(Y=Y, T=T, X=X_covariates)
    logger.info("Causal forest fitted")

    # ATE
    ate = cf.ate(X_covariates)
    ate_inf = cf.ate_inference(X_covariates)
    try:
        ci = ate_inf.conf_int_mean(alpha=0.05)
        ate_lower = float(ci[0])
        ate_upper = float(ci[1])
    except Exception as e:
        logger.warning(f"Could not get ATE CI: {e}")
        ate_lower, ate_upper = float('nan'), float('nan')

    logger.info(f"ATE: {ate:.4f} (95% CI: [{ate_lower}, {ate_upper}])")

    # CATE for all observations
    cate = cf.effect(X_covariates)  # X_covariates already passed

    # CATE by RTCC city
    logger.info("\nCATE by RTCC city:")
    cate_by_city = {}
    for city in df["rtcc_city"].dropna().unique():
        mask = df["rtcc_city"] == city
        if mask.sum() > 0:
            city_cate = float(cate[mask].mean())
            cate_by_city[city] = city_cate
            logger.info(f"  {city}: CATE = {city_cate:.4f} (n={mask.sum()})")

    # CATE by population quartile
    logger.info("\nCATE by population quartile:")
    pop = df["population"].values
    quartiles = pd.qcut(pop, q=4, labels=["Q1(small)", "Q2", "Q3", "Q4(large)"])
    cate_by_quartile = {}
    for q in quartiles.unique():
        mask = quartiles == q
        q_cate = float(cate[mask].mean())
        cate_by_quartile[str(q)] = q_cate
        logger.info(f"  {q}: CATE = {q_cate:.4f} (n={mask.sum()})")

    # Save CATE results
    cate_df = pd.DataFrame({
        "ori9": df["ori9"].values,
        "agency_name": df["agency_name"].values,
        "year": df["year"].values,
        "clearance_rate": df["clearance_rate"].values,
        "treated": T,
        "cate": cate,
        "rtcc_city": df["rtcc_city"].values,
        "population": df["population"].values,
    })
    cate_df.to_csv(RESULTS_DIR / "tables" / "cate_all.csv", index=False)
    logger.info(f"Saved CATE data to cate_all.csv")

    # CATE distribution plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(cate, bins=50, edgecolor="black", alpha=0.7)
    ax.axvline(cate.mean(), color="red", linestyle="--", label=f"Mean: {cate.mean():.3f}")
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("CATE (Treatment Effect on Clearance Rate)")
    ax.set_ylabel("Frequency")
    ax.set_title("Distribution of Conditional Average Treatment Effects")
    ax.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "figures" / "causal" / "cate_distribution.png", dpi=300, bbox_inches="tight")
    plt.close()
    logger.info("Saved cate_distribution.png")

    # CATE by city bar chart
    if cate_by_city:
        fig, ax = plt.subplots(figsize=(10, 6))
        cities = list(cate_by_city.keys())
        cates = list(cate_by_city.values())
        colors = ["green" if v > 0 else "red" for v in cates]
        ax.barh(cities, cates, color=colors, edgecolor="black")
        ax.axvline(0, color="black", linewidth=1)
        ax.set_xlabel("CATE (Treatment Effect)")
        ax.set_title("Heterogeneous Treatment Effects by RTCC City")
        plt.tight_layout()
        plt.savefig(RESULTS_DIR / "figures" / "causal" / "cate_by_city.png", dpi=300, bbox_inches="tight")
        plt.close()
        logger.info("Saved cate_by_city.png")

    # CATE vs population scatter
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(df["population"], cate, alpha=0.3, s=10)
    from scipy.stats import linregress
    slope, intercept, r, p, _ = linregress(df["population"], cate)
    x_line = np.linspace(df["population"].min(), df["population"].max(), 100)
    ax.plot(x_line, slope * x_line + intercept, "r-", label=f"r={r:.3f}, p={p:.4f}")
    ax.axhline(0, color="black", linewidth=1)
    ax.set_xlabel("Population")
    ax.set_ylabel("CATE")
    ax.set_title("CATE vs Population")
    ax.legend()
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "figures" / "causal" / "cate_vs_population.png", dpi=300, bbox_inches="tight")
    plt.close()
    logger.info("Saved cate_vs_population.png")

    return {
        "ate": float(ate),
        "ate_ci": (ate_lower, ate_upper),
        "cate_by_city": cate_by_city,
        "cate_by_quartile": cate_by_quartile,
        "cate_mean": float(cate.mean()),
        "cate_std": float(cate.std()),
        "n_treated": int(n_treated),
        "n_control": int(n_control),
    }


# ── Main ────────────────────────────────────────────────────────

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "tables").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "figures" / "shap").mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "figures" / "causal").mkdir(parents=True, exist_ok=True)

    df = load_data()
    X, y_binary, y_continuous, feature_names, scaler = build_features(df)

    # SHAP + Classification
    xgb_model, rf_model = run_shap(X, y_binary, feature_names)

    # Causal Forest
    causal_results = run_causal_forest(X, y_continuous, feature_names, df)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL RESULTS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"\nSHAP Feature Importance (XGBoost top features):")
    for name, score in sorted(zip(feature_names, xgb_model.feature_importances_), key=lambda x: -x[1])[:5]:
        logger.info(f"  {name}: {score:.4f}")

    logger.info(f"\nCausal Forest:")
    logger.info(f"  ATE: {causal_results['ate']:.4f} ({causal_results['ate']:.2f}pp)")
    logger.info(f"  95% CI: [{causal_results['ate_ci'][0]:.4f}, {causal_results['ate_ci'][1]:.4f}]")
    logger.info(f"  CATE by city:")
    for city, c in causal_results["cate_by_city"].items():
        logger.info(f"    {city}: {c:.4f}")

    logger.info(f"\nResults saved to: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
