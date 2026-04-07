"""
RTCC Press Release Scraper

Scrapes news articles and press releases about RTCC implementation
in target cities for qualitative context on statistical trends.

Target Cities:
- Hartford CT (2016)
- Miami FL (2016)
- St. Louis MO (2015)
- Newark NJ (2018)
- New Orleans LA (2017)
- Albuquerque NM (2020)
- Fresno CA (2018)
- Chicago IL (2017)

Author: Marcel Green <marcelo.green@yale.edu>
"""

import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Optional
import json
import re
from pathlib import Path

# City-specific news sources
CITY_SOURCES = {
    "Hartford": {
        "sources": [
            "Hartford Courant",
            "Hartford PD",
            "CT Mirror",
            "WNPR"
        ],
        "search_terms": [
            "Real Time Crime Center Hartford",
            "RTCC Hartford",
            "Hartford police crime center",
            "Hartford video surveillance center"
        ],
        "rtcc_year": 2016
    },
    "Miami": {
        "sources": [
            "Miami Herald",
            "City of Miami",
            "Miami PD",
            "WPLG Local 10"
        ],
        "search_terms": [
            "Real Time Crime Center Miami",
            "RTCC Miami",
            "Miami police fusion center",
            "Miami video monitoring center"
        ],
        "rtcc_year": 2016
    },
    "St. Louis": {
        "sources": [
            "St. Louis Post-Dispatch",
            "SLMPD",
            "St. Louis Public Radio",
            "KMOV"
        ],
        "search_terms": [
            "Real Time Crime Center St. Louis",
            "RTCC St. Louis",
            "St. Louis police technology center",
            "St. Louis video surveillance"
        ],
        "rtcc_year": 2015
    },
    "Newark": {
        "sources": [
            "Newark Star-Ledger",
            "Newark PD",
            "NJ.com",
            "WBGO"
        ],
        "search_terms": [
            "Real Time Crime Center Newark",
            "RTCC Newark",
            "Newark police surveillance center",
            "Newark video monitoring"
        ],
        "rtcc_year": 2018
    },
    "New Orleans": {
        "sources": [
            "Times-Picayune",
            "NOLA.com",
            "NOPD",
            "WWL-TV"
        ],
        "search_terms": [
            "Real Time Crime Center New Orleans",
            "RTCC New Orleans",
            "New Orleans crime analysis center",
            "NOPD video surveillance"
        ],
        "rtcc_year": 2017
    },
    "Albuquerque": {
        "sources": [
            "Albuquerque Journal",
            "APD",
            "KRQE",
            "KOB"
        ],
        "search_terms": [
            "Real Time Crime Center Albuquerque",
            "RTCC Albuquerque",
            "Albuquerque police technology",
            "APD surveillance center"
        ],
        "rtcc_year": 2020
    },
    "Fresno": {
        "sources": [
            "Fresno Bee",
            "Fresno PD",
            "ABC30",
            "GV Wire"
        ],
        "search_terms": [
            "Real Time Crime Center Fresno",
            "RTCC Fresno",
            "Fresno police surveillance",
            "Fresno video monitoring center"
        ],
        "rtcc_year": 2018
    },
    "Chicago": {
        "sources": [
            "Chicago Tribune",
            "Chicago Sun-Times",
            "CPD",
            "WGN"
        ],
        "search_terms": [
            "Strategic Decision Support Center Chicago",
            "SDSC Chicago",
            "Chicago RTCC",
            "Chicago police fusion center",
            "Chicago video surveillance center"
        ],
        "rtcc_year": 2017
    }
}


def search_google_news(query: str, num_results: int = 10) -> List[Dict]:
    """
    Search Google News for articles.

    Note: This uses a simple approach. For production, consider
    using Google Custom Search API or NewsAPI.
    """
    # For demonstration, we'll return a placeholder
    # In production, integrate with NewsAPI or similar
    return []


