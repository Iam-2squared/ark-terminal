import assert from 'node:assert/strict';
import test from 'node:test';
import {buildCapitalEfficiencyDiagnostic} from '../../scripts/analyze_p25_lane_c_capital_efficiency.mjs';

function result(maxPositions,{accepted=2,rejected=1,returnPct=3,util=0.2}={}){
  const decisions=[
    {status:'ACCEPTED',stateSnapshot:{actualPurchaseAmountJpy:200000,targetSlotBudgetJpy:250000,entryNotionalJpy:199000,availableCashBeforeJpy:1000000}},
    {status:'ACCEPTED',stateSnapshot:{actualPurchaseAmountJpy:240000,targetSlotBudgetJpy:250000,entryNotionalJpy:239000,availableCashBeforeJpy:800000}},
    {status:'REJECTED',reason:'MAX_CONCURRENT_POSITIONS',stateSnapshot:{targetSlotBudgetJpy:250000}},
  ];
  return {
    input:{profile:{maxPositions}},
    allocationDecisions:decisions,
    equityCurve:[
      {openPositionCount:0,grossExposureJpy:0,cashRatio:1},
      {openPositionCount:1,grossExposureJpy:200000,cashRatio:0.8},
      {openPositionCount:2,grossExposureJpy:400000,cashRatio:0.6},
    ],
    trade:{candidates:accepted+rejected,accepted,rejected,profitFactor:1.5},
    return:{finalEquityJpy:1000000*(1+returnPct/100),totalReturnPct:returnPct},
    risk:{maxDrawdownPct:4},
    capitalEfficiency:{averageCapitalUtilization:util,averageCashRatio:1-util,capitalRecyclingCount:1,turnover:1.2},
  };
}

function source(){
  return {
    evidenceClass:'LEGACY27_DIAGNOSTIC_ONLY',
    interpretation:{winnerSelectionAllowed:false,formalOos:false,promotionEligible:false},
    full:{comparison:{results:{MAX_10:result(10),MAX_4:result(4),MAX_3:result(3),MAX_2:result(2)}}},
    safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false},
  };
}

test('capital efficiency diagnostic explains utilization without selecting a winner',()=>{
  const x=buildCapitalEfficiencyDiagnostic(source());
  assert.equal(x.status,'LANE_C_CAPITAL_EFFICIENCY_DIAGNOSTIC_READY');
  assert.equal(x.profiles.length,4);
  assert.equal(x.interpretation.winnerSelectionAllowed,false);
  assert.equal(x.interpretation.allocationRuleTuningAllowed,false);
  const p=x.profiles.find(r=>r.profileId==='MAX_4');
  assert.equal(p.rejectionReasons.MAX_CONCURRENT_POSITIONS,1);
  assert.ok(Math.abs(p.averageSlotBudgetFillRatio-0.88)<1e-9);
  assert.ok(Math.abs(p.averageSlotOccupancyRatio-(1/4))<1e-9);
  assert.equal(p.zeroExposurePointRatio,1/3);
});

test('capital efficiency diagnostic fails closed if source is not diagnostic-only',()=>{
  const x=source();
  x.interpretation.winnerSelectionAllowed=true;
  assert.throws(()=>buildCapitalEfficiencyDiagnostic(x),/classification guard/);
});
