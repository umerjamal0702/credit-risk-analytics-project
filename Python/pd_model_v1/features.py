import pandas as pd
import numpy as np


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


LEAKAGE_COLS = [
    'total_rec_prncp', 'total_rec_int', 'total_rec_late_fee',
    'last_fico_range_high', 'last_fico_range_low',
]
DROP_COLS = [
    'id', 'funded_amnt', 'funded_amnt_inv', 'zip_code',
    'issue_year', 'issue_month',
] + LEAKAGE_COLS

CAT_COLS = ['term', 'grade', 'sub_grade', 'home_ownership', 'verification_status',
            'purpose', 'addr_state', 'initial_list_status', 'application_type']

def load_and_prep(path, is_scoring=False):
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    if not is_scoring:
        df['default'] = (df['loan_status'] == 'Charged Off').astype(int)
    ids = df['id'].copy()
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])
    df = df.drop(columns=['loan_status'])
    df['term'] = df['term'].str.strip()
    return df, ids

train_df, train_ids = load_and_prep(DATASET / 'credit_risk_training_clean.csv')
score_df, score_ids = load_and_prep(DATASET / 'current_loan_scoring_clean.csv', is_scoring=True)

print("train_df shape:", train_df.shape)
print("score_df shape:", score_df.shape)

y = train_df.pop('default')
X = train_df

# one-hot encode categoricals, align columns between train and scoring
X_enc = pd.get_dummies(X, columns=CAT_COLS, drop_first=False)
score_enc = pd.get_dummies(score_df, columns=CAT_COLS, drop_first=False)

# align
X_enc, score_enc = X_enc.align(score_enc, join='left', axis=1, fill_value=0)
score_enc = score_enc[X_enc.columns]

print("X_enc shape:", X_enc.shape, "score_enc shape:", score_enc.shape)
assert list(X_enc.columns) == list(score_enc.columns)

X_enc.to_pickle(HERE / 'X_train.pkl')
y.to_frame('default').to_pickle(HERE / 'y_train.pkl')
score_enc.to_pickle(HERE / 'X_score.pkl')
train_ids.to_frame('id').to_pickle(HERE / 'train_ids.pkl')
score_ids.to_frame('id').to_pickle(HERE / 'score_ids.pkl')

print("Feature columns:", list(X_enc.columns))
print("Saved parquet files.")
