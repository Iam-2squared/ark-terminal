import { replayIntradayFrames } from './phase57-intraday-capture-replay.js';

export const PHASE57_DATASET_SAFETY=Object.freeze({mode:'INTRADAY_LOCAL_DATASET_READ_ONLY',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,humanApprovalRequired:true});

function partitionKey(frame){return `${frame.sessionDate}/${frame.symbol}`;}
function stableFrame(frame){return {version:frame.version,symbol:frame.symbol,sessionDate:frame.sessionDate,capturedAt:frame.capturedAt,bar:frame.bar,market:frame.market,book:frame.book,ticks:frame.ticks};}

export function buildIntradayDataset(frames=[]){
  const ordered=replayIntradayFrames(frames);
  const partitions=new Map();
  for(const frame of ordered){
    const key=partitionKey(frame);
    if(!partitions.has(key)) partitions.set(key,[]);
    partitions.get(key).push(stableFrame(frame));
  }
  const partitionList=[...partitions.entries()].map(([key,rows])=>Object.freeze({key,rowCount:rows.length,start:rows[0]?.capturedAt??null,end:rows.at(-1)?.capturedAt??null,rows:Object.freeze(rows)}));
  return Object.freeze({phase:'57.p3',status:ordered.length?'INTRADAY_DATASET_READY':'NO_INTRADAY_DATA',schemaVersion:1,storageIntent:Object.freeze({hot:'memory/recent-session',warm:'local-parquet-or-duckdb',cold:'archive',backendBound:false}),partitioning:'sessionDate/symbol',appendOnly:true,deterministicReplay:true,rowCount:ordered.length,partitionCount:partitionList.length,partitions:Object.freeze(partitionList),sources:Object.freeze(['RssMarket','RssChart','RssChartPast','RssTickList','board/depth snapshot']),recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,safety:PHASE57_DATASET_SAFETY});
}

export function serializeDatasetJsonl(dataset){
  if(!dataset||!Array.isArray(dataset.partitions)) throw new Error('DATASET_REQUIRED');
  const lines=[];
  for(const partition of dataset.partitions){for(const row of partition.rows){lines.push(JSON.stringify({partition:partition.key,...row}));}}
  return lines.join('\n');
}

export function replayDataset(dataset,{symbol=null,sessionDate=null,from=null,to=null}={}){
  if(!dataset||!Array.isArray(dataset.partitions)) return Object.freeze([]);
  const rows=dataset.partitions.flatMap(p=>p.rows).filter(r=>(!symbol||r.symbol===String(symbol).toUpperCase())&&(!sessionDate||r.sessionDate===sessionDate));
  return replayIntradayFrames(rows,{symbol,from,to});
}

export default {buildIntradayDataset,serializeDatasetJsonl,replayDataset};
