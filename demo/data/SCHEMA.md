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

These values appear in the press release narrative but are absent from structured JSON fields.
Each must be independently verified against the Q2 FY26 press release PDF before the rebuild runs.

| Constant | Value | Source statement | Verified? |
|----------|-------|-----------------|-----------|
| Non-GAAP gross margin | 76.6% | PANW Q2 FY26 press release text | Pending |
| FCF | $509.0M | PANW Q2 FY26 press release text | Pending |
| FCF margin | 22.5% | PANW Q2 FY26 press release text | Pending |
| Deferred revenue current | $5.60B | PANW Q2 FY26 press release text | Pending |
| Deferred revenue long-term | $5.66B | PANW Q2 FY26 press release text | Pending |
| Platformized customers | 1,150 | PANW Q2 FY26 earnings call transcript | Pending |
| EBITDA | TBD | Prior script used ~$412.9M approximation — re-derive for Q2 FY26 | Pending |

*"Pending" = verified against Q2 FY25 source; must be re-verified against actual Q2 FY26 press release.*

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

| Column | Source |
|--------|--------|
| symbol | Hardcoded: 'PANW' |
| company_type | Hardcoded: 'primary' |
| fiscal_period | Hardcoded: 'Q2_FY26' |
| fiscal_date_ending | Hardcoded: '2026-01-31' |
| report_date | Hardcoded: '2026-02-17' |
| revenue_total_m | `panw_q2fy26_press_release.json` > `income_statement.revenue.total` |
| revenue_product_m | `panw_q2fy26_press_release.json` > `income_statement.revenue.product` |
| revenue_subscription_m | `panw_q2fy26_press_release.json` > `income_statement.revenue.subscription_support` |
| revenue_yoy_growth_pct | `panw_q2fy26_press_release.json` > `income_statement.revenue.yoy_total.growth_pct` |
| gross_profit_m | `panw_q2fy26_press_release.json` > `income_statement.gross_profit` |
| gross_margin_gaap_pct | `panw_q2fy26_press_release.json` > `income_statement.gross_margin_pct` |
| gross_margin_nongaap_pct | **Hardcoded supplement** — 76.6% from press release text |
| operating_income_gaap_m | `panw_q2fy26_press_release.json` > `income_statement.gaap_operating_income` |
| operating_income_nongaap_m | `panw_q2fy26_press_release.json` > `income_statement.nongaap_operating_income` |
| operating_margin_gaap_pct | `panw_q2fy26_press_release.json` > `income_statement.gaap_operating_margin_pct` |
| operating_margin_nongaap_pct | `panw_q2fy26_press_release.json` > `income_statement.nongaap_operating_margin_pct` |
| net_income_gaap_m | `panw_q2fy26_press_release.json` > `income_statement.net_income_gaap` |
| ebitda_m | **Hardcoded supplement** — re-derive from Q2 FY26 press release (prior: ~$412.9M approx) |
| eps_gaap | `panw_q2fy26_press_release.json` > `income_statement.eps_gaap_diluted` |
| eps_nongaap | `panw_q2fy26_press_release.json` > `income_statement.eps_nongaap_diluted` |
| deferred_revenue_total_bn | **Hardcoded supplement** — $11.26B (5.60 + 5.66) from press release text |
| fcf_m | **Hardcoded supplement** — $509.0M from press release text |
| gaap_profitable | Derived: 1 if net_income_gaap_m >= 0 |
| is_primary_quarter | Hardcoded: 1 |
| data_source | 'panw_q2fy26_press_release.json' |

### PANW historical rows (is_primary_quarter=0)

Source: `panw_income_statement.json` > `quarterlyReports[]`

Columns populated: revenue_total_m, gross_profit_m, gross_margin_gaap_pct, operating_income_gaap_m, net_income_gaap_m, revenue_yoy_growth_pct (derived). All non-GAAP columns are NULL for historical rows — source file does not have them.

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
| kpi_name, kpi_value, kpi_unit, kpi_label, kpi_note | Per-KPI: `panw_q2fy26_press_release.json` > `key_metrics.*` or hardcoded supplement |
| Platformized customers | **Hardcoded supplement** — 1,150 from transcript |
| Peer KPIs | `crwd_q4fy26_results.json`, `ftnt_q12026_results.json`, `zs_q3fy26_results.json` > `key_metrics.*` |
| data_source | Filename of originating raw file |

