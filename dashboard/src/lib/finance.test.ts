// The browser engine must reproduce the Python pipeline's exported results.
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { accretion, binomialCall, blackScholesCall, dcfA, dcfB, percentile, simulate, synergyValue, type ModelA, type ModelB } from "./finance";
import type { Dashboard } from "./data";

const D: Dashboard = JSON.parse(readFileSync(new URL("../../public/data/dashboard.json", import.meta.url), "utf-8"));
const A = D.valuation["A_announcement_2017-12"], B = D.valuation["B_proxy_2018-05"];
const bridgeSum = (p: typeof A) => p.bridge.plus_sky_39pct_stake + p.bridge.plus_other_investments_book - p.bridge.less_debt + p.bridge.plus_cash - p.bridge.less_noncontrolling_interests;

describe("DCF engines reproduce Stage 3", () => {
  it("A: estimate-based DCF", () => {
    const r = dcfA(A.model as ModelA, { g: A.g, tax: A.tax });
    expect(Math.abs(r.ev - A.outputs.enterprise_value_ops)).toBeLessThan(2);
    expect(Math.abs((r.ev + bridgeSum(A)) / A.shares - A.outputs.equity_value_per_21cf_share)).toBeLessThan(0.002);
  });
  it("B: management-forecast DCF", () => {
    const r = dcfB(B.model as ModelB, { g: B.g, tax: B.tax });
    expect(Math.abs(r.ev - B.outputs.enterprise_value_ops)).toBeLessThan(1);
  });
  it("B: margin and growth sensitivities", () => {
    for (const [table, shift] of [["ebitda_margin_shift", 0.02], ["revenue_growth_shift", -0.02]] as const) {
      const ref = B.sensitivity.find((s) => s.table === table && Math.abs(s.row_value - shift) < 1e-9)!;
      const r = dcfB(B.model as ModelB, { g: B.g, tax: B.tax, ...(table === "ebitda_margin_shift" ? { marginShift: shift } : { growthShift: shift }) });
      expect(Math.abs(r.ev - ref.enterprise_value_ops)).toBeLessThan(1.5);
    }
  });
});

describe("synergy engine reproduces Stage 4", () => {
  it("base / bear / bull net value for both perspectives", () => {
    for (const p of ["A_announcement_2017-12", "B_proxy_2018-05"] as const) {
      for (const c of ["bear", "base", "bull"] as const) {
        const sc = D.synergy.model.scenarios[c];
        const v = synergyValue({ runRate: sc.run_rate, phase: sc.phase, icPhase: D.synergy.model.ic_phase, icMult: sc.ic_mult, g: sc.g,
          rate: D.valuation[p].model.wacc, tax: D.valuation[p].tax, timing: D.synergy.model.timing[p] });
        const ref = D.synergy.values.find((x) => x.perspective === p && x.case === c && x.metric === "net_synergy_value")!.v;
        expect(Math.abs(v.net - ref)).toBeLessThan(2);
      }
    }
  });
});

describe("accretion engine reproduces Stage 4", () => {
  const get = (c: string, fy: string, m: string) => D.accretion.cases.find((x) => x.case.startsWith(c) && x.fiscal_year === fy && x.metric === m)!.v;
  it("base, RSN-retained and original-structure cases", () => {
    const base = accretion(D.accretion.params), keep = accretion(D.accretion.params, { includeRsn: true }), orig = accretion(D.accretion.params, { original: true });
    for (const fy of ["FY2020", "FY2021", "FY2022"]) {
      expect(base[fy].accAdj).toBeCloseTo(get("base", fy, "accretion_adjusted"), 5);
      expect(base[fy].accGaap).toBeCloseTo(get("base", fy, "accretion_gaap_basis"), 5);
      expect(keep[fy].accAdj).toBeCloseTo(get("variant: RSNs retained", fy, "accretion_adjusted"), 5);
      expect(orig[fy].accAdj).toBeCloseTo(get("variant: original Dec 2017 all-stock", fy, "accretion_adjusted"), 5);
    }
  });
});

describe("option engine reproduces Stage 5", () => {
  const inp = (p: string) => D.options.inputs.find((x) => x.parameter === p)!.value;
  const out = (m: string) => D.options.outputs.find((x) => x.metric === m && (x.case === "base" || x.case === "q = 0"))!.v;
  it("Black-Scholes and CRR", () => {
    const S = inp("S_underlying_pv_revenue_synergies"), K = inp("K_exercise_cost"), r = inp("r_risk_free"), T = inp("T_maturity_years"), s = inp("sigma_volatility");
    expect(Math.abs(blackScholesCall(S, K, r, T, s).call - out("black_scholes_call"))).toBeLessThan(0.05);
    expect(Math.abs(binomialCall(S, K, r, T, s, 2000) - Number(D.options.convergence.find((c) => c.n_steps === 2000)!.binomial_european))).toBeLessThan(0.05);
  });
});

describe("Browser Monte Carlo matches Stage 5B statistically", () => {
  it("P(value created > 0) and median vs the $38 offer", () => {
    const M = D.montecarlo, row = M.summary.find((x) => x.metric === "value_created_vs_amended_38")!;
    const v = simulate(B.model as ModelB, M.synergy_base, B.tax, B.g, M.paid["amended_38"],
      { n: 20000, seed: 7, real: [0.5, 1.0, 1.25], delayP: [0.6, 0.3, 0.1], ic: [0.75, 1.0, 2.0], growthSd: 0.01, marginSd: 0.01, clip: 0.03 });
    const sorted = Float64Array.from(v).sort();
    const pos = v.filter((x) => x > 0).length / v.length;
    expect(Math.abs(pos - Number(row.prob_positive))).toBeLessThan(0.02);
    expect(Math.abs(percentile(sorted, 0.5) - Number(row.p50))).toBeLessThan(400);
  });
});
