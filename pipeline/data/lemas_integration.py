"""
LEMAS 2020 Integration for RTCC Thesis Pipeline

Reads ICPSR 38651 (Law Enforcement Management and Administrative Statistics, 2020),
extracts thesis-relevant agency characteristics, handles ORI aliasing,
computes derived features, and merges into master_analysis_panel.csv.

Data source: https://www.icpsr.umich.edu/web/NACJD/studies/38651
LEMAS is collected every 3-4 years (2013, 2016, 2020). This uses the 2020 wave.

ICPSR missing codes: -8 = not applicable, -9 = missing

Author: Marcel Green <marcelo.green@yale.edu>
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent.parent
LEMAS_TSV = BASE_DIR / "thesis" / "Thesis Files" / "ICPSR_38651" / "DS0001" / "38651-0001-Data.tsv"
MASTER_PANEL = BASE_DIR / "thesis" / "data" / "master_analysis_panel.csv"
OUTPUT_PANEL = BASE_DIR / "thesis" / "data" / "master_analysis_panel_with_lemas.csv"
LEMAS_EXTRACT = BASE_DIR / "thesis" / "data" / "lemas_2020_extract.csv"

# ── ORI Alias Map ─────────────────────────────────────────────
# Master panel uses different ORIs than LEMAS for some agencies.
# Map: master_panel_ori → lemas_ori

# Map: master_panel_ori → lemas_ori
# Only needed when the master panel uses a different ORI than LEMAS.
# Most agencies match directly.
ORI_ALIASES = {
    "MO0640000": "MOSPD0000",   # St. Louis: master uses state code, LEMAS uses MOSPD
    "LA0360000": "LANPD0000",   # New Orleans: master uses state code, LEMAS uses LANPD
    "IL0160000": "ILCPD0000",   # Chicago: master uses county code, LEMAS uses ILCPD
    "FL0130200": "FL0130600",   # Miami: master uses old code, LEMAS uses FL0130600
    "FL0160000": "FL0130600",   # Duval/Jacksonville → Miami cluster fallback
}

# ── LEMAS Variables to Extract ────────────────────────────────

# Agency identification
ID_COLS = ["ORI9", "AGENCYNAME", "CITY", "STATE", "AGENCYSAMPTYPE"]

# Agency resources
RESOURCE_COLS = {
    "FTSWORN": "ft_sworn",
    "PTSWORN": "pt_sworn",
    "FTNON": "ft_civilian",
    "TOTFTEMP": "total_ft_employees",
    "OPBUDGET": "agency_budget",
    "PRIMARYPOP2020": "pop_served_2020",
}

# Body cameras
BWC_COLS = {
    "POL_BWC": "has_bwc",
    "EQ_VID_BWC": "bwc_units",
}

# Technology adoption (binary: 1=yes, 2=no)
TECH_COLS = {
    "TECH_TYP_CAD": "has_cad",
    "TECH_TYP_RMS": "has_rms",
    "TECH_TYP_GIS": "has_gis",
    "TECH_TYP_LPR": "has_lpr",
    "TECH_TYP_GUNSHOT": "has_gunshot_detection",
    "TECH_TYP_FACEREC": "has_facerec",
    "TECH_TYP_INFR": "has_infrared",
    "TECH_TYP_TRACE": "has_trace",
    "TECH_TYP_BALL": "has_ballistics",
    "TECH_EIS": "has_early_intervention",
}

# Data-driven policing (binary: 1=yes, 2=no)
DATA_COLS = {
    "DATA_PRED": "has_predictive_policing",
    "DATA_INTEL": "has_intel_analysis",
    "DATA_SNA": "has_social_network_analysis",
    "DATA_TARG": "has_targeted_policing",
    "DATA_PATROL": "has_data_driven_patrol",
    "DATA_HSA": "has_hotspot_analysis",
    "DATA_BUDGET": "has_data_budget",
}

# All LEMAS columns to extract
ALL_LEMAS_COLS = (
    ID_COLS
    + list(RESOURCE_COLS.keys())
    + list(BWC_COLS.keys())
    + list(TECH_COLS.keys())
    + list(DATA_COLS.keys())
)


def load_lemas(tsv_path: Path = LEMAS_TSV) -> pd.DataFrame:
    """Load LEMAS 2020 TSV and extract relevant columns."""
    logger.info(f"Loading LEMAS from {tsv_path}")
    df = pd.read_csv(tsv_path, delimiter="\t", usecols=ALL_LEMAS_COLS)
    logger.info(f"Loaded {len(df)} agencies with {len(ALL_LEMAS_COLS)} columns")
    return df


def clean_lemas(df: pd.DataFrame) -> pd.DataFrame:
    """Clean LEMAS data: rename columns, handle missing codes, convert types."""
    # Rename columns to friendly names
    rename_map = {}
    rename_map.update(RESOURCE_COLS)
    rename_map.update(BWC_COLS)
    rename_map.update(TECH_COLS)
    rename_map.update(DATA_COLS)
    df = df.rename(columns=rename_map)

    # Convert binary columns: LEMAS uses 1=yes, 2=no, -8=N/A, -9=missing
    binary_cols = list(TECH_COLS.values()) + list(DATA_COLS.values()) + ["has_bwc"]
    for col in binary_cols:
        # 1 = yes → 1, everything else → 0
        df[col] = (df[col] == 1).astype(int)

    # Replace ICPSR missing codes with NaN for numeric columns
    numeric_cols = list(RESOURCE_COLS.values()) + ["bwc_units"]
    for col in numeric_cols:
        df[col] = df[col].replace([-8, -9, "-8", "-9"], np.nan)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def compute_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute per-capita and composite features."""
    # Officers per 10K population
    df["officers_per_10k"] = np.where(
        df["pop_served_2020"].notna() & (df["pop_served_2020"] > 0),
        df["ft_sworn"] / (df["pop_served_2020"] / 10_000),
        np.nan,
    )

    # Budget per capita
    df["budget_per_capita"] = np.where(
        df["pop_served_2020"].notna() & (df["pop_served_2020"] > 0),
        df["agency_budget"] / df["pop_served_2020"],
        np.nan,
    )

    # Technology adoption score (sum of all tech binary vars)
    tech_vars = list(TECH_COLS.values())
    df["tech_score"] = df[tech_vars].sum(axis=1)

    # Data-driven policing score
    data_vars = list(DATA_COLS.values())
    df["data_driven_score"] = df[data_vars].sum(axis=1)

    # BWC coverage ratio
    df["bwc_coverage"] = np.where(
        df["ft_sworn"].notna() & (df["ft_sworn"] > 0) & df["bwc_units"].notna(),
        df["bwc_units"] / df["ft_sworn"],
        np.nan,
    )
    df["bwc_coverage"] = df["bwc_coverage"].clip(upper=1.0)

    return df


