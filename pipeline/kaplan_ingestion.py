"""
Kaplan UCR Return A Data Ingestion for RTCC Thesis
Source: OpenICPSR 100707-V22 (offenses_known_yearly_1960_2024.csv)

Extracts:
- 8 RTCC target cities (ORI mapped below)
- Comparison pool (100-300K population)
- Homicide counts: actual_murder, actual_manslaughter
- Clearance counts: total_cleared_murder, total_cleared_manslaughter
- Population, year, agency metadata

Author: Marcel Green <marcelo.green@yale.edu>
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# ============================================================================
# VERIFIED ORI CODES (from Kaplan yearly data inspection 2026-04-07)
# ============================================================================
# Note: Original thesis used different ORI codes. These are VERIFIED in the data.
# Chicago is NOT in this Kaplan dataset - will need FBI API for Chicago data.

RTCC_CITIES: Dict[str, Dict] = {
    "Hartford": {
        "ori9": "CT0006400",  # Verified: CT00064, CT0006400, hartford, connecticut
        "rtcc_year": 2016,
        "state": "CT"
    },
    "Miami": {
        "ori9": "FL0130200",  # Verified: FL01302, FL0130200, miami, florida
        "rtcc_year": 2016,
        "state": "FL"
    },
    "St. Louis": {
        "ori9": "MO0640000",  # Verified: MO06400, MO0640000, st louis, missouri
        "rtcc_year": 2015,
        "state": "MO"
    },
    "Newark": {
        "ori9": "NJ0071400",  # Verified: NJ00714, NJ0071400, newark, new jersey
        "rtcc_year": 2018,
        "state": "NJ"
    },
    "New Orleans": {
        "ori9": "LA0360000",  # Verified: LA03600, LA0360000, new orleans, louisiana
        "rtcc_year": 2017,
        "state": "LA"
    },
    "Albuquerque": {
        "ori9": "NM0010100",  # Verified: NM00101, NM0010100, albuquerque, new mexico
        "rtcc_year": 2020,
        "state": "NM"
    },
    "Fresno": {
        "ori9": "CA0190200",  # Verified: CA01902, CA0190200, fresno, california
        "rtcc_year": 2018,
        "state": "CA"
    },
    # Chicago NOT in Kaplan dataset - need FBI API
    # "Chicago": {
    #     "ori9": "ILXXXXXXX",  # Not found in Kaplan data
    #     "rtcc_year": 2017,
    #     "state": "IL"
    # },
}

# Column indices (0-indexed from header inspection)
COLS = {
    "ori7": 0,       # ori (7-digit)
    "ori9": 1,       # ori9 (9-digit) <- USE THIS
    "agency_name": 2,
    "state_name": 3,
    "state_abb": 4,
    "year": 5,
    "population": 47,  # population column
    "actual_murder": 61,      # col 62 in 1-indexed
    "actual_manslaughter": 62,  # col 63
    "total_cleared_murder": 92,  # col 93
    "total_cleared_manslaughter": 93,  # col 94
}


def load_kaplan_yearly(csv_path: str) -> pd.DataFrame:
    """
    Load the Kaplan yearly UCR data.

    Args:
        csv_path: Path to offenses_known_yearly_1960_2024.csv

    Returns:
        DataFrame with all columns
    """
    print(f"Loading Kaplan yearly data from {csv_path}...")

    # Define column names based on indices
    # Read with low_memory=False due to mixed types
    df = pd.read_csv(csv_path, low_memory=False)

    print(f"Loaded {len(df):,} records")
    print(f"Year range: {df['year'].min()} - {df['year'].max()}")
    print(f"Unique agencies: {df['ori9'].nunique():,}")

    return df


def extract_rtcc_cities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract data for RTCC target cities.

    Args:
        df: Full Kaplan DataFrame

    Returns:
        DataFrame with only RTCC cities
    """
    # Get list of RTCC ORI codes
    rtcc_oris = {v["ori9"] for v in RTCC_CITIES.values()}

    # Filter to RTCC cities
    df_rtcc = df[df["ori9"].isin(rtcc_oris)].copy()

    print(f"\nRTCC Cities Extraction:")
    print(f"  Found {len(df_rtcc):,} records for RTCC cities")

    # Verify each city is present
    found_oris = set(df_rtcc["ori9"].unique())
    for city, info in RTCC_CITIES.items():
        status = "FOUND" if info["ori9"] in found_oris else "MISSING"
        print(f"  {city}: {status} (ORI: {info['ori9']})")

    return df_rtcc


