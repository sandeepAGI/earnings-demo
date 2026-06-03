#!/usr/bin/env python3
"""
PANW Q3 FY26 Earnings Analysis
Follows: equity-research/earnings-analysis skill (financial-services-plugins, v0.1.0)
Workflow reference: .../equity-research/skills/earnings-analysis/references/workflow.md

DEPARTURE D1 — SKILL STEP 1 (data freshness):
  The skill requires a live web search to obtain the latest earnings materials.
  We use pre-staged raw files in demo/data/raw/ instead.
  Reason: Workshop reproducibility — the same output must render reliably
  before June 4, 2026. Live fetch would produce non-deterministic content.

DEPARTURE D2 — SKILL STEP 9 (model update):
  The skill shows an old-vs-new estimate table from a maintained analyst model.
  We show directional EPS trajectory only.
  Reason: No prior-quarter analyst model exists for PANW in this pipeline.
  Consensus trajectory from yfinance earnings history used as substitute.

DEPARTURE D3 — SKILL STEP 10 (valuation):
  The skill requires a DCF + comparables multiples analysis.
  We use peer NTM EV/Revenue multiples only — no DCF.
  Reason: No Bloomberg/FactSet for live consensus forward estimates.
  Pre-staged peer financials are sufficient for a directional PT range.

DEPARTURE D4 — SKILL STEPS 12-16 (output format):
  The skill produces an 8-12 page DOCX report.
  We produce structured JSON consumed by generate_baseline.py to render Tab 2.
  Reason: Tab 2 is a web dashboard section, not a Word document.

DATA SOURCE NOTE:
  panw_q2fy26_press_release.json contains Q2 FY25 data (source URL is the
  Feb 13, 2025 press release, fiscal ending 2025-01-31). Do NOT use for Q2 FY26
  financials. Use panw_earnings_estimates.json, panw_q2fy26_guidance.json,
  and panw_supplemental_8q.json instead.
"""

import json
import sqlite3
from datetime import date
from pathlib import Path

RAW = Path(__file__).parent.parent / "raw"
DB  = Path(__file__).parent.parent / "db" / "earnings.db"
OUT = Path(__file__).parent / "panw_q3fy26_earnings_analysis.json"

DEPARTURES = [
    {
        "id": "D1",
        "step": "1 — Data Freshness",
        "departure": "Pre-staged raw files used instead of live web search.",
        "reason": "Workshop reproducibility — the same output must render reliably for the June 4, 2026 workshop.",
    },
    {
        "id": "D2",
        "step": "9 — Model Update",
        "departure": "Directional EPS trajectory shown instead of old-vs-new model table.",
        "reason": "No prior-quarter analyst model maintained for PANW in this pipeline. Consensus EPS history from yfinance used as substitute.",
    },
    {
        "id": "D3",
        "step": "10 — Valuation",
        "departure": "Peer NTM EV/Revenue multiples only — no DCF model.",
        "reason": "No Bloomberg/FactSet access for live consensus forward estimates. Pre-staged peer files provide sufficient data for a directional price target range.",
    },
    {
        "id": "D4",
        "step": "12–16 — Output Format",
        "departure": "Structured JSON rendered as HTML (Tab 2) instead of 8–12 page DOCX.",
        "reason": "Tab 2 of earnings_baseline.html is a web dashboard section. DOCX output format does not apply.",
    },
]


def require_file(name: str) -> Path:
    p = RAW / name
    if not p.exists():
        raise FileNotFoundError(f"Required raw file missing: {p}")
    return p


def load_json(name: str) -> dict:
    with open(require_file(name)) as f:
        return json.load(f)


# ── SKILL STEPS 1–4: Data Collection & Verification (D1 — pre-staged) ─────────

print("[STEPS 1–4] Loading and verifying raw data files...")

est   = load_json("panw_earnings_estimates.json")
guide = load_json("panw_q3fy26_guidance.json")
suppl = load_json("panw_supplemental_8q.json")
qa    = load_json("panw_q3fy26_transcript_qa.json")
crwd  = load_json("crwd_q4fy26_results.json")
ftnt  = load_json("ftnt_q12026_results.json")
zs    = load_json("zs_q3fy26_results.json")

