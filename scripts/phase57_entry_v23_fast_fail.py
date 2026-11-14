"""Single preregistered Good-reference-trade probability screen; no full Development."""
import collections
import datetime
import operator
import gzip
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

from predict.research import phase57_msh_entry_long_v2_d30 as h
from scripts import phase57_entry_v22_fast_fail as old
from scripts import audit_phase57_msh_entry_v2_1_predevelopment as frozen

np = h.np
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'docs/evidence/phase57-entry-v2-3-fast-fail'
PROTOCOL = 'predict/research/phase57-entry-v2-3-fast-fail-protocol-v1.json'
SHA = 'e6fcff8580b6f7feed165a4a8272519dc5d7a661ec367eaf52961f71c1096f2c'
ORDER = list(h.FEATURE_ORDER)
SOURCES = ['scripts/phase57_entry_v23_fast_fail.py', 'scripts/test_phase57_entry_v23_fast_fail.py']
read, write, file_sha = old.read, old.write, old.sha


def audit():
    if file_sha(PROTOCOL) != SHA:
        raise h.IntegrityError('PROTOCOL_SHA')
    c = read(PROTOCOL)
    for p, expected in c['sourcePins'].items():
        if file_sha(p) != expected:
            raise h.IntegrityError('SOURCE_PIN:'+p)
    if c['features']['order'] != ORDER or any(c['safety'].values()):
        raise h.IntegrityError('FEATURE_SAFETY')
    return c


def good_label(net, strict):
    # Both observed, even when one known condition already fails: no partial-label shortcut.
    if net is None or not strict['labelable']:
        return None
    if (not h.finite(net) or strict.get('barCount') != 6
            or not h.finite(strict.get('trueMaePct')) or strict['trueMaePct'] > 0):
        raise h.IntegrityError('INVALID_JOINT_LABEL')
    return int(net > 0. and max(0., -strict['trueMaePct']) <= 2.)


def sigmoid(z):
    a = np.exp(-np.abs(z))
    return np.where(z >= 0., 1./(1.+a), a/(1.+a))


