"""Stage 5B: Monte Carlo simulation of the value Disney created (perspective B, 30 May 2018 information set).

Per draw:
  standalone equity  = Stage 3 base DCF (Disney forecasts for RemainCo), re-run with a revenue-growth shift and an
                       EBITDA-margin shift, then the same enterprise-to-equity bridge as Stage 3
  net cost synergies = Stage 4 base synergy model, re-run with realization %, delay and integration-cost multiple
  value created      = standalone equity + net synergies (+ expansion option value, optional) - consideration

Both engines are vectorised re-implementations of src/valuation/dcf.py (as used in build_valuation.py) and
src/valuation/synergy.py. With all shocks at zero they must reproduce the Stage 3 base EV and the Stage 4 base net
synergy value exactly; this is checked on every run.

Distributions (all estimates, anchored to the Stage 3/4 ranges):
  synergy realization       Triangular(min 0.50, mode 1.00, max 1.25)   [Stage 4 bear 75%, bull 125%; tail to 50%]
  synergy delay (years)     0 / 1 / 2 with probabilities 60% / 30% / 10%
  integration cost multiple Triangular(0.75, 1.00, 2.00) x $2.0bn run-rate
  revenue growth shift      Normal(0, 1.0pp) per year, truncated at +/-3pp   [Stage 3 sensitivity range +/-2pp]
  EBITDA margin shift       Normal(0, 1.0pp), truncated at +/-3pp            [Stage 3 sensitivity range +/-2pp]
Variables are independent; correlations are not modelled (limitation). Fixed seed for reproducibility.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))
import dcf  # noqa: E402
import synergy as syn  # noqa: E402

PROC = ROOT / "data" / "processed"
PERSP = "B_proxy_2018-05"
VD = date(2018, 5, 30)
SEED = 20180530
N_DRAWS = 20_000
CHECKS = []

DIST = {
    "synergy_realization": ("triangular", 0.50, 1.00, 1.25),
    "synergy_delay_years": ("discrete", {0: 0.60, 1: 0.30, 2: 0.10}),
    "integration_cost_multiple": ("triangular", 0.75, 1.00, 2.00),
    "revenue_growth_shift": ("normal_truncated", 0.0, 0.01, -0.03, 0.03),
    "ebitda_margin_shift": ("normal_truncated", 0.0, 0.01, -0.03, 0.03),
}


def chk(item, expected, observed, tol, ctype="montecarlo_consistency", detail=""):
    CHECKS.append({"check_type": ctype, "entity": "Disney / RemainCo", "source_id": "", "fiscal_period": PERSP, "item": item,
                   "expected": round(float(expected), 6), "observed": round(float(observed), 6),
                   "status": "pass" if abs(float(expected) - float(observed)) <= tol else "fail", "detail": detail})


class Model:
    """Vectorised Stage 3 (B, Disney forecasts) DCF and Stage 4 synergy model."""

    def __init__(self):
        A = pd.read_csv(PROC / "dcf_assumptions.csv")
        a = lambda p: float(A[(A.perspective == PERSP) & (A.parameter == p)].value.iloc[0])
        self.wacc, self.tax, self.g = a("wacc"), a("marginal_tax_rate"), a("terminal_growth")
        self.da_pct, self.capex_pct = a("da_pct_revenue"), a("capex_pct_revenue")
        self.shares = a("shares_fully_diluted_m")
        F = pd.read_csv(PROC / "management_forecasts.csv")
        F = F[F.forecast_set == "disney_for_remainco_original"].pivot_table(index="fiscal_year", columns="metric", values="value")
        F = F.sort_index()
        self.fy = list(F.index)
        R, E, U = F.revenue.values, F.ebitda.values, F.unlevered_fcf.values
        da, capx = self.da_pct * R, self.capex_pct * R
        nopat = (E - da) * (1 - self.tax)
        resid = nopat + da - capx - U
        self.R, self.margin, self.resid_pct = R, E / R, resid / R
        sel = [i for i, y in enumerate(self.fy) if "2024" <= y[:4] <= "2028"]
        self.conv = U[sel].sum() / E[sel].sum()
        # timing from the Stage 3 engine (fractions after the valuation date, mid-period discount times)
        ys = [dcf.Year(f"FY{y[:4]}", date(int(y[:4]) - 1, 7, 1), date(int(y[:4]), 6, 30), R[i], E[i], da[i], capx[i], resid[i], self.tax)
              for i, y in enumerate(self.fy)]
        base = dcf.value(ys, VD, self.wacc, self.g, E[-1] * self.conv)
        self.frac = np.array([r["fraction_after_valuation_date"] for r in base["table"]])
        self.t = np.array([r["discount_time_years"] for r in base["table"]])
        self.t_n = base["terminal_discount_time_years"]
        assert len(self.frac) == len(R)
        # exponent used by Stage 3 for revenue-growth shifts (FY2018 unchanged, later years (1+s)^(i+1))
        self.k_exp = np.array([0 if y.startswith("2018") else i + 1 for i, y in enumerate(self.fy)])
        # bridge (Stage 3 B base rows)
        O = pd.read_csv(PROC / "valuation_outputs.csv")
        b = O[(O.perspective == PERSP) & (O.method == "Bridge")].set_index("metric").value.astype(float)
        self.bridge = b["plus_sky_39pct_stake"] + b["plus_other_investments_book"] - b["less_debt"] + b["plus_cash"] - b["less_noncontrolling_interests"]
        self.stage3_ev = float(O[(O.perspective == PERSP) & (O.method == "DCF") & O.case.str.startswith("base") &
                                 (O.metric == "enterprise_value_ops")].value.iloc[0])
        S4 = pd.read_csv(PROC / "synergy_outputs.csv")
        self.stage4_net = float(S4[(S4.perspective == PERSP) & (S4.section == "Synergy value") & (S4.case == "base") &
                                   (S4.metric == "net_synergy_value")].value.iloc[0])
        # synergy timing (Disney FY) from the Stage 4 module
        sc = syn.SCENARIOS["base"]
        self.syn_years = list(syn.FY)
        self.phase = np.array([sc["phase"][y] for y in self.syn_years])
        self.ic_phase = np.array([syn.IC_PHASE[y] for y in self.syn_years])
        self.run_rate, self.g_syn = sc["run_rate"], sc["g"]
        st = []
        for y in self.syn_years:
            start = max(syn.FY_START[y], syn.CLOSE)
            mid = start + (syn.FY[y] - start) / 2
            st.append((mid - VD).days / 365.25)
        self.syn_t = np.array(st)
        self.syn_tn = (syn.FY[2023] - VD).days / 365.25

    def standalone_equity(self, gshift, mshift):
        gshift, mshift = np.atleast_1d(gshift)[:, None], np.atleast_1d(mshift)[:, None]
        R = self.R[None, :] * (1 + gshift) ** self.k_exp[None, :]
        E = (self.margin[None, :] + mshift) * R
        da = self.da_pct * R
        fcff = (E - da) * (1 - self.tax) + da - self.capex_pct * R - self.resid_pct[None, :] * R
        df = (1 + self.wacc) ** -self.t
        pv = (fcff * self.frac[None, :] * df[None, :]).sum(axis=1)
        tv = E[:, -1] * self.conv * (1 + self.g) / (self.wacc - self.g)
        ev = pv + tv * (1 + self.wacc) ** -self.t_n
        return ev, ev + self.bridge

    def net_synergies(self, realization, delay, ic_mult):
        realization, delay, ic_mult = (np.atleast_1d(x).astype(float) for x in (realization, delay, ic_mult))
        n = len(realization)
        idx = np.arange(len(self.syn_years))[None, :] - delay[:, None].astype(int)
        phase = np.where(idx >= 0, self.phase[np.clip(idx, 0, None)], 0.0)
        syn_pre = self.run_rate * phase * realization[:, None]
        ic_pre = self.run_rate * ic_mult[:, None] * self.ic_phase[None, :]
        df = (1 + self.wacc) ** -self.syn_t
        pv_s = (syn_pre * (1 - self.tax) * df).sum(axis=1)
        pv_ic = (ic_pre * (1 - self.tax) * df).sum(axis=1)
        last = syn_pre[:, -1] * (1 - self.tax)
        tv = last * (1 + self.g_syn) / (self.wacc - self.g_syn) * (1 + self.wacc) ** -self.syn_tn
        return pv_s + tv - pv_ic


def draw(n, seed):
    rng = np.random.default_rng(seed)
    out = {}
    for k, spec in DIST.items():
        if spec[0] == "triangular":
            out[k] = rng.triangular(spec[1], spec[2], spec[3], n)
        elif spec[0] == "discrete":
            vals, p = zip(*spec[1].items())
            out[k] = rng.choice(vals, size=n, p=p)
        else:
            _, mu, sd, lo, hi = spec
            x = rng.normal(mu, sd, n)
            out[k] = np.clip(x, lo, hi)
    return out


def simulate(model, n=N_DRAWS, seed=SEED, option_value=0.0):
    d = draw(n, seed)
    ev, eq = model.standalone_equity(d["revenue_growth_shift"], d["ebitda_margin_shift"])
    ns = model.net_synergies(d["synergy_realization"], d["synergy_delay_years"], d["integration_cost_multiple"])
    df = pd.DataFrame(d)
    df["enterprise_value_ops"] = ev
    df["standalone_equity"] = eq
    df["net_synergy_value"] = ns
    df["total_value_to_disney"] = eq + ns
    df["total_value_incl_option"] = eq + ns + option_value
    return df


def summarize(df, model, considerations):
    rows = []
    def stats(name, x, unit="USD_m"):
        x = np.asarray(x)
        rows.append({"metric": name, "unit": unit, "mean": x.mean(), "std": x.std(ddof=1), "se_mean": x.std(ddof=1) / np.sqrt(len(x)),
                     "p05": np.percentile(x, 5), "p25": np.percentile(x, 25), "p50": np.percentile(x, 50),
                     "p75": np.percentile(x, 75), "p95": np.percentile(x, 95), "min": x.min(), "max": x.max(),
                     "prob_positive": (x > 0).mean(), "n": len(x)})
    for c in ("standalone_equity", "net_synergy_value", "total_value_to_disney", "total_value_incl_option"):
        stats(c, df[c])
        stats(c + "_per_share", df[c] / model.shares, "USD_per_share")
    for lab, paid in considerations.items():
        stats(f"value_created_vs_{lab}", df["total_value_to_disney"] - paid)
        stats(f"value_created_incl_option_vs_{lab}", df["total_value_incl_option"] - paid)
        stats(f"synergy_coverage_of_premium_vs_{lab}", df["net_synergy_value"] / (paid - df["standalone_equity"]), "ratio")
    return pd.DataFrame(rows)
