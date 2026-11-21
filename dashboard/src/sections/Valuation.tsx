import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard, Perspective, PerspectiveKey } from "../lib/data";
import { dcfA, dcfB, type ModelA, type ModelB } from "../lib/finance";
import { PALETTE, bn, mult, musd, pct, usd } from "../lib/format";
import { Badge, Details, Finding, Legend, Num, Panel, Reveal, ResetButton, Section, Segmented, Slider, Source, Stat, Table, Term, anim, axisProps, gridProps, tooltipStyle } from "../components/ui";

const bridgeSum = (p: Perspective) => p.bridge.plus_sky_39pct_stake + p.bridge.plus_other_investments_book - p.bridge.less_debt + p.bridge.plus_cash - p.bridge.less_noncontrolling_interests;

function heat(v: number, lo: number, hi: number) {
  const t = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  const a = 0.08 + t * 0.72; // sequential single-hue ramp (navy), light -> dark
  return { background: `rgba(31,58,95,${a.toFixed(3)})`, color: t > 0.55 ? "#FCFAF6" : "#14202E" };
}

const PERSPECTIVE_NOTE: Record<PerspectiveKey, string> = {
  "A_announcement_2017-12": "Only what was public on 14 Dec 2017. Cash flows are estimated from 21CF's own history.",
  "B_proxy_2018-05": "Uses Disney management's forecasts for the acquired business, disclosed in the May 2018 proxy.",
};