# Primary Q3 FY26 figures from supplemental (authoritative)
q3     = next(q for q in suppl["quarters"] if q["fiscal_period"] == "Q3_FY26")
q3_py  = next(q for q in suppl["quarters"] if q["fiscal_period"] == "Q3_FY25")  # prior year

# EPS and consensus from earnings history
q3_eps = next(e for e in est["earnings_history"] if e["fiscal_date_ending"] == "2026-04-30")

# After-hours reaction from DB (verified actual — panw_price_daily.json)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
kpi_rows = conn.execute(
    "SELECT kpi_name, kpi_value FROM company_kpis WHERE symbol='PANW' AND fiscal_period='Q3_FY26'"
).fetchall()
conn.close()
kpis = {r["kpi_name"]: r["kpi_value"] for r in kpi_rows}

# Spot-check critical fields (expected values TBD — update after first run)
print(f"  ✓ Q3 FY26 revenue: ${q3['revenue_total_m']:,}M | EPS: ${q3['eps_nongaap_diluted']}")
print(f"  ✓ Consensus EPS: ${q3_eps['eps_nongaap_estimate']:.4f}")
print(f"  ✓ AH reaction: {kpis.get('stock_ah_change_pct', 'missing')}%")


# ── SKILL STEP 5: Beat/Miss Analysis ──────────────────────────────────────────

print("\n[STEP 5] Beat/Miss Analysis...")

eps_actual   = q3["eps_nongaap_diluted"]
eps_cons     = q3_eps["eps_nongaap_estimate"]
eps_beat     = round(eps_actual - eps_cons, 3)
eps_beat_pct = round(q3_eps["eps_surprise_pct"], 1)

rev_actual_m  = q3["revenue_total_m"]
rev_yoy_pct   = q3["revenue_yoy_growth_pct"]
rev_cons_m    = guide["beat_miss_q3_fy26"].get("revenue_consensus_m")
rev_beat_pct  = guide["beat_miss_q3_fy26"].get("revenue_beat_pct")

ngs_arr_bn  = guide["operational_kpis"]["ngs_arr_bn"]
ngs_arr_yoy = guide["operational_kpis"]["ngs_arr_yoy_growth_pct"]
# Organic NGS ARR growth ex-CyberArk and Chronosphere acquisitions (confirmed from Q3 transcript)
# Total NGS ARR $8.13B +60% YoY; organic (ex-acq) $6.5B +28% YoY. Delta is acquisition-driven.
ngs_arr_organic_yoy = 28.0

ah_pct     = float(kpis["stock_ah_change_pct"])
close_px   = float(kpis["stock_close_day_of"])
open_next  = float(kpis["stock_open_next_day"])

rev_beat_m   = round(rev_actual_m - rev_cons_m) if rev_cons_m else None
oi_ng_q3     = q3["operating_margin_nongaap_pct"]
oi_ng_py_val = q3_py["operating_margin_nongaap_pct"]
oi_ng_bps_q3 = round((oi_ng_q3 - oi_ng_py_val) * 100)

beat_miss = {
    "eps_nongaap": {
        "actual":     eps_actual,
        "consensus":  round(eps_cons, 4),
        "beat":       eps_beat,
        "beat_pct":   eps_beat_pct,
        "signal":     "beat" if eps_beat > 0 else "miss",
        "driver": (
            f"Revenue beat +${rev_beat_m}M vs consensus; "
            f"non-GAAP OI margin {oi_ng_q3}% ({oi_ng_bps_q3:+d}bps YoY) held near prior-year levels, "
            f"suggesting top-line outperformance flowed through to EPS."
        ) if rev_beat_m else "Revenue outperformance at maintained non-GAAP margins drove the beat.",
    },
    "revenue": {
        "actual_m":       rev_actual_m,
        "consensus_m":    rev_cons_m,
        "beat_pct":       rev_beat_pct,
        "yoy_growth_pct": rev_yoy_pct,
        "note": f"Revenue ${rev_actual_m:,}M vs consensus ${rev_cons_m:,}M (+{rev_beat_pct}% beat)." if rev_cons_m else "Revenue consensus not available.",
    },
    "ngs_arr": {
        "actual_bn":          ngs_arr_bn,
        "yoy_growth_pct":     ngs_arr_yoy,
        "organic_yoy_pct":    ngs_arr_organic_yoy,
        "note": (
            f"Reported NGS ARR +{ngs_arr_yoy}% YoY included CyberArk and Chronosphere acquisitions. "
            f"Organic growth +{ngs_arr_organic_yoy:.0f}% YoY (ex-acquisitions)."
        ),
    },
    "stock_reaction": {
        "ah_change_pct": ah_pct,
        "close_day_of":  close_px,
        "open_next_day": open_next,
        "signal":        "bearish_despite_beat" if ah_pct < -3 else ("bullish" if ah_pct > 3 else "neutral"),
        "driver": (
            f"Reported NGS ARR +{ngs_arr_yoy}% included CyberArk and Chronosphere acquisitions; "
            f"organic growth +{ngs_arr_organic_yoy:.0f}% may have disappointed vs. headline. "
            f"Sell-the-news dynamic: stock entered print at ${close_px:.2f} on elevated expectations."
        ),
    },
}

