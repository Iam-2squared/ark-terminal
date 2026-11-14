/**
 * Ark No.1.1 RSS-Market minute Va proxy, explicit user-approved input overlay.
 * No retrospective J-Quants parity, no training, no order or broker writes.
 *
 * Converts two RECEIVED cumulative-counter samples bracketed around one
 * RssChart 1M interval into an OBSERVED proxy Va. A missing, reversed or
 * misaligned source is dropped rather than filled with close*volume or zero.
 *
 * Does NOT prove provider-specific turnover field time or exact exchange Va.
 */
import {createHash} from 'node:crypto';
import {observeNo11RssCumulativeVa,inspectNo11ObservedTurnoverInterval}
  from './no11_rss_cumulative_va_observability.mjs';

export const RSS_VA_PROXY_RECEIPT='ARK_NO11_RSS_MARKET_APPROX_MINUTE_VA_SHADOW_V1';
const SYM=/^[0-9A-Z]{4}\.T$/;
const DATE=/^20\d{2}-\d\d-\d\d$/;
const JST=/^20\d{2}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00$/;
const SHA=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const bad=x=>{throw Error('NO11_RSS_VA_PROXY_'+x)};
const requireOk=(v,code)=>{if(!v)bad(code)};
const instant=s=>typeof s==='string'&&JST.test(s)&&Number.isFinite(Date.parse(s))?
  Date.parse(s):null;
const digits=s=>typeof s==='string'&&/^\d{2}:\d{2}$/.test(s)&&
  Number(s.slice(0,2))<=23&&Number(s.slice(3,5))<=59;
const msecOf=(date,hhmm)=>Date.parse(date+'T'+hhmm+':00+09:00');
const validOHLCV=(r)=>r&&
  ['O','H','L','C','Vo'].every(k=>typeof r[k]==='number'&&Number.isFinite(r[k]))&&
  r.O>0&&r.C>0&&r.H>=Math.max(r.O,r.C)&&
  r.L>0&&r.L<=Math.min(r.O,r.C)&&
  Number.isSafeInteger(r.Vo)&&r.Vo>=0;
/**
 * Source data shape:
 * chartRows: {Date,Code,Time,O,H,L,C,Vo,knownAtJst}[]
 * marketObservations: {symbol, marketDate, observedEndJst,
 *     cumulativeVolumeRaw, cumulativeTurnoverRaw,
 *     vendorVolumeWeightedAverage}[]
 *
 * Timestamps observedEndJst are PC receipt times, NOT exact venue change times.
 * Returns a frozen-selector-compatible Va field ONLY as an APPROXIMATE proxy.
 */
