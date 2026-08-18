import assert from 'node:assert/strict';
import test from 'node:test';
import {
  accumulateP252MultiSessionEvidence,
  PHASE57_P25_2H_SAFETY,
} from '../daytrade/phase57-p25-2h-multisession-evidence-accumulator.js';

const FROZEN5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);
function universe(sessionDate){return {ready:true,sessionDate,variants:{FIXED_5:FROZEN5,OLD_FIXED_30:OLD30,DYNAMIC_30:D50.slice(0,30),DYNAMIC_40:D50.slice(0,40),DYNAMIC_50:D50},rankAudit:{day50:D50.map(x=>({symbol:x,sector:'Tech'}))}};}
function frozen(symbol,sessionDate,variantMemberships){return {entryAccepted:true,symbol,sessionDate,entryTimestamp:`${sessionDate}T00:30:00.000Z`,featureCutoff:`${sessionDate}T00:30:00.000Z`,signalDirection:1,baseHorizonBars:1,sector:'Tech',variantMemberships,frozenBeforeOutcome:true,currentOutcomeUsed:false,outcomePending:true};}
function resolved(row,net=1){return {...row,netReturnPct:net,alignedReturnPct:net+0.05,grossReturnPct:net+0.05,hit:net+0.05>0,timeBucket:'09:00-09:59',regime:'RISK_ON',outcomePending:false};}
function packet(sessionDate,{includeFixed=true,unresolved=false}={}){
  const dynamic=frozen('1001.T',sessionDate,['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50']);
  const fixed=frozen('7203.T',sessionDate,['FIXED_5']);
  const trades=includeFixed?[dynamic,fixed]:[dynamic];
  return {
    sessionDate,
    universeRecord:universe(sessionDate),
    ledger:{
      sessionDate,
      frozenTrades:trades,
      eligibleDecisionCountsByVariant:{FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50},
    },
    outcomes:{
      resolvedTrades:trades.map(x=>resolved(x)),
      unresolvedTrades:unresolved?[{...dynamic,outcomeStatus:'UNRESOLVED_TEST'}]:[],
    },
    blockedDecisions:unresolved?[{symbol:'1002.T',status:'BLOCKED_TEST'}]:[],
  };
}

test('multi-session accumulator keeps performance on ready sessions but operational pace counts a missing expected day as zero',()=>{
  const result=accumulateP252MultiSessionEvidence({
    sessionPackets:[packet('2026-08-19'),packet('2026-08-20',{includeFixed:false,unresolved:true})],
    expectedSessionDates:['2026-08-19','2026-08-20','2026-08-21'],
  });
  assert.equal(result.status,'P25_2_MULTISESSION_EVIDENCE_ACCUMULATED');
  assert.equal(result.readySessionCount,2);
  assert.equal(result.expectedTradingSessionCount,3);
  assert.equal(result.missingExpectedSessionCount,1);
  assert.deepEqual(result.missingExpectedSessions,['2026-08-21']);
  assert.equal(result.comparison.commonReadySessionCount,2);
  assert.equal(result.operationalTradeFrequency.DYNAMIC_30.validFrozenEntries,2);
  assert.equal(result.operationalTradeFrequency.DYNAMIC_30.tradingSessions,3);
  assert.ok(Math.abs(result.operationalTradeFrequency.DYNAMIC_30.validFrozenEntriesPerTradingSession-2/3)<1e-12);
  assert.equal(result.operationalTradeFrequency.FIXED_5.validFrozenEntries,1);
  assert.ok(Math.abs(result.operationalTradeFrequency.FIXED_5.validFrozenEntriesPerTradingSession-1/3)<1e-12);
  assert.equal(result.operationalTradeFrequency.DYNAMIC_30.observedDaysToTarget,null);
  assert.equal(result.operationalTradeFrequency.DYNAMIC_30.byTradingSession[2].validFrozenEntries,0);
  assert.equal(result.operationalTradeFrequency.DYNAMIC_30.byTradingSession[2].packetReady,false);
  assert.equal(result.unresolvedBySession['2026-08-20'].length,1);
  assert.equal(result.blockedBySession['2026-08-20'].length,1);
});

test('eligible-decision denominators are summed without changing variant definitions',()=>{
  const result=accumulateP252MultiSessionEvidence({sessionPackets:[packet('2026-08-19'),packet('2026-08-20')]});
  assert.deepEqual(result.aggregateEligibleDecisionCountsByVariant,{FIXED_5:10,OLD_FIXED_30:60,DYNAMIC_30:60,DYNAMIC_40:80,DYNAMIC_50:100});
  assert.equal(result.comparison.results.DYNAMIC_30.coverage,0.033333);
  assert.equal(result.comparison.results.FIXED_5.coverage,0.2);
  assert.equal(result.methodology.currentOuterOosDoesNotSelectDynamicN,true);
});

test('duplicate session packets fail closed',()=>{
  assert.throws(()=>accumulateP252MultiSessionEvidence({sessionPackets:[packet('2026-08-19'),packet('2026-08-19')]}),/duplicate P25\.2 session packet/);
});

test('packet outside predeclared expected session set fails closed',()=>{
  assert.throws(()=>accumulateP252MultiSessionEvidence({
    sessionPackets:[packet('2026-08-20')],
    expectedSessionDates:['2026-08-19'],
  }),/outside predeclared expectedSessionDates/);
});

test('all execution and promotion surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_2H_SAFETY[key],false,key);
});