def fit(rows, labels):
    if sys.version_info[:2] != (3, 12) or np.__version__ != '2.3.5':
        raise h.FitError('PINNED_RUNTIME')
    ordered = sorted(rows, key=h.sort_key)
    if len({r['eventId'] for r in ordered}) != len(ordered):
        raise h.IntegrityError('DUPLICATE_TRAIN')
    for r in ordered:
        h.validate_envelope(r)
        if not r['valid']: raise h.FitError('MANDATORY_INPUT_INVALID')
        y = labels[r['eventId']]
        if y is not None and (type(y) is not int or y not in (0, 1)):
            raise h.IntegrityError('BINARY_LABEL')
    rows = [r for r in ordered if labels[r['eventId']] is not None]
    if len(rows) < 7 or len({r['symbol'] for r in rows}) < 2:
        raise h.FitError('TRAIN_SUPPORT')
    y = np.asarray([labels[r['eventId']] for r in rows], dtype=float)
    if len(set(y.tolist())) != 2: raise h.FitError('BOTH_CLASSES_REQUIRED')
    w = h.symbol_weights(rows); ids = [r['eventId'] for r in rows]
    raw = [r['raw'] for r in rows]
    med = [h.weighted_median([r[j] for r in raw], w, ids) for j in (1, 2)]
    vals = np.asarray([[r[0], r[1] if r[1] is not None else med[0],
                       r[2] if r[2] is not None else med[1]] for r in raw])
    mu = np.sum(w[:,None]*vals, axis=0)
    sd = np.sqrt(np.sum(w[:,None]*(vals-mu)**2, axis=0))
    if np.any(sd <= 0) or not np.all(np.isfinite(sd)): raise h.FitError('RAW_VARIANCE')
    masks = np.asarray([r['missing'] for r in rows], dtype=float)
    X = np.column_stack((np.ones(len(rows)), (vals-mu)/sd, masks))
    penalty = np.diag([0.,1.,1.,1.,1.,1.])
    prior = float(w@y)
    beta = np.asarray([math.log(prior/(1-prior)),0.,0.,0.,0.,0.])
    def objective(b):
        z = X@b
        return float(w@(np.logaddexp(0.,z)-y*z)+.5*b@penalty@b)
    converged = False
    for iteration in range(100):
        p = sigmoid(X@beta)
        grad = X.T@(w*(p-y))+penalty@beta
        if float(np.max(np.abs(grad))) <= 1e-10:
            converged = True; break
        H = X.T@((w*p*(1-p))[:,None]*X)+penalty
        try: delta = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError as exc: raise h.FitError('NEWTON_SOLVER') from exc
        current = objective(beta)
        for j in range(30):
            step = .5**j
            candidate = beta-step*delta
            if objective(candidate) <= current-1e-4*step*float(grad@delta):
                beta = candidate; break
        else: raise h.FitError('NEWTON_LINE_SEARCH')
    if not converged: raise h.FitError('NEWTON_CONVERGENCE')
    masses = collections.defaultdict(float)
    for r, mass in zip(rows,w): masses[r['symbol']] += float(mass)
    a = {'protocolSHA':SHA,'family':'WEIGHTED_L2_LOGISTIC_REGRESSION','featureOrder':ORDER,
         'lambda':1.,'intercept':float(beta[0]),'coefficients':beta[1:].tolist(),
         'medians':med,'means':mu.tolist(),'stds':sd.tolist(),
         'missingSeen':[bool(np.any(masks[:,j])) for j in range(2)],
         'probabilityThreshold':prior,'thresholdMeaning':'training symbol-weighted GOOD base rate',
         'training':{'candidateRows':len(ordered),'labelable':len(rows),'good':int(y.sum()),
             'bad':len(rows)-int(y.sum()),'unlabelable':len(ordered)-len(rows),
             'ids':ids,'sessions':sorted({r['sessionDate'] for r in rows}),
             'symbols':sorted(masses),'largestSymbolWeight':max(masses.values()),
             'weightsSHA':h.digest(list(zip(ids,w.tolist()))),'weightSum':float(w.sum()),
             'missingCounts':masks.sum(axis=0).astype(int).tolist(),
             'bothMissing':int(np.sum(np.all(masks==1,axis=1))),
             'iterations':iteration,'objective':objective(beta),'gradientInf':float(np.max(np.abs(grad)))}}
    a['artifactSHA'] = h.digest(a)
    validate_model(a)
    return a


def validate_model(a):
    copy = dict(a); expected = copy.pop('artifactSHA')
    if h.digest(copy) != expected or a['protocolSHA'] != SHA or a['featureOrder'] != ORDER or a['lambda'] != 1.:
        raise h.IntegrityError('MODEL_IDENTITY')
    if not 0 < a['probabilityThreshold'] < 1:
        raise h.IntegrityError('PRIOR')


def predict(a, rows):
    validate_model(a); out=[]; consumed=set()
    if len({r['eventId'] for r in rows}) != len(rows): raise h.IntegrityError('PREDICT_DUPLICATE')
    for r in sorted(rows,key=h.sort_key):
        h.validate_envelope(r)
        status = 'SCORED' if r['valid'] else 'INVALID_INPUT'
        if any(v and not seen for v,seen in zip(r['missing'],a['missingSeen'])):
            status='UNSUPPORTED_MISSING_STATE'
        p = None
        if status == 'SCORED':
            raw=r['raw']; v=[raw[0],raw[1] if raw[1] is not None else a['medians'][0],raw[2] if raw[2] is not None else a['medians'][1]]
            x=[(z-m)/s for z,m,s in zip(v,a['means'],a['stds'])]+r['missing']
            z=a['intercept']+math.fsum(v*b for v,b in zip(x,a['coefficients']))
            p=float(sigmoid(np.asarray([z]))[0])
        key=(r['symbol'],r['sessionDate'])
        state,reason='UNKNOWN',status
        if key in consumed: state,reason='SKIP_THIS_DECISION','ALREADY_ENTERED'
        elif p is not None:
            state,reason=('ENTER','ABOVE_TRAIN_BASE_RATE') if p>a['probabilityThreshold'] else ('SKIP_THIS_DECISION','NOT_ABOVE_TRAIN_BASE_RATE')
            if state=='ENTER':consumed.add(key)
        out.append({k:r[k] for k in ['eventId','symbol','sessionDate','decisionTimestamp']}|
                   {'status':status,'pGood':p,'baseRate':a['probabilityThreshold'],'state':state,'reason':reason,'missing':r['missing']})
    return out


