import assert from 'node:assert/strict';
import test from 'node:test';
import {
  replayP252FrozenDaySession,
  PHASE57_P25_2F_SAFETY,
} from '../daytrade/phase57-p25-2f-postsession-point-in-time-replay.js';

const FROZEN5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);
const D40=D50.slice(0,40),D30=D50.slice(0,30);
function universe(){
  return {
    ready:true,
    sessionDate:'2026-08-19',
    variants:{FIXED_5:FROZEN5,OLD_FIXED_30:OLD30,DYNAMIC_30:D30,DYNAMIC_40:D40,DYNAMIC_50:D50},
    rankAudit:{day50:D50.map((symbol,index)=>({symbol,sector:`S${index%7}`}))},
  };
}
function targets(){return [...new Set([...FROZEN5,...OLD30,...D50])].sort();}
function sixBars(){
  return Array.from({length:6},(_,i)=>({
    timestamp:`2026-08-19T00:${String(i*5).padStart(2,'0')}:00.000Z`,
    open:100+i,high:101+i,low:99+i,close:100.5+i,volume:1000+i*10,
  }));
}
function barsBySymbol(){return Object.fromEntries(targets().map(symbol=>[symbol,sixBars()]));}
function scorer({currentPrefix,symbol,featureCutoff}){
  assert.equal(currentPrefix.bars5m.at(-1).timestamp,featureCutoff);
  assert.ok(currentPrefix.bars5m.every(bar=>bar.timestamp<=featureCutoff));
  const signal=symbol==='1001.T';
  return {
    complete:true,
    status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
    policyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
    currentSymbol:symbol,
    snapshot:{asOf:featureCutoff,context:{sourceBarCloseAt:'2026-08-19T00:30:00.000Z'}},
    phase57:{
      status:signal?'PROSPECTIVE_PHASE57_FROZEN_SIGNAL_READY':'PROSPECTIVE_PHASE57_FROZEN_WAIT_READY',
      modelId:'phase57-p21-prospective-logit-h6',
      artifactSha256:'b'.repeat(64),
      decision:{
        direction:signal?1:0,
        confidence:signal?0.72:0.51,
        setup:signal?'TECHNICAL':null,
        asOf:featureCutoff,
        frozenByPhase57:true,
        pointInTimeOnly:true,
        futureOutcomeUsed:false,
        thresholdSearchAfterCapture:false,
        entryRetunedAfterCapture:false,
        context:{
          probability:signal?0.72:0.51,
          signalEligible:signal,
          selectedHorizonBars:signal?6:null,
          selectedFeatureFamily:signal?'TECHNICAL':null,
          selectedModelType:signal?'LOGISTIC_REGRESSION':null,
          selectedConfigId:signal?'LOGIT':null,
          selectedThreshold:signal?0.55:null,
        },
      },
    },
    provenance:{currentSymbol:symbol,currentFeatureCutoff:featureCutoff,currentSessionDate:'2026-08-19'},
  };
}

test('after-session replay exposes only each completed prefix and creates one fair complete cutoff',()=>{
  const replay=replayP252FrozenDaySession({
    universeRecord:universe(),
    historicalSessions:[],
    sessionBarsBySymbol:barsBySymbol(),
    scorePrefix:scorer,
  });
  assert.equal(replay.status,'POSTSESSION_POINT_IN_TIME_REPLAY_COMPLETE');
  assert.equal(replay.targetSymbolCount,85);
  assert.equal(replay.commonFairCutoffCount,1);
  assert.deepEqual(replay.commonFairCutoffs,['2026-08-19T00:25:00.000Z']);
  assert.equal(replay.scorerCallCount,85);
  assert.equal(replay.blockedDecisionCount,0);
  assert.equal(replay.ledger.status,'FROZEN_DAY_SESSION_LEDGER_READY');
  assert.equal(replay.ledger.comparisonEligibleFrozenSignalCount,1);
  assert.equal(replay.ledger.frozenTrades[0].symbol,'1001.T');
  assert.equal(replay.methodology.eachScorerReceivesPrefixOnly,true);
  assert.equal(replay.methodology.futureBarsPassedToScorer,false);
  assert.equal(replay.methodology.replayIsNotClaimedAsLiveWallClockDecision,true);
});

test('a blocked symbol keeps the cutoff visible but prevents partial sweep signals entering comparison',()=>{
  const replay=replayP252FrozenDaySession({
    universeRecord:universe(),
    sessionBarsBySymbol:barsBySymbol(),
    scorePrefix:args=>args.symbol==='1002.T'?{complete:false,status:'BLOCKED_TEST'}:scorer(args),
  });
  assert.equal(replay.commonFairCutoffCount,1);
  assert.equal(replay.blockedDecisionCount,1);
  assert.equal(replay.ledger.status,'FROZEN_DAY_SESSION_LEDGER_PARTIAL');
  assert.equal(replay.ledger.rawFrozenSignalCount,1);
  assert.equal(replay.ledger.comparisonEligibleFrozenSignalCount,0);
  assert.equal(replay.ledger.cutoffAudit[0].complete,false);
  assert.ok(replay.ledger.cutoffAudit[0].missingSymbols.includes('1002.T'));
});

test('no cutoff is declared fair when one target lacks the minimum contemporaneous prefix',()=>{
  const input=barsBySymbol();
  input['1002.T']=input['1002.T'].slice(0,5);
  const replay=replayP252FrozenDaySession({
    universeRecord:universe(),
    sessionBarsBySymbol:input,
    scorePrefix:scorer,
  });
  assert.equal(replay.status,'BLOCKED_NO_COMMON_FAIR_CUTOFF');
  assert.equal(replay.commonFairCutoffCount,0);
  assert.equal(replay.scorerCallCount,0);
  assert.equal(replay.ledger.frozenTrades.length,0);
});

test('outcome-poisoned 5m bars are rejected before any scorer call',()=>{
  const input=barsBySymbol();
  input['1001.T'][2]={...input['1001.T'][2],futureReturnPct:999};
  let calls=0;
  assert.throws(()=>replayP252FrozenDaySession({
    universeRecord:universe(),
    sessionBarsBySymbol:input,
    scorePrefix:args=>{calls+=1;return scorer(args);},
  }),/forbidden outcome fields/);
  assert.equal(calls,0);
});

test('all execution and promotion surfaces remain disabled',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','freshHoldoutConsumed',
  ])assert.equal(PHASE57_P25_2F_SAFETY[key],false,key);
});
