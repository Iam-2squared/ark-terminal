import assert from 'node:assert/strict';
import test from 'node:test';
import {
  materializeP252FixedHorizonOutcomes,
  evaluateP252ResolvedSession,
  PHASE57_P25_2G_SAFETY,
} from '../daytrade/phase57-p25-2g-fixed-horizon-outcome-materialization.js';

function trade(symbol='1001.T',{
  entryTimestamp='2026-08-19T00:25:00.000Z',
  signalDirection=1,
  baseHorizonBars=2,
}={}){
  return {
    entryAccepted:true,
    symbol,
    sessionDate:'2026-08-19',
    entryTimestamp,
    featureCutoff:entryTimestamp,
    signalDirection,
    baseHorizonBars,
    sector:'Tech',
    frozenBeforeOutcome:true,
    currentOutcomeUsed:false,
    outcomePending:true,
  };
}
function bars(closes=[100,101,102,103]){
  return closes.map((close,index)=>({
    timestamp:`2026-08-19T00:${String(25+index*5).padStart(2,'0')}:00.000Z`,
    open:close,high:close+1,low:close-1,close,volume:1000+index,
  }));
}
const FROZEN5=['7203.T','6758.T','9984.T','8306.T','8035.T'];
const OLD30=Array.from({length:30},(_,i)=>`${2001+i}.T`);
const D50=Array.from({length:50},(_,i)=>`${1001+i}.T`);
function universe(){return {ready:true,sessionDate:'2026-08-19',variants:{FIXED_5:FROZEN5,OLD_FIXED_30:OLD30,DYNAMIC_30:D50.slice(0,30),DYNAMIC_40:D50.slice(0,40),DYNAMIC_50:D50},rankAudit:{day50:D50.map(x=>({symbol:x,sector:'Tech'}))}};}

test('fixed horizon uses the nth future close and frozen 0.05% round-trip cost',()=>{
  const result=materializeP252FixedHorizonOutcomes({
    frozenTrades:[trade()],
    sessionBarsBySymbol:{'1001.T':bars([100,101,102,103])},
  });
  assert.equal(result.status,'FIXED_HORIZON_OUTCOMES_READY');
  assert.equal(result.resolvedCount,1);
  const row=result.resolvedTrades[0];
  assert.equal(row.entryPrice,100);
  assert.equal(row.exitPrice,102);
  assert.equal(row.barsHeld,2);
  assert.equal(row.exitReason,'FROZEN_HORIZON');
  assert.equal(row.horizonTruncatedAtSessionEnd,false);
  assert.ok(Math.abs(row.grossReturnPct-2)<1e-12);
  assert.ok(Math.abs(row.netReturnPct-1.95)<1e-12);
  assert.equal(row.hit,true);
});

test('SHORT aligned return preserves direction and cost semantics',()=>{
  const result=materializeP252FixedHorizonOutcomes({
    frozenTrades:[trade('1001.T',{signalDirection:-1,baseHorizonBars:1})],
    sessionBarsBySymbol:{'1001.T':bars([100,98,97])},
  });
  const row=result.resolvedTrades[0];
  assert.ok(Math.abs(row.grossReturnPct-2)<1e-12);
  assert.ok(Math.abs(row.netReturnPct-1.95)<1e-12);
  assert.equal(row.hit,true);
});

test('session-end truncation matches the P24 fixed-outcome continuity rule',()=>{
  const result=materializeP252FixedHorizonOutcomes({
    frozenTrades:[trade('1001.T',{baseHorizonBars:6})],
    sessionBarsBySymbol:{'1001.T':bars([100,101,102])},
  });
  const row=result.resolvedTrades[0];
  assert.equal(row.barsHeld,2);
  assert.equal(row.horizonTruncatedAtSessionEnd,true);
  assert.equal(row.exitPrice,102);
});

test('missing entry bar is retained as unresolved rather than backfilled',()=>{
  const result=materializeP252FixedHorizonOutcomes({
    frozenTrades:[trade('1001.T',{entryTimestamp:'2026-08-19T00:20:00.000Z'})],
    sessionBarsBySymbol:{'1001.T':bars([100,101,102])},
  });
  assert.equal(result.status,'FIXED_HORIZON_OUTCOMES_PARTIAL');
  assert.equal(result.resolvedCount,0);
  assert.equal(result.unresolvedCount,1);
  assert.equal(result.unresolvedTrades[0].outcomeStatus,'UNRESOLVED_ENTRY_BAR_MISSING');
});

test('non-frozen trade rows and cost changes fail closed',()=>{
  assert.throws(()=>materializeP252FixedHorizonOutcomes({
    frozenTrades:[{...trade(),currentOutcomeUsed:true}],
    sessionBarsBySymbol:{'1001.T':bars()},
  }),/only frozen outcome-free Entry rows/);
  assert.throws(()=>materializeP252FixedHorizonOutcomes({
    frozenTrades:[trade()],
    sessionBarsBySymbol:{'1001.T':bars()},
    roundTripCostPct:0.04,
  }),/must remain frozen at 0\.05%/);
});

test('resolved session flows directly into the five-variant comparison without selecting Dynamic N',()=>{
  const frozen=trade('1001.T',{baseHorizonBars:1});
  const result=evaluateP252ResolvedSession({
    universeRecord:universe(),
    ledger:{
      frozenTrades:[frozen],
      eligibleDecisionCountsByVariant:{FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50},
    },
    sessionBarsBySymbol:{'1001.T':bars([100,101,102])},
    regimeBySession:{'2026-08-19':'RISK_ON'},
  });
  assert.equal(result.status,'P25_2_SESSION_FIXED_HORIZON_COMPARISON_READY');
  assert.equal(result.outcomes.resolvedCount,1);
  assert.equal(result.comparison.results.DYNAMIC_30.validFrozenEntries,1);
  assert.equal(result.comparison.results.DYNAMIC_40.validFrozenEntries,1);
  assert.equal(result.comparison.results.DYNAMIC_50.validFrozenEntries,1);
  assert.equal(result.comparison.results.FIXED_5.validFrozenEntries,0);
  assert.equal(result.comparison.results.OLD_FIXED_30.validFrozenEntries,0);
  assert.equal(result.comparison.results.DYNAMIC_30.stability.byRegime.RISK_ON.entries,1);
  assert.equal(result.methodology.currentSessionDoesNotSelectDynamicN,true);
});

test('all execution and promotion surfaces remain disabled',()=>{
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','freshHoldoutConsumed',
  ])assert.equal(PHASE57_P25_2G_SAFETY[key],false,key);
});
