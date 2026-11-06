"""Identity, grid and pre-outcome freezes. Never computes future teachers."""
import argparse,collections,gzip,hashlib,json,shutil
import numpy as np
from common import *
def identity():
 watches=read(HERE/'PRIVATE_INPUTS/watches_source.json')
 ids={w['watch_key'] for w in watches};primary={w['watch_key'] for w in watches if w['canonical']}
 events=read(INPUT/'selector_events_full144.json.gz')
 by=collections.defaultdict(list)
 for e in events:
  k=e['sessionDate']+'|'+e['symbol']
  if k in ids:by[k].append(e)
 assert set(by)==ids and len(ids)==4931 and len(primary)==2155
 for w in watches:
  ee=sorted(by[w['watch_key']],key=lambda e:(e['decisionTimestamp'],e['selectorEventId']))
  assert len(ee)==len({e['selectorEventId'] for e in ee})
  first=ee[0]
  assert first['selectorEventId']==w['first_selector_event']
  assert first['decisionTimestamp']==w['first_selector_timestamp']
  assert first['decisionPrice']==w['selector_price']
  assert len(ee)==w['saved_total_selection_count'],'SELECTION_COUNT_MISMATCH'
  w['refresh_minutes']=[minute(e['decisionTimestamp']) for e in ee[1:]]
  w['refresh_event_ids']=[e['selectorEventId'] for e in ee[1:]]
  w['refresh_times']=[e['decisionTimestamp'] for e in ee[1:]]
  w['expiry_minute']=close_minute(w['session'])
 daily=[]
 for d in sorted({w['session'] for w in watches if w['canonical']}):
  ws=[w for w in watches if w['session']==d]
  daily.append({'session':d,'selector_events':sum(1+len(w['refresh_minutes']) for w in ws),'unique_watch':len(ws),'repeat_events':sum(len(w['refresh_minutes']) for w in ws),'repeated_watches':sum(bool(w['refresh_minutes']) for w in ws)})
 def panel(ws):return {'watch_N':len(ws),'selector_event_N':sum(1+len(w['refresh_minutes']) for w in ws),'repeat_event_N':sum(len(w['refresh_minutes']) for w in ws),'repeated_watch_N':sum(bool(w['refresh_minutes']) for w in ws),'sessions':len({w['session'] for w in ws})}
 write(HERE/'SELECTOR_REPEAT_AUDIT.json',{'status':'PASS','saved_at_jst':now(),'primary_watch_population':panel([w for w in watches if w['canonical']]),'all_training_and_OOF':panel(watches),'daily_primary':daily,'full_refresh_timestamps_saved_in':'WATCH_RECORDS.jsonl.gz','canonical_2155_is_already_unique_watch_population':True,'denominators_never_added':True,'safety':SAFETY})
 write(HERE/'WATCH_IDENTITY_CONTRACT.json',{'saved_at_jst':now(),'WATCH_KEY':'session|symbol','activation':'earliest valid saved Selector event by decisionTimestamp','refresh':'append SELECTOR_REFRESH; no parallel watch','refresh_feature_known_at':'each exact event decisionTimestamp; final selectionCount audit-only','expiry':'same-session regular close','first_entry_limit':1,'canonical_reference':'2155 first-selection records, not the 2900 repeated event population','primary_N':2155,'all_N':4931,'watch_identity_changes':0,'safety':SAFETY})
 write_lines(HERE/'WATCH_RECORDS.jsonl.gz',watches)
 print(json.dumps(read(HERE/'SELECTOR_REPEAT_AUDIT.json')['primary_watch_population']))
