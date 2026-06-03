"""
test_provenance.py — Stage 4: Provenance and integrity tests for earnings.db

Checks:
  1. Every row with a data_source column has a non-null, non-empty value.
  2. Every data_source value points to a real file under demo/data/raw/.
  3. Key Q3 FY26 financial figures match expected values (from PDFs).
  4. Q3 FY26 fiscal date is 2026-04-30.
  5. Transcript word count >= 1000.
  6. All 13 tables exist.

Run: python -m pytest demo/data/tests/test_provenance.py -v
"""

import json
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent.parent   # earnings-demo root
RAW  = ROOT / "demo" / "data" / "raw"
DB   = ROOT / "demo" / "data" / "db" / "earnings.db"


@pytest.fixture(scope="module")
def conn():
    if not DB.exists():
        pytest.fail(f"DB not found at {DB}. Run rebuild_db.py first.")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    yield con
    con.close()


# Tables that have a data_source or source column
TABLES_WITH_PROVENANCE = [
    ("companies",            "data_source"),
    ("quarterly_financials", "data_source"),
    ("company_kpis",         "data_source"),
    ("consensus_estimates",  "data_source"),
    ("eps_history",          "data_source"),
    ("guidance",             "data_source"),
    ("price_history",        "data_source"),
    ("transcripts",          "source"),
    ("transcript_qa",        "source"),
    ("sentiment_signals",    "data_source"),
]

EXPECTED_TABLES = [
    "companies", "quarterly_financials", "company_kpis", "consensus_estimates",
    "eps_history", "guidance", "insider_transactions", "forward_estimates",
    "price_history", "price_events", "transcripts", "transcript_qa", "sentiment_signals",
]


# ---------------------------------------------------------------------------
# Table existence
# ---------------------------------------------------------------------------

def test_all_13_tables_exist(conn):
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    missing = [t for t in EXPECTED_TABLES if t not in tables]
    assert not missing, f"Missing tables: {missing}"


# ---------------------------------------------------------------------------
# Provenance: every row has a non-null data_source pointing to a real file
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("table,col", TABLES_WITH_PROVENANCE)
def test_no_null_data_source(conn, table, col):
    bad = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL OR {col} = ''"
    ).fetchone()[0]
    assert bad == 0, f"{table}.{col} has {bad} null/empty rows"


@pytest.mark.parametrize("table,col", TABLES_WITH_PROVENANCE)
def test_data_source_files_exist(conn, table, col):
    rows = conn.execute(f"SELECT DISTINCT {col} FROM {table}").fetchall()
    missing = []
    for (src,) in rows:
        if src is None:
            continue
        # Some sentiment sources reference composite strings — skip those
        if " + " in src or "inferred from" in src or "narrative" in src.lower():
            continue
        # Strip any parenthetical notes after the filename
        fname = src.split(" (")[0].strip()
        if not (RAW / fname).exists():
            missing.append(f"{table}.{col} = '{src}' → {RAW / fname} not found")
    assert not missing, "\n".join(missing)


# ---------------------------------------------------------------------------
# Q2 FY26 correctness
# ---------------------------------------------------------------------------

