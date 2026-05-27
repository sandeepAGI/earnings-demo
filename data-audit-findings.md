# Data Audit Findings

*Created: 2026-05-27. This document captures the findings from a full audit of
the earnings-demo data pipeline (raw files, `rebuild_db.py`, `/tmp/earnings_v2.db`,
`generate_baseline.py`, `earnings_baseline.html`). It exists so the rebuild work
can begin from a clean baseline. A future agent (Claude Code or otherwise) should
read this end to end before touching the pipeline.*

*This document is honest about what was found. The CLAUDE.md hard rules apply.
Nothing here is paraphrased from a file that was not actually read.*

---

## Top line

The data values currently in `/tmp/earnings_v2.db` reconcile faithfully to the
raw JSON files for every field with a JSON source. The arithmetic checks out.
The Q&A bear case tagging is correct. The peer rows match their source files.
The accuracy problem is not at the value level.

The accuracy problem is at the **discipline level**. Provenance is incomplete,
the canonical database path is broken, the build scripts are not portable across
sessions, and the dashboard generator embeds analytical prose with hardcoded
figures that will silently misrepresent data once the underlying numbers change.
Worst of all, the test quarter labeled "Q2 FY26" everywhere in the demo is
actually PANW's Q2 FY2025 print from February 2025, not the Q2 FY2026 quarter
that PANW reported in February 2026.

A full rebuild is recommended, gated by a written contract, with the
fiscal-year question resolved first.

---

## Critical issue 1: the test quarter is labeled wrong (or the data is stale)

The raw press release JSON, transcript, and Q&A data are for PANW's
**Q2 FY2025**, reported February 13, 2025, fiscal period ending January 31, 2025.

Evidence:

- `panw_q2fy26_press_release.json` line 4 URL ends in
  `palo-alto-networks-reports-fiscal-second-quarter-2025-financial`
- `panw_q2fy26_transcript.txt` line 1 header reads literally:
  `PALO ALTO NETWORKS Q2 FY2026 (Fiscal Q2 2025) EARNINGS CALL TRANSCRIPT`
- The transcript's own first paragraph (Walter Pritchard speaking) opens with
  "welcome to Palo Alto Networks' second quarter 2025 earnings conference call"
- `panw_earnings.json` (Alpha Vantage) shows PANW's **actual** Q2 FY2026
  reported on 2026-02-17 with GAAP EPS of $1.03 against estimate $0.94
- The Q2 FY2026 quarter reported Feb 2026 is what PANW IR and the public market
  call Q2 FY2026

The demo applies a "Q2 FY26" label to the Feb 2025 quarter throughout. The spec
in `demo/demo_build_requirements.md` line 198 states:
"Q2 FY26 (reported February 2025) is the recommended test quarter. It is the
most recent full quarter before the June 2 print."

Those two claims contradict each other. Four PANW quarters were reported
between the Feb 2025 print and the upcoming June 2, 2026 print:

| Report date | Fiscal date ending | PANW IR label | Alpha Vantage GAAP EPS |
|---|---|---|---|
| 2025-02-13 | 2025-01-31 | Q2 FY25 | $0.38 (what is in the demo) |
| 2025-05-20 | 2025-04-30 | Q3 FY25 | $0.80 |
| 2025-08-18 | 2025-07-31 | Q4 FY25 | $0.95 |
| 2025-11-19 | 2025-10-31 | Q1 FY26 | $0.93 |
| 2026-02-17 | 2026-01-31 | Q2 FY26 | $1.03 |

If the goal is "the most recent full quarter before June 2, 2026," the test
quarter is fiscal date 2026-01-31 with EPS $1.03, not fiscal date 2025-01-31
with EPS $0.38.

This is the first thing to resolve. Until it is resolved, every downstream
artifact (HTML dashboard, EARNINGS-ANALYSIS-GUIDE.md, demo script) is anchored
on data that is 15 months stale.

**Decision required:**

1. Is the Feb 2025 print intentional as a historical case study, in which case
   the labels need to change to match (Q2 FY25 throughout, or whatever
   convention is preferred), OR
