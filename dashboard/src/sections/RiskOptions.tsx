import { useDeferredValue, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard } from "../lib/data";
import { binomialCall, binomialLattice, blackScholesCall, percentile, simulate, type ModelB } from "../lib/finance";
import { PALETTE, bn, musd, pct, usd } from "../lib/format";
import { Badge, Details, Finding, Legend, Num, Panel, Reveal, ResetButton, Section, Segmented, Slider, Stat, SubHead, Table, Term, TornadoRow, axisProps, gridProps, tooltipStyle } from "../components/ui";

export default function RiskOptions({ d }: { d: Dashboard }) {
  const opt = d.options.outputs.find((o) => o.section === "Option value" && o.metric === "black_scholes_call")!.v;
  const p38 = Number(d.montecarlo.summary.find((r) => r.metric === "value_created_vs_amended_38")!.prob_positive);
  const p38o = Number(d.montecarlo.summary.find((r) => r.metric === "value_created_incl_option_vs_amended_38")!.prob_positive);
  return (
    <Section id="risk" index="04" kicker="Risk & real options" title="How much was uncertainty worth, and how risky was the bet?"
      lede={<>Cost savings were a commitment. The streaming upside was not: Disney could invest more later <i>if</i> it worked. That flexibility is a <Term k="realoption">real option</Term>.
        Then a <Term k="montecarlo">Monte Carlo simulation</Term> asks how often the deal creates value when everything is uncertain at once.</>}
      takeaway={<>The streaming option is worth about {bn(opt)} and lifts the chance of creating value at $38 from {pct(p38, 0)} to {pct(p38o, 0)}: close to a coin flip.</>}>
      <OptionsBlock d={d} />
      <MonteCarloBlock d={d} />
    </Section>
  );
}

