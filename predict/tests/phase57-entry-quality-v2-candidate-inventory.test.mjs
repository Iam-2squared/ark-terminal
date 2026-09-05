import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildEntryV2CandidateInventory,
  buildEntryV2ActualDurableCandidateInventory,
} from '../daytrade/phase57-entry-quality-v2-candidate-inventory.js';

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

function artifact({ sessionDate = '2026-09-04', key = 'k1', symbol = '336A.T', direction = 'LONG', price = 1864 } = {}) {
  const ts = `${sessionDate}T01:25:00.000Z`;
  return {
    status: 'P25_DYNAMIC5M_BD_DAILY_EVALUATED',
    sessionDate,
    freshCompleteDay: false,
    classification: { formalOos: false, promotionEligible: false },
    safety: safety(),
    B: {
      route: 'Dynamic 5m Selection -> Frozen Entry -> EXIT v3',
      pointCount: 15,
      expectedPointCount: 68,
      missingExpectedBucketCount: 53,
      frozenEntryCount: 1,
      resolvedCount: 1,
      blockedCount: 0,
      blocked: [],
      pairs: [{
        key,
        sessionDate,
        symbol,
        entry: {
          key,
          entryAccepted: true,
          symbol,
          sessionDate,
          entryTimestamp: ts,
          selectionObservedAt: ts,
          featureCutoff: `${sessionDate}T01:20:00.000Z`,
          signalDirection: direction === 'LONG' ? 1 : -1,
          direction,
          entryPrice: price,
          confidence: 0.62,
          probability: direction === 'LONG' ? 0.62 : 0.38,
          selectedFeatureFamily: 'MOMENTUM',
          selectedModelType: 'LOGISTIC_REGRESSION',
          selectedConfigId: 'LOGIT',
          selectedThreshold: 0.6,
          baseHorizonBars: 12,
          sector: '情報・通信業',
          variantMemberships: ['DYNAMIC_5M'],
          frozenBeforeOutcome: true,
          currentOutcomeUsed: false,
          selectionOpportunityScore: 0.63,
        },
      }],
    },
  };
}

function fiveMinuteBar(sessionDate, minute, close = 1000) {
  const timestamp = new Date(Date.parse(`${sessionDate}T00:00:00.000Z`) + minute * 60_000).toISOString();
  return { timestamp, open: close - 1, high: close + 2, low: close - 2, close, volume: 1000 + minute };
}

function bundleFor(sourceArtifact, { includeV2 = true } = {}) {
  const entry = sourceArtifact.B.pairs[0].entry;
  const bars = [];
  for (let minute = 55; minute <= 150; minute += 5) bars.push(fiveMinuteBar(sourceArtifact.sessionDate, minute, entry.entryPrice));
  return {
    status: 'P25_DYNAMIC5M_DAILY_BUNDLE_READY',
    sessionDate: sourceArtifact.sessionDate,
    barsReady: true,
    safety: safety(),
    points: [{
      observedAt: entry.entryTimestamp,
      policy: { candidateId: 'INTRADAY_DYNAMIC_5M_UNIVERSE_V1' },
      safety: safety(),
      selected: [{
        symbol: entry.symbol,
        currentPrice: entry.entryPrice,
        sourceScannedAt: entry.entryTimestamp,
        opportunityScore: entry.selectionOpportunityScore,
      }],
      dynamic5mV2: {
        candidateId: 'INTRADAY_DYNAMIC_5M_UNIVERSE_V2',
        safety: safety(),
      },
      selectedV2: includeV2 ? [{
        symbol: entry.symbol,
        currentPrice: entry.entryPrice,
        sourceScannedAt: entry.entryTimestamp,
        opportunityScore: entry.selectionOpportunityScore,
        v2Score: 0.71,
      }] : [],
    }],
    sessionBarsBySymbol: { [entry.symbol]: bars },
  };
}

