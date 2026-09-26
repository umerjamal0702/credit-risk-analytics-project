"""
Build dashboard_data.json for the v2 Credit Risk Monitor.

v1 scored 11,402 loans whose outcomes were unknown, so the dashboard could only
show predictions. v2 scores the 225,639-loan out-of-time test set, where the real
outcomes ARE known — so every predicted figure can be shown against what actually
happened. Expected loss uses the 90% LGD measured from recovery data, not v1's
100% placeholder.
"""
import pandas as pd
import numpy as np
import json


from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning.
REPO_ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
MODEL_DIR = REPO_ROOT / 'Python' / 'pd_model_v2'


EX = str(REPO_ROOT / 'PowerBI' / 'extracts')
LGD = 0.90

def read_extract(name):
    """Read an extract, accepting either the plain or gzipped copy.
    The repository ships fact_scored_loans gzipped to keep its size down;
    regenerating it locally produces the uncompressed file."""
    plain = Path(EX) / f'{name}.csv'
    gz = Path(EX) / f'{name}.csv.gz'
    if plain.exists():
        return pd.read_csv(plain)
    if gz.exists():
        return pd.read_csv(gz, compression='gzip')
    raise FileNotFoundError(f"Missing {plain} (or {gz}). "
                            f"Run Python/pd_model_v2/build_dashboard_extracts.py first.")

fact = read_extract('fact_scored_loans')
calib = pd.read_csv(f'{EX}/agg_model_calibration.csv')
bands = pd.read_csv(f'{EX}/agg_risk_band_summary.csv')
res = json.load(open(MODEL_DIR / 'model_v2_results.json'))
meta = json.load(open(MODEL_DIR / 'features_v2_meta.json'))

hgb = res['results']['hist_gradient_boosting']

out = {}

# ---------------------------------------------------------------- KPI strip
out['kpi'] = {
    'n_scored': int(len(fact)),
    'total_exposure': float(fact['funded_amnt'].sum()),
    'avg_pd': float(fact['predicted_pd'].mean()),
    'actual_default_rate': float(fact['actual_default'].mean()),
    'expected_loss': float(fact['expected_loss'].sum()),
    'actual_loss': float(fact['actual_loss_proxy'].sum()),
    'auc': float(hgb['auc']),
    'ks': float(hgb['ks']),
    'n_training': int(meta['n_train']),
    'lgd': LGD,
}

# ------------------------------------------------- risk bands (count + actual)
bands = bands.sort_values('risk_band')

def band_label(raw):
    # '1 Low' -> '1 - Low', the separator the renderer splits on
    num, _, name = str(raw).partition(' ')
    return f"{num} - {name}"

out['risk_bands'] = [{
    'band': band_label(r['risk_band']),
    'count': int(r['loans']),
    'exposure': float(r['total_exposure']),
    'avg_pd': float(r['avg_predicted_pd']),
    'actual_rate': float(r['actual_default_rate']),
} for _, r in bands.iterrows()]

# --------------------------------------- predicted vs actual default by grade
g = fact.groupby('grade').agg(
    predicted_pd=('predicted_pd', 'mean'),
    actual_rate=('actual_default', 'mean'),
    count=('actual_default', 'size'),
).reset_index().sort_values('grade')
out['grade_comparison'] = [{
    'grade': r['grade'],
    'predicted_pd': float(r['predicted_pd']),
    'actual_rate': float(r['actual_rate']),
    'count': int(r['count']),
} for _, r in g.iterrows()]

# ------------------------------------------------- calibration by risk decile
out['decile_lift'] = [{
    'decile': int(r['decile']) - 1,       # 0-indexed to match the renderer
    'n': int(r['loans']),
    'avg_pd': float(r['avg_predicted_pd']),
    'default_rate': float(r['actual_default_rate']),
} for _, r in calib.iterrows()]

# ------------------------------------------- actual default rate by purpose
p = fact.groupby('purpose').agg(
    rate=('actual_default', 'mean'),
    count=('actual_default', 'size'),
).reset_index()
p = p[p['count'] >= 200].sort_values('rate', ascending=False)
out['purpose_rates'] = [{
    'purpose': r['purpose'],
    'rate': float(r['rate']),
    'count': int(r['count']),
} for _, r in p.iterrows()]

# ------------------------------------------------------------- watchlist top 20
w = fact.nlargest(20, 'predicted_pd')
out['watchlist'] = [{
    'id': int(r['loan_id']),
    'loan_amnt': float(r['funded_amnt']),
    'grade': r['grade'],
    'sub_grade': r['sub_grade'],
    'purpose': r['purpose'],
    'addr_state': r['state'],
    'pd': float(r['predicted_pd']),
    'risk_band': band_label(r['risk_band']),
    'expected_loss': float(r['expected_loss']),
    'actual_default': int(r['actual_default']),
} for _, r in w.iterrows()]

with open(HERE / 'dashboard_data.json', 'w') as f:
    json.dump(out, f, indent=2)

print(f"loans scored       : {out['kpi']['n_scored']:,}")
print(f"exposure           : ${out['kpi']['total_exposure']/1e9:.2f}B")
print(f"avg predicted PD   : {out['kpi']['avg_pd']:.4f}")
print(f"actual default rate: {out['kpi']['actual_default_rate']:.4f}")
print(f"expected loss @90% : ${out['kpi']['expected_loss']/1e6:.1f}M")
print(f"actual loss        : ${out['kpi']['actual_loss']/1e6:.1f}M")
print(f"AUC / KS           : {out['kpi']['auc']:.4f} / {out['kpi']['ks']:.4f}")
print(f"grades             : {len(out['grade_comparison'])}")
print(f"purposes (>=200)   : {len(out['purpose_rates'])}")
print(f"watchlist actually defaulted: {sum(x['actual_default'] for x in out['watchlist'])}/20")
