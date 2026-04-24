"""Utilities for RTCC impact evaluation pipeline."""

from .validators import (
    validate_clearance_rates,
    validate_rtcc_treatment_flags,
    validate_zero_homicides,
    validate_panel_structure,
    validate_covariates,
    validate_time_series_length,
    validate_analysis_panel,
    DataValidationError,
)

from .diagnostics import (
    compute_psm_smd,
    print_psm_balance_table,
    extract_bayesian_convergence,
    print_bayesian_convergence,
)

from .exceptions import (
    RTCCPipelineError,
    DataError,
    APIError,
    CachingError,
    ConfigurationError,
    ModelError,
    EstimationConvergenceError,
    MatchingError,
    ValidationError,
    ReproducibilityError,
)

__all__ = [
    # Validators
    "validate_clearance_rates",
    "validate_rtcc_treatment_flags",
    "validate_zero_homicides",
    "validate_panel_structure",
    "validate_covariates",
    "validate_time_series_length",
    "validate_analysis_panel",
    "DataValidationError",
    # Diagnostics
    "compute_psm_smd",
    "print_psm_balance_table",
    "extract_bayesian_convergence",
    "print_bayesian_convergence",
    # Exceptions
    "RTCCPipelineError",
    "DataError",
    "APIError",
    "CachingError",
    "ConfigurationError",
    "ModelError",
    "EstimationConvergenceError",
    "MatchingError",
    "ValidationError",
    "ReproducibilityError",
]
