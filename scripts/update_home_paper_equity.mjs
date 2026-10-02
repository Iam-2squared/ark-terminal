import fs from 'node:fs';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const scorecardPath=arg('--scorecard');
const evaluationPath=arg('--evaluation');
const inputPath=arg('--input','data/home/paper-equity.json');
const outputPath=arg('--output',inputPath);
const evidenceDate=arg('--date');
if(!scorecardPath||!evidenceDate){
  console.error('usage: node scripts/update_home_paper_equity.mjs --scorecard <json> --date YYYY-MM-DD [--evaluation <json>] [--input file] [--output file]');
  process.exit(2);
}

const data=JSON.parse(fs.readFileSync(inputPath,'utf8'));
const scorecardArtifact=JSON.parse(fs.readFileSync(scorecardPath,'utf8'));
const scorecard=scorecardArtifact?.scorecard;
const rows=scorecard?.rows;
if(!Array.isArray(rows)) throw new Error('P25 scorecard rows missing');

const variants=['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'];
const expectedSessionCount=Number(scorecard?.expectedSessionCount??1);
const round2=value=>Math.round(Number(value)*100)/100;

function getPerSessionReturns(variant){
  if(!evaluationPath) return null;
  const artifact=JSON.parse(fs.readFileSync(evaluationPath,'utf8'));
  const comparison=artifact?.evaluation?.result?.evidence?.comparison;
  const sessions=comparison?.results?.[variant]?.sessionEqualWeightPortfolio?.sessions;
  if(!Array.isArray(sessions)||!sessions.length) throw new Error(`Missing per-session portfolio returns for ${variant}`);
  return sessions.map(x=>({sessionDate:String(x.sessionDate),returnPct:Number(x.returnPct)}));
}

function rebuildSeriesFromSessions(variant,sessions){
  const current=Array.isArray(data.series?.[variant])?data.series[variant]:[];
  const start=current.find(x=>x?.source==='START')??{
    date:'START',
    equityJpy:Number(data.startingCapitalJpy),
    dailyReturnPct:0,
    resolvedEntries:0,
    source:'START',
  };
  let equity=Number(start.equityJpy??data.startingCapitalJpy);
  const rebuilt=[start];
  for(const session of sessions){
    if(!Number.isFinite(session.returnPct)) throw new Error(`Invalid per-session return for ${variant} ${session.sessionDate}`);
    equity=round2(equity*(1+session.returnPct/100));
    rebuilt.push({
      date:session.sessionDate,
      equityJpy:equity,
      dailyReturnPct:session.returnPct,
      source:`data/p25-evaluations/${evidenceDate}.json#sessionEqualWeightPortfolio`,
    });
  }
  data.series[variant]=rebuilt;
}

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
    const sessions=getPerSessionReturns(variant);
    if(sessions){
      if(sessions.length!==expectedSessionCount) throw new Error(`Expected ${expectedSessionCount} sessions for ${variant}, got ${sessions.length}`);
      rebuildSeriesFromSessions(variant,sessions);
    }
  }
  data.lastUpdatedAt=new Date().toISOString();
  fs.writeFileSync(outputPath,JSON.stringify(data,null,2)+'\n','utf8');
  console.log(JSON.stringify({status:evaluationPath?'HOME_PAPER_EQUITY_SERIES_REBUILT':'HOME_PAPER_EQUITY_CUMULATIVE_UPDATED',evidenceDate,expectedSessionCount,variants},null,2));
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
  const equityJpy=round2(Number(previous)*(1+dailyReturnPct/100));
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