// ======================================================================= real options (Stage 5A)
function OptionsBlock({ d }: { d: Dashboard }) {
  const inp = (p: string) => d.options.inputs.find((x) => x.parameter === p)!;
  const S0 = inp("S_underlying_pv_revenue_synergies").value, K0 = inp("K_exercise_cost").value, sig0 = inp("sigma_volatility").value;
  const r0 = inp("r_risk_free").value, T0 = inp("T_maturity_years").value;
  const shares = d.valuation["B_proxy_2018-05"].shares;
  const [S, setS] = useState(S0), [kRatio, setK] = useState(1), [sigma, setSigma] = useState(sig0), [T, setT] = useState(T0), [r, setR] = useState(r0), [q, setQ] = useState(0);
  const [n, setN] = useState(500), [style, setStyle] = useState<"european" | "american">("american");
  const K = K0 * kRatio;
  const bs = useMemo(() => blackScholesCall(S, K, r, T, sigma, q), [S, K, r, T, sigma, q]);
  const tree = useMemo(() => binomialCall(S, K, r, T, sigma, n, style === "american", q), [S, K, r, T, sigma, n, style, q]);
  const treeEu = useMemo(() => binomialCall(S, K, r, T, sigma, n, false, q), [S, K, r, T, sigma, n, q]);
  const lattice = useMemo(() => binomialLattice(S, K, r, T, sigma, 4, style === "american", q), [S, K, r, T, sigma, style, q]);
  const conv = useMemo(() => [10, 25, 50, 100, 200, 400, 800, 1600].map((k) => ({ n: k, crr: binomialCall(S, K, r, T, sigma, k, false, q), bs: bs.call })), [S, K, r, T, sigma, q, bs.call]);
  const curve = useMemo(() => Array.from({ length: 41 }, (_, i) => { const s = S0 * (0.5 + i * 0.025); return { s, value: blackScholesCall(s, K, r, T, sigma, q).call, payoff: Math.max(s - K, 0) }; }), [S0, K, r, T, sigma, q]);
  const scen = d.options.outputs.filter((o) => o.section === "Scenario" && o.metric === "option_value_american_crr");
  const deal = d.options.outputs.filter((o) => o.section === "Deal justification with option");
  const sens = d.options.outputs.filter((o) => o.section === "Sensitivity (Black-Scholes)");
  const changed = S !== S0 || kRatio !== 1 || sigma !== sig0 || T !== T0 || r !== r0 || q !== 0;
  const reset = () => { setS(S0); setK(1); setSigma(sig0); setT(T0); setR(r0); setQ(0); };
  const staticNpv = S - K, flex = bs.call - Math.max(staticNpv, 0);

  return (
    <>
      <SubHead title="The streaming upside as an option">
        Disney's advisors put about {bn(S0)} on revenue synergies. Capturing them needed more investment in content, so we price it as a call option instead of counting {bn(S0)} as certain and free.
      </SubHead>
      <Reveal>
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <Panel title="Option assumptions" right={<ResetButton show={changed} onClick={reset} />}>
            <div className="space-y-6">
              <Slider label={<Term k="volatility">Volatility (σ)</Term>} value={sigma} min={0.05} max={0.5} step={0.005} onChange={setSigma} fmt={(x) => pct(x, 1)} base={sig0}
                explain="How uncertain the streaming payoff is. More uncertainty makes the option worth more, because Disney only invests if it goes well."
                hint="Base: median peer asset volatility" />
              <Slider label={<Term k="strike">Exercise cost (K)</Term>} value={kRatio} min={0.5} max={1.5} step={0.05} onChange={setK} fmt={(x) => `${bn(K0 * x)} · ${x.toFixed(2)}x`} base={1}
                explain="What Disney must invest to capture the upside, relative to its value. Cheaper to exercise = more valuable option."
                hint="Estimate: not disclosed; base is at the money (K = S)" />
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink">
                  More assumptions <span className="transition-transform group-open:rotate-45">+</span>
                </summary>
                <div className="mt-5 space-y-6">
                  <Slider label="S · value of the upside today" value={S} min={S0 * 0.6} max={S0 * 1.4} step={50} onChange={setS} fmt={(x) => bn(x)} base={S0} hint="Derived from the advisors' disclosed ranges (proxy p.145)" />
                  <Slider label="T · decision window" value={T} min={0.5} max={6} step={0.25} onChange={setT} fmt={(x) => `${x.toFixed(2)} yrs`} base={T0} explain="How long Disney can wait before deciding." hint="Base: to fiscal 2021" />
                  <Slider label="r · risk-free rate" value={r} min={0.005} max={0.05} step={0.0005} onChange={setR} fmt={(x) => pct(x, 2)} base={r0} hint="3-year Treasury, 30 May 2018" />
                  <Slider label="q · value leakage while waiting" value={q} min={0} max={0.08} step={0.0025} onChange={setQ} fmt={(x) => pct(x, 2)} base={0} explain="Competitors erode the opportunity each year Disney waits." />
                  <Segmented label="Exercise" value={style} onChange={setStyle} options={[{ value: "american", label: "American (exercise any time)" }, { value: "european", label: "European (at the end)" }]} />
                </div>
              </details>
            </div>
          </Panel>

          <div className="space-y-6">
            <Panel>
              <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
                <Stat big label={<><Term k="bs">Black-Scholes</Term> value</>} value={<Num v={bs.call} fmt={(x) => bn(x, 2)} />} sub={<><Num v={bs.call / shares} fmt={usd} /> per 21CF share</>} />
                <Stat label={<><Term k="binomial">Binomial</Term> ({style})</>} value={<Num v={tree} fmt={(x) => bn(x, 2)} />} sub={`${n} steps`} />
                <Stat label="If committed today (S − K)" value={<Num v={staticNpv} fmt={(x) => bn(x)} />} sub="what a plain DCF would add" />
                <Stat label="Value of flexibility" value={<Num v={flex} fmt={(x) => bn(x, 2)} />} tone="pos" sub="option minus committing now" />
              </div>
            </Panel>
            <div className="grid gap-6 xl:grid-cols-[1.25fr_1fr]">
              <Panel title="Binomial tree: the upside can rise or fall each step" note={`A 4-step illustration of the same model (values in $bn; top = option value, bottom = value of the upside). The headline uses ${n} steps.${style === "american" ? " Brass nodes: better to invest early." : ""}`}>
                <TreeDiagram lattice={lattice} T={T} />
              </Panel>
              <Panel title="Option value vs the upside's value">
                <Legend items={[{ label: "Option value today", color: PALETTE.s1 }, { label: "Invest now: max(S − K, 0)", color: PALETTE.muted, dash: true }]} />
                <div className="mt-2 h-52">
                  <ResponsiveContainer>
                    <LineChart data={curve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid {...gridProps} />
                      <XAxis dataKey="s" {...axisProps} type="number" domain={["dataMin", "dataMax"]} tickFormatter={(x) => `${(x / 1000).toFixed(0)}bn`} />
                      <YAxis {...axisProps} width={44} tickFormatter={(x) => `${(x / 1000).toFixed(0)}bn`} />
                      <Tooltip {...tooltipStyle} formatter={(x: number, k: string) => [musd(x), k === "value" ? "Option value" : "Invest now"]} labelFormatter={(l) => `S = ${bn(Number(l))}`} />
                      <ReferenceLine x={K} stroke={PALETTE.brass} strokeDasharray="3 3" label={{ value: "K", position: "top", fill: PALETTE.muted, fontSize: 11 }} />
                      <Line dataKey="payoff" stroke={PALETTE.muted} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                      <Line dataKey="value" stroke={PALETTE.s1} strokeWidth={2.5} dot={false} isAnimationActive={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-2 text-xs text-muted">The gap between the curves is the value of waiting: largest near K and when volatility is high.</p>
              </Panel>
            </div>
          </div>
        </div>
      </Reveal>

      <Reveal>
        <div className="grid gap-4 md:grid-cols-3">
          {scen.map((s) => (
            <div key={s.case} className="panel rounded-[3px] border border-rule bg-card p-5">
              <div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-wider text-muted">{s.case} case</p><Badge kind="estimate" /></div>
              <p className="num mt-2 font-serif text-3xl">{bn(s.v, 2)}</p>
              <p className="mt-1 text-xs text-muted">{usd(s.v / shares)} per 21CF share · American, 2,000 steps</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted">Bear: upside at the low end of the advisors' range, σ −10pp, 2 years, 3% leakage. Bull: upside high, σ +10pp, 4 years.</p>
      </Reveal>

      <Details summary="Convergence check, sensitivities and effect on the deal">
        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Binomial converges to Black-Scholes">
            <Legend items={[{ label: "CRR (European)", color: PALETTE.s1 }, { label: "Black-Scholes", color: PALETTE.s2, dash: true }]} />
            <div className="mt-2 h-48">
              <ResponsiveContainer>
                <LineChart data={conv} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="n" {...axisProps} scale="log" domain={[10, 1600]} type="number" ticks={[10, 50, 200, 800, 1600]} />
                  <YAxis {...axisProps} width={52} domain={["auto", "auto"]} tickFormatter={(x) => `${(x / 1000).toFixed(2)}bn`} />
                  <Tooltip {...tooltipStyle} formatter={(x: number) => [musd(x, 1), "Value"]} labelFormatter={(l) => `${l} steps`} />
                  <Line dataKey="crr" stroke={PALETTE.s1} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                  <Line dataKey="bs" stroke={PALETTE.s2} strokeDasharray="5 4" strokeWidth={1.5} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3"><Slider label="Steps for the binomial value" value={n} min={20} max={2000} step={20} onChange={setN} fmt={(x) => `${x}`} /></div>
            <p className="mt-3 text-xs text-muted">Difference vs Black-Scholes at {n} steps: {pct((treeEu - bs.call) / bs.call, 3, true)}. Early-exercise premium: {musd(tree - treeEu)} ({q > 0 ? "American minus European" : "zero without leakage"}).</p>
          </Panel>
          <Panel title="Pipeline sensitivities (Black-Scholes, one input at a time)">
            <Table head={["Input", "Option value"]} rows={sens.map((s) => [s.case, bn(s.v, 2)])} />
          </Panel>
        </div>
        <Panel title="Effect on value created at the amended $38 offer" note="Standalone equity + net cost synergies − $38 × 1,871.1m shares, with and without the option.">
          <Table head={["View", "Value created"]} rows={deal.map((x) => [x.case, <span className={x.v < 0 ? "text-s2" : ""}>{bn(x.v)}</span>])} />
        </Panel>
        <p className="text-xs text-muted">Source: real_options_inputs.csv, real_options_outputs.csv, binomial_convergence.csv (Stage 5A). The Black-Scholes and CRR functions extend those in the original illustrative notebook.</p>
      </Details>
    </>
  );
}

function TreeDiagram({ lattice, T }: { lattice: ReturnType<typeof binomialLattice>; T: number }) {
  const n = lattice.nodes.length - 1, W = 420, H = 300, dx = (W - 84) / n, dy = 31;
  const pos = (i: number, j: number) => ({ x: 42 + i * dx, y: H / 2 - 4 - (2 * j - i) * dy });
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mx-auto w-full max-w-[520px]" role="img" aria-label="Binomial tree of option values">
      {lattice.nodes.slice(0, n).map((col, i) => col.map((_, j) => {
        const a = pos(i, j), u = pos(i + 1, j + 1), dn = pos(i + 1, j);
        return <g key={`e${i}-${j}`} stroke={PALETTE.rule} strokeWidth={1.2}><line x1={a.x} y1={a.y} x2={u.x} y2={u.y} /><line x1={a.x} y1={a.y} x2={dn.x} y2={dn.y} /></g>;
      }))}
      {lattice.nodes.map((col, i) => col.map((nd, j) => {
        const p = pos(i, j), term = i === n, itm = nd.v > 0.5;
        const fill = nd.early ? "#f3e7d3" : term ? (itm ? "#d7f0e5" : "#efece6") : PALETTE.card;
        const stroke = nd.early ? PALETTE.brass : term ? (itm ? PALETTE.s3 : PALETTE.rule) : PALETTE.navy;
        return (
          <g key={`n${i}-${j}`} style={{ transition: "all .3s" }}>
            <rect x={p.x - 34} y={p.y - 17} width={68} height={34} rx={3} fill={fill} stroke={stroke} strokeWidth={i === 0 ? 2 : 1} />
            <text x={p.x} y={p.y - 1} textAnchor="middle" fontSize={13} fontWeight={600} fill={PALETTE.ink} className="num">{(nd.v / 1000).toFixed(1)}</text>
            <text x={p.x} y={p.y + 12} textAnchor="middle" fontSize={10} fill={PALETTE.muted} className="num">S {(nd.s / 1000).toFixed(1)}</text>
          </g>);
      }))}
      <text x={42} y={H - 4} textAnchor="middle" fontSize={11} fill={PALETTE.muted}>Today</text>
      <text x={42 + n * dx} y={H - 4} textAnchor="middle" fontSize={11} fill={PALETTE.muted}>Year {T.toFixed(T % 1 ? 2 : 0)}</text>
    </svg>
  );
}

// ======================================================================= Monte Carlo (Stage 5B)
type Key = "amended_38" | "original_at_2018-05-30";
type Settings = { realMode: number; icHi: number; growthSd: number; marginSd: number };
const PRESETS: Record<string, { label: string; s: Settings; note: string }> = {
  pipeline: { label: "Pipeline assumptions", s: { realMode: 1.0, icHi: 2.0, growthSd: 0.01, marginSd: 0.01 }, note: "The distributions used in the Stage 5B run." },
  rough: { label: "Integration struggles", s: { realMode: 0.7, icHi: 3.0, growthSd: 0.01, marginSd: 0.01 }, note: "Savings most likely at 70% of guidance; integration could cost up to 3x run-rate." },
  smooth: { label: "Smooth integration", s: { realMode: 1.2, icHi: 1.0, growthSd: 0.01, marginSd: 0.01 }, note: "Savings most likely above guidance; integration costs capped at 1x run-rate." },
  volatile: { label: "Uncertain business", s: { realMode: 1.0, icHi: 2.0, growthSd: 0.02, marginSd: 0.02 }, note: "Twice the uncertainty on revenue growth and margins." },
};

function bins(values: Float64Array, nb = 50) {
  const lo = values[0], hi = values[values.length - 1], w = (hi - lo) / nb || 1;
  const counts = new Array(nb).fill(0);
  values.forEach((v) => { counts[Math.min(nb - 1, Math.floor((v - lo) / w))]++; });
  return counts.map((c, i) => ({ x: (lo + (i + 0.5) * w) / 1000, c }));
}

function MonteCarloBlock({ d }: { d: Dashboard }) {
  const M = d.montecarlo, B = d.valuation["B_proxy_2018-05"];
  const [key, setKey] = useState<Key>("amended_38");
  const pipe = M.summary.find((r) => r.metric === `value_created_vs_${key}`)!;
  const pipeOpt = M.summary.find((r) => r.metric === `value_created_incl_option_vs_${key}`)!;
  const h = M.histogram_bn[key];
  const pipeHist = h.counts.map((c, i) => ({ x: (h.edges[i] + h.edges[i + 1]) / 2, c }));

  const [preset, setPreset] = useState("pipeline");
  const [s, setS] = useState<Settings>(PRESETS.pipeline.s);
  const [n, setN] = useState(10000), [seed, setSeed] = useState(1);
  const [view, setView] = useState<"live" | "pipeline">("live");
  const set = (k: keyof Settings) => (x: number) => { setPreset("custom"); setS((o) => ({ ...o, [k]: x })); };
  const choose = (p: string) => { setPreset(p); if (PRESETS[p]) setS(PRESETS[p].s); };
  const job = useDeferredValue({ s, n, seed, key });
  const sim = useMemo(() => {
    const t0 = performance.now();
    const v = simulate(B.model as ModelB, M.synergy_base, B.tax, B.g, M.paid[job.key],
      { n: job.n, seed: job.seed, real: [0.5, job.s.realMode, 1.25], delayP: [0.6, 0.3, 0.1], ic: [0.75, 1.0, job.s.icHi], growthSd: job.s.growthSd, marginSd: job.s.marginSd, clip: 0.03 });
    const sorted = Float64Array.from(v).sort();
    const mean = v.reduce((a, b) => a + b, 0) / v.length;
    return { mean, p05: percentile(sorted, 0.05), p50: percentile(sorted, 0.5), p95: percentile(sorted, 0.95), pos: v.filter((x) => x > 0).length / v.length, ms: performance.now() - t0, hist: bins(sorted) };
  }, [job, B, M]);
  const stale = job.s !== s || job.n !== n || job.seed !== seed || job.key !== key;
  const hist = view === "live" ? sim.hist : pipeHist;
  const torn = M.tornado.map((t) => ({ v: String(t.variable).replace(/_/g, " "), lo: Math.min(Number(t.value_created_at_p05), Number(t.value_created_at_p95)), hi: Math.max(Number(t.value_created_at_p05), Number(t.value_created_at_p95)) }));
  const base = Number(M.tornado[0].base_value_created);

  return (
    <>
      <SubHead title="Monte Carlo: how often does the deal create value?">
        Each simulation redraws revenue growth, margins, synergy realization, delays and integration costs, reruns the DCF and synergy models, and compares the total with the price.
      </SubHead>
      <Reveal>
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:gap-5">
          <Segmented size="md" label="Price compared against" value={key} onChange={setKey} options={[{ value: "amended_38", label: "Amended $38 offer" }, { value: "original_at_2018-05-30", label: "Original offer (May 2018 value)" }]} />
          <p className="text-sm text-muted">Pipeline run: {M.n.toLocaleString("en-US")} simulations, seed {M.seed}.</p>
        </div>
      </Reveal>
      <Reveal>
        <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
          <Stat big label="Chance of creating value" value={<Num v={Number(pipe.prob_positive)} fmt={(x) => pct(x, 1)} />} sub={<><Num v={Number(pipeOpt.prob_positive)} fmt={(x) => pct(x, 1)} /> with the streaming option</>} />
          <Stat label="Median value created" value={<Num v={Number(pipe.p50)} fmt={(x) => bn(x)} />} tone={Number(pipe.p50) < 0 ? "neg" : "pos"} />
          <Stat label={<>Bad case · 5th <Term k="percentile">percentile</Term></>} value={<Num v={Number(pipe.p05)} fmt={(x) => bn(x)} />} tone={Number(pipe.p05) < 0 ? "neg" : "pos"} />
          <Stat label="Good case · 95th percentile" value={<Num v={Number(pipe.p95)} fmt={(x) => bn(x)} />} tone={Number(pipe.p95) < 0 ? "neg" : "pos"} />
        </div>
      </Reveal>

      <Reveal>
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <Panel title="Explore scenarios" right={<Badge kind="estimate" />}>
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(PRESETS).map(([k, p]) => (
                  <button key={k} onClick={() => choose(k)}
                    className={`rounded-[3px] border px-3 py-2 text-left text-xs font-medium transition-all duration-200 ${preset === k ? "border-navy bg-navy text-card shadow-sm" : "border-rule bg-paper text-ink hover:-translate-y-0.5 hover:border-navy/50"}`}>{p.label}</button>
                ))}
              </div>
              <p className="-mt-3 text-[11px] leading-snug text-muted">{PRESETS[preset]?.note ?? "Custom settings."} What-if presets are illustrative; only "Pipeline assumptions" matches the Stage 5B run.</p>
              <Slider label="Synergy realization: most likely" value={s.realMode} min={0.6} max={1.2} step={0.05} onChange={set("realMode")} fmt={(x) => pct(x, 0)} base={1}
                explain="The most likely share of the guided savings achieved (range 50%–125%)." />
              <Slider label="Integration cost: worst case" value={s.icHi} min={1.0} max={3.0} step={0.1} onChange={set("icHi")} fmt={(x) => `${x.toFixed(1)}x`} base={2}
                explain="The highest integration bill considered, as a multiple of run-rate savings." />
              <Slider label="Revenue-growth uncertainty" value={s.growthSd} min={0} max={0.02} step={0.0025} onChange={set("growthSd")} fmt={(x) => `±${pct(x, 2)}`} base={0.01}
                explain="How far yearly growth could miss or beat the forecast (1 standard deviation)." />
              <Slider label="Margin uncertainty" value={s.marginSd} min={0} max={0.02} step={0.0025} onChange={set("marginSd")} fmt={(x) => `±${pct(x, 2)}`} base={0.01}
                explain="How far profit margins could miss or beat the forecast." />
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink">
                  Simulation settings <span className="transition-transform group-open:rotate-45">+</span>
                </summary>
                <div className="mt-5 space-y-5">
                  <Slider label="Simulations" value={n} min={1000} max={20000} step={1000} onChange={setN} fmt={(x) => x.toLocaleString("en-US")} />
                  <button onClick={() => setSeed((x) => x + 1)} className="w-full rounded-[3px] border border-navy py-2 text-xs font-semibold text-navy transition-colors hover:bg-navy hover:text-card">Re-draw with a new random seed (#{seed})</button>
                </div>
              </details>
            </div>
          </Panel>

          <Panel title="Value created for Disney, USD bn" right={<Segmented label="Distribution shown" value={view} onChange={setView} options={[{ value: "live", label: "Your simulation" }, { value: "pipeline", label: "Pipeline run" }]} />}>
            <div className={`grid grid-cols-2 gap-6 transition-opacity duration-200 md:grid-cols-4 ${stale ? "opacity-60" : ""}`}>
              <Stat label="Chance > 0" value={<Num v={sim.pos} fmt={(x) => pct(x, 1)} />} tone={sim.pos < 0.5 ? "neg" : "pos"} sub={`pipeline ${pct(Number(pipe.prob_positive), 1)}`} />
              <Stat label="Average" value={<Num v={sim.mean} fmt={(x) => bn(x)} />} tone={sim.mean < 0 ? "neg" : "pos"} sub={`pipeline ${bn(Number(pipe.mean))}`} />
              <Stat label="5th – 95th" value={<span className="text-[1.35rem]"><Num v={sim.p05 / 1000} fmt={(x) => (x < 0 ? "−" : "") + Math.abs(x).toFixed(1)} /> to <Num v={sim.p95 / 1000} fmt={(x) => (x < 0 ? "−" : "") + Math.abs(x).toFixed(1)} /></span>} sub="USD bn" />
              <Stat label="Run time" value={`${sim.ms.toFixed(0)} ms`} sub={`${job.n.toLocaleString("en-US")} runs in your browser`} />
            </div>
            <div className="mt-5 h-64">
              <ResponsiveContainer>
                <BarChart data={hist} barCategoryGap={1} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="x" {...axisProps} type="number" domain={["dataMin", "dataMax"]} tickFormatter={(x) => `${x.toFixed(0)}`} />
                  <YAxis {...axisProps} width={40} />
                  <Tooltip {...tooltipStyle} formatter={(c: number) => [c, "Simulations"]} labelFormatter={(x) => `≈ ${Number(x).toFixed(1)}bn`} />
                  <ReferenceLine x={0} stroke={PALETTE.ink} label={{ value: "break-even", position: "insideTopRight", fill: PALETTE.muted, fontSize: 10 }} />
                  <Bar dataKey="c" isAnimationActive={false}>{hist.map((b) => <Cell key={b.x} fill={b.x > 0 ? PALETTE.s3 : PALETTE.s2} fillOpacity={0.85} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-muted">
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-3 bg-s3" />Disney creates value</span>
              <span className="inline-flex items-center gap-1.5"><span className="h-2 w-3 bg-s2" />Disney overpays</span>
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-muted">Value created = standalone equity + net cost synergies − price (before the streaming option). The browser uses a different random generator from the Python run, so results match statistically, not draw for draw; the model equations are the same and are tested against the pipeline.</p>
          </Panel>
        </div>
      </Reveal>

      <Reveal>
        <Panel title="What drives the outcome most (vs $38)" note={`Each input moved to its 5th / 95th percentile with everything else at base. Base (all central values): ${bn(base)}. Values in USD bn.`}>
          <div className="space-y-2.5">{torn.map((t) => <TornadoRow key={t.v} label={t.v} lo={t.lo} hi={t.hi} domain={[-16000, 13000]} fmt={(x) => (x / 1000).toFixed(1)} />)}</div>
          <div className="mt-5 space-y-2">
            <Finding>Revenue growth and synergy realization matter most: getting either wrong swings value by more than {bn(Math.min(...M.tornado.slice(0, 2).map((t) => Number(t.swing))), 0)}.</Finding>
          </div>
        </Panel>
      </Reveal>

      <Details summary="Distribution inputs and deterministic vs simulated scenarios">
        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Distribution inputs" note="All distributions are estimates. The anchors are the Stage 3 sensitivity ranges and the Stage 4 bear/bull cases. Variables are independent, which understates the tails if growth, margins and synergies move together.">
            <Table head={["Input", "Distribution", "Anchor"]} align={["l", "l", "l"]} rows={M.inputs.filter((i) => i.value_type === "estimate" && i.variable !== "expansion_option_value").map((i) => [String(i.variable).replace(/_/g, " "), `${i.distribution} ${i.parameters}`, <span className="text-xs text-muted">{String(i.anchor)}</span>])} />
          </Panel>
          <Panel title="Scenarios vs $38 (USD bn)">
            <Table head={["Scenario", "Net synergies", "Value created"]} rows={M.scenarios.map((x) => [String(x.source), bn(Number(x.net_synergy_value)), <span className={Number(x.value_created_vs_38) < 0 ? "text-s2" : ""}>{bn(Number(x.value_created_vs_38))}</span>])} />
          </Panel>
        </div>
        <p className="text-xs text-muted">Source: monte_carlo_inputs.csv, monte_carlo_summary.csv, monte_carlo_tornado.csv and the binned draws (Stage 5B). With all shocks at zero the engine reproduces the Stage 3 EV and the Stage 4 synergy value (checked).</p>
      </Details>
    </>
  );
}
