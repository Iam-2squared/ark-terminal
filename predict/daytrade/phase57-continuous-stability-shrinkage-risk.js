import {fitDynamicModel,scoreDynamic} from './phase57-dynamic-walkforward-risk.js';
import {P23_36_POLICY,p2336Key} from './phase57-stable-feature-exact-risk.js';
import {empiricalCompositeScale} from './phase57-empirical-scale-exact-risk.js';

export const P23_40_POLICY=Object.freeze({
  phase:'57.p23.40',
  priorSessionsOnly:true,
  baselineCoveragePreserved:true,
  recentWindowRows:P23_36_POLICY.recentWindowRows,
  samePolarityRequired:true,
  continuousReliabilityShrinkage:true,
  empiricalCompositeScalePreserved:true,
  thresholdSearchAllowed:false,
  selectionAllowed:false,
  exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,
  symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,
  purpose:'TEST_PRIOR_ONLY_CONTINUOUS_EFFECT_SIZE_STABILITY_SHRINKAGE_ON_EXACT_DYNAMIC_RISK'
});

export const p2340Key=p2336Key;

export function stabilityReliability(fullFeature,recentFeature){
  if(!fullFeature||!recentFeature||fullFeature.polarity!==recentFeature.polarity)return 0;
  const a=Math.abs(+fullFeature.weight),b=Math.abs(+recentFeature.weight);
  if(!(a>0&&b>0))return 0;
  return Math.min(a,b)/Math.max(a,b);
}

export function shrinkageFeatureModel(fullModel,recentModel){
  if(!fullModel?.ready||!recentModel?.ready)return null;
  const entries=[];
  for(const [k,f] of Object.entries(fullModel.features??{})){
    const r=recentModel.features?.[k],reliability=stabilityReliability(f,r);
    if(!(reliability>0))continue;
    entries.push([k,{...f,weight:f.weight*reliability,reliability}]);
  }
  if(entries.length<P23_36_POLICY.minStableFeatures)return null;
  const features=Object.fromEntries(entries),weightSum=Object.values(features).reduce((s,f)=>s+(f.weight??0),0);
  return weightSum>0?{...fullModel,features,weightSum,stableFeatureCount:entries.length,meanReliability:entries.reduce((s,[,f])=>s+f.reliability,0)/entries.length}:null;
}

export function walkForwardContinuousStabilityExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const out=[];let rescoredCount=0,baselinePreservedCount=0;
  for(const b of baselineRows){
    const q=xs.find(r=>p2340Key(r)===p2340Key(b));
    if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const full=fitDynamicModel(hist),recent=fitDynamicModel(hist.slice(-P23_40_POLICY.recentWindowRows)),model=shrinkageFeatureModel(full,recent);
    if(!model){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const scale=empiricalCompositeScale(hist,model),raw=scoreDynamic(q,model),riskScore=Number.isFinite(scale)&&scale>0&&Number.isFinite(raw)?raw/scale:null;
    if(!Number.isFinite(riskScore)){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    out.push({...b,riskScore,scoreSource:'CONTINUOUS_STABILITY_SHRINKAGE_EXACT',normalizationScale:scale,stableFeatureCount:model.stableFeatureCount,meanReliability:model.meanReliability,fullHistoryCount:full.n,recentHistoryCount:recent.n});
    rescoredCount++;
  }
  if(out.length!==baselineRows.length)throw Error('P23.40 baseline coverage changed');
  return{rows:out,rescoredCount,baselinePreservedCount};
}