test('builds deterministic all-candidate inventory without changing Selector/Entry/EXIT', () => {
  const a = artifact({ sessionDate: '2026-09-03', key: 'a', symbol: '4440.T', direction: 'SHORT', price: 2018 });
  const b = artifact({ sessionDate: '2026-09-04', key: 'b', symbol: '336A.T', direction: 'LONG', price: 1864 });
  const x = buildEntryV2CandidateInventory({ artifacts: [b, a] });
  const y = buildEntryV2CandidateInventory({ artifacts: [b, a] });
  assert.equal(x.rowCount, 2);
  assert.equal(x.countsByDirection.LONG, 1);
  assert.equal(x.countsByDirection.SHORT, 1);
  assert.equal(x.countsBySymbol['4440.T'], 1);
  assert.equal(x.countsBySymbol['336A.T'], 1);
  assert.equal(x.rows[0].sessionDate, '2026-09-03');
  assert.equal(x.rows[1].sessionDate, '2026-09-04');
  assert.equal(x.inventorySha256, y.inventorySha256);
  assert.equal(x.classification.allRowsFrozenBeforeOutcome, true);
  assert.equal(x.classification.allRowsCurrentOutcomeUnused, true);
  assert.equal(x.classification.allSessionsFormalOos, false);
  assert.equal(x.classification.promotionEligible, false);
  assert.equal(x.policy.selectorChangesAllowed, false);
  assert.equal(x.policy.exitChangesAllowed, false);
  assert.equal(x.policy.automaticPromotionAllowed, false);
  assert.equal(x.policy.executionAllowed, false);
  assert.equal(x.sourceClass, 'ACTUAL_DURABLE');
  assert.equal(x.canonicalDataAudited, false);
});

test('audits Actual Durable candidates against canonical bars and separates event from selector memberships', () => {
  const source = artifact();
  const result = buildEntryV2ActualDurableCandidateInventory({
    artifacts: [source],
    dailyBundles: [bundleFor(source)],
    roundTripCostBps: 5,
  });
  assert.equal(result.status, 'ENTRY_V2_ACTUAL_DURABLE_CANONICAL_INVENTORY_READY');
  assert.equal(result.totalCandidates, 1);
  assert.equal(result.uniqueCandidateEventCount, 1);
  assert.equal(result.selectorMembershipCount, 2);
  assert.equal(result.countsBySelectorMembership.DYNAMIC5M_V1, 1);
  assert.equal(result.countsBySelectorMembership.DYNAMIC5M_V2, 1);
  assert.equal(result.rows[0].contextBarCount, 6);
  assert.equal(result.rows[0].contextBars.at(-1).timestamp, '2026-09-04T01:20:00.000Z');
  assert.equal(result.rows[0].labelCompleteness[12], true);
  assert.equal(result.labelCompletenessByHorizon[12].complete, 1);
  assert.equal(result.pitViolationCount, 0);
  assert.equal(result.classification.historicalReplay, false);
  assert.equal(result.classification.allSessionsFormalOos, false);
});

test('fails closed on duplicate candidate or broken PIT lineage', () => {
  const a = artifact();
  assert.throws(() => buildEntryV2CandidateInventory({ artifacts: [a, a] }), /DUPLICATE_CANDIDATE/);

  const bad = artifact({ key: 'bad' });
  bad.B.pairs[0].entry.currentOutcomeUsed = true;
  assert.throws(() => buildEntryV2CandidateInventory({ artifacts: [bad] }), /CURRENT_OUTCOME_USED/);

  const bad2 = artifact({ key: 'bad2' });
  bad2.B.pairs[0].entry.selectionObservedAt = '2026-09-04T01:30:00.000Z';
  assert.throws(() => buildEntryV2CandidateInventory({ artifacts: [bad2] }), /TIMESTAMP_MISMATCH/);

  const bad3 = artifact({ key: 'bad3' });
  const badBundle = bundleFor(bad3);
  badBundle.points[0].selected[0].currentPrice += 1;
  assert.throws(() => buildEntryV2ActualDurableCandidateInventory({
    artifacts: [bad3], dailyBundles: [badBundle],
  }), /ENTRY_REFERENCE_PRICE_MISMATCH/);
});
