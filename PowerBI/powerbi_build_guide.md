# Power BI Build Guide — Credit Risk Dashboards

This is a data extract plus a build guide. The dashboard itself has to be assembled
in Power BI Desktop on your machine, so this document specifies exactly what to build:
the data model, the measures, and the visuals on each page.

Everything here was generated from and validated against the SQL warehouse
(2.26M accepted loans, 27.6M declined applications, 2007–2018).

---

## How many dashboards

**One .pbix file with three pages.**

The project answers three different questions for three different audiences, and each
one deserves its own page. They do not belong on one crowded canvas, and splitting
them further would pad the report rather than strengthen it.

| Page | Question it answers | Audience |
|----------|----------|----------|
| 1. Portfolio Performance | How is the loan book we already hold performing? | Credit risk monitoring |
| 2. Underwriting Funnel | Who applies, who gets approved, and how has that changed? | Underwriting and growth |
| 3. Model and Risk Segmentation | Can we predict default, and how much do we expect to lose? | Risk analytics and model validation |

An earlier draft of this guide proposed six pages. That was too many. Vintage trends,
grade performance, recovery rates and state exposure are all the same question
(portfolio performance) sliced four ways, so they belong together on page 1 as
separate visuals rather than as four thin pages.

---

## Data files

### Fact tables

| File | Grain | Rows | Used on |
|----------|----------|----------|----------|
| fact_loan_performance_part{1,2,3}of3.csv | One resolved loan | 1,348,099 | Page 1 |
| fact_scored_loans.csv | One scored loan from the out-of-time test set | 225,639 | Page 3 |

### Dimension table

| File | Grain | Rows |
|----------|----------|----------|
| dim_date.csv | One month, 2007-01 to 2018-12 | 144 |

### Pre-aggregated tables

| File | Grain | Rows | Used on |
|----------|----------|----------|----------|
| agg_vintage_default_trend.csv | Issue year | 12 | Page 1 |
| agg_grade_scorecard.csv | Grade | 7 | Page 1 |
| agg_recovery_by_grade.csv | Grade | 7 | Page 1 |
| agg_state_risk.csv | State | 50 | Page 1 |
| agg_monthly_trend.csv | Issue month | 139 | Page 1 |
| agg_purpose_grade_risk.csv | Grade x purpose | 68 | Page 1 |
| agg_application_volume.csv | Application year | 11 | Page 2 |
| agg_acceptance_funnel_by_state_year.csv | State x year | 490 | Page 2 |
| agg_accept_reject_profile.csv | Year x outcome | 22 | Page 2 |
| agg_model_calibration.csv | Risk decile | 10 | Page 3 |
| agg_risk_band_summary.csv | Risk band | 6 | Page 3 |

The aggregate tables let you build a working dashboard quickly, but the measures in
the next section are the part worth showing an interviewer. Build those on the fact
tables rather than relying only on pre-computed columns.

---

## Import and model

1. **Get Data → Text/CSV** for each file. The three `fact_loan_performance` parts are
   split only for file-size limits: import all three and use **Append Queries** to
   combine them into a single table named `fact_loan_performance`.
2. Check data types. `issue_yyyymm` and `dim_date[yyyymm]` must both be **Text** (they
   are the join key, formatted "YYYY-MM"). `dim_date[date]` must be **Date**.
3. Create relationships, both one-to-many from the date table:
   - `dim_date[yyyymm]` → `fact_loan_performance[issue_yyyymm]`
   - `dim_date[yyyymm]` → `fact_scored_loans[issue_yyyymm]`
4. Right-click `dim_date` → **Mark as date table**, using the `date` column. This
   enables time intelligence functions.
5. Leave the `agg_` tables unrelated to the rest of the model. They are standalone
   summary tables, and connecting them would create ambiguous filter paths.

---

## Measures

### Portfolio measures (on `fact_loan_performance`)

```
Total Loans = COUNTROWS(fact_loan_performance)

Total Funded = SUM(fact_loan_performance[funded_amnt])

Total Defaults = SUM(fact_loan_performance[default_flag])

Default Rate = DIVIDE([Total Defaults], [Total Loans])

Total Net Loss = SUM(fact_loan_performance[net_loss])

Loss Rate = DIVIDE([Total Net Loss], [Total Funded])

Weighted Avg Interest Rate =
    DIVIDE(
        SUMX(fact_loan_performance,
             fact_loan_performance[int_rate] * fact_loan_performance[funded_amnt]),
        [Total Funded]
    )

Avg FICO =
    AVERAGEX(
        fact_loan_performance,
        (fact_loan_performance[fico_range_low] + fact_loan_performance[fico_range_high]) / 2
    )

Recovery Rate =
    DIVIDE(
        CALCULATE(SUM(fact_loan_performance[recoveries]),
                  fact_loan_performance[default_flag] = 1),
        CALCULATE(SUM(fact_loan_performance[funded_amnt])
                  - SUM(fact_loan_performance[total_rec_prncp]),
                  fact_loan_performance[default_flag] = 1)
    )

Implied LGD = 1 - [Recovery Rate]

Default Rate YoY =
    VAR CurrentRate = [Default Rate]
    VAR PriorRate = CALCULATE([Default Rate], SAMEPERIODLASTYEAR(dim_date[date]))
    RETURN CurrentRate - PriorRate
```

