import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Dashboard, PerspectiveKey } from "../lib/data";
import { accretion, synergyValue } from "../lib/finance";
import { PALETTE, bn, mult, musd, pct, usd } from "../lib/format";
import { Badge, Details, Finding, Legend, Num, Panel, Reveal, ResetButton, Section, Segmented, Slider, Source, Stat, SubHead, Term, TornadoRow, anim, axisProps, gridProps, tooltipStyle } from "../components/ui";

type Sc = "bear" | "base" | "bull";

export default function SynergiesEps({ d }: { d: Dashboard }) {
  // ---------------------------------------------------------------- shared
  const [real, setReal] = useState(1); // synergy realization drives both the synergy value and EPS

  // ---------------------------------------------------------------- synergy model (Stage 4A)
  const [pk, setPk] = useState<PerspectiveKey>("B_proxy_2018-05");
  const [sc, setSc] = useState<Sc>("base");
  const M = d.synergy.model, P = d.valuation[pk];
  const def = M.scenarios[sc];
  const [rr, setRr] = useState(def.run_rate), [delay, setDelay] = useState(0), [icm, setIcm] = useState(def.ic_mult), [g, setG] = useState(def.g), [prem, setPrem] = useState(0);
  const pick = (s: Sc) => { setSc(s); const x = M.scenarios[s]; setRr(x.run_rate); setDelay(0); setIcm(x.ic_mult); setG(x.g); setPrem(0); };
  const synChanged = real !== 1 || rr !== def.run_rate || delay !== 0 || icm !== def.ic_mult || g !== def.g || prem !== 0;
  const v = useMemo(() => synergyValue({ runRate: rr, phase: M.scenarios[sc].phase, icPhase: M.ic_phase, icMult: icm, g, rate: P.model.wacc + prem, tax: P.tax,
    realization: real, delay, timing: M.timing[pk] }), [rr, sc, M, icm, g, P, prem, real, delay, pk]);
  const flows = v.flows.map((f, i) => ({ fy: `FY${M.fy[i]}`, synergies: f.syn, integration: -f.ic }));
  const standalonePs = P.outputs.equity_value_per_21cf_share, netPs = v.net / P.shares;
  const offers = d.synergy.justification.filter((j) => j.perspective === pk && j.metric === "consideration_per_share");
  const advisors = d.synergy.reference.filter((r) => r.perspective === "B_proxy_2018-05");

  // ---------------------------------------------------------------- accretion / dilution (Stage 4B)
  const A = d.accretion.params;
  const baseCash = A.cash / (A.cash + A.stock_val);
  const [structure, setStructure] = useState<"closing" | "original">("closing");
  const [rsn, setRsn] = useState<"sold" | "kept">("sold");
  const [cash, setCash] = useState(baseCash), [rate, setRate] = useState(A.rate), [price, setPrice] = useState(A.vwap), [ppa, setPpa] = useState(1);
  const custom = Math.abs(cash - baseCash) > 1e-9 || Math.abs(price - A.vwap) > 1e-9;
  const r = useMemo(() => accretion(A, { realization: real, rate, ppaFactor: ppa, includeRsn: rsn === "kept", original: structure === "original",
    cashShare: custom ? cash : null, price: custom ? price : null }), [A, real, rate, ppa, rsn, structure, custom, cash, price]);
  const epsChanged = real !== 1 || custom || rate !== A.rate || ppa !== 1 || structure !== "closing" || rsn !== "sold";
  const resetEps = () => { setReal(1); setCash(baseCash); setRate(A.rate); setPrice(A.vwap); setPpa(1); setStructure("closing"); setRsn("sold"); };
  const fys = Object.keys(r);
  const eps = fys.map((fy) => ({ fy, standalone: r[fy].standalone, adjusted: r[fy].adjusted, gaap: r[fy].gaap }));
  const acc = fys.map((fy) => ({ fy, adjusted: r[fy].accAdj, gaap: r[fy].accGaap }));
  const anchor = d.accretion.anchor.filter((a) => String(a.fiscal_year).startsWith("FY2018"));
  const an = (m: string) => Number(anchor.find((x) => x.metric === m)?.v);
  const sens = d.accretion.sensitivity_fy2021.filter((s) => s.metric === "accretion_adjusted");
  const groups = Array.from(new Set(sens.map((s) => s.case.split(" = ")[0].replace("sensitivity: ", ""))));
  const tornado = groups.map((gr) => { const xs = sens.filter((s) => s.case.includes(gr)).map((s) => s.v); return { g: gr.replace(/_/g, " "), lo: Math.min(...xs), hi: Math.max(...xs) }; })
    .filter((t) => t.hi - t.lo > 1e-6).sort((x, y) => (y.hi - y.lo) - (x.hi - x.lo));
  const fy21 = r["FY2021"];
  const baseFy21 = Number(d.summary.find((s) => s.metric === "FY2021 adjusted EPS accretion (base)")?.value);

  const amendedCover = d.synergy.justification.find((j) => j.perspective === "B_proxy_2018-05" && j.case.startsWith("amended") && j.metric === "synergy_coverage_of_premium_base")!.v!;

  const realSlider = (
    <Slider label="Synergy realization" value={real} min={0} max={1.25} step={0.05} onChange={setReal} fmt={(x) => pct(x, 0)} base={1}
      explain="How much of the promised savings Disney actually achieves. 100% = the guidance." hint="Shared: also drives the EPS model below" />
  );

  return (
    <Section id="synergies" index="03" kicker="Synergies & EPS" title="Could the savings justify the price?"
      lede={<>Disney guided to roughly <b className="text-ink">$2.0bn a year</b> of cost <Term k="synergies">synergies</Term>. The question: are those savings worth more than the <Term k="premium">premium</Term> Disney paid over standalone value?</>}
      takeaway={<>At $38 the base-case savings cover only {mult(amendedCover, 2)} of the premium. Disney paid away essentially all of the synergy value to Fox's shareholders.</>}>

      <Reveal>
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <Panel title="Synergy assumptions" right={<ResetButton show={synChanged} onClick={() => { pick(sc); setReal(1); }} />}>
            <div className="space-y-6">
              <div>
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">Scenario</p>
                <Segmented label="Scenario" value={sc} onChange={pick} options={[{ value: "bear", label: "Bear" }, { value: "base", label: "Guidance" }, { value: "bull", label: "Bull" }]} />
                <p className="mt-2 text-[11px] leading-snug text-muted">{def.note}</p>
              </div>
              {realSlider}
              <Slider label={<Term k="integration">Integration costs</Term>} value={icm} min={0.5} max={2} step={0.05} onChange={setIcm} fmt={(x) => `${mult(x, 2)} run-rate`} base={def.ic_mult}
                explain="One-off cost of getting the savings, as a multiple of one year's savings." hint="Disney later estimated ~$1.5bn of severance (0.75x)" />
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink">
                  More assumptions <span className="transition-transform group-open:rotate-45">+</span>
                </summary>
                <div className="mt-5 space-y-6">
                  <Segmented label="Perspective" value={pk} onChange={setPk} options={[{ value: "A_announcement_2017-12", label: "Dec 2017 (tax 36%)" }, { value: "B_proxy_2018-05", label: "May 2018 (tax 22%)" }]} />
                  <Slider label={<Term k="runrate">Run-rate savings</Term>} value={rr} min={500} max={3000} step={50} onChange={setRr} fmt={(x) => bn(x, 2)} base={def.run_rate} explain="Annual savings once fully achieved." hint="Guidance: ~$2.0bn" />
                  <Slider label="Delay" value={delay} min={0} max={2} step={1} onChange={setDelay} fmt={(x) => `${x} yr`} base={0} explain="Years the savings arrive late." />
                  <Slider label="Savings growth after run-rate" value={g} min={0} max={0.02} step={0.0025} onChange={setG} fmt={(x) => pct(x, 2)} base={def.g} explain="Growth of the savings each year, forever." />
                  <Slider label="Extra discount rate" value={prem} min={0} max={0.03} step={0.0025} onChange={setPrem} fmt={(x) => `+${pct(x, 2)}`} base={0} explain="Treat the savings as riskier than the business itself." hint={`Base = standalone WACC ${pct(P.model.wacc, 2)}`} />
                </div>
              </details>
            </div>
          </Panel>

          <div className="space-y-6">
            <Panel>
              <div className="grid grid-cols-2 gap-6 md:grid-cols-3">
                <Stat big label="Net synergy value" value={<Num v={v.net} fmt={(x) => bn(x)} />} sub={<><Num v={netPs} fmt={usd} /> per 21CF share</>} />
                <Stat label="Savings, present value" value={<Num v={v.gross} fmt={(x) => bn(x)} />} sub="after tax" />
                <Stat label={<Term k="integration">Integration costs</Term>} value={<Num v={-v.pvIntegration} fmt={(x) => bn(x)} />} tone="neg" sub="present value" />
              </div>
            </Panel>
            <Panel title={<><Term k="coverage">Premium coverage</Term>: do the savings pay for the premium?</>}
              note="Premium = price minus the Stage 3 standalone value per share. Coverage = net synergy value ÷ premium. Value created = standalone + net synergies − price.">
              <div className="space-y-7">
                {offers.map((o) => {
                  const premPs = (o.v ?? 0) - standalonePs, cover = premPs > 0 ? netPs / premPs : null, created = (standalonePs + netPs - (o.v ?? 0)) * P.shares;
                  const scale = Math.max(14, premPs, netPs) * 1.05, w = (x: number) => `${Math.max(0, (x / scale) * 100)}%`;
                  return (
                    <div key={o.case}>
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="text-sm font-semibold text-ink">{(() => { const c = o.case.replace(/\s*\(.*\)/, ""); return c.charAt(0).toUpperCase() + c.slice(1); })()} <span className="font-normal text-muted">· price {usd(o.v)}</span></p>
                        <p className="num text-sm">{cover === null ? <span className="text-muted">no premium over standalone</span> : <>coverage <b className={cover < 1 ? "text-s2" : "text-pos"}><Num v={cover} fmt={(x) => mult(x, 2)} /></b></>}</p>
                      </div>
                      <div className="mt-2 space-y-1.5">
                        <div className="flex items-center gap-3"><span className="w-20 shrink-0 text-[11px] text-muted">Premium</span>
                          <div className="h-4 flex-1 rounded-[2px] bg-paper"><div className="h-full rounded-[2px] bg-s2 transition-[width] duration-500 ease-out" style={{ width: w(premPs) }} /></div>
                          <span className="num w-14 text-right text-xs">{usd(premPs)}</span></div>
                        <div className="flex items-center gap-3"><span className="w-20 shrink-0 text-[11px] text-muted">Savings</span>
                          <div className="h-4 flex-1 rounded-[2px] bg-paper"><div className="h-full rounded-[2px] bg-s3 transition-[width] duration-500 ease-out" style={{ width: w(netPs) }} /></div>
                          <span className="num w-14 text-right text-xs"><Num v={netPs} fmt={usd} /></span></div>
                      </div>
                      <p className="mt-2 text-xs text-muted"><Term k="valuecreated">Value created</Term> for Disney: <b className={`num ${created < 0 ? "text-s2" : "text-pos"}`}><Num v={created} fmt={(x) => bn(x)} /></b></p>
                    </div>);
                })}
              </div>
            </Panel>
          </div>
        </div>
      </Reveal>

      <Details summary="Synergy and integration cash flows by year">
        <Panel>
          <Legend items={[{ label: "Cost synergies (pre-tax)", color: PALETTE.s3 }, { label: "Integration costs", color: PALETTE.s2 }]} />
          <div className="mt-2 h-56">
            <ResponsiveContainer>
              <BarChart data={flows} stackOffset="sign" margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="fy" {...axisProps} />
                <YAxis {...axisProps} width={52} tickFormatter={(x) => `${(x / 1000).toFixed(1)}bn`} />
                <Tooltip {...tooltipStyle} formatter={(x: number, k: string) => [musd(x), k === "synergies" ? "Cost synergies" : "Integration costs"]} />
                <ReferenceLine y={0} stroke={PALETTE.ink} />
                <Bar dataKey="synergies" stackId="s" fill={PALETTE.s3} {...anim} />
                <Bar dataKey="integration" stackId="s" fill={PALETTE.s2} {...anim} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-muted">Terminal value after FY2023: {bn(v.pvTv)} ({pct(v.pvTv / v.gross, 0)} of gross). Durability of the savings is the key judgement. Revenue synergies and integration costs were never quantified by Disney, so the phasing and integration costs are labelled estimates.</p>
          {pk === "B_proxy_2018-05" && advisors.length > 0 && (
            <p className="mt-3 text-xs text-muted">Cross-check: Disney's advisors' disclosed ranges imply about {usd(Number(advisors.find((a) => a.case === "cost synergies")?.v))} per share for cost synergies
              (May 2018 proxy p.145) and a further {usd(Number(advisors.find((a) => a.case === "revenue synergies")?.v))} for revenue synergies, which were never quantified and are treated as an option (Section 04).</p>)}
        </Panel>
      </Details>

      {/* ---------------------------------------------------------------- EPS */}
      <SubHead title="Does the deal raise Disney's earnings per share?">
        Management said the deal would be <Term k="accretion">accretive</Term> before purchase accounting in the second fiscal year after closing (FY2021).
        Borrowing to pay cash adds interest; issuing shares spreads earnings over more shares. The mix matters.
      </SubHead>

      <Reveal>
        <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <Panel title="Financing assumptions" right={<ResetButton show={epsChanged} onClick={resetEps} />}>
            <div className="space-y-6">
              <Slider label="Financing mix: cash share" value={cash} min={0} max={1} step={0.05} onChange={setCash} fmt={(x) => `${pct(x, 0)} cash`} base={baseCash}
                explain="Share of the price paid in cash (funded with new debt); the rest is paid in new Disney shares."
                hint={structure === "original" ? "Not used in the original all-stock structure" : `Closing: ${pct(baseCash, 1)} cash (debt-financed)`} />
              {realSlider}
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted hover:text-ink">
                  More assumptions <span className="transition-transform group-open:rotate-45">+</span>
                </summary>
                <div className="mt-5 space-y-6">
                  <Segmented label="Deal structure" value={structure} onChange={setStructure} options={[{ value: "closing", label: "Closing terms" }, { value: "original", label: "Original all-stock" }]} />
                  <Segmented label="RSNs" value={rsn} onChange={setRsn} options={[{ value: "sold", label: "RSNs sold (actual)" }, { value: "kept", label: "RSNs kept" }]} />
                  <Slider label="Rate on new debt" value={rate} min={0.02} max={0.06} step={0.001} onChange={setRate} fmt={(x) => pct(x, 1)} base={A.rate} explain="Interest Disney pays on the borrowing." hint="Disney's pro forma assumed 3.3%" />
                  <Slider label="Disney share price for the stock portion" value={price} min={90} max={130} step={1} onChange={setPrice} fmt={(x) => usd(x, 0)} base={A.vwap} explain="Higher price = fewer new shares to issue." hint="Closing average $114.18" />
                  <Slider label={<Term k="ppa">Purchase-accounting amortization</Term>} value={ppa} min={0.5} max={1.5} step={0.05} onChange={setPpa} fmt={(x) => pct(x, 0)} base={1} explain="Affects GAAP EPS only." hint="Base $2.7bn a year (FY2019 10-K, ex-RSN)" />
                </div>
              </details>
            </div>
          </Panel>

          <div className="space-y-6">
            <Panel>
              <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
                {fys.map((fy) => <Stat key={fy} big={fy === "FY2021"} label={`${fy}${fy === "FY2021" ? " · target year" : ""}`} value={<Num v={r[fy].accAdj} fmt={(x) => pct(x, 1, true)} />}
                  tone={r[fy].accAdj < 0 ? "neg" : "pos"} sub={<>GAAP basis <Num v={r[fy].accGaap} fmt={(x) => pct(x, 1, true)} /></>} />)}
                <Stat label="Interest on new debt" value={<Num v={r[fys[0]].interest / 1000} fmt={(x) => `$${x.toFixed(2)}bn`} />} sub="pre-tax, a year" />
              </div>
              <div className="mt-5 border-t border-rule pt-4">
                <Finding tone={fy21.accAdj >= 0 ? "pos" : "neg"}>
                  With these assumptions, FY2021 adjusted EPS is <b>{pct(Math.abs(fy21.accAdj), 1)} {fy21.accAdj >= 0 ? "higher" : "lower"}</b> than Disney on its own
                  {epsChanged ? <> (pipeline base: {pct(baseFy21, 1, true)})</> : null}.
                </Finding>
              </div>
            </Panel>
            <Panel title={<><Term k="accretion">Accretion / (dilution)</Term> by year</>}>
              <Legend items={[{ label: "Adjusted (ex purchase accounting, ex integration)", color: PALETTE.s1 }, { label: "GAAP basis", color: PALETTE.s2 }]} />
              <div className="mt-2 h-56">
                <ResponsiveContainer>
                  <BarChart data={acc} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="fy" {...axisProps} />
                    <YAxis {...axisProps} width={44} tickFormatter={(x) => pct(x, 0)} />
                    <Tooltip {...tooltipStyle} formatter={(x: number, k: string) => [pct(x, 1, true), k === "adjusted" ? "Adjusted" : "GAAP basis"]} />
                    <ReferenceLine y={0} stroke={PALETTE.ink} />
                    <Bar dataKey="adjusted" {...anim}>{acc.map((a) => <Cell key={a.fy} fill={PALETTE.s1} />)}</Bar>
                    <Bar dataKey="gaap" fill={PALETTE.s2} {...anim} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>
        </div>
      </Reveal>

      <Details summary="EPS paths, sensitivity and Disney's own pro forma">
        <p className="text-sm leading-relaxed text-muted">Disney's own pro forma for FY2018, on a GAAP basis without synergies, showed EPS falling from {usd(an("eps_disney"))} to {usd(an("eps_pro_forma"))} ({pct(an("accretion_dilution_pct"), 1)}).
          The forward model rebuilds FY2020–22 from the proxy forecasts and the actual closing financing.</p>
        <div className="grid gap-6 lg:grid-cols-2">
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
          <Panel title="What moves FY2021 accretion most" right={<Badge kind="estimate" />} note="One input at a time (Stage 4 sensitivity runs): synergy realization 0–125%, cash share 0–100%, debt rate 2–6%, Disney price $90–130. Purchase accounting and integration costs only affect the GAAP basis.">
            <div className="space-y-2.5">{tornado.map((t) => <TornadoRow key={t.g} label={t.g} lo={t.lo} hi={t.hi} domain={[-0.24, 0.22]} fmt={(x) => pct(x, 1, true)} />)}</div>
          </Panel>
        </div>
        <p className="text-xs text-muted">Disney standalone earnings come from the "Disney street forecasts" in the May 2018 proxy (analyst-based, not management EPS guidance). The model holds interest, NCI and share count flat, ignores Hulu consolidation and pre-dates COVID-19.</p>
      </Details>
      <Source>synergy_assumptions.csv, synergy_outputs.csv (Stage 4A); accretion_dilution_inputs.csv, accretion_dilution_outputs.csv (Stage 4B). Guidance quoted from DIS_8K_20171214_EX99_1, the 14 Dec 2017 investor-call transcript (Form 425) and the May 2018 proxy.</Source>
    </Section>
  );
}
