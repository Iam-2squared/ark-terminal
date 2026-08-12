import {P23_30_POLICY,fitDynamicModel,scoreDynamic} from './phase57-dynamic-walkforward-risk.js';

export const P23_36_POLICY=Object.freeze({
  phase:'57.p23.36',
  priorSessionsOnly:true,
  baselineCoveragePreserved:true,
  recentWindowRows:P23_30_POLICY.minHistory*2,
  minStableFeatures:2,
  fullParametersPreserved:true,
  recentModelUsedForPolarityGateOnly:true,
  thresholdSearchAllowed:false,
  selectionAllowed:false,
  exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,
  symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,
  purpose:'TEST_PRIOR_ONLY_STABLE_FEATURE_POLARITY_GATE_ON_EXACT_DYNAMIC_RISK'
});

export const p2336Key=r=>`${r.symbol}|${r.timestamp}|${r.offsetBars}|${r.setup}|${r.direction}`;

export function stableFeatureModel(fullModel,recentModel){
  if(!fullModel?.ready||!recentModel?.ready)return null;
  const stable=Object.entries(fullModel.features??{}).filter(([k,f])=>recentModel.features?.[k]?.polarity===f.polarity);
  if(stable.length<P23_36_POLICY.minStableFeatures)return null;
  const features=Object.fromEntries(stable);
  const weightSum=Object.values(features).reduce((s,f)=>s+(f.weight??0),0);
  return weightSum>0?{...fullModel,features,weightSum,stableFeatureCount:stable.length}:null;
}

export function walkForwardStableFeatureExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const baseline=new Map(baselineRows.map(r=>[p2336Key(r),r]));
  const out=[];let stableRescoredCount=0,baselinePreservedCount=0,recentUnavailableCount=0,insufficientStableFeatureCount=0;
  for(const b of baselineRows){
    const q=xs.find(r=>p2336Key(r)===p2336Key(b));
    if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const fullModel=fitDynamicModel(hist),recentModel=fitDynamicModel(hist.slice(-P23_36_POLICY.recentWindowRows));
    if(!recentModel.ready){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;recentUnavailableCount++;continue;}
    const stableModel=stableFeatureModel(fullModel,recentModel);
    if(!stableModel){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;insufficientStableFeatureCount++;continue;}
    const score=scoreDynamic(q,stableModel);
    if(!Number.isFinite(score)){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    out.push({...b,riskScore:score,scoreSource:'STABLE_FEATURE_EXACT',stableFeatureCount:stableModel.stableFeatureCount,fullHistoryCount:fullModel.n,recentHistoryCount:recentModel.n});
    stableRescoredCount++;
  }
  if(out.length!==baseline.size)throw Error('P23.36 baseline coverage changed');
  return{rows:out,stableRescoredCount,baselinePreservedCount,recentUnavailableCount,insufficientStableFeatureCount};
}
