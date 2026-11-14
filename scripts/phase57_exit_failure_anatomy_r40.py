"""Evaluator-only R36 failure anatomy; immutable predictions and ledgers only.

No fitting, policy replay, candidate creation or promotion is performed. The
R35 rows are joined in precisely R36's saved prediction order. Post-EXIT paths
and hypothesis diagnostics are outcome-exposed Development evidence, never
inputs to a decision encoder, selector, capital ranker or candidate gate.
"""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
import multiprocessing
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np

R36_SHA='1c574848c6106d34c1d53e902b339e1be2f43b7b5c615e40a7010c29332d997a'
ARMS=('IMMEDIATE','ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF')
HEADS=('HOLD5','HOLD15','HOLD_TERMINAL')
SIGNALS=('CONTINUATION','BREAKOUT','COMPRESSION_EXPANSION','HIGHER_LOW','LOWER_WICK','RECLAIM')
BUCKETS=('<1%','1-2%','2-3%','3-4%','4-5%','>=5%','NOT_EVALUABLE')
ENDPOINTS=tuple((*range(541,691),*range(751,926)))


def require(ok, reason):
    if not ok: raise ValueError(reason)


def finite(v): return isinstance(v,(int,float,np.integer,np.floating)) and not isinstance(v,(bool,np.bool_)) and math.isfinite(v)
def number(v): return float(v) if finite(v) else None

def summary(values):
    a=np.array([v for v in values if finite(v)],dtype=float)
    if not len(a):return dict(n=0,mean=None,median=None,p05=None,p10=None,p90=None,worst=None)
    return dict(n=len(a),mean=float(a.mean()),median=float(np.median(a)),p05=float(np.percentile(a,5)),p10=float(np.percentile(a,10)),p90=float(np.percentile(a,90)),worst=float(a.min()))


def read_json(path):
    b=path.read_bytes();return json.loads(gzip.decompress(b) if path.suffix=='.gz' else b)


def read_rows(path):
    with gzip.open(path,'rt',encoding='utf8') as f:return [json.loads(line) for line in f]


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def scalar_json(value):
    if isinstance(value,np.generic):return value.item()
    raise TypeError('UNSUPPORTED_JSON_TYPE:'+type(value).__name__)

def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False,default=scalar_json)+'\n').encode()


def write_json(path,value):
    require(not path.exists(),'APPEND_ONLY_OUTPUT_EXISTS');path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def write_rows(path,rows):
    require(not path.exists(),'APPEND_ONLY_OUTPUT_EXISTS');path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f,gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0,compresslevel=6) as gz:
        for row in rows:gz.write(canonical(row))


def bucket(row):
    value=row['metrics'].get('bucket')
    return value if value in BUCKETS[:-1] else 'NOT_EVALUABLE'


def decision_now(row):
    if row['exitKind']=='FORCED_TERMINAL':return 925
    if row['exitKind']=='MODEL_EXIT':return 690 if row['exitMinute']==750 else row['exitMinute']
    return None


def first_true(mask, times):
    found=np.flatnonzero(mask)
    return int(times[found[0]]) if len(found) else None


def prediction_diagnostics(times, pred, fresh, threshold, through):
    eligible=np.asarray(fresh,dtype=bool)&np.isfinite(pred).all(axis=1)
    before=eligible & (times<=through)
    negatives=[first_true(before & (pred[:,i]<0),times) for i in range(3)]
    earliest=min((x for x in negatives if x is not None),default=None)
    all_exit=before & (np.max(pred,axis=1)<=threshold)
    disagreement=before & (np.min(pred,axis=1)<=threshold)&(np.max(pred,axis=1)>threshold)
    n=int(before.sum())
    return {'freshPredictionCheckpoints':n,'firstNegativeByHead':dict(zip(HEADS,negatives)),
        'firstNegativeHeads':[HEADS[i] for i,v in enumerate(negatives) if v is not None and v==earliest],
        'firstAllHeadsExitSide':first_true(all_exit,times),'allHeadsExitSideCheckpoints':int(all_exit.sum()),
        'disagreementCheckpoints':int(disagreement.sum()),'disagreementFraction':float(disagreement.sum()/n) if n else None,
        'negativeFractionByHead':{h:float(np.sum(before & (pred[:,i]<0))/n) if n else None for i,h in enumerate(HEADS)},
        'beforeExitPredictionMean':{h:number(np.mean(pred[before,i])) if n else None for i,h in enumerate(HEADS)}}


