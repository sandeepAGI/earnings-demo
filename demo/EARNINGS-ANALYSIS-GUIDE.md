# Earnings Analysis Guide — PANW Demo Session

This guide instructs an LLM (via Cowork or similar session) how to conduct a structured AI-assisted earnings analysis of Palo Alto Networks Q2 FY26. It is the analytical companion to `earnings_baseline.html` (the reference dashboard) and `demo_script.md` (the presenter script).

The demo is organized as two moves. **Move 1** (~10 min) is the sell-side foundation: use the financial data to form a view on what the quarter actually said. **Move 2** (~3 min) is the buy-side overlay: interpret the sentiment and positioning signals that explain why the stock moved the way it did despite the beat.

This guide covers both moves in full. Read it at the start of any demo or analytical session.

---

## Source Hierarchy and Attribution

Every claim must be traceable to a source. Use this priority order:

1. **Press release (primary).** `raw/panw_q2fy26_press_release.json` — official PANW IR site. All financial figures, guidance numbers, beat/miss calculations, and GAAP-to-non-GAAP reconciliations should be cited from here. When in doubt, the press release is authoritative.

2. **Earnings call transcript (qualitative).** `raw/panw_q2fy26_transcript.txt` — Motley Fool transcript of the Q2 FY26 call. Use for management narrative, analyst challenge points, and strategic context. When quoting directly, use "per the earnings call" or "per the transcript."

3. **Consensus estimates (Street expectations).** `raw/panw_earnings_estimates.json` — Alpha Vantage, 43 analysts. Use for beat/miss framing. Non-GAAP EPS consensus: $0.7793. Revenue consensus: $2,239.8M. **Note: this file uses non-GAAP EPS throughout. The GAAP EPS consensus was ~$0.38 (a separate construct — do not conflate).**

4. **Income statement history (trends).** `raw/panw_income_statement.json` — Alpha Vantage INCOME_STATEMENT, quarterly. Use for multi-quarter trends, margin trajectories, YoY comps. **Note: gross margin here is GAAP (73.5%) — the press release non-GAAP gross margin is 76.6%. Use non-GAAP for Street comparison.**

5. **EPS history (beat/miss track record).** `raw/panw_earnings.json` — Alpha Vantage EARNINGS, ~14 quarters. Use for historical surprise patterns and trend reads.

6. **Peer comparison (relative context).** `raw/peer_snapshot.json` — manually assembled from public filings. CRWD, FTNT, ZS most recent reported quarters. Use only for relative framing, not absolute claims about competitors.

7. **Buy-side signals (positioning overlay).** Three files in `raw/`:
   - `panw_q2fy26_form4_summary.txt` — SEC EDGAR Form 4 filings ✅ complete
   - `panw_q2fy26_short_interest.txt` — estimated range; historical Feb 2025 data not accessible ⚠️
   - `panw_q2fy26_put_call.txt` — narrative fallback; historical Feb 2025 data not accessible ⚠️

   For the two ⚠️ files: use the narrative framing built into each file rather than specific numbers. The stock price action itself (−3.5% AH, +8% recovery by Feb 19) is the most reliable proxy for options and short positioning resolution.

8. **Database (aggregated).** `/tmp/earnings_v2.db` — SQLite, 13 tables, 118 rows. Ephemeral (rebuilt each session via `rebuild_db.py`). Aggregates all of the above into a queryable format. Use for structured queries when the demo calls for it. See schema below.

**Attribution rule:** When citing figures, name the source in parentheses — e.g., "(per press release)" or "(Alpha Vantage consensus, 43 analysts)." Never blend a press release figure and an estimated figure in the same sentence without flagging which is which.

---

## The Database: What You Have

**13 tables, 118 rows. Ephemeral — rebuilt each session from raw files via `data/rebuild_db.py`. Lives at `/tmp/earnings_v2.db`. HTML is the persistent artifact.**

