import {buildIntradayDynamicUniverseTimeline,PHASE57_INTRADAY_UNIVERSE_SAFETY} from './phase57-p25-intraday-dynamic-universe.js';

export const PHASE57_INTRADAY_UNIVERSE_V2_POLICY=Object.freeze({
  candidateId:'INTRADAY_DYNAMIC_5M_UNIVERSE_V2',
  baseCandidateId:'INTRADAY_DYNAMIC_5M_UNIVERSE_V1',
  finalUniverseSize:30,
  maxPerSector:3,
  persistenceWindowPoints:3,
  weights:Object.freeze({baseOpportunity:0.42,liquidityQuality:0.23,persistence:0.20,signalQuality:0.15}),
  firstFreshEligibleDate:'2026-09-01',
  august31PartialRole:'FAILURE_ANALYSIS_ONLY',
  august31UsedForWeightSearch:false,
  august31UsedForThresholdSearch:false,
  futureOutcomeSelectionAllowed:false,
  entryCompatibilityOutcomeFitAllowed:false,
  postHocWinnerFilteringAllowed:false,
  replaceFrozenDynamic50:false,
  formalOos:false,
  promotionEligible:false,
});

export const PHASE57_INTRADAY_UNIVERSE_V2_SAFETY=Object.freeze({...PHASE57_INTRADAY_UNIVERSE_SAFETY,phase:'57.p25.intraday-dynamic-universe-v2',mode:'READ_ONLY_5M_DYNAMIC_UNIVERSE_V2_RESEARCH_CHALLENGER'});
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const clamp=(v,min=0,max=1)=>Math.min(max,Math.max(min,Number(v)));
const sym=v=>String(v??'').trim().toUpperCase();
const sector=v=>String(v??'未分類').trim()||'未分類';
function conf01(v){if(!finite(v))return 0;const n=Number(v);return clamp(n<=1?n:n/100);}
function quality01(v){return finite(v)?clamp(Number(v)/100):0;}
function liquidityScore(row){
  const turnover=Math.max(0,Number(row?.currentPrice??0)*Number(row?.volume??0));
  const volumeRatio=Math.max(0,Number(row?.volumeRatio??0));
  const atr=Math.max(0,Number(row?.atrPercent??0));
  const absChange=Math.abs(Number(row?.dailyChangePercent??0));
  const turnoverScore=clamp(Math.log10(1+turnover)/10);
  const participation=clamp(volumeRatio/4);
  const directionalEfficiency=atr>0?clamp(absChange/atr):0;
  const excessNoisePenalty=atr>0?clamp(Math.max(0,atr-absChange)/(atr*2)):0;
  return clamp(turnoverScore*0.45+participation*0.30+directionalEfficiency*0.25-excessNoisePenalty*0.20);
}
function signalQualityScore(row){
  const discovery=finite(row?.discoveryScore)?Math.abs(Number(row.discoveryScore)-50)/50:0;
  const technical=finite(row?.technicalScore)?Math.abs(Number(row.technicalScore)-50)/50:0;
  return clamp(discovery*0.30+technical*0.30+conf01(row?.confidence)*0.20+quality01(row?.qualityScore)*0.20);
}
function diversify(rows,count,maxPerSector){const out=[],counts=new Map();for(const row of rows){if(out.length>=count)break;const s=row.sector,n=counts.get(s)??0;if(n>=maxPerSector)continue;out.push(row);counts.set(s,n+1);}return out;}