export function makeNo11RssVaProxyMinuteFeed({
  sessionDate,decisionAtJst,selectedSymbols,
  chartRows,marketObservations,maxBracketDelaySeconds=30
}={}){
  requireOk(typeof sessionDate==='string'&&DATE.test(sessionDate)&&
    instant(decisionAtJst)!==null&&
    decisionAtJst.slice(0,10)===sessionDate,'CLOCK_INVALID');
  requireOk(Array.isArray(selectedSymbols)&&selectedSymbols.length>=1&&
    selectedSymbols.length<=50&&
    selectedSymbols.every(s=>typeof s==='string'&&SYM.test(s))&&
    new Set(selectedSymbols).size===selectedSymbols.length,'CHART_SYMBOLS_INVALID');
  requireOk(Array.isArray(chartRows)&&Array.isArray(marketObservations),
    'CHART_AND_MARKET_INPUT_REQUIRED');
  requireOk(Number.isInteger(maxBracketDelaySeconds)&&
    maxBracketDelaySeconds>=0&&maxBracketDelaySeconds<=30,
    'BRACKET_DELAY_INVALID');
  const allowed=new Set(selectedSymbols),decision=instant(decisionAtJst);
  const observations=new Map();
  for(const raw of marketObservations){
    requireOk(raw&&allowed.has(raw.symbol),'MARKET_SYMBOL_OUTSIDE_SELECTED_CHARTS');
    const source=observeNo11RssCumulativeVa({
      record:raw,observedEndJst:raw.observedEndJst
    });
    if(source.status!=='VENDOR_RATIO_CONSISTENT_NOT_MINUTE_VA')continue;
    const stamp=instant(source.observedEndJst);
    if(stamp===null||stamp>decision||source.session!==sessionDate)continue;
    if(!observations.has(raw.symbol))observations.set(raw.symbol,[]);
    observations.get(raw.symbol).push(source);
  }
  for(const samples of observations.values()){
    samples.sort((a,b)=>a.observedEndJst.localeCompare(b.observedEndJst));
    for(let i=1;i<samples.length;i++)
      requireOk(samples[i-1].observedEndJst!==samples[i].observedEndJst,
        'DUPLICATE_MARKET_RECEIPT_INSTANT');
  }
  const rows=[],seenBars=new Set(),reasons={};
  const skip=reason=>{reasons[reason]=(reasons[reason]??0)+1};
  for(const raw of chartRows){
    requireOk(raw&&allowed.has(raw.Code)&&raw.Date===sessionDate&&
      digits(raw.Time),'CHART_BAR_IDENTITY_INVALID');
    const key=raw.Code+'|'+raw.Time;
    requireOk(!seenBars.has(key),'DUPLICATE_ONE_MINUTE_BAR');
    seenBars.add(key);
    if(!validOHLCV(raw)||instant(raw.knownAtJst)===null){
      skip('INVALID_ONE_MINUTE_CHART_BAR');continue;
    }
    const start=msecOf(sessionDate,raw.Time),end=start+60_000;
    const known=instant(raw.knownAtJst);
    if(end>decision||known<end||known>end+90_000||known>decision){
      skip('CHART_NOT_CAUSALLY_AVAILABLE');continue;
    }
    // Exact 1M duration; do not join over an auction/lunch gap.
    const startJst=raw.Time;
    if(startJst<'09:00'||startJst>='15:30'||
       (startJst>='11:30'&&startJst<'12:30')){
      skip('NOT_CASH_CONTINUOUS_ONE_MINUTE');continue;
    }
    const samples=observations.get(raw.Code)??[];
    const earliest=samples.filter(x=>{
      const t=instant(x.observedEndJst);
      return t>=start&&t<=start+maxBracketDelaySeconds*1000;
    });
    const latest=samples.filter(x=>{
      const t=instant(x.observedEndJst);
      return t>=end&&t<=end+maxBracketDelaySeconds*1000;
    });
    if(earliest.length!==1||latest.length!==1){
      skip('MISSING_OR_AMBIGUOUS_CUMULATIVE_BRACKET');continue;
    }
    const interval=inspectNo11ObservedTurnoverInterval({
      earlier:earliest[0],later:latest[0],
      chartOneMinuteVolume:raw.Vo
    });
    if(interval.status!=='RECEIVED_COUNTER_DELTA_WITH_MATCHING_1M_VOLUME'){
      skip(interval.status);continue;
    }
    // Once one-second or sub-minute market samples and 1M Chart
    // are read, the latest of both local receipts is the known-at.
    const finalSeen=Math.max(known,instant(latest[0].observedEndJst));
    if(finalSeen>decision){
      skip('PROXY_NOT_KNOWN_AT_DECISION');continue;
    }
    const knownAtJst=finalSeen===known?raw.knownAtJst:
      latest[0].observedEndJst;
    const Va=interval.turnoverDeltaYenObserved;
    if(!Number.isFinite(Va)||Va<0||
       (raw.Vo===0)!==(Va===0)){
      skip('PROXY_VA_UNUSABLE');continue;
    }
    rows.push({
      Date:raw.Date,Code:raw.Code,Time:raw.Time,
      O:raw.O,H:raw.H,L:raw.L,C:raw.C,Vo:raw.Vo,Va,
      knownAtJst,
      vaProvenance:'RSS_MARKET_CUMULATIVE_60S_ESTIMATE_NOT_VENDOR_MINUTE_VA',
    });
  }
  rows.sort((a,b)=>a.Code.localeCompare(b.Code)||a.Time.localeCompare(b.Time));
  const covered=new Set(rows.map(x=>x.Code));
  const resultReceipt={
    schemaId:RSS_VA_PROXY_RECEIPT,
    inputKind:'RSS_MARKET_OBSERVED_60S_CUMULATIVE_DELTA_PROXY',
    sessionDate,decisionAtJst,selectedSymbols:[...selectedSymbols],
    selectedSymbolCount:selectedSymbols.length,
    validOneMinuteProxyRows:rows.length,
    chartOneMinuteBarsSupplied:chartRows.length,
    availableSymbols:[...selectedSymbols].filter(s=>covered.has(s)),
    skippedBarsByReason:reasons,
    marketObservedAtPCOnly:true,exchangeMinuteBoundaryExact:false,
    marketTurnoverFieldTimestampCertified:false,
    nativeExactMinuteVaCertified:false,
    modelInputDistributionChanged:true,
    historicalOriginalVaParityNotRequired:true,
    hasAnyUsableRows:rows.length>0,
    readOnly:true,shadowOnly:true,productionReady:false,
    orderTransmission:false,derivedMinuteRowsSha256:SHA(rows)
  };
  return Object.freeze({
    receipt:Object.freeze(resultReceipt),
    rows:Object.freeze(rows.map(row=>Object.freeze(row)))
  });
}
