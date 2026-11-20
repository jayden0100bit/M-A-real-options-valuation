import type { Dashboard } from "../lib/data";
import { Badge, Panel, Section, Table } from "../components/ui";

const DOCS = [
  ["Data collection", "docs/data_collection_report.md"], ["Historical analysis", "docs/historical_analysis_report.md"],
  ["Valuation methodology", "docs/valuation_methodology.md"], ["Valuation report", "docs/valuation_report.md"],
  ["Synergy methodology", "docs/synergy_methodology.md"], ["Accretion / dilution", "docs/accretion_dilution_methodology.md"],
  ["Stage 4 report", "docs/stage4_analysis_report.md"], ["Real options", "docs/real_options_methodology.md"], ["Monte Carlo report", "docs/monte_carlo_report.md"],
];

export default function Methodology({ d }: { d: Dashboard }) {
  const forms = d.sources.filter((s) => !String(s.form).startsWith("XBRL") && s.form !== "external market data");
  const market = d.sources.filter((s) => s.form === "external market data");
  return (
    <Section id="method" kicker="08 · Method and sources" title="How every number was produced"
      lede="A reproducible Python pipeline downloads SEC filings and dated market data, extracts and verifies each figure, and builds the models. This site is a static front end over the pipeline's outputs: no backend, no database.">
      <div className="grid gap-6 lg:grid-cols-3">
        <Panel title="Validation">
          <p className="num font-serif text-4xl">{d.meta.checks_total.toLocaleString("en-US")}</p>
          <p className="text-sm text-muted">automated checks, {d.meta.checks_failed} failing</p>
          <ul className="mt-4 space-y-1.5 text-sm">
            {Object.entries(d.meta.checks_by_stage).map(([k, v]) => <li key={k} className="flex justify-between border-b border-rule pb-1"><span>{k}</span><span className="num text-muted">{v}</span></li>)}
          </ul>
          <p className="mt-3 text-xs text-muted">Tie-outs, XBRL cross-checks, quote and page checks against the filings, formula recomputation, look-ahead tests, convergence and reproducibility.</p>
        </Panel>
        <Panel title="Labels used throughout">
          <ul className="space-y-3 text-sm">
            <li><Badge kind="reported" /> <span className="ml-2 text-muted">taken from a filing, with page reference</span></li>
            <li><Badge kind="reported_forecast" /> <span className="ml-2 text-muted">management forecast as disclosed in the proxy</span></li>
            <li><Badge kind="market" /> <span className="ml-2 text-muted">external observation on a stated date</span></li>
            <li><Badge kind="derived" /> <span className="ml-2 text-muted">arithmetic on the above, formula stated</span></li>
            <li><Badge kind="estimate" /> <span className="ml-2 text-muted">judgement, with method and range stated</span></li>
          </ul>
          <p className="mt-4 text-xs leading-relaxed text-muted">No look-ahead: the December 2017 and May 2018 valuations use only information available on those dates. Later events appear only in labelled hindsight rows.</p>
        </Panel>
        <Panel title="Reports in the repository">
          <ul className="space-y-1.5 text-sm">
            {DOCS.map(([l, p]) => <li key={p}><a className="text-navy underline-offset-4 hover:underline" href={`${d.meta.repo}/blob/main/${p}`} target="_blank" rel="noreferrer">{l} ↗</a></li>)}
          </ul>
        </Panel>
      </div>
      <Panel title={`SEC filings used (${forms.length})`}>
        <Table head={["Document", "Form", "Filed", "Link"]} align={["l", "l", "l", "r"]}
          rows={forms.map((s) => [<span className="text-xs">{s.description}</span>, <span className="text-xs">{s.form}</span>, <span className="num text-xs">{s.filing_date ?? ""}</span>,
            <a className="text-xs text-navy underline-offset-4 hover:underline" href={s.url} target="_blank" rel="noreferrer">EDGAR ↗</a>])} />
      </Panel>
      <Panel title={`Market data (${market.length} series)`} note="Read as of each valuation date only. Stored with retrieval time and SHA-256 in the repository.">
        <Table head={["Series", "Link"]} align={["l", "r"]} rows={market.map((s) => [<span className="text-xs">{s.description}</span>, <a className="text-xs text-navy underline-offset-4 hover:underline" href={s.url} target="_blank" rel="noreferrer">source ↗</a>])} />
      </Panel>
    </Section>
  );
}