def grid():
 watches=list(lines(HERE/'WATCH_RECORDS.jsonl.gz'));raw=read(INPUT/'raw_paths_selected.json.gz')
 original=read(HERE/'PRIVATE_INPUTS/watches_source.json');assert len(raw)==len(watches)==4931
 records=[];support=[];indices=[]
 for wi,w in enumerate(watches):
  a=clean_array(raw[w['watch_key']]['today']);day=w['session'];regular=set(regular_starts(day))
  eligible=[x for x in a if int(x[0]) in regular and int(x[0])+1>=w['selector_minute'] and int(x[0])+1<=w['expiry_minute']]
  start=len(records)
  for x in eligible:
   t=int(x[0])+1
   records.append({'row_id':w['watch_key']+'|'+str(t),'watch_key':w['watch_key'],'watch_index':wi,'session':day,'symbol':w['symbol'],'intent_minute':t,'intent_timestamp':stamp(day,t),'feature_max_timestamp':stamp(day,t),'closed_raw_start':int(x[0]),'active_delay':active_elapsed(day,w['selector_minute'],t),'selector_minute':w['selector_minute'],'first_selector_event':w['first_selector_event'],'canonical':w['canonical']})
  expected=sum(m+1>=w['selector_minute'] for m in regular)
  status='EVALUABLE_FULL_GRID' if len(eligible)==expected else 'PARTIALLY_EVALUABLE' if eligible else 'SOURCE_UNAVAILABLE'
  support.append({'watch_key':w['watch_key'],'canonical':w['canonical'],'status':status,'expected_decisions':expected,'observed_decisions':len(eligible),'missing_decisions':expected-len(eligible)})
  indices.append([start,len(records)])
 assert all(r['intent_minute'] not in range(691,751) for r in records)
 write_lines(HERE/'PERSISTENT_GRID.jsonl.gz',records);write_lines(HERE/'WATCH_SOURCE_SUPPORT.jsonl.gz',support)
 np.save(HERE/'PRIVATE_INPUTS/watch_row_ranges.npy',np.asarray(indices,dtype=np.int64))
 def summarize_support(xs):return {'watch_N':len(xs),'status_counts':dict(collections.Counter(x['status'] for x in xs)),'expected_rows':sum(x['expected_decisions'] for x in xs),'observed_rows':sum(x['observed_decisions'] for x in xs),'missing_rows':sum(x['missing_decisions'] for x in xs)}
 write(HERE/'PERSISTENT_GRID_RECEIPT.json',{'saved_at_jst':now(),'status':'PERSISTENT_GRID_RECONSTRUCTED_WITH_EXPLICIT_MISSINGNESS','all':summarize_support(support),'primary':summarize_support([x for x in support if x['canonical']]),'source_inputs':input_manifest(),'grid_sha256':sha(HERE/'PERSISTENT_GRID.jsonl.gz'),'grid_rows':len(records),'provider_requests':0,'synthetic_missing_rows':0,'source_missing_zero_imputation':0,'lunch_rows':0,'old_30m_expiry_used':False,'bar_end_availability':'research assumption; historical actual knownAt UNKNOWN','safety':SAFETY})
 print(json.dumps(read(HERE/'PERSISTENT_GRID_RECEIPT.json')['primary']))
