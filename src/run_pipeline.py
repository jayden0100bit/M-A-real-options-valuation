"""Run the full data-collection pipeline in order.

    python src/run_pipeline.py            # download missing files, then rebuild everything
    python src/run_pipeline.py --offline  # skip downloading; use files already in data/raw

Steps: fetch SEC sources -> HTML to text/table caches -> historical financials ->
transaction assumptions -> source register -> Stage 2 ratios, segment analysis and charts ->
Stage 3 forecasts, comparables, WACC, DCF, transaction analysis and charts ->
Stage 4 synergy valuation and accretion/dilution -> Stage 5 real options and Monte Carlo. The script exits non-zero if any
verification check fails.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent


def run(script, *args):
    print(f"\n=== {script} {' '.join(args)}")
    return subprocess.call([sys.executable, str(SRC / script), *args])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="do not contact SEC EDGAR")
    a = ap.parse_args()
    if not a.offline:
        if run("fetch_sources.py") != 0 or run("valuation/market_data.py") != 0:
            return 1
    for step in ("sec_text.py", "build_historical.py", "build_transaction.py", "build_source_register.py",
                 "build_analysis.py", "make_charts.py",                    # Stage 2
                 "valuation/build_valuation.py", "valuation/charts.py",    # Stage 3
                 "valuation/build_stage4.py",                              # Stage 4
                 "valuation/build_stage5.py",                              # Stage 5
                 "export_dashboard.py"):                                   # dashboard data (static JSON)
        if run(step) != 0:
            print(f"step failed: {step}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
