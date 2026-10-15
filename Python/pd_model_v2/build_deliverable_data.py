"""
Assemble every v2 figure the Excel workbook and the Word report quote, into a
single JSON payload. Both deliverables read from this file, so they cannot
drift apart from each other or from the dashboard.
"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EX = REPO_ROOT / 'PowerBI' / 'extracts'
LGD = 0.90


def read_extract(name):
    """Accept either the plain or the gzipped copy of an extract."""
    plain, gz = EX / f'{name}.csv', EX / f'{name}.csv.gz'
    if plain.exists():
        return pd.read_csv(plain)
    if gz.exists():
        return pd.read_csv(gz, compression='gzip')
    raise FileNotFoundError(f"Missing {plain} (or {gz}).")


fact = read_extract('fact_scored_loans')
calib = read_extract('agg_model_calibration')
bands = read_extract('agg_risk_band_summary')
grade_scorecard = read_extract('agg_grade_scorecard')
recovery = read_extract('agg_recovery_by_grade')
vintage = read_extract('agg_vintage_default_trend')
state_risk = read_extract('agg_state_risk')

model = json.load(open(HERE / 'model_v2_results.json'))
meta = json.load(open(HERE / 'features_v2_meta.json'))
reject = json.load(open(REPO_ROOT / 'Python' / 'reject_inference_model'
                        / 'accept_reject_model_results.json'))

hgb = model['results']['hist_gradient_boosting']
logreg = model['results']['logistic_regression']

out = {}

# ----------------------------------------------------------------- portfolio
# Full resolved-loan history from the warehouse views, via the vintage extract.
out['portfolio'] = {
    'n_resolved_loans': int(vintage['n_resolved'].sum()),
    'n_defaults': int(vintage['n_default'].sum()),
    'overall_default_rate': float(vintage['n_default'].sum() / vintage['n_resolved'].sum()),
    'vintage_trend': [
        {'issue_year': int(r['issue_year']), 'n_resolved': int(r['n_resolved']),
         'default_rate': float(r['default_rate_pct']) / 100}
        for _, r in vintage.iterrows()
    ],
    'grade_scorecard': [
        {'grade': r['grade'], 'n_loans': int(r['n_loans']),
         'total_funded': float(r['total_funded']),
         'wavg_int_rate': float(r['wavg_int_rate']),
         'default_rate': float(r['default_rate_pct']) / 100,
         'total_net_loss': float(r['total_net_loss'])}
        for _, r in grade_scorecard.iterrows()
    ],
    'recovery_by_grade': [
        {'grade': r['grade'], 'n_defaults': int(r['n_defaults']),
         'recovery_rate': float(r['recovery_rate_pct']) / 100,
         'implied_lgd': 1 - float(r['recovery_rate_pct']) / 100}
        for _, r in recovery.iterrows()
    ],
    'top_states': [
        {'state': r['state'], 'n_loans': int(r['n_loans']),
         'total_exposure': float(r['total_exposure']),
         'default_rate': float(r['default_rate_pct']) / 100}
        for _, r in state_risk.head(10).iterrows()
    ],
}

# --------------------------------------------------------------------- model
out['model'] = {
    'name': 'HistGradientBoostingClassifier',
    'logreg_auc': float(logreg['auc']),
    'hgb_auc': float(hgb['auc']),
    'hgb_ks': float(hgb['ks']),
    'hgb_brier': float(hgb['brier']),
    'n_train': int(meta['n_train']),
    'n_test': int(meta['n_test']),
    'n_features': int(meta['n_features']),
    'n_dropped_for_missingness': len(meta['dropped_for_missingness']),
    'train_default_rate': float(meta['train_default_rate']),
    'test_default_rate': float(meta['test_default_rate']),
    'validation': 'out-of-time (train issue years <= 2016, test 2017-2018)',
    'v1_comparison': {
        'auc': 0.743970494775596, 'ks': 0.36027718696674743,
        'brier': 0.13945056516308238, 'n_train': 65918, 'n_test': 21973,
        'validation': 'random 75/25 split within a single 2015 vintage',
    },
    'decile_table': [
        {'decile': int(r['decile']), 'n': int(r['loans']),
         'avg_pd': float(r['avg_predicted_pd']),
         'actual_default_rate': float(r['actual_default_rate']),
         'lift': float(r['lift'])}
        for _, r in calib.iterrows()
    ],
    'top_features': [
        {'feature': f['feature'], 'importance': float(f['importance'])}
        for f in model['results']['top_permutation_importance'][:12]
    ],
}

# ------------------------------------------------------------------- scoring
out['scoring'] = {
    'n_scored': int(len(fact)),
    'total_exposure': float(fact['funded_amnt'].sum()),
    'avg_predicted_pd': float(fact['predicted_pd'].mean()),
    'actual_default_rate': float(fact['actual_default'].mean()),
    'expected_loss': float(fact['expected_loss'].sum()),
    'actual_loss': float(fact['actual_loss_proxy'].sum()),
    'lgd_assumption': LGD,
    'risk_bands': [
        {'band': str(r['risk_band']), 'count': int(r['loans']),
         'exposure': float(r['total_exposure']),
         'avg_predicted_pd': float(r['avg_predicted_pd']),
         'actual_default_rate': float(r['actual_default_rate']),
         'expected_loss': float(r['expected_loss']),
         'actual_loss': float(r['actual_loss_proxy'])}
        for _, r in bands.sort_values('risk_band').iterrows()
    ],
    'grade_predicted_vs_actual': [
        {'grade': g,
         'predicted_pd': float(d['predicted_pd'].mean()),
         'actual_default_rate': float(d['actual_default'].mean()),
         'count': int(len(d))}
        for g, d in fact.groupby('grade')
    ],
    'purpose_actual_rates': [
        {'purpose': p, 'default_rate': float(d['actual_default'].mean()), 'count': int(len(d))}
        for p, d in fact.groupby('purpose') if len(d) >= 200
    ],
    'top20_highest_risk': [
        {'id': int(r['loan_id']), 'loan_amnt': float(r['funded_amnt']),
         'grade': r['grade'], 'sub_grade': r['sub_grade'], 'purpose': r['purpose'],
         'addr_state': r['state'], 'pd': float(r['predicted_pd']),
         'risk_band': str(r['risk_band']), 'expected_loss': float(r['expected_loss']),
         'actual_default': int(r['actual_default'])}
        for _, r in fact.nlargest(20, 'predicted_pd').iterrows()
    ],
}
out['scoring']['purpose_actual_rates'].sort(key=lambda x: -x['default_rate'])
out['scoring']['grade_predicted_vs_actual'].sort(key=lambda x: x['grade'])
out['scoring']['top20_actual_defaults'] = sum(
    x['actual_default'] for x in out['scoring']['top20_highest_risk'])

# --------------------------------------------------------- reject inference
out['reject_inference'] = {
    'headline_auc': float(reject['models']['headline_no_emp_length']['auc']),
    'with_score_auc': float(reject['models']['with_credit_score']['auc']),
    'emp_length_inflated_auc': float(reject['models']['emp_length_included_caution']['auc']),
    'emp_length_under_1yr_accepted': float(
        reject['data_quality_note']['emp_length_pct_under_1yr_accepted']),
    'emp_length_under_1yr_rejected': float(
        reject['data_quality_note']['emp_length_pct_under_1yr_rejected']),
    'accepted_sampled': int(reject['sample_sizes']['accepted_sampled']),
    'rejected_sampled': int(reject['sample_sizes']['rejected_sampled']),
}

# ------------------------------------------------------- warehouse row counts
DB = REPO_ROOT / 'SQL' / 'credit_risk_warehouse.db'
if DB.exists():
    conn = sqlite3.connect(DB)
    out['warehouse'] = {
        'raw_accepted_rows': conn.execute('SELECT COUNT(*) FROM raw_accepted').fetchone()[0],
        'raw_rejected_rows': conn.execute('SELECT COUNT(*) FROM raw_rejected').fetchone()[0],
    }
    conn.close()
else:
    out['warehouse'] = {'raw_accepted_rows': 2260668, 'raw_rejected_rows': 27648741}

with open(HERE / 'deliverable_data_v2.json', 'w') as f:
    json.dump(out, f, indent=2)

print(f"resolved loans        : {out['portfolio']['n_resolved_loans']:,}")
print(f"overall default rate  : {out['portfolio']['overall_default_rate']:.4f}")
print(f"model AUC / KS        : {out['model']['hgb_auc']:.4f} / {out['model']['hgb_ks']:.4f}")
print(f"train / test          : {out['model']['n_train']:,} / {out['model']['n_test']:,}")
print(f"scored exposure       : ${out['scoring']['total_exposure']/1e9:.2f}B")
print(f"expected / actual loss: ${out['scoring']['expected_loss']/1e6:.1f}M / "
      f"${out['scoring']['actual_loss']/1e6:.1f}M")
print(f"implied LGD (grade A) : {out['portfolio']['recovery_by_grade'][0]['implied_lgd']:.3f}")
print(f"watchlist defaults    : {out['scoring']['top20_actual_defaults']}/20")
print(f"warehouse rows        : {out['warehouse']['raw_accepted_rows']:,} accepted, "
      f"{out['warehouse']['raw_rejected_rows']:,} rejected")
