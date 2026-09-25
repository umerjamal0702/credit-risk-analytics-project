import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
from openpyxl.comments import Comment
from openpyxl.worksheet.pagebreak import Break


from pathlib import Path

# Resolve paths relative to the repository root so the script runs anywhere
# after cloning. Raw source data is expected in Dataset/ (see Dataset/README.md).
REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / 'Dataset'
HERE = Path(__file__).resolve().parent


FONT = 'Arial'
NAVY = '1F4E78'
LIGHT = 'DCE6F1'
GRAY = '666666'
BLUE_INPUT = '0000FF'
GOLD_FILL = PatternFill('solid', fgColor='FFF2CC')
HEADER_FILL = PatternFill('solid', fgColor=NAVY)
OBJ_FILL = PatternFill('solid', fgColor=LIGHT)
HEADER_FONT = Font(name=FONT, size=11, bold=True, color='FFFFFF')
TITLE_FONT = Font(name=FONT, size=16, bold=True, color=NAVY)
OBJ_FONT = Font(name=FONT, size=11, italic=True, color='1F1F1F')
OBJ_LABEL_FONT = Font(name=FONT, size=10, bold=True, color=NAVY)
NORMAL_FONT = Font(name=FONT, size=11)
INPUT_FONT = Font(name=FONT, size=11, color=BLUE_INPUT)
NOTE_FONT = Font(name=FONT, size=9, italic=True, color=GRAY)
thin = Side(style='thin', color='CCCCCC')
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)

SOURCE_NOTE = ('Source: pivot analysis of credit_risk_master_final, a 250,000-loan sample '
               '(see credit_risk_pivot_tables.xlsx, tab "credit_risk_master_final", for the underlying raw data). '
               'Blue values are inputs pulled from that pivot; black values are formulas.')

with open(HERE / 'pivot_raw_dump.json') as f:
    raw = json.load(f)

def style_header_row(ws, row, ncols, start_col=1):
    for c in range(start_col, start_col+ncols):
        cell = ws.cell(row=row, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = BORDER

def autosize(ws, widths):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

def add_objective(ws, objective_text, row=1):
    ws.cell(row=row, column=1, value='OBJECTIVE').font = OBJ_LABEL_FONT
    c = ws.cell(row=row, column=2, value=objective_text)
    c.font = OBJ_FONT
    c.alignment = Alignment(wrap_text=True, vertical='center')
    ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=8)
    ws.row_dimensions[row].height = 42
    for col in range(1, 9):
        ws.cell(row=row, column=col).fill = OBJ_FILL

def add_source_note(ws, row, span=6):
    c = ws.cell(row=row, column=1, value=SOURCE_NOTE)
    c.font = NOTE_FONT
    c.alignment = Alignment(wrap_text=True)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=span)
    ws.row_dimensions[row].height = 26

def title(ws, text, row=1, col=1, span=6):
    c = ws.cell(row=row, column=col, value=text)
    c.font = TITLE_FONT
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col+span-1)

def input_cell(ws, row, col, value, fmt=None):
    c = ws.cell(row=row, column=col, value=value)
    c.font = INPUT_FONT
    if fmt: c.number_format = fmt
    c.border = BORDER
    return c

def formula_cell(ws, row, col, formula, fmt=None):
    c = ws.cell(row=row, column=col, value=formula)
    c.font = NORMAL_FONT
    if fmt: c.number_format = fmt
    c.border = BORDER
    return c

def label_cell(ws, row, col, value):
    c = ws.cell(row=row, column=col, value=value)
    c.font = NORMAL_FONT
    c.border = BORDER
    return c

def bar_chart(ws, title_text, data_ref, cats_ref, anchor, y_title='', x_title='', width=15, height=9):
    ch = BarChart()
    ch.title = title_text
    ch.y_axis.title = y_title
    ch.x_axis.title = x_title
    ch.add_data(data_ref, titles_from_data=True)
    ch.set_categories(cats_ref)
    ch.width = width
    ch.height = height
    ch.legend = None
    ws.add_chart(ch, anchor)
    return ch

wb = Workbook()
wb.remove(wb.active)

STATUS_ORDER = ['Charged Off', 'Current', 'Fully Paid']

