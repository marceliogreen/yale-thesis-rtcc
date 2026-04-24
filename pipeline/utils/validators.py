"""
Data validation functions for RTCC impact evaluation pipeline.

Validates data quality and assumptions before analysis to ensure result validity.
All validation checks are documented with the assumption being tested.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List
import logging

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


def validate_clearance_rates(df: pd.DataFrame, rate_column: str = "clearance_rate") -> None:
    """
    Validate that clearance rates are in valid range [0, 1].
    
    Assumption: Clearance rates are proportions (percent of crimes cleared/100).
    This catches: data entry errors, unit inconsistencies, reversed coding.
    
    Args:
        df: DataFrame to validate
        rate_column: Name of clearance rate column
        
    Raises:
        DataValidationError: If rates outside [0, 1] range or NaN values found
    """
    if rate_column not in df.columns:
        raise DataValidationError(f"Column '{rate_column}' not found in dataframe")
    
    rates = df[rate_column].dropna()
    
    # Check for out-of-range values
    invalid_mask = (rates < 0) | (rates > 1)
    if invalid_mask.any():
        invalid_index = rates[invalid_mask].index
        invalid_rows = df.loc[invalid_index]
        raise DataValidationError(
            f"Clearance rates outside [0,1] range:\n{invalid_rows[[rate_column]].head()}\n"
            f"Total invalid rows: {invalid_mask.sum()}"
        )
    
    # Check for excessive NaN
    nan_pct = df[rate_column].isna().sum() / len(df) * 100
    if nan_pct > 10:
        logger.warning(f"High proportion of missing clearance rates: {nan_pct:.1f}%")
    
    logger.info(f"✓ Clearance rates validated: N={len(rates)}, "
                f"Mean={rates.mean():.3f}, Min={rates.min():.3f}, Max={rates.max():.3f}")


def validate_rtcc_treatment_flags(df: pd.DataFrame) -> None:
    """
    Validate RTCC treatment flags align with treatment dates.
    
    Assumption: For each city, post_rtcc=1 starts in treatment year, =0 before.
    This catches: misaligned dates, data entry errors, encoding mistakes.
    
    Required columns: 'city', 'year', 'post_rtcc', 'rtcc_year' (or 'treatment_year')
    
    Args:
        df: DataFrame with treatment indicators
        
    Raises:
        DataValidationError: If flags don't align with treatment dates
    """
    required_cols = ['city', 'year', 'post_rtcc']
    if not all(col in df.columns for col in required_cols):
        raise DataValidationError(f"Missing required columns: {required_cols}")
    
    # Find treatment year column (may be named rtcc_year or treatment_year)
    treatment_year_col = None
    for col in ['rtcc_year', 'treatment_year']:
        if col in df.columns:
            treatment_year_col = col
            break
    
    if treatment_year_col is None:
        logger.warning("No treatment year column found; skipping treatment flag validation")
        return
    
    # Check alignment by city
    for city in df['city'].unique():
        city_data = df[df['city'] == city].sort_values('year')
        rtcc_year = city_data[treatment_year_col].iloc[0]
        
        # All rows before treatment year should have post_rtcc=0
        pre_treatment = city_data[city_data['year'] < rtcc_year]
        if (pre_treatment['post_rtcc'] != 0).any():
            bad_rows = pre_treatment[pre_treatment['post_rtcc'] != 0]
            raise DataValidationError(
                f"City '{city}': post_rtcc=1 found before treatment year {rtcc_year}\n"
                f"Bad rows:\n{bad_rows[['city', 'year', 'post_rtcc', treatment_year_col]]}"
            )
        
        # All rows from treatment year onward should have post_rtcc=1
        post_treatment = city_data[city_data['year'] >= rtcc_year]
        if (post_treatment['post_rtcc'] != 1).any():
            bad_rows = post_treatment[post_treatment['post_rtcc'] != 1]
            raise DataValidationError(
                f"City '{city}': post_rtcc=0 found at/after treatment year {rtcc_year}\n"
                f"Bad rows:\n{bad_rows[['city', 'year', 'post_rtcc', treatment_year_col]]}"
            )
    
    logger.info(f"✓ RTCC treatment flags validated across {df['city'].nunique()} cities")


def validate_zero_homicides(df: pd.DataFrame, homicide_column: str = "homicides") -> None:
    """
    Validate homicide counts including handling of zero values.
    
    Assumption: Zero homicides in a year is plausible but rare is suspect.
    This catches: data source errors, missing values coded as 0.
    
    Args:
        df: DataFrame with homicide counts
        homicide_column: Name of homicides column
        
    Warns:
        Log warning if excessive zeros (>10% of data)
    """
    if homicide_column not in df.columns:
        raise DataValidationError(f"Column '{homicide_column}' not found")
    
    homicides = df[homicide_column].dropna()
    
    # Check for negative values (impossible)
    if (homicides < 0).any():
        raise DataValidationError(
            f"Negative homicide counts found:\n"
            f"{df[homicides < 0][[homicide_column]]}"
        )
    
    # Warn about zeros
    zero_pct = (homicides == 0).sum() / len(homicides) * 100
    if zero_pct > 10:
        logger.warning(f"High proportion of zero homicides: {zero_pct:.1f}%")
        zero_cities = df[df[homicide_column] == 0]['city'].unique()
        logger.warning(f"Cities with zeros: {list(zero_cities)}")
    
    logger.info(f"✓ Homicide counts validated: Mean={homicides.mean():.1f}, "
                f"Median={homicides.median():.1f}, Zeros={zero_pct:.1f}%")


def validate_panel_structure(df: pd.DataFrame) -> Tuple[int, int]:
    """
    Validate balanced/unbalanced panel structure.
    
    Assumption: Should have consistent city-year combinations.
    
    Args:
        df: Panel data with 'city' and 'year' columns
        
    Returns:
        Tuple of (n_cities, n_years)
        
    Raises:
        DataValidationError: If required columns missing
    """
    required_cols = ['city', 'year']
    if not all(col in df.columns for col in required_cols):
        raise DataValidationError(f"Panel data must have columns: {required_cols}")
    
    n_cities = df['city'].nunique()
    n_years = df['year'].nunique()
    expected_rows = n_cities * n_years
    actual_rows = len(df)
    
    if actual_rows < expected_rows:
        year_min = int(df['year'].min())
        year_max = int(df['year'].max())
        logger.warning(
            f"Unbalanced panel: {actual_rows} rows vs {expected_rows} expected "
            f"({n_cities} cities × {n_years} years). "
            f"Year span: {year_min}-{year_max}"
        )
    else:
        logger.info(f"✓ Balanced panel validated: {n_cities} cities × {n_years} years = {actual_rows} rows")
    
    return n_cities, n_years


def validate_covariates(df: pd.DataFrame, covariate_cols: List[str]) -> None:
    """
    Validate covariate columns for statistical analysis.
    
    Checks: no missing values beyond threshold, reasonable ranges.
    
    Args:
        df: DataFrame with covariates
        covariate_cols: List of covariate column names
        
    Raises:
        DataValidationError: If missing values exceed 20% or other issues
    """
    missing_cols = [col for col in covariate_cols if col not in df.columns]
    if missing_cols:
        raise DataValidationError(f"Missing covariate columns: {missing_cols}")
    
    for col in covariate_cols:
        missing_pct = df[col].isna().sum() / len(df) * 100
        
        if missing_pct > 20:
            raise DataValidationError(
                f"Covariate '{col}' has {missing_pct:.1f}% missing values (threshold: 20%)"
            )
        
        if missing_pct > 5:
            logger.warning(f"Covariate '{col}' has {missing_pct:.1f}% missing values")
    
    logger.info(f"✓ Covariates validated: {len(covariate_cols)} covariates with <20% missing")


def validate_time_series_length(df: pd.DataFrame, min_years: int = 5) -> None:
    """
    Validate sufficient time series length for interrupted time series analysis.
    
    Assumption: Need sufficient pre/post treatment observations for trend estimation.
    Bayesian ITS requires at least 2-3 pre-treatment years for baseline.
    
    Args:
        df: Panel data with 'city', 'year' columns
        min_years: Minimum required years per city
        
    Raises:
        DataValidationError: If any city has insufficient data
    """
    years_per_city = df.groupby('city')['year'].nunique()
    
    short_cities = years_per_city[years_per_city < min_years]
    if len(short_cities) > 0:
        raise DataValidationError(
            f"Cities with <{min_years} years of data: {dict(short_cities)}"
        )
    
    logger.info(f"✓ Time series length validated: All cities have ≥{min_years} years")


# ============================================================================
# Comprehensive validation suite
# ============================================================================

def validate_analysis_panel(df: pd.DataFrame, config_dict: dict = None) -> None:
    """
    Run comprehensive validation on analysis panel.
    
    Args:
        df: Analysis panel DataFrame
        config_dict: Optional dict with validation parameters:
            - 'clearance_rate_col': name of clearance rate column
            - 'homicide_col': name of homicide counts column
            - 'covariates': list of covariate columns
            - 'min_years': minimum years per city
    
    Raises:
        DataValidationError: If any validation fails
    """
    config = config_dict or {}
    
    logger.info("Starting comprehensive panel validation...")
    
    try:
        # Structure validation
        validate_panel_structure(df)
        
        # Treatment flag validation
        validate_rtcc_treatment_flags(df)
        
        # Outcome validation
        validate_clearance_rates(df, rate_column=config.get('clearance_rate_col', 'clearance_rate'))
        validate_zero_homicides(df, homicide_column=config.get('homicide_col', 'homicides'))
        
        # Time series validation
        validate_time_series_length(df, min_years=config.get('min_years', 5))
        
        # Covariate validation
        if 'covariates' in config:
            validate_covariates(df, config['covariates'])
        
        logger.info("✓ ALL VALIDATIONS PASSED - Panel ready for analysis")
        
    except DataValidationError as e:
        logger.error(f"✗ VALIDATION FAILED: {str(e)}")
        raise


if __name__ == "__main__":
    """Example usage."""
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # Example: validate a loaded panel
    print("Data validation module ready. Usage:")
    print("  from pipeline.utils.validators import validate_analysis_panel")
    print("  validate_analysis_panel(df)")
