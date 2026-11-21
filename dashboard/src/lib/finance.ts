// Browser-side valuation engine. Each function mirrors a Python module in src/valuation/ and is tested
// (finance.test.ts) against the values the Python pipeline exported to public/data/dashboard.json.

// ---------------------------------------------------------------- statistics
export function normCdf(x: number): number {
  // Abramowitz-Stegun 7.1.26 via erf; |error| < 1.5e-7
  const t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-(x * x) / 2);
  return x >= 0 ? 0.5 * (1 + y) : 0.5 * (1 - y);
}

// ---------------------------------------------------------------- options (src/valuation/options.py)
export function blackScholesCall(S: number, K: number, r: number, T: number, sigma: number, q = 0) {
  const d1 = (Math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));
  const d2 = d1 - sigma * Math.sqrt(T);
  return { call: S * Math.exp(-q * T) * normCdf(d1) - K * Math.exp(-r * T) * normCdf(d2), d1, d2 };
}

export function binomialCall(S: number, K: number, r: number, T: number, sigma: number, n = 200, american = false, q = 0): number {
  const dt = T / n, u = Math.exp(sigma * Math.sqrt(dt)), d = 1 / u;
  const p = (Math.exp((r - q) * dt) - d) / (u - d), disc = Math.exp(-r * dt);
  if (!(p > 0 && p < 1)) return NaN;
  const v = new Float64Array(n + 1);
  for (let j = 0; j <= n; j++) v[j] = Math.max(S * Math.pow(u, j) * Math.pow(d, n - j) - K, 0);
  for (let step = n - 1; step >= 0; step--) {
    for (let j = 0; j <= step; j++) {
      let cont = disc * (p * v[j + 1] + (1 - p) * v[j]);
      if (american) cont = Math.max(cont, S * Math.pow(u, j) * Math.pow(d, step - j) - K);
      v[j] = cont;
    }
  }
  return v[0];
}

/** Full CRR lattice for small n (used to draw the tree). Root value equals binomialCall with the same inputs. */
export function binomialLattice(S: number, K: number, r: number, T: number, sigma: number, n = 4, american = false, q = 0) {
  const dt = T / n, u = Math.exp(sigma * Math.sqrt(dt)), d = 1 / u;
  const p = (Math.exp((r - q) * dt) - d) / (u - d), disc = Math.exp(-r * dt);
  const nodes = Array.from({ length: n + 1 }, (_, i) => Array.from({ length: i + 1 }, (_, j) => ({ s: S * Math.pow(u, j) * Math.pow(d, i - j), v: 0, early: false })));
  nodes[n].forEach((x) => { x.v = Math.max(x.s - K, 0); });
  for (let i = n - 1; i >= 0; i--) {
    for (let j = 0; j <= i; j++) {
      const cont = disc * (p * nodes[i + 1][j + 1].v + (1 - p) * nodes[i + 1][j].v), ex = nodes[i][j].s - K;
      nodes[i][j].v = american && ex > cont ? ex : cont;
      nodes[i][j].early = american && ex > cont;
    }
  }
  return { nodes, u, d, p, dt };
}

// ---------------------------------------------------------------- DCF (src/valuation/dcf.py, build_valuation.py)
export interface ModelA { base_revenue: number; growth: number; margin: number; da_pct: number; capex_pct: number; nwc_pct: number; frac: number[]; t: number[]; t_n: number; wacc: number }
export interface ModelB { fy: string[]; revenue: number[]; margin: number[]; resid_pct: number[]; da_pct: number; capex_pct: number; conv: number; frac: number[]; t: number[]; t_n: number; k_exp: number[]; wacc: number; bridge_total: number }
export interface DcfResult { ev: number; pvExplicit: number; pvTv: number; rows: { fy: string; revenue: number; ebitda: number; fcff: number; pv: number }[] }

