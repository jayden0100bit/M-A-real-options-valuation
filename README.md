# M&A Valuation using Real Options

A personal project, not a class assignment. I got curious about one of
those classic M&A questions: if you're acquiring a company with potential
synergies (that aren't guaranteed to happen), how much extra should you
actually be willing to pay?

I'm currently studying Statistics, so when I came
across **real options** and found out they can be valued with
Black-Scholes, I got interested in connecting it with stuff from my stats
knowlegde — lognormal distributions, Monte Carlo simulation, a bit of
stochastic processes. So this notebook ends up being somewhere between a
finance topic and a statistics exercise I did for fun, not a fully
polished professional finance analysis.

Two questions I tried to answer:

1. What's a reasonable **added value** to pay now, as the "price" of the
   option to expand later through synergies (e.g. cross-selling the
   target's products to our customers)?
2. If the seller asks for a higher price, how do you structure an
   **earn-out** (paying the rest later if targets are hit) so the numbers
   aren't just pulled out of thin air?

## Methods used

| Stage | Method | Purpose |
|---|---|---|
| 1 | DCF (Discounted Cash Flow) | Base valuation of the target, no synergies yet |
| 2 | Black-Scholes (call option) | Estimate the value of the expansion option from synergies |
| 3 | Binomial tree (CRR) | Manual cross-check, so I'm not just trusting one formula |
| 4 | Monte Carlo (Geometric Brownian Motion) | Simulate the probability of hitting the earn-out |
| 5 | Sensitivity matrix | Test how shaky the result is when assumptions change |

Main formula used:

```
NPV_total = NPV_standalone + C(S, K, r, T, sigma)
```

Honestly, I understand stages 3–5 better (the simulation/statistics-heavy
parts), while stages 1–2 (DCF & Black-Scholes) leaned more on following
the logic from finance textbooks/resources online rather than full
intuition on my end.

## Results (illustrative assumptions, not real data)

| Metric | Value | Notes |
|---|---|---|
| Base DCF | $100.0M | Standalone valuation of the target |
| Expansion Option Value | $11.05M | From Black-Scholes call `C(S, K, r, T, sigma)` |
| **Total Acquisition Price** | **$111.05M** | Base DCF + option value |
| Expansion Capex (Strike K) | $25.0M | Investment needed to unlock the synergy |
| Probability Earn-Out is Hit | ~72% | From Monte Carlo simulation, 10,000 scenarios |

> All numbers above are **illustrative assumptions** for the exercise, not
> derived from a real company's financials. Swap in your own inputs if you
> want to use this for an actual case.

## Folder contents

```
M-A-real-options-valuation/
├── notebooks/
│   └── MA_Real_Options_Valuation.ipynb   # main notebook
├── requirements.txt
├── .gitignore
├── LICENSE
└── README.md
```

## How to run it

```bash
git clone https://github.com/jayden0100bit/M-A-real-options-valuation.git
cd M-A-real-options-valuation
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
jupyter notebook notebooks/MA_Real_Options_Valuation.ipynb
```

The notebook has already been run once (so the numbers and charts show up
directly on GitHub without re-running), but it can be re-run from scratch
if you want to play around with the assumptions.

## What's inside the notebook

1. **Standalone DCF** — 5-year FCF projection, discounted with WACC, plus
   terminal value.
2. **Black-Scholes** — calculates the expansion option value; `d1`/`d2`
   are shown on purpose so the steps are visible (also mostly for my own
   sake, so I don't forget the flow when I look back at it).
3. **Binomial tree** — manual cross-check (European or American option),
   plus a convergence chart showing it lines up with Black-Scholes.
4. **Monte Carlo earn-out** — 10,000 simulations to estimate the
   probability of hitting the earn-out and the expected cost.
5. **Sensitivity matrix** — heatmap of total acquisition price as
   volatility and integration speed are varied.
6. **Final summary** — charts + tables, mostly to wrap things up neatly.

## If you want to change the assumptions

All inputs are in clearly named variables in each section:

- `fcff_forecast`, `wacc`, `terminal_growth` → replace with the actual
  target's data.
- `S_synergy`, `K_capex`, `sigma_synergy`, `T_years`, `r_rf` → adjust to
  the relevant synergy estimate, capex, volatility, and interest rate.
- `hurdle`, `earn_out_bonus`, `mu_drift` → adjust to match whatever
  earn-out structure is being negotiated/discussed.

## Limitations & possible extensions

This is a first pass, not a finished model. Some known gaps if I (or
anyone else) wanted to take it further:

- **Constant volatility** is the biggest simplification — real synergy
  realization is path-dependent and volatility isn't actually constant
  over time. A stochastic volatility model (e.g. Heston) would be more
  realistic.
- **No jumps** — GBM assumes continuous price paths, but real M&A
  outcomes (regulatory approval, key customer churn, etc.) can move in
  discrete jumps. A jump-diffusion model (Merton) could capture that.
- **Single expansion option** — in practice, an acquirer often holds a
  sequence of options (compound options), not just one shot at expansion.
- **No real deal validated against it yet** — everything here runs on
  illustrative inputs. Testing it against a real (public) M&A deal with
  actual historical volatility would be the next natural step.

## Important notes

- This is a **self-directed learning project**, not a professional
  valuation. I'm a statistics student exploring finance out of curiosity,
  not a finance/accounting major, so the corporate finance assumptions
  (WACC, terminal growth, etc.) are pulled from textbook/online examples
  rather than deep research.
- Black-Scholes assumes lognormal returns and constant volatility — in
  reality, M&A synergies are a lot messier than that, so the numbers here
  are just rough estimates for practicing the concept.
- Volatility (`sigma`) is the most sensitive input (clearly visible in the
  sensitivity matrix) — don't just guess a number; ideally it should come
  from the historical volatility of comparable companies.
- If anyone has feedback or corrections (especially on the finance side),
  I'd genuinely appreciate it — still learning, and this was mostly built
  out of curiosity about where stats and finance overlap.

## License

MIT — see [LICENSE](LICENSE).
