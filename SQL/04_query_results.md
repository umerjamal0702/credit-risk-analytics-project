# Query Results

Output of every query in `02_analytical_queries.sql`, run against the warehouse built by `00_build_warehouse.py` over the full 2007-2018 LendingClub data: 2,260,668 funded loans and 27,648,741 declined applications.

Regenerate with `python SQL/03_run_queries.py`. Result sets longer than 25 rows are truncated here; the full row count is stated above each table.

---

## Q1. Vintage (cohort) default rate trend, with a trailing 3-vintage moving average to smooth year-to-year noise.

12 rows returned in 1.4s.

| issue_year | n_resolved | n_default | default_rate_pct | default_rate_3yr_avg | yoy_change_pp |
|---|---|---|---|---|---|
| 2007 | 603 | 158 | 26.20 | 26.20 |  |
| 2008 | 2,393 | 496 | 20.73 | 23.46 | -5.47 |
| 2009 | 5,281 | 723 | 13.69 | 20.21 | -7.04 |
| 2010 | 12,537 | 1,757 | 14.01 | 16.14 | 0.32 |
| 2011 | 21,721 | 3,297 | 15.18 | 14.29 | 1.17 |
| 2012 | 53,367 | 8,644 | 16.20 | 15.13 | 1.02 |
| 2013 | 134,804 | 21,024 | 15.60 | 15.66 | -0.6 |
| 2014 | 223,103 | 41,162 | 18.45 | 16.75 | 2.85 |
| 2015 | 375,546 | 75,804 | 20.19 | 18.08 | 1.74 |
| 2016 | 293,105 | 68,252 | 23.29 | 20.64 | 3.10 |
| 2017 | 169,321 | 39,169 | 23.13 | 22.20 | -0.16 |
| 2018 | 56,318 | 8,874 | 15.76 | 20.73 | -7.37 |

## Q2. Underwriting funnel: acceptance rate by state and year, ranked to surface the loosest / tightest underwriting states each year.

100 rows returned in 34.0s. First 25 shown.

| app_year | state | total_apps | accepted_apps | acceptance_rate_pct | acceptance_rank_in_year |
|---|---|---|---|---|---|
| 2008 | CA | 3,735 | 456 | 12.21 | 1 |
| 2008 | CT | 367 | 42 | 11.44 | 2 |
| 2008 | NJ | 839 | 95 | 11.32 | 3 |
| 2008 | MA | 591 | 65 | 11.00 | 4 |
| 2008 | CO | 628 | 66 | 10.51 | 5 |
| 2008 | TN | 301 | 30 | 9.97 | 6 |
| 2008 | VA | 925 | 91 | 9.84 | 7 |
| 2008 | NY | 1,904 | 178 | 9.35 | 8 |
| 2008 | MD | 681 | 62 | 9.10 | 9 |
| 2008 | KS | 286 | 26 | 9.09 | 10 |
| 2008 | MN | 420 | 38 | 9.05 | 11 |
| 2008 | AZ | 608 | 53 | 8.72 | 12 |
| 2008 | GA | 1,127 | 95 | 8.43 | 13 |
| 2008 | IL | 1,133 | 95 | 8.38 | 14 |
| 2008 | NV | 355 | 29 | 8.17 | 15 |
| 2008 | OR | 323 | 26 | 8.05 | 16 |
| 2008 | TX | 2,147 | 170 | 7.92 | 17 |
| 2008 | FL | 2,098 | 162 | 7.72 | 18 |
| 2008 | WA | 636 | 49 | 7.70 | 19 |
| 2008 | NC | 613 | 46 | 7.50 | 20 |
| 2008 | OH | 1,021 | 75 | 7.35 | 21 |
| 2008 | MO | 560 | 38 | 6.79 | 22 |
| 2008 | MI | 782 | 53 | 6.78 | 23 |
| 2008 | PA | 1,257 | 83 | 6.60 | 24 |
| 2008 | LA | 288 | 19 | 6.60 | 25 |

## Q3. Accepted vs. rejected applicant profile, by year: how much tighter is DTI and how much smaller is the requested amount for applicants who get funded vs. turned down? (Reject-inference angle — approximating the credit profile gap without a score that's consistently populated across both files.)

22 rows returned in 37.9s.

