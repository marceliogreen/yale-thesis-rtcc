"""
FBI CDE Webapp API Client (Reverse-Engineered)

The FBI CDE migrated from api.usa.gov (dead) to cde.ucr.cjis.gov.
The webapp at /LATEST/webapp/ uses undocumented internal API endpoints
discovered by analyzing the Angular SPA JavaScript bundle.

Working Endpoints:
  - /LATEST/shr/agency/{ORI}?from=MM-YYYY&to=MM-YYYY&type=counts
      Monthly homicide offense counts by agency
  - /LATEST/shr/state/{STATE}?from=MM-YYYY&to=MM-YYYY&type=counts
      Monthly homicide offense counts by state
  - /LATEST/agency/byStateAbbr/{STATE}
      Agency listings by state
  - /LATEST/lookup/{type}
      Lookup data (states, offenses, cde_properties)
  - /LATEST/participation/agency/{...}
      Agency participation data

Data currency: UCR data through 03/2026 (as of 2026-04-16)
No authentication required for these endpoints.

Author: Marcel Green <marcelo.green@yale.edu>
"""

import requests
import pandas as pd
import time
from pathlib import Path
from typing import Dict, List, Optional
import json

BASE_URL = "https://cde.ucr.cjis.gov/LATEST"

# RTCC city ORIs
# City PD ORIs (from CDE agency listings — NOT county-level)
RTCC_ORIS = {
    "Chicago": "ILCPD0000",
    "St. Louis": "MOSPD0000",
    "Miami": "FL0130600",
    "New Orleans": "LANPD0000",
    "Albuquerque": "NM0010100",
    "Fresno": "CA0100500",
    "Hartford": "CT0006400",
    "Newark": "NJNPD0000",
    # ── Expanded: 7 new cities (8 → 15) ──
    "Memphis": "TNMPD0000",
    "Baltimore": "MDBPD0000",
    "Detroit": "MI8234900",
    "Philadelphia": "PAPEP0000",
    "Houston": "TXHPD0000",
    "Dallas": "TXDPD0000",
    "Denver": "CODPD0000",
}


def get_shr_agency(ori: str, from_date: str = "01-2010", to_date: str = "12-2025",
                    data_type: str = "counts") -> Optional[Dict]:
    """
    Fetch SHR (Supplementary Homicide Report) data for an agency.

    Args:
        ori: 9-character ORI code (e.g., "CT0006400")
        from_date: Start date in MM-YYYY format
        to_date: End date in MM-YYYY format
        data_type: Only "counts" is supported

    Returns:
        Dict with monthly offense counts keyed by MM-YYYY
    """
    url = f"{BASE_URL}/shr/agency/{ori}"
    params = {"from": from_date, "to": to_date, "type": data_type}

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  Error fetching SHR for {ori}: {e}")
        return None


def get_shr_state(state_abbr: str, from_date: str = "01-2010", to_date: str = "12-2025",
                  data_type: str = "counts") -> Optional[Dict]:
    """Fetch SHR data aggregated at state level."""
    url = f"{BASE_URL}/shr/state/{state_abbr}"
    params = {"from": from_date, "to": to_date, "type": data_type}

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  Error fetching SHR for state {state_abbr}: {e}")
        return None


def get_agency_list(state_abbr: str) -> Optional[List[Dict]]:
    """Fetch all agencies for a state."""
    url = f"{BASE_URL}/agency/byStateAbbr/{state_abbr}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Flatten county-grouped structure
        agencies = []
        for county, agency_list in data.items():
            agencies.extend(agency_list)
        return agencies
    except Exception as e:
        print(f"  Error fetching agencies for {state_abbr}: {e}")
        return None


def get_max_data_date() -> Dict:
    """Get the maximum data date available in CDE."""
    url = f"{BASE_URL}/lookup/cde_properties"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        props = resp.json()
        result = {}
        for prop in props:
            if prop["name"] == "max_data_date":
                result[prop["project"]] = prop["value"]
        return result
    except Exception as e:
        print(f"  Error fetching CDE properties: {e}")
        return {}


def parse_monthly_to_annual(data: Dict, ori: str) -> pd.DataFrame:
    """
    Parse monthly SHR counts into annual aggregation.

    Returns DataFrame with columns: ori, year, homicides
    """
    records = []

    if not data or "actuals" not in data or data["actuals"] is None:
        return pd.DataFrame(records, columns=["ori", "year", "homicides"])

    for series_name, monthly_data in data["actuals"].items():
        if monthly_data is None:
            continue
        for month_year, count in monthly_data.items():
            # Parse "MM-YYYY" format
            parts = month_year.split("-")
            if len(parts) == 2:
                month = int(parts[0])
                year = int(parts[1])
                records.append({
                    "ori": ori,
                    "year": year,
                    "month": month,
                    "homicides": count,
                })

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame(columns=["ori", "year", "homicides"])

    # Aggregate to annual
    annual = df.groupby(["ori", "year"])["homicides"].sum().reset_index()
    return annual


def fetch_all_rtcc_cities(output_dir: str = "results/study1_rtcc/fbi_cde") -> pd.DataFrame:
    """
    Fetch SHR homicide data for all 8 RTCC cities from FBI CDE.

    Returns combined DataFrame with annual homicide counts.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Check data currency
    max_dates = get_max_data_date()
    print(f"CDE data currency: {max_dates}")

    all_annual = []

    for city, ori in RTCC_ORIS.items():
        print(f"\nFetching {city} ({ori})...")
        data = get_shr_agency(ori, from_date="01-2007", to_date="12-2025")

        if data and "actuals" in data:
            annual = parse_monthly_to_annual(data, ori)
            annual["city"] = city
            all_annual.append(annual)

            # Save raw response
            with open(output_path / f"shr_raw_{city.lower().replace(' ', '_').replace('.', '')}.json", "w") as f:
                json.dump(data, f, indent=2)

            print(f"  Got {len(annual)} years of data ({annual['year'].min()}-{annual['year'].max()})")
            print(f"  Total homicides: {annual['homicides'].sum()}")
        else:
            print(f"  No data returned for {city}")

        time.sleep(0.5)  # Rate limiting

    if not all_annual:
        print("\nNo data retrieved from FBI CDE")
        return pd.DataFrame()

    # Combine all cities
    df_combined = pd.concat(all_annual, ignore_index=True)
    df_combined.to_csv(output_path / "annual_homicides_fbi_cde.csv", index=False)

    # Print summary
    print(f"\n{'='*60}")
    print("FBI CDE SHR DATA SUMMARY")
    print(f"{'='*60}")
    for city in RTCC_ORIS:
        city_data = df_combined[df_combined["city"] == city]
        if not city_data.empty:
            print(f"{city}: {len(city_data)} years, "
                  f"{city_data['year'].min()}-{city_data['year'].max()}, "
                  f"total {city_data['homicides'].sum()} homicides")

    return df_combined


if __name__ == "__main__":
    df = fetch_all_rtcc_cities()
