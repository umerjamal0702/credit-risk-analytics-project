# Dataset

The raw data files are not committed to this repository because of their size
(roughly 1.2 GB compressed in total, well beyond GitHub's file size limits).

## Source

LendingClub loan data, 2007 to 2018 Q4, available on Kaggle:
https://www.kaggle.com/datasets/wordsforthewise/lending-club

## Files required

Download the dataset and place the following files in this folder:

| File | Rows | Columns | Description |
|----------|----------|----------|----------|
| accepted_2007_to_2018Q4.csv.gz | 2,260,701 | 151 | Funded loans with full origination attributes and payment history |
| rejected_2007_to_2018Q4.csv.gz | 27,648,741 | 9 | Declined applications: amount requested, DTI, state, employment length, risk score, application date |

The two sample files used by the v1 model (`credit_risk_training_clean.csv` and
`current_loan_scoring_clean.csv`) are cleaned 2015-vintage extracts derived from the
accepted file.

## Rebuilding the analysis

Once the files are in place, run the scripts in this order:

```bash
python SQL/00_build_warehouse.py          # builds SQL/credit_risk_warehouse.db (~4.5 GB)
python Python/pd_model_v2/features_v2.py  # builds the out-of-time feature split
python Python/pd_model_v2/model_v2.py     # trains and evaluates the PD model
python Python/reject_inference_model/accept_reject_model.py
```

The warehouse database and all intermediate model artifacts are excluded from version
control and regenerate from these scripts.
