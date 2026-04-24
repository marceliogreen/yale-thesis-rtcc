"""
RTCC Date Verification via Web Scraping

Searches for verified RTCC implementation dates for each target city
using Exa (academic search), Tavily (web search), and Firecrawl (page scraping).
Apify available for batch crawling if needed.

API keys are loaded from .env file. Set up before running:
  EXA_API_KEY=...
  TAVILY_API_KEY=...
  FIRECRAWL_API_KEY=...
  APIFY_API_KEY=...  (optional)

Output: thesis/data/rtcc_dates_verified.csv

Author: Marcel Green <marcelo.green@yale.edu>
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
OUTPUT_CSV = BASE_DIR / "thesis" / "data" / "rtcc_dates_verified.csv"

# ── API Configuration ──────────────────────────────────────────

EXA_API_KEY = os.getenv("EXA_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
APIFY_API_KEY = os.getenv("APIFY_API_KEY", "")

EXA_BASE = "https://api.exa.ai"
TAVILY_BASE = "https://api.tavily.com"
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


# ── Cities to Verify ───────────────────────────────────────────

CITIES = {
    "Hartford": {
        "state": "CT",
        "current_year": 2016,
        "search_queries": [
            "Hartford CT Real Time Crime Center launch",
            "Hartford Connecticut RTCC GVPA Gun Violence Prevention",
            "Hartford Police strategic decision support center",
        ],
    },
    "Miami": {
        "state": "FL",
        "current_year": 2016,
        "search_queries": [
            "Miami Real Time Crime Center launch date",
            "Miami RTCC Motorola contract",
            "Miami-Dade fusion center real time crime",
        ],
    },
    "St. Louis": {
        "state": "MO",
        "current_year": 2015,
        "search_queries": [
            "St. Louis Real Time Crime Center opening",
            "St. Louis Metro Police RTCC launch",
            "St. Louis strategic decision support center SDSC",
        ],
    },
    "New Orleans": {
        "state": "LA",
        "current_year": 2017,
        "search_queries": [
            "New Orleans Real Time Crime Center launch",
            "New Orleans NOPD RTCC",
            "New Orleans crime center technology partnership",
        ],
    },
    "Albuquerque": {
        "state": "NM",
        "current_year": 2013,  # RTCC opened March 2013 (Police Magazine, StateTech Magazine)
        "search_queries": [
            "Albuquerque Real Time Crime Center launch",
            "Albuquerque APD RTCC Motorola",
            "Albuquerque crime analysis center",
        ],
    },
    "Fresno": {
        "state": "CA",
        "current_year": 2015,  # RTCC opened July 2015 (ABC30, Fresno Bee, Atlas of Surveillance)
        "search_queries": [
            "Fresno Real Time Crime Center launch",
            "Fresno Police RTCC technology",
            "Fresno crime center opening ceremony",
        ],
    },
    "Chicago": {
        "state": "IL",
        "current_year": 2017,
        "search_queries": [
            "Chicago Strategic Decision Support Center SDSC launch",
            "Chicago RTCC CPD technology center",
            "Chicago CPD real time crime center Motorola",
        ],
    },
    # ── Expanded: 7 new cities (8 → 15) ──
    "Memphis": {
        "state": "TN",
        "current_year": 2008,  # ✓ Memphis Flyer 4/16/2008, OJP/StateTech
        "search_queries": [
            "Memphis Real Time Crime Center launch",
            "Memphis MPD RTCC Motorola",
            "Memphis crime analysis center opening",
        ],
    },
    "Baltimore": {
        "state": "MD",
        "current_year": 2013,  # ⚠ Watch Center ~2013-2014 (cameras since 2005)
        "search_queries": [
            "Baltimore CitiWatch real time crime center launch",
            "Baltimore RTCC BPD technology",
            "Baltimore crime camera center opening",
        ],
    },
    "Detroit": {
        "state": "MI",
        "current_year": 2016,  # ✓ Project Green Light
        "search_queries": [
            "Detroit Project Green Light launch",
            "Detroit RTCC DPD technology center",
            "Detroit real time crime center opening",
        ],
    },
    "Philadelphia": {
        "state": "PA",
        "current_year": 2012,  # ✓ Technical.ly, Inquirer, Atlas of Surveillance
        "search_queries": [
            "Philadelphia Real Time Crime Center launch",
            "Philadelphia PPD RTCC opening",
            "Philadelphia police technology center",
        ],
    },
    "Houston": {
        "state": "TX",
        "current_year": 2008,  # ✓ OJP — 4th US agency with RTCC
        "search_queries": [
            "Houston Real Time Crime Center launch",
            "Houston HPD RTCC opening",
            "Houston police technology center",
        ],
    },
    "Dallas": {
        "state": "TX",
        "current_year": 2019,  # ✓ Atlas of Surveillance, Motorola 2019
        "search_queries": [
            "Dallas Real Time Crime Center launch",
            "Dallas DPD RTCC Fusion Center",
            "Dallas police technology center opening",
        ],
    },
    "Denver": {
        "state": "CO",
        "current_year": 2019,  # ✓ RTCIC opened August 2019 (HALO cameras since 2008)
        "search_queries": [
            "Denver Real Time Crime Center launch",
            "Denver HALO camera network RTCC",
            "Denver police technology center opening",
        ],
    },
}


@dataclass
class RTCCDateResult:
    """Container for verified RTCC dates for one city."""
    city: str
    state: str
    current_year: int  # Our current assumed implementation year
    announcement_date: Optional[str] = None
    operational_date: Optional[str] = None
    full_ops_date: Optional[str] = None
    verified_year: Optional[int] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_snippet: Optional[str] = None
    confidence: str = "unverified"  # high, medium, low, unverified
    notes: str = ""
    search_results: list = field(default_factory=list)
    verified_at: str = ""


# ── Exa Search ─────────────────────────────────────────────────

def exa_search(query: str, num_results: int = 5) -> list[dict]:
    """Search using Exa API (academic + news focused)."""
    if not EXA_API_KEY:
        logger.warning("EXA_API_KEY not set, skipping Exa search")
        return []

    headers = {
        "x-api-key": EXA_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "num_results": num_results,
        "type": "neural",
        "use_autoprompt": True,
        "contents": {
            "text": {"maxCharacters": 500},
        },
    }

    try:
        resp = requests.post(
            f"{EXA_BASE}/search",
            headers=headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "text": r.get("text", ""),
                "published_date": r.get("publishedDate", ""),
                "score": r.get("score", 0),
            })
        return results
    except Exception as e:
        logger.error(f"Exa search failed: {e}")
        return []


# ── Tavily Search ──────────────────────────────────────────────

def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """Search using Tavily API."""
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set, skipping Tavily search")
        return []

    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": True,
    }

    try:
        resp = requests.post(
            f"{TAVILY_BASE}/search",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "text": r.get("content", ""),
                "score": r.get("score", 0),
            })
        # Tavily also returns an "answer" field
        if data.get("answer"):
            results.insert(0, {
                "title": "Tavily AI Answer",
                "url": "",
                "text": data["answer"],
                "score": 1.0,
            })
        return results
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


# ── Firecrawl Scrape ──────────────────────────────────────────

def firecrawl_scrape(url: str) -> Optional[str]:
    """Scrape full text from a URL using Firecrawl."""
    if not FIRECRAWL_API_KEY:
        logger.warning("FIRECRAWL_API_KEY not set, skipping Firecrawl scrape")
        return None

    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "formats": ["markdown"],
        "onlyMainContent": True,
    }

    try:
        resp = requests.post(
            f"{FIRECRAWL_BASE}/scrape",
            headers=headers,
            json=payload,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", {}).get("markdown", "")
    except Exception as e:
        logger.error(f"Firecrawl scrape failed for {url}: {e}")
        return None


# ── Date Extraction ────────────────────────────────────────────

def extract_dates_from_text(text: str, city: str) -> dict:
    """
    Extract potential RTCC dates from text using regex patterns.
    Returns dict with found dates and confidence.
    """
    dates = {
        "announcement_date": None,
        "operational_date": None,
        "full_ops_date": None,
        "confidence": "low",
    }

    # Date patterns
    date_patterns = [
        # "January 2016", "Feb. 2017", etc.
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}",
        # "2016", "2017" (4-digit years)
        r"\b(20[0-2]\d)\b",
        # "in 2016", "by 2017"
        r"(?:in|by|since|from|after)\s+(20[0-2]\d)",
    ]

    found_years = set()
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for m in matches:
            year_match = re.search(r"(20[0-2]\d)", m)
            if year_match:
                found_years.add(int(year_match.group(1)))

    # Contextual patterns for RTCC dates
    launch_patterns = [
        r"(?:launched|opened|began|started|went live|became operational|commissioned)\s+(?:in|on)?\s*({{DATE}})",
        r"(?:announced|approved|funded|granted)\s+(?:in|on)?\s*({{DATE}})",
        r"RTCC\s+(?:was|became)\s+(?:operational|active|live)\s+(?:in|on)?\s*({{DATE}})",
    ]

    if found_years:
        dates["operational_date"] = min(found_years)
        dates["confidence"] = "medium" if len(found_years) >= 2 else "low"

    return dates


def verify_city_dates(city: str, config: dict) -> RTCCDateResult:
    """Search and verify RTCC dates for a single city."""
    result = RTCCDateResult(
        city=city,
        state=config["state"],
        current_year=config["current_year"],
        verified_at=datetime.now().isoformat(),
    )

    all_results = []

    # Search via Exa
    for query in config["search_queries"]:
        logger.info(f"  Exa: '{query}'")
        results = exa_search(query)
        all_results.extend(results)
        time.sleep(0.5)  # Rate limiting

    # Search via Tavily
    for query in config["search_queries"][:2]:  # Limit Tavily calls
        logger.info(f"  Tavily: '{query}'")
        results = tavily_search(query)
        all_results.extend(results)
        time.sleep(0.5)

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique_results.append(r)
    result.search_results = unique_results

    if not unique_results:
        result.notes = "No search results found"
        return result

    # Scrape top results for detailed date extraction
    for r in unique_results[:3]:
        if r["url"]:
            logger.info(f"  Scraping: {r['url'][:80]}")
            text = firecrawl_scrape(r["url"])
            if text:
                dates = extract_dates_from_text(text, city)
                if dates.get("operational_date"):
                    result.operational_date = str(dates["operational_date"])
                    result.source_url = r["url"]
                    result.source_title = r["title"]
                    result.source_snippet = r["text"][:300]
                    result.confidence = dates["confidence"]
                    break
            time.sleep(1)

    # Determine verified year
    if result.operational_date:
        year_match = re.search(r"(20[0-2]\d)", str(result.operational_date))
        if year_match:
            result.verified_year = int(year_match.group(1))

    # Compare with current assumption
    if result.verified_year:
        if result.verified_year == result.current_year:
            result.notes = f"Verified: matches assumed year {result.current_year}"
            result.confidence = "high"
        else:
            diff = result.verified_year - result.current_year
            result.notes = f"DISCREPANCY: verified={result.verified_year}, assumed={result.current_year} (diff={diff:+d})"
    else:
        result.notes = "Could not verify — no date found in search results"

    return result


def run_verification() -> pd.DataFrame:
    """Run RTCC date verification for all cities."""
    logger.info("=" * 60)
    logger.info("RTCC DATE VERIFICATION")
    logger.info("=" * 60)

    if not EXA_API_KEY and not TAVILY_API_KEY:
        logger.error("No API keys set. Export EXA_API_KEY and/or TAVILY_API_KEY before running.")
        logger.error("Example: export EXA_API_KEY=your-key-here")
        return pd.DataFrame()

    results = []
    for city, config in CITIES.items():
        logger.info(f"\nVerifying {city}...")
        result = verify_city_dates(city, config)
        results.append(asdict(result))

        # Summary
        logger.info(f"  Result: {result.verified_year or 'NOT FOUND'} (assumed: {result.current_year})")
        logger.info(f"  Confidence: {result.confidence}")
        logger.info(f"  Sources found: {len(result.search_results)}")

    # Save results
    df = pd.DataFrame(results)

    # Drop the search_results list column for CSV
    df_summary = df.drop(columns=["search_results"])
    df_summary.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"\nSaved to {OUTPUT_CSV}")

    # Also save full results as JSON
    json_path = OUTPUT_CSV.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Full results (with search results): {json_path}")

    return df


if __name__ == "__main__":
    run_verification()