export function dcfA(m: ModelA, o: { wacc?: number; g: number; tax: number; growth?: number; margin?: number; capex?: number; nwc?: number }): DcfResult {
  const w = o.wacc ?? m.wacc, gr = o.growth ?? m.growth, mg = o.margin ?? m.margin, cap = o.capex ?? m.capex_pct, nwc = o.nwc ?? m.nwc_pct;
  const rows: DcfResult["rows"] = [];
  let pv = 0, last = 0;
  for (let i = 1; i <= 5; i++) {
    const R = m.base_revenue * Math.pow(1 + gr, i), E = mg * R, da = m.da_pct * R;
    const fcff = (E - da) * (1 - o.tax) + da - cap * R - nwc * R;
    const p = fcff * m.frac[i - 1] * Math.pow(1 + w, -m.t[i - 1]);
    pv += p; last = fcff;
    rows.push({ fy: `FY${2017 + i}`, revenue: R, ebitda: E, fcff, pv: p });
  }
  const tv = (last * (1 + o.g)) / (w - o.g) * Math.pow(1 + w, -m.t_n);
  return { ev: pv + tv, pvExplicit: pv, pvTv: tv, rows };
}

export function dcfB(m: ModelB, o: { wacc?: number; g: number; tax: number; growthShift?: number; marginShift?: number; capexShift?: number; residShift?: number }): DcfResult {
  const w = o.wacc ?? m.wacc, gs = o.growthShift ?? 0, ms = o.marginShift ?? 0, cs = o.capexShift ?? 0, rs = o.residShift ?? 0;
  const rows: DcfResult["rows"] = [];
  let pv = 0, lastE = 0, lastR = 0;
  m.revenue.forEach((R0, i) => {
    const R = R0 * Math.pow(1 + gs, m.k_exp[i]), E = (m.margin[i] + ms) * R, da = m.da_pct * R;
    const fcff = (E - da) * (1 - o.tax) + da - (m.capex_pct + cs) * R - (m.resid_pct[i] + rs) * R;
    const p = fcff * m.frac[i] * Math.pow(1 + w, -m.t[i]);
    pv += p; lastE = E; lastR = R;
    rows.push({ fy: m.fy[i], revenue: R, ebitda: E, fcff, pv: p });
  });
  const term = lastE * m.conv - (cs + rs) * lastR;
  const tv = (term * (1 + o.g)) / (w - o.g) * Math.pow(1 + w, -m.t_n);
  return { ev: pv + tv, pvExplicit: pv, pvTv: tv, rows };
}

// ---------------------------------------------------------------- synergies (src/valuation/synergy.py)
export interface SynTiming { t: number[]; t_n: number }
export function synergyValue(o: { runRate: number; phase: number[]; icPhase: number[]; icMult: number; g: number; rate: number; tax: number; realization?: number; delay?: number; timing: SynTiming }) {
  const real = o.realization ?? 1, delay = Math.round(o.delay ?? 0);
  let pvS = 0, pvI = 0, lastAt = 0;
  const flows = o.phase.map((_, i) => {
    const ph = i - delay >= 0 ? o.phase[i - delay] : 0;
    const syn = o.runRate * ph * real, ic = o.runRate * o.icMult * o.icPhase[i];
    const df = Math.pow(1 + o.rate, -o.timing.t[i]);
    pvS += syn * (1 - o.tax) * df; pvI += ic * (1 - o.tax) * df; lastAt = syn * (1 - o.tax);
    return { syn, ic, fcff: (syn - ic) * (1 - o.tax) };
  });
  const tv = (lastAt * (1 + o.g)) / (o.rate - o.g) * Math.pow(1 + o.rate, -o.timing.t_n);
  return { gross: pvS + tv, pvIntegration: pvI, net: pvS + tv - pvI, pvTv: tv, flows };
}