export default function Valuation({ d }: { d: Dashboard }) {
  const [pk, setPk] = useState<PerspectiveKey>("B_proxy_2018-05");
  const P = d.valuation[pk];
  const isA = P.model.kind === "estimate";
  const mA = P.model as ModelA & { kind: "estimate" }, mB = P.model as ModelB & { kind: "management" };
  const [wacc, setWacc] = useState<number | null>(null);
  const [g, setG] = useState<number | null>(null);
  const [x1, setX1] = useState(0); // growth (A: absolute offset; B: shift)
  const [x2, setX2] = useState(0); // margin
  const reset = (k: PerspectiveKey) => { setPk(k); setWacc(null); setG(null); setX1(0); setX2(0); };
  const w = wacc ?? P.model.wacc, gg = g ?? P.g;
  const res = useMemo(() => isA
    ? dcfA(mA, { wacc: w, g: gg, tax: P.tax, growth: mA.growth + x1, margin: mA.margin + x2 })
    : dcfB(mB, { wacc: w, g: gg, tax: P.tax, growthShift: x1, marginShift: x2 }), [isA, mA, mB, w, gg, P.tax, x1, x2]);
  const eq = res.ev + bridgeSum(P), ps = eq / P.shares;
  const changed = wacc !== null || g !== null || x1 !== 0 || x2 !== 0;

  // prices to compare against
  const offerAtDate = d.synergy.justification.find((j) => j.perspective === pk && j.metric === "consideration_per_share")!.v!;
  const amended = d.deal.stages[1].per_share;
  const ref = isA ? offerAtDate : amended;
  const gap = ref - ps;

  // sensitivity grid (Stage 3, Python) — clicking a cell sets WACC and g
  const grid = P.grid;
  const ws = Array.from(new Set(grid.map((x) => x.row_value))).sort((a, b) => a - b);
  const gs = Array.from(new Set(grid.map((x) => x.col_value))).sort((a, b) => a - b);
  const lo = Math.min(...grid.map((x) => x.equity_per_share)), hi = Math.max(...grid.map((x) => x.equity_per_share));
  // grid WACCs are rounded to 4 dp by the pipeline (build_valuation.py), so a cell's WACC is its row value
  const rowToWacc = (rv: number) => rv;
  const activeCell = (rv: number, cv: number) => Math.abs(w - rowToWacc(rv)) < 0.00026 && Math.abs(gg - cv) < 0.0013 && x1 === 0 && x2 === 0;

  return (
    <Section id="valuation" index="02" kicker="Valuation" title="What was the business worth on its own?"
      lede={<>Before asking whether Disney overpaid, we need the <Term k="standalone">standalone value</Term>: what the acquired business was worth with no help from Disney.
        Two methods: a <Term k="dcf">DCF</Term> of future cash flows, and <Term k="comps">comparable companies</Term>.</>}
      takeaway={<>On Disney's own forecasts the business was worth about {usd(d.valuation["B_proxy_2018-05"].outputs.equity_value_per_21cf_share)} a share, far below the {usd(amended)} paid. The gap has to come from synergies.</>}>

      <Reveal>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-5">
          <Segmented size="md" label="Perspective" value={pk} onChange={reset}
            options={[{ value: "A_announcement_2017-12", label: "Dec 2017 · public info" }, { value: "B_proxy_2018-05", label: "May 2018 · Disney forecasts" }]} />
          <p className="text-sm text-muted">{PERSPECTIVE_NOTE[pk]}</p>
        </div>
      </Reveal>

      <Reveal>
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <Panel title="Your assumptions" right={<ResetButton show={changed} onClick={() => reset(pk)} />}>
            <div className="space-y-6">
              <Slider label={<Term k="wacc">WACC</Term>} value={w} min={0.045} max={0.095} step={0.0005} onChange={setWacc} fmt={(v) => pct(v, 2)} base={P.model.wacc}
                explain="The return investors demand. Higher means future cash is worth less today."
                hint={`Base ${pct(P.model.wacc, 2)}: CAPM with peer betas and dated market inputs`} />
              <Slider label={<Term k="tg">Terminal growth</Term>} value={gg} min={0} max={0.035} step={0.0025} onChange={setG} fmt={(v) => pct(v, 2)} base={P.g}
                explain="How fast cash flows grow forever after the forecast years."
                hint={`Base ${pct(P.g, 1)}`} />
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink">
                  More assumptions <span className="transition-transform group-open:rotate-45">+</span>
                </summary>
                <div className="mt-5 space-y-6">
                  <Slider label={isA ? "Revenue growth (a year)" : "Revenue growth shift"} value={isA ? mA.growth + x1 : x1} min={isA ? -0.01 : -0.03} max={isA ? 0.07 : 0.03} step={0.0025}
                    onChange={(v) => setX1(isA ? v - mA.growth : v)} fmt={(v) => pct(v, 2, !isA)} base={isA ? mA.growth : 0}
                    explain={isA ? "Annual sales growth over the forecast." : "Raise or cut Disney's sales forecast every year."} hint={isA ? `Base ${pct(mA.growth, 1)} (21CF ex-DBS history)` : undefined} />
                  <Slider label={isA ? "EBITDA margin" : "EBITDA margin shift"} value={isA ? mA.margin + x2 : x2} min={isA ? 0.18 : -0.03} max={isA ? 0.3 : 0.03} step={0.0025}
                    onChange={(v) => setX2(isA ? v - mA.margin : v)} fmt={(v) => pct(v, 2, !isA)} base={isA ? mA.margin : 0}
                    explain="Operating profit as a share of sales." hint={isA ? `Base ${pct(mA.margin, 1)}` : "Percentage points on every forecast year"} />
                </div>
              </details>
            </div>
          </Panel>

          <div className="space-y-6">
            <Panel>
              <div className="grid gap-6 sm:grid-cols-[1.2fr_1fr]">
                <Stat big label="Standalone value per share" value={<Num v={ps} fmt={usd} />}
                  sub={changed ? <>Pipeline base {usd(P.outputs.equity_value_per_21cf_share)}</> : <>{P.shares.toLocaleString("en-US", { maximumFractionDigits: 1 })}m 21CF shares</>} />
                <Stat big label={isA ? "Original offer minus value" : "Price paid minus value"} tone={gap > 0 ? "neg" : "pos"}
                  value={<Num v={gap} fmt={(x) => (x > 0 ? "+" : "") + usd(x)} />} sub={<>{isA ? "Dec 2017 offer" : "Amended offer"} {usd(ref)}: the <Term k="premium">premium</Term> over standalone value</>} />
              </div>
              <div className="mt-6 grid grid-cols-2 gap-4 border-t border-rule pt-5 sm:grid-cols-3">
                <Stat label={<Term k="ev">Enterprise value</Term>} value={<Num v={res.ev} fmt={(x) => bn(x)} />} />
                <Stat label={<Term k="equity">Equity value</Term>} value={<Num v={eq} fmt={(x) => bn(x)} />} />
                <Stat label={<Term k="tv">Terminal value</Term>} value={<Num v={res.pvTv / res.ev} fmt={(x) => pct(x, 0)} />} sub="share of EV" />
              </div>
            </Panel>
            <FootballField d={d} pk={pk} live={ps} offerAtDate={offerAtDate} amended={amended} />
          </div>
        </div>
      </Reveal>

      <Reveal>
        <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          <Panel title="Sensitivity: value per share by WACC and terminal growth" right={<span className="text-[11px] text-muted">Click a cell to load it</span>}
            note="Stage 3 sensitivity grid from the Python pipeline. Darker = higher value. The outlined cell matches your current WACC and growth.">
            <div className="overflow-x-auto">
              <table className="num w-full border-separate border-spacing-[3px] text-[12px]">
                <thead><tr><th className="p-1.5 text-left text-[11px] font-semibold text-muted">WACC ↓ · g →</th>{gs.map((x) => <th key={x} className="p-1.5 text-right text-[11px] font-semibold text-muted">{pct(x, 1)}</th>)}</tr></thead>
                <tbody>{ws.map((wv) => (
                  <tr key={wv}><td className="p-1.5 text-[11px] font-semibold text-muted">{pct(wv, 2)}</td>
                    {gs.map((gv) => {
                      const c = grid.find((x) => x.row_value === wv && x.col_value === gv)!, on = activeCell(wv, gv);
                      return (
                        <td key={gv} className="p-0">
                          <button onClick={() => { setWacc(rowToWacc(wv)); setG(gv); setX1(0); setX2(0); }} title={`WACC ${pct(wv, 2)}, g ${pct(gv, 1)}`}
                            className={`w-full rounded-[2px] p-1.5 text-right transition-all duration-200 hover:scale-[1.06] hover:shadow-md ${on ? "ring-2 ring-brass ring-offset-1 ring-offset-card" : ""}`} style={heat(c.equity_per_share, lo, hi)}>
                            {usd(c.equity_per_share)}
                          </button>
                        </td>);
                    })}</tr>))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 space-y-2">
              {(() => {
                const at = (rv: number) => grid.find((c) => c.row_value === rv && Math.abs(c.col_value - P.g) < 1e-9)?.equity_per_share;
                const a = at(ws[0]), z = at(ws[ws.length - 1]);
                return a != null && z != null ? <Finding>At {pct(P.g, 1)} growth, moving WACC from {pct(ws[0], 2)} to {pct(ws[ws.length - 1], 2)} takes the value from {usd(a)} to {usd(z)} a share.</Finding> : null;
              })()}
              <Finding>{pct(P.outputs.terminal_value_share_of_ev, 0)} of the base enterprise value sits in the <Term k="tv">terminal value</Term>, so long-run assumptions dominate.</Finding>
            </div>
          </Panel>
          <Panel title={<><Term k="fcff">Free cash flow</Term> by year (June FY)</>}>
            <Legend items={[{ label: "FCFF", color: PALETTE.s1 }, { label: "Present value", color: PALETTE.s4 }]} />
            <div className="mt-2 h-64">
              <ResponsiveContainer>
                <ComposedChart data={res.rows} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="fy" {...axisProps} />
                  <YAxis {...axisProps} width={56} tickFormatter={(v) => `${(v / 1000).toFixed(1)}bn`} />
                  <Tooltip {...tooltipStyle} formatter={(v: number, k: string) => [musd(v), k === "fcff" ? "FCFF" : k === "pv" ? "Present value" : k]} />
                  <Bar dataKey="fcff" fill={PALETTE.s1} radius={[2, 2, 0, 0]} {...anim} />
                  <Line dataKey="pv" stroke={PALETTE.s4} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-muted">{isA ? "Estimate-based projection (growth, margin, D&A, capex and content investment from 21CF's history)." : "FCFF equals Disney management's unlevered free cash flow exactly at base; the first year counts only the month after 30 May 2018."}</p>
          </Panel>
        </div>
      </Reveal>

      <Details summary="How the discount rate (WACC) is built">
        <Panel note="Beta: median of Comcast, AMC Networks and Netflix 2-year weekly betas (Blume-adjusted, unlevered, relevered at median peer leverage). Cost of debt: Moody's Baa yield (21CF was Baa1).">
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
      </Details>
      <Details summary="From enterprise value to equity value (the bridge)">
        <Bridge P={P} />
      </Details>
      <Details summary="Comparable companies table">
        <Comps d={d} pk={pk} P={P} />
      </Details>
      <Source>valuation_outputs.csv, valuation_sensitivity.csv, dcf_assumptions.csv, comparable_companies.csv (Stage 3); market data from FRED, Damodaran and Yahoo Finance, read as of each date.</Source>
    </Section>
  );
}

function FootballField({ d, pk, live, offerAtDate, amended }: { d: Dashboard; pk: PerspectiveKey; live: number; offerAtDate: number; amended: number }) {
  const P = d.valuation[pk];
  const range = (m: string) => { const xs = P.comps.filter((c) => c.case.startsWith(m)).map((c) => c.v); return xs.length ? [Math.min(...xs), Math.max(...xs)] as const : null; };
  const rows: { label: string; lo: number; hi: number; mark?: number; color: string; note: string }[] = [
    { label: "DCF (bear – bull)", lo: P.scenarios.bear, hi: P.scenarios.bull, mark: P.scenarios.base, color: PALETTE.navy, note: "Stage 3 scenarios; dot = base" },
  ];
  for (const [m, l] of [["ev_ebitda", "Comps · EV/EBITDA"], ["ev_ebit", "Comps · EV/EBIT"], ["ev_revenue", "Comps · EV/Revenue"]] as const) {
    const r = range(m); if (r) rows.push({ label: l, lo: r[0], hi: r[1], color: PALETTE.s1, note: "peer multiple range" });
  }
  if (pk === "B_proxy_2018-05") {
    const s = d.montecarlo.summary.find((x) => x.metric === "standalone_equity_per_share")!;
    rows.push({ label: "Monte Carlo (5th – 95th)", lo: Number(s.p05), hi: Number(s.p95), mark: Number(s.p50), color: PALETTE.s3, note: "20,000 simulations; dot = median" });
  }
  const lines = [
    { v: offerAtDate, label: pk === "A_announcement_2017-12" ? "Original offer" : "Original offer (May 2018)", color: PALETTE.muted },
    { v: amended, label: "Amended offer", color: PALETTE.s2 },
  ];
  const all = [...rows.flatMap((r) => [r.lo, r.hi]), ...lines.map((l) => l.v), live];
  const dLo = Math.floor(Math.min(...all) / 5) * 5, dHi = Math.ceil(Math.max(...all) / 5) * 5;
  const x = (v: number) => `${((v - dLo) / (dHi - dLo)) * 100}%`;
  const ticks = Array.from({ length: (dHi - dLo) / 5 + 1 }, (_, i) => dLo + i * 5);
  return (
    <Panel title="Value per share: every method vs the price" note="Bars show the range each method gives. The brass marker is your DCF; vertical lines are the prices offered.">
      <div className="grid grid-cols-[120px_1fr] gap-x-3 md:grid-cols-[160px_1fr]">
        <div />
        <div className="relative h-10">
          {lines.map((l, i) => (
            <span key={l.label} className="absolute -translate-x-1/2 whitespace-nowrap text-[10px] font-semibold" style={{ left: x(l.v), top: i % 2 ? 18 : 0, color: l.color }}>{l.label} {usd(l.v)}</span>
          ))}
        </div>
        {rows.map((r) => (
          <div key={r.label} className="contents">
            <div className="flex flex-col justify-center py-2"><span className="text-xs font-medium text-ink">{r.label}</span><span className="text-[10px] text-muted">{r.note}</span></div>
            <div className="relative my-2 h-7 rounded-[2px] bg-paper">
              {lines.map((l) => <span key={l.label} className="absolute -top-2 -bottom-2 w-px" style={{ left: x(l.v), background: l.color, opacity: 0.7 }} />)}
              <div className="group absolute top-1 h-5 rounded-[2px] transition-all duration-500" style={{ left: x(r.lo), width: `calc(${x(r.hi)} - ${x(r.lo)})`, background: r.color, opacity: 0.85 }}>
                <span className="pointer-events-none absolute -top-6 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-[2px] bg-ink px-1.5 py-0.5 text-[10px] text-paper opacity-0 transition-opacity group-hover:opacity-100">{usd(r.lo)} – {usd(r.hi)}</span>
              </div>
              {r.mark != null && <span className="absolute top-2.5 h-2 w-2 -translate-x-1/2 rounded-full bg-card" style={{ left: x(r.mark) }} />}
            </div>
          </div>
        ))}
        <div className="flex items-center py-2"><span className="text-xs font-semibold text-brass">Your DCF</span></div>
        <div className="relative my-2 h-7">
          <span className="absolute top-0 flex -translate-x-1/2 flex-col items-center transition-[left] duration-300 ease-out" style={{ left: x(live) }}>
            <span className="h-4 w-4 rotate-45 rounded-[2px] border-2 border-brass bg-card shadow" />
            <span className="num mt-1 text-[11px] font-semibold text-brass">{usd(live)}</span>
          </span>
        </div>
        <div />
        <div className="relative mt-3 h-4 border-t border-rule">
          {ticks.map((t) => <span key={t} className="num absolute top-1 -translate-x-1/2 text-[10px] text-muted" style={{ left: x(t) }}>${t}</span>)}
        </div>
      </div>
    </Panel>
  );
}

function Bridge({ P }: { P: Perspective }) {
  const b = P.bridge;
  const steps = [
    { name: "EV ops", delta: P.outputs.enterprise_value_ops, total: true },
    { name: "+ Sky 39%", delta: b.plus_sky_39pct_stake },
    { name: "+ Other inv.", delta: b.plus_other_investments_book },
    { name: "− Debt", delta: -b.less_debt },
    { name: "+ Cash", delta: b.plus_cash },
    { name: "− NCI", delta: -b.less_noncontrolling_interests },
    { name: "Equity value", delta: P.outputs.equity_value, total: true },
  ];
  let run = 0;
  const wf = steps.map((s) => {
    if (s.total) { run = s.delta; return { name: s.name, base: 0, value: s.delta, kind: "total", delta: s.delta }; }
    const start = run; run += s.delta;
    return { name: s.name, base: Math.min(start, run), value: Math.abs(s.delta), kind: s.delta >= 0 ? "up" : "down", delta: s.delta };
  });
  return (
    <Panel note="The Sky stake is valued at offer prices (A: 21CF's £10.75; B: Comcast's £12.50), not book. Hulu and other investments are at book. The regional sports networks are inside EV (they were part of the deal perimeter on both dates) and are not added twice. The New Fox dividend cash and the matching transaction-tax payable are excluded together.">
      <div className="h-72">
        <ResponsiveContainer>
          <BarChart data={wf} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
            <CartesianGrid {...gridProps} />
            <XAxis dataKey="name" {...axisProps} interval={0} angle={-30} textAnchor="end" height={52} tick={{ fill: PALETTE.muted, fontSize: 10 }} />
            <YAxis {...axisProps} width={52} tickFormatter={(v) => `${(v / 1000).toFixed(0)}bn`} />
            <Tooltip {...tooltipStyle} formatter={(_v: number, _k: string, p: { payload?: { delta: number } }) => [musd(p.payload?.delta ?? 0), "Amount"]} />
            <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
            <Bar dataKey="value" stackId="w" isAnimationActive={false}>
              {wf.map((s) => <Cell key={s.name} fill={s.kind === "total" ? PALETTE.navy : s.kind === "up" ? PALETTE.s3 : PALETTE.s2} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

function Comps({ d, pk, P }: { d: Dashboard; pk: PerspectiveKey; P: Perspective }) {
  const comps = d.comps.filter((c) => c.perspective === pk);
  const compsRange = (m: string) => { const xs = P.comps.filter((c) => c.case.startsWith(m)).map((c) => c.v); return xs.length ? `${usd(Math.min(...xs))} – ${usd(Math.max(...xs))}` : "–"; };
  return (
    <Panel note="LTM, as of the perspective date. Share counts are diluted weighted-average shares (a labelled proxy). Netflix is excluded from the ranges (content amortization is outside D&A; priced on growth); Disney is the acquirer and shown for reference only. Time Warner, Viacom, CBS and Discovery lack accessible historical prices.">
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
  );
}
