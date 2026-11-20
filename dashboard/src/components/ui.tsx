import type { ReactNode } from "react";
import { PALETTE } from "../lib/format";

export function Section({ id, kicker, title, lede, children }: { id: string; kicker: string; title: string; lede?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-rule py-14 md:py-20">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brass">{kicker}</p>
      <h2 className="mt-3 font-serif text-3xl font-semibold leading-tight text-ink md:text-[2.4rem]">{title}</h2>
      {lede && <div className="mt-4 max-w-3xl text-[15px] leading-relaxed text-muted">{lede}</div>}
      <div className="mt-10 space-y-8">{children}</div>
    </section>
  );
}

export function Panel({ title, note, right, children, className = "" }: { title?: ReactNode; note?: ReactNode; right?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-sm border border-rule bg-card p-5 md:p-6 ${className}`}>
      {(title || right) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          {title && <h3 className="text-[13px] font-semibold uppercase tracking-[0.08em] text-ink">{title}</h3>}
          {right}
        </div>
      )}
      {children}
      {note && <p className="mt-4 border-t border-rule pt-3 text-xs leading-relaxed text-muted">{note}</p>}
    </div>
  );
}

export function Stat({ label, value, sub, tone }: { label: string; value: ReactNode; sub?: ReactNode; tone?: "pos" | "neg" }) {
  return (
    <div className="border-l-2 border-navy/80 pl-4">
      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className={`num mt-1 font-serif text-[1.75rem] leading-none ${tone === "neg" ? "text-s2" : "text-ink"}`}>{value}</p>
      {sub && <p className="mt-2 text-xs leading-snug text-muted">{sub}</p>}
    </div>
  );
}

export function Badge({ kind }: { kind: string }) {
  const k = kind.toLowerCase();
  const label = k.startsWith("reported_forecast") ? "Forecast" : k.startsWith("reported") ? "Reported" : k.startsWith("derived") ? "Derived"
    : k.startsWith("estimate") ? "Estimate" : k.startsWith("market") ? "Market" : k.startsWith("management") ? "Guidance" : kind;
  const cls = label === "Reported" ? "border-navy/40 text-navy" : label === "Estimate" ? "border-brass/60 text-brass" : "border-rule text-muted";
  return <span className={`inline-block rounded-[2px] border px-1.5 py-[1px] text-[10px] font-semibold uppercase tracking-wider ${cls}`}>{label}</span>;
}

export function Slider({ label, value, min, max, step, onChange, fmt, hint }: { label: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void; fmt: (v: number) => string; hint?: string }) {
  return (
    <label className="block">
      <span className="flex items-baseline justify-between gap-3 text-xs">
        <span className="font-medium text-ink">{label}</span>
        <span className="num font-mono text-[12px] text-navy">{fmt(value)}</span>
      </span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(parseFloat(e.target.value))} className="mt-2 w-full" aria-label={label} />
      {hint && <span className="mt-1 block text-[11px] text-muted">{hint}</span>}
    </label>
  );
}

export function Segmented<T extends string>({ value, options, onChange, label }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; label: string }) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap rounded-sm border border-rule bg-paper p-0.5">
      {options.map((o) => (
        <button key={o.value} role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 text-xs font-medium transition-colors ${value === o.value ? "bg-navy text-card" : "text-muted hover:text-ink"}`}>
          {o.label}
        </button>
      ))}
    </div>
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
            <tr key={i} className="border-b border-rule last:border-0">
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

export const axisProps = { stroke: PALETTE.rule, tick: { fill: PALETTE.muted, fontSize: 11 }, tickLine: false } as const;
export const gridProps = { stroke: PALETTE.rule, strokeDasharray: "0", vertical: false } as const;
export const tooltipStyle = {
  contentStyle: { background: PALETTE.card, border: `1px solid ${PALETTE.rule}`, borderRadius: 2, fontSize: 12, color: PALETTE.ink },
  labelStyle: { color: PALETTE.ink, fontWeight: 600 },
  cursor: { fill: "#1F3A5F0D" },
} as const;
