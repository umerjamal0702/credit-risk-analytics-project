# Power BI Build Guide — Credit Risk Portfolio Dashboard

This session can't drive Power BI Desktop directly (no local access to your machine's
apps), so this is a data extract plus a step-by-step guide for you to assemble the
dashboard yourself. Everything below was generated from, and validated against, the
SQLite warehouse built in Phase 1 (2.26M accepted + 27.6M rejected loan applications,
2007-2018).

## 1. Files in this delivery

| File | Grain | Rows | Use |
|---|---|---|---|
| `fact_loan_performance_part{1,2,3}of3.csv.gz` | 1 row per resolved loan (split into 3 files for file-size limits) | 449,367 / 449,367 / 449,365 | Main fact table — import all 3 and append |
| `dim_date.csv` | 1 row per month, 2007-01 to 2018-12 | 144 | Date dimension for time intelligence |
| `agg_vintage_default_trend.csv` | 1 row per issue year | 12 | Pre-aggregated — optional shortcut |
| `agg_grade_scorecard.csv` | 1 row per grade | 7 | Pre-aggregated — optional shortcut |
| `agg_recovery_by_grade.csv` | 1 row per grade | 7 | Pre-aggregated — optional shortcut |
| `agg_monthly_trend.csv` | 1 row per month | 139 | Pre-aggregated — optional shortcut |
| `agg_state_risk.csv` | 1 row per state (top 50 by volume) | 50 | Pre-aggregated — optional shortcut |
| `agg_purpose_grade_risk.csv` | 1 row per grade x purpose | 68 | Pre-aggregated — optional shortcut |
| `agg_acceptance_funnel_by_state_year.csv` | 1 row per state x year | 490 | Underwriting funnel |

Unzip all three `fact_loan_performance_part*of3.csv.gz` files before importing —
Power BI's CSV connector doesn't read gzip directly. They're split only because of a
file-transfer size limit; in Power Query, import all 3 as separate queries and use
**Append Queries** (or **Combine Files** if you put them in one folder) to stitch
them back into a single `fact_loan_performance` table before building anything else.
The `agg_*` tables are optional: they let you build a
dashboard fast without writing DAX first, but the real portfolio value is building
the same numbers as **measures** on the fact table (see step 3) — that's what an
interviewer will actually ask you to walk through.

## 2. Import & model

1. **Get Data → Text/CSV** → import `fact_loan_performance.csv` and `dim_date.csv`
   (and any `agg_*` tables you want as a quick-start).
