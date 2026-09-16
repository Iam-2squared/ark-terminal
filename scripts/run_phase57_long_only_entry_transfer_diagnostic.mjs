import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {scoreL2Candidate} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {normalizeMinuteProvenance,measureCorrectedRow} from '../predict/long-only/phase57-long-only-corrected-measurement.js';
import {measureOnePct} from '../predict/long-only/phase57-long-only-top5-hit-evaluator.js';
import {
  assertCurrentEntryAssets,evaluateLongOnlyTransferSession,normalizeEntryBars,CURRENT_ENTRY_TRANSFER_ASSETS,CURRENT_ENTRY_TRANSFER_SAFETY,
} from '../predict/long-only/phase57-long-only-current-entry-transfer.js';

const arg=name=>{const index=process.argv.indexOf(name);return index<0?null:process.argv[index+1];};
for(const name of ['--cache-root','--output-dir'])if(!arg(name))throw new Error(`required ${name}`);
const cacheRoot=path.resolve(arg('--cache-root')),outputDir=path.resolve(arg('--output-dir'));
const root=path.resolve(new URL('..',import.meta.url).pathname),read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const sha=value=>createHash('sha256').update(value).digest('hex');
const spec=read(path.join(root,'predict/research/phase57-long-only-frozen-selector-v1.json'));
const transferContract=read(path.join(root,'predict/research/phase57-long-only-current-entry-transfer-contract-v1.json'));
const modelPath=path.join(root,'predict/research/phase57-msh-entry-v1-model.json');
const featureContractPath=path.join(root,'predict/research/phase57-minimal-stateful-entry-contract.json');
const featureImplementationPath=path.join(root,'scripts/lib/phase57-minimal-stateful-entry.mjs');
const modelBytes=fs.readFileSync(modelPath),model=JSON.parse(modelBytes);
assertCurrentEntryAssets({model,modelBytes,contractBytes:fs.readFileSync(featureContractPath),implementationBytes:fs.readFileSync(featureImplementationPath)});
if(transferContract.status!=='FROZEN_BEFORE_TRANSFER_OUTCOMES'||transferContract.scope.validationOpened!==false||transferContract.scope.oosOpened!==false)throw new Error('TRANSFER_CONTRACT_NOT_FROZEN_OR_SEALED');
if(spec.hashes.freezePayloadSha256!==transferContract.frozenSelector.frozenPayloadSha256||spec.hashes.savedModelArtifactSha256!==CURRENT_ENTRY_TRANSFER_ASSETS.selectorArtifactSha256)throw new Error('FROZEN_SELECTOR_TRANSFER_IDENTITY_MISMATCH');
if(spec.freezePayload.development.sessionCount!==76||spec.freezePayload.development.decisionTimestampCount!==760||spec.freezePayload.development.top5SelectionEvents!==3800)throw new Error('FROZEN_SELECTOR_DEVELOPMENT_COUNT_MISMATCH');

const plan=read(path.join(root,'predict/long-only/phase57-long-only-data-plan.json'));
const allocation=read(path.join(root,'predict/long-only/phase57-long-only-session-allocation-v3.json'));
const l1=read(path.join(root,'predict/long-only/phase57-long-only-l1-discovery-sessions.json'));
const l2=read(path.join(root,'predict/long-only/phase57-long-only-l2-development-sessions.json'));
const v2=read(path.join(root,'predict/long-only/phase57-long-only-v2-development-sessions.json'));
const groups=[
  {name:'L1',sessions:l1.sessions,manifest:'l1-minute-manifest.json',sessionHash:l1.sessionListSha256},
  {name:'V2',sessions:v2.sessions,manifest:'v2-minute-manifest.json',sessionHash:v2.sessionListSha256},
  {name:'C',sessions:allocation.partitions.DEVELOPMENT_C,manifest:'l2-minute-manifest.json',sessionHash:l2.sessionListSha256},
  {name:'D',sessions:allocation.partitions.DEVELOPMENT_D,manifest:'l2-minute-manifest.json',sessionHash:l2.sessionListSha256},
];
const frozenSessions=spec.freezePayload.development.sessions;
const decisionSchedule=spec.freezePayload.selectorSpecification.ranking.decisionTimesJst;
const artifact=spec.freezePayload.selectorSpecification.model.configuration;
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');
const symkey=(sessionDate,symbol)=>`${sessionDate}|${symbol}`;
const rowKey=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const bySymbol=rows=>{const map=new Map();for(const row of rows){const key=symkey(row.sessionDate,row.symbol);if(!map.has(key))map.set(key,[]);map.get(key).push(row);}return map;};
const l0s=new Map(),allEvents=[],allOpportunities=[],allTicks=[],sessionAudits=[];

