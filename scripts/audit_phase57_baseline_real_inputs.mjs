import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { gunzipSync } from 'node:zlib';
import assert from 'node:assert/strict';
import { buildHybridP21Input, P21_OPTIONS, P21_HORIZONS } from './lib/phase57-hybrid-p21-adapter.mjs';
import { verifyFreeze, SAFETY } from './lib/phase57-hybrid-p21-baseline.mjs';
const args=process.argv.slice(2); const arg=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const entryRoot=path.resolve(arg('--entry-root','')),selectorRoot=path.resolve(arg('--selector-root',''));
const out=path.resolve(arg('--output-dir','tmp/real-input-audit'));fs.mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const write=(name,v)=>fs.writeFileSync(path.join(out,name),JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const imp=(root,p)=>import(pathToFileURL(path.join(root,p)).href);
const policy=read('predict/research/phase57-entry-baseline-measurement-policy-v1.json');
const pre=read('predict/research/phase57-hybrid-p21-entry-baseline-precommit.json');
const dates=pre.allocation.sessions;
const archive=path.join(entryRoot,'tmp/entry-v2-historical-market');
const manifest=read(path.join(archive,'manifest.json'));const {manifestContentSha256,...core}=manifest;
assert.equal(hash(JSON.stringify(core)),manifestContentSha256);
assert.equal(manifestContentSha256,'0f0286aea9433f02e1aada36b31a7ac34a6fd3c65eb7241a108c9b03156e78bb');
assert.deepEqual(manifest.sessionShards.map(s=>s.sessionDate),dates);
assert.equal(manifest.sourceClass,policy.sourceClass);
const sourcePins=[];
const pins=[
 [entryRoot,'predict/daytrade/phase57-p21-prospective-history.js','966abb239c99449d01b8b7be21ea9283cf6999d3'],
 [entryRoot,'predict/daytrade/phase57-p21-prospective-frozen-base.js','406ee8121a7b7b2b61ca18853fa51c1569c71cd0'],
 [entryRoot,'predict/daytrade/phase57-p21-prospective-feature-feed.js','65a93fa56c89c08fcf82deeaf068513d028d20ec'],
 ...pre.selector.implementationGitBlobs.map(x=>[selectorRoot,x.path,x.sha]),
];
for(const [root,p,sha] of pins){const b=fs.readFileSync(path.join(root,p));assert.equal(createHash('sha1').update(`blob ${b.length}\0`).update(b).digest('hex'),sha);sourcePins.push({path:p,gitBlobSha:sha});}
const universeBytes=fs.readFileSync(path.join(entryRoot,'data/screener-universe.json'));assert.equal(hash(universeBytes),manifest.universe.sourceSha256);
const requiredSymbols=read(path.join(entryRoot,'data/screener-universe.json')).entries.map(x=>x.symbol).sort();
let receiptFilesVerified=0;
for(const r of manifest.receipts){for(const [file,sha] of [[r.rawFile,r.rawCompressedFileSha256],[r.normalizedFile,r.normalizedCompressedFileSha256]]){assert.equal(hash(fs.readFileSync(path.join(archive,file))),sha);receiptFilesVerified++;}}
const schedule=date=>[...Array.from({length:30},(_,i)=>9*60+5+i*5),...Array.from({length:36},(_,i)=>12*60+35+i*5)].map(m=>new Date(`${date}T${String(Math.floor(m/60)).padStart(2,'0')}:${String(m%60).padStart(2,'0')}:00+09:00`).toISOString());
const loadSession=shard=>{
 const b=fs.readFileSync(path.join(archive,shard.file));assert.equal(hash(b),shard.compressedFileSha256);
 const raw=gunzipSync(b);assert.equal(hash(raw),shard.uncompressedNdjsonSha256);
 return raw.toString().trim().split('\n').map(JSON.parse);
};
let totalBars=0;const inventory=[];let firstSession=null;
for(const shard of manifest.sessionShards){
 const rows=loadSession(shard);let excludedBoundary=0,bars=0,duplicates=0;
 const entries=rows.map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars.filter(b=>{
  assert.equal(b.sessionDate,shard.sessionDate); const jst=new Date(Date.parse(b.timestamp)+9*3600000).toISOString().slice(11,16);
  if(['11:30','15:30'].includes(jst)){excludedBoundary++;return false;}return true;
 }).map(b=>{
  assert.ok(['open','high','low','close','volume'].every(k=>Number.isFinite(b[k])));assert.ok(b.volume>=0&&b.low>0&&b.high>=Math.max(b.open,b.close)&&b.low<=Math.min(b.open,b.close));
  return {timestamp:b.timestamp,availableAt:new Date(Date.parse(b.timestamp)+300000).toISOString(),sessionDate:shard.sessionDate,open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume};
 })}));
 for(const e of entries){bars+=e.bars.length;duplicates+=e.bars.length-new Set(e.bars.map(b=>b.timestamp)).size;}
 assert.equal(duplicates,0);totalBars+=bars;
 const availableSymbols=entries.map(x=>x.symbol).sort(),missingSymbols=requiredSymbols.filter(s=>!availableSymbols.includes(s));
 const points=schedule(shard.sessionDate).map(t=>{const symbols=entries.filter(e=>e.bars.some(b=>b.availableAt<=t)).length;return {decisionTimestamp:t,availableSymbols:symbols,marketCoverageReady:symbols>=policy.minimumDecisionMarketSymbols};});
 const good=points.filter(x=>x.marketCoverageReady).length;
 const ready=availableSymbols.length/requiredSymbols.length>=policy.minimumSessionUniverseFraction&&good/points.length>=policy.minimumDecisionCoverageFraction;
 inventory.push({sessionDate:shard.sessionDate,source:manifest.provider,sourceClass:manifest.sourceClass,archiveCreatedAt:manifest.createdAt,archiveLocation:shard.file,artifactRunId:null,
 fileSha256:shard.compressedFileSha256,uncompressedSha256:shard.uncompressedNdjsonSha256,expectedUniverseCount:requiredSymbols.length,availableUniverseCount:availableSymbols.length,
 requiredSymbols,availableSymbols,missingSymbols,expectedDecisionPoints:points.length,availableDecisionPoints:good,points,
 requiredGridSlots:requiredSymbols.length*66,availableBars:bars,absentGridSlots:requiredSymbols.length*66-bars,missingVsNoTrade:'NOT_DISTINGUISHABLE;NO_FILL',excludedProviderBoundaryBars:excludedBoundary,
 timestampSemantics:'PROVIDER_NATIVE_BAR_OPEN;RECONSTRUCTED_AVAILABLE_AT_OPEN_PLUS_5M',coverageGate:ready?'GO':'NO_GO',replayPossiblePendingOtherGates:ready});
 if(shard.sessionDate===dates[0])firstSession=entries;
 console.log(JSON.stringify({stage:'ARCHIVE_METADATA',session:shard.sessionDate,hashVerified:true,coverageGate:ready?'GO':'NO_GO'}));
}
write('archive-inventory.json',{manifestSha256:hash(fs.readFileSync(path.join(archive,'manifest.json'))),manifestContentSha256,receiptFilesVerified,totalBars,inventory,safety:SAFETY});
const frozenDir=path.join(entryRoot,'tmp/entry-v2-frozen');
const snapBytes=fs.readFileSync(path.join(frozenDir,'canonical/phase57-p24-9-oos-byte-snapshot.json'));
assert.equal(hash(snapBytes),'10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a');
assert.equal(hash(fs.readFileSync(path.join(frozenDir,'canonical.zip'))),'a9c3c70a49938f56eec8bcf299e443359f2f64919eac247c120172b0b34ec463');
const snap=JSON.parse(snapBytes);assert.ok(snap.effectiveStartIso>'2026-06-11T23:59:59Z');
const packBytes=fs.readFileSync(path.join(frozenDir,'p25-history.json'));assert.equal(hash(packBytes),'0d110f22bc664da3d7b3615e4bee765eb642631cda1146f38a1b50bfbdcd9b67');
const pack=JSON.parse(packBytes);
const {buildP252PinnedHistoricalSessions}=await imp(entryRoot,'predict/daytrade/phase57-p25-2k-pinned-history-bridge.js');
assert.deepEqual(buildP252PinnedHistoricalSessions({snapshot:snap,snapshotSha256:hash(snapBytes)}).sessions,pack.sessions);
const uniqueDates=[...new Set(pack.sessions.map(s=>s.sessionDate))].sort();assert.ok(uniqueDates[0]>'2026-06-11');assert.equal(uniqueDates.at(-1),'2026-08-12');
const {buildProspectiveP21HistoricalRows}=await imp(entryRoot,'predict/daytrade/phase57-p21-prospective-history.js');
const history=buildProspectiveP21HistoricalRows({sessions:pack.sessions,horizons:P21_HORIZONS});assert.equal(history.complete,true);
const flat=Object.values(history.historicalHorizonRowsByBars).flat();const maxOutcomeAt=flat.map(x=>x.outcomeAt).sort().at(-1);
assert.ok(maxOutcomeAt<dates[0]+'T00:00:00.000Z');
const priorAudit={packSha256:hash(packBytes),snapshotSha256:hash(snapBytes),canonicalZipSha256:hash(fs.readFileSync(path.join(frozenDir,'canonical.zip'))),packCreatedAt:pack.createdAt,
 effectiveStartIso:snap.effectiveStartIso,dataEndIso:snap.dataEndIso,uniqueSessionDates:uniqueDates,symbolSessionRows:pack.sessions.length,
 symbols:[...new Set(pack.sessions.map(x=>x.symbol))],rowCounts:history.rowCounts,latestOutcomeTimestamp:maxOutcomeAt,sourcePins,
 futureOutcomeViolations:flat.filter(x=>x.outcomeAt>=dates[0]+'T00:00:00.000Z').length,baselineOutcomesViewed:false,safety:SAFETY};
