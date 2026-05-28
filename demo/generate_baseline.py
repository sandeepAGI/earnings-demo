"""
generate_baseline.py — Earnings Baseline Dashboard Generator
Reads: demo/data/db/earnings.db  (built by demo/data/rebuild_db.py)
Writes: demo/earnings_baseline.html  (sibling to this script)

Three-tab output:
  Tab 1 — Baseline Data:      data tables, KPIs, charts from the DB
  Tab 2 — Claude Analysis:    placeholder until earnings reviewer process is designed,
                               tested on Q1 FY26, validated, and re-run on Q2 FY26
  Tab 3 — Buy-Side Layer:     infrastructure cards + 4 prompt cards for live demo.
                               No pre-written analytical conclusions.

Chart.js is downloaded once and embedded inline so the HTML works offline
(file:// protocol blocks external CDN scripts in Chrome/Safari).

Run: python3 demo/generate_baseline.py  (from earnings-demo root)
"""

import sqlite3, json, sys, urllib.request, tempfile
from datetime import datetime
from pathlib import Path

_HERE         = Path(__file__).parent
DB_PATH       = _HERE / "data" / "db" / "earnings.db"
OUT_PATH      = _HERE / "earnings_baseline.html"
CHARTJS_CACHE = Path(tempfile.gettempdir()) / "chartjs_440.min.js"
CHARTJS_CDN   = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'

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

PRIMARY_PERIOD = 'Q2_FY26'
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

def fmt_cell(v, fmt='', na='—'):
    if v is None: return na
    if fmt == '$M':        return f'${v:,.0f}M'
    if fmt == 'pct':       return f'{v:+.1f}%'
    if fmt == 'pct_plain': return f'{v:.1f}%'
    if fmt == '$B':        return f'${v:.2f}B'
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
_q2_fy25    = next((r for r in panw_hist if r['fiscal_period'] == 'Q2_FY25'), None)
_oi_now     = panw_q2.get('operating_income_gaap_m')
_oi_prior   = _q2_fy25.get('operating_income_gaap_m') if _q2_fy25 else None
gaap_oi_yoy = ((_oi_now - _oi_prior) / abs(_oi_prior) * 100) if (_oi_now and _oi_prior) else None
fcf_m       = kpis.get('fcf_m', {}).get('kpi_value') or 0
fcf_margin  = kpis.get('fcf_margin_pct', {}).get('kpi_value') or 0
platf_cust  = kpis.get('platformized_customers', {}).get('kpi_value') or 0
defer_total = kpis.get('deferred_rev_total_bn', {}).get('kpi_value') or 0

# Guidance lookups
g_q3_rev  = next((g for g in guidance_rows if g['issued_for_period']=='Q3_FY26' and g['metric']=='revenue_m'), {})
g_q3_eps  = next((g for g in guidance_rows if g['issued_for_period']=='Q3_FY26' and g['metric']=='eps_nongaap'), {})
g_q3_arr  = next((g for g in guidance_rows if g['issued_for_period']=='Q3_FY26' and g['metric']=='ngs_arr_bn'), {})
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
     'profitable': 1, 'period': PRIMARY_PERIOD},
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
        price_event_markers.append({'idx': _idx, 'num': _i + 1, 'primary': _ev['event_key'] == 'q2_fy26_earnings'})

# Peer comparison chart data (already in PEER_ROWS, no new queries needed)
peer_chart_symbols   = [r['symbol'] for r in PEER_ROWS]
peer_chart_rev_yoy   = [r.get('rev_yoy') for r in PEER_ROWS]
peer_chart_oi_margin = [r.get('oi_margin') for r in PEER_ROWS]

