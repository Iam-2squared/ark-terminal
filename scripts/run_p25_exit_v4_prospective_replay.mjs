import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {runP25ExitV4ProspectiveReplay,P25_EXIT_V4_PROSPECTIVE_SAFETY} from '../predict/daytrade/phase57-p25-exit-v4-prospective-replay.js';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const readJson=(f,l)=>{try{return JSON.parse(fs.readFileSync(f,'utf8'));}catch(e){throw new Error(`${l} JSON read failed: ${e?.message??e}`);}};
const readJsonWithSha=(f,l)=>{try{const b=fs.readFileSync(f);return {parsed:JSON.parse(b.toString('utf8')),sha256:sha(b)};}catch(e){throw new Error(`${l} JSON read failed: ${e?.message??e}`);}};
const writeAtomic=(f,v)=>{fs.mkdirSync(path.dirname(f),{recursive:true});const t=`${f}.tmp-${process.pid}`;fs.writeFileSync(t,JSON.stringify(v,null,2)+'\n');fs.renameSync(t,f);};
const uniq=s=>[...new Set((s??[]).map(x=>String(x?.symbol??'').trim()).filter(Boolean))].sort();
const same=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);

function buildCachedScorePrefix(historySessions){
  const actual=uniq(historySessions),expected=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
  if(!same(actual,expected))throw new Error('P25 EXIT v4 replay frozen historical universe mismatch');
  const cached=buildProspectiveP21HistoricalRows({sessions:historySessions,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
  if(cached.complete!==true)throw new Error(`P25 EXIT v4 replay historical materialization blocked: ${cached.status}`);
  const priorOnlyCache=new Map();
  return ({currentPrefix})=>{
    const feed=buildProspectiveP21FeatureFeed({symbol:currentPrefix.symbol,sessionDate:currentPrefix.sessionDate,bars5m:currentPrefix.bars5m,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,latestBarClosed:true});
    if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
    const base=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:cached.historicalHorizonRowsByBars,currentRowsByHorizon:feed.currentRowsByHorizon,options:PHASE58_P13_FROZEN_POLICY.selectionOptions,priorOnlyCache});
    if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
    const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
    if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
    return {complete:true,status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',policyId:PHASE58_P13_FROZEN_POLICY.policyId,currentSymbol:currentPrefix.symbol,snapshot:built.snapshot,phase57:{status:base.status,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256}};
  };
}

const historyPath=arg('--history-pack'),captureDir=arg('--capture-dir'),integrityPath=arg('--integrity-ledger'),lineagePath=arg('--lineage-manifest'),sessionDate=arg('--session-date'),outputPath=arg('--output','data/p25-exit-v4/prospective.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath||!sessionDate)throw new Error('usage: --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --session-date YYYY-MM-DD [--output <json>]');
try{
  const historyPack=readJson(historyPath,'history pack');
  const captures=fs.readdirSync(captureDir).filter(x=>x.endsWith('.json')).sort().map(name=>{const x=readJsonWithSha(path.join(captureDir,name),`capture ${name}`);return {artifact:x.parsed,artifactSha256:x.sha256,artifactPath:name};});
  const result=runP25ExitV4ProspectiveReplay({historyPack,captureArtifacts:captures,sessionIntegrityLedger:readJson(integrityPath,'integrity ledger'),lineageManifest:readJson(lineagePath,'lineage manifest'),sessionDate,scorePrefix:buildCachedScorePrefix(historyPack.sessions??[])});
  const payload={schemaVersion:1,phase:result.phase,status:result.status,createdAt:new Date().toISOString(),result,methodology:{...result.methodology,appendOnlyProspective:true},safety:P25_EXIT_V4_PROSPECTIVE_SAFETY};
  writeAtomic(outputPath,payload);
  console.log(JSON.stringify({status:payload.status,sessionDate,classification:result.classification,pairedCount:result.summary.pairedCount,fixed:result.summary.fixed,v4:result.summary.v4,delta:result.summary.delta},null,2));
}catch(e){console.error(JSON.stringify({status:'BLOCKED_P25_EXIT_V4_PROSPECTIVE_REPLAY',error:String(e?.message??e),sessionDate,safety:P25_EXIT_V4_PROSPECTIVE_SAFETY},null,2));process.exit(1);}
