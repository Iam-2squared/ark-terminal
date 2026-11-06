import fs from 'node:fs';

const freezeUrl=new URL('../research/phase57-selector-v3-freeze.json',import.meta.url);
const deepFreeze=value=>{
  if(value&&typeof value==='object'&&!Object.isFrozen(value)){
    for(const child of Object.values(value))deepFreeze(child);
    Object.freeze(value);
  }
  return value;
};

export const PHASE57_SELECTOR_V3_FREEZE=deepFreeze(JSON.parse(fs.readFileSync(freezeUrl,'utf8')));
export const PHASE57_SELECTOR_V3_SAFETY=PHASE57_SELECTOR_V3_FREEZE.safety;
export const PHASE57_SELECTOR_V3_POLICY=deepFreeze({
  candidateId:PHASE57_SELECTOR_V3_FREEZE.candidateId,
  researchOnly:true,
  formalOos:false,
  promotionEligible:false,
  winnerSelectionAllowed:false,
  laneYIntegrationAllowed:false,
});

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const clamp=(value,min=0,max=1)=>Math.min(max,Math.max(min,Number(value)));
const symbolOf=value=>String(value??'').trim().toUpperCase();
const sectorOf=value=>String(value??'').trim()||'UNKNOWN';
const round6=value=>Number(Number(value).toFixed(6));

function median(values){
  const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!xs.length)return null;
  const middle=Math.floor(xs.length/2);
  return xs.length%2?xs[middle]:(xs[middle-1]+xs[middle])/2;
}

function percentileRanks(rows,valueOf){
  const values=rows.map((row,index)=>({index,value:Number(valueOf(row))})).filter(item=>Number.isFinite(item.value));
  const ranks=new Array(rows.length).fill(null);
  values.sort((a,b)=>a.value-b.value||a.index-b.index);
  if(values.length===1){ranks[values[0].index]=1;return ranks;}
  let start=0;
  while(start<values.length){
    let end=start;
    while(end+1<values.length&&values[end+1].value===values[start].value)end+=1;
    const rank=values.length?((start+end)/2)/(values.length-1):null;
    for(let index=start;index<=end;index+=1)ranks[values[index].index]=rank;
    start=end+1;
  }
  return ranks;
}

function weightedAvailable(parts){
  let numerator=0,denominator=0;
  for(const {value,weight} of parts){
    if(!Number.isFinite(value))continue;
    numerator+=value*weight;
    denominator+=weight;
  }
  return denominator>0?clamp(numerator/denominator):null;
}

function timeMs(value,label){
  const parsed=Date.parse(String(value??''));
  if(!Number.isFinite(parsed))throw new TypeError(`${label} must be a valid timestamp`);
  return parsed;
}

function normalizeBar(bar,{symbol,index}){
  if(!bar||typeof bar!=='object')throw new TypeError(`${symbol} bar[${index}] must be an object`);
  const timestamp=String(bar.timestamp??'');
  const availableAt=String(bar.availableAt??'');
  const timestampMs=timeMs(timestamp,`${symbol} bar[${index}].timestamp`);
  const availableAtMs=timeMs(availableAt,`${symbol} bar[${index}].availableAt`);
  if(availableAtMs<timestampMs)throw new Error(`${symbol} bar[${index}] availableAt precedes timestamp`);
  const sessionDate=String(bar.sessionDate??'').trim();
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`${symbol} bar[${index}] requires YYYY-MM-DD sessionDate`);
  for(const key of ['open','high','low','close','volume']){
    if(!finite(bar[key]))throw new Error(`${symbol} bar[${index}] missing finite ${key}; missing values cannot be zero-filled`);
  }
  const normalized={
    timestamp,availableAt,timestampMs,availableAtMs,sessionDate,
    open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),volume:Number(bar.volume),
  };
  if(normalized.open<=0||normalized.high<=0||normalized.low<=0||normalized.close<=0)throw new Error(`${symbol} bar[${index}] prices must be positive`);
  if(normalized.volume<0)throw new Error(`${symbol} bar[${index}] volume must be non-negative`);
  if(normalized.high<Math.max(normalized.open,normalized.close,normalized.low)||normalized.low>Math.min(normalized.open,normalized.close,normalized.high)){
    throw new Error(`${symbol} bar[${index}] has invalid OHLC ordering`);
  }
  return normalized;
}