| Table | Rows | What it contains |
|---|---|---|
| `companies` | 4 | Reference table — PANW (primary), CRWD, FTNT, ZS (peers). Fiscal year end months, data sources. |
| `quarterly_financials` | 9 | P&L per quarter. PANW: Q2 FY26, Q1 FY26, Q2 FY25, Q1 FY25. Peers: most recent quarter each. `company_type` = 'primary' or 'peer'. Revenue, margins, EPS (GAAP + non-GAAP), deferred revenue, FCF. |
| `company_kpis` | 18 | Key-value KPI table. PANW: NGS ARR, RPO, RPO <12m, platformized customers, XSIAM bookings, stock reaction, beat pcts. Peers: ARR equivalents, subscription revenue. |
| `consensus_estimates` | 1 | Q2 FY26 Street consensus — non-GAAP EPS $0.7793, revenue $2,239.8M, 43 analysts. |
| `eps_history` | 14 | EPS surprise history, ~14 quarters back to Q1 FY23. Reported vs. estimated, surprise $ and %. |
| `guidance` | 8 | Management guidance by quarter. Q3 FY26 (next quarter) and FY26 full year, per metric (`revenue_m`, `eps_nongaap`, `ngs_arr_bn`, `fcf_margin_pct`). Supports revision tracking via `revision_vs_prior`. |
| `insider_transactions` | 4 | Form 4 events — Arora CEO sale $143.7M, Jenkins post-earnings sale $493K, others. All under 10b5-1 plans. |
| `forward_estimates` | 2 | FY26 and FY27 full-year consensus — EPS and revenue, analyst count. |
| `price_history` | 41 | Monthly OHLCV, Jan 2023 – May 2026. **Not split-adjusted before December 2024 (2:1 split Dec 12, 2024).** |
| `price_events` | 4 | Annotated key price events: Feb 2024 guidance cut, Dec 2024 split month, Jan 2025 pre-earnings, Feb 2025 earnings month. |
| `transcripts` | 1 | Full Q2 FY26 earnings call transcript text (Motley Fool). ~7,400 words. |
| `transcript_qa` | 10 | Parsed Q&A exchanges — analyst name, firm, question, answer, `key_signal` (bullish/bearish/neutral), analytical note. Exchange #9 (Nowinski/Wells Fargo, net new ARR bear case) is flagged bearish. |
| `sentiment_signals` | 3 | Short interest, put/call ratio, options skew. Feb 2025 historical data is inferred/estimated (client-rendered web pages, not accessible via static fetch). `confidence` field: 'actual' | 'estimated' | 'inferred'. |

**Key fields to know:**

`quarterly_financials`:
- `symbol` + `fiscal_period` is the join key (e.g., `PANW` + `Q2_FY26`)
- `company_type`: 'primary' (PANW) or 'peer' (CRWD/FTNT/ZS)
- `revenue_total_m`, `revenue_product_m`, `revenue_subscription_m` — all in millions
- `gross_margin_gaap_pct` vs `gross_margin_nongaap_pct` — use non-GAAP for Street comparison
- `operating_income_gaap_m` vs `operating_income_nongaap_m` — this is where the +349% YoY trap lives (see below)
- `eps_gaap` vs `eps_nongaap` — GAAP EPS ~50% of non-GAAP due to SBC (~$343M/qtr)
- `is_primary_quarter` = 1 flags Q2 FY26 as the demo quarter

`company_kpis` (key-value — query by `kpi_name`):
- PANW: `ngs_arr_bn`, `rpo_bn`, `rpo_current_bn`, `platformized_customers`, `xsiam_bookings_m`, `stock_close_earnings_day`, `revenue_beat_pct`, `eps_beat_pct`
- CRWD: `arr_bn`, `subscription_rev_bn`; FTNT: `subscription_rev_bn`; ZS: `billings_bn`

