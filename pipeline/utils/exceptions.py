"""
Custom exceptions for RTCC impact evaluation pipeline.

Provides clear, typed error messages to aid debugging and thesis reviewer understanding.
"""


class RTCCPipelineError(Exception):
    """Base exception for all pipeline errors."""
    pass


class DataError(RTCCPipelineError):
    """Data loading, validation, or transformation error."""
    pass


class APIError(RTCCPipelineError):
    """Error from external API calls (FBI CDE, BJS, etc.)."""
    pass


class CachingError(RTCCPipelineError):
    """Error reading/writing cache."""
    pass


class ConfigurationError(RTCCPipelineError):
    """Configuration or environment setup error."""
    pass


class ModelError(RTCCPipelineError):
    """Model training or inference error."""
    pass


class EstimationConvergenceError(ModelError):
    """Model failed to converge (Bayesian ITS, PSM, etc.)."""
    
    def __init__(self, model_name: str, message: str = ""):
        self.model_name = model_name
        full_message = f"[{model_name}] Convergence failed"
        if message:
            full_message += f": {message}"
        super().__init__(full_message)


class MatchingError(ModelError):
    """Propensity score matching failed (no matches, poor overlap, etc.)."""
    pass


class ValidationError(RTCCPipelineError):
    """Data validation error."""
    pass


class ReproducibilityError(RTCCPipelineError):
    """Reproducibility issue (random seed, environment, etc.)."""
    pass
