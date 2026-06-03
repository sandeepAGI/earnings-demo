"""
generate_baseline.py — Earnings Baseline Dashboard Generator
Reads: demo/data/db/earnings.db  (built by demo/data/rebuild_db.py)
Writes: demo/earnings_baseline.html  (sibling to this script)

Three-tab output:
  Tab 1 — Baseline Data:      data tables, KPIs, charts from the DB
  Tab 2 — Claude Analysis:    placeholder until earnings reviewer process is designed,
                               tested on Q1 FY26, validated, and re-run on Q2 FY26
  Tab 3 — Decision Layer:     infrastructure cards + 4 prompt cards for live demo.
                               No pre-written analytical conclusions.

Chart.js is downloaded once and embedded inline so the HTML works offline
(file:// protocol blocks external CDN scripts in Chrome/Safari).

Run: python3 demo/generate_baseline.py  (from earnings-demo root)
"""

import sqlite3, json, math, sys, urllib.request, tempfile
from datetime import datetime
from pathlib import Path

_HERE         = Path(__file__).parent
DB_PATH       = _HERE / "data" / "db" / "earnings.db"
OUT_PATH      = _HERE / "earnings_baseline.html"
CHARTJS_CACHE = Path(tempfile.gettempdir()) / "chartjs_440.min.js"
CHARTJS_CDN   = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
ANALYSIS_PATH  = _HERE / "data" / "analysis" / "panw_q3fy26_earnings_analysis.json"
BUYSIDE_PATH   = _HERE / "data" / "analysis" / "panw_q3fy26_buyside_analysis.json"

# ── Preflight ──────────────────────────────────────────────────────────────────
if not DB_PATH.exists():
    print(f"ERROR: DB not found at {DB_PATH}")
    print("Run:  python3 demo/data/rebuild_db.py  first.")
    sys.exit(1)

# ── DB queries ────────────────────────────────────────────────────────────────
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
c = conn.cursor()

def q(sql, params=()):
    return [dict(r) for r in c.execute(sql, params).fetchall()]

def q1(sql, params=()):
    r = c.execute(sql, params).fetchone()
    return dict(r) if r else {}

PRIMARY_PERIOD = 'Q3_FY26'
PRIMARY_SYMBOL = 'PANW'

panw_q2       = q1("SELECT * FROM quarterly_financials WHERE symbol=? AND fiscal_period=?", (PRIMARY_SYMBOL, PRIMARY_PERIOD))
panw_hist     = q("SELECT * FROM quarterly_financials WHERE symbol=? AND company_type='primary' ORDER BY fiscal_date_ending", (PRIMARY_SYMBOL,))
consensus     = q1("SELECT * FROM consensus_estimates WHERE symbol=?", (PRIMARY_SYMBOL,))
eps_history   = q("SELECT * FROM eps_history WHERE symbol=? ORDER BY fiscal_date_ending DESC LIMIT 14", (PRIMARY_SYMBOL,))
kpis          = {r['kpi_name']: r for r in q("SELECT * FROM company_kpis WHERE symbol=? AND fiscal_period=?", (PRIMARY_SYMBOL, PRIMARY_PERIOD))}
guidance_rows = q("SELECT * FROM guidance WHERE symbol=? ORDER BY issued_for_period, metric", (PRIMARY_SYMBOL,))
insiders      = q("""
    SELECT insider_name, insider_role,
           MIN(transaction_date) as first_date, MAX(transaction_date) as last_date,
           COUNT(*) as num_txn, SUM(shares) as total_shares, ROUND(SUM(total_value_m),1) as total_value_m
    FROM insider_transactions
    WHERE symbol=? AND transaction_code='S'
    GROUP BY insider_name, insider_role
    ORDER BY total_value_m DESC
""", (PRIMARY_SYMBOL,))
fwd_est       = q("SELECT * FROM forward_estimates WHERE symbol=? ORDER BY fiscal_period", (PRIMARY_SYMBOL,))
price_events  = q("SELECT * FROM price_events WHERE symbol=? ORDER BY event_month", (PRIMARY_SYMBOL,))
price_hist    = q("SELECT * FROM price_history WHERE symbol=? ORDER BY month_date", (PRIMARY_SYMBOL,))
sentiment     = q("SELECT * FROM sentiment_signals WHERE symbol=?", (PRIMARY_SYMBOL,))

# ── Analysis JSON (Tab 2) ─────────────────────────────────────────────────────
_an = {}
if ANALYSIS_PATH.exists():
    with open(ANALYSIS_PATH) as _f:
        _an = json.load(_f)
else:
    print(f"  ⚠️  Analysis not found: {ANALYSIS_PATH}")
    print("     Run: python3 demo/data/analysis/run_earnings_analysis.py")

# ── Buy-side JSON (Tab 3) ──────────────────────────────────────────────────────
_bs = {}
if BUYSIDE_PATH.exists():
    with open(BUYSIDE_PATH) as _f:
        _bs = json.load(_f)
else:
    print(f"  ⚠️  Buy-side analysis not found: {BUYSIDE_PATH}")
    print("     Run: python3 demo/data/analysis/run_buyside_analysis.py")
qa_exchanges  = q("SELECT * FROM transcript_qa WHERE symbol=? ORDER BY exchange_num", (PRIMARY_SYMBOL,))
peers         = q("SELECT * FROM quarterly_financials WHERE company_type='peer' ORDER BY symbol")
peer_kpis     = q("SELECT * FROM company_kpis WHERE company_type='peer' ORDER BY symbol, kpi_name")
_all_tables   = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
db_row_count  = sum(c.execute(f"SELECT COUNT(*) FROM \"{t}\"").fetchone()[0] for t in _all_tables)

conn.close()

# ── Helpers ────────────────────────────────────────────────────────────────────
def sg(d, key, fmt=None, fallback='—'):
    v = d.get(key)
    if v is None: return fallback
    if fmt == '$M':        return f'${v:,.1f}M'
    if fmt == '$B':        return f'${v:.2f}B'
    if fmt == '$':         return f'${v:.2f}'
    if fmt == 'pct':       return f'{v:+.1f}%'
    if fmt == 'pct_plain': return f'{v:.1f}%'
    return str(v)

def _rhu(v, decimals=0):
    """Round half-up, avoiding Python's banker's rounding on exact .5 values."""
    factor = 10 ** decimals
    return math.floor(v * factor + 0.5) / factor

def fmt_cell(v, fmt='', na='—'):
    if v is None: return na
    if fmt == '$M':        return f'${_rhu(v):,.0f}M'
    if fmt == 'pct':       return f'{v:+.1f}%'
    if fmt == 'pct_plain': return f'{v:.1f}%'
    if fmt == '$B':        return f'${_rhu(v, 2):.2f}B'
    if fmt == 'yn':        return '✓' if v else '✗'
    return str(v)

def color_cls(v, good_positive=True):
    if v is None: return ''
    up = v > 0
    return ('pos' if up else 'neg') if good_positive else ('neg' if up else 'pos')

# Key values
ngs_arr     = kpis.get('ngs_arr_bn', {}).get('kpi_value') or 0
ngs_arr_yoy = kpis.get('ngs_arr_yoy_growth_pct', {}).get('kpi_value') or 0
rpo         = kpis.get('rpo_bn', {}).get('kpi_value') or 0
rpo_yoy     = kpis.get('rpo_yoy_growth_pct', {}).get('kpi_value') or 0
rev_beat    = kpis.get('revenue_beat_pct', {}).get('kpi_value') or 0
eps_beat    = kpis.get('eps_nongaap_beat_pct', {}).get('kpi_value') or 0
ah_chg      = kpis.get('stock_ah_change_pct', {}).get('kpi_value')
stock_close = kpis.get('stock_close_day_of', {}).get('kpi_value')
sbc         = kpis.get('sbc_m', {}).get('kpi_value')
# Compute GAAP OI YoY from quarterly data (prior-year same quarter)
_q2_fy25    = next((r for r in panw_hist if r['fiscal_period'] == 'Q3_FY25'), None)
_oi_now     = panw_q2.get('operating_income_gaap_m')
_oi_prior   = _q2_fy25.get('operating_income_gaap_m') if _q2_fy25 else None
gaap_oi_yoy = ((_oi_now - _oi_prior) / abs(_oi_prior) * 100) if (_oi_now and _oi_prior) else None
fcf_m       = kpis.get('fcf_m', {}).get('kpi_value') or 0
fcf_margin  = kpis.get('fcf_margin_pct', {}).get('kpi_value') or 0
platf_cust  = kpis.get('platformized_customers', {}).get('kpi_value') or 0
defer_total = kpis.get('deferred_rev_total_bn', {}).get('kpi_value') or 0

# Guidance lookups
g_q3_rev  = next((g for g in guidance_rows if g['issued_for_period']=='Q4_FY26' and g['metric']=='revenue_m'), {})
g_q3_eps  = next((g for g in guidance_rows if g['issued_for_period']=='Q4_FY26' and g['metric']=='eps_nongaap'), {})
g_q3_arr  = next((g for g in guidance_rows if g['issued_for_period']=='Q4_FY26' and g['metric']=='ngs_arr_bn'), {})
g_fy_rev  = next((g for g in guidance_rows if g['issued_for_period']=='FY26_Full' and g['metric']=='revenue_m'), {})
g_fy_eps  = next((g for g in guidance_rows if g['issued_for_period']=='FY26_Full' and g['metric']=='eps_nongaap'), {})
g_fy_fcf  = next((g for g in guidance_rows if g['issued_for_period']=='FY26_Full' and g['metric']=='fcf_margin_pct'), {})

# Peer data
peer_dict     = {p['symbol']: p for p in peers}
peer_kpi_dict = {}
for pk in peer_kpis:
    peer_kpi_dict.setdefault(pk['symbol'], {})[pk['kpi_name']] = pk

PEER_ROWS = [
    {'symbol': 'PANW', 'rev_m': panw_q2.get('revenue_total_m'), 'rev_yoy': panw_q2.get('revenue_yoy_growth_pct'),
     'arr_bn': ngs_arr, 'arr_yoy': ngs_arr_yoy, 'oi_margin': panw_q2.get('operating_margin_nongaap_pct'),
     'profitable': panw_q2.get('gaap_profitable'), 'period': PRIMARY_PERIOD},
]
for sym in ['CRWD', 'FTNT', 'ZS']:
    p  = peer_dict.get(sym, {})
    pk = peer_kpi_dict.get(sym, {})
    PEER_ROWS.append({
        'symbol': sym,
        'rev_m':     p.get('revenue_total_m'),
        'rev_yoy':   p.get('revenue_yoy_growth_pct'),
        'arr_bn':    pk.get('ending_arr_bn', {}).get('kpi_value'),
        'arr_yoy':   pk.get('ending_arr_yoy_growth_pct', {}).get('kpi_value'),
        'oi_margin': p.get('operating_margin_nongaap_pct'),
        'profitable': p.get('gaap_profitable'),
        'period':    p.get('fiscal_period', '—'),
    })

# Chart data — use GAAP OI (available all quarters; shows the litigation spike = teaching moment)
rev_quarters_sorted = sorted([r for r in panw_hist if r['revenue_total_m']], key=lambda x: x['fiscal_date_ending'])
rev_labels  = [r['fiscal_period'] for r in rev_quarters_sorted]
rev_values  = [r['revenue_total_m'] for r in rev_quarters_sorted]
oi_gaap     = [r.get('operating_income_gaap_m') for r in rev_quarters_sorted]

eps_chart   = list(reversed(eps_history[:8]))
eps_labels  = [e['fiscal_date_ending'][:7] for e in eps_chart]
eps_actual  = [e['eps_nongaap_actual'] for e in eps_chart]
eps_est     = [e['eps_nongaap_estimate'] for e in eps_chart]

price_labels = [p['month_date'] for p in price_hist]
price_closes = [p['close_price'] for p in price_hist]

# Price event markers — sorted chronologically, numbered 1–N for chart annotation
price_events_sorted = sorted(price_events, key=lambda e: e['event_month'])
price_event_markers = []
for _i, _ev in enumerate(price_events_sorted):
    _idx = next((j for j, lbl in enumerate(price_labels) if lbl == _ev['event_month']), None)
    if _idx is not None:
        price_event_markers.append({'idx': _idx, 'num': _i + 1, 'primary': _ev['event_key'] == 'q3_fy26_earnings'})

# Peer comparison chart data (already in PEER_ROWS, no new queries needed)
peer_chart_symbols   = [r['symbol'] for r in PEER_ROWS]
peer_chart_rev_yoy   = [r.get('rev_yoy') for r in PEER_ROWS]
peer_chart_oi_margin = [r.get('oi_margin') for r in PEER_ROWS]

SIGNAL_BADGE = {'answered': '✓', 'partial': '◑', 'deflected': '✗'}
generated_at = datetime.now().strftime('%Y-%m-%d %H:%M')

def _fmt_date(iso):
    try:
        return datetime.strptime(iso, '%Y-%m-%d').strftime('%b %d, %Y')
    except (ValueError, TypeError):
        return iso or '—'

fiscal_date_display = _fmt_date(panw_q2.get('fiscal_date_ending'))
report_date_display = _fmt_date(panw_q2.get('report_date'))

# ── Chart.js: download once, embed inline for offline-safe HTML ────────────────
def get_chartjs():
    if CHARTJS_CACHE.exists():
        js = CHARTJS_CACHE.read_text()
        if js.strip():
            return js
    try:
        print(f"  Downloading Chart.js 4.4.0 ...", end=' ', flush=True)
        with urllib.request.urlopen(CHARTJS_CDN, timeout=20) as r:
            js = r.read().decode('utf-8')
        CHARTJS_CACHE.write_text(js)
        print(f"OK ({len(js)//1024}KB cached)")
        return js
    except Exception as e:
        print(f"WARN — could not fetch Chart.js ({e}). Using CDN link (requires network).")
        return None

chartjs_js = get_chartjs()
chart_script_tag = (f'<script>\n{chartjs_js}\n</script>' if chartjs_js
                    else f'<script src="{CHARTJS_CDN}"></script>')

# ── Buy-side derived values ────────────────────────────────────────────────────
eps_nongaap   = panw_q2['eps_nongaap']
eps_cons      = consensus['eps_consensus_nongaap']
rev_total     = panw_q2['revenue_total_m']
oi_nongaap_m  = panw_q2['operating_income_nongaap_m']
oi_margin_ng  = panw_q2['operating_margin_nongaap_pct']
q3_eps_lo     = g_q3_eps.get('low_value') or 0
q3_eps_hi     = g_q3_eps.get('high_value') or 0
q3_arr_lo     = g_q3_arr.get('low_value') or 0
q3_arr_hi     = g_q3_arr.get('high_value') or 0
q3_rev_lo     = g_q3_rev.get('low_value') or 0
q3_rev_hi     = g_q3_rev.get('high_value') or 0
fy_fcf_lo     = g_fy_fcf.get('low_value') or 0
fy_fcf_hi     = g_fy_fcf.get('high_value') or 0

