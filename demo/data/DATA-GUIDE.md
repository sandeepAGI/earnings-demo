# Data Guide — Earnings Demo

*Last updated: 2026-06-03. Maintained alongside raw data files. Update after every data pull.*

---

## Purpose

This document is the single reference for all data in `demo/data/`. It covers:
1. What exists, what each file contains, and any quality caveats
2. What is still missing
3. How to update everything for the live Q3 FY26 print after June 2

If you are arriving at this file the evening before the workshop: go to **Phase B: Live Quarter Update** below.

---

## Current State

**Live quarter:** PANW Q3 FY26 (fiscal period ending April 30, 2026, reported June 2, 2026).
Q3 FY26 PDFs are in `demo/data/manual/`. Pipeline refresh in progress (June 3).

**Prior quarter (reference):** PANW Q2 FY26 (fiscal period ending January 31, 2026, reported
February 17, 2026). Q2 FY26 raw files remain in `demo/data/raw/panw_q2fy26_*` as historical context.

**Pipeline:** Fully automated — `demo/data/gather.py` (PDF extraction + yfinance + edgartools +
SEC EDGAR XBRL) → `demo/data/rebuild_db.py` (SQLite, 13 tables) → tests → analysis scripts →
`demo/generate_baseline.py` (HTML dashboard). Alpha Vantage was deprecated (all v3 endpoints
blocked Aug 2025); replaced by yfinance + edgartools + SEC EDGAR XBRL.

**Database:** `demo/data/db/earnings.db` — rebuilt on each run. Q2 FY26 build: 200 rows, 39/39
provenance tests passing. Q3 FY26 rebuild pending pipeline run.

---

**Note on the File Manifest below:** The manifest was written during Q2 FY26 pipeline development
(May 2026) and documents the Q2 FY26 source files. Many filenames and source notes are Q2-specific.
The Q3 FY26 raw files will follow the same structure with `panw_q3fy26_` naming. Treat the manifest
as a reference for data lineage and quality notes, not as a current file inventory.

---

## File Manifest

### `raw/panw_earnings.json`
**Source:** Alpha Vantage EARNINGS endpoint (pulled 2026-05-27)
**Contains:** Full quarterly EPS history — reported vs. estimated, surprise %, report dates. ~50 quarters.
**Key rows for demo:** Q2 FY26 (fiscalDateEnding 2025-01-31): $0.38 actual vs $0.38 estimate (GAAP EPS).
**Quality note:** This is GAAP EPS. Consensus tracked non-GAAP (~$0.77-0.81). See panw_earnings_estimates.json for non-GAAP consensus.
**Coverage:** Complete through Q3 FY26 (Feb 2026). ✅

---

### `raw/panw_earnings_estimates.json`
**Source:** Alpha Vantage EARNINGS_ESTIMATES endpoint (pulled 2026-05-27)
**Contains:** Forward and historical EPS and revenue consensus estimates, quarterly and annual.
**Key row for demo:** Q2 FY26 (date 2025-01-31): EPS consensus $0.7793, revenue consensus $2.24B (43 analysts).
**Quality note:** These are non-GAAP EPS estimates. Actual non-GAAP EPS was $0.81 — a +3.9% beat. Revenue actual $2.257B vs $2.240B estimate — +0.8% beat.
**Coverage:** Full history back to 2017. ✅

---

### `raw/panw_income_statement.json`
**Source:** Alpha Vantage INCOME_STATEMENT endpoint (pulled 2026-05-27), supplemented with press release
**Contains:** Quarterly P&L data — revenue, gross profit, operating income, EBITDA, net income. Key quarters extracted: Q2 FY26 (test), Q1 FY26, Q3 FY25, Q1 FY25, Q2 FY25 (year-ago comp).
**Key row:** Q2 FY26: Revenue $2,257.4M, GP $1,658.2M (73.5% GM), GAAP OI $240.4M, EBITDA $412.9M.
**Quality note:** Gross margin in this file is GAAP (73.5%). Press release reports non-GAAP gross margin of 76.6%. GAAP is correct for the financial model; use non-GAAP for Street comparison.
**Coverage:** Key quarters ✅. Full quarterly history available in Alpha Vantage full dataset but not extracted due to API limits. ⚠️

