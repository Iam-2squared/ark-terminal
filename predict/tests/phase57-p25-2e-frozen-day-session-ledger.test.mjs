import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildP252FrozenDaySessionLedger,
  PHASE57_P25_2E_SAFETY,
} from '../daytrade/phase57-p25-2e-frozen-day-session-ledger.js';

const FROZEN5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);
const D40=D50.slice(0,40);
const D30=D50.slice(0,30);

function universe(){
  return {
    ready:true,
    sessionDate:'2026-08-19',
    variants:{
      FIXED_5:FROZEN5,
      OLD_FIXED_30:OLD30,
      DYNAMIC_30:D30,
      DYNAMIC_40:D40,
      DYNAMIC_50:D50,
    },
    rankAudit:{
      day50:D50.map((symbol,index)=>({symbol,sector:`S${index%8}`})),
    },
  };
}

function result(symbol,featureCutoff='2026-08-19T00:30:00.000Z',{
  direction=0,
  signalEligible=false,
  probability=0.51,
  confidence=0.51,
}={}){
  return {
    status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
    policyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
    currentSymbol:symbol,
    snapshot:{
      asOf:featureCutoff,
      context:{sourceBarCloseAt:'2026-08-19T00:35:00.000Z'},
    },
    phase57:{
      status:signalEligible?'PROSPECTIVE_PHASE57_FROZEN_SIGNAL_READY':'PROSPECTIVE_PHASE57_FROZEN_WAIT_READY',
      modelId:'phase57-p21-prospective-logit-h6',
      artifactSha256:'a'.repeat(64),
      decision:{
        direction,
        confidence,
        setup:'TECHNICAL',
        asOf:featureCutoff,
        frozenByPhase57:true,
        pointInTimeOnly:true,
        futureOutcomeUsed:false,
        thresholdSearchAfterCapture:false,
        entryRetunedAfterCapture:false,
        context:{
          probability,
          signalEligible,
          selectedHorizonBars:signalEligible?6:null,
          selectedFeatureFamily:signalEligible?'TECHNICAL':null,
          selectedModelType:signalEligible?'LOGISTIC_REGRESSION':null,
          selectedConfigId:signalEligible?'LOGIT':null,
          selectedThreshold:signalEligible?0.55:null,
        },
      },
    },
    provenance:{
      currentSymbol:symbol,
      currentFeatureCutoff:featureCutoff,
      currentSessionDate:'2026-08-19',
    },
  };
}

function targetUnion(){
  return [...new Set([...FROZEN5,...OLD30,...D50])].sort();
}

test('complete target-union cutoff freezes signals and preserves exact five-variant denominators',()=>{
  const symbols=targetUnion();
  const rows=symbols.map(symbol=>result(symbol));
  rows[0]=result(symbols[0],undefined,{direction:1,signalEligible:true,probability:0.72,confidence:0.72});
  rows[1]=result(symbols[1],undefined,{direction:-1,signalEligible:true,probability:0.31,confidence:0.69});
  const ledger=buildP252FrozenDaySessionLedger({universeRecord:universe(),phase57Results:rows});
  assert.equal(ledger.status,'FROZEN_DAY_SESSION_LEDGER_READY');
  assert.equal(ledger.frozenTargetSymbolCount,85);
  assert.equal(ledger.featureCutoffCount,1);
  assert.equal(ledger.completeFeatureCutoffCount,1);
  assert.equal(ledger.rawFrozenSignalCount,2);
  assert.equal(ledger.comparisonEligibleFrozenSignalCount,2);
  assert.equal(ledger.frozenTrades.length,2);
  assert.ok(ledger.frozenTrades.every(x=>x.entryAccepted===true&&x.outcomePending===true&&x.currentOutcomeUsed===false));
  assert.deepEqual(ledger.eligibleDecisionCountsByVariant,{
    FIXED_5:5,
    OLD_FIXED_30:30,
    DYNAMIC_30:30,
    DYNAMIC_40:40,
    DYNAMIC_50:50,
  });
});

test('partial cutoff keeps the signal as audit evidence but excludes it from comparison trades',()=>{
  const rows=[
    result('1001.T',undefined,{direction:1,signalEligible:true,probability:0.8,confidence:0.8}),
    result('1002.T'),
  ];
  const ledger=buildP252FrozenDaySessionLedger({universeRecord:universe(),phase57Results:rows});
  assert.equal(ledger.status,'FROZEN_DAY_SESSION_LEDGER_PARTIAL');
  assert.equal(ledger.rawFrozenSignalCount,1);
  assert.equal(ledger.comparisonEligibleFrozenSignalCount,0);
  assert.equal(ledger.frozenTrades.length,0);
  assert.equal(ledger.cutoffAudit[0].complete,false);
  assert.equal(ledger.cutoffAudit[0].scoredTargetCount,2);
  assert.equal(ledger.cutoffAudit[0].missingSymbols.length,83);
  assert.equal(ledger.decisionAttempts.find(x=>x.symbol==='1001.T').signalEligible,true);
});

test('later complete cutoff is comparison eligible while earlier partial cutoff remains visible',()=>{
  const symbols=targetUnion();
  const early=[result('1001.T','2026-08-19T00:25:00.000Z',{direction:1,signalEligible:true,probability:0.77,confidence:0.77})];
  const complete=symbols.map(symbol=>result(symbol,'2026-08-19T00:30:00.000Z'));
  const index=complete.findIndex(x=>x.currentSymbol==='1001.T');
  complete[index]=result('1001.T','2026-08-19T00:30:00.000Z',{direction:1,signalEligible:true,probability:0.75,confidence:0.75});
  const ledger=buildP252FrozenDaySessionLedger({universeRecord:universe(),phase57Results:[...early,...complete]});
  assert.equal(ledger.featureCutoffCount,2);
  assert.equal(ledger.completeFeatureCutoffCount,1);
  assert.equal(ledger.rawFrozenSignalCount,2);
  assert.equal(ledger.frozenTrades.length,1);
  assert.equal(ledger.frozenTrades[0].entryTimestamp,'2026-08-19T00:30:00.000Z');
});

test('current outcome fields are rejected before ledger creation',()=>{
  const poisoned=result('1001.T');
  poisoned.snapshot.netReturnPct=99;
  assert.throws(
    ()=>buildP252FrozenDaySessionLedger({universeRecord:universe(),phase57Results:[poisoned]}),
    /forbidden current outcome fields/,
  );
});

test('symbols outside the frozen five-variant target union fail closed',()=>{
  assert.throws(
    ()=>buildP252FrozenDaySessionLedger({universeRecord:universe(),phase57Results:[result('9999.T')]}),
    /outside frozen P25\.2 target union/,
  );
});

test('duplicate symbol and feature-cutoff decisions fail closed',()=>{
  const row=result('1001.T');
  assert.throws(
    ()=>buildP252FrozenDaySessionLedger({universeRecord:universe(),phase57Results:[row,row]}),
    /duplicate Phase57 decision/,
  );
});

test('Phase57 signal cannot be relabeled when signalEligible and direction disagree',()=>{
  assert.throws(
    ()=>buildP252FrozenDaySessionLedger({
      universeRecord:universe(),
      phase57Results:[result('1001.T',undefined,{direction:1,signalEligible:false,probability:0.8,confidence:0.8})],
    }),
    /non-WAIT Phase57 direction must be signalEligible/,
  );
});

test('all execution, broker, Excel, RSS-order and promotion surfaces remain disabled',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','freshHoldoutConsumed',
  ])assert.equal(PHASE57_P25_2E_SAFETY[key],false,key);
});