# ============================================================
# 00_Index
# ============================================================
idx = wb.create_sheet('00_Index')
title(idx, 'Credit Risk Pivot Analysis — Index', span=5)
idx['A2'] = 'Redesigned ' + __import__('datetime').date.today().isoformat() + '. Each tab below states the business question it answers, then a single clean summary table and chart.'
idx['A2'].font = Font(name=FONT, size=10, italic=True, color=GRAY)
idx.merge_cells('A2:E2')
idx.row_dimensions[2].height = 28

sheet_objectives = [
    ('01_Portfolio_Overview', 'Understand the overall composition of the lending portfolio by analysing loan volumes, funding distribution, and loan status before performing detailed risk analysis.'),
    ('02_Default_Rate_Grade', 'Identify which loan grades carry the highest default risk, so risk-based pricing and provisioning can be calibrated by grade.'),
    ('03_Default_Rate_Purpose', 'Determine which loan purposes carry elevated default risk, to inform underwriting guidelines and purpose-based risk pricing.'),
    ('04_Default_Rate_Home_Ownership', "Assess whether a borrower's home-ownership status is associated with default risk, as a potential underwriting signal."),
    ('05_Default_Rate_Verification', 'Test whether income verification at origination is associated with lower default rates, to evaluate the value of the verification process.'),
    ('06_Exposure_by_Grade', 'Quantify how much capital is concentrated in each risk grade, to understand portfolio-level risk concentration.'),
    ('07_Exposure_by_Purpose', 'Quantify capital exposure by loan purpose, to identify which purposes represent the largest share of the book.'),
    ('08_Exposure_by_State', 'Quantify geographic concentration of exposure, to identify states that represent outsized portfolio risk.'),
    ('09_Recovery_Analysis', 'Measure how much is recovered on charged-off loans by grade, to calibrate loss-given-default (LGD) assumptions.'),
    ('10_Financial_Model', 'Estimate expected credit loss and loss ratio by grade, combining default rate, exposure, and recovery data into a single provisioning view.'),
]
r = 4
idx.cell(row=r, column=1, value='Tab').font = HEADER_FONT
idx.cell(row=r, column=2, value='Objective').font = HEADER_FONT
for c in (1, 2):
    idx.cell(row=r, column=c).fill = HEADER_FILL
    idx.cell(row=r, column=c).alignment = Alignment(horizontal='center')
for i, (name, obj) in enumerate(sheet_objectives):
    rr = r + 1 + i
    idx.cell(row=rr, column=1, value=name).font = Font(name=FONT, size=11, bold=True, color=NAVY)
    c2 = idx.cell(row=rr, column=2, value=obj)
    c2.font = NORMAL_FONT
    c2.alignment = Alignment(wrap_text=True, vertical='top')
    idx.row_dimensions[rr].height = 32
    idx.cell(row=rr, column=1).border = BORDER
    idx.cell(row=rr, column=2).border = BORDER
idx.cell(row=r+len(sheet_objectives)+2, column=1,
         value='Full 250,000-row raw loan data (127 columns) lives in credit_risk_pivot_tables.xlsx, '
               'tab "credit_risk_master_final" — not duplicated here to keep this workbook light.').font = NOTE_FONT
idx.merge_cells(start_row=r+len(sheet_objectives)+2, start_column=1, end_row=r+len(sheet_objectives)+2, end_column=5)
idx.row_dimensions[r+len(sheet_objectives)+2].height = 26
autosize(idx, [30, 95])

print("00_Index built")

# ============================================================
# 01_Portfolio_Overview
# ============================================================
ws = wb.create_sheet('01_Portfolio_Overview')
add_objective(ws, 'Understand the overall composition of the lending portfolio by analysing loan volumes, '
                   'funding distribution, and loan status before performing detailed risk analysis.')
title(ws, 'Portfolio Overview', row=3, span=5)
r0 = raw['01_Portfolio_Overview']
status_map = {row[0]: (row[1], row[2]) for row in r0[3:7] if row[0] in STATUS_ORDER}  # count, exposure$

r = 5
headers = ['Loan Status', 'Loan Count', '% of Portfolio', 'Exposure ($M)', '% of Exposure']
for i, h in enumerate(headers):
    ws.cell(row=r, column=1+i, value=h)
