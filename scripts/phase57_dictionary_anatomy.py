"""Read-only, post-hoc anatomy of frozen Development evidence. No raw/provider access."""
import argparse, collections, csv, gzip, hashlib, json, math
from pathlib import Path
import numpy as np
from scripts import phase57_research_dictionary_v0 as v
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/evidence/phase57-behavior-expansion-v1/measurement'
BASE=ROOT/'docs/evidence/phase57-dictionary-anatomy-v1'
CATEGORIES=['RELIABLE_PARTIAL_GATE_FAILURE','PEER_ADJUSTMENT_LOSS','STRATUM_LOCAL_SIGNAL','RECENT_ONLY_RELIABILITY','PEER_CLUSTER_RELIABILITY','SAMPLE_INSUFFICIENT','TAIL_SESSION_SENSITIVITY','DEFINITION_INSTABILITY','NO_RELIABILITY_DEMONSTRATED','REDUNDANT_RELIABLE_TRAIT']
CHART={
 'Swing':['swing_amplitude','swing_duration','pullback_depth'],
 'Rebound':['selloff_rebound'], 'Giveback':['rally_giveback'],
 'VWAP':['vwap_reclaim'], 'Breakout':['pdh_break','or_break','or_follow','or_fail'],
 'Reclaim':['pdl_reclaim','vwap_reclaim'],
 'Wick':['upper_wick','lower_wick','long_upper','long_lower'],
 'Compression':['range_con','range_exp','range_s'],
 'S/R':['pdh_break','pdl_reclaim','or_break','or_fail'],
 'Volume confirmation':['value_rvol','value_shock','value_O30','value_AM','value_PM1','volume_O30','volume_AM','volume_PM1']}
