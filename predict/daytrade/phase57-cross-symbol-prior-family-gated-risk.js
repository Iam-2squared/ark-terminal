import {fitDynamicModel,scoreDynamic,walkForwardDynamic,orderingAuc} from './phase57-dynamic-walkforward-risk.js';
import {fitCdfContrastModel,scoreCdfContrast,walkForwardCdfContrastExact} from './phase57-prior-cdf-contrast-risk.js';
import {walkForwardContinuousStabilityExact} from './phase57-continuous-stability-shrinkage-risk.js';
import {walkForwardPriorFamilyGatedExact} from './phase57-prior-family-gated-risk.js';

export const P23_48_POLICY=Object.freeze({phase:'57.p23.48',priorSessionsOnly:true,baselineCoveragePreserved:true,crossSymbolPriorEvidence:true,leaveCurrentSymbolOutOfGateEvidence:true,gateUsesCurrentOos:false,thresholdSearchAllowed:false,exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,purpose:'TEST_CROSS_SYMBOL_PRIOR_ONLY_FAMILY_GATE_WITH_LEAVE_CURRENT_SYMBOL_OUT_EVIDENCE'});
export const P23_49_POLICY=Object.freeze({phase:'57.p23.49b',priorSessionsOnly:true,baselineCoveragePreserved:true,fixedDirectionFamily:true,upFamily:'P2345',downFamily:'P2340',gateUsesCurrentOos:false,thresholdSearchAllowed:false,exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,purpose:'TEST_FIXED_DIRECTION_SPECIALIZED_HYBRID_P2345_UP_P2340_DOWN'});
const key=r=>`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`;
function evidence(hist=[]){const b=walkForwardDynamic(hist);if(b.length<8)return{family:'P2330',baselineAuc:null,cdfAuc:null,evidenceCount:b.length};const c=walkForwardCdfContrastExact(hist,b).rows,ba=orderingAuc(b),ca=orderingAuc(c);if(!Number.isFinite(ba)||!Number.isFinite(ca))return{family:'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};return{family:ca>ba?'P2344':'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};}
export function walkForwardCrossSymbolPriorFamilyGatedExact(rows=[],baselineRows=[]){
 const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol)),byKey=new Map(xs.map(r=>[key(r),r])),cache=new Map(),out=[];let cdfSelectedCount=0,baselineSelectedCount=0,baselinePreservedCount=0;
 for(const b of baselineRows){const q=byKey.get(key(b));if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
  const prior=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.symbol!==q.symbol&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
  const gk=`${q.setup}|${q.direction}|${q.symbol}|${q.sessionDate}`;let g=cache.get(gk);if(!g){g=evidence(prior);cache.set(gk,g);}
  const fitHist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
  if(g.family==='P2344'){const m=fitCdfContrastModel(fitHist),riskScore=scoreCdfContrast(q,m);if(Number.isFinite(riskScore)){out.push({...b,riskScore,scoreSource:'CROSS_SYMBOL_PRIOR_GATE_P2344',gateBaselineAuc:g.baselineAuc,gateCdfAuc:g.cdfAuc,gateEvidenceCount:g.evidenceCount});cdfSelectedCount++;continue;}}
  const m=fitDynamicModel(fitHist),riskScore=scoreDynamic(q,m);if(Number.isFinite(riskScore)){out.push({...b,riskScore,scoreSource:'CROSS_SYMBOL_PRIOR_GATE_P2330',gateBaselineAuc:g.baselineAuc,gateCdfAuc:g.cdfAuc,gateEvidenceCount:g.evidenceCount});baselineSelectedCount++;}else{out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;}
 }
 if(out.length!==baselineRows.length)throw Error('P23.48 baseline coverage changed');return{rows:out,cdfSelectedCount,baselineSelectedCount,baselinePreservedCount};
}
export function walkForwardConsensusPriorFamilyGatedExact(rows=[],baselineRows=[]){
 const p40=walkForwardContinuousStabilityExact(rows,baselineRows).rows,p45=walkForwardPriorFamilyGatedExact(rows,baselineRows).rows;
 const a=new Map(p40.map(r=>[key(r),r])),b=new Map(p45.map(r=>[key(r),r])),out=[];let upCount=0,downCount=0,baselinePreservedCount=0;
 for(const base of baselineRows){const chosen=base.direction==='UP'?b.get(key(base)):a.get(key(base));if(chosen&&Number.isFinite(chosen.riskScore)){out.push({...chosen,scoreSource:base.direction==='UP'?'DIRECTION_HYBRID_P2345_UP':'DIRECTION_HYBRID_P2340_DOWN'});if(base.direction==='UP')upCount++;else downCount++;}else{out.push({...base,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;}}
 if(out.length!==baselineRows.length)throw Error('P23.49b baseline coverage changed');return{rows:out,upCount,downCount,baselinePreservedCount};
}