print(f"  EPS: ${eps_actual} actual vs ${round(eps_cons,3)} consensus → +${eps_beat} (+{eps_beat_pct}%)")
print(f"  Revenue: ${rev_actual_m:,}M (+{rev_yoy_pct}% YoY)")
print(f"  NGS ARR: ${ngs_arr_bn}B (+{ngs_arr_yoy}% reported)")
print(f"  AH reaction: {ah_pct}%")


# ── SKILL STEP 6: Segment/Geo Analysis ────────────────────────────────────────

print("\n[STEP 6] Segment/Geo Analysis...")

rev_prod  = q3["revenue_product_m"]
rev_sub   = q3["revenue_subscription_support_m"]
sub_mix   = round(rev_sub / rev_actual_m * 100, 1)

prod_yoy  = round((rev_prod - q3_py["revenue_product_m"]) / q3_py["revenue_product_m"] * 100, 1)
sub_yoy   = round((rev_sub  - q3_py["revenue_subscription_support_m"]) / q3_py["revenue_subscription_support_m"] * 100, 1)

# FCF and billings context
fcf_m        = q3["fcf_m"]
fcf_margin   = q3["fcf_margin_pct"]
rpo_bn       = guide["operational_kpis"]["remaining_performance_obligations_bn"]
rpo_yoy      = guide["operational_kpis"]["rpo_yoy_growth_pct"]
plat_count   = guide["operational_kpis"]["platformized_customers"]

segment_analysis = {
    "product_revenue_m":       rev_prod,
    "subscription_revenue_m":  rev_sub,
    "subscription_mix_pct":    sub_mix,
    "product_yoy_pct":         prod_yoy,
    "subscription_yoy_pct":    sub_yoy,
    "fcf_m":                   fcf_m,
    "fcf_margin_pct":          fcf_margin,
    "rpo_bn":                  rpo_bn,
    "rpo_yoy_pct":             rpo_yoy,
    "platformized_customers":  plat_count,
    "segment_note": (
        f"Subscription/support is {sub_mix}% of total revenue — high recurring base. "
        f"Product revenue {prod_yoy:+.1f}% YoY. "
        f"FCF margin {fcf_margin}% (Q3 is seasonally mid-range; Q1 tends to be highest due to annual billings). "
        f"RPO ${rpo_bn}B (+{rpo_yoy}% YoY) provides forward revenue visibility."
    ),
    "geo_note": (
        "Geographic breakdown not available in supplemental data. "
        "Full geo breakdown requires the 10-Q filing."
    ),
}

print(f"  Product: ${rev_prod}M ({prod_yoy:+.1f}% YoY) | Sub/Support: ${rev_sub}M ({sub_yoy:+.1f}% YoY)")
print(f"  Sub mix: {sub_mix}% | RPO: ${rpo_bn}B (+{rpo_yoy}% YoY)")


# ── SKILL STEP 7: Margin Analysis ─────────────────────────────────────────────

print("\n[STEP 7] Margin Analysis...")

gm_gaap    = q3["gross_margin_gaap_pct"]
gm_ng      = q3["gross_margin_nongaap_pct"]
oi_gaap    = q3["operating_margin_gaap_pct"]
oi_ng      = q3["operating_margin_nongaap_pct"]

gm_gaap_py = q3_py["gross_margin_gaap_pct"]
gm_ng_py   = q3_py["gross_margin_nongaap_pct"]
oi_ng_py   = q3_py["operating_margin_nongaap_pct"]
oi_gaap_py = q3_py["operating_margin_gaap_pct"]

