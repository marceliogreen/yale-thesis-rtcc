"""
RTCC Press Release Scraper — Expanded with Live Search

Scrapes news articles and press releases about RTCC implementation
in 8 target cities using expanded query taxonomy (593 queries).

Search methods:
1. Google News RSS feeds (no API key needed)
2. Vendor case study pages
3. DOJ COPS grant search
4. Bing News API (if key available)

Target Cities:
- Hartford CT (2016), Miami FL (2016), St. Louis MO (2015)
- Newark NJ (2018), New Orleans LA (2017), Albuquerque NM (2020)
- Fresno CA (2018), Chicago IL (2017)

Author: Marcel Green <marcelo.green@yale.edu>
"""

import pandas as pd
import requests
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus, urlencode
import json
import re
import time
import logging
from pathlib import Path
from xml.etree import ElementTree

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Vendor case study URLs
VENDOR_URLS = {
    "Motorola Solutions": "https://www.motorolasolutions.com/en_us/government-and-commercial-enterprise/solutions-by-initiative/safe-city.html",
    "ShotSpotter": "https://www.soundthinking.com/customers/",
    "Flock Safety": "https://www.flocksafety.com/customers",
    "Genetec": "https://www.genetec.com/about-us/customer-stories",
    "Axon": "https://www.axon.com/customers",
}

# City government URLs for council minutes
GOVERNMENT_URLS = {
    "Hartford": "https://hartford.gov",
    "Miami": "https://www.miamigov.com",
    "St. Louis": "https://www.stlouis-mo.gov",
    "Newark": "https://www.newarknj.gov",
    "New Orleans": "https://www.nola.gov",
    "Albuquerque": "https://www.cabq.gov",
    "Fresno": "https://www.fresno.gov",
    "Chicago": "https://www.chicago.gov",
}


# ---------------------------------------------------------------------------
# Search: Google News RSS
# ---------------------------------------------------------------------------

def search_google_news_rss(query: str, num_results: int = 10) -> List[Dict]:
    """
    Search Google News via RSS feed. No API key required.

    Returns list of dicts with: title, url, snippet, date, source
    """
    results = []
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 "
                          "Safari/537.36"
        }, timeout=15)
        resp.raise_for_status()

        root = ElementTree.fromstring(resp.content)
        items = root.findall(".//item")

        for item in items[:num_results]:
            title_el = item.find("title")
            link_el = item.find("link")
            pubdate_el = item.find("pubDate")
            source_el = item.find(".//{http://purl.org/dc/elements/1.1/}source")
            desc_el = item.find("description")

            result = {
                "title": title_el.text if title_el is not None else "",
                "url": link_el.text if link_el is not None else "",
                "date": pubdate_el.text if pubdate_el is not None else "",
                "source": source_el.text if source_el is not None else "",
                "snippet": _strip_html(desc_el.text) if desc_el is not None else "",
            }
            if result["title"] and result["url"]:
                results.append(result)

    except requests.RequestException as e:
        logger.debug(f"Google News RSS failed for '{query}': {e}")
    except ElementTree.ParseError as e:
        logger.debug(f"XML parse error for '{query}': {e}")

    return results


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text) if text else ""


# ---------------------------------------------------------------------------
# Search: Bing News API (optional, requires key)
# ---------------------------------------------------------------------------

def search_bing_news(query: str, api_key: str, num_results: int = 10) -> List[Dict]:
    """
    Search Bing News API. Requires BING_NEWS_API_KEY in .env.
    Free tier: 1000 calls/month.
    """
    url = "https://api.bing.microsoft.com/v7.0/news/search"
    headers = {"Ocp-Apim-Subscription-Key": api_key}
    params = {"q": query, "count": num_results, "mkt": "en-US", "freshness": "Month"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for article in data.get("value", []):
            results.append({
                "title": article.get("name", ""),
                "url": article.get("url", ""),
                "date": article.get("datePublished", ""),
                "source": article.get("provider", [{}])[0].get("name", ""),
                "snippet": article.get("description", ""),
            })
        return results

    except requests.RequestException as e:
        logger.debug(f"Bing News API failed for '{query}': {e}")
        return []


# ---------------------------------------------------------------------------
# Search: Vendor case studies
# ---------------------------------------------------------------------------

def search_vendor_pages(city: str) -> List[Dict]:
    """
    Fetch vendor case study pages and check for city mentions.
    Returns list of vendor-page matches.
    """
    results = []
    city_lower = city.lower()
    city_variants = _get_city_variants(city)

    for vendor, url in VENDOR_URLS.items():
        try:
            resp = requests.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36"
            }, timeout=15)
            if resp.status_code != 200:
                continue

            text = resp.text.lower()
            for variant in city_variants:
                if variant.lower() in text:
                    results.append({
                        "title": f"{vendor} case study mentioning {city}",
                        "url": url,
                        "date": "",
                        "source": vendor,
                        "snippet": f"Found '{variant}' on {vendor} page",
                        "source_type": "vendor",
                    })
                    break

        except requests.RequestException:
            continue

    return results


