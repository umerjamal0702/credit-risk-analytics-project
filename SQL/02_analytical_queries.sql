-- =====================================================================
-- Credit Risk Warehouse — Analytical Query Portfolio
-- =====================================================================
-- Runs against credit_risk_warehouse.db (SQLite) after 01_create_views.sql
-- has been executed. Demonstrates CTEs, window functions, self-joins,
-- date bucketing and cohort/vintage analysis on top of the raw LendingClub
-- 2007-2018Q4 accepted (2.26M) + rejected (27.6M) application data.
-- =====================================================================


-- ---------------------------------------------------------------------
-- Q1. Vintage (cohort) default rate trend, with a trailing 3-vintage
--     moving average to smooth year-to-year noise.
-- ---------------------------------------------------------------------
WITH by_year AS (
    SELECT
        issue_year,
        COUNT(*)                                            AS n_resolved,
        SUM(default_flag)                                   AS n_default,
        ROUND(100.0 * SUM(default_flag) / COUNT(*), 2)      AS default_rate_pct
    FROM vw_loan_performance
    WHERE default_flag IS NOT NULL
    GROUP BY issue_year
)
SELECT
    issue_year,
    n_resolved,
    n_default,
    default_rate_pct,
    ROUND(AVG(default_rate_pct) OVER (
        ORDER BY issue_year ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 2)                                                   AS default_rate_3yr_avg,
    ROUND(default_rate_pct - LAG(default_rate_pct) OVER (ORDER BY issue_year), 2)
                                                              AS yoy_change_pp
FROM by_year
ORDER BY issue_year;


-- ---------------------------------------------------------------------
-- Q2. Underwriting funnel: acceptance rate by state and year, ranked
--     to surface the loosest / tightest underwriting states each year.
-- ---------------------------------------------------------------------
WITH funnel AS (
    SELECT
        app_year,
        state,
        COUNT(*)                                             AS total_apps,
        SUM(CASE WHEN outcome = 'accepted' THEN 1 ELSE 0 END) AS accepted_apps
    FROM vw_applications_funnel
    WHERE state IS NOT NULL AND state <> '' AND app_year BETWEEN 2008 AND 2018
    GROUP BY app_year, state
    HAVING COUNT(*) >= 200                -- drop tiny/unreliable state-year cells
)
SELECT
    app_year,
    state,
    total_apps,
    accepted_apps,
    ROUND(100.0 * accepted_apps / total_apps, 2)             AS acceptance_rate_pct,
    RANK() OVER (
        PARTITION BY app_year ORDER BY 100.0 * accepted_apps / total_apps DESC
    )                                                         AS acceptance_rank_in_year
FROM funnel
ORDER BY app_year, acceptance_rank_in_year
LIMIT 100;


-- ---------------------------------------------------------------------
-- Q3. Accepted vs. rejected applicant profile, by year: how much
--     tighter is DTI and how much smaller is the requested amount for
--     applicants who get funded vs. turned down? (Reject-inference
--     angle — approximating the credit profile gap without a score
--     that's consistently populated across both files.)
-- ---------------------------------------------------------------------
SELECT
    app_year,
    outcome,
    COUNT(*)                                                 AS n_apps,
    ROUND(AVG(dti_pct), 1)                                   AS avg_dti_pct,
    ROUND(AVG(amount_requested), 0)                          AS avg_amount_requested
FROM vw_applications_funnel
WHERE dti_pct IS NOT NULL AND dti_pct BETWEEN 0 AND 100   -- drop data-entry outliers
  AND app_year BETWEEN 2008 AND 2018
GROUP BY app_year, outcome
ORDER BY app_year, outcome;


-- ---------------------------------------------------------------------
-- Q4. Grade-level scorecard: volume, weighted-average rate, default
--     rate, dollar loss and a simple risk-adjusted-yield proxy, ranked
--     by default rate.
-- ---------------------------------------------------------------------
WITH grade_stats AS (
    SELECT
        grade,
        COUNT(*)                                             AS n_loans,
        SUM(funded_amnt)                                     AS total_funded,
        ROUND(SUM(int_rate * funded_amnt) / SUM(funded_amnt), 2)
                                                              AS wavg_int_rate,
        SUM(default_flag)                                    AS n_default,
        ROUND(100.0 * SUM(default_flag) / COUNT(*), 2)       AS default_rate_pct,
        SUM(net_loss)                                        AS total_net_loss
    FROM vw_loan_performance
    WHERE default_flag IS NOT NULL
    GROUP BY grade
)
SELECT
    grade,
    n_loans,
    total_funded,
    wavg_int_rate,
    default_rate_pct,
    total_net_loss,
    ROUND(100.0 * total_net_loss / total_funded, 2)          AS loss_rate_pct_of_funded,
    RANK() OVER (ORDER BY default_rate_pct DESC)             AS risk_rank
FROM grade_stats
ORDER BY grade;


-- ---------------------------------------------------------------------
-- Q5. Recovery analysis: of the dollars lost to charge-off, how much
--     comes back through collections, by grade — informs an LGD
--     (loss-given-default) assumption instead of the flat 100% used
--     in the v1 PD model's expected-loss calc.
-- ---------------------------------------------------------------------
SELECT
    grade,
    COUNT(*)                                                 AS n_defaults,
    ROUND(SUM(funded_amnt - total_rec_prncp), 0)             AS gross_unpaid_balance,
    ROUND(SUM(recoveries), 0)                                AS total_recoveries,
    ROUND(100.0 * SUM(recoveries) / NULLIF(SUM(funded_amnt - total_rec_prncp), 0), 2)
                                                              AS recovery_rate_pct,
    ROUND(100.0 - 100.0 * SUM(recoveries) / NULLIF(SUM(funded_amnt - total_rec_prncp), 0), 2)
                                                              AS implied_lgd_pct
FROM vw_loan_performance
WHERE default_flag = 1
GROUP BY grade
ORDER BY grade;


-- ---------------------------------------------------------------------
-- Q6. Monthly issuance & risk trend with a 3-month moving average —
--     the kind of time series a Power BI line chart would consume
--     directly.
-- ---------------------------------------------------------------------
WITH monthly AS (
    SELECT
        issue_yyyymm,
        COUNT(*)                                             AS loans_issued,
        SUM(funded_amnt)                                     AS dollars_issued,
        SUM(CASE WHEN default_flag = 1 THEN 1 ELSE 0 END)    AS defaults_to_date,
        SUM(CASE WHEN default_flag IS NOT NULL THEN 1 ELSE 0 END) AS resolved_to_date
    FROM vw_loan_performance
    GROUP BY issue_yyyymm
)
SELECT
    issue_yyyymm,
    loans_issued,
    dollars_issued,
    ROUND(AVG(loans_issued) OVER (
        ORDER BY issue_yyyymm ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ), 0)                                                    AS loans_issued_3mo_avg,
    CASE WHEN resolved_to_date > 0
         THEN ROUND(100.0 * defaults_to_date / resolved_to_date, 2) END
                                                              AS default_rate_pct_of_resolved
FROM monthly
ORDER BY issue_yyyymm;


-- ---------------------------------------------------------------------
-- Q7. Purpose x Grade cross-tab of default rate — which loan purposes
--     are riskiest *within* each grade band (i.e., after controlling
--     for the grade the model already assigned).
-- ---------------------------------------------------------------------
WITH cross_tab AS (
    SELECT
        grade,
        purpose,
        COUNT(*)                                             AS n_loans,
        SUM(default_flag)                                    AS n_default,
        ROUND(100.0 * SUM(default_flag) / COUNT(*), 2)       AS default_rate_pct
    FROM vw_loan_performance
    WHERE default_flag IS NOT NULL
    GROUP BY grade, purpose
    HAVING COUNT(*) >= 500
)
SELECT
    grade,
    purpose,
    n_loans,
    default_rate_pct,
    RANK() OVER (PARTITION BY grade ORDER BY default_rate_pct DESC) AS risk_rank_in_grade
FROM cross_tab
ORDER BY grade, risk_rank_in_grade;


-- ---------------------------------------------------------------------
-- Q8. State-level concentration & risk: which states carry the most
--     exposure, and how does their default rate compare to the
--     portfolio-wide rate (over/under-index)?
-- ---------------------------------------------------------------------
WITH state_stats AS (
    SELECT
        addr_state,
        COUNT(*)                                             AS n_loans,
        SUM(funded_amnt)                                     AS total_exposure,
        ROUND(100.0 * SUM(default_flag) / COUNT(*), 2)       AS default_rate_pct
    FROM vw_loan_performance
    WHERE default_flag IS NOT NULL
    GROUP BY addr_state
    HAVING COUNT(*) >= 1000
),
portfolio AS (
    SELECT ROUND(100.0 * SUM(default_flag) / COUNT(*), 2) AS overall_rate
    FROM vw_loan_performance WHERE default_flag IS NOT NULL
)
SELECT
    s.addr_state,
    s.n_loans,
    s.total_exposure,
    s.default_rate_pct,
    p.overall_rate                                           AS portfolio_default_rate_pct,
    ROUND(s.default_rate_pct - p.overall_rate, 2)             AS pp_vs_portfolio,
    RANK() OVER (ORDER BY s.total_exposure DESC)              AS exposure_rank
FROM state_stats s CROSS JOIN portfolio p
ORDER BY exposure_rank
LIMIT 20;
