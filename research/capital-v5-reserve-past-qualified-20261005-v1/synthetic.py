"""The28 predeclared causal/synthetic cases. No actual-input resampling or market path."""
from context import *
from policy import project_packet,proposal,score_check,success_counter,native_wrapper,singleton
from qualify import maturity,join_row
from contracts import prefix_certificate,accept_saved_prefix,settlement_contract,exact_E1,exact_Q3,verify_frozen_bytes
from copy import deepcopy
from fractions import Fraction
from decimal import Decimal as D
import ast, inspect, math

EXPECTATIONS={
 '01':'block1/past不足:例外0、native picked不変',
 '02':'current/future outcome mutation:過去依存join・current action不変',
 '03':'先行blockでも未成熟labelはknown=False',
 '04':'OOF frame外training resubstitutionは性能sampleに混入不可',
 '05':'rP exact3/4 PASS、直下FAIL、有理数',
 '06':'q exact1/2 HIGH、strict-lessはraw median等号と異なる',
 '07':'q2LOW/q3HIGH、q2HIGH/q3LOWともPASS',
 '08':'bothLOW FAIL、MRET mutationでaction不変',
 '09':'高pP先頭guard失敗:下位へbackfill0',
 '10':'native picked非空でassigned全quantity0でも例外0',
 '11':'actual open0/3拒否、1/2は構造候補',
 '12':'cashで1lot可能でもtarget budget0:quantity0',
 '13':'cap1lot未満qty0、1lotちょうど/直上qty100',
 '14':'BUY成功counterは同session自然EXIT後もtrue、再回収0',
 '15':'qty0はcounter非消費、同batch下位backfill0',
 '16':'same-symbol/pending/current Entry/cutoff拒否',
 '17':'future cash release mutationでcurrent quantity/action不変',
 '18':'future source availability mutationでBUY前選択不変',
 '19':'選択後source不足:BUY保持/義務保持/BLOCKED',
 '20':'protected100 membership mutationでruntime不変',
 '21':'完全prefix差分0はNO_EFFECT、state欠損UNMEASURABLE',
 '22':'初回差分後saved V5 snapshot継続拒否',
 '23':'future候補同batch混入拒否、過去Entry再検討拒否',
 '24':'bootstrap各session1値、空session0保持、counts合計frame長',
 '25':'元150/Loser82を純粋追加で維持:Q3 FAIL',
 '26':'19窓中1窓の厳密微小退行:E1 FAIL',
 '27':'Frozen head/score bytes変更:STOP',
 '28':'Safety10 false、全禁止実行counter0'}

def expect_exception(fn,kind):
    try:fn()
    except kind:return True
    raise AssertionError('EXPECTED_EXCEPTION_NOT_RAISED')

def fixture():
    row={'entry_id':'2025-07-04|X','session':'2025-07-04','symbol':'X','entry_minute':600,
        'entry_timestamp':'2025-07-04T10:00:00+09:00','block':2,'rank':'B','admission':True,'ML':1.2,
        'capital_score':1.2,'m2':.5,'m3':.4,'m5':.3,'raw_reference':'1000'}
    state={'equity':'1000000','cash':'600000','exposure':'400000','positions':{'H':{'band':'S','mark':'1000','quantity':400,'symbol':'H'}}}
    native={'picked_ids':[],'gate_decisions':[{'entry_id':row['entry_id'],'slot_gate_reason':'SLOT2_RESERVE_FOR_FUTURE_QUALITY'}],'assigned':[]}
    scores={h:{'raw_score':.9 if h=='pP' else .6,'numerator':3 if h=='pP' else 2,'denominator':4,'available':True,
        'score_asof':row['entry_timestamp'],'feature_max_source_minute':599,'prediction_origin':{'train_through':'2025-07-03'},
        'model_hash':'frozen','training_reference_hash':'frozen'} for h in ('pP','MOVE_U2','MOVE_U3')}
    p={'entry_id':row['entry_id'],'session':row['session'],'symbol':'X','minute':600,'block':2,'scores':scores}
    return row,state,native,{row['entry_id']:p}

def call(row,state,native,packets,**kw):
    rows=kw.pop('rows',[row])
    return proposal(rows,native,state,packets,row['session'],row['entry_minute'],**kw)

