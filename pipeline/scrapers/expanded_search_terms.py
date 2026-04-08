"""
Expanded RTCC Search Query Generator

Generates ~25-35 queries per city using looser language across 6 layers:
  1. Facility variants (crime analysis center, crime camera, etc.)
  2. Alternative terms (fusion center, smart policing, etc.)
  3. Vendor + city combinations (ShotSpotter, Motorola, Flock, etc.)
  4. Funding/grant searches (DOJ COPS, city council)
  5. City name variants (NOLA, ABQ, STL, etc.)
  6. Event-type queries (launch, opening, expansion)

Output: expanded_search_queries.csv with ~280 queries
"""

import pandas as pd
from pathlib import Path

# RTCC city configuration
RTCC_CITIES = {
    "Hartford": {
        "state": "CT", "rtcc_year": 2016, "vendor": "Motorola Solutions",
        "variants": ["Hartford", "Hartford CT", "HFD"],
        "sources": ["Hartford Courant", "Hartford PD", "CT Mirror", "WNPR",
                     "Hartford.gov", "CT Post"],
    },
    "Miami": {
        "state": "FL", "rtcc_year": 2016, "vendor": "Multiple vendors",
        "variants": ["Miami", "Miami FL", "MIA", "Miami-Dade"],
        "sources": ["Miami Herald", "City of Miami", "Miami PD", "WPLG Local 10",
                     "Miami New Times", "Miami.gov"],
    },
    "St. Louis": {
        "state": "MO", "rtcc_year": 2015, "vendor": "Unknown",
        "variants": ["St. Louis", "Saint Louis", "STL", "St. Louis MO"],
        "sources": ["St. Louis Post-Dispatch", "SLMPD", "St. Louis Public Radio",
                     "KMOV", "Riverfront Times", "St. Louis Today"],
    },
    "Newark": {
        "state": "NJ", "rtcc_year": 2018, "vendor": "Unknown",
        "variants": ["Newark", "Newark NJ", "Brick City"],
        "sources": ["Newark Star-Ledger", "Newark PD", "NJ.com", "WBGO",
                     "Essex County", "Patch Newark"],
    },
    "New Orleans": {
        "state": "LA", "rtcc_year": 2017, "vendor": "Motorola Solutions",
        "variants": ["New Orleans", "NOLA", "New Orleans LA", "NOPD"],
        "sources": ["Times-Picayune", "NOLA.com", "NOPD", "WWL-TV",
                     "Gambit", "The Lens NOLA"],
    },
    "Albuquerque": {
        "state": "NM", "rtcc_year": 2020, "vendor": "ShotSpotter integration",
        "variants": ["Albuquerque", "ABQ", "Albuquerque NM", "Duke City"],
        "sources": ["Albuquerque Journal", "APD", "KRQE", "KOB",
                     "Albuquerque Journal Online", "Daily Lobo"],
    },
    "Fresno": {
        "state": "CA", "rtcc_year": 2018, "vendor": "Unknown",
        "variants": ["Fresno", "Fresno CA", "Fresno County"],
        "sources": ["Fresno Bee", "Fresno PD", "ABC30", "GV Wire",
                     "Fresno CityView", "KVPR"],
    },
    "Chicago": {
        "state": "IL", "rtcc_year": 2017, "vendor": "Motorola + ShotSpotter",
        "variants": ["Chicago", "Chicago IL", "CHI", "CPD"],
        "sources": ["Chicago Tribune", "Chicago Sun-Times", "CPD", "WGN",
                     "Block Club Chicago", "Chicago Magazine"],
    },
}

# Vendor names to search (including rebranded names)
VENDORS = [
    "ShotSpotter", "SoundThinking",  # SoundThinking is ShotSpotter rebranded
    "Motorola Solutions", "Motorola",
    "Flock Safety", "Flock",
    "Genetec", "Axon", "Palantir",
    "Clearview AI", "Vigilant Solutions",
    "IBM", "Microsoft public safety",
]

# --- Query Templates ---

FACILITY_VARIANTS = [
    "{city} crime analysis center",
    "{city} crime camera",
    "{city} surveillance center",
    "{city} police data center",
    "{city} police operations center",
    "{city} public safety technology",
    "{city} police intelligence center",
    "{city} video monitoring center",
    "{city} camera network police",
    "{city} crime monitoring system",
]

ALTERNATIVE_TERMS = [
    "fusion center {city}",
    "smart policing {city}",
    "real-time intelligence {city}",
    "crime monitoring {city}",
    "{city} police technology upgrade",
    "{city} police technology center",
    "{city} predictive policing",
    "{city} data-driven policing",
]

EVENT_QUERIES = [
    "{city} crime center launch",
    "{city} crime center opening",
    "{city} crime center expansion",
    "{city} technology upgrade police",
    "{city} crime center announcement",
    "{city} surveillance launch",
    "{city} police technology grant",
    "{city} crime center ribbon",
]

GRANT_QUERIES = [
    "DOJ COPS grant {city}",
    "justice department grant {city} police",
    "COPS technology grant {city}",
    "public safety grant {city}",
    "city council {city} crime center",
    "{city} police budget technology",
    "{city} homeland security grant police",
    "{city} Bureau Justice Assistance grant",
]

