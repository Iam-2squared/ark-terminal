"""Prediction-only training CDF mapping. Does not read evaluation teachers."""
from control import *
from bisect import bisect_left
from collections import Counter
import numpy as np
LABELS=['P_HIGH','P_MID','P_BASE','P_BELOW']
def order(r):return (-r['pP'],r['entry_timestamp'],r['symbol'])
def predict(rr,a):
 p=a['preprocessing'];nf=p['numeric_fields'];cf=p['categorical_fields']
 vals=np.array([[float(r['numeric'][k]) if r['numeric'][k] is not None else np.nan for k in nf] for r in rr])
 x=(np.column_stack([np.nan_to_num(vals,nan=0),np.isnan(vals).astype(float)])-np.array(p['numeric_mean']))/np.array(p['numeric_scale'])
 cc=[]
 for k in cf:
  voc=p['categorical_train_vocab'][k];v=[r['categorical'][k] if r['categorical'][k] in voc else '__UNKNOWN__' for r in rr]
  cc.extend([[float(z==c) for z in v] for c in voc])
 xx=np.column_stack([x,np.array(cc).T]);logit=xx@np.array(a['coef'])+a['intercept']
 return np.exp(-np.logaddexp(0,-logit)).tolist()
def oldband(ml):return 'S' if ml>=2 else 'A' if ml>=1.5 else 'B' if ml>=1 else 'C'
def band_units(u,n,counts):
 acc=0
 for lb,old in zip(LABELS[:3],['S','A','B']):
  acc+=counts[old]
  if u>n-acc:return lb
 return LABELS[3]
