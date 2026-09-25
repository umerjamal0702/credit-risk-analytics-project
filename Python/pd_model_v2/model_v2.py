"""
PD model v2 — trained on the full out-of-time split (train issue years
<=2016, 1.10M loans; test 2017-2018, 245K loans) built by features_v2.py.
Mirrors the v1 model comparison (Logistic Regression baseline vs
HistGradientBoostingClassifier) so the two are a fair head-to-head, but
this time validated out-of-time rather than on a random split of a
single vintage — the harder, more realistic test.
"""
import pandas as pd
import numpy as np
import time, json, pickle
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss, roc_curve
from sklearn.inspection import permutation_importance


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


OUT = str(HERE)
t0 = time.time()

X_train = pd.read_pickle(f'{OUT}/X_train_v2.pkl')
X_test = pd.read_pickle(f'{OUT}/X_test_v2.pkl')
y_train = pd.read_pickle(f'{OUT}/y_train_v2.pkl')
y_test = pd.read_pickle(f'{OUT}/y_test_v2.pkl')
print(f"Loaded: train {X_train.shape}, test {X_test.shape}, {time.time()-t0:.1f}s")

def ks_stat(y_true, y_score):
    fpr, tpr, _ = roc_curve(y_true, y_score)
    return float(np.max(np.abs(tpr - fpr)))

def decile_table(y_true, y_score, n=10):
    df = pd.DataFrame({'y': y_true.values, 'score': y_score})
    df['decile'] = pd.qcut(df['score'].rank(method='first'), n, labels=False)
    rows = []
    overall_rate = df['y'].mean()
    for d in range(n):
        sub = df[df['decile'] == d]
        rows.append({
            'decile': int(d) + 1,  # 1 = lowest predicted risk .. 10 = highest
            'n': int(len(sub)),
            'avg_pd': float(sub['score'].mean()),
            'actual_default_rate': float(sub['y'].mean()),
            'lift': float(sub['y'].mean() / overall_rate) if overall_rate > 0 else None,
        })
    return rows

results = {}

# ---------------------------------------------------------------------
# Model 1: Logistic Regression baseline (scaled, class-balanced)
# ---------------------------------------------------------------------
t1 = time.time()
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

logreg = LogisticRegression(C=0.1, class_weight='balanced', max_iter=1000, n_jobs=-1)
logreg.fit(X_train_s, y_train)
p_lr = logreg.predict_proba(X_test_s)[:, 1]

results['logistic_regression'] = {
    'auc': float(roc_auc_score(y_test, p_lr)),
    'ks': ks_stat(y_test, p_lr),
    'brier': float(brier_score_loss(y_test, p_lr)),
    'train_seconds': time.time() - t1,
    'decile_table': decile_table(y_test, p_lr),
}
print(f"LogisticRegression: AUC={results['logistic_regression']['auc']:.4f} "
      f"KS={results['logistic_regression']['ks']:.4f} "
      f"Brier={results['logistic_regression']['brier']:.4f} "
      f"({time.time()-t1:.1f}s)")

# ---------------------------------------------------------------------
# Model 2: HistGradientBoostingClassifier
# ---------------------------------------------------------------------
t1 = time.time()
hgb = HistGradientBoostingClassifier(
    max_iter=300, learning_rate=0.05, max_depth=6, l2_regularization=1.0,
    random_state=42,
)
hgb.fit(X_train, y_train)
p_hgb = hgb.predict_proba(X_test)[:, 1]

results['hist_gradient_boosting'] = {
    'auc': float(roc_auc_score(y_test, p_hgb)),
    'ks': ks_stat(y_test, p_hgb),
    'brier': float(brier_score_loss(y_test, p_hgb)),
    'train_seconds': time.time() - t1,
    'decile_table': decile_table(y_test, p_hgb),
}
print(f"HistGradientBoosting: AUC={results['hist_gradient_boosting']['auc']:.4f} "
      f"KS={results['hist_gradient_boosting']['ks']:.4f} "
      f"Brier={results['hist_gradient_boosting']['brier']:.4f} "
      f"({time.time()-t1:.1f}s)")

# ---------------------------------------------------------------------
# Permutation importance for the better model (on a subsample for speed)
# ---------------------------------------------------------------------
best_name = 'hist_gradient_boosting' if results['hist_gradient_boosting']['auc'] >= results['logistic_regression']['auc'] else 'logistic_regression'
best_model = hgb if best_name == 'hist_gradient_boosting' else logreg
print(f"Best model: {best_name}. Computing permutation importance on a 30K-row sample...")

t1 = time.time()
rng = np.random.RandomState(42)
sample_idx = rng.choice(len(X_test), size=min(30000, len(X_test)), replace=False)
X_imp = X_test.iloc[sample_idx] if best_name == 'hist_gradient_boosting' else X_test_s[sample_idx]
y_imp = y_test.iloc[sample_idx]

perm = permutation_importance(best_model, X_imp, y_imp, n_repeats=5, random_state=42,
                               scoring='roc_auc', n_jobs=-1)
feat_names = list(X_train.columns)
importance_pairs = sorted(zip(feat_names, perm.importances_mean), key=lambda x: -x[1])[:25]
results['top_permutation_importance'] = [{'feature': f, 'importance': float(v)} for f, v in importance_pairs]
print(f"Permutation importance done ({time.time()-t1:.1f}s). Top 10:")
for f, v in importance_pairs[:10]:
    print(f"  {f}: {v:.5f}")

# ---------------------------------------------------------------------
# Comparison vs v1 (recorded from prior run)
# ---------------------------------------------------------------------
V1_RESULTS = {
    'note': 'v1 trained on an 87,891-row 2015-only sample with a RANDOM 80/20 split '
            '(not out-of-time); v2 trains on 1,103,084 loans (2007-2016) and tests '
            'out-of-time on 245,015 loans (2017-2018) — a materially harder, more '
            'realistic validation.',
}

meta = {
    'best_model': best_name,
    'results': results,
    'v1_comparison_note': V1_RESULTS,
    'n_train': int(len(X_train)),
    'n_test': int(len(X_test)),
    'elapsed_sec': time.time() - t0,
}
with open(f'{OUT}/model_v2_results.json', 'w') as f:
    json.dump(meta, f, indent=2)

with open(f'{OUT}/final_model_v2.pkl', 'wb') as f:
    pickle.dump({'model': best_model, 'model_name': best_name, 'scaler': scaler if best_name == 'logistic_regression' else None,
                 'feature_columns': feat_names}, f)

pd.DataFrame({'y_true': y_test.values, 'pd_logreg': p_lr, 'pd_hgb': p_hgb}).to_csv(
    f'{OUT}/test_predictions_v2.csv', index=False)

print(f"\nDone in {time.time()-t0:.1f}s. Results saved to model_v2_results.json")