function sourceFor(sessionDate){
  const matches=groups.filter(group=>group.sessions.includes(sessionDate));
  if(matches.length!==1)throw new Error(`SOURCE_GROUP_IDENTITY_MISMATCH:${sessionDate}`);
  return matches[0];
}
function partitionFor(sessionDate){
  const matches=Object.entries(allocation.partitions).filter(([,sessions])=>sessions.includes(sessionDate));
  if(matches.length!==1||!matches[0][0].startsWith('DEVELOPMENT_'))throw new Error(`SEALED_OR_AMBIGUOUS_PARTITION:${sessionDate}`);
  return matches[0][0];
}
function selectorOutcome(semantics,onePct){
  return Object.freeze({opportunity1:onePct.highOpportunity1,opportunity2:semantics.highOpportunity2,opportunity3:semantics.highOpportunity3,
    opportunity5:semantics.highOpportunity5,mfePct:semantics.sessionMfePct,maePct:semantics.sessionMaePct,futureBarCount:semantics.futureBarCount,
    futureAuctionCount:semantics.futureAuctionCount});
}
function flattenEvent(event){
  const outcome=event.selectorOutcome??{};
  return {
    selectorEventId:event.selectorEventId,sessionDate:event.sessionDate,symbol:event.symbol,decisionTimestamp:event.decisionTimestamp,
    decisionTimeJst:event.decisionTimeJst,decisionPrice:event.decisionPrice,ridgeRank:event.ridgeRank,ridgeScore:event.ridgeScore,
    selectorFeatureTimestamp:event.selectorFeatureTimestamp,selectorFeatureAvailableAt:event.selectorFeatureAvailableAt,
    segment:event.segment,liquidityBucket:event.liquidityBucket,sourceGroup:event.sourceGroup,partition:event.partition,
    selectorOpportunity1:outcome.opportunity1,selectorOpportunity2:outcome.opportunity2,selectorOpportunity3:outcome.opportunity3,
    selectorOpportunity5:outcome.opportunity5,selectorMfePct:outcome.mfePct,selectorMaePct:outcome.maePct,
    selectorFutureBarCount:outcome.futureBarCount,selectorFutureAuctionCount:outcome.futureAuctionCount,
    symbolSessionId:event.symbolSessionId,selectionIndex:event.selectionIndex,isFirstSelection:event.isFirstSelection,
    firstSelectionTimestamp:event.firstSelectionTimestamp,stateBeforeDecision:event.stateBeforeDecision,directStatus:event.directStatus,
    directReason:event.directReason,longProbability:event.longProbability,entryFeatureTimestamp:event.entryFeatureTimestamp,
    entryFeatureAvailableAt:event.entryFeatureAvailableAt,entryReferencePriceAtDecision:event.entryReferencePriceAtDecision,
    finalOpportunityStatus:event.finalOpportunityStatus,firstPassTimestamp:event.firstPassTimestamp,firstPassPrice:event.firstPassPrice,
    firstPassProbability:event.firstPassProbability,entryLatencyMinutes:event.entryLatencyMinutes,entryLatencyBucket:event.entryLatencyBucket,
    entryAfterThisSelectorEvent:event.entryAfterThisSelectorEvent,enteredBeforeThisSelectorEvent:event.enteredBeforeThisSelectorEvent,
    consumedReturnBps:event.consumedReturnBps,entryOpportunity1:event.entryOpportunity1,entryOpportunity2:event.entryOpportunity2,
    entryOpportunity3:event.entryOpportunity3,entryOpportunity5:event.entryOpportunity5,entryMfePct:event.entryMfePct,
    entryMaePct:event.entryMaePct,entryOutcomeEvaluable:event.entryOutcomeEvaluable,direction:'LONG',shortScoreEvaluated:false,
  };
}

