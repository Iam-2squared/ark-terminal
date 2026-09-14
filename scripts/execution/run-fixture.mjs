import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {spawnSync,execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {ExecutionRuntime} from './runtime.mjs';
import {FREEZE,VERSIONS,SAFETY,fingerprint} from './contract.mjs';
import {digest,verifyFreeze} from '../lib/phase57-offline-parity.mjs';
const root=fileURLToPath(new URL('../../',import.meta.url));
const destination=path.resolve(process.argv[2]??'execution-fixture-output');
verifyFreeze(root);fs.mkdirSync(destination,{recursive:false});
const fixtureBytes=fs.readFileSync(new URL('./fixtures/lifecycle.json',import.meta.url));
const fixture=JSON.parse(fixtureBytes);assert.equal(fixture.sourceClass,'SYNTHETIC_FIXTURE');
const head=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
const tests=spawnSync(process.execPath,['--test','scripts/execution/tests/execution.test.mjs','scripts/execution/tests/msii-rss-contract.test.mjs'],{cwd:root,encoding:'utf8',env:{...process.env,ARK_EXECUTION_EVIDENCE_DIR:path.join(destination,'evidence')}});
fs.writeFileSync(path.join(destination,'tests.log'),tests.stdout+tests.stderr,{flag:'wx'});assert.equal(tests.status,0,'EXECUTION_TEST_GATE_FAILED');
const config={mode:'SYNTHETIC_FIXTURE',freezeSha256:FREEZE,repoHead:head,fixtureHash:digest(fixtureBytes),sessionDate:fixture.sessionDate,startedAt:fixture.at,symbols:fixture.symbols,initialCashJpy:fixture.initialCashJpy,limits:fixture.limits};
fs.writeFileSync(path.join(destination,'run-config.json'),JSON.stringify(config,null,2)+'\n',{flag:'wx'});
let runtime=new ExecutionRuntime(destination,config),sequence=0;
const send=(kind,data={})=>runtime.process({eventId:`demo-${++sequence}`,at:fixture.at,kind,...data});
function context(){const s=runtime.snapshot();return send('CONTEXT',{evidenceHash:config.fixtureHash,context:{msiiConnected:true,excelConnected:true,networkConnected:true,engineReady:true,finalizationPassed:true,adapterAvailable:true,feedAt:fixture.at,accountAt:fixture.at,account:{...s.portfolio,openOrders:[]}}});}
try{
  context();send('MODE',{operator:'SYNTHETIC_FIXTURE',mode:'ARM_REQUESTED'});send('MODE',{operator:'SYNTHETIC_FIXTURE',mode:'ARMED'});
  const d={...fixture.entry,decisionId:'fixture-enter',action:'ENTER',sessionDate:fixture.sessionDate,decisionAt:fixture.at,createdAt:fixture.at,orderType:'LIMIT',limitPrice:100,timeInForce:'DAY',...VERSIONS,sourceEvidenceHash:config.fixtureHash,decisionEvidenceHash:fingerprint(fixture.entry)};
  const id=send('CREATE',{decision:d}).orderIntentId;assert.equal(send('VALIDATE',{orderIntentId:id}).status,'READY');send('REQUEST',{orderIntentId:id});send('ADAPTER_RESPONSE',{orderIntentId:id,status:'SUBMITTED'});send('ACCEPT',{orderIntentId:id});
  for(const [i,fill]of fixture.fills.entries())send('FILL',{orderIntentId:id,fillId:`fixture-fill-${i}`,...fill});
  const before=runtime.snapshot();runtime.close();runtime=new ExecutionRuntime(destination,config);assert.deepEqual(runtime.snapshot().positions,before.positions);assert.equal(runtime.snapshot().cashJpy,before.cashJpy);
  send('EMERGENCY_STOP');const status=runtime.status();assert.equal(status.transmission,'LOCKED');assert.equal(runtime.submitOrder(d).blocked,true);
  fs.writeFileSync(path.join(destination,'status.json'),JSON.stringify(status,null,2)+'\n',{flag:'wx'});
  fs.writeFileSync(path.join(destination,'snapshot.json'),JSON.stringify(runtime.snapshot(),null,2)+'\n',{flag:'wx'});
}finally{runtime.close();}
const files={};for(const name of ['execution.jsonl','run-config.json','status.json','snapshot.json','tests.log'])files[name]=digest(fs.readFileSync(path.join(destination,name)));
for(const name of fs.readdirSync(path.join(destination,'evidence')))files['evidence/'+name]=digest(fs.readFileSync(path.join(destination,'evidence',name)));
const report={schemaId:'ARK_EXECUTION_FIXTURE_RUN_V1',status:'TRANSMISSION_DISABLED_FIXTURE_PASS',repoHead:head,freezeSha256:FREEZE,fixtureSha256:config.fixtureHash,files,safety:SAFETY,realAccountConnected:false,realOrderTransmitted:false,barFinalizationVerified:false,realtimeShadowVerified:false};
fs.writeFileSync(path.join(destination,'manifest.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({status:report.status,output:destination,transmission:'LOCKED'}));
