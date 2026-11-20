"""Full-day PRICE_CONTEXT + exact final RC2/Path; no future labels imported."""
import argparse,collections,concurrent.futures,sys,time
from decimal import Decimal,localcontext
from common import *
from price_features import *
SOURCE=OLD/'FROZEN_RC2_SOURCE';sys.path.insert(0,str(SOURCE))
from candidate.api import Engine
import normalize80,normalize120
from input_gate import scheduled_minutes
from PATH_FROZEN import PathBuilder,validate
from CAUSAL_FEATURE_BUILDER import FeatureBuilder
SCHEMA=read(SOURCE/'FEATURE_SCHEMA_V2.json');PROFILE=read(OLD/'FROZEN_PUBLIC_INPUTS/profile.json')
def state_task(arg):
 wi,w,raw,src=arg;day=w['session'];regular=set(regular_starts(day));a=clean_array(raw['today']);previous=clean_array(raw['previous'])
 a=a[np.asarray([int(x[0]) in regular for x in a],bool)];previous=previous[np.asarray([int(x[0]) in set(regular_starts(src['previous_session'])) for x in previous],bool)]
 tt=[int(x[0])+1 for x in a if x[0]+1>=w['selector_minute']]
 n=len(tt);nums=np.full((n,len(P0_NAMES)+len(P1_NUM)),np.nan);cats=[];meta=[]
 for j,t in enumerate(tt):nums[j,:len(P0_NAMES)]=compute(w,a[a[:,0]<t],previous,t)
 reason=None;prev=src['previous'];pd=src.get('previous_daily') or {}
 if not prev:reason='PREVIOUS_RAW_NOT_AVAILABLE'
 elif pd.get('AdjFactor') is None or Decimal(pd['AdjFactor'])!=1 or 'ExRT' not in pd or pd['ExRT'] is not None:reason='PREVIOUS_PRICE_BASIS_NOT_CONTINUOUS'
 if not reason:
  try:
   b80=normalize80.generate(prev,[]);b120=normalize120.regenerate(prev,[])
   assert b80['U']==b120['U'] and b80['P_ref']==b120['P_ref'],'NORMALIZATION_UNSTABLE'
  except ValueError as e:reason='M0_PREVIOUS_SOURCE_'+str(e)
 if reason or not tt:
  for t in tt:
   cats.append(['__MISSING__']*11+['__UNKNOWN_HISTORY__']*3+['SOURCE_UNAVAILABLE'])
   meta.append({'intent_minute':t,'state_as_of_minute':None,'source_status':'SOURCE_UNAVAILABLE','source_reason':reason,'formal_primary':None,'display_primary':None})
  return wi,nums,cats,meta,{'watch_key':w['watch_key'],'source_status':'SOURCE_UNAVAILABLE' if reason else 'NO_GRID_ROWS','source_reason':reason,'rows':n,'kernel_steps':0}
 assert src['previous_session']<day
 # Value-preserving compact decimal tokens were independently matched to original
 # saved provider lexemes; exact lexical original overlap is checked before run.
 current={int(x[0])+1:x for x in raw['today']};queue=[t for t in scheduled_minutes(day) if t<=max(tt)]
 engine=Engine(PROFILE);path=PathBuilder(w['watch_key']);builder=FeatureBuilder(SCHEMA)
 cache={};parity=0
 def coord(v):
  nonlocal parity
  lex=json.dumps(v,allow_nan=False)
  if lex not in cache:
   vals=[]
   for mod,base in ((normalize80,b80),(normalize120,b120)):
    ctx=normalize80.context() if mod is normalize80 else __import__('decimal').Context(prec=120,rounding=__import__('decimal').ROUND_HALF_EVEN,Emin=-999999,Emax=999999)
    with localcontext(ctx):vals.append(format(((Decimal(lex).ln()-Decimal(base['P_ref']).ln())/Decimal(base['U'])).quantize(Decimal('1e-24')),'f'))
   assert vals[0]==vals[1],'NORMALIZATION_UNSTABLE';cache[lex]=vals[0];parity+=1
  return cache[lex]
 first_am=min((int(x[0]) for x in raw['today'] if x[0]<690),default=None)
 first_pm=min((int(x[0]) for x in raw['today'] if 750<=x[0]<(900 if day<'2024-11-05' else 925)),default=None)
 seq=[];changes=[];segment=None;last_change=support_start=None;cursor=0;current_feats=history=state=endpoint=None
 for j,nowt in enumerate(tt):
  while cursor<len(queue) and queue[cursor]<=nowt:
   end=queue[cursor];cursor+=1;t=end-540;x=current.get(end);token=None;status='MISSING_RAW_SOURCE'
   if x is not None:
    auction='TERMINAL_AUCTION_MINUTE' if int(x[0]) in (690,close_minute(day)) else 'OPENING_MIXED_MINUTE' if int(x[0]) in (first_am,first_pm) else 'CONTINUOUS'
    if valid_bar(x):
     token={'t':t,'known_at':t,'source':'JQUANTS_V2_EQUITIES_BARS_MINUTE','auction':auction,**{k:coord(x[c]) for k,c in [('o',1),('h',2),('l',3),('c',4)]}};status='RAW_CLOSED_AT_ASSUMED_BAR_END'
    else:token={'t':t,'known_at':t,'source':'JQUANTS_V2_EQUITIES_BARS_MINUTE','auction':auction,**{k:'INVALID_RAW_PRICE' for k in 'ohlc'}};status='RAW_PRICE_NOT_NORMALIZABLE'
   assert token is None or end<=nowt
   state=engine.step(t,token,w['watch_key']);slot={'scheduled_t':t,'bar_end':stamp(day,end),'row_status':status}
   validate(state,slot,path.endpoints[-1] if path.endpoints else None);old=len(path.events);endpoint=path._push(state,slot);events=path.events[old:]
   fs=builder.push(state,endpoint,events,path.runs);current_feats={k:fs[k] for k in SCHEMA['numeric_state']+SCHEMA['categorical_state']}
   formal=endpoint['Primary_or_null']
   if endpoint['causal_segment_id']!=segment or formal is None or any(e['event_type'] in ('SEGMENT_BREAK','OBSERVATION_LOST') for e in events):seq=[];changes=[];last_change=support_start=None
   segment=endpoint['causal_segment_id']
   if formal is not None:
    if support_start is None:support_start=end
    if any(e['event_type']=='TRANSITION' for e in events):changes.append(end);last_change=end
    if not seq or seq[-1]!=formal:seq.append(formal);seq=seq[-3:]
   history={'previous_distinct_formal_primary':seq[-2] if len(seq)>=2 else '__UNKNOWN_HISTORY__','previous_to_current_pair':'>'.join(seq[-2:]) if len(seq)>=2 else '__UNKNOWN_HISTORY__','last3_distinct_primary_sequence':'>'.join(seq) if len(seq)>=3 else '__UNKNOWN_HISTORY__','current_state_active_dwell':active_elapsed(day,endpoint['entered_at']+540,end) if formal is not None else None,'active_time_since_last_primary_change':active_elapsed(day,last_change,end) if last_change is not None else None}
   for z in (5,10,20):history[f'transition_count_last{z}active']=sum(0<=active_elapsed(day,k,end)<z for k in changes) if support_start is not None and active_elapsed(day,support_start,end)>=z else None
  assert state is not None and state['as_of']+540<=nowt
  vals=[current_feats[k.split('/',1)[1]] if k.startswith('state/') else history[k.split('/',1)[1]] for k in P1_NUM]
  nums[j,len(P0_NAMES):]=[np.nan if v is None else float(v) for v in vals]
  cats.append([str(current_feats[k.split('/',1)[1]]) if k.startswith('state/') else str(history[k.split('/',1)[1]]) if k.startswith('history/') else 'SAVED_SOURCE_CONNECTED' for k in P1_CAT])
  meta.append({'intent_minute':nowt,'state_as_of_minute':state['as_of']+540,'source_status':'SAVED_SOURCE_CONNECTED','formal_primary':endpoint['Primary_or_null'],'display_primary':state['primary'],'observed':state['current_semantics_observed'],'causal_segment_id':segment,'row_source_status':endpoint['quality']['row_status']})
 return wi,nums,cats,meta,{'watch_key':w['watch_key'],'source_status':'SAVED_SOURCE_CONNECTED','rows':n,'kernel_steps':cursor,'normalization80_120_unique_price_checks':parity,'U_sha256':hashlib.sha256(b80['U'].encode()).hexdigest(),'previous_return_pairs':b80['previous_return_pairs_N'],'future_inputs':0}
