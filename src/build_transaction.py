"""Build ``data/processed/transaction_assumptions.csv`` (deal terms by stage) and verify it.

Every reported figure carries an exact quote from its source filing. On each run
the script checks:

* the quote appears in the source text (whitespace-normalised);
* the figure as worded in the quote (``value_as_stated``) appears in the quote
  and converts to the stored ``value``/``unit``;
* the printed page number that follows the quote is recorded as ``source_page``.

Derived figures are recomputed from the records they cite (``formula``) and
compared with the stored value.

Deal stages are kept separate and must not be mixed:
  original_2017_12  original all-stock agreement (signed 13/14 Dec 2017)
  amended_2018_06   amended cash-and-stock agreement (20 Jun 2018) as described in the 2018 joint proxy
  closing_2019_03   final terms computed at closing (19-20 Mar 2019)
  accounting_fy2019 Disney's ASC 805 purchase accounting (10-Q Q2 FY2019, 10-K FY2019)
  context           competing proposal / other deal context (not Disney terms)
"""
from __future__ import annotations

import bisect
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sec_text import paged_lines  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "transaction_assumptions.csv"
CHECKS = ROOT / "data" / "processed" / "verification_checks.csv"

# fields: id, stage, category, item, value, unit, measure_basis, value_type, as_of,
#         source_id, quote, value_as_stated, formula, notes
R = []


def rec(id, stage, category, item, value, unit, measure_basis, as_of, source_id, quote,
        value_as_stated, value_type="reported", notes=""):
    R.append(dict(id=id, stage=stage, category=category, item=item, value=value, unit=unit,
                  measure_basis=measure_basis, value_type=value_type, as_of=as_of,
                  source_id=source_id, quote=quote, value_as_stated=value_as_stated,
                  formula="", notes=notes))


def der(id, stage, category, item, value, unit, measure_basis, as_of, formula, notes="", rounding=None):
    R.append(dict(id=id, stage=stage, category=category, item=item, value=value, unit=unit,
                  measure_basis=measure_basis, value_type="derived", as_of=as_of, source_id="",
                  quote="", value_as_stated="", formula=formula, notes=notes, rounding=rounding))


# ======================================================================================
# 1. ORIGINAL AGREEMENT - December 2017 (all-stock)
# ======================================================================================
S = "original_2017_12"
PR17 = "DIS_8K_20171214_EX99_1"
rec("O01", S, "announcement", "Announcement date", "2017-12-14", "date", "date", "2017-12-14", PR17,
    "BURBANK, Calif., and NEW YORK, New York, December 14, 2017", "December 14, 2017",
    notes="Agreement and Plan of Merger dated 13 Dec 2017 (Disney 8-K filed 14 Dec 2017).")
rec("O02", S, "consideration", "Exchange ratio (Disney shares per 21CF share), before tax adjustment", 0.2745,
    "ratio", "per_share_consideration", "2017-12-14", PR17,
    "shareholders of 21st Century Fox will receive 0.2745 Disney shares for each 21st Century Fox share they hold",
    "0.2745", notes="All-stock. Subject to adjustment for transaction tax liabilities (see O09-O11).")
rec("O03", S, "headline value", "Headline equity value of business to be acquired", 52400, "USD_m",
    "equity_value_headline", "2017-12-14", PR17,
    "The acquisition price implies a total equity value of approximately $52.4 billion",
    "$52.4 billion", notes="Based on the stated exchange ratio with no adjustment. Not an accounting purchase price.")
rec("O04", S, "headline value", "Net debt of 21CF to be assumed", 13700, "USD_m", "net_debt_assumed_headline",
    "2017-12-14", PR17, "Disney will also assume approximately $13.7 billion of net debt of 21st Century Fox.",
    "$13.7 billion", notes="Measurement date not stated in the release. 21CF consolidated borrowings less cash at 30 Jun 2017 "
    "is 13,750 (historical_financials.csv, derived net_debt), which is consistent but is not confirmed as the definition used.")
rec("O05", S, "headline value", "Headline total transaction value", 66100, "USD_m", "transaction_value_headline",
    "2017-12-14", PR17, "a total transaction value of approximately $66.1 billion", "$66.1 billion",
    notes="Equity value + net debt assumed, as defined by the parties. Not an accounting enterprise value.")
rec("O06", S, "share issuance", "New Disney shares to be issued (approx.)", 515, "shares_m", "share_count",
    "2017-12-14", PR17, "Disney to issue approximately 515 million new shares to 21st Century Fox shareholders",
    "515 million")
rec("O07", S, "share issuance", "21CF holders' pro forma stake in Disney (approx.)", 25, "percent", "ownership",
    "2017-12-14", PR17, "representing approximately a 25% stake in Disney on a pro forma basis", "25%")
rec("O08", S, "pricing reference", "Disney reference price used to set exchange ratio (30-trading-day VWAP, 20 Oct-1 Dec 2017)",
    102.0, "USD_per_share", "reference_price", "2017-12-01", "JPROXY_ORIG_20180530",
    "The $102 reference price per share of Disney common stock represents the volume-weighted average price of Disney common stock over the 30-trading day period from October 20, 2017 to December 1, 2017.",
    "$102")
