import {createHash} from 'node:crypto';

const round=value=>Number.isFinite(value)?Number(value.toFixed(6)):null;
const quantile=(values,p)=>{const xs=values.filter(Number.isFinite).sort((a,b)=>a-b);if(!xs.length)return null;const i=(xs.length-1)*p,lo=Math.floor(i),hi=Math.ceil(i);return round(xs[lo]+(xs[hi]-xs[lo])*(i-lo));};
const mean=(rows,key)=>{const xs=rows.map(row=>Number(row[key])).filter(Number.isFinite);return xs.length?round(xs.reduce((sum,x)=>sum+x,0)/xs.length):null;};
const summarize=rows=>Object.freeze({
  observations:rows.length,
  symbols:new Set(rows.map(row=>`${row.sessionDate}|${row.symbol}`)).size,
  winnerRatePct:rows.length?round(100*rows.filter(row=>row.winner).length/rows.length):null,
  largeWinnerRatePct:rows.length?round(100*rows.filter(row=>row.largeWinner).length/rows.length):null,
  meanRemainingUpsidePct:mean(rows,'remainingUpsidePct'),medianRemainingUpsidePct:quantile(rows.map(row=>Number(row.remainingUpsidePct)),.5),
  meanFutureMfePct:mean(rows,'futureMfePct'),meanFutureMaePct:mean(rows,'futureMaePct'),
  meanFutureMfeAtr:mean(rows,'futureMfeAtr'),meanFutureMaeAtr:mean(rows,'futureMaeAtr'),
  meanTimeToWinnerMinutes:mean(rows,'timeToWinnerMinutes'),lateDetectionRatePct:rows.length?round(100*rows.filter(row=>row.lateDetection).length/rows.length):null,
});
const group=(rows,key)=>Object.freeze(Object.fromEntries([...new Set(rows.map(row=>row[key]??'UNKNOWN'))].sort().map(value=>[value,summarize(rows.filter(row=>(row[key]??'UNKNOWN')===value))])));
const returnBucket=value=>value<0?'LT_0':value<1?'0_TO_1':value<2?'1_TO_2':value<3?'2_TO_3':value<5?'3_TO_5':'GTE_5';
const stableHash=value=>createHash('sha256').update(value).digest('hex');

function selectionMetrics(selected,all){
  const winnerIds=new Set(all.filter(row=>row.winner).map(row=>`${row.sessionDate}|${row.symbol}`));
  const selectedWinner=selected.filter(row=>row.winner);
  return Object.freeze({candidateCount:selected.length,winnerRecallPct:winnerIds.size?round(100*new Set(selectedWinner.map(row=>`${row.sessionDate}|${row.symbol}`)).size/winnerIds.size):null,...summarize(selectedWinner)});
}

function causalFeatureDiagnostics(rows){
  const fields=['currentReturnPct','momentum5Pct','momentum15Pct','momentum30Pct','momentumAccelerationPct','volumeAccelerationRatio','vwapDistancePct','vwapSlope15Pct','highBreakoutPct','rangeExpansionPct','trendEfficiency','marketBreadthPositivePct','sectorBreadthPositivePct'];
  const byTime={};
  for(const decisionTimeJst of [...new Set(rows.map(row=>row.decisionTimeJst))].sort()){
    const atTime=rows.filter(row=>row.decisionTimeJst===decisionTimeJst),n=atTime.filter(row=>row.winner).length;
    if(!n){byTime[decisionTimeJst]={winnerCount:0};continue;}
    const random=[...atTime].sort((a,b)=>stableHash(`${decisionTimeJst}|${a.sessionDate}|${a.symbol}`).localeCompare(stableHash(`${decisionTimeJst}|${b.sessionDate}|${b.symbol}`))).slice(0,n);
    const features={};
    for(const field of fields){
      const eligible=atTime.filter(row=>Number.isFinite(Number(row[field])));
      features[field]=selectionMetrics([...eligible].sort((a,b)=>Number(b[field])-Number(a[field])||a.symbol.localeCompare(b.symbol)).slice(0,Math.min(n,eligible.length)),atTime);
    }
    // Minimal negative control: rotate outcome labels across the stable cross-section.
    const ordered=[...atTime].sort((a,b)=>`${a.sessionDate}|${a.symbol}`.localeCompare(`${b.sessionDate}|${b.symbol}`));
    const shifted=ordered.map((row,index)=>({...row,winner:ordered[(index+Math.max(1,Math.floor(ordered.length/3)))%ordered.length].winner}));
    const permutationTopCurrent=[...shifted].sort((a,b)=>Number(b.currentReturnPct)-Number(a.currentReturnPct)).slice(0,n);
    byTime[decisionTimeJst]=Object.freeze({winnerCount:n,random:selectionMetrics(random,atTime),topNByCausalFeature:Object.freeze(features),labelShiftTopCurrentReturn:selectionMetrics(permutationTopCurrent,shifted)});
  }
  return Object.freeze(byTime);
}

export function buildL1DiscoveryReport({featureRows=[],evaluatorOnlyLabels=[],audit={}}={}){
  const features=new Map(featureRows.map(row=>[`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`,row]));
  const joined=evaluatorOnlyLabels.flatMap(label=>{const feature=features.get(`${label.sessionDate}|${label.symbol}|${label.decisionTimeJst}`);return feature?[Object.freeze({...feature,...label,currentReturnBucket:returnBucket(Number(feature.currentReturnPct))})]:[];});
  if(joined.some(row=>row.evaluatorOnly!==true))throw new Error('L1 report requires physically separated evaluator labels');
  const winners=joined.filter(row=>row.winner),largeWinners=joined.filter(row=>row.largeWinner);
  return Object.freeze({schemaVersion:1,evaluatorOnly:true,audit:Object.freeze({...audit,joinedRows:joined.length}),
    overall:summarize(joined),winnerTimeStructure:group(winners,'decisionTimeJst'),largeWinnerTimeStructure:group(largeWinners,'decisionTimeJst'),
    winnerCurrentReturnBuckets:group(winners,'currentReturnBucket'),byMarket:group(joined,'segment'),byLiquidity:group(joined,'liquidityBucket'),byGap:group(joined,'gapBucket'),byLimitUp:group(joined,'limitUpTouched'),
    outcomeCohorts:group(joined,'finalClass'),causalFeatureDiagnostics:causalFeatureDiagnostics(joined),
    contract:Object.freeze({currentReturnBuckets:['LT_0','0_TO_1','1_TO_2','2_TO_3','3_TO_5','GTE_5'],randomCountMatchedByDecisionTime:true,permutationControl:'DETERMINISTIC_ONE_THIRD_LABEL_ROTATION',outcomesNeverReturnedToDecisionPipeline:true})});
}

export default {buildL1DiscoveryReport};