# ══════════════════════════════════════════════════════════════════════════════
# HTML
# ══════════════════════════════════════════════════════════════════════════════
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PANW Q3 FY26 — Earnings Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
{chart_script_tag}
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.1.6/dist/purify.min.js"></script>
<style>
  :root {{
    --blue:       #60B5E5;
    --purple:     #2D2042;
    --light-blue: #B3DCF3;
    --off-white:  #F2F2F2;
    --white:      #FFFFFF;
    --text:       #1A1A2E;
    --muted:      #666680;
    --border:     #DDE3EC;
    --green:      #1E7E34;
    --red:        #C0392B;
    --amber:      #B7770D;
    --green-bg:   #E8F5E9;
    --red-bg:     #FDEDEC;
    --amber-bg:   #FEF9E7;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--off-white);
    color: var(--text);
    font-family: 'Montserrat', -apple-system, sans-serif;
    font-size: 13px;
    line-height: 1.55;
  }}

  /* ── Header ── */
  .page-header {{ background: var(--blue); border-bottom: 4px solid var(--purple); }}
  .page-header-inner {{
    max-width: 1280px; margin: 0 auto; padding: 18px 28px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .page-header h1 {{ font-size: 20px; font-weight: 700; color: #fff; }}
  .page-header p  {{ font-size: 12px; color: rgba(255,255,255,.82); margin-top: 3px; }}
  .header-meta {{ text-align: right; font-size: 11px; color: rgba(255,255,255,.75); line-height: 1.6; }}
  .header-badge {{
    display: inline-block; background: var(--purple); color: #fff;
    font-size: 10px; font-weight: 600; padding: 3px 9px; border-radius: 12px;
    margin-top: 5px; letter-spacing: .04em; text-transform: uppercase;
  }}

  /* ── Tab nav ── */
  .tab-nav {{
    background: var(--purple);
    display: flex;
    max-width: 1280px;
    margin: 0 auto;
    padding: 0 28px;
  }}
  .tab-btn {{
    background: none; border: none; cursor: pointer;
    font-family: 'Montserrat', sans-serif;
    font-size: 12px; font-weight: 600;
    color: rgba(255,255,255,.6);
    padding: 12px 22px 10px;
    border-bottom: 3px solid transparent;
    letter-spacing: .04em; text-transform: uppercase;
    transition: color .15s, border-color .15s;
  }}
  .tab-btn:hover {{ color: rgba(255,255,255,.9); }}
  .tab-btn.active {{ color: #fff; border-bottom-color: var(--blue); }}
  .tab-label-pill {{
    display: inline-block;
    background: rgba(96,181,229,.25); color: var(--light-blue);
    font-size: 9px; font-weight: 700; padding: 1px 7px; border-radius: 8px;
    margin-left: 6px; vertical-align: middle; letter-spacing: .03em;
  }}
  .tab-btn.active .tab-label-pill {{ background: var(--blue); color: #fff; }}

  /* ── Tab content wrapper ── */
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}

  /* ── Layout ── */
  .container {{ max-width: 1280px; margin: 0 auto; padding: 22px 28px; display: grid; gap: 20px; }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 860px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

  /* ── Sections ── */
  .section {{
    background: var(--white); border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.06);
  }}
  .section-header {{
    background: var(--blue); padding: 10px 18px;
    display: flex; align-items: center; justify-content: space-between;
  }}
  .section-header h2 {{
    font-size: 12px; font-weight: 700; color: #fff;
    text-transform: uppercase; letter-spacing: .07em;
  }}
  .section-header .tag {{
    font-size: 10px; font-weight: 600; color: rgba(255,255,255,.8);
    background: rgba(255,255,255,.15); padding: 2px 8px; border-radius: 10px;
  }}
  .section-body {{ padding: 18px; }}

  /* ── KPI Grid ── */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }}
  .kpi-card {{
    background: var(--off-white); border: 1px solid var(--border);
    border-radius: 6px; padding: 13px 15px; border-top: 3px solid var(--blue);
  }}
  .kpi-card.accent {{ border-top-color: var(--purple); }}
  .kpi-label {{ font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }}
  .kpi-value {{ font-size: 24px; font-weight: 700; margin: 5px 0 3px; color: var(--purple); }}
  .kpi-value.pos  {{ color: var(--green); }}
  .kpi-value.neg  {{ color: var(--red);   }}
  .kpi-value.neu  {{ color: var(--amber); }}
  .kpi-value.blue {{ color: var(--blue);  }}
  .kpi-note {{ font-size: 11px; color: var(--muted); }}

  /* ── Tables ── */
  table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
  th {{
    background: var(--off-white); font-size: 10px; font-weight: 700;
    color: var(--muted); text-transform: uppercase; letter-spacing: .06em;
    padding: 7px 12px; text-align: left; border-bottom: 2px solid var(--border);
  }}
  td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; }}
  tr:last-child td {{ border-bottom: none; }}
  tr.primary-row td {{ background: rgba(96,181,229,.07); font-weight: 600; }}
  tr:hover td {{ background: #f7fafd; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; font-weight: 500; }}
  .sym      {{ font-weight: 700; color: var(--purple); }}
  .sym-peer {{ font-weight: 600; color: var(--muted); }}
  .pos {{ color: var(--green); font-weight: 600; }}
  .neg {{ color: var(--red);   font-weight: 600; }}
  .neu {{ color: var(--amber); font-weight: 600; }}

  /* ── Callout boxes ── */
  .callout {{
    background: var(--light-blue); border-left: 4px solid var(--blue);
    border-radius: 0 6px 6px 0; padding: 11px 15px;
    font-size: 12px; color: var(--purple); margin-top: 14px; line-height: 1.6;
  }}
  .callout strong {{ font-weight: 700; display: block; margin-bottom: 3px; }}
  .trap {{
    background: var(--red-bg); border-left: 4px solid var(--red);
    border-radius: 0 6px 6px 0; padding: 11px 15px;
    font-size: 12px; color: #7B241C; margin-top: 14px;
  }}
  .trap strong {{ font-weight: 700; display: block; margin-bottom: 3px; }}
  .info-box {{
    background: var(--amber-bg); border-left: 4px solid var(--amber);
    border-radius: 0 6px 6px 0; padding: 11px 15px;
    font-size: 12px; color: #7D6608; margin-top: 14px;
  }}
  .info-box strong {{ font-weight: 700; display: block; margin-bottom: 3px; }}

  /* ── Guidance ── */
  .guidance-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  @media (max-width: 860px) {{ .guidance-grid {{ grid-template-columns: 1fr; }} }}
  .guidance-panel {{
    background: var(--off-white); border: 1px solid var(--border);
    border-radius: 6px; overflow: hidden;
  }}
  .guidance-panel-header {{
    background: var(--purple); padding: 8px 14px;
    font-size: 11px; font-weight: 700; color: #fff;
    text-transform: uppercase; letter-spacing: .06em;
  }}
  .guidance-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 14px; border-bottom: 1px solid var(--border); font-size: 12.5px;
  }}
  .guidance-row:last-child {{ border-bottom: none; }}
  .guidance-label {{ color: var(--muted); font-size: 11.5px; }}
  .guidance-value {{ font-weight: 700; color: var(--purple); }}

  /* ── Q&A ── */
  .qa-item {{ padding: 12px 0; border-bottom: 1px solid var(--border); }}
  .qa-item:last-child {{ border-bottom: none; }}
  .qa-item.bear {{ border-left: 3px solid var(--red); padding-left: 12px; margin-left: -18px; }}
  .qa-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 5px; flex-wrap: wrap; }}
  .qa-num {{ background: var(--blue); color: #fff; font-size: 10px; font-weight: 700; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .qa-analyst {{ font-weight: 700; font-size: 13px; color: var(--purple); }}
  .qa-firm {{ font-size: 11px; color: var(--muted); }}
  .qa-q {{ font-size: 12px; color: var(--muted); margin-bottom: 4px; font-style: italic; }}
  .qa-a {{ font-size: 12.5px; color: var(--text); margin-bottom: 5px; }}
  .qa-note {{ font-size: 12px; color: #1A5276; background: var(--light-blue); padding: 7px 11px; border-radius: 4px; margin-top: 5px; }}

  /* ── Badges ── */
  .badge {{
    display: inline-flex; align-items: center; gap: 4px;
    padding: 2px 9px; border-radius: 12px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
  }}
  .badge-bull {{ background: var(--green-bg); color: var(--green); }}
  .badge-bear {{ background: var(--red-bg);   color: var(--red);   }}
  .badge-neu  {{ background: var(--off-white); color: var(--muted); border: 1px solid var(--border); }}
  .badge-est  {{ background: var(--amber-bg);  color: var(--amber); }}
  .badge-plan {{ background: rgba(45,32,66,.08); color: var(--purple); }}

  /* ── Signals ── */
  .signal-item {{ padding: 11px 0; border-bottom: 1px solid var(--border); }}
  .signal-item:last-child {{ border-bottom: none; }}
  .signal-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }}
  .signal-title {{ font-weight: 700; font-size: 13px; color: var(--purple); }}
  .signal-meta {{ font-size: 11px; color: var(--muted); margin-bottom: 3px; }}
  .signal-note {{ font-size: 11.5px; color: var(--text); line-height: 1.5; }}
  .signal-row {{ font-size: 12px; color: var(--text); margin: 5px 0; }}
  .signal-row .sr-label {{ color: var(--muted); }}
  .signal-row .sr-val {{ font-weight: 700; }}
  .signal-row .sr-bull {{ color: var(--green); font-weight: 700; }}
  .signal-row .sr-bear {{ color: var(--red); font-weight: 700; }}
  .signal-insight {{ font-size: 11px; color: var(--muted); border-left: 2px solid var(--border); padding-left: 8px; line-height: 1.5; margin-top: 7px; }}

  /* ── Charts ── */
  .chart-wrap {{ position: relative; height: 220px; margin: 4px 0; }}
  .chart-wrap.short {{ height: 170px; }}

  /* ── Misc ── */
  .event-key {{ font-weight: 600; color: var(--purple); font-size: 12px; }}
  .divider {{ height: 1px; background: var(--border); margin: 14px 0; }}
  .ev-badge {{
    display: inline-flex; align-items: center; justify-content: center;
    width: 20px; height: 20px; border-radius: 50%;
    background: var(--blue); color: #fff; font-size: 10px; font-weight: 700; flex-shrink: 0;
  }}
  .ev-badge.primary {{ background: var(--purple); }}

  /* ── Buy-side tab specific ── */
  .bs-context {{
    background: var(--purple); color: #fff;
    border-radius: 8px; padding: 20px 24px; margin-bottom: 0;
    line-height: 1.7; font-size: 13px;
  }}
  .bs-context strong {{ color: var(--light-blue); }}
  .bs-context .bs-verdict {{
    margin-top: 14px; font-size: 14px; font-weight: 600;
    color: var(--light-blue); border-top: 1px solid rgba(255,255,255,.15);
    padding-top: 12px;
  }}

  .foundation-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
  @media (max-width: 860px) {{ .foundation-grid {{ grid-template-columns: 1fr; }} }}
  .foundation-card {{
    background: var(--off-white); border: 1px solid var(--border);
    border-radius: 6px; padding: 14px 16px;
  }}
  .foundation-card.green-accent {{ border-top: 3px solid var(--green); }}
  .foundation-card.red-accent   {{ border-top: 3px solid var(--red);   }}
  .foundation-card.amber-accent {{ border-top: 3px solid var(--amber); }}
  .foundation-card.blue-accent  {{ border-top: 3px solid var(--blue);  }}
  .fc-title {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin-bottom: 6px; }}
  .fc-verdict {{ font-size: 15px; font-weight: 700; color: var(--purple); margin-bottom: 6px; }}
  .fc-body {{ font-size: 12px; color: var(--text); line-height: 1.6; }}
  .fc-body strong {{ color: var(--purple); }}

  /* ── Horizon toggle ── */
  .hz-toggle {{
    display: flex; gap: 8px; margin-bottom: 18px;
    background: var(--off-white); border: 1px solid var(--border);
    border-radius: 8px; padding: 6px; width: fit-content;
  }}
  .hz-btn {{
    background: none; border: none; cursor: pointer;
    font-family: 'Montserrat', sans-serif;
    font-size: 12px; font-weight: 600; padding: 8px 20px;
    border-radius: 6px; color: var(--muted);
    transition: background .15s, color .15s;
  }}
  .hz-btn.active {{ background: var(--blue); color: #fff; }}

  /* ── Framework dimensions ── */
  .framework-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 860px) {{ .framework-grid {{ grid-template-columns: 1fr; }} }}
  .fw-card {{
    background: var(--white); border: 1px solid var(--border);
    border-radius: 8px; overflow: hidden;
  }}
  .fw-card-header {{
    background: var(--blue); padding: 9px 16px;
    font-size: 11px; font-weight: 700; color: #fff;
    text-transform: uppercase; letter-spacing: .07em;
  }}
  .fw-card-header.purple {{ background: var(--purple); }}
  .fw-card-body {{ padding: 14px 16px; font-size: 12.5px; line-height: 1.65; }}
  .fw-card-body p {{ margin-bottom: 8px; }}
  .fw-card-body p:last-child {{ margin-bottom: 0; }}
  .fw-card-body strong {{ color: var(--purple); font-weight: 700; }}

  /* prelim-view and debate CSS removed — those sections no longer exist in Tab 3 */

  /* ── Footer ── */
  .page-footer {{
    background: var(--purple); color: rgba(255,255,255,.65);
    font-size: 11px; text-align: center; padding: 14px 28px;
    margin-top: 4px; line-height: 1.7;
  }}
  .page-footer strong {{ color: rgba(255,255,255,.9); }}

  /* ── Sell-side plugin tab (Tab 2) ── */
  .plugin-context {{
    background: var(--purple); color: #fff;
    border-radius: 8px; padding: 18px 22px;
    display: flex; align-items: flex-start; gap: 16px; line-height: 1.7;
  }}
  .plugin-context-icon {{ font-size: 30px; flex-shrink: 0; padding-top: 2px; }}
  .plugin-context-label {{ font-size: 14px; font-weight: 700; color: var(--light-blue); margin-bottom: 5px; }}
  .plugin-context-note {{ font-size: 12px; color: rgba(255,255,255,.82); line-height: 1.65; }}

  /* ── Tab 2: Earnings Analysis ── */
  .skill-banner {{
    background: var(--purple); color: rgba(255,255,255,.75);
    font-size: 11px; padding: 8px 18px; border-radius: 6px;
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 18px;
  }}
  .skill-banner strong {{ color: #fff; }}
  .skill-sep {{ color: rgba(255,255,255,.35); }}

  .an-hero {{
    background: var(--purple); border-radius: 8px; padding: 22px 26px;
    color: #fff; margin-bottom: 20px;
  }}
  .an-hero-top {{ display: flex; align-items: flex-start; gap: 20px; flex-wrap: wrap; margin-bottom: 14px; }}
  .an-rating-badge {{
    background: rgba(255,255,255,.15); border: 1.5px solid rgba(255,255,255,.35);
    border-radius: 6px; padding: 6px 16px;
    font-size: 13px; font-weight: 800; letter-spacing: .08em; color: #fff;
    white-space: nowrap;
  }}
  .an-rating-badge.upgrade {{ background: var(--green); border-color: var(--green); }}
  .an-pt-block {{ flex: 1; min-width: 160px; }}
  .an-pt-val {{ font-size: 32px; font-weight: 800; color: #fff; line-height: 1; }}
  .an-pt-label {{ font-size: 11px; color: rgba(255,255,255,.6); text-transform: uppercase; letter-spacing: .06em; margin-top: 3px; }}
  .an-pt-meta {{ font-size: 12px; color: rgba(255,255,255,.75); margin-top: 6px; }}
  .an-upside {{ color: #7DCEA0; font-weight: 700; }}
  .an-hero-rationale {{ font-size: 12.5px; color: rgba(255,255,255,.85); line-height: 1.65; border-top: 1px solid rgba(255,255,255,.15); padding-top: 12px; }}
  .an-risks-header {{ font-size: 11px; font-weight: 700; color: rgba(255,255,255,.5); text-transform: uppercase; letter-spacing: .06em; margin: 12px 0 6px; }}
  .an-risks {{ list-style: none; padding: 0; margin: 0; }}
  .an-risks li {{ font-size: 11.5px; color: rgba(255,255,255,.7); padding: 3px 0 3px 14px; position: relative; }}
  .an-risks li::before {{ content: '▸'; position: absolute; left: 0; color: rgba(255,255,255,.35); }}

  .an-step-label {{
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em;
    color: var(--blue); margin-bottom: 10px;
  }}
  .an-kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  @media (max-width: 860px) {{ .an-kpi-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  .an-kpi {{
    background: var(--off-white); border: 1px solid var(--border);
    border-radius: 6px; padding: 12px 14px;
  }}
  .an-kpi-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); margin-bottom: 4px; }}
  .an-kpi-val {{ font-size: 22px; font-weight: 800; color: var(--purple); line-height: 1.1; }}
  .an-kpi-val.pos {{ color: var(--green); }}
  .an-kpi-val.neg {{ color: var(--red); }}
  .an-kpi-note {{ font-size: 11px; color: var(--muted); margin-top: 5px; line-height: 1.4; }}

  .an-flag {{
    border-left: 3px solid var(--amber); background: var(--amber-bg);
    padding: 10px 14px; border-radius: 0 6px 6px 0; margin: 10px 0;
    font-size: 12px; color: var(--text);
  }}
  .an-flag.neg {{ border-left-color: var(--red); background: var(--red-bg); }}
  .an-flag.pos {{ border-left-color: var(--green); background: var(--green-bg); }}

  .an-tbl {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  .an-tbl th {{ font-size: 10px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); font-weight: 700; padding: 5px 10px; text-align: left; border-bottom: 2px solid var(--border); }}
  .an-tbl td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  .an-tbl tr:last-child td {{ border-bottom: none; }}
  .an-tbl td.num {{ text-align: right; font-weight: 700; color: var(--purple); }}
  .an-tbl td.muted {{ color: var(--muted); font-size: 11px; }}
  .an-tbl tr.highlight td {{ background: rgba(45,32,66,.04); }}

  .dep-panel {{ border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }}
  .dep-header {{
    background: rgba(45,32,66,.06); padding: 9px 14px;
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .07em; color: var(--purple); border-bottom: 1px solid var(--border);
  }}
  .dep-row {{ display: flex; gap: 10px; padding: 9px 14px; border-bottom: 1px solid var(--border); align-items: flex-start; }}
  .dep-row:last-child {{ border-bottom: none; }}
  .dep-badge {{
    background: var(--purple); color: #fff; font-size: 10px; font-weight: 800;
    padding: 2px 7px; border-radius: 4px; white-space: nowrap; flex-shrink: 0; margin-top: 1px;
  }}
  .dep-content {{ font-size: 12px; color: var(--text); }}
  .dep-step {{ font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; margin-bottom: 2px; }}
  .dep-what {{ margin-bottom: 3px; }}
  .dep-why {{ font-size: 11px; color: var(--muted); font-style: italic; }}

  /* ── Tab 2: Tool intro card ── */
  .tool-intro {{
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0;
    border: 1px solid var(--border); border-radius: 8px; overflow: hidden; margin-bottom: 24px;
  }}
  @media (max-width: 860px) {{ .tool-intro {{ grid-template-columns: 1fr; }} }}
  .tool-panel {{ padding: 18px 20px; border-right: 1px solid var(--border); }}
  .tool-panel:last-child {{ border-right: none; }}
  .tool-panel-icon {{ font-size: 22px; margin-bottom: 8px; }}
  .tool-panel-title {{
    font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .07em; color: var(--purple); margin-bottom: 7px;
  }}
  .tool-panel-body {{ font-size: 12.5px; color: var(--text); line-height: 1.7; }}
  .tool-panel-body strong {{ color: var(--purple); }}
  .tool-panel.adapt {{ background: #fffcf0; }}
  .tool-panel.adapt .tool-panel-title {{ color: #96720a; }}
  .tool-adapt-row {{ display: flex; gap: 8px; margin-bottom: 6px; font-size: 12px; line-height: 1.45; }}
  .tool-adapt-id {{
    background: var(--purple); color: #fff; font-size: 9px; font-weight: 800;
    padding: 2px 5px; border-radius: 3px; flex-shrink: 0; margin-top: 1px;
  }}

  /* ── Tab 2: Report note layout ── */
  .rn-cover {{
    background: var(--purple); color: #fff; border-radius: 8px;
    padding: 20px 24px; margin-bottom: 20px;
  }}
  .rn-cover-top {{
    display: flex; align-items: flex-start; justify-content: space-between;
    flex-wrap: wrap; gap: 12px; margin-bottom: 14px;
  }}
  .rn-cover-company {{ font-size: 20px; font-weight: 800; letter-spacing: -.01em; }}
  .rn-cover-meta {{ font-size: 12px; opacity: .72; margin-top: 3px; }}
  .rn-cover-right {{ text-align: right; }}
  .rn-cover-date {{ font-size: 12px; opacity: .72; margin-bottom: 2px; }}
  .rn-cover-type {{ font-size: 10px; opacity: .55; text-transform: uppercase; letter-spacing: .07em; }}
  .rn-cover-stats {{
    display: flex; gap: 28px; padding-top: 14px;
    border-top: 1px solid rgba(255,255,255,.2); flex-wrap: wrap; align-items: flex-end;
  }}
  .rn-stat {{ min-width: 80px; }}
  .rn-stat-label {{ font-size: 10px; opacity: .62; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 3px; }}
  .rn-stat-val {{ font-size: 22px; font-weight: 800; line-height: 1; }}
  .rn-stat-val.up {{ color: #a3e6b8; }}
  .rn-stat-val.dn {{ color: #ff9494; }}
  .rn-stat-note {{ font-size: 11px; opacity: .68; margin-top: 3px; }}

  .rn-keypoints {{
    background: var(--off-white); border: 1px solid var(--border);
    border-left: 4px solid var(--purple); border-radius: 0 6px 6px 0;
    padding: 14px 18px; margin-bottom: 22px;
  }}
  .rn-keypoints-label {{
    font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .08em; color: var(--purple); margin-bottom: 8px;
  }}
  .rn-keypoints ul {{ margin: 0; padding-left: 16px; }}
  .rn-keypoints li {{ font-size: 13px; line-height: 1.65; margin-bottom: 5px; }}
  .rn-keypoints li:last-child {{ margin-bottom: 0; }}

  .rn-section {{ margin-bottom: 24px; }}
  .rn-section-title {{
    font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .09em; color: var(--muted); padding-bottom: 7px;
    border-bottom: 2px solid var(--border); margin-bottom: 14px;
  }}
  .rn-two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  @media (max-width: 760px) {{ .rn-two-col {{ grid-template-columns: 1fr; }} }}
  .rn-prose {{ font-size: 13px; line-height: 1.78; color: var(--text); }}
  .rn-prose p {{ margin: 0 0 10px; }}
  .rn-prose p:last-child {{ margin-bottom: 0; }}
  .rn-risks {{ margin: 0; padding-left: 18px; }}
  .rn-risks li {{ font-size: 13px; line-height: 1.65; margin-bottom: 6px; color: var(--text); }}
  .rn-risks li:last-child {{ margin-bottom: 0; }}
  .rn-callout {{
    background: #fff8e1; border-left: 3px solid #e6a817;
    padding: 10px 14px; border-radius: 0 5px 5px 0;
    font-size: 12.5px; line-height: 1.6; margin-top: 12px;
  }}
  .rn-callout.neg {{ background: #fff0f0; border-left-color: #e74c3c; }}
  .rn-callout.pos {{ background: #f0fff5; border-left-color: #27ae60; }}

  .rn-methodology {{
    border-top: 1px solid var(--border); margin-top: 28px; padding-top: 16px;
  }}
  .rn-methodology-title {{
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .07em; color: var(--muted); margin-bottom: 10px;
  }}

  /* ── Tab 3: Buy-side static cards ── */
  .bs-framing {{
    border-left: 4px solid var(--purple); background: var(--off-white);
    border-radius: 0 8px 8px 0; padding: 16px 20px; margin-bottom: 24px;
  }}
  .bs-framing-label {{
    font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .08em; color: var(--purple); margin-bottom: 6px;
  }}
  .bs-framing-text {{ font-size: 14px; font-style: italic; color: var(--text); line-height: 1.6; }}
  .bs-cards {{ display: flex; flex-direction: column; gap: 16px; margin-bottom: 32px; }}
  .bs-card {{
    border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
    border-top: 3px solid var(--purple);
  }}
  .bs-card-head {{
    padding: 12px 18px; background: var(--off-white);
    display: flex; align-items: center; gap: 12px; cursor: pointer;
  }}
  .bs-card-head:hover {{ background: #ede8f5; }}
  .bs-card-num {{
    background: var(--purple); color: #fff; font-size: 11px; font-weight: 800;
    width: 22px; height: 22px; border-radius: 50%; display: flex;
    align-items: center; justify-content: center; flex-shrink: 0;
  }}
  .bs-card-title {{ font-size: 13.5px; font-weight: 700; color: var(--text); flex: 1; }}
  .bs-card-chevron {{ font-size: 12px; color: var(--muted); transition: transform .2s; }}
  .bs-card-body {{ padding: 0 18px 0; max-height: 0; overflow: hidden; transition: max-height .3s ease, padding .3s; }}
  .bs-card-body.open {{ max-height: 800px; padding: 14px 18px 18px; }}
  .bs-card-q {{ font-size: 12px; color: var(--muted); font-style: italic; margin-bottom: 12px; line-height: 1.55; }}
  .bs-card-a {{ font-size: 13px; color: var(--text); line-height: 1.75; }}
  .bs-card-a p {{ margin: 0 0 10px; }}
  .bs-card-a p:last-child {{ margin-bottom: 0; }}
  .bs-card-a strong {{ color: var(--purple); }}

  /* ── Tab 3: dimension pill ── */
  .dim-pill {{
    display: inline-block; font-size: 9px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .07em; padding: 2px 9px; border-radius: 10px; white-space: nowrap;
    background: rgba(112,80,166,.12); color: var(--purple); flex-shrink: 0;
  }}

  /* ── Tab 3: horizon banner ── */
  .hz-banner {{
    display: flex; align-items: stretch; background: var(--purple); color: #fff;
    border-radius: 8px; padding: 14px 20px; margin-bottom: 20px; flex-wrap: wrap; gap: 0;
  }}
  .hz-banner-item {{
    font-size: 13px; font-weight: 800; letter-spacing: -.01em;
    padding: 0 20px; border-right: 1px solid rgba(255,255,255,.2); flex-shrink: 0;
  }}
  .hz-banner-item:first-child {{ padding-left: 0; }}
  .hz-banner-item:last-child {{ border-right: none; }}
  .hz-banner-label {{ font-size: 9px; font-weight: 700; opacity: .6; display: block; margin-bottom: 2px; text-transform: uppercase; letter-spacing: .07em; }}

  /* ── Tab 3: framework intro (5 dim mini-cards) ── */
  .fw-intro {{
    background: var(--off-white); border: 1px solid var(--border);
    border-radius: 8px; padding: 16px 18px; margin-bottom: 24px;
  }}
  .fw-intro-label {{
    font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .08em; color: var(--purple); margin-bottom: 12px;
  }}
  .fw-intro-dims {{
    display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px;
  }}
  @media (max-width: 860px) {{ .fw-intro-dims {{ grid-template-columns: 1fr 1fr; }} }}
  .fw-dim {{
    background: #fff; border: 1px solid var(--border); border-top: 3px solid var(--purple);
    border-radius: 6px; padding: 10px 12px;
  }}
  .fw-dim-name {{ font-size: 11px; font-weight: 800; color: var(--purple); margin-bottom: 4px; }}
  .fw-dim-def {{ font-size: 11px; color: var(--muted); line-height: 1.5; }}

  /* ── Tab 3: recommendation card ── */
  .rec-card {{
    background: var(--purple); color: #fff; border-radius: 8px;
    padding: 22px 24px; margin-bottom: 32px;
  }}
  .rec-header {{ display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 4px; }}
  .rec-label {{ font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em; opacity: .6; margin-bottom: 4px; }}
  .rec-stance {{ font-size: 30px; font-weight: 900; letter-spacing: -.02em; color: #fff; line-height: 1; }}
  .rec-stance.buy  {{ color: #7dffb0; }}
  .rec-stance.hold {{ color: #ffe77d; }}
  .rec-stance.sell {{ color: #ff8a8a; }}
  .rec-hz {{ font-size: 10px; font-weight: 700; opacity: .6; text-transform: uppercase; letter-spacing: .07em; margin-top: 6px; }}
  .rec-row {{
    padding: 10px 0; border-top: 1px solid rgba(255,255,255,.15);
    font-size: 13px; color: rgba(255,255,255,.9); line-height: 1.65;
  }}
  .rec-row-label {{
    font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .08em;
    opacity: .55; margin-bottom: 3px;
  }}

  /* ── Tab 3: Chat section ── */
  .chat-section {{
    border-top: 2px solid var(--border); padding-top: 28px; margin-top: 8px;
  }}
  .chat-section-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }}
  .chat-section-title {{ font-size: 16px; font-weight: 800; color: var(--text); }}
  .chat-server-badge {{
    font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 12px;
    background: #eee; color: #999;
  }}
  .chat-server-badge.live {{ background: #e8f8ee; color: #27ae60; }}
  .chat-subtitle {{ font-size: 12.5px; color: var(--muted); margin-bottom: 16px; line-height: 1.5; }}
  .chat-suggestions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }}
  .chat-suggestion {{
    font-size: 12px; padding: 6px 12px; border-radius: 16px;
    border: 1px solid var(--purple); color: var(--purple); background: transparent;
    cursor: pointer; transition: background .15s, color .15s;
  }}
  .chat-suggestion:hover {{ background: var(--purple); color: #fff; }}
  .chat-window {{
    border: 1px solid var(--border); border-radius: 8px; background: #fff;
    min-height: 120px; max-height: 520px; overflow-y: auto;
    padding: 16px; margin-bottom: 12px; scroll-behavior: smooth;
  }}
  .chat-empty {{
    text-align: center; color: var(--muted); font-size: 13px;
    padding: 32px 0; font-style: italic;
  }}
  .chat-msg {{ margin-bottom: 16px; }}
  .chat-msg:last-child {{ margin-bottom: 0; }}
  .chat-msg-role {{
    font-size: 10px; font-weight: 800; text-transform: uppercase;
    letter-spacing: .07em; margin-bottom: 5px;
  }}
  .chat-msg.user .chat-msg-role {{ color: var(--blue); }}
  .chat-msg.assistant .chat-msg-role {{ color: var(--purple); }}
  .chat-msg-content {{
    font-size: 13px; line-height: 1.72; color: var(--text);
    background: var(--off-white); padding: 10px 14px; border-radius: 6px;
  }}
  .chat-msg.user .chat-msg-content {{ background: #eef4fb; }}
  .chat-searching {{
    display: inline-flex; align-items: center; gap: 7px;
    font-size: 11.5px; color: #888; font-style: italic;
    background: #fff8e1; padding: 6px 12px; border-radius: 14px;
    border: 1px solid #f0d060; margin-bottom: 8px;
  }}
  .chat-searching-dot {{
    width: 6px; height: 6px; border-radius: 50%; background: #c8a000;
    animation: pulse-dot 1s infinite;
  }}
  @keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; }} 50% {{ opacity: .3; }}
  }}
  .chat-input-row {{ display: flex; gap: 8px; }}
  .chat-input {{
    flex: 1; padding: 10px 14px; border: 1px solid var(--border);
    border-radius: 6px; font-size: 13px; font-family: inherit;
    outline: none; resize: none;
  }}
  .chat-input:focus {{ border-color: var(--purple); }}
  .chat-send {{
    padding: 10px 20px; background: var(--purple); color: #fff;
    border: none; border-radius: 6px; font-size: 13px; font-weight: 700;
    cursor: pointer; white-space: nowrap; transition: opacity .15s;
  }}
  .chat-send:disabled {{ opacity: .45; cursor: default; }}
  .chat-clear-btn {{
    margin-left: auto; font-size: 11px; color: var(--muted); background: none;
    border: 1px solid var(--border); border-radius: 12px; padding: 3px 10px;
    cursor: pointer; transition: color .15s, border-color .15s;
  }}
  .chat-clear-btn:hover {{ color: var(--red); border-color: var(--red); }}
  .chat-offline-note {{
    background: #fff8e1; border: 1px solid #f0d060;
    border-radius: 6px; padding: 12px 16px; font-size: 12.5px;
    color: #7a5c00; margin-bottom: 14px; display: none;
  }}
  .chat-offline-note code {{ background: rgba(0,0,0,.07); padding: 2px 5px; border-radius: 3px; }}

  /* ── Secret sauce (Tab 3) ── */
  .sauce-outer {{
    background: var(--purple); border-radius: 8px; padding: 22px 24px; color: #fff;
  }}
  .sauce-outer h3 {{
    font-size: 13px; font-weight: 700; color: var(--light-blue);
    text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px;
  }}
  .sauce-intro {{ font-size: 13px; color: rgba(255,255,255,.85); line-height: 1.65; margin-bottom: 18px; }}
  .sauce-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px;
  }}
  @media (max-width: 860px) {{ .sauce-grid {{ grid-template-columns: 1fr 1fr; }} }}
  .sauce-card {{
    background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.15);
    border-radius: 7px; padding: 16px; border-top: 3px solid var(--light-blue);
  }}
  .sauce-card.fresh {{ border-top-color: #27AE60; }}
  .sc-label {{ font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .07em; color: var(--light-blue); margin-bottom: 8px; }}
  .sc-value {{ font-size: 22px; font-weight: 700; color: #fff; margin-bottom: 4px; }}
  .sc-note {{ font-size: 12px; color: rgba(255,255,255,.75); line-height: 1.55; }}
  .sauce-card.fresh .sc-label {{ color: #82E0AA; }}
  .sauce-card.fresh .sc-value {{ color: #82E0AA; }}
</style>
</head>
<body>

<!-- ── Page Header ─────────────────────────────────────────────────────────── -->
<div class="page-header">
  <div class="page-header-inner">
    <div>
      <h1>PANW Q3 FY26 — Earnings Dashboard</h1>
      <p>Fiscal period ending {fiscal_date_display} &nbsp;·&nbsp; Reported {report_date_display} &nbsp;·&nbsp; <em>Everyone Is Wrong About AI, Including Me</em> — Digital FutureFest &#39;26</p>
    </div>
    <div class="header-meta">
      Generated {generated_at}<br>
      13 tables · {db_row_count} rows · earnings.db
      <br><span class="header-badge">Aileron Group · Workshop Use Only</span>
    </div>
  </div>
</div>

<!-- ── Tab Navigation ─────────────────────────────────────────────────────── -->
<div style="background:var(--purple)">
  <div class="tab-nav" id="tab-nav">
    <button class="tab-btn active" onclick="showTab('data', this)">
      Baseline Data <span class="tab-label-pill">Raw Data</span>
    </button>
    <button class="tab-btn" onclick="showTab('sellside', this)">
      Claude for Financial Services <span class="tab-label-pill">Earnings Reviewer</span>
    </button>
    <button class="tab-btn" onclick="showTab('buyside', this)">
      Decision Layer <span class="tab-label-pill">Claude API</span>
    </button>
  </div>
</div>

<!-- ════════════════════════════════════════════════════════════════════════
     TAB 1 — SELL-SIDE BASELINE
     ════════════════════════════════════════════════════════════════════════ -->
<div id="tab-data" class="tab-content active">
<div class="container">

<!-- ═══ HEADLINE KPIs ══════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-header">
    <h2>Q3 FY26 — Beat / Miss vs Consensus</h2>
    <span class="tag">Reported {report_date_display}</span>
  </div>
  <div class="section-body">
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Revenue</div>
        <div class="kpi-value blue">{sg(panw_q2, 'revenue_total_m', '$M')}</div>
        <div class="kpi-note">Consensus {sg(consensus, 'revenue_consensus_m', '$M')} &nbsp;·&nbsp; beat +{fmt_cell(rev_beat, 'pct_plain')}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Non-GAAP EPS</div>
        <div class="kpi-value pos">{sg(panw_q2, 'eps_nongaap', '$')}</div>
        <div class="kpi-note">Consensus ${consensus.get('eps_consensus_nongaap', '—')} &nbsp;·&nbsp; beat +{fmt_cell(eps_beat, 'pct_plain')}</div>
      </div>
      <div class="kpi-card accent">
        <div class="kpi-label">GAAP EPS</div>
        <div class="kpi-value neu">{sg(panw_q2, 'eps_gaap', '$')}</div>
        <div class="kpi-note">~50% of non-GAAP &nbsp;·&nbsp; SBC add-back largest reconciling item</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Revenue YoY Growth</div>
        <div class="kpi-value pos">{sg(panw_q2, 'revenue_yoy_growth_pct', 'pct')}</div>
        <div class="kpi-note">See peer table for context</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">NGS ARR</div>
        <div class="kpi-value blue">${ngs_arr:.1f}B</div>
        <div class="kpi-note">+{ngs_arr_yoy:.0f}% YoY &nbsp;·&nbsp; Platform engine</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Non-GAAP OI Margin</div>
        <div class="kpi-value pos">{sg(panw_q2, 'operating_margin_nongaap_pct', 'pct_plain')}</div>
        <div class="kpi-note">GAAP OI margin {sg(panw_q2, 'operating_margin_gaap_pct', 'pct_plain')}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">After-Hours Reaction</div>
        <div class="kpi-value {'neg' if ah_chg and ah_chg < 0 else 'pos' if ah_chg and ah_chg > 0 else 'neu'}">{f'{ah_chg:+.1f}%' if ah_chg is not None else '—'}</div>
        <div class="kpi-note">Close {f'${stock_close:.2f}' if stock_close else '—'} &nbsp;·&nbsp; post-earnings move</div>
      </div>
      <div class="kpi-card accent">
        <div class="kpi-label">GAAP OI YoY Growth</div>
        <div class="kpi-value neu">{f'{gaap_oi_yoy:+.0f}%' if gaap_oi_yoy is not None else '—'}</div>
        <div class="kpi-note">⚠️ Q3 FY26 one-time charge — compare non-GAAP</div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ REVENUE & MARGINS ═══════════════════════════════════════════════════ -->
<div class="two-col">
  <div class="section">
    <div class="section-header"><h2>Revenue Mix &amp; Trend</h2><span class="tag">GAAP OI shown — spike = litigation normalisation</span></div>
    <div class="section-body">
      <div class="chart-wrap"><canvas id="revChart"></canvas></div>
      <div class="divider"></div>
      <table>
        <tr><th>Segment</th><th class="num">Q3 FY26</th><th class="num">Mix</th></tr>
        <tr>
          <td>Subscription &amp; Support</td>
          <td class="num">{sg(panw_q2, 'revenue_subscription_m', '$M')}</td>
          <td class="num pos">{100 * (panw_q2.get('revenue_subscription_m') or 0) / (panw_q2.get('revenue_total_m') or 1):.1f}%</td>
        </tr>
        <tr>
          <td>Product (Hardware)</td>
          <td class="num">{sg(panw_q2, 'revenue_product_m', '$M')}</td>
          <td class="num" style="color:var(--muted)">{100 * (panw_q2.get('revenue_product_m') or 0) / (panw_q2.get('revenue_total_m') or 1):.1f}%</td>
        </tr>
      </table>
    </div>
  </div>

  <div class="section">
    <div class="section-header"><h2>Margin Analysis — GAAP vs Non-GAAP</h2></div>
    <div class="section-body">
      <div class="chart-wrap"><canvas id="marginChart"></canvas></div>
      <div class="divider"></div>
      <table>
        <tr><th>Metric</th><th class="num">GAAP</th><th class="num">Non-GAAP</th></tr>
        <tr>
          <td>Gross Margin</td>
          <td class="num">{sg(panw_q2, 'gross_margin_gaap_pct', 'pct_plain')}</td>
          <td class="num pos">{sg(panw_q2, 'gross_margin_nongaap_pct', 'pct_plain')}</td>
        </tr>
        <tr>
          <td>Operating Margin</td>
          <td class="num">{sg(panw_q2, 'operating_margin_gaap_pct', 'pct_plain')}</td>
          <td class="num pos">{sg(panw_q2, 'operating_margin_nongaap_pct', 'pct_plain')}</td>
        </tr>
        <tr>
          <td>Operating Income</td>
          <td class="num">{sg(panw_q2, 'operating_income_gaap_m', '$M')}</td>
          <td class="num pos">{sg(panw_q2, 'operating_income_nongaap_m', '$M')}</td>
        </tr>
        <tr>
          <td>EPS (diluted)</td>
          <td class="num">{sg(panw_q2, 'eps_gaap', '$')}</td>
          <td class="num pos">{sg(panw_q2, 'eps_nongaap', '$')}</td>
        </tr>
      </table>
    </div>
  </div>
</div>

<!-- ═══ PLATFORM KPIS ══════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-header">
    <h2>Platform Metrics — Platformisation Engine</h2>
    <span class="tag">Q3 FY26</span>
  </div>
  <div class="section-body">
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">NGS ARR</div>
        <div class="kpi-value blue">${ngs_arr:.1f}B</div>
        <div class="kpi-note">+{ngs_arr_yoy:.0f}% YoY &nbsp;·&nbsp; Long-term target $15B</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">RPO</div>
        <div class="kpi-value blue">${rpo:.1f}B</div>
        <div class="kpi-note">+{rpo_yoy:.0f}% YoY &nbsp;·&nbsp; Contracted future revenue</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Deferred Revenue</div>
        <div class="kpi-value blue">${defer_total:.2f}B</div>
        <div class="kpi-note">Current + LT &nbsp;·&nbsp; Forward visibility</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Free Cash Flow</div>
        <div class="kpi-value pos">${fcf_m:.0f}M</div>
        <div class="kpi-note">FCF margin ~{fcf_margin:.0f}%</div>
      </div>
      <div class="kpi-card accent">
        <div class="kpi-label">Platformised Customers</div>
        <div class="kpi-value blue">{int(platf_cust):,}</div>
        <div class="kpi-note">Using 3+ product pillars</div>
      </div>
      <div class="kpi-card accent">
        <div class="kpi-label">XSIAM Customers</div>
        <div class="kpi-value blue">200+</div>
        <div class="kpi-note">In 24 months &nbsp;·&nbsp; $1B cumulative milestone</div>
      </div>
    </div>
    <div class="chart-wrap short" style="margin-top:16px"><canvas id="epsChart"></canvas></div>
  </div>
</div>

<!-- ═══ GUIDANCE ════════════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-header">
    <h2>Management Guidance — Issued Jun 2, 2026</h2>
    <span class="tag">Q3 FY26 + FY26 Full Year</span>
  </div>
  <div class="section-body">
    <div class="guidance-grid">
      <div class="guidance-panel">
        <div class="guidance-panel-header">Q4 FY26 Guidance</div>
        <div class="guidance-row">
          <span class="guidance-label">Revenue</span>
          <span class="guidance-value">${g_q3_rev.get('low_value', 0):,.0f}–${g_q3_rev.get('high_value', 0):,.0f}M</span>
        </div>
        <div class="guidance-row">
          <span class="guidance-label">Non-GAAP EPS</span>
          <span class="guidance-value {('pos' if (g_q3_eps.get('low_value') or 0) + (g_q3_eps.get('high_value') or 0) > 2 * (panw_q2.get('eps_nongaap') or 0) else 'neg')}">${g_q3_eps.get('low_value', 0):.2f}–${g_q3_eps.get('high_value', 0):.2f}</span>
        </div>
        <div class="guidance-row">
          <span class="guidance-label">NGS ARR</span>
          <span class="guidance-value">${g_q3_arr.get('low_value', 0):.2f}–${g_q3_arr.get('high_value', 0):.2f}B</span>
        </div>
      </div>
      <div class="guidance-panel">
        <div class="guidance-panel-header">FY26 Full-Year Guidance</div>
        <div class="guidance-row">
          <span class="guidance-label">Revenue</span>
          <span class="guidance-value">${(g_fy_rev.get('low_value') or 0)/1000:.2f}–${(g_fy_rev.get('high_value') or 0)/1000:.2f}B</span>
        </div>
        <div class="guidance-row">
          <span class="guidance-label">Non-GAAP EPS</span>
          <span class="guidance-value pos">${g_fy_eps.get('low_value', 0):.2f}–${g_fy_eps.get('high_value', 0):.2f} <span style="font-size:10px;font-weight:400">↑ raised</span></span>
        </div>
        <div class="guidance-row">
          <span class="guidance-label">FCF Margin</span>
          <span class="guidance-value">{g_fy_fcf.get('low_value', 0):.1f}–{g_fy_fcf.get('high_value', 0):.1f}%</span>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ PEER COMPARISON ═════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-header">
    <h2>Peer Comparison — Platform Consolidation Race</h2>
    <span class="tag">Most Recent Reported Quarter</span>
  </div>
  <div class="section-body">
    <table>
      <thead>
        <tr>
          <th>Company</th><th>Period</th>
          <th class="num">Revenue</th><th class="num">Rev YoY</th>
          <th class="num">ARR</th><th class="num">ARR YoY</th>
          <th class="num">Non-GAAP OI Margin</th><th class="num">GAAP Profitable</th>
        </tr>
      </thead>
      <tbody>
"""

for row in PEER_ROWS:
    sym = row['symbol']
    is_panw = sym == 'PANW'
    tr_class = 'primary-row' if is_panw else ''
    sym_class = 'sym' if is_panw else 'sym-peer'
    html += f"""        <tr class="{tr_class}">
          <td class="{sym_class}">{sym}</td>
          <td>{row.get('period', '—')}</td>
          <td class="num">{fmt_cell(row.get('rev_m'), '$M')}</td>
          <td class="num {color_cls(row.get('rev_yoy'))}">{fmt_cell(row.get('rev_yoy'), 'pct')}</td>
          <td class="num">{fmt_cell(row.get('arr_bn'), '$B')}</td>
          <td class="num {color_cls(row.get('arr_yoy'))}">{fmt_cell(row.get('arr_yoy'), 'pct')}</td>
          <td class="num {color_cls(row.get('oi_margin'))}">{fmt_cell(row.get('oi_margin'), 'pct_plain')}</td>
          <td class="num {'pos' if row.get('profitable') else 'neg'}">{fmt_cell(row.get('profitable'), 'yn')}</td>
        </tr>
"""

html += """      </tbody>
    </table>
  </div>
</div>

<!-- ═══ PEER COMPARISON CHARTS ═════════════════════════════════════════════ -->
<div class="two-col">
  <div class="section">
    <div class="section-header"><h2>Revenue Growth — YoY</h2><span class="tag">Most Recent Reported Quarter per Company</span></div>
    <div class="section-body">
      <div class="chart-wrap"><canvas id="peerRevYoyChart"></canvas></div>
    </div>
  </div>
  <div class="section">
    <div class="section-header"><h2>Non-GAAP Operating Margin</h2><span class="tag">Most Recent Reported Quarter per Company</span></div>
    <div class="section-body">
      <div class="chart-wrap"><canvas id="peerOiMarginChart"></canvas></div>
    </div>
  </div>
</div>

<!-- ═══ BUY-SIDE SIGNALS ════════════════════════════════════════════════════ -->
<div class="two-col">
  <div class="section">
    <div class="section-header"><h2>Insider Transactions — Form 4</h2><span class="tag">SEC EDGAR</span></div>
    <div class="section-body">
"""

for ins_row in insiders:
    total  = ins_row['total_value_m']
    role   = ins_row['insider_role'] or '—'
    dates  = ins_row['first_date'] if ins_row['first_date'] == ins_row['last_date'] else f"{ins_row['first_date']} – {ins_row['last_date']}"
    txn_s  = 'transaction' if ins_row['num_txn'] == 1 else 'transactions'
    html += f"""      <div class="signal-item">
        <div class="signal-header">
          <span class="signal-title">{ins_row['insider_name']}</span>
          <span class="badge badge-plan">{role}</span>
          <span class="badge badge-est">${total:.1f}M sold</span>
        </div>
        <div class="signal-meta">{dates} &nbsp;·&nbsp; {ins_row['total_shares']:,} shares &nbsp;·&nbsp; {ins_row['num_txn']} {txn_s}</div>
      </div>
"""

html += """    </div>
  </div>

  <div class="section">
    <div class="section-header"><h2>Sentiment &amp; Positioning Signals</h2><span class="tag">Jun 2026</span></div>
    <div class="section-body">
"""

_sent_by_type = {s['signal_type']: s for s in sentiment}
_si = _sent_by_type.get('short_interest', {})
_pc = _sent_by_type.get('put_call_ratio', {})

if _si:
    html += """      <div class="signal-item">
        <div class="signal-header">
          <span class="signal-title">Short Interest</span>
          <span class="badge badge-bull">actual</span>
        </div>
        <div class="signal-row">
          <span class="sr-label">Most recent report before earnings (May 15, 2026):&nbsp;</span>
        </div>
        <div class="signal-row">
          <span class="sr-label">Float short&nbsp;</span><span class="sr-val">3.48%</span>
          <span style="color:var(--muted)">&nbsp;·&nbsp;</span><span class="sr-bear">+11.1%</span><span class="sr-label"> vs prior</span>
          &nbsp;·&nbsp;<span class="sr-val">28.0M</span><span class="sr-label"> shares</span>
          &nbsp;·&nbsp;<span class="sr-val">3.4</span><span class="sr-label"> days to cover</span>
        </div>
        <div class="signal-insight">Low-to-moderate short interest; slight pre-earnings buildup (+11% in May). Not a meaningful bearish overhang. Short squeeze risk low at 3.4 days to cover.</div>
      </div>
"""

if _pc:
    html += """      <div class="signal-item">
        <div class="signal-header">
          <span class="signal-title">Put/Call Ratio</span>
          <span class="badge badge-bull">actual</span>
        </div>
        <div class="signal-row">
          <span class="sr-label">Post-earnings (Jun 3):&nbsp;</span>
          <span class="sr-label">vol&nbsp;</span><span class="sr-val">0.94</span>
          &nbsp;·&nbsp;<span class="sr-label">OI&nbsp;</span><span class="sr-val">1.00</span>
          &nbsp;·&nbsp;<span class="sr-label" style="font-style:italic">near neutral</span>
        </div>
        <div class="signal-row">
          <span class="sr-label">IV Rank&nbsp;</span><span class="sr-bear">100%</span>
          &nbsp;·&nbsp;<span class="sr-label">IV&nbsp;</span><span class="sr-val">78.5%</span>
          &nbsp;vs&nbsp;<span class="sr-label">HV&nbsp;</span><span class="sr-val">50.2%</span>
        </div>
        <div class="signal-insight">Options market near balanced post-earnings — not a panic put-buying event (contrast with Q2 FY26 post-earnings P/C of 4.02). IV at 100th percentile reflects elevated uncertainty, not directional conviction.</div>
      </div>
"""

html += f"""    </div>
  </div>
</div>

<!-- ═══ Q&A ANALYSIS ════════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-header">
    <h2>Q&amp;A Exchange Analysis — {len(qa_exchanges)} Analyst Exchanges</h2>
    <span class="tag">Jun 2, 2026 Earnings Call</span>
  </div>
  <div class="section-body">
"""

for ex in qa_exchanges:
    sig   = ex.get('key_signal', 'partial')
    bc    = {'answered': 'badge-bull', 'deflected': 'badge-bear', 'partial': 'badge-neu'}.get(sig, 'badge-neu')
    emoji = SIGNAL_BADGE.get(sig, '◑')
    topics = json.loads(ex.get('topics', '[]')) if ex.get('topics') else []
    topic_str = ' · '.join(topics)
    item_class = 'qa-item bear' if sig == 'deflected' else 'qa-item'
    html += f"""    <div class="{item_class}">
      <div class="qa-header">
        <div class="qa-num">{ex['exchange_num']}</div>
        <span class="qa-analyst">{ex['analyst_name']}</span>
        <span class="qa-firm">{ex['analyst_firm']}</span>
        <span class="badge {bc}">{emoji} {sig}</span>
        {'<span style="font-size:10px;color:var(--muted)">Topics: ' + topic_str + '</span>' if topic_str else ''}
      </div>
      <div class="qa-q">{ex['question_text']}</div>
      <div class="qa-a">{ex['answer_text']}</div>
      {'<div class="qa-note">' + ex['analytical_note'] + '</div>' if ex.get('analytical_note') else ''}
    </div>
"""

html += """  </div>
</div>

<!-- ═══ PRICE HISTORY ════════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-header">
    <h2>Price History — Monthly</h2>
    <span class="tag">Alpha Vantage · Not Split-Adjusted Pre-Dec 2024</span>
  </div>
  <div class="section-body">
    <div class="chart-wrap" style="height:200px"><canvas id="priceChart"></canvas></div>
    <div class="divider"></div>
    <table>
      <thead>
        <tr><th></th><th>Event</th><th class="num">Open</th><th class="num">High</th><th class="num">Low</th><th class="num">Close</th></tr>
      </thead>
      <tbody>
"""

for _n, ev in enumerate(price_events_sorted, 1):
    _bc = 'ev-badge primary' if ev['event_key'] == 'q3_fy26_earnings' else 'ev-badge'
    html += f"""        <tr>
          <td><span class="{_bc}">{_n}</span></td>
          <td class="event-key">{ev['event_note'] or ev['event_key'].replace('_',' ').title()}</td>
          <td class="num">${ev['open_price']:.2f}</td>
          <td class="num">${ev['high_price']:.2f}</td>
          <td class="num">${ev['low_price']:.2f}</td>
          <td class="num">${ev['close_price']:.2f}</td>
        </tr>
"""

# ── Tab 2: pre-render analysis from JSON ─────────────────────────────────────
_tab2_html = ""
if _an:
    _s5  = _an["steps"]["5_beat_miss"]
    _s6  = _an["steps"]["6_segment_geo"]
    _s7  = _an["steps"]["7_margin"]
    _s8  = _an["steps"]["8_guidance"]
    _s9  = _an["steps"]["9_estimate_revisions"]
    _s10 = _an["steps"]["10_valuation"]
    _s11 = _an["steps"]["11_rating"]

    # ── Departures: adapt rows (intro card) and full dep-panel rows ──────────
    _adapt_rows = ""
    _dep_rows   = ""
    _adapt_labels = {
        "D1": "Pre-staged data — no live web search",
        "D2": "EPS trajectory — no prior analyst model",
        "D3": "Peer multiples only — no DCF",
        "D4": "HTML output — not Word doc",
    }
    for _d in _an["departures"]:
        _short = _adapt_labels.get(_d["id"], _d["departure"])
        _adapt_rows += (
            f'        <div class="tool-adapt-row">'
            f'<span class="tool-adapt-id">{_d["id"]}</span>'
            f'<span>{_short}</span></div>\n'
        )
        _dep_rows += (
            f'    <div class="dep-row">\n'
            f'      <span class="dep-badge">{_d["id"]}</span>\n'
            f'      <div class="dep-content">\n'
            f'        <div class="dep-step">Step {_d["step"]}</div>\n'
            f'        <div class="dep-what">{_d["departure"]}</div>\n'
            f'        <div class="dep-why">Why: {_d["reason"]}</div>\n'
            f'      </div>\n'
            f'    </div>\n'
        )

    # ── Financial highlights table rows ──────────────────────────────────────
    _fin_rows = (
        f'      <tr class="highlight">'
        f'<td><strong>Non-GAAP EPS</strong></td>'
        f'<td class="num"><strong>${_s5["eps_nongaap"]["actual"]}</strong></td>'
        f'<td class="num pos"><strong>+{_s5["eps_nongaap"]["beat_pct"]}% beat</strong></td>'
        f'<td class="muted">vs ${_s5["eps_nongaap"]["consensus"]:.3f} consensus</td></tr>\n'
        f'      <tr><td>Revenue</td>'
        f'<td class="num">${_s5["revenue"]["actual_m"]:,}M</td>'
        f'<td class="num pos">+{_s5["revenue"]["yoy_growth_pct"]}% YoY</td>'
        f'<td class="muted">{("vs $" + str(int(_s5["revenue"]["consensus_m"])) + "M consensus (+" + str(_s5["revenue"]["beat_pct"]) + "% beat)") if _s5["revenue"].get("consensus_m") else "Revenue consensus not available"}</td></tr>\n'
        f'      <tr><td>NGS ARR</td>'
        f'<td class="num">${_s5["ngs_arr"]["actual_bn"]}B</td>'
        f'<td class="num pos">+{_s5["ngs_arr"]["yoy_growth_pct"]}% YoY</td>'
        f'<td class="muted">Organic +{_s5["ngs_arr"]["organic_yoy_pct"]}% · {_s6["platformized_customers"]:,} platformized customers</td></tr>\n'
        f'      <tr><td>After-Hours Reaction</td>'
        f'<td class="num neg">{_s5["stock_reaction"]["ah_change_pct"]:+.2f}%</td>'
        f'<td class="muted" colspan="2">${_s5["stock_reaction"]["close_day_of"]} close → ${_s5["stock_reaction"]["open_next_day"]} open · market sold the guidance, not the beat</td></tr>\n'
    )

    # ── Margin table rows (last 4 quarters + current) ─────────────────────────
    _traj_rows = ""
    for _t in _s7["trajectory"][-4:]:
        _hl = ' class="highlight"' if _t["period"] == "Q3_FY26" else ""
        _traj_rows += (
            f'      <tr{_hl}><td>{_t["period"].replace("_"," ")}</td>'
            f'<td class="num">{_t["gm_nongaap_pct"]}%</td>'
            f'<td class="num">{_t["oi_nongaap_pct"]}%</td>'
            f'<td class="num">{_t["fcf_margin_pct"]}%</td></tr>\n'
        )

    # ── Guidance table rows ──────────────────────────────────────────────────
    _q3_rev  = f'${_s8["q4_fy26"]["revenue_midpoint"]:,}M'
    _q3_eps  = f'${_s8["q4_fy26"]["eps_midpoint"]}'
    _q3_arr  = f'${_s8["q4_fy26"]["ngs_arr_range_bn"][0]}–{_s8["q4_fy26"]["ngs_arr_range_bn"][1]}B'
    _fy_rev  = f'${_s8["fy26_full_year"]["revenue_midpoint"]:,}M'
    _fy_eps  = f'${_s8["fy26_full_year"]["eps_midpoint"]}'

    # ── EPS beat trend rows ──────────────────────────────────────────────────
    _eps_rows = ""
    for _e in _s9["eps_history"]:
        _hl   = ' class="highlight"' if _e["period"] == "2026-04-30" else ""
        _bcls = "pos" if _e["beat_pct"] > 5 else ""
        _eps_rows += (
            f'      <tr{_hl}><td>{_e["period"]}</td>'
            f'<td class="num">${_e["estimate"]:.3f}</td>'
            f'<td class="num">${_e["actual"]:.2f}</td>'
            f'<td class="num {_bcls}">+{_e["beat_pct"]}%</td></tr>\n'
        )

    # ── Peer table rows ──────────────────────────────────────────────────────
    _peer_rows = ""
    for _p in _s10["peer_table"]:
        _hl    = ' class="highlight"' if _p["symbol"] == "PANW" else ""
        _ev_ttm = f'{_p["ev_rev_ttm_x"]:.1f}x' if _p.get("ev_rev_ttm_x") else "—"
        _ev_ntm = f'{_p["ev_rev_ntm_x"]}x'     if _p.get("ev_rev_ntm_x") else "—"
        _peer_rows += (
            f'      <tr{_hl}><td><strong>{_p["symbol"]}</strong></td>'
            f'<td class="num">{_ev_ttm}</td>'
            f'<td class="num">{_ev_ntm}</td>'
            f'<td class="num">{_p["rev_growth_pct"]}%</td>'
            f'<td class="num">{_p["oi_margin_pct"]}%</td>'
            f'<td class="muted">{_p["note"]}</td></tr>\n'
        )

    # ── Key risks ────────────────────────────────────────────────────────────
    _risks = "".join(f"      <li>{_r}</li>\n" for _r in _s11["key_risks"])

    # ── Margin trajectory (last 4 reported quarters) ─────────────────────────
    _margin_trajectory_rows = ""
    for _t in _s7["trajectory"][-4:]:
        _hl = ' class="highlight"' if _t["period"] == "Q3_FY26" else ""
        _margin_trajectory_rows += (
            f'      <tr{_hl}><td><strong>{_t["period"].replace("_", " ")}</strong></td>'
            f'<td class="num">{_t["gm_nongaap_pct"]}%</td>'
            f'<td class="num">{_t["oi_nongaap_pct"]}%</td>'
            f'<td class="num">{_t["fcf_margin_pct"]}%</td></tr>\n'
        )

    # ── Rating logic: primary trigger + moderating factors ───────────────────
    _pt    = _s11["skill_criteria"]["primary_trigger"]
    _mf    = _s11["skill_criteria"]["moderating_factors"]
    _tick  = lambda b: '<span class="pos">✓</span>' if b else '<span class="neg">✗</span>'
    _aglbl = lambda b: '<span class="neg">against upgrade</span>' if b else '<span class="pos">supports upgrade</span>'

    _trigger_rows = (
        f'      <tr><td>EPS beat ≥ 5% vs consensus</td><td class="num">+{_s5["eps_nongaap"]["beat_pct"]}%</td><td>{_tick(_pt["eps_beat_significant"])}</td></tr>\n'
        f'      <tr><td>FY guidance raised</td><td class="muted">{_s8["fy26_full_year"]["revision"]}</td><td>{_tick(_pt["fy_guidance_raised"])}</td></tr>\n'
        f'      <tr><td>Q4 EPS stepping up vs Q3 actual</td><td class="num">${_s8["q4_fy26"]["eps_midpoint"]:.2f} vs ${_s5["eps_nongaap"]["actual"]}</td><td>{_tick(_pt["q4_step_up_vs_actual"])}</td></tr>\n'
    )
    _moderator_rows = (
        f'      <tr><td>Stock reaction</td><td class="num">{_mf["stock_reaction_negative"]["data"]}</td><td>{_aglbl(_mf["stock_reaction_negative"]["value"])}</td></tr>\n'
        f'      <tr><td>Valuation vs target multiple</td><td class="num">{_mf["valuation_rich_vs_target"]["data"]}</td><td>{_aglbl(_mf["valuation_rich_vs_target"]["value"])}</td></tr>\n'
        f'      <tr><td>Risk/reward asymmetry</td><td class="num">{_mf["risk_reward_asymmetric_neg"]["data"]}</td><td>{_aglbl(_mf["risk_reward_asymmetric_neg"]["value"])}</td></tr>\n'
    )

    _tab2_html = f"""<div id="tab-sellside" class="tab-content">
<div class="container">

<!-- ── Tool intro card ──────────────────────────────────────────────────── -->
<div class="tool-intro">
  <div class="tool-panel">
    <div class="tool-panel-icon">🔬</div>
    <div class="tool-panel-title">The Tool</div>
    <div class="tool-panel-body">
      <strong>Claude for Financial Services:<br>Earnings Reviewer Agent</strong><br><br>
      A sell-side earnings update workflow that processes a quarterly earnings release
      and produces a formal research note with a rating and price target.<br><br>
      <span style="font-size:11px;color:#888">{_an["skill_version"]}</span>
    </div>
  </div>
  <div class="tool-panel">
    <div class="tool-panel-icon">📋</div>
    <div class="tool-panel-title">The Process</div>
    <div class="tool-panel-body">
      11-step workflow covering data collection, beat/miss analysis, segment review,
      margin analysis, guidance analysis, estimate revisions, valuation, and
      rating — following standard sell-side research conventions.<br><br>
      Output: <strong>Rating + Price Target</strong>, structured as a research note.
    </div>
  </div>
  <div class="tool-panel adapt">
    <div class="tool-panel-icon">⚡</div>
    <div class="tool-panel-title">4 Adaptations from Full Spec</div>
    <div class="tool-panel-body">
{_adapt_rows}      <span style="font-size:11px;color:#888">Full detail in Methodology Note below.</span>
    </div>
  </div>
</div>

<!-- ── Report cover ──────────────────────────────────────────────────────── -->
<div class="rn-cover">
  <div class="rn-cover-top">
    <div>
      <div class="rn-cover-company">Palo Alto Networks, Inc. &nbsp;<span style="font-size:13px;opacity:.7">PANW · NASDAQ</span></div>
      <div class="rn-cover-meta">Cybersecurity &nbsp;·&nbsp; Q3 FY26 Earnings Update &nbsp;·&nbsp; Jun 2, 2026</div>
    </div>
    <div class="rn-cover-right">
      <div class="rn-cover-date">Earnings call: Jun 2, 2026</div>
      <div class="rn-cover-type">Sell-side research note</div>
    </div>
  </div>
  <div class="rn-cover-stats">
    <div class="rn-stat">
      <div class="rn-stat-label">Rating</div>
      <div class="rn-stat-val">{_s11["rating_short"]}</div>
      <div class="rn-stat-note">{_s11["rating"]}</div>
    </div>
    <div class="rn-stat">
      <div class="rn-stat-label">Price Target</div>
      <div class="rn-stat-val {('up' if _s11['price_target'] >= _s11['current_price'] else 'dn')}">${_s11["price_target"]}</div>
      <div class="rn-stat-note">Range ${_s11["pt_range"][0]}–${_s11["pt_range"][1]}</div>
    </div>
    <div class="rn-stat">
      <div class="rn-stat-label">Implied Upside</div>
      <div class="rn-stat-val {('up' if _s11['implied_upside_pct'] >= 0 else 'dn')}">{_s11["implied_upside_pct"]:+.1f}%</div>
      <div class="rn-stat-note">From ${_s11["current_price"]} close</div>
    </div>
    <div class="rn-stat">
      <div class="rn-stat-label">AH Reaction</div>
      <div class="rn-stat-val dn">{_s5["stock_reaction"]["ah_change_pct"]:+.1f}%</div>
      <div class="rn-stat-note">Jun 2 close → Jun 3 open</div>
    </div>
    <div class="rn-stat">
      <div class="rn-stat-label">Mgmt Responsiveness</div>
      <div class="rn-stat-val" style="font-size:14px;line-height:1.5">
        <span style="color:#a3e6b8">{sum(1 for e in qa_exchanges if e.get('key_signal')=='answered')}✓</span> /
        <span style="opacity:.7">{sum(1 for e in qa_exchanges if e.get('key_signal')=='partial')}◑</span> /
        <span style="color:#ff9494">{sum(1 for e in qa_exchanges if e.get('key_signal')=='deflected')}✗</span>
      </div>
      <div class="rn-stat-note">{len(qa_exchanges)} exchanges · answered/partial/deflected</div>
    </div>
  </div>
</div>

<!-- ── Key Takeaways ─────────────────────────────────────────────────────── -->
<div class="rn-keypoints">
  <div class="rn-keypoints-label">Key Takeaways</div>
  <ul>
    <li><strong>Beat:</strong> Non-GAAP EPS ${_s5["eps_nongaap"]["actual"]} vs. ${_s5["eps_nongaap"]["consensus"]:.3f} consensus (+{_s5["eps_nongaap"]["beat_pct"]}%). Revenue +{_s5["revenue"]["yoy_growth_pct"]}% YoY to ${_s5["revenue"]["actual_m"]:,}M. NGS ARR +{_s5["ngs_arr"]["yoy_growth_pct"]}% to ${_s5["ngs_arr"]["actual_bn"]}B ({_s5["ngs_arr"]["organic_yoy_pct"]}% organic). {_s5["eps_nongaap"]["driver"]}</li>
    <li><strong>Reaction:</strong> Stock fell {_s5["stock_reaction"]["ah_change_pct"]:+.1f}% AH despite the beat. {_s5["stock_reaction"]["driver"]}</li>
    <li><strong>Thesis intact:</strong> Platform consolidation on track — {_s6["platformized_customers"]:,} platformized customers, RPO ${_s6["rpo_bn"]}B (+{_s6["rpo_yoy_pct"]}%). FY26 guidance raised. {_s8["key_signals"]["credibility_read"]}</li>
    <li><strong>Rating:</strong> {_s11["rating"]}, PT ${_s11["price_target"]} ({_s11["implied_upside_pct"]:+.1f}% to PT). Skill primary trigger met (EPS +{_s5["eps_nongaap"]["beat_pct"]}% beat, FY26 raised, Q4 stepping up ${round(_s8["q4_fy26"]["eps_midpoint"] - _s5["eps_nongaap"]["actual"], 2):.2f}) — the print is upgrade-eligible. Moderating factors per skill: stock {_s5["stock_reaction"]["ah_change_pct"]:+.1f}% AH (against), valuation {_s10["panw_ev_rev_ntm_x"]}x NTM vs 10–12x target (expensive), implied {_s11["implied_upside_pct"]:+.1f}% to PT (negative asymmetry). {_s11["skill_criteria"]["moderating_factors"]["count_against_upgrade"]} of 3 moderators argue against upgrade → maintain.</li>
  </ul>
</div>

<!-- ── Financial Highlights ──────────────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>Financial Highlights</h2>
    <span class="tag">Q3 FY26 · Jun 2, 2026</span>
  </div>
  <div class="section-body">
    <div class="rn-two-col">
      <div>
        <table class="an-tbl">
          <thead><tr><th>Metric</th><th>Actual</th><th>vs. Estimate</th><th>Notes</th></tr></thead>
          <tbody>
{_fin_rows}          </tbody>
        </table>
      </div>
      <div>
        <table class="an-tbl" style="margin-bottom:10px">
          <thead><tr><th>Margin (Non-GAAP)</th><th>Q3 FY26</th><th>YoY</th><th>FCF</th></tr></thead>
          <tbody>
            <tr><td>Gross Margin</td><td class="num">{_s7["q3_fy26"]["gross_margin_nongaap_pct"]}%</td><td class="num">{_s7["yoy_delta_bps"]["gross_margin_nongaap"]:+d}bps</td><td class="muted" rowspan="2" style="vertical-align:middle">FCF {_s7["q3_fy26"]["fcf_margin_pct"]}%<br><span style="font-size:10px">Q1 FY26: 68.2%</span></td></tr>
            <tr class="highlight"><td><strong>OI Margin</strong></td><td class="num"><strong>{_s7["q3_fy26"]["oi_margin_nongaap_pct"]}%</strong></td><td class="num {'pos' if _s7['yoy_delta_bps']['oi_margin_nongaap'] >= 0 else 'neg'}"><strong>{_s7["yoy_delta_bps"]["oi_margin_nongaap"]:+d}bps</strong></td></tr>
          </tbody>
        </table>
        <table class="an-tbl">
          <thead><tr><th>Margin Trend</th><th>GM</th><th>OI</th><th>FCF</th></tr></thead>
          <tbody>
{_traj_rows}          </tbody>
        </table>
      </div>
    </div>
    <div class="rn-callout neg" style="margin-top:14px">
      {_s7["driver_note"]}
    </div>
  </div>
</div>

<!-- ── Guidance ───────────────────────────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>Guidance</h2>
    <span class="tag">Next quarter + Full year</span>
  </div>
  <div class="section-body">
    <table class="an-tbl" style="margin-bottom:14px">
      <thead>
        <tr><th></th><th>Revenue</th><th>Non-GAAP EPS</th><th>NGS ARR</th><th>Signal</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Q4 FY26</strong></td>
          <td class="num">{_q3_rev} <span style="font-size:10px;color:#888">(${_s8["q4_fy26"]["revenue_range_m"][0]}–{_s8["q4_fy26"]["revenue_range_m"][1]}M)</span></td>
          <td class="num neg"><strong>{_q3_eps}</strong> <span style="font-size:10px;color:#888">(${_s8["q4_fy26"]["eps_range"][0]}–{_s8["q4_fy26"]["eps_range"][1]})</span></td>
          <td class="num">{_q3_arr}</td>
          <td class="muted">{_s8["q4_fy26"]["revision"]}</td>
        </tr>
        <tr class="highlight">
          <td><strong>FY26 Full Year</strong></td>
          <td class="num">{_fy_rev} <span style="font-size:10px;color:#888">(${_s8["fy26_full_year"]["revenue_range_m"][0]:,}–{_s8["fy26_full_year"]["revenue_range_m"][1]:,}M)</span></td>
          <td class="num pos"><strong>{_fy_eps}</strong> <span style="font-size:10px;color:#888">(${_s8["fy26_full_year"]["eps_range"][0]}–{_s8["fy26_full_year"]["eps_range"][1]})</span></td>
          <td class="muted">—</td>
          <td class="muted pos">{_s8["fy26_full_year"]["revision"]} ↑</td>
        </tr>
      </tbody>
    </table>
    <div class="rn-callout pos">
      <strong>Q4 step-up:</strong> {_s8["key_signals"]["q4_eps_vs_q3_actual"]}
    </div>
    <div class="rn-callout pos" style="margin-top:8px">
      <strong>Full-year credibility:</strong> {_s8["key_signals"]["credibility_read"]}
    </div>
    <div class="rn-callout" style="margin-top:8px">
      <strong>NGS ARR trajectory:</strong> {_s8["key_signals"]["ngs_arr_trajectory"]}
    </div>
  </div>
</div>

<!-- ── Business Highlights ───────────────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>Business Highlights</h2>
    <span class="tag">Platformization · Segment mix · Backlog</span>
  </div>
  <div class="section-body">
    <div class="rn-prose">
      <p><strong>Platformization:</strong> NGS ARR reached ${_s5["ngs_arr"]["actual_bn"]}B (+{_s5["ngs_arr"]["yoy_growth_pct"]}% reported, +{_s5["ngs_arr"]["organic_yoy_pct"]}% organic), with {_s6["platformized_customers"]:,} platformized customers. The gap between reported and organic growth reflects CyberArk and Chronosphere acquisitions. Management cited broad-based adoption across cloud security, identity, and SASE. {_s8["key_signals"]["ngs_arr_trajectory"]}</p>
      <p><strong>Revenue mix:</strong> Subscription and support represented {_s6["subscription_mix_pct"]}% of total revenue at ${_s6["subscription_revenue_m"]}M (+{_s6["subscription_yoy_pct"]}% YoY), providing a high-quality recurring base. Product revenue of ${_s6["product_revenue_m"]}M (+{_s6["product_yoy_pct"]}% YoY) reflects platform consolidation driving firewall refresh cycles.</p>
      <p><strong>Forward visibility:</strong> RPO of ${_s6["rpo_bn"]}B (+{_s6["rpo_yoy_pct"]}% YoY) provides strong 12-month revenue visibility. Free cash flow of ${_s6["fcf_m"]}M ({_s6["fcf_margin_pct"]}% margin) was seasonally low; Q1 FY26 FCF margin was 68.2% due to annual billings concentration. FY26 FCF margin guidance is {_s8["fy26_full_year"]["fcf_margin_pct"]}%.</p>
    </div>
  </div>
</div>

<!-- ── Margin Analysis ──────────────────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>Margin Analysis</h2>
    <span class="tag">Q3 FY26 vs Q3 FY25 · GAAP and Non-GAAP</span>
  </div>
  <div class="section-body">
    <table class="an-tbl" style="margin-bottom:14px">
      <thead>
        <tr><th>Margin</th><th>Q3 FY26</th><th>YoY Δ (bps)</th><th>Note</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Gross margin · Non-GAAP</strong></td>
          <td class="num">{_s7["q3_fy26"]["gross_margin_nongaap_pct"]}%</td>
          <td class="num {('pos' if _s7['yoy_delta_bps']['gross_margin_nongaap'] >= 0 else 'neg')}"><strong>{_s7["yoy_delta_bps"]["gross_margin_nongaap"]:+d}bps</strong></td>
          <td class="muted">Hardware mix vs. software dilution</td>
        </tr>
        <tr>
          <td><strong>Gross margin · GAAP</strong></td>
          <td class="num">{_s7["q3_fy26"]["gross_margin_gaap_pct"]}%</td>
          <td class="num {('pos' if _s7['yoy_delta_bps']['gross_margin_gaap'] >= 0 else 'neg')}"><strong>{_s7["yoy_delta_bps"]["gross_margin_gaap"]:+d}bps</strong></td>
          <td class="muted">Includes stock-comp and amortisation</td>
        </tr>
        <tr class="highlight">
          <td><strong>Operating margin · Non-GAAP</strong></td>
          <td class="num">{_s7["q3_fy26"]["oi_margin_nongaap_pct"]}%</td>
          <td class="num {('pos' if _s7['yoy_delta_bps']['oi_margin_nongaap'] >= 0 else 'neg')}"><strong>{_s7["yoy_delta_bps"]["oi_margin_nongaap"]:+d}bps</strong></td>
          <td class="muted">Held near prior-year — EPS beat flowed from top-line</td>
        </tr>
        <tr>
          <td><strong>Operating margin · GAAP</strong></td>
          <td class="num">{_s7["q3_fy26"]["oi_margin_gaap_pct"]}%</td>
          <td class="num {('pos' if _s7['yoy_delta_bps']['oi_margin_gaap'] >= 0 else 'neg')}"><strong>{_s7["yoy_delta_bps"]["oi_margin_gaap"]:+d}bps</strong></td>
          <td class="muted">Q3 FY26 one-time charge — see Tab 1 callout</td>
        </tr>
        <tr>
          <td><strong>Free cash flow margin</strong></td>
          <td class="num">{_s7["q3_fy26"]["fcf_margin_pct"]}%</td>
          <td class="muted">—</td>
          <td class="muted">Seasonally mid; Q1 highest due to annual billings</td>
        </tr>
      </tbody>
    </table>
    <div class="rn-prose">
      <p>{_s7["driver_note"]}</p>
    </div>
    <div style="margin-top:12px">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:6px">Non-GAAP OI margin · last 4 quarters</div>
      <table class="an-tbl" style="font-size:11.5px">
        <thead><tr><th>Quarter</th><th>GM Non-GAAP</th><th>OI Non-GAAP</th><th>FCF margin</th></tr></thead>
        <tbody>
{_margin_trajectory_rows}        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- ── EPS Trend & Estimate Context ─────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>EPS Trend</h2>
    <span class="tag">4-quarter beat history</span>
  </div>
  <div class="section-body">
    <div class="rn-two-col">
      <div>
        <table class="an-tbl">
          <thead><tr><th>Quarter End</th><th>Consensus</th><th>Actual</th><th>Beat</th></tr></thead>
          <tbody>
{_eps_rows}          </tbody>
        </table>
      </div>
      <div class="rn-prose" style="padding-top:4px">
        <p>{_s9["direction"]}</p>
        <p>FY26 EPS build: Q1–Q3 actual ${_s9["fy26_build"]["first_3q_total"]} (Q1 ${_s9["fy26_build"]["q1_actual"]} + Q2 ${_s9["fy26_build"]["q2_actual"]} + Q3 ${_s9["fy26_build"]["q3_actual"]}). FY26 midpoint ${_s9["fy26_build"]["fy26_midpoint"]} implies Q4 of ${_s9["fy26_build"]["q4_implied"]}.</p>
      </div>
    </div>
  </div>
</div>

<!-- ── Valuation & Price Target ──────────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>Valuation &amp; Price Target</h2>
    <span class="tag">NTM EV/Revenue · Peer comps</span>
  </div>
  <div class="section-body">
    <table class="an-tbl" style="margin-bottom:16px">
      <thead><tr><th>Company</th><th>EV/Rev TTM</th><th>EV/Rev NTM</th><th>Rev Growth</th><th>OI Margin</th><th>Notes</th></tr></thead>
      <tbody>
{_peer_rows}      </tbody>
    </table>
    <div class="rn-prose">
      <p>{_s10["rationale"]}</p>
      <p style="font-size:11.5px;color:#888">
        NTM revenue estimate: Q4 FY26 implied ${_s10["ntm_build"]["q4_fy26_implied_m"]:,}M + Q1 FY27 ${_s10["ntm_build"]["q1_fy27_est_m"]:,}M + Q2 FY27 ${_s10["ntm_build"]["q2_fy27_est_m"]:,}M + Q3 FY27 ${_s10["ntm_build"]["q3_fy27_est_m"]:,}M = <strong>${_s10["ntm_build"]["total_ntm_m"]:,}M</strong>. {_s10["ntm_build"]["assumption"]}.
      </p>
    </div>
  </div>
</div>

<!-- ── Rating Logic ──────────────────────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>Rating Logic</h2>
    <span class="tag">Skill Step 11 walkthrough</span>
  </div>
  <div class="section-body">
    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:6px">Primary trigger — does the print make this upgrade-eligible?</div>
    <table class="an-tbl" style="margin-bottom:14px">
      <thead><tr><th>Criterion</th><th>Reading</th><th>Met</th></tr></thead>
      <tbody>
{_trigger_rows}        <tr class="highlight"><td colspan="2"><strong>Trigger met</strong> — print is upgrade-eligible</td><td>{_tick(_pt["trigger_met"])}</td></tr>
      </tbody>
    </table>

    <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:6px">Moderating factors — should the upgrade actually happen?</div>
    <table class="an-tbl" style="margin-bottom:14px">
      <thead><tr><th>Factor (per skill)</th><th>Data</th><th>Direction</th></tr></thead>
      <tbody>
{_moderator_rows}        <tr class="highlight"><td colspan="2"><strong>Moderators against upgrade</strong></td><td class="num"><strong>{_mf["count_against_upgrade"]} of 3</strong></td></tr>
      </tbody>
    </table>

    <div class="rn-callout {('neg' if _mf['count_against_upgrade'] >= 2 else 'pos')}">
      <strong>Decision:</strong> {_s11["skill_criteria"]["decision_basis"]}
    </div>
    <div class="rn-prose" style="margin-top:12px">
      <p style="font-size:11.5px;color:#666">
        The skill (equity-research/earnings-analysis v0.1.0) says: <em>"significantly better + guidance raised → Consider upgrade,"</em> then mandates considering stock reaction, valuation, and risk/reward asymmetry before locking the rating. The rating reflects this discipline: the trigger condition is permission to consider an upgrade, not a mandate to upgrade.
      </p>
    </div>
  </div>
</div>

<!-- ── Key Risks ─────────────────────────────────────────────────────────── -->
<div class="section">
  <div class="section-header">
    <h2>Key Risks</h2>
  </div>
  <div class="section-body">
    <ul class="rn-risks">
{_risks}    </ul>
  </div>
</div>

<!-- ── Methodology Note ──────────────────────────────────────────────────── -->
<div class="rn-methodology">
  <div class="rn-methodology-title">Methodology Note — Adaptations from Skill Spec</div>
  <div class="dep-panel">
    <div class="dep-header">
      {_an["skill_version"]} &nbsp;·&nbsp; {len(_an["departures"])} adaptations from full spec &nbsp;·&nbsp; all other steps follow official workflow
    </div>
{_dep_rows}  </div>
  <div style="font-size:11px;color:#aaa;margin-top:10px">
    Analysis generated {_an["generated"]} from pre-staged PANW Q3 FY26 source files.
    Workshop use only. Not investment advice.
  </div>
</div>

</div><!-- /tab-sellside container -->
</div><!-- /tab-sellside -->
"""

# ── Tab 3: pre-render buy-side static section + chat UI ──────────────────────
import re as _re

def _md_to_html(text):
    text = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    return ''.join(f'<p>{p}</p>' for p in paras)

_tab3_html = ""
if _bs:
    _dim_short = {
        "Alpha Edge":              "Is the market&#39;s post-earnings verdict right — or is it mispricing something?",
        "Thesis Integrity":        "Are the core bull-case metrics still proving out?",
        "Guidance Credibility":    "What is management&#39;s forward signal — sandbagging, caution, or stretch?",
        "Peer Context":            "Who is winning the key strategic trade in the competitive set?",
        "Sentiment / Positioning": "Does the positioning setup create asymmetric risk/reward independent of fundamentals?",
    }
    _fw           = _bs.get("framework", {})
    _rec          = _bs.get("recommendation", {})
    _bs_generated = _bs.get("generated", "")

    # ── Horizon banner ──────────────────────────────────────────────
    _hz_banner = f"""<div class="hz-banner">
  <div class="hz-banner-item"><span class="hz-banner-label">Horizon</span>{_fw.get("horizon", "6 months").title()}</div>
  <div class="hz-banner-item"><span class="hz-banner-label">Objective</span>{_fw.get("objective", "alpha vs. market").title()}</div>
  <div class="hz-banner-item"><span class="hz-banner-label">Role</span>{_fw.get("role", "buy-side").title()}</div>
</div>"""

    # ── Framework intro (5 dimension mini-cards) ────────────────────
    _fw_dims_html = ""
    for _dim in _bs["dimensions"]:
        _dname = _dim["dimension"]
        _ddesc = _dim_short.get(_dname, "")
        _fw_dims_html += f"""
    <div class="fw-dim">
      <div class="fw-dim-name">{_dname}</div>
      <div class="fw-dim-def">{_ddesc}</div>
    </div>"""
    _fw_intro = f"""<div class="fw-intro">
  <div class="fw-intro-label">Decision Framework — Five Analytical Lenses</div>
  <div class="fw-intro-dims">{_fw_dims_html}
  </div>
</div>"""

    # ── Accordion cards ─────────────────────────────────────────────
    _bs_cards = ""
    for _i, _dim in enumerate(_bs["dimensions"], 1):
        _a_html = _md_to_html(_dim["answer"])
        _q_esc  = _dim["question"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        _dname  = _dim["dimension"]
        _bs_cards += f"""
  <div class="bs-card">
    <div class="bs-card-head" onclick="bsToggle(this)">
      <div class="bs-card-num">{_i}</div>
      <div class="bs-card-title">{_q_esc}</div>
      <div class="dim-pill">{_dname}</div>
      <div class="bs-card-chevron">&#9660;</div>
    </div>
    <div class="bs-card-body">
      <div class="bs-card-a">{_a_html}</div>
    </div>
  </div>"""

    # ── Recommendation card ─────────────────────────────────────────
    def _esc(s): return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    _stance_raw  = _rec.get("stance", "").strip()
    _stance_cls  = _stance_raw.lower()
    _rec_card = f"""<div class="rec-card">
  <div class="rec-header">
    <div>
      <div class="rec-label">Investment Recommendation</div>
      <div class="rec-stance {_stance_cls}">{_stance_raw}</div>
    </div>
    <div class="rec-hz">6-Month Horizon</div>
  </div>
  <div class="rec-row"><div class="rec-row-label">Primary Conviction</div>{_esc(_rec.get("conviction",""))}</div>
  <div class="rec-row"><div class="rec-row-label">Key Uncertainty</div>{_esc(_rec.get("uncertainty",""))}</div>
  <div class="rec-row"><div class="rec-row-label">Rationale</div>{_esc(_rec.get("rationale",""))}</div>
</div>"""

    _tab3_html = f"""<div id="tab-buyside" class="tab-content">
<div class="container">

<div class="section-header" style="margin-bottom:12px">
  <h2>Decision Layer</h2>
  <span class="tag">Pre-run &#183; {_bs_generated}</span>
</div>

{_hz_banner}

{_fw_intro}

<div class="section-header" style="margin-bottom:16px">
  <h3 style="margin:0;font-size:14px;font-weight:700;color:var(--text)">Five-Dimension Interrogation</h3>
</div>
<div class="bs-cards">
{_bs_cards}
</div>

{_rec_card}

<!-- ── Chat section ── -->
<div class="chat-section">
  <div class="chat-section-header">
    <span class="chat-section-title">Ask the Analyst</span>
    <span class="chat-server-badge" id="serverBadge">checking...</span>
    <button class="chat-clear-btn" onclick="clearChat()" title="Clear conversation">&#x21BA; Clear</button>
  </div>
  <div class="chat-subtitle">
    Backed by Claude Opus + Tavily web search. Context: sell-side analysis, buy-side framework, CRWD peer results, and PANW Q3 FY26 transcript.
  </div>

  <div class="chat-offline-note" id="offlineNote">
    <strong>Server not running.</strong> Start with: <code>python3 demo/server.py</code> then reload.
  </div>

  <div class="chat-suggestions">
    <button class="chat-suggestion" onclick="fillQ('What is the most important number to watch in Q3 FY26, and why?')">Q3 metric to watch</button>
    <button class="chat-suggestion" onclick="fillQ('How does CrowdStrike platform recovery change the PANW investment thesis?')">CRWD competitive read</button>
    <button class="chat-suggestion" onclick="fillQ('How does the 6-month view change if this is a 3-month trade instead?')">Horizon comparison</button>
    <button class="chat-suggestion" onclick="fillQ('What is the organic NGS ARR story stripped of CyberArk and Chronosphere?')">Organic ARR clarity</button>
  </div>

  <div class="chat-window" id="chatWindow">
    <div class="chat-empty" id="chatEmpty">Ask a question above to start the analysis.</div>
  </div>

  <div class="chat-input-row">
    <textarea class="chat-input" id="chatInput" rows="2" placeholder="Ask about PANW Q3 FY26..."></textarea>
    <button class="chat-send" id="chatSend" onclick="sendChat()">Send &#x2192;</button>
  </div>
</div>

<!-- ── What powers this ── -->
<div class="sauce-outer" style="margin-top:32px">
  <h3>What&#39;s powering this</h3>
  <div class="sauce-intro">
    Every response draws on pre-loaded context: sell-side research note (Steps 5&#8211;11), buy-side framework interrogation (5 dimensions), CRWD peer results, PANW Q3 FY26 earnings call transcript excerpt, and DB KPIs. Web search via Tavily is available as a tool for current market data after Jun 2, 2026.
  </div>
  <div class="sauce-grid">
    <div class="sauce-card">
      <div class="sc-label">Model</div>
      <div class="sc-value">Opus 4</div>
      <div class="sc-note">claude-opus-4-7 via Anthropic API</div>
    </div>
    <div class="sauce-card">
      <div class="sc-label">Context</div>
      <div class="sc-value">~12K</div>
      <div class="sc-note">chars of earnings context pre-loaded at server startup</div>
    </div>
    <div class="sauce-card fresh">
      <div class="sc-label">Web Search</div>
      <div class="sc-value">Live</div>
      <div class="sc-note">Tavily &#8212; triggered by Claude when current data is needed</div>
    </div>
    <div class="sauce-card">
      <div class="sc-label">Streaming</div>
      <div class="sc-value">SSE</div>
      <div class="sc-note">Server-Sent Events stream tokens as they arrive from Claude</div>
    </div>
  </div>
</div>

</div><!-- /container -->
</div><!-- /tab-buyside -->
"""
else:
    _tab3_html = """<div id="tab-buyside" class="tab-content">
<div class="container">
<div class="plugin-context">
  <div class="plugin-context-icon">&#9203;</div>
  <div>
    <div class="plugin-context-label">Decision Layer Not Found</div>
    <div class="plugin-context-note">Run: python3 demo/data/analysis/run_buyside_analysis.py</div>
  </div>
</div>
</div>
</div>"""

html += f"""      </tbody>
    </table>
    <div class="info-box" style="margin-top:12px">
      <strong>Split note</strong>
      PANW executed a 2:1 stock split on Dec 12, 2024. Pre-split prices (before Dec 2024) are stored raw —
      divide by 2 to compare on a like-for-like basis. {len(price_hist)} months of monthly OHLCV data ({price_hist[0]['month_date'][:7]} – {price_hist[-1]['month_date'][:7]}).
    </div>
  </div>
</div>

</div><!-- /tab-data container -->
</div><!-- /tab-data -->


{_tab2_html}

{_tab3_html}

<div class="page-footer">
  <strong>Aileron Group</strong> &nbsp;·&nbsp; PANW Q3 FY26 Earnings Dashboard &nbsp;·&nbsp; Workshop use only &nbsp;·&nbsp; Generated {generated_at}<br>
  Tab 1: Baseline Data (real data from DB) &nbsp;·&nbsp; Tab 2: Sell-Side Analysis (equity-research/earnings-analysis, 4 departures) &nbsp;·&nbsp; Tab 3: Decision Layer (Claude API + Tavily)<br>
  Phase B: re-run rebuild_db.py &#8594; run_earnings_analysis.py &#8594; generate_baseline.py after June 2, 2026 Q3 print
</div>

<script>
// ── Tab switching ──────────────────────────────────────────────────────────────
function showTab(name, btn) {{
  document.querySelectorAll('.tab-content').forEach(el => {{
    el.classList.remove('active');
    el.style.display = 'none';
  }});
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  var tab = document.getElementById('tab-' + name);
  tab.style.display = 'block';
  tab.classList.add('active');
  if (btn) btn.classList.add('active');
}}

// ── Price event markers (from DB price_events, numbered chronologically) ─────
var priceEventMarkers = {json.dumps(price_event_markers)};
var earningsMarkerPlugin = {{
  id: 'earningsMarkers',
  afterDraw: function(chart) {{
    if (chart.canvas.id !== 'priceChart') return;
    var ctx = chart.ctx, xScale = chart.scales.x, yScale = chart.scales.y;
    if (!xScale || !yScale) return;
    var top = yScale.top, bottom = yScale.bottom;
    priceEventMarkers.forEach(function(ev) {{
      var x = xScale.getPixelForValue(ev.idx);
      if (x == null || isNaN(x)) return;
      ctx.save();
      // Vertical line
      ctx.beginPath();
      ctx.strokeStyle = ev.primary ? '#2D2042' : '#60B5E5';
      ctx.lineWidth   = ev.primary ? 1.5 : 1;
      if (!ev.primary) ctx.setLineDash([4, 3]);
      ctx.moveTo(x, top); ctx.lineTo(x, bottom);
      ctx.stroke();
      ctx.setLineDash([]);
      // Numbered circle at top of plot area
      var r = 8, cy = top - r - 4;
      ctx.beginPath();
      ctx.arc(x, cy, r, 0, 2 * Math.PI);
      ctx.fillStyle = ev.primary ? '#2D2042' : '#60B5E5';
      ctx.fill();
      ctx.font = 'bold 8px Montserrat, sans-serif';
      ctx.fillStyle = '#fff';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(ev.num), x, cy);
      ctx.restore();
    }});
  }}
}};

// ── Charts ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {{

  var C = {{
    blue:      '#60B5E5',
    purple:    '#2D2042',
    lightBlue: '#B3DCF3',
    green:     '#1E7E34',
    red:       '#C0392B',
    amber:     '#B7770D',
    muted:     '#9099A8',
    border:    '#DDE3EC',
  }};

  Chart.defaults.color          = C.muted;
  Chart.defaults.borderColor    = C.border;
  Chart.defaults.font.family    = "'Montserrat', sans-serif";
  Chart.defaults.font.size      = 11;

  // ── Revenue trend + GAAP OI (GAAP OI spike is the teaching moment) ──────
  try {{
    new Chart(document.getElementById('revChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(rev_labels)},
        datasets: [
          {{
            label: 'Revenue ($M)',
            data: {json.dumps(rev_values)},
            backgroundColor: 'rgba(96,181,229,.25)',
            borderColor: C.blue,
            borderWidth: 1.5,
            order: 2
          }},
          {{
            label: 'GAAP OI ($M)',
            data: {json.dumps(oi_gaap)},
            type: 'line',
            borderColor: C.red,
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: C.red,
            order: 1
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ boxWidth: 10, padding: 12, font: {{ size: 11 }} }} }},
          tooltip: {{ mode: 'index', intersect: false }}
        }},
        scales: {{
          x: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }} }} }},
          y: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }}, callback: function(v) {{ return '$' + v.toFixed(0) + 'M'; }} }} }}
        }}
      }}
    }});
  }} catch(e) {{ console.error('revChart:', e); }}

  // ── GAAP vs Non-GAAP margin ──────────────────────────────────────────────
  try {{
    new Chart(document.getElementById('marginChart'), {{
      type: 'bar',
      data: {{
        labels: ['Gross Margin', 'OI Margin'],
        datasets: [
          {{
            label: 'GAAP',
            data: [{panw_q2.get('gross_margin_gaap_pct') or 0}, {panw_q2.get('operating_margin_gaap_pct') or 0}],
            backgroundColor: 'rgba(179,220,243,.5)',
            borderColor: C.lightBlue,
            borderWidth: 1.5
          }},
          {{
            label: 'Non-GAAP',
            data: [{panw_q2.get('gross_margin_nongaap_pct') or 0}, {panw_q2.get('operating_margin_nongaap_pct') or 0}],
            backgroundColor: 'rgba(45,32,66,.2)',
            borderColor: C.purple,
            borderWidth: 1.5
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ boxWidth: 10, padding: 12, font: {{ size: 11 }} }} }}
        }},
        scales: {{
          x: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }} }} }},
          y: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }}, callback: function(v) {{ return v + '%'; }} }} }}
        }}
      }}
    }});
  }} catch(e) {{ console.error('marginChart:', e); }}

  // ── EPS surprise history ─────────────────────────────────────────────────
  try {{
    new Chart(document.getElementById('epsChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(eps_labels)},
        datasets: [
          {{
            label: 'Actual Non-GAAP EPS',
            data: {json.dumps(eps_actual)},
            backgroundColor: 'rgba(96,181,229,.3)',
            borderColor: C.blue,
            borderWidth: 1.5,
            order: 2
          }},
          {{
            label: 'Estimated Non-GAAP EPS',
            data: {json.dumps(eps_est)},
            type: 'line',
            borderColor: C.amber,
            backgroundColor: 'transparent',
            borderWidth: 2,
            pointRadius: 3,
            borderDash: [4, 3],
            order: 1
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ position: 'top', labels: {{ boxWidth: 10, padding: 12, font: {{ size: 11 }} }} }},
          title: {{ display: true, text: 'Non-GAAP EPS Surprise History (4 quarters)', color: C.muted, font: {{ size: 11 }} }}
        }},
        scales: {{
          x: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }} }} }},
          y: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }} }} }}
        }}
      }}
    }});
  }} catch(e) {{ console.error('epsChart:', e); }}

  // ── Price history with earnings event markers ①②③④ ──────────────────────
  try {{
    var priceLabels = {json.dumps(price_labels)};
    var priceData   = {json.dumps(price_closes)};
    new Chart(document.getElementById('priceChart'), {{
      type: 'line',
      plugins: [earningsMarkerPlugin],
      data: {{
        labels: priceLabels,
        datasets: [{{
          label: 'Monthly Close ($)',
          data: priceData,
          borderColor: C.blue,
          backgroundColor: 'rgba(96,181,229,.08)',
          fill: true,
          borderWidth: 2,
          pointRadius: 2,
          pointBackgroundColor: C.blue,
          tension: 0.15
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        layout: {{ padding: {{ top: 24 }} }},
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ grid: {{ color: C.border }}, ticks: {{ maxTicksLimit: 12, font: {{ size: 10 }} }} }},
          y: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }}, callback: function(v) {{ return '$' + v.toFixed(0); }} }} }}
        }}
      }}
    }});
  }} catch(e) {{ console.error('priceChart:', e); }}

  // ── Peer revenue YoY growth ──────────────────────────────────────────────
  try {{
    new Chart(document.getElementById('peerRevYoyChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(peer_chart_symbols)},
        datasets: [{{
          label: 'Revenue YoY Growth (%)',
          data: {json.dumps(peer_chart_rev_yoy)},
          backgroundColor: ['rgba(45,32,66,.8)', 'rgba(96,181,229,.8)', 'rgba(30,126,52,.8)', 'rgba(183,119,13,.8)'],
          borderColor:     ['#2D2042', '#60B5E5', '#1E7E34', '#B7770D'],
          borderWidth: 1.5,
        }}]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          title: {{ display: true, text: 'Revenue YoY Growth — Most Recent Reported Quarter', color: C.muted, font: {{ size: 11 }} }}
        }},
        scales: {{
          x: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }}, callback: function(v) {{ return v + '%'; }} }} }},
          y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11, weight: '600' }} }} }}
        }}
      }}
    }});
  }} catch(e) {{ console.error('peerRevYoyChart:', e); }}

  // ── Peer non-GAAP operating margin ──────────────────────────────────────
  try {{
    new Chart(document.getElementById('peerOiMarginChart'), {{
      type: 'bar',
      data: {{
        labels: {json.dumps(peer_chart_symbols)},
        datasets: [{{
          label: 'Non-GAAP OI Margin (%)',
          data: {json.dumps(peer_chart_oi_margin)},
          backgroundColor: ['rgba(45,32,66,.8)', 'rgba(96,181,229,.8)', 'rgba(30,126,52,.8)', 'rgba(183,119,13,.8)'],
          borderColor:     ['#2D2042', '#60B5E5', '#1E7E34', '#B7770D'],
          borderWidth: 1.5,
        }}]
      }},
      options: {{
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          title: {{ display: true, text: 'Non-GAAP Operating Margin — Most Recent Reported Quarter', color: C.muted, font: {{ size: 11 }} }}
        }},
        scales: {{
          x: {{ grid: {{ color: C.border }}, ticks: {{ font: {{ size: 10 }}, callback: function(v) {{ return v + '%'; }} }} }},
          y: {{ grid: {{ display: false }}, ticks: {{ font: {{ size: 11, weight: '600' }} }} }}
        }}
      }}
    }});
  }} catch(e) {{ console.error('peerOiMarginChart:', e); }}

  // ── Tab 3: server ping on load ────────────────────────────────────────────
  pingServer();

}});