rec("O09", S, "tax adjustment", "Transaction tax estimate used to set the exchange ratio (= New Fox cash dividend to 21CF)",
    8500, "USD_m", "adjustment_mechanism", "2017-12-14", PR17,
    "The initial exchange ratio of 0.2745 Disney shares for each 21st Century Fox share was set based on an estimate of such tax liabilities to be covered by an $8.5 billion cash dividend to 21st Century Fox from the company to be spun off.",
    "$8.5 billion")
rec("O10", S, "tax adjustment", "First tranche of downward tax adjustment absorbed by reducing the New Fox dividend", 2000, "USD_m",
    "adjustment_mechanism", "2017-12-14", PR17,
    "if the final estimate of the tax liabilities is lower than the initial estimate, the first $2 billion of that adjustment will instead be made by net reduction in the amount of the cash dividend",
    "$2 billion")
rec("O11", S, "tax adjustment", "Exchange-ratio adjustment denominator ($102 x 1,871,147,237 fully diluted 21CF shares)",
    190857.018174, "USD_m", "adjustment_mechanism", "2017-12-13", "JPROXY_ORIG_20180530",
    "exchange ratio = 0.2745 + [(the equity adjustment amount) ÷ $190,857,018,174]", "$190,857,018,174")
rec("O12", S, "share count", "21CF fully diluted shares at 13 Dec 2017", 1871.147237, "shares_m", "share_count",
    "2017-12-13", "JPROXY_ORIG_20180530",
    "multiplied by 1,871,147,237, the number of fully diluted shares of 21CF common stock as of the close of business on December 13, 2017",
    "1,871,147,237")
rec("O13", S, "market reference", "Disney closing price on 13 Dec 2017 (last trading day before announcement)", 107.61,
    "USD_per_share", "market_price", "2017-12-13", "JPROXY_ORIG_20180530",
    "Based on the closing price of Disney common stock of $107.61 on December 13, 2017", "$107.61")
rec("O14", S, "market reference", "Implied value per 21CF share at 13 Dec 2017 Disney close", 29.54, "USD_per_share",
    "per_share_consideration", "2017-12-13", "JPROXY_ORIG_20180530",
    "the merger consideration represented an implied value of $29.54 per share of 21CF common stock", "$29.54",
    notes="Market-implied value at the announcement-date price. Different from the $102-reference headline value.")
rec("O15", S, "synergies", "Expected annual cost savings (at least)", 2000, "USD_m", "synergy_guidance", "2017-12-14", PR17,
    "The acquisition is expected to yield at least $2 billion in cost savings", "$2 billion",
    notes="Management guidance, not a historical figure.")
rec("O16", S, "deal protection", "Termination fee (payable by either party, specified circumstances)", 1525, "USD_m",
    "termination_fee", "2018-05-30", "JPROXY_ORIG_20180530",
    "21CF may be required to pay Disney a termination fee of $1.525 billion, or Disney may be required to pay 21CF a termination fee of $1.525 billion",
    "$1.525 billion")
rec("O17", S, "deal protection", "Regulatory termination fee payable by Disney", 2500, "USD_m", "termination_fee",
    "2018-05-30", "JPROXY_ORIG_20180530", "Disney may be required to pay 21CF a termination fee of $2.5 billion", "$2.5 billion")
der("O90", S, "derived check", "Implied new Disney shares = 0.2745 x fully diluted 21CF shares", 0.2745 * 1871.147237,
    "shares_m", "share_count", "2017-12-13", "O02 * O12",
    notes="513.6m, against the 'approximately 515 million' in O06. The release does not explain the ~1.4m gap.")
der("O91", S, "derived check", "Implied equity value = O90 x $102 reference price", 0.2745 * 1871.147237 * 102.0,
    "USD_m", "equity_value_headline", "2017-12-13", "O02 * O12 * O08",
    notes="Reproduces the $52.4bn headline (O03) to rounding.", rounding=("O03", 100))
der("O92", S, "derived check", "Equity value + net debt", 52400 + 13700, "USD_m", "transaction_value_headline", "2017-12-14",
    "O03 + O04", notes="Reproduces the $66.1bn headline (O05).", rounding=("O05", 100))

# ======================================================================================
# 2. AMENDED AGREEMENT - June 2018 (cash and stock; 2018 joint proxy statement/prospectus)
# ======================================================================================
S = "amended_2018_06"
PR18 = "DIS_8K_20180621_EX99_1"
JP = "JPROXY_AMENDED_20180628"
rec("A01", S, "announcement", "Amended and restated merger agreement date", "2018-06-20", "date", "date", "2018-06-20", PR18,
    "BURBANK, Calif., June 20, 2018", "June 20, 2018")
rec("A02", S, "consideration", "Headline value per 21CF share (cash or stock, at holder's election)", 38.0, "USD_per_share",
    "per_share_consideration", "2018-06-20", PR18,
    "21st Century Fox shareholders may elect to receive, for each share of 21st Century Fox common stock, $38 in either cash or shares of Disney common stock",
    "$38", notes="Subject to the transaction-tax adjustment, the collar and proration.")
rec("A03", S, "consideration", "Target consideration mix: cash share", 50, "percent", "consideration_mix", "2018-06-20", PR18,
    "The overall mix of consideration paid to 21st Century Fox shareholders will be approximately 50% cash and 50% stock.", "50%")
rec("A04", S, "consideration", "Aggregate cash consideration (maximum cash amount, before tax adjustment)", 35700, "USD_m",
    "cash_consideration", "2018-06-28", JP,
    "to ensure that the aggregate 21CF cash consideration (before giving effect to the adjustment for transaction taxes described below) is equal to $35.7 billion, which we refer to as the maximum cash amount",
    "$35.7 billion")
