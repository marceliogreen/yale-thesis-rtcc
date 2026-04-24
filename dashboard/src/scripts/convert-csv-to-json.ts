/**
 * CSV -> JSON converter for thesis dashboard.
 * Run from dashboard/: npx tsx src/scripts/convert-csv-to-json.ts
 */
import * as fs from 'fs';
import * as path from 'path';

// Repo root is the parent of dashboard/
const REPO_ROOT = path.resolve(process.cwd(), '..');
console.log(`Repo root: ${REPO_ROOT}`);

function parseCSV(text: string): Record<string, string>[] {
  const lines = text.trim().split('\n');
  if (lines.length < 2) return [];
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, '').toLowerCase().replace(/\s+/g, '_'));
  return lines.slice(1).map(line => {
    const values = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''));
    const row: Record<string, string> = {};
    headers.forEach((h, i) => { row[h] = values[i] || ''; });
    return row;
  });
}

function autoType(rows: Record<string, string>[]): Record<string, unknown>[] {
  return rows.map(row => {
    const typed: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(row)) {
      if (val === '' || val === 'NA' || val === 'NaN' || val === 'None' || val === 'null') {
        typed[key] = null;
      } else if (val === 'True' || val === 'true') { typed[key] = true;
      } else if (val === 'False' || val === 'false') { typed[key] = false;
      } else if (!isNaN(Number(val)) && val !== '') { typed[key] = Number(val);
      } else { typed[key] = val; }
    }
    return typed;
  });
}

const RESULTS_S1 = path.join(REPO_ROOT, 'results/study1_rtcc');
const RESULTS_S1R = path.join(REPO_ROOT, 'results/study1_rtcc/rerun_verified_dates');
const RESULTS_S1ROB = path.join(REPO_ROOT, 'results/study1_rtcc/robustness');
const RESULTS_S2 = path.join(REPO_ROOT, 'results/study2_dfr/processed');
const THESIS_DATA = path.join(REPO_ROOT, 'thesis/data');
const DATA_DIR = path.join(process.cwd(), 'src/data');

for (const sub of ['study1', 'study2']) {
  fs.mkdirSync(path.join(DATA_DIR, sub), { recursive: true });
}

function convertCSV(csvPath: string, outName: string, outDir: string): void {
  if (!fs.existsSync(csvPath)) {
    console.log(`  SKIP: ${outName} (${csvPath} not found)`);
    return;
  }
  const text = fs.readFileSync(csvPath, 'utf-8');
  const rows = parseCSV(text);
  const typed = autoType(rows);
  fs.writeFileSync(path.join(outDir, outName), JSON.stringify(typed, null, 2));
  console.log(`  OK: ${outName} (${typed.length} rows)`);
}

console.log('\nStudy 1:');
const s1 = path.join(DATA_DIR, 'study1');
convertCSV(path.join(RESULTS_S1, 'annual_clearance_rates.csv'), 'clearance_rates.json', s1);
convertCSV(path.join(RESULTS_S1, 'pre_post_rtcc_summary.csv'), 'pre_post_summary.json', s1);
convertCSV(path.join(RESULTS_S1, 'psm_did_results.csv'), 'psm_did_results.json', s1);
convertCSV(path.join(RESULTS_S1ROB, 'robustness_6_extended_its.csv'), 'extended_its.json', s1);
convertCSV(path.join(RESULTS_S1ROB, 'robustness_7_ml_pipeline.csv'), 'ml_pipeline.json', s1);
convertCSV(path.join(RESULTS_S1ROB, 'robustness_7_xgboost_importance.csv'), 'shap_importance.json', s1);
convertCSV(path.join(RESULTS_S1ROB, 'robustness_8_9_10.csv'), 'robustness_specs.json', s1);
convertCSV(path.join(RESULTS_S1ROB, 'sensitivity_results.csv'), 'sensitivity_results.json', s1);
convertCSV(path.join(RESULTS_S1ROB, 'event_study_results.csv'), 'event_study_results.json', s1);
convertCSV(path.join(RESULTS_S1ROB, 'matching_balance.json'), 'matching_balance.json', s1);
convertCSV(path.join(RESULTS_S1R, 'event_study_coefficients.csv'), 'event_study_coefficients.json', s1);
convertCSV(path.join(THESIS_DATA, 'rtcc_dates_verified.csv'), 'verified_dates.json', s1);

console.log('\nStudy 2:');
const s2 = path.join(DATA_DIR, 'study2');
convertCSV(path.join(RESULTS_S2, 'dfr_cross_program_comparison.csv'), 'dfr_cross_program.json', s2);
convertCSV(path.join(RESULTS_S2, 'dfr_response_time_analysis.csv'), 'dfr_response_times.json', s2);
convertCSV(path.join(RESULTS_S2, 'cross_city_cog_sci_comparison.csv'), 'cog_sci_comparison.json', s2);
convertCSV(path.join(RESULTS_S2, 'cog_sci_benchmark_mapping.csv'), 'benchmark_mapping.json', s2);

console.log('\nDone.');