function sameBar(left,right){
  return ['timestamp','availableAt','sessionDate','open','high','low','close','volume'].every(key=>left[key]===right[key]);
}

function normalizeBars(bars,{symbol}){
  if(!Array.isArray(bars))throw new TypeError(`${symbol} bars must be an array`);
  const byAvailableAt=new Map();
  for(let index=0;index<bars.length;index+=1){
    const bar=normalizeBar(bars[index],{symbol,index});
    const previous=byAvailableAt.get(bar.availableAt);
    if(previous&&!sameBar(previous,bar))throw new Error(`${symbol} conflicting duplicate availableAt ${bar.availableAt}`);
    if(!previous)byAvailableAt.set(bar.availableAt,bar);
  }
  return [...byAvailableAt.values()].sort((a,b)=>a.availableAtMs-b.availableAtMs||a.timestampMs-b.timestampMs);
}

function trueRange(bar,previousClose){
  return Math.max(bar.high-bar.low,Math.abs(bar.high-previousClose),Math.abs(bar.low-previousClose));
}

function pathEfficiency(bars,period){
  const start=bars.length-1-period;
  if(start<0)return null;
  let path=0;
  for(let index=start+1;index<bars.length;index+=1)path+=Math.abs(bars[index].close-bars[index-1].close);
  return path>0?clamp(Math.abs(bars.at(-1).close-bars[start].close)/path):0;
}

function consecutiveDirectionRun(bars){
  if(bars.length<2)return 0;
  const lastMove=Math.sign(bars.at(-1).close-bars.at(-2).close);
  if(lastMove===0)return 0;
  let run=0;
  for(let index=bars.length-1;index>0;index-=1){
    const direction=Math.sign(bars[index].close-bars[index-1].close);
    if(direction!==lastMove)break;
    run+=1;
  }
  return run;
}

