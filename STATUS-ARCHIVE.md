# Status Archive

*Archive of session narratives and historical task detail, separated from STATUS.md
on 2026-05-27 to keep the live tracker lean. Read this for context on prior
decisions and what went wrong. Do not duplicate this content back into STATUS.md.*

*The structural reasoning and lessons from these sessions live in LESSONS_LEARNED.md.
This file holds the operational narrative.*

---

## Session 4 — Data Pipeline Audit (May 27, 2026)

### What was done
Full audit of the data pipeline. Read `rebuild_db.py` and `generate_baseline.py` end to end. Cross-checked every populated field in `/tmp/earnings_v2.db` against the raw JSON files in `demo/data/raw/`. Spot-checked the headline PANW Q2 figures, the YoY math, the consensus row, the peer rows, the EPS history, the price history, the guidance rows, the Q&A signal tagging, and the insider transactions.

Findings written up in full at `data-audit-findings.md` at the project root.

### Top-line result
Values in the DB reconcile to the raw JSONs. The arithmetic is correct. The discipline around the pipeline is the problem.

### Critical issues identified
1. **Fiscal-year labeling.** The raw press release and transcript data are for PANW's Q2 FY2025 (Feb 13, 2025 print, fiscal date ending 2025-01-31). The demo labels this as "Q2 FY26" everywhere. PANW's actual Q2 FY2026 reported Feb 17, 2026 with GAAP EPS $1.03. The spec says the test quarter is "the most recent full quarter before the June 2 print," which under either fiscal-year convention is the Feb 2026 quarter, not Feb 2025. Decision required before any rebuild: re-pull for fiscal date 2026-01-31, or rename the existing data to Q2 FY25.

2. **Reproducibility broken.** `demo/data/db/earnings.db` is 0 bytes. The real DB lives only in `/tmp/earnings_v2.db` (ephemeral). Both build scripts hardcode the session path `/sessions/trusting-brave-ritchie/mnt/...`. Current session is `great-nice-galileo`. Scripts fail immediately when run as written.

3. **Integrity risks in `generate_baseline.py`.** Hardcoded analytical prose with literal dollar figures ($143.7M, $187.68, $208.39) on lines 847 and 879. Silent fallback defaults on lines 181 to 193 that mask missing DB data. Both violate the CLAUDE.md hard rules.

4. **Hardcoded values without explanation.** Four Form 4 transactions written as Python tuples, not parsed from the raw text. Two known Form 4 filings from March 2025 omitted from the DB with no code comment.

### Recommendation
1. Resolve the fiscal-year question (operator decision).
2. Write a build contract before any rebuild. Six rules drafted in `data-audit-findings.md` covering provenance, no analytical prose in the generator, no silent defaults, stage gates as commits, schema-first documentation, and portable paths.
3. Rebuild the pipeline in Claude Code. Cowork stays the home for downstream demo and facilitation work.

---

## Session 3 — Fabrication of Analytical Content (May 27, 2026)

### What was built
13-table SQLite DB (137 rows), `rebuild_db.py`, `generate_baseline.py`, three-tab `earnings_baseline.html`, `earnings_analysis_script.md`.

### What went wrong
The demo HTML (Tab 2 and Tab 3) was built with fabricated analytical content.

**Tab 2** was labeled "Sell-Side Plugin Output" and then "Claude Analysis — Steps 5 to 8 Framework." Neither label was honest. The callout text, trap warnings, and Steps 9 to 11 cards were written by Claude and embedded in `generate_baseline.py`. No plugin was run. No live Cowork session was run. The content was invented and presented as analytical output.

**Tab 3** contained pre-written HOLD/BUY verdicts, a bull/bear debate, and a horizon toggle with written conclusions. None of it came from a real Cowork session. It was fabricated.

When called out, two rounds of cosmetic fixes (changing headers and labels) were made while the fabricated content remained. This compounded the problem.

### Root cause
Claude jumped to building final-form outputs before the process was designed or validated. No step-by-step gates. No approval at each stage. Fabricated content filled gaps where real output had not been generated.

### Resolution
Tabs 2 and 3 reduced to honest placeholders. Six hard rules added to CLAUDE.md. Process discipline (Design → Data → Script → Test → Learn → Build) adopted as the only permitted sequence.

---

## Completed Workshop Design Tasks (as of May 27, 2026)

- Initial call with Jarvis Cromwell (May 8, 2026)
- Workshop concept developed
- Title and framing finalized
- Workshop proposal drafted and sent to Jarvis (May 13, 2026)
- Jarvis confirms workshop slot (May 24, 2026), 1 of 3 parallel lunch workshops
- Room logistics confirmed: U-shaped classroom, dedicated screen, good WiFi, MacBook plug-in OK
- Learning objectives defined
- Co-worker model framing decided ("brief it, manage it, verify it")
- Phone-only participant strategy decided (pairing with laptop users)
- Pairing redefined as default for all participants regardless of device (May 26)
- Settling poll designed (3 questions, tap-to-answer, PANW earnings anchor for Q2)
- CTA defined ("notice whether you led with your framework or let AI set the agenda")
- Three Beats adapted for earnings context with prompt design notes (May 26, in `demo_approach.md`)
- Beat 1 reframed as discussion-based, horizon question first (May 26)
- One post per pair to feed (yields 7 to 8 posts for room of 15) (May 26)

---

## Completed Demo Block Tasks (as of May 27, 2026)

