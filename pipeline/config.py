"""
Centralized configuration for the RTCC thesis pipeline.

This module is the single source of truth for file paths, model parameters,
and RTCC treatment metadata used across Study 1 analyses.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import os


# Root paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
SCRAPED_DATA_DIR = PROJECT_ROOT / "scraped_data"
PIPELINE_DIR = PROJECT_ROOT / "pipeline"


# Core Study 1 treatment set used throughout the thesis.
# These values are aligned to the checked-in panel data and downstream analyses.
RTCC_CITY_METADATA: Dict[str, Dict[str, Any]] = {
    "Hartford": {
        "ori": "CT0006400",
        "rtcc_year": 2016,
        "population": 121000,
        "state": "CT",
        "tier": "reference",
        "notes": "Kaplan/UCR-aligned Hartford agency mapping used in the panel.",
    },
    "Miami": {
        "ori": "FL0130200",
        "rtcc_year": 2016,
        "population": 467000,
        "state": "FL",
        "tier": "partial",
        "notes": "Core Study 1 treatment city.",
    },
    "St. Louis": {
        "ori": "MO0640000",
        "rtcc_year": 2015,
        "population": 293000,
        "state": "MO",
        "tier": "partial",
        "notes": "Core Study 1 treatment city.",
    },
    "Newark": {
        "ori": "NJ0071400",
        "rtcc_year": 2018,
        "population": 277000,
        "state": "NJ",
        "tier": "dropped",
        "notes": "Configured for completeness; often dropped for sparse outcome data.",
    },
    "New Orleans": {
        "ori": "LA0360000",
        "rtcc_year": 2017,
        "population": 376000,
        "state": "LA",
        "tier": "dropped",
        "notes": "Configured for completeness; often dropped for sparse outcome data.",
    },
    "Albuquerque": {
        "ori": "NM0010100",
        "rtcc_year": 2020,
        "population": 564000,
        "state": "NM",
        "tier": "primary",
        "notes": "Core Study 1 treatment city.",
    },
    "Fresno": {
        "ori": "CA0190200",
        "rtcc_year": 2018,
        "population": 545000,
        "state": "CA",
        "tier": "primary",
        "notes": "Core Study 1 treatment city.",
    },
    "Chicago": {
        "ori": "IL0160000",
        "rtcc_year": 2017,
        "population": 2694000,
        "state": "IL",
        "tier": "partial",
        "notes": "Core Study 1 treatment city.",
    },
    # Expanded panel cities used in the broader comparison design.
    "Baltimore": {
        "ori": "MDBPD0000",
        "rtcc_year": 2013,
        "population": None,
        "state": "MD",
        "tier": "primary",
        "notes": "Expanded panel city.",
    },
    "Detroit": {
        "ori": "MI8234900",
        "rtcc_year": 2016,
        "population": None,
        "state": "MI",
        "tier": "primary",
        "notes": "Expanded panel city.",
    },
    "Philadelphia": {
        "ori": "PAPEP0000",
        "rtcc_year": 2012,
        "population": None,
        "state": "PA",
        "tier": "primary",
        "notes": "Expanded panel city.",
    },
    "Houston": {
        "ori": "TXHPD0000",
        "rtcc_year": 2008,
        "population": None,
        "state": "TX",
        "tier": "primary",
        "notes": "Expanded panel city.",
    },
    "Memphis": {
        "ori": "TNMPD0000",
        "rtcc_year": 2008,
        "population": None,
        "state": "TN",
        "tier": "primary",
        "notes": "Expanded panel city.",
    },
    "Dallas": {
        "ori": "TXDPD0000",
        "rtcc_year": 2019,
        "population": None,
        "state": "TX",
        "tier": "primary",
        "notes": "Expanded panel city.",
    },
    "Denver": {
        "ori": "CODPD0000",
        "rtcc_year": 2019,
        "population": None,
        "state": "CO",
        "tier": "primary",
        "notes": "Expanded panel city.",
    },
}

STUDY1_RTCC_CITIES: List[str] = [
    "Hartford",
    "Miami",
    "St. Louis",
    "Newark",
    "New Orleans",
    "Albuquerque",
    "Fresno",
    "Chicago",
]


def get_rtcc_city_metadata(cities: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Return RTCC city metadata for the requested city subset."""
    if cities is None:
        return dict(RTCC_CITY_METADATA)
    return {city: dict(RTCC_CITY_METADATA[city]) for city in cities if city in RTCC_CITY_METADATA}


