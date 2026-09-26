"""One-pass diagnostic of frozen Gen1/Gen2; no Gen3 policy or fitting."""
from __future__ import annotations
import argparse, collections, gzip, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from scripts import phase57_exit_finite_r36 as base
from scripts.phase57_exit_gen2_labels_r41 import REASONS
from scripts.phase57_exit_result_audit_r38 import decision_now
from scripts.phase57_exit_gen2_data_r41 import pattern_vector
from scripts.phase57_exit_feature_contract_v1 import pattern_rows

SIGNALS=('CONTINUATION','BREAKOUT','COMPRESSION_EXPANSION','HIGHER_LOW','LOWER_WICK','RECLAIM')
NUM=('stateDwellObservedActiveMinutes','history.3.stateChanges','history.5.stateChanges','history.10.stateChanges','history.stateRunObservedSamplesCapped10','position.activeMinutesHeld','position.fullOwnedPrefix','position.currentReturnPct','position.observedMfePct','position.observedPeakGivebackPp','position.activeMinutesSincePeakConfirmation')
CAT=('currentState.state','entryToCurrentState')+tuple(f'signal.{s}.{t}' for t in ('currentTriState','observedTrueToFalseTriState') for s in SIGNALS)
STARTS=np.array([*range(540,690),*range(750,925)])
def rows(p):
 with gzip.open(p,'rt') as f: return [json.loads(s) for s in f]
def stats(x):
 a=np.asarray(x,dtype=float);a=a[np.isfinite(a)]
 return {'n':len(a),'mean':float(a.mean()) if len(a) else None,'median':float(np.median(a)) if len(a) else None}
def overlap(c,f):
 valid=np.isfinite(c)&np.isfinite(f);n=int(valid.sum())
 return {'bothAvailableN':n,'cells':{f'C{a}F{b}':{'n':int(np.sum(valid&(c==a)&(f==b))),'fraction':float(np.sum(valid&(c==a)&(f==b))/n) if n else None} for a in (0,1) for b in (0,1)}}
def path_class(row):
 if row['exitStatus']!='RESOLVED':return 'CENSORED'
 m=row['metrics'];cap=m.get('postEntryUpsideCapturePct');ret=row['netReturnPctBySellCost']['0.05'];winner=base._bucket(row)=='>=5%'
 if winner and cap is not None and cap>=50 and ret>0:return 'A_RETAINED_WINNER'
 gap=m.get('postEntryHighEvaluatorGapPp')
 if winner and cap is not None and cap<50 and gap is not None and gap>=2 and m.get('postEntryHighKnownAt') is not None and m['postEntryHighKnownAt']<=row['exitMinute']:return 'B_GIVEBACK_WINNER'
 if not winner and ret<=-1 and row['activeMinutesHeld']>=30:return 'C_PROLONGED_LOSER'
 return 'OTHER'
