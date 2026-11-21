# Data collection report: Disney / 21st Century Fox

*Scope: building and checking the historical and transaction dataset. No valuation modelling.*
Rebuild: `python src/run_pipeline.py --offline`. Column definitions: [`data_dictionary.md`](data_dictionary.md).

## 1. Summary

| Output | Size | Verification |
|---|---|---|
| `historical_financials.csv` | 3,558 rows (1,174 primary): Disney 1,731, 21CF 1,303, RemainCo 160, RemainCo bridge 364 | 204 arithmetic tie-outs pass; 376 values match SEC XBRL facts, 0 mismatches |
| `transaction_assumptions.csv` | 116 records: 100 reported, 16 derived | 82 quotes found verbatim with matching values; 14 PPA values match the parsed 10-K table; 16 derived figures reproduce the reported ones |
| `source_register.csv` | 41 sources (38 EDGAR documents + 3 XBRL datasets) | SHA-256 for every file |

No figure in the processed files was typed in from memory or estimated. Financial-statement values are
parsed from the filing HTML. Deal terms are stored with the exact quote they come from, and the build fails
if a quote is not found in the source or its number does not match the stored value.

## 2. Sources collected

| Group | Documents (`source_id`) |
|---|---|
| Disney annual reports | `DIS_10K_FY2015`, `DIS_10K_FY2016`, `DIS_10K_FY2017`; supplementary `DIS_10K_FY2018` (CIK 1001039) |
| 21CF annual reports | `FOX_10K_FY2015`, `FOX_10K_FY2016`, `FOX_10K_FY2017`; supplementary `FOX_10K_FY2018` (CIK 1308161) |
| Original agreement (Dec 2017) | Disney 8-K with merger agreement (Ex. 2.1) and press release (Ex. 99.1); 21CF 8-K and releases; **original joint proxy statement/prospectus** (424B3, 30 May 2018, `JPROXY_ORIG_20180530`), superseded |
| Amended agreement (Jun 2018) | Disney 8-K with amended merger agreement and press release; 21CF 8-K; **2018 joint proxy statement/prospectus** (424B3 filed by TWDC Holdco 613 Corp., 28 Jun 2018, `JPROXY_AMENDED_20180628`) |
| Closing (Mar 2019) | 21CF releases on the election deadline, preliminary election results, distribution multiple, distribution completion and per-share value; 21CF 8-K of 20 Mar 2019; New Disney 8-K12B (final consideration and proration) and 8-K (debt exchange) |
| Acquired business | New Disney 8-K/A of 27 Mar 2019: 21CF audited FY2018 statements (Ex. 99.1), interim Dec 2018 (Ex. 99.2), New Disney pro forma (Ex. 99.3), **RemainCo pro forma on the closing perimeter** (Ex. 99.4) |
| Disney FY2019 acquisition disclosures | `DIS_10Q_Q2FY2019` (initial purchase price allocation), `DIS_10K_FY2019` (Note 4: final purchase price, updated allocation, pro formas, divestitures) |
| Structured data | SEC XBRL company facts for CIKs 1001039, 1744489 and 1308161 (verification only) |

Each URL in the register is the EDGAR archive location for the accession number listed. All 41 files
downloaded successfully on 2026-11-20.

## 3. Method

1. **Download** (`fetch_sources.py`): reads the filing list and saves the documents unchanged, with hashes.
2. **Parse** (`sec_text.py`, `sec_tables.py`): turns HTML tables into label/value rows. Parentheses become
   negatives and dashes become zero. Each table is given the printed page number from the footer of its
   physical page; pages are found from the HTML page-break markers.
3. **Historical build** (`build_historical.py`): each statement table is pinned by table index and printed
   page, and the script stops if the page differs. Every row of every period is written out with its
   reported label, and key rows also get a standardized code. A single `is_primary` value is chosen per
   item (rules in §5).
4. **Transaction build** (`build_transaction.py`): one record per term, with a quote, the value as worded,
   the stage and `measure_basis`.
5. **Verification**: arithmetic tie-outs, an independent check of mapped 10-K values against the XBRL facts
   of the same accession and period, quote and value checks, and recomputation of derived figures. Results
   are in `verification_checks.csv`.

Page numbers are the **printed page numbers** of the filing, not PDF page indexes. When the quoted text sits
on a page without a printed number (proxy cover letters, most 8-K bodies, first pages of press releases),
`source_page` is blank and `source_location` says so. Every quote can still be found by searching the document.