rec("A05", S, "share issuance", "New Disney shares to be issued (approx.)", 343, "shares_m", "share_count", "2018-06-20", PR18,
    "issue approximately 343 million new shares to 21st Century Fox shareholders", "343 million")
rec("A06", S, "share issuance", "21CF holders' pro forma stake (approx.)", 19, "percent", "ownership", "2018-06-20", PR18,
    "representing about a 19% stake in Disney on a pro forma basis", "19%")
rec("A07", S, "headline value", "Headline equity value", 71300, "USD_m", "equity_value_headline", "2018-06-20", PR18,
    "The acquisition price implies a total equity value of approximately $71.3 billion", "$71.3 billion",
    notes="Assumes no tax adjustment. Not an accounting purchase price.")
rec("A08", S, "headline value", "Net debt of 21CF to be assumed", 13800, "USD_m", "net_debt_assumed_headline", "2018-06-20", PR18,
    "Disney will also assume about $13.8 billion of net debt of 21st Century Fox.", "$13.8 billion",
    notes="Measurement date not stated. Not reconciled to a specific 21CF balance sheet in this dataset.")
rec("A09", S, "headline value", "Headline total transaction value", 85100, "USD_m", "transaction_value_headline", "2018-06-20", PR18,
    "a total transaction value of approximately $85.1 billion (assuming no tax adjustment)", "$85.1 billion")
rec("A10", S, "collar", "Collar lower bound (average Disney stock price)", 93.53, "USD_per_share", "collar", "2018-06-20", PR18,
    "if the average Disney stock price at closing is between $93.53 and $114.32", "$93.53")
rec("A11", S, "collar", "Collar upper bound (average Disney stock price)", 114.32, "USD_per_share", "collar", "2018-06-20", PR18,
    "if the average Disney stock price at closing is between $93.53 and $114.32", "$114.32")
rec("A12", S, "collar", "Exchange ratio if average Disney price above $114.32", 0.3324, "ratio", "collar", "2018-06-20", PR18,
    "21st Century Fox shareholders will receive an exchange ratio of 0.3324 shares of Disney common stock if the average Disney stock price at closing is above $114.32",
    "0.3324")
rec("A13", S, "collar", "Exchange ratio if average Disney price below $93.53", 0.4063, "ratio", "collar", "2018-06-20", PR18,
    "0.4063 shares of Disney common stock if the average Disney stock price at closing is below $93.53", "0.4063")
rec("A14", S, "pricing reference", "Collar midpoint / reference price (20-trading-day VWAP to 18 Jun 2018)", 103.926,
    "USD_per_share", "reference_price", "2018-06-18", JP,
    "The midpoint of this collar, $103.926, was set based on the volume weighted average price of Disney common stock over the 20-trading day period ending on June 18, 2018.",
    "$103.926")
rec("A15", S, "consideration", "Stock consideration at the collar midpoint (New Disney shares per 21CF share)", 0.3656, "ratio",
    "per_share_consideration", "2018-06-18", JP,
    "0.3656 shares of New Disney common stock for each share of 21CF common stock for which a stock election is made", "0.3656")
rec("A16", S, "share count", "Estimated fully diluted 21CF shares (18 Jun 2018) used in the tax-adjustment formula", 1877.0,
    "shares_m", "share_count", "2018-06-18", JP,
    "1,877,000,000 represents an estimate of the fully diluted number of shares of 21CF common stock outstanding as of June 18, 2018.",
    "1,877,000,000")
rec("A17", S, "tax adjustment", "Transaction tax estimate used to set consideration (= New Fox dividend to 21CF)", 8500, "USD_m",
    "adjustment_mechanism", "2018-06-28", JP,
    "The 21CF merger consideration in the combination merger agreement was set based on an estimate of $8.5 billion for the transaction tax",
    "$8.5 billion")
rec("A18", S, "tax adjustment", "Lower edge of no-adjustment band for the transaction tax", 6500, "USD_m", "adjustment_mechanism",
    "2018-06-28", JP,
    "will be adjusted immediately prior to the consummation of the transactions if the final estimate of the transaction tax at closing is more than $8.5 billion or less than $6.5 billion",
    "$6.5 billion")
rec("A19", S, "tax adjustment", "Maximum cash payment from Disney to New Fox if final tax estimate < $8.5bn", 2000, "USD_m",
    "adjustment_mechanism", "2018-06-28", JP,
    "which cash payment will be the amount obtained by subtracting the amount of the transaction tax from $8.5 billion, up to a maximum cash payment of $2 billion",
    "$2 billion")
rec("A20", S, "deal protection", "Termination fee (either party, specified circumstances)", 1525, "USD_m", "termination_fee",
    "2018-06-28", JP,
    "21CF may be required to pay Disney a termination fee of $1.525 billion, or Disney may be required to pay 21CF a termination fee of $1.525 billion",
    "$1.525 billion")
rec("A21", S, "deal protection", "Regulatory termination fee payable by Disney", 2500, "USD_m", "termination_fee", "2018-06-28", JP,
    "Disney may be required to pay 21CF a termination fee of $2.5 billion", "$2.5 billion")
rec("A22", S, "synergies", "Expected cost synergies by 2021 (at least)", 2000, "USD_m", "synergy_guidance", "2018-06-20", PR18,
    "to yield at least $2 billion in cost synergies by 2021", "$2 billion", notes="Management guidance.")