export function buildIntradayDynamicUniverseTimelineV2({snapshots=[],heldSymbolsByCutoff={},policy={}}={}){
  const cfg={...PHASE57_INTRADAY_UNIVERSE_V2_POLICY,...policy,weights:{...PHASE57_INTRADAY_UNIVERSE_V2_POLICY.weights,...policy?.weights}};
  if(!Number.isInteger(Number(cfg.finalUniverseSize))||Number(cfg.finalUniverseSize)<1)throw new TypeError('finalUniverseSize must be positive integer');
  if(!Number.isInteger(Number(cfg.maxPerSector))||Number(cfg.maxPerSector)<1)throw new TypeError('maxPerSector must be positive integer');
  if(!Number.isInteger(Number(cfg.persistenceWindowPoints))||Number(cfg.persistenceWindowPoints)<1)throw new TypeError('persistenceWindowPoints must be positive integer');
  const weightSum=Object.values(cfg.weights).reduce((s,v)=>s+Number(v),0);if(Math.abs(weightSum-1)>1e-9)throw new Error('Dynamic5m v2 weights must sum to 1');
  if(cfg.futureOutcomeSelectionAllowed!==false||cfg.postHocWinnerFilteringAllowed!==false||cfg.replaceFrozenDynamic50!==false)throw new Error('Dynamic5m v2 safety policy violation');

  const base=buildIntradayDynamicUniverseTimeline({snapshots,heldSymbolsByCutoff,policy:{finalUniverseSize:50}});
  const snapshotBySource=new Map(snapshots.map(s=>[String(s?.asOf??''),s]));
  const recentSelections=[];const points=[];
  for(const point of base.points){
    const source=snapshotBySource.get(point.sourceAsOf);const bySymbol=new Map((source?.entries??[]).map(r=>[sym(r.symbol),r]));
    const previous=recentSelections.slice(-Number(cfg.persistenceWindowPoints));
    const scored=point.rawUniverse.map(baseRow=>{
      const row=bySymbol.get(sym(baseRow.symbol))??{};
      const appearances=previous.reduce((n,set)=>n+(set.has(sym(baseRow.symbol))?1:0),0);
      const persistence=previous.length?appearances/previous.length:0;
      const liquidityQuality=liquidityScore(row),signalQuality=signalQualityScore(row),baseOpportunity=clamp(Number(baseRow.opportunityScore??0));
      const v2Score=baseOpportunity*cfg.weights.baseOpportunity+liquidityQuality*cfg.weights.liquidityQuality+persistence*cfg.weights.persistence+signalQuality*cfg.weights.signalQuality;
      return Object.freeze({...baseRow,sector:sector(baseRow.sector),v2Score:Number(clamp(v2Score).toFixed(6)),components:Object.freeze({baseOpportunity,liquidityQuality,persistence,signalQuality})});
    }).sort((a,b)=>b.v2Score-a.v2Score||b.opportunityScore-a.opportunityScore||b.turnoverYen-a.turnoverYen||a.symbol.localeCompare(b.symbol));
    const selected=diversify(scored,Number(cfg.finalUniverseSize),Number(cfg.maxPerSector));
    const held=new Set((heldSymbolsByCutoff?.[point.sourceAsOf]??heldSymbolsByCutoff?.[point.asOf]??[]).map(sym));
    const allocationEligible=selected.filter(x=>!held.has(sym(x.symbol)));
    recentSelections.push(new Set(selected.map(x=>sym(x.symbol))));
    points.push(Object.freeze({...point,rawUniverse:Object.freeze(selected),allocationEligibleUniverse:Object.freeze(allocationEligible),heldExcludedCount:selected.length-allocationEligible.length,v2RankedUniverse:Object.freeze(scored)}));
  }
  return Object.freeze({
    phase:'57.p25.intraday-dynamic-universe-v2',status:'INTRADAY_DYNAMIC_5M_UNIVERSE_V2_TIMELINE_READY',candidateId:cfg.candidateId,
    points:Object.freeze(points),baseDiagnostics:base.diagnostics,
    methodology:Object.freeze({marketWideRefreshEachFiveMinutes:true,baseV1PrescreenRetained:true,causalPersistenceOnly:true,liquidityQualityGate:true,directionalEfficiencyProxy:true,sectorConcentrationCap:true,futureOutcomeUsed:false,entryOutcomeFitUsed:false,postHocWinnerFiltering:false,formalOos:false,promotionEligible:false}),
    policy:Object.freeze(cfg),safety:PHASE57_INTRADAY_UNIVERSE_V2_SAFETY,
  });
}

export default {buildIntradayDynamicUniverseTimelineV2,PHASE57_INTRADAY_UNIVERSE_V2_POLICY,PHASE57_INTRADAY_UNIVERSE_V2_SAFETY};
