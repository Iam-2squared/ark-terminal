"""R52 Development-only one-step continuation value and fixed-Capital EXIT replay.

Future execution references are isolated in training-label construction and
post-intent historical execution. Allocation only consumes frozen Entry/CI rank.
"""
from __future__ import annotations
import argparse, collections, csv, datetime as dt, gzip, hashlib, json, math, os, statistics, zipfile
from decimal import Decimal
from pathlib import Path
import numpy as np
from scripts import phase57_capital_exit_integrated as integrated
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1
from scripts import phase57_exit_winner_lifecycle_r50 as r50
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_capital_v3 as v3

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/evidence/phase57-exit-continuation-r52'
PRECOMMIT=EVIDENCE/'PRECOMMIT.json'
SUPPORT_ADDENDUM=EVIDENCE/'PREPERFORMANCE_SUPPORT_ADDENDUM.json'
SUPPORT_ADDENDUM_SHA='89b10fc56145bd0eb2821eb7fbc9fc768268df08c4745841b3a82173fd46effb'
RAW=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
GEN3_SHA='d3936171002e7579e431568b9900ee5fa1fc8ade3dae0bf6de92870c8dbe4b38'
FEATURE_SHA='45b91faed0ee7ac3dd46d5fa9bdb4f9f5940cfa2c4a9292af468427d551f5b3e'
IDENTITY_SHA='41d875a3c7d8d8ebcb6fe6ef2022277143b6b34f9ba34c163395f81f2873ac47'
CORE_NUMERIC=('stateDwellObservedActiveMinutes','history.5.stateChanges',
 'history.5.signal.CONTINUATION.true','history.5.signal.BREAKOUT.true',
 'history.5.signal.HIGHER_LOW.true','position.clockMinutesHeld',
 'position.activeMinutesHeld','position.observedOwnedBars','position.missingOwnedBars',
 'position.freshClosedPrice','position.currentReturnPct','calendar.remainingContinuousBars',
 'facts.currentReturnPct','facts.barsHeld','facts.weakRun','facts.signalTrueN',
 'facts.signalFalseN','facts.signalUnknownN','facts.signalLossN',
 'facts.signalRecoveryN','facts.stateRecovery','facts.failedRecovery',
 'facts.momentum5Pct','facts.range5Pct','facts.volume5','facts.higherHigh',
 'facts.higherLow','facts.lowerHigh','facts.lowerLow')
EXTRA_NUMERIC=('position.fullOwnedPrefix','position.observedRunningHigh',
 'position.observedRunningLow','position.observedMfePct','position.observedMaePct',
 'position.completePrefixMfePct','position.completePrefixMaePct',
 'position.observedPeakGivebackPp','position.activeMinutesSincePeakConfirmation',
 'facts.certifiedMfePct','facts.certifiedGivebackPp','facts.timeSincePeak','facts.newPeak')
CATEGORICAL=('entryState.state','currentState.state','entryToCurrentState',
 'signal.CONTINUATION.currentTriState','signal.BREAKOUT.currentTriState',
 'signal.COMPRESSION_EXPANSION.currentTriState','signal.HIGHER_LOW.currentTriState',
 'signal.LOWER_WICK.currentTriState','signal.RECLAIM.currentTriState')
FUTURE_DENY=('futureHigh','futureLow','futureOPEN','terminalOutcome','label','labelAvailability',
 'futureMFE','futureMAE','postEntryUpside','finalPnL','capture','oraclePeak','postExitPath')
CANDIDATES=('R52_CORE_VALUE','R52_PREFIX_PATTERN_VALUE')

def require(ok,msg):v0.require(ok,msg)

def protocol():
    raw=PRECOMMIT.read_bytes();p=json.loads(raw)
    require(hashlib.sha256(raw).hexdigest()==(EVIDENCE/'PRECOMMIT.sha256').read_text().strip(),
            'R52_PRECOMMIT_HASH')
    require(tuple(p['candidateIds'])==CANDIDATES and p['safety']==v0.SAFETY and
            not any(v0.SAFETY.values()),'R52_FINITE_SAFETY')
    for name,expected in p['pins'].items():require(v0.digest(ROOT/name)==expected,'PIN:'+name)
    require(v0.digest(SUPPORT_ADDENDUM)==SUPPORT_ADDENDUM_SHA and
            json.loads(SUPPORT_ADDENDUM.read_text())['basisFrozenProtocolSha256']==v0.digest(PRECOMMIT),
            'SUPPORT_ADDENDUM_IMMUTABLE')
    return p