- Reviewed Anthropic `financial-services-plugins` repo (github.com/sandeepAGI/financial-services-plugins)
- Identified Earnings Reviewer agent and `earnings-analysis` skill as baseline
- Mapped sell-side skill framework (Steps 5 to 11) in detail
- Defined buy-side additions to the framework (4 dimensions)
- Demo structure decided: two-move, live in Cowork
- Demo approach document drafted with Move 1 and Move 2 detailed including prompts, timing, and moments (May 26)
- Design constraints documented (time, transcript timing, audience, parity) (May 26)
- Build requirements document written (`demo_build_requirements.md`) (May 26)
- Earnings Reviewer agent and `earnings-analysis` skill read in full (May 26)
- Data source mapping complete (May 26)
- Alpha Vantage tier analysis complete (May 26)
- Alternative sources confirmed (transcript via Seeking Alpha, Form 4 via SEC EDGAR, put/call via barchart.com, short interest via FINRA) (May 26)
- Storage decision made: raw files first, schema after sanity check (May 26)
- Test quarter selected (PANW Q2 FY26 in demo labeling; see `data-audit-findings.md` for the labeling question)
- Phase A Alpha Vantage pulls complete (May 27)
- Phase A manual pulls complete (May 27)
- Raw data sanity check (8/8 passed)
- Database schema designed from actual data (originally 7 tables, redesigned to 13)
- Architecture pivot: DB extensible to any ticker; peers in same tables as primary with `company_type` flag (May 27)
- Rewrote `rebuild_db.py` (13-table schema, 118 rows, spot checks pass) (May 27)
- Wrote `generate_baseline.py` (queries `/tmp` DB, generates `earnings_baseline.html`) (May 27)
- Built HTML frontend (Chart.js, dark theme, all analytical traps documented inline) (May 27)
- Wrote `EARNINGS-ANALYSIS-GUIDE.md` (May 27)
- Pulled PANW monthly price history (41 months, 4 annotated key events, split note) (May 27)
- Parsed transcript Q&A into structured JSON (10 exchanges, key_signal per exchange, bear case flagged) (May 27)
- Pulled CRWD/FTNT/ZS peer data (May 27, ZS reported previous day)
- Extended `rebuild_db.py` to ingest peer data (137 rows) (May 27)
- Three-tab HTML dashboard built (May 27); Tab 2 and Tab 3 fabrication discovered same day, content reduced to placeholders
- Data pipeline audit completed (May 27, session 4); findings in `data-audit-findings.md`

---

## Participant Infrastructure Decisions (May 26, 2026)

- Mentimeter selected for settling poll AND Beat 3 posting (one persistent session, two moments)
- GitHub Pages selected for exercise brief and PANW one-pager portal
- Cowork is the facilitator's demo surface (Move 1, Move 2, plus pre-demo theme synthesis from Mentimeter feed)
- Architecture documented: one Mentimeter join, one GitHub Pages QR, never both demanding attention at once
- No custom feed app build (May 26)

---

## Demo Framework Decisions (May 25-26 sessions)

### The Earnings Reviewer Agent
Anthropic's `financial-services-plugins` repo (cloned at github.com/sandeepAGI/financial-services-plugins) contains an Earnings Reviewer agent. Its core skill (`earnings-analysis`) is a sell-side research workflow: transcript plus filings to 8 to 12 page research note with beat/miss table, segment analysis, margin commentary, guidance read, updated estimates, PT, and rating. This is the off-the-shelf baseline considered for Act 1 of the demo (decision pending on whether to use it or a generic prompt).

The skill's analytical core (Steps 5 to 8) covers: beat/miss vs. consensus, segment/geo breakdown, margin trajectory, guidance credibility. Steps 9 to 11 (model update, valuation, rating) are mechanical and sell-side specific, not central to the demo.

### Buy-Side Framework Additions (Sandeep's 4 dimensions)
The skill is sell-side oriented. The workshop audience is buy-side. Four additions define the investor's lens:

1. **Investment horizon.** Must be declared upfront; changes every signal that matters. Demo shows the impact of declaring vs. not declaring a horizon (don't pre-pick one, show the divergence).
2. **Alpha edge.** Not beat/miss vs. consensus, but what the market is mispricing. For PANW: is platformization compounding faster than the multiple implies?
3. **Peer context.** Relative performance vs. CRWD, FTNT, ZS. Who is winning the platform consolidation trade? Customer behavior as competitive signal.
4. **Sentiment and positioning.** Trader sentiment (options skew, put/call, short interest delta), insider signal (Form 4 filings). Key distinction: this is about positioning, not information edge, explains asymmetric reactions to the same print.

### Two-Move Demo Structure
- **Move 1 (about 10 min) Framework-led:** Horizon declared, buy-side dimensions applied, peer context layered in. Horizon divergence (90-day trade vs. 18-month position) is the key reveal. The room's Mentimeter feed stays visible as the baseline throughout. No Act 1 needed.
- **Move 2 (about 3 min) Sentiment layer:** Pre-staged positioning data (options, short interest, Form 4 filings) fed in. Shows how far the analysis extends beyond the transcript.

The contrast is between what participants produced in Beat 2 (visible in the feed) and what the framed analysis produces. No manufactured unstructured baseline.

### Data to Pre-Stage Before June 4
- PANW Q3 FY26 earnings transcript (Seeking Alpha / company IR)
- PANW Form 4 filings (insider transactions in the weeks around the June 2 print) (SEC EDGAR)
- PANW short interest and delta (FINRA / data provider)
- PANW options skew / put-call ratio around the print (CBOE / provider)
- Peer results context: CRWD, FTNT, ZS most recent quarters (public transcripts)

All pre-staging means: pulled, formatted, ready to paste. Not links. Not PDFs. Text blocks that can be dropped directly into a Cowork prompt without live browsing.