def freeze():
 from price_features import P0_NAMES,P1_NUM,P1_CAT,provenance
 feature={'saved_at_jst':now(),'before_teacher_computation':True,'P0_numeric':P0_NAMES,'P0_categorical':[],'P1_numeric':P0_NAMES+P1_NUM,'P1_categorical':P1_CAT,'price_primitive_provenance':provenance(),'state_identity':read(OLD/'STATE9_FINAL_IDENTITY.json'),'numeric_preprocessing':'training-feature rows only median + missing indicator; all-train-missing median 0 with indicator 1','categorical_preprocessing':'training-only one-hot with explicit MISSING, semantic UNKNOWN and unseen UNKNOWN buckets; no ordinal substitute','prohibited':['future evaluator','teacher','selector future selectionCount','V6 R2 probability','V6 R2 raw score','V6 R2 rank','symbol/session identity as predictor'],'existing_primitives_absent_and_not_invented':['HH/HL/LH/LL fraction','time above VWAP','causal close-path recovery fraction'],'code_hashes':{p.name:sha(p) for p in [HERE/'price_features.py',HERE/'price_primitives.py',HERE/'causal_features.py',HERE/'teacher.py',HERE/'model_oof.py',HERE/'first_entry.py']},'safety':SAFETY}
 write(HERE/'FEATURE_FREEZE.json',feature)
 teacher={'saved_at_jst':now(),'before_teacher_computation':True,'heads':{'U':'strictly later raw-bar-start maximum observed High / fill; raw percent saved; training clip 0..10','Q':'fill + closed closes including fill bar through earliest strictly later max-High bar; max(net close progress,0)/total variation; TV=0 =>0; complete scheduled-source path required','D':'absolute min(0,min Low/fill-1) from fill bar through peak bar inclusive; train clip 0..5; complete scheduled-source path required'},'future_used_only_in':'teacher/evaluator','fill':'first available regular raw open at start>=intent +5bps; exclude actual 09:00/12:30 mixed opening starts; no 30-minute cap','strictly_later':'maximum over raw source start>fill_minute; same fill-bar High excluded','peak':'earliest raw bar attaining observed maximum High; exact touch time and intrabar order unknown','missing_path':'Q and D targets NULL; observed raw statistics separately saved, no interpolation across missing scheduled minute','lunch_and_closing_auction_pause':'not active; expected dated RC2 source schedule, including terminal marks, otherwise no inserted bar','U_is_observed_maximum':'partial-source U is a lower-bound observed target, not guaranteed true maximum','additional_labels_not_selection_targets':['time-to-peak','first +1..5% and pre-hit MAE','reversal count','session-end MFE/MAE','terminal return','Selector Low/High anatomy'],'primary_winner_denominator':'saved canonical first-selector full-session MFE, reused; continuous 1m completeness separate','capture':'observed strictly later hit confirmed; absent hit on incomplete remaining source =>unknown','safety':SAFETY}
 write(HERE/'CLEAN_UPTREND_TEACHER_CONTRACT.json',teacher)
 folds=read(OLD/'R1_folds.json');ws=list(lines(HERE/'WATCH_RECORDS.jsonl.gz'));days={w['session'] for w in ws};primary={w['session'] for w in ws if w['canonical']}
 out=[]
 for f in folds:
  assert set(f['train'])<=days and set(f['test'])<=days and max(f['train'])<f['purge']<min(f['test'])
  out.append({k:f[k] for k in ['id','train','purge','test']})
 assert set(sum([f['test'] for f in out],[]))==primary
 write(HERE/'SPLIT_PRECOMMIT.json',{'saved_at_jst':now(),'before_teacher_computation':True,'status':'EXACT_R1_OUTER_SESSION_SPLIT_REUSED_AT_WATCH_LEVEL','original_sha256':sha(OLD/'R1_folds.json'),'folds':out,'same_session_crossing':False,'same_watch_crossing':False,'random_row_split':False,'future_training_session':False,'outer_OOF_only':True,'train_feature_distribution_scope':'all train decision rows, independent of teacher availability','safety':SAFETY})
 write(HERE/'MODEL_SCORE_POLICY_FREEZE.json',{'saved_at_jst':now(),'before_teacher_computation':True,'families':['P0','P1'],'heads':list(HEADS),'folds':5,'planned_fits':30,'hard_cap':36,'model':'HistGradientBoostingRegressor','parameters':{'max_depth':3,'learning_rate':.05,'max_iter':100,'max_leaf_nodes':31,'min_samples_leaf':20,'l2_regularization':0.,'early_stopping':False,'random_state':570926},'percentile':'(train predictions strictly less + .5*equal)/N, training grid in-sample distribution for each fold/family/head','score':'(U_pctile+Q_pctile+(1-D_pctile))/3','thresholds':POLICIES,'threshold_method':'np.quantile(train score,q,method=linear)','first_cross':'score>=threshold at earliest causal grid row; lock BUY_INTENT, wait first available fill, stop scoring after FIRST ENTRY','quality_selection':['max median Q','min median pre-peak MAE','max median remaining upside','max >=5 capture','max watch Entry rate'],'balanced_selection':['max >=5 capture; candidates within 2pp','max median Q','min median pre-peak MAE','max >=3 capture','max watch Entry rate'],'candidate_scope':'both per-family four-policy panels and global eight-policy candidates; deterministic P0,Q70 lexical tie order only after all specified ties','search_counts':{'hyperparameter':0,'family':0,'weight':0,'threshold':0,'bootstrap':0},'safety':SAFETY})
 print(json.dumps({'frozen':True,'P0_numeric':len(P0_NAMES),'P1_numeric':len(P0_NAMES+P1_NUM),'P1_categorical':len(P1_CAT),'fits_planned':30}))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['identity','grid','freeze']);args=parser.parse_args();globals()[args.stage]()
