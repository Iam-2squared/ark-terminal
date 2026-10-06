"""Small meaningful contract tests, no learner fits and no market replays."""
import math
import random
import numpy as np
from build_sign_view import sign_row
from sign_io import *
from sign_model import transform
from sign_policy import select_threshold, action, filter_metrics, gate

def independent_tau(history, alpha):
    from fractions import Fraction
    allowance=int(Fraction(alpha)*sum(r['y_neg']==0 for r in history))
    feasible=[s for s in sorted({r['score_neg'] for r in history}) if sum(r['y_neg']==0 and r['score_neg']>=s for r in history)<=allowance]
    return feasible[0] if feasible else None

def main():
    checks=[]
    def check(name,value):
        assert value,name;checks.append(name)
    base={'entry_id':'fixture','session':'2025-01-01','known':True,'buy_debit':'100','sell_credit':'100',
          'label_maturity':'2025-01-01T15:31:00+09:00'}
    for credit,status in [('100','EXACT_ZERO'),('100.000000000000000000000000000001','POSITIVE'),('99.999999999999999999999999999999','NEGATIVE')]:
        check('exact boundary '+status,sign_row({**base,'sell_credit':credit})['sign_status']==status)
    check('unknown != zero',sign_row({**base,'known':False})['sign_status']=='UNKNOWN')
    # Compare payloads without provenance, preserving all signed mathematics.
    for credit1,credit2 in [('100.0000001','1000000000'),('99.9999999','0.0000001')]:
        a=sign_row({**base,'sell_credit':credit1});b=sign_row({**base,'sell_credit':credit2})
        check('within sign magnitude source hash differs',a['source_hash']!=b['source_hash'])
        check('within sign view invariant',{k:v for k,v in a.items() if k!='source_hash'}=={k:v for k,v in b.items() if k!='source_hash'})
    rng=random.Random(57)
    for case in range(100):
        history=[{'entry_id':str(i),'session':'2025-01-'+str(i%10+1).zfill(2),'score_neg':rng.choice([.1,.3,.5,.7,.9]),
                  'y_neg':i%2,'execution_eligible':True,'model_prediction_valid':True,'label_maturity':'2025-01-11'} for i in range(120)]
        for alpha in ALPHAS:
            snapshot=select_threshold(history,alpha,'2025-02-01');tau=independent_tau(history,alpha)
            check('tau tie/floor minimal '+str(case)+' '+alpha,snapshot['tau']==tau)
            check('tau allowed positives '+str(case)+' '+alpha,tau is None or sum(r['y_neg']==0 and r['score_neg']>=tau for r in history)<=math.floor(float(alpha)*60))
    h=[{'entry_id':str(i),'session':'2025-01-'+str(i%5+1).zfill(2),'score_neg':.8,'y_neg':i%2,
        'execution_eligible':True,'model_prediction_valid':True,'label_maturity':'2025-01-11'} for i in range(120)]
    check('initial insufficient sessions OFF',select_threshold(h,'0.10','2025-02-01')['status']=='OFF_SUPPORT_ALL_PASS')
    for r in h:r['session']='2025-01-'+str(int(r['entry_id'])%10+1).zfill(2)
    check('no finite tau ALL_PASS',select_threshold(h,'0.10','2025-02-01')['tau'] is None)
    for r in h:r['label_maturity']='2025-03-01'
    check('immature history excluded',select_threshold(h,'0.10','2025-02-01')['CAL_N']==0)
    check('empty division null',filter_metrics([])['pass_negative_rate'] is None)
    allreject=[{'y_neg':i%2,'action':'REJECT'} for i in range(100)]
    check('all reject pass rate null',filter_metrics(allreject)['pass_negative_rate'] is None)
    for name,acts in [('allreject',allreject),('allpass',[{'y_neg':i%2,'action':'PASS'} for i in range(100)]),
                      ('unassessed',[{'y_neg':i%2,'action':'PASS_UNASSESSED_MODEL'} for i in range(100)])]:
        fm=filter_metrics(acts);bb=[{**fm,'CAL_support_met':True} for _ in range(8)]
        check('uninformative not success '+name,gate(fm,0 if name=='unassessed' else 1,bb,True)['status']!='SIGN_FILTER_STAGE1_REVIEW_CANDIDATE')
    train=[{'numeric':{'n':1},'categorical':{'c':'A'}},{'numeric':{'n':None},'categorical':{'c':'B'}}]
    test=[{'numeric':{'n':100},'categorical':{'c':'FUTURE'}}]
    x,z,prep=transform(train,test,['n'],[]);check('numeric only shape',x.shape==(2,2) and z.shape==(1,2))
    x,z,prep=transform(train,test,[],['c']);check('categorical only shape',x.shape==(2,3) and z.shape==(1,3))
    check('categorical future unknown',prep['categorical_train_vocab']['c']==['A','B','__UNKNOWN__'] and z[0,-1]==1)
    x,z,prep=transform(train,test,['n'],['c']);check('train only mean',prep['numeric_mean']==[.5,.5])
    altered=[{'numeric':{'n':-10000},'categorical':{'c':'SUFFIX'}}]
    x2,z2,prep2=transform(train,altered,['n'],['c']);check('future suffix not prep',prep==prep2 and np.array_equal(x,x2))
    save(OUT/'SYNTHETIC_SIGN_TESTS.json',{'status':'PASS','exact_jst':now(),'checks_N':len(checks),'checks':checks,
         'model_fits':0,'market_replays':0,'scope':'new sign/view, threshold ties/floor/support/sentinel, degenerate gate and empty-family shape only'})
    print(canonical({'synthetic_checks':len(checks),'status':'PASS','fits':0}))

if __name__=='__main__':main()