style_header_row(ws, r, len(headers))
start = r+1
for i, status in enumerate(STATUS_ORDER):
    rr = start+i
    cnt, exp = status_map[status]
    label_cell(ws, rr, 1, status)
    input_cell(ws, rr, 2, cnt, '#,##0')
    formula_cell(ws, rr, 3, f'=B{rr}/B${start+3}', '0.0%')
    input_cell(ws, rr, 4, round(exp/1e6, 4), '$#,##0.0')
    formula_cell(ws, rr, 5, f'=D{rr}/D${start+3}', '0.0%')
tot_row = start+3
label_cell(ws, tot_row, 1, 'Total')
formula_cell(ws, tot_row, 2, f'=SUM(B{start}:B{start+2})', '#,##0')
formula_cell(ws, tot_row, 3, f'=SUM(C{start}:C{start+2})', '0.0%')
formula_cell(ws, tot_row, 4, f'=SUM(D{start}:D{start+2})', '$#,##0.0')
formula_cell(ws, tot_row, 5, f'=SUM(E{start}:E{start+2})', '0.0%')
for row_ in (tot_row,):
    for c in range(1,6):
        ws.cell(row=row_, column=c).font = Font(name=FONT, size=11, bold=True)

data_ref = Reference(ws, min_col=4, min_row=r, max_row=start+2)
cats_ref = Reference(ws, min_col=1, min_row=start, max_row=start+2)
bar_chart(ws, 'Exposure ($M) by Loan Status', data_ref, cats_ref, 'G5', y_title='Exposure ($M)')
autosize(ws, [16, 13, 15, 15, 15])
ws.column_dimensions['A'].width = 16

print("01 built")

# ============================================================
# Helper: generic breakdown sheet (grade/purpose/home_ownership/verification)
# ============================================================
def build_breakdown_sheet(sheet_name, display_title, objective, raw_rows_key, sort_desc_by_rate=True,
                           chart_title='Default Rate'):
    ws = wb.create_sheet(sheet_name)
    add_objective(ws, objective)
    title(ws, display_title, row=3, span=6)
    rows_raw = raw[raw_rows_key]
    # find the block with 'Row Labels','Charged Off','Current','Fully Paid','Grand Total' as first data table
    items = []
    header_idx = None
    for i, row in enumerate(rows_raw):
        if row[0] == 'Row Labels' and row[1] == 'Charged Off':
            header_idx = i
            break
    i = header_idx + 1
    while i < len(rows_raw) and rows_raw[i][0] not in (None, 'Grand Total'):
        cat, co, cur, fp = rows_raw[i][0], rows_raw[i][1] or 0, rows_raw[i][2] or 0, rows_raw[i][3] or 0
        items.append((cat, co, cur, fp))
        i += 1
    if sort_desc_by_rate:
        items.sort(key=lambda x: -(x[1] / max(x[1]+x[2]+x[3], 1)))

    r = 5
    headers = ['Category', 'Charged Off', 'Current', 'Fully Paid', 'Total Loans', 'Default Rate']
    for j, h in enumerate(headers):
        ws.cell(row=r, column=1+j, value=h)
    style_header_row(ws, r, len(headers))
    start = r + 1
    for k, (cat, co, cur, fp) in enumerate(items):
        rr = start + k
        label_cell(ws, rr, 1, cat)
        input_cell(ws, rr, 2, co, '#,##0')
        input_cell(ws, rr, 3, cur, '#,##0')
        input_cell(ws, rr, 4, fp, '#,##0')
        formula_cell(ws, rr, 5, f'=SUM(B{rr}:D{rr})', '#,##0')
        formula_cell(ws, rr, 6, f'=B{rr}/E{rr}', '0.0%')
    end = start + len(items) - 1
    tot_row = end + 1
    label_cell(ws, tot_row, 1, 'Grand Total')
    for col, letter in [(2,'B'),(3,'C'),(4,'D'),(5,'E')]:
        formula_cell(ws, tot_row, col, f'=SUM({letter}{start}:{letter}{end})', '#,##0')
    formula_cell(ws, tot_row, 6, f'=B{tot_row}/E{tot_row}', '0.0%')
    for c in range(1,7):
        ws.cell(row=tot_row, column=c).font = Font(name=FONT, size=11, bold=True)

    data_ref = Reference(ws, min_col=6, min_row=r, max_row=end)
    cats_ref = Reference(ws, min_col=1, min_row=start, max_row=end)
    bar_chart(ws, chart_title, data_ref, cats_ref, 'H5', y_title='Default rate')
    autosize(ws, [22, 13, 11, 12, 13, 13])
    print(sheet_name, "built,", len(items), "categories")
    return ws

