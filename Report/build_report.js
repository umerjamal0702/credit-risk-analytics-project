/*
 * Build credit_risk_report.docx from the v2 model results.
 *
 * Reads Python/pd_model_v2/deliverable_data_v2.json — the same payload the Excel
 * workbook uses — so the two deliverables quote identical figures.
 */
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, BorderStyle, PageBreak, Header, Footer,
  PageNumber,
} = require('docx');

const DATA_PATH = path.join(__dirname, '..', 'Python', 'pd_model_v2', 'deliverable_data_v2.json');
const D = JSON.parse(fs.readFileSync(DATA_PATH, 'utf8'));
const { portfolio, model, scoring, reject_inference: rj, warehouse } = D;
const v1 = model.v1_comparison;

const NAVY = '1F4E78';
const GRAY = '666666';

const pct = (v, d = 1) => (v * 100).toFixed(d) + '%';
const money = (v, d = 1) => {
  v = Number(v);
  if (Math.abs(v) >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
  if (Math.abs(v) >= 1e6) return '$' + (v / 1e6).toFixed(d) + 'M';
  if (Math.abs(v) >= 1e3) return '$' + (v / 1e3).toFixed(d) + 'K';
  return '$' + v.toFixed(0);
};
const num = (v) => Number(v).toLocaleString('en-US');
const title = (s) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

function h1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 320, after: 160 } });
}
function h2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 } });
}
function body(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, size: 22, ...opts })],
    spacing: { after: 160 },
  });
}
function bullet(text) {
  return new Paragraph({
    children: [new TextRun({ text, size: 22 })],
    bullet: { level: 0 },
    spacing: { after: 80 },
  });
}
function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, size: 18, italics: true, color: GRAY })],
    spacing: { after: 200 },
  });
}
function pageBreak() {
  return new Paragraph({ children: [new PageBreak()] });
}

function cell(text, { header = false, width, align = AlignmentType.LEFT, color } = {}) {
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: header ? { type: ShadingType.CLEAR, fill: NAVY } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({
      alignment: align,
      children: [new TextRun({
        text: String(text),
        bold: header,
        size: 20,
        color: header ? 'FFFFFF' : (color || '000000'),
      })],
    })],
  });
}

// Numbers read best right-aligned, text left-aligned. Column 0 is always text;
// leftCols names any further text columns (a purpose, a feature name) that would
// otherwise be right-aligned along with the figures.
function makeTable(headers, rows, widths, leftCols = []) {
  const alignOf = (i) => (i === 0 || leftCols.includes(i)
    ? AlignmentType.LEFT : AlignmentType.RIGHT);
  const totalWidth = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, {
          header: true, width: widths[i], align: alignOf(i),
        })),
      }),
      ...rows.map((r) => new TableRow({
        children: r.map((v, i) => cell(v, { width: widths[i], align: alignOf(i) })),
      })),
    ],
  });
}

// ---------- Derived table rows ----------

const gradeScorecardRows = portfolio.grade_scorecard.map((g) => [
  g.grade, num(g.n_loans), money(g.total_funded), g.wavg_int_rate.toFixed(2) + '%',
  pct(g.default_rate), pct(g.total_net_loss / g.total_funded),
]);

const gradePredActualRows = scoring.grade_predicted_vs_actual.map((g) => [
  g.grade, pct(g.predicted_pd), pct(g.actual_default_rate),
  ((g.predicted_pd - g.actual_default_rate) * 100).toFixed(1) + ' pp', num(g.count),
]);

const recoveryRows = portfolio.recovery_by_grade.map((g) => [
  g.grade, num(g.n_defaults), pct(g.recovery_rate), pct(g.implied_lgd),
]);

const vintageRows = portfolio.vintage_trend.map((v) => [
  String(v.issue_year), num(v.n_resolved), pct(v.default_rate),
]);

const decileRows = [...model.decile_table]
  .sort((a, b) => b.decile - a.decile)
  .map((d) => [
    String(d.decile), num(d.n), pct(d.avg_pd), pct(d.actual_default_rate),
    ((d.avg_pd - d.actual_default_rate) * 100).toFixed(1) + ' pp', d.lift.toFixed(2) + 'x',
  ]);

const featRows = model.top_features.slice(0, 12).map((f, i) => [
  String(i + 1), f.feature, f.importance.toFixed(4),
]);

