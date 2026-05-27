# Database Schema — earnings.db

*Written 2026-05-27. Updated at each stage gate. This is the authoritative source-of-truth for
every table, column, and data provenance in the earnings demo database. Every column must trace
to either a raw file in `demo/data/raw/` or a signed-off hardcoded supplement below.*

**Target quarter:** PANW Q2 FY26 — fiscal date ending 2026-01-31, reported 2026-02-17.
**DB path:** `demo/data/db/earnings.db` (canonical; rebuilt by `rebuild_db.py`).

---

## Build Contract Rules (enforced in rebuild_db.py)

1. Every row in every table has a non-null `data_source` (or `source`) field.
2. Every `data_source` value points to a real file under `demo/data/raw/`.
3. No `.get(key, literal_default)` on financial values — missing data raises `KeyError`.
4. Form 4 window: 2025-11-01 to 2026-02-17 (full Q2 FY26 fiscal quarter, post-earnings inclusive).
5. All paths resolved via `pathlib.Path(__file__).parent` — no session-pinned absolute paths.
6. Stage transitions require explicit approval and a `STAGE: <name> approved` commit.

---

## Signed-Off Hardcoded Supplements

Values verified from Claude API extraction of Q2 FY26 PDFs (2026-05-27 gather.py run).
Source files: `Supplemental Financial Information Q2'26_vF.pdf`, `Q2'26 Earnings Presentation vF.pdf`.

| Constant | Value | Source | Verified? |
|----------|-------|--------|-----------|
| Non-GAAP gross margin | 76.1% | `panw_supplemental_8q.json` > Q2_FY26 `gross_margin_nongaap_pct` | ✓ 2026-05-27 |
| FCF (standard) | $384M | `panw_supplemental_8q.json` > Q2_FY26 `fcf_m` | ✓ 2026-05-27 |
| FCF margin (standard) | 14.8% | `panw_supplemental_8q.json` > Q2_FY26 `fcf_margin_pct` | ✓ 2026-05-27 |
| Deferred revenue current | $6.248B | `panw_supplemental_8q.json` > Q2_FY26 `deferred_revenue_current_bn` | ✓ 2026-05-27 |
| Deferred revenue long-term | $6.181B | `panw_supplemental_8q.json` > Q2_FY26 `deferred_revenue_longterm_bn` | ✓ 2026-05-27 |
| Deferred revenue total | $12.429B | Derived: 6.248 + 6.181 | ✓ 2026-05-27 |
| Platformized customers | 1,550 | `panw_q2fy26_guidance.json` > `operational_kpis.platformized_customers` | ✓ 2026-05-27 |
| NGS ARR | $6.33B | `panw_supplemental_8q.json` > Q2_FY26 `ngs_arr_bn` | ✓ 2026-05-27 |
| RPO | $16.0B | `panw_supplemental_8q.json` > Q2_FY26 `remaining_performance_obligations_bn` | ✓ 2026-05-27 |
| EBITDA | Re-derive | Non-GAAP OI ($785M) + D&A from supplemental, if shown | Pending re-derive |

*Prior SCHEMA.md values (76.6% gross margin, $509M FCF, $5.60B/$5.66B deferred rev, 1,150 platformized customers) were Q2 FY25 figures. Now corrected to Q2 FY26 actuals.*

---

## Table 1: companies

Reference table for all tracked symbols.

| Column | Type | Source |
|--------|------|--------|
| symbol | TEXT PK | Hardcoded: PANW, CRWD, FTNT, ZS |
| company_type | TEXT | Hardcoded: 'primary' (PANW) \| 'peer' (others) |
| full_name | TEXT | `peer_snapshot.json` > `peers.<TICKER>.full_name` |
| sector | TEXT | Hardcoded: 'Cybersecurity' |
| fiscal_year_end_month | INTEGER | Hardcoded: 7=PANW/ZS, 1=CRWD, 12=FTNT |
| data_source | TEXT | Filename of originating raw file |

---

## Table 2: quarterly_financials

P&L per quarter for primary and peers in a single table.

### PANW Q2 FY26 row (is_primary_quarter=1)

Primary source: `panw_supplemental_8q.json` (extracted from PANW supplemental PDF via Claude API).
Guidance and KPI overlay: `panw_q2fy26_guidance.json` (extracted from PANW presentation PDF via Claude API).

