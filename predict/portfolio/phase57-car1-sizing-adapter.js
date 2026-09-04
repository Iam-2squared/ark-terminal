import {
  PHASE57_CAR1_POLICY,
  PHASE57_CAR1_SAFETY,
  buildCausalRiskSnapshot,
  normalizeSizingWeights,
} from './phase57-car1-sizing-research.js';

const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);

function assertSafety(){
  for(const key of FALSE_KEYS){
    if(PHASE57_CAR1_SAFETY[key]!==false)throw new Error(`CAR-1 safety ${key} must remain false`);
  }
  if(PHASE57_CAR1_SAFETY.winnerSelectionAllowed!==false)throw new Error('CAR-1 winner selection must remain disabled');
  if(PHASE57_CAR1_POLICY.parameterSearchAllowed!==false)throw new Error('CAR-1 parameter search must remain disabled');
}

const iso=value=>{
  const ms=Date.parse(String(value??''));
  if(!Number.isFinite(ms))throw new Error(`invalid CAR-1 timestamp: ${value??'MISSING'}`);
  return new Date(ms).toISOString();
};

function symbolOf(row){
  const symbol=String(row?.symbol??'').trim().toUpperCase();
  if(!symbol)throw new Error('CAR-1 symbol required');
  return symbol;
}

function keyOf(row){
  const explicit=String(row?.key??'').trim();
  if(explicit)return explicit;
  const sessionDate=String(row?.sessionDate??'').trim();
  return `${sessionDate}|${iso(row?.entryTimestamp??row?.featureCutoff)}|${symbolOf(row)}`;
}

function causalBars(rows,cutoff){
  const all=Array.isArray(rows)?rows:[];
  return all.filter(row=>iso(row?.timestamp??row?.time)<=cutoff);
}

export function buildCausalSizingGroup({profileId,entries,barsBySymbol}={}){
  assertSafety();
  const ordered=[...(Array.isArray(entries)?entries:[])].sort((a,b)=>{
    const left=iso(a?.entryTimestamp??a?.featureCutoff),right=iso(b?.entryTimestamp??b?.featureCutoff);
    return left.localeCompare(right)||symbolOf(a).localeCompare(symbolOf(b))||keyOf(a).localeCompare(keyOf(b));
  });
  if(ordered.length===0)return Object.freeze({profileId,entryTimestamp:null,candidates:Object.freeze([]),weights:Object.freeze([])});
  const entryTimestamp=iso(ordered[0]?.entryTimestamp??ordered[0]?.featureCutoff);
  if(ordered.some(row=>iso(row?.entryTimestamp??row?.featureCutoff)!==entryTimestamp)){
    throw new Error('CAR-1 sizing group must contain one simultaneous Entry timestamp');
  }
  const source=barsBySymbol instanceof Map?barsBySymbol:new Map(Object.entries(barsBySymbol??{}));
  const candidates=ordered.map(row=>{
    const symbol=symbolOf(row),key=keyOf(row);
    let riskSnapshot=null;
    if(profileId!=='EQUAL_NOTIONAL'){
      const bars=source.get(symbol)??source.get(symbol.replace(/\.T$/,''));
      if(!Array.isArray(bars))throw new Error(`CAR-1 bars missing for ${symbol}`);
      riskSnapshot=buildCausalRiskSnapshot({bars:causalBars(bars,entryTimestamp),entryTimestamp});
    }
    return Object.freeze({key,symbol,entryTimestamp,riskSnapshot});
  });
  const weights=normalizeSizingWeights({profileId,candidates});
  return Object.freeze({
    profileId,
    entryTimestamp,
    candidates:Object.freeze(candidates),
    weights,
    audit:Object.freeze({
      simultaneousEntryOrder:'TIMESTAMP_THEN_SYMBOL',
      futureBarUsed:false,
      futureOutcomeUsed:false,
      rankingChanged:false,
      entryChanged:false,
      exitChanged:false,
      costChanged:false,
      winnerSelectionAllowed:false,
    }),
  });
}

export function targetBudgetsFromGroup({group,equityBeforeEntry,maxPositions}={}){
  assertSafety();
  const equity=Number(equityBeforeEntry),slots=Number(maxPositions);
  if(!Number.isFinite(equity)||equity<=0)throw new Error('CAR-1 equityBeforeEntry must be positive');
  if(!Number.isInteger(slots)||slots<1)throw new Error('CAR-1 maxPositions must be a positive integer');
  const weights=Array.isArray(group?.weights)?group.weights:[];
  if(weights.length===0)return Object.freeze([]);
  const groupSize=weights.length;
  const totalGroupBudget=equity*groupSize/slots;
  return Object.freeze(weights.map(row=>Object.freeze({
    key:row.key,
    weight:row.weight,
    targetBudgetJpy:totalGroupBudget*row.weight,
    targetBudgetFractionOfEquity:(groupSize/slots)*row.weight,
  })));
}
