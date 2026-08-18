import assert from 'node:assert/strict';
import test from 'node:test';
import {
  runP252EndToEndProspectiveEvaluation,
  PHASE57_P25_2I_SAFETY,
  PHASE57_P25_2I_POLICY,
} from '../daytrade/phase57-p25-2i-end-to-end-prospective-evaluation.js';

const FIXED5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);

function universe(sessionDate){
  return {
    ready:true,
    sessionDate,
    variants:{FIXED_5:FIXED5,OLD_FIXED_30:OLD30,DYNAMIC_30:D50.slice(0,30),DYNAMIC_40:D50.slice(0,40),DYNAMIC_50:D50},
    rankAudit:{day50:D50.map(symbol=>({symbol,sector:'Tech'}))},
  };
}

function allSymbols(record){return [...new Set(Object.values(record.variants).flat())];}
function bars(sessionDate,count=8){
  const base=Date.parse(`${sessionDate}T00:00:00.000Z`);
  return Array.from({length:count},(_,i)=>({
    timestamp:new Date(base+i*5*60_000).toISOString(),
    open:100+i,
    high:101+i,
    low:99+i,
    close:100.5+i,
    volume:1000+i*10,
  }));
}
function barsBySymbol(record){return Object.fromEntries(allSymbols(record).map(symbol=>[symbol,bars(record.sessionDate)]));}

function scorePrefix({currentPrefix}){
  const asOf=currentPrefix.bars5m.at(-1).timestamp;
  const symbol=currentPrefix.symbol;
  const signal=symbol==='1001.T';
  const decision={
    direction:signal?1:0,
    confidence:signal?0.7:null,
    setup:signal?'TEST':null,
    context:{
      probability:signal?0.7:0.5,
      signalEligible:signal,
      selectedHorizonBars:signal?1:null,
      selectedFeatureFamily:signal?'TEST':null,
      selectedModelType:signal?'LOGIT':null,
      selectedConfigId:signal?'TEST_LOGIT':null,
      selectedThreshold:signal?0.6:null,
    },
    asOf,
    frozenByPhase57:true,
    pointInTimeOnly:true,
    futureOutcomeUsed:false,
    thresholdSearchAfterCapture:false,
    entryRetunedAfterCapture:false,
  };
  return {
    complete:true,
    status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
    policyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
    currentSymbol:symbol,
    snapshot:{symbol,sessionDate:currentPrefix.sessionDate,asOf,context:{sourceBarCloseAt:new Date(Date.parse(asOf)+5*60_000).toISOString()}},
    phase57:{status:signal?'PROSPECTIVE_PHASE57_FROZEN_SIGNAL_READY':'PROSPECTIVE_PHASE57_FROZEN_WAIT_READY',decision,modelId:'test-model',artifactSha256:'a'.repeat(64)},
    provenance:{currentSymbol:symbol,currentSessionDate:currentPrefix.sessionDate,currentFeatureCutoff:asOf},
  };
}

test('end-to-end evaluator composes prefix replay, frozen ledger, outcomes and five-variant evidence without MarketSpeed',()=>{
  const sessionDate='2026-08-19';
  const record=universe(sessionDate);
  const result=runP252EndToEndProspectiveEvaluation({
    sessionInputs:[{sessionDate,universeRecord:record,sessionBarsBySymbol:barsBySymbol(record),sourceProvenance:{provider:'TEST_NON_RSS_5M'}}],
    historicalSessions:[],
    expectedSessionDates:[sessionDate,'2026-08-20'],
    scorePrefix,
  });
  assert.equal(result.status,'P25_2_END_TO_END_PROSPECTIVE_EVIDENCE_READY');
  assert.equal(result.readyPacketCount,1);
  assert.equal(result.blockedSessionCount,0);
  assert.equal(result.packetSummaries[0].commonFairCutoffCount,3);
  assert.equal(result.packetSummaries[0].frozenTradeCount,3);
  assert.equal(result.packetSummaries[0].resolvedTradeCount,2);
  assert.equal(result.packetSummaries[0].unresolvedTradeCount,1);
  assert.equal(result.evidence.expectedTradingSessionCount,2);
  assert.deepEqual(result.evidence.missingExpectedSessions,['2026-08-20']);
  assert.equal(result.evidence.operationalTradeFrequency.DYNAMIC_30.validFrozenEntries,3);
  assert.equal(result.evidence.operationalTradeFrequency.DYNAMIC_30.tradingSessions,2);
  assert.equal(result.evidence.comparison.results.DYNAMIC_30.trades,2);
  assert.equal(result.methodology.dailyMarketSpeedRequired,false);
  assert.equal(result.methodology.microstructureUsed,false);
  assert.equal(result.methodology.currentOuterOosDoesNotSelectDynamicN,true);
});

test('missing or broken session bars are preserved as blocked session and count as zero operational day',()=>{
  const sessionDate='2026-08-19';
  const record=universe(sessionDate);
  const result=runP252EndToEndProspectiveEvaluation({
    sessionInputs:[{sessionDate,universeRecord:record,sessionBarsBySymbol:{},sourceProvenance:{provider:'BROKEN'}}],
    expectedSessionDates:[sessionDate],
    scorePrefix,
  });
  assert.equal(result.readyPacketCount,0);
  assert.equal(result.blockedSessionCount,1);
  assert.equal(result.blockedSessions[0].status,'BLOCKED_SESSION_REPLAY_EXCEPTION');
  assert.equal(result.evidence.operationalTradeFrequency.DYNAMIC_50.validFrozenEntries,0);
  assert.equal(result.evidence.operationalTradeFrequency.DYNAMIC_50.tradingSessions,1);
});

test('a session outside the predeclared expected set fails closed',()=>{
  const record=universe('2026-08-20');
  assert.throws(()=>runP252EndToEndProspectiveEvaluation({
    sessionInputs:[{sessionDate:'2026-08-20',universeRecord:record,sessionBarsBySymbol:barsBySymbol(record)}],
    expectedSessionDates:['2026-08-19'],
    scorePrefix,
  }),/outside expectedSessionDates/);
});

test('routine policy keeps MarketSpeed, board and tick data optional and every execution surface disabled',()=>{
  assert.equal(PHASE57_P25_2I_POLICY.dailyMarketSpeedRequired,false);
  assert.equal(PHASE57_P25_2I_POLICY.marketSpeedVerificationOptionalAndSeparate,true);
  assert.equal(PHASE57_P25_2I_POLICY.microstructureUsed,false);
  assert.equal(PHASE57_P25_2I_POLICY.boardOrTickRequired,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_P25_2I_SAFETY[key],false,key);
});
