"""
Bass Diffusion Model for RTCC Adoption Forecasting

Models the spread of RTCC adoption across US cities using Bass diffusion.
Uses scraped RTCC launch dates (with hardcoded fallback).

Bass equation: F(t) = M * (1 - exp(-(p+q)t) / (1 + (q/p)*exp(-(p+q)t))
- p: coefficient of innovation (external influence)
- q: coefficient of imitation (internal influence)
- M: total market size

Author: Marcelo Green <marcelo.green@yale.edu>
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from dotenv import load_dotenv

# Local imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scrapers.rtcc_scraper import RTCCScraper

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class BassResults:
    """Container for Bass diffusion results."""
    p: float  # Innovation coefficient
    q: float  # Imitation coefficient
    M: int  # Total market size
    mape: float  # Mean absolute percentage error
    peak_time: float  # Year of peak adoption rate
    peak_adoption: int  # Number of adoptions at peak
    forecast: pd.DataFrame  # Adoption forecast through horizon


class RTCCBassDiffusion:
    """
    Bass diffusion model for RTCC adoption forecasting.

    Known adoptions (from advisor deck or scraping):
    - 2015: St. Louis
    - 2016: Hartford, Miami
    - 2017: New Orleans, Chicago
    - 2018: Newark, Fresno
    - 2020: Albuquerque

    Assumes total market M ≈ 500 mid-sized US cities eligible for RTCC.
    """

    # Hardcoded fallback adoption timeline (from advisor deck)
    FALLBACK_ADOPTIONS = {
        2015: 1,  # St. Louis
        2016: 3,  # + Hartford, Miami
        2017: 5,  # + New Orleans, Chicago
        2018: 7,  # + Newark, Fresno
        2019: 7,  # No new adoptions
        2020: 8,  # + Albuquerque
        2021: 8,
        2022: 8,
        2023: 8,
    }

    def __init__(
        self,
        M: int = 500,
        results_dir: Optional[Path] = None,
        use_scraped: bool = True,
    ):
        """
        Initialize the Bass diffusion model.

        Args:
            M: Total market size (potential adopters)
            results_dir: Where to save outputs
            use_scraped: Whether to use scraped RTCC dates (vs hardcoded)
        """
        self.M = M

        if results_dir is None:
            results_dir = Path(__file__).parent.parent.parent / "results" / "study2_dfr"
        self.results_dir = Path(results_dir)

        # Create output directories
        (self.results_dir / "figures" / "adoption").mkdir(parents=True, exist_ok=True)
        (self.results_dir / "tables").mkdir(parents=True, exist_ok=True)

        self.use_scraped = use_scraped
        self.adoption_data = None
        self.results = None

        logger.info(f"Initialized RTCCBassDiffusion with M={M}")

    def _load_scraped_adoptions(self) -> Dict[int, int]:
        """
        Load scraped RTCC adoption dates.

        Returns:
            Dict mapping year to cumulative adoptions
        """
        logger.info("Loading scraped RTCC adoptions")

        scraper = RTCCScraper()
        timeline = scraper.load_scraped_timeline()

        if not timeline:
            logger.warning("No scraped timeline found, using fallback")
            return self.FALLBACK_ADOPTIONS

        # Convert timeline to cumulative adoptions by year
        adoptions_by_year = {}

        for city, info in timeline.items():
            if info.launch_date:
                year = int(info.launch_date[:4])
                adoptions_by_year[year] = adoptions_by_year.get(year, 0) + 1

        # Make cumulative
        years = sorted(adoptions_by_year.keys())
        cumulative = 0
        cumulative_by_year = {}

        for year in range(min(years), max(years) + 1):
            if year in adoptions_by_year:
                cumulative += adoptions_by_year[year]
            cumulative_by_year[year] = cumulative

        # Fill in recent years with no new adoptions
        last_year = max(cumulative_by_year.keys())
        for year in range(last_year, 2024):
            cumulative_by_year[year] = cumulative

        logger.info(f"Loaded scraped adoptions: {cumulative_by_year}")
        return cumulative_by_year

    def _load_known_adoptions(self) -> pd.DataFrame:
        """
        Load known RTCC adoptions (from scraping or fallback).

        Returns:
            DataFrame with columns [year, cumulative_adoptions]
        """
        if self.use_scraped:
            try:
                adoptions = self._load_scraped_adoptions()
            except Exception as e:
                logger.warning(f"Failed to load scraped adoptions: {e}")
                adoptions = self.FALLBACK_ADOPTIONS
        else:
            adoptions = self.FALLBACK_ADOPTIONS

        df = pd.DataFrame([
            {"year": year, "cumulative_adoptions": count}
            for year, count in adoptions.items()
        ])

        df = df.sort_values("year").reset_index(drop=True)
        self.adoption_data = df

        logger.info(f"Loaded {len(df)} years of adoption data")
        return df

    @staticmethod
    def bass_diffusion_fn(t: np.ndarray, p: float, q: float, M: float) -> np.ndarray:
        """
        Bass diffusion cumulative adoption function.

        F(t) = M * (1 - exp(-(p+q)t) / (1 + (q/p)*exp(-(p+q)t)))

        Args:
            t: Time (years since first adoption)
            p: Innovation coefficient (external influence)
            q: Imitation coefficient (internal influence)
            M: Total market size

        Returns:
            Cumulative adoptions at time t
        """
        # Avoid division by zero
        p = max(p, 1e-6)

        pt = (p + q) * t
        ratio = q / p

        numerator = np.exp(-pt)
        denominator = 1 + ratio * np.exp(-pt)

        return M * (1 - numerator / denominator)

    def bass_rate_fn(self, t: np.ndarray, p: float, q: float, M: float) -> np.ndarray:
        """
        Bass diffusion adoption rate (annual adoptions).

        f(t) = M * (p^2/q) * exp(-(p+q)t) / (1 + (q/p)*exp(-(p+q)t))^2

        Args:
            t: Time (years since first adoption)
            p, q, M: Bass parameters

        Returns:
            Annual adoptions at time t
        """
        p = max(p, 1e-6)

        pt = (p + q) * t
        ratio = q / p

        numerator = (p**2 / q) * np.exp(-pt)
        denominator = (1 + ratio * np.exp(-pt)) ** 2

        return M * numerator / denominator

    def estimate_parameters(
        self,
        method: str = "curve_fit",
    ) -> Tuple[float, float, float]:
        """
        Estimate p and q via nonlinear least squares.

        Args:
            method: Optimization method ("curve_fit" or "basinhopping")

        Returns:
            (p, q, M) estimated parameters
        """
        df = self._load_known_adoptions()

        # Time since first adoption
        t0 = df["year"].min()
        t = df["year"].values - t0
        N = df["cumulative_adoptions"].values

        # Initial guesses and bounds
        p0 = [0.01, 0.3, self.M]  # Initial guess: p=0.01, q=0.3
        bounds = (
            [0.001, 0.1, self.M * 0.5],  # Lower bounds
            [0.1, 1.0, self.M * 2],  # Upper bounds
        )

        if method == "curve_fit":
            # Use scipy.optimize.curve_fit
            popt, pcov = curve_fit(
                lambda t, p, q: self.bass_diffusion_fn(t, p, q, self.M),
                t,
                N,
                p0=[0.01, 0.3],  # p, q initial guesses (M is fixed)
                bounds=([0.001, 0.1], [0.1, 1.0]),
                maxfev=10000,
            )
            p_hat, q_hat = popt
            M_hat = self.M

        else:
            raise ValueError(f"Unknown method: {method}")

        # Calculate MAPE
        N_pred = self.bass_diffusion_fn(t, p_hat, q_hat, M_hat)
        mape = np.mean(np.abs((N - N_pred) / (N + 1))) * 100

        logger.info(f"Estimated parameters: p={p_hat:.4f}, q={q_hat:.4f}, M={M_hat}")
        logger.info(f"MAPE: {mape:.2f}%")

        return p_hat, q_hat, M_hat

    def forecast(
        self,
        horizon: int = 2030,
    ) -> pd.DataFrame:
        """
        Generate adoption forecast through horizon year.

        Args:
            horizon: End year for forecast

        Returns:
            DataFrame with columns [year, cumulative_adoptions, annual_adoptions, adoption_rate]
        """
        df = self._load_known_adoptions()

        # Estimate parameters
        p, q, M = self.estimate_parameters()

        # Create forecast range
        t0 = df["year"].min()
        forecast_years = np.arange(t0, horizon + 1)

        # Calculate cumulative and annual adoptions
        t_forecast = forecast_years - t0
        cumulative = self.bass_diffusion_fn(t_forecast, p, q, M)
        annual = self.bass_rate_fn(t_forecast, p, q, M)

        # Build forecast dataframe
        forecast_df = pd.DataFrame({
            "year": forecast_years,
            "cumulative_adoptions": np.round(cumulative).astype(int),
            "annual_adoptions": np.round(annual).astype(int),
            "adoption_rate": np.round(annual / M * 100, 2),
        })

        # Mark historical vs forecast
        historical_years = df["year"].values
        forecast_df["period"] = forecast_df["year"].apply(
            lambda x: "historical" if x in historical_years else "forecast"
        )

        return forecast_df

    def compute_peak_time(self, p: float, q: float) -> Tuple[float, float]:
        """
        Compute time of peak adoption rate.

        t* = ln(q/p) / (p+q)

        Returns:
            (year, peak_adoptions)
        """
        if self.adoption_data is None:
            self._load_known_adoptions()

        t0 = self.adoption_data["year"].min()

        # Time of peak rate
        t_peak = np.log(q / p) / (p + q)
        year_peak = t0 + t_peak

        # Adoptions at peak
        peak_adoptions = self.bass_rate_fn(np.array([t_peak]), p, q, self.M)[0]

        logger.info(f"Peak adoption at year {year_peak:.1f}: {peak_adoptions:.1f} cities/year")

        return year_peak, peak_adoptions

    def plot_adoption_curve(
        self,
        horizon: int = 2030,
    ) -> None:
        """
        Plot Bass diffusion adoption curve.

        Shows:
        - Historical adoptions (scatter)
        - Fitted Bass curve (line)
        - Forecast (dashed line)
        - Peak adoption time (vertical line)
        """
        logger.info("Plotting Bass diffusion adoption curve")

        df = self._load_known_adoptions()
        forecast_df = self.forecast(horizon=horizon)

        # Estimate parameters
        p, q, M = self.estimate_parameters()

        # Compute peak
        peak_year, peak_adoption = self.compute_peak_time(p, q)

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))

        # Historical data
        historical = forecast_df[forecast_df["period"] == "historical"]
        ax.scatter(
            historical["year"],
            historical["cumulative_adoptions"],
            color="blue",
            s=50,
            label="Historical Adoptions",
            zorder=5,
        )

        # Fitted curve (all years)
        ax.plot(
            forecast_df["year"],
            forecast_df["cumulative_adoptions"],
            "r-",
            linewidth=2,
            label="Bass Diffusion Fit",
        )

        # Forecast portion (dashed)
        forecast = forecast_df[forecast_df["period"] == "forecast"]
        if len(forecast) > 0:
            ax.plot(
                forecast["year"],
                forecast["cumulative_adoptions"],
                "r--",
                linewidth=2,
                label="Forecast",
            )

        # Peak line
        ax.axvline(
            peak_year,
            color="green",
            linestyle=":",
            linewidth=2,
            label=f"Peak ({peak_year:.0f})",
        )

        # Market size line
        ax.axhline(
            M,
            color="gray",
            linestyle="-",
            linewidth=1,
            alpha=0.5,
            label=f"Market Size (M={M})",
        )

        # Labels and formatting
        ax.set_xlabel("Year", fontsize=12)
        ax.set_ylabel("Cumulative RTCC Adoptions", fontsize=12)
        ax.set_title("RTCC Adoption: Bass Diffusion Model", fontsize=14)
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)

        # Annotate parameters
        param_text = f"p (innovation) = {p:.4f}\nq (imitation) = {q:.4f}\nq/p = {q/p:.1f}"
        ax.text(
            0.02, 0.98,
            param_text,
            transform=ax.transAxes,
            verticalalignment="top",
            bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
        )

        plt.tight_layout()

        # Save plot
        output_path = self.results_dir / "figures" / "adoption" / "bass_diffusion.png"
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved adoption curve to {output_path}")

    def save_forecast(
        self,
        forecast_df: pd.DataFrame,
        filename: str = "adoption_forecast.csv",
    ) -> None:
        """
        Save forecast to CSV.

        Args:
            forecast_df: Forecast dataframe
            filename: Output filename
        """
        output_path = self.results_dir / "tables" / filename
        forecast_df.to_csv(output_path, index=False)
        logger.info(f"Saved forecast to {output_path}")

    def run_full_analysis(self, horizon: int = 2030) -> BassResults:
        """
        Run complete Bass diffusion analysis.

        Args:
            horizon: Forecast end year

        Returns:
            BassResults with all findings
        """
        logger.info("Running full Bass diffusion analysis")

        # Load data and estimate parameters
        p, q, M = self.estimate_parameters()

        # Generate forecast
        forecast_df = self.forecast(horizon=horizon)

        # Compute peak
        peak_year, peak_adoption = self.compute_peak_time(p, q)

        # Calculate MAPE
        historical = forecast_df[forecast_df["period"] == "historical"]
        if len(historical) > 0:
            mape = np.mean(
                np.abs(
                    (historical["cumulative_adoptions"].values -
                     self.adoption_data["cumulative_adoptions"].values) /
                    (self.adoption_data["cumulative_adoptions"].values + 1)
                )
            ) * 100
        else:
            mape = 0.0

        # Save results
        self.save_forecast(forecast_df)
        self.plot_adoption_curve(horizon=horizon)

        # Create results object
        results = BassResults(
            p=p,
            q=q,
            M=int(M),
            mape=mape,
            peak_time=peak_year,
            peak_adoption=int(peak_adoption),
            forecast=forecast_df,
        )

        self.results = results

        # Print summary
        print("\n" + "=" * 50)
        print("BASS DIFFUSION RESULTS")
        print("=" * 50)
        print(f"Innovation coefficient (p): {p:.4f}")
        print(f"Imitation coefficient (q): {q:.4f}")
        print(f"q/p ratio: {q/p:.1f}")
        print(f"Market size (M): {M}")
        print(f"Peak adoption: Year {peak_year:.0f}, {peak_adoption:.0f} cities")
        print(f"MAPE: {mape:.2f}%")
        print(f"\nForecast for {horizon}: {forecast_df[forecast_df['year'] == horizon]['cumulative_adoptions'].values[0]} cities")

        return results


def main():
    """CLI interface for Bass diffusion model."""
    import argparse

    parser = argparse.ArgumentParser(description="RTCC Bass Diffusion Model")
    parser.add_argument("--M", type=int, default=500, help="Market size (default: 500)")
    parser.add_argument("--horizon", type=int, default=2030, help="Forecast horizon year")
    parser.add_argument("--no-scraped", action="store_true", help="Don't use scraped dates")
    parser.add_argument("--output", type=str, help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    model = RTCCBassDiffusion(
        M=args.M,
        results_dir=args.output,
        use_scraped=not args.no_scraped,
    )

    results = model.run_full_analysis(horizon=args.horizon)


if __name__ == "__main__":
    main()
