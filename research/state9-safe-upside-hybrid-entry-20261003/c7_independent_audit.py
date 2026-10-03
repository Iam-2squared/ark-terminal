"""Independent originals/OOF arithmetic audit. Never imports main fit/label helpers.

No model fit, threshold tuning, bootstrap, provider call or policy runner.
Threshold verification activates ALL OOF candidate scores in descending order,
an alternative route to the main prefix-record-high forward scanner.
Predictions are independently reproduced by dense coefficient arithmetic from
the frozen original feature arrays and exported train-only preprocessing.
"""
import argparse
import bisect
import collections
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import warnings
import zipfile
import numpy as np

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
SUB=REPO/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
GEOM=REPO/'research/entry-geometry-capture-baseline-20261002'
KNOWN={'UP_FIRST','DOWN_FIRST','NEITHER'}
FAMILIES=('H0','H1','H2')
COUNTS=collections.Counter();MAXERR=0.
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def lines(p):
 for s in gzip.open(p,'rt'):yield json.loads(s)
def clock(day,a,b):
 end=900 if day<'2024-11-05' else 925
 am=max(0,min(b,690)-max(a,540));pm=max(0,min(b,end)-max(a,750))
 return am+pm
def equal(x,y,atol=1e-10,rtol=1e-11):
 if x is None or y is None:return x is y
 return math.isclose(float(x),float(y),abs_tol=atol,rel_tol=rtol)
def checked_hash(p,expected):
 assert sha(p)==expected,('SOURCE_IDENTITY_MISMATCH',str(p));COUNTS['source_hash_checks']+=1

