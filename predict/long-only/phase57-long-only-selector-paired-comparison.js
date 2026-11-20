export const PAIRED_SELECTOR_COMPARISON_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_FROZEN_SELECTOR_PAIRED_D_V1',
  partition:'DEVELOPMENT_D',horizonBars:6,equalBudgetTopN:5,v3Threshold:0.70,
  selectors:Object.freeze(['NEW_LONG','CURRENT_V1','FROZEN_V3','FROZEN_MINIMAL_HYBRID']),
  newSelectorMayChange:false,oldSelectorMayChange:false,validationOpened:false,oosOpened:false,
});

const finite=value=>Number.isFinite(Number(value));
const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const mean=xs=>xs.length?xs.reduce((sum,x)=>sum+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const round=value=>Number.isFinite(value)?Number(value.toFixed(8)):value;

export function equalBudgetTopN(rows=[],topN=PAIRED_SELECTOR_COMPARISON_CONTRACT.equalBudgetTopN){
  const groups=new Map();
  for(const row of rows){const k=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row);}
  return Object.freeze([...groups.values()].flatMap(group=>[...group].sort((a,b)=>Number(a.selectorRank)-Number(b.selectorRank)||String(a.symbol).localeCompare(String(b.symbol))).slice(0,topN)));
}

export function summarizeFrozenSelector({selected=[],targetRows=[]}={}){
  const targets=new Map(targetRows.map(row=>[key(row),row]));
  const joined=selected.map(feature=>({feature,target:targets.get(key(feature))})).filter(row=>finite(row.target?.y30Bps));
  const values=joined.map(row=>Number(row.target.y30Bps)),mfe=joined.map(row=>Number(row.target.futureMfe30Pct)).filter(Number.isFinite),mae=joined.map(row=>Number(row.target.futureMae30Pct)).filter(Number.isFinite),remaining=joined.map(row=>Number(row.target.remainingUpsidePct)).filter(Number.isFinite);
  const sessions=[...new Set(joined.map(row=>row.feature.sessionDate))];
  const sessionMeans=sessions.map(date=>mean(joined.filter(row=>row.feature.sessionDate===date).map(row=>Number(row.target.y30Bps))));
  const allWinnerKeys=new Set(targetRows.filter(row=>row.winner&&finite(row.y30Bps)).map(key)),selectedWinners=joined.filter(row=>row.target.winner).length;
  const grouped=(field,values)=>Object.fromEntries(values.map(value=>[value,summarizeFrozenSelector({selected:selected.filter(row=>(row[field]??'UNKNOWN')===value),targetRows})]));
  const basic=Object.freeze({
    candidateCount:joined.length,decisionCount:new Set(joined.map(row=>`${row.feature.sessionDate}|${row.feature.decisionTimeJst}`)).size,
    candidatesPerDecision:round(joined.length/(new Set(joined.map(row=>`${row.feature.sessionDate}|${row.feature.decisionTimeJst}`)).size||1)),
    meanFutureReturnBps:round(mean(values)),medianFutureReturnBps:round(median(values)),positiveRatePct:round(100*values.filter(value=>value>0).length/(values.length||1)),
    meanFutureMfePct:round(mean(mfe)),meanFutureMaePct:round(mean(mae)),mfeToAbsMae:round(mean(mfe)/Math.abs(mean(mae))),meanRemainingUpsidePct:round(mean(remaining)),
    winnerPrecisionPct:round(100*selectedWinners/(joined.length||1)),winnerRecallPct:round(100*selectedWinners/(allWinnerKeys.size||1)),
    positiveSessions:sessionMeans.filter(value=>value>0).length,sessionCount:sessions.length,positiveSessionRatePct:round(100*sessionMeans.filter(value=>value>0).length/(sessionMeans.length||1)),
  });
  if(selected.__nestedSummary)return basic;
  const nest=rows=>{Object.defineProperty(rows,'__nestedSummary',{value:true});return summarizeFrozenSelector({selected:rows,targetRows});};
  return Object.freeze({...basic,
    byMarket:Object.fromEntries(['PRIME','STANDARD','GROWTH'].map(value=>[value,nest(selected.filter(row=>(row.segment??'UNKNOWN')===value))])),
    byLiquidity:Object.fromEntries(['LOW','MID','HIGH'].map(value=>[value,nest(selected.filter(row=>(row.liquidityBucket??'UNKNOWN')===value))])),
    byGap:Object.fromEntries(['NON_GAP','GAP_UP'].map(value=>[value,nest(selected.filter(row=>(row.gapBucket??'UNKNOWN')===value))])),
    bySessionPeriod:{MORNING:nest(selected.filter(row=>String(row.decisionTimeJst)<'12:00')),AFTERNOON:nest(selected.filter(row=>String(row.decisionTimeJst)>='12:00'))},
  });
}

export default {PAIRED_SELECTOR_COMPARISON_CONTRACT,equalBudgetTopN,summarizeFrozenSelector};
