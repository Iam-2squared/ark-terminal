/**
 * TEXT-ONLY representation of MarketSpeed II's 20-argument RssStockOrder.
 * No Excel formula is written/evaluated, no RSS function call, no transmission.
 *
 * Order-ID uniqueness observation is a necessary but not sufficient real-order
 * certificate. It must be rechecked against the actual broker just before any
 * separately authorized future live order. This module cannot enable live.
 */
import {digest} from './locked_intent.mjs';

const fail=s=>{throw Error(s)};
function when(s,label){
  if(typeof s!=='string'||!/(Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s)))fail(label);
  return Date.parse(s);
}
function integer(n,label){if(!Number.isSafeInteger(n)||n<1)fail(label);return n;}
function excelArg(x){
  const value=String(x);
  if(value!==''&&/^-?\d+(?:\.\d+)?$/.test(value))return value;
  return '"'+value.replace(/"/g,'""')+'"';
}
export function makeLockedMsiiDraft(intent,identity,{now=new Date()}={}){
  if(!intent||intent.schemaId!=='ARK_NO11_CASH_LOCKED_INTENT_V1')fail('NO11_LOCKED_INTENT_REQUIRED');
  const {lockedIntentSha256,...core}=intent;
  if(lockedIntentSha256!==digest(core)||intent.executable!==false||intent.transmitted!==false)fail('UNSAFE_OR_UNVERIFIED_INTENT');
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','transmitted']){
    if(intent.safety?.[key]!==false)fail('TRANSMISSION_FLAG_UNSAFE:'+key);
  }
  if(!identity||identity.schemaId!=='ARK_MSII_ORDER_ID_READONLY_OBSERVATION_V1')fail('ORDER_ID_OBSERVATION_REQUIRED');
  const {observationSha256,...source}=identity;
  if(observationSha256!==digest(source))fail('ORDER_ID_OBSERVATION_HASH_MISMATCH');
  if(identity.source!=='MARKETSPEED_II_RSS_ORDER_ID_LIST'||identity.readOnly!==true)fail('ORDER_ID_NOT_BROKER_READ_ONLY');
  const ms=when(identity.capturedAt,'ORDER_ID_TIMESTAMP_INVALID');
  const nowMs=now instanceof Date?+now:when(now,'NOW_INVALID');
  if(ms>nowMs+1000||nowMs-ms>30000)fail('ORDER_ID_SNAPSHOT_STALE');
  const id=integer(identity.reservedOrderId,'ORDER_ID_INVALID');
  if(!Array.isArray(identity.usedOrderIds))fail('USED_ORDER_IDS_UNAVAILABLE');
  const used=new Set();
  for(const n of identity.usedOrderIds){
    integer(n,'USED_ORDER_ID_INVALID');
    if(used.has(n))fail('USED_ORDER_ID_DUPLICATE');
    used.add(n);
  }
  if(used.has(id))fail('ORDER_ID_ALREADY_USED');
  if(identity.sourceIntentId!==intent.sourceIntentId||identity.sourceIntentHash!==intent.lockedIntentSha256)fail('ORDER_ID_INTENT_PROOF_MISMATCH');
  if(identity.confirmedUniqueAcrossLocalWorkbooks!==true)fail('ORDER_ID_LOCAL_COLLISION_NOT_EXCLUDED');
  const sideCode=intent.side==='BUY'?'3':intent.side==='SELL'?'1':fail('MSII_SIDE_INVALID');
  const priceCode=intent.orderType==='MARKET'?'0':intent.orderType==='LIMIT'?'1':fail('MSII_ORDER_TYPE_INVALID');
  if(!Number.isInteger(intent.accountType)||intent.accountType<0||intent.accountType>3)fail('MSII_ACCOUNT_TYPE_INVALID');
  const args=[
    String(id),'0',intent.symbol,sideCode,'0',intent.sor?'1':'0',
    String(intent.quantity),priceCode,intent.orderType==='MARKET'?'':String(intent.limitPrice),
    '1','',String(intent.accountType),'','','','','0','','',''
  ];
  if(args.length!==20)fail('MSII_ARG_COUNT_MISMATCH');
  const coreDraft={
    schemaId:'ARK_NO11_MSII_TEXT_ONLY_DRAFT_V1',sourceIntentSha256:intent.lockedIntentSha256,
    brokerOrderId:id,function:'RssStockOrder',arguments:args,
    formulaText:'=RssStockOrder('+args.map(excelArg).join(',')+')',
    formulaCellType:'TEXT',trigger:0,formulaEvaluationAllowed:false,
    cashOnly:true,marginAllowed:false,shortSellingAllowed:false,
    executable:false,transmitted:false,brokerWriteAllowed:false,
    excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
    liveOrderIdReconciliationCertified:false,
  };
  return {...coreDraft,draftSha256:digest(coreDraft)};
}