der("A90", S, "derived check", "Equity value = $38 x 1,877m fully diluted shares", 38.0 * 1877.0, "USD_m", "equity_value_headline",
    "2018-06-18", "A02 * A16", notes="Reproduces the $71.3bn headline (A07).", rounding=("A07", 100))
der("A91", S, "derived check", "50% cash component = 0.5 x A90", 0.5 * 38.0 * 1877.0, "USD_m", "cash_consideration", "2018-06-18",
    "0.5 * A02 * A16", notes="35,663, consistent with the $35.7bn maximum cash amount (A04).", rounding=("A04", 100))
der("A92", S, "derived check", "Implied new shares = stock component / $103.926", 0.5 * 38.0 * 1877.0 / 103.926, "shares_m",
    "share_count", "2018-06-18", "0.5 * A02 * A16 / A14", notes="Consistent with ~343m (A05).", rounding=("A05", 1))
der("A93", S, "derived check", "Equity value + net debt", 71300 + 13800, "USD_m", "transaction_value_headline", "2018-06-20",
    "A07 + A08", notes="Reproduces the $85.1bn headline (A09).", rounding=("A09", 100))
der("A94", S, "derived check", "Stock ratio at midpoint = $38 / $103.926", 38.0 / 103.926, "ratio", "per_share_consideration",
    "2018-06-18", "A02 / A14", notes="Reproduces 0.3656 (A15).", rounding=("A15", 0.00005))

# ======================================================================================
# 3. CLOSING - March 2019 (final terms)
# ======================================================================================
S = "closing_2019_03"
K12 = "DIS_8K12B_20190320"
PRC = "FOX_8K_20190319B_EX99_1"
rec("C01", S, "closing", "Effective time of the 21CF merger", "2019-03-20", "date", "date", "2019-03-20", "FOX_8K_20190319A_EX99_1",
    "The Walt Disney Company’s (“Disney”) acquisition of 21CF will become effective at 12:02 a.m. Eastern Time tomorrow, March 20, 2019.",
    "March 20, 2019")
rec("C02", S, "separation", "Distribution of Fox Corporation (New Fox) shares completed", "2019-03-19", "date", "date", "2019-03-19",
    "FOX_8K_20190319A_EX99_1", "announced that it has today completed the distribution of all issued and outstanding shares of Fox Corporation",
    "", notes="Release dated 19 Mar 2019.")
rec("C03", S, "tax adjustment", "Final estimate of the Transaction Tax", 6500, "USD_m", "adjustment_mechanism", "2019-03-19", K12,
    "Based on the final estimate of the Transaction Tax (as defined in the Merger Agreement) of $6,500,000,000, the Equity Adjustment Amount was $0.",
    "$6,500,000,000")
rec("C04", S, "tax adjustment", "Equity Adjustment Amount", 0, "USD_m", "adjustment_mechanism", "2019-03-19", K12,
    "the Equity Adjustment Amount was $0.", "$0")
rec("C05", S, "pricing", "Average Parent Stock Price (15-trading-day VWAP ending 15 Mar 2019)", 114.1801, "USD_per_share",
    "reference_price", "2019-03-15", K12, "was $114.1801, the Base Exchange Ratio (as defined in the Merger Agreement) was 0.3328",
    "$114.1801", notes="Inside the $93.53-$114.32 collar, so the base value stays $38.00 before the distribution multiple.")
rec("C06", S, "pricing", "Base Exchange Ratio", 0.3328, "ratio", "collar", "2019-03-15", K12,
    "the Base Exchange Ratio (as defined in the Merger Agreement) was 0.3328", "0.3328")
rec("C07", S, "separation", "Distribution Adjustment Multiple", 1.35719, "ratio", "adjustment_mechanism", "2019-03-18",
    "FOX_8K_20190318_EX99_1", "has been calculated to be approximately 1.357190", "1.357190",
    notes="Merger consideration per remaining 21CF share is scaled by this multiple because 0.263183 of each 21CF share was "
          "exchanged for Fox Corporation stock in the distribution (0.736817 of each share remained outstanding).")
rec("C08", S, "consideration", "Per Share Value (cash consideration per remaining 21CF share)", 51.572626, "USD_per_share",
    "per_share_consideration", "2019-03-19", K12, "exchanged for $51.572626 in cash", "$51.572626",
    notes="Per 21CF share remaining after the distribution. Not comparable to the $38.00 per pre-distribution share without the multiple.")
rec("C09", S, "consideration", "Stock consideration (New Disney shares per remaining 21CF share)", 0.4517, "ratio",
    "per_share_consideration", "2019-03-19", K12, "or 0.4517 shares of common stock, par value $0.01 per share, of Disney", "0.4517")
rec("C10", S, "share issuance", "Disney shares issued to former 21CF holders", 306.844635, "shares_m", "share_count", "2019-03-20", K12,
    "Disney issued approximately 306,844,635 shares of Disney Common Stock to former holders of 21CF Common Stock.", "306,844,635")
rec("C11", S, "headline value", "Aggregate implied value of consideration (approx.)", 71000, "USD_m", "equity_value_headline",
    "2019-03-20", K12, "The aggregate implied value of the consideration paid to former holders of 21CF Common Stock pursuant to the 21CF Merger was approximately $71 billion",
    "$71 billion", notes="Market-implied, using the $114.1801 average price. Differs from the accounting purchase price (P01).")
