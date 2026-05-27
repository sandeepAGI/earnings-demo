#!/usr/bin/env python3
"""
gather.py — Stage 2: Data Gather
Pulls financial data from PDFs (Anthropic API), FMP, yfinance, and edgartools.
Writes validated raw files to demo/data/raw/.

Run from project root: python demo/data/gather.py
"""
import base64
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT   = Path(__file__).parent.parent.parent
MANUAL = Path(__file__).parent / "manual"
RAW    = Path(__file__).parent / "raw"

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv(ROOT / ".env")

FMP_API_KEY      = os.environ["FMP_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# PDF filenames (exact, as dropped into manual/)
PDF_SUPPLEMENTAL = "Supplemental Financial Information Q2'26_vF.pdf"
PDF_PRESENTATION = "Q2'26 Earnings Presentation vF.pdf"
PDF_TRANSCRIPT   = ("CORRECTED TRANSCRIPT_ Palo Alto Networks Inc.(PANW-US) "
                    "Q2 2026 Earnings Call 17-February-2026 4_30 PM ET.pdf")


def fail(msg: str) -> None:
    print(f"\n[FATAL] {msg}", file=sys.stderr)
    sys.exit(1)


def check_manual_files() -> None:
    required = [PDF_SUPPLEMENTAL, PDF_PRESENTATION, PDF_TRANSCRIPT]
    missing = [f for f in required if not (MANUAL / f).exists()]
    if missing:
        fail(
            "Missing required manual files:\n"
            + "\n".join(f"  {MANUAL / f}" for f in missing)
            + "\n\nPlace PDFs from PANW IR into demo/data/manual/ and re-run."
        )
    print("[✓] Manual files present")


def pdf_base64(filename: str) -> str:
    return base64.standard_b64encode((MANUAL / filename).read_bytes()).decode()


def write_raw(filename: str, data: dict | list | str) -> None:
    path = RAW / filename
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[✓] Wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# Claude API helper
# ---------------------------------------------------------------------------

def claude_extract(pdf_b64: str, prompt: str, *, model: str = "claude-opus-4-7") -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# [1/6] Supplemental PDF → panw_supplemental_8q.json
# ---------------------------------------------------------------------------

SUPPLEMENTAL_PROMPT = """
You are extracting structured financial data from a Palo Alto Networks supplemental financial information document.

Extract the following for EVERY quarter shown (up to 8 quarters). Return a JSON object with this structure:

{
  "source_document": "Supplemental Financial Information Q2'26_vF.pdf",
  "quarters": [
    {
      "fiscal_period": "Q2_FY26",
      "fiscal_date_ending": "2026-01-31",
      "report_date": "2026-02-17",
      "revenue_total_m": <number in millions>,
      "revenue_product_m": <number in millions>,
      "revenue_subscription_support_m": <number in millions>,
      "revenue_yoy_growth_pct": <number, e.g. 15.0 for 15%>,
      "gross_profit_gaap_m": <number in millions or null>,
      "gross_margin_gaap_pct": <number, e.g. 74.2>,
      "gross_margin_nongaap_pct": <number, e.g. 76.6>,
      "operating_income_gaap_m": <number in millions>,
      "operating_margin_gaap_pct": <number>,
      "operating_income_nongaap_m": <number in millions>,
      "operating_margin_nongaap_pct": <number>,
      "net_income_gaap_m": <number in millions>,
      "eps_gaap_diluted": <number>,
      "eps_nongaap_diluted": <number>,
      "fcf_m": <number in millions or null>,
      "fcf_margin_pct": <number or null>,
      "ngs_arr_bn": <number in billions or null>,
      "remaining_performance_obligations_bn": <number in billions or null>,
      "deferred_revenue_current_bn": <number in billions or null>,
      "deferred_revenue_longterm_bn": <number in billions or null>,
      "shares_diluted_m": <number in millions or null>
    }
  ]
}

Rules:
- Fiscal periods: Q2 FY26 = 2026-01-31, Q1 FY26 = 2025-10-31, Q4 FY25 = 2025-07-31, Q3 FY25 = 2025-04-30, Q2 FY25 = 2025-01-31, Q1 FY25 = 2024-10-31, Q4 FY24 = 2024-07-31, Q3 FY24 = 2024-04-30
- All dollar values in millions UNLESS the field name ends in _bn (then billions)
- Percentages as numbers: 76.6 not 0.766
- Use null for any field not present in the document, never guess
- If revenue_yoy_growth_pct is not stated, derive it from adjacent quarters if both are present; otherwise null
- Return ONLY valid JSON, no commentary
"""


def gather_supplemental() -> None:
    print("\n[1/6] Supplemental PDF → panw_supplemental_8q.json")
    b64 = pdf_base64(PDF_SUPPLEMENTAL)
    raw_text = claude_extract(b64, SUPPLEMENTAL_PROMPT)

    # Strip markdown code fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        fail(f"Claude returned invalid JSON for supplemental: {e}\n\nRaw:\n{raw_text[:500]}")

    if "quarters" not in data or not data["quarters"]:
        fail("Supplemental extraction returned no quarters")

    # Validate Q2 FY26 row is present
    q2_rows = [q for q in data["quarters"] if q.get("fiscal_period") == "Q2_FY26"]
    if not q2_rows:
        fail("Q2_FY26 row missing from supplemental extraction")

    q2 = q2_rows[0]
    if q2.get("revenue_total_m") is None:
        fail("Q2_FY26 revenue_total_m is null — extraction failed")

    print(f"    Q2 FY26 revenue: ${q2['revenue_total_m']}M  non-GAAP EPS: ${q2['eps_nongaap_diluted']}")
    write_raw("panw_supplemental_8q.json", data)


# ---------------------------------------------------------------------------
# [2/6] Presentation PDF → panw_q2fy26_guidance.json
# ---------------------------------------------------------------------------

GUIDANCE_PROMPT = """
You are extracting guidance and beat/miss data from a Palo Alto Networks earnings presentation.

Extract the following and return a JSON object:

{
  "source_document": "Q2'26 Earnings Presentation vF.pdf",
  "beat_miss_q2_fy26": {
    "eps_nongaap_actual": <number>,
    "eps_nongaap_consensus": <number or null>,
    "eps_beat_pct": <number or null, e.g. 9.6 for 9.6%>,
    "revenue_actual_m": <number in millions>,
    "revenue_consensus_m": <number in millions or null>,
    "revenue_beat_pct": <number or null>
  },
  "guidance_q3_fy26": {
    "revenue_low_m": <number in millions>,
    "revenue_high_m": <number in millions>,
    "eps_nongaap_low": <number>,
    "eps_nongaap_high": <number>,
    "ngs_arr_low_bn": <number in billions or null>,
    "ngs_arr_high_bn": <number in billions or null>,
    "revision_vs_prior": "raise" | "maintain" | "cut" | "initial"
  },
  "guidance_fy26_full_year": {
    "revenue_low_m": <number in millions>,
    "revenue_high_m": <number in millions>,
    "eps_nongaap_low": <number>,
    "eps_nongaap_high": <number>,
    "ngs_arr_low_bn": <number in billions or null>,
    "ngs_arr_high_bn": <number in billions or null>,
    "fcf_margin_low_pct": <number or null>,
    "fcf_margin_high_pct": <number or null>,
    "revision_vs_prior": "raise" | "maintain" | "cut" | "initial"
  },
  "operational_kpis": {
    "platformized_customers": <integer or null>,
    "ngs_arr_bn": <number in billions or null>,
    "ngs_arr_yoy_growth_pct": <number or null>,
    "remaining_performance_obligations_bn": <number in billions or null>,
    "rpo_yoy_growth_pct": <number or null>
  }
}

Rules:
- Revenue in millions. NGS ARR in billions. Percentages as numbers (15.0 not 0.15).
- For revision_vs_prior: "raise" if guidance increased vs prior quarter's guidance, "maintain" if unchanged, "initial" if first guidance for this period.
- Use null for any field not present; do not guess.
- Return ONLY valid JSON, no commentary.
"""


def gather_guidance() -> None:
    print("\n[2/6] Presentation PDF → panw_q2fy26_guidance.json")
    b64 = pdf_base64(PDF_PRESENTATION)
    raw_text = claude_extract(b64, GUIDANCE_PROMPT)

    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        fail(f"Claude returned invalid JSON for guidance: {e}\n\nRaw:\n{raw_text[:500]}")

    q3g = data.get("guidance_q3_fy26", {})
    if not q3g.get("revenue_low_m"):
        fail("Q3 FY26 guidance revenue missing from extraction")

    print(f"    Q3 guidance: ${q3g['revenue_low_m']}–${q3g['revenue_high_m']}M revenue")
    write_raw("panw_q2fy26_guidance.json", data)


# ---------------------------------------------------------------------------
# [3/6] Transcript PDF → panw_q2fy26_transcript.txt + panw_q2fy26_transcript_qa.json
# ---------------------------------------------------------------------------

TRANSCRIPT_EXTRACT_PROMPT = """
You are extracting the full text of a Palo Alto Networks earnings call transcript from a PDF.

Return the complete verbatim transcript text, preserving speaker names, section headers (PREPARED REMARKS, QUESTION AND ANSWER), and all spoken content. Do not summarize. Do not omit any content.

Format:
- Each speaker line: "SPEAKER NAME: text of what they said"
- Keep paragraphs as spoken
- Include all Q&A exchanges

Return ONLY the transcript text, no preamble or commentary.
"""

TRANSCRIPT_QA_PROMPT = """
You are parsing a Palo Alto Networks earnings call transcript and extracting the Q&A section as structured data.

For each Q&A exchange, extract:

Return a JSON object:
{
  "source_document": "CORRECTED TRANSCRIPT_ Palo Alto Networks Inc.(PANW-US) Q2 2026 Earnings Call 17-February-2026 4_30 PM ET.pdf",
  "call_date": "2026-02-17",
  "company": "PANW",
  "fiscal_period": "Q2_FY26",
  "exchanges": [
    {
      "exchange_num": 1,
      "analyst_name": "First Last",
      "analyst_firm": "Firm Name",
      "question_text": "full question text",
      "respondent": "Nikesh Arora" | "Dipak Golechha" | "Other Name",
      "answer_text": "full answer text",
      "topics": ["platformization", "NGS ARR", "guidance", "competition", "margins", "AI", "federal"],
      "key_signal": "bullish" | "bearish" | "neutral",
      "analytical_note": "one sentence: what this exchange reveals about company trajectory or risk"
    }
  ]
}

Rules for key_signal:
- "bullish": management expresses confidence, raises guidance, reports acceleration, announces wins
- "bearish": management hedges, acknowledges competitive pressure, guides down, flags risk
- "neutral": factual clarification, accounting question, housekeeping

Rules for analytical_note:
- One sentence. Factual observation from the exchange. No investment recommendation.
- Example: "Management confirmed platformization pace is accelerating with 35% YoY customer growth."
- Do NOT write: "This is bullish for the stock."

Return ONLY valid JSON, no commentary.
"""


def gather_transcript() -> None:
    print("\n[3/6] Transcript PDF → panw_q2fy26_transcript.txt + panw_q2fy26_transcript_qa.json")
    b64 = pdf_base64(PDF_TRANSCRIPT)

    print("    Extracting full transcript text...")
    transcript_text = claude_extract(b64, TRANSCRIPT_EXTRACT_PROMPT)

    if len(transcript_text) < 5000:
        fail(f"Transcript text too short ({len(transcript_text)} chars) — extraction may have failed")

    write_raw("panw_q2fy26_transcript.txt", transcript_text)
    print(f"    Transcript: {len(transcript_text):,} chars")

    print("    Extracting Q&A structure and tagging...")
    raw_qa = claude_extract(b64, TRANSCRIPT_QA_PROMPT)

    text = raw_qa.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        qa_data = json.loads(text)
    except json.JSONDecodeError as e:
        fail(f"Claude returned invalid JSON for Q&A: {e}\n\nRaw:\n{raw_qa[:500]}")

    exchanges = qa_data.get("exchanges", [])
    if not exchanges:
        fail("No Q&A exchanges extracted from transcript")

    print(f"    Q&A exchanges: {len(exchanges)}")
    write_raw("panw_q2fy26_transcript_qa.json", qa_data)


# ---------------------------------------------------------------------------
# [4/6] yfinance earnings history → panw_earnings_estimates.json
# Note: FMP v3 earnings-surprises is a legacy endpoint (blocked post Aug 2025).
# yfinance earnings_history provides non-GAAP EPS actual + consensus for ~4 quarters.
# Revenue consensus is not available from free APIs for historical quarters;
# revenue_consensus_m is left null and must be sourced manually if needed.
# ---------------------------------------------------------------------------

def gather_yf_estimates() -> None:
    import yfinance as yf

    print("\n[4/6] yfinance → panw_earnings_estimates.json")
    ticker = yf.Ticker("PANW")

    # EPS actual + consensus for recent quarters
    eh = ticker.earnings_history
    if eh is None or eh.empty:
        fail("yfinance earnings_history returned empty for PANW")

    # Revenue actuals from quarterly income statement
    is_ = ticker.quarterly_income_stmt
    rev_series = is_.loc["Total Revenue"] if "Total Revenue" in is_.index else None

    history_records = []
    for quarter_date, row in eh.iterrows():
        date_str = quarter_date.strftime("%Y-%m-%d")
        rev_actual = None
        if rev_series is not None:
            ts = quarter_date.normalize() if hasattr(quarter_date, "normalize") else quarter_date
            matching = [v for k, v in rev_series.items()
                        if hasattr(k, "strftime") and k.strftime("%Y-%m-%d") == date_str]
            if matching and matching[0] is not None:
                try:
                    rev_actual = round(float(matching[0]) / 1e6, 1)
                except (TypeError, ValueError):
                    pass

        history_records.append({
            "fiscal_date_ending": date_str,
            "eps_nongaap_actual": float(row["epsActual"]) if row["epsActual"] is not None else None,
            "eps_nongaap_estimate": float(row["epsEstimate"]) if row["epsEstimate"] is not None else None,
            "eps_difference": float(row["epsDifference"]) if row["epsDifference"] is not None else None,
            "eps_surprise_pct": round(float(row["surprisePercent"]) * 100, 2) if row["surprisePercent"] is not None else None,
            "revenue_actual_m": rev_actual,
            "revenue_consensus_m": None,
        })

    # Validate Q2 FY26 row
    q2_rows = [r for r in history_records if r["fiscal_date_ending"] == "2026-01-31"]
    if not q2_rows:
        fail("Q2 FY26 (2026-01-31) missing from yfinance earnings_history")

    q2 = q2_rows[0]
    print(f"    Q2 FY26 non-GAAP EPS: actual={q2['eps_nongaap_actual']}  "
          f"consensus={q2['eps_nongaap_estimate']}  beat={q2['eps_surprise_pct']}%")

    payload = {
        "source": "yfinance PANW earnings_history + quarterly_income_stmt",
        "retrieved_date": "2026-05-27",
        "note": (
            "eps figures are non-GAAP (yfinance reports analyst-consensus non-GAAP for PANW). "
            "revenue_consensus_m unavailable from free APIs for historical quarters — left null."
        ),
        "q2_fy26_fiscal_date": "2026-01-31",
        "earnings_history": history_records,
    }
    write_raw("panw_earnings_estimates.json", payload)


# ---------------------------------------------------------------------------
# [5/6] yfinance monthly price → panw_price_monthly.json
# ---------------------------------------------------------------------------

def gather_price() -> None:
    import yfinance as yf

    print("\n[5/6] yfinance → panw_price_monthly.json")
    ticker = yf.Ticker("PANW")
    hist = ticker.history(period="5y", interval="1mo")

    if hist.empty:
        fail("yfinance returned empty price history for PANW")

    records = []
    for date, row in hist.iterrows():
        records.append({
            "date": date.strftime("%Y-%m-%d"),
            "open": round(float(row["Open"]), 4),
            "high": round(float(row["High"]), 4),
            "low": round(float(row["Low"]), 4),
            "close": round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
            "split_adjusted": 1,
        })

    payload = {
        "source": "yfinance PANW monthly 5y",
        "retrieved_date": "2026-05-27",
        "ticker": "PANW",
        "interval": "1mo",
        "records": records,
    }

    # Spot-check: find Feb 2026 close (earnings month)
    feb26 = [r for r in records if r["date"].startswith("2026-02")]
    if feb26:
        print(f"    Feb 2026 close: ${feb26[0]['close']}")
    print(f"    {len(records)} monthly bars")
    write_raw("panw_price_monthly.json", payload)


# ---------------------------------------------------------------------------
# [6/6] edgartools Form 4 → panw_q2fy26_form4_summary.json
# ---------------------------------------------------------------------------

def gather_form4() -> None:
    print("\n[6/6] edgartools → panw_q2fy26_form4_summary.json")

    try:
        import edgar
        from edgar import Company
    except ImportError:
        fail("edgartools not installed. Run: pip install edgartools")

    # SEC requires a User-Agent header identifying the requester
    edgar.set_identity("Aileron Group info@aileron-group.com")

    company = Company("PANW")
    filings = company.get_filings(form="4", filing_date="2025-11-01:2026-02-17")

    if filings is None or len(filings) == 0:
        fail("edgartools returned no Form 4 filings for PANW in the Q2 FY26 window")

    records = []
    for filing in filings:
        try:
            f4 = filing.obj()
            transactions = []

            # Non-derivative transactions (common stock open-market trades, awards, etc.)
            ndt = f4.non_derivative_table
            if ndt is not None and ndt.has_transactions:
                for txn in ndt.transactions:
                    transactions.append({
                        "transaction_date": str(getattr(txn, 'date', None)),
                        "security_title": str(getattr(txn, 'security', None)),
                        "transaction_code": str(getattr(txn, 'transaction_code', None)),
                        "transaction_type": str(getattr(txn, 'transaction_type', None)),
                        "shares": float(getattr(txn, 'shares', 0) or 0),
                        "price_per_share": float(getattr(txn, 'price', 0) or 0) if getattr(txn, 'price', None) is not None else None,
                        "acquired_disposed": str(getattr(txn, 'acquired_disposed', None)),
                        "direct_indirect": str(getattr(txn, 'direct_indirect', None)),
                    })

            # Derivative transactions (options, RSUs with exercise events)
            ddt = f4.derivative_table
            if ddt is not None and hasattr(ddt, 'has_transactions') and ddt.has_transactions:
                for txn in ddt.transactions:
                    transactions.append({
                        "transaction_date": str(getattr(txn, 'date', None)),
                        "security_title": str(getattr(txn, 'security', None)),
                        "transaction_code": str(getattr(txn, 'transaction_code', None)),
                        "transaction_type": str(getattr(txn, 'transaction_type', None)),
                        "shares": float(getattr(txn, 'shares', 0) or 0),
                        "price_per_share": None,
                        "acquired_disposed": str(getattr(txn, 'acquired_disposed', None)),
                        "direct_indirect": str(getattr(txn, 'direct_indirect', None)),
                    })

            record = {
                "filing_date": str(filing.filing_date),
                "accession_number": str(filing.accession_number),
                "reporting_owner": str(f4.insider_name) if hasattr(f4, 'insider_name') else "Unknown",
                "issuer": "PANW",
                "transaction_count": len(transactions),
                "transactions": transactions,
            }
            records.append(record)
        except Exception as e:
            print(f"    WARNING: Could not parse filing {filing.accession_number}: {e}")

    if not records:
        fail("No Form 4 records successfully parsed")

    payload = {
        "source": "edgartools SEC EDGAR PANW Form 4",
        "window": "2025-11-01 to 2026-02-17",
        "window_rule": "Full Q2 FY26 fiscal quarter, post-earnings inclusive",
        "retrieved_date": "2026-05-27",
        "filing_count": len(records),
        "filings": records,
    }

    print(f"    Form 4 filings: {len(records)}")
    write_raw("panw_q2fy26_form4_summary.json", payload)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("gather.py — PANW Q2 FY26 Data Gather")
    print("=" * 60)

    RAW.mkdir(parents=True, exist_ok=True)
    check_manual_files()

    gather_supplemental()
    gather_guidance()
    gather_transcript()
    gather_yf_estimates()
    gather_price()
    gather_form4()

    print("\n" + "=" * 60)
    print("gather.py complete. Check demo/data/raw/ for output files.")
    print("=" * 60)


if __name__ == "__main__":
    main()
