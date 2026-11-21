"""Stage 3 charts: valuation football field (equity value per 21CF share) for each perspective.

Same visual system as Stage 2 (src/make_charts.py): light surface, reference palette slots, direct labels.
The table view is data/processed/valuation_outputs.csv and valuation_sensitivity.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import make_charts  # noqa: E402
from make_charts import FIG, INK2, SLOTS, SURFACE, finish  # noqa: E402,F401  (shared style)

make_charts.SOURCE = "Source: data/processed/valuation_outputs.csv and valuation_sensitivity.csv (Stage 3)."
plt.rcParams["text.usetex"] = False
plt.rcParams["text.parse_math"] = False  # dollar signs are literal

PROC = ROOT / "data" / "processed"


def ranges(o, s, persp):
    q = o[o.perspective == persp]
    eps = q[q.metric == "equity_value_per_21cf_share"].copy()
    eps["v"] = pd.to_numeric(eps.value)
    rows = []
    g = s[(s.perspective == persp) & (s.table == "wacc_x_terminal_growth")]
    rows.append(("DCF: WACC ±1pp x growth 1-3%", g.equity_per_share.min(), g.equity_per_share.max(), SLOTS[0]))
    sc = eps[eps.method == "DCF scenario"].set_index("case").v
    rows.append(("DCF scenarios (bear-bull)", sc["bear"], sc["bull"], SLOTS[0]))
    for m, lab in (("ev_ebitda", "Comparables EV/EBITDA"), ("ev_ebit", "Comparables EV/EBIT"), ("ev_revenue", "Comparables EV/Revenue")):
        c = eps[(eps.method == "Comparables") & eps.case.str.startswith(m)].set_index("case").v
        if len(c):
            rows.append((lab + " (low-high)", c[f"{m} low"], c[f"{m} high"], SLOTS[1]))
    base = sc["base"]
    return rows, base


def main():
    o = pd.read_csv(PROC / "valuation_outputs.csv")
    s = pd.read_csv(PROC / "valuation_sensitivity.csv")
    tr = o[o.perspective == "transaction"].copy()
    tr["v"] = pd.to_numeric(tr.value, errors="coerce")
    tv = lambda m: float(tr[tr.metric == m].v.iloc[0])
    unaff = tv("21cf_unaffected_price_weighted")
    marks = {
        "A_announcement_2017-12": [("unaffected 21CF price 3 Nov 2017", unaff),
                                   ("original offer at 13 Dec 2017 Disney close", tv("per_share_value_at_2017-12-13_close"))],
        "B_proxy_2018-05": [("unaffected 21CF price 3 Nov 2017", unaff),
                            ("original offer at $102 reference", tv("per_share_value_at_102_reference")),
                            ("amended offer $38 (20 Jun 2018, subsequent)", tv("per_share_value"))],
    }
    titles = {"A_announcement_2017-12": "A. Announcement date (14 Dec 2017): estimates only",
              "B_proxy_2018-05": "B. May 2018 proxy date: management forecasts"}
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.6), sharex=True)
    for ax, persp in zip(axes, marks):
        rows, base = ranges(o, s, persp)
        for i, (lab, lo, hi, col) in enumerate(rows):
            ax.barh(i, hi - lo, left=lo, height=0.55, color=col, edgecolor=SURFACE, linewidth=2)
            ax.annotate(f"{lo:.1f}", (lo, i), xytext=(-4, 0), textcoords="offset points", ha="right", va="center", fontsize=8, color=INK2)
            ax.annotate(f"{hi:.1f}", (hi, i), xytext=(4, 0), textcoords="offset points", ha="left", va="center", fontsize=8, color=INK2)
        ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=8.5)
        ax.invert_yaxis()
        ax.axvline(base, color=SLOTS[0], lw=1.2, ls=":")
        ax.annotate(f"DCF base {base:.1f}", (base, len(rows) - 0.75), xytext=(3, 0), textcoords="offset points", fontsize=8, color=INK2)
        for j, (lab, v) in enumerate(marks[persp]):
            ax.axvline(v, color=[SLOTS[2], SLOTS[3], "#6250d6"][j], lw=1.6)
            ax.annotate(f"{lab}: ${v:.2f}", (v, -0.6 - 0.32 * j), xytext=(3, 0), textcoords="offset points", fontsize=7.5,
                        color=INK2, annotation_clip=False)
        ax.set_title(titles[persp], fontsize=10.5, loc="left", pad=40)
        ax.set_xlim(10, 62)
        ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    axes[-1].set_xlabel("Equity value per 21CF share (USD) - RemainCo + Sky stake + investments - net debt - NCI")
    finish(fig, "08_valuation_football_field.png",
           "Not a fairness opinion. A uses estimates built from public Dec 2017 information. B uses the Disney/21CF management "
           "forecasts in the May 2018 proxy. Per-share values cover 21CF's acquired business only; holders also kept New Fox.",
           y=-0.03)


if __name__ == "__main__":
    main()
