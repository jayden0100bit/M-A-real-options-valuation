import { useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard } from "../lib/data";
import { binomialCall, blackScholesCall } from "../lib/finance";
import { PALETTE, bn, musd, pct, usd } from "../lib/format";
import { Badge, Legend, Panel, Section, Segmented, Slider, Source, Stat, Table, axisProps, gridProps, tooltipStyle } from "../components/ui";

export default function Options({ d }: { d: Dashboard }) {
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
  const conv = useMemo(() => [10, 25, 50, 100, 200, 400, 800, 1600].map((k) => ({ n: k, crr: binomialCall(S, K, r, T, sigma, k, false, q), bs: bs.call })), [S, K, r, T, sigma, q, bs.call]);
  const curve = useMemo(() => Array.from({ length: 41 }, (_, i) => { const s = S0 * (0.5 + i * 0.025); return { s, value: blackScholesCall(s, K, r, T, sigma, q).call, payoff: Math.max(s - K, 0) }; }), [S0, K, r, T, sigma, q]);
  const scen = d.options.outputs.filter((o) => o.section === "Scenario" && o.metric === "option_value_american_crr");
  const deal = d.options.outputs.filter((o) => o.section === "Deal justification with option");
  const changed = S !== S0 || kRatio !== 1 || sigma !== sig0 || T !== T0 || r !== r0 || q !== 0;
  return (
    <Section id="options" kicker="06 · Real options" title="Revenue synergies as an option to expand"
      lede={<>The $2.0bn of cost synergies were a commitment. Revenue synergies were not: Disney's advisors valued them, but Disney never quantified them, and capturing them
        required further investment in content for its own streaming services. That is a right, not an obligation. Pricing it as a call option values the <i>flexibility</i>, instead of
        booking the advisors' {bn(S0)} as if it were certain and free.</>}>
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Panel title="Option inputs (May 2018)" right={changed ? <button className="text-xs font-medium text-navy underline-offset-4 hover:underline" onClick={() => { setS(S0); setK(1); setSigma(sig0); setT(T0); setR(r0); setQ(0); }}>Reset</button> : null}>
          <div className="space-y-5">
            <Slider label="S · PV of revenue synergies" value={S} min={S0 * 0.6} max={S0 * 1.4} step={50} onChange={setS} fmt={(x) => bn(x)} hint="Derived from the advisors' disclosed ranges (proxy p.145)" />
            <Slider label="K · investment required (× S₀)" value={kRatio} min={0.5} max={1.5} step={0.05} onChange={setK} fmt={(x) => `${x.toFixed(2)}x`} hint="Estimate: not disclosed; base is at the money" />
            <Slider label="σ · volatility" value={sigma} min={0.05} max={0.5} step={0.005} onChange={setSigma} fmt={(x) => pct(x, 1)} hint="Base: median peer asset volatility" />
            <Slider label="T · decision window" value={T} min={0.5} max={6} step={0.25} onChange={setT} fmt={(x) => `${x.toFixed(2)} yrs`} hint="Base: to fiscal 2021" />
            <Slider label="r · risk-free" value={r} min={0.005} max={0.05} step={0.0005} onChange={setR} fmt={(x) => pct(x, 2)} hint="3-year Treasury, 30 May 2018" />
            <Slider label="q · value leakage while waiting" value={q} min={0} max={0.08} step={0.0025} onChange={setQ} fmt={(x) => pct(x, 2)} hint="Competition erodes the opportunity" />
          </div>
        </Panel>
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            <Stat label="Black-Scholes value" value={bn(bs.call, 2)} sub={`${usd(bs.call / shares)} per 21CF share`} />
            <Stat label={`CRR ${style}, ${n} steps`} value={bn(tree, 2)} sub={`vs Black-Scholes ${pct((treeEu - bs.call) / bs.call, 3, true)}`} />
            <Stat label="Early-exercise premium" value={musd(tree - treeEu)} sub={q > 0 ? "American minus European" : "Zero without leakage"} />
            <Stat label="Static NPV (S − K)" value={bn(S - K)} sub="What a DCF would add if investment were committed now" />
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            <Panel title="Binomial convergence to Black-Scholes" right={<Segmented label="Exercise" value={style} onChange={setStyle} options={[{ value: "european", label: "European" }, { value: "american", label: "American" }]} />}>
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
              <div className="mt-3"><Slider label="Steps for the CRR value above" value={n} min={20} max={2000} step={20} onChange={setN} fmt={(x) => `${x}`} /></div>
            </Panel>
            <Panel title="Option value vs the underlying">
              <Legend items={[{ label: "Option value today", color: PALETTE.s1 }, { label: "Exercise now (max(S − K, 0))", color: PALETTE.muted, dash: true }]} />
              <div className="mt-2 h-48">
                <ResponsiveContainer>
                  <LineChart data={curve} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="s" {...axisProps} type="number" domain={["dataMin", "dataMax"]} tickFormatter={(x) => `${(x / 1000).toFixed(0)}bn`} />
                    <YAxis {...axisProps} width={44} tickFormatter={(x) => `${(x / 1000).toFixed(0)}bn`} />
                    <Tooltip {...tooltipStyle} formatter={(x: number, k: string) => [musd(x), k === "value" ? "Option value" : "Exercise now"]} labelFormatter={(l) => `S = ${bn(Number(l))}`} />
                    <ReferenceLine x={K} stroke={PALETTE.rule} />
                    <Line dataKey="payoff" stroke={PALETTE.muted} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                    <Line dataKey="value" stroke={PALETTE.s1} strokeWidth={2} dot={false} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-muted">The gap between the curves is the value of waiting: largest at the money and with high volatility.</p>
            </Panel>
          </div>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Scenarios (American CRR, 2,000 steps)" note="Bear: S at the low end of the advisors' range, σ −10pp, 2 years, 3% leakage. Bull: S high, σ +10pp, 4 years.">
          <Table head={["Scenario", "Option value", "Per share", ""]} align={["l", "r", "r", "r"]}
            rows={scen.map((s) => [s.case, bn(s.v, 2), usd(s.v / shares), <Badge kind="estimate" />])} />
        </Panel>
        <Panel title="Effect on value created at the amended $38 offer" note="Standalone equity + net cost synergies − $38 × 1,871.1m shares, with and without the option.">
          <Table head={["View", "Value created"]} rows={deal.map((x) => [x.case, <span className={x.v < 0 ? "text-s2" : ""}>{bn(x.v)}</span>])} />
        </Panel>
      </div>
      <Source>real_options_inputs.csv, real_options_outputs.csv, binomial_convergence.csv (Stage 5A). The Black-Scholes and CRR functions extend those in the original illustrative notebook.</Source>
    </Section>
  );
}
