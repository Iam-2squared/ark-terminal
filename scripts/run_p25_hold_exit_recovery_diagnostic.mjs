import fs from 'node:fs';
import path from 'node:path';
import {assembleP253AutonomousEvidenceInputs} from '../predict/daytrade/phase57-p25-3d-autonomous-evidence-evaluation.js';
import {runP253AKDynamicManagementSession,buildP253AKManagementRows} from '../predict/daytrade/phase57-p25-3ak-dynamic-management-prospective.js';
import {evaluateP25HoldExitRecoveryDiagnostic,P25_HOLD_EXIT_RECOVERY_SAFETY} from '../predict/daytrade/phase57-p25-hold-exit-recovery-diagnostic.js';
import {buildProspectiveP21HistoricalRows} from '../predict/daytrade/phase57-p21-prospective-history.js';
import {buildProspectiveP21FeatureFeed} from '../predict/daytrade/phase57-p21-prospective-feature-feed.js';
import {buildProspectiveP21FrozenDecision} from '../predict/daytrade/phase57-p21-prospective-frozen-base.js';
import {buildFrozenPhase57SnapshotFromRuntimeDecision} from '../predict/scalping/phase58-phase57-runtime-adapter.js';
import {PHASE58_P13_FROZEN_POLICY} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const uniqueSortedSymbols=sessions=>[...new Set((sessions??[]).map(s=>String(s?.symbol??'').trim()).filter(Boolean))].sort();
const sameArray=(a,b)=>a.length===b.length&&a.every((v,i)=>v===b[i]);

function buildCachedScorePrefix(historySessions){
  const actual=uniqueSortedSymbols(historySessions),expected=[...PHASE58_P13_FROZEN_POLICY.historicalUniverse].sort();
  if(!sameArray(actual,expected))throw new Error(`frozen historical universe mismatch expected=${expected.join(',')} actual=${actual.join(',')}`);
  const cachedHistory=buildProspectiveP21HistoricalRows({sessions:historySessions,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars});
  if(cachedHistory.complete!==true)throw new Error(`historical materialization blocked: ${cachedHistory.status}`);
  const priorOnlyCache=new Map();
  return ({currentPrefix})=>{
    const feed=buildProspectiveP21FeatureFeed({symbol:currentPrefix.symbol,sessionDate:currentPrefix.sessionDate,bars5m:currentPrefix.bars5m,horizons:PHASE58_P13_FROZEN_POLICY.horizonsBars,latestBarClosed:true});
    if(!feed.complete)return {complete:false,status:'BLOCKED_P21_CURRENT_FEATURE_FEED'};
    const base=buildProspectiveP21FrozenDecision({historicalHorizonRowsByBars:cachedHistory.historicalHorizonRowsByBars,currentRowsByHorizon:feed.currentRowsByHorizon,options:PHASE58_P13_FROZEN_POLICY.selectionOptions,priorOnlyCache});
    if(!base.complete)return {complete:false,status:'BLOCKED_P21_PROSPECTIVE_BASE'};
    const built=buildFrozenPhase57SnapshotFromRuntimeDecision({decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256});
    if(!built.complete)return {complete:false,status:'BLOCKED_PHASE57_RUNTIME_ADAPTER'};
    return {complete:true,status:'PHASE57_PROSPECTIVE_SNAPSHOT_READY',policyId:PHASE58_P13_FROZEN_POLICY.policyId,currentSymbol:currentPrefix.symbol,snapshot:built.snapshot,phase57:{status:base.status,decision:base.decision,modelId:base.modelId,artifactSha256:base.artifactSha256},provenance:{currentSymbol:currentPrefix.symbol,currentFeatureCutoff:feed.featureCutoff,currentSessionDate:currentPrefix.sessionDate,currentSourceBarCount:feed.sourceBarCount,currentPrefixStatus:currentPrefix.status??null}};
  };
}

const historyPath=arg('--history-pack'),captureDir=arg('--capture-dir'),integrityPath=arg('--integrity-ledger'),lineagePath=arg('--lineage-manifest'),sessionDate=arg('--session-date'),outputPath=arg('--output','/tmp/p25-hold-exit-recovery.json');
if(!historyPath||!captureDir||!integrityPath||!lineagePath||!sessionDate)throw new Error('missing required diagnostic inputs');
const history=read(historyPath),integrity=read(integrityPath),lineage=read(lineagePath);
const captures=fs.readdirSync(captureDir).filter(n=>n.endsWith('.json')).sort().map(name=>({artifact:read(path.join(captureDir,name)),artifactPath:name}));
const assembled=assembleP253AutonomousEvidenceInputs({historyPack:history,captureArtifacts:captures,sessionIntegrityLedger:integrity,lineageManifest:lineage});
const input=assembled.sessionInputs.find(x=>String(x?.universeRecord?.sessionDate??'')===String(sessionDate));
if(!input)throw new Error(`session not ready ${sessionDate}`);
const scorePrefix=buildCachedScorePrefix(assembled.historicalSessions);
const base=runP253AKDynamicManagementSession({universeRecord:input.universeRecord,historicalSessions:assembled.historicalSessions,sessionBarsBySymbol:input.sessionBarsBySymbol??{},scorePrefix});
const adapted=buildP253AKManagementRows({frozenTrades:base.replay?.ledger?.frozenTrades??[],sessionBarsBySymbol:input.sessionBarsBySymbol??{}});
const diagnostic=evaluateP25HoldExitRecoveryDiagnostic({frozenEntryRows:adapted.rows,fixedResolvedTrades:base.fixedOutcomes?.resolvedTrades??[]});
const variantByKey=new Map((base.replay?.ledger?.frozenTrades??[]).map(x=>[`${x.sessionDate}|${x.entryTimestamp}|${String(x.symbol).toUpperCase()}`,x.variantMemberships??[]]));
const pairs=diagnostic.pairs.map(p=>({...p,variantMemberships:variantByKey.get(p.key)??[]}));
const out={schemaVersion:1,phase:'57.p25.recovery.r1-r2.session',status:'HOLD_EXIT_RECOVERY_SESSION_READY',sessionDate,lineageManifestHeadSha256:assembled.lineageManifestHeadSha256,frozenTradeCount:base.adapterAudit.frozenTradeCount,fixedResolvedCount:base.adapterAudit.fixedResolvedCount,pairedCount:pairs.length,diagnostic:{...diagnostic,pairs},methodology:{diagnosticOnly:true,p247RiskExactReplayClaimed:false,noParameterRetuning:true,freshHoldoutConsumed:false},safety:P25_HOLD_EXIT_RECOVERY_SAFETY};
fs.mkdirSync(path.dirname(outputPath),{recursive:true});fs.writeFileSync(outputPath,JSON.stringify(out,null,2)+'\n');
console.log(JSON.stringify({status:out.status,sessionDate,pairedCount:out.pairedCount,summary:diagnostic.summary,limitations:diagnostic.limitations,safety:out.safety},null,2));
