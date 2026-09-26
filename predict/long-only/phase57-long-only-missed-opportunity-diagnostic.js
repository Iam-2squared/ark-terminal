import {createHash} from 'node:crypto';

export const MISSED_OPPORTUNITY_DIAGNOSTIC_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_MISSED_OPPORTUNITY_DIAGNOSTIC_V1',
  evaluationPartition:'DEVELOPMENT_D',
  scoreState:'CANDIDATE_V1_FIXED_RIDGE_SCORE',
  horizonBars:6,
  barSemantics:'SIX_CLOSED_FIVE_MINUTE_BARS_EQUALS_30_TRADING_MINUTES',
  topReference:20,
  missedRankFloor:101,
  retrainingAllowed:false,
  targetChangeAllowed:false,
  validationAllowed:false,
  oosAllowed:false,
});

export const CONTRAST_FEATURES=Object.freeze([
  'currentReturnPct','momentum5Pct','momentum15Pct','momentum30Pct','momentumAccelerationPct',
  'vwapSlope15Pct','vwapDistancePct','relativeVolumePercentile','volumeAccelerationRatio',
  'rangeExpansionPct','trendEfficiency','pullbackDepthPct','decisionVolatilityPct',
  'marketBreadthPositivePct','sectorBreadthPositivePct','gapPct',
]);

const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const pointKey=row=>`${row.sessionDate}|${row.decisionTimeJst}`;
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const round=value=>Number.isFinite(value)?Number(value.toFixed(8)):value;
const mean=values=>values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;
const quantile=(values,p)=>{if(!values.length)return null;const sorted=[...values].sort((a,b)=>a-b),position=(sorted.length-1)*p,low=Math.floor(position),high=Math.ceil(position);return sorted[low]+(sorted[high]-sorted[low])*(position-low);};
const variance=values=>{const average=mean(values);return values.length?mean(values.map(value=>(value-average)**2)):null;};
const numericSummary=values=>{const xs=values.map(Number).filter(Number.isFinite);return Object.freeze({n:xs.length,mean:round(mean(xs)),median:round(quantile(xs,0.5)),p25:round(quantile(xs,0.25)),p75:round(quantile(xs,0.75))});};
const categoricalSummary=(rows,field)=>{const counts={};for(const row of rows){const value=String(row.feature[field]??'UNKNOWN');counts[value]=(counts[value]??0)+1;}return Object.freeze(Object.fromEntries(Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(([value,count])=>[value,{count,pct:round(rows.length?100*count/rows.length:0)}])));};
const hash=value=>createHash('sha256').update(value).digest('hex');

function percentileRanks(rows,valueOf){
  const values=rows.map((row,index)=>({index,value:Number(valueOf(row))})).filter(row=>Number.isFinite(row.value)).sort((a,b)=>a.value-b.value||a.index-b.index),out=Array(rows.length).fill(null);
  if(values.length===1){out[values[0].index]=100;return out;}
  for(let start=0;start<values.length;){let end=start;while(end+1<values.length&&values[end+1].value===values[start].value)end++;const percentile=100*((start+end)/2)/(values.length-1);for(let i=start;i<=end;i++)out[values[i].index]=percentile;start=end+1;}
  return out;
}

export function addDiagnosticPercentiles(ranked=[]){
  const groups=new Map();for(const row of ranked){const k=pointKey(row.feature);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row);}
  const out=[];
  const definitions={
    currentReturnPct:'currentReturnPct',momentum5Pct:'momentum5Pct',momentum30Pct:'momentum30Pct',
    momentumAccelerationPct:'momentumAccelerationPct',cumulativeVolume:'cumulativeVolume',volumeAccelerationRatio:'volumeAccelerationRatio',
    vwapSlope15Pct:'vwapSlope15Pct',vwapDistancePct:'vwapDistancePct',pullbackDepthPct:'pullbackDepthPct',
    decisionVolatilityPct:'decisionVolatilityPct',marketBreadthPositivePct:'marketBreadthPositivePct',sectorBreadthPositivePct:'sectorBreadthPositivePct',
  };
  for(const rows of groups.values()){
    const ranks=Object.fromEntries(Object.entries(definitions).map(([name,field])=>[name,percentileRanks(rows,row=>row.feature[field])]));
    rows.forEach((row,index)=>out.push(Object.freeze({...row,diagnostic:Object.freeze({...row.diagnostic,...Object.fromEntries(Object.entries(ranks).map(([name,values])=>[`${name}Percentile`,values[index]])),relativeVolumePercentile:ranks.cumulativeVolume[index]})})));
  }
  return Object.freeze(out);
}

