/**
 * Optional local-only FIRST ENTRY historical clock parity check.
 * Reads only an EXPLICIT local archived FIRST_ENTRY_*.jsonl[.gz]; never commits
 * it, sends it over the network, or prints symbols, prices, IDs or file paths.
 * Date-wise research simulation is not a live broker execution certificate.
 */
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import readline from 'node:readline';
import {fileURLToPath} from 'node:url';
import {summarizeNo11OriginalClockParity} from '../runtime/frozen_first_entry_timing_audit.mjs';
const fail=x=>{throw Error(x)};
const FAMILIES=new Set(['P0','P1']), POLICIES=new Set(['Q70','Q80','Q90','Q95']);
export async function auditPrivateOriginalFirstEntryClocks({
 localInputPath,family='P1',policy='Q70',maxRows=100000
}={}){
 if(typeof localInputPath!=='string'||!path.isAbsolute(localInputPath)||
    !/\.jsonl(?:\.gz)?$/.test(localInputPath))fail('NO11_LOCAL_SOURCE_PATH_INVALID');
 if(!FAMILIES.has(family)||!POLICIES.has(policy)||
    !Number.isSafeInteger(maxRows)||maxRows<1||maxRows>100000)
  fail('NO11_LOCAL_AUDIT_ARGUMENT_INVALID');
 const stats=fs.lstatSync(localInputPath);
 if(!stats.isFile()||stats.isSymbolicLink()||stats.size>800000000)
  fail('NO11_LOCAL_SOURCE_UNSAFE');
 let src=fs.createReadStream(localInputPath);
 if(localInputPath.endsWith('.gz'))src=src.pipe(zlib.createGunzip());
 const input=readline.createInterface({input:src,crlfDelay:Infinity});
 const rows=[];
 let considered=0,noIntent=0,nonSelected=0;
 try{
  for await (const line of input){
   if(!line.trim())continue;
   const item=JSON.parse(line);
   if(item?.family!==family||item?.policy!==policy){nonSelected++;continue;}
   considered++;
   if(considered>maxRows)fail('NO11_PRIVATE_AUDIT_MAX_ROWS');
   if(!item.first_intent){noIntent++;continue;}
   rows.push(item);
  }
 }finally{input.close();}
 if(considered===0)fail('NO11_PRIVATE_AUDIT_NO_MATCHING_ROWS');
 if(rows.length===0)fail('NO11_PRIVATE_AUDIT_NO_FIRST_INTENT_ROWS');
 const results=summarizeNo11OriginalClockParity({mode:'SYNTHETIC_OFFLINE_ONLY',rows});
 return Object.freeze({status:results.status,family,policy,selectedRecords:considered,
  noFirstIntentRecords:noIntent,ignoredOtherPolicyRecords:nonSelected,
  ...results,readOnly:true,privateRowsExported:false,privateSourceRssUsed:false,
  modelScoreComputed:false,brokerOrderAllowed:false,productionReady:false});
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const args=process.argv.slice(2);
  if(args.length!==6||args[0]!=='--private-first-entry-jsonl'||
    args[2]!=='--family'||args[4]!=='--policy')fail('NO11_LOCAL_AUDIT_USAGE');
  const result=await auditPrivateOriginalFirstEntryClocks({
    localInputPath:args[1],family:args[3],policy:args[5]});
  // Intentionally only aggregate counts, no private evidence or file paths.
  console.log(JSON.stringify(result,null,2));
 }catch{
  console.error('NO11_FROZEN_FIRST_ENTRY_CLOCK_AUDIT=BLOCKED');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