// ── Tab 3: accordion ─────────────────────────────────────────────────────────
function bsToggle(head) {{
  var body = head.nextElementSibling;
  var chev = head.querySelector('.bs-card-chevron');
  body.classList.toggle('open');
  chev.style.transform = body.classList.contains('open') ? 'rotate(180deg)' : '';
}}

// ── Tab 3: clear chat ────────────────────────────────────────────────────────
function clearChat() {{
  _chatHistory = [];
  var win = document.getElementById('chatWindow');
  if (!win) return;
  win.innerHTML = '<div class="chat-empty" id="chatEmpty">Ask a question above to start the analysis.</div>';
  var inp = document.getElementById('chatInput');
  if (inp) inp.value = '';
  var btn = document.getElementById('chatSend');
  if (btn) btn.disabled = false;
}}

// ── Tab 3: fill suggestion into input ────────────────────────────────────────
function fillQ(text) {{
  var inp = document.getElementById('chatInput');
  if (inp) {{ inp.value = text; inp.focus(); }}
}}

// ── Tab 3: chat state ─────────────────────────────────────────────────────────
var _chatHistory = [];

function _addMsg(role, contentHtml) {{
  var win = document.getElementById('chatWindow');
  var empty = document.getElementById('chatEmpty');
  if (empty) empty.style.display = 'none';
  var div = document.createElement('div');
  div.className = 'chat-msg ' + role;
  var roleDiv = document.createElement('div');
  roleDiv.className = 'chat-msg-role';
  roleDiv.textContent = role === 'user' ? 'You' : 'Analyst';
  var contentDiv = document.createElement('div');
  contentDiv.className = 'chat-msg-content';
  if (typeof DOMPurify !== 'undefined') {{
    contentDiv.innerHTML = DOMPurify.sanitize(contentHtml);
  }} else {{
    contentDiv.textContent = contentHtml.replace(/<[^>]+>/g, '');
  }}
  div.appendChild(roleDiv);
  div.appendChild(contentDiv);
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
  return contentDiv;
}}

