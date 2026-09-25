import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, roc_curve, brier_score_loss, confusion_matrix, classification_report
from sklearn.calibration import calibration_curve


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


X = pd.read_pickle(HERE / 'X_train.pkl')
y = pd.read_pickle(HERE / 'y_train.pkl')['default']
X_score = pd.read_pickle(HERE / 'X_score.pkl')
score_ids = pd.read_pickle(HERE / 'score_ids.pkl')['id']
train_ids = pd.read_pickle(HERE / 'train_ids.pkl')['id']

X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
    X, y, train_ids, test_size=0.25, random_state=42, stratify=y
)
print("Train:", X_train.shape, "Test:", X_test.shape)
print("Train default rate:", y_train.mean(), "Test default rate:", y_test.mean())

results = {}

# ---- Logistic Regression baseline (scaled) ----
scaler = StandardScaler()
X_train_s = scaler.fit_transform(X_train)
X_test_s = scaler.transform(X_test)

lr = LogisticRegression(max_iter=2000, C=0.1, class_weight='balanced')
lr.fit(X_train_s, y_train)
lr_pred = lr.predict_proba(X_test_s)[:,1]
lr_auc = roc_auc_score(y_test, lr_pred)
print("\nLogistic Regression AUC:", lr_auc)
results['logreg_auc'] = lr_auc

coefs = pd.Series(lr.coef_[0], index=X.columns).sort_values(key=abs, ascending=False)
print("Top 15 LR coefficients (standardized):")
print(coefs.head(15))
results['logreg_top_coefs'] = {k: float(v) for k,v in coefs.head(20).items()}

# ---- Gradient Boosting ----
hgb = HistGradientBoostingClassifier(
    max_iter=300, learning_rate=0.05, max_depth=6, l2_regularization=1.0,
    random_state=42
)
hgb.fit(X_train, y_train)
hgb_pred = hgb.predict_proba(X_test)[:,1]
hgb_auc = roc_auc_score(y_test, hgb_pred)
print("\nHistGradientBoosting AUC:", hgb_auc)
results['hgb_auc'] = hgb_auc

# KS statistic for HGB (chosen model)
fpr, tpr, thresh = roc_curve(y_test, hgb_pred)
ks = max(tpr - fpr)
results['hgb_ks'] = float(ks)
print("KS statistic:", ks)

brier = brier_score_loss(y_test, hgb_pred)
results['hgb_brier'] = float(brier)
print("Brier score:", brier)

# permutation-free feature importance via HGB built-in (not directly available); use simple approach:
# train sklearn's permutation_importance on a subsample for speed
from sklearn.inspection import permutation_importance
sub_idx = np.random.RandomState(42).choice(len(X_test), size=min(8000, len(X_test)), replace=False)
perm = permutation_importance(hgb, X_test.iloc[sub_idx], y_test.iloc[sub_idx], n_repeats=3, random_state=42, scoring='roc_auc', n_jobs=-1)
imp = pd.Series(perm.importances_mean, index=X.columns).sort_values(ascending=False)
print("\nTop 15 HGB permutation importances:")
print(imp.head(15))
results['hgb_top_features'] = {k: float(v) for k,v in imp.head(20).items()}

# Decide final model: use HGB if it clearly beats LR
final_model_name = 'HistGradientBoosting' if hgb_auc >= lr_auc else 'LogisticRegression'
results['final_model'] = final_model_name
print("\nFinal model selected:", final_model_name)

# Save ROC curve points for dashboard
roc_points = list(zip(fpr[::max(1,len(fpr)//200)].tolist(), tpr[::max(1,len(tpr)//200)].tolist()))
results['roc_curve_points'] = roc_points

# Calibration curve
prob_true, prob_pred = calibration_curve(y_test, hgb_pred, n_bins=10)
results['calibration'] = {'prob_true': prob_true.tolist(), 'prob_pred': prob_pred.tolist()}

# Score full dataset (test set) deciles for KS/lift table
test_out = pd.DataFrame({'id': ids_test.values, 'y_true': y_test.values, 'pd': hgb_pred})
test_out['decile'] = pd.qcut(test_out['pd'], 10, labels=False, duplicates='drop')
decile_summary = test_out.groupby('decile').agg(
    n=('y_true','count'), defaults=('y_true','sum'), avg_pd=('pd','mean')
).reset_index()
decile_summary['default_rate'] = decile_summary['defaults']/decile_summary['n']
decile_summary = decile_summary.sort_values('decile', ascending=False)
print("\nDecile table (highest risk decile first):")
print(decile_summary)
results['test_decile_table'] = decile_summary.to_dict(orient='records')

with open(HERE / 'model_results.json','w') as f:
    json.dump(results, f, indent=2, default=str)

# Save model + scaler + test predictions for later use
import pickle
with open(HERE / 'final_model.pkl','wb') as f:
    pickle.dump({'model': hgb, 'feature_names': list(X.columns)}, f)

test_out.to_csv(HERE / 'test_predictions.csv', index=False)
print("\nSaved model_results.json, final_model.pkl, test_predictions.csv")