build_breakdown_sheet('02_Default_Rate_Grade', 'Default Rate by Grade',
    'Identify which loan grades carry the highest default risk, so risk-based pricing and provisioning can be calibrated by grade.',
    '02_Default_Rate_grade', sort_desc_by_rate=False, chart_title='Default Rate by Grade')

build_breakdown_sheet('03_Default_Rate_Purpose', 'Default Rate by Purpose',
    'Determine which loan purposes carry elevated default risk, to inform underwriting guidelines and purpose-based risk pricing.',
    '03_default_rate_purpose', sort_desc_by_rate=True, chart_title='Default Rate by Purpose')

build_breakdown_sheet('04_Default_Rate_Home_Ownership', 'Default Rate by Home Ownership',
    "Assess whether a borrower's home-ownership status is associated with default risk, as a potential underwriting signal.",
    '04_Default_Rate_Home_Ownership', sort_desc_by_rate=True, chart_title='Default Rate by Home Ownership')

ws05 = build_breakdown_sheet('05_Default_Rate_Verification', 'Default Rate by Verification Status',
    'Test whether income verification at origination is associated with lower default rates, to evaluate the value of the verification process.',
    '05_Default_Rate_Verification_St', sort_desc_by_rate=True, chart_title='Default Rate by Verification Status')
# Insight callout — verified loans default MORE, not less (counter-intuitive)
insight_row = 12
ws05.cell(row=insight_row, column=1,
    value='Insight: "Verified" loans default at a higher rate than "Not Verified" loans — verification appears to correlate with '
          'riskier applicants seeking verification (e.g. higher loan amounts), not with safer ones. Worth flagging for underwriting review.'
).font = Font(name=FONT, size=10, italic=True, color='9C5700')
ws05.cell(row=insight_row, column=1).fill = PatternFill('solid', fgColor='FFEB9C')
ws05.merge_cells(start_row=insight_row, start_column=1, end_row=insight_row, end_column=6)
ws05.row_dimensions[insight_row].height = 30

print("00-05 built")

# ============================================================
# Helper: exposure-by-category sheet (grade/purpose/state)
# ============================================================
def build_exposure_sheet(sheet_name, display_title, objective, raw_rows_key, top_n_for_chart=None, sort_desc=True):
    ws = wb.create_sheet(sheet_name)
    add_objective(ws, objective)
    title(ws, display_title, row=3, span=4)
    rows_raw = raw[raw_rows_key]
    header_idx = None
    for i, row in enumerate(rows_raw):
        if row[0] == 'Row Labels' and 'funded_amnt' in str(row[1] or ''):
            header_idx = i
            break
    items = []
    i = header_idx + 1
    while i < len(rows_raw) and rows_raw[i][0] not in (None, 'Grand Total'):
        cat, amt = rows_raw[i][0], rows_raw[i][1] or 0
        items.append((cat, amt))
        i += 1
    if sort_desc:
        items.sort(key=lambda x: -x[1])

    r = 5
    headers = ['Category', 'Exposure ($M)', '% of Portfolio']
    for j, h in enumerate(headers):
        ws.cell(row=r, column=1+j, value=h)
    style_header_row(ws, r, len(headers))
    start = r + 1
    for k, (cat, amt) in enumerate(items):
        rr = start + k
        label_cell(ws, rr, 1, cat)
        input_cell(ws, rr, 2, round(amt/1e6, 4), '$#,##0.0')
        formula_cell(ws, rr, 3, f'=B{rr}/B${start+len(items)}', '0.0%')
    end = start + len(items) - 1
    tot_row = end + 1
    label_cell(ws, tot_row, 1, 'Grand Total')
    formula_cell(ws, tot_row, 2, f'=SUM(B{start}:B{end})', '$#,##0.0')
    formula_cell(ws, tot_row, 3, f'=B{tot_row}/B{tot_row}', '0.0%')
    for c in range(1,4):
        ws.cell(row=tot_row, column=c).font = Font(name=FONT, size=11, bold=True)

    chart_end = start + (top_n_for_chart - 1) if top_n_for_chart else end
    data_ref = Reference(ws, min_col=2, min_row=r, max_row=chart_end)
    cats_ref = Reference(ws, min_col=1, min_row=start, max_row=chart_end)
    ct = f'Exposure ($M) — Top {top_n_for_chart}' if top_n_for_chart else 'Exposure ($M)'
    bar_chart(ws, ct, data_ref, cats_ref, 'E5', y_title='Exposure ($M)', height=max(9, 0.35*(chart_end-start+1)))
    autosize(ws, [22, 15, 15])
    print(sheet_name, "built,", len(items), "categories")
    return ws

