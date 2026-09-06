import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';

import {buildPhase57MinimalHybridTargets} from '../predict/daytrade/phase57-selector-minimal-hybrid-targets.js';
import {runPhase57MinimalHybrid} from '../predict/daytrade/phase57-selector-minimal-hybrid.js';
import {Phase57FreshSessionInternals} from './lib/phase57-selector-jquants-fresh-session.mjs';

const allocation=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const model=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-development-model.json',import.meta.url),'utf8'));
const freeze=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-development-freeze.json',import.meta.url),'utf8'));
const release=JSON.parse(fs.readFileSync(new URL('../predict/research/phase57-selector-minimal-hybrid-oos-release.json',import.meta.url),'utf8'));
const sha256=value=>createHash('sha256').update(value).digest('hex');
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

function findFiles(root,name){const found=[];for(const entry of fs.readdirSync(root,{withFileTypes:true})){const target=path.join(root,entry.name);if(entry.isDirectory())found.push(...findFiles(target,name));else if(entry.name===name)found.push(target);}return found.sort();}
function audits(root){return findFiles(root,'audit.json').flatMap(file=>JSON.parse(fs.readFileSync(file,'utf8')).sessionAudits??[]);}
function modelDigest(){const core={...model};delete core.modelDigest;return sha256(JSON.stringify(core));}
function freezeDigest(){const core={...freeze};delete core.freezeSha256;return sha256(JSON.stringify(core));}

async function withRetry(args){
  for(let attempt=0;attempt<6;attempt+=1){
    try{return await Phase57FreshSessionInternals.loadFreshSession({...args,paceMs:1800});}
    catch(error){if(String(error?.message??error)!=='RATE_LIMITED'||attempt===5)throw error;await sleep((attempt+1)*30000);}
  }
  throw new Error('CAPACITY_REPLAY_RATE_LIMIT_EXHAUSTED');
}

export async function evaluateCapacitySession({apiKey,date,fold,expectedAudit,fetchImpl=globalThis.fetch}={}){
  if(!['VALIDATION','UNTOUCHED_OOS'].includes(fold)||expectedAudit?.sessionDate!==date||expectedAudit?.fold!==fold)throw new Error('frozen opened-fold audit is required');
  const {structuralAudit,bySymbol}=await withRetry({apiKey,date,fold,fetchImpl});
  for(const key of ['minuteSha256','fiveMinuteSha256','memberSetSha256'])if(structuralAudit[key]!==expectedAudit[key])throw new Error(`capacity source drift: ${key}`);
  const entries=[...bySymbol.values()].map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars}));
  const records=[],points=[];
  for(const time of Phase57FreshSessionInternals.DECISION_TIMES){
    const {featureCutoff,rows:v1Rows}=Phase57FreshSessionInternals.v1AtCutoff({date,time,entries});
    const hybrid=runPhase57MinimalHybrid({featureCutoff,entries,model});
    const currentSelected=new Set(hybrid.selected.map(row=>row.symbol));
    const qualifiedCount=hybrid.ranked.filter(row=>row.stage2.remainingOpportunityScore>=model.selectionPolicy.minimumRemainingOpportunityScore).length;
    const marketBreadth=hybrid.ranked[0]?.features?.marketBreadth??null;
    points.push({fold,sessionDate:date,featureCutoff,timeOfDay:time,hybridSelectedCount:hybrid.selected.length,
      hybridEligibleCount:hybrid.ranked.length,hybridQualifiedCount:qualifiedCount,v1CandidateCount:v1Rows.length,marketBreadth});
    const decisionSegment=time<'12:00'?'AM':'PM',cutoffMs=Date.parse(featureCutoff);
    const arms={HYBRID:hybrid.ranked.map(row=>({symbol:row.symbol,rank:row.hybridRank,score:row.hybridScore,v1Rank:row.v1Rank,
      remainingOpportunityScore:row.stage2.remainingOpportunityScore,softAdjustment:row.softAdjustment,isCurrentSelected:currentSelected.has(row.symbol)})),
      V1:v1Rows.map((row,index)=>({symbol:row.symbol,rank:index+1,score:Number(row.opportunityScore),v1Rank:index+1,
        remainingOpportunityScore:null,softAdjustment:null,isCurrentSelected:true}))};
    for(const [selector,rows] of Object.entries(arms))for(const row of rows){
      const item=bySymbol.get(row.symbol);if(!item)continue;
      const causal=item.bars.filter(bar=>Date.parse(bar.availableAt)<=cutoffMs);if(!causal.length)continue;
      const current=causal.at(-1),futureBars=item.bars.filter(bar=>Date.parse(bar.availableAt)>cutoffMs&&bar.sessionSegment===decisionSegment);
      const targets=buildPhase57MinimalHybridTargets({featureCutoff,anchorPrice:current.close,sessionDate:date,futureBars});
      records.push({fold,sessionDate:date,featureCutoff,timeOfDay:time,symbol:row.symbol,selector,rank:row.rank,score:row.score,
        v1Rank:row.v1Rank,remainingOpportunityScore:row.remainingOpportunityScore,softAdjustment:row.softAdjustment,
        isCurrentSelected:row.isCurrentSelected,preSelectionMove:Math.abs(current.close/causal[0].open-1),marketBreadth,targetsByHorizon:targets.horizons});
    }
  }
  return {records,points};
}