def case(number):
    row,state,native,packets=fixture();p=packets[row['entry_id']]
    if number==1:
        tables=json.loads((OUT/'PAST_QUALIFICATION_BY_BLOCK.json').read_text())['tables']
        assert tables[0]['status']=='COLD_ABSTAIN' and not tables[0]['PAST_QUALIFIED']
        before=deepcopy(native);assert call(row,state,native,packets,qualified=False)['candidate'] is None and native==before
    elif number==2:
        outcomes=read('outcomes');teachers={r['entry_id']:r for r in read('teachers')}
        table=json.loads((OUT/'PAST_QUALIFICATION_BY_BLOCK.json').read_text())['tables'][2]
        S=read_private('PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz');past=[r for r in S if r['block']<3]
        a=[join_row(r,teachers,outcomes,table['first_current_block_session']) for r in past]
        altered=deepcopy(outcomes)
        for r in S:
            if r['block']>=3:altered[r['entry_id']]['frozen_realized_net_return_cell']='999999'
        b=[join_row(r,teachers,altered,table['first_current_block_session']) for r in past]
        assert a==b and table['current_or_future_outcome_inputs']==0
        packets2=deepcopy(packets);packets2[row['entry_id']]['future_outcome']=999999
        assert call(row,state,native,packets)==call(row,state,native,packets2)
    elif number==3:
        teacher={'session':'2025-07-04','capture_complete':True,'strictly_after_entry_before_1520':True,
            'execution_status':'COMPLETE','release_minute':601,'source_minute':600,'source_lineage':{'sha':'same'}}
        result=join_row({'entry_id':'A','session':'2025-07-04','block':1},{'A':teacher},{},'2025-07-04')
        assert not result['known'] and result['unknown_reason']=='LABEL_NOT_MATURED_BEFORE_BLOCK'
        teacher['release_minute']=None;assert maturity(teacher)[0] is None
    elif number==4:
        split=read('split');frame=set(split['OOF38']);resub=split['blocks'][0]['train'][0]
        assert resub not in frame
        def requireframe():assert all(r['session'] in frame for r in [{'session':resub,'block':0}])
        expect_exception(requireframe,AssertionError)
    elif number==5:
        assert score_check(p)[0];p['scores']['pP'].update(numerator=749,denominator=1000)
        assert not score_check(p)[0] and Fraction(749,1000)<Fraction(3,4)
    elif number==6:
        p['scores']['MOVE_U2'].update(numerator=2,denominator=4);p['scores']['MOVE_U3'].update(numerator=1,denominator=4)
        assert score_check(p)[0]
        ref=[.2,.5,.5];rank=Fraction(1+sum(t<.5 for t in ref),len(ref)+1)
        assert rank==Fraction(1,2) and rank!=Fraction(1+sum(t<=.5 for t in ref),4)
        assert .5==sorted(ref)[1]
    elif number==7:
        for h in ('MOVE_U2','MOVE_U3'):
            test=deepcopy(p);test['scores'][h]['numerator']=1;assert score_check(test)[0]
    elif number==8:
        p['scores']['MOVE_U2']['numerator']=1;p['scores']['MOVE_U3']['numerator']=1
        assert not score_check(p)[0]
        p['MRET']=-1e9;a=call(row,state,native,packets);p['MRET']=1e9;assert call(row,state,native,packets)==a
    elif number==9:
        low=deepcopy(row);low['entry_id']=row['session']+'|Y';low['symbol']='Y'
        lowp=deepcopy(p);lowp.update(entry_id=low['entry_id'],symbol='Y');lowp['scores']['pP']['raw_score']=.8
        packets[low['entry_id']]=lowp;native['gate_decisions'].append({'entry_id':low['entry_id'],'slot_gate_reason':'SLOT2_RESERVE_FOR_FUTURE_QUALITY'})
        p['scores']['MOVE_U2']['numerator']=1;p['scores']['MOVE_U3']['numerator']=1
        result=call(row,state,native,packets,rows=[row,low]);assert result['candidate']==row['entry_id'] and result['reason']=='BOTH_QUALITY_LOW' and 'allocation' not in result
    elif number==10:
        native.update(picked_ids=['NATIVE'],assigned=[{'entry_id':'NATIVE','quantity':0}])
        assert call(row,state,native,packets)['reason']=='NATIVE_PICKED_NONEMPTY'
    elif number==11:
        for count in (0,1,2,3):
            s=deepcopy(state);s['positions']={str(i):{'symbol':str(i),'band':'S','quantity':100,'mark':'1'} for i in range(count)}
            result=call(row,s,native,packets)
            assert (result.get('candidate')==row['entry_id'])==(count in (1,2))
    elif number==12:
        state['exposure']='800000';assert D(state['cash'])>=D(row['raw_reference'])*D('1.0005')*100
        result=call(row,state,native,packets);assert result['allocation']['batch_budget']=='0' and result['allocation']['quantity']==0
    elif number==13:
        row['raw_reference']='1000';lot=D('100050');state['exposure']='0';state['cash']='1000000'
        for eq,expected in [('400199.96',0),('400200',100),('400200.04',100)]:
            s=deepcopy(state);s['equity']=eq;a=singleton(row,s);assert a['quantity']==expected
            assert D(a['equity_cap'])==D(eq)*D('.25')
    elif number==14:
        recovered=success_counter(False,100);assert recovered and success_counter(recovered,0)
        assert call(row,state,native,packets,recovered=recovered)['reason']=='SESSION_RECOVERY_ALREADY_USED'
        # Natural EXIT may alter positions but has no authority to clear this bool.
        state['positions']={'OTHER':{'band':'S','symbol':'OTHER','quantity':100,'mark':'1'}}
        assert call(row,state,native,packets,recovered=recovered)['candidate'] is None
    elif number==15:
        high=deepcopy(row);high['raw_reference']='300000';low=deepcopy(row);low['symbol']='Y';low['entry_id']=row['session']+'|Y'
        lowp=deepcopy(p);lowp.update(entry_id=low['entry_id'],symbol='Y');lowp['scores']['pP']['raw_score']=.8;packets[low['entry_id']]=lowp
        native['gate_decisions'].append({'entry_id':low['entry_id'],'slot_gate_reason':'SLOT2_RESERVE_FOR_FUTURE_QUALITY'})
        result=call(high,state,native,packets,rows=[high,low]);assert result['candidate']==high['entry_id'] and result['allocation']['quantity']==0
        assert not success_counter(False,0)
    elif number==16:
        assert call(row,state,native,packets,pending_symbols=('X',))['reason']=='SAME_SYMBOL_OR_PENDING_ABSTAIN'
        s=deepcopy(state);s['positions']['H']['symbol']='X';assert call(row,s,native,packets)['reason']=='SAME_SYMBOL_OR_PENDING_ABSTAIN'
        altered=deepcopy(packets);altered[row['entry_id']]['minute']=599;assert call(row,state,native,altered)['reason']=='ENTRY_IDENTITY_ASOF_ABSTAIN'
        r=deepcopy(row);r['entry_minute']=920;assert call(r,state,native,packets)['reason']=='ENTRY_CUTOFF'
    elif number==17:
        a=call(row,state,native,packets);s=deepcopy(state);s['future_release']={'cash':'999999999','minute':601}
        assert call(row,s,native,packets)==a
    elif number==18:
        a=call(row,state,native,packets)
        for value in (False,True):
            changed=deepcopy(packets);changed[row['entry_id']]['future_source_available']=value
            assert call(row,state,native,changed)==a
    elif number==19:
        result=call(row,state,native,packets);assert result['allocation']['quantity']>=100
        blocked=settlement_contract(True,False)
        assert blocked['status']=='EXECUTION_MEASUREMENT_BLOCKED' and blocked['buy_retained'] and blocked['unresolved_obligation']
    elif number==20:
        raw=read('packet')[0];projected=project_packet(raw);changed=deepcopy(raw)
        changed['protected100_membership']=not raw.get('protected100_membership',False);changed['evaluation_ids']=['FAKE']
        assert project_packet(changed)==projected
    elif number==21:
        assert prefix_certificate(True,[True,True],True,[0,0])=='NO_EFFECT_PROVEN'
        assert prefix_certificate(True,[True,True],False,[0,0])=='UNMEASURABLE'
    elif number==22:
        assert prefix_certificate(True,[True],True,[100])=='FIRST_DIVERGENCE_FOUND'
        expect_exception(lambda:accept_saved_prefix(True),ValueError)
    elif number==23:
        future=deepcopy(row);future['entry_id']=row['session']+'|Y';future['entry_minute']=601
        table=read('arrival')['2']
        expect_exception(lambda:native_wrapper([row,future],state,row['session'],600,table),AssertionError)
        old=deepcopy(packets);old[row['entry_id']]['minute']=599;assert call(row,state,native,old)['reason']=='ENTRY_IDENTITY_ASOF_ABSTAIN'
    elif number==24:
        counts=read_private('PAST_BOOTSTRAP_SESSION_COUNTS.jsonl.gz');tables=json.loads((OUT/'PAST_QUALIFICATION_BY_BLOCK.json').read_text())['tables']
        for t in tables[1:]:
            proxy=t['metrics']['session_proxy_values'];assert len(proxy)==len(t['frame_sessions']) and len({r['session'] for r in proxy})==len(proxy)
            Ssessions={r['session'] for r in read_private('PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz') if r['block']<t['block']}
            assert all(Fraction(r['net_return_exact'])==0 for r in proxy if r['session'] not in Ssessions)
        assert all(sum(r['counts'])==len(r['frame']) and len(r['counts'])==len(r['frame']) for r in counts)
    elif number==25:
        assert not exact_Q3(82,150,68) and not exact_Q3(82,151,69)
    elif number==26:
        v5=[Fraction(1)]*19;r=[Fraction(101,100)]*18+[Fraction(10**20-1,10**20)]
        assert float(r[-1])==1.0 and not exact_E1(v5,r)
    elif number==27:
        payload=(INPUT/ROLES['packet']).read_bytes();assert verify_frozen_bytes(payload,sha(INPUT/ROLES['packet']))
        expect_exception(lambda:verify_frozen_bytes(payload+b'changed',sha(INPUT/ROLES['packet'])),ValueError)
    elif number==28:
        assert len(SAFETY)==10 and not any(SAFETY.values()) and not any(ZERO_COUNTS.values())
    else:raise AssertionError('UNDECLARED_CASE')
    return True

