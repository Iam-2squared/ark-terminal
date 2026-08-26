import fs from 'node:fs';
import path from 'node:path';
import {summarizeP25DataDrivenPairs,P25_DATA_DRIVEN_PAIRED_SAFETY} from '../predict/daytrade/phase57-p25-data-driven-exit-multisession.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function readJson(file){return JSON.parse(fs.readFileSync(file,'utf8'));}
function writeAtomic(file,value){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=`${file}.tmp-${process.pid}`;fs.writeFileSync(tmp,JSON.stringify(value,null,2)+'\n');fs.renameSync(tmp,file);}
const inputDir=arg('--input-dir'),output=arg('--output','data/p25-data-driven-exit/paired.json');
if(!inputDir){console.error('usage: node scripts/reduce_p25_data_driven_exit_shards.mjs --input-dir <dir> [--output <json>]');process.exit(2);}
const files=fs.readdirSync(inputDir).filter(x=>x.endsWith('.json')).sort();
if(!files.length)throw new Error('no shard JSON files');
const shards=files.map(f=>readJson(path.join(inputDir,f)));
const lineage=new Set(shards.map(x=>x.result?.lineageManifestHeadSha256));
const analogCounts=new Set(shards.map(x=>x.result?.analogPoolCount));
if(lineage.size!==1||[...lineage][0]==null)throw new Error('lineage mismatch across shards');
if(analogCounts.size!==1||![...analogCounts][0])throw new Error('analog pool mismatch across shards');
const pairs=shards.flatMap(x=>x.result?.pairs??[]).sort((a,b)=>String(a.key).localeCompare(String(b.key)));
const keys=pairs.map(x=>x.key); if(new Set(keys).size!==keys.length)throw new Error('duplicate pair key across shards');
const sessions=shards.flatMap(x=>x.result?.sessions??[]).sort((a,b)=>String(a.sessionDate).localeCompare(String(b.sessionDate)));
if(new Set(sessions.map(x=>x.sessionDate)).size!==sessions.length)throw new Error('duplicate session shard');
for(const x of shards){
  if(x.methodology?.exactDynamic50Only!==true||x.methodology?.resultBasedRetuning!==false)throw new Error('shard methodology guard violation');
  for(const [k,v] of Object.entries(P25_DATA_DRIVEN_PAIRED_SAFETY)) if(typeof v==='boolean'&&x.safety?.[k]!==v)throw new Error(`shard safety mismatch: ${k}`);
}
const result={phase:'57.p25.data-driven-exit.paired.v1',status:'P25_DATA_DRIVEN_EXIT_PAIRED_EVALUATED',lineageManifestHeadSha256:[...lineage][0],analogPoolCount:[...analogCounts][0],readySessionCount:sessions.length,sessions,pairs,summary:summarizeP25DataDrivenPairs(pairs),methodology:{exactDynamic50Only:true,sameFrozenEntryAsFixed:true,fixedBaselineUntouched:true,pre20260812HistoricalAnalogOnlyByUpstreamPin:true,currentProspectiveOutcomeUsedForFitting:false,resultBasedRetuning:false,fixedHorizonUsedAsDecisionInput:false,freshHoldoutConsumed:false,shardedComputeOnly:true,deterministicReduce:true},safety:P25_DATA_DRIVEN_PAIRED_SAFETY};
const payload={schemaVersion:1,phase:result.phase,status:result.status,createdAt:new Date().toISOString(),result,methodology:{exactDynamic50Only:true,fixedBaselineUntouched:true,resultBasedRetuning:false,freshHoldoutConsumed:false,shardedComputeOnly:true,deterministicReduce:true},safety:P25_DATA_DRIVEN_PAIRED_SAFETY};
writeAtomic(output,payload);
console.log(JSON.stringify({status:payload.status,shards:shards.length,pairedCount:result.summary.pairedCount,fixed:result.summary.fixed,dataDriven:result.summary.dataDriven,delta:result.summary.delta},null,2));
