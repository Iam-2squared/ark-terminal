/**
 * Independent market-only audit of Excel RssChart 1M/5M captured locally.
 * Neither the vendor bar-label semantics nor historical arrival is certified.
 * This NEVER feeds the Frozen No.1.1 decision engine or authorizes orders.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const fail=s=>{throw Error(s)};
const clock=(s,label)=>{
 if(typeof s!=='string'||!/^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?\+09:00$/.test(s))
  fail(label);
 const t=Date.parse(s);
 if(!Number.isFinite(t)||new Date(t).toLocaleDateString('en-CA',{timeZone:'Asia/Tokyo'}).replaceAll('/','-')!==s.slice(0,10))
  fail(label);
 return t;
};
const num=(x,zero=false)=>{
 if(typeof x!=='number'||!Number.isFinite(x)||(zero?x<0:x<=0))
  fail('NO11_CHART_EVIDENCE_NUMERIC_INVALID');
 return x;
};
const marketMinute=t=>{
 const d=new Date(t);
 const f=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
 const [h,m]=f.format(d).split(':').map(Number);
 return h*60+m;
};
export function inspectNo11SavedChartEvidence({evidence,now=new Date()}={}){
 if(evidence?.schemaId!=='ARK_NO11_RSS_CHART_DUAL_EVIDENCE_V1'||
    evidence.symbol!=='7203.T'||evidence.sourceFunction!=='RssChart'||
    evidence.evidenceMode!=='OBSERVED_READ_ONLY'||
    evidence.privateAccountDataIncluded!==false||
    evidence.excelOrderEnabled!==false||
    evidence.labelSemanticsCertified!==false||
    evidence.brokerArrivalCertified!==false||
    evidence.originalNativeState9Certified!==false||
    evidence.productionReady!==false||evidence.orderTransmission!==false||
    !evidence.periods||typeof evidence.periods!=='object'||
    Object.keys(evidence.periods).sort().join(',')!=='1M,5M')
  fail('NO11_CHART_EVIDENCE_CONTRACT_INVALID');
 const captured=clock(evidence.capturedAt,'NO11_CHART_EVIDENCE_CAPTURE_INVALID');
 const current=now instanceof Date?now.getTime():clock(now,'NO11_CHART_EVIDENCE_NOW_INVALID');
 if(!Number.isFinite(current)||captured>current+1000)
  fail('NO11_CHART_EVIDENCE_CAPTURE_IN_FUTURE');
 const results={};
 for(const period of ['1M','5M']){
  const group=evidence.periods[period],duration=period==='1M'?60000:300000;
  if(!group||!Number.isInteger(group.requestedBars)||
     group.requestedBars<20||group.requestedBars>3000||
     !Array.isArray(group.rows)||group.rows.length<1||
     group.rows.length>group.requestedBars||group.validRows!==group.rows.length)
   fail('NO11_CHART_EVIDENCE_ROW_COUNT_INVALID');
  const observed=clock(group.observedAt,'NO11_CHART_EVIDENCE_OBSERVED_INVALID');
  if(observed>captured||captured-observed>180000)
   fail('NO11_CHART_EVIDENCE_CAPTURE_SEQUENCE_INVALID');
  let min=Infinity,max=-Infinity,closed=0,excluded=0;
  const seen=new Set(),dayCounts=new Map();
  for(const r of group.rows){
   const label=clock(r?.label,'NO11_CHART_EVIDENCE_LABEL_INVALID');
   if(label>observed||seen.has(label))
    fail('NO11_CHART_EVIDENCE_FUTURE_OR_DUPLICATE_LABEL');
   seen.add(label);
   const minute=marketMinute(label);
   if(!((minute>=540&&minute<=690)||(minute>=750&&minute<=930))||
     (period==='5M'&&minute%5!==0))
    fail('NO11_CHART_EVIDENCE_MARKET_LABEL_INVALID');
   const o=num(r.open),h=num(r.high),l=num(r.low),c=num(r.close),v=num(r.volume,true);
   if(!Number.isSafeInteger(v)||l>Math.min(o,c)||h<Math.max(o,c)||h<l)
    fail('NO11_CHART_EVIDENCE_OHLCV_INCONSISTENT');
   if(label+duration<=observed)closed++;
   else excluded++;
   min=Math.min(min,label);max=Math.max(max,label);
   const day=r.label.slice(0,10);
   dayCounts.set(day,(dayCounts.get(day)||0)+1);
  }
  results[period]=Object.freeze({
   observedRows:group.rows.length,conservativelyClosedRows:closed,
   notConservativelyClosedRows:excluded,
   earliestLabel:new Date(min).toISOString(),latestLabel:new Date(max).toISOString(),
   observedSessions:dayCounts.size,
   days:Object.freeze([...dayCounts].sort((a,b)=>a[0].localeCompare(b[0])).map(([day,count])=>({day,count}))),
   barLabelStartOrEndCertified:false,missingBarsCertified:false,
   frozenState9InputCertified:false
  });
 }
 return Object.freeze({
  schemaId:'ARK_NO11_RSS_CHART_DUAL_AUDIT_V1',
  status:'LOCAL_OHLCV_AUDITED_NOT_NATIVE_CERTIFIED',
  symbol:'7203.T',capturedAt:evidence.capturedAt,
  periods:Object.freeze(results),
  vendorBarLabelSemanticsCertified:false,
  completeBarAvailabilityCertified:false,
  marketwideSelectorDataAvailable:false,
  frozenFirstEntryConnected:false,frozenState9Connected:false,
  originalFrozenModelsExecuted:false,capitalExitConnected:false,
  productionReady:false,orderTransmission:false
 });
}
export function readNo11SavedChartEvidence({file,now=new Date()}={}){
 if(typeof file!=='string'||!path.isAbsolute(file)||
   !/^chart-evidence-[a-f0-9]{32}\.json$/.test(path.basename(file)))
  fail('NO11_CHART_EVIDENCE_PATH_INVALID');
 const st=fs.lstatSync(file);
 if(!st.isFile()||st.isSymbolicLink()||st.size<100||st.size>4000000)
  fail('NO11_CHART_EVIDENCE_FILE_UNSAFE');
 const bytes=fs.readFileSync(file);
 const evidence=JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,''));
 const result=inspectNo11SavedChartEvidence({evidence,now});
 return Object.freeze({...result,localFileSha256:createHash('sha256').update(bytes).digest('hex')});
}
