import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { buildIntradayDynamicUniverseTimeline } from '../daytrade/phase57-p25-intraday-dynamic-universe.js';
import {
  ENTRY_V2_HISTORICAL_REPLAY_POLICY,
  auditEntryV2HistoricalReplayInputs,
  separateEntryV2ActualAndHistoricalSources,
} from '../daytrade/phase57-entry-quality-v2-historical-replay.js';

const observedAt = '2026-09-04T01:25:00.000Z';
const safety = () => ({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  transmitted: false,
});

function rawRows() {
  return Array.from({ length: 3000 }, (_, index) => ({
    symbol: `${String(1000 + index).padStart(4, '0')}.T`,
    price: 100 + index % 500,
    volume: 1000 + index * 10,
    changePct: (index % 17) - 8,
    turnover: 0,
    sector: `SECTOR_${index % 20}`,
  }));
}

function snapshot() {
  const rows = rawRows();
  return {
    schemaVersion: 1,
    phase: '57.p25.marketwide-5m-fresh-capture',
    bucket: '2026-09-04T01:25:00.000Z',
    observedAt,
    symbolCount: rows.length,
    stateHash: createHash('sha256').update(JSON.stringify(rows)).digest('hex'),
    rows,
    methodology: { pointInTimeOnly: true },
    safety: safety(),
  };
}

function currentMeasurement(raw) {
  const entries = raw.rows.map(row => ({
    symbol: row.symbol,
    sector: row.sector,
    market: null,
    status: 'analyzed',
    currentPrice: row.price,
    volume: row.volume,
    dailyChangePercent: row.changePct,
    scannedAt: raw.observedAt,
  }));
  const selected = buildIntradayDynamicUniverseTimeline({ snapshots: [{ asOf: raw.observedAt, entries }] })
    .points[0].rawUniverse.map(({ symbol, sector, currentPrice, sourceScannedAt, opportunityScore, turnoverYen }) => ({
      symbol, sector, currentPrice, sourceScannedAt, opportunityScore, turnoverYen,
    }));
  return {
    status: 'MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY',
    observedAt: raw.observedAt,
    inputSymbols: raw.rows.length,
    selected,
    selectedV2: [],
    policy: { candidateId: 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1' },
    safety: safety(),
  };
}

function bars() {
  const result = [];
  for (let minute = 50; minute <= 150; minute += 5) {
    result.push({
      timestamp: new Date(Date.parse('2026-09-04T00:00:00.000Z') + minute * 60_000).toISOString(),
      open: 100, high: 102, low: 99, close: 101, volume: 1000,
    });
  }
  return result;
}

function archiveFor(measurement) {
  return {
    sessionDate: '2026-09-04',
    status: 'P25_DYNAMIC5M_DAILY_BUNDLE_READY',
    safety: safety(),
    sessionBarsBySymbol: Object.fromEntries(measurement.selected.map(row => [row.symbol, bars()])),
  };
}

test('replays the current Dynamic5m selector from raw PIT rows and verifies exact stored parity', () => {
  const raw = snapshot();
  const measurement = currentMeasurement(raw);
  const audit = auditEntryV2HistoricalReplayInputs({
    marketSnapshots: [raw],
    storedMeasurements: [measurement],
    barArchives: [archiveFor(measurement)],
  });
  assert.equal(audit.pointCount, 1);
  assert.equal(audit.readyPointCount, 1);
  assert.equal(audit.blockedPointCount, 0);
  assert.equal(audit.exactSelectorParityCount, 1);
  assert.equal(audit.points[0].currentSelectorCandidateId, 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1');
  assert.equal(audit.points[0].exactSelectorParity, true);
  assert.equal(audit.points[0].prefixes[measurement.selected[0].symbol].at(-1).timestamp, '2026-09-04T01:20:00.000Z');
  assert.equal(audit.pitViolationCount, 0);
  assert.equal(audit.classification.prospective, false);
  assert.equal(ENTRY_V2_HISTORICAL_REPLAY_POLICY.oldSelectorMembershipMayBeReused, false);
});

test('blocks the whole replay point when any current-selector symbol lacks stored bars', () => {
  const raw = snapshot();
  const measurement = currentMeasurement(raw);
  const archive = archiveFor(measurement);
  delete archive.sessionBarsBySymbol[measurement.selected[0].symbol];
  const audit = auditEntryV2HistoricalReplayInputs({
    marketSnapshots: [raw],
    storedMeasurements: [measurement],
    barArchives: [archive],
  });
  assert.equal(audit.readyPointCount, 0);
  assert.equal(audit.blockedPointCount, 1);
  assert.equal(audit.points[0].reason, 'INCOMPLETE_CURRENT_SELECTOR_BAR_COVERAGE');
  assert.equal(audit.points[0].missingBarSymbolCount, 1);
  assert.equal(audit.blockedReasonDistribution.INCOMPLETE_CURRENT_SELECTOR_BAR_COVERAGE, 1);
});

test('rejects old selector outputs, raw outcome contamination, and selector parity drift', () => {
  const raw = snapshot();
  const measurement = currentMeasurement(raw);
  const archive = archiveFor(measurement);

  const oldSelector = structuredClone(measurement);
  oldSelector.policy.candidateId = 'DYNAMIC_50';
  assert.throws(() => auditEntryV2HistoricalReplayInputs({
    marketSnapshots: [raw], storedMeasurements: [oldSelector], barArchives: [archive],
  }), /OLD_OR_DIFFERENT_SELECTOR_REJECTED/);

  const poisoned = structuredClone(raw);
  poisoned.rows[0].netReturnPct = 1;
  poisoned.stateHash = createHash('sha256').update(JSON.stringify(poisoned.rows)).digest('hex');
  assert.throws(() => auditEntryV2HistoricalReplayInputs({
    marketSnapshots: [poisoned], storedMeasurements: [measurement], barArchives: [archive],
  }), /RAW_ROW_FORBIDDEN_netReturnPct/);

  const drifted = structuredClone(measurement);
  drifted.selected[0].currentPrice += 1;
  assert.throws(() => auditEntryV2HistoricalReplayInputs({
    marketSnapshots: [raw], storedMeasurements: [drifted], barArchives: [archive],
  }), /CURRENT_SELECTOR_PARITY_MISMATCH/);
});

test('keeps Actual Durable and Historical Replay separate and excludes overlapping events', () => {
  const eventId = '2026-09-04|2026-09-04T01:25:00.000Z|336A.T';
  const actualInventory = {
    sourceClass: 'ACTUAL_DURABLE',
    rows: [{ candidateEventId: eventId }],
  };
  const historicalReplay = {
    sourceClass: 'HISTORICAL_RETROSPECTIVE_REPLAY',
    classification: { prospective: false, developmentOnly: true },
    candidates: [
      { candidateEventId: eventId },
      { candidateEventId: '2026-09-02|2026-09-02T01:30:00.000Z|4440.T' },
    ],
  };
  const separated = separateEntryV2ActualAndHistoricalSources({ actualInventory, historicalReplay });
  assert.equal(separated.actualDurableCandidateCount, 1);
  assert.equal(separated.historicalReplayCandidateCount, 2);
  assert.equal(separated.overlapExcludedFromHistoricalDevelopmentCount, 1);
  assert.equal(separated.independentHistoricalDevelopmentCandidateCount, 1);
  assert.equal(separated.historicalIncludedInProspectiveDenominator, false);
  assert.equal(separated.sourceClassesKeptSeparate, true);
});
