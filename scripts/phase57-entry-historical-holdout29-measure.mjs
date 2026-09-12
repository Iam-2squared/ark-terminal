import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {verifyDevelopmentContracts} from './lib/phase57-entry-development-fit.mjs';
import {CONTRACT,CONTRACT_SHA256,FEATURES,sha256} from './lib/phase57-minimal-stateful-entry.mjs';
import {labels,stateful,metrics,mean,median} from './lib/phase57-entry-development-measure.mjs';

const input=process.env.INPUT_DIR??'artifacts/holdout29-input';
const candidateDir=process.env.CANDIDATE_DIR??'artifacts/input/candidate';
const out=process.env.OUTPUT_DIR??'artifacts/holdout29-measurement';
const hash=b=>createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const pins=verifyDevelopmentContracts();fs.mkdirSync(out,{recursive:true});
const write=(name,value)=>{const b=JSON.stringify(value,null,2)+'\n';fs.writeFileSync(`${out}/${name}`,b,{flag:'wx'});fs.writeFileSync(`${out}/${name}.sha256`,`${hash(b)}  ${name}\n`,{flag:'wx'});return hash(b);};
const precommit=read('predict/research/phase57-entry-historical-holdout29-source-parity-precommit.json');
assert.equal(precommit.status,'HISTORICAL_HOLDOUT_SOURCE_PARITY_PRECOMMITTED_NO_OUTCOME_ACCESS');
assert.equal(precommit.holdoutRole,'HISTORICAL_HOLDOUT_DIAGNOSTIC_NOT_PROSPECTIVE_NOT_FORMAL_OOS');
assert.equal(precommit.candidatePolicy,'FROZEN_MINIMAL_STATEFUL_ENTRY_NO_RETRAIN_NO_RETUNE');
assert.equal(precommit.count,29);assert.equal(precommit.sessions.length,29);
const holdoutSessions=new Set(precommit.sessions);
function verifyHoldoutFrozenRow(row){
 const {featureSha256,...core}=row;
 assert.equal(sha256(core),featureSha256,'FEATURE_BYTES_CHANGED');
 assert.equal(row.contractSha256,CONTRACT_SHA256,'CONTRACT_SHA_MISMATCH');
 assert(holdoutSessions.has(row.sessionDate),'SESSION_NOT_IN_HOLDOUT29_PRECOMMIT');
 assert(Number.isFinite(Date.parse(row.latestAvailableAt))&&Date.parse(row.latestAvailableAt)<=Date.parse(row.decisionTimestamp),'FUTURE_FEATURE');
 assert.deepEqual(Object.keys(row.features),FEATURES,'FEATURE_ORDER_CHANGED');
 assert(FEATURES.every(k=>Number.isFinite(row.features[k])),'MISSING_FEATURE');
 return true;
}

const candidateBytes=fs.readFileSync(`${candidateDir}/candidate-model.json`);
assert.equal(hash(candidateBytes),'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a','CANDIDATE_SHA_MISMATCH');
const model=JSON.parse(candidateBytes);
assert.equal(model.artifactClass,'OFFLINE_DEVELOPMENT_CANDIDATE_NOT_PRODUCTION');
assert.equal(model.threshold,0.6);assert.equal(model.selectorModelDigest,CONTRACT.selectorModelDigest);assert.equal(model.selectorFreezeSHA,CONTRACT.selectorFreezeSHA);
assert.deepEqual(model.features,CONTRACT.features);assert.equal(model.validationOpened,false);
for(const [k,v] of Object.entries(CONTRACT.safety))assert.equal(model.safety[k],v);
assert.equal(model.weights.length,CONTRACT.features.length);assert.equal(model.means.length,CONTRACT.features.length);assert.equal(model.scales.length,CONTRACT.features.length);
assert(model.weights.every(Number.isFinite)&&model.means.every(Number.isFinite)&&model.scales.every(x=>Number.isFinite(x)&&x>0)&&Number.isFinite(model.intercept));

