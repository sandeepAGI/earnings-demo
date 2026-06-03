# Earnings Demo: Project Context

The objective of this project is to design and build a hands-on AI workshop on earnings call analysis, targeted at a financially sophisticated but heterogeneous audience. It demonstrates the value of using LLMs as analytical partners on a real-world investment problem — and the importance of human judgment at the jagged frontier.

This is a sibling project to `branch-demo` (at `../branch-demo`). It shares the same pedagogical philosophy — participants work the problem before seeing the AI-assisted approach — but targets a different audience and uses a different analytical domain. Do not copy branch-demo artifacts wholesale; reference and adapt deliberately.

---

## Entry points for new sessions

This file (`CLAUDE.md`) is the single orientation document. Read it first regardless of scope. Then branch based on what you are here to do.

**For workshop design and facilitation work:** read this file, then `STATUS.md` (active tasks, open questions, blockers), then `LESSONS_LEARNED.md` (design decisions and why prior choices were made the way they were).

**For the data pipeline rebuild:** read this file, then `data-audit-findings.md` (what was found in the 2026-05-27 audit and the build contract draft), then `demo/demo_build_requirements.md` (the spec the pipeline must satisfy), then survey `demo/data/raw/` (the actual inputs). STATUS.md is operator-facing and not required for pipeline execution. `LESSONS_LEARNED.md` Session 3 and Session 4 entries explain why the hard rules below have the force they do.

**For the analytical demo design (post pipeline rebuild):** read this file, then `demo/demo_approach.md`, then `demo/EARNINGS-ANALYSIS-GUIDE.md` (will be updated after rebuild).

Whichever path you take, the hard rules in the "Process Discipline" section below are non-negotiable. They are not suggestions. They exist because they were violated, and the receipts are in `LESSONS_LEARNED.md`.

During brainstorming, when you want to discuss anything or have questions, please number them.

**CRITICAL: Never assume the contents of any file, document, deck, or material the user asks you to review. You must read it first using the appropriate tool before responding. If you cannot read it, say so explicitly. Do not summarize, paraphrase, or reason from a file you have not actually opened. This applies without exception — there is no context in which assuming file contents is acceptable.**

---

## The Opportunity

**Contact:** Jarvis Cromwell, CEO and Co-Founder, CT Digital Forum (jarvis@ctdigitalforum.com, 203-505-4646)

**Event:** Digital FutureFest '26, June 4, 2026, UConn Stamford, CT. All-day event, 40+ speakers. Workshop is a separate sign-up, up to 15 participants, boardroom style.

**Workshop title:** Everyone Is Wrong About AI, Including Me
**Subheader:** Navigating the Edge: A Hands-On Look at What AI Can and Can't Do

**Status:** Confirmed. Workshop is 1 of 3 offered in parallel over the lunch break.

**Room logistics confirmed:**
- U-shaped classroom, dedicated screen, good WiFi
- Can plug in MacBook Pro — buy adapter before event
- Up to 15 participants, sign-in process (count may go up or down)
- Workshops run in parallel — no cross-workshop straggler issue
- Effective working time: plan for 45 minutes. People arrive, grab box lunches, and settle — the formal 60-minute clock starts late in practice.

---

## Audience Profile

Financially sophisticated, senior, heterogeneous. Mix of investment bankers, board directors, investors, wealth managers, and innovators from the Tri-state area. Self-selected into the workshop — engagement is high by design. Heterogeneity is a design asset, not a constraint: the feed mechanism makes divergence of views visible and interesting.

---

## Directory Structure

```
earnings-demo/
  CLAUDE.md                        # This file: project context for new sessions
  STATUS.md                        # Current phase, task progress, open questions
  LESSONS_LEARNED.md               # Workarounds, design decisions, what failed
  data-audit-findings.md           # Audit of the data pipeline (2026-05-27). Read before any rebuild.

  workshop/                        # Workshop design and facilitation materials
    agenda.md                      # Full 60-minute agenda with timing rationale
    exercise_brief.md              # Participant-facing exercise brief
    facilitator_guide.md           # Facilitator one-pager (timing cues, failure modes)
    behind_the_veil.md             # Content outline for the opening presentation
    run_of_show.md                 # Full run of show for the session

  demo/                            # The AI-assisted earnings analysis demo
    demo_script.md                 # Presenter script for the demo block
    demo_approach.md               # Design decisions for the demo (live vs. pre-built)
    fallback/                      # Pre-recorded or scripted fallback options

  feed-app/                        # The live feed web application
    README.md                      # Feed app design spec and build plan
    app/                           # Application code (to be built)
```

