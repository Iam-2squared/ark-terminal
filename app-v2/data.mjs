import assert from 'node:assert/strict';
export const FLAGS=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'];
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const number=x=>{assert.ok(finite(x),'INVALID_NUMBER');return x;};
const stamp=x=>typeof x==='string'&&Number.isFinite(Date.parse(x));
export function emptyStatus(now=new Date().toISOString()) {return {schemaId:'ARK_APP_V2_STATUS_V1',mode:'READ_ONLY',observedAt:now,portfolio:null,positions:[],history:[],activity:[],source:{feeds:[],rawLatest:null,normalizedLatest:null,parity:'UNVERIFIED',finalizedLatest:null},execution:{mode:'UNKNOWN',transmission:'LOCKED',reconciliation:'UNKNOWN',orders:[],preflight:[],limits:{}},components:['MARKETSPEED II','Excel RSS','RSS Market','RSS Chart','5m Finalization','Realtime Engine','Realtime Shadow','Execution Layer','Transmission'].map(name=>({name,status:name==='Transmission'?'LOCKED':name==='5m Finalization'?'UNVERIFIED':'UNKNOWN',detail:'No verified status bound'})),system:{version:'2.0.0-preview',head:'UNKNOWN',branch:'UNKNOWN'},warnings:[]};}
function locked(s){assert.ok(s);for(const flag of FLAGS)assert.equal(s[flag],false,'UNSAFE_STATUS');}
export function executionView(s){
 assert.equal(s.version,'PHASE57_EXECUTION_V1');assert.equal(s.fixtureOnly,true,'FIXTURE_ONLY');locked(s.safety);assert.equal(s.transmission,'LOCKED');
 const p=s.portfolio;assert.ok(p);const initial=number(s.initialEquity),flow=number(s.externalCashFlowJpy),equity=number(p.equityJpy),pnl=number(p.realizedPnl)+number(p.unrealizedPnl);
 assert.ok(Math.abs(equity-initial-flow-pnl)<.01,'CONSERVATION_MISMATCH');assert.ok(Array.isArray(p.positions),'POSITIONS_UNKNOWN');
 const identities=new Set();const positions=p.positions.map(x=>{assert.ok(typeof x.symbol==='string'&&!identities.has(x.symbol),'POSITION_IDENTITY');identities.add(x.symbol);assert.ok(['LONG','SHORT'].includes(x.direction));const quantity=number(x.quantity),averagePrice=number(x.averagePrice),price=number(x.markPrice);assert.ok(quantity>0&&averagePrice>0&&price>0);const upnl=(price-averagePrice)*quantity*(x.direction==='LONG'?1:-1);return {symbol:x.symbol,name:typeof x.name==='string'?x.name:'名称未接続',direction:x.direction,quantity,averagePrice,price,value:quantity*price,pnl:upnl,pnlPct:upnl/(averagePrice*quantity)*100,entryAt:null,barsHeld:null,mfe:null,mae:null,exitState:'UNBOUND',details:{entryReason:'UNBOUND',selector:'UNBOUND',score:null,allocation:'V3_B_RISK × MAX_3',v4:'UNBOUND',v5:'UNBOUND',vwapDeviation:null,lastDecisionAt:null}};});
 assert.ok(s.orders&&typeof s.orders==='object'&&!Array.isArray(s.orders),'ORDERS_UNKNOWN');const orders=Object.values(s.orders);
 const today=finite(s.sessionStartPnl)?pnl-s.sessionStartPnl:null;
 return {portfolio:{equity,initial,cash:number(p.cashJpy),buyingPower:number(p.buyingPower),gross:number(p.grossExposureJpy),net:number(p.signedNetExposureJpy),realized:p.realizedPnl,unrealized:p.unrealizedPnl,pnl,flow,today,todayPct:today!==null&&finite(s.sessionStartEquity)&&s.sessionStartEquity>0?today/s.sessionStartEquity*100:null,returnPct:flow===0&&initial>0?pnl/initial*100:null,maxDD:null},positions,execution:{mode:typeof s.mode==='string'?s.mode:'UNKNOWN',transmission:'LOCKED',reconciliation:typeof s.reconciliation==='string'?s.reconciliation:'UNKNOWN',orders,limits:Object.fromEntries(Object.entries(s.limits??{}).filter(([,v])=>finite(v))),preflight:['engineReady','finalizationPassed','msiiConnected','excelConnected','networkConnected','adapterAvailable'].map(name=>({name,status:s.context?.[name]===true?'FIXTURE_PASS':s.context?.[name]===false?'FAIL':'UNKNOWN'}))},activity:orders.map(o=>({at:stamp(o.intent?.createdAt)?o.intent.createdAt:null,symbol:o.intent?.symbol??'',type:'ORDER INTENT',state:o.status??'UNKNOWN',reason:(o.blockReasons??[]).join(', '),category:'EXECUTION',raw:o}))};
}
export function sourceFromCapture(p){
 assert.equal(p.mode,'SOURCE_SEMANTICS_ONLY');assert.equal(p.sourceClass,'REAL_SOURCE_DIAGNOSTIC');assert.ok(stamp(p.captureTimestamp));assert.ok(Array.isArray(p.rows));
 // The capture reader owns connection/freshness semantics. UI does not invent a new threshold.
 return {schemaId:'ARK_REAL_SOURCE_SEMANTICS_REPORT_V1',mode:p.mode,strategyCalculated:false,readyForStrategy:false,safety:Object.fromEntries(FLAGS.map(f=>[f,false])),captureTimestamp:p.captureTimestamp,connectionState:p.connectionState??'SOURCE_CONNECTION_UNVERIFIED',currentFeedObservations:p.rows.map(r=>({...r,captureTimestamp:p.captureTimestamp})),latestRawWindowMetadata:p.workbookHealthy===true&&p.partialRead===false?p.rawWindowMetadata??[]:[],events:p.workbookHealthy===true&&p.partialRead===false?[]:[{cause:p.error??'EXCEL_CAPTURE_FAILURE'}]};
}
export function assemble({source=null,execution=null,now=new Date().toISOString(),system={},errors=[]}={}){
 const out=emptyStatus(now);out.system={...out.system,...system};out.warnings=[...errors];
 if(source)try{
  assert.equal(source.schemaId,'ARK_REAL_SOURCE_SEMANTICS_REPORT_V1');assert.equal(source.mode,'SOURCE_SEMANTICS_ONLY');assert.equal(source.strategyCalculated,false);assert.equal(source.readyForStrategy,false);locked(source.safety);
  assert.ok(Array.isArray(source.currentFeedObservations));const map=new Map();for(const f of source.currentFeedObservations){assert.equal(typeof f.symbol,'string');map.set(f.symbol,f);}const feeds=[...map.values()];
  const at=source.captureTimestamp??feeds.at(-1)?.captureTimestamp;const age=stamp(at)?Date.parse(now)-Date.parse(at):Infinity;const recent=age>=0&&age<=5000;
  const windows=source.latestRawWindowMetadata??[];assert.ok(Array.isArray(windows));
  const parity=windows.length>0&&windows.every(w=>w.normalizationParity==='PASS'&&typeof w.rawLatestSessionSourceTime==='string'&&w.rawLatestSessionSourceTime===w.normalizedLatestSourceTime)?'PASS':'UNVERIFIED';
  const src={feeds:feeds.map(f=>({symbol:f.symbol,price:finite(f.currentPrice)?f.currentPrice:null,bid:finite(f.bestBid)?f.bestBid:null,ask:finite(f.bestAsk)?f.bestAsk:null,marketTimestamp:stamp(f.marketTimestamp)?f.marketTimestamp:null,feedAgeMs:stamp(f.marketTimestamp)?Date.parse(now)-Date.parse(f.marketTimestamp):null,freshness:typeof f.freshnessState==='string'?f.freshnessState:'UNVERIFIED'})),rawLatest:windows[0]?.rawLatestSessionSourceTime??null,normalizedLatest:windows[0]?.normalizedLatestSourceTime??null,parity,finalizedLatest:null};
  out.source=src;const connected=recent&&source.connectionState==='REAL_SOURCE_CONNECTED_OBSERVED';
  out.components[0]={name:'MARKETSPEED II',status:connected?'CONNECTED':recent?'UNVERIFIED':'STALE',detail:'Observed source report; not proof of finality'};
  out.components[1]={name:'Excel RSS',status:connected?'CONNECTED':'UNVERIFIED',detail:'Read-only capture'};
  out.components[2]={name:'RSS Market',status:recent&&feeds.length&&feeds.every(f=>f.fresh===true)?'FRESH':recent?'UNVERIFIED':'STALE',detail:'Upstream feed freshness; bar age is separate'};
  out.components[3]={name:'RSS Chart',status:parity==='PASS'?(recent?'READY':'STALE'):'UNVERIFIED',detail:'RAW ↔ normalized only'};
  if(!recent)out.warnings.push('SOURCE_REPORT_STALE: static report is not a live heartbeat.');
  out.activity.push(...(source.events??[]).slice(-200).map(e=>({at:null,symbol:e.symbol??'',type:e.cause??'SOURCE EVENT',state:'REVIEW',reason:e.cause??'',category:'SOURCE',raw:e})));
 }catch(e){out.warnings.push('MALFORMED_SOURCE_STATUS: '+e.message);}
 if(execution)try{const v=executionView(execution);Object.assign(out,{portfolio:v.portfolio,positions:v.positions,execution:v.execution,mode:'FIXTURE_STATUS'});out.activity.push(...v.activity);out.components[7]={name:'Execution Layer',status:v.execution.mode,detail:'Synthetic execution snapshot only'};out.warnings.push('FIXTURE PORTFOLIO — not a real account.');}catch(e){out.warnings.push('MALFORMED_EXECUTION_STATUS: '+e.message);}
 return out;
}