SIGNAL_BADGE = {'bullish': '▲', 'bearish': '▼', 'neutral': '●'}
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
<title>PANW Q2 FY26 — Earnings Dashboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
{chart_script_tag}
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
      <h1>PANW Q2 FY26 — Earnings Dashboard</h1>
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
      Claude Analysis <span class="tab-label-pill">Steps 5–8</span>
    </button>
    <button class="tab-btn" onclick="showTab('buyside', this)">
      Buy-Side Layer <span class="tab-label-pill">Cowork</span>
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
    <h2>Q2 FY26 — Beat / Miss vs Consensus</h2>
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
        <div class="kpi-value neu">{f'+{gaap_oi_yoy:.0f}%' if gaap_oi_yoy is not None else '—'}</div>
        <div class="kpi-note">⚠️ Prior year had one-time charges — compare non-GAAP</div>
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
        <tr><th>Segment</th><th class="num">Q2 FY26</th><th class="num">Mix</th></tr>
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
    <span class="tag">Q2 FY26</span>
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
    <h2>Management Guidance — Issued Feb 17, 2026</h2>
    <span class="tag">Q3 FY26 + FY26 Full Year</span>
  </div>
  <div class="section-body">
    <div class="guidance-grid">
      <div class="guidance-panel">
        <div class="guidance-panel-header">Q3 FY26 Guidance</div>
        <div class="guidance-row">
          <span class="guidance-label">Revenue</span>
          <span class="guidance-value">${g_q3_rev.get('low_value', 0):,.0f}–${g_q3_rev.get('high_value', 0):,.0f}M</span>
        </div>
        <div class="guidance-row">
          <span class="guidance-label">Non-GAAP EPS</span>
          <span class="guidance-value neg">${g_q3_eps.get('low_value', 0):.2f}–${g_q3_eps.get('high_value', 0):.2f}</span>
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
          <span class="guidance-value">{g_fy_fcf.get('low_value', 0):.0f}–{g_fy_fcf.get('high_value', 0):.0f}%</span>
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
    <div class="section-header"><h2>Sentiment &amp; Positioning Signals</h2><span class="tag">Feb 2026</span></div>
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
          <span class="sr-label">Two weeks pre-earnings (Jan 30 → Feb 13):&nbsp;</span>
        </div>
        <div class="signal-row">
          <span class="sr-label">Float short&nbsp;</span><span class="sr-bear">6.7%</span>
          <span style="color:var(--muted)">&nbsp;→&nbsp;</span><span class="sr-val">2.8%</span>
          &nbsp;·&nbsp;<span class="sr-bull">-50.8% covering</span>
          &nbsp;·&nbsp;<span class="sr-val">22.8M</span><span class="sr-label"> shares remaining</span>
        </div>
        <div class="signal-insight">Bullish positioning into the print — massive short covering in the final two weeks. Despite the setup, stock fell -8.5% AH.</div>
      </div>
"""

if _pc:
    html += """      <div class="signal-item">
        <div class="signal-header">
          <span class="signal-title">Put/Call Ratio</span>
          <span class="badge badge-bull">actual</span>
        </div>
        <div class="signal-row">
          <span class="sr-label">Earnings day (Feb 17):&nbsp;</span>
          <span class="sr-label">vol&nbsp;</span><span class="sr-val">1.09</span>
          &nbsp;·&nbsp;<span class="sr-label">OI&nbsp;</span><span class="sr-val">0.95</span>
          &nbsp;·&nbsp;<span class="sr-label" style="font-style:italic">not elevated pre-print</span>
        </div>
        <div class="signal-row">
          <span class="sr-label">Post-earnings (Feb 18):&nbsp;</span>
          <span class="sr-label">vol&nbsp;</span><span class="sr-bear">4.02</span>
          &nbsp;·&nbsp;<span class="sr-label" style="font-style:italic">extreme put buying</span>
        </div>
        <div class="signal-insight">Options market didn't anticipate the drop. P/C volume 4.02 day-after shows the market scrambling to reprice downside.</div>
      </div>
"""

html += """    </div>
  </div>
</div>

<!-- ═══ Q&A ANALYSIS ════════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-header">
    <h2>Q&amp;A Exchange Analysis — 10 Analyst Exchanges</h2>
    <span class="tag">Feb 17, 2026 Earnings Call</span>
  </div>
  <div class="section-body">
"""

for ex in qa_exchanges:
    sig   = ex.get('key_signal', 'neutral')
    bc    = {'bullish': 'badge-bull', 'bearish': 'badge-bear', 'neutral': 'badge-neu'}.get(sig, 'badge-neu')
    emoji = SIGNAL_BADGE.get(sig, '●')
    topics = json.loads(ex.get('topics', '[]')) if ex.get('topics') else []
    topic_str = ' · '.join(topics)
    item_class = 'qa-item bear' if sig == 'bearish' else 'qa-item'
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
    _bc = 'ev-badge primary' if ev['event_key'] == 'q2_fy26_earnings' else 'ev-badge'
    html += f"""        <tr>
          <td><span class="{_bc}">{_n}</span></td>
          <td class="event-key">{ev['event_note'] or ev['event_key'].replace('_',' ').title()}</td>
          <td class="num">${ev['open_price']:.2f}</td>
          <td class="num">${ev['high_price']:.2f}</td>
          <td class="num">${ev['low_price']:.2f}</td>
          <td class="num">${ev['close_price']:.2f}</td>
        </tr>