function extractRawFeature(entry,featureCutoffMs){
  const symbol=symbolOf(entry?.symbol);
  if(!symbol)throw new Error('V3 entry requires symbol');
  const allBars=normalizeBars(entry?.bars,{symbol});
  const bars=allBars.filter(bar=>bar.availableAtMs<=featureCutoffMs);
  const cfg=PHASE57_SELECTOR_V3_FREEZE;
  if(bars.length<cfg.causality.minimumClosedLookbackBars){
    return {symbol,status:'INELIGIBLE',reason:'INSUFFICIENT_CLOSED_LOOKBACK',closedBarCount:bars.length};
  }
  const current=bars.at(-1);
  const sessionBars=bars.filter(bar=>bar.sessionDate===current.sessionDate);
  if(sessionBars.length<cfg.causality.minimumCurrentSessionBars){
    return {symbol,status:'INELIGIBLE',reason:'INSUFFICIENT_CURRENT_SESSION_BARS',closedBarCount:bars.length};
  }
  const lookback=cfg.featureDefinitions.atrLookbackBars;
  const atrBars=bars.slice(-lookback);
  const firstAtrIndex=bars.length-atrBars.length;
  const ranges=atrBars.map((bar,index)=>{
    const absoluteIndex=firstAtrIndex+index;
    const previousClose=absoluteIndex>0?bars[absoluteIndex-1].close:bar.open;
    return trueRange(bar,previousClose);
  });
  const atrPrice=ranges.reduce((sum,value)=>sum+value,0)/ranges.length;
  const close=current.close;
  if(!(atrPrice>0))return {symbol,status:'INELIGIBLE',reason:'NON_POSITIVE_ATR',closedBarCount:bars.length};
  const shortBars=cfg.featureDefinitions.shortReturnBars;
  const mediumBars=cfg.featureDefinitions.mediumReturnBars;
  if(bars.length<=mediumBars)return {symbol,status:'INELIGIBLE',reason:'INSUFFICIENT_RETURN_LOOKBACK',closedBarCount:bars.length};
  const return3=close/bars[bars.length-1-shortBars].close-1;
  const return6=close/bars[bars.length-1-mediumBars].close-1;
  const atrPct=atrPrice/close;
  const sessionVolume=sessionBars.reduce((sum,bar)=>sum+bar.volume,0);
  if(!(sessionVolume>0))return {symbol,status:'INELIGIBLE',reason:'NON_POSITIVE_SESSION_VOLUME',closedBarCount:bars.length};
  const cumulativeTurnoverYen=sessionBars.reduce((sum,bar)=>sum+bar.close*bar.volume,0);
  const turnoverBars=bars.slice(-cfg.featureDefinitions.turnoverMedianBars).map(bar=>bar.close*bar.volume);
  const medianBarTurnoverYen=median(turnoverBars);
  if(!(cumulativeTurnoverYen>0)||!(medianBarTurnoverYen>0)){
    return {symbol,status:'INELIGIBLE',reason:'NON_POSITIVE_TURNOVER',closedBarCount:bars.length};
  }
  const vwapNumerator=sessionBars.reduce((sum,bar)=>sum+((bar.high+bar.low+bar.close)/3)*bar.volume,0);
  const sessionVwap=vwapNumerator/sessionVolume;
  const sessionOpen=sessionBars[0].open;
  const vwapExtensionAtr=Math.abs(close-sessionVwap)/atrPrice;
  const sessionMoveAtr=Math.abs(close/sessionOpen-1)/atrPct;
  const efficiency6=pathEfficiency(bars,mediumBars);
  if(!Number.isFinite(efficiency6)){
    return {symbol,status:'INELIGIBLE',reason:'MISSING_PATH_EFFICIENCY',closedBarCount:bars.length};
  }
  return {
    status:'ELIGIBLE',symbol,sector:sectorOf(entry?.sector),market:entry?.market??null,
    featureTimestamp:current.availableAt,sessionDate:current.sessionDate,currentPrice:close,sessionOpen,sessionVwap,
    closedBarCount:bars.length,currentSessionBarCount:sessionBars.length,
    cumulativeTurnoverYen,medianBarTurnoverYen,atrPrice,atrPct,return3,return6,
    normalizedAbsoluteReturn3:Math.abs(return3)/atrPct,
    normalizedAbsoluteReturn6:Math.abs(return6)/atrPct,
    pathEfficiency6:efficiency6,vwapExtensionAtr,sessionMoveAtr,
    sameDirectionRun:consecutiveDirectionRun(sessionBars),
    preSelectionMove:return3,
  };
}

function breadthAlignment(rows,direction){
  if(direction===0||!rows.length)return 0.5;
  let value=0;
  for(const row of rows){
    const candidateDirection=Math.sign(row.return3);
    if(candidateDirection===0)value+=0.5;
    else if(candidateDirection===direction)value+=1;
  }
  return value/rows.length;
}

