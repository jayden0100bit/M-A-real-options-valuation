import type { ReactNode } from "react";
import type { Dashboard } from "../lib/data";
import { bn, mult, pct, usd } from "../lib/format";
import { Badge, Details, Panel, Reveal, Section, Table, Term, useInView } from "../components/ui";

const DOCS = [
  ["Data collection", "docs/data_collection_report.md"], ["Historical analysis", "docs/historical_analysis_report.md"],
  ["Valuation methodology", "docs/valuation_methodology.md"], ["Valuation report", "docs/valuation_report.md"],
  ["Synergy methodology", "docs/synergy_methodology.md"], ["Accretion / dilution", "docs/accretion_dilution_methodology.md"],
  ["Stage 4 report", "docs/stage4_analysis_report.md"], ["Real options", "docs/real_options_methodology.md"], ["Monte Carlo report", "docs/monte_carlo_report.md"],
];

export default function Conclusion({ d }: { d: Dashboard }) {
  const A = d.valuation["A_announcement_2017-12"], B = d.valuation["B_proxy_2018-05"];
  const J = (pk: string, c: string, m: string) => d.synergy.justification.find((j) => j.perspective === pk && j.case.startsWith(c) && j.metric === m)!.v!;
  const mc = (m: string) => Number(d.montecarlo.summary.find((r) => r.metric === m)!.prob_positive);
  const deal = (c: string) => d.options.outputs.find((o) => o.section === "Deal justification with option" && o.case.startsWith(c))!.v;
  const inp = (p: string) => d.options.inputs.find((x) => x.parameter === p)!.value;
  const base = d.synergy.model.scenarios.base;
  const ad = d.accretion.params;

  const verdicts: { label: string; sub: string; v: number; p?: number; tone: "pos" | "neg" | "muted" }[] = [
    { label: "Original offer", sub: "May 2018 value of the all-stock deal", v: J("B_proxy_2018-05", "original", "value_created_for_disney_base"), p: mc("value_created_vs_original_at_2018-05-30"), tone: "pos" },
    { label: "$38, cash flows only", sub: "standalone + cost savings − price", v: deal("without expansion option"), p: mc("value_created_vs_amended_38"), tone: "neg" },
    { label: "$38, with streaming option", sub: "adds the real-option value", v: deal("with expansion option"), p: mc("value_created_incl_option_vs_amended_38"), tone: "pos" },
    { label: "$38, streaming counted as certain", sub: "advisors' static view: ignores the investment needed", v: deal("with revenue synergies counted as certain"), tone: "muted" },
  ];
  const max = Math.max(...verdicts.map((x) => Math.abs(x.v)));
  const { ref, inView } = useInView<HTMLDivElement>();
  const forms = d.sources.filter((s) => !String(s.form).startsWith("XBRL") && s.form !== "external market data");
  const market = d.sources.filter((s) => s.form === "external market data");

  return (
    <Section id="verdict" index="05" kicker="Conclusion & methodology" title="So, was it worth it?"
      lede={<>At the original all-stock price, clearly yes. After Comcast's counter-bid, the amended {usd(d.deal.stages[1].per_share)} offer paid away essentially all of the cost-synergy value.
        Whether the deal created value then rests on the streaming upside.</>}
      takeaway={<>At $38 the deal was roughly a coin flip on the information available in 2018: {pct(mc("value_created_vs_amended_38"), 0)} without the streaming option, {pct(mc("value_created_incl_option_vs_amended_38"), 0)} with it.</>}>

      <Reveal>
        <Panel title={<>Value created for Disney under each view (May 2018 forecasts)</>}>
          <div ref={ref} className="space-y-5">
            {verdicts.map((x, i) => {
              const w = inView ? (Math.abs(x.v) / max) * 50 : 0;
              const color = x.tone === "muted" ? "bg-muted/35" : x.v < 0 ? "bg-s2" : "bg-s3";
              return (
                <div key={x.label} className="grid items-center gap-3 md:grid-cols-[240px_1fr_120px]">
                  <div><p className="text-sm font-semibold text-ink">{x.label}</p><p className="text-[11px] text-muted">{x.sub}</p></div>
                  <div className="relative h-8 rounded-[2px] bg-paper">
                    <span className="absolute inset-y-0 left-1/2 w-px bg-ink/60" />
                    <span className={`absolute inset-y-1.5 rounded-[2px] ${color} transition-all duration-1000 ease-out`}
                      style={{ transitionDelay: `${i * 120}ms`, width: `${Math.max(w, inView ? 0.6 : 0)}%`, left: x.v < 0 ? `${50 - w}%` : "50%" }} />
                  </div>
                  <div className="text-right">
                    <p className={`num font-serif text-xl ${x.tone === "muted" ? "text-muted" : x.v < 0 ? "text-s2" : "text-pos"}`}>{x.v > 0 ? "+" : ""}{bn(x.v)}</p>
                    {x.p != null && <p className="text-[11px] text-muted">{pct(x.p, 1)} chance &gt; 0</p>}
                  </div>
                </div>);
            })}
          </div>
          <p className="mt-5 border-t border-rule pt-3 text-xs text-muted"><Term k="valuecreated">Value created</Term> = standalone value + net cost synergies (+ option) − price. Chances from the Stage 5B Monte Carlo (20,000 simulations). Deterministic values are the Stage 4–5 base cases.</p>
        </Panel>
      </Reveal>

      <Reveal>
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.14em] text-brass">What you have to believe for the $38 price to work</p>
        <div className="grid gap-6 md:grid-cols-3">
          {([
            ["The savings arrive in full", <>At $38 the base-case cost savings cover {mult(J("B_proxy_2018-05", "amended", "synergy_coverage_of_premium_base"), 2)} of the premium. Any shortfall means Disney overpaid.</>],
            ["Disney's forecasts hold", <>Revenue growth is the single biggest swing factor in the simulation. The standalone value is {usd(B.outputs.equity_value_per_21cf_share)} a share on management's own numbers.</>],
            ["Streaming pays off", <>The content had to create value beyond cost savings. Priced as an option it is worth about {bn(d.montecarlo.option_value)}, not the {bn(inp("S_underlying_pv_revenue_synergies"))} a static view would book.</>],
          ] as [string, ReactNode][]).map(([t, body], i) => (
            <Reveal key={t} delay={i * 90}>
              <div className="panel h-full rounded-[3px] border border-rule bg-card p-5">
                <p className="num font-mono text-xs text-brass">0{i + 1}</p>
                <p className="mt-2 font-serif text-lg font-semibold text-ink">{t}</p>
                <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Reveal>

      <Reveal>
        <Panel title="Key assumptions">
          <Table head={["Assumption", "Dec 2017 view", "May 2018 view", "Type", "Basis"]} align={["l", "r", "r", "r", "l"]} rows={[
            [<Term k="wacc">WACC</Term>, pct(A.model.wacc, 2), pct(B.model.wacc, 2), <Badge kind="derived" />, <span className="text-xs text-muted">CAPM, peer betas, dated FRED / Damodaran inputs</span>],
            [<Term k="tg">Terminal growth</Term>, pct(A.g, 1), pct(B.g, 1), <Badge kind="estimate" />, <span className="text-xs text-muted">Below the 10-year Treasury yield and nominal GDP; range 1%–3%</span>],
            ["Marginal tax rate", pct(A.tax, 0), pct(B.tax, 0), <Badge kind="estimate" />, <span className="text-xs text-muted">Federal + state; 21% federal after the Tax Cuts and Jobs Act</span>],
            [<Term k="runrate">Run-rate cost synergies</Term>, bn(base.run_rate, 1), bn(base.run_rate, 1), <Badge kind="management" />, <span className="text-xs text-muted">Disney guidance, fully realized by fiscal 2021</span>],
            [<Term k="integration">Integration costs</Term>, `${mult(base.ic_mult, 2)} run-rate`, `${mult(base.ic_mult, 2)} run-rate`, <Badge kind="estimate" />, <span className="text-xs text-muted">Not disclosed at either date</span>],
            ["Financing (closing)", "all stock", `${pct(ad.cash / (ad.cash + ad.stock_val), 1)} cash`, <Badge kind="reported" />, <span className="text-xs text-muted">New debt at {pct(ad.rate, 1)} (Disney pro forma)</span>],
            [<Term k="volatility">Option volatility</Term>, "–", pct(inp("sigma_volatility"), 1), <Badge kind="estimate" />, <span className="text-xs text-muted">Median peer asset volatility; K = S, T = {inp("T_maturity_years")} years</span>],
            [<Term k="montecarlo">Monte Carlo</Term>, "–", `${d.montecarlo.n.toLocaleString("en-US")} runs`, <Badge kind="estimate" />, <span className="text-xs text-muted">Seed {d.montecarlo.seed}; independent inputs</span>],
          ]} />
        </Panel>
      </Reveal>

      <Reveal>
        <div className="grid gap-6 lg:grid-cols-3">
          <Panel title="Validation">
            <p className="num font-serif text-5xl text-ink">{d.meta.checks_total.toLocaleString("en-US")}</p>
            <p className="text-sm text-muted">automated checks, {d.meta.checks_failed} failing</p>
            <ul className="mt-4 space-y-1.5 text-sm">
              {Object.entries(d.meta.checks_by_stage).map(([k, v]) => <li key={k} className="flex justify-between border-b border-rule pb-1"><span>{k}</span><span className="num text-muted">{v}</span></li>)}
            </ul>
            <p className="mt-3 text-xs text-muted">Tie-outs, XBRL cross-checks, quote and page checks against the filings, formula recomputation, look-ahead tests, convergence and reproducibility.</p>
          </Panel>
          <Panel title="How to read the labels">
            <ul className="space-y-3 text-sm">
              <li><Badge kind="reported" /> <span className="ml-2 text-muted">taken from a filing, with page reference</span></li>
              <li><Badge kind="reported_forecast" /> <span className="ml-2 text-muted">management forecast as disclosed in the proxy</span></li>
              <li><Badge kind="management" /> <span className="ml-2 text-muted">management guidance (e.g. synergy target)</span></li>
              <li><Badge kind="market" /> <span className="ml-2 text-muted">external observation on a stated date</span></li>
              <li><Badge kind="derived" /> <span className="ml-2 text-muted">arithmetic on the above, formula stated</span></li>
              <li><Badge kind="estimate" /> <span className="ml-2 text-muted">judgement, with method and range stated</span></li>
            </ul>
          </Panel>
          <Panel title="Limits of the analysis">
            <ul className="list-disc space-y-2 pl-4 text-sm text-muted">
              <li>No look-ahead: the Dec 2017 and May 2018 valuations use only information available on those dates.</li>
              <li>Disney never quantified revenue synergies or integration costs, so those are labelled estimates.</li>
              <li>Monte Carlo inputs are independent, which understates the tails if growth, margins and synergies move together.</li>
              <li>The EPS model holds interest, NCI and share count flat, ignores Hulu consolidation and pre-dates COVID-19.</li>
            </ul>
          </Panel>
        </div>
      </Reveal>

      <Details summary={`Sources: ${forms.length} SEC filings, ${market.length} market data series, and the full reports`}>
        <Panel title="Reports in the repository">
          <ul className="grid gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2 lg:grid-cols-3">
            {DOCS.map(([l, p]) => <li key={p}><a className="text-navy underline-offset-4 hover:underline" href={`${d.meta.repo}/blob/main/${p}`} target="_blank" rel="noreferrer">{l} ↗</a></li>)}
          </ul>
        </Panel>
        <Panel title={`SEC filings used (${forms.length})`}>
          <Table head={["Document", "Form", "Filed", "Link"]} align={["l", "l", "l", "r"]}
            rows={forms.map((s) => [<span className="text-xs">{s.description}</span>, <span className="text-xs">{s.form}</span>, <span className="num text-xs">{s.filing_date ?? ""}</span>,
              <a className="text-xs text-navy underline-offset-4 hover:underline" href={s.url} target="_blank" rel="noreferrer">EDGAR ↗</a>])} />
        </Panel>
        <Panel title={`Market data (${market.length} series)`} note="Read as of each valuation date only. Stored with retrieval time and SHA-256 in the repository.">
          <Table head={["Series", "Link"]} align={["l", "r"]} rows={market.map((s) => [<span className="text-xs">{s.description}</span>, <a className="text-xs text-navy underline-offset-4 hover:underline" href={s.url} target="_blank" rel="noreferrer">source ↗</a>])} />
        </Panel>
      </Details>
      <p className="text-xs text-muted">A reproducible Python pipeline downloads SEC filings and dated market data, extracts and verifies each figure, and builds the models. This site is a static front end over the pipeline's outputs: no backend, no database.</p>
    </Section>
  );
}