---

### `raw/panw_q2fy26_press_release.json`
**Source:** PANW official IR site (paloaltonetworks.com), scraped 2026-05-27
**Contains:** Complete Q2 FY26 financial results — full P&L, balance sheet snapshot, GAAP-to-nonGAAP reconciliation, beat/miss vs. consensus, guidance (Q3 and FY25 full year), geographic breakdown, mgmt quotes, stock reaction.
**This is the primary source for the demo.** All numbers here are from the official press release and are authoritative.
**Key analytical notes embedded:**
- GAAP OI +349% YoY is misleading — $175M of $187M improvement is litigation normalization (not operating leverage)
- Non-GAAP OI +13.5% YoY; non-GAAP operating margin 28.4% vs 28.6% — flat, not expanding
- Q3 EPS guidance $0.76-0.77 is below Q2 actual $0.81 — sequential step-down is likely why stock fell -3.5% AH
- NGS ARR $4.78B (+37%) is the primary platformization KPI; guided to decelerate to 33-34% for Q3
**Coverage:** ✅ Complete for Q2 FY26.

---

### `raw/panw_q2fy26_transcript.txt`
**Source:** The Motley Fool transcript, scraped 2026-05-27
**Contains:** Full earnings call — prepared remarks (Nikesh Arora, Dipak Golechha) plus complete Q&A (10 analyst exchanges).
**Key analytical themes in transcript:**
- Platformization acceleration (75 new in Q2 vs 45 YoY; 2-platform customers +50%; 3-platform +3x)
- XSIAM $1B cumulative bookings milestone
- QRadar >$100M bookings in Q2; partnership "couldn't have been better"
- Cortex Cloud announcement (Prisma Cloud + CDR + Cortex unified)
- Bear case: Andrew Nowinski (Wells Fargo) challenged net new ARR — declining YoY ex-QRadar for 2 consecutive quarters
- Gross margin pressure: one-time inventory write-off (~40 bps) + newer SaaS not at scale
- AI efficiency: 50% support case resolution time reduction; 50% contract labor reduction underway
- DeepSeek commentary: opportunity for AI security, not threat
- FCF deferred payment dynamics: entering FY26 with $2B deferred (increasing visibility)
**Coverage:** ✅ Complete. This is the primary input for the demo analytical session.

---

### `raw/panw_q2fy26_form4_summary.txt`
**Source:** SEC EDGAR Form 4 filings, fetched 2026-05-27
**Contains:** Insider transaction summary for Dec 2024 – Mar 2025. Key transactions:
- Nikesh Arora (CEO): Sold 788,396 shares at ~$182 avg = $143.7M on Feb 3-4 (10 days pre-earnings). Options exercise-and-sell under 10b5-1 plan adopted March 2024.
- Josh D. Paul (CAO): Sold 700 shares at $181.22 = $127K on Feb 3. Minimal.
- William D. Jenkins Jr. (President): Sold 2,401 shares at $203-208 on Feb 19 (6 days post-earnings). Stock had recovered from $187 to $203+.
**Key analytical note:** All transactions are under pre-scheduled 10b5-1 plans. CEO sales look alarming on surface; context shows routine option expiry management (options expired Dec 2025). This is the "looks bearish, isn't" signal for Move 2.
**Coverage:** ✅ Sufficient for demo. Lee Klarich (EVP) filings not fully parsed but follow same pattern.

---

### `raw/panw_q2fy26_put_call.txt`
**Source:** Barchart.com (static fetch), web search
**Contains:** Current put/call ratio (0.94 volume / 1.01 OI), narrative framing for Feb 2025, Phase B instructions.
**Quality note:** Historical Feb 2025 specific data is client-rendered on barchart.com — not accessible via static web fetch. File contains a pre-written narrative framing for Move 2 that is consistent with the known price action and options market context.
**Coverage:** ⚠️ Narrative fallback. Sufficient for demo.

---

