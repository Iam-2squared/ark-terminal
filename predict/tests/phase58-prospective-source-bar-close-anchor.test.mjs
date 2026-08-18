import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {evaluatePhase58ProspectiveComparison} from '../scalping/phase58-prospective-comparison-evaluator.js';

const HASH='b'.repeat(64);
const SAFE={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false};
const artifact=seed=>crypto.createHash('sha256').update(seed).digest('hex');

function row({at,direction=0,seed='x',price=100,horizonBars=1,symbol='7203.0'}={}){
  const spread=.02;
  return {
    schemaVersion:2,phase:'58.p9.sync-capture',sourceMode:'MARKETSPEED_II_RSS_READ_ONLY',capturedAt:at,symbol,tickOrder:'DESC',
    market:{bestBid:price-spread/2,bestAsk:price+spread/2,bestBidSize:1000,bestAskSize:1000,spreadBps:spread/price*10000},
    orderBook:{asks:[],bids:[]},ticks:[],
    phase57Snapshot:{direction,confidence:direction===0?.51:.7,setup:'VOLATILITY',context:{selectedHorizonBars:horizonBars},asOf:at,modelId:`model-${seed}`,artifactSha256:artifact(seed),frozen:true,futureOutcomeUsed:false,thresholdSearchAfterCapture:false,entryRetunedAfterCapture:false},
    methodology:{phase57DirectionIsFrozenBase:true,phase58MayConfirmDeferOrAbstainOnly:true,phase58MayReverseDirection:false,pointInTimeOnly:true,futureOutcomeUsed:false,historicalDecisionReconstructionAllowed:false,sameCaptureBoundary:true,freshHoldoutConsumed:false},
    safety:{...SAFE},
  };
}

test('live P27 lineage anchors a 24-bar horizon to context.sourceBarCloseAt, not first microstructure capture',()=>{
  const candidate=row({at:'2026-08-18T00:51:42.284Z',direction:1,seed:'live',horizonBars:24});
  candidate.phase57Snapshot.asOf='2026-08-18T00:45:00.000Z';
  candidate.phase57Snapshot.context={
    ...candidate.phase57Snapshot.context,
    sourceBarTimestamp:'2026-08-18T00:45:00.000Z',
    sourceBarDurationMinutes:5,
    sourceBarCloseAt:'2026-08-18T00:50:00.000Z',
  };
  const result=evaluatePhase58ProspectiveComparison({rows:[candidate],datasetSha256:HASH});
  assert.equal(result.complete,true);
  assert.equal(result.pendingEventCount,1);
  assert.equal(result.eventAudit[0].symbol,'7203.T');
  assert.equal(result.eventAudit[0].horizonAnchorAt,'2026-08-18T00:50:00.000Z');
  assert.equal(result.eventAudit[0].frozenOutcomeTargetAt,'2026-08-18T03:50:00.000Z');
  assert.equal(result.methodology.frozenHorizonAnchoredToCompletedSourceBarClose,true);
});

test('legacy snapshots without completed-bar metadata keep the conservative capture-time fallback',()=>{
  const candidate=row({at:'2026-08-18T00:51:42.284Z',direction:1,seed:'legacy',horizonBars:1});
  const result=evaluatePhase58ProspectiveComparison({rows:[candidate],datasetSha256:HASH});
  assert.equal(result.complete,true);
  assert.equal(result.eventAudit[0].horizonAnchorAt,'2026-08-18T00:51:42.284Z');
  assert.equal(result.eventAudit[0].frozenOutcomeTargetAt,'2026-08-18T00:56:42.284Z');
});
