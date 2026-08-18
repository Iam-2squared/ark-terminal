import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {
  buildPhase57ProspectiveSnapshotPipeline,
  PHASE58_P13_FROZEN_POLICY,
  PHASE58_TARGET_MODES,
} from '../predict/scalping/phase58-phase57-prospective-pipeline.js';

const SAFETY=Object.freeze({
  phase:'58.p16.phase57-prospective-snapshot-cli',
  mode:'READ_ONLY_REUSABLE_LIVE_TARGET',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

const SOURCE_BAR_MINUTES=5;

function arg(name,fallback=null){
  const i=process.argv.indexOf(name);
  return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;
}
function flag(name){return process.argv.includes(name);}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}
function readJson(file,label){
  let bytes;
  try{bytes=fs.readFileSync(file);}catch(error){throw new Error(`${label} read failed: ${error?.message??error}`);}
  let parsed;
  try{parsed=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`${label} JSON failed: ${error?.message??error}`);}
  return {bytes,parsed,sha256:sha(bytes)};
}
function addMinutesIso(timestamp,minutes){
  const ms=Date.parse(timestamp??'');
  return Number.isFinite(ms)?new Date(ms+minutes*60_000).toISOString():null;
}

const historyPath=arg('--history-pack');
const currentPath=arg('--current-prefix');
const outputPath=arg('--output','data/phase58/live-phase57-snapshot.json');
const reusable=flag('--reusable-target');
if(!historyPath||!currentPath){
  console.error('usage: node tools/phase58_phase57_prospective_snapshot.mjs --history-pack <json> --current-prefix <json> [--reusable-target] [--output <json>]');
  process.exit(2);
}

let history,current;
try{
  history=readJson(historyPath,'history pack');
  current=readJson(currentPath,'current prefix');
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_PHASE57_PROSPECTIVE_INPUT',error:String(error?.message??error),safety:SAFETY},null,2));
  process.exit(1);
}

const pack=history.parsed??{};
if(pack.status!=='PHASE58_FROZEN_UNIVERSE_5M_HISTORY_PACK_READY'||!Array.isArray(pack.sessions)){
  console.error(JSON.stringify({status:'BLOCKED_INVALID_HISTORY_PACK',historyPackStatus:pack.status??null,safety:SAFETY},null,2));
  process.exit(1);
}
if(pack.methodology?.currentSessionExcludedFromTrainingHistory!==true||pack.methodology?.frozenP24CombinedUniverseRequired!==true){
  console.error(JSON.stringify({status:'BLOCKED_HISTORY_PACK_INTEGRITY',methodology:pack.methodology??null,safety:SAFETY},null,2));
  process.exit(1);
}
if(current.parsed?.status!=='PHASE58_RSSCHART_5M_PREFIX_READY'||current.parsed?.latestBarClosed!==true){
  console.error(JSON.stringify({status:'BLOCKED_INVALID_CURRENT_PREFIX',currentPrefixStatus:current.parsed?.status??null,safety:SAFETY},null,2));
  process.exit(1);
}
if(String(pack.asOfSessionDate??'')!==String(current.parsed.sessionDate??'')){
  console.error(JSON.stringify({status:'BLOCKED_HISTORY_CURRENT_CUTOFF_MISMATCH',historyAsOfSessionDate:pack.asOfSessionDate??null,currentSessionDate:current.parsed.sessionDate??null,safety:SAFETY},null,2));
  process.exit(1);
}

const targetMode=reusable?PHASE58_TARGET_MODES.REUSABLE_RESEARCH_TARGET:PHASE58_TARGET_MODES.FROZEN_UNIVERSE_ONLY;
const result=buildPhase57ProspectiveSnapshotPipeline({
  historicalSessions:pack.sessions,
  currentPrefix:current.parsed,
  policy:PHASE58_P13_FROZEN_POLICY,
  targetMode,
});
if(!result.complete){
  console.error(JSON.stringify({status:'BLOCKED_PHASE57_PROSPECTIVE_PIPELINE',pipeline:result,historyPackSha256:history.sha256,currentPrefixSha256:current.sha256,safety:SAFETY},null,2));
  process.exit(1);
}

// RssChart 5M timestamps identify the five-minute source interval. The exporter
// drops the newest visible interval and only marks the retained prefix as closed.
// Freshness therefore starts when the retained source bar is fully available
// (timestamp + 5 minutes), not at the interval's opening timestamp.
const sourceBarTimestamp=result.snapshot?.asOf??null;
const sourceBarCloseAt=addMinutesIso(sourceBarTimestamp,SOURCE_BAR_MINUTES);
if(!sourceBarCloseAt){
  console.error(JSON.stringify({status:'BLOCKED_PHASE57_SOURCE_BAR_FRESHNESS_METADATA',sourceBarTimestamp,safety:SAFETY},null,2));
  process.exit(1);
}
const snapshot=Object.freeze({
  ...result.snapshot,
  context:Object.freeze({
    ...(result.snapshot?.context??{}),
    sourceBarTimestamp,
    sourceBarDurationMinutes:SOURCE_BAR_MINUTES,
    sourceBarCloseAt,
  }),
});

const payload={
  schemaVersion:1,
  phase:'58.p16.phase57-prospective-snapshot-cli',
  status:'PHASE57_FROZEN_PROSPECTIVE_SNAPSHOT_WRITTEN',
  createdAt:new Date().toISOString(),
  targetMode,
  currentSymbol:result.provenance.currentSymbol,
  targetWithinFrozenHistoricalUniverse:result.targetWithinFrozenHistoricalUniverse,
  outOfTrainingUniverseResearch:result.outOfTrainingUniverseResearch,
  promotionEvidence:false,
  targetGeneralizationClaimAllowed:false,
  historyPackSha256:history.sha256,
  currentPrefixSha256:current.sha256,
  policyId:result.policyId,
  policyFrozen:result.policyFrozen,
  snapshot,
  phase57:result.phase57,
  provenance:result.provenance,
  methodology:{
    ...result.methodology,
    reusableSingleRssChartTargetSupported:true,
    targetSheetMayBeReusedAcrossSymbols:true,
    sourceBarTimestampRepresentsFiveMinuteIntervalStart:true,
    snapshotFreshnessUsesCompletedSourceBarClose:true,
    sourceBarDurationMinutes:SOURCE_BAR_MINUTES,
    excelWritePerformed:false,
  },
  safety:SAFETY,
};
fs.mkdirSync(path.dirname(outputPath),{recursive:true});
const tmp=`${outputPath}.tmp-${process.pid}`;
fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
fs.renameSync(tmp,outputPath);
const outputSha256=sha(fs.readFileSync(outputPath));
console.log(JSON.stringify({status:payload.status,output:outputPath,outputSha256,currentSymbol:payload.currentSymbol,targetMode,phase57Direction:payload.snapshot.direction,phase57Confidence:payload.snapshot.confidence,selectedHorizonBars:payload.phase57.selectedHorizonBars,selectedFeatureFamily:payload.phase57.selectedFeatureFamily,selectedModelType:payload.phase57.selectedModelType,selectedThreshold:payload.phase57.selectedThreshold,sourceBarTimestamp,sourceBarCloseAt,targetWithinFrozenHistoricalUniverse:payload.targetWithinFrozenHistoricalUniverse,outOfTrainingUniverseResearch:payload.outOfTrainingUniverseResearch,safety:SAFETY},null,2));
