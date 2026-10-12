"""One immutable integrated LONG Entry measurement; TRAIN fit, Validation once.

Policy accepts PIT-only state records. Label/economic evaluators are separate.
No DEV TEST route, no research-data refit in audit or CI.
"""
import argparse
import collections
import copy
import json
import math
import platform
from pathlib import Path
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from scripts import phase57_comprehensive_entry_v3 as v3

v2=v3.v2
m,c,q=v3.m,v3.c,v3.q
ROOT=m.ROOT
BASE=ROOT/'docs/evidence/phase57-integrated-long-entry-v1'
PROTOCOL_COMMIT='b20aec53bb318e1db119758b018b8c4f8bc0b128'
PROTOCOL_SHA='93dab410a6116d52bc70489a1322bcc16e041c43591e6a94bf7eba4d96ef004c'
FEATURES=m.FEATURES+['state_'+k for k in v3.protocol_descriptor_names()]
OUTPUTS=['urgent','viable','failure']


def protocol():
    assert m.sha(BASE/'protocol.json')==PROTOCOL_SHA,'PROTOCOL_MUTATED'
    p=m.read(BASE/'protocol.json')
    for f,h in p['sourcePins'].items(): assert m.sha(ROOT/f)==h,f
    assert m.sha(BASE/'feature-manifest.json')==p['featureManifestSHA256']
    assert m.read(BASE/'feature-manifest.json')['modelFeatures']==FEATURES
    for f,h in p['instructionSHA256'].items(): assert m.sha(BASE/f)==h
    assert len(p['safety'])==9 and all(x is False for x in p['safety'].values())
    return p


def sources(partition):
    if partition not in ('TRAIN','VALIDATION'): raise RuntimeError('SEALED_PARTITION')
    p=protocol();old,ops,paths,selectors,legacy=v2.sources()
    assert p['split']==old['split']
    assert len(ops)==3508
    for k,ds in p['split'].items(): assert sum(x['session'] in ds for x in ops)==p['population'][k]
    ops=[x for x in ops if x['session'] in p['split'][partition]]
    ids={x['op']['anchorId'] for x in ops}
    return p,ops,{k:paths[k] for k in ids},{k:selectors[k] for k in ids},{k:legacy[k] for k in ids if k in legacy}


def states(x,path,selector,legacy):
    """Project each decision timestamp, no evaluator fields or forward extrema."""
    op=x['op'];start=c.minute(op['opportunityTimestamp']);bound=c.segment_end(start,path['sessionEndMinute'])
    price=op.get('referencePrice');terminal=None;out=[]
    if op.get('referenceStatus')!='REFERENCE_OPEN' or isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or price<=0:terminal='EXPIRE_REFERENCE'
    for d in (0,5,10,15):
        t=start+d
        if terminal is None and (bound is None or t>=bound):terminal='EXPIRE_BOUNDARY'
        f=v2.state(x,path,selector,legacy,t) if terminal is None else None
        if terminal is None and f is None:terminal='EXPIRE_MISSING_PREFIX'
        row={'timestamp':c.stamp(x['session'],t),'delay':d,'status':terminal or 'AVAILABLE'}
        if terminal is None:
            bars=[b for b in path['future'] if c.minute(b['start'])>=start and c.minute(b['end'])<=t]
            assert len(bars)==d//5
            bs=v3.normalized(bars,path,price);desc=v3.describe(bs)
            row.update(features={**f,**{'state_'+k:desc[k] for k in v3.protocol_descriptor_names()}},
                descriptors=desc,pullbackSeen=any(b['c']<0 for b in bs),
                canWait=d<15 and t+5<bound,newestCompletedEnd=bars[-1]['end'] if bars else None,
                intrabarOrder='UNKNOWN_INTRABAR_ORDER')
        out.append(row)
    return out


def training_dataset(ops,paths,selectors,legacy):
    pit=[];labels=[]
    for x in ops:
        aid=x['op']['anchorId'];path=paths[aid];ss=states(x,path,selectors[aid],legacy.get(aid,{}))
        pit.append({'id':x['id'],'session':x['session'],'source':x['op']['eventType'],'states':ss})
        baseline=v2.evaluate(x,path,0)
        if not baseline or not baseline['commonComplete']:continue
        cls=m.path_class(x,path);group=[]
        for s in ss:
            if s['status']!='AVAILABLE':break
            e=v2.evaluate(x,path,s['delay'])
            if e is None or not e['commonComplete']:continue
            group.append({'id':x['id'],'session':x['session'],'delay':s['delay'],
                'targets':[int(e['fastWinner'] or (s['delay']==0 and cls=='IMMEDIATE_WINNER')),
                    int(e['common']['mfe']>=3),int(e['common']['return']<0 and e['common']['mae']<=-3)]})
        for r in group:r['weight']=1/len(group);labels.append(r)
    return pit,labels