`guidance` (query by `symbol` + `issued_for_period` + `metric`):
- Q3 FY26: `revenue_m` (low 2260 / high 2290), `eps_nongaap` (low 0.76 / high 0.77), `ngs_arr_bn` (low 4.90 / high 4.95)
- FY26 full year: `revenue_m`, `eps_nongaap` (raised, low 3.18 / high 3.24), `fcf_margin_pct` (low 37 / high 38)

`insider_transactions`:
- `is_10b5_1_plan` = 1 for all four entries — critical for correct interpretation
- `plan_adoption_date` — Arora's is `2024-03-27` (9+ months before the transactions)

`price_history` / `price_events`:
- `split_adjusted` = 0 for all rows — prices are raw (pre-split values will be ~2x current for pre-Dec 2024 dates)
- Feb 2025 earnings month: close $190.43, high $208.39 (6-day recovery post-earnings)

**What is NOT in the DB** (do not fabricate):
- Specific historical short interest figures from February 2025 (not accessible — use narrative)
- Historical put/call ratios from February 2025 (not accessible — use narrative)
- Intraday or hourly price data
- Analyst price targets or rating history
- Segment-level geographic revenue beyond the three-region split (Americas/EMEA/APAC) in the press release
- Q3 FY26 actual results (June 2 print — not yet reported as of this writing)

**Rebuilding the DB and regenerating the HTML:**
```bash
# From the earnings-demo root directory:
python3 demo/data/rebuild_db.py      # → /tmp/earnings_v2.db (13 tables, 118 rows)
python3 demo/generate_baseline.py    # → demo/earnings_baseline.html (Aileron-branded)
```
The DB is ephemeral — it lives only in `/tmp` and must be rebuilt at the start of each session. SQLite direct writes to the mounted filesystem fail silently; the scripts handle this correctly. See `LESSONS_LEARNED.md` for the full pattern. **Never attempt to read `earnings.db` from the mounted filesystem** — any file there with that name is a stale artifact from a prior failed write attempt.

---

## Move 1 — Sell-Side Foundation (~10 minutes)

Move 1 answers: *What did this quarter actually say?* The goal is not to summarize the press release — it is to develop a structured investment view by working through the data systematically, identifying the traps, and surfacing the real debate.

### The Setup Prompt

Before looking at any data, ask participants to answer: *What factors drive an investment view on a cybersecurity platform company in an earnings call context?* This is Beat 1 of the workshop. Move 1 then shows what a structured AI-assisted approach produces on the same question.

For the demo, the setup prompt is:

> "I'm going to analyze the Q2 FY26 earnings call for Palo Alto Networks. Before I look at the numbers, here's my analytical framework: [beat/miss vs consensus, guidance vs expectations, unit economics trends, competitive positioning, management credibility]. Now walk me through the quarter against that framework."

This demonstrates framework-led use — the AI is briefed before it starts, not left to choose its own structure.

### Layer 1: Headline Beat/Miss

**What to show:**

| Metric | Actual | Consensus | Beat |
|---|---|---|---|
| Non-GAAP EPS | $0.81 | $0.779 | +3.9% |
| Revenue | $2,257M | $2,240M | +0.8% |
| GAAP EPS | $0.38 | $0.38 | 0.0% |
| NGS ARR | $4.78B | ~$4.6B est | ~+4% |

**The Street-tracked metric is non-GAAP EPS, not GAAP.** The GAAP/non-GAAP gap at PANW is ~2x — driven by stock-based compensation of ~$343M per quarter. If you use GAAP EPS as your beat/miss metric, you're not talking the same language as the sell-side.

**Why the stock fell −3.5% AH despite the beat:** Surface this as the central analytical tension in Move 1. The company beat on the two headline metrics. The stock still fell. Something else was driving the reaction.

### Layer 2: The Guidance Trap

**Q3 FY26 EPS guidance: $0.76–$0.77 (non-GAAP)**

Q2 actual was $0.81. The guidance implies a **sequential step-down of ~5%** in the next quarter. For a company that just beat, that is a signal — the beat was partly from one-time items, or the company is signaling conservatively, or the expense base is stepping up.

