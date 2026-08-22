export const PHASE57_P25_3P_SAFETY=Object.freeze({
  phase:'57.p25.3p.checkpoint-plan',
  mode:'READ_ONLY_DETERMINISTIC_CHECKPOINT_PLAN',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

const EXPECTED=Object.freeze({FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50});
const normalizeSymbol=value=>String(value??'').trim().toUpperCase();

function validateUniverse(record){
  if(record?.ready!==true||!record?.variants)throw new Error('P25.3P requires ready frozen universe');
  const normalized={};
  for(const [variant,count] of Object.entries(EXPECTED)){
    const values=record.variants?.[variant];
    if(!Array.isArray(values)||values.length!==count)throw new Error(`P25.3P ${variant} must contain ${count} symbols`);
    const symbols=values.map(normalizeSymbol);
    if(symbols.some(x=>!x)||new Set(symbols).size!==count)throw new Error(`P25.3P ${variant} invalid membership`);
    normalized[variant]=symbols;
  }
  if(!normalized.DYNAMIC_30.every((x,i)=>normalized.DYNAMIC_40[i]===x)||!normalized.DYNAMIC_40.every((x,i)=>normalized.DYNAMIC_50[i]===x))throw new Error('P25.3P dynamic memberships must remain nested');
  return [...new Set(Object.values(normalized).flat())].sort();
}

export function buildP253PCheckpointPlan({universeRecord,batchSize=5}={}){
  const size=Number(batchSize);
  if(!Number.isInteger(size)||size<1)throw new TypeError('P25.3P batchSize must be a positive integer');
  const symbols=validateUniverse(universeRecord);
  const batches=[];
  for(let start=0;start<symbols.length;start+=size){
    const shardSymbols=symbols.slice(start,start+size);
    batches.push(Object.freeze({
      batchIndex:batches.length,
      batchId:`batch-${String(batches.length).padStart(2,'0')}`,
      shardSymbols:Object.freeze(shardSymbols),
      firstSymbol:shardSymbols[0],
      lastSymbol:shardSymbols.at(-1),
    }));
  }
  return Object.freeze({
    phase:'57.p25.3p.checkpoint-plan',
    status:'P25_3P_CHECKPOINT_PLAN_READY',
    batchSize:size,
    targetSymbolCount:symbols.length,
    targetSymbols:Object.freeze(symbols),
    batchCount:batches.length,
    batches:Object.freeze(batches),
    methodology:Object.freeze({
      deterministicSortedUnion:true,
      fullUnionCoverageRequired:true,
      overlappingShardMembershipAllowed:false,
      currentOuterOosUsedForPartitioning:false,
      entryThresholdRelaxed:false,
      modelChanged:false,
      universeChanged:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_3P_SAFETY,
  });
}

export function validateP253PCheckpointCoverage({plan,checkpoints=[]}={}){
  if(plan?.phase!=='57.p25.3p.checkpoint-plan'||plan?.status!=='P25_3P_CHECKPOINT_PLAN_READY')throw new Error('P25.3P valid plan required');
  if(!Array.isArray(checkpoints))throw new TypeError('P25.3P checkpoints must be an array');
  const byBatch=new Map();
  for(const checkpoint of checkpoints){
    const batchId=String(checkpoint?.batchId??'');
    if(!batchId)throw new Error('P25.3P checkpoint batchId missing');
    if(byBatch.has(batchId))throw new Error(`P25.3P duplicate checkpoint ${batchId}`);
    byBatch.set(batchId,checkpoint);
  }
  const missing=plan.batches.filter(batch=>!byBatch.has(batch.batchId)).map(batch=>batch.batchId);
  if(missing.length)throw new Error(`P25.3P missing checkpoints: ${missing.join(',')}`);
  const seen=new Set();
  for(const batch of plan.batches){
    const checkpoint=byBatch.get(batch.batchId);
    if(checkpoint?.phase!=='57.p25.3p.checkpoint'||checkpoint?.status!=='P25_3P_CHECKPOINT_COMPLETE')throw new Error(`P25.3P invalid checkpoint ${batch.batchId}`);
    const got=[...(checkpoint.shardSymbols??[])].map(normalizeSymbol);
    if(JSON.stringify(got)!==JSON.stringify(batch.shardSymbols))throw new Error(`P25.3P checkpoint membership mismatch ${batch.batchId}`);
    for(const symbol of got){if(seen.has(symbol))throw new Error(`P25.3P duplicate covered symbol ${symbol}`);seen.add(symbol);}
  }
  const missingSymbols=plan.targetSymbols.filter(symbol=>!seen.has(symbol));
  const extraSymbols=[...seen].filter(symbol=>!plan.targetSymbols.includes(symbol));
  if(missingSymbols.length||extraSymbols.length)throw new Error('P25.3P checkpoint symbol coverage mismatch');
  return Object.freeze({complete:true,batchCount:plan.batchCount,targetSymbolCount:plan.targetSymbolCount});
}

export default {buildP253PCheckpointPlan,validateP253PCheckpointCoverage,PHASE57_P25_3P_SAFETY};
