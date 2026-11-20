import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard } from "../lib/data";
import { percentile, simulate, type ModelB } from "../lib/finance";
import { PALETTE, bn, pct } from "../lib/format";
import { Badge, Panel, Section, Segmented, Slider, Source, Stat, Table, axisProps, gridProps, tooltipStyle } from "../components/ui";

type Key = "amended_38" | "original_at_2018-05-30";

function bins(values: Float64Array, nb = 60) {
  const lo = values[0], hi = values[values.length - 1], w = (hi - lo) / nb || 1;
  const counts = new Array(nb).fill(0);
  values.forEach((v) => { counts[Math.min(nb - 1, Math.floor((v - lo) / w))]++; });
  return counts.map((c, i) => ({ x: (lo + (i + 0.5) * w) / 1000, c }));
}

export default function MonteCarlo({ d }: { d: Dashboard }) {
  const M = d.montecarlo, B = d.valuation["B_proxy_2018-05"];
  const [key, setKey] = useState<Key>("amended_38");
  const pipe = M.summary.find((r) => r.metric === `value_created_vs_${key}`)!;
  const pipeOpt = M.summary.find((r) => r.metric === `value_created_incl_option_vs_${key}`)!;
  const h = M.histogram_bn[key];
  const hist = h.counts.map((c, i) => ({ x: (h.edges[i] + h.edges[i + 1]) / 2, c }));
  // browser re-simulation
  const [n, setN] = useState(10000), [seed, setSeed] = useState(1), [realMode, setRealMode] = useState(1.0), [growthSd, setGrowthSd] = useState(0.01), [marginSd, setMarginSd] = useState(0.01), [icHi, setIcHi] = useState(2.0);
  const [run, setRun] = useState(0);
  const sim = useMemo(() => {
    if (!run) return null;
    const t0 = performance.now();
    const v = simulate(B.model as ModelB, M.synergy_base, B.tax, B.g, M.paid[key], { n, seed, real: [0.5, realMode, 1.25], delayP: [0.6, 0.3, 0.1], ic: [0.75, 1.0, icHi], growthSd, marginSd, clip: 0.03 });
    const sorted = Float64Array.from(v).sort();
    const mean = v.reduce((a, b) => a + b, 0) / v.length;
    return { sorted, mean, p05: percentile(sorted, 0.05), p50: percentile(sorted, 0.5), p95: percentile(sorted, 0.95), pos: v.filter((x) => x > 0).length / v.length, ms: performance.now() - t0, hist: bins(sorted) };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run]);
  const torn = M.tornado.map((t) => ({ v: String(t.variable).replace(/_/g, " "), lo: Math.min(Number(t.value_created_at_p05), Number(t.value_created_at_p95)), hi: Math.max(Number(t.value_created_at_p05), Number(t.value_created_at_p95)) }));
  const base = Number(M.tornado[0].base_value_created);
  return (
    <Section id="montecarlo" kicker="07 · Monte Carlo and sensitivity" title="How likely was Disney to create value?"
      lede="Each of 20,000 draws reruns the May 2018 DCF (with revenue-growth and margin shocks) and the synergy model (realization, delay, integration costs), then compares the total with the price paid. The distributions are labelled estimates anchored to the Stage 3–4 ranges. Variables are independent, which understates the tails if growth, margins and synergies move together.">
      <div className="flex flex-wrap items-center gap-4">
        <Segmented label="Consideration" value={key} onChange={setKey} options={[{ value: "amended_38", label: "Amended $38 offer" }, { value: "original_at_2018-05-30", label: "Original offer (30 May 2018 value)" }]} />
      </div>
      <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
        <Stat label="P(value created > 0)" value={pct(Number(pipe.prob_positive), 1)} sub={`${pct(Number(pipeOpt.prob_positive), 1)} including the revenue-synergy option`} />
        <Stat label="Median value created" value={bn(Number(pipe.p50))} tone={Number(pipe.p50) < 0 ? "neg" : undefined} />
        <Stat label="5th percentile" value={bn(Number(pipe.p05))} tone={Number(pipe.p05) < 0 ? "neg" : undefined} />
        <Stat label="95th percentile" value={bn(Number(pipe.p95))} />
      </div>
      <Panel title={`Value created for Disney, USD bn (pipeline run: ${M.n.toLocaleString("en-US")} draws, seed ${M.seed})`} right={<Badge kind="estimate" />}
        note="Value created = standalone equity + net cost synergies − consideration. Draws with value above zero are shown in green.">
        <div className="h-64">
          <ResponsiveContainer>
            <BarChart data={hist} barCategoryGap={1} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="x" {...axisProps} type="number" domain={["dataMin", "dataMax"]} tickFormatter={(x) => `${x.toFixed(0)}`} />
              <YAxis {...axisProps} width={40} />
              <Tooltip {...tooltipStyle} formatter={(c: number) => [c, "Draws"]} labelFormatter={(x) => `≈ ${Number(x).toFixed(1)}bn`} />
              <ReferenceLine x={0} stroke={PALETTE.ink} />
              <Bar dataKey="c" isAnimationActive={false}>{hist.map((b) => <Cell key={b.x} fill={b.x > 0 ? PALETTE.s3 : PALETTE.s1} />)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <Panel title="Drivers: value created vs $38, one input at its 5th / 95th percentile" note={`Base (all inputs at their central values): ${bn(base)}.`}>
          <div className="space-y-3">
            {torn.map((t) => {
              const lo = -16000, hi = 13000, x = (v: number) => ((v - lo) / (hi - lo)) * 100;
              return (
                <div key={t.v} className="grid grid-cols-[150px_1fr] items-center gap-3 text-xs">
                  <span className="text-muted">{t.v}</span>
                  <div className="relative h-6 rounded-sm bg-paper">
                    <div className="absolute top-0 h-full w-px bg-ink" style={{ left: `${x(0)}%` }} />
                    <div className="absolute top-1 h-4 rounded-[2px] bg-s1/80" style={{ left: `${x(t.lo)}%`, width: `${Math.max(0.5, x(t.hi) - x(t.lo))}%` }} />
                    <span className="num absolute top-1 -translate-x-full pr-1 text-[11px]" style={{ left: `${x(t.lo)}%` }}>{(t.lo / 1000).toFixed(1)}</span>
                    <span className="num absolute top-1 pl-1 text-[11px]" style={{ left: `${x(t.hi)}%` }}>{(t.hi / 1000).toFixed(1)}</span>
                  </div>
                </div>);
            })}
          </div>
        </Panel>
        <Panel title="Distribution inputs" note="All distributions are estimates. The anchors are the Stage 3 sensitivity ranges and the Stage 4 bear/bull cases.">
          <Table head={["Input", "Distribution", "Anchor"]} align={["l", "l", "l"]} rows={M.inputs.filter((i) => i.value_type === "estimate" && i.variable !== "expansion_option_value").map((i) => [String(i.variable).replace(/_/g, " "), `${i.distribution} ${i.parameters}`, <span className="text-xs text-muted">{String(i.anchor)}</span>])} />
        </Panel>
      </div>

      <Panel title="Re-run the simulation in your browser" note="Uses a different random generator from the Python run, so results match statistically, not draw for draw. The model equations are the same (tested against the pipeline outputs).">
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <div className="space-y-5">
            <Slider label="Draws" value={n} min={1000} max={20000} step={1000} onChange={setN} fmt={(x) => x.toLocaleString("en-US")} />
            <Slider label="Seed" value={seed} min={1} max={99} step={1} onChange={setSeed} fmt={(x) => `${x}`} />
            <Slider label="Synergy realization: most likely" value={realMode} min={0.6} max={1.2} step={0.05} onChange={setRealMode} fmt={(x) => pct(x, 0)} hint="Triangular(50%, mode, 125%)" />
            <Slider label="Integration cost: worst case" value={icHi} min={1.0} max={3.0} step={0.1} onChange={setIcHi} fmt={(x) => `${x.toFixed(1)}x`} hint="Triangular(0.75x, 1.0x, max)" />
            <Slider label="Revenue-growth shock (σ)" value={growthSd} min={0} max={0.02} step={0.0025} onChange={setGrowthSd} fmt={(x) => pct(x, 2)} />
            <Slider label="Margin shock (σ)" value={marginSd} min={0} max={0.02} step={0.0025} onChange={setMarginSd} fmt={(x) => pct(x, 2)} />
            <button onClick={() => setRun((x) => x + 1)} className="w-full rounded-sm bg-navy py-2.5 text-sm font-semibold text-card transition-colors hover:bg-ink">Run simulation</button>
          </div>
          <div>
            {!sim && <p className="py-16 text-center text-sm text-muted">Set the inputs and run. The pipeline results above stay unchanged.</p>}
            {sim && (
              <>
                <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
                  <Stat label="P(value > 0)" value={pct(sim.pos, 1)} sub={`pipeline ${pct(Number(pipe.prob_positive), 1)}`} />
                  <Stat label="Mean" value={bn(sim.mean)} sub={`pipeline ${bn(Number(pipe.mean))}`} />
                  <Stat label="5th / 95th" value={`${(sim.p05 / 1000).toFixed(1)} / ${(sim.p95 / 1000).toFixed(1)}`} sub="USD bn" />
                  <Stat label="Run time" value={`${sim.ms.toFixed(0)} ms`} sub={`${n.toLocaleString("en-US")} draws in the browser`} />
                </div>
                <div className="mt-4 h-52">
                  <ResponsiveContainer>
                    <BarChart data={sim.hist} barCategoryGap={1} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid {...gridProps} />
                      <XAxis dataKey="x" {...axisProps} type="number" domain={["dataMin", "dataMax"]} tickFormatter={(x) => `${x.toFixed(0)}`} />
                      <YAxis {...axisProps} width={40} />
                      <Tooltip {...tooltipStyle} formatter={(c: number) => [c, "Draws"]} labelFormatter={(x) => `≈ ${Number(x).toFixed(1)}bn`} />
                      <ReferenceLine x={0} stroke={PALETTE.ink} />
                      <Bar dataKey="c" isAnimationActive={false}>{sim.hist.map((b) => <Cell key={b.x} fill={b.x > 0 ? PALETTE.s3 : PALETTE.s1} />)}</Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </>)}
          </div>
        </div>
      </Panel>
      <Source>monte_carlo_inputs.csv, monte_carlo_summary.csv, monte_carlo_tornado.csv and the binned draws (Stage 5B). With all shocks at zero the engine reproduces the Stage 3 EV and the Stage 4 synergy value (checked).</Source>
    </Section>
  );
}