build_exposure_sheet('06_Exposure_by_Grade', 'Portfolio Exposure by Grade',
    'Quantify how much capital is concentrated in each risk grade, to understand portfolio-level risk concentration.',
    '06_Portfolio_Exposure_Grade', sort_desc=False)

build_exposure_sheet('07_Exposure_by_Purpose', 'Portfolio Exposure by Purpose',
    'Quantify capital exposure by loan purpose, to identify which purposes represent the largest share of the book.',
    '07_Portfolio_Exposure_Purpose')

build_exposure_sheet('08_Exposure_by_State', 'Portfolio Exposure by State',
    'Quantify geographic concentration of exposure, to identify states that represent outsized portfolio risk.',
    '08_Portfolio_Exposure_State', top_n_for_chart=15)

print("06-08 built")

# ============================================================
# 09_Recovery_Analysis
# ============================================================
ws09 = wb.create_sheet('09_Recovery_Analysis')
add_objective(ws09, 'Measure how much is recovered on charged-off loans by grade, to calibrate loss-given-default (LGD) assumptions.')
title(ws09, 'Recovery Analysis by Grade', row=3, span=4)
r09 = raw['09_Recovery_Analysis']
grade_recovery = {}
for row in r09[1:8]:
    g, rec, fee = row[0], row[1] or 0, row[2] or 0
    grade_recovery[g] = (rec, fee)
grades = ['A','B','C','D','E','F','G']

r = 5
headers = ['Grade', 'Recoveries ($M)', 'Collection Fee ($M)', 'Net Recovery ($M)']
for j, h in enumerate(headers):
    ws09.cell(row=r, column=1+j, value=h)
style_header_row(ws09, r, len(headers))
start09 = r + 1
for k, g in enumerate(grades):
    rr = start09 + k
    rec, fee = grade_recovery[g]
    label_cell(ws09, rr, 1, g)
    input_cell(ws09, rr, 2, round(rec/1e6, 4), '$#,##0.00')
    input_cell(ws09, rr, 3, round(fee/1e6, 4), '$#,##0.00')
    formula_cell(ws09, rr, 4, f'=B{rr}-C{rr}', '$#,##0.00')
end09 = start09 + len(grades) - 1
tot09 = end09 + 1
label_cell(ws09, tot09, 1, 'Grand Total')
for col, letter in [(2,'B'),(3,'C'),(4,'D')]:
    formula_cell(ws09, tot09, col, f'=SUM({letter}{start09}:{letter}{end09})', '$#,##0.00')
for c in range(1,5):
    ws09.cell(row=tot09, column=c).font = Font(name=FONT, size=11, bold=True)

data_ref = Reference(ws09, min_col=2, min_row=r, max_row=end09)
cats_ref = Reference(ws09, min_col=1, min_row=start09, max_row=end09)
bar_chart(ws09, 'Recoveries ($M) by Grade', data_ref, cats_ref, 'F5', y_title='Recoveries ($M)')
autosize(ws09, [10, 17, 18, 17])
print("09 built, grade rows:", start09, "-", end09)

# ============================================================
# 10_Financial_Model — fully formula-linked to sheets 02, 06, 09
# ============================================================
ws10 = wb.create_sheet('10_Financial_Model')
add_objective(ws10, 'Estimate expected credit loss and loss ratio by grade, combining default rate, exposure, and recovery data into a single provisioning view.')
title(ws10, 'Financial Model — Expected Credit Loss by Grade', row=3, span=8)

r = 5
headers = ['Grade', 'Default Rate', 'Exposure ($M)', 'Est. Default Exposure ($M)',
           'Recovery ($M)', 'Est. Credit Loss ($M)', 'Recovery Rate', 'Est. Loss Ratio']
