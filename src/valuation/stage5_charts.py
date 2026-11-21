"""Stage 5 charts (same visual system as Stages 2-3). Table views: the CSVs written by build_stage5.py."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import make_charts  # noqa: E402
from make_charts import INK2, SLOTS, SURFACE, finish  # noqa: E402

plt.rcParams["text.parse_math"] = False
PROC = ROOT / "data" / "processed"


def main():
    make_charts.SOURCE = "Source: data/processed Stage 5 outputs (estimates built on Stage 1-4 data)."
    # 09 binomial convergence
    c = pd.read_csv(PROC / "binomial_convergence.csv")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(c.n_steps, c.binomial_european, color=SLOTS[0], lw=2, marker="o", ms=6, markeredgecolor=SURFACE, label="CRR binomial (European)")
    ax.axhline(c.black_scholes.iloc[0], color=SLOTS[1], lw=1.6, ls="--", label=f"Black-Scholes {c.black_scholes.iloc[0]:,.0f}")
    ax.set_xscale("log"); ax.set_xlabel("Binomial steps (log scale)"); ax.set_ylabel("Option value (USD m)")
    ax.set_title("Revenue-synergy expansion option: CRR converges to Black-Scholes", fontsize=10.5, loc="left")
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.legend(fontsize=8)
    finish(fig, "09_option_binomial_convergence.png", "B perspective (30 May 2018). Inputs in real_options_inputs.csv; K = S is an estimate.")
    # 10 value created distribution
    d = pd.read_csv(PROC / "monte_carlo_draws.csv")
    inp = pd.read_csv(PROC / "monte_carlo_inputs.csv").set_index("variable")
    paid = float(inp.loc["consideration_amended_38", "parameters"])
    paid0 = float(inp.loc["consideration_original_at_2018-05-30", "parameters"])
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for x, col, lab in ((d.total_value_to_disney - paid0, SLOTS[2], "vs original offer at 30 May 2018"),
                        (d.total_value_to_disney - paid, SLOTS[0], "vs amended $38 offer")):
        x = x / 1000
        ax.hist(x, bins=80, color=col, alpha=0.85, edgecolor=SURFACE, linewidth=0.3, label=f"{lab}: P(>0) = {(x > 0).mean():.0%}, median {np.median(x):,.1f}")
    ax.axvline(0, color=INK2, lw=1)
    ax.set_ylim(0, ax.get_ylim()[1] * 1.22)  # headroom so the legend does not cover the bars
    ax.set_xlabel("Value created for Disney (USD bn) = standalone equity + net cost synergies - consideration")
    ax.set_ylabel("Draws")
    ax.set_title("Monte Carlo: value created (20,000 draws, excluding the expansion option)", fontsize=10.5, loc="left")
    ax.legend(fontsize=8, loc="upper left")
    finish(fig, "10_mc_value_created.png", "Distributions are estimates (see monte_carlo_inputs.csv). Information set: May 2018 proxy.")
    # 11 tornado
    t = pd.read_csv(PROC / "monte_carlo_tornado.csv").sort_values("swing")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    base = t.base_value_created.iloc[0] / 1000
    for i, r in enumerate(t.itertuples()):
        lo, hi = sorted([r.value_created_at_p05 / 1000, r.value_created_at_p95 / 1000])
        ax.barh(i, hi - lo, left=lo, color=SLOTS[0], height=0.55, edgecolor=SURFACE, linewidth=2)
        ax.annotate(f"{lo:,.1f}", (lo, i), xytext=(-4, 0), textcoords="offset points", ha="right", va="center", fontsize=8, color=INK2)
        ax.annotate(f"{hi:,.1f}", (hi, i), xytext=(4, 0), textcoords="offset points", ha="left", va="center", fontsize=8, color=INK2)
    ax.axvline(base, color=SLOTS[1], lw=1.4, ls="--")
    ax.annotate(f"base {base:,.1f}", (base, len(t) - 0.4), xytext=(3, 0), textcoords="offset points", fontsize=8, color=INK2)
    ax.set_yticks(range(len(t)), [v.replace("_", " ") for v in t.variable], fontsize=8.5)
    ax.set_xlabel("Value created vs amended $38 offer (USD bn), one input at its 5th / 95th percentile")
    ax.set_title("What drives value creation: one-at-a-time sensitivity", fontsize=10.5, loc="left")
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    finish(fig, "11_value_tornado.png", "Other inputs held at base. Excludes the expansion option.")


if __name__ == "__main__":
    main()
