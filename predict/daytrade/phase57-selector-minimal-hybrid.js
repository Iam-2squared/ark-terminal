import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {buildIntradayDynamicUniverseTimeline} from './phase57-p25-intraday-dynamic-universe.js';
import {predictPhase57MinimalHybridTargets} from './phase57-selector-minimal-hybrid-model.js';

const amendmentUrl=new URL('../research/phase57-selector-minimal-hybrid-phase-a-amendment-v1.1.json',import.meta.url);
export const PHASE57_SELECTOR_MINIMAL_HYBRID_AMENDMENT=deepFreeze(JSON.parse(fs.readFileSync(amendmentUrl,'utf8')));
export const PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY=PHASE57_SELECTOR_MINIMAL_HYBRID_AMENDMENT.safety;

const FORBIDDEN_KEYS=Object.freeze([
  'outcome','label','target','targets','futureReturn','futureReturnPct','netReturnPct','tradeWin','profitFactor','entryDirection','entryPrice','exitTime','positionSize',
]);
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const clamp=(value,min=0,max=1)=>Math.min(max,Math.max(min,Number(value)));
const round8=value=>Number(Number(value).toFixed(8));
const symbolOf=value=>String(value??'').trim().toUpperCase();
const sectorOf=value=>String(value??'').trim()||'UNKNOWN';

function deepFreeze(value){
  if(value&&typeof value==='object'&&!Object.isFrozen(value)){
    for(const child of Object.values(value))deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

function timeMs(value,label){
  const result=Date.parse(String(value??''));
  if(!Number.isFinite(result))throw new TypeError(`${label} must be a valid timestamp`);
  return result;
}

function jstTime(timestamp){
  const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(timestamp));
  const values=Object.fromEntries(parts.map(part=>[part.type,part.value]));
  return `${values.hour}:${values.minute}`;
}

function sessionSegment(timestamp){
  const time=jstTime(timestamp);
  if(time>='09:00'&&time<'11:30')return 'AM';
  if(time>='12:30'&&time<'15:30')return 'PM';
  return null;
}

function normalizeBar(bar,{symbol,index}){
  const timestamp=String(bar?.timestamp??'');
  const availableAt=String(bar?.availableAt??'');
  const timestampValue=timeMs(timestamp,`${symbol} bars[${index}].timestamp`);
  const availableAtValue=timeMs(availableAt,`${symbol} bars[${index}].availableAt`);
  if(availableAtValue<timestampValue)throw new Error(`${symbol} bars[${index}] availableAt precedes timestamp`);
  const sessionDate=String(bar?.sessionDate??'');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`${symbol} bars[${index}] requires sessionDate`);
  const segment=sessionSegment(timestamp);
  if(!segment)throw new Error(`${symbol} bars[${index}] is outside a regular JPX session segment`);
  for(const key of ['open','high','low','close','volume'])if(!finite(bar?.[key]))throw new Error(`${symbol} bars[${index}] missing ${key}; missing cannot become zero`);
  const normalized={
    timestamp,availableAt,timestampMs:timestampValue,availableAtMs:availableAtValue,sessionDate,segment,
    open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),volume:Number(bar.volume),
    turnover:finite(bar.turnover)?Number(bar.turnover):null,
  };
  if(normalized.open<=0||normalized.high<=0||normalized.low<=0||normalized.close<=0||normalized.volume<0)throw new Error(`${symbol} bars[${index}] has invalid OHLCV`);
  if(normalized.high<Math.max(normalized.open,normalized.close,normalized.low)||normalized.low>Math.min(normalized.open,normalized.close,normalized.high))throw new Error(`${symbol} bars[${index}] has invalid OHLC ordering`);
  if(normalized.turnover!==null&&normalized.turnover<0)throw new Error(`${symbol} bars[${index}] turnover must be non-negative`);
  return normalized;
}

function sameBar(left,right){
  return ['timestamp','availableAt','sessionDate','open','high','low','close','volume','turnover'].every(key=>left[key]===right[key]);
}

