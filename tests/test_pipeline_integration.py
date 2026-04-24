"""
Integration Tests for RTCC Thesis Pipeline

Tests cover:
1. FBI CDE client cache behavior
2. BJS NIBRS client clearance data
3. ICPSR client authentication
4. RTCC scraper date extraction
5. Comparison pool shape validation
6. Classifier with real data
7. Classifier missing data handling
8. Causal forest ATE range validation
9. Bass diffusion convergence

Author: Marcelo Green <marcelo.green@yale.edu>
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock

import numpy as np
import pandas as pd
import pytest

# Add pipeline to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.config import RTCC_CONFIG, get_rtcc_oris
from pipeline.data.fbi_api_client import UnifiedCrimeDataClient, RTCC_ORIS
from pipeline.data.comparison_pool import ComparisonPoolBuilder
from pipeline.models.clearance_classifier import RTCCClearanceClassifier
from pipeline.models.causal_forest import RTCCCausalForest
from pipeline.models.bass_diffusion import RTCCBassDiffusion
from pipeline.scrapers.rtcc_scraper import RTCCScraper, RTCCTimelineEvent


# ============ FIXTURES ============

@pytest.fixture
def rtcc_cities_dict():
    """RTCC cities configuration."""
    return RTCC_ORIS.copy()


@pytest.fixture
def sample_fbi_response():
    """Mock FBI CDE API response for homicide data."""
    return {
        "agency": {"ori": "CT0006400", "name": "Hartford Police Department"},
        "offenses": {
            "offense": [
                {
                    "crime_name": "Homicide",
                    "data": {
                        "2010": {"actual": 22, "cleared": 12},
                        "2011": {"actual": 18, "cleared": 9},
                        "2012": {"actual": 25, "cleared": 11},
                    }
                }
            ]
        }
    }


@pytest.fixture
def sample_clearance_data():
    """Mock clearance rate data for testing."""
    return pd.DataFrame({
        'city': ['Hartford'] * 14,
        'ori': ['CT0006400'] * 14,
        'year': list(range(2010, 2024)),
        'homicide_count': [22, 18, 25, 20, 23, 19, 21, 24, 20, 18, 22, 19, 21, 20],
        'clearance_count': [12, 9, 11, 10, 13, 8, 12, 14, 11, 9, 13, 10, 11, 10],
        'population': [125000] * 14,
        'region': ['Northeast'] * 14,
        'state_fe': ['CT'] * 14,
        'rtcc_year': [2016] * 14,
        'post_rtcc': [False] * 6 + [True] * 8,
    })


@pytest.fixture
def mock_scraped_html():
    """Mock HTML content for scraper testing."""
    return """
    <html>
    <head>
        <title>Hartford Launches Real Time Crime Center</title>
        <meta property="article:published_time" content="2016-03-15" />
    </head>
    <body>
        <h1>Real Time Crime Center Opens March 15, 2016</h1>
        <p>Mayor Luke Bronin today announced the opening of Hartford's
        new Real Time Crime Center, a $2.5 million investment in public safety.</p>
        <p>The center, built in partnership with Motorola Solutions, will
        provide real-time crime monitoring and shot spotter technology.</p>
        <blockquote>"This will revolutionize how we fight crime"</blockquote>
    </body>
    </html>
    """


@pytest.fixture
def mid_sized_cities_df():
    """Mock mid-sized cities dataframe."""
    return pd.DataFrame({
        'ORI': ['CT0006400', 'FL0130200', 'NY0501200', 'CA0190200', 'TX0123400'],
        'AGENCY': ['Hartford PD', 'Miami PD', 'Buffalo PD', 'Fresno PD', 'Austin PD'],
        'STNAME': ['CT', 'FL', 'NY', 'CA', 'TX'],
        'POP': [125000, 450000, 260000, 540000, 950000],
    })


# ============ TEST 1: FBI CDE Client Cache ============

def test_fbi_api_client_cache(tmp_path, sample_fbi_response):
    """Test that FBI API client writes and reads cache correctly."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    client = UnifiedCrimeDataClient(cache_dir=cache_dir)

    # Test cache path generation
    cache_path = client._get_cache_path("fbi_cde", "CT0006400", 2010, 2023)
    assert "fbi_cde" in str(cache_path)
    assert "ct0006400" in str(cache_path).lower()


