"""Build ``data/processed/source_register.csv``: one row per source document.

Joins the filing list (``data/reference/filings_to_fetch.csv``) with the download
manifest (URL, size, SHA-256) and counts how many processed records cite each source.
"""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILINGS = ROOT / "data" / "reference" / "filings_to_fetch.csv"
MANIFEST = ROOT / "data" / "raw" / "download_manifest.csv"
HIST = ROOT / "data" / "processed" / "historical_financials.csv"
TRANS = ROOT / "data" / "processed" / "transaction_assumptions.csv"
OUT = ROOT / "data" / "processed" / "source_register.csv"

XBRL_META = {
    "XBRL_FACTS_1001039": ("TWDC Enterprises 18 Corp. (legacy The Walt Disney Company)", "1001039"),
    "XBRL_FACTS_1744489": ("The Walt Disney Company (formerly TWDC Holdco 613 Corp.)", "1744489"),
    "XBRL_FACTS_1308161": ("Twenty-First Century Fox, Inc. (later TFCF Corporation)", "1308161"),
    # Stage 3 comparable companies
    "XBRL_FACTS_1166691": ("Comcast Corporation", "1166691"),
    "XBRL_FACTS_1514991": ("AMC Networks Inc.", "1514991"),
    "XBRL_FACTS_1065280": ("Netflix, Inc.", "1065280"),
}


def read(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    manifest = {r["doc_id"]: r for r in read(MANIFEST)}
    hist_counts = Counter(r["source_id"] for r in read(HIST)) if HIST.exists() else Counter()
    hist_primary = Counter(r["source_id"] for r in read(HIST) if r["is_primary"] == "True") if HIST.exists() else Counter()
    trans_counts = Counter(r["source_id"] for r in read(TRANS)) if TRANS.exists() else Counter()
    rows = []
    for f in read(FILINGS):
        m = manifest.get(f["doc_id"], {})
        acc = f["accession"]
        rows.append({
            "source_id": f["doc_id"], "entity": f["entity"], "cik": f["cik"], "form": f["form"],
            "filing_date": f["filing_date"], "period_end": f["period_end"], "accession": acc,
            "document": f["filename"], "description": f["description"],
            "url": m.get("url", ""),
            "filing_index_url": f"https://www.sec.gov/Archives/edgar/data/{int(f['cik'])}/{acc.replace('-', '')}/{acc}-index.htm",
            "local_path": m.get("local_path", ""), "bytes": m.get("bytes", ""), "sha256": m.get("sha256", ""),
            "download_status": m.get("status", "not downloaded"),
            "records_historical_financials": hist_counts.get(f["doc_id"], 0),
            "primary_records_historical_financials": hist_primary.get(f["doc_id"], 0),
            "records_transaction_assumptions": trans_counts.get(f["doc_id"], 0),
            "source_type": "primary SEC filing",
        })
    for doc_id, (entity, cik) in XBRL_META.items():
        m = manifest.get(doc_id, {})
        rows.append({
            "source_id": doc_id, "entity": entity, "cik": cik, "form": "XBRL company facts (API)",
            "filing_date": "", "period_end": "", "accession": "(multiple; each fact carries its accession)",
            "document": Path(m.get("local_path", "")).name, "description":
                "SEC XBRL company-facts JSON. Used only to cross-check values parsed from the 10-K HTML; never the primary source.",
            "url": m.get("url", ""), "filing_index_url": "", "local_path": m.get("local_path", ""),
            "bytes": m.get("bytes", ""), "sha256": m.get("sha256", ""), "download_status": m.get("status", "not downloaded"),
            "records_historical_financials": 0, "primary_records_historical_financials": 0, "records_transaction_assumptions": 0,
            "source_type": "SEC structured data (verification only)",
        })
    # Stage 3 external market data (FRED, Damodaran, Yahoo Finance)
    mm = ROOT / "data" / "raw" / "market" / "market_manifest.csv"
    if mm.exists():
        desc = {"FRED_DGS10.csv": "FRED DGS10: 10-year US Treasury constant-maturity yield (risk-free rate)",
                "FRED_DBAA.csv": "FRED DBAA: Moody's seasoned Baa corporate bond yield (pre-tax cost of debt proxy)",
                "FRED_DEXUSUK.csv": "FRED DEXUSUK: US dollars per British pound (Sky stake conversion)",
                "DAMODARAN_histimpl.html": "Damodaran implied equity risk premium table (end-of-year values)",
                "FRED_DGS3.csv": "FRED DGS3: 3-year US Treasury constant-maturity yield (Stage 5 option risk-free rate)"}
        for r in read(mm):
            name = r["file"]
            d = desc.get(name) or (f"Yahoo Finance chart API: {name.split('_')[1]} "
                                   f"{'daily prices' if 'daily' in name else 'split history'} (peer betas, market caps, FOXA at closing)")
            rows.append({
                "source_id": "MKT_" + name.rsplit(".", 1)[0], "entity": "", "cik": "", "form": "external market data",
                "filing_date": "", "period_end": "", "accession": "", "document": name, "description": d,
                "url": r["url"], "filing_index_url": "", "local_path": f"data/raw/market/{name}", "bytes": r["bytes"],
                "sha256": r["sha256"], "download_status": r.get("status", "ok") or "ok",
                "records_historical_financials": 0, "primary_records_historical_financials": 0, "records_transaction_assumptions": 0,
                "source_type": f"external market data (retrieved {r['retrieved_utc']}; observations read as of each valuation date)",
            })
    fields = list(rows[0].keys())
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} sources -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
