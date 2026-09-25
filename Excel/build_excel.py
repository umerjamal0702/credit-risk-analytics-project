import pandas as pd
import numpy as np
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment


import os
from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


FONT = 'Arial'
HEADER_FILL = PatternFill('solid', fgColor='1F4E78')
HEADER_FONT = Font(name=FONT, size=11, bold=True, color='FFFFFF')
TITLE_FONT = Font(name=FONT, size=16, bold=True, color='1F4E78')
SUBTITLE_FONT = Font(name=FONT, size=10, italic=True, color='666666')
LABEL_FONT = Font(name=FONT, size=11, bold=True)
NORMAL_FONT = Font(name=FONT, size=11)
KPI_FONT = Font(name=FONT, size=20, bold=True, color='1F4E78')
thin = Side(style='thin', color='CCCCCC')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

scored = pd.read_csv(REPO_ROOT / 'Python' / 'pd_model_v1' / 'scored_current_loans.csv')
model_results = json.load(open(REPO_ROOT / 'Python' / 'pd_model_v1' / 'model_results.json'))
scoring_summary = json.load(open(REPO_ROOT / 'Python' / 'pd_model_v1' / 'scoring_summary.json'))
eda = json.load(open(REPO_ROOT / 'Python' / 'pd_model_v1' / 'eda_results.json'))

wb = Workbook()

def style_header_row(ws, row, ncols):
    for c in range(1, ncols+1):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER

def autosize(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

# ============ SHEET 1: SUMMARY ============
ws = wb.active
ws.title = 'Summary'
ws['B2'] = 'Credit Risk Portfolio — Summary'
ws['B2'].font = TITLE_FONT
ws['B3'] = 'LendingClub-style loan book · PD model scoring · Generated {}'.format(pd.Timestamp.now().strftime('%Y-%m-%d'))
ws['B3'].font = SUBTITLE_FONT

kpis = [
    ('Active Loans Scored', scoring_summary['n_scored'], '#,##0'),
    ('Total Exposure (Funded Amt)', scoring_summary['total_exposure'], '$#,##0'),
    ('Portfolio Avg PD', scoring_summary['avg_pd'], '0.0%'),
    ('Expected Loss (LGD=100% upper bound)', scoring_summary['total_expected_loss_upper_bound'], '$#,##0'),
]
row = 5
for i, (label, val, fmt) in enumerate(kpis):
    col = 2 + i*2
    cell = ws.cell(row=row, column=col, value=label)
    cell.font = LABEL_FONT
    cell.alignment = Alignment(wrap_text=True)
    vcell = ws.cell(row=row+1, column=col, value=val)
    vcell.font = KPI_FONT
    vcell.number_format = fmt

ws['B9'] = 'Model Performance (held-out test set)'
ws['B9'].font = LABEL_FONT
model_kpis = [
    ('Model', model_results['final_model']),
    ('AUC-ROC', model_results['hgb_auc']),
    ('KS Statistic', model_results['hgb_ks']),
    ('Brier Score', model_results['hgb_brier']),
]
r = 10
ws.cell(row=r, column=2, value='Metric').font = HEADER_FONT
ws.cell(row=r, column=2).fill = HEADER_FILL
ws.cell(row=r, column=3, value='Value').font = HEADER_FONT
ws.cell(row=r, column=3).fill = HEADER_FILL
for label, val in model_kpis:
    r += 1
    ws.cell(row=r, column=2, value=label).font = NORMAL_FONT
    vc = ws.cell(row=r, column=3, value=val)
    vc.font = NORMAL_FONT
    if isinstance(val, float):
        vc.number_format = '0.000'
comment = Comment('AUC/KS/Brier computed in Python (scikit-learn HistGradientBoostingClassifier) on a 25% held-out test split (21,973 loans), stratified by default outcome. See Methodology tab.', 'Model')
ws.cell(row=11, column=3).comment = comment

ws['B16'] = 'Risk Band Distribution (current active loan book)'
ws['B16'].font = LABEL_FONT
r = 17
headers = ['Risk Band', 'Loan Count', '% of Book', 'Total Exposure', 'Avg PD', 'Expected Loss']
for i, h in enumerate(headers):
    ws.cell(row=r, column=2+i, value=h)
style_header_row(ws, r, len(headers))
band_order = ['1 - Low','2 - Low-Medium','3 - Medium','4 - Medium-High','5 - High','6 - Very High']
for bi, band in enumerate(band_order):
    rr = r + 1 + bi
    ws.cell(row=rr, column=2, value=band).font = NORMAL_FONT
    ws.cell(row=rr, column=3, value=f'=COUNTIF(Scored_Loans!$L:$L,B{rr})').number_format = '#,##0'
    ws.cell(row=rr, column=4, value=f'=C{rr}/SUM($C${r+1}:$C${r+6})').number_format = '0.0%'
    ws.cell(row=rr, column=5, value=f'=SUMIF(Scored_Loans!$L:$L,B{rr},Scored_Loans!$C:$C)').number_format = '$#,##0'
    ws.cell(row=rr, column=6, value=f'=AVERAGEIF(Scored_Loans!$L:$L,B{rr},Scored_Loans!$K:$K)').number_format = '0.0%'
    ws.cell(row=rr, column=7, value=f'=SUMIF(Scored_Loans!$L:$L,B{rr},Scored_Loans!$M:$M)').number_format = '$#,##0'
    for c in range(2,8):
        ws.cell(row=rr, column=c).border = BORDER

# bar chart of risk band exposure
chart = BarChart()
chart.title = "Exposure by Risk Band"
chart.y_axis.title = 'Exposure ($)'
chart.x_axis.title = 'Risk Band'
data = Reference(ws, min_col=5, min_row=r, max_row=r+6)
cats = Reference(ws, min_col=2, min_row=r+1, max_row=r+6)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
chart.width = 16
chart.height = 9
ws.add_chart(chart, 'I17')

autosize(ws, [3,26,16,16,18,14,16])

# ============ SHEET 2: Scored_Loans (raw data) ============
ws2 = wb.create_sheet('Scored_Loans')
cols = ['id','loan_amnt','funded_amnt','term','int_rate','grade','sub_grade','home_ownership',
        'annual_inc','purpose','addr_state','pd','risk_band','expected_loss']
# reorder scored df to a friendly column layout matching formula refs above:
# need pd in col K (11th), risk_band in col L (12th), expected_loss in col M (13th) per formulas -> adjust
export_cols = ['id','loan_amnt','funded_amnt','term','int_rate','grade','sub_grade','home_ownership','annual_inc','purpose','pd','risk_band','expected_loss']
df_export = scored[export_cols].copy()
df_export.columns = ['Loan ID','Loan Amount','Funded Amount','Term','Interest Rate','Grade','Sub-Grade','Home Ownership','Annual Income','Purpose','PD','Risk Band','Expected Loss']
for j, h in enumerate(df_export.columns, start=1):
    ws2.cell(row=1, column=j, value=h)
style_header_row(ws2, 1, len(df_export.columns))
for i, row_vals in enumerate(df_export.itertuples(index=False), start=2):
    for j, v in enumerate(row_vals, start=1):
        c = ws2.cell(row=i, column=j, value=v)
        if df_export.columns[j-1] in ('Loan Amount','Funded Amount','Expected Loss'):
            c.number_format = '$#,##0'
        elif df_export.columns[j-1] == 'Annual Income':
            c.number_format = '$#,##0'
        elif df_export.columns[j-1] == 'Interest Rate':
            c.number_format = '0.00"%"'
        elif df_export.columns[j-1] == 'PD':
            c.number_format = '0.0%'
autosize(ws2, [12,13,14,10,12,8,10,16,14,20,10,16,14])
ws2.freeze_panes = 'A2'

# ============ SHEET 3: Grade_Analysis ============
ws3 = wb.create_sheet('Grade_Analysis')
ws3['B2'] = 'Risk by Grade — Historical vs Current Book'
ws3['B2'].font = TITLE_FONT
ws3['B3'] = 'Historical default rate = actual outcomes, 87,891 completed loans (training set). Current avg PD = model score on 11,402 active loans.'
ws3['B3'].font = SUBTITLE_FONT

grade_hist = eda['default_rate_by_grade']
headers3 = ['Grade','Historical Default Rate','Historical Loan Count','Current Book: Avg PD (formula)','Current Book: Loan Count (formula)']
r = 5
for i,h in enumerate(headers3):
    ws3.cell(row=r, column=2+i, value=h)
style_header_row(ws3, r, len(headers3))
grades = ['A','B','C','D','E','F','G']
for gi, g in enumerate(grades):
    rr = r+1+gi
    ws3.cell(row=rr, column=2, value=g).font=NORMAL_FONT
    hv = grade_hist.get(g, {'rate':0,'count':0})
    c_rate = ws3.cell(row=rr, column=3, value=hv['rate']); c_rate.number_format='0.0%'
    c_cnt = ws3.cell(row=rr, column=4, value=hv['count']); c_cnt.number_format='#,##0'
    c_rate.comment = Comment('Source: training data EDA (credit_risk_training_clean.csv), actual Charged Off rate by LendingClub grade.', 'EDA')
    ws3.cell(row=rr, column=5, value=f'=AVERAGEIF(Scored_Loans!$F:$F,B{rr},Scored_Loans!$K:$K)').number_format='0.0%'
    ws3.cell(row=rr, column=6, value=f'=COUNTIF(Scored_Loans!$F:$F,B{rr})').number_format='#,##0'
    for c in range(2,7):
        ws3.cell(row=rr, column=c).border = BORDER

chart3 = BarChart()
chart3.title = 'Default Rate: Historical (train) vs Avg PD (current book), by Grade'
chart3.y_axis.title = 'Rate'
chart3.x_axis.title = 'Grade'
d1 = Reference(ws3, min_col=3, min_row=r, max_row=r+7)
d2 = Reference(ws3, min_col=5, min_row=r, max_row=r+7)
cats3 = Reference(ws3, min_col=2, min_row=r+1, max_row=r+7)
chart3.add_data(d1, titles_from_data=True)
chart3.add_data(d2, titles_from_data=True)
chart3.set_categories(cats3)
chart3.width=18; chart3.height=10
ws3.add_chart(chart3, 'B16')
autosize(ws3, [3,10,22,20,26,26])

# ============ SHEET 4: Model_Performance ============
ws4 = wb.create_sheet('Model_Performance')
ws4['B2'] = 'PD Model Performance — Decile (Lift) Table'
ws4['B2'].font = TITLE_FONT
ws4['B3'] = 'Held-out test set, 21,973 loans not used in training. Decile 10 = highest predicted risk.'
ws4['B3'].font = SUBTITLE_FONT
headers4 = ['Decile (10=highest risk)','Loans','Actual Defaults','Avg Predicted PD','Actual Default Rate']
r = 5
for i,h in enumerate(headers4):
    ws4.cell(row=r, column=2+i, value=h)
style_header_row(ws4, r, len(headers4))
dt = sorted(model_results['test_decile_table'], key=lambda x: -x['decile'])
for i, rowd in enumerate(dt):
    rr = r+1+i
    ws4.cell(row=rr, column=2, value=int(rowd['decile'])+1).font=NORMAL_FONT
    ws4.cell(row=rr, column=3, value=int(rowd['n'])).number_format='#,##0'
    ws4.cell(row=rr, column=4, value=int(rowd['defaults'])).number_format='#,##0'
    ws4.cell(row=rr, column=5, value=rowd['avg_pd']).number_format='0.0%'
    ws4.cell(row=rr, column=6, value=rowd['default_rate']).number_format='0.0%'
    for c in range(2,7):
        ws4.cell(row=rr, column=c).border = BORDER

chart4 = LineChart()
chart4.title = 'Lift Chart: Actual Default Rate by Predicted-Risk Decile'
chart4.y_axis.title = 'Actual Default Rate'
chart4.x_axis.title = 'Decile'
d4 = Reference(ws4, min_col=6, min_row=r, max_row=r+10)
cats4 = Reference(ws4, min_col=2, min_row=r+1, max_row=r+10)
chart4.add_data(d4, titles_from_data=True)
chart4.set_categories(cats4)
chart4.width=18; chart4.height=10
ws4.add_chart(chart4, 'B18')

ws4['I5'] = 'Top Feature Importances (permutation, AUC-based)'
ws4['I5'].font = LABEL_FONT
ws4.cell(row=6, column=9, value='Feature').font=HEADER_FONT
ws4.cell(row=6, column=9).fill = HEADER_FILL
ws4.cell(row=6, column=10, value='Importance').font=HEADER_FONT
ws4.cell(row=6, column=10).fill = HEADER_FILL
for i,(feat,imp) in enumerate(list(model_results['hgb_top_features'].items())[:15]):
    rr = 7+i
    ws4.cell(row=rr, column=9, value=feat).font=NORMAL_FONT
    ws4.cell(row=rr, column=10, value=imp).number_format='0.0000'
autosize(ws4, [3,24,10,16,18,18,3,3,26,14])

# ============ SHEET 5: Methodology ============
ws5 = wb.create_sheet('Methodology')
ws5['B2'] = 'Methodology & Assumptions'
ws5['B2'].font = TITLE_FONT
lines = [
    ('Data source', 'LendingClub-style accepted loan data. Training set: 87,891 completed loans (Fully Paid / Charged Off, issued 2015). Scoring set: 11,402 currently active loans.'),
    ('Target definition', 'default = 1 if loan_status == "Charged Off", else 0. Overall training charge-off rate: {:.1%}.'.format(eda['overall_default_rate'])),
    ('Leakage columns excluded', 'total_rec_prncp, total_rec_int, total_rec_late_fee, last_fico_range_high, last_fico_range_low — all reflect loan performance during/after origination and were excluded to avoid target leakage.'),
    ('Features used', '~191 features after one-hot encoding: origination terms (loan amount, term, rate, installment), credit bureau attributes at application (FICO, DTI, revolving utilization, trade line counts, delinquency history), and categoricals (grade, sub-grade, purpose, home ownership, state, verification status, application type).'),
    ('Model', 'HistGradientBoostingClassifier (scikit-learn), 300 iterations, depth 6, learning rate 0.05, selected over a logistic regression baseline (AUC {:.3f} vs {:.3f}).'.format(model_results['hgb_auc'], model_results['logreg_auc'])),
    ('Validation', '75/25 stratified train/test split, random_state=42. Metrics reported on the untouched 25% test set.'),
    ('Risk bands', '1-Low (PD<6%), 2-Low-Medium (6-12%), 3-Medium (12-20%), 4-Medium-High (20-30%), 5-High (30-45%), 6-Very High (PD>=45%). Thresholds set judgmentally to roughly track historical LendingClub grade default rates.'),
    ('Expected loss', 'PD x funded amount, assuming LGD = 100% (i.e., an upper bound — no recovery/collateral data available in this dataset). Actual expected loss would be lower given partial recoveries.'),
    ('Known limitation', 'The active loan book skews toward riskier grades than the training population (grade A = 3.7% of current book vs 19.4% of training set), which explains why average current-book PD (33%) exceeds the training base rate (20%) — this is a portfolio composition effect, not a model calibration issue.'),
]
r = 4
for label, text in lines:
    ws5.cell(row=r, column=2, value=label).font = LABEL_FONT
    ws5.cell(row=r, column=2).alignment = Alignment(vertical='top')
    c = ws5.cell(row=r, column=3, value=text)
    c.font = NORMAL_FONT
    c.alignment = Alignment(wrap_text=True, vertical='top')
    ws5.row_dimensions[r].height = 45
    r += 2
autosize(ws5, [3,20,110])
ws5.column_dimensions['C'].width = 110

wb.save(HERE / 'credit_risk_analysis.xlsx')
print("Saved workbook")