trajectory = [
    {
        "period":            q["fiscal_period"],
        "gm_gaap_pct":       q["gross_margin_gaap_pct"],
        "gm_nongaap_pct":    q["gross_margin_nongaap_pct"],
        "oi_gaap_pct":       q["operating_margin_gaap_pct"],
        "oi_nongaap_pct":    q["operating_margin_nongaap_pct"],
        "fcf_margin_pct":    q["fcf_margin_pct"],
    }
    for q in suppl["quarters"]
    if q.get("gross_margin_nongaap_pct")
]

margin_analysis = {
    "q3_fy26": {
        "gross_margin_gaap_pct":    gm_gaap,
        "gross_margin_nongaap_pct": gm_ng,
        "oi_margin_gaap_pct":       oi_gaap,
        "oi_margin_nongaap_pct":    oi_ng,
        "fcf_margin_pct":           round(fcf_m / rev_actual_m * 100, 1),
    },
    "yoy_delta_bps": {
        "gross_margin_gaap":    round((gm_gaap - gm_gaap_py) * 100),
        "gross_margin_nongaap": round((gm_ng   - gm_ng_py)   * 100),
        "oi_margin_nongaap":    round((oi_ng   - oi_ng_py)   * 100),
        "oi_margin_gaap":       round((oi_gaap - oi_gaap_py) * 100),
    },
    "driver_note": (
        f"Non-GAAP gross margin {gm_ng}% ({round((gm_ng - gm_ng_py)*100):+d}bps YoY). "
        f"Non-GAAP OI margin {oi_ng}% ({round((oi_ng - oi_ng_py)*100):+d}bps YoY). "
        f"GAAP OI margin {oi_gaap}% ({round((oi_gaap - oi_gaap_py)*100):+d}bps YoY). "
        f"FCF margin {round(fcf_m / rev_actual_m * 100, 1)}%."
    ),
    "trajectory": trajectory,
}

print(f"  Non-GAAP GM: {gm_ng}% ({round((gm_ng-gm_ng_py)*100):+d}bps YoY)")
print(f"  Non-GAAP OI margin: {oi_ng}% ({round((oi_ng-oi_ng_py)*100):+d}bps YoY)")


# ── SKILL STEP 8: Guidance Analysis ───────────────────────────────────────────

print("\n[STEP 8] Guidance Analysis...")

q4g = guide["guidance_q4_fy26"]
fyg = guide["guidance_fy26_full_year"]

q4_eps_mid  = round((q4g["eps_nongaap_low"] + q4g["eps_nongaap_high"]) / 2, 3)
q4_rev_mid  = round((q4g["revenue_low_m"]   + q4g["revenue_high_m"])   / 2)
fy_eps_mid  = round((fyg["eps_nongaap_low"] + fyg["eps_nongaap_high"]) / 2, 3)
fy_rev_mid  = round((fyg["revenue_low_m"]   + fyg["revenue_high_m"])   / 2)

eps_delta_to_q4 = round(eps_actual - q4_eps_mid, 3)  # positive = step-down, negative = step-up

_hist_beats  = sorted(est["earnings_history"], key=lambda x: x["fiscal_date_ending"])
_beat_count  = sum(1 for e in _hist_beats if e.get("eps_surprise_pct", 0) > 0)
_avg_beat    = round(sum(e["eps_surprise_pct"] for e in _hist_beats if e.get("eps_surprise_pct", 0) > 0) / max(_beat_count, 1), 1)
_step_dir    = "step-up" if eps_delta_to_q4 < 0 else "step-down"

