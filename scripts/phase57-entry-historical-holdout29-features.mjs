import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {reconstructDevelopmentSession} from './phase57-entry-development-source.mjs';
import {developmentUniverse} from './lib/phase57-entry-development-universe.mjs';
import {verifyDevelopmentContracts} from './lib/phase57-entry-development-fit.mjs';
import {CONTRACT,MinimalStatefulEntry,selectionSchedule} from './lib/phase57-minimal-stateful-entry.mjs';

const hash=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const out=process.env.OUTPUT_DIR??'artifacts/holdout29-features';
const shard=Number(process.env.SHARD_INDEX),count=3;
assert(Number.isInteger(shard)&&shard>=0&&shard<count,'INVALID_SHARD');
const pins=verifyDevelopmentContracts();
const precommit=read('predict/research/phase57-entry-historical-holdout29-source-parity-precommit.json');
assert.equal(precommit.status,'HISTORICAL_HOLDOUT_SOURCE_PARITY_PRECOMMITTED_NO_OUTCOME_ACCESS');
assert.equal(precommit.holdoutRole,'HISTORICAL_HOLDOUT_DIAGNOSTIC_NOT_PROSPECTIVE_NOT_FORMAL_OOS');
assert.equal(precommit.candidatePolicy,'FROZEN_MINIMAL_STATEFUL_ENTRY_NO_RETRAIN_NO_RETUNE');
assert.equal(precommit.count,29);assert.equal(precommit.sessions.length,29);
assert.equal(precommit.sharding.shardCount,count);

