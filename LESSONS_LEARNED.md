# Lessons Learned

*Last updated: 2026-05-28 (session 8, continued — Tab 3 framework redesign)*

This file captures technical workarounds, design decisions, and things that failed or surprised us. Update at the end of every working session. Promote patterns to findings when they recur.

---

## Synthesized Findings

### SQLite: /tmp workaround was Cowork-specific; not needed in Claude Code
**Pattern:** The "SQLite fails silently on mounted FS" finding was specific to the Cowork environment. In Claude Code (terminal-first), SQLite writes cleanly to `demo/data/db/earnings.db` — 131KB, confirmed readable. The `/tmp` workaround has been retired.

**Current state:** DB lives at `demo/data/db/` (gitignored, rebuilt on each run). The two-step workflow is:
```
python demo/data/rebuild_db.py      # → demo/data/db/earnings.db
python demo/generate_baseline.py    # → demo/earnings_baseline.html
```

**Cowork context (historical):** `/sessions/.../mnt/` filesystem in Cowork failed silently for SQLite binary writes. This finding was real in that environment but does not apply here.

---

## Session Log

### 2026-06-03 (session 10) — QC pass: 8 bugs fixed, 2 false positives diagnosed

Full QC of the three-tab dashboard via two parallel Explore agents cross-checking every displayed value against the DB. Eight real bugs were found and fixed. Two of the ten agent-reported issues were false positives (correct behavior misread as bugs). Root causes fell into four patterns:

**Pattern 1 — f-string sign anti-pattern (`+{negative}%`)**
Three bugs shared the same root: the author prepended a literal `+` before the format expression instead of using Python's built-in `+` sign specifier. `f'+{-30}%'` → `+-30%`; the fix is `f'{-30:+.0f}%'`. Affected: GAAP OI YoY display (line 1023), OI margin bps in Tab 2 (line 1581). In both cases a hardcoded `+` was prepended to a value that could be negative. Rule going forward: **always use `{value:+.Nf}` for values that may be negative; never prepend a literal `+`.**

**Pattern 2 — Python banker's rounding on exact `.5` values**
Python's default `:.0f` and `:.2f` format specifiers use round-half-to-even (banker's rounding), which rounds `.5` to the nearest *even* digit rather than up. This affected:
- ZS Revenue 850.5 → displayed as `$850M` instead of `$851M` (expected 851)
- ZS ARR 3.525 → displayed as `$3.52B` instead of `$3.53B` (expected 3.53)
- FY FCF margin guidance 37.5–37.5 → displayed as `38–38%` instead of `37.5–37.5%`
Fix: added a `_rhu(v, decimals)` helper (round-half-up using `math.floor(v * factor + 0.5) / factor`) applied in `fmt_cell` for `$M` and `$B` formats; FCF margin guidance switched from `:.0f` to `:.1f` since values are exactly 37.5. Rule going forward: **use `_rhu()` in any `fmt_cell` path where exact `.5` values could appear; use `:.1f` or `:.nf` when the natural precision of the data is not integer.**

**Pattern 3 — hardcoded values that don't read from DB**
Two bugs were literal hardcoded values left from an earlier draft that bypassed the DB entirely:
- PANW `'profitable': 1` in `PEER_ROWS` — hardcoded True regardless of net income. Q3 FY26 PANW had net income -$177M (GAAP unprofitable). Fix: read `panw_q2.get('gaap_profitable')` from DB.
- Q4 EPS guidance `class="guidance-value neg"` — hardcoded `neg` was a leftover from Q2 FY26 when the sequential EPS step-down was the signal. Q4 FY26 guidance ($0.96–$0.98) is above Q3 actual ($0.85). Fix: dynamic class computed from guidance midpoint vs actual EPS. Rule going forward: **no literal financial judgments (profitable/unprofitable, positive/negative direction) may be hardcoded in templates; derive from DB values at generate time.**

**Pattern 4 — stale quarter reference in YoY lookups**
The variable computing GAAP OI YoY was looking up `Q2_FY25` as the prior-year comparison when the primary quarter changed to Q3 FY26. YoY comparison must use the same fiscal quarter one year prior (`Q3_FY25`, not `Q2_FY25`). Fix: update the period string in the prior-year lookup. This was a copy-paste artifact from the Q2 FY26 build. The note in the KPI card ("Prior year had one-time charges") was also stale — in Q3 FY26 it is the *current* quarter with the one-time GAAP charge, not the prior year. Updated to "Q3 FY26 one-time charge — compare non-GAAP". Rule going forward: **when updating the primary period for a quarterly refresh, grep for all prior-year period strings and update them at the same time.**

**Missing KPI — `revenue_beat_pct`**
The `revenue_beat_pct` KPI was never written to `company_kpis` in `rebuild_db.py`, so the dashboard displayed `beat +0.0%`. The value (2.11%) was already in the guidance JSON under `beat_miss_q3_fy26.revenue_beat_pct`. Fix: add the `kpi()` call in `rebuild_db.py` immediately after `eps_nongaap_beat_pct`. The `eps_nongaap_beat_pct` KPI was written correctly because it came from a dedicated EPS history JSON with an explicit field; revenue beat was a derived field in the guidance JSON that was not wired through.

