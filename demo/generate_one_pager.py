#!/usr/bin/env python3
"""
Generate docs/index.html — PANW Q3 FY26 facts-only one-pager for workshop participants.

Mobile-first, tap-to-copy, no analytical conclusions.
Source: demo/data/db/earnings.db + selected raw JSON files.

Pedagogical guardrail: facts only. No rating, no PT, no bull/bear framing,
no skill-applied signals (answered/partial/deflected). Participants must
lead with their own framework.
"""

import sqlite3
import json
import html
import re
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent
DB = ROOT / "data" / "db" / "earnings.db"
RAW = ROOT / "data" / "raw"
DOCS = ROOT.parent / "docs"
DOCS.mkdir(exist_ok=True)
OUT = DOCS / "index.html"


# ── Data loading ──────────────────────────────────────────────────────────────
def load():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    fin = conn.execute(
        "SELECT * FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()

    kpis = {
        r["kpi_name"]: r["kpi_value"]
        for r in conn.execute(
            "SELECT kpi_name, kpi_value FROM company_kpis WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
        ).fetchall()
    }

    guidance = conn.execute(
        "SELECT issued_for_period, metric, low_value, high_value, unit, revision_vs_prior FROM guidance WHERE symbol='PANW' ORDER BY id"
    ).fetchall()

    eps_hist = conn.execute(
        "SELECT fiscal_date_ending, eps_nongaap_actual, eps_nongaap_estimate, eps_surprise_pct FROM eps_history WHERE symbol='PANW' ORDER BY fiscal_date_ending DESC LIMIT 5"
    ).fetchall()

    qa = conn.execute(
        "SELECT exchange_num, analyst_name, analyst_firm, topics, answer_text, respondent FROM transcript_qa WHERE symbol='PANW' AND fiscal_period='Q3_FY26' ORDER BY exchange_num"
    ).fetchall()

    insiders = conn.execute(
        "SELECT filing_date, insider_name, insider_role, transaction_code, shares, price_per_share, total_value_m, is_10b5_1_plan FROM insider_transactions WHERE symbol='PANW' AND filing_date BETWEEN '2026-02-01' AND '2026-06-02' ORDER BY filing_date, insider_name"
    ).fetchall()

    sentiment = {
        r["signal_type"]: {"value": r["value"], "unit": r["unit"], "note": r["context_note"]}
        for r in conn.execute(
            "SELECT signal_type, value, unit, context_note FROM sentiment_signals WHERE symbol='PANW'"
        ).fetchall()
    }

    peers_fin = conn.execute(
        "SELECT symbol, fiscal_period, revenue_total_m, revenue_yoy_growth_pct, operating_margin_nongaap_pct, fcf_m FROM quarterly_financials WHERE company_type='peer' ORDER BY symbol"
    ).fetchall()

    peer_kpis = {}
    for r in conn.execute(
        "SELECT symbol, kpi_name, kpi_value FROM company_kpis WHERE company_type='peer'"
    ).fetchall():
        peer_kpis.setdefault(r["symbol"], {})[r["kpi_name"]] = r["kpi_value"]

    # Prior-year for YoY bps
    py = conn.execute(
        "SELECT gross_margin_gaap_pct, gross_margin_nongaap_pct, operating_margin_gaap_pct, operating_margin_nongaap_pct FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q3_FY25'"
    ).fetchone()

    conn.close()
    return fin, kpis, guidance, eps_hist, qa, insiders, sentiment, peers_fin, peer_kpis, py


# ── Formatting helpers ────────────────────────────────────────────────────────
TXN_CODE = {
    "P": "Open-market purchase",
    "S": "Open-market sale",
    "A": "Award (grant/vesting)",
    "F": "Tax withholding",
    "M": "Option exercise",
    "D": "Disposition to issuer",
    "G": "Gift",
}


def first_sentence(text, max_len=180):
    """Return first sentence of text, capped at max_len chars."""
    if not text:
        return ""
    # Split on sentence-ending punctuation followed by space + capital letter or end
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip(), maxsplit=1)
    s = parts[0].strip()
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def fmt_m(v):
    return f"${v:,.0f}M" if v is not None else "—"


def fmt_b(v, decimals=2):
    return f"${v:.{decimals}f}B" if v is not None else "—"