def load_checkpoints(source):
    p=source/'data';receipt=json.loads((p/'data-receipt.json').read_text())
    require(v0.digest(p/'decision-features.npz')==FEATURE_SHA and
            v0.digest(p/'row-identities.jsonl.gz')==IDENTITY_SHA,'GEN3_SOURCE_PIN')
    with np.load(p/'decision-features.npz',allow_pickle=False) as z:
        arrays={name:z[name] for name in ('numeric','categorical','pattern','fresh')}
    groups=collections.defaultdict(list); identities=[]
    with gzip.open(p/'row-identities.jsonl.gz','rt') as stream:
        for line in stream:
            x=json.loads(line);require(x['index']==len(identities),'CHECKPOINT_ROW_ORDER')
            identities.append(x);groups[(x['arm'],x['entryId'])].append(x['index'])
    require(len(identities)==len(arrays['numeric'])==656247 and
            arrays['pattern'].shape==(len(identities),187),'CHECKPOINT_CENSUS')
    require(tuple(receipt['numericColumns'])[:len(CORE_NUMERIC)]!=CORE_NUMERIC,
            'SANITY_FEATURE_ORDER')
    return receipt,arrays,identities,groups

def all_frozen_entries():
    original=json.loads((ROOT/'docs/evidence/phase57-comprehensive-exit-v1/DEVELOPMENT_INTEGRATED_V0_PRECOMMIT.json').read_text())
    paths={v0.IM:ROOT/'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz',
           v0.R1:ROOT/'docs/evidence/phase57-capital-v3/INPUTS/R1-entry-records.json.gz'}
    result={}
    for arm,path in paths.items():
        expected=original['inputPins']['immediateRecordSha256' if arm==v0.IM else 'r1RecordSha256']
        rows=v0.frozen_entry_projection(path,arm,expected)
        for x in rows:
            if x['entryId']:result[(arm,x['entryId'])]=x
    return result

def projected_raw(entries):
    require(v0.digest(RAW)==v0.RAW_HASH,'RAW_SHA')
    raw,skipped=v0.allowlisted_raw_paths(RAW,{x['opportunity'] for x in entries.values()})
    require(skipped==5375-len(raw),'RAW_ALLOWLIST_SKIP')
    return raw

def fact(arrays,names,i,now):
    col={k:j for j,k in enumerate(names)}
    values={}
    for k in r50.FACTS:
        x=float(arrays['numeric'][i,col['facts.'+k]])
        values[k]=x if math.isfinite(x) else None
    return {'now':now,'maxKnownAt':now,'maxBarEnd':now,'fresh':bool(arrays['fresh'][i]),'values':values}

def geometry(source,out):
    """Check label/execution availability only; no advantage or candidate performance."""
    receipt,arrays,ids,groups=load_checkpoints(source);entries=all_frozen_entries()
    raw=projected_raw(entries)
    p, data, score, model=integrated.load_inputs()
    window=set(p['sessions']);summary=collections.defaultdict(lambda:collections.Counter())
    all_rows=0
    for (arm,eid),seq in groups.items():
        require((arm,eid) in entries,'CHECKPOINT_NOT_FROZEN_ENTRY')
        entry=entries[(arm,eid)];day=entry['session']; bars=raw[entry['opportunity']]
        schedule=execution.continuous_minutes(day); nset={m+1 for m in schedule}
        prior=-1
        for i in seq:
            now=ids[i]['now'];require(now>prior and now in nset,'CHECKPOINT_TIME');prior=now
            if day not in window:continue
            all_rows+=1
            x=fact(arrays,receipt['numericColumns'],i,now)
            core=x['values']['currentReturnPct'] is not None and x['fresh']
            s=execution.next_execution_start(day,now) if now!=925 else None
            key=(arm,'fresh' if core else 'fallback',
                 'complete' if math.isfinite(float(arrays['numeric'][i,receipt['numericColumns'].index('position.fullOwnedPrefix')])) and
                 arrays['numeric'][i,receipt['numericColumns'].index('position.fullOwnedPrefix')]==1 else 'incomplete')
            summary[key]['checkpoints']+=1
            if s is not None and s in bars and core:summary[key]['candidateLabelAnchorPresent']+=1
            if now==925:summary[key]['terminalOnly']+=1
    cohort={arm:sum(e['session'] in window for (a,_),e in entries.items() if a==arm) for arm in v0.ARMS}
    require(all(cohort[a]==len(score[a])==len(model[a]) for a in v0.ARMS),'FULL_24_ENTRY_COVERAGE')
    require(all(len(groups[a,eid])>0 for a in v0.ARMS for eid in score[a]),'ENTRY_CHECKPOINT_COVERAGE')
    result={'schema':'phase57-r52-preperformance-source-geometry-v1','sourceFeatureSha256':FEATURE_SHA,
            'sourceRowIdentitySha256':IDENTITY_SHA,'rowsInWindow':all_rows,'frozenEntries':cohort,
            'sourceGroups':len(groups),'allRows':len(ids),'rowsByArmFreshPrefix':{'|'.join(k):dict(v) for k,v in summary.items()},
            'dataExposure':'outcome-exposed Development','candidatePerformanceRead':False,
            'fits':0,'providerRequests':0,'protectedPartitionsOpened':0,'safety':v0.SAFETY}
    out.write_bytes(v0.canonical(result));return result