def build_comparison_pool(df: pd.DataFrame, rtcc_oris: set, pop_min: int = 100000, pop_max: int = 300000) -> pd.DataFrame:
    """
    Build comparison pool of mid-sized cities.

    Criteria:
    - Population 100,000 - 300,000
    - Not an RTCC city
    - At least 5 years of data
    - Has murder data (not all zeros)

    Args:
        df: Full Kaplan DataFrame
        rtcc_oris: Set of RTCC ORI codes to exclude
        pop_min: Minimum population
        pop_max: Maximum population

    Returns:
        DataFrame with comparison cities
    """
    print(f"\nBuilding comparison pool (population {pop_min:,} - {pop_max:,})...")

    # Filter by population and exclude RTCC cities
    df_comp = df[
        (df["population"] >= pop_min) &
        (df["population"] <= pop_max) &
        (~df["ori9"].isin(rtcc_oris))
    ].copy()

    print(f"  Initial pool: {len(df_comp):,} records")

    # Require at least 5 years of data per agency
    year_counts = df_comp.groupby("ori9")["year"].count()
    valid_agencies = year_counts[year_counts >= 5].index
    df_comp = df_comp[df_comp["ori9"].isin(valid_agencies)]

    print(f"  After 5-year requirement: {len(df_comp):,} records")
    print(f"  Unique agencies: {df_comp['ori9'].nunique():,}")

    return df_comp


