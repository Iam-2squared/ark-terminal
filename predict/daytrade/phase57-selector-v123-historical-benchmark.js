import {createHash} from 'node:crypto';
import {buildIntradayDynamicUniverseTimeline} from './phase57-p25-intraday-dynamic-universe.js';
import {buildIntradayDynamicUniverseTimelineV2} from './phase57-p25-intraday-dynamic-universe-v2.js';
import {
  PHASE57_SELECTOR_V3_FREEZE,
  PHASE57_SELECTOR_V3_SAFETY,
  scorePhase57SelectorV3CrossSection,
} from './phase57-selector-v3.js';
import {buildPhase57SelectorNativeTargets} from './phase57-selector-v3-targets.js';

const EVIDENCE_LABELS=new Set(PHASE57_SELECTOR_V3_FREEZE.benchmark.historicalReplayLabels);
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const round6=value=>Number(Number(value).toFixed(6));
const mean=values=>values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;

function median(values){
  const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!xs.length)return null;
  const middle=Math.floor(xs.length/2);
  return xs.length%2?xs[middle]:(xs[middle-1]+xs[middle])/2;
}

function timestampMs(value,label){
  const parsed=Date.parse(String(value??''));
  if(!Number.isFinite(parsed))throw new TypeError(`${label} must be a valid timestamp`);
  return parsed;
}

function symbolOf(value){return String(value??'').trim().toUpperCase();}
function sectorOf(value){return String(value??'').trim()||'UNKNOWN';}

