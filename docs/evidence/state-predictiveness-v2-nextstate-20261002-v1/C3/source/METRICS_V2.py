from pathlib import Path
from collections import defaultdict,Counter
import json,csv,math,numpy as np
R=Path(__file__).resolve().parent
def csvout(n,rs):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]) if rs else ['status']);w.writeheader();w.writerows(rs)
def save(n,x):(R/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def confusion(rs,classes):
 cm=np.zeros((len(classes),len(classes)),dtype=int);index={v:i for i,v in enumerate(classes)}
 for r in rs:cm[index[r['actual']],index[r['predicted']]]+=1
 return cm
def ratios(cm):
 tp=np.diag(cm);pred=cm.sum(0);actual=cm.sum(1);p=np.divide(tp,pred,out=np.full(len(tp),np.nan),where=pred>0);rec=np.divide(tp,actual,out=np.full(len(tp),np.nan),where=actual>0);f=np.divide(2*p*rec,p+rec,out=np.zeros(len(tp)),where=p+rec>0);f[~np.isfinite(p)|~np.isfinite(rec)]=np.nan;return p,rec,f
def maybe(v):return float(v) if np.isfinite(v) else None
def score(rs,classes):
 cm=confusion(rs,classes);p,rec,f=ratios(cm);ds=defaultdict(list);index={c:i for i,c in enumerate(classes)}
 for r in rs:ds[r['date']].append(r)
 def losses(rr):
  ll=[-math.log(r['probabilities'][index[r['actual']]]) for r in rr];br=[sum((v-int(i==index[r['actual']]))**2 for i,v in enumerate(r['probabilities'])) for r in rr];return sum(ll)/len(rr),sum(br)/len(rr)
 ll,br=losses(rs) if rs else (None,None);d=[losses(v) for v in ds.values()]
 return {'row_N':len(rs),'date_N':len(ds),'security_N':len({r['security_id'] for r in rs}),'security_session_N':len({(r['security_id'],r['session_id']) for r in rs}),'fold_N':len({r['fold'] for r in rs}),'accuracy':float(np.trace(cm)/cm.sum()) if cm.sum() else None,'balanced_accuracy':maybe(np.nanmean(rec)) if np.isfinite(rec).any() else None,'macro_precision':float(np.nan_to_num(p).mean()),'macro_recall':float(np.nan_to_num(rec).mean()),'macro_F1':float(np.nan_to_num(f).mean()),'Brier':br,'log_loss':ll,'date_equal_Brier':float(np.mean([x[1] for x in d])) if d else None,'date_equal_log_loss':float(np.mean([x[0] for x in d])) if d else None}
def metric_boot(rs,classes,dates,draws):
 cm=np.array([confusion([r for r in rs if r['date']==d],classes) for d in dates]);b=cm[draws].sum(1);tp=np.diagonal(b,axis1=1,axis2=2);pn=b.sum(1);an=b.sum(2);prec=np.divide(tp,pn,out=np.full(tp.shape,np.nan),where=pn>0);rec=np.divide(tp,an,out=np.full(tp.shape,np.nan),where=an>0)
 return prec,rec,b
def ci(a,tail=.025):
 a=np.asarray(a);a=a[np.isfinite(a)];return (None,None,0) if not len(a) else (float(np.quantile(a,tail)),float(np.quantile(a,1-tail)),len(a))
def main():
 rs=list(map(json.loads,(R/'OOF_ALL.jsonl').read_text().splitlines()));ts=json.loads((R/'TARGET_SCHEMA_V2.json').read_text());g=defaultdict(list);fg=defaultdict(list)
 for r in rs:g[(r['task'],r['control'],r['model'])].append(r);fg[(r['task'],r['control'],r['model'],r['fold'])].append(r)
 boot=json.loads((R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').read_text());dates=boot['dates'];draws=np.asarray(boot['draws']);assert len(draws)==1000
 ag=[];folds=[];states=[];cms=[];predsup=[];actsup=[];families={'motion':[],'context':[]};familycm=[];binary=[];bootcache={};cis=[]
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30']:
  classes=['NO_TRANSITION','TRANSITION'] if task=='TRANSITION_WITHIN30' else ts['class_order']
  for control in ['REAL','TRUE_NULL','SHIFT60']:
   for model in ['B0','B1','B2','B3']:
    rr=g.get((task,control,model),[]);m=score(rr,classes);ag.append({'task':task,'control':control,'model':model,**m});cm=confusion(rr,classes);p,re,f=ratios(cm);bp,br,bcm=metric_boot(rr,classes,dates,draws);bootcache[(task,control,model)]=bp
    for fold in [1,2,3]:folds.append({'task':task,'control':control,'model':model,'fold':fold,**score(fg.get((task,control,model,fold),[]),classes)})
    for i,a in enumerate(classes):
     lo,hi,valid=ci(bp[:,i]);rl,rh,rv=ci(br[:,i]);row={'task':task,'control':control,'model':model,'State':a,'Predicted_N':int(cm[:,i].sum()),'Correct_N':int(cm[i,i]),'Precision':maybe(p[i]),'Actual_N':int(cm[i,:].sum()),'Recalled_N':int(cm[i,i]),'Recall':maybe(re[i]),'F1':maybe(f[i]),'precision_CI95_low':lo,'precision_CI95_high':hi,'precision_valid_global_draws':valid,'recall_CI95_low':rl,'recall_CI95_high':rh,'predicted_date_N':len({r['date'] for r in rr if r['predicted']==a}),'actual_date_N':len({r['date'] for r in rr if r['actual']==a}),'predicted_fold_N':len({r['fold'] for r in rr if r['predicted']==a}),'actual_fold_N':len({r['fold'] for r in rr if r['actual']==a}),'false_positive_actual_breakdown':json.dumps({c:int(cm[j,i]) for j,c in enumerate(classes) if j!=i}),'false_negative_predicted_as':json.dumps({c:int(cm[i,j]) for j,c in enumerate(classes) if j!=i})}
     if task=='TRANSITION_WITHIN30':binary.append(row)
     else:
      states.append(row);predsup.append({k:row[k] for k in ['task','control','model','State','Predicted_N','Correct_N','predicted_date_N','predicted_fold_N']});actsup.append({k:row[k] for k in ['task','control','model','State','Actual_N','Recalled_N','actual_date_N','actual_fold_N']})
     for j,b in enumerate(classes):cms.append({'task':task,'control':control,'model':model,'actual_State':a,'predicted_State':b,'N':int(cm[i,j])})
    total=bcm.sum((1,2));accuracy=np.divide(np.trace(bcm,axis1=1,axis2=2),total,out=np.full(1000,np.nan),where=total>0);lo,hi,v=ci(accuracy);cis.append({'task':task,'control':control,'model':model,'metric':'accuracy','CI95_low':lo,'CI95_high':hi,'valid_global_vectors':v,'new_draws':0})
    if task=='TRANSITION_WITHIN30':continue
    for kind in ['motion','context']:
     mapping={s:fam for fam,stateset in ts[kind].items() for s in stateset};cl=list(ts[kind]);fr=[{**r,'actual':mapping[r['actual']],'predicted':mapping[r['predicted']]} for r in rr];fcm=confusion(fr,cl);fpr,fre,ff=ratios(fcm);fb,_,_=metric_boot(fr,cl,dates,draws)
     for i,fam in enumerate(cl):
      lo,hi,v=ci(fb[:,i]);families[kind].append({'task':task,'control':control,'model':model,'family':fam,'Predicted_N':int(fcm[:,i].sum()),'Correct_N':int(fcm[i,i]),'Precision':maybe(fpr[i]),'Actual_N':int(fcm[i].sum()),'Recall':maybe(fre[i]),'F1':maybe(ff[i]),'precision_CI95_low':lo,'precision_CI95_high':hi,'valid_global_vectors':v})
      for j,other in enumerate(cl):familycm.append({'task':task,'control':control,'model':model,'mapping':kind,'actual':fam,'predicted':other,'N':int(fcm[i,j])})
 csvout('MODEL_METRICS_AGGREGATE.csv',ag);csvout('MODEL_METRICS_BY_FOLD.csv',folds);csvout('PER_STATE_PRECISION_RECALL_F1.csv',states);csvout('PER_STATE_PREDICTED_SUPPORT.csv',predsup);csvout('PER_STATE_ACTUAL_SUPPORT.csv',actsup);csvout('CONFUSION_MATRIX_9STATE.csv',[r for r in cms if r['task']!='TRANSITION_WITHIN30']);csvout('TRANSITION_BINARY_METRICS.csv',binary);csvout('MOTION_FAMILY_METRICS.csv',families['motion']);csvout('TREND_CONTEXT_FAMILY_METRICS.csv',families['context']);csvout('FAMILY_CONFUSION_MATRIX.csv',familycm);csvout('BOOTSTRAP_METRIC_INTERVALS.csv',cis)
 increments=[]
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30']:
  for candidate,baseline in [('B1','B0'),('B2','B1'),('B3','B2'),('B3','B1')]:
   a=next(r for r in ag if r['task']==task and r['control']=='REAL' and r['model']==candidate);b=next(r for r in ag if r['task']==task and r['control']=='REAL' and r['model']==baseline)
   increments.append({'task':task,'candidate':candidate,'baseline':baseline,'accuracy_difference':None if a['accuracy'] is None or b['accuracy'] is None else a['accuracy']-b['accuracy'],'macro_F1_difference':a['macro_F1']-b['macro_F1'],'date_equal_log_loss_reduction':None if a['date_equal_log_loss'] is None or b['date_equal_log_loss'] is None else b['date_equal_log_loss']-a['date_equal_log_loss'],'date_equal_Brier_reduction':None if a['date_equal_Brier'] is None or b['date_equal_Brier'] is None else b['date_equal_Brier']-a['date_equal_Brier']})
 csvout('B1_B2_B3_INCREMENTAL.csv',increments)
 controls=[];stress=[]
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY','TRANSITION_WITHIN30']:
  classes=['NO_TRANSITION','TRANSITION'] if task=='TRANSITION_WITHIN30' else ts['class_order']
  for control in ['TRUE_NULL','SHIFT60']:
   for model in ['B0','B1','B2','B3']:
    cc=g.get((task,control,model),[]);keys={r['row_key'] for r in cc};rr=[r for r in g.get((task,'REAL',model),[]) if r['row_key'] in keys];assert {r['row_key'] for r in rr}==keys
    cm=score(cc,classes);rm=score(rr,classes);cb=[r for r in g.get((task,control,'B1'),[]) if r['row_key'] in keys];rb=[r for r in g.get((task,'REAL','B1'),[]) if r['row_key'] in keys];cbm=score(cb,classes);rbm=score(rb,classes)
    cg=None if cm['date_equal_log_loss'] is None or cbm['date_equal_log_loss'] is None else cbm['date_equal_log_loss']-cm['date_equal_log_loss'];rg=None if rm['date_equal_log_loss'] is None or rbm['date_equal_log_loss'] is None else rbm['date_equal_log_loss']-rm['date_equal_log_loss'];comparably=cg is not None and rg is not None and rg>0 and cg>0 and cg>=.9*rg;absolute=cm['log_loss'] is not None and rm['log_loss'] is not None and cm['log_loss']<=rm['log_loss'];warning=(comparably or absolute) and model!='B0'
    controls.append({'task':task,'control':control,'model':model,'matched_row_N':len(keys),'date_N':cm['date_N'],'fold_N':cm['fold_N'],'matched_keys_PASS':True,'REAL_accuracy':rm['accuracy'],'control_accuracy':cm['accuracy'],'REAL_log_loss':rm['log_loss'],'control_log_loss':cm['log_loss'],'REAL_date_equal_log_loss':rm['date_equal_log_loss'],'control_date_equal_log_loss':cm['date_equal_log_loss'],'REAL_gain_vs_B1':rg,'control_gain_vs_B1':cg,'comparable_positive_gain':comparably,'absolute_control_as_good':absolute,'warning':warning,'status':('REGIME_PERSISTENCE_OR_SHIFT_CONTROL_WARNING' if control=='SHIFT60' else 'TRUE_NULL_WARNING_PROMOTION_VETO') if warning else 'NO_COMPARABLE_CONTROL_WARNING','class_support':json.dumps(dict(Counter(r['actual'] for r in cc)))})
    if control=='SHIFT60':stress.append(controls[-1])
 csvout('NEGATIVE_CONTROL_V2.csv',controls);csvout('SHIFT60_STRESS_V2.csv',stress)
 price=list(csv.DictReader((R/'PRICE_SECONDARY_OOF.csv').open()));pg=defaultdict(list);pfg=defaultdict(list)
 for r in price:pg[(int(r['horizon']),r['model'])].append(r);pfg[(int(r['horizon']),r['model'],r['fold'])].append(r)
 def pm(rr):
  errors=[(float(r['y'])-float(r['prediction']))**2 for r in rr];mae=[abs(float(r['y'])-float(r['prediction'])) for r in rr];d=defaultdict(list)
  for e,r in zip(errors,rr):d[r['date']].append(e)
  return {'row_N':len(rr),'date_N':len(d),'fold_N':len({r['fold'] for r in rr}),'MSE':float(np.mean(errors)) if errors else None,'MAE':float(np.mean(mae)) if errors else None,'date_equal_MSE':float(np.mean([np.mean(v) for v in d.values()])) if d else None}
 pmetrics=[{'version':'V2','horizon':h,'model':m,**pm(rr)} for (h,m),rr in sorted(pg.items())]
 old=list(csv.DictReader((R.parent/'state_predictiveness_20261002_v1/METRICS_AGGREGATE.csv').open()))
 for v in old:
  if v['control']=='REAL':pmetrics.append({'version':'V1_RETAINED','horizon':int(v['horizon']),'model':v['model'],'row_N':int(v['row_N']),'date_N':int(v['date_N']),'fold_N':2,'MSE':float(v['MSE']),'MAE':float(v['MAE']),'date_equal_MSE':float(v['date_equal_MSE'])})
 csvout('PRICE_SECONDARY_V2.csv',pmetrics);csvout('PRICE_SECONDARY_BY_FOLD_V2.csv',[{'horizon':h,'model':m,'fold':f,**pm(rr)} for (h,m,f),rr in sorted(pfg.items())])
 proposals=[];concentrations=[]
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']:
  for model in ['B2','B3']:
   candidates=g.get((task,'REAL',model),[]);base={r['row_key']:r for r in g.get((task,'REAL','B1'),[])};metrics=next(a for a in ag if a['task']==task and a['control']=='REAL' and a['model']==model);bm=next(a for a in ag if a['task']==task and a['control']=='REAL' and a['model']=='B1');cal=metrics['date_equal_Brier'] is not None and bm['date_equal_Brier'] is not None and metrics['date_equal_Brier']<=bm['date_equal_Brier'] and metrics['date_equal_log_loss']<=bm['date_equal_log_loss'];nullveto=next(c['warning'] for c in controls if c['task']==task and c['model']==model and c['control']=='TRUE_NULL')
   for i,state in enumerate(ts['class_order']):
    a=next(x for x in states if x['task']==task and x['control']=='REAL' and x['model']==model and x['State']==state);b=next(x for x in states if x['task']==task and x['control']=='REAL' and x['model']=='B1' and x['State']==state);diff=bootcache[(task,'REAL',model)][:,i]-bootcache[(task,'REAL','B1')][:,i];lo,hi,n=ci(diff,1/720);positivefolds=0
    for fold in [1,2,3]:
     ar=fg.get((task,'REAL',model,fold),[]);br=fg.get((task,'REAL','B1',fold),[]);acm=confusion(ar,ts['class_order']);bcm=confusion(br,ts['class_order']);av=ratios(acm)[0][i];bv=ratios(bcm)[0][i]
     positivefolds+=int(acm[:,i].sum()>0 and acm[i].sum()>0 and np.isfinite(av) and np.isfinite(bv) and av>bv)
    gross=Counter();sgross=Counter()
    for r in candidates:
     brr=base[r['row_key']];gain=int(r['predicted']==state and r['actual']==state)-int(brr['predicted']==state and brr['actual']==state)
     if gain>0:gross[r['date']]+=gain;sgross[r['security_id']]+=gain
    total=sum(gross.values());ds=None if not total else max(gross.values())/total;ss=None if not total else max(sgross.values())/total
    adequate=a['Predicted_N']>=50 and a['Actual_N']>=50 and metrics['date_N']>=6 and a['predicted_fold_N']>=2 and a['actual_fold_N']>=2
    concentration=ds is not None and ss is not None and ds<=.5 and ss<=.5;passed=adequate and positivefolds>=2 and lo is not None and lo>0 and cal and concentration and not nullveto
    proposals.append({'task':task,'model':model,'State':state,'support_adequate':adequate,'precision_improvement_vs_B1':None if a['Precision'] is None or b['Precision'] is None else a['Precision']-b['Precision'],'adjusted_CI_low':lo,'adjusted_CI_high':hi,'valid_vectors':n,'positive_folds':positivefolds,'global_calibration_not_worse':cal,'max_date_gross_positive_share':ds,'max_security_gross_positive_share':ss,'true_null_veto':nullveto,'promotable':passed,'status':'PROMOTABLE_DEV_CANDIDATE' if passed else 'MEASURED_NO_PROMOTION' if adequate else 'MEASURED_INSUFFICIENT_SUPPORT'})
 csvout('STATE_PROMOTION_ASSESSMENT.csv',proposals)
 core=next(x for x in ag if x['task']=='NEXT_DISTINCT_PRIMARY' and x['model']=='B3' and x['control']=='REAL');split=json.loads((R/'SPLIT_REALIZED_V2.json').read_text());sample=core['date_N']<6 or split['mode']!='V2_NEW_DEV_EVAL' or not any(x['support_adequate'] for x in proposals if x['task']=='NEXT_DISTINCT_PRIMARY');promoted=[p for p in proposals if p['task']=='NEXT_DISTINCT_PRIMARY' and p['promotable']]
 status='STATE_NEXTSTATE_PREDICTIVENESS_LIMITED_SAMPLE' if sample else 'STATE_NEXTSTATE_PREDICTIVENESS_DEV_CANDIDATE_READY_FOR_ENTRY_DESIGN' if promoted else 'STATE_NEXTSTATE_PREDICTIVENESS_MEASURED_NO_PROMOTABLE_STATE'
 save('GATE_ASSESSMENT_V2.json',{'provisional_status_pending_independent_audit':status,'core_OOF_date_N':core['date_N'],'core_evaluable_fold_N':core['fold_N'],'sample_status':'INSUFFICIENT_DEV_EVAL' if core['date_N']<6 else 'LIMITED_BUT_EVALUABLE' if core['date_N']<12 else 'GOOD','promoted_states':promoted,'true_null_warnings':sum(c['warning'] for c in controls if c['control']=='TRUE_NULL'),'SHIFT60_warnings':sum(c['warning'] for c in controls if c['control']=='SHIFT60'),'actual_future_leakage_proven':False,'D_not_used_for_low_accuracy':True,'independent_audit_pending':True})
 print(json.dumps({'provisional_status':status,'core':core,'controls':sum(c['warning'] for c in controls)}))
if __name__=='__main__':main()