def discrimination(records):
    rows=[r for r in records if r['pGood'] is not None and r['good'] is not None]
    n=len(rows); positives=sum(r['good'] for r in rows); negatives=n-positives
    auc=ap=None
    if positives and negatives:
        ranks=old.average_ranks([r['pGood'] for r in rows])
        auc=float((sum(v for v,r in zip(ranks,rows) if r['good'])-positives*(positives+1)/2)/(positives*negatives))
        groups=collections.defaultdict(list)
        for r in rows: groups[r['pGood']].append(r['good'])
        tp=seen=0; ap=0.
        for score in sorted(groups,reverse=True):
            ys=groups[score]; hits=sum(ys);tp+=hits;seen+=len(ys);ap+=hits/positives*tp/seen
    by=collections.defaultdict(list)
    for r in rows:by[r['unit']].append(r)
    sums=[]; weighted_prevalences=[]
    for v in by.values():
        w=h.symbol_weights(v); y=np.asarray([r['good'] for r in v]);p=np.asarray([r['pGood'] for r in v]);b=np.asarray([r['baseRate'] for r in v])
        weighted_prevalences.append(float(w@y))
        loss=lambda z:float(w@(-y*np.log(np.clip(z,1e-15,1))-(1-y)*np.log(np.clip(1-z,1e-15,1))))
        sums.append([float(w@((p-y)**2)),float(w@((b-y)**2)),loss(p),loss(b)])
    mean=[statistics.mean(x[i] for x in sums) for i in range(4)] if sums else [None]*4
    chosen=[r for r in rows if r['state']=='ENTER'];goodchosen=sum(r['good'] for r in chosen)
    return {'candidates':len(records),'labelableScored':n,'good':positives,'bad':negatives,
        'prevalence':positives/n if n else None,'weightedPrevalence':statistics.mean(weighted_prevalences) if weighted_prevalences else None,'auc':auc,'averagePrecision':ap,
        'brier':mean[0],'baseRateBrier':mean[1],'brierSkill':1-mean[0]/mean[1] if mean[1] else None,
        'logLoss':mean[2],'baseRateLogLoss':mean[3],'logLossSkill':1-mean[2]/mean[3] if mean[3] else None,
        'selectedLabelable':len(chosen),'precision':goodchosen/len(chosen) if chosen else None,
        'recall':goodchosen/positives if positives else None}


def entry_metrics(rows, baseline=False):
    entered=[r for r in rows if r['v1Anchor']] if baseline else [r for r in rows if r['state']=='ENTER']
    ds=[r['D30'] for r in entered if r['D30'] is not None];ms=[r['MFE'] for r in entered if r['MFE'] is not None]
    n=len(entered);sessions=len({r['sessionDate'] for r in rows})
    return {'enter':n,'enterPerSession':n/sessions if sessions else None,'symbols':len({r['symbol'] for r in entered}),
        'meanD30':statistics.mean(ds) if ds else None,'D30':old.distribution(ds),'MAE':old.distribution([-d for d in ds]),
        'MFE':old.distribution(ms),'tailCounts':{str(k):sum(x>=k for x in ds) for k in (2,5,10)},
        'jointCoverage':sum(r['good'] is not None for r in entered)/n if n else None,'strictCoverage':len(ds)/n if n else None,
        'precision':{str(k):sum(x>=k for x in ms)/len(ms) if ms else None for k in (1,2,3,5)}}


