import { useMemo, useState } from "react";
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard, Perspective, PerspectiveKey } from "../lib/data";
import { dcfA, dcfB, type ModelA, type ModelB } from "../lib/finance";
import { PALETTE, bn, mult, musd, pct, usd } from "../lib/format";
import { Badge, Legend, Panel, Section, Segmented, Slider, Source, Stat, Table, axisProps, gridProps, tooltipStyle } from "../components/ui";

const bridgeSum = (p: Perspective) => p.bridge.plus_sky_39pct_stake + p.bridge.plus_other_investments_book - p.bridge.less_debt + p.bridge.plus_cash - p.bridge.less_noncontrolling_interests;

function heat(v: number, lo: number, hi: number) {
  const t = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  // sequential single-hue ramp (navy), light -> dark
  const a = 0.08 + t * 0.72;
  return { background: `rgba(31,58,95,${a.toFixed(3)})`, color: t > 0.55 ? "#FCFAF6" : "#14202E" };
}

export default function Valuation({ d }: { d: Dashboard }) {
  const [pk, setPk] = useState<PerspectiveKey>("B_proxy_2018-05");
  const P = d.valuation[pk];
  const isA = P.model.kind === "estimate";
  const mA = P.model as ModelA & { kind: "estimate" }, mB = P.model as ModelB & { kind: "management" };
  const [wacc, setWacc] = useState<number | null>(null);
  const [g, setG] = useState<number | null>(null);
  const [x1, setX1] = useState(0); // growth (A: absolute; B: shift)
  const [x2, setX2] = useState(0); // margin
  const reset = (k: PerspectiveKey) => { setPk(k); setWacc(null); setG(null); setX1(0); setX2(0); };
  const w = wacc ?? P.model.wacc, gg = g ?? P.g;
  const res = useMemo(() => isA
    ? dcfA(mA, { wacc: w, g: gg, tax: P.tax, growth: mA.growth + x1, margin: mA.margin + x2 })
    : dcfB(mB, { wacc: w, g: gg, tax: P.tax, growthShift: x1, marginShift: x2 }), [isA, mA, mB, w, gg, P.tax, x1, x2]);
  const eq = res.ev + bridgeSum(P), ps = eq / P.shares;
  const changed = wacc !== null || g !== null || x1 !== 0 || x2 !== 0;
  const grid = P.grid;
  const ws = Array.from(new Set(grid.map((x) => x.row_value))).sort((a, b) => a - b);
  const gs = Array.from(new Set(grid.map((x) => x.col_value))).sort((a, b) => a - b);
  const lo = Math.min(...grid.map((x) => x.equity_per_share)), hi = Math.max(...grid.map((x) => x.equity_per_share));
  const comps = d.comps.filter((c) => c.perspective === pk);
  const compsRange = (m: string) => { const xs = P.comps.filter((c) => c.case.startsWith(m)).map((c) => c.v); return xs.length ? `${usd(Math.min(...xs))} – ${usd(Math.max(...xs))}` : "–"; };
  return (
    <Section id="valuation" kicker="02 · Standalone valuation" title="What the acquired business was worth on its own"
      lede={<>Two perspectives with separate information sets. <b>A</b> uses only what was public on 14 Dec 2017, so its cash flows are estimates.
        <b> B</b> uses the management forecasts disclosed in the May 2018 joint proxy. Move the assumptions: the DCF reruns in your browser with the same formulas as the Python engine.</>}>
      <div className="flex flex-wrap items-center gap-4">
        <Segmented label="Perspective" value={pk} onChange={reset} options={[{ value: "A_announcement_2017-12", label: d.valuation["A_announcement_2017-12"].label }, { value: "B_proxy_2018-05", label: d.valuation["B_proxy_2018-05"].label }]} />
        <span className="text-xs text-muted">{P.basis}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Panel title="Assumptions" right={changed ? <button onClick={() => reset(pk)} className="text-xs font-medium text-navy underline-offset-4 hover:underline">Reset</button> : <Badge kind="derived" />}>
          <div className="space-y-5">
            <Slider label="WACC" value={w} min={0.045} max={0.095} step={0.0005} onChange={setWacc} fmt={(v) => pct(v, 2)} hint={`Base ${pct(P.model.wacc, 2)} (CAPM, peer betas, dated FRED / Damodaran inputs)`} />
            <Slider label="Terminal growth" value={gg} min={0} max={0.035} step={0.0025} onChange={setG} fmt={(v) => pct(v, 2)} hint="Base 2.0%" />
            <Slider label={isA ? "Revenue growth (a year)" : "Revenue growth shift"} value={isA ? mA.growth + x1 : x1} min={isA ? -0.01 : -0.03} max={isA ? 0.07 : 0.03} step={0.0025}
              onChange={(v) => setX1(isA ? v - mA.growth : v)} fmt={(v) => pct(v, 2, !isA)} hint={isA ? `Base ${pct(mA.growth, 1)} (21CF ex-DBS history)` : "Applied to the Disney forecasts"} />
            <Slider label={isA ? "EBITDA margin" : "EBITDA margin shift"} value={isA ? mA.margin + x2 : x2} min={isA ? 0.18 : -0.03} max={isA ? 0.3 : 0.03} step={0.0025}
              onChange={(v) => setX2(isA ? v - mA.margin : v)} fmt={(v) => pct(v, 2, !isA)} hint={isA ? `Base ${pct(mA.margin, 1)}` : "Percentage points on every forecast year"} />
          </div>
        </Panel>
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-x-6 gap-y-6 md:grid-cols-4">
            <Stat label="Enterprise value" value={bn(res.ev)} sub={changed ? `base ${bn(P.outputs.enterprise_value_ops)}` : "operations incl. RSNs"} />
            <Stat label="Equity value" value={bn(eq)} sub="after Sky stake, debt, cash, NCI" />
            <Stat label="Per 21CF share" value={usd(ps)} sub={changed ? `base ${usd(P.outputs.equity_value_per_21cf_share)}` : `${P.shares.toLocaleString("en-US", { maximumFractionDigits: 1 })}m shares`} />
            <Stat label="Terminal value share" value={pct(res.pvTv / res.ev, 0)} sub="of enterprise value" />
          </div>
          <Panel title="Free cash flow to the firm by fiscal year (June FY)">
            <Legend items={[{ label: "FCFF", color: PALETTE.s1 }, { label: "Present value", color: PALETTE.s4 }]} />
            <div className="mt-2 h-60">
              <ResponsiveContainer>
                <ComposedChart data={res.rows} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="fy" {...axisProps} />
                  <YAxis {...axisProps} width={56} tickFormatter={(v) => `${(v / 1000).toFixed(1)}bn`} />
                  <Tooltip {...tooltipStyle} formatter={(v: number, k: string) => [musd(v), k === "fcff" ? "FCFF" : k === "pv" ? "Present value" : k]} />
                  <Bar dataKey="fcff" fill={PALETTE.s1} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                  <Line dataKey="pv" stroke={PALETTE.s4} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-muted">{isA ? "A: estimate-based projection (growth, margin, D&A, capex and content investment from 21CF's history)." : "B: FCFF equals Disney management's unlevered free cash flow exactly at base; the first year counts only the month after 30 May 2018."}</p>
          </Panel>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Equity value per share: WACC × terminal growth" note="Stage 3 sensitivity grid (Python). Darker = higher value.">
          <div className="overflow-x-auto">
            <table className="num w-full border-collapse text-[12px]">
              <thead><tr><th className="p-1.5 text-left text-[11px] font-semibold text-muted">WACC \ g</th>{gs.map((x) => <th key={x} className="p-1.5 text-right text-[11px] font-semibold text-muted">{pct(x, 1)}</th>)}</tr></thead>
              <tbody>{ws.map((wv) => (
                <tr key={wv}><td className="p-1.5 text-[11px] font-semibold text-muted">{pct(wv, 2)}</td>
                  {gs.map((gv) => { const c = grid.find((x) => x.row_value === wv && x.col_value === gv)!; return <td key={gv} className="p-1.5 text-right" style={heat(c.equity_per_share, lo, hi)}>{usd(c.equity_per_share)}</td>; })}</tr>))}
              </tbody>
            </table>
          </div>
        </Panel>
        <Panel title="WACC build-up" note="Beta: median of Comcast, AMC Networks and Netflix 2-year weekly betas (Blume-adjusted, unlevered, relevered at median peer leverage). Cost of debt: Moody's Baa yield (21CF was Baa1).">
          <Table head={["Component", "Value", "Type"]} align={["l", "r", "r"]} rows={[
            ["Risk-free rate (10y Treasury)", pct(P.wacc.rf, 2), <Badge kind="market" />],
            ["Equity risk premium (Damodaran)", pct(P.wacc.erp, 2), <Badge kind="market" />],
            ["Relevered beta", P.wacc.relevered_beta.toFixed(2), <Badge kind="derived" />],
            ["Cost of equity", pct(P.wacc.cost_of_equity, 2), <Badge kind="derived" />],
            ["Cost of debt, after tax", pct(P.wacc.kd_aftertax, 2), <Badge kind="derived" />],
            ["Debt weight", pct(P.wacc.weight_debt, 1), <Badge kind="derived" />],
            [<b>WACC</b>, <b>{pct(P.wacc.wacc, 2)}</b>, ""],
          ]} />
        </Panel>
      </div>

      <Panel title="Comparable companies (LTM, as of the perspective date)" note="Share counts are diluted weighted-average shares (a labelled proxy). Netflix is excluded from the ranges (content amortization is outside D&A; priced on growth); Disney is the acquirer and shown for reference only. Time Warner, Viacom, CBS and Discovery lack accessible historical prices.">
        <Table head={["Company", "EV", "EV / Revenue", "EV / EBITDA", "EV / EBIT", "P / E", ""]} align={["l", "r", "r", "r", "r", "r", "l"]}
          rows={comps.map((c) => [String(c.company), bn(Number(c.enterprise_value)), mult(Number(c.ev_revenue)), mult(Number(c.ev_ebitda)), mult(Number(c.ev_ebit)),
            c.pe_flag === "ok" ? mult(Number(c.pe)) : "n.m.", <span className="text-[11px] text-muted">{c.ev_ebitda_flag === "ok" ? "in range" : String(c.ev_ebitda_flag).split(":")[0]}</span>])} />
        <div className="mt-4 grid gap-4 text-sm md:grid-cols-3">
          <p><span className="text-muted">EV/EBITDA →</span> <span className="num font-medium">{compsRange("ev_ebitda")}</span></p>
          <p><span className="text-muted">EV/EBIT →</span> <span className="num font-medium">{compsRange("ev_ebit")}</span></p>
          <p><span className="text-muted">EV/Revenue →</span> <span className="num font-medium">{compsRange("ev_revenue")}</span></p>
        </div>
        <p className="mt-2 text-xs text-muted">Per 21CF share after the same bridge as the DCF. The DCF scenarios span {usd(P.scenarios.bear)} (bear) to {usd(P.scenarios.bull)} (bull).</p>
      </Panel>
      <Source>valuation_outputs.csv, valuation_sensitivity.csv, dcf_assumptions.csv, comparable_companies.csv (Stage 3); market data from FRED, Damodaran and Yahoo Finance, read as of each date.</Source>
    </Section>
  );
}
