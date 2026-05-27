# Demo Build Requirements

*Created: 2026-05-26. This document defines the full build sequence for the earnings
demo analytical system. It governs all subsequent build work.*

*Build sequence: Framework → Data → Gather → Store → Sanity Check → Present → Analyze*

---

## Context

We are building a reusable earnings analysis framework, not just a one-time demo script.
The framework combines the sell-side analytical foundation from Anthropic's Earnings
Reviewer agent with a buy-side overlay designed for the workshop audience. The output is
two surfaces: an HTML frontend displaying the structured sell-side baseline, and a Cowork
analytical guide (EARNINGS-ANALYSIS-GUIDE.md) that allows free-form interrogation of the
database through the buy-side framework.

The demo on June 4 is a live session run against the PANW June 2 print using this system.
The test build runs against a prior PANW quarter to validate the framework before the print.

---

## Step 1 — Framework

### Sell-Side Foundation (from Earnings Reviewer Agent, Steps 5–8)

These are the analytical inputs. They produce structured data the buy-side framework
then interprets. Do not recreate them — leverage the existing skill.

| Step | What it produces |
|------|-----------------|
| Beat/Miss (Step 5) | Revenue, GM, EBITDA, EPS vs. consensus. Quantified delta and direction. |
| Segment/Geo (Step 6) | Breakdown by segment, geography, channel. What outperformed and by how much. |
| Margin Analysis (Step 7) | Gross → operating → net. Driver decomposition: pricing, mix, costs, leverage. |
| Guidance (Step 8) | Raised / lowered / maintained vs. prior and vs. Street. Management language. |

Steps 9–11 (model update, valuation/PT, rating) are sell-side specific and are not part
of this framework. They produce outputs that don't apply to a buy-side forming a view.

### Buy-Side Overlay (four dimensions)

These sit on top of the sell-side foundation and transform raw analytical inputs into
an investment view. All four are available in the analytical guide; the analyst invokes
them in whatever combination serves their question.

**Dimension 1 — Investment Horizon**

The single most important declaration before any analysis. It governs which signals
matter and which can be ignored.

| Horizon | Primary signals | What to weight |
|---------|----------------|---------------|
| Short (<3 months) | Guidance vs. consensus, gap fill, options positioning | Beat/miss magnitude, guidance raise/lower, near-term catalysts |
| Medium (6–18 months) | ARR trajectory, margin expansion path, re-rating potential | NGS ARR growth rate, billings as leading indicator, RPO coverage |
| Long (2–5 years) | Moat durability, TAM capture, platform dominance | Customer metrics, NRR trajectory, competitive displacement signals |

Horizon is not a fixed parameter — the analyst declares it when relevant and can
compare across horizons in a single session.

**Dimension 2 — Alpha Edge**

Not beat/miss vs. consensus (known, priced). The question is: what in this print is
the market over- or under-weighting in its reaction?

For PANW specifically:
- Is platformization compounding faster than the multiple implies?
- What did management emphasize in prepared remarks that analysts glossed over in Q&A?
- Is billings trajectory signaling acceleration or deceleration ahead of the revenue line?
- What forward-looking language did management use that the Street may have taken at face value?

The alpha edge dimension requires the analyst to bring a prior thesis — what they
believed before the print. The guide prompts for this; the analyst provides it.

**Dimension 3 — Peer Context**

PANW is not analyzed in isolation. The competitive set is CRWD, FTNT, ZS. The question
is not absolute performance but relative positioning on the platform consolidation trade.

Key signals:
- NRR and land-and-expand velocity vs. peers
- Customer count growth and churn signals
- Billings and RPO relative to competitive commentary
- Management language about competitive wins and displacement

For a market leader: is the moat widening or narrowing? This shows up in customer
metrics before it shows up in multiples.

**Dimension 4 — Sentiment and Positioning**

Not an informational edge — a positioning edge. Explains asymmetric reactions to the
same print. Compatible with semi-strong EMH: the market prices known information
efficiently, but positioning creates asymmetric reaction profiles.

