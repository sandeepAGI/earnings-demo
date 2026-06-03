# Status

*Last updated: 2026-06-03 — Q3 FY26 PANW print released June 2. All 7 pipeline scripts updated for Q3 FY26 refresh. PDFs dropped into `demo/data/manual/`. Placeholder sentiment files created (Playwright capture pending before June 4). Pipeline ready to run. (Historical narrative and completed task detail in `STATUS-ARCHIVE.md`. Why prior failures matter: `LESSONS_LEARNED.md`.)*

---

## Current Phase

Phase 2 (demo build) — **Tab 1 complete. Tab 2 complete. Tab 3 complete.**

Tab 1: all KPIs populated with actual values (200 rows, 39/39 provenance tests pass). After-hours reaction: -8.5% (yfinance daily, overnight gap). Sentiment: short interest 2.8% float (Playwright/MarketBeat), P/C 1.09/4.02 (Playwright/Barchart). *(Q2 FY26 baseline — Q3 FY26 refresh in progress)*

Tab 2: full sell-side analysis following `equity-research/earnings-analysis v0.1.0`. Steps 5–11 rendered from real JSON output. Rating: Maintain Outperform, PT $186 (+13.8% upside). 4 departures documented and visible. Script: `demo/data/analysis/run_earnings_analysis.py`. Output: `demo/data/analysis/panw_q3fy26_earnings_analysis.json`. *(Q3 FY26 output pending pipeline run)*

Tab 3: buy-side layer + live chat. Full framework redesign: horizon banner (6-month, alpha vs. market, buy-side), framework intro (5-dimension mini-cards with one-line definitions), 5 accordion cards (Claude-generated questions, dimension pill labels, answers pre-run), recommendation card (stance Buy, conviction/uncertainty/rationale from synthesis pass). Chat section: Claude Opus + Tavily web search via `demo/server.py` (FastAPI, SSE streaming, DOMPurify). Agentic loop handles compound questions: Claude may issue multiple parallel searches per turn; all tool_use blocks are matched with tool_results before the next round. Suggestion chips: Q3 metric, CRWD read, Horizon comparison (new), Organic ARR clarity. *(Q3 FY26 output pending pipeline run)*

**Rebuild summary:** `demo/data/gather.py` → 7 raw files → `demo/data/rebuild_db.py` → 13 tables / 200 rows → `demo/data/tests/test_provenance.py` (39 tests, all pass) → `demo/generate_baseline.py` → `demo/earnings_baseline.html`.

**Full findings (audit):** `data-audit-findings.md` (project root).
**Schema source-of-truth:** `demo/data/SCHEMA.md`.

**Next action:** Run the Q3 FY26 pipeline now (June 3): `python demo/data/gather.py` → `rebuild_db.py` → provenance tests → `run_earnings_analysis.py` → `run_buyside_analysis.py` → `generate_baseline.py`. After pipeline completes: (1) capture real sentiment data via Playwright (MarketBeat short interest + Barchart P/C), re-run rebuild_db.py with real figures, (2) build the PANW one-pager in Claude Code from the refreshed data layer (facts only, no sell-side/buy-side conclusions). See Active Tasks.

---

## Active Tasks

### Pipeline rebuild — COMPLETE
- [x] Resolve fiscal-year question: real Q2 FY26 materials sourced into `demo/data/manual/`
- [x] Build contract operationalized in `demo/data/SCHEMA.md` (6 rules at top)
- [x] API stack: FMP deprecated (free tier blocked Aug 2025), replaced with yfinance + edgartools + Anthropic PDF extraction + SEC EDGAR XBRL research done
- [x] `gather.py` run end to end — 7 raw files written with provenance
- [x] `rebuild_db.py` rewritten — 13 tables, 197 rows, 39/39 provenance tests pass
- [x] `generate_baseline.py` fixed — portable paths, no analytical callouts, no stale fallbacks, all dates from DB
- [x] `SCHEMA.md` updated with verified Q2 FY26 figures
- [x] `LESSONS_LEARNED.md` updated (Sessions 6 and 7)
- [x] Stage-gate commits: Design, Data, Script, Test, Learn, Build all committed
- [x] XBRL integration: backfilled 4 null PANW YoY values; populated GAAP gross margins for FTNT/ZS peers
- [x] Peer comparison charts added (Revenue YoY, Non-GAAP OI Margin horizontal bars, 4 companies)
- [x] Price event markers added ①②③④ — earnings report months annotated on price chart