def preservation(rows):
    chosen={(r['symbol'],r['sessionDate']):r for r in rows if r['state']=='ENTER'}
    out={}
    for k in (3,5):
        anchors=[r for r in rows if r['v1Anchor'] and r['MFE'] is not None and r['MFE']>=k]
        hit=unknown=exact=0
        for r in anchors:
            s=chosen.get((r['symbol'],r['sessionDate']))
            if s is None:continue
            exact+=s['eventId']==r['eventId']
            if s['MFE'] is None:unknown+=1
            else:hit+=s['MFE']>=k
        out[str(k)]={'baselineWinners':len(anchors),'hits':hit,'unknown':unknown,'exactAnchorEntries':exact,
                     'lower':hit/len(anchors) if anchors else None,'upper':(hit+unknown)/len(anchors) if anchors else None}
    return out


def summary(rows):
    return {'discrimination':discrimination(rows),'v1':entry_metrics(rows,True),
            'v23':entry_metrics(rows),'preservation':preservation(rows)}


def gates(units, pooled, reduced, c):
    g=[];lim=c['gates']
    def add(name,x,op,bound):
        compare={'>':operator.gt,'>=':operator.ge,'<':operator.lt,'<=':operator.le}[op]
        g.append({'name':name,'value':x,'operator':op,'limit':bound,'status':'INCONCLUSIVE' if x is None else 'PASS' if compare(x,bound) else 'FAIL'})
    for scope,n in [('chronological',4),('symbol',5)]:
        ds=pooled[scope]['discrimination']; vals=[u['summary']['discrimination']['auc'] for u in units if u['scope']==scope]
        add(scope+'PooledAUC',ds['auc'],'>=',.55)
        add(scope+'Direction',sum(x is not None and x>.5 for x in vals) if len(vals)==n and all(x is not None for x in vals) else None,'>=',3)
        add(scope+'BrierSkill',ds['brierSkill'],'>',0.)
        add(scope+'LogLossSkill',ds['logLossSkill'],'>',0.)
    p=pooled['chronological'];a=p['v1'];b=p['v23']
    for k in (3,5):
        v=p['preservation'][str(k)];status='INCONCLUSIVE'
        if v['lower'] is not None:
            status='PASS' if v['lower']>=.9 else 'FAIL' if v['upper']<.9 else 'INCONCLUSIVE'
        g.append({'name':'winnerPreservation'+str(k),'lower':v['lower'],'upper':v['upper'],'limit':.9,'status':status})
    add('throughputRatio',b['enter']/a['enter'] if a['enter'] else None,'>=',.8)
    add('meanD30Ratio',b['meanD30']/a['meanD30'] if a['meanD30'] and b['meanD30'] is not None else None,'<',1.)
    add('ES95Ratio',b['D30']['upperES95']/a['D30']['upperES95'] if a['D30']['upperES95'] and b['D30']['upperES95'] is not None else None,'<=',1.)
    for key in ['jointCoverage','strictCoverage']:
        add(key+'Gap',abs(a[key]-b[key]) if a[key] is not None and b[key] is not None else None,'<=',.05)
    add('top2RemovedAUC',reduced['auc'],'>',.5);add('top2RemovedBrierSkill',reduced['brierSkill'],'>',0.)
    v='KILL' if any(x['status']=='FAIL' for x in g) else 'CONTINUE' if all(x['status']=='PASS' for x in g) else 'INCONCLUSIVE'
    if any(u['status']!='MEASURED' for u in units):v='INCONCLUSIVE'
    return 'MSH_ENTRY_LONG_V2_3_FAST_FAIL_'+v,g


