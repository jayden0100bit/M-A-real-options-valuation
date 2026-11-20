import { useEffect, useState } from "react";
import type { AdParams, ModelA, ModelB } from "./finance";

// Shapes of public/data/dashboard.json (written by src/export_dashboard.py). Fields not used by the UI are omitted.
export type Row = Record<string, string | number | null>;
export interface Perspective {
  label: string; basis: string; tax: number; g: number; shares: number;
  wacc: Record<"rf" | "erp" | "relevered_beta" | "cost_of_equity" | "kd_pretax" | "kd_aftertax" | "weight_debt" | "wacc", number>;
  bridge: Record<"plus_sky_39pct_stake" | "plus_other_investments_book" | "less_debt" | "plus_cash" | "less_noncontrolling_interests", number>;
  outputs: Record<"enterprise_value_ops" | "pv_explicit_fcff" | "pv_terminal_value" | "equity_value" | "equity_value_per_21cf_share" | "terminal_value_share_of_ev", number>;
  scenarios: Record<"bear" | "base" | "bull", number>;
  grid: { row_value: number; col_value: number; equity_per_share: number; enterprise_value_ops: number }[];
  sensitivity: { table: string; row_value: number; enterprise_value_ops: number; equity_per_share: number }[];
  comps: { case: string; v: number }[];
  projection: Row[];
  model: (ModelA & { kind: "estimate" }) | (ModelB & { kind: "management" });
}
export interface Dashboard {
  meta: { checks_total: number; checks_failed: number; checks_by_stage: Record<string, number>; sources: number; repo: string; note: string };
  timeline: { date: string; title: string; detail: string; source: string }[];
  deal: {
    unaffected_price: number; accounting_purchase_price: number; market_implied_closing: number; package_premium_closing: number; package_value_closing: number;
    stages: { stage: string; per_share: number; equity_headline: number; ev_headline: number; cash: number; stock: number; premium: number; implied_ev_ebitda: number }[];
    ppa: { id: string; item: string; value: number }[];
    terms: Row[];
  };
  historical: { entity: string; fiscal_period: string; period_end: string; metric: string; value: number | null; unit: string; value_type: string }[];
  segments: { entity: string; fiscal_period: string; segment: string; metric: string; value: number | null; value_type: string }[];
  valuation: Record<"A_announcement_2017-12" | "B_proxy_2018-05", Perspective>;
  comps: Row[];
  forecasts: Row[];
  synergy: {
    assumptions: Row[]; values: { perspective: string; case: string; metric: string; v: number }[]; cashflows: Row[];
    sensitivity: { perspective: string; case: string; v: number }[]; justification: { perspective: string; case: string; metric: string; v: number | null }[];
    reference: Row[];
    model: { fy: number[]; scenarios: Record<"bear" | "base" | "bull", { run_rate: number; phase: number[]; g: number; ic_mult: number; note: string }>; ic_phase: number[];
             timing: Record<string, { t: number[]; t_n: number }> };
  };
  accretion: { params: AdParams; inputs: Row[]; cases: { case: string; fiscal_year: string; metric: string; v: number }[]; anchor: Row[]; sensitivity_fy2021: { case: string; metric: string; v: number }[] };
  options: { inputs: { parameter: string; value: number; unit: string; value_type: string; method: string; sensitivity_low: number | null; sensitivity_high: number | null }[];
             outputs: { section: string; case: string; metric: string; v: number; notes: string | null }[]; convergence: Row[] };
  montecarlo: {
    inputs: Row[]; summary: Row[]; convergence: Row[]; tornado: Row[]; scenarios: Row[]; histogram_bn: Record<string, { edges: number[]; counts: number[] }>;
    paid: Record<string, number>; seed: number; n: number; option_value: number;
    synergy_base: { run_rate: number; g: number; phase: number[]; ic_phase: number[]; t: number[]; t_n: number };
  };
  sources: { source_id: string; form: string; filing_date: string | null; description: string; url: string }[];
  summary: Row[];
}

export function useDashboard() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetch("/data/dashboard.json")
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);
  return { data, error };
}

export const PERSPECTIVES = ["A_announcement_2017-12", "B_proxy_2018-05"] as const;
export type PerspectiveKey = (typeof PERSPECTIVES)[number];
