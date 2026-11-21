# Synergy valuation methodology (Stage 4A)

Code: `src/valuation/synergy.py` (driver `build_stage4.py`). Outputs: `data/processed/synergy_assumptions.csv`,
`synergy_outputs.csv`. Checks: `synergy_*` in `verification_checks.csv`.

## 1. What management disclosed (every item quoted and page-checked by the build)

| Item | Disclosure | Source | Available |
|---|---|---|---|
| Run-rate cost synergies | "at least $2 billion in cost savings from efficiencies" | Disney press release (`DIS_8K_20171214_EX99_1`) | 14 Dec 2017 |
| | "$2.0 billion in anticipated run-rate cost synergies"; deal value 11.9x CY2018 EBITDA, **8.3x including** synergies | Investor call transcript (`DIS_425_20171215_CALL`) | 14/15 Dec 2017 |
| Timeline | "fully realize roughly $2.0 billion of cost synergies by 2021"; "we would start realizing savings in the first year" | same call | 14/15 Dec 2017 |
| | "approximately $2 billion in cost savings ... by 2021" (Disney board's reasons) | May 2018 proxy p.130 | 30 May 2018 |
| Sources of savings | "the overlap and the redundancies", domestic and international | Investor meeting transcript (`DIS_425_20171215_MEETING`) | 14/15 Dec 2017 |
| Accretion | accretive "before the impact of purchase accounting for the second fiscal year after the close"; the accretion math includes share repurchases | release; call | 14/15 Dec 2017 |
| Revenue synergies | **Not quantified publicly.** Disney management prepared internal estimates, which its advisors used ("cost and revenue synergies") | May 2018 proxy pp.144–145 | 30 May 2018 |
| Integration / restructuring costs | **Not disclosed** at either valuation date | | |
| *Subsequent:* severance | "on the order of $1.5 billion"; plan complete by end of fiscal 2021; $906m recorded in FY2019 | 10-Q Q2 FY2019 p.78; 10-K FY2019 p.51 | May / Nov 2019 |
| *Reference:* advisors' synergy value | Implied by the per-share DCF ranges (midpoints): cost synergies ≈ $11.00 per RemainCo share (May proxy p.145; 6.75–7.75%, g 0.75–1.25%, pre-TCJA taxes); revenue synergies ≈ $9.63 more. June proxy p.192: $13.50 and $10.75 | proxies | 30 May / 28 Jun 2018 |

The advisors' figures are a **cross-check only**, never an input. The annual synergy amounts, phasing and costs to
achieve behind them were not disclosed.

## 2. Model

Per perspective (A: 14 Dec 2017; B: 30 May 2018), using that perspective's Stage 3 WACC and tax rate:

```
cost synergies_t      = run-rate x phase-in_t x realization            (pre-tax; 100% incremental EBITDA margin)
integration costs_t   = run-rate x cost multiple x spend share_t        (one-time, pre-tax, tax-deductible)
after-tax synergy FCFF_t = (cost synergies_t - integration costs_t) x (1 - t)
PV = sum over Disney FY2019-FY2023 of FCFF_t x (1 + r)^-(mid-point of the post-close part of year t)
TV = after-tax synergies_FY2023 x (1 + g_s) / (r - g_s), discounted from 30 Sep 2023
net synergy value = PV(after-tax synergies) + PV(TV) - PV(after-tax integration costs)
```

* **Fiscal years:** Disney's, ending around 30 Sep. Assumed close: 15 Mar 2019 (estimate: the midpoint of "12–18 months"
  after 13 Dec 2017; actual close 20 Mar 2019). FY2019 counts only the period after closing.
* **No capex or working capital** is attached to cost synergies (overhead removal). This is an assumption.
* **Incremental margin:** $2.0bn equals about 8.9% of Disney's forecast FY2021 RemainCo revenue. Attributed to the acquired
  business alone, that is a ~9pp EBITDA-margin uplift (from ~24%: FY2021 forecast EBITDA 5,348 / revenue 22,488). This is why the guidance looked high relative to the
  acquired EBITDA (the analyst question in the meeting transcript).

