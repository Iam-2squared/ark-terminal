import assert from "node:assert/strict";
import test from "node:test";
import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import { processRawEnvelopeFile } from "../../tools/phase57_msii_raw_e2e_runtime.mjs";

const DATE="2026-09-04",AT="2026-09-04T00:35:00.000Z";
const SAFE={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false};
const VERSIONS={selectorVersion:"PHASE57_DYNAMIC5M_FROZEN_SELECTOR",entryVersion:"PHASE57_FROZEN_ENTRY",exitV3Version:"PHASE57_EXIT_V3_FROZEN",exitV4Version:"PHASE57_EXIT_V4_FROZEN",allocationVersion:"PHASE57_CAPITAL_ALLOCATION_FROZEN"};
function entry(){const cells=["V1_V3","V1_V4"];return {candidateId:`${DATE}|${AT}|V1|7203`,entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,symbol:"7203",sessionDate:DATE,entryTimestamp:AT,signalDirection:1,entryPrice:100,confidence:.8,probability:.75,sector:"TEST",contextBars:[],selectionLineage:{variant:"V1"},strategyLineage:{cells,strategyIds:STRATEGY_IDS.filter((id)=>cells.some((cell)=>id.startsWith(`${cell}__`)))}};}
function capture(capturedAt){return {schemaVersion:1,phase:"58.p31.multi-symbol-capture",sourceMode:"MARKETSPEED_II_RSS_READ_ONLY",batchId:`b-${capturedAt}`,capturedAt,symbol:"7203.T",market:{symbol:"7203",bestBid:99.9,bestAsk:100.1,bestBidSize:10000,bestAskSize:10000},ticks:[],sourceFunctions:["RssMarket","RssTickList"],marketSizeUnit:"SHARES",tickSizeUnit:"SHARES",methodology:{preconfiguredSheetsOnly:true,excelFormulaWritePerformed:false,symbolSwitchWritePerformed:false,pointInTimeOnly:true,futureOutcomeUsed:false},safety:SAFE};}
function envelope(){const state=createRealtimeSessionState({sessionDate:DATE});const allocation=allocateRealtimeFrozenEntries(state,{at:AT,entries:[entry()],marksBySymbol:{"7203":100}});return {schemaVersion:1,sessionDate:DATE,predeclaredStartAt:"2026-09-04T00:00:00.000Z",actualStartAt:"2026-09-04T00:00:00.000Z",missingCaptureCount:0,backfillUsed:false,initialCapital:1_000_000,phase57State:state,pointResult:{at:AT,allocation,exitEvaluation:{at:AT,closed:[]}},versions:VERSIONS,laneYDecisions:allocation.decisions.filter((x)=>x.status==="ACCEPTED").map((x)=>({strategyId:x.strategyId,symbol:x.symbol,decisionAt:AT,intentKind:"ENTRY",referencePrice:100})),safety:SAFE};}

test("raw E2E coordinator slices only causal window and persists replay guard",()=>{
 const env=envelope();
 const rows=[capture("2026-09-04T00:34:40.000Z"),capture("2026-09-04T00:34:59.500Z"),capture("2026-09-04T00:35:00.200Z"),capture("2026-09-04T00:35:10.000Z")];
 const first=processRawEnvelopeFile({envelope:env,captureRows:rows});
 assert.equal(first.captureRowCount,2);
 assert.equal(first.result.complete,true);
 assert.equal(first.nextState.lastDecisionAt,AT);
 assert.equal(first.nextState.processedEvidenceHashes.length,1);
 assert.throws(()=>processRawEnvelopeFile({envelope:env,captureRows:rows,priorState:first.nextState}),/strictly forward/);
});