def state_transitions(values):
    c=collections.Counter()
    for before,after in zip(values,values[1:]):
        if before!=after:c[before+'→'+after]+=1
    return dict(sorted(c.items()))


def signal_transitions(values):
    # TRUE→UNKNOWN remains explicitly UNKNOWN, never a TRUE→FALSE failure.
    return state_transitions(values)


def active_future_endpoint(exit_minute,horizon):
    if exit_minute is None:return None
    future=[m for m in ENDPOINTS if m>exit_minute]
    return future[horizon-1] if len(future)>=horizon else None


def post_exit_path(times, closes, fresh, exit_minute, exit_price, entry_price, peak):
    if exit_minute is None or exit_price is None:return {'status':'UNRESOLVED_EXIT','returnsPctByActiveHorizon':{str(h):None for h in (5,15,30,60)}}
    by_time={int(t):(number(c) if f else None) for t,c,f in zip(times,closes,fresh)}
    out={}
    for horizon in (5,15,30,60):
        t=active_future_endpoint(exit_minute,horizon);p=by_time.get(t)
        out[str(horizon)]={'targetEndpoint':t,'exactFreshClose':p,'returnFromExitPct':None if p is None else 100*(p/exit_price-1)}
    later=(times>exit_minute)&np.asarray(fresh,dtype=bool)&np.isfinite(closes)
    def crossed(level):
        t=first_true(later & (closes>level),times) if level is not None else None
        return {'firstObservedEndpoint':t,'wallMinutes':None if t is None else t-exit_minute,
            'activeMinutes':None if t is None else sum(exit_minute<m<=t for m in ENDPOINTS)}
    return {'status':'OBSERVED_POST_EXIT_EVALUATOR_ONLY','returnsPctByActiveHorizon':out,
        'recoveryAboveExit':crossed(exit_price),'recoveryAboveEntry':crossed(entry_price),
        'recoveryAboveOwnedObservedPeak':crossed(peak),'observedFreshPostExitCloses':int(later.sum()),
        'recoverySemantics':'FIRST_OBSERVED_CLOSE_STRICTLY_ABOVE; gaps are not interpolated; no claim of first latent crossing'}


class CoreIndex:
    def __init__(self,root,session_names,expected_rows):
        self.columns=read_json(root/'core-a/columns.json')
        self.ni={k:i for i,k in enumerate(self.columns['numeric'])}
        self.ci={k:i for i,k in enumerate(self.columns['categorical'])}
        self.numeric=np.full((expected_rows,len(self.ni)),np.nan,dtype=np.float32)
        self.categorical=np.zeros((expected_rows,len(self.ci)),dtype=np.int16)
        self.categories=[[] for _ in self.ci];maps=[{} for _ in self.ci]
        self.times=np.empty(expected_rows,dtype=np.int16);self.fresh=np.empty(expected_rows,dtype=bool)
        self.groups={};cursor=0
        self.projectionDigest=hashlib.sha256()
        for session in session_names:
            rows=read_rows(root/'core-a/checkpoints'/(session+'.jsonl.gz'))
            rows.sort(key=lambda r:(ARMS.index(r['identity'][0]),r['identity'][1],r['identity'][2]))
            for row in rows:
                arm,eid,now=row['identity'];key=(arm,eid)
                self.groups.setdefault(key,[cursor,cursor])[1]=cursor+1
                self.times[cursor]=now;self.fresh[cursor]=row['fresh']
                self.numeric[cursor]=[np.nan if v is None else v for v in row['numeric']]
                for j,v in enumerate(row['categorical']):
                    if v not in maps[j]:maps[j][v]=len(maps[j]);self.categories[j].append(v)
                    self.categorical[cursor,j]=maps[j][v]
                self.projectionDigest.update(canonical([session,arm,eid,now]))
                cursor+=1
        require(cursor==expected_rows==656247,'CORE_ROWS_OR_JOIN_ORDER')
    def cats(self,key,name):
        lo,hi=self.groups[key];j=self.ci[name];v=self.categories[j]
        return [v[int(c)] for c in self.categorical[lo:hi,j]]
    def nums(self,key,name):
        lo,hi=self.groups[key];return self.numeric[lo:hi,self.ni[name]]
    def snapshot(self,key,idx):
        lo,hi=self.groups[key];absolute=lo+idx
        categorical={name:self.categories[j][int(self.categorical[absolute,j])] for name,j in self.ci.items()}
        numeric={name:number(self.numeric[absolute,j]) for name,j in self.ni.items()}
        return {'now':int(self.times[absolute]),'fresh':bool(self.fresh[absolute]),'categorical':categorical,'numeric':numeric}