function matchedOrdinaryControl(ranked,missed100){
  const wanted=new Map();for(const row of missed100){const k=pointKey(row.feature);wanted.set(k,(wanted.get(k)??0)+1);}
  const groups=new Map();for(const row of ranked){if(row.rank<=20||Number(row.target.y30Bps)>=50)continue;const k=pointKey(row.feature);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row);}
  const selected=[];for(const [k,count] of wanted){const rows=(groups.get(k)??[]).sort((a,b)=>hash(key(a.feature)).localeCompare(hash(key(b.feature))));selected.push(...rows.slice(0,count));}
  return Object.freeze(selected);
}

export function buildDiagnosticCohorts(ranked=[]){
  const top20=ranked.filter(row=>row.rank<=20),missed100=ranked.filter(row=>row.rank>=101&&Number(row.target.y30Bps)>=100),missed200=ranked.filter(row=>row.rank>=101&&Number(row.target.y30Bps)>=200);
  return Object.freeze({RIDGE_TOP20:Object.freeze(top20),MISSED_100_RANK101_PLUS:Object.freeze(missed100),MISSED_200_RANK101_PLUS:Object.freeze(missed200),ORDINARY_MATCHED_CONTROL:matchedOrdinaryControl(ranked,missed100)});
}

function summarizeCohort(rows){
  const featureSummary=Object.fromEntries(CONTRAST_FEATURES.map(field=>[field,numericSummary(rows.map(row=>field==='relativeVolumePercentile'?row.diagnostic?.relativeVolumePercentile:row.feature[field]))]));
  return Object.freeze({
    n:rows.length,features:Object.freeze(featureSummary),vwapReclaim5mPct:round(rows.length?100*rows.filter(row=>row.feature.vwapReclaim5m===true).length/rows.length:0),
    realized30mBps:numericSummary(rows.map(row=>row.target.y30Bps)),futureMfe30Pct:numericSummary(rows.map(row=>row.target.futureMfe30Pct)),futureMae30Pct:numericSummary(rows.map(row=>row.target.futureMae30Pct)),timeToMfe30Minutes:numericSummary(rows.map(row=>row.target.timeToMfe30Minutes)),
    market:categoricalSummary(rows,'segment'),liquidity:categoricalSummary(rows,'liquidityBucket'),gap:categoricalSummary(rows,'gapBucket'),timeOfDay:categoricalSummary(rows,'decisionTimeJst'),
  });
}

function effect(left,right,field){
  const values=(rows)=>rows.map(row=>Number(field==='relativeVolumePercentile'?row.diagnostic?.relativeVolumePercentile:row.feature[field])).filter(Number.isFinite),a=values(left),b=values(right),pooled=Math.sqrt(((variance(a)??0)+(variance(b)??0))/2),meanDifference=mean(a)-mean(b);
  return Object.freeze({meanDifference:round(meanDifference),medianDifference:round(quantile(a,0.5)-quantile(b,0.5)),standardizedMeanDifference:round(pooled?meanDifference/pooled:null)});
}

export function buildFeatureContrast(cohorts={}){
  const summaries=Object.fromEntries(Object.entries(cohorts).map(([name,rows])=>[name,summarizeCohort(rows)]));
  const pairs={TOP20_VS_MISSED100:['RIDGE_TOP20','MISSED_100_RANK101_PLUS'],TOP20_VS_MISSED200:['RIDGE_TOP20','MISSED_200_RANK101_PLUS'],MISSED100_VS_CONTROL:['MISSED_100_RANK101_PLUS','ORDINARY_MATCHED_CONTROL'],MISSED200_VS_CONTROL:['MISSED_200_RANK101_PLUS','ORDINARY_MATCHED_CONTROL']};
  const effects=Object.fromEntries(Object.entries(pairs).map(([name,[left,right]])=>[name,Object.fromEntries(CONTRAST_FEATURES.map(field=>[field,effect(cohorts[left]??[],cohorts[right]??[],field)]))]));
  return Object.freeze({cohorts:Object.freeze(summaries),effects:Object.freeze(effects)});
}

