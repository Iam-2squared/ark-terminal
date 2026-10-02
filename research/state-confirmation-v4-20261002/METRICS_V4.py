"""Aggregate fixed predictions; reuse the one saved bootstrap, no fits or draws."""
from pathlib import Path
from collections import Counter, defaultdict
import json, csv, math, hashlib
import numpy as np
R=Path(__file__).resolve().parent
SCHEMA=json.loads((R/'REVERSAL_TARGET_SCHEMA.json').read_text())
CLASSES=SCHEMA['classes']
BOOT=json.loads((R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').read_text())
DATES=BOOT['dates']; DI={d:i for i,d in enumerate(DATES)}
COUNTS=np.array([np.bincount(v,minlength=len(DATES)) for v in BOOT['draws']],float)
assert len(COUNTS)==1000
def save(n,x): (R/n).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def csvout(n,rows,columns=None):
    with (R/n).open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else columns or ['status'])
        writer.writeheader();writer.writerows(rows)
def loadcsv(n):return list(csv.DictReader((R/n).open()))
def ratio_draw(rows,numerator,denominator):
    a=np.zeros(len(DATES));b=a.copy()
    for row in rows:
        a[DI[row['date']]]+=int(numerator(row));b[DI[row['date']]]+=int(denominator(row))
    aa=COUNTS@a;bb=COUNTS@b
    return np.divide(aa,bb,out=np.full(1000,np.nan),where=bb>0)
def interval(draws,tail=.025):
    ok=draws[np.isfinite(draws)]
    return (float(np.quantile(ok,tail)),float(np.quantile(ok,1-tail)),len(ok)) if len(ok) else (None,None,0)
def cm(rows,classes):
    out=np.zeros((len(classes),len(classes)),int);idx={c:i for i,c in enumerate(classes)}
    for row in rows:out[idx[row['actual']],idx[row['predicted']]]+=1
    return out
def perclass(matrix,i):
    actual=int(matrix[i].sum());pred=int(matrix[:,i].sum());correct=int(matrix[i,i])
    p=correct/pred if pred else None;r=correct/actual if actual else None
    f=None if p is None or r is None else 2*p*r/(p+r) if p+r else 0.
    return {'Predicted_N':pred,'Correct_N':correct,'Precision':p,'Actual_N':actual,'Recalled_N':correct,'Recall':r,'F1':f}
def metrics(rows,classes):
    matrix=cm(rows,classes);pc=[perclass(matrix,i) for i in range(len(classes))]
    perdate=defaultdict(list)
    for row in rows:perdate[row['date']].append(row)
    def losses(rr):
        ll=[];br=[]
        for row in rr:
            idx=classes.index(row['actual']);p=row['probabilities']
            ll.append(-math.log(max(p[idx],1e-300)))
            br.append(sum((v-int(i==idx))**2 for i,v in enumerate(p)))
        return (float(np.mean(ll)),float(np.mean(br))) if rr else (None,None)
    ll,br=losses(rows);dl=[losses(rr) for rr in perdate.values()]
    ece=0.
    for bucket in range(10):
        rr=[r for r in rows if min(int(max(r['probabilities'])*10),9)==bucket]
        if rr:ece+=len(rr)/len(rows)*abs(np.mean([max(r['probabilities']) for r in rr])-np.mean([r['actual']==r['predicted'] for r in rr]))
    recalls=[x['Recall'] for x in pc if x['Recall'] is not None]
    return {'row_N':len(rows),'date_N':len(perdate),'security_N':len({r['security_id'] for r in rows}),
        'security_session_N':len({(r['security_id'],r['session_id']) for r in rows}), 'fold_N':len({r['fold'] for r in rows}),
        'accuracy':float(np.trace(matrix)/len(rows)) if rows else None,
        'balanced_accuracy':float(np.mean(recalls)) if recalls else None,
        'macro_precision':sum(x['Precision'] or 0 for x in pc)/len(classes),
        'macro_recall':sum(x['Recall'] or 0 for x in pc)/len(classes),
        'macro_F1':sum(x['F1'] or 0 for x in pc)/len(classes), 'Brier':br,'log_loss':ll,
        'date_equal_Brier':float(np.mean([x[1] for x in dl])) if dl else None,
        'date_equal_log_loss':float(np.mean([x[0] for x in dl])) if dl else None,'top_label_ECE':ece if rows else None}
def risk(rows,predicted='UP_CONTINUE',actual='DOWN_REVERSAL'):
    pn=sum(r['predicted']==predicted for r in rows);dn=sum(r['predicted']==predicted and r['actual']==actual for r in rows)
    lo,hi,valid=interval(ratio_draw(rows,lambda r:r['predicted']==predicted and r['actual']==actual,lambda r:r['predicted']==predicted))
    return {'predicted_N':pn,'opposite_actual_N':dn,'rate':dn/pn if pn else None,'CI95_low':lo,'CI95_high':hi,
        'valid_global_draws':valid,'date_N':len({r['date'] for r in rows if r['predicted']==predicted}),
        'security_N':len({r['security_id'] for r in rows if r['predicted']==predicted}),
        'row_N':len(rows),'cluster_CI_informative':len({r['date'] for r in rows if r['predicted']==predicted})>=2,'sampling_unit':'DATE_CLUSTER_REPEATED_ANCHORS_NOT_INDEPENDENT_TRADES'}
def precision_draw(rows,c):return ratio_draw(rows,lambda r:r['predicted']==c and r['actual']==c,lambda r:r['predicted']==c)
def danger_draw(rows):return ratio_draw(rows,lambda r:r['predicted']=='UP_CONTINUE' and r['actual']=='DOWN_REVERSAL',lambda r:r['predicted']=='UP_CONTINUE')
def sequence(row,length):
    history=[x['primary'] for x in row['anatomy_history']][-length:]
    return '>'.join(['<MISSING>']*(length-len(history))+history)
def main():
    rows=list(map(json.loads,(R/'OOF_ALL.jsonl').open()))
    groups=defaultdict(list);foldgroups=defaultdict(list)
    for row in rows:
        key=(row['task'],row['control'],row['model'],row['calibrated']);groups[key].append(row);foldgroups[key+(row['fold'],)].append(row)
    aggregate=[];byfold=[];pcs=[];matrices=[];buckets=[]
    for task in CLASSES:
        classes=CLASSES[task]
        for control in ['REAL','TRUE_NULL','SHIFT60']:
            for model in ['R0','R1','R2','R3','R4']:
                for cal in [False,True]:
                    key=(task,control,model,cal);rs=groups.get(key,[]);base=dict(task=task,control=control,model=model,calibrated=cal)
                    aggregate.append({**base,**metrics(rs,classes)})
                    for fold in [1,2,3]:byfold.append({**base,'fold':fold,**metrics(foldgroups.get(key+(fold,),[]),classes)})
                    matrix=cm(rs,classes)
                    for i,c in enumerate(classes):
                        pl,ph,pv=interval(precision_draw(rs,c));rl,rh,rv=interval(ratio_draw(rs,lambda r:r['actual']==c and r['predicted']==c,lambda r:r['actual']==c))
                        pcs.append({**base,'class':c,**perclass(matrix,i),'precision_CI95_low':pl,'precision_CI95_high':ph,'precision_valid_global_draws':pv,
                            'recall_CI95_low':rl,'recall_CI95_high':rh,'predicted_date_N':len({r['date'] for r in rs if r['predicted']==c}),
                            'actual_date_N':len({r['date'] for r in rs if r['actual']==c}),
                            'predicted_fold_N':len({r['fold'] for r in rs if r['predicted']==c}), 'actual_fold_N':len({r['fold'] for r in rs if r['actual']==c})})
                        for j,p in enumerate(classes):matrices.append({**base,'actual_class':c,'predicted_class':p,'N':int(matrix[i,j])})
                    for kind in ['TOP_LABEL']+(['DOWN_REVERSAL'] if task=='CONTEXT_REVERSAL' else []):
                        for bucket in range(10):
                            getprob=(lambda r:max(r['probabilities'])) if kind=='TOP_LABEL' else (lambda r:r['probabilities'][1])
                            rr=[r for r in rs if min(int(getprob(r)*10),9)==bucket]
                            actual=(lambda r:r['actual']==r['predicted']) if kind=='TOP_LABEL' else (lambda r:r['actual']=='DOWN_REVERSAL')
                            buckets.append({**base,'kind':kind,'bucket':bucket,'lower':bucket/10,'upper':(bucket+1)/10,'N':len(rr),
                                'mean_predicted_probability':float(np.mean([getprob(r) for r in rr])) if rr else None,
                                'empirical_rate':float(np.mean([actual(r) for r in rr])) if rr else None,'date_N':len({r['date'] for r in rr})})
    csvout('REVERSAL_METRICS_AGGREGATE_V4.csv',aggregate);csvout('REVERSAL_METRICS_BY_FOLD_V4.csv',byfold)
    csvout('REVERSAL_PER_CLASS_METRICS_V4.csv',pcs);csvout('REVERSAL_CONFUSION_MATRIX_V4.csv',matrices)
    csvout('CALIBRATION_METRICS_V4.csv',aggregate);csvout('CALIBRATION_BUCKETS_V4.csv',buckets)
    csvout('NEXTSTATE_9CLASS_V4.csv',[r for r in aggregate if r['task'].startswith('NEXT_')])
    csvout('CONFUSION_MATRIX_9STATE_V4.csv',[r for r in matrices if r['task'].startswith('NEXT_')])
    csvout('PER_STATE_PRECISION_RECALL_F1_V4.csv',[{**{k:v for k,v in r.items() if k!='class'},'State':r['class']} for r in pcs if r['task'].startswith('NEXT_')])
    features={}
    manifest=json.loads((R/'DATASET_MANIFEST_V4.json').read_text())
    for pair in manifest['pairs']:
        for row in map(json.loads,Path(pair['feature_path']).read_text().splitlines()):features[row['row_key']]=row
    riskrows=[];reverserows=[]
    for model in ['R0','R1','R2','R3','R4']:
        rs=groups.get(('CONTEXT_REVERSAL','REAL',model,True),[])
        subsets={('ALL','ALL'):rs}
        for kind,key in [('FOLD','fold'),('DATE','date'),('SECURITY','security_id'),('CURRENT_PRIMARY','current_primary')]:
            for value in sorted({r[key] for r in rs}):subsets[(kind,str(value))]=[r for r in rs if r[key]==value]
        for length in range(1,5):
            sub=defaultdict(list)
            for r in rs:sub[sequence(features[r['row_key']],length)].append(r)
            for s,rr in sorted(sub.items()):subsets[(f'SEQUENCE_LENGTH{length}',s)]=rr
        for (kind,key),rr in subsets.items():
            base={'task':'CONTEXT_REVERSAL','control':'REAL','model':model,'calibrated':True,'group_kind':kind,'group':key}
            riskrows.append({**base,**risk(rr)});reverserows.append({**base,**risk(rr,'DOWN_REVERSAL','UP_CONTINUE')})
    csvout('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv',riskrows);csvout('DOWN_TO_UP_FALSE_NEGATIVE_V4.csv',reverserows)
    anatomical=groups.get(('CONTEXT_REVERSAL','REAL','R0',False),[]);supportsummary=[]
    for length in range(1,5):
        sub=defaultdict(list)
        for row in anatomical:sub[sequence(features[row['row_key']],length)].append(row)
        table=[]
        for s,rr in sorted(sub.items(),key=lambda kv:(-len(kv[1]),kv[0])):
            counts=Counter(r['actual'] for r in rr);dn=len({r['date'] for r in rr});sn=len({r['security_id'] for r in rr})
            base={'length':length,'sequence':s,'history_complete':'<MISSING>' not in s,'N':len(rr),'date_N':dn,'security_N':sn,
                'supported_descriptive_sequence':len(rr)>=100 and dn>=8 and sn>=3 and '<MISSING>' not in s}
            for c in CLASSES['CONTEXT_REVERSAL']:
                lo,hi,valid=interval(ratio_draw(rr,lambda r:r['actual']==c,lambda r:True))
                base.update({c+'_N':counts[c],c+'_rate':counts[c]/len(rr),c+'_CI95_low':lo,c+'_CI95_high':hi,c+'_valid_global_draws':valid})
            table.append(base)
        csvout(f'PATH_ANATOMY_LENGTH{length}_V4.csv',table,['length','sequence','history_complete','N','date_N','security_N','supported_descriptive_sequence']+[c+s for c in CLASSES['CONTEXT_REVERSAL'] for s in ['_N','_rate','_CI95_low','_CI95_high','_valid_global_draws']])
        supportsummary.append({'length':length,'anchor_N':sum(x['N'] for x in table),'sequence_N':len(table),
            'complete_history_anchor_N':sum(x['N'] for x in table if x['history_complete']),
            'supported_sequence_N':sum(x['supported_descriptive_sequence'] for x in table),
            'largest_sequence_N':max((x['N'] for x in table),default=0)})
    csvout('PATH_ANATOMY_SUPPORT_SUMMARY_V4.csv',supportsummary)
    controls=[]
    for task in CLASSES:
        for control in ['TRUE_NULL','SHIFT60']:
            for cal in [False,True]:
                matched={}
                for model in ['R0','R1','R2','R3','R4']:
                    a={r['row_key']:r for r in groups.get((task,'REAL',model,cal),[])}
                    b={r['row_key']:r for r in groups.get((task,control,model,cal),[])}
                    keys=sorted(a.keys()&b.keys());matched[model]=([a[k] for k in keys],[b[k] for k in keys])
                bm1=metrics(matched['R1'][0],CLASSES[task]);bm2=metrics(matched['R1'][1],CLASSES[task])
                for model,(a,b) in matched.items():
                    am=metrics(a,CLASSES[task]);bm=metrics(b,CLASSES[task]);av=am['date_equal_log_loss'];bv=bm['date_equal_log_loss']
                    gain=(bm1['date_equal_log_loss']-av) if av is not None else None
                    cg=(bm2['date_equal_log_loss']-bv) if bv is not None else None
                    comparable=gain is not None and gain>0 and cg>=.9*gain
                    absolute=bv is not None and av is not None and bv<=av+1e-12
                    warning=model in ['R2','R3','R4'] and (comparable or absolute)
                    controls.append({'task':task,'control':control,'model':model,'calibrated':cal,'matched_row_N':len(a),
                        'date_N':am['date_N'],'fold_N':am['fold_N'],'matched_keys_PASS':[r['row_key'] for r in a]==[r['row_key'] for r in b],
                        'REAL_accuracy':am['accuracy'],'control_accuracy':bm['accuracy'],'REAL_log_loss':am['log_loss'],'control_log_loss':bm['log_loss'],
                        'REAL_date_equal_log_loss':av,'control_date_equal_log_loss':bv,'REAL_gain_vs_R1':gain,'control_gain_vs_R1':cg,
                        'warning':warning,'status':('TRUE_NULL_PRIMARY_INTEGRITY_FAILURE_IF_CALIBRATED_CONTEXT' if control=='TRUE_NULL' else 'REGIME_DEPENDENCE_STRESS_WARNING') if warning else 'NO_COMPARABLE_CONTROL_WARNING',
                        'control_class_support':json.dumps(dict(Counter(r['actual'] for r in b)),sort_keys=True)})
    csvout('NEGATIVE_CONTROL_V4.csv',controls);csvout('SHIFT60_STRESS_V4.csv',[r for r in controls if r['control']=='SHIFT60'])
    inc=[]
    for task in CLASSES:
        for cal in [False,True]:
            for base,model in [('R0','R1'),('R1','R2'),('R2','R3'),('R3','R4'),('R2','R4'),('R1','R3'),('R1','R4')]:
                a=groups.get((task,'REAL',base,cal),[]);b=groups.get((task,'REAL',model,cal),[])
                am=metrics(a,CLASSES[task]);bm=metrics(b,CLASSES[task]);item={'task':task,'calibrated':cal,'baseline':base,'model':model,'row_N':len(b)}
                for k in ['accuracy','macro_F1','balanced_accuracy','log_loss','Brier','date_equal_log_loss','date_equal_Brier']:
                    item[k+'_improvement']=(bm[k]-am[k])*(1 if k in ['accuracy','macro_F1','balanced_accuracy'] else -1) if bm[k] is not None and am[k] is not None else None
                if task=='CONTEXT_REVERSAL':
                    ar=risk(a);br=risk(b);lo,hi,valid=interval(danger_draw(a)-danger_draw(b))
                    item.update(dangerous_rate_improvement=ar['rate']-br['rate'] if ar['rate'] is not None and br['rate'] is not None else None,
                        dangerous_improvement_CI95_low=lo,dangerous_improvement_CI95_high=hi,dangerous_valid_draws=valid)
                else:item.update(dangerous_rate_improvement=None,dangerous_improvement_CI95_low=None,dangerous_improvement_CI95_high=None,dangerous_valid_draws=0)
                inc.append(item)
    csvout('R0_R1_R2_R3_R4_INCREMENTAL_V4.csv',inc)
    import ASSESS_V4
    import sys
    ASSESS_V4.main(sys.modules[__name__],groups,controls)
if __name__=='__main__':main()