def build_labels(receipt,arrays,identities,groups,entries,raw):
    """Training-only action comparison: H starts the frozen R50-A at the NEXT checkpoint.

    Running its state through counterfactual owned paths, including beyond its
    factual exit, makes continuation well-defined without inventing a state.
    """
    col={n:i for i,n in enumerate(receipt['numericColumns'])}
    targets=np.full(len(identities),np.nan,dtype=np.float32)
    reasons=collections.Counter();control_calendar={arm:{} for arm in v0.ARMS}
    for (arm,eid),seq in groups.items():
        entry=entries[(arm,eid)];day=entry['session'];path=raw[entry['opportunity']]
        entry_price=float(entry['effectiveEntryPrice']);state=r50.initial_state()
        resolved=[None]*len(seq)
        for k,i in enumerate(seq):
            now=identities[i]['now']
            values={n:(float(arrays['numeric'][i,col['facts.'+n]]) if math.isfinite(
                    float(arrays['numeric'][i,col['facts.'+n]])) else None) for n in r50.FACTS}
            envelope={'now':now,'maxKnownAt':now,'maxBarEnd':now,
                      'fresh':bool(arrays['fresh'][i]),'values':values}
            decision=r50.intent(envelope,state,'R50_A_LIFECYCLE',terminal=now==925)
            state=decision['state']
            if decision['action']=='EXIT_INTENT':
                ref=execution.ordinary_execution_reference(day,now,[path[t] for t in sorted(path)])
                if ref['status']=='RESOLVED_NEXT_SCHEDULED_OPEN':
                    resolved[k]=(ref['referenceStart'],ref['price'],'MODEL_EXIT')
            elif decision['action']=='FORCE_TERMINAL':
                ref=execution.terminal_execution_reference([path[t] for t in sorted(path)])
                if ref['status']=='RESOLVED_TERMINAL_AUCTION':
                    resolved[k]=(930,ref['price'],'FORCED_TERMINAL')
        next_exit=None
        for k in range(len(seq)-1,-1,-1):
            i=seq[k];now=identities[i]['now'];h=next_exit
            if now==925:reasons['TERMINAL_NOT_A_TRAIN_DECISION']+=1
            elif not arrays['fresh'][i] or not math.isfinite(float(arrays['numeric'][i,col['facts.currentReturnPct']])):
                reasons['MISSING_REQUIRED_NOW']+=1
            else:
                sell_start=execution.next_execution_start(day,now)
                s=path.get(sell_start) if sell_start is not None else None
                if s is None:reasons['MISSING_EXACT_NEXT_OPEN']+=1
                elif h is None:reasons['UNKNOWN_CONTINUATION_EXIT']+=1
                else:
                    # Entry cost and same sell-cost contract cancel symmetrically.
                    targets[i]=100*(float(h[1])-float(s[1]))*(1-.0005)/entry_price
                    reasons['AVAILABLE']+=1
            if resolved[k] is not None:next_exit=resolved[k]
        control_calendar[arm][eid]=next((x for x in resolved if x is not None),None)
    require(sum(reasons.values())==len(identities),'LABEL_CENSUS')
    return targets,reasons,control_calendar

def feature_matrix(receipt,arrays,indices,candidate):
    numeric_names=tuple(receipt['numericColumns']);cat_names=tuple(receipt['categoricalColumns'])
    names=CORE_NUMERIC+(EXTRA_NUMERIC if candidate==CANDIDATES[1] else ())
    require(set(names)<=set(numeric_names) and set(CATEGORICAL)<=set(cat_names),
            'FEATURE_SOURCE_COLUMN_MISSING')
    num=arrays['numeric'][np.ix_(indices,[numeric_names.index(n) for n in names])]
    cat=arrays['categorical'][np.ix_(indices,[cat_names.index(n) for n in CATEGORICAL])]
    blocks=[num,cat.astype(np.float32)]
    if candidate==CANDIDATES[1]:blocks.append(arrays['pattern'][indices])
    result=np.concatenate(blocks,axis=1).astype(np.float32,copy=False)
    require(result.shape[1]==len(names)+len(CATEGORICAL)+(187 if candidate==CANDIDATES[1] else 0),
            'FEATURE_WIDTH')
    return result

