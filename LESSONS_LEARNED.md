# Lessons Learned

*Last updated: 2026-05-27*

This file captures technical workarounds, design decisions, and things that failed or surprised us. Update at the end of every working session. Promote patterns to findings when they recur.

---

## Synthesized Findings

### SQLite on mounted filesystem fails silently
**Pattern (confirmed):** SQLite databases cannot be reliably written to or read from the mounted workspace filesystem (`/sessions/.../mnt/`). `shutil.copy2()` reports success but writes 0 bytes. Binary `open(path, 'wb').write(data)` reports success but file remains 0 bytes. The `sqlite3` module raises `disk I/O error` when reading from the mount even if the file shows non-zero size. A stale `earnings.db-journal` file on the mount can block deletion.

**Solution:** DB lives in `/tmp` permanently. It is ephemeral across sessions — rebuilt by `rebuild_db.py` at the start of each session (takes ~1 second). The HTML artifact is the persistent output; it is plain text and writes cleanly to the mount.

**The two-step workflow:**
```
python3 demo/data/rebuild_db.py      # → /tmp/earnings_v2.db
python3 demo/generate_baseline.py    # → /mnt/.../earnings_baseline.html
```

**Related:** branch-demo CLAUDE.md documents the same pattern for `branch_selection.db`. Branch-demo's DB IS on the mount (29MB, working) — likely because it was built before the mount filesystem behavior changed, or because it was moved there via a different mechanism. Do not attempt to replicate.

---

## Session Log

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
