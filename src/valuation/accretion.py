"""Stage 4B: accretion / dilution of Disney EPS from the 21CF acquisition.

Outputs: data/processed/accretion_dilution_inputs.csv, data/processed/accretion_dilution_outputs.csv; checks (accretion_*).

Structure (Disney fiscal years ending ~30 Sep; FY2020-FY2022 = the first three full fiscal years after the 20 Mar 2019 close):

  Disney standalone NI  = (Total segment operating income - corporate & unallocated - net interest) x (1 - t) - NCI
                          segment OI and corporate expense from the "Disney street forecasts/estimates" in the May 2018 proxy
                          (pp.152-153); net interest and NCI held at FY2018 actuals (estimate)
  RemainCo NI           = (EBITDA - D&A - net interest + equity income) x (1 - t) - NCI
                          EBITDA from Disney's forecasts for RemainCo (June FY, calendarised to Disney's FY as 0.75 x FY(t) +
                          0.25 x FY(t+1)); D&A at 2.01% of revenue (Stage 3 estimate); net interest, equity income and NCI held at
                          the FY2018 closing-perimeter pro forma (8-K/A Ex. 99.4), which already excludes Sky
  Financing             = interest on incremental acquisition debt (cash consideration 35.7bn less 16.1bn repaid from acquired cash)
                          at 3.3% (rate assumed in Disney's 8-K/A pro forma); 306.8m new shares (closing)
  Purchase accounting   = incremental amortization of film/TV costs and intangibles, ex-RSN: 2.7bn a year (FY2019 10-K pro forma)
  Synergies / integration = Stage 4A base case
  Adjusted EPS          = excludes purchase-accounting amortization and integration costs (management's "before purchase accounting")
  GAAP-basis EPS        = includes both

Base perimeter: RSNs EXCLUDED (sold Aug 2019, before FY2020). RSN operating profit is removed in proportion to RSN revenue share
(20.8%, FY2018); the ~$11bn proceeds repay acquisition debt. Both are estimates, and the tax on the sale is not modelled.
A variant keeps the RSNs. Disney's FY2018 pro forma EPS from the 8-K/A (GAAP, incl. purchase accounting, no synergies) is
reported as an anchor.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from build_transaction import find_quote  # noqa: E402
from forecasts import parse_forecast_row  # noqa: E402
from sec_tables import load_tables  # noqa: E402

PROC = ROOT / "data" / "processed"
INPUTS, OUT, CHECKS = [], [], []
YEARS = [2020, 2021, 2022]
TAX = 0.22


def inp(group, item, value, unit, value_type, source, note=""):
    INPUTS.append({"group": group, "item": item, "value": value, "unit": unit, "value_type": value_type, "source": source, "notes": note})
    return value


def o(case, fy, metric, value, unit, value_type="estimate", notes=""):
    OUT.append({"case": case, "fiscal_year": fy, "metric": metric, "value": round(value, 6) if isinstance(value, float) else value,
                "unit": unit, "value_type": value_type, "notes": notes})


def chk(ctype, item, expected, observed, tol, period=""):
    CHECKS.append({"check_type": ctype, "entity": "Disney pro forma", "source_id": "", "fiscal_period": period, "item": item,
                   "expected": round(float(expected), 6), "observed": round(float(observed), 6),
                   "status": "pass" if abs(float(expected) - float(observed)) <= tol else "fail", "detail": ""})


def q(doc, text):
    found, page = find_quote(doc, text)
    if not found:
        raise AssertionError(f"quote not found {doc}: {text[:60]}")
    CHECKS.append({"check_type": "accretion_input_quote", "entity": "", "source_id": doc, "fiscal_period": "", "item": text[:120],
                   "expected": "found", "observed": f"page {page or 'unnumbered'}", "status": "pass", "detail": ""})
    return f"{doc} p.{page or 'unnumbered'}"


def table_row(doc, idx, page, label):
    t = load_tables(doc)[idx]
    assert t.page == page, (doc, idx, t.page)
    hdr = [c for c in t.rows[1][2] if c.strip()[:4].isdigit()]
    for lab, vals, cells in t.rows:
        if cells[0].startswith(label):
            v, _ = parse_forecast_row(cells, len(hdr))
            return dict(zip([h[:4] for h in hdr], v)), f"{doc} p.{page} t{idx}"
    raise KeyError(label)


def gather():
    HF = pd.read_csv(PROC / "historical_financials.csv", low_memory=False, dtype={"source_page": str})
    TA = pd.read_csv(PROC / "transaction_assumptions.csv", dtype={"source_page": str})
    FR = pd.read_csv(PROC / "financial_ratios.csv")
    MF = pd.read_csv(PROC / "management_forecasts.csv")
    S = {}

    def hf(entity, fp, item, perimeter=None):
        qq = HF[(HF.entity == entity) & (HF.fiscal_period == fp) & (HF.line_item == item) & HF.is_primary]
        if perimeter:
            qq = qq[qq.perimeter == perimeter]
        r = qq.iloc[0]
        return float(r.value), f"{r.source_id} p.{r.source_page} [{r.record_id}]"

    ta = lambda i: (float(TA[TA.id == i].value.iloc[0]), f"transaction_assumptions {i}")
    # Disney standalone forecasts (May 2018 proxy)
    seg, s1 = table_row("JPROXY_ORIG_20180530", 613, "153", "Total Segment Operating Income")
    ebitda, s2 = table_row("JPROXY_ORIG_20180530", 613, "153", "EBITDA")
    rev, s3 = table_row("JPROXY_ORIG_20180530", 613, "153", "Revenue")
    for y in range(2018, 2023):
        inp("disney_forecast", f"revenue_FY{y}", rev[str(y)], "USD_m", "reported_forecast (Disney street forecasts)", s3)
        inp("disney_forecast", f"ebitda_FY{y}", ebitda[str(y)], "USD_m", "reported_forecast (Disney street forecasts)", s2)
        inp("disney_forecast", f"segment_operating_income_FY{y}", "" if seg[str(y)] is None else seg[str(y)], "USD_m",
            "reported_forecast (Disney street forecasts)" if seg[str(y)] is not None else "not_available_in_source", s1,
            "FY2022 shown as n/a in the proxy" if seg[str(y)] is None else "")
    S["seg"], S["ebitda"] = seg, ebitda
    corp_src = q("JPROXY_ORIG_20180530", "Corporate & Unallocated Shared Expenses | 2020E | (659 | ) | 4.2 | %")
    S["corp2020"] = inp("disney_forecast", "corporate_unallocated_FY2020", 659.0, "USD_m", "reported_forecast (Disney street estimates)", corp_src)
    S["corp_g"] = inp("disney_forecast", "corporate_unallocated_cagr", 0.042, "ratio", "reported_forecast (implied CAGR)", corp_src,
                      "used to extend corporate expense to FY2021-FY2022 (estimate)")
    q("JPROXY_ORIG_20180530", "the Disney street estimates and the Disney street forecasts were not internally prepared nor reviewed in advance or adopted by Disney management")
    for k, item in (("dis_int", "interest_expense_net"), ("dis_nci", "net_income_nci"), ("dis_ni", "net_income_attributable_parent"),
                    ("dis_sh", "shares_diluted"), ("dis_eps", "eps_diluted")):
        v, s = hf("DIS", "FY2018", item)
        S[k] = inp("disney_actual_FY2018", item, v, "USD_m" if "share" not in item and "eps" not in item else ("shares_m" if "shares" in item else "USD_per_share"),
                   "reported", s, "held flat in projections (estimate)" if k in ("dis_int", "dis_nci", "dis_sh") else "")
    # RemainCo forecasts (Disney forecasts for RemainCo, May proxy) and closing-perimeter non-operating items (8-K/A)
    mf = MF[(MF.forecast_set == "disney_for_remainco_original")]
    S["rc"] = {}
    for _, r in mf.iterrows():
        S["rc"][(r.metric, int(r.fiscal_year[:4]))] = float(r.value)
    for y in range(2020, 2024):
        for m in ("revenue", "ebitda"):
            inp("remainco_forecast", f"{m}_FY{y}_june", S["rc"][(m, y)], "USD_m", "reported_forecast (Disney forecasts for RemainCo)",
                "JPROXY_ORIG_20180530 p.129 t473")
    for k, item in (("rc_int", "interest_expense_net"), ("rc_intinc", "interest_income"), ("rc_eq", "equity_income_affiliates"),
                    ("rc_nci", "net_income_nci")):
        v, s = hf("RemainCo", "FY2018", item, "RemainCo (closing perimeter)")
        S[k] = inp("remainco_actual_FY2018_pro_forma", item, v, "USD_m", "reported (pro forma)", s, "held flat in projections (estimate)")
    S["rc_da_pct"] = inp("remainco_estimate", "da_pct_revenue", 0.0201, "ratio", "estimate", "dcf_assumptions.csv (Stage 3, B)")
    rsn = float(FR[(FR.entity == "RemainCo") & (FR.metric == "rsn_revenue_share") & (FR.fiscal_period == "FY2018")].value.iloc[0])
    S["rsn_share"] = inp("perimeter", "rsn_revenue_share_FY2018", rsn, "ratio", "derived", "financial_ratios.csv (Stage 2; 8-K/A Ex. 99.3 bridge)",
                         "RSN operating profit assumed proportional to revenue (estimate)")
    S["rsn_proceeds"], s = ta("P20")
    inp("perimeter", "rsn_sale_proceeds", S["rsn_proceeds"], "USD_m", "reported", s, "assumed to repay acquisition debt; tax on gain not modelled")
    # Financing
    S["cash"], s = ta("C12"); inp("financing", "cash_consideration", S["cash"], "USD_m", "reported", s)
    S["shares_new"], s = ta("C10"); inp("financing", "new_shares_issued_m", S["shares_new"], "shares_m", "reported", s)
    S["vwap"], s = ta("C05"); inp("financing", "average_disney_price_closing", S["vwap"], "USD_per_share", "reported", s)
    S["stock_val"], s = ta("C13"); inp("financing", "stock_consideration_implied", S["stock_val"], "USD_m", "reported", s)
    S["bridge"], s = ta("P22"); inp("financing", "bridge_loans_drawn", S["bridge"], "USD_m", "reported", s)
    S["repaid"], s = ta("P23"); inp("financing", "bridge_repaid_with_acquired_cash", S["repaid"], "USD_m", "reported", s)
    S["orig_shares"], s = ta("O06"); inp("financing", "original_all_stock_new_shares_m", S["orig_shares"], "shares_m", "reported", s)
    rsrc = q("DIS_8KA_20190327_EX99_3", "assuming an estimated weighted average interest rate of 3.3% based on New Disney")
    S["rate"] = inp("financing", "interest_rate_new_debt", 0.033, "ratio", "reported_assumption (Disney pro forma)", rsrc,
                    "short-term bridge/CP rate assumed by Disney; long-term refinancing would cost more (see sensitivity)")
    isrc = q("DIS_10K_FY2019", "Interest expense of $0.4 billion and $0.5 billion is included to reflect the cost of borrowings to finance the TFCF acquisition")
    inp("financing", "disney_pro_forma_financing_interest_FY2018", 500.0, "USD_m", "reported", isrc, "cross-check only")
    bb = q("DIS_425_20171215_CALL", "buying back $10 billion of our stock between now and shortly after the transaction closes, and up to an additional $10 billion within 24 months post-closing")
    inp("financing", "planned_buybacks_dec2017", 20000.0, "USD_m", "management_guidance", bb, "used only in the original-structure variant")
    tb = q("DIS_10K_FY2019", "In March 2019, Legacy Disney terminated its share repurchase program")
    inp("financing", "buyback_program_terminated_mar2019", "yes", "text", "reported", tb, "base case assumes no buybacks")
    # Purchase accounting
    psrc = q("DIS_10K_FY2019", "These pro formas also include $3.1 billion and $3.5 billion (including $0.4 billion and $0.8 billion of amortization related to the RSNs)")
    S["ppa"] = inp("purchase_accounting", "incremental_amortization_ex_rsn", 2700.0, "USD_m", "derived", psrc,
                   "FY2018 3.5bn - 0.8bn RSN = 2.7bn; FY2019 3.1bn - 0.4bn = 2.7bn; held flat FY2020-22 (estimate; film-cost step-ups amortize "
                   "faster early on, intangibles over 9-16 years)")
    q("DIS_10K_FY2019", "Intangible assets primarily consist of MVPD agreements, with a weighted average useful life of 9 years, and advertising networks and trade names, with a weighted average useful life of 16 years")
    # Tax
    S["tax"] = inp("tax", "tax_rate", TAX, "ratio", "estimate", "dcf_assumptions.csv (Stage 3 B: 21% federal + ~1% state)",
                   "applied to all pre-tax items incl. interest, PPA amortization, synergies and integration costs")
    # Reported anchor: Disney pro forma EPS (8-K/A Ex. 99.3)
    for idx, page, per in ((6, "5", "FY2018 (12m to 29 Sep 2018)"), (7, "6", "Q1 FY2019 (3m to 29 Dec 2018)")):
        t = load_tables("DIS_8KA_20190327_EX99_3")[idx]
        assert t.page == page
        rows = {lab: vals for lab, vals, _ in t.rows}
        dil = [r for r in t.rows if r[0] == "Diluted"]
        eps_dis, eps_pf = dil[0][1][0], dil[0][1][1]
        sh_dis, sh_pf = dil[1][1][0], dil[1][1][-1]
        ni_dis, ni_pf = rows["Net income attributable to Disney"][0], rows["Net income attributable to Disney"][-1]
        src = f"DIS_8KA_20190327_EX99_3 p.{page} t{idx}"
        inp("reported_anchor", f"disney_eps_diluted {per}", eps_dis, "USD_per_share", "reported", src)
        inp("reported_anchor", f"pro_forma_combined_eps_diluted {per}", eps_pf, "USD_per_share", "reported (pro forma)", src,
            "GAAP basis: includes purchase-accounting amortization and financing; excludes synergies; RSNs removed")
        o("reported anchor (Disney 8-K/A pro forma)", per, "eps_disney", eps_dis, "USD_per_share", "reported")
        o("reported anchor (Disney 8-K/A pro forma)", per, "eps_pro_forma", eps_pf, "USD_per_share", "reported")
        o("reported anchor (Disney 8-K/A pro forma)", per, "accretion_dilution_pct", eps_pf / eps_dis - 1, "ratio", "derived",
          "GAAP, no synergies; Disney FY2018 EPS includes one-off TCJA benefits")
        chk("accretion_eps", f"anchor {per}: EPS = NI / shares (Disney)", ni_dis / sh_dis, eps_dis, 0.011)
        chk("accretion_eps", f"anchor {per}: EPS = NI / shares (pro forma)", ni_pf / sh_pf, eps_pf, 0.011)
    return S


def synergies_base():
    import synergy
    sc = synergy.SCENARIOS["base"]
    syn = {y: sc["run_rate"] * sc["phase"][y] * (1 + sc["g"]) ** max(0, y - 2021) for y in YEARS}
    ic = {y: sc["run_rate"] * sc["ic_mult"] * synergy.IC_PHASE[y] for y in YEARS}
    return syn, ic


def model(S, case="base", realization=1.0, ic_mult_factor=1.0, cash_share=None, rate=None, price=None, ppa_factor=1.0,
          include_rsn=False, structure="closing", buybacks=0.0):
    syn0, ic0 = synergies_base()
    rate = S["rate"] if rate is None else rate
    t = S["tax"]
    total_consid = S["cash"] + S["stock_val"]
    if structure == "original":
        new_shares, new_debt = S["orig_shares"], 0.0
    else:
        cs = (S["cash"] / total_consid) if cash_share is None else cash_share
        px = S["vwap"] if price is None else price
        cash = total_consid * cs
        stock = total_consid - cash
        new_shares = stock / px if (cash_share is not None or price is not None) else S["shares_new"]
        new_debt = max(0.0, cash - S["repaid"])
    if not include_rsn:
        new_debt = max(0.0, new_debt - S["rsn_proceeds"])
    if buybacks:
        new_debt += buybacks
    rows = {}
    for y in YEARS:
        seg = S["seg"][str(y)]
        if seg is None:  # FY2022 segment OI not given: scale FY2021 by EBITDA growth (estimate)
            seg = S["seg"]["2021"] * S["ebitda"][str(y)] / S["ebitda"]["2021"]
        corp = S["corp2020"] * (1 + S["corp_g"]) ** (y - 2020)
        d_pre = seg - corp + S["dis_int"]
        d_ni = d_pre * (1 - t) + S["dis_nci"]
        rc_rev = 0.75 * S["rc"][("revenue", y)] + 0.25 * S["rc"][("revenue", y + 1)]
        rc_ebitda = 0.75 * S["rc"][("ebitda", y)] + 0.25 * S["rc"][("ebitda", y + 1)]
        rc_ebit = rc_ebitda - S["rc_da_pct"] * rc_rev
        if not include_rsn:
            rc_ebit *= (1 - S["rsn_share"])
        rc_pre = rc_ebit + S["rc_int"] + S["rc_intinc"] + S["rc_eq"]
        rc_ni = rc_pre * (1 - t) + S["rc_nci"]
        interest = new_debt * rate
        ppa = S["ppa"] * ppa_factor
        syn = syn0[y] * realization
        ic = ic0[y] * ic_mult_factor
        sh_sa = S["dis_sh"] - (buybacks / S["vwap"] if buybacks else 0.0)
        shares_pf = sh_sa + new_shares
        eps_sa = d_ni / S["dis_sh"]
        ni_adj = d_ni + rc_ni - interest * (1 - t) + syn * (1 - t)
        ni_gaap = ni_adj - ppa * (1 - t) - ic * (1 - t)
        rows[y] = {"disney_standalone_pretax": d_pre, "disney_standalone_ni": d_ni, "disney_standalone_shares": S["dis_sh"],
                   "disney_standalone_eps": eps_sa, "remainco_revenue_disney_fy": rc_rev, "remainco_ebitda_disney_fy": rc_ebitda,
                   "remainco_ebit": rc_ebit, "remainco_pretax": rc_pre, "remainco_ni": rc_ni, "incremental_debt": new_debt,
                   "incremental_interest_pretax": interest, "incremental_interest_aftertax": interest * (1 - t),
                   "ppa_amortization_pretax": ppa, "ppa_amortization_aftertax": ppa * (1 - t), "synergies_pretax": syn,
                   "synergies_aftertax": syn * (1 - t), "integration_costs_pretax": ic, "integration_costs_aftertax": ic * (1 - t),
                   "new_shares_issued": new_shares, "pro_forma_shares": shares_pf, "pro_forma_ni_adjusted": ni_adj,
                   "pro_forma_ni_gaap_basis": ni_gaap, "pro_forma_eps_adjusted": ni_adj / shares_pf, "pro_forma_eps_gaap_basis": ni_gaap / shares_pf,
                   "accretion_adjusted": (ni_adj / shares_pf) / eps_sa - 1, "accretion_gaap_basis": (ni_gaap / shares_pf) / eps_sa - 1}
    return rows


def build():
    S = gather()
    cases = {
        "base: closing financing, RSNs sold, synergies (base)": {},
        "variant: RSNs retained": {"include_rsn": True},
        "variant: no synergies": {"realization": 0.0},
        "variant: original Dec 2017 all-stock structure (515m shares), no buybacks": {"structure": "original"},
        "variant: original all-stock + $20bn planned buybacks (debt-funded at 3.3%)": {"structure": "original", "buybacks": 20000.0},
    }
    for case, kw in cases.items():
        rows = model(S, **kw)
        for y, r in rows.items():
            for k, v in r.items():
                o(case, f"FY{y}", k, v, "ratio" if k.startswith("accretion") else ("USD_per_share" if "eps" in k else
                                                                                    ("shares_m" if "shares" in k else "USD_m")))
            # checks
            chk("accretion_eps", f"{case} FY{y}: adjusted EPS = NI / shares", r["pro_forma_ni_adjusted"] / r["pro_forma_shares"],
                r["pro_forma_eps_adjusted"], 1e-9, f"FY{y}")
            chk("accretion_eps", f"{case} FY{y}: accretion = PF EPS / standalone EPS - 1",
                r["pro_forma_eps_adjusted"] / r["disney_standalone_eps"] - 1, r["accretion_adjusted"], 1e-9, f"FY{y}")
            chk("accretion_ppa", f"{case} FY{y}: PPA after tax = amortization x (1 - t)", r["ppa_amortization_pretax"] * (1 - S["tax"]),
                r["ppa_amortization_aftertax"], 1e-9, f"FY{y}")
            chk("accretion_ppa", f"{case} FY{y}: GAAP NI = adjusted NI - PPA(at) - integration(at)",
                r["pro_forma_ni_adjusted"] - r["ppa_amortization_aftertax"] - r["integration_costs_aftertax"], r["pro_forma_ni_gaap_basis"], 1e-6, f"FY{y}")
            chk("accretion_financing", f"{case} FY{y}: interest = incremental debt x rate", r["incremental_debt"] * S["rate"],
                r["incremental_interest_pretax"], 1e-6, f"FY{y}")
    # financing reconciliations
    chk("accretion_financing", "shares issued x closing average price = stock consideration (~$35bn, rounded)", S["stock_val"],
        S["shares_new"] * S["vwap"], 100.0)
    chk("accretion_financing", "net incremental debt = cash consideration - bridge repaid from acquired cash (closing, RSNs retained)",
        S["cash"] - S["repaid"], model(S, include_rsn=True)[2020]["incremental_debt"], 1e-6)
    chk("accretion_financing", "original structure: 0.2745 x 1,871m fully diluted shares ~ 515m new shares (release rounding)",
        S["orig_shares"], 0.2745 * 1871.147237, 2.0)
    # sensitivities on FY2021 (second full fiscal year after close)
    sens = {
        "synergy_realization": [("0%", {"realization": 0.0}), ("50%", {"realization": 0.5}), ("75%", {"realization": 0.75}),
                                ("100%", {}), ("125%", {"realization": 1.25})],
        "integration_cost_overrun": [("1.0x", {}), ("1.5x", {"ic_mult_factor": 1.5}), ("2.0x", {"ic_mult_factor": 2.0})],
        "financing_cash_share": [(f"{c:.0%} cash", {"cash_share": c}) for c in (0.0, 0.25, 0.5047, 0.75, 1.0)],
        "interest_rate_new_debt": [(f"{r:.1%}", {"rate": r}) for r in (0.02, 0.033, 0.04, 0.05, 0.06)],
        "disney_share_price_for_stock_portion": [(f"${p:.0f}", {"price": p}) for p in (90.0, 100.0, 114.18, 120.0, 130.0)],
        "ppa_amortization": [(f"{f:.0%}", {"ppa_factor": f}) for f in (0.5, 1.0, 1.5)],
    }
    for name, items in sens.items():
        prev = None
        for lab, kw in items:
            r = model(S, **kw)
            for y in YEARS:
                for m in ("accretion_adjusted", "accretion_gaap_basis", "pro_forma_eps_adjusted", "pro_forma_eps_gaap_basis"):
                    o(f"sensitivity: {name} = {lab}", f"FY{y}", m, r[y][m], "ratio" if m.startswith("accretion") else "USD_per_share")
            v = r[2021]["accretion_gaap_basis" if name in ("integration_cost_overrun", "ppa_amortization") else "accretion_adjusted"]
            if prev is not None:
                expect_up = name in ("synergy_realization", "disney_share_price_for_stock_portion")
                ok = (v > prev) if expect_up else (v < prev) if name in ("integration_cost_overrun", "interest_rate_new_debt", "ppa_amortization") else True
                CHECKS.append({"check_type": "accretion_sensitivity", "entity": "", "source_id": "", "fiscal_period": "FY2021",
                               "item": f"{name} {lab}: expected direction", "expected": "monotonic", "observed": round(v - prev, 6),
                               "status": "pass" if ok else "fail", "detail": ""})
            prev = v
    # timeline statement
    base = model(S)
    first_adj = next((f"FY{y}" for y in YEARS if base[y]["accretion_adjusted"] > 0), "not within FY2020-FY2022")
    first_gaap = next((f"FY{y}" for y in YEARS if base[y]["accretion_gaap_basis"] > 0), "not within FY2020-FY2022")
    o("base: closing financing, RSNs sold, synergies (base)", "timeline", "first_accretive_year_adjusted", first_adj, "fiscal year", "estimate",
      "Management guidance: accretive before purchase accounting in the second fiscal year after close (= FY2021 for a Mar 2019 close)")
    o("base: closing financing, RSNs sold, synergies (base)", "timeline", "first_accretive_year_gaap_basis", first_gaap, "fiscal year", "estimate")
    return S


def write():
    for path, rows in ((PROC / "accretion_dilution_inputs.csv", INPUTS), (PROC / "accretion_dilution_outputs.csv", OUT)):
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