const manifests=fs.readdirSync(input).filter(f=>/^\d{4}-\d{2}-\d{2}\.manifest\.json$/.test(f));assert.equal(manifests.length,29,'EXPECTED_29_MANIFESTS');
const bundles=[];
for(const date of precommit.sessions){
 const m=read(`${input}/${date}.manifest.json`);assert.equal(m.sessionDate,date);assert.equal(m.sourceParity,true);assert.equal(m.labelsGenerated,false);assert.equal(m.candidateChanged,false);assert.equal(m.retraining,false);
 for(const [k,v] of Object.entries(pins))assert.equal(m[k],v);
 const bytes=gunzipSync(fs.readFileSync(`${input}/${date}.features.json.gz`));assert.equal(hash(bytes),m.featureSha256);
 const bundle=JSON.parse(bytes);assert.equal(bundle.sessionDate,date);assert.equal(bundle.points.length,66);
 for(const e of bundle.events){assert.equal(e.sessionDate,date);for(const r of e.directionFeatures??[])verifyHoldoutFrozenRow(r);}
 assert(bundle.events.some(e=>e.directionFeatures),'NO_FEATURE_READY_SESSION');bundles.push({m,bundle});
}
write('feature-barrier.json',{...pins,status:'ALL29_HOLDOUT_FEATURES_FROZEN_BEFORE_LABELS',candidateSha256:hash(candidateBytes),threshold:model.threshold,holdoutRole:precommit.holdoutRole,candidateChanged:false,retraining:false,sessions:bundles.map(x=>({sessionDate:x.m.sessionDate,featureSha256:x.m.featureSha256}))});

const events=[];
for(const {m,bundle} of bundles){
 fs.appendFileSync(`${out}/holdout29-access.ndjson`,JSON.stringify({sessionDate:m.sessionDate,stage:'HISTORICAL_HOLDOUT29_USED_FUTURE_LABELS',at:new Date().toISOString(),candidateSha256:hash(candidateBytes),threshold:model.threshold,candidateChanged:false,retraining:false,...pins,safety:CONTRACT.safety})+'\n');
 const bytes=gunzipSync(fs.readFileSync(`${input}/${m.sessionDate}.bars.json.gz`));assert.equal(hash(bytes),m.barsSha256);
 const source=new Map(JSON.parse(bytes).map(e=>[e.symbol,e.bars]));
 for(const e of bundle.events)events.push({...e,labels:labels(e,source.get(e.symbol)??[])});
}
assert.equal(new Set(events.map(e=>e.eventId)).size,events.length,'DUPLICATE_EVENT');
const decisionInputs=events.map(({eventId,symbolSessionId,stateBefore,directionFeatures})=>({eventId,symbolSessionId,stateBefore,directionFeatures}));
const decision=stateful(decisionInputs,model,model.threshold);
const result=metrics(events,decision,precommit.sessions);

