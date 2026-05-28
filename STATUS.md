# Status

*Last updated: 2026-05-28 (historical narrative and completed task detail in
`STATUS-ARCHIVE.md`. Why prior failures matter: `LESSONS_LEARNED.md`.)*

---

## Current Phase

Phase 2 (demo build) — **Tab 1 visual layer in progress. Pipeline rebuild complete.**

All 6 stages of the pipeline rebuild landed on 2026-05-27. Tab 1 charts are rendering with verified Q2 FY26 figures. Two visual enhancements added 2026-05-28: peer comparison bar charts (Revenue YoY, Non-GAAP OI Margin) and price event markers ①②③④. Two KPI fields remain unpopulated: `after_hours_reaction` (no daily price data in current pipeline) and sentiment signal numeric values (client-rendered source sites). See Data Quality Notes.

**Rebuild summary:** `demo/data/gather.py` → 7 raw files → `demo/data/rebuild_db.py` → 13 tables / 198 rows → `demo/data/tests/test_provenance.py` (39 tests, all pass) → `demo/generate_baseline.py` → `demo/earnings_baseline.html`.

**Full findings (audit):** `data-audit-findings.md` (project root).
**Schema source-of-truth:** `demo/data/SCHEMA.md`.

**Next action (Tab 1 completion):** Populate after-hours reaction and sentiment signal values — see Data Quality Notes for approach. After Tab 1 is complete, begin workshop materials track.

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

### Tab 1 completion
- [ ] After-hours reaction KPI — add daily price data to `gather.py` (yfinance 1d interval) and backfill `stock_ah_change_pct` + `stock_close_day_of` KPIs in `rebuild_db.py`
- [ ] Sentiment signal values — extract short interest % and put/call ratio from context notes; update `sentiment_signals` table with `value` fields (tag as May 2026 current figures, confidence=estimated)

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
- [ ] Build Mentimeter session (settling poll plus Beat 3 posting slide)
- [ ] Build GitHub Pages site (exercise brief plus PANW one-pager)
- [ ] Generate QR codes and test on multiple devices
- [ ] End-to-end test of Mentimeter Beat 3 to Cowork synthesis flow
- [ ] Retire or repurpose `feed-app/` subfolder

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
7. Pipeline (remaining from `data-audit-findings.md`, fiscal-year question now resolved): mounted FS workaround for DB, treatment of omitted Form 4s, sparse Q4 FY25 row handling, peer period footnote convention.
8. Stage-gate discipline started in Design — is the same commit pattern (`STAGE: <name> approved`) sufficient for Data/Script/Test/Learn, or does each stage need mechanical guardrails (tests, linters) per the Session 4 finding?

---

## Blockers

**Fiscal-year question resolved (2026-05-27 EOD).** Actual Q2 FY26 source PDFs are in `demo/data/manual/`. Pipeline rebuild now active, no external blockers. Downstream work (Tab 1 finalization, Tab 2 design, demo script, fallback recording) remains dependent on the rebuild reaching the Test stage, but it is no longer blocked on a decision.

---

## Data Quality Notes

(Kept here because these are operationally referenced during pipeline work. Move to `LESSONS_LEARNED.md` if they crystallize into general findings.)

**`panw_earnings_estimates.json`:** Original file had `actual_eps_nongaap_approx: "0.77"` which was wrong. Corrected to `actual_eps_nongaap: "0.81"` with a note field. Press release is authoritative; Q2 non-GAAP EPS was $0.81.

**`panw_income_statement.json`:** Gross margin field is GAAP (73.5%). Non-GAAP gross margin (76.6%) is in the press release narrative, not in this file. Use press release figures for non-GAAP comparisons.

**`eps_history`:** Only 14 quarters of history (back to Q1 FY23) on Alpha Vantage free tier. Sufficient for demo.

**Short interest / put-call:** Historical Feb 2026 data not accessible via static web fetch (both platforms are client-rendered JavaScript). Narrative fallbacks in `panw_q2fy26_short_interest.txt` and `panw_q2fy26_put_call.txt`. Current (May 2026) figures ARE in the context notes: short interest 3.11% float / 25.2M shares; P/C volume 0.94, P/C OI 1.01. Context note text erroneously says "Feb 2025" — should be "Feb 2026". Phase B: capture live via Claude in Chrome before June 2 print for real Feb 2026 historical figures.

**After-hours reaction (Q2 FY26):** `stock_ah_change_pct` and `stock_close_day_of` KPIs are missing from `company_kpis`. The `stock_reaction` block in `panw_q2fy26_press_release.json` contains Q2 FY25 data (source URL is the Feb 2025 press release, `close_price_day_of: 187.68` exceeds Feb 2026 monthly high of $177.73). Do not use. Fix: add `yf.Ticker("PANW").history(period="5y", interval="1d")` to `gather.py`, save as `panw_price_daily.json`, then in `rebuild_db.py` use Feb 17 close and Feb 18 open to compute the post-earnings gap.

**`panw_q2fy26_press_release.json` line 62:** Deferred revenue note reads "Current .60B + LT .66B" (missing leading "5"s). Total ($11.26B) and the script's hardcoded values (5.60 + 5.66) confirm the typo. The DB is correct because of the hardcoded supplement; the raw JSON note should be fixed when the file is re-touched.