const bandRows = scoring.risk_bands.map((b) => [
  b.band.replace(/^\d+ - /, ''), num(b.count), pct(b.count / scoring.n_scored),
  money(b.exposure), pct(b.avg_predicted_pd), pct(b.actual_default_rate), money(b.expected_loss),
]);

const watchlistRows = scoring.top20_highest_risk.slice(0, 15).map((w) => [
  String(w.id), w.sub_grade, money(w.loan_amnt), title(w.purpose), w.addr_state,
  pct(w.pd), w.actual_default ? 'Defaulted' : 'Repaid',
]);

const purposeRows = scoring.purpose_actual_rates.slice(0, 10).map((p) => [
  title(p.purpose), pct(p.default_rate), num(p.count),
]);

const stateRows = portfolio.top_states.slice(0, 8).map((s) => [
  s.state, num(s.n_loans), money(s.total_exposure), pct(s.default_rate),
]);

const modelCompareRows = [
  ['AUC-ROC', model.hgb_auc.toFixed(3), v1.auc.toFixed(3)],
  ['KS statistic', model.hgb_ks.toFixed(3), v1.ks.toFixed(3)],
  ['Brier score', model.hgb_brier.toFixed(3), v1.brier.toFixed(3)],
  ['Training loans', num(model.n_train), num(v1.n_train)],
  ['Test loans', num(model.n_test), num(v1.n_test)],
];

const lossVariance = scoring.expected_loss / scoring.actual_loss - 1;

