import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateEntryResearchOos, PHASE56_4_SAFETY } from '../chart/phase56-entry-oos-validation.js';

function goodRows(count=80){
  const rows=[];
  let price=100;
  for(let i=0;i<count;i++){
    const long=i%4!==0;
    rows.push({time:`2026-08-${String(Math.floor(i/24)+1).padStart(2,'0')}T${String(i%24).padStart(2,'0')}:00:00Z`,state:long?'RESEARCH_CANDIDATE_LONG':'WAIT',close:price});
    price += long ? 0.8 : 0.1;
  }
  return rows;
}

test('Phase56.4 promotes only to read-only OOS review candidate',()=>{
  const result=evaluateEntryResearchOos({rows:goodRows(),foldCount:4,minimumSamplesPerFold:5,minimumPassingFolds:3,horizonBars:1,minimumPrecision:0.55});
  assert.equal(result.status,'ENTRY_OOS_REVIEW_CANDIDATE');
  assert.ok(result.passingFolds>=3);
  assert.equal(result.executionAllowed,false);
  assert.equal(result.paperTradingAllowed,false);
  assert.equal(result.transmitted,false);
});

test('Phase56.4 blocks unstable research states',()=>{
  const rows=Array.from({length:40},(_,i)=>({time:String(i).padStart(3,'0'),state:'RESEARCH_CANDIDATE_LONG',close:100+(i%2===0?i:-i)}));
  const result=evaluateEntryResearchOos({rows,foldCount:4,minimumSamplesPerFold:5,minimumPassingFolds:3,horizonBars:1,minimumPrecision:0.8});
  assert.equal(result.status,'OBSERVE');
  assert.ok(result.blockers.includes('ENTRY_SIGNAL_STABILITY_NOT_PROVEN'));
});

test('Phase56.4 safety remains fully read only',()=>{
  assert.equal(PHASE56_4_SAFETY.executionAllowed,false);
  assert.equal(PHASE56_4_SAFETY.brokerWriteAllowed,false);
  assert.equal(PHASE56_4_SAFETY.excelOrderWriteAllowed,false);
  assert.equal(PHASE56_4_SAFETY.rssOrderFunctionAllowed,false);
  assert.equal(PHASE56_4_SAFETY.liveTradingAllowed,false);
  assert.equal(PHASE56_4_SAFETY.paperTradingAllowed,false);
});