def run(workers=8,limit=0):
 assert (HERE/'FEATURE_FREEZE.json').exists() and (HERE/'CLEAN_UPTREND_TEACHER_CONTRACT.json').exists()
 amendment=read(HERE/'IMPLEMENTATION_FIX_RECEIPT.json') if (HERE/'IMPLEMENTATION_FIX_RECEIPT.json').exists() else {}
 for name,expected in read(HERE/'FEATURE_FREEZE.json')['code_hashes'].items():
  if name=='price_features.py' and amendment:expected=amendment['corrected_code_sha256']
  if name=='causal_features.py' and amendment:expected=amendment['corrected_causal_runner_sha256']
  if name=='model_oof.py' and (HERE/'FIT_MEMORY_RESUME_RECEIPT.json').exists():expected=read(HERE/'FIT_MEMORY_RESUME_RECEIPT.json')['corrected_model_code_sha256']
  if (HERE/'NPZ_STORAGE_READ_RECEIPT.json').exists():expected=read(HERE/'NPZ_STORAGE_READ_RECEIPT.json')['updated_code_sha256'].get(name,expected)
  assert sha(HERE/name)==expected,'POST_FREEZE_CODE_MUTATION'
 raw=read(INPUT/'raw_paths_selected.json.gz');src=read(SCRATCH/'private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz');watches=list(lines(HERE/'WATCH_RECORDS.jsonl.gz'))
 proof=read(OLD/'ORIGINAL_SAVED_SOURCE_PROOF.json');assert sha(SCRATCH/'private_source/PRIVATE_SELECTED_SOURCE_TOKENS.json.gz')==proof['private_source_sha256']
 overlap=0
 for w in watches:
  rr={int(r[0]):r for r in raw[w['watch_key']]['today']}
  for r in src[w['watch_key']]['current_prefix']:
   m=int(r['Time'][:2])*60+int(r['Time'][3:]);a=rr[m]
   for i,k in enumerate(('O','H','L','C','Vo','Va'),1):assert Decimal(str(a[i]))==Decimal(r[k]),'RAW_COMPACT_ORIGINAL_VALUE_MISMATCH';overlap+=1
 write(HERE/'COMPACT_ORIGINAL_VALUE_PARITY.json',{'saved_at_jst':now(),'status':'PASS','current_prefix_decimal_checks':overlap,'mismatch':0,'original_full_compact_value_checks':proof['exact_numeric_value_checks'],'source_proof_sha256':sha(OLD/'ORIGINAL_SAVED_SOURCE_PROOF.json'),'future_source_used_by_decision':0})
 if limit:watches=watches[:limit]
 ranges=np.load(HERE/'PRIVATE_INPUTS/watch_row_ranges.npy');N=int(ranges[len(watches)-1,1]);num=np.lib.format.open_memmap(HERE/'PRIVATE_INPUTS/features_numeric.npy',mode='w+',dtype=np.float64,shape=(N,len(P0_NAMES)+len(P1_NUM)))
 cc=np.lib.format.open_memmap(HERE/'PRIVATE_INPUTS/features_categories.npy',mode='w+',dtype=np.int32,shape=(N,len(P1_CAT)));vocab=[{} for _ in P1_CAT];receipts=[];start=time.time()
 def arg(wi,w):
  s=src[w['watch_key']];return wi,w,raw[w['watch_key']],{k:s[k] for k in ('previous','previous_daily','previous_session')}
 with (HERE/'STATE_FEATURE_METADATA.jsonl.gz').open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as gz,concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
  for wi,nn,cats,meta,receipt in pool.map(state_task,(arg(i,w) for i,w in enumerate(watches)),chunksize=1):
   lo,hi=ranges[wi];assert hi-lo==len(nn);num[lo:hi]=nn
   for j,cs in enumerate(cats):
    for k,c in enumerate(cs):
     if c not in vocab[k]:vocab[k][c]=len(vocab[k])
     cc[lo+j,k]=vocab[k][c]
   for j,r in enumerate(meta):r.update(row_index=int(lo+j),row_id=watches[wi]['watch_key']+'|'+str(r['intent_minute']),watch_key=watches[wi]['watch_key']);gz.write((json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode())
   receipts.append(receipt)
   if wi%100==0:print(json.dumps({'feature_watches':wi+1,'feature_rows':int(hi),'seconds':round(time.time()-start,1),'new_fits':0}),flush=True)
 num.flush();cc.flush();write(HERE/'PRIVATE_INPUTS/category_vocabulary.json',[list(v) for v in vocab]);write(HERE/'STATE_TIMELINE_WATCH_RECEIPTS.jsonl.gz',receipts) if False else write_lines(HERE/'STATE_TIMELINE_WATCH_RECEIPTS.jsonl.gz',receipts)
 write(HERE/'FEATURE_COMPUTATION_RECEIPT.json',{'saved_at_jst':now(),'status':'FEATURES_CAUSALLY_COMPUTED','rows':N,'watches':len(watches),'numeric_fields':len(P0_NAMES)+len(P1_NUM),'categorical_fields':len(P1_CAT),'storage_category_encoding':'lossless strings dictionary only, model train-only one-hot later','kernel_steps':sum(r['kernel_steps'] for r in receipts),'normalization80_120_unique_price_checks':sum(r.get('normalization80_120_unique_price_checks',0) for r in receipts),'source_status_counts':dict(collections.Counter(r['source_status'] for r in receipts)),'source_unavailable_reasons':dict(collections.Counter(r.get('source_reason') for r in receipts if r['source_status']=='SOURCE_UNAVAILABLE')),'feature_inputs_future':0,'new_fits':0,'numeric_sha256':sha(HERE/'PRIVATE_INPUTS/features_numeric.npy'),'categorical_sha256':sha(HERE/'PRIVATE_INPUTS/features_categories.npy'),'state_metadata_sha256':sha(HERE/'STATE_FEATURE_METADATA.jsonl.gz'),'actual_known_at':'UNKNOWN; historic research assumes closed bar available at bar end','safety':SAFETY})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=8);ap.add_argument('--limit',type=int,default=0);a=ap.parse_args();run(a.workers,a.limit)
