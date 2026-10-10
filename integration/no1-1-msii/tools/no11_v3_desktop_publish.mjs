// READ ONLY V3 candidate -> validated private desktop snapshot/health/Capital preview.
// Never opens Excel, transmits orders, resets Safety, or certifies broker feed arrival.
// No synthetic or old "last good" snapshot can be substituted on a failed capture.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {check} from './no11_desktop_cash_preview.mjs';

const METHOD='ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION';
const BASIS='FINAL_STATUS_RE_READ_NOT_MARKET_SOURCE_TIMESTAMP';
const ID_PATTERN=/^[a-f0-9]{32}$/;
const MAX_JSON_BYTES=2*1024*1024;
const LIMIT_SECONDS=25;
const disallow=x=>{throw Error(x);};
function directory(name,label) {
  const stat=fs.lstatSync(name);
  if(!stat.isDirectory()||stat.isSymbolicLink())disallow(label);
}
function readPrivate(name,label) {
  const stat=fs.lstatSync(name);
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size>MAX_JSON_BYTES)disallow(label);
  return JSON.parse(fs.readFileSync(name,'utf8'));
}
function sha(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}
function preparePrivateFile(name,value) {
  if(fs.existsSync(name)) {
    const stat=fs.lstatSync(name);
    if(!stat.isFile()||stat.isSymbolicLink())disallow('UNSAFE_PUBLISH_TARGET');
  }
  const temp=name+'.v3-tmp-'+crypto.randomBytes(12).toString('hex');
  const fd=fs.openSync(temp,'wx',0o600);
  try{fs.writeFileSync(fd,value,'utf8');fs.fsyncSync(fd);}
  finally{fs.closeSync(fd);}
  return {temp,name};
}

export function publishNo11V3ReadOnly({privateRoot,runId,now=new Date()}={}) {
  if(typeof privateRoot!=='string'||!path.isAbsolute(privateRoot))disallow('PRIVATE_ROOT_REQUIRED');
  if(typeof runId!=='string'||!ID_PATTERN.test(runId))disallow('V3_RUN_ID_INVALID');
  const root=path.resolve(privateRoot);
  const candidateBase=path.join(root,'capture-v3-candidate');
  const runDir=path.join(candidateBase,runId);
  directory(root,'PRIVATE_ROOT_UNSAFE');
  directory(candidateBase,'PRIVATE_CANDIDATE_ROOT_UNSAFE');
  directory(runDir,'V3_RUN_DIRECTORY_UNSAFE');
  const snap=readPrivate(path.join(runDir,'snapshot.json'),'V3_SNAPSHOT_UNSAFE');
  const health=readPrivate(path.join(runDir,'source-health.json'),'V3_HEALTH_UNSAFE');
  const baseline=readPrivate(path.join(root,'ownership-baseline.json'),'PRIVATE_OWNERSHIP_UNSAFE');
  if(snap.captureMethod!==METHOD||snap.mode!=='READ_ONLY' ||
      health.observationBasis!==BASIS||health.actualFeedTimestampCertified!==false) {
    disallow('V3_CAPTURE_OR_OBSERVATION_CONTRACT_INVALID');
  }
  const captured=Date.parse(snap.capturedAt),completed=Date.parse(snap.captureCompletedAt);
  if(!Number.isFinite(captured)||!Number.isFinite(completed)||completed<captured||
     completed-captured>=LIMIT_SECONDS*1000) {
    disallow('V3_CAPTURE_DURATION_UNVERIFIED');
  }
  const result=check({snapshot:snap,health,ownership:baseline,now});
  if(result.status!=='READ_ONLY_CAPITAL_PREVIEW'||result.productionReady!==false||
     result.orderTransmission!==false||!result.arkCapitalInputs||
     result.personalStockDoubleDeducted!==false) {
    disallow('V3_CAPITAL_OR_OWNERSHIP_GATE_BLOCKED');
  }
  // Recheck immediately prior to publication; never give an aged snapshot a fresh stamp.
  const last=check({snapshot:snap,health,ownership:baseline,now:new Date()});
  if(last.status!=='READ_ONLY_CAPITAL_PREVIEW')disallow('V3_SNAPSHOT_EXPIRED_BEFORE_PUBLISH');
  const snapJSON=JSON.stringify(snap,null,2)+'\n';
  const healthJSON=JSON.stringify(health,null,2)+'\n';
  const reportJSON=JSON.stringify(last,null,2)+'\n';
  // All three JSON outputs are prepared before the first official destination changes.
  // Atomic replacements are per file; a mid-commit crash is NOT a successful poll.
  const receiptJSON=JSON.stringify({
    schemaId:'ARK_NO11_V3_READONLY_PUBLISH_RECEIPT_V1',
    captureRunId:runId, snapshotSha256:sha(snapJSON),healthSha256:sha(healthJSON),
    capitalPreviewSha256:sha(reportJSON),captureCompletedAt:snap.captureCompletedAt,
    realBrokerFeedTimestampCertified:false,productionReady:false,transmitted:false
  },null,2)+'\n';
  const items=[
    ['snapshot.json',snapJSON],['source-health.json',healthJSON],
    ['desktop-capital-readonly.json',reportJSON],
    ['desktop-v3-readonly-receipt.json',receiptJSON]
  ];
  const prepared=[];
  try {
    for(const [filename,json] of items)prepared.push(preparePrivateFile(path.join(root,filename),json));
    for(const {temp,name} of prepared)fs.renameSync(temp,name);
  } finally {
    for(const {temp} of prepared)if(fs.existsSync(temp))fs.unlinkSync(temp);
  }
  return Object.freeze({status:'READ_ONLY_CAPITAL_PREVIEW',runId,readOnly:true,
    productionReady:false,orderTransmission:false,actualFeedTimestampCertified:false});
}

const isCli=process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url));
if(isCli) {
  try {
    if(process.argv.length!==3||!process.env.LOCALAPPDATA)disallow('V3_CLI_INPUT_INVALID');
    const root=path.join(process.env.LOCALAPPDATA,'ArkTerminal','No11');
    const result=publishNo11V3ReadOnly({privateRoot:root,runId:process.argv[2]});
    console.log('NO11_DESKTOP_CAPITAL='+result.status);
    console.log('NO11_V3_DESKTOP_SNAPSHOT_PUBLISHED=READ_ONLY_VALIDATED');
    console.log('ACTUAL_FEED_TIMESTAMP_CERTIFIED=FALSE');
    console.log('PRODUCTION_READY=FALSE');
    console.log('TRANSMITTED=FALSE');
  } catch {
    // No file paths, cash, stock symbols, holdings, or parse errors on public output.
    console.error('NO11_V3_DESKTOP_PUBLISH_BLOCKED=READ_ONLY_GATE_OR_PRIVATE_IO');
    console.error('PRODUCTION_READY=FALSE');
    console.error('TRANSMITTED=FALSE');
    process.exitCode=2;
  }
}