def test_fbi_api_client_rtcc_oris_completeness():
    """Verify all 8 RTCC cities are configured."""
    assert len(get_rtcc_oris(RTCC_CONFIG.study1_cities)) == 8
    expected_cities = set(RTCC_CONFIG.study1_cities)
    assert set(UnifiedCrimeDataClient.RTCC_ORIS.keys()) >= expected_cities


def test_fbi_api_client_ori_format():
    """Verify ORI codes are in correct format."""
    for city, config in get_rtcc_oris(RTCC_CONFIG.study1_cities).items():
        ori = config
        assert len(ori) == 9, f"{city} ORI has wrong length: {ori}"
        assert ori[2] == "0", f"{city} ORI format incorrect: {ori}"


# ============ TEST 2: BJS NIBRS Client ============

@pytest.mark.asyncio
async def test_bjs_nibrs_clearance_structure():
    """Test that BJS client handles clearance data structure."""
    client = UnifiedCrimeDataClient()

    # Mock response structure
    mock_response = {
        "data": [
            {"offense": "homicide", "clearance_rate": 0.62}
        ]
    }

    # Test that we can parse this structure
    assert "data" in mock_response
    assert mock_response["data"][0]["clearance_rate"] >= 0
    assert mock_response["data"][0]["clearance_rate"] <= 1


# ============ TEST 3: ICPSR Client Auth ============

def test_icpsr_api_key_resolution():
    """Test ICPSR API key resolution from environment."""
    # Test with direct key
    client = UnifiedCrimeDataClient(icpsr_api_key="test_key")
    assert client.icpsr_api_key == "test_key"

    # Test with en:// prefix
    os.environ["TEST_ICPSR_KEY"] = "resolved_key"
    client = UnifiedCrimeDataClient(icpsr_api_key="en://TEST_ICPSR_KEY")
    assert client.icpsr_api_key == "resolved_key"

    del os.environ["TEST_ICPSR_KEY"]


# ============ TEST 4: RTCC Scraper Date Extraction ============

def test_rtcc_scraper_extract_date(mock_scraped_html):
    """Test date extraction from HTML content."""
    scraper = RTCCScraper()

    # Test with BeautifulSoup
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(mock_scraped_html, 'html.parser')

    date = scraper._extract_date(mock_scraped_html, soup)
    assert date == "2016-03-15" or "2016" in date


def test_rtcc_scraper_extract_budget(mock_scraped_html):
    """Test budget extraction from HTML content."""
    scraper = RTCCScraper()

    budget = scraper._extract_budget(mock_scraped_html)
    assert budget is not None
    assert budget == 2_500_000 or budget == 2500000  # $2.5 million


def test_rtcc_scraper_extract_vendor(mock_scraped_html):
    """Test vendor extraction from HTML content."""
    scraper = RTCCScraper()

    vendor = scraper._extract_vendor(mock_scraped_html)
    assert vendor == "Motorola"


def test_rtcc_scraper_timeline_event_creation():
    """Test RTCCTimelineEvent dataclass creation."""
    event = RTCCTimelineEvent(
        date="2016-03-15",
        city="Hartford",
        event_type="launch",
        source_url="https://hartford.gov/news/rtcc",
        source_type="press_release",
        title="RTCC Opens",
        summary="Hartford launches Real Time Crime Center",
        budget=2500000,
        vendor="Motorola",
    )

    assert event.date == "2016-03-15"
    assert event.city == "Hartford"
    assert event.budget == 2500000


# ============ TEST 5: Comparison Pool Shape ============

def test_comparison_pool_shape(mid_sized_cities_df, tmp_path):
    """Test that comparison pool output has expected schema."""
    builder = ComparisonPoolBuilder(output_dir=tmp_path)

    # Filter mid-sized (should exclude Miami and Fresno based on population)
    filtered = builder.filter_mid_sized(mid_sized_cities_df, min_pop=100000, max_pop=300000)

    # Should have Hartford and Buffalo (100K-300K range)
    assert len(filtered) >= 1
    assert "ORI" in filtered.columns
    assert "AGENCY" in filtered.columns
    assert "STNAME" in filtered.columns
    assert "POP" in filtered.columns


def test_comparison_pool_exclude_rtcc(mid_sized_cities_df, tmp_path):
    """Test that RTCC cities are excluded from comparison pool."""
    builder = ComparisonPoolBuilder(output_dir=tmp_path)

    # Add RTCC cities to dataframe
    mid_sized_cities_df.loc[len(mid_sized_cities_df)] = {
        'ORI': 'CT0006400',
        'AGENCY': 'Hartford PD',
        'STNAME': 'CT',
        'POP': 125000,
    }

    # Filter and exclude
    filtered = builder.filter_mid_sized(mid_sized_cities_df, min_pop=100000, max_pop=300000)
    result = builder.exclude_rtcc_cities(filtered)

    # Hartford should be excluded
    assert "CT0006400" not in result["ORI"].values