def join_training(pit,labels):
    index={(r['id'],s['delay']):s['features'] for r in pit for s in r['states'] if s['status']=='AVAILABLE'}
    return [index[(r['id'],r['delay'])] for r in labels]


class Model:
    def __init__(self,artifact):self.artifact=artifact
    @staticmethod
    def fit_once(fs,labels,p):
        a=m.matrix(fs,FEATURES)
        med=np.array([np.median(z[np.isfinite(z)]) if np.isfinite(z).any() else 0. for z in a.T])
        z=np.concatenate([np.where(np.isfinite(a),a,med),~np.isfinite(a)],axis=1)
        model=DecisionTreeRegressor(**p['architecture']['hyperparameters'])
        model.fit(z,np.array([r['targets'] for r in labels]),sample_weight=[r['weight'] for r in labels])
        t=model.tree_
        artifact={'kind':p['architecture']['id'],'features':FEATURES,'outputs':OUTPUTS,'hyperparameters':p['architecture']['hyperparameters'],
            'medians':med.tolist(),'scaler':'IDENTITY','missingIndicatorOrder':FEATURES,
            'tree':{k:getattr(t,k).tolist() for k in ('children_left','children_right','feature','threshold','value','n_node_samples','weighted_n_node_samples','impurity')},
            'runtime':{'python':platform.python_version(),'numpy':np.__version__,'sklearn':m.sklearn.__version__}}
        out=Model(artifact)
        assert np.allclose(out.predict_many(fs),model.predict(z),rtol=0,atol=1e-14)
        return out
    def vector(self,f):
        a=m.matrix([f],FEATURES)[0];valid=np.isfinite(a)
        return np.concatenate([np.where(valid,a,np.array(self.artifact['medians'])),~valid]).astype(np.float32)
    def predict(self,f):
        z=self.vector(f);t=self.artifact['tree'];node=0
        while t['children_left'][node]!=-1:
            node=t['children_left'][node] if z[t['feature'][node]]<=t['threshold'][node] else t['children_right'][node]
        return [float(y[0]) for y in t['value'][node]]
    def predict_many(self,fs):return np.array([self.predict(f) for f in fs])


def route(s,scores,thresholds):
    u,g,b=scores;h=thresholds;d=s['delay'];z=s['descriptors']
    if not all(math.isfinite(x) and -1e-12<=x<=1+1e-12 for x in scores):return 'D','EXPIRE_INVALID_SCORE'
    if b>=h['skipFailure'] and g<h['skipViableCeiling']:return 'D','SKIP'
    if d==0 and (u>=h['urgent'] or (g>=h['immediateViable'] and b<h['entryFailureCeiling'])):return 'A','BUY_NOW'
    support=(z['newLowStopped'] and z['closeDeteriorationStopped']) or z['priorHighReclaim'] or z['momentumTurn']
    if d>0 and s['pullbackSeen'] and support and g>=h['entryViable'] and b<h['entryFailureCeiling']:return 'B','BUY_NOW'
    if d>0 and (u>=h['urgent'] or (z['continuation'] and g>=h['entryViable'] and b<h['entryFailureCeiling'])):return 'C','BUY_NOW'
    if s['canWait']:return 'C','WAIT_ONE_STEP'
    if g>=h['entryViable'] and b<h['entryFailureCeiling']:return 'C','BUY_NOW'
    return 'D','EXPIRE_WAIT_CAP' if d==15 else 'EXPIRE_BOUNDARY'