write('prior-audit-before-selection.json',priorAudit);
const model=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-model.json'));
const freeze=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-freeze.json'));verifyFreeze(model,freeze);
const {runPhase57MinimalHybrid}=await imp(selectorRoot,'predict/daytrade/phase57-selector-minimal-hybrid.js');
const t=dates[0]+'T01:00:00.000Z';
const entries=firstSession.map(e=>({...e,bars:e.bars.filter(b=>b.availableAt<=t)}));
const selection=runPhase57MinimalHybrid({featureCutoff:t,entries,model});
assert.ok(selection.selected.length>0,'No case at fixed gate timestamp; do not pick using outcome');
const candidate=selection.selected[0],bars=entries.find(e=>e.symbol===candidate.symbol).bars;
const adapted=buildHybridP21Input({selection,symbol:candidate.symbol,sessionDate:dates[0],decisionTimestamp:t,contextBars:bars,selectorFreezeSHA:pre.selector.freezeSha256,sourceClass:policy.sourceClass});
const {buildProspectiveP21FeatureFeed}=await imp(entryRoot,'predict/daytrade/phase57-p21-prospective-feature-feed.js');
const {buildProspectiveP21FrozenDecision}=await imp(entryRoot,'predict/daytrade/phase57-p21-prospective-frozen-base.js');
const direct=buildProspectiveP21FeatureFeed({symbol:candidate.symbol,sessionDate:dates[0],bars5m:bars,horizons:P21_HORIZONS,latestBarClosed:true});
assert.deepEqual(adapted.currentRowsByHorizon,direct.currentRowsByHorizon);
console.log(JSON.stringify({stage:'REAL_PRIOR_SELECTION_STARTED',rowCounts:history.rowCounts}));
const cache=new Map();
const a=buildProspectiveP21FrozenDecision({currentRowsByHorizon:direct.currentRowsByHorizon,historicalHorizonRowsByBars:history.historicalHorizonRowsByBars,options:P21_OPTIONS,priorOnlyCache:cache});
const b=buildProspectiveP21FrozenDecision({...adapted,historicalHorizonRowsByBars:history.historicalHorizonRowsByBars,priorOnlyCache:new Map()});
assert.deepEqual(a,b);assert.ok(a.complete);
const selected=a.selection?.selected;assert.ok(selected&&selected.signalCount>=50);assert.ok(a.decision.context.priorTrainingRows>=200);
const parity={decisionTimestamp:t,symbol:candidate.symbol,inputParity:true,outputParity:true,independentPriorRefits:true,decisionFieldsCompared:Object.keys(a.decision.context),priorCutoff:direct.featureCutoff,
 latestOutcomeTimestampUsed:a.decision.context.maxPriorOutcomeAt,priorTrainingRows:a.decision.context.priorTrainingRows,selectedPriorSignalCount:selected.signalCount,
 selectedHorizonBars:a.decision.context.selectedHorizonBars,selectedFeatureFamily:a.decision.context.selectedFeatureFamily,selectedModelType:a.decision.context.selectedModelType,selectedConfigId:a.decision.context.selectedConfigId,selectedThreshold:a.decision.context.selectedThreshold,
 baselineFutureLabelsViewed:false};
