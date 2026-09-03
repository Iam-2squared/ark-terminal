#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { buildPhase57MsiiDynamicWatchlist, PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY } from "../predict/realtime/phase57-msii-dynamic-watchlist.js";

const SAFETY = Object.freeze({ ...PHASE57_MSII_DYNAMIC_WATCHLIST_SAFETY, mode: "LANE_M_DYNAMIC_WATCHLIST_WATCH" });
const FALSE_KEYS = Object.freeze(["executionAllowed","brokerWriteAllowed","excelOrderWriteAllowed","rssOrderFunctionAllowed","liveTradingAllowed","paperTradingAllowed","automaticPromotionAllowed","productionUpdateAllowed"]);
function assertSafety(){for(const key of FALSE_KEYS)if(SAFETY[key]!==false)throw new Error(`unsafe watchlist watcher ${key}`);if(SAFETY.excelMarketDataQueryWriteAllowed!==true)throw new Error("market-data query write scope must be explicit");}
function parseArgs(argv){const out={};for(let i=0;i<argv.length;i+=1){const token=argv[i];if(!token.startsWith("--"))throw new Error(`unexpected argument ${token}`);const key=token.slice(2),next=argv[i+1];if(next===undefined||next.startsWith("--"))out[key]=true;else{out[key]=next;i+=1;}}return out;}
function required(args,key){const value=args[key];if(value===undefined||value===true||String(value).trim()==="")throw new Error(`--${key} is required`);return String(value);}
function numeric(args,key,fallback){if(args[key]===undefined)return fallback;const value=Number(args[key]);if(!Number.isFinite(value))throw new Error(`--${key} must be numeric`);return value;}
function iso(value,label="timestamp"){const parsed=Date.parse(String(value??""));if(!Number.isFinite(parsed))throw new Error(`${label} invalid`);return new Date(parsed).toISOString();}
function readJson(file){return JSON.parse(fs.readFileSync(file,"utf8"));}
function atomicWrite(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const temp=`${file}.tmp-${process.pid}`;fs.writeFileSync(temp,`${JSON.stringify(value,null,2)}\n`,`utf8`);fs.renameSync(temp,file);}
function sleep(ms){return new Promise((resolve)=>setTimeout(resolve,ms));}
function listRaw(directory){if(!fs.existsSync(directory))return [];return fs.readdirSync(directory,{withFileTypes:true}).filter((x)=>x.isFile()&&x.name.endsWith(".json")).map((x)=>path.join(directory,x.name));}
function rawMeta(file){const payload=readJson(file);const observedAt=iso(payload?.meta?.observedAt,"raw observedAt");return {file,payload,observedAt};}
function normalizeSymbol(value){const raw=String(value??"").trim().toUpperCase();if(!raw)return "";if(/^\d+(?:\.0+)?$/.test(raw))return `${String(Math.trunc(Number(raw)))}.T`;return raw;}
function pinnedSymbolsFromLaneMState(file){
  if(!file||!fs.existsSync(file))return [];
  const state=readJson(file),latestFill=new Map(),intents=[];
  for(const row of state?.ledger??[]){
    if(row?.eventType==="SHADOW_ORDER_INTENT_COMMITTED"&&row.intent)intents.push(row.intent);
    if(row?.eventType==="SHADOW_FILL_COMMITTED"&&row.fill){const prior=latestFill.get(row.fill.intentId);if(!prior||Number(row.sequence)>Number(prior.sequence))latestFill.set(row.fill.intentId,row.fill);}
  }
  const inventory=new Map();
  intents.sort((a,b)=>Number(a.decisionSequence)-Number(b.decisionSequence));
  for(const intent of intents){const fill=latestFill.get(intent.intentId),qty=Number(fill?.filledQuantity??0);if(!(qty>0))continue;const symbol=normalizeSymbol(intent.symbol),key=`${intent.strategyId}|${symbol}`,prior=Number(inventory.get(key)??0);inventory.set(key,intent.intentKind==="ENTRY"?prior+qty:Math.max(0,prior-qty));}
  return [...new Set([...inventory.entries()].filter(([,qty])=>qty>0).map(([key])=>key.split("|").slice(1).join("|")))].sort();
}
function loadState(file,sessionDate){if(!fs.existsSync(file))return {schemaVersion:1,sessionDate,lastObservedAt:null,priorV2Selections:[],recentV1Selections:[],processedRaw:[],safety:SAFETY};const state=readJson(file);if(state.sessionDate!==sessionDate)throw new Error("dynamic watchlist state sessionDate mismatch");return state;}