def anatomy_row(row, config, core, predicted, target_cache, pattern_cache):
    key=(row['entryArm'],row['entryId']);lo,hi=core.groups[key]
    times=core.times[lo:hi];fresh=core.fresh[lo:hi];now=decision_now(row)
    if now is None:idx=len(times)-1;now=int(times[idx])
    else:
        found=np.flatnonzero(times==now);require(len(found)==1,'EXIT_CHECKPOINT_NOT_UNIQUE');idx=int(found[0])
    snap=core.snapshot(key,idx);nums=snap['numeric'];cats=snap['categorical'];pred=predicted[lo:hi]
    states=core.cats(key,'currentState.state');closes=core.nums(key,'position.lastObservedClose')
    current=nums['position.currentReturnPct'];complete=nums['position.fullOwnedPrefix']==1
    peak=nums['position.observedRunningHigh'];eid_key=(row['opportunity'],now)
    targets=target_cache[eid_key]
    diagnostics=prediction_diagnostics(times,pred,fresh,config['exitThresholdPp'],now)
    at_predictions={h:number(pred[idx,i]) for i,h in enumerate(HEADS)}
    at_targets={h:targets['targetsPp'][h] for h in HEADS}
    all_exit=bool(fresh[idx] and np.isfinite(pred[idx]).all() and max(pred[idx])<=config['exitThresholdPp'])
    actual_max=max((v for v in at_targets.values() if finite(v)),default=None)
    missing_prediction=not bool(np.isfinite(pred).all(axis=1).all())
    raw_core={}
    for offset in (-10,-5,0,5,15,30):
        j=idx+offset
        if 0<=j<len(times):
            window=core.snapshot(key,j)
            raw_core[str(offset)]={'now':window['now'],'fresh':window['fresh'],
                'categorical':{k:v for k,v in window['categorical'].items() if k.startswith('currentState.') or '.currentTriState' in k},
                'numeric':{k:v for k,v in window['numeric'].items() if k in ('position.currentReturnPct','position.observedMfePct','position.observedPeakGivebackPp','stateDwellObservedActiveMinutes','history.10.stateChanges')}}
    post=post_exit_path(times,closes,fresh,row['exitMinute'],row['exitPrice'],row['entryPrice'],peak)
    signals={s:{'current':cats[f'signal.{s}.currentTriState'],
        'observedTrueToFalse':cats[f'signal.{s}.observedTrueToFalseTriState'],
        'beforeTransitions':signal_transitions(core.cats(key,f'signal.{s}.currentTriState')[:idx+1]),
        'afterTransitions':signal_transitions(core.cats(key,f'signal.{s}.currentTriState')[idx:])} for s in SIGNALS}
    at_pattern=pattern_cache[eid_key]
    return {'candidateId':config['candidateId'],'entryArm':row['entryArm'],'entryId':row['entryId'],
        'opportunity':row['opportunity'],'session':row['session'],'symbol':row['opportunity'].split('|')[1],
        'fold':row['fold'],'bucketEvaluatorOnly':bucket(row),'exitKind':row['exitKind'],'exitStatus':row['exitStatus'],
        'entryMinute':row['entryMinute'],'decisionNow':now,'exitMinute':row['exitMinute'],
        'activeMinutesHeld':row['activeMinutesHeld'],'wallMinutesHeld':row['wallMinutesHeld'],
        'netReturnPct':row['netReturnPctBySellCost']['0.05'],'metrics':row['metrics'],
        'earlyExitOpportunityCostPp':row['earlyExitOpportunityCostPp'],
        'currentPnlAtDecisionPct':current,'observedRunningPeak':peak,
        'observedMfePct':nums['position.observedMfePct'],'observedMaePct':nums['position.observedMaePct'],
        'observedPeakGivebackPp':nums['position.observedPeakGivebackPp'],
        'certifiedOwnedGivebackPp':row['metrics']['ownedPeakGivebackPp'],
        'timeSincePeakActiveMinutes':nums['position.activeMinutesSincePeakConfirmation'],
        'entryState':cats['entryState.state'],'currentState':cats['currentState.state'],
        'entryToCurrentState':cats['entryToCurrentState'],'currentStateQuality':cats['currentState.dataQuality'],
        'currentStateConfidence':cats['currentState.confidence'],'stateDwell':nums['stateDwellObservedActiveMinutes'],
        'stateChurn10':nums['history.10.stateChanges'],'beforeStateTransitions':state_transitions(states[:idx+1]),
        'afterStateTransitions':state_transitions(states[idx:]),'signals':signals,
        'missingness':{'freshAtDecision':bool(fresh[idx]),'completeOwnedPrefixAtDecision':complete,
            'missingOwnedBarsAtDecision':nums['position.missingOwnedBars'],
            'preExitMissingFreshCount':int((~fresh[:idx+1]).sum()),'preExitCheckpoints':idx+1,
            'signalUnknownCountAtDecision':sum(v['current']=='UNKNOWN' for v in signals.values()),
            'predictionContainsMissing':missing_prediction},
        'predictionAtDecision':at_predictions,'targetAtDecisionEvaluatorOnly':at_targets,
        'predictionErrorPp':{h:None if at_predictions[h] is None or at_targets[h] is None else at_predictions[h]-at_targets[h] for h in HEADS},
        'allHeadsExitSideAtDecision':all_exit,'actualObservedMaxHoldValueAtDecision':actual_max,
        'falseAllHeadsExitConditionalOnAvailableTargets':None if actual_max is None else bool(all_exit and actual_max>config['exitThresholdPp']),
        'predictionDiagnostics':diagnostics,'postExit':post,
        'patternAtDecisionKey':row['opportunity']+'|'+str(now),
        'patternFamiliesAtDecision':at_pattern['families'],
        'stateSignalWindowsByCheckpointOffset':raw_core,
        'execution':{'missingOrdinaryReferences':row['missingOrdinaryReferences'],
            'decisionToFillWallMinutes':None if row['exitMinute'] is None else row['exitMinute']-now,
            'freshCloseToFillChangePp':None if row['exitPrice'] is None or current is None else 100*(row['exitPrice']/row['entryPrice']-1)-current,
            'lunchBoundary':row['exitMinute']==750 and now==690},
        'timeOfDay':'AM' if now<=690 else 'PM','evaluatorOnly':True}


