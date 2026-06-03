# Session Deck Outline

*Last updated: 2026-06-02. Status: build complete, mid-flight pivots locked. Sandeep is making live edits to session_deck.pptx; this doc is the design source of truth and gets reconciled after his pass.*

---

## Scope decisions (locked)

1. Tight skeleton, 10 slides (settling poll, title, then the 8-slide arc).
2. Targeted at 45-minute compressed working version. Full 60-minute agenda still in CLAUDE.md as reference.
3. Built on the Aileron Group branded template (`ag-brand-guidelines` skill) with two slides adapted from branch-demo `phase6/session_deck.pptx`: slide 2 (5-component framework) and slide 4 (Three Beats).
4. Behind the Veil draws content directly from branch-demo slide 2. Speaker notes on that slide also feed the facilitator guide later.
5. **Polling platform: Microsoft Forms (not Mentimeter).** Forms is bundled with M365, supports anonymous responses, has presentation-mode word cloud and live bar charts, embeds natively in PowerPoint. Two forms total (settling poll + Beat 3 post). Q3 re-poll cut.

## Design principles for this deck

1. The deck owns five facilitation moments: arrival, opening, problem setup, working-block standing references, debrief. It does not narrate the demo. The demo runs live in Cowork plus pre-staged HTML windows.
2. QR codes live in the deck to minimize participant-side switching. Three unique codes: Microsoft Forms settling poll, PANW one-pager (GitHub Pages), Microsoft Forms Beat 3 posting board.
3. Room-screen switching is minimized. Surface switches happen at two moments: Q2 reveal between settling and BTV opening, and read-the-feed after Pair + Post. All triggered manually by the facilitator.
4. Standing slides (Beats 1, 2, Pair + Post) must be readable from 20 feet and self-explanatory. The facilitator will not be repeating instructions while 15 people work.
5. Text-only slides are allowed where they make sense. The Beat 1 standing slide and Slide 10 take-home both lean text-dominant by design. Default is visual + text; minimalism is a deliberate choice on specific slides.
6. **PANW one-pager: facts only, no conclusions.** The participant-facing artifact contains earnings figures, transcript quotes, peer snapshot, stock reaction. It does not contain the sell-side rating, the buy-side recommendation, price targets, or any framework-derived thesis. Including conclusions hands participants the answer key and collapses the Beat 2 work into reading. Pedagogical move: facts up, framework from the participant, conclusion from the participant, then watch the structured demo arrive at its own recommendation.

## Surface-switching map

This map is the implicit operating model for the facilitator. The bottom strip on Slide 5 (Three Beats) shows the participant-visible portion (Beats 1, 2, Pair + Post, Read, Demo, Debrief).

| Phase | Time | Surface | Trigger |
|---|---|---|---|
| Arrival + settling poll (static) | ~5 min | Deck (Slide 1) | Up as room enters |
| Q2 reveal (word cloud + detailed responses) | ~30 sec | **MS Forms present mode** | Manual switch by facilitator |
| Title + opening provocation (verbal) | ~1 min | Deck (Slide 2) | Manual switch back |
| 5-component framework | 4 to 5 min | Deck (Slide 3) | Advance |
| Problem Setup | 3 min | Deck (Slide 4) | Advance |
| How the 30 min run | 1 min | Deck (Slide 5) | Advance |
| Beat 1 | 4 min | Deck (Slide 6, standing) | Advance |
| Beat 2 | 12 min | Deck (Slide 7, standing) | Advance |
| Pair + Post | 4 min | Deck (Slide 8, standing) | Advance |
| Read the feed | 1 min | **MS Forms present mode** | Manual switch |
| Demo | 12 min | **Cowork + HTML windows** | Cmd-Tab |
| Debrief | 3 min | Deck (Slide 9) | Advance; show-of-hands close |
| Take-home | 30 sec | Deck (Slide 10) | Advance |

---

## Slide-by-slide

### Slide 1. Settling poll (arrival)

