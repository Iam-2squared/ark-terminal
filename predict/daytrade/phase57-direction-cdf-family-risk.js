export const P23_51_POLICY=Object.freeze({phase:'57.p23.51',baselineCoveragePreserved:true,developmentDerivedDirectionSpecialization:true,upFamily:'P2345',downFamily:'P2344',thresholdSearchAllowed:false,exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,freshHoldoutConsumed:false,purpose:'TEST_UP_P2345_DOWN_P2344_DIRECTION_COMPOSITION_ON_FROZEN_DEVELOPMENT_BENCHMARK'});
const key=r=>`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`;
export function composeDirectionCdfFamilyExact(baselineRows=[],p2344Rows=[],p2345Rows=[]){
 const cdf=new Map(p2344Rows.map(r=>[key(r),r])),gate=new Map(p2345Rows.map(r=>[key(r),r])),out=[];let upCount=0,downCount=0,preservedCount=0;
 for(const base of baselineRows){const src=base.direction==='DOWN'?cdf.get(key(base)):gate.get(key(base));if(src&&Number.isFinite(src.riskScore)){out.push({...base,riskScore:src.riskScore,scoreSource:base.direction==='DOWN'?'P23_51_DOWN_P2344':'P23_51_UP_P2345'});if(base.direction==='DOWN')downCount++;else upCount++;}else{out.push({...base,scoreSource:'EXACT_P23_30_BASELINE'});preservedCount++;}}
 if(out.length!==baselineRows.length)throw Error('P23.51 baseline coverage changed');return{rows:out,upCount,downCount,preservedCount};
}
