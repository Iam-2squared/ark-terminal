import test from 'node:test';
import assert from 'node:assert/strict';
import {buildFourTrackDurable} from '../../scripts/package_p25_four_track_durable.mjs';

const safety=()=>({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});
const measurement={status:'MARKETWIDE_DYNAMIC_5M_MEASUREMENT_READY',inputSymbols:3697,selectedCount:36,safety:safety()};
const snapshot={bucket:'2026-08-27T09:05:00.000Z',symbolCount:3697,stateHash:'abc',methodology:{pointInTimeOnly:true,deduplicated:true},safety:safety()};
const laneC={status:'LANE_C_CAPITAL_EFFICIENCY_DIAGNOSTIC_READY',evidenceClass:'LEGACY27_DIAGNOSTIC_ONLY',interpretation:{winnerSelectionAllowed:false,formalOos:false,promotionEligible:false},safety:safety()};

test('four-track package binds durable references and remains research-only',()=>{
  const x=buildFourTrackDurable({measurement,marketwideNdjson:JSON.stringify(snapshot)+'\n',laneC,entryRef:'automation/p25-evaluation-data@abc',exitRef:'automation/p25-exit-v3-data@def',selectionRef:'automation/p25-four-track-data',laneCRef:'automation/p25-lane-c-data@ghi',sourceRunId:'123'});
  assert.equal(x.status,'FOUR_TRACK_DURABLE_EVIDENCE_READY');
  assert.equal(x.tracks.entry.status,'DURABLE_EXISTING');
  assert.equal(x.tracks.dynamic5m.status,'DURABLE_APPEND_ONLY');
  assert.equal(x.tracks.exitV3.status,'DURABLE_EXISTING');
  assert.equal(x.tracks.capitalAllocation.status,'DURABLE_APPEND_ONLY');
  assert.equal(x.interpretation.winnerSelectionAllowed,false);
  for(const [k,v] of Object.entries(x.safety))assert.equal(v,false,k);
});

test('fails closed when market-wide evidence is too small',()=>{
  assert.throws(()=>buildFourTrackDurable({measurement:{...measurement,inputSymbols:80},marketwideNdjson:JSON.stringify(snapshot),laneC,entryRef:'a',exitRef:'b',selectionRef:'c',laneCRef:'d',sourceRunId:'1'}),/not market-wide/);
});
