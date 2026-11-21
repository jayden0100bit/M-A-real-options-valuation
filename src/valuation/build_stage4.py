"""Stage 4 driver: synergy valuation (4A) and accretion/dilution (4B).

Reads Stage 1-3 outputs (never rewrites them) and writes synergy_* and accretion_dilution_* CSVs.
Stage 4 checks replace earlier Stage 4 checks in verification_checks.csv; Stage 1-3 checks are kept unchanged.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import accretion  # noqa: E402
import synergy  # noqa: E402

PROC = HERE.parents[1] / "data" / "processed"
STAGE4 = ("synergy_", "accretion_")


def main():
    synergy.build()
    synergy.write()
    accretion.build()
    accretion.write()
    checks = synergy.CHECKS + accretion.CHECKS
    vc = PROC / "verification_checks.csv"
    with vc.open(encoding="utf-8") as fh:
        existing = [c for c in csv.DictReader(fh) if not c["check_type"].startswith(STAGE4)]
    with vc.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["check_type", "entity", "source_id", "fiscal_period", "item", "expected", "observed", "status", "detail"])
        w.writeheader()
        w.writerows(existing + checks)
    bad = [c for c in checks if c["status"] != "pass"]
    print(f"stage 4: {len(synergy.ASSUME)} synergy assumptions, {len(synergy.OUT)} synergy outputs, {len(accretion.INPUTS)} A/D inputs, "
          f"{len(accretion.OUT)} A/D outputs, {len(checks)} checks, {len(bad)} failed")
    for c in bad[:20]:
        print("FAILED", c)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
