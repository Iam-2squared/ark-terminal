import crypto from 'node:crypto';
import {buildPhase58P2P3,PHASE58_P2P3_SAFETY} from './phase58-orderbook-tickflow.js';

export const PHASE58_FINAL_SAFETY=Object.freeze({...PHASE58_P2P3_SAFETY,phase:'58.p4-p8',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});
const finite=x=>Number.isFinite(Number(x));
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const canonical=x=>JSON.stringify(x,Object.keys(x).sort());

export function buildPhase57MicrostructureOverlay({phase57Direction=0,inputSeries=[],qualityOptions={}}={}){
 const intelligence=buildPhase58P2P3(inputSeries,qualityOptions); const b=intelligence.orderBook?.features??{},f=intelligence.tickFlow?.features??{};
 const votes=[b.pressureConsensus,f.signedVolumeImbalance,f.flowMomentum,b.micropriceEdgeBps].filter(finite).map(Number);
 const pressure=votes.length?votes.reduce((s,x)=>s+Math.sign(x),0)/votes.length:0;
 const direction=Math.sign(Number(phase57Direction)||0); const aligned=direction!==0&&Math.sign(pressure)===direction;
 const adverse=direction!==0&&Math.sign(pressure)===-direction;
 const degraded=intelligence.orderBook?.status!=='ORDER_BOOK_INTELLIGENCE_READY'||intelligence.tickFlow?.status!=='TICK_FLOW_INTELLIGENCE_READY';
 const action=degraded?'DEFER_TO_PHASE57':b.liquidityShock?'ABSTAIN_LIQUIDITY_SHOCK':adverse?'DEFER_TO_PHASE57':aligned?'MICROSTRUCTURE_ALIGNED':'DEFER_TO_PHASE57';
 return Object.freeze({phase:'58.p4',action,pressure,aligned,adverse,degraded,intelligence,researchOnly:true,safety:PHASE58_FINAL_SAFETY});
}

export function estimateScalpingCostBps({spreadBps,slippageBps=0.5,feesBps=0,marketImpactBps=0.25}={}){
 const spread=finite(spreadBps)?Math.max(0,Number(spreadBps)):null; if(spread===null)return Object.freeze({ready:false,totalRoundTripBps:null});
 const oneWay=spread/2+Math.max(0,Number(slippageBps)||0)+Math.max(0,Number(feesBps)||0)+Math.max(0,Number(marketImpactBps)||0);
 return Object.freeze({ready:true,spreadBps:spread,slippageBps:Number(slippageBps)||0,feesBps:Number(feesBps)||0,marketImpactBps:Number(marketImpactBps)||0,totalRoundTripBps:2*oneWay});
}

export function buildResearchScalpingDecision({phase57Direction=0,inputSeries=[],expectedGrossEdgeBps=null,qualityOptions={},costOptions={}}={}){
 const overlay=buildPhase57MicrostructureOverlay({phase57Direction,inputSeries,qualityOptions}); const spread=overlay.intelligence.orderBook?.features?.latestSpreadBps;
 const cost=estimateScalpingCostBps({spreadBps:spread,...costOptions}); const gross=finite(expectedGrossEdgeBps)?Math.max(0,Number(expectedGrossEdgeBps)):null;
 const net=gross!==null&&cost.ready?gross-cost.totalRoundTripBps:null;
 const eligible=overlay.action==='MICROSTRUCTURE_ALIGNED'&&net!==null&&net>0;
 return Object.freeze({phase:'58.p5-p6',decision:eligible?'RESEARCH_CANDIDATE':'NO_SCALP',expectedGrossEdgeBps:gross,expectedNetEdgeBps:net,cost,overlay,researchOnly:true,recommendationAllowed:false,safety:PHASE58_FINAL_SAFETY});
}

export function evaluatePinnedWalkForward({datasetBytes=null,datasetSha256=null,rows=[]}={}){
 if(!(datasetBytes instanceof Uint8Array||Buffer.isBuffer(datasetBytes)))return Object.freeze({phase:'58.p7-p8',status:'BLOCKED_NO_PINNED_MICROSTRUCTURE_DATASET',complete:false,safety:PHASE58_FINAL_SAFETY});
 const actual=crypto.createHash('sha256').update(datasetBytes).digest('hex');
 if(!datasetSha256||actual!==datasetSha256)return Object.freeze({phase:'58.p7-p8',status:'BLOCKED_DATASET_HASH_MISMATCH',complete:false,actualSha256:actual,safety:PHASE58_FINAL_SAFETY});
 if(!Array.isArray(rows)||rows.length<100)return Object.freeze({phase:'58.p7-p8',status:'BLOCKED_INSUFFICIENT_PINNED_ROWS',complete:false,actualSha256:actual,rowCount:rows?.length??0,safety:PHASE58_FINAL_SAFETY});
 const returns=rows.map(r=>Number(r.netReturn)).filter(finite); if(returns.length<100)return Object.freeze({phase:'58.p7-p8',status:'BLOCKED_INSUFFICIENT_EVALUABLE_ROWS',complete:false,actualSha256:actual,rowCount:returns.length,safety:PHASE58_FINAL_SAFETY});
 const wins=returns.filter(x=>x>0),losses=returns.filter(x=>x<0); const grossWin=wins.reduce((s,x)=>s+x,0),grossLoss=-losses.reduce((s,x)=>s+x,0); let equity=1,peak=1,maxDD=0; for(const r of returns){equity*=1+r;peak=Math.max(peak,equity);maxDD=Math.max(maxDD,(peak-equity)/peak);} const pf=grossLoss>0?grossWin/grossLoss:null;
 return Object.freeze({phase:'58.p7-p8',status:'PINNED_WALK_FORWARD_MEASURED',complete:true,datasetSha256:actual,rowCount:returns.length,netReturn:equity-1,profitFactor:pf,winRate:wins.length/returns.length,maxDrawdown:maxDD,resultSha256:crypto.createHash('sha256').update(JSON.stringify({actual,returns})).digest('hex'),safety:PHASE58_FINAL_SAFETY});
}
