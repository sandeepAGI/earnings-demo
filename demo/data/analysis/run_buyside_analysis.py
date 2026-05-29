"""
Buy-side framework analysis — PANW Q2 FY26
Generates: panw_q2fy26_buyside_analysis.json

Architecture:
- 5 fixed framework dimensions (reusable across quarters — only the answers change)
- Claude generates a quarter-specific question + answer for each dimension
- Final synthesis step produces a recommendation with explicit horizon
- Schema is stable: re-run with new data, same structure, no script edits needed
"""

import json
import os
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

RAW  = Path(__file__).parent.parent / "raw"
DB   = Path(__file__).parent.parent / "db" / "earnings.db"
OUT  = Path(__file__).parent / "panw_q2fy26_buyside_analysis.json"
SELL = Path(__file__).parent / "panw_q2fy26_earnings_analysis.json"

def require_file(p: Path) -> Path:
    if not p.exists():
        sys.exit(f"MISSING: {p}")
    return p

def load_json(p: Path) -> dict:
    with open(require_file(p)) as f:
        return json.load(f)

def load_text(p: Path) -> str:
    with open(require_file(p)) as f:
        return f.read()

def parse_delimited(text: str, fields: list) -> dict:
    """Parse a response using ---FIELD--- delimiters. Robust against any content."""
    result = {}
    for i, field in enumerate(fields):
        marker = f"---{field.upper()}---"
        next_marker = f"---{fields[i+1].upper()}---" if i + 1 < len(fields) else None
        start = text.find(marker)
        if start == -1:
            sys.exit(f"Missing delimiter {marker} in response:\n{text[:400]}")
        start += len(marker)
        end = text.find(next_marker) if next_marker else len(text)
        result[field] = text[start:end].strip()
    return result

def parse_json_response(text: str, fields: list) -> dict:
    """Try JSON first, fall back to delimiter parsing."""
    stripped = text.strip()
    # Strip markdown fences if present
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    # JSON failed (likely unescaped quotes in content) — use delimiters
    if all(f"---{f.upper()}---" in text for f in fields):
        return parse_delimited(text, fields)
    sys.exit(f"Could not parse response. Fields: {fields}\nResponse:\n{text[:400]}")

# ── Framework definition — fixed, reusable across quarters ────────────────────

FRAMEWORK = {
    "horizon":   "6 months",
    "objective": "alpha vs. market",
    "role":      "buy-side",
}

DIMENSIONS = [
    {
        "id":         "Q1",
        "dimension":  "Alpha Edge",
        "definition": (
            "Given the market's post-earnings reaction, what is the market's apparent "
            "verdict on this print, and what might it be mispricing or overweighting? "
            "The after-hours move is the market's answer — the analyst's job is to assess "
            "whether that verdict is right, too harsh, or too lenient, and where the "
            "information asymmetry lies."
        ),
    },
    {
        "id":         "Q2",
        "dimension":  "Thesis Integrity",
        "definition": (
            "Is the core investment thesis still intact? Focus on the metrics that directly "
            "validate or challenge the primary bull case. Separate what this print proves "
            "from what it leaves open. Flag any data points that quietly weaken the thesis "
            "without appearing in the headline numbers."
        ),
    },
    {
        "id":         "Q3",
        "dimension":  "Guidance Credibility",
        "definition": (
            "What is management signaling about the forward trajectory? Assess whether "
            "guidance reflects sandbagging, realistic caution, or stretched optimism. "
            "What did the Q&A reveal beyond the headline numbers — in tone, specificity, "
            "deflection, or what was conspicuously left unsaid?"
        ),
    },
    {
        "id":         "Q4",
        "dimension":  "Peer Context",
        "definition": (
            "Relative to the competitive set, who is winning the key strategic trade? "
            "What does peer performance say about this company's positioning? For a "
            "platform company, is the moat widening or narrowing? Peer results are "
            "evidence about the industry, not just about the competitor."
        ),
    },
    {
        "id":         "Q5",
        "dimension":  "Sentiment / Positioning",
        "definition": (
            "What does the positioning setup say about the risk/reward asymmetry? "
            "Short interest, options activity, and the after-hours reaction can create "
            "asymmetric setups independent of the fundamental view. Distinguish what is "
            "a positioning edge from what is an information edge. Asymmetric reactions "
            "to the same print often come from positioning, not information."
        ),
    },
]

# ── Load source data ──────────────────────────────────────────────────────────
print("Loading source data...")
sell_side  = load_json(SELL)
guidance   = load_json(RAW / "panw_q2fy26_guidance.json")
transcript = load_text(RAW / "panw_q2fy26_transcript.txt")
qa_json    = load_json(RAW / "panw_q2fy26_transcript_qa.json")
crwd       = load_json(RAW / "crwd_q4fy26_results.json")
supp       = load_json(RAW / "panw_supplemental_8q.json")

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
kpis = {r["kpi_name"]: r["kpi_value"] for r in conn.execute(
    "SELECT kpi_name, kpi_value FROM company_kpis WHERE symbol='PANW' AND fiscal_period='Q2_FY26'"
).fetchall()}
conn.close()

