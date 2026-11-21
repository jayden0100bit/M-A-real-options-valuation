"""Stage 4A: synergy valuation and deal justification, on top of the Stage 3 standalone valuation.

Outputs: data/processed/synergy_assumptions.csv, data/processed/synergy_outputs.csv; checks (synergy_*) appended
to data/processed/verification_checks.csv by build_stage4.py.

Disclosed management guidance (quoted, page-referenced) vs our estimates (labelled ``estimate``):
  * run-rate cost synergies ~$2.0bn, "fully realize ... by 2021" (Disney fiscal 2021), starting in year 1;
  * accretive to EPS before purchase accounting in the second fiscal year after close;
  * revenue synergies: not quantified publicly; Disney's internal estimates exist, but only the advisors' implied
    per-share values are disclosed (used here as a reference only, never as an input);
  * integration costs: not disclosed at either valuation date. The ~$1.5bn severance estimate (May 2019) is
    subsequent information and appears only in a hindsight case.

Valuation per perspective (A: 14 Dec 2017; B: 30 May 2018), using that perspective's WACC and tax rate from
Stage 3 (dcf_assumptions.csv). Synergy cash flows are dated by Disney fiscal year (ending about 30 Sep).
  after-tax synergy FCFF_t = (cost synergies_t - integration costs_t) x (1 - tax)
No capex or working capital is attached to cost synergies (assumption). The terminal value is Gordon growth on
the FY2023 after-tax run-rate synergy, at a synergy growth rate below the standalone terminal growth.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from build_transaction import find_quote  # noqa: E402

PROC = ROOT / "data" / "processed"
FY = {2019: date(2019, 9, 28), 2020: date(2020, 10, 3), 2021: date(2021, 10, 2), 2022: date(2022, 10, 1), 2023: date(2023, 9, 30)}
FY_START = {2019: date(2018, 9, 30), 2020: date(2019, 9, 29), 2021: date(2020, 10, 4), 2022: date(2021, 10, 3), 2023: date(2022, 10, 2)}
CLOSE = date(2019, 3, 15)  # estimate: midpoint of "12-18 months" after 13 Dec 2017

PERSP = {
    "A_announcement_2017-12": {"valuation_date": date(2017, 12, 14), "cutoff": "2017-12-15"},
    "B_proxy_2018-05": {"valuation_date": date(2018, 5, 30), "cutoff": "2018-05-30"},
}
SCENARIOS = {
    # run-rate (USD m), phase-in share of run-rate by Disney FY, post-run-rate growth, integration cost multiple of run-rate
    "bear": {"run_rate": 1500.0, "phase": {2019: 0.0, 2020: 0.25, 2021: 0.50, 2022: 1.0, 2023: 1.0}, "g": 0.0, "ic_mult": 1.5,
             "note": "75% of guidance, one year late; integration costs 1.5x run-rate (overrun)"},
    "base": {"run_rate": 2000.0, "phase": {2019: 0.10, 2020: 0.50, 2021: 1.0, 2022: 1.0, 2023: 1.0}, "g": 0.01, "ic_mult": 1.0,
             "note": "management guidance: ~$2.0bn run-rate, savings start in year 1, fully realized by fiscal 2021"},
    "bull": {"run_rate": 2500.0, "phase": {2019: 0.25, 2020: 0.75, 2021: 1.0, 2022: 1.0, 2023: 1.0}, "g": 0.02, "ic_mult": 0.75,
             "note": "'at least $2 billion' exceeded by 25%, faster ramp; integration costs 0.75x run-rate"},
}
SCEN_WEIGHTS = {"bear": 0.25, "base": 0.50, "bull": 0.25}  # estimate: probability of realization scenarios
IC_PHASE = {2019: 0.5, 2020: 0.4, 2021: 0.1, 2022: 0.0, 2023: 0.0}  # estimate: integration spend front-loaded

ASSUME, OUT, CHECKS = [], [], []


def a(persp, category, parameter, value, unit, value_type, source, available_date, method, low="", high=""):
    ASSUME.append({"perspective": persp, "category": category, "parameter": parameter, "value": value, "unit": unit,
                   "value_type": value_type, "source": source, "available_date": available_date, "method": method,
                   "sensitivity_low": low, "sensitivity_high": high})
    cut = PERSP.get(persp, {}).get("cutoff", "9999-12-31")
    CHECKS.append({"check_type": "synergy_lookahead", "entity": "Disney+RemainCo", "source_id": str(source)[:80], "fiscal_period": persp,
                   "item": parameter, "expected": f"available <= {cut}", "observed": available_date,
                   "status": "pass" if (not available_date or available_date <= cut) else "fail", "detail": category})
    return value


def o(persp, section, case, metric, value, unit, value_type, notes=""):
    OUT.append({"perspective": persp, "section": section, "case": case, "metric": metric,
                "value": round(value, 6) if isinstance(value, float) else value, "unit": unit, "value_type": value_type, "notes": notes})


def chk(ctype, item, expected, observed, tol, persp=""):
    CHECKS.append({"check_type": ctype, "entity": "Disney+RemainCo", "source_id": "", "fiscal_period": persp, "item": item,
                   "expected": round(float(expected), 6), "observed": round(float(observed), 6),
                   "status": "pass" if abs(float(expected) - float(observed)) <= tol else "fail", "detail": ""})


def q(doc, text):
    found, page = find_quote(doc, text)
    if not found:
        raise AssertionError(f"quote not found: {doc}: {text[:70]}")
    CHECKS.append({"check_type": "synergy_input_quote", "entity": "", "source_id": doc, "fiscal_period": "", "item": text[:120],
                   "expected": "found", "observed": f"page {page or 'unnumbered'}", "status": "pass", "detail": ""})
    return f"{doc} p.{page or 'unnumbered'}"


def guidance():
    """Management disclosures, recorded once per perspective in which they were available."""
    g = {}
    g["release"] = q("DIS_8K_20171214_EX99_1", "The acquisition is expected to yield at least $2 billion in cost savings from efficiencies realized through the combination of businesses, and to be accretive to earnings before the impact of purchase accounting for the second fiscal year after the close of the transaction.")
    g["call_runrate"] = q("DIS_425_20171215_CALL", "8.3x including $2.0 billion in anticipated run-rate cost synergies")
    g["call_timing"] = q("DIS_425_20171215_CALL", "we expect to fully realize roughly $2.0 billion of cost synergies by 2021")
    g["call_year1"] = q("DIS_425_20171215_CALL", "we would start realizing savings in the first year, but as I said, we would fully realize the benefits by 2021")
    g["call_close"] = q("DIS_425_20171215_CALL", "We expect our acquisition of 21st Century Fox to close within 12-18")
    g["meeting_sources"] = q("DIS_425_20171215_MEETING", "when you take the two organizations and you look at the overlap and the redundancies")
    g["call_accretion"] = q("DIS_425_20171215_CALL", "The accretion math is, as I mentioned, this does not include purchase accounting adjustments, but it does include the benefit of share repurchase")
    g["proxy_board"] = q("JPROXY_ORIG_20180530", "the Disney board's expectation that the transactions will yield approximately $2 billion in cost savings from efficiencies realized through the combination of the businesses by 2021")
    g["proxy_close"] = q("JPROXY_ORIG_20180530", "it is anticipated that the transactions will be completed within 12-18 months after December 13, 2017")
    g["proxy_separate"] = q("JPROXY_ORIG_20180530", "based on Disney forecasts for RemainCo, the Disney forecasts for Sky and the synergy estimates prepared by Disney management")
    g["proxy_tax"] = q("JPROXY_ORIG_20180530", "the synergy estimates, any other estimates and any other forward-looking information reflected the then-current US federal corporate income tax regime")
    g["hind_sev"] = q("DIS_10Q_Q2FY2019", "The Company estimates it will incur severance and severance-related costs on the order of $1.5 billion")
    g["hind_complete"] = q("DIS_10Q_Q2FY2019", "We expect to complete the restructuring and integration plan by the end of Fiscal Year 2021")
    g["hind_10k"] = q("DIS_10K_FY2019", "we anticipate that the total severance and related costs could be on the order of $1.5 billion")
    return g


def advisors_reference(g):
    """Advisor-implied synergy values per RemainCo share (midpoints of disclosed ranges). Reference only."""
    rows = [("A_announcement_2017-12", None),  # not public at A
            ("B_proxy_2018-05", ("JPROXY_ORIG_20180530", "p.145", (17.75, 24.00), (27.50, 36.25), (35.75, 47.25), "6.75%-7.75%", "0.75%-1.25%")),
            ("subsequent_info_2018-06", ("JPROXY_AMENDED_20180628", "p.192", (22.50, 29.25), (34.50, 44.25), (44.00, 56.25), "7.25%-8.25%", "0.75%-1.25%"))]
    q("JPROXY_ORIG_20180530", "Stand-Alone + Cost Synergies | 27.50 | 36.25 | 28.25 | 40.25")
    q("JPROXY_AMENDED_20180628", "Stand-Alone + Cost Synergies | 34.50 | 44.25")
    for persp, r in rows:
        if r is None:
            continue
        doc, pg, sa, cs, crs, dr, gr = r
        mid = lambda x: (x[0] + x[1]) / 2
        o(persp, "Reference: Disney advisors (not an input)", "cost synergies", "implied_value_per_remainco_share", mid(cs) - mid(sa), "USD_per_share",
          "derived", f"{doc} {pg}: midpoint 'Stand-Alone + Cost Synergies' {cs} minus midpoint 'Stand-Alone' {sa}; discount {dr}, growth {gr}; "
          "Sky acquisition does not close; pre-TCJA tax regime for the May proxy")
        o(persp, "Reference: Disney advisors (not an input)", "revenue synergies", "implied_value_per_remainco_share", mid(crs) - mid(cs), "USD_per_share",
          "derived", f"{doc} {pg}: midpoint '+ Cost and Revenue Synergies' {crs} minus midpoint '+ Cost Synergies' {cs}. Revenue synergy "
          "amounts are not disclosed, so they are not modelled; shown for reference.")


def run_scenario(sc, wacc, tax, vd, run_rate=None, phase=None, g=None, ic_mult=None, rate_add=0.0, realization=1.0):
    run_rate = sc["run_rate"] if run_rate is None else run_rate
    phase = sc["phase"] if phase is None else phase
    g = sc["g"] if g is None else g
    ic_mult = sc["ic_mult"] if ic_mult is None else ic_mult
    r = wacc + rate_add
    rows, pv_syn, pv_ic = [], 0.0, 0.0
    for fy, end in FY.items():
        start = max(FY_START[fy], CLOSE)
        syn = run_rate * phase[fy] * realization
        ic = run_rate * ic_mult * IC_PHASE[fy]
        mid = start + (end - start) / 2
        t = (mid - vd).days / 365.25
        df = (1 + r) ** -t
        syn_at, ic_at = syn * (1 - tax), ic * (1 - tax)
        pv_syn += syn_at * df
        pv_ic += ic_at * df
        rows.append({"fiscal_year": f"FY{fy}", "pretax_cost_synergies": syn, "tax_on_synergies": syn * tax, "aftertax_synergies": syn_at,
                     "pretax_integration_costs": ic, "tax_shield_integration": ic * tax, "aftertax_integration_costs": ic_at,
                     "aftertax_synergy_fcff": syn_at - ic_at, "discount_time_years": t, "discount_factor": df,
                     "pv_aftertax_synergies": syn_at * df, "pv_aftertax_integration": ic_at * df})
    t_n = (FY[2023] - vd).days / 365.25
    last = rows[-1]["aftertax_synergies"]
    tv = last * (1 + g) / (r - g)
    pv_tv = tv * (1 + r) ** -t_n
    gross = pv_syn + pv_tv
    return {"rows": rows, "pv_explicit_synergies": pv_syn, "terminal_value": tv, "pv_terminal": pv_tv, "gross_synergy_value": gross,
            "pv_integration_costs": pv_ic, "net_synergy_value": gross - pv_ic, "rate": r, "g": g, "t_n": t_n, "last": last}


def build():
    g = guidance()
    A3 = pd.read_csv(PROC / "dcf_assumptions.csv")
    O3 = pd.read_csv(PROC / "valuation_outputs.csv")
    O3["v"] = pd.to_numeric(O3.value, errors="coerce")
    P3 = pd.read_csv(PROC / "dcf_projections.csv")
    advisors_reference(g)
    results = {}
    for persp, meta in PERSP.items():
        vd = meta["valuation_date"]
        get = lambda p: float(A3[(A3.perspective == persp) & (A3.parameter == p)].value.iloc[0])
        wacc, tax = get("wacc"), get("marginal_tax_rate")
        shares = get("shares_outstanding_m") if persp.startswith("A") else get("shares_fully_diluted_m")
        avail = "2017-12-15" if persp.startswith("A") else "2018-05-30"
        src_g = g["call_runrate"] + "; " + g["call_timing"] + ("" if persp.startswith("A") else "; " + g["proxy_board"])
        a(persp, "guidance", "run_rate_cost_synergies", 2000.0, "USD_m", "management_guidance", src_g, "2017-12-15",
          "Run-rate pre-tax cost synergies ('at least $2 billion' in the release; '$2.0 billion ... run-rate' on the call)")
        a(persp, "guidance", "full_realization_year", "FY2021", "Disney fiscal year", "management_guidance", g["call_timing"] + "; " + g["call_year1"],
          "2017-12-15", "Savings start in the first year after close; fully realized by (fiscal) 2021")
        a(persp, "guidance", "revenue_synergies", "", "USD_m", "not_disclosed", g["proxy_separate"] if persp.startswith("B") else g["release"],
          avail, "Not quantified publicly; excluded from all scenarios (only advisor-implied values exist; reference rows)")
        a(persp, "estimate", "expected_close", CLOSE.isoformat(), "date", "estimate", g["call_close"] if persp.startswith("A") else g["proxy_close"],
          "2017-12-15", "Midpoint of '12-18 months' after signing (actual close: 20 Mar 2019)")
        a(persp, "estimate", "phase_in_base", "FY2019 10% (post-close), FY2020 50%, FY2021+ 100%", "share of run-rate", "estimate",
          g["call_year1"], "2017-12-15", "Consistent with 'start realizing savings in the first year' and 'fully realize ... by 2021'")
        a(persp, "estimate", "integration_cost_multiple_base", 1.0, "x run-rate", "estimate", "judgement (no disclosure at this date)", "",
          "One-time pre-tax costs equal to 1.0x run-rate synergies ($2.0bn), spent 50/40/10% in FY2019/20/21. Hindsight: Disney "
          "later estimated ~$1.5bn of severance (0.75x)", 0.75, 1.5)
        a(persp, "estimate", "synergy_terminal_growth", 0.01, "ratio", "estimate", "judgement",
          "", "Below the 2.0% standalone terminal growth (cost savings tend to erode); advisors used 0.75%-1.25%, Centerview 0.5%", 0.0, 0.02)
        a(persp, "estimate", "discount_rate", round(wacc, 6), "ratio", "derived", "dcf_assumptions.csv (Stage 3 WACC)", avail,
          "Standalone RemainCo WACC: cost synergies are mostly overhead removal, controllable by Disney, with execution risk "
          "comparable to the operating cash flows; Disney's advisors used the same rate for RemainCo and synergies. +1pp/+2pp sensitivities.",
          round(wacc, 6), round(wacc + 0.02, 6))
        a(persp, "estimate", "tax_rate", tax, "ratio", "estimate", "dcf_assumptions.csv (Stage 3)", avail,
          "Same marginal rate as the standalone valuation; integration costs are assumed tax-deductible at that rate")
        a(persp, "estimate", "scenario_weights", "bear 25% / base 50% / bull 25%", "probability", "estimate", "judgement", "",
          "Probability of realization scenarios for the risk-weighted value")
        standalone = float(O3[(O3.perspective == persp) & (O3.method == "DCF") & O3.case.str.startswith("base") &
                              (O3.metric == "equity_value")].v.iloc[0])
        sa_ps = standalone / shares
        res = {}
        for name, sc in SCENARIOS.items():
            r = run_scenario(sc, wacc, tax, vd)
            res[name] = r
            for row in r["rows"]:
                chk("synergy_cashflow", f"{name} {row['fiscal_year']}: after-tax FCFF = (synergy - integration) x (1 - t)",
                    (row["pretax_cost_synergies"] - row["pretax_integration_costs"]) * (1 - tax), row["aftertax_synergy_fcff"], 1e-6, persp)
                chk("synergy_tax", f"{name} {row['fiscal_year']}: tax on synergies = t x pre-tax", tax * row["pretax_cost_synergies"],
                    row["tax_on_synergies"], 1e-6, persp)
                chk("synergy_integration", f"{name} {row['fiscal_year']}: integration cost after tax = cost x (1 - t)",
                    row["pretax_integration_costs"] * (1 - tax), row["aftertax_integration_costs"], 1e-6, persp)
                OUT.append({"perspective": persp, "section": "Synergy cash flows", "case": name, "metric": row["fiscal_year"],
                            "value": round(row["aftertax_synergy_fcff"], 3), "unit": "USD_m", "value_type": "estimate",
                            "notes": "; ".join(f"{k}={v:,.3f}" for k, v in row.items() if k != "fiscal_year")})
            chk("synergy_terminal", f"{name}: TV = last after-tax synergy x (1+g)/(r-g)", r["last"] * (1 + r["g"]) / (r["rate"] - r["g"]),
                r["terminal_value"], 1e-6, persp)
            chk("synergy_terminal", f"{name}: gross value = PV explicit + PV TV", r["pv_explicit_synergies"] + r["pv_terminal"],
                r["gross_synergy_value"], 1e-6, persp)
            chk("synergy_integration", f"{name}: net = gross - PV integration costs", r["gross_synergy_value"] - r["pv_integration_costs"],
                r["net_synergy_value"], 1e-6, persp)
            CHECKS.append({"check_type": "synergy_terminal", "entity": "", "source_id": "", "fiscal_period": persp,
                           "item": f"{name}: discount rate exceeds synergy growth", "expected": ">0",
                           "observed": round(r["rate"] - r["g"], 6), "status": "pass" if r["rate"] > r["g"] else "fail", "detail": ""})
            for metric, val in (("pv_explicit_aftertax_synergies", r["pv_explicit_synergies"]), ("pv_terminal_value", r["pv_terminal"]),
                                ("gross_synergy_value", r["gross_synergy_value"]), ("pv_integration_costs", r["pv_integration_costs"]),
                                ("net_synergy_value", r["net_synergy_value"])):
                o(persp, "Synergy value", name, metric, val, "USD_m", "estimate", sc["note"])
            o(persp, "Synergy value", name, "net_synergy_value_per_21cf_share", r["net_synergy_value"] / shares, "USD_per_share", "estimate")
            o(persp, "Synergy value", name, "standalone_plus_net_synergies_equity", standalone + r["net_synergy_value"], "USD_m", "estimate",
              "Stage 3 base standalone equity value + net synergy value = total value to Disney (before price paid)")
            o(persp, "Synergy value", name, "standalone_plus_net_synergies_per_share", sa_ps + r["net_synergy_value"] / shares, "USD_per_share", "estimate")
        pw = sum(SCEN_WEIGHTS[k] * res[k]["net_synergy_value"] for k in res)
        o(persp, "Synergy value", "probability-weighted", "net_synergy_value", pw, "USD_m", "estimate",
          "bear 25% / base 50% / bull 25% (realization probability estimate)")
        o(persp, "Synergy value", "probability-weighted", "net_synergy_value_per_21cf_share", pw / shares, "USD_per_share", "estimate")
        # incremental margin on the acquired business (base run-rate vs forecast revenue)
        if persp.startswith("B"):
            rev = P3[(P3.perspective == persp) & P3.case.str.startswith("base") & (P3.fy == "FY2021")].revenue.iloc[0]
            o(persp, "Synergy value", "base", "run_rate_synergies_pct_of_remainco_fy2021_revenue", 2000.0 / rev, "ratio", "derived",
              f"$2.0bn / Disney forecast RemainCo FY2021 revenue {rev:,.0f}: EBITDA margin uplift on the acquired business if all savings "
              "are attributed to it")
        # sensitivities (base): discount rate premium, realization %, integration overrun, growth
        for add in (0.0, 0.01, 0.02):
            r = run_scenario(SCENARIOS["base"], wacc, tax, vd, rate_add=add)
            o(persp, "Synergy sensitivity", f"discount rate +{add:.0%}", "net_synergy_value", r["net_synergy_value"], "USD_m", "estimate")
        prev = None
        for real in (0.0, 0.5, 0.75, 1.0, 1.25):
            r = run_scenario(SCENARIOS["base"], wacc, tax, vd, realization=real)
            o(persp, "Synergy sensitivity", f"realization {real:.0%}", "net_synergy_value", r["net_synergy_value"], "USD_m", "estimate")
            if prev is not None:
                CHECKS.append({"check_type": "synergy_sensitivity", "entity": "", "source_id": "", "fiscal_period": persp,
                               "item": f"net value increases with realization ({real:.0%})", "expected": "increasing",
                               "observed": round(r["net_synergy_value"] - prev, 3), "status": "pass" if r["net_synergy_value"] > prev else "fail", "detail": ""})
            prev = r["net_synergy_value"]
        for m in (0.75, 1.0, 1.5, 2.0):
            r = run_scenario(SCENARIOS["base"], wacc, tax, vd, ic_mult=m)
            o(persp, "Synergy sensitivity", f"integration cost {m:.2f}x run-rate", "net_synergy_value", r["net_synergy_value"], "USD_m", "estimate")
        for gg in (0.0, 0.005, 0.01, 0.015, 0.02):
            r = run_scenario(SCENARIOS["base"], wacc, tax, vd, g=gg)
            o(persp, "Synergy sensitivity", f"synergy growth {gg:.1%}", "net_synergy_value", r["net_synergy_value"], "USD_m", "estimate")
        # hindsight integration cost (subsequent information, shown separately)
        hind = run_scenario(SCENARIOS["base"], wacc, tax, vd, ic_mult=0.75)
        o("hindsight", "Synergy value", f"{persp} base with ~$1.5bn severance (May 2019 estimate)", "net_synergy_value",
          hind["net_synergy_value"], "USD_m", "estimate", f"{g['hind_sev']}; {g['hind_10k']}. Subsequent information; not used in A or B.")
        results[persp] = {"res": res, "pw": pw, "shares": shares, "standalone": standalone, "sa_ps": sa_ps, "wacc": wacc, "tax": tax}
    deal_justification(results)
    return results


def deal_justification(results):
    T = pd.read_csv(PROC / "valuation_outputs.csv")
    T["v"] = pd.to_numeric(T.value, errors="coerce")
    tv = lambda m: float(T[(T.perspective == "transaction") & (T.metric == m)].v.iloc[0])
    import market_data as md
    dis_b, dis_b_d = md.price_asof("DIS", "2018-05-30")
    consid = {
        "A_announcement_2017-12": [("original offer at 13 Dec 2017 Disney close", tv("per_share_value_at_2017-12-13_close"), "transaction (0.2745 x $107.61)")],
        "B_proxy_2018-05": [("original offer at 30 May 2018 Disney close", 0.2745 * dis_b, f"0.2745 x Disney close {dis_b:.2f} on {dis_b_d} (Yahoo)"),
                            ("amended offer $38 (20 Jun 2018; subsequent)", 38.0, "transaction_assumptions A02")],
    }
    for persp, R in results.items():
        for lab, cps, src in consid[persp]:
            prem_ps = cps - R["sa_ps"]
            prem = prem_ps * R["shares"]
            base_net = R["res"]["base"]["net_synergy_value"]
            o(persp, "Deal justification", lab, "consideration_per_share", cps, "USD_per_share", "derived", src)
            o(persp, "Deal justification", lab, "standalone_value_per_share", R["sa_ps"], "USD_per_share", "estimate", "Stage 3 base DCF")
            o(persp, "Deal justification", lab, "premium_over_standalone_per_share", prem_ps, "USD_per_share", "derived",
              "consideration - standalone intrinsic value (both per 21CF share, acquired business only)")
            o(persp, "Deal justification", lab, "premium_over_standalone_total", prem, "USD_m", "derived")
            chk("synergy_premium_reconciliation", f"{lab}: premium = consideration - standalone", cps - R["sa_ps"], prem_ps, 1e-9, persp)
            for name in ("bear", "base", "bull"):
                net = R["res"][name]["net_synergy_value"]
                cov = (net / prem) if prem > 0 else None
                o(persp, "Deal justification", lab, f"synergy_coverage_of_premium_{name}", cov if cov is not None else "",
                  "ratio", "estimate" if cov is not None else "not_applicable",
                  "net synergy value / premium over standalone" if cov is not None else "no premium over standalone value: synergies not needed")
                o(persp, "Deal justification", lab, f"value_created_for_disney_{name}", R["standalone"] + net - cps * R["shares"], "USD_m", "estimate",
                  "standalone equity + net synergies - consideration (positive = acquirer keeps value; negative = premium exceeds synergies)")
            pw = R["pw"]
            o(persp, "Deal justification", lab, "synergy_coverage_of_premium_probability_weighted", (pw / prem) if prem > 0 else "", "ratio",
              "estimate" if prem > 0 else "not_applicable")
            o(persp, "Deal justification", lab, "max_justified_price_per_share_base",
              R["sa_ps"] + base_net / R["shares"], "USD_per_share", "estimate", "standalone + 100% of base net synergies (walk-away price)")
            chk("synergy_premium_reconciliation", f"{lab}: value created (base) = standalone + net synergies - consideration",
                R["standalone"] + base_net - cps * R["shares"],
                (R["sa_ps"] + base_net / R["shares"] - cps) * R["shares"], 1e-3, persp)


def write():
    def w(path, rows):
        import csv
        with path.open("w", newline="", encoding="utf-8") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
    w(PROC / "synergy_assumptions.csv", ASSUME)
    w(PROC / "synergy_outputs.csv", OUT)
