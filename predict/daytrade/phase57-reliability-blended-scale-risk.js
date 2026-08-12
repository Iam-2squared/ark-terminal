import {P23_30_POLICY,fitDynamicModel,scoreDynamic} from './phase57-dynamic-walkforward-risk.js';
import {P23_36_POLICY,stableFeatureModel,p2336Key} from './phase57-stable-feature-exact-risk.js';
import {compositeScale} from './phase57-variance-normalized-exact-risk.js';
import {empiricalCompositeScale} from './phase57-empirical-scale-exact-risk.js';

export const P23_39_POLICY=Object.freeze({
  phase:'57.p23.39',
  priorSessionsOnly:true,
  baselineCoveragePreserved:true,
  stableFeatureGatePreserved:true,
  reliabilityBlendedScale:true,
  blendOnVariance:true,
  empiricalReliabilityPriorRows:P23_30_POLICY.minHistory,
  thresholdSearchAllowed:false,
  selectionAllowed:false,
  exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,
  symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,
  purpose:'TEST_PRIOR_ONLY_RELIABILITY_BLEND_OF_THEORETICAL_AND_EMPIRICAL_COMPOSITE_SCALE'
});

export const p2339Key=p2336Key;

export function empiricalReliability(historyCount){
  const n=Math.max(0,+historyCount||0),k=P23_39_POLICY.empiricalReliabilityPriorRows;
  return n/(n+k);
}

export function reliabilityBlendedScale(history=[],model){
  const theoretical=compositeScale(model),empirical=empiricalCompositeScale(history,model);
  if(!(Number.isFinite(theoretical)&&theoretical>0))return Number.isFinite(empirical)&&empirical>0?empirical:null;
  if(!(Number.isFinite(empirical)&&empirical>0))return theoretical;
  const lambda=empiricalReliability(history.length);
  const variance=(1-lambda)*theoretical**2+lambda*empirical**2;
  return variance>0?Math.sqrt(variance):null;
}

export function reliabilityBlendedScore(row,history,model){
  const raw=scoreDynamic(row,model),scale=reliabilityBlendedScale(history,model);
  return Number.isFinite(raw)&&Number.isFinite(scale)&&scale>0?raw/scale:null;
}

export function walkForwardReliabilityBlendedExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const out=[];let normalizedCount=0,baselinePreservedCount=0;
  for(const b of baselineRows){
    const q=xs.find(r=>p2339Key(r)===p2339Key(b));
    if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const full=fitDynamicModel(hist),recent=fitDynamicModel(hist.slice(-P23_36_POLICY.recentWindowRows));
    const model=stableFeatureModel(full,recent)??full;
    const scale=reliabilityBlendedScale(hist,model),riskScore=Number.isFinite(scale)&&scale>0?scoreDynamic(q,model)/scale:null;
    if(!Number.isFinite(riskScore)){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    out.push({...b,riskScore,scoreSource:'RELIABILITY_BLENDED_SCALE_EXACT',normalizationScale:scale,empiricalReliability:empiricalReliability(hist.length),stableFeatureCount:Object.keys(model.features??{}).length,scaleHistoryCount:hist.length});
    normalizedCount++;
  }
  if(out.length!==baselineRows.length)throw Error('P23.39 baseline coverage changed');
  return{rows:out,normalizedCount,baselinePreservedCount};
}
