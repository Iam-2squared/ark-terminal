"""Frozen pre-entry Potential forensic diagnostic, strictly independent of EXIT."""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score,average_precision_score,brier_score_loss,log_loss

from scripts import phase57_ccmg_layer_a as layer
from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_finite_r36 as r36
from scripts import phase57_entry_all_material_r1_train as frozen
from scripts import phase57_wpsd_phase0 as upstream

OUT=layer.OUT
PREFIT=layer.ROOT/'artifacts/all-material-r1/prefit'
FEATURE_SHA='54bf771f6a090eb3e8035f7ee433ca1fbd617c165d77955ab71054b4e259a3fe'


def read_rows(path):
    with gzip.open(path,'rt') as f:return [json.loads(s) for s in f]


def labels():
    require=layer.require
    frozen_entries=r52.all_frozen_entries()
    raw=r52.projected_raw(frozen_entries)
    primary={(x['arm'],x['entryId']):x for x in read_rows(OUT/'LAYER_A_ENTRY_ROWS.jsonl.gz')}
    require(len(primary)==1614,'PINNED_TEACHER_POPULATION')
    feature_rows=json.loads((PREFIT/'rows.json').read_bytes())
    features={}
    for i,r in enumerate(feature_rows):
        if r['quoteAvailable']:
            key=(r['opportunity'],r['minute'])
            require(key not in features,'FEATURE_DUPLICATE_KEY')
            features[key]=i
    observed=[];mismatches=[];unmapped=[]
    for (arm,eid),e in sorted(frozen_entries.items()):
        pair=(upstream.ARMS[arm],eid)
        idx=features.get((e['opportunity'],e['entryMinute']))
        if idx is None or feature_rows[idx]['computedThroughMinute']>=e['entryMinute']:
            unmapped.append(pair);continue
        high=r36._post_entry_high(e,[raw[e['opportunity']][m] for m in sorted(raw[e['opportunity']])])
        teacher=None if high is None else 100*(high.high/e['effectiveEntryPrice']-1)
        if pair in primary:
            expected=primary[pair]['postEntryUpsidePct']
            if teacher is None or expected is None or abs(teacher-expected)>1e-12:
                mismatches.append({'arm':pair[0],'entryId':eid,'recomputed':teacher,'pinned':expected})
        observed.append({'arm':pair[0],'entryId':eid,'session':e['session'],
            'featureRow':idx,'teacherUpsidePct':teacher,'pinnedTest':pair in primary})
    audit={'schema':'phase57-ccmg-potential-teacher-audit-v1','status':
        'POTENTIAL_LABEL_LINEAGE_PASS' if not mismatches and len(primary)==sum(x['pinnedTest'] for x in observed) and not unmapped else 'POTENTIAL_LABEL_LINEAGE_ABORT',
        'frozenFilledRows':len(frozen_entries),'mappedRows':len(observed),'missingFeatureRows':len(unmapped),
        'missingFeatureExamples':unmapped[:10],'pinnedTestN':len(primary),
        'pinnedExactIdentityN':len(primary)-len(mismatches),'mismatchExamples':mismatches[:10],
        'featureSha256':FEATURE_SHA,'teacher':'r36::_post_entry_high strictly after entry; max High until 930; evaluator only',
        'perArm':{arm:{'available':sum(x['arm']==arm and x['teacherUpsidePct'] is not None for x in observed),
            'test':sum(x['arm']==arm and x['pinnedTest'] for x in observed),
            'positive5':sum(x['arm']==arm and x['pinnedTest'] and x['teacherUpsidePct'] is not None and x['teacherUpsidePct']>=5 for x in observed),
            'positive10':sum(x['arm']==arm and x['pinnedTest'] and x['teacherUpsidePct'] is not None and x['teacherUpsidePct']>=10 for x in observed)} for arm in ('IM','R1')},
        'safety':layer.execution.SAFETY,'providerRequests':0,'restrictedPartitionsOpened':0}
    (OUT/'POTENTIAL_TEACHER_AUDIT.json').write_bytes(layer.encoded(audit))
    (OUT/'POTENTIAL_TEACHER_ROWS.jsonl.gz').write_bytes(gzip.compress(b''.join(layer.encoded(x) for x in observed),mtime=0))
    print(json.dumps({k:audit[k] for k in ('status','frozenFilledRows','mappedRows','missingFeatureRows','pinnedTestN','pinnedExactIdentityN','mismatchExamples','perArm')},indent=2))
    return audit,observed


def score(rows,head):
    yt=np.asarray([x['teacherUpsidePct']>=head for x in rows],dtype=int)
    pred=np.asarray([x[f'probability{head}'] for x in rows])
    base=np.asarray([x[f'baseline{head}'] for x in rows])
    if len(np.unique(yt))!=2:return {'n':len(yt),'positives':int(yt.sum()),'auc':None}
    return {'n':len(yt),'positives':int(yt.sum()),'positiveSessions':len({x['session'] for x in rows if x['teacherUpsidePct']>=head}),
      'prevalence':float(np.mean(yt)),'auc':float(roc_auc_score(yt,pred)),
      'prAuc':float(average_precision_score(yt,pred)),
      'brier':float(brier_score_loss(yt,pred)),'baselineBrier':float(brier_score_loss(yt,base)),
      'logLoss':float(log_loss(yt,pred)),'baselineLogLoss':float(log_loss(yt,base))}