def decide(x,path,ss,model,p):
    log=[]
    def finish(status,delay=None,rt='D',price=None):
        return {'status':status,'delay':delay,'route':rt,'executionPrice':price,'transitions':log}
    for s in ss:
        if s['status']!='AVAILABLE':return finish(s['status'])
        scores=model.predict(s['features']);rt,action=route(s,scores,p['decision']['thresholds'])
        log.append({'timestamp':s['timestamp'],'delay':s['delay'],'route':rt,'action':action,'scores':dict(zip(OUTPUTS,scores)),
            'missingFeatures':[k for k in FEATURES if s['features'][k] is None]})
        if action=='WAIT_ONE_STEP':continue
        if action=='BUY_NOW':
            price=v2.open_reference(path,c.minute(s['timestamp']))
            return finish('COUNTERFACTUAL_ENTER',s['delay'],rt,price) if price is not None else finish('EXPIRE_MISSING_OPEN')
        return finish('MODEL_SKIP' if action=='SKIP' else action)
    raise AssertionError('UNTERMINATED_WAIT')


def measure(ops,paths,selectors,legacy,model,p):
    pit=[];rows=[]
    for x in ops:
        aid=x['op']['anchorId'];path=paths[aid];ss=states(x,path,selectors[aid],legacy.get(aid,{}))
        d=decide(x,path,ss,model,p)
        # Outcomes only evaluated after complete terminal policy decision.
        b=v2.evaluate(x,path,0);e=v2.evaluate(x,path,d['delay']) if d['delay'] is not None else None
        rows.append({'id':x['id'],'session':x['session'],'symbol':x['symbol'],'source':x['op']['eventType'],
            'timestamp':x['op']['opportunityTimestamp'],'breadth':x['breadth'],'pathClass':m.path_class(x,path),
            'anchorContextAvailable':aid in legacy,'decision':d,'baseline':b,'entry':e,
            'rangeMeanAt0':ss[0].get('features',{}).get('rangeMean')})
        pit.append({'id':x['id'],'session':x['session'],'source':x['op']['eventType'],'states':ss})
    return pit,rows


def dist(values):
    a=[x for x in values if x is not None];d=m.dist(a)
    d.update(p10=c.quantile(a,.1),p25=c.quantile(a,.25),p75=c.quantile(a,.75))
    return d


def fraction(n,d):return n/d if d else None


def delta(b,a,key):return a[key]-b[key] if a[key] is not None and b[key] is not None else None


def summary(rows):
    s=v2.summarize(rows);complete=v3.complete(rows);pairs=v3.entered(complete)
    strict=[r for r in pairs if r['baseline']['strict30Complete'] and r['entry']['strict30Complete']]
    improvements=[100*(r['baseline']['price']-r['entry']['price'])/r['baseline']['price'] for r in pairs]
    s.update(priceImprovement=dist(improvements),baselineEntryPrice=dist([r['baseline']['price'] for r in pairs]),entryPrice=dist([r['entry']['price'] for r in pairs]),
        buyNow=sum(r['decision']['delay']==0 for r in rows),delayedBuy=sum(r['decision']['delay'] is not None and r['decision']['delay']>0 for r in rows),
        skip=sum(r['decision']['status']=='MODEL_SKIP' for r in rows),expire=sum(r['decision']['status'].startswith('EXPIRE') for r in rows),
        waitStarted=sum(any(t['action']=='WAIT_ONE_STEP' for t in r['decision']['transitions']) for r in rows),
        noEntryWinner={str(k):sum(r['baseline']['common']['mfe']>=k and r['decision']['delay'] is None for r in complete) for k in v2.LEVELS},
        winnerBeforeEntry={str(k):sum(r['decision']['delay'] is not None and r['baseline']['common']['hitMinutes'][str(k)] is not None and r['baseline']['common']['hitMinutes'][str(k)]<=r['decision']['delay'] for r in complete) for k in v2.LEVELS},
        terminalRoutes=dict(collections.Counter(r['decision']['route'] for r in rows)),
        delayBins={str(k):sum(r['decision']['delay']==k for r in rows) for k in (0,5,10,15,20,25,30)},
        riskAttribution={str(k):{'BETTER_ENTRY_LOCATION':s['tails'][str(k)]['baselineEnteredPair']-s['tails'][str(k)]['entryPair'],
            'SKIP_AVOIDANCE':s['tails'][str(k)]['baselineAll']-s['tails'][str(k)]['baselineEnteredPair'],
            'nonEntryByReason':dict(collections.Counter(r['decision']['status'] for r in complete if r['decision']['delay'] is None and r['baseline']['common']['mae']<=-k)),
            'strict30_BETTER_ENTRY_LOCATION':s['tails'][str(k)]['strict30BaselinePair']-s['tails'][str(k)]['strict30EntryPair']} for k in (3,5,10)})
    for name,rs,arm,window,key in [('baselinePairedMAE',pairs,'baseline','common','mae'),('entryPairedMAE',pairs,'entry','common','mae'),('baselineStrict30MAE',strict,'baseline','strict30','mae'),('entryStrict30MAE',strict,'entry','strict30','mae'),('baselinePairedMFE',pairs,'baseline','common','mfe'),('entryPairedMFE',pairs,'entry','common','mfe')]:
        s[name]=dist([r[arm][window][key] for r in rs])
    s['strict30MedianImprovementPP']=delta(s['baselineStrict30MAE'],s['entryStrict30MAE'],'median')
    s['strict30P05ImprovementPP']=delta(s['baselineStrict30MAE'],s['entryStrict30MAE'],'p05')
    bm=s['baselinePairedMFE']['mean'];am=s['entryPairedMFE']['mean'];s['remainingMFERatio']=am/bm if am is not None and bm is not None and bm>0 else None
    s['routeShares']={k:fraction(s['terminalRoutes'].get(k,0),len(rows)) for k in 'ABCD'}
    return s


