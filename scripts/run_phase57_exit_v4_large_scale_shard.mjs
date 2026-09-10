import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildP25DataDrivenExitAnalogPool} from '../predict/daytrade/phase57-p25-data-driven-exit.js';
import {P25_EXIT_V4_POLICY_SHA256} from '../predict/daytrade/phase57-p25-exit-v4-structural-risk.js';
import {buildExactExitV4AnalogIndex,simulateP25ExitV4ExactIndexed} from '../predict/daytrade/phase57-exit-v4-exact-indexed-replay.js';
import {PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,PHASE57_EXIT_V4_LARGE_SCALE_SAFETY,assertExitV4PairedIdentity,buildExitV4StressProbe,simulateFixedProbeExit,summarizeExitV4LargeScale} from '../predict/daytrade/phase57-exit-v4-large-scale.js';

const arg=(name,fallback)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const sourcePath=arg('--source');
const historyPath=arg('--history-pack');
const output=arg('--output','tmp/phase57-exit-v4-large-scale-evaluation-shard.json');
if(!sourcePath||!historyPath)throw new Error('--source and --history-pack are required');
const source=JSON.parse(fs.readFileSync(sourcePath,'utf8')),history=JSON.parse(fs.readFileSync(historyPath,'utf8'));
if(!Array.isArray(source.sessions)||!Array.isArray(history.sessions))throw new Error('source/history sessions missing');
const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:history.sessions});
const index=buildExactExitV4AnalogIndex(analogPool),records=[],blocked=[];
const sha=value=>crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
for(const session of source.sessions){
  const probe=buildExitV4StressProbe({session});
  if(!probe.ready){blocked.push(probe);continue;}
  const cost=PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.roundTripCostPct,marketDataSha256=sha({contextBars:probe.row.contextBars,futureBars:probe.row.futureBars});
  const common={probeId:probe.row.probeId,symbol:probe.row.symbol,sessionDate:probe.row.sessionDate,entryTimestamp:probe.row.entryTimestamp,entryPrice:probe.row.entryPrice,signalDirection:probe.row.signalDirection,marketDataSha256,roundTripCostPct:cost,allocationUnits:1,market:session.market??null,sector:session.sector??null};
  const v4=simulateP25ExitV4ExactIndexed({row:probe.row,index,roundTripCostPct:cost}),fixed=simulateFixedProbeExit({row:probe.row,roundTripCostPct:cost});
  const v4Record={...common,variant:'V4',...v4,managementDecisions:undefined},fixedRecord={...common,variant:'FIXED_24',...fixed};
  assertExitV4PairedIdentity({probe:common,v4:v4Record,fixed:fixedRecord});records.push(v4Record,fixedRecord);
}
records.sort((a,b)=>a.probeId.localeCompare(b.probeId)||a.variant.localeCompare(b.variant));
const evidence={schemaVersion:1,phase:'57.exit-v4.large-scale.evaluation-shard',status:'V4_LARGE_SCALE_EVALUATION_SHARD_READY',sourcePayloadSha256:source.payloadSha256??null,canonicalSnapshotSha256:history.canonicalSnapshotSha256??null,policySha256:P25_EXIT_V4_POLICY_SHA256,analogRowCount:analogPool.length,indexedCandidateRowCount:index.buckets.LONG.WINNER_PROTECTION.length+index.buckets.LONG.LOSER_RESCUE.length+index.buckets.SHORT.WINNER_PROTECTION.length+index.buckets.SHORT.LOSER_RESCUE.length,probeCount:records.length/2,blockedProbeCount:blocked.length,blocked,records,summary:summarizeExitV4LargeScale(records),classification:{historicalReconstruction:true,stressDiagnostic:true,formalOos:false,prospective:false,promotionEligible:false},methodology:PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,safety:PHASE57_EXIT_V4_LARGE_SCALE_SAFETY};
evidence.evidenceSha256=sha(evidence);
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(evidence,null,2)}\n`);
console.log(JSON.stringify({status:evidence.status,output,probeCount:evidence.probeCount,blockedProbeCount:evidence.blockedProbeCount,analogRowCount:evidence.analogRowCount,summary:evidence.summary,evidenceSha256:evidence.evidenceSha256},null,2));
