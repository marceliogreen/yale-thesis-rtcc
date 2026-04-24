"""
RTCC Clearance Rate Analysis - Real Data Pipeline

Uses:
1. Washington Post homicide data (2007-2017) - incident-level with clearance status
2. Kaplan UCR Return A (1960-2024) - longitudinal clearance data
3. FBI API - for updates and missing cities

Author: Marcel Green <marcelo.green@yale.edu>
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

# RTCC City Configuration (from thesis/Thesis Files/yale-thesis-rtcc/data/rtcc_cities.json)
RTCC_CITIES = {
    # ── Original 8 cities (ORIs corrected to city PD) ──
    "Chicago": {"ori": "ILCPD0000", "rtcc_year": 2017, "population": 2694000},
    "St. Louis": {"ori": "MOSPD0000", "rtcc_year": 2015, "population": 293000},
    "Miami": {"ori": "FL0130600", "rtcc_year": 2016, "population": 467000},
    "New Orleans": {"ori": "LANPD0000", "rtcc_year": 2017, "population": 376000},
    "Albuquerque": {"ori": "NM0010100", "rtcc_year": 2013, "population": 564000},  # RTCC opened March 2013
    "Fresno": {"ori": "CA0100500", "rtcc_year": 2015, "population": 545000},  # RTCC opened July 2015
    "Hartford": {"ori": "CT0006400", "rtcc_year": 2016, "population": 121000},  # Verified in Kaplan
    "Newark": {"ori": "NJNPD0000", "rtcc_year": 2018, "population": 277000},
    # ── Expanded: 7 new cities (8 → 15) ──
    "Memphis": {"ori": "TNMPD0000", "rtcc_year": 2008, "population": 633000},  # ✓ Memphis Flyer 4/16/2008, OJP/StateTech confirmed
    "Baltimore": {"ori": "MDBPD0000", "rtcc_year": 2013, "population": 576000},  # ⚠ Watch Center ~2013-2014, formal RTCC 2024
    "Detroit": {"ori": "MI8234900", "rtcc_year": 2016, "population": 639000},  # ✓ Project Green Light launch
    "Philadelphia": {"ori": "PAPEP0000", "rtcc_year": 2012, "population": 1600000},  # ✓ Technical.ly, Inquirer, Atlas of Surveillance
    "Houston": {"ori": "TXHPD0000", "rtcc_year": 2008, "population": 2300000},  # ✓ OJP — 4th US agency with RTCC, operating since 2008
    "Dallas": {"ori": "TXDPD0000", "rtcc_year": 2019, "population": 1300000},  # ✓ Atlas of Surveillance, Motorola partnership 2019
    "Denver": {"ori": "CODPD0000", "rtcc_year": 2019, "population": 716000},  # ✓ Atlas of Surveillance, RTCIC opened August 2019
}


def load_washington_post_data(filepath: str) -> pd.DataFrame:
    """
    Load and process Washington Post homicide data.

    Returns DataFrame with:
    - year, city, state
    - disposition (clearance status)
    - is_cleared (binary)
    """
    print(f"Loading Washington Post data from {filepath}...")

    # Handle encoding issues
    df = pd.read_csv(filepath, encoding='latin-1', on_bad_lines='skip')

    # Extract year
    df['year'] = df['reported_date'].astype(str).str[:4].astype(int)

    # Create clearance indicator - ONLY "Closed by arrest" counts as cleared
    # "Closed without arrest" is NOT cleared, "Open/No arrest" is NOT cleared
    df['is_cleared'] = (df['disposition'] == 'Closed by arrest').astype(int)

    print(f"  Loaded {len(df):,} records")
    print(f"  Year range: {df['year'].min()} - {df['year'].max()}")
    print(f"  Overall clearance rate: {df['is_cleared'].mean():.1%}")

    return df


def compute_annual_clearance_rates(df: pd.DataFrame, cities: List[str]) -> pd.DataFrame:
    """
    Compute annual clearance rates by city.

    Returns DataFrame with columns:
    - city, year
    - homicides (count)
    - cleared (count)
    - clearance_rate
    """
    # Filter to specified cities
    df_filtered = df[df['city'].isin(cities)].copy()

    # Aggregate by city and year
    annual = df_filtered.groupby(['city', 'year']).agg(
        homicides=('is_cleared', 'count'),
        cleared=('is_cleared', 'sum')
    ).reset_index()

    annual['clearance_rate'] = annual['cleared'] / annual['homicides']

    # Add RTCC year
    annual['rtcc_year'] = annual['city'].map(lambda x: RTCC_CITIES.get(x, {}).get('rtcc_year'))
    annual['post_rtcc'] = (annual['year'] >= annual['rtcc_year']).astype(int)

    return annual


def pre_post_analysis(annual_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute pre/post RTCC clearance rate changes.

    Returns summary DataFrame by city.
    """
    results = []

    for city in annual_df['city'].unique():
        city_data = annual_df[annual_df['city'] == city]
        rtcc_year = RTCC_CITIES.get(city, {}).get('rtcc_year')

        if rtcc_year is None:
            continue

        pre = city_data[city_data['year'] < rtcc_year]
        post = city_data[city_data['year'] >= rtcc_year]

        if len(pre) > 0 and len(post) > 0:
            results.append({
                'city': city,
                'rtcc_year': rtcc_year,
                'pre_years': len(pre),
                'post_years': len(post),
                'pre_homicides': pre['homicides'].sum(),
                'post_homicides': post['homicides'].sum(),
                'pre_clearance': pre['cleared'].sum() / pre['homicides'].sum() if pre['homicides'].sum() > 0 else np.nan,
                'post_clearance': post['cleared'].sum() / post['homicides'].sum() if post['homicides'].sum() > 0 else np.nan,
            })

    df_results = pd.DataFrame(results)
    df_results['change_pp'] = (df_results['post_clearance'] - df_results['pre_clearance']) * 100
    df_results['change_pct'] = ((df_results['post_clearance'] / df_results['pre_clearance']) - 1) * 100

    return df_results


