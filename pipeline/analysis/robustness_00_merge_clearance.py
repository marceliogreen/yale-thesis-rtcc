"""
Robustness Step 0: Merge clearance data into RTCC panel.

Merges actual_murder and total_cleared_murder from comparison pool
into the RTCC city panel, computing clearance_rate.

Output: results/study1_rtcc/robustness/rtcc_panel_with_clearance.csv
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
OUT = BASE / "results" / "study1_rtcc" / "robustness"
OUT.mkdir(parents=True, exist_ok=True)

def main():
    # Load panels
    rtcc = pd.read_csv(BASE / "results/study1_rtcc" / "rtcc_city_panel_enhanced.csv")
    comp = pd.read_csv(BASE / "thesis/data/comparison_pool_yearly.csv")

    logger.info(f"RTCC panel: {rtcc.shape}")
    logger.info(f"Comparison pool: {comp.shape}")

    # Extract clearance columns from comparison pool
    clearance_cols = ["ori", "year", "actual_murder", "actual_manslaughter",
                      "total_cleared_murder", "total_cleared_manslaughter"]
    avail = [c for c in clearance_cols if c in comp.columns]
    clr = comp[avail].copy()

    # Compute total homicides and cleared
    clr["homicides_raw"] = clr.get("actual_murder", 0).fillna(0) + clr.get("actual_manslaughter", 0).fillna(0)
    clr["cleared_raw"] = clr.get("total_cleared_murder", 0).fillna(0) + clr.get("total_cleared_manslaughter", 0).fillna(0)
    clr["clearance_rate_raw"] = np.where(clr["homicides_raw"] > 0,
                                          clr["cleared_raw"] / clr["homicides_raw"], np.nan)
    clr = clr[["ori", "year", "homicides_raw", "cleared_raw", "clearance_rate_raw"]]

    # Merge into RTCC panel
    merged = rtcc.merge(clr, on=["ori", "year"], how="left")
    merged["clearance_rate"] = merged["clearance_rate_raw"]

    # Use FBI CDE homicides where available, fall back to raw
    merged["homicides_total"] = merged["homicides"].fillna(merged["homicides_raw"])

    # Summary
    n_with_cr = merged["clearance_rate"].notna().sum()
    n_total = len(merged)
    logger.info(f"Rows with clearance_rate: {n_with_cr}/{n_total} ({n_with_cr/n_total*100:.0f}%)")

    # Per-city coverage
    for city in sorted(merged["city"].unique()):
        cdf = merged[merged["city"] == city]
        n_cr = cdf["clearance_rate"].notna().sum()
        logger.info(f"  {city}: {n_cr}/{len(cdf)} years with clearance data")

    out_path = OUT / "rtcc_panel_with_clearance.csv"
    merged.to_csv(out_path, index=False)
    logger.info(f"Saved: {out_path} ({merged.shape})")
    return merged

if __name__ == "__main__":
    main()
