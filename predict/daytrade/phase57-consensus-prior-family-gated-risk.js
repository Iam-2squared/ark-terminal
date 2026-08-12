import {fitDynamicModel,scoreDynamic,walkForwardDynamic,orderingAuc} from './phase57-dynamic-walkforward-risk.js';
import {fitCdfContrastModel,scoreCdfContrast,walkForwardCdfContrastExact} from './phase57-prior-cdf-contrast-risk.js';
import {walkForwardContinuousStabilityExact,shrinkageFeatureModel,P23_40_POLICY} from './phase57-continuous-stability-shrinkage-risk.js';
import {empiricalCompositeScale} from './phase57-empirical-scale-exact-risk.js';

export const P23_49_POLICY=Object.freeze({phase:'57.p23.49b',priorSessionsOnly:true,baselineCoveragePreserved:true,threeFamilyPriorConsensus:true,fullPriorAndLeaveSymbolOutConsensus:true,gateUsesCurrentOos:false,thresholdSearchAllowed:false,exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,purpose:'TEST_CONSERVATIVE_PRIOR_ONLY_CONSENSUS_AMONG_P2330_P2340_P2344'});
const key=r=>`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`;
function auc(x){return Number.isFinite(x)?x:-Infinity;}
function evidence(hist=[]){
 const b=walkForwardDynamic(hist);if(b.length<8)return{family:'P2330',n:b.length,auc30:null,auc40:null,auc44:null};
 const r40=walkForwardContinuousStabilityExact(hist,b).rows,r44=walkForwardCdfContrastExact(hist,b).rows;
 const a30=orderingAuc(b),a40=orderingAuc(r40),a44=orderingAuc(r44),rank=[['P2330',auc(a30)],['P2340',auc(a40)],['P2344',auc(a44)]].sort((x,y)=>y[1]-x[1]);
 return{family:rank[0][0],n:b.length,auc30:a30,auc40:a40,auc44:a44};
}
function score40(q,hist){
 const full=fitDynamicModel(hist),recent=fitDynamicModel(hist.slice(-P23_40_POLICY.recentWindowRows)),m=shrinkageFeatureModel(full,recent);if(!m)return null;
 const scale=empiricalCompositeScale(hist,m),raw=scoreDynamic(q,m);return Number.isFinite(scale)&&scale>0&&Number.isFinite(raw)?raw/scale:null;
}
export function walkForwardConsensusPriorFamilyGatedExact(rows=[],baselineRows=[]){
 const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol)),byKey=new Map(xs.map(r=>[key(r),r])),cache=new Map(),out=[];let selected40=0,selected44=0,selected30=0,baselinePreservedCount=0;
 for(const b of baselineRows){const q=byKey.get(key(b));if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
  const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));const loo=hist.filter(r=>r.symbol!==q.symbol),gk=`${q.setup}|${q.direction}|${q.symbol}|${q.sessionDate}`;let g=cache.get(gk);if(!g){g={full:evidence(hist),loo:evidence(loo)};cache.set(gk,g);}
  const family=g.full.family===g.loo.family?g.full.family:'P2330';let riskScore=null,scoreSource='CONSENSUS3_PRIOR_GATE_P2330';
  if(family==='P2344'){const m=fitCdfContrastModel(hist);riskScore=scoreCdfContrast(q,m);scoreSource='CONSENSUS3_PRIOR_GATE_P2344';}
  else if(family==='P2340'){riskScore=score40(q,hist);scoreSource='CONSENSUS3_PRIOR_GATE_P2340';}
  else{const m=fitDynamicModel(hist);riskScore=scoreDynamic(q,m);}
  if(Number.isFinite(riskScore)){out.push({...b,riskScore,scoreSource,gateFamily:family,gateFullAuc30:g.full.auc30,gateFullAuc40:g.full.auc40,gateFullAuc44:g.full.auc44,gateLooAuc30:g.loo.auc30,gateLooAuc40:g.loo.auc40,gateLooAuc44:g.loo.auc44});if(family==='P2344')selected44++;else if(family==='P2340')selected40++;else selected30++;}
  else{out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;}
 }
 if(out.length!==baselineRows.length)throw Error('P23.49 baseline coverage changed');return{rows:out,selected40,selected44,selected30,baselinePreservedCount};
}