### Scenarios (estimates; base = management guidance)

| | Run-rate | Phase-in (FY2019 / 20 / 21 / 22+) | Synergy growth after run-rate | Integration costs |
|---|---|---|---|---|
| Bear | $1.5bn (75%) | 0 / 25% / 50% / 100% (one year late) | 0% | 1.5x run-rate (overrun) |
| **Base** | **$2.0bn** | **10% / 50% / 100% / 100%** | **1.0%** | **1.0x run-rate** |
| Bull | $2.5bn ("at least" exceeded) | 25% / 75% / 100% / 100% | 2.0% | 0.75x run-rate |

Integration spend: 50% / 40% / 10% in FY2019 / FY2020 / FY2021 (estimate, front-loaded). Probability of realization:
bear 25% / base 50% / bull 25% gives a probability-weighted value (estimate). Sensitivities: discount rate +1pp/+2pp,
realization 0–125%, integration cost 0.75–2.0x, synergy growth 0–2%.

### Discount rate
The base case uses the **standalone RemainCo WACC** (A 6.04%, B 6.86%):
* Cost synergies here are mainly the removal of duplicate overhead. Disney controls them, and their execution risk is
  similar to the operating cash flows they come from.
* Disney's own advisors discounted RemainCo and the synergies at the same rate.

Risk is handled through the scenarios and realization probabilities rather than an arbitrary rate premium. The +1pp/+2pp
sensitivities show the effect of a higher rate. Revenue synergies, if modelled, would warrant a higher rate; they are
not modelled.

### Avoiding double counting
* **Standalone excludes synergies.** The Stage 3 forecasts (Disney's forecasts for RemainCo) are standalone. The proxy
  states the advisors combined them with the separately prepared "synergy estimates" (p.145). The Stage 3 terminal value
  is likewise standalone.
* **Sky synergies are not included.** The 21CF forecast table that includes small Sky synergies ($25m/$50m) relates to
  Sky and is not used anywhere.
* **Corporate overhead risk.** The RemainCo standalone figures carry all 21CF corporate costs, because New Fox was removed
  without allocations. Some of the overhead Disney "saves" might have moved to New Fox anyway (estimated at $275–350m of
  New Fox corporate costs a year). Counting all $2.0bn as incremental to RemainCo standalone could therefore overstate
  synergies by up to roughly that amount, which is one reason for the bear case.
* **Dis-synergies not modelled.** Management said its long-term modelling also built in higher production investment and
  forgone third-party licensing as Disney moved to its own streaming services (meeting transcript). These are not
  quantified and not modelled.

## 3. Deal justification

Premium over standalone = consideration per 21CF share − Stage 3 standalone equity value per share (acquired business
only). Coverage = net synergy value ÷ premium. Value created for Disney = standalone equity + net synergies −
consideration. Considerations used:
* A: the original offer at the 13 Dec 2017 close ($29.54);
* B: the original offer at the 30 May 2018 close (0.2745 × $99.98 = $27.44), and, labelled subsequent, the amended $38.00.

This intrinsic premium is the like-for-like measure for the acquired business. The market premium over 21CF's
unaffected price (Stage 3) is not, because 21CF's share price also included New Fox.

## 4. Limitations
* Synergy phasing, integration costs and revenue synergies are estimates; only the run-rate and the target year are guidance.
* The synergies are pre-TCJA management numbers. Applying the 22% post-reform tax rate at B raises their after-tax value.
* Synergies are attributed to the acquired business. In practice some savings fall in Disney's own cost base, which makes
  no difference to value.
* The ex-ante integration cost (1.0x) is above the later severance estimate ($1.5bn, 0.75x), but "other costs" such as
  lease terminations were not estimated by Disney either.
