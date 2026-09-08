import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {Phase57CapacityV2Internals as I} from '../../scripts/run_phase57_selector_capacity_v2.mjs';

const days=(count,start='2025-04-15')=>{const result=[];let d=new Date(`${start}T00:00:00Z`);while(result.length<count){if(![0,6].includes(d.getUTCDay()))result.push({Date:d.toISOString().slice(0,10),HolDiv:'1'});d=new Date(d.getTime()+86400000);}return result;};

test('materializes exact chronological 60/1/29/1/29 split and preserves 162',()=>{
  const allocation=I.buildAllocation(days(282));
  assert.equal(allocation.development.length,60);
  assert.equal(allocation.validation.length,29);
  assert.equal(allocation.untouchedOos.length,29);
  assert.equal(allocation.remainingReserve.sessionCount,162);
  assert.equal(new Set(I.allocationRows(allocation).map(r=>r.sessionDate)).size,120);
});

test('ridge prediction is deterministic',()=>{
  const centers=[0,0,0,0],scales=[1,1,1,1];
  const rows=Array.from({length:120},(_,i)=>({features:{hybridQualityDecayRank5To1:i/120,qualifiedCandidateCount:10,marketBreadth:.5,dataQualityConfidence:1},targets:{RANK_6_10:i/10}}));
  const model={...I.fitRidge(rows,'RANK_6_10',1,centers,scales),centers,scales};
  assert.equal(I.predict(model,rows[10].features),I.predict(model,rows[10].features));
});

test('capacity action is always a frozen action-space prefix length',()=>{
  const layer={coefficients:[100,0,0,0,0],centers:[0,0,0,0],scales:[1,1,1,1]};
  const model={layers:{RANK_6_10:layer,RANK_11_15:layer,RANK_16_20:layer}};
  const row={frozenSelectedCount:5,rankedCount:17,features:{hybridQualityDecayRank5To1:.1,qualifiedCandidateCount:15,marketBreadth:.5,dataQualityConfidence:1}};
  assert.equal(I.capacityFor(row,model,{RANK_6_10:0,RANK_11_15:0,RANK_16_20:0}),17);
  assert.equal(I.capacityFor({...row,frozenSelectedCount:0},model,{RANK_6_10:0,RANK_11_15:0,RANK_16_20:0}),0);
});

test('jump rate counts only changes greater than five',()=>{
  assert.equal(I.jumpRate([5,10,15,20]),0);
  assert.equal(I.jumpRate([5,15,20]),.5);
});

test('development target builder receives the causally filtered future bars',()=>{
  const source=fs.readFileSync(new URL('../../scripts/run_phase57_selector_capacity_v2.mjs',import.meta.url),'utf8');
  assert.match(source,/sessionDate:date,futureBars:future/);
  assert.doesNotMatch(source,/sessionDate:date,futureBars\}\)/);
});
