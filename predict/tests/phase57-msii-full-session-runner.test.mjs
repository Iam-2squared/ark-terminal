import assert from "node:assert/strict";
import test from "node:test";
import { allocateRealtimeFrozenEntries } from "../realtime/phase57-realtime-allocation.js";
import { STRATEGY_IDS, createRealtimeSessionState } from "../realtime/phase57-stateful-contract.js";
import { stepFullSession, PHASE57_MSII_FULL_SESSION_SAFETY } from "../../tools/phase57_msii_full_session_runner.mjs";

const DATE="2026-09-04",AT="2026-09-04T00:35:00.000Z";
const SAFE={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false};
const VERSIONS={selectorVersion:"PHASE57_DYNAMIC5M_FROZEN_SELECTOR",entryVersion:"PHASE57_FROZEN_ENTRY",exitV3Version:"PHASE57_EXIT_V3_FROZEN",exitV4Version:"PHASE57_EXIT_V4_FROZEN",allocationVersion:"PHASE57_CAPITAL_ALLOCATION_FROZEN"};
function entry(){const cells=["V1_V3","V1_V4"];return {candidateId:`${DATE}|${AT}|V1|7203`,entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,symbol:"7203",sessionDate:DATE,entryTimestamp:AT,signalDirection:1,entryPrice:100,confidence:.8,probability:.75,sector:"TEST",contextBars:[],selectionLineage:{variant:"V1"},strategyLineage:{cells,strategyIds:STRATEGY_IDS.filter((id)=>cells.some((cell)=>id.startsWith(`${cell}__`)))}};}
function envelope(){const state=createRealtimeSessionState({sessionDate:DATE});const allocation=allocateRealtimeFrozenEntries(state,{at:AT,entries:[entry()],marksBySymbol:{"7203":100}});return {schemaVersion:1,sessionDate:DATE,predeclaredStartAt:"2026-09-04T00:00:00.000Z",actualStartAt:"2026-09-04T00:00:00.000Z",missingCaptureCount:0,backfillUsed:false,initialCapital:1_000_000,phase57State:state,pointResult:{at:AT,allocation,exitEvaluation:{at:AT,closed:[]}},versions:VERSIONS,laneYDecisions:allocation.decisions.filter((x)=>x.status==="ACCEPTED").map((x)=>({strategyId:x.strategyId,symbol:x.symbol,decisionAt:AT,intentKind:"ENTRY",referencePrice:100})),safety:SAFE};}
function capture(capturedAt){return {schemaVersion:1,phase:"58.p31.multi-symbol-capture",sourceMode:"MARKETSPEED_II_RSS_READ_ONLY",batchId:`b-${capturedAt}`,capturedAt,symbol:"7203.T",market:{symbol:"7203",bestBid:99.9,bestAsk:100.1,bestBidSize:10000,bestAskSize:10000},ticks:[],sourceFunctions:["RssMarket","RssTickList"],marketSizeUnit:"SHARES",tickSizeUnit:"SHARES",methodology:{preconfiguredSheetsOnly:true,excelFormulaWritePerformed:false,symbolSwitchWritePerformed:false,pointInTimeOnly:true,futureOutcomeUsed:false},safety:SAFE};}
function emptyState(){return {schemaVersion:1,version:"phase57-msii-full-session-r1",sessionDate:DATE,lastDecisionAt:null,ledger:[],processedEvidenceHashes:[],blockedPoints:[],committedPoints:[],safety:PHASE57_MSII_FULL_SESSION_SAFETY};}

test("full-session watcher waits before causal deadline, then commits when evidence arrives",()=>{
 const env=envelope();
 const waiting=stepFullSession({envelopes:[env],captureRows:[],sessionState:emptyState(),nowMs:Date.parse(AT)+1000});
 assert.equal(waiting.events[0].status,"WAITING_FOR_CAUSAL_EVIDENCE");
 assert.equal(waiting.state.lastDecisionAt,null);
 const committed=stepFullSession({envelopes:[env],captureRows:[capture("2026-09-04T00:34:59.500Z"),capture("2026-09-04T00:35:00.200Z")],sessionState:waiting.state,nowMs:Date.parse(AT)+2000});
 assert.equal(committed.events[0].status,"COMMITTED");
 assert.equal(committed.state.lastDecisionAt,AT);
 assert.equal(committed.state.committedPoints.length,1);
});

test("full-session watcher permanently blocks after deadline and cannot backfill same decision",()=>{
 const env=envelope();
 const blocked=stepFullSession({envelopes:[env],captureRows:[],sessionState:emptyState(),nowMs:Date.parse(AT)+7000,ttlMs:5000,settleGraceMs:1000});
 assert.equal(blocked.events[0].status,"BLOCKED");
 assert.equal(blocked.state.lastDecisionAt,AT);
 assert.equal(blocked.state.blockedPoints[0].backfillAllowed,false);
 const late=stepFullSession({envelopes:[env],captureRows:[capture("2026-09-04T00:34:59.500Z"),capture("2026-09-04T00:35:00.200Z")],sessionState:blocked.state,nowMs:Date.parse(AT)+8000});
 assert.equal(late.events.length,0);
 assert.equal(late.state.committedPoints.length,0);
 assert.equal(late.state.blockedPoints.length,1);
});

test("full-session watcher safety remains read-only",()=>{
 for(const key of ["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"]) assert.equal(PHASE57_MSII_FULL_SESSION_SAFETY[key],false);
});