function normalizeBars(bars,{symbol}){
  if(!Array.isArray(bars))throw new TypeError(`${symbol} bars must be an array`);
  const unique=new Map();
  bars.forEach((bar,index)=>{
    const normalized=normalizeBar(bar,{symbol,index});
    const previous=unique.get(normalized.availableAt);
    if(previous&&!sameBar(previous,normalized))throw new Error(`${symbol} conflicting bar at ${normalized.availableAt}`);
    if(!previous)unique.set(normalized.availableAt,normalized);
  });
  return [...unique.values()].sort((a,b)=>a.availableAtMs-b.availableAtMs||a.timestampMs-b.timestampMs);
}

function trueRange(bar,previousClose){return Math.max(bar.high-bar.low,Math.abs(bar.high-previousClose),Math.abs(bar.low-previousClose));}
function average(values){return values.reduce((sum,value)=>sum+value,0)/values.length;}
function barTurnover(bar){return bar.turnover??((bar.high+bar.low+bar.close)/3*bar.volume);}

function vwap(bars){
  const volume=bars.reduce((sum,bar)=>sum+bar.volume,0);
  return volume>0?bars.reduce((sum,bar)=>sum+barTurnover(bar),0)/volume:null;
}

function pathEfficiency(bars){
  let path=0;for(let index=1;index<bars.length;index+=1)path+=Math.abs(bars[index].close-bars[index-1].close);
  return path>0?clamp(Math.abs(bars.at(-1).close-bars[0].close)/path):0;
}

function reversalFrequency(bars){
  const directions=[];
  for(let index=1;index<bars.length;index+=1){const direction=Math.sign(bars[index].close-bars[index-1].close);if(direction)directions.push(direction);}
  if(directions.length<2)return 0;
  let reversals=0;for(let index=1;index<directions.length;index+=1)if(directions[index]!==directions[index-1])reversals+=1;
  return reversals/(directions.length-1);
}

function rawFeature(entry,cutoffMs){
  for(const key of FORBIDDEN_KEYS)if(Object.prototype.hasOwnProperty.call(entry??{},key))throw new Error(`${symbolOf(entry?.symbol)||'entry'} contains forbidden ${key} input`);
  const symbol=symbolOf(entry?.symbol);
  if(!symbol)throw new Error('Minimal Hybrid entry requires symbol');
  const bars=normalizeBars(entry?.bars,{symbol}).filter(bar=>bar.availableAtMs<=cutoffMs);
  if(bars.length<12)return {symbol,status:'INELIGIBLE',reason:'INSUFFICIENT_CLOSED_5M_BARS'};
  const current=bars.at(-1);
  if(cutoffMs-current.availableAtMs>5*60_000)return {symbol,status:'INELIGIBLE',reason:'STALE_LATEST_5M_BAR'};
  const sessionBars=bars.filter(bar=>bar.sessionDate===current.sessionDate);
  const segmentBars=sessionBars.filter(bar=>bar.segment===current.segment);
  if(segmentBars.length<6)return {symbol,status:'INELIGIBLE',reason:'INSUFFICIENT_CURRENT_SEGMENT_5M_BARS'};
  const recent=segmentBars.slice(-6),previous=recent.slice(0,3),latest=recent.slice(3);
  const atrBars=bars.slice(-12);
  const atr=average(atrBars.map((bar,index)=>{
    const absoluteIndex=bars.length-atrBars.length+index;
    return trueRange(bar,absoluteIndex>0?bars[absoluteIndex-1].close:bar.open);
  }));
  if(!(atr>0))return {symbol,status:'INELIGIBLE',reason:'NON_POSITIVE_ATR'};
  const currentPrice=current.close,atrPct=atr/currentPrice;
  const cumulativeVolume=sessionBars.reduce((sum,bar)=>sum+bar.volume,0);
  const cumulativeTurnover=sessionBars.reduce((sum,bar)=>sum+barTurnover(bar),0);
  const priorVolume=average(previous.map(bar=>bar.volume));
  const currentVolume=average(latest.map(bar=>bar.volume));
  const relativeActivity=priorVolume>0?currentVolume/priorVolume:null;
  const previousMa=average(previous.map(bar=>bar.close)),latestMa=average(latest.map(bar=>bar.close));
  const previousVwap=vwap(previous),latestVwap=vwap(latest),sessionVwap=vwap(sessionBars);
  if(!finite(relativeActivity)||!finite(previousVwap)||!finite(latestVwap)||!finite(sessionVwap)||!(cumulativeTurnover>0)||!(cumulativeVolume>0))return {symbol,status:'INELIGIBLE',reason:'MISSING_ACTIVITY_OR_VWAP'};
  const previousReturn=previous.at(-1).close/previous[0].open-1;
  const latestReturn=latest.at(-1).close/latest[0].open-1;
  const intradayHigh=Math.max(...sessionBars.map(bar=>bar.high)),intradayLow=Math.min(...sessionBars.map(bar=>bar.low));
  const range=intradayHigh-intradayLow;
  return {
    symbol,status:'ELIGIBLE',sector:sectorOf(entry?.sector),market:entry?.market??null,
    sessionDate:current.sessionDate,featureTimestamp:current.availableAt,currentPrice,
    cumulativeVolume,cumulativeTurnover,turnoverSource:sessionBars.every(bar=>bar.turnover!==null)?'OBSERVED':'OHLCV_CAUSAL_PROXY',
    atr,atrPct,relativeActivity,
    recentAbsoluteMovementAtr:Math.abs(currentPrice/recent[0].open-1)/atrPct,
    maSlopeAtr:(latestMa-previousMa)/atr,
    vwapSlopeAtr:(latestVwap-previousVwap)/atr,
    momentumAccelerationAtr:(latestReturn-previousReturn)/atrPct,
    pathEfficiency:pathEfficiency(recent),reversalFrequency:reversalFrequency(recent),
    extensionAtr:Math.abs(currentPrice-sessionVwap)/atr,
    intradayRangePosition:range>0?clamp((currentPrice-intradayLow)/range):0.5,
    returnFromSessionOpen:currentPrice/sessionBars[0].open-1,
  };
}

