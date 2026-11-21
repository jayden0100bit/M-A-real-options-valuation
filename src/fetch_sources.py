"""Download the primary SEC sources used by the Disney / 21st Century Fox case study.

Reads ``data/reference/filings_to_fetch.csv`` and stores each document under
``data/raw/sec/``. It also downloads the SEC XBRL "company facts" JSON for
the three registrants (old Disney, new Disney, 21CF) into ``data/raw/xbrl/``.
Every downloaded file is recorded in ``data/raw/download_manifest.csv`` with
its source URL, byte size and SHA-256 hash, so later runs can confirm they
are working from the same files.

SEC fair-access policy asks automated clients to identify themselves in the
User-Agent header. Set the ``SEC_USER_AGENT`` environment variable to your own
"Name contact@domain" string before running. The default is a generic
project identifier.

Usage::

    python src/fetch_sources.py            # download only missing files
    python src/fetch_sources.py --force    # re-download everything
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import time
import urllib.request  # noqa: F401 (kept for compatibility)
from net import download_to
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILINGS_CSV = ROOT / "data" / "reference" / "filings_to_fetch.csv"
RAW_DIR = ROOT / "data" / "raw"
SEC_DIR = RAW_DIR / "sec"
XBRL_DIR = RAW_DIR / "xbrl"
MANIFEST = RAW_DIR / "download_manifest.csv"

USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", "MA-real-options-valuation-research research@example.invalid"
)
PAUSE_SECONDS = 0.25  # stays well below SEC's 10 requests/second limit

# CIK -> label for the XBRL company-facts downloads
XBRL_COMPANIES = {
    "1001039": "TWDC_Enterprises_18_old_Disney",
    "1744489": "Walt_Disney_Co_new_Disney",
    "1308161": "Twenty_First_Century_Fox",
    # Stage 3 comparable companies (share counts and LTM financials)
    "1166691": "Comcast",
    "1514991": "AMC_Networks",
    "1065280": "Netflix",
}


def archive_url(cik: str, accession: str, filename: str) -> str:
    return (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession.replace('-', '')}/{filename}"
    )


def companyfacts_url(cik: str) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"


def download(url: str, dest: Path, force: bool) -> bytes:
    if dest.exists() and not force:
        return dest.read_bytes()
    # bounded retries on transient errors; atomic write (see src/net.py)
    data = download_to(url, dest, {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    time.sleep(PAUSE_SECONDS)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    args = parser.parse_args()

    rows = []
    with FILINGS_CSV.open(newline="", encoding="utf-8") as fh:
        filings = list(csv.DictReader(fh))

    for f in filings:
        url = archive_url(f["cik"], f["accession"], f["filename"])
        dest = SEC_DIR / f"{f['doc_id']}__{f['filename']}"
        try:
            data = download(url, dest, args.force)
        except Exception as exc:  # keep going, report the failure in the manifest
            print(f"FAILED {f['doc_id']}: {exc}", file=sys.stderr)
            rows.append({"doc_id": f["doc_id"], "url": url, "local_path": "",
                         "bytes": "", "sha256": "", "status": f"failed: {exc}"})
            continue
        rows.append({"doc_id": f["doc_id"], "url": url,
                     "local_path": dest.relative_to(ROOT).as_posix(),
                     "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                     "status": "ok"})
        print(f"ok  {f['doc_id']:<28} {len(data):>10,} bytes")

    for cik, label in XBRL_COMPANIES.items():
        url = companyfacts_url(cik)
        dest = XBRL_DIR / f"companyfacts_CIK{int(cik):010d}_{label}.json"
        doc_id = f"XBRL_FACTS_{cik}"
        try:
            data = download(url, dest, args.force)
        except Exception as exc:
            print(f"FAILED {doc_id}: {exc}", file=sys.stderr)
            rows.append({"doc_id": doc_id, "url": url, "local_path": "", "bytes": "",
                         "sha256": "", "status": f"failed: {exc}"})
            continue
        rows.append({"doc_id": doc_id, "url": url,
                     "local_path": dest.relative_to(ROOT).as_posix(),
                     "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
                     "status": "ok"})
        print(f"ok  {doc_id:<28} {len(data):>10,} bytes")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["doc_id", "url", "local_path", "bytes",
                                                "sha256", "status", "manifest_written_utc"])
        writer.writeheader()
        for r in rows:
            r["manifest_written_utc"] = stamp
            writer.writerow(r)
    failed = [r for r in rows if r["status"] != "ok"]
    print(f"\n{len(rows) - len(failed)} ok, {len(failed)} failed -> {MANIFEST.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
