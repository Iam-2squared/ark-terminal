import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TREND_GATE_ID, DAILY_SMA_PERIODS, validateExchangeCalendar,
  evaluateOriginalSelectorTrendG1, prefilterOriginalSelectorUniverse,
} from '../runtime/no11_existing_selector_trend_prefilter.mjs';

// Synthetic calendar is explicit input, never presented as an exchange calendar.
const sessions = Array.from({length: 77}, (_, i) =>
  new Date(Date.UTC(2026, 0, 1 + i)).toISOString().slice(0, 10));
const session = sessions.at(-1);
const cutoff = session + 'T09:30:00+09:00';
const expected = sessions.slice(0, 76);
const rising = Array.from({length: 76}, (_, i) => String(100 + i));
const history = (closes = rising, symbol = 'SYNTH.T') => ({
  symbol, priceBasis: 'COMPARABLE_RAW', corporateActionsCleared: true,
  bars: expected.map((day, i) => ({
    session: day, close: closes[i], knownAtJst: day + 'T16:00:00+09:00',
  })),
});
const run = instruments => prefilterOriginalSelectorUniverse({
  session, decisionCutoffJst: cutoff, tradingSessions: sessions, instruments,
});
test('donor G1 only: 5/15/25/75 are the fixed SMA periods', () => {
  assert.equal(TREND_GATE_ID, 'NO11_OPTIONAL_DAILY_G1_ALL_AXES_UP_V1');
  assert.deepEqual(DAILY_SMA_PERIODS, [5, 15, 25, 75]);
  assert.deepEqual(validateExchangeCalendar(session, sessions), expected);
});
test('all long/medium/short axes UP: admission without a new score', () => {
  const v = run([history()]);
  assert.deepEqual(v.eligibleSymbols, ['SYNTH.T']);
  assert.equal(v.results[0].status, 'PASS');
  assert.deepEqual(v.results[0].dailySmaUp, {5: true, 15: true, 25: true, 75: true});
  assert.equal(v.originalIntradaySelectionScheduleModified, false);
  assert.equal(v.newModelTraining, false);
  assert.equal(v.orderTransmission, false);
  assert.equal(v.productionReady, false);
});
test('all flat, all falling: REJECT rather than positive or neutral admission', () => {
  assert.deepEqual(run([history(rising.map(() => '100'))]).eligibleSymbols, []);
  const down = Array.from({length: 76}, (_, i) => String(300-i));
  assert.equal(run([history(down)]).results[0].status, 'REJECT');
});
test('mixed trend is WAIT and also outside active original Selector pool', () => {
  const mixed = rising.slice();
  mixed.splice(71, 5, '168', '167', '166', '165', '164');
  const r = run([history(mixed)]).results[0];
  assert.equal(r.status, 'WAIT');
  assert.equal(r.axes.long, true);
  assert.equal(r.axes.short, false);
});
test('future day poisoning cannot change previous-day gate', () => {
  const a = history();
  const b = structuredClone(a);
  b.bars.push({session, close: '1', knownAtJst: session + 'T15:30:00+09:00'});
  assert.deepEqual(run([a]).results, run([b]).results);
});
test('missing and late inputs are UNKNOWN, never silently treated as zero', () => {
  const missing = history(); missing.bars.splice(4, 1);
  assert.equal(run([missing]).results[0].status, 'UNKNOWN');
  const late = history();
  late.bars.at(-1).knownAtJst = session + 'T15:30:00+09:00';
  assert.equal(run([late]).results[0].status, 'UNKNOWN');
  const absent = history(); absent.bars.at(1).close = null;
  assert.equal(run([absent]).results[0].status, 'UNKNOWN');
});
test('corporate action basis must be explicitly certified', () => {
  const bad = history();
  bad.corporateActionsCleared = false;
  assert.equal(run([bad]).results[0].reason,
    'PRICE_BASIS_OR_CORPORATE_ACTION_NOT_VERIFIED');
});
test('exact-decimal tiny positive slope is not rounded into flat', () => {
  const values = rising.map(x => x + '.00000000000000000000001');
  assert.equal(run([history(values)]).results[0].status, 'PASS');
  const wrongType = history();
  wrongType.bars.at(-1).close = Number(wrongType.bars.at(-1).close);
  assert.equal(run([wrongType]).results[0].status, 'UNKNOWN');
});
test('unexpected duplicate dates or symbol identity fail closed', () => {
  const dup = history();
  dup.bars.push({...dup.bars[0]});
  assert.equal(run([dup]).results[0].status, 'UNKNOWN');
  assert.throws(() => run([history(), history()]), /SYMBOL_IDENTITY_INVALID/);
  assert.throws(() => validateExchangeCalendar(session, sessions.slice(1)),
    /EXCHANGE_CALENDAR_REQUIRED/);
  assert.throws(() => validateExchangeCalendar(sessions.at(-2), sessions),
    /EXCHANGE_CALENDAR_COVERAGE_INSUFFICIENT/);
});
test('RSS limit is reported, not bypassed by arbitrary top-500 truncation', () => {
  const many = Array.from({length: 501}, (_, i) =>
    history(rising, 'SYNTH' + i + '.T'));
  const r = run(many);
  assert.equal(r.eligibleSymbols.length, 501);
  assert.equal(r.withinRssMarketCap, false);
  assert.equal(r.truncatedForCap, false);
  assert.equal(r.counts.PASS, 501);
});
test('input objects remain unchanged and decision does not require future outcome', () => {
  const input = history();
  const previous = structuredClone(input);
  const r = run([input]);
  assert.deepEqual(input, previous);
  assert.equal(r.marketPerformanceCertified, false);
  assert.equal(r.actualProviderReceiptCertified, false);
});
test('invalid global market calendar or cutoff cannot yield a green receipt', () => {
  assert.throws(() => prefilterOriginalSelectorUniverse({session, decisionCutoffJst: '2026-01-01T09:30:00+09:00', tradingSessions: sessions, instruments: []}), /DECISION_CUTOFF_INVALID/);
  assert.throws(() => prefilterOriginalSelectorUniverse({session, decisionCutoffJst: cutoff, tradingSessions: [session], instruments: []}), /EXCHANGE_CALENDAR_REQUIRED/);
});
