"""Separate saved-artifact validation; no candidate helper imports/fits/draws."""
from pathlib import Path
from collections import Counter,defaultdict
import json,math,csv,hashlib
import numpy as np
import FORENSICS_V5 as a
R=Path(__file__).resolve().parent;P=R/'PARENT_V4';C=a.C
def date_ll(p,y,rows):
 ds=defaultdict(list)
 for i,r in enumerate(rows):ds[r['date']].append(-math.log(float(p[i,y[i]])))
 return sum(sum(v)/len(v) for v in ds.values())/len(ds)
def replay(art,tr,te,labels,name):
 Y=np.eye(4)[[C.index(labels[r['row_key']]['target']) for r in tr]]
 if art['model']=='R2':return a.replay(art,tr,te,Y,name)
 w=a.weights(tr);prior=(Y*w[:,None]).sum(0)/w.sum();a.check(np.allclose(prior,art['prior'],atol=1e-8),'R1_prior',name);lookup={}
 for k in sorted({r['features']['formal_primary'] for r in tr}):
  ix=np.array([r['features']['formal_primary']==k for r in tr]);p=((Y[ix]*w[ix,None]).sum(0)+10*prior)/(w[ix].sum()+10);lookup[k]=p;a.check(np.allclose(p,art['lookup'][k],atol=1e-8),'R1_lookup',name)
 raw=np.array([lookup.get(r['features']['formal_primary'],prior) for r in te]);q=np.maximum(raw,1e-12);return q/q.sum(1,keepdims=True)
def pick(grid,key,order):
 best=min(x[key] for x in grid);return min([x for x in grid if x[key]<=best+1e-12],key=order)