function canonicalDigest(value){
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function assertSafety(safety,label){
  for(const key of Object.keys(PHASE57_SELECTOR_V3_SAFETY)){
    if(PHASE57_SELECTOR_V3_SAFETY[key]===false&&safety?.[key]!==false)throw new Error(`${label} safety ${key} must remain false`);
  }
}

export function validatePhase57SelectorHistoricalDataset(dataset){
  if(!dataset||typeof dataset!=='object')throw new TypeError('dataset must be an object');
  const manifest=dataset.manifest;
  if(!manifest||typeof manifest!=='object')throw new TypeError('dataset.manifest is required');
  if(!EVIDENCE_LABELS.has(manifest.evidenceClassification))throw new Error('manifest evidenceClassification is not preregistered');
  if(manifest.claimsExactTradingViewReplay===true&&manifest.evidenceClassification!=='EXACT_HISTORICAL_REPLAY'){
    throw new Error('reconstruction cannot claim exact TradingView replay');
  }
  if(manifest.universeStatus==='SURVIVORSHIP_LIMITED'&&manifest.evidenceClassification!=='SURVIVORSHIP_LIMITED_RECONSTRUCTION'){
    throw new Error('survivorship-limited input must use SURVIVORSHIP_LIMITED_RECONSTRUCTION');
  }
  if(!['POINT_IN_TIME','SURVIVORSHIP_LIMITED'].includes(manifest.universeStatus)){
    throw new Error('manifest universeStatus must be POINT_IN_TIME or SURVIVORSHIP_LIMITED');
  }
  if(Number(manifest.intervalMinutes)!==PHASE57_SELECTOR_V3_FREEZE.causality.intervalMinutes)throw new Error('dataset interval must be frozen at 5m');
  if(!Array.isArray(dataset.sessions))throw new TypeError('dataset.sessions must be an array');
  if(dataset.sessions.length<PHASE57_SELECTOR_V3_FREEZE.split.minimumTradingSessions){
    throw new Error(`dataset requires at least ${PHASE57_SELECTOR_V3_FREEZE.split.minimumTradingSessions} trading sessions`);
  }
  const dates=new Set();
  const globalSymbols=Array.isArray(dataset.symbols)?dataset.symbols:null;
  const globalSymbolSet=new Set();
  if(globalSymbols){
    if(!globalSymbols.length)throw new Error('dataset.symbols cannot be empty');
    for(const item of globalSymbols){
      const symbol=symbolOf(item?.symbol);
      if(!symbol||globalSymbolSet.has(symbol))throw new Error(`dataset.symbols contains missing/duplicate symbol ${symbol}`);
      globalSymbolSet.add(symbol);
      if(!Array.isArray(item.bars)||!item.bars.length)throw new Error(`dataset.symbols ${symbol} requires bars[]`);
    }
  }
  let priorDate='';
  for(const [sessionIndex,session] of dataset.sessions.entries()){
    const date=String(session?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw new Error(`sessions[${sessionIndex}] requires YYYY-MM-DD sessionDate`);
    if(dates.has(date))throw new Error(`duplicate sessionDate ${date}`);
    if(priorDate&&date<=priorDate)throw new Error('sessions must be strictly chronological');
    priorDate=date;dates.add(date);
    if(!Array.isArray(session.decisionCutoffs)||!session.decisionCutoffs.length)throw new Error(`${date} requires decisionCutoffs[]`);
    let priorCutoff=-Infinity;
    for(const cutoff of session.decisionCutoffs){
      const value=timestampMs(cutoff,`${date} decisionCutoff`);
      if(value<=priorCutoff)throw new Error(`${date} decisionCutoffs must be strictly chronological`);
      priorCutoff=value;
    }
    if(!globalSymbols&&(!Array.isArray(session.symbols)||!session.symbols.length))throw new Error(`${date} requires symbols[] or top-level dataset.symbols[]`);
    if(globalSymbols&&session.memberSymbols!==undefined&&!Array.isArray(session.memberSymbols))throw new Error(`${date} memberSymbols must be an array`);
    if(globalSymbols&&Array.isArray(session.memberSymbols)){
      for(const member of session.memberSymbols){
        if(!globalSymbolSet.has(symbolOf(member)))throw new Error(`${date} unknown member symbol ${member}`);
      }
    }
    const symbols=new Set();
    for(const item of session.symbols??[]){
      const symbol=symbolOf(item?.symbol);
      if(!symbol||symbols.has(symbol))throw new Error(`${date} contains missing/duplicate symbol ${symbol}`);
      symbols.add(symbol);
      if(!Array.isArray(item.bars)||!item.bars.length)throw new Error(`${date} ${symbol} requires bars[]`);
    }
  }
  assertSafety(manifest.safety,'dataset manifest');
  return Object.freeze({
    status:'SELECTOR_HISTORICAL_DATASET_VALID',
    datasetId:String(manifest.datasetId??'UNNAMED_DATASET'),
    sessionCount:dataset.sessions.length,
    evidenceClassification:manifest.evidenceClassification,
    universeStatus:manifest.universeStatus,
    datasetDigest:canonicalDigest(dataset),
  });
}

export function splitPhase57SelectorHistoricalSessions(sessions){
  if(!Array.isArray(sessions))throw new TypeError('sessions must be an array');
  const cfg=PHASE57_SELECTOR_V3_FREEZE.split;
  if(sessions.length<cfg.minimumTradingSessions)throw new Error(`at least ${cfg.minimumTradingSessions} sessions required`);
  const developmentBoundary=Math.floor(sessions.length*cfg.developmentFraction);
  const validationBoundary=developmentBoundary+Math.floor(sessions.length*cfg.validationFraction);
  const purge=PHASE57_SELECTOR_V3_FREEZE.causality.purgeSessionsAtEachBoundary;
  if(developmentBoundary-purge<1||validationBoundary-developmentBoundary-purge<1||sessions.length-validationBoundary<1){
    throw new Error('session split leaves an empty fold');
  }
  const development=sessions.slice(0,developmentBoundary-purge);
  const purgeDevelopmentValidation=sessions.slice(developmentBoundary-purge,developmentBoundary);
  const validation=sessions.slice(developmentBoundary,validationBoundary-purge);
  const purgeValidationOos=sessions.slice(validationBoundary-purge,validationBoundary);
  const untouchedOos=sessions.slice(validationBoundary);
  const label=list=>list.map(session=>session.sessionDate);
  return Object.freeze({
    development:Object.freeze(label(development)),
    purgeDevelopmentValidation:Object.freeze(label(purgeDevelopmentValidation)),
    validation:Object.freeze(label(validation)),
    purgeValidationOos:Object.freeze(label(purgeValidationOos)),
    untouchedOos:Object.freeze(label(untouchedOos)),
    atomicUnit:cfg.atomicFoldUnit??PHASE57_SELECTOR_V3_FREEZE.causality.atomicFoldUnit,
    outerGrouping:PHASE57_SELECTOR_V3_FREEZE.causality.outerGrouping,
  });
}

function normalizeDatasetBar(bar,manifest){
  if(!bar||typeof bar!=='object')throw new TypeError('historical bar must be an object');
  const timestamp=String(bar.timestamp??'');
  const timestampValue=timestampMs(timestamp,'bar.timestamp');
  let availableAt=bar.availableAt==null?null:String(bar.availableAt);
  if(!availableAt){
    if(manifest.barTimestampMeaning!=='BAR_OPEN')throw new Error('bar.availableAt missing without BAR_OPEN manifest declaration');
    availableAt=new Date(timestampValue+Number(manifest.intervalMinutes)*60_000).toISOString();
  }
  timestampMs(availableAt,'bar.availableAt');
  return {...bar,timestamp,availableAt};
}

function normalizedSymbols(items,manifest){
  return items.map(item=>({
    ...item,
    symbol:symbolOf(item.symbol),
    sector:sectorOf(item.sector),
    bars:item.bars.map(bar=>normalizeDatasetBar(bar,manifest)),
  }));
}

function barsClosedBy(symbol,cutoffMs){
  return symbol.bars
    .filter(bar=>timestampMs(bar.availableAt,'bar.availableAt')<=cutoffMs)
    .sort((a,b)=>timestampMs(a.availableAt,'bar.availableAt')-timestampMs(b.availableAt,'bar.availableAt'));
}

function derivePreviousClose(symbol,sessionDate){
  if(finite(symbol.previousClose)&&Number(symbol.previousClose)>0)return Number(symbol.previousClose);
  const prior=symbol.bars
    .filter(bar=>String(bar.sessionDate??'')<sessionDate&&finite(bar.close)&&Number(bar.close)>0)
    .sort((a,b)=>timestampMs(a.availableAt,'bar.availableAt')-timestampMs(b.availableAt,'bar.availableAt'));
  return prior.length?Number(prior.at(-1).close):null;
}

function sessionSymbolView(symbol,sessionDate){
  const prior=symbol.bars.filter(bar=>String(bar.sessionDate??'')<sessionDate).slice(-13);
  const current=symbol.bars.filter(bar=>bar.sessionDate===sessionDate);
  if(!prior.length||!current.length)return null;
  return {
    ...symbol,
    previousClose:finite(symbol.previousClose)&&Number(symbol.previousClose)>0
      ?Number(symbol.previousClose)
      :Number(prior.at(-1).close),
    bars:[...prior,...current],
  };
}

function reconstructSnapshotEntry(symbol,sessionDate,featureCutoff){
  const cutoffMs=timestampMs(featureCutoff,'featureCutoff');
  const closed=barsClosedBy(symbol,cutoffMs);
  const currentSession=closed.filter(bar=>bar.sessionDate===sessionDate);
  if(!currentSession.length)return null;
  const latest=currentSession.at(-1);
  const currentPrice=Number(latest.close);
  const volume=currentSession.reduce((sum,bar)=>sum+(finite(bar.volume)?Number(bar.volume):0),0);
  const previousClose=derivePreviousClose(symbol,sessionDate);
  if(!(currentPrice>0)||!(volume>0)||!(previousClose>0))return null;
  return {
    symbol:symbol.symbol,sector:symbol.sector,market:symbol.market??null,status:'analyzed',
    scannedAt:featureCutoff,currentPrice,volume,
    dailyChangePercent:(currentPrice/previousClose-1)*100,
  };
}

function pointBySource(timeline){
  return new Map(timeline.points.map(point=>[point.sourceAsOf,point]));
}

function jstTimeOfDay(timestamp){
  const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(timestamp));
  const values=Object.fromEntries(parts.map(part=>[part.type,part.value]));
  return `${values.hour}:${values.minute}`;
}

function priceBand(price){
  if(price<100)return 'LT_100';
  if(price<500)return '100_TO_499';
  if(price<2000)return '500_TO_1999';
  return 'GE_2000';
}

function liquidityBand(turnover){
  if(turnover<10_000_000)return 'LT_10M';
  if(turnover<100_000_000)return '10M_TO_99M';
  if(turnover<1_000_000_000)return '100M_TO_999M';
  return 'GE_1B';
}

function marketRegime(snapshot){
  const moves=snapshot.map(row=>Number(row.dailyChangePercent)).filter(Number.isFinite);
  const center=median(moves)??0;
  if(center>0.1)return 'UP';
  if(center<-0.1)return 'DOWN';
  return 'FLAT';
}

function rankDecile(rank,total){
  if(!Number.isFinite(rank)||!Number.isFinite(total)||total<1)return 'NOT_RANKED';
  return `D${Math.min(10,Math.max(1,Math.ceil(rank/total*10)))}`;
}

function recordForSymbol({
  session,featureCutoff,symbol,snapshotEntry,v1Point,v2Point,v3Result,selectionMaps,regime,
}){
  const v1Index=selectionMaps.v1.get(symbol.symbol)??-1;
  const v2Index=selectionMaps.v2.get(symbol.symbol)??-1;
  const v1Row=v1Index>=0?v1Point.rawUniverse[v1Index]:null;
  const v2Row=v2Index>=0?v2Point.rawUniverse[v2Index]:null;
  const v3Index=selectionMaps.v3.get(symbol.symbol)??-1;
  const v3Row=v3Index>=0?v3Result.ranked[v3Index]:null;
  const closed=barsClosedBy(symbol,timestampMs(featureCutoff,'featureCutoff'));
  const current=closed.filter(bar=>bar.sessionDate===session.sessionDate).at(-1);
  if(!current)return null;
  const currentSession=closed.filter(bar=>bar.sessionDate===session.sessionDate);
  const sessionOpen=Number(currentSession[0].open);
  const anchorPrice=Number(current.close);
  const targets=buildPhase57SelectorNativeTargets({
    featureCutoff,anchorPrice,sessionDate:session.sessionDate,futureBars:symbol.bars,
  });
  const primary=targets.horizons[PHASE57_SELECTOR_V3_FREEZE.targets.primaryHorizonBars];
  const horizonTargets=Object.fromEntries(PHASE57_SELECTOR_V3_FREEZE.targets.horizonBars.map(horizon=>{
    const value=targets.horizons[horizon];
    return [String(horizon),{
      status:value.status,
      upExcursion:value.upExcursion,
      downExcursion:value.downExcursion,
      twoSidedOpportunity:value.twoSidedOpportunity,
      costAdjustedTwoSidedUtility:value.costAdjustedTwoSidedUtility,
      barriers:value.barriers===null?null:Object.fromEntries(Object.entries(value.barriers).map(([bps,barrier])=>[bps,barrier.status])),
    }];
  }));
  const turnoverYen=anchorPrice*Number(snapshotEntry.volume);
  return Object.freeze({
    sessionDate:session.sessionDate,featureCutoff,timeOfDay:jstTimeOfDay(featureCutoff),
    symbol:symbol.symbol,sector:symbol.sector,market:symbol.market??null,marketRegime:regime,
    currentPrice:anchorPrice,turnoverYen,priceBand:priceBand(anchorPrice),liquidityBand:liquidityBand(turnoverYen),
    preSelectionMove:Math.abs(anchorPrice/sessionOpen-1),
    v1Selected:v1Index>=0,v1Rank:v1Index>=0?v1Index+1:null,v1Score:v1Row?.opportunityScore??null,
    v2Selected:v2Index>=0,v2Rank:v2Index>=0?v2Index+1:null,v2Score:v2Row?.v2Score??null,
    v3Eligible:v3Index>=0,v3Rank:v3Index>=0?v3Index+1:null,v3Score:v3Row?.utilityScore??null,
    v3StructuralTradability:v3Row?.structuralTradability??null,
    v3SectorContextStatus:v3Row?.components?.sectorContextStatus??null,
    v1RankDecile:rankDecile(v1Index>=0?v1Index+1:null,v1Point?.rawUniverse?.length??0),
    v2RankDecile:rankDecile(v2Index>=0?v2Index+1:null,v2Point?.rawUniverse?.length??0),
    v3RankDecile:rankDecile(v3Index>=0?v3Index+1:null,v3Result.ranked.length),
    targetStatus:primary.status,
    primaryUpExcursion:primary.upExcursion,
    primaryDownExcursion:primary.downExcursion,
    primaryTwoSidedOpportunity:primary.twoSidedOpportunity,
    primaryCostAdjustedUtility:primary.costAdjustedTwoSidedUtility,
    horizonTargets,
  });
}

export function replayPhase57SelectorHistoricalDataset(dataset){
  const validation=validatePhase57SelectorHistoricalDataset(dataset);
  const records=[];
  const pointAudits=[];
  const globalSymbols=Array.isArray(dataset.symbols)?normalizedSymbols(dataset.symbols,dataset.manifest):null;
  const globalBySymbol=globalSymbols?new Map(globalSymbols.map(item=>[item.symbol,item])):null;
  for(const session of dataset.sessions){
    const sourceSymbols=globalSymbols
      ?(Array.isArray(session.memberSymbols)
        ?session.memberSymbols.map(symbol=>globalBySymbol.get(symbolOf(symbol))).filter(Boolean)
        :globalSymbols)
      :normalizedSymbols(session.symbols,dataset.manifest);
    const symbols=sourceSymbols.map(symbol=>sessionSymbolView(symbol,session.sessionDate)).filter(Boolean);
    const snapshots=session.decisionCutoffs.map(featureCutoff=>({
      asOf:featureCutoff,
      entries:symbols.map(symbol=>reconstructSnapshotEntry(symbol,session.sessionDate,featureCutoff)).filter(Boolean),
    }));
    const v1=buildIntradayDynamicUniverseTimeline({snapshots,policy:{finalUniverseSize:50}});
    const v2=buildIntradayDynamicUniverseTimelineV2({snapshots,priorSelections:[]});
    assertSafety(v1.safety,'V1');
    assertSafety(v2.safety,'V2');
    const v1BySource=pointBySource(v1);
    const v2BySource=pointBySource(v2);
    for(const snapshot of snapshots){
      const v3=scorePhase57SelectorV3CrossSection({
        featureCutoff:snapshot.asOf,
        entries:symbols.map(symbol=>({symbol:symbol.symbol,sector:symbol.sector,market:symbol.market,bars:symbol.bars})),
      });
      const v1Point=v1BySource.get(snapshot.asOf);
      const v2Point=v2BySource.get(snapshot.asOf);
      const selectionMaps={
        v1:new Map((v1Point?.rawUniverse??[]).map((row,index)=>[row.symbol,index])),
        v2:new Map((v2Point?.rawUniverse??[]).map((row,index)=>[row.symbol,index])),
        v3:new Map(v3.ranked.map((row,index)=>[row.symbol,index])),
      };
      const regime=marketRegime(snapshot.entries);
      const bySymbol=new Map(symbols.map(symbol=>[symbol.symbol,symbol]));
      for(const snapshotEntry of snapshot.entries){
        const symbol=bySymbol.get(snapshotEntry.symbol);
        const record=recordForSymbol({session,featureCutoff:snapshot.asOf,symbol,snapshotEntry,v1Point,v2Point,v3Result:v3,selectionMaps,regime});
        if(record)records.push(record);
      }
      pointAudits.push(Object.freeze({
        sessionDate:session.sessionDate,featureCutoff:snapshot.asOf,inputSymbols:snapshot.entries.length,
        v1Selected:v1Point?.rawUniverse?.length??0,v2Selected:v2Point?.rawUniverse?.length??0,
        v3Eligible:v3.ranked.length,v3Rejected:v3.rejectedCount,
      }));
    }
  }
  return Object.freeze({
    phase:'57.selector-v1-v2-v3.historical-replay',
    status:'SELECTOR_V1_V2_V3_PAIRED_REPLAY_READY',
    validation,recordCount:records.length,records:Object.freeze(records),pointAudits:Object.freeze(pointAudits),
    methodology:Object.freeze({
      sameReconstructedMarketState:true,currentV1Frozen:true,currentV2Frozen:true,v3Frozen:true,
      v1V2RealtimeExactReplayClaimed:dataset.manifest.evidenceClassification==='EXACT_HISTORICAL_REPLAY',
      futureBarsUsedOnlyForTargets:true,pairedBySymbolTimestamp:true,
    }),
    safety:PHASE57_SELECTOR_V3_SAFETY,
  });
}

function applyV3Threshold(records,threshold){
  const selected=new Set();
  if(threshold===null)return selected;
  const groups=new Map();
  records.forEach((row,index)=>{
    if(!groups.has(row.featureCutoff))groups.set(row.featureCutoff,[]);
    groups.get(row.featureCutoff).push({row,index});
  });
  for(const group of groups.values()){
    const ranked=group
      .filter(item=>finite(item.row.v3Score)&&finite(item.row.v3StructuralTradability))
      .sort((a,b)=>a.row.v3Rank-b.row.v3Rank||a.row.symbol.localeCompare(b.row.symbol));
    const sectors=new Map();
    let count=0;
    for(const item of ranked){
      if(count>=PHASE57_SELECTOR_V3_FREEZE.selection.maximumSelectedPerTimestamp)break;
      if(item.row.v3Score<threshold||item.row.v3StructuralTradability<PHASE57_SELECTOR_V3_FREEZE.score.minimumStructuralTradability)continue;
      const sector=item.row.sector;
      const sectorCount=sectors.get(sector)??0;
      if(sectorCount>=PHASE57_SELECTOR_V3_FREEZE.selection.maximumSelectedPerSector)continue;
      selected.add(item.index);count+=1;sectors.set(sector,sectorCount+1);
    }
  }
  return selected;
}

function downsideDeviation(values){
  if(!values.length)return null;
  return Math.sqrt(values.reduce((sum,value)=>sum+Math.min(0,value)**2,0)/values.length);
}

export function calibratePhase57SelectorV3Threshold(validationRecords){
  if(!Array.isArray(validationRecords))throw new TypeError('validationRecords must be an array');
  const candidates=[];
  for(const threshold of PHASE57_SELECTOR_V3_FREEZE.selection.thresholdCandidates){
    const selectedIndices=applyV3Threshold(validationRecords,threshold);
    const selected=[...selectedIndices].map(index=>validationRecords[index]).filter(row=>finite(row.primaryCostAdjustedUtility));
    const timestamps=new Set(selected.map(row=>row.featureCutoff));
    const values=selected.map(row=>Number(row.primaryCostAdjustedUtility));
    const eligible=selected.length>=PHASE57_SELECTOR_V3_FREEZE.selection.minimumValidationSelectedRows&&
      timestamps.size>=PHASE57_SELECTOR_V3_FREEZE.selection.minimumValidationDecisionTimestamps;
    const average=mean(values);
    const downside=downsideDeviation(values);
    const objective=eligible?(average-0.25*downside)*10000:null;
    candidates.push(Object.freeze({
      threshold,eligible,selectedRows:selected.length,decisionTimestamps:timestamps.size,
      meanCostAdjustedUtilityBps:average===null?null:round6(average*10000),
      downsideDeviationBps:downside===null?null:round6(downside*10000),
      objectiveBps:objective===null?null:round6(objective),
    }));
  }
  const winner=candidates.filter(candidate=>candidate.eligible).sort((a,b)=>
    b.objectiveBps-a.objectiveBps||b.threshold-a.threshold||a.selectedRows-b.selectedRows
  )[0]??null;
  return Object.freeze({
    status:winner?'SELECTOR_V3_VALIDATION_THRESHOLD_FROZEN':'SELECTOR_V3_ABSTAIN_ALL_NO_ELIGIBLE_THRESHOLD',
    selectedThreshold:winner?.threshold??null,
    candidates:Object.freeze(candidates),
    validationRows:validationRecords.length,
    outerOosUsed:false,
  });
}

function selectedPredicate(selector,v3Selected){
  if(selector==='V1')return (row,index)=>row.v1Selected;
  if(selector==='V2')return (row,index)=>row.v2Selected;
  return (row,index)=>v3Selected.has(index);
}

function simpleGroupSummary(rows,predicate){
  const selected=rows.filter(predicate).filter(row=>finite(row.primaryCostAdjustedUtility));
  return {
    selectedTargetReady:selected.length,
    meanCostAdjustedUtilityBps:selected.length?round6(mean(selected.map(row=>row.primaryCostAdjustedUtility))*10000):null,
    meanTwoSidedOpportunityBps:selected.length?round6(mean(selected.map(row=>row.primaryTwoSidedOpportunity))*10000):null,
  };
}

function groupedSlices(rows,predicate,keyOf){
  const groups=new Map();
  rows.forEach((row,index)=>{
    if(!predicate(row,index))return;
    const key=String(keyOf(row)??'UNKNOWN');
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(row);
  });
  return Object.fromEntries([...groups.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([key,values])=>[
    key,simpleGroupSummary(values,()=>true),
  ]));
}

function horizonSummary(rows,predicate,horizon){
  const selected=rows.filter(predicate);
  const ready=selected.filter(row=>row.horizonTargets?.[String(horizon)]?.status==='TARGET_READY');
  const values=ready.map(row=>row.horizonTargets[String(horizon)]);
  const barriers=Object.fromEntries(PHASE57_SELECTOR_V3_FREEZE.targets.barrierBps.map(bps=>{
    const statuses=values.map(value=>value.barriers?.[String(bps)]).filter(Boolean);
    const counts={UP_FIRST:0,DOWN_FIRST:0,AMBIGUOUS_SAME_BAR:0,NOT_REACHED:0};
    for(const status of statuses)counts[status]=(counts[status]??0)+1;
    return [String(bps),{observations:statuses.length,...counts}];
  }));
  return Object.freeze({
    selectedRows:selected.length,targetReady:ready.length,
    meanUpExcursionBps:ready.length?round6(mean(values.map(value=>value.upExcursion))*10000):null,
    meanDownExcursionBps:ready.length?round6(mean(values.map(value=>value.downExcursion))*10000):null,
    meanTwoSidedOpportunityBps:ready.length?round6(mean(values.map(value=>value.twoSidedOpportunity))*10000):null,
    meanCostAdjustedUtilityBps:ready.length?round6(mean(values.map(value=>value.costAdjustedTwoSidedUtility))*10000):null,
    barriers:Object.freeze(barriers),
  });
}

function selectorRankDecile(selector,row){
  if(selector==='V1')return row.v1RankDecile;
  if(selector==='V2')return row.v2RankDecile;
  return row.v3RankDecile;
}

function summarizeSelector(rows,selector,v3Selected){
  const predicate=selectedPredicate(selector,v3Selected);
  const selected=rows.filter(predicate);
  const targetReady=selected.filter(row=>finite(row.primaryCostAdjustedUtility));
  const timestamps=new Set(rows.map(row=>row.featureCutoff));
  const selectedTimestamps=new Set(selected.map(row=>row.featureCutoff));
  const utility=targetReady.map(row=>Number(row.primaryCostAdjustedUtility));
  const pre=targetReady.map(row=>Number(row.preSelectionMove));
  const post=targetReady.map(row=>Number(row.primaryTwoSidedOpportunity));
  const late=targetReady.filter((row,index)=>pre[index]>post[index]).length;
  return Object.freeze({
    selector,
    candidateRows:rows.length,
    decisionTimestamps:timestamps.size,
    selectedRows:selected.length,
    selectedTargetReady:targetReady.length,
    selectedDecisionTimestamps:selectedTimestamps.size,
    coverage:rows.length?round6(selected.length/rows.length):0,
    meanSelectedPerTimestamp:timestamps.size?round6(selected.length/timestamps.size):0,
    meanPreSelectionMoveBps:targetReady.length?round6(mean(pre)*10000):null,
    meanUpExcursionBps:targetReady.length?round6(mean(targetReady.map(row=>row.primaryUpExcursion))*10000):null,
    meanDownExcursionBps:targetReady.length?round6(mean(targetReady.map(row=>row.primaryDownExcursion))*10000):null,
    meanTwoSidedOpportunityBps:targetReady.length?round6(mean(post)*10000):null,
    meanCostAdjustedUtilityBps:targetReady.length?round6(mean(utility)*10000):null,
    medianCostAdjustedUtilityBps:targetReady.length?round6(median(utility)*10000):null,
    positiveCostAdjustedUtilityRate:targetReady.length?round6(utility.filter(value=>value>0).length/targetReady.length):null,
    lateDetectionCandidateRate:targetReady.length?round6(late/targetReady.length):null,
    horizons:Object.freeze(Object.fromEntries(PHASE57_SELECTOR_V3_FREEZE.targets.horizonBars.map(horizon=>[
      String(horizon),horizonSummary(rows,predicate,horizon),
    ]))),
    slices:Object.freeze({
      timeOfDay:groupedSlices(rows,predicate,row=>row.timeOfDay),
      sector:groupedSlices(rows,predicate,row=>row.sector),
      marketRegime:groupedSlices(rows,predicate,row=>row.marketRegime),
      priceBand:groupedSlices(rows,predicate,row=>row.priceBand),
      liquidityBand:groupedSlices(rows,predicate,row=>row.liquidityBand),
      rankDecile:groupedSlices(rows,predicate,row=>selectorRankDecile(selector,row)),
    }),
  });
}

function leadTimeSummary(records,v3Selected){
  const selectors=['V1','V2','V3'];
  const first=new Map();
  records.forEach((row,index)=>{
    if(!(Number(row.primaryCostAdjustedUtility)>0))return;
    const key=`${row.sessionDate}|${row.symbol}`;
    if(!first.has(key))first.set(key,{});
    const value=first.get(key);
    for(const selector of selectors){
      const selected=selector==='V1'?row.v1Selected:selector==='V2'?row.v2Selected:v3Selected.has(index);
      if(selected&&!value[selector])value[selector]=row.featureCutoff;
    }
  });
  const deltas={v3VsV1:[],v3VsV2:[]};
  for(const value of first.values()){
    if(value.V3&&value.V1)deltas.v3VsV1.push((Date.parse(value.V1)-Date.parse(value.V3))/60000);
    if(value.V3&&value.V2)deltas.v3VsV2.push((Date.parse(value.V2)-Date.parse(value.V3))/60000);
  }
  const summarize=values=>({pairedEpisodes:values.length,meanMinutes:values.length?round6(mean(values)):null,medianMinutes:values.length?round6(median(values)):null,positiveMeansV3Earlier:true});
  return Object.freeze({v3VsV1:summarize(deltas.v3VsV1),v3VsV2:summarize(deltas.v3VsV2)});
}

function foldSummary(records,threshold){
  const v3Selected=applyV3Threshold(records,threshold);
  return Object.freeze({
    recordCount:records.length,
    V1:summarizeSelector(records,'V1',v3Selected),
    V2:summarizeSelector(records,'V2',v3Selected),
    V3:summarizeSelector(records,'V3',v3Selected),
    opportunityDetectionLeadTime:leadTimeSummary(records,v3Selected),
  });
}

export function evaluatePhase57SelectorHistoricalBenchmark(dataset,{releaseOuterOos=false}={}){
  const replay=replayPhase57SelectorHistoricalDataset(dataset);
  const split=splitPhase57SelectorHistoricalSessions(dataset.sessions);
  const setOf=dates=>new Set(dates);
  const developmentDates=setOf(split.development);
  const validationDates=setOf(split.validation);
  const oosDates=setOf(split.untouchedOos);
  const development=replay.records.filter(row=>developmentDates.has(row.sessionDate));
  const validation=replay.records.filter(row=>validationDates.has(row.sessionDate));
  const untouchedOos=replay.records.filter(row=>oosDates.has(row.sessionDate));
  const calibration=calibratePhase57SelectorV3Threshold(validation);
  const threshold=calibration.selectedThreshold;
  const output={
    schemaVersion:1,
    phase:'57.selector-v1-v2-v3.large-scale-historical-benchmark',
    status:releaseOuterOos?'SELECTOR_V1_V2_V3_BENCHMARK_WITH_OOS_RELEASED':'SELECTOR_V1_V2_V3_BENCHMARK_OOS_SEALED',
    dataset:replay.validation,split,calibration,
    development:foldSummary(development,threshold),
    validation:foldSummary(validation,threshold),
    untouchedOos:releaseOuterOos
      ?foldSummary(untouchedOos,threshold)
      :Object.freeze({status:'SEALED_UNTOUCHED_OOS',sessionCount:split.untouchedOos.length,recordCount:untouchedOos.length}),
    outerOosConsumed:Boolean(releaseOuterOos),
    methodology:Object.freeze({
      completeTimestampCrossSectionsAtomic:true,sessionChronologicalSplit:true,purgeApplied:true,
      sameHistoricalStatePaired:true,thresholdSelectedOnValidationOnly:true,
      v1V2Changed:false,v3PostFreezeChanged:false,automaticWinnerPromotion:false,
    }),
    safety:PHASE57_SELECTOR_V3_SAFETY,
  };
  assertSafety(output.safety,'benchmark');
  return Object.freeze(output);
}

export default {
  validatePhase57SelectorHistoricalDataset,
  splitPhase57SelectorHistoricalSessions,
  replayPhase57SelectorHistoricalDataset,
  calibratePhase57SelectorV3Threshold,
  evaluatePhase57SelectorHistoricalBenchmark,
};