def fmt_pct(v, decimals=1, with_sign=False):
    if v is None:
        return "—"
    return f"{v:+.{decimals}f}%" if with_sign else f"{v:.{decimals}f}%"


def bps(curr, prior):
    if curr is None or prior is None:
        return None
    return round((curr - prior) * 100)


# ── Section builders ──────────────────────────────────────────────────────────
def build_summary(fin, kpis):
    """One-line summary at the very top."""
    text_lines = [
        "PANW Q3 FY26 — THE PRINT AT A GLANCE",
        f"Reported: June 2, 2026 (fiscal quarter ending April 30, 2026)",
        "",
        f"Revenue: ${fin['revenue_total_m']:,.0f}M ({fin['revenue_yoy_growth_pct']:+.1f}% YoY)",
        f"Non-GAAP EPS: ${fin['eps_nongaap']} (vs ${0.800:.3f} consensus, {kpis['eps_nongaap_beat_pct']:+.2f}% beat)",
        f"Revenue beat: {kpis['revenue_beat_pct']:+.2f}% vs consensus",
        f"After-hours reaction: {kpis['stock_ah_change_pct']:+.2f}%",
        f"Close Jun 2: ${kpis['stock_close_day_of']:.2f} → Open Jun 3: ${kpis['stock_open_next_day']:.2f}",
    ]
    return text_lines


def build_income(fin, py):
    text = [
        "PANW Q3 FY26 INCOME STATEMENT",
        "",
        f"Revenue: ${fin['revenue_total_m']:,.0f}M ({fin['revenue_yoy_growth_pct']:+.1f}% YoY)",
        f"  Product revenue: ${fin['revenue_product_m']:,.0f}M",
        f"  Subscription & Support: ${fin['revenue_subscription_m']:,.0f}M",
        "",
        f"Gross profit: ${fin['gross_profit_m']:,.0f}M",
        f"  GAAP gross margin: {fin['gross_margin_gaap_pct']}% ({bps(fin['gross_margin_gaap_pct'], py['gross_margin_gaap_pct']):+d}bps YoY)",
        f"  Non-GAAP gross margin: {fin['gross_margin_nongaap_pct']}% ({bps(fin['gross_margin_nongaap_pct'], py['gross_margin_nongaap_pct']):+d}bps YoY)",
        "",
        f"Operating income (GAAP): ${fin['operating_income_gaap_m']:,.0f}M ({fin['operating_margin_gaap_pct']}% margin, {bps(fin['operating_margin_gaap_pct'], py['operating_margin_gaap_pct']):+d}bps YoY)",
        f"Operating income (Non-GAAP): ${fin['operating_income_nongaap_m']:,.0f}M ({fin['operating_margin_nongaap_pct']}% margin, {bps(fin['operating_margin_nongaap_pct'], py['operating_margin_nongaap_pct']):+d}bps YoY)",
        "",
        f"Net income (GAAP): ${fin['net_income_gaap_m']:,.0f}M",
        f"EPS (GAAP): ${fin['eps_gaap']}",
        f"EPS (Non-GAAP): ${fin['eps_nongaap']}",
        "",
        f"Free cash flow: ${fin['fcf_m']:,.0f}M",
        f"Deferred revenue (total): ${fin['deferred_revenue_total_bn']}B",
    ]
    return text


def build_beat_miss(fin, kpis, eps_hist):
    eps_actual = fin["eps_nongaap"]
    cons = next((e["eps_nongaap_estimate"] for e in eps_hist if e["fiscal_date_ending"] == "2026-04-30"), None)
    rev_actual = fin["revenue_total_m"]
    rev_consensus = round(rev_actual / (1 + kpis["revenue_beat_pct"] / 100), 0)
    text = [
        "PANW Q3 FY26 — BEAT / MISS VS. CONSENSUS",
        "",
        f"Revenue actual: ${rev_actual:,.0f}M",
        f"Revenue consensus: ${rev_consensus:,.0f}M",
        f"Revenue beat: +${rev_actual - rev_consensus:,.0f}M ({kpis['revenue_beat_pct']:+.2f}%)",
        "",
        f"EPS Non-GAAP actual: ${eps_actual}",
        f"EPS Non-GAAP consensus: ${cons:.3f}" if cons else "EPS Non-GAAP consensus: n/a",
        f"EPS beat: +${round(eps_actual - cons, 3):.3f} ({kpis['eps_nongaap_beat_pct']:+.2f}%)" if cons else "",
    ]
    return [t for t in text if t != ""] if len(text) < 5 else text