This is almost certainly the primary driver of the AH reaction. Beat prints do not automatically equal higher stocks when guidance implies deceleration.

**Full-year FY26 guidance context:** Revenue $9.14–$9.17B, non-GAAP EPS $3.18–$3.24. These frame the year, but the quarterly guidance step-down is the near-term signal.

**Prompt to demonstrate:**
> "The company beat non-GAAP EPS by 3.9%. But Q3 guidance implies $0.76-0.77. How do you reconcile the beat with a sequential step-down in EPS guidance, and what does that tell you about the stock reaction?"

### Layer 3: The GAAP OI Trap

**This is the single most important analytical trap in the dataset. Demo it explicitly.**

GAAP Operating Income: $240M (Q2 FY26) vs $54M (Q2 FY25) = **+349% YoY**.

That number looks extraordinary. It is not operating leverage. Here is the decomposition:
- Q2 FY25 had **$179M in litigation charges** (one-time) → GAAP OI was artificially suppressed
- Q2 FY26 had **$3M in litigation charges** → artificially normalized
- The improvement attributable to litigation normalization: **~$175M of the $187M total YoY gain**

**Non-GAAP OI: +13.5% YoY. Non-GAAP operating margin: 28.4% vs 28.6% prior year — flat.**

Platform investments are not yet converting to margin expansion. That is the real read.

**Prompt to demonstrate:**
> "GAAP Operating Income is up 349% year-over-year. What is the correct interpretation of that number for a long-term investor?"

The AI should surface the litigation normalization if the context contains the press release. If it misses it, that is itself a teaching moment — it shows why the source document matters.

### Layer 4: The NGS ARR Story (Platformization)

NGS ARR (Next-Generation Security Annual Recurring Revenue) is the primary KPI for PANW's platformization thesis. The bull case rests entirely on this number.

**Q2 FY26:** $4.78B, +37% YoY. Q3 guidance: $4.90–$4.95B (+33-34% YoY). The deceleration in growth rate is intentional and guided — not a surprise. The absolute dollar ramp is the metric.

**What platformization means:** PANW is converting point-product customers into full-platform relationships. Each conversion is lower near-term revenue (they discount to consolidate) but higher future NDR and gross margin as the full platform scales.

**From the transcript:** 75 new platformization customers in Q2 (vs 45 YoY). 2-platform customers up 50% YoY. 3-platform customers up 3x YoY. XSIAM: $1B cumulative bookings milestone reached. QRadar (IBM partnership): >$100M bookings in Q2.

**The bear case from the transcript:** Andrew Nowinski (Wells Fargo) challenged net new ARR — pointed out it was declining YoY ex-QRadar for two consecutive quarters. This is the key bear case to surface. The QRadar partnership is masking organic ARR growth deceleration.

**RPO:** $13.0B (+21% YoY). RPO is a leading indicator of future revenue — contracts signed but not yet recognized. +21% provides revenue visibility.

**Prompt to demonstrate:**
> "PANW's NGS ARR is growing 37% YoY but Q3 guidance implies deceleration to 33-34%. The analyst community is split on whether this is sustainable. Walk me through the bull and bear cases on the platformization thesis based on this call."

### Layer 5: Revenue Mix and Margin Bridge

**Revenue composition (Q2 FY26):**
- Subscription & Support: $1,835.9M (81.3% of total)
- Product: $421.5M (18.7% of total)
- YoY growth: +14.3% total; subscription growing faster than product

**Margin bridge (GAAP → non-GAAP):**
The gap is primarily SBC (~$343M/qtr) plus amortization and one-time charges. Non-GAAP gross margin 76.6% vs GAAP 73.5%. Non-GAAP operating margin 28.4% vs GAAP 10.6%.

One analytical note from the transcript: gross margin had a one-time inventory write-off (~40 bps drag) in Q2 FY26. This is a transient drag, not structural.

**Geographic mix:** Americas ~68%, EMEA ~20%, APAC ~12%. No significant geographic surprises in Q2 FY26.

