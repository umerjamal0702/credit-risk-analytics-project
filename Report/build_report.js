const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, BorderStyle, PageBreak, Header, Footer,
  PageNumber, NumberFormat, LevelFormat, convertInchesToTwip
} = require('docx');

const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'report_data.json'), 'utf8'));
const eda = data.eda;
const model = data.model;
const scoring = data.scoring;

const NAVY = '1F4E78';
const LIGHT_BLUE = 'DCE6F1';
const GRAY = '666666';
const RED = 'C0392B';

const pct = (v, d = 1) => (v * 100).toFixed(d) + '%';
const money = (v, d = 1) => {
  v = Number(v);
  if (Math.abs(v) >= 1e6) return '$' + (v / 1e6).toFixed(d) + 'M';
  if (Math.abs(v) >= 1e3) return '$' + (v / 1e3).toFixed(d) + 'K';
  return '$' + v.toFixed(0);
};
const num = (v) => Number(v).toLocaleString();

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

function makeTable(headers, rows, widths) {
  const totalWidth = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, { header: true, width: widths[i], align: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT })),
      }),
      ...rows.map((r) => new TableRow({
        children: r.map((v, i) => cell(v, { width: widths[i], align: i === 0 ? AlignmentType.LEFT : AlignmentType.RIGHT })),
      })),
    ],
  });
}

// ---------- Build content ----------

const gradeRows = ['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((g) => {
  const h = eda.default_rate_by_grade[g] || { rate: 0, count: 0 };
  return [g, pct(h.rate), num(h.count)];
});

const purposeRows = Object.entries(eda.default_rate_by_purpose)
  .sort((a, b) => b[1].rate - a[1].rate)
  .map(([k, v]) => [k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()), pct(v.rate), num(v.count)]);

const decileRows = [...model.test_decile_table]
  .sort((a, b) => b.decile - a.decile)
  .map((d) => [String(d.decile + 1), num(d.n), num(d.defaults), pct(d.avg_pd), pct(d.default_rate)]);

const featRows = Object.entries(model.hgb_top_features).slice(0, 12).map(([k, v], i) => [String(i + 1), k, v.toFixed(4)]);

const bandRows = scoring.risk_band_counts && Object.entries(scoring.risk_band_counts)
  .sort((a, b) => a[0].localeCompare(b[0]))
  .map(([band, count]) => [
    band.split(' - ')[1],
    num(count),
    pct(count / scoring.n_scored),
    money(scoring.risk_band_exposure[band] || 0),
  ]);

const watchlistRows = scoring.top20_highest_risk.slice(0, 15).map((w) => [
  String(w.id), w.grade + '' + (w.sub_grade ? w.sub_grade.slice(-1) : ''), money(w.loan_amnt), w.purpose.replace(/_/g, ' '), pct(w.pd),
]);