def get_rtcc_years(cities: Optional[List[str]] = None) -> Dict[str, int]:
    """Return city -> RTCC implementation year."""
    return {city: meta["rtcc_year"] for city, meta in get_rtcc_city_metadata(cities).items()}


def get_rtcc_oris(cities: Optional[List[str]] = None) -> Dict[str, str]:
    """Return city -> ORI mapping."""
    return {city: meta["ori"] for city, meta in get_rtcc_city_metadata(cities).items()}


@dataclass
class RTCCConfiguration:
    """RTCC program specification for the thesis."""

    treatment_cities: Dict[str, int] = field(default_factory=lambda: get_rtcc_years(STUDY1_RTCC_CITIES))
    comparison_cities: List[str] = field(default_factory=lambda: [
        "Baltimore",
        "Detroit",
        "Philadelphia",
        "Houston",
        "Chicago",
        "Memphis",
        "Charlotte",
        "Atlanta",
    ])
    study1_cities: List[str] = field(default_factory=lambda: list(STUDY1_RTCC_CITIES))
    start_year: int = 2010
    end_year: int = 2023
    pretreatment_years: int = 5

    def __post_init__(self):
        if self.start_year >= self.end_year:
            raise ValueError(f"start_year ({self.start_year}) must be < end_year ({self.end_year})")
        if self.pretreatment_years <= 0:
            raise ValueError(f"pretreatment_years must be positive, got {self.pretreatment_years}")


@dataclass
class DataSourceConfiguration:
    """Data source specifications and file locations."""

    fbi_cde_homicides_csv: Path = DATA_DIR / "fbi_cde_homicides.csv"
    bjs_nibrs_data_csv: Path = DATA_DIR / "bjs_nibrs_2015_2020.csv"
    lemas_2020_csv: Path = DATA_DIR / "lemas_2020.csv"
    acs_demographics_csv: Path = DATA_DIR / "acs_demographics_2015_2020.csv"
    washpost_homicides_csv: Path = DATA_DIR / "washpost_homicides_2015_2020.csv"
    master_panel_csv: Path = DATA_DIR / "master_analysis_panel.csv"
    analysis_ready_panel_csv: Path = DATA_DIR / "analysis_ready_panel.csv"
    master_panel_with_lemas_csv: Path = DATA_DIR / "master_analysis_panel_with_lemas.csv"
    master_panel_v2_csv: Path = DATA_DIR / "master_analysis_panel_v2.csv"
    rtcc_cities_json: Path = DATA_DIR / "rtcc_cities.json"

    def __post_init__(self):
        missing_files = []
        for attr_name in self.__dataclass_fields__:
            path = getattr(self, attr_name)
            if isinstance(path, Path) and not path.exists():
                missing_files.append(str(path))

        if missing_files:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Missing expected data files (may be generated): {missing_files}")


@dataclass
class PSMConfiguration:
    """Propensity Score Matching parameters for DiD estimation."""

    caliper: float = 0.05
    method: str = "nearest"
    replace: bool = True
    pscore_controls: List[str] = field(default_factory=lambda: [
        "total_officers",
        "pct_college_educated",
        "pct_female_officers",
        "pct_racial_minority",
        "community_policing_strategies",
        "use_of_force_hours_training",
    ])
    outcome_controls: List[str] = field(default_factory=lambda: [
        "unemployment_rate",
        "poverty_rate",
        "population_density",
    ])


