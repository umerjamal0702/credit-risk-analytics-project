import pandas as pd
import numpy as np
import json


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


pd.set_option('display.max_columns', 200)

df = pd.read_csv(DATASET / 'credit_risk_training_clean.csv')
print("Shape:", df.shape)

df['default'] = (df['loan_status'] == 'Charged Off').astype(int)
overall_rate = df['default'].mean()
print("Overall charge-off rate: {:.2%}".format(overall_rate))

results = {}
results['overall_default_rate'] = overall_rate
results['n_loans'] = len(df)
results['n_charged_off'] = int(df['default'].sum())
results['n_fully_paid'] = int((df['default']==0).sum())

def rate_by(col):
    g = df.groupby(col)['default'].agg(['mean','count']).sort_values('mean', ascending=False)
    return g

for col in ['grade','purpose','home_ownership','term','verification_status','application_type']:
    g = rate_by(col)
    print(f"\n--- Default rate by {col} ---")
    print(g)
    results[f'default_rate_by_{col}'] = {str(k): {'rate': float(v['mean']), 'count': int(v['count'])} for k,v in g.iterrows()}

# sub_grade too
g = rate_by('sub_grade')
results['default_rate_by_sub_grade'] = {str(k): {'rate': float(v['mean']), 'count': int(v['count'])} for k,v in g.iterrows()}

# numeric distributions by outcome
numeric_cols = ['loan_amnt','int_rate','annual_inc','dti','fico_range_low','revol_util','credit_history_years','emp_length_num','open_acc','pub_rec','delinq_2yrs','inq_last_6mths','mort_acc']
num_summary = {}
for col in numeric_cols:
    num_summary[col] = {
        'fully_paid_mean': float(df.loc[df['default']==0, col].mean()),
        'charged_off_mean': float(df.loc[df['default']==1, col].mean()),
        'overall_mean': float(df[col].mean()),
        'overall_median': float(df[col].median()),
    }
results['numeric_summary'] = num_summary
print("\n--- Numeric means by outcome ---")
print(pd.DataFrame(num_summary).T)

# correlation with default for numeric cols
corr = df[numeric_cols + ['default']].corr()['default'].drop('default').sort_values(key=abs, ascending=False)
print("\n--- Correlation with default ---")
print(corr)
results['correlation_with_default'] = {k: float(v) for k,v in corr.items()}

with open(HERE / 'eda_results.json','w') as f:
    json.dump(results, f, indent=2)
print("\nSaved eda_results.json")
