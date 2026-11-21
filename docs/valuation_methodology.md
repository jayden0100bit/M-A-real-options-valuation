# Valuation methodology (Stage 3)

Scope: a standalone valuation of the business Disney acquired from 21st Century Fox ("RemainCo"), plus comparable
companies and a transaction analysis. **Not included:** synergy valuation, accretion/dilution, real options.
Code: `src/valuation/`. Rebuild: `python src/run_pipeline.py --offline`.

## 1. Two information sets (no look-ahead)

| | **A: announcement** | **B: proxy date** |
|---|---|---|
| Valuation date | 14 Dec 2017 (deal announced) | 30 May 2018 (May 2018 joint proxy filed) |
| Market data | close of 13 Dec 2017 | close of 30 May 2018 |
| Information cut-off | documents dated on or before 14 Dec 2017 | documents dated on or before 30 May 2018 |
| Cash-flow basis | **estimates** (no management forecasts were public) | **management forecasts** disclosed in the May 2018 proxy |
| Tax regime | 35% federal + ~1% state = 36% (TCJA not yet law; enacted 22 Dec 2017) | 21% federal (TCJA) + ~1% state = 22% |

Every row of `dcf_assumptions.csv` carries an `available_date`. The `valuation_lookahead` check fails if any input became
available after its perspective's cut-off. Information published later (June 2018 updated forecasts, DOJ remedy on RSNs,
Sky sale, RSN sale, closing, Disney's purchase accounting) is only shown in rows labelled `subsequent_info_2018-06`
or `hindsight`, and never feeds A or B.

Labels used throughout: **reported** (from a filing) · **reported_forecast** (a management forecast as disclosed) ·
**market** (an external observation on a stated date) · **derived** (arithmetic on the above) · **estimate** (a judgement,
with method and sensitivity range stated).

## 2. Management forecasts (B)

Extracted by `src/valuation/forecasts.py` into `management_forecasts.csv`:

| Set | Proxy, page, table | Content | Period |
|---|---|---|---|
| 21CF forecasts to its advisor (original) | May 2018 p.127, t460/t461 | revenue, EBITDA, levered FCF, adjustment to unlevered FCF | FY2016A–FY2022E (June FY) |
| **Disney forecasts for RemainCo (original)** | May 2018 p.129, t473 | revenue, EBITDA, unlevered FCF | FY2018E–FY2028E |
| 21CF updated forecasts (subsequent) | June 2018 p.172, t616/t617 | revenue, EBITDA, levered FCF, Goldman/Centerview adjustments | FY2018F–FY2023E |
| Disney updated forecasts (subsequent) | June 2018 p.174, t630 | revenue, EBITDA, unlevered FCF | FY2018E–FY2028E |

* **Definitions differ from the historical data.** Forecast "EBITDA" is the provider's own measure and is not reconciled
  to GAAP. Disney's "unlevered free cash flow" = EBITDA − cash taxes − capex − change in NWC. 21CF's "levered FCF" also
  deducts interest and adds back stock compensation and dividends received. Unlevered FCF for 21CF is *derived* here as
  levered FCF + the disclosed net adjustment. Its FY2018F figure covers Q2–Q4 only (proxy footnote 4).
* **Perimeter:** the Disney forecasts reflect the agreed separation (RemainCo, including the RSNs, excluding Sky
  consolidation). The table "21CF forecasts provided to Disney" uses an earlier allocation and includes Sky, so it is
  not used.
* **Footnote markers** such as "(6,664" + ") (2)" or a bare "(4)" are parsed by a dedicated row parser. A bare
  single-digit "(n)" counts as a footnote only if the remaining cells then match the number of fiscal-year columns;
  otherwise the build stops. Unit tests cover both cases. "N/A" becomes an empty value, never zero.
* **Independent verification:** each row is matched a second time against the page text of the filing, a separate
  extraction of the HTML document (`forecast_extraction` checks). The SEC filings are HTML documents; no PDF version
  exists on EDGAR for these proxies.

## 3. DCF

Engine: `src/valuation/dcf.py`. It reuses the structure of `dcf_valuation` in the original illustrative notebook
(explicit PV + Gordon terminal value).

FCFF = EBIT × (1 − t) + D&A − capex − investment in working capital / content, with EBIT = EBITDA − D&A.

* **Periods:** June fiscal years. Only the part of a year after the valuation date counts. Cash flows are discounted from
  the midpoint of that remaining part. The terminal value is discounted from the end of the last forecast year
  (conservative).
* **Terminal value:** TV = FCFF_terminal × (1 + g) / (WACC − g), with g = 2.0% (range 1.0–3.0%).
  * A: FCFF_terminal = FY2022 FCFF.
  * B: management FCF is lumpy (e.g. 2,102 in FY2026, then 3,832 in FY2027), so FCFF_terminal = final-year EBITDA ×
    the average FCF/EBITDA conversion over the last five forecast years. That is 0.515 for the Disney case (FY2024–28)
    and 0.526 for the 21CF case (FY2020–22).

