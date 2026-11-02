/**
 * RssChart 1M->5M OHLCV parity research: tests all four start/end label
 * interpretations. Only full five-minute groups are compared.
 * Does not certify broker semantics, native State9, or production readiness.
 */
import {inspectNo11SavedChartEvidence} from './no11_saved_chart_evidence_audit.mjs';
const fail=s=>{throw Error(s)};
const ms=s=>Date.parse(s);
const rounded=(x,y)=>Math.abs(x-y)<=1e-8*Math.max(1,Math.abs(x),Math.abs(y));
const slot=t=>Math.floor(t/300000)*300000;
const key=(day,slotMs)=>day+'|'+slotMs;
function bucket1m(rows,oneMinuteMode){
 const groups=new Map();
 for(const r of rows){
  const t=ms(r.label);
  const start=t-(oneMinuteMode==='END'?60000:0);
  const day=new Date(start).toLocaleDateString('en-CA',{timeZone:'Asia/Tokyo'}).replaceAll('/','-');
  const k=key(day,slot(start));
  if(!groups.has(k))groups.set(k,[]);
  groups.get(k).push({...r,start});
 }
 const complete=new Map();
 for(const [k,g] of groups){
  g.sort((a,b)=>a.start-b.start);
  const start=slot(g[0].start);
  if(g.length!==5||g.some((x,i)=>x.start!==start+i*60000))continue;
  complete.set(k,{
   open:g[0].open,high:Math.max(...g.map(x=>x.high)),
   low:Math.min(...g.map(x=>x.low)),close:g[4].close,
   volume:g.reduce((n,x)=>n+x.volume,0)
  });
 }
 return complete;
}
export function compareNo11SavedChartParity({evidence,now=new Date()}={}){
 const audit=inspectNo11SavedChartEvidence({evidence,now});
 const one=evidence.periods['1M'].rows,five=evidence.periods['5M'].rows;
 const combinations=[];
 for(const oneMode of ['START','END']){
  const buckets=bucket1m(one,oneMode);
  for(const fiveMode of ['START','END']){
   let compared=0,matched=0,mismatched=0,unmatchedFive=0;
   const examples=[];
   for(const f of five){
    const t=ms(f.label);
    const start=t-(fiveMode==='END'?300000:0);
    const day=new Date(start).toLocaleDateString('en-CA',{timeZone:'Asia/Tokyo'}).replaceAll('/','-');
    const group=buckets.get(key(day,start));
    if(!group){unmatchedFive++;continue;}
    compared++;
    const ok=['open','high','low','close','volume'].every(k=>rounded(group[k],f[k]));
    if(ok)matched++;else{
     mismatched++;
     if(examples.length<3)examples.push({label:f.label,fieldMismatch:true});
    }
   }
   combinations.push(Object.freeze({oneMinuteLabel:oneMode,fiveMinuteLabel:fiveMode,
    completeGroupsCompared:compared,matched,mismatched,unmatchedFive,
    mismatchExamples:examples}));
  }
 }
 const sorted=[...combinations].sort((a,b)=>b.matched-a.matched||a.mismatched-b.mismatched);
 const best=sorted[0];
 return Object.freeze({
  schemaId:'ARK_NO11_RSS_1M_5M_PARITY_RESEARCH_V1',
  status:'LOCAL_BAR_PARITY_RESEARCH_ONLY',
  symbol:audit.symbol,
  combinations:Object.freeze(combinations),
  bestObservedCombination:best,
  sufficientEvidenceToCertifyProviderLabelSemantics:false,
  dataCompletenessCertified:false,
  frozenState9ParityCertified:false,
  productionReady:false,orderTransmission:false
 });
}