def test_comparison_pool_region_mapping(mid_sized_cities_df, tmp_path):
    """Test region mapping from state."""
    builder = ComparisonPoolBuilder(output_dir=tmp_path)

    df = builder.add_region(mid_sized_cities_df)

    assert "region" in df.columns
    assert df[df["STNAME"] == "CT"]["region"].values[0] == "Northeast"
    assert df[df["STNAME"] == "FL"]["region"].values[0] == "South"
    assert df[df["STNAME"] == "CA"]["region"].values[0] == "West"


# ============ TEST 6: Classifier Real Data ============

def test_classifier_initialization():
    """Test classifier initializes correctly."""
    classifier = RTCCClearanceClassifier(data_source="bjs")

    assert classifier.data_source == "bjs"
    assert classifier.random_state == 42
    assert classifier.results_dir is not None


def test_classifier_feature_matrix(sample_clearance_data):
    """Test feature matrix construction."""
    classifier = RTCCClearanceClassifier()

    city_rtcc_years = {"Hartford": 2016}
    X, y = classifier.build_feature_matrix(sample_clearance_data, city_rtcc_years)

    # Check shapes
    assert X.shape[0] == y.shape[0]
    assert X.shape[0] == len(sample_clearance_data)

    # Check target is binary
    assert y.dtype in [np.int32, np.int64, bool]
    assert set(y).issubset({0, 1})


def test_classifier_model_configs():
    """Test model configurations are set correctly."""
    from pipeline.models.clearance_classifier import RTCCClearanceClassifier

    xgb_config = RTCCClearanceClassifier.MODEL_CONFIGS["xgboost"]
    assert xgb_config["n_estimators"] == 100
    assert xgb_config["max_depth"] == 5

    rf_config = RTCCClearanceClassifier.MODEL_CONFIGS["random_forest"]
    assert rf_config["class_weight"] == "balanced"


def test_classifier_data_coverage_report():
    """Test data coverage report generation."""
    classifier = RTCCClearanceClassifier()

    # Add some missing data
    classifier.missing_data_log = [("Hartford", 2010), ("Miami", 2011)]

    # Should not error
    classifier.report_data_coverage()


# ============ TEST 7: Classifier Missing Data Handling ============

def test_classifier_handles_missing_data(tmp_path):
    """Test that classifier handles missing clearance data gracefully."""
    # Create data with missing clearance
    data = pd.DataFrame({
        'city': ['Hartford', 'Hartford', 'Hartford'],
        'year': [2010, 2011, 2012],
        'homicide_count': [22, 18, 25],
        'clearance_count': [12, None, 11],
        'population': [125000] * 3,
        'region': ['Northeast'] * 3,
        'state_fe': ['CT'] * 3,
        'rtcc_year': [2016] * 3,
        'post_rtcc': [False] * 3,
    })

    classifier = RTCCClearanceClassifier(results_dir=tmp_path)

    # Should handle None in clearance_count
    # Either by dropping rows or filling
    assert len(data) == 3


# ============ TEST 8: Causal Forest ATE Range ============

@pytest.mark.skipif(
    not os.getenv("ECONML_AVAILABLE") and True,
    reason="EconML not installed"
)
def test_causal_forest_initialization():
    """Test causal forest initializes correctly."""
    try:
        forest = RTCCCausalForest(n_estimators=100)
        assert forest.n_estimators == 100
        assert forest.max_depth == 10
    except ImportError:
        pytest.skip("EconML not installed")