- **Role:** Anchors the room on arrival. Three diagnostic questions visible on the deck slide; participants scan the QR and complete the form in Microsoft Forms on their phone. After ~5 minutes, facilitator switches to Forms present mode to reveal Q2 (word cloud + detailed responses). Q1 and Q3 are not revealed to the room (diagnostic for facilitator and setup for the close).
- **Time on screen:** ~5 minutes static. Q2 reveal is a ~30-second beat before transitioning to Slide 2.
- **Content:**
  - Header: "While you settle in"
  - Three questions stacked, large type (mirroring the form so participants can read while waiting to scan):
    1. Q1 (MCQ, required): "How would you describe your current use of AI in your professional work?" Five options: Not using AI today / Experimenting occasionally / Regular use in parts of my workflow / AI is central to my role or team / Prefer not to say.
    2. Q2 (open text, optional, 1-2 sentences): "How do you interpret recent market reactions to domain-specific AI launches (e.g., legal, financial services)?"
    3. Q3 (Likert, required, 5-point scale): "Overall, do you believe AI will be net positive or net negative for investment analysis?" Strongly net negative / Somewhat net negative / Neutral or unclear / Somewhat net positive / Strongly net positive.
  - Microsoft Forms QR code, prominent.
  - Small instruction line: "Tap. No name required."
- **Form artifact:** "AI: Where Are You Starting From?" — built by Sandeep, anonymous, ~90 sec to complete.
- **Reveal handling:** Only Q2 is revealed to the room. Word cloud + a few detailed responses, surfaced via Forms present mode in the ~30-second beat between settling and the title slide. Q1 and Q3 are diagnostic only; Q3 informs the verbal show-of-hands at debrief.
- **Source:** Questions are Sandeep's refined version of the original CLAUDE.md "Settling Poll" set. Q1 expanded to 5 options (added "AI is central" and "Prefer not to say"). Q2 changed from MCQ to open text (richer data, sets up heterogeneity theme). Q3 changed from 4-bucket MCQ to 5-point Likert (better signal for the closing reflection).
- **Open items:** None.

### Slide 2. Title / cold open