### A: estimate-based projection (all labelled `estimate` or `derived`)
| Input | Value | Basis |
|---|---|---|
| Base revenue FY2017 | 18,500 | 21CF revenue 28,500 − New Fox ~$10bn (14 Dec 2017 release). The RemainCo pro forma, published later, was 19,307. |
| Base EBITDA FY2017 | 4,373 (23.6%) | 21CF Total Segment OIBDA 7,173 − New Fox ~$2.8bn |
| Revenue growth | 3.0% (1–5%) | 21CF growth excluding the DBS disposal: FY2016 +1.7%, FY2017 +4.3% |
| D&A | 1.94% of revenue | 21CF consolidated FY2017 |
| Capex | 1.25% (1.0–2.0%) | 21CF FY2015–FY2017 aggregate |
| Content / working-capital investment | 2.95% (1.5–4.5%) | 21CF cash-flow line "inventories net of program rights payable", FY2015–FY2017 |
| Tax | 36% | 21CF FY2017 tax rate reconciliation |

### B: management forecasts
FCFF equals management's unlevered FCF **exactly** (checked for every year). The decomposition shown is a labelled
estimate: D&A at 2.01% of revenue (RemainCo FY2017 pro forma), taxes at 22% of EBIT, capex at 1.25% of revenue. The
working-capital/other line is the residual that reconciles to management FCF, including any difference between
management's cash taxes and the 22% rate. Base case: Disney forecasts. Alternative: 21CF forecasts (to FY2022).
Sensitivity / bull case: an estimated **TCJA cash-tax uplift** of (36% − 22%) × EBIT. The forecasts were prepared
before the tax reform and may embed pre-reform taxes; the proxy does not say.

## 4. WACC