def group_summary(rows):
    def vals(name):return [r.get(name) for r in rows]
    metrics=('netReturnPct','activeMinutesHeld','wallMinutesHeld','currentPnlAtDecisionPct',
        'observedMfePct','observedMaePct','observedPeakGivebackPp','certifiedOwnedGivebackPp',
        'timeSincePeakActiveMinutes','stateDwell','stateChurn10','earlyExitOpportunityCostPp')
    result={'n':len(rows),'resolvedN':sum(r['exitStatus']=='RESOLVED' for r in rows),
        'metrics':{m:summary(vals(m)) for m in metrics},
        'exitKinds':dict(collections.Counter(r['exitKind'] or 'UNRESOLVED' for r in rows)),
        'entryStates':dict(collections.Counter(vals('entryState'))),'currentStates':dict(collections.Counter(vals('currentState'))),
        'entryToCurrentStates':dict(collections.Counter(vals('entryToCurrentState'))),
        'stateConfidence':dict(collections.Counter(vals('currentStateConfidence'))),
        'stateQuality':dict(collections.Counter(vals('currentStateQuality'))),
        'timeOfDay':dict(collections.Counter(vals('timeOfDay'))),
        'signals':{s:{'current':dict(collections.Counter(r['signals'][s]['current'] for r in rows)),
            'observedTrueToFalse':dict(collections.Counter(r['signals'][s]['observedTrueToFalse'] for r in rows)),
            'beforeTransitions':dict(sum((collections.Counter(r['signals'][s]['beforeTransitions']) for r in rows),collections.Counter())),
            'afterTransitions':dict(sum((collections.Counter(r['signals'][s]['afterTransitions']) for r in rows),collections.Counter()))} for s in SIGNALS},
        'stateTransitionsBefore':dict(sum((collections.Counter(r['beforeStateTransitions']) for r in rows),collections.Counter())),
        'stateTransitionsAfter':dict(sum((collections.Counter(r['afterStateTransitions']) for r in rows),collections.Counter())),
        'missingness':{k:summary([float(r['missingness'][k]) for r in rows]) for k in ('freshAtDecision','completeOwnedPrefixAtDecision','missingOwnedBarsAtDecision','preExitMissingFreshCount','signalUnknownCountAtDecision')},
        'firstNegativeHeads':dict(collections.Counter(h for r in rows for h in r['predictionDiagnostics']['firstNegativeHeads'])),
        'headDisagreementFraction':summary([r['predictionDiagnostics']['disagreementFraction'] for r in rows]),
        'exitConditionalPredictionErrors':{h:summary([r['predictionErrorPp'][h] for r in rows]) for h in HEADS},
        'exitConditionalPredictions':{h:summary([r['predictionAtDecision'][h] for r in rows]) for h in HEADS},
        'exitConditionalTargets':{h:summary([r['targetAtDecisionEvaluatorOnly'][h] for r in rows]) for h in HEADS},
        'falseAllHeadsExitAmongObservedTargets':summary([float(r['falseAllHeadsExitConditionalOnAvailableTargets']) for r in rows if r['falseAllHeadsExitConditionalOnAvailableTargets'] is not None]),
        'postExitReturns':{str(h):summary([r['postExit']['returnsPctByActiveHorizon'][str(h)]['returnFromExitPct'] for r in rows if r['postExit']['status']!='UNRESOLVED_EXIT']) for h in (5,15,30,60)},
        'firstObservedRecoveryAboveExitActiveMinutes':summary([r['postExit']['recoveryAboveExit']['activeMinutes'] for r in rows if r['postExit']['status']!='UNRESOLVED_EXIT']),
        'execution':{k:summary([r['execution'][k] for r in rows]) for k in ('missingOrdinaryReferences','decisionToFillWallMinutes','freshCloseToFillChangePp')},
        'lunchBoundaryExits':sum(r['execution']['lunchBoundary'] for r in rows),
        'bullishPriceStateN':sum(r['currentState'] in ('RISE','REBOUND','SHARP_RISE') for r in rows),
        'qualityOkN':sum(r['currentStateQuality']=='OK' for r in rows),
        'bullishPriceStateAndQualityOkN':sum(r['currentState'] in ('RISE','REBOUND','SHARP_RISE') and r['currentStateQuality']=='OK' for r in rows),
        'anySignalTrueN':sum(any(v['current']=='TRUE' for v in r['signals'].values()) for r in rows),
        'postEntryBestHighStrictlyAfterExitN':sum(r['exitMinute'] is not None and r['metrics'].get('postEntryHighKnownAt') is not None and r['metrics']['postEntryHighKnownAt']>r['exitMinute'] for r in rows)}
    for dim in ('session','symbol'):
        groups=collections.defaultdict(list)
        for r in rows:groups[r[dim]].append(r)
        result[dim+'Groups']={k:{'n':len(v),'netReturnPct':summary([x['netReturnPct'] for x in v])} for k,v in sorted(groups.items())}
    result['completePrefixStrata']={str(flag):{'n':sum(r['missingness']['completeOwnedPrefixAtDecision']==flag for r in rows),
        'netReturnPct':summary([r['netReturnPct'] for r in rows if r['missingness']['completeOwnedPrefixAtDecision']==flag])} for flag in (False,True)}
    result['patternFamiliesAtExit']={name:{metric:summary([r['patternFamiliesAtDecision'][name][metric] for r in rows]) for metric in ('knownFraction','mean','min','max')} for name in sorted({n for r in rows for n in r['patternFamiliesAtDecision']})}
    return result


