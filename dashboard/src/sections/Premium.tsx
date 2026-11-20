import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard, PerspectiveKey } from "../lib/data";
import { PALETTE, bn, mult, musd, pct, usd } from "../lib/format";
import { Legend, Panel, Section, Segmented, Source, Table, axisProps, gridProps, tooltipStyle } from "../components/ui";

export default function Premium({ d }: { d: Dashboard }) {
  const [pk, setPk] = useState<PerspectiveKey>("B_proxy_2018-05");
  const P = d.valuation[pk];
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
  const concept = d.deal.stages.map((s) => ({ stage: s.stage.replace(" (", "\n("), equity: s.equity_headline, ev: s.ev_headline }));
  const unaff = d.deal.unaffected_price;
  return (
    <Section id="premium" kicker="03 · Price, premium and bridge" title="Equity value, enterprise value and the accounting price are different numbers"
      lede={<>The headline figures mix concepts. The original offer's "$66.1bn" is equity plus assumed net debt. The closing "~$71bn" is market-implied equity at Disney's $114.18 average price, while the ASC 805 purchase price of {bn(d.deal.accounting_purchase_price)} values the same shares at $110.00.</>}>
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Panel title="Headline value by deal stage (USD bn)" note="The headline enterprise value is the parties' 'transaction value' (equity plus net debt assumed). At closing it roughly equals equity because cash acquired (~$19.8bn, including the Sky sale proceeds) offsets debt assumed (~$19.2bn).">
          <Legend items={[{ label: "Equity value (headline)", color: PALETTE.s1 }, { label: "Enterprise / transaction value", color: PALETTE.s2 }]} />
          <div className="mt-2 h-64">
            <ResponsiveContainer>
              <BarChart data={concept} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barGap={4}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="stage" {...axisProps} interval={0} tick={{ fill: PALETTE.muted, fontSize: 11 }} />
                <YAxis {...axisProps} width={44} tickFormatter={(v) => `${(v / 1000).toFixed(0)}`} />
                <Tooltip {...tooltipStyle} formatter={(v: number, k: string) => [bn(v), k === "equity" ? "Equity value" : "Enterprise value"]} />
                <Bar dataKey="equity" fill={PALETTE.s1} radius={[2, 2, 0, 0]} isAnimationActive={false} />
                <Bar dataKey="ev" fill={PALETTE.s2} radius={[2, 2, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Per 21CF share and premium" note={`Premium vs the unaffected 21CF price of ${usd(unaff)} (3 Nov 2017, before press reports). It understates what holders received, because they also kept New Fox shares. Including 1/3 of a Fox Corporation share, the closing package was worth ${usd(d.deal.package_value_closing)}: a ${pct(d.deal.package_premium_closing, 0)} nominal premium.`}>
          <Table head={["Stage", "Per share", "Premium", "Cash", "EV / EBITDA"]} rows={d.deal.stages.map((s) => [s.stage, usd(s.per_share), pct(s.premium, 1, true), bn(s.cash), mult(s.implied_ev_ebitda)])} />
          <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
            <div><p className="text-[11px] uppercase tracking-wider text-muted">Market-implied (closing)</p><p className="num font-serif text-xl">{bn(d.deal.market_implied_closing)}</p></div>
            <div><p className="text-[11px] uppercase tracking-wider text-muted">ASC 805 purchase price</p><p className="num font-serif text-xl">{bn(d.deal.accounting_purchase_price)}</p></div>
          </div>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        <Panel title="Enterprise value to equity value (standalone DCF)" right={<Segmented label="Perspective" value={pk} onChange={setPk}
          options={[{ value: "A_announcement_2017-12", label: "A · Dec 2017" }, { value: "B_proxy_2018-05", label: "B · May 2018" }]} />}
          note="The Sky stake is valued at offer prices (A: 21CF's £10.75; B: Comcast's £12.50), not book. Hulu and other investments are at book. The regional sports networks are inside EV (they were part of the deal perimeter on both dates) and are not added twice. The New Fox dividend cash and the matching transaction-tax payable are excluded together.">
          <div className="h-72">
            <ResponsiveContainer>
              <BarChart data={wf} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="name" {...axisProps} interval={0} angle={-35} textAnchor="end" height={56} tick={{ fill: PALETTE.muted, fontSize: 10 }} />
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
        <Panel title="Purchase price allocation (FY2019 10-K)" note="Disney's updated ASC 805 allocation at 20 Mar 2019 (USD m). Liabilities and NCI are negative.">
          <Table head={["Item", "USD m"]} rows={d.deal.ppa.map((r) => [r.item.replace("PPA updated allocation (FY2019 10-K): ", ""), musd(r.value)])} />
        </Panel>
      </div>
      <Source>transaction_assumptions.csv (each term quoted from the 8-Ks, proxies and 10-K with page references) and valuation_outputs.csv.</Source>
    </Section>
  );
}
