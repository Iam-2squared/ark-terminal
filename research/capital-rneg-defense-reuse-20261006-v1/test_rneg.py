"""Focused contracts, no market fits and no Control portfolio replay."""
import unittest, copy
from fractions import Fraction as F
from rneg_policy import qualify, select_policy, action
from fit_rneg import transform
from defense_engine import make_engine, native

DAY='2025-08-01'
def candidate(key='x',minute=570,rank='S'):
    return {'entry_id':key,'session':DAY,'symbol':key,'entry_minute':minute,'entry_timestamp':DAY+'T09:30:00+09:00',
        'capital_score':2.1,'capacity_band':rank,'rank':rank,'admission':True,'ML':2.1,'m2':.8,'m3':.7,'m5':.6,'block':1,'raw_reference':'100'}
def fixture(c):
    def market(t,p):return {'session':DAY,'minute':t,'O':p,'H':p,'L':p,'C':p,'Vo':'100','Va':'10000','lineage':{'fixture':True}}
    return {'session':DAY,'entry_id':c['entry_id'],'capture_complete':True,'entry_actual_source':market(c['entry_minute'],'100'),
        'market':[market(c['entry_minute'],'100'),market(600,'110')],
        'limit_up_authority':None,'frozen_exit':{'sell_status':'FILLED','sell_source_assumed_available_at':DAY+'T10:01:00+09:00',
            'sell_minute':600,'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':'109.945'}}
def table():
    return {'1':{'training_session_N':20,'B_median':1.1,'B_p75':1.2,
        'minute_counts':{str(t):[0,0,0] for t in range(540,932)},'minute_bucket':{str(t):0 for t in range(540,932)}}}
def cal():
    return [{'entry_id':str(i),'session':f'2025-06-{i%10+1:02d}','r':F(-1,10) if i<60 else F(1,10),
        'y_neg':int(i<60),'score':.9 if i<20 else .2,'can_veto':True,'block':1,
        'label_maturity':'2025-06-11','execution_eligible':True,'rank_pass':True} for i in range(100)]

class Contracts(unittest.TestCase):
    def test_qualification_whole_tie_and_no_all_reject(self):
        best,_=qualify(cal(),'D1');self.assertEqual(best['tau'],.9);self.assertEqual(best['veto_support']['N'],20)
    def test_support_insufficient_OFF(self):
        best,_=qualify(cal()[:99],'D1');self.assertIsNone(best)
    def test_current_future_not_CAL(self):
        h={'D1':cal()+[{**r,'block':3,'score':1.0} for r in cal()]}
        self.assertEqual(select_policy(h,2,['2025-07-01'])['selection']['tau'],.9)
    def test_first_block_OFF(self):
        self.assertEqual(select_policy({'D1':cal()},1,['2025-07-01'])['status'],'DEFENSE_OFF')
    def test_no_positive_denominator_OFF(self):
        z=[{**r,'r':F(-1,100),'y_neg':1} for r in cal()]
        self.assertIsNone(qualify(z,'D1')[0])
    def test_one_session_dependency_fails(self):
        z=cal()
        for r in z[:20]:r['session']='2025-06-01'
        self.assertIsNone(qualify(z,'D1')[0])
    def test_model_lexical_tie(self):
        self.assertEqual(select_policy({'D1':cal(),'D2':cal()},2,['2025-07-01'])['selection']['recipe'],'D1')
    def test_abstain_and_equal_tau(self):
        p=select_policy({'D1':cal()},2,['2025-07-01'])
        self.assertEqual(action({'score':.9,'can_veto':True},p),'VETO_THIS_ENTRY')
        self.assertEqual(action({'score':.99,'can_veto':False},p),'ABSTAIN/PASS_TO_V5')
    def test_train_only_vocabulary_and_future_numeric(self):
        r={'numeric':{'x':None},'categorical':{'c':'A'}}
        _,_,a=transform([r],[{'numeric':{'x':100},'categorical':{'c':'FUTURE'}}],['x'],['c'])
        _,_,b=transform([r],[{'numeric':{'x':-100},'categorical':{'c':'DIFFERENT'}}],['x'],['c'])
        self.assertEqual(a,b);self.assertNotIn('FUTURE',a['categorical_train_vocab']['c'])
    def test_OFF_equals_native_exact(self):
        c=candidate();args=(3,DAY,[c],{'x':fixture(c)},1000000,True,'test')
        old=native.day_replay(*args,tables=table());new=make_engine(lambda r:'PASS_TO_V5')(*args,tables=table())
        for d in new[1]:d.pop('defense_action',None)
        self.assertEqual(old,new)
    def test_veto_frees_picked_slots_and_applies_to_later(self):
        cs=[candidate(k) for k in ['a','b','c','d']]+[candidate('later',580)]
        res,ds,ts,frames,_=make_engine(lambda r:'VETO_THIS_ENTRY' if r['entry_id'] in ('a','later') else 'PASS_TO_V5')(3,DAY,cs,{c['entry_id']:fixture(c) for c in cs},1000000,True,'test',tables=table())
        self.assertEqual({t['entry_id'] for t in ts},{'b','c','d'});self.assertEqual(res['max_concurrent'],3)
        self.assertEqual(next(d for d in ds if d['entry_id']=='later')['reason'],'RNEG_DEFENSE_VETO')
    def test_sell_precedes_same_time_buy(self):
        a=candidate('a');b=candidate('b',601)
        res,ds,ts,_,_=make_engine(lambda r:'PASS_TO_V5')(3,DAY,[a,b],{'a':fixture(a),'b':{**fixture(b),'market':fixture(b)['market']+[{'session':DAY,'minute':620,'O':'110','H':'110','L':'110','C':'110','Vo':'100','Va':'11000','lineage':{'fixture':True}}],'frozen_exit':{**fixture(b)['frozen_exit'],'sell_minute':620,'sell_source_assumed_available_at':DAY+'T10:21:00+09:00'} }},1000000,True,'test',tables=table())
        self.assertEqual(res['status'],'COMPLETE');self.assertEqual(len(ts),2)
        self.assertEqual(next(d for d in ds if d['entry_id']=='b')['held_before_batch'],[])

if __name__=='__main__':unittest.main()