### `raw/panw_q2fy26_short_interest.txt`
**Source:** FINRA, MarketBeat, Benzinga, web search
**Contains:** Current short interest data (3.11% float, 25.2M shares May 2026), estimated Feb 2025 context (5-7% float), narrative framing for Move 2, Phase B instructions.
**Quality note:** FINRA and Nasdaq short interest detail pages are client-rendered. File contains reasonable inference from directional data (Dec 2025: 6.65%, May 2026: 3.11% — declining trend; Feb 2025 likely in the 5-7% range).
**Coverage:** ⚠️ Estimated range, not point-in-time. Sufficient for demo narrative.

---

### `raw/peer_snapshot.json`
**Source:** Web search + public earnings reports (scraped 2026-05-27)
**Contains:** Most recent quarter results for CRWD, FTNT, ZS — revenue, ARR, margins, report dates, analytical read.
**Key comparisons:**
- Revenue growth: ZS +23%, CRWD +23%, FTNT +17%, PANW +14% — PANW slowest headline growth
- ARR: PANW NGS ARR $4.78B (+37%) > CRWD ending ARR $4.24B (+23%) — PANW winning ARR race
- Non-GAAP op margin: FTNT 39.2% (record), PANW 28.4%, ZS not GAAP profitable
- PANW slowest headline revenue growth but fastest NGS ARR growth — core investment tension
**Quality note:** Peer quarters are not perfectly contemporaneous with PANW Q2 FY26:
- CRWD Q4 FY25 reported March 4, 2025 (3 weeks after PANW)
- FTNT Q4 2024 reported February 6, 2025 (1 week before PANW)
- ZS Q2 FY25 reported March 5, 2025 (3 weeks after PANW)
**Coverage:** ✅ Sufficient for demo peer context. No detailed P&L for peers — use for narrative, not model.

---

## Still Missing (as of 2026-05-27)

### Sell-Side Foundation
| Item | Gap | Impact |
|------|-----|--------|
| PANW stock price time series | API rate limit hit; Yahoo Finance bot-blocked | Low — $187.68 close on report day from news search |
| PANW balance sheet (detailed) | Partial — key items in press_release.json | Medium — deferred revenue $11.26B is captured |
| PANW cash flow statement | Not pulled | Low — FCF $509M for Q2 is captured from PR |
| Peer P&L details (CRWD, FTNT, ZS) | Narrative only, no structured numbers | Low for demo — narrative read is sufficient |

### Buy-Side Sentiment Layer (Move 2)
| Item | Source | Status |
|------|--------|--------|
| Form 4 insider filings (Dec 2024 – Mar 2025) | SEC EDGAR | ✅ `raw/panw_q2fy26_form4_summary.txt` |
| Put/call ratio around Feb 13, 2025 | barchart.com | ⚠️ `raw/panw_q2fy26_put_call.txt` — historical data client-rendered, narrative fallback documented |
| Short interest and delta | FINRA/MarketBeat | ⚠️ `raw/panw_q2fy26_short_interest.txt` — historical data client-rendered, narrative fallback documented |

**Sentiment layer status:** Form 4 is fully usable and analytically rich (CEO sold $143M pre-earnings under 10b5-1 plan — excellent demo material on the "looks bearish, isn't" nuance). Put/call and short interest files contain narrative framings that can be read directly into Move 2 without specific historical figures.

---

## API Stack (current)

Alpha Vantage was deprecated in August 2025 — all v3 endpoints blocked on the free tier.
The current stack in `gather.py`:

- **Anthropic Claude API** — PDF extraction (supplemental, presentation, transcript → structured JSON)
- **yfinance** — EPS history (earnings_history), daily price bars, peer financials
- **edgartools** — SEC Form 4 insider transaction filings
- **SEC EDGAR XBRL frames API** — GAAP metric backfill for historical quarters (no auth required)

## Alpha Vantage Notes (historical — deprecated)

The notes below were accurate for May 2026 when Alpha Vantage was the primary data source.
Retained for reference on data lineage for the Q2 FY26 raw files.

