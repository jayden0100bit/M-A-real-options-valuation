"""Stage 2: historical ratios and segment metrics from the verified data layer.

Inputs : data/processed/historical_financials.csv  (single source of truth; primary rows only,
         except prior-year balance sheets needed for averages, which are flagged)
Outputs: data/processed/financial_ratios.csv
         data/processed/segment_analysis.csv

Every output row lists the input figures it uses, each tagged with its record_id, source_id and
printed page, so any number can be traced back to the filing. Nothing is estimated. Where an
input is not in the dataset, the output row is written with an empty value and
value_type = "not_available", together with the reason.

value_type:
  reported       - a figure taken unchanged from the dataset (e.g. revenue)
  derived        - arithmetic on reported figures, using the stated formula (ratios, EBIT, EBITDA)
  adjusted       - derived and also excluding an item the filings report separately (restructuring/impairment)
  not_available  - cannot be computed from the verified data; see notes
"""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HF = ROOT / "data" / "processed" / "historical_financials.csv"
OUT_R = ROOT / "data" / "processed" / "financial_ratios.csv"
OUT_S = ROOT / "data" / "processed" / "segment_analysis.csv"

PERIODS = ["FY2015", "FY2016", "FY2017", "FY2018"]
CONSOL = {"DIS": "Disney consolidated", "21CF": "21CF consolidated (pre-separation, incl. New Fox businesses)"}


class Data:
    def __init__(self):
        df = pd.read_csv(HF, low_memory=False, dtype={"source_page": str})
        self.all = df
        self.p = df[df.is_primary]

    def _pick(self, rows, desc):
        if len(rows) == 0:
            return None
        if len(rows) > 1:
            raise ValueError(f"ambiguous input {desc}: {rows.record_id.tolist()}")
        return rows.iloc[0]

    def get(self, entity, perimeter, period, item, statement=None):
        r = self.p[(self.p.entity == entity) & (self.p.perimeter == perimeter) &
                   (self.p.fiscal_period == period) & (self.p.line_item == item)]
        if statement:
            r = r[r.statement == statement]
        return self._pick(r, (entity, perimeter, period, item))

    def get_prior_bs(self, entity, period, item):
        """Balance-sheet value for a year before the primary range (FY2014): the comparative column of
        the earliest 10-K. Used only for averages; flagged in notes."""
        src = {"DIS": "DIS_10K_FY2015", "21CF": "FOX_10K_FY2015"}[entity]
        r = self.all[(self.all.entity == entity) & (self.all.source_id == src) & (self.all.fiscal_period == period) &
                     (self.all.line_item == item) & (self.all.statement == "balance_sheet")]
        return self._pick(r, (entity, period, item, "prior"))


def tag(name, row):
    return f"{name}={row.value:g} [{row.record_id}; {row.source_id} p.{row.source_page}]"


ratio_rows, seg_rows = [], []


def emit(entity, perimeter, period, metric, category, value, unit, value_type, formula, inputs, note="", period_end=""):
    ratio_rows.append(dict(entity=entity, perimeter=perimeter, fiscal_period=period, period_end=period_end,
                           category=category, metric=metric,
                           value="" if value is None else round(value, 6), unit=unit, value_type=value_type,
                           formula=formula, inputs=" | ".join(inputs), notes=note))


def missing(entity, perimeter, period, metric, category, unit, reason):
    emit(entity, perimeter, period, metric, category, None, unit, "not_available", "", [], reason)


