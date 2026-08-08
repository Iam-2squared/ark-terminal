export const PHASE56_4_SAFETY = Object.freeze({
  mode: 'ENTRY_RESEARCH_OOS_READ_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const VALID_STATES = new Set(['WAIT','RESEARCH_CANDIDATE_LONG','RESEARCH_CANDIDATE_SHORT','AVOID_CONFLICT']);
function finite(v){ return Number.isFinite(Number(v)); }
function sortRows(rows=[]){ return [...rows].sort((a,b)=>String(a?.time??a?.timestamp??a?.date??'').localeCompare(String(b?.time??b?.timestamp??b?.date??''))); }
function bucket(rows, foldCount){ const out=[]; const n=Math.max(1,Number(foldCount)||4); for(let i=0;i<n;i++){ const s=Math.floor(rows.length*i/n), e=Math.floor(rows.length*(i+1)/n); const part=rows.slice(s,e); if(part.length) out.push(part); } return out; }
function evaluateFold(rows, horizonBars=3){
  const samples=[];
  for(let i=0;i<rows.length;i++){
    const row=rows[i];
    if(!VALID_STATES.has(row?.state) || !finite(row?.close)) continue;
    const j=i+Math.max(1,Number(horizonBars)||3); if(j>=rows.length || !finite(rows[j]?.close)) continue;
    const r=(Number(rows[j].close)-Number(row.close))/Number(row.close);
    if(row.state==='RESEARCH_CANDIDATE_LONG') samples.push({state:row.state,success:r>0,returnPct:r});
    if(row.state==='RESEARCH_CANDIDATE_SHORT') samples.push({state:row.state,success:r<0,returnPct:-r});
  }
  const count=samples.length, successes=samples.filter(x=>x.success).length;
  const avg=count?samples.reduce((s,x)=>s+x.returnPct,0)/count:null;
  const precision=count?successes/count:null;
  return Object.freeze({count,successes,precision,averageAlignedReturn:avg});
}
export function evaluateEntryResearchOos({rows=[], foldCount=4, minimumSamplesPerFold=5, minimumPassingFolds=3, minimumPrecision=0.55, minimumAverageAlignedReturn=0, horizonBars=3}={}){
  const sorted=sortRows(rows), folds=bucket(sorted,foldCount);
  const foldResults=folds.map((fold,index)=>{ const m=evaluateFold(fold,horizonBars); const usable=m.count>=minimumSamplesPerFold; const passed=usable && m.precision>=minimumPrecision && m.averageAlignedReturn>minimumAverageAlignedReturn; return Object.freeze({fold:index+1,rowCount:fold.length,usable,passed,metrics:m}); });
  const usableFolds=foldResults.filter(x=>x.usable).length;
  const passingFolds=foldResults.filter(x=>x.passed).length;
  const blockers=[];
  if(sorted.length===0) blockers.push('NO_OOS_ROWS');
  if(usableFolds<minimumPassingFolds) blockers.push('INSUFFICIENT_USABLE_FOLDS');
  if(passingFolds<minimumPassingFolds) blockers.push('ENTRY_SIGNAL_STABILITY_NOT_PROVEN');
  return Object.freeze({
    phase:'56.4',
    status:blockers.length?'OBSERVE':'ENTRY_OOS_REVIEW_CANDIDATE',
    rowCount:sorted.length,
    usableFolds, passingFolds,
    foldResults:Object.freeze(foldResults),
    blockers:Object.freeze(blockers),
    reviewOnly:true,
    executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false, rssOrderFunctionAllowed:false,
    liveTradingAllowed:false, paperTradingAllowed:false, automaticPromotionAllowed:false, productionUpdateAllowed:false,
    transmitted:false, humanApprovalRequired:true, safety:PHASE56_4_SAFETY,
  });
}
