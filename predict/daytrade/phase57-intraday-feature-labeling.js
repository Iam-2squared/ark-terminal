import { buildIntradayReadonlyFeatures } from './phase57-intraday-readonly.js';
import { replayIntradayFrames } from './phase57-intraday-capture-replay.js';

export const PHASE57_LABEL_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_LABEL_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const num = v => finite(v) ? Number(v) : null;

function framePrice(frame) {
  return num(frame?.market?.last) ?? num(frame?.bar?.close) ?? null;
}

function frameHigh(frame) {
  return num(frame?.bar?.high) ?? framePrice(frame);
}

function frameLow(frame) {
  return num(frame?.bar?.low) ?? framePrice(frame);
}

function resolveBarrierLabel(current, futureFrames, barrierBps) {
  const entry = framePrice(current);
  if (!finite(entry) || entry <= 0) return null;
  const delta = entry * Number(barrierBps) / 10000;
  const upper = entry + delta;
  const lower = entry - delta;
  for (const frame of futureFrames) {
    const hi = frameHigh(frame);
    const lo = frameLow(frame);
    if (!finite(hi) || !finite(lo)) continue;
    const up = hi >= upper;
    const down = lo <= lower;
    if (up && down) return Object.freeze({ status: 'AMBIGUOUS_SAME_FRAME', label: null, outcomeAt: frame.capturedAt, entry, upper, lower });
    if (up) return Object.freeze({ status: 'RESOLVED', label: 1, direction: 'UPPER_FIRST', outcomeAt: frame.capturedAt, entry, upper, lower });
    if (down) return Object.freeze({ status: 'RESOLVED', label: 0, direction: 'LOWER_FIRST', outcomeAt: frame.capturedAt, entry, upper, lower });
  }
  return Object.freeze({ status: 'TIMEOUT', label: null, outcomeAt: futureFrames.at(-1)?.capturedAt ?? null, entry, upper, lower });
}

export function buildIntradayFeatureLabelRows(frames = [], { horizonFrames = 3, barrierBps = 20, minHistoryBars = 4 } = {}) {
  const ordered = replayIntradayFrames(frames);
  const groups = new Map();
  for (const frame of ordered) {
    const key = `${frame.sessionDate}|${frame.symbol}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(frame);
  }
  const rows = [];
  for (const group of groups.values()) {
    for (let i = 0; i < group.length; i += 1) {
      const current = group[i];
      const history = group.slice(0, i + 1);
      const bars = history.map(f => f.bar).filter(Boolean);
      if (bars.length < minHistoryBars) continue;
      const future = group.slice(i + 1, i + 1 + horizonFrames);
      if (!future.length) continue;
      const label = resolveBarrierLabel(current, future, barrierBps);
      if (!label || label.status !== 'RESOLVED') continue;
      const featureResult = buildIntradayReadonlyFeatures({
        bars,
        snapshot: current.book ?? current.market ?? {},
        ticks: current.ticks ?? [],
        sessionOpen: bars[0]?.open ?? null,
      });
      rows.push(Object.freeze({
        phase: '57.p4',
        symbol: current.symbol,
        sessionDate: current.sessionDate,
        featureCutoff: current.capturedAt,
        outcomeAt: label.outcomeAt,
        label: label.label,
        labelDirection: label.direction,
        barrierBps,
        horizonFrames,
        features: featureResult.features,
        interactions: featureResult.interactions,
        pointInTimeValid: Date.parse(current.capturedAt) < Date.parse(label.outcomeAt),
        source: Object.freeze({ mode: 'READ_ONLY', rssOrderFunctionsUsed: false }),
      }));
    }
  }
  return Object.freeze(rows.filter(row => row.pointInTimeValid).sort((a, b) => a.featureCutoff.localeCompare(b.featureCutoff)));
}

export function buildIntradayLabelManifest(rows = [], config = {}) {
  const list = Array.isArray(rows) ? rows : [];
  return Object.freeze({
    phase: '57.p4',
    status: list.length ? 'INTRADAY_FEATURE_LABEL_DATASET_READY' : 'NO_RESOLVED_INTRADAY_LABELS',
    rowCount: list.length,
    symbols: Object.freeze([...new Set(list.map(row => row.symbol))]),
    config: Object.freeze({ horizonFrames: config.horizonFrames ?? 3, barrierBps: config.barrierBps ?? 20, ambiguousSameFrame: 'EXCLUDED', timeouts: 'EXCLUDED' }),
    pointInTime: Object.freeze({ featureCutoffBeforeOutcomeRequired: true, futureFramesUsedOnlyForLabels: true }),
    recommendationAllowed: false,
    paperTradingAllowed: false,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    humanApprovalRequired: true,
    safety: PHASE57_LABEL_SAFETY,
  });
}

export default { buildIntradayFeatureLabelRows, buildIntradayLabelManifest };