def economic_metrics(rows):
    pairs=[r for r in rows if r['entry']]
    def stats(vals):
        d=dist(vals);d.update(PF=m.ca.pf(vals) if vals else None,winRate=fraction(sum(z>0 for z in vals),len(vals)));return d
    def arm(rs,name):
        return {'net':stats([r[name]['net'] for r in rs]),'MFE':dist([r[name]['MFE'] for r in rs]),'MAE':dist([r[name]['MAE'] for r in rs]),'HOLD':dist([r[name]['holdingMinutes'] for r in rs])}
    base=[r['baseline']['net'] for r in rows];pol=[r['entry']['net'] if r['entry'] else 0 for r in rows]
    loc=[r['entry']['net']-r['baseline']['net'] for r in pairs];avoid=[-r['baseline']['net'] for r in rows if not r['entry']]
    return {'pairedN':len(rows),'enteredN':len(pairs),'baseline':arm(rows,'baseline'),'policyCashIncluded':stats(pol),
        'enteredBaseline':arm(pairs,'baseline'),'enteredPolicy':arm(pairs,'entry'),
        'delta':dist([b-a for a,b in zip(base,pol)]),
        'decomposition':{'enteredTimingDeltaSumPP':sum(loc),'nonEntryAvoidanceDeltaSumPP':sum(avoid),
            'enteredTimingContributionMeanPP':fraction(sum(loc),len(rows)),'nonEntryContributionMeanPP':fraction(sum(avoid),len(rows)),
            'interpretation':'Timing contribution includes changed fixed EXIT horizon and location. No causal profitability claim; coverage/cash effect separated.'}}


def report_panel(rows,p,partition,top3,volmedian,econ):
    old=v2.panel(rows,top3);dates=p['evaluation']['chronologicalBlocks'][partition]
    def panels(key):return {k:summary(rs) for k,rs in key.items()}
    groups={'cohorts':{k:[r for r in rows if r['source']==k] for k in (q.INITIAL,q.DIP)},
        'classes':{k:[r for r in rows if r['pathClass']==k] for k in v3.CLASSES},
        'routes':{k:[r for r in rows if r['decision']['route']==k] for k in 'ABCD'},
        'blocks':{str(i+1):[r for r in rows if r['session'] in ds] for i,ds in enumerate(dates)},
        'breadth':{str(k):[r for r in rows if r['breadth']==k] for k in range(1,6)},
        'sessionPart':{k:[r for r in rows if (c.minute(r['timestamp'])<690)==b] for k,b in [('MORNING',True),('AFTERNOON',False)]},
        'volatility':{k:[r for r in rows if ('MISSING' if r['rangeMeanAt0'] is None or volmedian is None else 'LOW_OR_EQUAL' if r['rangeMeanAt0']<=volmedian else 'HIGH')==k] for k in ['MISSING','LOW_OR_EQUAL','HIGH']}}
    result={'overall':summary(rows),'entryGates':old['gates'],'entryGatePass':old['entryGatePass'],
        'concentration':old['concentration'],'top3Excluded':summary([r for r in rows if r['symbol'] not in top3]),
        'sessions':{d:summary([r for r in rows if r['session']==d]) for d in p['split'][partition]}}
    for name,group in groups.items():result[name]=panels(group)
    wait=[r for r in rows if any(t['action']=='WAIT_ONE_STEP' for t in r['decision']['transitions'])]
    result['waitMembership']=summary(wait)
    result['waitMembership']['waitDurationAll']=dist([r['decision']['transitions'][-1]['delay'] for r in wait])
    result['economic']={'overall':economic_metrics(econ)}
    emap={r['id']:r for r in econ}
    for name,group in groups.items():result['economic'][name]={k:economic_metrics([emap[r['id']] for r in rs if r['id'] in emap]) for k,rs in group.items()}
    result['economic']['top3Excluded']=economic_metrics([r for r in econ if r['symbol'] not in top3])
    return result