def finite_fit(source,out):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    import joblib
    p=protocol();receipt,arrays,identities,groups=load_checkpoints(source)
    entries=all_frozen_entries();raw=projected_raw(entries)
    require(set(groups)<=set(entries),'FROZEN_CHECKPOINT_SCOPE')
    labels,reasons,r50_calendar=build_labels(receipt,arrays,identities,groups,entries,raw)
    sessions=np.asarray([x['session'] for x in identities]);arms=np.asarray([x['arm'] for x in identities])
    eids=np.asarray([x['entryId'] for x in identities]);n=len(identities)
    all_score=set(s for f in p['folds'] for s in f['score'])
    require(set(p['sessions'])<=all_score,'WINDOW_OOF_COVERAGE')
    support=[]
    for fold in p['folds']:
        require(max(fold['train'])<min(fold['purge'])<=max(fold['purge'])<min(fold['score'])
                and not(set(fold['train'])&set(fold['purge'])),'FOLD_PURGE')
        for arm in v0.ARMS:
            train=np.flatnonzero((arms==arm)&np.isin(sessions,fold['train'])&np.isfinite(labels))
            test=np.flatnonzero((arms==arm)&np.isin(sessions,fold['score'])&(np.asarray([x['now'] for x in identities])!=925))
            require(len(train)>=json.loads(SUPPORT_ADDENDUM.read_text())['minMatureLabeledCheckpointsPerTrainArm']
                    and len(test)>0,'TRAIN_SUPPORT_100')
            support.append({'fold':fold['fold'],'arm':arm,'trainRows':len(train),
                'scoreRows':len(test),'trainMax':max(fold['train']),'scoreMin':min(fold['score'])})
    require(len(support)==8,'OOF_SUPPORT_EIGHT_SLICES')
    out.mkdir(parents=True,exist_ok=False)
    (out/'label-support.json').write_bytes(v0.canonical({'reasons':dict(reasons),'folds':support,
                'trainingOnlyLabels':True,'protocolSha256':v0.digest(PRECOMMIT)}))
    preds={c:np.full(n,np.nan,np.float32) for c in CANDIDATES};manifest=[]
    model_dir=out/'models';model_dir.mkdir()
    for fold in p['folds']:
        for arm in v0.ARMS:
            tr=np.flatnonzero((arms==arm)&np.isin(sessions,fold['train'])&np.isfinite(labels))
            te=np.flatnonzero((arms==arm)&np.isin(sessions,fold['score']) &
                              np.asarray([x['now'] for x in identities])!=925)
            # Equal total influence per frozen Entry, independent of path length.
            counts=collections.Counter(eids[tr].tolist())
            weights=np.asarray([1/counts[eids[i]] for i in tr],np.float64)
            weights*=len(tr)/weights.sum()
            for c in CANDIDATES:
                X=feature_matrix(receipt,arrays,tr,c); Z=feature_matrix(receipt,arrays,te,c)
                imputer=SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)
                X=imputer.fit_transform(X);Z=imputer.transform(Z)
                scaler=StandardScaler()
                X=scaler.fit_transform(X);Z=scaler.transform(Z)
                clf=Ridge(**p['model']);clf.fit(X,labels[tr],sample_weight=weights)
                values=clf.predict(Z)
                require(np.all(np.isfinite(values)) and np.all(np.isnan(preds[c][te])),
                        'OOF_PREDICTION_FINITE_UNIQUE')
                preds[c][te]=values.astype(np.float32)
                filename=f"F{fold['fold']}__{'IM' if arm==v0.IM else 'R1'}__{c}.joblib"
                joblib.dump({'model':clf,'imputer':imputer,'scaler':scaler,
                    'features':list(CORE_NUMERIC+(EXTRA_NUMERIC if c==CANDIDATES[1] else ()))+
                     list(CATEGORICAL)+(receipt['patternColumns'] if c==CANDIDATES[1] else [])},
                    model_dir/filename,compress=3)
                manifest.append({'fold':fold['fold'],'arm':arm,'candidate':c,
                    'trainRows':len(tr),'scoreRows':len(te),
                    'trainMax':max(fold['train']),'scoreMin':min(fold['score']),
                    'modelFile':filename,'modelSha256':v0.digest(model_dir/filename),
                    'imputerFits':1,'scalerFits':1,'estimatorFits':1})
                print(v0.canonical({'phase':'FIT_COMPLETED','ordinal':len(manifest),
                       'candidate':c,'arm':arm,'fold':fold['fold']}).decode().strip(),flush=True)
    require(len(manifest)==16,'FINITE_16_ESTIMATOR_FITS')
    for arm in v0.ARMS:
        expected=np.flatnonzero((arms==arm)&np.isin(sessions,p['sessions'])&
                                (np.asarray([x['now'] for x in identities])!=925))
        for c in CANDIDATES:require(np.all(np.isfinite(preds[c][expected])),
                                  'EVALUATION_SCORE_GAP')
    np.savez_compressed(out/'oof-predictions.npz',**preds)
    (out/'fit-manifest.json').write_bytes(v0.canonical(manifest))
    return (receipt,arrays,identities,groups,entries,raw,labels,reasons,
            r50_calendar,preds,manifest)

