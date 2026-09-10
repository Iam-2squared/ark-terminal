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
const SELECTORS=Object.freeze(['V1','V2','V3']);
const STUDENT_T_975=Object.freeze([
  null,12.706205,4.302653,3.182446,2.776445,2.570582,2.446912,2.364624,2.306004,2.262157,
  2.228139,2.200985,2.178813,2.160369,2.144787,2.13145,2.119905,2.109816,2.100922,2.093024,
  2.085963,2.079614,2.073873,2.068658,2.063899,2.059539,2.055529,2.051831,2.048407,2.04523,
  2.042272,
]);
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const round6=value=>Number(Number(value).toFixed(6));
const mean=values=>values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;

function median(values){
  const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!xs.length)return null;
  const middle=Math.floor(xs.length/2);
  return xs.length%2?xs[middle]:(xs[middle-1]+xs[middle])/2;
}

function nearestRank(values,probability){
  const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!xs.length)return null;
  return xs[Math.max(0,Math.ceil(probability*xs.length)-1)];
}

function sampleStandardDeviation(values){
  if(values.length<2)return null;
  const center=mean(values);
  return Math.sqrt(values.reduce((sum,value)=>sum+(value-center)**2,0)/(values.length-1));
}

function studentTCritical975(degreesOfFreedom){
  if(degreesOfFreedom<1)return null;
  return STUDENT_T_975[degreesOfFreedom]??1.959964;
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
    benchmarkScope:String(manifest.benchmarkScope??'UNSPECIFIED'),
    requestedSampleSize:finite(manifest.requestedSampleSize)?Number(manifest.requestedSampleSize):null,
    actualSymbolCount:finite(manifest.actualSymbolCount)?Number(manifest.actualSymbolCount):(globalSymbols?.length??null),
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
    bars:item.bars.map(bar=>normalizeDatasetBar(bar,manifest)).sort((a,b)=>
      timestampMs(a.availableAt,'bar.availableAt')-timestampMs(b.availableAt,'bar.availableAt')
    ),
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

function timeOfDayBucket(timestamp){
  const [hour,minute]=jstTimeOfDay(timestamp).split(':').map(Number);
  const value=hour*60+minute;
  if(value<9*60+30)return '09:00-09:30';
  if(value<10*60+30)return '09:30-10:30';
  if(value<11*60+30)return '10:30-11:30';
  if(value<13*60+30)return '12:30-13:30';
  if(value<14*60+30)return '13:30-14:30';
  return '14:30-CLOSE';
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

function snapshotContext(entries){
  const marketMoves=entries.map(row=>Number(row.dailyChangePercent)).filter(Number.isFinite);
  const sectors=new Map();
  for(const row of entries){
    const move=Number(row.dailyChangePercent);
    if(!Number.isFinite(move))continue;
    const sector=sectorOf(row.sector);
    if(!sectors.has(sector))sectors.set(sector,[]);
    sectors.get(sector).push(move);
  }
  return Object.freeze({
    marketMedianMovePct:median(marketMoves),
    marketBreadthPositive:marketMoves.length?marketMoves.filter(value=>value>0).length/marketMoves.length:null,
    sectors,
  });
}

function contextForSymbol(context,entry){
  const sectorMoves=context.sectors.get(sectorOf(entry.sector))??[];
  const sectorMedianMovePct=median(sectorMoves);
  const stockMovePct=finite(entry.dailyChangePercent)?Number(entry.dailyChangePercent):null;
  return Object.freeze({
    marketMedianMovePct:context.marketMedianMovePct,
    marketBreadthPositive:context.marketBreadthPositive,
    sectorMedianMovePct,
    sectorBreadthPositive:sectorMoves.length?sectorMoves.filter(value=>value>0).length/sectorMoves.length:null,
    stockVsSectorResidualPct:stockMovePct!==null&&sectorMedianMovePct!==null?stockMovePct-sectorMedianMovePct:null,
  });
}

function trueRange(bar,previousClose){
  return Math.max(Number(bar.high)-Number(bar.low),Math.abs(Number(bar.high)-previousClose),Math.abs(Number(bar.low)-previousClose));
}

function preSelectionDiagnostics(symbol,sessionDate,featureCutoff){
  const closed=barsClosedBy(symbol,timestampMs(featureCutoff,'featureCutoff'));
  const sessionBars=closed.filter(bar=>bar.sessionDate===sessionDate);
  if(!sessionBars.length)return null;
  const anchorPrice=Number(sessionBars.at(-1).close);
  const preReturns=Object.fromEntries(PHASE57_SELECTOR_V3_FREEZE.targets.horizonBars.map(horizon=>{
    const priorIndex=sessionBars.length-1-horizon;
    return [String(horizon),priorIndex>=0?round6(anchorPrice/Number(sessionBars[priorIndex].close)-1):null];
  }));
  const sessionVolume=sessionBars.reduce((sum,bar)=>sum+Number(bar.volume),0);
  const sessionTurnover=sessionBars.reduce((sum,bar)=>sum+Number(bar.close)*Number(bar.volume),0);
  const vwapNumerator=sessionBars.reduce((sum,bar)=>sum+((Number(bar.high)+Number(bar.low)+Number(bar.close))/3)*Number(bar.volume),0);
  const vwap=sessionVolume>0?vwapNumerator/sessionVolume:null;
  const intradayHigh=Math.max(...sessionBars.map(bar=>Number(bar.high)));
  const intradayLow=Math.min(...sessionBars.map(bar=>Number(bar.low)));
  const ranges=closed.map((bar,index)=>trueRange(bar,index?Number(closed[index-1].close):Number(bar.open)))
    .slice(-PHASE57_SELECTOR_V3_FREEZE.featureDefinitions.atrLookbackBars);
  const atrPrice=ranges.length?mean(ranges):null;
  return Object.freeze({
    returnsByBars:Object.freeze(preReturns),
    returnFromSessionOpen:round6(anchorPrice/Number(sessionBars[0].open)-1),
    distanceFromVwap:vwap&&vwap>0?round6(anchorPrice/vwap-1):null,
    distanceFromIntradayHigh:intradayHigh>0?round6(anchorPrice/intradayHigh-1):null,
    distanceFromIntradayLow:intradayLow>0?round6(anchorPrice/intradayLow-1):null,
    atrPrice:Number.isFinite(atrPrice)?round6(atrPrice):null,
    atrNormalizedVwapExtension:vwap&&atrPrice>0?round6(Math.abs(anchorPrice-vwap)/atrPrice):null,
    cumulativeVolume:sessionVolume,
    cumulativeTurnoverYen:round6(sessionTurnover),
    rvol:null,
    rvolStatus:'UNAVAILABLE_NO_CAUSAL_SAME_TIME_HISTORY',
  });
}

function futureReturn(symbol,sessionDate,featureCutoff,anchorPrice,horizon){
  const cutoffMs=timestampMs(featureCutoff,'featureCutoff');
  const future=symbol.bars.filter(bar=>bar.sessionDate===sessionDate&&timestampMs(bar.availableAt,'bar.availableAt')>cutoffMs)
    .sort((a,b)=>timestampMs(a.availableAt,'bar.availableAt')-timestampMs(b.availableAt,'bar.availableAt'));
  if(future.length<horizon)return null;
  return round6(Number(future[horizon-1].close)/anchorPrice-1);
}

function rankBucket(rank){
  if(!Number.isFinite(rank))return 'NOT_RANKED';
  if(rank<=10)return 'RANK_01_10';
  if(rank<=20)return 'RANK_11_20';
  if(rank<=30)return 'RANK_21_30';
  if(rank<=40)return 'RANK_31_40';
  if(rank<=50)return 'RANK_41_50';
  return 'RANK_GT_50';
}

function persistenceBucket(value){
  if(!Number.isFinite(value))return 'UNKNOWN';
  if(Math.abs(value)<1e-9)return 'PERSISTENCE_0';
  if(Math.abs(value-1/3)<1e-6)return 'PERSISTENCE_1_3';
  if(Math.abs(value-1/2)<1e-6)return 'PERSISTENCE_WARMUP_1_2';
  if(Math.abs(value-2/3)<1e-6)return 'PERSISTENCE_2_3';
  if(Math.abs(value-1)<1e-9)return 'PERSISTENCE_1';
  return 'PERSISTENCE_OTHER';
}

function rankDecile(rank,total){
  if(!Number.isFinite(rank)||!Number.isFinite(total)||total<1)return 'NOT_RANKED';
  return `D${Math.min(10,Math.max(1,Math.ceil(rank/total*10)))}`;
}

function recordForSymbol({
  session,featureCutoff,symbol,snapshotEntry,v1Point,v2Point,v3Result,selectionMaps,regime,context,v2Transition,
}){
  const v1Index=selectionMaps.v1.get(symbol.symbol)??-1;
  const v2Index=selectionMaps.v2.get(symbol.symbol)??-1;
  const v1Row=v1Index>=0?v1Point.rawUniverse[v1Index]:null;
  const v2SelectedRow=v2Index>=0?v2Point.rawUniverse[v2Index]:null;
  const v2ScoredIndex=selectionMaps.v2Scored.get(symbol.symbol)??-1;
  const v2Row=v2ScoredIndex>=0?v2Point.v2RankedUniverse[v2ScoredIndex]:v2SelectedRow;
  const v3Index=selectionMaps.v3.get(symbol.symbol)??-1;
  const v3Row=v3Index>=0?v3Result.ranked[v3Index]:null;
  const closed=barsClosedBy(symbol,timestampMs(featureCutoff,'featureCutoff'));
  const current=closed.filter(bar=>bar.sessionDate===session.sessionDate).at(-1);
  if(!current)return null;
  const anchorPrice=Number(current.close);
  const pre=preSelectionDiagnostics(symbol,session.sessionDate,featureCutoff);
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
      futureReturn:futureReturn(symbol,session.sessionDate,featureCutoff,anchorPrice,horizon),
      barriers:value.barriers===null?null:Object.fromEntries(Object.entries(value.barriers).map(([bps,barrier])=>[bps,barrier.status])),
    }];
  }));
  const turnoverYen=anchorPrice*Number(snapshotEntry.volume);
  const persistence=finite(v2Row?.components?.persistence)?Number(v2Row.components.persistence):null;
  return Object.freeze({
    sessionDate:session.sessionDate,featureCutoff,timeOfDay:jstTimeOfDay(featureCutoff),timeOfDayBucket:timeOfDayBucket(featureCutoff),
    symbol:symbol.symbol,sector:symbol.sector,market:symbol.market??null,marketRegime:regime,
    currentPrice:anchorPrice,cumulativeVolume:Number(snapshotEntry.volume),dailyChangePercent:Number(snapshotEntry.dailyChangePercent),
    turnoverYen,priceBand:priceBand(anchorPrice),liquidityBand:liquidityBand(turnoverYen),
    preSelectionMove:Math.abs(pre.returnFromSessionOpen),preSelection:pre,context,
    v1Selected:v1Index>=0,v1Rank:v1Index>=0?v1Index+1:null,v1Score:v1Row?.opportunityScore??null,
    v1RankBucket:rankBucket(v1Index>=0?v1Index+1:null),v1Modes:v1Row?.modes??null,
    v2Selected:v2Index>=0,v2Rank:v2Index>=0?v2Index+1:null,v2Score:v2Row?.v2Score??null,
    v2ScoredRank:v2ScoredIndex>=0?v2ScoredIndex+1:null,v2RankBucket:rankBucket(v2Index>=0?v2Index+1:null),
    v2Persistence:persistence,v2PersistenceBucket:persistenceBucket(persistence),v2Transition,
    v2Components:v2Row?.components??null,
    v3Eligible:v3Index>=0,v3Rank:v3Index>=0?v3Index+1:null,v3Score:v3Row?.utilityScore??null,
    v3RankBucket:rankBucket(v3Index>=0?v3Index+1:null),
    v3StructuralTradability:v3Row?.structuralTradability??null,
    v3Momentum:v3Row?.momentum??null,v3RemainingHeadroom:v3Row?.remainingHeadroom??null,
    v3MarketSectorContext:v3Row?.marketSectorContext??null,v3Components:v3Row?.components??null,
    v3SectorContextStatus:v3Row?.components?.sectorContextStatus??null,
    v1RankDecile:rankDecile(v1Index>=0?v1Index+1:null,v1Point?.rawUniverse?.length??0),
    v2RankDecile:rankDecile(v2Index>=0?v2Index+1:null,v2Point?.rawUniverse?.length??0),
    v3RankDecile:rankDecile(v3Index>=0?v3Index+1:null,v3Result.ranked.length),
    targetStatus:primary.status,
    primaryUpExcursion:primary.upExcursion,
    primaryDownExcursion:primary.downExcursion,
    primaryTwoSidedOpportunity:primary.twoSidedOpportunity,
    primaryCostAdjustedUtility:primary.costAdjustedTwoSidedUtility,
    primaryFutureReturn:horizonTargets[String(PHASE57_SELECTOR_V3_FREEZE.targets.primaryHorizonBars)].futureReturn,
    featureAvailability:Object.freeze({
      reconstructedRealtime:Object.freeze({currentPrice:true,cumulativeVolume:true,dailyChangePercent:true,sector:true,market:snapshotEntry.market!==null}),
      unavailableRealtime:Object.freeze({volumeRatio:false,rvol:false,atrPercent:false,discoveryScore:false,technicalScore:false,confidence:false,qualityScore:false,microstructure:false}),
      missingValuesZeroFilled:false,
    }),
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
    let previousV2Selected=new Set();
    const everV2Selected=new Set();
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
        v2Scored:new Map((v2Point?.v2RankedUniverse??[]).map((row,index)=>[row.symbol,index])),
        v3:new Map(v3.ranked.map((row,index)=>[row.symbol,index])),
      };
      const regime=marketRegime(snapshot.entries);
      const pointContext=snapshotContext(snapshot.entries);
      const currentV2Selected=new Set(selectionMaps.v2.keys());
      const bySymbol=new Map(symbols.map(symbol=>[symbol.symbol,symbol]));
      for(const snapshotEntry of snapshot.entries){
        const symbol=bySymbol.get(snapshotEntry.symbol);
        const isCurrent=currentV2Selected.has(snapshotEntry.symbol);
        const wasPrevious=previousV2Selected.has(snapshotEntry.symbol);
        const wasEver=everV2Selected.has(snapshotEntry.symbol);
        const v2Transition=isCurrent
          ?(wasPrevious?'INCUMBENT':wasEver?'RE_ENTERED':'NEW_ENTRANT')
          :(wasPrevious?'DROPPED':'NOT_SELECTED');
        const record=recordForSymbol({
          session,featureCutoff:snapshot.asOf,symbol,snapshotEntry,v1Point,v2Point,v3Result:v3,
          selectionMaps,regime,context:contextForSymbol(pointContext,snapshotEntry),v2Transition,
        });
        if(record)records.push(record);
      }
      for(const selected of currentV2Selected)everV2Selected.add(selected);
      previousV2Selected=currentV2Selected;
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
  const late=selected.filter(row=>Number(row.preSelectionMove)>Number(row.primaryTwoSidedOpportunity)).length;
  return {
    selectedTargetReady:selected.length,
    meanReturnFromSessionOpenBps:selected.length?round6(mean(selected.map(row=>row.preSelection.returnFromSessionOpen))*10000):null,
    meanPreSelectionMoveBps:selected.length?round6(mean(selected.map(row=>row.preSelectionMove))*10000):null,
    meanPostSelectionReturnBps:selected.length?round6(mean(selected.map(row=>row.primaryFutureReturn))*10000):null,
    meanUpExcursionBps:selected.length?round6(mean(selected.map(row=>row.primaryUpExcursion))*10000):null,
    meanDownExcursionBps:selected.length?round6(mean(selected.map(row=>row.primaryDownExcursion))*10000):null,
    meanCostAdjustedUtilityBps:selected.length?round6(mean(selected.map(row=>row.primaryCostAdjustedUtility))*10000):null,
    meanTwoSidedOpportunityBps:selected.length?round6(mean(selected.map(row=>row.primaryTwoSidedOpportunity))*10000):null,
    lateDetectionCandidateRate:selected.length?round6(late/selected.length):null,
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
  const futureReturns=values.map(value=>value.futureReturn).filter(finite).map(Number);
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
    meanPostSelectionReturnBps:futureReturns.length?round6(mean(futureReturns)*10000):null,
    barriers:Object.freeze(barriers),
  });
}

