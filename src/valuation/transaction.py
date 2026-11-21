"""Transaction analysis: original offer (Dec 2017), amended offer (Jun 2018), closing (Mar 2019).

Value concepts are kept apart in the output (``metric`` names):
  equity_value_headline        parties' announced equity value
  enterprise_value_headline    parties' equity value + net debt assumed ("transaction value")
  market_implied_equity_value  consideration valued at market prices on the stated date
  accounting_purchase_price    Disney's ASC 805 purchase price
  cash_consideration / stock_consideration_*
  per_share_value / premium_*  per 21CF share
All deal terms come from transaction_assumptions.csv (verified in Stage 1). Unaffected 21CF prices come from
the May 2018 proxy closing-price table (p.56). The Fox Corporation price comes from Yahoo Finance.

Unaffected date: 3 Nov 2017, the last trading day before press reports of the talks (proxy p.56).
Like-for-like issue: 21CF holders kept New Fox in addition to the Disney consideration. Premiums on the
consideration alone therefore *understate* what holders received. A closing-date "package" premium (Disney
consideration + Fox Corporation shares) is shown separately. It is nominal (not market-adjusted), because the
16-month gap includes general market movement.
"""
from __future__ import annotations

import pandas as pd

import market_data as md
from sec_tables import load_tables

PROC = md.ROOT / "data" / "processed"


