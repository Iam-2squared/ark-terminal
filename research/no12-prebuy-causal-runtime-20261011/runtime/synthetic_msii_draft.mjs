/**
 * No.1.2 MSII CASH order preview, TEXT ONLY, trigger always 0.
 * Does not create an Excel formula cell, call RSS, reserve actual broker IDs,
 * enable any trade, nor pretend synthetic First Entry is live certified.
 * Mirrors the verified 20-argument original No.1.1 draft contract.
 */
import {digest} from '../../../integration/no1-1-msii/runtime/locked_intent.mjs';
import {orderInstant,currentOrderInstant,validMsiiOrderId,validateMsiiOrderIds,NS_PER_MS} from './no11_order_boundary.mjs';
import {compileCashOrderArguments} from './no11_msii_argument_contract.mjs';
export const NO12_ORDER_INTENT_SCHEMA='ARK_NO12_SYNTHETIC_ORDER_INTENT_V1';
const fail=x=>{throw Error(x)};
const txt=x=>{
 const s=String(x);
 return s!==''&&/^-?\d+(?:\.\d+)?$/.test(s)?s:'"'+s.replace(/"/g,'""')+'"';
};
export function buildNo12SyntheticMsiiOrderText({intent,orderIdentity,now=new Date()}={}){
 if(!intent||intent.schemaId!==NO12_ORDER_INTENT_SCHEMA||
     intent.evidenceMode!=='SYNTHETIC_OFFLINE_ONLY'||intent.transmitted!==false||
     intent.productionReady!==false||intent.executionAllowed===true)
    fail('NO12_LIVE_OR_UNVERIFIED_INTENT_REJECTED');
 const {intentSha256,...body}=intent;
 if(typeof intentSha256!=='string'||digest(body)!==intentSha256)
   fail('NO12_INTENT_CHECKSUM_INVALID');
 if(!/^[0-9A-Z]{4}\.T$/.test(intent.symbol??''))fail('NO12_BROKER_SYMBOL_NOT_VERIFIED');
 if(!Number.isSafeInteger(intent.quantity)||intent.quantity<100||
     intent.quantity%100!==0)fail('NO12_100_SHARE_LOT_REQUIRED');
 if(!((intent.side==='BUY'&&intent.positionEffect==='OPEN')||
      (intent.side==='SELL'&&intent.positionEffect==='CLOSE')))
   fail('NO12_CASH_LONG_SIDE_EFFECT_MISMATCH');
 if(intent.cashOnly!==true||intent.marginAllowed!==false||
     intent.shortSellingAllowed!==false)fail('NO12_CASH_ACCOUNT_ONLY');
 if(intent.side==='BUY'&&intent.syntheticCashAndSlotReserved!==true)
   fail('NO12_BUY_NEEDS_SYNTHETIC_CASH_AND_SLOT_RESERVATION');
 if(intent.side==='SELL'&&intent.syntheticArkOwnedPosition!==true)
   fail('NO12_EXTERNAL_SELL_REJECTED');
 if(intent.timeInForce!=='DAY'||typeof intent.sor!=='boolean')fail('NO12_MSII_ORDER_POLICY_MISSING');
 if(!['MARKET','LIMIT'].includes(intent.orderType))fail('NO12_MSII_PRICE_TYPE_INVALID');
 if(intent.orderType==='MARKET'&&intent.limitPrice!==null)fail('NO12_MSII_MARKET_LIMIT_MUST_BE_NULL');
 if(intent.orderType==='LIMIT'&&(!Number.isFinite(intent.limitPrice)||intent.limitPrice<=0))
   fail('NO12_MSII_LIMIT_PRICE_INVALID');
 if(!Number.isSafeInteger(intent.accountType)||intent.accountType<0||intent.accountType>3||
    intent.accountTypeVerified!==true)fail('NO12_BROKER_ACCOUNT_TYPE_NOT_VERIFIED');
 if(!orderIdentity||orderIdentity.schemaId!=='ARK_NO12_SYNTHETIC_ORDER_ID_OBSERVATION_V1'||
    orderIdentity.evidenceMode!=='SYNTHETIC_OFFLINE_ONLY')fail('NO12_REAL_ORDER_ID_NOT_CERTIFIED');
 const time=orderInstant(orderIdentity.observedAt,'NO12_ORDER_ID_OBSERVATION_CLOCK_INVALID');
 const current=currentOrderInstant(now,'NO12_CURRENT_CLOCK_INVALID');
 if(time.ns>current.ns||current.ns-time.ns>30000n*NS_PER_MS)
   fail('NO12_ORDER_ID_SNAPSHOT_STALE');
 const id=orderIdentity.reservedOrderId;
 if(!validMsiiOrderId(id)||!Array.isArray(orderIdentity.usedOrderIds))
   fail('NO12_RSS_ID_NOT_AVAILABLE');
 const used=validateMsiiOrderIds(orderIdentity.usedOrderIds,'NO12_RSS_USED_ORDER_IDS_INVALID');
 if(used.has(id))fail('NO12_RSS_ORDER_ID_ALREADY_USED');
 if(orderIdentity.sourceIntentSha256!==intentSha256)fail('NO12_ORDER_ID_TO_INTENT_NOT_MATCHED');
 if(orderIdentity.syntheticUniquenessChecked!==true)fail('NO12_ORDER_ID_DUPLICATE_RISK');
 const args=compileCashOrderArguments({...intent,rssOrderId:id});
 if(args.length!==20)fail('NO12_MSII_ARGUMENT_COUNT_WRONG');
 const core={
  schemaId:'ARK_NO12_MSII_TEXT_DRAFT_V1',evidenceMode:'SYNTHETIC_OFFLINE_ONLY',
  sourceIntentSha256:intentSha256,rssOrderId:id,function:'RssStockOrder',
  arguments:args,formulaText:'='+['Rss','Stock','Order'].join('')+'('+args.map(txt).join(',')+')',
  formulaCellType:'TEXT',trigger:0,
  formulaEvaluationAllowed:false,orderTransmission:false,
  productionReady:false,excelOrderWriteAllowed:false,
  brokerOrderIdActuallyReserved:false,brokerOrderActuallySubmitted:false
 };
 return Object.freeze({...core,draftSha256:digest(core)});
}
