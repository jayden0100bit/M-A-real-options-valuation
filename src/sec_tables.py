"""Parse financial tables out of downloaded SEC HTML filings.

Each table is turned into rows of ``(label, [numbers...])`` where numbers are
parsed from the remaining cells: ``(1,234)`` becomes -1234 and an em dash
becomes 0. Each table also gets the printed page number of the filing page it
sits on (the next standalone page-number line after the table). That page
number is what the source register cites.

Typical use::

    from sec_tables import load_tables, find_tables
    tables = load_tables("DIS_10K_FY2017")
    t = find_tables(tables, must_contain=["Revenues", "Parks and Resorts"])[0]
    t.value("Revenues", col=0)
"""
from __future__ import annotations

import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from sec_text import decode_html, doc_path

ROOT = Path(__file__).resolve().parents[1]
TABLE_CACHE = ROOT / "data" / "interim" / "tables"
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_NUM = re.compile(r"\(?-?\$?\s*\d[\d,]*(?:\.\d+)?\s*\)?%?|—|–|-")
_PAGE_LINE = re.compile(r"^\s*(\d{1,3}|[ivxlc]{1,6}|[A-Z]-\d{1,3}|F-\d{1,3})\s*$")


def _clean(s: str) -> str:
    s = s.replace("\xa0", " ").replace("​", "")
    s = re.sub(r"[\x80-\x9f]", lambda m: bytes([ord(m.group(0))]).decode("cp1252", "replace"), s)
    return re.sub(r"\s+", " ", s).strip()


def parse_number(tok: str):
    t = tok.strip()
    if t in ("—", "–", "-"):
        return 0.0
    neg = t.startswith("(") or t.startswith("-")
    t = re.sub(r"[()$,%\s-]", "", t)
    if not t:
        return None
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


@dataclass
class Table:
    doc_id: str
    index: int
    page: str | None
    rows: list = field(default_factory=list)  # list of (label, [values], raw_cells)

    def text(self) -> str:
        return "\n".join(r[0] + " | " + " | ".join("" if v is None else f"{v:g}" for v in r[1])
                         for r in self.rows)

    def find_row(self, label: str, occurrence: int = 0, exact: bool = False):
        hits = []
        for r in self.rows:
            lab = r[0].lower().rstrip(":")
            want = label.lower()
            if (lab == want) if exact else lab.startswith(want):
                hits.append(r)
        if len(hits) <= occurrence:
            raise KeyError(f"row '{label}' (occurrence {occurrence}) not in {self.doc_id} table {self.index}")
        return hits[occurrence]

    def value(self, label: str, col: int = 0, occurrence: int = 0, exact: bool = False) -> float:
        vals = self.find_row(label, occurrence, exact)[1]
        if col >= len(vals):
            raise IndexError(f"row '{label}' has only {len(vals)} values in {self.doc_id} table {self.index}")
        return vals[col]


def _row_cells(tr) -> list[str]:
    return [_clean(td.get_text(" ")) for td in tr.find_all(["td", "th"])]


def _parse_row(cells: list[str]):
    cells = [c for c in cells if c not in ("", "$")]
    if not cells:
        return None
    # merge dangling ")" or "%" cells into the previous cell
    merged = []
    for c in cells:
        if merged and c in (")", "%", ")%", "%)"):
            merged[-1] += c
        else:
            merged.append(c)
    label_parts, values = [], []
    for c in merged:
        if values or _NUM.fullmatch(c.replace(" ", "")) or c in ("—", "–", "-"):
            v = parse_number(c)
            if v is not None or c in ("—", "–", "-"):
                values.append(v)
                continue
            if values:  # text after numbers: keep as part of label suffix
                continue
        label_parts.append(c)
    label = " ".join(label_parts).strip()
    return label, values, merged


def extract_tables(doc_id: str) -> list[Table]:
    soup = BeautifulSoup(decode_html(doc_path(doc_id).read_bytes()), "lxml")
    tables = soup.find_all("table")
    # Replace each table with a marker so its position in the page text is known
    parsed = []
    for i, t in enumerate(tables):
        rows = []
        for tr in t.find_all("tr"):
            r = _parse_row(_row_cells(tr))
            if r:
                rows.append(r)
        parsed.append(rows)
        t.replace_with(soup.new_string(f"\n@@TABLE{i}@@\n"))
    # physical page breaks (same rule as sec_text.paged_lines)
    n_breaks = 0
    for tag in soup.find_all(style=re.compile(r"page-break-(before|after)\s*:\s*always", re.I)):
        marker = soup.new_string("\n@@PB@@\n")
        if re.search(r"page-break-before", tag.get("style", ""), re.I):
            tag.insert_before(marker)
        else:
            tag.insert_after(marker)
        n_breaks += 1
    for hr in soup.find_all("hr"):
        hr.insert_after(soup.new_string("\n@@PB@@\n"))
        n_breaks += 1
    for tag in soup.find_all(["p", "div", "br", "hr"]):
        tag.append("\n")
    lines = [_clean(l) for l in soup.get_text().splitlines()]
    lines = [l for l in lines if l]
    pages = {}
    pending = []
    if n_breaks:
        # a table's page is the printed page number found on the same physical page
        page_no = None
        for line in lines + ["@@PB@@"]:
            m = re.fullmatch(r"@@TABLE(\d+)@@", line)
            if m:
                pending.append(int(m.group(1)))
            elif line == "@@PB@@":
                for idx in pending:
                    pages[idx] = page_no
                pending, page_no = [], None
            elif _PAGE_LINE.match(line):
                page_no = line
    else:
        # no break markers: a table belongs to the page whose number comes next
        for line in lines:
            m = re.fullmatch(r"@@TABLE(\d+)@@", line)
            if m:
                pending.append(int(m.group(1)))
            elif _PAGE_LINE.match(line) and pending:
                for idx in pending:
                    pages[idx] = line
                pending = []
    return [Table(doc_id, i, pages.get(i), rows) for i, rows in enumerate(parsed)]


def load_tables(doc_id: str, rebuild: bool = False) -> list[Table]:
    cache = TABLE_CACHE / f"{doc_id}.json"
    if cache.exists() and not rebuild:
        data = json.loads(cache.read_text(encoding="utf-8"))
        return [Table(doc_id, d["index"], d["page"], [tuple(r) for r in d["rows"]]) for d in data]
    tables = extract_tables(doc_id)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps([{"index": t.index, "page": t.page, "rows": t.rows} for t in tables]),
                     encoding="utf-8")
    return tables


def find_tables(tables: list[Table], must_contain: list[str], near_page: str | None = None) -> list[Table]:
    """Tables whose row labels include every string in ``must_contain`` (case-insensitive prefix)."""
    out = []
    for t in tables:
        labels = [r[0].lower() for r in t.rows]
        if all(any(l.startswith(m.lower()) for l in labels) for m in must_contain):
            if near_page is None or t.page == near_page:
                out.append(t)
    return out
