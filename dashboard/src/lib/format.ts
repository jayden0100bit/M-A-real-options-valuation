export const bn = (m: number | null | undefined, d = 1) => (m == null || !isFinite(m) ? "–" : `${m < 0 ? "−" : ""}$${(Math.abs(m) / 1000).toFixed(d)}bn`);
export const musd = (m: number | null | undefined, d = 0) => (m == null || !isFinite(m) ? "–" : `${m < 0 ? "−" : ""}$${Math.abs(m).toLocaleString("en-US", { maximumFractionDigits: d, minimumFractionDigits: d })}m`);
export const usd = (x: number | null | undefined, d = 2) => (x == null || !isFinite(x) ? "–" : `${x < 0 ? "−" : ""}$${Math.abs(x).toFixed(d)}`);
export const pct = (x: number | null | undefined, d = 1, sign = false) => (x == null || !isFinite(x) ? "–" : `${sign && x > 0 ? "+" : x < 0 ? "−" : ""}${Math.abs(x * 100).toFixed(d)}%`);
export const mult = (x: number | null | undefined, d = 1) => (x == null || !isFinite(x) ? "–" : `${x.toFixed(d)}x`);
export const PALETTE = { s1: "#2a78d6", s2: "#eb6834", s3: "#1baf7a", s4: "#eda100", ink: "#14202E", muted: "#5B6472", rule: "#E3DDD1", navy: "#1F3A5F", card: "#FCFAF6" };
export const ENTITY: Record<string, { label: string; color: string }> = {
  DIS: { label: "Disney", color: PALETTE.s1 },
  "21CF": { label: "21CF consolidated", color: PALETTE.s2 },
  RemainCo: { label: "RemainCo (acquired)", color: PALETTE.s3 },
};