def main():
 features={};labels={};manifest=a.read('DATASET_MANIFEST_PORTABLE_V4.json')
 for pair in manifest['pairs']:
  ls={r['row_key']:r['REAL']['CONTEXT_REVERSAL'] for r in map(json.loads,(P/pair['label_path']).open())}
  for r in map(json.loads,(P/pair['feature_path']).open()):
   if ls[r['row_key']]['available']:features[r['row_key']]=r;labels[r['row_key']]=ls[r['row_key']]
 split=a.read('SPLIT_REALIZED_V4.json');oof=list(map(json.loads,(R/'CALIBRATION_RESEARCH_OOF_V5.jsonl').open()));ordinals=[]
 for fp in sorted((R/'RESEARCH_FITTED').glob('*.json')):
  art=json.loads(fp.read_text());name=fp.name;fold=int(name.split('_F')[-1].split('.')[0]);outer=next(f for f in split['folds'] if f['fold']==fold);expected_train=[k for k,r in sorted(features.items()) if r['date'] in outer['train_dates'] and labels[k]['label_end']<outer['test_start']];expected_test=[k for k,r in sorted(features.items()) if r['date'] in outer['test_dates']]
  a.check(art['train_keys']==expected_train and art['test_keys']==expected_test,'exact_outer_train_test_keys',name);tr=[features[k] for k in expected_train];te=[features[k] for k in expected_test];raw=replay(art,tr,te,labels,name);ordinals.append(art['charged_fit_ordinal']);inner=defaultdict(list)
  dates=sorted(outer['train_dates']);q,rem=divmod(len(dates[5:]),4);blocks=[];start=5
  for b in range(4):n=q+(b<rem);blocks.append(dates[start:start+n]);start+=n
  a.check([p['validation_dates'] for p in art['inner_plan']]==blocks,'fixed_inner_calendar_blocks',name)
  for ix in art['inner_artifacts']:
   b=blocks[ix['inner_fold']-1];first=b[0]+'T00:00:00+09:00';it=[r for r in tr if r['date']<b[0] and labels[r['row_key']]['label_end']<first];iv=[r for r in tr if r['date'] in b]
   a.check(ix['train_keys']==[r['row_key'] for r in it] and ix['validation_keys']==[r['row_key'] for r in iv],'inner_train_only_purge_and_keys',name);p=replay(ix,it,iv,labels,name+':inner');iy=np.array([C.index(labels[r['row_key']]['target']) for r in iv]);a.check(np.allclose(p,ix['validation_probabilities'],atol=1e-8) and iy.tolist()==ix['validation_actual'],'inner_OOF_exact_replay',name)
   inner[ix['alpha']].extend({'row_key':r['row_key'],'date':r['date'],'inner_fold':ix['inner_fold'],'probabilities':p[i].tolist(),'actual':int(iy[i])} for i,r in enumerate(iv));ordinals.append(ix['charged_fit_ordinal'])
  grid=[{'alpha':alpha,'date_equal_LL':date_ll(np.array([r['probabilities'] for r in rr]),np.array([r['actual'] for r in rr]),rr)} for alpha,rr in inner.items()]
  alpha=pick(grid,'date_equal_LL',lambda x:-(x['alpha'] or 0))['alpha'];a.check(alpha==art['alpha'],'rolling_alpha_choice',name)
  for g in grid:a.check(any(s['alpha']==g['alpha'] and a.near(s['date_equal_LL'],g['date_equal_LL']) for s in art['alpha_receipt']),'rolling_alpha_LL',name)
  rr=inner[alpha];ip=np.array([r['probabilities'] for r in rr]);iy=np.array([r['actual'] for r in rr]);tg=[{'temperature':T,'date_equal_LL':date_ll(a.temperature(ip,T),iy,rr)} for T in [.5,.75,1,1.25,1.5,2]];en=len({r['inner_fold'] for r in rr});ds=len({r['date'] for r in rr});fallback=[]
  if en<2:fallback.append('INNER_EVALUABLE_FOLDS_LT2')
  if ds<5:fallback.append('INNER_OOF_DATES_LT5')
  if len(rr)<20:fallback.append('INNER_OOF_ROWS_LT20')
  T=1 if fallback else pick(tg,'date_equal_LL',lambda x:(abs(x['temperature']-1),-x['temperature']))['temperature'];a.check(T==art['temperature'] and fallback==art['fallback_reason'],'temperature_choice_and_fallback',name)
  for g in tg:a.check(any(s['temperature']==g['temperature'] and a.near(s['date_equal_LL'],g['date_equal_LL']) for s in art['temperature_receipt']),'temperature_grid_LL',name)
  for cal,p in [(False,raw),(True,a.temperature(raw,T))]:
   saved={r['row_key']:r for r in oof if r['fold']==fold and r['model']==art['model'] and r['calibrated']==cal}
   a.check(set(saved)==set(expected_test),'complete_outer_OOF',name)
   for i,r in enumerate(te):s=saved[r['row_key']];a.check(np.allclose(p[i],s['probabilities'],atol=1e-8) and s['predicted']==C[int(p[i].argmax())] and s['actual']==labels[r['row_key']]['target'],'outer_probabilities_and_labels',r['row_key'])
 ledger=list(map(json.loads,(R/'MODEL_EXECUTION_LEDGER_V5.jsonl').open()));a.check(sorted(ordinals)==list(range(1,37)) and len(ledger)==36 and all(l['lane']=='research' and l['charged_before_fit'] for l in ledger),'complete_append_before_fit_ledger')
 with (R/'V5_CALIBRATION_RESEARCH_EXPOSED_ONLY.csv').open() as f:
  for row in csv.DictReader(f):
   rs=[r for r in oof if r['model']==row['model'] and r['calibrated']==(row['calibrated']=='True') and (row['fold']=='ALL' or r['fold']==int(row['fold']))];p=np.array([r['probabilities'] for r in rs]);y=np.array([C.index(r['actual']) for r in rs]);br=((p-np.eye(4)[y])**2).sum(1)
   a.check(a.near(date_ll(p,y,rs),float(row['date_equal_LL'])) and a.near(br.mean(),float(row['Brier'])),'reported_probability_metrics')
 receipt={'status':'PASS' if not a.ERRORS else 'FAIL','mismatch_N':len(a.ERRORS),'counts':dict(a.CHECKS),'errors':a.ERRORS[:100],'new_fits':0,'new_bootstrap_draws':0,'new_fresh_labels':0,'candidate_helper_imports':0,'independent_logic':'separate forensic replay + independent rolling split/selection/metrics; no MODEL_V5 import','research_fit_N':36,'method_performance_not_promotion_gate':True};(R/'AUDIT_CALIBRATION_RESEARCH_V5.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k not in ['counts','errors']}));
 if a.ERRORS:raise RuntimeError('UNRECONCILED_RESEARCH_MISMATCH')
if __name__=='__main__':main()
