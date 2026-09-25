"""
PD model v2 — feature engineering on the FULL 2.26M-loan accepted file
(v1 used an 87K-row 2015-only sample). Builds a leakage-free feature set
and an out-of-time train/test split (train issue years <=2016, test
2017-2018) instead of v1's random split on a single vintage.

Reads in chunks to stay within the sandbox's memory budget (a single
low_memory=False read of all 80 columns OOM'd at ~6GB RSS).
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
OUT = str(HERE)
CHUNKSIZE = 200_000

t0 = time.time()

NUMERIC_COLS = [
    'loan_amnt', 'installment', 'annual_inc', 'dti', 'delinq_2yrs',
    'fico_range_low', 'fico_range_high', 'inq_last_6mths',
    'mths_since_last_delinq', 'mths_since_last_record', 'open_acc',
    'pub_rec', 'revol_bal', 'total_acc', 'collections_12_mths_ex_med',
    'mths_since_last_major_derog', 'acc_now_delinq', 'tot_coll_amt',
    'tot_cur_bal', 'mort_acc', 'mo_sin_old_il_acct', 'mo_sin_old_rev_tl_op',
    'mo_sin_rcnt_rev_tl_op', 'mo_sin_rcnt_tl', 'num_accts_ever_120_pd',
    'num_actv_bc_tl', 'num_actv_rev_tl', 'num_bc_sats', 'num_bc_tl',
    'num_il_tl', 'num_op_rev_tl', 'num_rev_accts', 'num_rev_tl_bal_gt_0',
    'num_sats', 'num_tl_120dpd_2m', 'num_tl_30dpd', 'num_tl_90g_dpd_24m',
    'num_tl_op_past_12m', 'pct_tl_nvr_dlq', 'percent_bc_gt_75',
    'pub_rec_bankruptcies', 'tax_liens', 'tot_hi_cred_lim',
    'total_bal_ex_mort', 'total_bc_limit', 'total_il_high_credit_limit',
    'avg_cur_bal', 'bc_open_to_buy', 'bc_util', 'chargeoff_within_12_mths',
    'delinq_amnt', 'acc_open_past_24mths', 'inq_last_12m', 'all_util',
    'open_acc_6m', 'open_il_12m', 'open_il_24m', 'open_rv_12m',
    'open_rv_24m', 'il_util', 'max_bal_bc', 'mths_since_rcnt_il',
    'total_bal_il', 'total_rev_hi_lim',
]
PCT_STRING_COLS = ['int_rate', 'revol_util']
CAT_COLS = [
    'grade', 'sub_grade', 'home_ownership', 'verification_status',
    'purpose', 'addr_state', 'initial_list_status', 'application_type',
]
# fixed category universes (confirmed via a full pass over the file) so
# every chunk's one-hot columns line up identically
CATEGORIES = {
    'grade': ['A','B','C','D','E','F','G'],
    'sub_grade': [f'{g}{n}' for g in 'ABCDEFG' for n in '12345'],
    'home_ownership': ['ANY','MORTGAGE','NONE','OTHER','OWN','RENT'],
    'verification_status': ['Not Verified','Source Verified','Verified'],
    'purpose': ['car','credit_card','debt_consolidation','educational','home_improvement',
                'house','major_purchase','medical','moving','other','renewable_energy',
                'small_business','vacation','wedding'],
    'addr_state': ['AK','AL','AR','AZ','CA','CO','CT','DC','DE','FL','GA','HI','IA','ID',
                   'IL','IN','KS','KY','LA','MA','MD','ME','MI','MN','MO','MS','MT','NC',
                   'ND','NE','NH','NJ','NM','NV','NY','OH','OK','OR','PA','RI','SC','SD',
                   'TN','TX','UT','VA','VT','WA','WI','WV','WY'],
    'initial_list_status': ['f','w'],
    'application_type': ['Individual','Joint App'],
}

MONTHS = {m: i+1 for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'])}

def parse_mon_year(series):
    # Vectorized "Mon-YYYY" -> months-since-year-0 integer.
    # The month is zero-indexed (mon - 1) so that integer-dividing the result
    # by 12 recovers the calendar year for every month. With a 1-indexed month,
    # December would divide up into the following year and land in the wrong
    # side of the train/test split. Differences between two parsed dates are
    # unaffected by the offset, so credit_history_years is unchanged.
    parts = series.astype(str).str.split('-', expand=True)
    mon = parts[0].map(MONTHS)
    yr = pd.to_numeric(parts[1], errors='coerce')
    return yr * 12 + (mon - 1)

EMP_MAP = {f'{i} years': i for i in range(2, 10)}
EMP_MAP.update({'1 year': 1, '10+ years': 10, '< 1 year': 0})

BAD = {'Charged Off', 'Default', 'Does not meet the credit policy. Status:Charged Off'}
GOOD = {'Fully Paid', 'Does not meet the credit policy. Status:Fully Paid'}

USECOLS = (['id'] + NUMERIC_COLS + PCT_STRING_COLS + ['term', 'emp_length'] +
           CAT_COLS + ['issue_d', 'earliest_cr_line', 'loan_status'])

processed_chunks = []
n_read = 0
n_kept = 0

reader = pd.read_csv(SRC, usecols=USECOLS, compression='gzip',
                      chunksize=CHUNKSIZE, dtype=str)

for i, chunk in enumerate(reader):
    n_read += len(chunk)

    chunk = chunk[chunk['id'].astype(str).str.strip().str.isdigit()]
    chunk = chunk[chunk['issue_d'].notna()]
    chunk = chunk[chunk['loan_status'].isin(BAD | GOOD)]
    if len(chunk) == 0:
        continue

    out = pd.DataFrame(index=chunk.index)
    out['default_flag'] = chunk['loan_status'].isin(BAD).astype(np.int8)

    issue_ym = parse_mon_year(chunk['issue_d'])
    earliest_ym = parse_mon_year(chunk['earliest_cr_line'])
    out['issue_year'] = (issue_ym // 12).astype('Int64')
    credit_hist = (issue_ym - earliest_ym) / 12.0
    credit_hist[credit_hist < 0] = np.nan
    out['credit_history_years'] = credit_hist.astype(np.float32)

    for c in NUMERIC_COLS:
        out[c] = pd.to_numeric(chunk[c], errors='coerce').astype(np.float32)

    for c in PCT_STRING_COLS:
        out[c] = pd.to_numeric(
            chunk[c].astype(str).str.replace('%', '', regex=False).str.strip(),
            errors='coerce').astype(np.float32)

    out['term_months'] = pd.to_numeric(
        chunk['term'].astype(str).str.extract(r'(\d+)')[0], errors='coerce').astype(np.float32)
    out['emp_length_years'] = chunk['emp_length'].map(EMP_MAP).astype(np.float32)
    out['fico_avg'] = ((out['fico_range_low'] + out['fico_range_high']) / 2.0).astype(np.float32)

    for c in CAT_COLS:
        cat = pd.Categorical(chunk[c], categories=CATEGORIES[c])
        dummies = pd.get_dummies(cat, prefix=c, dtype=np.int8)
        out = pd.concat([out, dummies.set_axis(out.index)], axis=1)

    processed_chunks.append(out)
    n_kept += len(out)
    if i % 3 == 0:
        print(f"  chunk {i}: read {n_read:,} rows so far, kept {n_kept:,}, "
              f"elapsed {time.time()-t0:.1f}s", flush=True)

print(f"Concatenating {len(processed_chunks)} chunks ...", flush=True)
full = pd.concat(processed_chunks, ignore_index=True)
del processed_chunks
print(f"Full processed frame: {full.shape}, default rate {full['default_flag'].mean():.4f}, "
      f"{time.time()-t0:.1f}s", flush=True)

# ---------------------------------------------------------------------
# Missingness audit -> drop any numeric feature >50% missing (mostly
# newer bureau fields LendingClub only started collecting ~2015, which
# would be almost entirely NaN in the pre-2017 training window)
# ---------------------------------------------------------------------
FEATURE_NUMERIC = NUMERIC_COLS + ['int_rate', 'revol_util', 'term_months',
                                   'emp_length_years', 'fico_avg', 'credit_history_years']
miss = full[FEATURE_NUMERIC].isna().mean().sort_values(ascending=False)
dropped_for_missingness = miss[miss > 0.5].index.tolist()
FEATURE_NUMERIC = [c for c in FEATURE_NUMERIC if c not in dropped_for_missingness]
print(f"Dropped for >50% missing ({len(dropped_for_missingness)}): {dropped_for_missingness}")

dummy_cols = [c for c in full.columns if any(c.startswith(p + '_') for p in CAT_COLS)]
feature_cols = FEATURE_NUMERIC + dummy_cols

X = full[feature_cols]
y = full['default_flag']
issue_year = full['issue_year']

train_mask = (issue_year <= 2016).values
test_mask = (issue_year >= 2017).values

X_train, y_train = X[train_mask].copy(), y[train_mask].copy()
X_test, y_test = X[test_mask].copy(), y[test_mask].copy()
del full, X, y

medians = X_train.median(numeric_only=True)
X_train[FEATURE_NUMERIC] = X_train[FEATURE_NUMERIC].fillna(medians)
X_test[FEATURE_NUMERIC] = X_test[FEATURE_NUMERIC].fillna(medians)

X_train = X_train.astype(np.float32)
X_test = X_test.astype(np.float32)

print(f"Train: {X_train.shape}, default rate {y_train.mean():.4f} (issue years <= 2016)")
print(f"Test:  {X_test.shape}, default rate {y_test.mean():.4f} (issue years 2017-2018)")

X_train.to_pickle(f'{OUT}/X_train_v2.pkl')
X_test.to_pickle(f'{OUT}/X_test_v2.pkl')
y_train.to_pickle(f'{OUT}/y_train_v2.pkl')
y_test.to_pickle(f'{OUT}/y_test_v2.pkl')
medians.to_pickle(f'{OUT}/train_medians_v2.pkl')

meta = {
    'n_read_total': int(n_read),
    'n_train': int(len(X_train)), 'n_test': int(len(X_test)),
    'train_default_rate': float(y_train.mean()), 'test_default_rate': float(y_test.mean()),
    'n_features': int(X_train.shape[1]),
    'dropped_for_missingness': dropped_for_missingness,
    'feature_columns': list(X_train.columns),
    'elapsed_sec': time.time() - t0,
}
with open(f'{OUT}/features_v2_meta.json', 'w') as f:
    json.dump(meta, f, indent=2)

print(f"\nDone in {time.time()-t0:.1f}s. Saved to {OUT}/")
