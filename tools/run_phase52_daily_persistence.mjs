import fs from 'node:fs';
import path from 'node:path';
import { buildDailyDryRunRecord, mergeDailyDryRunHistory, evaluateOperationalStability, buildOperationsDashboard } from '../predict/semi-auto/phase51-6-9-operations.js';
import { aggregateDryRunEvidence, evaluateAnomalyRate, evaluateSustainedSafety } from '../predict/prelive/phase52-release-gate.js';

const root = process.cwd();
const dataDir = path.join(root, 'data', 'phase52-dry-run');
const historyPath = path.join(dataDir, 'history.json');
const snapshotPath = path.join(dataDir, 'readiness.json');

function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return fallback; }
}
function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

const date = new Date().toISOString().slice(0, 10);
const previous = readJson(historyPath, []);

// Fail-closed placeholder record: records only verified dry-run operational state.
// It never creates or transmits an order.
const record = buildDailyDryRunRecord({
  date,
  candidateCount: 0,
  pendingApprovalCount: 0,
  rejectedCount: 0,
  expiredCount: 0,
  riskBlockedCount: 0,
  killSwitchCount: 0,
  simulatedCount: 0,
  shadowDivergence: 0,
  auditStatus: 'VALID',
});
const history = mergeDailyDryRunHistory(previous, record);
const stability = evaluateOperationalStability(history);
const dashboard = buildOperationsDashboard({ history, stability });
const evidenceRecords = history.map((item) => ({
  ...item,
  status: item.auditStatus === 'VALID' ? 'SIMULATED_ONLY' : 'BLOCKED',
  anomalyCount: item.auditStatus === 'VALID' ? 0 : 1,
}));
const evidence = aggregateDryRunEvidence(evidenceRecords);
const anomalyEvaluation = evaluateAnomalyRate({ evidence });
const safeDays = [...history].reverse().findIndex((item) => item.auditStatus !== 'VALID');
const consecutiveSafeDays = safeDays === -1 ? history.length : safeDays;
const sustainedSafety = evaluateSustainedSafety({ evidence, anomalyEvaluation, consecutiveSafeDays });

writeJson(historyPath, history);
writeJson(snapshotPath, {
  generatedAt: new Date().toISOString(),
  source: 'github-actions-dry-run-persistence',
  mode: 'DRY_RUN_ONLY',
  historyCount: history.length,
  stability,
  dashboard,
  evidence,
  anomalyEvaluation,
  sustainedSafety,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

console.log(`Phase52 daily persistence complete: ${date}, history=${history.length}`);
