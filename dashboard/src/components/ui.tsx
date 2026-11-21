import { useEffect, useRef, useState, type ReactNode } from "react";
import { PALETTE } from "../lib/format";
import { GLOSSARY, type TermKey } from "../lib/glossary";

// ---------------------------------------------------------------- motion helpers
export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(() => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    const m = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    if (!m) return;
    const on = () => setReduced(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return reduced;
}

export function useInView<T extends Element>(opts: IntersectionObserverInit = { threshold: 0.12 }) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || inView) return;
    if (typeof IntersectionObserver === "undefined") { setInView(true); return; }
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setInView(true); obs.disconnect(); } }, opts);
    obs.observe(el);
    return () => obs.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView]);
  return { ref, inView };
}

/** Fades content up the first time it scrolls into view. Disabled under prefers-reduced-motion (see index.css). */
export function Reveal({ children, delay = 0, className = "" }: { children: ReactNode; delay?: number; className?: string }) {
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.08, rootMargin: "0px 0px -6% 0px" });
  return <div ref={ref} className={`reveal ${inView ? "is-in" : ""} ${className}`} style={{ transitionDelay: `${delay}ms` }}>{children}</div>;
}

/** A number that eases to its new value whenever the input changes. */
export function Num({ v, fmt, duration = 450, start }: { v: number; fmt: (x: number) => string; duration?: number; start?: number }) {
  const reduced = usePrefersReducedMotion();
  const [shown, setShown] = useState(start ?? v);
  const cur = useRef(start ?? v), raf = useRef(0);
  useEffect(() => {
    cancelAnimationFrame(raf.current);
    const a = cur.current;
    if (reduced || !isFinite(v) || !isFinite(a) || a === v) { cur.current = v; setShown(v); return; }
    const t0 = performance.now();
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / duration), e = 1 - Math.pow(1 - k, 3), x = a + (v - a) * e;
      cur.current = x; setShown(k === 1 ? v : x);
      if (k < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [v, duration, reduced]);
  return <span className="num">{fmt(shown)}</span>;
}

// ---------------------------------------------------------------- layout
export function Section({ id, index, kicker, title, lede, takeaway, children }: { id: string; index: string; kicker: string; title: string; lede?: ReactNode; takeaway?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-28 border-t border-rule py-16 md:py-24">
      <Reveal>
        <div className="grid gap-8 lg:grid-cols-[1fr_340px] lg:items-end">
          <div>
            <p className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.2em] text-brass">
              <span className="num font-mono text-[13px] tracking-normal text-brass/80">{index}</span><span className="h-px w-8 bg-brass/50" />{kicker}
            </p>
            <h2 className="mt-4 max-w-3xl font-serif text-[2rem] font-semibold leading-[1.12] text-ink md:text-[2.75rem]">{title}</h2>
            {lede && <div className="mt-5 max-w-2xl text-[16px] leading-relaxed text-muted">{lede}</div>}
          </div>
          {takeaway && (
            <aside className="rounded-sm border-l-[3px] border-brass bg-card px-5 py-4 shadow-[0_1px_0_rgba(20,32,46,0.04)]">
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-brass">Key finding</p>
              <p className="mt-1.5 font-serif text-[17px] leading-snug text-ink">{takeaway}</p>
            </aside>
          )}
        </div>
      </Reveal>
      <div className="mt-12 space-y-8">{children}</div>
    </section>
  );
}

export function SubHead({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <Reveal className="pt-6">
      <h3 className="font-serif text-2xl font-semibold text-ink md:text-[1.7rem]">{title}</h3>
      {children && <div className="mt-2 max-w-2xl text-[15px] leading-relaxed text-muted">{children}</div>}
    </Reveal>
  );
}

export function Panel({ title, note, right, children, className = "" }: { title?: ReactNode; note?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={`panel rounded-[3px] border border-rule bg-card p-5 md:p-6 ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          {title && <h4 className="text-[12px] font-semibold uppercase tracking-[0.1em] text-ink">{title}</h4>}
          {right}
        </div>
      )}
      {children}
      {note && <p className="mt-4 border-t border-rule pt-3 text-xs leading-relaxed text-muted">{note}</p>}
    </div>
  );
}

export function Stat({ label, value, sub, tone, big }: { label: ReactNode; value: ReactNode; sub?: ReactNode; tone?: "pos" | "neg"; big?: boolean }) {
  return (
    <div className="border-l-2 border-navy/70 pl-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className={`num mt-1.5 font-serif leading-none transition-colors duration-300 ${big ? "text-[2rem] md:text-[2.4rem]" : "text-[1.45rem] md:text-[1.7rem]"} ${tone === "neg" ? "text-s2" : tone === "pos" ? "text-pos" : "text-ink"}`}>{value}</p>
      {sub && <p className="mt-2 text-xs leading-snug text-muted">{sub}</p>}
    </div>
  );
}

/** Plain-language finding callout. */
export function Finding({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "pos" | "neg" }) {
  const bar = tone === "pos" ? "bg-s3" : tone === "neg" ? "bg-s2" : "bg-navy";
  return (
    <div className="flex gap-3 text-sm leading-relaxed text-ink">
      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${bar}`} />
      <p>{children}</p>
    </div>
  );
}

