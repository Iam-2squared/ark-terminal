import {fitDynamicModel,scoreDynamic} from './phase57-dynamic-walkforward-risk.js';
import {P23_36_POLICY,p2336Key} from './phase57-stable-feature-exact-risk.js';
import {empiricalCompositeScale} from './phase57-empirical-scale-exact-risk.js';
import {stabilityReliability} from './phase57-continuous-stability-shrinkage-risk.js';

export const P23_41_POLICY=Object.freeze({
  phase:'57.p23.41',priorSessionsOnly:true,baselineCoveragePreserved:true,
  recentWindowRows:P23_36_POLICY.recentWindowRows,samePolarityRequired:true,
  directionAdaptiveShrinkage:true,continuousNoThreshold:true,empiricalCompositeScalePreserved:true,
  thresholdSearchAllowed:false,selectionAllowed:false,exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,
  purpose:'TEST_PRIOR_ONLY_DIRECTION_ADAPTIVE_CONTINUOUS_STABILITY_SHRINKAGE'
});
export const p2341Key=p2336Key;

export function directionAdaptiveFeatureModel(fullModel,recentModel){
  if(!fullModel?.ready||!recentModel?.ready)return null;
  const stable=[];
  for(const [k,f] of Object.entries(fullModel.features??{})){
    const r=recentModel.features?.[k],rel=stabilityReliability(f,r);
    if(rel>0)stable.push([k,f,rel]);
  }
  if(stable.length<P23_36_POLICY.minStableFeatures)return null;
  const meanRel=stable.reduce((s,x)=>s+x[2],0)/stable.length;
  const instability=1-meanRel;
  const features={};
  for(const [k,f,rel] of stable){
    const adaptiveRel=1-instability*(1-rel);
    features[k]={...f,weight:f.weight*adaptiveRel,reliability:rel,adaptiveReliability:adaptiveRel};
  }
  const weightSum=Object.values(features).reduce((s,f)=>s+(f.weight??0),0);
  return weightSum>0?{...fullModel,features,weightSum,stableFeatureCount:stable.length,meanReliability:meanRel,directionInstability:instability}:null;
}

export function walkForwardDirectionAdaptiveExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const out=[];let rescoredCount=0,baselinePreservedCount=0;
  for(const b of baselineRows){
    const q=xs.find(r=>p2341Key(r)===p2341Key(b));
    if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const full=fitDynamicModel(hist),recent=fitDynamicModel(hist.slice(-P23_41_POLICY.recentWindowRows));
    const model=directionAdaptiveFeatureModel(full,recent);
    if(!model){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const scale=empiricalCompositeScale(hist,model),raw=scoreDynamic(q,model);
    const riskScore=Number.isFinite(scale)&&scale>0&&Number.isFinite(raw)?raw/scale:null;
    if(!Number.isFinite(riskScore)){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    out.push({...b,riskScore,scoreSource:'DIRECTION_ADAPTIVE_STABILITY_EXACT',normalizationScale:scale,
      stableFeatureCount:model.stableFeatureCount,meanReliability:model.meanReliability,directionInstability:model.directionInstability,
      fullHistoryCount:full.n,recentHistoryCount:recent.n});rescoredCount++;
  }
  if(out.length!==baselineRows.length)throw Error('P23.41 baseline coverage changed');
  return{rows:out,rescoredCount,baselinePreservedCount};
}
