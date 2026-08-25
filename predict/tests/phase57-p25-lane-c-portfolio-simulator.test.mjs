import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildCurrentExistingReference,
  buildP252FixedPortfolioSessions,
  compareLaneCAllocationProfiles,
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_ALLOCATOR_VISIBLE_FIELDS,
  PHASE57_P25_LANE_C_CURRENT_BASELINE_AUDIT,
  PHASE57_P25_LANE_C_POLICY,
  PHASE57_P25_LANE_C_SAFETY,
  simulateLaneCPortfolio,
} from '../portfolio/phase57-p25-lane-c-portfolio-simulator.js';

const DATE='2026-08-25';
const time=minute=>`${DATE}T00:${String(minute).padStart(2,'0')}:00.000Z`;

function bars(points){
  return points.map(([minute,close])=>({timestamp:time(minute),open:close,high:close,low:close,close,volume:1_000}));
}

function trade(symbol,{entryMinute=0,exitMinute=10,entryPrice=100,exitPrice=101,direction=1,sector='TECH',netReturnPct=null}={}){
  const gross=(exitPrice/entryPrice-1)*100*direction;
  return {
    entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,
    sessionDate:DATE,symbol,sector,signalDirection:direction,
    entryTimestamp:time(entryMinute),entryPrice,exitTimestamp:time(exitMinute),exitPrice,
    exitReason:'FROZEN_HORIZON',netReturnPct:netReturnPct??gross-0.05,
  };
}

function session({trades,bySymbol}){
  return {sessionDate:DATE,trades,sessionBarsBySymbol:bySymbol};
}

const profile=maxPositions=>({id:`TEST_MAX_${maxPositions}`,label:`Test ${maxPositions}`,maxPositions,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'});

test('Lane C freezes independent progress/safety and does not relabel Max 10 as Current',()=>{
  assert.deepEqual(PHASE57_P25_LANE_C_ALLOCATION_PROFILES.map(row=>row.id),['MAX_10','MAX_4','MAX_3','MAX_2']);
  assert.equal(PHASE57_P25_LANE_C_CURRENT_BASELINE_AUDIT.max10AssumedEquivalent,false);
  assert.equal(PHASE57_P25_LANE_C_CURRENT_BASELINE_AUDIT.laneCDisposition.causalCurrentProfileInvented,false);
  assert.equal(PHASE57_P25_LANE_C_POLICY.unrealizedPnlMayIncreaseBuyingPower,false);
  assert.deepEqual(PHASE57_P25_LANE_C_POLICY.eventOrder,['PRICE_UPDATE','EXIT','CASH_RELEASE','ENTRY']);
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','freshHoldoutConsumed',
  ])assert.equal(PHASE57_P25_LANE_C_SAFETY[key],false,key);
});

test('MTM equity may raise slot budget but unrealized gains never become available cash',()=>{
  const first=trade('1001.T',{entryMinute:0,exitMinute:15,entryPrice:4_990,exitPrice:10_000});
  const second=trade('1002.T',{entryMinute:5,exitMinute:15,entryPrice:6_000,exitPrice:6_100});
  const result=simulateLaneCPortfolio({
    sessions:[session({
      trades:[first,second],
      bySymbol:{
        '1001.T':bars([[0,4_990],[5,10_000],[10,10_000],[15,10_000]]),
        '1002.T':bars([[0,6_000],[5,6_000],[10,6_050],[15,6_100]]),
      },
    })],
    profile:profile(2),initialEquity:1_000_000,
  });
  const rejected=result.allocationDecisions.find(row=>row.candidateSnapshot.symbol==='1002.T');
  assert.equal(rejected.status,'REJECTED');
  assert.equal(rejected.reason,'INSUFFICIENT_AVAILABLE_CASH_FOR_100_SHARES');
  assert.ok(rejected.stateSnapshot.portfolioEquityJpy>1_490_000);
  assert.ok(rejected.stateSnapshot.targetSlotBudgetJpy>745_000);
  assert.ok(rejected.stateSnapshot.availableCashJpy<501_000);
  assert.equal(result.trade.accepted,1);
  const accepted=result.allocationDecisions.find(row=>row.status==='ACCEPTED');
  assert.ok(accepted.stateSnapshot.actualPurchaseAmountJpy<=accepted.stateSnapshot.availableCashBeforeJpy);
});

