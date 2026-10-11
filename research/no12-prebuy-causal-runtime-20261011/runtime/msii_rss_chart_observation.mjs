/**
 * No.1.2 prospective READ ONLY normalization of MarketSpeed II RssChart 5M.
 * Source contract: user-supplied Rakuten MSII RSS function spec 2026-03-30,
 * pages 18, 33 and 38. RssChart exposes date/time/OHLC/volume, but its
 * data-time is NOT an independently certified broker-delivery timestamp.
 *
 * No Excel I/O here, no native model, no live orders. Input must be a separate
 * physically captured READ ONLY sheet observation; synth-only until verified.
 */
import {createHash} from 'node:crypto';
import {canonical} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {CAUSAL_FRAME_SCHEMA,inspectNo11ProspectiveAsOf} from
  '../../../integration/no1-1-msii/runtime/native_causal_asof.mjs';

export const NO12_CHART_SCHEMA='ARK_NO12_MSII_RSS_CHART_5M_OBSERVATION_V1';
export const RSS_CHART_COLUMNS=Object.freeze([
  '銘柄名称','市場名称','足種','日付','時刻','始値','高値','安値','終値','出来高'
]);
const error=s=>{throw Error(s)};
const ms=(s,label)=>{
 if(typeof s!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s)))
   error(label);
 return Date.parse(s);
};
const jstDay=when=>new Intl.DateTimeFormat('en-CA',{
 timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'
}).format(new Date(when)).replace(/\//g,'-');
const symbol=x=>{
 if(typeof x!=='string'||!/^[0-9A-Z]{4}\.T$/.test(x.trim().toUpperCase()))
   error('NO12_CHART_SYMBOL_MUST_BE_VERIFIED_TSE_4');
 return x.trim().toUpperCase();
};
const number=(x,label,{allowZero=false}={})=>{
 if(typeof x!=='number'||!Number.isFinite(x)||
    (allowZero?x<0:x<=0))error(label);
 return x;
};
const hash=v=>createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
function dateTime(row){
 if(!/^\d{4}\/\d\d\/\d\d$/.test(row?.['日付']??'')||
    !/^\d\d:\d\d$/.test(row?.['時刻']??''))
   error('NO12_CHART_VENDOR_DATE_TIME_FORMAT_INVALID');
 const stamp=row['日付'].replaceAll('/','-')+'T'+row['時刻']+':00+09:00';
 const epoch=Date.parse(stamp);
 if(!Number.isFinite(epoch)||
    jstDay(epoch)!==row['日付'].replaceAll('/','-')||
    new Intl.DateTimeFormat('en-GB',{
      timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'
    }).format(new Date(epoch))!==row['時刻'])error('NO12_CHART_VENDOR_TIME_INVALID');
 if(epoch%300000!==0)error('NO12_CHART_5MIN_BAR_CLOCK_INVALID');
 return {epoch,stamp};
}
/**
 * No.1.2 synthetic chart row normalizer. Assumes nothing about whether the
 * vendor's displayed 5M time denotes a start or an end. Waiting an EXTRA
 * complete 5-minute interval after the displayed timestamp is conservative.
 * Still NOT provider-arrival-time certification.
 */
export function inspectNo12RssChartSnapshot({
 snapshot,decisionAt,now=new Date()
}={}){
 if(!snapshot||snapshot.schemaId!==NO12_CHART_SCHEMA||
    snapshot.sourceFunction!=='RssChart'||snapshot.period!=='5M'||
    snapshot.evidenceMode!=='OBSERVED_READ_ONLY'||
    snapshot.privateAccountDataIncluded===true||
    snapshot.excelOrderEnabled===true)error('NO12_CHART_READONLY_SOURCE_CONTRACT_INVALID');
 const s=symbol(snapshot.symbol);
 const captured=ms(snapshot.capturedAt,'NO12_CHART_CAPTURE_CLOCK_INVALID');
 const decision=ms(decisionAt,'NO12_CHART_DECISION_CLOCK_INVALID');
 const nowMs=now instanceof Date?now.getTime():ms(now,'NO12_CHART_NOW_INVALID');
 if(!Number.isFinite(nowMs)||captured>decision||decision>nowMs+1000||
    nowMs-captured>30000)error('NO12_CHART_CLOCK_NOT_FRESH_FOR_RESEARCH');
 if(!Array.isArray(snapshot.rows)||snapshot.rows.length>3000)error('NO12_CHART_ROWS_UNAVAILABLE');
 if(snapshot.columns?.length!==RSS_CHART_COLUMNS.length||
    RSS_CHART_COLUMNS.some((name,i)=>snapshot.columns[i]!==name))
   error('NO12_CHART_HEADER_NOT_OFFICIAL');
 const rows=[],used=new Set();let inProgress=0;
 for(const row of snapshot.rows){
   if(!row||typeof row!=='object'||Array.isArray(row))error('NO12_CHART_ROW_INVALID');
   if(row['足種']!==undefined&&row['足種']!=='5M')error('NO12_CHART_PERIOD_MISMATCH');
   const {stamp,epoch}=dateTime(row);
   if(used.has(stamp))error('NO12_CHART_DUPLICATE_BAR_TIME');
   used.add(stamp);
   const open=number(row['始値'],'NO12_CHART_OHLC_MISSING');
   const high=number(row['高値'],'NO12_CHART_OHLC_MISSING');
   const low=number(row['安値'],'NO12_CHART_OHLC_MISSING');
   const close=number(row['終値'],'NO12_CHART_OHLC_MISSING');
   const volume=number(row['出来高'],'NO12_CHART_VOLUME_INVALID',{allowZero:true});
   if(!Number.isSafeInteger(volume)||low>Math.min(open,close)||
      high<Math.max(open,close)||low>high)error('NO12_CHART_OHLCV_INCONSISTENT');
   const conservativeBarClosed=epoch+300000;
   if(conservativeBarClosed>captured){inProgress++;continue;}
   rows.push(Object.freeze({at:stamp,atMs:epoch,open,high,low,close,volume,
     conservativeBarClosedAt:new Date(conservativeBarClosed).toISOString()}));
 }
 rows.sort((a,b)=>a.atMs-b.atMs);
 const session=jstDay(decision);
 const sameDay=rows.filter(r=>jstDay(r.atMs)===session);
 const latest=sameDay.at(-1)??null;
 if(latest===null){
   return Object.freeze({schemaId:'ARK_NO12_RSS_CHART_AUDIT_V1',
     status:'NO_CURRENT_SESSION_COMPLETED_BAR',
     symbol:s,retainedBars:rows.length,inProgressBars:inProgress,
     bar:null,sourceRecord:null,sourceFrameSha256:null,
     actualBrokerFeedArrivalCertified:false,providerBarLabelSemanticsCertified:false,
     nativeState9Certified:false,nativeEntryCertified:false,
     productionReady:false,orderTransmission:false});
 }
 const payload={symbol:s,sourceFunction:'RssChart',period:'5M',
   sourceAsOf:latest.at,conservativeBarClosedAt:latest.conservativeBarClosedAt,
   observedAt:snapshot.capturedAt,knownAt:snapshot.capturedAt,
   ohlcv:{open:latest.open,high:latest.high,low:latest.low,
     close:latest.close,volume:latest.volume}};
 const priceReceipt=hash(payload);
 const record={recordId:'chart-'+s.replace('.','-')+'-'+priceReceipt.slice(0,16),
   sourceType:'MARKETSPEED_II_RSS_MARKET_OBSERVATION',
   evidenceMode:'OBSERVED_READ_ONLY',
   sourceAsOf:latest.at,
   barClosedAt:latest.conservativeBarClosedAt,
   observedAt:snapshot.capturedAt,knownAt:snapshot.capturedAt};
 const frame={schemaId:CAUSAL_FRAME_SCHEMA,session,decisionAt,records:[record]};
 const checked=inspectNo11ProspectiveAsOf({frame,now});
 return Object.freeze({schemaId:'ARK_NO12_RSS_CHART_AUDIT_V1',
   status:'LOCAL_CHART_5M_BAR_OBSERVED_READONLY_NOT_LIVE_CERTIFIED',
   symbol:s,retainedBars:rows.length,inProgressBars:inProgress,
   bar:Object.freeze({...latest,atMs:undefined}),sourceRecord:Object.freeze(record),
   sourcePayloadSha256:priceReceipt,sourceFrameSha256:checked.sourceFrameSha256,
   actualBrokerFeedArrivalCertified:false,providerBarLabelSemanticsCertified:false,
   nativeState9Certified:false,nativeEntryCertified:false,
   productionReady:false,orderTransmission:false});
}
/** Bind a candidate market reference to an EXACT previously normalized bar.
 * It cannot fabricate First Entry score, State9 or a live-trading attestation.
 */
export function bindNo12SyntheticChartReference({
 candidate,chartAudit,requestedDecisionAt
}={}){
 if(!candidate||typeof candidate!=='object'||
    chartAudit?.status!=='LOCAL_CHART_5M_BAR_OBSERVED_READONLY_NOT_LIVE_CERTIFIED'||
    chartAudit.productionReady!==false||chartAudit.orderTransmission!==false)
   error('NO12_CHART_BACKING_SOURCE_UNAVAILABLE');
 if(symbol(candidate.symbol)!==chartAudit.symbol)
   error('NO12_CHART_BACKING_SYMBOL_MISMATCH');
 if(!chartAudit.sourceRecord||!chartAudit.bar)
   error('NO12_CHART_BACKING_BAR_UNAVAILABLE');
 if(ms(chartAudit.sourceRecord.knownAt,'NO12_CHART_KNOWN_AT_INVALID')>
    ms(requestedDecisionAt,'NO12_CHART_CANDIDATE_DECISION_AT_INVALID'))
   error('NO12_CHART_VALUE_NOT_YET_OBSERVED');
 if(candidate.referencePrice!==undefined &&
    candidate.referencePrice!==chartAudit.bar.close)
   error('NO12_CHART_REFERENCE_PRICE_MISMATCH');
 return Object.freeze({
   ...candidate,referencePrice:chartAudit.bar.close,
   marketRecordId:chartAudit.sourceRecord.recordId,
   candidateKnownAt:chartAudit.sourceRecord.knownAt,
   liveNativeDecisionCertified:false,orderTransmission:false});
}
