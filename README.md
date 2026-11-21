# M&A Valuation using Real Options

A personal project, not a class assignment. I got curious about one of
those classic M&A questions: if you're acquiring a company with potential
synergies (that aren't guaranteed to happen), how much extra should you
actually be willing to pay?

I'm currently studying Statistics, so when I came
across **real options** and found out they can be valued with
Black-Scholes, I got interested in connecting it with stuff from my stats
knowledge — lognormal distributions, Monte Carlo simulation, a bit of
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

## Case study in progress: Disney / 21st Century Fox

The next step (see *Limitations* below) is to run these methods on a real public deal: The Walt Disney
Company's acquisition of Twenty-First Century Fox (announced December 2017, amended June 2018, closed
March 2019). Stage 1, the **data layer**, is done. Historical financials and deal terms were collected from
SEC filings and checked against them. No valuation has been run on them yet.

| Deliverable | What it is |
|---|---|
| `data/raw/` | Original SEC filings (10-Ks FY2015-FY2018 for both companies, the 2017/2018 joint proxy statements, deal 8-Ks, Disney FY2019 10-K/10-Q) and SEC XBRL data, with SHA-256 hashes |
| `data/processed/historical_financials.csv` | Income statement, balance sheet, cash flow and segment data for Disney and 21CF, plus RemainCo (the 21CF business Disney actually bought) on a pro forma basis. USD millions, page-cited |
| `data/processed/transaction_assumptions.csv` | Original offer, amended offer, closing terms and purchase accounting, kept separate; each figure carries the quote it came from |
| `data/processed/source_register.csv` | Every source document with EDGAR URL and hash |
| `notebooks/01_data_collection.ipynb` | Runs the pipeline and walks through the data and the verification checks |
| `docs/data_dictionary.md`, `docs/data_collection_report.md` | Column definitions; method, fiscal-year issues, perimeter and limitations |

### Stage 2: historical financial analysis

Stage 2 works only from the verified data layer: it computes ratios and segment metrics and draws the charts. There
is still no valuation.

| Deliverable | What it is |
|---|---|
| `data/processed/financial_ratios.csv` | Growth, margins (EBIT/EBITDA derived on one definition for both companies), tax rates, ROA/ROE, leverage, working capital, cash flow and FCF for Disney, 21CF and RemainCo. Each row cites its inputs (record id, filing, page) and is labelled reported / derived / adjusted / not available |
| `data/processed/segment_analysis.csv` | Segment revenue, profit, margins and mix (Disney segment operating income; 21CF Segment OIBDA, flagged as *not* the acquired perimeter) |
| `notebooks/02_historical_analysis.ipynb` | Tables, charts and a traceability spot check |
| `docs/historical_analysis_report.md` | Findings, RemainCo analysis and its limitations, and possible allocation methods (none applied) |
| `docs/figures/` | Charts (USD m, fiscal-year end month shown on each axis) |

Headline: Disney earned a steady ~30% EBITDA margin. 21CF earned 21–24%. RemainCo, the business Disney actually
bought, earned ~20% on ~$19–21bn of pro forma revenue, but that figure still carries all 21CF corporate costs and
the regional sports networks Disney later sold. The sources contain no RemainCo cash-flow or capex data.

### Stage 3: valuation engine

A standalone valuation of the business Disney actually bought, at two dates with separate information sets:
**A** at the announcement (14 Dec 2017, estimates from public information only) and **B** at the May 2018 proxy
(using the management forecasts disclosed there). Also included: comparables, transaction analysis, sensitivities and
scenarios. Not included: synergies, accretion/dilution and real options.

