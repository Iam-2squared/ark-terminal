import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {freezeOwnershipBaseline} from './phase57_cash_upstream_request.mjs';

const FALSE_KEYS=[
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
];

function finitePositive(value,label){const n=Number(value);if(!Number.isFinite(n)||n<=0)throw Error(`${label}_INVALID`);return n;}

export function createInitialExternalOwnershipBaseline(snapshot,{
  confirmAllCurrentPositionsExternal=false,
  now=new Date(),
  maxAgeSeconds=120,
}={}){
  if(confirmAllCurrentPositionsExternal!==true)throw Error('EXPLICIT_EXTERNAL_OWNERSHIP_CONFIRMATION_REQUIRED');
  if(!snapshot||snapshot.schemaId!=='ARK_ACCOUNT_READONLY_SNAPSHOT_V2')throw Error('ACCOUNT_SNAPSHOT_SCHEMA_REQUIRED');
  if(snapshot.source!=='MARKETSPEED_II_RSS'||snapshot.mode!=='READ_ONLY')throw Error('READ_ONLY_MSII_SNAPSHOT_REQUIRED');
  for(const key of FALSE_KEYS)if(snapshot.safety?.[key]!==false)throw Error(`UNSAFE_SNAPSHOT:${key}`);
  if(!Array.isArray(snapshot.positions)||!Array.isArray(snapshot.orders)||!Array.isArray(snapshot.executions))throw Error('ACCOUNT_ARRAYS_REQUIRED');
  if(snapshot.orders.length)throw Error('OPEN_BROKER_ORDERS_PRESENT');
  if(snapshot.executions.length)throw Error('EXECUTIONS_PRESENT_DURING_BASELINE_CAPTURE');
  const captured=Date.parse(String(snapshot.capturedAt??''));
  const current=now instanceof Date?now.getTime():Date.parse(String(now));
  const maxAge=Number(maxAgeSeconds);
  if(!Number.isFinite(captured)||!Number.isFinite(current)||!Number.isFinite(maxAge)||maxAge<=0)throw Error('BASELINE_FRESHNESS_INPUT_INVALID');
  const age=(current-captured)/1000;
  if(age<0)throw Error('ACCOUNT_SNAPSHOT_FROM_FUTURE');
  if(age>maxAge)throw Error('ACCOUNT_SNAPSHOT_TOO_OLD_FOR_BASELINE');
  const externalPositions=snapshot.positions.map((row,index)=>{
    const symbol=String(row?.symbol??'').trim().toUpperCase();
    if(!/^[0-9A-Z]{4}(?:\.T)?$/.test(symbol))throw Error(`POSITION_${index}_IDENTITY_UNRESOLVED`);
    return {symbol,quantity:finitePositive(row?.quantity,`POSITION_${index}_QUANTITY`)};
  });
  return freezeOwnershipBaseline({
    capturedAt:new Date(captured).toISOString(),
    source:'MARKETSPEED_II_RSS_INITIAL_EXTERNAL_BASELINE',
    externalPositions,
    arkManagedPositions:[],
  });
}

function parseArgs(argv){const out={};for(let i=2;i<argv.length;i+=2){if(!argv[i]?.startsWith('--')||argv[i+1]===undefined)throw Error('USAGE');out[argv[i].slice(2)]=argv[i+1];}return out;}
const isMain=process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]);
if(isMain){
  try{
    const args=parseArgs(process.argv);
    if(!args.snapshot||!args.output)throw Error('USAGE');
    if(args['confirm-all-current-positions-external']!=='YES')throw Error('EXPLICIT_EXTERNAL_OWNERSHIP_CONFIRMATION_REQUIRED');
    const snapshot=JSON.parse(fs.readFileSync(args.snapshot,'utf8'));
    const baseline=createInitialExternalOwnershipBaseline(snapshot,{confirmAllCurrentPositionsExternal:true,maxAgeSeconds:args['max-age-seconds']===undefined?120:Number(args['max-age-seconds'])});
    if(fs.existsSync(args.output))throw Error('OUTPUT_ALREADY_EXISTS');
    fs.writeFileSync(args.output,JSON.stringify(baseline,null,2));
    console.log('CASH_OWNERSHIP_BASELINE_FROZEN');
    console.log(`BASELINE_SHA256=${baseline.baselineSha256}`);
  }catch(error){console.error(`CASH_OWNERSHIP_BASELINE_ERROR:${error.message}`);process.exitCode=2;}
}
