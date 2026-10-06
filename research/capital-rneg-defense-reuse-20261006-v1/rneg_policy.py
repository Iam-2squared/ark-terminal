"""Exactly one past-first-OOF qualification procedure, no portfolio simulation."""
from collections import defaultdict
from fractions import Fraction

def support(rr):
    return {'N':len(rr), 'session_N':len({r['session'] for r in rr}),
            'negative_N':sum(r['y_neg']==1 for r in rr),
            'nonnegative_N':sum(r['y_neg']==0 for r in rr)}

def qualify(cal, recipe):
    s = support(cal)
    if s['N'] < 100 or s['session_N'] < 10 or min(s['negative_N'],s['nonnegative_N']) < 20:
        return None, {'recipe':recipe, 'support':s, 'status':'CAL_PAST_SUPPORT_INSUFFICIENT', 'candidate_N':0}
    pos = sum(r['r']>0 for r in cal)
    pos_profit = sum((max(r['r'],0) for r in cal), Fraction(0))
    viable=[]; reasons=defaultdict(int)
    for tau in sorted({r['score'] for r in cal}):
        rejected=[r for r in cal if r['score']>=tau and r.get('can_veto',True)]
        z=support(rejected)
        positive_N=sum(r['r']>0 for r in rejected)
        profit=sum((max(r['r'],0) for r in rejected),Fraction(0))
        net=sum((-r['r'] for r in rejected),Fraction(0))
        by_session=defaultdict(lambda:Fraction(0))
        for r in rejected: by_session[r['session']]-=r['r']
        conditions = {
            'veto_support':z['N']>=20 and z['session_N']>=5,
            'positive_count_budget':pos>0 and positive_N*10<=pos,
            'positive_profit_budget':pos_profit>0 and profit*10<=pos_profit,
            'precision_lift':z['N']>0 and z['negative_N']*s['N']>s['negative_N']*z['N'],
            'net_value':net>0,
            'leave_one_session_nonnegative':bool(by_session) and all(net-v>=0 for v in by_session.values())}
        for k,v in conditions.items():
            if not v:reasons[k]+=1
        if all(conditions.values()):
            v={'recipe':recipe,'tau':tau,'CAL_PAST':s,'veto_support':z,
               'negative_recall':z['negative_N']/s['negative_N'],
               'precision':z['negative_N']/z['N'],
               'positive_false_veto_rate':positive_N/pos,
               'positive_unit_profit_removed_rate':float(profit/pos_profit),
               'unit_net_value':float(net),'min_leave_one_session_net':float(min(net-v for v in by_session.values()))}
            viable.append(v)
    best=max(viable,key=lambda v:(v['negative_recall'],v['precision'],v['tau'])) if viable else None
    return best, {'recipe':recipe,'support':s,'status':'QUALIFIED' if best else 'NO_QUALIFIED_THRESHOLD',
                  'candidate_N':len({r['score'] for r in cal}),'qualified_N':len(viable),'failed_condition_counts':dict(reasons)}

def select_policy(histories, block, dates):
    options=[]; audits=[]
    for recipe in ('D1','D2'):
        if recipe not in histories:continue
        cal=[r for r in histories[recipe] if r['block']<block and r['label_maturity']<dates[0]
             and r['execution_eligible'] and r['rank_pass'] and r['r'] is not None and r['can_veto']]
        best,audit=qualify(cal,recipe);audits.append(audit)
        if best:options.append(best)
    best=max(options,key=lambda v:(v['negative_recall'],v['precision'],v['tau'], -(1 if v['recipe']=='D1' else 2))) if options else None
    return {'block':block,'test_dates':dates,'status':'ACTIVE' if best else 'DEFENSE_OFF',
            'selection':best,'past_qualification':audits,
            'current_or_future_teacher_payloads':0,'in_sample_CAL_rows':0,'tie_rule':'score >= tau; entire tie retained',
            'single_procedure':True}

def action(prediction, policy):
    if policy['status']!='ACTIVE':return 'PASS_TO_V5'
    if not prediction or not prediction.get('can_veto',False):return 'ABSTAIN/PASS_TO_V5'
    return 'VETO_THIS_ENTRY' if prediction['score']>=policy['selection']['tau'] else 'PASS_TO_V5'
