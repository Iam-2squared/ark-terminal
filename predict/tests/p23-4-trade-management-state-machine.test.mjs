import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P23_4_SAFETY,
  TRADE_MANAGEMENT_STATES,
  DEFAULT_STATE_MACHINE_CONFIG,
  transitionTradeManagementState,
  simulateTradeManagementStateMachine,
  evaluateTradeManagementStateMachine,
} from '../daytrade/phase57-trade-management-state-machine.js';

const safetyFalse = [
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed',
];

function bar(timestamp, open, high, low, close, volume = 1000) {
  return { timestamp, open, high, low, close, volume };
}

const sessionDate = '2026-08-10';
const context = [
  bar('2026-08-10T00:00:00.000Z', 100.0, 100.4, 99.8, 100.2),
  bar('2026-08-10T00:05:00.000Z', 100.2, 100.8, 100.1, 100.7),
  bar('2026-08-10T00:10:00.000Z', 100.7, 101.3, 100.6, 101.2),
  bar('2026-08-10T00:15:00.000Z', 101.2, 101.9, 101.1, 101.8),
];

test('P23.4 safety remains fail-closed', () => {
  for (const key of safetyFalse) assert.equal(PHASE57_P23_4_SAFETY[key], false, key);
  assert.equal(PHASE57_P23_4_SAFETY.humanApprovalRequired, true);
});

test('a mild one-bar warning enters CAUTION but does not exit', () => {
  const config = { ...DEFAULT_STATE_MACHINE_CONFIG, minBarsBeforeStateExit: 1 };
  const transition = transitionTradeManagementState({
    priorState: TRADE_MANAGEMENT_STATES.STRONG_HOLD,
    damageVotes: 2,
    healthyVotes: 4,
    structureBroken: false,
    barsHeld: 5,
    warningStreak: 0,
    severeStreak: 0,
    recoveryStreak: 0,
    barsInCaution: 0,
  }, config);
  assert.equal(transition.nextState, TRADE_MANAGEMENT_STATES.CAUTION);
  assert.equal(transition.exit, false);
  assert.equal(transition.reason, 'ENTER_CAUTION');
});

test('CAUTION can recover instead of forcing a sale', () => {
  const transition = transitionTradeManagementState({
    priorState: TRADE_MANAGEMENT_STATES.CAUTION,
    damageVotes: 0,
    healthyVotes: 7,
    structureBroken: false,
    barsHeld: 4,
    warningStreak: 1,
    severeStreak: 0,
    recoveryStreak: 0,
    barsInCaution: 1,
  });
  assert.equal(transition.nextState, TRADE_MANAGEMENT_STATES.STRONG_HOLD);
  assert.equal(transition.exit, false);
  assert.equal(transition.reason, 'CAUTION_RECOVERED');
});

test('persistent damage must be confirmed before a state-machine exit', () => {
  const config = { ...DEFAULT_STATE_MACHINE_CONFIG, severeBreakdownConfirmBars: 99 };
  const first = transitionTradeManagementState({
    priorState: TRADE_MANAGEMENT_STATES.HOLD,
    damageVotes: 4,
    healthyVotes: 2,
    structureBroken: false,
    barsHeld: 3,
  }, config);
  assert.equal(first.nextState, TRADE_MANAGEMENT_STATES.CAUTION);
  assert.equal(first.exit, false);

  const second = transitionTradeManagementState({
    priorState: TRADE_MANAGEMENT_STATES.CAUTION,
    damageVotes: 4,
    healthyVotes: 2,
    structureBroken: false,
    barsHeld: 4,
    warningStreak: first.warningStreak,
    severeStreak: first.severeStreak,
    recoveryStreak: first.recoveryStreak,
    barsInCaution: first.barsInCaution,
  }, config);
  assert.equal(second.nextState, TRADE_MANAGEMENT_STATES.EXIT);
  assert.equal(second.reason, 'PERSISTENT_CHART_BREAKDOWN');
});

