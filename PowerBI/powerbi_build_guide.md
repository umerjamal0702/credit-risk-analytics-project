# Power BI Build Guide — Credit Risk Dashboard

A click-by-click build for a three-page report. Every field name below is real,
and most steps end with the number you should be seeing, so you can catch a
mistake at the step that caused it rather than three steps later.

Work from **`PowerBI/import/`**, not `PowerBI/extracts/`. The import folder is a
cleaned copy: every rate is a fraction (so Power BI's percentage format behaves),
year columns are whole numbers, and the scored-loan table is uncompressed.
Regenerate it any time with `python PowerBI/build_import_layer.py`.

---

## Why three pages

The project answers three different questions for three different readers.

| Page | Question | Reader |
|---|---|---|
| 1. Portfolio Performance | How is the book we already hold performing? | Credit risk monitoring |
| 2. Underwriting Funnel | Who applies, who gets approved, how has that changed? | Underwriting and growth |
| 3. Model and Risk Segmentation | Can we predict default, and what do we expect to lose? | Risk analytics |

---

## Step 1 — Import the data

**Home → Get data → Text/CSV.** Import these thirteen files from `PowerBI/import/`:

```
agg_grade_scorecard.csv          agg_application_volume.csv
agg_vintage_default_trend.csv    agg_acceptance_funnel_by_state_year.csv
agg_state_risk.csv               agg_accept_reject_profile.csv
agg_purpose_grade_risk.csv       agg_model_calibration.csv
agg_recovery_by_grade.csv        agg_risk_band_summary.csv
agg_monthly_trend.csv            fact_scored_loans.csv
dim_date.csv
```

On each dialog click **Load** (not Transform) — the import layer is already clean.
`fact_scored_loans.csv` is 26 MB and takes a few seconds; the rest are instant.

**Check:** the Data pane lists 13 tables. Click `fact_scored_loans` and confirm
225,639 rows at the bottom of the table view.

---

## Step 2 — Set up the model

**Model view.** There is exactly one relationship to create:

- Drag `dim_date[yyyymm]` onto `fact_scored_loans[issue_yyyymm]`.
- Cardinality **one to many**, direction **single**, `dim_date` on the one side.

Then select `dim_date` in the Data pane → **Table tools → Mark as date table** →
choose the `date` column.

**Leave every other table unrelated.** They are pre-aggregated summaries at
different grains, and joining them would create ambiguous filter paths that
silently produce wrong totals. Each page uses its own tables, which is a design
decision worth being able to explain.

### A measures table

**Home → Enter data**, leave the blank table empty, name it `_Measures`, Load.
Every measure below goes in this table. Once a measure is in there, delete the
placeholder `Column1`.

This is a standard modelling convention: measures live in one place rather than
scattered across data tables, and the underscore sorts it to the top of the pane.

---

## Step 3 — Create the measures

Select `_Measures`, then **Table tools → New measure** for each. Set the format
for each one on the **Measure tools** ribbon as noted.

### Portfolio (page 1)

```
Total Loans = SUM('agg_grade_scorecard'[n_loans])
Total Funded = SUM('agg_grade_scorecard'[total_funded])
Total Defaults = SUM('agg_grade_scorecard'[n_default])
Portfolio Default Rate = DIVIDE([Total Defaults], [Total Loans])
Total Net Loss = SUM('agg_grade_scorecard'[total_net_loss])
Loss Rate = DIVIDE([Total Net Loss], [Total Funded])
Recovery Rate =
    DIVIDE(
        SUM('agg_recovery_by_grade'[total_recoveries]),
        SUM('agg_recovery_by_grade'[gross_unpaid_balance])
    )
Implied LGD = 1 - [Recovery Rate]
```

Format: `Total Loans` and `Total Defaults` as Whole number with thousands
separator; `Total Funded` and `Total Net Loss` as Currency with 0 decimals; the
four rates as Percentage with 1 decimal.

**Check** — drop each into a card:

| Measure | Expected |
|---|---|
| Total Loans | 1,348,099 |
| Total Funded | $19.41bn |
| Portfolio Default Rate | 20.0% |
| Total Net Loss | $2.68bn |
| Loss Rate | 13.8% |
| Recovery Rate | 10.8% |
| Implied LGD | 89.2% |

If Portfolio Default Rate shows 1,998% you have imported from `extracts/`
rather than `import/`.

### Funnel (page 2)

```
Total Applications = SUM('agg_application_volume'[total_applications])
Accepted Applications = SUM('agg_application_volume'[accepted])
Rejected Applications = SUM('agg_application_volume'[rejected])
Acceptance Rate = DIVIDE([Accepted Applications], [Total Applications])
```

Format: first three Whole number, `Acceptance Rate` Percentage with 1 decimal.

**Check:** 29,903,532 applications · 2,260,065 accepted · 7.6% acceptance rate.

### Model (page 3)

```
Loans Scored = COUNTROWS('fact_scored_loans')
Exposure Scored = SUM('fact_scored_loans'[funded_amnt])
Avg Predicted PD = AVERAGE('fact_scored_loans'[predicted_pd])
Actual Default Rate = DIVIDE(SUM('fact_scored_loans'[actual_default]), [Loans Scored])
Calibration Gap = [Avg Predicted PD] - [Actual Default Rate]
Expected Loss = SUM('fact_scored_loans'[expected_loss])
Actual Loss = SUM('fact_scored_loans'[actual_loss_proxy])
Loss Variance = DIVIDE([Expected Loss], [Actual Loss]) - 1
```

Format: `Loans Scored` Whole number; `Exposure Scored`, `Expected Loss`,
`Actual Loss` Currency with 0 decimals; the rest Percentage with 1 decimal.

**Check:** 225,639 scored · $3.26bn exposure · 20.4% predicted · 21.3% actual ·
−0.9% gap · $662.6M expected · $693.2M actual · −4.4% variance.

That last pair is the most interesting number on the report: the model
under-predicts real losses by 4.4%.

---

## Step 4 — Page 1: Portfolio Performance

Rename the page tab to **Portfolio Performance**.

**Card row** (five cards across the top): Total Loans · Total Funded ·
Portfolio Default Rate · Loss Rate · Implied LGD.

For each: insert a **Card**, drag the measure into Fields, then under
**Format → Callout value** set the text size to about 28, and under
**Format → Category label** turn the label on so the card says what it is.

**Visual 1 — Default rate by vintage** *(Line chart)*
- X axis: `agg_vintage_default_trend[issue_year]`
- Y axis: `default_rate`, then `default_rate_3yr_avg`
- Format → X axis → Type: **Categorical** (otherwise 2007–2018 renders with
  decimal gridlines like 2,010.5)
- Title: *Default rate by vintage year*

The shape to expect: high in 2007–2008, falling through 2013, rising again to
2016. That is the credit cycle.

**Visual 2 — Risk grading** *(Clustered column chart)*
- X axis: `agg_grade_scorecard[grade]`
- Y axis: `default_rate`, then add the `[Loss Rate]` measure as a second series
- Title: *Default and loss rate by grade*

Don't put `total_net_loss` on here as well — dollars and rates have no shared
scale. `[Loss Rate]` works without any new measure because filter context does
the work: the same measure that reads 13.8% on the card recalculates per grade
once `grade` is on the axis. Being able to explain that is most of what DAX
fluency means in an interview.

Both series should climb from A to G without a single reversal: 6.0% to 49.7%
default, 3.2% to 37.7% loss.

**Visual 3 — Recovery** *(Clustered column chart)*
- X axis: `agg_recovery_by_grade[grade]`, Y axis: `recovery_rate`
- Format → Y axis → set **Maximum** to 0.2 so the variation is visible
- Title: *Recovery rate by grade*

The point of this chart is how **flat** it is — 10.0% to 11.6% regardless of
grade. A grade G default returns about as little as a grade A default, which is
why a single portfolio-wide LGD is defensible.

**Visual 4 — Geographic exposure** *(Clustered bar chart)*
- Y axis: `agg_state_risk[state]`, X axis: `total_exposure`
- Filter: **Top N** → Top 10 by `total_exposure`
- Add `default_rate` to the Tooltips well
- Title: *Exposure by state (top 10)*

Use a bar chart rather than a map. Power BI maps need the column's data category
set to State or Province plus a country context, and they often fail silently on
two-letter codes — not worth the risk for a portfolio piece. California, Texas
and New York lead on exposure, but hover New York and you will see it defaults
at 22.1% against California's 19.6%, which is the insight worth captioning.

**Visual 5 — Purpose within grade** *(Matrix)*
- Rows: `agg_purpose_grade_risk[grade]`, Columns: `purpose`, Values: `default_rate`
- Format → Cell elements → Background colour → On, applied to `default_rate`
- Title: *Default rate by purpose within grade*

This shows which purposes are risky **after** controlling for the grade the
lender already assigned. Small business is the standout.

---

## Step 5 — Page 2: Underwriting Funnel

New page, renamed **Underwriting Funnel**.

**Card row:** Total Applications · Accepted Applications · Acceptance Rate.

**Visual 1 — Application volume** *(Clustered column chart)*
- X axis: `agg_application_volume[app_year]` (X axis type: Categorical)
- Y axis: `total_applications`
- Title: *Applications received by year*

**Visual 2 — Acceptance rate** *(Line chart, placed directly beneath visual 1)*
- X axis: `agg_application_volume[app_year]` (Categorical)
- Y axis: `acceptance_rate`
- Title: *Acceptance rate by year*

Power BI offers a "Line and clustered column chart" that would put both of these
on one canvas with two Y axes. Don't use it. A dual-axis chart lets you imply any
relationship you like by sliding one scale against the other, and the two axes
here (millions of applications, a percentage) have no common basis. Two stacked
charts sharing an X axis tell the same story without the distortion — and being
able to say that in an interview is worth more than the chart.

The story across the two: applications grew from 896K in 2013 to 9.99M in 2018
while the acceptance rate fell from 15.1% to 5.0%. Volume went up, standards
went up faster.

**Visual 3 — Acceptance by state** *(Clustered bar chart)*
- Y axis: `agg_acceptance_funnel_by_state_year[state]`, X axis: `acceptance_rate`
- Filter: Top N → Top 15 by `acceptance_rate`
- Add a **slicer** for `app_year` from the same table, set to single-select, 2018
- Title: *Acceptance rate by state*

**Visual 4 — Who gets approved** *(Clustered column chart)*
- X axis: `agg_accept_reject_profile[app_year]` (Categorical)
- Y axis: `avg_dti`
- Legend: `outcome`
- Title: *Average debt-to-income: accepted vs rejected*

Rejected applicants carry visibly higher debt-to-income in every single year.
That is the clearest honest driver of the approval decision in the data.

**Text box** — add one noting the acceptance model result: AUC 0.672 on amount,
DTI, year and state; 0.855 once a credit score proxy is added. Mention the
employment-length defect too (83% of rejections read "< 1 year" against 8% of
approvals), because that is the finding people remember.

---

## Step 6 — Page 3: Model and Risk Segmentation

New page, renamed **Model and Risk**.

**Card row:** Loans Scored · Exposure Scored · Avg Predicted PD ·
Actual Default Rate · Expected Loss · Actual Loss.

**Visual 1 — Calibration** *(Line chart)*
- X axis: `agg_model_calibration[decile]` (Categorical)
- Y axis: `avg_predicted_pd`, then `actual_default_rate`
- Title: *Predicted vs actual default rate by risk decile*

The two lines should sit almost on top of each other across all ten deciles.
That is calibration, and it is a more demanding property than a good AUC: it
means the probabilities are honest, not just correctly ordered. This is the
single best visual on the report.

**Visual 2 — Risk bands** *(Clustered column chart)*
- X axis: `agg_risk_band_summary[risk_band]`
- Y axis: `avg_predicted_pd`, then `actual_default_rate`
- Title: *Predicted vs actual by risk band*

The band labels sort correctly on their own because they are prefixed 1 to 6.

**Visual 3 — Expected vs actual loss** *(Clustered column chart)*
- X axis: `agg_risk_band_summary[risk_band]`
- Y axis: `expected_loss`, then `actual_loss_proxy`
- Title: *Expected vs actual loss by risk band*

Actual exceeds expected in the lower bands and the gap closes higher up — the
visual form of that −4.4% variance.

**Visual 4 — Watchlist** *(Table)*
- Columns in order: `loan_id`, `sub_grade`, `funded_amnt`, `purpose`, `state`,
  `predicted_pd`, `risk_band`, `actual_default`
- Sort by `predicted_pd` descending
- Filter: **Top N** → Top 20 by `predicted_pd`
- Set `funded_amnt` to Currency 0dp and `predicted_pd` to Percentage 1dp in the
  Column tools ribbon
- Title: *Highest-risk loans — predicted vs what happened*

15 of these 20 defaulted. The `actual_default` column is what makes this a test
of the model rather than a restatement of it.

**Text box:** *"Every loan on this page is from the out-of-time test set — issued
2017–2018, after the model's training window. The model never saw any of them."*
Say it on the page. A model scoring loans it trained on would look far better and
mean far less.

---

## Step 7 — Tidy up

- **View → Themes**, pick one and keep it across all three pages.
- Give every visual a real title describing the finding, not the fields
  ("Default rate climbs monotonically A to G" beats "default_rate by grade").
- **View → Gridlines + Snap to grid** on, then align the card rows.
- Turn off the "Filters" pane for the reader: **View → Filters** collapsed.
- Save as `credit_risk_dashboard.pbix`.

## Step 8 — Capture for the repository

Screenshot each page and save into `PowerBI/` as:

```
page1_portfolio_performance.png
page2_underwriting_funnel.png
page3_model_segmentation.png
```

Then add each image to the README under the matching workflow section, the same
way the Excel and dashboard screenshots already appear. Commit the `.pbix` too —
it is about 30 MB, well within GitHub's limits.

---

## If something looks wrong

| Symptom | Cause |
|---|---|
| A rate reads 604% or 1,998% | Imported from `extracts/` instead of `import/` |
| Years show as 2,010.50 | X axis type is Continuous; set it to Categorical |
| A card shows a blank or a date | The measure landed in a data table rather than `_Measures`, or the wrong column was dragged |
| Totals change when a slicer moves on another visual | You created a relationship between two aggregate tables — delete it |
| The matrix shows 1 in every cell | `default_rate` is being summarised as Count; set it to Average or Sum on the field well |