function selectorRankDecile(selector,row){
  if(selector==='V1')return row.v1RankDecile;
  if(selector==='V2')return row.v2RankDecile;
  return row.v3RankDecile;
}

function selectorRankBucket(selector,row){
  if(selector==='V1')return row.v1RankBucket;
  if(selector==='V2')return row.v2RankBucket;
  return row.v3RankBucket;
}

function summarizeSelection(rows,selector,predicate){
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
    meanReturnFromSessionOpenBps:targetReady.length?round6(mean(targetReady.map(row=>row.preSelection.returnFromSessionOpen))*10000):null,
    meanPostSelectionReturnBps:targetReady.length?round6(mean(targetReady.map(row=>row.primaryFutureReturn))*10000):null,
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
      timeOfDayBucket:groupedSlices(rows,predicate,row=>row.timeOfDayBucket),
      sector:groupedSlices(rows,predicate,row=>row.sector),
      marketRegime:groupedSlices(rows,predicate,row=>row.marketRegime),
      priceBand:groupedSlices(rows,predicate,row=>row.priceBand),
      liquidityBand:groupedSlices(rows,predicate,row=>row.liquidityBand),
      rankDecile:groupedSlices(rows,predicate,row=>selectorRankDecile(selector,row)),
      rankBucket:groupedSlices(rows,predicate,row=>selectorRankBucket(selector,row)),
    }),
  });
}