def paired_summary(rows,b):
    maps={a:{r['opportunity']:r for r in rows if r['entryArm']==a and (b=='ALL' or r['bucketEvaluatorOnly']==b) and r['exitStatus']=='RESOLVED'} for a in ARMS}
    ids=sorted(set(maps[ARMS[0]])&set(maps[ARMS[1]]))
    return {'n':len(ids),'direction':'R1_MINUS_IMMEDIATE','delta':{m:summary([maps[ARMS[1]][k][m]-maps[ARMS[0]][k][m] for k in ids if finite(maps[ARMS[1]][k][m]) and finite(maps[ARMS[0]][k][m])]) for m in ('netReturnPct','activeMinutesHeld','earlyExitOpportunityCostPp','observedPeakGivebackPp')},'opportunityIds':ids}


def pattern_family(name):
    # Canonical registry names are preserved; these are descriptive groups only.
    return name.split('/')[0]


def pattern_record(values):
    groups=collections.defaultdict(list)
    for name,value in values.items():groups[pattern_family(name)].append(value)
    return {'values':values,'families':{k:{'knownFraction':sum(finite(x) for x in v)/len(v),'mean':summary(v)['mean'],
        'min':min((x for x in v if finite(x)),default=None),'max':max((x for x in v if finite(x)),default=None)} for k,v in sorted(groups.items())}}