function percentileRanks(rows,valueOf){
  const values=rows.map((row,index)=>({index,value:Number(valueOf(row))})).sort((a,b)=>a.value-b.value||a.index-b.index);
  const ranks=Array(rows.length).fill(0);
  if(values.length===1){ranks[values[0].index]=1;return ranks;}
  let start=0;while(start<values.length){let end=start;while(end+1<values.length&&values[end+1].value===values[start].value)end+=1;const rank=((start+end)/2)/(values.length-1);for(let index=start;index<=end;index+=1)ranks[values[index].index]=rank;start=end+1;}
  return ranks;
}

function stage1SnapshotEntry(entry,cutoffMs){
  const symbol=symbolOf(entry?.symbol);if(!symbol)throw new Error('Minimal Hybrid entry requires symbol');
  const bars=normalizeBars(entry?.bars,{symbol}).filter(bar=>bar.availableAtMs<=cutoffMs);
  if(!bars.length)return null;
  const current=bars.at(-1),sessionBars=bars.filter(bar=>bar.sessionDate===current.sessionDate);
  if(!sessionBars.length)return null;
  return {symbol,sector:sectorOf(entry?.sector),market:entry?.market??null,status:'analyzed',scannedAt:new Date(cutoffMs).toISOString(),
    currentPrice:current.close,volume:sessionBars.reduce((sum,bar)=>sum+bar.volume,0),dailyChangePercent:(current.close/sessionBars[0].open-1)*100};
}