function summarizeSelector(rows,selector,v3Selected){
  return summarizeSelection(rows,selector,selectedPredicate(selector,v3Selected));
}

function selectionFlags(row,index,v3Selected){
  return Object.freeze({V1:Boolean(row.v1Selected),V2:Boolean(row.v2Selected),V3:v3Selected.has(index)});
}

function overlapCategory(flags){
  const selected=Object.entries(flags).filter(([,value])=>value).map(([key])=>key);
  if(!selected.length)return 'NONE';
  return selected.length===1?`${selected[0]}_ONLY`:selected.join('_');
}

function selectorRank(selector,row){
  if(selector==='V1')return row.v1Rank;
  if(selector==='V2')return row.v2Rank;
  return row.v3Rank;
}

function selectorScore(selector,row){
  if(selector==='V1')return row.v1Score;
  if(selector==='V2')return row.v2Score;
  return row.v3Score;
}

function selectorFeatureSnapshot(selector,row){
  const shared=Object.freeze({
    currentPrice:row.currentPrice,cumulativeVolume:row.cumulativeVolume,dailyChangePercent:row.dailyChangePercent,
    turnoverYen:row.turnoverYen,recentReturn3Bars:row.preSelection.returnsByBars['3'],
    rvol:row.preSelection.rvol,distanceFromVwap:row.preSelection.distanceFromVwap,
    atrNormalizedVwapExtension:row.preSelection.atrNormalizedVwapExtension,
    marketContext:row.context.marketMedianMovePct,sectorContext:row.context.sectorMedianMovePct,
  });
  if(selector==='V1')return Object.freeze({
    ...shared,modes:row.v1Modes,
    volumeRatio:null,atrPercent:null,discoveryScore:null,technicalScore:null,confidence:null,qualityScore:null,
    unavailableRealtimeFeaturesExplicit:true,
  });
  if(selector==='V2')return Object.freeze({
    ...shared,baseOpportunity:row.v2Components?.baseOpportunity??null,
    liquidityQuality:row.v2Components?.liquidityQuality??null,
    persistence:row.v2Persistence,signalQuality:row.v2Components?.signalQuality??null,
    transition:row.v2Transition,unavailableRealtimeFeaturesExplicit:true,
  });
  return Object.freeze({
    ...shared,structuralTradability:row.v3StructuralTradability,momentum:row.v3Momentum,
    remainingHeadroom:row.v3RemainingHeadroom,marketSectorContext:row.v3MarketSectorContext,
    components:row.v3Components,missingValuesZeroFilled:false,
  });
}

