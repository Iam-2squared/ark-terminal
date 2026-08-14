import {fitDynamicModel,scoreDynamic} from './phase57-dynamic-walkforward-risk.js';
import {P23_36_POLICY,stableFeatureModel,p2336Key} from './phase57-stable-feature-exact-risk.js';

export const P23_38_POLICY=Object.freeze({
  phase:'57.p23.38',
  priorSessionsOnly:true,
  baselineCoveragePreserved:true,
  stableFeatureGatePreserved:true,
  empiricalCompositeScale:true,
  covarianceAware:true,
  centerRemoved:false,
  thresholdSearchAllowed:false,
  selectionAllowed:false,
  exitPolicyChangeAllowed:false,
  entryRetuningAllowed:false,
  symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,
  purpose:'TEST_PRIOR_ONLY_EMPIRICAL_COMPOSITE_SCALE_OF_EXACT_DYNAMIC_RISK'
});

export const p2338Key=p2336Key;
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
const sd=a=>{if(a.length<2)return null;const m=mean(a);return Math.sqrt(a.reduce((s,v)=>s+(v-m)**2,0)/(a.length-1));};

export function empiricalCompositeScale(history=[],model){
  if(!model?.ready)return null;
  const scores=history.map(r=>scoreDynamic(r,model)).filter(Number.isFinite);
  const scale=sd(scores);
  return Number.isFinite(scale)&&scale>0?scale:null;
}

export function empiricalScaleScore(row,history,model){
  const raw=scoreDynamic(row,model),scale=empiricalCompositeScale(history,model);
  return Number.isFinite(raw)&&Number.isFinite(scale)&&scale>0?raw/scale:null;
}

export function walkForwardEmpiricalScaleExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const out=[];let normalizedCount=0,baselinePreservedCount=0;
  for(const b of baselineRows){
    const q=xs.find(r=>p2338Key(r)===p2338Key(b));
    if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const full=fitDynamicModel(hist),recent=fitDynamicModel(hist.slice(-P23_36_POLICY.recentWindowRows));
    const model=stableFeatureModel(full,recent)??full;
    const scale=empiricalCompositeScale(hist,model),riskScore=Number.isFinite(scale)&&scale>0?scoreDynamic(q,model)/scale:null;
    if(!Number.isFinite(riskScore)){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    out.push({...b,riskScore,scoreSource:'EMPIRICAL_SCALE_EXACT',normalizationScale:scale,stableFeatureCount:Object.keys(model.features??{}).length,scaleHistoryCount:hist.length});
    normalizedCount++;
  }
  if(out.length!==baselineRows.length)throw Error('P23.38 baseline coverage changed');
  return{rows:out,normalizedCount,baselinePreservedCount};
}
