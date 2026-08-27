const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};

export const P25_EXIT_V1_DIAGNOSTIC_POLICY=Object.freeze({
  phase:'57.p25.data-driven-exit.v1.diagnostics',
  diagnosticOnly:true,
  changesDecisionSemantics:false,
  thresholdSearchAllowed:false,
  outcomeTuningAllowed:false,
  promotionAllowed:false,
  purpose:'post-hoc failure-mode classification only; not an input to v1 or v2 policy fitting',
});

function classifyActiveExit(pair){
  const fixed=Number(pair?.fixed?.netReturnPct),data=Number(pair?.dataDriven?.netReturnPct),delta=Number(pair?.deltaNetReturnPct);
  if(![fixed,data,delta].every(Number.isFinite))return 'INVALID_RETURN';
  if(delta===0)return 'ACTIVE_EXIT_EQUAL';
  if(delta>0&&fixed<0)return 'LOSS_RESCUE';
  if(delta>0&&fixed>=0)return 'WIN_IMPROVED';
  if(delta<0&&fixed>0)return 'WIN_TRUNCATED';
  return 'LOSS_WORSENED';
}

export function buildP25ExitV1DiagnosticEvidence(pairs=[]){
  const rows=(Array.isArray(pairs)?pairs:[]).map(pair=>{
    const active=pair?.dataDriven?.exitReason==='DATA_DRIVEN_EXPECTED_VALUE_EXIT';
    const decisions=Array.isArray(pair?.dataDriven?.managementDecisions)?pair.dataDriven.managementDecisions:[];
    const finalDecision=decisions.at(-1)??null;
    return Object.freeze({
      key:String(pair?.key??''),sessionDate:String(pair?.sessionDate??''),symbol:String(pair?.symbol??''),
      activeDataDrivenExit:active,
      class:active?classifyActiveExit(pair):'NO_ACTIVE_EXIT',
      fixedNetReturnPct:finite(pair?.fixed?.netReturnPct)?Number(pair.fixed.netReturnPct):null,
      dataDrivenNetReturnPct:finite(pair?.dataDriven?.netReturnPct)?Number(pair.dataDriven.netReturnPct):null,
      deltaNetReturnPct:finite(pair?.deltaNetReturnPct)?Number(pair.deltaNetReturnPct):null,
      barsHeld:finite(pair?.dataDriven?.barsHeld)?Number(pair.dataDriven.barsHeld):null,
      mfePct:finite(pair?.dataDriven?.mfePct)?Number(pair.dataDriven.mfePct):null,
      maePct:finite(pair?.dataDriven?.maePct)?Number(pair.dataDriven.maePct):null,
      givebackPct:finite(pair?.dataDriven?.givebackPct)?Number(pair.dataDriven.givebackPct):null,
      captureRatio:finite(pair?.dataDriven?.captureRatio)?Number(pair.dataDriven.captureRatio):null,
      finalState:finalDecision?.state??null,
      finalReason:finalDecision?.reason??null,
      bestHorizonBars:finite(finalDecision?.bestHorizonBars)?Number(finalDecision.bestHorizonBars):null,
      bestUpper90Pct:finite(finalDecision?.bestUpper90Pct)?Number(finalDecision.bestUpper90Pct):null,
    });
  });
  const active=rows.filter(x=>x.activeDataDrivenExit),inactive=rows.filter(x=>!x.activeDataDrivenExit);
  const classes={};for(const row of active)classes[row.class]=(classes[row.class]??0)+1;
  const activeDeltas=active.map(x=>x.deltaNetReturnPct).filter(finite).map(Number);
  const nums=(key,src=rows)=>src.map(x=>x[key]).filter(finite).map(Number);
  return Object.freeze({
    phase:P25_EXIT_V1_DIAGNOSTIC_POLICY.phase,
    status:'P25_EXIT_V1_DIAGNOSTIC_EVIDENCE_BUILT',
    methodology:P25_EXIT_V1_DIAGNOSTIC_POLICY,
    counts:Object.freeze({paired:rows.length,activeExit:active.length,noActiveExit:inactive.length,classes:Object.freeze(classes)}),
    activeExitDelta:Object.freeze({meanPct:mean(activeDeltas),medianPct:median(activeDeltas),sumPct:activeDeltas.reduce((s,x)=>s+x,0)}),
    dataDrivenPath:Object.freeze({
      meanBarsHeld:mean(nums('barsHeld')),
      meanMfePct:mean(nums('mfePct')),
      meanMaePct:mean(nums('maePct')),
      meanGivebackPct:mean(nums('givebackPct')),
      meanCaptureRatio:mean(nums('captureRatio')),
    }),
    activeExitPath:Object.freeze({
      meanBarsHeld:mean(nums('barsHeld',active)),
      meanMfePct:mean(nums('mfePct',active)),
      meanMaePct:mean(nums('maePct',active)),
      meanGivebackPct:mean(nums('givebackPct',active)),
      meanCaptureRatio:mean(nums('captureRatio',active)),
    }),
    rows:Object.freeze(rows),
  });
}

export default {buildP25ExitV1DiagnosticEvidence,P25_EXIT_V1_DIAGNOSTIC_POLICY};