def main():
 move={r['entry_id']:r for r in rows(INPUT/'movement/RUNTIME_CAUSAL.jsonl.gz')};core={r['entry_id']:r for r in rows(INPUT/'core/CORE_RUNTIME_CAUSAL.jsonl.gz')}
 stream=rows(INPUT/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz');split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')
 maps={};training=[];outputs=[];maxdiff=0
 for block in split['blocks']:
  b=block['block'];pm=read(INPUT/f'movement/models/MOVE_P_BLOCK_{b:02}.json');heads=[read(INPUT/f'current/models/H{h}_BLOCK_{b:02}.json') for h in (2,3,5)]
  ids=pm['train_entry_ids'];assert all(a['train_entry_ids']==ids for a in heads);assert len(ids)==pm['train_N']
  assert all(move[k]['session'] in block['train'] and move[k]['session']<min(block['test']) and move[k]['entry_minute']<920 for k in ids)
  assert pm['test_dates']==block['test'] and all(a['test_dates']==block['test'] for a in heads)
  pp=predict([move[k] for k in ids],pm);ph=[predict([core[k] for k in ids],a) for a in heads];base=sum(a['base_rate'] for a in heads)
  ml=[sum(v)/base for v in zip(*ph)];counts=Counter(oldband(z) for z in ml);counts={s:counts[s] for s in 'SABC'}
  rr=[dict(entry_id=k,session=move[k]['session'],entry_minute=move[k]['entry_minute'],entry_timestamp=move[k]['entry_timestamp'],symbol=move[k]['symbol'],pP=p,old_ML=z,old_band=oldband(z)) for k,p,z in zip(ids,pp,ml)]
  rr.sort(key=order);keys=[order(r) for r in rr];n=len(rr)
  for i,r in enumerate(rr):r.update(block=b,rank_units=n-i,train_N=n,r=(n-i)/n,band=band_units(n-i,n,counts))
  assert {lb:sum(r['band']==lb for r in rr) for lb in LABELS}==dict(zip(LABELS,[counts[s] for s in 'SABC']))
  test=[r for r in stream if r['block']==b];inferred=predict(test,pm);maxdiff=max(maxdiff,max(abs(r['pP']-p) for r,p in zip(test,inferred)))
  for r in test:
   units=n-bisect_left(keys,order(r));outputs.append({k:r[k] for k in ('entry_id','session','symbol','entry_minute','entry_timestamp','raw_reference','pP','block')}|{'rank_units':units,'train_N':n,'r':units/n,'band':band_units(units,n,counts),'liquidity':r['liquidity']})
  maps[str(b)]={'block':b,'train_N':n,'training_sessions':block['train'],'test_sessions':block['test'],'old_band_counts':counts,'band_counts_training':dict(zip(LABELS,[counts[s] for s in 'SABC'])),'boundary_rank_units':[n-counts['S'],n-counts['S']-counts['A'],counts['C']],'training_keys':[list(k) for k in keys],'training_scores_desc':[r['pP'] for r in rr],'model_sha256':sha(INPUT/f'movement/models/MOVE_P_BLOCK_{b:02}.json'),'current_model_sha256':{str(h):sha(INPUT/f'current/models/H{h}_BLOCK_{b:02}.json') for h in (2,3,5)},'no_test_outcome_read':True}
  training+=rr
 assert maxdiff<=1e-12
 outputs.sort(key=lambda r:(r['session'],r['entry_minute'],*order(r)))
 gzsave(PRIVATE/'TRAIN_MAPPED_SCORES.jsonl.gz',training);gzsave(PRIVATE/'RANK_NATIVE_RUNTIME.jsonl.gz',outputs)
 save(OUT/'RANK_NATIVE_BAND_MAP.json',{'exact_jst':now(),'blocks':{b:{k:v for k,v in m.items() if k not in ('training_keys','training_scores_desc')} for b,m in maps.items()},'basis_precommit_sha256':sha(OUT/'BAND_MAPPING_PRECOMMIT.json')})
 save(OUT/'TRAIN_SCORE_DISTRIBUTIONS.json',maps)
 save(OUT/'BAND_VOLUME_IDENTITY_AUDIT.json',{'exact_jst':now(),'training_volume_mismatch_N':0,'same_train_ID_mismatch_N':0,'strict_past_mismatch_N':0,'OOF_saved_score_max_abs_delta':maxdiff,'model_fits':0,'OOF_original_byte_hash_unchanged':sha(INPUT/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz'),'runtime_N':len(outputs),'pre_cutoff_N':sum(r['entry_minute']<920 for r in outputs),'test_volume_forced':False,'private_hashes':{f:sha(PRIVATE/f) for f in ('TRAIN_MAPPED_SCORES.jsonl.gz','RANK_NATIVE_RUNTIME.jsonl.gz')}})
 print(json.dumps({'training_volume_mismatch':0,'blocks':{b:m['old_band_counts'] for b,m in maps.items()},'prediction_max_delta':maxdiff,'runtime_N':len(outputs)}),flush=True)
def future():
 maps=read(OUT/'RANK_NATIVE_BAND_MAP.json')['blocks'];rr=rows(PRIVATE/'TRAIN_MAPPED_SCORES.jsonl.gz');tables={}
 for b,m in maps.items():
  train=[r for r in rr if r['block']==int(b) and r['band']!='P_BELOW'];sessions=m['training_sessions']
  tables[b]={'train_N':m['train_N'],'training_sessions':sessions,'minutes':{str(t):[max((r['rank_units'] for r in train if r['session']==day and t<r['entry_minute']<920),default=None) for day in sessions] for t in range(540,920)}}
 save(OUT/'FUTURE_MAX_RANK_TABLE.json',tables)
 save(OUT/'TABLE_CODE_INPUT_PIN.json',{'exact_jst':now(),'tables_sha256':sha(OUT/'FUTURE_MAX_RANK_TABLE.json'),'training_rows_sha256':sha(PRIVATE/'TRAIN_MAPPED_SCORES.jsonl.gz'),'mapping_code_sha256':sha(CODE/'mapping.py'),'future_label_read':0,'test_session_future_arrival_read':0,'exact_minute_range':[540,919]})
if __name__=='__main__':
 import sys
 (future if len(sys.argv)>1 and sys.argv[1]=='future' else main)()
