import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PHASE57_P22_3_SAFETY,
  buildDurableMicrostructureEvents,
  appendMicrostructureEventsIdempotently,
  auditMicrostructureCaptureGaps,
  assessMicrostructureRuntimeHealth,
  planMicrostructureRetention,
  buildMicrostructureDurabilityCycle,
} from '../daytrade/phase57-rss-microstructure-durability.js';

const safety = Object.freeze({
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

function bundle({
  symbol = '8035.T',
  sessionDate = '2026-08-10',
  capturedAt = '2026-08-10T00:30:00.000Z',
  ticks = [
    { timestamp: '2026-08-10T00:29:59.000Z', price: 100, volume: 10, captureId: '8035.T|2026-08-10|2026-08-10T00:30:00.000Z|RssTickList', tickOrdinalWithinCapture: 0 },
  ],
  replayEligible = true,
  continuityStatus = 'ROLLING_WINDOW_OVERLAP_RECONCILED',
  previousWindowSize = 0,
  currentWindowSize = ticks.length,
  overlapLength = 0,
} = {}) {
  const market = {
    type: 'RSS_MARKET_MICROSTRUCTURE_SNAPSHOT', symbol, sessionDate, capturedAt,
    timestamp: capturedAt, sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY', sourceFunction: 'RssMarket',
    excelReadOnly: true, transmitted: false,
  };
  const tickWindow = {
    type: 'RSS_TICKLIST_MICROSTRUCTURE_WINDOW', symbol, sessionDate, capturedAt,
    sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY', sourceFunction: 'RssTickList',
    excelReadOnly: true, transmitted: false, replayEligible, continuityStatus,
    previousWindowSize, currentWindowSize, overlapLength,
    newTickCount: ticks.length, newTicks: ticks,
  };
  return {
    status: replayEligible ? 'RSS_MICROSTRUCTURE_CAPTURE_READY' : 'RSS_MICROSTRUCTURE_CAPTURE_REVIEW_REQUIRED',
    symbol, sessionDate, capturedAt, market, ticks: tickWindow,
    excelReadOnly: true,
    executionAllowed: false,
    brokerWriteAllowed: false,
    excelOrderWriteAllowed: false,
    rssOrderFunctionAllowed: false,
    liveTradingAllowed: false,
    paperTradingAllowed: false,
    automaticPromotionAllowed: false,
    productionUpdateAllowed: false,
    transmitted: false,
    safety,
  };
}

function meta({
  eventId,
  captureKey,
  symbol = '8035.T',
  sessionDate = '2026-08-10',
  capturedAt,
  replayEligible = true,
  previousWindowSize = 0,
  currentWindowSize = 1,
  overlapLength = 0,
  continuityStatus = 'ROLLING_WINDOW_OVERLAP_RECONCILED',
} = {}) {
  return {
    phase: '57.p22.3', eventType: 'RSS_MICROSTRUCTURE_CAPTURE_META', eventId, captureKey,
    symbol, sessionDate, capturedAt, sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY',
    replayEligible, previousWindowSize, currentWindowSize, overlapLength, continuityStatus,
    transmitted: false, safety: PHASE57_P22_3_SAFETY,
  };
}

test('P22.3 safety remains fail-closed for execution, broker/Excel/RSS writes, paper/live trading and promotion', () => {
  for (const key of [
    'executionAllowed', 'brokerWriteAllowed', 'excelOrderWriteAllowed', 'rssOrderFunctionAllowed',
    'liveTradingAllowed', 'paperTradingAllowed', 'automaticPromotionAllowed', 'productionUpdateAllowed',
  ]) assert.equal(PHASE57_P22_3_SAFETY[key], false);
});

test('durable event builder preserves identical trade multiplicity with distinct capture ordinals', () => {
  const captureId = '8035.T|2026-08-10|2026-08-10T00:30:00.000Z|RssTickList';
  const input = bundle({
    ticks: [
      { timestamp: '2026-08-10T00:29:59.000Z', price: 100, volume: 10, captureId, tickOrdinalWithinCapture: 0 },
      { timestamp: '2026-08-10T00:29:59.000Z', price: 100, volume: 10, captureId, tickOrdinalWithinCapture: 1 },
    ],
  });
  const events = buildDurableMicrostructureEvents(input);
  const tradeEvents = events.filter(event => event.eventType === 'RSS_TICK_EVENT');
  assert.equal(events.length, 4);
  assert.equal(tradeEvents.length, 2);
  assert.equal(tradeEvents[0].timestamp, tradeEvents[1].timestamp);
  assert.equal(tradeEvents[0].price, tradeEvents[1].price);
  assert.equal(tradeEvents[0].volume, tradeEvents[1].volume);
  assert.notEqual(tradeEvents[0].eventId, tradeEvents[1].eventId);
});

test('idempotent append deduplicates only exact event identity and never timestamp-price-volume tuples', () => {
  const captureId = '8035.T|2026-08-10|2026-08-10T00:30:00.000Z|RssTickList';
  const events = buildDurableMicrostructureEvents(bundle({
    ticks: [
      { timestamp: '2026-08-10T00:29:59.000Z', price: 100, volume: 10, captureId, tickOrdinalWithinCapture: 0 },
      { timestamp: '2026-08-10T00:29:59.000Z', price: 100, volume: 10, captureId, tickOrdinalWithinCapture: 1 },
    ],
  }));
  const first = appendMicrostructureEventsIdempotently([], events);
  const replay = appendMicrostructureEventsIdempotently(first.events, events);
  assert.equal(first.events.length, 4);
  assert.equal(first.insertedCount, 4);
  assert.equal(replay.events.length, 4);
  assert.equal(replay.insertedCount, 0);
  assert.equal(replay.replayedDuplicates, 4);
  assert.equal(replay.multiplicityPreserved, true);
});

test('event identity collision with different payload is rejected instead of silently overwriting history', () => {
  const events = buildDurableMicrostructureEvents(bundle());
  const original = events[0];
  const conflict = { ...original, newTickCount: original.newTickCount + 1 };
  assert.throws(() => appendMicrostructureEventsIdempotently([original], [conflict]), /EVENT_ID_CONFLICT/);
});

test('gap audit detects active-window gaps but does not invent a gap across explicitly configured inactive windows', () => {
  const m1 = meta({ eventId: 'm1', captureKey: 'c1', capturedAt: '2026-08-10T00:00:00.000Z' });
  const m2 = meta({ eventId: 'm2', captureKey: 'c2', capturedAt: '2026-08-10T00:00:20.000Z' });
  const gap = auditMicrostructureCaptureGaps([m1, m2], { expectedIntervalMs: 5000, maxGapMultiplier: 3 });
  assert.equal(gap.status, 'MICROSTRUCTURE_GAP_AUDIT_BLOCKED');
  assert.equal(gap.largeGaps.length, 1);

  const am = meta({ eventId: 'am', captureKey: 'amc', capturedAt: '2026-08-10T02:29:58.000Z' });
  const pm = meta({ eventId: 'pm', captureKey: 'pmc', capturedAt: '2026-08-10T03:30:02.000Z' });
  const windows = [{ start: '09:00', end: '11:30', label: 'AM' }, { start: '12:30', end: '15:30', label: 'PM' }];
  const ignored = auditMicrostructureCaptureGaps([am, pm], { expectedIntervalMs: 5000, maxGapMultiplier: 3, activeWindowsJst: windows });
  assert.equal(ignored.largeGaps.length, 0);
  assert.equal(ignored.ignoredInactiveWindowTransitions, 1);
});

test('gap audit blocks zero-overlap rolling continuity and ambiguous 300-row windows', () => {
  const broken = meta({
    eventId: 'broken', captureKey: 'broken-capture', capturedAt: '2026-08-10T00:30:00.000Z',
    previousWindowSize: 200, currentWindowSize: 200, overlapLength: 0,
  });
  const ambiguous = meta({
    eventId: 'ambiguous', captureKey: 'ambiguous-capture', capturedAt: '2026-08-10T00:30:05.000Z',
    replayEligible: false, previousWindowSize: 300, currentWindowSize: 300, overlapLength: 300,
    continuityStatus: 'AMBIGUOUS_FULL_300_ROW_WINDOW_NO_SEQUENCE',
  });
  const audit = auditMicrostructureCaptureGaps([broken, ambiguous]);
  assert.deepEqual(audit.continuityBreaks, ['broken']);
  assert.deepEqual(audit.ambiguousCaptures, ['ambiguous']);
  assert.equal(audit.replayEligible, false);
});

test('runtime health blocks stale active-session data but pauses staleness outside configured active windows', () => {
  const event = meta({ eventId: 'm', captureKey: 'c', capturedAt: '2026-08-10T00:00:00.000Z' });
  const active = assessMicrostructureRuntimeHealth([event], {
    asOf: '2026-08-10T00:00:31.000Z', staleAfterMs: 30000,
  });
  assert.equal(active.status, 'MICROSTRUCTURE_RUNTIME_HEALTH_BLOCKED');
  assert.deepEqual(active.staleSymbols, ['8035.T']);

  const windows = [{ start: '09:00', end: '11:30' }, { start: '12:30', end: '15:30' }];
  const lunch = assessMicrostructureRuntimeHealth([event], {
    asOf: '2026-08-10T03:00:00.000Z', staleAfterMs: 30000, activeWindowsJst: windows,
  });
  assert.equal(lunch.runtimeExpectedActive, false);
  assert.deepEqual(lunch.staleSymbols, []);
});

test('retention plans whole capture groups, preserves review evidence, and performs no automatic deletion', () => {
  const oldNormal = meta({ eventId: 'old-normal', captureKey: 'old-normal-c', capturedAt: '2026-07-01T00:00:00.000Z' });
  const oldReview = meta({ eventId: 'old-review', captureKey: 'old-review-c', capturedAt: '2026-07-01T00:00:01.000Z', replayEligible: false });
  const recent1 = meta({ eventId: 'recent1', captureKey: 'recent1-c', capturedAt: '2026-08-10T00:00:00.000Z' });
  const recent2 = meta({ eventId: 'recent2', captureKey: 'recent2-c', capturedAt: '2026-08-10T00:00:05.000Z' });
  const recentMarket = {
    phase: '57.p22.3', eventType: 'RSS_MARKET_SNAPSHOT_EVENT', eventId: 'recent1-market', captureKey: 'recent1-c',
    symbol: '8035.T', sessionDate: '2026-08-10', capturedAt: '2026-08-10T00:00:00.000Z',
    sourceMode: 'MARKETSPEED_II_RSS_READ_ONLY', transmitted: false, safety: PHASE57_P22_3_SAFETY,
  };
  const plan = planMicrostructureRetention([oldNormal, oldReview, recent1, recentMarket, recent2], {
    asOf: '2026-08-10T00:01:00.000Z', retentionDays: 30, maxCapturesPerSymbolSession: 1,
  });
  assert.deepEqual(plan.expiredCaptureKeys, ['old-normal-c']);
  assert.deepEqual(plan.protectedCaptureKeys, ['old-review-c']);
  assert.deepEqual(plan.overflowCaptureKeys, ['recent1-c']);
  assert.equal(plan.archiveCandidates.filter(event => event.captureKey === 'recent1-c').length, 2);
  assert.equal(plan.deletionPerformed, false);
  assert.equal(plan.persistenceWritePerformed, false);
});

test('durability cycle remains research-only and ready only when capture continuity and health are clear', () => {
  const input = bundle();
  const result = buildMicrostructureDurabilityCycle({ bundle: input, asOf: input.capturedAt });
  assert.equal(result.status, 'MICROSTRUCTURE_DURABILITY_READY');
  assert.equal(result.researchReplayEligible, true);
  assert.equal(result.edgeClaimAllowed, false);
  assert.equal(result.executionAllowed, false);
  assert.equal(result.paperTradingAllowed, false);
  assert.equal(result.persistenceWritePerformed, false);
  assert.equal(result.transmitted, false);
});
