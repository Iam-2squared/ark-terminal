import fs from 'node:fs';
import path from 'node:path';
import {gzipSync} from 'node:zlib';
import {buildLaneCFixedPersistenceSummary} from '../predict/portfolio/phase57-p25-lane-c-fixed-persistence.js';

const arg=(name,fallback=null)=>{const index=process.argv.indexOf(name);return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;};
const inputPath=arg('--input');
const summaryPath=arg('--summary');
const archivePath=arg('--archive');
const sourceRunId=arg('--source-run-id');

if(!inputPath||!summaryPath||!archivePath||!sourceRunId){
  console.error('usage: node scripts/package_p25_lane_c_fixed_portfolio.mjs --input <json> --summary <json> --archive <json.gz> --source-run-id <id>');
  process.exit(2);
}

function writeAtomic(file,bytes){
  fs.mkdirSync(path.dirname(file),{recursive:true});
  const temporary=`${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary,bytes);
  fs.renameSync(temporary,file);
}

try{
  const rawArtifactBytes=fs.readFileSync(inputPath);
  const artifact=JSON.parse(rawArtifactBytes.toString('utf8'));
  const archiveBytes=gzipSync(rawArtifactBytes,{level:9,mtime:0});
  const summary=buildLaneCFixedPersistenceSummary({
    artifact,sourceRunId,rawArtifactBytes,archiveBytes,
    rawArtifactName:path.basename(inputPath),archiveName:path.basename(archivePath),
  });
  writeAtomic(archivePath,archiveBytes);
  writeAtomic(summaryPath,Buffer.from(`${JSON.stringify(summary,null,2)}\n`,'utf8'));
  console.log(JSON.stringify({
    status:summary.status,
    evidenceDate:summary.evidenceDate,
    sourceRunId:summary.sourceRunId,
    lineageManifestHeadSha256:summary.lineageManifestHeadSha256,
    resultCanonicalSha256:summary.resultCanonicalSha256,
    rawSha256:summary.fullArtifact.rawSha256,
    archiveSha256:summary.fullArtifact.archiveSha256,
    rawBytes:summary.fullArtifact.rawBytes,
    archiveBytes:summary.fullArtifact.archiveBytes,
    winnerSelectionAllowed:summary.methodology.winnerSelectionAllowed,
    safety:summary.safety,
  },null,2));
}catch(error){
  console.error(JSON.stringify({
    status:'BLOCKED_LANE_C_FIXED_PORTFOLIO_PACKAGING',
    error:String(error?.message??error),
  },null,2));
  process.exit(1);
}