## 4. Fiscal-year differences

| | Disney | 21CF |
|---|---|---|
| Fiscal year end | Saturday closest to 30 September | 30 June |
| FY2015 | 28 Sep 2014 – 3 Oct 2015, **53 weeks** (FY2015 10-K, Note 1) | 1 Jul 2014 – 30 Jun 2015 |
| FY2016 | 4 Oct 2015 – 1 Oct 2016 | 1 Jul 2015 – 30 Jun 2016 |
| FY2017 | 2 Oct 2016 – 30 Sep 2017 | 1 Jul 2016 – 30 Jun 2017 |
| FY2018 | 1 Oct 2017 – 29 Sep 2018 | 1 Jul 2017 – 30 Jun 2018 |

* The two companies' "FY" labels are **three months apart**. Nothing has been calendarised, and each row
  keeps its own start and end dates. Putting both on one calendar would need quarterly data (10-Qs), which
  has not been collected.
* Disney's FY2015 has one extra week. Disney says the extra week helped FY2015 revenue, but the effect is
  not quantified in the dataset.
* Disney's own pro forma combination (8-K/A Ex. 99.3) pairs Disney's year to **29 Sep 2018** with RemainCo's
  year to **30 Jun 2018**, and Disney's quarter to 29 Dec 2018 with RemainCo's quarter to 30 Sep 2018.
  That pro forma therefore mixes periods.
* After closing, 21CF's results enter Disney's books from **20 March 2019** (Disney FY2019 Q2).

## 5. Choosing one value per item (restatements and reclassifications)

Each 10-K shows two or three years, so most periods appear in several filings. **All versions are kept.**
`basis` tells them apart (`as_originally_reported` vs `comparative_in_later_filing`), and `is_primary`
marks one:

* **FY2015–FY2017 → the FY2017 10-K** of each company: the last annual report before the 14 Dec 2017
  announcement, so the three years are on one consistent basis. FY2015 balance sheets come from the FY2016
  10-K, because the FY2017 10-K shows only two balance-sheet dates.
* **FY2018 → the FY2018 10-K.** This year is supplementary, beyond the requested FY2015–FY2017.

Differences found between filings (notebook §6 lists all of them):

| Company | What changed | Where it comes from |
|---|---|---|
| 21CF | FY2015 "Other, net" was 4,196 as originally reported and 4,698 in the FY2017 10-K, where impairment and restructuring (−502) became a separate line. FY2016 "Other, net" went from −658 to −335 (impairment −323 separated). Pretax income is unchanged. | FY2017 10-K presentation |
| 21CF | FY2016 and FY2017 costs moved from SG&A to operating expenses: FY2017 opex −17,775 → −18,094, SG&A −3,617 → −3,298. Revenue, pretax and net income are unchanged. | FY2018 10-K: "reclassified certain fiscal 2017 and 2016 amounts for development and certain other costs from Selling, general and administrative to Operating expenses" |
| 21CF | FY2015 balance sheet recast in the FY2016 10-K: total assets 50,051 → 50,039, deferred income taxes 2,082 → 2,290, current liabilities 7,262 → 7,042. | FY2016 10-K: early, retrospective adoption of ASU 2015-17 (all deferred taxes non-current). ASU 2015-03 (debt issuance costs) is discussed in the same filing. The split of the change between the two was not analysed. |
| 21CF | FY2016 total assets 48,365 → 48,193 in the FY2017 10-K. | Not explained. The FY2017 10-K's reclassification note (tax credits moved from non-current inventories to other non-current assets) says it "did not affect previously reported ... Total assets", so it does not account for the −172. |
| 21CF | FY2017 balance sheet recast in the FY2018 10-K: receivables 6,477 → 6,625, deferred revenue 580 → 728, total assets 50,724 → 50,872. FY2016/FY2017 cash-flow lines also differ (FY2017 CFO 3,785 → 3,795). | Not analysed; both versions are kept. |
| Disney | FY2015 CFO was 10,909 as originally reported and 11,385 in the FY2017 10-K; FY2016 CFO 13,213 → 13,136; financing cash flows changed too. | FY2017 10-K: ASU 2016-09 retrospectively reclassified cash paid for shares withheld for employee taxes (~$0.3bn FY2015, ~$0.2bn FY2016) from operating to financing activities. Cash flows are now presented including restricted cash. The rest of the difference was not broken down. |
| Disney | Segments: the FY2015 10-K reports five (Media Networks, Parks and Resorts, Studio Entertainment, Consumer Products, Interactive). From FY2016 there are four (Consumer Products & Interactive Media combined). | The primary FY2015 segment data uses the four-segment comparatives in the FY2017 10-K. The FY2018 10-K still uses the four segments; Disney's new segments start in FY2019. |