def load_originals(archive,h0_path):
 checked_hash(archive,'33a0f64d48d25701215dadb82b9769a9c3bde2b9fec3d82d9879706f8f90e1a0')
 with zipfile.ZipFile(archive) as z:
  rb=z.read('all-material-r1/prefit/rows.json');assert hashlib.sha256(rb).hexdigest()=='54f7dbb8bd0c9f8974ccccb7a949c0b7ebf0bbe46581be7778f1607f9d9d8cb6'
  rows=json.loads(rb);folds=json.loads(z.read('all-material-r1/prefit/folds.json'));names=json.loads(z.read('all-material-r1/prefit/feature-names.json'))
 assert folds==read(HERE/'SPLIT_PRECOMMIT.json')['folds'];assert names==read(HERE/'R1_feature-names.json')
 assert len(rows)==149900 and len({r['id'] for r in rows})==149900
 freeze=read(HERE/'FEATURE_FAMILY_FREEZE.json');index={r['id']:i for i,r in enumerate(rows)}
 assert [n for n in names if not n.startswith(('STATE/','SIX/'))]==freeze['H0']
 for k in freeze['H0']+freeze['H1_numeric_added']+freeze['H1_categorical_added']+freeze['H2_added']:
  assert not any(s in k.lower() for s in ('future','winner','capture','first_passage','selectoroutcome','mfeend','returnend','session_terminal')),'FORBIDDEN_FEATURE_KEY'
 assert len(freeze['H0'])==480 and len(freeze['H1_numeric_added'])==33 and len(freeze['H1_categorical_added'])==11
 numkeys=freeze['H1_numeric_added']+freeze['H2_numeric'];catkeys=freeze['H1_categorical_added']+freeze['H2_categorical']
 num=np.full((len(rows),len(numkeys)),np.nan);cat=np.empty((len(rows),len(catkeys)),dtype=object)
 sampleoids=set(read(HERE/'C1_CONNECTION_AUDIT.json')['sampled_opportunities']);samples={};seen=set()
 for s in lines(HERE/'CAUSAL_STATE_CANDIDATE_ROWS.jsonl.gz'):
  i=index[s['row_id']];r=rows[i];assert i not in seen;seen.add(i)
  assert s['opportunity']==r['opportunity'] and s['session']==r['session'] and s['intent_minute']==r['minute']
  assert r['computedThroughMinute'] is None or r['computedThroughMinute']<r['minute']
  assert s['state_as_of_minute'] is None or s['state_as_of_minute']<=r['minute']
  assert s['feature_max_current_bar_end'] is None or s['feature_max_current_bar_end']<=r['minute']
  assert s['previous_source_date'] is None or s['previous_source_date']<r['session']
  assert set(s['H1'])==set(freeze['H1_numeric_added']+freeze['H1_categorical_added'])
  assert set(s['H2'])==set(freeze['H2_added'])
  for j,k in enumerate(numkeys):
   v=s['H1'].get(k) if j<33 else s['H2'].get(k)
   if v is not None:num[i,j]=float(v)
  for j,k in enumerate(catkeys):
   v=s['H1'].get(k) if j<11 else s['H2'].get(k);cat[i,j]='__MISSING__' if v is None else str(v)
  if r['opportunity'] in sampleoids:samples[r['id']]=s
  COUNTS['all_row_causal_cutoff_checks']+=1
 assert len(seen)==149900
 labels={}
 for x in lines(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz'):
  i=index[x['row_id']];assert i not in labels
  labels[i]=dict(status=x['primary_status'],fill_id=x['fill_id'],fill_minute=x['fill_minute'],price=x['fill_price'],primary=x['grid']['+2/-1'])
 assert len(labels)==149900
 checked_hash(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz',read(HERE/'C4_INDEPENDENT_LABEL_AUDIT.json')['labels_sha256'])
 assert read(HERE/'C4_INDEPENDENT_LABEL_AUDIT.json')['mismatch_count']==0
 checked_hash(h0_path,read(HERE/'H0_SAVED_FEATURE_JOIN_RECEIPT.json')['matrix_sha256'])
 return rows,folds,freeze,index,np.load(h0_path,mmap_mode='r',allow_pickle=False),num,cat,labels,samples

def audit_h0_original_matrix(rows,h0):
 source=read(SUB/'rows.json.gz');manifest=read(SUB/'manifest.json');raw=read(SUB/'raw-paths-evaluator-only.json.gz')
 offsets=collections.defaultdict(int);position={}
 for r in source:
  d=r['session'];position[r['id']]=(d,offsets[d],r);offsets[d]+=1
 byday=collections.defaultdict(list)
 for i,r in enumerate(rows):byday[r['session']].append(i)
 for di,(day,ix) in enumerate(sorted(byday.items())):
  file=SUB/(day+'.npy.gz');checked_hash(file,manifest[file.name])
  with gzip.open(file,'rb') as f:matrix=np.load(f,allow_pickle=False)
  jj=[]
  for i in ix:
   r=rows[i];d,j,s=position[r['id']];assert d==day
   assert all(r[k]==s[k] for k in ('opportunity','minute','delay','quoteAvailable','computedThroughMinute'))
   jj.append(j)
  want=matrix[jj].astype(np.float64);actual=np.asarray(h0[ix,:476]);assert np.array_equal(actual,want,equal_nan=True)
  COUNTS['H0_saved_original_cell_checks']+=want.size
  for i in ix:
   r=rows[i];bars=raw[r['opportunity']]['today'];times=[b[0] for b in bars];pos=bisect.bisect_left(times,r['minute'])
   latest=bars[pos-1] if pos else None;assert latest is None or latest[0]==r['computedThroughMinute']
   m=r['minute'];want=[m-540 if m<=690 else 150+m-750,float(m>=750),float(m in (690,750,751)),math.log(float(latest[4])) if latest else float('nan')]
   assert np.allclose(h0[i,476:],want,atol=1e-12,rtol=1e-12,equal_nan=True)
   COUNTS['H0_causal_context_cell_checks']+=4
  if di%30==0:print(json.dumps({'independent_H0_days_verified':di+1}),flush=True)
 return raw

def identity_history_audit(rows,samples,sources_path):
 identity=read(HERE/'STATE9_FINAL_IDENTITY.json')
 names={'RC2_CONTRACT.txt':'contract_sha256','profile.json':'profile_sha256','M0.md':'M0_sha256','source_snapshot.json':'source_snapshot_sha256','STATE_PATH_CONTRACT_V1.md':'path_contract_sha256','STATE9_RC2_SEMANTIC_FREEZE_RECEIPT.json':'semantic_freeze_receipt_sha256'}
 for f,k in names.items():checked_hash(HERE/'FROZEN_PUBLIC_INPUTS'/f,identity[k])
 for s in identity['source_files']:checked_hash(HERE/'FROZEN_RC2_SOURCE'/s['path'],s['sha256'])
 assert (identity['reviewed_N'],identity['agreement_N'],identity['observed_primary_N'],identity['coverage'])==(29,29,18,9)
 checked_hash(sources_path,read(HERE/'ORIGINAL_SAVED_SOURCE_PROOF.json')['private_source_sha256'])
 sys.path.insert(0,str(HERE/'FROZEN_RC2_SOURCE'))
 from independent.api import Engine
 from PATH_FROZEN import PathBuilder
 from CAUSAL_FEATURE_BUILDER import FeatureBuilder
 from input_gate import scheduled_minutes
 import normalize120
 source=read(sources_path);profile=read(HERE/'FROZEN_PUBLIC_INPUTS/profile.json');schema=read(HERE/'FROZEN_RC2_SOURCE/FEATURE_SCHEMA_V2.json')
 by=collections.defaultdict(list)
 for k in samples:by[samples[k]['opportunity']].append(k)
 for oi,(oid,keys) in enumerate(by.items()):
  saved=source[oid];day=saved['session'];last=max(samples[k]['intent_minute'] for k in keys)
  raw=[x for x in saved['current_prefix'] if int(x['Time'][:2])*60+int(x['Time'][3:])+1<=last]
  norm=normalize120.regenerate(saved['previous'],raw)
  mapped={int(x['Time'][:2])*60+int(x['Time'][3:])+1:(x,c) for x,c in zip(raw,norm['coordinates'])}
  engine=Engine(profile);path=PathBuilder(oid);fb=FeatureBuilder(schema);snapshot={samples[k]['intent_minute']:samples[k] for k in keys}
  observed_start=None;last_change=None;sequence=[];transitions=[];segment=None;first_am=first_pm=None
  for end in (t for t in scheduled_minutes(day) if t<=last):
   entry=None;source_status='MISSING_RAW_SOURCE';t=end-540
   if end in mapped:
    r,c=mapped[end];m=end-1;terminal=m in (690,900 if day<'2024-11-05' else 930)
    if not terminal and m<690 and first_am is None:first_am=m
    if not terminal and m>=750 and first_pm is None:first_pm=m
    auction='TERMINAL_AUCTION_MINUTE' if terminal else 'OPENING_MIXED_MINUTE' if m in (first_am,first_pm) else 'CONTINUOUS'
    entry=dict(t=t,known_at=t,source='JQUANTS_V2_EQUITIES_BARS_MINUTE',auction=auction,**{k.lower():v for k,v in c.items()});source_status='RAW_CLOSED_AT_ASSUMED_BAR_END'
   state=engine.step(t,entry,oid);before=len(path.events)
   ep=path.push(state,dict(scheduled_t=t,bar_end=f'{day}T{end//60:02d}:{end%60:02d}:00+09:00',row_status=source_status))
   events=path.events[before:];features=fb.push(state,ep,events,path.runs);formal=ep['Primary_or_null']
   lost=ep['causal_segment_id']!=segment or formal is None or any(e['event_type'] in ('SEGMENT_BREAK','OBSERVATION_LOST') for e in events)
   if lost:observed_start=last_change=None;sequence=[];transitions=[]
   segment=ep['causal_segment_id']
   if formal is not None:
    if observed_start is None:observed_start=end
    for event in events:
     if event['event_type']=='TRANSITION':transitions.append(end);last_change=end
    if not sequence or sequence[-1]!=formal:sequence.append(formal)
   if end in snapshot:
    expected=snapshot[end];unknown='__UNKNOWN_HISTORY__'
    h=dict(previous_distinct_formal_primary=sequence[-2] if len(sequence)>1 else unknown,previous_to_current_pair='>'.join(sequence[-2:]) if len(sequence)>1 else unknown,
     current_state_active_dwell=clock(day,ep['entered_at']+540,end) if formal is not None else None,
     active_time_since_last_primary_change=clock(day,last_change,end) if last_change is not None else None,
     last3_distinct_primary_sequence='>'.join(sequence[-3:]) if len(sequence)>=3 else unknown)
    for w in (5,10,15):h[f'transition_count_last{w}active']=sum(0<=clock(day,v,end)<w for v in transitions) if observed_start is not None and clock(day,observed_start,end)>=w else None
    assert h==expected['H2'],('INDEPENDENT_HISTORY_MISMATCH',oid,end)
    assert expected['H1']=={k:features[k] for k in schema['numeric_state']+schema['categorical_state']}
    COUNTS['independent_H1_H2_snapshot_checks']+=1
   COUNTS['independent_RC2_public_Path_steps']+=1
  print(json.dumps({'independent_RC2_history_opportunities':oi+1}),flush=True)

def prediction_audit(rows,folds,index,h0,num,cat,labels):
 ledger=read(HERE/'MODEL_FIT_LEDGER.json');assert ledger['started_fits']==ledger['completed_fits']==60 and len(ledger['fits'])==60
 fits={x['fit_id']:x for x in ledger['fits']};pred=collections.defaultdict(list);inner=collections.defaultdict(list);outer={f:[] for f in FAMILIES}
 session=np.array([r['session'] for r in rows])
 for fam in FAMILIES:
  for kind in ('INNER_OOF','OOF'):
   seen=collections.defaultdict(set)
   for r in lines(HERE/f'{kind}_{fam}.jsonl.gz'):
    i=index[r['row_id']];model=fits[r['model_fit_id']];assert model['family']==fam
    assert r['session']==rows[i]['session'] and r['opportunity']==rows[i]['opportunity'] and r['intent_minute']==rows[i]['minute']
    assert r['max_training_session']==max(model['training_sessions'])<r['session']
    assert not r['score_is_probability'];assert i not in seen[r['model_fit_id']];seen[r['model_fit_id']].add(i)
    item=(i,float(r['raw_score']));pred[r['model_fit_id']].append(item)
    if kind=='INNER_OOF':inner[(r['outer_fold'],fam)].append(item)
    else:outer[fam].append((i,float(r['raw_score']),r['outer_fold']))
   if kind=='OOF':assert len(outer[fam])==65312 and len({v[0] for v in outer[fam]})==65312
 for fit_id,model in sorted(fits.items()):
  f=next(x for x in folds if x['id']==model['outer_fold']);spec=next(x for x in f['inner'] if x['id']==model['inner_fold']) if model['role']=='inner' else f
  scoring=spec['validation'] if model['role']=='inner' else spec['test'];train=np.array([i for i,r in enumerate(rows) if r['session'] in spec['train'] and labels[i]['status'] in KNOWN])
  wanted=np.flatnonzero(np.isin(session,scoring));items=pred[fit_id]
  assert [i for i,s in items]==wanted.tolist();assert max(spec['train'])<min(scoring)
  assert not {rows[i]['opportunity'] for i in train}&{rows[i]['opportunity'] for i in wanted}
  if spec.get('purge'):assert spec['purge'] not in spec['train'] and spec['purge'] not in scoring
  cc=collections.Counter(rows[i]['opportunity'] for i in train);w=np.array([1/cc[rows[i]['opportunity']] for i in train])
  assert equal(w.sum(),len(cc)) and equal(model['weight_sum'],len(cc))
  assert model['training_rows']==len(train) and model['training_opportunities']==len(cc)
  assert model['preprocessing_fit_rows_sha256']==hashlib.sha256('\n'.join(rows[i]['id'] for i in train).encode()).hexdigest()
  COUNTS['opportunity_weight_checks']+=len(cc);COUNTS['temporal_model_split_checks']+=1
  fam=model['family'];D=480 if fam=='H0' else 513 if fam=='H1' else 518;cats=cat[:,:0] if fam=='H0' else cat[:,:11] if fam=='H1' else cat
  def numeric(ix):return np.asarray(h0[ix]) if fam=='H0' else np.column_stack((h0[ix],num[ix,:D-480]))
  saved=HERE/model['model_arithmetic_path'];checked_hash(saved,model['model_arithmetic_sha256'])
  with np.load(saved,allow_pickle=False) as z:med=z['median'];mean=z['mean'];std=z['std'];allmissing=z['all_missing'];coef=z['coef'];intercept=float(z['intercept'][0]);categories=json.loads(str(z['categories_json']));classes=z['classes']
  assert classes.tolist()==[0,1] and len(med)==D and len(categories)==cats.shape[1]
  tr=numeric(train)
  for j in range(D):
   col=tr[:,j];known=col[np.isfinite(col)];middle=float(np.median(known)) if len(known) else 0.
   assert bool(allmissing[j])==(len(known)==0) and equal(med[j],middle)
   clean=np.where(np.isfinite(col),col,middle);avg=float(clean.sum()/len(clean));sd=float(np.sqrt(np.mean((clean-avg)**2)));sd=sd if sd else 1.
   assert equal(mean[j],avg,atol=1e-8,rtol=1e-11) and equal(std[j],sd,atol=1e-8,rtol=1e-11),('TRAIN_ONLY_PREPROCESSING_MISMATCH',fit_id,j)
   COUNTS['train_only_numeric_preprocessing_checks']+=1
  del tr
  for j,values in enumerate(categories):assert values==sorted(set(cats[train,j]));COUNTS['train_only_categorical_checks']+=1
  global MAXERR
  for begin in range(0,len(items),4000):
   chunk=items[begin:begin+4000];ix=np.array([v[0] for v in chunk]);source=numeric(ix);missing=~np.isfinite(source)
   score=((np.where(missing,med,source)-mean)/std).dot(coef[:D])+missing.dot(coef[D:2*D])+intercept
   offset=2*D
   for j,values in enumerate(categories):
    mapping={v:coef[offset+k] for k,v in enumerate(values)};score+=np.array([mapping.get(v,0.) for v in cats[ix,j]]);offset+=len(values)
   assert offset==len(coef)
   wanted=np.array([v[1] for v in chunk]);error=np.abs(score-wanted);MAXERR=max(MAXERR,float(error.max(initial=0)))
   assert np.all(error<=1e-8+1e-11*np.abs(wanted)),('OOF_DENSE_SCORE_MISMATCH',fit_id)
   COUNTS['independent_OOF_score_checks']+=len(ix)
  print(json.dumps({'independent_model_arithmetic_verified':fit_id,'new_fits':0}),flush=True)
 return inner,outer

def threshold_audit(rows,labels,inner):
 receipt=read(HERE/'THRESHOLD_SELECTION_RECEIPT.json');curves=collections.defaultdict(dict)
 for p in lines(HERE/'THRESHOLD_CURVES.jsonl.gz'):curves[(p['outer_fold'],p['family'])][p['threshold']]=p
 audited={}
 for key,items in sorted(inner.items()):
  events=collections.defaultdict(list);expected=curves[key];N=len({rows[i]['opportunity'] for i,s in items})
  assert len({i for i,s in items})==len(items)
  for i,s in items:events[s].append(i)
  timelines=collections.defaultdict(list)
  for i,s in items:timelines[rows[i]['opportunity']].append((rows[i]['minute'],s))
  contract_boundaries=set()
  for seq in timelines.values():
   previous=-math.inf
   for minute,s in sorted(seq):
    if s>previous:contract_boundaries.add(s);previous=s
  contract_boundaries.add(float(np.nextafter(min(contract_boundaries),-np.inf)))
  assert contract_boundaries==set(expected),'THRESHOLD_BOUNDARY_CONTRACT_MISMATCH'
  selected={};c=collections.Counter();sessions=collections.Counter();filled=0;verified=0;best={str(t):None for t in (.9,.85,.8)}
  def change(i,sign):
   nonlocal filled
   x=labels[i];c[x['status']]+=sign
   if x['fill_id'] is not None:filled+=sign
   if x['status'] in KNOWN:sessions[rows[i]['session']]+=sign
  def inspect(t):
   nonlocal verified
   if t not in expected:return
   p=expected[t];k=sum(c[s] for s in KNOWN);ses=sum(v>0 for v in sessions.values());prec=c['UP_FIRST']/k if k else None;down=c['DOWN_FIRST']/k if k else None
   assert p['opportunities']==N and p['selected_N']==len(selected) and p['filled_N']==filled and p['evaluable_N']==k and p['represented_evaluable_sessions']==ses
   for s in ('UP_FIRST','DOWN_FIRST','NEITHER','ORDER_UNKNOWN','DATA_UNAVAILABLE'):assert p[s]==c[s],('INDEPENDENT_THRESHOLD_COUNT_MISMATCH',key,t,s)
   assert equal(p['precision'],prec) and equal(p['DOWN_FIRST_rate'],down) and equal(p['coverage'],len(selected)/N)
   assert p['support_pass']==(k>=100 and ses>=10)
   for target in (.9,.85,.8):
    if k>=100 and ses>=10 and prec>=target and down<=.1:
     old=best[str(target)];metric=(len(selected),-down,-(1-len(selected)/N),t)
     if old is None or metric>old[0]:best[str(target)]=(metric,t)
   verified+=1;COUNTS['independent_threshold_boundary_checks']+=1
  # The initial contract cut is below the minimum prefix-record score, not
  # necessarily below the minimum of ALL later candidate scores. Query it at
  # its actual place in the descending activation schedule.
  for t in sorted(set(events)|contract_boundaries,reverse=True):
   inspect(t)
   for i in events.get(t,[]):
    oid=rows[i]['opportunity'];old=selected.get(oid)
    if old is None or rows[i]['minute']<rows[old]['minute']:
     if old is not None:change(old,-1)
     selected[oid]=i;change(i,1)
  assert verified==len(expected),('THRESHOLD_BOUNDARY_COVERAGE',key,verified,len(expected))
  declared=next(x for x in receipt['family_selections'] if (x['outer_fold'],x['family'])==key)
  for t in (.9,.85,.8):
   actual=best[str(t)];given=declared['targets'][str(t)];assert (actual is None)==(given is None)
   if actual is not None:assert actual[1]==given['threshold']
  chosen=next((declared['targets'][str(t)] for t in (.9,.85,.8) if declared['targets'][str(t)] is not None),None)
  assert chosen==declared['selected_operating_point'];assert not declared['outer_labels_used']
  audited[key]=chosen
  print(json.dumps({'independent_threshold_fold':key[0],'family':key[1],'points_verified':verified}),flush=True)
 assert COUNTS['independent_threshold_boundary_checks']==130249
 return audited,receipt

def own_metrics(items,labels,rows):
 a=[(i,s) for i,s,*rest in items if labels[i]['status'] in KNOWN];counts=collections.Counter(rows[i]['opportunity'] for i,s in a)
 groups=collections.defaultdict(lambda:[0.,0.]);brier=loss=weight=0.
 for i,s in a:
  w=1/counts[rows[i]['opportunity']];y=int(labels[i]['status']=='UP_FIRST');e=math.exp(-abs(s));p=1/(1+e) if s>=0 else e/(1+e)
  groups[s][0 if y else 1]+=w;weight+=w;brier+=w*(p-y)**2;loss+=w*(max(s,0)+math.log1p(e)-y*s)
 P=sum(v[0] for v in groups.values());Q=sum(v[1] for v in groups.values());wins=neg=0.
 for s,(p,n) in sorted(groups.items()):wins+=p*(neg+n/2);neg+=n
 cp=cn=AP=area=0.;prev_precision=1.;prev_recall=0.
 for s,(p,n) in sorted(groups.items(),reverse=True):
  cp+=p;cn+=n;prec=cp/(cp+cn);recall=cp/P;AP+=(p/P)*prec;area+=(recall-prev_recall)*(prec+prev_precision)/2;prev_recall=recall;prev_precision=prec
 return dict(PR_AUC_AP=AP,PR_AUC_trapezoid=area,ROC_AUC=wins/(P*Q),Brier=brier/weight,LogLoss=loss/weight,weighted_prevalence=P/weight)

def decimal_primary(day,m,p0,path,full):
 last=900 if day<'2024-11-05' else 925;terminal=900 if day<'2024-11-05' else 930
 schedule=[t for t in list(range(540,690))+[690]+list(range(750,last))+[terminal] if t>=m]
 bars={int(b[0]):b for b in path['today']};high=Decimal(str(p0))*Decimal('1.02');low=Decimal(str(p0))*Decimal('0.99')
 for t in schedule:
  if t not in bars:return 'DATA_UNAVAILABLE',None
  b=bars[t];o,h,l=map(lambda x:Decimal(str(x)),b[1:4]);COUNTS['baseline_primary_OHLC_bar_checks']+=1
  if o>=high:return 'UP_FIRST',t
  if o<=low:return 'DOWN_FIRST',t
  if h>=high and l<=low:return 'ORDER_UNKNOWN',t
  if h>=high:return 'UP_FIRST',t
  if l<=low:return 'DOWN_FIRST',t
 return ('NEITHER' if full=='AVAILABLE' else 'DATA_UNAVAILABLE'),None

def policies_evaluation_audit(rows,index,labels,outer,operating,selection,raw):
 canonical=read(REPO/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz');canon={r['opportunity']:r for r in canonical}
 den={str(t):sum((r.get('selectorOutcome') or {}).get('mfeEnd') is not None and Decimal(str(r['selectorOutcome']['mfeEnd']))>=t for r in canonical) for t in range(1,6)}
 assert list(den.values())==[1496,1054,761,544,408];COUNTS['capture_denominator_checks']+=5
 choices={}
 for fold in range(1,6):
  choose=None
  for target in (.9,.85,.8):
   options=[x for x in selection['family_selections'] if x['outer_fold']==fold and x['targets'][str(target)] is not None]
   if options:
    choose=min(options,key=lambda x:(-x['targets'][str(target)]['selected_N'],x['targets'][str(target)]['DOWN_FIRST_rate'],x['targets'][str(target)]['no_entry_rate'],FAMILIES.index(x['family'])))
    choose=(choose['family'],choose['targets'][str(target)]);break
  choices[fold]=choose
  declared=next(x for x in selection['fold_selected_candidate'] if x['outer_fold']==fold)
  assert declared['selected_family']==(choose[0] if choose else None) and declared['selected_operating_point']==(choose[1] if choose else None)
 records={ (x['arm'],x['opportunity']):x for x in lines(HERE/'ENTRY_CANDIDATE_RECORDS.jsonl.gz')}
 assert len(records)==8620
 for fam,items in outer.items():
  by=collections.defaultdict(list)
  for i,s,f in items:by[(f,rows[i]['opportunity'])].append((i,s))
  for (fold,oid),values in by.items():
   op=operating[(fold,fam)];earliest=None
   if op:
    eligible=[(i,s) for i,s in values if s>op['threshold']]
    if eligible:earliest=min(eligible,key=lambda x:rows[x[0]]['minute'])
   actual=records[(fam,oid)]
   assert actual['intent_row_id']==(rows[earliest[0]]['id'] if earliest else None)
   assert actual['status']==('BUY_INTENT' if earliest else 'NO_HIGH_CONFIDENCE_ENTRY') and not actual['forced_fallback'] and not actual['score_is_probability']
   assert actual['threshold']==(op['threshold'] if op else None)
   selected=records[('SELECTED_DEVELOPMENT',oid)];choice=choices[fold]
   if choice is None:assert selected['intent_row_id'] is None and selected['selected_family'] is None and not selected['forced_fallback']
   elif choice[0]==fam:assert selected['intent_row_id']==actual['intent_row_id'] and selected['selected_family']==fam
   COUNTS['first_cross_policy_record_checks']+=1
 evaluated={};byarm=collections.defaultdict(list)
 for r in lines(HERE/'C6_EVALUATED_ENTRY_RECORDS.jsonl.gz'):evaluated[(r['arm'],r['opportunity'])]=r;byarm[r['arm']].append(r)
 evaluation=read(HERE/'ENTRY_EVALUATION.json');incremental=read(HERE/'STATE_INCREMENTAL_VALUE.json')
 for arm,rs in byarm.items():
  assert len(rs)==2155 and {r['opportunity'] for r in rs}==set(canon);c=collections.Counter()
  for r in rs:
   if arm in ('IMMEDIATE','R1') and r['filled']:
    old=r['quality'];p=r['primary'];status,touch=decimal_primary(r['session'],r['fill_minute'],r['fill_price'],raw[r['opportunity']], 'AVAILABLE' if old['session_end_MFE_pct'] is not None else None)
    assert status==r['primary_status'] and touch==p['first_touch_bar_start']
    COUNTS['independent_baseline_fill_primary_checks']+=1
   if arm in FAMILIES or arm=='SELECTED_DEVELOPMENT':
    original=records[(arm,r['opportunity'])];intent=original['intent_row_id'];x=labels[index[intent]] if intent else None
    fill=x is not None and x['fill_id'] is not None;assert r['filled']==fill
    assert r['primary_status']==(x['status'] if fill else 'NO_ENTRY')
   if r['filled']:c[r['primary_status']]+=1
  declared=evaluation['arms'][arm]['safe_up'];filled=sum(c.values());known=sum(c[x] for x in KNOWN)
  assert declared['filled_N']==filled and declared['evaluable_N']==known and declared['no_entry_N']==2155-filled
  for x in ('UP_FIRST','DOWN_FIRST','NEITHER','ORDER_UNKNOWN','DATA_UNAVAILABLE'):assert declared[x+'_N']==c[x]
  assert equal(declared['conservative_success'],c['UP_FIRST']/filled if filled else None)
  assert equal(declared['evaluable_precision'],c['UP_FIRST']/known if known else None)
  if arm in ('IMMEDIATE','R1'):
   score=read(GEOM/f'FROZEN_ARTIFACT_MEMBERS/{arm}_SCORECARD.original.json.gz');assert evaluation['arms'][arm]['capture']==score['overall']['capture']
  else:
   for t in range(1,6):
    cc=collections.Counter()
    for r in rs:
     sel=canon[r['opportunity']]['selectorOutcome'].get('mfeEnd')
     if sel is None or sel<t:continue
     if not r['filled']:cc['noEntry']+=1
     else:
      mfe=r['quality']['session_end_MFE_pct'];cc['unknownEntered' if mfe is None else 'captured' if mfe>=t else 'belowThreshold']+=1
    d=evaluation['arms'][arm]['capture'][str(t)];assert d['selectorWinnerDenominator']==den[str(t)]
    for k in ('captured','noEntry','unknownEntered','belowThreshold'):assert d[k]==cc[k]
    assert sum(cc.values())==den[str(t)];COUNTS['new_arm_capture_checks']+=1
  COUNTS['evaluation_denominator_unknown_checks']+=1
 for f,items in outer.items():
  computed=own_metrics(items,labels,rows)
  for k,v in computed.items():assert equal(v,incremental['pooled'][f][k],atol=1e-10,rtol=1e-10),('INDEPENDENT_METRIC_ARITHMETIC_MISMATCH',f,k)
  COUNTS['independent_metric_checks']+=len(computed)
 assert clock('2025-07-01',690,750)==0 and clock('2025-07-01',680,760)==20 and clock('2025-07-01',689,750)==1
 COUNTS['lunch_clock_boundary_checks']+=3

def run(archive,h0,sources):
 rows,folds,freeze,index,base,num,cat,labels,samples=load_originals(archive,h0)
 raw=audit_h0_original_matrix(rows,base)
 inner,outer=prediction_audit(rows,folds,index,base,num,cat,labels)
 operating,selection=threshold_audit(rows,labels,inner)
 policies_evaluation_audit(rows,index,labels,outer,operating,selection,raw)
 identity_history_audit(rows,samples,sources)
 report=dict(status='SAFE_UPSIDE_ENTRY_INDEPENDENT_AUDIT_PASS',gate='PASS',mismatch_count=0,checks=dict(COUNTS),
  max_independent_dense_score_absolute_error=MAXERR,OOF_score_tolerance='1e-8 absolute + 1e-11*abs(score)',
  main_model_helper_imported=False,main_label_helper_imported=False,new_model_fits=0,threshold_tuning=0,bootstrap_draws=0,provider_requests=0,orders=0,
  primary='SAFE_UP_2_BEFORE_DOWN_1',future_feature_inputs=0,old_State_substitutions=0,forced_fallbacks=0,
  original_candidate_first_passage_audit=read(HERE/'C4_INDEPENDENT_LABEL_AUDIT.json'),
  evidence_scope='All149900 causal row cutoffs and exact H0 source matrix; all60 preprocessing/split/weight/1,208,796 prediction scores; all130249 threshold points via descending activation; all8620 policy records; all3848 baseline fill Primary and six-arm denominators/capture; independent frozen RC2/public Path/H1/H2 on preselected12 full prefixes.',
  caveats=['Candidate first-passage labels inherit missing expected raw-minute UNKNOWN semantics; this is not a full-source coverage or live received_at certificate.','RC2 independent arithmetic shares Python Decimal; finite source-identity checks are not an exact-log proof.','No performance-significance gate or fresh validation inferred from arithmetic PASS.'],
  source_archive_sha256=sha(archive),H0_matrix_sha256=sha(h0),RC2_contract_sha256=read(HERE/'STATE9_FINAL_IDENTITY.json')['contract_sha256'],
  model_fits_total=60,fit_hard_cap=72,productionReady=False,automaticPromotionAllowed=False)
 (HERE/'INDEPENDENT_AUDIT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('original_candidate_first_passage_audit','caveats')},ensure_ascii=False),flush=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--r1-archive',required=True);ap.add_argument('--h0',required=True);ap.add_argument('--sources',required=True);a=ap.parse_args()
 try:run(a.r1_archive,a.h0,a.sources)
 except Exception as e:
  receipt=dict(status='SAFE_UPSIDE_ENTRY_INDEPENDENT_AUDIT_INCOMPLETE',error_type=type(e).__name__,error=str(e),completed_checks=dict(COUNTS),new_model_fits=0,threshold_tuning=0,bootstrap_draws=0)
  (HERE/'C7_AUDIT_ATTEMPT_FAILURE.json').write_text(json.dumps(receipt,indent=2)+'\n');raise
