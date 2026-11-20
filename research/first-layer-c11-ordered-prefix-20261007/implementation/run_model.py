"""Exactly one fixed C11 sign-only HGB fit per S1/S2; no parent reruns."""
import argparse,datetime as dt,hashlib,math,os,pathlib,pickle,sys,time
import numpy as np,sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from threadpoolctl import threadpool_limits
from common import ROOT,PUB,PRIV,canonical,clock,dump,read,sha,pin,gzrows,seal_rows,event,checkpoint
from operating_policy import cal_point,decide

PARENT=ROOT.parent/'recovery/saved_parent/nc09_c10'

def run(stage):
 assert stage=='C11';pre=read(PUB/(stage+'_PRECOMMIT.json'));receipt=read(PUB/(stage+'_PRECOMMIT_READBACK.json'))
 assert receipt['status']=='PASS' and receipt['precommit_sha256']==sha(PUB/(stage+'_PRECOMMIT.json')),'PRECOMMIT_NOT_READ_BACK'
 assert not (PRIV/stage/'COMPLETE.json').exists(),'ALREADY_COMPLETED_NO_DOUBLE_FIT'
 assert sklearn.__version__==pre['runtime']['sklearn'] and np.__version__==pre['runtime']['numpy']
 assert pre['options']['max_leaf_nodes']==7 and pre['options']==read(PARENT/'public/C10_PRECOMMIT.json')['options']
 if stage=='C11':
  qa=read(PUB/'C11_CAUSAL_QA.json');assert qa['status']=='PASS' and qa['mismatch_N']==0 and qa['all1600_future_suffix_mutation_cases']==1600
  assert qa['field_registry']==pin(PUB/'C11_FIELD_REGISTRY.json')
  assert pin(ROOT/'ordered_prefix.py')==qa['builder'] and pin(ROOT/'build_features.py')==qa['assembly']
 lock=read(PUB/'C11_IMPLEMENTATION_LOCK.json');assert read(PUB/'C11_QA_READBACK.json')['status']=='PASS'
 for n,p in lock['implementation_pins'].items():assert pin(ROOT/n)==p,n
 splits=read(PARENT/'private/SPLITS_S1_S2.json');feature_seal=read(PUB/'C11_FEATURE_SEAL.json')
 matrix_root=PRIV/'INPUTS'
 # Runtime access guard applies to project data reads, not installed library code.
 allowed={str((PUB/n).resolve()) for n in ['BUDGET_LEDGER.json','SOURCE_PIN.json']}
 allowed.update(str((PARENT/'private/C08'/b/n).resolve()) for b in ['S1','S2'] for n in ['FIT_SIGN_ONLY_INPUT.json','FIT_ROW_IDS.json','CAL_ROW_IDS.json','DEV_COMPARE_ROW_IDS.json','CAL_SIGN_ONLY_INPUT.json','CAL_PREDICTIONS.jsonl.gz','DECISIONS.jsonl.gz','PREPROCESSOR.json','COLUMN_SELECTION.json'])
 allowed.update(str((matrix_root/b/n).resolve()) for b in ['S1','S2'] for n in ['FIT_MATRIX.npy','CAL_MATRIX.npy','DEV_COMPARE_MATRIX.npy'])
 allowed.update(str((PARENT/'private/C08'/b/'FIT_Y_SIGN_ONLY.npy').resolve()) for b in ['S1','S2'])
 # Hash the freshly written outputs without granting access to evaluation joins.
 output_names=['HGB_MODEL.pkl','MODEL.json','CAL_SELECTION_INPUT.json','THRESHOLDS.json','CAL_SCORES_DECISIONS.jsonl.gz','DEV_COMPARE_SCORES_DECISIONS.jsonl.gz','PREDICTION_SEAL.json']
 allowed.update(str((PRIV/stage/b/n).resolve()) for b in ['S1','S2'] for n in output_names)
 allowed.update(str((PRIV/stage/n).resolve()) for n in ['DEV_SCORES_DECISIONS.jsonl.gz','COMPLETE.json'])
 rootpath=str(ROOT.parent.resolve())+'/'
 def guard(name,args):
  if name!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
  p=str(pathlib.Path(args[0]).resolve());mode=args[1] if len(args)>1 else None;flags=args[2] if len(args)>2 else 0
  writing=isinstance(mode,str) and any(c in mode for c in 'wax+') or isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT))
  if p.startswith(rootpath) and not writing and p not in allowed:raise PermissionError('MODEL_INPUT_CAPABILITY_REFUSED:'+p)
 sys.addaudithook(guard)
 event('CYCLE_STARTED',candidate=stage,phase='SEARCH',fixed_config_sha256=hashlib.sha256(canonical(pre['options'])).hexdigest())
 all_dec=[];manifests=[]
 for block in ['S1','S2']:
  b=next(x for x in splits if x['block']==block);base=PARENT/'private/C08'/block;inputd=matrix_root/block;dest=PRIV/stage/block;dest.mkdir(parents=True,exist_ok=True)
  assert not (dest/'HGB_MODEL.pkl').exists(),'PARTIAL_MODEL_REQUIRES_EXPLICIT_TECHNICAL_RESUME'
  X=np.load(inputd/'FIT_MATRIX.npy',allow_pickle=False);y=np.load(base/'FIT_Y_SIGN_ONLY.npy',allow_pickle=False)
  fit_sign=read(base/'FIT_SIGN_ONLY_INPUT.json');fit_ids=read(base/'FIT_ROW_IDS.json')
  assert set(np.unique(y))=={0,1} and len(y)==len(fit_ids)==len(fit_sign)
  assert all(set(r)=={'entry_id','session','sign_status','y_plus','label_maturity','source_hash'} for r in fit_sign)
  assert all(r['entry_id']==i and r['y_plus']==int(v) and r['sign_status'] in ['PLUS','MINUS'] and r['label_maturity']<b['FIT_maturity_before'] for r,i,v in zip(fit_sign,fit_ids,y))
  expected=feature_seal['blocks'][block]['matrices']
  for n,p in expected.items():assert pin(inputd/n)==p,('MATRIX_PIN_MISMATCH',stage,block,n)
  event('MODEL_FIT_STARTED',candidate=stage,block=block,phase='SEARCH',rows=len(y),columns=X.shape[1],teacher='SIGN_ONLY',sample_weight=None)
  checkpoint(stage+'_'+block+'_FIT_STARTED','Complete this one committed fit then seal CAL/DEV scores; no band labels.',rows=len(y),columns=X.shape[1])
  t0=time.monotonic()
  model=HistGradientBoostingClassifier(**pre['options'])
  with threadpool_limits(limits=1):model.fit(X,y)
  assert model.n_iter_==pre['options']['max_iter'] and model.classes_.tolist()==[0,1]
  with (dest/'HGB_MODEL.pkl').open('wb') as f:pickle.dump(model,f,protocol=5)
  meta={'family':'HGB7','options':pre['options'],'stage':stage,'block':block,'runtime':pre['runtime'],'FIT_N':len(y),'FIT_PLUS_N':int(y.sum()),'columns':X.shape[1],'model_pickle':pin(dest/'HGB_MODEL.pkl'),'base_preprocessor':pin(base/'PREPROCESSOR.json'),'base_column_selection':pin(base/'COLUMN_SELECTION.json'),'input_matrices':expected,'FIT_sign_input':pin(base/'FIT_SIGN_ONLY_INPUT.json'),'R_or_bucket_input':False,'new_preprocessing_fit':0,'fit_seconds':time.monotonic()-t0,'clock':clock()}
  dump(dest/'MODEL.json',meta);event('MODEL_FIT_SUCCESS',candidate=stage,block=block,phase='SEARCH')
  scores={};row_ids={};old={}
  for role,original in [('CAL','CAL_PREDICTIONS.jsonl.gz'),('DEV_COMPARE','DECISIONS.jsonl.gz')]:
   M=np.load(inputd/(role+'_MATRIX.npy'),allow_pickle=False);ids=read(base/(role+'_ROW_IDS.json'));legacy=gzrows(base/original)
   assert [r['entry_id'] for r in legacy]==ids and set(ids)==set(b[role+'_Entry_IDs'])
   with threadpool_limits(limits=1):eta=model.decision_function(M)
   assert len(eta)==len(ids) and np.isfinite(eta).all();scores[role]=eta;row_ids[role]=ids;old[role]=legacy
  signs=read(base/'CAL_SIGN_ONLY_INPUT.json');sm={r['entry_id']:r for r in signs}
  assert set(sm)==set(row_ids['CAL'])
  cal_only=[{'entry_id':i,'eta':float(e),'sign_status':sm[i]['sign_status'] if sm[i]['sign_status'] in ['PLUS','MINUS'] and sm[i]['label_maturity']<b['CAL_maturity_before'] else 'UNKNOWN'} for i,e in zip(row_ids['CAL'],scores['CAL'])]
  dump(dest/'CAL_SELECTION_INPUT.json',{'rows':cal_only,'CAL_ID_sha256':b['CAL_ID_sha256'],'CAL_maturity_before':b['CAL_maturity_before'],'input_fields':['entry_id','eta','sign_status'],'R_or_DEV_labels':False})
  thresholds={}
  for point in pre['thresholds']['points']:
   th=cal_point(cal_only,point);assert th['threshold'] is not None,('CAL_SUPPORT_OR_FALLBACK_UNAVAILABLE',stage,block,point)
   counts={s:{'N':0,'KEEP':0,'DROP':0} for s in ['PLUS','MINUS','UNKNOWN']}
   for r in cal_only:c=counts[r['sign_status']];c['N']+=1;c[decide(r['eta'],th['threshold'])]+=1
   thresholds[point]={**th,'CAL_counts':counts,'block':block,'stage':stage,'operating_point':point,'selection_input_sha256':sha(dest/'CAL_SELECTION_INPUT.json'),'CAL_ID_sha256':b['CAL_ID_sha256']}
   if point=='CAL95':event('CAL95_REFERENCE_DECIDED',candidate=stage,block=block,point=point)
   elif point!='ALL_KEEP':event('THRESHOLD_DECIDED',candidate=stage,block=block,point=point,gamma_percent=th['gamma_percent'])
  dump(dest/'THRESHOLDS.json',thresholds)
  blockseals={}
  for role in ['CAL','DEV_COMPARE']:
   rr=[]
   for i,(identity,e,legacy) in enumerate(zip(row_ids[role],scores[role],old[role])):
    rr.append({'entry_id':identity,'session':legacy['session'],'block':block,'model':stage,'eta':float(e),'score_ieee754_hex':float(e).hex(),'current_state_available':legacy['current_state_available'],'history_available':legacy['history_available'],'base_feature_sha256':legacy['feature_sha256'],'matrix_source_sha256':expected[role+'_MATRIX.npy']['sha256'],'model_sha256':sha(dest/'MODEL.json'),'decisions':{p:decide(float(e),thresholds[p]['threshold']) for p in pre['thresholds']['points']}})
   seal=seal_rows(dest/(role+'_SCORES_DECISIONS.jsonl.gz'),rr);blockseals[role]=seal
   if role=='DEV_COMPARE':all_dec+=rr
  seal={'clock':clock(),'model':pin(dest/'MODEL.json'),'pickle':pin(dest/'HGB_MODEL.pkl'),'thresholds':pin(dest/'THRESHOLDS.json'),'selection_input':pin(dest/'CAL_SELECTION_INPUT.json'),'scores':blockseals,'new_fit':1,'new_preprocessing_fit':0,'winner_R_read':0,'DEV_label_read':0,'input_capability_guard':True,'precommit_sha256':receipt['precommit_sha256']}
  dump(dest/'PREDICTION_SEAL.json',seal);manifests.append({'block':block,**seal})
  checkpoint(stage+'_'+block+'_SEALED','Proceed fixed next block; no winner join until both blocks sealed.',score_N=len(scores['DEV_COMPARE']))
  print({'stage':stage,'block':block,'fit_N':len(y),'columns':X.shape[1],'CAL_N':len(scores['CAL']),'DEV_N':len(scores['DEV_COMPARE']),'winner_opened':False},flush=True)
 total=seal_rows(PRIV/stage/'DEV_SCORES_DECISIONS.jsonl.gz',all_dec)
 complete={'clock':clock(),'status':'ALL_STAGE_DECISIONS_SEALED_BEFORE_WINNER_JOIN','stage':stage,'blocks':manifests,'DEV_union_seal':total,'new_fit':2,'new_preprocessing_fit':0,'new_aggressive_thresholds':10,'new_fixed_CAL95_references':2,'all_CAL_calculations':12,'REPORT501_new':0,'options_sha256':hashlib.sha256(canonical(pre['options'])).hexdigest(),'precommit_sha256':receipt['precommit_sha256']}
 dump(PRIV/stage/'COMPLETE.json',complete);dump(PUB/(stage+'_PREDICTION_SEAL.json'),complete)
 event('CYCLE_COMPLETED',candidate=stage,phase='SEARCH');checkpoint(stage+'_STAGE_SEALED','Save sealed predictions, then join frozen322 winner bands for evaluation. No automatic C12.')

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('stage',choices=['C11']);run(a.parse_args().stage)
