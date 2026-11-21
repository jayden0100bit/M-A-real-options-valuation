"""Helpers to turn downloaded SEC HTML filings into searchable plain text.

The text cache (``data/interim/text/<doc_id>.txt``) is derived and can be
rebuilt at any time with ``python src/sec_text.py``.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

ROOT = Path(__file__).resolve().parents[1]
SEC_DIR = ROOT / "data" / "raw" / "sec"
TEXT_DIR = ROOT / "data" / "interim" / "text"

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_BLOCK_TAGS = ["p", "div", "tr", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "table"]


def decode_html(raw: bytes | str) -> str:
    """Decode filing bytes: UTF-8 when valid, otherwise Windows-1252 (common in older EDGAR HTML)."""
    if isinstance(raw, str):
        s = raw
    else:
        try:
            s = raw.decode("utf-8")
        except UnicodeDecodeError:
            s = raw.decode("cp1252", errors="replace")
    # drop the EDGAR SGML wrapper lines (<TYPE>, <SEQUENCE>, <FILENAME>, <DESCRIPTION>): the
    # sequence number would otherwise look like a printed page number
    return re.sub(r"(?im)^<(TYPE|SEQUENCE|FILENAME|DESCRIPTION)>[^\n<]*$", "", s)


def html_to_text(html: bytes | str) -> str:
    """Convert filing HTML to text: one line per block element, cells split by ' | '."""
    soup = BeautifulSoup(decode_html(html), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # hidden inline-XBRL header blocks repeat facts; drop them
    for tag in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
        tag.decompose()
    for td in soup.find_all(["td", "th"]):
        td.append(" | ")
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.append("\n")
    text = soup.get_text()
    text = text.replace("\xa0", " ").replace("​", "")
    # older EDGAR HTML uses cp1252 numeric entities (e.g. &#146;) that decode to C1 controls
    text = re.sub(r"[\x80-\x9f]",
                  lambda m: bytes([ord(m.group(0))]).decode("cp1252", errors="replace"), text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        line = re.sub(r"(\|\s*){2,}", "| ", line)  # collapse empty cells
        line = re.sub(r"\(\s*\|\s*", "(", line)
        line = re.sub(r"\$\s*\|\s*", "$", line)
        line = re.sub(r"\|\s*\)", ")", line)
        line = re.sub(r"\|\s*%", "%", line)
        if line and line != "|":
            lines.append(line)
    return "\n".join(lines)


def doc_path(doc_id: str) -> Path:
    matches = list(SEC_DIR.glob(f"{doc_id}__*"))
    if len(matches) != 1:
        raise FileNotFoundError(f"expected one raw file for {doc_id}, found {matches}")
    return matches[0]


def load_text(doc_id: str, rebuild: bool = False) -> str:
    """Return the plain-text version of a downloaded filing, building the cache if needed."""
    cache = TEXT_DIR / f"{doc_id}.txt"
    if cache.exists() and not rebuild:
        return cache.read_text(encoding="utf-8")
    text = html_to_text(doc_path(doc_id).read_bytes())
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


_PAGE_LINE = re.compile(r"^(\d{1,3}|F-\d{1,3})$")


def paged_lines(doc_id: str, rebuild: bool = False) -> list[tuple[str, str]]:
    """Return ``(line, page)`` pairs for a filing.

    ``page`` is the printed page number of the page the line sits on: the next
    standalone page-number line found *outside* tables, since EDGAR documents put
    the page number in each page's footer. Numeric table cells are never taken as
    page numbers. Lines on pages without a printed number get ``""``.
    """
    import json
    cache = TEXT_DIR.parent / "paged" / f"{doc_id}.json"
    if cache.exists() and not rebuild:
        return [tuple(x) for x in json.loads(cache.read_text(encoding="utf-8"))]
    soup = BeautifulSoup(decode_html(doc_path(doc_id).read_bytes()), "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(style=re.compile(r"display:\s*none", re.I)):
        tag.decompose()
    for t in soup.find_all("table"):
        rows = []
        for tr in t.find_all("tr"):
            cells = [re.sub(r"\s+", " ", td.get_text(" ")).strip() for td in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if cells:
                rows.append("\x00" + " | ".join(cells))  # \x00 marks a table line
        t.replace_with(soup.new_string("\n" + "\n".join(rows) + "\n"))
    # physical page breaks: CSS page-break-before/after, or <hr>
    n_breaks = 0
    for tag in soup.find_all(style=re.compile(r"page-break-(before|after)\s*:\s*always", re.I)):
        marker = soup.new_string("\n\x01PB\n")
        if re.search(r"page-break-before", tag.get("style", ""), re.I):
            tag.insert_before(marker)
        else:
            tag.insert_after(marker)
        n_breaks += 1
    for hr in soup.find_all("hr"):
        hr.insert_after(soup.new_string("\n\x01PB\n"))
        n_breaks += 1
    for tag in soup.find_all(_BLOCK_TAGS):
        tag.append("\n")
    text = soup.get_text().replace("\xa0", " ").replace("​", "")
    text = re.sub(r"[\x80-\x9f]", lambda m: bytes([ord(m.group(0))]).decode("cp1252", errors="replace"), text)
    raw = [re.sub(r"[ \t]+", " ", l).strip() for l in text.splitlines()]
    raw = [l for l in raw if l and l != "\x00"]
    out = []
    if n_breaks:
        # one segment per physical page; its number is the standalone number found outside tables
        page_lines, page_no = [], ""
        for l in raw + ["\x01PB"]:
            if l == "\x01PB":
                out.extend((x, page_no) for x in page_lines)
                page_lines, page_no = [], ""
                continue
            clean = l.lstrip("\x00")
            if not l.startswith("\x00") and _PAGE_LINE.match(clean):
                page_no = clean
                continue
            page_lines.append(clean)
    else:
        # no break markers: a line belongs to the page whose number comes next
        pending = []
        for l in raw:
            clean = l.lstrip("\x00")
            if not l.startswith("\x00") and _PAGE_LINE.match(clean):
                out.extend((x, clean) for x in pending)
                pending = []
                continue
            pending.append(clean)
        out.extend((x, "") for x in pending)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


def build_all(rebuild: bool = False) -> None:
    for path in sorted(SEC_DIR.glob("*__*")):
        doc_id = path.name.split("__")[0]
        load_text(doc_id, rebuild=rebuild)
        print(f"text  {doc_id}")


if __name__ == "__main__":
    build_all(rebuild=True)
