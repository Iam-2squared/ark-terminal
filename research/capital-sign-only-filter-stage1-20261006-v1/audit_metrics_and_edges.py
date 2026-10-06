"""Additional independent probability metrics, auxiliary slices and degenerate gates."""
import csv
import math
from collections import Counter
from sign_io import *

def conf(data):
    c=Counter(('N' if r['y_neg']==1 else 'P')+('_reject' if r['action']=='REJECT' else '_keep') for r in data if r['y_neg'] is not None)
    return {k:c[k] for k in ['P_keep','P_reject','N_keep','N_reject']}

def average_precision(values):
    groups={}
    for score,label in values:
        p,n=groups.get(score,(0,0));groups[score]=(p+label,n+1)
    positive=sum(y for _,y in values)
    if not positive:return None
    tp=seen=0;total=0
    for score in sorted(groups,reverse=True):
        gp,gn=groups[score];tp+=gp;seen+=gn;total+=(gp/positive)*(tp/seen)
    return total

def main():
    checks=[]
    def check(name,value):assert value,name;checks.append(name)
    j=read(OUT/'SIGN_METRICS.json');target={r['entry_id']:r for r in rows(PRIVATE/'SIGN_LABEL_VIEW.jsonl.gz')}
    runtime=rows(PRIVATE/'INPUT_ROWS.jsonl.gz');split=read(SPLIT);member={r['entry_id']:r for r in rows(PRIVATE/'AUXILIARY_MEMBERSHIP.jsonl.gz')}
    eligible={r['entry_id'] for r in runtime if r['execution_eligible'] and r['session'] in split['OOF38']}
    masks={'FROZEN_ENTRY_EXECUTION_ELIGIBLE':eligible,'ALL_ENTRY':{r['entry_id'] for r in runtime if r['session'] in split['OOF38']},
           'RANK_PASS':{k for k in eligible if member[k]['rank_pass']},'OLD_V5_PURCHASED':{k for k in eligible if member[k]['old_V5_purchased']}}
    pred=rows(PRIVATE/'INITIAL_OOF_PREDICTIONS.jsonl.gz');actions=rows(PRIVATE/'SIGN_FILTER_ACTIONS.jsonl.gz')
    eps=2.220446049250313e-16
    for recipe,by in j['metrics'].items():
        for mask,metrics in by.items():
            valid=[r for r in pred if r['recipe']==recipe and r['entry_id'] in masks[mask] and r['model_prediction_valid'] and target[r['entry_id']]['y_neg'] is not None]
            values=[(r['score_neg'],target[r['entry_id']]['y_neg']) for r in valid]
            apneg=average_precision(values);appos=average_precision([(1-s,1-y) for s,y in values])
            brier=sum((s-y)**2 for s,y in values)/len(values) if values else None
            loss=-sum(y*math.log(min(1-eps,max(eps,s)))+(1-y)*math.log(1-min(1-eps,max(eps,s))) for s,y in values)/len(values) if values else None
            for name,value in [('AP_neg',apneg),('AP_pos',appos),('Brier',brier),('log_loss',loss)]:
                saved=metrics['binary_0.5'][name];check('independent '+recipe+' '+mask+' '+name,value==saved or value is not None and abs(value-saved)<1e-12)
            for alpha,fm in metrics['filters'].items():
                data=[{**a,**target[a['entry_id']]} for a in actions if a['recipe']==recipe and a['alpha']==alpha and a['entry_id'] in masks[mask]]
                computed=conf(data);check('same frozen decisions slice '+recipe+' '+mask+' '+alpha,all(computed[k]==fm[k] for k in computed))
    with (OUT/'BLOCK_METRICS.csv').open() as f:blocks=list(csv.DictReader(f))
    for block in blocks:
        data=[{**a,**target[a['entry_id']]} for a in actions if a['recipe']==block['recipe'] and a['alpha']==block['alpha'] and a['block']==int(block['block']) and a['entry_id'] in eligible]
        computed=conf(data);check('all block confusion '+block['recipe']+str(block['block'])+block['alpha'],all(computed[k]==int(block[k]) for k in computed))
    # Degenerate binary predictions also imply a degenerate count-budget filter.
    # Calling frozen policy for these fixture tests is separate from independent metric calculations above.
    from sign_policy import select_threshold,action,filter_metrics,gate
    for name,score in [('ALL_NEGATIVE_PREDICTION',1.0),('ALL_POSITIVE_PREDICTION',0.0)]:
        history=[{'entry_id':str(i),'session':'2025-01-'+str(i%10+1).zfill(2),'score_neg':score,'y_neg':i%2,
                  'model_prediction_valid':True,'execution_eligible':True,'label_maturity':'2025-01-11'} for i in range(120)]
        snap=select_threshold(history,'0.10','2025-02-01');check(name+' ALL_PASS sentinel',snap['tau'] is None)
        data=[{**r,'action':action(r,snap)} for r in history];fm=filter_metrics(data)
        check(name+' cannot success',gate(fm,1,[{**fm,'CAL_support_met':True} for _ in range(8)],True)['status']!='SIGN_FILTER_STAGE1_REVIEW_CANDIDATE')
    snap={'status':'ACTIVE','tau':.7}
    p={'execution_eligible':True,'model_prediction_valid':False,'score_neg':.99}
    check('unavailable score cannot reject',action(p,snap)=='PASS_UNASSESSED_MODEL')
    p={'execution_eligible':False,'model_prediction_valid':True,'score_neg':.99}
    check('ineligible independent coverage',action(p,snap)=='PASS_UNASSESSED_INELIGIBLE')
    # Optimistic apparent counts cannot rescue model coverage dominated by unavailable rows.
    fm=filter_metrics([{'y_neg':0,'action':'PASS'} for _ in range(100)]+[{'y_neg':1,'action':'REJECT'} for _ in range(50)]+[{'y_neg':1,'action':'PASS_UNASSESSED_MODEL'} for _ in range(50)])
    check('unavailable-heavy gate cannot success',gate(fm,.5,[{**fm,'CAL_support_met':True} for _ in range(8)],True)['status']!='SIGN_FILTER_STAGE1_REVIEW_CANDIDATE')
    data=rows(PRIVATE/'OOF_PASS_HANDOFF.jsonl.gz')
    check('handoff is runtime PASS with unknown retained',len(data)==986 and all(r['action']!='REJECT' for r in data))
    check('handoff contains actual negatives',sum(target[r['entry_id']]['y_neg']==1 for r in data)==528)
    check('handoff not oracle positive',sum(target[r['entry_id']]['y_neg']==0 for r in data)==447 and sum(target[r['entry_id']]['sign_status']=='UNKNOWN' for r in data)==11)
    save(OUT/'SUPPLEMENTAL_SIGN_AUDIT.json',{'status':'PASS','exact_jst':now(),'checks_N':len(checks),'checks':checks,
      'independent_metrics':['AP_neg','AP_pos','Brier','log_loss','all4slice count matrices','all192block count matrices'],
      'fixture_tests':['all-negative','all-positive','unavailable','ineligible','coverage-dominated gate'],
      'independent_metric_policy_imports':0,'fixture_policy_imports':'only synthetic edge cases after independent metric checks',
      'new_fit':0,'replay':0,'retune':0})
    print(canonical({'supplemental_sign_audit':'PASS','checks_N':len(checks),'fit':0}))

if __name__=='__main__':main()