for j, h in enumerate(headers):
    ws10.cell(row=r, column=1+j, value=h)
style_header_row(ws10, r, len(headers))
start10 = r + 1
# Robust to row order in source sheets: look up each grade by name (INDEX/MATCH) rather than
# assuming positional alignment, since 07/08 sort by exposure descending (06 does not, but this
# stays correct even if that changes).
end02 = 6 + len(grades) - 1  # sheet 02 data rows 6..12
end06 = 6 + len(grades) - 1  # sheet 06 data rows 6..12
end09 = start09 + len(grades) - 1
for k, g in enumerate(grades):
    rr = start10 + k
    label_cell(ws10, rr, 1, g)
    ws10.cell(row=rr, column=1).font = NORMAL_FONT
    formula_cell(ws10, rr, 2,
        f"=INDEX('02_Default_Rate_Grade'!$F$6:$F${end02},MATCH(A{rr},'02_Default_Rate_Grade'!$A$6:$A${end02},0))", '0.0%')
    formula_cell(ws10, rr, 3,
        f"=INDEX('06_Exposure_by_Grade'!$B$6:$B${end06},MATCH(A{rr},'06_Exposure_by_Grade'!$A$6:$A${end06},0))", '$#,##0.0')
    formula_cell(ws10, rr, 4, f'=B{rr}*C{rr}', '$#,##0.00')
    formula_cell(ws10, rr, 5,
        f"=INDEX('09_Recovery_Analysis'!$B${start09}:$B${end09},MATCH(A{rr},'09_Recovery_Analysis'!$A${start09}:$A${end09},0))", '$#,##0.00')
    formula_cell(ws10, rr, 6, f'=D{rr}-E{rr}', '$#,##0.00')
    formula_cell(ws10, rr, 7, f'=E{rr}/D{rr}', '0.0%')
    formula_cell(ws10, rr, 8, f'=F{rr}/C{rr}', '0.0%')
end10 = start10 + len(grades) - 1
tot10 = end10 + 1
label_cell(ws10, tot10, 1, 'Grand Total')
for col, letter in [(3,'C'),(4,'D'),(5,'E'),(6,'F')]:
    formula_cell(ws10, tot10, col, f'=SUM({letter}{start10}:{letter}{end10})', '$#,##0.0')
formula_cell(ws10, tot10, 2, f'=D{tot10}/C{tot10}', '0.0%')
formula_cell(ws10, tot10, 7, f'=E{tot10}/D{tot10}', '0.0%')
formula_cell(ws10, tot10, 8, f'=F{tot10}/C{tot10}', '0.0%')
for c in range(1,9):
    ws10.cell(row=tot10, column=c).font = Font(name=FONT, size=11, bold=True)

data_ref = Reference(ws10, min_col=8, min_row=r, max_row=end10)
cats_ref = Reference(ws10, min_col=1, min_row=start10, max_row=end10)
bar_chart(ws10, 'Estimated Loss Ratio by Grade', data_ref, cats_ref, 'J5', y_title='Loss ratio')
autosize(ws10, [8, 13, 14, 20, 13, 16, 13, 14])

print("09-10 built")

from openpyxl.worksheet.page import PageMargins

for ws_ in wb.worksheets:
    cur = ws_.column_dimensions['A'].width or 8.43
    if cur < 13:
        ws_.column_dimensions['A'].width = 13

for ws_ in wb.worksheets:
    ws_.page_setup.orientation = 'landscape'
    ws_.page_setup.fitToWidth = 1
    ws_.page_setup.fitToHeight = 0
    ws_.sheet_properties.pageSetUpPr.fitToPage = True
    ws_.page_margins = PageMargins(left=0.4, right=0.4, top=0.5, bottom=0.5, header=0.2, footer=0.2)
    ws_.print_options.horizontalCentered = False
    ws_.freeze_panes = None

wb.active = 0
import os

wb.save(HERE / 'credit_risk_pivot_tables_redesigned.xlsx')

# NOTE: openpyxl writes formulas as strings with no cached values, so charts that
# plot formula-driven columns render blank until the workbook is recalculated once.
# After running this script, open the workbook in Excel/LibreOffice and save it (or
# run a headless LibreOffice recalculation) so the formula values and chart caches
# are populated. The committed copy of this workbook has already been recalculated.
print("Saved final workbook")
