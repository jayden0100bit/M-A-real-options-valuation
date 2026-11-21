"""Comparable-company inputs and trading multiples, as of a valuation date (no look-ahead).

Financial data: SEC XBRL company facts (data/raw/xbrl/). Only facts **filed on or before** the valuation
date are used. LTM flows = latest fiscal year + current year-to-date - prior year-to-date.
Prices: Yahoo Finance daily close on or before the market-data date, with later stock splits undone
(see market_data.yahoo) so the price matches the share counts reported at the time.

Shares: Comcast and AMC Networks have several share classes and their company-facts files carry no
cover-page share count, so for every peer the share count is a **proxy**: diluted weighted-average
shares for the latest reported quarter (``shares_basis = "diluted_weighted_average_latest_quarter (proxy)"``).
It is never presented as actual shares outstanding.

EV = market cap (proxy shares x price) + total debt - cash and equivalents + noncontrolling interests.
Equity-method investments are not deducted (a simplification, noted in the output).
"""
from __future__ import annotations

import json
from datetime import date as _date
from pathlib import Path

import pandas as pd

from market_data import price_asof

ROOT = Path(__file__).resolve().parents[2]
XBRL = ROOT / "data" / "raw" / "xbrl"

PEERS = {
    "CMCSA": {"name": "Comcast Corporation", "cik": "1166691",
              "file": "companyfacts_CIK0001166691_Comcast.json",
              "mix": "Cable distribution (~60% of revenue) plus NBCUniversal (cable networks, broadcast, film studio, theme parks). "
                     "Only NBCUniversal is comparable to RemainCo; the cable distribution business has a different, capex-heavy model."},
    "AMCX": {"name": "AMC Networks Inc.", "cik": "1514991", "file": "companyfacts_CIK0001514991_AMC_Networks.json",
             "mix": "Pure-play cable networks (AMC, IFC, SundanceTV, BBC America) and international channels. Closest to the FX / "
                    "National Geographic / international networks in RemainCo, but far smaller and with no film studio."},
    "NFLX": {"name": "Netflix, Inc.", "cik": "1065280", "file": "companyfacts_CIK0001065280_Netflix.json",
             "mix": "Streaming subscription service. Content amortization is in cost of revenues, not in D&A, so EBITDA is not "
                    "comparable, and its growth-stage multiples are far above mature media companies."},
    "DIS": {"name": "The Walt Disney Company (reference only)", "cik": "1001039",
            "file": "companyfacts_CIK0001001039_TWDC_Enterprises_18_old_Disney.json",
            "mix": "The acquirer. Shown for reference and excluded from peer medians: its price reflects the transaction after "
                   "6 Nov 2017 press reports, and its mix is dominated by parks and ESPN."},
}

CONCEPTS = {  # first available concept in each list is used
    "revenue": ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "operating_income": ["OperatingIncomeLoss"],
    "da": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet"],
    "net_income": ["NetIncomeLoss"],
    "shares_diluted_wavg": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}
DEBT_CONCEPTS = {
    "CMCSA": ["DebtCurrent", "LongTermDebtAndCapitalLeaseObligations"],
    "AMCX": ["DebtCurrent", "LongTermDebtNoncurrent"],
    "NFLX": ["LongTermDebtNoncurrent", "LongTermDebtCurrent"],
    "DIS": ["LongTermDebtCurrent", "LongTermDebtNoncurrent"],
}
INSTANT = {"cash": ["CashAndCashEquivalentsAtCarryingValue"], "nci": ["MinorityInterest"]}


def _facts(ticker):
    d = json.loads((XBRL / PEERS[ticker]["file"]).read_text(encoding="utf-8"))
    return d["facts"]


def _series(facts, concept, unit_kind, filed_by):
    for tax in ("us-gaap", "dei"):
        body = facts.get(tax, {}).get(concept)
        if not body:
            continue
        rows = []
        for unit, arr in body["units"].items():
            if (unit_kind == "USD" and unit != "USD") or (unit_kind == "shares" and unit != "shares"):
                continue
            for f in arr:
                if f.get("form") in ("10-K", "10-Q", "10-K/A", "10-Q/A") and f["filed"] <= filed_by:
                    rows.append(f)
        if rows:
            df = pd.DataFrame(rows)
            # same period reported in several filings: keep the latest filed on or before the date
            df = df.sort_values("filed").drop_duplicates(["start", "end"] if "start" in df else ["end"], keep="last")
            return df
    return None


def _days(a, b):
    return (_date.fromisoformat(b) - _date.fromisoformat(a)).days


def ltm(facts, concepts, filed_by):
    """Last-twelve-months flow and a description of how it was formed."""
    for c in concepts:
        df = _series(facts, c, "USD", filed_by)
        if df is None or "start" not in df:
            continue
        df = df.dropna(subset=["start"])
        df["dur"] = [_days(s, e) for s, e in zip(df.start, df.end)]
        latest_end = df.end.max()
        cur = df[df.end == latest_end]
        annual = cur[cur.dur.between(350, 380)]
        if len(annual):
            r = annual.iloc[-1]
            return float(r.val), f"{c}: FY {r.start}..{r.end} (accn {r.accn}, filed {r.filed})", latest_end
        ytd = cur.sort_values("dur").iloc[-1]  # longest YTD duration ending at latest_end
        fy = df[(df.dur.between(350, 380)) & (df.end < ytd.start)]
        if fy.empty:
            continue
        fyr = fy.sort_values("end").iloc[-1]
        prior_end = (pd.Timestamp(ytd.end) - pd.DateOffset(years=1))
        pr = df[(df.dur.between(ytd.dur - 8, ytd.dur + 8)) &
                (pd.to_datetime(df.end).sub(prior_end).abs() <= pd.Timedelta(days=8))]
        if pr.empty:
            continue
        prr = pr.iloc[-1]
        v = float(fyr.val) + float(ytd.val) - float(prr.val)
        return v, (f"{c}: FY {fyr.start}..{fyr.end} + YTD {ytd.start}..{ytd.end} - YTD {prr.start}..{prr.end} "
                   f"(latest accn {ytd.accn}, filed {ytd.filed})"), latest_end
    return None, "not available", None