def hypothesis_report(summaries):
    return {
      'A_labels':{'status':'PARTLY_SUPPORTED_DESIGN_LIMITATION_NOT_CAUSAL_PROOF','evidence':'R36 labels are exact future OPEN minus sell-NOW OPEN at 5/15/terminal. They do not directly label continuation survival or thesis failure. Exit-conditional target/prediction errors are measured. Counterfactual training was not performed.'},
      'B_maxAggregation':{'status':'MECHANISM_VERIFIED_HARM_NOT_IDENTIFIED','evidence':'MAX exits only when all three predicted hold values are <= threshold; by itself it is more HOLD-permissive than MIN/mean. Disagreement and first-all-exit counts are supplied. No aggregation ablation was run.'},
      'C_calibration':{'status':'EXIT_CONDITIONAL_ERROR_MEASURED','evidence':'Predicted versus exact realized targets at saved EXIT checkpoints are reported per head, candidate, arm and bucket. These are selection-conditional diagnostics, not independent calibration or proof of model-family superiority.'},
      'D_stateSignalMisrecognition':{'status':'ASSOCIATION_MEASURED_CAUSATION_UNPROVEN','evidence':'Entry/current State, quality, confidence, transitions, dwell/churn and tri-state Signals are reported; future recovery is evaluator-only. R36 policy does not directly SELL on a State or negative current PnL.'},
      'E_patternInsufficiency':{'status':'NOT_IDENTIFIED','evidence':'Canonical 187 curated feature values are generated at unique saved EXIT checkpoints and grouped by canonical family. Candidate family comparisons are descriptive; additional features/ablations were not evaluated.'},
      'F_missingness':{'status':'EXPOSURE_MEASURED_DOMINANCE_UNPROVEN','evidence':'Fresh close, owned-prefix completeness, signal UNKNOWN and missing reference strata are reported. UNKNOWN is separate from FALSE. Nonrandom missingness prevents causal attribution from these stratified outcomes alone.'},
      'G_executionDelay':{'status':'DIRECT_TIMING_AND_CLOSE_TO_FILL_EFFECT_MEASURED','evidence':'Exact saved fill minus decision timing, missing references, lunch boundaries and close-to-fill change are reported. No alternative execution convention was replayed.'},
      'H_singleScore':{'status':'ARCHITECTURE_HYPOTHESIS_NOT_R36_CAUSAL_PROOF','evidence':'Winner continuation and loss containment share the same three-head exit rule in R36. Different observed error profiles can motivate a precommitted separation; they cannot establish Gen2 performance before its finite test.'}}


_AUX_FROZEN=None
_AUX_RAW=None
_AUX_ORIGINS=None
_AUX_PREVIOUS=None


def _checkpoint_audit(key):
    oid,now=key;frozen=_AUX_FROZEN;path=_AUX_RAW[oid];session=oid.split('|')[0];origin=_AUX_ORIGINS[oid]
    target=frozen.hold_targets(now,frozen.execution.continuous_minutes(session),path['today'])
    values=frozen.feature_contract.pattern_now(day=session,now=now,
        selector_minute=frozen.chart_minute(origin['decisionTimestamp']),selector_origin=origin,
        today_prefix=frozen.r20.closed_prefix(session,now,path['today']),previous_prefix=_AUX_PREVIOUS[oid])['curated']
    require(len(values)==187,'PATTERN_CURATED_COUNT')
    return key,target,pattern_record(values)