def run(core,gen2,gen1,out):
 assert not out.exists(),'APPEND_ONLY'
 p=base.read_json(base.ROOT/'docs/evidence/phase57-comprehensive-exit-v1/GEN2_PRECOMMIT_R41.json')
 receipt=base.read_json(gen2/'data/data-receipt.json')
 pins={gen2/'data'/name:h for name,h in receipt['outputHashes'].items()}
 pins[gen2/'oof-predictions.npz']=base.read_json(gen2/'fit-receipt.json')['predictionSha256']
 manifest=base.read_json(core/'core-a/manifest.json')
 for name,h in manifest['outputHashes'].items():pins[core/'core-a'/name]=h
 for name,h in receipt['sourceHashes'].items():pins[base.ROOT/name]=h
 for f,h in pins.items():assert base.sha(f)==h,str(f)
 labels=np.load(gen2/'data/training-labels.npz',allow_pickle=False);pred=np.load(gen2/'oof-predictions.npz',allow_pickle=False)
 columns=base.read_json(core/'core-a/columns.json');ni=[columns['numeric'].index(n) for n in NUM];ci=[columns['categorical'].index(n) for n in CAT]
 parts=[]
 for session in base.r25.development_sessions():
  data=[]
  for r in sorted(rows(core/'core-a/checkpoints'/f'{session}.jsonl.gz'), key=lambda r:(base.ARMS.index(r['identity'][0]),r['identity'][1],r['identity'][2])):
   a,e,n=r['identity'];data.append([session,a,e,n,r['fresh']]+[r['categorical'][i] for i in ci]+[r['numeric'][i] for i in ni])
  parts.append(pd.DataFrame(data,columns=['session','arm','entryId','now','fresh',*CAT,*NUM]))
 frame=pd.concat(parts,ignore_index=True);assert len(frame)==656247
 # Exact source identity alignment to saved predictions and labels.
 with gzip.open(gen2/'data/source-row-identity.jsonl.gz','rt') as f:
  for i,line in enumerate(f):
   r=json.loads(line);s=frame.iloc[i];assert (r['index'],r['session'],r['arm'],r['entryId'],r['now'])==(i,s['session'],s['arm'],s['entryId'],int(s['now']))
 score_sessions={s for f in p['split']['folds'] for s in f['score']};frame['oof']=frame.session.isin(score_sessions)&(frame.now!=925)
 frame['symbol']=frame.entryId.str.split('|').str[1];frame['timeBand']=pd.cut(frame.now,[540,600,690,810,870,925],labels=['09-10','10-lunch','lunch-13:30','13:30-14:30','14:30-terminal']).astype(str)
 frame['remaining']=np.array([len(STARTS)-np.searchsorted(STARTS,n) for n in frame.now]);frame['remainingBand']=pd.cut(frame.remaining,[-1,0,15,60,400],labels=['0','1-15','16-60','61+']).astype(str)
 frame['lunchBoundary']=frame.now.isin([689,690,751,752])
 raw=base.read_json(base.RAW_PATHS);origins={r['id']:r['origin'] for r in base.read_json(base.PATTERN_OPPORTUNITIES)}
 # Diagnostic closed-prefix momentum/range/volume only; no future window access here.
 past={}
 for oid,path in raw.items():
  by={int(r[0]):r for r in path['today']};d={}
  for k,start in enumerate(STARTS):
   rr=[by.get(int(t)) for t in STARTS[max(0,k-4):k+1]]
   valid=len(rr)==5 and all(r is not None and all(base.finite(v) and v>0 for v in r[1:5]) for r in rr)
   d[int(start)+1]=(100*(rr[-1][4]/rr[0][4]-1),100*(max(r[2] for r in rr)/min(r[3] for r in rr)-1),sum(r[5] for r in rr) if all(base.finite(r[5]) and r[5]>=0 for r in rr) else np.nan) if valid else (np.nan,np.nan,np.nan)
  past[oid]=d
 arr=np.array([past[base._oid(e)][int(n)] for e,n in zip(frame.entryId,frame.now)])
 for j,name in enumerate(('past5MomentumPct','past5RangePct','past5Volume')):frame[name]=arr[:,j]
 frame['volatilityBand']=pd.cut(frame.past5RangePct,[-np.inf,.5,1,2,np.inf],labels=['<.5','.5-1','1-2','>=2']).astype(str)
 frame['volumeBand']=pd.cut(frame.past5Volume,[-1,0,1000,10000,100000,np.inf],labels=['zero','1-1k','1k-10k','10k-100k','100k+']).astype(str)
 for h,name in enumerate(('C','F')):
  frame[name]=labels['targets'][:,h];frame[name+'Reason']=[REASONS[i] for i in labels['reasonCode'][:,h]];frame[name+'Full']=labels['horizonBars'][:,h]==(60 if h==0 else 15)
 summary=[];breakdown=[]
 for arm in base.ARMS:
  f=frame[(frame.arm==arm)&frame.oof&frame.fresh];full=f[f.CFull&f.FFull]
  auc={}
  for spec in pred.files:
   vals=pred[spec];auc[spec]={}
   for h,n in enumerate(('C','F')):
    sub=f[f[n+'Full']&f[n].notna()];auc[spec][n]={'n':len(sub),'auc':float(roc_auc_score(sub[n],vals[sub.index,h])) if sub[n].nunique()==2 else None}
   auc[spec]['scoreCorrelationFullWindow']=float(np.corrcoef(vals[full.index].T)[0,1])
  summary.append({'arm':arm,'freshOofN':len(f),'CavailableN':int(f.C.notna().sum()),'FavailableN':int(f.F.notna().sum()),'Ccoverage':float(f.C.notna().mean()),'Fcoverage':float(f.F.notna().mean()),'allHorizonOverlap':overlap(f.C.values,f.F.values),'fullWindowOverlap':overlap(full.C.values,full.F.values),'modelSpecs':auc})
  for dim in ('timeBand','remainingBand','lunchBoundary','session','symbol','currentState.state','volatilityBand','volumeBand','position.fullOwnedPrefix','fresh'):
   # Freshness comparison deliberately includes stale OOF rows; other denominators fresh OOF.
   scope=frame[(frame.arm==arm)&frame.oof] if dim=='fresh' else f
   for value,g in scope.groupby(dim,dropna=False,observed=True):
    gf=g[g.CFull&g.FFull];breakdown.append({'arm':arm,'dimension':dim,'value':str(value),'n':len(g),'Ccoverage':float(g.C.notna().mean()),'Fcoverage':float(g.F.notna().mean()),'CshortenedN':int((~g.CFull).sum()),'FshortenedN':int((~g.FFull).sum()),'CmissingReasons':g.CReason.value_counts().to_dict(),'FmissingReasons':g.FReason.value_counts().to_dict(),'fullWindowOverlap':overlap(gf.C.values,gf.F.values)})
 print('LABEL_AND_MISSINGNESS_COMPLETE',json.dumps(summary),flush=True)
 # Sequential diagnostics never infer a transition across missing/stale checkpoints.
 rank={int(m)+1:i for i,m in enumerate(STARTS)}
 frame['activeRank']=frame.now.map(rank)
 group=frame.groupby(['arm','entryId'],sort=False)
 prev=group[['activeRank','fresh','currentState.state']].shift(1)
 valid=frame.fresh & prev.fresh.fillna(False).astype(bool) & (frame.activeRank-prev.activeRank==1)
 statevalid=valid & frame['currentState.state'].ne('UNKNOWN') & prev['currentState.state'].ne('UNKNOWN')
 frame['path2']=np.where(statevalid,prev['currentState.state'].fillna('UNKNOWN')+'>'+frame['currentState.state'],'UNKNOWN')
 prev2=group['currentState.state'].shift(2).fillna('UNKNOWN')
 frame['pairValid']=statevalid
 valid3=statevalid & group.pairValid.shift(1).fillna(False).astype(bool) & prev2.ne('UNKNOWN')
 frame['path3']=np.where(valid3,prev2+'>'+prev['currentState.state'].fillna('UNKNOWN')+'>'+frame['currentState.state'],'UNKNOWN')
 signal_paths={s:np.where(valid,group[f'signal.{s}.currentTriState'].shift(1).fillna('UNKNOWN')+'>'+frame[f'signal.{s}.currentTriState'],'UNKNOWN') for s in SIGNALS}
 transitions=[]
 scope=frame[frame.oof&frame.fresh]
 for arm in base.ARMS:
  f=scope[scope.arm==arm]
  for dim,values in [('path2',f.path2),('path3',f.path3)]+[(s,pd.Series(signal_paths[s][f.index],index=f.index)) for s in SIGNALS]:
   for val,ids in values.groupby(values).groups.items():
    q=f.loc[ids];transitions.append({'arm':arm,'kind':dim,'transition':val,'n':len(q),'currentReturn':stats(q['position.currentReturnPct']),'giveback':stats(q['position.observedPeakGivebackPp']),'Ccoverage':float(q.C.notna().mean()),'Fcoverage':float(q.F.notna().mean())})
 print('TRANSITIONS_COMPLETE',flush=True)
 lookup={(a,e,int(n)):i for i,(a,e,n) in enumerate(zip(frame.arm,frame.entryId,frame.now))}
 pattern_names=sorted(r['feature'] for r in pattern_rows() if r['selectedInFiniteSearch']);pcache={};separation=[];details=[]
 for generation,paths in [('R36',sorted((gen1/'run-a/ledgers').glob('*.jsonl.gz'))),('R41',sorted((gen2/'run-a').glob('GEN2_R41_*.jsonl.gz')))]:
  assert len(paths)==(24 if generation=='R36' else 16)
  for path in paths:
   ledger=rows(path);pins[path]=base.sha(path)
   for row in ledger:
    cls=path_class(row)
    if cls not in ('A_RETAINED_WINNER','B_GIVEBACK_WINNER','C_PROLONGED_LOSER'):continue
    idx=lookup[(row['entryArm'],row['entryId'],row.get('decisionNow',decision_now(row))) ];q=frame.loc[idx];key=(row['opportunity'],int(q['now']))
    if key not in pcache:
     vec=pattern_vector(row['session'],int(q['now']),raw[key[0]],origins[key[0]],pattern_names)
     fam={}
     for name,value in zip(pattern_names,vec):fam.setdefault(name.split('/')[0],[]).append(value)
     pcache[key]={f'pattern.{k}':stats(v) for k,v in fam.items()}
    item={'generation':generation,'candidate':path.stem.split('.')[0],'arm':row['entryArm'],'opportunity':row['opportunity'],'class':cls,'decisionNow':int(q['now']), 'fresh':bool(q.fresh),'state':q['currentState.state'],'path2':q.path2,'path3':q.path3,'signals':{s:q[f'signal.{s}.currentTriState'] for s in SIGNALS},'signalLoss':{s:q[f'signal.{s}.observedTrueToFalseTriState'] for s in SIGNALS},'numeric':{n:float(q[n]) if pd.notna(q[n]) else None for n in (*NUM,'past5MomentumPct','past5RangePct','past5Volume')},'patternFamily':pcache[key]}
    details.append(item)
 print('SEPARATION_ROWS',len(details),'PATTERN_KEYS',len(pcache),flush=True)
 for generation in ('R36','R41'):
  for arm in base.ARMS:
   for cls in ('A_RETAINED_WINNER','B_GIVEBACK_WINNER','C_PROLONGED_LOSER'):
    rr=[r for r in details if r['generation']==generation and r['arm']==arm and r['class']==cls]
    separation.append({'generation':generation,'arm':arm,'class':cls,'policyObservationN':len(rr),'uniqueOpportunities':len({r['opportunity'] for r in rr}),'states':dict(collections.Counter(r['state'] for r in rr)),'paths3':dict(collections.Counter(r['path3'] for r in rr)),'signals':{s:dict(collections.Counter(r['signals'][s] for r in rr)) for s in SIGNALS},'signalLoss':{s:dict(collections.Counter(r['signalLoss'][s] for r in rr)) for s in SIGNALS},'numeric':{n:stats([r['numeric'][n] for r in rr]) for n in (*NUM,'past5MomentumPct','past5RangePct','past5Volume')},'patternFamily':{k:stats([r['patternFamily'][k]['mean'] for r in rr]) for k in sorted(next(iter(pcache.values())))}})
 out.mkdir(parents=True)
 for name,obj in [('label-overlap-and-auc.json',summary),('missingness-breakdown.json',breakdown),('state-signal-transitions.json',transitions),('winner-giveback-loser-separation.json',separation)]:base.write_json(out/name,obj)
 base.write_jsonl_gz(out/'separation-detail.jsonl.gz',details)
 base.write_json(out/'receipt.json',{'schema':'phase57-final-pre-gen3-analysis-r44-v1','gen3ModelFits':0,'gen3PolicyReplays':0,'gen1Gen2RefitsOrPolicyReplays':0,'providerRequests':0,'protectedPartitionsOpened':0,'safety':base.SAFETY,'allRows':len(frame),'sourceHashes':{str(f):h for f,h in pins.items()},'outputHashes':{x.name:base.sha(x) for x in out.iterdir()},'definitions':{'A':'resolved >=5 bucket, capture>=50%, net>0','B':'resolved >=5 bucket,capture<50%, postEntryHigh gap>=2pp and observed High knownAt<=exitMinute; not a certified complete-prefix claim','C':'resolved non->=5 bucket, net<=-1%, held>=30 active minutes','overlap':'same checkpoint, full means C60/F15 calendar horizons unshortened; missing is not false','missingness':'terminal shrinkage is separated from unavailable raw bars; missing raw may be MNAR; no MAR claim','patternFamily':'canonical Pattern187 rebuilt at saved decision NOW only; family numerical means heterogeneous-unit descriptive summaries, not tradable scores'},'limitations':['Outcome-defined groups are evaluator-only and observational, not causal effect estimates','Across-policy observations repeat opportunities; report unique counts; no independent-sample inference','Post-Entry best High is not an executable fill','Volume availability is observed liquidity proxy, not bid/ask spread/depth','Classification AUC uses only complete windows, hence selected label-available subset; not utility performance','Gen3 label support not measured before its separate freeze; future support gate must fail closed, never adapt']})
 return summary
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--core',type=Path,required=True);ap.add_argument('--gen2',type=Path,required=True);ap.add_argument('--gen1',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();print(json.dumps(run(a.core,a.gen2,a.gen1,a.out),indent=2))