### Tab 1 completion — COMPLETE
- [x] After-hours reaction KPI — yfinance daily, Feb 17 close $163.50 → Feb 18 open $149.55, gap -8.53%
- [x] Sentiment signal values — Playwright extraction: short interest 2.8% float (MarketBeat), P/C 1.09/4.02 (Barchart). Confidence=actual.
- [x] Sentiment cards redesigned — story-first layout surfacing the positioning/reaction disconnect

### Tab 2 — COMPLETE
- [x] Agreed on content: full sell-side output Steps 5–11 including recommendation (Option A)
- [x] Skill: `equity-research/earnings-analysis v0.1.0` from financial-services-plugins
- [x] Script written: `demo/data/analysis/run_earnings_analysis.py` — 4 departures labeled inline
- [x] Output validated: `panw_q2fy26_earnings_analysis.json` — Rating: Maintain Outperform, PT $186
- [x] Tab 2 wired into `generate_baseline.py` — all steps render from JSON, departures panel visible
- [x] HTML confirmed in browser — Steps 5–11 all render, peer table, valuation, skill banner
- [ ] **Phase B (June 3) — IN PROGRESS:** Q3 FY26 print released June 2. Scripts updated, PDFs in `demo/data/manual/`. Step 1: `python demo/data/gather.py`. Then rebuild_db.py → tests → run_earnings_analysis.py → generate_baseline.py.

### Tab 3 — COMPLETE
- [x] Design agreed: static buy-side Q&A (pre-run) + live chat (Claude API + Tavily)
- [x] Framework redesign: 5 fixed dimensions (Alpha Edge, Thesis Integrity, Guidance Credibility, Peer Context, Sentiment/Positioning) with Claude-generated quarter-specific questions
- [x] Script rewritten: `demo/data/analysis/run_buyside_analysis.py` — delimiter-based parsing, 6-call total (5 dims + synthesis), claude-opus-4-7
- [x] Output: `panw_q2fy26_buyside_analysis.json` — new schema: `framework` + `dimensions[]` + `recommendation` (stance: Buy)
- [x] Server bug fixed: `demo/server.py` — agentic loop collects ALL parallel tool_use blocks per turn, single tool_results user message → resolves 400 errors on compound questions
- [x] Tab 3 HTML: horizon banner, framework intro (5 mini-cards), 5 accordion cards with dimension pills, recommendation card (always visible), chat section, sauce panel
- [x] JavaScript: accordion toggle, suggestion chips, SSE chat streaming, DOMPurify sanitization
- [x] Live/offline server badge — pings `/chat` on tab load
- [x] End-to-end tested: simple, single-search, and multi-search compound questions all work
- [ ] **Phase B (June 3) — IN PROGRESS:** Re-run `run_buyside_analysis.py` after gather.py + rebuild_db.py complete.

### Workshop design
- [ ] Compressed 45-minute agenda pass
- [ ] Participant exercise brief (mobile-readable, QR-accessible)
- [ ] Facilitator guide
- [ ] Behind the Veil presentation outline (builds on Anthropic 4D framework)
- [ ] Run of show
- [ ] Backup earnings call identified

### Demo block
- [ ] Demo script (`demo_script.md`)
- [ ] Design Beat 2 prompt sequence for exercise brief
- [ ] Phase B: slot in Q3 FY26 data after June 2 print
- [ ] Fallback option (pre-recorded or scripted, mandatory)

### Participant infrastructure
- [x] Build Form 1: settling poll ("AI: Where Are You Starting From?") — Microsoft Forms, anonymous, Q1 MCQ + Q2 open text + Q3 Likert
- [x] Build Form 2: Beat 3 post ("Your view on Palo Alto Networks") — Microsoft Forms, anonymous, Q1 B/H/S MCQ + Q2 confidence 1-5 + Q3 primary reason + Q4 biggest risk
- [ ] Build PANW one-pager (GitHub Pages) — facts-only design, mobile-first, copy-paste friendly. Excludes Tab 2 sell-side and Tab 3 buy-side conclusions to preserve Beat 2 pedagogy. Sources from Q3 FY26 data layer post-refresh. Build in Claude Code from `demo/data/` artifacts.
- [ ] Drop real QR codes into Slides 4, 7, 8 of session_deck (settling poll, one-pager, Beat 3 post) once one-pager is live
- [ ] Test QR scans on multiple devices (iOS Safari, Android Chrome)
- [ ] Retire or repurpose `feed-app/` subfolder (Forms-based architecture replaced the custom feed plan)

