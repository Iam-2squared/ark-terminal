import {fitDynamicModel,scoreDynamic} from './phase57-dynamic-walkforward-risk.js';
import {P23_36_POLICY,stableFeatureModel,p2336Key} from './phase57-stable-feature-exact-risk.js';

export const P23_37_POLICY=Object.freeze({
  phase:'57.p23.37',
  priorSessionsOnly:true,
  baselineCoveragePreserved:true,
  stableFeatureGatePreserved:true,
  varianceNormalization:true,
  independenceApproximation:true,
  thresholdSearchAllowed:false,
  selectionAllowed:false,
  exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,
  symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,
  purpose:'TEST_PRIOR_ONLY_VARIANCE_NORMALIZATION_OF_EXACT_DYNAMIC_RISK'
});

export const p2337Key=p2336Key;

export function compositeScale(model){
  if(!model?.ready)return null;
  const ws=Object.values(model.features??{}).map(f=>+f.weight).filter(w=>Number.isFinite(w)&&w>0);
  const sum=ws.reduce((s,w)=>s+w,0),sq=ws.reduce((s,w)=>s+w*w,0);
  if(!(sum>0&&sq>0))return null;
  return Math.sqrt(sq)/sum;
}

export function varianceNormalizedScore(row,model){
  const raw=scoreDynamic(row,model),scale=compositeScale(model);
  return Number.isFinite(raw)&&Number.isFinite(scale)&&scale>0?raw/scale:null;
}

export function walkForwardVarianceNormalizedExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const out=[];let normalizedCount=0,baselinePreservedCount=0;
  for(const b of baselineRows){
    const q=xs.find(r=>p2337Key(r)===p2337Key(b));
    if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const full=fitDynamicModel(hist),recent=fitDynamicModel(hist.slice(-P23_36_POLICY.recentWindowRows));
    const model=stableFeatureModel(full,recent)??full;
    const riskScore=varianceNormalizedScore(q,model);
    if(!Number.isFinite(riskScore)){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    out.push({...b,riskScore,scoreSource:'VARIANCE_NORMALIZED_EXACT',normalizationScale:compositeScale(model),stableFeatureCount:Object.keys(model.features??{}).length});
    normalizedCount++;
  }
  if(out.length!==baselineRows.length)throw Error('P23.37 baseline coverage changed');
  return{rows:out,normalizedCount,baselinePreservedCount};
}
