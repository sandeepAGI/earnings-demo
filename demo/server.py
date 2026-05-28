"""
Chat server for Tab 3 — PANW Q2 FY26 buy-side analysis
Serves the dashboard HTML and a /chat SSE endpoint backed by Claude + Tavily.

Usage:
    python3 demo/server.py
    Open: http://localhost:8000
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from tavily import TavilyClient

ROOT = Path(__file__).parent
load_dotenv(ROOT.parent / ".env")

# ── Validate keys at startup ──────────────────────────────────────────────────
for key in ("ANTHROPIC_API_KEY", "TAVILY_API_KEY"):
    if not os.environ.get(key):
        sys.exit(f"Missing {key} in .env")

claude  = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
tavily  = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# ── Load context once at startup ──────────────────────────────────────────────
def _load():
    analysis_dir = ROOT / "data" / "analysis"
    raw_dir      = ROOT / "data" / "raw"
    db_path      = ROOT / "data" / "db" / "earnings.db"

    sell = json.loads((analysis_dir / "panw_q2fy26_earnings_analysis.json").read_text())
    buy  = json.loads((analysis_dir / "panw_q2fy26_buyside_analysis.json").read_text())
    crwd = json.loads((raw_dir / "crwd_q4fy26_results.json").read_text())

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    kpis = {r["kpi_name"]: r["kpi_value"] for r in conn.execute(
        "SELECT kpi_name, kpi_value FROM company_kpis WHERE symbol='PANW' AND fiscal_period='Q2_FY26'"
    ).fetchall()}
    conn.close()

    transcript = (raw_dir / "panw_q2fy26_transcript.txt").read_text()[:8000]

    return f"""
=== PANW Q2 FY26 — ANALYSIS CONTEXT ===
Report date: February 17, 2026. Fiscal period: Q2 FY26 (ending Jan 31, 2026).

--- SELL-SIDE RESEARCH NOTE (equity-research/earnings-analysis v0.1.0) ---
Rating: {sell["steps"]["11_rating"]["rating"]} | PT: ${sell["steps"]["11_rating"]["price_target"]} | Upside: +{sell["steps"]["11_rating"]["implied_upside_pct"]}%
EPS: ${sell["steps"]["5_beat_miss"]["eps_nongaap"]["actual"]} actual vs ${sell["steps"]["5_beat_miss"]["eps_nongaap"]["consensus"]:.3f} consensus (+{sell["steps"]["5_beat_miss"]["eps_nongaap"]["beat_pct"]}% beat)
Revenue: ${sell["steps"]["5_beat_miss"]["revenue"]["actual_m"]}M (+{sell["steps"]["5_beat_miss"]["revenue"]["yoy_growth_pct"]}% YoY)
NGS ARR: ${sell["steps"]["5_beat_miss"]["ngs_arr"]["actual_bn"]}B (+{sell["steps"]["5_beat_miss"]["ngs_arr"]["yoy_growth_pct"]}% reported, +{sell["steps"]["5_beat_miss"]["ngs_arr"]["organic_yoy_pct"]}% organic)
AH reaction: {sell["steps"]["5_beat_miss"]["stock_reaction"]["ah_change_pct"]:+.2f}%
Q3 FY26 EPS guidance: ${sell["steps"]["8_guidance"]["q3_fy26"]["eps_midpoint"]} midpoint (vs Q2 actual $1.03)
FY26 EPS guidance: ${sell["steps"]["8_guidance"]["fy26_full_year"]["eps_midpoint"]} midpoint (raised)
Non-GAAP OI margin: {sell["steps"]["7_margin"]["q2_fy26"]["oi_margin_nongaap_pct"]}% (+{sell["steps"]["7_margin"]["yoy_delta_bps"]["oi_margin_nongaap"]}bps YoY)
Platformized customers: {sell["steps"]["6_segment_geo"]["platformized_customers"]}
RPO: ${sell["steps"]["6_segment_geo"]["rpo_bn"]}B (+{sell["steps"]["6_segment_geo"]["rpo_yoy_pct"]}% YoY)
Peer CRWD EV/Rev TTM: {sell["steps"]["10_valuation"]["peer_table"][0]["ev_rev_ttm_x"]}x | PANW NTM: {sell["steps"]["10_valuation"]["panw_ev_rev_ntm_x"]}x