def run():
    c=audit();receipt=read(str((BASE/'prefit.json').relative_to(ROOT)))
    if receipt['status']!='PASS' or receipt['protocolSHA']!=SHA:raise h.IntegrityError('PREFIT')
    if any(file_sha(p)!=receipt['sourcePins'][p] for p in SOURCES):raise h.IntegrityError('PREFIT_CHANGED')
    write(BASE/'run-once.json',{'protocolSHA':SHA,'maximumFits':9})
    frozen.audit()
    rows=old.ndjson(frozen.FEATURES);baseline={r['selectorEventId']:r for r in old.ndjson(frozen.PREDICTIONS)}
    strict={r['selectorEventId']:r for r in read(frozen.LABELS)['events']}
    prior=read('docs/evidence/phase57-entry-v2-2-fast-fail/target-ledger.json.gz');target={r['eventId']:r for r in prior}
    ids={r['selectorEventId'] for r in rows}
    if len(ids)!=3800 or ids!=set(target) or ids!=set(strict) or ids!=set(baseline):raise h.IntegrityError('UNIVERSE')
    inputs={r['selectorEventId']:h.extract_inputs(r) for r in rows}
    labels={eid:good_label(target[eid]['target'],strict[eid]) for eid in ids}
    ledger=[]
    for r in rows:
        eid=r['selectorEventId'];t=target[eid];s=strict[eid]
        reason=[]
        if t['target'] is None:reason.append('EXIT_'+t['exit']['reason'])
        if not s['labelable']:reason.append('D30_'+s['reason'])
        ledger.append({'eventId':eid,'symbol':r['symbol'],'sessionDate':r['sessionDate'],'decisionPrice':r['decisionPrice'],
            'good':labels[eid],'netReferenceReturn':t['target'],'D30':max(0.,-s['trueMaePct']) if s['labelable'] else None,
            'reason':reason,'labelEnd':datetime.datetime.fromtimestamp(max(h.timestamp(t['exit'].get('exitTimestamp') or r['decisionTimestamp']),
                h.timestamp(r['decisionTimestamp'])+1800),datetime.timezone.utc).isoformat()})
    write(BASE/'label-ledger.json.gz',ledger);label_by={r['eventId']:r for r in ledger}
    units=[];models=[];predictions=[]
    plans=[('chrono-'+str(i+1),'chronological',i,None) for i in range(4)]+[('symbol-'+str(g),'symbol',3,g) for g in range(5)]
    for name,scope,i,group in plans:
        training,evaluation=old.partition(rows,c,i,group)
        next_start=min(h.timestamp(r['decisionTimestamp']) for r in evaluation)
        purged=[r['selectorEventId'] for r in training if labels[r['selectorEventId']] is not None and h.timestamp(label_by[r['selectorEventId']]['labelEnd'])>=next_start]
        training=[r for r in training if r['selectorEventId'] not in set(purged)]
        try:
            a=fit([inputs[r['selectorEventId']] for r in training],labels)
            restored=json.loads(h.canonical(a));validate_model(restored)
            if restored!=a:raise h.IntegrityError('SERIALIZATION')
            ps=predict(restored,[inputs[r['selectorEventId']] for r in evaluation])
        except h.FitError as exc:
            units.append({'name':name,'scope':scope,'status':'FIT_SUPPORT_UNKNOWN','reason':str(exc),'summary':summary([])});continue
        for p in ps:
            eid=p['eventId'];s=strict[eid]
            p.update(unit=name,scope=scope,good=labels[eid],netReferenceReturn=target[eid]['target'],
                D30=max(0.,-s['trueMaePct']) if s['labelable'] else None,MFE=s['mfePct'] if s['labelable'] else None,
                v1Anchor=baseline[eid]['state']=='ENTER')
        predictions+=ps;models.append({'unit':name,'model':a})
        sm=summary(ps)
        units.append({'name':name,'scope':scope,'status':'MEASURED','trainingRows':len(training),'evaluationRows':len(evaluation),
            'modelSHA':a['artifactSHA'],'purged':purged,'sessionOverlap':0,'heldSymbolOverlap':0 if group is not None else None,'summary':sm})
        print(json.dumps({'unit':name,'train':len(training),'labelable':a['training']['labelable'],'baseRate':a['probabilityThreshold'],
            'auc':sm['discrimination']['auc'],'enter':sm['v23']['enter']}),flush=True)
    scopes={s:[p for p in predictions if p['scope']==s] for s in ['chronological','symbol']}
    duplicate={s:len(rs)-len({r['eventId'] for r in rs}) for s,rs in scopes.items()}
    if any(duplicate.values()):raise h.IntegrityError('OOF_DUPLICATES')
    pooled={s:summary(rs) for s,rs in scopes.items()}
    counts=collections.Counter(r['symbol'] for r in scopes['chronological'] if r['good']==1)
    top=[s for s,n in sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:2]]
    reduced=discrimination([r for r in scopes['chronological'] if r['symbol'] not in top])
    verdict,gs=gates(units,pooled,reduced,c)
    symbol_labels=collections.defaultdict(lambda:collections.Counter())
    for r in ledger:symbol_labels[r['symbol']]['UNKNOWN' if r['good'] is None else 'GOOD' if r['good'] else 'BAD']+=1
    execution=[]
    for r in ledger:
        if r['symbol'] in ('89180','57590') and r['good']==1:
            execution.append(r|{'referenceExitPrice':r['decisionPrice']*(1+(r['netReferenceReturn']+.05)/100),
                               'fillQualityVerified':False})
    count=collections.Counter('UNKNOWN' if y is None else 'GOOD' if y else 'BAD' for y in labels.values())
    result={'protocolSHA':SHA,'verdict':verdict,'exposure':'HISTORICAL_DEVELOPMENT_OUTCOME_EXPOSED_CONDITIONAL_UNIVERSE',
        'label':c['label'],'featureOrder':ORDER,'coverage':{'candidates':3800,'sessions':76,'dates':[c['universe']['sessions'][0],c['universe']['sessions'][-1]],
            'rawV1Qualified':353,'v1Anchors':277,'jointLabelable':count['GOOD']+count['BAD'],'counts':dict(count),
            'unlabelableReasons':dict(collections.Counter('+'.join(r['reason']) for r in ledger if r['good'] is None))},
        'units':units,'pooled':pooled,'gates':gs,'top2Diagnostic':{'symbols':top,'goodCounts':dict(counts),'removedMetrics':reduced},
        'labelBySymbol':dict(symbol_labels),'executionWarning':{'scope':'supporting89180/57590 only, no rule/model/filter','goodReferenceExamples':execution,'allLabelsAreReferenceNotFillCertified':True},
        'portfolio':c['portfolio'],'integrity':{'sourcePinsVerified':len(c['sourcePins']),'fitAttempts':9,'successfulFits':len(models),
            'predictionRows':len(predictions),'numericPredictions':sum(p['pGood'] is not None for p in predictions),'duplicates':duplicate,
            'priorModelRefits':0,'targetTrials':1,'thresholdSearch':0,'modelSearch':0,'featureChangesAfterFit':0,'gatesChanged':0,
            'newPortfolioRuns':0,'fullDevelopment':0,**c['dataProtection']},'safety':c['safety'],
        'nextAction':'STOP. CONTINUE -> separate v2.3 Pre-Development contract. KILL -> formal A/B/C/D research-exit decision; no v2.4/v2.5 target cycling.'}
    write(BASE/'models.json.gz',models);write(BASE/'predictions.json.gz',predictions);write(BASE/'result.json',result)
    print(json.dumps({'verdict':verdict,'counts':dict(count),'failed':[g['name'] for g in gs if g['status']=='FAIL']}))


if __name__=='__main__':run()
