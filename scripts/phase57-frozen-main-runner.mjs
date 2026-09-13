#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {digest,FREEZE,hash} from './lib/phase57-offline-parity.mjs';
import {OfflineSession,exportSession} from './lib/phase57-offline-session.mjs';
import {createFrozenMainEngine,FROZEN_MAIN_POLICY} from './lib/phase57-frozen-main-engine.mjs';

function args(argv){const out={};for(let i=0;i<argv.length;i+=2){const key=argv[i],value=argv[i+1];if(!key?.startsWith('--')||value===undefined)throw Error('ARGS_REQUIRE_KEY_VALUE_PAIRS');out[key.slice(2)]=value;}for(const key of ['input','journal-dir','export-dir'])if(!out[key])throw Error(`MISSING_ARG:${key}`);return out;}
function main(){
  const options=args(process.argv.slice(2)),root=process.cwd(),bytes=fs.readFileSync(options.input),packet=JSON.parse(bytes);
  if(!Array.isArray(packet.points)||!packet.points.length)throw Error('POINTS_REQUIRED');
  if(!Array.isArray(packet.analogPool)||!packet.analogPool.length)throw Error('ANALOG_POOL_REQUIRED');
  const sessionDate=packet.points[0].sessionDate,sourceClass=packet.points[0].sourceClass;
  for(const point of packet.points){if(point.sessionDate!==sessionDate||point.sourceClass!==sourceClass)throw Error('MIXED_SESSION_OR_SOURCE_PACKET');}
  const repoHead=String(packet.repoHead??execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim());
  const workbookSha256=packet.workbookSha256??digest(bytes);if(!/^[a-f0-9]{64}$/.test(workbookSha256))throw Error('WORKBOOK_SHA256_REQUIRED');
  const identity={sessionDate,sourceClass,freezeSha256:FREEZE,repoHead,workbookSha256,sourceIdentity:hash({packetSha256:digest(bytes),schemaId:packet.schemaId??null,analogPoolSha256:hash(packet.analogPool),memberSetSha256:packet.points[0].memberSetSha256})};
  const makeReducer=()=>createFrozenMainEngine({root,analogPool:packet.analogPool}).step;
  const session=new OfflineSession(options['journal-dir'],identity,makeReducer);
  try{
    for(const point of packet.points)session.commit(String(point.captureId??point.timestamp),point);
    const reducer=createFrozenMainEngine({root,analogPool:packet.analogPool});
    for(const point of packet.points)reducer.step(point);
    const snapshot=reducer.snapshot();
    const report={schemaId:'ARK_PHASE57_FROZEN_MAIN_REPORT_V1',status:snapshot.closed?'COMPLETE_SHADOW_SESSION':'PARTIAL_SHADOW_SESSION',sessionDate,pointCount:packet.points.length,openPositionCount:snapshot.openPositionCount,closedTradeCount:snapshot.ledger.closedTrades.length,finalEquityJpy:snapshot.ledger.curve.at(-1)?.equityJpy??null,policy:FROZEN_MAIN_POLICY,performanceClaimAllowed:false,realOrderTransmissionImplemented:false,realOrderTransmissionEnabled:false};
    session.seal(report);session.close();const manifest=exportSession(path.join(options['journal-dir'],'session.jsonl'),options['export-dir']);
    process.stdout.write(JSON.stringify({status:report.status,report,manifest},null,2)+'\n');
  }catch(error){session.close();throw error;}
}
if(process.argv[1]&&fileURLToPath(import.meta.url)===path.resolve(process.argv[1]))main();