def consolidated(d: Data):
    for ent, per in CONSOL.items():
        prev = {}
        for fp in PERIODS:
            g = lambda item, st=None: d.get(ent, per, fp, item, st)
            rev = g("revenue", "income_statement")
            pend = rev.period_end
            E = lambda *a, **k: emit(ent, per, fp, *a, period_end=pend, **k)
            E("revenue", "growth", rev.value, "USD_m", "reported", "revenue", [tag("revenue", rev)])
            if "revenue" in prev:
                pr = prev["revenue"]
                E("revenue_growth_yoy", "growth", rev.value / pr.value - 1, "ratio", "derived",
                  "revenue / revenue(prior FY) - 1", [tag("revenue", rev), tag("revenue_prior", pr)],
                  "Disney FY2015 had 53 weeks, which flatters FY2015 and depresses FY2016 growth." if ent == "DIS" and fp == "FY2016" else "")
            # ---- operating profit build (same perimeter on both companies: before equity income, other, interest)
            da = g("depreciation_amortization", "income_statement")
            restr = g("restructuring_impairment", "income_statement")
            if ent == "DIS":
                cs, cp, tce = g("cost_of_services"), g("cost_of_products"), g("total_costs_and_expenses")
                direct = cs.value + cp.value
                E("gross_profit_excl_da", "profitability", rev.value + direct, "USD_m", "derived",
                  "revenue + cost_of_services + cost_of_products (both exclusive of D&A)",
                  [tag("revenue", rev), tag("cost_of_services", cs), tag("cost_of_products", cp)],
                  "Disney's cost of services/products excludes D&A. Not comparable with 21CF.")
                ebit = rev.value + tce.value + restr.value
                ebit_inputs = [tag("revenue", rev), tag("total_costs_and_expenses", tce), tag("restructuring_impairment", restr)]
                ebit_f = "revenue + total_costs_and_expenses + restructuring_impairment"
            else:
                ox, sga = g("operating_expenses"), g("sga")
                E("gross_profit_excl_da", "profitability", rev.value + ox.value, "USD_m", "derived",
                  "revenue + operating_expenses", [tag("revenue", rev), tag("operating_expenses", ox)],
                  "21CF 'operating expenses' (programming, production, participations, etc.) differ in scope from "
                  "Disney's cost of services/products. FY2016-FY2017 were reclassified in the FY2018 10-K; primary "
                  "FY2015-FY2017 values are the FY2017 10-K basis, FY2018 is the FY2018 10-K basis (see report).")
                ebit = rev.value + ox.value + sga.value + da.value + restr.value
                ebit_inputs = [tag("revenue", rev), tag("operating_expenses", ox), tag("sga", sga),
                               tag("depreciation_amortization", da), tag("restructuring_impairment", restr)]
                ebit_f = "revenue + operating_expenses + sga + depreciation_amortization + restructuring_impairment"
            E("gross_margin_excl_da", "profitability", None if False else (ratio_rows[-1]["value"] / rev.value), "ratio",
              "derived", "gross_profit_excl_da / revenue", [tag("revenue", rev)], ratio_rows[-1]["notes"])
            ebit_note = ("EBIT here = operating income before equity income of investees/affiliates, other "
                         "income/expense and interest. Neither company reports this subtotal; it is derived.")
            E("ebit", "profitability", ebit, "USD_m", "derived", ebit_f, ebit_inputs, ebit_note)
            E("ebit_margin", "profitability", ebit / rev.value, "ratio", "derived", "ebit / revenue", ebit_inputs)
            ebitda = ebit - da.value
            E("ebitda", "profitability", ebitda, "USD_m", "derived", "ebit - depreciation_amortization (D&A negative)",
              ebit_inputs + [tag("depreciation_amortization", da)],
              "Uses income-statement D&A. 21CF also amortizes cable distribution investments (shown separately "
              "in its cash flow statement); that amortization is not added back here.")
            E("ebitda_margin", "profitability", ebitda / rev.value, "ratio", "derived", "ebitda / revenue", [])
            E("ebitda_excl_restructuring", "profitability", ebitda - restr.value, "USD_m", "adjusted",
              "ebitda - restructuring_impairment", [tag("restructuring_impairment", restr)],
              "Adjusted: excludes restructuring and impairment charges as reported on the income statement.")
            E("ebitda_excl_restructuring_margin", "profitability", (ebitda - restr.value) / rev.value, "ratio", "adjusted",
              "ebitda_excl_restructuring / revenue", [])
            pre, tax = g("pretax_income_continuing"), g("income_tax")
            ni = g("net_income_attributable_parent")
            E("net_income_attributable", "profitability", ni.value, "USD_m", "reported", "net_income_attributable_parent", [tag("ni", ni)])
            E("net_margin", "profitability", ni.value / rev.value, "ratio", "derived", "net_income_attributable_parent / revenue",
              [tag("ni", ni), tag("revenue", rev)],
              "21CF net income includes discontinued operations (small, FY2015-FY2018)." if ent == "21CF" else "")
            E("effective_tax_rate", "profitability", -tax.value / pre.value, "ratio", "derived",
              "-income_tax / pretax_income_continuing", [tag("income_tax", tax), tag("pretax", pre)],
              {"21CF": {"FY2018": "FY2018 includes the effect of the December 2017 US tax law change (21CF reports a tax benefit).",
                        "FY2015": "FY2015 pretax includes the ~$5.0bn gain on the Sky Italia/Deutschland sale in Other, net."},
               "DIS": {"FY2018": "FY2018 includes the effect of the December 2017 US tax law change."}}.get(ent, {}).get(fp, ""))
            # ---- returns: average balance sheet
            ta, eq = g("total_assets"), g("equity_attributable_parent")
            if fp == "FY2015":
                ta0, eq0 = d.get_prior_bs(ent, "FY2014", "total_assets"), d.get_prior_bs(ent, "FY2014", "equity_attributable_parent")
                prior_note = "FY2014 opening balance from the FY2015 10-K comparative column (not a primary value)."
            else:
                ta0, eq0 = prev["total_assets"], prev["equity_attributable_parent"]
                prior_note = ""
            E("roa_avg_assets", "returns", ni.value / ((ta.value + ta0.value) / 2), "ratio", "derived",
              "net_income_attributable_parent / average(total_assets, prior total_assets)",
              [tag("ni", ni), tag("total_assets", ta), tag("total_assets_prior", ta0)], prior_note)
            E("roe_avg_equity", "returns", ni.value / ((eq.value + eq0.value) / 2), "ratio", "derived",
              "net_income_attributable_parent / average(parent equity, prior parent equity)",
              [tag("ni", ni), tag("equity", eq), tag("equity_prior", eq0)],
              (prior_note + " Disney's equity is reduced by large buybacks (treasury stock), which raises ROE.").strip()
              if ent == "DIS" else prior_note)
            # ---- balance sheet
            cash, tb, nd = g("cash"), g("total_borrowings"), g("net_debt")
            te = g("total_equity")
            tca, tcl = g("total_current_assets"), g("total_current_liabilities")
            bc = g("borrowings_current")
            for nm, row in (("cash", cash), ("total_borrowings", tb), ("net_debt", nd), ("total_equity", te)):
                E(nm, "balance_sheet", row.value, "USD_m", row.data_type, row.line_item if row.data_type == "reported" else row.notes, [tag(nm, row)])
            E("working_capital", "balance_sheet", tca.value - tcl.value, "USD_m", "derived",
              "total_current_assets - total_current_liabilities", [tag("tca", tca), tag("tcl", tcl)])
            E("working_capital_excl_cash_debt", "balance_sheet", (tca.value - cash.value) - (tcl.value - bc.value), "USD_m",
              "derived", "(total_current_assets - cash) - (total_current_liabilities - borrowings_current)",
              [tag("tca", tca), tag("cash", cash), tag("tcl", tcl), tag("borrowings_current", bc)])
            E("debt_to_equity", "leverage", tb.value / te.value, "ratio", "derived", "total_borrowings / total_equity",
              [tag("total_borrowings", tb), tag("total_equity", te)], "Book values; total equity includes noncontrolling interests.")
            E("debt_to_capital", "leverage", tb.value / (tb.value + te.value), "ratio", "derived",
              "total_borrowings / (total_borrowings + total_equity)", [])
            E("net_debt_to_ebitda", "leverage", nd.value / ebitda, "x", "derived", "net_debt / ebitda", [tag("net_debt", nd)])
            intx = g("interest_expense_net")
            E("ebit_interest_cover", "leverage", ebit / -intx.value, "x", "derived", "ebit / -interest_expense_net",
              [tag("interest_expense_net", intx)],
              "Disney's interest expense is net of capitalized interest and interest income; 21CF reports interest income separately.")
            # ---- cash flow
            cfo, capex, fcf = g("cfo"), g("capex"), g("fcf_cfo_less_capex")
            E("cfo", "cash_flow", cfo.value, "USD_m", "reported", "cfo", [tag("cfo", cfo)],
              "21CF: cash from continuing operations." if ent == "21CF" else "")
            E("capex", "cash_flow", capex.value, "USD_m", "reported", "capex", [tag("capex", capex)])
            E("fcf_cfo_less_capex", "cash_flow", fcf.value, "USD_m", "derived", "cfo + capex", [tag("cfo", cfo), tag("capex", capex)],
              "Not a company-defined measure. Film/TV content spend is inside CFO for both companies, not capex.")
            E("capex_to_revenue", "cash_flow", -capex.value / rev.value, "ratio", "derived", "-capex / revenue", [])
            E("fcf_margin", "cash_flow", fcf.value / rev.value, "ratio", "derived", "fcf / revenue", [])
            E("cfo_to_ebitda", "cash_flow", cfo.value / ebitda, "ratio", "derived", "cfo / ebitda", [])
            E("fcf_to_net_income", "cash_flow", fcf.value / ni.value, "ratio", "derived", "fcf / net_income_attributable_parent", [])
            prev = {"revenue": rev, "total_assets": ta, "equity_attributable_parent": eq}
        # CAGRs
        r = {fp: d.get(ent, per, fp, "revenue", "income_statement") for fp in PERIODS}
        for a, b, n in (("FY2015", "FY2017", 2), ("FY2015", "FY2018", 3)):
            emit(ent, per, f"{a}-{b}", f"revenue_cagr_{a}_{b}", "growth", (r[b].value / r[a].value) ** (1 / n) - 1, "ratio",
                 "derived", f"(revenue {b} / revenue {a})^(1/{n}) - 1", [tag(a, r[a]), tag(b, r[b])], period_end=r[b].period_end)


