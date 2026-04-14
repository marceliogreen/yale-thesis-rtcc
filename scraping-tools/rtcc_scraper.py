#!/usr/bin/env python3
"""
RTCC Data Scraper - Multi-tool scraping for RTCC effectiveness research

Collects data from:
- City government websites (RTCC announcements)
- Police department news releases
- Vendor websites (Motorola, ShotSpotter)
- Academic sources (Google Scholar, journals)
- News coverage

Tools integrated:
- AutoScraper: Learn patterns from examples
- ScrapeGraphAI: LLM-powered extraction
- Trafilatura: Clean text extraction
- BeautifulSoup: HTML parsing
"""

import json
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import trafilatura
from autoscraper import AutoScraper


class RTCCScraper:
    """Multi-tool scraper for RTCC effectiveness research."""

    # RTCC cities with known implementation years
    RTCC_CITIES = {
        "Hartford": {"state": "CT", "rtcc_year": 2016, "ori": "CT0030100"},
        "Miami": {"state": "FL", "rtcc_year": 2016, "ori": "FL0130200"},
        "St. Louis": {"state": "MO", "rtcc_year": 2015, "ori": "MO0640000"},
        "Newark": {"state": "NJ", "rtcc_year": 2018, "ori": "NJ0071400"},
        "New Orleans": {"state": "LA", "rtcc_year": 2017, "ori": "LA0360000"},
        "Albuquerque": {"state": "NM", "rtcc_year": 2020, "ori": "NM0010100"},
        "Fresno": {"state": "CA", "rtcc_year": 2018, "ori": "CA0190200"},
        "Chicago": {"state": "IL", "rtcc_year": 2017, "ori": "IL0160000"},
    }

    # Search query templates
    SEARCH_TEMPLATES = {
        "launch": "{city} Real Time Crime Center launch announcement",
        "evaluation": "{city} RTCC evaluation effectiveness report",
        "news": "{city} Real Time Crime Center news coverage",
        "vendor": "{city} RTCC Motorola ShotSpotter contract",
    }

    # Vendor websites to scrape
    VENDOR_SOURCES = {
        "Motorola": "https://www.motorolasolutions.com/newsroom.html",
        "ShotSpotter": "https://www.shotspotter.com/news/",
        "Flock Safety": "https://www.flocksafety.com/news",
    }

    # Academic search URLs
    ACADEMIC_SOURCES = {
        "Google Scholar": "https://scholar.google.com/scholar?q=real+time+crime+center+effectiveness",
        "NIJ": "https://nij.ojp.gov/topics/articles/real-time-crime-centers",
        "Police Chief": "https://www.policechiefmagazine.org/?s=real+time+crime+center",
    }

    def __init__(self, output_dir: str = "scraped_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results = []

    def scrape_with_trafilatura(self, url: str) -> Optional[Dict]:
        """Extract clean text and metadata from URL using Trafilatura."""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded, include_comments=False)
                metadata = trafilatura.metadata_extraction(downloaded)
                return {
                    "url": url,
                    "text": text,
                    "title": metadata.title if metadata else "",
                    "date": metadata.date if metadata else "",
                    "author": metadata.author if metadata else "",
                }
        except Exception as e:
            print(f"Trafilatura error for {url}: {e}")
        return None

    def scrape_city_announcements(self, city: str) -> List[Dict]:
        """Search and scrape city RTCC announcements."""
        results = []
        state = self.RTCC_CITIES[city]["state"]

        # City.gov news search patterns
        search_urls = [
            f"https://www.{city.lower().replace(' ', '')}gov.com/news",  # Try common patterns
            f"https://www.{city.lower()}{state.lower()}.gov/news",
        ]

        for base_url in search_urls:
            try:
                data = self.scrape_with_trafilatura(base_url)
                if data and "real time crime" in data.get("text", "").lower():
                    data["city"] = city
                    data["source_type"] = "city_announcement"
                    results.append(data)
            except:
                continue

        return results

    def scrape_vendor_pages(self) -> List[Dict]:
        """Scrape vendor websites for RTCC mentions."""
        results = []

        for vendor, url in self.VENDOR_SOURCES.items():
            print(f"Scraping {vendor}...")
            data = self.scrape_with_trafilatura(url)
            if data:
                data["vendor"] = vendor
                data["source_type"] = "vendor"
                results.append(data)

        return results

    def extract_rtcc_dates(self, text: str) -> List[str]:
        """Extract dates from text that might be RTCC launch dates."""
        # Date patterns: March 15, 2016; March 2016; 2016
        date_patterns = [
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}",
            r"\b\d{4}\b",
        ]

        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)

        return dates

    def use_autoscraper(self, url: str, wanted_list: List[str]) -> List[str]:
        """Use AutoScraper to learn patterns and extract similar data."""
        scraper = AutoScraper()
        try:
            result = scraper.build(url, wanted_list)
            return result
        except Exception as e:
            print(f"AutoScraper error: {e}")
            return []

    def save_results(self, filename: str = "rtcc_scraped_data.json"):
        """Save all scraped results to JSON."""
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(self.results)} results to {output_path}")
        return output_path

    def export_to_csv(self, filename: str = "rtcc_scraped_data.csv"):
        """Export scraped data to CSV for analysis."""
        output_path = self.output_dir / filename

        if not self.results:
            print("No results to export")
            return None

        # Get all unique keys
        fieldnames = set()
        for item in self.results:
            fieldnames.update(item.keys())

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            writer.writerows(self.results)

        print(f"Exported to {output_path}")
        return output_path


