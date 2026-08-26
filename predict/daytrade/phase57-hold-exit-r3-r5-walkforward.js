export const R3_R5_SAFETY=Object.freeze({executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});

const CANDIDATES=Object.freeze([
 Object.freeze({id:'FIXED',kind:'FIXED'}),
 Object.freeze({id:'HPX_P2_A075_G075',kind:'HOLD_PROTECT_EXIT',persistenceBars:2,adverseAtr:0.75,givebackAtr:0.75}),
 Object.freeze({id:'HPX_P2_A100_G100',kind:'HOLD_PROTECT_EXIT',persistenceBars:2,adverseAtr:1.00,givebackAtr:1.00}),
 Object.freeze({id:'HPX_P3_A075_G075',kind:'HOLD_PROTECT_EXIT',persistenceBars:3,adverseAtr:0.75,givebackAtr:0.75}),
 Object.freeze({id:'HPX_P3_A100_G100',kind:'HOLD_PROTECT_EXIT',persistenceBars:3,adverseAtr:1.00,givebackAtr:1.00}),
]);
export const R3_R5_CANDIDATES=CANDIDATES;
const finite=x=>Number.isFinite(Number(x));
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
function atrPct(row){const b=(row.contextBars||[]).slice(-12);if(b.length<2)return 0.5;const trs=[];for(let i=1;i<b.length;i++){const p=+b[i-1].close,h=+b[i].high,l=+b[i].low;if(finite(p)&&finite(h)&&finite(l)&&p>0)trs.push((Math.max(h,p)-Math.min(l,p))/p*100);}return trs.length?Math.max(0.05,mean(trs)):0.5;}
function dir(row){return row.signalDirection===1||row.signalDirection==='LONG'?1:-1;}
function signedRet(row,bar){return ((+bar.close/+row.entryPrice)-1)*100*dir(row);}
function pf(xs){const g=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),l=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return l>0?g/l:(g>0?Infinity:null);}
function summary(outcomes){const xs=outcomes.map(x=>x.netReturnPct).filter(finite).map(Number),eq=[1];let peak=1,dd=0;for(const x of xs){eq.push(eq.at(-1)*(1+x/100));peak=Math.max(peak,eq.at(-1));dd=Math.max(dd,(peak-eq.at(-1))/peak*100);}return Object.freeze({n:xs.length,netReturnPct:(eq.at(-1)-1)*100,meanNetReturnPct:mean(xs),winRate:xs.length?xs.filter(x=>x>0).length/xs.length:null,profitFactor:pf(xs),maxDrawdownPct:dd,meanBarsHeld:mean(outcomes.map(x=>x.barsHeld)),meanMfePct:mean(outcomes.map(x=>x.mfePct)),meanMaePct:mean(outcomes.map(x=>x.maePct)),meanGivebackPct:mean(outcomes.map(x=>x.givebackPct)),meanCaptureRatio:mean(outcomes.map(x=>x.captureRatio).filter(finite))});}
export function simulateHoldFirst(row,candidate,{roundTripCostPct=0.05}={}){
 if(!row?.entryAccepted||!finite(row.entryPrice)||!(row.futureBars||[]).length)return null;
 const h=Math.min(Math.max(1,Math.floor(+row.baseHorizonBars||1)),row.futureBars.length),bars=row.futureBars.slice(0,h),a=atrPct(row),d=dir(row);
 let mfe=-Infinity,mae=Infinity,protect=false,deterioration=0,prev=0,exitIndex=h-1,reason='FROZEN_HORIZON';
 for(let i=0;i<bars.length;i++){
  const r=signedRet(row,bars[i]);mfe=Math.max(mfe,r);mae=Math.min(mae,r);
  if(candidate.kind!=='FIXED'){
   const protectTrigger=Math.max(roundTripCostPct,a*0.75);
   if(mfe>=protectTrigger)protect=true;
   const adverseStep=r<prev;
   const structuralAdverse=r<=-candidate.adverseAtr*a;
   const protectedGiveback=protect&&(mfe-r)>=candidate.givebackAtr*a;
   deterioration=(adverseStep&&(structuralAdverse||protectedGiveback))?deterioration+1:0;
   if(deterioration>=candidate.persistenceBars){exitIndex=i;reason=protect?'PERSISTENT_PROTECTED_DETERIORATION':'PERSISTENT_STRUCTURAL_BREAKDOWN';break;}
  }
  prev=r;
 }
 const gross=signedRet(row,bars[exitIndex]),net=gross-roundTripCostPct,giveback=Math.max(0,mfe-gross),capture=mfe>0?gross/mfe:null;
 return Object.freeze({symbol:row.symbol??null,sessionDate:row.sessionDate??null,entryTimestamp:row.entryTimestamp??null,candidateId:candidate.id,exitReason:reason,barsHeld:exitIndex+1,grossReturnPct:gross,netReturnPct:net,mfePct:mfe,maePct:mae,givebackPct:giveback,captureRatio:capture,atrPct:a,direction:d});
}
function evalRows(rows,c){return summary(rows.map(r=>simulateHoldFirst(r,c)).filter(Boolean));}
function uniqueSessions(rows){return [...new Set(rows.map(r=>r.sessionDate).filter(Boolean))].sort();}
function rowsForSessions(rows,sessions){const s=new Set(sessions);return rows.filter(r=>s.has(r.sessionDate));}
function betterThanFixed(a,f){return a.n===f.n&&a.n>0&&a.netReturnPct>f.netReturnPct&&((a.profitFactor??-Infinity)>=(f.profitFactor??-Infinity))&&a.maxDrawdownPct<=Math.max(f.maxDrawdownPct,0)+5;}
export function runHoldExitHistoricalWalkForward(rows=[],options={}){
 const accepted=rows.filter(r=>r?.entryAccepted===true&&r?.pointInTimeValid!==false).slice().sort((a,b)=>String(a.entryTimestamp).localeCompare(String(b.entryTimestamp)));
 const sessions=uniqueSessions(accepted),minTrain=options.minTrainSessions??Math.max(5,Math.floor(sessions.length*0.4)),validationSessions=options.validationSessions??Math.max(2,Math.floor(sessions.length*0.15)),testSessions=options.testSessions??Math.max(2,Math.floor(sessions.length*0.15));
 const folds=[];for(let testStart=minTrain+validationSessions;testStart+testSessions<=sessions.length;testStart+=testSessions){
  const trainEnd=testStart-validationSessions,devS=sessions.slice(0,trainEnd),valS=sessions.slice(trainEnd,testStart),testS=sessions.slice(testStart,testStart+testSessions),dev=rowsForSessions(accepted,devS),val=rowsForSessions(accepted,valS),test=rowsForSessions(accepted,testS);
  const fixed=CANDIDATES[0],devFixed=evalRows(dev,fixed),valFixed=evalRows(val,fixed),testFixed=evalRows(test,fixed);
  const devScores=CANDIDATES.slice(1).map(c=>({candidate:c,summary:evalRows(dev,c)})).filter(x=>betterThanFixed(x.summary,devFixed)).sort((a,b)=>b.summary.netReturnPct-a.summary.netReturnPct);
  let selected=fixed,selectionReason='NO_DEV_CANDIDATE_BEATS_FIXED';
  if(devScores.length){const proposed=devScores[0].candidate,v=evalRows(val,proposed);if(betterThanFixed(v,valFixed)){selected=proposed;selectionReason='DEV_WINNER_PASSED_SEPARATE_VALIDATION';}else selectionReason='DEV_WINNER_FAILED_VALIDATION_FALLBACK_FIXED';}
  const selectedTest=evalRows(test,selected);
  folds.push(Object.freeze({devSessions:devS,validationSessions:valS,testSessions:testS,selectedCandidate:selected.id,selectionReason,devFixed,valFixed,testFixed,selectedTest,testBeatsFixed:betterThanFixed(selectedTest,testFixed)}));
 }
 const outerSelected=[],outerFixed=[];for(const f of folds){outerSelected.push(...rowsForSessions(accepted,f.testSessions).map(r=>simulateHoldFirst(r,CANDIDATES.find(c=>c.id===f.selectedCandidate))).filter(Boolean));outerFixed.push(...rowsForSessions(accepted,f.testSessions).map(r=>simulateHoldFirst(r,CANDIDATES[0])).filter(Boolean));}
 const selectedSummary=summary(outerSelected),fixedSummary=summary(outerFixed),promotionEligible=folds.length>0&&betterThanFixed(selectedSummary,fixedSummary)&&folds.filter(f=>f.testBeatsFixed).length>=Math.ceil(folds.length/2);
 return Object.freeze({phase:'57.r3-r5',status:'HISTORICAL_WALK_FORWARD_RESEARCH',method:'EXPANDING_DEV_SEPARATE_VALIDATION_OUTER_OOS',candidateIds:CANDIDATES.map(c=>c.id),holdIsDefault:true,protectBeforeExit:true,noSameOosThresholdSweep:true,noPostHocSymbolFiltering:true,currentP25EvidenceUsedForTuning:false,freshHoldoutConsumed:false,sessionCount:sessions.length,folds:Object.freeze(folds),outerOos:{fixed:fixedSummary,selected:selectedSummary,foldWins:folds.filter(f=>f.testBeatsFixed).length,foldCount:folds.length,promotionEligible},safety:R3_R5_SAFETY});
}