### Layer 6: Peer Positioning

Use `peer_snapshot.json` for relative context. The core tension:

| Ticker | Revenue Growth | ARR | Non-GAAP Op Margin |
|---|---|---|---|
| PANW | +14% | $4.78B NGS (+37%) | 28.4% |
| CRWD | +23% | $4.24B (+23%) | ~24% |
| FTNT | +17% | N/A (product model) | 39.2% |
| ZS | +23% | N/A (billings) | ~21% |

**PANW paradox:** Slowest headline revenue growth. Fastest ARR growth among peers. This is what the platformization thesis predicts: near-term revenue sacrificed for platform ARR. Whether the market rewards this depends on whether you believe the platform ramp translates to future margin expansion.

**Prompt to demonstrate:**
> "PANW's revenue growth is the slowest in the peer group. CRWD and ZS are both growing at 23%. How do you think about PANW's positioning versus peers given this quarter?"

---

## Move 2 — Buy-Side Overlay (~3 minutes)

Move 2 answers: *What was the smart money doing before and after this print?* This is where the insider, options, and short interest signals come together to explain price action beyond the headline beat/miss.

Move 2 is intentionally short — it is a demonstration that this layer of analysis exists and can be structured, not a deep dive. The goal is to show the demo audience that the analytical framework extends beyond sell-side fundamentals.

### Signal 1: Insider Activity (Form 4)

**The headline:** Nikesh Arora (CEO) sold $143.7M of PANW stock on February 3-4, 2025 — **10 days before the earnings announcement**.

That number is alarming on its face. Here is the full context:

- **Plan type:** 10b5-1 automatic trading plan — pre-scheduled, not discretionary
- **Plan adoption date:** March 27, 2024 — **9+ months** before the transactions
- **Underlying instrument:** Options at $33.08 strike (pre-split) expiring **December 2025**
- **Correct read:** Routine option expiry management. Arora had to exercise before the options expired in December 2025. Adopting the plan in March 2024 and executing in February 2025 is textbook 10b5-1 usage.

**The tell for the correct interpretation:** William D. Jenkins Jr. (President) sold 2,401 shares on **February 19** — **6 days after earnings** — at $203–$208. That's a stock that had already recovered from the $187.68 earnings-day close. If insiders had anticipated a bad quarter, Jenkins would not be selling at $203+ into a recovery.

**Prompt to demonstrate:**
> "The CEO sold $143.7M of PANW stock 10 days before earnings. What is the correct interpretation of this transaction for an investor trying to read insider signals?"

**The teaching moment:** The AI should flag the 10b5-1 plan and adoption date. If it misses it and leads with "this is a bearish signal," that is the jagged frontier moment — the AI read the surface, not the context. A junior analyst who has seen a 10b5-1 plan before would catch this immediately.

### Signal 2: Short Interest

**What we know:** Short interest was declining over the period. Current levels (May 2026): 3.11% of float (25.2M shares). December 2025: 6.65% (44.6M shares). Directional inference for February 2025: likely 5–7% of float given the elevated risk premium from the February 2024 guidance cut.

**Why it matters:** Elevated short interest creates a setup where a clean beat generates a squeeze — shorts covering accelerates the upside. But it also creates a defensive floor heading in — the stock is pricing in skepticism. For PANW in February 2025, the February 2024 guidance cut had put the stock on short sellers' radar as a company that had shown willingness to trade near-term revenue for long-term platformization.

**The dip-and-rip pattern:** Stock fell −3.5% AH on report day ($187.68 close). By February 19, Jenkins was selling at $203–208 — a +8–11% recovery in 6 days. This is consistent with short covering as shorts concluded the guidance fears didn't materialize as badly as feared.

**Note on data availability:** Historical FINRA short interest data for February 2025 is not accessible via static web fetch — the FINRA and Nasdaq detail pages are client-rendered. Use the narrative framing above and the price action as the proxy. See `raw/panw_q2fy26_short_interest.txt` for the full written framing.

