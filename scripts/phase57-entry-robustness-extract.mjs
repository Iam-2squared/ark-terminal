// Read-only audit of already opened Development evidence. No fitting or labels.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {stateful,probability,metrics} from './lib/phase57-entry-development-measure.mjs';
import {verifyFrozenRow} from './lib/phase57-entry-development-fit.mjs';
const dir=process.argv[2],out=process.argv[3];
const sha=b=>createHash('sha256').update(b).digest('hex');
const read=f=>JSON.parse(fs.readFileSync(`${dir}/${f}`));
for(const f of fs.readdirSync(dir).filter(f=>f.endsWith('.json'))){assert.equal(sha(fs.readFileSync(`${dir}/${f}`)),fs.readFileSync(`${dir}/${f}.sha256`,'utf8').split(/\s/)[0]);}
const report=read('development-report.json'),candidate=read('candidate-model.json');
assert.equal(sha(fs.readFileSync(`${dir}/candidate-model.json`)),'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a');
const packed=fs.readFileSync(`${dir}/training-events.ndjson.gz`);
assert.equal(sha(gunzipSync(packed)),report.integrity.datasetSha256);
const events=gunzipSync(packed).toString().trim().split('\n').map(JSON.parse);
assert.equal(events.length,16392);assert.equal(new Set(events.map(e=>e.eventId)).size,events.length);
for(const e of events)for(const r of e.directionFeatures??[])verifyFrozenRow(r);
const entered=[],scores=[],recomputed=[];
for(let i=0;i<4;i++){
 const fold=read(`fold-${i}.json`),ev=events.filter(e=>fold.evaluate.includes(e.sessionDate));
 assert(!fold.train.some(d=>fold.evaluate.includes(d)));assert(fold.train.at(-1)<fold.evaluate[0]);
 const input=ev.map(({eventId,symbolSessionId,stateBefore,directionFeatures})=>({eventId,symbolSessionId,stateBefore,directionFeatures}));
 const by=new Map(ev.map(e=>[e.eventId,e]));
 for(const t of [.5,.55,.6]){
  const d=stateful(input,fold.model,t);recomputed.push({fold:i,threshold:t,metrics:metrics(ev,d,fold.evaluate)});
  if(t===.6)for(const x of d.ledger.filter(x=>x.status==='ENTER'))entered.push({...by.get(x.eventId),direction:x.direction,fold:i});
 }
 for(const e of ev)for(const r of e.directionFeatures??[])scores.push({eventId:e.eventId,stateBefore:e.stateBefore,fold:i,direction:r.direction,probability:probability(r,fold.model)});
}
assert.equal(entered.length,95);assert.equal(entered.filter(e=>e.labels[3]).length,84);
assert.equal(new Set(entered.map(e=>e.symbolSessionId)).size,95);
for(const t of [.5,.55,.6]){const a=recomputed.filter(x=>x.threshold===t),old=report.thresholdResults.find(x=>x.threshold===t);assert.equal(a.reduce((s,x)=>s+x.metrics.enter,0),old.enter);const n=a.reduce((s,x)=>s+x.metrics.horizons[3].complete,0),net=a.reduce((s,x)=>s+x.metrics.horizons[3].complete*x.metrics.horizons[3].meanNet,0)/n;assert(Math.abs(net-old.horizons[3].meanNet)<1e-10);}
fs.writeFileSync(out,JSON.stringify({report,candidate,entered,scores,events,recomputed}));
console.log('Original hashes, frozen feature rows and OOF ENTER/return parity PASS; no fitting, no new labels');
