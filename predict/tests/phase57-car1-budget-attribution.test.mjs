import assert from 'node:assert/strict';
import test from 'node:test';
import {buildCar1PairedBudgetAttribution} from '../portfolio/phase57-car1-budget-attribution.js';

const DATE='2026-09-01';
const at=minute=>`${DATE}T00:${String(minute).padStart(2,'0')}:00.000Z`;

function bars({range=1,wiggle=0.05,count=20}={}){
  return Array.from({length:count},(_,index)=>{
    const close=100+index*0.1+(index%2===0?-wiggle:wiggle);
    return {
      timestamp:at(index),open:close,high:close+range/2,low:close-range/2,close,volume:1_000,
    };
  });
}

function trade(symbol,rows,{entryMinute=15,exitMinute=19,sector='TEST'}={}){
  const entryPrice=rows[entryMinute].close,exitPrice=rows[exitMinute].close;
  return {
    entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,
    sessionDate:DATE,symbol,sector,signalDirection:1,
    entryTimestamp:at(entryMinute),entryPrice,
    exitTimestamp:at(exitMinute),exitPrice,exitReason:'FROZEN_HORIZON',
    netReturnPct:(exitPrice/entryPrice-1)*100-0.05,
  };
}

const profile=Object.freeze({id:'TEST_MAX_4',label:'Test Max 4',maxPositions:4,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'});

function pairedSession(){
  const low=bars({range:1,wiggle:0.05});
  const high=bars({range:6,wiggle:0.8});
  return {
    sessionDate:DATE,
    trades:[trade('LOW.T',low),trade('HIGH.T',high)],
    sessionBarsBySymbol:{'LOW.T':low,'HIGH.T':high},
  };
}

test('CAR-1 bridge anchors all sizing challengers to the exact Lane C legacy target-budget envelope',()=>{
  const result=buildCar1PairedBudgetAttribution({sessions:[pairedSession()],baselineProfile:profile});
  assert.equal(result.status,'CAR1_PAIRED_TARGET_BUDGET_ATTRIBUTION');
  assert.equal(result.pairedAudit.sameFrozenEntryCandidates,true);
  assert.equal(result.pairedAudit.sameFrozenExit,true);
  assert.equal(result.pairedAudit.sameCostAssumption,true);
  assert.equal(result.pairedAudit.sameCandidatePriority,true);
  assert.equal(result.pairedAudit.portfolioOutcomeSimulatedForChallengers,false);
  assert.equal(result.methodology.winnerSelectionAllowed,false);
  assert.equal(result.methodology.parameterSearchAllowed,false);

  const envelope=result.groups[0].legacyTargetBudgetEnvelopeJpy;
  for(const profileId of result.profileOrder){
    const profileResult=result.profiles[profileId];
    assert.equal(profileResult.candidateCount,2);
    assert.ok(Math.abs(profileResult.totalTargetBudgetJpy-envelope)<1e-4);
    assert.ok(Math.abs(profileResult.totalLegacyTargetBudgetJpy-envelope)<1e-4);
  }

  const equal=result.profiles.EQUAL_NOTIONAL.rows;
  assert.equal(equal[0].weight,0.5);
  assert.equal(equal[1].weight,0.5);

  const inverseAtr=result.profiles.INVERSE_ATR.rows;
  const lowAtr=inverseAtr.find(row=>row.symbol==='LOW.T');
  const highAtr=inverseAtr.find(row=>row.symbol==='HIGH.T');
  assert.ok(lowAtr.targetBudgetJpy>highAtr.targetBudgetJpy);
  assert.equal(lowAtr.riskSnapshot.futureBarUsed,false);
  assert.equal(highAtr.riskSnapshot.futureOutcomeUsed,false);

  const inverseVol=result.profiles.INVERSE_REALIZED_VOL.rows;
  const lowVol=inverseVol.find(row=>row.symbol==='LOW.T');
  const highVol=inverseVol.find(row=>row.symbol==='HIGH.T');
  assert.ok(lowVol.targetBudgetJpy>highVol.targetBudgetJpy);

  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
  ]){
    assert.equal(result.safety.car1[key],false,key);
    assert.equal(result.safety.laneC[key],false,key);
  }
});

test('CAR-1 bridge fails closed when a multi-candidate risk-weighted group lacks causal pre-entry history',()=>{
  const left=bars({range:2,wiggle:0.2,count:10});
  const right=bars({range:4,wiggle:0.4,count:10});
  const session={
    sessionDate:DATE,
    trades:[
      trade('SHORT1.T',left,{entryMinute:8,exitMinute:9}),
      trade('SHORT2.T',right,{entryMinute:8,exitMinute:9}),
    ],
    sessionBarsBySymbol:{'SHORT1.T':left,'SHORT2.T':right},
  };
  assert.throws(()=>buildCar1PairedBudgetAttribution({
    sessions:[session],baselineProfile:profile,profileIds:['INVERSE_ATR'],
  }),/insufficient causal history/);
});
