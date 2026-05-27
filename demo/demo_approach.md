# Demo Design: Approach and Decisions

*Created: 2026-05-25. This document captures design decisions for the demo block.
It feeds into `demo_script.md` once the prompt sequence is finalized.*

---

## What the Demo Is For

The demo block (0:38–0:53, ~12–15 effective minutes) has one job: make visceral the
difference between unstructured AI use and framework-led AI use on the same earnings
call participants just worked. It is not a product showcase. It is not a tutorial. It
is evidence — delivered live, on a live transcript, against views the room just formed.

The demo answers Q3 from the settling poll ("Will AI be net positive for investment
analysis specifically?") — not by asserting yes, but by showing the room something
concrete and letting them judge.

---

## Design Constraints

- **Time:** 12–15 effective minutes. Cannot compress below 12. Do not over-plan for 15.
- **Transcript timing:** PANW reports June 2. Transcript available ~48 hours before the
  event. Demo must be designed to work with a real, live transcript we will not have
  seen in advance.
- **Audience:** Buy-side in orientation — investors, board directors, wealth managers.
  Not sell-side analysts. They are forming views, not publishing notes.
- **Live vs. pre-built:** **Decision: live in Cowork.** This is the most credible
  format for this audience — they see it working in real time, not a rehearsed replay.
  Fallback (pre-recorded) is mandatory and must be built before June 4.
- **Feed visibility:** The feed output (room's aggregated views) should remain visible
  during the demo so participants can see their own positions being tested.
- **Participant parity:** The demo uses only tools participants could theoretically use
  — general-purpose Claude in Cowork, not specialized connectors they don't have access
  to. The lesson is about *how* you use it, not *what* you have access to.

---

## The Analytical Framework

### Baseline: Sell-Side Skill (Earnings Reviewer Agent)

Anthropic's financial-services-plugins repo
(`github.com/sandeepAGI/financial-services-plugins`) contains an Earnings Reviewer
agent with an `earnings-analysis` skill. Its analytical core covers:

| Step | What it does |
|------|-------------|
| Beat/Miss (Step 5) | Revenue, GM, EBITDA, EPS vs. consensus. Quantify and explain. |
| Segment/Geo (Step 6) | Breakdown by segment, geography, channel. What outperformed? |
| Margin Analysis (Step 7) | Gross → operating → net. Driver decomposition: pricing, mix, costs, leverage. |
| Guidance (Step 8) | Raised/lowered/maintained vs. prior and vs. Street. Credibility read. |
| Model Update (Step 9) | Old vs. new estimates. Current FY + next FY. |
| Valuation/PT (Step 10) | DCF recalc, comps multiples, new price target. |
| Rating (Step 11) | Maintain/upgrade/downgrade decision with explicit rationale. |

This is the **off-the-shelf baseline** — what you get if you deploy the skill without
a buy-side framework. Steps 9–11 are sell-side specific (coverage model, rating,
published note) and are not central to the demo. Steps 5–8 are the analytical core
where judgment lives.

### The Buy-Side Additions (Sandeep's Framework)

The sell-side framework is consensus-relative, 12-month horizon by convention, rating
output. The workshop audience needs a buy-side lens: alpha-seeking, horizon-explicit,
relative-return focused. Four additions:

**1. Investment Horizon (declared upfront)**

Must be stated before any analysis begins — it governs which signals matter.
- Short (<3 months): guidance vs. consensus, gap fill, options positioning
- Medium (6–18 months): margin expansion trajectory, RPO/backlog visibility, re-rating
- Long (2–5 years): moat durability, TAM capture, platform dominance

*Demo treatment:* Do not pre-pick a horizon. Show the divergence — run the same
prompt twice with different declared horizons. The delta IS the lesson.

**2. Alpha Edge**

Not "did they beat consensus" — that's known information. The question is: what is the
market mispricing? What information in this print is being over- or under-weighted in
the reaction?

For PANW specifically: is platformization compounding faster than the multiple implies?
What did management signal in the Q&A that analysts glossed over?

*AI role:* Can surface what management emphasized vs. downplayed, flag analyst Q&A
themes, extract forward-looking language. Cannot know what the market has already
priced in — that requires the analyst's prior.

**3. Peer Context**

Not just PANW in absolute terms — relative to the competitive set. For PANW: CRWD,
FTNT, ZS. Who is winning the platform consolidation trade? Customer behavior (churn
signals, land-and-expand velocity) as competitive signal.

For a market leader, the question is whether the moat is widening or narrowing — which
shows up in customer metrics and billings before it shows up in multiples.

*AI role:* Can compare management language across peer transcripts if fed them. Cannot
access live peer financials without a data connector. Pre-pulling peer context (most
recent quarters for CRWD, FTNT, ZS) before June 4 resolves this.

**4. Sentiment and Positioning**

Not an informational edge — a positioning edge. Short interest delta, options skew,
put/call ratio, insider transactions (Form 4 filings) tell you who is set up how.
Asymmetric reactions to the same print often come from positioning, not information.

Key distinction worth making explicit in the demo: this is about *positioning*, not
information. It's compatible with semi-strong EMH — the market prices known information
efficiently, but positioning creates asymmetric reaction profiles.

*AI role:* Can synthesize Form 4 filings, parse options commentary, summarize short
interest trends if fed the data. Cannot access live market microstructure without a
connector. **Pre-stage this data before June 4** (see below).

---

## Two-Move Demo Structure

The demo does not re-demonstrate unstructured AI use. The room just spent 15 minutes doing
that in the exercise. Their Beat 2 work is the baseline. The Mentimeter feed synthesis — the
room's collective output — sits on the screen as the left side of the comparison throughout
the demo. There is no Act 1.

The demo is two moves: framework-led analysis, then the sentiment layer.

---

### Move 1 — Framework-Led Analysis (~10 minutes)

**What we show:** The same transcript the room just worked, but led by a buy-side framework.
Horizon declared upfront. Four dimensions applied: alpha edge, guidance credibility, peer
context, horizon-conditional read.

**The contrast:** The feed stays visible. Participants compare what they produced against what
the framed analysis produces. The facilitator names the gap: "Notice what changed — and notice
what you had to bring for it to change."

**Prompt sequence (to be scripted in demo_script.md):**

1. **Declare the frame.** Investment horizon (medium-term, 6–18 months), objective (alpha vs.
   market, not vs. consensus), role (buy-side, forming a view — not publishing a note).

2. **Beat/miss through the thesis lens.** Not generic revenue and EPS — platformization
   velocity, Next-Gen Security ARR trajectory, billings as the forward indicator.

3. **Guidance credibility read.** Is management sandbagging or stretching? What language did
   they use that the Street may have taken at face value?

4. **Alpha question.** Given the stock's reaction to the print, what is the market getting
   right? What might it be getting wrong?

5. **Horizon divergence.** *"Now show me what changes if this is a 90-day trade vs. an
   18-month position."* Run live. Let the room watch the output shift.

**The closing beat of Move 1:** Point to the feed. "Look at your conviction statement. Look
at what this produced. Where do they overlap? Where do they diverge? It didn't do this
without the frame. You had to bring the frame."

**Time:** ~10 minutes.

---

### Move 2 — Sentiment Layer (~3 minutes)

**What we show:** Pre-staged positioning data (options skew, short interest delta, Form 4
filings) fed in alongside the transcript analysis. Shows how far the analysis extends when
you bring context the transcript cannot provide.

**The prompt:** *"Given this analysis of the transcript, here is the positioning context
around the print: [paste pre-staged data]. How does this change the risk/reward read?"*

**What we get:** The AI synthesizes the transcript thesis with the positioning read.
Asymmetric setups surface naturally: heavily shorted stock plus positive guidance surprise;
insider buying ahead of the print.

**The closing beat of Move 2:** "The transcript is public. The earnings model is public.
The edge, if there is one, is in what you bring that others don't — your framework, your
horizon, your read of positioning. The AI didn't create the edge. It amplified the one
you brought."

**Time:** ~3 minutes.

---

## Data to Pre-Stage Before June 4

All of this must be ready before the event. Do not rely on live access during the demo.

| Data | Source | Format |
|------|--------|--------|
| PANW Q3 FY26 earnings transcript | Seeking Alpha / company IR | Plain text, pasted in |
| PANW Form 4 filings (4–6 weeks pre/post print) | SEC EDGAR | Summary table |
| PANW short interest and delta | FINRA / data provider | 2–3 line summary |
| PANW options skew / put-call ratio around print | CBOE / provider | 2–3 line summary |
| CRWD, FTNT, ZS — most recent quarter summary | Public transcripts | 3–4 sentence peer read per company |

Pre-staging means: pulled, formatted, ready to paste. Not links. Not PDFs. Text blocks
that can be dropped directly into a Cowork prompt without live browsing.

---

## The Three Beats (Earnings-Adapted)

*The Three Beats structure carries over from branch-demo and is adapted here for the
earnings context. Full timing lives in `workshop/agenda.md` — this section captures
the design rationale.*

### Device and Pairing Design

Pairing is the default — regardless of device. Two phones works just as well as a
laptop and a phone. The division of labor is the point, not the device: one person
drives the interface, the other pushes the thinking. No need to sort participants by
device type. "Turn to your neighbor" is the entire instruction. Whatever they have
between them, they work with it.

This design feature — articulating thinking to a partner who prompts — produces better
analytical dialogue than two people running in parallel. The phone person isn't
constrained; they're doing the harder job.

One post per pair to the feed. For a 15-person room that's 7–8 posts — clean enough
to aggregate meaningfully, diverse enough to show real divergence.

---

### Beat 1 — State Your Lens (5 min, no devices)

Turn to your neighbor. Discuss:

- What's your investment horizon on a trade like this? Days, months, years?
- What would make PANW a Buy for you? What would make it a Sell?
- What are the two or three things you most need to know from this earnings call?

No typing. Just talk. By the end of five minutes, your pair should be able to state
your shared lens in one sentence.

*Design note:* The horizon question comes first deliberately — it's the thing most
participants won't have thought to declare, and it's the first dimension that separates
a real investment framework from a generic "what does this call say" prompt. The
discussion format (vs. individual writing) warms up the room faster and works for
everyone regardless of device.

---

### Beat 2 — Work the Call with AI (15 min)

One interface per pair — whatever device they have. The person not typing pushes the
thinking; the person typing shapes the prompts. Start by telling the AI your lens from
Beat 1. Then work the call through it.

**Structured moves:**

1. Share your lens. Tell the AI your horizon, your objective, and your two or three
   key questions. Ask what's missing from your framework.
2. Ask it to read the call through your lens — not a summary, a view.
3. Ask what management emphasized vs. avoided.
4. Ask it to argue against your emerging position.
5. Form a view: Buy / Hold / Sell + your biggest conviction + your biggest uncertainty.

You will not finish all five. That is fine.

**Phone-native prompt design:** Prompts must be typeable on a phone in under a minute.
The first move should be short and declarative — something like:

> *"I'm a buy-side investor with an 18-month horizon. I'm looking for alpha vs. the
> market, not just vs. consensus. My key questions are: [two things]. Analyze this
> earnings transcript through that lens."*

That's the frame. Everything after it follows from the frame. The Beat 2 participant
guide (in `workshop/exercise_brief.md`) must model this economy — tight declarative
sentences, not long structured inputs.

---

### Beat 3 — Post and Compare (5 min)

One post per pair to the feed via QR code:

- **Buy / Hold / Sell**
- One sentence: biggest conviction
- One sentence: biggest uncertainty

Then compare with another pair nearby. Did you start with the same horizon? Did you
ask the same questions? What diverged?

*Design note:* Beat 3 is explicitly collaborative — pairs compare with other pairs,
not just within themselves. The divergence across pairs is what the room reads silently
before the demo begins.

---

## Relationship to Branch-Demo

| Branch-Demo Element | Earnings-Demo Equivalent |
|---------------------|--------------------------|
| Slide 2: 5-component framework | Same framework, same slide — re-skin for earnings branding |
| Slide 3: The Problem setup | PANW profile + earnings event + task statement |
| Slide 4: Three Beats | Same structure, adapted Beat 2 prompts for earnings |
| Slides 5–7: What/How We Built | Not a dashboard — the demo IS the artifact |
| Slide 8: What the Model Recommends | Move 1 output: structured investment view |
| Slide 9: What If We Disagree | Move 1 horizon divergence + Move 2 sentiment layer |

Key structural difference: branch-demo's demo showed a *pre-built artifact* (the
dashboard). Earnings-demo's demo IS the live analytical session — nothing is pre-built
except the pre-staged data. This is riskier but more credible for this audience.

The other key difference: branch-demo's demo had an Act 1 that showed the unstructured
baseline. Earnings-demo has no such act — the room's own Beat 2 work serves as the
baseline. The feed is on the screen throughout the demo. No manufactured contrast needed.

---

## Open Design Questions

1. **Beat 2 prompt sequence:** What exactly are the 5 structured prompts participants
   follow during the exercise? These drive the quality of the Mentimeter feed — better
   structured prompts produce more specific conviction and uncertainty statements, which
   make the feed contrast sharper when the demo begins.

2. **The "thing" shown at the end:** Branch-demo had a dashboard. What is the
   equivalent tangible output from the earnings demo that the room walks away thinking
   about? The structured investment view + horizon divergence is strong, but is there a
   more concrete artifact?

3. **Fallback design:** What does the pre-recorded fallback cover? Both moves, or just
   Move 1? Move 2 (sentiment layer) is easiest to skip if time is short.

4. **Backup earnings call:** If PANW's June 2 print is delayed, unusual, or unusable
   for some reason, what's the backup? Need to identify a prior quarter's transcript
   that could substitute with minor adjustments to the demo framing.

---

## Participant Infrastructure Architecture

### Design Principle: One Mentimeter Session, One GitHub Pages QR

Participants join Mentimeter once at the start and stay in it. GitHub Pages QR covers the
exercise content. Cowork is the facilitator's surface throughout. No participant ever needs
to manage two entry points at the same time.

### Mentimeter — One Session, Two Moments

Mentimeter runs as a single persistent presentation across the whole workshop. Participants
join at the opening (settling poll) and the session stays live. The facilitator advances
slides to activate each moment.

**Moment 1 — Settling Poll (opening, during box lunch)**
Three questions, tap-to-answer. Q1: AI journey diagnostic. Q2: market signal read.
Q3: "Will AI be net positive for investment analysis specifically?" Participants join via
the Mentimeter code on the room screen.

**Moment 2 — Beat 3 Posting (exercise close)**
Facilitator advances to the next Mentimeter slide. Buy/Hold/Sell as a tap (multiple choice),
conviction and uncertainty as short text fields. Responses aggregate in real time. Same session,
same join — participants never had to leave.

**Why Mentimeter for Beat 3:** Real-time aggregation is built in. No separate form backend.
Responses are visible to the facilitator immediately and can be projected.

### GitHub Pages — Exercise Content Portal

A static site serving as the participant reference during the exercise. Accessed via a single
QR code displayed in the room from Beat 1 through the end of the demo.

**Contents:**
- Exercise brief (mobile-readable, concise): Beat 1 discussion prompts, Beat 2 five structured
  moves
- PANW one-pager: company overview, platform consolidation thesis in two sentences, stock
  context — enough to ground participants who don't follow PANW closely, without giving away
  the analysis
- No Beat 3 form — that lives in Mentimeter

**No backend required.** GitHub Pages is read-only for participants. All submission happens
through Mentimeter.

### Cowork — Feed Synthesis and Demo Surface

**Feed synthesis (transition moment before the demo):**
Facilitator copies Beat 3 Mentimeter responses into Cowork and asks for a theme synthesis.
Projects the output on the room screen. The room watches their collective investment views
get synthesized by the same tool they just used — and before the structured demo begins.
This is a micro-demo in itself and sets up the Act 1 vs. Act 2 contrast.

**Demo (Acts 1–3):** Cowork is the live analysis surface throughout. Live PPT or Google
Slides handles the presentation frame (PANW profile slide, framework slide). Cowork handles
the actual analytical prompts.

**Feed visibility during demo:** Mentimeter Beat 3 output (or a screenshot of it) remains
visible on the room screen alongside the demo. Participants can see their own positions as
the AI-assisted analysis unfolds.

**Debrief close — Q3 re-poll:** A separate Mentimeter slide re-asks Q3 ("Will AI be net
positive for investment analysis?") at the end of the debrief. Separate from the Beat 3
submission slide — this is a fresh vote, not the same moment. The delta from opening to
close is the closing beat of the session.

### Summary

| Tool | When | Who drives | QR |
|------|------|-----------|-----|
| Mentimeter | Opening (settling poll) + Beat 3 (posting) | Room screen / participants | Yes — on opening slide, stays live |
| GitHub Pages | Exercise brief + Beat 2 support | Participants | Yes — displayed for exercise block |
| Cowork | Feed synthesis + demo (Acts 1–3) | Facilitator | No |
| Live PPT/Slides | Demo frame slides | Facilitator | No |

One Mentimeter join code. One GitHub Pages QR. Never both demanding attention at once.

---

## What This Document Does Not Cover

- **Demo script** (prompt-by-prompt, line-by-line) → `demo_script.md`
- **Fallback recording plan** → `fallback/` directory
- **The slide deck** for setup and debrief → `workshop/` directory
- **Feed app** → `feed-app/` directory
