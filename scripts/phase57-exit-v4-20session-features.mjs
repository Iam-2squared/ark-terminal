import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

const CONFIG_PATH=process.env.DIAGNOSTIC_CONFIG??'predict/research/phase57-exit-v4-20session-diagnostic-v1.json';
process.env.ENTRY_SOURCE_ALLOCATION_PATH=CONFIG_PATH;
const [{reconstructDevelopmentSession},{developmentUniverse},{CONTRACT,MinimalStatefulEntry,selectionSchedule}]=await Promise.all([
  import('./phase57-entry-development-source.mjs'),
  import('./lib/phase57-entry-development-universe.mjs'),
  import('./lib/phase57-minimal-stateful-entry.mjs'),
]);
const hash=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const cfg=read(CONFIG_PATH);
assert(['PHASE57_EXIT_V4_20SESSION_DIAGNOSTIC_V1','PHASE57_EXIT_BLOCK_A_UNSEEN_VALIDATION_V1'].includes(cfg.schemaId),'UNSUPPORTED_RESEARCH_CONFIG');
assert.equal(cfg.sessions.length,Number(cfg.expectedSessionCount??20));
const sessionFilter=String(process.env.SESSION_FILTER??'').trim();
if(sessionFilter)assert(cfg.sessions.some(x=>x.sessionDate===sessionFilter),'SESSION_FILTER_NOT_FROZEN');
const shard=Number(process.env.SHARD_INDEX??0),shardCount=Number(process.env.SHARD_COUNT??4);
assert(Number.isInteger(shard)&&shard>=0&&shard<shardCount);
const out=process.env.OUTPUT_DIR??'artifacts/phase57-exit-v4-20session-features';
fs.mkdirSync(out,{recursive:true});
const selectorRoot=path.resolve('frozen-selector');
const {runPhase57MinimalHybrid}=await import(pathToFileURL(path.join(selectorRoot,'predict/daytrade/phase57-selector-minimal-hybrid.js')).href);
const model=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-model.json'));
assert.equal(model.modelDigest,cfg.lockedUpstream.selectorModelDigest);
const freeze=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-freeze.json'));
assert.equal(freeze.freezeSha256,cfg.lockedUpstream.selectorFreezeSha256);
const regular=b=>{const hm=new Date(Date.parse(b.timestamp)+32400000).toISOString().slice(11,16);return (hm>='09:00'&&hm<'11:30')||(hm>='12:30'&&hm<'15:30');};
const writeGz=(name,obj)=>{const bytes=Buffer.from(JSON.stringify(obj)+'\n');fs.writeFileSync(path.join(out,name),gzipSync(bytes),{flag:'wx'});return hash(bytes);};
for(const [i,row] of cfg.sessions.entries()){
  if(sessionFilter&&row.sessionDate!==sessionFilter)continue;
  if(i%shardCount!==shard)continue;
  const date=row.sessionDate;
  const source=await reconstructDevelopmentSession(date);
  const universe=developmentUniverse(source),meta=universe.meta;
  const grouped=new Map();
  for(const b of universe.bars){if(!regular(b))continue;if(!grouped.has(b.symbol))grouped.set(b.symbol,[]);grouped.get(b.symbol).push(b);}
  const entries=[...grouped].map(([symbol,bars])=>({symbol,sector:meta.get(symbol)?.sector??'UNKNOWN',market:meta.get(symbol)?.marketCode??'UNKNOWN',bars:bars.sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp))}));
  const engine=new MinimalStatefulEntry(date),events=[],points=[];
  for(const t of selectionSchedule(date)){
    const completed=entries.map(e=>({...e,bars:e.bars.filter(b=>Date.parse(b.availableAt)<=Date.parse(t)&&Date.parse(b.timestamp)+300000<=Date.parse(t))}));
    const result=runPhase57MinimalHybrid({featureCutoff:t,entries:completed,model});
    const prefixes=Object.fromEntries(completed.map(e=>[e.symbol,e.bars]));
    const snapshot={decisionTimestamp:t,complete:true,selected:result.selected.map(c=>({symbol:c.symbol,rank:c.hybridRank,score:c.hybridScore,priceReference:c.currentPrice})),selectorModelDigest:CONTRACT.selectorModelDigest,selectorFreezeSHA:CONTRACT.selectorFreezeSHA,sourceClass:'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',selectionLineage:{source:source.fiveMinuteSha256,cutoff:t}};
    const step=engine.step(snapshot,prefixes);
    for(const event of step.events){
      const selected=snapshot.selected.find(c=>c.symbol===event.symbol);
      events.push({...event,priceReference:selected?.priceReference??null,hybridRank:selected?.rank??null,hybridScore:selected?.score??null});
    }
    points.push({decisionTimestamp:t,selectedCount:result.selected.length});
  }
  engine.close(`${date}T15:30:00+09:00`);
  assert.equal(new Set(events.map(e=>e.eventId)).size,events.length,'DUPLICATE_EVENT');
  const ready=events.filter(e=>e.directionFeatures).length;
  assert(ready>0,'NO_FEATURE_READY_EVENTS');
  const used=new Set(events.map(e=>e.symbol));
  const featureSha256=writeGz(`${date}.features.json.gz`,{sessionDate:date,events,points});
  const barsSha256=writeGz(`${date}.bars.json.gz`,entries.filter(e=>used.has(e.symbol)));
  fs.writeFileSync(path.join(out,`${date}.manifest.json`),JSON.stringify({sessionDate:date,role:cfg.role,events:events.length,featureReady:ready,source:{minuteSha256:source.minuteSha256,fiveMinuteSha256:source.fiveMinuteSha256,memberSetSha256:source.memberSetSha256},featureSha256,barsSha256,labelsGenerated:false,outcomeMeasured:false,safety:cfg.safety},null,2)+'\n');
  console.log(JSON.stringify({sessionDate:date,events:events.length,featureReady:ready,selectedPoints:points.reduce((s,x)=>s+x.selectedCount,0),labelsGenerated:false}));
}