for(const sessionDate of frozenSessions){
  const group=sourceFor(sessionDate),partition=partitionFor(sessionDate),dir=path.join(base,sessionDate);
  const manifest=read(path.join(dir,group.manifest)),pages=read(path.join(dir,'minute-pages.json'));
  if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==group.sessionHash||pages.length!==manifest.pageCount)throw new Error(`MINUTE_MANIFEST_IDENTITY_MISMATCH:${sessionDate}`);
  if(pages.some(page=>sha(page.responseText)!==page.responseSha256))throw new Error(`MINUTE_PAGE_HASH_MISMATCH:${sessionDate}`);
  const raw=pages.flatMap(page=>JSON.parse(page.responseText).data??[]);
  if(raw.length!==manifest.rowCount)throw new Error(`MINUTE_ROW_COUNT_MISMATCH:${sessionDate}`);
  if(!l0s.has(partition))l0s.set(partition,loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}));
  const dailyRows=l0s.get(partition).rows.filter(row=>row.sessionDate===sessionDate);
  const intraday=normalizeAndAggregateMinuteRows(raw),provenance=normalizeMinuteProvenance(raw);
  const barsMap=bySymbol(intraday.bars),auctionMap=bySymbol(intraday.terminalAuctions),dailyMap=new Map(dailyRows.map(row=>[symkey(row.sessionDate,row.symbol),row]));
  const masterPages=read(path.join(dir,'master-pages.json')),sectorBySymbol={};
  for(const page of masterPages){
    if(sha(page.responseText)!==page.responseSha256)throw new Error(`MASTER_PAGE_HASH_MISMATCH:${sessionDate}`);
    for(const row of JSON.parse(page.responseText).data??[]){const symbol=codeOf(row);if(symbol)sectorBySymbol[symkey(sessionDate,symbol)]=sectorOf(row);}
  }
  const built=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
  const targets=buildFixedHorizonTargets({featureRows:built.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:built.evaluatorOnlyLabels});
  const targetMap=new Map(targets.map(row=>[rowKey(row),row])),labelMap=new Map(built.evaluatorOnlyLabels.map(row=>[rowKey(row),row]));
  const candidateGroups=new Map();
  for(const feature of built.featureRows){
    if(feature.latestAvailableAtJst>feature.decisionAtJst)throw new Error('FUTURE_SELECTOR_FEATURE_PROVENANCE');
    const key=symkey(sessionDate,feature.symbol),bars=barsMap.get(key)??[],auctions=auctionMap.get(key)??[];
    const semantics=measureCorrectedRow({feature,target:targetMap.get(rowKey(feature)),label:labelMap.get(rowKey(feature)),bars,
      minutes:provenance.get(key)??[],terminalAuctions:auctions,daily:dailyMap.get(key)});
    if(semantics.decisionPriceValid!==1||!(semantics.referenceAgeMin>=0&&semantics.referenceAgeMin<=5))continue;
    const onePct=measureOnePct({bars,auctions,reference:semantics.decisionPrice,decisionTimeJst:feature.decisionAtJst});
    const candidate={sessionDate,symbol:String(feature.symbol),decisionTimestamp:feature.decisionAtJst,decisionTimeJst:feature.decisionTimeJst,
      decisionPrice:Number(semantics.decisionPrice),ridgeScore:Number(scoreL2Candidate(feature,artifact)),selectorFeatureTimestamp:feature.decisionAtJst,
      selectorFeatureAvailableAt:feature.latestAvailableAtJst,segment:feature.segment,liquidityBucket:feature.liquidityBucket,sourceGroup:group.name,
      partition,selectorOutcome:selectorOutcome(semantics,onePct)};
    if(!candidateGroups.has(candidate.decisionTimestamp))candidateGroups.set(candidate.decisionTimestamp,[]);
    candidateGroups.get(candidate.decisionTimestamp).push(candidate);
  }
  const selections=[];
  for(const decisionTimeJst of decisionSchedule){
    const timestamp=`${sessionDate}T${decisionTimeJst}:00+09:00`,eligible=candidateGroups.get(timestamp)??[];
    const top=eligible.sort((left,right)=>right.ridgeScore-left.ridgeScore||left.symbol.localeCompare(right.symbol)).slice(0,5);
    if(top.length!==5)throw new Error(`FROZEN_TOP5_UNAVAILABLE:${sessionDate}:${decisionTimeJst}:${top.length}`);
    selections.push(...top.map((row,index)=>({...row,ridgeRank:index+1,selectorEventId:`${sessionDate}|${timestamp}|${row.symbol}`})));
  }
  const selectedSymbols=new Set(selections.map(row=>row.symbol)),entryBars=new Map(),entryAuctions=new Map();
  for(const symbol of selectedSymbols){entryBars.set(symbol,normalizeEntryBars(barsMap.get(symkey(sessionDate,symbol))??[]));entryAuctions.set(symbol,auctionMap.get(symkey(sessionDate,symbol))??[]);}
  const transfer=evaluateLongOnlyTransferSession({sessionDate,selections,barsBySymbol:entryBars,auctionsBySymbol:entryAuctions,model});
  allEvents.push(...transfer.events.map(flattenEvent));allOpportunities.push(...transfer.opportunities);allTicks.push(...transfer.ticks);
  const tickReasonCounts={};
  for(const tick of transfer.ticks){const key=`${tick.status}:${tick.reason}`;tickReasonCounts[key]=(tickReasonCounts[key]??0)+1;}
  const scoredProbabilities=transfer.ticks.map(row=>row.probability).filter(Number.isFinite).sort((a,b)=>a-b);
  sessionAudits.push({sessionDate,partition,sourceGroup:group.name,rawMinuteRows:raw.length,eligibleFeatureRows:[...candidateGroups.values()].reduce((sum,rows)=>sum+rows.length,0),
    decisionTimestamps:candidateGroups.size,selectedEvents:selections.length,uniqueSelectedSymbols:selectedSymbols.size,entryEvaluationTicks:transfer.ticks.length,
    directStatus:Object.fromEntries(['PASS','WAIT','REJECT','BLOCKED','UNAVAILABLE'].map(status=>[status,transfer.events.filter(event=>event.directStatus===status).length])),
    tickReasonCounts,scoredTicks:scoredProbabilities.length,
    scoredProbabilityMin:scoredProbabilities.at(0)??null,scoredProbabilityMax:scoredProbabilities.at(-1)??null,
    firstEntryOpportunities:transfer.opportunities.length,firstPass:transfer.opportunities.filter(row=>row.finalStatus==='PASS').length});
  console.log(JSON.stringify({status:'ENTRY_TRANSFER_SESSION_COMPLETE',...sessionAudits.at(-1)}));
}