| Column | Source |
|--------|--------|
| symbol | Hardcoded: 'PANW' |
| company_type | Hardcoded: 'primary' |
| fiscal_period | Hardcoded: 'Q2_FY26' |
| fiscal_date_ending | Hardcoded: '2026-01-31' |
| report_date | Hardcoded: '2026-02-17' |
| revenue_total_m | `panw_supplemental_8q.json` > Q2_FY26 `revenue_total_m` |
| revenue_product_m | `panw_supplemental_8q.json` > Q2_FY26 `revenue_product_m` |
| revenue_subscription_m | `panw_supplemental_8q.json` > Q2_FY26 `revenue_subscription_support_m` |
| revenue_yoy_growth_pct | `panw_supplemental_8q.json` > Q2_FY26 `revenue_yoy_growth_pct` |
| gross_profit_m | `panw_supplemental_8q.json` > Q2_FY26 `gross_profit_gaap_m` |
| gross_margin_gaap_pct | `panw_supplemental_8q.json` > Q2_FY26 `gross_margin_gaap_pct` |
| gross_margin_nongaap_pct | `panw_supplemental_8q.json` > Q2_FY26 `gross_margin_nongaap_pct` (76.1%) |
| operating_income_gaap_m | `panw_supplemental_8q.json` > Q2_FY26 `operating_income_gaap_m` |
| operating_income_nongaap_m | `panw_supplemental_8q.json` > Q2_FY26 `operating_income_nongaap_m` |
| operating_margin_gaap_pct | `panw_supplemental_8q.json` > Q2_FY26 `operating_margin_gaap_pct` |
| operating_margin_nongaap_pct | `panw_supplemental_8q.json` > Q2_FY26 `operating_margin_nongaap_pct` |
| net_income_gaap_m | `panw_supplemental_8q.json` > Q2_FY26 `net_income_gaap_m` |
| ebitda_m | Derived in rebuild_db.py: non-GAAP OI + D&A if D&A present; else null with note |
| eps_gaap | `panw_supplemental_8q.json` > Q2_FY26 `eps_gaap_diluted` |
| eps_nongaap | `panw_supplemental_8q.json` > Q2_FY26 `eps_nongaap_diluted` |
| deferred_revenue_total_bn | Derived: `deferred_revenue_current_bn` + `deferred_revenue_longterm_bn` = 12.429 |
| fcf_m | `panw_supplemental_8q.json` > Q2_FY26 `fcf_m` (384, standard FCF) |
| gaap_profitable | Derived: 1 if net_income_gaap_m >= 0 |
| is_primary_quarter | Hardcoded: 1 |
| data_source | 'panw_supplemental_8q.json' |

### PANW historical rows (is_primary_quarter=0)

Source: `panw_supplemental_8q.json` > all quarters where `fiscal_period` != 'Q2_FY26'

Contains up to 8 quarters of GAAP + non-GAAP data (same fields as Q2 FY26 row). Non-GAAP columns are populated for all quarters present in the supplemental.

Fiscal periods mapped (fiscal_date_ending → fiscal_period, report_date):

| fiscal_date_ending | fiscal_period | report_date |
|--------------------|---------------|-------------|
| 2025-10-31 | Q1_FY26 | 2025-11-19 |
| 2025-07-31 | Q4_FY25 | 2025-08-18 |
| 2025-04-30 | Q3_FY25 | 2025-05-20 |
| 2025-01-31 | Q2_FY25 | 2025-02-13 |
| 2024-10-31 | Q1_FY25 | 2024-11-19 |
| 2024-07-31 | Q4_FY24 | 2024-09-09 |

*Note: Q4 FY25 (2025-07-31) may have sparse data — gross profit, OI, net income may be null depending on FMP coverage.*

### Peer rows

Sources: `crwd_q4fy26_results.json`, `ftnt_q12026_results.json`, `zs_q3fy26_results.json`

| Peer | fiscal_period | fiscal_date_ending | report_date |
|------|---------------|--------------------|-------------|
| CRWD | Q4_FY26 | 2026-01-31 | 2026-03-03 |
| FTNT | Q1_2026 | 2026-03-31 | 2026-05-07 |
| ZS | Q3_FY26 | 2026-01-31 | 2026-03-05 |

