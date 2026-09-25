import sqlite3, csv, gzip, time, os


from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


DB_PATH = str(HERE / 'credit_risk_warehouse.db')
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
conn.execute('PRAGMA journal_mode=OFF')
conn.execute('PRAGMA synchronous=OFF')
conn.execute('PRAGMA temp_store=MEMORY')
conn.execute('PRAGMA cache_size=-200000')  # 200MB cache

# ------------------------------------------------------------------
# raw_accepted: curated column set from the full 2007-2018 accepted file
# ------------------------------------------------------------------
KEEP_ACCEPTED = [
    'id','loan_amnt','funded_amnt','funded_amnt_inv','term','int_rate','installment',
    'grade','sub_grade','emp_title','emp_length','home_ownership','annual_inc',
    'verification_status','issue_d','loan_status','pymnt_plan','purpose','zip_code',
    'addr_state','dti','delinq_2yrs','earliest_cr_line','fico_range_low','fico_range_high',
    'inq_last_6mths','mths_since_last_delinq','mths_since_last_record','open_acc','pub_rec',
    'revol_bal','revol_util','total_acc','initial_list_status',
    'out_prncp','out_prncp_inv','total_pymnt','total_pymnt_inv','total_rec_prncp',
    'total_rec_int','total_rec_late_fee','recoveries','collection_recovery_fee',
    'last_pymnt_d','last_pymnt_amnt','last_credit_pull_d','last_fico_range_high','last_fico_range_low',
    'collections_12_mths_ex_med','mths_since_last_major_derog','application_type',
    'annual_inc_joint','dti_joint','acc_now_delinq','tot_coll_amt','tot_cur_bal','mort_acc',
    'mo_sin_old_il_acct','mo_sin_old_rev_tl_op','mo_sin_rcnt_rev_tl_op','mo_sin_rcnt_tl',
    'num_accts_ever_120_pd','num_actv_bc_tl','num_actv_rev_tl','num_bc_sats','num_bc_tl',
    'num_il_tl','num_op_rev_tl','num_rev_accts','num_rev_tl_bal_gt_0','num_sats',
    'num_tl_120dpd_2m','num_tl_30dpd','num_tl_90g_dpd_24m','num_tl_op_past_12m',
    'pct_tl_nvr_dlq','percent_bc_gt_75','pub_rec_bankruptcies','tax_liens','tot_hi_cred_lim',
    'total_bal_ex_mort','total_bc_limit','total_il_high_credit_limit','avg_cur_bal',
    'bc_open_to_buy','bc_util','chargeoff_within_12_mths','delinq_amnt','acc_open_past_24mths',
    'inq_last_12m','all_util','total_rev_hi_lim','open_acc_6m','open_il_12m','open_il_24m',
    'open_rv_12m','open_rv_24m','il_util','max_bal_bc','mths_since_rcnt_il','total_bal_il',
    'hardship_flag','debt_settlement_flag',
]

t0 = time.time()
with gzip.open(DATASET / 'accepted_2007_to_2018Q4.csv.gz', 'rt') as f:
    reader = csv.reader(f)
    header = next(reader)
    idx = {h: i for i, h in enumerate(header)}
    missing = [c for c in KEEP_ACCEPTED if c not in idx]
    if missing:
        raise SystemExit(f"Missing columns: {missing}")
    col_positions = [idx[c] for c in KEEP_ACCEPTED]

    cols_sql = ', '.join(f'"{c}" TEXT' for c in KEEP_ACCEPTED)
    conn.execute(f'CREATE TABLE raw_accepted ({cols_sql})')
    placeholders = ','.join(['?'] * len(KEEP_ACCEPTED))
    insert_sql = f'INSERT INTO raw_accepted VALUES ({placeholders})'

    n = 0
    batch = []
    for row in reader:
        if len(row) < len(header):
            continue
        # skip blank/summary rows (LendingClub files sometimes have trailing summary lines)
        if not row[idx['id']] or not row[idx['id']].strip().isdigit():
            continue
        batch.append([row[p] for p in col_positions])
        n += 1
        if len(batch) >= 50000:
            conn.executemany(insert_sql, batch)
            batch = []
    if batch:
        conn.executemany(insert_sql, batch)
conn.commit()
print(f"raw_accepted: {n:,} rows loaded in {time.time()-t0:.1f}s")

# ------------------------------------------------------------------
# raw_rejected: full 27.6M-row rejected applications file
# ------------------------------------------------------------------
t0 = time.time()
conn.execute('''CREATE TABLE raw_rejected (
    amount_requested TEXT, application_date TEXT, loan_title TEXT, risk_score TEXT,
    dti_pct TEXT, zip_code TEXT, state TEXT, emp_length TEXT, policy_code TEXT
)''')
with gzip.open(DATASET / 'rejected_2007_to_2018Q4.csv.gz', 'rt') as f:
    reader = csv.reader(f)
    header = next(reader)
    n = 0
    batch = []
    for row in reader:
        if len(row) < 9:
            continue
        batch.append(row[:9])
        n += 1
        if len(batch) >= 100000:
            conn.executemany('INSERT INTO raw_rejected VALUES (?,?,?,?,?,?,?,?,?)', batch)
            batch = []
    if batch:
        conn.executemany('INSERT INTO raw_rejected VALUES (?,?,?,?,?,?,?,?,?)', batch)
conn.commit()
print(f"raw_rejected: {n:,} rows loaded in {time.time()-t0:.1f}s")

# ------------------------------------------------------------------
# Indexes (built after bulk load, standard warehouse practice)
# ------------------------------------------------------------------
t0 = time.time()
conn.execute('CREATE INDEX idx_accepted_grade ON raw_accepted(grade)')
conn.execute('CREATE INDEX idx_accepted_state ON raw_accepted(addr_state)')
conn.execute('CREATE INDEX idx_accepted_status ON raw_accepted(loan_status)')
conn.execute('CREATE INDEX idx_accepted_issue_d ON raw_accepted(issue_d)')
conn.execute('CREATE INDEX idx_rejected_state ON raw_rejected(state)')
conn.execute('CREATE INDEX idx_rejected_date ON raw_rejected(application_date)')
conn.commit()
print(f"Indexes built in {time.time()-t0:.1f}s")

# row counts sanity check
for t in ('raw_accepted', 'raw_rejected'):
    c = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    print(t, 'row count:', f'{c:,}')

conn.close()
print("Done. DB size:", os.path.getsize(DB_PATH)/1e6, "MB")