export function buildPhase57SelectorSelectionArtifacts(records,v3Selected){
  const groups=new Map();
  records.forEach((row,index)=>{
    const key=`${row.sessionDate}|${row.featureCutoff}`;
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push({row,index,flags:selectionFlags(row,index,v3Selected)});
  });
  const points=[];
  const outcomes=[];
  for(const group of groups.values()){
    const first=group[0].row;
    const selectedBy={};
    for(const selector of ['V1','V2','V3']){
      selectedBy[selector]=group.filter(item=>item.flags[selector]).sort((a,b)=>
        selectorRank(selector,a.row)-selectorRank(selector,b.row)||a.row.symbol.localeCompare(b.row.symbol)
      );
    }
    const sets=Object.fromEntries(Object.entries(selectedBy).map(([selector,items])=>[selector,new Set(items.map(item=>item.row.symbol))]));
    const intersection=(...selectors)=>[...sets[selectors[0]]].filter(symbol=>selectors.every(selector=>sets[selector].has(symbol))).sort();
    const union=new Set([...sets.V1,...sets.V2,...sets.V3]);
    const categorySymbols={V1_ONLY:[],V2_ONLY:[],V3_ONLY:[],V1_V2:[],V1_V3:[],V2_V3:[],V1_V2_V3:[]};
    for(const symbol of union){
      const item=group.find(candidate=>candidate.row.symbol===symbol);
      const category=overlapCategory(item.flags);
      if(categorySymbols[category])categorySymbols[category].push(symbol);
    }
    for(const values of Object.values(categorySymbols))values.sort();
    points.push(Object.freeze({
      sessionDate:first.sessionDate,selectionTimestamp:first.featureCutoff,timeOfDay:first.timeOfDay,timeOfDayBucket:first.timeOfDayBucket,
      selectedSymbols:Object.freeze(Object.fromEntries(Object.entries(selectedBy).map(([selector,items])=>[selector,Object.freeze(items.map(item=>item.row.symbol))]))),
      selectedCounts:Object.freeze(Object.fromEntries(Object.entries(selectedBy).map(([selector,items])=>[selector,items.length]))),
      overlaps:Object.freeze({
        v1V2:Object.freeze(intersection('V1','V2')),v1V3:Object.freeze(intersection('V1','V3')),
        v2V3:Object.freeze(intersection('V2','V3')),v1V2V3:Object.freeze(intersection('V1','V2','V3')),
        categories:Object.freeze(Object.fromEntries(Object.entries(categorySymbols).map(([key,value])=>[key,Object.freeze(value)]))),
      }),
    }));
    for(const item of group){
      const category=overlapCategory(item.flags);
      for(const selector of ['V1','V2','V3']){
        if(!item.flags[selector])continue;
        const row=item.row;
        outcomes.push(Object.freeze({
          recordType:'SELECTOR_SELECTION_OUTCOME',sessionDate:row.sessionDate,selectionTimestamp:row.featureCutoff,
          symbol:row.symbol,selectorVersion:selector,rank:selectorRank(selector,row),score:selectorScore(selector,row),
          selectedCount:selectedBy[selector].length,overlapCategory:category,
          priceAtSelection:row.currentPrice,sector:row.sector,market:row.market,
          selectorFeatures:selectorFeatureSnapshot(selector,row),featureAvailability:row.featureAvailability,
          preSelection:row.preSelection,postSelection:row.horizonTargets,
          primaryOutcome:Object.freeze({
            horizonBars:PHASE57_SELECTOR_V3_FREEZE.targets.primaryHorizonBars,
            futureReturn:row.primaryFutureReturn,upExcursion:row.primaryUpExcursion,
            downExcursion:row.primaryDownExcursion,twoSidedOpportunity:row.primaryTwoSidedOpportunity,
            costAdjustedTradableUtility:row.primaryCostAdjustedUtility,
          }),
          v2Transition:row.v2Transition,v2Persistence:row.v2Persistence,v2PersistenceBucket:row.v2PersistenceBucket,
          evidence:Object.freeze({selectionFrozenBeforeOutcome:true,futureUsedOnlyForOutcome:true}),
        }));
      }
    }
  }
  outcomes.sort((a,b)=>a.selectionTimestamp.localeCompare(b.selectionTimestamp)||a.selectorVersion.localeCompare(b.selectorVersion)||a.rank-b.rank||a.symbol.localeCompare(b.symbol));
  return Object.freeze({points:Object.freeze(points),outcomes:Object.freeze(outcomes)});
}