def remainco(d: Data):
    per = None
    for fp in ["FY2015", "FY2016", "FY2017", "6M_DEC2017", "FY2018", "Q1_FY2019"]:
        rows = d.p[(d.p.entity == "RemainCo") & (d.p.fiscal_period == fp) & (d.p.statement == "income_statement")]
        if rows.empty:
            continue
        per = rows.perimeter.iloc[0]
        g = lambda item: d.get("RemainCo", per, fp, item, "income_statement")
        rev, ox, sga, da, restr = g("revenue"), g("operating_expenses"), g("sga"), g("depreciation_amortization"), g("restructuring_impairment")
        pend = rev.period_end
        basis = rev.basis
        E = lambda *a, **k: emit("RemainCo", per, fp, *a, period_end=pend, **k)
        src_note = f"Pro forma (S-X Article 11), basis {basis}."
        E("revenue", "growth", rev.value, "USD_m", "reported", "revenue (pro forma as presented)", [tag("revenue", rev)], src_note)
        h = d.get("21CF", CONSOL["21CF"], fp, "revenue", "income_statement") if fp.startswith("FY") else None
        if h is None:  # 6M / Q1: use the 21CF historical column of the same pro forma table
            hh = d.all[(d.all.entity == "21CF") & (d.all.perimeter == "21CF historical") & (d.all.fiscal_period == fp) &
                       (d.all.source_id == rev.source_id) & (d.all.line_item == "revenue")]
            h = hh.iloc[0] if len(hh) else None
        if h is not None:
            E("share_of_21cf_revenue", "perimeter", rev.value / h.value, "ratio", "derived", "RemainCo revenue / 21CF consolidated revenue",
              [tag("remainco_revenue", rev), tag("21cf_revenue", h)])
        ebit = rev.value + ox.value + sga.value + da.value + restr.value
        inp = [tag("revenue", rev), tag("operating_expenses", ox), tag("sga", sga), tag("depreciation_amortization", da),
               tag("restructuring_impairment", restr)]
        note = (src_note + " Includes all 21CF corporate costs (New Fox removed on an ASC 205 basis without carve-out "
                "allocations) and the RSNs that Disney later divested.")
        E("ebit", "profitability", ebit, "USD_m", "derived", "revenue + operating_expenses + sga + D&A + restructuring_impairment", inp, note)
        E("ebit_margin", "profitability", ebit / rev.value, "ratio", "derived", "ebit / revenue", [], note)
        e21 = [r for r in ratio_rows if r["entity"] == "21CF" and r["fiscal_period"] == fp and r["metric"] == "ebit"]
        if e21:
            E("share_of_21cf_ebit", "perimeter", ebit / e21[0]["value"], "ratio", "derived",
              "RemainCo ebit / 21CF consolidated ebit (same EBIT definition)", [f"21cf_ebit={e21[0]['value']:g} [financial_ratios.csv]"],
              "RemainCo carries all 21CF corporate costs (no allocation to New Fox), so this understates the acquired "
              "businesses' share of operating profit. The opex/SG&A reclassification between filings does not affect EBIT.")
        E("ebitda", "profitability", ebit - da.value, "USD_m", "derived", "ebit - depreciation_amortization", [tag("D&A", da)],
          note + " D&A is the pro forma income-statement line; no capex is available to pair with it.")
        E("ebitda_margin", "profitability", (ebit - da.value) / rev.value, "ratio", "derived", "ebitda / revenue", [], note)
        pre, tax, ni = g("pretax_income_continuing"), g("income_tax"), g("income_continuing_ops_attributable_parent")
        E("income_continuing_attributable", "profitability", ni.value, "USD_m", "reported",
          "income_continuing_ops_attributable_parent", [tag("ni", ni)], src_note)
        E("net_margin_continuing", "profitability", ni.value / rev.value, "ratio", "derived",
          "income_continuing_ops_attributable_parent / revenue", [], src_note)
        E("effective_tax_rate", "profitability", -tax.value / pre.value, "ratio", "derived", "-income_tax / pretax_income_continuing",
          [tag("income_tax", tax), tag("pretax", pre)],
          src_note + (" FY2015 pretax includes the ~$5.0bn Sky Italia/Deutschland disposal gain." if fp == "FY2015" else ""))
        for m, u in (("cfo", "USD_m"), ("capex", "USD_m"), ("fcf_cfo_less_capex", "USD_m")):
            missing("RemainCo", per, fp, m, "cash_flow", u,
                    "No RemainCo cash-flow statement in the 2018 joint proxy or the 8-K/A; capex for the acquired perimeter is not disclosed.")
    # RSN revenue from Disney's pro forma bridge
    for fp in ["FY2018", "Q1_FY2019"]:
        b = d.all[(d.all.perimeter == "Divestiture of RSNs (Disney pro forma bridge)") & (d.all.fiscal_period == fp) &
                  (d.all.line_item == "revenue")].iloc[0]
        rc = d.get("RemainCo", "RemainCo (closing perimeter)", fp, "revenue", "income_statement")
        emit("RemainCo", "RemainCo (closing perimeter)", fp, "rsn_revenue_share", "perimeter", -b.value / rc.value, "ratio", "derived",
             "-(RSN divestiture revenue adjustment) / RemainCo revenue", [tag("rsn_bridge_revenue", b), tag("remainco_revenue", rc)],
             "RSN revenue as eliminated in the New Disney pro forma (8-K/A Ex. 99.3). Only revenue is clean (note h).",
             period_end=rc.period_end)
    # balance sheets
    for fp in ["MAR2018", "DEC2018"]:
        rows = d.p[(d.p.entity == "RemainCo") & (d.p.fiscal_period == fp) & (d.p.statement == "balance_sheet")]
        per = rows.perimeter.iloc[0]
        g = lambda item: d.get("RemainCo", per, fp, item, "balance_sheet")
        cash, tb, nd, te = g("cash"), g("total_borrowings"), g("net_debt"), g("total_equity")
        tca, tcl = g("total_current_assets"), g("total_current_liabilities")
        E = lambda *a, **k: emit("RemainCo", per, fp, *a, period_end=cash.period_end, **k)
        n = ("Dec 2018 cash includes proceeds of the Oct 2018 sale of the 39% Sky stake (~$15.1bn) and the pro forma "
             "net $6.5bn New Fox dividend; current liabilities include the matching $6.5bn transaction tax payable."
             if fp == "DEC2018" else
             "Pro forma includes the net $6.5bn New Fox dividend in cash and a $6.5bn transaction tax payable in current liabilities.")
        for nm, row in (("cash", cash), ("total_borrowings", tb), ("net_debt", nd), ("total_equity", te)):
            E(nm, "balance_sheet", row.value, "USD_m", "reported" if row.data_type == "pro_forma" else row.data_type,
              nm, [tag(nm, row)], n)
        E("working_capital", "balance_sheet", tca.value - tcl.value, "USD_m", "derived", "total_current_assets - total_current_liabilities",
          [tag("tca", tca), tag("tcl", tcl)], n)
        E("debt_to_equity", "leverage", tb.value / te.value, "ratio", "derived", "total_borrowings / total_equity", [], n)