def action(prediction,fresh,current_return,now,p):
    """Only NOW facts and saved OOF prediction may authorize a sell intent."""
    if now==925:return 'FORCE_TERMINAL','SESSION_END'
    if (not fresh or current_return is None or not math.isfinite(current_return) or
            prediction is None or not math.isfinite(prediction)):
        return 'HOLD','MISSING_REQUIRED_NOW'
    if prediction<p['action']['negativePredictedAdvantageBelowPp']:
        return 'SELL_INTENT','PREDICTED_CONTINUATION_DISADVANTAGE'
    return 'HOLD','PREDICTED_CONTINUATION_OR_UNCERTAINTY'

def exit_calendars(p,receipt,arrays,identities,groups,entries,raw,predictions,source_r50):
    col=receipt['numericColumns'].index('facts.currentReturnPct')
    window=set(p['sessions']);calendars={c:{arm:{} for arm in v0.ARMS} for c in CANDIDATES}
    decision_trace={c:[] for c in CANDIDATES}
    for (arm,eid),seq in groups.items():
        entry=entries[(arm,eid)];day=entry['session']
        if day not in window:continue
        path=raw[entry['opportunity']]
        terminal=execution.terminal_execution_reference([path[t] for t in sorted(path)])
        for candidate in CANDIDATES:
            chosen=None;missing=[]
            for idx in seq:
                now=identities[idx]['now'];z=float(predictions[candidate][idx]);ret=float(arrays['numeric'][idx,col])
                act,reason=action(z if math.isfinite(z) else None,bool(arrays['fresh'][idx]),
                                  ret if math.isfinite(ret) else None,now,p)
                if act=='HOLD':continue
                if act=='FORCE_TERMINAL':
                    chosen={'session':day,'entryId':eid,'decisionNow':now,
                            'exitMinute':930 if terminal['status']=='RESOLVED_TERMINAL_AUCTION' else None,
                            'exitPrice':terminal['price'],'exitKind':'FORCED_TERMINAL',
                            'reason':reason,'predictedAdvantagePp':None}
                    break
                # Historical OPEN is looked up only AFTER a causal SELL_INTENT.
                ref=execution.ordinary_execution_reference(day,now,[path[t] for t in sorted(path)])
                if ref['status']=='RESOLVED_NEXT_SCHEDULED_OPEN':
                    chosen={'session':day,'entryId':eid,'decisionNow':now,
                            'exitMinute':ref['referenceStart'],'exitPrice':ref['price'],
                            'exitKind':'MODEL_EXIT','reason':reason,'predictedAdvantagePp':z}
                    break
                missing.append({'decisionNow':now,'status':ref['status']})
            require(chosen is not None,'NO_TERMINAL_CHECKPOINT')
            calendars[candidate][arm][eid]=chosen
            decision_trace[candidate].append({**chosen,'arm':arm,'missingOrdinaryReferences':missing})
    for arm in v0.ARMS:
        require(len(calendars[CANDIDATES[0]][arm])==len(source_r50[arm]),'EXIT_CALENDAR_SCOPE')
    return calendars,decision_trace

def archive_control(arm):
    name='IM' if arm==v0.IM else 'R1'
    archive=ROOT/'docs/evidence/phase57-capital-exit-integrated/RESULT/phase57-integrated-result.zip'
    with zipfile.ZipFile(archive) as z:
        return json.loads(gzip.decompress(z.read(name+'_V3_B_R50_A_ledger.json.gz')))

def classify(ledger):
    """Replacement requires an earlier confirmed exit in the SAME session."""
    exits=collections.defaultdict(list)
    for x in ledger['closed']:exits[x['session']].append(x['exitTimestamp'])
    return {eid:('Replacement' if any(t<=row['entryTimestamp'] for t in exits[row['session']])
                 else 'Initial') for eid,row in ledger['funded'].items()}

def pnl_delta(control,new):
    old={x['entryId']:Decimal(x['realizedPnlJpy']) for x in control['closed']}
    nxt={x['entryId']:Decimal(x['realizedPnlJpy']) for x in new['closed']}
    common=set(old)&set(nxt);added=set(nxt)-set(old);dropped=set(old)-set(nxt)
    base=sum((nxt[e]-old[e] for e in common),Decimal(0))
    add=sum((nxt[e] for e in added),Decimal(0));minus=-sum((old[e] for e in dropped),Decimal(0))
    expression=base+add+minus
    final_old=control['snapshots'][-1]['equityJpy'];final_new=new['snapshots'][-1]['equityJpy']
    observed=(Decimal(final_new)-Decimal(final_old) if final_old is not None and
              final_new is not None and not control['endOpenEntryIds'] and
              not new['endOpenEntryIds'] else None)
    if observed is not None:require(abs(observed-expression)<Decimal('0.000001'),
                                    'PNL_CURRENCY_IDENTITY')
    return {'commonIds':len(common),'newOnlyIds':sorted(added),'controlOnlyIds':sorted(dropped),
            'commonPnlDeltaJpy':str(base),'newOnlyPnlJpy':str(add),
            'controlOnlyPnlSubtractionJpy':str(minus),'closedPnlDeltaJpy':str(expression),
            'certifiedFinalEquityDeltaJpy':None if observed is None else str(observed),
            'unresolvedDifference':None if observed is not None else 'NO_CERTIFIED_COMPLETE_EQUITY'}

