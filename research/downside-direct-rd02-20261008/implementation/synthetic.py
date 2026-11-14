"""Original required artificial fixtures; never fit a model or tune thresholds."""
from common import *
from features import compute
import copy,math

def run():
    day='2000-01-04';key='SYNTHETIC';boundary=[]
    for threshold in range(-5,6):
        for offset in [-1,0,1]:
            r=Fraction(threshold)+Fraction(offset,10**9);boundary.append({'r':str(r),'band':bucket(r),'class':target(r)})
    def raw(m,**kw):return {'minute':m,'session':day,'O':'100','H':'100','L':'100','C':'100','Vo':'0','Va':'0','lineage':{'synthetic':True},**kw}
    def trace(t,state='RANGE',valid=True,segment=1,**kw):
        return {'bar_end_minute':t,'watch_key':key,'assumed_available_at':stamp(day,t),'source_status':'RAW_CLOSED_AT_ASSUMED_BAR_END','input':None,'state':{'case_id':key,'current_semantics_observed':valid,'observed_at':t-540,'as_of':t-540,'activity':'OBSERVED' if valid else 'INITIALIZING','basis':'OBSERVED'},'path':{'case_id':key,'current_semantics_observed':valid,'scheduled_t':t-540,'bar_end':stamp(day,t),'Primary_or_null':state if valid else None,'causal_segment_id':segment,'quality':{'numeric_status':'ACCEPTED' if valid else 'REJECTED','reset_reasons':[]}},'path_events':[],**kw}
    cases=[]
    def add(name,tx,market,states,evidence=True):
        x=compute(key,day,tx,market,states,evidence);cases.append({'name':name,'key':key,'day':day,'tx':tx,'market':market,'trace':states,'evidence':evidence,'output':{k:x[k] for k in ['numeric','categorical','price_available','state_evidence_ok']}})
    add('FLAT_ZERO_VOLUME_VALUE',542,[raw(540),raw(541)],[trace(541),trace(542)])
    x=cases[-1]['output'];assert x['numeric']['PRICE/flat']==1 and x['numeric']['PRICE/body']==0 and x['numeric']['PRICE/w5/signed_efficiency']==0 and x['numeric']['PRICE/w5/down_volume_share'] is None and x['numeric']['PRICE/volume5_20_log'] is None
    add('EMPTY_PREFIX',540,[],[])
    add('RAW_EVIDENCE_MISSING',542,[],[trace(541),trace(542)])
    add('NAN_SOURCE',542,[raw(540,O='NaN'),raw(541)],[trace(541),trace(542)])
    add('INVALID_OHLC_INTERVAL',542,[raw(540,L='110'),raw(541)],[trace(541),trace(542)])
    add('INITIALIZING_OPENING',541,[raw(540)],[trace(541,valid=False)])
    add('LEGITIMATE_GAP_SEGMENT',544,[raw(540),raw(543)],[trace(541),trace(542,valid=False),trace(543,valid=False),trace(544,segment=2)])
    add('LUNCH_INVALID_CURRENT',691,[raw(689)],[trace(690),trace(691,valid=False)])
    add('STATE_EVIDENCE_GAP',542,[raw(540),raw(541)],[trace(541)],False)
    add('SIMULTANEOUS_CLOSED_BEFORE_INTENT',542,[raw(540),raw(541),raw(542,C='999')],[trace(541),trace(542),{'bar_end_minute':543,'future_R':999}])
    add('TRUE_MISSING_NUMERICS',542,[raw(541,Va=None)],[trace(541),trace(542)])
    # Predetermined zero-count and tie fixtures, not a new policy.
    ids=['C','A','B'];scores={i:.1 for i in ids};seq=sorted(ids,key=lambda i:(-scores[i],i));assert seq[:math.ceil(.2*len(seq))]==['A'] and seq[:0]==[]
    assert [1+5*i//3 for i in range(3)]==[1,2,4]
    assert bucket(None)=='R_UNKNOWN' and target(None) is None
    p=[.01,.02,.03,.40,.54];q=[p[0],p[0]+p[1],p[0]+p[1]+p[2],sum(p[:4])];assert abs(sum(p)-1)<1e-15 and q==sorted(q)
    from worker import preprocess
    missing=[{'entry_id':i,'numeric':{k:None for k in PRICE+STATE},'categorical':{k:'UNKNOWN' for k in CAT}} for i in ['SYNTHETIC_A','SYNTHETIC_B']]
    X,pre=preprocess(missing,PRICE+STATE,True);assert all(pre['all_missing_train']) and all(v==0 for v in pre['median']) and all(v==1 for v in pre['scale'])
    payload={'boundaries':boundary,'feature_cases':cases,'tie_fixture':{'canonical_high_order':seq,'top20_K':1,'K0':0,'empty_quintiles':[3,5]},'empty_class_rank':'count0, denominator0, N/A; no fitted model','all_missing_train_numeric_N':70,'zero_std_scale':1,'calibration_boundary_fixture':[0,.01,.02,.05,.1,.2,.4,.6,1]}
    save(PRIVATE/'SYNTHETIC_PRIMARY_OUTPUTS.json',payload,once=True);save(PUB/'SYNTHETIC_TEST_RECEIPT.json',{'status':'PASS_PRIMARY_PENDING_SEPARATE_CHECK','boundary_values_N':33,'feature_cases_N':len(cases),'fit_N':0,'tests':['flat','zero Volume/Value','NaN','missing','invalid interval','empty class/rank','complete q tie','K0','initialization/opening','lunch','gap','same-timestamp frozen event order','train-all-missing','std0 scale1','5class sum/cumulative order'],'formal_R_epsilon':False})
    print('ARTIFICIAL_FIXTURES_PRIMARY_PASS',len(cases),33)
if __name__=='__main__':run()