---

## Workshop Design

### The Three Beats (adapted from branch-demo session_deck.pptx slide 4)

**Beat 1 — Think before you type (5 min, no laptops)**
What factors drive your investment view on this company? What would you want to know? Write it down. You will need it.

**Beat 2 — Work the problem with AI (15 min, laptops and phones)**
Lead with your framework. Share it with the AI, ask what's missing, ask where to get data, form an investment view. You will not finish everything. That is fine.

**Phone-only participants:** A meaningful share of participants will have only their phones. This is accommodated by pairing. At the start of Beat 2, ask laptop users to raise their hands and pair them with phone-only participants. The phone person can't drive the interface, so they articulate their thinking while the laptop person prompts. This produces better analytical dialogue than two laptops running in parallel — it is a design feature, not a workaround. The exercise brief must be mobile-readable and QR-accessible from day one.

**Pair + Post (5 min)**
Compare with your neighbor. Post your combined view to the feed anonymously via QR code. Structured prompt: Buy / Hold / Sell + one sentence biggest conviction + one sentence biggest uncertainty.

**Read the feed (1 min, silent)**
Everyone reads the aggregated themes. No discussion. Let the divergence land before the demo.

### Settling Poll (pre-session, during box lunch)

Three questions, displayed as people arrive and settle. Tap-to-answer on a phone — no typing required. Responses feed into the Behind the Veil discussion and Q3 is explicitly revisited in the debrief.

**Q1 — AI journey (diagnostic):**
"How would you describe your current use of AI in your professional work?"
- It's part of my daily workflow
- I use it occasionally when the right task comes up
- I've experimented but haven't found the right fit yet
- I'm mostly watching from the sidelines

**Q2 — Market signal (priors):**
"Recent market reactions to domain-specific AI launches — tools like Claude for Legal, AI for financial services — how do you read them?" *(Anchor to PANW earnings release June 2 as the live example in the room.)*
- The market is right, these are genuinely transformative
- Overreaction — we've seen this cycle before
- Underreaction — bigger than people think
- I don't follow these moves closely

**Q3 — Setup for the debrief:**
"Will AI be net positive for investment analysis specifically?"
- Yes, clearly
- Yes, but with significant caveats
- Too early to tell
- Skeptical

Q3 is shown again at the end of the debrief. Whether the room has shifted — or deliberately hasn't — is the closing moment.

### Full 60-Minute Agenda (plan for 45 effective minutes)

| Time | Block | Description |
|------|-------|-------------|
| 0:00 – 0:08 | Behind the Veil | Straight presentation. What's actually happening inside these tools. |
| 0:08 – 0:12 | Problem Setup | Here's the earnings call. Your task: form an investment view. Here's how the next 30 minutes run. |
| 0:12 – 0:17 | Beat 1 | Think before you type. No laptops. |
| 0:17 – 0:32 | Beat 2 | Work the problem with AI. |
| 0:32 – 0:37 | Pair + Post | Compare, post to feed anonymously via QR code. |
| 0:37 – 0:38 | Read the Feed | Silent. Let the divergence land. |
| 0:38 – 0:53 | Demo | Structured AI-assisted earnings analysis. Same call. Same question. |
| 0:53 – 1:00 | Debrief | Feed + demo together. What diverged? Where's the jagged edge? |

**Note:** The agenda above reflects the formal 60-minute design. Given box lunch settling, plan a compressed 45-minute version as the working default. The agenda needs a dedicated compression pass — this is an open task. Blocks most at risk: Behind the Veil (can go from 8 to 5 min), debrief (can compress but is where learning crystallizes — protect it). The demo should not go below 12 minutes.

---

## Learning Objectives

**Primary objective:**
Participants leave with a concrete practice for deploying a general-purpose AI tool on specific knowledge work tasks — starting with their own domain.

The core insight this workshop is built around: people treat AI like a search engine — general query in, hope something useful comes out. The skill they're missing is task translation: taking their specific professional judgment and briefing the tool against it. This is the biggest gap for sophisticated professionals, and it's what the earnings exercise makes visceral.