def cohort_buckets(ledger,evaluation,classification,context):
    ids={e for e,kind in classification.items() if context=='Combined' or kind==context}
    sub={'funded':{e:ledger['funded'][e] for e in ids},
         'closed':[r for r in ledger['closed'] if r['entryId'] in ids]}
    return integrated.distribution(sub,evaluation)

def layer_a(control,calendar,evaluation):
    old={x['entryId']:x for x in control['closed']};paired=[]
    for eid,row in sorted(control['funded'].items()):
        candidate=calendar[eid];baseline=old.get(eid)
        net=(None if candidate['exitPrice'] is None else
             Decimal(str(candidate['exitPrice']))*row['quantity']*Decimal('.9995')-
             Decimal(row['notionalJpy']))
        former=Decimal(baseline['realizedPnlJpy']) if baseline else None
        paired.append({'entryId':eid,'quantity':row['quantity'],'entryTimestamp':row['entryTimestamp'],
            'controlExitMinute':None if baseline is None else int(dt.datetime.fromisoformat(baseline['exitTimestamp']).hour*60+
                                                           dt.datetime.fromisoformat(baseline['exitTimestamp']).minute),
            'newExitMinute':candidate['exitMinute'],'controlPnlJpy':None if former is None else str(former),
            'candidatePnlJpy':None if net is None else str(net),
            'sameQuantityPnlDeltaJpy':None if net is None or former is None else str(net-former),
            'evaluatorOnlyUpsidePct':evaluation[eid]['postUpsidePct']})
    return paired

def score(ledger,entry_intents,evaluation,labels,folds,sessions):
    daily,summary=integrated.daily(ledger,sessions)
    attribution=v3.attribute(ledger,entry_intents,evaluation,labels,folds)
    kinds=classify(ledger)
    cohort={k:cohort_buckets(ledger,evaluation,kinds,k) for k in ('Initial','Replacement','Combined')}
    closes={x['entryId']:x for x in ledger['closed']}
    quality={}
    for kind in ('Initial','Replacement','Combined'):
        selected=[e for e,k in kinds.items() if kind=='Combined' or k==kind]
        vals=[evaluation[e]['postUpsidePct'] for e in selected if evaluation[e]['postUpsidePct'] is not None]
        nets=[float(closes[e]['netReturnPct']) for e in selected if e in closes]
        quality[kind]={'n':len(selected),'meanUpsidePct':statistics.fmean(vals) if vals else None,
            'medianUpsidePct':statistics.median(vals) if vals else None,
            'ge3':sum(x>=3 for x in vals),'ge4':sum(x>=4 for x in vals),
            'ge5':sum(x>=5 for x in vals),'ge7_5':sum(x>=7.5 for x in vals),
            'ge10':sum(x>=10 for x in vals),'below1':sum(x<1 for x in vals),
            'realizedNetMeanPct':statistics.fmean(nets) if nets else None,
            'realizedNetMedianPct':statistics.median(nets) if nets else None,
            'realizedPnlJpy':str(sum((Decimal(closes[e]['realizedPnlJpy']) for e in selected if e in closes),Decimal(0)))}
    eod=[Decimal(x['equityJpy']) for x in daily if x['certified']]
    eod_dd=None
    if len(eod)==len(sessions):
        peak=Decimal('1000000');dd=[]
        for x in eod:peak=max(peak,x);dd.append(float(x/peak-1)*100)
        eod_dd=min(dd)
    return {'portfolio':integrated.portfolio_card(ledger,summary),'turnover':integrated.turnover(ledger,sessions),
        'upside':attribution,'daily':daily,'dailySummary':summary,'eodMaxDrawdownPct':eod_dd,
        'quality':quality,'buckets':cohort}

