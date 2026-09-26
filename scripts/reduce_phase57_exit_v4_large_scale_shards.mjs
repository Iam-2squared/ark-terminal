import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,PHASE57_EXIT_V4_LARGE_SCALE_SAFETY,summarizeExitV4LargeScale} from '../predict/daytrade/phase57-exit-v4-large-scale.js';

const arg=(name,fallback)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const inputDir=arg('--input-dir');const output=arg('--output','tmp/phase57-exit-v4-large-scale-evidence.json');
if(!inputDir)throw new Error('--input-dir is required');
const files=fs.readdirSync(inputDir,{recursive:true}).filter(x=>String(x).endsWith('.json')).map(x=>path.join(inputDir,String(x))).sort();
if(!files.length)throw new Error('no evaluation shards found');
const shards=files.map(file=>JSON.parse(fs.readFileSync(file,'utf8')));
if(shards.some(x=>x.status!=='V4_LARGE_SCALE_EVALUATION_SHARD_READY'))throw new Error('non-ready evaluation shard');
const records=shards.flatMap(x=>x.records??[]).sort((a,b)=>a.probeId.localeCompare(b.probeId)||a.variant.localeCompare(b.variant));
const ids=[...new Set(records.map(x=>x.probeId))];
for(const id of ids){const variants=records.filter(x=>x.probeId===id).map(x=>x.variant).sort();if(JSON.stringify(variants)!==JSON.stringify(['FIXED_24','V4']))throw new Error(`unpaired probe: ${id}`);}
const deltas=ids.map(id=>{const pair=records.filter(x=>x.probeId===id),v4=pair.find(x=>x.variant==='V4'),fixed=pair.find(x=>x.variant==='FIXED_24');return {probeId:id,symbol:v4.symbol,sessionDate:v4.sessionDate,market:v4.market,sector:v4.sector,netReturnDeltaPct:v4.netReturnPct-fixed.netReturnPct,barsHeldDelta:v4.barsHeld-fixed.barsHeld};});
const evidence={schemaVersion:1,phase:'57.exit-v4.large-scale.evidence',status:'V4_LARGE_SCALE_HISTORICAL_RECONSTRUCTION_READY',shardCount:shards.length,pairedCount:ids.length,records,pairedDeltas:deltas,summary:summarizeExitV4LargeScale(records),coverage:{symbols:new Set(records.map(x=>x.symbol)).size,sessions:new Set(records.map(x=>x.sessionDate)).size,symbolSessions:ids.length,blockedProbeCount:shards.reduce((s,x)=>s+Number(x.blockedProbeCount??0),0)},classification:{historicalReconstruction:true,stressDiagnostic:true,formalOos:false,prospective:false,promotionEligible:false,currentUniverseSurvivorshipBias:true},methodology:{...PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,deterministicReduce:true,bestResultOnlyReporting:false,resultBasedRetuning:false},safety:PHASE57_EXIT_V4_LARGE_SCALE_SAFETY};
evidence.evidenceSha256=crypto.createHash('sha256').update(JSON.stringify(evidence)).digest('hex');
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(evidence,null,2)}\n`);
console.log(JSON.stringify({status:evidence.status,output,pairedCount:evidence.pairedCount,coverage:evidence.coverage,summary:evidence.summary,evidenceSha256:evidence.evidenceSha256},null,2));