def missingness(pit,rows=None):
    ss=[s for r in pit for s in r['states'] if s['status']=='AVAILABLE']
    def rates(states):
        return {k:{'n':len(states),'available':sum(s['features'][k] is not None for s in states),'missingRate':fraction(sum(s['features'][k] is None for s in states),len(states))} for k in FEATURES}
    result={'allAvailableStates':rates(ss),'t0':rates([s for s in ss if s['delay']==0]),'terminalUnavailable':dict(collections.Counter(s['status'] for r in pit for s in r['states'] if s['status']!='AVAILABLE'))}
    if rows is not None:
        smap={(r['id'],s['delay']):s for r in pit for s in r['states']}
        result['visitedByTerminalRoute']={k:rates([smap[(r['id'],t['delay'])] for r in rows if r['decision']['route']==k for t in r['decision']['transitions']]) for k in 'ABCD'}
        result['visitedByEntryStatus']={k:rates([smap[(r['id'],t['delay'])] for r in rows if (r['decision']['delay'] is not None)==enter for t in r['decision']['transitions']]) for k,enter in [('ENTER',True),('NON_ENTRY',False)]}
    return result


def numeric_status(observed,target,unit):
    near={'fraction':.05,'pp':.05,'count':10}[unit]
    hard=-.25 if unit=='pp' else .5*target
    if observed is None or not math.isfinite(observed):status='HARD_FAIL'
    elif observed>=target:status='PASS'
    elif observed>=target-near:status='NEAR_MISS'
    elif observed<hard:status='HARD_FAIL'
    else:status='FAIL'
    return {'target':target,'observed':observed,'gap':observed-target if observed is not None else None,'unit':unit,'nearTolerance':near,'hardFloor':hard,'status':status}


def classify(panel,economic_gate):
    s=panel['overall'];e=panel['economic']['overall'];rows={}
    def add(k,o,t,u):rows[k]=numeric_status(o,t,u)
    add('completeN',s['commonComplete'],100,'count');add('entryCoverage',s['entryCoverage'],.70,'fraction')
    for k,t in [('1',.80),('2',.85),('3',.90),('5',.90)]:add('preservation'+k,s['preservation'][k]['rate'],t,'fraction')
    for k in ['IMMEDIATE_WINNER','FAST_WINNER']:add(k,s['classes'][k]['rate3'],.90,'fraction')
    add('priceImprovementPP',s['priceImprovement']['mean'],.10,'pp')
    add('strict30MedianImprovementPP',s['strict30MedianImprovementPP'],.10,'pp')
    add('strict30P05ImprovementPP',s['strict30P05ImprovementPP'],.25,'pp')
    tail=s['tails']['5'];add('deep5Reduction',fraction(tail['baselineAll']-tail['entryPair'],tail['baselineAll']),.10,'fraction')
    add('remainingMFE',s['remainingMFERatio'],.90,'fraction')
    add('economicEvaluable',fraction(e['pairedN'],s['commonComplete']),.90,'fraction')
    add('economicMeanDeltaPP',e['delta']['mean'],.05,'pp')
    add('economicPFDelta',delta(e['baseline']['net'],e['policyCashIncluded'],'PF'),0,'pp')
    add('economicP05DeltaPP',delta(e['baseline']['net'],e['policyCashIncluded'],'p05'),0,'pp')
    composite={**{'entry_'+k:val for k,val in panel['entryGates'].items() if k in ('pullback','cohorts','chronological','top3Exclusion')},**{'economic_'+k:val for k,val in economic_gate.items() if k in ('cohorts','blocks','top3')},'waitUsed':s['waitTransitions']>0,'delayedEntryUsed':s['delayedBuy']>0}
    severity={'PASS':0,'NEAR_MISS':1,'FAIL':2,'HARD_FAIL':3}
    overall=max([r['status'] for r in rows.values()]+['PASS' if x else 'FAIL' for x in composite.values()],key=lambda x:severity[x])
    return {'overallStatus':overall,'metrics':rows,'compositeGates':composite}


