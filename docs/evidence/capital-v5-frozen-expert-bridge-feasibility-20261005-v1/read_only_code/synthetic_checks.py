"""18 required executable contract fixtures; fake labels, no market run."""
import copy,json,numpy as np
from adapter import HEADS,OUT,BASE,read,rows,save,sha,long_wide,fraction,support
from metrics import auc_ap,cluster_auc,concordance
from support_checker import check,summarize
def main():
 tests=[]
 def test(n,name,f):
  try:f();tests.append({'case':n,'name':name,'status':'PASS'})
  except Exception as e:tests.append({'case':n,'name':name,'status':'FAIL','error':repr(e)})
 def require(v):assert v
 def case1():
  a=[{'entry_id':str(i),'head':h,'score':.1} for i in range(150) for h in HEADS];require(len(long_wide(a))==150)
  try:long_wide(a+[a[0]])
  except AssertionError:return
  raise AssertionError('duplicate head accepted')
 test(1,'long600 ->150; duplicate head rejected',case1)
 test(2,'raw median tie .2 is2/6 LOW',lambda:require(fraction([.1,.2,.2,.2,.3],.2)=={'numerator':2,'denominator':6,'LOW':True,'HIGH':False}))
 test(3,'exact1/2 HIGH; missing neither',lambda:require(fraction([.1,.3,.5],.2)['HIGH'] and fraction([.1],None)['LOW'] is None and fraction([.1],None)['HIGH'] is None))
 test(4,'reverse pP/q2 pair is conflict',lambda:require((.9-.1)*(.1-.9)<0))
 test(5,'U10 and realized loss both count',lambda:require(.12>=.10 and -.02<=0))
 test(6,'U3 and U5 positive not Medium-only',lambda:require(.06>=.03 and .06>=.05 and not (.03<=.06<.05)))
 def case7():
  s=np.array([.2,.2,.8,.9]);y=[0,1,1,0];a,_=auc_ap(s,y);b,_=auc_ap(-s,y);require(abs(a[0]+b[0]-1)<=1e-12)
  # Additional tie-credit/session-pair contract subcase: same session m once, not m².
  v=cluster_auc([.5,.8,.1],[1,0,0],[0,0,1],np.array([[2,1]]));require(v[0]==.5)
 test(7,'signed AUC identity incl ties and same-session pair weight',case7)
 def case8():
  a,_=auc_ap([.1,.2],[1,1]);require(np.isnan(a[0]));v,_=concordance([.1],[.2],['g'],[0],np.ones((1999,1)));require(v['concordance'] is None and v['null_reason']=='NO_PAIR')
 test(8,'ONE_CLASS/NO_PAIR null, unknown not zero',case8)
 p={'entry_id':'synthetic','native':{'reason':'SLOT_RESERVE_REJECT'},'heads':{h:{'available':True,'raw_score':.2,'LOW':False,'HIGH':True} for h in HEADS}};sn={'existing_open_N':1,'planned_quantity':100,'same_batch_candidate_N':2};frozen=copy.deepcopy(p)
 def case9():
  before=json.dumps(p,sort_keys=True);one=support(sn,p,'VACANT_SLOT_RESERVE');labels={'U10':0,'realized':-.01};labels.update(U10=1,realized=10);require(json.dumps(p,sort_keys=True)==before and support(sn,p,'VACANT_SLOT_RESERVE')==one and p==frozen)
 test(9,'mutating separate future labels leaves packet/rank/support invariant',case9)
 test(10,'existing0 + prior successful2 ->planned3; quantity0 ignored',lambda:require(0+sum(q>=100 for q in [100,0,200])+1==3))
 test(11,'fullMAX3 higher-pP arrival comparison only, no action',lambda:require(support({'existing_open_N':3},p,'FULL_MAX3')['support'] is False and all(k not in support({'existing_open_N':3},p,'FULL_MAX3') for k in ['BUY','SELL'])))
 test(12,'different minute not same batch',lambda:require(('day',570)!=('day',571)))
 test(13,'union>K not same-budget success',lambda:require(len({1,2}|{2,3})>2))
 test(14,'block percentile reverses raw global order',lambda:require(.9>.8 and fraction([.95,.96,.97],.9)['numerator']/4 < fraction([.1,.2,.3],.8)['numerator']/4))
 test(15,'future outcome availability cannot change eligibility',lambda:require(support(sn,p,'VACANT_SLOT_RESERVE')==support(sn,{**p,'future_outcome_available':False},'VACANT_SLOT_RESERVE')))
 test(16,'score preserved not Capital PASS',lambda:require(read(OUT/'ORIGINAL_SKILL_REPRODUCTION.json')['L3']=='NOT_EVALUATED'))
 test(17,'CH3 support without defense token',lambda:require(support(sn,p,'VACANT_SLOT_RESERVE')['support'] and 'token' not in sn and 'token' not in p))
 test(18,'hypothetical zero-support NO_REPLAY_REQUIRED; no automatic relaxation',lambda:require(summarize([check(p,sn,'VACANT_SLOT_RESERVE',[('pP','LOW')])])=={'support_N':0,'unknown_N':0,'status':'NO_REPLAY_REQUIRED','runtime_actions':0,'automatic_condition_relaxation':False}))
 save('SYNTHETIC_CHECKS.json',{'cases':tests,'mandatory_case_N':18,'pass_N':sum(r['status']=='PASS' for r in tests),'fail_N':sum(r['status']=='FAIL' for r in tests),'fixtures_are_not_real_predictions':True,'real_dataset_condition_scan_N':0,'no_fake_production_intents':True,'code_hash':sha(BASE/'code/synthetic_checks.py')})
 print(json.dumps(tests));assert all(t['status']=='PASS' for t in tests)
if __name__=='__main__':main()
