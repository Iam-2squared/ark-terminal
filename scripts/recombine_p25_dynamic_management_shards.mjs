import fs from 'node:fs';
import path from 'node:path';
import {summarizeP253ALPairs,summarizeP253ALByVariant,PHASE57_P25_3AL_SAFETY} from '../predict/daytrade/phase57-p25-3al-dynamic-management-multisession.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function writeAtomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n','utf8');fs.renameSync(tmp,file);}
const shardDir=arg('--shard-dir');
const outputPath=arg('--output','data/p25-dynamic-management/evaluation.json');
const scorecardPath=arg('--scorecard','data/p25-dynamic-management/scorecard.json');
if(!shardDir){console.error('usage: node scripts/recombine_p25_dynamic_management_shards.mjs --shard-dir <dir> [--output <json>] [--scorecard <json>]');process.exit(2);}

try{
  const files=fs.readdirSync(shardDir).filter(name=>name.endsWith('.json')).sort();
  const evaluations=[];
  for(const name of files){
    const parsed=JSON.parse(fs.readFileSync(path.join(shardDir,name),'utf8'));
    if(parsed?.evaluation?.status==='P25_3AL_DYNAMIC_MANAGEMENT_MULTISESSION_EVALUATED')evaluations.push(parsed);
  }
  if(!evaluations.length)throw new Error('no dynamic shard evaluations found');
  const heads=new Set(evaluations.map(x=>x?.inputs?.lineageManifestHeadSha256));
  if(heads.size!==1||heads.has(undefined)||heads.has(null))throw new Error('dynamic shard lineage head mismatch');
  const expectedCounts=new Set(evaluations.map(x=>Number(x?.evaluation?.expectedSessionCount)));
  if(expectedCounts.size!==1)throw new Error('dynamic shard expected-session mismatch');
  const sessions=evaluations.flatMap(x=>x.evaluation.sessions??[]).sort((a,b)=>String(a.sessionDate).localeCompare(String(b.sessionDate)));
  const pairs=evaluations.flatMap(x=>x.evaluation.pairs??[]).sort((a,b)=>String(a.key).localeCompare(String(b.key)));
  const sessionDates=sessions.map(x=>String(x.sessionDate));
  if(new Set(sessionDates).size!==sessionDates.length)throw new Error('duplicate session shard detected');
  const expectedSessionCount=[...expectedCounts][0];
  if(sessionDates.length!==expectedSessionCount)throw new Error(`incomplete dynamic shard union: ${sessionDates.length}/${expectedSessionCount}`);
  const pairKeys=pairs.map(x=>String(x.key));
  if(new Set(pairKeys).size!==pairKeys.length)throw new Error('duplicate dynamic pair detected during recombine');
  const lineageManifestHeadSha256=[...heads][0];
  const createdAt=new Date().toISOString();
  const summary=summarizeP253ALPairs(pairs);
  const byVariant=summarizeP253ALByVariant(pairs);
  const evaluation={
    schemaVersion:1,
    phase:'57.p25.3am.dynamic-management-sharded-recombine',
    status:'P25_3AM_DYNAMIC_MANAGEMENT_FULL_UNION_RECOMBINED',
    createdAt,
    inputs:{lineageManifestHeadSha256,shardCount:evaluations.length,expectedSessionCount},
    evaluation:{
      phase:'57.p25.3al.dynamic-management-multisession',
      status:'P25_3AL_DYNAMIC_MANAGEMENT_MULTISESSION_EVALUATED',
      lineageManifestHeadSha256,
      expectedSessionCount,
      readySessionCount:sessions.length,
      sessions,
      pairs,
      summary,
      byVariant,
      methodology:{sameFrozenEvidenceChainAsP253D:true,sameFrozenUniverseAndEntryAsFixedBaseline:true,fixedBaselineUntouched:true,deterministicShardUnion:true,postOutcomeRuleSelection:false,entryRetuning:false,modelRetuning:false,universeRetuning:false,thresholdRetuning:false,dynamicNSelectionFromResults:false,freshHoldoutConsumed:false,performanceConclusionAllowed:false},
      safety:PHASE57_P25_3AL_SAFETY,
    },
    methodology:{appendOnlyTarget:true,idempotentByEvidenceDateAndLineage:true,deterministicShardUnion:true,fixedBaselineUntouched:true,resultBasedRetuning:false,winnerSelection:false,freshHoldoutConsumed:false},
    safety:PHASE57_P25_3AL_SAFETY,
  };
  const scorecard={
    schemaVersion:1,
    phase:'57.p25.3am.dynamic-management-sharded-scorecard',
    status:'P25_3AM_DYNAMIC_MANAGEMENT_SCORECARD_READY',
    createdAt,
    lineageManifestHeadSha256,
    expectedSessionCount,
    readySessionCount:sessions.length,
    sessions,
    summary,
    byVariant,
    methodology:{descriptiveOnly:true,fixedVsDynamicPaired:true,deterministicShardUnion:true,winnerSelection:false,resultBasedRetuning:false,freshHoldoutConsumed:false},
    safety:PHASE57_P25_3AL_SAFETY,
  };
  writeAtomic(outputPath,evaluation);
  writeAtomic(scorecardPath,scorecard);
  console.log(JSON.stringify({status:evaluation.status,shardCount:evaluations.length,readySessionCount:sessions.length,pairedCount:summary.pairedCount,lineageManifestHeadSha256,output:outputPath,scorecard:scorecardPath},null,2));
}catch(error){console.error(JSON.stringify({status:'BLOCKED_P25_3AM_DYNAMIC_MANAGEMENT_RECOMBINE',error:String(error?.message??error),safety:PHASE57_P25_3AL_SAFETY},null,2));process.exit(1);}
