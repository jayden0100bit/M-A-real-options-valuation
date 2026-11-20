import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard } from "../lib/data";
import { accretion } from "../lib/finance";
import { PALETTE, pct, usd } from "../lib/format";
import { Badge, Legend, Panel, Section, Segmented, Slider, Source, Stat, axisProps, gridProps, tooltipStyle } from "../components/ui";

export default function Accretion({ d }: { d: Dashboard }) {
  const A = d.accretion.params;
  const [structure, setStructure] = useState<"closing" | "original">("closing");
  const [rsn, setRsn] = useState<"sold" | "kept">("sold");
  const [real, setReal] = useState(1), [cash, setCash] = useState(A.cash / (A.cash + A.stock_val)), [rate, setRate] = useState(A.rate), [price, setPrice] = useState(A.vwap), [ppa, setPpa] = useState(1);
  const custom = Math.abs(cash - A.cash / (A.cash + A.stock_val)) > 1e-9 || Math.abs(price - A.vwap) > 1e-9;
  const r = useMemo(() => accretion(A, { realization: real, rate, ppaFactor: ppa, includeRsn: rsn === "kept", original: structure === "original",
    cashShare: custom ? cash : null, price: custom ? price : null }), [A, real, rate, ppa, rsn, structure, custom, cash, price]);
  const fys = Object.keys(r);
  const eps = fys.map((fy) => ({ fy, standalone: r[fy].standalone, adjusted: r[fy].adjusted, gaap: r[fy].gaap }));
  const acc = fys.map((fy) => ({ fy, adjusted: r[fy].accAdj, gaap: r[fy].accGaap }));
  const anchor = d.accretion.anchor.filter((a) => String(a.fiscal_year).startsWith("FY2018"));
  const a = (m: string) => Number(anchor.find((x) => x.metric === m)?.v);
  const sens = d.accretion.sensitivity_fy2021.filter((s) => s.metric === "accretion_adjusted");
  const groups = Array.from(new Set(sens.map((s) => s.case.split(" = ")[0].replace("sensitivity: ", ""))));
  const tornado = groups.map((g) => { const xs = sens.filter((s) => s.case.includes(g)).map((s) => s.v); return { g: g.replace(/_/g, " "), lo: Math.min(...xs), hi: Math.max(...xs) }; })
    .filter((t) => t.hi - t.lo > 1e-6).sort((x, y) => (y.hi - y.lo) - (x.hi - x.lo)).map((t) => ({ ...t, base: t.lo, span: t.hi - t.lo }));
  return (
    <Section id="eps" kicker="05 · Accretion / dilution" title="Did the deal raise Disney's earnings per share?"
      lede={<>Management said the deal would be accretive <i>before purchase accounting</i> in the second fiscal year after closing, i.e. FY2021. Disney's own pro forma for FY2018,
        on a GAAP basis without synergies, showed EPS falling from {usd(a("eps_disney"))} to {usd(a("eps_pro_forma"))} ({pct(a("accretion_dilution_pct"), 1)}). The forward model below rebuilds
        FY2020–22 from the proxy forecasts and the actual closing financing.</>}>
      <div className="flex flex-wrap gap-3">
        <Segmented label="Deal structure" value={structure} onChange={setStructure} options={[{ value: "closing", label: "Closing: $35.7bn cash + 306.8m shares" }, { value: "original", label: "Original: 515m shares, all stock" }]} />
        <Segmented label="RSNs" value={rsn} onChange={setRsn} options={[{ value: "sold", label: "RSNs sold (actual)" }, { value: "kept", label: "RSNs kept" }]} />
      </div>
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Panel title="Assumptions" right={<Badge kind="estimate" />}>
          <div className="space-y-5">
            <Slider label="Synergy realization" value={real} min={0} max={1.25} step={0.05} onChange={setReal} fmt={(x) => pct(x, 0)} />
            <Slider label="Cash share of consideration" value={cash} min={0} max={1} step={0.05} onChange={setCash} fmt={(x) => pct(x, 0)} hint={structure === "original" ? "Not used in the original all-stock structure" : "Closing: 50.5% (debt-financed)"} />
            <Slider label="Rate on new debt" value={rate} min={0.02} max={0.06} step={0.001} onChange={setRate} fmt={(x) => pct(x, 1)} hint="Disney's pro forma assumed 3.3%" />
            <Slider label="Disney price for the stock portion" value={price} min={90} max={130} step={1} onChange={setPrice} fmt={(x) => usd(x, 0)} hint="Closing average $114.18" />
            <Slider label="Purchase-accounting amortization" value={ppa} min={0.5} max={1.5} step={0.05} onChange={setPpa} fmt={(x) => pct(x, 0)} hint="Base $2.7bn a year (FY2019 10-K, ex-RSN)" />
          </div>
        </Panel>
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            {fys.map((fy) => <Stat key={fy} label={`${fy} adjusted`} value={pct(r[fy].accAdj, 1, true)} tone={r[fy].accAdj < 0 ? "neg" : undefined} sub={`GAAP basis ${pct(r[fy].accGaap, 1, true)}`} />)}
            <Stat label="Interest on new debt" value={usd(r[fys[0]].interest / 1000, 2) + "bn"} sub="pre-tax, a year" />
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            <Panel title="EPS: standalone vs pro forma">
              <Legend items={[{ label: "Disney standalone", color: PALETTE.ink }, { label: "Pro forma, adjusted", color: PALETTE.s1 }, { label: "Pro forma, GAAP basis", color: PALETTE.s2 }]} />
              <div className="mt-2 h-52">
                <ResponsiveContainer>
                  <LineChart data={eps} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="fy" {...axisProps} />
                    <YAxis {...axisProps} width={44} domain={["auto", "auto"]} tickFormatter={(x) => `$${x.toFixed(1)}`} />
                    <Tooltip {...tooltipStyle} formatter={(x: number, k: string) => [usd(x), k]} />
                    <Line dataKey="standalone" stroke={PALETTE.ink} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                    <Line dataKey="adjusted" stroke={PALETTE.s1} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                    <Line dataKey="gaap" stroke={PALETTE.s2} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="Accretion / (dilution)">
              <Legend items={[{ label: "Adjusted (ex PPA, ex integration)", color: PALETTE.s1 }, { label: "GAAP basis", color: PALETTE.s2 }]} />
              <div className="mt-2 h-52">
                <ResponsiveContainer>
                  <BarChart data={acc} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="fy" {...axisProps} />
                    <YAxis {...axisProps} width={44} tickFormatter={(x) => pct(x, 0)} />
                    <Tooltip {...tooltipStyle} formatter={(x: number, k: string) => [pct(x, 1, true), k]} />
                    <ReferenceLine y={0} stroke={PALETTE.ink} />
                    <Bar dataKey="adjusted" fill={PALETTE.s1} isAnimationActive={false} />
                    <Bar dataKey="gaap" fill={PALETTE.s2} isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>
        </div>
      </div>
      <Panel title="What moves FY2021 accretion most (adjusted EPS, one input at a time)" note="Ranges from the Stage 4 sensitivity runs: synergy realization 0–125%, cash share 0–100%, debt rate 2–6%, Disney price $90–130. Purchase accounting and integration costs only affect the GAAP basis.">
        <div className="space-y-3">
          {tornado.map((t) => {
            const lo = -0.24, hi = 0.22, x = (v: number) => ((v - lo) / (hi - lo)) * 100;
            return (
              <div key={t.g} className="grid grid-cols-[150px_1fr] items-center gap-3 text-xs md:grid-cols-[220px_1fr]">
                <span className="text-muted">{t.g}</span>
                <div className="relative h-6 rounded-sm bg-paper">
                  <div className="absolute top-0 h-full w-px bg-ink" style={{ left: `${x(0)}%` }} />
                  <div className="absolute top-1 h-4 rounded-[2px] bg-s1/80" style={{ left: `${x(t.lo)}%`, width: `${Math.max(0.5, x(t.hi) - x(t.lo))}%` }} />
                  <span className="num absolute top-1 -translate-x-full pr-1 text-[11px]" style={{ left: `${x(t.lo)}%` }}>{pct(t.lo, 1, true)}</span>
                  <span className="num absolute top-1 pl-1 text-[11px]" style={{ left: `${x(t.hi)}%` }}>{pct(t.hi, 1, true)}</span>
                </div>
              </div>);
          })}
        </div>
      </Panel>
      <Source>accretion_dilution_inputs.csv and accretion_dilution_outputs.csv (Stage 4B). Disney standalone earnings come from the "Disney street forecasts" in the May 2018 proxy (analyst-based, not management EPS guidance). The model holds interest, NCI and share count flat, ignores Hulu consolidation and pre-dates COVID-19.</Source>
    </Section>
  );
}