export function processAvailableRawSnapshots({rawDirectory,sessionDate,state,slotCount=80,retentionPoints=3,laneMStateFile=null}={}){
  assertSafety();
  const files=listRaw(rawDirectory).map(rawMeta).filter((x)=>x.observedAt.startsWith(sessionDate)).sort((a,b)=>Date.parse(a.observedAt)-Date.parse(b.observedAt)||a.file.localeCompare(b.file));
  let next={...state,priorV2Selections:[...(state?.priorV2Selections??[])],recentV1Selections:[...(state?.recentV1Selections??[])],processedRaw:[...(state?.processedRaw??[])],safety:SAFETY};
  const outputs=[];
  for(const item of files){
    if(next.processedRaw.includes(path.basename(item.file)))continue;
    if(next.lastObservedAt&&Date.parse(item.observedAt)<=Date.parse(next.lastObservedAt)){next.processedRaw.push(path.basename(item.file));continue;}
    const pinned=pinnedSymbolsFromLaneMState(laneMStateFile);
    const watchlist=buildPhase57MsiiDynamicWatchlist({snapshot:item.payload,priorV2Selections:next.priorV2Selections,recentV1Selections:next.recentV1Selections,pinnedSymbols:pinned,slotCount,retentionPoints});
    if(watchlist.complete!==true){outputs.push({status:"BLOCKED",file:item.file,watchlist});break;}
    next={...next,lastObservedAt:item.observedAt,priorV2Selections:watchlist.v2PriorSelectionsNext,recentV1Selections:watchlist.recentV1SelectionsNext,processedRaw:[...next.processedRaw,path.basename(item.file)],safety:SAFETY};
    outputs.push({status:"READY",file:item.file,watchlist});
  }
  return {state:next,outputs};
}

async function main(){
  const args=parseArgs(process.argv.slice(2)),rawDirectory=required(args,"raw-dir"),output=required(args,"output"),stateFile=required(args,"state"),sessionDate=required(args,"session-date");
  const slotCount=numeric(args,"slot-count",80),retentionPoints=numeric(args,"retention-points",3),pollMs=numeric(args,"poll-ms",1000),laneMStateFile=args["lane-m-state"]?String(args["lane-m-state"]):null,stopAt=args["stop-at"]?Date.parse(iso(args["stop-at"],"stop-at")):null;
  if(pollMs<200)throw new Error("--poll-ms must be >= 200");
  process.stdout.write(`${JSON.stringify({status:"PHASE57_MSII_DYNAMIC_WATCHLIST_WATCH_START",sessionDate,rawDirectory,slotCount,retentionPoints,safety:SAFETY})}\n`);
  while(true){
    const now=Date.now();if(stopAt!==null&&now>=stopAt)break;
    const state=loadState(stateFile,sessionDate),processed=processAvailableRawSnapshots({rawDirectory,sessionDate,state,slotCount,retentionPoints,laneMStateFile});
    if(processed.outputs.length){
      atomicWrite(stateFile,processed.state);
      for(const item of processed.outputs){
        if(item.status==="READY"){
          atomicWrite(output,item.watchlist);
          process.stdout.write(`${JSON.stringify({status:item.watchlist.status,observedAt:item.watchlist.observedAt,assignedSymbolCount:item.watchlist.assignedSymbolCount,pinnedSymbolCount:item.watchlist.pinnedSymbols.length,retainedSymbolCount:item.watchlist.retainedSymbols.length,safety:SAFETY})}\n`);
        }else{
          process.stderr.write(`${JSON.stringify({status:item.watchlist.status,observedAt:item.watchlist.observedAt,requiredSymbolCount:item.watchlist.requiredSymbolCount,slotCount:item.watchlist.slotCount,overflowRequiredSymbols:item.watchlist.overflowRequiredSymbols,safety:SAFETY})}\n`);
          return 2;
        }
      }
    }
    await sleep(pollMs);
  }
  process.stdout.write(`${JSON.stringify({status:"PHASE57_MSII_DYNAMIC_WATCHLIST_WATCH_STOPPED",sessionDate,safety:SAFETY})}\n`);return 0;
}
const direct=process.argv[1]?import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href:false;
if(direct){main().then((code)=>{process.exitCode=code;}).catch((error)=>{process.stderr.write(`${JSON.stringify({status:"BLOCKED_PHASE57_MSII_DYNAMIC_WATCHLIST_WATCH",error:String(error?.message??error),safety:SAFETY})}\n`);process.exitCode=1;});}
export const PHASE57_MSII_DYNAMIC_WATCHLIST_WATCH_SAFETY=SAFETY;