| app_year | outcome | n_apps | avg_dti_pct | avg_amount_requested |
|---|---|---|---|---|
| 2008 | accepted | 2,393 | 13.20 | 8,825.00 |
| 2008 | rejected | 22,887 | 18.80 | 8,636.00 |
| 2009 | accepted | 5,281 | 12.50 | 9,833.00 |
| 2009 | rejected | 48,667 | 18.90 | 10,336.00 |
| 2010 | accepted | 12,537 | 13.10 | 10,528.00 |
| 2010 | rejected | 106,183 | 20.00 | 11,010.00 |
| 2011 | accepted | 21,721 | 13.80 | 12,048.00 |
| 2011 | rejected | 205,456 | 18.80 | 12,983.00 |
| 2012 | accepted | 53,367 | 16.70 | 13,462.00 |
| 2012 | rejected | 326,166 | 20.50 | 14,343.00 |
| 2013 | accepted | 134,814 | 17.20 | 14,707.00 |
| 2013 | rejected | 731,387 | 21.20 | 13,210.00 |
| 2014 | accepted | 235,629 | 18.00 | 14,870.00 |
| 2014 | rejected | 1,645,497 | 21.60 | 12,036.00 |
| 2015 | accepted | 421,086 | 19.10 | 15,240.00 |
| 2015 | rejected | 2,537,647 | 23.20 | 12,528.00 |
| 2016 | accepted | 434,280 | 18.80 | 14,732.00 |
| 2016 | rejected | 4,326,687 | 23.90 | 12,365.00 |
| 2017 | accepted | 442,728 | 18.80 | 14,835.00 |
| 2017 | rejected | 6,541,729 | 27.20 | 12,074.00 |
| 2018 | accepted | 493,666 | 18.90 | 16,010.00 |
| 2018 | rejected | 9,140,232 | 30.20 | 12,655.00 |

## Q4. Grade-level scorecard: volume, weighted-average rate, default rate, dollar loss and a simple risk-adjusted-yield proxy, ranked by default rate.

7 rows returned in 2.5s.

| grade | n_loans | total_funded | wavg_int_rate | default_rate_pct | total_net_loss | loss_rate_pct_of_funded | risk_rank |
|---|---|---|---|---|---|---|---|
| A | 235,193 | 3,264,291,775.00 | 7.11 | 6.04 | 103,445,987.80 | 3.17 | 7 |
| B | 393,102 | 5,198,798,075.00 | 10.66 | 13.40 | 407,721,167.09 | 7.84 | 6 |
| C | 382,323 | 5,419,304,775.00 | 14.07 | 22.44 | 789,870,956.01 | 14.58 | 5 |
| D | 201,657 | 3,073,793,625.00 | 17.76 | 30.38 | 645,806,957.73 | 21.01 | 4 |
| E | 94,192 | 1,652,654,100.00 | 21.14 | 38.43 | 454,217,096.01 | 27.48 | 3 |
| F | 32,306 | 613,936,900.00 | 24.92 | 45.15 | 207,291,870.46 | 33.76 | 2 |
| G | 9,326 | 190,098,450.00 | 27.61 | 49.67 | 71,673,331.15 | 37.70 | 1 |

## Q5. Recovery analysis: of the dollars lost to charge-off, how much comes back through collections, by grade — informs an LGD (loss-given-default) assumption instead of the flat 100% used in the v1 PD model's expected-loss calc.

7 rows returned in 2.0s.

| grade | n_defaults | gross_unpaid_balance | total_recoveries | recovery_rate_pct | implied_lgd_pct |
|---|---|---|---|---|---|
| A | 14,214 | 114,955,166.00 | 11,529,259.00 | 10.03 | 89.97 |
| B | 52,661 | 455,004,481.00 | 47,346,937.00 | 10.41 | 89.59 |
| C | 85,805 | 883,900,256.00 | 94,140,390.00 | 10.65 | 89.35 |
| D | 61,264 | 723,757,063.00 | 78,061,750.00 | 10.79 | 89.21 |
| E | 36,199 | 511,981,713.00 | 57,851,907.00 | 11.30 | 88.70 |
| F | 14,585 | 234,400,636.00 | 27,167,266.00 | 11.59 | 88.41 |
| G | 4,632 | 80,813,690.00 | 9,165,447.00 | 11.34 | 88.66 |

## Q6. Monthly issuance & risk trend with a 3-month moving average — the kind of time series a Power BI line chart would consume directly.

139 rows returned in 2.2s. First 25 shown.

| issue_yyyymm | loans_issued | dollars_issued | loans_issued_3mo_avg | default_rate_pct_of_resolved |
|---|---|---|---|---|
| 2007-06 | 24 | 91,850.00 | 24.00 | 12.50 |
| 2007-07 | 63 | 332,100.00 | 44.00 | 11.11 |
| 2007-08 | 74 | 488,600.00 | 54.00 | 27.03 |
| 2007-09 | 53 | 372,950.00 | 63.00 | 24.53 |
| 2007-10 | 105 | 682,875.00 | 77.00 | 32.38 |
| 2007-11 | 112 | 995,950.00 | 90.00 | 30.36 |
| 2007-12 | 172 | 1,827,225.00 | 130.00 | 27.33 |
| 2008-01 | 305 | 2,902,250.00 | 196.00 | 27.54 |
| 2008-02 | 306 | 2,951,225.00 | 261.00 | 19.93 |
| 2008-03 | 402 | 4,150,050.00 | 338.00 | 22.14 |
| 2008-04 | 259 | 1,811,025.00 | 322.00 | 24.32 |
| 2008-05 | 115 | 582,000.00 | 259.00 | 21.74 |
| 2008-06 | 124 | 654,975.00 | 166.00 | 17.74 |
| 2008-07 | 141 | 809,250.00 | 127.00 | 21.28 |
| 2008-08 | 100 | 468,450.00 | 122.00 | 12.00 |
| 2008-09 | 57 | 270,950.00 | 99.00 | 17.54 |
| 2008-10 | 122 | 945,400.00 | 93.00 | 17.21 |
| 2008-11 | 209 | 2,008,675.00 | 129.00 | 18.66 |
| 2008-12 | 253 | 2,420,775.00 | 195.00 | 15.81 |
| 2009-01 | 269 | 2,469,700.00 | 244.00 | 15.24 |
| 2009-02 | 302 | 2,708,950.00 | 275.00 | 13.58 |
| 2009-03 | 324 | 3,061,300.00 | 298.00 | 12.65 |
| 2009-04 | 333 | 3,071,350.00 | 320.00 | 14.71 |
| 2009-05 | 359 | 3,351,250.00 | 339.00 | 14.21 |
| 2009-06 | 406 | 3,591,925.00 | 366.00 | 14.29 |

