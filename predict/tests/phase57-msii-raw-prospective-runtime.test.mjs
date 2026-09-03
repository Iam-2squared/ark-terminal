import assert from "node:assert/strict";
import test from "node:test";

import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import {
  normalizeRawProspectiveMsiiEvent,
  processRawProspectiveMsiiPoint,
} from "../realtime/phase57-msii-raw-prospective-runtime.js";

const DATE = "2026-09-04";
const AT = "2026-09-04T00:35:00.000Z";
const SAFE = Object.freeze({
  executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false, rssOrderFunctionAllowed:false,
  liveTradingAllowed:false, paperTradingAllowed:false, automaticPromotionAllowed:false, productionUpdateAllowed:false, transmitted:false,
});
const VERSIONS = Object.freeze({
  selectorVersion:"PHASE57_DYNAMIC5M_FROZEN_SELECTOR", entryVersion:"PHASE57_FROZEN_ENTRY",
  exitV3Version:"PHASE57_EXIT_V3_FROZEN", exitV4Version:"PHASE57_EXIT_V4_FROZEN", allocationVersion:"PHASE57_CAPITAL_ALLOCATION_FROZEN",
});
function raw(capturedAt,{bid=100,ask=100.2}={}) {
  return {
    schemaVersion:1, phase:"58.p31.multi-symbol-capture", sourceMode:"MARKETSPEED_II_RSS_READ_ONLY",
    batchId:`B|${capturedAt}`, capturedAt, symbol:"7203.T",
    market:{symbol:"7203",bestBid:bid,bestAsk:ask,bestBidSize:10000,bestAskSize:10000,bestBidTime:"09:35:00",bestAskTime:"09:35:00"},
    ticks:[], sourceFunctions:["RssMarket","RssTickList"], marketSizeUnit:"SHARES", tickSizeUnit:"SHARES",
    methodology:{preconfiguredSheetsOnly:true,excelFormulaWritePerformed:false,symbolSwitchWritePerformed:false,pointInTimeOnly:true,futureOutcomeUsed:false},
    safety:SAFE,
  };
}
function frozenEntry() {
  const cells=["V1_V3","V1_V4"];
  return Object.freeze({
    candidateId:`${DATE}|${AT}|DYNAMIC5M_V1|7203`, entryAccepted:true, frozenBeforeOutcome:true, currentOutcomeUsed:false,
    symbol:"7203", sessionDate:DATE, entryTimestamp:AT, signalDirection:1, entryPrice:100, confidence:0.8, probability:0.75,
    sector:"TEST", contextBars:Object.freeze([]), selectionLineage:Object.freeze({variant:"V1",opportunityScore:0.8,v2Score:null}),
    strategyLineage:Object.freeze({cells:Object.freeze(cells),strategyIds:Object.freeze(STRATEGY_IDS.filter((id)=>cells.some((cell)=>id.startsWith(`${cell}__`))))}),
  });
}
function fixture() {
  const state=createRealtimeSessionState({sessionDate:DATE});
  const allocation=allocateRealtimeFrozenEntries(state,{at:AT,entries:[frozenEntry()],marksBySymbol:{"7203":100}});
  const laneYDecisions=allocation.decisions.filter((x)=>x.status==="ACCEPTED").map((x)=>({strategyId:x.strategyId,symbol:x.symbol,decisionAt:AT,intentKind:"ENTRY",referencePrice:100}));
  return {state,point:{at:AT,allocation,exitEvaluation:{at:AT,closed:[]}},laneYDecisions};
}

test("raw prospective MarketSpeed event stays decision-neutral and read-only",()=>{
  const event=normalizeRawProspectiveMsiiEvent(raw("2026-09-04T00:34:59.500Z"));
  assert.equal(event.rawProspectiveCapture,true);
  assert.equal(event.phase57SnapshotHash,null);
  assert.equal(event.selectorDirection,null);
  assert.equal(event.sourceMode,"MARKETSPEED_II_RSS_READ_ONLY");
  assert.equal(event.safety.executionAllowed,false);
});

test("raw prospective runtime uses pre-decision quote and post-decision evidence without fabricated Phase57 context",()=>{
  const {state,point,laneYDecisions}=fixture();
  const result=processRawProspectiveMsiiPoint({
    sessionDate:DATE, predeclaredStartAt:"2026-09-04T00:00:00.000Z", actualStartAt:"2026-09-04T00:00:00.000Z",
    phase57State:state, pointResult:point, versions:VERSIONS, laneYDecisions,
    captureRows:[raw("2026-09-04T00:34:59.500Z",{bid:99.9,ask:100.1}),raw("2026-09-04T00:35:00.200Z",{bid:100,ask:100.2})],
  });
  assert.equal(result.complete,true);
  assert.equal(result.entryIntentCount,14);
  assert.equal(result.score.statusCounts.FILLED,14);
  assert.equal(result.pair.pairCount,14);
  assert.equal(result.ledger.filter((x)=>x.eventType==="MSII_MARKET_EVENT_COMMITTED").every((x)=>x.marketEvent.rawProspectiveCapture===true),true);
});

test("raw prospective runtime fails closed when required pre-decision quote is stale",()=>{
  const {state,point,laneYDecisions}=fixture();
  const result=processRawProspectiveMsiiPoint({
    sessionDate:DATE, predeclaredStartAt:"2026-09-04T00:00:00.000Z", actualStartAt:"2026-09-04T00:00:00.000Z",
    phase57State:state, pointResult:point, versions:VERSIONS, laneYDecisions, referenceMaxAgeMs:5000,
    captureRows:[raw("2026-09-04T00:34:50.000Z"),raw("2026-09-04T00:35:00.200Z")],
  });
  assert.equal(result.complete,false);
  assert.deepEqual(result.missingReferenceSymbols,["7203.T"]);
});

test("raw capture with order-capable provenance is rejected",()=>{
  const bad=structuredClone(raw("2026-09-04T00:34:59.500Z"));
  bad.sourceFunctions.push("RssStockOrder");
  assert.throws(()=>normalizeRawProspectiveMsiiEvent(bad),/forbidden RSS order function/);
});
