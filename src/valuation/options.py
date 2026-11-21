"""Option-pricing building blocks.

``black_scholes_call``, ``binomial_call`` and ``simulate_gbm_paths`` are taken from the original illustrative notebook
(notebooks/MA_Real_Options_Valuation.ipynb, cells 6, 8 and 12). They have the same signatures, extended with an
optional continuous payout yield ``q`` (q = 0 reproduces the original exactly). The notebook itself is not modified.

With q > 0 these are the Merton (1973) generalisation and the CRR tree with yield. For a real option, q represents the
value that leaks away while the holder waits (cash flows forgone, competitive erosion). It is the only reason early
exercise of an American call can be optimal.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import norm


def black_scholes_call(S, K, r, T, sigma, q=0.0):
    """European call value plus (d1, d2). q = continuous payout/leakage yield (Merton)."""
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call, d1, d2


def black_scholes_put(S, K, r, T, sigma, q=0.0):
    c, d1, d2 = black_scholes_call(S, K, r, T, sigma, q)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


def binomial_call(S, K, r, T, sigma, n_steps=200, american=False, q=0.0):
    """Cox-Ross-Rubinstein tree (original notebook logic; growth term uses r - q)."""
    dt = T / n_steps
    u = np.exp(sigma * np.sqrt(dt))
    d = 1 / u
    p = (np.exp((r - q) * dt) - d) / (u - d)
    if not 0 < p < 1:
        raise ValueError(f"risk-neutral probability {p:.4f} outside (0,1): increase n_steps")
    disc = np.exp(-r * dt)
    j = np.arange(n_steps + 1)
    ST = S * (u ** j) * (d ** (n_steps - j))
    values = np.maximum(ST - K, 0.0)
    for step in range(n_steps - 1, -1, -1):
        values = disc * (p * values[1:] + (1 - p) * values[:-1])
        if american:
            j = np.arange(step + 1)
            St = S * (u ** j) * (d ** (step - j))
            values = np.maximum(values, St - K)
    return float(values[0])


def simulate_gbm_paths(E0, mu, sigma, T, n_steps, n_paths, seed=42):
    """Original notebook GBM path simulator (log-Euler, exact for GBM)."""
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    increments = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * rng.standard_normal((n_paths, n_steps))
    log_paths = np.log(E0) + np.cumsum(increments, axis=1)
    log_paths = np.hstack([np.full((n_paths, 1), np.log(E0)), log_paths])
    return np.exp(log_paths)


def mc_european_call(S, K, r, T, sigma, q=0.0, n_paths=200_000, seed=42):
    """Risk-neutral Monte Carlo price with antithetic variates; returns (price, standard error)."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(n_paths // 2)
    z = np.concatenate([z, -z])
    ST = S * np.exp((r - q - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * z)
    pay = np.exp(-r * T) * np.maximum(ST - K, 0.0)
    pair = 0.5 * (pay[: n_paths // 2] + pay[n_paths // 2:])
    return float(pay.mean()), float(pair.std(ddof=1) / np.sqrt(len(pair)))
