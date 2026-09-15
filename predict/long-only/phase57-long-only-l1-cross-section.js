import {createHash} from 'node:crypto';
import {buildL1ResearchRows,addCausalBreadthContext,assignCausalLiquidityBuckets} from './phase57-long-only-l1-labels-features.js';

const DEVELOPMENT_PARTITIONS=new Set(['DEVELOPMENT_A','DEVELOPMENT_B','DEVELOPMENT_C','DEVELOPMENT_D']);
const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');

export function buildL1CrossSectionDataset({partition,dailyRows=[],bars5m=[],terminalAuctions=[],sectorBySymbol={}}={}){
  if(!DEVELOPMENT_PARTITIONS.has(partition))throw new Error('L1 construction is Development-only until an explicit sealed-partition release');
  const barsBySessionSymbol=new Map(),auctionsBySessionSymbol=new Map();
  for(const bar of bars5m){const k=`${bar.sessionDate}|${bar.symbol}`;if(!barsBySessionSymbol.has(k))barsBySessionSymbol.set(k,[]);barsBySessionSymbol.get(k).push(bar);}
  for(const row of terminalAuctions){const k=`${row.sessionDate}|${row.symbol}`;if(!auctionsBySessionSymbol.has(k))auctionsBySessionSymbol.set(k,[]);auctionsBySessionSymbol.get(k).push(row);}
  const rawFeatures=[],labels=[],exclusions={CORPORATE_ACTION_UNRESOLVED:0,NO_INTRADAY_BARS:0,NO_EVALUATOR_LABEL:0};
  for(const daily of dailyRows){
    if(daily.corporateActionFlag){exclusions.CORPORATE_ACTION_UNRESOLVED++;continue;}
    const k=`${daily.sessionDate}|${daily.symbol}`,symbolBars=barsBySessionSymbol.get(k)??[];
    if(!symbolBars.length){exclusions.NO_INTRADAY_BARS++;continue;}
    const built=buildL1ResearchRows({sessionDate:daily.sessionDate,symbol:daily.symbol,segment:daily.segment,bars5m:symbolBars,terminalAuctions:auctionsBySessionSymbol.get(k)??[],previousAdjustedClose:Number(daily.adjustedPreviousClose),officialFinalAdjustedClose:Number(daily.adjustedClose)});
    rawFeatures.push(...built.features);labels.push(...built.evaluatorOnlyLabels);
  }
  const features=assignCausalLiquidityBuckets(addCausalBreadthContext(rawFeatures,{sectorBySymbol}));
  const featureKeys=new Set(features.map(key)),matchedLabels=labels.filter(label=>featureKeys.has(key(label)));
  exclusions.NO_EVALUATOR_LABEL=features.length-matchedLabels.length;
  const labelKeys=new Set(matchedLabels.map(key)),matchedFeatures=features.filter(feature=>labelKeys.has(key(feature)));
  if(matchedFeatures.some(row=>Object.keys(row).some(k=>/winner|future|remaining|lateDetection/i.test(k))))throw new Error('evaluator outcome leaked into L1 feature rows');
  return Object.freeze({schemaVersion:1,partition,featureRows:Object.freeze(matchedFeatures),evaluatorOnlyLabels:Object.freeze(matchedLabels),audit:Object.freeze({dailyRows:dailyRows.length,bars5m:bars5m.length,featureRows:matchedFeatures.length,labelRows:matchedLabels.length,exclusions:Object.freeze(exclusions),labelFieldsReachDecisionPipeline:false}),featureSha256:sha(matchedFeatures),labelSha256:sha(matchedLabels)});
}

export default {buildL1CrossSectionDataset};