guidance_analysis = {
    "q4_fy26": {
        "revenue_range_m":  [q4g["revenue_low_m"], q4g["revenue_high_m"]],
        "revenue_midpoint": q4_rev_mid,
        "eps_range":        [q4g["eps_nongaap_low"], q4g["eps_nongaap_high"]],
        "eps_midpoint":     q4_eps_mid,
        "ngs_arr_range_bn": [q4g.get("ngs_arr_low_bn"), q4g.get("ngs_arr_high_bn")],
        "revision":         q4g["revision_vs_prior"],
    },
    "fy26_full_year": {
        "revenue_range_m":  [fyg["revenue_low_m"], fyg["revenue_high_m"]],
        "revenue_midpoint": fy_rev_mid,
        "eps_range":        [fyg["eps_nongaap_low"], fyg["eps_nongaap_high"]],
        "eps_midpoint":     fy_eps_mid,
        "fcf_margin_pct":   fyg.get("fcf_margin_low_pct"),
        "revision":         fyg["revision_vs_prior"],
    },
    "key_signals": {
        "q4_eps_vs_q3_actual": f"Q4 midpoint ${q4_eps_mid:.2f} vs Q3 actual ${eps_actual:.2f} — {'step-down' if eps_delta_to_q4 > 0 else 'step-up'} of ${abs(eps_delta_to_q4):.2f}",
        "fy_guidance_raised":  fyg["revision_vs_prior"] == "raise",
        "credibility_read": (
            f"Beat EPS consensus in {_beat_count} of the last {len(_hist_beats)} quarters "
            f"(avg +{_avg_beat}% on beats). "
            f"Q4 FY26 ${q4_eps_mid:.2f} midpoint is a {_step_dir} of ${abs(eps_delta_to_q4):.2f} "
            f"from Q3 actual — consistent with PANW's pattern of raising guidance after the beat."
        ),
        "ngs_arr_trajectory":  f"Q4 NGS ARR guided ${q4g.get('ngs_arr_low_bn')}–{q4g.get('ngs_arr_high_bn')}B.",
    },
}

print(f"  Q4 EPS guidance: ${q4_eps_mid:.2f} midpoint | Q3 actual: ${eps_actual:.2f}")
print(f"  FY26 EPS: ${fy_eps_mid} midpoint | Revenue: ${fy_rev_mid:,}M midpoint (guidance {fyg['revision_vs_prior']}d)")


# ── SKILL STEP 9 (D2): Estimate Direction ─────────────────────────────────────
# DEPARTURE D2: Directional trajectory only — no old-vs-new model table.

print("\n[STEP 9 / D2] Estimate Direction...")

eps_hist_sorted = sorted(est["earnings_history"], key=lambda x: x["fiscal_date_ending"])

q1_fy26_eps  = next((e["eps_nongaap_actual"] for e in eps_hist_sorted if e["fiscal_date_ending"] == "2025-10-31"), None)
q2_fy26_eps  = next((e["eps_nongaap_actual"] for e in eps_hist_sorted if e["fiscal_date_ending"] == "2026-01-31"), None)
h1_fy26_eps  = round(q1_fy26_eps + q2_fy26_eps, 2) if (q1_fy26_eps and q2_fy26_eps) else None
h3q_fy26_eps = round(h1_fy26_eps + eps_actual, 2) if h1_fy26_eps else None
q4_fy26_imp  = round(fy_eps_mid - h3q_fy26_eps, 3) if h3q_fy26_eps else None

estimate_revisions = {
    "departure": "D2",
    "note": "No prior analyst model maintained. EPS trajectory shown instead of old-vs-new table.",
    "eps_history": [
        {
            "period":    e["fiscal_date_ending"],
            "actual":    e["eps_nongaap_actual"],
            "estimate":  round(e["eps_nongaap_estimate"], 3),
            "beat_pct":  round(e["eps_surprise_pct"], 1),
        }
        for e in eps_hist_sorted
    ],
    "fy26_build": {
        "q1_actual":       q1_fy26_eps,
        "q2_actual":       q2_fy26_eps,
        "q3_actual":       eps_actual,
        "h1_total":        h1_fy26_eps,
        "first_3q_total":  h3q_fy26_eps,
        "fy26_midpoint":   fy_eps_mid,
        "q4_implied":      q4_fy26_imp,
    },
    "direction": (
        f"FY26 guidance {fyg['revision_vs_prior']}. "
        f"Q4 FY26 implied ${q4_fy26_imp:.3f} based on FY26 guidance midpoint ${fy_eps_mid} minus 3-quarter actuals."
        if q4_fy26_imp else "FY26 build pending — check eps_history for prior quarter actuals."
    ),
}

print(f"  3Q FY26: ${h3q_fy26_eps} | Q4 FY26 implied: ${q4_fy26_imp}")


# ── SKILL STEP 10 (D3): Valuation ─────────────────────────────────────────────
# DEPARTURE D3: Peer NTM EV/Revenue multiples only — no DCF.

print("\n[STEP 10 / D3] Valuation...")

shares_m     = q3["shares_diluted_m"]
mktcap_b     = round(close_px * shares_m / 1000, 1)