def _get_city_variants(city: str) -> List[str]:
    """Return search variants for a city name."""
    variants = {
        "Hartford": ["Hartford", "Connecticut"],
        "Miami": ["Miami", "Miami-Dade"],
        "St. Louis": ["St. Louis", "Saint Louis"],
        "Newark": ["Newark", "Essex County"],
        "New Orleans": ["New Orleans", "Orleans Parish", "NOLA"],
        "Albuquerque": ["Albuquerque", "Bernalillo"],
        "Fresno": ["Fresno"],
        "Chicago": ["Chicago", "Cook County"],
    }
    return variants.get(city, [city])


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def extract_implementation_dates(text: str) -> List[int]:
    """Extract potential implementation years from article text."""
    years = []
    patterns = [
        r'(?:launched|opened|implemented|began|started|deployed|activated|unveiled|rolled out)(?:\s+\w+){0,3}\s+in?\s*(\d{4})',
        r'in\s+(\d{4})(?:\s+\w+){0,3}\s+(?:launched|opened|implemented|began|started|unveiled)',
        r'(\d{4})(?:\s+\w+){0,3}\s+(?:launch|opening|implementation|deployment)',
        r'since\s+(\d{4})',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            y = int(m)
            if 2010 <= y <= 2026:
                years.append(y)
    return list(set(years))


def extract_budget_info(text: str) -> Optional[str]:
    """Extract budget/cost information from article text."""
    patterns = [
        r'\$[\d,]+(?:\.\d+)?\s*(?:million|M|thousand|K)',
        r'[\d,]+\s*(?:million|M)\s*(?:dollar)',
        r'budget(?:\s+of)?\s+\$?[\d,]+',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def extract_capabilities(text: str) -> List[str]:
    """Extract mentioned RTCC capabilities from article text."""
    cap_patterns = {
        'shotspotter': r'\bshotspotter\b|\bsoundthinking\b',
        'camera_integration': r'(?:camera|video|cctv|surveillance)\s+(?:integration|feed|network)',
        'license_plate_readers': r'(?:license plate|lpr|alpr)\s*(?:reader|recognition)',
        'predictive_policing': r'predictive\s+policing',
        'data_fusion': r'data\s+fusion',
        'real_time_monitoring': r'real[- ]time\s+(?:monitoring|analysis|crime)',
        'gis_mapping': r'(?:gis|mapping)\s+(?:system|tool)',
        'social_media_monitoring': r'social\s+media\s+(?:monitoring|analysis)',
        'drone': r'\bdrone\b|\buav\b|\bdfr\b',
        'gunshot_detection': r'gunshot\s+detection',
    }
    return [name for name, pat in cap_patterns.items() if re.search(pat, text, re.IGNORECASE)]


# ---------------------------------------------------------------------------
# Main scraper
# ---------------------------------------------------------------------------

def load_expanded_queries(press_dir: Path) -> pd.DataFrame:
    """Load the expanded query set (593 queries) generated by expanded_search_terms.py."""
    expanded_path = press_dir / "expanded_search_queries.csv"
    original_path = press_dir / "search_queries.csv"

    dfs = []
    if original_path.exists():
        dfs.append(pd.read_csv(original_path))
    if expanded_path.exists():
        dfs.append(pd.read_csv(expanded_path))

    if not dfs:
        raise FileNotFoundError("No search query files found")

    df = pd.concat(dfs, ignore_index=True)
    df = df.drop_duplicates(subset=["query"]).reset_index(drop=True)
    return df


def run_live_search(
    queries_df: pd.DataFrame,
    output_dir: Path,
    bing_api_key: Optional[str] = None,
    delay: float = 1.0,
    max_queries_per_city: int = 50,
) -> pd.DataFrame:
    """
    Execute live search across all queries. Rate-limited.

    Args:
        queries_df: DataFrame with columns: city, query, rtcc_year
        output_dir: Where to save results
        bing_api_key: Optional Bing News API key
        delay: Seconds between requests (rate limiting)
        max_queries_per_city: Cap queries per city to avoid over-scraping
    """
    all_results = []
    total_queries = 0
    total_hits = 0

    for city in queries_df["city"].unique():
        city_queries = queries_df[queries_df["city"] == city].head(max_queries_per_city)
        city_hits = 0

        logger.info(f"Searching {city}: {len(city_queries)} queries")

        for _, row in city_queries.iterrows():
            query = row["query"]
            rtcc_year = row.get("rtcc_year", "")
            category = row.get("query_category", "unknown")

            # --- Google News RSS ---
            results = search_google_news_rss(query, num_results=10)

            for r in results:
                r["city"] = city
                r["query_used"] = query
                r["rtcc_year"] = rtcc_year
                r["query_category"] = category
                r["source_type"] = "google_news"
                r["search_date"] = datetime.now().strftime("%Y-%m-%d")

                # Extract structured data from snippet + title
                combined_text = f"{r['title']} {r['snippet']}"
                r["extracted_years"] = str(extract_implementation_dates(combined_text))
                r["extracted_budget"] = extract_budget_info(combined_text) or ""
                r["extracted_capabilities"] = str(extract_capabilities(combined_text))

            all_results.extend(results)
            city_hits += len(results)
            total_queries += 1

            if total_queries % 20 == 0:
                logger.info(f"  Progress: {total_queries} queries, {total_hits} hits")

            time.sleep(delay)

        # --- Vendor pages for this city ---
        vendor_results = search_vendor_pages(city)
        for r in vendor_results:
            r["city"] = city
            r["query_used"] = "vendor_page_scan"
            r["rtcc_year"] = rtcc_year
            r["query_category"] = "vendor"
            r["search_date"] = datetime.now().strftime("%Y-%m-%d")
        all_results.extend(vendor_results)
        city_hits += len(vendor_results)

        logger.info(f"  {city}: {city_hits} total hits")

    # Build DataFrame
    df_results = pd.DataFrame(all_results) if all_results else pd.DataFrame()

    if not df_results.empty:
        # Deduplicate by URL
        before = len(df_results)
        df_results = df_results.drop_duplicates(subset=["url"]).reset_index(drop=True)
        after = len(df_results)
        logger.info(f"Deduplicated: {before} -> {after} unique articles")

        # Save
        df_results.to_csv(output_dir / "scraped_articles.csv", index=False)
        logger.info(f"Saved {len(df_results)} results to scraped_articles.csv")

        # Update city summary
        _update_city_summary(df_results, output_dir)

    # Print summary
    print(f"\n{'='*60}")
    print("RTCC PRESS SEARCH RESULTS")
    print(f"{'='*60}")
    print(f"Queries executed: {total_queries}")
    print(f"Total hits: {len(df_results)}")

    if not df_results.empty:
        print(f"\nBy city:")
        print(df_results.groupby("city").size().to_string())
        print(f"\nBy category:")
        print(df_results.groupby("query_category").size().to_string())

        # Flag articles with implementation year mentions
        year_mentions = df_results[df_results["extracted_years"] != "[]"]
        if not year_mentions.empty:
            print(f"\nArticles mentioning implementation years: {len(year_mentions)}")
            for _, row in year_mentions.head(10).iterrows():
                print(f"  [{row['city']}] {row['title'][:60]}... -> years={row['extracted_years']}")

    return df_results


def _update_city_summary(df_results: pd.DataFrame, output_dir: Path):
    """Update city_summary.csv with search results."""
    summary_path = output_dir / "city_summary.csv"

    # Load existing if present
    existing = pd.read_csv(summary_path) if summary_path.exists() else pd.DataFrame()

    new_summary = df_results.groupby("city").agg(
        scraped_articles=("title", "count"),
        unique_sources=("source", "nunique"),
        queries_with_hits=("query_used", "nunique"),
    ).reset_index()

    if not existing.empty:
        merged = existing.merge(new_summary, on="city", how="outer", suffixes=("_old", ""))
        new_summary = merged

    new_summary.to_csv(summary_path, index=False)


def run_scraper(output_dir: str = "results/study1_rtcc/press_correlation"):
    """
    Run the full RTCC press release scraper with expanded queries.

    Creates:
    - scraped_articles.csv — all search results
    - city_summary.csv — updated summary
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load expanded queries
    queries_df = load_expanded_queries(output_path)
    logger.info(f"Loaded {len(queries_df)} queries across {queries_df['city'].nunique()} cities")

    # Run live search
    df_results = run_live_search(queries_df, output_path)

    return df_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Press Release Scraper (Expanded)")
    parser.add_argument("--output", default="results/study1_rtcc/press_correlation")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--max-per-city", type=int, default=50, help="Max queries per city")
    args = parser.parse_args()

    run_scraper(args.output)