allEvents.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.decisionTimestamp.localeCompare(b.decisionTimestamp)||a.ridgeRank-b.ridgeRank||a.symbol.localeCompare(b.symbol));
allOpportunities.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.firstSelectionTimestamp.localeCompare(b.firstSelectionTimestamp)||a.stateSymbol.localeCompare(b.stateSymbol));
allTicks.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.evaluationTimestamp.localeCompare(b.evaluationTimestamp)||a.symbol.localeCompare(b.symbol));
const decisionCount=new Set(allEvents.map(row=>`${row.sessionDate}|${row.decisionTimestamp}`)).size;
if(allEvents.length!==3800||decisionCount!==760||new Set(allEvents.map(row=>row.sessionDate)).size!==76)throw new Error('FINAL_FROZEN_SELECTOR_COUNT_MISMATCH');
if(new Set(allEvents.map(row=>row.selectorEventId)).size!==allEvents.length)throw new Error('DUPLICATE_SELECTOR_EVENT_ID');
if(allEvents.some(row=>row.direction!=='LONG'||row.shortScoreEvaluated!==false)||allTicks.some(row=>row.direction!=='LONG'||row.shortScoreEvaluated!==false))throw new Error('ABSOLUTE_LONG_ONLY_CONTRACT_VIOLATION');
if(new Set(allTicks.map(row=>row.tickId)).size!==allTicks.length)throw new Error('DUPLICATE_ENTRY_EVALUATION_TICK');