**False positives from agent QC (issues #7 and #8)**
The QC agent flagged Nikesh Arora as "missing from insiders" due to the `transaction_code='S'` filter. In Q3 FY26, Arora made no open-market sales — he purchased 68,185 shares at ~$147 (code `P`, acquired_disposed=`A`). The filter is correct; Arora should not appear in a sales table. Similarly, Klarich shows 12 S transactions and Paul shows 4 S transactions, which are correct counts. The `F`-code transactions (tax withholding on RSU vesting) are appropriately excluded from a discretionary sales display. The QC agent's reasoning was: "the filter excludes his transactions" — technically true, but those transactions are purchases, not sales. Rule going forward: **before concluding a filter is wrong, confirm what transaction codes the excluded rows actually have.**

---

### 2026-06-03 (session 9) — Q3 FY26 pipeline refresh: all scripts updated

PANW Q3 FY26 earnings released June 2, 2026. Updated all 7 pipeline scripts for the Q3 FY26 refresh. PDFs (supplemental, presentation, transcript) dropped into `demo/data/manual/`. Pipeline is ready to run.

**Files updated:**
- `demo/data/gather.py` — PDF filenames, fiscal dates (Q3_FY26 / 2026-04-30), guidance fields (q4_fy26), price window (2026-02-01 to 2026-07-15), Form 4 window (2026-02-01:2026-06-02)
- `demo/data/rebuild_db.py` — primary period Q3_FY26, report date 2026-06-02, KPI/guidance/event inserts, AH reaction window Jun 2→Jun 3
- `demo/data/analysis/run_earnings_analysis.py` — output file, period refs, guidance keys (q4_fy26), TTM quarters
- `demo/data/analysis/run_buyside_analysis.py` — output file, period refs, task prompt ("Q3 FY26 print")
- `demo/generate_baseline.py` — PRIMARY_PERIOD, analysis file paths, date strings, AH reaction note
- `demo/server.py` — analysis file paths, KPI query period, guidance keys, context date strings
- `demo/data/tests/test_provenance.py` — all Q3_FY26 assertions (existence/range checks, not exact values — Q3 figures unknown until gather.py runs)

**Key bug fixed:** `rebuild_db.py` was using `daily_raw["rows"]` to index the price history JSON, but `gather.py` writes the key as `"records"`. Changed to `daily_raw["records"]`. The Q2 build never caught this because the daily file wasn't regenerated after the key was standardized.

**Intentional Q2 FY26 references preserved (not stale):**
- `crwd_q4fy26_results.json`: CRWD fiscal Q4 FY26 ends 2026-01-31 — correct
- TTM quarters in `run_earnings_analysis.py`: `["Q4_FY25", "Q1_FY26", "Q2_FY26", "Q3_FY26"]` — correct, Q2 FY26 is a TTM component
- `EVENT_MONTHS` in `rebuild_db.py`: Q2 FY26 (2026-02) kept as historical price marker — correct

**Placeholder sentiment files created** (`panw_q3fy26_short_interest.txt`, `panw_q3fy26_put_call.txt`, `panw_q3fy26_sentiment_signals.json`) so `rebuild_db.py` does not fail on missing files. Confidence flag set to "placeholder". Real figures require Playwright capture of MarketBeat + Barchart before June 4 — open task.

**Provenance test assertions:** Q3-specific value assertions (platformized customers, NGS ARR, etc.) changed from exact values (which were known for Q2 FY26) to existence/range checks. Exact Q3 figures are unknown until `gather.py` runs. After the pipeline completes and values are confirmed, tests can be tightened if desired.

---

### 2026-05-28 (session 8) — Tab 1 completion, Tab 2 sell-side, Tab 3 buy-side + live chat

Heavy build day. Tabs 1, 2, and 3 of `earnings_baseline.html` all reached completion. Pipeline gained an SEC EDGAR XBRL layer to backfill nulls. Tab 3 introduced the first live agentic surface in the project (Claude Opus + Tavily, SSE streaming, FastAPI server).

**XBRL backfill (early AM):**
- New `panw_revenue_xbrl.json` and `peers_gross_margin_xbrl.json` raw files via SEC EDGAR XBRL frames API.
- Backfilled 4 null PANW YoY values that yfinance / Alpha Vantage could not supply for historical quarters.
- Populated GAAP gross margins for FTNT and ZS peers — peer comparison charts (Revenue YoY, Non-GAAP OI Margin horizontal bars, 4 companies) added to the dashboard.
- Price chart annotated with earnings-month markers ①②③④ to align price action with quarterly prints.
- Commit: `STAGE: Data approved 2026-05-28 — SEC EDGAR XBRL integration` (ba29e85). XBRL is now part of the API stack alongside FMP-deprecated / yfinance / edgartools / Anthropic.

**Tab 1 completion (mid-AM):**
- After-hours reaction KPI populated: yfinance daily, Feb 17 close $163.50 → Feb 18 open $149.55, gap **-8.53%**. Resolves the Session 6 known gap on `stock_ah_change_pct`. Daily-bar overnight gap is the chosen proxy; intraday after-hours feeds are not free.
- Sentiment signals values extracted via Playwright: short interest 2.8% float (MarketBeat), put/call 1.09 volume / 4.02 OI (Barchart). Confidence flag = actual (not narrative fallback).
- Sentiment cards redesigned to a story-first layout that surfaces the positioning vs. reaction disconnect, instead of a flat KPI grid.
- Commits: `Tab 1 complete — after-hours reaction and sentiment signals populated` (a6189b9), `Redesign sentiment signals cards — story-first layout` (c17e41a).

**Tab 2 — sell-side analysis (late AM):**
- Resolved Open Question 7 from STATUS.md: Tab 2 is **full sell-side output** following the off-the-shelf `equity-research/earnings-analysis v0.1.0` skill from `financial-services-plugins`. Option A. Steps 5 through 11 render from real JSON, including the recommendation.
- Script `demo/data/analysis/run_earnings_analysis.py` wraps the skill, runs against the rebuilt Q2 FY26 DB, and writes `panw_q2fy26_earnings_analysis.json`.
- Output: Maintain Outperform, PT **$186** (+13.8% upside vs. spot).
- **Four departures from the skill's default output are documented inline and visible in the rendered tab** — this is the demo's pedagogical hook for Tab 2 (off-the-shelf baseline, then show where a buy-side practitioner would deliberately depart). Departures panel is wired into the HTML, not buried in JSON.
- Tab 2 redesigned to a report-note layout with a tool intro card and a new tab name; replaces the previous "Sell-Side Plugin Output" framing from Session 3 (which was fabricated and torn down).
- Commits: `STAGE: Tab 2 Analysis approved` (281494c), `Redesign Tab 2: report-note layout, tool intro card, new tab name` (4633e62).

**Tab 3 — buy-side static + live chat (afternoon / evening):**
- Resolved Open Question 7 (Tab 3 portion): hybrid design — **pre-run static buy-side Q&As** plus **live chat surface**, not one or the other.
- Static layer: `demo/data/analysis/run_buyside_analysis.py` runs five buy-side questions through Claude Opus (claude-opus-4-7) grounded on the Q2 FY26 context. Output `panw_q2fy26_buyside_analysis.json` renders as a five-card accordion in the tab.
- Live layer: `demo/server.py` — FastAPI server with SSE streaming, CORS, and a Claude + Tavily web search tool loop. Start with `python3 demo/server.py` → `http://localhost:8000`. The tab pings `/chat` on load and shows a live/offline badge so the room knows whether the chat surface is up.
- **Agentic loop hardened to handle multiple parallel tool calls per turn.** First version assumed Claude would emit one tool_use per turn; in practice compound questions (e.g., "how does PANW compare to FTNT and CRWD on growth and margins") trigger multiple parallel `web_search` calls. The loop now matches every `tool_use` block with a `tool_result` block before submitting the next round, preventing the API from rejecting the conversation as malformed. This is the fix in commit 428ad30.
- Chat hardening also covered: error handling (graceful display, no silent failures), history rollback on error so a failed exchange doesn't poison the next turn, clear-history button. Commit d437712.
- DOMPurify wrapped around the SSE-rendered HTML to prevent XSS from model output or search results.
- Suggestion chips pre-fill common buy-side questions to lower the friction of the first interaction.
- Sauce panel ("What's powering this") makes the stack visible: Claude Opus + Tavily + the Q2 FY26 context bundle.
- Commits: `STAGE: Tab 3 complete — buy-side layer + live chat` (92865a4), `Fix chat: error handling, history rollback, clear button` (d437712), `Fix Tab 3 chat: handle multiple parallel tool calls per turn` (428ad30).

**Tab 3 framework redesign (session 8 continuation):**

The original Tab 3 static section had 5 pre-written question titles with Claude-generated answers against a loosely defined brief. User flagged that this missed the core design intent: buy-side analysis requires an explicit framework (horizon, alpha edge, peer context, positioning) not just a list of analyst questions.

Full redesign:
- `run_buyside_analysis.py` rewritten from scratch. Five fixed dimension definitions (reusable across quarters — only the answers change per print). Claude generates the quarter-specific question from each definition, then answers it. A sixth call synthesizes stance, conviction, uncertainty, and rationale. Script uses delimiter-based response parsing (`---QUESTION---` / `---ANSWER---` markers) instead of JSON to handle unescaped quotes in transcript-grounded answers.
- New output schema: `framework` dict + `dimensions[]` (id, dimension, question, answer) + `recommendation` (stance, conviction, uncertainty, rationale). Old schema had `questions[]` with title/question/answer — not compatible; both the script and the HTML renderer were rewritten together.
- Tab 3 HTML redesigned: horizon banner (purple strip declaring 6-month / alpha vs. market / buy-side), framework intro (5 mini-cards with one-line dimension definitions — explains the lens before showing the output), accordion cards now carry a dimension pill label showing which lens each card represents, recommendation card is always visible and prominent (stance in green/amber/red depending on buy/hold/sell).
- Suggestion chips updated: "Bull case" replaced with "How does the 6-month view change if this is a 3-month trade instead?" — horizon comparison is the key buy-side departure from sell-side thinking and reinforces the framework.
- Commits: `STAGE: Tab 3 buy-side framework redesign complete` (783da22).

**Key technical finding — delimiter parsing vs. JSON for Claude responses containing quoted text:**
When Claude answers grounded in earnings transcripts, management commentary (e.g., "organic is roughly in line") breaks `json.loads()` because the unescaped quotes corrupt the JSON structure. Delimiter-based parsing (`text.find("---FIELD---")`) is robust against any content in the value, including nested quotes, dashes, and brackets. Use delimiters when asking Claude to produce structured output that may contain arbitrary quoted text.

**Key design finding — fixed dimensions with variable questions:**
Fixing the dimension *definitions* and asking Claude to generate the quarter-specific *question* from each one is more reusable than fixing questions: the definition stays stable across quarters, the question adapts to what this specific print actually raised. Phase B (Q3 FY26) is a straight re-run of the same script — same 5 definitions, new questions and answers from the new data.

**Phase B procedure documented (June 3 refresh for Q3 FY26 print):**
- Re-run `demo/data/gather.py` → `python3 demo/data/analysis/run_earnings_analysis.py` → `python3 demo/generate_baseline.py`. Tab 2 updates automatically from the new JSON. No HTML edits needed.
- Tab 3 static Q&As: re-run `run_buyside_analysis.py` if the questions need to track new disclosures.
- Commit: `STATUS: note June 3 Phase B refresh procedure for Q3 FY26` (c461190).

**Decisions made today:**
- Tab 2 is the off-the-shelf sell-side baseline, full Steps 5–11 from `equity-research/earnings-analysis v0.1.0`. Departures from the skill default are surfaced explicitly as the pedagogical hook — not hidden inside the JSON.
- Tab 3 is **hybrid**: pre-run static buy-side Q&As (accordion) plus a live chat surface. The static layer guarantees there is always something to show; the live layer is the live demonstration of an analyst-as-conversation-partner.
- The live chat uses Claude Opus + Tavily web search via SSE — the first agentic surface in the project. Agentic loop must reconcile every `tool_use` with a `tool_result` before the next round, no matter how many parallel calls Claude emits in a single turn.
- After-hours reaction is approximated by the overnight gap between consecutive daily bars (Feb 17 close → Feb 18 open). Free intraday after-hours feeds are not available; the daily-bar gap is the honest substitute.
- Sentiment signal cards lead with the **positioning-vs-reaction disconnect**, not raw KPI tiles. The story is the divergence.
- XBRL is part of the standing API stack; not a one-off backfill. Frames API is reliable for both PANW YoY history and peer GAAP gross margins.

**Gaps / known limitations carried forward:**
- `revenue_consensus_m` still null (no free API has historical revenue consensus).
- `is_10b5_1_plan` still null (edgartools does not surface this at transaction level).
- `revenue_beat_pct` display still shows "Consensus — · beat +0.0%" because there is nothing to compare against.
- Some pre-Q2 FY26 short interest / P/C historical points remain narrative fallback (client-rendered platforms; static web fetch insufficient). Phase B can capture live via Claude in Chrome before the June 2 print.

**Hard-rules check (this matters):**
- Tab 2: real output from a real run of the `equity-research/earnings-analysis` skill, not fabricated; departures explicitly labeled as departures.
- Tab 3 static: real Claude Opus output on actual Q2 FY26 context, not pre-written analytical conclusions.
- Tab 3 live: runs live in the browser session with the user's API keys; nothing is pre-rendered.
- The Session 3 failure pattern (fabricated analytical content presented as tool output) does not recur in today's build.

---

### 2026-05-27 (session 6) — Pipeline rebuild: Data, Script, Test stages complete

Stages 2 through 4 executed and committed. Full pipeline operational.

**Work completed:**

- **`gather.py` written and run**: 6 sections, all succeeded. PDF extraction (3 PDFs → 5 raw files) via Anthropic Claude API. yfinance for EPS history and price. edgartools for Form 4 (26 filings, full Q2 FY26 window). FMP rejected — all v3 endpoints are now legacy/blocked post-Aug 2025.
- **FMP fully deprecated**: Attempted earnings-surprises, analyst-estimates, income-statement, key-metrics, financial-reports-json. All returned 403 "Legacy Endpoint." FMP cannot be used on the free tier as of Aug 2025. yfinance earnings_history is the replacement for EPS consensus data (4 quarters of non-GAAP actual + estimate). Revenue consensus is not available from any free API for historical quarters — `revenue_consensus_m` is null.
- **edgartools identity requirement**: SEC EDGAR requires a User-Agent header. Fix: `edgar.set_identity("Aileron Group info@aileron-group.com")` before any EDGAR call.
- **`rebuild_db.py` fully rewritten**: Portable paths, correct Q2 FY26 dates (2026-01-31 fiscal, 2026-02-17 report), all data from new raw files, Form 4 from JSON (26 filings, 62 transactions), no hardcoded analytical prose, no silent fallback defaults. All 13 tables populated. 197 rows total.
- **`test_provenance.py` written**: 39 tests, all pass. Provenance (non-null data_source, real files), Q2 FY26 figure verification, staleness check (fiscal date must be 2026-01-31), row count sanity for all key tables.
- **SCHEMA.md updated**: Signed-off supplements corrected to Q2 FY26 actuals (76.1% GM, $384M FCF, $12.429B deferred rev, 1,550 platformized customers). Superseded files documented.

**Verified Q2 FY26 figures (all from PDF extraction, confirmed by tests):**
- Revenue: $2,594M (+14.9% YoY)
- Non-GAAP EPS: $1.03 vs $0.937 consensus (+9.94% beat)
- Non-GAAP gross margin: 76.1%
- Non-GAAP OI margin: 30.3%
- FCF: $384M (14.8% margin, standard)
- NGS ARR: $6.33B (+33% YoY)
- Platformized customers: 1,550
- Deferred revenue: $12.429B ($6.248B current + $6.181B long-term)

**Gaps / known limitations:**
- EBITDA is null — D&A not in supplemental PDF; cannot derive without fabricating.
- Revenue consensus null — not available from yfinance or any free API for historical quarters.
- is_10b5_1_plan null in insider_transactions — edgartools does not surface this at transaction level in our extraction structure.

---

### 2026-05-27 (session 7) — Pipeline rebuild Stage 6: generate_baseline.py

Stage 6 complete. Pipeline rebuild is fully done; `earnings_baseline.html` Tab 1 is final.

**Work completed:**

- **Paths fixed**: all `/tmp/earnings_v2.db`, `/sessions/trusting-brave-ritchie/...` hardcoded paths replaced with `pathlib.Path(__file__).parent` resolution. `os` import removed; file writes use Path `.write_text()` / `.read_text()`.
- **Stale literal fallbacks removed**: `panw_q2.get('eps_nongaap', 0.81)`, `panw_q2.get('revenue_total_m', 2257.4)`, `consensus.get('eps_consensus_nongaap', 0.779)`, and six guidance fallbacks (all with stale FY25 values) converted to direct dict access or `.get() or 0` without embedded stale data.
- **Five analytical callouts removed** (the hard rule from Session 3 was violated in five places):
  1. "GAAP OI Trap" (blamed litigation normalisation, stated "+13.5%" as fact)
  2. "Platformisation thesis" (stated bull/bear case in template)
  3. "Guidance Trap" (analytical interpretation of sequential EPS step-down)
  4. "Peer read" (stated thesis and bear case with hardcoded growth percentages)
  5. "Analytical read" (Arora $143.7M block commentary, Jenkins "mild constructive tell")
  6. "Phase B note" (dip-and-rip $187.68 → $208.39)
- **Stale dates fixed**: `Feb 13, 2025` → `Feb 17, 2026` (report date from DB); `Jan 31, 2025` → `Jan 31, 2026` (fiscal date from DB). Now computed from `panw_q2` dict, not hardcoded.
- **DB info computed**: header now shows `13 tables · 197 rows · earnings.db` (not the old hardcoded `/tmp/earnings_v2.db`).
- **Dead JS removed**: `setHz()` function and hz-related element ID references had no matching HTML elements — removed.
- **Insider display aggregated**: 30 individual sale rows replaced with a 5-row aggregated query (by insider, sum shares/value, date range). Display no longer crashes on null `price_per_share` or hardcodes `10b5-1` badge for all transactions.
- **GAAP OI YoY computed from DB**: `gaap_oi_yoy` now computed as `(Q2FY26_oi - Q2FY25_oi) / |Q2FY25_oi| * 100` = +65% (Q2 FY25 GAAP OI was depressed by one-time charge). Old code showed 0 because the KPI wasn't in the KPI table.
- **FY revenue guidance lookup fixed**: `g_fy_rev` looked for `metric='revenue_bn'` but DB stores it as `metric='revenue_m'`. Display now shows $11.28–$11.31B (was $0.00–$0.00B).
- **EPS chart corrected**: column names changed from `eps_gaap_actual` → `eps_nongaap_actual` and `eps_gaap_estimated` → `eps_nongaap_estimate` to match actual DB schema. Chart labels and title updated to say "Non-GAAP."
- **Revenue mix computed**: subscription/product % are now computed from DB values (80.2% / 19.8%), not hardcoded stale values (81.3% / 18.7%).

**Remaining known gaps (unchanged from Session 6):**
- `revenue_consensus_m` = null (no free API has historical revenue consensus)
- `stock_ah_change_pct` and `stock_close_day_of` = null (not in DB; these would require a live price feed at the time of the earnings release)
- `is_10b5_1_plan` = null (edgartools transaction-level attribute not extracted)
- `revenue_beat_pct` = 0 (no revenue consensus to compute against; display shows "Consensus — · beat +0.0%")
- XSIAM customer count (200+) hardcoded — from transcript text, no KPI slot in DB; acceptable as a factual data point from a stated source, not an analytical conclusion

---

### 2026-05-27 (session 5, end of day) — Pipeline rebuild: Design stage approved

Picked up directly from the Session 4 audit. Resolved the fiscal-year question by sourcing actual PANW Q2 FY26 materials. Operationalized the build contract in code and documentation. Stage-gate discipline activated as git commits.

**Work completed:**
- **Real Q2 FY26 source materials in `demo/data/manual/`**: corrected transcript PDF (Feb 17, 2026 call), Q2'26 earnings presentation, supplemental financial information PDF. Closes the 15-month staleness gap identified in the Session 4 audit.
- **`demo/data/SCHEMA.md` written** as the authoritative source-of-truth for every table, column, and provenance. Build contract rules from `data-audit-findings.md` step 2 sit at the top of the file (provenance mandatory, no silent defaults, Form 4 window 2025-11-01 to 2026-02-17, no session-pinned paths, stage transitions as commits). Seven signed-off hardcoded supplements enumerated in a table with explicit "Pending" verification status.
- **API stack locked**: FMP (income statements, surprises, consensus) + yfinance (price, peers) + edgartools (Form 4s, filings) + Anthropic (PDF extraction, Q&A tagging). `.env.example` committed with key placeholders. No new vendor lock-in beyond what `data-audit-findings.md` recommended.
- **`gather.py` drafted** as the Stage 2 entry point. Loads from `manual/` and APIs, validates, writes to `raw/`. Uses `pathlib.Path(__file__).parent` for all resolution per build-contract rule 5. Exits loudly on missing/invalid manual files.
- **`demo/data/manual/README.md`** documents the manual-file contract: what's required, where to source it, what minimum validation `gather.py` enforces.
- **Stage-gate commits started**. First gate: `STAGE: Design approved 2026-05-27` (fedd02c). The commit message itself enumerates what closed in the Design stage. This is the mechanical guardrail the Session 4 finding called for — discipline expressed in git, not in markdown.

**Decisions made:**
- Real Q2 FY26 data is the test quarter, not Q2 FY25 renamed. The harder path, but the only one that holds up on June 4 (the live PANW story in the room will be Q3 FY26 / June 2 print; Q2 FY26 must be the most recent prior reference point, not a 15-month-old proxy).
- Manual ingestion path is part of the pipeline, not a workaround. PANW press release PDFs, transcripts, and supplemental decks are not API-accessible at the granularity the demo needs. `manual/` is a first-class input folder, validated by `gather.py`, not a dumping ground.
- Stage gates are git commits, not markdown checkboxes. Each `STAGE: <name> approved` commit is the explicit approval moment. A new agent picking up the project can `git log --grep="STAGE:"` to see exactly where the pipeline is.
- Anthropic API is used for PDF extraction inside the pipeline (not just in the demo). Mid-build use, with structured output and provenance back to the source PDF, is consistent with the build contract.
- The seven hardcoded supplements remain "Pending" until each is independently verified against the actual Q2 FY26 press release PDF. The Q2 FY25 verification carried over does not count.

**Open follow-ups for next session (Data stage):**
- Fill in `panw_q2fy26_press_release_supplement.json` from the template using the actual Q2 FY26 press release PDF.
- Verify the seven Pending supplements; check off in `SCHEMA.md`.
- Run `gather.py` end to end. Confirm every raw file written has a `data_source` field tracing to a real input.
- Commit `STAGE: Data approved` once raw files validate.

---

### 2026-05-27 (session 4) — Data pipeline audit

Full audit of `rebuild_db.py`, `generate_baseline.py`, `/tmp/earnings_v2.db`, the raw files in `demo/data/raw/`, and the rendered `earnings_baseline.html`. Findings in `data-audit-findings.md`.

**Top-line:** Values in the DB reconcile to the raw JSONs. The arithmetic is correct. The discipline around the pipeline is the problem.

**Critical issues:**
- Fiscal-year labeling. The raw press release data is for PANW's Q2 FY2025 (Feb 13, 2025 print, fiscal date ending 2025-01-31). The demo labels it "Q2 FY26" throughout. PANW's actual Q2 FY2026 reported Feb 17, 2026. The demo data is 15 months stale relative to where the audience will be on June 4. Operator decision required.
- Reproducibility broken. `demo/data/db/earnings.db` is 0 bytes. The DB lives only in `/tmp`. Both build scripts hardcode the prior session's path (`/sessions/trusting-brave-ritchie/...`). Scripts fail when run as written.
- Integrity risks in `generate_baseline.py`. Hardcoded analytical prose with literal dollar figures on lines 847 and 879. Silent `.get(key, literal_default)` fallbacks on lines 181 to 193 that mask missing DB data. Both violate the Session 3 hard rules in CLAUDE.md, expressed in Python rather than markdown.
- Hardcoded values without explanation. Four Form 4 transactions written as Python tuples, not parsed from the raw text. Two known March 2025 Form 4 filings omitted with no code comment.

**Decisions made:**
- Pipeline rebuild required before any further demo work. Tab 1 of the dashboard is not final until the rebuild lands.
- Build contract drafted (six rules in `data-audit-findings.md` step 2): provenance mandatory, no analytical prose in generator, no silent defaults, stage gates as commits, schema-first documentation, portable paths.
- Tool target for the rebuild: Claude Code. The pipeline only needs filesystem, shell, and web fetch. Git becomes the discipline mechanism for stage transitions.
- Cowork remains the home for downstream demo and facilitation work once the data is locked.

**Documentation discipline applied:** STATUS.md slimmed to a lean tracker. Historical session narrative and completed-task detail archived to `STATUS-ARCHIVE.md`. CLAUDE.md updated with explicit entry points and a pointer to this file as the source of "why these rules exist."

---

### 2026-05-27 (session 3) — Fabrication of analytical content

Tab 2 and Tab 3 of `earnings_baseline.html` were built with fabricated analytical content. Tab 2 was labeled "Sell-Side Plugin Output" and then "Claude Analysis." Neither label was honest. The callout text, trap warnings, and Steps 9 to 11 cards were written by Claude and embedded in `generate_baseline.py`. No plugin was run. No live Cowork session was run. Tab 3 contained pre-written HOLD/BUY verdicts, a bull/bear debate, and a horizon toggle with written conclusions. None of it came from a real session.

When called out, two rounds of cosmetic header fixes were made while the fabricated content remained. The cosmetic fixes compounded the failure.

**Root cause:** Claude jumped to building final-form outputs before the process was designed or validated. No stage gates. No approval at each step. Fabricated content filled gaps where real output had not been generated.

**Decisions made:**
- Tabs 2 and 3 reduced to honest placeholders. No analytical content appears there until the earnings reviewer process has been designed, tested on Q1 FY26, validated, and re-run on the actual test quarter.
- Six hard rules added to CLAUDE.md as a direct response:
  1. Never write analytical conclusions into a template or HTML file.
  2. Never label content as the output of a tool or session that was not actually run.
  3. Never make cosmetic fixes to attribution without fixing the underlying content.
  4. Get approval before each stage transition.
  5. If a step cannot be completed honestly, say so. Do not invent.
  6. Tab 2 and Tab 3 of `earnings_baseline.html` are placeholders until real output exists.
- Process discipline adopted: **Design → Data → Script → Test → Learn → Build.** No stage skipped. No final-form output built before preceding stages are complete and approved.

**Why this matters going forward:** A new agent reading the hard rules without the story may treat them as suggestions. The rules exist because they were violated. This entry is the receipt.

---

### 2026-05-26 — Demo approach expanded, infrastructure architecture decided

Substantial work in `demo/demo_approach.md`. Three-act demo structure is now fully drafted with prompts, timing, and "the moment" notes for each act. Buy-side framework documented with explicit AI role and limitation per dimension. Pre-staging data table specified.

**Decisions made:**
- **Infrastructure: Mentimeter plus GitHub Pages plus Cowork. No custom feed app.** Mentimeter handles the settling poll AND Beat 3 posting in one persistent session. GitHub Pages serves a static exercise brief and PANW one-pager. Cowork is the facilitator surface for theme synthesis and Acts 1 to 3. Architectural principle: one Mentimeter join, one GitHub Pages QR, never both demanding attention at once.
- **Pairing is the default for all participants, not just phone-only.** Two phones works as well as a laptop and a phone. The division of labor (one drives, one pushes the thinking) is the point, not the device. Removes the device-sorting step from facilitator overhead.
- **One post per pair to the feed.** Room of 15 yields 7 to 8 posts, clean to aggregate, diverse enough to show real divergence.
- **Beat 1 reframed as discussion-based, no individual writing.** Horizon question leads. Pair states a shared lens by the end of five minutes. Warms up the room faster and avoids the "stare at a blank page" failure mode.
- **Pre-demo feed synthesis is itself a micro-demo.** Facilitator copies Mentimeter Beat 3 responses into Cowork and asks for a theme synthesis, projected on the room screen. Sets up the Act 1 vs. Act 2 contrast and shows the tool in action before the formal demo begins.
- **Feed visibility during the demo.** Mentimeter Beat 3 output (or screenshot) stays visible on the room screen alongside Cowork during Acts 1 to 3, so participants can see their own positions interrogated live.
- **Demo is live in Cowork, not pre-built.** Resolves the live vs. pre-built question. Fallback recording is mandatory.
- **Act 2 horizon divergence is the headline moment.** Running the same prompt twice with declared horizons (90-day vs. 18-month) is what makes the framework lesson visceral. Pre-pick neither.
- **Act 3 sentiment data must be pre-staged as plain text blocks.** Not links, not PDFs. Drop-in ready.
- **Participant parity rule for the demo.** Only use tools participants could theoretically use themselves (general-purpose Cowork). No specialized connectors they don't have access to. The lesson is about *how* you use it, not *what* you have access to.

**Open questions surfaced today:**
- Beat 2's five structured prompts must be designed so participants end up close to "Act 1 unguided," not pre-trained on Act 2 thinking. The exercise has to leave room for the demo's framework-led reveal to land.
- The "thing" walked away with: branch-demo had a tangible dashboard. Earnings-demo's structured investment view plus horizon divergence is good but may need a more concrete take-home artifact.
- Equity-research plugin: install and use as Act 1 baseline, or use a generic Claude prompt? Leaning generic for replicability and to keep the lesson about prompting rather than tooling.

---

### 2026-05-25 — Demo framework decisions

Reviewed Anthropic's financial-services-plugins repo and the Earnings Reviewer agent's `earnings-analysis` skill. Mapped Steps 5 to 11. Decided the sell-side skill is the off-the-shelf baseline; the workshop value-add is the buy-side overlay (horizon, alpha edge, peer context, sentiment/positioning).

**Decisions made:**
- Demo is live in Cowork, three-act structure (resolves the live vs. pre-built question).
- Buy-side framework defined as four explicit dimensions added to the sell-side analytical core.
- Sentiment and positioning is about *positioning* not *information edge*. This distinction matters and should be made explicit in the demo (semi-strong EMH compatible).
- Horizon divergence is the Act 2 lesson: run the same prompt with different declared horizons and show how the output shifts.
- Data to pre-stage: PANW transcript, Form 4s, short interest, options skew, peer context (CRWD, FTNT, ZS).

---

### 2026-05-24 — Workshop confirmed, design session

**Confirmed logistics:**
- Slot confirmed by Jarvis. Workshop is 1 of 3 offered in parallel over the lunch break.
- U-shaped classroom (not boardroom as originally noted). Dedicated screen. Good WiFi. MacBook Pro plug-in allowed, need to buy adapter.
- Up to 15 participants, sign-in process. Workshops in parallel, so no straggler issue.
- Effective time is 45 minutes, not 60. Box lunch plus settling eats the difference. Plan for 45, design for 45.

**Design decisions made:**
- Phone-only participants are real and must be designed for, not worked around. Pairing is the response. (Refined on May 26 to apply to all pairs regardless of device.)
- Exercise brief must be mobile-readable and QR-accessible.
- Feedback capture must be phone-native: tap not type. Buy/Hold/Sell is a button, not a text field. Character limit on conviction and uncertainty fields.
- Settling poll: 3 questions, displayed during box lunch/settling. Q1 = AI journey diagnostic. Q2 = market reaction to domain-specific AI (anchored to PANW earnings June 2). Q3 = net positive for investment analysis, revisited at debrief.
- Learning objectives reframed around the primary objective: leave with a concrete practice for deploying a general-purpose tool on specific knowledge work tasks. Everything else is in service of that.
- The core gap the workshop addresses: people don't know how to use a general-purpose tool for specific tasks. They treat AI like a search engine.
- Co-worker model: "brief it, manage it, verify it." This is the mental model participants should leave with.
- CTA: "The next time you use AI on a real problem, notice whether you led with your framework or let AI set the agenda." Simple, behavioral, tied to the exercise.
- 4D framework documented in CLAUDE.md: Anthropic's Description, Discernment, Delegation, Diligence, extended with Data Literacy. Maps to 5 infrastructure components in Behind the Veil.

**Access note:** Branch-demo folder is not mounted in this session. To reference branch-demo materials, ask user to share specific slides or add the folder to the workspace.

---

### 2026-05-24 — Scheduled check-in (earlier today, before confirmation)

No work done today. No new files in `workshop/`, `demo/`, or `feed-app/`.

**Flag for Sandeep:** The internal kill date for Jarvis's confirmation (end of weekend May 23-24) has now passed with no response received. Decision needed: wind down the project, or make one final contact with a hard deadline and reset explicitly. Do not let the project linger in ambiguous state, no-go is a valid outcome that frees up time.

---

### 2026-05-13 — Project initialization

**Decisions made:**
- Project is a sibling to branch-demo, not a subfolder. Keeps CLAUDE.md context clean and prevents branch-demo session discipline from bleeding into this project.
- Three subfolders: `workshop/`, `demo/`, `feed-app/`. Each distinct build component gets its own space. (Feed-app subfolder now likely to be retired or repurposed after May 26 Mentimeter decision.)
- Feed mechanism will be a custom web app, not an off-the-shelf tool like Slido. The LLM aggregation is itself a demonstration of AI capability and needs to be purpose-built. (**Reversed on May 26**: Mentimeter selected. The pre-demo Cowork theme synthesis becomes the LLM demonstration of aggregation, which is arguably more direct.)
- Beat 2 compressed to 15 minutes (vs. branch-demo's 20-30). Workable with a structured post prompt but will need to be stress-tested in a dry run.
- The silent feed read (1 min) stays silent, no discussion until the debrief. The tension is deliberate.
- Structured post prompt for the feed: Buy/Hold/Sell plus one sentence biggest conviction plus one sentence biggest uncertainty. Gives the LLM aggregation something meaningful to work with.

**Carried over from branch-demo:**
- Never assume file contents. Read first, always.
- A fallback option for the demo is mandatory. Live demos fail.
- Dry runs surface things design sessions don't. Plan at least one before June 4th.
- The "what if we disagree" moment (branch-demo Act 2 Beat B) is the highest-value part of the demo. Protect time for the equivalent here. (Earnings-demo equivalent: Act 2 horizon divergence and Act 3 sentiment layer.)

---

## Synthesized Findings

*(Promote patterns here when they recur across sessions)*

**Pairing is a feature, not a constraint.** First surfaced May 24 as a phone-only accommodation, generalized May 26 to apply to all participants. The articulation/drive division of labor produces better analytical dialogue than parallel solo work. Carry this principle forward to any future workshop design where heterogeneous device or skill levels are expected.

**Reuse off-the-shelf platforms when LLM-aggregation can be demonstrated elsewhere.** Initial May 13 instinct was to build a custom feed app because LLM aggregation was itself a demo. May 26 reversal: Mentimeter handles capture, and the *pre-demo Cowork synthesis* becomes the LLM demonstration. The lesson generalizes: when the AI demonstration can happen anywhere in the flow, don't force it into a custom build that adds risk.

**Audience parity in tool selection.** The demo must only use tools participants could theoretically use themselves. Specialized connectors break the "you can do this too" lesson. Worth re-checking before installing any plugins (cf. equity-research plugin question).

**Pipeline fabrication is the same failure as content fabrication, one layer down.** Session 3 hard rules prevent fabricated analytical content from entering rendered output. Session 4 audit found the same failure pattern in the pipeline code: literal analytical figures embedded in the HTML generator's f-strings, silent `.get(key, literal_default)` fallbacks that mask missing data, hardcoded Form 4 transactions written as Python tuples instead of parsed from raw files. The hard rules need to extend to the pipeline layer. The build contract in `data-audit-findings.md` operationalizes this: provenance is mandatory, the generator interpolates DB query results only, missing data fails loudly.

**Cosmetic fixes are not fixes.** When fabricated content was called out in Session 3, the first instinct was to change labels (header from "Sell-Side Plugin Output" to "Claude Analysis") while the fabricated content remained. This compounded the failure rather than resolving it. The rule: if content is fabricated, remove it. Do not relabel.

**Process discipline must outlive the session that invented it.** The Design → Data → Script → Test → Learn → Build sequence was adopted in Session 3 in response to a specific failure. It was then partially bypassed in the same session when `generate_baseline.py` was written with embedded literal figures (Session 4 finding). Hard rules in markdown do not enforce themselves. Mechanical guardrails (tests, linters, stage commits) are what make discipline tool-independent.

**Stage gates belong in git, not markdown.** Session 5 operationalized this. The first stage-gate commit (`STAGE: Design approved 2026-05-27`) is the explicit approval moment a new agent can search for with `git log --grep="STAGE:"`. A markdown checkbox can be flipped without thought; a commit forces a deliberate act and leaves a timestamped, attributable record. Carry this pattern forward to any pipeline or build sequence that crosses a session boundary.

**The "manual/" folder is a first-class input, not a workaround.** Session 5 ratified this for materials that are not API-accessible at the required granularity (PANW press release PDFs, transcripts, earnings decks). A `manual/` folder with a README, a validation contract enforced by the gather script, and explicit failure on missing/invalid files is the right pattern. Distinguish this from the Session 3 anti-pattern of hardcoding values directly in code — the difference is that `manual/` content is sourced, named, validated, and traceable; hardcoded code values are none of those things.

**Agentic tool loops must reconcile every `tool_use` with a `tool_result` before the next round.** Surfaced in Session 8 when Tab 3's live chat broke on compound questions. The model can emit multiple parallel tool_use blocks in a single turn (e.g., two parallel `web_search` calls when asked to compare three companies on two dimensions). The loop has to collect every tool_use, run them all, post every matching tool_result, and only then submit the next user-or-model message. Skipping or merging tool_results yields a malformed conversation that the API rejects. Carry this pattern forward to any future agentic surface in the project.

**Use delimiter-based parsing, not JSON, when Claude responses may contain arbitrary quoted text.** When Claude grounds answers in earnings transcripts or call Q&A, management commentary (literal quoted speech) breaks `json.loads()`. Delimiter markers (`---FIELD---`) are robust against any content in the value. The fallback chain is: try JSON → try delimiters → exit loudly. Do not silently swallow parse errors.

**Fixed dimension definitions with variable questions is the right structure for reusable analytical frameworks.** Fixing the *definition* of each analytical lens and asking Claude to generate the quarter-specific *question* from it keeps the framework stable across quarterly refreshes while allowing the output to adapt to what each specific print actually raised. Phase B re-runs require no script edits — only new data. Apply this pattern to any recurring analytical workflow that shares a framework but needs quarter-specific output.

**Off-the-shelf skill output plus explicit departures is the demo's pedagogical shape.** Session 8 settled Tab 2 as the off-the-shelf sell-side baseline (`equity-research/earnings-analysis v0.1.0`), with the four places a buy-side practitioner would deliberately depart from the skill default surfaced as labeled departures in the rendered tab. This generalizes: when demonstrating a domain skill to sophisticated users, ship the unmodified default first, then make the human judgment visible as deliberate departures. The contrast is the lesson.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-13 | Project is a sibling to branch-demo, not a subfolder | Clean CLAUDE.md context, no interference between projects |
| 2026-05-13 | Feed app is a custom build | LLM aggregation is itself a demo of AI capability |
| 2026-05-13 | Palo Alto Networks as primary earnings call | Name recognition, June 2 timing, cybersecurity/AI governance relevance |
| 2026-05-13 | 60-minute hard ceiling on workshop | Jarvis's event constraint; designed tightly to fit |
| 2026-05-13 | Beat 1 is no-laptops | Creates friction that makes Beat 2 meaningful; carried from branch-demo |
| 2026-05-13 | Anonymous posting to feed | Senior participants won't post honest views if named |
| 2026-05-24 | Phone-only participants to pairing strategy | Pairing is a design improvement, not a workaround. Better analytical dialogue than two solo laptops. |
| 2026-05-24 | Effective time is 45 min, not 60 | Box lunch plus settling. Plan and script for 45. |
| 2026-05-24 | Settling poll anchored to PANW earnings (June 2) | Live example in the room two days before the event. Sets up the demo naturally. |
| 2026-05-24 | Primary learning objective: concrete practice for specific task deployment | "General purpose tool, specific tasks" is the gap. Everything else is in service of this. |
| 2026-05-24 | Co-worker model as the mental model | "Brief it, manage it, verify it." Replaces tool/assistant framing. |
| 2026-05-25 | Demo is live in Cowork, three-act structure | Most credible format for buy-side audience. Pre-built feels rehearsed. Fallback is mandatory. |
| 2026-05-25 | Four buy-side dimensions on top of sell-side baseline | Horizon, alpha edge, peer context, sentiment/positioning. Defines the investor's lens for the audience. |
| 2026-05-25 | Horizon divergence is the Act 2 reveal | Same prompt, different declared horizons. The delta makes the framework lesson visceral. |
| 2026-05-26 | Mentimeter plus GitHub Pages plus Cowork, no custom feed app | One Mentimeter join, one GitHub Pages QR. Reduces build risk; the AI aggregation demo moves to the pre-demo Cowork synthesis moment, which is arguably more direct. |
| 2026-05-26 | Pairing is the default for all participants regardless of device | Two phones works. The division of labor is the point, not the device. |
| 2026-05-26 | One post per pair to the feed | Cleaner aggregate, more diverse posts, naturally enforces pair discussion. |
| 2026-05-26 | Beat 1 is discussion-based with horizon question first | Warms up the room faster than individual writing; horizon is the most overlooked framework dimension. |
| 2026-05-26 | Participant parity rule for the demo | Demo only uses tools participants could theoretically use. Keeps the lesson about *how*, not *what*. |
| 2026-05-26 | Pre-demo Cowork theme synthesis is itself a micro-demo | Sets up Act 1 vs. Act 2 contrast naturally and shows AI aggregation before the formal demo. |
| 2026-05-27 | Six hard rules adopted in CLAUDE.md: no fabricated analytical content, no false attribution, no cosmetic fixes, stage gates with explicit approval, honest "cannot do" responses, Tab 2/3 placeholders preserved | Direct response to Session 3 fabrication in `earnings_baseline.html`. Without these the failure pattern recurs. |
| 2026-05-27 | Process sequence adopted: Design → Data → Script → Test → Learn → Build | Same Session 3 response. No stage skipped, no final-form output before preceding stages are complete. |
| 2026-05-27 | Data pipeline rebuild required; tool target is Claude Code | Session 4 audit found pipeline-layer fabrication that recapitulated Session 3 content fabrication. Git as discipline mechanism, terminal-first surface reduces the temptation to render polished output before data is right. |
| 2026-05-27 | Build contract drafted: provenance mandatory, no literal analytical figures in generator, no silent fallback defaults, stage gates as commits, schema-first documentation, portable paths | Operationalizes the hard rules at the pipeline layer. Tool-independent. Tests and linters enforce what markdown rules cannot. |
| 2026-05-27 | Documentation structure: lean STATUS.md, archive in STATUS-ARCHIVE.md, "why the rules exist" in LESSONS_LEARNED.md, single entry point in CLAUDE.md | Reduces handoff context bloat. A new agent doing the pipeline rebuild reads CLAUDE.md, `data-audit-findings.md`, `demo/demo_build_requirements.md`, and the raw files. STATUS.md is operator-facing, not required for execution. |
| 2026-05-27 (EOD) | Real Q2 FY26 source materials sourced into `demo/data/manual/` (corrected transcript, earnings presentation, supplemental financial information PDFs from the Feb 17, 2026 print) | Resolves the fiscal-year question. Renaming Q2 FY25 data was the easy path; sourcing the real Q2 FY26 print is the only path that holds up on June 4, when the live story in the room is the June 2 Q3 FY26 print and Q2 FY26 must be the most recent prior reference point. |
| 2026-05-27 (EOD) | `demo/data/SCHEMA.md` is the authoritative source-of-truth for all tables, columns, and provenance | Operationalizes the build contract in a single readable artifact. Six rules at top. Hardcoded supplements enumerated in a verification table. New agent reads SCHEMA.md before touching `rebuild_db.py`. |
| 2026-05-27 (EOD) | API stack locked: FMP + yfinance + edgartools + Anthropic | Covers GAAP P&L (FMP), price + peers (yfinance), Form 4s + filings (edgartools), PDF extraction + Q&A tagging (Anthropic). No new vendor lock-in beyond the audit recommendation. |
| 2026-05-27 (EOD) | `manual/` is a first-class input folder with a README, validation contract, and loud failure on missing files | Distinguishes legitimate manual ingestion (sourced, named, validated, traceable) from the Session 3 anti-pattern of hardcoded values in code (none of those things). |
| 2026-05-27 (EOD) | Stage gates expressed as git commits (`STAGE: <name> approved`), not markdown checkboxes | A markdown checkbox can be flipped without thought; a commit forces a deliberate act and leaves a timestamped, attributable record. First gate `STAGE: Design approved 2026-05-27` (fedd02c) closes the Design stage. |
| 2026-05-27 (EOD) | Hardcoded supplement verification status carried over from Q2 FY25 does not count | Each of the seven values in `SCHEMA.md` must be re-verified against the actual Q2 FY26 press release PDF before the Data stage closes. Marked "Pending" in the schema table. |
| 2026-05-28 | SEC EDGAR XBRL frames API added to the standing data stack | Backfills 4 null PANW YoY values and peer GAAP gross margins (FTNT, ZS) that yfinance / Alpha Vantage cannot supply for historical quarters. Not a one-off backfill — part of the pipeline going forward. |
| 2026-05-28 | After-hours reaction approximated by daily-bar overnight gap (Feb 17 close → Feb 18 open) | Free intraday after-hours feeds are not available. The daily-bar gap is the honest substitute. Closes the Session 6 known gap on `stock_ah_change_pct`. |
| 2026-05-28 | Sentiment signal cards lead with the positioning-vs-reaction disconnect, not raw KPI tiles | The story is the divergence between positioning (short interest, P/C) and the price reaction. A flat KPI grid buried the point. |
| 2026-05-28 | Tab 2 is the off-the-shelf sell-side baseline from `equity-research/earnings-analysis v0.1.0` (Option A: Steps 5–11 including recommendation), with four explicitly labeled departures | Resolves Open Question 7. The contrast between the skill default and the buy-side departures is the lesson — ship the default first, then make human judgment visible. Departures are surfaced in the rendered tab, not hidden in JSON. |
| 2026-05-28 | Tab 3 is hybrid: pre-run static buy-side Q&A accordion plus live chat surface | Resolves Tab 3 portion of Open Question 7. Static layer guarantees something to show; live layer is the agentic demonstration. Belt-and-suspenders against any live failure. |
| 2026-05-28 | Live chat stack: Claude Opus 4.7 + Tavily web search + FastAPI server + SSE streaming + DOMPurify | First agentic surface in the project. Live/offline badge on tab load. Suggestion chips lower friction of first interaction. Clear-history button for clean state. |
| 2026-05-28 | Agentic tool loop must match every `tool_use` block with a `tool_result` before the next round, no matter how many parallel calls Claude emits | Compound questions trigger multiple parallel `web_search` tool_use blocks in one turn. Skipping or merging tool_results yields a malformed conversation the API rejects. Promoted to Synthesized Findings. |
| 2026-05-28 | June 3 Phase B refresh procedure documented in STATUS.md | After June 2 Q3 FY26 print: re-run `demo/data/gather.py` → `run_earnings_analysis.py` → `generate_baseline.py`. Tab 2 updates automatically from the new JSON; no HTML edits. Tab 3 static Q&As re-run only if questions need to track new disclosures. |
| 2026-05-28 | Tab 3 static section redesigned: fixed dimension definitions + Claude-generated questions + recommendation synthesis | Original 5 Q&As missed the explicit buy-side framework (horizon, alpha edge, peer context, positioning). Fixed definitions are reusable across quarters; Claude generates the quarter-specific question from each. Phase B is a straight re-run, no script edits. |
| 2026-05-28 | Delimiter-based response parsing (`---FIELD---`) for structured Claude output containing quoted text | JSON parsing fails when transcript-grounded answers contain unescaped management quotes. Delimiter markers are robust against any content. Carry forward to any script asking Claude to produce structured output grounded in call transcripts. |
| 2026-05-28 | Tab 3 HTML: horizon banner + framework intro + dimension pills + always-visible recommendation card | Pedagogical sequence: declare the framework first (banner + 5 mini-cards), then show the output (accordions with dimension pill), then state the verdict (recommendation card). Matches how a real buy-side framework write-up is structured. |
| 2026-05-28 | "Bull case" chip replaced with "Horizon comparison" (how does the 6-month view change if this is a 3-month trade?) | Horizon is the primary departure between sell-side and buy-side analytical framing. The chip should reinforce the framework's core dimension, not restate a generic bull case. |
