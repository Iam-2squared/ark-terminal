// Existing Development cache only. Projection is evaluator data, never runtime inputs.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {projectPath} from './phase57_long_exit_paired_paths.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const readGz=p=>JSON.parse(gunzipSync(fs.readFileSync(p)));
const CONTRACT='predict/research/phase57-msh-entry-long-v2-predevelopment-contract-v1.json';
export const CONTRACT_SHA='18818ffd1157c7ba15c93eb4723c3e28945c238e0e2f6a2440bee98c7ad1267f';
export function projectCandidates(bars,rows){
  const map=new Map();
  for(const b of bars){if(!map.has(b.symbol))map.set(b.symbol,[]);map.get(b.symbol).push(b);}
  return rows.map(r=>projectPath(map.get(r.symbol)??[],Object.fromEntries(
    ['selectorEventId','symbolSessionId','symbol','sessionDate','decisionTimestamp','decisionPrice'].map(k=>[k,r[k]]))));
}
export function main(cacheRoot,output){
  if(!cacheRoot||!output||fs.existsSync(output))throw Error('EXPLICIT_NEW_OUTPUT_REQUIRED');
  if(sha(fs.readFileSync(CONTRACT))!==CONTRACT_SHA)throw Error('CONTRACT_SHA_MISMATCH');
  const c=read(CONTRACT);
  for(const [p,h]of Object.entries(c.sourcePins))if(sha(fs.readFileSync(p))!==h)throw Error(`SOURCE_SHA_MISMATCH:${p}`);
  const rows=gunzipSync(fs.readFileSync('docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')).toString().trim().split('\n').map(JSON.parse);
  if(rows.length!==3800||new Set(rows.map(r=>r.selectorEventId)).size!==3800)throw Error('CANDIDATE_IDENTITY');
  const prior=readGz('docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement/path-diagnostics.json.gz');
  const legacy=readGz('docs/evidence/phase57-long-exit-v345-paired/paths.json.gz');
  const alloc=read('predict/long-only/phase57-long-only-session-allocation-v3.json');
  const l1=read('predict/long-only/phase57-long-only-l1-discovery-sessions.json');
  const l2=read('predict/long-only/phase57-long-only-l2-development-sessions.json');
  const v2=read('predict/long-only/phase57-long-only-v2-development-sessions.json');
  const groups=[{sessions:l1.sessions,manifest:'l1-minute-manifest.json',hash:l1.sessionListSha256},
    {sessions:v2.sessions,manifest:'v2-minute-manifest.json',hash:v2.sessionListSha256},
    {sessions:[...alloc.partitions.DEVELOPMENT_C,...alloc.partitions.DEVELOPMENT_D],manifest:'l2-minute-manifest.json',hash:l2.sessionListSha256}];
  const events=[],sources=[];
  for(const date of c.universe.sessions){
    const group=groups.filter(g=>g.sessions.includes(date));
    const parts=Object.entries(alloc.partitions).filter(([,dates])=>dates.includes(date));
    if(group.length!==1||parts.length!==1||!parts[0][0].startsWith('DEVELOPMENT_'))throw Error('SEALED_OR_AMBIGUOUS_SCOPE');
    const dir=path.join(cacheRoot,'phase57-long-only/raw/jquants-v2',date);
    const m=read(path.join(dir,group[0].manifest)),file=path.join(dir,'minute-pages.json'),pages=read(file);
    if(m.sessionDate!==date||m.partition!==parts[0][0]||m.sessionListSha256!==group[0].hash||m.pageCount!==pages.length)throw Error('SOURCE_MANIFEST_MISMATCH');
    for(const p of pages)if(sha(p.responseText)!==p.responseSha256)throw Error('PAGE_HASH_MISMATCH');
    const saved=prior.sources.find(s=>s.sessionDate===date);
    if(!saved||sha(fs.readFileSync(file))!==saved.rawPagesSHA)throw Error('RAW_CHECKPOINT_CHANGED');
    const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);
    if(raw.length!==m.rowCount||raw.some(r=>(r.Date??r.date)!==date))throw Error('UNAUTHORIZED_SESSION');
    const n=normalizeAndAggregateMinuteRows(raw),normalizedSHA=sha(JSON.stringify(n.bars));
    if(normalizedSHA!==saved.normalizedSHA)throw Error('NORMALIZED_SOURCE_CHANGED');
    events.push(...projectCandidates(n.bars,rows.filter(r=>r.sessionDate===date)));
    sources.push({sessionDate:date,partition:m.partition,rawPagesSHA:saved.rawPagesSHA,normalizedSHA});
    console.log(JSON.stringify({sessionDate:date,source:'PINNED_DEVELOPMENT_CACHE',providerRequests:0}));
  }
  const byId=new Map(events.map(e=>[e.selectorEventId,e]));
  if(byId.size!==3800||events.length!==3800)throw Error('PROJECTION_COUNT');
  for(const e of legacy.events){
    const p=byId.get(e.selectorEventId);
    if(!p||JSON.stringify(p.future)!==JSON.stringify(e.future)||p.expectedBars!==e.expectedBars||p.decisionPrice!==e.decisionPrice)throw Error('LEGACY277_PATH_PARITY');
  }
  const result={contractSHA:CONTRACT_SHA,role:'EVALUATOR_ONLY_ALL3800_NO_LABEL_AVAILABILITY_FILTER',
    exposure:'HISTORICAL_DEVELOPMENT_IN_SAMPLE_OUTCOME_EXPOSED',sourceCheckpointRuns:prior.sourceCheckpointRuns,
    sources,events,legacy277Parity:true,providerRequests:0,freshAccess:0,oosAccess:0,safety:c.safety};
  const bytes=Buffer.from(JSON.stringify(result)+'\n'),compressed=gzipSync(bytes);
  fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,compressed,{flag:'wx'});
  fs.writeFileSync(`${output}.sha256`,sha(compressed)+'\n',{flag:'wx'});
  console.log(JSON.stringify({status:'ALL3800_PATHS_PROJECTED',events:events.length,legacy277Parity:true,sha256:sha(compressed)}));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main(process.argv[2],process.argv[3]);