rec("C12", S, "consideration", "Cash paid to former 21CF holders", 35700, "USD_m", "cash_consideration", "2019-03-20", K12,
    "including $35.7 billion in cash and approximately $35 billion in Disney Common Stock", "$35.7 billion")
rec("C13", S, "consideration", "Implied value of Disney stock issued (approx.)", 35000, "USD_m", "stock_consideration_implied",
    "2019-03-20", K12, "including $35.7 billion in cash and approximately $35 billion in Disney Common Stock", "$35 billion")
rec("C14", S, "elections", "21CF shares electing stock", 499.851490660098, "shares_m", "share_count", "2019-03-20", K12,
    "Holders of approximately 499,851,490.660098 shares of 21CF Common Stock outstanding (or 36.44%)", "499,851,490.660098")
rec("C15", S, "elections", "21CF shares electing cash", 704.595899751058, "shares_m", "share_count", "2019-03-20", K12,
    "Holders of approximately 704,595,899.751058 shares of 21CF Common Stock outstanding (or 51.37%)", "704,595,899.751058")
rec("C16", S, "elections", "21CF shares making no election", 167.141699891581, "shares_m", "share_count", "2019-03-20", K12,
    "Holders of approximately 167,141,699.891581 shares of 21CF Common Stock outstanding (or 12.19%)", "167,141,699.891581")
rec("C17", S, "proration", "Cash received per cash-electing share after proration", 50.66734, "USD_per_share",
    "per_share_consideration", "2019-03-20", K12, "was exchanged for 0.007929 shares of Disney Common Stock and $50.667340 in cash",
    "$50.667340", notes="The cash election was oversubscribed.")
rec("C18", S, "proration", "Stock received per cash-electing share after proration", 0.007929, "ratio", "per_share_consideration",
    "2019-03-20", K12, "was exchanged for 0.007929 shares of Disney Common Stock and $50.667340 in cash", "0.007929")
rec("C19", S, "headline value", "Cash of 21CF acquired (approx.)", 19800, "USD_m", "acquired_cash_headline", "2019-03-19", PRC,
    "Disney is also acquiring approximately $19.8 billion of cash", "$19.8 billion",
    notes="Press-release figure. The ASC 805 cash acquired is 25,701 (P03). Definitions are not reconciled in the sources.")
rec("C20", S, "headline value", "Debt of 21CF assumed (approx.)", 19200, "USD_m", "assumed_debt_headline", "2019-03-19", PRC,
    "assuming approximately $19.2 billion of debt of 21st Century Fox in the acquisition", "$19.2 billion",
    notes="Press-release figure. Fair value of borrowings recognised in purchase accounting is 21,723 (P10).")
rec("C21", S, "headline value", "Headline total transaction value at closing (approx.)", 71000, "USD_m", "transaction_value_headline",
    "2019-03-19", PRC, "a total transaction value of approximately $71 billion", "$71 billion",
    notes="Equity ~$71bn plus ~$19.2bn debt less ~$19.8bn cash (cash includes proceeds of the Oct 2018 sale of the 39% Sky stake).")
rec("C22", S, "regulatory", "Divestiture of 21CF Regional Sports Networks required (DOJ consent decree)", "", "text", "perimeter",
    "2019-03-19", PRC, "under which Disney will divest 21st Century Fox’s Regional Sports Networks", "",
    notes="RSNs are inside the acquired RemainCo perimeter but were sold in Aug 2019 (P20).")
der("C90", S, "derived check", "Per Share Value = $38.00 x Distribution Adjustment Multiple (equity adjustment = 0)", 38.0 * 1.35719,
    "USD_per_share", "per_share_consideration", "2019-03-19", "A02 * C07",
    notes="51.5732 against 51.572626 reported. The gap comes from the multiple being rounded to six decimals in the release.",
    rounding=("C08", 0.001))
der("C91", S, "derived check", "Stock ratio = Per Share Value / average Disney price", 51.572626 / 114.1801, "ratio",
    "per_share_consideration", "2019-03-19", "C08 / C05", notes="Reproduces 0.4517 (C09).", rounding=("C09", 0.00005))
der("C92", S, "derived check", "Base exchange ratio = $38 / average Disney price (inside collar)", 38.0 / 114.1801, "ratio",
    "collar", "2019-03-15", "A02 / C05", notes="Reproduces 0.3328 (C06).", rounding=("C06", 0.00005))
der("C93", S, "derived check", "Cash paid = cash-electing shares x $50.667340", 704.595899751058 * 50.66734, "USD_m",
    "cash_consideration", "2019-03-20", "C15 * C17", notes="Reproduces $35.7bn (C12).", rounding=("C12", 50))
der("C94", S, "derived check", "Shares issued = cash-electing x 0.007929 + (stock-electing + non-electing) x 0.4517",
    704.595899751058 * 0.007929 + (499.851490660098 + 167.141699891581) * 0.4517, "shares_m", "share_count", "2019-03-20",
    "C15 * C18 + (C14 + C16) * C09",
    notes="306.87m against 306.84m reported (C10). The gap reflects cash paid in lieu of fractional shares and rounding of the ratios.",
    rounding=("C10", 0.1))
der("C95", S, "derived check", "Implied stock value = shares issued x average Disney price", 306.844635 * 114.1801, "USD_m",
    "stock_consideration_implied", "2019-03-20", "C10 * C05", notes="About $35.0bn (C13).", rounding=("C13", 100))
