"""Extract the management forecasts from the 2018 joint proxy statements.

Output: data/processed/management_forecasts.csv (one row per forecast figure) and
        verification checks of type ``forecast_extraction``.

Sources (pinned tables; table index = position of <table> in the downloaded HTML, page = printed page):
  May 2018 proxy (JPROXY_ORIG_20180530, 424B3 filed 2018-05-30; "latest practicable date" 25 May 2018)
    p.127 t460  21CF forecasts for RemainCo provided to 21CF's financial advisor (revenue, EBITDA)
    p.127 t461  same: levered FCF and net adjustment to unlevered FCF
    p.129 t473  Disney forecasts for RemainCo (revenue, EBITDA, unlevered FCF)
  June 2018 proxy (JPROXY_AMENDED_20180628, filed 2018-06-28): SUBSEQUENT to the May valuation date
    p.172 t616  updated 21CF forecasts for RemainCo (revenue, EBITDA)
    p.172 t617  updated levered FCF and adjustments (Goldman / Centerview)
    p.174 t630  updated Disney forecasts for RemainCo

Footnote markers: proxy tables put footnote references in their own cells, e.g. "(6,664" + ") (2)"
or a bare "(4)". A bare single-digit "(n)" cannot be told apart from a value of -n on its own, so it is
treated as a *candidate* marker and accepted as a marker only when the remaining value cells then
match the number of fiscal-year columns exactly. Otherwise the row is rejected with an error.
"N/A" cells are stored as not available (empty value), never as zero.

Independent verification: every figure is matched again against the page text produced by
``sec_text.paged_lines`` (a separate extraction of the same filing). The row must be found on the cited
printed page, and the figures must appear in the same order with the same sign.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sec_tables import load_tables  # noqa: E402
from sec_text import paged_lines  # noqa: E402

OUT = ROOT / "data" / "processed" / "management_forecasts.csv"

DEF_EBITDA = ("EBITDA as defined by the forecast provider; no reconciliation to GAAP is given in the proxy. "
              "Not equal to the EBITDA derived in this project (operating income + income-statement D&A).")
DEF_UFCF_DISNEY = "Unlevered free cash flow = EBITDA less cash taxes, less capital expenditures and less changes in net working capital (proxy footnote 1)."
DEF_LFCF = ("Levered free cash flow = EBITDA less cash taxes, less cash interest expense, less capital expenditures, less increases "
            "in net working capital, plus stock-based compensation expenses, plus dividends received (proxy footnote 1).")
DEF_ADJ_ORIG = ("Net adjustments include: (a) adding back interest expense, (b) subtracting stock-based compensation expenses, "
                "dividends received and investments and (c) adjusting for taxes (footnote 3).")
DEF_ADJ_UPD = ("Net adjustments include (a) adding back interest expense, (b) subtracting stock-based compensation, dividends received "
               "and other non-recurring cash flow, (c) adjusting for taxes and (d) for Goldman, subtracting investment amounts (footnote 3).")

SPECS = [
    # proxy, table, page, forecast_set, provider, recipient, {row label prefix: (metric, definition)}
    ("JPROXY_ORIG_20180530", 460, "127", "21cf_to_advisor_original", "21CF management", "Goldman Sachs / 21CF board",
     {"Revenue": ("revenue", "Revenue"), "EBITDA": ("ebitda", DEF_EBITDA)}),
    ("JPROXY_ORIG_20180530", 461, "127", "21cf_to_advisor_original", "21CF management", "Goldman Sachs / 21CF board",
     {"Levered Free Cash Flow": ("levered_fcf", DEF_LFCF),
      "Net adjustment from levered free cash flow to unlevered free cash flow": ("lfcf_to_ufcf_adjustment", DEF_ADJ_ORIG)}),
    ("JPROXY_ORIG_20180530", 473, "129", "disney_for_remainco_original", "Disney management", "Guggenheim / J.P. Morgan / Disney board",
     {"Revenue": ("revenue", "Revenue"), "EBITDA": ("ebitda", DEF_EBITDA),
      "Unlevered Free Cash Flow": ("unlevered_fcf", DEF_UFCF_DISNEY)}),
    ("JPROXY_AMENDED_20180628", 616, "172", "21cf_to_advisors_updated", "21CF management", "Goldman Sachs / Centerview / 21CF board",
     {"Revenue": ("revenue", "Revenue"), "EBITDA": ("ebitda", DEF_EBITDA)}),
    ("JPROXY_AMENDED_20180628", 617, "172", "21cf_to_advisors_updated", "21CF management", "Goldman Sachs / Centerview / 21CF board",
     {"Levered Free Cash Flow": ("levered_fcf", DEF_LFCF + " Updated forecasts do NOT reflect the $8.5bn tax payment / dividend (footnote 2)."),
      "Net adjustment from levered free cash flow to unlevered free cash flow used by Goldman Sachs": ("lfcf_to_ufcf_adjustment_goldman", DEF_ADJ_UPD),
      "Net adjustment from levered free cash flow to unlevered free cash flow used by Centerview": ("lfcf_to_ufcf_adjustment_centerview", DEF_ADJ_UPD)}),
    ("JPROXY_AMENDED_20180628", 630, "174", "disney_for_remainco_updated", "Disney management", "Guggenheim / J.P. Morgan / Disney board",
     {"Revenue": ("revenue", "Revenue"), "EBITDA": ("ebitda", DEF_EBITDA),
      "Unlevered Free Cash Flow": ("unlevered_fcf", DEF_UFCF_DISNEY)}),
]
FOOTNOTE_TEXT = {
    ("JPROXY_ORIG_20180530", "levered_fcf", "2018F"): "(2) Assumes payment of the dividend in the amount of $8.5 billion.",
    ("JPROXY_ORIG_20180530", "lfcf_to_ufcf_adjustment", "2018F"):
        "(4) Net adjustments for 2018F adjust for all of the first quarter of fiscal year 2018, such that unlevered free cash flow "
        "reflects only the second through fourth quarters of fiscal year 2018.",
    ("JPROXY_AMENDED_20180628", "levered_fcf", "2018F"):
        "(2) Unlike the original 21CF forecasts, the updated 21CF forecasts do not reflect the tax payment in the amount of $8.5 billion "
        "or the associated dividend in the same amount.",
}
AVAILABLE = {"JPROXY_ORIG_20180530": "2018-05-30", "JPROXY_AMENDED_20180628": "2018-06-28"}

_FOOT = re.compile(r"^\)?\s*\(\s*\d\s*\)$")          # "(2)" or ") (2)"
_NUM = re.compile(r"^\(?\$?\s*-?\d[\d,]*(\.\d+)?\s*\)?$")


class ExtractionError(ValueError):
    pass


def parse_forecast_row(cells, n_periods):
    """Return (values, footnotes): values has exactly n_periods entries (None for N/A)."""
    tokens = []  # (kind, value, raw)
    for c in [c.strip() for c in cells[1:]]:
        if c in ("", "$", "£"):
            continue
        if c.upper() in ("N/A", "NA", "—", "–", "-"):
            tokens.append(("na", None, c))
            continue
        m = re.fullmatch(r"\)\s*(\(\s*\d\s*\))", c)  # closes a previous "(1,234" and carries a footnote
        if m:
            if not tokens or tokens[-1][0] != "open":
                raise ExtractionError(f"dangling ')' in {cells}")
            k, v, raw = tokens[-1]
            tokens[-1] = ("num", -v, raw + ")")
            tokens.append(("foot", None, m.group(1)))
            continue
        if c == ")":
            k, v, raw = tokens[-1]
            tokens[-1] = ("num", -v, raw + ")")
            continue
        if re.fullmatch(r"\(\s*\d\s*\)", c):
            tokens.append(("foot?", -float(re.sub(r"\D", "", c)), c))
            continue
        if re.fullmatch(r"\(\$?\s*\d[\d,]*(\.\d+)?", c):  # open negative, closed by the next cell
            tokens.append(("open", float(re.sub(r"[^\d.]", "", c)), c))
            continue
        if _NUM.fullmatch(c.replace(" ", "")):
            neg = c.startswith("(")
            v = float(re.sub(r"[^\d.]", "", c))
            tokens.append(("num", -v if neg else v, c))
            continue
        if c.endswith("%"):
            continue  # CAGR columns are not periods
        raise ExtractionError(f"unrecognised cell {c!r} in {cells}")
    if any(k == "open" for k, _, _ in tokens):
        raise ExtractionError(f"unclosed negative in {cells}")
    certain = [t for t in tokens if t[0] in ("num", "na")]
    cands = [t for t in tokens if t[0] == "foot?"]
    if len(certain) == n_periods:
        chosen_foot = cands  # all candidates are footnote markers
    elif len(certain) + len(cands) == n_periods:
        chosen_foot = []     # candidates are genuine single-digit negatives
    else:
        raise ExtractionError(f"cannot reconcile {len(certain)} values + {len(cands)} '(n)' cells with {n_periods} periods: {cells}")
    values, footnotes, last_period = [], {}, None
    for t in tokens:
        if t[0] == "foot" or (t[0] == "foot?" and t in chosen_foot):
            footnotes[len(values) - 1] = t[2]
            continue
        values.append(t[1] if t[0] != "na" else None)
    return values, footnotes


def periods_of(table):
    hdr = [c for c in table.rows[1][2] if re.fullmatch(r"20\d\d[AFE]", c.strip())]
    if not hdr:
        raise ExtractionError(f"no period header in {table.doc_id} t{table.index}")
    return [h.strip() for h in hdr]


def text_verify(doc_id, page, label, values):
    """Independent check on the page text: row found on the cited page, values in order with signs."""
    lines = [l for l, p in paged_lines(doc_id) if p == page and l.startswith(label)]
    if not lines:
        return False, "row label not found on page"
    line = re.sub(r"(\d)\s*,\s*(\d)", r"\1,\2", lines[0])  # "18 , 554" -> "18,554" (split HTML spans)
    toks = re.findall(r"\(?\d[\d,]*(?:\.\d+)?", line.split("|", 1)[1] if "|" in line else line)
    toks = [t for t in toks if not re.fullmatch(r"\(\d", t)]  # footnote references like "(2" from "(2)"
    nums = [(-1 if t.startswith("(") else 1) * float(t.strip("(").replace(",", "")) for t in toks]
    want = [v for v in values if v is not None]
    i = 0
    for n in nums:
        if i < len(want) and abs(n - want[i]) < 1e-9:
            i += 1
    return i == len(want), f"{i}/{len(want)} matched in text: {line[:160]}"


def fy_end(period):
    return f"{period[:4]}-06-30"


def build():
    rows, checks = [], []
    for doc_id, tidx, page, fset, provider, recipient, metrics in SPECS:
        t = load_tables(doc_id)[tidx]
        if str(t.page) != page:
            raise ExtractionError(f"{doc_id} t{tidx}: expected page {page}, found {t.page}")
        periods = periods_of(t)
        for label, values, cells in t.rows[2:]:
            key = next((k for k in metrics if cells[0].startswith(k)), None)
            if key is None:
                continue
            # prefer the longest matching prefix (two adjustment rows share a prefix)
            key = max((k for k in metrics if cells[0].startswith(k)), key=len)
            metric, definition = metrics[key]
            vals, foots = parse_forecast_row(cells, len(periods))
            ok, detail = text_verify(doc_id, page, cells[0].split(" (")[0] if "(" in cells[0] else cells[0], vals)
            checks.append({"check_type": "forecast_extraction", "entity": "RemainCo", "source_id": doc_id,
                           "fiscal_period": f"{periods[0]}-{periods[-1]}", "item": f"{fset}:{metric}",
                           "expected": len(periods), "observed": len(vals), "status": "pass" if ok and len(vals) == len(periods) else "fail",
                           "detail": f"table {tidx} p.{page}; {detail}"})
            for j, (per, v) in enumerate(zip(periods, vals)):
                note = FOOTNOTE_TEXT.get((doc_id, metric, per), "")
                if j in foots and not note:
                    note = f"footnote {foots[j]} attached in source"
                rows.append({
                    "proxy": doc_id, "available_date": AVAILABLE[doc_id], "forecast_set": fset, "provider": provider,
                    "provided_to": recipient, "metric": metric, "fiscal_year": per, "fiscal_year_end": fy_end(per),
                    "period_type": {"A": "actual", "F": "forecast (current year)", "E": "estimate (future year)"}[per[-1]],
                    "value": "" if v is None else v, "value_status": "not_available_in_source" if v is None else "reported_forecast",
                    "unit": "USD_m", "source_page": page, "source_table_index": tidx, "row_label_in_source": cells[0],
                    "definition": definition, "footnote": note, "text_verified": ok,
                    "perimeter": ("RemainCo as allocated in the agreed separation principles (includes the RSNs; excludes Sky consolidation)"
                                  if fset.startswith("disney") or "updated" in fset else
                                  "RemainCo excluding Sky (21CF forecast to its advisor; allocation as presented in the proxy)"),
                })
    # derived: 21CF unlevered FCF = levered FCF + net adjustment (original set; updated set per advisor)
    def val(fs, m, per):
        for r in rows:
            if r["forecast_set"] == fs and r["metric"] == m and r["fiscal_year"] == per:
                return r
    for fs, adj_metric, out_metric in (("21cf_to_advisor_original", "lfcf_to_ufcf_adjustment", "unlevered_fcf_derived"),
                                      ("21cf_to_advisors_updated", "lfcf_to_ufcf_adjustment_goldman", "unlevered_fcf_derived_goldman"),
                                      ("21cf_to_advisors_updated", "lfcf_to_ufcf_adjustment_centerview", "unlevered_fcf_derived_centerview")):
        for r in [r for r in rows if r["forecast_set"] == fs and r["metric"] == "levered_fcf"]:
            a = val(fs, adj_metric, r["fiscal_year"])
            if a is None:
                continue
            ok = r["value"] != "" and a["value"] != ""
            base = dict(r)
            base.update({"metric": out_metric, "value": (r["value"] + a["value"]) if ok else "",
                         "value_status": "derived" if ok else "not_available_in_source",
                         "definition": f"levered_fcf + {adj_metric} (derived here; the proxy does not print the sum)",
                         "footnote": ("Unlevered FCF for 2018F covers Q2-Q4 of FY2018 only (footnote 4)."
                                      if fs.endswith("original") and r["fiscal_year"] == "2018F" else ""),
                         "text_verified": ""})
            rows.append(base)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows, checks


def self_test():
    """Unit tests for the footnote-aware parser (run on every build)."""
    v, f = parse_forecast_row(["Levered Free Cash Flow (1)", "(6,664", ") (2)", "2,011", "3,039", "2,891", "3,621"], 5)
    assert v == [-6664, 2011, 3039, 2891, 3621] and f == {0: "(2)"}, (v, f)
    v, f = parse_forecast_row(["Net adjustment (3)", "7,288", "(4)", "(132)", "43", "212", "150"], 5)
    assert v == [7288, -132, 43, 212, 150] and f == {0: "(4)"}, (v, f)
    v, f = parse_forecast_row(["x", "N/A", "(1,048)", "(32)", "(16)", "(30)", "(31)"], 6)
    assert v == [None, -1048, -32, -16, -30, -31], v
    v, f = parse_forecast_row(["x", "10", "(4)", "12"], 3)  # (4) must be a value here: -4
    assert v == [10, -4, 12], v
    try:
        parse_forecast_row(["x", "1", "2"], 3)
        raise AssertionError("should have failed")
    except ExtractionError:
        pass
    return True


if __name__ == "__main__":
    self_test()
    rows, checks = build()
    print(len(rows), "forecast rows;", sum(c["status"] != "pass" for c in checks), "failed checks")