def balance_date(facts, filed_by):
    """Common balance-sheet date: latest cash-balance date filed on or before the cutoff."""
    df = _series(facts, "CashAndCashEquivalentsAtCarryingValue", "USD", filed_by)
    return df.end.max()


def instant(facts, concepts, filed_by, bs_date, unit_kind="USD"):
    """Sum of concepts at the common balance date. A concept with no fact at that date is reported as
    'no fact at <date>' in the description and contributes nothing (stated, never silently)."""
    total, parts, found = 0.0, [], False
    for c in concepts:
        df = _series(facts, c, unit_kind, filed_by)
        if df is None:
            parts.append(f"{c}: no fact")
            continue
        at = df[df.end == bs_date]
        if at.empty:
            parts.append(f"{c}: no fact at {bs_date} (contributes 0)")
            continue
        r = at.iloc[-1]
        total += float(r.val)
        found = True
        parts.append(f"{c}={float(r.val) / 1e6:,.0f} at {bs_date} (accn {r.accn})")
    return (total if found else None), "; ".join(parts), bs_date


def latest_quarter_shares(facts, filed_by):
    df = _series(facts, "WeightedAverageNumberOfDilutedSharesOutstanding", "shares", filed_by)
    df = df.dropna(subset=["start"])
    df["dur"] = [_days(s, e) for s, e in zip(df.start, df.end)]
    q = df[df.dur.between(80, 100)]
    r = q.sort_values("end").iloc[-1]
    return float(r.val), f"WeightedAverageNumberOfDilutedSharesOutstanding {r.start}..{r.end} (accn {r.accn}, filed {r.filed})"


def peer_snapshot(ticker, info_date, price_date):
    facts = _facts(ticker)
    out = {"ticker": ticker, "company": PEERS[ticker]["name"], "information_cutoff": info_date, "price_date_requested": price_date,
           "business_mix_note": PEERS[ticker]["mix"]}
    for k in ("revenue", "operating_income", "da", "net_income"):
        v, desc, end = ltm(facts, CONCEPTS[k], info_date)
        out[f"ltm_{k}"] = None if v is None else v / 1e6
        out[f"ltm_{k}_source"] = desc
        if k == "revenue":
            out["ltm_period_end"] = end
    bs = balance_date(facts, info_date)
    debt, ddesc, dend = instant(facts, DEBT_CONCEPTS[ticker], info_date, bs)
    cash, cdesc, _ = instant(facts, INSTANT["cash"], info_date, bs)
    nci, ndesc, _ = instant(facts, INSTANT["nci"], info_date, bs)
    out.update({"debt": debt / 1e6, "debt_source": ddesc, "balance_sheet_date": dend,
                "cash": cash / 1e6, "cash_source": cdesc,
                "nci": (nci or 0.0) / 1e6, "nci_source": ndesc if nci is not None else "no MinorityInterest fact: treated as 0"})
    sh, sdesc = latest_quarter_shares(facts, info_date)
    px, pdate = price_asof(ticker, price_date)
    out.update({"shares_m_proxy": sh / 1e6, "shares_basis": "diluted_weighted_average_latest_quarter (proxy, not shares outstanding)",
                "shares_source": sdesc, "price": px, "price_date": pdate,
                "price_source": f"Yahoo Finance chart API close on {pdate}, later splits undone"})
    out["market_cap"] = out["shares_m_proxy"] * px
    out["enterprise_value"] = out["market_cap"] + out["debt"] - out["cash"] + out["nci"]
    out["ltm_ebitda"] = (out["ltm_operating_income"] + out["ltm_da"]) if out["ltm_da"] is not None else None
    return out


NM_CAP = 60.0  # multiples above this (or with a non-positive denominator) are flagged not meaningful


def multiples(s):
    res = {}
    for name, num, den in (("ev_revenue", "enterprise_value", "ltm_revenue"), ("ev_ebitda", "enterprise_value", "ltm_ebitda"),
                           ("ev_ebit", "enterprise_value", "ltm_operating_income"), ("pe", "market_cap", "ltm_net_income")):
        d = s.get(den)
        if d is None or d <= 0:
            res[name], res[name + "_flag"] = None, "not meaningful (non-positive or missing denominator)"
            continue
        m = s[num] / d
        flag = "ok"
        if m > NM_CAP:
            flag = f"not meaningful (> {NM_CAP:.0f}x)"
        if s["ticker"] == "NFLX" and name in ("ev_ebitda", "ev_ebit"):
            flag = "excluded: content amortization sits in cost of revenues, so EBITDA/EBIT are not comparable"
        elif s["ticker"] == "NFLX":
            flag = ("excluded from ranges: high-growth streaming model priced on subscriber growth, not on current revenue or "
                    "earnings; shown for reference")
        if name == "pe" and s["information_cutoff"] >= "2018-02-01":
            flag = ("not meaningful: LTM net income includes the December 2017 quarter, in which US companies remeasured "
                    "deferred taxes under the Tax Cuts and Jobs Act")
        if s["ticker"] == "DIS":
            flag = ("reference only (acquirer; excluded from medians). Disney tags total segment operating income as "
                    "OperatingIncomeLoss, so its EV/EBIT is on a segment basis")
        res[name], res[name + "_flag"] = m, flag
    return res
