"""Exactly one past-positive-count threshold procedure. No magnitude inputs."""
import math
from fractions import Fraction
from sign_io import *

def select_threshold(history, alpha, block_start):
    cal=[r for r in history if r['execution_eligible'] and r['model_prediction_valid']
         and r['y_neg'] is not None and r['label_maturity']<block_start]
    positive=sum(r['y_neg']==0 for r in cal); negative=sum(r['y_neg']==1 for r in cal)
    allowance=math.floor(Fraction(alpha)*positive)
    base={'alpha':alpha,'CAL_N':len(cal),'CAL_sessions':len({r['session'] for r in cal}),
          'CAL_positive_N':positive,'CAL_negative_N':negative,'allowed_positive_reject_N':allowance,
          'CAL_identity_sign_score_hash':digest([{k:r[k] for k in ['entry_id','session','score_neg','y_neg','label_maturity']} for r in cal]),
          'support_met':sufficient(cal),'tau':None,'status':'OFF_SUPPORT_ALL_PASS',
          'distinct_score_N':0,'distinct_tested_N':0,'sentinel':'ALL_PASS',
          'current_future_CAL_rows':0,'warmup_in_sample_rows':0,'tie_split':False}
    if not base['support_met']:return base
    scores=sorted({r['score_neg'] for r in cal});base['distinct_score_N']=len(scores)
    for i,tau in enumerate(scores,1):
        rejects=sum(r['y_neg']==0 and r['score_neg']>=tau for r in cal)
        if rejects<=allowance:
            base.update(tau=tau,status='ACTIVE',distinct_tested_N=i,CAL_positive_reject_N=rejects)
            return base
    base.update(status='OFF_NO_FINITE_TAU_ALL_PASS',distinct_tested_N=len(scores),CAL_positive_reject_N=0)
    return base

def action(prediction, snapshot):
    if not prediction['execution_eligible']:return 'PASS_UNASSESSED_INELIGIBLE'
    if not prediction['model_prediction_valid']:return 'PASS_UNASSESSED_MODEL'
    if snapshot['status']!='ACTIVE':return 'PASS_UNASSESSED_OFF'
    return 'REJECT' if prediction['score_neg']>=snapshot['tau'] else 'PASS'

def div(a,b):return a/b if b else None

def filter_metrics(values):
    known=[r for r in values if r['y_neg'] is not None]
    pk=sum(r['y_neg']==0 and r['action']!='REJECT' for r in known)
    pr=sum(r['y_neg']==0 and r['action']=='REJECT' for r in known)
    nk=sum(r['y_neg']==1 and r['action']!='REJECT' for r in known)
    nr=sum(r['y_neg']==1 and r['action']=='REJECT' for r in known)
    retention=div(pk,pk+pr);removal=div(nr,nk+nr);fpr=div(pr,pk+pr)
    return dict(known_N=len(known),P_keep=pk,N_keep=nk,P_reject=pr,N_reject=nr,
                positive_retention=retention,positive_false_reject=fpr,negative_removal=removal,
                pass_negative_rate=div(nk,pk+nk),reject_precision=div(nr,nr+pr),pass_rate=div(pk+nk,len(known)),
                J_sign=removal-fpr if removal is not None and fpr is not None else None,
                filter_balanced_accuracy=(removal+retention)/2 if removal is not None and retention is not None else None,
                PASS_UNASSESSED_known_N=sum(r['action'].startswith('PASS_UNASSESSED') for r in known),
                PASS_UNASSESSED_all_N=sum(r['action'].startswith('PASS_UNASSESSED') for r in values),
                PASS_all_N=sum(r['action']!='REJECT' for r in values),REJECT_all_N=sum(r['action']=='REJECT' for r in values),
                UNKNOWN_N=sum(r.get('sign_status')=='UNKNOWN' for r in values),EXACT_ZERO_N=sum(r.get('sign_status')=='EXACT_ZERO' for r in values))

def gate(primary, coverage, qualifying_blocks, audit_pass):
    stable=[r for r in qualifying_blocks if r['CAL_support_met'] and r['P_keep']+r['P_reject']>=10 and r['N_keep']+r['N_reject']>=10]
    base=div(primary['N_keep']+primary['N_reject'],primary['known_N'])
    checks={'audit_PASS':audit_pass,'actual_model_prediction_coverage_ge95':coverage>=.95,
            'positive_retention_ge90':primary['positive_retention'] is not None and primary['positive_retention']>=.90,
            'negative_removal_ge30':primary['negative_removal'] is not None and primary['negative_removal']>=.30,
            'pass_negative_rate_below_no_filter':primary['pass_negative_rate'] is not None and base is not None and primary['pass_negative_rate']<base,
            'at_least4_evaluable_supported_blocks':len(stable)>=4,
            'at_least75percent_J_positive':bool(stable) and sum(r['J_sign']>0 for r in stable)/len(stable)>=.75}
    if not audit_pass:status='SIGN_FILTER_BLOCKED'
    elif all(checks.values()):status='SIGN_FILTER_STAGE1_REVIEW_CANDIDATE'
    elif primary['J_sign'] is None or primary['J_sign']<=0:status='SIGN_FILTER_NO_SEPARATION'
    else:status='SIGN_FILTER_TRADEOFF_ONLY'
    return {'status':status,'checks':checks,'evaluable_block_N':len(stable),'J_positive_block_N':sum(r['J_sign']>0 for r in stable),
            'no_filter_negative_rate':base,'productionReady':False,'executionAllowed':False,'automaticPromotionAllowed':False}