export function extractPhase57MinimalHybridFeatures({featureCutoff,entries=[]}={}){
  const cutoff=timeMs(featureCutoff,'featureCutoff');
  if(!Array.isArray(entries))throw new TypeError('entries must be an array');
  const seen=new Set(),raw=[],rejected=[];
  for(const entry of entries){
    const symbol=symbolOf(entry?.symbol);if(!symbol)throw new Error('Minimal Hybrid entry requires symbol');if(seen.has(symbol))throw new Error(`duplicate Minimal Hybrid symbol ${symbol}`);seen.add(symbol);
    const row=rawFeature(entry,cutoff);if(row.status==='ELIGIBLE')raw.push(row);else rejected.push(row);
  }
  if(!raw.length)return deepFreeze({status:'MINIMAL_HYBRID_NO_ELIGIBLE_FEATURE_ROWS',featureCutoff:new Date(cutoff).toISOString(),rankedFeatures:[],rejected});
  const turnoverRanks=percentileRanks(raw,row=>row.cumulativeTurnover);
  const marketBreadth=raw.filter(row=>row.returnFromSessionOpen>0).length/raw.length;
  const sectors=new Map();for(const row of raw){if(!sectors.has(row.sector))sectors.set(row.sector,[]);sectors.get(row.sector).push(row);}
  const rankedFeatures=raw.map((row,index)=>{
    const sectorRows=sectors.get(row.sector);
    const sectorBreadth=sectorRows.filter(item=>item.returnFromSessionOpen>0).length/sectorRows.length;
    const normalizedExtension=clamp(row.extensionAtr/3);
    const features={
      turnoverRank:turnoverRanks[index],relativeActivity:row.relativeActivity,
      recentAbsoluteMovementAtr:row.recentAbsoluteMovementAtr,
      maSlopeAtr:row.maSlopeAtr,vwapSlopeAtr:row.vwapSlopeAtr,
      momentumAccelerationAtr:row.momentumAccelerationAtr,
      pathEfficiency:row.pathEfficiency,reversalFrequency:row.reversalFrequency,
      extensionPersistenceInteraction:normalizedExtension*row.pathEfficiency,
      extensionReversalInteraction:normalizedExtension*row.reversalFrequency,
      marketBreadth,sectorBreadth,
    };
    return {...row,features,featureAvailability:Object.fromEntries(Object.keys(features).map(name=>[name,Number.isFinite(features[name])])),microstructure:null,microstructureStatus:'EXCLUDED_FROM_MINIMAL'};
  });
  return deepFreeze({
    phase:'57.selector-minimal-hybrid.features',status:'MINIMAL_HYBRID_5M_FEATURES_READY',
    featureCutoff:new Date(cutoff).toISOString(),inputCount:entries.length,eligibleCount:rankedFeatures.length,rejectedCount:rejected.length,
    rankedFeatures,rejected,
    methodology:{
      fiveMinuteOnly:true,futureBarsUsed:false,missingToZero:false,microstructureUsed:false,
      rawExtensionUsedAsDirectPenalty:false,conditionalExtensionInteractionsOnly:true,lunchSegmentsNotBridged:true,
    },safety:PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY,
  });
}

function stableEvidence(value){return createHash('sha256').update(JSON.stringify(value)).digest('hex');}

