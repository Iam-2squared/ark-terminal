// Mechanical frozen 5m projection for newly selected identities only. No new data.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {projectCandidates} from './phase57_msh_entry_v2_paths.mjs';
const [cache,ledgerFile,out]=process.argv.slice(2);
if(!cache||!ledgerFile||!out||fs.existsSync(out))throw Error('NEW_OUTPUT_REQUIRED');
const read=p=>JSON.parse(fs.readFileSync(p));
const gz=p=>JSON.parse(gunzipSync(fs.readFileSync(p)));
const sha=b=>createHash('sha256').update(b).digest('hex');
const ledger=gz(ledgerFile), prior=gz('docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz');
const parent=new Map(prior.events.map(e=>[e.selectorEventId,e]));
const newRows=ledger.new.filter(r=>!parent.has(r.selectorEventId));
const paths=ledger.new.filter(r=>parent.has(r.selectorEventId)).map(r=>{
 const p=parent.get(r.selectorEventId);if(p.decisionPrice!==r.decisionPrice)throw Error('REFERENCE_DRIFT');return p;
});
const sources=[];
const alloc=read('predict/long-only/phase57-long-only-session-allocation-v3.json');
for(const date of [...new Set(newRows.map(r=>r.sessionDate))].sort()){
 const saved=prior.sources.find(s=>s.sessionDate===date);
 if(!saved||!Object.entries(alloc.partitions).some(([k,v])=>k.startsWith('DEVELOPMENT_')&&v.includes(date)))throw Error('SEALED_SCOPE');
 const file=path.join(cache,'phase57-long-only/raw/jquants-v2',date,'minute-pages.json');
 if(sha(fs.readFileSync(file))!==saved.rawPagesSHA)throw Error('CACHE_IDENTITY');
 const pages=read(file);for(const p of pages)if(sha(p.responseText)!==p.responseSha256)throw Error('PAGE_HASH');
 const raw=pages.flatMap(p=>JSON.parse(p.responseText).data??[]);
 if(raw.some(r=>(r.Date??r.date)!==date))throw Error('DATE_SCOPE');
 const n=normalizeAndAggregateMinuteRows(raw);
 if(sha(JSON.stringify(n.bars))!==saved.normalizedSHA)throw Error('NORMALIZED_5M_IDENTITY');
 paths.push(...projectCandidates(n.bars,newRows.filter(r=>r.sessionDate===date).map(r=>({...r,symbolSessionId:date+'|'+r.symbol}))));
 sources.push(saved);
 console.log(JSON.stringify({sessionDate:date,newProjection:true,providerRequests:0}));
}
paths.sort((a,b)=>a.selectorEventId.localeCompare(b.selectorEventId));
if(paths.length!==ledger.new.length||new Set(paths.map(r=>r.selectorEventId)).size!==paths.length)throw Error('LEDGER_COUNT');
fs.writeFileSync(out,gzipSync(JSON.stringify({role:'EVALUATOR_ONLY',sources,newProjected:newRows.length,reused:paths.length-newRows.length,events:paths})+'\n'),{flag:'wx'});
