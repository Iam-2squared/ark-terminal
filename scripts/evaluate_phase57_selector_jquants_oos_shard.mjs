import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';

import {buildPhase57MinimalHybridTargets} from '../predict/daytrade/phase57-selector-minimal-hybrid-targets.js';
import {runPhase57MinimalHybrid} from '../predict/daytrade/phase57-selector-minimal-hybrid.js';
import {selectPhase57SelectorV3} from '../predict/daytrade/phase57-selector-v3.js';
import {Phase57FreshSessionInternals} from './lib/phase57-selector-jquants-fresh-session.mjs';

const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const release=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-oos-release.json',import.meta.url),'utf8'));
const sha256=value=>createHash('sha256').update(value).digest('hex');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function findFiles(root,name){const found=[];for(const entry of fs.readdirSync(root,{withFileTypes:true})){const target=path.join(root,entry.name);if(entry.isDirectory())found.push(...findFiles(target,name));else if(entry.name===name)found.push(target);}return found.sort();}
function one(root,name){const files=findFiles(root,name);if(files.length!==1)throw new Error(`expected one ${name}, received ${files.length}`);return JSON.parse(fs.readFileSync(files[0],'utf8'));}

async function evaluateWithRateLimitRetry(evaluate,args){
  for(let attempt=0;attempt<6;attempt+=1){
    try{return await evaluate({...args,paceMs:1800});}
    catch(error){
      if(String(error?.message??error)!=='RATE_LIMITED'||attempt===5)throw error;
      const delayMs=(attempt+1)*30000;
      console.error(`OOS_RATE_LIMIT_RETRY attempt=${attempt+1} delayMs=${delayMs}`);
      await sleep(delayMs);
    }
  }
  throw new Error('OOS_RATE_LIMIT_RETRY_EXHAUSTED');
}

async function evaluateSession({apiKey,date,expectedAudit,model,fetchImpl=globalThis.fetch,paceMs=1100}){
  if(expectedAudit?.fold!=='UNTOUCHED_OOS'||expectedAudit?.sessionDate!==date)throw new Error('frozen OOS structural audit is required');
  const {structuralAudit,bySymbol}=await Phase57FreshSessionInternals.loadFreshSession({apiKey,date,fold:'UNTOUCHED_OOS',fetchImpl,paceMs});
  for(const name of ['minuteSha256','fiveMinuteSha256','memberSetSha256'])if(structuralAudit[name]!==expectedAudit[name])throw new Error(`OOS source drift: ${name}`);
  const entries=[...bySymbol.values()].map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars}));
  const records=[],points=[];
  for(const time of Phase57FreshSessionInternals.DECISION_TIMES){
    const {featureCutoff,rows:v1Rows}=Phase57FreshSessionInternals.v1AtCutoff({date,time,entries});
    const v3=selectPhase57SelectorV3({featureCutoff,entries,threshold:0.7});
    const hybrid=runPhase57MinimalHybrid({featureCutoff,entries,model,baselineDiagnostics:{v3SelectedSymbols:v3.selected.map(row=>row.symbol)}});
    const arms={
      V1:v1Rows.map((row,index)=>({symbol:row.symbol,rank:index+1,score:Number(row.opportunityScore),remainingOpportunityScore:null})),
      V3:v3.selected.map(row=>({symbol:row.symbol,rank:row.rank,score:row.utilityScore,remainingOpportunityScore:null})),
      HYBRID:hybrid.selected.map(row=>({symbol:row.symbol,rank:row.hybridRank,score:row.hybridScore,remainingOpportunityScore:row.stage2.remainingOpportunityScore,v1Rank:row.v1Rank,softAdjustment:row.softAdjustment})),
    };
    points.push({sessionDate:date,featureCutoff,selectedCounts:Object.fromEntries(Object.entries(arms).map(([name,rows])=>[name,rows.length])),hybridStatus:hybrid.status});
    const decisionSegment=time<'12:00'?'AM':'PM',cutoffMs=Date.parse(featureCutoff);
    for(const [selector,selected] of Object.entries(arms))for(const row of selected){
      const item=bySymbol.get(row.symbol);if(!item)continue;
      const causal=item.bars.filter(bar=>Date.parse(bar.availableAt)<=cutoffMs);if(!causal.length)continue;
      const current=causal.at(-1),futureBars=item.bars.filter(bar=>Date.parse(bar.availableAt)>cutoffMs&&bar.sessionSegment===decisionSegment);
      const targets=buildPhase57MinimalHybridTargets({featureCutoff,anchorPrice:current.close,sessionDate:date,futureBars});
      records.push({sessionDate:date,featureCutoff,symbol:row.symbol,selector,rank:row.rank,score:row.score,
        v1Rank:row.v1Rank??(selector==='V1'?row.rank:null),softAdjustment:row.softAdjustment??null,remainingOpportunityScore:row.remainingOpportunityScore,
        preSelectionMove:Math.abs(current.close/causal[0].open-1),targetsByHorizon:targets.horizons});
    }
  }
  return {records,points,structuralHashesVerified:true};
}