2. Is the data the wrong quarter and should be re-pulled for fiscal date
   2026-01-31?

The natural reading of the spec, combined with the fact that the dashboard's
analytical commentary references "Q3 FY26 reports June 2," strongly suggests
option 2.

---

## Critical issue 2: reproducibility is broken

### The canonical database does not exist

`demo/data/db/earnings.db` is **0 bytes**. The orphan journal file
`earnings.db-journal` (512 bytes) suggests a write was attempted and aborted.
The actual data lives only in `/tmp/earnings_v2.db` (about 106 KB, 13 tables,
118 rows).

A comment in `rebuild_db.py` explains: "SQLite on the mounted FS fails silently.
Do NOT copy DB to mount." So this is a known workaround. But it means the
database has no persistence beyond the current Cowork sandbox. Every fresh
session needs a full rebuild from raw to recreate it. There is no canonical
artifact a teammate or auditor can open.

### The build scripts are pinned to a stale session path

Both scripts hardcode an old session path:

- `rebuild_db.py` line 25: `RAW = '/sessions/trusting-brave-ritchie/mnt/earnings-demo/demo/data/raw'`
- `generate_baseline.py` line 24: `OUT_PATH = '/sessions/trusting-brave-ritchie/mnt/earnings-demo/demo/earnings_baseline.html'`

The current session is `great-nice-galileo`. Running either script as written
fails immediately with `FileNotFoundError`. The HTML in the workspace was
generated against the old session and has not been refreshed since.

Two-line fix per script. Use `os.path.dirname(__file__)` style path resolution
so the scripts find their own siblings regardless of session name.

---

## Data accuracy: what passes

For every field that has a JSON source, the DB value matches the raw file
exactly. Verified items:

**PANW Q2 (the labeled "Q2 FY26") quarterly_financials row.** All 18 income
statement fields match `panw_q2fy26_press_release.json`. Revenue 2,257.4M,
gross profit 1,658.2M, GAAP OI 240.4M, non-GAAP OI 640.4M, GAAP EPS $0.38,
non-GAAP EPS $0.81, net income 267.3M.

**Historical PANW quarters.** Three quarters present (Q1 FY26 / 2024-10-31,
Q4 FY25 / 2024-07-31, Q2 FY25 / 2024-01-31) all match `panw_income_statement.json`
exactly. The other three quarters in the script's HIST_MAP (Q3 FY25, Q1 FY25,
Q4 FY24) are absent from the source JSON, so the DB correctly has no rows for
them. The revenue trend chart shows four bars as a result.

**YoY revenue math.** 2,257.4 / 1,975.1 minus 1 equals 14.29 percent. Press
release states 14.3 percent. Match.

**Consensus row.** EPS consensus $0.7793, revenue consensus $2,239.8M, 43
analysts. Matches `panw_earnings_estimates.json`.

**Peer rows.** CRWD Q4 FY26 (rev 1,313, YoY 23.0, OI margin 25.0), FTNT Q1 2026
(rev 1,850, YoY 20.0, OI margin 35.8), ZS Q3 FY26 (rev 850.5, YoY 25.0,
OI margin 23.0, GAAP not profitable). All three match their respective JSON
files.

**EPS history.** 14 quarters from `panw_earnings.json` loaded correctly.

**Price history.** 41 months from `panw_price_monthly.json` loaded correctly.
Feb 2025 row (open 181.56, high 208.39, low 180.12, close 190.43) matches
exactly. The dip-and-rip pattern referenced throughout the dashboard
(close 187.68 on Feb 13, recovery to 208.39 by Feb 19) is sourced.

**Guidance.** Seven guidance rows all derive from the press release JSON's
`guidance_q3_fy26` and `guidance_fy26_full_year` blocks. The "raise" flag on
FY26 EPS guidance matches the JSON note.

**Q&A tagging.** All 10 exchanges loaded from `panw_q2fy26_transcript_qa.json`.
Distribution: 5 bullish, 4 neutral, 1 bearish. The bearish exchange is
exchange 9, Andrew Nowinski at Wells Fargo, with the bear case on net new ARR
ex-QRadar declining year over year. This is correctly identified as the
key bear case.