def verdict(p,report):
    base=report['IM']['R50_A_CONTROL'];rules=p['selectionGate'];result={}
    for c in CANDIDATES:
        x=report['IM'][c];b=x['portfolio'];q=x['quality'];rel=q['Replacement']
        target=rules['qualityGuardrails']
        gates={'full24Eod':x['dailySummary']['validSessions']==24,
          'positivePortfolioReturn':b['finalEquityJpy'] is not None and
                                    Decimal(b['finalEquityJpy'])>Decimal('1000000'),
          'controlImprovement':b['finalEquityJpy'] is not None and
                                    Decimal(b['finalEquityJpy'])>Decimal(p['controlExactFinalEquityJpy']),
          'ge5Reach':x['upside']['reach']>=target['IM_ge5_reachMinControl'],
          'ge10Count':q['Combined']['ge10']>=target['IM_ge10_fundedMin'],
          'replacementSupport':rel['n']>=target['IM_replacementMinN'],
          'replacementMedian':rel['medianUpsidePct'] is not None and
                           rel['medianUpsidePct']>=target['IM_replacementMedianUpsideMinPct'],
          'replacementGe5':rel['ge5']>=target['IM_replacementGe5Min']}
        util=x['turnover'];user={'validUtilizationCoverage':util['utilizationCoverage'],
             'timeWeightedUtilization':util['timeWeightedUtilizationValidOnly'],
             'utilizationGe80TimeShare':util['utilizationGe80TimeShareValidOnly'],
             'utilizationTarget':('UNVERIFIED' if util['utilizationCoverage']<.95 else
                  'ATTAINED' if util['timeWeightedUtilizationValidOnly']>=.8 else 'UNMET'),
             'highQualityReplacement':rel['ge5']>=1 and
                                      rel['medianUpsidePct'] is not None and
                                      rel['medianUpsidePct']>=target['IM_replacementMedianUpsideMinPct']}
        result[c]={'passed':all(gates.values()),'gates':gates,'userTarget':user}
    candidates=[c for c in CANDIDATES if result[c]['passed']]
    selection=None
    if candidates:
        key=lambda c:(Decimal(report['IM'][c]['portfolio']['finalEquityJpy']),
                      report['IM'][c]['quality']['Combined']['ge5'])
        top=max(key(c) for c in candidates)
        winners=[c for c in candidates if key(c)==top]
        if len(winners)==1:selection=winners[0]
    return {'status':'SELECT_DEVELOPMENT_ONLY' if selection else 'NO_SELECTION_STOP',
            'selection':selection,'votes':result,'integrity':'SOURCE_PINNED_REPLAY_AB_IDENTICAL',
            'finalExitSelected':False,'productionReady':False}

