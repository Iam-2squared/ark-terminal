import test from 'node:test';
import assert from 'node:assert/strict';
import {
 observeNo11RssCumulativeVa,inspectNo11ObservedTurnoverInterval
} from '../runtime/no11_rss_cumulative_va_observability.mjs';
const base={
 symbol:'7203.T',marketDate:'2026-10-26',
 lastPrice:'105',marketClock:'09:30:02',
 cumulativeVolumeRaw:'1000',
 cumulativeTurnoverRaw:'102.4',
 vendorVolumeWeightedAverage:'102.4'
};
const at='2026-10-26T09:30:08+09:00';
test('venue turnover expressed in thousand yen is recognized only as observed hint',()=>{
 const x=observeNo11RssCumulativeVa({record:base,observedEndJst:at});
 assert.equal(x.status,'VENDOR_RATIO_CONSISTENT_NOT_MINUTE_VA');
 assert.equal(x.observedUnitScale,1000);
 assert.equal(x.cumulativeTurnoverYenObserved,102400);
 assert.equal(x.nativeOneMinuteVaCertified,false);
 assert.equal(x.usedCloseTimesVolume,false);
 assert.equal(x.turnoverUpdateClockCertified,false);
});
test('yen unit possible, but never call local observations broker exact Va',()=>{
 const x=observeNo11RssCumulativeVa({record:{
  ...base,cumulativeTurnoverRaw:'102400'
 },observedEndJst:at});
 assert.equal(x.observedUnitScale,1);
 assert.equal(x.nativeOneMinuteVaCertified,false);
});
test('null, string errors, stale mismatch and ratio mismatch stay unresolved',()=>{
 for(const v of [null,'#N/A',-1]){
  const x=observeNo11RssCumulativeVa({
    record:{...base,cumulativeTurnoverRaw:v},observedEndJst:at
  });
  assert.equal(x.status,'SOURCE_INCOMPLETE');
 }
 assert.equal(observeNo11RssCumulativeVa({
  record:base,observedEndJst:'2026-10-27T09:30:08+09:00'
 }).status,'SOURCE_INCOMPLETE');
 const mismatch=observeNo11RssCumulativeVa({
  record:{...base,vendorVolumeWeightedAverage:'4000'},
  observedEndJst:at
 });
 assert.equal(mismatch.status,'TURNOVER_VWAP_RATIO_MISMATCH');
});
test('cumulative turnover delta with one-minute matching volume stays estimate only',()=>{
 const first=observeNo11RssCumulativeVa({record:base,observedEndJst:at});
 const next=observeNo11RssCumulativeVa({
  record:{...base,cumulativeVolumeRaw:'1100',
   cumulativeTurnoverRaw:'112.64',vendorVolumeWeightedAverage:'102.4'},
  observedEndJst:'2026-10-26T09:31:08+09:00'
 });
 const result=inspectNo11ObservedTurnoverInterval({
  earlier:first,later:next,chartOneMinuteVolume:100
 });
 assert.equal(result.status,'RECEIVED_COUNTER_DELTA_WITH_MATCHING_1M_VOLUME');
 assert.ok(Math.abs(result.turnoverDeltaYenObserved-10240)<1e-9);
 assert.equal(result.nativeOneMinuteVaCertified,false);
 assert.equal(result.frozenSelectorProductionVaAllowed,false);
 assert.equal(result.orderTransmission,false);
});
test('negative counter, late sample, volume mismatch all explicitly block',()=>{
 const first=observeNo11RssCumulativeVa({record:base,observedEndJst:at});
 const create=(end,volume,turnover,vwap='102.4')=>
 observeNo11RssCumulativeVa({
  record:{...base,cumulativeVolumeRaw:String(volume),
   cumulativeTurnoverRaw:String(turnover),
   vendorVolumeWeightedAverage:vwap},
  observedEndJst:end
 });
 const early=create('2026-10-26T09:31:08+09:00',999,102.3);
 assert.match(inspectNo11ObservedTurnoverInterval({
  earlier:first,later:early,chartOneMinuteVolume:0
 }).status,/BLOCKED_COUNTER_REVERSED/);
 const delayed=create('2026-10-26T09:35:08+09:00',1100,112.64);
 assert.match(inspectNo11ObservedTurnoverInterval({
  earlier:first,later:delayed,chartOneMinuteVolume:100
 }).status,/BLOCKED_OBSERVATION_INTERVAL_GAP/);
 const mismatch=create('2026-10-26T09:31:08+09:00',1100,112.64);
 assert.match(inspectNo11ObservedTurnoverInterval({
  earlier:first,later:mismatch,chartOneMinuteVolume:101
 }).status,/BLOCKED_CHART_VOLUME/);
});