**Sentiment signals.** Three rows. All correctly flagged
`confidence='estimated'` or `confidence='inferred'`, with explicit text noting
that historical Feb 2025 data is not accessible via static fetch.

---

## Hardcoded values: full audit

The script supplements the JSON with hardcoded values in three categories.

### Category A: hardcoded but flagged with provenance in code

These are stated in the press release narrative but absent from the JSON
structured fields. Each has an inline comment explaining the source. They are
acceptable in principle but need independent verification against the original
press release PDF before being trusted.

| Value | Hardcoded as | Stated source |
|---|---|---|
| Non-GAAP gross margin | 76.6% | Press release text |
| EBITDA | $412.9M | Explicitly labeled approximation |
| FCF | $509.0M | Press release text |
| FCF margin | 22.5% | Press release text |
| Deferred revenue current | $5.60B | Press release text |
| Deferred revenue long-term | $5.66B | Press release text |
| Platformized customers | 1,150 | Earnings call transcript |

### Category B: hardcoded without explanation

Four Form 4 transactions are written directly as Python tuples in
`rebuild_db.py` lines 688 to 707, not parsed from the raw text file
`panw_q2fy26_form4_summary.txt`. The four loaded values reconcile to the raw
text. However, the raw text documents **six** Form 4 filings in the window.
The two omitted (Arora ~$50M+ on 2025-03-03, Klarich ~$10M+ on 2025-03-03) have
no comment in code explaining their exclusion.

There is also a small inconsistency on Arora's Feb 4 filing: the raw text
summary table lists $54.1M while the detail section says $54.2M. The DB stores
$54.2M. Worth resolving.

### Category C: hardcoded analytical prose in the HTML generator

This is the most serious integrity risk.

`generate_baseline.py` line 847:
> CEO Arora's $143.7M block exercised options expiring Dec 2025 at a $33 strike,
> plan adopted March 2024 9+ months prior.

`generate_baseline.py` line 879:
> The dip-and-rip ($187.68 → $208.39 in 6 days) is the most reliable
> positioning proxy.

Both contain dollar figures as literal f-string text, not interpolated from
the DB. If the DB is updated for Q3 FY26 (after the June 2 print), these strings
will still claim Q2 numbers. This is exactly the failure mode `CLAUDE.md` hard
rule 1 is designed to prevent: analytical conclusions written into a template
rather than derived from a real run.

These two lines must be either deleted, marked explicitly as commentary about
the test quarter only, or rewritten to interpolate from DB values.

---

## Integrity risk: silent fallback defaults

`generate_baseline.py` lines 181 to 193 read values from the DB with literal
defaults:

```python
eps_nongaap   = panw_q2.get('eps_nongaap', 0.81)
eps_cons      = consensus.get('eps_consensus_nongaap', 0.779)
rev_total     = panw_q2.get('revenue_total_m', 2257.4)
oi_nongaap_m  = panw_q2.get('operating_income_nongaap_m', 640.4)
oi_margin_ng  = panw_q2.get('operating_margin_nongaap_pct', 28.4)
q3_eps_lo     = g_q3_eps.get('low_value', 0.76)
q3_eps_hi     = g_q3_eps.get('high_value', 0.77)
q3_arr_lo     = g_q3_arr.get('low_value', 4.90)
q3_arr_hi     = g_q3_arr.get('high_value', 4.95)
q3_rev_lo     = g_q3_rev.get('low_value', 2260)
q3_rev_hi     = g_q3_rev.get('high_value', 2290)
fy_fcf_lo     = g_fy_fcf.get('low_value', 37)
fy_fcf_hi     = g_fy_fcf.get('high_value', 38)
```

If the DB row is empty, the key is missing, or the lookup is wrong, the
dashboard silently renders the literal default instead of erroring. The
"data-driven from DB" guarantee is not actually enforced.

Replace these with raises or explicit assertions. The pipeline should fail
loudly when expected data is missing.

---

## Minor cleanup items