def search_google_scholar(query: str) -> List[Dict]:
    """
    Search Google Scholar for RTCC effectiveness studies.

    Note: This returns titles/links - full paper access may require subscriptions.
    """
    results = []
    scholar_url = f"https://scholar.google.com/scholar?q={query.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        response = requests.get(scholar_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract paper titles and links
        for entry in soup.find_all("div", class_="gs_r gs_or gs_scl"):
            title_elem = entry.find("h3")
            link_elem = entry.find("a")

            if title_elem and link_elem:
                results.append({
                    "title": title_elem.get_text(strip=True),
                    "url": link_elem.get("href", ""),
                    "source": "Google Scholar",
                })
    except Exception as e:
        print(f"Google Scholar search error: {e}")

    return results


def main():
    """Main scraping workflow."""
    print("=" * 60)
    print("RTCC Data Scraper - Multi-tool scraping for thesis research")
    print("=" * 60)

    scraper = RTCCScraper(output_dir="scraped_data")

    # 1. Search Google Scholar for academic papers
    print("\n[1/5] Searching Google Scholar...")
    scholar_results = search_google_scholar("real time crime center effectiveness evaluation")
    scraper.results.extend(scholar_results)
    print(f"Found {len(scholar_results)} academic sources")

    # 2. Scrape vendor websites
    print("\n[2/5] Scraping vendor websites...")
    vendor_results = scraper.scrape_vendor_pages()
    scraper.results.extend(vendor_results)

    # 3. For each RTCC city, search for announcements
    print("\n[3/5] Searching city announcements...")
    for city in scraper.RTCC_CITIES.keys():
        print(f"  - {city}...")
        city_results = scraper.scrape_city_announcements(city)
        scraper.results.extend(city_results)

    # 4. Save results
    print("\n[4/5] Saving results...")
    json_path = scraper.save_results()
    csv_path = scraper.export_to_csv()

    # 5. Summary
    print("\n[5/5] Summary:")
    print(f"  Total items scraped: {len(scraper.results)}")
    print(f"  JSON saved to: {json_path}")
    print(f"  CSV saved to: {csv_path}")

    return scraper.results


if __name__ == "__main__":
    results = main()