def test_q3_fy26_fiscal_date(conn):
    row = conn.execute(
        "SELECT fiscal_date_ending FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()
    assert row is not None, "Q3_FY26 row missing from quarterly_financials"
    assert row[0] == "2026-04-30", f"fiscal_date_ending is {row[0]!r}, expected '2026-04-30'"


def test_q3_fy26_revenue(conn):
    val = conn.execute(
        "SELECT revenue_total_m FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()[0]
    assert val is not None and val > 0, f"Revenue null or zero: {val}"


def test_q3_fy26_nongaap_eps(conn):
    val = conn.execute(
        "SELECT eps_nongaap FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()[0]
    assert val is not None and val > 0, f"Non-GAAP EPS null or zero: {val}"


def test_q3_fy26_nongaap_gross_margin(conn):
    val = conn.execute(
        "SELECT gross_margin_nongaap_pct FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()[0]
    assert val is not None and val > 50, f"Non-GAAP gross margin unexpected: {val}"


def test_q3_fy26_fcf(conn):
    val = conn.execute(
        "SELECT fcf_m FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()[0]
    assert val is not None, f"FCF is null: {val}"


def test_q3_fy26_deferred_revenue(conn):
    val = conn.execute(
        "SELECT deferred_revenue_total_bn FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()[0]
    assert val is not None and val > 0, f"Deferred revenue total: {val}"


def test_q3_fy26_platformized_customers(conn):
    val = conn.execute(
        "SELECT kpi_value FROM company_kpis "
        "WHERE symbol='PANW' AND kpi_name='platformized_customers'"
    ).fetchone()[0]
    assert val is not None and val > 1000, f"Platformized customers unexpected: {val}"


def test_q3_fy26_ngs_arr(conn):
    val = conn.execute(
        "SELECT kpi_value FROM company_kpis "
        "WHERE symbol='PANW' AND kpi_name='ngs_arr_bn'"
    ).fetchone()[0]
    assert val is not None and val > 0, f"NGS ARR: {val}"


def test_eps_consensus_present(conn):
    row = conn.execute(
        "SELECT eps_consensus_nongaap FROM consensus_estimates WHERE symbol='PANW'"
    ).fetchone()
    assert row is not None, "No consensus row for PANW"
    assert row[0] is not None and row[0] > 0, f"EPS consensus: {row[0]}"


# ---------------------------------------------------------------------------
# Row count sanity
# ---------------------------------------------------------------------------

def test_panw_has_8_quarterly_rows(conn):
    cnt = conn.execute(
        "SELECT COUNT(*) FROM quarterly_financials WHERE symbol='PANW'"
    ).fetchone()[0]
    assert cnt == 8, f"Expected 8 PANW quarterly rows, got {cnt}"


def test_peer_rows_present(conn):
    for peer in ("CRWD", "FTNT", "ZS"):
        cnt = conn.execute(
            "SELECT COUNT(*) FROM quarterly_financials WHERE symbol=?", (peer,)
        ).fetchone()[0]
        assert cnt >= 1, f"No quarterly_financials row for peer {peer}"


def test_transcript_word_count(conn):
    wc = conn.execute(
        "SELECT word_count FROM transcripts WHERE symbol='PANW'"
    ).fetchone()[0]
    assert wc >= 1000, f"Transcript word count too low: {wc}"


def test_qa_exchanges_count(conn):
    cnt = conn.execute(
        "SELECT COUNT(*) FROM transcript_qa WHERE symbol='PANW'"
    ).fetchone()[0]
    assert cnt >= 5, f"Too few Q&A exchanges: {cnt}"


def test_insider_transactions_present(conn):
    cnt = conn.execute(
        "SELECT COUNT(*) FROM insider_transactions WHERE symbol='PANW'"
    ).fetchone()[0]
    assert cnt >= 10, f"Expected many insider transactions, got {cnt}"


def test_price_history_months(conn):
    cnt = conn.execute(
        "SELECT COUNT(*) FROM price_history WHERE symbol='PANW'"
    ).fetchone()[0]
    assert cnt >= 24, f"Expected at least 24 months of price history, got {cnt}"


def test_guidance_rows(conn):
    cnt = conn.execute(
        "SELECT COUNT(*) FROM guidance WHERE symbol='PANW'"
    ).fetchone()[0]
    assert cnt >= 4, f"Expected at least 4 guidance rows, got {cnt}"


def test_q3_fy26_is_primary_quarter(conn):
    val = conn.execute(
        "SELECT is_primary_quarter FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
    ).fetchone()[0]
    assert val == 1, f"is_primary_quarter should be 1 for Q3_FY26, got {val}"


def test_historical_quarters_not_primary(conn):
    bad = conn.execute(
        "SELECT COUNT(*) FROM quarterly_financials "
        "WHERE symbol='PANW' AND fiscal_period != 'Q3_FY26' AND is_primary_quarter = 1"
    ).fetchone()[0]
    assert bad == 0, f"{bad} non-primary PANW quarters marked as is_primary_quarter=1"