def build_platform(kpis):
    # Organic NGS ARR growth is documented in the Q3 transcript (ex-CyberArk/Chronosphere = 28%)
    text = [
        "PANW Q3 FY26 — PLATFORM KPIs",
        "",
        f"NGS ARR: ${kpis['ngs_arr_bn']}B ({kpis['ngs_arr_yoy_growth_pct']:+.1f}% YoY reported)",
        f"  Organic NGS ARR growth: +28% YoY (ex-CyberArk and Chronosphere acquisitions; disclosed in Q3 prepared remarks)",
        "",
        f"Platformized customers: {int(kpis['platformized_customers']):,}",
        "",
        f"RPO (Remaining Performance Obligation): ${kpis['rpo_bn']}B ({kpis['rpo_yoy_growth_pct']:+.1f}% YoY)",
        f"  Organic RPO growth: ~+22% YoY (ex-acquisitions)",
        "",
        f"Free cash flow margin (Q3): {kpis['fcf_margin_pct']}%",
    ]
    return text


def build_guidance(guidance):
    METRIC_LABEL = {
        "revenue_m":       "Revenue",
        "eps_nongaap":     "Non-GAAP EPS",
        "ngs_arr_bn":      "NGS ARR",
        "fcf_margin_pct":  "Free cash flow margin",
        "oi_margin_nongaap_pct": "Non-GAAP OI margin",
    }
    PERIOD_LABEL = {"Q4_FY26": "Q4 FY26", "FY26_Full": "FY26 full year"}

    rows = []
    for g in guidance:
        period = PERIOD_LABEL.get(g["issued_for_period"], g["issued_for_period"].replace("_", " "))
        metric = METRIC_LABEL.get(g["metric"], g["metric"])
        rng = (
            f"${g['low_value']:.2f}–${g['high_value']:.2f}"
            if g["unit"] == "$"
            else f"${g['low_value']:,.0f}M–${g['high_value']:,.0f}M"
            if g["unit"] == "m"
            else f"${g['low_value']}B–${g['high_value']}B"
            if g["unit"] == "bn"
            else f"{g['low_value']}–{g['high_value']}%"
            if g["unit"] == "pct"
            else f"{g['low_value']}–{g['high_value']} {g['unit']}"
        )
        rev = f" ({g['revision_vs_prior']})" if g["revision_vs_prior"] else ""
        rows.append((period, metric, rng, rev))

    text = ["PANW Q3 FY26 — GUIDANCE", ""]
    last_period = None
    for period, metric, rng, rev in rows:
        if period != last_period:
            if last_period is not None:
                text.append("")
            text.append(f"-- {period} --")
            last_period = period
        text.append(f"  {metric}: {rng}{rev}")
    return text


def build_eps_history(eps_hist):
    text = ["PANW — EPS SURPRISE HISTORY (last 5 reported quarters)", ""]
    for e in eps_hist:
        marker = "  ← Q3 FY26 (this quarter)" if e["fiscal_date_ending"] == "2026-04-30" else ""
        text.append(
            f"{e['fiscal_date_ending']}: actual ${e['eps_nongaap_actual']:.2f} / est ${e['eps_nongaap_estimate']:.3f} / beat {e['eps_surprise_pct']:+.2f}%{marker}"
        )
    return text


def build_qa(qa):
    text = ["PANW Q3 FY26 — EARNINGS CALL Q&A (9 exchanges)", ""]
    for ex in qa:
        topics_raw = json.loads(ex["topics"]) if ex["topics"] else []
        topics = ", ".join(topics_raw[:5])
        first = first_sentence(ex["answer_text"], max_len=200)
        text.append(f"[{ex['exchange_num']}] {ex['analyst_name']} ({ex['analyst_firm']})")
        text.append(f"    Topics: {topics}")
        text.append(f"    Management ({ex['respondent']}): {first}")
        text.append("")
    return text


