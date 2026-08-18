import {
  buildPhase57ProspectiveSnapshotPipeline,
  PHASE58_P13_FROZEN_POLICY,
  PHASE58_TARGET_MODES,
} from '../scalping/phase58-phase57-prospective-pipeline.js';
import {buildP252FrozenDaySessionLedger} from './phase57-p25-2e-frozen-day-session-ledger.js';

export const PHASE57_P25_2F_SAFETY=Object.freeze({
  phase:'57.p25.2f.postsession-point-in-time-replay',
  mode:'READ_ONLY_POSTSESSION_PREFIX_REPLAY',
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

export const PHASE57_P25_2F_POLICY=Object.freeze({
  frozenPhase57PolicyId:PHASE58_P13_FROZEN_POLICY.policyId,
  replayMode:'POST_SESSION_FROZEN_UNIVERSE_PREFIX_ONLY',
  minimumPrefixBars:6,
  requireOneCommonBarTimestampAcrossTargetUnion:true,
  currentDecisionReceivesPrefixOnly:true,
  fullSessionBarsMayBeAvailableToReplayController:true,
  fullSessionFutureBarsPassedToScorer:false,
  outcomeMaterializationInThisPart:false,
  entryThresholdRelaxationAllowed:false,
  universeSizeSelectionFromOuterOosAllowed:false,
  postHocWinnerFilteringAllowed:false,
});

const FORBIDDEN_BAR_KEYS=Object.freeze([
  'outcomeAt','label','actualReturnPct','futureReturnPct','netReturnPct','grossReturnPct','hit','tradeWin','target',
]);
const JST=new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',
});