def audit_tree(model,fs,labels):
    """Independent fitted-node moments and greedy split check, zero estimator.fit."""
    x=np.array([model.vector(f) for f in fs]);y=np.array([r['targets'] for r in labels],float);w=np.array([r['weight'] for r in labels])
    t=model.artifact['tree'];checked=[]
    def impurity(indices):
        ww=w[indices];yy=y[indices];sw=ww.sum();mean=(ww[:,None]*yy).sum(axis=0)/sw
        return float(np.mean((ww[:,None]*yy*yy).sum(axis=0)/sw-mean*mean)),mean
    def walk(node,indices,depth):
        imp,mean=impurity(indices)
        assert t['n_node_samples'][node]==len(indices)
        assert np.allclose(mean,np.array(t['value'][node]).reshape(-1),rtol=0,atol=1e-12)
        assert abs(imp-t['impurity'][node])<1e-11
        assert abs(w[indices].sum()-t['weighted_n_node_samples'][node])<1e-10
        left=t['children_left'][node]
        if left==-1:
            checked.append({'node':node,'leaf':True,'n':len(indices),'depth':depth});return
        feature=t['feature'][node];thr=t['threshold'][node];a=indices[x[indices,feature]<=thr];b=indices[x[indices,feature]>thr]
        assert len(a)>=100 and len(b)>=100 and depth<4
        sw=w[indices].sum();chosen=(w[a].sum()*impurity(a)[0]+w[b].sum()*impurity(b)[0])/sw
        best=imp
        for col in range(x.shape[1]):
            order=indices[np.argsort(x[indices,col],kind='stable')];zz=x[order,col];ww=w[order];yy=y[order]
            cuts=np.arange(99,len(order)-100)
            cuts=cuts[zz[cuts+1]>zz[cuts]+1e-7]
            if not len(cuts):continue
            cw=np.cumsum(ww);cy=np.cumsum(ww[:,None]*yy,axis=0);cy2=np.cumsum(ww[:,None]*yy*yy,axis=0)
            wl=cw[cuts,None];wr=cw[-1]-wl;yl=cy[cuts];yr=cy[-1]-yl
            costs=np.mean((cy2[cuts]-yl*yl/wl)+(cy2[-1]-cy2[cuts]-yr*yr/wr),axis=1)/cw[-1]
            best=min(best,float(costs.min()))
        assert chosen<=best+1e-9,(node,chosen,best)
        checked.append({'node':node,'leaf':False,'n':len(indices),'depth':depth,'splitCost':chosen,'globalBestEligibleSplitCost':best})
        walk(left,a,depth+1);walk(t['children_right'][node],b,depth+1)
    walk(0,np.arange(len(labels)),0)
    return {'status':'PASS','fitCalls':0,'nodeChecks':checked,'method':'Independent weighted moments and global eligible CART split impurity; deterministic exported-tree traversal, no research-data refit.'}