def build_ori_lookup(lemas: pd.DataFrame) -> dict:
    """Build a CITY+STATE → ORI9 lookup for fuzzy matching."""
    lookup = {}
    for _, row in lemas.iterrows():
        key = (row["CITY"].strip().upper(), row["STATE"].strip().upper())
        # Prefer municipal PDs over sheriff/state agencies
        name = row["AGENCYNAME"].upper()
        is_pd = "POLICE DEPARTMENT" in name or "POLICE DIVISION" in name
        if key not in lookup or is_pd:
            lookup[key] = row["ORI9"]
    return lookup


def resolve_ori(master_ori: str, master_city: str, master_state: str,
                ori_aliases: dict, city_state_lookup: dict) -> str | None:
    """Resolve a master panel ORI to the LEMAS ORI."""
    # 1. Direct match
    # 2. Known alias
    if master_ori in ori_aliases:
        return ori_aliases[master_ori]
    # 3. CITY+STATE fuzzy match
    city_upper = master_city.strip().upper() if pd.notna(master_city) else ""
    state_upper = master_state.strip().upper() if pd.notna(master_state) else ""
    if city_upper and state_upper:
        return city_state_lookup.get((city_upper, state_upper))
    return None


def merge_with_master(
    lemas: pd.DataFrame,
    master_path: Path = MASTER_PANEL,
    output_path: Path = OUTPUT_PANEL,
    extract_path: Path = LEMAS_EXTRACT,
) -> pd.DataFrame:
    """Merge LEMAS features into the master analysis panel."""
    logger.info(f"Loading master panel from {master_path}")
    master = pd.read_csv(master_path)
    logger.info(f"Master panel: {len(master)} rows, {master['ori9'].nunique()} unique ORIs")

    # De-duplicate LEMAS by ORI9 (keep first, drop any dupes)
    lemas_dedup = lemas.drop_duplicates(subset="ORI9", keep="first")
    lemas_dict = lemas_dedup.set_index("ORI9")
    city_state_lookup = build_ori_lookup(lemas_dedup)

    # Save LEMAS extract for reference
    extract_cols = [
        "ORI9", "AGENCYNAME", "CITY", "STATE",
        "ft_sworn", "agency_budget", "pop_served_2020",
        "has_bwc", "bwc_units", "officers_per_10k", "budget_per_capita",
        "tech_score", "data_driven_score", "bwc_coverage",
    ] + list(TECH_COLS.values()) + list(DATA_COLS.values())
    extract = lemas_dedup[extract_cols].copy()
    extract.to_csv(extract_path, index=False)
    logger.info(f"Saved LEMAS extract to {extract_path}")

    # Resolve ORIs and merge
    lemas_cols_to_add = [
        "ft_sworn", "agency_budget", "pop_served_2020",
        "has_bwc", "bwc_units", "bwc_coverage",
        "officers_per_10k", "budget_per_capita",
        "tech_score", "data_driven_score",
    ] + list(TECH_COLS.values()) + list(DATA_COLS.values())

    # Build a lookup: master_ori → row of LEMAS data
    ori_to_lemas = {}

    for ori in master["ori9"].unique():
        # Try direct match
        if ori in lemas_dict.index:
            ori_to_lemas[ori] = lemas_dict.loc[ori, lemas_cols_to_add].to_dict()
            continue

        # Try alias or fuzzy CITY+STATE
        sample = master[master["ori9"] == ori].iloc[0]
        resolved = resolve_ori(
            ori,
            sample.get("agency_name", ""),
            sample.get("state_abb", ""),
            ORI_ALIASES,
            city_state_lookup,
        )

        if resolved and resolved in lemas_dict.index:
            ori_to_lemas[ori] = lemas_dict.loc[resolved, lemas_cols_to_add].to_dict()
            continue

    # Apply the merge via map
    for col in lemas_cols_to_add:
        master[col] = master["ori9"].map(
            lambda o, c=col: ori_to_lemas.get(o, {}).get(c, np.nan)
        )

    # Compute match stats
    total_oris = master["ori9"].nunique()
    matched_oris = len(ori_to_lemas)
    unmatched_oris = [o for o in master["ori9"].unique() if o not in ori_to_lemas]

    logger.info(f"\n{'='*50}")
    logger.info(f"LEMAS MERGE RESULTS")
    logger.info(f"{'='*50}")
    logger.info(f"Total unique ORIs: {total_oris}")
    logger.info(f"Matched: {matched_oris}")
    logger.info(f"Unmatched: {len(unmatched_oris)}")
    logger.info(f"Coverage: {matched_oris / total_oris:.1%}")

    if unmatched_oris:
        logger.info(f"\nUnmatched ORIs ({len(unmatched_oris)}):")
        for ori in sorted(unmatched_oris)[:20]:
            row = master[master["ori9"] == ori].iloc[0]
            logger.info(f"  {ori}: {row.get('agency_name', 'N/A')}, {row.get('state_abb', 'N/A')}")

    # Save
    master.to_csv(output_path, index=False)
    logger.info(f"\nSaved enhanced panel to {output_path}")
    logger.info(f"Columns: {list(master.columns)}")

    # Coverage summary
    logger.info(f"\n{'='*50}")
    logger.info(f"VARIABLE COVERAGE (non-null / total)")
    logger.info(f"{'='*50}")
    for col in lemas_cols_to_add:
        n = master[col].notna().sum()
        pct = n / len(master)
        logger.info(f"  {col}: {n:,} ({pct:.1%})")

    return master