function normalizeSymbol(value){return String(value??'').trim().toUpperCase();}
function finite(value){return value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));}
function jstDate(timestamp){
  const ms=Date.parse(String(timestamp??''));
  if(!Number.isFinite(ms))return null;
  const parts=Object.fromEntries(JST.formatToParts(new Date(ms)).map(x=>[x.type,x.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}
function addMinutesIso(timestamp,minutes){
  const ms=Date.parse(timestamp);
  return Number.isFinite(ms)?new Date(ms+minutes*60_000).toISOString():null;
}

function targetUnionFromRecord(record){
  if(record?.ready!==true||!record?.variants)throw new Error('P25.2F requires a ready frozen universe record');
  const sessionDate=String(record.sessionDate??'').trim();
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('frozen universe sessionDate must be YYYY-MM-DD');
  const expected={FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50};
  const normalized={};
  for(const [variant,count] of Object.entries(expected)){
    const values=record.variants?.[variant];
    if(!Array.isArray(values)||values.length!==count)throw new Error(`${variant} must contain exactly ${count} symbols`);
    const symbols=values.map(normalizeSymbol);
    if(symbols.some(x=>!x)||new Set(symbols).size!==count)throw new Error(`${variant} contains blank or duplicate symbols`);
    normalized[variant]=symbols;
  }
  if(!normalized.DYNAMIC_30.every((x,i)=>normalized.DYNAMIC_40[i]===x)||!normalized.DYNAMIC_40.every((x,i)=>normalized.DYNAMIC_50[i]===x)){
    throw new Error('Dynamic30/40/50 must remain nested prefixes');
  }
  return {sessionDate,targetUnion:[...new Set(Object.values(normalized).flat())].sort()};
}

function normalizeBars(symbol,rows,sessionDate){
  if(!Array.isArray(rows))throw new Error(`bars missing for ${symbol}`);
  const out=rows.map((bar,index)=>{
    if(!bar||typeof bar!=='object')throw new Error(`invalid 5m bar for ${symbol} at index ${index}`);
    const poisoned=FORBIDDEN_BAR_KEYS.filter(key=>Object.prototype.hasOwnProperty.call(bar,key));
    if(poisoned.length)throw new Error(`5m bar contains forbidden outcome fields for ${symbol}: ${poisoned.join(',')}`);
    const timestamp=String(bar.timestamp??bar.time??'').trim();
    if(!Number.isFinite(Date.parse(timestamp)))throw new Error(`invalid 5m timestamp for ${symbol} at index ${index}`);
    if(jstDate(timestamp)!==sessionDate)throw new Error(`cross-session 5m bar for ${symbol}: ${timestamp}`);
    for(const key of ['open','high','low','close'])if(!finite(bar[key])||Number(bar[key])<=0)throw new Error(`invalid ${key} for ${symbol} at ${timestamp}`);
    if(!finite(bar.volume)||Number(bar.volume)<0)throw new Error(`invalid volume for ${symbol} at ${timestamp}`);
    const normalized={
      timestamp:new Date(Date.parse(timestamp)).toISOString(),
      open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),volume:Number(bar.volume),
    };
    if(normalized.high<normalized.low||normalized.high<Math.max(normalized.open,normalized.close)||normalized.low>Math.min(normalized.open,normalized.close)){
      throw new Error(`invalid OHLC relationship for ${symbol} at ${timestamp}`);
    }
    return Object.freeze(normalized);
  }).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(new Set(out.map(x=>x.timestamp)).size!==out.length)throw new Error(`duplicate 5m timestamps for ${symbol}`);
  return Object.freeze(out);
}

function commonTimestamps(barsBySymbol,targetUnion,minimumPrefixBars){
  const sets=targetUnion.map(symbol=>new Set((barsBySymbol.get(symbol)??[]).map(x=>x.timestamp)));
  if(!sets.length)return [];
  const common=[...sets[0]].filter(timestamp=>sets.every(set=>set.has(timestamp))).sort();
  return common.filter(timestamp=>targetUnion.every(symbol=>{
    const bars=barsBySymbol.get(symbol)??[];
    return bars.filter(bar=>bar.timestamp<=timestamp).length>=minimumPrefixBars;
  }));
}

function defaultScorePrefix({historicalSessions,currentPrefix}){
  return buildPhase57ProspectiveSnapshotPipeline({
    historicalSessions,
    currentPrefix,
    policy:PHASE58_P13_FROZEN_POLICY,
    targetMode:PHASE58_TARGET_MODES.REUSABLE_RESEARCH_TARGET,
  });
}

/**
 * Replays a session only after its universe was frozen before the open. The replay
 * controller may possess the completed session bars, but each Phase57 scorer call
 * receives only bars at or before that decision cutoff. Outcomes are not created
 * here. This is prospective-universe OOS replay evidence, not a claim that the
 * decision was computed live at the original wall-clock time.
 */
export function replayP252FrozenDaySession({
  universeRecord,
  historicalSessions=[],
  sessionBarsBySymbol={},
  minimumPrefixBars=PHASE57_P25_2F_POLICY.minimumPrefixBars,
  scorePrefix=defaultScorePrefix,
}={}){
  if(!Number.isInteger(Number(minimumPrefixBars))||Number(minimumPrefixBars)<6)throw new TypeError('minimumPrefixBars must be an integer >= 6');
  if(typeof scorePrefix!=='function')throw new TypeError('scorePrefix must be a function');
  const universe=targetUnionFromRecord(universeRecord);
  const input=sessionBarsBySymbol instanceof Map?sessionBarsBySymbol:new Map(Object.entries(sessionBarsBySymbol??{}));
  const bars=new Map();
  for(const symbol of universe.targetUnion){
    const value=input.get(symbol)??input.get(symbol.replace(/\.T$/,''));
    bars.set(symbol,normalizeBars(symbol,value,universe.sessionDate));
  }
  const cutoffs=commonTimestamps(bars,universe.targetUnion,Number(minimumPrefixBars));
  const scored=[],blocked=[];
  for(const cutoff of cutoffs){
    for(const symbol of universe.targetUnion){
      const prefix=(bars.get(symbol)??[]).filter(bar=>bar.timestamp<=cutoff);
      const currentPrefix=Object.freeze({
        schemaVersion:1,
        phase:'57.p25.2f.postsession-point-in-time-replay',
        status:'PHASE58_RSSCHART_5M_PREFIX_READY',
        symbol,
        sessionDate:universe.sessionDate,
        capturedAt:addMinutesIso(cutoff,5),
        latestBarClosed:true,
        bars5m:Object.freeze(prefix),
        closedBarCount:prefix.length,
        sourceBarCount:prefix.length,
        methodology:Object.freeze({
          source:'P25_2F_FROZEN_SESSION_5M_REPLAY',
          currentPrefixOnly:true,
          futureBarsPassedToScorer:false,
          currentOutcomeUsed:false,
        }),
      });
      let result;
      try{
        result=scorePrefix({
          historicalSessions,
          currentPrefix,
          symbol,
          sessionDate:universe.sessionDate,
          featureCutoff:cutoff,
          frozenPolicy:PHASE58_P13_FROZEN_POLICY,
        });
      }catch(error){
        blocked.push(Object.freeze({symbol,featureCutoff:cutoff,status:'BLOCKED_SCORER_EXCEPTION',reason:String(error?.message??error)}));
        continue;
      }
      if(!result||typeof result!=='object'||result.complete!==true||!result?.phase57?.decision||!result?.snapshot){
        blocked.push(Object.freeze({symbol,featureCutoff:cutoff,status:String(result?.status??'BLOCKED_PHASE57_RESULT_NOT_READY'),reason:'PHASE57_RESULT_NOT_COMPLETE'}));
        continue;
      }
      scored.push(result);
    }
  }
  const ledger=buildP252FrozenDaySessionLedger({universeRecord,phase57Results:scored});
  return Object.freeze({
    phase:'57.p25.2f.postsession-point-in-time-replay',
    status:cutoffs.length?'POSTSESSION_POINT_IN_TIME_REPLAY_COMPLETE':'BLOCKED_NO_COMMON_FAIR_CUTOFF',
    sessionDate:universe.sessionDate,
    targetSymbolCount:universe.targetUnion.length,
    commonFairCutoffCount:cutoffs.length,
    commonFairCutoffs:Object.freeze(cutoffs),
    scorerCallCount:scored.length+blocked.length,
    scoredDecisionCount:scored.length,
    blockedDecisionCount:blocked.length,
    blockedDecisions:Object.freeze(blocked),
    ledger,
    methodology:Object.freeze({
      universeFrozenBeforeSession:true,
      replayComputedAfterSessionAllowed:true,
      replayIsNotClaimedAsLiveWallClockDecision:true,
      eachScorerReceivesPrefixOnly:true,
      futureBarsPassedToScorer:false,
      outcomeMaterialized:false,
      commonTimestampGridOutcomeIndependent:true,
      entryThresholdRelaxed:false,
      universeSizeSelectedFromOuterOos:false,
      postHocWinnerFiltering:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2F_SAFETY,
  });
}

export default {replayP252FrozenDaySession,PHASE57_P25_2F_POLICY,PHASE57_P25_2F_SAFETY};
