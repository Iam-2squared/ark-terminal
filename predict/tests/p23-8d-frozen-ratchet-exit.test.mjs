import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_8D_SAFETY,
  P23_8D_FROZEN_RATCHET_CONFIG,
  simulateFrozenRatchetExit,
  summarizeFrozenRatchetOutcomes,
} from '../daytrade/phase57-frozen-ratchet-exit.js';

const safetyFalse = [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
];
const bar = (timestamp, open, high, low, close, volume = 1000) => ({ timestamp, open, high, low, close, volume });
const sessionDate = '2026-08-10';
const context = [
  bar('2026-08-10T00:00:00.000Z', 100.0, 100.3, 99.9, 100.2),
  bar('2026-08-10T00:05:00.000Z', 100.2, 100.6, 100.1, 100.5),
  bar('2026-08-10T00:10:00.000Z', 100.5, 100.9, 100.4, 100.8),
  bar('2026-08-10T00:15:00.000Z', 100.8, 101.2, 100.7, 101.1),
];

test('P23.8D remains research-only and fail-closed', () => {
  for (const key of safetyFalse) assert.equal(PHASE57_P23_8D_SAFETY[key], false, key);
  assert.equal(PHASE57_P23_8D_SAFETY.humanApprovalRequired, true);
  assert.equal(P23_8D_FROZEN_RATCHET_CONFIG.configId, 'STATE_MONOTONIC_RATCHET_V1');
});

test('monotonic ratchet never loosens after activation', () => {
  const future = [
    bar('2026-08-10T00:20:00.000Z', 101.1, 102.0, 101.0, 101.9),
    bar('2026-08-10T00:25:00.000Z', 101.9, 102.8, 101.8, 102.7),
    bar('2026-08-10T00:30:00.000Z', 102.7, 103.5, 102.6, 103.4),
    bar('2026-08-10T00:35:00.000Z', 103.4, 104.0, 103.2, 103.8),
    bar('2026-08-10T00:40:00.000Z', 103.8, 103.9, 102.8, 103.0),
  ];
  const outcome = simulateFrozenRatchetExit({
    sessionDate,
    entryPrice: 101.1,
    direction: 'LONG',
    frozenEntry: true,
    contextBars: context,
    futureBars: future,
  }, {
    hardStopAtr: 20,
    ratchetActivationAtr: 0.5,
    ratchetGivebackAtrStrong: 1,
    ratchetGivebackAtrHold: 1,
    ratchetGivebackAtrCaution: 1,
    minBarsBeforeStateExit: 99,
  });
  assert.equal(outcome.ratchetActivated, true);
  assert.equal(outcome.ratchetNeverLoosened, true);
  const active = outcome.ratchetHistory.filter(item => item.stop != null).map(item => item.stop);
  assert.ok(active.length >= 2);
  for (let i = 1; i < active.length; i += 1) assert.ok(active[i] >= active[i - 1]);
});

test('ratchet stop used on a bar was fixed from completed prior bars', () => {
  const future = [
    bar('2026-08-10T00:20:00.000Z', 101.1, 103.0, 101.0, 102.9),
    bar('2026-08-10T00:25:00.000Z', 102.9, 103.2, 101.0, 101.2),
  ];
  const outcome = simulateFrozenRatchetExit({
    sessionDate,
    entryPrice: 101.1,
    direction: 'LONG',
    frozenEntry: true,
    contextBars: context,
    futureBars: future,
  }, {
    hardStopAtr: 20,
    ratchetActivationAtr: 0.1,
    ratchetGivebackAtrStrong: 0.5,
    ratchetGivebackAtrHold: 0.5,
    ratchetGivebackAtrCaution: 0.5,
    minBarsBeforeStateExit: 99,
  });
  const stopDecision = outcome.decisions.find(item => item.reason === 'MONOTONIC_RATCHET_STOP');
  assert.ok(stopDecision);
  assert.equal(stopDecision.stopWasFixedBeforeCurrentBar, true);
  assert.equal(outcome.preBarStopsUseCompletedBarsOnly, true);
  assert.equal(outcome.futureBarsUsedBeforeDecision, false);
  assert.equal(outcome.futureExtremaUsedForDecision, false);
});

test('cross-session paths are rejected and frozen-entry opt-out is forbidden', () => {
  assert.throws(() => simulateFrozenRatchetExit({
    sessionDate,
    entryPrice: 101.1,
    direction: 'LONG',
    frozenEntry: true,
    contextBars: context,
    futureBars: [bar('2026-08-11T00:20:00.000Z', 101.1, 101.5, 100.9, 101.2)],
  }), /forbids cross-session/);
  assert.throws(() => simulateFrozenRatchetExit({
    sessionDate,
    entryPrice: 101.1,
    direction: 'LONG',
    frozenEntry: false,
    contextBars: context,
    futureBars: [bar('2026-08-10T00:20:00.000Z', 101.1, 101.5, 100.9, 101.2)],
  }), /requires a frozen entry/);
});

test('aggregate summary preserves monotonic ratchet diagnostics', () => {
  const rows = [
    simulateFrozenRatchetExit({
      sessionDate, entryPrice: 101.1, direction: 'LONG', frozenEntry: true, contextBars: context,
      futureBars: [bar('2026-08-10T00:20:00.000Z', 101.1, 102, 101, 101.9)],
    }, { hardStopAtr: 20, ratchetActivationAtr: 100, minBarsBeforeStateExit: 99 }),
  ];
  const summary = summarizeFrozenRatchetOutcomes(rows);
  assert.equal(summary.signalCount, 1);
  assert.equal(summary.ratchetNeverLoosenedForAllTrades, true);
  assert.ok(Number.isFinite(summary.netAverageReturnPct));
});
