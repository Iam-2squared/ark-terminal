"""RD02 manager: pin sources, prepare prefix-only X and reuse immutable labels."""
import os, sys, zipfile, tarfile, importlib.util, collections, shutil
from common import *
from features import compute

def load_module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def sources():
 shared=read(INPUT/'shared_manifest.txt')
 for r in shared['members']:assert pin(INPUT/'shared'/r['path'])=={k:r[k] for k in ['bytes','sha256','git_blob']},r['path']
 rd=read(INPUT/'rd01/rd01/private/PRIVATE_MEMBER_MANIFEST.json')
 for r in rd['members']:assert pin(INPUT/'rd01'/r['path'])=={k:r[k] for k in ['bytes','sha256','git_blob']},r['path']
 p=INPUT/'rd01/rd01_sources/exitfreeze.json';assert pin(p)['sha256']=='a9845422555b478fe1ed34a95b97fa185f83c2c487c19926f72dbe628eec590d'
 assert pin(INPUT/'shared/native/staircase.py')['git_blob']=='6863b2dded50e4d0caa4e2d470619017fcf0b759'
 assert pin(INPUT/'numeric_adapter.py')['sha256']=='ddd1d3313ebfb67124cd4efc4ba17381c92dec27b3c10433d77116434e7ef994'
 tracepin=read(INPUT/'shared/inputs/STATE9_TRACE_ARCHIVE_BINDING.json')['archive_pin']
 assert pin(INPUT/'STATE9_V2_FROZEN_TRACE_ARCHIVE.zip')==tracepin
 core=rows(INPUT/'shared/inputs/core_runtime');split=read(INPUT/'shared/inputs/split')
 assert len(core)==len({r['entry_id'] for r in core})==1600
 assert {r['session'] for r in core}==set(split['all58'])
 return core,split