def run(root,core_root,corrected,out):
    from scripts import phase57_exit_finite_r36 as frozen
    require(not out.exists(),'APPEND_ONLY_OUTPUT_EXISTS')
    receipt=read_json(root/'receipt.json');selection=read_json(root/'run-a/selection.json')
    require(receipt['status']=='NO_SELECTION_STOP','R36_CLOSURE_REQUIRED')
    require(sha(root/'oof-predictions.npz')==receipt['predictionSha256'],'PREDICTION_HASH')
    audit=read_json(corrected/'audit.json');require(audit['additionalFits']==audit['additionalPolicyReplays']==0,'R38_NOT_EVALUATOR_ONLY')
    require(audit['decisionExecutionAndReturnUnchanged'] is True,'R38_DECISION_DRIFT')
    frozen._verify_r35(core_root)
    for path,expected in ((frozen.RAW_PATHS,frozen.RAW_PATHS_SHA256),(frozen.PATTERN_OPPORTUNITIES,frozen.PATTERN_OPPORTUNITIES_SHA256)):
        require(sha(path)==expected,'PINNED_SOURCE_HASH')
    core=CoreIndex(core_root,frozen.r25.development_sessions(),656247)
    with np.load(root/'oof-predictions.npz') as saved_predictions:
        predictions={sid:saved_predictions[sid] for sid in saved_predictions.files}
    require(len(predictions)==6 and all(predictions[s].shape==(656247,3) for s in predictions),'PREDICTION_SPEC_SHAPE')
    ledgers={c['candidateId']:read_rows(corrected/'run-a/ledgers'/(c['candidateId']+'.jsonl.gz')) for c in selection['candidates']}
    require(len(ledgers)==24,'EXACTLY_24_CANDIDATES')
    # Check repaired ledger changes are confined to the owned giveback field.
    for cid,rows in ledgers.items():
        path=corrected/'run-a/ledgers'/(cid+'.jsonl.gz')
        require(sha(path)==audit['correctedHashes']['ledgers/'+cid+'.jsonl.gz'],'CORRECTED_LEDGER_HASH')
        old=read_rows(root/'run-a/ledgers'/(cid+'.jsonl.gz'));require(len(old)==len(rows),'LEDGER_ROWS_CHANGED')
        for arm in ARMS:
            armrows=[r for r in rows if r['entryArm']==arm]
            require(sum(sum(bucket(r)==b for r in armrows) for b in BUCKETS)==len(armrows),'BUCKET_POPULATION_SUM')
        for a,b in zip(old,rows):
            aa=dict(a,metrics=dict(a['metrics']));aa['metrics']['ownedPeakGivebackPp']=b['metrics']['ownedPeakGivebackPp'];require(aa==b,'NON_OWNED_LEDGER_DRIFT')
    raw=read_json(frozen.RAW_PATHS);origins={r['id']:r['origin'] for r in read_json(frozen.PATTERN_OPPORTUNITIES)}
    keys=sorted({(r['opportunity'],decision_now(r) or 925) for rows in ledgers.values() for r in rows})
    targets={};patterns={};previous={}
    for oid in sorted({oid for oid,now in keys}):
        path=raw[oid]
        previous[oid]=frozen.r20.closed_prefix(path['previousSession'],1440,path['previous']) if path['previousSession'] else ()
    global _AUX_FROZEN,_AUX_RAW,_AUX_ORIGINS,_AUX_PREVIOUS
    _AUX_FROZEN,_AUX_RAW,_AUX_ORIGINS,_AUX_PREVIOUS=frozen,raw,origins,previous
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('fork')) as pool:
        for j,(key,target,pattern) in enumerate(pool.map(_checkpoint_audit,keys,chunksize=32),1):
            targets[key]=target;patterns[key]=pattern
            if j%1000==0:print(json.dumps({'stage':'EXIT_CHECKPOINT_LABEL_PATTERN_AUDIT','done':j,'total':len(keys)}),flush=True)
    out.mkdir(parents=True)
    write_rows(out/'pattern-at-exit-evaluator-only.jsonl.gz',({'opportunity':oid,'now':now,**patterns[(oid,now)],'evaluatorOnly':True} for oid,now in keys))
    summaries=[]
    for candidate in selection['candidates']:
        config=candidate['configuration'];cid=config['candidateId'];spec=frozen.candidate_spec(config)
        rows=[anatomy_row(r,config,core,predictions[spec],targets,patterns) for r in ledgers[cid]]
        write_rows(out/'detail'/(cid+'.jsonl.gz'),rows)
        summary_row={'candidateId':cid,'configuration':config,'predictionSpec':spec,
            'overall':{a:group_summary([r for r in rows if r['entryArm']==a]) for a in ARMS},
            'buckets':{b:{a:group_summary([r for r in rows if r['entryArm']==a and r['bucketEvaluatorOnly']==b]) for a in ARMS} for b in BUCKETS},
            'paired':{b:paired_summary(rows,b) for b in ('ALL',)+BUCKETS},
            'byExitKind':{kind:{a:group_summary([r for r in rows if r['entryArm']==a and r['exitKind']==kind]) for a in ARMS} for kind in ('MODEL_EXIT','FORCED_TERMINAL')},
            'winnerByExitKind':{kind:{a:group_summary([r for r in rows if r['entryArm']==a and r['exitKind']==kind and r['bucketEvaluatorOnly']=='>=5%']) for a in ARMS} for kind in ('MODEL_EXIT','FORCED_TERMINAL')}}
        write_json(out/'candidates'/(cid+'.json'),summary_row);summaries.append(summary_row)
        print(json.dumps({'stage':'CANDIDATE_ANATOMY','candidate':cid,'rows':len(rows)}),flush=True)
    # Full prediction trajectories are available without refitting/replaying:
    # exact group slice + stored NPZ reconstruct all heads at all checkpoints.
    trajectory_rows=[]
    used_keys=sorted({(r['entryArm'],r['entryId']) for rows in ledgers.values() for r in rows})
    for key in used_keys:
        lo,hi=core.groups[key]
        trajectory_rows.append({'entryArm':key[0],'entryId':key[1],'predictionSlice':[lo,hi],
            'now':core.times[lo:hi].tolist(),'fresh':core.fresh[lo:hi].tolist(),
            'heads':list(HEADS),'specs':{sid:[[number(x) for x in v] for v in predictions[sid][lo:hi]] for sid in sorted(predictions)},'evaluatorOnly':True})
    write_rows(out/'full-prediction-trajectories-evaluator-only.jsonl.gz',trajectory_rows)
    report={'schema':'phase57-r40-failure-anatomy-v1','evaluatorOnly':True,
        'sourcePredictionSha256':receipt['predictionSha256'],'r38AuditSha256':sha(corrected/'audit.json'),
        'r35IdentityOrderSha256':core.projectionDigest.hexdigest(),'sourceScriptSha256':sha(Path(__file__)),
        'candidateCount':24,'predictionSpecCount':6,'joinedCheckpoints':656247,'uniqueExitCheckpoints':len(keys),
        'scoredEntryArmGroups':len(used_keys),'newModelFits':0,'newPolicyReplays':0,'newCandidates':0,
        'portfolioReplays':0,'providerRequests':0,'protectedPartitionsOpened':0,'safety':frozen.SAFETY,
        'outcome':'R36_NO_SELECTION_STOP_UNCHANGED','hypotheses':hypothesis_report(summaries),
        'summaryByCandidate':[{'candidateId':s['candidateId'],'configuration':s['configuration'],
            'overall':{a:{k:v for k,v in s['overall'][a].items() if k not in ('sessionGroups','symbolGroups')} for a in ARMS},
            'winnerBucket':{a:{k:v for k,v in s['buckets']['>=5%'][a].items() if k not in ('sessionGroups','symbolGroups')} for a in ARMS},
            'winnerByExitKind':{kind:{a:{k:v for k,v in s['winnerByExitKind'][kind][a].items() if k in ('n','metrics','exitConditionalPredictions','falseAllHeadsExitAmongObservedTargets','postExitReturns','firstObservedRecoveryAboveExitActiveMinutes','bullishPriceStateN','qualityOkN','bullishPriceStateAndQualityOkN','anySignalTrueN','postEntryBestHighStrictlyAfterExitN')} for a in ARMS} for kind in ('MODEL_EXIT','FORCED_TERMINAL')}} for s in summaries],
        'limitations':['All data are outcome-exposed Development. No causal attribution to a feature/model family from descriptive strata.',
            'Pattern family means mix canonical units and are descriptive availability summaries; individual values retain canonical column names.',
            'Post-EXIT horizon prices require exact fresh scheduled continuous endpoint; missing and terminal truncation remain null.',
            'Observed recovery is interval-censored by gaps; future State/Signal snapshots are evaluator-only.',
            'Exit-conditional calibration is selected by the R36 policy and is not an independent holdout calibration estimate.']}
    write_json(out/'summary.json',report)
    write_json(out/'hashes.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    return {k:v for k,v in report.items() if k not in ('summaryByCandidate','hypotheses')}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--core-root',type=Path,required=True);p.add_argument('--corrected',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.root,a.core_root,a.corrected,a.out),sort_keys=True))
