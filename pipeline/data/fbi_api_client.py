"""
Unified Crime Data Client for RTCC Thesis Pipeline

Integrates multiple federal crime data APIs:
- FBI Crime Data Explorer (CDE): https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi
- BJS NIBRS National Estimates: https://bjs.ojp.gov/national-incident-based-reporting-system-nibrs-national-estimates-api
- ICPSR Researcher Passport: https://dir.api.it.umich.edu/docs/icpsr-researcher-passport/1/overview
- LEMAS: https://catalog.data.gov/dataset/law-enforcement-management-and-administrative-statistics-lemas-series-db146

Author: Marcelo Green <marcelo.green@yale.edu>
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

import httpx
import numpy as np
import pandas as pd
from dotenv import load_dotenv

from pipeline.config import get_rtcc_years, get_rtcc_oris

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class RTCCCity:
    """Configuration for an RTCC target city."""
    city: str
    ori: str
    rtcc_year: int


@dataclass
class APIError(Exception):
    """Structured error information."""
    endpoint: str
    status_code: Optional[int]
    message: str
    retry_after: Optional[int] = None


class UnifiedCrimeDataClient:
    """
    Multi-source client for FBI crime data.

    Integrates:
    - FBI Crime Data Explorer (CDE): Homicide counts by ORI
    - BJS NIBRS: Clearance rates (national and agency-level)
    - ICPSR: UCR, NIBRS, Supplementary Homicide Reports datasets
    - LEMAS: Agency characteristics (budget, officers, technology)

    All data is cached locally to minimize API calls.
    """

    RTCC_ORIS = {
        city: {"ori": ori, "rtcc_year": get_rtcc_years()[city]}
        for city, ori in get_rtcc_oris().items()
    }

    # Reverse-engineered CDE webapp ORIs differ from some panel/Kaplan ORIs.
    # These aliases preserve the checked-in FBI CDE results when the legacy
    # api.data.gov routes fall back to the current webapp endpoints.
    FBI_WEBAPP_ORI_ALIASES = {
        "IL0160000": "ILCPD0000",
        "MO0640000": "MOSPD0000",
        "LA0360000": "LANPD0000",
        "FL0130200": "FL0130600",
        "NJ0071400": "NJNPD0000",
        "CA0190200": "CA0100500",
    }

    # API Endpoints
    FBI_CDE_BASE = "https://api.usa.gov/crime/fbi/cde"
    FBI_CDE_WEBAPP_BASE = "https://cde.ucr.cjis.gov/LATEST"
    BJS_NIBRS_BASE = "https://api.bjs.ojp.gov/nibrs"
    ICPSR_BASE = "https://dir.api.it.umich.edu"
    LEMAS_BASE = "https://api.bjs.ojp.gov/lemas"

    # Default years
    DEFAULT_START_YEAR = 2010
    DEFAULT_END_YEAR = 2023

    def __init__(
        self,
        fbi_api_key: Optional[str] = None,
        bjs_api_key: Optional[str] = None,
        icpsr_api_key: Optional[str] = None,
        icpsr_email: Optional[str] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize the unified crime data client.

        Args:
            fbi_api_key: FBI Crime Data Explorer API key (from data.gov)
            bjs_api_key: BJS NIBRS API key (optional, for rate limit increases)
            icpsr_api_key: ICPSR Researcher Passport API token
            icpsr_email: ICPSR account email
            cache_dir: Base directory for cache storage
        """
        # Resolve API keys from environment if not provided
        self.fbi_api_key = self._resolve_api_key(fbi_api_key, "FBI_API_KEY")
        self.bjs_api_key = self._resolve_api_key(bjs_api_key, "BJS_API_KEY", optional=True)
        self.icpsr_api_key = self._resolve_api_key(icpsr_api_key, "ICPSR_API_KEY", optional=True)
        self.icpsr_email = self._resolve_api_key(icpsr_email, "ICPSR_EMAIL", optional=True)

        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "cache"
        self.cache_dir = Path(cache_dir)
        self.fbi_cache_dir = self.cache_dir / "fbi_cde"
        self.bjs_cache_dir = self.cache_dir / "bjs_nibrs"
        self.icpsr_cache_dir = self.cache_dir / "icpsr"

        # Create cache directories
        for dir_path in [self.fbi_cache_dir, self.bjs_cache_dir, self.icpsr_cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Track data sources for transparency
        self.data_source_log = []

        logger.info(f"Initialized UnifiedCrimeDataClient")
        logger.info(f"FBI CDE API key: {'✓ Configured' if self.fbi_api_key else '✗ Missing'}")
        logger.info(f"BJS NIBRS API key: {'✓ Configured' if self.bjs_api_key else 'Optional'}")
        logger.info(f"ICPSR API key: {'✓ Configured' if self.icpsr_api_key else '✗ Missing'}")

    @staticmethod
    def _resolve_api_key(
        key: Optional[str], env_var: str, optional: bool = False
    ) -> Optional[str]:
        """
        Resolve API key from various sources.

        Handles the en:// prefix pattern used in this project.

        Args:
            key: Provided key (may have en:// prefix)
            env_var: Environment variable name
            optional: If True, return None instead of raising error

        Returns:
            Resolved API key or None
        """
        if key:
            if key.startswith("en://"):
                env_var_name = key[5:]
                resolved = os.getenv(env_var_name)
                if not resolved and not optional:
                    raise ValueError(
                        f"Environment variable {env_var_name} not found. "
                        f"Add to .env: {env_var_name}=your_key_here"
                    )
                return resolved
            return key

        # Try direct environment lookup
        direct_key = os.getenv(env_var)
        if direct_key:
            if direct_key.startswith("en://"):
                return UnifiedCrimeDataClient._resolve_api_key(direct_key, env_var, optional)
            return direct_key

        if not optional:
            logger.warning(f"{env_var} not found in environment")
        return None

    def _get_cache_path(
        self, source: str, ori: str, start_year: int, end_year: int
    ) -> Path:
        """Generate cache file path for a specific city/year range."""
        city_slug = ori.lower().replace("-", "_")
        filename = f"{source}_{city_slug}_{start_year}-{end_year}.json"
        if source == "fbi_cde":
            return self.fbi_cache_dir / filename
        elif source == "bjs_nibrs":
            return self.bjs_cache_dir / filename
        else:
            return self.icpsr_cache_dir / filename

    def _load_from_cache(self, cache_path: Path) -> Optional[Dict]:
        """Load cached response if available and fresh."""
        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)

            # Check cache age (24 hours for API data)
            cached_at = datetime.fromisoformat(cached.get("cached_at", ""))
            age = (datetime.now() - cached_at).total_seconds()
            if age > 86400:  # 24 hours
                logger.debug(f"Cache expired: {cache_path.name}")
                return None

            logger.debug(f"Loaded from cache: {cache_path.name}")
            return cached
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}")
            return None

    def _save_to_cache(self, cache_path: Path, data: Dict, endpoint: str):
        """Save API response to cache."""
        cache_entry = {
            "cached_at": datetime.now().isoformat(),
            "endpoint": endpoint,
            "data": data,
        }
        try:
            with open(cache_path, "w") as f:
                json.dump(cache_entry, f, indent=2)
            logger.debug(f"Saved to cache: {cache_path.name}")
        except Exception as e:
            logger.warning(f"Failed to save cache {cache_path}: {e}")

    async def _fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Dict,
        max_retries: int = 5,
        initial_delay: float = 1.0,
    ) -> Dict:
        """
        Execute HTTP request with exponential backoff.

        Retry strategy:
        - max_retries: 5
        - initial_delay: 1.0 second
        - backoff_factor: 2.0
        - max_delay: 60 seconds

        Handles: 429 (rate limit), 500, 502, 503, 504
        """
        delay = initial_delay
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = await client.get(url, params=params, timeout=30.0)

                # Success
                if response.status_code == 200:
                    return response.json()

                # Don't retry client errors (except 429)
                if response.status_code in (400, 401, 403, 404, 422):
                    error_msg = APIError(
                        endpoint=url,
                        status_code=response.status_code,
                        message=response.text,
                    )
                    logger.error(f"Client error {response.status_code}: {url}")
                    raise error_msg

                # Rate limited - check Retry-After header
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = float(retry_after)
                        except ValueError:
                            pass

                # Retry server errors
                last_error = APIError(
                    endpoint=url,
                    status_code=response.status_code,
                    message=response.text,
                )
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: "
                    f"{response.status_code} - retrying in {delay}s"
                )

                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60.0)  # Exponential backoff, max 60s

            except httpx.TimeoutException as e:
                last_error = APIError(endpoint=url, status_code=None, message=f"Timeout: {e}")
                logger.warning(f"Timeout on attempt {attempt + 1}: {url}")

                if attempt < max_retries:
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 60.0)

        # All retries exhausted
        logger.error(f"All retries exhausted for {url}")
        raise last_error

    async def _fetch_cde_webapp_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: Optional[Dict] = None,
    ) -> Dict:
        """Fetch from the reverse-engineered CDE webapp endpoints."""
        url = f"{self.FBI_CDE_WEBAPP_BASE}{path}"
        response = await client.get(url, params=params or {}, timeout=30.0)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _aggregate_shr_actuals_to_offense(data: Dict) -> Dict:
        """
        Convert monthly SHR webapp data into the legacy annual offense structure.
        """
        annual_counts: Dict[int, int] = {}
        actuals = data.get("actuals") or {}
        for _series_name, monthly_data in actuals.items():
            if not monthly_data:
                continue
            for month_year, count in monthly_data.items():
                try:
                    _month, year_str = month_year.split("-")
                    year = int(year_str)
                except ValueError:
                    continue
                annual_counts[year] = annual_counts.get(year, 0) + int(count or 0)

        return {
            "offenses": {
                "offense": [
                    {
                        "crime_name": "Homicide",
                        "data": {
                            str(year): {"actual": count, "cleared": None}
                            for year, count in sorted(annual_counts.items())
                        },
                    }
                ]
            },
            "source": "fbi_cde_webapp_shr",
        }

    # ============ FBI CDE Methods ============

    async def get_fbi_homicide(
        self, ori: str, start_year: int, end_year: int, use_cache: bool = True
    ) -> Dict:
        """
        Fetch homicide data from FBI Crime Data Explorer.

        Endpoint: /agency/{ori}/offenses/homicide/{start_year}/{end_year}

        Args:
            ori: FBI ORI code (e.g., "CT0030100")
            start_year: Start year (inclusive)
            end_year: End year (inclusive)
            use_cache: Whether to use cached data

        Returns:
            API response with homicide counts by year
        """
        endpoint = f"/agency/{ori}/offenses/homicide/{start_year}/{end_year}"
        url = f"{self.FBI_CDE_BASE}{endpoint}"
        params = {"API_KEY": self.fbi_api_key}

        # Check cache
        cache_path = self._get_cache_path("fbi_cde", ori, start_year, end_year)
        if use_cache:
            cached = self._load_from_cache(cache_path)
            if cached:
                self.data_source_log.append(("fbi_cde", ori, start_year, end_year, "cache"))
                return cached["data"]

        # Fetch from API, with fallback to the current webapp endpoints if the
        # legacy api.data.gov route is unavailable.
        async with httpx.AsyncClient() as client:
            try:
                if not self.fbi_api_key:
                    raise ValueError("legacy FBI API key not configured")
                data = await self._fetch_with_retry(client, url, params)
            except Exception as legacy_error:
                logger.info(f"Legacy FBI homicide endpoint unavailable for {ori}; using CDE webapp fallback")
                fallback_ori = self.FBI_WEBAPP_ORI_ALIASES.get(ori, ori)
                shr_data = await self._fetch_cde_webapp_json(
                    client,
                    f"/shr/agency/{fallback_ori}",
                    params={
                        "from": f"01-{start_year}",
                        "to": f"12-{end_year}",
                        "type": "counts",
                    },
                )
                data = self._aggregate_shr_actuals_to_offense(shr_data)
                data["fallback_reason"] = str(legacy_error)
                data["fallback_ori"] = fallback_ori

        # Save to cache
        self._save_to_cache(cache_path, data, endpoint)
        self.data_source_log.append(("fbi_cde", ori, start_year, end_year, "api"))

        return data

    async def get_fbi_summarized(
        self, ori: str, start_year: int, end_year: int, use_cache: bool = True
    ) -> Dict:
        """
        Fetch summarized offense data from FBI CDE.

        Endpoint: /summarized/agency/{ori}/offenses/{start_year}/{end_year}

        Includes clearance data when available.
        """
        endpoint = f"/summarized/agency/{ori}/offenses/{start_year}/{end_year}"
        url = f"{self.FBI_CDE_BASE}{endpoint}"
        params = {"API_KEY": self.fbi_api_key}

        cache_path = self._get_cache_path("fbi_cde_summary", ori, start_year, end_year)
        if use_cache:
            cached = self._load_from_cache(cache_path)
            if cached:
                return cached["data"]

        async with httpx.AsyncClient() as client:
            try:
                if not self.fbi_api_key:
                    raise ValueError("legacy FBI API key not configured")
                data = await self._fetch_with_retry(client, url, params)
            except Exception as exc:
                logger.info(f"Legacy FBI summarized endpoint unavailable for {ori}; returning empty summary")
                data = {"source": "unavailable", "fallback_reason": str(exc)}

        self._save_to_cache(cache_path, data, endpoint)
        return data

    async def get_national_participation(self, use_cache: bool = True) -> Dict:
        """
        Fetch national participation rates.

        Endpoint: /participation/national

        Useful for data quality checks.
        """
        endpoint = "/participation/national"
        url = f"{self.FBI_CDE_BASE}{endpoint}"
        params = {"API_KEY": self.fbi_api_key}

        cache_path = self.fbi_cache_dir / "national_participation.json"
        if use_cache:
            cached = self._load_from_cache(cache_path)
            if cached:
                return cached["data"]

        async with httpx.AsyncClient() as client:
            try:
                if not self.fbi_api_key:
                    raise ValueError("legacy FBI API key not configured")
                data = await self._fetch_with_retry(client, url, params)
            except Exception as legacy_error:
                logger.info("Legacy FBI participation endpoint unavailable; using CDE webapp properties fallback")
                props = await self._fetch_cde_webapp_json(client, "/lookup/cde_properties")
                data = {"data": props, "source": "fbi_cde_webapp_properties", "fallback_reason": str(legacy_error)}

        self._save_to_cache(cache_path, data, endpoint)
        return data

    # ============ BJS NIBRS Methods ============

    async def get_bjs_clearance(self, year: int, offense: str = "homicide") -> Dict:
        """
        Fetch national clearance rates from BJS NIBRS.

        Endpoint: /national-estimates/{year}

        Args:
            year: Year of data
            offense: Offense type (default: "homicide")

        Returns:
            National clearance rate data
        """
        endpoint = f"/national-estimates/{year}"
        url = f"{self.BJS_NIBRS_BASE}{endpoint}"

        # BJS doesn't require API key, but respects rate limits
        await asyncio.sleep(0.1)  # Be respectful

        cache_path = self.bjs_cache_dir / f"national_clearance_{year}.json"
        cached = self._load_from_cache(cache_path)
        if cached:
            self.data_source_log.append(("bjs_nibrs", "national", year, year, "cache"))
            return cached["data"]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                self._save_to_cache(cache_path, data, endpoint)
                self.data_source_log.append(("bjs_nibrs", "national", year, year, "api"))
                return data
            else:
                logger.warning(f"BJS API returned {response.status_code} for {year}")
                return {}

    async def get_bjs_agency_clearance(
        self, ori: str, start_year: int, end_year: int
    ) -> Dict:
        """
        Fetch agency-level clearance estimates from BJS NIBRS.

        Endpoint: /agency-estimates/{ori}/{start_year}/{end_year}

        Note: Not all agencies have NIBRS reporting, especially pre-2021.
        """
        endpoint = f"/agency-estimates/{ori}/{start_year}/{end_year}"
        url = f"{self.BJS_NIBRS_BASE}{endpoint}"

        await asyncio.sleep(0.1)

        cache_path = self._get_cache_path("bjs_nibrs", ori, start_year, end_year)
        cached = self._load_from_cache(cache_path)
        if cached:
            return cached["data"]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                self._save_to_cache(cache_path, data, endpoint)
                return data
            elif response.status_code == 404:
                logger.debug(f"No BJS data for {ori} ({start_year}-{end_year})")
                return {}
            else:
                logger.warning(f"BJS API returned {response.status_code} for {ori}")
                return {}

    # ============ ICPSR Methods ============

    async def get_icpsr_study(self, study_id: str) -> Dict:
        """
        Fetch ICPSR study metadata.

        Requires ICPSR Researcher Passport access.

        Args:
            study_id: ICPSR study number (e.g., "39069")

        Returns:
            Study metadata including variables and files
        """
        if not self.icpsr_api_key:
            logger.warning("ICPSR API key not configured")
            return {}

        endpoint = f"/studies/{study_id}"
        url = f"{self.ICPSR_BASE}{endpoint}"
        headers = {"Authorization": f"Bearer {self.icpsr_api_key}"}

        cache_path = self.icpsr_cache_dir / f"study_{study_id}.json"
        cached = self._load_from_cache(cache_path)
        if cached:
            return cached["data"]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                self._save_to_cache(cache_path, data, endpoint)
                return data
            else:
                logger.warning(f"ICPSR API returned {response.status_code} for study {study_id}")
                return {}

    async def download_icpsr_file(self, study_id: str, file_id: str, output_path: Path) -> bool:
        """
        Download a file from ICPSR.

        Requires ICPSR Researcher Passport access.
        """
        if not self.icpsr_api_key:
            logger.warning("ICPSR API key not configured")
            return False

        endpoint = f"/downloads/{study_id}/{file_id}"
        url = f"{self.ICPSR_BASE}{endpoint}"
        headers = {"Authorization": f"Bearer {self.icpsr_api_key}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=120.0)
            if response.status_code == 200:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Downloaded ICPSR file to {output_path}")
                return True
            else:
                logger.error(f"Failed to download ICPSR file: {response.status_code}")
                return False

    # ============ LEMAS Methods ============

    async def get_lemas_agency(self, ori: str, year: int) -> Dict:
        """
        Fetch LEMAS agency characteristics.

        Provides data on budget, officers, technology adoption.

        Note: LEMAS is collected every 3-4 years (2013, 2016, 2020).
        """
        endpoint = f"/agencies/{ori}/{year}"
        url = f"{self.LEMAS_BASE}{endpoint}"

        await asyncio.sleep(0.1)

        cache_path = self.icpsr_cache_dir / f"lemas_{ori}_{year}.json"
        cached = self._load_from_cache(cache_path)
        if cached:
            return cached["data"]

        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            if response.status_code == 200:
                data = response.json()
                self._save_to_cache(cache_path, data, endpoint)
                return data
            elif response.status_code == 404:
                logger.debug(f"No LEMAS data for {ori} {year}")
                return {}
            else:
                logger.warning(f"LEMAS API returned {response.status_code}")
                return {}

    # ============ Main Aggregation Method ============

    async def fetch_all_rtcc_cities(
        self,
        start_year: int = DEFAULT_START_YEAR,
        end_year: int = DEFAULT_END_YEAR,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch comprehensive crime data for all 8 RTCC cities.

        Combines data from FBI CDE (homicide counts) and BJS/FBI (clearance rates).

        Args:
            start_year: Start year (default: 2010)
            end_year: End year (default: 2023)
            use_cache: Whether to use cached data

        Returns:
            DataFrame with columns:
            - city, ori, year
            - homicide_count (from FBI CDE)
            - clearance_count (from FBI CDE when available)
            - clearance_rate (computed or from BJS)
            - rtcc_year, post_rtcc
            - data_source
        """
        results = []

        for city, config in self.RTCC_ORIS.items():
            ori = config["ori"]
            rtcc_year = config["rtcc_year"]

            logger.info(f"Fetching data for {city} (ORI: {ori})")

            try:
                # Get homicide data from FBI CDE
                fbi_data = await self.get_fbi_homicide(ori, start_year, end_year, use_cache)

                # Get clearance data if available
                try:
                    summary_data = await self.get_fbi_summarized(ori, start_year, end_year, use_cache)
                except Exception as e:
                    logger.debug(f"No FBI summary data for {city}: {e}")
                    summary_data = None

                # Parse FBI response
                offenses = fbi_data.get("offenses", [])
                if isinstance(offenses, dict) and "offense" in offenses:
                    offenses = offenses["offense"]

                # Handle different response formats
                if not isinstance(offenses, list):
                    offenses = [offenses] if offenses else []

                for offense_item in offenses:
                    if offense_item.get("crime_name") != "Homicide":
                        continue

                    # Get data by year
                    data_by_year = offense_item.get("data", {})
                    if isinstance(data_by_year, list):
                        # Convert list format to dict
                        for year_data in data_by_year:
                            year = int(year_data.get("year", 0))
                            if start_year <= year <= end_year:
                                results.append({
                                    "city": city,
                                    "ori": ori,
                                    "year": year,
                                    "homicide_count": year_data.get("actual", 0),
                                    "clearance_count": year_data.get("cleared", 0),
                                    "rtcc_year": rtcc_year,
                                    "post_rtcc": year >= rtcc_year,
                                    "data_source": "fbi_cde",
                                })
                    elif isinstance(data_by_year, dict):
                        # Dict format
                        for year_str, year_data in data_by_year.items():
                            year = int(year_str)
                            if start_year <= year <= end_year:
                                results.append({
                                    "city": city,
                                    "ori": ori,
                                    "year": year,
                                    "homicide_count": year_data.get("actual", 0),
                                    "clearance_count": year_data.get("cleared", 0),
                                    "rtcc_year": rtcc_year,
                                    "post_rtcc": year >= rtcc_year,
                                    "data_source": "fbi_cde",
                                })

            except Exception as e:
                logger.error(f"Failed to fetch data for {city}: {e}")
                # Continue with other cities

        # Create DataFrame
        df = pd.DataFrame(results)

        if df.empty:
            logger.warning("No data retrieved for any RTCC city")
            return df

        # Compute clearance rate
        df["clearance_count"] = pd.to_numeric(df["clearance_count"], errors="coerce")
        df["homicide_count"] = pd.to_numeric(df["homicide_count"], errors="coerce")
        df["clearance_rate"] = np.where(
            df["homicide_count"].fillna(0) > 0,
            df["clearance_count"].fillna(0) / df["homicide_count"],
            np.nan,
        )

        # Sort by city and year
        df = df.sort_values(["city", "year"]).reset_index(drop=True)

        logger.info(f"Fetched {len(df)} city-year observations for {df['city'].nunique()} cities")

        return df

    # ============ Sync Wrapper for Convenience ============

    def fetch_all_rtcc_cities_sync(
        self,
        start_year: int = DEFAULT_START_YEAR,
        end_year: int = DEFAULT_END_YEAR,
        use_cache: bool = True,
    ) -> pd.DataFrame:
        """Synchronous wrapper for fetch_all_rtcc_cities."""
        return asyncio.run(self.fetch_all_rtcc_cities(start_year, end_year, use_cache))


# ============ CLI Interface ============

def main():
    """CLI interface for testing the API client."""
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Crime Data API Client")
    parser.add_argument("--test", action="store_true", help="Test API connectivity")
    parser.add_argument("--fetch", action="store_true", help="Fetch all RTCC city data")
    parser.add_argument("--output", type=str, help="Output CSV path")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    client = UnifiedCrimeDataClient()

    if args.test:
        print("Testing API connectivity...")

        # Test FBI API
        if client.fbi_api_key:
            print("✓ FBI API key configured")
            try:
                participation = asyncio.run(client.get_national_participation())
                print(f"✓ FBI CDE API reachable: {len(participation.get('data', []))} records")
            except Exception as e:
                print(f"✗ FBI CDE API error: {e}")
        else:
            print("✗ FBI API key missing (get one at https://api.data.gov/signup/)")

        # Test BJS API
        try:
            clearance = asyncio.run(client.get_bjs_clearance(2020))
            if clearance:
                print("✓ BJS NIBRS API reachable")
            else:
                print("? BJS NIBRS API returned empty (may be rate limited)")
        except Exception as e:
            print(f"? BJS NIBRS API: {e}")

        # Test ICPSR API
        if client.icpsr_api_key:
            try:
                study = asyncio.run(client.get_icpsr_study("39069"))
                if study:
                    print("✓ ICPSR API reachable")
                else:
                    print("? ICPSR API returned empty")
            except Exception as e:
                print(f"? ICPSR API: {e}")
        else:
            print("✗ ICPSR API key not configured")

    elif args.fetch:
        print("Fetching data for all 8 RTCC cities...")
        df = client.fetch_all_rtcc_cities_sync()

        if args.output:
            df.to_csv(args.output, index=False)
            print(f"Saved {len(df)} observations to {args.output}")
        else:
            print(df.to_string())

        # Print summary
        print("\n" + "=" * 50)
        print("DATA SUMMARY")
        print("=" * 50)
        print(f"Total observations: {len(df)}")
        print(f"Cities: {', '.join(df['city'].unique())}")
        print(f"Year range: {df['year'].min()} - {df['year'].max()}")
        print(f"Total homicides: {df['homicide_count'].sum()}")
        print(f"Total cleared: {df['clearance_count'].sum()}")
        print(f"Mean clearance rate: {df['clearance_rate'].mean():.2%}")

    else:
        parser.print_help()


RTCC_ORIS = UnifiedCrimeDataClient.RTCC_ORIS


if __name__ == "__main__":
    main()