## Q7. Purpose x Grade cross-tab of default rate — which loan purposes are riskiest *within* each grade band (i.e., after controlling for the grade the model already assigned).

68 rows returned in 2.8s. First 25 shown.

| grade | purpose | n_loans | default_rate_pct | risk_rank_in_grade |
|---|---|---|---|---|
| A | small_business | 1,445 | 12.39 | 1 |
| A | moving | 839 | 9.06 | 2 |
| A | vacation | 1,174 | 8.60 | 3 |
| A | medical | 2,008 | 8.02 | 4 |
| A | other | 8,989 | 6.91 | 5 |
| A | house | 993 | 6.34 | 6 |
| A | debt_consolidation | 115,113 | 6.06 | 7 |
| A | credit_card | 74,562 | 5.90 | 8 |
| A | major_purchase | 6,714 | 5.70 | 9 |
| A | home_improvement | 18,893 | 5.40 | 10 |
| A | car | 3,822 | 5.21 | 11 |
| B | small_business | 2,565 | 20.90 | 1 |
| B | moving | 1,848 | 16.72 | 2 |
| B | vacation | 2,321 | 15.12 | 3 |
| B | medical | 3,867 | 15.10 | 4 |
| B | major_purchase | 8,389 | 13.66 | 5 |
| B | debt_consolidation | 220,565 | 13.40 | 6 |
| B | other | 17,591 | 13.36 | 7 |
| B | house | 1,429 | 13.23 | 8 |
| B | credit_card | 103,995 | 13.22 | 9 |
| B | home_improvement | 25,179 | 13.05 | 10 |
| B | car | 4,508 | 11.16 | 11 |
| B | wedding | 552 | 10.33 | 12 |
| C | small_business | 3,951 | 26.58 | 1 |
| C | medical | 4,874 | 23.14 | 2 |

## Q8. State-level concentration & risk: which states carry the most exposure, and how does their default rate compare to the portfolio-wide rate (over/under-index)?

20 rows returned in 3.8s.

| addr_state | n_loans | total_exposure | default_rate_pct | portfolio_default_rate_pct | pp_vs_portfolio | exposure_rank |
|---|---|---|---|---|---|---|
| CA | 196,853 | 2,885,623,375.00 | 19.63 | 19.98 | -0.35 | 1 |
| TX | 110,354 | 1,673,963,425.00 | 19.84 | 19.98 | -0.14 | 2 |
| NY | 110,097 | 1,572,517,275.00 | 22.05 | 19.98 | 2.07 | 3 |
| FL | 95,843 | 1,314,115,350.00 | 21.50 | 19.98 | 1.52 | 4 |
| IL | 51,870 | 762,742,825.00 | 18.12 | 19.98 | -1.86 | 5 |
| NJ | 48,583 | 735,800,150.00 | 21.12 | 19.98 | 1.14 | 6 |
| PA | 45,656 | 639,899,050.00 | 20.83 | 19.98 | 0.85 | 7 |
| GA | 43,480 | 633,637,025.00 | 18.43 | 19.98 | -1.55 | 8 |
| OH | 43,947 | 600,497,300.00 | 20.52 | 19.98 | 0.54 | 9 |
| VA | 38,119 | 582,987,150.00 | 19.94 | 19.98 | -0.04 | 10 |
| NC | 37,826 | 536,222,975.00 | 20.80 | 19.98 | 0.82 | 11 |
| MI | 35,308 | 486,587,650.00 | 20.31 | 19.98 | 0.33 | 12 |
| MA | 31,071 | 474,433,850.00 | 19.07 | 19.98 | -0.91 | 13 |
| MD | 31,298 | 472,861,575.00 | 21.34 | 19.98 | 1.36 | 14 |
| AZ | 32,748 | 454,859,850.00 | 19.66 | 19.98 | -0.32 | 15 |
| CO | 29,736 | 434,955,025.00 | 15.54 | 19.98 | -4.44 | 16 |
| WA | 29,235 | 431,615,400.00 | 15.79 | 19.98 | -4.19 | 17 |
| MN | 24,004 | 335,050,975.00 | 19.76 | 19.98 | -0.22 | 18 |
| IN | 21,726 | 304,786,425.00 | 21.43 | 19.98 | 1.45 | 19 |
| MO | 21,340 | 295,758,100.00 | 21.34 | 19.98 | 1.36 | 20 |

