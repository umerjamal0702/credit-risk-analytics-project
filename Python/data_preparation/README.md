# Data Preparation

The cleaning and exploration pass that produced the modelling datasets, carried out before any warehouse or model existed.

`data_cleaning_and_exploration.ipynb` works through the raw LendingClub accepted-loans file end to end: reading it, splitting resolved loans from loans still running, removing fields a lender would not have at the point of approval, auditing missingness, engineering the derived features, aligning the two datasets, and imputing what remained.

The notebook is left as it was worked, including the `UnicodeDecodeError` on the first attempt to count rows. The raw file is not clean UTF-8, and that is the first thing anyone working with it has to deal with.

## What it produces

| Output | Contents |
|---|---|
| `credit_risk_training_clean.csv` | Resolved loans with a known outcome, used for model training |
| `current_loan_scoring_clean.csv` | Loans still running, used for scoring |

Both files are gitignored because of their size. Running the notebook against the raw files described in `Dataset/README.md` regenerates them.

## Decisions worth noting

Loans that had not reached a final state were separated out rather than labelled. A loan still being repaid has no outcome to learn from, and treating it as non-default would understate the default rate.

Columns were dropped in several passes rather than one, because the leakage fields are not obvious from their names alone. Searching the column list for `rec_`, `recover`, `next_`, `hardship` and `settlement` surfaced fields that only exist once a loan has resolved.

Fields that were mostly empty were dropped rather than imputed. Most of them are bureau attributes LendingClub began collecting partway through the period, so their presence indicates when a loan was written rather than anything about the borrower.

Missing values were filled according to what the blank meant: `-1` where the event had never happened, `0` where the answer was none, and the median for genuinely missing numeric readings.
