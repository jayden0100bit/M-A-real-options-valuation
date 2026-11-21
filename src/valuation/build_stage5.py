"""Stage 5 driver: real options (5A) and Monte Carlo (5B). Reads Stage 1-4 outputs; never rewrites them.

Outputs (data/processed/): real_options_inputs.csv, real_options_outputs.csv, binomial_convergence.csv,
monte_carlo_inputs.csv, monte_carlo_draws.csv, monte_carlo_summary.csv, monte_carlo_convergence.csv,
monte_carlo_tornado.csv, monte_carlo_scenarios.csv; charts docs/figures/09-11; checks realoption_* / montecarlo_*.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
import monte_carlo as mc  # noqa: E402
import real_options as ro  # noqa: E402

PROC = ROOT / "data" / "processed"
STAGE5 = ("realoption_", "montecarlo_")


def write(path, rows):
    rows = rows.to_dict("records") if isinstance(rows, pd.DataFrame) else rows
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    # ---------------- 5A real options
    R = ro.build()
    write(PROC / "real_options_inputs.csv", ro.INPUTS)
    write(PROC / "real_options_outputs.csv", ro.OUT)
    write(PROC / "binomial_convergence.csv", ro.CONV)

    # ---------------- 5B Monte Carlo
    m = mc.Model()
    zero_ev, zero_eq = m.standalone_equity(0.0, 0.0)
    # tolerance: Stage 3 stores WACC rounded to 6 decimals in dcf_assumptions.csv, worth ~0.4m on a ~51bn EV (1e-5 relative)
    mc.chk("zero shocks reproduce the Stage 3 base EV (B, Disney forecasts; WACC stored to 6 dp)", m.stage3_ev, zero_ev[0], 1e-5 * m.stage3_ev)
    zero_syn = m.net_synergies(1.0, 0, 1.0)
    mc.chk("zero shocks reproduce the Stage 4 base net synergy value (B)", m.stage4_net, zero_syn[0], 0.5)
    # stage-4 scenario reproduction where the parametrisation matches (realization / integration multiple only)
    S4 = pd.read_csv(PROC / "synergy_outputs.csv")
    for lab, real, icm in (("realization 50%", 0.5, 1.0), ("integration cost 2.00x run-rate", 1.0, 2.0)):
        ref = float(S4[(S4.perspective == mc.PERSP) & (S4.section == "Synergy sensitivity") & (S4.case.str.startswith(lab))].value.iloc[0])
        mc.chk(f"vectorised synergy model matches Stage 4 sensitivity '{lab}'", ref, m.net_synergies(real, 0, icm)[0], 0.5)
    # Stage 3 margin / growth sensitivity reproduction
    S3 = pd.read_csv(PROC / "valuation_sensitivity.csv")
    for tab, shift in (("ebitda_margin_shift", 0.02), ("revenue_growth_shift", -0.02)):
        ref = float(S3[(S3.perspective == mc.PERSP) & (S3.table == tab) & (np.isclose(S3.row_value.astype(float), shift))].enterprise_value_ops.iloc[0])
        ev = m.standalone_equity(shift if "growth" in tab else 0.0, shift if "margin" in tab else 0.0)[0][0]
        mc.chk(f"vectorised DCF matches Stage 3 sensitivity {tab} {shift:+.2f}", ref, ev, 1.0)

    so = pd.read_csv(PROC / "synergy_outputs.csv")
    orig_ps = float(so[(so.perspective == mc.PERSP) & (so.section == "Deal justification") & (so.case.str.startswith("original")) &
                       (so.metric == "consideration_per_share")].value.iloc[0])
    paid = {"amended_38": 38.0 * m.shares, "original_at_2018-05-30": orig_ps * m.shares}
    df = mc.simulate(m, option_value=R["bs"])
    summ = mc.summarize(df, m, paid)
    summ = summ[~((summ.metric.str.startswith("synergy_coverage")) & ~summ.metric.str.endswith("amended_38"))]
    # reproducibility and convergence
    df2 = mc.simulate(m, option_value=R["bs"])
    mc.chk("same seed reproduces every draw (max abs difference)", 0.0,
           float(np.abs(df2.total_value_to_disney.values - df.total_value_to_disney.values).max()), 0.0, "montecarlo_reproducibility")
    conv = []
    for n in (1000, 2000, 5000, 10000, 20000):
        x = df.total_value_to_disney.values[:n] - paid["amended_38"]
        conv.append({"n_draws": n, "mean_value_created_vs_38": x.mean(), "se": x.std(ddof=1) / np.sqrt(n), "prob_positive": (x > 0).mean(),
                     "note": "first n draws of the base seed"})
    alt = mc.simulate(m, seed=mc.SEED + 1)
    xa = alt.total_value_to_disney.values - paid["amended_38"]
    x = df.total_value_to_disney.values - paid["amended_38"]
    se = np.sqrt(x.var(ddof=1) / len(x) + xa.var(ddof=1) / len(xa))
    conv.append({"n_draws": 20000, "mean_value_created_vs_38": xa.mean(), "se": xa.std(ddof=1) / np.sqrt(len(xa)), "prob_positive": (xa > 0).mean(),
                 "note": "independent seed"})
    mc.chk("independent seed: means agree within 3 standard errors", x.mean(), xa.mean(), 3 * se, "montecarlo_convergence")
    mc.CHECKS.append({"check_type": "montecarlo_convergence", "entity": "", "source_id": "", "fiscal_period": mc.PERSP,
                      "item": "standard error falls roughly with 1/sqrt(n) (se(20k)/se(1k) between 0.15 and 0.30)",
                      "expected": 0.2236, "observed": round(conv[4]["se"] / conv[0]["se"], 4),
                      "status": "pass" if 0.15 <= conv[4]["se"] / conv[0]["se"] <= 0.30 else "fail", "detail": "theory: sqrt(1/20)=0.2236"})
    mc.CHECKS.append({"check_type": "montecarlo_convergence", "entity": "", "source_id": "", "fiscal_period": mc.PERSP,
                      "item": "relative standard error of the mean value created below 2%", "expected": "<0.02",
                      "observed": round(abs(conv[4]["se"] / conv[4]["mean_value_created_vs_38"]), 5) if conv[4]["mean_value_created_vs_38"] else "",
                      "status": "pass" if abs(conv[4]["se"]) < 0.02 * max(abs(conv[4]["mean_value_created_vs_38"]), 1000) else "fail", "detail": ""})
    # distribution sanity: sampled inputs respect their bounds
    for k, spec in mc.DIST.items():
        lo, hi = (spec[1], spec[3]) if spec[0] == "triangular" else ((min(spec[1]), max(spec[1])) if spec[0] == "discrete" else (spec[3], spec[4]))
        ok = df[k].min() >= lo - 1e-12 and df[k].max() <= hi + 1e-12
        mc.CHECKS.append({"check_type": "montecarlo_inputs", "entity": "", "source_id": "", "fiscal_period": mc.PERSP, "item": f"{k} within [{lo}, {hi}]",
                          "expected": "bounded", "observed": f"{df[k].min():.4f}..{df[k].max():.4f}", "status": "pass" if ok else "fail", "detail": ""})
    # identity per draw
    mc.chk("total value = standalone equity + net synergies (max abs error over draws)", 0.0,
           float(np.abs(df.total_value_to_disney - df.standalone_equity - df.net_synergy_value).max()), 1e-6)

    # tornado: one variable at a time at its 5th / 95th percentile (others at base)
    base_vc = (zero_eq[0] + zero_syn[0]) - paid["amended_38"]
    torn = []
    for k in mc.DIST:
        lo, hi = np.percentile(df[k], 5), np.percentile(df[k], 95)
        vals = []
        for v in (lo, hi):
            kw = {"g": 0.0, "mm": 0.0, "r": 1.0, "d": 0, "ic": 1.0}
            key = {"revenue_growth_shift": "g", "ebitda_margin_shift": "mm", "synergy_realization": "r",
                   "synergy_delay_years": "d", "integration_cost_multiple": "ic"}[k]
            kw[key] = v
            eq = m.standalone_equity(kw["g"], kw["mm"])[1][0]
            ns = m.net_synergies(kw["r"], int(round(kw["d"])), kw["ic"])[0]
            vals.append(eq + ns - paid["amended_38"])
        torn.append({"variable": k, "p05_input": lo, "p95_input": hi, "value_created_at_p05": vals[0], "value_created_at_p95": vals[1],
                     "base_value_created": base_vc, "swing": abs(vals[1] - vals[0])})
    torn = pd.DataFrame(torn).sort_values("swing", ascending=False)
    # scenarios: Stage 4 deterministic bear/base/bull vs simulated percentiles
    scen = []
    for case in ("bear", "base", "bull"):
        ns = float(S4[(S4.perspective == mc.PERSP) & (S4.section == "Synergy value") & (S4.case == case) & (S4.metric == "net_synergy_value")].value.iloc[0])
        scen.append({"source": f"Stage 4 deterministic {case} (standalone base)", "net_synergy_value": ns,
                     "value_created_vs_38": float(zero_eq[0]) + ns - paid["amended_38"]})
    for p in (5, 50, 95):
        scen.append({"source": f"Monte Carlo p{p:02d}", "net_synergy_value": float(np.percentile(df.net_synergy_value, p)),
                     "value_created_vs_38": float(np.percentile(df.total_value_to_disney - paid["amended_38"], p))})
    s4 = {r["source"]: r["value_created_vs_38"] for r in scen}
    mc.CHECKS.append({"check_type": "montecarlo_scenarios", "entity": "", "source_id": "", "fiscal_period": mc.PERSP,
                      "item": "Monte Carlo median lies between the deterministic bear and bull cases", "expected": "bear < p50 < bull",
                      "observed": f"{s4['Stage 4 deterministic bear (standalone base)']:.0f} < {s4['Monte Carlo p50']:.0f} < {s4['Stage 4 deterministic bull (standalone base)']:.0f}",
                      "status": "pass" if s4["Stage 4 deterministic bear (standalone base)"] < s4["Monte Carlo p50"] < s4["Stage 4 deterministic bull (standalone base)"] else "fail",
                      "detail": ""})
    inputs = [{"variable": k, "distribution": v[0], "parameters": str(v[1:]), "value_type": "estimate",
               "anchor": {"synergy_realization": "Stage 4 bear 75% / base 100% / bull 125%, lower tail to 50%",
                          "synergy_delay_years": "Stage 4 bear = one year late",
                          "integration_cost_multiple": "Stage 4 range 0.75x-2.0x; later severance estimate 0.75x",
                          "revenue_growth_shift": "Stage 3 sensitivity +/-2pp",
                          "ebitda_margin_shift": "Stage 3 sensitivity +/-2pp"}[k]} for k, v in mc.DIST.items()]
    inputs += [{"variable": "seed", "distribution": "fixed", "parameters": str(mc.SEED), "value_type": "setting", "anchor": ""},
               {"variable": "n_draws", "distribution": "fixed", "parameters": str(mc.N_DRAWS), "value_type": "setting", "anchor": ""},
               {"variable": "consideration_amended_38", "distribution": "fixed", "parameters": f"{paid['amended_38']:.1f}", "value_type": "derived",
                "anchor": "$38 x 1,871.1m fully diluted shares"},
               {"variable": "consideration_original_at_2018-05-30", "distribution": "fixed", "parameters": f"{paid['original_at_2018-05-30']:.1f}",
                "value_type": "derived", "anchor": "0.2745 x Disney close 30 May 2018 x shares"},
               {"variable": "expansion_option_value", "distribution": "fixed", "parameters": f"{R['bs']:.1f}", "value_type": "estimate",
                "anchor": "Stage 5A Black-Scholes base"}]
    write(PROC / "monte_carlo_inputs.csv", inputs)
    df.round(6).to_csv(PROC / "monte_carlo_draws.csv", index_label="draw")
    write(PROC / "monte_carlo_summary.csv", summ)
    write(PROC / "monte_carlo_convergence.csv", conv)
    write(PROC / "monte_carlo_tornado.csv", torn)
    write(PROC / "monte_carlo_scenarios.csv", scen)

    import stage5_charts
    stage5_charts.main()

    checks = ro.CHECKS + mc.CHECKS
    vc = PROC / "verification_checks.csv"
    with vc.open(encoding="utf-8") as fh:
        existing = [c for c in csv.DictReader(fh) if not c["check_type"].startswith(STAGE5)]
    with vc.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["check_type", "entity", "source_id", "fiscal_period", "item", "expected", "observed", "status", "detail"])
        w.writeheader()
        w.writerows(existing + checks)
    bad = [c for c in checks if c["status"] != "pass"]
    print(f"stage 5: option base {R['bs']:,.0f}; {len(df):,} draws; {len(checks)} checks, {len(bad)} failed")
    for c in bad:
        print("FAILED", c)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
