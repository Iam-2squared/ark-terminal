export const P23_50_POLICY=Object.freeze({phase:'57.p23.50',baselineCoveragePreserved:true,developmentDerivedDirectionSpecialization:true,upFamily:'P2345',downFamily:'P2340',thresholdSearchAllowed:false,exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,purpose:'TEST_DIRECTION_SPECIALIZED_PRIOR_ONLY_FAMILY_COMPOSITION_ON_FROZEN_DEVELOPMENT_BENCHMARK'});
const key=r=>`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`;
export function composeDirectionSpecializedFamilyExact(baselineRows=[],p2340Rows=[],p2345Rows=[]){
 const a=new Map(p2340Rows.map(r=>[key(r),r])),b=new Map(p2345Rows.map(r=>[key(r),r])),out=[];let upCount=0,downCount=0,preservedCount=0;
 for(const base of baselineRows){const src=base.direction==='DOWN'?a.get(key(base)):b.get(key(base));if(src&&Number.isFinite(src.riskScore)){out.push({...base,riskScore:src.riskScore,scoreSource:base.direction==='DOWN'?'P23_50_DOWN_P2340':'P23_50_UP_P2345'});if(base.direction==='DOWN')downCount++;else upCount++;}else{out.push({...base,scoreSource:'EXACT_P23_30_BASELINE'});preservedCount++;}}
 if(out.length!==baselineRows.length)throw Error('P23.50 baseline coverage changed');return{rows:out,upCount,downCount,preservedCount};
}
