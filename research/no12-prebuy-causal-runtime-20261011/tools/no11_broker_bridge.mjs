/** Pure JSON boundary for the Python coordinator. Never sends or opens Excel. */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {compileTransportCommand,validateTransportCommand,validateTransportConfiguration} from './no11_msii_transport.mjs';
import {normalizeBrokerObservation} from './no11_broker_snapshot.mjs';
const need=(v,c)=>{if(!v)throw Error('NO11_BROKER_BRIDGE_'+c)};
export function calculate(request){
 need(request&&typeof request==='object'&&!Array.isArray(request),'REQUEST');
 if(request.action==='compile')return compileTransportCommand(request.input);
 if(request.action==='validate-command')return validateTransportCommand(request.command);
 if(request.action==='normalize')return normalizeBrokerObservation(request.input);
 if(request.action==='validate-config')return validateTransportConfiguration(request.config,request.command,request.now);
 throw Error('NO11_BROKER_BRIDGE_ACTION');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{
  const input=fs.readFileSync(0);need(input.length>0&&input.length<=20000000,'SIZE');
  const result=calculate(JSON.parse(input.toString('utf8').replace(/^\uFEFF/,'')));
  process.stdout.write(JSON.stringify(result)+'\n');
 }catch(e){process.stderr.write(/^NO11_[A-Z0-9_:]+$/.test(e.message)?e.message:'NO11_BROKER_BRIDGE_INVALID');process.exitCode=2;}
}