| Deliverable | What it is |
|---|---|
| `src/valuation/` | forecast extraction, peer data, WACC, DCF engine (reusing the original notebook's DCF logic), bridge, transaction analysis, charts |
| `data/processed/management_forecasts.csv` | every 21CF and Disney forecast figure from the May and June 2018 proxies, with page, table and definition |
| `data/processed/dcf_assumptions.csv` | every input with value type (reported / forecast / market / derived / estimate), source and availability date |
| `data/processed/valuation_outputs.csv` | DCF, bridge, comparables, transaction and hindsight results |
| `data/processed/valuation_sensitivity.csv`, `dcf_projections.csv`, `comparable_companies.csv` | sensitivity grids, FCFF projections, peer data and multiples |
| `notebooks/03_dcf_valuation.ipynb`, `04_comparable_company_analysis.ipynb`, `05_transaction_analysis.ipynb` | walkthroughs |
| `docs/valuation_methodology.md`, `docs/valuation_report.md` | method and results |

Headline (per 21CF share, acquired business only): DCF **$29.08** at A and **$26.22** at B (Disney forecasts; $35.69 with
21CF's). The original offer was $28.00–29.54, the amended offer $38.00, and the unaffected price $24.74. Market data
(FRED, Damodaran, Yahoo Finance) is stored in `data/raw/market/` with URLs and hashes. All 910 checks pass.

### Stage 4: synergies and accretion / dilution

| Deliverable | What it is |
|---|---|
| `data/processed/synergy_assumptions.csv`, `synergy_outputs.csv` | Guidance-based cost-synergy model (bear/base/bull, integration costs, tax, discounting) and the premium-coverage analysis |
| `data/processed/accretion_dilution_inputs.csv`, `accretion_dilution_outputs.csv` | Disney EPS FY2020–22, standalone vs pro forma (adjusted and GAAP basis), financing variants and sensitivities |
| `notebooks/06_synergy_valuation.ipynb`, `07_accretion_dilution.ipynb` | Walkthroughs |
| `docs/synergy_methodology.md`, `accretion_dilution_methodology.md`, `stage4_analysis_report.md` | Method and findings |

Headline: base net synergy value is about $21–22bn ($11.2–11.7 per 21CF share), close to the value implied by Disney's
advisors. Base synergies cover the original offer's small premium over standalone value many times over, but only about
1.0x for the amended $38 offer. Adjusted EPS is about −1% in FY2021 against management's "accretive in year two" (−15% on a
GAAP basis).

### Stage 5: real options and Monte Carlo

The original illustrative notebook is left unchanged. Its Black-Scholes, CRR binomial and GBM functions are reused
(`src/valuation/options.py`) with Disney–21CF inputs.

| Deliverable | What it is |
|---|---|
| `notebooks/08_real_options.ipynb`, `docs/real_options_methodology.md` | Revenue-synergy expansion option: Black-Scholes, CRR (European/American), Monte Carlo cross-check, scenarios |
| `notebooks/09_monte_carlo.ipynb`, `docs/monte_carlo_report.md` | 20,000-draw simulation of standalone value, synergy delivery and value created vs price paid |
| `data/processed/real_options_*.csv`, `binomial_convergence.csv`, `monte_carlo_*.csv` | Inputs, outputs, draws, convergence, tornado, scenarios |
| `docs/figures/09-11` | Binomial convergence, value-created distribution, driver tornado |

Headline: the expansion option is worth about $2.4bn ($1.28/share; bear ≈ $0, bull ≈ $6.0bn). The probability that the
deal created value at $38 is about 34% on cash flows alone and 47% including the option, against 99.7% at the original
offer's value.

Rebuild everything from the stored filings with `python src/run_pipeline.py --offline`. Leave out `--offline`
to download from EDGAR (set `SEC_USER_AGENT` first; see `data/raw/README.md`).

### Interactive dashboard

`dashboard/` is a static React + TypeScript + Tailwind CSS site (Vite, Recharts) that presents all five stages
as an interactive case study in five sections: **Deal Overview** (perimeter, price stages, timeline; historical
financials in an expandable note), **Valuation** (live DCF, comparables football field, clickable WACC × growth
heatmap, EV-to-equity bridge), **Synergies & EPS** (synergy value, premium coverage, accretion/dilution with a shared
realization input), **Risk & Real Options** (Black-Scholes, binomial tree, live Monte Carlo explorer) and
**Conclusion & Methodology** (verdict, key assumptions, validation and sources). Finance terms carry plain-English
definitions and detailed tables sit in expandable technical notes. It has no backend and no database.

- **Data:** the last pipeline step, `src/export_dashboard.py`, writes `dashboard/public/data/dashboard.json`
  (about 210 KB) from the processed outputs. It refuses to export if any verification check fails. Raw filings
  are not shipped with the site.
- **Browser calculations:** the DCF, synergy, accretion/dilution, Black-Scholes, CRR and Monte Carlo models are
  re-implemented in `dashboard/src/lib/finance.ts`. `npm test` checks them against the pipeline outputs.

```bash
cd dashboard
npm install
npm run dev        # local development
npm test           # engine reproduces the Python results
npm run build      # production build -> dashboard/dist
```

To deploy on Vercel, import the repository and set **Root Directory** to `dashboard`, or run `npx vercel --prod`
from `dashboard/`. `dashboard/vercel.json` sets the Vite framework, the build command and `dist` as the output directory.

## Folder contents

```
M-A-real-options-valuation/
├── notebooks/
│   ├── MA_Real_Options_Valuation.ipynb   # original illustrative valuation notebook
│   └── 01_…09_*.ipynb                    # Disney/21CF case study, stages 1-5
├── src/                                  # data pipeline (fetch, parse, build, verify) + valuation/
├── dashboard/                            # static React dashboard (Vercel)
├── data/
│   ├── raw/                              # unmodified SEC filings + XBRL JSON
│   ├── reference/filings_to_fetch.csv    # list of filings to download
│   └── processed/                        # clean datasets + verification_checks.csv
├── docs/                                 # methodology and analysis reports, figures
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

- **Constant volatility** is a simplification — real synergy
  realization is path-dependent and volatility isn't actually constant
  over time. A stochastic volatility model would be more
  realistic.
- **No jumps** — GBM assumes continuous price paths, but real M&A
  outcomes (regulatory approval, key customer churn, etc.) can move in
  discrete jumps. 
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
- Black-Scholes assumes lognormal returns and constant volatility. In
  reality, M&A synergies are a lot messier than that, so the numbers here
  are just rough estimates for practicing the concept.
- Volatility (`sigma`) is the most sensitive input (clearly visible in the
  sensitivity matrix) — don't just guess a number; ideally it should come
  from the historical volatility of comparable companies.
- If anyone has feedback or corrections (especially on the finance side),
  I'd genuinely appreciate it. I'm still learning, and this was mostly built
  out of curiosity about where stats and finance overlap.

## License

MIT — see [LICENSE](LICENSE).