function archetypeMatches(row){
  const p=row.diagnostic??{},feature=row.feature,momentum=p.momentum30PctPercentile,weakMomentum=finite(momentum)&&momentum<=60;
  return Object.freeze({
    PRE_BREAKOUT_VOLUME_LED:weakMomentum&&(p.relativeVolumePercentile>=80||p.volumeAccelerationRatioPercentile>=80),
    VWAP_RECLAIM:feature.vwapReclaim5m===true,
    PULLBACK_CONTINUATION:p.currentReturnPctPercentile>=60&&p.pullbackDepthPctPercentile<=20&&p.momentum5PctPercentile<=50,
    SECTOR_BREADTH_LED:weakMomentum&&p.sectorBreadthPositivePctPercentile>=80,
    HIGH_VOL_ACCELERATION:p.decisionVolatilityPctPercentile>=80&&p.momentumAccelerationPctPercentile>=80,
    VWAP_LED_WEAK_PRICE:weakMomentum&&(p.vwapSlope15PctPercentile>=80||p.vwapDistancePctPercentile>=70),
    GAP_DOWN_RECOVERY:Number(feature.gapPct)<0&&Number(feature.currentReturnPct)>0,
  });
}

const ARCHETYPE_PRIORITY=Object.freeze(['VWAP_RECLAIM','PULLBACK_CONTINUATION','PRE_BREAKOUT_VOLUME_LED','SECTOR_BREADTH_LED','HIGH_VOL_ACCELERATION','VWAP_LED_WEAK_PRICE','GAP_DOWN_RECOVERY']);
function summarizeArchetype(rows,total){
  return Object.freeze({count:rows.length,pctOfMissed:round(total?100*rows.length/total:0),realized30mBps:numericSummary(rows.map(row=>row.target.y30Bps)),futureMfe30Pct:numericSummary(rows.map(row=>row.target.futureMfe30Pct)),futureMae30Pct:numericSummary(rows.map(row=>row.target.futureMae30Pct)),timeToMfe30Minutes:numericSummary(rows.map(row=>row.target.timeToMfe30Minutes)),medianRidgeRank:round(quantile(rows.map(row=>row.rank),0.5)),market:categoricalSummary(rows,'segment'),liquidity:categoricalSummary(rows,'liquidityBucket'),timeOfDay:categoricalSummary(rows,'decisionTimeJst')});
}

function classifyArchetypes(rows){
  const exclusive=new Map([...ARCHETYPE_PRIORITY,'OTHER_UNCLASSIFIED'].map(name=>[name,[]])),overlapping=new Map(ARCHETYPE_PRIORITY.map(name=>[name,[]]));
  for(const row of rows){const matches=archetypeMatches(row);for(const name of ARCHETYPE_PRIORITY)if(matches[name])overlapping.get(name).push(row);exclusive.get(ARCHETYPE_PRIORITY.find(name=>matches[name])??'OTHER_UNCLASSIFIED').push(row);}
  return Object.freeze({thresholds:'WITHIN_DECISION_CROSS_SECTION_FIXED_PERCENTILES_ONLY',exclusive:Object.freeze(Object.fromEntries([...exclusive].map(([name,items])=>[name,summarizeArchetype(items,rows.length)]))),overlapping:Object.freeze(Object.fromEntries([...overlapping].map(([name,items])=>[name,summarizeArchetype(items,rows.length)])))});
}

export function buildArchetypeDistribution(cohorts={}){
  return Object.freeze({GE_100_BPS:classifyArchetypes(cohorts.MISSED_100_RANK101_PLUS??[]),GE_200_BPS:classifyArchetypes(cohorts.MISSED_200_RANK101_PLUS??[])});
}

export function buildEndpointMfeDiagnostic(ranked=[],cohorts={}){
  const rank101=ranked.filter(row=>row.rank>=101),largeMfe=rank101.filter(row=>Number(row.target.futureMfe30Pct)>=2),reverted=largeMfe.filter(row=>Number(row.target.y30Bps)<50);
  const summary=rows=>Object.freeze({n:rows.length,endpointReturnBps:numericSummary(rows.map(row=>row.target.y30Bps)),futureMfePct:numericSummary(rows.map(row=>row.target.futureMfe30Pct)),mfeLessEndpointBps:numericSummary(rows.map(row=>100*Number(row.target.futureMfe30Pct)-Number(row.target.y30Bps))),timeToMfeMinutes:numericSummary(rows.map(row=>row.target.timeToMfe30Minutes))});
  return Object.freeze({missed100:summary(cohorts.MISSED_100_RANK101_PLUS??[]),missed200:summary(cohorts.MISSED_200_RANK101_PLUS??[]),largeMfeRank101:{...summary(largeMfe),revertedBelow50Bps:reverted.length,revertedPct:round(largeMfe.length?100*reverted.length/largeMfe.length:0)}});
}

