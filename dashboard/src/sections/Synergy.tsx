import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard, PerspectiveKey } from "../lib/data";
import { synergyValue } from "../lib/finance";
import { PALETTE, bn, mult, musd, pct, usd } from "../lib/format";
import { Badge, Legend, Panel, Section, Segmented, Slider, Source, Stat, axisProps, gridProps, tooltipStyle } from "../components/ui";

type Sc = "bear" | "base" | "bull";

export default function Synergy({ d }: { d: Dashboard }) {
  const [pk, setPk] = useState<PerspectiveKey>("B_proxy_2018-05");
  const [sc, setSc] = useState<Sc>("base");
  const M = d.synergy.model, P = d.valuation[pk];
  const def = M.scenarios[sc];
  const [rr, setRr] = useState(def.run_rate), [real, setReal] = useState(1), [delay, setDelay] = useState(0), [icm, setIcm] = useState(def.ic_mult), [g, setG] = useState(def.g), [prem, setPrem] = useState(0);
  const pick = (s: Sc) => { setSc(s); const x = M.scenarios[s]; setRr(x.run_rate); setReal(1); setDelay(0); setIcm(x.ic_mult); setG(x.g); setPrem(0); };
  const v = useMemo(() => synergyValue({ runRate: rr, phase: M.scenarios[sc].phase, icPhase: M.ic_phase, icMult: icm, g, rate: P.model.wacc + prem, tax: P.tax,
    realization: real, delay, timing: M.timing[pk] }), [rr, sc, M, icm, g, P, prem, real, delay, pk]);
  const flows = v.flows.map((f, i) => ({ fy: `FY${M.fy[i]}`, synergies: f.syn, integration: -f.ic }));
  const standalonePs = P.outputs.equity_value_per_21cf_share, netPs = v.net / P.shares;
  const offers = d.synergy.justification.filter((j) => j.perspective === pk && j.metric === "consideration_per_share");
  const advisors = d.synergy.reference.filter((r) => r.perspective === "B_proxy_2018-05");
  return (
    <Section id="synergies" kicker="04 · Synergy valuation" title="How much were the cost synergies worth, and who kept them?"
      lede={<>Disney guided to roughly <b>$2.0bn of run-rate cost synergies</b>, starting in year one and fully realized by fiscal 2021 (Dec 2017 release and investor call; May 2018 proxy p.130).
        Revenue synergies and integration costs were never quantified at either date, so the phasing, integration costs and probabilities below are labelled estimates.</>}>
      <div className="flex flex-wrap items-center gap-4">
        <Segmented label="Perspective" value={pk} onChange={setPk} options={[{ value: "A_announcement_2017-12", label: "A · Dec 2017 (tax 36%)" }, { value: "B_proxy_2018-05", label: "B · May 2018 (tax 22%)" }]} />
        <Segmented label="Scenario" value={sc} onChange={pick} options={[{ value: "bear", label: "Bear" }, { value: "base", label: "Base (guidance)" }, { value: "bull", label: "Bull" }]} />
      </div>
      <p className="-mt-4 text-xs text-muted">{def.note}</p>
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Panel title="Assumptions" right={<Badge kind="estimate" />}>
          <div className="space-y-5">
            <Slider label="Run-rate cost synergies" value={rr} min={500} max={3000} step={50} onChange={setRr} fmt={(x) => bn(x, 2)} hint="Guidance: ~$2.0bn" />
            <Slider label="Realization" value={real} min={0} max={1.25} step={0.05} onChange={setReal} fmt={(x) => pct(x, 0)} />
            <Slider label="Delay" value={delay} min={0} max={2} step={1} onChange={setDelay} fmt={(x) => `${x} yr`} />
            <Slider label="Integration cost (× run-rate)" value={icm} min={0.5} max={2} step={0.05} onChange={setIcm} fmt={(x) => mult(x, 2)} hint="Disney later estimated ~$1.5bn of severance (0.75x)" />
            <Slider label="Synergy growth after run-rate" value={g} min={0} max={0.02} step={0.0025} onChange={setG} fmt={(x) => pct(x, 2)} />
            <Slider label="Discount-rate premium" value={prem} min={0} max={0.03} step={0.0025} onChange={setPrem} fmt={(x) => `+${pct(x, 2)}`} hint={`Base = standalone WACC ${pct(P.model.wacc, 2)}`} />
          </div>
        </Panel>
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            <Stat label="Gross PV (after tax)" value={bn(v.gross)} />
            <Stat label="PV integration costs" value={bn(-v.pvIntegration)} tone="neg" />
            <Stat label="Net synergy value" value={bn(v.net)} sub={`${usd(netPs)} per 21CF share`} />
            <Stat label="Standalone + synergies" value={usd(standalonePs + netPs)} sub="per share: the walk-away price" />
          </div>
          <Panel title="Pre-tax synergy and integration cash flows by Disney fiscal year">
            <Legend items={[{ label: "Cost synergies", color: PALETTE.s3 }, { label: "Integration costs", color: PALETTE.s2 }]} />
            <div className="mt-2 h-56">
              <ResponsiveContainer>
                <BarChart data={flows} stackOffset="sign" margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                  <CartesianGrid {...gridProps} />
                  <XAxis dataKey="fy" {...axisProps} />
                  <YAxis {...axisProps} width={52} tickFormatter={(x) => `${(x / 1000).toFixed(1)}bn`} />
                  <Tooltip {...tooltipStyle} formatter={(x: number, k: string) => [musd(x), k === "synergies" ? "Cost synergies" : "Integration costs"]} />
                  <ReferenceLine y={0} stroke={PALETTE.ink} />
                  <Bar dataKey="synergies" stackId="s" fill={PALETTE.s3} isAnimationActive={false} />
                  <Bar dataKey="integration" stackId="s" fill={PALETTE.s2} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-muted">Terminal value after FY2023: {bn(v.pvTv)} ({pct(v.pvTv / v.gross, 0)} of gross). Durability of the savings is the key judgement.</p>
          </Panel>
        </div>
      </div>

      <Panel title="Premium coverage: price vs standalone value plus synergies" note="Premium = price minus the Stage 3 standalone value per share (acquired business only). Coverage = net synergy value ÷ premium. Value created = standalone + net synergies − price.">
        <div className="grid gap-6 md:grid-cols-2">
          {offers.map((o) => {
            const premPs = (o.v ?? 0) - standalonePs, cover = premPs > 0 ? netPs / premPs : null, created = (standalonePs + netPs - (o.v ?? 0)) * P.shares;
            return (
              <div key={o.case} className="border-l-2 border-rule pl-4">
                <p className="text-sm font-semibold">{o.case}</p>
                <p className="mt-1 text-xs text-muted">Price {usd(o.v)} · standalone {usd(standalonePs)} · premium {usd(premPs)} per share ({bn(premPs * P.shares)})</p>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-sm bg-rule">
                  <div className="h-full" style={{ width: `${Math.min(100, (cover ?? 1) * 100)}%`, background: cover !== null && cover < 1 ? PALETTE.s2 : PALETTE.s3 }} />
                </div>
                <p className="num mt-2 text-sm">{cover === null ? "No premium over standalone: synergies not needed" : <>Synergies cover <b>{mult(cover, 2)}</b> the premium · value created for Disney <b className={created < 0 ? "text-s2" : ""}>{bn(created)}</b></>}</p>
              </div>);
          })}
        </div>
        {pk === "B_proxy_2018-05" && advisors.length > 0 && (
          <p className="mt-5 text-xs text-muted">Cross-check: Disney's advisors' disclosed ranges imply about {usd(Number(advisors.find((a) => a.case === "cost synergies")?.v))} per share for cost synergies
            (May 2018 proxy p.145) and a further {usd(Number(advisors.find((a) => a.case === "revenue synergies")?.v))} for revenue synergies, which were never quantified and are treated as an option (Section 06).</p>)}
      </Panel>
      <Source>synergy_assumptions.csv and synergy_outputs.csv (Stage 4A). Guidance quoted from DIS_8K_20171214_EX99_1, the 14 Dec 2017 investor-call transcript (Form 425) and the May 2018 proxy.</Source>
    </Section>
  );
}