// ---------------------------------------------------------------- accretion / dilution (src/valuation/accretion.py)
export interface AdParams {
  tax: number; rate: number; ppa: number; dis_int: number; dis_nci: number; dis_sh: number; rc_int: number; rc_intinc: number; rc_eq: number; rc_nci: number;
  rsn_share: number; rsn_proceeds: number; cash: number; stock_val: number; shares_new: number; vwap: number; repaid: number; orig_shares: number;
  years: Record<string, { seg: number; corp: number; rc_ebit_full: number; syn: number; ic: number }>;
}
export interface AdOptions { realization?: number; icFactor?: number; cashShare?: number | null; rate?: number; price?: number | null; ppaFactor?: number; includeRsn?: boolean; original?: boolean; buybacks?: number }
export function accretion(P: AdParams, o: AdOptions = {}) {
  const t = P.tax, rate = o.rate ?? P.rate, total = P.cash + P.stock_val;
  let newShares: number, newDebt: number;
  if (o.original) { newShares = P.orig_shares; newDebt = 0; }
  else {
    const custom = o.cashShare != null || o.price != null;
    const cs = o.cashShare ?? P.cash / total, px = o.price ?? P.vwap;
    const cash = total * cs;
    newShares = custom ? (total - cash) / px : P.shares_new;
    newDebt = Math.max(0, cash - P.repaid);
  }
  if (!o.includeRsn) newDebt = Math.max(0, newDebt - P.rsn_proceeds);
  const bb = o.buybacks ?? 0;
  if (bb) newDebt += bb;
  const out: Record<string, { standalone: number; adjusted: number; gaap: number; accAdj: number; accGaap: number; interest: number; synergies: number; ppa: number }> = {};
  for (const [fy, y] of Object.entries(P.years)) {
    const dNi = (y.seg - y.corp + P.dis_int) * (1 - t) + P.dis_nci;
    const rcEbit = o.includeRsn ? y.rc_ebit_full : y.rc_ebit_full * (1 - P.rsn_share);
    const rcNi = (rcEbit + P.rc_int + P.rc_intinc + P.rc_eq) * (1 - t) + P.rc_nci;
    const interest = newDebt * rate, ppa = P.ppa * (o.ppaFactor ?? 1), syn = y.syn * (o.realization ?? 1), ic = y.ic * (o.icFactor ?? 1);
    const sh = P.dis_sh - (bb ? bb / P.vwap : 0) + newShares;
    const epsSa = dNi / P.dis_sh;
    const niAdj = dNi + rcNi - interest * (1 - t) + syn * (1 - t);
    const niGaap = niAdj - ppa * (1 - t) - ic * (1 - t);
    out[fy] = { standalone: epsSa, adjusted: niAdj / sh, gaap: niGaap / sh, accAdj: niAdj / sh / epsSa - 1, accGaap: niGaap / sh / epsSa - 1, interest, synergies: syn, ppa };
  }
  return out;
}

// ---------------------------------------------------------------- Monte Carlo (src/valuation/monte_carlo.py)
export function rng(seed: number) {
  // mulberry32 + Box-Muller. Not numpy's generator: browser draws differ from the Python draws but follow the same distributions.
  let a = seed >>> 0;
  const u = () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  let spare: number | null = null;
  const normal = () => {
    if (spare !== null) { const s = spare; spare = null; return s; }
    let x = 0, y = 0, s = 0;
    do { x = 2 * u() - 1; y = 2 * u() - 1; s = x * x + y * y; } while (s === 0 || s >= 1);
    const f = Math.sqrt((-2 * Math.log(s)) / s); spare = y * f; return x * f;
  };
  const triangular = (lo: number, mode: number, hi: number) => {
    const p = u(), c = (mode - lo) / (hi - lo);
    return p < c ? lo + Math.sqrt(p * (hi - lo) * (mode - lo)) : hi - Math.sqrt((1 - p) * (hi - lo) * (hi - mode));
  };
  return { u, normal, triangular };
}

export interface McSettings { n: number; seed: number; real: [number, number, number]; delayP: [number, number, number]; ic: [number, number, number]; growthSd: number; marginSd: number; clip: number }
export function simulate(B: ModelB, syn: { run_rate: number; g: number; phase: number[]; ic_phase: number[]; t: number[]; t_n: number }, tax: number, g: number, paid: number, s: McSettings) {
  const r = rng(s.seed), out = new Float64Array(s.n);
  const clip = (x: number) => Math.max(-s.clip, Math.min(s.clip, x));
  for (let k = 0; k < s.n; k++) {
    const real = r.triangular(...s.real);
    const p = r.u(), delay = p < s.delayP[0] ? 0 : p < s.delayP[0] + s.delayP[1] ? 1 : 2;
    const ic = r.triangular(...s.ic);
    const gs = clip(r.normal() * s.growthSd), ms = clip(r.normal() * s.marginSd);
    const eq = dcfB(B, { g, tax, growthShift: gs, marginShift: ms }).ev + B.bridge_total;
    const ns = synergyValue({ runRate: syn.run_rate, phase: syn.phase, icPhase: syn.ic_phase, icMult: ic, g: syn.g, rate: B.wacc, tax, realization: real, delay, timing: { t: syn.t, t_n: syn.t_n } }).net;
    out[k] = eq + ns - paid;
  }
  return out;
}

export function percentile(sorted: Float64Array | number[], p: number) {
  const i = (sorted.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
}
