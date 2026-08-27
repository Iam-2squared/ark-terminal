import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {runP25ExitV2ProspectivePaired,P25_EXIT_V2_PROSPECTIVE_SAFETY} from '../predict/daytrade/phase57-p25-exit-v2-prospective.js';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function readJson(file,label){try{return JSON.parse(fs.readFileSync(file,'utf8'));}catch(error){throw new Error(`${label} JSON read failed: ${error?.message??error}`);}}
function readJsonWithSha(file,label){try{const bytes=fs.readFileSync(file);return {parsed:JSON.parse(bytes.toString('utf8')),sha256:sha(bytes)};}catch(error){throw new Error(`${label} JSON read failed: ${error?.message??error}`);}}
function writeAtomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n');fs.renameSync(tmp,file);}
function uniqueSortedSymbols(sessions){return [...new Set((Array.isArray(sessions)?sessions:[]).map(session=>String(session?.symbol??'').trim()).filter(Boolean))].sort();}
function sameArray(a,b){return a.length===b.length&&a.every((value,index)=>value===b[index]);}

function buildCachedScorePrefix(historySessions){
  const actualHistoricalUniverse=uniqueSortedSymbols(historySessions);
  const expectedHistoricalUniverse=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
  if(!sameArray(actualHistoricalUniverse,expectedHistoricalUniverse))throw new Error(`P25 EXIT v2 frozen historical universe mismatch expected=${expectedHistoricalUniverse.join(',')} actual=${actualHistoricalUniverse.join(',')}`);
  const cachedHistory=buildProspectiveP21HistoricalRows({sessions:historySessions,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
  if(cachedHistory.complete!==true)throw new Error(`P25 EXIT v2 historical materialization blocked: ${cachedHistory.status}`);
  const priorOnlyCache=new Map();
  return ({currentPrefix})=>{
    const feed=buildProspectiveP21FeatureFeed({symbol:currentPrefix.symbol,sessionDate:currentPrefix.sessionDate,bars5m:currentPrefix.bars5m,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,latestBarClosed:true});
    if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
    const base=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:cachedHistory.historicalHorizonRowsByBars,currentRowsByHorizon:feed.currentRowsByHorizon,options:PHASE58_P13_FROZEN_POLICY.selectionOptions,priorOnlyCache});
    if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
    if(!base.decision||typeof base.modelId!=='string'||!/^[a-f0-9]{64}$/i.test(String(base.artifactSha256??'')))return {complete:false,status:'BLOCKED_P21_PROVENANCE_NOT_READY'};
    const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
    if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
    return {complete:true,status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',policyId:PHASE58_P13_FROZEN_POLICY.policyId,currentSymbol:currentPrefix.symbol,snapshot:built.snapshot,phase57:{status:base.status,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256},provenance:{currentSymbol:currentPrefix.symbol,currentFeatureCutoff:feed.featureCutoff,currentSessionDate:currentPrefix.sessionDate,currentSourceBarCount:feed.sourceBarCount,currentPrefixStatus:currentPrefix.status??null}};
  };
}

const historyPath=arg('--history-pack'),captureDir=arg('--capture-dir'),integrityPath=arg('--integrity-ledger'),lineagePath=arg('--lineage-manifest'),freshSessionDate=arg('--fresh-session-date'),outputPath=arg('--output','data/p25-exit-v2/prospective.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath||!freshSessionDate){console.error('usage: node scripts/run_p25_exit_v2_prospective.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> --fresh-session-date YYYY-MM-DD [--output <json>]');process.exit(2);}
try{
  const historyPack=readJson(historyPath,'history pack');
  const captureArtifacts=fs.readdirSync(captureDir).filter(x=>x.endsWith('.json')).sort().map(name=>{const loaded=readJsonWithSha(path.join(captureDir,name),`capture ${name}`);return {artifact:loaded.parsed,artifactSha256:loaded.sha256,artifactPath:name};});
  const scorePrefix=buildCachedScorePrefix(historyPack.sessions??[]);
  const result=runP25ExitV2ProspectivePaired({historyPack,captureArtifacts,sessionIntegrityLedger:readJson(integrityPath,'integrity ledger'),lineageManifest:readJson(lineagePath,'lineage manifest'),freshSessionDate,scorePrefix});
  const payload={schemaVersion:1,phase:result.phase,status:result.status,createdAt:new Date().toISOString(),result,methodology:{...result.methodology,computeCacheOnly:true,priorOnlyCacheUsesExactFrozenScorer:true},safety:P25_EXIT_V2_PROSPECTIVE_SAFETY};
  writeAtomic(outputPath,payload);
  console.log(JSON.stringify({status:payload.status,output:outputPath,freshSessionDate,pairedCount:result.summary.pairedCount,fixed:result.summary.fixed,v2:result.summary.v2,delta:result.summary.delta,safety:P25_EXIT_V2_PROSPECTIVE_SAFETY},null,2));
}catch(error){console.error(JSON.stringify({status:'BLOCKED_P25_EXIT_V2_PROSPECTIVE',error:String(error?.message??error),freshSessionDate,safety:P25_EXIT_V2_PROSPECTIVE_SAFETY},null,2));process.exit(1);}
