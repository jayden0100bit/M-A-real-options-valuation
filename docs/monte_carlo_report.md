# Monte Carlo and real options report (Stage 5)

*Information set: May 2018 joint proxy (perspective B). Built on the Stage 1–4 outputs, which are unchanged. USD
millions unless stated. Every distribution is a labelled estimate (`monte_carlo_inputs.csv`). Method:
[`real_options_methodology.md`](real_options_methodology.md), `src/valuation/monte_carlo.py`.*

## 1. Simulation design

| Input | Distribution | Anchor |
|---|---|---|
| Synergy realization | Triangular(0.50, 1.00, 1.25) × $2.0bn run-rate | Stage 4 bear 75% / base 100% / bull 125%; lower tail to 50% |
| Synergy delay | 0 / 1 / 2 years with 60% / 30% / 10% | Stage 4 bear is one year late |
| Integration-cost multiple | Triangular(0.75, 1.00, 2.00) × run-rate | Stage 4 range; Disney's later severance estimate is 0.75x |
| Revenue-growth shift | Normal(0, 1pp) a year, truncated ±3pp | Stage 3 sensitivity ±2pp |
| EBITDA-margin shift | Normal(0, 1pp), truncated ±3pp | Stage 3 sensitivity ±2pp |

Each draw re-runs the Stage 3 DCF of the acquired business (Disney's forecasts) and its enterprise-to-equity bridge, plus
the Stage 4 synergy model. The draws are compared with two prices: the **amended $38 offer** ($71,104m) and the
**original offer valued at the 30 May 2018 close** ($51,353m).

## 2. Results (20,000 draws, seed 20180530)

| Per 21CF share | Mean | p5 | Median | p95 |
|---|---|---|---|---|
| Standalone equity value | $26.36 | $21.71 | $26.22 | $31.42 |
| Net cost-synergy value | $10.19 | $6.74 | $10.35 | $13.19 |
| **Total value to Disney** | **$36.54** | $30.86 | $36.45 | $42.58 |
| Total incl. expansion option (+$1.28) | $37.82 | $32.14 | $37.73 | $43.85 |

| Value created for Disney (USD m) | Mean | p5 | Median | p95 | **P(value created > 0)** |
|---|---|---|---|---|---|
| vs amended $38 offer | −2,725 | −13,357 | −2,893 | +8,563 | **33.5%** |
| vs amended $38 offer, incl. expansion option | −335 | −10,968 | −504 | +10,953 | **46.9%** |
| vs original offer (30 May 2018 value) | +17,026 | +6,394 | +16,858 | +28,314 | **99.7%** |

* **Simulated mean below the deterministic base.** The simulated mean value is $2.6bn below the Stage 4 deterministic base
  (−$96m). The distributions are skewed against Disney: realization averages 92%, delays only push synergies later, and
  integration-cost overruns are more likely than savings.
* **Synergy coverage of the $38 premium:** median 0.87x, 5th–95th percentile 0.52–1.65x. The mean is not meaningful,
  because some draws have a premium close to zero.
* **Original vs amended offer.** The original offer was value-creating in almost every scenario. At $38, Disney needed
  base-case-or-better execution, or the strategic option, to break even.

### Drivers (one at a time, inputs at their 5th / 95th percentile)

| Input | Value created vs $38 (USD bn) | Swing |
|---|---|---|
| Revenue-growth shift (±1.6pp) | −7.3 → +8.2 | 15.5 |
| Synergy realization (64% → 115%) | −8.6 → +3.5 | 12.0 |
| EBITDA-margin shift (±1.6pp) | −4.7 → +4.6 | 9.2 |
| Synergy delay (0 → 2 years) | −0.1 → −2.7 | 2.6 |
| Integration-cost multiple (0.88x → 1.75x) | +0.1 → −1.2 | 1.2 |

Growth of the acquired business and synergy delivery dominate. One-off integration costs barely matter.

### Scenarios: deterministic vs simulated
| | Net synergies | Value created vs $38 |
|---|---|---|
| Stage 4 bear / base / bull (standalone at base) | 12,894 / 21,947 / 33,721 | −9,149 / −96 / +11,679 |
| Monte Carlo p5 / p50 / p95 | 12,602 / 19,375 / 24,682 | −13,357 / −2,893 / +8,563 |

The simulated median lies between the deterministic bear and bull cases (checked). The simulated p95 synergy value is
below the deterministic bull case, because the bull case assumes a $2.5bn run-rate and the simulation caps realization at 125%.

## 3. Real option
* **Base value:** the revenue-synergy expansion option (S = K = $18.0bn, σ 13.8%, T 3 years, r 2.53%) is worth **$2,389m**
  by Black-Scholes. CRR gives $2,389.3m at 5,000 steps and Monte Carlo $2,394m ± 5.
* **With 3% leakage:** European $1,461m, American $1,517m (an early-exercise premium of $56m).
* **Scenarios:** bear ≈ $0 (out of the money, low volatility), base $2.4bn, bull $6.0bn.
* **Sensitivities:**
  * K/S 0.75–1.25: $5.6bn – $0.8bn;
  * σ ±10pp: $1.4bn – $3.5bn;
  * T 1–5 years: $1.2bn – $3.3bn.
* **Deal effect at $38:** without the option, value created is −$0.1bn. With the base option it is +$2.3bn. With revenue
  synergies counted as certain and free (the advisors' static view) it would be +$17.9bn, which overstates value because
  it ignores the investment needed.

## 4. Validation (33 checks, all pass)
* **Consistency with earlier stages.** With all shocks at zero the vectorised engines reproduce:
  * the Stage 3 base EV (within $0.42m, because WACC is stored to 6 decimals);
  * the Stage 4 base net synergy value (exactly);
  * a Stage 4 realization sensitivity and a Stage 4 integration-cost sensitivity (exactly);
  * Stage 3's margin and growth sensitivities (within $0.5m).
* **Arithmetic and inputs:** the total = standalone + synergies identity holds in every draw, and every sampled input stays
  within its bounds.
* **Reproducibility and convergence:**
  * The same seed gives identical draws.
  * An independent seed agrees within 3 standard errors.
  * The standard error falls at about 1/√n (ratio 0.22 against a theoretical 0.224).
  * The standard error of the mean is about $47m.
* **Option checks:** put-call parity, price bounds, convergence of the binomial and Monte Carlo prices to Black-Scholes,
  American ≥ European, comparative statics, and ordered scenarios.

## 5. Limitations
1. **Distributions are judgement.** They are anchored to Stage 3/4 ranges but not estimated from data. Inputs are
   independent: no correlation between growth, margins and synergy delivery, which in reality tend to move together and
   would widen the tails.
2. **What is not simulated:** WACC, terminal growth, the bridge (e.g. the Sky stake) and the choice of forecast set. The
   biggest of these, Disney's vs 21CF's forecasts, is worth about $9/share (Stage 3).
3. **Hindsight is excluded.** Actual outcomes (COVID-19, Disney+ and Hulu investment, the actual realization of synergies)
   are not in the simulation.
4. **Option inputs** carry the limits in the methodology: S is advisor-derived, K is assumed at the money, σ is a peer
   proxy, and the option is a single option rather than a compound one.

## 6. Overall conclusion (Stages 3–5)
* **Price relative to value:** Disney's standalone value of the acquired business (~$26/share) plus committed cost
  synergies (~$10–12/share) is about $36–38 per share. That is almost exactly the $38 Disney paid after Comcast's
  counter-bid.
* **Who gained:** at $38, the cost synergies went to 21CF's shareholders.
* **The bet:** Disney's case rested on the strategic, option-like value of content for its own streaming services. That
  value is real but modest when priced as flexibility (~$2.4bn base), and highly uncertain (bear ≈ $0, bull ≈ $6bn).
* **The odds:** the probability that the deal created value at $38 is roughly 1 in 3 on cash flows alone, and about even
  including the option.