| Input | A | B | Source |
|---|---|---|---|
| Risk-free | 2.36% | 2.84% | FRED DGS10 on the market-data date |
| ERP | 5.69% | 5.08% | Damodaran implied ERP (FCFE), end-2016 / end-2017 values, published in January of the following year |
| Beta | 0.87 relevered | 1.09 relevered | Median Blume-adjusted, unlevered 2-year weekly beta of Comcast, AMC Networks and Netflix vs the S&P 500 (Yahoo Finance prices); relevered at the median peer D/(D+E) (27% / 32%) |
| Cost of equity | 7.30% | 8.37% | CAPM |
| Pre-tax cost of debt | 4.19% | 4.75% | FRED DBAA (Moody's Baa). 21CF was rated Baa1/BBB+ (FY2017 10-K) |
| **WACC** | **6.04%** | **6.86%** | |

For reference only (not used as inputs): Goldman Sachs, 21CF's advisor, applied discount rates of 7.5%–8.5% to RemainCo
in the May 2018 proxy (p.119), and 6.75%–7.75% in the June 2018 proxy (p.146, subsequent information). Our A WACC of
6.04% is below the May range, mainly because of the low peer betas and 2.36% Treasury yields; the WACC sensitivity
grid spans 5.0%–7.9%.

## 5. Enterprise value to equity value

Equity = EV (consolidated operations) + Sky 39% stake + other investments (book) − borrowings + cash − noncontrolling interests.

| Item | A | B | Treatment |
|---|---|---|---|
| Debt | 19,849 (21CF 10-Q, 30 Sep 2017) | 19,997 (RemainCo pro forma, 31 Mar 2018) | All 21CF debt stays with RemainCo. The parties' "~$13.7bn net debt" is noted, not used. |
| Cash | 6,901 | 13,272 − 6,500 = 6,772 | B excludes the net $6.5bn New Fox dividend, which is matched by a $6.5bn transaction-tax payable. Both are left out to avoid double counting. |
| **Sky 39% stake** | 10,389 (estimate) | 12,018 (estimate) | Valued at offer prices, not at book (3,175). A: 21CF's own £10.75 offer (the 60.9% was ~$15bn at the Dec 2016 exchange rate, so the 39.1% stake ≈ £7.77bn). B: Comcast's £12.50 offer of 25 Apr 2018 (range £10.75–£14.00). Not in EV, so not double counted. |
| Other investments | 727 (book) | 606 (book) | Endemol Shine, Hulu 30%, Tata Sky etc. at book. Hulu's market value is **not** captured (hindsight reference: Disney valued its own 30% at 4,737 at closing). |
| NCI | 1,951 | 1,787 | Book values. A uses consolidated 21CF; B uses RemainCo redeemable NCI plus 21CF non-redeemable NCI, because RemainCo's own is not disclosed. |
| **RSNs** | inside EV | inside EV | The RSNs were part of the deal perimeter on both dates; the DOJ required their sale only on 27 Jun 2018. No RSN forecasts were disclosed, so they cannot be separated ex ante. They are **not** added again. A hindsight row subtracts their ~$11bn sale price (Aug 2019) for illustration only. |
| Transaction tax | 0 | 0 | The $8.5bn estimated tax was funded by the New Fox dividend; adjustments flowed into the deal terms, not into RemainCo's standalone value. |
| Shares | 1,851.1m (10-K cover, basic) | 1,871.1m (fully diluted, merger agreement) | |

Per-share values are for 21CF's *acquired* business only. 21CF holders also kept New Fox shares.

## 6. Comparable companies

`src/valuation/peers.py`; output `comparable_companies.csv`.
* **Peers:** Comcast, AMC Networks and Netflix (Disney as reference only). The natural peers (Time Warner, Viacom, CBS,
  Discovery, Scripps, Lionsgate) lack price history in the accessible source. This is a material limitation.
* **LTM financials:** from SEC XBRL facts **filed on or before** the valuation date (FY + YTD − prior YTD). The balance
  sheet is taken at a single common date.
* **Shares:** diluted weighted-average shares for the latest quarter, used as an explicitly labelled proxy (the
  `shares_basis` column). Not actual shares outstanding.
* **EV:** market cap + debt − cash + NCI.
* **Exclusions:**
  * Netflix is excluded from the ranges, because its content amortization sits in cost of revenues and it is priced on growth.
  * Disney is reference only, as the acquirer.
  * P/E is not meaningful at B, because LTM earnings include the TCJA remeasurement.
  * Multiples above 60x are flagged.
* **Application:** the ranges come from Comcast and AMC Networks only. They are applied to RemainCo LTM metrics:
  * A: FY2017, derived from public December 2017 information;
  * B: the FY2017 pro forma from the May proxy, which is about 11 months stale because no LTM to March 2018 was disclosed.

  The results go through the same bridge as the DCF. The advisors' 8.0–9.0x CY2018E EBITDA range (proxy p.149) is shown
  separately as a disclosed reference.

## 7. Transaction analysis

`src/valuation/transaction.py`. Terms come from the verified `transaction_assumptions.csv`.
* **Unaffected price:** 21CF on 3 Nov 2017, the last trading day before press reports (proxy p.56). FOXA $24.97 and FOX
  $24.43, weighted by class share counts: $24.74.
* **Premiums:**
  * Consideration-only premiums understate the economics, because holders also kept New Fox.
  * The closing "package" premium adds 1/3 Fox Corporation share per original 21CF share, at FOXA's first close
    ($40.34, 19 Mar 2019). It is nominal and not market-adjusted.
* **Value concepts kept separate:**
  * headline equity value;
  * headline transaction (enterprise) value;
  * market-implied equity value;
  * cash and stock consideration;
  * accounting purchase price (ASC 805, stock at $110.00);
  * derived closing EV.
* **Implied EV/EBITDA:** the headline EV, less the Sky stake estimate and other investments, divided by RemainCo EBITDA
  (estimate/derived).

## 8. Sensitivities and scenarios

`valuation_sensitivity.csv`:
* a 5×5 grid of WACC (±1pp) against g (1–3%);
* EBITDA margin ±2pp;
* revenue growth ±2pp;
* capex −0.5 to +1.0pp of revenue;
* content/working-capital investment ±1pp of revenue.

Scenarios (`DCF scenario` rows):
| | A | B |
|---|---|---|
| Bear | growth 1%, margin −2pp, content investment 4.5%, g 1.5% | Disney forecasts with margin −1pp, growth −1pp a year, g 1.5% |
| Base | as in §3 | Disney forecasts |
| Bull | growth 5%, margin +2pp, content investment 1.5%, g 2.5%, 22% tax (TCJA pending) | 21CF forecasts + TCJA cash-tax uplift, g 2.5% |

## 9. Validation checks (in `verification_checks.csv`)

| check_type | What it tests |
|---|---|
| `forecast_extraction` | each forecast row parsed with the right number of periods and re-found, in order and with signs, on the cited page |
| `valuation_input_quote`, `valuation_input_table` | every quoted input found verbatim (prose) or in the cited table row |
| `valuation_lookahead` | every input available on or before its perspective's cut-off |
| `valuation_market_data` | Yahoo Disney closes equal the closes printed in the proxy (3 Nov 2017, 13 Dec 2017, 25 May 2018) |
| `valuation_fcff` | FCFF identity each year; B rebuilt FCFF = management unlevered FCF |
| `valuation_wacc` | weights sum to 1; CAPM; WACC recomputation; WACC within 4–12% |
| `valuation_terminal` | Gordon formula; discounting; TV share of EV below 90% |
| `valuation_ev`, `valuation_bridge` | EV = PV(explicit) + PV(TV); equity bridge arithmetic |
| `valuation_sensitivity` | EV falls with WACC, rises with g; margin, growth, capex and content effects in the expected direction |
| `valuation_outputs` | EV and equity finite and positive |
| `transaction_premium` | 0.2745 × $107.61 = $29.54; $51.572626 × 0.736817 = $38.00 |
