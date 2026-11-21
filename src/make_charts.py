"""Stage 2 charts (static PNG, light mode) from financial_ratios.csv and segment_analysis.csv.

Output: docs/figures/*.png. Every chart is in USD millions or percent, and fiscal-year labels show the period-end
month (Disney: Sep/Oct; 21CF and RemainCo: Jun) so the 3-month offset is visible. The CSVs are the
table view for every chart.

Palette: reference categorical slots 1-4 (validated with the dataviz validator, light mode: all checks
pass; aqua and yellow are below 3:1 contrast, so direct labels and legends are always shown).
Entity colours are fixed: Disney = blue, 21CF consolidated = orange, RemainCo = aqua.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
FIG = ROOT / "docs" / "figures"

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
ENT_COLOR = {"DIS": SLOTS[0], "21CF": SLOTS[1], "RemainCo": SLOTS[2]}
ENT_LABEL = {"DIS": "Disney (FY ends Sep/Oct)", "21CF": "21CF consolidated (FY ends Jun)",
             "RemainCo": "RemainCo, acquired perimeter (pro forma, FY ends Jun)"}
FY = ["FY2015", "FY2016", "FY2017", "FY2018"]
PE = {"DIS": ["Oct-15", "Oct-16", "Sep-17", "Sep-18"], "21CF": ["Jun-15", "Jun-16", "Jun-17", "Jun-18"]}
PE["RemainCo"] = PE["21CF"]
SOURCE = "Source: SEC filings via data/processed/financial_ratios.csv; derived metrics as defined in docs/historical_analysis_report.md."

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "font.size": 9.5, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlecolor": INK,
    "legend.frameon": False, "figure.dpi": 130,
})


def load():
    r = pd.read_csv(PROC / "financial_ratios.csv")
    r["v"] = pd.to_numeric(r["value"], errors="coerce")
    s = pd.read_csv(PROC / "segment_analysis.csv")
    s["v"] = pd.to_numeric(s["value"], errors="coerce")
    return r, s


def series(r, ent, metric, periods=FY):
    q = r[(r.entity == ent) & (r.metric == metric)].set_index("fiscal_period")["v"]
    return [q.get(p, np.nan) for p in periods]


def xlabels(ent):
    return [f"{fy}\n({pe})" for fy, pe in zip(FY, PE[ent])]


def finish(fig, name, note="", y=-0.04):
    """Footnote placed below everything (y in figure coordinates; lower when legends sit under the axes)."""
    fig.tight_layout()
    fig.text(0.01, y, (note + "\n" if note else "") + SOURCE, fontsize=7.5, color=INK2, ha="left", va="top")
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)
    print("chart", name)


def bars(ax, x, vals, color, width, label=None, fmt="{:,.0f}", labels=True):
    vals = np.array(vals, dtype=float)
    b = ax.bar(x, np.nan_to_num(vals), width, color=color, label=label, edgecolor=SURFACE, linewidth=2)
    if labels:
        for xi, v in zip(x, vals):
            if not np.isnan(v):
                ax.annotate(fmt.format(v), (xi, v), xytext=(0, 3 if v >= 0 else -11), textcoords="offset points",
                            ha="center", fontsize=7.5, color=INK2)
    return b


def chart_revenue(r):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(4)
    ax = axes[0]
    bars(ax, x, series(r, "DIS", "revenue"), ENT_COLOR["DIS"], 0.6, ENT_LABEL["DIS"])
    ax.set_xticks(x, xlabels("DIS")); ax.set_title("Disney revenue (USD m)"); ax.set_ylim(0, 68000)
    ax = axes[1]
    bars(ax, x - 0.2, series(r, "21CF", "revenue"), ENT_COLOR["21CF"], 0.38, ENT_LABEL["21CF"])
    bars(ax, x + 0.2, series(r, "RemainCo", "revenue"), ENT_COLOR["RemainCo"], 0.38, ENT_LABEL["RemainCo"])
    ax.set_xticks(x, xlabels("21CF")); ax.set_title("21CF consolidated vs RemainCo revenue (USD m)"); ax.set_ylim(0, 37000)
    ax.legend(loc="upper left", fontsize=8)
    axes[0].legend(loc="upper left", fontsize=8)
    for a in axes:
        a.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    finish(fig, "01_revenue_trends.png",
           "RemainCo: FY2015 from the 2018 joint proxy, FY2016-FY2018 from the March 2019 8-K/A (closing perimeter). "
           "Disney FY2015 = 53 weeks.")


def chart_ebit_ebitda(r):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=False)
    x = np.arange(4)
    for ax, ent in zip(axes, ["DIS", "21CF", "RemainCo"]):
        bars(ax, x - 0.2, series(r, ent, "ebitda"), ENT_COLOR[ent], 0.38, "EBITDA (derived)")
        bars(ax, x + 0.2, series(r, ent, "ebit"), "#9fc3ee" if ent == "DIS" else ("#f5b398" if ent == "21CF" else "#8fd6bb"),
             0.38, "EBIT (derived)")
        ax.set_xticks(x, xlabels(ent)); ax.set_title(ENT_LABEL[ent].split(" (")[0] + " - EBITDA and EBIT (USD m)", fontsize=10)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
        ax.legend(loc="upper left", fontsize=8)
        ax.set_ylim(0, max(np.nanmax(series(r, ent, "ebitda")) * 1.25, 1))
    finish(fig, "02_ebit_ebitda_trends.png",
           "EBIT = operating income before equity income, other income/expense and interest (not a reported subtotal); "
           "EBITDA = EBIT + income-statement D&A. RemainCo includes all 21CF corporate costs and the RSNs.")


def chart_margins(r):
    metrics = [("ebitda_margin", "EBITDA margin"), ("ebit_margin", "EBIT margin"), ("net_margin", "Net margin (attributable)")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    for ax, (m, title) in zip(axes, metrics):
        for ent in ["DIS", "21CF", "RemainCo"]:
            mm = "net_margin_continuing" if (m == "net_margin" and ent == "RemainCo") else m
            y = np.array(series(r, ent, mm)) * 100
            ax.plot(FY, y, color=ENT_COLOR[ent], lw=2, marker="o", ms=6, label=ENT_LABEL[ent].split(" (")[0],
                    markeredgecolor=SURFACE, markeredgewidth=1.5)
            ax.annotate(f"{y[-1]:.1f}%", (3, y[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
        ax.set_title(title + " (%)"); ax.set_xlim(-0.3, 3.6)
        ax.set_xticks(range(4), [f"{f}" for f in FY])
    axes[0].legend(loc="lower left", fontsize=8)
    finish(fig, "03_profitability_margins.png",
           "Fiscal years differ: Disney Oct-Sep, 21CF/RemainCo Jul-Jun. 21CF and RemainCo FY2015 net margins include the ~$5.0bn "
           "Sky Italia/Deutschland disposal gain; RemainCo net margin uses income from continuing operations.")


def chart_segments(s):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    x = np.arange(4)
    for ax, ent, segs, title in [
        (axes[0], "DIS", ["Media Networks", "Parks and Resorts", "Studio Entertainment", "Consumer Products & Interactive Media"],
         "Disney segment revenue (USD m)"),
        (axes[1], "21CF", ["Cable Network Programming", "Filmed Entertainment", "Television", "Direct Broadcast Satellite Television"],
         "21CF consolidated segment revenue (USD m)\nNOT the acquired perimeter")]:
        bottom = np.zeros(4)
        for i, seg in enumerate(segs):
            q = s[(s.entity == ent) & (s.segment == seg) & (s.metric == "segment_revenue")].set_index("fiscal_period")["v"]
            v = np.array([q.get(p, 0.0) for p in FY])
            ax.bar(x, v, 0.6, bottom=bottom, color=SLOTS[i], label=seg, edgecolor=SURFACE, linewidth=2)
            bottom += v
        for xi, t in zip(x, bottom):
            ax.annotate(f"{t:,.0f}", (xi, t), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=7.5, color=INK2)
        ax.set_xticks(x, xlabels(ent)); ax.set_title(title, fontsize=10)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, fontsize=8)
    finish(fig, "04_segment_revenue_composition.png",
           "Disney segments include intersegment revenue (Studio -> CP&IM, eliminated within CP&IM). 21CF bars exclude "
           "'Other, Corporate and Eliminations' (negative, -1,318 to -1,514), so stacks exceed reported total revenue.", y=-0.16)


def chart_segment_margins(s):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, ent, segs, title in [
        (axes[0], "DIS", ["Media Networks", "Parks and Resorts", "Studio Entertainment", "Consumer Products & Interactive Media"],
         "Disney segment operating income margin (%)"),
        (axes[1], "21CF", ["Cable Network Programming", "Filmed Entertainment", "Television"],
         "21CF Segment OIBDA margin (%) - consolidated, not acquired perimeter")]:
        for i, seg in enumerate(segs):
            q = s[(s.entity == ent) & (s.segment == seg) & (s.metric == "segment_margin")].set_index("fiscal_period")["v"]
            y = np.array([q.get(p, np.nan) for p in FY]) * 100
            ax.plot(FY, y, color=SLOTS[i], lw=2, marker="o", ms=6, label=seg, markeredgecolor=SURFACE, markeredgewidth=1.5)
            ax.annotate(f"{y[-1]:.1f}%", (3, y[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=8, color=INK2)
        ax.set_title(title, fontsize=10); ax.set_xlim(-0.3, 3.7)
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=8)
    finish(fig, "05_segment_margins.png",
           "Not comparable across panels: Disney segment operating income is after D&A; 21CF Segment OIBDA is before D&A.", y=-0.16)


def chart_debt_cash(r):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    x = np.arange(4)
    for ax, ent in zip(axes, ["DIS", "21CF"]):
        bars(ax, x - 0.27, series(r, ent, "cash"), SLOTS[2], 0.26, "Cash and cash equivalents (reported)")
        bars(ax, x, series(r, ent, "total_borrowings"), SLOTS[0], 0.26, "Total borrowings (derived: current + non-current)")
        bars(ax, x + 0.27, series(r, ent, "net_debt"), SLOTS[1], 0.26, "Net debt (derived)")
        ax.set_xticks(x, xlabels(ent)); ax.set_title(ENT_LABEL[ent] + " - balance sheet (USD m)", fontsize=10)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1, fontsize=8)
    finish(fig, "06_debt_and_cash.png",
           "Year-end balance sheets. Net debt = borrowings (carrying amount) - cash; excludes investments, leases, pensions and NCI. "
           "RemainCo pro forma: Mar-18 net debt 6,725; Dec-18 net cash 7,129 (after the Sky stake sale).", y=-0.16)


def chart_cash_flow(r):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    x = np.arange(4)
    for ax, ent in zip(axes, ["DIS", "21CF"]):
        bars(ax, x - 0.27, series(r, ent, "cfo"), SLOTS[0], 0.26, "Cash from operations (reported)")
        bars(ax, x, series(r, ent, "capex"), SLOTS[1], 0.26, "Capital expenditure (reported)")
        bars(ax, x + 0.27, series(r, ent, "fcf_cfo_less_capex"), SLOTS[2], 0.26, "FCF = CFO + capex (derived)")
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(x, xlabels(ent)); ax.set_title(ENT_LABEL[ent] + " - cash flow (USD m)", fontsize=10)
        ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1, fontsize=8)
    finish(fig, "07_cash_flow_trends.png",
           "21CF CFO = continuing operations. Film/TV content spending sits inside CFO for both companies. "
           "No cash-flow data exists for RemainCo (not disclosed).", y=-0.16)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    r, s = load()
    chart_revenue(r); chart_ebit_ebitda(r); chart_margins(r)
    chart_segments(s); chart_segment_margins(s); chart_debt_cash(r); chart_cash_flow(r)


if __name__ == "__main__":
    main()
