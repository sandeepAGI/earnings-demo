# Manual Input Files

This folder holds source PDFs that cannot be retrieved via API and must be sourced manually.
`gather.py` checks for required files here before running. If any are missing, it fails loudly
with instructions on where to get them.

`gather.py` extracts structured data from these PDFs via the Claude API (base64 PDF → structured
JSON prompt → `demo/data/raw/`). Do not write to `demo/data/raw/` directly.

---

## Required Files — Q3 FY26 (Active Quarter)

All three files are already present for the June 2, 2026 print.

### 1. `Supplemental Financial Information Q3'26_vF.pdf`

**What:** PANW Q3 FY26 supplemental financial data — 8-quarter KPI history, ARR, deferred revenue,
platformized customers, margin trends.

**Where to get it:** PANW Investor Relations: https://investors.paloaltonetworks.com → Financials → Quarterly Results

---

### 2. `Q3'26 Earnings Presentation vF (6).pdf`

**What:** Q3 FY26 earnings presentation slides — beat/miss summary, guidance, segment metrics.

**Where to get it:** Same IR page as above.

---

### 3. `Palo Alto Networks Inc.(PANW-US) Q3 2026 Earnings Call 2-June-2026 4_30 PM ET.pdf`

**What:** Full transcript PDF of the Q3 FY26 earnings call (June 2, 2026, 4:30 PM ET).

**Where to get it:** Transcript services (AlphaSense, Seeking Alpha, S&P Capital IQ) or
the PANW IR events page once the PDF becomes available.

---

## Process

1. Place the three PDFs above in this folder with the exact filenames shown.
2. Run `python demo/data/gather.py` from the project root.
3. `gather.py` validates each PDF (present, non-zero size), then submits to the Claude API
   for structured extraction, writing ~20 JSON/text files to `demo/data/raw/`.
4. If a file fails validation, `gather.py` exits loudly — it does not proceed with partial data.

---

## Prior Quarter Reference (Q2 FY26)

Q2 FY26 source PDFs are gitignored (`.gitignore` excludes `*.pdf`). The Q2 FY26 raw files
extracted from those PDFs remain in `demo/data/raw/` under `panw_q2fy26_*` names and serve
as historical context in the database.
