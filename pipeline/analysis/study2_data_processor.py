"""
Study 2 Data Integration Processor

Loads raw DFR data from all 3 cities, normalizes metrics,
creates cross-program comparison tables, and maps each data point
to cognitive science framework claims.

Input:
  results/study2_dfr/raw/chula_vista_dfr_data.json
  results/study2_dfr/raw/elizabeth_nj_policy.json
  results/study2_dfr/raw/cincinnati_dfr_data.json
  thesis/literature/cog_sci_framework.md (for theory mapping)

Output:
  results/study2_dfr/processed/dfr_cross_program_comparison.csv
  results/study2_dfr/processed/dfr_response_time_analysis.csv
  results/study2_dfr/processed/cog_sci_benchmark_mapping.csv
  results/study2_dfr/processed/human_benchmark_parameters.json

Author: Marcel Green <marcelo.green@yale.edu>
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DIR = BASE_DIR / "results" / "study2_dfr" / "raw"
PROCESSED_DIR = BASE_DIR / "results" / "study2_dfr" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ── Data Classes ────────────────────────────────────────────────

@dataclass
class DFRComparison:
    """Normalized cross-program comparison record."""
    city: str
    state: str
    launch_date: str
    program_status: str
    vendor: str
    avg_response_time_sec: Optional[float] = None
    avg_flight_time_sec: Optional[float] = None
    total_missions: Optional[int] = None
    successful_missions: Optional[int] = None
    incidents_assisted: Optional[int] = None
    deployment_period: Optional[str] = None
    fleet_size: Optional[int] = None
    coverage_area: Optional[str] = None
    drone_models: Optional[str] = None
    data_quality: str = "secondary"  # "primary", "secondary", "sparse"


@dataclass
class CogSciMapping:
    """Maps a DFR data point to a cognitive science theoretical claim."""
    data_point: str
    city: Optional[str]
    cognitive_theory: str
    key_author: str
    prediction: str
    data_available: bool
    status: str  # "testable", "pending_data", "qualitative"


# ── Human Cognitive Benchmark Parameters ────────────────────────
# Extracted from the 38 verified cog sci papers in thesis/literature/cog_sci_framework.md

HUMAN_BENCHMARK_PARAMETERS = {
    "vigilance_decrement": {
        "parameter": "Time-on-task performance decline",
        "onset_minutes": 20,
        "onset_range": [15, 30],
        "source": "Mackworth (1948); Warm, Parasuraman & Mathews (2008)",
        "relevance": "DFR operator shifts exceeding 20 min should show degraded detection",
        "metric_unit": "minutes",
    },
    "change_blindness": {
        "parameter": "Detection rate for scene changes",
        "rate_percent": 50,
        "rate_range": [30, 70],
        "source": "Head & Helton (2012); Simons & Levin (1997)",
        "relevance": "RTCC operators monitoring multiple feeds miss ~50% of scene changes",
        "metric_unit": "percent detected",
    },
    "sa_failure_rate": {
        "parameter": "Situation awareness Level 2/3 failure",
        "level2_failure_percent": 75,
        "level3_failure_percent": 90,
        "source": "Endsley (1995, 2015); Jones & Endsley (1996)",
        "relevance": "75% of SA failures are comprehension-level; more data ≠ better SA",
        "metric_unit": "percent of total SA errors",
    },
    "intent_attribution_accuracy": {
        "parameter": "Intent inference from ambiguous motion",
        "accuracy_percent": 70,
        "accuracy_range": [55, 85],
        "source": "Heider & Simmel (1944); Berry et al. (2011)",
        "relevance": "Humans attribute intent to geometric shapes — operators will over-attribute intent to ambiguous behavior",
        "metric_unit": "percent correct classification",
    },
    "automaticity_onset": {
        "parameter": "Automatic evaluation activation time",
        "activation_ms": 250,
        "activation_range": [150, 400],
        "source": "Bargh, Chen & Burrows (1996); Ferguson & Bargh (2004)",
        "relevance": "RTCC operators develop automatic threat evaluations within months — may increase false positives",
        "metric_unit": "milliseconds",
    },
    "legitimacy_cooperation": {
        "parameter": "Procedural justice → cooperation effect size",
        "effect_size_r": 0.40,
        "effect_range": [0.30, 0.55],
        "source": "Tyler (1990, 2004); Tyler & Huo (2002)",
        "relevance": "DFR surveillance perceived as illegitimate reduces cooperation by ~40% correlation",
        "metric_unit": "Pearson r",
    },
}


# ── Cognitive Science Benchmark Mapping ─────────────────────────

COG_SCI_MAPPINGS = [
    CogSciMapping(
        data_point="avg_response_time",
        city=None,
        cognitive_theory="Endsley Situation Awareness",
        key_author="Endsley (1995, 2015)",
        prediction="Faster aerial arrival ≠ better situational comprehension. Response time measures detection (SA Level 1), not understanding (SA Level 2).",
        data_available=True,
        status="testable",
    ),
    CogSciMapping(
        data_point="avg_response_time",
        city="Chula Vista",
        cognitive_theory="Endsley SA + Response Time",
        key_author="Endsley (1995)",
        prediction="234 sec avg response is fast for aerial arrival but measures Level 1 only. No data on Level 2/3 outcomes.",
        data_available=True,
        status="testable",
    ),
    CogSciMapping(
        data_point="avg_response_time",
        city="Elizabeth",
        cognitive_theory="Endsley SA + Response Time",
        key_author="Endsley (1995)",
        prediction="94 sec avg response is exceptionally fast — 2.5x faster than Chula Vista. Tests whether speed correlates with mission success.",
        data_available=True,
        status="testable",
    ),
    CogSciMapping(
        data_point="mission_duration",
        city=None,
        cognitive_theory="Mackworth Vigilance Decrement",
        key_author="Mackworth (1948); Warm et al. (2008)",
        prediction="Missions >20 min should show degraded operator performance. Avg flight time 172 sec (Chula Vista) is below threshold — good.",
        data_available=True,
        status="testable",
    ),
    CogSciMapping(
        data_point="total_missions",
        city="Chula Vista",
        cognitive_theory="Bargh Automaticity",
        key_author="Bargh et al. (1996); Ferguson & Bargh (2004)",
        prediction="10,000+ missions means operators have extensive experience — automaticity predicts faster but potentially biased threat evaluation.",
        data_available=True,
        status="testable",
    ),
    CogSciMapping(
        data_point="total_missions",
        city="Elizabeth",
        cognitive_theory="Bargh Automaticity",
        key_author="Bargh et al. (1996)",
        prediction="1,390 deployments in 7 months — moderate experience. Automaticity may not yet be fully developed.",
        data_available=True,
        status="testable",
    ),
    CogSciMapping(
        data_point="geospatial_deployment",
        city=None,
        cognitive_theory="Tyler Procedural Justice",
        key_author="Tyler (1990, 2004, 2008)",
        prediction="Concentrated DFR deployments in specific neighborhoods predict lower perceived legitimacy and reduced community cooperation.",
        data_available=False,
        status="pending_data",
    ),
    CogSciMapping(
        data_point="video_anomaly_detection",
        city=None,
        cognitive_theory="Warm Vigilance + Mackworth",
        key_author="Warm et al. (2008); Guidetti et al. (2023)",
        prediction="AI anomaly detection should show no time-dependent decrement (unlike human operators). If it does, reveals architectural bias.",
        data_available=False,
        status="pending_data",
    ),
    CogSciMapping(
        data_point="skeleton_intent_attribution",
        city=None,
        cognitive_theory="Heider-Simmel Intent Attribution",
        key_author="Heider & Simmel (1944)",
        prediction="PoseC3D classifies actions from skeleton data — tests whether movement patterns alone carry sufficient intent signal.",
        data_available=False,
        status="pending_data",
    ),
    CogSciMapping(
        data_point="event_segmentation_boundaries",
        city=None,
        cognitive_theory="Zacks Event Segmentation",
        key_author="Zacks et al. (2001, 2007)",
        prediction="Self-supervised VideoMAE should discover event boundaries matching human-annotated transitions in surveillance footage.",
        data_available=False,
        status="pending_data",
    ),
    CogSciMapping(
        data_point="operator_experience_vs_success",
        city=None,
        cognitive_theory="Gartenberg Vigilance Modulation",
        key_author="Gartenberg et al. (2018)",
        prediction="Experienced operators maintain vigilance longer — DFR mission success rate should increase with operator tenure.",
        data_available=False,
        status="pending_data",
    ),
    CogSciMapping(
        data_point="cincinnati_expansion_coverage",
        city="Cincinnati",
        cognitive_theory="Tyler Legitimacy + Endsley SA",
        key_author="Tyler (2004); Endsley (2015)",
        prediction="90% city coverage goal → maximum surveillance visibility. Tests whether comprehensive coverage improves or degrades community trust.",
        data_available=True,
        status="qualitative",
    ),
]


def load_city_data() -> Dict[str, Any]:
    """Load raw DFR data for all 3 cities."""
    cities = {}
    city_files = {
        "Chula Vista": RAW_DIR / "chula_vista_dfr_data.json",
        "Elizabeth": RAW_DIR / "elizabeth_nj_policy.json",
        "Cincinnati": RAW_DIR / "cincinnati_dfr_data.json",
    }

    for city, path in city_files.items():
        if path.exists():
            with open(path) as f:
                cities[city] = json.load(f)
            logger.info(f"Loaded {city}: {path}")
        else:
            logger.warning(f"Missing data for {city}: {path}")

    return cities


def build_cross_program_comparison(cities: Dict[str, Any]) -> pd.DataFrame:
    """Build normalized cross-program comparison table."""
    records = []

    # Chula Vista
    cv = cities.get("Chula Vista", {})
    cv_metrics = cv.get("known_metrics", cv.get("operational_metrics", {}))
    records.append(DFRComparison(
        city="Chula Vista",
        state="CA",
        launch_date=cv_metrics.get("launch_date", cv.get("program_details", {}).get("launch_date", "")),
        program_status=cv_metrics.get("program_status", cv.get("program_details", {}).get("program_status", "")),
        vendor=cv_metrics.get("vendor", cv.get("program_details", {}).get("vendor", "")),
        avg_response_time_sec=cv_metrics.get("avg_response_time_sec"),
        avg_flight_time_sec=cv_metrics.get("avg_flight_time_sec"),
        total_missions=cv_metrics.get("total_missions"),
        drone_models="Skydio X2, Skydio X10",
        coverage_area="Expanded city-wide from downtown",
        data_quality="secondary",
    ).__dict__)

    # Elizabeth
    el = cities.get("Elizabeth", {})
    el_metrics = el.get("known_metrics", {})
    records.append(DFRComparison(
        city="Elizabeth",
        state="NJ",
        launch_date=el_metrics.get("launch_date", ""),
        program_status="active",
        vendor=el_metrics.get("vendor", "Skydio"),
        avg_response_time_sec=el_metrics.get("avg_response_time_sec"),
        total_missions=el_metrics.get("total_deployments") or el_metrics.get("total_missions"),
        successful_missions=el_metrics.get("successful_missions"),
        incidents_assisted=el_metrics.get("incidents_assisted"),
        deployment_period=el_metrics.get("deployment_period"),
        drone_models="Skydio",
        coverage_area="City-wide (Mon-Fri 0900-2000)",
        data_quality="policy_doc",
    ).__dict__)

    # Cincinnati
    ci = cities.get("Cincinnati", {})
    ci_metrics = ci.get("known_metrics", ci.get("program_details", {}))
    records.append(DFRComparison(
        city="Cincinnati",
        state="OH",
        launch_date=ci_metrics.get("launch_date", ci.get("program_details", {}).get("launch_date", "")),
        program_status=ci_metrics.get("program_status", ci.get("program_details", {}).get("program_status", "")),
        vendor=ci_metrics.get("vendor", ci.get("program_details", {}).get("vendor", "")),
        drone_models="Skydio autonomous",
        coverage_area="Downtown → 90% city by end 2025",
        data_quality="sparse",
    ).__dict__)

    df = pd.DataFrame(records)
    return df


def build_response_time_analysis(cities: Dict[str, Any]) -> pd.DataFrame:
    """Build response time comparison table."""
    rows = []

    cv = cities.get("Chula Vista", {})
    cv_metrics = cv.get("known_metrics", cv.get("operational_metrics", {}))
    cv_rt = cv_metrics.get("avg_response_time_sec")
    if cv_rt:
        rows.append({
            "city": "Chula Vista",
            "state": "CA",
            "response_time_sec": cv_rt,
            "response_time_min": round(cv_rt / 60, 1),
            "priority_level": "P1 (estimated)",
            "flight_time_sec": cv_metrics.get("avg_flight_time_sec"),
            "source": "Power BI dashboard / secondary sources",
            "cog_sci_link": "Endsley SA Level 1 — fast detection, comprehension unknown",
        })

    el = cities.get("Elizabeth", {})
    el_metrics = el.get("known_metrics", {})
    el_rt = el_metrics.get("avg_response_time_sec")
    if el_rt:
        rows.append({
            "city": "Elizabeth",
            "state": "NJ",
            "response_time_sec": el_rt,
            "response_time_min": round(el_rt / 60, 1),
            "priority_level": "P1 + P2",
            "flight_time_sec": None,
            "source": "Policy document (General Order Vol 3 Ch 18)",
            "cog_sci_link": "94s is 2.5x faster than Chula Vista — tests speed-accuracy tradeoff",
        })

    ci = cities.get("Cincinnati", {})
    rows.append({
        "city": "Cincinnati",
        "state": "OH",
        "response_time_sec": None,
        "response_time_min": None,
        "priority_level": "N/A",
        "flight_time_sec": None,
        "source": "No response time data available (program in expansion)",
        "cog_sci_link": "Pending — FOIA request recommended",
    })

    return pd.DataFrame(rows)


def save_results(
    comparison_df: pd.DataFrame,
    response_df: pd.DataFrame,
):
    """Save all processed outputs."""
    # Cross-program comparison
    comp_path = PROCESSED_DIR / "dfr_cross_program_comparison.csv"
    comparison_df.to_csv(comp_path, index=False)
    logger.info(f"Cross-program comparison: {comp_path}")

    # Response time analysis
    rt_path = PROCESSED_DIR / "dfr_response_time_analysis.csv"
    response_df.to_csv(rt_path, index=False)
    logger.info(f"Response time analysis: {rt_path}")

    # Cognitive science benchmark mapping
    mapping_data = [asdict(m) for m in COG_SCI_MAPPINGS]
    mapping_df = pd.DataFrame(mapping_data)
    mapping_path = PROCESSED_DIR / "cog_sci_benchmark_mapping.csv"
    mapping_df.to_csv(mapping_path, index=False)
    logger.info(f"Cog-sci mapping: {mapping_path}")

    # Human benchmark parameters
    params_path = PROCESSED_DIR / "human_benchmark_parameters.json"
    with open(params_path, "w") as f:
        json.dump(HUMAN_BENCHMARK_PARAMETERS, f, indent=2)
    logger.info(f"Human benchmark parameters: {params_path}")


def run_processor():
    """Run the full data integration pipeline."""
    logger.info("=" * 60)
    logger.info("STUDY 2 DATA INTEGRATION PROCESSOR")
    logger.info("=" * 60)

    # Load raw data
    cities = load_city_data()
    if not cities:
        logger.error("No city data found. Run dfr_scraper.py first.")
        return

    logger.info(f"\nLoaded data for {len(cities)} cities: {list(cities.keys())}")

    # Build comparison tables
    comparison_df = build_cross_program_comparison(cities)
    logger.info(f"\nCross-program comparison: {len(comparison_df)} programs")

    # Build response time analysis
    response_df = build_response_time_analysis(cities)
    logger.info(f"Response time analysis: {len(response_df)} entries")

    # Save everything
    save_results(comparison_df, response_df)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("PROCESSING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"  Programs compared: {len(comparison_df)}")
    logger.info(f"  Response time entries: {len(response_df)}")
    logger.info(f"  Cog-sci mappings: {len(COG_SCI_MAPPINGS)}")
    testable = sum(1 for m in COG_SCI_MAPPINGS if m.status == "testable")
    pending = sum(1 for m in COG_SCI_MAPPINGS if m.status == "pending_data")
    logger.info(f"  Testable predictions: {testable}")
    logger.info(f"  Pending data: {pending}")
    logger.info(f"  Human benchmarks: {len(HUMAN_BENCHMARK_PARAMETERS)}")

    logger.info(f"\n{'='*60}")
    logger.info("COGNITIVE SCIENCE INTEGRATION MATRIX")
    logger.info(f"{'='*60}")
    for mapping in COG_SCI_MAPPINGS:
        status_icon = "✓" if mapping.status == "testable" else "⏳" if mapping.status == "pending_data" else "📝"
        logger.info(f"  {status_icon} {mapping.data_point} → {mapping.cognitive_theory} [{mapping.status}]")


if __name__ == "__main__":
    run_processor()
