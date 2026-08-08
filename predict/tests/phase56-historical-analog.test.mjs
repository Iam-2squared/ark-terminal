import assert from 'node:assert/strict';
import { findHistoricalAnalogs, PHASE56_ANALOG_SAFETY } from '../chart/phase56-historical-analog.js';

function makeBars(n=140){
  const out=[];
  let close=100;
  for(let i=0;i<n;i++){
    const drift=Math.sin(i/7)*0.8 + (i%11===0?1.1:0.15);
    const open=close;
    close=Math.max(1,close+drift);
    out.push({sessionDate:`2026-01-${String((i%28)+1).padStart(2,'0')}-${i}`,open,high:Math.max(open,close)+1,low:Math.min(open,close)-1,close,volume:100000+i*1000});
  }
  return out;
}

const bars=makeBars();
const asOfIndex=110;
const horizon=5;
const r=findHistoricalAnalogs({bars,asOfIndex,horizon,topK:12});
assert.equal(r.status,'ANALOGS_READY');
assert.equal(r.pointInTime,true);
assert.ok(r.sampleCount>0);
assert.ok(r.maxOutcomeIndexUsed<=asOfIndex,'analog outcomes must never use information after asOf');
for(const a of r.analogs) assert.ok(a.index+horizon<=asOfIndex,'every candidate outcome must be resolved by asOf');
assert.equal(r.executionAllowed,false);
assert.equal(r.brokerWriteAllowed,false);
assert.equal(r.excelOrderWriteAllowed,false);
assert.equal(r.rssOrderFunctionAllowed,false);
assert.equal(r.liveTradingAllowed,false);
assert.equal(r.automaticPromotionAllowed,false);
assert.equal(r.productionUpdateAllowed,false);
assert.equal(r.transmitted,false);
assert.equal(PHASE56_ANALOG_SAFETY.executionAllowed,false);

const insufficient=findHistoricalAnalogs({bars:bars.slice(0,20)});
assert.equal(insufficient.status,'INSUFFICIENT_DATA');
assert.equal(insufficient.executionAllowed,false);

const invalid=findHistoricalAnalogs({bars,asOfIndex:5});
assert.equal(invalid.status,'INVALID_ASOF');
assert.equal(invalid.executionAllowed,false);

console.log('phase56 historical analog tests passed');
