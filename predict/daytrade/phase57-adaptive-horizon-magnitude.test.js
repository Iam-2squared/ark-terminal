import test from 'node:test';
import assert from 'node:assert/strict';
import {buildMultiHorizonMagnitudeRows,materializeHorizonRows,scoreMagnitudeSignals,rankHorizonCandidates,PHASE57_P21_SAFETY} from './phase57-adaptive-horizon-magnitude.js';

function bars(n=40){return Array.from({length:n},(_,i)=>({timestamp:new Date(Date.UTC(2026,0,5,0,i*5)).toISOString(),open:100+i*0.1,high:100.2+i*0.1,low:99.8+i*0.1,close:100+i*0.1,volume:1000+i*10}));}

test('builds causal multi-horizon magnitude targets',()=>{
  const rows=buildMultiHorizonMagnitudeRows({symbol:'7203.T',sessionDate:'2026-01-05',bars:bars(),horizons:[1,3,6]});
  assert.ok(rows.length>0);
  const r=rows[0];
  assert.ok(r.targets[1]);
  assert.ok(r.targets[3]);
  assert.ok(r.targets[6]);
  assert.ok(r.featureCutoff<r.targets[6].outcomeAt);
  assert.ok(r.targets[6].mfePct>=r.targets[6].actualReturnPct);
});

test('materializes one horizon without changing point-in-time boundary',()=>{
  const base=buildMultiHorizonMagnitudeRows({symbol:'7203.T',sessionDate:'2026-01-05',bars:bars(),horizons:[3]});
  const rows=materializeHorizonRows(base,3);
  assert.ok(rows.length>0);
  assert.equal(rows[0].horizonBars,3);
  assert.equal(rows[0].label,rows[0].actualReturnPct>=0?1:0);
  assert.ok(rows[0].featureCutoff<rows[0].outcomeAt);
});

test('scores actual magnitude net of round-trip cost',()=>{
  const rows=[{label:1,actualReturnPct:1.2,horizonBars:12},{label:0,actualReturnPct:-0.8,horizonBars:12}];
  const r=scoreMagnitudeSignals(rows,()=>0.9,{threshold:0.55,roundTripCostPct:0.05});
  assert.equal(r.signalCount,2);
  assert.equal(r.hitRate,0.5);
  assert.ok(Math.abs(r.netAverageReturnPct-0.15)<1e-12);
});

test('horizon ranking requires sample sufficiency and positive net',()=>{
  const r=rankHorizonCandidates([{horizonBars:3,signalCount:50,hitRate:0.6,netAverageReturnPct:0.1},{horizonBars:12,signalCount:40,hitRate:0.58,netAverageReturnPct:0.3}],{minimumSignals:30,minimumNetReturnPct:0});
  assert.equal(r.selected.horizonBars,12);
  const abstain=rankHorizonCandidates([{horizonBars:3,signalCount:10,hitRate:0.9,netAverageReturnPct:2}],{minimumSignals:30,minimumNetReturnPct:0});
  assert.equal(abstain.selected,null);
});

test('P21 remains research-only with all write paths disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed']) assert.equal(PHASE57_P21_SAFETY[key],false);
});
