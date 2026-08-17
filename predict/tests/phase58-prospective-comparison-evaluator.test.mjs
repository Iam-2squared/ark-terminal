import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {
  evaluatePhase58ProspectiveComparison,
  PHASE58_P26_EVIDENCE_POLICY,
  PHASE58_P26_SAFETY,
} from '../scalping/phase58-prospective-comparison-evaluator.js';

const HASH='a'.repeat(64);
const SAFE=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

function artifact(seed){
  return crypto.createHash('sha256').update(String(seed)).digest('hex');
}

function row({at,direction=0,price=100,seed='x',horizonBars=1,testAction='CONFIRM_PHASE57_ENTRY',symbol='7203.T'}={}){
  const spread=0.02;
  return {
    schemaVersion:2,
    phase:'58.p9.sync-capture',
    sourceMode:'MARKETSPEED_II_RSS_READ_ONLY',
    capturedAt:at,
    symbol,
    tickOrder:'DESC',
    market:{bestBid:price-spread/2,bestAsk:price+spread/2,bestBidSize:1000,bestAskSize:1000,spreadBps:spread/price*10000},
    orderBook:{
      asks:Array.from({length:10},(_,i)=>({level:i+1,price:price+spread/2+i*.01,size:1000})),
      bids:Array.from({length:10},(_,i)=>({level:i+1,price:price-spread/2-i*.01,size:1000})),
    },
    ticks:[{time:'09:00:02',price:price+.01,volume:100},{time:'09:00:01',price,size:100}],
    phase57Snapshot:{
      direction,confidence:direction===0?.51:.7,setup:'MOMENTUM',context:{selectedHorizonBars:horizonBars},
      asOf:at,modelId:`model-${seed}`,artifactSha256:artifact(seed),frozen:true,
      futureOutcomeUsed:false,thresholdSearchAfterCapture:false,entryRetunedAfterCapture:false,
    },
    methodology:{
      phase57DirectionIsFrozenBase:true,phase58MayConfirmDeferOrAbstainOnly:true,phase58MayReverseDirection:false,
      pointInTimeOnly:true,futureOutcomeUsed:false,historicalDecisionReconstructionAllowed:false,sameCaptureBoundary:true,freshHoldoutConsumed:false,
    },
    safety:{...SAFE},
    testAction,
  };
}

const overlayFromTestAction=(rows,index)=>({action:rows[index].testAction});
const evaluate=rows=>evaluatePhase58ProspectiveComparison({rows,datasetSha256:HASH,overlayActionForIndex:overlayFromTestAction});

test('Phase57 WAIT stays WAIT and never becomes an overlay entry',()=>{
  const result=evaluate([
    row({at:'2026-08-18T00:00:00.000Z',direction:0,seed:'wait-a'}),
    row({at:'2026-08-18T00:05:00.000Z',direction:0,seed:'wait-b',price:101}),
  ]);
  assert.equal(result.complete,true);
  assert.equal(result.decisionEventCount,0);
  assert.equal(result.waitDecisionCount,2);
  assert.equal(result.formalNonOverlappingEventCount,0);
  assert.equal(result.methodology.waitMayBecomeEntry,false);
  assert.equal(result.methodology.phase58MayReverseDirection,false);
});

test('outcome is pending until a synchronized same-symbol row reaches the frozen horizon',()=>{
  const candidate=row({at:'2026-08-18T00:00:00.000Z',direction:1,seed:'candidate',horizonBars:1});
  const early=row({at:'2026-08-18T00:04:59.000Z',direction:0,seed:'early',price:101});
  const pending=evaluate([candidate,early]);
  assert.equal(pending.pendingEventCount,1);
  assert.equal(pending.maturedEventCount,0);

  const mature=row({at:'2026-08-18T00:05:00.000Z',direction:0,seed:'mature',price:101});
  const measured=evaluate([candidate,early,mature]);
  assert.equal(measured.pendingEventCount,0);
  assert.equal(measured.maturedEventCount,1);
  assert.equal(measured.formalNonOverlapping.baseline.entryCount,1);
  assert.equal(measured.eventAudit[0].baselineExitAt,'2026-08-18T00:05:00.000Z');
});