test('healthy trend is not sold at a fixed 5/15/30 minute bucket', () => {
  const future = [
    bar('2026-08-10T00:20:00.000Z', 101.8, 102.4, 101.7, 102.3),
    bar('2026-08-10T00:25:00.000Z', 102.3, 103.0, 102.2, 102.9),
    bar('2026-08-10T00:30:00.000Z', 102.9, 103.6, 102.8, 103.5),
    bar('2026-08-10T00:35:00.000Z', 103.5, 104.2, 103.4, 104.1),
    bar('2026-08-10T00:40:00.000Z', 104.1, 104.8, 104.0, 104.7),
    bar('2026-08-10T00:45:00.000Z', 104.7, 105.4, 104.6, 105.3),
    bar('2026-08-10T00:50:00.000Z', 105.3, 106.0, 105.2, 105.9),
  ];
  const outcome = simulateTradeManagementStateMachine({
    sessionDate,
    entryPrice: 101.8,
    signalDirection: 'LONG',
    contextBars: context,
    futureBars: future,
  }, {
    hardStopAtr: 20,
    profitProtectActivationAtr: 100,
    maxHoldBars: 1000,
  });
  assert.equal(outcome.exitReason, 'SESSION_OR_DATA_END');
  assert.equal(outcome.barsHeld, 7);
  assert.equal(outcome.fixedTimeExitPrimary, false);
  assert.ok(outcome.stateVisitCounts.STRONG_HOLD > 0);
});

test('profit protection uses only a stop fixed before the current bar', () => {
  const future = [
    bar('2026-08-10T00:20:00.000Z', 101.8, 104.0, 101.7, 103.8),
    bar('2026-08-10T00:25:00.000Z', 103.8, 104.2, 103.4, 104.0),
    bar('2026-08-10T00:30:00.000Z', 104.0, 104.1, 102.0, 102.5),
  ];
  const outcome = simulateTradeManagementStateMachine({
    sessionDate,
    entryPrice: 101.8,
    signalDirection: 'LONG',
    contextBars: context,
    futureBars: future,
  }, {
    hardStopAtr: 20,
    profitProtectActivationAtr: 0.5,
    profitProtectGivebackAtrStrong: 1,
    profitProtectGivebackAtrHold: 1,
    profitProtectGivebackAtrCaution: 1,
    minBarsBeforeStateExit: 99,
  });
  const stopDecision = outcome.decisions.find(item => item.reason === 'STATE_AWARE_PROFIT_PROTECTION');
  assert.ok(stopDecision);
  assert.equal(stopDecision.stopWasFixedBeforeCurrentBar, true);
  assert.equal(outcome.intrabarExit, true);
});

test('cross-session future bars are rejected', () => {
  assert.throws(() => simulateTradeManagementStateMachine({
    sessionDate,
    entryPrice: 101.8,
    signalDirection: 'LONG',
    contextBars: context,
    futureBars: [bar('2026-08-11T00:20:00.000Z', 101.8, 102, 101.5, 101.9)],
  }), /forbids cross-session/);
});

test('aggregate evaluator preserves research-only semantics', () => {
  const rows = [{
    sessionDate,
    entryPrice: 101.8,
    signalDirection: 'LONG',
    contextBars: context,
    futureBars: [
      bar('2026-08-10T00:20:00.000Z', 101.8, 102.5, 101.7, 102.4),
      bar('2026-08-10T00:25:00.000Z', 102.4, 103.0, 102.3, 102.9),
    ],
  }];
  const summary = evaluateTradeManagementStateMachine(rows, { hardStopAtr: 20, profitProtectActivationAtr: 100 });
  assert.equal(summary.signalCount, 1);
  assert.equal(summary.stateful, true);
  assert.equal(summary.edgeClaimAllowed, false);
  assert.equal(summary.recommendationAllowed, false);
  assert.equal(summary.executionAllowed, false);
  assert.equal(summary.transmitted, false);
});
