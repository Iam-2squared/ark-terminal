import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { P23_5_PRESET_CONFIGS } from './phase57-nested-trade-management-selection.js';
import { simulateTradeManagementStateMachine } from './phase57-trade-management-state-machine.js';
import {
  P23_8D_FROZEN_RATCHET_CONFIG,
  PHASE57_P23_8D_SAFETY,
  simulateFrozenRatchetExit,
  summarizeFrozenRatchetOutcomes,
} from './phase57-frozen-ratchet-exit.js';

const SHARD_INDEX = Number(process.env.PHASE57_SHARD_INDEX ?? 0);
if (!Number.isInteger(SHARD_INDEX) || SHARD_INDEX < 0 || SHARD_INDEX > 2) throw new Error('PHASE57_SHARD_INDEX must be 0, 1, or 2');
const SHARD_NUMBER = SHARD_INDEX + 1;
const here = path.dirname(fileURLToPath(import.meta.url));
const frozenMeta = JSON.parse(fs.readFileSync(path.join(here, 'phase57-p23-8-frozen-outer-trades.json'), 'utf8'));
const shardMeta = frozenMeta.shards.find(item => Number(item.matrixIndex) === SHARD_INDEX);
if (!shardMeta) throw new Error(`missing frozen shard metadata for index ${SHARD_INDEX}`);
if (frozenMeta.sourceWorkflowRunId !== 31379583578) throw new Error('unexpected frozen source workflow run');
if (frozenMeta.entrySelectionFrozen !== true || frozenMeta.frozenBeforeP23_8dExitMeasurement !== true) {
  throw new Error('P23.8D requires a pre-frozen entry source');
}

const sourceRoot = path.resolve(process.env.PHASE57_FROZEN_ARTIFACT_DIR || 'frozen-source');
function findJson(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? findJson(full) : (entry.name.endsWith('.json') ? [full] : []);
  });
}
const sourceFiles = findJson(sourceRoot);
if (sourceFiles.length !== 1) throw new Error(`expected exactly one frozen source JSON, found ${sourceFiles.length}`);
const source = JSON.parse(fs.readFileSync(sourceFiles[0], 'utf8'));
if (source.phase !== `57.p23.8-entry-exit-quality-shard-${SHARD_NUMBER}`) {
  throw new Error(`unexpected source phase: ${source.phase}`);
}
if (Number(source.qualityShardPolicy?.shardIndex) !== SHARD_INDEX) throw new Error('source shard index mismatch');
if (source.qualityShardPolicy?.entryThresholdsChanged !== false) throw new Error('frozen source entry thresholds were not stable');
if (source.qualityShardPolicy?.futureExtremaUsedForDecision !== false) throw new Error('frozen source has future-extrema decision contamination');
const frozenRecords = source.entryExitQuality?.records ?? [];
if (frozenRecords.length !== Number(shardMeta.tradeCount)) {
  throw new Error(`frozen trade count mismatch: records=${frozenRecords.length} expected=${shardMeta.tradeCount}`);
}

const safetyKeys = [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
];
for (const key of safetyKeys) {
  if (source[key] !== false) throw new Error(`frozen source safety ${key} must be false`);
  if (PHASE57_P23_8D_SAFETY[key] !== false) throw new Error(`P23.8D safety ${key} must be false`);
}

const candidateMap = new Map(P23_5_PRESET_CONFIGS.map(candidate => [candidate.id, candidate.config]));
for (const record of frozenRecords) {
  if (!candidateMap.has(record.candidateId)) throw new Error(`unknown frozen candidate: ${record.candidateId}`);
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
function jst(ts) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(ts));
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return { date: `${values.year}-${values.month}-${values.day}`, hm: `${values.hour}:${values.minute}` };
}

async function fetchJson(urls, symbol) {
  let lastError;
  for (const url of urls) {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 30000);
        const response = await fetch(url, {
          headers: {
            'User-Agent': 'Mozilla/5.0 ArkTerminalResearch/1.0',
            Accept: 'application/json',
            Connection: 'close',
          },
          signal: controller.signal,
        });
        clearTimeout(timer);
        if (!response.ok) throw new Error(`${symbol} Yahoo HTTP ${response.status}`);
        return await response.json();
      } catch (error) {
        lastError = error;
        if (attempt < 4) await sleep(attempt * 1000);
      }
    }
  }
  throw lastError;
}