2. In Power Query, check types: `issue_yyyymm` and `dim_date[yyyymm]` should both be
   **Text** (they're the join key, "YYYY-MM"); `dim_date[date]` should be **Date**.
3. **Model view** → create a relationship: `dim_date[yyyymm]` (one) → 
   `fact_loan_performance[issue_yyyymm]` (many).
4. Right-click `dim_date` → **Mark as date table**, using the `date` column. This
   unlocks time-intelligence DAX functions (`SAMEPERIODLASTYEAR`, `DATEADD`, etc.)
   later if you extend the model.
5. Hide the raw `agg_*` tables' underlying columns you don't need for slicing, or
   just leave them as standalone quick-reference tables — either is fine for a
   portfolio piece as long as you can explain the choice.

## 3. Core DAX measures (build these on `fact_loan_performance`)

```
Total Loans            = COUNTROWS(fact_loan_performance)
Total Funded            = SUM(fact_loan_performance[funded_amnt])
Total Defaults          = SUM(fact_loan_performance[default_flag])
Default Rate            = DIVIDE([Total Defaults], [Total Loans])
Total Net Loss           = SUM(fact_loan_performance[net_loss])
Loss Rate (% of Funded)  = DIVIDE([Total Net Loss], [Total Funded])
Weighted Avg Interest Rate =
    DIVIDE(
        SUMX(fact_loan_performance, fact_loan_performance[int_rate] * fact_loan_performance[funded_amnt]),
        [Total Funded]
    )
Avg FICO =
    AVERAGEX(
        fact_loan_performance,
        (fact_loan_performance[fico_range_low] + fact_loan_performance[fico_range_high]) / 2
    )
Recovery Rate (Defaults Only) =
    DIVIDE(
        CALCULATE(SUM(fact_loan_performance[recoveries]), fact_loan_performance[default_flag] = 1),
        CALCULATE(SUM(fact_loan_performance[funded_amnt]) - SUM(fact_loan_performance[total_rec_prncp]),
                   fact_loan_performance[default_flag] = 1)
    )
```

(`recoveries` and `total_rec_prncp` are included in `fact_loan_performance.csv.gz`
specifically so this measure works live; `agg_recovery_by_grade.csv` has the same
number pre-computed by grade if you'd rather use that directly.)

Once `dim_date` is marked as a date table, add:
```
Default Rate YoY =
    VAR CurrentRate = [Default Rate]
    VAR PriorRate = CALCULATE([Default Rate], SAMEPERIODLASTYEAR(dim_date[date]))
    RETURN CurrentRate - PriorRate
```

## 4. Suggested pages & visuals

**Page 1 — Portfolio Overview**
- KPI cards: Total Loans, Total Funded, Default Rate, Loss Rate, Weighted Avg
  Interest Rate.
- Line chart: `issue_yyyymm` (x-axis) vs Total Funded and Default Rate (dual axis,
  or two stacked charts) — use `agg_monthly_trend.csv` or the fact table + dim_date.
- Slicers: issue_year, grade, purpose.

**Page 2 — Vintage / Cohort Analysis**
- Line chart: issue_year vs default_rate_pct, with the 3-year moving average as a
  second series (from `agg_vintage_default_trend.csv` — this is the "does credit
  quality drift over time" story; the 2008 crisis cohort and the 2015-2017 rise are
  worth calling out explicitly in the write-up).

**Page 3 — Grade & Purpose Risk**
- Bar chart: default rate by grade (`agg_grade_scorecard.csv`), ordered A→G — should
  climb monotonically; a break in that pattern is worth investigating.
- Matrix or heatmap: grade x purpose default rate (`agg_purpose_grade_risk.csv`) —
  shows which purposes are riskiest *within* a grade band, i.e. after controlling for
  the risk grade LendingClub already assigned.

**Page 4 — Recovery / Loss Given Default**
- Bar chart: recovery rate by grade, and implied LGD (100 - recovery rate) by grade
  (`agg_recovery_by_grade.csv`). Call out that implied LGD is close to ~90% across
  all grades — informs a more realistic expected-loss assumption than a flat 100%.

**Page 5 — Underwriting Funnel (accepted vs rejected)**
- Map or bar chart: acceptance rate by state (`agg_acceptance_funnel_by_state_year.csv`),
  with a year slicer.
- Optional: bring in the accept/reject model result (headline AUC 0.67 on DTI +
  amount + year + state alone, 0.86 with the credit-score proxy) as a text box —
  this is where you talk through the reject-inference angle and the employment-length
  data-quality catch (see the case-study writeup for the full finding).

**Page 6 — State Exposure**
- Filled map: total_exposure by state (`agg_state_risk.csv`).
- Table: state, n_loans, total_exposure, default_rate_pct, ranked by exposure —
  useful for a "where is concentration risk" narrative.

## 5. Refresh

This is a static extract (a snapshot of the SQLite warehouse). For a "scheduled
refresh" story in an interview, you can describe the intended production path
honestly: Power BI Desktop → publish to the Power BI Service → a gateway or
cloud data source connection to the warehouse (Postgres/Snowflake/etc. in a real
deployment) → scheduled refresh. Framing it as "here's the pipeline design, and
here's a static extract of it running end-to-end" is a perfectly credible answer
for a portfolio piece — don't overclaim a live refresh that isn't actually wired up.

## 6. What this demonstrates in an interview

- A modeled star-ish schema (fact + date dimension), not just a flat pasted table.
- DAX measures built from first principles (`DIVIDE`, `SUMX`, `CALCULATE`,
  `SAMEPERIODLASTYEAR`) rather than only pre-aggregated columns.
- A narrative that ties back to the SQL warehouse and the PD model — the same
  numbers (default rate, LGD, vintage trend) show up consistently across the SQL
  queries, the Python model, and this dashboard, which is exactly the kind of
  cross-checked consistency a hiring manager looks for.
