import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildP25ExitV3PortfolioSessions,
  compareP25ExitV3LaneCAllocations,
  PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_SAFETY,
} from '../portfolio/phase57-p25-lane-c-exit-v3-connector.js';
import {P25_EXIT_V3_DUAL_GATE_POLICY_SHA256} from '../daytrade/phase57-p25-exit-v3-dual-gate.js';

const DATE='2026-08-25';
const time=minute=>`${DATE}T00:${String(minute).padStart(2,'0')}:00.000Z`;
const bars=points=>points.map(([minute,close])=>({timestamp:time(minute),open:close,high:close,low:close,close,volume:1_000}));

function pair(symbol,{entryMinute=0,exitMinute=10,entryPrice=1_000,exitPrice=1_020,direction=1}={}){
  const entryTimestamp=time(entryMinute);
  const gross=(exitPrice/entryPrice-1)*100*direction;
  return {
    key:`${DATE}|${entryTimestamp}|${symbol}`,
    sessionDate:DATE,
    symbol,
    variantMemberships:['DYNAMIC_50'],
    fixed:{
      entryAccepted:true,
      frozenBeforeOutcome:true,
      currentOutcomeUsed:false,
      sessionDate:DATE,
      symbol,
      sector:'TECH',
      signalDirection:direction,
      entryTimestamp,
      entryPrice,
      exitTimestamp:time(15),
      exitPrice,
      netReturnPct:gross-0.05,
    },
    v3:{
      exitTimestamp:time(exitMinute),
      exitPrice,
      exitReason:'V3_TEST_EXIT',
      netReturnPct:gross-0.05,
      policySha256:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,
    },
  };
}

function replay(pairs){
  return {
    classification:{diagnosticOnly:true,formalOos:false,promotionEligible:false},
    lineageManifestHeadSha256:'lineage-test',
    policySha256:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,
    pairs,
    methodology:{
      exactDynamic50Only:true,
      sameFrozenEntryAsFixed:true,
      resultBasedRetuning:false,
      freshHoldoutConsumed:false,
    },
  };
}

function packet(){
  return {
    sessionDate:DATE,
    sessionBarsBySymbol:{
      '1001.T':bars([[0,1_000],[5,1_010],[10,1_020],[15,1_020]]),
      '1002.T':bars([[0,2_000],[5,2_000],[10,1_980],[15,1_980]]),
    },
  };
}

test('EXIT v3 connector preserves Frozen DYNAMIC_50 Entry identity and replaces only management outcome',()=>{
  const source=pair('1001.T');
  const result=buildP25ExitV3PortfolioSessions({replay:replay([source]),sessionPackets:[packet()]});
  assert.equal(result.sessions.length,1);
  assert.equal(result.sessions[0].trades.length,1);
  const trade=result.sessions[0].trades[0];
  assert.equal(trade.entryTimestamp,source.fixed.entryTimestamp);
  assert.equal(trade.entryPrice,source.fixed.entryPrice);
  assert.equal(trade.signalDirection,source.fixed.signalDirection);
  assert.equal(trade.exitTimestamp,source.v3.exitTimestamp);
  assert.equal(trade.exitPrice,source.v3.exitPrice);
  assert.equal(trade.exitReason,source.v3.exitReason);
  assert.equal(result.audit.exactDynamic50Only,true);
  assert.equal(result.audit.winnerSelectionAllowed,false);
  assert.equal(result.audit.formalOos,false);
});

test('EXIT v3 connector fails closed on non-DYNAMIC_50 pair',()=>{
  const source=pair('1001.T');
  source.variantMemberships=['DYNAMIC_40'];
  assert.throws(()=>buildP25ExitV3PortfolioSessions({replay:replay([source]),sessionPackets:[packet()]}),/non-DYNAMIC_50/);
});

test('EXIT v3 connector fails closed on policy hash mismatch',()=>{
  const source=pair('1001.T');
  source.v3.policySha256='wrong';
  assert.throws(()=>buildP25ExitV3PortfolioSessions({replay:replay([source]),sessionPackets:[packet()]}),/policy hash mismatch/);
});

test('EXIT v3 connector fails closed when future EXIT fields are smuggled into Frozen Entry identity',()=>{
  const source=pair('1001.T');
  source.fixed.currentOutcomeUsed=true;
  assert.throws(()=>buildP25ExitV3PortfolioSessions({replay:replay([source]),sessionPackets:[packet()]}),/not a frozen outcome-free Entry/);
});

test('EXIT v3 diagnostic allocation matrix runs Max10 Max4 Max3 Max2 without selecting a winner',()=>{
  const pairs=[pair('1001.T',{entryPrice:1_000,exitPrice:1_020}),pair('1002.T',{entryPrice:2_000,exitPrice:1_980,direction:-1})];
  const result=compareP25ExitV3LaneCAllocations({replay:replay(pairs),sessionPackets:[packet()]});
  assert.equal(result.status,'P25_EXIT_V3_LANE_C_DIAGNOSTIC_MATRIX_READY');
  assert.equal(result.interpretation.edgeLabel,'MANAGEMENT_X_CAPITAL_ALLOCATION');
  assert.equal(result.interpretation.winnerSelectionAllowed,false);
  assert.equal(result.interpretation.formalOosEvidence,false);
  assert.deepEqual(result.comparison.resultOrder,['CURRENT_EXISTING','MAX_10','MAX_4','MAX_3','MAX_2']);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_SAFETY[key],false,key);
  }
});
