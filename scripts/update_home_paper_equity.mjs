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
const rows=scorecardArtifact?.scorecard?.rows;
if(!Array.isArray(rows)) throw new Error('P25 scorecard rows missing');

const variants=['DYNAMIC_30','DYNAMIC_40','DYNAMIC_50'];
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