### Polling platform decision (resolved 2026-06-02)
Microsoft Forms over Mentimeter. Reasons: bundled with M365 (zero cost), anonymous responses native, word cloud + bar chart + detailed-list visualizations in present mode, structured multi-field submission for Beat 3, Excel export, embeds in PowerPoint. Q3 re-poll cut from the original design (verbal show-of-hands at debrief replaces it).

### Logistics
- [ ] Buy MacBook Pro adapter before June 4

---

## Open Questions

1. Compressed 45-minute agenda: what gets cut to fit 45 effective minutes? (Behind the Veil can go 8 to 5 min; debrief is protected.)
2. Is Gil involved in this workshop or Sandeep solo?
3. Backup earnings call if Palo Alto Networks does not work for some reason.
4. Beat 2 prompt sequence: what are the exact structured prompts participants follow?
5. Concrete take-home artifact: branch-demo had a dashboard. What is earnings-demo's equivalent?
6. Fallback recording scope: both moves, or just Move 1? Move 2 (sentiment layer) is easiest to skip.
7. ~~**Tab 2 design:** What does Tab 2 contain — sell-side baseline (Steps 5–8 from Earnings Reviewer), buy-side framework output, or both? Does it serve as a static reference during the demo, or as the captured artifact of the live demo session? Resolve before any analysis is run.~~ **Resolved 2026-05-28:** Tab 2 = full sell-side output from `equity-research/earnings-analysis v0.1.0` Steps 5–11 (Option A) with four explicit departures. Tab 3 = hybrid: pre-run static buy-side Q&A accordion + live chat (Claude Opus + Tavily via FastAPI/SSE).
8. Pipeline (remaining from `data-audit-findings.md`): treatment of omitted Form 4s, sparse Q4 FY25 row handling, peer period footnote convention.

---

## Blockers

**No active blockers.** Demo build (Tabs 1–3) is complete as of 2026-05-28 EOD. Workshop materials (agenda, exercise brief, facilitator guide, run of show) and the demo script are open but not blocked on any decision or data dependency. Phase B (June 3 pipeline refresh after Q3 FY26 print) is a scheduled action, not a blocker.

---

## Data Quality Notes

(Kept here because these are operationally referenced during pipeline work. Move to `LESSONS_LEARNED.md` if they crystallize into general findings.)

**`panw_earnings_estimates.json`:** Original file had `actual_eps_nongaap_approx: "0.77"` which was wrong. Corrected to `actual_eps_nongaap: "0.81"` with a note field. Press release is authoritative; Q2 non-GAAP EPS was $0.81.

**`panw_income_statement.json`:** Gross margin field is GAAP (73.5%). Non-GAAP gross margin (76.6%) is in the press release narrative, not in this file. Use press release figures for non-GAAP comparisons.

**`eps_history`:** Only 14 quarters of history (back to Q1 FY23) on Alpha Vantage free tier. Sufficient for demo.

**Short interest / put-call:** Historical Feb 2026 data not accessible via static web fetch (both platforms are client-rendered JavaScript). Narrative fallbacks in `panw_q2fy26_short_interest.txt` and `panw_q2fy26_put_call.txt`. Current (May 2026) figures ARE in the context notes: short interest 3.11% float / 25.2M shares; P/C volume 0.94, P/C OI 1.01. Context note text erroneously says "Feb 2025" — should be "Feb 2026". Phase B: capture live via Claude in Chrome before June 2 print for real Feb 2026 historical figures.

**After-hours reaction (Q2 FY26):** `stock_ah_change_pct` and `stock_close_day_of` KPIs are missing from `company_kpis`. The `stock_reaction` block in `panw_q2fy26_press_release.json` contains Q2 FY25 data (source URL is the Feb 2025 press release, `close_price_day_of: 187.68` exceeds Feb 2026 monthly high of $177.73). Do not use. Fix: add `yf.Ticker("PANW").history(period="5y", interval="1d")` to `gather.py`, save as `panw_price_daily.json`, then in `rebuild_db.py` use Feb 17 close and Feb 18 open to compute the post-earnings gap.

**`panw_q2fy26_press_release.json` line 62:** Deferred revenue note reads "Current .60B + LT .66B" (missing leading "5"s). Total ($11.26B) and the script's hardcoded values (5.60 + 5.66) confirm the typo. The DB is correct because of the hardcoded supplement; the raw JSON note should be fixed when the file is re-touched.
