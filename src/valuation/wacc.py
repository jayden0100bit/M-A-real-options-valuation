"""WACC from dated market inputs and peer betas.

Beta method: 2-year weekly (Friday close) simple returns of each peer against the S&P 500, ending on the
market-data date; Blume adjustment (0.67 x raw + 0.33). Each peer beta is unlevered with Hamada using its
market D/E on the date and the valuation's marginal tax rate. The median unlevered beta is relevered at the
target D/E (median peer market D/(D+E)).
"""
from __future__ import annotations

import numpy as np

from market_data import weekly_returns


def regression_beta(ticker, end, years=2):
    r = weekly_returns(ticker, end, years)
    m = weekly_returns("^GSPC", end, years).reindex(r.index).dropna()
    r = r.reindex(m.index)
    raw = float(np.cov(r, m)[0, 1] / np.var(m, ddof=1))
    return raw, 0.67 * raw + 0.33, len(m)


def unlever(beta_l, d_e, tax):
    return beta_l / (1 + (1 - tax) * d_e)


def relever(beta_u, d_e, tax):
    return beta_u * (1 + (1 - tax) * d_e)


def compute(rf, erp, kd_pre, tax, peer_rows, market_date):
    """peer_rows: list of dicts with ticker, debt, market_cap. Returns dict with all intermediate values."""
    betas = []
    for p in peer_rows:
        raw, adj, n = regression_beta(p["ticker"], market_date)
        de = p["debt"] / p["market_cap"]
        betas.append({"ticker": p["ticker"], "raw_beta": raw, "adjusted_beta": adj, "weeks": n, "d_e": de,
                      "d_v": p["debt"] / (p["debt"] + p["market_cap"]), "unlevered_beta": unlever(adj, de, tax)})
    bu = float(np.median([b["unlevered_beta"] for b in betas]))
    dv = float(np.median([b["d_v"] for b in betas]))
    de = dv / (1 - dv)
    bl = relever(bu, de, tax)
    ke = rf + bl * erp
    kd_after = kd_pre * (1 - tax)
    wacc = (1 - dv) * ke + dv * kd_after
    return {"peer_betas": betas, "unlevered_beta_median": bu, "target_d_v": dv, "target_d_e": de, "relevered_beta": bl,
            "rf": rf, "erp": erp, "cost_of_equity": ke, "kd_pretax": kd_pre, "tax": tax, "kd_aftertax": kd_after,
            "weight_equity": 1 - dv, "weight_debt": dv, "wacc": wacc}
