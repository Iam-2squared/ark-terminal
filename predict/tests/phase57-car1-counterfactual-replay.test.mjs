import assert from 'node:assert/strict';
import test from 'node:test';
import {runCar1CounterfactualPortfolioAttribution} from '../portfolio/phase57-car1-counterfactual-replay.js';

const DATE='2026-09-01';
const at=minute=>`${DATE}T00:${String(minute).padStart(2,'0')}:00.000Z`;

function bars({range=1,wiggle=0.05,count=30,base=100}={}){
  return Array.from({length:count},(_,index)=>{
    const close=base+index*0.1+(index%2===0?-wiggle:wiggle);
    return {timestamp:at(index),open:close,high:close+range/2,low:close-range/2,close,volume:1_000};
  });
}

function setClose(rows,index,close,range=1){
  rows[index]={...rows[index],open:close,high:close+range/2,low:close-range/2,close};
}

function trade(symbol,rows,{entryMinute=15,exitMinute=19,direction=1,sector='TEST'}={}){
  const entryPrice=rows[entryMinute].close,exitPrice=rows[exitMinute].close;
  return {
    entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,
    sessionDate:DATE,symbol,sector,signalDirection:direction,
    entryTimestamp:at(entryMinute),entryPrice,exitTimestamp:at(exitMinute),exitPrice,
    exitReason:'FROZEN_HORIZON',netReturnPct:(exitPrice/entryPrice-1)*100*direction-0.05,
  };
}

const max4=Object.freeze({id:'TEST_MAX_4',label:'Test Max 4',maxPositions:4,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'});
const max1=Object.freeze({id:'TEST_MAX_1',label:'Test Max 1',maxPositions:1,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'});

test('CAR-1 counterfactual replay must reproduce Lane C legacy exactly before challenger outcomes are exposed',()=>{
  const low=bars({range:1,wiggle:0.05,count:30});
  const high=bars({range:6,wiggle:0.8,count:30});
  setClose(low,19,106,1);
  setClose(high,19,96,6);
  const session={sessionDate:DATE,trades:[trade('LOW.T',low),trade('HIGH.T',high)],sessionBarsBySymbol:{'LOW.T':low,'HIGH.T':high}};
  const result=runCar1CounterfactualPortfolioAttribution({sessions:[session],baselineProfile:max4});

  assert.equal(result.status,'CAR1_PARITY_GATED_COUNTERFACTUAL_PORTFOLIO_ATTRIBUTION');
  assert.equal(result.legacyReplayParity.passed,true);
  assert.equal(result.legacyReplayParity.finalEquityDeltaJpy,0);
  assert.equal(result.legacyReplayParity.acceptedTradeDelta,0);
  assert.equal(result.pairedAudit.sameFrozenEntryCandidates,true);
  assert.equal(result.pairedAudit.sameFrozenExit,true);
  assert.equal(result.pairedAudit.sameCostAssumption,true);
  assert.equal(result.pairedAudit.sameCandidatePriority,true);
  assert.equal(result.pairedAudit.futureOutcomeUsedBySizer,false);
  assert.equal(result.interpretation.winnerSelectionAllowed,false);
  assert.equal(result.interpretation.parameterSearchAllowed,false);
  assert.equal(result.interpretation.promotionEligible,false);
  assert.equal(result.interpretation.formalOos,false);

  const inverseAtr=result.results.INVERSE_ATR.allocationDecisions;
  const lowAtr=inverseAtr.find(row=>row.key.endsWith('|LOW.T'));
  const highAtr=inverseAtr.find(row=>row.key.endsWith('|HIGH.T'));
  assert.ok(lowAtr.quantity>highAtr.quantity);

  const inverseVol=result.results.INVERSE_REALIZED_VOL.allocationDecisions;
  const lowVol=inverseVol.find(row=>row.key.endsWith('|LOW.T'));
  const highVol=inverseVol.find(row=>row.key.endsWith('|HIGH.T'));
  assert.ok(lowVol.quantity>highVol.quantity);

  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
  ]){
    assert.equal(result.safety.car1[key],false,key);
    assert.equal(result.safety.laneC[key],false,key);
  }
});

test('legacy parity gate covers same-timestamp cash release and fully collateralized SHORT accounting',()=>{
  const first=bars({range:1,wiggle:0.1,count:30,base:100});
  const second=bars({range:2,wiggle:0.2,count:30,base:200});
  setClose(first,20,110,1);
  setClose(second,25,190,2);
  const session={
    sessionDate:DATE,
    trades:[
      trade('1001.T',first,{entryMinute:15,exitMinute:20,direction:1}),
      trade('1002.T',second,{entryMinute:20,exitMinute:25,direction:-1}),
    ],
    sessionBarsBySymbol:{'1001.T':first,'1002.T':second},
  };
  const result=runCar1CounterfactualPortfolioAttribution({sessions:[session],baselineProfile:max1,profileIds:['EQUAL_NOTIONAL']});
  assert.equal(result.legacyReplayParity.passed,true);
  assert.equal(result.baseline.acceptedTradeCount,2);
  assert.equal(result.results.EQUAL_NOTIONAL.acceptedTradeCount,2);
  assert.ok(result.results.EQUAL_NOTIONAL.closedTrades.find(row=>row.key.endsWith('|1002.T')).realizedPnlJpy>0);
});