export async function evaluateOosShard({apiKey,inputRoot,shardIndex,shardCount,evaluate=evaluateSession}={}){
  if(!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardIndex<0||shardIndex>=shardCount)throw new Error('invalid shard coordinates');
  const gate=one(inputRoot,'gate.json'),model=one(inputRoot,'model.json'),freeze=one(inputRoot,'freeze.json'),oosAudits=one(inputRoot,'oosAudits.json');
  if(gate.status!=='UNTOUCHED_OOS_INTEGRITY_PASS'||gate.reserveSessionsTouched!==0)throw new Error('OOS integrity gate did not pass');
  if(model.modelDigest!==release.expectedModelDigest||freeze.freezeSha256!==release.expectedHybridFreezeSha256||freeze.modelDigest!==model.modelDigest)throw new Error('frozen Hybrid mismatch');
  if(oosAudits.length!==24||new Set(oosAudits.map(row=>row.sessionDate)).size!==24)throw new Error('OOS audit set is incomplete');
  const byDate=new Map(oosAudits.map(row=>[row.sessionDate,row]));
  const dates=allocation.untouchedOos.filter((_,index)=>index%shardCount===shardIndex),records=[],points=[],sessionReports=[];
  for(const [index,date] of dates.entries()){
    console.error(`OOS_SHARD_PROGRESS shard=${shardIndex} session=${index+1}/${dates.length} date=${date}`);
    const result=await evaluateWithRateLimitRetry(evaluate,{apiKey,date,expectedAudit:byDate.get(date),model});
    records.push(...result.records);points.push(...result.points);
    sessionReports.push({sessionDate:date,status:'OOS_SESSION_EVALUATED_FROZEN_SELECTORS',recordCount:result.records.length,decisionCount:result.points.length,structuralHashesVerified:result.structuralHashesVerified});
  }
  return {status:'FROZEN_SELECTORS_UNTOUCHED_OOS_SHARD_COMPLETE',shardIndex,shardCount,dates,modelDigest:model.modelDigest,freezeSha256:freeze.freezeSha256,
    integrityGateSha256:gate.gateSha256,records,points,sessionReports,validationRetuningPerformed:false,modelMutationPerformed:false,
    untouchedOosReleased:true,reserveSessionsTouched:0,safety:release.safety};
}

async function main(){
  const shardIndex=Number(process.env.SHARD_INDEX),shardCount=Number(process.env.SHARD_COUNT);
  const result=await evaluateOosShard({apiKey:process.env.JQUANTS_API_KEY,inputRoot:process.env.INPUT_ROOT||'artifacts/phase57-oos-integrity',shardIndex,shardCount});
  const directory=`artifacts/phase57-jquants-oos-shard-${shardIndex}`;fs.mkdirSync(directory,{recursive:true,mode:0o700});
  const records=result.records,points=result.points,report={...result};delete report.records;delete report.points;
  const writeGzip=(name,rows)=>{const text=rows.map(row=>JSON.stringify(row)).join('\n')+(rows.length?'\n':'');fs.writeFileSync(`${directory}/${name}.ndjson.gz`,gzipSync(text),{mode:0o600});fs.writeFileSync(`${directory}/${name}.sha256`,`${sha256(text)}  ${name}.ndjson\n`,{mode:0o600});};
  writeGzip('oos-records',records);writeGzip('oos-points',points);
  const bytes=JSON.stringify(report,null,2)+'\n';fs.writeFileSync(`${directory}/oos-shard.json`,bytes,{mode:0o600});fs.writeFileSync(`${directory}/oos-shard.sha256`,`${sha256(bytes)}  oos-shard.json\n`,{mode:0o600});
  console.log('PHASE57_OOS_SHARD_REPORT '+JSON.stringify({status:report.status,shardIndex,sessionCount:report.dates.length,recordCount:records.length,
    decisionCount:points.length,modelDigest:report.modelDigest,freezeSha256:report.freezeSha256,reserveSessionsTouched:0,safety:report.safety}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`PHASE57_OOS_SHARD_FAIL ${String(error?.message??error)}`);process.exitCode=1;});

export const Phase57OosShardInternals=Object.freeze({findFiles,evaluateSession,evaluateWithRateLimitRetry});