def main():
    """Run the full LEMAS integration pipeline."""
    logger.info("=" * 60)
    logger.info("LEMAS 2020 INTEGRATION")
    logger.info("=" * 60)

    # Load
    lemas = load_lemas()

    # Clean
    lemas = clean_lemas(lemas)

    # Derived features
    lemas = compute_derived_features(lemas)

    # Quick stats
    logger.info(f"\nLEMAS 2020 Summary:")
    logger.info(f"  Agencies: {len(lemas)}")
    logger.info(f"  With sworn officers: {lemas['ft_sworn'].notna().sum()}")
    logger.info(f"  With budget data: {lemas['agency_budget'].notna().sum()}")
    logger.info(f"  With BWC policy: {(lemas['has_bwc'] == 1).sum()}")
    logger.info(f"  Mean tech score: {lemas['tech_score'].mean():.2f}")
    logger.info(f"  Mean data-driven score: {lemas['data_driven_score'].mean():.2f}")

    # Merge
    enhanced = merge_with_master(lemas)

    # RTCC city check — use actual agency ORIs, not the rtcc_city label
    logger.info(f"\n{'='*50}")
    logger.info(f"RTCC CITY LEMAS COVERAGE")
    logger.info(f"{'='*50}")
    RTCC_AGENCY_ORIS = {
        "Hartford": "CT0006400",
        "Miami": "FL0130600",
        "St. Louis": "MOSPD0000",
        "Newark": "NJNPD0000",
        "New Orleans": "LANPD0000",
        "Albuquerque": "NM0010100",
        "Fresno": "CA0100500",
        "Chicago": "ILCPD0000",
    }
    for city, ori in RTCC_AGENCY_ORIS.items():
        match = enhanced[enhanced["ori9"] == ori]
        if len(match) > 0:
            row = match.iloc[0]
            logger.info(f"\n  {city} ({ori}):")
            if pd.notna(row.get("ft_sworn")):
                logger.info(f"    Officers: {row['ft_sworn']:.0f}")
                logger.info(f"    Budget: ${row['agency_budget']:,.0f}")
                logger.info(f"    Officers/10K: {row['officers_per_10k']:.1f}")
                logger.info(f"    BWC: {row['has_bwc']:.0f}")
                logger.info(f"    Tech score: {row['tech_score']:.0f}")
                logger.info(f"    Data-driven score: {row['data_driven_score']:.0f}")
                logger.info(f"    LPR: {row['has_lpr']:.0f}, Gunshot: {row['has_gunshot_detection']:.0f}, GIS: {row['has_gis']:.0f}")
            else:
                logger.info(f"    NO LEMAS DATA (ORI not in master panel)")
        else:
            logger.info(f"\n  {city} ({ori}): NOT IN MASTER PANEL")

    logger.info(f"\nDone. Enhanced panel: {OUTPUT_PANEL}")
    return enhanced


if __name__ == "__main__":
    main()