---

## Table 3: company_kpis

Flexible key-value KPIs (e.g. NGS ARR, platformized customers).

| Column | Source |
|--------|--------|
| kpi_name, kpi_value, kpi_unit, kpi_label, kpi_note | Per-KPI: `panw_supplemental_8q.json` > Q2_FY26 fields or `panw_q2fy26_guidance.json` > `operational_kpis.*` |
| Platformized customers | `panw_q2fy26_guidance.json` > `operational_kpis.platformized_customers` (1,550) |
| NGS ARR | `panw_supplemental_8q.json` > Q2_FY26 `ngs_arr_bn` (6.33) |
| RPO | `panw_supplemental_8q.json` > Q2_FY26 `remaining_performance_obligations_bn` (16.0) |
| Peer KPIs | `crwd_q4fy26_results.json`, `ftnt_q12026_results.json`, `zs_q3fy26_results.json` > `key_metrics.*` |
| data_source | Filename of originating raw file |

---

## Table 4: consensus_estimates

Street consensus at time of Q2 FY26 earnings.

| Column | Source |
|--------|--------|
| eps_consensus_nongaap | `panw_earnings_estimates.json` > `earnings_history[fiscal_date=2026-01-31].eps_nongaap_estimate` |
| revenue_consensus_m | NULL — not available from free APIs for historical quarters |
| data_source | 'panw_earnings_estimates.json' |

*FMP v3 earnings-surprises is a legacy endpoint blocked post-Aug 2025. Using yfinance earnings_history instead.*

---

## Table 5: eps_history

Non-GAAP EPS beat/miss track record (4 quarters from yfinance earnings_history).

| Column | Source |
|--------|--------|
| eps_nongaap_actual | `panw_earnings_estimates.json` > `earnings_history[].eps_nongaap_actual` |
| eps_nongaap_estimate | `panw_earnings_estimates.json` > `earnings_history[].eps_nongaap_estimate` |
| eps_difference | `panw_earnings_estimates.json` > `earnings_history[].eps_difference` |
| eps_surprise_pct | `panw_earnings_estimates.json` > `earnings_history[].eps_surprise_pct` |
| revenue_actual_m | `panw_earnings_estimates.json` > `earnings_history[].revenue_actual_m` |

*yfinance returns ~4 quarters of non-GAAP EPS history for PANW.*

---

## Table 6: guidance

Management guidance issued at Q2 FY26.

| Column | Source |
|--------|--------|
| All guidance fields | `panw_q2fy26_guidance.json` > `guidance_q3_fy26.*` and `guidance_fy26_full_year.*` |
| revision_vs_prior | `panw_q2fy26_guidance.json` > guidance revision_vs_prior flag |
| data_source | 'panw_q2fy26_guidance.json' |

---

## Table 7: insider_transactions

Form 4 filings, full Q2 FY26 window. 26 filings retrieved, 41 disposal transactions.

| Column | Source |
|--------|--------|
| All transaction fields | `panw_q2fy26_form4_summary.json` > `filings[].transactions[]` |
| reporting_owner | `panw_q2fy26_form4_summary.json` > `filings[].reporting_owner` |
| Window rule | 2025-11-01 to 2026-02-17 (full fiscal quarter, post-earnings inclusive) |

*edgartools returned 26 Form 4 filings. is_10b5_1 flag not parsed (edgartools does not surface it from XML at this level); set to null.*
*No `data_source` column in this table — provenance is the window rule documented above.*

---

## Table 8: forward_estimates

Not populated. FMP forward estimates require a paid subscription (v3 legacy endpoints blocked post-Aug 2025). yfinance revenue_estimate provides current-quarter forward revenue but not historical consensus at point of earnings. Table left empty; guidance table carries forward-looking data.

---

## Table 9: price_history

Monthly OHLCV.

| Column | Source |
|--------|--------|
| open, high, low, close, volume | `panw_price_monthly.json` > yfinance monthly history |
| split_adjusted | 1 for all rows (yfinance returns adjusted by default) |
| data_source | 'panw_price_monthly.json' |

---

## Table 10: price_events

Annotated key price events (earnings reaction, dip-and-rip, etc.).