der("C96", S, "derived check", "Remaining 21CF shares at closing = C14 + C15 + C16", 499.851490660098 + 704.595899751058 + 167.141699891581,
    "shares_m", "share_count", "2019-03-20", "C14 + C15 + C16",
    notes="Shares outstanding after the distribution (0.736817 of each pre-distribution share).")
der("C97", S, "derived check", "Cash payment from Disney to New Fox under the tax mechanism = min(8.5bn - final tax, 2bn)",
    min(8500 - 6500, 2000), "USD_m", "adjustment_mechanism", "2019-03-19", "min(A17 - C03, A19)",
    notes="Formula result from the merger-agreement mechanism. The amount actually paid is not stated in the downloaded "
          "Disney/21CF filings, so it should be confirmed against Fox Corporation filings before use.")

# ======================================================================================
# 4. ACCOUNTING - Disney ASC 805 purchase accounting (10-Q Q2 FY2019 and 10-K FY2019)
# ======================================================================================
S = "accounting_fy2019"
K19 = "DIS_10K_FY2019"
Q19 = "DIS_10Q_Q2FY2019"
rec("P01", S, "purchase price", "Total purchase price (ASC 805 consideration)", 69507, "USD_m", "purchase_consideration_accounting",
    "2019-03-20", K19, "Total purchase price | $ | 69,507", "69,507",
    notes="Uses $110.00 per Disney share (P02), not the $114.1801 VWAP. The 10-K says it includes $361m for TFCF equity awards (P05).")
rec("P02", S, "purchase price", "Stock component: 307 million Disney shares at $110.00", 33800, "USD_m", "stock_consideration_accounting",
    "2019-03-20", K19,
    "The acquisition purchase price totaled $69.5 billion, of which the Company paid $35.7 billion in cash and $33.8 billion in Disney shares (307 million shares at a price of $110.00 per share).",
    "$33.8 billion")
rec("P03", S, "purchase price", "Cash component", 35700, "USD_m", "cash_consideration", "2019-03-20", K19,
    "of which the Company paid $35.7 billion in cash", "$35.7 billion")
rec("P04", S, "purchase price", "Disney share price used for accounting stock consideration", 110.0, "USD_per_share", "market_price",
    "2019-03-20", K19, "307 million shares at a price of $110.00 per share", "$110.00")
rec("P05", S, "purchase price", "Portion of purchase price for TFCF equity awards settled or replaced", 361, "USD_m",
    "purchase_consideration_accounting", "2019-03-20", K19,
    "The purchase price for TFCF includes $361 million related to TFCF awards that were settled or replaced in connection with the acquisition",
    "$361 million")
ALLOC = [  # (id, item, initial (10-Q, as restated in 10-K table), adjustment, updated)
    ("P10", "Cash and cash equivalents", 25666, 35, 25701),
    ("P11", "Receivables", 4746, 484, 5230),
    ("P12", "Film and television costs", 20120, -2322, 17798),
    ("P13", "Investments", 1471, -507, 964),
    ("P14", "Intangible assets", 20385, -2504, 17881),
    ("P15", "Net assets held for sale", 11704, -338, 11366),
    ("P16", "Accounts payable and other liabilities", -10753, -1606, -12359),
    ("P17", "Borrowings", -21723, 0, -21723),
    ("P18", "Deferred income taxes", -6497, 1164, -5333),
    ("P19", "Other net liabilities acquired", -3865, -93, -3958),
    ("P1A", "Noncontrolling interests", -10638, 230, -10408),
    ("P1B", "Goodwill", 43751, 5334, 49085),
    ("P1C", "Fair value of net assets acquired", 74367, -123, 74244),
    ("P1D", "Less: Disney's previously held 30% interest in Hulu", -4860, 123, -4737),
]


def fmt_num(v):
    return f"({abs(v):,})" if v < 0 else f"{v:,}"


for pid, item, init, adj, upd in ALLOC:
    quote_upd = f"{item}".split(":")[0]
    rec(pid, S, "purchase price allocation", f"PPA updated allocation (FY2019 10-K): {item}", upd, "USD_m", "purchase_price_allocation",
        "2019-09-28", K19, quote_upd, "", notes=f"Initial allocation (Q2 FY2019 10-Q): {init:,}; adjustment: {adj:,}. "
        "Sign as presented: liabilities and NCI negative. Value checked against the parsed allocation table.")
    R[-1]["table_check"] = (item, upd, init)
rec("P20", S, "post-closing", "RSNs sold (approximate proceeds)", 11000, "USD_m", "divestiture", "2019-08-31", K19,
    "The Company sold the RSNs in August 2019 for approximately $11 billion.", "$11 billion")
rec("P21", S, "post-closing", "Gain on remeasuring Disney's previously held 30% Hulu interest", 4800, "USD_m", "accounting_gain",
    "2019-03-20", K19, "recorded a one-time gain of $4.8 billion (Hulu Gain)", "$4.8 billion")
rec("P22", S, "financing", "Bridge loans drawn to fund the cash consideration", 31100, "USD_m", "financing", "2019-03-20", K19,
    "the Company borrowed $31.1 billion under two 364-day unsecured bridge loan facilities", "$31.1 billion")
