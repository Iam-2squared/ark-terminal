"""V4 exposed-only sanity. No fresh labels, no bootstrap, no promotion."""
from pathlib import Path
from collections import defaultdict
import json,csv,math,hashlib
import numpy as np
import MODEL_V5 as m
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def main():
 freeze=json.loads((R/'CALIBRATION_RESEARCH_PRECOMMIT_V5.json').read_text())
 for n,h in freeze['hashes'].items():assert m.sha(R/n)==h,'RESEARCH_PRECOMMIT_BREACH'
 manifest=json.loads((P/'DATASET_MANIFEST_PORTABLE_V4.json').read_text());features=[];targets={}
 for pair in manifest['pairs']:
  labs={x['row_key']:x['REAL']['CONTEXT_REVERSAL'] for x in map(json.loads,(P/pair['label_path']).open())}
  for r in map(json.loads,(P/pair['feature_path']).open()):
   if labs[r['row_key']]['available']:features.append(r);targets[r['row_key']]=labs[r['row_key']]
 features.sort(key=lambda r:r['row_key']);schema=json.loads((P/'FEATURE_SCHEMA_V4.json').read_text());split=json.loads((P/'SPLIT_REALIZED_V4.json').read_text());oof=[];selections=[]
 for fold in split['folds']:
  if not fold['initial_train_dates_sufficient']:continue
  train=[r for r in features if r['date'] in fold['train_dates'] and targets[r['row_key']]['label_end']<fold['test_start']];test=[r for r in features if r['date'] in fold['test_dates']]
  if not train or not test:continue
  for model in ['R1','R2']:
   raw,cal,path,art=m.fit(train,test,targets,model,schema,fold['train_dates'],'research',fold['fold'],'REAL');selections.append({'fold':fold['fold'],'model':model,'alpha':art['alpha'],'T':art['temperature'],'inner_plan':art['inner_plan'],'fallback_reason':art['fallback_reason'],'path':path,'SHA256':m.sha(R/path)})
   for i,r in enumerate(test):
    for calibrated,p in [(False,raw),(True,cal)]:oof.append({'row_key':r['row_key'],'date':r['date'],'security_id':r['security_id'],'session_id':r['session_id'],'fold':fold['fold'],'model':model,'control':'REAL','calibrated':calibrated,'actual':targets[r['row_key']]['target'],'predicted':m.CLASSES[int(p[i].argmax())],'probabilities':p[i].tolist(),'fit_path':path,'exposure':'V4_EXPOSED_RESEARCH_ONLY_NOT_FRESH'})
   print(json.dumps({'lane':'exposed_research','model':model,'fold':fold['fold'],'alpha':art['alpha'],'T':art['temperature'],'fallback':art['fallback_reason']}),flush=True)
 m.save('V5_CALIBRATION_RESEARCH_SELECTION.json',{'scope':'V4 exposed only','method':'ROLLING_INNER_OOF_TEMPERATURE_V1','selection':selections,'fresh_labels':0,'promotion_authorized':False,'new_bootstrap':0})
 with (R/'CALIBRATION_RESEARCH_OOF_V5.jsonl').open('x') as f:
  for r in oof:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
 output=[]
 for model in ['R1','R2']:
  for cal in [False,True]:
   for fold in [0,2,3]:
    rs=[r for r in oof if r['model']==model and r['calibrated']==cal and (not fold or r['fold']==fold)];p=np.array([r['probabilities'] for r in rs]);y=np.array([m.CLASSES.index(r['actual']) for r in rs]);pred=p.argmax(1);ll=-np.log(p[np.arange(len(rs)),y]);br=((p-np.eye(4)[y])**2).sum(1);mx=p.max(1);ece=0.;d=defaultdict(list)
    for i,r in enumerate(rs):d[r['date']].append(i)
    for b in range(10):
     ix=np.minimum((mx*10).astype(int),9)==b
     if ix.any():ece+=ix.mean()*abs(mx[ix].mean()-(pred[ix]==y[ix]).mean())
    output.append({'scope':'V4_EXPOSED_RESEARCH_ONLY_NOT_FRESH','model':model,'calibrated':cal,'fold':fold or 'ALL','N':len(rs),'dates':len(d),'row_LL':float(ll.mean()),'date_equal_LL':m.date_ll(p,y,rs),'Brier':float(br.mean()),'date_equal_Brier':sum(float(br[v].mean()) for v in d.values())/len(d),'ECE':float(ece),'accuracy':float((pred==y).mean()),'dangerous_numerator':int(sum((pred==0)&(y==1))),'dangerous_denominator':int(sum(pred==0)),'promotion_authorized':False})
 with (R/'V5_CALIBRATION_RESEARCH_EXPOSED_ONLY.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
 print(json.dumps({'summary':[r for r in output if r['fold']=='ALL'],'fits':len((R/'MODEL_EXECUTION_LEDGER_V5.jsonl').read_text().splitlines()),'fresh_labels':0}),flush=True)
if __name__=='__main__':main()
