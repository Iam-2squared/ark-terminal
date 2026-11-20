import assert from 'node:assert/strict';
import test from 'node:test';
import {normalizeAndAggregateMinuteRows} from '../long-only/phase57-long-only-integrated-dataset.js';
import {buildCausalL1Features,buildEvaluatorOnlyL1Label} from '../long-only/phase57-long-only-l1-labels-features.js';
import {buildFixedHorizonTargets} from '../long-only/phase57-long-only-l2-fixed-horizon.js';
import {normalizeMinuteProvenance,measureCorrectedRow} from '../long-only/phase57-long-only-corrected-measurement.js';

const date='2024-01-04',symbol='11110';
const raw=(time,close=100,{open=close,high=close,low=close}={})=>({Date:date,Code:symbol,Time:time,O:open,H:high,L:low,C:close,Vo:10,Va:close*10});
function setup(rows,decisionTimeJst='09:30'){
  const intraday=normalizeAndAggregateMinuteRows(rows),key=`${date}|${symbol}`;
  const feature=buildCausalL1Features({sessionDate:date,symbol,decisionTimeJst,bars5m:intraday.bars,previousAdjustedClose:100});
  const label=buildEvaluatorOnlyL1Label({sessionDate:date,symbol,decisionTimeJst,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,previousAdjustedClose:100,officialFinalAdjustedClose:105});
  const target=buildFixedHorizonTargets({featureRows:[feature],bars5m:intraday.bars,evaluatorOnlyLabels:label?[label]:[]})[0]??null;
  return measureCorrectedRow({feature,target,label,bars:intraday.bars,minutes:normalizeMinuteProvenance(rows).get(key)??[],terminalAuctions:intraday.terminalAuctions,daily:{unadjustedClose:105,adjustedClose:105,adjustedPreviousClose:100,adjustmentScale:1}});
}

test('fresh decision close and strict wall-clock endpoint are causal',()=>{
  const rows=[raw('09:29'),raw('09:34',101),raw('09:39',102),raw('09:44',103),raw('09:49',104),raw('09:54',105),raw('09:59',106)];
  const out=setup(rows);
  assert.equal(out.decisionPrice,100); assert.equal(out.referenceAgeMin,0); assert.equal(out.corrected30Evaluable,1);
  assert.ok(Math.abs(out.corrected30ReturnBps-600)<1e-8); assert.equal(out.corrected30EndpointAgeMin,0);
});

test('lunch is not bridged and stale decision price fails closed',()=>{
  const lunch=setup([raw('11:29'),raw('12:34',110),raw('12:39',111)],'11:30');
  assert.equal(lunch.decisionPriceValid,1); assert.equal(lunch.corrected30Evaluable,0);
  const stale=setup([raw('09:30'),raw('10:04',110)],'10:00');
  assert.equal(stale.referenceAgeMin,29); assert.equal(stale.decisionPriceValid,0);
  assert.equal(stale.sessionMfePct,null); assert.equal(stale.highOpportunity3,null);
});

test('high touch and close confirmation remain distinct',()=>{
  const out=setup([raw('09:29'),raw('09:30',101,{high:106,low:99}),raw('09:34',101)]);
  assert.equal(out.highOpportunity5,1); assert.equal(out.closeOpportunity5,0);
  assert.equal(out.timeToHigh5Min,5); assert.equal(out.timeToClose5Min,null);
});

test('MFE and MAE are clipped for 30m and same session',()=>{
  const allUp=setup([raw('09:29'),raw('09:30',101,{low:100.5}),raw('09:34',102,{low:101})]);
  assert.equal(allUp.mae30Pct,0); assert.equal(allUp.sessionMaePct,0);
  const allDown=setup([raw('09:29'),raw('09:30',99,{high:99.5,low:98}),raw('09:34',98,{high:99,low:97})]);
  assert.equal(allDown.mfe30Pct,0); assert.equal(allDown.sessionMfePct,0);
});

test('terminal auction close is a separate confirmation and may be a 30m endpoint',()=>{
  const out=setup([raw('11:29'),raw('11:30',106)],'11:30');
  assert.equal(out.decisionPrice,106); // auction at the decision is the latest causal price.
  assert.equal(out.futureAuctionCount,0); assert.equal(out.corrected30Evaluable,0);
  const prior=setup([raw('10:59'),raw('11:30',106)],'11:00');
  assert.equal(prior.corrected30EndpointKind,'TERMINAL_AUCTION_CLOSE');
});

test('future interval must start at or after decision',()=>{
  const out=setup([raw('09:29',100,{high:106}),raw('09:30',100),raw('09:34',100)]);
  assert.equal(out.highOpportunity5,0);
});