### Signal 3: Options Positioning

**What we know:** Current put/call volume ratio: 0.94 (slightly bullish). Current OI ratio: 1.01 (slightly bearish). Historical February 2025 data is not accessible (client-rendered on barchart.com).

**Contextual framing:** The February 2024 guidance cut had created institutional memory. Options players heading into Q2 FY26 were pricing elevated implied volatility. Put/call OI ratios for megacap tech earnings plays typically run 0.9–1.2; PANW would have been in the upper half of that range given the precedent. Elevated put OI creates a ceiling — the stock needs to beat AND reset guidance expectations to clear it.

**What happened:** PANW beat on EPS and revenue, but the Q3 guidance step-down ($0.76–$0.77 vs $0.81 actual) kept put holders from fully covering. That explains why the beat didn't produce an immediate rally — options holders needed guidance clarity they didn't get.

**Note on data availability:** See `raw/panw_q2fy26_put_call.txt` for the full narrative framing.

### Move 2 Synthesis Prompt

This is the closing prompt for Move 2:

> "Given the insider activity (CEO sold $143.7M pre-earnings under 10b5-1), estimated short interest of 5-7% of float heading in, and elevated put/call ratios due to the 2024 guidance cut precedent — and given that the stock fell 3.5% AH on a beat but recovered 8% by February 19 — walk me through the positioning story. What does this price action tell you about how the smart money was positioned?"

---

## The Horizon Reference

Use this table to anchor the investment debate in the correct time horizon. The answer to "Buy/Hold/Sell?" depends almost entirely on which time horizon you are evaluating.

| Horizon | Bull Case | Bear Case | Key Variable |
|---|---|---|---|
| **1 quarter** | Q3 guidance was conservative; PANW has beaten estimates in 13 of 14 recent quarters. | EPS step-down sequential is real; margins not expanding. | Q3 actual EPS vs $0.76–$0.77 guide |
| **4 quarters (FY26)** | NGS ARR ramp ($4.78B → $5B+) provides revenue visibility; platformization cohorts mature. | Net new ARR ex-QRadar is declining YoY for 2 quarters — organic momentum is slowing. | Net new ARR trend ex-partnerships |
| **3+ years** | If platformization works: 3-platform customers have 70-80%+ NDR; margin expansion follows scale. Cybersecurity spend is structural. | Platform consolidation is a bet that customers choose PANW over best-of-breed. They may not. CRWD and ZS are growing faster today. | 3-platform customer cohort economics |

The workshop investment debate should surface these horizons explicitly. When two participants have opposite views, it is often because they are evaluating different time horizons — not because they disagree on the facts.

---

## Analytical Patterns

### Pattern 1: "Let me see the quarter at a glance"

The entry point for first-time demo audiences. Give the overview, then zoom in.

**Step 1:** Pull `key_metrics` and `quarterly_financials` for Q2 FY26. Show the four top-line metrics: revenue, non-GAAP EPS, NGS ARR, stock reaction.

**Step 2:** Pull `consensus_estimates` for Q2 FY26 and compute beat/miss on each.

**Step 3:** Show that the beat is real but modest (+3.9% EPS, +0.8% revenue). Frame the −3.5% AH reaction as the analytical question that needs explaining.

**Step 4:** Surface the guidance: Q3 non-GAAP EPS $0.76–$0.77 vs Q2 actual $0.81. That's the answer.

**Step 5:** Surface the GAAP OI trap: $240M vs $54M = +349%. Show the litigation normalization decomposition. Non-GAAP OI +13.5%. Margin flat. This is the single best demonstration of analytical trap → AI-assisted clarification.

### Pattern 2: "What's the bull case / bear case?"

Triggered by participants who want structured debate rather than a summary.

**Step 1:** Establish the time horizon first. The bull/bear answer is different at 1 quarter vs 3 years.

