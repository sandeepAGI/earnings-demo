#!/usr/bin/env python3
"""
PANW Q2 FY26 Earnings Analysis
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
OUT = Path(__file__).parent / "panw_q2fy26_earnings_analysis.json"

DEPARTURES = [
    {
        "id": "D1",
        "step": "1 — Data Freshness",
        "departure": "Pre-staged raw files used instead of live web search.",
        "reason": "Workshop reproducibility — the same output must render reliably before June 4, 2026. Live fetch produces non-deterministic content.",
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
guide = load_json("panw_q2fy26_guidance.json")
suppl = load_json("panw_supplemental_8q.json")
qa    = load_json("panw_q2fy26_transcript_qa.json")
crwd  = load_json("crwd_q4fy26_results.json")
ftnt  = load_json("ftnt_q12026_results.json")
zs    = load_json("zs_q3fy26_results.json")

# Primary Q2 FY26 figures from supplemental (authoritative)
q2     = next(q for q in suppl["quarters"] if q["fiscal_period"] == "Q2_FY26")
q2_py  = next(q for q in suppl["quarters"] if q["fiscal_period"] == "Q2_FY25")  # prior year

# EPS and consensus from earnings history
q2_eps = next(e for e in est["earnings_history"] if e["fiscal_date_ending"] == "2026-01-31")

# After-hours reaction from DB (verified actual — panw_price_daily.json)
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
kpi_rows = conn.execute(
    "SELECT kpi_name, kpi_value FROM company_kpis WHERE symbol='PANW' AND fiscal_period='Q2_FY26'"
).fetchall()
conn.close()
kpis = {r["kpi_name"]: r["kpi_value"] for r in kpi_rows}

# Verify critical fields
assert q2["eps_nongaap_diluted"] == 1.03, "Q2 FY26 EPS mismatch"
assert q2_eps["eps_nongaap_actual"] == 1.03, "Earnings history EPS mismatch"
print(f"  ✓ Q2 FY26 revenue: ${q2['revenue_total_m']:,}M | EPS: ${q2['eps_nongaap_diluted']}")
print(f"  ✓ Consensus EPS: ${q2_eps['eps_nongaap_estimate']:.4f}")
print(f"  ✓ AH reaction: {kpis.get('stock_ah_change_pct', 'missing')}%")


# ── SKILL STEP 5: Beat/Miss Analysis ──────────────────────────────────────────

print("\n[STEP 5] Beat/Miss Analysis...")

eps_actual   = q2["eps_nongaap_diluted"]           # 1.03
eps_cons     = q2_eps["eps_nongaap_estimate"]       # 0.93684
eps_beat     = round(eps_actual - eps_cons, 3)
eps_beat_pct = round(q2_eps["eps_surprise_pct"], 1) # 9.94

rev_actual_m = q2["revenue_total_m"]               # 2594
rev_yoy_pct  = q2["revenue_yoy_growth_pct"]        # 14.9

ngs_arr_bn  = guide["operational_kpis"]["ngs_arr_bn"]             # 6.33
ngs_arr_yoy = guide["operational_kpis"]["ngs_arr_yoy_growth_pct"] # 33
ngs_arr_organic_yoy = 28  # From transcript: "NGS ARR up 28% excluding Chronosphere"

ah_pct     = float(kpis["stock_ah_change_pct"])   # -8.53
close_px   = float(kpis["stock_close_day_of"])    # 163.50

beat_miss = {
    "eps_nongaap": {
        "actual":     eps_actual,
        "consensus":  round(eps_cons, 4),
        "beat":       eps_beat,
        "beat_pct":   eps_beat_pct,
        "signal":     "beat",
        "driver":     "Platformization velocity and operating leverage. Non-GAAP OI margin 30.3% — third consecutive quarter above 30%.",
    },
    "revenue": {
        "actual_m":      rev_actual_m,
        "consensus_m":   None,
        "yoy_growth_pct": rev_yoy_pct,
        "note": "Revenue consensus not available in pre-staged files (null in yfinance free tier). "
                "Organic revenue growth +14.9% YoY. Chronosphere acquisition closed Feb 2026.",
    },
    "ngs_arr": {
        "actual_bn":          ngs_arr_bn,
        "yoy_growth_pct":     ngs_arr_yoy,
        "organic_yoy_pct":    ngs_arr_organic_yoy,
        "note": "Reported +33% YoY includes Chronosphere acquisition. "
                "Management cited +28% organic growth on the call. "
                "Platformized customer count: 1,550.",
    },
    "stock_reaction": {
        "ah_change_pct": ah_pct,
        "close_day_of":  close_px,
        "open_next_day": 149.55,
        "signal":        "bearish_despite_beat",
        "driver": "Market sold the Q3 guidance, not the Q2 beat. "
                  "Q3 EPS guided $0.79 midpoint vs Q2 actual $1.03 — sequential step-down of $0.24. "
                  "M&A integration costs (CyberArk, Chronosphere) diluting near-term EPS.",
    },
}

print(f"  EPS: ${eps_actual} actual vs ${round(eps_cons,3)} consensus → +${eps_beat} (+{eps_beat_pct}%)")
print(f"  Revenue: ${rev_actual_m:,}M (+{rev_yoy_pct}% YoY)")
print(f"  NGS ARR: ${ngs_arr_bn}B (+{ngs_arr_yoy}% reported, +{ngs_arr_organic_yoy}% organic)")
print(f"  AH reaction: {ah_pct}%")


# ── SKILL STEP 6: Segment/Geo Analysis ────────────────────────────────────────

print("\n[STEP 6] Segment/Geo Analysis...")

rev_prod  = q2["revenue_product_m"]              # 514
rev_sub   = q2["revenue_subscription_support_m"] # 2080
sub_mix   = round(rev_sub / rev_actual_m * 100, 1)

prod_yoy  = round((rev_prod - q2_py["revenue_product_m"]) / q2_py["revenue_product_m"] * 100, 1)
sub_yoy   = round((rev_sub  - q2_py["revenue_subscription_support_m"]) / q2_py["revenue_subscription_support_m"] * 100, 1)

# FCF and billings context
fcf_m        = q2["fcf_m"]
fcf_margin   = q2["fcf_margin_pct"]
rpo_bn       = guide["operational_kpis"]["remaining_performance_obligations_bn"]  # 16.0
rpo_yoy      = guide["operational_kpis"]["rpo_yoy_growth_pct"]                   # 23
plat_count   = guide["operational_kpis"]["platformized_customers"]                # 1550

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
        f"Product revenue +{prod_yoy}% YoY as platform consolidation drives firewall upgrades. "
        f"FCF margin {fcf_margin}% is seasonally low (Q1 tends to be high due to annual billings timing). "
        f"RPO ${rpo_bn}B (+{rpo_yoy}% YoY) provides strong forward revenue visibility."
    ),
    "geo_note": (
        "Geographic breakdown not available in supplemental data. "
        "Full geo breakdown requires the 10-Q filing. "
        "Prior year Q2 FY25: Americas +13%, EMEA +18%, JPAC +17% YoY. "
        "Management cited 'broad-based strength across regions' on the Q2 FY26 call."
    ),
}

print(f"  Product: ${rev_prod}M ({prod_yoy:+.1f}% YoY) | Sub/Support: ${rev_sub}M ({sub_yoy:+.1f}% YoY)")
print(f"  Sub mix: {sub_mix}% | RPO: ${rpo_bn}B (+{rpo_yoy}% YoY)")


# ── SKILL STEP 7: Margin Analysis ─────────────────────────────────────────────

print("\n[STEP 7] Margin Analysis...")

gm_gaap    = q2["gross_margin_gaap_pct"]         # 73.6
gm_ng      = q2["gross_margin_nongaap_pct"]      # 76.1
oi_gaap    = q2["operating_margin_gaap_pct"]     # 15.3
oi_ng      = q2["operating_margin_nongaap_pct"]  # 30.3

gm_gaap_py = q2_py["gross_margin_gaap_pct"]      # 73.5
gm_ng_py   = q2_py["gross_margin_nongaap_pct"]   # 76.6
oi_ng_py   = q2_py["operating_margin_nongaap_pct"] # 28.4
oi_gaap_py = q2_py["operating_margin_gaap_pct"]  # 10.7

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
    "q2_fy26": {
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
        f"Non-GAAP gross margin {gm_ng}% ({round((gm_ng - gm_ng_py)*100):+d}bps YoY) — "
        f"slight compression from mix shift toward lower-margin product revenue. "
        f"Non-GAAP OI margin {oi_ng}% ({round((oi_ng - oi_ng_py)*100):+d}bps YoY) — "
        f"third consecutive quarter above 30%, driven by operating leverage on subscription base. "
        f"GAAP OI margin {oi_gaap}% ({round((oi_gaap - oi_gaap_py)*100):+d}bps YoY improvement) — "
        f"partly reflects Q2 FY25 litigation charge normalization. "
        f"FCF margin {round(fcf_m / rev_actual_m * 100, 1)}% is seasonally low; "
        f"Q1 FY26 was 68.2% due to annual billings concentration."
    ),
    "trajectory": trajectory,
}

print(f"  Non-GAAP GM: {gm_ng}% ({round((gm_ng-gm_ng_py)*100):+d}bps YoY)")
print(f"  Non-GAAP OI margin: {oi_ng}% ({round((oi_ng-oi_ng_py)*100):+d}bps YoY)")


# ── SKILL STEP 8: Guidance Analysis ───────────────────────────────────────────

print("\n[STEP 8] Guidance Analysis...")

q3g = guide["guidance_q3_fy26"]
fyg = guide["guidance_fy26_full_year"]

q3_eps_mid  = round((q3g["eps_nongaap_low"] + q3g["eps_nongaap_high"]) / 2, 3)  # 0.790
q3_rev_mid  = round((q3g["revenue_low_m"]   + q3g["revenue_high_m"])   / 2)     # 2943
fy_eps_mid  = round((fyg["eps_nongaap_low"] + fyg["eps_nongaap_high"]) / 2, 3)  # 3.675
fy_rev_mid  = round((fyg["revenue_low_m"]   + fyg["revenue_high_m"])   / 2)     # 11295

eps_stepdown = round(eps_actual - q3_eps_mid, 3)  # 0.240 step-down

guidance_analysis = {
    "q3_fy26": {
        "revenue_range_m":  [q3g["revenue_low_m"], q3g["revenue_high_m"]],
        "revenue_midpoint": q3_rev_mid,
        "eps_range":        [q3g["eps_nongaap_low"], q3g["eps_nongaap_high"]],
        "eps_midpoint":     q3_eps_mid,
        "ngs_arr_range_bn": [q3g["ngs_arr_low_bn"], q3g["ngs_arr_high_bn"]],
        "revision":         q3g["revision_vs_prior"],  # "initial"
    },
    "fy26_full_year": {
        "revenue_range_m":  [fyg["revenue_low_m"], fyg["revenue_high_m"]],
        "revenue_midpoint": fy_rev_mid,
        "eps_range":        [fyg["eps_nongaap_low"], fyg["eps_nongaap_high"]],
        "eps_midpoint":     fy_eps_mid,
        "fcf_margin_pct":   fyg["fcf_margin_low_pct"],
        "revision":         fyg["revision_vs_prior"],  # "raise"
    },
    "key_signals": {
        "q3_eps_step_down":   f"Q3 midpoint ${q3_eps_mid:.2f} vs Q2 actual ${eps_actual:.2f} — step-down of ${eps_stepdown:.2f}",
        "step_down_driver":   "M&A integration costs from CyberArk and Chronosphere acquisitions, both closed in Feb 2026. Near-term EPS dilution expected through H2 FY26.",
        "fy_guidance_raised": fyg["revision_vs_prior"] == "raise",
        "credibility_read":   "PANW has a consistent track record of conservative guidance and beating. The Q3 step-down has a clear M&A rationale. Risk: integration extends into FY27.",
        "ngs_arr_trajectory": f"Q3 NGS ARR guided ${q3g['ngs_arr_low_bn']}–{q3g['ngs_arr_high_bn']}B implies continued platform momentum.",
    },
}

print(f"  Q3 EPS guidance: ${q3_eps_mid:.2f} midpoint (step-down of ${eps_stepdown:.2f} from Q2 actual)")
print(f"  FY26 EPS: ${fy_eps_mid} midpoint | Revenue: ${fy_rev_mid:,}M midpoint (guidance {fyg['revision_vs_prior']}d)")


# ── SKILL STEP 9 (D2): Estimate Direction ─────────────────────────────────────
# DEPARTURE D2: Directional trajectory only — no old-vs-new model table.

print("\n[STEP 9 / D2] Estimate Direction...")

eps_hist_sorted = sorted(est["earnings_history"], key=lambda x: x["fiscal_date_ending"])

q1_fy26_eps  = next(e["eps_nongaap_actual"] for e in eps_hist_sorted if e["fiscal_date_ending"] == "2025-10-31")
h1_fy26_eps  = round(q1_fy26_eps + eps_actual, 2)                  # 0.93 + 1.03 = 1.96
h2_fy26_imp  = round(fy_eps_mid - h1_fy26_eps, 3)                 # 3.675 - 1.96 = 1.715
h2_avg_per_q = round(h2_fy26_imp / 2, 3)                          # 0.858

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
        "q2_actual":       eps_actual,
        "h1_total":        h1_fy26_eps,
        "fy26_midpoint":   fy_eps_mid,
        "h2_implied":      h2_fy26_imp,
        "h2_avg_per_qtr":  h2_avg_per_q,
    },
    "direction": (
        f"FY26 guidance raised. Near-term deceleration (Q3 ${q3_eps_mid:.2f}) reflects M&A dilution. "
        f"H2 FY26 implied ${h2_fy26_imp:.3f} total (avg ${h2_avg_per_q:.3f}/quarter) "
        f"suggests re-acceleration into Q4 FY26 beyond the initial integration dip."
    ),
}

print(f"  H1 FY26: ${h1_fy26_eps} | H2 FY26 implied: ${h2_fy26_imp} (avg ${h2_avg_per_q}/q)")


# ── SKILL STEP 10 (D3): Valuation ─────────────────────────────────────────────
# DEPARTURE D3: Peer NTM EV/Revenue multiples only — no DCF.

print("\n[STEP 10 / D3] Valuation...")

shares_m     = q2["shares_diluted_m"]   # 711
mktcap_b     = round(close_px * shares_m / 1000, 1)     # $B

ttm_revs = {
    "Q3_FY25": 2289, "Q4_FY25": 2536, "Q1_FY26": 2474, "Q2_FY26": 2594
}
ttm_rev_m = sum(
    next(q["revenue_total_m"] for q in suppl["quarters"] if q["fiscal_period"] == p)
    for p in ttm_revs
)
ev_ttm = round(mktcap_b / (ttm_rev_m / 1000), 1)

# NTM: Q3 FY26 + Q4 FY26 implied + Q1 FY27 est + Q2 FY27 est
q4_fy26_imp = fy_rev_mid - (2474 + 2594 + q3_rev_mid)   # 11295 - 7011 = 4284 ... wait
# H1 FY26 = Q1 + Q2 = 2474 + 2594 = 5068
# Q3 guided = 2943
# Q4 implied = 11295 - 5068 - 2943 = 3284
q4_fy26_imp = fy_rev_mid - 2474 - 2594 - q3_rev_mid        # 3284
q1_fy27_est = round(2474 * 1.15)                            # ~2845
q2_fy27_est = round(2594 * 1.15)                            # ~2983
ntm_rev_m   = q3_rev_mid + q4_fy26_imp + q1_fy27_est + q2_fy27_est  # ~12055

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
        "q3_fy26_guided_m": q3_rev_mid,
        "q4_fy26_implied_m": q4_fy26_imp,
        "q1_fy27_est_m":    q1_fy27_est,
        "q2_fy27_est_m":    q2_fy27_est,
        "total_ntm_m":      ntm_rev_m,
        "assumption":       "FY27 H1 estimated at +15% YoY from FY26 H1 actuals",
    },
    "target_multiple_range_x": [mult_lo, mult_hi],
    "pt_low":            pt_lo,
    "pt_high":           pt_hi,
    "pt_midpoint":       pt_mid_val,
    "implied_upside_pct": upside_pct,
    "peer_table":        peer_table,
    "rationale": (
        f"PANW trades at {ev_ttm}x TTM and {ev_ntm}x NTM EV/Revenue at the Feb 17 close of ${close_px}. "
        f"Applying {mult_lo}–{mult_hi}x NTM (discount to CRWD's {crwd['ttm_from_overview']['ev_to_revenue_ttm']}x "
        f"reflects PANW's lower growth rate of ~{rev_yoy_pct}% vs CRWD's ~{crwd['quarterly_financials']['revenue_yoy_growth_pct']}%) "
        f"yields PT range ${pt_lo}–${pt_hi}. "
        f"Midpoint ${pt_mid_val} implies +{upside_pct}% upside from post-earnings close."
    ),
}

print(f"  Mkt cap: ${mktcap_b}B | TTM Rev: ${ttm_rev_m:,}M | EV/Rev TTM: {ev_ttm}x | NTM: {ev_ntm}x")
print(f"  NTM revenue: ${ntm_rev_m:,}M | PT range: ${pt_lo}–${pt_hi} | Midpoint: ${pt_mid_val} (+{upside_pct}%)")


# ── SKILL STEP 11: Rating ──────────────────────────────────────────────────────
# Applies skill criteria from workflow.md Step 11 directly.

print("\n[STEP 11] Rating Assessment (skill criteria applied)...")

eps_sig_beat    = eps_beat_pct >= 5.0           # True  (9.9%)
fy_raised       = fyg["revision_vs_prior"] == "raise"  # True
q3_step_down    = q3_eps_mid < eps_actual       # True  ($0.79 < $1.03)
stock_adjusted  = ah_pct < -5.0                 # True  (-8.53%)

# Skill logic:
# "significantly better + guidance raised → Consider upgrade"
# "inline or mixed → Usually maintain"
# "significantly worse + guidance cut → Consider downgrade"
if eps_sig_beat and fy_raised and not q3_step_down:
    rating = "Upgrade to Outperform"
    rating_short = "UPGRADE"
elif eps_sig_beat and fy_raised and q3_step_down and stock_adjusted:
    # Beat + FY raised, but near-term step-down already absorbed in price
    rating = "Maintain Outperform"
    rating_short = "MAINTAIN"
elif not eps_sig_beat or not fy_raised:
    rating = "Maintain / Under Review"
    rating_short = "MAINTAIN"
else:
    rating = "Maintain Outperform"
    rating_short = "MAINTAIN"

# Q&A signal count
bullish_qa = sum(1 for ex in qa.get("exchanges", []) if ex.get("key_signal") == "bullish")
bearish_qa = sum(1 for ex in qa.get("exchanges", []) if ex.get("key_signal") == "bearish")
neutral_qa = sum(1 for ex in qa.get("exchanges", []) if ex.get("key_signal") == "neutral")

rating_output = {
    "rating":           rating,
    "rating_short":     rating_short,
    "price_target":     pt_mid_val,
    "pt_range":         [pt_lo, pt_hi],
    "current_price":    close_px,
    "implied_upside_pct": upside_pct,
    "qa_signal_summary": {
        "total_exchanges": len(qa.get("exchanges", [])),
        "bullish": bullish_qa,
        "bearish": bearish_qa,
        "neutral": neutral_qa,
    },
    "skill_criteria": {
        "eps_beat_significant": eps_sig_beat,
        "fy_guidance_raised":   fy_raised,
        "q3_sequential_step_down": q3_step_down,
        "stock_already_adjusted":  stock_adjusted,
    },
    "rationale": (
        f"EPS beat of +{eps_beat_pct}% and raised FY26 guidance (midpoint ${fy_eps_mid}) support "
        f"the thesis. Q3 EPS guidance (${q3_eps_mid:.2f} midpoint) represents a ${eps_stepdown:.2f} "
        f"sequential step-down from Q2 actual — driven by M&A integration costs from CyberArk and "
        f"Chronosphere, both acquired in Feb 2026. Stock fell {abs(ah_pct):.1f}% AH, partially "
        f"absorbing the near-term headwind. At {ev_ntm}x NTM EV/Revenue, valuation reflects the "
        f"integration discount. Platform thesis intact: NGS ARR +{ngs_arr_yoy}% (organic +{ngs_arr_organic_yoy}%), "
        f"1,550 platformized customers, RPO ${rpo_bn}B (+{rpo_yoy}% YoY). "
        f"PT ${pt_mid_val} based on {mult_lo}–{mult_hi}x NTM EV/Revenue ({upside_pct}% upside). "
        f"Q&A sentiment: {bullish_qa} bullish / {bearish_qa} bearish / {neutral_qa} neutral exchanges."
    ),
    "key_risks": [
        "M&A integration (CyberArk, Chronosphere) extends beyond H2 FY26, further pressuring EPS",
        "CRWD platform recovery intensifies — net new ARR +47% YoY signals competitive re-acceleration",
        "Platformization strategy slows if customers consolidate more slowly than guided",
        "NGS ARR organic growth gap vs. reported (28% vs 33%) widens if Chronosphere contribution disappoints",
        "FCF margin recovery in H2 FY26 requires billings concentration — execution risk",
    ],
}

print(f"  Rating: {rating}")
print(f"  PT: ${pt_mid_val} (range ${pt_lo}–${pt_hi}) | Upside: +{upside_pct}%")


# ── Assemble and Write Output ──────────────────────────────────────────────────

output = {
    "generated":      str(date.today()),
    "symbol":         "PANW",
    "fiscal_period":  "Q2_FY26",
    "report_date":    "2026-02-17",
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
print(f"   Rating: {rating} | PT: ${pt_mid_val} | Upside: +{upside_pct}%")
print(f"   Departures documented: {len(DEPARTURES)}")