function scoreEligibleRows(rows){
  if(!rows.length)return [];
  const cfg=PHASE57_SELECTOR_V3_FREEZE;
  const f=cfg.featureDefinitions;
  const scoreCfg=cfg.score;
  const cumulativeRanks=percentileRanks(rows,row=>row.cumulativeTurnoverYen);
  const barTurnoverRanks=percentileRanks(rows,row=>row.medianBarTurnoverYen);
  const return3Ranks=percentileRanks(rows,row=>row.normalizedAbsoluteReturn3);
  const return6Ranks=percentileRanks(rows,row=>row.normalizedAbsoluteReturn6);
  const sectorGroups=new Map();
  for(const row of rows){
    if(!sectorGroups.has(row.sector))sectorGroups.set(row.sector,[]);
    sectorGroups.get(row.sector).push(row);
  }
  const marketRows=rows;
  return rows.map((row,index)=>{
    const structuralTradability=
      cumulativeRanks[index]*f.structuralTradability.cumulativeTurnoverPercentileWeight+
      barTurnoverRanks[index]*f.structuralTradability.medianBarTurnoverPercentileWeight;
    const momentum=
      return3Ranks[index]*f.momentum.absoluteAtrNormalizedReturn3PercentileWeight+
      return6Ranks[index]*f.momentum.absoluteAtrNormalizedReturn6PercentileWeight+
      row.pathEfficiency6*f.momentum.pathEfficiency6Weight;
    const extensionPenalty=clamp(
      clamp(row.vwapExtensionAtr/f.extensionPenalty.vwapExtensionAtrDivisor)*f.extensionPenalty.vwapExtensionWeight+
      clamp(row.sessionMoveAtr/f.extensionPenalty.sessionMoveAtrDivisor)*f.extensionPenalty.sessionMoveWeight+
      clamp(row.sameDirectionRun/f.extensionPenalty.sameDirectionRunDivisor)*f.extensionPenalty.sameDirectionRunWeight
    );
    const remainingHeadroom=1-extensionPenalty;
    const direction=Math.sign(row.return3);
    const marketBreadthAlignment=breadthAlignment(marketRows,direction);
    const sectorRows=sectorGroups.get(row.sector)??[];
    const sectorContextAvailable=row.sector!=='UNKNOWN'&&sectorRows.length>=f.minimumSectorPeers;
    const sectorBreadthAlignment=sectorContextAvailable?breadthAlignment(sectorRows,direction):null;
    const sectorMedianReturn3=sectorContextAvailable?median(sectorRows.map(item=>item.return3)):null;
    const sectorResidualHeadroom=sectorContextAvailable
      ?1-clamp(Math.abs(row.return3-sectorMedianReturn3)/(4*row.atrPct))
      :null;
    const marketSectorContext=weightedAvailable([
      {value:sectorBreadthAlignment,weight:f.context.sectorBreadthAlignmentWeight},
      {value:marketBreadthAlignment,weight:f.context.marketBreadthAlignmentWeight},
      {value:sectorResidualHeadroom,weight:f.context.sectorResidualHeadroomWeight},
    ]);
    if(!Number.isFinite(marketSectorContext))throw new Error(`${row.symbol} has no available market/sector context`);
    const utilityScore=clamp(
      structuralTradability*scoreCfg.structuralTradabilityWeight+
      momentum*scoreCfg.momentumWeight+
      remainingHeadroom*scoreCfg.remainingHeadroomWeight+
      marketSectorContext*scoreCfg.marketSectorContextWeight
    );
    return deepFreeze({
      ...row,
      structuralTradability:round6(structuralTradability),
      momentum:round6(momentum),
      remainingHeadroom:round6(remainingHeadroom),
      marketSectorContext:round6(marketSectorContext),
      utilityScore:round6(utilityScore),
      components:{
        cumulativeTurnoverPercentile:round6(cumulativeRanks[index]),
        medianBarTurnoverPercentile:round6(barTurnoverRanks[index]),
        absoluteAtrNormalizedReturn3Percentile:round6(return3Ranks[index]),
        absoluteAtrNormalizedReturn6Percentile:round6(return6Ranks[index]),
        pathEfficiency6:round6(row.pathEfficiency6),
        vwapExtensionAtr:round6(row.vwapExtensionAtr),
        sessionMoveAtr:round6(row.sessionMoveAtr),
        sameDirectionRun:row.sameDirectionRun,
        extensionPenalty:round6(extensionPenalty),
        marketBreadthAlignment:round6(marketBreadthAlignment),
        sectorBreadthAlignment:Number.isFinite(sectorBreadthAlignment)?round6(sectorBreadthAlignment):null,
        sectorResidualHeadroom:Number.isFinite(sectorResidualHeadroom)?round6(sectorResidualHeadroom):null,
        sectorContextStatus:sectorContextAvailable?'AVAILABLE':'UNKNOWN_RENORMALIZED',
      },
    });
  }).sort((a,b)=>
    b.utilityScore-a.utilityScore||
    b.structuralTradability-a.structuralTradability||
    b.cumulativeTurnoverYen-a.cumulativeTurnoverYen||
    a.symbol.localeCompare(b.symbol)
  ).map((row,index)=>deepFreeze({...row,rank:index+1}));
}

