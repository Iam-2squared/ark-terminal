"""Sequential rolling-origin manager. Fit and prediction views are disjoint."""
import os,sys,pickle,subprocess,shutil,collections,datetime
from common import *

def restrict_sources():
 for p in [INPUT,PRIVATE,ROOT/'project_sources']:p.chmod(0o700)
 for p in [ROOT,WORK,WORK/'implementation',WORK/'worker_views']:p.mkdir(exist_ok=True);p.chmod(0o755)

def view(path):
 path.mkdir(parents=True,exist_ok=True);path.chmod(0o700);os.chown(path,65534,65534);return path

def grant(path):os.chown(path,65534,65534);path.chmod(0o600)

def feature_view(r,trainlabel=None):
 z={k:r[k] for k in ['entry_id','feature_asof','numeric','categorical']}
 if trainlabel is not None:z['target']=target(unpack(trainlabel))
 assert set(z)<=set(['entry_id','feature_asof','numeric','categorical','target'])
 return z

def launch(v,mode,method):
 env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 r=subprocess.run([sys.executable,str(WORK/'implementation/worker.py'),str(v),mode,method],env=env,capture_output=True,text=True)
 (v/'worker.log').write_text(r.stdout+r.stderr)
 return r

def run(block):
 restrict_sources();features=rows(PRIVATE/'FEATURE_ROWS.jsonl.gz');fm={r['entry_id']:r for r in features}
 seal=read(PRIVATE/'INPUT_SEAL.json');assert pin(PRIVATE/'FEATURE_ROWS.jsonl.gz')==seal['features'];assert pin(PUB/'MODEL_PRECOMMIT.json')==seal['precommit'];assert pin(PUB/'FEATURE_FORMULAS_AND_SCHEMA.json')==seal['schema']
 code=read(PUB/'MODEL_PRECOMMIT.json')['precommit_implementation_pins']
 for name in ['common.py','features.py','worker.py','prepare.py']:assert pin(WORK/'implementation'/name)==code[name],'PRECOMMIT_CODE_CHANGED:'+name
 labels=rows(PRIVATE/'WARMUP_R_NEW.jsonl.gz')+rows(PRIVATE/'EVALUATION_R_NEW_REUSED.jsonl.gz');lm={r['entry_id']:r for r in labels};split=read(INPUT/'shared/inputs/split');sp=split['blocks'][block-1]
 checkpoints=read(PUB/'BLOCK_CHECKPOINTS.json')
 if block>1:assert block-1 in checkpoints['actual_GET_complete_blocks'],'PREVIOUS_BLOCK_NOT_ACTUALLY_READ_BACK'
 bd=PRIVATE/'blocks'/f'BLOCK_{block:02d}';bd.mkdir(parents=True,exist_ok=True)
 if (bd/'PREDICTION_SEAL.json').exists():
  s=read(bd/'PREDICTION_SEAL.json');assert pin(bd/'OOF_PROBABILITIES.jsonl.gz')==s['predictions'];print('Already sealed block reused; no fit.');return
 cutoff=stamp(min(sp['test']),0)
 train=[];excluded=collections.Counter();alltrain=[]
 for r in sorted(features,key=lambda r:r['entry_id']):
  if r['session'] not in sp['train']:continue
  l=lm[r['entry_id']];alltrain.append(r['entry_id'])
  if not l['known']:excluded['UNKNOWN_R']+=1;continue
  if not l['label_maturity'] or l['label_maturity']>=cutoff:excluded['IMMATURE_LABEL']+=1;continue
  if not r['price_available']:excluded['NO_LEGAL_RAW']+=1;continue
  if not r['state_evidence_ok']:excluded['STATE_EVIDENCE_GAP_COMMON_TRAIN_MASK']+=1;continue
  assert r['session']<min(sp['test']) and l['session']<min(sp['test']);train.append(feature_view(r,l))
 test=[r for r in sorted(features,key=lambda r:r['entry_id']) if r['session'] in sp['test']]
 counts=collections.Counter(r['target'] for r in train);ns=len({fm[r['entry_id']]['session'] for r in train});active=len(train)>=200 and ns>=10 and all(counts[k]>=3 for k in range(5));p0=[(counts[k]+.5)/(len(train)+2.5) for k in range(5)]
 manifest={'block':block,'train_sessions':sp['train'],'eval_sessions':sp['test'],'learning_cutoff':cutoff,'all_train_ID_N':len(alltrain),'same_method_train_IDs':[r['entry_id'] for r in train],'train_N':len(train),'known_mature_common_input_sessions':ns,'class_counts':[counts[k] for k in range(5)],'train_exclusions':dict(excluded),'support_active':active,'evaluation_IDs':[r['entry_id'] for r in test],'evaluation_N':len(test),'train_view_forbidden_fields_present':False,'predict_view_R_U_EXIT_suffix_fields_present':False,'B0_p5':p0,'input_seal':seal}
 save(bd/'TRAIN_ID_MANIFEST.json',manifest,once=True);ledger=read(PUB/'FIT_LEDGER.json');rep=read(PUB/'REPAIR_AND_ATTEMPT_LEDGER.json');allq=[];models={}
 for method in METHODS:
  mv=bd/method;mv.mkdir(exist_ok=True);good=[r for r in test if r['price_available'] and (r['state_evidence_ok'] or method=='D-PRICE')];qdict={};status='OFF_SUPPORT';modelhash=None
  if active:
   if not (mv/'model.pkl').exists():
    fv=view(WORK/'worker_views'/f'b{block:02d}_{method}_fit');gzsave(fv/'train.jsonl.gz',train);grant(fv/'train.jsonl.gz')
    row={'block':block,'method':method,'status':'FIT_STARTED','train_N':len(train),'train_sessions':ns,'class_counts':[counts[k] for k in range(5)],'train_ID_sha256':sha(canonical([r['entry_id'] for r in train])),'preprocessing_fit_count':1,'base_attempt_count':1,'eval_outcome_in_worker':False}
    ledger['rows'].append(row);ledger['base_attempt_N']+=1;ledger['preprocessing_fit_N']+=1;assert ledger['base_attempt_N']<=28 and len([r for r in ledger['rows'] if r['base_attempt_count']])<=28;save(PUB/'FIT_LEDGER.json',ledger)
    rep['fit_attempts'].append({'block':block,'method':method,'attempt':1,'status':'STARTED'});save(PUB/'REPAIR_AND_ATTEMPT_LEDGER.json',rep)
    result=launch(fv,'fit',method)
    if result.returncode!=0:
     row['status']='TECHNICAL_FIT_INTERRUPTED';rep['fit_attempts'][-1]['status']='INTERRUPTED';save(PUB/'FIT_LEDGER.json',ledger);save(PUB/'REPAIR_AND_ATTEMPT_LEDGER.json',rep);raise RuntimeError(result.stderr[-4000:])
    shutil.copyfile(fv/'model.pkl',mv/'model.pkl');shutil.copyfile(fv/'fit_result.json',mv/'fit_result.json');shutil.copyfile(fv/'train.jsonl.gz',mv/'TRAIN_ONLY_VIEW.jsonl.gz');shutil.copyfile(fv/'worker.log',mv/'fit_worker.log')
    fit=read(mv/'fit_result.json');row.update(fit);row['status']='FIT_CONVERGED' if fit['converged'] else 'FIT_NOT_CONVERGED';ledger['successful_fit_N']+=int(fit['converged']);rep['fit_attempts'][-1]['status']=row['status'];save(PUB/'FIT_LEDGER.json',ledger);save(PUB/'REPAIR_AND_ATTEMPT_LEDGER.json',rep)
   fit=read(mv/'fit_result.json');modelhash=pin(mv/'model.pkl')['sha256'];assert modelhash==fit['model_sha256'];status='ACTIVE' if fit['converged'] else 'NOT_CONVERGED'
   if fit['converged']:
    pv=view(WORK/'worker_views'/f'b{block:02d}_{method}_predict');rr=[feature_view(r) for r in good];gzsave(pv/'evaluate.jsonl.gz',rr);shutil.copyfile(mv/'model.pkl',pv/'model.pkl');grant(pv/'evaluate.jsonl.gz');grant(pv/'model.pkl')
    r=launch(pv,'predict',method)
    if r.returncode!=0:raise RuntimeError(r.stderr[-4000:])
    shutil.copyfile(pv/'probabilities.jsonl.gz',mv/'SEALED_ACTIVE_PREDICTIONS.jsonl.gz');shutil.copyfile(pv/'evaluate.jsonl.gz',mv/'PREDICT_ONLY_VIEW.jsonl.gz');qdict={r['entry_id']:r for r in rows(mv/'SEALED_ACTIVE_PREDICTIONS.jsonl.gz')}
   models[method]={'model':pin(mv/'model.pkl'),'fit':fit,'prediction':pin(mv/'SEALED_ACTIVE_PREDICTIONS.jsonl.gz') if qdict else None,'preprocessing_sha256':fit['preprocessing_sha256']}
  for r in test:
   base={'entry_id':r['entry_id'],'block':block,'method':method,'feature_asof':r['feature_asof'],'model_hash':modelhash,'price_available':r['price_available'],'State_evidence_ok':r['state_evidence_ok'],'B0_p5':p0,'p5':None,'q3':None,'q5':None,'q2':None,'qNEG':None,'status':status}
   if r['entry_id'] in qdict:base.update(qdict[r['entry_id']]);base['status']='ACTIVE'
   elif active and status=='ACTIVE':base['status']='UNASSESSED_NO_LEGAL_RAW' if not r['price_available'] else 'UNASSESSED_STATE_EVIDENCE_GAP'
   allq.append(base)
 gzsave(bd/'OOF_PROBABILITIES.jsonl.gz',allq,once=True)
 ps={'block':block,'predictions':pin(bd/'OOF_PROBABILITIES.jsonl.gz'),'row_order':'method declaration order then canonical Entry ID ascending','train_manifest':pin(bd/'TRAIN_ID_MANIFEST.json'),'models':models,'feature_source':seal,'eval_outcome_joined_before_seal':False,'model_attempt_N':sum(r['block']==block for r in ledger['rows']),'prediction_ROW_N':len(allq),'effective_prediction_N_by_method':{m:sum(r['method']==m and r['status']=='ACTIVE' for r in allq) for m in METHODS}}
 save(bd/'PREDICTION_SEAL.json',ps,once=True)
 # Only after seal: an evaluation view receives immutable q plus current R/U/R0.
 oldref={r['entry_id']:r for r in rows(INPUT/'rd01/rd01/private/RUNTIME_INPUTS.jsonl.gz')}
 joined=[{'prediction':q,'label':lm[q['entry_id']],'R0_reference':oldref[q['entry_id']]} for q in allq];assert pin(bd/'OOF_PROBABILITIES.jsonl.gz')==ps['predictions'];gzsave(bd/'EVALUATION_JOIN_AFTER_SEAL.jsonl.gz',joined,once=True)
 checkpoints['complete_blocks'].append(block);checkpoints['prediction_seals'][str(block)]={'predictions':ps['predictions'],'model_hashes':{m:z['model']['sha256'] for m,z in models.items()},'train_N':len(train),'train_class_counts':[counts[k] for k in range(5)],'effective_prediction_N_by_method':ps['effective_prediction_N_by_method']};save(PUB/'BLOCK_CHECKPOINTS.json',checkpoints)
 current=read(PUB/'CURRENT_STATE.json');current.update(stage=f'S2 BLOCK_{block:02d}_SEALED_AWAITING_ACTUAL_GET',base_fit_N=ledger['successful_fit_N'],feature_campaign_N=1);save(PUB/'CURRENT_STATE.json',current)
 print(json.dumps({'block':block,'train_N':len(train),'class_counts':[counts[k] for k in range(5)],'fits_cumulative':ledger['successful_fit_N'],'coverage':ps['effective_prediction_N_by_method'],'seal':'PASS'}))

def readback_complete(block):
 rb=read(WORK/'transport'/f'B{block:02d}'/'READBACK.json');assert all(r['actual_GET'] for r in rb['rows'])
 cp=read(PUB/'BLOCK_CHECKPOINTS.json');assert block in cp['complete_blocks'];cp['actual_GET_complete_blocks'].append(block);save(PUB/'BLOCK_CHECKPOINTS.json',cp)
 cr=read(PUB/'CURRENT_STATE.json');cr['stage']=f'S2 BLOCK_{block:02d}_ACTUAL_GET_COMPLETE';save(PUB/'CURRENT_STATE.json',cr)

if __name__=='__main__':
 if sys.argv[1]=='run':run(int(sys.argv[2]))
 else:readback_complete(int(sys.argv[2]))
