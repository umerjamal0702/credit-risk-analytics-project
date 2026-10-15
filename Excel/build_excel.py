"""
Build credit_risk_analysis.xlsx from the v2 model results.

Every figure comes from Python/pd_model_v2/deliverable_data_v2.json, the same
payload the Word report reads, so the two deliverables cannot disagree.

Convention used throughout: blue text marks a hardcoded input carried in from
the model pipeline; black text marks a cell Excel computes. Run recalc.py on
the output afterwards — openpyxl writes formulas with no cached values, so the
charts render blank until the workbook has been recalculated once.
"""
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

REPO_ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent

FONT = 'Arial'
HEADER_FILL = PatternFill('solid', fgColor='1F4E78')
HEADER_FONT = Font(name=FONT, size=11, bold=True, color='FFFFFF')
TITLE_FONT = Font(name=FONT, size=16, bold=True, color='1F4E78')
SUBTITLE_FONT = Font(name=FONT, size=10, italic=True, color='666666')
LABEL_FONT = Font(name=FONT, size=11, bold=True)
NORMAL_FONT = Font(name=FONT, size=11)
INPUT_FONT = Font(name=FONT, size=11, color='0000FF')      # carried-in value
KPI_FONT = Font(name=FONT, size=20, bold=True, color='1F4E78')
thin = Side(style='thin', color='CCCCCC')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

D = json.load(open(REPO_ROOT / 'Python' / 'pd_model_v2' / 'deliverable_data_v2.json'))
model, scoring, portfolio, rj = D['model'], D['scoring'], D['portfolio'], D['reject_inference']

wb = Workbook()


def style_header_row(ws, row, ncols, start_col=2):
    for c in range(start_col, start_col + ncols):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER


def autosize(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def put(ws, row, col, value, fmt=None, font=NORMAL_FONT, border=True):
    c = ws.cell(row=row, column=col, value=value)
    c.font = font
    if fmt:
        c.number_format = fmt
    if border:
        c.border = BORDER
    return c


# ===================== SHEET 1: SUMMARY =====================
ws = wb.active
ws.title = 'Summary'
ws['B2'] = 'Credit Risk Portfolio — Summary (PD Model v2)'
ws['B2'].font = TITLE_FONT
ws['B3'] = ('LendingClub loan book 2007–2018 · model validated out-of-time: trained on '
            f"{model['n_train']:,} loans issued up to 2016, scored on {model['n_test']:,} "
            'loans issued 2017–2018 that it never saw during training')
ws['B3'].font = SUBTITLE_FONT

# The KPI values render at 20pt, where a full $3,259,579,400 would need a column
# roughly twice as wide as the table below it needs. Scaled formats keep the tiles
# readable ($3.26B / $662.6M) while the cells still hold the exact underlying value;
# the band table below shows the figures in full.
kpis = [
    ('Loans Scored (out-of-time)', scoring['n_scored'], '#,##0'),
    ('Total Exposure (Funded Amt)', scoring['total_exposure'], '$#,##0.00,,,"B"'),
    ('Avg Predicted PD', scoring['avg_predicted_pd'], '0.0%'),
    ('Actual Default Rate', scoring['actual_default_rate'], '0.0%'),
    ('Expected Loss (LGD 90%)', scoring['expected_loss'], '$#,##0.0,,"M"'),
]
for i, (label, val, fmt) in enumerate(kpis):
    col = 2 + i * 2
    lc = ws.cell(row=5, column=col, value=label)
    lc.font = LABEL_FONT
    lc.alignment = Alignment(wrap_text=True, vertical='bottom')
    vc = ws.cell(row=6, column=col, value=val)
    vc.font = KPI_FONT
    vc.number_format = fmt

ws['B8'] = 'Expected vs actual loss'
ws['B8'].font = LABEL_FONT
put(ws, 9, 2, 'Expected loss (PD × exposure × 90% LGD)', border=False)
put(ws, 9, 4, scoring['expected_loss'], '$#,##0', INPUT_FONT, border=False)
put(ws, 10, 2, 'Actual loss on the same loans', border=False)
put(ws, 10, 4, scoring['actual_loss'], '$#,##0', INPUT_FONT, border=False)
put(ws, 11, 2, 'Variance (model under/over-prediction)', None, LABEL_FONT, border=False)
v = put(ws, 11, 4, '=D9/D10-1', '0.0%', NORMAL_FONT, border=False)
v.comment = Comment(
    'Negative means the model under-predicted losses on the out-of-time test set. '
    'Expected loss applies a 90% loss given default, measured from actual recovery '
    'data on charged-off loans rather than assumed. See the Recovery_LGD tab.', 'Model v2')

ws['B13'] = 'Model performance (out-of-time test set)'
ws['B13'].font = LABEL_FONT
r = 14
ws.cell(row=r, column=2, value='Metric')
ws.cell(row=r, column=3, value='v2 (out-of-time)')
ws.cell(row=r, column=4, value='v1 (random split)')
style_header_row(ws, r, 3)
v1 = model['v1_comparison']
perf_rows = [
    ('AUC-ROC', model['hgb_auc'], v1['auc'], '0.000'),
    ('KS statistic', model['hgb_ks'], v1['ks'], '0.000'),
    ('Brier score', model['hgb_brier'], v1['brier'], '0.000'),
    ('Training loans', model['n_train'], v1['n_train'], '#,##0'),
    ('Test loans', model['n_test'], v1['n_test'], '#,##0'),
]
for i, (label, a, b, fmt) in enumerate(perf_rows):
    rr = r + 1 + i
    put(ws, rr, 2, label)
    put(ws, rr, 3, a, fmt, INPUT_FONT)
    put(ws, rr, 4, b, fmt, INPUT_FONT)
ws.cell(row=r + 1, column=3).comment = Comment(
    'v2 scores lower than v1 despite training on seventeen times more data. v1 used a '
    'random 75/25 split inside a single 2015 vintage, which lets loans from the same '
    'period sit on both sides of the split; v2 trains on loans issued up to 2016 and '
    'tests on 2017–2018 only. Out-of-time validation is the harder, more realistic test.',
    'Model v2')

ws['B21'] = 'Risk band distribution (out-of-time scored book)'
ws['B21'].font = LABEL_FONT
r = 22
headers = ['Risk Band', 'Loan Count', '% of Book', 'Total Exposure', 'Avg Predicted PD',
           'Actual Default Rate', 'Expected Loss', 'Actual Loss', 'Variance']
for i, h in enumerate(headers):
    ws.cell(row=r, column=2 + i, value=h)
style_header_row(ws, r, len(headers))
first_band_row = r + 1
for bi, b in enumerate(scoring['risk_bands']):
    rr = first_band_row + bi
    put(ws, rr, 2, b['band'])
    put(ws, rr, 3, b['count'], '#,##0', INPUT_FONT)
    put(ws, rr, 4, f'=C{rr}/SUM($C${first_band_row}:$C${first_band_row + 5})', '0.0%')
    put(ws, rr, 5, b['exposure'], '$#,##0', INPUT_FONT)
    put(ws, rr, 6, b['avg_predicted_pd'], '0.0%', INPUT_FONT)
    put(ws, rr, 7, b['actual_default_rate'], '0.0%', INPUT_FONT)
    # Expected loss is the sum of per-loan PD x funded x LGD within the band, not
    # the band's average PD applied to its total exposure — those differ by about
    # 0.4% here because larger loans score slightly differently. Carried in so the
    # column reconciles exactly with the headline figure above.
    put(ws, rr, 8, b['expected_loss'], '$#,##0', INPUT_FONT)
    put(ws, rr, 9, b['actual_loss'], '$#,##0', INPUT_FONT)
    put(ws, rr, 10, f'=H{rr}/I{rr}-1', '0.0%')
total_row = first_band_row + 6
put(ws, total_row, 2, 'Total', None, LABEL_FONT)
for col, idx in (('C', 3), ('E', 5), ('H', 8), ('I', 9)):
    put(ws, total_row, idx,
        f'=SUM({col}{first_band_row}:{col}{total_row - 1})',
        '#,##0' if col == 'C' else '$#,##0', LABEL_FONT)
put(ws, total_row, 4, f'=SUM(D{first_band_row}:D{total_row - 1})', '0.0%', LABEL_FONT)
put(ws, total_row, 10, f'=H{total_row}/I{total_row}-1', '0.0%', LABEL_FONT)

ws['B36'] = 'Loss given default (LGD) assumption'
ws['B36'].font = LABEL_FONT
lgd_cell = put(ws, 36, 4, scoring['lgd_assumption'], '0.0%', INPUT_FONT, border=False)
lgd_cell.comment = Comment(
    'Measured, not assumed: recoveries through collections return only 10.0%–11.6% of the '
    'unpaid balance on charged-off loans, and that holds across every risk grade. The v1 '
    'workbook used a flat 100% LGD placeholder. See the Recovery_LGD tab.', 'Model v2')

chart = BarChart()
chart.title = 'Exposure by Risk Band'
chart.y_axis.title = 'Exposure ($)'
chart.x_axis.title = 'Risk Band'
chart.add_data(Reference(ws, min_col=5, min_row=r, max_row=r + 6), titles_from_data=True)
chart.set_categories(Reference(ws, min_col=2, min_row=first_band_row, max_row=r + 6))
chart.width, chart.height = 16, 9
ws.add_chart(chart, 'K22')

# Columns B/D/F/H/J carry both the KPI tiles and the band table, so they are
# sized for the widest value either one holds — $3,259,579,400 needs 17.
autosize(ws, [3, 30, 15, 17, 18, 15, 16, 17, 17, 16])

# ===================== SHEET 2: WATCHLIST =====================
ws2 = wb.create_sheet('Watchlist')
ws2['B2'] = 'Highest-Risk Loans — Watchlist'
ws2['B2'].font = TITLE_FONT
ws2['B3'] = (f"Top 20 of {scoring['n_scored']:,} scored loans by predicted PD. The Outcome "
             f"column records what actually happened: {scoring['top20_actual_defaults']} of "
             'these 20 went on to default.')
ws2['B3'].font = SUBTITLE_FONT
headers2 = ['Loan ID', 'Funded Amount', 'Grade', 'Purpose', 'State', 'Predicted PD',
            'Risk Band', 'Expected Loss', 'Outcome']
r = 5
for i, h in enumerate(headers2):
    ws2.cell(row=r, column=2 + i, value=h)
style_header_row(ws2, r, len(headers2))
for i, w in enumerate(scoring['top20_highest_risk']):
    rr = r + 1 + i
    put(ws2, rr, 2, w['id'], '0')
    put(ws2, rr, 3, w['loan_amnt'], '$#,##0', INPUT_FONT)
    put(ws2, rr, 4, w['sub_grade'])
    put(ws2, rr, 5, w['purpose'].replace('_', ' ').title())
    put(ws2, rr, 6, w['addr_state'])
    put(ws2, rr, 7, w['pd'], '0.0%', INPUT_FONT)
    put(ws2, rr, 8, w['risk_band'])
    put(ws2, rr, 9, f'=C{rr}*G{rr}*Summary!$D$36', '$#,##0')
    put(ws2, rr, 10, 'Defaulted' if w['actual_default'] else 'Repaid')
summary_row = r + 21
put(ws2, summary_row, 2, 'Defaulted (of 20)', None, LABEL_FONT)
put(ws2, summary_row, 3, f'=COUNTIF(J{r + 1}:J{r + 20},"Defaulted")', '#,##0', LABEL_FONT)
put(ws2, summary_row, 4, f'=C{summary_row}/20', '0.0%', LABEL_FONT)
autosize(ws2, [3, 18, 15, 9, 22, 8, 13, 16, 15, 12])
ws2.freeze_panes = 'A6'

# ===================== SHEET 3: GRADE ANALYSIS =====================
ws3 = wb.create_sheet('Grade_Analysis')
ws3['B2'] = 'Risk by Grade'
ws3['B2'].font = TITLE_FONT
ws3['B3'] = ('Predicted vs actual measured on the out-of-time test set. The scorecard below '
             f"covers all {portfolio['n_resolved_loans']:,} resolved loans in the warehouse.")
ws3['B3'].font = SUBTITLE_FONT

headers3 = ['Grade', 'Predicted PD', 'Actual Default Rate', 'Gap (pp)', 'Loans Scored']
r = 5
for i, h in enumerate(headers3):
    ws3.cell(row=r, column=2 + i, value=h)
style_header_row(ws3, r, len(headers3))
for gi, g in enumerate(scoring['grade_predicted_vs_actual']):
    rr = r + 1 + gi
    put(ws3, rr, 2, g['grade'])
    put(ws3, rr, 3, g['predicted_pd'], '0.0%', INPUT_FONT)
    put(ws3, rr, 4, g['actual_default_rate'], '0.0%', INPUT_FONT)
    put(ws3, rr, 5, f'=C{rr}-D{rr}', '0.0%')
    put(ws3, rr, 6, g['count'], '#,##0', INPUT_FONT)

chart3 = BarChart()
chart3.title = 'Predicted PD vs Actual Default Rate, by Grade'
chart3.y_axis.title = 'Rate'
chart3.x_axis.title = 'Grade'
chart3.add_data(Reference(ws3, min_col=3, min_row=r, max_row=r + 7), titles_from_data=True)
chart3.add_data(Reference(ws3, min_col=4, min_row=r, max_row=r + 7), titles_from_data=True)
chart3.set_categories(Reference(ws3, min_col=2, min_row=r + 1, max_row=r + 7))
chart3.width, chart3.height = 18, 10
ws3.add_chart(chart3, 'H5')

ws3['B15'] = 'Full-history grade scorecard (all resolved loans)'
ws3['B15'].font = LABEL_FONT
headers3b = ['Grade', 'Loans', 'Total Funded', 'Wtd Avg Rate', 'Default Rate',
             'Net Loss', 'Loss Rate (% of funded)']
r2 = 16
for i, h in enumerate(headers3b):
    ws3.cell(row=r2, column=2 + i, value=h)
style_header_row(ws3, r2, len(headers3b))
for gi, g in enumerate(portfolio['grade_scorecard']):
    rr = r2 + 1 + gi
    put(ws3, rr, 2, g['grade'])
    put(ws3, rr, 3, g['n_loans'], '#,##0', INPUT_FONT)
    put(ws3, rr, 4, g['total_funded'], '$#,##0', INPUT_FONT)
    put(ws3, rr, 5, g['wavg_int_rate'] / 100, '0.0%', INPUT_FONT)
    put(ws3, rr, 6, g['default_rate'], '0.0%', INPUT_FONT)
    put(ws3, rr, 7, g['total_net_loss'], '$#,##0', INPUT_FONT)
    put(ws3, rr, 8, f'=G{rr}/D{rr}', '0.0%')
autosize(ws3, [3, 10, 16, 20, 14, 16, 18, 22])

# ===================== SHEET 4: MODEL PERFORMANCE =====================
ws4 = wb.create_sheet('Model_Performance')
ws4['B2'] = 'PD Model v2 Performance — Decile (Lift) Table'
ws4['B2'].font = TITLE_FONT
ws4['B3'] = (f"Out-of-time test set: {model['n_test']:,} loans issued 2017–2018, none of which "
             'the model saw during training. Decile 10 = highest predicted risk.')
ws4['B3'].font = SUBTITLE_FONT
headers4 = ['Decile (10=highest risk)', 'Loans', 'Avg Predicted PD', 'Actual Default Rate',
            'Gap (pp)', 'Lift vs Portfolio']
r = 5
for i, h in enumerate(headers4):
    ws4.cell(row=r, column=2 + i, value=h)
style_header_row(ws4, r, len(headers4))
for i, d in enumerate(sorted(model['decile_table'], key=lambda x: -x['decile'])):
    rr = r + 1 + i
    put(ws4, rr, 2, d['decile'])
    put(ws4, rr, 3, d['n'], '#,##0', INPUT_FONT)
    put(ws4, rr, 4, d['avg_pd'], '0.0%', INPUT_FONT)
    put(ws4, rr, 5, d['actual_default_rate'], '0.0%', INPUT_FONT)
    put(ws4, rr, 6, f'=D{rr}-E{rr}', '0.0%')
    put(ws4, rr, 7, f'=E{rr}/$E$17', '0.00"x"')
put(ws4, 17, 2, 'Portfolio', None, LABEL_FONT)
put(ws4, 17, 3, f'=SUM(C{r + 1}:C{r + 10})', '#,##0', LABEL_FONT)
put(ws4, 17, 4, scoring['avg_predicted_pd'], '0.0%', INPUT_FONT)
put(ws4, 17, 5, scoring['actual_default_rate'], '0.0%', INPUT_FONT)

chart4 = LineChart()
chart4.title = 'Predicted PD vs Actual Default Rate, by Risk Decile'
chart4.y_axis.title = 'Rate'
chart4.x_axis.title = 'Decile'
chart4.add_data(Reference(ws4, min_col=4, min_row=r, max_row=r + 10), titles_from_data=True)
chart4.add_data(Reference(ws4, min_col=5, min_row=r, max_row=r + 10), titles_from_data=True)
chart4.set_categories(Reference(ws4, min_col=2, min_row=r + 1, max_row=r + 10))
chart4.width, chart4.height = 18, 10
ws4.add_chart(chart4, 'B20')

ws4['J5'] = 'Top feature importances (permutation, AUC-based)'
ws4['J5'].font = LABEL_FONT
ws4.cell(row=6, column=10, value='Feature')
ws4.cell(row=6, column=11, value='Importance')
style_header_row(ws4, 6, 2, start_col=10)
for i, f in enumerate(model['top_features']):
    rr = 7 + i
    put(ws4, rr, 10, f['feature'])
    put(ws4, rr, 11, f['importance'], '0.0000', INPUT_FONT)
autosize(ws4, [3, 24, 12, 18, 18, 12, 16, 3, 3, 26, 14])

# ===================== SHEET 5: RECOVERY / LGD =====================
ws5 = wb.create_sheet('Recovery_LGD')
ws5['B2'] = 'Recovery and Loss Given Default'
ws5['B2'].font = TITLE_FONT
ws5['B3'] = ('Of the principal outstanding when a loan charges off, how much comes back '
             'through collections. This is where the 90% LGD used throughout comes from.')
ws5['B3'].font = SUBTITLE_FONT
headers5 = ['Grade', 'Defaults', 'Recovery Rate', 'Implied LGD']
r = 5
for i, h in enumerate(headers5):
    ws5.cell(row=r, column=2 + i, value=h)
style_header_row(ws5, r, len(headers5))
for i, g in enumerate(portfolio['recovery_by_grade']):
    rr = r + 1 + i
    put(ws5, rr, 2, g['grade'])
    put(ws5, rr, 3, g['n_defaults'], '#,##0', INPUT_FONT)
    put(ws5, rr, 4, g['recovery_rate'], '0.0%', INPUT_FONT)
    put(ws5, rr, 5, f'=1-D{rr}', '0.0%')
avg_row = r + 8
put(ws5, avg_row, 2, 'Weighted average', None, LABEL_FONT)
put(ws5, avg_row, 4, f'=SUMPRODUCT(C{r + 1}:C{r + 7},D{r + 1}:D{r + 7})/SUM(C{r + 1}:C{r + 7})',
    '0.0%', LABEL_FONT)
put(ws5, avg_row, 5, f'=1-D{avg_row}', '0.0%', LABEL_FONT)
ws5.cell(row=avg_row, column=5).comment = Comment(
    'Recovery barely moves across grades — a grade G default returns about as little as a '
    'grade A default. That flatness is why a single portfolio-wide LGD is defensible here.',
    'Model v2')

chart5 = BarChart()
chart5.title = 'Recovery Rate by Grade'
chart5.y_axis.title = 'Recovery rate'
chart5.x_axis.title = 'Grade'
chart5.add_data(Reference(ws5, min_col=4, min_row=r, max_row=r + 7), titles_from_data=True)
chart5.set_categories(Reference(ws5, min_col=2, min_row=r + 1, max_row=r + 7))
chart5.width, chart5.height = 16, 9
ws5.add_chart(chart5, 'H5')
autosize(ws5, [3, 18, 14, 16, 14])

# ===================== SHEET 6: METHODOLOGY =====================
ws6 = wb.create_sheet('Methodology')
ws6['B2'] = 'Methodology & Assumptions'
ws6['B2'].font = TITLE_FONT
lines = [
    ('Data source',
     f"LendingClub accepted and rejected loan applications, 2007–2018. The SQL warehouse holds "
     f"{D['warehouse']['raw_accepted_rows']:,} funded loans and "
     f"{D['warehouse']['raw_rejected_rows']:,} declined applications. Of the funded loans, "
     f"{portfolio['n_resolved_loans']:,} have reached a final outcome and are used here."),
    ('Target definition',
     'default = 1 for Charged Off or Default, 0 for Fully Paid. Loans still Current, Late or '
     'In Grace Period are excluded entirely — their outcome is not yet known, and including '
     f"them would bias the default rate downward. Overall rate: {portfolio['overall_default_rate']:.2%}."),
    ('Validation design',
     f"Out-of-time. Trained on {model['n_train']:,} loans issued up to 2016; tested on "
     f"{model['n_test']:,} loans issued 2017–2018. A random split would let loans from the "
     'same vintage sit on both sides and share the same economic conditions, which flatters '
     'the result. This is the standard used in real credit risk model validation.'),
    ('Leakage control',
     'Fields only knowable after a loan resolves are excluded: received principal and interest, '
     'recoveries, outstanding balance, last payment date and amount, updated FICO, hardship and '
     'debt-settlement flags. Only information available at origination is used as a feature.'),
    ('Missingness audit',
     f"{model['n_dropped_for_missingness']} candidate features were dropped for being more than "
     '50% empty in the training window. LendingClub added several bureau fields partway through '
     'the data history, so keeping them would let the model learn "is this field populated" as '
     'a proxy for how recent a loan is — a subtler form of the same temporal leakage.'),
    ('Model',
     f"{model['name']} (scikit-learn), {model['n_features']} features after one-hot encoding, "
     f"selected over a logistic regression baseline (AUC {model['hgb_auc']:.3f} vs "
     f"{model['logreg_auc']:.3f})."),
    ('Risk bands',
     'Low (PD<6%), Low-Medium (6–12%), Medium (12–20%), Medium-High (20–30%), High (30–45%), '
     'Very High (PD>=45%). Thresholds set judgmentally to track observed grade default rates.'),
    ('Expected loss',
     f"PD × funded amount × {scoring['lgd_assumption']:.0%} LGD. The LGD is measured from actual "
     'recovery data on charged-off loans rather than assumed; see the Recovery_LGD tab. The v1 '
     'version of this workbook used a flat 100% placeholder because recovery data had not yet '
     'been analysed.'),
    ('Reject inference',
     f"An acceptance model on the fields shared by funded and declined applications scores AUC "
     f"{rj['headline_auc']:.3f}, rising to {rj['with_score_auc']:.3f} once a credit score proxy "
     f"is added. Employment length was excluded: it reads '< 1 year' for "
     f"{rj['emp_length_under_1yr_rejected']:.0%} of declined applications against "
     f"{rj['emp_length_under_1yr_accepted']:.0%} of funded ones, which is a form default rather "
     f"than a real signal, and including it inflates AUC to {rj['emp_length_inflated_auc']:.3f}."),
    ('Known limitations',
     'LGD is measured at charge-off and does not discount later recoveries or account for the '
     'time value of money. The model contains no macroeconomic variables, so it describes '
     'default patterns without explaining the credit cycle behind them. The credit score proxy '
     'used in the acceptance model compares two similar but not identically defined measures.'),
]
r = 4
for label, text in lines:
    lc = ws6.cell(row=r, column=2, value=label)
    lc.font = LABEL_FONT
    lc.alignment = Alignment(vertical='top')
    c = ws6.cell(row=r, column=3, value=text)
    c.font = NORMAL_FONT
    c.alignment = Alignment(wrap_text=True, vertical='top')
    ws6.row_dimensions[r].height = 58
    r += 2
autosize(ws6, [3, 22, 110])
ws6.column_dimensions['C'].width = 110

for sheet in wb:
    sheet.sheet_view.showGridLines = False
    # Landscape and fit-to-width, so a sheet prints or exports to PDF as one
    # page across instead of spilling its right-hand columns onto a second page.
    sheet.page_setup.orientation = 'landscape'
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True

wb.save(HERE / 'credit_risk_analysis.xlsx')
print(f"Wrote {HERE / 'credit_risk_analysis.xlsx'}")
print('Now run the xlsx recalc script over it so formula values and chart caches populate.')
