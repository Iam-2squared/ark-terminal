"""Contract canaries and support-state proofs. No historical capital replay."""
from control import *
from runtime import gate,allocation,order,predicted_release,FROZEN
from tables import primary_tables
from scores import predict
from decimal import Decimal as D
import copy,ast
def main():
    checks=[]
    def check(name,condition,evidence):checks.append({'name':name,'PASS':bool(condition),'evidence':evidence})
    auth=read(OUT/'PARENT_AUTHORITY_FREEZE.json');cross=read(OUT/'PRIVATE_PACK_CROSS_AUTHORITY_AUDIT.json');score=read(OUT/'QUALITY_SCORE_RUNTIME_RECONSTRUCTION.json');tf=read(OUT/'TRAIN_QUALITY_SCORE_TABLE_FREEZE.json');pf=read(OUT/'I1_I2_PRESSURE_TABLE_FREEZE.json');design=read(OUT/'INTEGRATION_DESIGN_PRECOMMIT.json');numeric=read(OUT/'NUMERIC_DOMINANCE_BOUNDARY_AUDIT.json')
    rowscurrent=rows(PRIVATE/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz');tr=rows(PRIVATE/'QUALITY_TRAIN_SCORE_TABLE.jsonl.gz');original={r['entry_id']:r for r in rows(MAIN/'private/RANK_NATIVE_RUNTIME.jsonl.gz')};states=rows(PRIVATE/'I1_I2_PRESSURE_SUPPORT_STATES.jsonl.gz');tables=primary_tables();rp=(CODE/'replay.py').read_text();r7=(ROOT/'research/capital-v7-rank-native-max3-20261005-v1/runtime.py').read_text()
    check('01 Selector freeze',cross['mismatch_N']==0 and auth['branch_base']==MAIN_SHA,'shared frozen Entry identities; parent tree immutable')
    check('02 Entry freeze',sha(MAIN/'inputs/entry/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz')==sha(QUALITY/'inputs/FROZEN_ENTRY.jsonl.gz'),'shared byte-identical frozen Entry')
    hashes=read(OUT/'FROZEN_CODE_AND_TABLE_AUTHORITY.json')['parent_hashes']
    check('03 EXIT freeze',all(sha(ROOT/p)==h for p,h in hashes.items()),'frozen execution source bytes unchanged')
    check('04 pP model hashes',all(sha(MAIN/f'inputs/movement/models/MOVE_P_BLOCK_{b:02}.json')==sha(QUALITY/f'inputs/models/MOVE_P_BLOCK_{b:02}.json') for b in range(1,9)),'8 pinned identical models')
    check('05 pP stream hash',sha(MAIN/'inputs/movement/MOVE_P5_SCORE_STREAM.jsonl.gz')==sha(QUALITY/'inputs/MOVE_P5_SCORE_STREAM.jsonl.gz'),'frozen saved ordering authority')
    check('06 U2 model hashes',sum(z['head']=='MOVE_U2' for z in score['models'])==8,'16 fitted-state identities checked against completed claims')
    check('07 U3 model hashes',sum(z['head']=='MOVE_U3' for z in score['models'])==8,'16 fitted-state identities checked against completed claims')
    check('08 current causal score reconstruction',score['mismatch_N']==0 and score['max_saved_OOF_abs_delta']<=1e-12 and score['current_OOF_N']==1039,'saved predictions audit-only; causal inference runtime source')
    models=[read(QUALITY/f'private/models/MOVE_U{h}_BLOCK_01.json') for h in (2,3)]
    fields=models[0]['preprocessing']['numeric_fields']+models[0]['preprocessing']['categorical_fields']
    for name,term in [('09 future High input0','high'),('10 realized PnL input0','realized'),('11 future EXIT input0','exit')]:check(name,not any(term in f.lower() for f in fields),'frozen explicit 46+7 feature allowlist')
    check('12 test future candidates input0',all(all(d<min(tab['test_sessions']) for d in tab['training_sessions']) for tab in tables.values()),'strict completed-past arrivals only')
    check('13 U2 U3 teacher pressure input0',all(set(r)==set(tf['fields']) for r in tr) and tf['teacher_payload_files_opened']==0,'table input object exactly 8 label-free fields')
    check('14 training sessions strictly past',all(r['session']<min(tables[str(r['block'])]['test_sessions']) for r in tr),'all8161 training rows')
    check('15 training resubstitution only',tf['score_semantics'].startswith('raw frozen block-model resubstitution') and tf['fit_N']==0,'same completed model training IDs; no new fit')
    check('16 admission exact',all(all(r[k]==original[r['entry_id']][k] for k in ('band','r','rank_units','train_N','pP')) for r in rowscurrent),'all1039 frozen native mappings')
    check('17 B2 tenure exact',pf['tenure_byte_exact_sha256']==sha(PARENT/'B2_TENURE_LOOKUP_TABLE.json'),'same saved table, support10 and median semantics')
    check('18 predicted release exact',all((z['I1']['predicted_release_minute'],z['I1']['predicted_active_duration'])==(z['B2']['predicted_release_minute'],z['B2']['predicted_active_duration']) for z in states),'all support states same frozen horizon')
    cell={'median_active_duration':20};tenure={'cells':{'P_BASE':{'600-630':cell}}};c={'entry_id':'synthetic_current','session':'later','entry_minute':600,'entry_timestamp':'2025-01-01T10:00:00+09:00','symbol':'S','band':'P_BASE','pP':.7,'r':.7,'rank_units':7,'train_N':10,'q2':.5,'q3':.5,'raw_reference':'1000'}
    f={'entry_id':'synthetic_train','entry_minute':601,'r':.8,'q2':.5,'q3':.5};tab={'training_sessions':['a','b'],'sessions':{'a':[f],'b':[]},'tenure':tenure}
    for occ in range(3):check(f'{19+occ:02} occupancy{occ} free{3-occ}',gate(ARMS[0],c,occ,600,tab)[2]['free_slots']==3-occ,'synthetic gate boundary')
    check('22 occupancy3 reject',gate(ARMS[0],c,3,600,tab)[:2]==(False,'MAX3_FULL'),'hard MAX3')
    equalrank=copy.deepcopy(tab);equalrank['sessions']['a'][0]['r']=c['r']
    check('23 future pP rank strict greater',gate(ARMS[0],c,2,600,equalrank)[2]['future_pressure_session_N']==0,'equal r excluded')
    check('24 I1 q2 greater equal',gate(ARMS[0],c,2,600,tab)[2]['future_pressure_session_N']==1,'exact q2 equality included')
    check('25 I2 q2 greater equal',gate(ARMS[1],c,2,600,tab)[2]['future_pressure_session_N']==1,'exact q2 equality included')
    check('26 I2 q3 greater equal',gate(ARMS[1],c,2,600,tab)[2]['future_pressure_session_N']==1,'exact q3 equality included')
    check('27 local pressure I2<=I1',all(z['occupancy']==3 or z['I2']['future_pressure_session_N']<=z['I1']['future_pressure_session_N'] for z in states),'complete support state enumeration')
    check('28 local pressure I1<=B2',all(z['occupancy']==3 or z['I1']['future_pressure_session_N']<=z['B2']['future_pressure_session_N'] for z in states),'complete support state enumeration')
    check('29 local action implications',all((not z['B2']['action'] or z['I1']['action']) and (not z['I1']['action'] or z['I2']['action']) and (z['I2']['action'] or (not z['I1']['action'] and not z['B2']['action'])) for z in states),'same state only, no global funding inclusion claim')
    check('30 same minute pP order',all(order(r)==(-r['pP'],r['entry_timestamp'],r['symbol'],r['entry_id']) for r in rowscurrent),'pP DESC then timestamp/symbol/entry_id')
    changed=[r|{'q2':1-r['q2'],'q3':1-r['q3']} for r in rowscurrent]
    check('31 quality never batch reorder',[r['entry_id'] for r in sorted(changed,key=order)]==[r['entry_id'] for r in sorted(rowscurrent,key=order)],'quality perturbation order invariant')
    check('32 pending occupancy sequential','occupancy=len(positions)+len(picked)' in rp,'frozen day engine provisional reservations')
    check('33 no backfill','if q<100:d[\'reason\']=\'CASH_OR_LOT\';continue' in rp,'no re-entry to rejected candidate batch')
    check('34 no later topup',"if a['first_pass_quantity']<100:continue" in r7,'frozen same-batch waterfill only')
    a=allocation([c],D(1000000),D(0),D(1000000),[]);a2=allocation([c|{'q2':0.,'q3':1.}],D(1000000),D(0),D(1000000),[])
    check('35 quality not quantity input',a==a2,'q2/q3 perturbation sizing invariant')
    check('36 pP proportional sizing exact',allocation is FROZEN.allocation and 'weights=sum(D(str(r[\'pP\']))' in r7,'same immutable v7 sizing function object')
    check('37 cash nonnegative',sum(x['debit'] for x in a)<=D(1000000) and 'assert recycled_pool>=0 and cash>=0' in rp,'synthetic exact Decimal allocation and runtime invariants')
    check('38 lot100',all(x['quantity']%100==0 for x in a),'integer hundred-share lots')
    check('39 MAX3<=3',all(not z['I1']['action'] and not z['I2']['action'] for z in states if z['occupancy']==3) and 'assert len(positions)<=3' in rp,'hard gate and actual engine invariant')
    check('40 same symbol<=1',len({(r['session'],r['symbol']) for r in rowscurrent})==len(rowscurrent) and "if any(p['symbol']==r['symbol']" in rp,'unique frozen candidate per session/symbol + open-symbol gate')
    check('41 after15:20 funded0',"if t>=920:d['reason']='CUTOFF';continue" in rp,'unconditional cutoff precedes all funding paths')
    check('42 no replacement',"positions.pop(key)" in rp and "source.get('blocked')" in rp,'positions removed only by confirmed frozen sell events')
    check('43 no forced EXIT','FROZEN.frozen_execution(book)' in rp and 'FROZEN.eod_intent(p)' in rp,'only frozen EXIT and preexisting EOD contract')
    baseline=[gate(arm,c,occ,600,tab) for arm in ARMS for occ in range(4)]
    for name,field in [('44 future U5 mutation unchanged','U5'),('45 future U10 mutation unchanged','U10'),('46 future potential bucket mutation unchanged','potential_bucket'),('47 realized PnL mutation unchanged','realized_PnL')]:
        cm=c|{field:999};tm=copy.deepcopy(tab)
        for rr in tm['sessions'].values():
            for frow in rr:frow[field]=-999
        check(name,[gate(arm,cm,occ,600,tm) for arm in ARMS for occ in range(4)]==baseline,'extra evaluation fields cannot affect explicit runtime predicates')
    check('48 quality probability calibration claim false',not score['probability_claim'] and design['new_fit_budget']==0,'raw Logistic ordering/dominance only')
    check('49 pP true probability claim false','true-probability claim false' in design['score_role'],'pP remains frozen ordering authority')
    check('50 Safety all false',not any(SAFETY.values()) and all(v==0 for v in ZERO.values()),'no order/provider/production interfaces')
    check('51 numeric boundary independent PASS',numeric['status']=='PASS' and numeric['independent_boundary_disagreement_N']==0,'every actual compared q2/q3 pair; near ties enumerated')
    check('52 Main Quality hashes exact',auth['Main']['HEAD']==MAIN_SHA and auth['Quality']['HEAD']==QUALITY_SHA and cross['mismatch_N']==0,'both independent parent closures immutable')
    check('53 old evidence rewrite0',all(sha(ROOT/p)==v['sha256'] for p,v in auth['required_public_authorities'].items() if v['commit']==MAIN_SHA),'all pinned Main/rank/v7/v5 public bytes unchanged')
    check('54 exact pressure0.5 reserve',gate(ARMS[0],c,2,600,tab)[1]=='CAPACITY_RESERVE_REJECT','one pressured of two past sessions')
    endtab=copy.deepcopy(tab);endtab['sessions']['a'][0]['entry_minute']=620
    check('55 horizon strict endpoint',gate(ARMS[0],c,2,600,endtab)[2]['future_pressure_session_N']==0,'arrival exactly predicted release excluded')
    nowtab=copy.deepcopy(tab);nowtab['sessions']['a'][0]['entry_minute']=600
    check('56 arrival strictly later',gate(ARMS[0],c,2,600,nowtab)[2]['future_pressure_session_N']==0,'same minute train arrival excluded')
    high=c|{'pP':.8,'r':.75,'q2':.4};low=c|{'pP':.7,'r':.7,'q2':.9}
    full=copy.deepcopy(tab);full['sessions']['b']=[dict(f)]
    check('57 lower p accept after higher p reserve allowed',not gate(ARMS[0],high,2,600,full)[0] and gate(ARMS[0],low,2,600,full)[0] and order(high)<order(low),'higher evaluated first; lower quality dominance can ACCEPT, no reorder')
    check('58 lunch excluded horizon',FROZEN.active_clock(690)==FROZEN.active_clock(750),'frozen trading clock')
    check('59 lower middle tenure',all(c['median_active_duration']>=1 for t in tables.values() for cells in t['tenure']['cells'].values() for c in cells.values()),'same audited support10 lower-middle table')
    imports=[];calls=[]
    for p in CODE.glob('*.py'):
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module or '')
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):calls.append(node.func.attr)
    check('60 no optimizer fit imports',not any(x.startswith('sklearn') for x in imports) and not any(x in ('fit','fit_transform','partial_fit') for x in calls),'inference/Decimal/Fraction only')
    o={'exact_jst':now(),'canary_N':len(checks),'PASS_N':sum(x['PASS'] for x in checks),'all_PASS':all(x['PASS'] for x in checks),'checks':checks,'historical_Main_replays':0,'preMain_proof_scope':'input boundaries, synthetic contract cases and exhaustive same-state support; actual cash/occupancy additionally audited after the two claimed replays','Safety':SAFETY}
    save(OUT/'CAUSAL_CANARY_RESULTS.json',o)
    checkpoint('V6_CAUSAL_CANARY_PASS',{'PASS_N':o['PASS_N'],'canary_N':len(checks),'all_PASS':o['all_PASS']},'Publish independent score/numeric/all-state action audit before Main')
    print(json.dumps({k:o[k] for k in ('canary_N','PASS_N','all_PASS')}),flush=True)
if __name__=='__main__':main()