def read(p):
 with (gzip.open(p,'rt') if str(p).endswith('.gz') else open(p)) as f:return json.load(f)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(v.clean(obj),ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def stats(a):
 a=np.asarray([np.nan if x is None else x for x in a],float);a=a[np.isfinite(a)]
 return {'n':len(a),'min':float(a.min()) if len(a) else None,'p10':float(np.quantile(a,.1)) if len(a) else None,'median':float(np.median(a)) if len(a) else None,'p90':float(np.quantile(a,.9)) if len(a) else None,'max':float(a.max()) if len(a) else None}
def classify(r,lane):
 c={k:{'status':'NOT_ESTABLISHED','basis':None} for k in CATEGORIES};checks=r.get('checks',{});reasons=r['reasons']
 def put(k,s,b):c[k]={'status':s,'basis':b}
 if checks.get('raw') and checks.get('incremental') and r['status']=='WATCH':put('RELIABLE_PARTIAL_GATE_FAILURE','CONFIRMED','Raw and incremental thresholds passed; remaining failures: '+','.join(reasons))
 if checks.get('raw') and not checks.get('incremental'):put('PEER_ADJUSTMENT_LOSS','CONFIRMED','Raw threshold passed, joint peer-adjusted incremental threshold failed; cannot attribute loss to individual covariate')
 strata=r.get('liquidityStrata',[])
 if strata and 0<sum(s['pass'] for s in strata)<3:put('STRATUM_LOCAL_SIGNAL','INDICATION','Positive point correlation in only some liquidity tertiles; no per-stratum CI/FDR; price/volatility strata unavailable')
 for k in ['RECENT_ONLY_RELIABILITY','PEER_CLUSTER_RELIABILITY']:put(k,'UNKNOWN','Saved window estimates / A-only peer fits are not independent validation; no temporal cluster assessment')
 if r['status']=='INSUFFICIENT':put('SAMPLE_INSUFFICIENT','CONFIRMED','Fewer than 100 paired eligible symbols; '+('intraday data absent by lane design' if lane=='daily' and r['tier']=='intraday' else 'inspect saved per-symbol sessions/nEff; no threshold relaxation'))
 if checks and not checks.get('tail'):put('TAIL_SESSION_SENSITIVITY','INDICATION' if not (checks.get('raw') and checks.get('incremental')) else 'CONFIRMED','Tail exclusion failed thresholds; when full-sample thresholds already fail this does not establish tail causation')
 if not checks.get('raw',True) and not checks.get('incremental',True):put('NO_RELIABILITY_DEMONSTRATED','CONFIRMED','Neither fixed raw nor incremental threshold passed; not proof that all conditional signal is absent')
 if any(x.startswith('REDUNDANT_WITH:') for x in reasons):put('REDUNDANT_RELIABLE_TRAIT','CONFIRMED','All statistical gates passed; fixed registry-order deduplication only')
 if r['id']=='pullback_depth':put('DEFINITION_INSTABILITY','CONFIRMED','Code averages all consecutive confirmed swing ratios, including upward/downward and cross-phase adjacent swings; LONG correction semantics are not enforced')
 elif r['id'] in ['value_CL','volume_CL','range_CL','hod_CL','lod_CL']:put('DEFINITION_INSTABILITY','INDICATION','Closing bucket unavailable before 2024-11-05 calendar change; structural availability shift, not proven coding error')
 return c

def window_summary(w):
 return {'window':w['window'],'windowStart':w['windowStart'],'computed_through':w['computed_through'],'eligibleSymbols':w['status'].count('ELIGIBLE'),'totalSymbols':len(w['status']),'nEffAll':stats(w['nEff']),'sessionsAll':stats(w['n_sessions']),'coverageAll':stats(w['coverage']),'posteriorSD':stats(w.get('posterior_sd',[])),'driftFlagTrue':sum(x is True for x in w['drift']['driftFlag']),'driftTested':sum(x is not None for x in w['drift']['driftFlag']),'recentReliability':'NOT_MEASURED','episodesUnit':'nonmissing symbol-session summaries, not individual intraday swings' if w.get('episodes') is not None else 'N/A','statusSemantics':'ELIGIBLE is sufficient observations, not symbol-specific USABLE','windowSemantics':'last N positions in calendar grid; may contain excluded sessions; not N observed sessions'}

def run(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 registry=read(ROOT/'docs/evidence/phase57-research-dictionary-v0/registry.json');catalog={x['id']:x for x in registry['catalog']}
 manifest=read(SOURCE/'manifest.json');before={k:sha(SOURCE/k) for k in manifest};assert before==manifest,'SOURCE_HASH_MISMATCH'
 allrows=[];sparse={};window_diagnostics=[];lane_summary={};source_summary=read(SOURCE/'summary.json')
 for lane in ['daily','intraday']:
  results=read(SOURCE/(lane+'-reliability.json'));profiles=read(SOURCE/(lane+'-profiles.json.gz'));windows=read(SOURCE/(lane+'-windows.json.gz'))
  ps={x['id']:x for x in profiles['profiles']};ws={(x['trait'],x['window']):x for x in windows['profiles']};assert len(results)==73
  eligible_by_window={w:[[] for _ in windows['codeJoinKeys']] for w in [20,60,250]}
  for r in results:
   p=ps[r['id']];row={'lane':lane,**r,'definition':catalog[r['id']]['definition'],'classifications':classify(r,lane),'sampleDiagnostics':{'allSymbols':len(p['allSymbolStatus']),'eligiblePaired':p['allSymbolStatus'].count('ELIGIBLE'),'A_sessions':stats(p['allSymbolNSessionsA']),'B_sessions':stats(p['allSymbolNSessionsB']),'A_nEff':stats(p['allSymbolNEffA']),'B_nEff':stats(p['allSymbolNEffB']),'observationUnit':'one symbol-session summary; conditional session count not intraday episode count','pairedMinimumPerHalf':8 if r['id'] in v.CONDITIONAL else 20,'eligibleSessionMinimumPerHalf':20,'pairedSymbolMinimum':100},'windows':[window_summary(ws[r['id'],w]) for w in [20,60,250]],'evidence':{'gate':str((SOURCE/(lane+'-reliability.json')).relative_to(ROOT)),'profiles':str((SOURCE/(lane+'-profiles.json.gz')).relative_to(ROOT)),'windows':str((SOURCE/(lane+'-windows.json.gz')).relative_to(ROOT))}}
   if 'peerPredictionA' in p:
    row['peerDiagnostic']={'A_fitCrossSectionCorrelation':v.spearman(np.array(p['transformedA']),np.array(p['peerPredictionA'])),'interpretation':'In-sample explanatory association only; no independent peer or cluster reliability claim','covariates':['logVa','logS','logPrice','coverage'],'covariateAblations':'NOT_SAVED','priceVolatilityStrata':'NOT_SAVED'}
   for window in [20,60,250]:
    w=ws[r['id'],window]
    if r['status']=='USABLE':
     for i,s in enumerate(w['status']):
      if s=='ELIGIBLE':eligible_by_window[window][i].append(r['id'])
   a=ws[r['id'],20];b=ws[r['id'],250]
   row['overlappingWindowDiagnostic']={'rawRank20vs250':v.spearman(np.asarray(a['transformed'],float),np.asarray(b['transformed'],float)),'interpretation':'Overlapping endpoint snapshots, descriptive only; not recent-window replication'}
   allrows.append(row)
  sparse[lane]={str(w):{'symbols':len(lists),'nonemptySymbols':sum(bool(x) for x in lists),'traitCountDistribution':dict(sorted(collections.Counter(map(len,lists)).items())),'traitSetDistribution':[{'traits':list(k),'symbols':n} for k,n in sorted(collections.Counter(tuple(x) for x in lists).items())],'symbolSpecificReliabilityCertified':False,'productionAllowed':False} for w,lists in eligible_by_window.items()}
  reasons=collections.Counter(x for r in results for x in r['reasons']);gate=source_summary['lanes'][lane]['gate']
  lane_summary[lane]={'statusCounts':dict(collections.Counter(r['status'] for r in results)),'failureReasonCounts':dict(sorted(reasons.items())),'watchOnlyCalibration':[r['id'] for r in results if r['reasons']==['calibration']],'watchOnlyRedundancy':[r['id'] for r in results if r['reasons'] and all(x.startswith('REDUNDANT_WITH:') for x in r['reasons'])],'completion':{'usable':{'actual':gate['usable'],'required':8},'families':{'actual':len(gate['families']),'required':4,'names':gate['families']},'daily':{'actual':gate['daily'],'required':2},'intraday':{'actual':gate['intraday'],'required':2}},'note':'Population-level diverse-trait completion, not a minimum trait count for every symbol. Daily-only lane cannot satisfy intraday minimum by design; operational expansion completion follows intraday gate.'}
  del profiles,windows,ps,ws
 assert len(allrows)==146 and sum(r['status']=='WATCH' for r in allrows)==92
 chart={family:{'traits':[{'lane':r['lane'],'id':r['id'],'status':r['status'],'reasons':r['reasons'],'raw':r.get('rawSplitHalf'),'incremental':r.get('incremental'),'calibrationSlope':r.get('calibrationSlope'),'ci':r.get('ci'),'pairedSymbols':r['pairedSymbols']} for r in allrows if r['id'] in names],'limitations':{'Compression':'range_con is daily range contraction, not a separately validated causal intraday compression trait','S/R':'Only PDH/PDL/OR proxies; generalized support/resistance touches have no scalar reliability gate','Volume confirmation':'volume/value bucket shares are not breakout volume confirmation; break_value and gap_down_value are descriptive composites without scalar Gate','Swing':'Mean swing summaries and all-direction ratios are not an already validated LONG pullback personality'}.get(family,'Historical full-session trait cannot be used as current-session predictor before its outcomes mature')} for family,names in CHART.items()}
 by_status={s:{lane:{cat:dict(collections.Counter(r['classifications'][cat]['status'] for r in allrows if r['lane']==lane and r['status']==s)) for cat in CATEGORIES} for lane in ['daily','intraday']} for s in ['USABLE','WATCH','INSUFFICIENT']}
 write(out/'01_source_integrity.json',{'sourceHead':'573a0bfebf87319cdc07f93ee6db533f74457c69','hashes':before,'registryHash':sha(ROOT/'docs/evidence/phase57-research-dictionary-v0/registry.json'),'newProtectedPayloadReads':0,'priorExposureIncidentPreserved':True,'newProviderRequests':0,'rawRemeasurements':0,'newPrimaryTests':0})
 write(out/'02_all_traits.json',allrows);write(out/'03_watch_92.json',[r for r in allrows if r['status']=='WATCH']);write(out/'04_classification_counts.json',by_status);write(out/'05_completion.json',lane_summary);write(out/'06_chart_traits.json',chart);write(out/'07_sparse_availability.json',sparse)
 with (out/'08_trait_gate_matrix.csv').open('w',newline='') as f:
  writer=csv.writer(f);writer.writerow(['lane','trait','tier','status','pairedSymbols','raw','incremental','CI_low','CI_high','q','calibration','tailRaw','tailIncremental','failedGates','diagnosticCategories'])
  for r in allrows:writer.writerow([r['lane'],r['id'],r['tier'],r['status'],r['pairedSymbols'],r.get('rawSplitHalf'),r.get('incremental'),*r.get('ci',[None,None]),r['q'],r.get('calibrationSlope'),r.get('tailRaw'),r.get('tailIncremental'),'|'.join(r['reasons']),'|'.join(k+':'+x['status'] for k,x in r['classifications'].items())])
 write(out/'09_decision.json',{'originalCompletion':'FAIL_UNCHANGED','sparseRepresentation':'FEASIBLE_RESEARCH_AVAILABILITY_VIEW','sparsePracticalPersonality':'NOT_ESTABLISHED_PER_SYMBOL_OR_CLUSTER','chartSignal':'pdh_break passes intraday fixed Gate; other chart traits have partial evidence or missing samples; not Entry profitability','newRegistry':'REQUIRED_FOR_CONFIRMED_PULLBACK_SEMANTIC_CORRECTION_IF_PURSUED; NOT_CREATED_OR_REMEASURED','chartReader':'NOT_READY_SCHEMA_AND_STALENESS_BLOCKERS','dictionaryReaderReadyForEntryExit':False,'newEntryExitStarted':False,'nextStep':'Separate finite definition/Reader correction precommit; keep v0 and its Gates unchanged; no holdout opening','holdoutPayloadReads':0,'productionAllowed':False})
 assert before=={k:sha(SOURCE/k) for k in manifest},'SOURCE_CHANGED'
 write(out/'manifest.json',{p.name:sha(p) for p in sorted(out.iterdir())})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();run(a.output)
