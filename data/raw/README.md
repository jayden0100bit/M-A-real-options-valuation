# data/raw

Unmodified source documents downloaded from SEC EDGAR by `src/fetch_sources.py`.
**Do not edit these files.** Every processed figure points back to one of them by `source_id`.

| Path | Content |
|---|---|
| `sec/<source_id>__<original file name>` | Filing documents (10-K, 10-Q, 8-K and exhibits, 424B3 joint proxy statements/prospectuses), exactly as served by `https://www.sec.gov/Archives/edgar/data/...` |
| `xbrl/companyfacts_CIK<cik>_<label>.json` | SEC XBRL company-facts API responses (`https://data.sec.gov/api/xbrl/companyfacts/...`). Used only to cross-check figures parsed from the HTML. |
| `download_manifest.csv` | URL, size, SHA-256 and status of each downloaded file, with the time the manifest was written. |

The list of filings (CIK, accession number, document, purpose) is in `data/reference/filings_to_fetch.csv`.
To re-download:

```bash
export SEC_USER_AGENT="Your Name your.email@example.com"   # SEC fair-access policy asks for a contact
python src/fetch_sources.py           # only missing files
python src/fetch_sources.py --force   # everything
```

Then compare the new `sha256` values with the committed manifest. EDGAR documents for these accession numbers
should not change. A different hash means the parsed tables may have moved and `src/build_historical.py`
will stop on its page/table checks.

Total size is about 86 MB, and the largest single file (a 21CF 10-K) is about 10 MB.