## 6. Acquired business perimeter

Disney did **not** acquire 21CF as reported in its 10-Ks. Before closing, 21CF transferred Fox News Channel,
Fox Business Network, Fox Broadcasting Company, Fox Sports, Fox Television Stations, FS1, FS2, Fox Deportes,
Big Ten Network and some other assets (the 20th Century Fox studio lot among them) to Fox Corporation
("New Fox") and distributed its shares on 19 Mar 2019. Disney then acquired the rest, "RemainCo": the film and
TV studios, FX Networks, National Geographic Partners, the regional sports networks (RSNs), Fox Networks Group
International, Star India, and stakes in Hulu (30%), Tata Sky and Endemol Shine. The 39% Sky stake was sold to
Comcast in October 2018 for about $15.1bn, before closing.

The dataset holds three layers. They must not be combined without care:

| Layer | `entity` / `basis` | Coverage | Use |
|---|---|---|---|
| 21CF consolidated (pre-separation) | `21CF`, reported | FY2013–FY2018 full statements and segments | History of the whole company, **including New Fox** |
| RemainCo, 2018 joint proxy | `RemainCo`, `pro_forma_2018_joint_proxy` | Income statement FY2015, FY2016, FY2017, 6M to Dec 2017; balance sheet 31 Mar 2018 (proxy pp. 285–289) | Perimeter as described when shareholders voted. The proxy's hypothetical "consolidation of Sky" columns are left out because that never happened. |
| RemainCo, closing perimeter | `RemainCo`, `pro_forma_8KA_closing_perimeter` | Income statement FY2016, FY2017, FY2018, Q1 FY2019; balance sheet 31 Dec 2018 (8-K/A Ex. 99.4, pp. 3–7) | **Primary** where available: New Fox spun off and Sky sold |

Key RemainCo figures (USD m, primary): revenue FY2015 21,456 · FY2016 19,111 · FY2017 19,307 · FY2018 20,851;
pretax income from continuing operations FY2015 8,103 (includes the FY2015 gain in "Other, net") ·
FY2016 2,044 · FY2017 2,122 · FY2018 1,456.

Perimeter caveats:
* **New Fox is removed on an ASC 205 (discontinued operations) basis, with no carve-out allocations.** All
  21CF corporate costs therefore stay in RemainCo. 21CF management estimated New Fox's standalone corporate
  costs at $275–350m a year (proxy note 3.b).
* **RSNs are in RemainCo but were divested** (DOJ consent decree; sold Aug 2019 for about $11bn). The only
  RSN figures available are the "Divestiture of RSNs" bridge in Disney's pro forma (FY2018 revenue −4,331;
  Q1 FY2019 −1,144). Per note (h) the other lines in that column also reverse pro forma fair-value
  amortization, so only the revenue line is clean.
* **21CF segment data is not on the acquired perimeter.** Cable Network Programming combines acquired
  networks (FX, National Geographic, RSNs, international, Star) with New Fox networks (Fox News, FS1, …).
  Television is almost all New Fox. No segment split of RemainCo was found in the sources.
