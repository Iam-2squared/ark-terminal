import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateOosAdaptiveFusion, PHASE56_FUSION_SAFETY } from '../chart/phase56-oos-adaptive-fusion.js';

function trendBars(step=.8,n=80){
  return Array.from({length:n},(_,i)=>({
    open:100+i*step,
    high:101+i*step,
    low:99+i*step,
    close:100.6+i*step,
    volume:1000+i*10,
    vwap:100+i*step,
  }));
}

test('keeps fusion research-only when a selective signal survives regime filter',()=>{
  const r=evaluateOosAdaptiveFusion({bars:trendBars(),horizon:1,minimumScore:2,minimumMargin:1});
  assert.ok(['FUSION_REVIEW_CANDIDATE','ABSTAIN'].includes(r.status));
  assert.equal(r.executionAllowed,false);
  assert.equal(r.paperTradingAllowed,false);
});

test('fails closed when pattern OOS evidence is required but missing',()=>{
  const r=evaluateOosAdaptiveFusion({bars:trendBars(),horizon:1,minimumScore:2,minimumMargin:1,requirePatternEvidence:true,patternOosEvidence:[]});
  if(r.status==='ABSTAIN' && r.reason==='PATTERN_OOS_EVIDENCE_MISSING') assert.equal(r.signal,0);
  assert.equal(r.executionAllowed,false);
});

test('safety forbids all write and live surfaces',()=>{
  assert.equal(PHASE56_FUSION_SAFETY.brokerWriteAllowed,false);
  assert.equal(PHASE56_FUSION_SAFETY.excelOrderWriteAllowed,false);
  assert.equal(PHASE56_FUSION_SAFETY.rssOrderFunctionAllowed,false);
  assert.equal(PHASE56_FUSION_SAFETY.liveTradingAllowed,false);
  assert.equal(PHASE56_FUSION_SAFETY.automaticPromotionAllowed,false);
  assert.equal(PHASE56_FUSION_SAFETY.productionUpdateAllowed,false);
});
