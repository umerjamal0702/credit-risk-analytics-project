"""
Build the remaining Power BI extracts: a scored-loan fact table from the v2
out-of-time test set, model calibration/risk-band summaries, and the
underwriting funnel profile tables.
"""
import pandas as pd
import numpy as np
import time, json


from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


SRC = str(DATASET / 'accepted_2007_to_2018Q4.csv.gz')
OUT = str(REPO_ROOT / 'PowerBI' / 'extracts')
t0 = time.time()

# ---------------------------------------------------------------------
# Rebuild the attribute frame for the v2 test set using IDENTICAL filter
# logic to features_v2.py, so row order matches test_predictions_v2.csv.
# Alignment is then PROVEN by checking the reconstructed default flag
# against the y_true column saved at scoring time.
# ---------------------------------------------------------------------
BAD = {'Charged Off', 'Default', 'Does not meet the credit policy. Status:Charged Off'}
GOOD = {'Fully Paid', 'Does not meet the credit policy. Status:Fully Paid'}
MONTHS = {m: i+1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}

ATTR_COLS = ['id', 'issue_d', 'loan_status', 'grade', 'sub_grade', 'purpose',
             'addr_state', 'term', 'funded_amnt', 'int_rate', 'annual_inc', 'dti']

frames = []
reader = pd.read_csv(SRC, usecols=ATTR_COLS, compression='gzip',
                      chunksize=200_000, dtype=str)
for chunk in reader:
    chunk = chunk[chunk['id'].astype(str).str.strip().str.isdigit()]
    chunk = chunk[chunk['issue_d'].notna()]
    chunk = chunk[chunk['loan_status'].isin(BAD | GOOD)]
    if len(chunk):
        frames.append(chunk)

attrs = pd.concat(frames, ignore_index=True)
del frames

parts = attrs['issue_d'].astype(str).str.split('-', expand=True)
attrs['issue_month_num'] = parts[0].map(MONTHS)
attrs['issue_year'] = pd.to_numeric(parts[1], errors='coerce')
attrs['issue_yyyymm'] = (attrs['issue_year'].astype('Int64').astype(str) + '-' +
                          attrs['issue_month_num'].astype('Int64').astype(str).str.zfill(2))
attrs['default_flag'] = attrs['loan_status'].isin(BAD).astype(np.int8)

test_attrs = attrs[attrs['issue_year'] >= 2017].reset_index(drop=True)
print(f"Rebuilt test attributes: {test_attrs.shape}, {time.time()-t0:.1f}s")

preds = pd.read_csv(HERE / 'test_predictions_v2.csv')
print(f"Predictions: {preds.shape}")

assert len(preds) == len(test_attrs), \
    f"ROW COUNT MISMATCH: preds {len(preds)} vs attrs {len(test_attrs)}"
mismatches = int((preds['y_true'].values != test_attrs['default_flag'].values).sum())
print(f"Alignment check — default-flag mismatches: {mismatches} / {len(preds)}")
assert mismatches == 0, "ALIGNMENT FAILED: predictions do not line up with attributes"

# ---------------------------------------------------------------------
# fact_scored_loans
# ---------------------------------------------------------------------
LGD = 0.90  # observed loss given default from the recovery analysis

fact = pd.DataFrame({
    'loan_id': test_attrs['id'],
    'issue_year': test_attrs['issue_year'],
    'issue_yyyymm': test_attrs['issue_yyyymm'],
    'grade': test_attrs['grade'],
    'sub_grade': test_attrs['sub_grade'],
    'purpose': test_attrs['purpose'],
    'state': test_attrs['addr_state'],
    'term': test_attrs['term'].str.strip(),
    'funded_amnt': pd.to_numeric(test_attrs['funded_amnt'], errors='coerce'),
    'int_rate': pd.to_numeric(test_attrs['int_rate'], errors='coerce'),
    'annual_inc': pd.to_numeric(test_attrs['annual_inc'], errors='coerce'),
    'dti': pd.to_numeric(test_attrs['dti'], errors='coerce'),
    'predicted_pd': preds['pd_hgb'].round(6),
    'actual_default': preds['y_true'].astype(np.int8),
})

BANDS = [(0.00, 0.06, '1 Low'), (0.06, 0.12, '2 Low-Medium'), (0.12, 0.20, '3 Medium'),
         (0.20, 0.30, '4 Medium-High'), (0.30, 0.45, '5 High'), (0.45, 1.01, '6 Very High')]
fact['risk_band'] = pd.cut(fact['predicted_pd'],
                            bins=[b[0] for b in BANDS] + [BANDS[-1][1]],
                            labels=[b[2] for b in BANDS], right=False)
fact['expected_loss'] = (fact['predicted_pd'] * fact['funded_amnt'] * LGD).round(2)
fact['actual_loss_proxy'] = (fact['actual_default'] * fact['funded_amnt'] * LGD).round(2)

fact.to_csv(f'{OUT}/fact_scored_loans.csv', index=False)
print(f"fact_scored_loans: {fact.shape} -> {OUT}/fact_scored_loans.csv")

# ---------------------------------------------------------------------
# agg_model_calibration — decile table (1 = lowest predicted risk)
# ---------------------------------------------------------------------
d = fact[['predicted_pd', 'actual_default', 'funded_amnt']].copy()
d['decile'] = pd.qcut(d['predicted_pd'].rank(method='first'), 10, labels=False) + 1
overall = d['actual_default'].mean()
calib = d.groupby('decile').agg(
    loans=('actual_default', 'size'),
    avg_predicted_pd=('predicted_pd', 'mean'),
    actual_default_rate=('actual_default', 'mean'),
    total_funded=('funded_amnt', 'sum'),
).reset_index()
calib['lift'] = (calib['actual_default_rate'] / overall).round(3)
calib['avg_predicted_pd'] = calib['avg_predicted_pd'].round(4)
calib['actual_default_rate'] = calib['actual_default_rate'].round(4)
calib.to_csv(f'{OUT}/agg_model_calibration.csv', index=False)
print(f"agg_model_calibration: {calib.shape}")

# ---------------------------------------------------------------------
# agg_risk_band_summary
# ---------------------------------------------------------------------
band = fact.groupby('risk_band', observed=True).agg(
    loans=('actual_default', 'size'),
    total_exposure=('funded_amnt', 'sum'),
    avg_predicted_pd=('predicted_pd', 'mean'),
    actual_default_rate=('actual_default', 'mean'),
    expected_loss=('expected_loss', 'sum'),
    actual_loss_proxy=('actual_loss_proxy', 'sum'),
).reset_index()
band['avg_predicted_pd'] = band['avg_predicted_pd'].round(4)
band['actual_default_rate'] = band['actual_default_rate'].round(4)
band.to_csv(f'{OUT}/agg_risk_band_summary.csv', index=False)
print(f"agg_risk_band_summary: {band.shape}")
print(band.to_string(index=False))

meta = {
    'test_set_loans': int(len(fact)),
    'alignment_mismatches': mismatches,
    'lgd_assumption': LGD,
    'overall_actual_default_rate': float(overall),
    'elapsed_sec': time.time() - t0,
}
with open(f'{OUT}/_scored_extract_meta.json', 'w') as f:
    json.dump(meta, f, indent=2)

print(f"\nDone in {time.time()-t0:.1f}s")
