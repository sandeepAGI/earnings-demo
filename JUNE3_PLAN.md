# June 3 Execution Plan — Q3 FY26 Pipeline + Workshop Prep

*Written 2026-06-03. Execute after 9:30 AM ET (market open). Workshop is June 4.*

**Current state:** gather.py complete (raw files written, EPS consensus from Yahoo Finance injected). Waiting on Jun 3 market open for the AH reaction price.

---

## Phase 1 — Complete the pipeline (9:30 AM +)

### Step 1: Re-pull Jun 3 price data

Run after 9:30 AM ET. This gets the real Jun 3 open for the AH reaction KPI.

```bash
python3 -c "
import json, yfinance as yf
from pathlib import Path
RAW = Path('demo/data/raw')
t = yf.Ticker('PANW')
hist = t.history(start='2026-02-01', end='2026-07-15', interval='1d', auto_adjust=True)
records = [{'date': ts.strftime('%Y-%m-%d'), 'open': round(float(r['Open']),2), 'high': round(float(r['High']),2), 'low': round(float(r['Low']),2), 'close': round(float(r['Close']),2), 'volume': int(r['Volume'])} for ts, r in hist.iterrows()]
payload = json.loads((RAW / 'panw_price_daily.json').read_text())
payload['records'] = records
(RAW / 'panw_price_daily.json').write_text(json.dumps(payload, indent=2))
for r in records:
    if r['date'] in ('2026-06-02','2026-06-03'): print(r)
print(f'{len(records)} bars written')
"
```

**Verify:** Jun 2 close $297.18 and Jun 3 open printed. The gap is the AH reaction.

---

### Step 2: Rebuild the database

```bash
python demo/data/rebuild_db.py
```

**Verify:** No errors. Watch for the AH reaction % printed to console.

---

### Step 3: Run provenance tests

```bash
python -m pytest demo/data/tests/test_provenance.py -v
```

**Target:** 39/39 pass. If any fail, fix before proceeding.

---

### Step 4: Check organic NGS ARR before running earnings analysis

`run_earnings_analysis.py` has a `NOTE: update after reading Q3 transcript` on the
`ngs_arr_organic_yoy` variable. Before running the script, confirm whether management
called out organic NGS ARR growth separately (ex-Microsoft QRadar migration). If they
did, update the variable; if they did not distinguish it, leave as `None`.

Look for: any mention of "organic," "ex-QRadar," or "ex-Microsoft" in the transcript.

```bash
grep -i "organic\|ex-qradar\|ex-microsoft\|excluding" demo/data/raw/panw_q3fy26_transcript.txt | head -20
```

---

### Step 5: Run sell-side earnings analysis

```bash
python demo/data/analysis/run_earnings_analysis.py
```

**Verify:** `panw_q3fy26_earnings_analysis.json` written. Check printed rating, PT, and
implied upside — these will be live on stage.

---

### Step 6: Run buy-side framework analysis

```bash
python demo/data/analysis/run_buyside_analysis.py
```

**Verify:** `panw_q3fy26_buyside_analysis.json` written. Note the recommendation stance
(Buy/Hold/Sell) — this is the Tab 3 headline.

---

### Step 7: Generate the HTML dashboard

```bash
python3 demo/generate_baseline.py
```

Open `demo/earnings_baseline.html` in a browser. Spot-check all three tabs:

- **Tab 1:** AH reaction KPI shows correct % (Jun 2 close → Jun 3 open). Revenue $3,002M.
  NGS ARR $8.13B. Platformized customers 2,280. Sentiment cards show "placeholder" (expected
  until Step 9).
- **Tab 2:** Rating, PT, and EPS beat populated from Q3 FY26 JSON. Departures panel visible.
- **Tab 3:** Horizon banner visible. 5 accordion cards with Q3-specific questions. Recommendation
  card shows stance from buy-side analysis.

---

### Step 8: Commit the data build

```bash
git add demo/data/raw/ demo/data/analysis/ demo/earnings_baseline.html
git commit -m "STAGE: Q3 FY26 data build complete — pipeline run June 3"
```

---

## Phase 2 — Sentiment data capture (Playwright)

### Step 9: Capture real short interest + put/call ratio

Both `panw_q3fy26_short_interest.txt` and `panw_q3fy26_put_call.txt` are placeholders.
Dashboard sentiment cards show "placeholder" confidence until these are updated.

**Short interest (MarketBeat):**
Navigate to MarketBeat PANW short interest page. Capture:
- Short interest as % of float (most recent settlement)
- Shares short
- Change from prior period

Save to `demo/data/raw/panw_q3fy26_short_interest.txt`. Replace placeholder content.