fs.mkdirSync(outputDir,{recursive:true,mode:0o700});
const eventsPath=path.join(outputDir,'selector-current-entry-events.ndjson'),opportunitiesPath=path.join(outputDir,'first-entry-opportunities.json'),
  ticksPath=path.join(outputDir,'entry-evaluation-ticks.ndjson');
fs.writeFileSync(eventsPath,allEvents.map(row=>JSON.stringify(row)).join('\n')+'\n',{flag:'wx',mode:0o600});
fs.writeFileSync(opportunitiesPath,JSON.stringify(allOpportunities,null,2)+'\n',{flag:'wx',mode:0o600});
fs.writeFileSync(ticksPath,allTicks.map(row=>JSON.stringify(row)).join('\n')+'\n',{flag:'wx',mode:0o600});
const manifest={schemaVersion:1,status:'FROZEN_SELECTOR_CURRENT_ENTRY_TRANSFER_INPUT_READY',contractId:transferContract.contractId,
  source:{frozenSelectorFreezeCommit:CURRENT_ENTRY_TRANSFER_ASSETS.selectorFreezeCommit,frozenSelectorArtifactSha256:CURRENT_ENTRY_TRANSFER_ASSETS.selectorArtifactSha256,
    currentEntryModelSha256:CURRENT_ENTRY_TRANSFER_ASSETS.modelSha256,currentEntryFeatureContractSha256:CURRENT_ENTRY_TRANSFER_ASSETS.featureContractSha256,
    currentEntryFeatureImplementationSha256:CURRENT_ENTRY_TRANSFER_ASSETS.featureImplementationSha256},
  counts:{sessions:76,decisionTimestamps:decisionCount,selectionEvents:allEvents.length,uniqueSymbols:new Set(allEvents.map(row=>row.symbol)).size,
    uniqueSymbolSessions:new Set(allEvents.map(row=>row.symbolSessionId)).size,firstEntryOpportunities:allOpportunities.length,
    entryEvaluationTicks:allTicks.length,scoredEntryTicks:allTicks.filter(row=>Number.isFinite(row.probability)).length},
  files:[{path:path.basename(eventsPath),sha256:sha(fs.readFileSync(eventsPath)),rows:allEvents.length},
    {path:path.basename(opportunitiesPath),sha256:sha(fs.readFileSync(opportunitiesPath)),rows:allOpportunities.length},
    {path:path.basename(ticksPath),sha256:sha(fs.readFileSync(ticksPath)),rows:allTicks.length}],
  sessionAudits,methodology:{selectorRecomputedFromFrozenSavedWeights:true,selectorFitCalls:0,currentEntryFitCalls:0,currentEntryLongDirectionOnly:true,
    shortScoreEvaluated:false,validationOpened:false,oosOpened:false,providerRequests:0,rawCachePersisted:false,
    augmentedTickAndFeatureDiagnosticsDecisionNeutral:true},safety:CURRENT_ENTRY_TRANSFER_SAFETY};
fs.writeFileSync(path.join(outputDir,'input-manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx',mode:0o600});
console.log(JSON.stringify({status:manifest.status,...manifest.counts,eventsSha256:manifest.files[0].sha256,opportunitiesSha256:manifest.files[1].sha256}));