const admissionBytes=fs.readFileSync(process.env.ADMISSION_V2_PATH??'artifacts/input/admission-v2/admission.json');
assert.equal(hash(admissionBytes),'9650e9a7f3b0d9ae5d8339879b4571de58681d337785ca4f7715262580b72b08');
const admission=new Map(JSON.parse(admissionBytes).auditBySession.map(r=>[r.sessionDate,r]));
const selectorRoot=path.resolve('frozen-selector');
for(const [name,expected] of Object.entries({'phase57-selector-minimal-hybrid.js':'336ac8ccda8d1fd6636e65475b58c749dec72fa5','phase57-selector-minimal-hybrid-model.js':'1a44ab4886c8ff4a80e61af983594e39bbd67bf6','phase57-p25-intraday-dynamic-universe.js':'9612eb764f9cbc5d9de247c4f05c734bae0f9d85'})){
 const b=fs.readFileSync(path.join(selectorRoot,'predict/daytrade',name));
 assert.equal(createHash('sha1').update(`blob ${b.length}\0`).update(b).digest('hex'),expected);
}
const {runPhase57MinimalHybrid}=await import(pathToFileURL(path.join(selectorRoot,'predict/daytrade/phase57-selector-minimal-hybrid.js')).href);
const model=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-model.json'));
const freeze=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-freeze.json'));
const {modelDigest,...modelCore}=model,{freezeSha256,...freezeCore}=freeze;
assert.equal(modelDigest,CONTRACT.selectorModelDigest);assert.equal(hash(JSON.stringify(modelCore)),modelDigest);
assert.equal(freeze.modelDigest,modelDigest);assert.equal(freezeSha256,CONTRACT.selectorFreezeSHA);assert.equal(hash(JSON.stringify(freezeCore)),freezeSha256);
fs.mkdirSync(out,{recursive:true});
const write=(name,obj)=>{const b=Buffer.from(JSON.stringify(obj)+'\n');fs.writeFileSync(`${out}/${name}`,gzipSync(b),{flag:'wx'});return hash(b);};
const ledger=(sessionDate,stage)=>fs.appendFileSync(`${out}/access-${shard}.ndjson`,JSON.stringify({sessionDate,stage,at:new Date().toISOString(),purpose:'HISTORICAL_HOLDOUT29_DIAGNOSTIC',candidateChanged:false,retraining:false,...pins,safety:CONTRACT.safety})+'\n');
const regular=b=>{const time=new Date(Date.parse(b.timestamp)+32400000).toISOString().slice(11,16);return (time>='09:00'&&time<'11:30')||(time>='12:30'&&time<'15:30');};
let cacheInstalled=false;
for(const [i,date] of precommit.sessions.entries()){
 if(i%count!==shard)continue;
 ledger(date,'MARKET_DATA_RECONSTRUCTION');
 const source=await reconstructDevelopmentSession(date),expected=admission.get(date);assert(expected,'MISSING_ADMISSION');
 for(const key of ['minuteSha256','fiveMinuteSha256','memberSetSha256','normalizedMinuteRows','fiveMinuteBars','eligibleJpxSymbolCount'])assert.equal(source[key],expected[key],`SOURCE_MISMATCH_${key}`);
 const universe=developmentUniverse(source),meta=universe.meta;
 const grouped=new Map();
 for(const b of universe.bars){if(!regular(b))continue;assert.equal(b.sessionDate,date);assert.equal(Date.parse(b.availableAt),Date.parse(b.timestamp)+300000);if(!grouped.has(b.symbol))grouped.set(b.symbol,[]);grouped.get(b.symbol).push(b);}
 const entries=[...grouped].map(([symbol,bars])=>({symbol,sector:meta.get(symbol).sector,market:meta.get(symbol).marketCode,bars:bars.sort((a,b)=>Date.parse(a.timestamp)-Date.parse(b.timestamp))}));
 const engine=new MinimalStatefulEntry(date),events=[],points=[];
 for(const t of selectionSchedule(date)){
  const completed=entries.map(e=>({...e,bars:e.bars.filter(b=>Date.parse(b.availableAt)<=Date.parse(t)&&Date.parse(b.timestamp)+300000<=Date.parse(t))}));
  let result=runPhase57MinimalHybrid({featureCutoff:t,entries:completed,model});
  if(!cacheInstalled){
   const Native=Intl.DateTimeFormat,cache=new Map();const get=args=>{const k=JSON.stringify(args);if(!cache.has(k))cache.set(k,new Native(...args));return cache.get(k);};
   Intl.DateTimeFormat=new Proxy(Native,{construct:(_t,args)=>get(args),apply:(_t,_this,args)=>get(args)});
   const cached=runPhase57MinimalHybrid({featureCutoff:t,entries:completed,model});assert.deepEqual(cached,result);cacheInstalled=true;
  }
  const prefixes=Object.fromEntries(completed.map(e=>[e.symbol,e.bars]));
  const snapshot={decisionTimestamp:t,complete:true,selected:result.selected.map(c=>({symbol:c.symbol,rank:c.hybridRank,score:c.hybridScore,priceReference:c.currentPrice})),selectorModelDigest:CONTRACT.selectorModelDigest,selectorFreezeSHA:CONTRACT.selectorFreezeSHA,sourceClass:'HISTORICAL_HOLDOUT_RECONSTRUCTION_LATER_FETCHED',selectionLineage:{source:source.fiveMinuteSha256,cutoff:t}};
  const step=engine.step(snapshot,prefixes);
  for(const event of step.events)events.push({...event,priceReference:snapshot.selected.find(c=>c.symbol===event.symbol).priceReference});
  points.push({decisionTimestamp:t,complete:true,selectedCount:result.selected.length,selectionSha256:hash(JSON.stringify(result.selected))});
 }
 engine.close(`${date}T15:30:00+09:00`);
 assert(new Set(events.map(e=>e.eventId)).size===events.length,'DUPLICATE_EVENTS');
 const ready=events.filter(e=>e.directionFeatures).length;assert(ready>0,'NO_FEATURE_READY_EVENTS_STOP_BEFORE_LABELS');
 const usedSymbols=new Set(events.map(e=>e.symbol));
 const featureSha=write(`${date}.features.json.gz`,{sessionDate:date,...pins,events,points});
 const barsSha=write(`${date}.bars.json.gz`,entries.filter(e=>usedSymbols.has(e.symbol)));
 const evidence={sessionDate:date,...pins,holdoutRole:precommit.holdoutRole,candidateChanged:false,retraining:false,featureSha256:featureSha,barsSha256:barsSha,events:events.length,featureReady:ready,sourceHashes:Object.fromEntries(['minuteSha256','fiveMinuteSha256','memberSetSha256'].map(k=>[k,source[k]])),featureFrozenAt:new Date().toISOString(),labelsGenerated:false,sourceParity:true,freshValidationOpened:0,freshOosOpened:0,reserve180To282Opened:0,safety:CONTRACT.safety};
 fs.writeFileSync(`${out}/${date}.manifest.json`,JSON.stringify(evidence,null,2)+'\n',{flag:'wx'});ledger(date,'FEATURES_FROZEN_NO_LABELS');
 console.log(JSON.stringify({sessionDate:date,events:events.length,featureReady:ready,featureSha256:featureSha,labelsGenerated:false}));
}