rec("P23", S, "financing", "Bridge loan repaid with cash acquired (21 Mar 2019)", 16100, "USD_m", "financing", "2019-03-21", K19,
    "the Company repaid one bridge loan facility in the amount of $16.1 billion, utilizing cash acquired in the TFCF transaction", "$16.1 billion")
rec("P24", S, "debt", "Fair value of TFCF public debt assumed", 21200, "USD_m", "assumed_debt_accounting", "2019-03-20", K19,
    "the Company assumed public debt with a fair value of $21.2 billion", "$21.2 billion")
rec("P25", S, "debt", "Principal of TFCF public debt assumed", 17400, "USD_m", "assumed_debt_accounting", "2019-03-20", K19,
    "(principal balance of $17.4 billion)", "$17.4 billion")
rec("P26", S, "cash flow", "Cash paid for TFCF less cash acquired (fiscal 2019 acquisitions spend)", 9900, "USD_m", "cash_flow",
    "2019-09-28", K19, "The fiscal 2019 spending of $9.9 billion on acquisitions reflects $35.7 billion of cash paid to acquire TFCF less $25.7 billion of cash acquired",
    "$9.9 billion")
rec("P27", S, "cash flow", "Tax obligations paid in FY2019 from the Fox spin-off and the RSN sale (approx.)", 7600, "USD_m", "cash_flow",
    "2019-09-28", K19, "the payment of approximately $7.6 billion of tax obligations that arose from the spin-off of Fox Corporation in connection with the TFCF acquisition and the sale of the RSNs",
    "$7.6 billion")
rec("P28", S, "results", "TFCF revenues included in Disney FY2019 since acquisition", 6950, "USD_m", "post_acquisition_results",
    "2019-09-28", K19, "Revenues | $ | 6,950", "6,950")
rec("P29", S, "results", "Pro forma Disney revenues FY2019 (as if acquired 1 Oct 2017)", 78116, "USD_m", "pro_forma_results",
    "2019-09-28", K19, "Revenues | $ | 78,116 | $ | 76,318", "78,116")
rec("P30", S, "results", "Pro forma Disney revenues FY2018 (as if acquired 1 Oct 2017)", 76318, "USD_m", "pro_forma_results",
    "2018-09-29", K19, "Revenues | $ | 78,116 | $ | 76,318", "76,318")
rec("P31", S, "costs", "Acquisition-related expenses incurred in FY2019", 300, "USD_m", "transaction_costs", "2019-09-28", K19,
    "the Company incurred $0.3 billion of acquisition-related expenses", "$0.3 billion")
rec("P32", S, "purchase price", "Initial total purchase price as first reported (Q2 FY2019 10-Q)", 69500, "USD_m",
    "purchase_consideration_accounting", "2019-03-30", Q19, "The acquisition purchase price totaled $69.5 billion", "$69.5 billion")
der("P90", S, "derived check", "Cash + stock components = total purchase price", 35700 + 33800, "USD_m",
    "purchase_consideration_accounting", "2019-03-20", "P03 + P02", notes="69.5bn, consistent with P01 (69,507).",
    rounding=("P01", 50))
der("P91", S, "derived check", "Stock component = 307m shares x $110.00", 307 * 110.0, "USD_m", "stock_consideration_accounting",
    "2019-03-20", "307 * P04", notes="33,770, consistent with $33.8bn (P02).", rounding=("P02", 50))
der("P92", S, "derived check", "Market-implied closing value less accounting purchase price", 71000 - 69507, "USD_m", "bridge",
    "2019-03-20", "C11 - P01",
    notes="About $1.5bn, mainly the share price used ($114.1801 VWAP vs $110.00 for accounting). Shows why these measures must be kept apart.")
der("P93", S, "derived check", "Sum of updated PPA lines = total purchase price",
    sum(u for _, it, _, _, u in ALLOC if not it.startswith("Fair value")), "USD_m", "purchase_price_allocation", "2019-09-28",
    "sum(P10..P1B) + P1D", notes="Ties to 69,507 (P01).", rounding=("P01", 1.5))

# ======================================================================================
# 5. CONTEXT - competing proposal (not Disney terms)
# ======================================================================================
S = "context"
rec("X01", S, "competing bid", "Comcast unsolicited proposal for RemainCo (13 Jun 2018), cash per 21CF share", 35.0, "USD_per_share",
    "competing_offer", "2018-06-13", JP,
    "unsolicited, non-binding proposal to acquire the RemainCo businesses for $35.00 per share in cash, subject to an adjustment for transaction taxes, reflecting a total unadjusted equity value of $65 billion for 21CF",
    "$35.00", notes="Context only; this proposal was not accepted.")
rec("X02", S, "competing bid", "Comcast proposal implied unadjusted equity value", 65000, "USD_m", "competing_offer", "2018-06-13", JP,
    "reflecting a total unadjusted equity value of $65 billion for 21CF", "$65 billion")
rec("X03", S, "sky", "Sale of 21CF's 39% Sky interest to Comcast (Oct 2018)", 15100, "USD_m", "divestiture", "2018-10-31",
    "DIS_8KA_20190327_EX99_4", "to Comcast Corporation (“Comcast”) for approximately £11.6 billion ($15.1 billion)", "$15.1 billion",
    notes="Explains part of the large cash balance in RemainCo at closing. Sky was not acquired by Disney.")


# ======================================================================================
# Verification helpers
# ======================================================================================
def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()


_text_cache = {}


