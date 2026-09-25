"""
Phase 4 — Acceptance-propensity model (a reject-inference-style angle).

The accepted file only shows loans LendingClub already chose to fund —
it can't say anything about *who gets turned down and why*. The 27.6M
rejected applications close that gap. This script builds a simple
accept-vs-reject classifier on the fields both files share (amount
requested, DTI, employment length, state, application year, and an
approximate credit-score proxy) to quantify what separates an accepted
application from a rejected one — the underwriting-funnel counterpart
to the PD model (which only scores loans that already got funded).

Caveat carried into the writeup: the two files don't share a native
credit-score field. `risk_score` (rejected) and the accepted file's
FICO range are both roughly credit-score-like but not identically
defined or scaled — treated here as an approximate proxy, not a hard
apples-to-apples match.
"""
import sqlite3, time, json
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, roc_curve


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


OUT = str(HERE)
DB = str(REPO_ROOT / 'SQL' / 'credit_risk_warehouse.db')
t0 = time.time()

conn = sqlite3.connect(DB)

# systematic samples via rowid modulo — fast on 2.26M / 27.6M rows,
# no full-table sort needed
accepted = pd.read_sql_query("""
    SELECT loan_amnt, dti, emp_length, addr_state, issue_d,
           fico_range_low, fico_range_high
    FROM raw_accepted
    WHERE rowid % 7 = 0
""", conn)
accepted['outcome'] = 1
accepted['amount_requested'] = pd.to_numeric(accepted['loan_amnt'], errors='coerce')
accepted['dti_pct'] = pd.to_numeric(accepted['dti'], errors='coerce')
accepted['credit_score_proxy'] = (
    pd.to_numeric(accepted['fico_range_low'], errors='coerce') +
    pd.to_numeric(accepted['fico_range_high'], errors='coerce')
) / 2.0
accepted['state'] = accepted['addr_state']
MONTHS = {m: i+1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}
accepted['app_year'] = accepted['issue_d'].astype(str).str.split('-').str[1]
accepted['app_year'] = pd.to_numeric(accepted['app_year'], errors='coerce')

rejected = pd.read_sql_query("""
    SELECT amount_requested, dti_pct, emp_length, state, application_date, risk_score
    FROM raw_rejected
    WHERE rowid % 92 = 0
""", conn)
conn.close()
rejected['outcome'] = 0
rejected['amount_requested'] = pd.to_numeric(rejected['amount_requested'], errors='coerce')
rejected['dti_pct'] = pd.to_numeric(rejected['dti_pct'].astype(str).str.replace('%', '', regex=False),
                                     errors='coerce')
rejected['credit_score_proxy'] = pd.to_numeric(rejected['risk_score'], errors='coerce')
rejected['app_year'] = pd.to_numeric(rejected['application_date'].astype(str).str[:4], errors='coerce')

EMP_MAP = {f'{i} years': i for i in range(2, 10)}
EMP_MAP.update({'1 year': 1, '10+ years': 10, '< 1 year': 0})
accepted['emp_length_years'] = accepted['emp_length'].map(EMP_MAP)
rejected['emp_length_years'] = rejected['emp_length'].map(EMP_MAP)

COMMON = ['outcome', 'amount_requested', 'dti_pct', 'emp_length_years', 'state',
          'app_year', 'credit_score_proxy']
df = pd.concat([accepted[COMMON], rejected[COMMON]], ignore_index=True)
print(f"Combined sample: {df.shape}, {time.time()-t0:.1f}s")
print(f"Class balance: {df['outcome'].value_counts(normalize=True).to_dict()}")

# clean obvious data-entry outliers
df = df[(df['dti_pct'] >= 0) & (df['dti_pct'] <= 100)]
df = df[(df['amount_requested'] > 0) & (df['amount_requested'] <= 100000)]
df = df[df['app_year'].between(2008, 2018)]

# credit_score_proxy has heavy missingness on the rejected side (risk_score
# only ~55% populated pre-2015, ~35-70% after) — model with AND without it
# so the score's contribution is visible without throwing away rows that lack it
has_score = df['credit_score_proxy'].notna()
print(f"Rows with a credit_score_proxy: {has_score.sum():,} / {len(df):,} ({has_score.mean():.1%})")

