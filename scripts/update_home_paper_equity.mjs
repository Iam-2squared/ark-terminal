import fs from 'node:fs';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const scorecardPath=arg('--scorecard');
const inputPath=arg('--input','data/home/paper-equity.json');
const outputPath=arg('--output',inputPath);
const evidenceDate=arg('--date');
if(!scorecardPath||!evidenceDate){
  console.error('usage: node scripts/update_home_paper_equity.mjs --scorecard <json> --date YYYY-MM-DD [--input file] [--output file]');
  process.exit(2);
}

const data=JSON.parse(fs.readFileSync(inputPath,'utf8'));
const scorecardArtifact=JSON.parse(fs.readFileSync(scorecardPath,'utf8'));
const scorecard=scorecardArtifact?.scorecard;
const rows=scorecard?.rows;
if(!Array.isArray(rows)) throw new Error('P25 scorecard rows missing');

const variants=['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'];
const expectedSessionCount=Number(scorecard?.expectedSessionCount??1);

if(expectedSessionCount>1){
  const cumulative={
    evidenceDate,
    expectedSessionCount,
    blockedSessionCount:Number(scorecard?.blockedSessionCount??0),
    source:`data/p25-scorecards/${evidenceDate}.json`,
    variants:{},
  };
  for(const variant of variants){
    const row=rows.find(x=>x?.variant===variant);
    if(!row) throw new Error(`Missing ${variant} in scorecard`);
    cumulative.variants[variant]={
      frozenEntries:Number(row.frozenEntries??0),
      resolvedEntries:Number(row.resolvedEntries??0),
      unresolvedFrozenEntries:Number(row.unresolvedFrozenEntries??0),
      entriesPerTradingSession:Number(row.entriesPerTradingSession??0),
      hitRate:row.hitRate??null,
      tradeWinRate:row.tradeWinRate??null,
      afterCostNetPct:Number(row.afterCostNetPct??0),
      profitFactor:row.profitFactor??null,
      maxDrawdownPct:Number(row.maxDrawdownPct??0),
      meanNetReturnPct:row.meanNetReturnPct??null,
      sessionEqualWeightAfterCostNetPct:Number(row.sessionEqualWeightAfterCostNetPct??0),
      conservativeEffectiveIndependentEntries:Number(row.conservativeEffectiveIndependentEntries??0),
    };
  }
  data.latestCumulative=cumulative;
  data.lastUpdatedAt=new Date().toISOString();
  fs.writeFileSync(outputPath,JSON.stringify(data,null,2)+'\n','utf8');
  console.log(JSON.stringify({status:'HOME_PAPER_EQUITY_CUMULATIVE_UPDATED',evidenceDate,expectedSessionCount,variants},null,2));
  process.exit(0);
}

for(const variant of variants){
  const row=rows.find(x=>x?.variant===variant);
  if(!row) throw new Error(`Missing ${variant} in scorecard`);
  if(!Number.isFinite(Number(row.sessionEqualWeightAfterCostNetPct))) throw new Error(`Missing sessionEqualWeightAfterCostNetPct for ${variant}`);
  const series=Array.isArray(data.series?.[variant])?data.series[variant]:[];
  if(series.some(point=>point.date===evidenceDate)) continue;
  const previous=series.at(-1)?.equityJpy??data.startingCapitalJpy;
  const dailyReturnPct=Number(row.sessionEqualWeightAfterCostNetPct);
  const equityJpy=Math.round((Number(previous)*(1+dailyReturnPct/100))*100)/100;
  series.push({
    date:evidenceDate,
    equityJpy,
    dailyReturnPct,
    resolvedEntries:Number(row.resolvedEntries??0),
    hitRate:row.hitRate??null,
    profitFactor:row.profitFactor??null,
    maxDrawdownPct:row.maxDrawdownPct??null,
    source:`data/p25-scorecards/${evidenceDate}.json`,
  });
  data.series[variant]=series;
}

data.lastUpdatedAt=new Date().toISOString();
fs.writeFileSync(outputPath,JSON.stringify(data,null,2)+'\n','utf8');
console.log(JSON.stringify({status:'HOME_PAPER_EQUITY_UPDATED',evidenceDate,variants},null,2));
