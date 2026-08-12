import {fitDynamicModel,scoreDynamic,walkForwardDynamic,orderingAuc} from './phase57-dynamic-walkforward-risk.js';
import {fitCdfContrastModel,scoreCdfContrast,walkForwardCdfContrastExact} from './phase57-prior-cdf-contrast-risk.js';

export const P23_45_POLICY=Object.freeze({
  phase:'57.p23.45',priorSessionsOnly:true,baselineCoveragePreserved:true,
  priorInternalWalkForwardFamilyGate:true,gateUsesCurrentOos:false,thresholdSearchAllowed:false,
  exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,purpose:'TEST_PRIOR_ONLY_INTERNAL_WALKFORWARD_FAMILY_GATE_BETWEEN_P2330_AND_P2344'
});

const key=r=>`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`;

function priorFamilyEvidence(hist=[]){
  const b=walkForwardDynamic(hist);
  if(b.length<8)return{family:'P2330',baselineAuc:null,cdfAuc:null,evidenceCount:b.length};
  const c=walkForwardCdfContrastExact(hist,b).rows;
  const ba=orderingAuc(b),ca=orderingAuc(c);
  if(!Number.isFinite(ba)||!Number.isFinite(ca))return{family:'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};
  return{family:ca>ba?'P2344':'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};
}

export function walkForwardPriorFamilyGatedExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const byKey=new Map(xs.map(r=>[key(r),r])),gateCache=new Map();
  const out=[];let cdfSelectedCount=0,baselineSelectedCount=0,baselinePreservedCount=0;
  for(const b of baselineRows){
    const q=byKey.get(key(b));if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const gk=`${q.setup}|${q.direction}|${q.sessionDate}`;let gate=gateCache.get(gk);if(!gate){gate=priorFamilyEvidence(hist);gateCache.set(gk,gate);}
    if(gate.family==='P2344'){
      const m=fitCdfContrastModel(hist),riskScore=scoreCdfContrast(q,m);
      if(Number.isFinite(riskScore)){out.push({...b,riskScore,scoreSource:'PRIOR_FAMILY_GATE_P2344',gateBaselineAuc:gate.baselineAuc,gateCdfAuc:gate.cdfAuc,gateEvidenceCount:gate.evidenceCount});cdfSelectedCount++;continue;}
    }
    const m=fitDynamicModel(hist),riskScore=scoreDynamic(q,m);
    if(Number.isFinite(riskScore)){out.push({...b,riskScore,scoreSource:'PRIOR_FAMILY_GATE_P2330',gateBaselineAuc:gate.baselineAuc,gateCdfAuc:gate.cdfAuc,gateEvidenceCount:gate.evidenceCount});baselineSelectedCount++;}
    else{out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;}
  }
  if(out.length!==baselineRows.length)throw Error('P23.45 baseline coverage changed');
  return{rows:out,cdfSelectedCount,baselineSelectedCount,baselinePreservedCount};
}
