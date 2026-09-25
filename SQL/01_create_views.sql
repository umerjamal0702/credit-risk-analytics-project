-- =====================================================================
-- Credit Risk Warehouse — Mart Layer
-- =====================================================================
-- raw_accepted / raw_rejected hold the source data as-is (all TEXT,
-- loaded straight from the LendingClub 2007-2018Q4 CSVs). These views
-- sit on top and do the cleaning: type casting, date parsing, default
-- labeling, and a common grain so accepted + rejected applications can
-- be compared side by side.
-- =====================================================================

DROP VIEW IF EXISTS vw_loan_performance;
DROP VIEW IF EXISTS vw_applications_funnel;

-- ---------------------------------------------------------------------
-- vw_loan_performance
-- One row per *funded* loan with a resolved outcome (Fully Paid or
-- Charged Off / Default). Loans still "Current", "Late", or "In Grace
-- Period" are excluded because their final outcome isn't known yet —
-- including them would bias the default rate downward (survivorship).
-- This is the same leakage-aware logic used in the PD model: fields
-- only known post-origination (total_rec_prncp, recoveries, etc.) are
-- exposed here for performance analysis, but a modeling view would
-- drop them.
-- ---------------------------------------------------------------------
CREATE VIEW vw_loan_performance AS
SELECT
    id,
    grade,
    sub_grade,
    purpose,
    home_ownership,
    verification_status,
    addr_state,
    substr(zip_code,1,3)                                   AS zip3,
    term,
    issue_d,
    -- issue_d comes in as "Mon-YYYY" (e.g. "Dec-2015") — parse to a
    -- sortable year and yyyymm key
    CAST(substr(issue_d, instr(issue_d,'-')+1) AS INTEGER)  AS issue_year,
    CASE substr(issue_d,1,3)
        WHEN 'Jan' THEN '01' WHEN 'Feb' THEN '02' WHEN 'Mar' THEN '03'
        WHEN 'Apr' THEN '04' WHEN 'May' THEN '05' WHEN 'Jun' THEN '06'
        WHEN 'Jul' THEN '07' WHEN 'Aug' THEN '08' WHEN 'Sep' THEN '09'
        WHEN 'Oct' THEN '10' WHEN 'Nov' THEN '11' WHEN 'Dec' THEN '12'
    END                                                     AS issue_month,
    substr(issue_d, instr(issue_d,'-')+1) || '-' ||
    CASE substr(issue_d,1,3)
        WHEN 'Jan' THEN '01' WHEN 'Feb' THEN '02' WHEN 'Mar' THEN '03'
        WHEN 'Apr' THEN '04' WHEN 'May' THEN '05' WHEN 'Jun' THEN '06'
        WHEN 'Jul' THEN '07' WHEN 'Aug' THEN '08' WHEN 'Sep' THEN '09'
        WHEN 'Oct' THEN '10' WHEN 'Nov' THEN '11' WHEN 'Dec' THEN '12'
    END                                                     AS issue_yyyymm,
    loan_status,
    CASE
        WHEN loan_status IN ('Charged Off', 'Default',
                              'Does not meet the credit policy. Status:Charged Off')
            THEN 1
        WHEN loan_status IN ('Fully Paid',
                              'Does not meet the credit policy. Status:Fully Paid')
            THEN 0
        ELSE NULL
    END                                                     AS default_flag,
    CAST(loan_amnt AS REAL)                                 AS loan_amnt,
    CAST(funded_amnt AS REAL)                                AS funded_amnt,
    CAST(int_rate AS REAL)                                   AS int_rate,
    CAST(installment AS REAL)                                AS installment,
    CAST(annual_inc AS REAL)                                 AS annual_inc,
    CAST(dti AS REAL)                                        AS dti,
    CAST(fico_range_low AS REAL)                             AS fico_range_low,
    CAST(fico_range_high AS REAL)                            AS fico_range_high,
    CAST(total_pymnt AS REAL)                                AS total_pymnt,
    CAST(total_rec_prncp AS REAL)                            AS total_rec_prncp,
    CAST(total_rec_int AS REAL)                              AS total_rec_int,
    CAST(recoveries AS REAL)                                 AS recoveries,
    CAST(collection_recovery_fee AS REAL)                    AS collection_recovery_fee,
    -- net dollar loss for a resolved loan: unpaid principal minus what
    -- was later recovered through collections (floor at 0 for edge cases)
    CASE
        WHEN loan_status IN ('Charged Off', 'Default',
                              'Does not meet the credit policy. Status:Charged Off')
        THEN MAX(CAST(funded_amnt AS REAL) - CAST(total_rec_prncp AS REAL)
                  - CAST(recoveries AS REAL), 0)
        ELSE 0
    END                                                     AS net_loss,
    -- recovery rate on the defaulted balance (NULL for non-defaults)
    CASE
        WHEN loan_status IN ('Charged Off', 'Default',
                              'Does not meet the credit policy. Status:Charged Off')
             AND (CAST(funded_amnt AS REAL) - CAST(total_rec_prncp AS REAL)) > 0
        THEN CAST(recoveries AS REAL)
             / (CAST(funded_amnt AS REAL) - CAST(total_rec_prncp AS REAL))
        ELSE NULL
    END                                                     AS recovery_rate,
    application_type,
    emp_length,
    mort_acc,
    pub_rec,
    revol_util
FROM raw_accepted
WHERE issue_d IS NOT NULL AND issue_d <> '';

-- ---------------------------------------------------------------------
-- vw_applications_funnel
-- Every application LendingClub received — accepted (funded) and
-- rejected — at a common grain: date, state, zip3, employment length,
-- DTI, amount requested. Used for acceptance-rate / underwriting-
-- funnel analysis and for comparing the credit profile of accepted vs
-- rejected applicants (a reject-inference angle the accepted-only
-- dataset can't answer on its own).
-- ---------------------------------------------------------------------
CREATE VIEW vw_applications_funnel AS
SELECT
    'accepted'                                              AS outcome,
    id                                                       AS application_id,
    CAST(substr(issue_d, instr(issue_d,'-')+1) AS INTEGER)   AS app_year,
    addr_state                                               AS state,
    substr(zip_code,1,3)                                     AS zip3,
    emp_length,
    CAST(dti AS REAL)                                        AS dti_pct,
    CAST(loan_amnt AS REAL)                                  AS amount_requested,
    NULL                                                     AS risk_score
FROM raw_accepted
WHERE issue_d IS NOT NULL AND issue_d <> ''

UNION ALL

SELECT
    'rejected'                                               AS outcome,
    NULL                                                     AS application_id,
    CAST(substr(application_date,1,4) AS INTEGER)            AS app_year,
    state,
    substr(zip_code,1,3)                                     AS zip3,
    emp_length,
    CASE WHEN dti_pct <> '' THEN CAST(REPLACE(dti_pct,'%','') AS REAL) END AS dti_pct,
    CAST(amount_requested AS REAL)                           AS amount_requested,
    CASE WHEN risk_score <> '' THEN CAST(risk_score AS REAL) END AS risk_score
FROM raw_rejected
WHERE application_date IS NOT NULL AND application_date <> '';
