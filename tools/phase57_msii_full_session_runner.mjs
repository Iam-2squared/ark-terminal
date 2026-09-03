#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { processRawEnvelopeFile, PHASE57_MSII_RAW_E2E_SAFETY } from "./phase57_msii_raw_e2e_runtime.mjs";

const SAFETY=Object.freeze({...PHASE57_MSII_RAW_E2E_SAFETY,mode:"LANE_M_FULL_SESSION_WATCHER_READ_ONLY"});
const FALSE_KEYS=Object.freeze(["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"]);
function assertSafety(value,label){if(!value||typeof value!=="object")throw new Error(`${label} safety required`);for(const key of FALSE_KEYS)if(value[key]!==false)throw new Error(`${label}.${key} must remain false`);}
function parseArgs(argv){const out={};for(let i=0;i<argv.length;i+=1){const token=argv[i];if(!token.startsWith("--"))throw new Error(`unexpected argument ${token}`);const key=token.slice(2),next=argv[i+1];if(next===undefined||next.startsWith("--"))out[key]=true;else{out[key]=next;i+=1;}}return out;}
function required(args,key){const value=args[key];if(value===undefined||value===true||String(value).trim()==="")throw new Error(`--${key} is required`);return String(value);}
function numeric(args,key,fallback){if(args[key]===undefined)return fallback;const value=Number(args[key]);if(!Number.isFinite(value))throw new Error(`--${key} must be numeric`);return value;}
function iso(value,label="timestamp"){const parsed=Date.parse(String(value??""));if(!Number.isFinite(parsed))throw new Error(`${label} invalid`);return new Date(parsed).toISOString();}
function jstDate(value){const parts=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Tokyo",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date(iso(value)));const f=Object.fromEntries(parts.map((x)=>[x.type,x.value]));return `${f.year}-${f.month}-${f.day}`;}
function normalizeSymbol(value){const raw=String(value??"").trim().toUpperCase();if(/^\d+(?:\.0+)?$/.test(raw))return `${String(Math.trunc(Number(raw)))}.T`;return raw;}
function readJson(file){return JSON.parse(fs.readFileSync(file,"utf8"));}
function readJsonl(file){if(!fs.existsSync(file))return [];return fs.readFileSync(file,"utf8").split(/\r?\n/).filter((line)=>line.trim()).map((line,index)=>{try{return JSON.parse(line);}catch(error){throw new Error(`invalid JSONL ${file}:${index+1}: ${error.message}`);}});}
function atomicWrite(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const temp=`${file}.tmp-${process.pid}`;fs.writeFileSync(temp,`${JSON.stringify(value,null,2)}\n`,"utf8");fs.renameSync(temp,file);}
function sleep(ms){return new Promise((resolve)=>setTimeout(resolve,ms));}
function listEnvelopeFiles(directory){if(!fs.existsSync(directory))return [];return fs.readdirSync(directory,{withFileTypes:true}).filter((entry)=>entry.isFile()&&entry.name.toLowerCase().endsWith(".json")).map((entry)=>path.join(directory,entry.name));}
function envelopeMeta(file){const envelope=readJson(file);assertSafety(envelope.safety,"envelope");const decisionAt=iso(envelope?.pointResult?.at,"pointResult.at");return {file,envelope,decisionAt};}
function loadSessionState(file,sessionDate){if(!fs.existsSync(file))return {schemaVersion:2,version:"phase57-msii-full-session-r3-coverage",sessionDate,lastDecisionAt:null,ledger:[],processedEvidenceHashes:[],blockedPoints:[],committedPoints:[],safety:SAFETY};const state=readJson(file);assertSafety(state.safety,"sessionState");if(state.sessionDate!==sessionDate)throw new Error("Lane M full-session state sessionDate mismatch");return state;}
function pointArtifactPath(outputDir,decisionAt,status){const stamp=decisionAt.replace(/[-:.]/g,"");return path.join(outputDir,"session-points",`${stamp}-${status}.json`);}
function evidenceDeadlineMs(envelope,{ttlMs,decisionLatencyMs,settleGraceMs}){return Date.parse(iso(envelope.pointResult.at))+Math.max(ttlMs,decisionLatencyMs)+settleGraceMs;}
function requiredSymbols(envelope){const accepted=envelope?.pointResult?.allocation?.decisions??[];const closed=envelope?.pointResult?.exitEvaluation?.closed??[];return [...new Set([...accepted.filter((row)=>row?.status==="ACCEPTED").map((row)=>normalizeSymbol(row.symbol)),...closed.map((row)=>normalizeSymbol(row.symbol))].filter(Boolean))].sort();}

/** Pure diagnostic only. It does not change selection/fill semantics or rescue missing evidence. */
export function diagnosePhase57MsiiPointCoverage(envelope,captureRows,{referenceMaxAgeMs=5_000,ttlMs=5_000,decisionLatencyMs=100}={}){
  const decisionAt=iso(envelope?.pointResult?.at,"pointResult.at");
  const decisionMs=Date.parse(decisionAt),minMs=decisionMs-referenceMaxAgeMs,maxMs=decisionMs+Math.max(ttlMs,decisionLatencyMs);
  const required=requiredSymbols(envelope),requiredSet=new Set(required),observedSet=new Set();
  for(const row of captureRows??[]){const symbol=normalizeSymbol(row?.symbol),capturedMs=Date.parse(String(row?.capturedAt??""));if(requiredSet.has(symbol)&&Number.isFinite(capturedMs)&&capturedMs>=minMs&&capturedMs<=maxMs)observedSet.add(symbol);}
  const observed=[...observedSet].sort(),missing=required.filter((symbol)=>!observedSet.has(symbol));
  return Object.freeze({decisionAt,requiredSymbolCount:required.length,observedRequiredSymbolCount:observed.length,missingSymbolCount:missing.length,coveragePercent:required.length?100*observed.length/required.length:100,requiredSymbols:Object.freeze(required),observedRequiredSymbols:Object.freeze(observed),missingSymbols:Object.freeze(missing),diagnosticOnly:true,backfillAllowed:false});
}
function summarizeCoverage(state){
  const points=[...(state?.committedPoints??[]),...(state?.blockedPoints??[])].filter((row)=>row?.coverage),missingSymbols=[...new Set(points.flatMap((row)=>row.coverage.missingSymbols??[]))].sort();
  const requiredOccurrences=points.reduce((sum,row)=>sum+Number(row.coverage.requiredSymbolCount??0),0),observedOccurrences=points.reduce((sum,row)=>sum+Number(row.coverage.observedRequiredSymbolCount??0),0);
  return Object.freeze({pointCount:points.length,fullCoveragePointCount:points.filter((row)=>Number(row.coverage.missingSymbolCount??0)===0).length,missingCoveragePointCount:points.filter((row)=>Number(row.coverage.missingSymbolCount??0)>0).length,requiredSymbolOccurrences:requiredOccurrences,observedRequiredSymbolOccurrences:observedOccurrences,occurrenceCoveragePercent:requiredOccurrences?100*observedOccurrences/requiredOccurrences:null,distinctMissingSymbolCount:missingSymbols.length,distinctMissingSymbols:Object.freeze(missingSymbols),diagnosticOnly:true});
}
function captureStartAttestation(captureRows,envelope){
  const declared=iso(envelope.predeclaredStartAt,"predeclaredStartAt");
  const valid=(captureRows??[]).map((row)=>{try{return {row,at:iso(row?.capturedAt,"capturedAt")};}catch{return null;}}).filter(Boolean).filter((x)=>jstDate(x.at)===envelope.sessionDate).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  if(!valid.length)return null;
  const firstObservedAt=valid[0].at,effectiveActualStartAt=Date.parse(firstObservedAt)<=Date.parse(declared)?declared:firstObservedAt;
  return Object.freeze({firstObservedAt,effectiveActualStartAt,predeclaredStartAt:declared,startedOnTime:effectiveActualStartAt===declared});
}
function envelopeWithCaptureAttestation(envelope,captureRows){const attestation=captureStartAttestation(captureRows,envelope);if(!attestation)return {envelope,attestation:null};return {envelope:{...envelope,actualStartAt:attestation.effectiveActualStartAt,methodology:{...(envelope.methodology??{}),laneMActualStartAttestedFromRawCapture:true,laneMFirstObservedCaptureAt:attestation.firstObservedAt,laneMStartedOnTime:attestation.startedOnTime}},attestation};}
function blockedSessionQuality(state,attestation){return (state?.actualStartAt||attestation?.effectiveActualStartAt)?"PARTIAL_INCOMPLETE_MSII":"SOURCE_NOT_READY";}

/** Missing evidence waits until the causal window closes, then blocks permanently. Diagnostics never upgrade a point. */
export function stepFullSession({envelopes,captureRows,sessionState,nowMs=Date.now(),referenceMaxAgeMs=5_000,ttlMs=5_000,decisionLatencyMs=100,settleGraceMs=1_000,transactionCostJpy=0}={}){
  assertSafety(SAFETY,"watcher");
  const ordered=[...(envelopes??[])].map((item)=>item.envelope?item:{envelope:item,decisionAt:iso(item?.pointResult?.at)}).sort((a,b)=>Date.parse(a.decisionAt)-Date.parse(b.decisionAt));
  let state={...sessionState,ledger:[...(sessionState?.ledger??[])],processedEvidenceHashes:[...(sessionState?.processedEvidenceHashes??[])],blockedPoints:[...(sessionState?.blockedPoints??[])],committedPoints:[...(sessionState?.committedPoints??[])],safety:SAFETY};
  const events=[];
  for(const item of ordered){
    const sourceEnvelope=item.envelope,decisionAt=iso(item.decisionAt??sourceEnvelope?.pointResult?.at);
    if(sourceEnvelope.sessionDate!==state.sessionDate)continue;
    if(state.lastDecisionAt&&Date.parse(decisionAt)<=Date.parse(state.lastDecisionAt))continue;
    const {envelope,attestation}=envelopeWithCaptureAttestation(sourceEnvelope,captureRows),coverage=diagnosePhase57MsiiPointCoverage(sourceEnvelope,captureRows,{referenceMaxAgeMs,ttlMs,decisionLatencyMs});
    try{
      const processed=processRawEnvelopeFile({envelope,captureRows,priorState:state,referenceMaxAgeMs,ttlMs,decisionLatencyMs,transactionCostJpy});
      state={...processed.nextState,blockedPoints:state.blockedPoints,committedPoints:[...state.committedPoints,{decisionAt,evidenceHash:processed.evidenceHash,captureRowCount:processed.captureRowCount,captureStartAttestation:attestation,coverage}],safety:SAFETY};
      events.push({status:"COMMITTED",decisionAt,evidenceHash:processed.evidenceHash,captureRowCount:processed.captureRowCount,captureStartAttestation:attestation,coverage,result:processed.result});
    }catch(error){
      const deadline=evidenceDeadlineMs(sourceEnvelope,{ttlMs,decisionLatencyMs,settleGraceMs}),message=String(error?.message??error);
      if(nowMs<deadline){events.push({status:"WAITING_FOR_CAUSAL_EVIDENCE",decisionAt,error:message,deadline:new Date(deadline).toISOString(),captureStartAttestation:attestation,coverage});break;}
      const blocked={decisionAt,status:"BLOCKED_CAUSAL_EVIDENCE_MISSING",reason:message,blockedAt:new Date(nowMs).toISOString(),backfillAllowed:false,captureStartAttestation:attestation,coverage};
      const missingCaptureCount=Math.max(Number(state.missingCaptureCount??0),state.blockedPoints.length+1),sessionQuality=blockedSessionQuality(state,attestation);
      state={...state,lastDecisionAt:decisionAt,actualStartAt:state.actualStartAt??attestation?.effectiveActualStartAt??null,blockedPoints:[...state.blockedPoints,blocked],missingCaptureCount,sessionQuality,safety:SAFETY};
      events.push({status:"BLOCKED",decisionAt,error:message,blocked,coverage,sessionQuality});
    }
  }
  return Object.freeze({state:Object.freeze(state),events:Object.freeze(events),coverageSummary:summarizeCoverage(state)});
}

async function main(){
  const args=parseArgs(process.argv.slice(2));
  const envelopeDir=required(args,"envelope-dir"),captureFile=required(args,"captures"),outputDir=required(args,"output-dir"),sessionDate=required(args,"session-date");
  const stateFile=String(args.state??path.join(outputDir,"full-session-state.json"));
  const pollMs=numeric(args,"poll-ms",1_000),referenceMaxAgeMs=numeric(args,"reference-max-age-ms",5_000),ttlMs=numeric(args,"ttl-ms",5_000),decisionLatencyMs=numeric(args,"decision-latency-ms",100),settleGraceMs=numeric(args,"settle-grace-ms",1_000),transactionCostJpy=numeric(args,"transaction-cost-jpy",0);
  const stopAt=args["stop-at"]?Date.parse(iso(args["stop-at"],"stop-at")):null;
  if(pollMs<200)throw new Error("--poll-ms must be >= 200");
  process.stdout.write(`${JSON.stringify({status:"PHASE57_MSII_FULL_SESSION_START",sessionDate,envelopeDir,captureFile,outputDir,pollMs,safety:SAFETY})}\n`);
  while(true){
    const now=Date.now();if(stopAt!==null&&now>=stopAt)break;
    const state=loadSessionState(stateFile,sessionDate),envelopes=listEnvelopeFiles(envelopeDir).map(envelopeMeta),captureRows=readJsonl(captureFile);
    const stepped=stepFullSession({envelopes,captureRows,sessionState:state,nowMs:now,referenceMaxAgeMs,ttlMs,decisionLatencyMs,settleGraceMs,transactionCostJpy});
    if(stepped.events.length){
      atomicWrite(stateFile,stepped.state);atomicWrite(path.join(outputDir,"coverage-latest.json"),stepped.coverageSummary);
      for(const event of stepped.events){
        if(event.status==="COMMITTED"){
          atomicWrite(path.join(outputDir,"latest-score.json"),{...event.result.score,sessionQuality:event.result.sessionQuality??stepped.state.sessionQuality??null,coverage:event.coverage});
          atomicWrite(path.join(outputDir,"latest-pair.json"),event.result.pair);
          atomicWrite(pointArtifactPath(outputDir,event.decisionAt,"COMMITTED"),{schemaVersion:3,...event,result:undefined,sessionQuality:event.result.sessionQuality??stepped.state.sessionQuality??null,score:event.result.score,pair:event.result.pair,safety:SAFETY});
        }else if(event.status==="BLOCKED")atomicWrite(pointArtifactPath(outputDir,event.decisionAt,"BLOCKED"),{schemaVersion:3,...event,safety:SAFETY});
        process.stdout.write(`${JSON.stringify({status:event.status,decisionAt:event.decisionAt,error:event.error??null,sessionQuality:event.sessionQuality??event.result?.sessionQuality??stepped.state.sessionQuality??null,coverage:event.coverage,captureStartAttestation:event.captureStartAttestation??event.blocked?.captureStartAttestation??null,safety:SAFETY})}\n`);
      }
    }
    await sleep(pollMs);
  }
  const state=loadSessionState(stateFile,sessionDate),coverageSummary=summarizeCoverage(state);
  atomicWrite(path.join(outputDir,"coverage-final.json"),coverageSummary);
  atomicWrite(path.join(outputDir,"full-session-final.json"),{schemaVersion:3,status:"PHASE57_MSII_FULL_SESSION_STOPPED",sessionDate,lastDecisionAt:state.lastDecisionAt,sessionQuality:state.sessionQuality??null,predeclaredStartAt:state.predeclaredStartAt??null,actualStartAt:state.actualStartAt??null,missingCaptureCount:Number(state.missingCaptureCount??0),committedPointCount:state.committedPoints.length,blockedPointCount:state.blockedPoints.length,ledgerEventCount:state.ledger.length,coverageSummary,backfillAllowed:false,safety:SAFETY});
  process.stdout.write(`${JSON.stringify({status:"PHASE57_MSII_FULL_SESSION_STOPPED",sessionDate,sessionQuality:state.sessionQuality??null,committedPointCount:state.committedPoints.length,blockedPointCount:state.blockedPoints.length,missingCaptureCount:Number(state.missingCaptureCount??0),coverageSummary,safety:SAFETY})}\n`);
  return 0;
}
const direct=process.argv[1]?import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href:false;
if(direct){main().then((code)=>{process.exitCode=code;}).catch((error)=>{process.stderr.write(`${JSON.stringify({status:"BLOCKED_PHASE57_MSII_FULL_SESSION",error:String(error?.message??error),safety:SAFETY})}\n`);process.exitCode=1;});}
export {captureStartAttestation as attestPhase57MsiiCaptureStart,summarizeCoverage as summarizePhase57MsiiCoverage,SAFETY as PHASE57_MSII_FULL_SESSION_SAFETY};
