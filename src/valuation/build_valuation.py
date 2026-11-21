"""Stage 3: build the valuation (two dated perspectives), comparables, transaction analysis and checks.

Perspectives (never mixed):
  A_announcement_2017-12 : valuation date 2017-12-14 (announcement), market data at the 2017-12-13 close.
                           Uses only documents dated on or before 2017-12-14. No management forecasts were public,
                           so projections are labelled estimates.
  B_proxy_2018-05        : valuation date 2018-05-30 (May 2018 joint proxy filed), market data at the 2018-05-30 close.
                           Uses the management forecasts disclosed in that proxy. The June 2018 updated forecasts are
                           subsequent information and appear only in a separate comparison.

Outputs (data/processed/): dcf_assumptions.csv, valuation_outputs.csv, valuation_sensitivity.csv,
comparable_companies.csv, dcf_projections.csv, management_forecasts.csv; checks appended to verification_checks.csv.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import dcf  # noqa: E402
import forecasts  # noqa: E402
import market_data as md  # noqa: E402
import peers  # noqa: E402
import wacc as waccmod  # noqa: E402
from build_transaction import find_quote  # noqa: E402  (page-aware quote finder from Stage 1)
from sec_tables import load_tables  # noqa: E402

PROC = ROOT / "data" / "processed"
HF = pd.read_csv(PROC / "historical_financials.csv", low_memory=False, dtype={"source_page": str})
TA = pd.read_csv(PROC / "transaction_assumptions.csv", dtype={"source_page": str})
REG = pd.read_csv(PROC / "source_register.csv", dtype=str)
FILED = dict(zip(REG.source_id, REG.filing_date))

ASSUMPTIONS, OUTPUTS, SENS, CHECKS, PROJ, COMPS = [], [], [], [], [], []

PERSPECTIVES = {
    "A_announcement_2017-12": {"valuation_date": date(2017, 12, 14), "market_date": "2017-12-13", "info_cutoff": "2017-12-14"},
    "B_proxy_2018-05": {"valuation_date": date(2018, 5, 30), "market_date": "2018-05-30", "info_cutoff": "2018-05-30"},
}


# --------------------------------------------------------------------------------------------- helpers
def assume(persp, category, parameter, value, unit, value_type, source, observation_date, available_date, method,
           low=None, high=None):
    cutoff = PERSPECTIVES[persp]["info_cutoff"] if persp in PERSPECTIVES else "9999-12-31"
    ok = (not available_date) or available_date <= cutoff
    ASSUMPTIONS.append({"perspective": persp, "category": category, "parameter": parameter, "value": value, "unit": unit,
                        "value_type": value_type, "source": source, "observation_date": observation_date,
                        "available_date": available_date, "method": method,
                        "sensitivity_low": "" if low is None else low, "sensitivity_high": "" if high is None else high})
    CHECKS.append({"check_type": "valuation_lookahead", "entity": "RemainCo", "source_id": source[:80], "fiscal_period": persp,
                   "item": parameter, "expected": f"available <= {cutoff}", "observed": available_date,
                   "status": "pass" if ok else "fail", "detail": category})
    return value


def quote(doc_id, text):
    found, page = find_quote(doc_id, text)
    if not found:
        raise AssertionError(f"quote not found in {doc_id}: {text[:80]}")
    CHECKS.append({"check_type": "valuation_input_quote", "entity": "", "source_id": doc_id, "fiscal_period": "",
                   "item": text[:120], "expected": "found", "observed": f"page {page or 'unnumbered'}", "status": "pass", "detail": ""})
    return f"{doc_id} p.{page or 'unnumbered'}"


def table_fact(doc_id, row_label, expect_first=None, contains=None):
    """Find a table row by label (and optional co-occurring label); return (values, raw cells, 'doc p.N tI')."""
    for t in load_tables(doc_id):
        labs = [r[0] for r in t.rows]
        if any(l.startswith(row_label) for l in labs) and (contains is None or any(l.startswith(contains) for l in labs)):
            r = next(r for r in t.rows if r[0].startswith(row_label))
            ok = expect_first is None or (r[1] and abs(r[1][0] - expect_first) < 1e-9) or expect_first in r[2]
            CHECKS.append({"check_type": "valuation_input_table", "entity": "", "source_id": doc_id, "fiscal_period": "",
                           "item": row_label, "expected": expect_first, "observed": r[2][1:4], "status": "pass" if ok else "fail",
                           "detail": f"table {t.index} p.{t.page}"})
            return r[1], r[2], f"{doc_id} p.{t.page} t{t.index}"
    raise AssertionError(f"table row {row_label!r} not found in {doc_id}")


def hf(entity, fp, item, source_id=None, statement=None, perimeter=None, primary=True):
    q = HF[(HF.entity == entity) & (HF.fiscal_period == fp) & (HF.line_item == item)]
    if source_id:
        q = q[q.source_id == source_id]
    if statement:
        q = q[q.statement == statement]
    if perimeter:
        q = q[q.perimeter == perimeter]
    if primary and not source_id:
        q = q[q.is_primary]
    if len(q) != 1:
        raise ValueError(f"{entity} {fp} {item} {source_id}: {len(q)} rows")
    r = q.iloc[0]
    return float(r.value), f"{r.source_id} p.{r.source_page} [{r.record_id}]"


def hf_label(entity, fp, label, source_id):
    q = HF[(HF.entity == entity) & (HF.fiscal_period == fp) & (HF.line_item_reported == label) & (HF.source_id == source_id)]
    r = q.iloc[0]
    return float(r.value), f"{r.source_id} p.{r.source_page} [{r.record_id}]"


def ta(id_):
    r = TA[TA.id == id_].iloc[0]
    return float(r.value), f"transaction_assumptions {id_} ({r.source_id} p.{r.source_page})"


def out(persp, method, case, metric, value, unit, value_type, notes=""):
    OUTPUTS.append({"perspective": persp, "method": method, "case": case, "metric": metric,
                    "value": round(value, 4) if isinstance(value, float) else value, "unit": unit,
                    "value_type": value_type, "notes": notes})


def check(ctype, item, expected, observed, tol, persp="", detail=""):
    ok = abs(float(expected) - float(observed)) <= tol
    CHECKS.append({"check_type": ctype, "entity": "RemainCo", "source_id": "", "fiscal_period": persp, "item": item,
                   "expected": round(float(expected), 6), "observed": round(float(observed), 6),
                   "status": "pass" if ok else "fail", "detail": detail})
    return ok


def fx(d):
    return md.asof(md.fred("DEXUSUK"), d)


# --------------------------------------------------------------------------------------------- market inputs
def market_inputs(persp):
    p = PERSPECTIVES[persp]
    man = md.manifest()
    rf, rf_d = md.asof(md.fred("DGS10"), p["market_date"])
    kd, kd_d = md.asof(md.fred("DBAA"), p["market_date"])
    erp_year = 2016 if persp.startswith("A") else 2017
    erp, col = md.implied_erp(erp_year)
    avail_erp = f"{erp_year + 1}-01-31"
    assume(persp, "wacc", "risk_free_rate", rf / 100, "ratio", "market", man["FRED_DGS10.csv"]["url"], rf_d, rf_d,
           "10-year US Treasury constant-maturity yield (FRED DGS10) on the market-data date")
    assume(persp, "wacc", "equity_risk_premium", erp, "ratio", "market", man["DAMODARAN_histimpl.html"]["url"],
           f"{erp_year}-12-31", avail_erp,
           f"Damodaran implied ERP ({col}) at the end of {erp_year}, the latest value published before the valuation date "
           f"(published in January {erp_year + 1}; that availability date is an approximation)", 0.045, 0.065)
    assume(persp, "wacc", "pretax_cost_of_debt", kd / 100, "ratio", "market", man["FRED_DBAA.csv"]["url"], kd_d, kd_d,
           "Moody's seasoned Baa corporate yield (FRED DBAA). 21CF senior debt was rated Baa1/BBB+ "
           f"({table_fact('FOX_10K_FY2017', 'Moody', 'Baa1')[2]}); a Baa average slightly overstates the yield for Baa1.")
    return rf / 100, erp, kd / 100


def tax_rate(persp):
    fed, _, s1 = table_fact("FOX_10K_FY2017", "U.S. federal income tax rate", 35.0, contains="State and local taxes")
    st, _, _ = table_fact("FOX_10K_FY2017", "State and local taxes", 1.0, contains="U.S. federal income tax rate")
    src = f"{s1} rate reconciliation (federal {fed[0]:.0f}%, state and local {st[0]:.0f}% in FY2017)"
    if persp.startswith("A"):
        return assume(persp, "tax", "marginal_tax_rate", 0.36, "ratio", "estimate", src, "2017-06-30", FILED["FOX_10K_FY2017"],
                      "35% US federal statutory rate + ~1% state and local (21CF FY2017 rate reconciliation). The Tax Cuts and "
                      "Jobs Act (21% federal) was not law on 14 Dec 2017 (enacted 22 Dec 2017), so it enters only as a "
                      "sensitivity / bull-case item.", 0.22, 0.36)
    return assume(persp, "tax", "marginal_tax_rate", 0.22, "ratio", "estimate", src + "; Tax Cuts and Jobs Act (21% federal, effective 1 Jan 2018)",
                  "2018-01-01", "2017-12-22",
                  "21% federal (TCJA, enacted 22 Dec 2017) + ~1% state and local (21CF FY2017 rate reconciliation).", 0.21, 0.26)


def peer_set(persp):
    p = PERSPECTIVES[persp]
    snaps = []
    for t in ("CMCSA", "AMCX", "NFLX", "DIS"):
        s = peers.peer_snapshot(t, p["info_cutoff"], p["market_date"])
        s.update(peers.multiples(s))
        s["perspective"] = persp
        snaps.append(s)
        COMPS.append(s)
    return snaps


def build_wacc(persp, tax):
    rf, erp, kd = market_inputs(persp)
    snaps = [s for s in peer_set(persp) if s["ticker"] in ("CMCSA", "AMCX", "NFLX")]
    w = waccmod.compute(rf, erp, kd, tax, [{"ticker": s["ticker"], "debt": s["debt"], "market_cap": s["market_cap"]} for s in snaps],
                        PERSPECTIVES[persp]["market_date"])
    for b in w["peer_betas"]:
        assume(persp, "wacc_beta", f"beta_{b['ticker']}", round(b["unlevered_beta"], 4), "beta", "derived",
               "Yahoo Finance weekly closes vs ^GSPC; SEC XBRL debt; diluted-share proxy market cap", PERSPECTIVES[persp]["market_date"],
               PERSPECTIVES[persp]["market_date"],
               f"raw {b['raw_beta']:.3f} ({b['weeks']} weekly returns, 2y) -> Blume {b['adjusted_beta']:.3f} -> unlevered at "
               f"D/E {b['d_e']:.3f}, tax {tax:.0%}")
    for k, unit, how in (("unlevered_beta_median", "beta", "median of peer unlevered betas (Comcast, AMC Networks, Netflix)"),
                         ("target_d_v", "ratio", "median peer market D/(D+E)"),
                         ("relevered_beta", "beta", "Hamada relevering at target D/E"),
                         ("cost_of_equity", "ratio", "rf + beta x ERP"), ("kd_aftertax", "ratio", "Baa yield x (1 - tax)"),
                         ("wacc", "ratio", "E/V x ke + D/V x kd x (1 - t)")):
        assume(persp, "wacc", k, round(w[k], 6), unit, "derived", "computed", PERSPECTIVES[persp]["market_date"],
               PERSPECTIVES[persp]["market_date"], how)
    # checks
    check("valuation_wacc", "weights sum to 1", 1.0, w["weight_equity"] + w["weight_debt"], 1e-12, persp)
    check("valuation_wacc", "cost of equity = rf + beta x ERP", w["rf"] + w["relevered_beta"] * w["erp"], w["cost_of_equity"], 1e-12, persp)
    check("valuation_wacc", "WACC recomputed", w["weight_equity"] * w["cost_of_equity"] + w["weight_debt"] * w["kd_pretax"] * (1 - tax),
          w["wacc"], 1e-12, persp)
    CHECKS.append({"check_type": "valuation_wacc", "entity": "RemainCo", "source_id": "", "fiscal_period": persp,
                   "item": "WACC within plausible 4%-12% band", "expected": "0.04-0.12", "observed": round(w["wacc"], 6),
                   "status": "pass" if 0.04 <= w["wacc"] <= 0.12 else "fail", "detail": ""})
    for k in ("rf", "erp", "relevered_beta", "cost_of_equity", "kd_pretax", "kd_aftertax", "weight_debt", "wacc"):
        out(persp, "WACC", "base", k, w[k], "beta" if "beta" in k else "ratio", "derived" if k not in ("rf", "erp", "kd_pretax") else "market")
    return w


# --------------------------------------------------------------------------------------------- perspective A
def build_A():
    P = "A_announcement_2017-12"
    vd = PERSPECTIVES[P]["valuation_date"]
    tax = tax_rate(P)
    w = build_wacc(P, tax)

    # Base year (FY2017, Jun) of the acquired perimeter from public information at announcement
    rev21, s_rev = hf("21CF", "FY2017", "revenue", statement="income_statement")
    oibda21 = float(HF[(HF.source_id == "FOX_10K_FY2017") & (HF.fiscal_period == "FY2017") & (HF.line_item == "segment_oibda") &
                       (HF.segment == "Total Segment OIBDA")].value.iloc[0])
    q_nf = quote("FOX_8K_20171214_EX99_2", "Using Fiscal 2017 as a base, Fox is expected to have annual revenue of approximately $10 billion and EBITDA of")
    nf_rev, nf_ebitda = 10000.0, 2800.0
    base_rev = assume(P, "base_year", "remainco_fy2017_revenue", rev21 - nf_rev, "USD_m", "derived",
                      f"{s_rev}; New Fox revenue ~$10bn ({q_nf})", "2017-06-30", "2017-12-14",
                      "21CF FY2017 revenue (28,500) - New Fox FY2017 revenue (~$10bn, rounded in the release). The RemainCo pro forma "
                      "(19,307) was not public until the 2018 proxy; the hindsight gap is about +4%.")
    base_ebitda = assume(P, "base_year", "remainco_fy2017_ebitda", oibda21 - nf_ebitda, "USD_m", "derived",
                         f"FOX_10K_FY2017 p.120 Total Segment OIBDA {oibda21:,.0f}; New Fox EBITDA ~$2.8bn ({q_nf})", "2017-06-30",
                         "2017-12-14",
                         "21CF Total Segment OIBDA - New Fox EBITDA (~$2.8bn). OIBDA-type EBITDA: before D&A, impairment and "
                         "amortization of cable distribution investments.")
    margin = base_ebitda / base_rev
    # growth estimate from 21CF history (ex-DBS disposal)
    r15, _ = hf("21CF", "FY2015", "revenue", statement="income_statement")
    r16, _ = hf("21CF", "FY2016", "revenue", statement="income_statement")
    dbs15 = float(HF[(HF.source_id == "FOX_10K_FY2017") & (HF.fiscal_period == "FY2015") & (HF.segment == "Direct Broadcast Satellite Television")
                     & (HF.line_item == "segment_revenue")].value.iloc[0])
    g16, g17 = r16 / (r15 - dbs15) - 1, rev21 / r16 - 1
    growth = assume(P, "projection", "revenue_growth", round((g16 + g17) / 2, 4), "ratio", "estimate",
                    "historical_financials.csv (21CF FY2015-FY2017, FY2017 10-K basis)", "2017-06-30", FILED["FOX_10K_FY2017"],
                    f"Average 21CF growth excluding the DBS disposal: FY2016 {g16:.1%}, FY2017 {g17:.1%}. Applied flat FY2018-FY2022.",
                    0.01, 0.05)
    assume(P, "projection", "ebitda_margin", round(margin, 4), "ratio", "derived", "base-year EBITDA / revenue", "2017-06-30", "2017-12-14",
           "Held flat at the FY2017 derived margin (no cost synergies).", round(margin - 0.02, 4), round(margin + 0.02, 4))
    da21, s_da = hf("21CF", "FY2017", "depreciation_amortization", statement="income_statement")
    da_pct = assume(P, "projection", "da_pct_revenue", round(-da21 / rev21, 4), "ratio", "estimate", s_da, "2017-06-30",
                    FILED["FOX_10K_FY2017"], "21CF consolidated D&A / revenue FY2017; RemainCo-specific D&A was not public.", 0.015, 0.025)
    capex = [-hf("21CF", f"FY{y}", "capex")[0] for y in (2015, 2016, 2017)]
    revs = [r15, r16, rev21]
    capex_pct = assume(P, "projection", "capex_pct_revenue", round(sum(capex) / sum(revs), 4), "ratio", "estimate",
                       "historical_financials.csv 21CF capex FY2015-FY2017", "2017-06-30", FILED["FOX_10K_FY2017"],
                       "21CF consolidated capex / revenue, FY2015-FY2017 aggregate. New Fox kept the studio lot and TV stations, so "
                       "this may overstate RemainCo capex.", 0.010, 0.020)
    inv = [-hf_label("21CF", f"FY{y}", "Inventories net of program rights payable", "FOX_10K_FY2017")[0] for y in (2015, 2016, 2017)]
    nwc_pct = assume(P, "projection", "content_and_wc_investment_pct_revenue", round(sum(inv) / sum(revs), 4), "ratio", "estimate",
                     "FOX_10K_FY2017 p.71 cash flow line 'Inventories net of program rights payable' FY2015-FY2017",
                     "2017-06-30", FILED["FOX_10K_FY2017"],
                     "Content investment in excess of amortization: 21CF's cash outflow for inventories net of program rights "
                     "payable, as % of revenue (FY2015-FY2017 aggregate). Other working-capital lines are omitted (volatile).",
                     0.015, 0.045)
    g = assume(P, "terminal", "terminal_growth", 0.02, "ratio", "estimate", "judgement", "", "",
               "Long-run nominal growth below the 10-year Treasury yield (2.36%) and nominal GDP; range 1.0%-3.0%.", 0.01, 0.03)

    def years(gr=growth, m=margin, cap=capex_pct, nwc=nwc_pct, t=tax, da=da_pct):
        ys = []
        for i, y in enumerate(range(2018, 2023), start=1):
            R = base_rev * (1 + gr) ** i
            ys.append(dcf.Year(f"FY{y}", date(y - 1, 7, 1), date(y, 6, 30), R, m * R, da * R, cap * R, nwc * R, t))
        return ys

    def run(**kw):
        wv = kw.pop("wacc", w["wacc"])
        gg = kw.pop("g", g)
        ys = years(**kw)
        ys[-1].compute()
        return dcf.value(ys, vd, wv, gg, ys[-1].rows["fcff"])

    base = run()
    bridge = bridge_A(P, vd)
    shares = bridge["shares"]
    record_case(P, "DCF", "base (estimates)", base, bridge, shares)
    # FCFF identity checks
    for r in base["table"]:
        check("valuation_fcff", f"{r['fy']} FCFF = EBITDA - tax - capex - dNWC", r["ebitda"] - r["taxes_on_ebit"] - r["capex"] - r["dnwc"],
              r["fcff"], 1e-6, P)
    tv_check(P, base)
    sensitivities(P, run, bridge, shares, w["wacc"], g,
                  margin_fn=lambda d: run(m=margin + d), growth_fn=lambda d: run(gr=growth + d),
                  capex_fn=lambda d: run(cap=capex_pct + d), conv_fn=lambda d: run(nwc=nwc_pct + d))
    scen = {"bear": run(gr=0.01, m=margin - 0.02, nwc=0.045, g=0.015),
            "base": base,
            "bull": run(gr=0.05, m=margin + 0.02, nwc=0.015, g=0.025, t=0.22)}
    notes = {"bear": "growth 1%, margin -2pp, content investment 4.5% of revenue, g 1.5%",
             "base": "estimates as listed in dcf_assumptions.csv",
             "bull": "growth 5%, margin +2pp, content investment 1.5%, g 2.5%, 22% tax (TCJA, pending at the date)"}
    for k, v in scen.items():
        record_case(P, "DCF scenario", k, v, bridge, shares, notes[k], projections=False)
    comps_apply(P, {"revenue": base_rev, "ebitda": base_ebitda, "ebit": base_ebitda - da_pct * base_rev},
                "RemainCo FY2017 (Jun) derived from 21CF 10-K and the 14 Dec 2017 release; EBIT uses estimated D&A", bridge, shares)
    return base, bridge


def bridge_A(P, vd):
    f = json.loads((ROOT / "data/raw/xbrl/companyfacts_CIK0001308161_Twenty_First_Century_Fox.json").read_text())["facts"]
    bs = peers.balance_date(f, "2017-12-14")
    get = lambda c: peers.instant(f, [c], "2017-12-14", bs)[0] / 1e6
    debt = get("LongTermDebtCurrent") + get("LongTermDebtNoncurrent")
    cash = get("CashAndCashEquivalentsAtCarryingValue")
    nci = get("MinorityInterest") + get("RedeemableNoncontrollingInterestEquityCarryingAmount")
    src_bs = f"21CF 10-Q for 30 Sep 2017 via SEC XBRL (filed {bs} quarter; accn 0001564590-17-022900)"
    assume(P, "bridge", "debt", debt, "USD_m", "reported", src_bs, bs, "2017-11-08", "Borrowings current + non-current; all 21CF debt stays with RemainCo")
    assume(P, "bridge", "cash", cash, "USD_m", "reported", src_bs, bs, "2017-11-08", "Cash and cash equivalents")
    assume(P, "bridge", "noncontrolling_interests", nci, "USD_m", "reported", src_bs, bs, "2017-11-08",
           "Book NCI + redeemable NCI of consolidated 21CF (includes any New Fox-related NCI, which cannot be separated)")
    q_net = quote("DIS_8K_20171214_EX99_1", "Disney will also assume approximately $13.7 billion of net debt of 21st Century Fox.")
    # Sky stake at 21CF's agreed offer price
    q15 = quote("FOX_10K_FY2017", "at a price of £10.75 per Sky share (approximately $15 billion in the aggregate)")
    q39 = quote("DIS_8K_20171214_EX99_1", "approximately 39.1 per cent of the issued shares of Sky")
    fx16, fx16d = fx("2016-12-15")
    fxa, fxad = fx("2017-12-13")
    gbp_offer = 15000 / fx16
    sky_gbp = gbp_offer * 39.1 / 60.9
    sky = sky_gbp * fxa
    assume(P, "bridge", "sky_39pct_stake", round(sky, 1), "USD_m", "estimate", f"{q15}; {q39}; FRED DEXUSUK {fx16d} and {fxad}",
           "2017-12-13", "2017-12-14",
           f"21CF's £10.75 offer for the 60.9% it did not own was ~$15bn at the 15 Dec 2016 rate ({fx16:.4f} $/£) = £{gbp_offer:,.0f}m; "
           f"the 39.1% stake at the same price = £{sky_gbp:,.0f}m, converted at {fxa:.4f} $/£. Market value of Sky, not the book value (3,175).",
           round(sky * 0.9, 1), round(sky * 1.163, 1))
    other_inv = 262.0 + 465.0
    q_inv = "FOX_10K_FY2017 p.89 investments table (Endemol Shine 262, Other 465; Sky 3,175 excluded)"
    assume(P, "bridge", "other_investments_book", other_inv, "USD_m", "reported", q_inv, "2017-06-30", FILED["FOX_10K_FY2017"],
           "Book value of non-Sky investments (Hulu 30% is inside 'Other' at book; its market value is not captured)")
    shares = 1052.536963 + 798.520953
    q_sh = quote("FOX_10K_FY2017", "1,052,536,963 shares of Class A Common Stock and 798,520,953 shares of Class B Common Stock were outstanding")
    assume(P, "bridge", "shares_outstanding_m", shares, "shares_m", "reported", q_sh, "2017-08-09", FILED["FOX_10K_FY2017"],
           "21CF Class A + Class B shares outstanding at 9 Aug 2017 (basic; fully diluted count not public until 2018)")
    return {"debt": debt, "cash": cash, "nci": nci, "sky": sky, "other_inv": other_inv, "shares": shares,
            "transaction_tax_net": 0.0, "note_net_debt_release": f"Parties' figure ~$13.7bn ({q_net}); balance-sheet net debt {debt - cash:,.0f}"}


# --------------------------------------------------------------------------------------------- perspective B
def build_B():
    P = "B_proxy_2018-05"
    vd = PERSPECTIVES[P]["valuation_date"]
    tax = tax_rate(P)
    w = build_wacc(P, tax)
    F = pd.read_csv(PROC / "management_forecasts.csv")
    F = F[F.proxy == "JPROXY_ORIG_20180530"]
    for _, r in F.iterrows():
        if r.value_status in ("reported_forecast", "derived"):
            assume(P, "forecast", f"{r.forecast_set}:{r.metric}:{r.fiscal_year}", r.value, "USD_m",
                   "reported_forecast" if r.value_status == "reported_forecast" else "derived",
                   f"JPROXY_ORIG_20180530 p.{r.source_page} t{r.source_table_index}", r.fiscal_year_end, r.available_date,
                   r.definition[:160])
    # decomposition parameters
    t907 = load_tables("JPROXY_ORIG_20180530")[907]
    assert t907.page == "223"
    rv = {lab: vals for lab, vals, _ in t907.rows}
    rc_rev, rc_da = rv["Revenues"][3], -rv["Depreciation and amortization"][3]
    da_pct = assume(P, "projection", "da_pct_revenue", round(rc_da / rc_rev, 4), "ratio", "estimate",
                    "JPROXY_ORIG_20180530 p.223 RemainCo pro forma FY2017 (D&A 388 / revenue 19,307)", "2017-06-30", "2018-05-30",
                    "RemainCo pro forma D&A / revenue, held flat. The forecasts give EBITDA only, so D&A is needed to derive EBIT and taxes.",
                    0.015, 0.025)
    capex_pct = assume(P, "projection", "capex_pct_revenue", 0.0125, "ratio", "estimate",
                       "historical_financials.csv 21CF capex FY2015-FY2017 (aggregate 1.25% of revenue)", "2017-06-30", "2017-08-14",
                       "Not disclosed in the forecasts; 21CF consolidated ratio used. It affects only the split of the (management) "
                       "FCFF between capex and the working-capital residual, not the base FCFF.", 0.010, 0.020)
    g = assume(P, "terminal", "terminal_growth", 0.02, "ratio", "estimate", "judgement", "", "",
               "Long-run nominal growth; range 1.0%-3.0%", 0.01, 0.03)

    def mgmt_years(fs, ufcf_metric, cov_start_first=None):
        d = F[F.forecast_set == fs]
        piv = d.pivot_table(index="fiscal_year", columns="metric", values="value", aggfunc="first")
        piv = piv[[c for c in ("revenue", "ebitda", ufcf_metric) if c in piv]].dropna()
        piv = piv[[not y.endswith("A") for y in piv.index]]
        ys = []
        for fy, r in piv.iterrows():
            y = int(fy[:4])
            cs = date(y - 1, 7, 1)
            if cov_start_first and y == 2018:
                cs = cov_start_first  # 21CF 2018F unlevered FCF covers Q2-Q4 only (proxy footnote 4)
            R, E, U = float(r.revenue), float(r.ebitda), float(r[ufcf_metric])
            da, capx = da_pct * R, capex_pct * R
            ebit = E - da
            nopat = ebit * (1 - tax)
            resid = nopat + da - capx - U   # working capital + other cash items implied by management FCFF
            ys.append(dcf.Year(f"FY{y}", cs, date(y, 6, 30), R, E, da, capx, resid, tax, fcff_reported=U))
        return ys

    cases = {
        "disney_mgmt": mgmt_years("disney_for_remainco_original", "unlevered_fcf"),
        "21cf_mgmt": mgmt_years("21cf_to_advisor_original", "unlevered_fcf_derived", cov_start_first=date(2017, 10, 1)),
    }
    conv_years = {"disney_mgmt": ("FY2024", "FY2028"), "21cf_mgmt": ("FY2020", "FY2022")}
    bridge = bridge_B(P, vd)
    shares = bridge["shares"]
    results = {}
    for cname, ys in cases.items():
        for y in ys:
            y.compute()
            check("valuation_fcff", f"{cname} {y.fy}: rebuilt FCFF equals management unlevered FCF", y.fcff_reported, y.rows["fcff"], 1e-6, P)
            check("valuation_fcff", f"{cname} {y.fy}: FCFF = EBITDA - tax - capex - dNWC",
                  y.rows["ebitda"] - y.rows["taxes_on_ebit"] - y.rows["capex"] - y.rows["dnwc"], y.rows["fcff"], 1e-6, P)
        a, b = conv_years[cname]
        sel = [y for y in ys if a <= y.fy <= b]
        conv = sum(y.rows["fcff"] for y in sel) / sum(y.rows["ebitda"] for y in sel)
        assume(P, "terminal", f"{cname}_terminal_fcff_conversion", round(conv, 4), "ratio", "derived",
               "management_forecasts.csv", "", "2018-05-30",
               f"Sum of unlevered FCF / sum of EBITDA over {a}-{b}; terminal FCFF = final-year EBITDA x conversion "
               "(management FCF is lumpy year to year)")
        results[cname] = (ys, conv)

    def run(cname="disney_mgmt", wacc=None, g_=None, margin_shift=0.0, growth_shift=0.0, resid_shift=0.0, capex_shift=0.0,
            tax_uplift=False):
        ys0, conv = results[cname]
        ys = []
        for i, y in enumerate(ys0):
            k = (1 + growth_shift) ** (i + 1 if y.fy != "FY2018" else 0)
            R = y.revenue * k
            E = (y.ebitda / y.revenue + margin_shift) * R
            capx = (y.capex / y.revenue + capex_shift) * R
            resid = (y.dnwc / y.revenue + resid_shift) * R
            if tax_uplift:  # forecasts may embed pre-TCJA cash taxes: add back (36% - 22%) x EBIT (estimate)
                resid -= (0.36 - 0.22) * (E - y.da / y.revenue * R)
            ys.append(dcf.Year(y.fy, y.coverage_start, y.coverage_end, R, E, y.da / y.revenue * R, capx, resid, tax))
        for y in ys:
            y.compute()
        term = ys[-1].rows["ebitda"] * (conv + (-(capex_shift + resid_shift) * ys[-1].revenue / ys[-1].rows["ebitda"]))
        if tax_uplift:
            term += (0.36 - 0.22) * ys[-1].rows["ebit"]
        return dcf.value(ys, vd, wacc or w["wacc"], g if g_ is None else g_, term)

    base = run()
    record_case(P, "DCF", "base (Disney management forecasts)", base, bridge, shares)
    alt = run("21cf_mgmt")
    record_case(P, "DCF", "alternative (21CF management forecasts to FY2022)", alt, bridge, shares)
    tv_check(P, base)
    tv_check(P, alt, "21cf")
    sensitivities(P, lambda **k: run(**{("g_" if kk == "g" else kk): vv for kk, vv in k.items()}), bridge, shares, w["wacc"], g,
                  margin_fn=lambda d: run(margin_shift=d), growth_fn=lambda d: run(growth_shift=d),
                  capex_fn=lambda d: run(capex_shift=d), conv_fn=lambda d: run(resid_shift=d))
    scen = {"bear": run(margin_shift=-0.01, growth_shift=-0.01, g_=0.015),
            "base": base,
            "bull": run("21cf_mgmt", tax_uplift=True, g_=0.025)}
    notes = {"bear": "Disney forecasts with EBITDA margin -1pp and revenue growth -1pp a year; g 1.5%",
             "base": "Disney management forecasts as disclosed",
             "bull": "21CF management forecasts + estimated TCJA cash-tax uplift (forecasts may embed pre-reform taxes); g 2.5%"}
    for k, v in scen.items():
        record_case(P, "DCF scenario", k, v, bridge, shares, notes[k], projections=False)
    tr = run(tax_uplift=True)
    record_case(P, "DCF", "sensitivity: Disney forecasts + TCJA cash-tax uplift (estimate)", tr, bridge, shares, projections=False)
    comps_apply(P, {"revenue": rc_rev, "ebitda": rv["Revenues"][3] + rv["Operating expenses"][3] + rv["Selling, general and administrative"][3],
                    "ebit": rv["Revenues"][3] + rv["Operating expenses"][3] + rv["Selling, general and administrative"][3]
                    + rv["Depreciation and amortization"][3] + rv["Impairment and restructuring charges"][3]},
                "RemainCo pro forma FY2017 (Jun), May 2018 proxy p.223 (stale by ~11 months; no LTM to Mar 2018 is disclosed)",
                bridge, shares)
    # reference: advisors' multiple range (disclosed in the proxy; not our calculation)
    q_m = quote("JPROXY_ORIG_20180530", "selected CY2018E EBITDA multiple reference ranges of (i) 8.00x – 9.00x for purposes of evaluating RemainCo (excluding Sky)")
    for mlt in (8.0, 9.0):
        ev = mlt * 4506.0
        out(P, "Reference: Disney advisors' CY2018E EBITDA range", f"{mlt:.2f}x x Disney FY2018E EBITDA 4,506", "enterprise_value_ops",
            ev, "USD_m", "derived", f"{q_m}. FY2018E (Jun) EBITDA used as a proxy for CY2018E: a mismatch noted, not adjusted.")
    forecast_comparison()
    return base, bridge


def bridge_B(P, vd):
    t910 = load_tables("JPROXY_ORIG_20180530")[910]
    assert t910.page == "226"
    rows = {lab: vals for lab, vals, _ in t910.rows}
    cur_b, nc_b = None, None
    seen = 0
    for lab, vals, _ in t910.rows:
        if lab == "Borrowings":
            if seen == 0:
                cur_b = vals[3]
            else:
                nc_b = vals[3]
            seen += 1
    cash = rows["Cash and cash equivalents"][3]
    inv = rows["Investments"][3]
    sky_book = -rows["Investments"][5]
    redeem = rows["Redeemable noncontrolling interests"][3]
    src = "JPROXY_ORIG_20180530 p.226 RemainCo pro forma balance sheet at 31 Mar 2018 (column 'RemainCo without Sky')"
    q_div = quote("JPROXY_ORIG_20180530", "Represents an adjustment to record a net dividend of $6.5 billion paid to 21CF by New Fox and a corresponding current taxes payable of $6.5 billion")
    assume(P, "bridge", "debt", cur_b + nc_b, "USD_m", "reported", src, "2018-03-31", "2018-05-30", "Current + non-current borrowings")
    assume(P, "bridge", "cash_excluding_earmarked_dividend", cash - 6500, "USD_m", "derived", f"{src}; {q_div}", "2018-03-31", "2018-05-30",
           f"Pro forma cash {cash:,.0f} less the net $6.5bn New Fox dividend, which is matched by a $6.5bn transaction tax payable "
           "(both excluded so the tax is not double counted)")
    f = json.loads((ROOT / "data/raw/xbrl/companyfacts_CIK0001308161_Twenty_First_Century_Fox.json").read_text())["facts"]
    bs = peers.balance_date(f, "2018-05-30")
    nci_nr = peers.instant(f, ["MinorityInterest"], "2018-05-30", bs)[0] / 1e6
    assume(P, "bridge", "noncontrolling_interests", nci_nr + redeem, "USD_m", "estimate",
           f"{src} (redeemable NCI {redeem:,.0f}); 21CF 10-Q 31 Mar 2018 via SEC XBRL (MinorityInterest {nci_nr:,.0f})", "2018-03-31",
           "2018-05-10", "RemainCo redeemable NCI + consolidated 21CF non-redeemable NCI (RemainCo's own non-redeemable NCI is not disclosed)")
    other_inv = inv - sky_book
    assume(P, "bridge", "other_investments_book", other_inv, "USD_m", "derived", src, "2018-03-31", "2018-05-30",
           f"RemainCo investments {inv:,.0f} less Sky carrying value {sky_book:,.0f} (elimination column of the same table). Hulu at book.")
    q125 = quote("JPROXY_ORIG_20180530", "announced a pre-conditional cash offer for the fully diluted share capital of Sky at an offer price of £12.50 per Sky share")
    fx16, _ = fx("2016-12-15")
    fxb, fxbd = fx("2018-05-30")
    sky_gbp = 15000 / fx16 * 39.1 / 60.9 * 12.50 / 10.75
    sky = sky_gbp * fxb
    assume(P, "bridge", "sky_39pct_stake", round(sky, 1), "USD_m", "estimate", f"{q125}; FRED DEXUSUK {fxbd}", "2018-05-30", "2018-05-30",
           f"Stake value at Comcast's competing £12.50 offer (scaled from the £10.75-based estimate) = £{sky_gbp:,.0f}m at {fxb:.4f} $/£. "
           "Low end: 21CF's own £10.75 offer.", round(sky * 10.75 / 12.50, 1), round(sky * 14.0 / 12.50, 1))
    q_sh = quote("JPROXY_ORIG_20180530", "1,871,147,237, the number of fully diluted shares of 21CF common stock as of the close of business on December 13, 2017")
    shares = 1871.147237
    assume(P, "bridge", "shares_fully_diluted_m", shares, "shares_m", "reported", q_sh, "2017-12-13", "2018-05-30",
           "Fully diluted 21CF shares used in the merger agreement")
    return {"debt": cur_b + nc_b, "cash": cash - 6500, "nci": nci_nr + redeem, "sky": sky, "other_inv": other_inv, "shares": shares,
            "transaction_tax_net": 0.0, "note_net_debt_release": ""}


# --------------------------------------------------------------------------------------------- shared pieces
def equity_from(ev, b):
    return ev + b["sky"] + b["other_inv"] - b["debt"] + b["cash"] - b["nci"]


def record_case(P, method, case, res, b, shares, notes="", projections=True):
    ev = res["enterprise_value"]
    eq = equity_from(ev, b)
    vt = "estimate" if P.startswith("A") else "derived (management forecasts + estimates)"
    out(P, method, case, "enterprise_value_ops", ev, "USD_m", vt, notes)
    out(P, method, case, "pv_explicit_fcff", res["pv_explicit"], "USD_m", vt)
    out(P, method, case, "pv_terminal_value", res["pv_terminal"], "USD_m", vt)
    out(P, method, case, "terminal_value_share_of_ev", res["tv_share_of_ev"], "ratio", "derived")
    out(P, method, case, "enterprise_value_incl_sky_and_investments", ev + b["sky"] + b["other_inv"], "USD_m", vt)
    out(P, method, case, "equity_value", eq, "USD_m", vt)
    out(P, method, case, "equity_value_per_21cf_share", eq / shares, "USD_per_share", vt)
    if method == "DCF" and case.startswith("base"):
        # bridge lines and checks
        for k, lab in (("sky", "plus_sky_39pct_stake"), ("other_inv", "plus_other_investments_book"), ("debt", "less_debt"),
                       ("cash", "plus_cash"), ("nci", "less_noncontrolling_interests")):
            out(P, "Bridge", "base", lab, b[k], "USD_m", "reported/estimate (see dcf_assumptions)")
        out(P, "Bridge", "base", "rsn_treatment", 0.0, "USD_m", "n/a",
            "RSNs are inside enterprise_value_ops (part of the deal perimeter on this date; the DOJ divestiture remedy came "
            "on 27 Jun 2018). They are not added again; see the hindsight rows.")
        check("valuation_bridge", "equity = EV + Sky + other investments - debt + cash - NCI",
              ev + b["sky"] + b["other_inv"] - b["debt"] + b["cash"] - b["nci"], eq, 1e-6, P)
        check("valuation_ev", "EV = PV(explicit FCFF) + PV(terminal value)", res["pv_explicit"] + res["pv_terminal"], ev, 1e-6, P)
        CHECKS.append({"check_type": "valuation_outputs", "entity": "RemainCo", "source_id": "", "fiscal_period": P,
                       "item": "EV, equity value finite and positive", "expected": ">0", "observed": round(eq, 1),
                       "status": "pass" if (math.isfinite(ev) and ev > 0 and eq > 0) else "fail", "detail": ""})
    if projections:
        for r in res["table"]:
            PROJ.append({"perspective": P, "case": case, **{k: (round(v, 6) if isinstance(v, float) else v) for k, v in r.items()}})


def tv_check(P, res, tag=""):
    last = res["terminal_fcff_base"]
    check("valuation_terminal", f"TV = FCFF x (1+g)/(WACC-g) {tag}", last * (1 + res["g"]) / (res["wacc"] - res["g"]),
          res["terminal_value"], 1e-6, P)
    check("valuation_terminal", f"PV(TV) = TV x (1+WACC)^-t {tag}", res["terminal_value"] * (1 + res["wacc"]) ** -res["terminal_discount_time_years"],
          res["pv_terminal"], 1e-6, P)
    CHECKS.append({"check_type": "valuation_terminal", "entity": "RemainCo", "source_id": "", "fiscal_period": P,
                   "item": f"terminal value share of EV below 90% {tag}", "expected": "<0.9", "observed": round(res["tv_share_of_ev"], 4),
                   "status": "pass" if res["tv_share_of_ev"] < 0.9 else "fail", "detail": "flag for over-reliance on TV"})


def sensitivities(P, run, b, shares, w0, g0, margin_fn, growth_fn, capex_fn, conv_fn):
    grid_w = [round(w0 + d, 4) for d in (-0.01, -0.005, 0, 0.005, 0.01)]
    grid_g = [0.01, 0.015, 0.02, 0.025, 0.03]
    evs = {}
    for wv in grid_w:
        for gv in grid_g:
            r = run(wacc=wv, g=gv)
            evs[(wv, gv)] = r["enterprise_value"]
            eq = equity_from(r["enterprise_value"], b)
            SENS.append({"perspective": P, "table": "wacc_x_terminal_growth", "row_param": "wacc", "row_value": wv,
                         "col_param": "terminal_growth", "col_value": gv, "enterprise_value_ops": round(r["enterprise_value"], 1),
                         "equity_value": round(eq, 1), "equity_per_share": round(eq / shares, 3)})
    mono = all(evs[(grid_w[i], gv)] > evs[(grid_w[i + 1], gv)] for i in range(len(grid_w) - 1) for gv in grid_g) and \
        all(evs[(wv, grid_g[j])] < evs[(wv, grid_g[j + 1])] for j in range(len(grid_g) - 1) for wv in grid_w)
    CHECKS.append({"check_type": "valuation_sensitivity", "entity": "RemainCo", "source_id": "", "fiscal_period": P,
                   "item": "EV falls as WACC rises and rises with terminal growth", "expected": "monotonic", "observed": mono,
                   "status": "pass" if mono else "fail", "detail": "5x5 grid"})
    for name, fn, deltas in (("ebitda_margin_shift", margin_fn, (-0.02, -0.01, 0, 0.01, 0.02)),
                             ("revenue_growth_shift", growth_fn, (-0.02, -0.01, 0, 0.01, 0.02)),
                             ("capex_pct_revenue_shift", capex_fn, (-0.005, 0, 0.005, 0.01)),
                             ("content_wc_pct_revenue_shift", conv_fn, (-0.01, -0.005, 0, 0.005, 0.01))):
        vals = []
        for dlt in deltas:
            r = fn(dlt)
            eq = equity_from(r["enterprise_value"], b)
            vals.append(r["enterprise_value"])
            SENS.append({"perspective": P, "table": name, "row_param": name, "row_value": dlt, "col_param": "", "col_value": "",
                         "enterprise_value_ops": round(r["enterprise_value"], 1), "equity_value": round(eq, 1),
                         "equity_per_share": round(eq / shares, 3)})
        inc = all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))
        dec = all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))
        want = inc if name in ("ebitda_margin_shift", "revenue_growth_shift") else dec
        CHECKS.append({"check_type": "valuation_sensitivity", "entity": "RemainCo", "source_id": "", "fiscal_period": P,
                       "item": f"{name}: expected direction", "expected": "increasing" if name in ("ebitda_margin_shift", "revenue_growth_shift") else "decreasing",
                       "observed": want, "status": "pass" if want else "fail", "detail": ""})


def comps_apply(P, metrics, basis_note, b, shares):
    rows = [c for c in COMPS if c["perspective"] == P and c["ticker"] in ("CMCSA", "AMCX", "NFLX")]
    for mname, metric in (("ev_revenue", "revenue"), ("ev_ebitda", "ebitda"), ("ev_ebit", "ebit")):
        used = [c[mname] for c in rows if c[mname + "_flag"] == "ok"]
        excluded = [f"{c['ticker']}: {c[mname + '_flag']}" for c in rows if c[mname + "_flag"] != "ok"]
        if not used:
            out(P, "Comparables", mname, "not_meaningful", "", "", "not_available", "; ".join(excluded))
            continue
        lo, hi = min(used), max(used)
        med = float(pd.Series(used).median())
        for lab, mult in (("low", lo), ("median", med), ("high", hi)):
            ev = mult * metrics[metric]
            eq = equity_from(ev, b)
            note = (f"{lab} multiple {mult:.2f}x of {len(used)} peer(s) x RemainCo {metric} {metrics[metric]:,.0f} ({basis_note}). "
                    f"Excluded: {'; '.join(excluded) or 'none'}")
            out(P, "Comparables", f"{mname} {lab}", "enterprise_value_ops", ev, "USD_m", "derived", note)
            out(P, "Comparables", f"{mname} {lab}", "equity_value_per_21cf_share", eq / shares, "USD_per_share", "derived")
    pe = [c for c in rows if c["pe_flag"] == "ok"]
    out(P, "Comparables", "pe", "note", "", "", "not_available" if not pe else "derived",
        "P/E not applied: " + ("RemainCo net income was not public on this date" if P.startswith("A") else
                               "peer LTM earnings include TCJA deferred-tax remeasurements") + "; peer P/E values are shown in comparable_companies.csv")


def forecast_comparison():
    """June 2018 updated forecasts vs May 2018 (subsequent information; comparison only, not valued)."""
    F = pd.read_csv(PROC / "management_forecasts.csv")
    for a, bset, m in (("disney_for_remainco_original", "disney_for_remainco_updated", ("revenue", "ebitda", "unlevered_fcf")),
                       ("21cf_to_advisor_original", "21cf_to_advisors_updated", ("revenue", "ebitda"))):
        for metric in m:
            x = F[(F.forecast_set == a) & (F.metric == metric)].set_index("fiscal_year").value
            y = F[(F.forecast_set == bset) & (F.metric == metric)].set_index("fiscal_year").value
            for fy in sorted(set(x.index) & set(y.index)):
                if pd.notna(x[fy]) and pd.notna(y[fy]):
                    out("subsequent_info_2018-06", "Forecast revision (not valued)", f"{bset} vs {a}", f"{metric}:{fy}:change",
                        float(y[fy]) - float(x[fy]), "USD_m", "derived",
                        f"June 2018 proxy {float(y[fy]):,.0f} vs May 2018 proxy {float(x[fy]):,.0f}. Subsequent to the B valuation date.")


def hindsight(baseA, bridgeA, baseB, bridgeB):
    """Subsequent information, shown separately and never used in A or B."""
    rsn, s = ta("P20")
    hulu, s2 = ta("P1D")
    skysale, s3 = ta("X03")
    for P, base, b in (("A_announcement_2017-12", baseA, bridgeA), ("B_proxy_2018-05", baseB, bridgeB)):
        out("hindsight", "Hindsight (subsequent information)", P, "enterprise_value_ops_less_rsn_sale_price",
            base["enterprise_value"] - rsn, "USD_m", "derived",
            f"Illustrative only: the DCF EV includes the RSNs; subtracting their Aug 2019 sale price (~$11bn, {s}) shows the value of the "
            "perimeter Disney kept, assuming the DCF valued the RSNs at their sale price. No RSN forecasts were disclosed, so their DCF value is unknown.")
        out("hindsight", "Hindsight (subsequent information)", P, "sky_stake_estimate_vs_actual_sale", skysale - b["sky"], "USD_m", "derived",
            f"Actual Oct 2018 sale proceeds for the 39% Sky stake ({s3}) minus the bridge estimate {b['sky']:,.0f}")
    out("hindsight", "Hindsight (subsequent information)", "Hulu", "hulu_30pct_fair_value_reference", -hulu, "USD_m", "reported",
        f"Fair value of Disney's own previously held 30% Hulu interest at closing ({s2}); 21CF's 30% stake sits at book in both bridges, "
        "so equity values understate this asset by roughly this order of magnitude")


def price_crosscheck():
    for d, v in (("2017-11-03", 98.64), ("2017-12-13", 107.61), ("2018-05-25", 102.20)):
        px, _ = md.price_asof("DIS", d)
        check("valuation_market_data", f"Yahoo DIS close {d} matches proxy-disclosed close", v, px, 0.006, "",
              "JPROXY_ORIG_20180530 p.56 closing price table")


def write():
    def w(path, rows):
        with path.open("w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
    w(PROC / "dcf_assumptions.csv", ASSUMPTIONS)
    w(PROC / "valuation_outputs.csv", OUTPUTS)
    w(PROC / "valuation_sensitivity.csv", SENS)
    w(PROC / "dcf_projections.csv", PROJ)
    keep = ["perspective", "ticker", "company", "information_cutoff", "price_date", "price", "price_source", "shares_m_proxy",
            "shares_basis", "shares_source", "market_cap", "debt", "debt_source", "cash", "cash_source", "nci", "nci_source",
            "balance_sheet_date", "enterprise_value", "ltm_period_end", "ltm_revenue", "ltm_revenue_source", "ltm_operating_income",
            "ltm_operating_income_source", "ltm_da", "ltm_da_source", "ltm_ebitda", "ltm_net_income", "ltm_net_income_source",
            "ev_revenue", "ev_revenue_flag", "ev_ebitda", "ev_ebitda_flag", "ev_ebit", "ev_ebit_flag", "pe", "pe_flag", "business_mix_note"]
    w(PROC / "comparable_companies.csv", [{k: c.get(k) for k in keep} for c in COMPS])
    vc = PROC / "verification_checks.csv"
    with vc.open(encoding="utf-8") as fh:
        existing = [c for c in csv.DictReader(fh) if not (c["check_type"].startswith("valuation_") or c["check_type"] in
                                                          ("forecast_extraction", "transaction_premium"))]
    with vc.open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=["check_type", "entity", "source_id", "fiscal_period", "item", "expected", "observed", "status", "detail"])
        wr.writeheader()
        wr.writerows(existing + CHECKS)


def main():
    import transaction
    forecasts.self_test()
    _, fchecks = forecasts.build()
    CHECKS.extend(fchecks)
    price_crosscheck()
    baseA, bridgeA = build_A()
    baseB, bridgeB = build_B()
    hindsight(baseA, bridgeA, baseB, bridgeB)
    transaction.build(out, check, CHECKS, bridgeA, bridgeB)
    write()
    bad = [c for c in CHECKS if c["status"] not in ("pass", "match")]
    print(f"{len(ASSUMPTIONS)} assumptions, {len(OUTPUTS)} outputs, {len(SENS)} sensitivity rows, {len(CHECKS)} checks, "
          f"{len(bad)} failed")
    for c in bad[:20]:
        print("FAILED", c)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