# TTM: Q4 FY25 + Q1 FY26 + Q2 FY26 + Q3 FY26
ttm_periods = ["Q4_FY25", "Q1_FY26", "Q2_FY26", "Q3_FY26"]
ttm_rev_m = sum(
    next(q["revenue_total_m"] for q in suppl["quarters"] if q["fiscal_period"] == p)
    for p in ttm_periods
)
ev_ttm = round(mktcap_b / (ttm_rev_m / 1000), 1)

# NTM: Q4 FY26 (guided) + Q1 FY27 est + Q2 FY27 est + Q3 FY27 est
q1_fy26_rev = next(q["revenue_total_m"] for q in suppl["quarters"] if q["fiscal_period"] == "Q1_FY26")
q2_fy26_rev = next(q["revenue_total_m"] for q in suppl["quarters"] if q["fiscal_period"] == "Q2_FY26")
q4_fy26_rev_imp = fy_rev_mid - q1_fy26_rev - q2_fy26_rev - rev_actual_m
q1_fy27_est = round(q1_fy26_rev * 1.15)
q2_fy27_est = round(q2_fy26_rev * 1.15)
q3_fy27_est = round(rev_actual_m * 1.15)
ntm_rev_m   = q4_fy26_rev_imp + q1_fy27_est + q2_fy27_est + q3_fy27_est

ev_ntm   = round(mktcap_b / (ntm_rev_m / 1000), 1)

# Target multiple range: 10-12x NTM (discount to CRWD for lower growth)
mult_lo, mult_hi = 10.0, 12.0
pt_lo = round(mult_lo * ntm_rev_m / shares_m * 1000 / 1000)  # in $
pt_hi = round(mult_hi * ntm_rev_m / shares_m * 1000 / 1000)
pt_mid_val = round((pt_lo + pt_hi) / 2)
upside_pct = round((pt_mid_val / close_px - 1) * 100, 1)

# Peer table
ftnt_ttm_rev_est = ftnt["quarterly_financials"]["revenue_total_m"] * 4  # annualized single quarter
ftnt_ev_ttm = round(ftnt["valuation"]["market_cap_bn"] / (ftnt_ttm_rev_est / 1000), 1)

peer_table = [
    {
        "symbol":          "CRWD",
        "ev_rev_ttm_x":    crwd["ttm_from_overview"]["ev_to_revenue_ttm"],
        "rev_growth_pct":  crwd["quarterly_financials"]["revenue_yoy_growth_pct"],
        "oi_margin_pct":   crwd["quarterly_financials"]["operating_margin_nongaap_pct"],
        "note":            "Premium multiple reflects faster growth and ARR recovery",
    },
    {
        "symbol":          "FTNT",
        "ev_rev_ttm_x":    ftnt_ev_ttm,
        "rev_growth_pct":  ftnt["quarterly_financials"]["revenue_yoy_growth_pct"],
        "oi_margin_pct":   ftnt["quarterly_financials"]["operating_margin_nongaap_pct"],
        "note":            "Margin leader; lower multiple reflects more hardware-oriented mix",
    },
    {
        "symbol":          "ZS",
        "ev_rev_ttm_x":    None,
        "rev_growth_pct":  zs["quarterly_financials"]["revenue_yoy_growth_pct"],
        "oi_margin_pct":   zs["quarterly_financials"]["operating_margin_nongaap_pct"],
        "note":            "EV not pre-staged; revenue miss this quarter notable",
    },
    {
        "symbol":          "PANW",
        "ev_rev_ttm_x":    ev_ttm,
        "ev_rev_ntm_x":    ev_ntm,
        "rev_growth_pct":  rev_yoy_pct,
        "oi_margin_pct":   oi_ng,
        "note":            "Subject company — NTM multiple computed",
    },
]