def build_insiders(insiders):
    text = ["PANW — INSIDER FORM 4 TRANSACTIONS (Feb 1 – Jun 2, 2026 window)", ""]
    text.append("Transaction codes: P = open-market purchase | S = open-market sale | A = award/grant | F = tax withholding | M = option exercise")
    text.append("")
    for ins in insiders:
        code = ins["transaction_code"]
        label = TXN_CODE.get(code, f"Code {code}")
        price = f"${ins['price_per_share']:.2f}" if ins["price_per_share"] not in (None, 0) else "n/a"
        value = f"${ins['total_value_m']:.4f}M" if ins["total_value_m"] is not None else "n/a"
        plan = " (10b5-1)" if ins["is_10b5_1_plan"] else ""
        role = ins["insider_role"] or ""
        text.append(
            f"{ins['filing_date']} | {ins['insider_name']}{f' ({role})' if role else ''} | {label} | {ins['shares']:,} shares @ {price} = {value}{plan}"
        )
    return text


def build_sentiment(sentiment):
    """Build sentiment section — pull facts only, stop scanning a note after the first matching block."""

    def first_matches(note, prefixes):
        """Return the first occurrence of each prefix in the note (top-down)."""
        seen = set()
        out = []
        for line in (note or "").splitlines():
            s = line.strip()
            for p in prefixes:
                if p in seen:
                    continue
                if s.startswith(p):
                    out.append(s)
                    seen.add(p)
                    break
            if len(seen) == len(prefixes):
                break
        return out

    text = ["PANW — SENTIMENT & POSITIONING", ""]
    if "short_interest" in sentiment:
        si = sentiment["short_interest"]
        text.append(f"Short interest: {si['value']}% of float (MarketBeat, most recent settlement before Q3 print)")
        for s in first_matches(si["note"], ["Shares short:", "Days to cover:", "Change vs prior:"]):
            text.append(f"  {s}")
    if "put_call_ratio" in sentiment:
        pc = sentiment["put_call_ratio"]
        text.append("")
        text.append(f"Put/Call volume ratio: {pc['value']} (Barchart, Jun 3 intraday post-earnings)")
        for s in first_matches(pc["note"], ["Put/Call OI Ratio:", "Implied Volatility:", "IV Rank:"]):
            text.append(f"  {s}")
    return text


def build_peers(peers_fin, peer_kpis):
    text = ["PANW PEERS — MOST RECENT REPORTED QUARTER", ""]
    for p in peers_fin:
        sym = p["symbol"]
        text.append(f"-- {sym} ({p['fiscal_period'].replace('_', ' ')}) --")
        text.append(f"  Revenue: ${p['revenue_total_m']:,.1f}M ({p['revenue_yoy_growth_pct']:+.1f}% YoY)")
        text.append(f"  Non-GAAP OI margin: {p['operating_margin_nongaap_pct']}%")
        if p["fcf_m"] is not None:
            text.append(f"  Free cash flow: ${p['fcf_m']:,.1f}M")
        kp = peer_kpis.get(sym, {})
        if "ending_arr_bn" in kp:
            text.append(f"  Ending ARR: ${kp['ending_arr_bn']}B ({kp.get('ending_arr_yoy_growth_pct', '—')}% YoY)")
        if "net_new_arr_m" in kp:
            text.append(f"  Net new ARR: ${kp['net_new_arr_m']:,.1f}M")
        if "net_retention_rate_pct" in kp:
            text.append(f"  Net retention rate: {kp['net_retention_rate_pct']}%")
        if "rpo_bn" in kp:
            text.append(f"  RPO: ${kp['rpo_bn']}B")
        if "market_cap_bn" in kp:
            text.append(f"  Market cap: ${kp['market_cap_bn']}B")
        if "billings_m" in kp:
            text.append(f"  Billings: ${kp['billings_m']:,.0f}M")
        text.append("")
    return text


def build_market(kpis, fin):
    mkt_cap = round(kpis["stock_close_day_of"] * kpis["shares_diluted_m"] / 1000, 1)
    text = [
        "PANW Q3 FY26 — MARKET DATA",
        "",
        f"Stock close Jun 2, 2026: ${kpis['stock_close_day_of']:.2f}",
        f"Stock open Jun 3, 2026: ${kpis['stock_open_next_day']:.2f}",
        f"After-hours reaction: {kpis['stock_ah_change_pct']:+.2f}%",
        f"Diluted share count: {int(kpis['shares_diluted_m']):,}M",
        f"Market capitalisation (Jun 2 close): ~${mkt_cap}B",
    ]
    return text


