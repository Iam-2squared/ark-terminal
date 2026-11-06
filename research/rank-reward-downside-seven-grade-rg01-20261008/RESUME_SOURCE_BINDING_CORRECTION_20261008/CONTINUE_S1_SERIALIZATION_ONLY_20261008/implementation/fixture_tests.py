"""Mandatory synthetic fixtures only. Never reads actual outcome rows."""
import copy,json,math,pathlib
from fractions import Fraction as F
import assign_ranks as p
import evaluate_ranks as e
import independent_audit as a
def fixture(ml=3.,r3=1.,r5=1.):
    return {'entry_id':'FIXTURE|0000','session':'2020-01-01','symbol':'0000','entry_timestamp':'2020-01-01T09:30:00+09:00','ML':ml,'m2':.8,'m3':.6,'m5':.3,'R0_rank':'S' if ml>=2 else 'A' if ml>=1.5 else 'B' if ml>=1 else 'C','R0_candidate_order':[-ml,-.3,-.6,-.8,'2020-01-01T09:30:00+09:00','0000','FIXTURE|0000'],'risk':{m:{'q3':.25*r3,'q5':.125*r5,'B0_p5':[.125,.125,.2,.2,.35]} for m in ['D-FULL','D-PRICE']}}
def main():
    tests=[];checks=0
    for bound,at in [(.75,5),(1.,4),(1.25,3),(1.5,2),(2.,1),(2.5,0)]:
        for v,expected in [(math.nextafter(bound,-math.inf),at+1),(bound,at),(math.nextafter(bound,math.inf),at)]:assert p.grade(v)==a.seven(v)==expected;checks+=1
    tests.append('ML six thresholds: immediately below/exact/above, no epsilon')
    for r3,r5 in [(1,1),(math.nextafter(1,math.inf),1),(1,math.nextafter(1,math.inf)),(1.5,1.5),(1.5,1.25),(1.25,1.5)]:
        for ml in [3.,2.2,1.6,1.3,1.1,.8,.5]:
            row=fixture(ml,r3,r5);d=p.one(row);alt=a.calc({**row,'rank':row['R0_rank']},row['risk']);base=p.grade(ml)
            for m in p.METHODS:
                assert d[m]['grade']==alt[m]['grade'] and d[m]['order_key']==alt[m]['order_key'];checks+=1
            dg=d['G7_FULL']['grade_index'];assert dg==min(6,base+int((r3>1 or r5>1) if base==0 else r3>=1.5 and r5>=1.5));checks+=1
    tests.append('G strict S OR>1 / non-S AND>=1.5 and all combinations; independent formula')
    for ml in [100.,3.,2.5,2.2,2.,1.6,1.1,.8,.5]:
        d=p.one(fixture(ml,3.6,3.2));b=d['B7_FULL'];assert b['penalty']==.30;assert b['downshift']<=(1 if ml>=2 else 2)
        if p.grade(ml)==0:assert b['grade']=='A'
        assert b['grade_index']>=p.grade(ml);checks+=4
    for ml in [.5,.8,1.1,1.6,2.2,3.]:
        d=p.one(fixture(ml));assert d['B7_FULL']['penalty']==0
        for m in p.METHODS[2:]:assert d[m]['grade']==d['U7']['grade'];checks+=1
        assert d['B7_FULL']['order_key'][2:]==d['U7']['order_key'][1:];checks+=1
    tests.append('Risk excess cap>3, penalty0/.30, high-ML max one grade, no upgrades, risk prior identity')
    invalid=[{'B0_p5':[0,0,.2,.3,.5]},{'B0_p5':[]},{'B0_p5':None},{'q3':float('nan')},{'q3':-.1},{'q5':.4,'q3':.2},{}]
    for patch in invalid:
        r=fixture();r['risk']['D-FULL'].update(patch)
        if not patch:r['risk']['D-FULL'].pop('B0_p5')
        d=p.one(r)
        for m in ['G7_FULL','B7_FULL']:assert d[m]['grade']=='RANK_UNAVAILABLE' and not d[m]['available'];checks+=1
    tests.append('Invalid/absent/zero prior and NaN/negative/inverted q fail closed, never F')
    eps=F(1,2**60)
    for n in range(-5,6):
        for v in [F(n)-eps,F(n),F(n)+eps]:assert e.band(v)==a.rband(v);checks+=1
    assert e.band(None)==a.rband(None)=='R_UNKNOWN';assert e.band(F(0))=='ZERO';checks+=2
    tests.append('Exact Fraction R boundaries -5 through +5, ZERO and unknown separate')
    rows=[]
    for time,symbol,i in [('09:31','0000','B'),('09:30','0001','C'),('09:30','0000','B'),('09:30','0000','A')]:
        r=fixture(3.);r['entry_timestamp']='2020-01-01T'+time+':00+09:00';r['symbol']=symbol;r['entry_id']=i;r['R0_candidate_order']=[-3.,-.3,-.6,-.8,r['entry_timestamp'],symbol,i];rows.append(r)
    assert [r['entry_id'] for r in sorted(rows,key=lambda x:p.one(x)['U7']['order_key'])]==['A','B','C','B'];checks+=1
    tests.append('Complete stable ML/m5/m3/m2/timestamp/symbol/ID tie order')
    r=fixture();before=p.bytes_for([{'entry_id':r['entry_id'],'methods':p.one(r)}]);r_with_future={**r,'R_NEW':999,'U10':True,'EXIT':'FAKE','future_bar':{'close':0},'future_State':{'state':9}};after=p.bytes_for([{'entry_id':r['entry_id'],'methods':p.one(r_with_future)}]);assert before==after;checks+=1
    tiny={r['entry_id']:{'R':F(1),'U':F(5),'U_flags':{2:True,3:True,5:True,10:False},'session':'X','symbol':'0','block':1}}
    m1=e.metrics(set(tiny),tiny);tiny2=copy.deepcopy(tiny);tiny2[r['entry_id']]['R']=F(-5);m2=e.metrics(set(tiny2),tiny2);assert m1!=m2 and m1['R_GE_P5_band_n']==0 and m2['R_LE_M5_band_n']==1;checks+=1
    tiny3=copy.deepcopy(tiny);tiny3[r['entry_id']]['R']=None;v=e.metrics(set(tiny3),tiny3);assert v['R_UNKNOWN_band_N']==1 and v['ZERO_band_N']==0 and v['U5_N']==1 and v['R_GE_P5_band_nN_pct']=='0/0 (N/A)';checks+=1
    tests.append('R-only and future bar/State replacements cannot affect assignment bytes; evaluator changes; independent U mask')
    result={'status':'PASS','synthetic_assertion_N':checks,'tests':tests,'actual_Entry_assignment_campaign_used':0,'actual_outcome_file_opens':0,'source_pin_and_all_block_K_tests':'Completed by source preparation and dataset audit, separately from synthetic fixtures','classification_epsilon':0,'float_testing':'math.nextafter for ML, Fraction(1,2**60) for R','not_a_threshold_search':True}
    root=pathlib.Path(__file__).resolve().parents[1];(root/'public/BOUNDARY_AND_SEPARATION_TEST_RECEIPT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