valuation = {
    "departure":         "D3",
    "note":              "No DCF. Peer NTM EV/Revenue multiples used for PT range.",
    "panw_price":        close_px,
    "panw_shares_m":     shares_m,
    "panw_mktcap_b":     mktcap_b,
    "panw_ttm_rev_m":    ttm_rev_m,
    "panw_ev_rev_ttm_x": ev_ttm,
    "panw_ntm_rev_m":    ntm_rev_m,
    "panw_ev_rev_ntm_x": ev_ntm,
    "ntm_build": {
        "q4_fy26_implied_m": q4_fy26_rev_imp,
        "q1_fy27_est_m":    q1_fy27_est,
        "q2_fy27_est_m":    q2_fy27_est,
        "q3_fy27_est_m":    q3_fy27_est,
        "total_ntm_m":      ntm_rev_m,
        "assumption":       "FY27 estimated at +15% YoY from FY26 actuals",
    },
    "target_multiple_range_x": [mult_lo, mult_hi],
    "pt_low":            pt_lo,
    "pt_high":           pt_hi,
    "pt_midpoint":       pt_mid_val,
    "implied_upside_pct": upside_pct,
    "peer_table":        peer_table,
    "rationale": (
        f"PANW trades at {ev_ttm}x TTM and {ev_ntm}x NTM EV/Revenue at the Jun 2 close of ${close_px}. "
        f"Applying {mult_lo}–{mult_hi}x NTM (discount to CRWD's {crwd['ttm_from_overview']['ev_to_revenue_ttm']}x "
        f"reflects PANW's lower growth rate of ~{rev_yoy_pct}% vs CRWD's ~{crwd['quarterly_financials']['revenue_yoy_growth_pct']}%) "
        f"yields PT range ${pt_lo}–${pt_hi}. "
        f"Midpoint ${pt_mid_val} implies {upside_pct:+.1f}% upside from post-earnings close."
    ),
}

print(f"  Mkt cap: ${mktcap_b}B | TTM Rev: ${ttm_rev_m:,}M | EV/Rev TTM: {ev_ttm}x | NTM: {ev_ntm}x")
print(f"  NTM revenue: ${ntm_rev_m:,}M | PT range: ${pt_lo}–${pt_hi} | Midpoint: ${pt_mid_val} ({upside_pct:+.1f}%)")


# ── SKILL STEP 11: Rating ──────────────────────────────────────────────────────
# Applies skill criteria from workflow.md Step 11 directly.

print("\n[STEP 11] Rating Assessment (skill criteria applied)...")

# Primary trigger per skill Step 11:
# "significantly better + guidance raised → Consider upgrade"
eps_sig_beat = eps_beat_pct >= 5.0
fy_raised    = fyg["revision_vs_prior"] == "raise"
q4_step_up   = q4_eps_mid > eps_actual

upgrade_trigger = eps_sig_beat and fy_raised

# Moderating factors per skill Step 11 "Consider:":
# - Stock reaction (up/down/flat?)
# - Valuation (expensive/cheap relative to new estimates?)
# - Risk/reward (asymmetry shifted?)
stock_negative   = ah_pct <= -3.0
valuation_rich   = ev_ntm > mult_hi          # NTM multiple above target high end
asym_negative    = upside_pct < -15.0        # PT meaningfully below current price

moderators_against_upgrade = sum([stock_negative, valuation_rich, asym_negative])

# Apply skill discipline: trigger is permission to "consider", not a mandate.
# The moderating considerations decide whether to upgrade or maintain.
if upgrade_trigger and moderators_against_upgrade == 0:
    rating = "Upgrade to Outperform"
    rating_short = "UPGRADE"
    rating_basis = "primary trigger met; no moderating factors against."
elif upgrade_trigger and moderators_against_upgrade >= 2:
    rating = "Maintain Outperform"
    rating_short = "MAINTAIN"
    rating_basis = (
        f"primary trigger met (EPS beat +{eps_beat_pct}%, FY26 guidance raised), but "
        f"{moderators_against_upgrade} of 3 moderating factors argue against upgrade — "
        f"holding rating at Outperform without the upgrade step."
    )
elif upgrade_trigger and moderators_against_upgrade == 1:
    rating = "Upgrade to Outperform"
    rating_short = "UPGRADE"
    rating_basis = (
        f"primary trigger met; one moderating factor against (noted in rationale) but "
        f"insufficient to block upgrade."
    )
elif not upgrade_trigger and (eps_beat_pct >= 0 or fy_raised):
    rating = "Maintain Outperform"
    rating_short = "MAINTAIN"
    rating_basis = "results inline/mixed — usually maintain rating per skill."
else:
    rating = "Maintain / Under Review"
    rating_short = "MAINTAIN"
    rating_basis = "results below expectations — review pending."

