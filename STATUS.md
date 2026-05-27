# Status

*Last updated: 2026-05-27 (end of day; historical narrative and completed task
detail in `STATUS-ARCHIVE.md`. Why prior failures matter: `LESSONS_LEARNED.md`.)*

---

## Current Phase

Phase 2 (demo build) — **pipeline rebuild active, Design stage approved.** The fiscal-year question is resolved: the operator obtained the actual PANW Q2 FY26 materials (Feb 17, 2026 print) and dropped the source PDFs into `demo/data/manual/`. The Design stage closed with the first stage-gate commit (`STAGE: Design approved 2026-05-27`). The build contract is operationalized in `demo/data/SCHEMA.md` (6 rules, signed-off hardcoded supplements enumerated). API stack locked: FMP + yfinance + edgartools + Anthropic. `gather.py` exists as the Stage 2 entry point; `rebuild_db.py` is in place. Pipeline now in the Data stage of the Design → Data → Script → Test → Learn → Build sequence.

**Full findings (audit):** `data-audit-findings.md` (project root).
**Schema source-of-truth:** `demo/data/SCHEMA.md`.

Tab 1 of `earnings_baseline.html` is not final until the rebuilt data flows through. Tabs 2 and 3 remain honest placeholders.

**Next action:** verify the seven signed-off hardcoded supplements against the actual Q2 FY26 press release PDF; complete the manual `panw_q2fy26_press_release_supplement.json` from the template; run `gather.py` end to end; commit `STAGE: Data approved`.

---

## Active Tasks

### Pipeline rebuild (Data stage active)
- [x] Resolve fiscal-year question: real Q2 FY26 materials sourced into `demo/data/manual/`
- [x] Finalize build contract — operationalized in `demo/data/SCHEMA.md` (6 rules at top)
- [x] API stack locked: FMP + yfinance + edgartools + Anthropic; `.env.example` added
- [x] Schema doc written: 13 tables mapped to sources, hardcoded supplements enumerated
- [x] `gather.py` (Stage 2 entry point) drafted; `manual/README.md` documents required files
- [x] Stage-gate discipline started: first commit `STAGE: Design approved 2026-05-27`
- [ ] Verify all 7 signed-off hardcoded supplements against actual Q2 FY26 press release PDF (table in `SCHEMA.md` is "Pending")
- [ ] Complete `panw_q2fy26_press_release_supplement.json` from the template in `manual/`
- [ ] Run `gather.py` end to end; confirm all raw files written with provenance
- [ ] Commit `STAGE: Data approved` once raw files validated
- [ ] Run `rebuild_db.py` → confirm provenance tests pass → commit `STAGE: Script approved`
- [ ] Re-run `generate_baseline.py` against rebuilt DB; remove silent fallbacks and hardcoded analytical prose
- [ ] Update `EARNINGS-ANALYSIS-GUIDE.md` to match the rebuilt schema

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

**Short interest / put-call:** Historical Feb 2025 data not accessible via static web fetch (both platforms are client-rendered JavaScript). Narrative fallbacks in respective `.txt` files. Phase B action: capture live via Claude in Chrome before June 2 print.

**`panw_q2fy26_press_release.json` line 62:** Deferred revenue note reads "Current .60B + LT .66B" (missing leading "5"s). Total ($11.26B) and the script's hardcoded values (5.60 + 5.66) confirm the typo. The DB is correct because of the hardcoded supplement; the raw JSON note should be fixed when the file is re-touched.