export function summarizePhase57PairedSessionDeltas({
  leftSelector,rightSelector,sessionDeltasBps,expectedSessionCount,
}){
  if(!SELECTORS.includes(leftSelector)||!SELECTORS.includes(rightSelector)||leftSelector===rightSelector){
    throw new TypeError('paired delta requires two different frozen selectors');
  }
  if(!Array.isArray(sessionDeltasBps))throw new TypeError('sessionDeltasBps must be an array');
  const deltas=sessionDeltasBps.map(item=>({
    sessionDate:String(item.sessionDate),deltaBps:Number(item.deltaBps),
  }));
  if(deltas.some(item=>!Number.isFinite(item.deltaBps)))throw new TypeError('paired session delta must be finite');
  const values=deltas.map(item=>item.deltaBps);
  const center=mean(values);
  const standardDeviation=sampleStandardDeviation(values);
  const standardError=standardDeviation===null?null:standardDeviation/Math.sqrt(values.length);
  const critical=studentTCritical975(values.length-1);
  const margin=standardError===null||critical===null?null:critical*standardError;
  const positive=values.filter(value=>value>0).length;
  const negative=values.filter(value=>value<0).length;
  const tie=values.length-positive-negative;
  return Object.freeze({
    leftSelector,rightSelector,orientation:'LEFT_SELECTOR_MINUS_RIGHT_SELECTOR',
    expectedSessionCount:Number(expectedSessionCount),pairedSessionCount:values.length,
    completeExpectedSessions:values.length===Number(expectedSessionCount),
    meanDeltaBps:center===null?null:round6(center),
    sampleStandardDeviationBps:standardDeviation===null?null:round6(standardDeviation),
    standardErrorBps:standardError===null?null:round6(standardError),
    confidenceLevel:0.95,intervalMethod:'TWO_SIDED_STUDENT_T_PAIRED_SESSION_DELTAS',
    degreesOfFreedom:values.length>=2?values.length-1:null,
    criticalValue:critical===null?null:round6(critical),
    ci95Bps:margin===null?null:Object.freeze({lower:round6(center-margin),upper:round6(center+margin)}),
    zeroIncluded:margin===null?null:center-margin<=0&&center+margin>=0,
    direction:Object.freeze({
      positiveSessions:positive,negativeSessions:negative,tiedSessions:tie,
      positiveRate:values.length?round6(positive/values.length):null,
    }),
    sessionDeltasBps:Object.freeze(deltas.map(item=>Object.freeze({...item,deltaBps:round6(item.deltaBps)}))),
  });
}