"""

html += f"""      </tbody>
    </table>
    <div class="info-box" style="margin-top:12px">
      <strong>Split note</strong>
      PANW executed a 2:1 stock split on Dec 12, 2024. Pre-split prices (before Dec 2024) are stored raw —
      divide by 2 to compare on a like-for-like basis. {len(price_hist)} months of monthly OHLCV data (Jan 2023 – May 2026).
    </div>
  </div>
</div>

</div><!-- /tab-data container -->
</div><!-- /tab-data -->


<!-- ════════════════════════════════════════════════════════════════════════
     TAB 2 — PLACEHOLDER
     Analysis has not been run. Process to be designed, tested on Q1 FY26,
     then re-run on Q2 FY26 before any content appears here.
     ════════════════════════════════════════════════════════════════════════ -->
<div id="tab-sellside" class="tab-content">
<div class="container">

<!-- Placeholder -->
<div class="plugin-context">
  <div class="plugin-context-icon">⏳</div>
  <div>
    <div class="plugin-context-label">Analysis Not Yet Run</div>
    <div class="plugin-context-note">
      This tab will contain real output from the Earnings Reviewer skill once the process has been
      designed, tested on Q1 FY26 (quarter ending October 31, 2024), and validated before being
      re-run on Q2 FY26. Nothing appears here until that process has been completed and reviewed.
      See STATUS.md and earnings_analysis_script.md for the planned approach.
    </div>
  </div>
</div>

<!-- STEPS 5-11 REMOVED — placeholder only until real output is generated -->
</div><!-- /tab-sellside container -->
</div><!-- /tab-sellside -->

<!-- ════════════════════════════════════════════════════════════════════════
     TAB 3 — PLACEHOLDER
     Buy-side layer not yet designed. Design to be confirmed before any
     content is added. No content here until the process is agreed and tested.
     ════════════════════════════════════════════════════════════════════════ -->
<div id="tab-buyside" class="tab-content">
<div class="container">

<div class="plugin-context">
  <div class="plugin-context-icon">⏳</div>
  <div>
    <div class="plugin-context-label">Buy-Side Layer — Not Yet Designed</div>
    <div class="plugin-context-note">
      This tab will contain the buy-side analytical layer once the process has been agreed and the
      earnings reviewer output from Tab 2 exists as a foundation to build on. No content here until
      the Tab 2 process is complete and the buy-side design is approved. See STATUS.md.
    </div>
  </div>
</div>

<!-- TAB 3 CONTENT REMOVED — placeholder only -->
</div><!-- /tab-buyside container -->
</div><!-- /tab-buyside -->

<div class="page-footer">
  <strong>Aileron Group</strong> &nbsp;·&nbsp; PANW Q2 FY26 Earnings Dashboard &nbsp;·&nbsp; Workshop use only &nbsp;·&nbsp; Generated {generated_at}<br>
  Tab 1: Baseline Data (real data from DB) &nbsp;·&nbsp; Tab 2: Placeholder — analysis not yet run &nbsp;·&nbsp; Tab 3: Placeholder — design not yet agreed<br>
  Phase B: re-run rebuild_db.py → generate_baseline.py after June 2, 2026 Q3 print
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

}});
</script>
</body>
</html>
"""

OUT_PATH.write_text(html, encoding='utf-8')

size = OUT_PATH.stat().st_size
print(f"\n  ✅ {OUT_PATH}")
print(f"     Size:      {size:,} bytes")
print(f"     Generated: {generated_at}")
print(f"     Tabs:      Baseline Data | Claude Analysis (Steps 5–8) | Buy-Side Layer")
print(f"     Charts:    Chart.js {'embedded inline' if chartjs_js else 'CDN link (offline may fail)'}")
print(f"     Branding:  Aileron Group (Montserrat · #60B5E5 · #2D2042 · #B3DCF3)")
