import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {buildCashExecutionIntentFromShadowIntent} from '../predict/realtime/phase57-cash-execution-adapter.js';

export const CASH_UPSTREAM_ACTION_SCHEMA='ARK_CASH_UPSTREAM_ACTION_V1';
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])])):value;
const sha256=value=>createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');

export function cashUpstreamActionFromShadowIntent(shadowIntent){
  const cash=buildCashExecutionIntentFromShadowIntent(shadowIntent);
  const core={
    schemaId:CASH_UPSTREAM_ACTION_SCHEMA,
    sourceType:'PHASE57_SHADOW_ORDER_INTENT',
    symbol:cash.symbol,
    direction:'LONG',
    side:cash.side,
    positionEffect:cash.positionEffect,
    quantity:cash.quantity,
    orderType:cash.orderType,
    limitPrice:cash.limitPrice,
    timeInForce:cash.timeInForce,
    estimatedNotional:cash.estimatedNotional,
    sourceRequestedNotional:cash.sourceRequestedNotional,
    lineage:cash.lineage,
    sourceCashExecutionIntentSha256:cash.cashExecutionIntentSha256,
    cashOnly:true,
    marginAllowed:false,
    shortSellingAllowed:false,
    marginFallbackAllowed:false,
    executable:false,
    transmitted:false,
  };
  return Object.freeze({...core,actionSha256:sha256(core)});
}

export function validateCashUpstreamAction(action){
  if(!action||action.schemaId!==CASH_UPSTREAM_ACTION_SCHEMA)throw Error('CASH_UPSTREAM_ACTION_SCHEMA_REQUIRED');
  const {actionSha256,...core}=action;
  if(!/^[a-f0-9]{64}$/i.test(String(actionSha256??''))||sha256(core)!==actionSha256)throw Error('CASH_UPSTREAM_ACTION_HASH_MISMATCH');
  if(action.direction!=='LONG'||action.cashOnly!==true||action.marginAllowed!==false||action.shortSellingAllowed!==false||action.marginFallbackAllowed!==false)throw Error('CASH_UPSTREAM_ACTION_NOT_LONG_CASH_ONLY');
  if(action.executable!==false||action.transmitted!==false)throw Error('CASH_UPSTREAM_ACTION_NOT_LOCKED');
  if(!/^[0-9A-Z]{4}\.T$/.test(String(action.symbol??'')))throw Error('CASH_UPSTREAM_ACTION_SYMBOL_INVALID');
  if(!Number.isInteger(action.quantity)||action.quantity<=0||action.quantity%100!==0)throw Error('CASH_UPSTREAM_ACTION_LOT_INVALID');
  if(![['BUY','OPEN'],['SELL','CLOSE']].some(([side,effect])=>side===action.side&&effect===action.positionEffect))throw Error('CASH_UPSTREAM_ACTION_SIDE_EFFECT_INVALID');
  if(!Number.isFinite(Number(action.estimatedNotional))||Number(action.estimatedNotional)<=0)throw Error('CASH_UPSTREAM_ACTION_NOTIONAL_INVALID');
  return action;
}

function parseArgs(argv){
  const out={};
  for(let i=2;i<argv.length;i+=2){const key=argv[i],value=argv[i+1];if(!key?.startsWith('--')||value===undefined)throw Error('USAGE');out[key.slice(2)]=value;}
  return out;
}

if(import.meta.url===`file://${process.argv[1].replaceAll('\\','/')}`){
  try{
    const args=parseArgs(process.argv);
    if(!args.input||!args.output)throw Error('USAGE');
    const input=JSON.parse(fs.readFileSync(args.input,'utf8'));
    const action=args.mode==='validate'?validateCashUpstreamAction(input):cashUpstreamActionFromShadowIntent(input);
    const output=path.resolve(args.output);
    if(fs.existsSync(output))throw Error('OUTPUT_ALREADY_EXISTS');
    fs.writeFileSync(output,JSON.stringify(action,null,2));
    console.log(args.mode==='validate'?'CASH_UPSTREAM_ACTION_VALID':'CASH_UPSTREAM_ACTION_CREATED');
  }catch(error){console.error(`CASH_UPSTREAM_ACTION_ERROR:${error.message}`);process.exitCode=2;}
}