### Model measures (on `fact_scored_loans`)

```
Loans Scored = COUNTROWS(fact_scored_loans)

Avg Predicted PD = AVERAGE(fact_scored_loans[predicted_pd])

Actual Default Rate = DIVIDE(SUM(fact_scored_loans[actual_default]), [Loans Scored])

Calibration Gap = [Avg Predicted PD] - [Actual Default Rate]

Expected Loss = SUM(fact_scored_loans[expected_loss])

Actual Loss = SUM(fact_scored_loans[actual_loss_proxy])

Exposure Scored = SUM(fact_scored_loans[funded_amnt])
```

`expected_loss` is already calculated in the extract as
`predicted_pd × funded_amnt × 0.90`, using the 90% loss given default measured from
actual recovery data rather than an assumption.

---

## Page 1 — Portfolio Performance

**KPI cards:** Total Loans · Total Funded · Default Rate · Loss Rate · Weighted Avg
Interest Rate

**Visuals:**

- **Line chart** — default rate by issue year, with the three-year moving average as a
  second series. Source: `agg_vintage_default_trend`. This is the credit cycle story:
  elevated in 2008–2009, falling through 2010–2013, rising again from 2014.
- **Column chart** — default rate by grade (A to G, in that order, not sorted by
  value). Should climb monotonically from 6.0% to 49.7%. Add loss rate as a second
  series to show that losses rise faster than default counts.
- **Filled map** — total exposure by state, with default rate on the tooltip. Source:
  `agg_state_risk`.
- **Matrix** — grade (rows) by purpose (columns), default rate as values, conditional
  formatting on a colour scale. Source: `agg_purpose_grade_risk`.
- **Bar chart** — recovery rate and implied LGD by grade. Source:
  `agg_recovery_by_grade`. The flatness is the point: recoveries return only 10% to
  11.6% regardless of borrower quality.

**Slicers:** issue year, grade, purpose

---

## Page 2 — Underwriting Funnel

**KPI cards:** Total Applications · Accepted · Acceptance Rate · Rejected

**Visuals:**

- **Combo chart** — application volume as columns and acceptance rate as a line, by
  year. Source: `agg_application_volume`. This is the strongest single chart in the
  project: applications grew from 896K in 2013 to 9.99M in 2018 while the acceptance
  rate fell from 15.1% to 5.0%.
- **Filled map** — acceptance rate by state, with a year slicer. Source:
  `agg_acceptance_funnel_by_state_year`.
- **Clustered column chart** — average DTI for accepted versus rejected applicants by
  year. Source: `agg_accept_reject_profile`. Rejected applicants consistently carry
  higher debt-to-income, which is the clearest legitimate driver of the decision.
- **Text box** — note the acceptance model result (AUC 0.672 on amount, DTI, year and
  state; 0.855 once a credit score proxy is added) and the employment-length data
  quality finding.

**Slicers:** application year, state

---

## Page 3 — Model and Risk Segmentation

**KPI cards:** Loans Scored · Avg Predicted PD · Actual Default Rate · Expected Loss ·
Actual Loss

**Visuals:**

- **Line chart** — predicted PD versus actual default rate across the ten risk
  deciles. Source: `agg_model_calibration`. The two lines should track closely, which
  is what calibration means and is more informative than a single AUC number.
- **Column chart** — loan count by risk band, with exposure on a second axis. Source:
  `agg_risk_band_summary`.
- **Clustered column chart** — expected loss versus actual loss by risk band. Source:
  `agg_risk_band_summary`. Across the whole test set the model expects $662.6M against
  $693.2M actual, so it under-predicts losses by roughly 4%, which is worth stating
  plainly rather than hiding.
- **Table** — highest-risk scored loans: loan ID, grade, purpose, state, funded amount,
  predicted PD, risk band, expected loss. Sort descending by predicted PD, top 20.
  Source: `fact_scored_loans`.

**Slicers:** grade, risk band, state

**Important framing:** every loan on this page is from the out-of-time test set, which
the model never saw during training. Say so on the page. A model scoring loans it was
trained on would look far better and mean far less.

---

## Refresh

This is a static extract. If asked about production refresh, describe the intended
path honestly: Power BI Desktop → publish to the Power BI Service → gateway or cloud
connection to the warehouse → scheduled refresh. Presenting a design alongside a
working static extract is a credible answer. Claiming a live refresh that is not
wired up is not.

---

## What to capture for the repository

Screenshot each of the three pages and save them into `PowerBI/` as
`page1_portfolio_performance.png`, `page2_underwriting_funnel.png` and
`page3_model_segmentation.png`, then embed them in the project README under the
relevant workflow sections.