def segments(d: Data):
    p = d.p[(d.p.statement == "segment") & d.p.entity.isin(["DIS", "21CF"])]
    spec = {"DIS": ("segment_operating_income", "Total consolidated revenues", "Total segment operating income", "segment operating income"),
            "21CF": ("segment_oibda", "Total revenues", "Total Segment OIBDA", "Segment OIBDA")}
    for ent, (pm, rev_total, prof_total, pname) in spec.items():
        for fp in PERIODS:
            q = p[(p.entity == ent) & (p.fiscal_period == fp)]
            rev = q[q.line_item == "segment_revenue"]
            prof = q[q.line_item == pm]
            # Disney: use segment totals (third parties + intersegment) - rows without "- Third parties/Intersegment"
            if ent == "DIS":
                rev = rev[~rev.segment.str.contains(" - Third parties| - Intersegment", regex=True)]
                rev = rev.assign(segment=rev.segment.str.replace(" - total", "", regex=False))
            tot_rev = rev[rev.segment == rev_total].iloc[0]
            tot_prof = prof[prof.segment == prof_total].iloc[0]
            perim = CONSOL[ent]
            for _, r in rev.iterrows():
                if r.segment in (rev_total,):
                    continue
                pr = prof[prof.segment == r.segment]
                pr = pr.iloc[0] if len(pr) else None
                base = dict(entity=ent, perimeter=perim, fiscal_period=fp, period_end=r.period_end, segment=r.segment)
                seg_rows.append({**base, "metric": "segment_revenue", "value": r.value, "unit": "USD_m", "value_type": "reported",
                                 "formula": "", "inputs": tag("revenue", r), "notes": ""})
                share_ok = not r.segment.startswith("Other, Corporate")
                seg_rows.append({**base, "metric": "revenue_share", "value": round(r.value / tot_rev.value, 6) if share_ok else "",
                                 "unit": "ratio", "value_type": "derived" if share_ok else "not_available",
                                 "formula": "segment revenue / total revenue", "inputs": tag("total_revenue", tot_rev),
                                 "notes": "" if share_ok else "Eliminations/corporate line: a revenue share is not meaningful."})
                if pr is not None:
                    seg_rows.append({**base, "metric": pm, "value": pr.value, "unit": "USD_m", "value_type": "reported",
                                     "formula": "", "inputs": tag(pm, pr), "notes": ""})
                    if r.value and share_ok:
                        seg_rows.append({**base, "metric": "segment_margin", "value": round(pr.value / r.value, 6), "unit": "ratio",
                                         "value_type": "derived", "formula": f"{pname} / segment revenue",
                                         "inputs": f"{tag('profit', pr)} | {tag('revenue', r)}", "notes": ""})
                        seg_rows.append({**base, "metric": "profit_share", "value": round(pr.value / tot_prof.value, 6), "unit": "ratio",
                                         "value_type": "derived", "formula": f"{pname} / total {pname}", "inputs": tag("total", tot_prof),
                                         "notes": ""})
            # totals
            base = dict(entity=ent, perimeter=perim, fiscal_period=fp, period_end=tot_rev.period_end, segment="Total")
            seg_rows.append({**base, "metric": "segment_revenue", "value": tot_rev.value, "unit": "USD_m", "value_type": "reported",
                             "formula": "", "inputs": tag("revenue", tot_rev), "notes": ""})
            seg_rows.append({**base, "metric": pm, "value": tot_prof.value, "unit": "USD_m", "value_type": "reported",
                             "formula": "", "inputs": tag(pm, tot_prof), "notes": ""})
            seg_rows.append({**base, "metric": "segment_margin", "value": round(tot_prof.value / tot_rev.value, 6), "unit": "ratio",
                             "value_type": "derived", "formula": f"total {pname} / total revenue", "inputs": "", "notes": ""})
    for r in seg_rows:
        if r["entity"] == "21CF":
            r["notes"] = ((r["notes"] + " ") if r["notes"] else "") + (
                "21CF consolidated segment, NOT the acquired perimeter: Cable Network Programming mixes acquired networks "
                "(FX, National Geographic, RSNs, international, Star) with New Fox networks (Fox News, FS1, etc.); "
                "Television is almost entirely New Fox.")
        if r["entity"] == "DIS" and r["metric"] in ("segment_operating_income", "segment_margin", "profit_share"):
            r["notes"] = ((r["notes"] + " ") if r["notes"] else "") + (
                "Disney segment operating income is after D&A; 21CF Segment OIBDA is before D&A. Not comparable.")
    # RemainCo segments: not available
    for fp in ["FY2015", "FY2016", "FY2017", "FY2018"]:
        seg_rows.append(dict(entity="RemainCo", perimeter="RemainCo", fiscal_period=fp, period_end="", segment="(all)",
                             metric="segment_revenue", value="", unit="USD_m", value_type="not_available", formula="", inputs="",
                             notes="No segment breakdown of RemainCo is disclosed in the 2018 joint proxy or the 8-K/A."))


def main():
    d = Data()
    consolidated(d)
    remainco(d)
    segments(d)
    for path, rows in ((OUT_R, ratio_rows), (OUT_S, seg_rows)):
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} rows -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