def compute_clearance_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute clearance rate and derived metrics.

    Adds columns:
    - homicides: actual_murder + actual_manslaughter
    - cleared: total_cleared_murder + total_cleared_manslaughter
    - clearance_rate: cleared / homicides

    Args:
        df: DataFrame with raw counts

    Returns:
        DataFrame with computed metrics
    """
    df = df.copy()

    # Handle missing values
    for col in ["actual_murder", "actual_manslaughter", "total_cleared_murder", "total_cleared_manslaughter"]:
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Compute derived metrics
    df["homicides"] = df["actual_murder"] + df["actual_manslaughter"]
    df["cleared"] = df["total_cleared_murder"] + df["total_cleared_manslaughter"]

    # Clearance rate (handle division by zero)
    df["clearance_rate"] = np.where(
        df["homicides"] > 0,
        df["cleared"] / df["homicides"],
        np.nan
    )

    return df


def add_treatment_indicators(df: pd.DataFrame, rtcc_info: Dict) -> pd.DataFrame:
    """
    Add RTCC treatment indicators.

    Adds columns:
    - rtcc_city: Name of RTCC city (or None for comparison)
    - rtcc_year: Year RTCC was implemented
    - post_rtcc: 1 if year >= rtcc_year, else 0
    - years_since_rtcc: years since implementation (negative = before)

    Args:
        df: DataFrame
        rtcc_info: Dict mapping city name to {ori9, rtcc_year, state}

    Returns:
        DataFrame with treatment indicators
    """
    df = df.copy()

    # Create reverse mapping: ORI -> city info
    ori_to_city = {v["ori9"]: {"city": k, "rtcc_year": v["rtcc_year"]} for k, v in rtcc_info.items()}

    # Add city name and RTCC year
    df["rtcc_city"] = df["ori9"].map(lambda x: ori_to_city.get(x, {}).get("city"))
    df["rtcc_year_impl"] = df["ori9"].map(lambda x: ori_to_city.get(x, {}).get("rtcc_year"))

    # Treatment indicator
    df["post_rtcc"] = (
        (df["year"] >= df["rtcc_year_impl"]) &
        (df["rtcc_year_impl"].notna())
    ).astype(int)

    # Years since RTCC (negative = before implementation)
    df["years_since_rtcc"] = df["year"] - df["rtcc_year_impl"]

    return df


def run_ingestion_pipeline(
    csv_path: str,
    output_dir: str,
    pop_min: int = 100000,
    pop_max: int = 300000
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run the complete ingestion pipeline.

    Args:
        csv_path: Path to Kaplan yearly CSV
        output_dir: Directory for output files
        pop_min: Minimum population for comparison pool
        pop_max: Maximum population for comparison pool

    Returns:
        Tuple of (rtcc_df, comparison_df)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load data
    df = load_kaplan_yearly(csv_path)

    # Extract RTCC cities
    rtcc_oris = {v["ori9"] for v in RTCC_CITIES.values()}
    df_rtcc = extract_rtcc_cities(df)

    # Build comparison pool
    df_comp = build_comparison_pool(df, rtcc_oris, pop_min, pop_max)

    # Compute clearance metrics
    df_rtcc = compute_clearance_metrics(df_rtcc)
    df_comp = compute_clearance_metrics(df_comp)

    # Add treatment indicators
    df_rtcc = add_treatment_indicators(df_rtcc, RTCC_CITIES)

    # Mark comparison cities
    df_comp["rtcc_city"] = None
    df_comp["rtcc_year_impl"] = None
    df_comp["post_rtcc"] = 0
    df_comp["years_since_rtcc"] = np.nan
    df_comp["is_comparison"] = 1
    df_rtcc["is_comparison"] = 0

    # Combine for master panel
    # Select common columns
    common_cols = [
        "ori9", "agency_name", "state_name", "state_abb", "year",
        "population", "homicides", "cleared", "clearance_rate",
        "rtcc_city", "rtcc_year_impl", "post_rtcc", "years_since_rtcc",
        "is_comparison"
    ]

    # Ensure columns exist
    for col in common_cols:
        if col not in df_rtcc.columns:
            df_rtcc[col] = np.nan
        if col not in df_comp.columns:
            df_comp[col] = np.nan

    df_master = pd.concat([
        df_rtcc[common_cols],
        df_comp[common_cols]
    ], ignore_index=True)

    # Save outputs
    rtcc_out = output_path / "rtcc_cities_yearly.csv"
    comp_out = output_path / "comparison_pool_yearly.csv"
    master_out = output_path / "master_analysis_panel.csv"

    df_rtcc.to_csv(rtcc_out, index=False)
    df_comp.to_csv(comp_out, index=False)
    df_master.to_csv(master_out, index=False)

    print(f"\n{'='*60}")
    print("OUTPUT FILES")
    print(f"{'='*60}")
    print(f"RTCC cities:     {rtcc_out} ({len(df_rtcc):,} records)")
    print(f"Comparison pool: {comp_out} ({len(df_comp):,} records)")
    print(f"Master panel:    {master_out} ({len(df_master):,} records)")

    # Summary statistics
    print(f"\n{'='*60}")
    print("SUMMARY STATISTICS")
    print(f"{'='*60}")
    print(f"\nRTCC Cities ({df_rtcc['rtcc_city'].nunique()} cities):")
    print(f"  Year range: {df_rtcc['year'].min():.0f} - {df_rtcc['year'].max():.0f}")
    print(f"  Total homicides: {df_rtcc['homicides'].sum():,.0f}")
    print(f"  Total cleared: {df_rtcc['cleared'].sum():,.0f}")
    print(f"  Mean clearance rate: {df_rtcc['clearance_rate'].mean():.1%}")

    print(f"\nComparison Pool ({df_comp['ori9'].nunique()} agencies):")
    print(f"  Year range: {df_comp['year'].min():.0f} - {df_comp['year'].max():.0f}")
    print(f"  Total homicides: {df_comp['homicides'].sum():,.0f}")
    print(f"  Total cleared: {df_comp['cleared'].sum():,.0f}")
    print(f"  Mean clearance rate: {df_comp['clearance_rate'].mean():.1%}")

    return df_rtcc, df_comp


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Kaplan UCR data for RTCC thesis")
    parser.add_argument(
        "--input",
        default="thesis/Thesis Files/Kaplan_Data_100707-V22/offenses_known_yearly_1960_2024.csv",
        help="Path to Kaplan yearly CSV"
    )
    parser.add_argument(
        "--output",
        default="thesis/data",
        help="Output directory"
    )
    parser.add_argument(
        "--pop-min",
        type=int,
        default=100000,
        help="Minimum population for comparison pool"
    )
    parser.add_argument(
        "--pop-max",
        type=int,
        default=300000,
        help="Maximum population for comparison pool"
    )

    args = parser.parse_args()

    run_ingestion_pipeline(
        csv_path=args.input,
        output_dir=args.output,
        pop_min=args.pop_min,
        pop_max=args.pop_max
    )
