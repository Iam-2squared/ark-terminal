export const PHASE57_P25_SAFETY=Object.freeze({
  phase:'57.p25.jpx-opportunity-universe',
  mode:'READ_ONLY_POINT_IN_TIME_RESEARCH_UNIVERSE',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_P25_POLICY=Object.freeze({
  sourceScope:'JPX_DOMESTIC_PRIME_STANDARD_GROWTH',
  defaultDayCount:30,
  defaultSwingCount:30,
  defaultMaxCombinedCount:50,
  defaultMaxPerSector:4,
  pointInTimeOnly:true,
  futureOutcomeSelectionAllowed:false,
  outcomeDrivenWinnerFilteringAllowed:false,
  thresholdSearchAllowed:false,
  postHocSymbolFilteringAllowed:false,
  selectionDirection:'DIRECTION_AGNOSTIC_OPPORTUNITY_STRENGTH',
});

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const clamp=(value,min=0,max=1)=>Math.min(max,Math.max(min,Number(value)));
const symbolOf=row=>String(row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.sector??'未分類').trim()||'未分類';

function percentileRanks(rows,valueOf){
  const values=rows.map((row,index)=>({index,value:Number(valueOf(row))})).filter(x=>Number.isFinite(x.value));
  values.sort((a,b)=>a.value-b.value||a.index-b.index);
  const ranks=new Array(rows.length).fill(0);
  if(!values.length)return ranks;
  if(values.length===1){ranks[values[0].index]=1;return ranks;}
  let start=0;
  while(start<values.length){
    let end=start;
    while(end+1<values.length&&values[end+1].value===values[start].value)end+=1;
    const rank=((start+end)/2)/(values.length-1);
    for(let i=start;i<=end;i+=1)ranks[values[i].index]=rank;
    start=end+1;
  }
  return ranks;
}

function normalizedConviction(value){
  if(!finite(value))return 0;
  return Math.abs(Number(value)-50);
}

function normalizedConfidence(value){
  if(!finite(value))return 0;
  const n=Number(value);
  return n<=1?n*100:n;
}

function pointInTimeEligible(row,{asOfMs,maxAgeMs}){
  if(!row||typeof row!=='object')return false;
  if(row.status&&row.status!=='analyzed')return false;
  if(!symbolOf(row)||!finite(row.currentPrice)||Number(row.currentPrice)<=0||!finite(row.volume)||Number(row.volume)<=0)return false;
  if(asOfMs===null)return true;
  const scannedMs=Date.parse(row.scannedAt??'');
  if(!Number.isFinite(scannedMs)||scannedMs>asOfMs)return false;
  if(maxAgeMs!==null&&asOfMs-scannedMs>maxAgeMs)return false;
  return true;
}

function enrich(rows){
  return rows.map(row=>({
    ...row,
    _symbol:symbolOf(row),
    _sector:sectorOf(row),
    _turnover:Number(row.currentPrice)*Number(row.volume),
    _volumeRatio:finite(row.volumeRatio)?Math.max(0,Number(row.volumeRatio)):0,
    _absChange:finite(row.dailyChangePercent)?Math.abs(Number(row.dailyChangePercent)):0,
    _atr:finite(row.atrPercent)?Math.max(0,Number(row.atrPercent)):0,
    _discoveryConviction:normalizedConviction(row.discoveryScore),
    _technicalConviction:normalizedConviction(row.technicalScore),
    _confidence:normalizedConfidence(row.confidence),
    _quality:finite(row.qualityScore)?Math.max(0,Number(row.qualityScore)):0,
  }));
}

function score(rows,mode){
  const pTurnover=percentileRanks(rows,r=>r._turnover);
  const pVolumeRatio=percentileRanks(rows,r=>r._volumeRatio);
  const pAbsChange=percentileRanks(rows,r=>r._absChange);
  const pAtr=percentileRanks(rows,r=>r._atr);
  const pDiscovery=percentileRanks(rows,r=>r._discoveryConviction);
  const pTechnical=percentileRanks(rows,r=>r._technicalConviction);
  const pConfidence=percentileRanks(rows,r=>r._confidence);
  const pQuality=percentileRanks(rows,r=>r._quality);
  return rows.map((row,index)=>{
    const dayScore=
      pTurnover[index]*0.30+
      pVolumeRatio[index]*0.20+
      pAbsChange[index]*0.15+
      pAtr[index]*0.10+
      pDiscovery[index]*0.10+
      pTechnical[index]*0.05+
      pConfidence[index]*0.05+
      pQuality[index]*0.05;
    const swingScore=
      pDiscovery[index]*0.30+
      pTechnical[index]*0.25+
      pConfidence[index]*0.15+
      pQuality[index]*0.10+
      pVolumeRatio[index]*0.10+
      pTurnover[index]*0.10;
    const opportunityScore=mode==='DAY'?dayScore:swingScore;
    return Object.freeze({
      symbol:row._symbol,
      sector:row._sector,
      market:row.market??null,
      currentPrice:Number(row.currentPrice),
      turnoverYen:row._turnover,
      volumeRatio:row._volumeRatio,
      absoluteChangePct:row._absChange,
      atrPercent:row._atr,
      opportunityScore:Number(clamp(opportunityScore,0,1).toFixed(6)),
      sourceScannedAt:row.scannedAt??null,
      mode,
    });
  }).sort((a,b)=>b.opportunityScore-a.opportunityScore||b.turnoverYen-a.turnoverYen||a.symbol.localeCompare(b.symbol));
}

function diversify(sorted,count,maxPerSector){
  const selected=[];
  const sectorCounts=new Map();
  for(const row of sorted){
    if(selected.length>=count)break;
    const n=sectorCounts.get(row.sector)??0;
    if(n>=maxPerSector)continue;
    selected.push(row);
    sectorCounts.set(row.sector,n+1);
  }
  return selected;
}

export function selectJpxOpportunityUniverse({
  entries=[],
  dayCount=PHASE57_P25_POLICY.defaultDayCount,
  swingCount=PHASE57_P25_POLICY.defaultSwingCount,
  maxCombinedCount=PHASE57_P25_POLICY.defaultMaxCombinedCount,
  maxPerSector=PHASE57_P25_POLICY.defaultMaxPerSector,
  asOf=null,
  maxAgeMs=null,
}={}){
  const input=Array.isArray(entries)?entries:[];
  const asOfMs=asOf===null?null:Date.parse(asOf);
  if(asOf!==null&&!Number.isFinite(asOfMs))throw new TypeError('asOf must be a valid timestamp');
  if(maxAgeMs!==null&&(!Number.isFinite(Number(maxAgeMs))||Number(maxAgeMs)<0))throw new TypeError('maxAgeMs must be null or non-negative');
  for(const [name,value] of Object.entries({dayCount,swingCount,maxCombinedCount,maxPerSector})){
    if(!Number.isInteger(Number(value))||Number(value)<1)throw new TypeError(`${name} must be a positive integer`);
  }

  const eligible=enrich(input.filter(row=>pointInTimeEligible(row,{asOfMs,maxAgeMs:maxAgeMs===null?null:Number(maxAgeMs)})));
  const day=diversify(score(eligible,'DAY'),Math.min(Number(dayCount),eligible.length),Number(maxPerSector));
  const swing=diversify(score(eligible,'SWING'),Math.min(Number(swingCount),eligible.length),Number(maxPerSector));
  const merged=new Map();
  for(const row of [...day,...swing]){
    const previous=merged.get(row.symbol);
    const modes=new Set(previous?.modes??[]);modes.add(row.mode);
    merged.set(row.symbol,Object.freeze({
      symbol:row.symbol,
      sector:row.sector,
      market:row.market,
      modes:Object.freeze([...modes].sort()),
      opportunityScore:Math.max(previous?.opportunityScore??0,row.opportunityScore),
      turnoverYen:Math.max(previous?.turnoverYen??0,row.turnoverYen),
    }));
  }
  const combined=[...merged.values()].sort((a,b)=>b.opportunityScore-a.opportunityScore||b.turnoverYen-a.turnoverYen||a.symbol.localeCompare(b.symbol)).slice(0,Number(maxCombinedCount));

  return Object.freeze({
    phase:'57.p25.jpx-opportunity-universe',
    status:'JPX_DYNAMIC_RESEARCH_UNIVERSE_READY',
    inputCount:input.length,
    eligibleCount:eligible.length,
    day:Object.freeze(day),
    swing:Object.freeze(swing),
    combined:Object.freeze(combined),
    policy:Object.freeze({...PHASE57_P25_POLICY,dayCount:Number(dayCount),swingCount:Number(swingCount),maxCombinedCount:Number(maxCombinedCount),maxPerSector:Number(maxPerSector),asOf:asOf??null,maxAgeMs:maxAgeMs===null?null:Number(maxAgeMs)}),
    methodology:Object.freeze({
      usesFutureOutcome:false,
      usesTradeResult:false,
      usesOuterOosPerformance:false,
      directionAgnosticOpportunityStrength:true,
      crossSectionalPercentileRanking:true,
      sectorConcentrationCap:true,
      pointInTimeFreshnessGuard:asOf!==null,
    }),
    safety:PHASE57_P25_SAFETY,
  });
}

export default {selectJpxOpportunityUniverse,PHASE57_P25_POLICY,PHASE57_P25_SAFETY};