**Supporting objectives (means to the primary):**
1. Understand why AI outputs are bounded by input quality — and what "quality input" actually means for analytical work
2. Recognize the co-worker model: brief it, manage it, verify it — same as a capable junior analyst
3. Experience the difference between unstructured AI use and framework-led use on a real task, in real time

**The CTA (what they take home):**
"The next time you use AI on a real problem, notice whether you led with your framework or let AI set the agenda."

Delivered at the close of the debrief. Simple, behavioral, tied directly to what they just experienced.

---

## The 4D Framework (Behind the Veil)

The Behind the Veil presentation is built on Anthropic's 4D AI Fluency Framework — Description, Discernment, Delegation, Diligence — extended with Data Literacy for the enterprise context. This maps to 5 infrastructure components:

| Component | What's Actually Happening | Practitioner Competency |
|-----------|--------------------------|------------------------|
| The Interface | Surface where prompts and outputs exchange. Output quality is bounded by input quality. | Description |
| The Model (LLM) | Pattern completion, not deduction. Real capabilities, real limitations. | Discernment |
| Knowledge & Data Access | The model amplifies whatever you feed it. Your data quality is your strategy quality. | Data Literacy |
| Agents | Agents take actions — send the email, modify the record, move the money. Risk is in the action, not the answer. | Delegation |
| Guardrails | Controls that turn capability into accountable capability. Without them, capability is exposure. | Diligence |

