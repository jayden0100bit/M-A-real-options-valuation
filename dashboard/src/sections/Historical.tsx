import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard } from "../lib/data";
import { ENTITY, PALETTE, musd, pct } from "../lib/format";
import { Legend, Panel, Section, Segmented, Source, Table, axisProps, gridProps, tooltipStyle } from "../components/ui";

const METRICS = {
  revenue: { label: "Revenue", fmt: (v: number) => musd(v), ratio: false },
  ebitda: { label: "EBITDA (derived)", fmt: (v: number) => musd(v), ratio: false },
  ebitda_margin: { label: "EBITDA margin", fmt: (v: number) => pct(v), ratio: true },
  net_margin: { label: "Net margin", fmt: (v: number) => pct(v), ratio: true },
  fcf_cfo_less_capex: { label: "Free cash flow", fmt: (v: number) => musd(v), ratio: false },
  net_debt: { label: "Net debt", fmt: (v: number) => musd(v), ratio: false },
} as const;
type MetricKey = keyof typeof METRICS;
const FY = ["FY2015", "FY2016", "FY2017", "FY2018"];

export default function Historical({ d }: { d: Dashboard }) {
  const [metric, setMetric] = useState<MetricKey>("revenue");
  const [segEntity, setSegEntity] = useState<"DIS" | "21CF">("DIS");
  const series = useMemo(() => FY.map((fy) => {
    const row: Record<string, number | string | null> = { fy };
    for (const e of ["DIS", "21CF", "RemainCo"]) {
      const h = d.historical.find((x) => x.entity === e && x.fiscal_period === fy && x.metric === metric);
      row[e] = h?.value ?? null;
    }
    return row;
  }), [d, metric]);
  const segs = useMemo(() => {
    const names = Array.from(new Set(d.segments.filter((s) => s.entity === segEntity && s.metric === "segment_revenue" && s.segment !== "Total" && !s.segment.startsWith("Other")).map((s) => s.segment)));
    return { names, rows: FY.map((fy) => {
      const r: Record<string, number | string> = { fy };
      names.forEach((n) => { r[n] = d.segments.find((s) => s.entity === segEntity && s.fiscal_period === fy && s.segment === n && s.metric === "segment_revenue")?.value ?? 0; });
      return r;
    }) };
  }, [d, segEntity]);
  const segMargins = segs.names.map((n) => [n, ...FY.map((fy) => pct(d.segments.find((s) => s.entity === segEntity && s.fiscal_period === fy && s.segment === n && s.metric === "segment_margin")?.value ?? null))]);
  const M = METRICS[metric];
  const remainNote = metric === "revenue" || metric === "ebitda" || metric === "ebitda_margin";
  return (
    <Section id="historical" kicker="01 · Historical performance" title="Two very different businesses"
      lede="Disney earned a steady ~30% EBITDA margin with parks-led growth. 21CF earned 21–24%, with profit concentrated in cable networks and lower cash conversion because of content spending. RemainCo, the part Disney actually bought, earned ~20% on a pro forma basis that still carries all of 21CF's corporate costs.">
      <Panel title="Financial metrics by fiscal year" right={<Segmented label="Metric" value={metric} onChange={setMetric}
        options={(Object.keys(METRICS) as MetricKey[]).map((k) => ({ value: k, label: METRICS[k].label }))} />}
        note={<>Fiscal years differ: Disney ends on the Saturday nearest 30 Sep (FY2015 was 53 weeks); 21CF and RemainCo end on 30 Jun. EBITDA is derived
          (operating income before equity income, other items and interest, plus D&amp;A). RemainCo is pro forma (2018 proxy / March 2019 8-K/A){remainNote ? "" : " and has no cash-flow or net-debt history"}.</>}>
        <Legend items={["DIS", "21CF", "RemainCo"].map((e) => ({ label: ENTITY[e].label, color: ENTITY[e].color }))} />
        <div className="mt-3 h-72">
          <ResponsiveContainer>
            <LineChart data={series} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="fy" {...axisProps} />
              <YAxis {...axisProps} width={64} tickFormatter={(v) => (M.ratio ? pct(v, 0) : `${(v / 1000).toFixed(0)}bn`)} />
              <Tooltip {...tooltipStyle} formatter={(v: number, k: string) => [M.fmt(v), ENTITY[k]?.label ?? k]} />
              {["DIS", "21CF", "RemainCo"].map((e) => <Line key={e} dataKey={e} stroke={ENTITY[e].color} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: PALETTE.card }} connectNulls={false} isAnimationActive={false} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <Panel title="Segment revenue (USD m)" right={<Segmented label="Company" value={segEntity} onChange={setSegEntity}
          options={[{ value: "DIS", label: "Disney" }, { value: "21CF", label: "21CF consolidated" }]} />}
          note={segEntity === "21CF" ? "21CF segments describe the whole pre-separation company, not the acquired perimeter: Cable Network Programming mixes acquired networks (FX, Nat Geo, RSNs, Star) with New Fox networks (Fox News, FS1), and Television is almost all New Fox. Eliminations are excluded from the stacks." : "Disney segment revenue includes intersegment sales (Studio → Consumer Products)."}>
          <Legend items={segs.names.map((n, i) => ({ label: n, color: [PALETTE.s1, PALETTE.s2, PALETTE.s3, PALETTE.s4][i] }))} />
          <div className="mt-3 h-64">
            <ResponsiveContainer>
              <BarChart data={segs.rows} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="fy" {...axisProps} />
                <YAxis {...axisProps} width={56} tickFormatter={(v) => `${(v / 1000).toFixed(0)}bn`} />
                <Tooltip {...tooltipStyle} formatter={(v: number, k: string) => [musd(v), k]} />
                {segs.names.map((n, i) => <Bar key={n} dataKey={n} stackId="a" fill={[PALETTE.s1, PALETTE.s2, PALETTE.s3, PALETTE.s4][i]} stroke={PALETTE.card} strokeWidth={1} isAnimationActive={false} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title={segEntity === "DIS" ? "Segment operating margin" : "Segment OIBDA margin"}
          note={segEntity === "DIS" ? "After D&A." : "Before D&A; not comparable with Disney's segment margins."}>
          <Table head={["Segment", ...FY]} rows={segMargins} />
        </Panel>
      </div>
      <Source>financial_ratios.csv and segment_analysis.csv (Stage 2), built from 10-Ks FY2015–FY2018, the 2018 joint proxy and the March 2019 8-K/A.</Source>
    </Section>
  );
}
