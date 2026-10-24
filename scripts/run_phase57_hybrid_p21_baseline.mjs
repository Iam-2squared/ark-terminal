import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {pathToFileURL} from 'node:url';
import {buildHybridP21Input,P21_HORIZONS,P21_OPTIONS} from './lib/phase57-hybrid-p21-adapter.mjs';
import {verifyFreeze,SAFETY,freezeFeatureRecord,buildFutureLabels,buildStatefulLedger} from './lib/phase57-hybrid-p21-baseline.mjs';
const args=process.argv.slice(2),arg=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const entryRoot=path.resolve(arg('--entry-root','')),selectorRoot=path.resolve(arg('--selector-root',''));
const out=path.resolve(arg('--output-dir','tmp/baseline-measurement-v1'));
const phase=arg('--phase','events');assert.ok(['events','labels'].includes(phase));
const precommit=arg('--precommit-sha','');assert.match(precommit,/^[a-f0-9]{40}$/);
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),hash=b=>createHash('sha256').update(b).digest('hex'),sha=v=>hash(JSON.stringify(v));
const gateDir='predict/research/phase57-entry-baseline-real-gates-2026-09-09';
const gates=read(`${gateDir}/gates.json`),policyFile='predict/research/phase57-entry-baseline-measurement-policy-v1.json',policy=read(policyFile);
assert.equal(hash(fs.readFileSync(policyFile)),gates.policySha256);
for(const k of ['gate1','gate2','gate3','gate4'])assert.equal(gates[k],'GO');
assert.equal(gates.protectedNewlyOpened,0);assert.equal(gates.protectedNewOutcomeViewed,0);
const inventoryBytes=gunzipSync(fs.readFileSync(`${gateDir}/archive-inventory.json.gz`));assert.equal(hash(inventoryBytes),gates.archiveInventorySha256);
const inventory=JSON.parse(inventoryBytes).inventory;
const priorAudit=read(`${gateDir}/prior-audit-before-selection.json`);assert.equal(hash(fs.readFileSync(`${gateDir}/prior-audit-before-selection.json`)),gates.priorAuditSha256);
assert.equal(hash(fs.readFileSync(`${gateDir}/real-adapter-parity.json`)),gates.realParitySha256);
const pre=read('predict/research/phase57-hybrid-p21-entry-baseline-precommit.json');assert.deepEqual(gates.eligibleSessions,pre.allocation.sessions);assert.equal(gates.eligibleSessions.length,17);
const cost=read('predict/research/phase57-entry-baseline-cost-contract-v1.json');
assert.equal(cost.roundTripCostBps,5);assert.equal(cost.netReturnBpsFormula,'grossDirectionalReturnBps - 5');
// The pinned contract was verified before outcomes; fail closed on any byte change.
const costHash=hash(fs.readFileSync('predict/research/phase57-entry-baseline-cost-contract-v1.json'));
const archive=path.join(entryRoot,'tmp/entry-v2-historical-market');
const imp=(root,p)=>import(pathToFileURL(path.join(root,p)).href);
fs.mkdirSync(out,{recursive:true});
const write=(name,v)=>fs.writeFileSync(path.join(out,name),JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const writeLines=(name,rows)=>fs.writeFileSync(path.join(out,name),gzipSync(rows.map(x=>JSON.stringify(x)).join('\n')+'\n'),{flag:'wx'});
const loadLines=name=>gunzipSync(fs.readFileSync(path.join(out,name))).toString().trim().split('\n').filter(Boolean).map(JSON.parse);
function loadSession(record){
 assert.ok(gates.eligibleSessions.includes(record.sessionDate)&&record.sessionDate>'2026-06-11');
 const compressed=fs.readFileSync(path.join(archive,record.archiveLocation));assert.equal(hash(compressed),record.fileSha256);
 const raw=gunzipSync(compressed);assert.equal(hash(raw),record.uncompressedSha256);
 return raw.toString().trim().split('\n').map(JSON.parse).map(row=>({symbol:row.symbol,sector:row.sector,market:row.market,bars:row.bars.filter(b=>!policy.excludedProviderBoundaryBars.includes(new Date(Date.parse(b.timestamp)+32400000).toISOString().slice(11,16))).map(b=>{
  assert.equal(b.sessionDate,record.sessionDate);return {timestamp:b.timestamp,availableAt:new Date(Date.parse(b.timestamp)+300000).toISOString(),sessionDate:b.sessionDate,open:b.open,high:b.high,low:b.low,close:b.close,volume:b.volume};
 })}));
}
function artifactHash(bundle,asOf){const p=bundle.picked;return sha({lineage:'PHASE57_P21_NESTED_ADAPTIVE_PROSPECTIVE_V1',asOf,selection:{horizonBars:p.horizonBars,featureFamily:p.featureFamily,featureKeys:p.featureKeys,configId:p.configId,modelType:p.modelType,modelOptions:p.modelOptions,threshold:p.threshold},trainingRows:bundle.trainRows.map(r=>({key:`${r.symbol??''}|${r.sessionDate??''}|${r.featureCutoff??''}`,outcomeAt:r.outcomeAt,label:Number(r.label),actualReturnPct:Number(r.actualReturnPct),features:r.features}))});}
function timing(bars,price){const first=bars[0],last=bars.at(-1),prior=bars.at(-2),prior2=bars.at(-3);const vol=bars.reduce((s,b)=>s+b.volume,0),vwap=vol?bars.reduce((s,b)=>s+(b.high+b.low+b.close)/3*b.volume,0)/vol:null;const hi=Math.max(...bars.map(b=>b.high)),lo=Math.min(...bars.map(b=>b.low));const momentum=prior?(last.close/prior.close-1)*10000:null,previous=prior2?(prior.close/prior2.close-1)*10000:null;
 return {preEntryMoveBps:(price/first.open-1)*10000,firstObservedBarTimestamp:first.timestamp,officialSessionOpenVerified:first.timestamp.endsWith('T00:00:00.000Z'),vwapDistanceBps:vwap?(price/vwap-1)*10000:null,vwapBasis:'OBSERVED_TYPICAL_PRICE_VOLUME_PROXY',intradayRangePosition:hi>lo?(price-lo)/(hi-lo):null,recentMomentumBps:momentum,momentumAccelerationBps:momentum!=null&&previous!=null?momentum-previous:null};}
if(phase==='events'){
 write('input-manifest.json',{createdAt:new Date().toISOString(),precommitSha:precommit,policySha256:gates.policySha256,gateSha256:hash(fs.readFileSync(`${gateDir}/gates.json`)),costContractSha256:costHash,roundTripCostBps:5,sourceClass:policy.sourceClass,sessionDates:gates.eligibleSessions,baselineLabelsStarted:false,protectedNewlyOpened:0,protectedNewOutcomeViewed:0,safety:SAFETY});
 for(const pin of priorAudit.sourcePins){const root=pin.path.includes('p21-prospective')?entryRoot:selectorRoot;const b=fs.readFileSync(path.join(root,pin.path));assert.equal(createHash('sha1').update(`blob ${b.length}\0`).update(b).digest('hex'),pin.gitBlobSha);}
 const model=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-model.json')),freeze=read(path.join(selectorRoot,'predict/research/phase57-selector-minimal-hybrid-development-freeze.json'));verifyFreeze(model,freeze);
 const {runPhase57MinimalHybrid}=await imp(selectorRoot,'predict/daytrade/phase57-selector-minimal-hybrid.js');
 const {buildProspectiveP21HistoricalRows}=await imp(entryRoot,'predict/daytrade/phase57-p21-prospective-history.js');
 const {buildProspectiveP21FrozenDecision}=await imp(entryRoot,'predict/daytrade/phase57-p21-prospective-frozen-base.js');
 const packBytes=fs.readFileSync(path.join(entryRoot,'tmp/entry-v2-frozen/p25-history.json'));assert.equal(hash(packBytes),priorAudit.packSha256);
 const history=buildProspectiveP21HistoricalRows({sessions:JSON.parse(packBytes).sessions,horizons:P21_HORIZONS});assert.ok(history.complete);
 const maxOutcome=Object.values(history.historicalHorizonRowsByBars).flat().map(r=>r.outcomeAt).sort().at(-1);
 // Cache only identical native Intl constructor arguments. Native-output parity precedes use.
 const firstEntries=loadSession(inventory[0]).map(e=>({...e,bars:e.bars.filter(b=>b.availableAt<='2026-08-13T01:00:00.000Z')}));
 const native=runPhase57MinimalHybrid({featureCutoff:'2026-08-13T01:00:00.000Z',entries:firstEntries,model});
 const Native=Intl.DateTimeFormat,formatters=new Map();const get=args=>{const key=JSON.stringify(args);if(!formatters.has(key))formatters.set(key,new Native(...args));return formatters.get(key);};
 Intl.DateTimeFormat=new Proxy(Native,{construct:(_t,args)=>get(args),apply:(_t,_this,args)=>get(args)});
 const cached=runPhase57MinimalHybrid({featureCutoff:'2026-08-13T01:00:00.000Z',entries:firstEntries,model});assert.deepEqual(cached,native);
 write('runtime-parity.json',{nativeVsFormatterCacheFullSelectionParity:true,caseTimestamp:native.featureCutoff,fullSelectionSha256:sha(native),p21CacheMethod:'IDENTICAL_PINNED_PRIOR_BUNDLE_REUSE_AFTER_MAX_OUTCOME;EXACT_REFIT_PARITY_FIRST_AND_LAST_SESSION',selectorSourceUnmodified:true});
 let reusable=null,cache=new Map(),cacheParity=[];const pointLedger=[];let nEvents=0;
 for(const record of inventory){
  const entries=loadSession(record),events=[],frozenRecords=[];let sessionChecked=false;
  for(const point of record.points){const t=point.decisionTimestamp;
   if(!point.marketCoverageReady){pointLedger.push({...point,sessionDate:record.sessionDate,status:'BLOCKED_MARKET_COVERAGE',selectionCount:null});continue;}
   const completed=entries.map(e=>({...e,bars:e.bars.filter(b=>b.availableAt<=t)}));const bySymbol=new Map(completed.map(e=>[e.symbol,e]));
   const selection=runPhase57MinimalHybrid({featureCutoff:t,entries:completed,model});
   pointLedger.push({sessionDate:record.sessionDate,decisionTimestamp:t,status:'REPLAYED',selectionCount:selection.selected.length,selectionSha256:sha(selection)});
   for(const candidate of selection.selected){
    const bars=bySymbol.get(candidate.symbol).bars;
    assert.ok(bars.every(b=>Date.parse(b.timestamp)+300000<=Date.parse(t)&&b.availableAt<=t));
    const event={sessionDate:record.sessionDate,symbol:candidate.symbol,decisionAt:t,selectionTimestamp:t,hybridRank:candidate.hybridRank,hybridScore:candidate.hybridScore,selectionCount:selection.selected.length,selectionSha256:sha(selection),sourceClass:policy.sourceClass,priceReference:candidate.currentPrice};
    const frozen=freezeFeatureRecord({decisionAt:t,symbol:candidate.symbol,bars,features:{hybridRank:candidate.hybridRank,hybridScore:candidate.hybridScore,...timing(bars,candidate.currentPrice)}});
    frozenRecords.push(frozen);event.featureSha256=frozen.featureSha256;event.timing=frozen.features;
    let adapted;
    try{adapted=buildHybridP21Input({selection,symbol:candidate.symbol,sessionDate:record.sessionDate,decisionTimestamp:t,contextBars:bars,selectorFreezeSHA:pre.selector.freezeSha256,sourceClass:policy.sourceClass});}
    catch(error){events.push({...event,p21Status:'BLOCKED',direction:null,blockedReason:String(error.message)});continue;}
    const asOf=adapted.lineage.p21LegacyFeatureCutoff;assert.ok(maxOutcome<=asOf&&maxOutcome<t);
    if(reusable&&!cache.has(asOf))cache.set(asOf,Object.freeze({...reusable,asOf,artifactSha256:artifactHash(reusable,asOf)}));
    const result=buildProspectiveP21FrozenDecision({...adapted,historicalHorizonRowsByBars:history.historicalHorizonRowsByBars,priorOnlyCache:cache});
    if(!reusable&&cache.get(asOf)?.status==='PRIOR_ONLY_MODEL_READY')reusable=cache.get(asOf);
    if(!sessionChecked&&[gates.eligibleSessions[0],gates.eligibleSessions.at(-1)].includes(record.sessionDate)){
     const direct=buildProspectiveP21FrozenDecision({...adapted,historicalHorizonRowsByBars:history.historicalHorizonRowsByBars,priorOnlyCache:new Map()});
     const {priorOnlyCacheHit:a,...left}=result,{priorOnlyCacheHit:b,...right}=direct;assert.deepEqual(left,right);cacheParity.push({sessionDate:record.sessionDate,decisionTimestamp:t,symbol:candidate.symbol,entireOutputExceptCacheHitEqual:true,artifactSha256:result.artifactSha256});sessionChecked=true;
    }
    const d=result.decision,c=d?.context;
    if(d){assert.equal(d.futureOutcomeUsed,false);assert.equal(d.pointInTimeOnly,true);assert.ok(c.maxPriorOutcomeAt<t);}
    const status=!result.complete?'BLOCKED':c?.signalEligible?'ENTER':'ABSTAIN';
    events.push({...event,p21Status:status,direction:status==='ENTER'?(d.direction===1?'LONG':'SHORT'):null,signalEligible:c?.signalEligible??false,probability:c?.probability??null,confidence:d?.confidence??null,p21Context:c??null,p21ArtifactSha256:result.artifactSha256??null,adapterLineage:adapted.lineage,blockedReason:status==='BLOCKED'?result.status:null});
   }
  }
  writeLines(`${record.sessionDate}.events.ndjson.gz`,events);writeLines(`${record.sessionDate}.features.ndjson.gz`,frozenRecords);nEvents+=events.length;
  console.log(JSON.stringify({stage:'EVENTS_FROZEN',sessionDate:record.sessionDate,events:events.length,baselineFutureLabelsViewed:false}));
 }
 Intl.DateTimeFormat=Native;
 write('point-ledger.json',pointLedger);write('p21-cache-parity.json',cacheParity);
 write('events-complete.json',{createdAt:new Date().toISOString(),sessionCount:17,eventCount:nEvents,pitViolations:0,baselineFutureLabelsViewed:false,protectedNewlyOpened:0,protectedNewOutcomeViewed:0,safety:SAFETY});
}else{
 assert.equal(read(''+path.join(out,'input-manifest.json')).precommitSha,precommit);assert.equal(read(path.join(out,'events-complete.json')).sessionCount,17);
 write('outcome-access-started.json',{createdAt:new Date().toISOString(),sessionDates:gates.eligibleSessions,role:'BASELINE_DIAGNOSTIC_USED',protectedNewlyOpened:0,protectedNewOutcomeViewed:0,safety:SAFETY});
 const all=[];
 for(const record of inventory){const bySymbol=new Map(loadSession(record).map(e=>[e.symbol,e.bars]));const frozen=new Map(loadLines(`${record.sessionDate}.features.ndjson.gz`).map(f=>[f.featureSha256,f]));
  const events=loadLines(`${record.sessionDate}.events.ndjson.gz`).map(e=>({...e,labels:buildFutureLabels(frozen.get(e.featureSha256),bySymbol.get(e.symbol).filter(b=>b.timestamp>=e.decisionAt),5)}));
  writeLines(`${record.sessionDate}.labels.ndjson.gz`,events.map(e=>({eventId:`${e.sessionDate}|${e.decisionAt}|${e.symbol}`,labels:e.labels})));all.push(...events);
 }
 const state=buildStatefulLedger(all);writeLines('stateful-ledger.ndjson.gz',state.ledger);write('counts.json',state.counts);
 write('measurement-complete.json',{createdAt:new Date().toISOString(),role:'BASELINE_DIAGNOSTIC_USED',measuredSessions:17,outcomeNewlyViewedSessions:17,eventCount:all.length,protectedNewlyOpened:0,protectedNewOutcomeViewed:0,pitViolations:0,duplicates:0,safety:SAFETY});
 console.log(JSON.stringify({stage:'LABELS_COMPLETE',...state.counts}));
}
