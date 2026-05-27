# Manual Input Files

This folder holds source files that cannot be retrieved via API and must be sourced manually.
`gather.py` checks for required files here before running. If any are missing, it fails loudly
with instructions on where to get them.

Files placed here are ingested by `gather.py` → validated → written to `demo/data/raw/`.
Do not write to `demo/data/raw/` directly for manually sourced content.

---

## Required Files

### 1. `panw_q2fy26_transcript.txt`

**What:** Full text of the PANW Q2 FY26 earnings call (February 17, 2026).

**Where to get it:**
- PANW Investor Relations: https://investors.paloaltonetworks.com → Events & Presentations
- Seeking Alpha (search "PANW Q2 2026 earnings call transcript")
- The Motley Fool transcripts section

**Format:** Plain text. Paste the full transcript including prepared remarks and Q&A.
Remove any HTML tags if copying from a web page. The file should be UTF-8 encoded.

**Minimum size:** ~15,000 characters (a typical earnings call is 8,000–20,000 words).
`gather.py` will reject the file if it is under 5,000 characters.

---

### 2. `panw_q2fy26_press_release_supplement.json`

**What:** Non-GAAP metrics, guidance, and stock reaction data from the Q2 FY26 press release.
FMP's income statement endpoint provides GAAP P&L only. This file supplies the rest.

**Where to get it:**
- Start from the template at `panw_q2fy26_press_release_supplement.TEMPLATE.json` in this folder.
- Fill in values from the PANW Q2 FY26 press release PDF (available at PANW IR above).
- Save the completed file as `panw_q2fy26_press_release_supplement.json`.

**Fields required (see template for full structure):**
- Non-GAAP gross margin %
- Non-GAAP operating income and margin %
- Non-GAAP EPS diluted
- FCF and FCF margin %
- Deferred revenue (current and long-term)
- Platformized customers (from earnings call)
- Guidance for Q3 FY26 (revenue range, EPS range, NGS ARR range)
- Guidance for FY26 full year
- Stock price reaction (close on earnings date, prior close)

---

## Process

1. Save required files to this folder with the exact filenames above.
2. Run `python demo/data/gather.py` from the project root.
3. `gather.py` validates each manual file (present, not empty, meets minimum size).
4. Validated files are copied to `demo/data/raw/` and used in the DB rebuild.

If a file fails validation, `gather.py` prints the reason and exits — it does not proceed
with partial data.
