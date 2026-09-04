import test from 'node:test';
import assert from 'node:assert/strict';
import { buildEntryV2CandidateInventory } from '../daytrade/phase57-entry-quality-v2-candidate-inventory.js';

function artifact({ sessionDate = '2026-09-04', key = 'k1', symbol = '336A.T', direction = 'LONG', price = 1864 } = {}) {
  const ts = `${sessionDate}T01:25:00.000Z`;
  return {
    status: 'P25_DYNAMIC5M_BD_DAILY_EVALUATED',
    sessionDate,
    freshCompleteDay: false,
    classification: { formalOos: false, promotionEligible: false },
    B: {
      route: 'Dynamic 5m Selection -> Frozen Entry -> EXIT v3',
      pointCount: 15,
      expectedPointCount: 68,
      missingExpectedBucketCount: 53,
      resolvedCount: 1,
      pairs: [{
        key,
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
});
