"""Download and parse the external market data used by the Stage 3 valuation.

Every response is stored unchanged in ``data/raw/market/`` and recorded in
``data/raw/market/market_manifest.csv`` (URL, retrieval time, size, SHA-256).
Downstream code reads only those stored files, so the valuation can be rebuilt
offline and always uses the same data.

Look-ahead control: values are always read **as of** a valuation date. The
accessors return the last observation on or before that date and never later data.

Sources
-------
* FRED (Federal Reserve Bank of St. Louis), https://fred.stlouisfed.org/
  - DGS10   10-year Treasury constant-maturity yield (%)
  - DBAA    Moody's seasoned Baa corporate bond yield (%)
  - DEXUSUK US dollars per British pound (noon buying rate)
* Aswath Damodaran, "Implied Equity Risk Premiums" historical table (start-of-year values),
  https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html
* Yahoo Finance chart API (daily prices; split-adjusted "close" plus split events), used for peer
  returns (beta) and market capitalisation. https://query1.finance.yahoo.com/v8/finance/chart/<ticker>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from net import DownloadError, download_to  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MKT = ROOT / "data" / "raw" / "market"
MANIFEST = MKT / "market_manifest.csv"
UA = {"User-Agent": "Mozilla/5.0 (MA-real-options-valuation research script)"}

FRED_SERIES = ["DGS10", "DBAA", "DEXUSUK", "DGS3"]  # DGS3 added in Stage 5 (option horizon)
YAHOO = {  # ticker: (start, end)
    "DIS": ("2015-01-01", "2018-07-01"),
    "CMCSA": ("2015-01-01", "2018-07-01"),
    "AMCX": ("2015-01-01", "2018-07-01"),
    "NFLX": ("2015-01-01", "2018-07-01"),
    "^GSPC": ("2015-01-01", "2018-07-01"),
    "FOXA": ("2019-03-01", "2019-04-30"),  # Fox Corporation (New Fox), first trading days after the 19 Mar 2019 distribution
}


def _ts(d):
    return int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def urls():
    out = {}
    for sid in FRED_SERIES:
        out[f"FRED_{sid}.csv"] = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2014-01-01&coed=2019-12-31"
    out["DAMODARAN_histimpl.html"] = "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/histimpl.html"
    for t, (a, b) in YAHOO.items():
        safe = t.replace("^", "IDX_")
        out[f"YAHOO_{safe}_daily.json"] = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={_ts(a)}"
                                           f"&period2={_ts(b)}&interval=1d&events=split")
        # split events over the full history (to undo later splits when computing historical market cap)
        out[f"YAHOO_{safe}_splits.json"] = (f"https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1=0"
                                            f"&period2={_ts('2026-01-01')}&interval=1mo&events=split")
    return out


def fetch(force=False):
    """Download missing files (all with --force). Failures are recorded in the manifest, the run
    continues with the remaining files, and the function returns the list of failed files."""
    MKT.mkdir(parents=True, exist_ok=True)
    rows, failed = [], []
    for name, url in urls().items():
        dest = MKT / name
        status = "ok"
        if force or not dest.exists():
            try:
                data = download_to(url, dest, UA)  # bounded retries + atomic write (src/net.py)
                stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                time.sleep(0.5)
            except DownloadError as exc:
                print(f"FAILED {name}: {exc}")
                failed.append(name)
                status, data, stamp = f"failed: {exc}", (dest.read_bytes() if dest.exists() else b""), ""
        else:
            data = dest.read_bytes()
            stamp = _old_stamp(name)
        rows.append({"file": name, "url": url, "retrieved_utc": stamp, "bytes": len(data),
                     "sha256": hashlib.sha256(data).hexdigest() if data else "", "status": status})
        print(f"{'ok' if status == 'ok' else 'FAILED'} {name} {len(data):,}")
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows) - len(failed)} ok, {len(failed)} failed -> {MANIFEST.relative_to(ROOT)}")
    return failed


def _old_stamp(name):
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["file"] == name:
                    return r["retrieved_utc"]
    return ""


def manifest():
    with MANIFEST.open(encoding="utf-8") as fh:
        return {r["file"]: r for r in csv.DictReader(fh)}


# ----------------------------------------------------------------------------- parsers
@lru_cache(None)
def fred(series: str) -> pd.Series:
    df = pd.read_csv(MKT / f"FRED_{series}.csv")
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")  # FRED marks holidays with "."
    return df.dropna().set_index("date")["value"]


def asof(series: pd.Series, date: str):
    """Last observation on or before ``date``: (value, observation_date)."""
    s = series[series.index <= pd.Timestamp(date)]
    return float(s.iloc[-1]), s.index[-1].strftime("%Y-%m-%d")


@lru_cache(None)
def damodaran_implied_erp() -> pd.DataFrame:
    """Start-of-year implied ERP table (year label = value as of 1 January of that year).
    The page has one row per year: Year, Earnings yield, Dividend yield, S&P 500, ..., Implied ERP (FCFE),
    Implied premium (DDM)..."""
    tables = pd.read_html(MKT / "DAMODARAN_histimpl.html", flavor="lxml")
    t = max(tables, key=len)
    header_row = None
    for i in range(min(10, len(t))):
        if any(isinstance(v, str) and v.strip().lower() == "year" for v in t.iloc[i].values):
            header_row = i
            break
    t.columns = [str(c).strip() for c in t.iloc[header_row].values]
    t = t.iloc[header_row + 1:]
    t = t[pd.to_numeric(t["Year"], errors="coerce").notna()].copy()
    t["Year"] = t["Year"].astype(float).astype(int)
    return t.set_index("Year")


def implied_erp(year: int, column_hint="Implied ERP (FCFE)"):
    t = damodaran_implied_erp()
    col = [c for c in t.columns if c.lower().startswith(column_hint.lower())]
    if not col:
        col = [c for c in t.columns if "implied" in c.lower() and "fcfe" in c.lower()]
    v = t.loc[year, col[0]]
    v = float(str(v).replace("%", "")) / (100 if "%" in str(v) else 1)
    return v, col[0]


@lru_cache(None)
def yahoo(ticker: str) -> pd.DataFrame:
    safe = ticker.replace("^", "IDX_")
    d = json.loads((MKT / f"YAHOO_{safe}_daily.json").read_text(encoding="utf-8"))["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    df = pd.DataFrame({"close_split_adjusted": q["close"]},
                      index=pd.to_datetime(d["timestamp"], unit="s").normalize())
    df = df.dropna()
    sp = json.loads((MKT / f"YAHOO_{safe}_splits.json").read_text(encoding="utf-8"))["chart"]["result"][0]
    splits = sp.get("events", {}).get("splits", {})
    ev = sorted((pd.to_datetime(int(v["date"]), unit="s").normalize(), v["numerator"] / v["denominator"]) for v in splits.values())
    # actual traded price on date d = adjusted close x product of split ratios that occur AFTER d
    factor = []
    for day in df.index:
        f = 1.0
        for when, ratio in ev:
            if when > day:
                f *= ratio
        factor.append(f)
    df["split_factor_after"] = factor
    df["close_as_traded"] = df["close_split_adjusted"] * df["split_factor_after"]
    df.attrs["splits"] = ev
    return df


def price_asof(ticker, date):
    df = yahoo(ticker)
    s = df[df.index <= pd.Timestamp(date)]
    return float(s["close_as_traded"].iloc[-1]), s.index[-1].strftime("%Y-%m-%d")


def weekly_returns(ticker, end, years=2):
    """Friday-to-Friday simple returns over ``years`` ending on or before ``end`` (split-adjusted closes)."""
    df = yahoo(ticker)
    s = df["close_split_adjusted"]
    s = s[(s.index <= pd.Timestamp(end)) & (s.index > pd.Timestamp(end) - pd.DateOffset(years=years))]
    w = s.resample("W-FRI").last().dropna()
    return w.pct_change().dropna()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    raise SystemExit(1 if fetch(ap.parse_args().force) else 0)
