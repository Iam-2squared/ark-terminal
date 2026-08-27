import fs from 'node:fs';
import path from 'node:path';
import {compareP25ExitV3LaneCAllocations} from '../predict/portfolio/phase57-p25-lane-c-exit-v3-connector.js';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const write=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n','utf8');};

export function loadSessionPackets(capturesDir){
  const files=fs.readdirSync(capturesDir).filter(name=>name.endsWith('.json')).sort();
  if(!files.length)throw new Error('Lane C EXIT v3 diagnostic requires capture JSON files');
  const packets=[];
  for(const file of files){
    const capture=read(path.join(capturesDir,file));
    for(const session of capture?.sessions??[]){
      packets.push({
        sessionDate:String(session?.sessionDate??session?.universeRecord?.sessionDate??''),
        universeRecord:session?.universeRecord??null,
        sessionBarsBySymbol:session?.sessionBarsBySymbol??{},
      });
    }
  }
  const dedup=new Map();
  for(const packet of packets){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(packet.sessionDate))throw new Error('invalid capture session date');
    if(dedup.has(packet.sessionDate))throw new Error(`duplicate capture session ${packet.sessionDate}`);
    dedup.set(packet.sessionDate,packet);
  }
  return [...dedup.values()].sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
}

function causalRow(profileId,result){
  return {
    managementMode:'EXIT_V3',
    universeVariant:'DYNAMIC_50',
    profileId,
    candidateEntryCount:result.trade.candidates,
    acceptedTradeCount:result.trade.accepted,
    rejectedTradeCount:result.trade.rejected,
    finalEquityJpy:result.return.finalEquityJpy,
    totalReturnPct:result.return.totalReturnPct,
    profitFactor:result.trade.profitFactor,
    winRate:result.trade.winRate,
    meanPnlPct:result.trade.meanPnlPct??null,
    maxDrawdownPct:result.risk.maxDrawdownPct,
    sharpe:result.risk.sharpe,
    averageCapitalUtilization:result.capitalEfficiency.averageCapitalUtilization,
    averageCashRatio:result.capitalEfficiency.averageCashRatio,
    capitalRecyclingCount:result.capitalEfficiency.capitalRecyclingCount,
    turnover:result.capitalEfficiency.turnover,
    maximumConcurrentPositions:result.trade.maximumConcurrentPositions??result.input?.profile?.maxPositions??null,
    maximumSymbolShare:result.concentration.maximumSymbolShare,
    maximumSectorShare:result.concentration.maximumSectorShare,
  };
}

function fixedRows(summary){
  if(!summary)return [];
  return (summary.matrixRows??[]).filter(row=>row.universeVariant==='DYNAMIC_50'&&['MAX_10','MAX_4','MAX_3','MAX_2'].includes(row.profileId));
}

export function buildDiagnostic({replay,sessionPackets,fixedSummary=null}){
  const output=compareP25ExitV3LaneCAllocations({replay,sessionPackets});
  if(output.connectorAudit.pairedCount!==27)throw new Error(`expected legacy27 pairedCount=27, got ${output.connectorAudit.pairedCount}`);
  if(output.interpretation.winnerSelectionAllowed!==false||output.interpretation.formalOosEvidence!==false||output.interpretation.promotionEligible!==false){
    throw new Error('Lane C EXIT v3 diagnostic interpretation guard violation');
  }
  const ids=['MAX_10','MAX_4','MAX_3','MAX_2'];
  const v3Rows=ids.map(id=>causalRow(id,output.comparison.results[id]));
  const baseline=fixedRows(fixedSummary);
  if(baseline.length&&baseline.some(row=>Number(row.candidateEntryCount)!==27))throw new Error('Fixed DYNAMIC_50 baseline candidate count mismatch');
  return {
    schemaVersion:1,
    phase:'57.p25.lane-c.exit-v3-diagnostic-measurement',
    status:'LANE_C_EXIT_V3_DIAGNOSTIC_MEASUREMENT_READY',
    evidenceClass:'LEGACY27_DIAGNOSTIC_ONLY',
    source:{
      pairedCount:output.connectorAudit.pairedCount,
      candidateKeySha256:output.connectorAudit.candidateKeySha256,
      lineageManifestHeadSha256:output.connectorAudit.sourceLineageManifestHeadSha256,
      exitV3PolicySha256:output.connectorAudit.sourcePolicySha256,
    },
    fixedBaselineRows:baseline,
    exitV3Rows:v3Rows,
    interpretation:{
      winnerSelectionAllowed:false,
      formalOos:false,
      promotionEligible:false,
      resultBasedRetuning:false,
      freshHoldoutConsumed:false,
      note:'Pipeline/diagnostic measurement only. Do not select Max10/4/3/2 from legacy27.',
    },
    full:output,
    safety:output.safety,
  };
}

const replayPath=arg('--replay');
const capturesDir=arg('--captures-dir');
const outputPath=arg('--output','tmp/p25-lane-c-exit-v3-diagnostic.json');
const fixedSummaryPath=arg('--fixed-summary');
if(replayPath&&capturesDir){
  const result=buildDiagnostic({
    replay:read(replayPath),
    sessionPackets:loadSessionPackets(capturesDir),
    fixedSummary:fixedSummaryPath?read(fixedSummaryPath):null,
  });
  write(outputPath,result);
  console.log(JSON.stringify({status:result.status,source:result.source,fixedBaselineRows:result.fixedBaselineRows,exitV3Rows:result.exitV3Rows,interpretation:result.interpretation,safety:result.safety},null,2));
}
