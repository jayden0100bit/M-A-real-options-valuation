"""Stage 5A: the strategic expansion option (revenue synergies), valued with Black-Scholes and a CRR tree.

The option
----------
Cost synergies (~$2.0bn run-rate, Stage 4) are a management *commitment* and are valued as cash flows. Revenue synergies
are different. Disney's advisors valued them (May 2018 proxy p.145), but Disney never quantified or committed to them,
and realizing them needs further investment (management cited extra production spend and forgoing third-party
licensing to feed its own streaming services). That is a right, not an obligation: an expansion call option.

| Parameter | Definition | Base value | Type |
|---|---|---|---|
| S  underlying | PV of the revenue-synergy cash flows | advisors' implied midpoint $9.625 per RemainCo share x 1,871.1m shares | derived from disclosed ranges |
| K  exercise cost | PV of the investment needed to capture them | = S (at the money) | estimate (not disclosed) |
| sigma volatility | volatility of the underlying value | median peer *asset* volatility (2y weekly equity vol x E/V) | derived from market data |
| T  maturity | decision window | 3.0 years (to fiscal 2021, end of management's synergy-realization period) | estimate |
| r  risk-free | 3-year Treasury (FRED DGS3) on 30 May 2018 | 2.53% | market |
| q  leakage | value lost per year of waiting (competition) | 0% base; 3% in the American-exercise case | estimate |

Setting K = S makes the static NPV of pursuing revenue synergies zero. The option value is then purely the value of
flexibility, i.e. of being able to wait and invest only if the outcome is favourable. This stops the analysis from
counting the full $18bn as if it were certain, as a DCF of the advisors' estimates would.
Perspective: B (30 May 2018), the first date on which any revenue-synergy information was public.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
import market_data as md  # noqa: E402
from options import binomial_call, black_scholes_call, mc_european_call  # noqa: E402

PROC = ROOT / "data" / "processed"
PERSP = "B_proxy_2018-05"
MKT_DATE = "2018-05-30"
INPUTS, OUT, CONV, CHECKS = [], [], [], []


def inp(param, value, unit, value_type, source, method, low="", high=""):
    INPUTS.append({"perspective": PERSP, "parameter": param, "value": value, "unit": unit, "value_type": value_type, "source": source,
                   "method": method, "sensitivity_low": low, "sensitivity_high": high})
    return value


def o(section, case, metric, value, unit, value_type="estimate", notes=""):
    OUT.append({"perspective": PERSP, "section": section, "case": case, "metric": metric,
                "value": round(value, 6) if isinstance(value, float) else value, "unit": unit, "value_type": value_type, "notes": notes})


def chk(ctype, item, expected, observed, tol, detail=""):
    CHECKS.append({"check_type": ctype, "entity": "RemainCo expansion option", "source_id": "", "fiscal_period": PERSP, "item": item,
                   "expected": round(float(expected), 6), "observed": round(float(observed), 6),
                   "status": "pass" if abs(float(expected) - float(observed)) <= tol else "fail", "detail": detail})


def asset_volatility():
    comps = pd.read_csv(PROC / "comparable_companies.csv")
    comps = comps[comps.perspective == PERSP]
    rows = []
    for t in ("CMCSA", "AMCX", "NFLX", "DIS"):
        r = md.weekly_returns(t, MKT_DATE, 2)
        sig_e = float(r.std(ddof=1) * np.sqrt(52))
        c = comps[comps.ticker == t].iloc[0]
        ev_w = c.market_cap / (c.market_cap + c.debt)
        rows.append({"ticker": t, "equity_vol": sig_e, "equity_weight": ev_w, "asset_vol": sig_e * ev_w, "weeks": len(r)})
        inp(f"asset_vol_{t}", round(sig_e * ev_w, 6), "ratio", "derived",
            "Yahoo Finance weekly closes (data/raw/market) and comparable_companies.csv",
            f"equity vol {sig_e:.3f} (2y weekly, annualised x sqrt(52), {len(r)} returns) x E/(D+E) {ev_w:.3f}"
            + ("; reference only" if t == "DIS" else ""))
    peers = [x["asset_vol"] for x in rows if x["ticker"] != "DIS"]
    return float(np.median(peers)), rows


def build():
    so = pd.read_csv(PROC / "synergy_outputs.csv")
    ref = so[(so.perspective == PERSP) & (so.case == "revenue synergies")].iloc[0]
    da = pd.read_csv(PROC / "dcf_assumptions.csv")
    shares = float(da[(da.perspective == PERSP) & (da.parameter == "shares_fully_diluted_m")].value.iloc[0])
    S = inp("S_underlying_pv_revenue_synergies", float(ref.value) * shares, "USD_m", "derived",
            f"synergy_outputs.csv reference row: {ref.notes[:160]}",
            f"advisors' implied revenue-synergy value {float(ref.value):.3f} USD per RemainCo share x {shares:,.1f}m fully diluted shares. "
            "Pre-TCJA taxes; discounted at 6.75%-7.75% to Dec 2017; not updated to May 2018 (limitation)",
            (35.75 - 27.50) * shares, (47.25 - 36.25) * shares)
    K = inp("K_exercise_cost", S, "USD_m", "estimate", "judgement (investment needed is not disclosed)",
            "At the money (K = S): static NPV of pursuing revenue synergies is zero, so the option value is pure flexibility value",
            0.75 * S, 1.25 * S)
    sig, vols = asset_volatility()
    sigma = inp("sigma_volatility", round(sig, 6), "ratio", "derived", "median of peer asset volatilities (CMCSA, AMCX, NFLX)",
                "Proxy for volatility of the value of media cash flows. Revenue synergies are arguably riskier, hence the +10pp sensitivity",
                round(sig - 0.10, 6), round(sig + 0.10, 6))
    r, rd = md.asof(md.fred("DGS3"), MKT_DATE)
    r = inp("r_risk_free", r / 100, "ratio", "market", md.manifest()["FRED_DGS3.csv"]["url"], f"3-year Treasury yield on {rd}")
    T = inp("T_maturity_years", 3.0, "years", "estimate", "DIS_425_20171215_CALL ('fully realize ... by 2021'); judgement",
            "Decision window to the end of management's synergy-realization period (fiscal 2021)", 1.0, 5.0)
    q_base = inp("q_leakage_yield_base", 0.0, "ratio", "estimate", "judgement", "No value leakage while waiting (European = American)")
    q_alt = inp("q_leakage_yield_alt", 0.03, "ratio", "estimate", "judgement",
                "3% a year of value lost to competition while waiting; makes early exercise potentially optimal", 0.0, 0.06)

    # ---- base valuation
    bs, d1, d2 = black_scholes_call(S, K, r, T, sigma, q_base)
    o("Option value", "base", "black_scholes_call", bs, "USD_m", notes=f"d1={d1:.4f}, d2={d2:.4f}")
    o("Option value", "base", "option_value_per_21cf_share", bs / shares, "USD_per_share")
    o("Option value", "base", "static_npv_S_minus_K", S - K, "USD_m", "estimate", "zero by construction (at the money)")
    o("Option value", "base", "advisors_static_value_of_revenue_synergies", S, "USD_m", "derived",
      "what a DCF counting revenue synergies as certain would add (no investment cost)")
    # put-call parity check
    from options import black_scholes_put
    put = black_scholes_put(S, K, r, T, sigma, q_base)
    chk("realoption_parity", "put-call parity: C - P = S e^-qT - K e^-rT", S * np.exp(-q_base * T) - K * np.exp(-r * T), bs - put, 1e-6)
    chk("realoption_bounds", "max(S e^-qT - K e^-rT, 0) <= C <= S", 1.0,
        1.0 if max(S * np.exp(-q_base * T) - K * np.exp(-r * T), 0) <= bs <= S else 0.0, 0)
    # ---- binomial cross-check and convergence
    for n in (10, 25, 50, 100, 250, 500, 1000, 2000, 5000):
        eu = binomial_call(S, K, r, T, sigma, n, american=False, q=q_base)
        am = binomial_call(S, K, r, T, sigma, n, american=True, q=q_base)
        CONV.append({"n_steps": n, "binomial_european": eu, "binomial_american": am, "black_scholes": bs,
                     "abs_error_vs_bs": abs(eu - bs), "rel_error_vs_bs": abs(eu - bs) / bs})
    last = CONV[-1]
    o("Binomial cross-check", "q = 0", "binomial_european_n5000", last["binomial_european"], "USD_m")
    o("Binomial cross-check", "q = 0", "binomial_american_n5000", last["binomial_american"], "USD_m",
      notes="equals European: early exercise of a call is never optimal without leakage")
    chk("realoption_convergence", "CRR European (n=5000) within 0.05% of Black-Scholes", 0.0, last["rel_error_vs_bs"], 0.0005)
    chk("realoption_convergence", "American = European when q = 0 (n=5000)", last["binomial_european"], last["binomial_american"], 1e-6)
    errs = [c["abs_error_vs_bs"] for c in CONV]
    CHECKS.append({"check_type": "realoption_convergence", "entity": "", "source_id": "", "fiscal_period": PERSP,
                   "item": "binomial error shrinks: error(n=5000) < error(n=100) < error(n=10)", "expected": "decreasing",
                   "observed": f"{errs[0]:.3f} > {errs[3]:.3f} > {errs[-1]:.4f}",
                   "status": "pass" if errs[-1] < errs[3] < errs[0] else "fail", "detail": "CRR oscillates, so endpoints are compared"})
    mc, se = mc_european_call(S, K, r, T, sigma, q_base, 400_000, seed=42)
    o("Monte Carlo cross-check", "q = 0", "mc_european_call", mc, "USD_m", notes=f"400k antithetic paths, seed 42, s.e. {se:.2f}")
    chk("realoption_convergence", "Monte Carlo within 3 standard errors of Black-Scholes", bs, mc, 3 * se)
    mc2, _ = mc_european_call(S, K, r, T, sigma, q_base, 400_000, seed=42)
    chk("realoption_reproducibility", "same seed gives an identical Monte Carlo price", mc, mc2, 0.0)
    # ---- leakage case: American > European
    bs_q, _, _ = black_scholes_call(S, K, r, T, sigma, q_alt)
    eu_q = binomial_call(S, K, r, T, sigma, 2000, american=False, q=q_alt)
    am_q = binomial_call(S, K, r, T, sigma, 2000, american=True, q=q_alt)
    o("Option value", f"leakage q = {q_alt:.0%}", "black_scholes_merton_call", bs_q, "USD_m")
    o("Option value", f"leakage q = {q_alt:.0%}", "binomial_european_n2000", eu_q, "USD_m")
    o("Option value", f"leakage q = {q_alt:.0%}", "binomial_american_n2000", am_q, "USD_m",
      notes="early-exercise premium = American - European")
    o("Option value", f"leakage q = {q_alt:.0%}", "early_exercise_premium", am_q - eu_q, "USD_m")
    chk("realoption_convergence", "Merton BS vs CRR European with leakage (n=2000) within 0.1%", 0.0, abs(eu_q - bs_q) / bs_q, 0.001)
    CHECKS.append({"check_type": "realoption_bounds", "entity": "", "source_id": "", "fiscal_period": PERSP,
                   "item": "American >= European with leakage", "expected": ">=0", "observed": round(am_q - eu_q, 4),
                   "status": "pass" if am_q >= eu_q - 1e-9 else "fail", "detail": ""})
    # ---- scenarios and one-at-a-time sensitivities
    lowS, highS = (35.75 - 27.50) * shares, (47.25 - 36.25) * shares
    scen = {"bear": dict(S=lowS, K=K, sigma=sigma - 0.10, T=2.0, q=q_alt),
            "base": dict(S=S, K=K, sigma=sigma, T=T, q=q_base),
            "bull": dict(S=highS, K=K, sigma=sigma + 0.10, T=4.0, q=q_base)}
    notes = {"bear": "S at the low end of the advisors' range, lower volatility (-10pp), 2-year window, 3% leakage",
             "base": "as defined above", "bull": "S at the high end, higher volatility (+10pp), 4-year window"}
    vals = {}
    for k, p in scen.items():
        v = binomial_call(p["S"], p["K"], r, p["T"], p["sigma"], 2000, american=True, q=p["q"])
        vals[k] = v
        o("Scenario", k, "option_value_american_crr", v, "USD_m", notes=notes[k])
        o("Scenario", k, "option_value_per_21cf_share", v / shares, "USD_per_share")
    CHECKS.append({"check_type": "realoption_scenarios", "entity": "", "source_id": "", "fiscal_period": PERSP,
                   "item": "bear < base < bull", "expected": "ordered", "observed": f"{vals['bear']:.0f} < {vals['base']:.0f} < {vals['bull']:.0f}",
                   "status": "pass" if vals["bear"] < vals["base"] < vals["bull"] else "fail", "detail": ""})
    tests = [("sigma", sigma - 0.10, sigma + 0.10), ("T", 1.0, 5.0), ("K", 0.75 * S, 1.25 * S), ("S", lowS, highS), ("r", r - 0.01, r + 0.01),
             ("q", 0.0, 0.06)]
    for name, lo, hi in tests:
        res = []
        for lab, val in (("low", lo), ("high", hi)):
            p = dict(S=S, K=K, r=r, T=T, sigma=sigma, q=q_base)
            p[name] = val
            v, _, _ = black_scholes_call(p["S"], p["K"], p["r"], p["T"], p["sigma"], p["q"])
            res.append(v)
            o("Sensitivity (Black-Scholes)", f"{name} {lab} = {val:.4g}", "option_value", v, "USD_m")
        expected_up = name in ("sigma", "T", "S", "r")
        ok = (res[1] > res[0]) if expected_up else (res[1] < res[0])
        CHECKS.append({"check_type": "realoption_sensitivity", "entity": "", "source_id": "", "fiscal_period": PERSP,
                       "item": f"option value {'rises' if expected_up else 'falls'} with {name}", "expected": "monotonic",
                       "observed": round(res[1] - res[0], 3), "status": "pass" if ok else "fail", "detail": "comparative statics"})
    # ---- link to deal justification (amended $38 offer)
    vo = pd.read_csv(PROC / "valuation_outputs.csv")
    sa = float(vo[(vo.perspective == PERSP) & (vo.method == "DCF") & vo.case.str.startswith("base") & (vo.metric == "equity_value")].value.iloc[0])
    syn = float(so[(so.perspective == PERSP) & (so.section == "Synergy value") & (so.case == "base") & (so.metric == "net_synergy_value")].value.iloc[0])
    paid = 38.0 * shares
    for lab, opt in (("without expansion option", 0.0), ("with expansion option (base)", bs),
                     ("with revenue synergies counted as certain (advisors' static view)", S)):
        o("Deal justification with option", lab, "value_created_vs_amended_38", sa + syn + opt - paid, "USD_m", "estimate",
          f"standalone {sa:,.0f} + net cost synergies {syn:,.0f} + option {opt:,.0f} - $38 x {shares:,.1f}m")
    return {"S": S, "K": K, "sigma": sigma, "r": r, "T": T, "bs": bs, "shares": shares, "vols": vols}