def train(outdir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=False)
    p,ops,paths,selectors,legacy=sources('TRAIN')
    pit,labels=training_dataset(ops,paths,selectors,legacy);fs=join_training(pit,labels)
    assert labels and all(r['session'] in p['split']['TRAIN'] for r in labels)
    m.write(out/'pit-states.json.gz',pit);m.write(out/'training-labels.json.gz',labels)
    # Exactly one research fit. A partial directory prevents accidental repetition.
    model=Model.fit_once(fs,labels,p);m.write(out/'model.json',model.artifact)
    audit=audit_tree(model,fs,labels);m.write(out/'tree-fit-audit.json',audit)
    top3=[k for k,n in sorted(collections.Counter(x['symbol'] for x in ops).items(),key=lambda z:(-z[1],z[0]))[:3]]
    vals=[r['states'][0]['features']['rangeMean'] for r in pit if r['states'][0]['status']=='AVAILABLE' and r['states'][0]['features']['rangeMean'] is not None]
    volmedian=c.quantile(vals,.5)
    _,rows=measure(ops,paths,selectors,legacy,model,p)
    econ,es=v2.economic(rows,{x['id']:x for x in ops},paths,top3)
    panel=report_panel(rows,p,'TRAIN',top3,volmedian,econ);panel['economicAudit']=es;panel['classification']=classify(panel,es['gates'])
    m.write(out/'ledger.json.gz',rows);m.write(out/'economic-ledger.json.gz',econ);m.write(out/'summary.json',panel)
    m.write(out/'missingness.json',missingness(pit,rows))
    manifest={'partition':'TRAIN','protocolCommit':PROTOCOL_COMMIT,'protocolSHA256':PROTOCOL_SHA,'featureManifestSHA256':p['featureManifestSHA256'],
        'trainingEpisodes':len({r['id'] for r in labels}),'trainingStates':len(labels),'labelMeans':np.average([r['targets'] for r in labels],axis=0,weights=[r['weight'] for r in labels]).tolist(),
        'supervisedFits':1,'candidateCount':1,'calibrationFits':0,'top3':top3,'volatilityMedian':volmedian,
        'split':p['split']['TRAIN'],'opportunityIdSHA256':m.hashlib.sha256(m.enc([x['id'] for x in ops])).hexdigest(),
        'modelSHA256':m.sha(out/'model.json'),'codeSHA256':m.sha(__file__),'sourcePins':p['sourcePins'],
        'files':{f.name:m.sha(f) for f in sorted(out.iterdir())},'safety':p['safety'],'developmentTestOpened':False,'freshOOSOpened':False}
    m.write(out/'manifest.json',manifest)
    print(json.dumps({'phase':'TRAIN_COMPLETE','states':len(labels),'episodes':manifest['trainingEpisodes'],'fits':1,'status':panel['classification']['overallStatus'],'coverage':panel['overall']['entryCoverage'],'routes':panel['overall']['terminalRoutes']}))


def validate(outdir,train_dir):
    out=Path(outdir);out.mkdir(parents=True,exist_ok=False)
    trained=Path(train_dir);tm=m.read(trained/'manifest.json');p=protocol()
    for f,h in tm['files'].items():assert m.sha(trained/f)==h,f
    assert tm['protocolSHA256']==PROTOCOL_SHA
    model=Model(m.read(trained/'model.json'));assert m.sha(trained/'model.json')==tm['modelSHA256']
    p,ops,paths,selectors,legacy=sources('VALIDATION')
    pit,rows=measure(ops,paths,selectors,legacy,model,p)
    econ,es=v2.economic(rows,{x['id']:x for x in ops},paths,tm['top3'])
    panel=report_panel(rows,p,'VALIDATION',tm['top3'],tm['volatilityMedian'],econ)
    panel['economicAudit']=es;panel['classification']=classify(panel,es['gates'])
    m.write(out/'pit-states.json.gz',pit);m.write(out/'ledger.json.gz',rows);m.write(out/'economic-ledger.json.gz',econ)
    m.write(out/'route-ledger.json.gz',[{'id':r['id'],**r['decision']} for r in rows]);m.write(out/'summary.json',panel)
    m.write(out/'missingness.json',missingness(pit,rows))
    m.write(out/'manifest.json',{'partition':'VALIDATION','protocolCommit':PROTOCOL_COMMIT,'protocolSHA256':PROTOCOL_SHA,'featureManifestSHA256':p['featureManifestSHA256'],
        'trainingManifestSHA256':m.sha(trained/'manifest.json'),'modelSHA256':tm['modelSHA256'],'codeSHA256':m.sha(__file__),
        'opportunityIdSHA256':m.hashlib.sha256(m.enc([x['id'] for x in ops])).hexdigest(),'split':p['split']['VALIDATION'],
        'files':{f.name:m.sha(f) for f in sorted(out.iterdir())},'validationExposed':True,'firstCandidateMeasurementCount':1,
        'postMeasurementChanges':p['runControl']['postMeasurementChanges'],'supervisedFits':0,'developmentTestOpened':False,'freshOOSOpened':False,'candidateFreeze':False,'safety':p['safety']})
    print(json.dumps({'phase':'VALIDATION_COMPLETE','classification':panel['classification'],'summary':panel['overall'],'economic':panel['economic']['overall']},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['train','validate']);parser.add_argument('--out',required=True);parser.add_argument('--train-dir',default=str(BASE/'train'))
    args=parser.parse_args()
    if args.phase=='train':train(args.out)
    else:validate(args.out,args.train_dir)