- **Role:** Marks the formal start of the workshop. Carries the opening provocation verbally; the title itself does the work on screen.
- **Time on screen:** ~1 minute.
- **Content:**
  - Title: "Everyone Is Wrong About AI, Including Me"
  - Subhead: "Navigating the Edge: A Hands-On Look at What AI Can and Can't Do"
  - Workshop date, location (Digital FutureFest '26, UConn Stamford)
  - Facilitator names (Sandeep + Gil) and Aileron lockup
- **Facilitator opening line (verbal, no slide content):** Lands the provocation as a spoken beat. Working draft: "Faster than any tech in history. Used by everyone. Understood by almost no one. That is why everyone is wrong about AI, including me." Finalized in the facilitator guide.
- **Source:** Fresh on AG template. Layout adapted from branch-demo slide 1.
- **Open items:** None.

### Slide 3. The 5 components (Behind the Veil core)

- **Role:** Centerpiece of the Behind the Veil opening. Shows the practitioner what is actually happening inside these tools.
- **Time on screen:** 4 to 5 minutes.
- **Content:** Five-row table, three columns per row.
  - Column 1: numbered component (01 to 05) plus a one-line subtitle of what it physically is
  - Column 2: "What's actually happening"
  - Column 3: "What practitioners need" plus competency tag
  - Footer: 4D Fluency reference line
  - Components and competencies:
    1. The Interface, DESCRIPTION
    2. The Model (LLM), DISCERNMENT
    3. Knowledge & Data Access, DATA LITERACY
    4. Agents, DELEGATION
    5. Guardrails, DILIGENCE
- **Source:** Direct lift from branch-demo slide 2. Content unchanged, re-skinned to AG palette and typography. Speaker notes on the source slide are excellent and will flow into the facilitator guide.
- **Facilitator transition cue (verbal, no slide):** On the way from this slide to Slide 4, the facilitator delivers the "brief, manage, verify" co-worker model line. The cut co-worker slide (from prior outline) lives here as spoken framing, not as a deck slide.
- **Open items:** None.

### Slide 4. The call and your question (Problem Setup)

- **Role:** Hands the room the task. Sets the question they will answer.
- **Time on screen:** 3 minutes.
- **Content (three zones):**
  - **Zone A (top, fixed):** the framing one-liner (locked) and a one-line "why PANW" hook.
    - **One-liner:** "Palo Alto Networks reported Q3 FY26 on June 2. Your task: form an investment view."
    - **Why PANW line:** "AI governance and cybersecurity tracks on the forum agenda. The market just told you what it thinks. The question is what you think."
  - **Zone B (middle):** earnings highlights box with five slots, populated from Q3 FY26 figures after the June 3 pipeline refresh.
    1. Revenue: $ + YoY
    2. NGS ARR: $ + YoY
    3. Non-GAAP EPS: $ vs consensus
    4. Stock reaction (after-hours / next-day gap)
    5. One qualitative callout (guidance change, segment color, AI mention)
  - **Zone C (bottom):** the task statement and QR
    - "Form an investment view. Buy / Hold / Sell + one sentence biggest conviction + one sentence biggest uncertainty."
    - QR to PANW one-pager (GitHub Pages)
- **Source:** Highlights pulled from `demo/data/analysis/panw_q3fy26_earnings_analysis.json` after the June 3 refresh. Sandeep updates the deck values inline once the data lands.
- **Open items:** None.

### Slide 5. How the next 30 minutes run (Three Beats)

- **Role:** Agenda anchor. The room sees the whole arc before they start working.
- **Time on screen:** 1 minute, then transition into Slide 6.
- **Content:** Three-column timeline, same structure as branch-demo slide 4. All three columns rewritten.
  - **Beat 1.** Think before you type. 4 min. No laptops. Talking points: starter questions from Slide 6.
  - **Beat 2.** Work the problem with AI. 12 min. Laptops or phones, pair up. Talking points: lead with your framework. Sequence preview lives on Slide 7.
  - **Pair + Post.** 4 min. Compare with a neighbor. Post one combined view.
  - **Footer line (unchanged from branch-demo):** "There is no right answer. The point is the quality of your reasoning."
  - **Surface-switching strip across the bottom:** small visual showing the participant-visible flow (Beat 1, Beat 2, Pair + Post, Read, Demo, Debrief). The strip carries the Mentimeter Beat 3 posting QR anchored to the Pair + Post column so participants can pre-scan during the agenda preview.
- **Source:** Adapted from branch-demo slide 4. Visual structure carried; content rewritten end to end.
- **Open items:** None.

### Slide 6. Beat 1 standing slide

- **Role:** Stays up for the full 4 minutes of Beat 1. The slide IS the prompt. Text-dominant by design (per principle 5).
- **Time on screen:** 4 minutes.
- **Content:**
  - Two starter questions, large type, no decoration:
    - "What factors drive your investment view on this company?"
    - "What would you want to know?"
  - One quiet support line below: "Write it down. You will need it."
  - "No laptops" icon prominent.
- **Source:** Fresh. Adapts the branch-demo Beat 1 pattern (talk-it-out questions, write it down line) to a single-investor-view framing rather than a group framework framing.
- **Open items:** None.

### Slide 7. Beat 2 standing slide (highest leverage, will A/B in dry run)

- **Role:** Stays up for the full 12 minutes of Beat 2. Acts simultaneously as pairing instructions and prompt scaffold. The sequence is the workshop's portable takeaway.
- **Time on screen:** 12 minutes.
- **Content (four elements, layout TBD):**
  - **Pairing rule.** "Laptop users raise hands. Pair with phone-only. Phone person articulates. Laptop person prompts."
  - **Beat 2 sequence (locked).** Five numbered steps:
    1. Share your framework. Ask what is missing.
    2. Decide what data your framework needs. Pull what you can from the one-pager. Ask AI for what is missing.
    3. Pick your biggest uncertainty. Ask what the call said about it.
    4. Ask it to argue the strongest case against your view.
    5. Land it. Buy / Hold / Sell with one-sentence conviction and uncertainty.
  - **Reassurance line.** "You will not finish all five. That is fine. The five-step structure is what you take home, pick it up at any step and your AI session improves."
  - **Form a view (deliverable reminder).** "Buy / Hold / Sell + biggest conviction + biggest uncertainty."
  - **QR to PANW one-pager.** GitHub Pages. The data source for step 2.
- **Pedagogical logic (one line per step, for facilitator guide):**
  1. Brief. The most-skipped move, compounds everything that follows.
  2. Pull facts with constraints. Pattern: decide what you need, source it, gap-fill with AI.
  3. Drill on a specific uncertainty. Focused probing transfers to any analytical task.
  4. Red-team. The bias check that prevents AI from becoming a confirmation engine.
  5. Synthesize. AI helps you sharpen the decision; the decision is yours.
- **Source:** Fresh. Pattern and cadence adapted from branch-demo slide 4 Beat 2 column.
- **Layout (locked: Option C, Three Zone):**
  - Top banner (~15% height): Pairing rule.
  - Middle zone (~65% height): Five numbered steps. Step 5 absorbs the deliverable so it does not need a separate panel.
  - Bottom strip (~20% height): Form-a-view restatement and reassurance caption on the left; QR to PANW one-pager on the right.
- **Open items:** None.

### Slide 8. Pair + Post standing slide

- **Role:** Switches the room from individual work to pair conversation, then to posting.
- **Time on screen:** 4 minutes.
- **Content:**
  - Step 1: "Compare with your neighbor. Land on one combined view."
  - Step 2: Structured post format. Three fields visible:
    - Buy / Hold / Sell (tap)
    - One sentence biggest conviction (short text)
    - One sentence biggest uncertainty (short text)
  - QR to Microsoft Forms Beat 3 posting board (large, center-right).
  - Small reminder under QR: "Anonymous. No name. No login."
- **Form artifact:** "Your view on Palo Alto Networks" — built by Sandeep. Anonymous. Four required questions.
  - Q1 (MCQ): "What is your investment recommendation for Palo Alto Networks (PANW)?" Three options: Buy / Hold / Sell.
  - Q2 (5-star rating): "How confident are you in your recommendation?" 1 = Very uncertain, 5 = Very confident.
  - Q3 (open text): "In one sentence, what is the primary reason for your recommendation?" Subtitle anchors to growth outlook, margins, valuation, AI narrative.
  - Q4 (open text): "In one sentence, what is the biggest risk or uncertainty that could make your recommendation wrong?" Subtitle anchors to execution risk, macro, competition, AI expectations.
  - Intro line on form: "Your responses will be shown live after a pause to avoid influencing others."
- **Reveal handling:** Read-the-feed beat shows all four results in Forms present mode. Bar chart for B/H/S, distribution chart for confidence, word cloud plus toggleable detailed responses for primary reason, same for biggest risk. ~15 seconds per visualization in the 60-second window; tight but doable. Facilitator paces by reading aloud a couple of contrasting responses from the open-text views.
- **Source:** Fresh. Q3 and Q4 reframed from the original "biggest conviction" and "biggest uncertainty" framings; the analyst-language sharpening (primary reason, biggest risk) raises rigor. Q2 (confidence) added as a fourth field for quantitative dimension.
- **Open items:** Confirm one submission per pair (verbal instruction; Forms cannot enforce).

### (No deck slide) Read the feed

Mentimeter on screen. 1 minute, silent. Facilitator switches surfaces. Not a deck slide.

### (No deck slide) Demo

12 minutes live. Cowork plus pre-staged HTML windows. Facilitator Cmd-Tabs between windows. Deck dark. Not a deck slide.

### Slide 9. Debrief

- **Role:** Closes the loop. Surfaces divergence between the feed view and the structured demo, names the jagged edge, and asks the room directly whether their view shifted.
- **Time on screen:** 3 to 4 minutes.
- **Content (three blocks):**
  - **Block 1: Feed vs demo.** "What diverged? Where did the room agree with the AI-assisted view? Where did it disagree?" Skeleton labels only; the actual divergence is named in real time by the facilitator. (Build as skeleton, finalize after dry run.)
  - **Block 2: The jagged edge.** "Where did AI add real value? Where was human judgment load-bearing?" Same skeleton-then-fill treatment.
  - **Block 3: Did your view shift?** Verbal show-of-hands close, no re-poll. Facilitator asks: "How many of you feel your view on AI in investment analysis shifted in the last 45 minutes?" Picks up two or three voices from the room to name what moved them.
- **Source:** Fresh. Skeleton committed now; talking points finalize after dry run.
- **Open items:** None.

### Slide 10. Take-home + contact

- **Role:** The behavioral CTA from CLAUDE.md, then contact lockup.
- **Time on screen:** 30 seconds, plus stays up during open Q&A or room exit.
- **Content:**
  - The CTA, large type, single line: "Next time you use AI on a real problem, notice whether you led with your framework or let AI set the agenda."
  - Below: two-up contact block adapted from branch-demo slide 10. Sandeep + Gil. Phone, emails, address, lockup.
  - Optional: small icon row pointing to the GitHub Pages site for materials.
- **Source:** CTA verbatim from CLAUDE.md. Contact format from branch-demo slide 10.
- **Open items:** None.

---

## What does NOT carry from branch-demo

Branch-demo slides 5 through 9 (the "What We Built / How We Built This / What the Model Recommends / What If We Disagree" sequence) are workflow narration. They retold the build story. We do not retell our build story. Our demo is live and uses pre-staged windows. No analog needed.

## What was cut from this outline (and why)

1. **Co-worker model slide** from prior draft. Cut because Slide 5 (Three Beats) carries the task-translation move in action, and the "brief, manage, verify" line lands cleaner as a verbal facilitator transition than as its own slide. CLAUDE.md still owns the concept; the facilitator guide will own the verbal cue.

2. **Standalone provocation slide.** Cut. The title slide carries the provocation through facilitator delivery rather than a separate visual beat. Working spoken line preserved in Slide 2 notes.

3. **"No text-only slides" design principle** (prior principle 5). Relaxed. Some slides earn their force by stripping decoration: Beat 1 standing slide is the most obvious example. Default is visual + text; minimalism is a deliberate choice on specific slides.

4. **Harvard adoption chart.** Cut as a planned slide element. The audience already knows the speed-of-adoption stat. Facilitator carries the provocation verbally. Possible add-back to a Slide 2 footer if dry run signals need.

5. **Mentimeter as the polling platform.** Replaced with Microsoft Forms. Forms is bundled with M365, supports anonymous responses, has word cloud + bar chart visualizations in present mode, embeds natively in PowerPoint, and gives a clean Excel export. The structured submission for Beat 3 (B/H/S + conviction + uncertainty in one form) is also easier in Forms than in Menti's multi-slide pattern.

6. **Q1 and Q3 settling poll reveal to the room.** Cut. Q1 and Q3 are diagnostic for the facilitator only. Only Q2 (the open-text question with the richest heterogeneity signal) is revealed to the room, in a ~30-second beat between settling and the title slide.

7. **Q3 re-poll at debrief.** Cut. In a 45-minute compressed agenda, a 60-second re-poll-and-reveal moment is real time. The risk of a flat distribution undercutting the workshop's central provocation is asymmetric. Replaced with a verbal show-of-hands close ("Did your view shift, and what moved you?") that gets the qualitative signal in 20 seconds with the room watching each other.

## Open items rollup

1. Slide 4 Zone A and Zone B Q3 figure swap. Q3 actuals from `panw_q3fy26_earnings_analysis.json`: Revenue $3.00B (+31.1% YoY, +2.1% beat), NGS ARR $8.13B (+60% reported / +28% organic), Non-GAAP EPS $0.85 vs $0.80 consensus (+6.2%), stock reaction -4.4% next-day, suggested twist callout on M&A-boosted ARR (CyberArk + Chronosphere) and the organic-vs-reported gap. Workshop is June 4.
2. Small reconciliation items in deck language: Slide 5 surface strip "Mentimeter" → "MS Forms" (one-word fix), and the question of whether Slides 5/7/8 should mirror Form 2's four-field structure (B/H/S + confidence + primary reason + biggest risk) or stay generic.
3. Slide 2 callout language: "We will reveal where the room landed" could soften to "We'll surface what the room is thinking" since only Q2 is revealed.
4. Slide 9 (Debrief) content blocks 1 and 2 are skeletons; finalize after dry run.
5. Harvard adoption chart possible add-back to Slide 2 footer if dry run signals need.
6. Backup earnings call identified (mandatory per CLAUDE.md, listed in STATUS.md Open Question 3).
7. Fallback option for the demo block (pre-recorded or scripted, mandatory per CLAUDE.md).

## Completed since last update

- Q3 FY26 pipeline refresh (June 3). `panw_q3fy26_earnings_analysis.json` and `panw_q3fy26_buyside_analysis.json` generated. `earnings_baseline.html` refreshed.
- PANW one-pager built in Claude Code: `demo/generate_one_pager.py` → `docs/index.html`, deployed at https://sandeepagi.github.io/earnings-demo/. 12 sections, mobile-first, tap-to-copy per section plus master Copy-everything button, facts only (no rating, no price target, no bull-bear framing).
- Real QR codes inserted into all four deck placements: Slide 2 (settling poll), Slide 4 (one-pager), Slide 7 (one-pager), Slide 8 (Beat 3 post).
- Slide 9 Block 3 renamed "Use of AI revisited" with verbal show-of-hands scaffold (no Q3 re-poll).

## Next steps

1. Slide 4 Q3 figure swap (workshop is June 4).
2. Small reconciliation items in deck language.
3. Backup earnings call decision.
4. Fallback for the demo block.
5. Dry run pass.
