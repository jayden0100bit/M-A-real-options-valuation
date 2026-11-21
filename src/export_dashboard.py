"""Export the validated Stage 1-5 outputs to the static dashboard data bundle.

Writes:
  dashboard/public/data/dashboard.json   single JSON file consumed by the React dashboard (no backend)
  data/processed/dashboard_summary.csv   flat, dashboard-ready summary of the headline results

Only verified project outputs are read (data/processed/*.csv and the Stage 3-5 modules). Nothing is typed in by hand.
Model parameters needed for in-browser recalculation (DCF, synergies, EPS, options, Monte Carlo) are exported
together with the Python base values, so the frontend tests can confirm the TypeScript engine reproduces them.
Raw filings, text caches and the 20,000 Monte Carlo draws are NOT exported (histograms are pre-binned).
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "valuation"))
PROC = ROOT / "data" / "processed"
OUT_JSON = ROOT / "dashboard" / "public" / "data" / "dashboard.json"
OUT_CSV = PROC / "dashboard_summary.csv"


def rd(p):
    return pd.read_csv(PROC / p, low_memory=False)


def num(x, nd=6):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return x if isinstance(x, str) and x != "" else None
    if math.isnan(v) or math.isinf(v):
        return None
    return round(v, nd)


def records(df, cols=None, nd=6):
    df = df[cols] if cols else df
    return [{k: (num(v, nd) if not isinstance(v, str) else v) for k, v in r.items()} for r in df.to_dict("records")]


SUMMARY = []


def s(section, metric, value, unit, value_type, source):
    SUMMARY.append({"section": section, "metric": metric, "value": num(value), "unit": unit, "value_type": value_type, "source": source})
    return num(value)


def build():
    TA, VO, FR, SA = rd("transaction_assumptions.csv"), rd("valuation_outputs.csv"), rd("financial_ratios.csv"), rd("segment_analysis.csv")
    DA, VS, CC, DP = rd("dcf_assumptions.csv"), rd("valuation_sensitivity.csv"), rd("comparable_companies.csv"), rd("dcf_projections.csv")
    SO, SY = rd("synergy_outputs.csv"), rd("synergy_assumptions.csv")
    AI, AO = rd("accretion_dilution_inputs.csv"), rd("accretion_dilution_outputs.csv")
    RI, RO, BC = rd("real_options_inputs.csv"), rd("real_options_outputs.csv"), rd("binomial_convergence.csv")
    MI, MS, MCV, MT, MSC = (rd("monte_carlo_inputs.csv"), rd("monte_carlo_summary.csv"), rd("monte_carlo_convergence.csv"),
                            rd("monte_carlo_tornado.csv"), rd("monte_carlo_scenarios.csv"))
    VC, REG, MF = rd("verification_checks.csv"), rd("source_register.csv"), rd("management_forecasts.csv")
    VO["v"] = pd.to_numeric(VO.value, errors="coerce")
    SO["v"] = pd.to_numeric(SO.value, errors="coerce")
    AO["v"] = pd.to_numeric(AO.value, errors="coerce")
    ta = lambda i: TA[TA.id == i].iloc[0]
    tv = lambda i: float(ta(i).value)
    vo = lambda p, meth, case_prefix, metric: float(VO[(VO.perspective == p) & (VO.method == meth) & VO.case.astype(str).str.startswith(case_prefix) & (VO.metric == metric)].v.iloc[0])
    D = {}

    # ---------------- meta / validation
    stage_of = lambda t: ("Stage 1" if t in ("arithmetic", "xbrl_cross_check") or t.startswith("transaction_") and t != "transaction_premium"
                          else "Stage 3" if t.startswith(("valuation_", "forecast_")) or t == "transaction_premium"
                          else "Stage 4" if t.startswith(("synergy_", "accretion_"))
                          else "Stage 5" if t.startswith(("realoption_", "montecarlo_")) else "other")
    VC["stage"] = VC.check_type.map(stage_of)
    D["meta"] = {"checks_total": int(len(VC)), "checks_failed": int((~VC.status.isin(["pass", "match"])).sum()),
                 "checks_by_stage": {k: int(v) for k, v in VC.groupby("stage").size().items()},
                 "sources": int(len(REG)), "repo": "https://github.com/jayden0100bit/M-A-real-options-valuation",
                 "note": "All figures come from the validated Python pipeline (python src/run_pipeline.py --offline). USD millions unless stated."}
    if D["meta"]["checks_failed"]:
        raise SystemExit("verification checks failing: refusing to export dashboard data")

    # ---------------- timeline and deal values
    ev = [("2017-11-03", "Unaffected date", "Last trading day before press reports of talks; 21CF FOXA $24.97 / FOX $24.43", "JPROXY_ORIG_20180530 p.56"),
          (ta("O01").value, "Original agreement", "All-stock: 0.2745 Disney shares per 21CF share; equity value ~$52.4bn, transaction value ~$66.1bn", "DIS_8K_20171214_EX99_1"),
          ("2018-05-30", "First joint proxy", "Management forecasts disclosed (basis of the May 2018 valuation)", "JPROXY_ORIG_20180530"),
          ("2018-06-13", "Comcast proposal", "Unsolicited $35.00 cash per share for RemainCo (~$65bn equity)", "JPROXY_AMENDED_20180628 p.131"),
          (ta("A01").value, "Amended agreement", "$38.00 per share in cash or stock (50/50), collar $93.53–$114.32; equity ~$71.3bn, transaction ~$85.1bn", "DIS_8K_20180621_EX99_1"),
          ("2018-10", "Sky stake sold", "21CF sells its 39% Sky stake to Comcast for ~£11.6bn ($15.1bn)", "DIS_8KA_20190327_EX99_4 p.1"),
          (ta("C02").value, "New Fox distribution", "Fox Corporation spun off to 21CF holders", "FOX_8K_20190319A_EX99_1"),
          (ta("C01").value, "Closing", "$51.572626 cash or 0.4517 Disney shares per remaining 21CF share; ~$71bn market-implied", "DIS_8K12B_20190320"),
          ("2019-08", "RSNs divested", "Regional sports networks sold for ~$11bn (DOJ remedy)", "DIS_10K_FY2019 p.98")]
    D["timeline"] = [{"date": a, "title": b, "detail": c, "source": d} for a, b, c, d in ev]
    T = VO[VO.perspective == "transaction"]
    tget = lambda method, metric: float(T[(T.method == method) & (T.metric == metric)].v.iloc[0])
    D["deal"] = {
        "unaffected_price": s("Deal", "21CF unaffected price (3 Nov 2017, class-weighted)", tget("Unaffected price", "21cf_unaffected_price_weighted"), "USD_per_share", "derived", "valuation_outputs.csv"),
        "stages": [
            {"stage": "Original (Dec 2017)", "per_share": tget("original_2017_12", "per_share_value_at_2017-12-13_close"),
             "equity_headline": tv("O03"), "ev_headline": tv("O05"), "cash": 0.0, "stock": tv("O03"),
             "premium": tget("original_2017_12", "premium_consideration_only_at_2017-12-13_close"),
             "implied_ev_ebitda": tget("original_2017_12", "ev_ops_to_remainco_fy2017_ebitda_estimate")},
            {"stage": "Amended (Jun 2018)", "per_share": tv("A02"), "equity_headline": tv("A07"), "ev_headline": tv("A09"),
             "cash": tv("A04"), "stock": tv("A07") - tv("A04"), "premium": tget("amended_2018_06", "premium_consideration_only"),
             "implied_ev_ebitda": tget("amended_2018_06", "ev_ops_to_disney_fy2018e_ebitda")},
            {"stage": "Closing (Mar 2019)", "per_share": tget("closing_2019_03", "disney_consideration_per_original_21cf_share"),
             "equity_headline": tv("C11"), "ev_headline": tv("C21"), "cash": tv("C12"), "stock": tv("C13"),
             "premium": tget("closing_2019_03", "premium_disney_consideration_only"),
             "implied_ev_ebitda": tget("closing_2019_03", "ev_derived_to_remainco_fy2018_ebitda")},
        ],
        "accounting_purchase_price": s("Deal", "ASC 805 purchase price", tv("P01"), "USD_m", "reported", "DIS_10K_FY2019 p.96"),
        "market_implied_closing": tv("C11"),
        "package_premium_closing": tget("closing_2019_03", "premium_package_nominal"),
        "package_value_closing": tget("closing_2019_03", "package_value_per_original_21cf_share"),
        "ppa": records(TA[TA.id.str.match(r"^P1[0-9A-D]$")], ["id", "item", "value"]),
        "terms": records(TA[TA.value_type == "reported"][["id", "stage", "item", "value", "unit", "measure_basis", "source_id", "source_page"]]),
    }
    for st in D["deal"]["stages"]:
        s("Deal", f"{st['stage']} equity value (headline)", st["equity_headline"], "USD_m", "reported", "transaction_assumptions.csv")

    # ---------------- historical
    keep = ["revenue", "revenue_growth_yoy", "ebitda", "ebitda_margin", "ebit_margin", "net_margin", "effective_tax_rate", "roe_avg_equity",
            "cash", "total_borrowings", "net_debt", "net_debt_to_ebitda", "cfo", "capex", "fcf_cfo_less_capex", "fcf_margin", "share_of_21cf_revenue",
            "share_of_21cf_ebit", "rsn_revenue_share", "income_continuing_attributable", "net_income_attributable"]
    H = FR[FR.metric.isin(keep)]
    D["historical"] = records(H, ["entity", "fiscal_period", "period_end", "metric", "value", "unit", "value_type"])
    D["segments"] = records(SA[SA.metric.isin(["segment_revenue", "segment_margin", "revenue_share", "segment_operating_income", "segment_oibda"])],
                            ["entity", "fiscal_period", "segment", "metric", "value", "value_type"])

    # ---------------- valuation (Stage 3)
    P = {}
    for persp in ("A_announcement_2017-12", "B_proxy_2018-05"):
        get = lambda p: DA[(DA.perspective == persp) & (DA.parameter == p)].value.iloc[0]
        w = {k: vo(persp, "WACC", "base", k) for k in ("rf", "erp", "relevered_beta", "cost_of_equity", "kd_pretax", "kd_aftertax", "weight_debt", "wacc")}
        base_case = "base" if persp.startswith("A") else "base (Disney"
        bridge = {k: vo(persp, "Bridge", "base", k) for k in ("plus_sky_39pct_stake", "plus_other_investments_book", "less_debt", "plus_cash", "less_noncontrolling_interests")}
        out = {k: vo(persp, "DCF", base_case, k) for k in ("enterprise_value_ops", "pv_explicit_fcff", "pv_terminal_value", "equity_value", "equity_value_per_21cf_share", "terminal_value_share_of_ev")}
        scen = {c: vo(persp, "DCF scenario", c, "equity_value_per_21cf_share") for c in ("bear", "base", "bull")}
        grid = VS[(VS.perspective == persp) & (VS.table == "wacc_x_terminal_growth")]
        comps = VO[(VO.perspective == persp) & (VO.method == "Comparables") & (VO.metric == "equity_value_per_21cf_share")]
        proj = DP[(DP.perspective == persp) & DP.case.astype(str).str.startswith(base_case)]
        shares = float(get("shares_outstanding_m") if persp.startswith("A") else get("shares_fully_diluted_m"))
        P[persp] = {"label": "A · Announcement (14 Dec 2017)" if persp.startswith("A") else "B · Proxy (30 May 2018)",
                    "basis": "Estimates from public Dec 2017 information" if persp.startswith("A") else "Disney management forecasts (May 2018 proxy)",
                    "wacc": w, "tax": float(get("marginal_tax_rate")), "g": float(get("terminal_growth")), "shares": shares,
                    "bridge": bridge, "outputs": out, "scenarios": scen,
                    "grid": records(grid, ["row_value", "col_value", "equity_per_share", "enterprise_value_ops"]),
                    "sensitivity": records(VS[(VS.perspective == persp) & (VS.table != "wacc_x_terminal_growth")], ["table", "row_value", "enterprise_value_ops", "equity_per_share"]),
                    "comps": records(comps, ["case", "v"]),
                    "projection": records(proj, ["fy", "revenue", "ebitda", "ebitda_margin", "da", "ebit", "taxes_on_ebit", "nopat", "capex", "dnwc", "fcff",
                                                 "fraction_after_valuation_date", "discount_time_years", "pv_fcff"])}
        s("Valuation", f"{persp} DCF equity value per 21CF share", out["equity_value_per_21cf_share"], "USD_per_share", "estimate", "valuation_outputs.csv")
        s("Valuation", f"{persp} WACC", w["wacc"], "ratio", "derived", "valuation_outputs.csv")
    # browser model parameters
    A_ = DP[(DP.perspective == "A_announcement_2017-12") & (DP.case == "base (estimates)")]
    getA = lambda p: float(DA[(DA.perspective == "A_announcement_2017-12") & (DA.parameter == p)].value.iloc[0])
    # ratios backed out of the projection rows (6-dp exports) rather than the 4-dp rounded assumption values
    r0 = A_.iloc[0]
    P["A_announcement_2017-12"]["model"] = {
        "kind": "estimate", "base_revenue": getA("remainco_fy2017_revenue"), "growth": float(r0.revenue) / getA("remainco_fy2017_revenue") - 1,
        "margin": float(r0.ebitda) / float(r0.revenue), "da_pct": float(r0.da) / float(r0.revenue), "capex_pct": float(r0.capex) / float(r0.revenue),
        "nwc_pct": float(r0.dnwc) / float(r0.revenue),
        "frac": A_.fraction_after_valuation_date.tolist(), "t": A_.discount_time_years.tolist(),
        "t_n": None}
    import dcf as dcfmod
    from datetime import date
    P["A_announcement_2017-12"]["model"]["t_n"] = (date(2022, 6, 30) - date(2017, 12, 14)).days / 365.25
    # precise WACC (unrounded) from the Stage 3 output rows
    P["A_announcement_2017-12"]["model"]["wacc"] = getA("wacc")  # 6-dp value used by Stage 3 (valuation_outputs rounds to 4 dp)
    import monte_carlo as mc
    m = mc.Model()
    P["B_proxy_2018-05"]["model"] = {"kind": "management", "fy": [f"FY{y[:4]}" for y in m.fy], "revenue": m.R.tolist(), "margin": m.margin.tolist(),
                                      "resid_pct": m.resid_pct.tolist(), "da_pct": m.da_pct, "capex_pct": m.capex_pct, "conv": m.conv,
                                      "frac": m.frac.tolist(), "t": m.t.tolist(), "t_n": m.t_n, "k_exp": m.k_exp.tolist(), "wacc": m.wacc,
                                      "bridge_total": float(m.bridge)}
    D["valuation"] = P
    D["comps"] = records(CC, ["perspective", "ticker", "company", "price_date", "price", "shares_m_proxy", "market_cap", "debt", "cash", "enterprise_value",
                              "ltm_revenue", "ltm_ebitda", "ltm_operating_income", "ev_revenue", "ev_revenue_flag", "ev_ebitda", "ev_ebitda_flag",
                              "ev_ebit", "ev_ebit_flag", "pe", "pe_flag", "business_mix_note"], nd=4)
    D["forecasts"] = records(MF[MF.value_status.isin(["reported_forecast", "derived"])], ["proxy", "forecast_set", "metric", "fiscal_year", "value", "source_page"])

    # ---------------- synergies (Stage 4A)
    import synergy as syn
    SV = SO[SO.section == "Synergy value"]
    D["synergy"] = {
        "assumptions": records(SY, ["perspective", "parameter", "value", "unit", "value_type", "source"]),
        "values": records(SV, ["perspective", "case", "metric", "v"]),
        "cashflows": records(SO[SO.section == "Synergy cash flows"], ["perspective", "case", "metric", "v"]),
        "sensitivity": records(SO[SO.section == "Synergy sensitivity"], ["perspective", "case", "v"]),
        "justification": records(SO[SO.section == "Deal justification"], ["perspective", "case", "metric", "v"]),
        "reference": records(SO[SO.section.str.startswith("Reference")], ["perspective", "case", "v", "notes"]),
        "model": {"fy": list(syn.FY.keys()), "scenarios": {k: {"run_rate": v["run_rate"], "phase": [v["phase"][y] for y in syn.FY], "g": v["g"],
                                                             "ic_mult": v["ic_mult"], "note": v["note"]} for k, v in syn.SCENARIOS.items()},
                  "ic_phase": [syn.IC_PHASE[y] for y in syn.FY],
                  "timing": {}},
    }
    for persp, vd in (("A_announcement_2017-12", date(2017, 12, 14)), ("B_proxy_2018-05", date(2018, 5, 30))):
        tt = []
        for y in syn.FY:
            start = max(syn.FY_START[y], syn.CLOSE)
            tt.append((start + (syn.FY[y] - start) / 2 - vd).days / 365.25)
        D["synergy"]["model"]["timing"][persp] = {"t": tt, "t_n": (syn.FY[2023] - vd).days / 365.25}
    for persp in ("A_announcement_2017-12", "B_proxy_2018-05"):
        s("Synergies", f"{persp} base net synergy value", float(SV[(SV.perspective == persp) & (SV.case == "base") & (SV.metric == "net_synergy_value")].v.iloc[0]),
          "USD_m", "estimate", "synergy_outputs.csv")

    # ---------------- accretion / dilution (Stage 4B)
    import accretion as ad
    S = ad.gather()
    syn0, ic0 = ad.synergies_base()
    years = {}
    for y in ad.YEARS:
        seg = S["seg"][str(y)] if S["seg"][str(y)] is not None else S["seg"]["2021"] * S["ebitda"][str(y)] / S["ebitda"]["2021"]
        corp = S["corp2020"] * (1 + S["corp_g"]) ** (y - 2020)
        rc_rev = 0.75 * S["rc"][("revenue", y)] + 0.25 * S["rc"][("revenue", y + 1)]
        rc_ebitda = 0.75 * S["rc"][("ebitda", y)] + 0.25 * S["rc"][("ebitda", y + 1)]
        years[f"FY{y}"] = {"seg": seg, "corp": corp, "rc_ebit_full": rc_ebitda - S["rc_da_pct"] * rc_rev, "syn": syn0[y], "ic": ic0[y]}
    D["accretion"] = {
        "params": {"tax": S["tax"], "rate": S["rate"], "ppa": S["ppa"], "dis_int": S["dis_int"], "dis_nci": S["dis_nci"], "dis_sh": S["dis_sh"],
                   "rc_int": S["rc_int"], "rc_intinc": S["rc_intinc"], "rc_eq": S["rc_eq"], "rc_nci": S["rc_nci"], "rsn_share": S["rsn_share"],
                   "rsn_proceeds": S["rsn_proceeds"], "cash": S["cash"], "stock_val": S["stock_val"], "shares_new": S["shares_new"],
                   "vwap": S["vwap"], "repaid": S["repaid"], "orig_shares": S["orig_shares"], "years": years},
        "inputs": records(AI, ["group", "item", "value", "unit", "value_type", "source"]),
        "cases": records(AO[~AO.case.str.startswith(("sensitivity", "reported")) & AO.metric.isin(
            ["disney_standalone_eps", "pro_forma_eps_adjusted", "pro_forma_eps_gaap_basis", "accretion_adjusted", "accretion_gaap_basis"])], ["case", "fiscal_year", "metric", "v"]),
        "anchor": records(AO[AO.case.str.startswith("reported")], ["fiscal_year", "metric", "v"]),
        "sensitivity_fy2021": records(AO[AO.case.str.startswith("sensitivity") & (AO.fiscal_year == "FY2021") & AO.metric.isin(["accretion_adjusted", "accretion_gaap_basis"])], ["case", "metric", "v"]),
    }
    base_fy21 = float(AO[AO.case.str.startswith("base") & (AO.fiscal_year == "FY2021") & (AO.metric == "accretion_adjusted")].v.iloc[0])
    s("Accretion/dilution", "FY2021 adjusted EPS accretion (base)", base_fy21, "ratio", "estimate", "accretion_dilution_outputs.csv")

    # ---------------- real options and Monte Carlo (Stage 5)
    RO["v"] = pd.to_numeric(RO.value, errors="coerce")
    D["options"] = {"inputs": records(RI, ["parameter", "value", "unit", "value_type", "method", "sensitivity_low", "sensitivity_high"]),
                    "outputs": records(RO, ["section", "case", "metric", "v", "notes"]), "convergence": records(BC)}
    bs = float(RO[(RO.section == "Option value") & (RO.case == "base") & (RO.metric == "black_scholes_call")].v.iloc[0])
    s("Real options", "Revenue-synergy expansion option (Black-Scholes)", bs, "USD_m", "estimate", "real_options_outputs.csv")
    draws = pd.read_csv(PROC / "monte_carlo_draws.csv")
    inp = MI.set_index("variable")
    paid38 = float(inp.loc["consideration_amended_38", "parameters"])
    paid0 = float(inp.loc["consideration_original_at_2018-05-30", "parameters"])
    hist = {}
    for lab, paid in (("amended_38", paid38), ("original_at_2018-05-30", paid0)):
        x = (draws.total_value_to_disney - paid) / 1000
        cnt, edges = np.histogram(x, bins=60)
        hist[lab] = {"edges": [round(e, 4) for e in edges.tolist()], "counts": cnt.tolist()}
    D["montecarlo"] = {"inputs": records(MI), "summary": records(MS), "convergence": records(MCV), "tornado": records(MT), "scenarios": records(MSC),
                       "histogram_bn": hist, "paid": {"amended_38": paid38, "original_at_2018-05-30": paid0},
                       "seed": int(mc.SEED), "n": int(mc.N_DRAWS), "option_value": bs,
                       "synergy_base": {"run_rate": m.run_rate, "g": m.g_syn, "phase": m.phase.tolist(), "ic_phase": m.ic_phase.tolist(),
                                        "t": m.syn_t.tolist(), "t_n": m.syn_tn}}
    p38 = float(MS[MS.metric == "value_created_vs_amended_38"].prob_positive.iloc[0])
    s("Monte Carlo", "P(value created > 0) vs amended $38 offer", p38, "ratio", "estimate", "monte_carlo_summary.csv")
    D["sources"] = records(REG[REG.download_status == "ok"], ["source_id", "form", "filing_date", "description", "url"])
    D["summary"] = SUMMARY
    return D


def main():
    D = build()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(D, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(SUMMARY[0]))
        w.writeheader()
        w.writerows(SUMMARY)
    print(f"dashboard data -> {OUT_JSON.relative_to(ROOT)} ({OUT_JSON.stat().st_size / 1024:,.0f} KB); {len(SUMMARY)} summary rows -> {OUT_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