export async function evaluateCapacityShard({apiKey,inputRoot,shardIndex,shardCount,fold}={}){
  if(!Number.isInteger(shardIndex)||!Number.isInteger(shardCount)||shardIndex<0||shardIndex>=shardCount)throw new Error('invalid shard coordinates');
  if(modelDigest()!==model.modelDigest||model.modelDigest!==release.expectedModelDigest)throw new Error('Frozen model digest mismatch');
  if(freezeDigest()!==freeze.freezeSha256||freeze.freezeSha256!==release.expectedHybridFreezeSha256)throw new Error('Frozen Hybrid digest mismatch');
  const sourceAudits=audits(inputRoot),byDate=new Map(sourceAudits.map(row=>[row.sessionDate,row]));
  const allDates=fold==='VALIDATION'?allocation.validation:allocation.untouchedOos;
  const dates=allDates.filter((_,index)=>index%shardCount===shardIndex),records=[],points=[];
  for(const [index,date] of dates.entries()){
    console.error(`CAPACITY_PROGRESS fold=${fold} shard=${shardIndex} session=${index+1}/${dates.length} date=${date}`);
    const result=await evaluateCapacitySession({apiKey,date,fold,expectedAudit:byDate.get(date)});records.push(...result.records);points.push(...result.points);
  }
  return {status:'POST_HOC_CAPACITY_SHARD_COMPLETE',fold,dates,records,points,modelDigest:model.modelDigest,freezeSha256:freeze.freezeSha256,
    frozenHybridChanged:false,retuningPerformed:false,reserveSessionsTouched:0,safety:release.safety};
}

async function main(){
  const shardIndex=Number(process.env.SHARD_INDEX),shardCount=Number(process.env.SHARD_COUNT),fold=String(process.env.FOLD??'');
  const result=await evaluateCapacityShard({apiKey:process.env.JQUANTS_API_KEY,inputRoot:process.env.INPUT_ROOT||'artifacts/capacity-input',shardIndex,shardCount,fold});
  const directory=`artifacts/phase57-capacity-${fold.toLowerCase()}-${shardIndex}`;fs.mkdirSync(directory,{recursive:true,mode:0o700});
  for(const [name,rows] of [['records',result.records],['points',result.points]]){const text=rows.map(row=>JSON.stringify(row)).join('\n')+'\n';fs.writeFileSync(`${directory}/${name}.ndjson.gz`,gzipSync(text),{mode:0o600});}
  const report={...result};delete report.records;delete report.points;fs.writeFileSync(`${directory}/report.json`,JSON.stringify(report,null,2)+'\n',{mode:0o600});
  console.log('PHASE57_CAPACITY_SHARD '+JSON.stringify({status:report.status,fold,sessionCount:report.dates.length,recordCount:result.records.length,pointCount:result.points.length,reserveSessionsTouched:0}));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(`PHASE57_CAPACITY_SHARD_FAIL ${String(error?.message??error)}`);process.exitCode=1;});

export const Phase57CapacityShardInternals=Object.freeze({findFiles,audits,modelDigest,freezeDigest});
