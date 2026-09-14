import assert from 'node:assert/strict';

export const MSII_RSS_SPEC_DATE='2026-03-30';
export const ORDER_FUNCTIONS=Object.freeze({CASH:'RssStockOrder',MARGIN_OPEN:'RssMarginOpenOrder',MARGIN_CLOSE:'RssMarginCloseOrder',MODIFY:'RssModifyOrder',CANCEL:'RssCancelOrder'});
export const OBSERVATION_FUNCTIONS=Object.freeze(['RssOrderList','RssExecutionList','RssPositionList','RssMarginPositionList','RssCapacityList','RssBuyingPower','RssMarginPower','RssOrderIDList','RssOrderStatus']);
const sideCode=side=>{assert.ok(['BUY','SELL'].includes(side),'MSII_SIDE_REQUIRED');return side==='BUY'?'3':'1';};
const priceFields=intent=>{assert.ok(['MARKET','LIMIT'].includes(intent.orderType),'MSII_ORDER_TYPE_REQUIRED');if(intent.orderType==='MARKET'){assert.equal(intent.limitPrice,null,'MARKET_LIMIT_PRICE_MUST_BE_NULL');return ['0',''];}assert.ok(Number.isFinite(intent.limitPrice)&&intent.limitPrice>0,'MSII_LIMIT_PRICE_REQUIRED');return ['1',String(intent.limitPrice)];};
const q=x=>{assert.ok(Number.isSafeInteger(x)&&x>0&&x%100===0,'MSII_LOT_QUANTITY_REQUIRED');return String(x);};
const id=x=>{assert.ok(Number.isSafeInteger(x)&&x>=1,'MSII_ORDER_ID_REQUIRED');return String(x);};
const symbol=x=>{assert.match(x,/^[0-9A-Z]{4}\.T$/,'MSII_TSE_SYMBOL_REQUIRED');return x;};
const code=x=>{assert.ok(['0','1','2','3','4','5','6','7'].includes(String(x)),'MSII_CODE_INVALID');return String(x);};
const date=x=>{assert.match(x,/^\d{8}$/,'MSII_YYYYMMDD_REQUIRED');return x;};
const num=x=>{assert.ok(Number.isFinite(x)&&x>0,'MSII_POSITIVE_NUMBER_REQUIRED');return String(x);};
const esc=x=>`"${String(x).replaceAll('"','""')}"`;
const quoted=x=>Object.freeze({excelQuoted:String(x)});
const arg=x=>x&&typeof x==='object'&&Object.hasOwn(x,'excelQuoted')?esc(x.excelQuoted):typeof x==='string'&&/^-?\d+(?:\.\d+)?$/.test(x)?x:esc(x??'');
export const excelFormula=(fn,args)=>`=${fn}(${args.map(arg).join(',')})`;

export function lockedOrderFormula(intent,routing){
  assert.equal(intent.timeInForce,'DAY','MSII_DAY_ONLY');
  const trigger='0';
  const [priceType,price]=priceFields(intent);const common=[id(routing.orderId),trigger,symbol(intent.symbol),sideCode(intent.side),'0',code(routing.sor??0)];
  const execution='1',expiry='',account=code(routing.accountType??0);
  if(routing.product==='CASH'){
    assert.equal(intent.direction,'LONG','CASH_SHORT_UNSUPPORTED');
    return {function:ORDER_FUNCTIONS.CASH,trigger:0,transmitted:false,formula:excelFormula(ORDER_FUNCTIONS.CASH,[...common,q(intent.quantity),priceType,price,execution,expiry,account,'','','','', '0','','',''])};
  }
  assert.equal(routing.product,'MARGIN','MSII_PRODUCT_REQUIRED');
  const marginType=code(routing.marginType);
  if(intent.positionEffect==='OPEN')return {function:ORDER_FUNCTIONS.MARGIN_OPEN,trigger:0,transmitted:false,formula:excelFormula(ORDER_FUNCTIONS.MARGIN_OPEN,[...common,marginType,q(intent.quantity),priceType,price,execution,expiry,account,'','','','', '0','','','',''])};
  assert.ok(routing.openPosition,'MSII_OPEN_POSITION_REQUIRED');
  return {function:ORDER_FUNCTIONS.MARGIN_CLOSE,trigger:0,transmitted:false,formula:excelFormula(ORDER_FUNCTIONS.MARGIN_CLOSE,[...common,marginType,q(intent.quantity),priceType,price,execution,expiry,account,quoted(date(routing.openPosition.openDate)),num(routing.openPosition.openPrice),code(routing.openPosition.openMarket),'','','',''])};
}

export function lockedCancelFormula({orderId,targetOrderNumber}){
  assert.ok(Number.isSafeInteger(targetOrderNumber)&&targetOrderNumber>0,'MSII_TARGET_ORDER_NUMBER_REQUIRED');
  return {function:ORDER_FUNCTIONS.CANCEL,trigger:0,transmitted:false,formula:excelFormula(ORDER_FUNCTIONS.CANCEL,[id(orderId),'0',String(targetOrderNumber)])};
}

export function observationFormulas(symbolCode){
  const s=symbol(symbolCode);
  return Object.freeze({orderList:'=RssOrderList(TRUE,"","","","","","","","","")',executionList:'=RssExecutionList(TRUE,"","","","","")',cashPositions:`=RssPositionList(TRUE,"${s}","")`,marginPositions:`=RssMarginPositionList(TRUE,"${s}","","","","")`,capacity:'=RssCapacityList(TRUE)',buyingPower:`=RssBuyingPower(TRUE,"${s}")`,marginPower:`=RssMarginPower(TRUE,"${s}")`,usedOrderIds:'=RssOrderIDList(TRUE)'});
}