---

## Table 4: consensus_estimates

Street consensus at time of Q2 FY26 earnings.

| Column | Source |
|--------|--------|
| eps_consensus_nongaap | `panw_earnings_estimates.json` > FMP earnings surprises (estimated EPS field) |
| eps_consensus_gaap | `panw_earnings_estimates.json` > FMP earnings surprises (if available) |
| revenue_consensus_m | `panw_earnings_estimates.json` > FMP earnings surprises (revenue estimate) |
| analyst_count | `panw_earnings_estimates.json` > FMP earnings surprises (analyst count if available) |
| data_source | 'panw_earnings_estimates.json' |

---

## Table 5: eps_history

GAAP EPS beat/miss track record.

| Column | Source |
|--------|--------|
| eps_gaap_actual | `panw_earnings_estimates.json` > FMP earnings surprises (actualEps field) |
| eps_gaap_estimated | `panw_earnings_estimates.json` > FMP earnings surprises (estimatedEps field) |
| eps_surprise | `panw_earnings_estimates.json` > FMP (difference field) |
| eps_surprise_pct | `panw_earnings_estimates.json` > FMP (surprisePercentage field) |

*FMP returns ~16 quarters of earnings surprise history. No separate `panw_earnings.json` needed.*

---

## Table 6: guidance

Management guidance issued at Q2 FY26.

| Column | Source |
|--------|--------|
| All guidance fields | `panw_q2fy26_press_release.json` > `guidance_q3_fy26.*` and `guidance_fy26_full_year.*` |
| revision_vs_prior | `panw_q2fy26_press_release.json` > guidance raise/maintain flag |
| data_source | 'panw_q2fy26_press_release.json' |

---

## Table 7: insider_transactions

Form 4 filings, full Q2 FY26 window.

| Column | Source |
|--------|--------|
| All transaction fields | `panw_q2fy26_form4_summary.txt` — parsed from edgartools output |
| Window rule | 2025-11-01 to 2026-02-17 (full fiscal quarter, post-earnings inclusive) |
| is_10b5_1_plan, plan_adoption_date | From Form 4 text, parsed by edgartools or noted in summary file |

*Prior script had 4 of 6 filings. edgartools will pull all filings in the window.*
*No `data_source` column in this table — provenance is the window rule documented above.*

---

## Table 8: forward_estimates

Consensus forward-year estimates.

| Column | Source |
|--------|--------|
| All fields | `panw_earnings_estimates.json` > FMP forward estimates (if available on free tier) |

*If FMP free tier does not return forward estimates, this table remains empty and the guidance table carries forward-looking data instead.*

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

| File | Populated by | Tables fed |
|------|-------------|-----------|
| `panw_q2fy26_press_release.json` | Manual (PANW IR PDF) + FMP income statement | 2, 3, 6 |
| `panw_income_statement.json` | FMP income statement endpoint | 2 (historical) |
| `panw_earnings_estimates.json` | FMP earnings surprises endpoint | 4, 5, 8 |
| `panw_price_monthly.json` | yfinance monthly OHLCV | 9, 10 |
| `panw_q2fy26_transcript.txt` | Manual — PANW IR or Seeking Alpha | 11 |
| `panw_q2fy26_transcript_qa.json` | Claude API tagging pass | 12 |
| `panw_q2fy26_form4_summary.txt` | edgartools (SEC EDGAR) | 7 |
| `panw_q2fy26_short_interest.txt` | Manual narrative fallback (existing) | 13 |
| `panw_q2fy26_put_call.txt` | Manual narrative fallback (existing) | 13 |
| `peer_snapshot.json` | Existing (verify before reuse) | 1, 3 |
| `crwd_q4fy26_results.json` | Existing (verify before reuse) | 2, 3 |
| `ftnt_q12026_results.json` | Existing (verify before reuse) | 2, 3 |
| `zs_q3fy26_results.json` | Existing (verify before reuse) | 2, 3 |