def bootstrap(rows,head):
    sessions=sorted({x['session'] for x in rows})
    by={s:[x for x in rows if x['session']==s] for s in sessions}
    rng=np.random.default_rng(570929+head)
    values=[]
    for _ in range(1999):
        sampled=[x for s in rng.choice(sessions,size=len(sessions)) for x in by[s]]
        y=[int(x['teacherUpsidePct']>=head) for x in sampled]
        if len(set(y))==2:
            values.append(roc_auc_score(y,[x[f'probability{head}'] for x in sampled]))
    return {'resamplesRequested':1999,'valid':len(values),
       'ciLower':None if not values else float(np.quantile(values,.025)),
       'ciUpper':None if not values else float(np.quantile(values,.975))}


def fit(observed):
    layer.require(upstream.digest(PREFIT/'features.npy')==FEATURE_SHA,'FEATURE_ARRAY_DRIFT')
    folds=json.loads((PREFIT/'folds.json').read_bytes())
    layer.require(len(folds)==5,'FOLD_COUNT_DRIFT')
    X=np.load(PREFIT/'features.npy',mmap_mode='r')
    layer.require(X.shape==(149900,566),'FEATURE_DIMENSION_DRIFT')
    # The original 24-session testing cohort is identified by pinned exact IDs;
    # any earlier Development session in the frozen train fold may be used.
    rows=[x.copy() for x in observed if x['teacherUpsidePct'] is not None]
    predicted=[];fits=0;used=[]
    for fold in folds:
        train_sessions=set(fold['train']);test_sessions=set(fold['test'])
        train=[x for x in rows if x['session'] in train_sessions]
        test=[x for x in rows if x['session'] in test_sessions and x['pinnedTest']]
        if not test:continue
        layer.require(train and not train_sessions.intersection(test_sessions),'TEMPORAL_SPLIT_LEAK')
        pp=frozen.fit_preprocessor(np.asarray(X[[x['featureRow'] for x in train]]))
        xt=frozen.transform(np.asarray(X[[x['featureRow'] for x in train]]),pp)
        xv=frozen.transform(np.asarray(X[[x['featureRow'] for x in test]]),pp)
        for head in (5,10):
            y=np.asarray([x['teacherUpsidePct']>=head for x in train],dtype=int)
            layer.require(len(np.unique(y))==2,f'UNTRAINABLE_FOLD:{fold["id"]}:{head}')
            model=LogisticRegression(penalty='l2',C=1.,solver='liblinear',max_iter=1000,
                tol=.0001,class_weight=None,random_state=570926)
            model.fit(xt,y);fits+=1
            probs=model.predict_proba(xv)[:,1]
            baseline=float(np.mean(y))
            for i,x in enumerate(test):
                x[f'probability{head}']=float(probs[i]);x[f'baseline{head}']=baseline
        predicted.extend(test);used.append({'fold':fold['id'],'trainEntries':len(train),
            'testEntries':len(test),'trainLastSession':max(train_sessions),
            'testFirstSession':min(test_sessions),'fitHeads':2})
    predicted.sort(key=lambda x:(x['arm'],x['entryId']))
    layer.require(len(predicted)==1614 and len({(x['arm'],x['entryId']) for x in predicted})==1614,
                  'OOF_TEST_ENTRY_CENSUS')
    raw=b''.join(layer.encoded(x) for x in predicted)
    zipped=gzip.compress(raw,mtime=0)
    prior=OUT/'POTENTIAL_OOF.jsonl.gz'
    layer.require(not prior.exists() or prior.read_bytes()==zipped,'OOF_NOT_REPRODUCIBLE')
    prior.write_bytes(zipped)
    heads={}
    for head in (5,10):
        m=score(predicted,head)
        bs=bootstrap(predicted,head)
        arms={arm:score([x for x in predicted if x['arm']==arm],head) for arm in ('IM','R1')}
        bins=[]
        for start in np.arange(0,1,.1):
            part=[x for x in predicted if start<=x[f'probability{head}']<start+.1 or
                  (start>.89 and x[f'probability{head}']==1)]
            bins.append({'lo':float(start),'hi':min(float(start+.1),1.),'n':len(part),
                'meanPred':None if not part else statistics.mean(x[f'probability{head}'] for x in part),
                'observed':None if not part else statistics.mean(x['teacherUpsidePct']>=head for x in part)})
        contrary=any(x['auc'] is not None and x['auc']<.5 for x in arms.values())
        gate=(bs['ciLower'] is not None and bs['ciLower']>.5 and
             m['brier']<m['baselineBrier'] and m['logLoss']<m['baselineLogLoss'] and not contrary)
        heads[str(head)]={**m,'ci':bs,'perArm':arms,'calibration':bins,
            'armDirectionContradiction':contrary,'status':'POTENTIAL_SKILL_PASS' if gate else 'POTENTIAL_SKILL_FAIL'}
    result={'schema':'phase57-ccmg-potential-result-v1','heads':heads,'folds':used,
        'canonicalOuterFoldCount':5,'outerFitsActual':fits,'outerFitsMaximum':10,
        'innerFits':0,'calibrationRefits':0,'oofRowsSha256':layer.sha(zipped),
        'reproducibility':'BYTE_IDENTICAL_ON_REPEAT_REQUIRED','runtimeAuthority':{
            'holdVeto':False,'sellAuthority':False,'guardOverride':False,
            'capitalSizing':False,'candidateRanking':False},
        'safety':layer.execution.SAFETY,'providerRequests':0,'restrictedPartitionsOpened':0}
    (OUT/'POTENTIAL_RESULT.json').write_bytes(layer.encoded(result))
    print(json.dumps({'heads':{k:{m:x[m] for m in ('n','positives','auc','status')}|{'ci':x['ci']} for k,x in heads.items()},'fits':fits,'oofSha':layer.sha(zipped)},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--teacher-only',action='store_true');args=ap.parse_args()
    audit,rows=labels()
    if audit['status']=='POTENTIAL_LABEL_LINEAGE_PASS' and not args.teacher_only:fit(rows)