**Step 2: Bull case.** Build from the platformization data: NGS ARR +37%, XSIAM $1B milestone, QRadar partnership, 3-platform cohort growth, RPO $13B (+21%) for revenue visibility. Layer in PANW's beat track record from `eps_history` (consistent positive surprises).

**Step 3: Bear case.** Build from the transcript bear challenge: net new ARR declining YoY ex-QRadar (2 consecutive quarters), revenue growth slowest in peer group (14% vs CRWD/ZS at 23%), margins flat (28.4% vs 28.6%), guidance step-down on EPS. Add that platformization discounts suppress near-term revenue deliberately — the question is whether the market is willing to wait.

**Step 4: The synthesis question.** "The central question is whether you believe PANW's 3-platform cohort economics — which implies 70-80%+ NDR at maturity — will translate to margin expansion by FY28-29. If yes, current valuation is reasonable. If no, you're paying platform-company multiples for point-product-company growth."

### Pattern 3: "How does this compare to what the AI does without context?"

This is the meta-demo moment — showing the difference between unstructured AI use and framework-led use.

**Step 1:** First prompt (unstructured): "Tell me about PANW's Q2 FY26 earnings." Show the output — generic summary, likely misses the GAAP OI trap, may confuse GAAP and non-GAAP EPS.

**Step 2:** Second prompt (framework-led): "I'm analyzing PANW Q2 FY26 as a potential long position in an absolute return fund with a 12-month horizon. My analytical framework prioritizes: (1) beat/miss quality — is the beat sustainable or one-time?, (2) guidance vs. buy-side expectations, (3) the platformization KPI trend vs. peers. Walk me through the quarter against that framework." 

**Step 3:** Compare the two outputs. The difference in analytical depth — and the difference in where the traps surface — is the learning moment.

**This pattern is the core of the Beat 2 workshop exercise.** Participants who led with their framework (from Beat 1) will get structurally better outputs than participants who typed a generic question.

### Pattern 4: "What should I look for in the Q3 print?"

Use this for the debrief or for participants who want to extend the analysis forward.

**Step 1:** Identify the monitored variables from Q2:
- Non-GAAP EPS vs $0.76–$0.77 guidance (can they beat guidance again?)
- Net new NGS ARR — is the ex-QRadar organic decline reversing?
- Non-GAAP operating margin — any signs of leverage on the platform investments?
- QRadar integration bookings — partnership still "couldn't have been better" per transcript; update?

**Step 2:** Set the stakes. Q3 FY26 reports June 2, 2026 — two days before the workshop. The answer is live in the room. Whether PANW beats or misses against the lowered EPS bar ($0.76–$0.77) will be known. The workshop can reference the actual Q3 result.

**Step 3:** Update the data. See `DATA-GUIDE.md` for the Phase B runbook — how to swap in Q3 FY26 data after the June 2 print.

---

## Interpretation Guardrails

**GAAP vs non-GAAP direction.** For PANW: GAAP EPS is roughly 50% of non-GAAP EPS due to SBC (~$343M/qtr). If a claim sounds too dramatic (e.g., "EPS nearly doubled"), check whether someone blended GAAP and non-GAAP figures. Never cite GAAP EPS as the beat metric — the Street tracks non-GAAP.

**The GAAP OI +349% rule.** Always flag this as litigation normalization, not operating leverage. This is a red-level analytical trap in the demo. If an AI or participant cites +349% without the normalization context, it is wrong.

**10b5-1 plan adoption date always matters.** An insider sale under a 10b5-1 plan means nothing without the adoption date. A plan adopted 9 months before the transaction is not an insider signal. A plan adopted 2 weeks before the transaction would be. Always check `plan_adoption_date` in `insider_transactions`.

**Sequential vs YoY for guidance.** The Q3 EPS guidance step-down ($0.81 actual → $0.76–$0.77 guided) is sequential — quarter-over-quarter. The YoY comparison for Q3 is favorable (Q3 FY25 actual was lower). Don't confuse the two: the sequential step-down is what drove the AH reaction.