def save_artifacts(out,p,replays,report,layer_a_rows,traces,selection,fit_manifest):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for (arm,c),ledger in replays.items():
        short='IM' if arm==v0.IM else 'R1';prefix=short+'_'+c
        (out/(prefix+'_ledger.json.gz')).write_bytes(gzip.compress(v0.canonical(ledger),mtime=0))
        curve=v1.curve(ledger)
        (out/(prefix+'_equity.json')).write_bytes(v0.canonical(curve))
        with (out/(prefix+'_equity.csv')).open('w',newline='') as f:
            fields=('timestamp','equityJpy','cashJpy','grossExposureJpy','utilization','drawdownPct','equityValid')
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(curve)
        with (out/(prefix+'_daily.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=('session','cashJpy','equityJpy','certified','dailyReturn'))
            w.writeheader();w.writerows(report[short][c]['daily'])
        (out/(prefix+'_buckets.json')).write_bytes(v0.canonical(report[short][c]['buckets']))
    for (arm,c),rows in layer_a_rows.items():
        (out/(('IM' if arm==v0.IM else 'R1')+'_'+c+'_layerA.json')).write_bytes(v0.canonical(rows))
    for c in CANDIDATES:
        (out/(c+'_decision_trace.json.gz')).write_bytes(gzip.compress(v0.canonical(traces[c]),mtime=0))
    for c in CANDIDATES:
        fig,ax=plt.subplots(figsize=(11,4))
        for arm in v0.ARMS:
            for name in ('R50_A_CONTROL',c):
                curve=v1.curve(replays[arm,name]);xs=[dt.datetime.fromisoformat(z['timestamp']) for z in curve]
                ys=[float(z['equityJpy']) if z['equityJpy'] is not None else math.nan for z in curve]
                ax.plot(xs,ys,label=('IM' if arm==v0.IM else 'R1')+' '+name,linewidth=1)
        ax.set_title('Experimental Development R52 — '+c)
        ax.set_ylabel('Certified as-of equity (JPY); gaps are null')
        ax.grid(alpha=.3);ax.legend(fontsize=7);fig.autofmt_xdate();fig.tight_layout()
        fig.savefig(out/(c+'_asset_curves.png'),dpi=120);plt.close(fig)
    (out/'scorecard.json').write_bytes(v0.canonical(report))
    (out/'selection.json').write_bytes(v0.canonical(selection))
    (out/'manifest.json').write_bytes(v0.canonical({'schema':'phase57-r52-finite-integrated-manifest-v1',
        'executionSha':os.popen('git rev-parse HEAD').read().strip(),
        'protocolSha256':v0.digest(PRECOMMIT),'predictionSha256':v0.digest(out/'oof-predictions.npz'),
        'modelFits':len(fit_manifest),'candidateCount':len(CANDIDATES),'sessions':len(p['sessions']),
        'filesSha256':{q.name:v0.digest(q) for q in sorted(out.iterdir()) if q.is_file() and q.name!='manifest.json'},
        'providerRequests':0,'protectedPartitionsOpened':0,'safety':v0.SAFETY}))

def verify_control_only(out):
    p=protocol(); oldp,data,score,model=integrated.load_inputs()
    _,_,cohort,intents,_,_,raw,_,_,_=data
    for arm in v0.ARMS:
        subset={**cohort,'sessions':p['sessions']};eligible=[x for x in intents[arm] if x['timestamp'][:10] in p['sessions']]
        result=integrated.replay(arm,3,subset,v3.ranked_intents(eligible,score[arm]),raw,model[arm])
        archived=archive_control(arm)
        require(v0.canonical(result)==v0.canonical(archived),'R50_CONTROL_LEDGER_NOT_IDENTICAL')
    out.write_bytes(v0.canonical({'controlByteIdentical':True,'frozenEntryCount':{
        arm:len(score[arm]) for arm in v0.ARMS},'modelFits':0,'candidateReplays':0,
        'providerRequests':0,'protectedPartitionsOpened':0,'safety':v0.SAFETY}))

def finite(source,out):
    p=protocol();receipt,arrays,identities,groups,entries,raw,labels,reasons,r50c,preds,fit_manifest=finite_fit(source,out)
    _,data,capital_scores,r50_saved=integrated.load_inputs()
    # Independently reconstructed R50-A continues through every hypothetical
    # held checkpoint. On the 24-day input it must equal the archived control.
    for arm in v0.ARMS:
        for eid,saved in r50_saved[arm].items():
            computed=r50c[arm][eid]
            require((computed is None and saved['exitPrice'] is None) or
                (computed is not None and computed[0]==saved['exitMinute'] and
                 float(computed[1])==float(saved['exitPrice'])),
                'R50_CAUSAL_RECONSTRUCTION_DIFFERENCE:'+arm+':'+eid)
    calendars,traces=exit_calendars(p,receipt,arrays,identities,groups,entries,raw,preds,r50_saved)
    _,_,cohort,intents,evaluation,terminal,integrated_raw,_,_,available_labels=data
    replays={};ranked={}
    for arm in v0.ARMS:
        base=[x for x in intents[arm] if x['timestamp'][:10] in p['sessions']]
        ranked[arm]=v3.ranked_intents(base,capital_scores[arm])
        subset={**cohort,'sessions':p['sessions']}
        replays[arm,'R50_A_CONTROL']=integrated.replay(arm,3,subset,ranked[arm],integrated_raw,r50_saved[arm])
        require(v0.canonical(replays[arm,'R50_A_CONTROL'])==v0.canonical(archive_control(arm)),
                'ARCHIVED_CONTROL_IDENTITY')
        for c in CANDIDATES:
            a=integrated.replay(arm,3,subset,ranked[arm],integrated_raw,calendars[c][arm])
            b=integrated.replay(arm,3,subset,ranked[arm],integrated_raw,calendars[c][arm])
            require(v0.canonical(a)==v0.canonical(b),'REPLAY_AB_NONIDENTICAL')
            replays[arm,c]=a
    # Evaluator-only data and future High enter exclusively AFTER all replays.
    report={};layer_a_rows={}
    for arm in v0.ARMS:
        short='IM' if arm==v0.IM else 'R1';report[short]={}
        for c in ('R50_A_CONTROL',)+CANDIDATES:
            report[short][c]=score(replays[arm,c],ranked[arm],evaluation[arm],
                                   available_labels[arm],data[0]['split']['folds'],p['sessions'])
            if c!='R50_A_CONTROL':
                report[short][c]['currencyAttributionVsControl']=pnl_delta(
                    replays[arm,'R50_A_CONTROL'],replays[arm,c])
                layer_a_rows[arm,c]=layer_a(replays[arm,'R50_A_CONTROL'],calendars[c][arm],evaluation[arm])
    selection=verdict(p,report)
    save_artifacts(out,p,replays,report,layer_a_rows,traces,selection,fit_manifest)
    print(v0.canonical({'stage':'COMPLETE','selection':selection['status'],
        'im':{c:{'funded':report['IM'][c]['turnover']['fundedEntries'],
                 'finalEquityJpy':report['IM'][c]['portfolio']['finalEquityJpy']} for c in report['IM']},
        'fits':len(fit_manifest)}).decode().strip(),flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['geometry','control','finite'],required=True)
    ap.add_argument('--source',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.mode=='geometry':geometry(a.source,a.out)
    elif a.mode=='control':verify_control_only(a.out)
    else:finite(a.source,a.out)

if __name__=='__main__':main()
