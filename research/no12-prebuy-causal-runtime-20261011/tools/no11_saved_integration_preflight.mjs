#!/usr/bin/env node
/**
 * Offline-only CLI to confirm actual saved 2026 RSS summary receipts chain to
 * the provisional H2/H3/H5 Shadow integration readiness. NO orders, NO Excel.
 *
 * node no11_saved_integration_preflight.mjs --private-root "<user private dir>"
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {
  readNo11SavedIntegrationReports,
  inspectNo11SavedIntegrationReadiness
} from '../runtime/no11_saved_integration_preflight.mjs';

const bad=s=>{throw Error(s)};
function run(){
 const args=process.argv.slice(2);
 if(args.length!==2||args[0]!=='--private-root')bad('NO11_INTEGRATION_CLI_USAGE_INVALID');
 const privateRoot=path.resolve(args[1]);
 const receipts=readNo11SavedIntegrationReports({privateRoot});
 const result=inspectNo11SavedIntegrationReadiness(receipts);
 const data=Buffer.from(JSON.stringify(result,null,2)+'\n','utf8');
 const sha=createHash('sha256').update(data).digest('hex');
 const filename=path.join(privateRoot,'no11-provisional-integration-preflight-'+sha.slice(0,16)+'.json');
 if(fs.existsSync(filename)){
   const st=fs.lstatSync(filename);
   if(!st.isFile()||st.isSymbolicLink()||
      !fs.readFileSync(filename).equals(data))
      bad('NO11_INTEGRATION_EXISTING_REPORT_CHANGED');
 } else {
   const fd=fs.openSync(filename,'wx',0o600);
   try{
     fs.writeSync(fd,data,0,data.length,0);
     fs.fsyncSync(fd);
   } finally{fs.closeSync(fd);}
 }
 console.log('NO11_PROVISIONAL_INTEGRATION_READONLY_PREFLIGHT=PASS_SOURCE_ONLY');
 console.log('NO11_INTEGRATION_2025_H235_TRAINING=PROVISIONAL_COMPLETE');
 console.log('NO11_INTEGRATION_2026_RSS_PRICE_ANCHORS='+result.source.fixedClockPriceAnchors);
 console.log('NO11_INTEGRATION_2026_COMPLETE_FUTURE='+result.source.completeFutureObserved);
 console.log('NO11_INTEGRATION_NATIVE_SELECTOR_CONNECTED=False');
 console.log('NO11_INTEGRATION_NATIVE_CAPITAL_EXIT_CONNECTED=False');
 console.log('NO11_INTEGRATION_REPORT='+filename);
 console.log('NO11_PRODUCTION_READY=False');
 console.log('ORDER_TRANSMISSION=False');
}
try{run();}
catch(e){
 console.error('NO11_PROVISIONAL_INTEGRATION_READONLY_PREFLIGHT=BLOCKED:'+e.message);
 console.error('NO11_PRODUCTION_READY=False');
 console.error('ORDER_TRANSMISSION=False');
 process.exitCode=2;
}