**Raw JSON transcription typo.** `panw_q2fy26_press_release.json` line 62
reads `"Current .60B + LT .66B"`. Missing the leading "5" on both numbers.
The script's hardcoded values (5.60 + 5.66 = 11.26) and the deferred revenue
total in the same JSON both indicate the correct values are 5.60 and 5.66.
The DB is correct because of the hardcoded supplement. The raw JSON note
should be fixed for cleanliness.

**Q4 FY25 row has only revenue.** Gross profit, operating income, and net
income are null in `panw_income_statement.json` for fiscal date 2024-07-31.
The DB correctly stores nulls. The chart correctly shows a gap. This is a
source data limitation, not a bug. Worth documenting in `data/DATA-GUIDE.md`
so it does not surprise a reviewer.

**Sparse historical data.** Only three of the six expected historical PANW
quarters are present in `panw_income_statement.json`. The revenue trend chart
shows four bars total (three historical plus Q2 FY26). If a longer trend is
desired for the demo, the raw data needs to be supplemented.

**Two unused raw files.** `panw_q2fy26_short_interest.txt` and
`panw_q2fy26_put_call.txt` are narrative fallbacks. They are referenced as the
`data_source` for sentiment_signals rows but their actual text is not parsed.
This is acceptable given the explicit "estimated" or "inferred" confidence
flags, but a reviewer should know the text is not the source of any numbers.

**Tab 2 and Tab 3 placeholders.** Correctly preserved as placeholders per the
`CLAUDE.md` hard rule. No fabricated analysis content. The script in
`generate_baseline.py` references `setHz()` and elements like `hz-90d-content`
that no longer exist in the HTML. Dead JavaScript. Harmless but worth removing
when the file is touched.

---

## What the dashboard correctly does well

Worth noting so the next rebuild does not lose what is already right.

The "GAAP OI Trap" callout in the headline KPIs is sourced and correctly
attributes the 348% YoY GAAP OI growth to the $175.4M litigation normalization
swing. The non-GAAP comparison (+13.5% non-GAAP OI YoY) is the right anchor.

The "Guidance Trap" callout correctly flags that Q3 non-GAAP EPS guidance
$0.76 to $0.77 is below the Q2 actual $0.81, identifies sequential margin
pressure from SaaS scale as the driver, and notes the 13 of 14 beat history
as the credibility context.

The bear case on net new ARR ex-QRadar is correctly attributed to Andrew
Nowinski (Wells Fargo) exchange 9, with the underlying numbers in the Q&A
table and the analytical note.

Insider transactions are honestly framed as 10b5-1 (non-discretionary),
with the strike price and plan adoption dates included. The "$143.7M block"
narrative is internally consistent (89.5 plus 54.2).

Peer comparison is honest about fiscal period misalignment (PANW Q2 FY26,
CRWD Q4 FY26, FTNT Q1 2026, ZS Q3 FY26 are all shown with their period labels).
The note about NGS ARR leading revenue by 4 to 6 quarters is correct framing.

---

## Recommended path forward

The order matters.

### Step 1: resolve the fiscal-year question

Before any rebuild. Two options:

A. Re-pull the data for fiscal date 2026-01-31 (PANW's actual Q2 FY26 reported
   Feb 17, 2026). The Alpha Vantage EPS history confirms this quarter exists
   and EPS came in at $1.03 versus $0.94 consensus (about +9.6% surprise).
   New transcript, new press release, new Form 4 window. Peer quarters may
   shift accordingly. This is the option consistent with "most recent full
   quarter before June 2 print."

B. Rename "Q2 FY26" to "Q2 FY25" throughout the codebase (DB rows, scripts,
   dashboard, guides) to match the actual data. Then accept the test quarter
   is 15 months stale relative to where the demo audience will be on June 4.

Option A is what the spec actually wants. Option B is a smaller rewrite but
leaves the demo telling a story about a quarter the audience will treat as
old news.

### Step 2: write the build contract

Before any rebuild. The contract spells out what discipline looks like in this
project. A starting draft:

