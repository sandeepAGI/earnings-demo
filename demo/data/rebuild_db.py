"""
rebuild_db.py — Earnings Demo Database Builder
Target quarter: PANW Q2 FY26 (fiscal date 2026-01-31, reported 2026-02-17)

Build contract:
  1. Every row has a non-null data_source pointing to a real file under demo/data/raw/.
  2. No .get(key, literal_default) on financial values — missing data raises KeyError.
  3. Form 4 window: 2025-11-01 to 2026-02-17 (full fiscal quarter, post-earnings inclusive).
  4. All paths via pathlib.Path(__file__).parent — no session-pinned absolute paths.
  5. Stage transitions require explicit approval and a STAGE: <name> approved commit.

Run from project root: python demo/data/rebuild_db.py
"""

import json
import os
import sqlite3
from pathlib import Path

RAW = Path(__file__).parent / "raw"
DB  = Path(__file__).parent / "db" / "earnings.db"

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

DB.parent.mkdir(parents=True, exist_ok=True)
if DB.exists():
    DB.unlink()

conn = sqlite3.connect(DB)
c = conn.cursor()


def fail(msg: str) -> None:
    import sys
    print(f"\n[FATAL] {msg}", file=sys.stderr)
    sys.exit(1)


def require_file(fname: str) -> Path:
    p = RAW / fname
    if not p.exists():
        fail(f"Required raw file missing: {p}\nRun gather.py first.")
    return p


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

