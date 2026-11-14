"""Separate arithmetic/state-machine audit. Imports no study calculation code; fit=0.

Uses the frozen independent RC2 API and normalization120, independently extracts
numeric/history fields, and independently reconstructs teacher/score/first-entry.
Checks all grid, teacher and entry rows; model prediction audit is deterministic
sampled, with full-array percentile/threshold and train-preprocessing checks.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','8');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import ast,collections,datetime,gzip,hashlib,json,math,pickle,sys,time
from functools import lru_cache
from decimal import Decimal,localcontext,Context,ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=HERE.parents[2];SCRATCH=ROOT.parent;INPUT=SCRATCH/'persistent_sources';OLD=ROOT/'research/state9-safe-upside-hybrid-entry-20261003'
class TrainPreprocessor:pass # pickle metadata only; transform is independently implemented below
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def rows(p):
 with gzip.open(p,'rt') as f:
  for s in f:yield json.loads(s)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_npz(p):
 with np.load(p) as n:return {k:n[k] for k in n.files}
@lru_cache(None)
def reg(d):return list(range(540,690))+list(range(750,900 if d<'2024-11-05' else 925))
def close(d):return 900 if d<'2024-11-05' else 930
@lru_cache(None)
def schedule(d):return sorted(reg(d)+[690,close(d)])
def active(d,a,b):return sum(max(0,min(b,y)-max(a,x)) for x,y in [(540,690),(750,900 if d<'2024-11-05' else 925)])
def good(x):return len(x)==7 and all(math.isfinite(float(v)) for v in x) and x[3]>0 and x[3]<=min(x[1],x[4])<=max(x[1],x[4])<=x[2] and x[5]>=0 and x[6]>=0
def valid(a):return np.asarray([x for x in a if good(x)],float).reshape(-1,7)
def fill(d,a,t):
 for x in a:
  if x[0]>=t and int(x[0]) in reg(d) and int(x[0]) not in [540,750]:return int(x[0]),float(x[1]*1.0005)
 return None
checks=collections.Counter();failure_counts=collections.Counter();mismatches=[]
def check(name,ok,detail=None):
 checks[name]+=1
 if not ok:
  failure_counts[name]+=1
  if len(mismatches)<100:mismatches.append({'check':name,'detail':detail})
def same(a,b,tol=1e-8):
 if a is None or b is None:return a is b
 return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=tol
def expected_teacher(d,a,minute,price):
 a=a[np.isin(a[:,0],schedule(d))]
 future=a[a[:,0]>minute]
 if not len(future):return {'remaining_upside_pct':None,'U_target':None,'Q_target':None,'D_target':None,'peak_minute':None,'first_upside':{str(k):'UNKNOWN' for k in range(1,6)}}
 high=float(max(future[:,2]));peak=next(x for x in future if x[2]==high);path=a[(a[:,0]>=minute)&(a[:,0]<=peak[0])];expected=[m for m in schedule(d) if minute<=m<=peak[0]];complete=list(path[:,0])==expected
 tv=0.;last=price;sg=[]
 for x in path:
  delta=x[4]-last;tv+=abs(delta);last=x[4]
  if delta:sg.append(1 if delta>0 else -1)
 tv=tv*100/price;net=100*(peak[4]/price-1);q=min(1.,max(0.,net)/tv) if tv else 0.;mae=abs(min(0.,100*(min(path[:,3])/price-1)));up=100*(high/price-1);remaining=a[a[:,0]>=minute];full=list(remaining[:,0])==[m for m in schedule(d) if m>=minute]
 hits={}
 for k in range(1,6):hits[str(k)]='HIT_CONFIRMED' if any(x[2]>=price*(1+k/100) for x in future) else 'NO_HIT_CONFIRMED' if full else 'UNKNOWN'
 return {'remaining_upside_pct':float(up),'U_target':min(10.,max(0.,up)),'Q_target':q if complete else None,'D_target':min(5.,mae) if complete else None,'peak_minute':int(peak[0]),'peak_bar_close':float(peak[4]),'total_variation_pct':tv if complete else None,'path_efficiency':q if complete else None,'pre_peak_mae_abs_pct':mae if complete else None,'pre_peak_path_complete':complete,'remaining_source_complete':full,'reversal_count':sum(a!=b for a,b in zip(sg,sg[1:])) if complete else None,'time_to_peak_active_min':active(d,minute,int(peak[0])),'first_upside':hits}
def preprocess(prep,num,cat):
 miss=~np.isfinite(num);A=np.concatenate([np.where(miss,prep.median,num),miss.astype(float)],axis=1)
 if cat is not None:
  allcols=[]
  for j,known in enumerate(prep.known):
   mapping={int(c):k for k,c in enumerate(known)};one=np.zeros((len(cat),len(known)+1))
   for i,c in enumerate(cat[:,j]):one[i,mapping.get(int(c),len(known))]=1.
   allcols.append(one)
  A=np.concatenate([A]+allcols,axis=1)
 return A
def state_numeric(state,t):
 def n(v):
  if v is None:return None
  if isinstance(v,dict):return float(Fraction(v['num'])/Fraction(v['den']))
  return float(Fraction(str(int(v) if isinstance(v,bool) else v)))
 def delta(a,b):return n(a)-n(b) if a is not None and b is not None else None
 st=state.get('stop') or {};bal=state.get('balance') or {};ra=state.get('range_analysis') or {};fa=state.get('fast_analysis') or {}
 z={'observed':int(state['current_semantics_observed']),'observed_age':None if state['observed_at'] is None else t-state['observed_at'],'local_direction':n(state['leg_direction']),'context_direction':n(state['context']),'fast':n(state['fast_flag']),'fast_applicable':n(state['fast_applicable_to_primary']),'close_u':n(state['close_u']),'stop_direction':n(st.get('direction')),'stop_width':delta(st.get('high'),st.get('low')),'stop_center_distance':delta(state['close_u'],st.get('center')),'stop_age':t-st['start'] if st else None,'stop_recognized_age':t-st['recognized_at'] if st else None,'stop_count':n(st.get('count')),'stop_progress_age':t-st['progress_at'] if st else None,'range_width':delta(bal.get('high'),bal.get('low')),'range_established_age':t-bal['established_at'] if bal else None,'range_exit_low_distance':delta(state['close_u'],bal.get('exit_low')),'range_exit_high_distance':delta(bal.get('exit_high'),state['close_u'])}
 for k in ['net','tv','span','width','eta','turns','guard']:z['range_analysis_'+k]=n(ra.get(k))
 for k in ['A','B','C','D']:z['range_'+k]=n((ra.get('conditions') or {}).get(k))
 for k in ['net','tv','eta','directional_net']:z['fast_analysis_'+k]=n(fa.get(k))
 return z
def audit_state(samples,ws,raw,X,C,vocab,metadata,features):
 sys.path.insert(0,str(OLD/'FROZEN_RC2_SOURCE'));from independent.api import Engine
 import normalize120
 profile=read(OLD/'FROZEN_PUBLIC_INPUTS/profile.json');tokens=read(SCRATCH/'private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz');ranges=np.load(HERE/'PRIVATE_INPUTS/watch_row_ranges.npy');seen=0
 for wi in samples:
  w=ws[wi];lo,hi=ranges[wi]
  if hi==lo or metadata[int(lo)]['source_status']!='SAVED_SOURCE_CONNECTED':continue
  s=tokens[w['watch_key']];b=normalize120.regenerate(s['previous'],[]);day=w['session'];today={int(x[0])+1:x for x in raw[w['watch_key']]['today']};am=min((int(x[0]) for x in raw[w['watch_key']]['today'] if x[0]<690),default=None);pm=min((int(x[0]) for x in raw[w['watch_key']]['today'] if 750<=x[0]<(900 if day<'2024-11-05' else 925)),default=None);eng=Engine(profile);by={metadata[i]['intent_minute']:i for i in range(int(lo),int(hi))};max_t=max(by);ends=sorted([m+1 for m in schedule(day) if m+1<=max_t]);cache={};accepted=None;pending=set();segment=0;last_end=None;prev_formal=None;prev_obs=False;prev_segment=0;entered=None;seq=[];changes=[];start=last_change=None
  for end in ends:
   t=end-540;x=today.get(end);tok=None
   if x is not None:
    auction='TERMINAL_AUCTION_MINUTE' if int(x[0]) in [690,close(day)] else 'OPENING_MIXED_MINUTE' if int(x[0]) in [am,pm] else 'CONTINUOUS'
    vals={}
    if good(x):
     for k,col in [('o',1),('h',2),('l',3),('c',4)]:
      lex=json.dumps(x[col])
      if lex not in cache:
       with localcontext(Context(prec=120,rounding=ROUND_HALF_EVEN,Emin=-999999,Emax=999999)):cache[lex]=format(((Decimal(lex).ln()-Decimal(b['P_ref']).ln())/Decimal(b['U'])).quantize(Decimal('1e-24')),'f')
      vals[k]=cache[lex]
    else:vals={k:'INVALID_RAW_PRICE' for k in 'ohlc'}
    tok={'t':t,'known_at':t,'source':'JQUANTS_V2_EQUITIES_BARS_MINUTE','auction':auction,**vals}
   st=eng.step(t,tok,w['watch_key']);meta=st['bar_metadata'] or {};status=st['numeric_status']
   if status=='ACCEPTED':
    reset=bool(pending) or accepted is not None and (t!=accepted['t']+1 or meta['source']!=accepted['source'] or meta['auction']!=accepted['auction']) or 'SEGMENT_RESET_NO_GAP_RETURN' in st['events']
    if accepted is None:segment=1
    elif reset:segment+=1
    accepted=meta.copy();pending.clear()
   else:pending.add(status)
   observed=st['current_semantics_observed'];formal=st['primary'] if observed else None;brk=last_end is not None and (end!=last_end+1 or (segment!=prev_segment and prev_segment!=0));connection=last_end is not None and not brk and prev_obs and observed and segment==prev_segment;transition=connection and prev_formal!=formal;hold=connection and prev_formal==formal
   if segment!=prev_segment or formal is None or brk or prev_obs and not observed:seq=[];changes=[];start=last_change=None
   if observed:
    if not hold:entered=end
    if start is None:start=end
    if transition:changes.append(end);last_change=end
    if not seq or seq[-1]!=formal:seq=(seq+[formal])[-3:]
   else:entered=None
   hist={'current_state_active_dwell':active(day,entered,end) if observed else None,'active_time_since_last_primary_change':active(day,last_change,end) if last_change is not None else None}
   for k in [5,10,20]:hist[f'transition_count_last{k}active']=sum(0<=active(day,c,end)<k for c in changes) if start is not None and active(day,start,end)>=k else None
   if end in by:
    i=by[end];z=state_numeric(st,t);z.update(hist);m=metadata[i]
    check('State timestamp independent kernel',m['state_as_of_minute']==end,(w['watch_key'],end));check('State formal/display/observed independent route',m['formal_primary']==formal and m['display_primary']==st['primary'] and m['observed']==observed,(w['watch_key'],end));check('State segment independent Path derivation',m['causal_segment_id']==w['watch_key']+':S%04d'%segment,(w['watch_key'],end))
    for j,name in enumerate(features['P1_numeric'][len(features['P0_numeric']):],len(features['P0_numeric'])):
     v=z[name.split('/',1)[1]];actual=None if not np.isfinite(X[i,j]) else float(X[i,j]);check('State exact numeric and history independent extraction',same(actual,v,1e-6),[w['watch_key'],end,name,actual,v])
    def cat(v):return '__MISSING__' if v is None else str(v)
    cats={'formal_primary':'__FORMAL_NULL__' if formal is None else formal,'display_primary':cat(st['primary']),'activity':cat(st['activity']),'basis':cat(st['basis']),'direction_basis':cat(st['direction_basis']),'numeric_status':cat(st['numeric_status']),'rejection_reason':cat(st['rejection_reason']),'auction':cat(meta.get('auction')),'source':cat(meta.get('source')),'source_events':'|'.join(sorted(st['events'])),'range_reason':cat((st.get('balance') or {}).get('reason')),'previous_distinct_formal_primary':seq[-2] if len(seq)>=2 else '__UNKNOWN_HISTORY__','previous_to_current_pair':'>'.join(seq[-2:]) if len(seq)>=2 else '__UNKNOWN_HISTORY__','last3_distinct_primary_sequence':'>'.join(seq) if len(seq)>=3 else '__UNKNOWN_HISTORY__','source_status':'SAVED_SOURCE_CONNECTED'}
    for j,name in enumerate(features['P1_categorical']):check('State categorical/history independent extraction',vocab[j][int(C[i,j])]==cats[name.split('/',1)[-1]],[w['watch_key'],end,name])
    seen+=1
   prev_segment=segment;prev_formal=formal;prev_obs=observed;last_end=end
 print(json.dumps({'audit_independent_state_rows':seen,'sample_watches':len(samples),'mismatches_so_far':len(mismatches)}),flush=True);return seen

def repair_scope_checks():
 receipt=read(HERE/'CORRECTED_TEACHER_FREEZE_RECEIPT.json');scope=read(HERE/'REPAIR_SCOPE_PRECOMMIT.json');ledger=read(HERE/'CORRECTED_FIT_LEDGER.json');oo=read(HERE/'CORRECTED_OOF_LINEAGE_RECEIPT.json');features=read(HERE/'FEATURE_FREEZE.json');identity=read(OLD/'STATE9_FINAL_IDENTITY.json')
 check('Primary Freeze target fixed before outcomes',scope['Primary_Freeze_Target']=='P1_Q70' and not scope['candidate_reselection_allowed'])
 check('incremental exactly20; historical30; cumulative50',ledger['fits_reserved']==ledger['fits_completed']==20 and ledger['incremental_hard_cap']==20 and ledger['historical_completed']==30 and ledger['cumulative_completed']==50)
 expected={(f,i,h) for f in ['P0','P1'] for i in range(1,6) for h in ['QUALITY','ADVERSE']}
 check('exact authorized20 family/fold/head keys',set((r['family'],r['fold'],r['head']) for r in ledger['runs'])==expected and all(r['status']=='COMPLETED' for r in ledger['runs']) and ledger['UPSIDE_refits']==0)
 source=ast.parse((BASE/'common.py').read_text());fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='source_starts')
 check('calendar correction is chronological sort only',ast.unparse(fn)=='def source_starts(day):\n    return sorted(regular_starts(day) + [690, close_minute(day)])')
 sessions={r['session'] for r in rows(HERE/'PERSISTENT_GRID.jsonl.gz')}
 for day in sessions:
  original=reg(day)+[690,close(day)];corrected=schedule(day)
  check('scheduled bar set before/after identical',set(original)==set(corrected) and len(original)==len(corrected),day)
  check('calendar chronological ordering',corrected==sorted(original) and all(a<b for a,b in zip(corrected,corrected[1:])),day)
 old=np.load(BASE/'PRIVATE_PREFIT_LINEAGE/targets.npy',mmap_mode='r');new=np.load(HERE/'PRIVATE_INPUTS/targets.npy',mmap_mode='r')
 check('full UPSIDE target/mask unchanged',np.array_equal(old[:,0],new[:,0],equal_nan=True))
 for h,head in [(1,'QUALITY'),(2,'ADVERSE')]:
  good=np.isfinite(old[:,h]);ngood=np.isfinite(new[:,h]);check('Q/D old finite values unchanged',np.array_equal(old[good,h],new[good,h]),head);check('Q/D NULL to known13948',int((~good&ngood).sum())==13948 and not(good&~ngood).any(),head)
 check('P0/P1 feature separation',features['P1_numeric'][:len(features['P0_numeric'])]==features['P0_numeric'] and features['P0_categorical']==[] and len(features['P1_numeric'])>len(features['P0_numeric']))
 check('Legacy State feature0',not any('legacy' in n.lower() or 'state-v3' in n.lower() for n in features['P1_numeric']+features['P1_categorical']))
 check('P1 exact final RC2 identity',features['state_identity']==identity)
 for name,expected_hash in receipt['frozen_hashes'].items():
  check('frozen source/contracts/grid/State unchanged',digest(BASE/name)==expected_hash,name)
  # The original historical ledger is frozen in BASE. HERE/FIT_LEDGER is the
  # deliberate active30-model view (10 reused U +20 corrected Q/D), independently
  # verified below and in the full model audit; it is not a frozen-input copy.
  if name!='FIT_LEDGER.json' and (HERE/name).exists():check('repair bundle frozen copy parity',digest(HERE/name)==expected_hash,name)
 for name,k in [('features_numeric.npy','numeric_feature_sha256'),('features_categories.npy','categorical_feature_sha256')]:check('causal feature matrix immutable',digest(HERE/'PRIVATE_INPUTS'/name)==receipt[k],name)
 check('corrected target byte lineage',digest(HERE/'PRIVATE_INPUTS/targets.npy')==receipt['corrected_targets_sha256'])
 gs=np.asarray([r['session'] for r in rows(HERE/'PERSISTENT_GRID.jsonl.gz')]);folds=read(HERE/'SPLIT_PRECOMMIT.json')['folds'];oldledger=read(BASE/'FIT_LEDGER.json')
 fixed={'max_depth':3,'learning_rate':.05,'max_iter':100,'max_leaf_nodes':31,'min_samples_leaf':20,'l2_regularization':0.,'early_stopping':False,'random_state':570926}
 for r in ledger['runs']:
  fold=next(f for f in folds if f['id']==r['fold']);tr=np.flatnonzero(np.isin(gs,fold['train']));te=np.flatnonzero(np.isin(gs,fold['test']));h=1 if r['head']=='QUALITY' else 2;prefix=f"{r['family']}_F{r['fold']}";mp=HERE/'PRIVATE_MODELS';eligible=tr[np.isfinite(new[tr,h])];test=te[np.isfinite(new[te,h])]
  check('20 corrected fits frozen session split',r['train_sessions']==fold['train'] and r['test_sessions']==fold['test'],prefix)
  check('20 corrected fits exact train/test eligibility',np.array_equal(np.load(mp/(prefix+'_'+r['head']+'_eligible_train_indices.npy')),eligible) and np.array_equal(np.load(mp/(prefix+'_'+r['head']+'_eligible_test_indices.npy')),test) and r['head_train_rows']==len(eligible) and r['head_test_rows']==len(test),[prefix,r['head']])
  check('20 corrected target vectors independent lineage',np.array_equal(np.load(mp/(prefix+'_'+r['head']+'_training_target.npy')),new[eligible,h]) and digest(mp/(prefix+'_'+r['head']+'_training_target.npy'))==r['target_lineage_sha256'],[prefix,r['head']])
  check('20 corrected fits fixed parameters',r['model_parameters']==fixed,[prefix,r['head']])
  check('20 corrected fits model/preprocessor/reference SHA',digest(mp/(prefix+'_'+r['head']+'.pkl'))==r['model_sha256'] and digest(mp/(prefix+'_preprocessor.pkl'))==r['preprocessor_sha256'] and digest(mp/(prefix+'_'+r['head']+'_train_prediction_reference.npy'))==r['reference_sha256'],[prefix,r['head']])
  check('preprocessor byte reuse; train-only semantics unchanged',digest(mp/(prefix+'_preprocessor.pkl'))==digest(BASE/'PRIVATE_MODELS'/(prefix+'_preprocessor.pkl')),prefix)
  prior=next(x for x in oldledger['runs'] if (x['family'],x['fold'],x['head'])==(r['family'],r['fold'],r['head']))
  check('old buggy Q/D models not mixed',r['model_sha256']!=prior['model_sha256'],[prefix,r['head']])
 reuse=[r for r in oldledger['runs'] if r['head']=='UPSIDE'];check('exact ten UPSIDE fit reuse',len(reuse)==10 and len(oo['UPSIDE_reuse'])==2 and oo['mixed_old_bug_Q_D_predictions']==0)
 for r in reuse:
  prefix=f"{r['family']}_F{r['fold']}";p=HERE/'PRIVATE_MODELS';check('UPSIDE10 unchanged model/preprocessor/reference hashes',digest(p/(prefix+'_UPSIDE.pkl'))==r['model_sha256'] and digest(p/(prefix+'_preprocessor.pkl'))==r['preprocessor_sha256'] and digest(p/(prefix+'_UPSIDE_train_prediction_reference.npy'))==r['reference_sha256'],prefix)
 for family in ['P0','P1']:
  oldz=load_npz(BASE/'PRIVATE_INPUTS'/f'oof_{family}.npz');newz=load_npz(HERE/'PRIVATE_INPUTS'/f'oof_{family}.npz');check('UPSIDE OOF predictions/percentiles unchanged',np.array_equal(oldz['predictions'][:,0],newz['predictions'][:,0]) and np.array_equal(oldz['percentiles'][:,0],newz['percentiles'][:,0]),family);check('UPSIDE OOF byte hash unchanged',digest(BASE/f'OOF_{family}_UPSIDE.jsonl.gz')==digest(HERE/f'OOF_{family}_UPSIDE.jsonl.gz'),family)
 for name,spec in oo['files'].items():check('corrected OOF receipt byte lineage',digest(HERE/name)==spec['sha256'],name)
 primary=list(rows(HERE/'P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'));q70=[r for r in rows(HERE/'FIRST_ENTRY_Q70.jsonl.gz') if r['family']=='P1'];check('P1_Q70 primary records exact generated policy subset',primary==q70 and sum(r['entry_status']=='FIRST_ENTRY' for r in primary)>0)
 ev=read(HERE/'P1_Q70_ENTRY_EVALUATION.json');entered=[r for r in primary if r['entry_status']=='FIRST_ENTRY'];check('P1_Q70 official activity counts',ev['Activity']['FIRST_ENTRY_N']==len(entered) and ev['Activity']['watch_N']==len(primary))
 for field,target in [('remaining_upside_pct',ev['Upside']['Entry_to_strictly_later_High']),('upside_retention_pct',ev['Upside']['Upside_Retention_pct']),('pre_peak_mae_abs_pct',ev['Pre_peak_MAE_abs_pct']),('path_efficiency',ev['Path_Efficiency'])]:
  vals=[r[field] for r in entered if r.get(field) is not None];check('P1_Q70 official median evidence',target['N']==len(vals) and same(target['median'],float(np.median(vals)) if vals else None),field)
 check('downstream execution exposure0',ev['EXIT_calls']==ev['Reentry_calls']==ev['Capital_replays']==0 and all(not v for v in scope['safety'].values()))

def run():
 t0=time.time();repair_scope_checks();identity=read(OLD/'STATE9_FINAL_IDENTITY.json')
 for spec in identity['source_files']:check('exact final RC2 source identity',digest(OLD/'FROZEN_RC2_SOURCE'/spec['path'])==spec['sha256'],spec['path'])
 for name,key in [('RC2_CONTRACT.txt','contract_sha256'),('profile.json','profile_sha256'),('M0.md','M0_sha256'),('source_snapshot.json','source_snapshot_sha256'),('STATE_PATH_CONTRACT_V1.md','path_contract_sha256')]:check('exact final RC2 contract profile M0 Path',digest(OLD/'FROZEN_PUBLIC_INPUTS'/name)==identity[key],name)
 ws=list(rows(HERE/'WATCH_RECORDS.jsonl.gz'));primary=[w for w in ws if w['canonical']];raw=read(INPUT/'raw_paths_selected.json.gz');grid=list(rows(HERE/'PERSISTENT_GRID.jsonl.gz'));metadata=list(rows(HERE/'STATE_FEATURE_METADATA.jsonl.gz'));X=np.load(HERE/'PRIVATE_INPUTS/features_numeric.npy',mmap_mode='r');C=np.load(HERE/'PRIVATE_INPUTS/features_categories.npy',mmap_mode='r');Y=np.load(HERE/'PRIVATE_INPUTS/targets.npy',mmap_mode='r');vocab=read(HERE/'PRIVATE_INPUTS/category_vocabulary.json');features=read(HERE/'FEATURE_FREEZE.json');ranges=np.load(HERE/'PRIVATE_INPUTS/watch_row_ranges.npy');events=read(INPUT/'selector_events_full144.json.gz');byevent=collections.defaultdict(list)
 for e in events:byevent[e['sessionDate']+'|'+e['symbol']].append(e)
 check('watch identity unique',len(ws)==len({w['watch_key'] for w in ws})==4931)
 for wi,w in enumerate(ws):
  ee=sorted(byevent[w['watch_key']],key=lambda x:(x['decisionTimestamp'],x['selectorEventId']));check('first Selector event and first-selector anchor',ee[0]['selectorEventId']==w['first_selector_event'] and ee[0]['decisionTimestamp']==w['first_selector_timestamp'] and ee[0]['decisionPrice']==w['selector_price'],w['watch_key']);check('repeated Selector refresh',w['refresh_event_ids']==[e['selectorEventId'] for e in ee[1:]] and w['refresh_times']==[e['decisionTimestamp'] for e in ee[1:]],w['watch_key']);check('WATCH_KEY',w['watch_key']==w['session']+'|'+w['symbol'],w['watch_key'])
  a=valid(raw[w['watch_key']]['today']);expected=[int(x[0])+1 for x in a if int(x[0]) in reg(w['session']) and x[0]+1>=w['selector_minute']];lo,hi=ranges[wi];actual=[r['intent_minute'] for r in grid[int(lo):int(hi)]];check('full-day observed 1m grid',actual==expected,w['watch_key']);closes={int(x[0]):float(x[4]) for x in a};missing=np.ones(932,dtype=int)
  for m in closes:missing[m]=0
  missing_prefix=np.r_[0,np.cumsum(missing)]
  for i in range(int(lo),int(hi)):
   r=grid[i];m=metadata[i];t=r['intent_minute'];check('every-minute causal cutoff',r['closed_raw_start']+1==t and r['feature_max_timestamp']<=r['intent_timestamp'] and (m['state_as_of_minute'] is None or m['state_as_of_minute']<=t),r['row_id']);check('lunch/session-close and no 30m cap',t-1 in reg(w['session']) and t<=close(w['session']) and t>=w['selector_minute'],r['row_id'])
   known=[q for q in w['refresh_minutes'] if q<=t];j=features['P0_numeric'].index('knownRefreshCount');check('refresh causal feature',X[i,j]==len(known),r['row_id']);j=features['P0_numeric'].index('activeMinutesSinceSelector');check('active clock feature',X[i,j]==active(w['session'],w['selector_minute'],t),r['row_id'])
   if m['source_status']=='SOURCE_UNAVAILABLE':check('source missing distinct from semantic unknown',np.isnan(X[i,len(features['P0_numeric']):]).all() and vocab[-1][int(C[i,-1])]=='SOURCE_UNAVAILABLE' and all(vocab[j][int(C[i,j])]=='__MISSING__' for j in range(11)) and all(vocab[j][int(C[i,j])]=='__UNKNOWN_HISTORY__' for j in range(11,14)),r['row_id'])
   for n in [1,3,5,10,20]:
    begin=t-n-1;ok=begin>=(540 if t<=690 else 750) and missing_prefix[t]-missing_prefix[begin]==0;v=100*(closes[t-1]/closes[begin]-1) if ok else None;j=features['P0_numeric'].index('return'+str(n));check('price close-lag missing semantics',same(None if not np.isfinite(X[i,j]) else X[i,j],v),r['row_id'])
 # Every teacher row independently checked against saved source; cache fill results.
 source_clean={w['watch_key']:valid(raw[w['watch_key']]['today']) for w in ws};cached={};last_key=None;teacher_N=0
 for r in rows(HERE/'TEACHER_LABELS.jsonl.gz'):
  key=r['watch_key'];i=r['row_index'];day=r['session'];a=source_clean[key]
  if key!=last_key:cached={};last_key=key
  f=fill(day,a,r['intent_minute']);check('next raw regular open +5bps fill',f is None and r.get('fill_minute') is None or f is not None and r['fill_minute']==f[0] and same(r['fill_price'],f[1]),r['row_id'])
  if f is not None:
   if f[0] not in cached:cached[f[0]]=expected_teacher(day,a,*f)
   e=cached[f[0]]
   for k in ['remaining_upside_pct','peak_minute','peak_bar_close','U_target','Q_target','D_target','path_efficiency','total_variation_pct','pre_peak_mae_abs_pct','reversal_count','time_to_peak_active_min']:
    check('teacher independent '+k,same(r.get(k),e.get(k)),[r['row_id'],k])
   for k in [1,2,3,4,5]:check('first +1..5 hit/unknown',r.get('first_upside',{}).get(str(k),{}).get('status')==e['first_upside'][str(k)],r['row_id'])
  for h,k in enumerate(['U_target','Q_target','D_target']):check('teacher target file lineage',same(None if not np.isfinite(Y[i,h]) else Y[i,h],r.get(k)),r['row_id'])
  teacher_N+=1
  if teacher_N%100000==0:print(json.dumps({'audit_teacher_rows':teacher_N,'seconds':round(time.time()-t0,1),'mismatches_so_far':len(mismatches)}),flush=True)
 freeze=read(HERE/'MODEL_SCORE_POLICY_FREEZE.json');folds=read(HERE/'SPLIT_PRECOMMIT.json')['folds'];ledger=read(HERE/'FIT_LEDGER.json');check('fit budget and fixed model',ledger['fits_reserved']==ledger['fits_completed']==30 and all(x['status']=='COMPLETED' for x in ledger['runs']));sessions=np.asarray([r['session'] for r in grid]);model_prediction_samples=0
 for family in ['P0','P1']:
  z=load_npz(HERE/'PRIVATE_INPUTS'/f'oof_{family}.npz');primary_indices=np.flatnonzero([r['canonical'] for r in grid]);check('outer OOF population lineage',np.array_equal(z['row_indices'],primary_indices));dims=len(features['P0_numeric']) if family=='P0' else len(features['P1_numeric']);slot={int(i):j for j,i in enumerate(z['row_indices'])}
  for fold in folds:
   tr=np.flatnonzero(np.isin(sessions,fold['train']));te=np.flatnonzero(np.isin(sessions,fold['test']));check('temporal split no session/watch crossing',max(fold['train'])<fold['purge']<min(fold['test']) and not(set(fold['train'])&set(fold['test'])));p=HERE/'PRIVATE_MODELS'/f'{family}_F{fold["id"]}_preprocessor.pkl';prep=pickle.loads(p.read_bytes())
   with __import__('warnings').catch_warnings():
    __import__('warnings').simplefilter('ignore');med=np.nanmedian(X[tr,:dims],axis=0)
   med=np.where(np.isfinite(med),med,0);check('train-only median preprocessing',np.allclose(med,prep.median,atol=0,rtol=0) and prep.training_rows==len(tr))
   if family=='P1':
    for j,v in enumerate(vocab):
     expected=set(map(int,C[tr,j]));expected|={v.index(s) for s in ['__MISSING__','__UNKNOWN_HISTORY__','__FORMAL_NULL__'] if s in v};check('train-only one-hot and reserved missing/unknown',set(prep.known[j])==expected,[family,fold['id'],j])
   rawtrain=np.load(HERE/'PRIVATE_MODELS'/f'{family}_F{fold["id"]}_train_predictions.npy');calc_train_pct=[];out_te=[];sample_te=te[np.linspace(0,len(te)-1,min(128,len(te)),dtype=int)];sample_tr=tr[np.linspace(0,len(tr)-1,min(128,len(tr)),dtype=int)];sample=np.r_[sample_tr,sample_te];A=preprocess(prep,X[sample,:dims],C[sample] if family=='P1' else None)
   for h,head in enumerate(['UPSIDE','QUALITY','ADVERSE']):
    fit_record=next(f for f in ledger['runs'] if f['family']==family and f['fold']==fold['id'] and f['head']==head);check('model training labels match corrected frozen teacher',fit_record['head_train_rows']==int(np.isfinite(Y[tr,h]).sum()),[family,fold['id'],head,fit_record['head_train_rows'],int(np.isfinite(Y[tr,h]).sum())])
    ref=np.load(HERE/'PRIVATE_MODELS'/f'{family}_F{fold["id"]}_{head}_train_prediction_reference.npy');check('train prediction distribution lineage',np.array_equal(np.sort(rawtrain[:,h]),ref));model=pickle.loads((HERE/'PRIVATE_MODELS'/f'{family}_F{fold["id"]}_{head}.pkl').read_bytes());check('fixed HGB model parameters',all(model.get_params()[k]==v for k,v in freeze['parameters'].items()) and model.n_iter_==100);got=model.predict(A);sample_tr_positions=np.searchsorted(tr,sample_tr);check('independent preprocessed train model predictions',np.allclose(got[:len(sample_tr)],rawtrain[sample_tr_positions,h],atol=1e-10,rtol=0));sample_slots=[slot[int(i)] for i in sample_te];check('independent preprocessed OOF model predictions',np.allclose(got[len(sample_tr):],z['predictions'][sample_slots,h],atol=1e-10,rtol=0));model_prediction_samples+=len(sample)
    calc_train_pct.append((np.searchsorted(ref,rawtrain[:,h],'left')+np.searchsorted(ref,rawtrain[:,h],'right'))/(2*len(ref)));indices=[slot[int(i)] for i in te];pv=z['predictions'][indices,h];expected_pct=(np.searchsorted(ref,pv,'left')+np.searchsorted(ref,pv,'right'))/(2*len(ref));check('OOF score percentile transform all rows',np.array_equal(expected_pct,z['percentiles'][indices,h]));out_te.append(expected_pct)
   train_score=(calc_train_pct[0]+calc_train_pct[1]+1-calc_train_pct[2])/3;threshold=np.quantile(train_score,[.70,.80,.90,.95],method='linear');indices=[slot[int(i)] for i in te];check('Q70 Q80 Q90 Q95 train-only quantile lineage',np.array_equal(z['thresholds'][indices],np.repeat(threshold[None,:],len(indices),axis=0)));calc_score=(out_te[0]+out_te[1]+1-out_te[2])/3;check('equal-weight uptrend score all OOF rows',np.allclose(z['score'][indices],calc_score,rtol=0,atol=1e-15))
 entries={p:list(rows(HERE/f'FIRST_ENTRY_{p}.jsonl.gz')) for p in ['Q70','Q80','Q90','Q95']};geometry={(r['arm'],r['opportunity']):r for r in rows(INPUT/'geometry_rows.jsonl.gz')};evals=read(HERE/'SELECTOR_WATCH_BUCKET_EVALUATION.json')['policies'];pres=read(HERE/'WINNER_PRESERVATION.json')['panels'];daily=read(HERE/'DAILY_FIRST_ENTRY_ACTIVITY.json')['panels']
 for family in ['P0','P1']:
  z=load_npz(HERE/'PRIVATE_INPUTS'/f'oof_{family}.npz');by=collections.defaultdict(list)
  for j,i in enumerate(z['row_indices']):by[grid[int(i)]['watch_key']].append(j)
  for pi,p in enumerate(['Q70','Q80','Q90','Q95']):
   rr=[r for r in entries[p] if r['family']==family];check('FIRST entry watch population',len(rr)==2155 and len({r['watch_key'] for r in rr})==2155)
   for r in rr:
    hits=[j for j in by[r['watch_key']] if z['score'][j]>=z['thresholds'][j,pi]];first=hits[0] if hits else None;intent=r['first_intent'];check('FIRST threshold cross and decision stopping',first is None and intent is None and r['scoring_decisions']==len(by[r['watch_key']]) or first is not None and intent is not None and intent['row_index']==int(z['row_indices'][first]) and r['scoring_decisions']==by[r['watch_key']].index(first)+1,r['watch_key']);check('FIRST_ENTRY after decision stop / EXIT0 Reentry0',r['decision_after_first_entry']==r['second_intent']==r['EXIT_calls']==r['reentry_calls']==0,r['watch_key']);trace=[[grid[int(z['row_indices'][j])]['intent_minute'],float(z['score'][j]),float(z['thresholds'][j,pi])] for j in by[r['watch_key']][:r['scoring_decisions']]];check('FIRST threshold trace hash lineage',r['threshold_trace_sha256']==hashlib.sha256(json.dumps(trace,separators=(',',':')).encode()).hexdigest(),r['watch_key'])
    f=fill(r['session'],source_clean[r['watch_key']],intent['intent_minute']) if intent else None;check('FIRST entry next-open+5bps',f is None and r['entry_status']!='FIRST_ENTRY' or f is not None and r['entry_status']=='FIRST_ENTRY' and r['fill_minute']==f[0] and same(r['fill_price'],f[1]),r['watch_key'])
    if f is not None:
     e=expected_teacher(r['session'],source_clean[r['watch_key']],*f)
     for k in ['remaining_upside_pct','peak_minute','path_efficiency','total_variation_pct','pre_peak_mae_abs_pct','reversal_count']:check('FIRST ENTRY evaluator independent '+k,same(e.get(k),r.get(k)),r['watch_key'])
    g=geometry[('IMMEDIATE',r['watch_key'])];v=g['selector_to_high_pct'] if g['canonical_full_session_evaluable'] else None;check('watch first anchor Selector MFE',same(v,r['selector_to_high_pct']) and r['selector_minute']==g['selector_minute'] and r['selector_price']==g['selector_price'],r['watch_key']);b='missing' if v is None else '<1%' if v<1 else '1–<2%' if v<2 else '2–<3%' if v<3 else '3–<4%' if v<4 else '4–<5%' if v<5 else '>=5%';check('exclusive Selector MFE bucket',b==r['selector_bucket'],r['watch_key'])
   for b,panel in evals[family+'_'+p].items():
    rs=[r for r in rr if r['selector_bucket']==b];check('watch bucket denominator / Entry count',panel['watch_N']==len(rs) and panel['FIRST_ENTRY_N']==sum(r['entry_status']=='FIRST_ENTRY' for r in rs),[family,p,b])
   for k in range(1,6):
    winners=[r for r in rr if r['selector_to_high_pct'] is not None and r['selector_to_high_pct']>=k];entered=[r for r in winners if r['entry_status']=='FIRST_ENTRY'];hit=sum(r['first_upside'][str(k)]['status']=='HIT_CONFIRMED' for r in entered);unk=sum(r['first_upside'][str(k)]['status']=='UNKNOWN' for r in entered);panel=pres[family+'_'+p][str(k)];check('>=1..5 Winner denominator and capture',panel['selector_winner_denominator']==len(winners) and panel['FIRST_ENTRY_N']==len(entered) and panel['entry_after_same_threshold_hit_N']==hit and panel['unknown_N']==unk,[family,p,k])
   for panel in daily[family+'_'+p]['daily']:
    day=panel['session'];wsday=[w for w in primary if w['session']==day];rs=[r for r in rr if r['session']==day];ee=[r for r in rs if r['entry_status']=='FIRST_ENTRY'];check('daily FIRST_ENTRY counts',panel['FIRST_ENTRY_N']==len(ee) and panel['unique_entered_symbols_N']==len({r['symbol'] for r in ee}) and panel['selector_event_N']==sum(1+len(w['refresh_minutes']) for w in wsday) and panel['unique_active_watch_N']==len(wsday),[family,p,day]);timeline=sorted([(w['selector_minute'],0,1) for w in wsday]+[(r['fill_minute'],1,-1) for r in ee]);cur=peak=0
    for t,order,amount in timeline:cur+=amount;peak=max(peak,cur)
    check('daily peak active watchlist and simultaneous demand',panel['peak_active_watchlist_size']==peak and panel['max_simultaneous_FIRST_ENTRY_demand']==max(collections.Counter(r['fill_minute'] for r in ee).values(),default=0),[family,p,day])
 # Deterministic sample is fixed by index, never outcome or score.
 sample_indices=sorted(set(range(0,len(ws),100))|{len(ws)-1});state_N=audit_state(sample_indices,ws,raw,X,C,vocab,metadata,features)
 # Decision channels are causally allowlisted, and forbidden trading imports absent.
 tree=ast.parse((HERE/'first_entry.py').read_text());generate=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='generate');body=ast.get_source_segment((HERE/'first_entry.py').read_text(),generate);check('future teacher/evaluator isolation',all(s not in body for s in ['TEACHER_LABELS','targets.npy','future_metrics','remaining_upside','QUALITY_CANDIDATE','geometry_rows','selector_to_high_pct']))
 for script in ['model_oof.py','first_entry.py','causal_features.py','teacher.py','repair_refit.py','reconstruct_oof.py','regenerate_first_entry.py','evaluate_primary.py']:
  code=(HERE/script).read_text();tree=ast.parse(code);imports=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]+[a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names];check('EXIT / Reentry / Capital / order imports absent',not any(any(s in str(m).lower() for s in ['r50','broker','reentry','exit_replay','capital_replay','portfolio_replay']) for m in imports),script)
 check('previous Work remains closed',read(OLD/'FINAL_STATUS.json')['productionReady']==False if (OLD/'FINAL_STATUS.json').exists() else True)
 result={'saved_at_jst':datetime.datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'status':'PASS' if not failure_counts else 'FIRST_ENTRY_V2_FREEZE_BLOCKED_INTEGRITY','audit_implementation':'independent calendar/set/label/lineage arithmetic plus separate teacher/state-machine formulas; frozen independent RC2 API + normalization120; no main repair calculation imports','audit_fit':0,'future_causal_leakage':sum(failure_counts[n] for n in ['every-minute causal cutoff','refresh causal feature','future teacher/evaluator isolation','temporal split no session/watch crossing','train-only median preprocessing','train-only one-hot and reserved missing/unknown','State timestamp independent kernel']), 'Primary_Freeze_Target':'P1_Q70','Legacy_State_features':0,'corrected_Q_D_fits':20,'UPSIDE_fit_reuse':10,'Capital_replays':0,'checks':dict(checks),'total_checks':sum(checks.values()),'mismatch_N':sum(failure_counts.values()),'failure_counts':dict(failure_counts),'mismatch_examples_N':len(mismatches),'mismatches':mismatches,'grid_rows_checked':len(grid),'teacher_rows_checked':teacher_N,'FIRST_ENTRY_records_checked':sum(len(v) for v in entries.values()),'independent_state_sample_watch_N':len(sample_indices),'independent_state_rows_checked':state_N,'model_prediction_samples_checked':model_prediction_samples,'all_rows_score_threshold_lineage_checked':True,'train_only_preprocessing_all_training_rows_checked':True,'audit_limits':['independent exact State numeric/history replay uses predetermined51-watch sample; source/causal timestamp and missing checks cover every row','model direct prediction checked on deterministic256-row sample per fit; percentile transform and threshold lineage checked on all rows','actual historical bar arrival timestamp UNKNOWN; causal availability assumes bar end','low/high intrabar order unknown; peak-bar Low conservatively included','State Path EXIT event names are state-run annotations, never trading EXIT policy calls'],'seconds':round(time.time()-t0,1),'EXIT_calls':0,'reentry_calls':0,'provider_requests':0,'productionReady':False}
 (HERE/'INDEPENDENT_REPAIR_AUDIT.json').write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['checks','mismatches','audit_limits']},ensure_ascii=False))
 if mismatches:raise SystemExit(2)
if __name__=='__main__':run()
