import {fitDynamicModel,scoreDynamic,walkForwardDynamic,orderingAuc} from './phase57-dynamic-walkforward-risk.js';
import {fitCdfContrastModel,scoreCdfContrast,walkForwardCdfContrastExact} from './phase57-prior-cdf-contrast-risk.js';

export const P23_50_POLICY=Object.freeze({phase:'57.p23.50',priorSessionsOnly:true,baselineCoveragePreserved:true,pooledAndLeaveSymbolOutConsensus:true,gateUsesCurrentOos:false,thresholdSearchAllowed:false,exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,purpose:'TEST_CONSERVATIVE_PRIOR_ONLY_CONSENSUS_GATE_P2330_VS_P2344'});
const key=r=>`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`;
function evidence(hist=[]){const b=walkForwardDynamic(hist);if(b.length<8)return{family:'P2330',baselineAuc:null,cdfAuc:null,evidenceCount:b.length};const c=walkForwardCdfContrastExact(hist,b).rows,ba=orderingAuc(b),ca=orderingAuc(c);if(!Number.isFinite(ba)||!Number.isFinite(ca))return{family:'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};return{family:ca>ba?'P2344':'P2330',baselineAuc:ba,cdfAuc:ca,evidenceCount:b.length};}
export function walkForwardP2350ConsensusPriorFamilyGatedExact(rows=[],baselineRows=[]){
 const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol)),byKey=new Map(xs.map(r=>[key(r),r])),cache=new Map(),out=[];let cdfSelectedCount=0,baselineSelectedCount=0,baselinePreservedCount=0;
 for(const b of baselineRows){const q=byKey.get(key(b));if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
  const pooled=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
  const leave=pooled.filter(r=>r.symbol!==q.symbol),gk=`${q.setup}|${q.direction}|${q.symbol}|${q.sessionDate}`;let g=cache.get(gk);if(!g){g={pooled:evidence(pooled),leave:evidence(leave)};cache.set(gk,g);}
  const useCdf=g.pooled.family==='P2344'&&g.leave.family==='P2344';
  if(useCdf){const m=fitCdfContrastModel(pooled),riskScore=scoreCdfContrast(q,m);if(Number.isFinite(riskScore)){out.push({...b,riskScore,scoreSource:'CONSENSUS_PRIOR_GATE_P2344',pooledBaselineAuc:g.pooled.baselineAuc,pooledCdfAuc:g.pooled.cdfAuc,leaveBaselineAuc:g.leave.baselineAuc,leaveCdfAuc:g.leave.cdfAuc,pooledEvidenceCount:g.pooled.evidenceCount,leaveEvidenceCount:g.leave.evidenceCount});cdfSelectedCount++;continue;}}
  const m=fitDynamicModel(pooled),riskScore=scoreDynamic(q,m);if(Number.isFinite(riskScore)){out.push({...b,riskScore,scoreSource:'CONSENSUS_PRIOR_GATE_P2330'});baselineSelectedCount++;}else{out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;}
 }
 if(out.length!==baselineRows.length)throw Error('P23.50 baseline coverage changed');return{rows:out,cdfSelectedCount,baselineSelectedCount,baselinePreservedCount};
}