def build(out, check, CHECKS, bridgeA, bridgeB):
    TA = pd.read_csv(PROC / "transaction_assumptions.csv", dtype={"source_page": str})
    v = lambda i: float(TA[TA.id == i].value.iloc[0])
    src = lambda i: f"transaction_assumptions {i}"

    t = load_tables("JPROXY_ORIG_20180530")[329]
    assert t.page == "56"
    px = {r[0]: r[1] for r in t.rows[1:]}
    foxa_u, fox_u, dis_u = px["November 3, 2017"][0], px["November 3, 2017"][1], px["November 3, 2017"][2]
    foxa_d, fox_d, dis_d = px["December 13, 2017"][0], px["December 13, 2017"][1], px["December 13, 2017"][2]
    sh_a, sh_b = 1052.536963, 798.520953  # 21CF 10-K FY2017 cover (9 Aug 2017)
    unaff = (foxa_u * sh_a + fox_u * sh_b) / (sh_a + sh_b)
    S = "transaction"
    note_px = "JPROXY_ORIG_20180530 p.56 closing-price table; class weights from 21CF FY2017 10-K cover share counts"
    out(S, "Unaffected price", "2017-11-03", "21cf_unaffected_price_weighted", unaff, "USD_per_share", "derived",
        f"FOXA {foxa_u} / FOX {fox_u}, weighted by class share counts ({note_px})")
    out(S, "Unaffected price", "2017-12-13", "21cf_price_pre_announcement_weighted", (foxa_d * sh_a + fox_d * sh_b) / (sh_a + sh_b),
        "USD_per_share", "derived", "Affected by press reports from 6 Nov 2017; not used for premiums")

    # ---------------- original offer
    O = "original_2017_12"
    ratio = v("O02")
    ref = v("O08")
    per_share_ref = ratio * ref
    per_share_mkt = ratio * dis_d
    check("transaction_premium", "0.2745 x Disney 13 Dec 2017 close = proxy implied value $29.54", v("O14"), per_share_mkt, 0.006, O)
    out(S, O, "terms", "per_share_value_at_102_reference", per_share_ref, "USD_per_share", "derived", f"{src('O02')} x {src('O08')}")
    out(S, O, "terms", "per_share_value_at_2017-12-13_close", per_share_mkt, "USD_per_share", "derived", f"{src('O02')} x Disney close {dis_d}")
    for lab, ps in (("at_102_reference", per_share_ref), ("at_2017-12-13_close", per_share_mkt)):
        out(S, O, "premium", f"premium_consideration_only_{lab}", ps / unaff - 1, "ratio", "derived",
            "vs weighted unaffected 21CF price (3 Nov 2017). Understates the premium because holders also kept New Fox.")
    out(S, O, "values", "equity_value_headline", v("O03"), "USD_m", "reported", src("O03"))
    out(S, O, "values", "enterprise_value_headline", v("O05"), "USD_m", "reported", src("O05") + " (= equity + ~$13.7bn net debt assumed)")
    out(S, O, "values", "market_implied_equity_value_2017-12-13", per_share_mkt * v("O12"), "USD_m", "derived",
        f"{per_share_mkt:.2f} x {v('O12'):,.3f}m fully diluted shares ({src('O12')})")
    out(S, O, "values", "cash_consideration", 0.0, "USD_m", "reported", "all-stock offer")
    ev_ops = v("O05") - bridgeA["sky"] - bridgeA["other_inv"]
    out(S, O, "implied multiple", "headline_ev_less_sky_and_investments", ev_ops, "USD_m", "estimate",
        f"headline transaction value - Sky stake estimate {bridgeA['sky']:,.0f} - other investments {bridgeA['other_inv']:,.0f}")

    # ---------------- amended offer
    A = "amended_2018_06"
    out(S, A, "terms", "per_share_value", v("A02"), "USD_per_share", "reported", src("A02") + " (inside the collar)")
    out(S, A, "premium", "premium_consideration_only", v("A02") / unaff - 1, "ratio", "derived",
        "vs weighted unaffected price (3 Nov 2017); excludes New Fox, so understated")
    out(S, A, "values", "equity_value_headline", v("A07"), "USD_m", "reported", src("A07"))
    out(S, A, "values", "enterprise_value_headline", v("A09"), "USD_m", "reported", src("A09") + " (= equity + ~$13.8bn net debt)")
    out(S, A, "values", "cash_consideration", v("A04"), "USD_m", "reported", src("A04"))
    out(S, A, "values", "stock_consideration_at_103.926_reference", v("A07") - v("A04"), "USD_m", "derived", "headline equity - cash")
    ev_ops_a = v("A09") - bridgeB["sky"] - bridgeB["other_inv"]
    out(S, A, "implied multiple", "headline_ev_less_sky_and_investments", ev_ops_a, "USD_m", "estimate",
        f"headline transaction value - Sky stake (B estimate at Comcast's £12.50) {bridgeB['sky']:,.0f} - other investments {bridgeB['other_inv']:,.0f}")

    # ---------------- closing
    C = "closing_2019_03"
    psv, mult = v("C08"), v("C07")
    remaining = 0.736817
    per_orig = psv * remaining
    check("transaction_premium", "$51.572626 x 0.736817 remaining share = $38.00 per original 21CF share", v("A02"), per_orig, 0.005, C)
    foxa, foxa_d = md.price_asof("FOXA", "2019-03-19")
    newfox_per_orig = foxa / 3.0
    out(S, C, "terms", "disney_consideration_per_original_21cf_share", per_orig, "USD_per_share", "derived",
        f"{src('C08')} x 0.736817 (share remaining after the distribution, FOX_8K_20190318_EX99_1)")
    out(S, C, "terms", "fox_corporation_shares_per_original_21cf_share", 1 / 3, "shares", "reported",
        "0.263183 of each 21CF share exchanged for 1/3 Fox Corporation share (FOX_8K_20190318_EX99_1)")
    out(S, C, "terms", "fox_corporation_value_per_original_21cf_share", newfox_per_orig, "USD_per_share", "derived",
        f"1/3 x FOXA first close {foxa:.2f} on {foxa_d} (Yahoo Finance). Class A price used for both classes (approximation).")
    pkg = per_orig + newfox_per_orig
    out(S, C, "premium", "package_value_per_original_21cf_share", pkg, "USD_per_share", "derived", "Disney consideration + Fox Corporation shares")
    out(S, C, "premium", "premium_package_nominal", pkg / unaff - 1, "ratio", "derived",
        "Nominal premium over the 3 Nov 2017 unaffected price. Not adjusted for market movement over 16 months.")
    out(S, C, "premium", "premium_disney_consideration_only", per_orig / unaff - 1, "ratio", "derived", "excludes Fox Corporation shares")
    out(S, C, "values", "market_implied_equity_value", v("C11"), "USD_m", "reported", src("C11") + " (stock at the $114.1801 average price)")
    out(S, C, "values", "cash_consideration", v("C12"), "USD_m", "reported", src("C12"))
    out(S, C, "values", "stock_consideration_implied", v("C13"), "USD_m", "reported", src("C13"))
    out(S, C, "values", "enterprise_value_headline", v("C21"), "USD_m", "reported", src("C21"))
    out(S, C, "values", "enterprise_value_derived", v("C11") + v("C20") - v("C19"), "USD_m", "derived",
        f"market-implied equity {v('C11'):,.0f} + debt assumed {v('C20'):,.0f} - cash acquired {v('C19'):,.0f} (release figures, rounded)")
    out(S, C, "values", "accounting_purchase_price", v("P01"), "USD_m", "reported", src("P01") + " (ASC 805; stock at $110.00)")
    out(S, C, "values", "accounting_vs_market_implied_gap", v("C11") - v("P01"), "USD_m", "derived", "mainly $114.18 vs $110.00 share price")

    # implied EV/EBITDA multiples (derived; EBITDA from the verified datasets)
    hf = pd.read_csv(PROC / "historical_financials.csv", low_memory=False)
    fr = pd.read_csv(PROC / "financial_ratios.csv")
    rc18 = float(fr[(fr.entity == "RemainCo") & (fr.fiscal_period == "FY2018") & (fr.metric == "ebitda")].value.iloc[0])
    va = pd.read_csv(PROC / "dcf_assumptions.csv") if (PROC / "dcf_assumptions.csv").exists() else None
    out(S, O, "implied multiple", "ev_ops_to_remainco_fy2017_ebitda_estimate", ev_ops / 4373.0, "x", "estimate",
        "EV of operations / RemainCo FY2017 EBITDA derived from public Dec 2017 information (4,373)")
    out(S, A, "implied multiple", "ev_ops_to_remainco_fy2017_pro_forma_ebitda", ev_ops_a / 4116.0, "x", "estimate",
        "EV of operations / RemainCo FY2017 pro forma EBITDA before D&A and impairment (4,116; May 2018 proxy p.223)")
    out(S, A, "implied multiple", "ev_ops_to_disney_fy2018e_ebitda", ev_ops_a / 4506.0, "x", "estimate",
        "EV of operations / Disney management FY2018E EBITDA (4,506; May 2018 proxy p.129)")
    out(S, C, "implied multiple", "ev_derived_to_remainco_fy2018_ebitda", (v("C11") + v("C20") - v("C19")) / rc18, "x", "derived",
        f"Closing EV (derived) / RemainCo FY2018 EBITDA {rc18:,.0f} (financial_ratios.csv; 8-K/A closing perimeter). "
        "Sky was already sold, and its proceeds are in the cash acquired.")
