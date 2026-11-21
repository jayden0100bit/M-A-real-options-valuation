"""HTTP download helper with bounded retries, shared by every fetch script.

* Retries **transient** failures only: timeouts, connection resets/refusals, and HTTP 429 / 5xx.
  Permanent errors (e.g. 403, 404) fail immediately, because retrying would not help.
* Exponential backoff: 2 s, 4 s, 8 s ... (``max_attempts`` attempts in total, default 4).
* Writes atomically (temporary file, then rename), so an interrupted download never leaves a
  truncated file that a later offline run would mistake for a complete one.
* Raises ``DownloadError`` with the URL, number of attempts and last error once retries run out.
"""
from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

TRANSIENT_HTTP = {408, 425, 429, 500, 502, 503, 504}


class DownloadError(RuntimeError):
    pass


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in TRANSIENT_HTTP
    if isinstance(exc, (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError)):
        return True
    return False


def fetch_bytes(url: str, headers: dict, timeout: int = 120, max_attempts: int = 4,
                backoff: float = 2.0, log=print) -> bytes:
    last = None
    for attempt in range(1, max_attempts + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - classified below
            last = exc
            if not _is_transient(exc):
                raise DownloadError(f"permanent error for {url}: {exc}") from exc
            if attempt < max_attempts:
                wait = backoff * 2 ** (attempt - 1)
                log(f"  transient error ({exc}); retry {attempt}/{max_attempts - 1} in {wait:.0f}s: {url}")
                time.sleep(wait)
    raise DownloadError(f"failed after {max_attempts} attempts: {url}: {last}")


def download_to(url: str, dest: Path, headers: dict, **kw) -> bytes:
    data = fetch_bytes(url, headers, **kw)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return data