test('same timestamp processing marks, exits, releases cash, then accepts the next Entry',()=>{
  const first=trade('1001.T',{entryMinute:0,exitMinute:5,entryPrice:9_000,exitPrice:9_100});
  const second=trade('1002.T',{entryMinute:5,exitMinute:10,entryPrice:9_000,exitPrice:9_200});
  const result=simulateLaneCPortfolio({
    sessions:[session({
      trades:[second,first],
      bySymbol:{'1001.T':bars([[0,9_000],[5,9_100],[10,9_100]]),'1002.T':bars([[0,9_000],[5,9_000],[10,9_200]])},
    })],
    profile:profile(1),initialEquity:1_000_000,
  });
  assert.equal(result.trade.accepted,2);
  assert.equal(result.capitalEfficiency.capitalRecyclingCount,1);
  assert.equal(result.capitalEfficiency.sameTimestampCapitalRecyclingCount,1);
  const secondDecision=result.allocationDecisions.find(row=>row.candidateSnapshot.symbol==='1002.T');
  assert.equal(secondDecision.status,'ACCEPTED');
  assert.equal(secondDecision.stateSnapshot.sameTimestampExitCashReleased,true);
});

test('100-share lots and deterministic symbol ordering govern simultaneous Entries without confidence ranking',()=>{
  const a=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:4_000,exitPrice:4_100});
  const b=trade('1002.T',{entryMinute:0,exitMinute:10,entryPrice:4_000,exitPrice:4_200});
  const input=session({trades:[b,a],bySymbol:{'1001.T':bars([[0,4_000],[5,4_050],[10,4_100]]),'1002.T':bars([[0,4_000],[5,4_100],[10,4_200]])}});
  const result=simulateLaneCPortfolio({sessions:[input],profile:profile(1),initialEquity:500_000});
  assert.equal(result.allocationDecisions[0].candidateSnapshot.symbol,'1001.T');
  assert.equal(result.allocationDecisions[0].status,'ACCEPTED');
  assert.equal(result.allocationDecisions[0].stateSnapshot.quantity%100,0);
  assert.equal(result.allocationDecisions[1].reason,'MAX_CONCURRENT_POSITIONS');
  assert.equal(result.methodology.confidenceRankingApplied,false);
});

test('portfolio MaxDD comes from the 5-minute MTM curve, not only closed trades',()=>{
  const row=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:100,exitPrice:110});
  const result=simulateLaneCPortfolio({
    sessions:[session({trades:[row],bySymbol:{'1001.T':bars([[0,100],[5,70],[10,110]])}})],
    profile:profile(1),initialEquity:1_000_000,
  });
  assert.ok(result.risk.maxDrawdownPct>29);
  assert.ok(result.return.finalEquityJpy>1_000_000);
  assert.equal(result.equityCurve.length,3);
  assert.ok(result.equityCurve[1].unrealizedPnlJpy<0);
});

test('SHORT Frozen Entries remain paired using fully cash-collateralized research accounting',()=>{
  const row=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:1_000,exitPrice:900,direction:-1});
  const result=simulateLaneCPortfolio({
    sessions:[session({trades:[row],bySymbol:{'1001.T':bars([[0,1_000],[5,950],[10,900]])}})],
    profile:profile(1),initialEquity:1_000_000,
  });
  assert.equal(result.trade.accepted,1);
  assert.ok(result.closedTrades[0].realizedPnlJpy>0);
  assert.equal(result.methodology.fullyCashCollateralizedShorts,true);
  assert.equal(result.methodology.shortSaleProceedsReusable,false);
});

test('allocation decision snapshots cannot expose future EXIT, future return, or confidence',()=>{
  const row=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:1_000,exitPrice:1_100});
  const result=simulateLaneCPortfolio({
    sessions:[session({trades:[row],bySymbol:{'1001.T':bars([[0,1_000],[5,1_050],[10,1_100]])}})],
    profile:profile(2),
  });
  const visible=Object.keys(result.allocationDecisions[0].candidateSnapshot);
  assert.deepEqual(visible,PHASE57_P25_LANE_C_ALLOCATOR_VISIBLE_FIELDS);
  for(const forbidden of ['exitTimestamp','exitPrice','exitReferencePrice','netReturnPct','grossReturnPct','confidence']){
    assert.equal(forbidden in result.allocationDecisions[0].candidateSnapshot,false,forbidden);
  }
});

test('changing a future outcome cannot change its earlier allocation decision',()=>{
  const winner=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:1_000,exitPrice:1_200});
  const loser=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:1_000,exitPrice:800});
  const left=simulateLaneCPortfolio({
    sessions:[session({trades:[winner],bySymbol:{'1001.T':bars([[0,1_000],[5,1_100],[10,1_200]])}})],profile:profile(2),
  });
  const right=simulateLaneCPortfolio({
    sessions:[session({trades:[loser],bySymbol:{'1001.T':bars([[0,1_000],[5,900],[10,800]])}})],profile:profile(2),
  });
  assert.deepEqual(left.allocationDecisions[0],right.allocationDecisions[0]);
  assert.notEqual(left.return.finalEquityJpy,right.return.finalEquityJpy);
});