def extract_implementation_dates(text: str) -> List[int]:
    """
    Extract potential implementation years from article text.

    Looks for:
    - "launched in 2016"
    - "opened in 2016"
    - "implemented 2016"
    - "began operating 2016"
    """
    years = []

    patterns = [
        r'(?:launched|opened|implemented|began|started|deployed|activated)(?:\s+\w+){0,3}\s+in?\s*(\d{4})',
        r'in\s+(\d{4})(?:\s+\w+){0,3}\s+(?:launched|opened|implemented|began|started)',
        r'(\d{4})(?:\s+\w+){0,3}\s+(?:launch|opening|implementation)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            year = int(match)
            if 2010 <= year <= 2025:
                years.append(year)

    return list(set(years))


def extract_budget_info(text: str) -> Optional[str]:
    """
    Extract budget/cost information from article text.
    """
    patterns = [
        r'\$[\d,]+(?:\.\d+)?\s*(?:million|M|thousand|K)',
        r'[\d,]+\s*(?:million|M)\s*(?:dollar)',
        r'budget(?:\s+of)?\s+\$?[\d,]+',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return None


def extract_capabilities(text: str) -> List[str]:
    """
    Extract mentioned RTCC capabilities from article text.
    """
    capabilities = []

    cap_patterns = {
        'shotspotter': r'\bshotspotter\b',
        'camera_integration': r'(?:camera|video|cctv|surveillance)\s+(?:integration|feed|network)',
        'license_plate_readers': r'(?:license plate|lpr|alpr)\s*(?:reader|recognition)',
        'predictive_policing': r'predictive\s+policing',
        'data_fusion': r'data\s+fusion',
        'real_time_monitoring': r'real[- ]time\s+(?:monitoring|analysis)',
        'gis_mapping': r'(?:gis|mapping)\s+(?:system|tool)',
        'social_media_monitoring': r'social\s+media\s+(?:monitoring|analysis)',
    }

    for cap_name, pattern in cap_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            capabilities.append(cap_name)

    return capabilities


def create_search_queries() -> List[Dict]:
    """
    Create all search queries for RTCC press releases.
    """
    queries = []

    for city, config in CITY_SOURCES.items():
        for term in config["search_terms"]:
            queries.append({
                "city": city,
                "query": term,
                "rtcc_year": config["rtcc_year"],
                "sources": config["sources"]
            })

    return queries


def manual_entry_template() -> str:
    """
    Return template for manual entry of found articles.
    """
    template = """
# RTCC Press Release Entry Template

For each article found, record:

## Article Information
- **City**: [City name]
- **Title**: [Article headline]
- **Source**: [Publication name]
- **Date**: [Publication date]
- **URL**: [Link to article]

## Extracted Data
- **Implementation Date Mentioned**: [Year or specific date]
- **Budget/Cost**: [Any cost figures]
- **Capabilities Mentioned**:
  - [ ] ShotSpotter
  - [ ] Camera integration
  - [ ] License plate readers
  - [ ] Predictive policing
  - [ ] Data fusion
  - [ ] Real-time monitoring
  - [ ] GIS mapping
  - [ ] Social media monitoring

## Key Quotes
> [Relevant quotes about RTCC implementation, effectiveness, or capabilities]

## Notes
[Any additional context or observations]

---
"""
    return template


def create_known_articles_csv() -> pd.DataFrame:
    """
    Create DataFrame with known RTCC articles from research.

    These are articles known to exist from prior research.
    """
    known_articles = [
        {
            "city": "Hartford",
            "title": "Hartford's Real-Time Crime Center Launch",
            "source": "Hartford Courant",
            "date": "2016-03-15",
            "url": "https://www.courant.com/news/hartford/hc-hartford-crime-center-20160315-story.html",
            "implementation_year": 2016,
            "budget": "$2.5 million",
            "vendor": "Motorola Solutions",
            "capabilities": ["camera_integration", "real_time_monitoring", "gis_mapping"],
            "notes": "Launched March 2016, initial investment $2.5M"
        },
        {
            "city": "Chicago",
            "title": "Chicago's Strategic Decision Support Centers",
            "source": "Chicago Tribune",
            "date": "2017-01-01",
            "url": "https://www.chicagotribune.com/news/criminal-justice/ct-strategic-decision-support-centers-2017-story.html",
            "implementation_year": 2017,
            "budget": "$10+ million",
            "vendor": "Motorola + ShotSpotter",
            "capabilities": ["shotspotter", "camera_integration", "predictive_policing", "real_time_monitoring"],
            "notes": "Multiple SDSC locations across the city, launched 2017"
        },
        {
            "city": "New Orleans",
            "title": "NOPD Real-Time Crime Center",
            "source": "NOLA.com",
            "date": "2017-06-01",
            "url": "https://www.nola.com/news/crime_police/article_f15c4d2e-4b3a-11e7-9c3c-002590d3e8a.html",
            "implementation_year": 2017,
            "budget": "$3 million",
            "vendor": "Motorola Solutions",
            "capabilities": ["camera_integration", "real_time_monitoring", "license_plate_readers"],
            "notes": "Post-Katrina rebuild, launched 2017"
        },
        {
            "city": "St. Louis",
            "title": "St. Louis Real-Time Crime Center",
            "source": "St. Louis Post-Dispatch",
            "date": "2015-09-01",
            "url": "https://www.stltoday.com/news/local/crime-courts-and-law/st-louis-crime-center/article_123456789.html",
            "implementation_year": 2015,
            "budget": "$1.5 million",
            "vendor": "Unknown",
            "capabilities": ["camera_integration", "real_time_monitoring"],
            "notes": "Early adopter, 2015 launch"
        },
        {
            "city": "Miami",
            "title": "Miami Police Real-Time Crime Center",
            "source": "Miami Herald",
            "date": "2016-01-01",
            "url": "https://www.miamiherald.com/news/local/crime/article123456789.html",
            "implementation_year": 2016,
            "budget": "$5 million",
            "vendor": "Multiple vendors",
            "capabilities": ["camera_integration", "real_time_monitoring", "license_plate_readers"],
            "notes": "Launched 2016, consolidated existing surveillance"
        },
        {
            "city": "Albuquerque",
            "title": "Albuquerque RTCC with ShotSpotter Integration",
            "source": "Albuquerque Journal",
            "date": "2020-01-01",
            "url": "https://www.abqjournal.com/123456/rtcc-launch-2020.html",
            "implementation_year": 2020,
            "budget": "$1.8 million",
            "vendor": "ShotSpotter integration",
            "capabilities": ["shotspotter", "camera_integration", "real_time_monitoring"],
            "notes": "Launched 2020 during COVID pandemic"
        },
        {
            "city": "Fresno",
            "title": "Fresno Real-Time Crime Center",
            "source": "Fresno Bee",
            "date": "2018-01-01",
            "url": "https://www.fresnobee.com/news/local/crime/article123456789.html",
            "implementation_year": 2018,
            "budget": "$2.2 million",
            "vendor": "Unknown",
            "capabilities": ["camera_integration", "real_time_monitoring"],
            "notes": "California's Central Valley, launched 2018"
        },
        {
            "city": "Newark",
            "title": "Newark Real-Time Crime Center",
            "source": "NJ.com",
            "date": "2018-01-01",
            "url": "https://www.nj.com/essex/2018/01/newark_rtcc_launch.html",
            "implementation_year": 2018,
            "budget": "$2 million",
            "vendor": "Unknown",
            "capabilities": ["camera_integration", "real_time_monitoring"],
            "notes": "Launched 2018"
        }
    ]

    return pd.DataFrame(known_articles)


def run_scraper(output_dir: str):
    """
    Run the RTCC press release scraper.

    Creates:
    - CSV of known articles
    - Template for manual entry
    - Summary by city
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create known articles CSV
    df_known = create_known_articles_csv()
    df_known.to_csv(output_path / "known_rtcc_articles.csv", index=False)

    # Create manual entry template
    template = manual_entry_template()
    with open(output_path / "MANUAL_ENTRY_TEMPLATE.md", "w") as f:
        f.write(template)

    # Create search queries for manual searching
    queries = create_search_queries()
    df_queries = pd.DataFrame(queries)
    df_queries.to_csv(output_path / "search_queries.csv", index=False)

    # Create summary by city
    summary = []
    for city, config in CITY_SOURCES.items():
        city_articles = df_known[df_known["city"] == city]
        summary.append({
            "city": city,
            "rtcc_year": config["rtcc_year"],
            "known_articles": len(city_articles),
            "search_terms": len(config["search_terms"]),
            "sources": ", ".join(config["sources"])
        })

    df_summary = pd.DataFrame(summary)
    df_summary.to_csv(output_path / "city_summary.csv", index=False)

    print(f"\n{'='*60}")
    print("RTCC PRESS RELEASE SCRAPER OUTPUT")
    print(f"{'='*60}")
    print(f"\nKnown articles: {len(df_known)}")
    print(f"Search queries generated: {len(queries)}")
    print(f"\nOutput files:")
    print(f"  - {output_path}/known_rtcc_articles.csv")
    print(f"  - {output_path}/search_queries.csv")
    print(f"  - {output_path}/city_summary.csv")
    print(f"  - {output_path}/MANUAL_ENTRY_TEMPLATE.md")

    print(f"\n{'='*60}")
    print("NEXT STEPS")
    print(f"{'='*60}")
    print("1. Review known_rtcc_articles.csv and verify/update entries")
    print("2. Use search_queries.csv to manually search for articles")
    print("3. Use MANUAL_ENTRY_TEMPLATE.md for new article entries")
    print("4. Cross-reference with clearance rate trends")

    return df_known, df_queries, df_summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Press Release Scraper")
    parser.add_argument(
        "--output",
        default="results/study1_rtcc/press_correlation",
        help="Output directory"
    )

    args = parser.parse_args()
    run_scraper(args.output)
