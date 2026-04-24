"""Diagnostics utilities for Study 1 causal analyses.

These functions provide explicit, auditable diagnostics for:
- PSM covariate balance via standardized mean differences (SMD)
- Bayesian MCMC convergence via R-hat thresholds
"""

from __future__ import annotations

from typing import Dict, Iterable

import numpy as np

from .exceptions import EstimationConvergenceError, MatchingError


def _safe_smd(treated: np.ndarray, control: np.ndarray) -> float:
    """Compute standardized mean difference with pooled SD denominator."""
    if treated.size == 0 or control.size == 0:
        return np.nan

    t_mean = float(np.mean(treated))
    c_mean = float(np.mean(control))
    t_var = float(np.var(treated, ddof=1)) if treated.size > 1 else 0.0
    c_var = float(np.var(control, ddof=1)) if control.size > 1 else 0.0
    pooled_sd = np.sqrt((t_var + c_var) / 2.0)

    if pooled_sd == 0.0:
        return 0.0 if np.isclose(t_mean, c_mean) else np.nan

    return (t_mean - c_mean) / pooled_sd


def compute_psm_smd(
    unmatched_data,
    matched_data,
    covariates: Iterable[str],
    treated_col: str = "treated",
    threshold: float = 0.1,
) -> Dict[str, Dict[str, float | str]]:
    """Compute before/after matching SMD diagnostics for requested covariates."""
    results: Dict[str, Dict[str, float | str]] = {}

    for covariate in covariates:
        if covariate not in unmatched_data.columns or covariate not in matched_data.columns:
            continue

        unmatched_t = unmatched_data.loc[unmatched_data[treated_col] == 1, covariate].dropna().to_numpy()
        unmatched_c = unmatched_data.loc[unmatched_data[treated_col] == 0, covariate].dropna().to_numpy()
        matched_t = matched_data.loc[matched_data[treated_col] == 1, covariate].dropna().to_numpy()
        matched_c = matched_data.loc[matched_data[treated_col] == 0, covariate].dropna().to_numpy()

        smd_before = _safe_smd(unmatched_t, unmatched_c)
        smd_after = _safe_smd(matched_t, matched_c)
        abs_after = abs(smd_after) if np.isfinite(smd_after) else np.inf

        results[covariate] = {
            "smd_before": smd_before,
            "smd_after": smd_after,
            "status": "PASS" if abs_after < threshold else "FAIL",
        }

    if not results:
        raise MatchingError("No valid covariates available for SMD balance diagnostics.")

    return results


def print_psm_balance_table(smd_results: Dict[str, Dict[str, float | str]], threshold: float = 0.1) -> None:
    """Print a balance table and raise if any matched SMD exceeds threshold."""
    print("\nPSM Balance Diagnostics (SMD)")
    print(f"Threshold: |SMD| < {threshold}")
    print("-" * 68)
    print(f"{'Covariate':30s} {'Before':>10s} {'After':>10s} {'Status':>10s}")
    print("-" * 68)

    failed = []
    for covariate, values in smd_results.items():
        before = values["smd_before"]
        after = values["smd_after"]
        status = str(values["status"])

        before_str = f"{before:+.3f}" if np.isfinite(before) else "nan"
        after_str = f"{after:+.3f}" if np.isfinite(after) else "nan"
        print(f"{covariate:30s} {before_str:>10s} {after_str:>10s} {status:>10s}")

        if status != "PASS":
            failed.append(covariate)

    print("-" * 68)
    print(f"Balanced covariates: {len(smd_results) - len(failed)}/{len(smd_results)}")

    if failed:
        raise MatchingError(
            "PSM balance criterion failed for covariates: " + ", ".join(failed)
        )


def extract_bayesian_convergence(trace, model_name: str, rhat_threshold: float = 1.01) -> Dict[str, float]:
    """Extract max R-hat per parameter and enforce convergence threshold."""
    import arviz as az

    rhat_ds = az.rhat(trace)
    diagnostics: Dict[str, float] = {}

    for var_name, arr in rhat_ds.data_vars.items():
        values = np.asarray(arr.values).astype(float).reshape(-1)
        finite_vals = values[np.isfinite(values)]
        if finite_vals.size == 0:
            continue
        diagnostics[var_name] = float(np.max(finite_vals))

    if not diagnostics:
        raise EstimationConvergenceError(model_name, "Unable to compute R-hat diagnostics.")

    offenders = [k for k, v in diagnostics.items() if v > rhat_threshold]
    if offenders:
        details = ", ".join(f"{k}={diagnostics[k]:.4f}" for k in offenders)
        raise EstimationConvergenceError(
            model_name,
            f"R-hat above threshold {rhat_threshold}: {details}",
        )

    return diagnostics


def print_bayesian_convergence(diagnostics: Dict[str, float], rhat_threshold: float = 1.01) -> None:
    """Print parameter-level convergence diagnostics."""
    print("\nBayesian Convergence Diagnostics (R-hat)")
    print(f"Threshold: R-hat <= {rhat_threshold}")
    print("-" * 56)
    print(f"{'Parameter':30s} {'R-hat':>10s} {'Status':>10s}")
    print("-" * 56)

    for parameter, rhat in sorted(diagnostics.items()):
        status = "PASS" if rhat <= rhat_threshold else "FAIL"
        print(f"{parameter:30s} {rhat:>10.4f} {status:>10s}")

    print("-" * 56)