def build():
 dest=PRIVATE/'FEATURE_ROWS.jsonl.gz'
 if dest.exists():assert pin(dest)==read(PRIVATE/'INPUT_SEAL.json')['features'];print('Completed feature campaign reused.');return
 core,split=sources();books={r['entry_id']:r for r in rows(INPUT/'shared/inputs/books')}
 z=zipfile.ZipFile(INPUT/'STATE9_V2_FROZEN_TRACE_ARCHIVE.zip');manifest=json.loads(z.read('MANIFEST.json'));frozen=rows_from_bytes(z.read('FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'))
 frozen={r['watch_key']:r for r in frozen if r['entry_status']=='FIRST_ENTRY'}
 assert len(frozen)==1600 and frozen.keys()==books.keys()=={r['entry_id'] for r in core}
 oldlabels=rows(INPUT/'rd01/rd01/private/EVALUATION_ONLY_R_NEW.jsonl.gz');oldlabel={r['entry_id']:r for r in oldlabels}
 original_hash=pin(INPUT/'rd01/rd01/private/EVALUATION_ONLY_R_NEW.jsonl.gz');assert original_hash['sha256']=='2d6f17b9cb917bdd8d404a9db7ee1a6d0899b77ab37ed07175c7a56194fcffbb'
 assert len(oldlabels)==1039 and sum(r['known'] for r in oldlabels)==1016
 # Manager sees outcome sources; feature input views contain only an explicit
 # raw/State prefix and the original first-intent identity/cutoff.
 ex=load_module('rd02_native_execution',INPUT/'shared/native/execution.py')
 numeric=load_module('rd02_pinned_numeric',INPUT/'exit_completion/implementation/numeric_adapter.py')
 newfeatures=[];warm=[];prefixes=[];availability=[];binding=[];label_attempts=[];canary=[]
 support=collections.Counter();gaps=[]
 for orig in sorted(core,key=lambda r:r['entry_id']):
  key=orig['entry_id'];day=orig['session'];entry=frozen[key];intent=entry['first_intent'];tx=intent['intent_minute'];book=books[key]
  assert entry['fill_minute']==orig['entry_minute'] and entry['fill_timestamp']==orig['entry_timestamp']
  assert intent['row_id']==f'{key}|{tx}' and tx<=entry['fill_minute']
  member='FULL_TRACE/'+key.replace('|','_')+'.jsonl.gz';cp=manifest['components'][member];body=z.read(member)
  assert len(body)==cp['bytes'] and sha(body)==cp['sha256'];trace=rows_from_bytes(body)
  prefix=[r for r in trace if r['bar_end_minute']<=tx];raw=[r for r in book['market'] if r['minute']+1<=tx]
  x=compute(key,day,tx,raw,prefix);x['intent_row_id']=intent['row_id'];x['intent_row_index']=intent['row_index'];x['source_raw_member']='SHARED_INPUTS/inputs/books';x['source_raw_sha256']=next(r['sha256'] for r in read(INPUT/'shared_manifest.txt')['members'] if r['path']=='inputs/books');x['source_state_member']=member;x['source_state_member_sha256']=cp['sha256']
  pfx={'entry_id':key,'session':day,'intent_minute':tx,'market':raw,'trace':prefix,'intent_row_id':intent['row_id'],'intent_row_index':intent['row_index']}
  prefixes.append(pfx);newfeatures.append(x)
  # Each future-only perturbation is injected into the original source view.
  # Rebuild under the same cutoff, independent of labels/fill/legacy scores.
  for kind in ['FUTURE_RAW','FUTURE_STATE_EXIT_R_U','FILL_CLOCK_DELAY_OPEN']:
   m=list(raw);s=list(prefix)
   if kind=='FUTURE_RAW':m.append({'minute':tx,'session':day,'O':'99999','H':'999999','L':'0','C':'1','Vo':'999999999','Va':'999999999','lineage':{'canary':True}})
   elif kind=='FUTURE_STATE_EXIT_R_U':s.append({'bar_end_minute':tx+1,'state':{'future_R':'changed'},'future_exit':'SHARP_DROP','U':999})
   else:m.append({'minute':tx+100,'session':day,'O':'1','future_fill_clock':tx+100,'intent_to_actual_delay':100})
   y=compute(key,day,tx,m,s);assert canonical({k:x[k] for k in y})==canonical(y),(key,kind)
  canary.append({'entry_id':key,'future_raw_invariant':True,'future_state_exit_R_U_invariant':True,'actual_fill_delay_open_invariant':True})
  for field in PRICE+STATE+CAT:
   availability.append({'entry_id':key,'field':field,'available_at':x['max_raw_available_at'] if field in PRICE else x['max_state_available_at'],'missing':x['numeric'][field] is None if field in x['numeric'] else x['categorical'][field]=='UNKNOWN','missing_reason':x['missing_reason'].get(field) if field in x['numeric'] else 'UNKNOWN_CATEGORY' if x['categorical'][field]=='UNKNOWN' else None,'t_x':x['feature_asof'],'family_source_available':x['price_available'] if field in PRICE else x['state_evidence_ok']})
  binding.append({'entry_id':key,'intent_row_id':intent['row_id'],'intent_row_index':intent['row_index'],'intent_minute':tx,'raw_prefix_sha256':sha(canonical(raw)),'state_prefix_sha256':sha(canonical(prefix)),'trace_member':member,'trace_member_sha256':cp['sha256'],'max_raw_available_at':x['max_raw_available_at'],'max_state_available_at':x['max_state_available_at']})
  if not x['state_evidence_ok']:gaps.append(key)
  if key in oldlabel:continue
  assert day in split['warmup20'] if 'warmup20' in split else day in split['blocks'][0]['train']
  buymin=orig['entry_minute'];control=min(book['frozen_exit']['exit_intent']['minute'],920) if book['frozen_exit']['exit_intent'] else 920
  action='DELEGATE_CONTROL';it=control;reason=None
  from features import state_valid
  holding=[r for r in trace if buymin<r['bar_end_minute']<control]
  expected=[m+1 for m in regular_starts() if buymin<m+1<control]
  observed={r['bar_end_minute'] for r in holding}
  suffix_gap=[tm for tm in expected if tm not in observed]
  # Saved full trace supplies every inherited checkpoint, including valid
  # abstentions. Missing members fail source validation rather than no-trigger.
  for r in holding:
   if state_valid(r) and r['path']['Primary_or_null']=='SHARP_DROP':action='SD_FIRST';it=r['bar_end_minute'];break
  cf=ex.frozen_execution(book);cs=cf if cf is not None else ex.eod_source(book['market'],day)
  terminal=cs.get('source_minute') if cs and cs.get('price') else 930
  source=cs
  if action=='SD_FIRST':
   mf=[r for r in book['market'] if r['session']==day and r['minute']<=terminal]
   fill=numeric.resolve_fill({'session':day,'buy_fill_minute':buymin,'market':mf},it)
   if fill['status']=='FILLED':source={'price':str(Fraction(int(fill['effective_price_numerator']),int(fill['effective_price_denominator']))),'source_minute':fill['source_minute'],'release_minute':fill['source_available_minute'],'kind':'SHARP_DROP_FIRST_OBSERVED_EXIT_V0','lineage':fill['source_lineage']}
   else:source=None
  buy=Fraction(str(book['entry_actual_source']['O']))*Fraction('1.0005')*100
  if suffix_gap:reason='STATE_SUFFIX_EVIDENCE_GAP'
  elif buymin>=920:reason='ENTRY_AT_OR_AFTER_CANONICAL_EOD_INTENT'
  elif not ex.valid_market(book['entry_actual_source']):reason='BUY_SOURCE_UNAVAILABLE'
  elif source is None or source.get('blocked') or not source.get('price'):reason='LEGAL_SELL_SOURCE_UNAVAILABLE'
  elif source['release_minute']<=buymin:reason='SELL_RELEASE_NOT_AFTER_BUY'
  sell=Fraction(source['price'])*100 if reason is None else None
  ret=100*(sell/buy-1) if sell is not None else None
  label={'entry_id':key,'session':day,'block':0,'r_namespace':'R_NEW_SHARP_DROP_FIRST_OBSERVED_EXIT_V0_PCT_100SHARE','r_numerator':str(ret.numerator) if ret is not None else None,'r_denominator':str(ret.denominator) if ret is not None else None,'known':ret is not None,'unknown_reason':reason,'buy_debit_100':str(buy),'sell_credit_100':str(sell) if sell else None,'label_maturity':stamp(day,source['release_minute']) if ret is not None else None,'source_minute':source.get('source_minute') if source else None,'release_minute':source.get('release_minute') if source else None,'exit_action':action,'exit_intent_minute':it,'label_source':'RD02_UNSAVED_WARMUP_NEW_EXIT_ONLY'}
  warm.append(label);label_attempts.append({'entry_id':key,'attempt':1,'known':ret is not None,'unknown_reason':reason})
 assert len(newfeatures)==1600 and len(warm)==561 and len(label_attempts)==561
 assert pin(INPUT/'rd01/rd01/private/EVALUATION_ONLY_R_NEW.jsonl.gz')==original_hash
 gzsave(dest,newfeatures,once=True);gzsave(PRIVATE/'PREFIX_ONLY_INPUTS.jsonl.gz',prefixes,once=True);gzsave(PRIVATE/'WARMUP_R_NEW.jsonl.gz',warm,once=True)
 shutil.copyfile(INPUT/'rd01/rd01/private/EVALUATION_ONLY_R_NEW.jsonl.gz',PRIVATE/'EVALUATION_R_NEW_REUSED.jsonl.gz')
 gzsave(PRIVATE/'FEATURE_SOURCE_BINDING.jsonl.gz',binding,once=True);gzsave(PRIVATE/'FEATURE_CAUSALITY_CANARY_ID_ROWS.jsonl.gz',canary,once=True)
 save(PRIVATE/'WARMUP_LABEL_ATTEMPTS.json',label_attempts,once=True)
 import csv
 p=PRIVATE/'FEATURE_AVAILABILITY.csv'
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(availability[0]));w.writeheader();w.writerows(availability)
 save(PUB/'FEATURE_AVAILABILITY.csv_METADATA.json',{'private_file':'FEATURE_AVAILABILITY.csv','rows':len(availability),'feature_numeric_N':70,'feature_categorical_N':4,'individual_identifiers_public':False,'hash':pin(p)})
 save(PUB/'FEATURE_CAUSALITY_CANARY.json',{'tested_ID_N':1600,'future_raw_invariant_N':1600,'future_state_exit_R_U_invariant_N':1600,'fill_clock_delay_open_invariant_N':1600,'full_q_canary':'WILL_COMPARE_SAVED_MODEL_PREDICTIONS_IN_REPRODUCTION','actual_arrival':'UNKNOWN','identity_or_label_as_learning_feature':False,'duplicate_entry_train_expansion':0,'legacy_rank_score_in_X':False})
 save(PUB/'LABEL_REUSE_AND_WARMUP_MATERIALIZATION.json',{'evaluation_ID_N':1039,'evaluation_known_R_reused_N':1016,'evaluation_unknown_reused_N':23,'evaluation_regenerated_N':0,'evaluation_original_pin':original_hash,'warmup_ID_N':561,'warmup_attempt_N':561,'warmup_known_N':sum(r['known'] for r in warm),'warmup_unknown_N':sum(not r['known'] for r in warm),'warmup_unknown_reasons':dict(collections.Counter(r['unknown_reason'] for r in warm if not r['known'])),'State_kernel_runs':0,'provider_RAW_recovery':0,'new_namespace':True,'warmup_old_exit_R_used_as_new_R':False})
 save(PRIVATE/'INPUT_SEAL.json',{'features':pin(dest),'prefixes':pin(PRIVATE/'PREFIX_ONLY_INPUTS.jsonl.gz'),'warmup_labels':pin(PRIVATE/'WARMUP_R_NEW.jsonl.gz'),'evaluation_labels':original_hash,'schema':pin(PUB/'FEATURE_FORMULAS_AND_SCHEMA.json'),'precommit':pin(PUB/'MODEL_PRECOMMIT.json')},once=True)
 save(PUB/'INPUT_QUALITY_COUNTS.json',{'all_ID_N':1600,'evaluation_ID_N':1039,'raw_available_N':sum(x['price_available'] for x in newfeatures),'State_evidence_gap_N':len(gaps),'raw_unavailable_N':sum(not x['price_available'] for x in newfeatures),'unmapped_quality_reason_metadata_N':sum(x['quality_raw_category_unmapped'] is not None for x in newfeatures),'missing_is_zero_loss':False,'combined_price_fallback':False})
 print(json.dumps({'feature_ID_N':len(newfeatures),'warmup_known_N':sum(r['known'] for r in warm),'state_evidence_gap_N':len(gaps)}))

def rows_from_bytes(b):return [json.loads(x) for x in gzip.decompress(b).splitlines()]
if __name__=='__main__':build()