def build_glossary():
    terms = [
        ("NGS ARR", "Next-Generation Security Annual Recurring Revenue — PANW's headline platform-revenue metric covering cloud/SASE/AI security subscriptions. Reported and (when disclosed) organic figures both matter."),
        ("RPO", "Remaining Performance Obligation — contracted revenue not yet recognised. Forward revenue visibility."),
        ("Platformized customer", "PANW's term for a customer using multiple platform pillars (Network/Cloud/SecOps) together. Counts the consolidation flywheel."),
        ("Non-GAAP", "Generally Accepted Accounting Principles adjusted for stock-based compensation, acquisition amortisation, and other one-time items. Most equity research and management commentary uses Non-GAAP."),
        ("GAAP", "Strict accounting standard. Includes all expenses including SBC. Often lower than Non-GAAP for high-growth software companies."),
        ("FCF margin", "Free cash flow ÷ revenue. PANW's billings concentration makes Q1 FCF margins seasonally highest."),
        ("SASE", "Secure Access Service Edge — cloud-delivered network security combining firewall + VPN + secure web gateway. PANW competes with ZS here."),
        ("XSIAM", "Extended Security Intelligence and Automation Management — PANW's AI-driven security operations product, competes with CRWD Falcon."),
        ("Prisma AIRS", "PANW's AI runtime security product targeting LLM and agentic applications."),
        ("CyberArk", "Privileged access management vendor PANW acquired in 2025. Contributing to reported NGS ARR/RPO growth this quarter."),
        ("Chronosphere", "Observability vendor PANW acquired in 2025. Adds telemetry/data layer to the platform."),
        ("Form 4", "SEC filing required when an insider buys or sells shares. P = open-market purchase (rare/notable), S = open-market sale, A = award/grant."),
        ("10b5-1 plan", "Pre-scheduled trading plan adopted in advance. Removes the inference of opportunistic timing on insider sales."),
        ("Net new ARR", "Sequential increase in ARR for the quarter. Velocity metric — how much new business booked, net of churn."),
        ("Net retention rate (NRR)", "Existing-customer revenue trajectory — >100% means existing customers grew their spend net of churn."),
        ("EV/Revenue", "Enterprise Value (market cap + debt - cash) ÷ revenue. SaaS valuation multiple. TTM = trailing twelve months; NTM = next twelve months."),
    ]
    text = ["PANW Q3 FY26 — GLOSSARY (for non-cyber participants)", ""]
    for term, definition in terms:
        text.append(f"{term}: {definition}")
        text.append("")
    return text


# ── HTML rendering ────────────────────────────────────────────────────────────
SECTIONS_META = [
    ("summary",    "The print at a glance",   build_summary),
    ("market",     "Market data",              build_market),
    ("beat-miss",  "Beat / miss vs consensus", build_beat_miss),
    ("income",     "Income statement",         build_income),
    ("platform",   "Platform KPIs",            build_platform),
    ("guidance",   "Guidance",                 build_guidance),
    ("eps-history","EPS surprise history",     build_eps_history),
    ("qa",         "Earnings call Q&A",        build_qa),
    ("insiders",   "Insider Form 4",           build_insiders),
    ("sentiment",  "Sentiment & positioning",  build_sentiment),
    ("peers",      "Peer comparison",          build_peers),
    ("glossary",   "Glossary",                 build_glossary),
]


