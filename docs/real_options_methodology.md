# Real options methodology (Stage 5A)

Code: `src/valuation/options.py` (pricing functions), `real_options.py`, `build_stage5.py`.
Outputs: `data/processed/real_options_inputs.csv`, `real_options_outputs.csv`, `binomial_convergence.csv`;
chart `docs/figures/09_option_binomial_convergence.png`. Checks: `realoption_*`.

## 1. Relation to the original notebook
`notebooks/MA_Real_Options_Valuation.ipynb` is **unchanged**. Its `black_scholes_call`, `binomial_call` (CRR, European or
American) and `simulate_gbm_paths` are reused in `options.py` with the same signatures. The one extension is an optional
continuous yield `q` (Merton 1973 / CRR with yield). With q = 0 the functions reproduce the original exactly. The
illustrative inputs (S = 30.25, K = 25, σ = 35%, …) are replaced by the Disney–21CF inputs below.

## 2. Which option, and why
* **Cost synergies (~$2.0bn run-rate)** are guidance that management committed to. They are valued as expected cash flows in
  Stage 4, not as an option.
* **Revenue synergies** were valued by Disney's advisors ("Stand-Alone + Cost and Revenue Synergies", May 2018 proxy p.145)
  but never quantified or committed to by Disney. Capturing them needs further investment: management described more
  production spending and pulling content from third parties for its own streaming services (Dec 2017 investor-meeting
  transcript). Disney can invest if the opportunity turns out well and walk away if it doesn't. That is a **call option to expand**.
* **Perspective B (30 May 2018):** the first date with any public revenue-synergy information. No option is valued at A,
  because nothing was disclosed.

## 3. Parameters

| | Value | Basis | Type |
|---|---|---|---|
| **S** underlying | $18,010m | Advisors' implied revenue-synergy value: midpoint of "+ cost and revenue" minus midpoint of "+ cost only", $9.625 per RemainCo share × 1,871.1m fully diluted shares. Range from the low/high ends: $15.4–20.6bn | derived from disclosed ranges |
| **K** exercise cost | $18,010m (= S) | The investment needed is not disclosed. At the money means the static NPV is zero, so the option value isolates the value of flexibility. Range K/S 0.75–1.25 | **estimate** |
| **σ** volatility | 13.8% | Median of peer asset volatilities: 2-year weekly equity vol (annualized) × E/(D+E), for Comcast 13.8%, AMC Networks 13.7%, Netflix 38.5% (Disney 13.8%, reference). Revenue synergies are probably riskier than the average media asset; ±10pp sensitivity | derived (market data) |
| **T** maturity | 3.0 years | To fiscal 2021, when management expected synergies to be fully realized. Range 1–5 years | estimate |
| **r** risk-free | 2.53% | FRED DGS3 (3-year Treasury) on 30 May 2018 | market |
| **q** leakage | 0% base; 3% alternative | Value lost each year Disney waits (competitors, Netflix). With q > 0 early exercise can be optimal, so American > European | estimate |

## 4. Methods and checks
* **Black-Scholes(-Merton)** closed form, plus put-call parity and price-bound checks.
* **CRR binomial**, European and American, n = 10 to 5,000 steps. At n = 5,000 the European price is within 0.004% of
  Black-Scholes. American equals European when q = 0. With q = 3% (n = 2,000) the European tree matches Merton within 0.1%
  and the American price exceeds it (an early-exercise premium of $56m).
* **Monte Carlo** (400,000 antithetic risk-neutral paths, fixed seed): within 3 standard errors of Black-Scholes, and
  identical on re-run.
* **Comparative statics:** value rises with σ, T, S and r, and falls with K and q (all checked).
* **Scenarios** (American CRR, n = 2,000), checked to be ordered bear < base < bull:
  * bear: S low, σ − 10pp, T = 2, q = 3%;
  * base;
  * bull: S high, σ + 10pp, T = 4.

## 5. Interpretation and limitations
* **Flexibility value, not synergy value.** The option is worth about **$2.4bn ($1.28 per 21CF share)**, far less than the
  $18bn a static DCF would add if revenue synergies were treated as certain and free. The option view prices only the right
  to invest; the $18bn assumes the investment is costless.
* **S comes from advisors' ranges.** They used pre-tax-reform taxes, discounted to December 2017, and the cash flows behind
  them were not disclosed. S is not re-estimated.
* **K is unknown.** The value is very sensitive to moneyness ($0.8bn at K/S = 1.25; $5.6bn at 0.75).
* **σ is an asset-volatility proxy.** It comes from peers' equity volatility, de-levered by multiplying by E/V, which
  ignores debt volatility. Using that approximation is a judgement call.
* **Single European/American call.** Real expansion is a sequence of staged investments (a compound option). Volatility
  and the underlying follow GBM: no jumps (e.g. regulatory or technology shocks), constant σ. These are the same
  limitations listed in the original README.
* **Not risk-adjusted for execution or competition** beyond the q case.
