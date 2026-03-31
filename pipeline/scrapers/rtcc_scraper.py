"""
RTCC Web Scraper for Yale Thesis Pipeline

Scrapes web sources for RTCC launch announcements, news coverage, and vendor releases.

Data Sources:
- Mayor/Police press releases (city.gov domains)
- Local news coverage
- National news trend pieces
- Vendor announcements (Motorola, ShotSpotter, Flock Safety, etc.)
- City council minutes
"""

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class RTCCTimelineEvent:
    """A single event in the RTCC adoption timeline."""
    date: str  # YYYY-MM-DD or YYYY-MM format
    city: str
    event_type: str  # "launch", "expansion", "shutdown", "evaluation", "news"
    source_url: str
    source_type: str  # "press_release", "news", "council_minutes", "vendor"
    title: str
    summary: str
    budget: Optional[int] = None
    vendor: Optional[str] = None
    claims: Optional[Dict[str, str]] = None
    confounders: Optional[List[str]] = None
    quotes: Optional[List[Dict[str, str]]] = None


@dataclass
class CityRTCCInfo:
    """Aggregated RTCC information for a single city."""
    launch_date: Optional[str]  # YYYY-MM-DD
    initial_budget: Optional[int]
    vendor: Optional[str]
    expansions: List[Dict[str, Any]]
    news_coverage_count: int
    evaluation_mentions: int
    quotes: List[Dict[str, str]]
    data_sources: List[str]


