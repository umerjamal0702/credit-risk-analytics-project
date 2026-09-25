import pandas as pd
import numpy as np
import pickle
import json


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


with open(HERE / 'final_model.pkl','rb') as f:
    saved = pickle.load(f)
model = saved['model']
feature_names = saved['feature_names']

X_score = pd.read_pickle(HERE / 'X_score.pkl')[feature_names]
score_ids = pd.read_pickle(HERE / 'score_ids.pkl')['id']

pd_scores = model.predict_proba(X_score)[:,1]

# original (readable) scoring data for context
orig = pd.read_csv(DATASET / 'current_loan_scoring_clean.csv')
orig['pd'] = pd_scores

# risk grade buckets based on PD thresholds (roughly aligned with LendingClub grade default rates)
def risk_band(p):
    if p < 0.06: return '1 - Low'
    elif p < 0.12: return '2 - Low-Medium'
    elif p < 0.20: return '3 - Medium'
    elif p < 0.30: return '4 - Medium-High'
    elif p < 0.45: return '5 - High'
    else: return '6 - Very High'

orig['risk_band'] = orig['pd'].apply(risk_band)
orig['expected_loss'] = orig['pd'] * orig['funded_amnt']  # assumes LGD=100% (conservative upper bound on EL)

cols_keep = ['id','loan_amnt','funded_amnt','term','int_rate','installment','grade','sub_grade',
             'home_ownership','annual_inc','purpose','addr_state','dti','fico_range_low','fico_range_high',
             'revol_util','credit_history_years','emp_length_num','pd','risk_band','expected_loss']
scored = orig[cols_keep].sort_values('pd', ascending=False)
scored.to_csv(HERE / 'scored_current_loans.csv', index=False)

print("Scored", len(scored), "current loans")
print("\nPD distribution:")
print(scored['pd'].describe())
print("\nRisk band counts:")
print(scored['risk_band'].value_counts().sort_index())
print("\nRisk band counts by original LendingClub grade (cross-check):")
print(pd.crosstab(scored['grade'], scored['risk_band']))

summary = {
    'n_scored': len(scored),
    'avg_pd': float(scored['pd'].mean()),
    'total_exposure': float(scored['funded_amnt'].sum()),
    'total_expected_loss_upper_bound': float(scored['expected_loss'].sum()),
    'risk_band_counts': scored['risk_band'].value_counts().sort_index().to_dict(),
    'risk_band_exposure': scored.groupby('risk_band')['funded_amnt'].sum().to_dict(),
    'top20_highest_risk': scored.head(20)[['id','loan_amnt','grade','sub_grade','purpose','pd','risk_band']].to_dict(orient='records'),
}
with open(HERE / 'scoring_summary.json','w') as f:
    json.dump(summary, f, indent=2, default=str)
print("\nSaved scored_current_loans.csv and scoring_summary.json")
print("\nTotal exposure: ${:,.0f}".format(summary['total_exposure']))
print("Total expected loss (upper bound, LGD=100%): ${:,.0f}".format(summary['total_expected_loss_upper_bound']))
