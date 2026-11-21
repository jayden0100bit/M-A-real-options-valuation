import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard } from "../lib/data";
import { PALETTE, bn, mult, musd, pct, usd } from "../lib/format";
import { Details, Legend, Num, Panel, Reveal, Section, Segmented, Source, Stat, Table, Term, anim, axisProps, gridProps, tooltipStyle, useInView } from "../components/ui";
import HistoricalPanels from "./Historical";

const fmtDate = (s: string) => {
  const [y, m, d] = s.split("-").map(Number);
  const mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][(m || 1) - 1];
  return d ? `${d} ${mon} ${y}` : `${mon} ${y}`;
};

export default function DealOverview({ d }: { d: Dashboard }) {
  const B = d.valuation["B_proxy_2018-05"], A = d.valuation["A_announcement_2017-12"];
  const synB = d.synergy.values.find((v) => v.perspective === "B_proxy_2018-05" && v.case === "base" && v.metric === "net_synergy_value_per_21cf_share")!.v;
  const optPs = d.options.outputs.find((o) => o.section === "Option value" && o.metric === "option_value_per_21cf_share")!.v;
  const p38 = Number(d.montecarlo.summary.find((r) => r.metric === "value_created_vs_amended_38")!.prob_positive);
  const [orig, amended] = d.deal.stages;
  const { ref: heroRef, inView: heroIn } = useInView<HTMLDivElement>({ threshold: 0.2 });
  const worth = B.outputs.equity_value_per_21cf_share + synB;

  return (
    <>
      {/* ------------------------------------------------------------ hero */}
      <div id="top" className="relative overflow-hidden bg-ink text-paper">
        <div className="hero-grid pointer-events-none absolute inset-0" />
        <div ref={heroRef} className="relative mx-auto grid max-w-[1180px] gap-12 px-5 pb-16 pt-14 md:px-8 md:pb-24 md:pt-20 lg:grid-cols-[1.25fr_1fr] lg:items-center">
          <div className={`reveal ${heroIn ? "is-in" : ""}`}>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brass-light">Interactive M&amp;A case study · announced Dec 2017 · closed Mar 2019</p>
            <h1 className="mt-5 font-serif text-[2.6rem] font-semibold leading-[1.05] md:text-[3.8rem]">Did Disney overpay for 21st&nbsp;Century&nbsp;Fox?</h1>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-paper/75">
              Disney bought most of Fox's entertainment business, then raised its offer to beat Comcast. This case study values what Disney bought,
              what the deal could save, and what it paid. Every number comes from SEC filings and dated market data, and you can change the assumptions yourself.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#valuation" className="rounded-[3px] bg-paper px-5 py-2.5 text-sm font-semibold text-ink transition-all hover:-translate-y-0.5 hover:shadow-lg">Explore the valuation</a>
              <a href="#verdict" className="rounded-[3px] border border-paper/30 px-5 py-2.5 text-sm font-semibold text-paper transition-colors hover:border-paper/70">Jump to the verdict →</a>
            </div>
          </div>

          {/* worth vs paid: the whole case in one picture */}
          <div className={`reveal ${heroIn ? "is-in" : ""} rounded-[4px] border border-paper/15 bg-paper/[0.04] p-6 backdrop-blur-sm`} style={{ transitionDelay: "150ms" }}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-paper/60">Per 21CF share · May 2018 view</p>
            <WorthVsPaid standalone={B.outputs.equity_value_per_21cf_share} syn={synB} option={optPs} paid={amended.per_share} play={heroIn} />
            <p className="mt-5 border-t border-paper/15 pt-4 text-sm leading-relaxed text-paper/80">
              Standalone value plus cost savings comes to <b className="text-paper"><Num v={heroIn ? worth : 0} fmt={usd} duration={1200} start={0} /></b>, about the same as the{" "}
              <b className="text-paper">{usd(amended.per_share)}</b> Disney paid.
            </p>
          </div>
        </div>
        <div className="relative border-t border-paper/10 bg-ink-2/60">
          <div className="mx-auto grid max-w-[1180px] grid-cols-2 gap-x-6 gap-y-6 px-5 py-8 md:grid-cols-4 md:px-8">
            {[
              { l: "Price paid", v: amended.per_share, f: usd, s: `per share · ${bn(amended.equity_headline)} equity` },
              { l: "Standalone value", v: B.outputs.equity_value_per_21cf_share, f: usd, s: "DCF on Disney's own forecasts" },
              { l: "+ Net cost savings", v: synB, f: usd, s: "per share, after tax and integration costs" },
              { l: "Chance of creating value", v: p38, f: (x: number) => pct(x, 0), s: "at $38, from 20,000 simulations" },
            ].map((s, i) => (
              <div key={s.l} className={`reveal ${heroIn ? "is-in" : ""} border-l border-brass/60 pl-4`} style={{ transitionDelay: `${250 + i * 80}ms` }}>
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-paper/55">{s.l}</p>
                <p className="mt-1.5 font-serif text-[1.9rem] leading-none"><Num v={heroIn ? s.v : 0} fmt={s.f} duration={1100} start={0} /></p>
                <p className="mt-2 text-xs leading-snug text-paper/55">{s.s}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------ section 01 */}
      <div className="mx-auto max-w-[1180px] px-5 md:px-8">
        <Section id="deal" index="01" kicker="Deal overview" title="What Disney bought, why, and for how much"
          lede={<>The deal was not for all of Fox. Disney bought the entertainment assets; the news and broadcast businesses were spun off as a new company first.</>}
          takeaway={<>A bidding war with Comcast lifted the price from {usd(orig.per_share)} to {usd(amended.per_share)} per share, a {pct(amended.premium, 0)} premium to the <Term k="unaffected">unaffected price</Term>.</>}>

          <div className="grid gap-6 lg:grid-cols-3">
            <Reveal className="lg:col-span-2">
              <Panel title="The perimeter" className="h-full">
                <div className="grid gap-6 sm:grid-cols-2">
                  <div>
                    <p className="flex items-center gap-2 text-sm font-semibold text-ink"><span className="h-2.5 w-2.5 rounded-full bg-s1" />Disney bought</p>
                    <ul className="mt-3 space-y-2 text-sm text-ink">
                      {["The film and TV studios", "FX and National Geographic", "Star India", "The regional sports networks (sold in 2019)", "Stakes in Hulu and Sky (Sky sold in 2018)"].map((x) => (
                        <li key={x} className="flex gap-2"><span className="text-s1">+</span>{x}</li>))}
                    </ul>
                  </div>
                  <div>
                    <p className="flex items-center gap-2 text-sm font-semibold text-ink"><span className="h-2.5 w-2.5 rounded-full bg-muted/50" />Went to Fox Corporation</p>
                    <ul className="mt-3 space-y-2 text-sm text-muted">
                      {["Fox News", "The Fox broadcast network", "The Fox TV stations"].map((x) => <li key={x} className="flex gap-2"><span>–</span>{x}</li>)}
                    </ul>
                    <p className="mt-4 text-xs leading-relaxed text-muted">21CF shareholders kept shares in the new Fox Corporation, so the price paid by Disney is for the acquired business only ("RemainCo").</p>
                  </div>
                </div>
              </Panel>
            </Reveal>
            <Reveal delay={100}>
              <Panel title="Why Disney wanted it" className="h-full">
                <ol className="space-y-4 text-sm">
                  <li><p className="font-semibold text-ink">1 · Cost savings</p><p className="mt-1 text-muted">Disney guided to about <b className="text-ink">$2.0bn a year</b> of cost <Term k="synergies">synergies</Term>, fully achieved by fiscal 2021.</p></li>
                  <li><p className="font-semibold text-ink">2 · Content for streaming</p><p className="mt-1 text-muted">Fox's studios and networks could feed Disney's own streaming services. Disney never put a number on this, so Section 04 values it as an option.</p></li>
                </ol>
              </Panel>
            </Reveal>
          </div>

          <Reveal><PriceStages d={d} /></Reveal>
          <Reveal><Timeline d={d} /></Reveal>

          <Details summary="Why the headline deal values differ: equity, enterprise value and the accounting price">
            <HeadlineConcepts d={d} />
          </Details>
          <Details summary="Background: the two businesses before the deal (historical financials and segments)">
            <HistoricalPanels d={d} />
          </Details>
          <Source>transaction_assumptions.csv, valuation_outputs.csv, synergy_outputs.csv, monte_carlo_summary.csv. Original offer per share {usd(orig.per_share)} against a Dec 2017 standalone value of {usd(A.outputs.equity_value_per_21cf_share)}.</Source>
        </Section>
      </div>
    </>
  );
}

function WorthVsPaid({ standalone, syn, option, paid, play }: { standalone: number; syn: number; option: number; paid: number; play: boolean }) {
  const max = 42, w = (x: number) => `${play ? (x / max) * 100 : 0}%`;
  const bar = "h-full transition-[width] duration-[1200ms] ease-out";
  return (
    <div className="mt-5 space-y-5">
      <div>
        <div className="flex justify-between text-xs text-paper/70"><span>What it was worth to Disney</span><span className="num">{usd(standalone + syn)} <span className="text-paper/45">+ {usd(option)} option</span></span></div>
        <div className="mt-2 flex h-9 overflow-hidden rounded-[2px] bg-paper/[0.06]">
          <div className={`${bar} bg-s1`} style={{ width: w(standalone) }} title={`Standalone value ${usd(standalone)}`} />
          <div className={`${bar} bg-s3 delay-300`} style={{ width: w(syn) }} title={`Net cost synergies ${usd(syn)}`} />
          <div className={`${bar} delay-500 border border-dashed border-brass-light/80 bg-brass-light/20`} style={{ width: w(option) }} title={`Revenue-synergy option ${usd(option)}`} />
        </div>
      </div>
      <div>
        <div className="flex justify-between text-xs text-paper/70"><span>What Disney paid (amended offer)</span><span className="num">{usd(paid)}</span></div>
        <div className="mt-2 h-9 overflow-hidden rounded-[2px] bg-paper/[0.06]"><div className={`${bar} bg-s2`} style={{ width: w(paid) }} /></div>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-paper/60">
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 bg-s1" />Standalone</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 bg-s3" />Cost savings</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 border border-dashed border-brass-light" />Streaming option (estimate)</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 bg-s2" />Price</span>
      </div>
    </div>
  );
}

function PriceStages({ d }: { d: Dashboard }) {
  const [i, setI] = useState(1);
  const s = d.deal.stages[i], unaff = d.deal.unaffected_price;
  const chart = d.deal.stages.map((x, k) => ({ name: x.stage.split(" (")[0], when: x.stage.match(/\((.*)\)/)?.[1] ?? "", v: x.per_share, k }));
  const cashShare = s.cash / (s.cash + s.stock);
  const blurb = [
    "All in Disney shares: 0.2745 Disney shares for each 21CF share.",
    "After Comcast's counter-bid, Disney raised the price and paid about half in cash.",
    "Completed on the amended terms on 20 March 2019, after Fox Corporation was spun off.",
  ][i];
  return (
    <Panel title="The price, step by step" right={<Segmented label="Deal stage" value={String(i)} onChange={(v) => setI(Number(v))} options={d.deal.stages.map((x, k) => ({ value: String(k), label: x.stage.split(" (")[0] }))} />}>
      <div className="grid gap-8 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <p className="text-sm text-muted">{blurb}</p>
          <div className="mt-6 grid grid-cols-2 gap-6">
            <Stat big label="Per 21CF share" value={<Num v={s.per_share} fmt={usd} />} />
            <Stat big label={<>Premium to <Term k="unaffected">unaffected</Term></>} value={<Num v={s.premium} fmt={(x) => pct(x, 0, true)} />} sub={`vs ${usd(unaff)} on 3 Nov 2017`} />
            <Stat label={<Term k="equity">Equity value</Term>} value={<Num v={s.equity_headline} fmt={(x) => bn(x)} />} sub="headline" />
            <Stat label={<Term k="ev">Enterprise value</Term>} value={<Num v={s.ev_headline} fmt={(x) => bn(x)} />} sub={<>implied <Num v={s.implied_ev_ebitda} fmt={(x) => mult(x)} /> <Term k="ebitda">EBITDA</Term></>} />
          </div>
          <div className="mt-6">
            <div className="flex justify-between text-xs text-muted"><span>Paid in cash <b className="num text-ink">{bn(s.cash)}</b></span><span>in Disney shares <b className="num text-ink">{bn(s.stock)}</b></span></div>
            <div className="mt-1.5 flex h-2.5 overflow-hidden rounded-full bg-s1/25">
              <div className="h-full bg-navy transition-[width] duration-500 ease-out" style={{ width: `${cashShare * 100}%` }} />
            </div>
          </div>
        </div>
        <div>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={chart} margin={{ top: 22, right: 8, left: 0, bottom: 0 }} onClick={(e) => { const k = (e?.activePayload?.[0]?.payload as { k?: number })?.k; if (k != null) setI(k); }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="name" {...axisProps} />
                <YAxis {...axisProps} width={40} domain={[0, 45]} tickFormatter={(v) => `$${v}`} />
                <Tooltip {...tooltipStyle} formatter={(v: number) => [usd(v), "Per 21CF share"]} labelFormatter={(l, p) => `${l} · ${p?.[0]?.payload?.when ?? ""}`} />
                <ReferenceLine y={unaff} stroke={PALETTE.muted} strokeDasharray="4 4" />
                <Bar dataKey="v" radius={[2, 2, 0, 0]} cursor="pointer" {...anim}>
                  {chart.map((c) => <Cell key={c.k} fill={c.k === i ? PALETTE.navy : "#c9d3e0"} />)}
                  <LabelList dataKey="v" position="top" formatter={(v: number) => usd(v)} style={{ fill: PALETTE.ink, fontSize: 12 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-center text-[11px] text-muted">Dashed line: unaffected price {usd(unaff)} · click a bar to select a stage</p>
        </div>
      </div>
    </Panel>
  );
}

function Timeline({ d }: { d: Dashboard }) {
  const T = d.timeline;
  const [i, setI] = useState(Math.max(0, T.findIndex((t) => t.title.toLowerCase().includes("amended"))));
  const e = T[i];
  return (
    <Panel title="Timeline" right={<span className="text-xs text-muted">{i + 1} / {T.length}</span>}>
      <div className="overflow-x-auto pb-2">
        <ol className="relative flex min-w-[720px] justify-between">
          <span className="absolute left-0 right-0 top-[7px] h-px bg-rule" />
          <span className="absolute left-0 top-[7px] h-px bg-navy transition-[width] duration-500 ease-out" style={{ width: `${(i / (T.length - 1)) * 100}%` }} />
          {T.map((t, k) => (
            <li key={t.date + t.title} className="relative flex w-0 flex-1 flex-col items-center first:items-start last:items-end">
              <button onClick={() => setI(k)} onMouseEnter={() => setI(k)} aria-label={`${t.date}: ${t.title}`} aria-current={k === i}
                className={`relative z-10 h-[15px] w-[15px] rounded-full border-2 transition-all duration-300 ${k <= i ? "border-navy" : "border-rule"} ${k === i ? "scale-125 bg-navy" : "bg-card hover:border-navy"}`} />
              <span className={`mt-2 whitespace-nowrap text-[11px] transition-colors ${k === i ? "font-semibold text-ink" : "text-muted"}`}>{fmtDate(t.date)}</span>
            </li>
          ))}
        </ol>
      </div>
      <div key={i} className="mt-4 grid gap-2 rounded-[3px] bg-paper p-4 [animation:open-down_.35s_ease-out] md:grid-cols-[200px_1fr]">
        <div>
          <p className="num font-mono text-[11px] text-brass">{fmtDate(e.date)}</p>
          <p className="font-serif text-lg font-semibold text-ink">{e.title}</p>
        </div>
        <div>
          <p className="text-sm leading-relaxed text-ink">{e.detail}</p>
          <p className="mt-1 text-[11px] text-muted">Source: {e.source}</p>
        </div>
      </div>
      <div className="mt-3 flex justify-between">
        <button disabled={i === 0} onClick={() => setI(i - 1)} className="text-xs font-medium text-navy disabled:text-rule">← Previous</button>
        <button disabled={i === T.length - 1} onClick={() => setI(i + 1)} className="text-xs font-medium text-navy disabled:text-rule">Next →</button>
      </div>
    </Panel>
  );
}

function HeadlineConcepts({ d }: { d: Dashboard }) {
  const concept = d.deal.stages.map((s) => ({ stage: s.stage.split(" (")[0], equity: s.equity_headline, ev: s.ev_headline }));
  const unaff = d.deal.unaffected_price;
  return (
    <>
      <p className="max-w-3xl text-sm leading-relaxed text-muted">The headline figures mix concepts. The original offer's "$66.1bn" is equity plus assumed net debt. The closing "~$71bn" is market-implied equity at Disney's $114.18 average price, while the ASC 805 purchase price of {bn(d.deal.accounting_purchase_price)} values the same shares at $110.00.</p>
      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Panel title="Headline value by deal stage (USD bn)" note="The headline enterprise value is the parties' 'transaction value' (equity plus net debt assumed). At closing it roughly equals equity because cash acquired (~$19.8bn, including the Sky sale proceeds) offsets debt assumed (~$19.2bn).">
          <Legend items={[{ label: "Equity value (headline)", color: PALETTE.s1 }, { label: "Enterprise / transaction value", color: PALETTE.s2 }]} />
          <div className="mt-2 h-56">
            <ResponsiveContainer>
              <BarChart data={concept} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barGap={4}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="stage" {...axisProps} />
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
      <Panel title={<><Term k="ppa">Purchase price allocation</Term> (FY2019 10-K)</>} note="Disney's updated ASC 805 allocation at 20 Mar 2019 (USD m). Liabilities and NCI are negative.">
        <Table head={["Item", "USD m"]} rows={d.deal.ppa.map((r) => [r.item.replace("PPA updated allocation (FY2019 10-K): ", ""), musd(r.value)])} />
      </Panel>
    </>
  );
}