test('Phase58 filtering is measured against the same frozen Phase57 direction without reversal',()=>{
  const losing=row({at:'2026-08-18T00:00:00.000Z',direction:1,seed:'lose',horizonBars:1,testAction:'ABSTAIN_LIQUIDITY_SHOCK'});
  const outcome=row({at:'2026-08-18T00:05:00.000Z',direction:0,seed:'outcome',price:99});
  const result=evaluate([losing,outcome]);
  assert.equal(result.eventAudit[0].direction,1);
  assert.equal(result.eventAudit[0].overlayAction,'ABSTAIN_LIQUIDITY_SHOCK');
  assert.equal(result.formalNonOverlapping.baseline.entryCount,1);
  assert.equal(result.formalNonOverlapping.phase57PlusPhase58.entryCount,0);
  assert.equal(result.formalNonOverlapping.overlayCoveragePct,0);
  assert.equal(result.formalNonOverlapping.falseEntryReductionPct,100);
  assert.equal(result.promotionEvidence,false);
});

test('formal evidence remains insufficient below the predeclared sample/session floor',()=>{
  const result=evaluate([
    row({at:'2026-08-18T00:00:00.000Z',direction:1,seed:'one'}),
    row({at:'2026-08-18T00:05:00.000Z',direction:0,seed:'one-outcome',price:101}),
  ]);
  assert.equal(result.status,'PHASE58_PROSPECTIVE_COMPARISON_INSUFFICIENT_EVIDENCE');
  assert.equal(result.evidence.ready,false);
  assert.equal(result.formalNonOverlappingEventCount,1);
  assert.equal(result.evidence.minFormalNonOverlappingEvents,30);
  assert.equal(result.evidence.minDistinctSessions,3);
  assert.equal(result.evidence.thresholdSearchAllowed,false);
  assert.equal(result.evidence.postHocOptimizationAllowed,false);
});

test('30 non-overlapping events across 3 sessions satisfy only the evaluator evidence floor, never promotion',()=>{
  const rows=[];
  let seed=0;
  for(let day=18;day<=20;day+=1){
    const dayStart=Date.parse(`2026-08-${day}T00:00:00.000Z`);
    for(let event=0;event<10;event+=1){
      const start=new Date(dayStart+event*6*60*1000).toISOString();
      const end=new Date(dayStart+(event*6+5)*60*1000).toISOString();
      rows.push(row({at:start,direction:event%2===0?1:-1,seed:`signal-${seed}`,price:100,horizonBars:1}));
      const outcomePrice=event%2===0?101:99;
      rows.push(row({at:end,direction:0,seed:`outcome-${seed}`,price:outcomePrice}));
      seed+=1;
    }
  }
  rows.sort((a,b)=>Date.parse(a.capturedAt)-Date.parse(b.capturedAt));
  const result=evaluate(rows);
  assert.equal(result.status,'PHASE58_PROSPECTIVE_COMPARISON_EVIDENCE_READY');
  assert.equal(result.formalNonOverlappingEventCount,30);
  assert.equal(result.stability.distinctSessions,3);
  assert.equal(result.formalNonOverlapping.baseline.entryCount,30);
  assert.equal(result.formalNonOverlapping.phase57PlusPhase58.entryCount,30);
  assert.equal(result.formalNonOverlapping.overlayCoveragePct,100);
  assert.equal(result.evidence.ready,true);
  assert.equal(result.promotionEvidence,false);
  assert.equal(result.recommendationAllowed,false);
});

test('unsafe flags and unknown tick order fail closed',()=>{
  const bad=row({at:'2026-08-18T00:00:00.000Z',direction:1,seed:'bad'});
  bad.safety.brokerWriteAllowed=true;
  bad.tickOrder='UNKNOWN';
  const result=evaluate([bad]);
  assert.equal(result.complete,false);
  assert.equal(result.status,'BLOCKED_DATASET_INTEGRITY');
  assert.ok(result.blockers.includes('ROW_1_UNSAFE_brokerWriteAllowed'));
  assert.ok(result.blockers.includes('ROW_1_UNKNOWN_TICK_ORDER'));
});

test('P26 safety and methodology remain READ ONLY research only',()=>{
  assert.equal(PHASE58_P26_EVIDENCE_POLICY.thresholdSearchAllowed,false);
  assert.equal(PHASE58_P26_EVIDENCE_POLICY.postHocOptimizationAllowed,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE58_P26_SAFETY[key],false,key);
  }
});
