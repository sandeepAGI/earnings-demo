# Status

*Last updated: 2026-05-27 (lean version; historical narrative and completed task
detail in `STATUS-ARCHIVE.md`. Why prior failures matter: `LESSONS_LEARNED.md`.)*

---

## Current Phase

Phase 2 (demo build) is **paused pending data pipeline rebuild**. The Session 4 audit found that the data values in the DB reconcile to the raw files, but the pipeline itself is not trustworthy: session-pinned paths in the build scripts, 0-byte canonical DB, hardcoded analytical prose in `generate_baseline.py`, and a critical fiscal-year labeling question (the test quarter labeled "Q2 FY26" is actually PANW's Q2 FY2025 from February 2025).

**Full findings:** `data-audit-findings.md` (project root).

Tab 1 of `earnings_baseline.html` is not final until the rebuild lands. Tabs 2 and 3 remain honest placeholders.

**Next action:** operator resolves the fiscal-year question, then writes the build contract drafted in `data-audit-findings.md` step 2, then rebuilds the pipeline (likely in Claude Code).

---

## Active Tasks

### Pipeline rebuild (blocked on operator decision)
- [ ] Resolve fiscal-year question: re-pull for fiscal date 2026-01-31, or rename existing data to Q2 FY25
- [ ] Finalize build contract from `data-audit-findings.md` step 2
- [ ] Rebuild pipeline in Claude Code: gather, schema doc, `rebuild_db.py`, provenance tests, `generate_baseline.py`
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
7. Six pipeline-specific open questions enumerated at the bottom of `data-audit-findings.md` (fiscal year, mounted FS workaround, omitted Form 4s, sparse Q4 FY25 row, peer period footnote, tool choice).

---

## Blockers

**Operator decision on the fiscal-year question.** Without it, all pipeline rebuild work is blocked. Everything downstream (Tab 1 finalization, Tab 2 design, demo script, fallback recording) depends on the rebuild.

---

## Data Quality Notes

(Kept here because these are operationally referenced during pipeline work. Move to `LESSONS_LEARNED.md` if they crystallize into general findings.)

**`panw_earnings_estimates.json`:** Original file had `actual_eps_nongaap_approx: "0.77"` which was wrong. Corrected to `actual_eps_nongaap: "0.81"` with a note field. Press release is authoritative; Q2 non-GAAP EPS was $0.81.

**`panw_income_statement.json`:** Gross margin field is GAAP (73.5%). Non-GAAP gross margin (76.6%) is in the press release narrative, not in this file. Use press release figures for non-GAAP comparisons.

**`eps_history`:** Only 14 quarters of history (back to Q1 FY23) on Alpha Vantage free tier. Sufficient for demo.

**Short interest / put-call:** Historical Feb 2025 data not accessible via static web fetch (both platforms are client-rendered JavaScript). Narrative fallbacks in respective `.txt` files. Phase B action: capture live via Claude in Chrome before June 2 print.

**`panw_q2fy26_press_release.json` line 62:** Deferred revenue note reads "Current .60B + LT .66B" (missing leading "5"s). Total ($11.26B) and the script's hardcoded values (5.60 + 5.66) confirm the typo. The DB is correct because of the hardcoded supplement; the raw JSON note should be fixed when the file is re-touched.