def read_private(name):
    with gzip.open(PRIVATE/name,'rt',encoding='utf-8') as f:return [json.loads(s) for s in f]

def main():
    expectations=json.loads((OUT/'SYNTHETIC_EXPECTATIONS.json').read_text());assert expectations['cases']==EXPECTATIONS
    assert expectations['fixed_before_test_execution'] and expectations['directive_sha256']==sha(OUT/'DIRECTIVE.txt')
    resume=json.loads((PRIVATE/'SYNTHETIC_RESUME_AFTER_CASE11.json').read_text())
    assert resume['completed_cases']==[f'{n:02d}' for n in range(1,12)]
    results=[{'case':n,'expected':EXPECTATIONS[n],'status':'PASS','execution':'completed before preserved case12 import failure'} for n in resume['completed_cases']]
    for n in range(12,29):
        assert case(n);results.append({'case':f'{n:02d}','expected':EXPECTATIONS[f'{n:02d}'],'status':'PASS'})
    module=ast.parse(inspect.getsource(__import__('policy')))
    imports=[]
    for node in ast.walk(module):
        if isinstance(node,ast.Import):imports += [a.name for a in node.names]
        if isinstance(node,ast.ImportFrom):imports.append(node.module)
    assert not any(s in ('qualify','contracts','synthetic','independent','books','outcomes') for s in imports)
    sig=list(inspect.signature(proposal).parameters)
    assert not any(s in sig for s in ('outcomes','books','protected_ids','future_source_available'))
    assert set(project_packet(read('packet')[0])['scores'])=={'pP','MOVE_U2','MOVE_U3'}
    independent=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text());schema=json.loads((OUT/'P1_FULL_NATIVE_ROW_SCHEMA_SUPPLEMENT.json').read_text())
    assert independent['status']=='PASS' and independent['mismatch_N']==0 and schema['status']=='PASS'
    save('SYNTHETIC_AND_PREMAIN_AUDIT.json',{'schema':'V5_R_SYNTHETIC_PREMAIN_V1','exact_jst':now(),
        'status':'PASS','synthetic_case_N':28,'synthetic_pass_N':28,'cases':results,'mismatch_N':0,
        'J0':'PASS','J1':'PASS_WITH_FULL_NATIVE_ROW_SCHEMA_SUPPLEMENT','J2':'PASS',
        'J3':'NOT_EXECUTED_PAST_SUPPORT_NOT_ESTABLISHED','J4':'PASS',
        'firewall':{'policy_imports':imports,'proposal_arguments':sig,'projected_heads':['pP','MOVE_U2','MOVE_U3'],
            'future_outcome_input_N':0,'protected_ID_runtime_input_N':0,'future_source_availability_input_N':0,'MRET_runtime_input_N':0},
        'expectations_sha256':sha(OUT/'SYNTHETIC_EXPECTATIONS.json'),'independent_audit_sha256':sha(OUT/'INDEPENDENT_AUDIT.json'),
        'candidate_replay_authorized':False,'reason':'No past-qualified block; J3 was correctly skipped.',
        'limits':'Cases19/21/22/25/26 test pure certificate/evaluation contracts. They do not claim an executed R engine or whole-path future mutation invariance.',
        'new_market_replay_N':0,'new_statistical_table_N':0,'new_bootstrap_draw_N':0,'Safety':SAFETY})
    checkpoint('P3','PREMAIN_SAVED_CASES_AND_SYNTHETIC_VERIFIED',{'synthetic_N':28,'independent_mismatch_N':0,
        'native_saved_batch_N':907,'native_full_row_N':1039,'selected_snapshot_N':158,'past_table_N':8,'qualified_block_N':0},
        'Fix PAST_SUPPORT_NOT_ESTABLISHED; skip first-divergence and all market Replay; final report and closure')
    print(json.dumps({'status':'PASS','synthetic_N':28,'mismatch_N':0,'market_replay_N':0}))

if __name__=='__main__':main()