/** Expandable technical note: keeps detail one click away instead of on the page. */
export function Details({ summary, children, defaultOpen = false }: { summary: ReactNode; children: ReactNode; defaultOpen?: boolean }) {
  return (
    <details className="tech group rounded-[3px] border border-rule bg-card/60" open={defaultOpen}>
      <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-3.5 text-sm font-medium text-ink transition-colors hover:bg-paper/70 md:px-6">
        <span className="flex items-center gap-3">
          <span className="rounded-[2px] border border-rule bg-paper px-1.5 py-[1px] text-[10px] font-semibold uppercase tracking-wider text-muted">Technical</span>
          {summary}
        </span>
        <span aria-hidden className="text-muted transition-transform duration-300 group-open:rotate-45">+</span>
      </summary>
      <div className="details-body space-y-6 border-t border-rule px-5 py-5 md:px-6">{children}</div>
    </details>
  );
}

/** Finance term with an inline definition on hover / focus / tap. */
export function Term({ k, children }: { k: TermKey; children?: ReactNode }) {
  const g = GLOSSARY[k];
  return (
    <span className="term group relative inline-block cursor-help" tabIndex={0} aria-describedby={`term-${k}`}>
      <span className="border-b border-dotted border-navy/50 text-ink">{children ?? g.term}</span>
      <span id={`term-${k}`} role="tooltip"
        className="pointer-events-none absolute bottom-full left-1/2 z-40 mb-2 w-64 -translate-x-1/2 translate-y-1 rounded-[3px] border border-rule bg-ink px-3 py-2.5 text-left text-xs font-normal leading-relaxed text-paper opacity-0 shadow-lg transition-all duration-200 group-hover:translate-y-0 group-hover:opacity-100 group-focus:translate-y-0 group-focus:opacity-100">
        <span className="block font-semibold text-brass-light">{g.term}</span>{g.def}
      </span>
    </span>
  );
}

export function Badge({ kind }: { kind: string }) {
  const k = kind.toLowerCase();
  const label = k.startsWith("reported_forecast") ? "Forecast" : k.startsWith("reported") ? "Reported" : k.startsWith("derived") ? "Derived"
    : k.startsWith("estimate") ? "Estimate" : k.startsWith("market") ? "Market" : k.startsWith("management") ? "Guidance" : kind;
  const cls = label === "Reported" ? "border-navy/40 text-navy" : label === "Estimate" ? "border-brass/60 text-brass" : "border-rule text-muted";
  return <span className={`inline-block rounded-[2px] border px-1.5 py-[1px] text-[10px] font-semibold uppercase tracking-wider ${cls}`}>{label}</span>;
}

export function Slider({ label, value, min, max, step, onChange, fmt, hint, explain, base }: {
  label: ReactNode; value: number; min: number; max: number; step: number; onChange: (v: number) => void; fmt: (v: number) => string;
  hint?: ReactNode; explain?: ReactNode; base?: number;
}) {
  const fill = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));
  const bpos = base == null ? null : Math.max(0, Math.min(100, ((base - min) / (max - min)) * 100));
  const aria = typeof label === "string" ? label : undefined;
  return (
    <label className="block">
      <span className="flex items-baseline justify-between gap-3 text-[13px]">
        <span className="font-semibold text-ink">{label}</span>
        <span className="num rounded-[2px] bg-navy/[0.07] px-1.5 py-0.5 font-mono text-[12px] text-navy">{fmt(value)}</span>
      </span>
      {explain && <span className="mt-1 block text-[12px] leading-snug text-muted">{explain}</span>}
      <span className="relative mt-3 block">
        <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))}
          className="rng w-full" style={{ ["--fill" as string]: `${fill}%` }} aria-label={aria} />
        {bpos != null && <span aria-hidden title="Pipeline base" className="pointer-events-none absolute -bottom-2 h-1.5 w-px bg-brass" style={{ left: `calc(${bpos}% + ${8 - bpos * 0.16}px)` }} />}
      </span>
      {hint && <span className="mt-2 block text-[11px] text-muted/90">{hint}</span>}
    </label>
  );
}