def fit_eval(data, feature_cols, label):
    d = data.dropna(subset=feature_cols + ['outcome']).copy()
    cat_cols = [c for c in feature_cols if c == 'state']
    num_cols = [c for c in feature_cols if c != 'state']
    X = pd.get_dummies(d[feature_cols], columns=cat_cols, dtype=np.int8)
    y = d['outcome']
    from sklearn.model_selection import train_test_split
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)
    clf = LogisticRegression(max_iter=1000, class_weight='balanced')
    clf.fit(X_tr_s, y_tr)
    p = clf.predict_proba(X_te_s)[:, 1]
    auc = roc_auc_score(y_te, p)
    coefs = sorted(zip(X.columns, clf.coef_[0]), key=lambda x: -abs(x[1]))[:15]
    print(f"[{label}] n={len(d):,}, AUC={auc:.4f}")
    for f, c in coefs[:8]:
        print(f"   {f}: {c:+.3f}")
    return {'label': label, 'n': int(len(d)), 'auc': float(auc),
            'top_coefficients': [{'feature': f, 'coef': float(c)} for f, c in coefs]}

# ---------------------------------------------------------------------
# Data-quality flag: emp_length in the REJECTED file is ~83% defaulted
# to "< 1 year" (vs a roughly uniform 0-10 spread in the accepted file)
# — almost certainly a form/data artifact for quickly-declined
# applications, not a genuine employment-tenure signal. Including it
# inflates the acceptance model's AUC from ~0.68 to ~0.91 on separation
# that isn't real underwriting signal, so it's reported separately
# rather than folded into the headline model.
# ---------------------------------------------------------------------
emp_check = df.groupby('outcome')['emp_length_years'].apply(
    lambda s: (s == 0).mean())
print(f"Share of emp_length_years == 0 (i.e. '< 1 year'): "
      f"accepted={emp_check.get(1, float('nan')):.1%}, "
      f"rejected={emp_check.get(0, float('nan')):.1%}  <- data artifact, see note above")

results = {}
results['headline_no_emp_length'] = fit_eval(
    df, ['amount_requested', 'dti_pct', 'app_year', 'state'],
    'Acceptance model — headline (amount, DTI, year, state; emp_length excluded as artifact)')
results['with_credit_score'] = fit_eval(
    df[has_score], ['amount_requested', 'dti_pct', 'app_year', 'state', 'credit_score_proxy'],
    'Acceptance model — WITH credit_score_proxy (subset where populated, emp_length excluded)')
results['emp_length_included_caution'] = fit_eval(
    df, ['amount_requested', 'dti_pct', 'emp_length_years', 'app_year', 'state'],
    'Acceptance model — WITH emp_length (inflated by the data artifact above, for comparison only)')

# profile comparison table (accepted vs rejected), by year — mirrors SQL Q3
# but recomputed here on the same sample for a consistency check
profile = df.groupby([df['app_year'].astype(int), df['outcome']]).agg(
    n=('outcome', 'size'),
    avg_dti=('dti_pct', 'mean'),
    avg_amount=('amount_requested', 'mean'),
).reset_index()
profile['outcome'] = profile['outcome'].map({1: 'accepted', 0: 'rejected'})

out = {
    'sample_sizes': {'accepted_sampled': int(len(accepted)), 'rejected_sampled': int(len(rejected))},
    'data_quality_note': {
        'emp_length_pct_under_1yr_accepted': float(emp_check.get(1, float('nan'))),
        'emp_length_pct_under_1yr_rejected': float(emp_check.get(0, float('nan'))),
        'finding': "emp_length in the rejected-applications file is ~83% defaulted to "
                   "'< 1 year', vs a roughly uniform spread in the accepted file — treated "
                   "as a data artifact and excluded from the headline acceptance model.",
    },
    'models': results,
    'profile_by_year': profile.to_dict(orient='records'),
    'elapsed_sec': time.time() - t0,
}
with open(f'{OUT}/accept_reject_model_results.json', 'w') as f:
    json.dump(out, f, indent=2)

print(f"\nDone in {time.time()-t0:.1f}s")