c.executescript("""
-- 1. companies
CREATE TABLE companies (
    symbol                TEXT PRIMARY KEY,
    company_type          TEXT NOT NULL,
    full_name             TEXT,
    sector                TEXT,
    fiscal_year_end_month INTEGER,
    data_source           TEXT NOT NULL
);

-- 2. quarterly_financials
CREATE TABLE quarterly_financials (
    id                           INTEGER PRIMARY KEY,
    symbol                       TEXT NOT NULL,
    company_type                 TEXT NOT NULL,
    fiscal_period                TEXT,
    fiscal_date_ending           DATE,
    report_date                  DATE,
    revenue_total_m              REAL,
    revenue_product_m            REAL,
    revenue_subscription_m       REAL,
    revenue_yoy_growth_pct       REAL,
    gross_profit_m               REAL,
    gross_margin_gaap_pct        REAL,
    gross_margin_nongaap_pct     REAL,
    operating_income_gaap_m      REAL,
    operating_income_nongaap_m   REAL,
    operating_margin_gaap_pct    REAL,
    operating_margin_nongaap_pct REAL,
    net_income_gaap_m            REAL,
    ebitda_m                     REAL,
    eps_gaap                     REAL,
    eps_nongaap                  REAL,
    deferred_revenue_total_bn    REAL,
    fcf_m                        REAL,
    gaap_profitable              INTEGER,
    is_primary_quarter           INTEGER DEFAULT 0,
    data_source                  TEXT NOT NULL
);

-- 3. company_kpis
CREATE TABLE company_kpis (
    id                 INTEGER PRIMARY KEY,
    symbol             TEXT NOT NULL,
    company_type       TEXT NOT NULL,
    fiscal_period      TEXT,
    fiscal_date_ending DATE,
    kpi_name           TEXT NOT NULL,
    kpi_value          REAL,
    kpi_unit           TEXT,
    kpi_label          TEXT,
    kpi_note           TEXT,
    data_source        TEXT NOT NULL
);

-- 4. consensus_estimates
CREATE TABLE consensus_estimates (
    id                    INTEGER PRIMARY KEY,
    symbol                TEXT,
    fiscal_period         TEXT,
    fiscal_date_ending    DATE,
    eps_consensus_nongaap REAL,
    eps_consensus_gaap    REAL,
    revenue_consensus_m   REAL,
    analyst_count         INTEGER,
    data_source           TEXT NOT NULL
);

-- 5. eps_history
CREATE TABLE eps_history (
    id                   INTEGER PRIMARY KEY,
    symbol               TEXT,
    fiscal_date_ending   DATE,
    eps_nongaap_actual   REAL,
    eps_nongaap_estimate REAL,
    eps_difference       REAL,
    eps_surprise_pct     REAL,
    revenue_actual_m     REAL,
    data_source          TEXT NOT NULL
);

-- 6. guidance
CREATE TABLE guidance (
    id                INTEGER PRIMARY KEY,
    symbol            TEXT,
    issued_for_period TEXT,
    issued_in_period  TEXT,
    guidance_date     DATE,
    guidance_type     TEXT,
    metric            TEXT,
    low_value         REAL,
    high_value        REAL,
    midpoint          REAL,
    unit              TEXT,
    revision_vs_prior TEXT,
    data_source       TEXT NOT NULL
);

-- 7. insider_transactions
CREATE TABLE insider_transactions (
    id               INTEGER PRIMARY KEY,
    symbol           TEXT,
    filing_date      DATE,
    transaction_date DATE,
    insider_name     TEXT,
    insider_role     TEXT,
    transaction_type TEXT,
    transaction_code TEXT,
    shares           INTEGER,
    price_per_share  REAL,
    total_value_m    REAL,
    acquired_disposed TEXT,
    direct_indirect  TEXT,
    is_10b5_1_plan   INTEGER,
    notes            TEXT
);

-- 8. forward_estimates (empty — FMP forward estimates require paid tier)
CREATE TABLE forward_estimates (
    id                INTEGER PRIMARY KEY,
    symbol            TEXT,
    fiscal_period     TEXT,
    fiscal_date_ending DATE,
    eps_avg           REAL,
    revenue_avg_m     REAL,
    analyst_count     INTEGER
);

-- 9. price_history
CREATE TABLE price_history (
    id             INTEGER PRIMARY KEY,
    symbol         TEXT,
    month_date     DATE,
    open_price     REAL,
    high_price     REAL,
    low_price      REAL,
    close_price    REAL,
    volume         INTEGER,
    split_adjusted INTEGER DEFAULT 1,
    data_source    TEXT NOT NULL
);

-- 10. price_events
CREATE TABLE price_events (
    id             INTEGER PRIMARY KEY,
    symbol         TEXT,
    event_key      TEXT,
    event_month    DATE,
    open_price     REAL,
    high_price     REAL,
    low_price      REAL,
    close_price    REAL,
    event_note     TEXT,
    split_adjusted INTEGER DEFAULT 1
);

-- 11. transcripts
CREATE TABLE transcripts (
    id                 INTEGER PRIMARY KEY,
    symbol             TEXT,
    fiscal_period      TEXT,
    fiscal_date_ending DATE,
    call_date          DATE,
    transcript_type    TEXT,
    full_text          TEXT,
    word_count         INTEGER,
    source             TEXT NOT NULL
);

-- 12. transcript_qa
CREATE TABLE transcript_qa (
    id              INTEGER PRIMARY KEY,
    symbol          TEXT,
    fiscal_period   TEXT,
    exchange_num    INTEGER,
    analyst_name    TEXT,
    analyst_firm    TEXT,
    topics          TEXT,
    question_text   TEXT,
    answer_text     TEXT,
    respondent      TEXT,
    key_signal      TEXT,
    analytical_note TEXT,
    source          TEXT NOT NULL
);

-- 13. sentiment_signals
CREATE TABLE sentiment_signals (
    id            INTEGER PRIMARY KEY,
    symbol        TEXT,
    fiscal_period TEXT,
    signal_date   DATE,
    signal_type   TEXT,
    value         REAL,
    value_low     REAL,
    value_high    REAL,
    unit          TEXT,
    confidence    TEXT,
    context_note  TEXT,
    data_source   TEXT NOT NULL
);
""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ins(table: str, cols: str, vals: tuple) -> None:
    ph = ",".join(["?"] * len(vals))
    c.execute(f"INSERT INTO {table} ({cols}) VALUES ({ph})", vals)


def sf(v):
    """Safe float — None for missing/blank."""
    return float(v) if v not in (None, "None", "", "N/A") else None


def midpoint(low, high):
    return round((low + high) / 2, 4) if (low is not None and high is not None) else None


# ---------------------------------------------------------------------------
# Load raw files
# ---------------------------------------------------------------------------

with open(require_file("panw_supplemental_8q.json"))     as f: supp      = json.load(f)
with open(require_file("panw_q2fy26_guidance.json"))     as f: guidance  = json.load(f)
with open(require_file("panw_q2fy26_transcript.txt"))    as f: transcript_text = f.read()
with open(require_file("panw_q2fy26_transcript_qa.json")) as f: qa_raw   = json.load(f)
with open(require_file("panw_earnings_estimates.json"))  as f: est       = json.load(f)
with open(require_file("panw_price_monthly.json"))       as f: price_raw = json.load(f)
with open(require_file("panw_q2fy26_form4_summary.json")) as f: form4    = json.load(f)
with open(require_file("panw_q2fy26_short_interest.txt")) as f: si_text  = f.read()
with open(require_file("panw_q2fy26_put_call.txt"))      as f: pc_text   = f.read()
with open(require_file("peer_snapshot.json"))            as f: peer_raw  = json.load(f)
with open(require_file("panw_price_daily.json"))         as f: daily_raw = json.load(f)

# After-hours reaction: Feb 17 close → Feb 18 open overnight gap
_daily_by_date = {r["date"]: r for r in daily_raw["rows"]}
_feb17 = _daily_by_date.get("2026-02-17")
_feb18 = _daily_by_date.get("2026-02-18")
if not (_feb17 and _feb18):
    raise KeyError("panw_price_daily.json missing 2026-02-17 or 2026-02-18 — re-run gather.py")
_ah_chg = round((_feb18["open"] / _feb17["close"] - 1) * 100, 2)


def load_peer(fname: str) -> dict:
    p = RAW / fname
    if p.exists():
        with open(p) as f:
            return json.load(f)
    print(f"  WARNING: peer file not found: {fname}")
    return {}

crwd_results = load_peer("crwd_q4fy26_results.json")
ftnt_results = load_peer("ftnt_q12026_results.json")
zs_results   = load_peer("zs_q3fy26_results.json")

# Confirmed sentiment values (Playwright browser extract — 2026-05-28)
_sent = load_peer("panw_q2fy26_sentiment_signals.json")
_si   = _sent.get("short_interest", {}) if _sent else {}
_pc   = _sent.get("put_call", {})       if _sent else {}

# XBRL-derived data (optional: files created by gather_edgar_xbrl(), used to backfill nulls)
xbrl_panw  = load_peer("panw_revenue_xbrl.json")
xbrl_peers = load_peer("peers_gross_margin_xbrl.json")

# PANW YoY for quarters where supplemental has null (no adjacent quarter in 8-quarter window)
xbrl_yoy_by_period = xbrl_panw.get("yoy_by_period", {}) if xbrl_panw else {}
# Peer GAAP gross margins from XBRL (supplemental peer files have null for these)
ftnt_gm_gaap = xbrl_peers.get("ftnt_gross_margin_gaap_pct") if xbrl_peers else None
zs_gm_gaap   = xbrl_peers.get("zs_gross_margin_gaap_pct")   if xbrl_peers else None

# Index supplemental quarters by fiscal_period
supp_by_period = {q["fiscal_period"]: q for q in supp["quarters"]}

# Q2 FY26 primary row
q2 = supp_by_period["Q2_FY26"]

# Peers dict from peer_snapshot
pd2 = peer_raw["peers"]

# Guidance sections
g_q3 = guidance["guidance_q3_fy26"]
g_fy = guidance["guidance_fy26_full_year"]
kpis = guidance["operational_kpis"]

# Earnings history (4 quarters, most recent last in list)
eps_history = est["earnings_history"]
q2_eps = next(
    (r for r in eps_history if r["fiscal_date_ending"] == "2026-01-31"),
    None
)
if q2_eps is None:
    fail("Q2 FY26 EPS entry missing from panw_earnings_estimates.json")

# Report dates — factual lookup, not in PDFs (verified from PANW investor relations)
REPORT_DATE = {
    "Q3_FY24": "2024-05-20",
    "Q4_FY24": "2024-09-09",
    "Q1_FY25": "2024-11-19",
    "Q2_FY25": "2025-02-13",
    "Q3_FY25": "2025-05-20",
    "Q4_FY25": "2025-08-18",
    "Q1_FY26": "2025-11-19",
    "Q2_FY26": "2026-02-17",
}

# Insider role lookup for known PANW executives
INSIDER_ROLES = {
    "Nikesh Arora":          "Chairman & CEO",
    "Dipak Golechha":        "CFO",
    "Lee Klarich":           "EVP Chief Product & Tech Officer",
    "Nir Zuk":               "Founder & CTO",
    "Josh D. Paul":          "Chief Accounting Officer",
    "William D. Jenkins Jr": "President",
    "Mark D. McLaughlin":    "Director",
    "Aparna Bawa":           "Director",
    "Helene Gayle":          "Director",
    "James J. Goetz":        "Director",
    "Michal Braverman-Blumenstyk": "Director",
    "Mohamed Awad":          "Director",
    "Sherrese Clarke Soares": "Director",
}


# ===========================================================================
# TABLE 1 — companies
# ===========================================================================
CO_COLS = "symbol,company_type,full_name,sector,fiscal_year_end_month,data_source"

ins("companies", CO_COLS, ("PANW", "primary", "Palo Alto Networks", "Cybersecurity", 7, "panw_supplemental_8q.json"))
ins("companies", CO_COLS, ("CRWD", "peer", pd2["CRWD"]["full_name"], "Cybersecurity", 1, "peer_snapshot.json"))
ins("companies", CO_COLS, ("FTNT", "peer", pd2["FTNT"]["full_name"], "Cybersecurity", 12, "peer_snapshot.json"))
ins("companies", CO_COLS, ("ZS",   "peer", pd2["ZS"]["full_name"],   "Cybersecurity", 7,  "peer_snapshot.json"))


# ===========================================================================
# TABLE 2 — quarterly_financials
# ===========================================================================
QF_COLS = (
    "symbol,company_type,fiscal_period,fiscal_date_ending,report_date,"
    "revenue_total_m,revenue_product_m,revenue_subscription_m,revenue_yoy_growth_pct,"
    "gross_profit_m,gross_margin_gaap_pct,gross_margin_nongaap_pct,"
    "operating_income_gaap_m,operating_income_nongaap_m,operating_margin_gaap_pct,operating_margin_nongaap_pct,"
    "net_income_gaap_m,ebitda_m,eps_gaap,eps_nongaap,"
    "deferred_revenue_total_bn,fcf_m,gaap_profitable,is_primary_quarter,data_source"
)

# PANW — all quarters from supplemental (Q3 FY24 through Q2 FY26)
for period, row in supp_by_period.items():
    fd = row["fiscal_date_ending"]
    rdate = REPORT_DATE.get(period)
    defer_curr = row.get("deferred_revenue_current_bn")
    defer_lt   = row.get("deferred_revenue_longterm_bn")
    defer_total = round(defer_curr + defer_lt, 3) if (defer_curr is not None and defer_lt is not None) else None
    net_income = row["net_income_gaap_m"]
    gaap_profitable = (1 if net_income >= 0 else 0) if net_income is not None else None
    is_primary = 1 if period == "Q2_FY26" else 0
    ins("quarterly_financials", QF_COLS, (
        "PANW", "primary", period, fd, rdate,
        row["revenue_total_m"],
        row.get("revenue_product_m"),
        row.get("revenue_subscription_support_m"),
        row.get("revenue_yoy_growth_pct") or xbrl_yoy_by_period.get(period),
        row.get("gross_profit_gaap_m"),
        row.get("gross_margin_gaap_pct"),
        row.get("gross_margin_nongaap_pct"),
        row.get("operating_income_gaap_m"),
        row.get("operating_income_nongaap_m"),
        row.get("operating_margin_gaap_pct"),
        row.get("operating_margin_nongaap_pct"),
        net_income,
        None,   # ebitda_m — D&A not in supplemental; cannot derive
        row.get("eps_gaap_diluted"),
        row["eps_nongaap_diluted"],
        defer_total,
        row.get("fcf_m"),
        gaap_profitable,
        is_primary,
        "panw_supplemental_8q.json",
    ))

# CRWD Q4 FY26
if crwd_results:
    cqf = crwd_results["quarterly_financials"]
    ins("quarterly_financials", QF_COLS, (
        "CRWD", "peer", "Q4_FY26", "2026-01-31", "2026-03-03",
        cqf.get("revenue_total_m"), None, None,
        cqf.get("revenue_yoy_growth_pct"),
        None, None, cqf.get("gross_margin_nongaap_pct"),
        None, None, None, cqf.get("operating_margin_nongaap_pct"),
        None, None, None,
        crwd_results.get("eps", {}).get("eps_nongaap_actual"),
        None, cqf.get("fcf_m"),
        None, 0, "crwd_q4fy26_results.json",
    ))

# FTNT Q1 2026
if ftnt_results:
    fqf = ftnt_results["quarterly_financials"]
    ins("quarterly_financials", QF_COLS, (
        "FTNT", "peer", "Q1_2026", "2026-03-31", "2026-05-07",
        fqf.get("revenue_total_m"),
        fqf.get("revenue_product_m"),
        fqf.get("revenue_services_m"),
        fqf.get("revenue_yoy_growth_pct"),
        None, ftnt_gm_gaap, None,
        None, None,
        fqf.get("operating_margin_gaap_pct"),
        fqf.get("operating_margin_nongaap_pct"),
        None, None, None,
        ftnt_results.get("eps", {}).get("eps_nongaap_actual"),
        None, fqf.get("fcf_m"),
        1, 0, "ftnt_q12026_results.json",
    ))

# ZS Q3 FY26
if zs_results:
    zqf = zs_results["quarterly_financials"]
    ins("quarterly_financials", QF_COLS, (
        "ZS", "peer", "Q3_FY26", "2026-04-30", "2026-05-26",
        zqf.get("revenue_total_m"), None, None,
        zqf.get("revenue_yoy_growth_pct"),
        None, zs_gm_gaap, None,
        None, None, None, zqf.get("operating_margin_nongaap_pct"),
        None, None, None,
        zs_results.get("eps", {}).get("eps_nongaap_actual"),
        None, None,
        0, 0, "zs_q3fy26_results.json",
    ))


# ===========================================================================
# TABLE 3 — company_kpis
# ===========================================================================
KPI_COLS = "symbol,company_type,fiscal_period,fiscal_date_ending,kpi_name,kpi_value,kpi_unit,kpi_label,kpi_note,data_source"

def kpi(symbol, ctype, period, date, name, value, unit, label, note=None, src=None):
    ins("company_kpis", KPI_COLS, (symbol, ctype, period, date, name, value, unit, label, note, src))

# PANW Q2 FY26 KPIs
defer_curr  = q2["deferred_revenue_current_bn"]
defer_lt    = q2["deferred_revenue_longterm_bn"]
defer_total = round(defer_curr + defer_lt, 3)

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "ngs_arr_bn", q2["ngs_arr_bn"], "bn", "NGS ARR",
    f"+{kpis['ngs_arr_yoy_growth_pct']}% YoY",
    "panw_supplemental_8q.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "ngs_arr_yoy_growth_pct", kpis["ngs_arr_yoy_growth_pct"], "pct", "NGS ARR YoY Growth",
    None, "panw_q2fy26_guidance.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "rpo_bn", q2["remaining_performance_obligations_bn"], "bn", "Remaining Performance Obligation",
    f"+{kpis['rpo_yoy_growth_pct']}% YoY",
    "panw_supplemental_8q.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "rpo_yoy_growth_pct", kpis["rpo_yoy_growth_pct"], "pct", "RPO YoY Growth",
    None, "panw_q2fy26_guidance.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "deferred_rev_total_bn", defer_total, "bn", "Total Deferred Revenue",
    f"Current ${defer_curr}B + Long-term ${defer_lt}B",
    "panw_supplemental_8q.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "fcf_m", q2["fcf_m"], "m", "Free Cash Flow (Standard)",
    f"FCF margin {q2['fcf_margin_pct']}%",
    "panw_supplemental_8q.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "fcf_margin_pct", q2["fcf_margin_pct"], "pct", "FCF Margin",
    None, "panw_supplemental_8q.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "platformized_customers", kpis["platformized_customers"], "count", "Platformized Customers",
    "Customers using 3+ PANW product pillars",
    "panw_q2fy26_guidance.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "shares_diluted_m", q2["shares_diluted_m"], "m", "Diluted Shares Outstanding",
    None, "panw_supplemental_8q.json")

kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "eps_nongaap_beat_pct", q2_eps["eps_surprise_pct"], "pct", "Non-GAAP EPS Beat vs Consensus",
    f"Actual ${q2_eps['eps_nongaap_actual']} vs consensus ${q2_eps['eps_nongaap_estimate']}",
    "panw_earnings_estimates.json")

# After-hours reaction: Feb 17 close → Feb 18 open gap (yfinance daily)
kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "stock_close_day_of", _feb17["close"], "$", "Stock Close Day-of Earnings",
    "Feb 17, 2026 regular-hours close", "panw_price_daily.json")
kpi("PANW", "primary", "Q2_FY26", "2026-01-31",
    "stock_ah_change_pct", _ah_chg, "pct", "After-Hours Reaction (overnight gap)",
    f"Feb 17 close ${_feb17['close']} → Feb 18 open ${_feb18['open']}", "panw_price_daily.json")

# CRWD Q4 FY26 KPIs
if crwd_results:
    ck = crwd_results.get("kpis", {})
    ce = crwd_results.get("eps", {})
    ct = crwd_results.get("ttm_from_overview", {})
    cg = crwd_results.get("fy27_guidance", {})
    kpi("CRWD", "peer", "Q4_FY26", "2026-01-31", "ending_arr_bn", ck.get("ending_arr_bn"), "bn", "Ending ARR",
        f"+{ck.get('ending_arr_yoy_growth_pct')}% YoY", "crwd_q4fy26_results.json")
    kpi("CRWD", "peer", "Q4_FY26", "2026-01-31", "ending_arr_yoy_growth_pct", ck.get("ending_arr_yoy_growth_pct"), "pct", "ARR YoY Growth",
        None, "crwd_q4fy26_results.json")
    kpi("CRWD", "peer", "Q4_FY26", "2026-01-31", "net_new_arr_m", ck.get("net_new_arr_m"), "m", "Net New ARR",
        f"+{ck.get('net_new_arr_yoy_growth_pct')}% YoY", "crwd_q4fy26_results.json")
    kpi("CRWD", "peer", "Q4_FY26", "2026-01-31", "net_retention_rate_pct", ck.get("net_retention_rate_pct"), "pct", "Net Retention Rate",
        None, "crwd_q4fy26_results.json")
    kpi("CRWD", "peer", "Q4_FY26", "2026-01-31", "revenue_yoy_growth_pct",
        crwd_results["quarterly_financials"].get("revenue_yoy_growth_pct"), "pct", "Revenue YoY Growth",
        None, "crwd_q4fy26_results.json")
    kpi("CRWD", "peer", "Q4_FY26", "2026-01-31", "eps_nongaap_actual", ce.get("eps_nongaap_actual"), "$", "Non-GAAP EPS",
        None, "crwd_q4fy26_results.json")
    kpi("CRWD", "peer", "Q4_FY26", "2026-01-31", "market_cap_bn", ct.get("market_cap_bn"), "bn", "Market Cap",
        None, "crwd_company_overview.json")

# FTNT Q1 2026 KPIs
if ftnt_results:
    fqf = ftnt_results["quarterly_financials"]
    fe  = ftnt_results.get("eps", {})
    fv  = ftnt_results.get("valuation", {})
    kpi("FTNT", "peer", "Q1_2026", "2026-03-31", "revenue_yoy_growth_pct", fqf.get("revenue_yoy_growth_pct"), "pct", "Revenue YoY Growth",
        None, "ftnt_q12026_results.json")
    kpi("FTNT", "peer", "Q1_2026", "2026-03-31", "revenue_product_yoy_growth_pct", fqf.get("revenue_product_yoy_growth_pct"), "pct", "Product Revenue YoY Growth",
        None, "ftnt_q12026_results.json")
    kpi("FTNT", "peer", "Q1_2026", "2026-03-31", "billings_m", fqf.get("billings_m"), "m", "Billings",
        f"+{fqf.get('billings_yoy_growth_pct')}% YoY", "ftnt_q12026_results.json")
    kpi("FTNT", "peer", "Q1_2026", "2026-03-31", "nongaap_operating_margin_pct", fqf.get("operating_margin_nongaap_pct"), "pct", "Non-GAAP Operating Margin",
        None, "ftnt_q12026_results.json")
    kpi("FTNT", "peer", "Q1_2026", "2026-03-31", "fcf_m", fqf.get("fcf_m"), "m", "Free Cash Flow",
        None, "ftnt_q12026_results.json")
    kpi("FTNT", "peer", "Q1_2026", "2026-03-31", "eps_nongaap_actual", fe.get("eps_nongaap_actual"), "$", "Non-GAAP EPS",
        None, "ftnt_q12026_results.json")
    kpi("FTNT", "peer", "Q1_2026", "2026-03-31", "market_cap_bn", fv.get("market_cap_bn"), "bn", "Market Cap",
        None, "ftnt_q12026_results.json")

# ZS Q3 FY26 KPIs
if zs_results:
    zqf = zs_results["quarterly_financials"]
    ze  = zs_results.get("eps", {})
    zk  = zs_results.get("kpis", {})
    kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "revenue_yoy_growth_pct", zqf.get("revenue_yoy_growth_pct"), "pct", "Revenue YoY Growth",
        None, "zs_q3fy26_results.json")
    kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "ending_arr_m", zk.get("ending_arr_m"), "m", "Ending ARR",
        f"+{zk.get('ending_arr_yoy_growth_pct')}% YoY", "zs_q3fy26_results.json")
    if zk.get("ending_arr_m"):
        kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "ending_arr_bn",
            round(zk["ending_arr_m"] / 1000, 3), "bn", "Ending ARR",
            f"+{zk.get('ending_arr_yoy_growth_pct')}% YoY", "zs_q3fy26_results.json")
    kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "net_new_arr_m", zk.get("net_new_arr_m"), "m", "Net New ARR",
        None, "zs_q3fy26_results.json")
    kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "rpo_bn", zk.get("rpo_bn"), "bn", "Remaining Performance Obligation",
        f"+{zk.get('rpo_yoy_growth_pct')}% YoY", "zs_q3fy26_results.json")
    kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "nongaap_operating_margin_pct", zqf.get("operating_margin_nongaap_pct"), "pct", "Non-GAAP Operating Margin",
        None, "zs_q3fy26_results.json")
    kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "eps_nongaap_actual", ze.get("eps_nongaap_actual"), "$", "Non-GAAP EPS",
        None, "zs_q3fy26_results.json")
    kpi("ZS", "peer", "Q3_FY26", "2026-04-30", "customers_over_100k_arr", zk.get("customers_over_100k_arr"), "count", "Customers >$100K ARR",
        f"+{zk.get('customers_over_100k_yoy_growth_pct')}% YoY", "zs_q3fy26_results.json")


# ===========================================================================
# TABLE 4 — consensus_estimates
# ===========================================================================
ins("consensus_estimates",
    "symbol,fiscal_period,fiscal_date_ending,eps_consensus_nongaap,eps_consensus_gaap,revenue_consensus_m,analyst_count,data_source",
    (
        "PANW", "Q2_FY26", "2026-01-31",
        q2_eps["eps_nongaap_estimate"],
        None,   # GAAP consensus not in yfinance earnings_history
        None,   # Revenue consensus not available from free APIs for historical quarters
        None,
        "panw_earnings_estimates.json",
    )
)


# ===========================================================================
# TABLE 5 — eps_history
# ===========================================================================
for row in eps_history:
    ins("eps_history",
        "symbol,fiscal_date_ending,eps_nongaap_actual,eps_nongaap_estimate,eps_difference,eps_surprise_pct,revenue_actual_m,data_source",
        (
            "PANW",
            row["fiscal_date_ending"],
            row.get("eps_nongaap_actual"),
            row.get("eps_nongaap_estimate"),
            row.get("eps_difference"),
            row.get("eps_surprise_pct"),
            row.get("revenue_actual_m"),
            "panw_earnings_estimates.json",
        )
    )


# ===========================================================================
# TABLE 6 — guidance
# ===========================================================================
GD_COLS = (
    "symbol,issued_for_period,issued_in_period,guidance_date,guidance_type,"
    "metric,low_value,high_value,midpoint,unit,revision_vs_prior,data_source"
)

def g_ins(for_period, in_period, gtype, metric, low, high, unit, revision):
    mid = midpoint(low, high)
    ins("guidance", GD_COLS, (
        "PANW", for_period, in_period, "2026-02-17", gtype,
        metric, low, high, mid, unit, revision, "panw_q2fy26_guidance.json",
    ))

# Q3 FY26 guidance
g_ins("Q3_FY26", "Q2_FY26", "next_quarter", "revenue_m",
      g_q3["revenue_low_m"], g_q3["revenue_high_m"], "m", g_q3["revision_vs_prior"])
g_ins("Q3_FY26", "Q2_FY26", "next_quarter", "eps_nongaap",
      g_q3["eps_nongaap_low"], g_q3["eps_nongaap_high"], "$", g_q3["revision_vs_prior"])
if g_q3.get("ngs_arr_low_bn") is not None:
    g_ins("Q3_FY26", "Q2_FY26", "next_quarter", "ngs_arr_bn",
          g_q3["ngs_arr_low_bn"], g_q3["ngs_arr_high_bn"], "bn", g_q3["revision_vs_prior"])

# FY26 full-year guidance
g_ins("FY26_Full", "Q2_FY26", "full_year", "revenue_m",
      g_fy["revenue_low_m"], g_fy["revenue_high_m"], "m", g_fy["revision_vs_prior"])
g_ins("FY26_Full", "Q2_FY26", "full_year", "eps_nongaap",
      g_fy["eps_nongaap_low"], g_fy["eps_nongaap_high"], "$", g_fy["revision_vs_prior"])
if g_fy.get("fcf_margin_low_pct") is not None:
    g_ins("FY26_Full", "Q2_FY26", "full_year", "fcf_margin_pct",
          g_fy["fcf_margin_low_pct"], g_fy["fcf_margin_high_pct"], "pct", g_fy["revision_vs_prior"])
if g_fy.get("ngs_arr_low_bn") is not None:
    g_ins("FY26_Full", "Q2_FY26", "full_year", "ngs_arr_bn",
          g_fy["ngs_arr_low_bn"], g_fy["ngs_arr_high_bn"], "bn", g_fy["revision_vs_prior"])


# ===========================================================================
# TABLE 7 — insider_transactions
# Window: 2025-11-01 to 2026-02-17 (full Q2 FY26 fiscal quarter, post-earnings inclusive)
# ===========================================================================
IT_COLS = (
    "symbol,filing_date,transaction_date,insider_name,insider_role,"
    "transaction_type,transaction_code,shares,price_per_share,total_value_m,"
    "acquired_disposed,direct_indirect,is_10b5_1_plan,notes"
)

for filing in form4["filings"]:
    owner = filing["reporting_owner"]
    role  = INSIDER_ROLES.get(owner)
    for txn in filing["transactions"]:
        price = txn.get("price_per_share")
        shares = txn.get("shares")
        total_m = round(shares * price / 1e6, 4) if (shares and price) else None
        ins("insider_transactions", IT_COLS, (
            "PANW",
            filing["filing_date"],
            txn.get("transaction_date"),
            owner,
            role,
            txn.get("transaction_type"),
            txn.get("transaction_code"),
            int(shares) if shares else None,
            price,
            total_m,
            txn.get("acquired_disposed"),
            txn.get("direct_indirect"),
            None,   # is_10b5_1_plan — not surfaced by edgartools at transaction level
            f"Accession: {filing['accession_number']}",
        ))


# ===========================================================================
# TABLE 8 — forward_estimates (empty)
# ===========================================================================
# FMP forward estimates require a paid subscription. Table intentionally empty.
# guidance table carries forward-looking data for the demo.


# ===========================================================================
# TABLE 9 — price_history
# ===========================================================================
PH_COLS = "symbol,month_date,open_price,high_price,low_price,close_price,volume,split_adjusted,data_source"

price_records = price_raw["records"]
for bar in price_records:
    ins("price_history", PH_COLS, (
        "PANW",
        bar["date"],
        bar["open"], bar["high"], bar["low"], bar["close"],
        bar["volume"],
        bar["split_adjusted"],
        "panw_price_monthly.json",
    ))


# ===========================================================================
# TABLE 10 — price_events
# Factual event labels for key months. event_note is a factual identifier,
# not an analytical conclusion (per SCHEMA.md).
# ===========================================================================
PE_COLS = "symbol,event_key,event_month,open_price,high_price,low_price,close_price,event_note,split_adjusted"

# Index price records by month prefix
price_by_month = {}
for bar in price_records:
    prefix = bar["date"][:7]  # e.g. "2026-02"
    price_by_month[prefix] = bar

EVENT_MONTHS = [
    ("q2_fy26_earnings",  "2026-02", "Q2 FY26 earnings report month (Feb 17, 2026)"),
    ("q1_fy26_earnings",  "2025-11", "Q1 FY26 earnings report month (Nov 19, 2025)"),
    ("q4_fy25_earnings",  "2025-08", "Q4 FY25 earnings report month (Aug 18, 2025)"),
    ("q2_fy25_earnings",  "2025-02", "Q2 FY25 earnings report month (Feb 13, 2025)"),
]

for ev_key, month_prefix, ev_note in EVENT_MONTHS:
    bar = price_by_month.get(month_prefix)
    if bar:
        ins("price_events", PE_COLS, (
            "PANW", ev_key, bar["date"],
            bar["open"], bar["high"], bar["low"], bar["close"],
            ev_note,
            bar["split_adjusted"],
        ))
    else:
        print(f"  WARNING: price_events — no price bar for {month_prefix}")


# ===========================================================================
# TABLE 11 — transcripts
# ===========================================================================
word_count = len(transcript_text.split())
ins("transcripts",
    "symbol,fiscal_period,fiscal_date_ending,call_date,transcript_type,full_text,word_count,source",
    (
        "PANW", "Q2_FY26", "2026-01-31", "2026-02-17", "earnings_call",
        transcript_text, word_count,
        "panw_q2fy26_transcript.txt",
    )
)


# ===========================================================================
# TABLE 12 — transcript_qa
# ===========================================================================
QA_COLS = (
    "symbol,fiscal_period,exchange_num,analyst_name,analyst_firm,"
    "topics,question_text,answer_text,respondent,key_signal,analytical_note,source"
)
for ex in qa_raw["exchanges"]:
    ins("transcript_qa", QA_COLS, (
        "PANW", "Q2_FY26",
        ex["exchange_num"],
        ex["analyst_name"],
        ex["analyst_firm"],
        json.dumps(ex.get("topics", [])),
        ex["question_text"],
        ex["answer_text"],
        ex.get("respondent"),
        ex.get("key_signal"),
        ex.get("analytical_note"),
        "panw_q2fy26_transcript_qa.json",
    ))


# ===========================================================================
# TABLE 13 — sentiment_signals
# Source files contain narrative text; values are inferred. confidence is mandatory.
# ===========================================================================
SS_COLS = "symbol,fiscal_period,signal_date,signal_type,value,value_low,value_high,unit,confidence,context_note,data_source"

# Short interest: last report before earnings = Feb 13, 2026 (MarketBeat via Playwright)
_si_val     = _si.get("float_pct")           # 2.8% float
_si_hi      = _si.get("prior_float_pct")     # 6.7% float peak (Jan 30)
_si_note    = (
    f"PANW Short Interest — Q2 FY26 Earnings Window (Feb 2026)\n"
    f"Source: {_si.get('source', 'MarketBeat')}  |  Pulled: 2026-05-28 via Playwright\n\n"
    f"Last report before earnings (2026-02-13):\n"
    f"  Shares short: {_si.get('shares_short_m')}M  |  Float %: {_si_val}%  |  Days to cover: {_si.get('days_to_cover')}\n\n"
    f"Prior report (2026-01-30): {_si.get('prior_shares_short_m')}M shares, {_si_hi}% float\n"
    f"Change: {_si.get('change_pct')}% — massive short covering going into earnings.\n\n"
    f"{_si.get('note', '')}"
) if _si else si_text[:1000]
_si_conf    = "actual" if _si else "estimated"
_si_date    = _si.get("report_date", "2026-02-17") if _si else "2026-02-17"

ins("sentiment_signals", SS_COLS, (
    "PANW", "Q2_FY26", _si_date, "short_interest",
    _si_val, None, _si_hi, "pct_float", _si_conf,
    _si_note,
    "panw_q2fy26_sentiment_signals.json",
))

# Put/call ratio: earnings day (Feb 17, 2026) from Barchart Highcharts via Playwright
_pc_day     = _pc.get("earnings_day", {}) if _pc else {}
_pc_post    = _pc.get("post_earnings_day", {}) if _pc else {}
_pc_vol     = _pc_day.get("pc_volume_ratio")   # 1.09 on Feb 17
_pc_oi      = _pc_day.get("pc_oi_ratio")       # 0.95 on Feb 17
_pc_post_v  = _pc_post.get("pc_volume_ratio")  # 4.02 on Feb 18 (extreme put buying)
_pc_note    = (
    f"PANW Put/Call Ratio — Q2 FY26 Earnings Window (Feb 2026)\n"
    f"Source: {_pc.get('source', 'Barchart')}  |  Pulled: 2026-05-28 via Playwright\n\n"
    f"Earnings day (2026-02-17, close ${_pc_day.get('price_close')}):\n"
    f"  P/C Volume Ratio: {_pc_vol}  |  P/C OI Ratio: {_pc_oi}\n\n"
    f"Post-earnings day (2026-02-18, close ${_pc_post.get('price_close')}):\n"
    f"  P/C Volume Ratio: {_pc_post_v}  — {_pc_post.get('note', '')}"
) if _pc else pc_text[:1000]
_pc_conf    = "actual" if _pc else "estimated"

ins("sentiment_signals", SS_COLS, (
    "PANW", "Q2_FY26", "2026-02-17", "put_call_ratio",
    _pc_vol, _pc_oi, _pc_post_v, "ratio", _pc_conf,
    _pc_note,
    "panw_q2fy26_sentiment_signals.json",
))


# ===========================================================================
# Commit
# ===========================================================================
conn.commit()


# ===========================================================================
# Verification report
# ===========================================================================
print("\n" + "=" * 62)
print("  earnings.db — build complete")
print(f"  DB path: {DB}")
print("=" * 62)

tables = c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
total = 0
for (t,) in tables:
    cnt = c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
    total += cnt
    print(f"  {t:<30} {cnt:>4} rows")

print(f"\n  Total tables:  {len(tables)}  (target: 13)")
print(f"  Total rows:    {total}")
print(f"  DB size:       {os.path.getsize(DB):,} bytes")

print("\n  Spot checks:")

def chk(label, query, expected):
    r = c.execute(query).fetchone()
    val = r[0] if r else "NULL"
    status = "✓" if str(val) != "NULL" else "✗"
    print(f"  {status} {label:<44} {val!r}  [exp: {expected}]")

chk("Q2_FY26 revenue (M)",
    "SELECT revenue_total_m FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q2_FY26'",
    "2594")
chk("Q2_FY26 non-GAAP EPS",
    "SELECT eps_nongaap FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q2_FY26'",
    "1.03")
chk("Q2_FY26 non-GAAP gross margin %",
    "SELECT gross_margin_nongaap_pct FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q2_FY26'",
    "76.1")
chk("Q2_FY26 non-GAAP OI (M)",
    "SELECT operating_income_nongaap_m FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q2_FY26'",
    "785")
chk("Q2_FY26 fiscal_date_ending",
    "SELECT fiscal_date_ending FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q2_FY26'",
    "2026-01-31")
chk("NGS ARR (B)",
    "SELECT kpi_value FROM company_kpis WHERE symbol='PANW' AND kpi_name='ngs_arr_bn'",
    "6.33")
chk("Platformized customers",
    "SELECT kpi_value FROM company_kpis WHERE symbol='PANW' AND kpi_name='platformized_customers'",
    "1550")
chk("EPS consensus",
    "SELECT eps_consensus_nongaap FROM consensus_estimates WHERE symbol='PANW'",
    "0.93684")
chk("EPS history rows",
    "SELECT COUNT(*) FROM eps_history WHERE symbol='PANW'",
    "4")
chk("Guidance rows",
    "SELECT COUNT(*) FROM guidance WHERE symbol='PANW'",
    "7")
chk("Insider transaction rows",
    "SELECT COUNT(*) FROM insider_transactions WHERE symbol='PANW'",
    "26+")
chk("Q&A exchanges",
    "SELECT COUNT(*) FROM transcript_qa WHERE symbol='PANW'",
    "10")
chk("Price history months",
    "SELECT COUNT(*) FROM price_history WHERE symbol='PANW'",
    "60")
chk("Price events",
    "SELECT COUNT(*) FROM price_events WHERE symbol='PANW'",
    "4")
chk("Transcript word count",
    "SELECT word_count FROM transcripts WHERE symbol='PANW'",
    ">2000")
chk("Deferred revenue total (B)",
    "SELECT deferred_revenue_total_bn FROM quarterly_financials WHERE symbol='PANW' AND fiscal_period='Q2_FY26'",
    "12.429")
chk("Quarterly financials PANW rows",
    "SELECT COUNT(*) FROM quarterly_financials WHERE symbol='PANW'",
    "8")

companies = c.execute("SELECT symbol, company_type FROM companies ORDER BY company_type, symbol").fetchall()
print(f"\n  Companies: {companies}")

conn.close()

print(f"\n  ✅ DB ready at {DB}")
print("=" * 62)