export function Segmented<T extends string>({ value, options, onChange, label, size = "sm" }: { value: T; options: { value: T; label: ReactNode }[]; onChange: (v: T) => void; label: string; size?: "sm" | "md" }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap rounded-[3px] border border-rule bg-paper p-0.5">
      {options.map((o) => (
        <button key={o.value} role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={`rounded-[2px] font-medium transition-all duration-200 ${size === "md" ? "px-4 py-2 text-[13px]" : "px-3 py-1.5 text-xs"} ${value === o.value ? "bg-navy text-card shadow-sm" : "text-muted hover:bg-card hover:text-ink"}`}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function ResetButton({ onClick, show }: { onClick: () => void; show: boolean }) {
  return (
    <button onClick={onClick} disabled={!show}
      className={`text-xs font-medium text-navy underline-offset-4 transition-opacity duration-200 hover:underline ${show ? "opacity-100" : "pointer-events-none opacity-0"}`}>
      ↺ Reset to base
    </button>
  );
}

export function Table({ head, rows, align }: { head: ReactNode[]; rows: ReactNode[][]; align?: ("l" | "r")[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="num w-full border-collapse text-[13px]">
        <thead>
          <tr className="border-b border-ink/70">
            {head.map((h, i) => <th key={i} className={`px-2 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted ${(align?.[i] ?? (i === 0 ? "l" : "r")) === "r" ? "text-right" : "text-left"}`}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-rule transition-colors last:border-0 hover:bg-paper/70">
              {r.map((c, j) => <td key={j} className={`px-2 py-2 align-top ${(align?.[j] ?? (j === 0 ? "l" : "r")) === "r" ? "whitespace-nowrap text-right" : "text-left"}`}>{c}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color: string; dash?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted">
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-2">
          <span className="inline-block h-[3px] w-4 rounded" style={{ background: i.dash ? "transparent" : i.color, borderTop: i.dash ? `2px dashed ${i.color}` : undefined }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}

export function Source({ children }: { children: ReactNode }) {
  return <p className="text-[11px] leading-relaxed text-muted"><span className="font-semibold text-ink/70">Source · </span>{children}</p>;
}

/** Horizontal tornado bar (one input at a time, low → high). */
export function TornadoRow({ label, lo, hi, domain, fmt }: { label: string; lo: number; hi: number; domain: [number, number]; fmt: (v: number) => string }) {
  const x = (v: number) => ((v - domain[0]) / (domain[1] - domain[0])) * 100;
  return (
    <div className="grid grid-cols-[130px_1fr] items-center gap-3 text-xs md:grid-cols-[190px_1fr]">
      <span className="capitalize text-muted">{label}</span>
      <div className="relative h-7 rounded-sm bg-paper">
        <div className="absolute top-0 h-full w-px bg-ink" style={{ left: `${x(0)}%` }} />
        <div className="absolute top-1.5 h-4 rounded-[2px] bg-s1/80 transition-all duration-500 hover:bg-s1" style={{ left: `${x(lo)}%`, width: `${Math.max(0.5, x(hi) - x(lo))}%` }} />
        <span className="num absolute top-1.5 -translate-x-full pr-1.5 text-[11px]" style={{ left: `${x(lo)}%` }}>{fmt(lo)}</span>
        <span className="num absolute top-1.5 pl-1.5 text-[11px]" style={{ left: `${x(hi)}%` }}>{fmt(hi)}</span>
      </div>
    </div>
  );
}

export const axisProps = { stroke: PALETTE.rule, tick: { fill: PALETTE.muted, fontSize: 11 }, tickLine: false } as const;
export const gridProps = { stroke: PALETTE.rule, strokeDasharray: "0", vertical: false } as const;
export const tooltipStyle = {
  contentStyle: { background: PALETTE.card, border: `1px solid ${PALETTE.rule}`, borderRadius: 3, fontSize: 12, color: PALETTE.ink, boxShadow: "0 6px 20px rgba(20,32,46,0.10)" },
  labelStyle: { color: PALETTE.ink, fontWeight: 600 },
  cursor: { fill: "#1F3A5F0D" },
} as const;
/** Short, consistent chart transition: bars ease to new values when assumptions change. */
export const anim = { isAnimationActive: true, animationDuration: 380, animationEasing: "ease-out" } as const;