test('frozen 0.05 percent round-trip cost reconciles simulated per-trade return at zero slippage',()=>{
  const row=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:100,exitPrice:101});
  const result=simulateLaneCPortfolio({
    sessions:[session({trades:[row],bySymbol:{'1001.T':bars([[0,100],[5,100.5],[10,101]])}})],profile:profile(1),
  });
  const closed=result.closedTrades[0];
  const simulatedReturnPct=closed.realizedPnlJpy/closed.entryNotionalJpy*100;
  assert.ok(Math.abs(simulatedReturnPct-row.netReturnPct)<1e-9);
  assert.ok(result.costs.totalTransactionCostsJpy>0);
  assert.equal(result.costs.totalAdverseSlippageJpy,0);
});

test('explicit adverse slippage is recorded and lowers equity without changing Entry ordering',()=>{
  const row=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:1_000,exitPrice:1_100});
  const input=[session({trades:[row],bySymbol:{'1001.T':bars([[0,1_000],[5,1_050],[10,1_100]])}})];
  const baseline=simulateLaneCPortfolio({sessions:input,profile:profile(2),slippageBps:0});
  const stressed=simulateLaneCPortfolio({sessions:input,profile:profile(2),slippageBps:10});
  assert.ok(stressed.costs.totalAdverseSlippageJpy>0);
  assert.ok(stressed.return.finalEquityJpy<baseline.return.finalEquityJpy);
  assert.equal(stressed.allocationDecisions[0].candidateSnapshot.symbol,baseline.allocationDecisions[0].candidateSnapshot.symbol);
});

test('Fixed adapter uses frozen universe membership and never assumes Max 10 is Current',()=>{
  const included=trade('1001.T',{entryPrice:100,exitPrice:101});
  const excluded=trade('1002.T',{entryPrice:200,exitPrice:202});
  const variants={FIXED_5:['1001.T'],OLD_FIXED_30:['1001.T'],DYNAMIC_30:['1001.T'],DYNAMIC_40:['1001.T'],DYNAMIC_50:['1001.T']};
  const sessions=buildP252FixedPortfolioSessions({
    universeVariant:'DYNAMIC_50',
    sessionPackets:[{
      sessionDate:DATE,universeRecord:{ready:true,sessionDate:DATE,variants},
      outcomes:{resolvedTrades:[included,excluded]},
      sessionBarsBySymbol:{'1001.T':bars([[0,100],[5,100.5],[10,101]]),'1002.T':bars([[0,200],[5,201],[10,202]])},
    }],
  });
  assert.deepEqual(sessions[0].trades.map(row=>row.symbol),['1001.T']);
  const comparison=compareLaneCAllocationProfiles({sessions,profiles:[profile(2)],universeVariant:'DYNAMIC_50'});
  assert.deepEqual(comparison.resultOrder,['CURRENT_EXISTING','TEST_MAX_2']);
  assert.equal(comparison.results.CURRENT_EXISTING.status,'REFERENCE_ONLY_NOT_CAUSAL_PORTFOLIO');
  assert.equal(comparison.results.CURRENT_EXISTING.max10Equivalent,null);
  assert.equal(comparison.pairedAudit.sameFrozenEntryCandidates,true);
  assert.equal(comparison.interpretation.winnerSelectionAllowed,false);
});

test('Current Existing reference preserves formal session-equal-weight semantics but is excluded from causal comparison',()=>{
  const secondDate='2026-08-26';
  const reference=buildCurrentExistingReference({
    initialEquity:1_000_000,
    sessions:[
      {sessionDate:DATE,trades:[{netReturnPct:10},{netReturnPct:-10}]},
      {sessionDate:secondDate,trades:[{netReturnPct:10}]},
    ],
  });
  assert.equal(reference.referenceMetrics.totalReturnPct,10);
  assert.equal(reference.sessionCurve[0].returnPct,0);
  assert.equal(reference.sessionCurve[1].returnPct,10);
  assert.equal(reference.comparableWithEventDrivenProfiles,false);
  assert.equal(reference.eligibleForCapitalAllocationWinnerSelection,false);
});

test('input order cannot change a paired allocation result',()=>{
  const a=trade('1001.T',{entryMinute:0,exitMinute:10,entryPrice:2_000,exitPrice:2_100});
  const b=trade('1002.T',{entryMinute:0,exitMinute:10,entryPrice:2_000,exitPrice:2_200});
  const bySymbol={'1001.T':bars([[0,2_000],[5,2_050],[10,2_100]]),'1002.T':bars([[0,2_000],[5,2_100],[10,2_200]])};
  const left=simulateLaneCPortfolio({sessions:[session({trades:[a,b],bySymbol})],profile:profile(1)});
  const right=simulateLaneCPortfolio({sessions:[session({trades:[b,a],bySymbol})],profile:profile(1)});
  assert.equal(left.input.candidateKeySha256,right.input.candidateKeySha256);
  assert.equal(left.return.finalEquityJpy,right.return.finalEquityJpy);
  assert.deepEqual(left.allocationDecisions,right.allocationDecisions);
});