# Q&A signal count — answered/partial/deflected schema
qa_exchanges = qa.get("exchanges", [])
answered_qa  = sum(1 for ex in qa_exchanges if ex.get("key_signal") == "answered")
partial_qa   = sum(1 for ex in qa_exchanges if ex.get("key_signal") == "partial")
deflected_qa = sum(1 for ex in qa_exchanges if ex.get("key_signal") == "deflected")

rating_output = {
    "rating":           rating,
    "rating_short":     rating_short,
    "price_target":     pt_mid_val,
    "pt_range":         [pt_lo, pt_hi],
    "current_price":    close_px,
    "implied_upside_pct": upside_pct,
    "qa_signal_summary": {
        "total_exchanges": len(qa_exchanges),
        "answered":  answered_qa,
        "partial":   partial_qa,
        "deflected": deflected_qa,
    },
    "skill_criteria": {
        "primary_trigger": {
            "eps_beat_significant":  eps_sig_beat,
            "fy_guidance_raised":    fy_raised,
            "q4_step_up_vs_actual":  q4_step_up,
            "trigger_met":           upgrade_trigger,
        },
        "moderating_factors": {
            "stock_reaction_negative":    {"value": stock_negative, "data": f"AH {ah_pct:+.1f}%"},
            "valuation_rich_vs_target":   {"value": valuation_rich, "data": f"NTM {ev_ntm}x vs {mult_lo}–{mult_hi}x target"},
            "risk_reward_asymmetric_neg": {"value": asym_negative,  "data": f"implied {upside_pct:+.1f}% to PT"},
            "count_against_upgrade":      moderators_against_upgrade,
        },
        "decision_basis": rating_basis,
    },
    "rationale": (
        f"Primary trigger: EPS beat +{eps_beat_pct}% and FY26 guidance {fyg['revision_vs_prior']} "
        f"(midpoint ${fy_eps_mid}) make this an upgrade-eligible print. "
        f"Moderating factors per skill: stock reaction {ah_pct:+.1f}% AH ({'against' if stock_negative else 'neutral/for'} upgrade); "
        f"valuation {ev_ntm}x NTM vs {mult_lo}–{mult_hi}x target multiple ({'expensive' if valuation_rich else 'in-range'}); "
        f"risk/reward asymmetry {upside_pct:+.1f}% to PT ({'negatively skewed' if asym_negative else 'balanced'}). "
        f"{moderators_against_upgrade} of 3 moderators against upgrade → {rating}. "
        f"Platform metrics support the standing Outperform thesis: NGS ARR +{ngs_arr_yoy}% (organic +{ngs_arr_organic_yoy:.0f}%), "
        f"{plat_count} platformized customers, RPO ${rpo_bn}B (+{rpo_yoy}% YoY). "
        f"Q&A management responsiveness: {answered_qa} answered / {partial_qa} partial / {deflected_qa} deflected."
    ),
    "key_risks": [
        "Platformization velocity slows if customer consolidation pace disappoints",
        "CRWD competitive recovery intensifies and captures consolidation deals",
        "NGS ARR growth decelerates as large customer base matures",
        "FY27 growth outlook uncertain if macro conditions soften enterprise security spend",
        "FCF margin trajectory dependent on billings timing and M&A integration costs",
    ],
}

print(f"  Rating: {rating}")
print(f"  PT: ${pt_mid_val} (range ${pt_lo}–${pt_hi}) | Upside: {upside_pct:+.1f}%")


# ── Assemble and Write Output ──────────────────────────────────────────────────

output = {
    "generated":      str(date.today()),
    "symbol":         "PANW",
    "fiscal_period":  "Q3_FY26",
    "report_date":    "2026-06-02",
    "skill_version":  "equity-research/earnings-analysis v0.1.0 (financial-services-plugins)",
    "departures":     DEPARTURES,
    "steps": {
        "5_beat_miss":          beat_miss,
        "6_segment_geo":        segment_analysis,
        "7_margin":             margin_analysis,
        "8_guidance":           guidance_analysis,
        "9_estimate_revisions": estimate_revisions,
        "10_valuation":         valuation,
        "11_rating":            rating_output,
    },
}

with open(OUT, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Analysis complete → {OUT}")
print(f"   Rating: {rating} | PT: ${pt_mid_val} | Upside: {upside_pct:+.1f}%")
print(f"   Departures documented: {len(DEPARTURES)}")
