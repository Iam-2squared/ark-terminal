import {P23_27_FEATURES} from './phase57-feature-polarity-segmentation.js';
import {P23_30_POLICY} from './phase57-dynamic-walkforward-risk.js';

export const P23_44_POLICY=Object.freeze({
  phase:'57.p23.44',priorSessionsOnly:true,baselineCoveragePreserved:true,
  empiricalClassCdfContrast:true,thresholdSearchAllowed:false,selectionAllowed:false,
  exitPolicyChangeAllowed:false,entryRetuningAllowed:false,symbolFilteringAllowed:false,
  freshHoldoutConsumed:false,purpose:'TEST_PRIOR_ONLY_NONPARAMETRIC_CLASS_CDF_CONTRAST_DYNAMIC_RISK'
});

const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
const sd=a=>{if(a.length<2)return null;const m=mean(a);return Math.sqrt(a.reduce((s,v)=>s+(v-m)**2,0)/(a.length-1));};
const cdf=(x,a)=>{let lo=0,hi=a.length;while(lo<hi){const m=(lo+hi)>>1;if(a[m]<=x)lo=m+1;else hi=m;}return lo/a.length;};

function featureModel(rows,key){
  const bad=rows.filter(r=>r.actual===1).map(r=>+r.velocity?.[key]).filter(Number.isFinite).sort((a,b)=>a-b);
  const good=rows.filter(r=>r.actual===0).map(r=>+r.velocity?.[key]).filter(Number.isFinite).sort((a,b)=>a-b);
  if(bad.length<2||good.length<2)return null;
  const mb=mean(bad),mg=mean(good),sb=sd(bad),sg=sd(good);
  const v=((bad.length-1)*sb**2+(good.length-1)*sg**2)/(bad.length+good.length-2),p=v>0?Math.sqrt(v):null;
  if(!p)return null;
  const d=(mb-mg)/p;if(!Number.isFinite(d)||d===0)return null;
  return{bad,good,polarity:Math.sign(d),weight:Math.min(Math.abs(d),P23_30_POLICY.weightCap)};
}

export function fitCdfContrastModel(rows=[]){
  const bad=rows.filter(r=>r.actual===1).length,good=rows.filter(r=>r.actual===0).length;
  if(rows.length<P23_30_POLICY.minHistory||bad<P23_30_POLICY.minInvalidated||good<P23_30_POLICY.minSurvived)return{ready:false,n:rows.length,bad,good};
  const features=Object.fromEntries(P23_27_FEATURES.map(k=>[k,featureModel(rows,k)]).filter(([,v])=>v));
  const weightSum=Object.values(features).reduce((s,v)=>s+v.weight,0);
  return weightSum>0?{ready:true,n:rows.length,bad,good,features,weightSum}:{ready:false,n:rows.length,bad,good};
}

export function scoreCdfContrast(row,m){
  if(!m?.ready)return null;let s=0,w=0;
  for(const [k,f] of Object.entries(m.features)){
    const x=+row.velocity?.[k];if(!Number.isFinite(x))continue;
    const contrast=f.polarity*(cdf(x,f.good)-cdf(x,f.bad));
    s+=f.weight*contrast;w+=f.weight;
  }
  return w>0?s/w:null;
}

export function walkForwardCdfContrastExact(rows=[],baselineRows=[]){
  const xs=[...rows].sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  const byKey=new Map(xs.map(r=>[`${r.symbol}|${r.setup}|${r.direction}|${r.timestamp}|${r.offsetBars}`,r]));
  const out=[];let rescoredCount=0,baselinePreservedCount=0;
  for(const b of baselineRows){
    const q=byKey.get(`${b.symbol}|${b.setup}|${b.direction}|${b.timestamp}|${b.offsetBars}`);
    if(!q){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    const hist=xs.filter(r=>r.setup===q.setup&&r.direction===q.direction&&r.sessionDate<q.sessionDate&&String(r.fullyRealizedAt)<String(q.timestamp));
    const m=fitCdfContrastModel(hist),riskScore=scoreCdfContrast(q,m);
    if(!Number.isFinite(riskScore)){out.push({...b,scoreSource:'EXACT_P23_30_BASELINE'});baselinePreservedCount++;continue;}
    out.push({...b,riskScore,scoreSource:'PRIOR_CDF_CONTRAST_EXACT',historyCount:m.n,historyInvalidated:m.bad,historySurvived:m.good});rescoredCount++;
  }
  if(out.length!==baselineRows.length)throw Error('P23.44 baseline coverage changed');
  return{rows:out,rescoredCount,baselinePreservedCount};
}
