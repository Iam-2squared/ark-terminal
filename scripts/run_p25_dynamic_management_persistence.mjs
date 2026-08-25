import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {runP253ALDynamicManagementMultisession,PHASE57_P25_3AL_SAFETY} from '../predict/daytrade/phase57-p25-3al-dynamic-management-multisession.js';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function readJson(file,label){const bytes=fs.readFileSync(file);let parsed;try{parsed=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`${label} JSON parse failed: ${error?.message??error}`);}return {parsed,sha256:sha(bytes)};}
function writeAtomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n','utf8');fs.renameSync(tmp,file);}
function uniqueSortedSymbols(sessions){return [...new Set((Array.isArray(sessions)?sessions:[]).map(session=>String(session?.symbol??'').trim()).filter(Boolean))].sort();}
function sameArray(a,b){return a.length===b.length&&a.every((value,index)=>value===b[index]);}

function buildCachedScorePrefix(historySessions){
  const actualHistoricalUniverse=uniqueSortedSymbols(historySessions);
  const expectedHistoricalUniverse=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
  if(!sameArray(actualHistoricalUniverse,expectedHistoricalUniverse))throw new Error(`P25.3AN frozen historical universe mismatch expected=${expectedHistoricalUniverse.join(',')} actual=${actualHistoricalUniverse.join(',')}`);
  const historyStartedAt=Date.now();
  const cachedHistory=buildProspectiveP21HistoricalRows({sessions:historySessions,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
  if(cachedHistory.complete!==true)throw new Error(`P25.3AN historical materialization blocked: ${cachedHistory.status}`);
  const diagnostics={historicalMaterializationCount:1,historicalMaterializationMs:Date.now()-historyStartedAt,scorerCallCount:0,scorerElapsedMs:0,priorOnlyCacheHitCount:0,priorOnlyCacheMissCount:0,priorOnlyCacheEntries:0};
  const priorOnlyCache=new Map();
  const scorePrefix=({currentPrefix})=>{
    const startedAt=Date.now();
    diagnostics.scorerCallCount+=1;
    try{
      const feed=buildProspectiveP21FeatureFeed({
        symbol:currentPrefix.symbol,
        sessionDate:currentPrefix.sessionDate,
        bars5m:currentPrefix.bars5m,
        horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,
        latestBarClosed:true,
      });
      if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
      const base=buildProspectiveP21FrozenDecision({
        historicalHorizonRowsByBars:cachedHistory.historicalHorizonRowsByBars,
        currentRowsByHorizon:feed.currentRowsByHorizon,
        options:PHASE58_P13_FROZEN_POLICY.selectionOptions,
        priorOnlyCache,
      });
      if(base.priorOnlyCacheHit===true)diagnostics.priorOnlyCacheHitCount+=1;
      else if(base.complete===true||String(base.status??'').startsWith('BLOCKED_NO_')||String(base.status??'').startsWith('ABSTAIN_NO_'))diagnostics.priorOnlyCacheMissCount+=1;
      if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
      if(!base.decision||typeof base.modelId!=='string'||!/^[a-f0-9]{64}$/i.test(String(base.artifactSha256??'')))return {complete:false,status:'BLOCKED_P21_PROVENANCE_NOT_READY'};
      const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
      if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
      return {
        complete:true,
        status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',
        policyId:PHASE58_P13_FROZEN_POLICY.policyId,
        currentSymbol:currentPrefix.symbol,
        snapshot:built.snapshot,
        phase57:{status:base.status,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256},
        provenance:{
          currentSymbol:currentPrefix.symbol,
          currentFeatureCutoff:feed.featureCutoff,
          currentSessionDate:currentPrefix.sessionDate,
          currentSourceBarCount:feed.sourceBarCount,
          currentPrefixStatus:currentPrefix.status??null,
        },
      };
    }finally{
      diagnostics.scorerElapsedMs+=Date.now()-startedAt;
      diagnostics.priorOnlyCacheEntries=priorOnlyCache.size;
    }
  };
  return {scorePrefix,diagnostics};
}

const historyPath=arg('--history-pack');
const captureDir=arg('--capture-dir');
const integrityPath=arg('--integrity-ledger');
const lineagePath=arg('--lineage-manifest');
const sessionDate=arg('--session-date');
const outputPath=arg('--output','data/p25-dynamic-management/evaluation.json');
const scorecardPath=arg('--scorecard','data/p25-dynamic-management/scorecard.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath){console.error('usage: node scripts/run_p25_dynamic_management_persistence.mjs --history-pack <json> --capture-dir <dir> --integrity-ledger <json> --lineage-manifest <json> [--session-date YYYY-MM-DD] [--output <json>] [--scorecard <json>]');process.exit(2);}
if(sessionDate&&!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)){console.error('invalid --session-date');process.exit(2);}

try{
  const history=readJson(historyPath,'history pack');
  const integrity=readJson(integrityPath,'session integrity ledger');
  const lineage=readJson(lineagePath,'evidence lineage manifest');
  const files=fs.readdirSync(captureDir).filter(name=>name.endsWith('.json')).sort();
  const captures=files.map(name=>{const file=path.join(captureDir,name),loaded=readJson(file,`capture ${name}`);return {artifact:loaded.parsed,artifactSha256:loaded.sha256,artifactPath:name};});
  const cachedScorer=buildCachedScorePrefix(history.parsed.sessions??[]);
  const evaluation=runP253ALDynamicManagementMultisession({historyPack:history.parsed,captureArtifacts:captures,sessionIntegrityLedger:integrity.parsed,lineageManifest:lineage.parsed,sessionDates:sessionDate?[sessionDate]:null,scorePrefix:cachedScorer.scorePrefix});
  const createdAt=new Date().toISOString();
  const payload={
    schemaVersion:1,
    phase:'57.p25.3an.dynamic-management-cached-sharded-persistence-cli',
    status:'P25_3AN_DYNAMIC_MANAGEMENT_SHARD_WRITTEN',
    createdAt,
    shard:{sessionDate:sessionDate??null,executionOnly:true},
    inputs:{
      historyPackSha256:history.sha256,
      integrityLedgerSha256:integrity.sha256,
      lineageManifestSha256:lineage.sha256,
      lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,
      captureArtifactCount:captures.length,
    },
    computeDiagnostics:{...cachedScorer.diagnostics},
    evaluation,
    methodology:{appendOnlyTarget:true,idempotentByEvidenceDateAndLineage:true,fixedBaselineUntouched:true,executionShardSelectionOnly:true,computeCacheOnly:true,historyMaterializedOncePerShard:true,priorOnlyCacheUsesExactFrozenScorer:true,resultBasedRetuning:false,winnerSelection:false,freshHoldoutConsumed:false},
    safety:PHASE57_P25_3AL_SAFETY,
  };
  const scorecard={
    schemaVersion:1,
    phase:'57.p25.3an.dynamic-management-cached-shard-scorecard',
    status:'P25_3AN_DYNAMIC_MANAGEMENT_SHARD_SCORECARD_READY',
    createdAt,
    shard:{sessionDate:sessionDate??null,executionOnly:true},
    lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,
    expectedSessionCount:evaluation.expectedSessionCount,
    readySessionCount:evaluation.readySessionCount,
    sessions:evaluation.sessions,
    summary:evaluation.summary,
    byVariant:evaluation.byVariant,
    computeDiagnostics:{...cachedScorer.diagnostics},
    methodology:{descriptiveOnly:true,fixedVsDynamicPaired:true,executionShardSelectionOnly:true,computeCacheOnly:true,winnerSelection:false,resultBasedRetuning:false,freshHoldoutConsumed:false},
    safety:PHASE57_P25_3AL_SAFETY,
  };
  writeAtomic(outputPath,payload);
  writeAtomic(scorecardPath,scorecard);
  console.log(JSON.stringify({status:payload.status,sessionDate:sessionDate??null,output:outputPath,outputSha256:sha(fs.readFileSync(outputPath)),scorecard:scorecardPath,scorecardSha256:sha(fs.readFileSync(scorecardPath)),lineageManifestHeadSha256:evaluation.lineageManifestHeadSha256,pairedCount:evaluation.summary.pairedCount,readySessionCount:evaluation.readySessionCount,computeDiagnostics:cachedScorer.diagnostics,safety:PHASE57_P25_3AL_SAFETY},null,2));
}catch(error){console.error(JSON.stringify({status:'BLOCKED_P25_3AN_DYNAMIC_MANAGEMENT_SHARD',sessionDate:sessionDate??null,error:String(error?.message??error),safety:PHASE57_P25_3AL_SAFETY},null,2));process.exit(1);}