--- KEY KPIs (database) ---
{json.dumps(kpis, indent=2)}

--- BUY-SIDE FRAMEWORK INTERROGATION (pre-run) ---
{chr(10).join(f'Q: {q["title"]}{chr(10)}A: {q["answer"]}{chr(10)}' for q in buy["questions"])}

--- CRWD Q4 FY26 (peer) ---
{json.dumps(crwd, indent=2)}

--- EARNINGS CALL TRANSCRIPT EXCERPT ---
{transcript}
"""

print("Loading context...")
CONTEXT = _load()
print(f"  Context loaded: {len(CONTEXT):,} chars")

SYSTEM = f"""You are a senior buy-side equity analyst covering enterprise cybersecurity.
You have deep knowledge of Palo Alto Networks Q2 FY26 earnings (Feb 17, 2026).

Your context includes the full sell-side research note, key financial metrics,
a buy-side framework interrogation of the key questions, CRWD peer results,
and the earnings call transcript.

Be direct and specific. Cite numbers. Distinguish data from inference.
Use web search when you need current market data — stock prices, recent news,
competitor updates after the Feb 17 earnings date.

Do not say "great question." Lead with the most important point.
Keep answers focused: 2-4 paragraphs unless a table or list is clearly better.

Pre-loaded context:
{CONTEXT}"""

SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for current market data, recent news, or competitor updates. Use when the question requires information after Feb 17, 2026 or current stock prices.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
        },
        "required": ["query"],
    },
}

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    messages: list  # [{role, content}]

@app.get("/")
def serve_dashboard():
    return FileResponse(ROOT / "earnings_baseline.html")

@app.post("/chat")
async def chat(req: ChatRequest):
    async def event_stream():
        try:
            messages = req.messages

            # First pass — may include tool use
            response = claude.messages.create(
                model="claude-opus-4-7",
                max_tokens=2048,
                system=SYSTEM,
                tools=[SEARCH_TOOL],
                messages=messages,
            )

            # Handle tool use
            if response.stop_reason == "tool_use":
                tool_block = next(b for b in response.content if b.type == "tool_use")
                query = tool_block.input["query"]

                # Signal to frontend: search is happening
                yield f"event: searching\ndata: {json.dumps({'query': query})}\n\n"

                # Execute search
                results = tavily.search(query=query, search_depth="basic", max_results=4)
                search_text = "\n\n".join(
                    f"[{r['title']}]\n{r['content']}" for r in results.get("results", [])
                )

                # Convert SDK content blocks to plain dicts for the follow-up call
                assistant_content = [
                    block.model_dump() for block in response.content
                ]

                # Continue with tool result — now stream
                followup_messages = messages + [
                    {"role": "assistant", "content": assistant_content},
                    {"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": tool_block.id, "content": search_text}
                    ]},
                ]

                with claude.messages.stream(
                    model="claude-opus-4-7",
                    max_tokens=2048,
                    system=SYSTEM,
                    messages=followup_messages,
                ) as stream:
                    for text in stream.text_stream:
                        yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"

            else:
                # No tool use — stream from the completed response
                for block in response.content:
                    if hasattr(block, "text"):
                        text = block.text
                        chunk = 12
                        for i in range(0, len(text), chunk):
                            yield f"event: token\ndata: {json.dumps({'text': text[i:i+chunk]})}\n\n"

            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            print(f"ERROR in event_stream: {type(e).__name__}: {e}")
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    print("\n  Dashboard: http://localhost:8000")
    print("  Chat API:  http://localhost:8000/chat\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