- **Free tier:** 25 requests/day. Rate limit: 1 request/second.
- **Blocked on free tier:** EARNINGS_CALL_TRANSCRIPT, INSIDER_TRANSACTIONS, HISTORICAL_PUT_CALL_RATIO, HISTORICAL_OPTIONS.
- **Deprecated Aug 2025:** All v3 endpoints return 403 "Legacy Endpoint." Do not use.

---

## Phase B: Live Quarter Update

**Status as of June 3, 2026: IN PROGRESS.** Q3 FY26 print released June 2. All pipeline scripts
updated. Q3 FY26 PDFs are in `demo/data/manual/`. Running now.

**Phase B is now fully automated.** The manual steps documented below (May 2026) have been
replaced by `demo/data/gather.py`, which handles PDF extraction, yfinance data pulls, edgartools
Form 4 fetching, and SEC EDGAR XBRL backfill in a single script run.

### Current pipeline sequence (June 3, 2026)

```bash
python demo/data/gather.py                               # extract + pull all raw files
python demo/data/rebuild_db.py                           # build earnings.db (13 tables)
python -m pytest demo/data/tests/test_provenance.py -v  # validate 39 tests
python demo/data/analysis/run_earnings_analysis.py       # sell-side analysis JSON
python demo/data/analysis/run_buyside_analysis.py        # buy-side framework JSON
python3 demo/generate_baseline.py                        # regenerate HTML dashboard
```

### Remaining manual step: Sentiment capture (before June 4)

`panw_q3fy26_short_interest.txt` and `panw_q3fy26_put_call.txt` contain placeholders.
Capture live figures via Playwright before the workshop:

**Short interest:** MarketBeat PANW page → short interest % float and shares

- Save to: `demo/data/raw/panw_q3fy26_short_interest.txt`

**Put/call ratio:** Barchart PANW put-call-ratios page → volume P/C around June 2 print

- Save to: `demo/data/raw/panw_q3fy26_put_call.txt`

After both files are updated, re-run `rebuild_db.py` and `generate_baseline.py` to populate
the sentiment cards with real figures (confidence = actual, not placeholder).

### Final sanity check (June 4 morning)

1. Open `demo/earnings_baseline.html` — verify all numbers match Q3 FY26 press release
2. Read first 5 minutes of transcript — verify you can speak to the key themes
3. Start `python3 demo/server.py` and confirm Tab 3 chat loads with the live/online badge
4. Test one Tab 3 question end to end — confirm SSE streaming and Tavily search work

---

## What to Do If PANW Doesn't Report on June 2

If the earnings are delayed or the print is unusable (e.g., accounting restatement):

**Backup: PANW Q1 FY26 (October 31, 2024, reported November 19, 2024)**

- All the same data structure applies
- Peer context: use CRWD/FTNT/ZS quarters closest to November 2024
- Transcript: available on Motley Fool
- This is a lower-stakes quarter (no major announcements) but has all the right analytical structure

Alternatively, fall back to the Q2 FY26 test quarter data already in `raw/` — the demo is already built on it and it has excellent analytical texture (the +349% GAAP OI trap, the net new ARR bear case, the stock-fell-on-a-beat dynamic).

---

## Source Reference Card

| Data | URL | Auth Required |
|------|-----|---------------|
| PANW press releases | investors.paloaltonetworks.com/news-releases | None |
| Earnings call transcripts | fool.com/earnings/call-transcripts/ | None (but Motley Fool may gate) |
| Consensus estimates (historical) | Alpha Vantage EARNINGS_ESTIMATES | API key (free: 25/day) |
| EPS history | Alpha Vantage EARNINGS | API key |
| Income statement | Alpha Vantage INCOME_STATEMENT | API key |
| Price history | Alpha Vantage TIME_SERIES_DAILY | API key |
| SEC Form 4 filings | sec.gov/cgi-bin/browse-edgar | None |
| Put/call ratio | barchart.com/stocks/quotes/PANW/put-call-ratios | None (some pages may require login) |
| Short interest | finra.org / finra-markets.morningstar.com | None |

Alpha Vantage API key is configured in the Alpha Vantage MCP server in Cowork settings.

---

*Update this file after every data pull. Add quality notes when you spot anomalies.*