**NGS ARR is not revenue.** NGS ARR is an annualized recurring revenue metric — it measures the run-rate value of NGS contracts. It is not recognized revenue in the quarter. A $4.78B ARR base means ~$1.2B per quarter at the run-rate; the $2.26B quarterly revenue includes hardware, one-time items, and legacy products. Treat these as separate metrics.

**Peer ARR comparability.** PANW's NGS ARR ($4.78B) and CRWD's ending ARR ($4.24B) use different definitions. PANW's NGS ARR is a subset of total ARR (next-gen security only). CRWD's ARR includes all recurring revenue. Direct comparison is directionally valid but not apples-to-apples.

**Short interest and put/call figures before February 2025.** The historical data for these two metrics is not accessible via static web fetch — both platforms require JavaScript rendering. The `.txt` files contain narrative framings based on directional data. Use those framings. Do not fabricate specific figures.

---

## Output Style for the Demo

**Lead with the framework, not the data.** The demo teaches framework-led AI use. Always show the framework-first prompt before showing the output. The sequence is: *here is my framework → here is what I asked → here is what the AI produced → here is where it adds value and where it needed human judgment.*

**Name the traps explicitly.** The GAAP OI +349% trap and the 10b5-1 CEO sale are the two designed teaching moments in this dataset. Do not let them disappear into the analysis — surface them, frame them, and use them.

**Keep the investment view live.** The demo ends with a view: Buy / Hold / Sell with biggest conviction and biggest uncertainty. That view should be stated explicitly, mirroring what participants just posted via the feed. The contrast between the feed aggregate and the AI-assisted view is the closing moment.

**Pace Move 1 at about 10 minutes.** In practice: ~3 min on the setup + headline beat/miss, ~3 min on the GAAP OI trap + guidance, ~2 min on NGS ARR / platformization debate, ~2 min on peers + synthesis. Move 2 is 3 minutes: ~1 min on each signal, then the synthesis prompt.

**Handle data gaps with narration, not silence.** When a specific figure is not accessible (short interest Feb 2025, put/call Feb 2025), say so explicitly and use the narrative framing from the `.txt` files. This models appropriate epistemic humility — the AI should name its own data gaps. That is itself a teaching moment.

**The closing prompt.** End every demo session with this:

> "Given everything we just reviewed — the beat quality, the guidance step-down, the platform ARR trajectory, and the positioning signals — what is your investment view on PANW going into Q3? State it as: Buy / Hold / Sell, biggest conviction, biggest uncertainty."

The answer should match (or meaningfully diverge from) what the room just posted to the feed. That divergence — or alignment — is the debrief.

---

## Phase B: Live Quarter Update

After the June 2 print, update all data files and rebuild the DB per the runbook in `DATA-GUIDE.md`. The key files to update:

1. `raw/panw_earnings.json` — re-pull from Alpha Vantage EARNINGS endpoint
2. `raw/panw_income_statement.json` — re-pull INCOME_STATEMENT, add Q3 FY26 quarter
3. `raw/panw_earnings_estimates.json` — re-pull EARNINGS_ESTIMATES for Q3 actuals and Q4 forward
4. `raw/panw_q3fy26_press_release.json` — scrape the new press release (paloaltonetworks.com/company/press-room)
5. `raw/panw_q3fy26_transcript.txt` — scrape Motley Fool or Seeking Alpha transcript
6. Short interest and put/call: use Claude in Chrome (JavaScript-enabled) to screenshot the relevant pages before they update — capture the pre-earnings positioning data. URLs in each `.txt` file.

Rebuild: `python3 demo/data/rebuild_db.py`
Verify: open `earnings_baseline.html` in browser and confirm Q3 numbers appear correctly.

For the workshop on June 4: Q3 FY26 actuals will be live. The audience will have seen headlines. The demo can reference Q3 as the live quarter — whether PANW beat or missed the lowered $0.76–$0.77 bar will be the room's shared context.