function _renderMd(raw) {{
  var s = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  // Bold and italic
  s = s.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
  s = s.replace(/\\*(.+?)\\*/g, '<em>$1</em>');
  // Paragraphs
  s = s.split(/\\n\\n+/).map(function(p) {{ return '<p>' + p.replace(/\\n/g, '<br>') + '</p>'; }}).join('');
  return s;
}}

async function sendChat() {{
  var inp = document.getElementById('chatInput');
  var btn = document.getElementById('chatSend');
  var text = (inp.value || '').trim();
  if (!text) return;

  inp.value = '';
  btn.disabled = true;
  _addMsg('user', _renderMd(text));
  _chatHistory.push({{ role: 'user', content: text }});

  // Streaming assistant message container
  var win = document.getElementById('chatWindow');
  var div = document.createElement('div');
  div.className = 'chat-msg assistant';
  var roleDiv = document.createElement('div');
  roleDiv.className = 'chat-msg-role';
  roleDiv.textContent = 'Analyst';
  var contentDiv = document.createElement('div');
  contentDiv.className = 'chat-msg-content';
  div.appendChild(roleDiv);
  div.appendChild(contentDiv);
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;

  var rawAccum = '';
  var searchBadge = null;
  var streamDone = false;

  try {{
    var resp = await fetch('/chat', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ messages: _chatHistory }})
    }});

    var reader = resp.body.getReader();
    var decoder = new TextDecoder();
    var buf = '';

    while (!streamDone) {{
      var result = await reader.read();
      if (result.done) break;
      buf += decoder.decode(result.value, {{ stream: true }});
      var lines = buf.split('\\n');
      buf = lines.pop();

      var eventType = '';
      for (var i = 0; i < lines.length; i++) {{
        var line = lines[i];
        if (line.startsWith('event: ')) {{
          eventType = line.slice(7).trim();
        }} else if (line.startsWith('data: ')) {{
          var payload = line.slice(6);
          if (eventType === 'searching') {{
            var q = '';
            try {{ q = JSON.parse(payload).query; }} catch(e) {{}}
            if (!searchBadge) {{
              searchBadge = document.createElement('div');
              searchBadge.className = 'chat-searching';
              searchBadge.innerHTML = '<span class="chat-searching-dot"></span> Searching: <em>' + q + '</em>';
              contentDiv.appendChild(searchBadge);
              win.scrollTop = win.scrollHeight;
            }}
          }} else if (eventType === 'token') {{
            var tok = '';
            try {{ tok = JSON.parse(payload).text; }} catch(e) {{}}
            rawAccum += tok;
            var rendered = _renderMd(rawAccum);
            if (typeof DOMPurify !== 'undefined') {{
              contentDiv.innerHTML = DOMPurify.sanitize(rendered);
            }} else {{
              contentDiv.textContent = rawAccum;
            }}
            if (searchBadge && contentDiv.contains(searchBadge)) {{
              contentDiv.removeChild(searchBadge);
              searchBadge = null;
            }}
            win.scrollTop = win.scrollHeight;
          }} else if (eventType === 'done') {{
            _chatHistory.push({{ role: 'assistant', content: rawAccum }});
            streamDone = true;
            break;
          }} else if (eventType === 'error') {{
            var msg = '';
            try {{ msg = JSON.parse(payload).message; }} catch(e) {{}}
            contentDiv.textContent = 'Server error: ' + (msg || 'unknown');
            _chatHistory.pop();
            streamDone = true;
            break;
          }}
          eventType = '';
        }}
      }}
    }}
  }} catch(err) {{
    contentDiv.textContent = 'Error: ' + err.message;
    _chatHistory.pop();
  }}

  btn.disabled = false;
  win.scrollTop = win.scrollHeight;
}}

// ── Tab 3: server liveness check ─────────────────────────────────────────────
function pingServer() {{
  var badge = document.getElementById('serverBadge');
  var note  = document.getElementById('offlineNote');
  if (!badge) return;
  fetch('/chat', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ messages: [] }})
  }}).then(function(r) {{
    if (r.ok || r.status === 422) {{
      badge.textContent = 'live';
      badge.classList.add('live');
      if (note) note.style.display = 'none';
    }} else {{ throw new Error('status ' + r.status); }}
  }}).catch(function() {{
    badge.textContent = 'offline';
    if (note) note.style.display = 'block';
  }});
}}
</script>
</body>
</html>
"""

OUT_PATH.write_text(html, encoding='utf-8')

size = OUT_PATH.stat().st_size
print(f"\n  ✅ {OUT_PATH}")
print(f"     Size:      {size:,} bytes")
print(f"     Generated: {generated_at}")
print(f"     Tabs:      Baseline Data | Earnings Reviewer | Decision Layer (Claude API + Tavily)")
print(f"     Charts:    Chart.js {'embedded inline' if chartjs_js else 'CDN link (offline may fail)'}")
print(f"     Branding:  Aileron Group (Montserrat · #60B5E5 · #2D2042 · #B3DCF3)")