function sessionPrimaryMeans(rows,predicate){
  const groups=new Map();
  rows.forEach((row,index)=>{
    if(!predicate(row,index)||!finite(row.primaryCostAdjustedUtility))return;
    if(!groups.has(row.sessionDate))groups.set(row.sessionDate,[]);
    groups.get(row.sessionDate).push(Number(row.primaryCostAdjustedUtility)*10000);
  });
  return new Map([...groups.entries()].map(([sessionDate,values])=>[sessionDate,mean(values)]));
}

function pairedPrimaryUtility(rows,leftSelector,rightSelector,predicates){
  const sessions=[...new Set(rows.map(row=>row.sessionDate))].sort();
  const left=sessionPrimaryMeans(rows,predicates[leftSelector]);
  const right=sessionPrimaryMeans(rows,predicates[rightSelector]);
  const paired=sessions.filter(sessionDate=>left.has(sessionDate)&&right.has(sessionDate)).map(sessionDate=>({
    sessionDate,deltaBps:left.get(sessionDate)-right.get(sessionDate),
  }));
  const summary=summarizePhase57PairedSessionDeltas({
    leftSelector,rightSelector,sessionDeltasBps:paired,expectedSessionCount:sessions.length,
  });
  return Object.freeze({
    ...summary,
    leftMissingSessions:Object.freeze(sessions.filter(sessionDate=>!left.has(sessionDate))),
    rightMissingSessions:Object.freeze(sessions.filter(sessionDate=>!right.has(sessionDate))),
  });
}

function primaryInference(rows,predicates){
  const pairwise={};
  for(const left of SELECTORS){
    for(const right of SELECTORS){
      if(left===right)continue;
      pairwise[`${left}_MINUS_${right}`]=pairedPrimaryUtility(rows,left,right,predicates);
    }
  }
  const qualifies=SELECTORS.filter(selector=>SELECTORS.filter(other=>other!==selector).every(other=>{
    const comparison=pairwise[`${selector}_MINUS_${other}`];
    return comparison.completeExpectedSessions&&comparison.meanDeltaBps>0&&
      comparison.ci95Bps?.lower>0&&comparison.direction.positiveSessions>comparison.direction.negativeSessions;
  }));
  return Object.freeze({
    metric:'COST_ADJUSTED_TWO_SIDED_OPPORTUNITY_UTILITY',horizonBars:6,horizonMinutes:30,
    sessionWeighting:'EQUAL',pairwise:Object.freeze(pairwise),
    winnerDecision:Object.freeze({
      status:qualifies.length===1?'STATISTICALLY_ESTABLISHED_WINNER':'NO_STATISTICALLY_ESTABLISHED_WINNER',
      winner:qualifies.length===1?qualifies[0]:null,
      qualifyingSelectors:Object.freeze(qualifies),
      secondaryOrDiagnosticOverrideAllowed:false,automaticPromotionAllowed:false,
    }),
  });
}

