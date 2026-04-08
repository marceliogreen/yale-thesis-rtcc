"""
Data Reconciliation — Verify ORI mappings, document city vs county data

Checks:
1. ORI-to-city mapping in rtcc_cities.json against actual data
2. Fresno ORI issue (CA0190200 = "arcadia" in Kaplan, not Fresno)
3. County vs city-level data documentation
4. Outputs analysis_ready_panel.csv with data_level column

Author: Marcel Green <marcelo.green@yale.edu>
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent  # -> yale-thesis-rtcc/
DATA_DIR = BASE / "data"

# State-to-region mapping
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

# Known ORI data levels (city vs county)
ORI_DATA_LEVEL = {
    "CT0006400": "city",       # Hartford PD — city-level
    "FL0130200": "county",     # Miami-Dade county agency
    "MO0640000": "city",       # St. Louis PD — city-level (independent city)
    "NJ0071400": "city",       # Newark PD — city-level
    "LA0360000": "parish",     # Orleans Parish — county-equivalent
    "NM0010100": "county",     # Bernalillo County (Albuquerque area)
    "CA0190200": "UNKNOWN",    # Arcadia, CA — NOT Fresno!
    "IL0160000": "county",     # Cook County
}


def reconcile():
    """Run full data reconciliation."""
    print("=" * 60)
    print("DATA RECONCILIATION REPORT")
    print("=" * 60)

    # Load RTCC config
    config_path = BASE / "data" / "rtcc_cities.json"
    with open(config_path) as f:
        rtcc_config = json.load(f)

    # Load panel data
    panel_path = DATA_DIR / "master_analysis_panel.csv"
    df = pd.read_csv(panel_path)
    print(f"\nPanel data: {len(df)} rows, columns: {list(df.columns)}")

    # --- Check each RTCC city ---
    print(f"\n{'='*60}")
    print("RTCC CITY ORI VERIFICATION")
    print(f"{'='*60}")

    issues = []

    for city, config in rtcc_config.items():
        ori = config["ori"]
        rtcc_year = config["rtcc_year"]

        # Check if ORI exists in panel
        match = df[df["ori9"] == ori]
        data_level = ORI_DATA_LEVEL.get(ori, "unknown")

        if match.empty:
            print(f"\n  {city} ({ori}): NOT IN PANEL")
            issues.append({"city": city, "ori": ori, "issue": "NOT_IN_PANEL", "data_level": data_level})
        else:
            agency_name = match["agency_name"].iloc[0] if "agency_name" in match.columns else "N/A"
            years = sorted(match["year"].unique())
            homicides = match[match["homicides"] > 0]
            has_clearance = match["clearance_rate"].notna().any()

            print(f"\n  {city} ({ori}):")
            print(f"    Agency name in data: {agency_name}")
            print(f"    Data level: {data_level}")
            print(f"    Years: {min(years)}-{max(years)} ({len(years)} years)")
            print(f"    Records with homicides > 0: {len(homicides)}")
            print(f"    Has clearance data: {has_clearance}")

            if "arcadia" in str(agency_name).lower():
                print(f"    ⚠️  WARNING: ORI {ori} maps to '{agency_name}', NOT {city}!")
                issues.append({"city": city, "ori": ori, "issue": "WRONG_AGENCY", "data_level": data_level,
                               "actual_agency": agency_name})

            if data_level in ("county", "parish"):
                print(f"    ⚠️  NOTE: County/parish-level data, not city PD")

    # --- Fresno ORI investigation ---
    print(f"\n{'='*60}")
    print("FRESNO ORI INVESTIGATION")
    print(f"{'='*60}")

    fresno_county_oris = df[df["state_abb"] == "CA"]
    fresno_area = fresno_county_oris[fresno_county_oris["agency_name"].str.contains("fresno", case=False, na=False)]
    if not fresno_area.empty:
        print(f"Agencies with 'Fresno' in name:")
        for _, row in fresno_area.drop_duplicates(subset=["ori9"]).iterrows():
            print(f"  ORI: {row['ori9']}, Agency: {row['agency_name']}")

    # --- Build clean panel ---
    print(f"\n{'='*60}")
    print("BUILDING ANALYSIS-READY PANEL")
    print(f"{'='*60}")

    # Filter to 2010-2024
    clean = df[(df["year"] >= 2010) & (df["year"] <= 2024)].copy()

    # Add region
    clean["region"] = clean["state_abb"].map(STATE_TO_REGION).fillna("Unknown")

    # Add data level
    clean["data_level"] = clean["ori9"].map(ORI_DATA_LEVEL).fillna("city")

    # Mark RTCC cities
    rtcc_oris = {v["ori"]: k for k, v in rtcc_config.items()}
    clean["rtcc_city_name"] = clean["ori9"].map(rtcc_oris)
    clean["is_rtcc"] = clean["rtcc_city_name"].notna()

    # Add RTCC year
    rtcc_years = {k: v["rtcc_year"] for k, v in rtcc_config.items()}
    clean["rtcc_year_impl"] = clean["rtcc_city_name"].map(rtcc_years)

    # Compute pre-trend slopes per city (clearance rate trend 2010-RTCC year)
    pre_trends = {}
    for city_name in rtcc_config:
        ori = rtcc_config[city_name]["ori"]
        ry = rtcc_config[city_name]["rtcc_year"]
        city_data = clean[(clean["ori9"] == ori) & (clean["year"] < ry) & (clean["homicides"] > 0)]
        if len(city_data) >= 3:
            slope = np.polyfit(city_data["year"], city_data["clearance_rate"], 1)[0]
            pre_trends[ori] = slope
        else:
            pre_trends[ori] = float("nan")

    clean["pre_trend_slope"] = clean["ori9"].map(pre_trends)

    # Remove agencies with 5+ consecutive years of zero homicides
    zero_homicide_streaks = clean.groupby("ori9").apply(
        lambda g: _max_zero_streak(g["homicides"].values)
    )
    bad_oris = zero_homicide_streaks[zero_homicide_streaks >= 5].index
    clean = clean[~clean["ori9"].isin(bad_oris)]

    print(f"Final panel: {len(clean)} rows")
    print(f"  RTCC city observations: {clean['is_rtcc'].sum()}")
    print(f"  Comparison observations: {(~clean['is_rtcc']).sum()}")
    print(f"  Cities/agencies: {clean['ori9'].nunique()}")
    print(f"  Date range: {clean['year'].min()}-{clean['year'].max()}")

    # Save
    out_path = DATA_DIR / "analysis_ready_panel.csv"
    clean.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")

    # Save issues report
    if issues:
        issues_df = pd.DataFrame(issues)
        issues_path = DATA_DIR / "data_issues.csv"
        issues_df.to_csv(issues_path, index=False)
        print(f"Issues saved to {issues_path}")


def _max_zero_streak(values):
    """Find max consecutive zeros."""
    import numpy as np
    max_streak = 0
    current = 0
    for v in values:
        if v == 0:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 0
    return max_streak


if __name__ == "__main__":
    reconcile()
