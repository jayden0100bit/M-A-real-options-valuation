# Data dictionary

All processed files are UTF-8 CSV in `data/processed/`. They are rebuilt from the files in `data/raw/` with
`python src/run_pipeline.py --offline`.

**Units.** Monetary values are **USD millions** (`USD_m`) unless the `unit` column says otherwise
(`USD_per_share`, `shares_m` = millions of shares, `ratio`, `percent`, `date`, `text`). Every source used here
already reports in USD millions, so no currency or scale conversion was applied to financial-statement data.
Raw-dollar amounts quoted in deal documents (e.g. `$6,500,000,000`) were divided by 10^6.

**Signs.** Values keep the sign shown in the source. Expenses, losses and cash outflows shown in parentheses
are negative. Liabilities and noncontrolling interests in the purchase price allocation are negative, as in
Disney's table.

---

## 1. `historical_financials.csv`

Long format: one row per source line item × period × perimeter.

| Column | Description |
|---|---|
| `record_id` | Row identifier (`HF00001`…). Stable only for a given build; join on the descriptive columns instead. |
| `entity` | `DIS` = The Walt Disney Company (legacy registrant, CIK 1001039, now TWDC Enterprises 18 Corp.); `21CF` = Twenty-First Century Fox, Inc. consolidated (CIK 1308161); `RemainCo` = 21CF after separation of New Fox/FOX, i.e. the business Disney acquired (pro forma); `RemainCo_bridge` = pro forma bridging columns (New Fox removal, pro forma adjustments, Sky disposition, RSN divestiture). |
| `entity_name` | Long name of the entity. |
| `perimeter` | Which business the number describes, e.g. `Disney consolidated`, `21CF consolidated (pre-separation, incl. New Fox businesses)`, `21CF historical`, `New Fox (ASC 205 basis)`, `Pro forma adjustments`, `RemainCo (excl. Sky consolidation)`, `Disposition of Sky`, `RemainCo (closing perimeter)`, `Divestiture of RSNs (Disney pro forma bridge)`. |
| `statement` | `income_statement`, `balance_sheet`, `cash_flow`, `segment`. |
| `section` | Section heading in the source table (e.g. `Current assets`, `INVESTING ACTIVITIES`, `Segment OIBDA`), or `derived`. |
| `line_item` | Standardized code for the key rows (list below). Blank if the row is kept for completeness but not mapped. |
| `line_item_reported` | Row label exactly as in the filing (footnote markers kept). Blank-label subtotal rows are named `[unlabelled subtotal after: <previous label>]`. |
| `segment` | Segment-table rows only: segment name without footnote markers. Sub-rows are `Parent - Child`, e.g. `Studio Entertainment - Third parties`. |
| `fiscal_period` | `FY2013`…`FY2018` (each company's own fiscal year), `6M_DEC2017` (21CF six months to 31 Dec 2017), `Q1_FY2019` (21CF three months to 30 Sep 2018), `MAR2018` / `DEC2018` (balance-sheet dates 31 Mar 2018 / 31 Dec 2018). |
| `period_start`, `period_end` | ISO dates. `period_start` is blank for balance-sheet (instant) values. |
| `period_length` | `52 weeks`, `53 weeks` (Disney FY2015), `12 months`, `6 months`, `3 months`, or `instant`. |
| `value` | Numeric value in `unit`. |
| `unit` | `USD_m`, `USD_per_share`, `shares_m`. |
| `data_type` | `reported` (10-K statement value); `reported_in_pro_forma_presentation` (21CF historical column of a pro forma table); `pro_forma` (RemainCo); `pro_forma_adjustment` (bridging column); `derived` (computed here; formula in `notes`). |
| `basis` | `as_originally_reported` (the period is the filing's own fiscal year); `comparative_in_later_filing` (prior-year column of a later 10-K, which may be recast); `pro_forma_2018_joint_proxy`; `pro_forma_8KA_closing_perimeter`. |
| `is_primary` | `True` for exactly one value per entity × perimeter × period × line. Rules: FY2015-FY2017 from the **FY2017 10-K** of each company (FY2015 balance sheet from the FY2016 10-K); FY2018 from the FY2018 10-K; RemainCo from the 8-K/A where it covers the period, otherwise from the 2018 joint proxy (FY2015, 6M Dec 2017, Mar 2018); bridge columns are never primary. |
| `source_id` | Key into `source_register.csv`. |
| `source_page` | Printed page number of the page holding the table, as shown in the filing's page footer (not a PDF page index). |
| `source_table_index` | Position of the `<table>` element in the downloaded HTML (0-based). With the SHA-256 in the source register this locates the exact table. |
| `xbrl_check` | `match` / `mismatch` against the SEC XBRL fact with the same accession and period; `not_mapped` if no XBRL concept is mapped for that line; `not_applicable` for pro forma and derived rows. |
| `xbrl_fact` | The XBRL concept and value used for the check. |
| `notes` | Formula for derived rows, caveats for pro forma bridge rows. |

### Standardized `line_item` codes

Income statement: `revenue`, `revenue_services`, `revenue_products` (Disney), `cost_of_services`,
`cost_of_products` (Disney), `operating_expenses` (21CF), `sga`, `depreciation_amortization`,
`total_costs_and_expenses` (Disney), `restructuring_impairment`, `restructuring_impairment_and_other`
(Disney pro forma presentation), `other_income_expense_net`, `interest_expense_net`, `interest_income` (21CF),
`equity_income_affiliates`, `pretax_income_continuing`, `income_tax`, `income_continuing_ops`,
`discontinued_ops_net`, `net_income`, `net_income_nci`, `net_income_attributable_parent`,
`income_continuing_ops_attributable_parent`, `eps_basic`, `eps_diluted`, `shares_basic`, `shares_diluted`.

Balance sheet: `cash`, `receivables_current`, `inventories_current`, `tv_costs_advances_current` (Disney),
`total_current_assets`, `receivables_noncurrent`, `film_tv_inventories_noncurrent` (Disney "Film and
television costs"; 21CF non-current "Inventories, net"), `investments`, `ppe_net` (Disney "Parks, resorts and
other property" total; 21CF "Property, plant and equipment, net"), `intangible_assets_net`, `goodwill`,
`total_assets`, `borrowings_current`, `total_current_liabilities`, `borrowings_noncurrent`,
`deferred_income_taxes_liability`, `redeemable_nci`, `equity_attributable_parent`, `nci_equity`,
`total_equity`, `total_liabilities_and_equity`.

Cash flow: `cf_net_income`, `cf_depreciation_amortization`, `cfo`, `capex`, `acquisitions`, `cfi`,
`dividends_paid`, `share_repurchases`, `debt_proceeds`, `debt_repayments`, `commercial_paper_net` (Disney),
`cff`, `interest_paid` and `income_taxes_paid` (Disney; 21CF discloses these outside the cash-flow statement
and they were not extracted).

Segment (`statement == "segment"`): `segment_revenue`, `segment_operating_income` (Disney),
`segment_oibda` (21CF), `segment_reconciliation_item`, `segment_capex`, `segment_depreciation`,
`segment_amortization_intangibles`, `segment_identifiable_assets` (instant values), `supplemental_revenue`,
`geographic_revenue`, `geographic_segment_operating_income` (Disney).

Derived (`data_type == "derived"`, primary values only):
* `total_borrowings` = `borrowings_current` + `borrowings_noncurrent` (balance-sheet carrying amounts)
* `net_debt` = `total_borrowings` − `cash` (excludes investments, leases, pensions and NCI)
* `fcf_cfo_less_capex` = `cfo` + `capex` (capex is negative). Not a company-defined measure.

### Comparability notes
* Disney's segment measure is **segment operating income**; 21CF's is **Segment OIBDA**. They are different
  measures and should not be compared directly.
* Disney reports `cost_of_services` / `cost_of_products`. 21CF reports a single `operating_expenses` line.
* Disney presents **no** discontinued operations in FY2015-FY2018. 21CF does, so its `net_income` includes
  discontinued operations. Use `income_continuing_ops` for continuing results.

---

## 2. `transaction_assumptions.csv`

One row per deal term or accounting figure.

| Column | Description |
|---|---|
| `id` | `O..` original agreement, `A..` amended agreement, `C..` closing, `P..` purchase accounting, `X..` context. `*9x` ids are derived checks. |
| `stage` | `original_2017_12`, `amended_2018_06`, `closing_2019_03`, `accounting_fy2019`, `context`. **Do not mix stages.** |
| `category` | Grouping, e.g. `consideration`, `headline value`, `collar`, `tax adjustment`, `purchase price allocation`. |
| `item` | Description. |
| `value`, `unit` | Value and unit (`USD_m`, `USD_per_share`, `shares_m`, `ratio`, `percent`, `date`, `text`). |
| `measure_basis` | What kind of quantity this is. Key values: `equity_value_headline` (parties' announced equity value), `transaction_value_headline` (equity value + net debt assumed, as defined by the parties), `net_debt_assumed_headline`, `purchase_consideration_accounting` (ASC 805 purchase price), `cash_consideration`, `stock_consideration_accounting` (shares × $110.00 used in Disney's accounting), `stock_consideration_implied` (shares × $114.1801 average price), `per_share_consideration`, `reference_price`, `market_price`, `collar`, `adjustment_mechanism`, `share_count`, `ownership`, `termination_fee`, `synergy_guidance`, `purchase_price_allocation`, `acquired_cash_headline`, `assumed_debt_headline`, `assumed_debt_accounting`, `divestiture`, `accounting_gain`, `financing`, `cash_flow`, `post_acquisition_results`, `pro_forma_results`, `transaction_costs`, `competing_offer`, `perimeter`, `bridge`, `date`. |
| `value_type` | `reported` (quoted from a filing) or `derived` (computed from other rows; see `formula`). |
| `as_of` | Date the figure refers to. |
| `source_id` | Key into `source_register.csv` (blank for derived rows). |
| `source_page` | Printed page number of the page holding the quote, as shown in the filing's footer. Blank when that page is unnumbered (proxy cover letters, most 8-K bodies). |
| `source_location` | `printed page N`, or a note that the page is unnumbered and the quote should be used to find it. |
| `quote` | Exact text from the filing (whitespace-normalised). For purchase price allocation rows, the row label in Disney's allocation table. |
| `value_as_stated` | The figure as worded in the quote (e.g. `$52.4 billion`), parsed back to `value`/`unit` as a check. |
| `formula` | Derived rows: the arithmetic in terms of other `id`s. |
| `verification_status` | `verified_quote_and_value`, `verified_table_value`, `derived_consistent_with_<id>`, `derived_no_reported_counterpart`. Any `FAILED_*` / `DERIVED_INCONSISTENT_*` value makes the build exit with an error. |
| `notes` | Caveats, especially where similar-looking figures should not be confused. |

---

## 3. `source_register.csv`

| Column | Description |
|---|---|
| `source_id` | Identifier used throughout (`DIS_10K_FY2017`, `JPROXY_AMENDED_20180628`, …). |
| `entity`, `cik` | Filer and SEC Central Index Key. Disney filings before March 2019 are under CIK 1001039; the post-closing parent (formerly TWDC Holdco 613 Corp.) files under CIK 1744489. |
| `form`, `filing_date`, `period_end`, `accession`, `document` | EDGAR filing metadata. |
| `description` | What the document is and why it is used. |
| `url` | Direct EDGAR archive URL of the document that was downloaded. |
| `filing_index_url` | EDGAR filing index page, listing all documents in the filing. |
| `local_path`, `bytes`, `sha256` | Local copy and its hash (from `data/raw/download_manifest.csv`). |
| `download_status` | `ok` or the error message. |
| `records_historical_financials`, `primary_records_historical_financials`, `records_transaction_assumptions` | How many processed rows cite this source. |
| `source_type` | `primary SEC filing` or `SEC structured data (verification only)`. |

---

## 4. `verification_checks.csv`

| Column | Description |
|---|---|
| `check_type` | `arithmetic`, `xbrl_cross_check`, `transaction_quote`, `transaction_table_value`, `transaction_derived`. |
| `entity`, `source_id`, `fiscal_period` | What was checked. |
| `item` | The check or the record id. |
| `expected`, `observed` | Values compared (or verification status). |
| `status` | `pass` / `match`, or `fail` / `mismatch`. |
| `detail` | Table index, tolerance, or accession used. |

## 5. Supporting files

| Path | Content |
|---|---|
| `data/reference/filings_to_fetch.csv` | Hand-maintained list of filings (CIK, accession, file name, purpose). Drives the download. |
| `data/raw/sec/<source_id>__<file>` | Unmodified EDGAR documents. |
| `data/raw/xbrl/companyfacts_*.json` | Unmodified SEC XBRL company-facts API responses (verification only). |
| `data/raw/download_manifest.csv` | URL, size and SHA-256 of every downloaded file. |
| `data/interim/` | Derived text and table caches (git-ignored, rebuilt automatically). |

---

## 6. Stage 2 outputs (`src/build_analysis.py`)

### `financial_ratios.csv`
One row per entity × period × metric.

| Column | Description |
|---|---|
| `entity` | `DIS`, `21CF` (consolidated, pre-separation), `RemainCo` (pro forma acquired perimeter). |
| `perimeter` | As in `historical_financials.csv`. |
| `fiscal_period`, `period_end` | Own fiscal period of the entity (`FY2015`…, `6M_DEC2017`, `Q1_FY2019`, `MAR2018`, `DEC2018`). CAGR rows use `FY2015-FY2017` / `FY2015-FY2018`. |
| `category` | `growth`, `profitability`, `returns`, `balance_sheet`, `leverage`, `cash_flow`, `perimeter`. |
| `metric` | e.g. `revenue_growth_yoy`, `ebit`, `ebitda_margin`, `effective_tax_rate`, `roe_avg_equity`, `net_debt_to_ebitda`, `fcf_margin`, `share_of_21cf_revenue`, `rsn_revenue_share`. Definitions are in `docs/historical_analysis_report.md`. |
| `value`, `unit` | `USD_m`, `ratio` (0.25 = 25%), `x`. Empty when `value_type` is `not_available`. |
| `value_type` | `reported`, `derived`, `adjusted` (excludes restructuring/impairment), `not_available`. |
| `formula` | Arithmetic used. |
| `inputs` | Inputs as `name=value [record_id; source_id p.page]`. `record_id` refers to `historical_financials.csv` of the same build. |
| `notes` | Comparability caveats and reasons for `not_available`. |

### `segment_analysis.csv`
Columns as above plus `segment`. Metrics: `segment_revenue` (R), `segment_operating_income` (Disney, R), `segment_oibda`
(21CF, R), `segment_margin`, `revenue_share`, `profit_share` (D). Every 21CF row carries the note that it describes the
consolidated pre-separation company, not the acquired perimeter. RemainCo rows are `not_available` (no segment
disclosure exists).

---

## 7. Stage 3 outputs (`src/valuation/`)

Perspectives: `A_announcement_2017-12` (valuation date 14 Dec 2017), `B_proxy_2018-05` (30 May 2018), plus
`transaction`, `hindsight` and `subsequent_info_2018-06` rows that never feed A or B.

| File | Grain | Key columns |
|---|---|---|
| `management_forecasts.csv` | proxy × forecast set × metric × fiscal year | `value` (empty when the source shows N/A), `value_status` (reported_forecast / derived / not_available_in_source), `source_page`, `source_table_index`, `row_label_in_source`, `definition`, `footnote`, `text_verified`, `available_date`, `perimeter` |
| `dcf_assumptions.csv` | perspective × parameter | `value`, `unit`, `value_type` (reported / reported_forecast / market / derived / estimate), `source`, `observation_date`, `available_date`, `method`, `sensitivity_low`, `sensitivity_high` |
| `dcf_projections.csv` | perspective × case × fiscal year | revenue, EBITDA, D&A, EBIT, taxes, NOPAT, capex, `dnwc` (working capital / content investment; for B the residual that reconciles to management FCF), FCFF, fraction after the valuation date, discount time and factor, PV |
| `valuation_outputs.csv` | perspective × method × case × metric | `value`, `unit`, `value_type`, `notes`. Metrics include `enterprise_value_ops` (consolidated operations, incl. RSNs), `equity_value`, `equity_value_per_21cf_share`, bridge items, transaction values (`equity_value_headline`, `enterprise_value_headline`, `market_implied_equity_value`, `accounting_purchase_price`, `cash_consideration`, premiums) |
| `valuation_sensitivity.csv` | perspective × table × parameter value | `enterprise_value_ops`, `equity_value`, `equity_per_share` |
| `comparable_companies.csv` | perspective × ticker | price, `shares_m_proxy` with `shares_basis` (diluted weighted-average proxy, **not** shares outstanding), debt, cash, NCI, EV, LTM revenue / EBITDA / operating income / net income (each with its XBRL source and accession), multiples with `*_flag` explaining exclusions |
| `data/raw/market/` | one file per series | FRED CSVs, the Damodaran HTML, Yahoo JSON; `market_manifest.csv` holds URL, retrieval time, SHA-256 and status |

---

## 8. Stage 4 outputs (`src/valuation/synergy.py`, `accretion.py`, driver `build_stage4.py`)

| File | Grain | Key columns |
|---|---|---|
| `synergy_assumptions.csv` | perspective × parameter | `value`, `unit`, `value_type` (management_guidance / not_disclosed / estimate / derived), `source` (document and page, checked by the build), `available_date`, `method`, sensitivity range |
| `synergy_outputs.csv` | perspective × section × case × metric | Sections: `Synergy cash flows` (per Disney FY; `notes` hold every component), `Synergy value` (gross, PV integration, net, per share, standalone + synergies), `Synergy sensitivity`, `Deal justification` (consideration, standalone, premium, coverage, value created, walk-away price), `Reference: Disney advisors` (implied values, not inputs). `perspective = hindsight` rows use subsequent information |
| `accretion_dilution_inputs.csv` | group × item | `value`, `unit`, `value_type` (reported / reported_forecast / reported_assumption / derived / estimate / management_guidance), `source`, `notes` |
| `accretion_dilution_outputs.csv` | case × fiscal year × metric | Components (standalone NI and EPS, RemainCo NI, incremental debt and interest, PPA amortization, synergies, integration costs, shares) and `pro_forma_eps_adjusted` / `pro_forma_eps_gaap_basis` / `accretion_adjusted` / `accretion_gaap_basis` (ratio). `case` = base, variants, `sensitivity: <variable> = <value>`, or `reported anchor` |
