import json


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


data = json.load(open(HERE / 'dashboard_data.json'))
kpi = data['kpi']
risk_bands = data['risk_bands']
grade_comp = data['grade_comparison']
decile = data['decile_lift']
purpose = data['purpose_rates']
watchlist = data['watchlist']

def money(v, digits=1):
    v = float(v)
    if abs(v) >= 1e9:
        return f"${v/1e9:.{digits}f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.{digits}f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:.{digits}f}K"
    return f"${v:,.0f}"

def pct(v, digits=1):
    return f"{v*100:.{digits}f}%"

# ---------- SVG chart builders ----------

ORDINAL_BLUE = ["#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]  # 6 steps light
ORDINAL_BLUE_DARK = ["#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#1c5cab", "#104281"]

def risk_band_chart():
    W, H = 620, 320
    pad_l, pad_r, pad_t, pad_b = 130, 70, 10, 10
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(risk_bands)
    bar_h = 24
    gap = (plot_h - n*bar_h) / (n-1) if n > 1 else 0
    max_count = max(b['count'] for b in risk_bands)
    bars = []
    for i, b in enumerate(risk_bands):
        y = pad_t + i*(bar_h+gap)
        w = plot_w * b['count'] / max_count
        color = f"var(--band-{i})"
        bars.append(f'''
        <g class="rb-bar" data-tip="{b['band']}: {b['count']:,} loans &middot; {money(b['exposure'])} exposure &middot; avg PD {pct(b['avg_pd'])}">
          <rect x="{pad_l}" y="{y}" width="{plot_w}" height="{bar_h}" fill="var(--track)" rx="4"/>
          <rect x="{pad_l}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{color}" rx="4"/>
          <text x="{pad_l-10}" y="{y+bar_h/2+4}" text-anchor="end" class="axis-label">{b['band'].split(' - ')[1]}</text>
          <text x="{pad_l+w+8}" y="{y+bar_h/2+4}" class="val-label">{b['count']:,}</text>
        </g>''')
    return f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-label="Loan count by risk band">{"".join(bars)}</svg>'

def grade_chart():
    W, H = 620, 320
    pad_l, pad_r, pad_t, pad_b = 40, 10, 20, 40
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(grade_comp)
    group_w = plot_w / n
    bar_w = 16
    max_v = max(max(g['historical_default_rate'], g['current_avg_pd']) for g in grade_comp) * 1.15
    bars = []
    gridlines = []
    for gy in [0, 0.25, 0.5, 0.75]:
        if gy > max_v: continue
        y = pad_t + plot_h - (gy/max_v)*plot_h
        gridlines.append(f'<line x1="{pad_l}" x2="{W-pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="gridline"/><text x="{pad_l-6}" y="{y+3:.1f}" text-anchor="end" class="axis-label">{gy*100:.0f}%</text>')
    for i, g in enumerate(grade_comp):
        cx = pad_l + i*group_w + group_w/2
        h1 = (g['historical_default_rate']/max_v)*plot_h
        h2 = (g['current_avg_pd']/max_v)*plot_h
        x1 = cx - bar_w - 2
        x2 = cx + 2
        y1 = pad_t + plot_h - h1
        y2 = pad_t + plot_h - h2
        bars.append(f'''
        <g class="grade-bar" data-tip="Grade {g['grade']}: historical default {pct(g['historical_default_rate'])} &middot; current avg PD {pct(g['current_avg_pd'])} ({g['current_count']:,} active loans)">
          <rect x="{x1:.1f}" y="{y1:.1f}" width="{bar_w}" height="{h1:.1f}" fill="var(--series-1)" rx="3"/>
          <rect x="{x2:.1f}" y="{y2:.1f}" width="{bar_w}" height="{h2:.1f}" fill="var(--series-2)" rx="3"/>
          <text x="{cx:.1f}" y="{pad_t+plot_h+18}" text-anchor="middle" class="axis-label">{g['grade']}</text>
        </g>''')
    return f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-label="Historical default rate vs current average PD by grade">{"".join(gridlines)}{"".join(bars)}</svg>'

def lift_chart():
    W, H = 620, 320
    pad_l, pad_r, pad_t, pad_b = 44, 16, 16, 34
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(decile)
    max_v = max(max(d['avg_pd'], d['default_rate']) for d in decile) * 1.1
    def pt(i, v):
        x = pad_l + (i/(n-1))*plot_w
        y = pad_t + plot_h - (v/max_v)*plot_h
        return x, y
    pred_pts = [pt(i, d['avg_pd']) for i, d in enumerate(decile)]
    actual_pts = [pt(i, d['default_rate']) for i, d in enumerate(decile)]
    def path(pts):
        return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    gridlines = []
    for gy in [0, 0.2, 0.4, 0.6]:
        if gy > max_v: continue
        y = pad_t + plot_h - (gy/max_v)*plot_h
        gridlines.append(f'<line x1="{pad_l}" x2="{W-pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="gridline"/><text x="{pad_l-6}" y="{y+3:.1f}" text-anchor="end" class="axis-label">{gy*100:.0f}%</text>')
    xlabels = "".join(f'<text x="{pt(i,0)[0]:.1f}" y="{pad_t+plot_h+18}" text-anchor="middle" class="axis-label">{i+1}</text>' for i in range(n))
    dots_pred_parts = []
    for i, (x, y) in enumerate(pred_pts):
        tip = f"Decile {i+1}: predicted PD {pct(decile[i]['avg_pd'])}"
        dots_pred_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--series-1)" stroke="var(--surface-1)" stroke-width="2" class="dot" data-tip="{tip}"/>')
    dots_pred = "".join(dots_pred_parts)
    dots_act_parts = []
    for i, (x, y) in enumerate(actual_pts):
        tip = f"Decile {i+1}: actual default rate {pct(decile[i]['default_rate'])}"
        dots_act_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var(--series-2)" stroke="var(--surface-1)" stroke-width="2" class="dot" data-tip="{tip}"/>')
    dots_act = "".join(dots_act_parts)
    return f'''<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-label="Predicted PD vs actual default rate by risk decile">
      {"".join(gridlines)}
      <path d="{path(pred_pts)}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      <path d="{path(actual_pts)}" fill="none" stroke="var(--series-2)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      {dots_pred}{dots_act}
      {xlabels}
      <text x="{pad_l+plot_w/2:.1f}" y="{H-2}" text-anchor="middle" class="axis-label">Risk decile (10 = highest predicted risk)</text>
    </svg>'''