const doc = new Document({
  styles: {
    default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      {
        id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 30, bold: true, color: NAVY, font: 'Calibri' },
        paragraph: {
          spacing: { before: 320, after: 160 },
          border: { bottom: { color: NAVY, style: BorderStyle.SINGLE, size: 6 } },
        },
      },
      {
        id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 25, bold: true, color: NAVY, font: 'Calibri' },
        paragraph: { spacing: { before: 240, after: 120 } },
      },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, bottom: 1080, left: 1260, right: 1260 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: 'Credit Risk Portfolio Report', size: 16, color: GRAY })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: 'Page ', size: 16, color: GRAY }),
            new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GRAY }),
            new TextRun({ text: ' of ', size: 16, color: GRAY }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 16, color: GRAY }),
          ],
        })],
      }),
    },
    children: [
      new Paragraph({ text: 'Credit Risk Portfolio Analysis', heading: HeadingLevel.TITLE, spacing: { after: 80 } }),
      new Paragraph({
        children: [new TextRun({
          text: 'PD Model v2 — Out-of-Time Validation, Loss Given Default and Underwriting Funnel',
          size: 26, color: GRAY, italics: true,
        })],
        spacing: { after: 40 },
      }),
      new Paragraph({
        children: [new TextRun({
          text: 'Prepared ' + new Date().toISOString().slice(0, 10) + '  |  Credit Risk project',
          size: 20, color: GRAY,
        })],
        spacing: { after: 400 },
      }),

      // ---------------------------------------------------------------- 1
      h1('1. Executive Summary'),
      body(`This report documents a probability-of-default model built on the full LendingClub loan history from 2007 to 2018 and validated out-of-time. The SQL warehouse behind it holds ${num(warehouse.raw_accepted_rows)} funded loans and ${num(warehouse.raw_rejected_rows)} declined applications; ${num(portfolio.n_resolved_loans)} of the funded loans have reached a final outcome and form the modelling population, of which ${pct(portfolio.overall_default_rate)} charged off.`),
      body(`The model was trained on ${num(model.n_train)} loans issued up to 2016 and tested on ${num(model.n_test)} loans issued in 2017 and 2018 — loans it never saw during training. On that unseen set it achieves an AUC of ${model.hgb_auc.toFixed(3)} and a KS statistic of ${model.hgb_ks.toFixed(3)}. Those figures are deliberately lower than the ${v1.auc.toFixed(3)} AUC reported by an earlier version of this model, which used a random split inside a single 2015 vintage. A random split lets loans originated weeks apart, under identical economic conditions and underwriting policy, sit on opposite sides of the split; it flatters the result. The out-of-time figures are the ones that describe how the model would behave in production.`),
      body(`Across the ${num(scoring.n_scored)} scored loans, carrying ${money(scoring.total_exposure)} of exposure, average predicted default probability is ${pct(scoring.avg_predicted_pd)} against an actual realised default rate of ${pct(scoring.actual_default_rate)}. Applying a ${pct(scoring.lgd_assumption, 0)} loss given default — measured from recovery data rather than assumed — gives an expected loss of ${money(scoring.expected_loss)} against ${money(scoring.actual_loss)} actually incurred, so the model under-predicted losses by ${pct(Math.abs(lossVariance))}.`),
      body(`Two findings carry beyond the model itself. First, recoveries on charged-off loans return only ${pct(portfolio.recovery_by_grade[0].recovery_rate)} to ${pct(portfolio.recovery_by_grade[5].recovery_rate)} of the outstanding balance, and that figure barely moves across risk grades — so loss given default sits near 90% portfolio-wide, not the 100% placeholder an earlier version of this analysis assumed. Second, the declined-application file supports an underwriting view the funded data cannot provide on its own, and analysing it surfaced a data quality defect severe enough to distort any model that used the field naively (Section 6).`),

      // ---------------------------------------------------------------- 2
      h1('2. Data and Methodology'),
      h2('2.1 Data sources'),
      bullet(`Funded loans: ${num(warehouse.raw_accepted_rows)} records, 2007–2018, loaded into a SQL warehouse with origination terms, borrower credit bureau attributes as at application, and full payment history.`),
      bullet(`Declined applications: ${num(warehouse.raw_rejected_rows)} records over the same period, carrying amount requested, debt-to-income, state, employment length and a risk score.`),
      bullet(`Modelling population: ${num(portfolio.n_resolved_loans)} funded loans with a resolved outcome. Loans still Current, Late or In Grace Period are excluded entirely — their final outcome is unknown, and treating them as non-defaults would bias the default rate downward.`),
      bullet(`Target: default = 1 for Charged Off or Default, 0 for Fully Paid. Overall rate ${pct(portfolio.overall_default_rate)}.`),

      h2('2.2 Leakage control'),
      body('Credit models are unusually prone to target leakage because the richest fields in a loan file describe what happened after origination. Every such field is excluded here: principal and interest received, recoveries, outstanding balance, last payment date and amount, updated FICO scores, and the hardship and debt-settlement flags. Only information available at the moment of approval is used as a feature. This matters for honesty as much as rigour — several published analyses of this dataset report AUCs above 0.90, which is attainable only by including fields that encode the answer.'),
      body(`A second, subtler form of leakage was also controlled for. LendingClub introduced a number of credit bureau fields partway through the data history, so for older vintages they are empty. ${model.n_dropped_for_missingness} features more than half empty across the training window were dropped, because retaining them would let the model learn "is this field populated" as a proxy for how recently a loan was issued.`),

      h2('2.3 Validation design'),
      body(`Training covers loans issued up to 2016 (${num(model.n_train)} loans, ${pct(model.train_default_rate)} default rate); testing covers 2017 and 2018 only (${num(model.n_test)} loans, ${pct(model.test_default_rate)}). This is the standard applied in regulated credit model validation, and it is strictly harder than a random split: the test period carries its own economic conditions and its own underwriting policy, neither of which the model saw.`),
      body(`${model.name} was selected over a logistic regression baseline, which reached an AUC of ${model.logreg_auc.toFixed(3)} on the same split. ${model.n_features} features were used after one-hot encoding.`),

      pageBreak(),

      // ---------------------------------------------------------------- 3
      h1('3. Portfolio Findings'),
      h2('3.1 Risk grading'),
      body('LendingClub assigns each loan a grade from A to G at origination. Observed outcomes confirm the grading is meaningful: the default rate rises monotonically across all seven grades, and the dollar loss rate rises faster still, because higher-grade loans are also larger and priced higher.'),
      makeTable(
        ['Grade', 'Loans', 'Funded', 'Wtd Avg Rate', 'Default Rate', 'Loss Rate'],
        gradeScorecardRows,
        [900, 1300, 1700, 1700, 1600, 1600],
      ),
      caption(`All ${num(portfolio.n_resolved_loans)} resolved loans. Loss rate is net dollar loss as a share of funded principal.`),

      h2('3.2 Loan purpose'),
      body('Purpose remains informative after grade is accounted for. Small business lending is the clear outlier on the riskier end, while car loans and credit card refinancing sit at the lower end.'),
      makeTable(['Purpose', 'Default Rate', 'Loans'], purposeRows, [3200, 1900, 1900]),
      caption('Out-of-time test set, purposes with at least 200 loans.'),

      h2('3.3 Recovery and loss given default'),
      body(`When a loan charges off, the lender recovers only a small fraction of the outstanding balance through collections — and strikingly, that fraction is almost independent of the borrower's risk grade. A grade G default returns about as little as a grade A default.`),
      makeTable(['Grade', 'Defaults', 'Recovery Rate', 'Implied LGD'], recoveryRows, [1200, 1800, 2000, 2000]),
      caption('Recovery rate is total recoveries divided by unpaid principal at charge-off.'),
      body(`This flatness is what justifies applying a single portfolio-wide loss given default of ${pct(scoring.lgd_assumption, 0)} in the expected-loss calculations throughout this report. An earlier version of this analysis used 100% as a deliberately conservative placeholder, before the recovery data had been examined.`),

      h2('3.4 Vintage trend'),
      body('Default rates move with the credit cycle. The 2008 and 2009 vintages carry elevated rates, conditions improve through 2010 to 2013, and rates climb again from 2014 onward as origination volume grew.'),
      makeTable(['Issue Year', 'Resolved Loans', 'Default Rate'], vintageRows, [1900, 2400, 2200]),

      h2('3.5 Geographic concentration'),
      body('Exposure concentration and risk concentration are not the same map. California, Texas and New York carry the largest balances, but New York defaults materially above California at comparable scale.'),
      makeTable(['State', 'Loans', 'Exposure', 'Default Rate'], stateRows, [1200, 1800, 2000, 2000]),

      pageBreak(),

      // ---------------------------------------------------------------- 4
      h1('4. Model Performance'),
      h2('4.1 Out-of-time versus random split'),
      body('The table below compares this model against the earlier version built on a random split within a single vintage. The newer model trains on seventeen times more data and still scores lower, which is the expected and correct result.'),
      makeTable(['Metric', 'v2 (out-of-time)', 'v1 (random split)'], modelCompareRows, [2400, 2300, 2300]),
      caption('Both generations used the same algorithm and the same leakage controls. Only the validation design differs.'),

      h2('4.2 Discrimination and calibration'),
      body('Ranking the test set by predicted probability and splitting it into ten equal groups shows both whether the model separates risk and whether its probabilities are honest. Predicted and actual rates track closely in every decile, which is calibration — a more demanding property than discrimination, and the one that matters when the output feeds a loss provision rather than just a ranking.'),
      makeTable(
        ['Decile', 'Loans', 'Predicted PD', 'Actual Rate', 'Gap', 'Lift'],
        decileRows,
        [1100, 1400, 1700, 1600, 1200, 1100],
      ),
      caption('Decile 10 is the highest predicted risk. Lift is the decile default rate relative to the portfolio average.'),

      h2('4.3 Feature importance'),
      body('Permutation importance, measured as the drop in AUC when a feature is randomly shuffled, identifies which inputs the model actually relies on.'),
      makeTable(['Rank', 'Feature', 'Importance'], featRows, [900, 3700, 1700], [1]),
      caption('Interest rate dominates because it encodes the lender\'s own risk assessment at origination — it is a legitimate origination-time field, but it means the model partly learns to reproduce an existing pricing decision.'),

      // ---------------------------------------------------------------- 5
      h1('5. Risk Segmentation and Expected Loss'),
      body(`Scored loans are grouped into six bands by predicted probability. The bands behave as intended: predicted and actual default rates rise together, and the two highest bands carry ${pct((scoring.risk_bands[4].count + scoring.risk_bands[5].count) / scoring.n_scored)} of the loans.`),
      makeTable(
        ['Risk Band', 'Loans', '% of Book', 'Exposure', 'Predicted PD', 'Actual Rate', 'Expected Loss'],
        bandRows,
        [1600, 1200, 1200, 1500, 1500, 1300, 1500],
      ),
      caption(`Expected loss is predicted PD × funded amount × ${pct(scoring.lgd_assumption, 0)} LGD, summed per loan.`),
      body(`Aggregate expected loss of ${money(scoring.expected_loss)} compares with ${money(scoring.actual_loss)} actually realised — an under-prediction of ${pct(Math.abs(lossVariance))}. For a provisioning application this direction of error matters more than its size: a model that systematically under-states losses produces reserves that are too thin, and would warrant a conservatism adjustment before use.`),

      h2('5.1 Watchlist'),
      body(`The fifteen highest-risk loans in the scored book are listed below, with what actually happened to each. Of the top twenty by predicted probability, ${scoring.top20_actual_defaults} went on to default.`),
      makeTable(
        ['Loan ID', 'Grade', 'Amount', 'Purpose', 'State', 'Predicted PD', 'Outcome'],
        watchlistRows,
        [1500, 900, 1200, 2000, 900, 1400, 1300],
        [3, 6],
      ),
      caption('Every loan here is from the out-of-time test set, so the outcome column is a genuine test of the ranking rather than a restatement of training data.'),

      pageBreak(),

      // ---------------------------------------------------------------- 6
      h1('6. Underwriting Funnel and Reject Inference'),
      body(`The funded loan file describes only applications that were approved, which means it cannot answer who gets declined or why. The ${num(warehouse.raw_rejected_rows)} declined applications close that gap. An acceptance model built on the fields common to both populations — amount requested, debt-to-income, application year and state — reaches an AUC of ${rj.headline_auc.toFixed(3)}, rising to ${rj.with_score_auc.toFixed(3)} when an approximate credit score is included, with the score the dominant coefficient. That ordering is consistent with how underwriting actually operates.`),
      h2('6.1 A data quality finding'),
      body(`An initial version of this model included employment length and scored an AUC of ${rj.emp_length_inflated_auc.toFixed(3)}, which was implausibly strong for four weak inputs. The cause was a defect in the data rather than a signal in it: employment length reads "less than one year" for ${pct(rj.emp_length_under_1yr_rejected, 0)} of declined applications against ${pct(rj.emp_length_under_1yr_accepted, 0)} of funded ones. That is a form default on applications declined before employment details are collected, not a real difference in borrower tenure. The field was excluded, and the lower figure is the one reported.`),
      body('This is worth recording as a methodological point rather than a footnote. A model that is unexpectedly accurate deserves suspicion before celebration, and the usual explanation is that a field encodes the outcome rather than predicting it.'),

      // ---------------------------------------------------------------- 7
      h1('7. Recommendations'),
      bullet(`Provision using the measured ${pct(scoring.lgd_assumption, 0)} loss given default rather than a flat assumption. Recoveries are consistently minimal and do not vary meaningfully by grade, so a single portfolio-wide figure is defensible and materially more accurate than a 100% placeholder.`),
      bullet('Apply a conservatism adjustment when using model output for provisioning, given the model under-predicts realised losses on unseen data.'),
      bullet('Validate out-of-time before any deployment decision. The gap between the two validation designs documented here is the difference between a model that looks deployable and one that is.'),
      bullet(`Review pricing on grades E through G, where default rates reach ${pct(portfolio.grade_scorecard[6].default_rate)} and loss rates exceed a third of funded principal.`),
      bullet('Monitor state-level risk separately from state-level exposure, since the two do not move together.'),
      bullet('Treat the declined-application file as an analytical asset for underwriting review, with attention to fields that carry form defaults rather than observed values.'),

      // ---------------------------------------------------------------- 8
      h1('8. Limitations and Assumptions'),
      bullet('Loss given default is measured at the point of charge-off. It does not discount recoveries received in later periods, and takes no account of the time value of money. A full LGD model would do both.'),
      bullet('The model contains no macroeconomic variables. It describes how default rates moved across vintages without explaining the credit cycle driving them, which limits its usefulness for forward-looking stress scenarios.'),
      bullet('The credit score used in the acceptance model compares the risk score recorded on declined applications against the FICO range recorded on funded ones. These are similar measures but are not confirmed to share a definition or a scale, so that model is indicative rather than precise.'),
      bullet('Interest rate is the strongest single predictor, which means the model partly reproduces the lender\'s own pricing decision rather than forming an independent view of risk.'),
      bullet('Full reject inference techniques, such as fuzzy augmentation or a Heckman-style correction, were not applied. The acceptance model stands alongside the PD model rather than feeding into it.'),
      bullet('Results describe a single lender\'s book over one eleven-year period, ending in 2018. Transfer to another portfolio or a later period should not be assumed.'),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = path.join(__dirname, 'credit_risk_report.docx');
  fs.writeFileSync(out, buf);
  console.log('Wrote ' + out);
});
