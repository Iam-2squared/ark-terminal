import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {ALLOCATION,FIT,verifyDevelopmentContracts,verifyFrozenRow,foldSessions} from './lib/phase57-entry-development-fit.mjs';
import {CONTRACT} from './lib/phase57-minimal-stateful-entry.mjs';
import {labels,fitRows,stateful,metrics} from './lib/phase57-entry-development-measure.mjs';
const input=process.env.INPUT_DIR??'artifacts/development-input',out=process.env.OUTPUT_DIR??'artifacts/development-measurement';
const hash=b=>createHash('sha256').update(b).digest('hex'),read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const pins=verifyDevelopmentContracts();fs.mkdirSync(out,{recursive:true});
const write=(name,value)=>{const b=JSON.stringify(value,null,2)+'\n';fs.writeFileSync(`${out}/${name}`,b,{flag:'wx'});fs.writeFileSync(`${out}/${name}.sha256`,`${hash(b)}  ${name}\n`,{flag:'wx'});return hash(b);};
const manifests=fs.readdirSync(input).filter(f=>/^\d{4}-\d{2}-\d{2}\.manifest\.json$/.test(f));assert.equal(manifests.length,58);
const bundles=[];
// Global barrier: verify all58 feature bundles BEFORE loading future bars or labels.
for(const s of ALLOCATION.sessions){
 const m=read(`${input}/${s.sessionDate}.manifest.json`);assert.equal(m.sessionDate,s.sessionDate);assert(m.sourceParity);assert.equal(m.labelsGenerated,false);
 for(const [k,v] of Object.entries(pins))assert.equal(m[k],v);
 const bytes=gunzipSync(fs.readFileSync(`${input}/${s.sessionDate}.features.json.gz`));assert.equal(hash(bytes),m.featureSha256);
 const bundle=JSON.parse(bytes);assert.equal(bundle.sessionDate,s.sessionDate);assert.equal(bundle.points.length,66);
 for(const e of bundle.events){assert.equal(e.sessionDate,s.sessionDate);for(const r of e.directionFeatures??[])verifyFrozenRow(r);}
 assert(bundle.events.some(e=>e.directionFeatures),'NO_FEATURE_READY_SESSION');bundles.push({m,bundle});
}
write('feature-barrier.json',{...pins,status:'ALL58_FEATURES_FROZEN_BEFORE_LABELS',at:new Date().toISOString(),sessions:bundles.map(x=>({sessionDate:x.m.sessionDate,featureSha256:x.m.featureSha256}))});
const events=[];
for(const {m,bundle} of bundles){
 fs.appendFileSync(`${out}/development-access.ndjson`,JSON.stringify({sessionDate:m.sessionDate,stage:'ENTRY_DEVELOPMENT_USED_FUTURE_LABELS',at:new Date().toISOString(),...pins,safety:CONTRACT.safety})+'\n');
 const bytes=gunzipSync(fs.readFileSync(`${input}/${m.sessionDate}.bars.json.gz`));assert.equal(hash(bytes),m.barsSha256);
 const source=new Map(JSON.parse(bytes).map(e=>[e.symbol,e.bars]));
 for(const e of bundle.events)events.push({...e,labels:labels(e,source.get(e.symbol)??[])});
}
assert.equal(new Set(events.map(e=>e.eventId)).size,events.length,'DUPLICATE_EVENT');
// Fixed descriptive groupings, independent of outcomes; never used for threshold selection.
const groupedCounts=key=>Object.fromEntries([...new Set(events.map(key))].sort().map(k=>[k,events.filter(e=>key(e)===k).length]));
write('event-distribution.json',{hourJst:groupedCounts(e=>new Date(Date.parse(e.decisionTimestamp)+32400000).toISOString().slice(11,13)),exactHybridRank:groupedCounts(e=>String(e.hybridRank)),selectionIndex:groupedCounts(e=>String(e.selectionIndex))});
const datasetBytes=Buffer.from(events.map(e=>JSON.stringify(e)).join('\n')+'\n');fs.writeFileSync(`${out}/training-events.ndjson.gz`,gzipSync(datasetBytes),{flag:'wx'});
const blocked={};for(const e of events)if(!e.directionFeatures)blocked[e.featureStatus]=(blocked[e.featureStatus]??0)+1;
const eligible=events.filter(e=>e.directionFeatures&&e.labels[3]);
const integrity={sessions:58,events:events.length,uniqueSymbols:new Set(events.map(e=>e.symbol)).size,uniqueSymbolSessions:new Set(events.map(e=>e.symbolSessionId)).size,featureReady:events.filter(e=>e.directionFeatures).length,blocked,trainingTargetCompleteEvents:eligible.length,trainingDirectionalRows:eligible.length*2,targetPositive:eligible.reduce((s,e)=>s+Number(e.labels[3].LONG.net>0)+Number(e.labels[3].SHORT.net>0),0),targetMissingAmongFeatureReady:events.filter(e=>e.directionFeatures&&!e.labels[3]).length,datasetSha256:hash(datasetBytes)};integrity.targetNegative=integrity.trainingDirectionalRows-integrity.targetPositive;write('dataset-integrity.json',integrity);
const cv=[];const combined=new Map(FIT.threshold.candidates.map(t=>[t,{events:[],ledger:[],watch:0,noAction:0,entered:0,expired:0}]));
for(let i=0;i<4;i++){
 const split=foldSessions(i),train=events.filter(e=>split.train.includes(e.sessionDate)),ev=events.filter(e=>split.evaluate.includes(e.sessionDate)),model=fitRows(train);
 const result={fold:i,...split,trainEvents:train.length,evalEvents:ev.length,model,thresholds:{}};
 const decisionInputs=ev.map(({eventId,symbolSessionId,stateBefore,directionFeatures})=>({eventId,symbolSessionId,stateBefore,directionFeatures}));
 for(const t of FIT.threshold.candidates){const dec=stateful(decisionInputs,model,t);result.thresholds[t]=metrics(ev,dec,split.evaluate);const c=combined.get(t);c.events.push(...ev);c.ledger.push(...dec.ledger);for(const k of ['watch','noAction','entered','expired'])c[k]+=dec[k];}
 cv.push(result);write(`fold-${i}.json`,result);
}
const dates=FIT.cv.folds.flatMap((_,i)=>foldSessions(i).evaluate);
const results=FIT.threshold.candidates.map(threshold=>{const c=combined.get(threshold);return {threshold,...metrics(c.events,c,dates)};});
write('threshold-results.json',results);
const valid=results.filter(r=>cv.every(f=>f.thresholds[r.threshold].horizons[3].complete>0)&&r.horizons[3].meanNet>0&&r.medianActiveSessionNet3>0);
const vector=r=>[r.horizons[3].meanNet,r.coverage,r.sessionStability,-r.immediateAdverse,-r.meanMAE3,r.meanMFE3];
const finite=r=>[r.immediateAdverse,r.meanMAE3,r.meanMFE3,r.coverage,r.sessionStability,r.horizons[3].meanNet].every(Number.isFinite);
const complete=valid.every(finite);
const frontier=complete?valid.filter(r=>!valid.some(q=>q!==r&&vector(q).every((x,i)=>x>=vector(r)[i])&&vector(q).some((x,i)=>x>vector(r)[i]))):[];
frontier.sort((a,b)=>b.medianActiveSessionNet3-a.medianActiveSessionNet3||b.coverage-a.coverage||a.threshold-b.threshold);
const winner=frontier[0]??null;
let model=null,modelSha=null;
if(winner){model={artifactClass:'OFFLINE_DEVELOPMENT_CANDIDATE_NOT_PRODUCTION',...pins,features:CONTRACT.features,selectorModelDigest:CONTRACT.selectorModelDigest,selectorFreezeSHA:CONTRACT.selectorFreezeSHA,threshold:winner.threshold,...fitRows(events),runtime:process.versions,seed:FIT.model.randomSeed,validationOpened:false,safety:CONTRACT.safety};modelSha=write('candidate-model.json',model);}
const audit={pitViolations:0,stateViolations:0,duplicateViolations:0,basis:'Fail-closed source, prefix, feature-hash, same-session-label and state-uniqueness assertions; not an independent audit',reserve180To282NewAccess:0,freshValidationOpened:0,freshOosOpened:0,safety:CONTRACT.safety};
const report={status:winner?'DEVELOPMENT_CANDIDATE_FROZEN_REVIEW_REQUIRED':complete?'DEVELOPMENT_NO_GO':'DEVELOPMENT_INCONCLUSIVE_MISSING_DIAGNOSTIC',...pins,integrity,cv,thresholdResults:results,selectedThreshold:winner?.threshold??null,modelSha256:modelSha,model,audit,limitations:['Development OOF used to select threshold; selection-biased, not OOS','Historical reconstruction and later-frozen Selector; not contemporaneous prospective evidence','P21 17-session reference is unpaired; no historical prior reconstruction','No execution or portfolio returns; overlapping research opportunities','Provider-vintage and cross-research exposure uncertainty retained'],freshValidationAllowed:false};
write('development-report.json',report);
write('claude-review-packet.json',{...report,allocation:ALLOCATION,fitContract:FIT,featureTargetStateContract:CONTRACT,freshReservation:read('predict/research/phase57-minimal-stateful-entry-fresh-allocation.json'),question:'Should this frozen Minimal Stateful Hybrid Entry candidate be opened on Fresh Validation?',reviewReadiness:winner?'CANDIDATE_REVIEW_READY':'NO_CANDIDATE_DO_NOT_OPEN_VALIDATION'});
console.log(JSON.stringify({status:report.status,integrity,thresholdResults:results,selectedThreshold:report.selectedThreshold,modelSha256:modelSha,audit}));
