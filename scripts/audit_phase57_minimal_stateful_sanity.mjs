import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
import {CONTRACT,CONTRACT_SHA256,SAFETY,MinimalStatefulEntry,sha256,validationAdmission} from './lib/phase57-minimal-stateful-entry.mjs';
const args=process.argv.slice(2),arg=k=>args[args.indexOf(k)+1];
for(const k of ['--baseline-root','--entry-reference-root','--output-dir'])if(!args.includes(k))throw Error(`REQUIRED ${k}`);
const base=path.resolve(arg('--baseline-root')),entry=path.resolve(arg('--entry-reference-root')),out=path.resolve(arg('--output-dir'));
const hash=b=>createHash('sha256').update(b).digest('hex'),read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const accesses=[];
const readVerified=(file,sha,informationClass)=>{const b=fs.readFileSync(file);assert.equal(hash(b),sha);accesses.push({path:file,sha256:sha,informationClass,purpose:'OUTCOME_BLIND_FEATURE_STATE_SANITY',accessAt:new Date().toISOString()});return b;};
const releasePath=path.join(base,'predict/research/phase57-entry-baseline-measured-2026-09-09/release-manifest.json');
const release=JSON.parse(readVerified(releasePath,CONTRACT.baselineReleaseSha256,'MANIFEST'));
const releaseHashes=new Map(release.files.map(f=>[f.path,f.sha256]));
const releasedInput=JSON.parse(readVerified(path.join(path.dirname(releasePath),'input-manifest.json'),releaseHashes.get('input-manifest.json'),'MANIFEST'));
const gateDir=path.join(base,'predict/research/phase57-entry-baseline-real-gates-2026-09-09');
const gates=JSON.parse(readVerified(path.join(gateDir,'gates.json'),releasedInput.gateSha256,'MANIFEST'));
const inventoryBytes=gunzipSync(fs.readFileSync(path.join(gateDir,'archive-inventory.json.gz')));assert.equal(hash(inventoryBytes),gates.archiveInventorySha256);
const inventory=JSON.parse(inventoryBytes).inventory;
assert.equal(inventory.length,17);assert.deepEqual(inventory.map(r=>r.sessionDate),gates.eligibleSessions);
const measurement=path.join(base,'tmp/baseline-measurement-v1');
const sourceManifest=JSON.parse(readVerified(path.join(measurement,'evidence-manifest.json'),releaseHashes.get('evidence-manifest.json'),'MANIFEST'));
const hashes=new Map(sourceManifest.files.map(f=>[f.name,f.sha256]));
const points=JSON.parse(readVerified(path.join(measurement,'point-ledger.json'),hashes.get('point-ledger.json'),'SELECTOR_OUTPUT_METADATA'));
const sourceCode=path.join(entry,'predict/daytrade/phase57-entry-quality-v2-research.js');
const sourceBytes=fs.readFileSync(sourceCode);
assert.equal(createHash('sha1').update(`blob ${sourceBytes.length}\0`).update(sourceBytes).digest('hex'),'27414a4a5784bd4480ce2ff0135747fde16f4971');
const referenceCodeSha256=hash(sourceBytes);
const {buildEntryV2IntradayContext}=await import(pathToFileURL(sourceCode).href);
const rows=[],sessions=[],featureReasons={};let commonFeatureParityChecks=0;
for(const inv of inventory){
  assert.ok(inv.sessionDate>='2026-08-13'&&inv.sessionDate<='2026-09-04');
  const source=readVerified(path.join(entry,'tmp/entry-v2-historical-market',inv.archiveLocation),inv.fileSha256,'BASELINE17_MARKET_DATA');
  const decoded=gunzipSync(source);assert.equal(hash(decoded),inv.uncompressedSha256);
  const bySymbol=new Map(decoded.toString().trim().split('\n').map(JSON.parse).map(r=>[r.symbol,r.bars.filter(b=>!['11:30','15:30'].includes(new Date(Date.parse(b.timestamp)+32400000).toISOString().slice(11,16))).map(b=>({timestamp:b.timestamp,availableAt:new Date(Date.parse(b.timestamp)+300000).toISOString(),open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume}))]));
  const file=`${inv.sessionDate}.events.ndjson.gz`;
  const events=gunzipSync(readVerified(path.join(measurement,file),hashes.get(file),'BASELINE17_SELECTED_EVENTS_REFERENCE')).toString().trim().split('\n').map(JSON.parse);
  const byTime=new Map();for(const e of events){if(!byTime.has(e.decisionAt))byTime.set(e.decisionAt,[]);byTime.get(e.decisionAt).push(e);}
  const state=new MinimalStatefulEntry(inv.sessionDate);let count=0,ready=0;
  for(const p of points.filter(p=>p.sessionDate===inv.sessionDate)){
    const at=byTime.get(p.decisionTimestamp)??[];
    const snapshot={decisionTimestamp:p.decisionTimestamp,complete:p.status==='REPLAYED',selected:at.map(e=>({symbol:e.symbol,rank:e.hybridRank,score:e.hybridScore,priceReference:e.priceReference})),selectorModelDigest:CONTRACT.selectorModelDigest,selectorFreezeSHA:CONTRACT.selectorFreezeSHA,selectionLineage:p.selectionSha256??null,sourceClass:'HISTORICAL_RECONSTRUCTION_LATER_FETCHED'};
    const prefixes=Object.fromEntries(at.map(e=>[e.symbol,bySymbol.get(e.symbol).filter(b=>b.availableAt<=e.decisionAt)]));
    const result=state.step(snapshot,prefixes);
    for(const row of result.events){
      assert.notEqual(row.decision.action,'ENTER');assert.equal(row.p21UsedAsGate,false);count++;
      if(row.featureStatus==='READY'){
        ready++;
        const ref=buildEntryV2IntradayContext({intradayBars:prefixes[row.symbol],asOf:row.decisionTimestamp});
        for(const f of row.directionFeatures){
          const pairs=[['directionalReturnFromOpenPct','returnFromOpenPct',f.direction],['directionalVwapDistancePct','vwapDistancePct',f.direction],['directionalMomentum3Pct','threeBarMomentumPct',f.direction],['directionalMomentumAccelerationPct','momentumAccelerationPct',f.direction],['relativeVolume5','relativeVolume5',1]];
          for(const [a,b,d] of pairs){assert.ok(Math.abs(f.features[a]-ref[b]*d)<1e-10);commonFeatureParityChecks++;}
        }
      }else featureReasons[row.featureStatus]=(featureReasons[row.featureStatus]??0)+1;
      rows.push(row);
    }
  }
  state.close(`${inv.sessionDate}T15:30:00+09:00`);
  assert.equal(count,events.length);assert.ok([...state.states.values()].every(s=>s.entryCount===0&&s.state==='EXPIRED'));
  sessions.push({sessionDate:inv.sessionDate,selectedEvents:count,featureReadyEvents:ready,featureBlockedEvents:count-ready,uniqueSymbolSessions:state.states.size,modelAvailable:false,performanceComputed:false});
}
assert.equal(rows.length,4542);assert.equal(new Set(rows.map(r=>r.eventId)).size,4542);
const dataset=gzipSync(rows.map(r=>JSON.stringify(r)).join('\n')+'\n');
fs.mkdirSync(out,{recursive:true});fs.writeFileSync(path.join(out,'phase57-minimal-stateful-entry-sanity-events.ndjson.gz'),dataset,{flag:'wx'});
const audit={createdAt:new Date().toISOString(),architectureId:CONTRACT.architectureId,contractSha256:CONTRACT_SHA256,baselineReleaseSha256:CONTRACT.baselineReleaseSha256,
 sessions,selectedEvents:rows.length,directionalRowsReady:rows.filter(r=>r.featureStatus==='READY').length*2,featureBlockedReasons:featureReasons,commonFeatureParityChecks,commonFeatureParityMismatches:0,
 referenceCodePath:'predict/daytrade/phase57-entry-quality-v2-research.js',referenceCodeSha256,
 datasetSha256:hash(dataset),uncompressedDatasetSha256:sha256(rows.map(r=>JSON.stringify(r)).join('\n')+'\n'),
 logicalPitViolations:0,duplicateEventViolations:0,stateViolations:0,trainingPerformed:false,realModelArtifactAvailable:false,newPerformanceComputed:false,newFutureLabelsGenerated:false,
 protected190NewlyOpened:0,protected190NewOutcomesViewed:0,freshValidationOutcomesViewed:0,oosOutcomesViewed:0,baselineEvidenceChanged:false,sourceVintageVerified:false,
 validationAdmission:validationAdmission(),accessLedger:accesses,safety:SAFETY};
fs.writeFileSync(path.join(out,'phase57-minimal-stateful-entry-sanity-audit.json'),JSON.stringify(audit,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({selectedEvents:audit.selectedEvents,directionalRowsReady:audit.directionalRowsReady,featureBlockedReasons:featureReasons,commonFeatureParityChecks,protectedNewlyOpened:0,newPerformanceComputed:false}));
