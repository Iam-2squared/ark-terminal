"""Deterministic, zero-fit R50 replay and frozen-gate scorecard."""
from __future__ import annotations
import argparse, collections, gzip, hashlib, json, math, statistics
from pathlib import Path
import numpy as np
from scripts import phase57_exit_winner_lifecycle_r50 as runtime
from scripts import phase57_exit_execution_contract_v1 as execution

ROOT=runtime.ROOT
def require(x,m):
    if not x: raise ValueError(m)
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def read_json(p): return json.loads(Path(p).read_text())
def write_json(p,x): Path(p).write_text(json.dumps(x,sort_keys=True,separators=(',',':'))+'\n')
def write_gz(p,rows):
    with open(p,'wb') as raw:
        with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as z:
            for x in rows: z.write((json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode())

def identity_key(arm, entry_id):
    require(arm in runtime.protocol()['entryArms'] and isinstance(entry_id,str) and entry_id, 'R50_ENTRY_IDENTITY')
    return arm+'\x00'+entry_id

def load(root):
    data=root/'gen3/data'; p=runtime.protocol(); source=p['replaySource']
    expected={'decision-features.npz':'45b91faed0ee7ac3dd46d5fa9bdb4f9f5940cfa2c4a9292af468427d551f5b3e',
              'row-identities.jsonl.gz':'41d875a3c7d8d8ebcb6fe6ef2022277143b6b34f9ba34c163395f81f2873ac47'}
    for n,d in expected.items(): require(sha(data/n)==d,'R50_UPSTREAM_HASH_'+n)
    require(sha(root/'gen3/oof-predictions.npz')==source['predictionSha256'],'R50_PREDICTION_HASH')
    receipt=read_json(data/'data-receipt.json'); names=receipt['numericColumns']
    with np.load(data/'decision-features.npz',allow_pickle=False) as z:
        numeric=z['numeric']; fresh=z['fresh']
    identities=[]
    with gzip.open(data/'row-identities.jsonl.gz','rt') as f:
        for line in f: identities.append(json.loads(line))
    require(len(identities)==len(numeric)==656247,'R50_ROWS')
    base={}
    with gzip.open(root/'gen3/run-a/HOLD_TO_TERMINAL_DIAGNOSTIC.jsonl.gz','rt') as f:
        for line in f:
            x=json.loads(line); k=identity_key(x['entryArm'],x['entryId']); require(k not in base,'R50_DUPLICATE_ARM_ENTRY'); base[k]=x
    require(len(base)==2257,'R50_CONTROL_ROWS')
    return numeric,fresh,names,identities,base

def facts(numeric,fresh,names,i):
    vals={}
    for n in runtime.FACTS:
        x=float(numeric[i,names.index('facts.'+n)])
        vals[n]=x if math.isfinite(x) else None
    now=int(rows[i]['now'])
    return {'now':now,'maxKnownAt':now,'maxBarEnd':now,'fresh':bool(fresh[i]),'values':vals}

def replay(candidate,numeric,fresh,names,identities,base,raw):
    global rows; rows=identities
    groups=collections.defaultdict(list)
    for i,x in enumerate(identities):
        k=identity_key(x['arm'],x['entryId'])
        if k in base: groups[k].append(i)
    out=[]
    for key in sorted(base):
        control=base[key]; eid=control['entryId']; seq=groups[key]; state=runtime.initial_state(); chosen=None; trigger=None; counts=collections.Counter(); missing=[]
        for i in seq:
            now=int(identities[i]['now']); e=facts(numeric,fresh,names,i)
            result=runtime.intent(e,state,candidate,terminal=(now==925)); state=result['state']; counts[result['authority']]+=1
            if result['action']=='HOLD': continue
            if result['action']=='FORCE_TERMINAL':
                chosen=(control['exitPrice'],control['exitMinute'],'FORCED_TERMINAL'); trigger=i; break
            ref=execution.ordinary_execution_reference(control['session'],now,raw[control['opportunity']]['today'])
            if ref['status']=='RESOLVED_NEXT_SCHEDULED_OPEN':
                chosen=(float(ref['price']),int(ref['referenceStart']),'MODEL_EXIT'); trigger=i; break
            missing.append({'now':now,'status':ref['status']})
        require(chosen is not None and trigger is not None,'R50_UNRESOLVED')
        price,minute,kind=chosen; entry=float(control['entryPrice']); m0=control['metrics']; upside=float(m0['entryToPostEntryHighPct'])
        high=entry*(1+upside/100); gross=None if price is None else 100*(price-entry)/entry
        capture=None if price is None or high<=entry else 100*(price-entry)/(high-entry)
        metrics={'entryToExitGrossPct':gross,'entryToExitNetPct':None if gross is None else gross-0.05,'entryToPostEntryHighPct':upside,
                 'postEntryUpsideCapturePct':capture,'postEntryHighKnownAt':m0['postEntryHighKnownAt'],
                 'premature':False if minute is None else minute<int(m0['postEntryHighKnownAt']),'canonicalBucket':m0.get('bucket'),
                 'highToExitGapPp':None if price is None else 100*(high-price)/entry}
        out.append({'candidateId':candidate,'entryArm':control['entryArm'],'entryId':eid,'session':control['session'],
          'opportunity':control['opportunity'],'entryMinute':control['entryMinute'],'entryPrice':entry,
          'decisionNow':int(identities[trigger]['now']),'exitMinute':minute,'exitPrice':price,'exitKind':kind,
          'authority':result['authority'],'authorityCounts':dict(counts),'decisionState':state,
          'decisionFacts':facts(numeric,fresh,names,trigger),'missingOrdinaryReferences':missing,
          'netReturnPctBySellCost':{f'{c:.2f}':None if gross is None else gross-c for c in (0.05,0.10,0.20)},'metrics':metrics})
    return out

def q(v,p):
    return float(np.quantile(np.asarray(v,float),p))
def arm_score(rows,arm,p):
    allr=[x for x in rows if x['entryArm']==arm]; primary=[x for x in allr if x['metrics']['entryToPostEntryHighPct']>=5]
    require(all(x['metrics']['entryToExitNetPct'] is not None and x['metrics']['postEntryUpsideCapturePct'] is not None for x in primary),'R50_PRIMARY_UNRESOLVED')
    nets=[x['metrics']['entryToExitNetPct'] for x in primary]; caps=[x['metrics']['postEntryUpsideCapturePct'] for x in primary]
    losses=-sum(x for x in nets if x<0); profits=sum(x for x in nets if x>0)
    d={'allRows':len(allr),'support':len(primary),'meanNet':statistics.fmean(nets),'medianNet':statistics.median(nets),
       'profitFactor':None if losses==0 else profits/losses,'winRate':sum(x>0 for x in nets)/len(nets),
       'medianCapture':statistics.median(caps),'meanCapture':statistics.fmean(caps),'negativeCaptureShare':sum(x<0 for x in caps)/len(caps),
       'prematureRate':sum(x['metrics']['premature'] for x in primary)/len(primary),'medianHighToExitGapPp':statistics.median(x['metrics']['highToExitGapPp'] for x in primary),
       'p10Net':q(nets,.1),'p05Net':q(nets,.05),'worstNet':min(nets),
       'meanNetCost10':statistics.fmean(x['netReturnPctBySellCost']['0.10'] for x in primary),
       'meanNetCost20':statistics.fmean(x['netReturnPctBySellCost']['0.20'] for x in primary)}
    g=p['gatePerEntryArm']; d['gates']={'support':d['support']>=g['supportMin'],'capture':d['medianCapture']>=g['medianPostEntryUpsideCaptureMinPct'],
      'meanNet':d['meanNet']>=g['meanNetMinPct'],'medianNet':d['medianNet']>=g['medianNetMinPct'],'premature':d['prematureRate']<=g['prematureRateMax']}
    d['pass']=all(d['gates'].values()); return d

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--artifact-root',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    p=runtime.protocol(); require(not a.out.exists(),'R50_OUT_EXISTS'); a.out.mkdir(parents=True)
    numeric,fresh,names,ids,base=load(a.artifact_root)
    raw_path=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
    require(sha(raw_path)==p['replaySource']['rawPathSha256'],'R50_RAW_HASH')
    with gzip.open(raw_path,'rt') as f: raw=json.load(f)
    ledgers={}; cards={}; canonical={}
    for candidate in runtime.CANDIDATES:
        arows=replay(candidate,numeric,fresh,names,ids,base,raw); brows=replay(candidate,numeric,fresh,names,ids,base,raw)
        pa=a.out/(candidate+'-run-a.jsonl.gz'); pb=a.out/(candidate+'-run-b.jsonl.gz'); write_gz(pa,arows); write_gz(pb,brows)
        require(sha(pa)==sha(pb),'R50_AB_MISMATCH'); ledgers[candidate]=sha(pa)
        cards[candidate]={'arms':{arm:arm_score(arows,arm,p) for arm in p['entryArms']}}
        cards[candidate]['pass']=all(x['pass'] for x in cards[candidate]['arms'].values())
        cards[candidate]['harvests']=sum(x['exitKind']=='MODEL_EXIT' for x in arows)
    passing=[c for c in runtime.CANDIDATES if cards[c]['pass']]
    if len(passing)==1: selection=passing[0]
    elif len(passing)==0: selection=None
    else:
        key=lambda c:(min(x['medianCapture'] for x in cards[c]['arms'].values()),min(x['meanNet'] for x in cards[c]['arms'].values()),-max(x['prematureRate'] for x in cards[c]['arms'].values()))
        ranked=sorted(passing,key=key,reverse=True); selection=None if key(ranked[0])==key(ranked[1]) else ranked[0]
    result={'schema':'phase57-r50-finite-replay-result-v1','status':'SELECT' if selection else 'NO_SELECTION_STOP','selection':selection,
      'executionSha':__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),'protocolSha256':runtime.PROTOCOL_SHA256,
      'candidateCount':2,'modelFits':0,'predictionRefits':0,'runABIdentical':True,'ledgerHashes':ledgers,'scorecard':cards,
      'providerRequests':0,'protectedPartitionsOpened':0,'safety':p['safety'],'capitalAllowed':bool(selection)}
    write_json(a.out/'result.json',result); print(result['status'])
if __name__=='__main__': main()
