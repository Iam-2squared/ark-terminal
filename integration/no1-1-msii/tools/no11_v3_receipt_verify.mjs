// V3 READ ONLY published-source integrity check before and after UI2 model export.
// An interrupted multi-file update cannot supply a mixed-generation account model.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {check} from './no11_desktop_cash_preview.mjs';
const HASH=/^[0-9a-f]{64}$/,RUN=/^[0-9a-f]{32}$/,MAX_BYTES=2097152;
const invalid=()=>{throw Error('V3_PUBLISHED_SOURCE_RECEIPT_INVALID')};
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function dir(p){
  let stat;try{stat=fs.lstatSync(p)}catch{invalid()}
  if(!stat.isDirectory()||stat.isSymbolicLink())invalid();
}
function read(p){
  let stat;try{stat=fs.lstatSync(p)}catch{invalid()}
  if(!stat.isFile()||stat.isSymbolicLink()||stat.size<=0||stat.size>MAX_BYTES)invalid();
  try{
    const bytes=fs.readFileSync(p);
    return {hash:sha(bytes),value:JSON.parse(bytes.toString('utf8'))};
  }catch{invalid()}
}
export function verifyV3PublishedReceipt({privateRoot,now=new Date()}={}){
  if(typeof privateRoot!=='string'||!path.isAbsolute(privateRoot))invalid();
  const root=path.resolve(privateRoot);
  dir(root);
  const snap=read(path.join(root,'snapshot.json'));
  const health=read(path.join(root,'source-health.json'));
  const report=read(path.join(root,'desktop-capital-readonly.json'));
  const receipt=read(path.join(root,'desktop-v3-readonly-receipt.json')).value;
  if(receipt?.schemaId!=='ARK_NO11_V3_READONLY_PUBLISH_RECEIPT_V1'||
     !RUN.test(receipt.captureRunId??'')||
     receipt.productionReady!==false||receipt.transmitted!==false||
     receipt.realBrokerFeedTimestampCertified!==false)invalid();
  for(const [key,actual] of [
    ['snapshotSha256',snap.hash],['healthSha256',health.hash],
    ['capitalPreviewSha256',report.hash]
  ])if(typeof receipt[key]!=='string'||!HASH.test(receipt[key])||receipt[key]!==actual)invalid();
  const s=snap.value,h=health.value,p=report.value;
  if(s?.schemaId!=='ARK_ACCOUNT_READONLY_SNAPSHOT_V2'||
     s?.captureMethod!=='ISOLATED_BULK_CANDIDATE_NOT_PRODUCTION'||
     s?.mode!=='READ_ONLY'||s?.source!=='MARKETSPEED_II_RSS'||
     h?.schemaId!=='ARK_MSII_RSS_SOURCE_HEALTH_V1'||
     h?.observationBasis!=='FINAL_STATUS_RE_READ_NOT_MARKET_SOURCE_TIMESTAMP'||
     h?.actualFeedTimestampCertified!==false||
     receipt.captureCompletedAt!==s.captureCompletedAt||
     h.healthCapturedAt!==s.captureCompletedAt||
     p?.schemaId!=='ARK_NO11_DESKTOP_CASH_PREVIEW_V1'||
     p?.status!=='READ_ONLY_CAPITAL_PREVIEW'||
     p?.productionReady!==false||p?.orderTransmission!==false||
     p?.personalStockDoubleDeducted!==false)invalid();
  // Full original 30-second RSS freshness, cash, pending-order and ownership checks.
  const ownership=read(path.join(root,'ownership-baseline.json')).value;
  const current=check({snapshot:s,health:h,ownership,now});
  if(current.status!=='READ_ONLY_CAPITAL_PREVIEW'||current.productionReady!==false||
     current.orderTransmission!==false||
     JSON.stringify(current)!==JSON.stringify(p))invalid();
  return Object.freeze({status:'V3_PUBLISHED_SOURCE_RECEIPT_VALID_READ_ONLY',
    productionReady:false,orderTransmission:false,actualBrokerDeliveryTimestampCertified:false});
}
const isCli=process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url));
if(isCli){
  try{
    if(process.argv.length!==2||!process.env.LOCALAPPDATA)invalid();
    const root=path.join(process.env.LOCALAPPDATA,'ArkTerminal','No11');
    const result=verifyV3PublishedReceipt({privateRoot:root});
    console.log('NO11_V3_PUBLISHED_SOURCE_RECEIPT='+result.status);
    console.log('NO11_PRODUCTION_READY=False');
    console.log('ORDER_TRANSMISSION=False');
  }catch{
    // Never emit private file paths, money, symbols or arbitrary exception text.
    console.log('NO11_V3_PUBLISHED_SOURCE_RECEIPT=BLOCKED');
    console.log('NO11_PRODUCTION_READY=False');
    console.log('ORDER_TRANSMISSION=False');
    process.exitCode=2;
  }
}