export function runPhase57MinimalHybrid({featureCutoff,entries=[],model,baselineDiagnostics={}}={}){
  if(model?.status!=='MINIMAL_HYBRID_MULTI_TARGET_MODEL_READY')throw new Error('Minimal Hybrid inference requires a ready multi-target model');
  if(model.guards?.directExtensionCoefficientAllowed!==false||model.guards?.v3MembershipOrThresholdUsed!==false||model.guards?.microstructureUsed!==false)throw new Error('model violates Minimal Hybrid architecture guards');
  const cutoffMs=timeMs(featureCutoff,'featureCutoff');
  const snapshotEntries=entries.map(entry=>stage1SnapshotEntry(entry,cutoffMs)).filter(Boolean);
  const stage1=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf:featureCutoff,entries:snapshotEntries}]});
  const v1Rows=stage1.points[0]?.rawUniverse??[];
  const v1Set=new Set(v1Rows.map(row=>row.symbol));
  const featureResult=extractPhase57MinimalHybridFeatures({featureCutoff,entries:entries.filter(entry=>v1Set.has(symbolOf(entry?.symbol)))});
  const bySymbol=new Map(featureResult.rankedFeatures.map(row=>[row.symbol,row]));
  const maximumAdjustment=model.selectionPolicy.maximumAbsoluteSoftAdjustment;
  const ranked=v1Rows.flatMap((row,index)=>{
    const featureRow=bySymbol.get(row.symbol);
    if(!featureRow)return [];
    const inference=predictPhase57MinimalHybridTargets({model,features:featureRow?.features});
    const adjustment=(inference.remainingOpportunityScore-0.5)*2*maximumAdjustment;
    return {
      symbol:row.symbol,sector:row.sector,market:row.market,currentPrice:row.currentPrice,
      v1Rank:index+1,v1BaseScore:row.opportunityScore,
      stage2:inference,softAdjustment:round8(adjustment),
      hybridScore:round8(clamp(row.opportunityScore+adjustment)),
      features:featureRow.features,
      diagnostics:{
        extensionAtr:round8(featureRow.extensionAtr),intradayRangePosition:round8(featureRow.intradayRangePosition),
        turnoverSource:featureRow.turnoverSource,microstructureStatus:featureRow.microstructureStatus,
      },
    };
  }).sort((a,b)=>b.hybridScore-a.hybridScore||a.v1Rank-b.v1Rank||a.symbol.localeCompare(b.symbol))
    .map((row,index)=>({...row,hybridRank:index+1}));
  const qualified=ranked.filter(row=>row.stage2.remainingOpportunityScore>=model.selectionPolicy.minimumRemainingOpportunityScore);
  const selected=qualified.slice(0,model.selectionPolicy.maximumSelected);
  const v1Symbols=v1Rows.map(row=>row.symbol),hybridSymbols=selected.map(row=>row.symbol);
  const v3Symbols=Array.isArray(baselineDiagnostics.v3SelectedSymbols)?baselineDiagnostics.v3SelectedSymbols.map(symbolOf).filter(Boolean):null;
  const v3Set=new Set(v3Symbols??[]);
  const evidenceCore={
    phase:'57.selector-minimal-hybrid.evidence',featureCutoff:new Date(timeMs(featureCutoff,'featureCutoff')).toISOString(),
    modelDigest:model.modelDigest,
    v1SelectedCount:v1Rows.length,v3SelectedCount:v3Symbols?.length??null,hybridSelectedCount:selected.length,
    v1HybridOverlap:hybridSymbols.filter(symbol=>v1Set.has(symbol)).length,
    hybridV3Overlap:v3Symbols?hybridSymbols.filter(symbol=>v3Set.has(symbol)).length:null,
    hybridAllFromV1BroadRecall:hybridSymbols.every(symbol=>v1Set.has(symbol)),
    hybridRankChangedFromV1:ranked.some(row=>row.hybridRank!==row.v1Rank),
    hybridIdenticalToV1:v1Rows.length===selected.length&&v1Symbols.every((symbol,index)=>hybridSymbols[index]===symbol),
    hybridExtinct:selected.length===0,
    baselineDiagnosticsUsedForHybrid:false,
    performanceEvaluated:false,performanceClaimAllowed:false,
  };
  const evidence=deepFreeze({...evidenceCore,evidenceSha256:stableEvidence(evidenceCore)});
  return deepFreeze({
    phase:'57.selector-v1-v3-minimal-hybrid',
    status:selected.length?'MINIMAL_HYBRID_SELECTION_READY':'MINIMAL_HYBRID_SOFT_ABSTAIN',
    featureCutoff:new Date(timeMs(featureCutoff,'featureCutoff')).toISOString(),
    modelDigest:model.modelDigest,
    v1CandidateCount:v1Rows.length,eligibleStage2Count:ranked.length,dynamicN:selected.length,
    ranked,selected,
    rejected:featureResult.rejected,
    evidence,
    methodology:{
      v1BroadRecallPreserved:true,v3MembershipRequired:false,v3ThresholdUsed:false,
      stage2HardRejectUsed:false,softRankAdjustmentUsed:true,directExtensionPenaltyUsed:false,
      upDownMultiTargetUsed:true,fiveMinuteOnly:true,microstructureUsed:false,
      entryDirectionUsed:false,entryTimingUsed:false,exitLogicUsed:false,positionSizingUsed:false,
      futureOutcomeUsedForInference:false,automaticPromotionAllowed:false,
    },
    safety:PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY,
  });
}

export default {
  extractPhase57MinimalHybridFeatures,runPhase57MinimalHybrid,
  PHASE57_SELECTOR_MINIMAL_HYBRID_AMENDMENT,PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY,
};