def purpose_chart():
    W, H = 620, 340
    pad_l, pad_r, pad_t, pad_b = 150, 60, 10, 10
    plot_w = W - pad_l - pad_r
    plot_h = H - pad_t - pad_b
    n = len(purpose)
    bar_h = 18
    gap = (plot_h - n*bar_h)/(n-1)
    max_v = max(p['rate'] for p in purpose) * 1.05
    bars = []
    for i, p in enumerate(purpose):
        y = pad_t + i*(bar_h+gap)
        w = plot_w * p['rate']/max_v
        bars.append(f'''
        <g class="purpose-bar" data-tip="{p['purpose'].replace('_',' ').title()}: {pct(p['rate'])} default rate &middot; {p['count']:,} loans">
          <rect x="{pad_l}" y="{y}" width="{plot_w}" height="{bar_h}" fill="var(--track)" rx="3"/>
          <rect x="{pad_l}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="var(--series-1)" rx="3"/>
          <text x="{pad_l-8}" y="{y+bar_h/2+4}" text-anchor="end" class="axis-label">{p['purpose'].replace('_',' ').title()}</text>
          <text x="{pad_l+w+8}" y="{y+bar_h/2+4}" class="val-label">{pct(p['rate'])}</text>
        </g>''')
    return f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-label="Historical default rate by loan purpose">{"".join(bars)}</svg>'

def watchlist_rows():
    rows = []
    for w in watchlist:
        band_idx = int(w['risk_band'][0]) - 1
        rows.append(f'''<tr>
          <td class="mono">{w['id']}</td>
          <td>{money(w['loan_amnt'],1)}</td>
          <td><span class="grade-chip">{w['grade']}{w['sub_grade'][-1]}</span></td>
          <td>{w['purpose'].replace('_',' ').title()}</td>
          <td>{w['addr_state']}</td>
          <td class="mono num">{pct(w['pd'])}</td>
          <td><span class="band-chip band-{band_idx}">{w['risk_band'].split(' - ')[1]}</span></td>
          <td class="mono num">{money(w['expected_loss'],1)}</td>
        </tr>''')
    return "".join(rows)

band_css_vars_light = "\n".join(f"  --band-{i}: {c};" for i, c in enumerate(ORDINAL_BLUE))
band_css_vars_dark = "\n".join(f"  --band-{i}: {c};" for i, c in enumerate(ORDINAL_BLUE_DARK))

