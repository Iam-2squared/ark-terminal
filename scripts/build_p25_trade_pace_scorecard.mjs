import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {buildP253TradePaceScorecard,PHASE57_P25_3E_SAFETY} from '../predict/daytrade/phase57-p25-3e-trade-pace-scorecard.js';

function arg(name,fallback=null){const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;}
function sha(bytes){return crypto.createHash('sha256').update(bytes).digest('hex');}

const evaluationPath=arg('--evaluation');
const outputPath=arg('--output','data/p25-trade-pace-scorecard.json');
if(!evaluationPath){
  console.error('usage: node scripts/build_p25_trade_pace_scorecard.mjs --evaluation <p25.3d-json> [--output <json>]');
  process.exit(2);
}

try{
  const bytes=fs.readFileSync(evaluationPath);
  let evaluationArtifact;
  try{evaluationArtifact=JSON.parse(bytes.toString('utf8'));}catch(error){throw new Error(`evaluation JSON parse failed: ${error?.message??error}`);}
  const scorecard=buildP253TradePaceScorecard({evaluationArtifact});
  const payload={
    schemaVersion:1,
    phase:'57.p25.3e.trade-pace-scorecard-cli',
    status:'P25_3_TRADE_PACE_SCORECARD_ARTIFACT_WRITTEN',
    createdAt:new Date().toISOString(),
    inputs:{
      evaluation:path.normalize(evaluationPath),
      evaluationSha256:sha(bytes),
      lineageManifestHeadSha256:scorecard.lineageManifestHeadSha256,
    },
    scorecard,
    methodology:{
      descriptiveOnly:true,
      allFiveVariantsRetained:true,
      currentOuterOosDoesNotSelectDynamicN:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      performanceConclusionAllowed:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    },
    safety:PHASE57_P25_3E_SAFETY,
  };
  fs.mkdirSync(path.dirname(outputPath),{recursive:true});
  const tmp=`${outputPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp,JSON.stringify(payload,null,2)+'\n','utf8');
  fs.renameSync(tmp,outputPath);
  console.log(JSON.stringify({
    status:payload.status,
    output:outputPath,
    outputSha256:sha(fs.readFileSync(outputPath)),
    lineageManifestHeadSha256:scorecard.lineageManifestHeadSha256,
    expectedSessionCount:scorecard.expectedSessionCount,
    readyPacketCount:scorecard.readyPacketCount,
    variants:scorecard.rows.map(row=>({
      variant:row.variant,
      frozenEntries:row.frozenEntries,
      entriesPerTradingSession:row.entriesPerTradingSession,
      observedDaysTo400:row.observedDaysTo400,
      paceEstimatedDaysTo400:row.paceEstimatedDaysTo400,
    })),
    dynamicNSelectedFromCurrentOuterOos:false,
    dailyMarketSpeedRequired:false,
    safety:PHASE57_P25_3E_SAFETY,
  },null,2));
}catch(error){
  console.error(JSON.stringify({status:'BLOCKED_P25_3_TRADE_PACE_SCORECARD',error:String(error?.message??error),safety:PHASE57_P25_3E_SAFETY},null,2));
  process.exit(1);
}