export function buildVolatilityDiagnostic(ranked=[]){
  const bands=[['BOTTOM_20',0,20],['P20_TO_40',20,40],['P40_TO_60',40,60],['P60_TO_80',60,80],['TOP_20',80,100]];
  return Object.freeze(Object.fromEntries(bands.map(([name,low,high])=>{const rows=ranked.filter(row=>{const value=row.diagnostic?.decisionVolatilityPctPercentile;return finite(value)&&value>=low&&(high===100?value<=high:value<high);});return [name,{n:rows.length,meanReturnBps:round(mean(rows.map(row=>Number(row.target.y30Bps)))),positiveRatePct:round(rows.length?100*rows.filter(row=>Number(row.target.y30Bps)>0).length/rows.length:0),opportunity100RatePct:round(rows.length?100*rows.filter(row=>Number(row.target.y30Bps)>=100).length/rows.length:0),opportunity200RatePct:round(rows.length?100*rows.filter(row=>Number(row.target.y30Bps)>=200).length/rows.length:0),futureMfePct:round(mean(rows.map(row=>Number(row.target.futureMfe30Pct)).filter(Number.isFinite))),futureMaePct:round(mean(rows.map(row=>Number(row.target.futureMae30Pct)).filter(Number.isFinite)))}];})));
}

function pearson(a,b){if(a.length<2||a.length!==b.length)return null;const ma=mean(a),mb=mean(b),num=a.reduce((sum,value,index)=>sum+(value-ma)*(b[index]-mb),0),da=Math.sqrt(a.reduce((sum,value)=>sum+(value-ma)**2,0)),db=Math.sqrt(b.reduce((sum,value)=>sum+(value-mb)**2,0));return da&&db?num/(da*db):null;}
function averagePerDecisionRankCorrelation(ranked,oldRows){
  const old=new Map(oldRows.map(row=>[key(row),row])),groups=new Map();for(const row of ranked){const match=old.get(key(row.feature));if(!match||!finite(match.selectorRank))continue;const k=pointKey(row.feature);if(!groups.has(k))groups.set(k,[]);groups.get(k).push([row.rank,Number(match.selectorRank)]);}
  const values=[...groups.values()].map(rows=>pearson(rows.map(row=>row[0]),rows.map(row=>row[1]))).filter(Number.isFinite);return {meanPerDecision:round(mean(values)),decisionCount:values.length};
}

export function buildOldSelectorComplementarity(ranked=[],cohorts={},oldSelectors={}){
  return Object.freeze(Object.fromEntries(Object.entries(oldSelectors).map(([name,value])=>{
    if(value?.status!=='AVAILABLE')return [name,{status:'UNAVAILABLE',reason:value?.reason??'FORMAL_RANKING_NOT_AVAILABLE'}];
    const selectedRows=value.selectedRows??value.rows??value.rankedRows??[],rankedRows=value.rankedRows??value.rows??selectedRows,selectedMap=new Map(selectedRows.map(row=>[key(row),row])),cohortSummary=rows=>{const caught=rows.filter(row=>selectedMap.has(key(row.feature))),ranks=caught.map(row=>Number(selectedMap.get(key(row.feature)).selectorRank)).filter(Number.isFinite);return {missedCount:rows.length,caughtCount:caught.length,recallPct:round(rows.length?100*caught.length/rows.length:0),medianOldSelectorRank:round(quantile(ranks,0.5))};};
    return [name,{status:'AVAILABLE',nativeSelectionRows:selectedRows.length,rankCoverageRows:rankedRows.length,newRidgeRankCorrelation:averagePerDecisionRankCorrelation(ranked,rankedRows),missed100:cohortSummary(cohorts.MISSED_100_RANK101_PLUS??[]),missed200:cohortSummary(cohorts.MISSED_200_RANK101_PLUS??[])}];
  })));
}

export function diagnoseMissedOpportunities({ranked=[],oldSelectors={}}={}){
  const decorated=addDiagnosticPercentiles(ranked),cohorts=buildDiagnosticCohorts(decorated);
  return Object.freeze({contract:MISSED_OPPORTUNITY_DIAGNOSTIC_CONTRACT,featureContrast:buildFeatureContrast(cohorts),archetypes:buildArchetypeDistribution(cohorts),endpointVsMfe:buildEndpointMfeDiagnostic(decorated,cohorts),volatility:buildVolatilityDiagnostic(decorated),oldSelectorComplementarity:buildOldSelectorComplementarity(decorated,cohorts,oldSelectors)});
}

export default {addDiagnosticPercentiles,buildDiagnosticCohorts,buildFeatureContrast,buildArchetypeDistribution,buildEndpointMfeDiagnostic,buildVolatilityDiagnostic,buildOldSelectorComplementarity,diagnoseMissedOpportunities};
