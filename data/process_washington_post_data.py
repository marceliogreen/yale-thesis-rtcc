#!/usr/bin/env python3
"""
Process Washington Post homicide dataset for RTCC cities.
Extract annual homicide counts and clearance rates.
"""

import pandas as pd
from pathlib import Path

# RTCC cities configuration
RTCC_CITIES = {
    "Hartford": {"state": "CT", "rtcc_year": 2016, "population": 121000},
    "Miami": {"state": "FL", "rtcc_year": 2016, "population": 467000},
    "St. Louis": {"state": "MO", "rtcc_year": 2015, "population": 293000},
    "Newark": {"state": "NJ", "rtcc_year": 2018, "population": 277000},
    "New Orleans": {"state": "LA", "rtcc_year": 2017, "population": 376000},
    "Albuquerque": {"state": "NM", "rtcc_year": 2020, "population": 564000},
    "Fresno": {"state": "CA", "rtcc_year": 2018, "population": 545000},
    "Chicago": {"state": "IL", "rtcc_year": 2017, "population": 2694000},
}

def load_washington_post_data(filepath):
    """Load Washington Post homicide dataset."""
    df = pd.read_csv(filepath, encoding='utf-8', encoding_errors='replace')
    df['reported_date'] = pd.to_datetime(df['reported_date'], format='%Y%m%d', errors='coerce')
    df['year'] = df['reported_date'].dt.year
    return df

def extract_city_data(df, city, state):
    """Extract data for a specific city."""
    city_df = df[(df['city'] == city) & (df['state'] == state)].copy()
    return city_df

def compute_annual_stats(city_df, city_name, state, rtcc_year):
    """Compute annual homicide counts and clearance rates."""
    years = range(2007, 2024)  # Washington Post data range
    records = []

    for year in years:
        year_df = city_df[city_df['year'] == year]

        total = len(year_df)
        closed_by_arrest = len(year_df[year_df['disposition'] == 'Closed by arrest'])
        closed_without_arrest = len(year_df[year_df['disposition'] == 'Closed without arrest'])
        open_no_arrest = len(year_df[year_df['disposition'] == 'Open/No arrest'])

        # Clearance rate: Closed by arrest / total
        clearance_rate = (closed_by_arrest / total) if total > 0 else None

        post_rtcc = 1 if year >= rtcc_year else 0
        years_since_rtcc = year - rtcc_year if post_rtcc else 0

        records.append({
            'city': city_name,
            'state': state,
            'year': year,
            'homicide_count': total,
            'cleared_by_arrest': closed_by_arrest,
            'closed_without_arrest': closed_without_arrest,
            'open_no_arrest': open_no_arrest,
            'clearance_rate': clearance_rate,
            'rtcc_year': rtcc_year,
            'post_rtcc': post_rtcc,
            'years_since_rtcc': years_since_rtcc,
        })

    return pd.DataFrame(records)

def main():
    # Paths
    data_dir = Path(__file__).parent
    input_file = data_dir / "washington_post_homicides.csv"
    output_file = data_dir / "rtcc_homicide_washington_post.csv"

    print("Loading Washington Post homicide data...")
    df = load_washington_post_data(input_file)
    print(f"Total records: {len(df)}")
    print(f"Date range: {df['year'].min()} - {df['year'].max()}")

    # Process each RTCC city
    all_cities = []

    for city, config in RTCC_CITIES.items():
        state = config['state']
        rtcc_year = config['rtcc_year']

        print(f"\nProcessing {city}, {state}...")
        city_df = extract_city_data(df, city, state)
        print(f"  Total homicides: {len(city_df)}")

        city_stats = compute_annual_stats(city_df, city, state, rtcc_year)
        all_cities.append(city_stats)

    # Combine all cities
    result_df = pd.concat(all_cities, ignore_index=True)

    # Filter to study period 2010-2023
    result_df = result_df[result_df['year'].between(2010, 2023)].copy()

    # Save results
    result_df.to_csv(output_file, index=False)
    print(f"\nSaved results to: {output_file}")

    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY BY CITY (2010-2023)")
    print("="*60)

    for city in RTCC_CITIES.keys():
        city_data = result_df[result_df['city'] == city]
        total_homicides = city_data['homicide_count'].sum()
        avg_clearance = city_data['clearance_rate'].mean()
        rtcc_year = city_data['rtcc_year'].iloc[0]

        print(f"\n{city} (RTCC: {rtcc_year})")
        print(f"  Total homicides (2010-2023): {total_homicides}")
        print(f"  Avg clearance rate: {avg_clearance:.1%}")

        # Pre vs post RTCC
        pre_rtcc = city_data[city_data['post_rtcc'] == 0]
        post_rtcc = city_data[city_data['post_rtcc'] == 1]

        if len(pre_rtcc) > 0 and len(post_rtcc) > 0:
            pre_clearance = pre_rtcc['cleared_by_arrest'].sum() / pre_rtcc['homicide_count'].sum()
            post_clearance = post_rtcc['cleared_by_arrest'].sum() / post_rtcc['homicide_count'].sum()

            print(f"  Pre-RTCC clearance: {pre_clearance:.1%}")
            print(f"  Post-RTCC clearance: {post_clearance:.1%}")
            print(f"  Change: {(post_clearance - pre_clearance):.1%}")

    print("\n" + "="*60)
    print("DATA COVERAGE")
    print("="*60)
    print(result_df.groupby('city')['year'].count())

    return result_df

if __name__ == "__main__":
    main()