Components:
- Short interest and delta (who is set up short and by how much)
- Options skew and put/call ratio around the print (directional positioning)
- Implied volatility vs. realized (market's uncertainty premium)
- Form 4 filings (insider transactions in the 4–6 weeks around the print — alignment signal)

---

## Step 2 — Data Requirements

### What the sell-side skill actually needs (from reading the skill)

The earnings-analysis skill and its workflow.md specify the following inputs. These are
requirements, not assumptions.

| Skill step | Data required | Notes |
|-----------|--------------|-------|
| Step 4 (transcript read) | Full earnings call transcript, speaker-attributed | Not a summary — full text required |
| Step 5 (beat/miss) | Reported actuals + pre-earnings consensus estimates | Two separate sources |
| Step 5 (beat/miss) | Earnings press release | Actuals live here, not in transcript |
| Step 6 (segment/geo) | 10-Q or 10-K filing | Structured segment data |
| Step 6 (segment/geo) | Prior quarter 10-Q | For QoQ comparison |
| Step 7 (margin analysis) | 10-Q — current + 3 prior quarters | Trend requires history |
| Step 8 (guidance) | Press release — current quarter | New guidance |
| Step 8 (guidance) | Press release — prior quarter | Prior guidance for comparison |
| Step 8 (guidance) | Street consensus estimates | To assess sandbagging vs. stretch |
| Context | Investor presentation / supplemental data file | If available on IR site |

### What the buy-side additions need

| Dimension | Data required | Notes |
|-----------|--------------|-------|
| Horizon | No external data — analytical parameter | Declared by analyst, not pulled |
| Alpha edge | Stock price reaction to print | Open/close day of and day after |
| Alpha edge | Implied move (options) vs. actual move | Pre-print IV implies expected range |
| Peer context | Same materials as above for CRWD, FTNT, ZS | Most recent reported quarter each |
| Peer context | Key metrics: revenue growth, NGS ARR equiv, NRR, gross margin, billings | From peer 10-Qs |
| Sentiment | Short interest + delta | Two observations: ~2 weeks pre and post print |
| Sentiment | Put/call ratio around print | 1 week window around earnings |
| Sentiment | Options skew / IV vs. RV spread | Positioning vs. realized vol |
| Sentiment | Form 4 filings | 4–6 weeks pre and post print |

### Source mapping — confirmed after Alpha Vantage tier analysis

Alpha Vantage free tier (25 req/day) covers the sell-side foundation data cleanly.
The buy-side addition data requires alternative free sources. All sources confirmed
accessible without a paid subscription.

**Sell-side foundation — Alpha Vantage free tier:**

| Data element | Alpha Vantage endpoint | Notes |
|-------------|----------------------|-------|
| EPS actuals + analyst estimates + surprise | `EARNINGS` | Quarterly, includes beat/miss |
| Revenue estimates + analyst count | `EARNINGS_ESTIMATES` | Pre-earnings consensus |
| Income statement (revenue, margins) | `INCOME_STATEMENT` | Quarterly, normalized GAAP |
| Balance sheet | `BALANCE_SHEET` | Quarterly |
| Cash flow | `CASH_FLOW` | Quarterly |
| Company overview + key ratios | `COMPANY_OVERVIEW` | Refreshed on earnings day |
| Daily price history | `TIME_SERIES_DAILY` | Compact (100 days), free |

**Buy-side additions — Alpha Vantage premium (blocked on free tier):**

| Data element | Alpha Vantage endpoint | Tier | Alternative source |
|-------------|----------------------|------|--------------------|
| Earnings call transcript | `EARNINGS_CALL_TRANSCRIPT` | Premium ❌ | Seeking Alpha (free with account) |
| Insider transactions (Form 4) | `INSIDER_TRANSACTIONS` | Premium ❌ | SEC EDGAR full-text search |
| Historical put/call ratio | `HISTORICAL_PUT_CALL_RATIO` | Premium ❌ | CBOE / barchart.com |
| Historical options / IV | `HISTORICAL_OPTIONS` | Premium ❌ | barchart.com / market chameleon |
| Short interest | Not available | N/A | FINRA (finra.org, bi-monthly) |

**Summary:** Alpha Vantage handles all quantitative foundation data (financials, EPS
estimates, margins, price history) on the free tier — roughly 8–10 API calls for PANW
plus peers, well within the 25/day limit. Transcript, insider data, and options
positioning come from three supplemental free sources: Seeking Alpha, SEC EDGAR,
and CBOE/barchart.

### Schema design decision

**Do not finalize the database schema before gathering.** Schema follows data, not the
other way around. The format and field-level detail of each source (especially Alpha
Vantage and EDGAR) will determine what can realistically be stored. Gather raw first,
assess what exists, then design the schema to fit.

What the database must ultimately contain (to be confirmed against actual data):
- Transcript: full text, speaker-attributed, section-labeled (prepared remarks / Q&A)
- Financials: actuals vs. consensus, key metrics, QoQ and YoY deltas
- Segments: revenue by segment, growth rates, mix
- Guidance: current vs. prior vs. consensus, direction flag
- Margins: gross / operating / net, 4+ quarters of history
- Peers: same metric set as PANW financials, most recent quarter
- Sentiment: short interest, put/call, IV, Form 4 — with dates

---

## Step 3 — Gather

### Approach: Raw first, schema after

Land all data in `demo/data/raw/` exactly as it comes from each source — plain text,
CSV, JSON, whatever the source provides. Do not transform or normalize at this stage.
Once we have seen the actual data, Step 4 (Store) designs the schema to fit it.

### Test quarter: PANW Q2 FY26 (reported February 2025)

Q2 FY26 is the recommended test quarter. It is the most recent full quarter before the
June 2 print, the platform consolidation thesis applies fully, and all materials are
available. When the June 2 transcript drops, we update the primary data files and re-run.

*Note: PANW's fiscal year ends in July. Q3 FY26 is the quarter reporting June 2.*

### Gather sequence

**Phase A — Can start immediately (no June 2 dependency)**

| # | Data element | Source | Raw file |
|---|-------------|--------|---------|
| 1 | PANW Q2 FY26 earnings transcript | Seeking Alpha | transcript_PANW_Q2FY26.txt |
| 2 | PANW Q2 FY26 press release | investor.paloaltonetworks.com | press_release_PANW_Q2FY26.pdf/txt |
| 3 | PANW Q2 FY26 10-Q | SEC EDGAR | 10q_PANW_Q2FY26.txt |
| 4 | PANW Q1 FY26 press release (prior guidance) | investor.paloaltonetworks.com | press_release_PANW_Q1FY26.txt |
| 5 | PANW margin history — Q4 FY25 through Q2 FY26 | SEC EDGAR (10-Qs) | margins_PANW_history.csv |
| 6 | Consensus estimates for Q2 FY26 | Alpha Vantage MCP (test first) / Yahoo Finance | consensus_PANW_Q2FY26.csv |
| 7 | PANW stock price around Q2 print | Alpha Vantage MCP / Yahoo Finance | price_PANW_Q2FY26.csv |
| 8 | PANW Form 4 filings (±6 weeks of Q2 print) | SEC EDGAR full-text search | form4_PANW_Q2FY26.csv |
| 9 | PANW short interest around Q2 print | FINRA | short_interest_PANW.csv |
| 10 | PANW put/call + options skew around Q2 print | barchart.com / market chameleon | options_PANW_Q2FY26.csv |
| 11 | CRWD most recent quarter — transcript + 10-Q | Seeking Alpha + SEC EDGAR | transcript_CRWD_[q].txt, 10q_CRWD_[q].txt |
| 12 | FTNT most recent quarter — transcript + 10-Q | Seeking Alpha + SEC EDGAR | transcript_FTNT_[q].txt, 10q_FTNT_[q].txt |
| 13 | ZS most recent quarter — transcript + 10-Q | Seeking Alpha + SEC EDGAR | transcript_ZS_[q].txt, 10q_ZS_[q].txt |

**Phase B — After June 2 print**

| # | Data element | Source | Raw file |
|---|-------------|--------|---------|
| 14 | PANW Q3 FY26 earnings transcript | Seeking Alpha / PANW IR | transcript_PANW_Q3FY26.txt |
| 15 | PANW Q3 FY26 press release | investor.paloaltonetworks.com | press_release_PANW_Q3FY26.txt |
| 16 | PANW Q3 FY26 10-Q | SEC EDGAR | 10q_PANW_Q3FY26.txt |
| 17 | Consensus estimates for Q3 FY26 | Alpha Vantage MCP / Yahoo Finance | consensus_PANW_Q3FY26.csv |
| 18 | Sentiment data around June 2 print | FINRA + CBOE + SEC EDGAR | (same files, updated) |

### Alpha Vantage MCP calls for Phase A (PANW + peers)

All calls below are confirmed free tier. Estimated 13 API calls total — within the
25/day limit. Run PANW calls first, then one call per peer.

| Call # | Endpoint | Symbol | Purpose |
|--------|----------|--------|---------|
| 1 | `EARNINGS` | PANW | EPS actuals + consensus, all quarters |
| 2 | `EARNINGS_ESTIMATES` | PANW | Revenue + EPS consensus with analyst count |
| 3 | `INCOME_STATEMENT` | PANW | Revenue, margins — quarterly history |
| 4 | `COMPANY_OVERVIEW` | PANW | Key metrics, ratios |
| 5 | `TIME_SERIES_DAILY` | PANW | Price around Q2 FY26 print date (Feb 13, 2025) |
| 6 | `INCOME_STATEMENT` | CRWD | Revenue, margins — most recent quarter |
| 7 | `EARNINGS` | CRWD | EPS + estimates |
| 8 | `INCOME_STATEMENT` | FTNT | Revenue, margins |
| 9 | `EARNINGS` | FTNT | EPS + estimates |
| 10 | `INCOME_STATEMENT` | ZS | Revenue, margins |
| 11 | `EARNINGS` | ZS | EPS + estimates |

**Manual pulls (not via Alpha Vantage):**

| # | Data | Source | Method |
|---|------|--------|--------|
| 12 | PANW Q2 FY26 transcript | Seeking Alpha | Search "PANW Q2 2025 earnings call transcript" |
| 13 | PANW Form 4 filings (Dec 2024 – Mar 2025) | SEC EDGAR | EDGAR full-text search, filter by PANW, form type 4 |
| 14 | PANW put/call ratio around Feb 13, 2025 | barchart.com | Historical options tab, PANW, date range |
| 15 | PANW short interest (Jan–Feb 2025) | FINRA | finra.org/investors/tools/securities-research |

---

## Step 4 — Store

### Decision: raw files first, schema after

Schema design follows data gathering. Once Phase A raw files are collected and assessed
in Step 5 (Sanity Check), the schema is designed to fit what actually exists. Do not
build the database before the raw data assessment is complete.

### Raw data directory

`demo/data/raw/` — all source files exactly as gathered. Never modify. If a file needs
correction, fix the gather process and re-pull.

### Database (to be built after sanity check)

SQLite at `demo/data/earnings.db`. Same pattern as branch-demo: rebuild script at
`demo/rebuild_db.py` for recovery. Schema and build sequence to be defined in Step 4b
once raw data is assessed.

Anticipated tables (subject to revision based on actual data): earnings_transcript,
financials, segments, guidance, margins, peers, sentiment. Field definitions deferred
until we have seen the actual data from Alpha Vantage, EDGAR, and Seeking Alpha.

---

## Step 5 — Sanity Check

Validation criteria before any presentation or analysis work begins.

### Data completeness
- All tables populated with at least one quarter of data
- No NULL values in required fields (actual, consensus, beat_miss_pct for financials)
- Transcript covers both prepared remarks and Q&A sections
- All four peers represented (PANW + CRWD + FTNT + ZS)
- Sentiment table has at least short interest and Form 4 data

### Data accuracy
- Beat/miss calculations verified: (actual - consensus) / consensus
- Guidance direction flags verified against prior guidance values
- Margin values cross-checked against segment revenue totals
- Peer metrics from same fiscal period (flag if quarters don't align)

### Cross-checks
- NGS ARR in financials table consistent with transcript references
- Billings figure consistent with press release
- Guidance range consistent with what management stated on the call

---

## Step 6 — Present

### HTML Frontend: Sell-Side Baseline Display

A static HTML file (`demo/earnings_baseline.html`) that displays the structured
sell-side analysis — the output of Steps 5–8 from the Earnings Reviewer framework —
in a clean, readable format. This is the starting point card shown before Cowork
interrogates the data with the buy-side framework.

**Design principles:**
- Static — no interactive weights or sliders (that lives in Cowork)
- Mobile-readable — room audience may view on phones
- Single page — no navigation
- Data-driven from the database — not hardcoded

**Sections:**

1. **Header** — Company, quarter, report date, stock reaction to the print

2. **Beat/Miss Summary** — Table: metric, consensus, actual, beat/miss %, direction.
   Highlight outperforms in green, misses in red. Key metrics first: revenue, NGS ARR,
   billings, EPS, gross margin.

3. **Segment Breakdown** — Table: segment, revenue, YoY growth, mix. Simple bar
   chart showing segment contribution.

4. **Margin Trajectory** — Sparkline or small table showing gross/operating margin
   over last 4 quarters. Direction is the signal, not the absolute level.

5. **Guidance Read** — Table: metric, prior guidance, new guidance, street consensus,
   direction flag (raised/lowered/maintained).

6. **Peer Snapshot** — Side-by-side table: PANW vs. CRWD vs. FTNT vs. ZS on revenue
   growth, NGS ARR / equivalent, NRR, gross margin. Most recent available quarter.

7. **Positioning Indicators** — Short interest, put/call ratio, key Form 4 transactions.
   Text summary, not a chart.

**Technology:** Single HTML file. Reads from a JSON data file extracted from the
database (`demo/data/baseline_data.json`). Chart.js for the margin sparkline and
segment bar. No external dependencies beyond Chart.js CDN.

---

## Step 7 — Analyze

### EARNINGS-ANALYSIS-GUIDE.md

The analytical guide for Cowork sessions. Same pattern as branch-demo's
WHAT-IF-GUIDE.md. Loaded at the start of every analytical session.

**Contents:**

1. **Database reference** — Schema summary, table names, key fields, how to query.
   What data is available and what quarter(s) it covers.

2. **Sell-side foundation** — What the Steps 5–8 analysis covers and how to access
   it in the database. Reference to earnings_baseline.html for the structured display.

3. **Buy-side framework** — All four dimensions defined precisely (horizon, alpha edge,
   peer context, sentiment/positioning) with instructions for how to apply each one.

4. **Horizon reference table** — Which database fields are most relevant at each horizon.
   Short: guidance fields, beat/miss on billings. Medium: NGS ARR trajectory, margin
   expansion, RPO coverage. Long: NRR, customer growth, moat indicators.

5. **Analytical patterns** — Reusable prompt patterns for common analytical questions:
   - Horizon-conditional read: "Given a [horizon] position, what does this print say?"
   - Peer comparison: "How does PANW's [metric] compare to the competitive set?"
   - Guidance credibility: "Is management sandbagging or stretching? What's the evidence?"
   - Alpha question: "What in this print is the market likely over- or under-weighting?"
   - Sentiment synthesis: "Given this transcript analysis, how does the positioning context change the risk/reward?"

6. **Source hierarchy** — Database first. Transcript text second. Web search only for
   context not in the database, with attribution.

7. **Output style** — Investment-grade, direct, no hedging for its own sake. State
   the view, state the evidence, state what would change the view.

---

## Build Sequence and Dependencies

| Step | Depends on | June 2 dependent? |
|------|-----------|------------------|
| Framework | Nothing | No |
| Data requirements | Framework | No |
| Gather | Data requirements | Partial (sentiment) |
| Store | Gather | Partial (sentiment) |
| Sanity check | Store | No |
| Present (HTML) | Store + Sanity check | No |
| Analyze (Guide) | Framework + Store | No |

The framework and data requirements can be locked now. Gathering and storing can begin
immediately for all non-sentiment data using the prior quarter. Sentiment data and the
June 2 transcript slot in after June 2.

---

## Open Questions

1. Which prior PANW quarter for the test build? Q3 FY25 (May 2025) is the recommendation
   — recent enough that the platform thesis applies, distant enough that we're not
   competing with the June 2 print.

2. Consensus data source for beat/miss calculations — public options include Visible Alpha,
   LSEG, or proxies from analyst note summaries. Need a source accessible without a paid
   terminal.

3. Peer quarter alignment — CRWD, FTNT, ZS fiscal years don't align with PANW's. Flag
   mismatches in the database and in the HTML display.

4. HTML FE build approach — generated from Python script reading the database (same
   pattern as branch-demo's viz/generate.py), or hand-built from the JSON export?
   Recommendation: Python script for repeatability.
