import type { Dashboard } from "../lib/data";
import { bn, pct, usd } from "../lib/format";
import { Panel, Source, Stat } from "../components/ui";

export default function Overview({ d }: { d: Dashboard }) {
  const B = d.valuation["B_proxy_2018-05"], A = d.valuation["A_announcement_2017-12"];
  const synB = d.synergy.values.find((v) => v.perspective === "B_proxy_2018-05" && v.case === "base" && v.metric === "net_synergy_value_per_21cf_share")!.v;
  const p38 = Number(d.montecarlo.summary.find((r) => r.metric === "value_created_vs_amended_38")!.prob_positive);
  const amended = d.deal.stages[1];
  return (
    <section id="overview" className="scroll-mt-24 pb-14 pt-12 md:pb-20 md:pt-16">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brass">Case study · announced December 2017 · closed March 2019</p>
      <h1 className="mt-4 max-w-4xl font-serif text-4xl font-semibold leading-[1.1] text-ink md:text-[3.4rem]">
        Did Disney overpay for 21st Century Fox?
      </h1>
      <p className="mt-6 max-w-3xl text-[16px] leading-relaxed text-muted">
        A full valuation of the business Disney acquired: the studios, FX, National Geographic, Star India, the regional sports networks and
        stakes in Hulu and Sky. Fox News, the broadcast network and stations went to Fox Corporation instead. Every figure is traced to SEC
        filings or dated market data and checked by {d.meta.checks_total.toLocaleString("en-US")} automated validation tests.
      </p>

      <div className="mt-12 grid grid-cols-2 gap-x-6 gap-y-8 md:grid-cols-4">
        <Stat label="Price paid (amended offer)" value={usd(amended.per_share)} sub={`per 21CF share · equity ${bn(amended.equity_headline)} · EV ${bn(amended.ev_headline)}`} />
        <Stat label="Standalone value (DCF)" value={usd(B.outputs.equity_value_per_21cf_share)} sub="May 2018, Disney's own forecasts for the acquired business" />
        <Stat label="+ Cost synergies (net)" value={usd(synB)} sub="per share, ~$2.0bn run-rate guidance, after tax and integration costs" />
        <Stat label="P(value created) at $38" value={pct(p38, 0)} sub="20,000 Monte Carlo draws, before the revenue-synergy option" />
      </div>

      <div className="mt-12 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <Panel title="The answer in one line">
          <p className="font-serif text-xl leading-snug text-ink md:text-2xl">
            At the original all-stock price Disney kept almost all the synergy value. After Comcast's counter-bid, the amended
            $38 offer paid away essentially all of it.
          </p>
          <p className="mt-4 text-sm leading-relaxed text-muted">
            The original offer was worth {usd(d.deal.stages[0].per_share)} per share against a standalone value of {usd(A.outputs.equity_value_per_21cf_share)} (Dec 2017).
            At {usd(amended.per_share)}, standalone value plus base cost synergies ({usd(B.outputs.equity_value_per_21cf_share + synB)}) roughly equals the price.
            The deal case then rests on the option value of Fox's content for Disney's own streaming services.
          </p>
        </Panel>
        <Panel title="Deal timeline">
          <ol className="relative space-y-4 border-l border-rule pl-5">
            {d.timeline.map((e) => (
              <li key={e.date + e.title}>
                <span className="absolute -left-[5px] mt-1.5 h-[9px] w-[9px] rounded-full border-2 border-navy bg-card" />
                <p className="num font-mono text-[11px] text-brass">{e.date}</p>
                <p className="text-sm font-semibold text-ink">{e.title}</p>
                <p className="text-xs leading-relaxed text-muted">{e.detail}</p>
              </li>
            ))}
          </ol>
        </Panel>
      </div>
      <div className="mt-6"><Source>transaction_assumptions.csv, valuation_outputs.csv, synergy_outputs.csv, monte_carlo_summary.csv (each figure cites its SEC filing and page in the repository).</Source></div>
    </section>
  );
}