class RTCCScraper:
    """
    Scrapes web sources for RTCC launch and coverage data.

    Target: 8 RTCC cities + national trend analysis
    Output: scraped_rtcc_events.csv, scraped_rtcc_timeline.json
    """

    # RTCC Cities and their search patterns
    CITY_SEARCH_TEMPLATES = {
        "Hartford": [
            "Hartford Real Time Crime Center launch",
            "Hartford RTCC Motorola",
            "Hartford shot spotter implementation",
            "Hartford real time crime",
        ],
        "Miami": [
            "Miami Real Time Crime Center",
            "Miami RTCC launch",
            "Miami shot spotter",
        ],
        "St. Louis": [
            "St. Louis Real Time Crime Center",
            "St. Louis RTCC",
            "St. Louis crime center",
        ],
        "Newark": [
            "Newark Real Time Crime Center",
            "Newark RTCC",
            "Newark Public Safety headquarters",
        ],
        "New Orleans": [
            "New Orleans Real Time Crime Center",
            "New Orleans RTCC",
            "New Orleans crime center",
        ],
        "Albuquerque": [
            "Albuquerque Real Time Crime Center",
            "Albuquerque RTCC",
            "Albuquerque crime center",
        ],
        "Fresno": [
            "Fresno Real Time Crime Center",
            "Fresno RTCC",
            "Fresno crime center",
        ],
        "Chicago": [
            "Chicago Real Time Crime Center",
            "Chicago RTCC",
            "Chicago crime center",
        ],
    }

    # News sources by city
    NEWS_SOURCES = {
        "Hartford": ["hartfordcourant.com", "hartford.gov"],
        "Miami": ["miamiherald.com", "miamigov.com"],
        "St. Louis": ["stltoday.com", "stlouisco.com"],
        "Newark": ["nj.com", "newark.gov"],
        "New Orleans": ["nola.com", "nola.gov"],
        "Albuquerque": ["abqjournal.com", "cabq.gov"],
        "Fresno": ["fresnobee.com", "fresno.gov"],
        "Chicago": ["chicagotribune.com", "chicago.gov", "chicagopolice.org"],
    }

    # National news sources
    NATIONAL_SOURCES = [
        "nytimes.com",
        "washingtonpost.com",
        "cnn.com",
        "apnews.com",
        "npr.org",
    ]

    # Trade/industry sources
    TRADE_SOURCES = [
        "policechiefmagazine.org",
        "govtech.com",
        "justice.gov",
        "cops.usdoj.gov",
    ]

    # Vendor sources
    VENDOR_SOURCES = {
        "Motorola": ["motorolasolutions.com"],
        "ShotSpotter": ["shotspotter.com"],
        "Flock Safety": ["flocksafety.com"],
        "Axon": ["axon.com"],
        "Genetec": ["genetec.com"],
        "Hexagon": ["hexagon.com"],
    }

    # Hardcoded fallback dates (from advisor deck)
    FALLBACK_DATES = {
        "St. Louis": "2015-01-01",
        "Hartford": "2016-03-15",  # Approximate
        "Miami": "2016-01-01",
        "New Orleans": "2017-01-01",
        "Chicago": "2017-01-01",
        "Newark": "2018-01-01",
        "Fresno": "2018-01-01",
        "Albuquerque": "2020-01-01",
    }

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        user_agent: Optional[str] = None,
        min_delay: float = 1.0,
    ):
        """
        Initialize the RTCC scraper.

        Args:
            cache_dir: Directory for cached responses
            user_agent: User agent string for requests
            min_delay: Minimum delay between requests (seconds)
        """
        # Cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "cache" / "scraped"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # User agent (required via environment variable for personal accountability)
        if user_agent is None:
            user_agent = os.getenv("SCRAPER_USER_AGENT")
            if not user_agent:
                raise ValueError(
                    "SCRAPER_USER_AGENT environment variable required. "
                    "Add to .env: SCRAPER_USER_AGENT='Your User-Agent String'"
                )
        self.user_agent = user_agent
        self.min_delay = min_delay

        # Rate limiting
        self.last_request_time = 0

        # Results
        self.events: List[RTCCTimelineEvent] = []
        self.city_info: Dict[str, CityRTCCInfo] = {}

        logger.info(f"Initialized RTCCScraper with cache_dir={self.cache_dir}")

    async def _get_with_delay(
        self, client: httpx.AsyncClient, url: str, **kwargs
    ) -> httpx.Response:
        """Make HTTP request with rate limiting delay."""
        # Enforce minimum delay
        elapsed = asyncio.get_event_loop().time() - self.last_request_time
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)

        self.last_request_time = asyncio.get_event_loop().time()

        headers = kwargs.pop("headers", {})
        headers["User-Agent"] = self.user_agent

        try:
            response = await client.get(url, headers=headers, timeout=30.0, **kwargs)
            return response
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error for {url}: {e.response.status_code}")
            raise
        except httpx.TimeoutException:
            logger.warning(f"Timeout for {url}")
            raise
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e}")
            raise

    def _extract_date(self, text: str, soup: Optional[BeautifulSoup] = None) -> Optional[str]:
        """
        Extract RTCC launch date from text or HTML.

        Looks for patterns like:
        - "March 15, 2016"
        - "2016-03-15"
        - "opened in 2016"
        """
        # Check meta tags first
        if soup:
            # Date meta tags
            for meta in ["date", "publish-date", "article:published_time"]:
                meta_tag = soup.find("meta", property=f"article:{meta}") or soup.find(
                    "meta", attrs={"name": meta}
                )
                if meta_tag and meta_tag.get("content"):
                    date_str = meta_tag["content"]
                    # Try to parse
                    for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m"]:
                        try:
                            return datetime.strptime(date_str[:10], fmt).strftime("%Y-%m-%d")
                        except ValueError:
                            continue

        # Common date patterns in text
        patterns = [
            r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"\d{4}-\d{2}-\d{2}",
            r"(?:opened|launched|debuted|announced)\s+(?:on\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
            r"(?:opened|launched|debuted|announced)\s+(?:on\s+)?\d{1,2}/\d{1,2}/\d{4}",
            r"(?:in\s+)?(?:early|mid|late)?\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                # Clean up and parse
                date_str = re.sub(
                    r"(?:opened|launched|debuted|announced|on\s+|in\s+|early\s+|mid\s+|late\s+)",
                    "",
                    date_str,
                    flags=re.IGNORECASE,
                ).strip()

                # Try to parse
                for fmt in ["%B %d, %Y", "%B %d %Y", "%Y-%m-%d", "%m/%d/%Y", "%B %Y"]:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        return parsed_date.strftime("%Y-%m-%d")
                    except ValueError:
                        continue

        # Look for standalone years
        year_match = re.search(r"\b(20\d{2})\b", text)
        if year_match:
            return year_match.group(1) + "-01-01"

        return None

    def _extract_budget(self, text: str) -> Optional[int]:
        """Extract budget amount from text."""
        patterns = [
            r"\$([\d.]+)\s*million",
            r"\$([\d,]+)",
            r"([\d.]+)\s*million\s+dollars",
            r"budget\s+(?:of\s+)?\$?([\d.]+)\s*m",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    amount = float(amount_str)
                    if "million" in match.group(0).lower():
                        return int(amount * 1_000_000)
                    return int(amount)
                except ValueError:
                    continue

        return None

    def _extract_vendor(self, text: str) -> Optional[str]:
        """Extract RTCC vendor from text."""
        vendors = ["Motorola", "ShotSpotter", "Flock", "Axon", "Genetec", "Hexagon", "Palantir"]
        text_lower = text.lower()

        for vendor in vendors:
            if vendor.lower() in text_lower:
                return vendor

        return None

    def _extract_claims(self, text: str) -> Dict[str, str]:
        """Extract claimed benefits from text."""
        claims = {}

        # Common claim patterns
        claim_patterns = {
            "response_time": r"(?:response|respond)\s+time\s+(?:reduced|by|improved|faster)",
            "crime_reduction": r"(?:crime|criminal)\s+(?:reduction|reduced|down|decrease)",
            "clearance": r"(?:clearance|solve|solving)\s+(?:rate|improved|increased)",
            "real_time": r"(?:real\s?time|instant|immediate)",
            "efficiency": r"(?:efficiency|efficient)",
        }

        for claim_type, pattern in claim_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                claims[claim_type] = "claimed"

        return claims if claims else None

    async def scrape_city_press_releases(
        self, city: str, max_pages: int = 10
    ) -> List[RTCCTimelineEvent]:
        """
        Scrape city government press releases for RTCC announcements.

        Note: This is a placeholder implementation. In production,
        you would need to:
        1. Actually fetch from city.gov URLs
        2. Handle different CMS systems used by cities
        3. Parse press release listings

        For now, this returns a template structure.
        """
        logger.info(f"Scraping press releases for {city}")

        events = []

        # Template event - replace with actual scraping
        # This is where you would implement:
        # - Fetching from hartford.gov/news, miamigov.com/news, etc.
        # - Parsing RSS feeds if available
        # - Searching site-specific search functions

        logger.debug(f"Found {len(events)} press release events for {city}")
        return events

    async def scrape_vendor_releases(self, max_pages: int = 5) -> List[RTCCTimelineEvent]:
        """
        Scrape vendor press releases for RTCC client announcements.

        Vendors often publish case studies or announcements when cities adopt their technology.
        """
        logger.info("Scraping vendor press releases")

        events = []

        # Template implementation
        # In production, fetch from:
        # - motorolasolutions.com/newsroom
        # - shotspotter.com/news
        # - flocksafety.com/news

        logger.debug(f"Found {len(events)} vendor events")
        return events

    async def search_news_coverage(
        self, city: str, max_results: int = 20
    ) -> List[RTCCTimelineEvent]:
        """
        Search for news coverage of RTCC in a city.

        Note: This would require integration with a news API or
        direct scraping of known news sources.

        For a thesis, consider using:
        - NewsAPI.org (has free tier)
        - Google News RSS feeds
        - Direct scraping of known local news sites
        """
        logger.info(f"Searching news coverage for {city}")

        events = []

        # Template implementation
        # In production, use NewsAPI or similar

        logger.debug(f"Found {len(events)} news events for {city}")
        return events

    def build_timeline(self) -> Dict[str, CityRTCCInfo]:
        """
        Build RTCC timeline from scraped events.

        Returns aggregated information for each city.
        """
        logger.info("Building RTCC timeline from scraped events")

        # Initialize city info with fallback dates
        for city in self.CITY_SEARCH_TEMPLATES.keys():
            self.city_info[city] = CityRTCCInfo(
                launch_date=self.FALLBACK_DATES.get(city),
                initial_budget=None,
                vendor=None,
                expansions=[],
                news_coverage_count=0,
                evaluation_mentions=0,
                quotes=[],
                data_sources=["fallback"],
            )

        # Process scraped events
        for event in self.events:
            city = event.city

            if city not in self.city_info:
                continue

            info = self.city_info[city]

            # Update launch date if we found one
            if event.event_type == "launch" and event.date:
                if info.launch_date == self.FALLBACK_DATES.get(city):
                    info.launch_date = event.date
                    info.data_sources = ["scraped"]

            # Update vendor
            if event.vendor:
                info.vendor = event.vendor

            # Update budget
            if event.budget and not info.initial_budget:
                info.initial_budget = event.budget

            # Track expansions
            if event.event_type == "expansion":
                info.expansions.append(
                    {"date": event.date, "description": event.summary, "budget": event.budget}
                )

            # Count news coverage
            if event.source_type == "news":
                info.news_coverage_count += 1

            # Track evaluations
            if event.event_type == "evaluation":
                info.evaluation_mentions += 1

            # Collect quotes
            if event.quotes:
                info.quotes.extend(event.quotes)

            # Track data sources
            if "scraped" not in info.data_sources:
                info.data_sources.append("scraped")
            if event.source_type not in info.data_sources:
                info.data_sources.append(event.source_type)

        return self.city_info

    def load_scraped_timeline(self, path: Optional[Path] = None) -> Dict[str, CityRTCCInfo]:
        """Load previously scraped timeline from JSON file."""
        if path is None:
            path = self.cache_dir / "scraped_rtcc_timeline.json"

        if path.exists():
            with open(path, "r") as f:
                data = json.load(f)

            # Convert dicts back to CityRTCCInfo
            self.city_info = {
                city: CityRTCCInfo(**info) for city, info in data.items()
            }
            logger.info(f"Loaded scraped timeline for {len(self.city_info)} cities")
            return self.city_info

        return {}

    def save_timeline(self, path: Optional[Path] = None):
        """Save timeline to JSON file."""
        if path is None:
            path = self.cache_dir / "scraped_rtcc_timeline.json"

        # Convert CityRTCCInfo objects to dicts
        data = {
            city: asdict(info) for city, info in self.city_info.items()
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Saved timeline to {path}")

    def save_events(self, path: Optional[Path] = None):
        """Save events to CSV file."""
        if path is None:
            path = self.cache_dir / "scraped_rtcc_events.csv"

        import pandas as pd

        # Convert events to list of dicts
        data = [asdict(event) for event in self.events]

        # Flatten claims and quotes for CSV
        for row in data:
            if row.get("claims"):
                row["claims"] = json.dumps(row["claims"])
            if row.get("confounders"):
                row["confounders"] = json.dumps(row["confounders"])
            if row.get("quotes"):
                row["quotes"] = json.dumps(row["quotes"])

        df = pd.DataFrame(data)
        df.to_csv(path, index=False)

        logger.info(f"Saved {len(self.events)} events to {path}")

    async def scrape_all(
        self,
        cities: Optional[List[str]] = None,
        include_vendors: bool = True,
        include_news: bool = True,
    ):
        """
        Run full scraping pipeline.

        Args:
            cities: List of cities to scrape (default: all 8 RTCC cities)
            include_vendors: Whether to scrape vendor announcements
            include_news: Whether to search news coverage
        """
        if cities is None:
            cities = list(self.CITY_SEARCH_TEMPLATES.keys())

        logger.info(f"Starting scrape for {len(cities)} cities")

        # Scrape each city
        for city in cities:
            try:
                events = await self.scrape_city_press_releases(city)
                self.events.extend(events)
            except Exception as e:
                logger.error(f"Error scraping {city} press releases: {e}")

        # Scrape vendors
        if include_vendors:
            try:
                vendor_events = await self.scrape_vendor_releases()
                self.events.extend(vendor_events)
            except Exception as e:
                logger.error(f"Error scraping vendor releases: {e}")

        # Search news
        if include_news:
            for city in cities:
                try:
                    news_events = await self.search_news_coverage(city)
                    self.events.extend(news_events)
                except Exception as e:
                    logger.error(f"Error searching news for {city}: {e}")

        # Build timeline
        self.build_timeline()

        # Save results
        self.save_timeline()
        self.save_events()

        logger.info(f"Scraping complete: {len(self.events)} events collected")


# ============ CLI Interface ============

def main():
    """CLI interface for the RTCC scraper."""
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Timeline Scraper")
    parser.add_argument("--city", type=str, help="Specific city to scrape")
    parser.add_argument("--all", action="store_true", help="Scrape all 8 RTCC cities")
    parser.add_argument("--vendors", action="store_true", help="Include vendor announcements")
    parser.add_argument("--news", action="store_true", help="Include news search")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    cache_dir = args.output if args.output else None
    scraper = RTCCScraper(cache_dir=cache_dir)

    if args.all:
        cities = None  # All cities
    elif args.city:
        cities = [args.city]
    else:
        # Default to just Hartford for testing
        cities = ["Hartford"]

    asyncio.run(scraper.scrape_all(
        cities=cities,
        include_vendors=args.vendors,
        include_news=args.news,
    ))

    # Print summary
    print("\n" + "=" * 50)
    print("SCRAPING SUMMARY")
    print("=" * 50)
    print(f"Total events: {len(scraper.events)}")
    print(f"Cities with data: {len(scraper.city_info)}")

    for city, info in scraper.city_info.items():
        print(f"\n{city}:")
        print(f"  Launch date: {info.launch_date}")
        print(f"  Vendor: {info.vendor}")
        print(f"  Budget: ${info.initial_budget:,}" if info.initial_budget else "  Budget: Unknown")
        print(f"  News coverage: {info.news_coverage_count} articles")
        print(f"  Expansions: {len(info.expansions)}")


if __name__ == "__main__":
    main()