def render():
    fin, kpis, guidance, eps_hist, qa, insiders, sentiment, peers_fin, peer_kpis, py = load()

    # Build sections
    section_data = {}
    args_for = {
        "summary":     (fin, kpis),
        "market":      (kpis, fin),
        "beat-miss":   (fin, kpis, eps_hist),
        "income":      (fin, py),
        "platform":    (kpis,),
        "guidance":    (guidance,),
        "eps-history": (eps_hist,),
        "qa":          (qa,),
        "insiders":    (insiders,),
        "sentiment":   (sentiment,),
        "peers":       (peers_fin, peer_kpis),
        "glossary":    (),
    }
    for sid, title, fn in SECTIONS_META:
        lines = fn(*args_for[sid])
        section_data[sid] = (title, "\n".join(lines))

    # Compose "copy everything" master text
    master_lines = [
        "PANW Q3 FY26 — WORKSHOP REFERENCE",
        "Source: Aileron Group earnings demo. Facts only — no analytical conclusions.",
        f"Generated: {date.today().isoformat()}",
        "",
        "============================================================",
        "",
    ]
    for sid, title, _ in SECTIONS_META:
        master_lines.append(section_data[sid][1])
        master_lines.append("")
        master_lines.append("============================================================")
        master_lines.append("")
    master_text = "\n".join(master_lines)

    # Render section HTML
    section_html = []
    toc_html = []
    for sid, title, _ in SECTIONS_META:
        title_html, body_text = section_data[sid]
        body_html = html.escape(body_text)
        section_html.append(f"""
<section id="{sid}" class="card">
  <header class="card-head">
    <h2>{html.escape(title_html)}</h2>
    <button class="copy-btn" data-copy="{sid}-text" aria-label="Copy {html.escape(title_html)}">Copy</button>
  </header>
  <pre class="card-body" id="{sid}-text">{body_html}</pre>
</section>""")
        toc_html.append(f'<li><a href="#{sid}">{html.escape(title_html)}</a></li>')

    toc = "\n".join(toc_html)
    sections = "\n".join(section_html)

    master_text_html = html.escape(master_text)

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2D2042">
<meta name="description" content="PANW Q3 FY26 earnings facts — workshop reference for Aileron Group's Digital FutureFest 2026 session.">
<title>PANW Q3 FY26 — Workshop Reference</title>
<style>
  :root {{
    --purple: #2D2042;
    --blue: #60B5E5;
    --blue-pale: #B3DCF3;
    --bg: #F7F8FA;
    --card: #FFFFFF;
    --text: #1A1A1F;
    --muted: #6B6B7C;
    --border: #E3E5EB;
    --green: #1F8B4C;
    --green-pale: #E6F5EC;
  }}
  * {{ box-sizing: border-box; }}
  html {{ -webkit-text-size-adjust: 100%; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 16px; line-height: 1.55; color: var(--text);
    background: var(--bg);
    padding: 0; padding-bottom: env(safe-area-inset-bottom);
  }}
  .topbar {{
    position: sticky; top: 0; z-index: 10;
    background: var(--purple); color: #fff;
    padding: 14px 16px 12px; padding-top: max(14px, env(safe-area-inset-top));
    border-bottom: 3px solid var(--blue);
  }}
  .topbar h1 {{ margin: 0 0 2px; font-size: 17px; font-weight: 700; letter-spacing: -.01em; }}
  .topbar .sub {{ font-size: 12px; opacity: .8; margin-bottom: 10px; }}
  .copy-all {{
    display: block; width: 100%;
    background: var(--blue); color: var(--purple);
    border: 0; border-radius: 8px;
    padding: 13px 16px;
    font-size: 15px; font-weight: 700;
    letter-spacing: .01em;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }}
  .copy-all.copied {{ background: var(--green); color: #fff; }}
  .copy-all:active {{ transform: translateY(1px); }}

  .container {{ max-width: 720px; margin: 0 auto; padding: 16px 14px 32px; }}

  .toc {{
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    padding: 12px 14px; margin-bottom: 14px;
  }}
  .toc-title {{
    font-size: 11px; text-transform: uppercase; letter-spacing: .08em;
    color: var(--muted); font-weight: 700; margin-bottom: 8px;
  }}
  .toc ul {{ list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 14px; }}
  .toc li {{ break-inside: avoid; margin-bottom: 4px; }}
  .toc a {{ color: var(--purple); text-decoration: none; font-size: 14px; }}
  .toc a:active {{ color: var(--blue); }}

  .card {{
    background: var(--card); border: 1px solid var(--border); border-radius: 10px;
    margin-bottom: 14px; overflow: hidden;
  }}
  .card-head {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 10px; padding: 12px 14px;
    background: linear-gradient(to bottom, #FBFBFD, #F4F5F8);
    border-bottom: 1px solid var(--border);
  }}
  .card-head h2 {{ margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -.005em; }}
  .copy-btn {{
    flex-shrink: 0;
    background: var(--purple); color: #fff;
    border: 0; border-radius: 6px;
    padding: 8px 14px; min-height: 36px; min-width: 64px;
    font-size: 13px; font-weight: 600;
    cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }}
  .copy-btn.copied {{ background: var(--green); }}
  .copy-btn:active {{ transform: translateY(1px); }}

  .card-body {{
    margin: 0; padding: 14px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 12.5px; line-height: 1.6;
    white-space: pre-wrap; word-wrap: break-word;
    color: var(--text);
  }}

  .footer {{
    padding: 22px 16px 28px; text-align: center;
    font-size: 12px; color: var(--muted);
  }}
  .footer strong {{ color: var(--purple); }}

  .toast {{
    position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
    background: var(--purple); color: #fff;
    padding: 10px 18px; border-radius: 22px;
    font-size: 13px; font-weight: 600;
    opacity: 0; pointer-events: none;
    transition: opacity .18s ease, transform .18s ease;
    z-index: 20;
  }}
  .toast.show {{ opacity: 1; transform: translateX(-50%) translateY(-4px); }}

  @media (min-width: 600px) {{
    .topbar h1 {{ font-size: 19px; }}
    .card-head h2 {{ font-size: 16px; }}
    .card-body {{ font-size: 13px; }}
  }}
</style>
</head>
<body>

<div class="topbar">
  <h1>PANW Q3 FY26 — Workshop Reference</h1>
  <div class="sub">Facts only. Aileron Group · Digital FutureFest · Jun 4, 2026</div>
  <button class="copy-all" id="copyAll" aria-label="Copy entire page">Copy everything</button>
</div>

<main class="container">

<nav class="toc" aria-label="Table of contents">
  <div class="toc-title">Jump to</div>
  <ul>
{toc}
  </ul>
</nav>

{sections}

<div class="footer">
  <strong>Use this on your phone.</strong> Tap a section's <em>Copy</em> button to grab those facts, then paste into your LLM. The whole page is also available via <em>Copy everything</em> at the top.<br><br>
  No rating, no price target, no investment view here — those are yours to form.<br><br>
  Source: Aileron Group earnings demo · Q3 FY26 PANW print (Jun 2, 2026)
</div>

</main>

<div class="toast" id="toast" role="status" aria-live="polite">Copied</div>

<pre id="masterText" hidden>{master_text_html}</pre>

<script>
(function() {{
  const toast = document.getElementById('toast');
  let toastTimer;
  function showToast(msg) {{
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 1400);
  }}

  async function copyText(text) {{
    try {{
      await navigator.clipboard.writeText(text);
      return true;
    }} catch (e) {{
      // Fallback for older browsers / non-secure contexts
      const ta = document.createElement('textarea');
      ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    }}
  }}

  document.querySelectorAll('.copy-btn').forEach(btn => {{
    btn.addEventListener('click', async () => {{
      const target = document.getElementById(btn.dataset.copy);
      const text = target.textContent.trim();
      const ok = await copyText(text);
      if (ok) {{
        btn.classList.add('copied');
        const orig = btn.textContent;
        btn.textContent = 'Copied';
        showToast('Section copied');
        setTimeout(() => {{
          btn.classList.remove('copied');
          btn.textContent = orig;
        }}, 1400);
      }} else {{
        showToast('Copy failed — long-press to copy');
      }}
    }});
  }});

  const copyAllBtn = document.getElementById('copyAll');
  copyAllBtn.addEventListener('click', async () => {{
    const text = document.getElementById('masterText').textContent.trim();
    const ok = await copyText(text);
    if (ok) {{
      copyAllBtn.classList.add('copied');
      copyAllBtn.textContent = 'Copied everything ✓';
      showToast('Everything copied');
      setTimeout(() => {{
        copyAllBtn.classList.remove('copied');
        copyAllBtn.textContent = 'Copy everything';
      }}, 1800);
    }} else {{
      showToast('Copy failed — long-press the page text');
    }}
  }});
}})();
</script>

</body>
</html>
"""
    OUT.write_text(page)
    size_kb = OUT.stat().st_size / 1024
    print(f"  Wrote {OUT}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Sections: {len(SECTIONS_META)}")


if __name__ == "__main__":
    render()