# Chicago-specific SDSC queries (Chicago uses different terminology)
CHICAGO_SPECIFIC = [
    "Strategic Decision Support Center Chicago",
    "SDSC Chicago",
    "Strategic Decision Support Center CPD",
    "Chicago SDSC rollout",
    "Chicago police district technology center",
    "Chicago POD cameras",
    "Chicago police observation device",
]


def generate_vendor_queries(city: str, vendor: str) -> list:
    """Generate vendor + city queries."""
    return [
        f"{vendor} {city}",
        f"{vendor} {city} police",
    ]


def generate_queries() -> pd.DataFrame:
    """Generate the full expanded query set."""
    rows = []

    for city, config in RTCC_CITIES.items():
        rtcc_year = config["rtcc_year"]
        variants = config["variants"]
        vendor = config["vendor"]
        sources = config["sources"]

        # Primary city name for most queries
        primary = variants[0]

        # --- Layer 1: Facility variants ---
        for template in FACILITY_VARIANTS:
            for v in variants[:2]:  # primary + state variant
                rows.append({
                    "city": city,
                    "query": template.format(city=v),
                    "rtcc_year": rtcc_year,
                    "date_start": rtcc_year - 3,
                    "date_end": rtcc_year + 3,
                    "query_category": "facility_variant",
                    "sources": "; ".join(sources),
                })

        # --- Layer 2: Alternative terms ---
        for template in ALTERNATIVE_TERMS:
            rows.append({
                "city": city,
                "query": template.format(city=primary),
                "rtcc_year": rtcc_year,
                "date_start": rtcc_year - 3,
                "date_end": rtcc_year + 3,
                "query_category": "alternative_term",
                "sources": "; ".join(sources),
            })

        # --- Layer 3: Vendor + city ---
        for v in VENDORS:
            for q in generate_vendor_queries(primary, v):
                rows.append({
                    "city": city,
                    "query": q,
                    "rtcc_year": rtcc_year,
                    "date_start": rtcc_year - 3,
                    "date_end": rtcc_year + 3,
                    "query_category": "vendor",
                    "sources": "; ".join(sources),
                })

        # --- Layer 4: Grant/funding ---
        for template in GRANT_QUERIES:
            rows.append({
                "city": city,
                "query": template.format(city=primary),
                "rtcc_year": rtcc_year,
                "date_start": rtcc_year - 3,
                "date_end": rtcc_year + 3,
                "query_category": "grant",
                "sources": "; ".join(sources),
            })

        # --- Layer 5: City name variants ---
        if len(variants) > 2:
            for v in variants[2:]:  # skip primary + state
                rows.append({
                    "city": city,
                    "query": f"{v} crime center",
                    "rtcc_year": rtcc_year,
                    "date_start": rtcc_year - 3,
                    "date_end": rtcc_year + 3,
                    "query_category": "city_variant",
                    "sources": "; ".join(sources),
                })
                rows.append({
                    "city": city,
                    "query": f"{v} real-time crime",
                    "rtcc_year": rtcc_year,
                    "date_start": rtcc_year - 3,
                    "date_end": rtcc_year + 3,
                    "query_category": "city_variant",
                    "sources": "; ".join(sources),
                })

        # --- Layer 6: Event queries ---
        for template in EVENT_QUERIES:
            rows.append({
                "city": city,
                "query": template.format(city=primary),
                "rtcc_year": rtcc_year,
                "date_start": rtcc_year - 3,
                "date_end": rtcc_year + 3,
                "query_category": "event",
                "sources": "; ".join(sources),
            })

        # --- Chicago-specific SDSC queries ---
        if city == "Chicago":
            for q in CHICAGO_SPECIFIC:
                rows.append({
                    "city": city,
                    "query": q,
                    "rtcc_year": rtcc_year,
                    "date_start": rtcc_year - 3,
                    "date_end": rtcc_year + 3,
                    "query_category": "facility_variant",
                    "sources": "; ".join(sources),
                })

    df = pd.DataFrame(rows)

    # Deduplicate queries
    df = df.drop_duplicates(subset=["query"]).reset_index(drop=True)

    # Also deduplicate against existing queries
    existing_path = Path(__file__).parent.parent.parent.parent.parent / "results" / "study1_rtcc" / "press_correlation" / "search_queries.csv"
    if existing_path.exists():
        existing = pd.read_csv(existing_path)
        existing_queries = set(existing["query"].values)
        df = df[~df["query"].isin(existing_queries)].reset_index(drop=True)

    return df


if __name__ == "__main__":
    df = generate_queries()

    output_dir = Path(__file__).parent.parent.parent.parent.parent / "results" / "study1_rtcc" / "press_correlation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "expanded_search_queries.csv"

    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} expanded queries")
    print(f"\nBy city:")
    print(df.groupby("city").size().to_string())
    print(f"\nBy category:")
    print(df.groupby("query_category").size().to_string())
    print(f"\nSaved to {output_path}")
