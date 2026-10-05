"""Training-only tables and every same-state support case; no Main replay."""
from control import *
from runtime import gate,counts_by_session,FROZEN,predicted_release
def primary_tables():
    split=read(SPLIT);train=rows(PRIVATE/'QUALITY_TRAIN_SCORE_TABLE.jsonl.gz');tenure=read(PARENT/'B2_TENURE_LOOKUP_TABLE.json');out={}
    for block in split['blocks']:
        b=block['block'];rr=[r for r in train if r['block']==b]
        out[str(b)]={'training_sessions':block['train'],'test_sessions':block['test'],'sessions':{d:[r for r in rr if r['session']==d and r['band']!='P_BELOW'] for d in block['train']},'tenure':tenure[str(b)]}
    return out
def build():
    tables=primary_tables();b2=read(PARENT/'B2_CAPACITY_PRESSURE_TABLE.json')['sessions'];tenure=read(PARENT/'B2_TENURE_LOOKUP_TABLE.json')
    for b in b2:b2[b]['tenure']=tenure[b]
    current=rows(PRIVATE/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz');states=[];near=[];pairs=0;actions=0;session_checks=0
    for c in current:
        if c['band']=='P_BELOW' or c['entry_minute']>=920:continue
        b=str(c['block']);h,d=predicted_release(c,tables[b]);assert (h,d)==FROZEN.predicted_release(c,b2[b])
        n1,_,_=counts_by_session(c,tables[b],ARMS[0]);n2,_,_=counts_by_session(c,tables[b],ARMS[1])
        # Enumerate exactly the numeric pairs reached by the policy predicates.
        for day in tables[b]['training_sessions']:
            for f in tables[b]['sessions'][day]:
                if not c['entry_minute']<f['entry_minute']<h or not f['r']>c['r']:continue
                for field in ['q2']+(['q3'] if f['q2']>=c['q2'] else []):
                    pairs+=1;delta=abs(f[field]-c[field])
                    if delta<=1e-12:near.append({'block':c['block'],'current_entry_id':c['entry_id'],'future_train_entry_id':f['entry_id'],'field':field,'current_score':c[field],'future_score':f[field],'abs_delta':delta,'primary_ge':f[field]>=c[field]})
        raw_counts=[sum(c['entry_minute']<m<h and units>c['rank_units'] for m,units in b2[b]['sessions'][day]) for day in b2[b]['training_sessions']]
        assert all(z2<=z1<=zb for z2,z1,zb in zip(n2,n1,raw_counts));session_checks+=len(n1)
        for occ in range(4):
            x1=gate(ARMS[0],c,occ,c['entry_minute'],tables[b]);x2=gate(ARMS[1],c,occ,c['entry_minute'],tables[b]);xb=FROZEN.gate(FROZEN.ARMS[1],c,occ,c['entry_minute'],b2[b])
            if occ<3:assert x2[2]['future_pressure_session_N']<=x1[2]['future_pressure_session_N']<=xb[2]['future_pressure_session_N']
            assert not xb[0] or x1[0];assert not x1[0] or x2[0]
            assert x1[0] or not xb[0];assert x2[0] or (not x1[0] and not xb[0])
            states.append({'entry_id':c['entry_id'],'block':c['block'],'occupancy':occ,'B2':{'action':xb[0],'reason':xb[1],**xb[2]},'I1':{'action':x1[0],'reason':x1[1],**x1[2]},'I2':{'action':x2[0],'reason':x2[1],**x2[2]}});actions+=3
    gzsave(PRIVATE/'I1_I2_PRESSURE_SUPPORT_STATES.jsonl.gz',states);gzsave(PRIVATE/'NUMERIC_NEAR_TIE_PAIRS.jsonl.gz',near)
    save(OUT/'I1_I2_PRESSURE_TABLE_FREEZE.json',{'exact_jst':now(),'status':'PASS','table_sha256':sha(PRIVATE/'I1_I2_PRESSURE_SUPPORT_STATES.jsonl.gz'),'state_N':len(states),'candidate_N':len(states)//4,'action_N':actions,'training_session_count_inclusion_checks':session_checks,'local_pressure_violations':0,'local_action_violations':0,'actual_numeric_pair_N':pairs,'near_tie_N':len(near),'near_ties_sha256':sha(PRIVATE/'NUMERIC_NEAR_TIE_PAIRS.jsonl.gz'),'tenure_byte_exact_sha256':sha(PARENT/'B2_TENURE_LOOKUP_TABLE.json'),'future_test_candidate_payload_reads':0,'teacher_payload_reads':0,'independent_numeric_status':'PENDING','global_funded_superset_claim':False,'Safety':SAFETY})
    checkpoint('V5_I1_I2_PRESSURE_TABLE_FREEZE',{'candidate_N':len(states)//4,'state_N':len(states),'local_monotonicity':'PASS','near_tie_N':len(near)},'At least 50 causal canaries and independent raw-input pre-main audit')
if __name__=='__main__':build()
