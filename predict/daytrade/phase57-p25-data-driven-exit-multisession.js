import {assembleP253AutonomousEvidenceInputs} from './phase57-p25-3d-autonomous-evidence-evaluation.js';
import {runP253AKDynamicManagementSession,buildP253AKManagementRows} from './phase57-p25-3ak-dynamic-management-prospective.js';
import {buildP25DataDrivenExitAnalogPool,simulateP25DataDrivenExit,P25_DATA_DRIVEN_EXIT_SAFETY} from './phase57-p25-data-driven-exit.js';

export const P25_DATA_DRIVEN_PAIRED_SAFETY=Object.freeze({
  ...P25_DATA_DRIVEN_EXIT_SAFETY,
  phase:'57.p25.data-driven-exit.paired.v1',
  mode:'EXACT_D50_PAIRED_RESEARCH_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const keyOf=row=>`${String(row?.sessionDate??'')}|${String(row?.entryTimestamp??'')}|${String(row?.symbol??'').trim().toUpperCase()}`;
function profitFactor(xs){const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);}
function maxDrawdownPct(xs){let e=1,p=1,m=0;for(const r of xs){e*=1+r/100;p=Math.max(p,e);m=Math.max(m,(p-e)/p*100);}return m;}
function summarizeReturns(xs){const r=xs.map(Number).filter(Number.isFinite);let e=1;for(const x of r)e*=1+x/100;return Object.freeze({n:r.length,netReturnPct:(e-1)*100,meanNetReturnPct:mean(r),medianNetReturnPct:median(r),winRate:r.length?r.filter(x=>x>0).length/r.length:null,profitFactor:profitFactor(r),maxDrawdownPct:maxDrawdownPct(r)});}
export function summarizeP25DataDrivenPairs(pairs=[]){const rows=Array.isArray(pairs)?pairs:[],fixed=rows.map(x=>x.fixed?.netReturnPct).filter(finite).map(Number),data=rows.map(x=>x.dataDriven?.netReturnPct).filter(finite).map(Number),delta=rows.map(x=>x.deltaNetReturnPct).filter(finite).map(Number);return Object.freeze({pairedCount:rows.length,fixed:summarizeReturns(fixed),dataDriven:summarizeReturns(data),delta:Object.freeze({meanNetReturnPct:mean(delta),medianNetReturnPct:median(delta),dataDrivenBetterCount:delta.filter(x=>x>0).length,dataDrivenWorseCount:delta.filter(x=>x<0).length,equalCount:delta.filter(x=>x===0).length,meanBarsHeld:mean(rows.map(x=>x.dataDriven?.barsHeld).filter(finite).map(Number)),meanGivebackPct:mean(rows.map(x=>x.dataDriven?.givebackPct).filter(finite).map(Number)),meanCaptureRatio:mean(rows.map(x=>x.dataDriven?.captureRatio).filter(finite).map(Number))})});}

export function runP25DataDrivenExitMultisession({historyPack,captureArtifacts=[],sessionIntegrityLedger,lineageManifest,sessionDates=null,scorePrefix=null,roundTripCostPct=0.05}={}){
  const assembled=assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts,sessionIntegrityLedger,lineageManifest});
  const analogPool=buildP25DataDrivenExitAnalogPool({historicalSessions:assembled.historicalSessions});
  if(!analogPool.length)throw new Error('P25 data-driven paired evaluator: causal analog pool empty');
  const requested=sessionDates==null?null:new Set((Array.isArray(sessionDates)?sessionDates:[sessionDates]).map(String));
  const selected=requested==null?assembled.sessionInputs:assembled.sessionInputs.filter(x=>requested.has(String(x?.universeRecord?.sessionDate??'')));
  if(requested&&selected.length!==requested.size)throw new Error('P25 data-driven paired evaluator: requested session shard not ready');
  const pairs=[],sessions=[];
  for(const input of selected){
    const base=runP253AKDynamicManagementSession({universeRecord:input.universeRecord,historicalSessions:assembled.historicalSessions,sessionBarsBySymbol:input.sessionBarsBySymbol??{},...(typeof scorePrefix==='function'?{scorePrefix}:{}),});
    const frozen=base?.replay?.ledger?.frozenTrades??[];
    const managed=buildP253AKManagementRows({frozenTrades:frozen,sessionBarsBySymbol:input.sessionBarsBySymbol??{}});
    const rowByKey=new Map(managed.rows.map(r=>[keyOf(r),r]));
    const fixedByKey=new Map((base?.fixedOutcomes?.resolvedTrades??[]).map(r=>[keyOf(r),r]));
    let d50=0,paired=0;
    for(const trade of frozen){
      if(!(trade?.variantMemberships??[]).includes('DYNAMIC_50'))continue;
      d50+=1;
      const key=keyOf(trade),row=rowByKey.get(key),fixed=fixedByKey.get(key);
      if(!row||!fixed)continue;
      const dataDriven=simulateP25DataDrivenExit({row,analogPool,roundTripCostPct});
      const fixedNet=Number(fixed.netReturnPct??fixed.afterCostReturnPct??fixed.returnPct);
      if(!Number.isFinite(fixedNet))throw new Error(`P25 data-driven paired evaluator: fixed net missing for ${key}`);
      pairs.push(Object.freeze({key,sessionDate:trade.sessionDate,symbol:trade.symbol,sector:trade.sector??'UNKNOWN',variantMemberships:Object.freeze([...(trade.variantMemberships??[])]),fixed:Object.freeze({...fixed,netReturnPct:fixedNet}),dataDriven,deltaNetReturnPct:dataDriven.netReturnPct-fixedNet,deltaBarsHeld:Number(dataDriven.barsHeld)-Number(fixed.barsHeld??0)}));
      paired+=1;
    }
    sessions.push(Object.freeze({sessionDate:base.sessionDate,dynamic50FrozenCount:d50,pairedCount:paired,managementBlockedCount:managed.blocked.length}));
  }
  pairs.sort((a,b)=>a.key.localeCompare(b.key));
  if(pairs.some(p=>!p.variantMemberships.includes('DYNAMIC_50')))throw new Error('P25 data-driven paired evaluator: non-DYNAMIC_50 pair detected');
  return Object.freeze({phase:'57.p25.data-driven-exit.paired.v1',status:'P25_DATA_DRIVEN_EXIT_PAIRED_EVALUATED',lineageManifestHeadSha256:assembled.lineageManifestHeadSha256,analogPoolCount:analogPool.length,readySessionCount:selected.length,sessions:Object.freeze(sessions),pairs:Object.freeze(pairs),summary:summarizeP25DataDrivenPairs(pairs),methodology:Object.freeze({exactDynamic50Only:true,sameFrozenEntryAsFixed:true,fixedBaselineUntouched:true,pre20260812HistoricalAnalogOnlyByUpstreamPin:true,currentProspectiveOutcomeUsedForFitting:false,resultBasedRetuning:false,fixedHorizonUsedAsDecisionInput:false,freshHoldoutConsumed:false}),safety:P25_DATA_DRIVEN_PAIRED_SAFETY});
}

export default {runP25DataDrivenExitMultisession,summarizeP25DataDrivenPairs,P25_DATA_DRIVEN_PAIRED_SAFETY};