@dataclass
class BayesianITSConfiguration:
    """Bayesian Interrupted Time Series parameters."""

    draws: int = 4000
    tune: int = 2000
    target_accept: float = 0.9
    rhat_threshold: float = 1.01
    prior_slope_std: float = 0.1
    prior_break_std: float = 0.5
    prior_noise_sd_prior: str = "HalfNormal(2.0)"


@dataclass
class ClassifierConfiguration:
    """Clearance classifier specifications."""

    models: List[str] = field(default_factory=lambda: [
        "xgboost",
        "random_forest",
        "logistic",
    ])
    cv_folds: int = 5
    random_state: int = 42
    xgb_params: Dict[str, Any] = field(default_factory=lambda: {
        "max_depth": 5,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "n_estimators": 100,
        "random_state": 42,
        "eval_metric": "logloss",
    })
    rf_params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 100,
        "max_depth": 10,
        "class_weight": "balanced",
        "random_state": 42,
    })
    logistic_params: Dict[str, Any] = field(default_factory=lambda: {
        "max_iter": 1000,
        "class_weight": "balanced",
        "random_state": 42,
    })


@dataclass
class APIConfiguration:
    """FBI and BJS API credentials and configuration."""

    fbi_api_key: str = field(default_factory=lambda: os.getenv("FBI_API_KEY", ""))
    fbi_api_base_url: str = "https://crime-data-explorer.fr.cloud.gov/api/v1"
    fbi_api_timeout: int = 30
    bjs_api_base_url: str = "https://data.ojp.usdoj.gov/API/"
    bjs_api_timeout: int = 30
    cache_dir: Path = PIPELINE_DIR / "cache"
    cache_ttl_hours: int = 24
    max_retries: int = 3
    initial_retry_delay: float = 1.0
    backoff_factor: float = 2.0


@dataclass
class ResultsConfiguration:
    """Output paths and formatting."""

    study1_dir: Path = RESULTS_DIR / "study1_rtcc"
    study1_tables_dir: Path = study1_dir / "tables"
    study1_figures_dir: Path = study1_dir / "figures"
    study2_dir: Path = RESULTS_DIR / "study2_dfr"
    study2_tables_dir: Path = study2_dir / "tables"
    study2_figures_dir: Path = study2_dir / "figures"
    robustness_dir: Path = study1_dir / "robustness"
    figure_dpi: int = 300
    figure_format: str = "png"


RTCC_CONFIG = RTCCConfiguration()
DATA_CONFIG = DataSourceConfiguration()
PSM_CONFIG = PSMConfiguration()
BAYESIAN_ITS_CONFIG = BayesianITSConfiguration()
CLASSIFIER_CONFIG = ClassifierConfiguration()
API_CONFIG = APIConfiguration()
RESULTS_CONFIG = ResultsConfiguration()


def validate_configuration() -> None:
    """Validate all configuration settings."""
    import logging

    logger = logging.getLogger(__name__)

    required_dirs = [DATA_DIR, PIPELINE_DIR]
    for dir_path in required_dirs:
        if not dir_path.exists():
            logger.error(f"Required directory missing: {dir_path}")
            raise FileNotFoundError(f"Directory not found: {dir_path}")

    if not API_CONFIG.fbi_api_key:
        logger.warning("FBI_API_KEY environment variable not set")

    logger.info("Configuration validation passed")


if __name__ == "__main__":
    print("=" * 70)
    print("RTCC Thesis Pipeline - Configuration Summary")
    print("=" * 70)
    print(f"\nStudy 1 Cities: {RTCC_CONFIG.study1_cities}")
    print(f"Study Period: {RTCC_CONFIG.start_year}-{RTCC_CONFIG.end_year}")
    print(f"PSM Caliper: {PSM_CONFIG.caliper}")
    print(f"Bayesian ITS Draws: {BAYESIAN_ITS_CONFIG.draws}")
    print(f"Classifier Models: {', '.join(CLASSIFIER_CONFIG.models)}")
    print(f"Results directory: {RESULTS_CONFIG.study1_dir}")
    print("=" * 70)