function distribution(values){
  const xs=values.filter(Number.isFinite);
  return Object.freeze({
    observations:xs.length,min:xs.length?Math.min(...xs):null,
    p10NearestRank:nearestRank(xs,0.1),median:median(xs),p90NearestRank:nearestRank(xs,0.9),
    max:xs.length?Math.max(...xs):null,zeroTimestampCount:xs.filter(value=>value===0).length,
  });
}

function dynamicNDistribution(points){
  return Object.freeze(Object.fromEntries(SELECTORS.map(selector=>[
    selector,distribution(points.map(point=>Number(point.selectedCounts[selector]))),
  ])));
}

function overlapOutcomeGroups(rows,v3Selected){
  const categories=['V1_ONLY','V2_ONLY','V3_ONLY','V1_V2','V1_V3','V2_V3','V1_V2_V3'];
  return Object.freeze(Object.fromEntries(categories.map(category=>[
    category,Object.freeze(simpleGroupSummary(rows,(row,index)=>overlapCategory(selectionFlags(row,index,v3Selected))===category)),
  ])));
}

function sameCapacitySummary(rows,v3Selected){
  const selectedSets=Object.fromEntries(SELECTORS.map(selector=>[selector,new Set()]));
  const groups=new Map();
  rows.forEach((row,index)=>{
    if(!groups.has(row.featureCutoff))groups.set(row.featureCutoff,[]);
    groups.get(row.featureCutoff).push({row,index});
  });
  const kValues=[];
  for(const group of groups.values()){
    const selectedV3=group.filter(item=>v3Selected.has(item.index));
    const k=selectedV3.length;
    kValues.push(k);
    for(const item of selectedV3)selectedSets.V3.add(item.index);
    for(const selector of ['V1','V2']){
      const ranked=group.filter(item=>selector==='V1'?item.row.v1Selected:item.row.v2Selected)
        .sort((a,b)=>selectorRank(selector,a.row)-selectorRank(selector,b.row)||a.row.symbol.localeCompare(b.row.symbol));
      for(const item of ranked.slice(0,k))selectedSets[selector].add(item.index);
    }
  }
  const predicates=Object.freeze(Object.fromEntries(SELECTORS.map(selector=>[
    selector,(row,index)=>selectedSets[selector].has(index),
  ])));
  return Object.freeze({
    definition:'V1_TOP_K_V2_TOP_K_VS_V3_AT_EACH_TIMESTAMP',
    kDefinition:'FROZEN_V3_SELECTED_COUNT',kZeroPolicy:'SELECT_NONE_FOR_ALL_ARMS',
    kDistribution:distribution(kValues),
    V1:summarizeSelection(rows,'V1',predicates.V1),
    V2:summarizeSelection(rows,'V2',predicates.V2),
    V3:summarizeSelection(rows,'V3',predicates.V3),
    primaryInference:primaryInference(rows,predicates),
    primaryWinnerOverrideAllowed:false,
  });
}

function overlapSummary(points){
  const categories={V1_ONLY:0,V2_ONLY:0,V3_ONLY:0,V1_V2:0,V1_V3:0,V2_V3:0,V1_V2_V3:0};
  const counts={V1:[],V2:[],V3:[],v1V2:[],v1V3:[],v2V3:[],v1V2V3:[]};
  for(const point of points){
    for(const selector of ['V1','V2','V3'])counts[selector].push(point.selectedCounts[selector]);
    for(const key of ['v1V2','v1V3','v2V3','v1V2V3'])counts[key].push(point.overlaps[key].length);
    for(const [key,symbols] of Object.entries(point.overlaps.categories))categories[key]+=symbols.length;
  }
  return Object.freeze({
    decisionTimestamps:points.length,
    meanCounts:Object.freeze(Object.fromEntries(Object.entries(counts).map(([key,values])=>[key,values.length?round6(mean(values)):null]))),
    symbolTimestampCategories:Object.freeze(categories),
  });
}

function v2PersistenceSummary(rows){
  const selected=row=>row.v2Selected;
  const transition=row=>row.v2Transition!=='NOT_SELECTED';
  return Object.freeze({
    selectedByPersistence:groupedSlices(rows,selected,row=>row.v2PersistenceBucket),
    byTransition:groupedSlices(rows,transition,row=>row.v2Transition),
    transitionCounts:Object.freeze(Object.fromEntries(['NEW_ENTRANT','INCUMBENT','DROPPED','RE_ENTERED'].map(key=>[
      key,rows.filter(row=>row.v2Transition===key).length,
    ]))),
  });
}