def doc_index(doc_id):
    """Whitespace-normalised full text, line start offsets and each line's printed page number."""
    if doc_id not in _text_cache:
        starts, pages, parts, pos = [], [], [], 0
        for line, page in paged_lines(doc_id):
            n = norm(line)
            starts.append(pos)
            pages.append(page)
            parts.append(n)
            pos += len(n) + 1
        _text_cache[doc_id] = (" ".join(parts), starts, pages)
    return _text_cache[doc_id]


def find_quote(doc_id, quote):
    """(found, printed page of the line where the quote starts)."""
    text, starts, pages = doc_index(doc_id)
    q = norm(quote)
    i = text.find(q)
    if i < 0:
        return False, ""
    li = bisect.bisect_right(starts, i) - 1
    return True, pages[li]


def stated_to_value(stated: str, unit: str):
    s = stated.replace(",", "").replace("$", "").strip()
    m = re.match(r"^(-?\d+(?:\.\d+)?)\s*(billion|million)?%?$", s)
    if not m:
        return None
    v = float(m.group(1))
    scale = m.group(2)
    if unit == "USD_m":
        if scale == "billion":
            return v * 1000
        if scale == "million":
            return v
        # no scale word: raw dollar amounts (e.g. $6,500,000,000) vs table figures already in millions
        return v / 1e6 if abs(v) >= 1e7 else v
    if unit == "shares_m":
        return v if scale == "million" else v / 1e6
    return v


def ppa_table_check(item, upd, init):
    """Confirm the PPA values against the parsed allocation table in the FY2019 10-K."""
    from sec_tables import load_tables
    for t in load_tables(K19):
        labs = [r[0] for r in t.rows]
        if "Total purchase price" in labs and "Goodwill" in labs and t.page:
            for lab, vals, _ in t.rows:
                if norm(lab) == norm(item) and len(vals) == 3:
                    return vals[0] == init and vals[2] == upd, t.page
    return False, ""


def main():
    checks = []
    by_id = {r["id"]: r for r in R}
    for r in R:
        r.setdefault("rounding", None)
        r["source_page"], r["verification_status"] = "", ""
        if r["value_type"] == "reported":
            if "table_check" in r:
                ok, page = ppa_table_check(*r.pop("table_check"))
                r["source_page"] = page
                r["verification_status"] = "verified_table_value" if ok else "FAILED_table_value"
                checks.append(("transaction_table_value", r, ok, f"PPA table page {page}"))
                continue
            found, page = find_quote(r["source_id"], r["quote"])
            r["source_page"] = page
            ok_stated = True
            if r["value_as_stated"]:
                ok_stated = norm(r["value_as_stated"]) in norm(r["quote"])
                if isinstance(r["value"], (int, float)) and r["unit"] not in ("date", "text"):
                    sv = stated_to_value(r["value_as_stated"], r["unit"])
                    ok_stated = ok_stated and sv is not None and abs(sv - float(r["value"])) <= 1e-6 * max(1, abs(sv))
            r["verification_status"] = "verified_quote_and_value" if (found and ok_stated) else (
                "FAILED_quote_not_found" if not found else "FAILED_value_mismatch")
            checks.append(("transaction_quote", r, found and ok_stated, f"page {page}"))
        else:
            ref = r.get("rounding")
            if ref:
                target = by_id[ref[0]]["value"]
                ok = abs(float(r["value"]) - float(target)) <= ref[1]
                r["verification_status"] = f"derived_consistent_with_{ref[0]}" if ok else f"DERIVED_INCONSISTENT_with_{ref[0]}"
                checks.append(("transaction_derived", r, ok, f"vs {ref[0]}={target} tol {ref[1]}"))
            else:
                r["verification_status"] = "derived_no_reported_counterpart"
    for r in R:
        if r["value_type"] == "reported":
            r["source_location"] = (f"printed page {r['source_page']}" if r["source_page"]
                                    else "no printed page number on this page of the filing; locate by quote")
        else:
            r["source_location"] = ""
    fields = ["id", "stage", "category", "item", "value", "unit", "measure_basis", "value_type", "as_of", "source_id",
              "source_page", "source_location", "quote", "value_as_stated", "formula", "verification_status", "notes"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in R:
            if isinstance(r["value"], float):
                r["value"] = f"{r['value']:.6f}".rstrip("0").rstrip(".")
            w.writerow(r)
    # append to the verification log (replace previous transaction checks)
    existing = []
    if CHECKS.exists():
        with CHECKS.open(encoding="utf-8") as fh:
            existing = [c for c in csv.DictReader(fh) if not c["check_type"].startswith("transaction_")]
    with CHECKS.open("w", newline="", encoding="utf-8") as fh:
        cf = ["check_type", "entity", "source_id", "fiscal_period", "item", "expected", "observed", "status", "detail"]
        w = csv.DictWriter(fh, fieldnames=cf)
        w.writeheader()
        w.writerows(existing)
        for ctype, r, ok, detail in checks:
            w.writerow({"check_type": ctype, "entity": "", "source_id": r["source_id"], "fiscal_period": r["as_of"],
                        "item": f"{r['id']} {r['item']}", "expected": r["value"], "observed": r["verification_status"],
                        "status": "pass" if ok else "fail", "detail": detail})
    bad = [r["id"] for r in R if "FAILED" in r["verification_status"] or "INCONSISTENT" in r["verification_status"]]
    print(f"{len(R)} records -> {OUT.relative_to(ROOT)}; failures: {bad or 'none'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