# ── Build context block ───────────────────────────────────────────────────────
context = f"""
=== SELL-SIDE RESEARCH NOTE (equity-research/earnings-analysis v0.1.0) ===
{json.dumps(sell_side, indent=2)}

=== KEY Q2 FY26 KPIs FROM DATABASE ===
{json.dumps(dict(kpis), indent=2)}

=== Q2 FY26 GUIDANCE ===
{json.dumps(guidance, indent=2)}

=== CRWD Q4 FY26 RESULTS (peer) ===
{json.dumps(crwd, indent=2)}

=== EARNINGS CALL Q&A EXCHANGES (tagged) ===
{json.dumps(qa_json, indent=2)}

=== TRANSCRIPT EXCERPT (management prepared remarks) ===
{transcript[:6000]}
"""

SYSTEM = """You are a senior buy-side equity analyst. Your investment horizon is 6 months.
Your objective is alpha vs. the market — not vs. consensus. You are forming a portfolio
decision, not publishing a sell-side note.

Be direct and specific. Cite numbers. Distinguish data from inference.
No preamble. No filler. Lead with the most important point."""

DIMENSION_PROMPT = """\
Context:
{context}

---

Buy-side framework — {dimension} dimension:
{definition}

Horizon: {horizon} | Objective: {objective}

Task: Apply this lens to the PANW Q2 FY26 print.

Respond using exactly this format (include the delimiter lines verbatim):

---QUESTION---
The sharpest single question this dimension raises given the specific dynamics of this quarter (one sentence)
---ANSWER---
Your direct answer: 2-4 tight paragraphs, specific numbers cited, data distinguished from inference"""

RECOMMENDATION_PROMPT = """\
You have completed a five-dimension buy-side analysis of PANW Q2 FY26.

Horizon: {horizon} | Objective: {objective}

Dimension findings:
{summaries}

Based on these five dimensions, state your investment recommendation.

Respond using exactly this format (include the delimiter lines verbatim):

---STANCE---
Buy or Hold or Sell (one word only)
---CONVICTION---
One sentence stating the primary conviction that drives the stance
---UNCERTAINTY---
One sentence stating the key uncertainty that could change the view
---RATIONALE---
2-3 sentences synthesizing the recommendation from the five dimensions"""

# ── Run analysis ──────────────────────────────────────────────────────────────
client  = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
results = []

for dim in DIMENSIONS:
    print(f"  {dim['id']} — {dim['dimension']}...")
    prompt = DIMENSION_PROMPT.format(
        context    = context,
        dimension  = dim["dimension"],
        definition = dim["definition"],
        horizon    = FRAMEWORK["horizon"],
        objective  = FRAMEWORK["objective"],
    )
    msg = client.messages.create(
        model      = "claude-opus-4-7",
        max_tokens = 2048,
        system     = SYSTEM,
        messages   = [{"role": "user", "content": prompt}],
    )
    parsed = parse_delimited(msg.content[0].text, ["question", "answer"])
    results.append({
        "id":        dim["id"],
        "dimension": dim["dimension"],
        "question":  parsed["question"],
        "answer":    parsed["answer"],
    })
    print(f"    ✓ Q: {parsed['question'][:80]}...")

# ── Recommendation synthesis ──────────────────────────────────────────────────
print("  Recommendation synthesis...")
summaries = "\n\n".join(
    f"{r['dimension']}:\nQ: {r['question']}\nA: {r['answer'][:300]}..."
    for r in results
)
rec_prompt = RECOMMENDATION_PROMPT.format(
    horizon   = FRAMEWORK["horizon"],
    objective = FRAMEWORK["objective"],
    summaries = summaries,
)
rec_msg = client.messages.create(
    model      = "claude-opus-4-7",
    max_tokens = 512,
    system     = SYSTEM,
    messages   = [{"role": "user", "content": rec_prompt}],
)
rec_parsed = parse_delimited(
    rec_msg.content[0].text,
    ["stance", "conviction", "uncertainty", "rationale"],
)
recommendation = {
    "horizon":     FRAMEWORK["horizon"],
    "stance":      rec_parsed["stance"],
    "conviction":  rec_parsed["conviction"],
    "uncertainty": rec_parsed["uncertainty"],
    "rationale":   rec_parsed["rationale"],
}
print(f"    ✓ Stance: {recommendation.get('stance', '?')}")

# ── Write output ──────────────────────────────────────────────────────────────
output = {
    "generated":   str(date.today()),
    "symbol":      "PANW",
    "fiscal_period": "Q2_FY26",
    "report_date": "2026-02-17",
    "framework":   FRAMEWORK,
    "dimensions":  results,
    "recommendation": recommendation,
}

with open(OUT, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n✅ {OUT}")
print(f"   {len(results)} dimensions | Recommendation: {recommendation.get('stance', '?')}")
