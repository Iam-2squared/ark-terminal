import {createHash} from 'node:crypto';

export const PHASE57_LONG_ONLY_RESEARCH_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_CASH_EQUITY_RESEARCH_V1',
  branch:'research/phase57-long-only-cash-equity',
  objective:'JPX_LONG_MOMENTUM_REMAINING_UPSIDE',
  accountType:'CASH_EQUITY',
  longOnly:true,
  allowedSides:Object.freeze(['LONG']),
  cashBuyAllowed:true,
  marginBuyAllowed:false,
  shortSellAllowed:false,
  marginSellAllowed:false,
  shortEntryAllowed:false,
  shortPositionAllowed:false,
  leverageAllowed:false,
  fractionalSharesAllowed:false,
  defaultLotSize:100,
  availableCashPurchaseLimitRequired:true,
  entryCashLockRequired:true,
  exitCashReleaseRequired:true,
  releasedCashReuseAllowed:true,
  selectorReusesFrozenMinimalHybrid:false,
  selectorObjectiveMayUseFutureOutcome:false,
  futureOutcomeMayBeUsedAsEvaluationLabelOnly:true,
});

export const PHASE57_LONG_ONLY_SAFETY=Object.freeze({
  phase:'57.long-only-cash-equity',
  mode:'READ_ONLY_RESEARCH',
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
});

export const PHASE57_LONG_ONLY_DATA_PARTITIONS=Object.freeze({
  order:Object.freeze(['DEVELOPMENT_A','DEVELOPMENT_B','DEVELOPMENT_C','DEVELOPMENT_D','VALIDATION','VALIDATION_REPLICATION','PRIMARY_OOS','CONTINGENCY_OOS','RESERVE','FRESH_PROSPECTIVE']),
  DEVELOPMENT_A:Object.freeze({sessions:25,outcomeInspectionAllowed:true,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
  DEVELOPMENT_B:Object.freeze({sessions:15,outcomeInspectionAllowed:true,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
  DEVELOPMENT_C:Object.freeze({sessions:20,outcomeInspectionAllowed:true,thresholdSearchAllowed:false,featureSelectionAllowed:true}),
  DEVELOPMENT_D:Object.freeze({sessions:20,outcomeInspectionAllowed:true,thresholdSearchAllowed:true,featureSelectionAllowed:true}),
  VALIDATION:Object.freeze({sessions:30,outcomeInspectionAllowed:false,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
  VALIDATION_REPLICATION:Object.freeze({sessions:20,outcomeInspectionAllowed:false,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
  PRIMARY_OOS:Object.freeze({sessions:30,outcomeInspectionAllowed:false,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
  CONTINGENCY_OOS:Object.freeze({sessions:30,outcomeInspectionAllowed:false,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
  RESERVE:Object.freeze({sessions:15,outcomeInspectionAllowed:false,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
  FRESH_PROSPECTIVE:Object.freeze({sessions:25,outcomeInspectionAllowed:false,thresholdSearchAllowed:false,featureSelectionAllowed:false}),
});

const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);

export function assertLongOnlyResearchContract(){
  for(const key of FALSE_KEYS){
    if(PHASE57_LONG_ONLY_SAFETY[key]!==false)throw new Error(`LONG-only safety ${key} must remain false`);
  }
  const contract=PHASE57_LONG_ONLY_RESEARCH_CONTRACT;
  if(contract.longOnly!==true||contract.accountType!=='CASH_EQUITY')throw new Error('LONG-only cash-equity identity changed');
  for(const key of ['marginBuyAllowed','shortSellAllowed','marginSellAllowed','shortEntryAllowed','shortPositionAllowed','leverageAllowed']){
    if(contract[key]!==false)throw new Error(`LONG-only prohibition changed: ${key}`);
  }
  return true;
}

export function assertLongOnlyOrderIntent(intent,{availableCashJpy,lotSize=PHASE57_LONG_ONLY_RESEARCH_CONTRACT.defaultLotSize}={}){
  assertLongOnlyResearchContract();
  if(String(intent?.side??'').toUpperCase()!=='LONG')throw new Error('SHORT or unknown side is prohibited');
  if(intent?.accountType!=='CASH_EQUITY')throw new Error('only CASH_EQUITY is allowed');
  const quantity=Number(intent?.quantity),price=Number(intent?.price),cash=Number(availableCashJpy),lot=Number(lotSize);
  if(!Number.isInteger(quantity)||quantity<=0)throw new Error('quantity must be a positive integer');
  if(!Number.isInteger(lot)||lot<=0||quantity%lot!==0)throw new Error(`quantity must be a multiple of lot size ${lot}`);
  if(!Number.isFinite(price)||price<=0||!Number.isFinite(cash)||cash<0)throw new Error('positive price and non-negative available cash are required');
  if(quantity*price>cash+1e-9)throw new Error('order exceeds available cash');
  return true;
}

export function validatePartitionManifest(manifest={}){
  const partitions=PHASE57_LONG_ONLY_DATA_PARTITIONS.order;
  const seen=new Map();
  const normalized={};
  for(const partition of partitions){
    const sessions=[...new Set((manifest?.[partition]?.sessions??[]).map(String))].sort();
    for(const sessionDate of sessions){
      if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`invalid sessionDate in ${partition}: ${sessionDate}`);
      if(seen.has(sessionDate))throw new Error(`partition overlap: ${sessionDate} in ${seen.get(sessionDate)} and ${partition}`);
      seen.set(sessionDate,partition);
    }
    normalized[partition]=Object.freeze({sessions:Object.freeze(sessions),opened:Boolean(manifest?.[partition]?.opened)});
  }
  const opened=partitions.filter(partition=>normalized[partition].opened);
  if(opened.some(partition=>!partition.startsWith('DEVELOPMENT_')))throw new Error('only explicitly released Development blocks may be opened before validation');
  const releasedDevelopment=opened.map(partition=>partition.at(-1)).sort();
  if(releasedDevelopment.some((letter,index)=>letter!==String.fromCharCode(65+index)))throw new Error('Development blocks must be released in A/B/C/D order');
  return Object.freeze({
    partitions:Object.freeze(normalized),
    manifestSha256:createHash('sha256').update(JSON.stringify(normalized)).digest('hex'),
  });
}

assertLongOnlyResearchContract();
