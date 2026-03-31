"""
Comparison Pool Builder for RTCC Thesis Pipeline

Builds a control group of mid-sized US cities (100K-300K population)
that did not adopt RTCCs, for use in causal analysis.

Data Sources:
- ICPSR 39063: Arrests by Age/Sex/Race
- FBI CDE API: Real-time agency data
- mid_sized_cities.csv: Base city list
- Scraped RTCC data: For exclusion verification

Author: Marcelo Green <marcelo.green@yale.edu>
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.linear_model import LinearRegression

load_dotenv()

logger = logging.getLogger(__name__)


# State to region mapping
STATE_TO_REGION = {
    # Northeast
    "CT": "Northeast", "MA": "Northeast", "NY": "Northeast", "NJ": "Northeast",
    "PA": "Northeast", "RI": "Northeast", "VT": "Northeast", "NH": "Northeast", "ME": "Northeast",
    # Midwest
    "IL": "Midwest", "OH": "Midwest", "MI": "Midwest", "MO": "Midwest",
    "WI": "Midwest", "MN": "Midwest", "IA": "Midwest", "KS": "Midwest",
    "NE": "Midwest", "SD": "Midwest", "ND": "Midwest",
    # South
    "FL": "South", "GA": "South", "LA": "South", "TX": "South",
    "NC": "South", "SC": "South", "AL": "South", "MS": "South",
    "TN": "South", "KY": "South", "AR": "South", "OK": "South",
    "VA": "South", "WV": "South", "DC": "South", "DE": "South", "MD": "South",
    # West
    "CA": "West", "WA": "West", "OR": "West", "AZ": "West",
    "NV": "West", "CO": "West", "NM": "West", "UT": "West",
    "ID": "West", "MT": "West", "WY": "West", "AK": "West", "HI": "West",
}


# RTCC cities to exclude
RTCC_CITIES = {
    "Hartford": {"ori": "CT0030100"},
    "Miami": {"ori": "FL0130200"},
    "St. Louis": {"ori": "MO0640000"},
    "Newark": {"ori": "NJ0071400"},
    "New Orleans": {"ori": "LA0360000"},
    "Albuquerque": {"ori": "NM0010100"},
    "Fresno": {"ori": "CA0190200"},
    "Chicago": {"ori": "IL0160000"},
}


class ComparisonPoolBuilder:
    """
    Builds comparison city pool from UCR data.

    Target: 371 mid-sized agencies (100K-300K population)
    Excludes: 8 RTCC treatment cities + any scraped RTCC cities
    Years: 2010-2023
    """

    def __init__(
        self,
        ucr_path: Optional[str] = None,
        mid_sized_path: Optional[str] = None,
        output_dir: Optional[Path] = None,
        scraped_rtcc_cities: Optional[Set[str]] = None,
    ):
        """
        Initialize the comparison pool builder.

        Args:
            ucr_path: Path to ICPSR 39063 data (or uses UCR_ARRESTS_PATH env var)
            mid_sized_path: Path to mid_sized_cities.csv
            output_dir: Output directory for processed data
            scraped_rtcc_cities: Additional cities to exclude (from scraping)
        """
        # Resolve paths
        if ucr_path is None:
            ucr_path = os.getenv("UCR_ARRESTS_PATH")
        self.ucr_path = ucr_path

        if mid_sized_path is None:
            mid_sized_path = Path(__file__).parent.parent.parent / "thesis" / "Thesis Files" / "mid_sized_cities.csv"
        self.mid_sized_path = Path(mid_sized_path)

        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "data" / "processed"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # RTCC cities to exclude
        self.rtcc_oris = {city_data["ori"] for city_data in RTCC_CITIES.values()}
        self.scraped_rtcc_cities = scraped_rtcc_cities or set()

        logger.info(f"Initialized ComparisonPoolBuilder")
        logger.info(f"Output directory: {self.output_dir}")

    def load_mid_sized_cities(self) -> pd.DataFrame:
        """Load the mid-sized cities reference file."""
        logger.info(f"Loading mid-sized cities from {self.mid_sized_path}")

        if not self.mid_sized_path.exists():
            logger.warning(f"mid_sized_cities.csv not found at {self.mid_sized_path}")
            return pd.DataFrame()

        df = pd.read_csv(self.mid_sized_path)
        logger.info(f"Loaded {len(df)} mid-sized cities")
        return df

    def load_ucr_data(self) -> pd.DataFrame:
        """
        Load UCR arrest data.

        This is a placeholder - in production, you would:
        1. Read from ICPSR 39063 file if UCR_ARRESTS_PATH is set
        2. Or fetch via FBI CDE API for agencies not in local data
        3. Or use the mid_sized_cities.csv as the base
        """
        logger.info("Loading UCR data")

        # For now, use mid_sized_cities.csv as the base
        df = self.load_mid_sized_cities()

        if df.empty:
            logger.warning("No UCR data available")
            return pd.DataFrame()

        # Ensure required columns exist
        required_cols = ["ORI", "AGENCY", "STNAME", "POP"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return pd.DataFrame()

        # Clean population column
        if "POP" in df.columns:
            df["POP"] = pd.to_numeric(df["POP"], errors="coerce")

        return df

    def filter_mid_sized(
        self, df: pd.DataFrame, min_pop: int = 100000, max_pop: int = 300000
    ) -> pd.DataFrame:
        """
        Filter to mid-sized agencies.

        Args:
            df: Input dataframe
            min_pop: Minimum population (default: 100K)
            max_pop: Maximum population (default: 300K)

        Returns:
            Filtered dataframe
        """
        logger.info(f"Filtering to population {min_pop:,} - {max_pop:,}")

        df = df[
            (df["POP"] >= min_pop) & (df["POP"] <= max_pop)
        ].copy()

        logger.info(f"After population filter: {len(df)} agencies")
        return df

    def exclude_rtcc_cities(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Exclude RTCC treatment cities.

        Also excludes any cities found in scraping.
        """
        initial_count = len(df)

        # Exclude by ORI
        df = df[~df["ORI"].isin(self.rtcc_oris)]

        # Exclude by scraped city names
        if self.scraped_rtcc_cities:
            df = df[~df["AGENCY"].str.contains("|".join(self.scraped_rtcc_cities), case=False, na=False)]

        excluded = initial_count - len(df)
        logger.info(f"Excluded {excluded} RTCC cities")
        return df

    def add_region(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add region column based on state."""
        if "STNAME" in df.columns:
            df["region"] = df["STNAME"].map(STATE_TO_REGION)
            unknown_regions = df["region"].isna().sum()
            if unknown_regions > 0:
                logger.warning(f"{unknown_regions} agencies have unknown region")
        else:
            logger.warning("STNAME column not found, cannot add region")
            df["region"] = "Unknown"

        return df

    def compute_features(self, df: pd.DataFrame, start_year: int = 2010, end_year: int = 2023) -> pd.DataFrame:
        """
        Compute features for comparison pool.

        Features:
        - pre_2015_homicide_trend: Linear regression slope of homicide rates (2010-2014)
        - population_2015: Population in 2015 (or nearest year)
        - region: Census region
        - state_fe: State identifier for fixed effects
        - data_quality_score: Based on reporting completeness
        """
        logger.info("Computing features for comparison pool")

        # For this implementation, we'll create a basic feature set
        # In production, you would compute actual trends from time-series data

        # Add region
        df = self.add_region(df)

        # Add state FE
        df["state_fe"] = df["STNAME"] if "STNAME" in df.columns else "Unknown"

        # Placeholder: In production, compute from actual crime data
        # For now, set defaults
        df["pre_2015_homicide_trend"] = 0.0
        df["population_2015"] = df.get("POP", 100000)
        df["data_quality_score"] = 1.0

        return df

    def export_pool(self, df: pd.DataFrame, filename: str = "comparison_pool.parquet") -> Path:
        """Export comparison pool to parquet file."""
        output_path = self.output_dir / filename
        df.to_parquet(output_path, index=False)
        logger.info(f"Exported {len(df)} agencies to {output_path}")
        return output_path

    def print_summary(self, df: pd.DataFrame):
        """Print summary statistics."""
        print("\n" + "=" * 50)
        print("COMPARISON POOL SUMMARY")
        print("=" * 50)
        print(f"Total agencies: {len(df)}")
        print(f"Total states: {df['STNAME'].nunique()}")
        print(f"Population range: {df['POP'].min():,.0f} - {df['POP'].max():,.0f}")

        print("\nRegion distribution:")
        if "region" in df.columns:
            for region, count in df["region"].value_counts().items():
                print(f"  {region}: {count}")

        print("\nTop 10 states by agency count:")
        if "STNAME" in df.columns:
            for state, count in df["STNAME"].value_counts().head(10).items():
                print(f"  {state}: {count}")

    def build(
        self,
        min_pop: int = 100000,
        max_pop: int = 300000,
        start_year: int = 2010,
        end_year: int = 2023,
    ) -> pd.DataFrame:
        """
        Build the complete comparison pool.

        Args:
            min_pop: Minimum population threshold
            max_pop: Maximum population threshold
            start_year: Start year for analysis
            end_year: End year for analysis

        Returns:
            Comparison pool dataframe
        """
        logger.info("Building comparison pool")

        # Load data
        df = self.load_ucr_data()

        if df.empty:
            logger.error("No data loaded, cannot build comparison pool")
            return pd.DataFrame()

        # Filter to mid-sized
        df = self.filter_mid_sized(df, min_pop, max_pop)

        # Exclude RTCC cities
        df = self.exclude_rtcc_cities(df)

        # Compute features
        df = self.compute_features(df, start_year, end_year)

        # Export
        self.export_pool(df)

        # Print summary
        self.print_summary(df)

        return df


def main():
    """CLI interface for comparison pool builder."""
    import argparse

    parser = argparse.ArgumentParser(description="Build RTCC Comparison Pool")
    parser.add_argument("--ucr-path", type=str, help="Path to UCR data")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--min-pop", type=int, default=100000, help="Minimum population")
    parser.add_argument("--max-pop", type=int, default=300000, help="Maximum population")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    builder = ComparisonPoolBuilder(
        ucr_path=args.ucr_path,
        output_dir=args.output,
    )

    df = builder.build(min_pop=args.min_pop, max_pop=args.max_pop)

    if df.empty:
        print("No comparison pool built")
    else:
        print(f"\nBuilt comparison pool with {len(df)} agencies")


if __name__ == "__main__":
    main()