const byId=new Map(events.map(e=>[e.eventId,e]));
const entered=decision.ledger.filter(r=>r.status==='ENTER').map(r=>({...byId.get(r.eventId),direction:r.direction}));
const net3=entered.flatMap(e=>e.labels[3]?[{eventId:e.eventId,sessionDate:e.sessionDate,direction:e.direction,net:e.labels[3][e.direction].net}]:[]);
const sorted=[...net3].sort((a,b)=>b.net-a.net);const total=net3.reduce((s,r)=>s+r.net,0);
const contribution=n=>{const v=sorted.slice(0,n).reduce((s,r)=>s+r.net,0);return {n:Math.min(n,sorted.length),net:v,shareOfNet:total===0?null:v/total};};
const values=net3.map(r=>r.net).sort((a,b)=>a-b);
const trimCount=Math.floor(values.length*0.05),trimmed=values.slice(trimCount,Math.max(trimCount,values.length-trimCount));
const sessionReturns=result.sessions.filter(s=>Number.isFinite(s.meanNet3));
const sessionSorted=[...sessionReturns].sort((a,b)=>b.meanNet3-a.meanNet3);const sessionTotal=sessionReturns.reduce((s,r)=>s+r.meanNet3,0);
const sessionContribution=n=>{const v=sessionSorted.slice(0,n).reduce((s,r)=>s+r.meanNet3,0);return {n:Math.min(n,sessionSorted.length),sumSessionMeanNet3:v,shareOfSessionMeanSum:sessionTotal===0?null:v/sessionTotal};};
const enterCounts=precommit.sessions.map(date=>result.sessions.find(s=>s.sessionDate===date)?.enter??0).sort((a,b)=>a-b);
const frequency={sessions:29,totalEnter:result.enter,meanEnterPerSession:mean(enterCounts),medianEnterPerSession:median(enterCounts),minEnterPerSession:enterCounts[0]??null,maxEnterPerSession:enterCounts.at(-1)??null,zeroEnterSessions:enterCounts.filter(x=>x===0).length,oneEnterSessions:enterCounts.filter(x=>x===1).length,twoEnterSessions:enterCounts.filter(x=>x===2).length,threePlusEnterSessions:enterCounts.filter(x=>x>=3).length};
const blocked={};for(const e of events)if(!e.directionFeatures)blocked[e.featureStatus]=(blocked[e.featureStatus]??0)+1;
const integrity={sessions:29,events:events.length,uniqueSymbols:new Set(events.map(e=>e.symbol)).size,uniqueSymbolSessions:new Set(events.map(e=>e.symbolSessionId)).size,featureReady:events.filter(e=>e.directionFeatures).length,blocked,label3CompleteAmongEntered:net3.length,label3MissingAmongEntered:entered.length-net3.length,candidateSha256:hash(candidateBytes),threshold:model.threshold,candidateChanged:false,retraining:false};
const distribution={n:values.length,mean:mean(values),median:median(values),trimmedMean5pctEachTail:mean(trimmed),min:values[0]??null,max:values.at(-1)??null,top1:contribution(1),top3:contribution(3),top5:contribution(5),top10:contribution(10),sessionTop1:sessionContribution(1),sessionTop3:sessionContribution(3),sessionTop5:sessionContribution(5)};
const developmentReference={evaluationSessions:28,enter:95,enterPerSession:95/28,coverage:0.0115,positiveRate3:0.5714,meanNet3Bps:120.87,medianNet3Bps:62.19,immediateAdverse:0.7174,LONG:9,SHORT:86,note:'Reference only; holdout is a different historical period and prior Selector exposure means this is not formal OOS.'};
const audit={pitViolations:0,stateViolations:0,duplicateViolations:0,basis:'Same fail-closed source-parity, prefix, feature-hash, same-session-label and state-uniqueness assertions as Development; not a new independent raw-source audit',candidateChanged:false,retraining:false,thresholdChanged:false,freshValidationOpened:0,freshOosOpened:0,reserve180To282NewAccess:0,safety:CONTRACT.safety};
const report={status:'HISTORICAL_HOLDOUT29_DIAGNOSTIC_MEASURED',holdoutRole:precommit.holdoutRole,limitations:['Not prospective and not formal untouched OOS','Reserve92-120 had prior Selector/Capacity role; use only as downstream frozen-Entry historical holdout diagnostic','Later-fetched historical reconstruction','Candidate was trained and threshold selected on a later historical block; no retraining/retuning occurred here'],candidate:{sha256:hash(candidateBytes),threshold:model.threshold,selectorModelDigest:model.selectorModelDigest,selectorFreezeSHA:model.selectorFreezeSHA},integrity,frequency,metrics:result,distribution,developmentReference,audit};
write('holdout29-report.json',report);
write('holdout29-summary.json',{status:report.status,integrity,frequency,horizons:result.horizons,immediateAdverse:result.immediateAdverse,meanMFE3:result.meanMFE3,meanMAE3:result.meanMAE3,medianMFE3:result.medianMFE3,medianMAE3:result.medianMAE3,LONG:result.LONG,SHORT:result.SHORT,positiveSessions:result.positiveSessions,negativeSessions:result.negativeSessions,noLabeledEnterSessions:result.noLabeledEnterSessions,sessionStability:result.sessionStability,distribution,audit});
console.log(JSON.stringify({status:report.status,integrity,frequency,horizons:result.horizons,immediateAdverse:result.immediateAdverse,LONG:result.LONG,SHORT:result.SHORT,positiveSessions:result.positiveSessions,negativeSessions:result.negativeSessions,distribution,audit}));