function parse(json, symbol) {
  const result = json?.chart?.result?.[0];
  if (!result) throw new Error(`${symbol} no chart result`);
  const quote = result.indicators?.quote?.[0] || {};
  const rows = [];
  for (let index = 0; index < (result.timestamp || []).length; index += 1) {
    const timestamp = Number(result.timestamp[index]) * 1000;
    const { date, hm } = jst(timestamp);
    if (hm < '09:00' || hm > '15:30') continue;
    const values = [quote.open?.[index], quote.high?.[index], quote.low?.[index], quote.close?.[index]];
    if (values.some(value => value == null || !Number.isFinite(Number(value)))) continue;
    rows.push({
      timestamp: new Date(timestamp).toISOString(),
      open: Number(quote.open[index]),
      high: Number(quote.high[index]),
      low: Number(quote.low[index]),
      close: Number(quote.close[index]),
      volume: Number(quote.volume?.[index] || 0),
      sessionDate: date,
    });
  }
  return rows;
}

async function fetchBars(symbol) {
  const end = Math.floor(Date.now() / 1000);
  const day = 86400;
  const windows = [[end - 58 * day, end - 29 * day], [end - 29 * day, end]];
  const all = [];
  for (const [period1, period2] of windows) {
    const query = `period1=${period1}&period2=${period2}&interval=5m&includePrePost=false&events=div%2Csplits`;
    const urls = [1, 2].map(host => `https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?${query}`);
    all.push(...parse(await fetchJson(urls, symbol), symbol));
    await sleep(500);
  }
  return [...new Map(all.map(bar => [bar.timestamp, bar])).values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

const symbols = [...new Set(frozenRecords.map(record => String(record.symbol)))].sort();
const fetchedPairs = [];
for (let start = 0; start < symbols.length; start += 5) {
  const batch = symbols.slice(start, start + 5);
  fetchedPairs.push(...await Promise.all(batch.map(async symbol => [symbol, await fetchBars(symbol)])));
  if (start + 5 < symbols.length) await sleep(1000);
}
const fetchedBySymbol = new Map(fetchedPairs);
const sessions = new Map();
for (const [symbol, bars] of fetchedBySymbol) {
  for (const bar of bars) {
    const key = `${symbol}|${bar.sessionDate}`;
    if (!sessions.has(key)) sessions.set(key, []);
    sessions.get(key).push(bar);
  }
}
for (const rows of sessions.values()) rows.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

function approx(a, b, tolerance = 1e-8) {
  return Number.isFinite(Number(a)) && Number.isFinite(Number(b)) && Math.abs(Number(a) - Number(b)) <= tolerance;
}
function summarize(rows = []) {
  const n = rows.length;
  const positive = rows.filter(row => Number(row.netReturnPct) > 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  const negative = -rows.filter(row => Number(row.netReturnPct) < 0).reduce((sum, row) => sum + Number(row.netReturnPct), 0);
  const avg = key => n ? rows.reduce((sum, row) => sum + Number(row[key]), 0) / n : null;
  return {
    signalCount: n,
    hitRate: n ? rows.filter(row => Number(row.netReturnPct) > 0).length / n : null,
    netAverageReturnPct: avg('netReturnPct'),
    grossAverageReturnPct: avg('grossReturnPct'),
    profitFactor: negative > 0 ? positive / negative : (positive > 0 ? Infinity : null),
    averageHoldingBars: avg('barsHeld'),
  };
}

const baselineReplay = [];
const ratchetOutcomes = [];
const paired = [];
const reconciliationErrors = [];
for (const record of frozenRecords) {
  const sessionBars = sessions.get(`${record.symbol}|${record.sessionDate}`) ?? [];
  const cutoff = new Date(record.featureCutoff).toISOString();
  const index = sessionBars.findIndex(bar => new Date(bar.timestamp).toISOString() === cutoff);
  if (index < 0 || index >= sessionBars.length - 1) {
    reconciliationErrors.push({ symbol: record.symbol, sessionDate: record.sessionDate, featureCutoff: cutoff, reason: 'MISSING_FROZEN_PATH' });
    continue;
  }
  const row = {
    symbol: String(record.symbol),
    sessionDate: String(record.sessionDate),
    featureCutoff: cutoff,
    entryPrice: Number(record.entryPrice),
    signalDirection: record.direction,
    frozenEntry: true,
    contextBars: sessionBars.slice(0, index + 1),
    futureBars: sessionBars.slice(index + 1),
  };
  const baseline = simulateTradeManagementStateMachine(row, { config: candidateMap.get(record.candidateId) });
  if (!baseline) {
    reconciliationErrors.push({ symbol: record.symbol, sessionDate: record.sessionDate, featureCutoff: cutoff, reason: 'BASELINE_REPLAY_NULL' });
    continue;
  }
  const mismatches = [];
  if (!approx(baseline.entryPrice, record.entryPrice)) mismatches.push('entryPrice');
  if (!approx(baseline.exitPrice, record.exitPrice)) mismatches.push('exitPrice');
  if (!approx(baseline.netReturnPct, record.netReturnPct)) mismatches.push('netReturnPct');
  if (Number(baseline.barsHeld) !== Number(record.barsHeld)) mismatches.push('barsHeld');
  if (String(baseline.exitReason) !== String(record.exitReason)) mismatches.push('exitReason');
  if (mismatches.length) {
    reconciliationErrors.push({
      symbol: record.symbol,
      sessionDate: record.sessionDate,
      featureCutoff: cutoff,
      candidateId: record.candidateId,
      mismatches,
      frozen: { exitPrice: record.exitPrice, netReturnPct: record.netReturnPct, barsHeld: record.barsHeld, exitReason: record.exitReason },
      replay: { exitPrice: baseline.exitPrice, netReturnPct: baseline.netReturnPct, barsHeld: baseline.barsHeld, exitReason: baseline.exitReason },
    });
    continue;
  }

  const ratchet = simulateFrozenRatchetExit(row);
  if (!ratchet) throw new Error(`ratchet exit returned null for ${record.symbol} ${cutoff}`);
  if (ratchet.ratchetNeverLoosened !== true) throw new Error(`ratchet loosened for ${record.symbol} ${cutoff}`);
  baselineReplay.push({
    symbol: record.symbol,
    sessionDate: record.sessionDate,
    featureCutoff: cutoff,
    candidateId: record.candidateId,
    netReturnPct: baseline.netReturnPct,
    grossReturnPct: baseline.grossReturnPct,
    barsHeld: baseline.barsHeld,
    exitReason: baseline.exitReason,
    exitPrice: baseline.exitPrice,
  });
  ratchetOutcomes.push(ratchet);
  paired.push({
    symbol: record.symbol,
    sessionDate: record.sessionDate,
    featureCutoff: cutoff,
    direction: record.direction,
    entryPrice: record.entryPrice,
    frozenCandidateId: record.candidateId,
    baseline: {
      netReturnPct: baseline.netReturnPct,
      grossReturnPct: baseline.grossReturnPct,
      barsHeld: baseline.barsHeld,
      exitReason: baseline.exitReason,
      exitPrice: baseline.exitPrice,
    },
    ratchet: {
      netReturnPct: ratchet.netReturnPct,
      grossReturnPct: ratchet.grossReturnPct,
      barsHeld: ratchet.barsHeld,
      exitReason: ratchet.exitReason,
      exitPrice: ratchet.exitPrice,
      mfePct: ratchet.mfePct,
      maePct: ratchet.maePct,
      profitGivebackPctPoints: ratchet.profitGivebackPctPoints,
      captureRatio: ratchet.captureRatio,
      ratchetActivated: ratchet.ratchetActivated,
      ratchetNeverLoosened: ratchet.ratchetNeverLoosened,
    },
    deltaNetReturnPct: ratchet.netReturnPct - baseline.netReturnPct,
    outerOutcomeUsedForConfigSelection: false,
  });
}

// Fail closed before comparing V3 if the frozen P23.8 baseline cannot be reconstructed exactly.
if (reconciliationErrors.length) {
  const failurePath = path.resolve(`artifacts/phase57-p23-8d-reconciliation-failure-shard-${SHARD_NUMBER}.json`);
  fs.mkdirSync(path.dirname(failurePath), { recursive: true });
  fs.writeFileSync(failurePath, JSON.stringify({
    phase: `57.p23.8d-frozen-exit-shard-${SHARD_NUMBER}`,
    status: 'FROZEN_BASELINE_RECONCILIATION_FAILED',
    shardIndex: SHARD_INDEX,
    expectedTradeCount: frozenRecords.length,
    reconciledTradeCount: baselineReplay.length,
    reconciliationErrors,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    overnightHoldingAllowed: false,
    transmitted: false,
  }, null, 2));
  throw new Error(`P23.8D frozen baseline reconciliation failed for ${reconciliationErrors.length} trades`);
}
if (baselineReplay.length !== frozenRecords.length || ratchetOutcomes.length !== frozenRecords.length) {
  throw new Error('P23.8D frozen trade count changed');
}

const baselineSummary = summarize(baselineReplay);
const ratchetSummary = summarizeFrozenRatchetOutcomes(ratchetOutcomes);
if (!approx(baselineSummary.netAverageReturnPct, shardMeta.baselineNetAverageReturnPct, 1e-10)) throw new Error('frozen baseline Net does not match pre-registered metadata');
if (!approx(baselineSummary.profitFactor, shardMeta.baselineProfitFactor, 1e-10)) throw new Error('frozen baseline PF does not match pre-registered metadata');
if (!approx(baselineSummary.hitRate, shardMeta.baselineHitRate, 1e-12)) throw new Error('frozen baseline hit rate does not match pre-registered metadata');

const result = {
  phase: `57.p23.8d-frozen-exit-shard-${SHARD_NUMBER}`,
  status: 'FROZEN_ENTRY_EXIT_ISOLATION_DEVELOPMENT_MEASURED',
  shardIndex: SHARD_INDEX,
  shardNumber: SHARD_NUMBER,
  frozenSource: {
    workflowRunId: frozenMeta.sourceWorkflowRunId,
    sourceHeadSha: frozenMeta.sourceHeadSha,
    artifactName: shardMeta.sourceArtifactName,
    artifactId: shardMeta.sourceArtifactId,
    artifactDigest: shardMeta.sourceArtifactDigest,
    expectedTradeCount: shardMeta.tradeCount,
    exactTradeCountReconciled: true,
    baselineReplayExact: true,
  },
  symbols,
  entryPolicy: {
    frozen: true,
    changedForP23_8D: false,
    frozenFields: ['symbol','sessionDate','featureCutoff','direction','entryPrice','candidateId'],
    outerOutcomeMayChangeEntry: false,
  },
  exitPolicy: {
    configId: P23_8D_FROZEN_RATCHET_CONFIG.configId,
    onePreRegisteredV3ConfigOnly: true,
    configSelectedFromOuterOutcomes: false,
    monotonicRatchet: true,
    profitableStructureIntactSoftExitSuppression: true,
    futureExtremaUsedForDecision: false,
  },
  baselineSummary,
  ratchetSummary,
  deltas: {
    netAverageReturnPct: ratchetSummary.netAverageReturnPct - baselineSummary.netAverageReturnPct,
    profitFactor: ratchetSummary.profitFactor == null || baselineSummary.profitFactor == null ? null : ratchetSummary.profitFactor - baselineSummary.profitFactor,
    hitRate: ratchetSummary.hitRate - baselineSummary.hitRate,
    averageHoldingBars: ratchetSummary.averageHoldingBars - baselineSummary.averageHoldingBars,
  },
  paired,
  interpretation: {
    developmentOnly: true,
    reusedP23_8DevelopmentWindow: true,
    finalUntouchedOosEdgeClaimAllowed: false,
    improvementIfAnyIsMethodDevelopmentEvidenceOnly: true,
    frozenEntryMakesExitComparisonAppleToApple: true,
    futureExtremaUsedForConfigSelection: false,
  },
  edgeClaimAllowed: false,
  recommendationAllowed: false,
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  overnightHoldingAllowed: false,
  transmitted: false,
  safety: PHASE57_P23_8D_SAFETY,
};

const outputPath = path.resolve(`artifacts/phase57-p23-8d-frozen-exit-shard-${SHARD_NUMBER}.json`);
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
console.log(`PHASE57_P23_8D_DONE shard=${SHARD_NUMBER}/3 trades=${paired.length} baselineNet=${baselineSummary.netAverageReturnPct} ratchetNet=${ratchetSummary.netAverageReturnPct} delta=${result.deltas.netAverageReturnPct}`);