html = f'''<title>Credit Risk Monitor</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root {{
  color-scheme: light;
  --surface-1: #fcfcfb;
  --page: #f4f2ee;
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
  --text-muted: #898781;
  --gridline: #e1e0d9;
  --border: rgba(11,11,11,0.10);
  --track: #eef1f6;
  --series-1: #2a78d6;
  --series-2: #eb6834;
  --good: #0ca30c;
  --warning: #fab219;
  --serious: #ec835a;
  --critical: #d03b3b;
{band_css_vars_light}
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface-1: #1a1a19;
    --page: #0d0d0d;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted: #898781;
    --gridline: #2c2c2a;
    --border: rgba(255,255,255,0.10);
    --track: #22262c;
    --series-1: #3987e5;
    --series-2: #d95926;
    --good: #0ca30c;
    --warning: #fab219;
    --serious: #ec835a;
    --critical: #e66767;
{band_css_vars_dark}
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface-1: #1a1a19;
  --page: #0d0d0d;
  --text-primary: #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted: #898781;
  --gridline: #2c2c2a;
  --border: rgba(255,255,255,0.10);
  --track: #22262c;
  --series-1: #3987e5;
  --series-2: #d95926;
  --good: #0ca30c;
  --warning: #fab219;
  --serious: #ec835a;
  --critical: #e66767;
{band_css_vars_dark}
}}

* {{ box-sizing: border-box; }}
body {{
  background: var(--page);
  color: var(--text-primary);
  font-family: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  padding: 0 20px;
  padding-block: 28px;
  max-width: 1180px;
  margin: 0 auto;
}}
h1, h2, h3 {{ text-wrap: balance; margin: 0; }}
.page-header {{ display:flex; flex-direction:column; gap:4px; margin-bottom: 24px; }}
.eyebrow {{ font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); font-weight: 600; }}
.page-header h1 {{ font-size: 28px; font-weight: 700; }}
.page-header p {{ color: var(--text-secondary); font-size: 14px; margin: 2px 0 0; }}

.kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.kpi-tile {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }}
.kpi-label {{ font-size: 12px; color: var(--text-secondary); margin-bottom: 6px; }}
.kpi-value {{ font-size: 26px; font-weight: 600; letter-spacing: -0.01em; }}
.kpi-sub {{ font-size: 12px; color: var(--text-muted); margin-top: 4px; }}

.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }}
@media (max-width: 760px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}

.card {{ background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px 14px; position: relative; }}
.card h3 {{ font-size: 15px; font-weight: 600; margin-bottom: 2px; }}
.card .card-sub {{ font-size: 12.5px; color: var(--text-secondary); margin: 0 0 12px; }}
.legend {{ display:flex; gap:16px; font-size:12px; color:var(--text-secondary); margin-bottom:8px; }}
.legend span {{ display:inline-flex; align-items:center; gap:6px; }}
.swatch {{ width:10px; height:10px; border-radius:2px; display:inline-block; }}

.chart-svg {{ width: 100%; height: auto; overflow: visible; }}
.axis-label {{ font-size: 11px; fill: var(--text-muted); font-family: "IBM Plex Mono", monospace; }}
.val-label {{ font-size: 11px; fill: var(--text-secondary); font-family: "IBM Plex Mono", monospace; }}
.gridline {{ stroke: var(--gridline); stroke-width: 1; }}
.rb-bar, .grade-bar, .purpose-bar, .dot {{ cursor: pointer; }}
.rb-bar rect, .purpose-bar rect {{ transition: opacity .12s; }}
.rb-bar:hover rect:nth-child(2), .purpose-bar:hover rect:nth-child(2) {{ opacity: 0.8; }}
.grade-bar:hover rect {{ opacity: 0.8; }}

table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); font-weight: 600; padding: 8px 10px; border-bottom: 1px solid var(--gridline); }}
td {{ padding: 9px 10px; border-bottom: 1px solid var(--gridline); color: var(--text-primary); }}
td.mono {{ font-family: "IBM Plex Mono", monospace; font-size: 12.5px; }}
td.num {{ font-variant-numeric: tabular-nums; text-align: right; }}
th:last-child, td.num {{ text-align: right; }}
.table-wrap {{ overflow-x: auto; }}
.grade-chip {{ display:inline-block; font-family:"IBM Plex Mono",monospace; font-size:11.5px; background:var(--track); border-radius:5px; padding:2px 6px; }}
.band-chip {{ display:inline-block; font-size:11.5px; border-radius:20px; padding:2px 9px; font-weight:600; }}
.band-0 {{ background: color-mix(in srgb, var(--good) 18%, transparent); color: var(--good); }}
.band-1 {{ background: color-mix(in srgb, var(--good) 18%, transparent); color: var(--good); }}
.band-2 {{ background: color-mix(in srgb, var(--warning) 22%, transparent); color: #8a6200; }}
.band-3 {{ background: color-mix(in srgb, var(--serious) 22%, transparent); color: #a1441f; }}
.band-4 {{ background: color-mix(in srgb, var(--critical) 18%, transparent); color: var(--critical); }}
.band-5 {{ background: color-mix(in srgb, var(--critical) 26%, transparent); color: var(--critical); }}
:root:not([data-theme="light"]) .band-2 {{ color: var(--warning); }}
:root:not([data-theme="light"]) .band-3 {{ color: var(--serious); }}
:root[data-theme="dark"] .band-2 {{ color: var(--warning); }}
:root[data-theme="dark"] .band-3 {{ color: var(--serious); }}

.footer {{ margin-top: 20px; font-size: 12px; color: var(--text-muted); border-top: 1px solid var(--gridline); padding-top: 14px; }}

#tooltip {{
  position: fixed; pointer-events: none; z-index: 50;
  background: var(--text-primary); color: var(--surface-1);
  font-size: 12px; padding: 6px 10px; border-radius: 6px;
  max-width: 260px; opacity: 0; transition: opacity .1s;
  transform: translate(-50%, -100%);
}}
</style>

<div class="page-header">
  <div class="eyebrow">Portfolio &middot; PD Model v1</div>
  <h1>Credit Risk Monitor</h1>
  <p>Active loan book scored for probability of default &middot; {kpi['n_training']:,}-loan training population &middot; generated from HistGradientBoosting PD model</p>
</div>

<div class="kpi-row">
  <div class="kpi-tile">
    <div class="kpi-label">Active loans scored</div>
    <div class="kpi-value">{kpi['n_scored']:,}</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Total exposure</div>
    <div class="kpi-value">{money(kpi['total_exposure'])}</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Portfolio avg PD</div>
    <div class="kpi-value">{pct(kpi['avg_pd'])}</div>
    <div class="kpi-sub">vs {pct(kpi['historical_default_rate'])} historical base rate</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Expected loss (LGD 100%)</div>
    <div class="kpi-value">{money(kpi['expected_loss'])}</div>
    <div class="kpi-sub">upper bound, no recovery data</div>
  </div>
  <div class="kpi-tile">
    <div class="kpi-label">Model AUC / KS</div>
    <div class="kpi-value">{kpi['auc']:.3f}</div>
    <div class="kpi-sub">KS {kpi['ks']:.3f} &middot; held-out test set</div>
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <h3>Active loans by risk band</h3>
    <p class="card-sub">{kpi['n_scored']:,} loans currently outstanding, grouped by predicted PD</p>
    {risk_band_chart()}
  </div>
  <div class="card">
    <h3>Default rate by grade: historical vs current book</h3>
    <p class="card-sub">Historical = actual outcomes (training set) &middot; Current = model-predicted avg PD</p>
    <div class="legend">
      <span><span class="swatch" style="background:var(--series-1)"></span>Historical (actual)</span>
      <span><span class="swatch" style="background:var(--series-2)"></span>Current book (predicted)</span>
    </div>
    {grade_chart()}
  </div>
</div>

<div class="grid-2">
  <div class="card">
    <h3>Model calibration &mdash; lift by decile</h3>
    <p class="card-sub">Predicted PD tracks actual default rate closely across risk deciles (test set)</p>
    <div class="legend">
      <span><span class="swatch" style="background:var(--series-1)"></span>Predicted PD</span>
      <span><span class="swatch" style="background:var(--series-2)"></span>Actual default rate</span>
    </div>
    {lift_chart()}
  </div>
  <div class="card">
    <h3>Historical default rate by purpose</h3>
    <p class="card-sub">Training set, sorted highest to lowest risk</p>
    {purpose_chart()}
  </div>
</div>

<div class="card">
  <h3>Highest-risk active loans (watchlist)</h3>
  <p class="card-sub">Top 20 by predicted PD, out of {kpi['n_scored']:,} active loans</p>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>Loan ID</th><th>Amount</th><th>Grade</th><th>Purpose</th><th>State</th>
        <th>PD</th><th>Risk band</th><th>Expected loss</th>
      </tr></thead>
      <tbody>{watchlist_rows()}</tbody>
    </table>
  </div>
</div>

<div class="footer">
  PD model: HistGradientBoostingClassifier, trained on {kpi['n_training']:,} completed loans (Fully Paid / Charged Off), validated on a 25% held-out test set. Origination-time features only &mdash; post-origination fields (received payments, updated FICO) excluded to prevent leakage. Expected loss assumes 100% loss given default (no recovery data available), so is a conservative upper bound. Full methodology in the accompanying report and Excel workbook.
</div>

<div id="tooltip"></div>
<script>
(function(){{
  var tip = document.getElementById('tooltip');
  document.querySelectorAll('[data-tip]').forEach(function(el){{
    el.addEventListener('mousemove', function(e){{
      tip.textContent = el.getAttribute('data-tip');
      tip.style.left = e.clientX + 'px';
      tip.style.top = (e.clientY - 10) + 'px';
      tip.style.opacity = 1;
    }});
    el.addEventListener('mouseleave', function(){{ tip.style.opacity = 0; }});
  }});
}})();
</script>
'''

with open(HERE / 'dashboard.html', 'w') as f:
    f.write(html)
print("Wrote dashboard.html, length:", len(html))
