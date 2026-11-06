// Read-only private RSS account -> Capital v5 funding preview. No Excel/order access.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {inspectNo11CapitalFunding} from '../runtime/capital_funding_bridge.mjs';
function read(filename){
  if(!path.isAbsolute(filename))throw Error('ABSOLUTE_PATH_REQUIRED');
  const info=fs.lstatSync(filename);
  if(!info.isFile()||info.isSymbolicLink())throw Error('UNSAFE_PRIVATE_FILE');
  return JSON.parse(fs.readFileSync(filename,'utf8'));
}
export function check({snapshot,health,ownership,now=new Date()}={}){
  const verdict=inspectNo11CapitalFunding({snapshot,health,ownership,now});
  return {schemaId:'ARK_NO11_DESKTOP_CASH_PREVIEW_V1',
    status:verdict.status,blockers:verdict.blockers,
    arkCapitalInputs:verdict.arkCapitalInputs,
    arkManagedPositionCount:verdict.arkManagedPositionCount,
    personalStockDoubleDeducted:false,
    liveFeedCertified:false,liveDecisionCertified:false,
    liveOrderReconciliationCertified:false,productionReady:false,
    excelModified:false,orderTransmission:false};
}
const isCLI=process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url));
if(isCLI){
  try{
    const [snapshotPath,healthPath,ownershipPath,reportPath]=process.argv.slice(2);
    if(!snapshotPath||!healthPath||!ownershipPath||!reportPath||
      [snapshotPath,healthPath,ownershipPath,reportPath].some(p=>!path.isAbsolute(p)))
      throw Error('FOUR_ABSOLUTE_PATHS_REQUIRED');
    const root=path.dirname(path.resolve(snapshotPath));
    if([healthPath,ownershipPath,reportPath].some(p=>path.dirname(path.resolve(p))!==root))
      throw Error('PRIVATE_DIRECTORY_REQUIRED');
    if([snapshotPath,healthPath,ownershipPath].some(p=>path.resolve(p)===path.resolve(reportPath)))
      throw Error('OUTPUT_COLLIDES_WITH_SOURCE');
    const verdict=check({snapshot:read(snapshotPath),health:read(healthPath),ownership:read(ownershipPath)});
    const tmp=reportPath+'.tmp-'+process.pid;
    fs.writeFileSync(tmp,JSON.stringify(verdict,null,2)+'\n',{flag:'wx',mode:0o600});
    try{fs.renameSync(tmp,reportPath);}finally{if(fs.existsSync(tmp))fs.unlinkSync(tmp);}
    console.log('NO11_DESKTOP_CAPITAL='+verdict.status);
    console.log('CAPITAL_PREVIEW_AVAILABLE='+Boolean(verdict.arkCapitalInputs));
    console.log('ACTUAL_FEED_TIMESTAMP_CERTIFIED=FALSE');
    console.log('PRODUCTION_READY=FALSE');
    console.log('TRANSMITTED=FALSE');
    if(verdict.status!=='READ_ONLY_CAPITAL_PREVIEW')process.exitCode=2;
  }catch(e){console.error('NO11_DESKTOP_CAPITAL_BLOCKED:'+e.message);process.exitCode=2;}
}
