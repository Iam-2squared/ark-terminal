/** Pure cash/DAY argument contract shared by inert previews and transport.
 * This module never writes Excel, reserves an ID or grants execution authority.
 */
import {validMsiiOrderId} from './no11_order_boundary.mjs';
const need=(ok,code)=>{if(!ok)throw Error('NO11_MSII_ARGS_'+code)};
export const MSII_CASH_ACCOUNTS=Object.freeze(['特定','一般','NISA（NISA成長投資枠）','旧NISA']);

function price(value){
 need(typeof value==='number'&&Number.isFinite(value)&&value>0,'PRICE');
 const text=String(value);
 need(/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(text)&&text.length<=32,'PRICE_FORMAT');
 return text;
}
export function compileCashOrderArguments({rssOrderId,symbol,side,quantity,orderType,limitPrice,timeInForce,sor,accountType}){
 need(validMsiiOrderId(rssOrderId),'RSS_ID');
 need(typeof symbol==='string'&&/^[0-9A-Z]{4}\.T$/.test(symbol),'SYMBOL');
 need(side==='BUY'||side==='SELL','SIDE');
 need(Number.isSafeInteger(quantity)&&quantity>=100&&quantity%100===0,'QUANTITY');
 need(orderType==='MARKET'||orderType==='LIMIT','ORDER_TYPE');
 need(timeInForce==='DAY'&&typeof sor==='boolean','POLICY');
 need(Number.isSafeInteger(accountType)&&accountType>=0&&accountType<MSII_CASH_ACCOUNTS.length,'ACCOUNT');
 need(orderType!=='MARKET'||limitPrice===null,'MARKET_PRICE');
 const limit=orderType==='LIMIT'?price(limitPrice):'';
 return Object.freeze([String(rssOrderId),'0',symbol,side==='BUY'?'3':'1','0',sor?'1':'0',
  String(quantity),orderType==='MARKET'?'0':'1',limit,'1','',String(accountType),'','','','','0','','','']);
}
export function compileCancelArguments({rssOrderId,orderNumber}){
 need(validMsiiOrderId(rssOrderId),'RSS_ID');
 need(typeof orderNumber==='string'&&/^[1-9]\d{0,14}$/.test(orderNumber)&&Number.isSafeInteger(Number(orderNumber)),'ORDER_NUMBER');
 return Object.freeze([String(rssOrderId),'0',orderNumber]);
}
export function verifyMsiiArguments(functionName,args){
 need(Array.isArray(args)&&args.every(x=>typeof x==='string'&&x.length<=64),'ARRAY');
 let expected;
 if(functionName==='RssStockOrder'){
  need(args.length===20,'COUNT');
  need(/^[1-9]\d*$/.test(args[0])&&/^[1-9]\d*$/.test(args[6])&&/^[0-3]$/.test(args[11]),'INTEGER');
  need(['1','3'].includes(args[3])&&['0','1'].includes(args[5])&&['0','1'].includes(args[7]),'ENUM');
  expected=compileCashOrderArguments({rssOrderId:Number(args[0]),symbol:args[2],side:args[3]==='3'?'BUY':'SELL',
   quantity:Number(args[6]),orderType:args[7]==='0'?'MARKET':'LIMIT',limitPrice:args[7]==='0'?null:Number(args[8]),
   timeInForce:'DAY',sor:args[5]==='1',accountType:Number(args[11])});
 }else{
  need(functionName==='RssCancelOrder'&&args.length===3,'FUNCTION_OR_COUNT');
  need(/^[1-9]\d*$/.test(args[0]),'INTEGER');
  expected=compileCancelArguments({rssOrderId:Number(args[0]),orderNumber:args[2]});
 }
 need(expected.length===args.length&&expected.every((x,i)=>x===args[i]),'NONCANONICAL_OR_UNSAFE');
 return expected;
}
export function msiiFormulaText(functionName,args){
 const values=verifyMsiiArguments(functionName,args);
 const literal=x=>x!==''&&/^-?\d+(?:\.\d+)?$/.test(x)?x:'"'+x.replaceAll('"','""')+'"';
 return '='+functionName+'('+values.map(literal).join(',')+')';
}