function leadTimeSummary(records,v3Selected){
  const selectors=['V1','V2','V3'];
  const first=new Map();
  records.forEach((row,index)=>{
    const key=`${row.sessionDate}|${row.symbol}`;
    if(!first.has(key))first.set(key,{});
    const value=first.get(key);
    for(const selector of selectors){
      const selected=selector==='V1'?row.v1Selected:selector==='V2'?row.v2Selected:v3Selected.has(index);
      if(selected&&!value[selector])value[selector]={timestamp:row.featureCutoff,utility:row.primaryCostAdjustedUtility,opportunity:row.primaryTwoSidedOpportunity};
    }
  });
  const compare=other=>{
    const pairs=[];
    for(const value of first.values()){
      if(!value.V3||!value[other])continue;
      pairs.push({
        minutes:(Date.parse(value[other].timestamp)-Date.parse(value.V3.timestamp))/60000,
        v3Utility:Number(value.V3.utility),v3Opportunity:Number(value.V3.opportunity),otherUtility:Number(value[other].utility),
      });
    }
    const earlier=pairs.filter(pair=>pair.minutes>0);
    return Object.freeze({
      pairedSessionSymbols:pairs.length,
      meanMinutes:pairs.length?round6(mean(pairs.map(pair=>pair.minutes))):null,
      medianMinutes:pairs.length?round6(median(pairs.map(pair=>pair.minutes))):null,
      v3EarlierCount:earlier.length,
      v3EarlierWithPositiveUtilityCount:earlier.filter(pair=>pair.v3Utility>0).length,
      falseEarlyDetectionCount:earlier.filter(pair=>!(pair.v3Utility>0)).length,
      meanV3OpportunityWhenEarlierBps:earlier.length?round6(mean(earlier.map(pair=>pair.v3Opportunity))*10000):null,
      positiveMinutesMeanV3Earlier:true,
    });
  };
  return Object.freeze({
    episodeDefinition:'SESSION_SYMBOL_FIRST_DETECTION_PILOT_PROXY',
    v3VsV1:compare('V1'),v3VsV2:compare('V2'),
  });
}

function foldSummary(records,threshold,{includeSelectionOutcomes=false}={}){
  const v3Selected=applyV3Threshold(records,threshold);
  const selectionArtifacts=buildPhase57SelectorSelectionArtifacts(records,v3Selected);
  const predicates=Object.freeze({
    V1:selectedPredicate('V1',v3Selected),
    V2:selectedPredicate('V2',v3Selected),
    V3:selectedPredicate('V3',v3Selected),
  });
  return Object.freeze({
    recordCount:records.length,
    V1:summarizeSelector(records,'V1',v3Selected),
    V2:summarizeSelector(records,'V2',v3Selected),
    V3:summarizeSelector(records,'V3',v3Selected),
    primaryInference:primaryInference(records,predicates),
    sameCapacity:sameCapacitySummary(records,v3Selected),
    overlap:overlapSummary(selectionArtifacts.points),
    overlapOutcomeGroups:overlapOutcomeGroups(records,v3Selected),
    v2Persistence:v2PersistenceSummary(records),
    opportunityDetectionLeadTime:leadTimeSummary(records,v3Selected),
    dynamicN:dynamicNDistribution(selectionArtifacts.points),
    selectionOutcomeRecordCount:selectionArtifacts.outcomes.length,
    selectionPointRecordCount:selectionArtifacts.points.length,
    ...(includeSelectionOutcomes?{
      selectionOutcomes:selectionArtifacts.outcomes,
      selectionPoints:selectionArtifacts.points,
    }:{}),
  });
}

export function evaluatePhase57SelectorHistoricalBenchmark(dataset,{releaseOuterOos=false,includeSelectionOutcomes=false}={}){
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
    schemaVersion:3,
    phase:'57.selector-v1-v2-v3.large-scale-historical-benchmark',
    status:releaseOuterOos?'SELECTOR_V1_V2_V3_BENCHMARK_WITH_OOS_RELEASED':'SELECTOR_V1_V2_V3_BENCHMARK_OOS_SEALED',
    dataset:replay.validation,split,calibration,
    development:foldSummary(development,threshold,{includeSelectionOutcomes}),
    validation:foldSummary(validation,threshold,{includeSelectionOutcomes}),
    untouchedOos:releaseOuterOos
      ?foldSummary(untouchedOos,threshold,{includeSelectionOutcomes})
      :Object.freeze({status:'SEALED_UNTOUCHED_OOS',sessionCount:split.untouchedOos.length,recordCount:untouchedOos.length}),
    outerOosConsumed:Boolean(releaseOuterOos),
    methodology:Object.freeze({
      completeTimestampCrossSectionsAtomic:true,sessionChronologicalSplit:true,purgeApplied:true,
      sameHistoricalStatePaired:true,thresholdSelectedOnValidationOnly:true,
      selectionThenFreezeThenOutcome:true,continuousLateDetectionDiagnostics:true,
      outcomeRowsRetainedWhenRequested:true,
      primarySessionEqualWeighting:true,primaryPairedStudentT95Interval:true,
      sameCapacityPreRegisteredBeforeOos:true,analysisContractRequiredByCliForOos:true,
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
  buildPhase57SelectorSelectionArtifacts,
  summarizePhase57PairedSessionDeltas,
  evaluatePhase57SelectorHistoricalBenchmark,
};