def plot_clearance_trends(annual_df: pd.DataFrame, output_path: str):
    """
    Create visualization of clearance rate trends.
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    cities = annual_df['city'].unique()

    for i, city in enumerate(cities[:6]):
        ax = axes[i]
        city_data = annual_df[annual_df['city'] == city].sort_values('year')
        rtcc_year = RTCC_CITIES.get(city, {}).get('rtcc_year')

        # Plot clearance rate
        ax.plot(city_data['year'], city_data['clearance_rate'] * 100,
                'o-', linewidth=2, markersize=6, color='steelblue')

        # Add RTCC implementation line
        if rtcc_year:
            ax.axvline(x=rtcc_year, color='red', linestyle='--', linewidth=2,
                      label=f'RTCC ({rtcc_year})')

        ax.set_title(city, fontsize=12, fontweight='bold')
        ax.set_xlabel('Year')
        ax.set_ylabel('Clearance Rate (%)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 100)

    plt.suptitle('Homicide Clearance Rates: RTCC Cities (Washington Post Data 2007-2017)',
                fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved visualization to {output_path}")


def run_analysis_pipeline(wp_path: str, output_dir: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run the complete clearance rate analysis pipeline.

    Args:
        wp_path: Path to Washington Post homicides CSV
        output_dir: Directory for output files

    Returns:
        Tuple of (annual_rates, pre_post_summary)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load data
    df_wp = load_washington_post_data(wp_path)

    # Filter to RTCC cities that exist in data
    available_cities = [c for c in RTCC_CITIES.keys() if c in df_wp['city'].values]
    print(f"\nRTCC cities available in Washington Post data: {available_cities}")

    # Compute annual rates
    annual_rates = compute_annual_clearance_rates(df_wp, available_cities)

    # Pre/post analysis
    pre_post_summary = pre_post_analysis(annual_rates)

    # Save outputs
    annual_rates.to_csv(output_path / 'annual_clearance_rates.csv', index=False)
    pre_post_summary.to_csv(output_path / 'pre_post_rtcc_summary.csv', index=False)

    # Visualization
    plot_clearance_trends(annual_rates, str(output_path / 'clearance_trends.png'))

    # Print summary
    print(f"\n{'='*60}")
    print("PRE/POST RTCC CLEARANCE RATE ANALYSIS")
    print(f"{'='*60}")
    print(pre_post_summary.to_string(index=False))

    # Summary statistics
    print(f"\n{'='*60}")
    print("SUMMARY STATISTICS")
    print(f"{'='*60}")
    print(f"Average pre-RTCC clearance: {pre_post_summary['pre_clearance'].mean():.1%}")
    print(f"Average post-RTCC clearance: {pre_post_summary['post_clearance'].mean():.1%}")
    print(f"Average change: {pre_post_summary['change_pp'].mean():+.1f} percentage points")

    return annual_rates, pre_post_summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Clearance Rate Analysis")
    parser.add_argument(
        "--wp-data",
        default="thesis/Thesis Files/yale-thesis-rtcc/data/washington_post_homicides.csv",
        help="Path to Washington Post homicides CSV"
    )
    parser.add_argument(
        "--output",
        default="results/study1_rtcc",
        help="Output directory"
    )

    args = parser.parse_args()

    run_analysis_pipeline(args.wp_data, args.output)
