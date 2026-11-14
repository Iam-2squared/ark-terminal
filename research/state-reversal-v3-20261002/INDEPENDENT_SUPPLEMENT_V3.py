"""Complete calibration, incremental, promotion and image-source verification."""
from pathlib import Path
from collections import defaultdict,Counter
import json,csv,math,hashlib
import numpy as np
import INDEPENDENT_AUDIT_V3 as ref
R=Path(__file__).resolve().parent
def read(n):return list(csv.DictReader((R/n).open()))
def n(v):return None if v in [None,''] else float(v)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    classes=json.loads((R/'REVERSAL_TARGET_SCHEMA.json').read_text())['classes'];groups=defaultdict(list)
    for row in map(json.loads,(R/'OOF_ALL.jsonl').read_text().splitlines()):groups[(row['task'],row['control'],row['model'],row['calibrated'])].append(row)
    metric={k:ref.metric_ref(rr,classes[k[0]])[0] for k,rr in groups.items()}
    boot=json.loads((R/'BOOTSTRAP_GLOBAL_DATE_DRAWS.json').read_text());days=boot['dates'];idx={d:i for i,d in enumerate(days)};draws=np.asarray([np.bincount(v,minlength=len(days)) for v in boot['draws']],float)
    def ratio(rr,a,b):
        aa=np.zeros(len(days));bb=aa.copy()
        for r in rr:aa[idx[r['date']]]+=bool(a(r));bb[idx[r['date']]]+=bool(b(r))
        av=draws@aa;bv=draws@bb;return np.divide(av,bv,out=np.full(1000,np.nan),where=bv>0)
    def interval(v,tail=.025):
        ok=v[np.isfinite(v)];return (float(np.quantile(ok,tail)),float(np.quantile(ok,1-tail)),len(ok)) if len(ok) else (None,None,0)
    def danger(rr):return ratio(rr,lambda r:r['predicted']=='UP_CONTINUE' and r['actual']=='DOWN_REVERSAL',lambda r:r['predicted']=='UP_CONTINUE')
    for row in read('CALIBRATION_BUCKETS.csv'):
        key=(row['task'],row['control'],row['model'],row['calibrated']=='True');rr=groups[key]
        p=(lambda r:max(r['probabilities'])) if row['kind']=='TOP_LABEL' else (lambda r:r['probabilities'][1])
        a=(lambda r:r['predicted']==r['actual']) if row['kind']=='TOP_LABEL' else (lambda r:r['actual']=='DOWN_REVERSAL')
        rr=[r for r in rr if min(int(p(r)*10),9)==int(row['bucket'])]
        ref.check(int(row['N'])==len(rr) and int(row['date_N'])==len({r['date'] for r in rr}) and ref.near(n(row['mean_predicted_probability']),sum(p(r) for r in rr)/len(rr) if rr else None) and ref.near(n(row['empirical_rate']),sum(a(r) for r in rr)/len(rr) if rr else None),'calibration_bucket_exact',key)
    for row in read('R0_R1_R2_R3_R4_INCREMENTAL.csv'):
        cal=row['calibrated']=='True';a=metric[(row['task'],'REAL',row['baseline'],cal)];b=metric[(row['task'],'REAL',row['model'],cal)]
        for name in ['accuracy','macro_F1','balanced_accuracy','log_loss','Brier','date_equal_log_loss','date_equal_Brier']:
            expected=(b[name]-a[name])*(1 if name in ['accuracy','macro_F1','balanced_accuracy'] else -1) if a[name] is not None and b[name] is not None else None
            ref.check(ref.near(expected,n(row[name+'_improvement'])),'incremental_metric_direct',row['task']+':'+row['model'])
        if row['task']=='CONTEXT_REVERSAL':
            aa=groups[(row['task'],'REAL',row['baseline'],cal)];bb=groups[(row['task'],'REAL',row['model'],cal)];lo,hi,valid=interval(danger(aa)-danger(bb));ref.check(ref.near(lo,n(row['dangerous_improvement_CI95_low'])) and ref.near(hi,n(row['dangerous_improvement_CI95_high'])) and valid==int(row['dangerous_valid_draws']),'incremental_risk_saved_CI',row['model'])
    controls=read('NEGATIVE_CONTROL_V3.csv')
    for row in controls:
        task=row['task'];cal=row['calibrated']=='True';control=row['control'];model=row['model'];maps={}
        for m in [model,'R1']:
            a={r['row_key']:r for r in groups[(task,'REAL',m,cal)]};b={r['row_key']:r for r in groups[(task,control,m,cal)]};keys=sorted(a.keys()&b.keys());maps[m]=([a[k] for k in keys],[b[k] for k in keys])
        ma,mb=maps[model];ba,bb=maps['R1'];gm=ref.metric_ref(ba,classes[task])[0]['date_equal_log_loss']-ref.metric_ref(ma,classes[task])[0]['date_equal_log_loss'];gc=ref.metric_ref(bb,classes[task])[0]['date_equal_log_loss']-ref.metric_ref(mb,classes[task])[0]['date_equal_log_loss']
        ref.check(ref.near(gm,n(row['REAL_gain_vs_R1'])) and ref.near(gc,n(row['control_gain_vs_R1'])),'control_baseline_gain_exact',task+':'+model)
    for row in read('PROMOTION_GATE_V3.csv'):
        rr=groups[('CONTEXT_REVERSAL','REAL',row['model'],True)];bb=groups[('CONTEXT_REVERSAL','REAL',row['baseline'],True)];c=row['class'];cl=classes['CONTEXT_REVERSAL'];m=ref.metric_ref(rr,cl);b=ref.metric_ref(bb,cl)
        positive=0
        for fold in [1,2,3]:
            v=ref.metric_ref([r for r in rr if r['fold']==fold],cl)[2][cl.index(c)]['Precision'];bv=ref.metric_ref([r for r in bb if r['fold']==fold],cl)[2][cl.index(c)]['Precision'];positive+=v is not None and bv is not None and v>bv
        calibration=m[0]['date_equal_log_loss']<=1.05*b[0]['date_equal_log_loss'] and m[0]['date_equal_Brier']<=1.05*b[0]['date_equal_Brier'];recall=m[2][1]['Recall']>=b[2][1]['Recall']-.02
        old={r['row_key']:r for r in bb};gain=[r for r in rr if r['actual']==c and r['predicted']==c and not(old[r['row_key']]['actual']==c and old[r['row_key']]['predicted']==c)]
        dc=Counter(r['date'] for r in gain);sc=Counter(r['security_id'] for r in gain);ds=max(dc.values())/len(gain) if gain else None;ss=max(sc.values())/len(gain) if gain else None
        veto=any(x['task']=='CONTEXT_REVERSAL' and x['control']=='TRUE_NULL' and x['model']==row['model'] and x['calibrated']=='True' and x['warning']=='True' for x in controls)
        ref.check(positive==int(row['positive_precision_folds']) and calibration==(row['calibration_not_extremely_worse']=='True') and recall==(row['DOWN_recall_not_worse_by_more_than_02']=='True'),'promotion_folds_calibration_recall_direct',row['model']+':'+c)
        ref.check(len(gain)==int(row['gross_positive_correctness_N']) and ref.near(ds,n(row['max_date_gross_positive_share'])) and ref.near(ss,n(row['max_security_gross_positive_share'])) and veto==(row['true_null_veto']=='True'),'promotion_concentration_null_direct',row['model']+':'+c)
    chart=json.loads((R/'CHART_MANIFEST.json').read_text());ref.check(chart['unique_figures']==12,'required_chart_count')
    for f in chart['figures']:
        for name,h in f['source_CSVs'].items():ref.check(sha(R/name)==h,'chart_CSV_exact_hash',name)
        for kind in ['PNG','SVG']:ref.check((R/f[kind]).exists() and (R/f[kind]).stat().st_size>1000,'chart_file_present',f[kind])
    result={'status':'PASS' if ref.MISMATCH==0 else 'FAIL','assertion_N':sum(ref.CHECKS.values()),'mismatch_N':ref.MISMATCH,'counts':dict(ref.CHECKS),'errors':ref.ERRORS,
        'candidate_helper_imports':0,'new_fits':0,'new_draws':0,'new_kernel_steps':0,'provider_requests':0}
    (R/'INDEPENDENT_SUPPLEMENT_V3.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['counts','errors']}));print(json.dumps(ref.ERRORS[:5]))
    if ref.MISMATCH:raise SystemExit(1)
if __name__=='__main__':main()
