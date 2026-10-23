import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY,
  runCar1SelectedValidationReplay,
} from '../portfolio/phase57-car1-selected-validation-replay.js';
import {
  PHASE57_CAR1_VALIDATION_PLAN,
  PHASE57_CAR1_VALIDATION_SAFETY,
} from '../portfolio/phase57-car1-independent-validation.js';

const SELECTED=Object.freeze(['2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-11']);
const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);

function developmentLock(){
  return {
    status:'CAR1_DEVELOPMENT_EVIDENCE_LOCKED_BEFORE_VALIDATION',
    lockedBeforeValidationOutcomes:true,
    validationPlan:PHASE57_CAR1_VALIDATION_PLAN,
    configurationSha256:'c'.repeat(64),
    configuration:{
      managementMode:'FIXED_HORIZON',
      universeVariantOrder:['DYNAMIC_50'],
      baselineProfileOrder:['MAX_2'],
      sizingProfileOrder:['EQUAL_NOTIONAL','INVERSE_ATR','INVERSE_REALIZED_VOL'],
      initialEquityJpy:1_000_000,
      roundTripCostPct:0.05,
      slippageBps:0,
      lotSize:100,
      priorityRule:'ENTRY_TIMESTAMP_ASC_SYMBOL_ASC',
      atrLookbackBars:14,
      realizedVolLookbackBars:14,
      profileDefinitions:[
        {id:'EQUAL_NOTIONAL',riskMetric:null},
        {id:'INVERSE_ATR',riskMetric:'ATR_PCT'},
        {id:'INVERSE_REALIZED_VOL',riskMetric:'REALIZED_VOL'},
      ],
    },
  };
}

function validationGate(overrides={}){
  return {
    status:'CAR1_INDEPENDENT_VALIDATION_WINDOW_READY_FOR_WINDOWED_REPLAY',
    protocolId:PHASE57_CAR1_VALIDATION_PLAN.protocolId,
    selectedSessionDates:[...SELECTED],
    candidateLineageManifestHeadSha256:'d'.repeat(64),
    configurationSha256:'c'.repeat(64),
    sameFrozenConfiguration:true,
    developmentEvidenceReused:false,
    incompleteSessionReplacementAllowed:false,
    retrospectiveBackfillAllowed:false,
    parameterSearchAllowed:false,
    winnerSelectionAllowed:false,
    performanceExtractionAllowed:false,
    promotionEligible:false,
    safety:PHASE57_CAR1_VALIDATION_SAFETY,
    ...overrides,
  };
}

function packet(sessionDate,{exitPrice=101,symbol='1001.T'}={}){
  const entryTimestamp=`${sessionDate}T00:00:00.000Z`;
  const exitTimestamp=`${sessionDate}T00:05:00.000Z`;
  const entryPrice=100;
  const trade={
    entryAccepted:true,
    frozenBeforeOutcome:true,
    currentOutcomeUsed:false,
    sessionDate,
    symbol,
    sector:'TEST',
    signalDirection:1,
    entryTimestamp,
    entryPrice,
    exitTimestamp,
    exitPrice,
    exitReason:'FROZEN_HORIZON',
    netReturnPct:(exitPrice/entryPrice-1)*100-0.05,
  };
  const variants={
    FIXED_5:[symbol],OLD_FIXED_30:[symbol],DYNAMIC_30:[symbol],DYNAMIC_40:[symbol],DYNAMIC_50:[symbol],
  };
  return {
    sessionDate,
    universeRecord:{ready:true,sessionDate,variants},
    outcomes:{resolvedTrades:[trade]},
    sessionBarsBySymbol:{
      [symbol]:[
        {timestamp:entryTimestamp,open:entryPrice,high:entryPrice,low:entryPrice,close:entryPrice,volume:1_000},
        {timestamp:exitTimestamp,open:exitPrice,high:exitPrice,low:exitPrice,close:exitPrice,volume:1_000},
      ],
    },
  };
}

function run(packets,gate=validationGate()){
  return runCar1SelectedValidationReplay({
    developmentLock:developmentLock(),
    validationGate:gate,
    sessionPackets:packets,
  });
}

test('CAR-1 selected validation replay keeps every execution/order/promotion safety control false',()=>{
  for(const key of FALSE_KEYS)assert.equal(PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY[key],false,key);
  assert.equal(PHASE57_CAR1_SELECTED_VALIDATION_REPLAY_SAFETY.winnerSelectionAllowed,false);
});

test('only the five precommitted sessions are consumed and selected replay alone may expose their metrics',()=>{
  const selectedPackets=SELECTED.map(sessionDate=>packet(sessionDate));
  const result=run(selectedPackets);
  assert.equal(result.status,'CAR1_SELECTED_SESSION_ONLY_VALIDATION_REPLAY_READY');
  assert.deepEqual(result.selectedSessionDates,SELECTED);
  assert.deepEqual(result.inputAudit.consumedSessionDates,SELECTED);
  assert.equal(result.inputAudit.selectedSessionOnly,true);
  assert.equal(result.inputAudit.selectedSessionCount,5);
  assert.equal(result.inputAudit.excludedPacketCount,0);
  assert.equal(result.matrixRows.length,3);
  assert.deepEqual(result.sizingProfileOrder,['EQUAL_NOTIONAL','INVERSE_ATR','INVERSE_REALIZED_VOL']);
  assert.ok(result.matrixRows.every(row=>row.independentValidation===true&&row.winnerEligible===false&&row.promotionEligible===false));
  assert.equal(result.methodology.performanceExtractionAllowed,true);
  assert.equal(result.methodology.performanceExtractionScope,'SELECTED_PRECOMMITTED_SESSIONS_ONLY');
  assert.equal(result.methodology.cumulativeChallengerPerformanceRequired,false);
  assert.equal(result.methodology.winnerSelectionAllowed,false);
  assert.equal(result.methodology.parameterSearchAllowed,false);
  assert.equal(result.methodology.promotionEligible,false);
});

test('a later extra packet cannot leak into the selected-session performance',()=>{
  const selectedPackets=SELECTED.map(sessionDate=>packet(sessionDate));
  const baseline=run(selectedPackets);
  const withLater=run([...selectedPackets,packet('2026-09-14',{exitPrice:200,symbol:'9999.T'})]);
  assert.equal(withLater.inputAudit.excludedPacketCount,1);
  assert.deepEqual(withLater.inputAudit.consumedSessionDates,SELECTED);
  assert.deepEqual(withLater.matrixRows,baseline.matrixRows);
});

test('a missing precommitted session fails closed; a later packet cannot replace it',()=>{
  const packets=SELECTED.filter(date=>date!=='2026-09-08').map(sessionDate=>packet(sessionDate));
  packets.push(packet('2026-09-14',{exitPrice:200}));
  assert.throws(()=>run(packets),/missing precommitted packet 2026-09-08/);
});

test('the selected replay rejects configuration drift, cumulative-performance gates, and unsafe gates',()=>{
  assert.throws(
    ()=>run(SELECTED.map(sessionDate=>packet(sessionDate)),validationGate({configurationSha256:'e'.repeat(64)})),
    /configuration lock mismatch/,
  );
  assert.throws(
    ()=>run(SELECTED.map(sessionDate=>packet(sessionDate)),validationGate({performanceExtractionAllowed:true})),
    /must not expose cumulative challenger performance/,
  );
  assert.throws(
    ()=>run(SELECTED.map(sessionDate=>packet(sessionDate)),validationGate({safety:{...PHASE57_CAR1_VALIDATION_SAFETY,liveTradingAllowed:true}})),
    /liveTradingAllowed/,
  );
});