* **RemainCo FY2015 is unusual:** "Other, net" of +4,798 includes a pre-tax gain of about $5.0bn on the
  November 2014 sale of Sky Italia and Sky Deutschland (FY2017 10-K: "included in Other, net in the
  Consolidated Statement of Operations for fiscal 2015"). The DBS segment exists only in FY2015.
* The pro forma statements are SEC Regulation S-X Article 11 presentations and are illustrative. They
  include a $6.5bn net dividend from New Fox to 21CF and a matching $6.5bn transaction tax payable (proxy
  note 3.f).

## 7. Transaction terms

Stages are stored separately (`stage`), and different value concepts are labelled (`measure_basis`):

| Stage | Per-share terms | Headline equity value | Headline transaction value | Other |
|---|---|---|---|---|
| Original (14 Dec 2017) | 0.2745 Disney shares (all stock), set with a $102 30-day VWAP | ~$52,400m | ~$66,100m (incl. ~$13,700m net debt) | ~515m new shares, ~25% stake; $8.5bn tax estimate |
| Amended (20 Jun 2018) | $38.00 cash or stock, 50/50, collar $93.53–$114.32 (ratio 0.3324–0.4063); midpoint $103.926 | ~$71,300m (= $38 × 1,877m shares) | ~$85,100m (incl. ~$13,800m net debt) | Maximum cash $35,700m; ~343m shares, ~19% stake; tax band $6.5–8.5bn; up to $2bn cash payment to New Fox |
| Closing (19–20 Mar 2019) | $51.572626 cash or 0.4517 shares **per 21CF share remaining after the distribution** (= $38.00 × distribution multiple 1.357190); average Disney price $114.1801 (inside the collar); final transaction tax $6.5bn, so the equity adjustment is $0 | ~$71,000m implied ($35,700m cash + ~$35,000m stock) | ~$71,000m (cash acquired ~$19,800m roughly offsets debt assumed ~$19,200m) | 306,844,635 shares issued; cash election oversubscribed and prorated |
| Accounting (Disney FY2019) | 307m shares at **$110.00** | **Purchase price $69,507m** (ASC 805) = $35.7bn cash + $33.8bn stock | n/a | Goodwill 49,085; intangibles 17,881; borrowings (21,723); NCI (10,408); Hulu remeasurement gain $4.8bn |

Points to keep in mind:
* **Equity value, transaction value and purchase consideration are different things.** The ~$71bn closing
  figure values the stock at the $114.18 VWAP. The $69.5bn accounting price values it at $110.00. The ~$1.5bn
  gap (`P92`) is mostly that price difference.
* **The $38.00 and the $51.57 are per different shares.** $51.57 applies to the 0.736817 of each original
  21CF share that remained after the Fox Corporation distribution.
* The **net debt** figures in the announcements ($13.7bn, $13.8bn) have no stated measurement date. 21CF
  consolidated borrowings less cash at 30 Jun 2017 comes to 13,750, which is *consistent with* the $13.7bn
  but is not confirmed as its definition. The $13.8bn has not been reconciled.
* The press-release **cash acquired (~$19.8bn)** does not equal the PPA cash (25,701), and the 8-K/A
  RemainCo balance sheet shows 26,337 at 31 Dec 2018. The sources do not reconcile these definitions.
* The **$2bn cash payment** from Disney to New Fox (`C97`) is the result of the merger-agreement formula
  with the final $6.5bn tax estimate. The downloaded Disney/21CF filings do not state the amount paid, so
  it is flagged as derived.

## 8. Data limitations and what is missing

Missing items are left out rather than estimated:

1. **No RemainCo cash-flow statement, capex, D&A detail or segment split.** The pro forma sources contain
   only income statements and balance sheets. Capex and working-capital history for the acquired business
   are not available on its own perimeter.
2. **No RemainCo FY2018 balance sheet at 30 Jun 2018.** The available RemainCo balance sheets are at
   31 Mar 2018 (proxy) and 31 Dec 2018 (8-K/A, after the Sky sale).
3. **No calendarisation.** That would need quarterly 10-Q data for both companies.
4. **Management forecasts** (proxy sections "Certain 21CF Forecasts" and "Certain Disney Forecasts") and the
   financial advisers' valuation analyses were **not extracted**. They are forward-looking and belong to the
   modelling stage.
5. **No market data:** share prices, volatilities, betas and interest rates for the real-options inputs.
   These come from market-data sources, not SEC filings.
6. 21CF interest and taxes paid (disclosed in notes, not on the cash-flow face) were not extracted.
7. RSN standalone history is limited to revenue (see §6). The financials of Hulu (consolidated by Disney
   from 20 Mar 2019) were not collected.
8. Some reclassification differences (§5) are recorded but their causes are only partly explained.
9. Fox Corporation's own filings were not collected. They would be needed to confirm the $2bn payment and
   New Fox's side of the separation.
10. The 8-K/A Ex. 99.2 (21CF interim statements to 31 Dec 2018) is downloaded but not yet parsed.

## 9. Readiness

**Ready for historical financial analysis of Disney and 21CF as reported** (FY2015–FY2017, plus FY2018), and
for RemainCo **income-statement** analysis on both the proxy and closing perimeters. Statements tie out, the
values are confirmed by XBRL, and every value has a source and page.

**Not yet sufficient on its own for a cash-flow valuation of the acquired business.** Items 1–5 in §8 are
needed first. The most important are RemainCo free-cash-flow drivers (capex, D&A, working capital), which
will have to be estimated from 21CF consolidated data with an explicit, documented allocation method, or
taken from the management forecasts in the proxy.