**Put/call ratio (Barchart):**
Navigate to `barchart.com/stocks/quotes/PANW/put-call-ratios`. Capture:
- P/C volume ratio around Jun 2 (pre-earnings) and Jun 3 (post-earnings)

Save to `demo/data/raw/panw_q3fy26_put_call.txt`. Replace placeholder content.

After both files are updated:

```bash
python demo/data/rebuild_db.py
python3 demo/generate_baseline.py
```

Verify sentiment cards in Tab 1 now show "actual" confidence, not "placeholder."

---

## Phase 3 — Documentation updates

### Step 10: Update SCHEMA.md

`demo/data/SCHEMA.md` is fully Q2 FY26. After pipeline validates, update:
- Header: "Target quarter: PANW Q3 FY26 — fiscal date ending 2026-04-30, reported 2026-06-02"
- Build Contract Rule 4: Form 4 window → "2026-02-01 to 2026-06-02"
- Signed-Off Supplements table: replace Q2 FY26 values with Q3 FY26 actuals from supplemental
  (gross margin 75.8%, FCF $788M, deferred rev $7.113B + $6.492B, platformized customers 2,280,
  NGS ARR $8.13B, RPO $18.4B)
- Raw Files Summary: replace `panw_q2fy26_*` filenames with `panw_q3fy26_*`
- Table descriptions: update primary quarter references throughout

### Step 11: Update earnings_analysis_script.md

`demo/earnings_analysis_script.md` is the Cowork data package for the live demo. It
contains hardcoded Q2 FY26 values. Replace the DATA PACKAGE block with Q3 FY26 actuals.
This is the highest-priority doc update — it's what gets pasted live on stage.

Key Q3 FY26 values for the data package:
- Revenue: $3,002M (+31.1% YoY)
- Non-GAAP EPS: $0.85 vs $0.80 consensus (+6.25% beat)
- Non-GAAP gross margin: 75.8%
- Non-GAAP OI margin: 27.1%
- FCF: $788M (26.2% margin)
- NGS ARR: $8.13B (+60% YoY)
- Platformized customers: 2,280
- RPO: $18.4B (+36% YoY)
- Q4 FY26 guidance: $3,345–$3,355M revenue, $0.96–$0.98 EPS
- AH reaction: Jun 2 close → Jun 3 open (value from Step 1)

### Step 12: Update EARNINGS-ANALYSIS-GUIDE.md

Replace all Q2 FY26 source file references with Q3 FY26 equivalents. Update the DB
description (path, row count). Update consensus values ($0.7793 → $0.80). Update
Form 4 window dates.

### Step 13: Minor doc touches

- `demo/demo_approach.md`: change "PANW reports June 2. Transcript available ~48 hours
  before the event" → past tense (already happened)
- `CLAUDE.md`: "Current State" paragraph — remove "pipeline rebuild paused" note

---

## Phase 4 — Test the live server + final prep

### Step 14: Test Tab 3 chat end to end

```bash
python3 demo/server.py
# Open http://localhost:8000 in browser
```

Test:
1. Tab 3 loads with "online" badge
2. Click a suggestion chip — confirm SSE streaming works
3. Ask a question requiring web search — confirm Tavily search fires and result streams

### Step 15: Final commit

```bash
git add .
git commit -m "Workshop ready: Q3 FY26 dashboard + docs complete"
```

### Step 16: Logistics

- [ ] Buy MacBook Pro adapter before June 4
- [ ] Confirm QR codes in session deck point to correct Forms URLs (settling poll + Beat 3)
- [ ] Fallback: confirm a pre-recorded or scripted fallback option exists for the demo

---

## Summary checklist

| # | Step | Blocker |
|---|------|---------|
| 1 | Re-pull Jun 3 price | Market open 9:30 AM |
| 2 | rebuild_db.py | Step 1 |
| 3 | Provenance tests | Step 2 |
| 4 | Check organic ARR note in transcript | None |
| 5 | run_earnings_analysis.py | Steps 3–4 |
| 6 | run_buyside_analysis.py | Step 5 |
| 7 | generate_baseline.py + browser check | Step 6 |
| 8 | Commit data build | Step 7 |
| 9 | Playwright sentiment capture | None (parallel with above) |
| 10 | Update SCHEMA.md | Step 8 |
| 11 | Update earnings_analysis_script.md | Step 8 |
| 12 | Update EARNINGS-ANALYSIS-GUIDE.md | Step 8 |
| 13 | Minor doc touches | None |
| 14 | Test Tab 3 server | Steps 10–13 |
| 15 | Final commit | Step 14 |
| 16 | Buy adapter, confirm QR codes | None |
