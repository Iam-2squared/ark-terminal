import assert from 'node:assert/strict';
import test from 'node:test';
import {
  evaluateP252PrecommittedProspectiveComparison,
  PHASE57_P25_2D_SAFETY,
} from '../daytrade/phase57-p25-2d-precommitted-prospective-comparison.js';

const syms=(start,count)=>Array.from({length:count},(_,i)=>`${String(start+i).padStart(4,'0')}.T`);

function record(sessionDate){
  const d50=syms(2000,50);
  return {
    ready:true,
    status:'PROSPECTIVE_PREOPEN_UNIVERSE_FROZEN',
    sessionDate,
    variants:{
      FIXED_5:syms(1000,5),
      OLD_FIXED_30:syms(1000,30),
      DYNAMIC_30:d50.slice(0,30),
      DYNAMIC_40:d50.slice(0,40),
      DYNAMIC_50:d50,
    },
    rankAudit:{day50:d50.map((symbol,i)=>({symbol,sector:`S${i%10}`}))},
  };
}

function trade(sessionDate,symbol,entryTimestamp,netReturnPct,{hit=netReturnPct>0,sector=null}={}){
  return {
    entryAccepted:true,
    sessionDate,
    symbol,
    entryTimestamp,
    netReturnPct,
    alignedReturnPct:netReturnPct+0.05,
    hit,
    regime:'RANGE',
    timeBucket:'09:00-09:59',
    ...(sector?{sector}:{}),
  };
}

test('joins frozen trades to all five precommitted memberships on one common ready-session window',()=>{
  const a=record('2026-08-19'),b=record('2026-08-20');
  const blocked={ready:false,status:'BLOCKED_PROSPECTIVE_PREOPEN_UNIVERSE',sessionDate:'2026-08-21',reason:'PIT_INSUFFICIENT_POINT_IN_TIME_CROSS_SECTION'};
  const trades=[
    trade(a.sessionDate,'1000.T','2026-08-19T00:10:00.000Z',1.0,{sector:'Auto'}),
    trade(a.sessionDate,'2000.T','2026-08-19T00:15:00.000Z',-0.5),
    trade(a.sessionDate,'2035.T','2026-08-19T00:20:00.000Z',0.8),
    trade(a.sessionDate,'2045.T','2026-08-19T00:25:00.000Z',0.2),
    trade(b.sessionDate,'1001.T','2026-08-20T00:10:00.000Z',-0.3,{sector:'Tech'}),
    trade(b.sessionDate,'2025.T','2026-08-20T00:15:00.000Z',0.4),
    trade('2026-08-21','2001.T','2026-08-21T00:10:00.000Z',99),
    trade(a.sessionDate,'9999.T','2026-08-19T00:30:00.000Z',99),
  ];
  const result=evaluateP252PrecommittedProspectiveComparison({universeRecords:[a,b,blocked],frozenTrades:trades});
  assert.deepEqual(result.commonReadySessions,['2026-08-19','2026-08-20']);
  assert.equal(result.blockedUniverseSessions.length,1);
  assert.equal(result.blockedUniverseSessions[0].sessionDate,'2026-08-21');
  assert.equal(result.commonWindowFrozenTrades,7);
  assert.deepEqual(Object.keys(result.results),['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50']);
  assert.equal(result.results.FIXED_5.validFrozenEntries,2);
  assert.equal(result.results.OLD_FIXED_30.validFrozenEntries,2);
  assert.equal(result.results.DYNAMIC_30.validFrozenEntries,2);
  assert.equal(result.results.DYNAMIC_40.validFrozenEntries,3);
  assert.equal(result.results.DYNAMIC_50.validFrozenEntries,4);
  for(const variant of Object.values(result.results))assert.equal(variant.evaluatedTradingSessions,2);
  assert.equal(result.methodology.allFiveVariantsRetained,true);
  assert.equal(result.methodology.universeSizeSelectedFromOuterOos,false);
});

test('does not let a blocked universe session leak its excellent outcome into any variant',()=>{
  const ready=record('2026-08-19');
  const blocked={ready:false,sessionDate:'2026-08-20',status:'BLOCKED',reason:'NO_SNAPSHOT_AT_OR_BEFORE_DECISION'};
  const result=evaluateP252PrecommittedProspectiveComparison({
    universeRecords:[ready,blocked],
    frozenTrades:[
      trade('2026-08-19','2000.T','2026-08-19T00:10:00.000Z',-1),
      trade('2026-08-20','2000.T','2026-08-20T00:10:00.000Z',100),
    ],
  });
  assert.equal(result.results.DYNAMIC_30.validFrozenEntries,1);
  assert.equal(result.results.DYNAMIC_30.afterCostNetPct,-1);
  assert.equal(result.blockedUniverseSessions.length,1);
});

test('rejects duplicate frozen trade identities instead of overcounting them',()=>{
  const r=record('2026-08-19');
  const t=trade(r.sessionDate,'2000.T','2026-08-19T00:10:00.000Z',1);
  assert.throws(()=>evaluateP252PrecommittedProspectiveComparison({universeRecords:[r],frozenTrades:[t,{...t,netReturnPct:2}]}),/duplicate frozen trade row/);
});

test('rejects a ready record whose dynamic 30/40/50 are not nested prefixes',()=>{
  const r=record('2026-08-19');
  r.variants.DYNAMIC_40=[...r.variants.DYNAMIC_40];
  [r.variants.DYNAMIC_40[0],r.variants.DYNAMIC_40[1]]=[r.variants.DYNAMIC_40[1],r.variants.DYNAMIC_40[0]];
  assert.throws(()=>evaluateP252PrecommittedProspectiveComparison({universeRecords:[r],frozenTrades:[]}),/not nested/);
});

test('keeps all execution and promotion surfaces disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_2D_SAFETY[key],false,key);
  }
});
