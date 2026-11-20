// V3 bulk candidate -> existing READ ONLY Capital/Ownership gate, diagnostic only.
// Not part of the desktop/UI launcher, writes no reports or account data.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {check} from './no11_desktop_cash_preview.mjs';

const V3_METHOD='ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION';
const FINAL_OBSERVATION='FINAL_STATUS_RE_READ_NOT_MARKET_SOURCE_TIMESTAMP';
const safeCode=x=>typeof x==='string'&&/^(?:RSS_READ_ONLY_GATE_BLOCKED:)?[A-Z][A-Z0-9_]*(?::(?:capacity|orders|executions|positions))?$/.test(x)?x:'REDACTED_BLOCKER';

export function inspectV3CandidateCapital({snapshot,health,ownership,now=new Date()}={}) {
  if(snapshot?.captureMethod!==V3_METHOD || snapshot?.mode!=='READ_ONLY' ||
     health?.observationBasis!==FINAL_OBSERVATION ||
     health?.actualFeedTimestampCertified!==false) {
    return Object.freeze({status:'BLOCKED',blockers:['V3_OBSERVATION_CONTRACT_INVALID'],
      productionReady:false,actualBrokerDeliveryTimestampCertified:false,orderTransmission:false});
  }
  const result=check({snapshot,health,ownership,now});
  return Object.freeze({
    status:result.status,
    blockers:Object.freeze((result.blockers??[]).map(safeCode)),
    productionReady:false,
    actualBrokerDeliveryTimestampCertified:false,
    orderTransmission:false,
  });
}

function readFileStrict(file) {
  const info=fs.lstatSync(file);
  if(!info.isFile()||info.isSymbolicLink())throw Error('UNSAFE_PRIVATE_INPUT');
  return JSON.parse(fs.readFileSync(file,'utf8'));
}
const isCli=process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url));
if(isCli) {
  try {
    const runId=process.argv[2];
    if(process.argv.length!==3 || !/^[a-f0-9]{32}$/.test(runId??''))throw Error('CANDIDATE_RUN_ID_INVALID');
    if(!process.env.LOCALAPPDATA)throw Error('LOCAL_ROOT_MISSING');
    const local=path.join(process.env.LOCALAPPDATA,'ArkTerminal','No11');
    const candidateRoot=path.join(local,'capture-v3-candidate');
    const runDir=path.join(candidateRoot,runId);
    for(const dir of [local,candidateRoot,runDir]){
      const info=fs.lstatSync(dir);
      if(!info.isDirectory()||info.isSymbolicLink())throw Error('CANDIDATE_DIRECTORY_UNSAFE');
    }
    const snapshot=readFileStrict(path.join(runDir,'snapshot.json'));
    const health=readFileStrict(path.join(runDir,'source-health.json'));
    const ownership=readFileStrict(path.join(local,'ownership-baseline.json'));
    const result=inspectV3CandidateCapital({snapshot,health,ownership});
    console.log('NO11_V3_CAPITAL_STATUS='+result.status);
    for(const reason of result.blockers)console.log('NO11_V3_CAPITAL_BLOCKER='+reason);
    console.log('ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False');
    console.log('NO11_PRODUCTION_READY=False');
    console.log('ORDER_TRANSMISSION=False');
    if(result.status!=='READ_ONLY_CAPITAL_PREVIEW')process.exitCode=2;
  } catch {
    // Never print private data, paths, numerical account balances, JSON or stack traces.
    console.log('NO11_V3_CAPITAL_STATUS=BLOCKED');
    console.log('NO11_V3_CAPITAL_BLOCKER=PRIVATE_INPUT_OR_RUNTIME_INVALID');
    console.log('ACTUAL_BROKER_DELIVERY_TIMESTAMP_CERTIFIED=False');
    console.log('NO11_PRODUCTION_READY=False');
    console.log('ORDER_TRANSMISSION=False');
    process.exitCode=2;
  }
}