1. **Provenance is mandatory.** Every row in every table has a non-null
   `data_source` field. A test (`tests/test_provenance.py`) walks the DB and
   asserts each `data_source` value points to a real file under `demo/data/raw/`.
   Build fails if it breaks.

2. **No analytical prose in the generator.** The HTML generator
   (`generate_baseline.py`) cannot contain literal analytical figures in text.
   It can interpolate DB query results, or read prose from a separate
   `demo/narrative.md` file that is reviewed at the Build stage. A linter rule
   greps the generator for dollar signs and percent signs in string literals
   and fails the build if any are found outside f-string interpolation.

3. **No silent fallback defaults.** All `.get(key, default)` patterns in the
   generator are replaced with raises or explicit assertions. Missing data
   fails loudly.

4. **Stage gates are commits.** Every transition through
   Design → Data → Script → Test → Learn → Build is a commit titled
   `STAGE: <name> approved <date>`. No work proceeds without it.

5. **Schema is documented first.** A single `demo/data/SCHEMA.md` enumerates
   every table, every column, and for each column states either the source raw
   file and JSON path, or "hardcoded supplement" with a quoted source statement
   from the original press release / transcript. Hardcoded supplements get
   explicit sign off at the Data stage.

6. **DB path is portable.** Build scripts resolve paths relative to their own
   location. No session-pinned absolute paths. The canonical DB lives at
   `demo/data/db/earnings.db`, written atomically. The
   "SQLite on mounted FS fails silently" workaround needs verification: if it
   is still real in this sandbox, document the exact failure mode and the
   `/tmp` mitigation in `LESSONS_LEARNED.md`. If it can be solved, solve it.

### Step 3: rebuild

Only after steps 1 and 2.

A. Run gather for the resolved quarter. Land raw files in `demo/data/raw/`.
   Do not transform.

B. Build the schema doc from the actual data.

C. Write `rebuild_db.py` against the schema. Run it. Confirm the verification
   spot checks pass.

D. Write `tests/test_provenance.py`. Run it. Confirm clean.

E. Write `generate_baseline.py` against the DB. Run it. Confirm no literal
   figures in the source.

F. Open the resulting HTML. Confirm visually.

G. Commit each stage. Update `STATUS.md` and `LESSONS_LEARNED.md`.

### Tool recommendation

This rebuild belongs in Claude Code, not Cowork. The pipeline only needs
filesystem, shell, and web fetch. Claude Code has all three natively, plus
git as a first-class discipline mechanism. The Cowork-specific MCPs
(Apollo, Common Room, Slack, financial analysis skills) are not useful for
the pipeline. Once the data is locked and the dashboard is rebuilt, the
demo design and facilitation work can come back to Cowork.

The contract in step 2 above is the same regardless of tool. Writing it down
makes the discipline tool independent.

---

## Open questions for the operator

Numbered for easy reference.

1. Fiscal-year resolution: option A (re-pull Feb 2026 data) or option B
   (rename to Q2 FY25)?

2. The "SQLite on mounted FS fails silently" comment in `rebuild_db.py`.
   Is this still real in the current sandbox, or was it a transient issue
   that can now be solved? If real, what is the exact failure mode? Worth
   testing before declaring `/tmp` the permanent home.

3. The two omitted Form 4 filings (Arora 2025-03-03, Klarich 2025-03-03):
   intentional cutoff at the pre-earnings window, or accidental? If
   intentional, the script needs a comment explaining the window definition.

4. The Q4 FY25 row has revenue only. Acceptable as a sparse historical row,
   or should it be supplemented from the actual press release?

5. The peer fiscal quarter misalignment (CRWD Q4 FY26, FTNT Q1 2026,
   ZS Q3 FY26) is currently shown honestly in the peer table. Should the
   dashboard add an explicit footnote explaining why the periods diverge,
   or leave the period column to do the work?

6. Where should the rebuild work live? A new Claude Code session pointed at
   this same workspace folder is the recommendation. Confirm before starting.

---

*This file should be re-read at the start of the rebuild session. When the
rebuild is complete, update this file with the resolution of each open
question and a delta of what changed.*