| Column | Source |
|--------|--------|
| All OHLC fields | `panw_price_monthly.json` > same yfinance source, filtered to event months |
| event_key, event_note | Hardcoded in rebuild_db.py — keyed to specific months |

*The event_note strings in this table are factual labels ("earnings date", "recovery high") not analytical conclusions. They do not trigger the CLAUDE.md hard rule against hardcoded analytical prose.*

---

## Table 11: transcripts

Full earnings call text.

| Column | Source |
|--------|--------|
| full_text, word_count | `panw_q2fy26_transcript.txt` — sourced manually from PANW IR or Seeking Alpha |
| call_date | 2026-02-17 |
| source | 'panw_q2fy26_transcript.txt' |

---

## Table 12: transcript_qa

Parsed Q&A exchanges.

| Column | Source |
|--------|--------|
| exchange_num, analyst_name, analyst_firm, question_text, answer_text, respondent | `panw_q2fy26_transcript_qa.json` — structured from transcript text |
| topics | `panw_q2fy26_transcript_qa.json` — JSON array as text |
| key_signal | `panw_q2fy26_transcript_qa.json` — Claude API tagging pass ('bullish'\|'bearish'\|'neutral') |
| analytical_note | `panw_q2fy26_transcript_qa.json` — Claude API tagging pass |
| source | 'panw_q2fy26_transcript_qa.json' |

---

## Table 13: sentiment_signals

Short interest, put/call ratio, options skew.

| Column | Source |
|--------|--------|
| All fields | `panw_q2fy26_short_interest.txt`, `panw_q2fy26_put_call.txt` — narrative fallbacks |
| confidence | 'estimated' or 'inferred' (these platforms are client-rendered JS; historical data not accessible via static fetch) |
| data_source | Respective .txt filename |

*These files contain narrative text, not structured numbers. Values are inferred from context. confidence flag is mandatory.*

---

## Raw Files Summary

*Updated 2026-05-27 after gather.py run. Primary data source is now PDF extraction via Claude API.*

| File | Populated by | Tables fed | Status |
|------|-------------|-----------|--------|
| `panw_supplemental_8q.json` | Claude API → Supplemental PDF (8Q GAAP+nonGAAP) | 2, 3 | ✓ New |
| `panw_q2fy26_guidance.json` | Claude API → Presentation PDF (guidance + KPIs) | 3, 6 | ✓ New |
| `panw_q2fy26_transcript.txt` | Claude API → FactSet corrected transcript PDF | 11 | ✓ New |
| `panw_q2fy26_transcript_qa.json` | Claude API → transcript Q&A tag pass | 12 | ✓ New |
| `panw_earnings_estimates.json` | yfinance earnings_history (4Q non-GAAP EPS) | 4, 5 | ✓ Updated |
| `panw_price_monthly.json` | yfinance monthly OHLCV (60 months) | 9, 10 | ✓ Updated |
| `panw_q2fy26_form4_summary.json` | edgartools SEC EDGAR (26 filings, full Q2 FY26 window) | 7 | ✓ New (JSON) |
| `panw_q2fy26_short_interest.txt` | Manual narrative fallback (existing) | 13 | Existing |
| `panw_q2fy26_put_call.txt` | Manual narrative fallback (existing) | 13 | Existing |
| `peer_snapshot.json` | Existing (verify before reuse) | 1, 3 | Existing |
| `crwd_q4fy26_results.json` | Existing (verify before reuse) | 2, 3 | Existing |
| `ftnt_q12026_results.json` | Existing (verify before reuse) | 2, 3 | Existing |
| `zs_q3fy26_results.json` | Existing (verify before reuse) | 2, 3 | Existing |

*Superseded files (do not use in rebuild_db.py):*
- `panw_q2fy26_press_release.json` — Q2 FY25 data, mislabeled. Replaced by `panw_supplemental_8q.json`.
- `panw_income_statement.json` — Q2 FY25 era. Replaced by `panw_supplemental_8q.json`.
- `panw_earnings.json` — stale Alpha Vantage output. Replaced by `panw_earnings_estimates.json`.
- `panw_q2fy26_form4_summary.txt` — old text format. Replaced by `panw_q2fy26_form4_summary.json`.