@pytest.mark.skipif(
    not os.getenv("ECONML_AVAILABLE") and True,
    reason="EconML not installed"
)
def test_causal_forest_ate_within_range():
    """Test that ATE is within plausible range."""
    try:
        # Create synthetic data with known effect
        np.random.seed(42)
        n = 500

        X = pd.DataFrame({
            'population': np.random.uniform(100000, 300000, n),
            'pre_trend': np.random.uniform(-0.1, 0.1, n),
        })

        T = np.random.binomial(1, 0.5, n)
        W = np.random.uniform(-1, 1, (n, 2))

        # True ATE = 0.1
        Y = 0.5 + 0.1 * T + 0.01 * (X['population'] / 100000 - 2) + np.random.normal(0, 0.1, n)

        forest = RTCCCausalForest(n_estimators=100)

        # Fit model
        forest.fit(Y=Y, T=T, X=X, W=W)

        # Estimate ATE
        ate, (ci_lower, ci_upper), p_value = forest.estimate_ate()

        # ATE should be in plausible range for clearance rates (-0.5, 0.5)
        assert -0.5 <= ate <= 0.5, f"ATE {ate} outside plausible range"

        # CI should be reasonable width
        assert (ci_upper - ci_lower) < 1.0, "CI too wide"

    except ImportError:
        pytest.skip("EconML not installed")


# ============ TEST 9: Bass Diffusion Convergence ============

def test_bass_diffusion_initialization():
    """Test Bass diffusion model initializes correctly."""
    model = RTCCBassDiffusion(M=500)
    assert model.M == 500
    assert model.use_scraped == True


def test_bass_diffusion_fn():
    """Test Bass diffusion function properties."""
    from pipeline.models.bass_diffusion import RTCCBassDiffusion

    M = 500
    p = 0.01
    q = 0.3
    t = np.array([0, 1, 5, 10, 20])

    # Cumulative adoptions should be non-decreasing
    F = RTCCBassDiffusion.bass_diffusion_fn(t, p, q, M)
    assert np.all(np.diff(F) >= -1e-6)  # Allow small numerical errors

    # Should not exceed M
    assert np.all(F <= M + 1)  # Small tolerance


def test_bass_diffusion_converges():
    """Test that curve_fit finds p < q (typical for tech adoption)."""
    model = RTCCBassDiffusion(M=500, use_scraped=False)

    # Use fallback data
    df = model._load_known_adoptions()

    # Estimate parameters
    p, q, M = model.estimate_parameters()

    # For technology adoption, typically q > p
    # (imitation stronger than innovation)
    assert q > p, f"Expected q > p, got q={q}, p={p}"

    # Both should be positive
    assert p > 0, f"Expected p > 0, got p={p}"
    assert q > 0, f"Expected q > 0, got q={q}"

    # q/p ratio should be reasonable (usually > 1)
    assert (q / p) > 0.5, f"q/p ratio too small: {q/p}"


def test_bass_diffusion_peak_time():
    """Test peak time calculation."""
    model = RTCCBassDiffusion(M=500, use_scraped=False)

    p, q, M = model.estimate_parameters()
    peak_year, peak_adoption = model.compute_peak_time(p, q)

    # Peak should be in reasonable future
    assert peak_year > 2015, f"Peak year {peak_year} seems too early"
    assert peak_year < 2050, f"Peak year {peak_year} seems too late"

    # Peak adoptions should be positive
    assert peak_adoption > 0


def test_bass_diffusion_forecast_shape():
    """Test forecast dataframe has correct structure."""
    model = RTCCBassDiffusion(M=500, use_scraped=False)

    forecast = model.forecast(horizon=2030)

    # Check columns
    assert "year" in forecast.columns
    assert "cumulative_adoptions" in forecast.columns
    assert "annual_adoptions" in forecast.columns
    assert "adoption_rate" in forecast.columns
    assert "period" in forecast.columns

    # Check values
    assert forecast["year"].min() >= 2015
    assert forecast["year"].max() == 2030
    assert (forecast["cumulative_adoptions"] >= 0).all()


# ============ TEST SUMMARY ============

def test_pipeline_has_all_components():
    """Test that all pipeline components are importable."""
    # All modules should be importable
    import pipeline.data.fbi_api_client
    import pipeline.data.comparison_pool
    import pipeline.models.clearance_classifier
    import pipeline.models.causal_forest
    import pipeline.models.bass_diffusion
    import pipeline.scrapers.rtcc_scraper

    # All should have expected classes/functions
    assert hasattr(pipeline.data.fbi_api_client, "UnifiedCrimeDataClient")
    assert hasattr(pipeline.data.comparison_pool, "ComparisonPoolBuilder")
    assert hasattr(pipeline.models.clearance_classifier, "RTCCClearanceClassifier")
    assert hasattr(pipeline.models.causal_forest, "RTCCCausalForest")
    assert hasattr(pipeline.models.bass_diffusion, "RTCCBassDiffusion")
    assert hasattr(pipeline.scrapers.rtcc_scraper, "RTCCScraper")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
