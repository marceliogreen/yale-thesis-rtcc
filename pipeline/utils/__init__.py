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
