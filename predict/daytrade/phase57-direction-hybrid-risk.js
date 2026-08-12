import {walkForwardContinuousStabilityExact} from './phase57-continuous-stability-shrinkage-risk.js';
import {walkForwardPriorFamilyGatedExact} from './phase57-prior-family-gated-risk.js';

export const P23_50_POLICY=Object.freeze({phase:'57.p23.50',priorSessionsOnly:true,baselineCoveragePreserved:true,fixedDirectionFamily:true,upFamily:'P2345',downFamily:'P2340',thresholdSearchAllowed:false,selectionAllowed:false,exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,purpose:'TEST_FIXED_DIRECTION_SPECIALIZED_HYBRID_P2345_UP_P2340_DOWN'});
const key=r=>`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`;
export function walkForwardDirectionHybridExact(rows=[],baselineRows=[]){
  const p40=walkForwardContinuousStabilityExact(rows,baselineRows).rows;
  const p45=walkForwardPriorFamilyGatedExact(rows,baselineRows).rows;
  const a=new Map(p40.map(r=>[key(r),r])),b=new Map(p45.map(r=>[key(r),r]));
  const out=[];let upCount=0,downCount=0,baselinePreservedCount=0;
  for(const base of baselineRows){
    const chosen=base.direction==='UP'?b.get(key(base)):a.get(key(base));
    if(chosen&&Number.isFinite(chosen.riskScore)){
      out.push({...chosen,scoreSource:base.direction==='UP'?'DIRECTION_HYBRID_P2345_UP':'DIRECTION_HYBRID_P2340_DOWN'});
      if(base.direction==='UP')upCount++;else downCount++;
    }else{out.push({...base,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;}
  }
  if(out.length!==baselineRows.length)throw Error('P23.50 baseline coverage changed');
  return{rows:out,upCount,downCount,baselinePreservedCount};
}
