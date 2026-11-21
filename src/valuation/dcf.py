"""FCFF discounted cash flow engine.

Reuses the structure of ``dcf_valuation`` in notebooks/MA_Real_Options_Valuation.ipynb (explicit-period PV +
Gordon-growth terminal value), extended with dated fiscal periods, partial first periods and a
mid-period convention.

Per forecast year:  EBIT = EBITDA - D&A;  taxes = tax_rate x EBIT;  NOPAT = EBIT - taxes;
                    FCFF = NOPAT + D&A - capex - investment in working capital/content.
Only the part of a fiscal year that falls after the valuation date is counted:
  fraction = (coverage_end - max(valuation_date, coverage_start)) / (coverage_end - coverage_start),
and that cash flow is discounted from the midpoint of the remaining part (mid-period convention).
Terminal value (Gordon growth) at the end of the last forecast year: TV = FCFF_terminal x (1 + g) / (WACC - g),
discounted from that date (end-period, which is conservative relative to mid-period).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


def _yf(a: date, b: date) -> float:
    return (b - a).days / 365.25


@dataclass
class Year:
    fy: str
    coverage_start: date
    coverage_end: date
    revenue: float
    ebitda: float
    da: float
    capex: float
    dnwc: float
    tax_rate: float
    fcff_reported: float | None = None   # management UFCF, if the case is built to match it
    rows: dict = field(default_factory=dict)

    def compute(self):
        ebit = self.ebitda - self.da
        tax = self.tax_rate * ebit
        nopat = ebit - tax
        fcff = nopat + self.da - self.capex - self.dnwc
        self.rows = {"revenue": self.revenue, "ebitda": self.ebitda, "ebitda_margin": self.ebitda / self.revenue,
                     "da": self.da, "ebit": ebit, "ebit_margin": ebit / self.revenue, "taxes_on_ebit": tax, "nopat": nopat,
                     "capex": self.capex, "dnwc": self.dnwc, "fcff": fcff}
        return fcff


def value(years: list[Year], valuation_date: date, wacc: float, g: float, terminal_fcff_base: float):
    if wacc <= g:
        raise ValueError(f"WACC {wacc:.4f} must exceed terminal growth {g:.4f}")
    table, pv_sum = [], 0.0
    for y in years:
        fcff = y.compute()
        span = (y.coverage_end - y.coverage_start).days
        start = max(valuation_date, y.coverage_start)
        frac = max(0.0, (y.coverage_end - start).days / span) if span else 0.0
        if frac == 0:
            continue
        mid = start + (y.coverage_end - start) / 2
        t = _yf(valuation_date, mid)
        df = (1 + wacc) ** -t
        pv = fcff * frac * df
        pv_sum += pv
        table.append({**y.rows, "fy": y.fy, "fraction_after_valuation_date": frac, "discount_time_years": t,
                      "discount_factor": df, "pv_fcff": pv})
    t_n = _yf(valuation_date, years[-1].coverage_end)
    tv = terminal_fcff_base * (1 + g) / (wacc - g)
    pv_tv = tv * (1 + wacc) ** -t_n
    return {"table": table, "pv_explicit": pv_sum, "terminal_fcff_base": terminal_fcff_base, "terminal_value": tv,
            "terminal_discount_time_years": t_n, "pv_terminal": pv_tv, "enterprise_value": pv_sum + pv_tv,
            "tv_share_of_ev": pv_tv / (pv_sum + pv_tv), "wacc": wacc, "g": g}
