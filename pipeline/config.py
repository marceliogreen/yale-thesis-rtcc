"""
Centralized configuration for the RTCC impact evaluation pipeline.

This module defines all pipeline configuration including file paths, model parameters,
and RTCC treatment specifications. This centralization ensures reproducibility
across different environments and makes methodology transparent for thesis reviewers.

Treatment Cities and Dates (Source: RTCC program documentation):
- Cincinnati: May 2016
- Jackson, MS: November 2016
- Cleveland: January 2018
- Gun violence reduction tracking network: Multiple sites 2016-2018
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List
import os


# Root paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
SCRAPED_DATA_DIR = PROJECT_ROOT / "scraped_data"
PIPELINE_DIR = PROJECT_ROOT / "pipeline"


@dataclass
class RTCCConfiguration:
    """RTCC program specification: treatment cities and dates.
    
    All dates are based on official RTCC program documentation and verified
    through web scraping (see pipeline/scrapers/verify_rtcc_dates.py).
    """
    
    # RTCC Treatment Cities with Launch Dates (all dates are official announcements/launches)
    # Format: city -> year of RTCC announcement/implementation
    treatment_cities: Dict[str, int] = field(default_factory=lambda: {
        "Cincinnati": 2016,      # Official launch May 2016
        "Jackson": 2016,          # Official launch November 2016  
        "Cleveland": 2018,        # Official launch January 2018
    })
    
    # Comparison cities (matched on population size and pre-treatment crime trends)
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
    
    # Sample period: start year and end year
    # Note: Expanded to 2015-2020 to capture pre/post dynamics
    start_year: int = 2015
    end_year: int = 2020
    
    # Pre-treatment period for baseline estimation
    pretreatment_years: int = 5  # 2015-2019 is baseline period
    
    def __post_init__(self):
        """Validate configuration."""
        if self.start_year >= self.end_year:
            raise ValueError(f"start_year ({self.start_year}) must be < end_year ({self.end_year})")
        if self.pretreatment_years <= 0:
            raise ValueError(f"pretreatment_years must be positive, got {self.pretreatment_years}")


@dataclass
class DataSourceConfiguration:
    """Data source specifications and file locations."""
    
    # Raw data files
    fbi_cde_homicides_csv: Path = DATA_DIR / "fbi_cde_homicides.csv"
    bjs_nibrs_data_csv: Path = DATA_DIR / "bjs_nibrs_2015_2020.csv"
    lemas_2020_csv: Path = DATA_DIR / "lemas_2020.csv"
    acs_demographics_csv: Path = DATA_DIR / "acs_demographics_2015_2020.csv"
    washpost_homicides_csv: Path = DATA_DIR / "washpost_homicides_2015_2020.csv"
    
    # Master analysis panel (created by build_panel_v2.py)
    master_panel_csv: Path = DATA_DIR / "master_analysis_panel.csv"
    analysis_ready_panel_csv: Path = DATA_DIR / "analysis_ready_panel.csv"
    
    # RTCC city reference data
    rtcc_cities_json: Path = DATA_DIR / "rtcc_cities.json"
    
    def __post_init__(self):
        """Log which files are missing (for debugging)."""
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
    
    # Matching specification
    caliper: float = 0.05  # Caliper width as SD of propensity score
    # Rationale: 0.05 SD recommended by Austin (2009), reduces bias while maintaining sample
    # Sensitivity test in robustness/: caliper_sensitivity.py tests 0.01, 0.05, 0.1
    
    method: str = "nearest"  # "nearest", "stratification", "subclassification"
    replace: bool = True     # Allow replacement in matching
    
    # Control variables for propensity score model
    # LEMAS 2020 observed variables
    pscore_controls: List[str] = field(default_factory=lambda: [
        "total_officers",          # Department size (controls for capacity)
        "pct_college_educated",    # Officer education level
        "pct_female_officers",     # Officer demographics
        "pct_racial_minority",     # Officer diversity
        "community_policing_strategies",  # Existing practice
        "use_of_force_hours_training",    # Training intensity
    ])
    
    # Outcome model controls (beyond treatment and matching variables)
    outcome_controls: List[str] = field(default_factory=lambda: [
        "unemployment_rate",    # Economic conditions
        "poverty_rate",         # Socioeconomic status
        "population_density",   # Urbanization
    ])


@dataclass
class BayesianITSConfiguration:
    """Bayesian Interrupted Time Series parameters."""
    
    # PyMC sampling configuration
    draws: int = 4000          # MCMC samples after burn-in
    tune: int = 2000           # Burn-in/tuning samples
    target_accept: float = 0.9 # Target acceptance for HMC
    
    # Convergence diagnostics
    # Rhat < 1.01 indicates convergence (Gelman & Rubin 1992)
    rhat_threshold: float = 1.01
    
    # Prior specifications (documented for methodological clarity)
    prior_slope_std: float = 0.1  # SD of trend slope (weekly change)
    prior_break_std: float = 0.5  # SD of level shift at RTCC announcement
    prior_noise_sd_prior: str = "HalfNormal(2.0)"  # Residual noise


@dataclass
class ClassifierConfiguration:
    """Clearance classifier specifications."""
    
    # Models to ensemble
    models: List[str] = field(default_factory=lambda: [
        "xgboost",
        "random_forest", 
        "logistic_regression",
    ])
    
    # Cross-validation
    cv_folds: int = 5
    random_state: int = 42
    
    # XGBoost parameters
    xgb_params: Dict = field(default_factory=lambda: {
        "max_depth": 5,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "n_estimators": 100,
    })
    
    # Random Forest parameters
    rf_params: Dict = field(default_factory=lambda: {
        "n_estimators": 100,
        "max_depth": 10,
        "class_weight": "balanced",
    })


@dataclass
class APIConfiguration:
    """FBI and BJS API credentials and configuration."""
    
    # FBI CDE API
    fbi_api_key: str = field(default_factory=lambda: os.getenv("FBI_API_KEY", ""))
    fbi_api_base_url: str = "https://crime-data-explorer.fr.cloud.gov/api/v1"
    fbi_api_timeout: int = 30
    
    # BJS API
    bjs_api_base_url: str = "https://data.ojp.usdoj.gov/API/"
    bjs_api_timeout: int = 30
    
    # Cache configuration
    cache_dir: Path = PIPELINE_DIR / "cache"
    cache_ttl_hours: int = 24  # Cache validity period
    
    # Retry configuration
    max_retries: int = 3
    initial_retry_delay: float = 1.0  # seconds
    backoff_factor: float = 2.0


@dataclass
class ResultsConfiguration:
    """Output paths and formatting."""
    
    # Study 1: RTCC Impact via PSM-DiD
    study1_dir: Path = RESULTS_DIR / "study1_rtcc"
    study1_tables_dir: Path = study1_dir / "tables"
    study1_figures_dir: Path = study1_dir / "figures"
    
    # Study 2: Clearance classifier
    study2_dir: Path = RESULTS_DIR / "study2_dfr"
    study2_tables_dir: Path = study2_dir / "tables"
    study2_figures_dir: Path = study2_dir / "figures"
    
    # Robustness checks
    robustness_dir: Path = study1_dir / "robustness"
    
    # Figure format and DPI
    figure_dpi: int = 300
    figure_format: str = "png"


# ============================================================================
# Global Configuration Instances
# ============================================================================

RTCC_CONFIG = RTCCConfiguration()
DATA_CONFIG = DataSourceConfiguration()
PSM_CONFIG = PSMConfiguration()
BAYESIAN_ITS_CONFIG = BayesianITSConfiguration()
CLASSIFIER_CONFIG = ClassifierConfiguration()
API_CONFIG = APIConfiguration()
RESULTS_CONFIG = ResultsConfiguration()


def validate_configuration() -> None:
    """Validate all configuration settings.
    
    Should be called at pipeline startup to catch configuration errors early.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Check required directories exist
    required_dirs = [DATA_DIR, PIPELINE_DIR]
    for dir_path in required_dirs:
        if not dir_path.exists():
            logger.error(f"Required directory missing: {dir_path}")
            raise FileNotFoundError(f"Directory not found: {dir_path}")
    
    # Check API configuration
    if not API_CONFIG.fbi_api_key:
        logger.warning("FBI_API_KEY environment variable not set")
    
    logger.info("Configuration validation passed")


if __name__ == "__main__":
    """Print configuration summary for documentation."""
    print("=" * 70)
    print("RTCC Impact Evaluation Pipeline - Configuration Summary")
    print("=" * 70)
    print(f"\nTreatment Cities: {list(RTCC_CONFIG.treatment_cities.keys())}")
    print(f"Study Period: {RTCC_CONFIG.start_year}-{RTCC_CONFIG.end_year}")
    print(f"PSM Caliper: {PSM_CONFIG.caliper} SD (Austin 2009 recommendation)")
    print(f"Bayesian ITS Draws: {BAYESIAN_ITS_CONFIG.draws}")
    print(f"Classifier Models: {', '.join(CLASSIFIER_CONFIG.models)}")
    print(f"Results directory: {RESULTS_CONFIG.study1_dir}")
    print("=" * 70)