const doc = new Document({
  styles: {
    default: {
      document: { run: { font: 'Calibri', size: 22 } },
    },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 30, bold: true, color: NAVY, font: 'Calibri' },
        paragraph: { spacing: { before: 320, after: 160 }, border: { bottom: { color: NAVY, style: BorderStyle.SINGLE, size: 6 } } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 25, bold: true, color: NAVY, font: 'Calibri' },
        paragraph: { spacing: { before: 240, after: 120 } } },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 }, // US Letter
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
      // Title block
      new Paragraph({ text: 'Credit Risk Portfolio Analysis', heading: HeadingLevel.TITLE, spacing: { after: 80 } }),
      new Paragraph({
        children: [new TextRun({ text: 'PD Model Development, Validation & Active Loan Book Scoring', size: 26, color: GRAY, italics: true })],
        spacing: { after: 40 },
      }),
      new Paragraph({
        children: [new TextRun({ text: 'Prepared ' + new Date().toISOString().slice(0, 10) + '  |  Credit Risk project', size: 20, color: GRAY })],
        spacing: { after: 400 },
      }),

      h1('1. Executive Summary'),
      body(`This report documents a probability-of-default (PD) model built on a LendingClub-style loan portfolio and applies it to score the currently active loan book. The training population consists of ${num(eda.n_loans)} completed loans (issued 2015) with a known outcome — ${pct(eda.overall_default_rate)} charged off overall. A gradient boosting model (${model.final_model}) was trained on origination-time features only and validated on a 25% held-out test set, achieving an AUC-ROC of ${model.hgb_auc.toFixed(3)} and a KS statistic of ${model.hgb_ks.toFixed(3)} — strong separation between loans that went on to default and those that were repaid.`),
      body(`Applying the model to the ${num(scoring.n_scored)} loans currently outstanding (status "Current") produces a portfolio-level average PD of ${pct(scoring.avg_pd)} against total exposure of ${money(scoring.total_exposure, 1)}. Under a conservative assumption of 100% loss given default (no recovery data is available in this dataset), the resulting expected-loss upper bound is ${money(scoring.total_expected_loss_upper_bound, 1)}. The active book's average PD is materially higher than the ${pct(eda.overall_default_rate)} historical base rate; this is a portfolio-composition effect, not a model calibration problem — the current book is more heavily weighted toward higher-risk grades (C/D/E) than the training population (see Section 5).`),
      body('Three deliverables accompany this report: an Excel workbook with the full scored loan book, live pivot-style summary tables and charts; an interactive web dashboard for ongoing monitoring; and this document, covering methodology, findings, and recommendations.'),

      h1('2. Data & Methodology'),
      h2('2.1 Data sources'),
      bullet(`Training set: ${num(eda.n_loans)} completed loans (loan_status = Fully Paid or Charged Off), issued in 2015. Target variable: default = 1 if Charged Off, else 0.`),
      bullet(`Scoring set: ${num(scoring.n_scored)} currently active loans (loan_status = Current) to be scored for risk.`),
      bullet('Both files were pre-cleaned (no missing values): a co-borrower field block was dropped, employment length and credit history were converted to numeric features, and remaining nulls were imputed using column-appropriate rules (median, zero, or -1 sentinel depending on field semantics).'),
      h2('2.2 Leakage control'),
      body('A PD model must only use information available at the time of loan origination — using fields that are only observed later (during or after the loan\'s life) inflates validation metrics but is not usable in production. The following fields were identified as post-origination and excluded from the feature set:'),
      bullet('total_rec_prncp, total_rec_int, total_rec_late_fee — payments received over the life of the loan.'),
      bullet('last_fico_range_high / last_fico_range_low — the borrower\'s most recently reported FICO score, updated periodically as the loan matures.'),
      body('The remaining ~191 features (after one-hot encoding categoricals) are all known at, or derivable from, the loan application: loan terms (amount, rate, term, installment), credit bureau attributes (FICO at origination, DTI, revolving utilization, trade line counts and ages, delinquency history), and categorical fields (grade, sub-grade, purpose, home ownership, state, verification status, application type).'),
      h2('2.3 Model & validation'),
      body(`Two models were trained and compared: a logistic regression baseline (AUC ${model.logreg_auc.toFixed(3)}) and a HistGradientBoostingClassifier (AUC ${model.hgb_auc.toFixed(3)}). The gradient boosting model was selected as it outperformed the baseline while remaining well-calibrated (Brier score ${model.hgb_brier.toFixed(3)}). All metrics are reported on a stratified 25% held-out test set (${num(21973)} loans) not used in training.`),

      h1('3. Exploratory Findings'),
      body('Default rates vary sharply and monotonically with LendingClub\'s own assigned grade, confirming that grade — and the interest rate it drives — already captures most of the risk signal available at origination:'),
      makeTable(
        ['Grade', 'Historical default rate', 'Loan count'],
        gradeRows,
        [2000, 3600, 3000]
      ),
      caption('Table 1. Actual charge-off rate by grade, training set.'),
      body('By loan purpose, small business and house loans carry the highest historical default rates, while car loans and credit-card consolidation carry the lowest:'),
      makeTable(
        ['Purpose', 'Default rate', 'Loan count'],
        purposeRows,
        [3200, 2400, 3000]
      ),
      caption('Table 2. Actual charge-off rate by loan purpose, training set.'),
      body(`60-month loans default far more often than 36-month loans (${pct(eda.default_rate_by_term[' 60 months'].rate)} vs ${pct(eda.default_rate_by_term[' 36 months'].rate)}), and interest rate is the single strongest numeric correlate of default (r = ${eda.correlation_with_default.int_rate.toFixed(2)}), followed by FICO (r = ${eda.correlation_with_default.fico_range_low.toFixed(2)}) and DTI (r = ${eda.correlation_with_default.dti.toFixed(2)}).`),

      h1('4. PD Model Performance'),
      h2('4.1 Discrimination (decile / lift table)'),
      body('Sorting the test set into ten equal-sized groups by predicted PD shows the model cleanly separates risk: the highest-risk decile has an actual default rate of ' + pct([...model.test_decile_table].sort((a,b)=>b.decile-a.decile)[0].default_rate) + ', roughly 17x the lowest-risk decile\'s ' + pct([...model.test_decile_table].sort((a,b)=>a.decile-b.decile)[0].default_rate) + '.'),
      makeTable(
        ['Decile (10=highest risk)', 'Loans', 'Actual defaults', 'Avg predicted PD', 'Actual default rate'],
        decileRows,
        [2600, 1800, 2000, 2200, 2200]
      ),
      caption('Table 3. Decile lift table, held-out test set.'),
      h2('4.2 Feature importance'),
      body('Permutation importance (drop in test AUC when a feature is shuffled) confirms interest rate — itself LendingClub\'s own risk pricing — dominates, followed by loan term and a handful of credit-utilization and account-activity features:'),
      makeTable(['Rank', 'Feature', 'Importance (ΔAUC)'], featRows, [1200, 4600, 2200]),
      caption('Table 4. Top permutation-importance features, HistGradientBoostingClassifier.'),

      h1('5. Current Portfolio Risk Assessment'),
      body(`The PD model was applied to all ${num(scoring.n_scored)} currently active loans. Risk bands were defined judgmentally on predicted PD to roughly track historical grade-level default rates:`),
      bandRows ? makeTable(['Risk band', 'Loan count', '% of book', 'Exposure'], bandRows, [2600, 2000, 1800, 2600]) : new Paragraph(''),
      caption('Table 5. Active loan book by risk band.'),
      body(`${money(scoring.risk_band_exposure['5 - High'] || 0)} + ${money(scoring.risk_band_exposure['6 - Very High'] || 0)} of exposure sits in the two highest risk bands combined. Cross-tabulating against LendingClub's own grade shows the model recovers the expected ordering (grade A/B loans cluster in Low/Low-Medium bands; F/G loans cluster in High/Very High), which is a useful sanity check on the model rather than a new finding.`),
      body('Table 6 lists the 15 highest-risk active loans by predicted PD — the recommended starting point for portfolio review or early-intervention outreach.'),
      makeTable(['Loan ID', 'Grade', 'Amount', 'Purpose', 'Predicted PD'], watchlistRows, [1800, 1400, 1800, 2600, 1800]),
      caption('Table 6. Top 15 highest-risk active loans. Full list of 20 in the accompanying Excel workbook and dashboard.'),

      h1('6. Recommendations'),
      bullet('Prioritize review of the ' + num(scoring.risk_band_counts['6 - Very High'] || 0) + ' "Very High" risk-band loans (' + money(scoring.risk_band_exposure['6 - Very High'] || 0) + ' exposure) for early intervention — proactive outreach, restructuring, or provisioning.'),
      bullet('Treat the elevated portfolio-average PD (' + pct(scoring.avg_pd) + ' vs ' + pct(eda.overall_default_rate) + ' historical base rate) as a composition signal: recent originations skew toward C/D/E grades, so overall portfolio provisioning should be reviewed against this shift rather than assumed to track historical averages.'),
      bullet('Because expected loss here assumes 100% loss given default, treat the ' + money(scoring.total_expected_loss_upper_bound, 1) + ' figure as an upper bound. Incorporating actual recovery/collateral data (not present in this dataset) would materially reduce it and should be a near-term follow-up.'),
      bullet('Revisit risk-band thresholds periodically against realized outcomes as active loans season and resolve, rather than treating the current PD-to-band mapping as fixed.'),

      h1('7. Limitations & Assumptions'),
      bullet('Training data covers loans issued in a single year (2015); the model has not been validated against other vintages or macroeconomic regimes, so its accuracy under different economic conditions is unknown.'),
      bullet('Expected loss uses LGD = 100% in the absence of recovery data — a deliberately conservative upper bound, not a calibrated loss estimate.'),
      bullet('Risk-band cut points (Section 5) were set judgmentally, not derived from a formal loss-optimization exercise.'),
      bullet('The model has not been assessed for disparate impact across protected classes; before any operational or pricing use, a fair-lending review is recommended.'),
      bullet('This analysis is for internal portfolio-monitoring purposes and does not constitute investment, credit, or legal advice.'),
    ],
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(path.join(__dirname, 'credit_risk_report.docx'), buf);
  console.log('wrote docx, bytes:', buf.length);
});