export function scorePhase57SelectorV3CrossSection({featureCutoff,entries=[]}={}){
  const featureCutoffMs=timeMs(featureCutoff,'featureCutoff');
  if(!Array.isArray(entries))throw new TypeError('entries must be an array');
  const seen=new Set();
  const raw=[];
  const rejected=[];
  for(const entry of entries){
    const symbol=symbolOf(entry?.symbol);
    if(!symbol)throw new Error('V3 entry requires symbol');
    if(seen.has(symbol))throw new Error(`duplicate V3 symbol ${symbol}`);
    seen.add(symbol);
    const result=extractRawFeature(entry,featureCutoffMs);
    if(result.status==='ELIGIBLE')raw.push(result);else rejected.push(result);
  }
  const ranked=scoreEligibleRows(raw);
  return deepFreeze({
    phase:'57.selector-v3.0',
    status:'SELECTOR_V3_CROSS_SECTION_SCORED',
    candidateId:PHASE57_SELECTOR_V3_FREEZE.candidateId,
    featureCutoff:new Date(featureCutoffMs).toISOString(),
    inputCount:entries.length,
    eligibleCount:ranked.length,
    rejectedCount:rejected.length,
    ranked,
    rejected,
    methodology:{
      causalClosedBarsOnly:true,directionAgnostic:true,momentumExtensionSeparated:true,
      missingToZero:false,microstructureArm:'EXCLUDED_FROM_PRIMARY_V3_0',futureOutcomeUsed:false,
      outerOosPerformanceUsed:false,rawScoreIsProbability:false,
    },
    safety:PHASE57_SELECTOR_V3_SAFETY,
  });
}

function allowedThreshold(value){
  return PHASE57_SELECTOR_V3_FREEZE.selection.thresholdCandidates.some(candidate=>Math.abs(candidate-value)<1e-12);
}

export function selectPhase57SelectorV3({featureCutoff,entries=[],threshold=null}={}){
  const scored=scorePhase57SelectorV3CrossSection({featureCutoff,entries});
  if(threshold!==null&&(!finite(threshold)||!allowedThreshold(Number(threshold)))){
    throw new Error('V3 threshold must be null/ABSTAIN or one preregistered candidate');
  }
  const selected=[];
  const sectorCounts=new Map();
  if(threshold!==null){
    for(const row of scored.ranked){
      if(selected.length>=PHASE57_SELECTOR_V3_FREEZE.selection.maximumSelectedPerTimestamp)break;
      if(row.utilityScore<Number(threshold))continue;
      if(row.structuralTradability<PHASE57_SELECTOR_V3_FREEZE.score.minimumStructuralTradability)continue;
      const count=sectorCounts.get(row.sector)??0;
      if(count>=PHASE57_SELECTOR_V3_FREEZE.selection.maximumSelectedPerSector)continue;
      selected.push(row);
      sectorCounts.set(row.sector,count+1);
    }
  }
  return deepFreeze({
    ...scored,
    status:threshold===null?'SELECTOR_V3_ABSTAIN_NO_VALIDATED_THRESHOLD':'SELECTOR_V3_SELECTION_READY',
    threshold,
    selectedCount:selected.length,
    selected,
    fixedCountFillUsed:false,
    persistenceUsed:false,
    policy:PHASE57_SELECTOR_V3_POLICY,
  });
}

export default {
  scorePhase57SelectorV3CrossSection,
  selectPhase57SelectorV3,
  PHASE57_SELECTOR_V3_FREEZE,
  PHASE57_SELECTOR_V3_POLICY,
  PHASE57_SELECTOR_V3_SAFETY,
};

