#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { processRawProspectiveMsiiPoint } from "../predict/realtime/phase57-msii-raw-prospective-runtime.js";

const SAFETY = Object.freeze({
  mode:"LANE_M_RAW_E2E_READ_ONLY", executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false, liveTradingAllowed:false, paperTradingAllowed:false, automaticPromotionAllowed:false,
  productionUpdateAllowed:false, transmitted:false,
});
const FALSE_KEYS=["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"];
function parseArgs(argv){const out={};for(let i=0;i<argv.length;i+=1){const token=argv[i];if(!token.startsWith("--"))throw new Error(`unexpected argument ${token}`);const key=token.slice(2),next=argv[i+1];if(next===undefined||next.startsWith("--"))out[key]=true;else{out[key]=next;i+=1;}}return out;}
function required(args,key){const v=args[key];if(v===undefined||v===true||String(v).trim()==="")throw new Error(`--${key} is required`);return String(v);}
function numeric(args,key,fallback){if(args[key]===undefined)return fallback;const v=Number(args[key]);if(!Number.isFinite(v))throw new Error(`--${key} must be numeric`);return v;}
function iso(value,label="timestamp"){const parsed=Date.parse(String(value??""));if(!Number.isFinite(parsed))throw new Error(`${label} invalid`);return new Date(parsed).toISOString();}
function assertSafety(value,label){if(!value||typeof value!=="object")throw new Error(`${label} safety required`);for(const key of FALSE_KEYS)if(value[key]!==false)throw new Error(`${label}.${key} must remain false`);}
function canonical(value){if(Array.isArray(value))return value.map(canonical);if(value&&typeof value==="object")return Object.fromEntries(Object.keys(value).sort().map((key)=>[key,canonical(value[key])]));return value;}
function sha256(value){return crypto.createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex");}
function readJson(file){return JSON.parse(fs.readFileSync(file,"utf8"));}
function readJsonl(file){if(!fs.existsSync(file))return [];return fs.readFileSync(file,"utf8").split(/\r?\n/).filter((line)=>line.trim()).map((line,index)=>{try{return JSON.parse(line);}catch(error){throw new Error(`invalid JSONL ${file}:${index+1}: ${error.message}`);}});}
function atomicWrite(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const temp=`${file}.tmp-${process.pid}`;fs.writeFileSync(temp,`${JSON.stringify(value,null,2)}\n`,"utf8");fs.renameSync(temp,file);}
function normalizeSymbol(value){const raw=String(value??"").trim().toUpperCase();if(/^\d+(?:\.0+)?$/.test(raw))return `${String(Math.trunc(Number(raw)))}.T`;return raw;}
function requiredSymbols(envelope){const accepted=envelope?.pointResult?.allocation?.decisions??[];const closed=envelope?.pointResult?.exitEvaluation?.closed??[];return [...new Set([...accepted.filter((x)=>x?.status==="ACCEPTED").map((x)=>normalizeSymbol(x.symbol)),...closed.map((x)=>normalizeSymbol(x.symbol))].filter(Boolean))].sort();}
function captureSlice(rows,envelope,{referenceMaxAgeMs,ttlMs,decisionLatencyMs}){
  const decision=Date.parse(iso(envelope?.pointResult?.at,"pointResult.at"));
  const min=decision-referenceMaxAgeMs;
  const max=decision+Math.max(ttlMs,decisionLatencyMs);
  const symbols=new Set(requiredSymbols(envelope));
  return rows.filter((row)=>symbols.has(normalizeSymbol(row?.symbol))&&Number.isFinite(Date.parse(row?.capturedAt))&&Date.parse(row.capturedAt)>=min&&Date.parse(row.capturedAt)<=max)
    .sort((a,b)=>Date.parse(a.capturedAt)-Date.parse(b.capturedAt)||normalizeSymbol(a.symbol).localeCompare(normalizeSymbol(b.symbol)));
}

export function processRawEnvelopeFile({envelope,captureRows,priorState={},referenceMaxAgeMs=5000,ttlMs=5000,decisionLatencyMs=100,transactionCostJpy=0}={}){
  assertSafety(SAFETY,"coordinator");
  assertSafety(envelope?.safety,"envelope");
  if(envelope.backfillUsed===true)throw new Error("raw Lane M coordinator forbids backfill");
  const decisionAt=iso(envelope?.pointResult?.at,"pointResult.at");
  if(priorState.lastDecisionAt&&Date.parse(decisionAt)<=Date.parse(priorState.lastDecisionAt))throw new Error("raw Lane M decisionAt must move strictly forward");
  if(priorState.sessionDate&&priorState.sessionDate!==envelope.sessionDate)throw new Error("raw Lane M prior session mismatch");
  const slice=captureSlice(captureRows,envelope,{referenceMaxAgeMs,ttlMs,decisionLatencyMs});
  if(!slice.length)throw new Error("no raw MarketSpeed evidence in causal decision window");
  const evidenceHash=sha256({decisionAt,rows:slice});
  if((priorState.processedEvidenceHashes??[]).includes(evidenceHash))throw new Error("raw Lane M evidence already processed");
  const result=processRawProspectiveMsiiPoint({
    sessionDate:envelope.sessionDate, predeclaredStartAt:envelope.predeclaredStartAt, actualStartAt:envelope.actualStartAt,
    missingCaptureCount:Number(envelope.missingCaptureCount??0), initialCapital:Number(envelope.initialCapital??1_000_000),
    priorLedger:Array.isArray(priorState.ledger)?priorState.ledger:[], captureRows:slice,
    phase57State:envelope.phase57State, pointResult:envelope.pointResult, versions:envelope.versions,
    orderStyleResearchLabel:envelope.orderStyleResearchLabel??"MARKETABLE_QUOTE", ttlMs, decisionLatencyMs, referenceMaxAgeMs,
    transactionCostJpy, laneYDecisions:Array.isArray(envelope.laneYDecisions)?envelope.laneYDecisions:[],
  });
  if(result.complete!==true)throw new Error(`raw Lane M runtime blocked: ${result.status} ${(result.missingReferenceSymbols??[]).join(",")}`);
  const nextState=Object.freeze({schemaVersion:1,version:"phase57-msii-raw-e2e-r1",sessionDate:envelope.sessionDate,lastDecisionAt:decisionAt,processedEvidenceHashes:Object.freeze([...(priorState.processedEvidenceHashes??[]),evidenceHash]),ledger:result.ledger,safety:SAFETY});
  return Object.freeze({result,nextState,evidenceHash,captureRowCount:slice.length});
}

function main(){
  const args=parseArgs(process.argv.slice(2));
  const envelope=readJson(required(args,"envelope"));
  const captureRows=readJsonl(required(args,"captures"));
  const outputDir=required(args,"output-dir");
  const stateFile=String(args.state??path.join(outputDir,"state.json"));
  const priorState=fs.existsSync(stateFile)?readJson(stateFile):{};
  const processed=processRawEnvelopeFile({
    envelope,captureRows,priorState,
    referenceMaxAgeMs:numeric(args,"reference-max-age-ms",Number(envelope.referenceMaxAgeMs??5000)),
    ttlMs:numeric(args,"ttl-ms",Number(envelope.ttlMs??5000)),
    decisionLatencyMs:numeric(args,"decision-latency-ms",Number(envelope.decisionLatencyMs??100)),
    transactionCostJpy:numeric(args,"transaction-cost-jpy",Number(envelope.transactionCostJpy??0)),
  });
  const stamp=processed.nextState.lastDecisionAt.replace(/[-:.]/g,"");
  atomicWrite(stateFile,processed.nextState);
  atomicWrite(path.join(outputDir,"latest-score.json"),processed.result.score);
  atomicWrite(path.join(outputDir,"latest-pair.json"),processed.result.pair);
  atomicWrite(path.join(outputDir,"points",`${stamp}.json`),{schemaVersion:1,status:"PHASE57_MSII_RAW_E2E_POINT_COMMITTED",sessionDate:envelope.sessionDate,decisionAt:processed.nextState.lastDecisionAt,evidenceHash:processed.evidenceHash,captureRowCount:processed.captureRowCount,score:processed.result.score,pair:processed.result.pair,safety:SAFETY});
  process.stdout.write(`${JSON.stringify({status:"PHASE57_MSII_RAW_E2E_POINT_COMMITTED",decisionAt:processed.nextState.lastDecisionAt,captureRowCount:processed.captureRowCount,ledgerEventCount:processed.nextState.ledger.length,fillRatePercent:processed.result.score?.fillRatePercent??null,pairCount:processed.result.pair?.pairCount??0,safety:SAFETY})}\n`);
  return 0;
}
const direct=process.argv[1]?import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href:false;
if(direct){try{process.exitCode=main();}catch(error){process.stderr.write(`${JSON.stringify({status:"BLOCKED_PHASE57_MSII_RAW_E2E",error:String(error?.message??error),safety:SAFETY})}\n`);process.exitCode=1;}}
export const PHASE57_MSII_RAW_E2E_SAFETY=SAFETY;
