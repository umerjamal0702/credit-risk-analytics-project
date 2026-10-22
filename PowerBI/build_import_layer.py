"""
Build PowerBI/import/ — a clean, import-ready copy of the extracts.

The extracts in PowerBI/extracts/ are the raw output of the SQL and modelling
steps, and they are inconsistent in two ways that cause real problems once the
data is in Power BI:

  * Rates are stored as whole numbers in the aggregate tables (6.04 meaning
    6.04%) but as fractions in the scored-loan and calibration tables (0.0604).
    Power BI's percentage format multiplies by 100, so the first kind renders
    as 604%. Every rate here is converted to a fraction.
  * Year columns arrive as floats (2008.0) because the source CSV has blanks,
    so Power Query types them as decimals and they display as 2,008.00.
    They are cast to integers here.

Column names are also lowercased and the "_pct" suffix dropped, since the
suffix would be wrong once the values are fractions.
"""
import gzip
import shutil
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
SRC = HERE / 'extracts'
OUT = HERE / 'import'
OUT.mkdir(exist_ok=True)

# column -> conversion to apply, per file
PCT_TO_FRACTION = {
    'agg_grade_scorecard.csv': ['default_rate_pct'],
    'agg_state_risk.csv': ['default_rate_pct'],
    'agg_purpose_grade_risk.csv': ['default_rate_pct'],
    'agg_recovery_by_grade.csv': ['recovery_rate_pct'],
    'agg_vintage_default_trend.csv': ['default_rate_pct', 'default_rate_3yr_avg'],
    'agg_application_volume.csv': ['acceptance_rate_pct'],
    'agg_acceptance_funnel_by_state_year.csv': ['acceptance_rate_pct'],
    'agg_accept_reject_profile.csv': ['avg_dti_pct'],
}
INT_COLS = {
    'agg_application_volume.csv': ['app_year', 'total_applications', 'accepted', 'rejected'],
    'agg_vintage_default_trend.csv': ['issue_year', 'n_resolved', 'n_default'],
    'agg_acceptance_funnel_by_state_year.csv': ['app_year'],
    'agg_accept_reject_profile.csv': ['app_year'],
    'agg_model_calibration.csv': ['decile', 'loans'],
}

written = []

for src in sorted(SRC.glob('*.csv')):
    df = pd.read_csv(src)
    name = src.name

    for col in PCT_TO_FRACTION.get(name, []):
        if col in df.columns:
            df[col] = df[col] / 100.0

    for col in INT_COLS.get(name, []):
        if col in df.columns:
            df[col] = df[col].astype('Int64')

    # drop the now-misleading _pct suffix
    df.columns = [c[:-4] if c.endswith('_pct') else c for c in df.columns]

    df.to_csv(OUT / name, index=False)
    written.append((name, len(df), len(df.columns)))

# the scored-loan fact table ships gzipped to keep the repository small;
# Power BI's CSV connector cannot read gzip, so write the plain copy here
gz = SRC / 'fact_scored_loans.csv.gz'
if gz.exists():
    with gzip.open(gz, 'rb') as fin, open(OUT / 'fact_scored_loans.csv', 'wb') as fout:
        shutil.copyfileobj(fin, fout)
    n = sum(1 for _ in open(OUT / 'fact_scored_loans.csv')) - 1
    written.append(('fact_scored_loans.csv', n, 17))

for name, rows, cols in written:
    size_kb = (OUT / name).stat().st_size / 1024
    print(f"{name:<45} {rows:>9,} rows  {cols:>3} cols  {size_kb:>9,.0f} KB")

print(f"\nWrote {len(written)} files to {OUT}")