write('real-adapter-parity.json',parity);
const gates={createdAt:new Date().toISOString(),policySha256:hash(fs.readFileSync('predict/research/phase57-entry-baseline-measurement-policy-v1.json')),
 gate1:inventory.every(x=>x.coverageGate==='GO')?'GO':'NO_GO',gate2:'GO',gate3:'GO',gate4:'GO',eligibleSessions:inventory.filter(x=>x.coverageGate==='GO').map(x=>x.sessionDate),
 minimumEligibleSessions:policy.MIN_BASELINE_ELIGIBLE_SESSIONS,protectedNewlyOpened:0,protectedNewOutcomeViewed:0,baselineOutcomeViewed:false,
 sourceClass:policy.sourceClass,archiveInventorySha256:hash(fs.readFileSync(path.join(out,'archive-inventory.json'))),priorAuditSha256:hash(fs.readFileSync(path.join(out,'prior-audit-before-selection.json'))),realParitySha256:hash(fs.readFileSync(path.join(out,'real-adapter-parity.json'))),safety:SAFETY};
gates.measurementAllowed=gates.gate1==='GO'&&gates.eligibleSessions.length>=gates.minimumEligibleSessions;
write('gates.json',gates);console.log(JSON.stringify({stage:'GATES_COMPLETE',...gates}));
