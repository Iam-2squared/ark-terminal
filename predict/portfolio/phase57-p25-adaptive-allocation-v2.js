import {createHash} from 'node:crypto';

export const PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY=Object.freeze({
  phase:'57.p25.adaptive-allocation-v2',mode:'READ_ONLY_EVENT_TIME_ADAPTIVE_PORTFOLIO_RESEARCH',researchOnly:true,
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

export const PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY=Object.freeze({
  candidateId:'ADAPTIVE_ALLOCATION_V2',firstFreshEligibleDate:'2026-09-01',initialEquityJpy:1_000_000,lotSize:100,
  maximumConcurrentPositions:9,minimumConcurrentPositions:1,roundTripCostPct:0.05,
  rankThresholds:Object.freeze({S:0.85,A:0.70,B:0.55,C:0}),
  candidateEquityCaps:Object.freeze({S:0.45,A:0.35,B:0.25,C:0.15}),
  deployment:Object.freeze({singleRankTarget:Object.freeze({S:0.68,A:0.56,B:0.44,C:0.30}),breadthBonusPerAdditionalCandidate:0.055,maximumTargetUtilization:0.92}),
  scoreWeights:Object.freeze({entryConfidence:0.30,entryProbability:0.20,selectionOpportunity:0.25,selectionV2:0.25}),
  allocationProfiles:Object.freeze([
    Object.freeze({id:'ADAPTIVE_EQUAL',weighting:'EQUAL'}),
    Object.freeze({id:'ADAPTIVE_RANK',weighting:'RANK'}),
    Object.freeze({id:'ADAPTIVE_SCORE',weighting:'SCORE'}),
  ]),
  rankWeights:Object.freeze({S:4,A:3,B:2,C:1}),
  futureOutcomeVisibleToAllocator:false,resultBasedRetuning:false,postHocWinnerFiltering:false,winnerSelectionAllowed:false,
});

const FALSE_KEYS=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'];
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const clamp=(v,min=0,max=1)=>Math.min(max,Math.max(min,Number(v)));
const mean=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
const round=(v,d=6)=>Number.isFinite(v)?Number(v.toFixed(d)):v;
const sym=v=>String(v??'').trim().toUpperCase();
const iso=v=>{const t=Date.parse(String(v??''));if(!Number.isFinite(t))throw new Error(`invalid timestamp ${v}`);return new Date(t).toISOString();};
const hash=v=>createHash('sha256').update(JSON.stringify(v)).digest('hex');
function assertSafety(){for(const k of FALSE_KEYS)if(PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY[k]!==false)throw new Error(`unsafe ${k}`);}
function norm01(v){if(!finite(v))return null;const n=Number(v);return clamp(n>1?n/100:n);}
function opp01(v){if(!finite(v))return null;const n=Number(v);return clamp(n>1?n/100:n);}

export function scoreP25AdaptiveAllocationCandidate(entry,{policy=PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY}={}){
  const parts={
    entryConfidence:norm01(entry?.confidence),entryProbability:norm01(entry?.probability),
    selectionOpportunity:opp01(entry?.selectionOpportunityScore),selectionV2:opp01(entry?.selectionV2Score),
  };
  let num=0,den=0;for(const [k,w] of Object.entries(policy.scoreWeights)){if(parts[k]!==null){num+=parts[k]*Number(w);den+=Number(w);}}
  if(den<=0)throw new Error('adaptive allocation candidate has no causal quality inputs');
  const score=clamp(num/den);let rank='C';if(score>=policy.rankThresholds.S)rank='S';else if(score>=policy.rankThresholds.A)rank='A';else if(score>=policy.rankThresholds.B)rank='B';
  return Object.freeze({score:round(score),rank,components:Object.freeze(parts),equityCap:Number(policy.candidateEquityCaps[rank])});
}

function targetUtilization(ranked,{policy}){
  if(!ranked.length)return 0;
  const best=ranked.map(x=>x.quality.rank).sort((a,b)=>['S','A','B','C'].indexOf(a)-['S','A','B','C'].indexOf(b))[0];
  const base=Number(policy.deployment.singleRankTarget[best]);
  return Math.min(Number(policy.deployment.maximumTargetUtilization),base+Math.max(0,ranked.length-1)*Number(policy.deployment.breadthBonusPerAdditionalCandidate));
}
function profileWeight(row,profile,policy){if(profile.weighting==='EQUAL')return 1;if(profile.weighting==='RANK')return Number(policy.rankWeights[row.quality.rank]);return Math.max(1e-6,row.quality.score);}
function barMap(sessionBarsBySymbol){const out=new Map();for(const [raw,rows] of Object.entries(sessionBarsBySymbol??{})){const s=sym(raw),m=new Map();for(const b of rows??[]){const t=iso(b.timestamp),p=Number(b.close);if(Number.isFinite(p)&&p>0)m.set(t,p);}out.set(s,m);}return out;}
function maximumDrawdown(curve,initial){let peak=initial,max=0;for(const x of curve){peak=Math.max(peak,x.equityJpy);if(peak>0)max=Math.max(max,(peak-x.equityJpy)/peak*100);}return max;}

export function simulateP25AdaptiveAllocationV2({sessions=[],profile=PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.allocationProfiles[0],policy=PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY}={}){
  assertSafety();if(!policy.allocationProfiles.some(x=>x.id===profile.id))throw new Error('unknown adaptive allocation profile');
  const initial=Number(policy.initialEquityJpy),lot=Number(policy.lotSize),halfCost=Number(policy.roundTripCostPct)/200;
  let cash=initial,realizedPnl=0,turnover=0,maxConcurrent=0,recycling=0,missedHighQuality=0;
  const positions=new Map(),closed=[],decisions=[],curve=[],utilSamples=[],candidateRanks=[];
  for(const session of [...sessions].sort((a,b)=>String(a.sessionDate).localeCompare(String(b.sessionDate)))){
    const date=String(session.sessionDate??'');if(!/^\d{4}-\d{2}-\d{2}$/.test(date))throw new Error('adaptive allocation sessionDate invalid');
    const bars=barMap(session.sessionBarsBySymbol??{}),events=new Map();
    const event=t=>{if(!events.has(t))events.set(t,{entries:[],exits:[],marks:[]});return events.get(t);};
    for(const [s,m] of bars)for(const [t,p] of m)event(t).marks.push({symbol:s,price:p});
    for(const row of session.trades??[]){
      if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false)throw new Error('adaptive allocation accepts frozen outcome-free entries only');
      const e={...row,symbol:sym(row.symbol),entryTimestamp:iso(row.entryTimestamp),exitTimestamp:iso(row.exitTimestamp),entryPrice:Number(row.entryPrice),exitPrice:Number(row.exitPrice),signalDirection:Number(row.signalDirection)};
      if(![-1,1].includes(e.signalDirection)||!Number.isFinite(e.entryPrice)||!Number.isFinite(e.exitPrice))throw new Error('adaptive allocation resolved trade invalid');
      event(e.entryTimestamp).entries.push(e);event(e.exitTimestamp).exits.push(e);
    }
    const marks=new Map();
    for(const [timestamp,ev] of [...events].sort(([a],[b])=>a.localeCompare(b))){
      for(const m of ev.marks)marks.set(m.symbol,m.price);
      for(const x of ev.exits.sort((a,b)=>a.symbol.localeCompare(b.symbol))){
        const pos=positions.get(x.symbol);if(!pos)continue;
        const exitCost=pos.quantity*x.exitPrice*halfCost;
        const gross=pos.signalDirection*(x.exitPrice-pos.entryPrice)*pos.quantity;
        cash+=pos.collateral+gross-exitCost;realizedPnl+=gross-pos.entryCost-exitCost;turnover+=pos.quantity*x.exitPrice;positions.delete(x.symbol);closed.push({symbol:x.symbol,rank:pos.rank,score:pos.score,entryTimestamp:pos.entryTimestamp,exitTimestamp:timestamp,quantity:pos.quantity,realizedPnlJpy:round(gross-pos.entryCost-exitCost)});recycling++;
      }
      const equity=()=>{let e=cash;for(const p of positions.values()){const mark=marks.get(p.symbol)??p.entryPrice;e+=p.collateral+p.signalDirection*(mark-p.entryPrice)*p.quantity;}return e;};
      const grossExposure=()=>{let g=0;for(const p of positions.values())g+=p.quantity*(marks.get(p.symbol)??p.entryPrice);return g;};
      if(ev.entries.length){
        const ranked=ev.entries.filter(x=>!positions.has(x.symbol)).map(x=>({entry:x,quality:scoreP25AdaptiveAllocationCandidate(x,{policy})})).sort((a,b)=>b.quality.score-a.quality.score||a.entry.symbol.localeCompare(b.entry.symbol));
        for(const r of ranked)candidateRanks.push({timestamp,symbol:r.entry.symbol,rank:r.quality.rank,score:r.quality.score});
        const slots=Math.max(0,Number(policy.maximumConcurrentPositions)-positions.size),accepted=ranked.slice(0,slots),rejectedSlots=ranked.slice(slots);
        for(const r of rejectedSlots){decisions.push({timestamp,symbol:r.entry.symbol,status:'REJECTED',reason:'MAX_CONCURRENT_POSITIONS',rank:r.quality.rank,score:r.quality.score});if(['S','A'].includes(r.quality.rank))missedHighQuality++;}
        if(accepted.length){
          const eq=equity(),existingExposure=grossExposure(),target=targetUtilization([...positions.values()].map(p=>({quality:{rank:p.rank,score:p.score}})).concat(accepted),{policy}),capacity=Math.max(0,eq*target-existingExposure),available=Math.min(cash,capacity);
          const weights=accepted.map(r=>profileWeight(r,profile,policy)),sumW=weights.reduce((a,b)=>a+b,0);
          for(let i=0;i<accepted.length;i++){
            const r=accepted[i],desired=Math.min(eq*r.quality.equityCap,available*(weights[i]/sumW)),perShare=r.entry.entryPrice*(1+halfCost),qty=Math.floor(desired/perShare/lot)*lot;
            if(qty<lot){decisions.push({timestamp,symbol:r.entry.symbol,status:'REJECTED',reason:'LOT_OR_CASH_CONSTRAINT',rank:r.quality.rank,score:r.quality.score,targetUtilization:round(target)});if(['S','A'].includes(r.quality.rank))missedHighQuality++;continue;}
            const notional=qty*r.entry.entryPrice,entryCost=notional*halfCost,cashNeed=notional+entryCost;if(cashNeed>cash+1e-8)continue;
            cash-=cashNeed;realizedPnl-=entryCost;turnover+=notional;positions.set(r.entry.symbol,{symbol:r.entry.symbol,entryTimestamp:timestamp,entryPrice:r.entry.entryPrice,signalDirection:r.entry.signalDirection,quantity:qty,collateral:notional,entryCost,rank:r.quality.rank,score:r.quality.score});maxConcurrent=Math.max(maxConcurrent,positions.size);
            decisions.push({timestamp,symbol:r.entry.symbol,status:'ACCEPTED',rank:r.quality.rank,score:r.quality.score,quantity:qty,notionalJpy:round(notional),targetUtilization:round(target),candidateEquityCap:r.quality.equityCap,weighting:profile.weighting});
          }
        }
      }
      const eqNow=equity(),expNow=grossExposure(),util=eqNow>0?expNow/eqNow:0;utilSamples.push(util);curve.push({timestamp,sessionDate:date,equityJpy:round(eqNow),cashJpy:round(cash),grossExposureJpy:round(expNow),capitalUtilization:round(util),openPositions:positions.size});
    }
  }
  if(positions.size)throw new Error('adaptive allocation ended with unresolved positions');
  const finalEquity=cash,gp=closed.filter(x=>x.realizedPnlJpy>0).reduce((s,x)=>s+x.realizedPnlJpy,0),gl=-closed.filter(x=>x.realizedPnlJpy<0).reduce((s,x)=>s+x.realizedPnlJpy,0);
  return Object.freeze({
    phase:'57.p25.adaptive-allocation-v2',status:'P25_ADAPTIVE_ALLOCATION_V2_SIMULATED',profile:Object.freeze({...profile}),policySha256:hash(policy),
    return:Object.freeze({initialEquityJpy:initial,finalEquityJpy:round(finalEquity),totalReturnPct:round((finalEquity/initial-1)*100),realizedPnlJpy:round(realizedPnl)}),
    risk:Object.freeze({maxDrawdownPct:round(maximumDrawdown(curve,initial))}),trade:Object.freeze({accepted:closed.length,winRate:closed.length?round(closed.filter(x=>x.realizedPnlJpy>0).length/closed.length):null,profitFactor:gl>0?round(gp/gl):(gp>0?Infinity:null)}),
    capitalEfficiency:Object.freeze({averageCapitalUtilization:round(mean(utilSamples)??0),peakCapitalUtilization:round(Math.max(0,...utilSamples)),idleCashRatio:round(1-(mean(utilSamples)??0)),grossTurnoverNotionalJpy:round(turnover),capitalRecyclingCount:recycling,missedHighQualityCandidates:missedHighQuality,maxConcurrentPositions:maxConcurrent}),
    candidateRanks:Object.freeze(candidateRanks),allocationDecisions:Object.freeze(decisions),equityCurve:Object.freeze(curve),
    methodology:Object.freeze({oneCandidateMayEnter:true,minimumConcurrentPositions:1,maximumConcurrentPositions:9,dynamicReserveViaTargetUtilization:true,rankedOpportunityBudgeting:true,hundredShareLots:true,futureOutcomeVisibleToAllocator:false,resultBasedRetuning:false,postHocWinnerFiltering:false,winnerSelectionAllowed:false,freshHoldoutConsumed:false}),safety:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY,
  });
}

export default {simulateP25AdaptiveAllocationV2,scoreP25AdaptiveAllocationCandidate,PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY,PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY};