Reference: branch-demo `phase6/session_deck.pptx` slide 2 (Sandeep's adapted version of the Anthropic framework). Branch-demo folder is not mounted in this session — ask user to share the slide if needed.

---

### The Earnings Call

**Primary:** Palo Alto Networks, earnings announcement June 2, 2026 (two days before the event). Strong name recognition, relevant to AI governance and cybersecurity tracks on the forum agenda.

**Backup:** Prior week announcements TBD. Having a backup is mandatory — learned from branch-demo.

### The Exercise Task

Participants form an investment view: Buy / Hold / Sell, with their biggest conviction and biggest uncertainty. Specific enough to aggregate meaningfully via the feed, open enough that heterogeneous backgrounds produce genuinely different outputs.

---

## The Feed Mechanism

A web app (in `feed-app/`) where participants post their paired investment view anonymously via a QR code link. An LLM call aggregates posts and surfaces themes in near real time. The room watches their own collective thinking get synthesized before the demo begins.

**Key design requirements:**
- Anonymous posting — no login, no name attached
- Structured prompt (Buy/Hold/Sell + conviction + uncertainty) to enable meaningful aggregation
- Phone-native: Buy/Hold/Sell is a tap, not typed. Conviction and uncertainty are short text fields with a hard character limit (one sentence, enforced). Minimize typing friction — participants are eating lunch.
- Near real-time theme display as posts arrive
- Visible during the demo so participants can see their views interrogated live
- QR code displayed in the room for easy access
- The settling poll (3 questions) may live in the same app or as a separate lightweight form — decision pending

**Build status:** Not started. This is a core deliverable.

---

## The Demo Block

The 15-minute demo (0:38–0:53) shows what a structured AI-assisted approach produces on the same earnings call participants just worked. Key design decisions still open:

- Live in Cowork vs. pre-built analytical workflow vs. hybrid
- Foundation: Anthropic financial skills around earnings review — show the off-the-shelf baseline, then show what context and structure add
- A fallback option is mandatory (pre-recorded or scripted) — branch-demo learned this the hard way
- The feed output should be visible during the demo

**This is the most critical design decision for the project. Resolve before building anything else.**

---

## Relationship to Branch-Demo

| Branch-Demo Artifact | Relevance to This Project |
|---------------------|--------------------------|
| `phase6/session_deck.pptx` slide 2 | Behind the Veil content — 5-component practitioner fluency framework is directly reusable |
| `phase6/session_deck.pptx` slide 4 | Three Beats structure — adapted directly |
| `phase6/demo_script.md` | Acts 1-3 structure informs demo block design |
| `phase6/dry_run_lessons_learned.md` | Session design lessons — read before finalizing facilitator guide |
| `phase6/facilitator_guide.md` | Reference for facilitator one-pager format |
| `phase6/exercise_brief.md` | Reference for participant brief format |

---

## Process Discipline — How to Work on This Project

The following rules exist because fabricated analytical content was built and presented as real output in session 3. They are not suggestions.

### The only permitted sequence

**Design → Data → Script → Test → Learn → Build**

No stage can be skipped. No final-form output gets built before the preceding stages are complete and approved.

- **Design:** Agree on what the output should be and how it will be produced before writing any code or content. Get explicit approval before moving forward.
- **Data:** Pull and verify data. Document sources. Do not proceed until data is confirmed accurate.
- **Script:** Write the prompts, steps, and workflow. Do not run it yet. Share for review.
- **Test:** Run the script on a test case — not the demo case. Show the actual output. Get it reviewed.
- **Learn:** What worked, what didn't, what needs to change. Update the script.
- **Build:** Only now does the demo artifact get populated — with real output from a real run.

### Hard rules

1. **Never write analytical conclusions into a template or HTML file.** Verdicts, theses, bull/bear cases, investment views, horizon reads — these can only come from actually running the process. They cannot be pre-written and embedded.

2. **Never label content as the output of a tool, plugin, or AI session that was not actually run.** If the plugin was not installed and executed, the output cannot be attributed to it. If a Cowork session was not run, the output cannot be attributed to one.

3. **Never make cosmetic fixes to attribution without fixing the underlying content.** If content is fabricated, the fix is to remove it — not relabel it. Changing a header is not a fix.

4. **Get approval before each stage transition.** Before moving from one stage to the next, state explicitly: "I am about to move from [stage] to [stage]. Here is what I have. Do you approve?" Wait for confirmation.

5. **If a step cannot be completed honestly with available data or tools, say so.** Do not fill the gap with invented content. The honest answer is always: "This cannot be done yet because [reason]. Here is what we need."

6. **Tab 2 and Tab 3 of earnings_baseline.html are placeholders until real output exists.** They get populated only after the earnings reviewer process has been designed, tested on Q1 FY26, validated, and re-run on Q2 FY26 (or Q3 FY26 after June 2 print). No exceptions.

---

## Session Discipline

At the end of each working session, update `STATUS.md` with current progress and any new open questions. If new technical workarounds or design decisions are discovered, add them to `LESSONS_LEARNED.md`. A scheduled daily task runs to prompt these updates — do not skip them.

**Dry-run sessions:** When preparing for or debriefing a workshop dry run, read `LESSONS_LEARNED.md` first and update it after — capture observations, promote patterns to findings, log decisions made.

---

## Current State

Workshop slot confirmed by Jarvis Cromwell (May 24, 2026). Workshop design is largely settled: learning objectives, settling poll, co-worker model framing, phone/pairing strategy, Three Beats structure, two-move demo structure (live in Cowork), Microsoft Forms plus GitHub Pages plus Cowork infrastructure (no custom feed app), and the participant parity rule for tooling. Outstanding workshop items are the compressed 45-minute agenda pass, the participant exercise brief, the facilitator guide, the Behind the Veil outline, the run of show, and identifying a backup earnings call.

Phase 2 (demo build) is **complete and workshop-ready as of 2026-06-03**. The data pipeline rebuild landed in late May; the Q3 FY26 pipeline run (gather → rebuild_db → analysis scripts → generate_baseline) executed cleanly on June 3 after the PANW Q3 FY26 print (June 2). All three dashboard tabs render from current Q3 FY26 data: Tab 1 (baseline data + sentiment captured via Playwright), Tab 2 ("Earnings Reviewer" — sell-side skill applied with Rating Logic and Margin Analysis sections showing the skill's reasoning chain; rating is Maintain Outperform with PT $174), Tab 3 ("Decision Layer" — buy-side judgment overlay with 5-dimension framework and live chat via Claude + Tavily). The presenter script `demo/earnings_analysis_script.md` is refreshed to Q3 FY26 actuals. Session 10 corrections applied: faithful Step 11 skill application (primary trigger + three moderating factors), substantive data-derived Key Takeaways, dynamic sign-based coloring in cover stats. Server smoke tests pass end-to-end. Remaining for workshop day: real QR codes dropped into deck slides 4/7/8, fallback materials (mandatory per hard rules), and the workshop facilitation deliverables noted above.

See `STATUS.md` for task-level progress, open questions, and blockers. See `LESSONS_LEARNED.md` for the reasoning behind the hard rules and the Session 3 and Session 4 narratives.
