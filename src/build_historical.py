"""Build ``data/processed/historical_financials.csv`` from the downloaded SEC filings.

What it does
------------
1. Takes the pinned statement tables (income statement, balance sheet, cash flow,
   segment note) from each 10-K, plus the RemainCo pro forma tables from the
   2018 joint proxy and the March 2019 Form 8-K/A, and writes every row as it is
   presented in the source (label, sign and period unchanged).
2. Adds a standardized ``line_item`` code to the key rows so the companies can be
   compared.
3. Labels each value with its ``basis`` (as originally reported, a comparative
   presented in a later filing, or pro forma) and marks one value per
   entity/period/line item as ``is_primary``.
4. Adds a small set of derived figures (total borrowings, net debt, simple FCF),
   with the formula stated.
5. Runs arithmetic tie-outs and an independent cross-check against the SEC XBRL
   company-facts data, written to ``data/processed/verification_checks.csv``.

Sign convention: values keep the sign shown in the filing. Expenses and cash
outflows shown in parentheses are negative.
Units: USD millions, except per-share rows (USD per share) and share counts
(millions of shares). See the ``unit`` column.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sec_tables import load_tables  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "historical_financials.csv"
CHECKS = ROOT / "data" / "processed" / "verification_checks.csv"
XBRL_DIR = ROOT / "data" / "raw" / "xbrl"

# --------------------------------------------------------------------------------------
# Fiscal periods (from the filings: Disney FY ends on the Saturday closest to Sept 30;
# 21CF FY ends June 30). Disney FY2015 was a 53-week year (FY2015 10-K, Note 1).
# --------------------------------------------------------------------------------------
PERIODS = {
    "DIS": {
        "FY2013": ("2012-09-30", "2013-09-28", "52 weeks"),
        "FY2014": ("2013-09-29", "2014-09-27", "52 weeks"),
        "FY2015": ("2014-09-28", "2015-10-03", "53 weeks"),
        "FY2016": ("2015-10-04", "2016-10-01", "52 weeks"),
        "FY2017": ("2016-10-02", "2017-09-30", "52 weeks"),
        "FY2018": ("2017-10-01", "2018-09-29", "52 weeks"),
    },
    "21CF": {
        "FY2013": ("2012-07-01", "2013-06-30", "12 months"),
        "FY2014": ("2013-07-01", "2014-06-30", "12 months"),
        "FY2015": ("2014-07-01", "2015-06-30", "12 months"),
        "FY2016": ("2015-07-01", "2016-06-30", "12 months"),
        "FY2017": ("2016-07-01", "2017-06-30", "12 months"),
        "FY2018": ("2017-07-01", "2018-06-30", "12 months"),
        "6M_DEC2017": ("2017-07-01", "2017-12-31", "6 months"),
        "Q1_FY2019": ("2018-07-01", "2018-09-30", "3 months"),
    },
}
INSTANTS = {  # balance-sheet dates
    ("DIS", "FY2014"): "2014-09-27", ("DIS", "FY2015"): "2015-10-03", ("DIS", "FY2016"): "2016-10-01",
    ("DIS", "FY2017"): "2017-09-30", ("DIS", "FY2018"): "2018-09-29",
    ("21CF", "FY2014"): "2014-06-30", ("21CF", "FY2015"): "2015-06-30", ("21CF", "FY2016"): "2016-06-30",
    ("21CF", "FY2017"): "2017-06-30", ("21CF", "FY2018"): "2018-06-30",
    ("21CF", "MAR2018"): "2018-03-31", ("21CF", "DEC2018"): "2018-12-31",
}

# The most recent 10-K filed before the 14 Dec 2017 announcement is the primary basis
# for FY2015-FY2017; FY2018 values come from the FY2018 10-K (supplementary year).
PRIMARY_DOC = {
    ("DIS", "FY2015"): "DIS_10K_FY2017", ("DIS", "FY2016"): "DIS_10K_FY2017",
    ("DIS", "FY2017"): "DIS_10K_FY2017", ("DIS", "FY2018"): "DIS_10K_FY2018",
    ("21CF", "FY2015"): "FOX_10K_FY2017", ("21CF", "FY2016"): "FOX_10K_FY2017",
    ("21CF", "FY2017"): "FOX_10K_FY2017", ("21CF", "FY2018"): "FOX_10K_FY2018",
}
# The FY2017 10-K balance sheets only show FY2017 and FY2016, so the FY2015 balance
# sheet comes from the FY2016 10-K comparative column.
PRIMARY_DOC_BS = {("DIS", "FY2015"): "DIS_10K_FY2016", ("21CF", "FY2015"): "FOX_10K_FY2016"}

DOC_FY = {  # fiscal year each annual report covers
    "DIS_10K_FY2015": "FY2015", "DIS_10K_FY2016": "FY2016", "DIS_10K_FY2017": "FY2017",
    "DIS_10K_FY2018": "FY2018", "FOX_10K_FY2015": "FY2015", "FOX_10K_FY2016": "FY2016",
    "FOX_10K_FY2017": "FY2017", "FOX_10K_FY2018": "FY2018",
}

# --------------------------------------------------------------------------------------
# Pinned tables: (doc_id, statement, table index, expected printed page, column periods)
# Table indexes refer to the order of <table> elements in the downloaded HTML (sha256 in
# data/raw/download_manifest.csv). The expected page is checked when the script runs.
# --------------------------------------------------------------------------------------
TEN_K_TABLES = [
    # Disney
    ("DIS_10K_FY2015", "income_statement", 151, "63", ["FY2015", "FY2014", "FY2013"]),
    ("DIS_10K_FY2015", "balance_sheet", 153, "65", ["FY2015", "FY2014"]),
    ("DIS_10K_FY2015", "cash_flow", 154, "66", ["FY2015", "FY2014", "FY2013"]),
    ("DIS_10K_FY2015", "segment", 158, "70", ["FY2015", "FY2014", "FY2013"]),
    ("DIS_10K_FY2015", "segment", 159, "71", ["FY2015", "FY2014", "FY2013"]),
    ("DIS_10K_FY2016", "income_statement", 161, "61", ["FY2016", "FY2015", "FY2014"]),
    ("DIS_10K_FY2016", "balance_sheet", 163, "63", ["FY2016", "FY2015"]),
    ("DIS_10K_FY2016", "cash_flow", 164, "64", ["FY2016", "FY2015", "FY2014"]),
    ("DIS_10K_FY2016", "segment", 168, "68", ["FY2016", "FY2015", "FY2014"]),
    ("DIS_10K_FY2016", "segment", 169, "69", ["FY2016", "FY2015", "FY2014"]),
    ("DIS_10K_FY2017", "income_statement", 151, "58", ["FY2017", "FY2016", "FY2015"]),
    ("DIS_10K_FY2017", "balance_sheet", 153, "60", ["FY2017", "FY2016"]),
    ("DIS_10K_FY2017", "cash_flow", 154, "61", ["FY2017", "FY2016", "FY2015"]),
    ("DIS_10K_FY2017", "segment", 158, "65", ["FY2017", "FY2016", "FY2015"]),
    ("DIS_10K_FY2017", "segment", 159, "66", ["FY2017", "FY2016", "FY2015"]),
    ("DIS_10K_FY2018", "income_statement", 170, "62", ["FY2018", "FY2017", "FY2016"]),
    ("DIS_10K_FY2018", "balance_sheet", 172, "64", ["FY2018", "FY2017"]),
    ("DIS_10K_FY2018", "cash_flow", 173, "65", ["FY2018", "FY2017", "FY2016"]),
    ("DIS_10K_FY2018", "segment", 177, "69", ["FY2018", "FY2017", "FY2016"]),
    ("DIS_10K_FY2018", "segment", 178, "70", ["FY2018", "FY2017", "FY2016"]),
    # 21st Century Fox
    ("FOX_10K_FY2015", "income_statement", 97, "71", ["FY2015", "FY2014", "FY2013"]),
    ("FOX_10K_FY2015", "balance_sheet", 100, "73", ["FY2015", "FY2014"]),
    ("FOX_10K_FY2015", "cash_flow", 103, "74", ["FY2015", "FY2014", "FY2013"]),
    ("FOX_10K_FY2015", "segment", 211, "129", ["FY2015", "FY2014", "FY2013"]),
    ("FOX_10K_FY2016", "income_statement", 98, "67", ["FY2016", "FY2015", "FY2014"]),
    ("FOX_10K_FY2016", "balance_sheet", 101, "69", ["FY2016", "FY2015"]),
    ("FOX_10K_FY2016", "cash_flow", 104, "70", ["FY2016", "FY2015", "FY2014"]),
    ("FOX_10K_FY2016", "segment", 203, "120", ["FY2016", "FY2015", "FY2014"]),
    ("FOX_10K_FY2017", "income_statement", 101, "68", ["FY2017", "FY2016", "FY2015"]),
    ("FOX_10K_FY2017", "balance_sheet", 104, "70", ["FY2017", "FY2016"]),
    ("FOX_10K_FY2017", "cash_flow", 107, "71", ["FY2017", "FY2016", "FY2015"]),
    ("FOX_10K_FY2017", "segment", 207, "120", ["FY2017", "FY2016", "FY2015"]),
    ("FOX_10K_FY2018", "income_statement", 109, "79", ["FY2018", "FY2017", "FY2016"]),
    ("FOX_10K_FY2018", "balance_sheet", 112, "81", ["FY2018", "FY2017"]),
    ("FOX_10K_FY2018", "cash_flow", 115, "82", ["FY2018", "FY2017", "FY2016"]),
    ("FOX_10K_FY2018", "segment", 216, "135", ["FY2018", "FY2017", "FY2016"]),
]

# RemainCo pro forma tables. Columns are perimeters, not periods. Only the columns on
# the path from 21CF historical to RemainCo are kept. The proxy's hypothetical
# "consolidation of Sky" columns are left out because that acquisition never happened
# (21CF's 39% Sky stake was sold to Comcast in October 2018).
PF_TABLES = [
    # 2018 joint proxy statement/prospectus (amended deal), RemainCo pro forma financials
    ("JPROXY_AMENDED_20180628", "income_statement", 1114, "285", "6M_DEC2017",
     ["21CF historical", "New Fox (ASC 205 basis)", "Pro forma adjustments", "RemainCo (excl. Sky consolidation)"]),
    ("JPROXY_AMENDED_20180628", "income_statement", 1115, "286", "FY2017",
     ["21CF historical", "New Fox (ASC 205 basis)", "Pro forma adjustments", "RemainCo (excl. Sky consolidation)"]),
    ("JPROXY_AMENDED_20180628", "income_statement", 1116, "287", "FY2016",
     ["21CF historical", "New Fox (ASC 205 basis)", "Pro forma adjustments", "RemainCo (excl. Sky consolidation)"]),
    ("JPROXY_AMENDED_20180628", "income_statement", 1117, "288", "FY2015",
     ["21CF historical", "New Fox (ASC 205 basis)", "Pro forma adjustments", "RemainCo (excl. Sky consolidation)"]),
    ("JPROXY_AMENDED_20180628", "balance_sheet", 1118, "289", "MAR2018",
     ["21CF historical", "New Fox (ASC 205 basis)", "Pro forma adjustments", "RemainCo (excl. Sky consolidation)"]),
    # Form 8-K/A (27 Mar 2019) Ex. 99.4: closing perimeter (FOX spun off, 39% Sky stake sold)
    ("DIS_8KA_20190327_EX99_4", "income_statement", 5, "3", "Q1_FY2019",
     ["21CF historical", "FOX (ASC 205 basis)", "Pro forma adjustments", "Disposition of Sky", "RemainCo (closing perimeter)"]),
    ("DIS_8KA_20190327_EX99_4", "income_statement", 6, "4", "FY2018",
     ["21CF historical", "FOX (ASC 205 basis)", "Pro forma adjustments", "Disposition of Sky", "RemainCo (closing perimeter)"]),
    ("DIS_8KA_20190327_EX99_4", "income_statement", 7, "5", "FY2017",
     ["21CF historical", "FOX (ASC 205 basis)", "Pro forma adjustments", "RemainCo (closing perimeter)"]),
    ("DIS_8KA_20190327_EX99_4", "income_statement", 8, "6", "FY2016",
     ["21CF historical", "FOX (ASC 205 basis)", "Pro forma adjustments", "RemainCo (closing perimeter)"]),
    ("DIS_8KA_20190327_EX99_4", "balance_sheet", 9, "7", "DEC2018",
     ["21CF historical", "FOX (ASC 205 basis)", "Pro forma adjustments", "RemainCo (closing perimeter)"]),
]
# Which columns to keep from each pro forma table, and how many numeric values a full
# row has (rows with fewer values are EPS/share rows or stacked adjustment detail).
PF_KEEP_COLS = {
    "JPROXY_AMENDED_20180628": ([0, 1, 2, 3], {"6M_DEC2017": 9, "FY2017": 9, "MAR2018": 9, "FY2016": 4, "FY2015": 4}),
    "DIS_8KA_20190327_EX99_4": (None, {"Q1_FY2019": 5, "FY2018": 5, "FY2017": 4, "FY2016": 4, "DEC2018": 4}),
    "DIS_8KA_20190327_EX99_3": ([3], {"FY2018": 5, "Q1_FY2019": 5}),
}
# New Disney pro forma (8-K/A Ex. 99.3): only the "Divestiture of RSN" column is kept.
# It is a bridge item. Per note (h) it removes RSN revenues and expenses and also the
# pro forma amortization of RSN fair-value intangibles, so only the revenue line shows
# RSN historical activity cleanly. Disney's line-item classification is used.
PF_TABLES += [
    ("DIS_8KA_20190327_EX99_3", "income_statement", 6, "5", "FY2018",
     ["Disney historical", "RemainCo", "Pro forma adjustments", "Divestiture of RSNs (Disney pro forma bridge)", "Combined"]),
    ("DIS_8KA_20190327_EX99_3", "income_statement", 7, "6", "Q1_FY2019",
     ["Disney historical", "RemainCo", "Pro forma adjustments", "Divestiture of RSNs (Disney pro forma bridge)", "Combined"]),
]

PF_NOTES = {
    "DIS_8KA_20190327_EX99_3": "RSN divestiture column of the New Disney pro forma (Disney line-item classification). "
                               "Per note (h) it also reverses pro forma amortization of RSN fair-value intangibles, "
                               "so only revenue is a clean RSN historical figure.",
}

ENTITY_NAME = {"DIS": "The Walt Disney Company (legacy Disney; CIK 1001039)",
               "21CF": "Twenty-First Century Fox, Inc. (CIK 1308161)"}

# --------------------------------------------------------------------------------------
# Standardized line-item mapping: (statement, section regex or None, label regex) -> code
# --------------------------------------------------------------------------------------
STD_MAP = [
    # income statement
    ("income_statement", None, r"^(total revenues|revenues)$", "revenue"),
    ("income_statement", None, r"^services$", "revenue_services"),
    ("income_statement", None, r"^products$", "revenue_products"),
    ("income_statement", None, r"^cost of services", "cost_of_services"),
    ("income_statement", None, r"^cost of products", "cost_of_products"),
    ("income_statement", None, r"^operating expenses$", "operating_expenses"),
    ("income_statement", None, r"^selling, general", "sga"),
    ("income_statement", None, r"^depreciation and amortization$", "depreciation_amortization"),
    ("income_statement", None, r"^total costs and expenses$", "total_costs_and_expenses"),
    ("income_statement", None, r"^(restructuring and impairment charges|impairment and restructuring charges)$", "restructuring_impairment"),
    ("income_statement", None, r"^restructuring and impairment and other$", "restructuring_impairment_and_other"),
    ("income_statement", None, r"^(other income, net|other income \(expense\), net|other, net|other expense, net)$", "other_income_expense_net"),
    ("income_statement", None, r"^(interest expense, net|interest income/\(expense\), net|interest \(expense\)/income, net)$", "interest_expense_net"),
    ("income_statement", None, r"^interest income$", "interest_income"),
    ("income_statement", None, r"^equity (in the income of investees|in the income \(loss\) of investees|\(losses\) earnings of affiliates|earnings \(losses\) of affiliates|earnings of affiliates|losses of affiliates)", "equity_income_affiliates"),
    ("income_statement", None, r"^income (\(loss\) )?(from continuing operations )?before income tax", "pretax_income_continuing"),
    ("income_statement", None, r"^(income taxes|income tax expense|income tax \(expense\) benefit|income tax benefit \(expense\)|income taxes on income from continuing operations)$", "income_tax"),
    ("income_statement", None, r"^income (\(loss\) )?from continuing operations$", "income_continuing_ops"),
    ("income_statement", None, r"discontinued operations, net of tax$", "discontinued_ops_net"),
    ("income_statement", None, r"^net income$", "net_income"),
    ("income_statement", None, r"^less: (net )?(\(net income\) loss|net income|\(income\) loss) attributable to noncontrolling", "net_income_nci"),
    ("income_statement", None, r"^net income attributable to (the walt disney company|twenty-first century fox, inc\. stockholders|twenty-first century fox stockholders)(?!.*per share)", "net_income_attributable_parent"),
    ("income_statement", r"earnings per share", r"^diluted$", "eps_diluted"),
    ("income_statement", r"earnings per share", r"^basic$", "eps_basic"),
    ("income_statement", None, r"^net income attributable to twenty-first century fox, inc\. stockholders per share - diluted$", "eps_diluted"),
    ("income_statement", None, r"^net income attributable to twenty-first century fox, inc\. stockholders per share - basic$", "eps_basic"),
    ("income_statement", r"weighted average", r"^diluted$", "shares_diluted"),
    ("income_statement", r"weighted average", r"^basic$", "shares_basic"),
    ("income_statement", None, r"^income \(loss\) from continuing operations attributable to 21cf stockholders$", "income_continuing_ops_attributable_parent"),
    # balance sheet
    ("balance_sheet", None, r"^cash and cash equivalents$", "cash"),
    ("balance_sheet", r"^current assets", r"^receivables", "receivables_current"),
    ("balance_sheet", r"^current assets", r"^inventories", "inventories_current"),
    ("balance_sheet", r"^current assets", r"^television costs and advances", "tv_costs_advances_current"),
    ("balance_sheet", None, r"^total current assets$", "total_current_assets"),
    ("balance_sheet", r"^non-current assets", r"^inventories", "film_tv_inventories_noncurrent"),
    ("balance_sheet", r"^non-current assets", r"^film and television costs", "film_tv_inventories_noncurrent"),
    ("balance_sheet", r"^non-current assets", r"^receivables", "receivables_noncurrent"),
    ("balance_sheet", r"^non-current assets", r"^investments$", "investments"),
    ("balance_sheet", r"^non-current assets", r"^property, plant and equipment, net$", "ppe_net"),
    ("balance_sheet", r"^non-current assets", r"^\[unlabelled subtotal after: land\]$", "ppe_net"),
    ("balance_sheet", None, r"^intangible assets, net$", "intangible_assets_net"),
    ("balance_sheet", None, r"^goodwill$", "goodwill"),
    ("balance_sheet", None, r"^total assets$", "total_assets"),
    ("balance_sheet", r"^current liabilities", r"^(borrowings|current portion of borrowings)$", "borrowings_current"),
    ("balance_sheet", None, r"^total current liabilities$", "total_current_liabilities"),
    ("balance_sheet", r"^non-current liabilities", r"^borrowings$", "borrowings_noncurrent"),
    ("balance_sheet", r"^non-current liabilities", r"^deferred income taxes$", "deferred_income_taxes_liability"),
    ("balance_sheet", None, r"^redeemable noncontrolling interests$", "redeemable_nci"),
    ("balance_sheet", None, r"^total (disney shareholders.? equity|twenty-first century fox, inc\. stockholders.? equity)$", "equity_attributable_parent"),
    ("balance_sheet", r"^equity", r"^noncontrolling interests$", "nci_equity"),
    ("balance_sheet", None, r"^total equity$", "total_equity"),
    ("balance_sheet", None, r"^total liabilities and equity$", "total_liabilities_and_equity"),
    # cash flow
    ("cash_flow", r"^operating", r"^net income$", "cf_net_income"),
    ("cash_flow", r"^(operating|adjustments to reconcile)", r"^depreciation and amortization$", "cf_depreciation_amortization"),
    ("cash_flow", None, r"^(cash provided by operations|cash provided by operations - continuing operations|net cash provided by operating activities from continuing operations|net cash provided by operating activities)$", "cfo"),
    ("cash_flow", r"^investing", r"^(investments in parks, resorts and other property|property, plant and equipment)$", "capex"),
    ("cash_flow", r"^investing", r"^acquisitions", "acquisitions"),
    ("cash_flow", None, r"^(cash used in investing activities|cash used in investing activities - continuing operations|net cash \(used in\) provided by investing activities from continuing operations|net cash used in investing activities from continuing operations|net cash provided by \(used in\) investing activities from continuing operations)$", "cfi"),
    ("cash_flow", r"^financing", r"^(dividends|dividends paid and distributions)$", "dividends_paid"),
    ("cash_flow", r"^financing", r"^(repurchases of common stock|repurchase of shares)$", "share_repurchases"),
    ("cash_flow", r"^financing", r"^borrowings$", "debt_proceeds"),
    ("cash_flow", r"^financing", r"^(reduction of borrowings|repayment of borrowings)$", "debt_repayments"),
    ("cash_flow", r"^financing", r"^commercial paper", "commercial_paper_net"),
    ("cash_flow", None, r"^(cash used in financing activities|cash used in financing activities - continuing operations|net cash used in financing activities from continuing operations|net cash \(used in\) provided by financing activities from continuing operations|net cash provided by \(used in\) financing activities from continuing operations)$", "cff"),
    ("cash_flow", None, r"^interest paid$", "interest_paid"),
    ("cash_flow", None, r"^income taxes paid$", "income_taxes_paid"),
]

SECTION_HEADERS = {
    "balance_sheet": [r"^assets$", r"^current assets$", r"^non-current assets$", r"^liabilities and equity$",
                      r"^current liabilities$", r"^non-current liabilities$", r"^equity$"],
    "cash_flow": [r"^operating activit", r"^investing activities$", r"^financing activities$",
                  r"^changes in operating assets", r"^change in operating assets", r"^discontinued operations$",
                  r"^supplemental disclosure", r"^adjustments to reconcile"],
    "income_statement": [r"^revenues:?$", r"^costs and expenses:?$", r"^earnings per share", r"^weighted average",
                         r"^earnings per share data$"],
}
SEGMENT_SECTIONS = [r"^revenues:?$", r"^segment operating income:?$", r"^segment oibda:?$",
                    r"^reconciliation of segment operating income", r"^capital expenditures:?$",
                    r"^depreciation expense:?$", r"^amortization of intangible assets:?$",
                    r"^identifiable assets", r"^supplemental revenue data$", r"^equity in the income of investees"]


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def unit_for(label: str, section: str) -> str:
    l, s = label.lower(), section.lower()
    if "per share" in l or "dividends declared" in l or ("per share" in s and l in ("diluted", "basic", "basic and diluted")):
        return "USD_per_share"
    if "earnings per share" in s and l in ("diluted", "basic", "basic and diluted"):
        return "USD_per_share"
    if "weighted average" in s or "weighted average" in l:
        return "shares_m"
    return "USD_m"


def std_code(statement: str, section: str, label: str):
    l, s = label.lower().strip().rstrip(":"), section.lower()
    for st, sec_re, lab_re, code in STD_MAP:
        if st != statement:
            continue
        if sec_re and not re.search(sec_re, s):
            continue
        if re.search(lab_re, l):
            return code
    return ""


def walk_rows(statement: str, rows):
    """Yield (section, label, values) with section context and labels for blank subtotal rows."""
    section, prev_label = "", ""
    headers = SECTION_HEADERS.get(statement, [])
    for i, (label, values, _) in enumerate(rows):
        lab = label.strip()
        low = lab.lower().rstrip(":")
        if i < 3 and not lab and values and all(v is not None and v == int(v) and 1990 <= v <= 2030 for v in values):
            continue  # column-header row of fiscal years
        if not values or all(v is None for v in values):
            if any(re.search(h, low) for h in headers):
                section = lab.rstrip(":")
            elif statement == "income_statement" and low.startswith("earnings per share"):
                section = lab.rstrip(":")
            prev_label = lab or prev_label
            continue
        if statement == "balance_sheet":
            if low == "total current assets":
                yield section, lab, values
                section = "Non-current assets"
                prev_label = lab
                continue
            if low == "total current liabilities":
                yield section, lab, values
                section = "Non-current liabilities"
                prev_label = lab
                continue
        if not lab:
            lab = f"[unlabelled subtotal after: {prev_label}]"
        yield section, lab, values
        if statement == "income_statement" and low == "total costs and expenses":
            section = ""
        if not lab.startswith("[unlabelled"):
            prev_label = lab


def walk_segment_rows(rows):
    """Segment tables: track section (Revenues / Segment operating income / ...) and sub-groups."""
    section, group, seen = "", "", defaultdict(int)
    after_total_oibda = False
    for i, (label, values, _) in enumerate(rows):
        lab = label.strip()
        low = lab.lower().rstrip(":")
        if i < 3 and not lab and values and all(v is not None and v == int(v) and 1990 <= v <= 2030 for v in values):
            continue  # column-header row of fiscal years
        has_vals = values and any(v is not None for v in values)
        if not has_vals:
            if any(re.search(p, low) for p in SEGMENT_SECTIONS):
                seen[low] += 1
                if low.startswith(("supplemental revenue data", "identifiable assets")):
                    seen["_geo"] = 1  # Disney: Revenues / Segment operating income after these blocks are by geography
                is_geo = low.startswith(("revenues", "segment operating income")) and (seen[low] > 1 or seen["_geo"])
                section = lab.rstrip(":") + (" (geographic)" if is_geo else "")
                group = ""
            elif lab:
                group = lab
            continue
        if after_total_oibda:
            sec = "Reconciliation of Segment OIBDA to income"
        else:
            sec = section
        if not lab:
            name = f"{group} - total" if group else f"{sec} - total"
            group = ""
        elif group and lab.lower() in ("third parties", "intersegment", "domestic", "international",
                                        "cable networks", "broadcasting"):
            name = f"{group} - {lab}"
        else:
            if group and lab.lower() not in ("third parties", "intersegment"):
                group = ""
            name = lab
        yield sec, name, values
        if low.startswith("total segment oibda"):
            after_total_oibda = True


SEGMENT_CODES = [
    (r"^revenues \(geographic\)", "geographic_revenue"),
    (r"^revenues", "segment_revenue"),
    (r"^segment operating income \(geographic\)", "geographic_segment_operating_income"),
    (r"^segment operating income", "segment_operating_income"),
    (r"^segment oibda", "segment_oibda"),
    (r"^reconciliation", "segment_reconciliation_item"),
    (r"^capital expenditures", "segment_capex"),
    (r"^depreciation expense", "segment_depreciation"),
    (r"^amortization of intangible assets", "segment_amortization_intangibles"),
    (r"^identifiable assets", "segment_identifiable_assets"),
    (r"^supplemental revenue data", "supplemental_revenue"),
]


def segment_code(section: str) -> str:
    low = section.lower()
    for pat, code in SEGMENT_CODES:
        if re.search(pat, low):
            return code
    return "segment_other"


def segment_name(label: str) -> str:
    """Segment label with footnote markers like (a) or (3) removed."""
    return re.sub(r"\s*\((?:[a-z]|\d{1,2})\)\s*", " ", label).strip()


def check_page(t, expected, doc_id):
    if str(t.page) != str(expected):
        raise AssertionError(f"{doc_id} table {t.index}: expected page {expected}, parser found {t.page}")


def basis_for(doc_id: str, period: str) -> str:
    return "as_originally_reported" if DOC_FY.get(doc_id) == period else "comparative_in_later_filing"


def build_rows():
    out = []
    table_cache = {}

    def tables(doc_id):
        if doc_id not in table_cache:
            table_cache[doc_id] = load_tables(doc_id)
        return table_cache[doc_id]

    # ---- 10-K statements
    for doc_id, statement, idx, page, cols in TEN_K_TABLES:
        entity = "DIS" if doc_id.startswith("DIS") else "21CF"
        t = tables(doc_id)[idx]
        check_page(t, page, doc_id)
        walker = walk_segment_rows(t.rows) if statement == "segment" else walk_rows(statement, t.rows)
        for section, label, values in walker:
            vals = values[:len(cols)]
            for period, v in zip(cols, vals):
                if v is None:
                    continue
                if statement == "balance_sheet":
                    end = INSTANTS[(entity, period)]
                    start, length = "", "instant"
                elif statement == "segment" and section.lower().startswith("identifiable assets"):
                    end = INSTANTS.get((entity, period), PERIODS[entity][period][1])
                    start, length = "", "instant"
                else:
                    start, end, length = PERIODS[entity][period]
                code = std_code(statement, section, label) if statement != "segment" else segment_code(section)
                seg_name = segment_name(label) if statement == "segment" else ""
                out.append({
                    "entity": entity, "entity_name": ENTITY_NAME[entity],
                    "perimeter": "Disney consolidated" if entity == "DIS" else "21CF consolidated (pre-separation, incl. New Fox businesses)",
                    "statement": statement, "section": section,
                    "line_item": code, "line_item_reported": label, "segment": seg_name,
                    "fiscal_period": period, "period_start": start, "period_end": end, "period_length": length,
                    "value": v, "unit": unit_for(label, section) if statement != "segment" else "USD_m",
                    "data_type": "reported", "basis": basis_for(doc_id, period),
                    "source_id": doc_id, "source_table_index": idx, "source_page": page,
                })

    # ---- pro forma RemainCo
    for doc_id, statement, idx, page, period, colnames in PF_TABLES:
        t = tables(doc_id)[idx]
        check_page(t, page, doc_id)
        keep, full_len = PF_KEEP_COLS[doc_id]
        keep = keep or list(range(len(colnames)))
        for section, label, values in walk_rows(statement, t.rows):
            # EPS / share rows and stacked adjustment detail have fewer values: skip them
            if len(values) != full_len[period]:
                continue
            for ci in keep:
                v = values[ci]
                col = colnames[ci]
                if statement == "balance_sheet":
                    start, end, length = "", INSTANTS[("21CF", period)], "instant"
                else:
                    start, end, length = PERIODS["21CF"][period]
                if col == "21CF historical":
                    ent, dtype = "21CF", "reported_in_pro_forma_presentation"
                elif col.startswith("RemainCo"):
                    ent, dtype = "RemainCo", "pro_forma"
                else:
                    ent, dtype = "RemainCo_bridge", "pro_forma_adjustment"
                out.append({
                    "entity": ent,
                    "entity_name": "21CF after separation of New Fox/FOX ('RemainCo', the business acquired by Disney)" if ent != "21CF" else ENTITY_NAME["21CF"],
                    "perimeter": col, "statement": statement, "section": section,
                    "line_item": std_code(statement, section, label), "line_item_reported": label,
                    "fiscal_period": period, "period_start": start, "period_end": end, "period_length": length,
                    "value": v, "unit": unit_for(label, section), "data_type": dtype,
                    "basis": "pro_forma_2018_joint_proxy" if doc_id.startswith("JPROXY") else "pro_forma_8KA_closing_perimeter",
                    "notes": PF_NOTES.get(doc_id, ""),
                    "source_id": doc_id, "source_table_index": idx, "source_page": page,
                })
    return out


def mark_primary(rows):
    """One primary value per (entity, perimeter, statement, line_item_reported/section, period)."""
    for r in rows:
        r["is_primary"] = False
        if r["data_type"] == "reported":
            key = (r["entity"], r["fiscal_period"])
            want = PRIMARY_DOC.get(key)
            if r["statement"] == "balance_sheet" and key in PRIMARY_DOC_BS:
                want = PRIMARY_DOC_BS[key]
            if r["statement"] == "segment" and r["section"].lower().startswith("identifiable assets") and key in PRIMARY_DOC_BS:
                want = PRIMARY_DOC_BS[key]
            r["is_primary"] = (r["source_id"] == want)
        elif r["data_type"] == "pro_forma":
            # The closing-perimeter (8-K/A) RemainCo figures are primary where available
            # (FY2016-FY2018, Q1 FY2019, Dec 2018). The 2018 proxy RemainCo figures are
            # primary only for periods the 8-K/A does not cover (FY2015, 6M Dec 2017, Mar 2018).
            if r["source_id"] == "DIS_8KA_20190327_EX99_4":
                r["is_primary"] = True
            else:
                r["is_primary"] = r["fiscal_period"] in ("FY2015", "6M_DEC2017", "MAR2018")
    return rows


def add_derived(rows):
    """Derived figures from primary reported/pro forma values. Formula in 'notes'."""
    idx = defaultdict(dict)
    for r in rows:
        if r["is_primary"] and r["line_item"]:
            idx[(r["entity"], r["perimeter"], r["fiscal_period"], r["statement"])][r["line_item"]] = r
    derived = []

    def mk(base, code, value, formula, statement=None):
        d = dict(base)
        d.update({"statement": statement or base["statement"], "section": "derived", "line_item": code,
                  "line_item_reported": "", "value": round(value, 3), "unit": "USD_m", "data_type": "derived",
                  "notes": formula, "is_primary": True})
        derived.append(d)

    for (ent, per, fp, st), items in idx.items():
        if st == "balance_sheet" and "cash" in items and "borrowings_noncurrent" in items:
            cur = items.get("borrowings_current")
            tb = items["borrowings_noncurrent"]["value"] + (cur["value"] if cur else 0.0)
            base = items["cash"]
            mk(base, "total_borrowings", tb, "borrowings_current + borrowings_noncurrent (carrying amounts as presented on the balance sheet)")
            mk(base, "net_debt", tb - base["value"], "total_borrowings - cash (cash and cash equivalents only; excludes investments, leases, pensions and NCI)")
        if st == "cash_flow" and "cfo" in items and "capex" in items:
            base = items["cfo"]
            mk(base, "fcf_cfo_less_capex", items["cfo"]["value"] + items["capex"]["value"],
               "cfo + capex (capex is negative as presented); not a company-defined measure")
    return derived


# --------------------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------------------
XBRL_FILES = {"DIS": "companyfacts_CIK0001001039_TWDC_Enterprises_18_old_Disney.json",
              "21CF": "companyfacts_CIK0001308161_Twenty_First_Century_Fox.json"}
ACCESSION = {}
with (ROOT / "data" / "reference" / "filings_to_fetch.csv").open(encoding="utf-8") as fh:
    for f in csv.DictReader(fh):
        ACCESSION[f["doc_id"]] = f["accession"]

XBRL_MAP = {
    "revenue": ["Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "net_income": ["ProfitLoss", "NetIncomeLossIncludingPortionAttributableToNonredeemableNoncontrollingInterest"],
    "net_income_attributable_parent": ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "pretax_income_continuing": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                                 "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "income_tax": ["IncomeTaxExpenseBenefit"],
    "depreciation_amortization": ["DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "CostOfServicesDepreciationAndAmortization"],
    "total_assets": ["Assets"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue"],
    "goodwill": ["Goodwill"],
    "total_equity": ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "equity_attributable_parent": ["StockholdersEquity"],
    "total_current_assets": ["AssetsCurrent"],
    "total_current_liabilities": ["LiabilitiesCurrent"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "cfi": ["NetCashProvidedByUsedInInvestingActivities", "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations"],
    "cff": ["NetCashProvidedByUsedInFinancingActivities", "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations"],
    "capex": ["PaymentsToAcquirePropertyPlantAndEquipment"],
    "eps_diluted": ["EarningsPerShareDiluted"],
}


def load_xbrl(entity):
    data = json.loads((XBRL_DIR / XBRL_FILES[entity]).read_text(encoding="utf-8"))
    facts = defaultdict(list)  # (concept, accession) -> list of facts
    for tax in ("us-gaap",):
        for concept, body in data["facts"].get(tax, {}).items():
            for unit, arr in body["units"].items():
                for f in arr:
                    facts[(concept, f["accn"])].append((unit, f))
    return facts


def xbrl_check(rows):
    results = []
    facts = {e: load_xbrl(e) for e in XBRL_FILES}
    for r in rows:
        if r["data_type"] != "reported" or r["line_item"] not in XBRL_MAP:
            continue
        acc = ACCESSION[r["source_id"]]
        status, found = "no_xbrl_fact_for_period", ""
        for concept in XBRL_MAP[r["line_item"]]:
            for unit, f in facts[r["entity"]].get((concept, acc), []):
                if f["end"] != r["period_end"]:
                    continue
                if r["period_start"] and f.get("start") and f["start"] != r["period_start"]:
                    continue
                scale = 1.0 if unit.endswith("/shares") else 1e6
                xv = f["val"] / scale
                found = f"{concept}={xv:g}"
                status = "match" if abs(abs(xv) - abs(r["value"])) < 0.6 or (unit.endswith("/shares") and abs(abs(xv) - abs(r["value"])) < 0.006) else "mismatch"
                if status == "match":
                    break
            if status == "match":
                break
        r["xbrl_check"] = status
        r["xbrl_fact"] = found
        results.append({"check_type": "xbrl_cross_check", "entity": r["entity"], "source_id": r["source_id"],
                        "fiscal_period": r["fiscal_period"], "item": r["line_item"],
                        "expected": r["value"], "observed": found, "status": status,
                        "detail": f"XBRL company facts, accession {acc}"})
    return results


def arithmetic_checks(rows):
    """Tie-outs within each source table/period."""
    by = defaultdict(dict)
    for r in rows:
        if r["line_item"] and r["data_type"] != "derived":
            by[(r["source_id"], r["source_table_index"], r["perimeter"], r["fiscal_period"])][r["line_item"]] = r["value"]
    seg = defaultdict(list)
    for r in rows:
        if r["statement"] == "segment":
            seg[(r["source_id"], r["source_table_index"], r["fiscal_period"])].append(r)
    res = []

    def add(key, name, expected, observed, tol=1.5):
        status = "pass" if abs(expected - observed) <= tol else "fail"
        res.append({"check_type": "arithmetic", "entity": "", "source_id": key[0], "fiscal_period": key[3] if len(key) > 3 else key[2],
                    "item": name, "expected": round(expected, 3), "observed": round(observed, 3), "status": status,
                    "detail": f"table {key[1]}" + (f", {key[2]}" if len(key) > 3 else "")})

    for key, it in by.items():
        g = it.get
        if "total_assets" in it and "total_liabilities_and_equity" in it:
            add(key, "total_assets == total_liabilities_and_equity", it["total_assets"], it["total_liabilities_and_equity"])
        if "net_income" in it and "net_income_nci" in it and "net_income_attributable_parent" in it:
            add(key, "net_income + net_income_nci == net_income_attributable_parent",
                it["net_income_attributable_parent"], it["net_income"] + it["net_income_nci"])
        if "pretax_income_continuing" in it and "income_tax" in it:
            target = it.get("income_continuing_ops", it.get("net_income"))
            if target is not None:
                add(key, "pretax + income_tax == income (continuing)", target, it["pretax_income_continuing"] + it["income_tax"])
        if "total_costs_and_expenses" in it:  # Disney layout
            comp = sum(g(k, 0) for k in ("cost_of_services", "cost_of_products", "sga", "depreciation_amortization"))
            add(key, "sum(cost lines) == total_costs_and_expenses", it["total_costs_and_expenses"], comp)
            pre = it["revenue"] + it["total_costs_and_expenses"] + sum(
                g(k, 0) for k in ("restructuring_impairment", "other_income_expense_net", "interest_expense_net", "equity_income_affiliates"))
            add(key, "revenue + costs + other items == pretax (Disney layout)", it["pretax_income_continuing"], pre)
        elif "operating_expenses" in it and "pretax_income_continuing" in it:  # 21CF layout
            pre = sum(g(k, 0) for k in ("revenue", "operating_expenses", "sga", "depreciation_amortization", "restructuring_impairment",
                                         "equity_income_affiliates", "interest_expense_net", "interest_income", "other_income_expense_net",
                                         "restructuring_impairment_and_other"))
            add(key, "sum(income statement lines) == pretax (21CF layout)", it["pretax_income_continuing"], pre)
    # segment revenue totals vs consolidated revenue in the same filing
    rev_by = {}
    for r in rows:
        if r["line_item"] == "revenue" and r["data_type"] == "reported":
            rev_by[(r["source_id"], r["fiscal_period"])] = r["value"]
    for (doc, idx, fp), rs in seg.items():
        rev_rows = [r for r in rs if r["section"].lower().startswith("revenues") and "geographic" not in r["section"].lower()]
        tot = [r for r in rev_rows if r["line_item_reported"].lower().startswith("total")]
        if tot and (doc, fp) in rev_by:
            add((doc, idx, fp), "segment table total revenues == income statement revenue", rev_by[(doc, fp)], tot[0]["value"])
    return res


def main():
    rows = build_rows()
    rows = mark_primary(rows)
    rows += add_derived(rows)
    checks = arithmetic_checks(rows) + xbrl_check(rows)
    for r in rows:
        r.setdefault("xbrl_check", "not_applicable" if r["data_type"] != "reported" else "not_mapped")
        r.setdefault("xbrl_fact", "")
        r.setdefault("notes", "")
        r.setdefault("segment", "")
    fields = ["record_id", "entity", "entity_name", "perimeter", "statement", "section", "line_item", "line_item_reported", "segment",
              "fiscal_period", "period_start", "period_end", "period_length", "value", "unit", "data_type", "basis",
              "is_primary", "source_id", "source_page", "source_table_index", "xbrl_check", "xbrl_fact", "notes"]
    order = {"income_statement": 0, "balance_sheet": 1, "cash_flow": 2, "segment": 3}
    rows.sort(key=lambda r: (r["entity"], r["perimeter"], order.get(r["statement"], 9), r["fiscal_period"], r["source_id"]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for i, r in enumerate(rows, 1):
            r["record_id"] = f"HF{i:05d}"
            r["value"] = f"{r['value']:g}" if isinstance(r["value"], float) else r["value"]
            w.writerow(r)
    existing = []
    if CHECKS.exists():  # keep checks written by other build steps
        with CHECKS.open(encoding="utf-8") as fh:
            existing = [c for c in csv.DictReader(fh) if c["check_type"] not in ("arithmetic", "xbrl_cross_check")]
    with CHECKS.open("w", newline="", encoding="utf-8") as fh:
        cf = ["check_type", "entity", "source_id", "fiscal_period", "item", "expected", "observed", "status", "detail"]
        w = csv.DictWriter(fh, fieldnames=cf)
        w.writeheader()
        w.writerows(existing + checks)
    n_fail = sum(c["status"] in ("fail", "mismatch") for c in checks)
    print(f"{len(rows)} rows -> {OUT.relative_to(ROOT)}; {len(checks)} checks, {n_fail} fail/mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
