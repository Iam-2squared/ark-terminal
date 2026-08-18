import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildP252PinnedHistoricalSessions,PHASE57_P25_2K_POLICY,PHASE57_P25_2K_SAFETY} from '../predict/daytrade/phase57-p25-2k-pinned-history-bridge.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}

const snapshotPath=arg('--snapshot');
const outputPath=arg('--output','data/p25-pinned-history-pack.json');
if(!snapshotPath){
  console.error('usage: node scripts/build_p25_pinned_history_pack.mjs --snapshot <phase57-p24-9-oos-byte-snapshot.json> [--output <json>]');
  process.exit(2);
}

try{
  const bytes=fs.readFileSync(snapshotPath),snapshotSha256=sha(bytes);
  let snapshot;
  try{snapshot=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`snapshot JSON parse failed: ${error?.message??error}`);}
  const history=buildP252PinnedHistoricalSessions({snapshot,snapshotSha256});
  const payload={
    schemaVersion:1,
    phase:'57.p25.2k.pinned-history-bridge-cli',
    status:'P25_2_PINNED_HISTORY_PACK_READY',
    createdAt:new Date().toISOString(),
    canonicalSourceRunId:PHASE57_P25_2K_POLICY.canonicalSourceRunId,
    canonicalArtifactName:PHASE57_P25_2K_POLICY.canonicalArtifactName,
    canonicalSnapshotSha256:snapshotSha256,
    sessions:history.sessions,
    sessionCount:history.sessionCount,
    perSymbolSessionCount:history.perSymbolSessionCount,
    methodology:{...history.methodology,pinnedSnapshotIdentityVerified:true,dailyMarketSpeedRequired:false},
    safety:PHASE57_P25_2K_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({status:payload.status,output:outputPath,outputSha256:sha(fs.readFileSync(outputPath)),canonicalSnapshotSha256:snapshotSha256,sessionCount:payload.sessionCount,perSymbolSessionCount:payload.perSymbolSessionCount,dailyMarketSpeedRequired:false,safety:PHASE57_P25_2K_SAFETY},null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_2_PINNED_HISTORY_PACK',error:String(error?.message??error),expectedSnapshotSha256:PHASE57_P25_2K_POLICY.canonicalSnapshotSha256,safety:PHASE57_P25_2K_SAFETY},null,2));
  process.exit(1);
}
