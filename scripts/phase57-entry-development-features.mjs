import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {reconstructDevelopmentSession} from './phase57-entry-development-source.mjs';
import {ALLOCATION,FIT,verifyDevelopmentContracts} from './lib/phase57-entry-development-fit.mjs';
import {CONTRACT,MinimalStatefulEntry,selectionSchedule} from './lib/phase57-minimal-stateful-entry.mjs';
import {runPhase57MinimalHybrid} from '../predict/daytrade/phase57-selector-minimal-hybrid.js';

const hash=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const out=process.env.OUTPUT_DIR??'artifacts/development-features';
const shard=Number(process.env.SHARD_INDEX),count=6;
assert(Number.isInteger(shard)&&shard>=0&&shard<count,'INVALID_SHARD');
const pins=verifyDevelopmentContracts();
const admissionBytes=fs.readFileSync(process.env.ADMISSION_V21_PATH??'artifacts/input/admission-v21/admission.json');
assert.equal(hash(admissionBytes),'18edbdb30325797cde7bdd1316c6086077fc8907a09d9e1755575f2722c04379');
const admission=new Map(JSON.parse(admissionBytes).auditBySession.map(r=>[r.sessionDate,r]));
const model=read('predict/research/phase57-selector-minimal-hybrid-development-model.json');
const freeze=read('predict/research/phase57-selector-minimal-hybrid-development-freeze.json');
const {modelDigest,...modelCore}=model,{freezeSha256,...freezeCore}=freeze;
assert.equal(modelDigest,CONTRACT.selectorModelDigest);
assert.equal(hash(JSON.stringify(modelCore)),modelDigest);
assert.equal(freeze.modelDigest,modelDigest);
assert.equal(freezeSha256,CONTRACT.selectorFreezeSHA);
assert.equal(hash(JSON.stringify(freezeCore)),freezeSha256);
fs.mkdirSync(out,{recursive:true});
const write=(name,obj)=>{const b=Buffer.from(JSON.stringify(obj)+'\n');fs.writeFileSync(`${out}/${name}`,gzipSync(b),{flag:'wx'});return hash(b);};
const ledger=(sessionDate,stage)=>fs.appendFileSync(`${out}/access-${shard}.ndjson`,JSON.stringify({sessionDate,stage,at:new Date().toISOString(),purpose:'DEVELOPMENT_ONLY',...pins,safety:CONTRACT.safety})+'\n');
const regular=b=>{const time=new Date(Date.parse(b.timestamp)+32400000).toISOString().slice(11,16);return (time>='09:00'&&time<'11:30')||(time>='12:30'&&time<'15:30');};
let cacheInstalled=false;
for(const [i,session] of ALLOCATION.sessions.entries()){
 if(i%count!==shard)continue;
 const date=session.sessionDate;ledger(date,'MARKET_DATA_RECONSTRUCTION');
 const source=await reconstructDevelopmentSession(date),expected=admission.get(date);assert(expected,'MISSING_ADMISSION');
 for(const key of ['minuteSha256','fiveMinuteSha256','memberSetSha256','normalizedMinuteRows','fiveMinuteBars','eligibleJpxSymbolCount'])assert.equal(source[key],expected[key],`SOURCE_MISMATCH_${key}`);
 const member=new Set(source.members),meta=new Map(source.master.map(m=>[m.symbol,m]));
 const grouped=new Map();
 for(const b of source.bars){if(!member.has(b.symbol)||!regular(b))continue;assert.equal(b.sessionDate,date);assert.equal(Date.parse(b.availableAt),Date.parse(b.timestamp)+300000);if(!grouped.has(b.symbol))grouped.set(b.symbol,[]);grouped.get(b.symbol).push(b);}
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
  const snapshot={decisionTimestamp:t,complete:true,selected:result.selected.map(c=>({symbol:c.symbol,rank:c.hybridRank,score:c.hybridScore,priceReference:c.currentPrice})),selectorModelDigest:CONTRACT.selectorModelDigest,selectorFreezeSHA:CONTRACT.selectorFreezeSHA,sourceClass:'HISTORICAL_RECONSTRUCTION_LATER_FETCHED',selectionLineage:{source:source.fiveMinuteSha256,cutoff:t}};
  const step=engine.step(snapshot,prefixes);
  for(const event of step.events)events.push({...event,priceReference:snapshot.selected.find(c=>c.symbol===event.symbol).priceReference});
  points.push({decisionTimestamp:t,complete:true,selectedCount:result.selected.length,selectionSha256:hash(JSON.stringify(result.selected))});
 }
 engine.close(`${date}T15:30:00+09:00`);
 assert(new Set(events.map(e=>e.eventId)).size===events.length,'DUPLICATE_EVENTS');
 const ready=events.filter(e=>e.directionFeatures).length;
 // Fail before labels on an entirely unusable session; never substitute features.
 assert(ready>0,'NO_FEATURE_READY_EVENTS_STOP_BEFORE_LABELS');
 const usedSymbols=new Set(events.map(e=>e.symbol));
 const featureSha=write(`${date}.features.json.gz`,{sessionDate:date,...pins,events,points});
 const barsSha=write(`${date}.bars.json.gz`,entries.filter(e=>usedSymbols.has(e.symbol)));
 const evidence={sessionDate:date,...pins,featureSha256:featureSha,barsSha256:barsSha,events:events.length,featureReady:ready,sourceHashes:Object.fromEntries(['minuteSha256','fiveMinuteSha256','memberSetSha256'].map(k=>[k,source[k]])),featureFrozenAt:new Date().toISOString(),labelsGenerated:false,sourceParity:true,safety:CONTRACT.safety};
 fs.writeFileSync(`${out}/${date}.manifest.json`,JSON.stringify(evidence,null,2)+'\n',{flag:'wx'});ledger(date,'FEATURES_FROZEN_NO_LABELS');
 console.log(JSON.stringify({sessionDate:date,events:events.length,featureReady:ready,featureSha256:featureSha,labelsGenerated:false}));
}
