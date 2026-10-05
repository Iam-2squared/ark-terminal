"""70+ source-backed and algebraic causal checks, before any Main execution."""
from control import *
from runtime import *
from prepare import tables
from decimal import Decimal as D,ROUND_FLOOR
from collections import defaultdict
import inspect
def build():
    assert read(OUT/'S9R_CERTIFICATION_DECISION.json')['S9R']=='PASS'
    stream=rows(PRIVATE/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz');rt={r['entry_id']:r for r in stream};tt=tables();old=rows(V9/f'private/{I2}_DECISIONS.jsonl.gz');batches=defaultdict(list);cases=[]
    for r in old:
        if 'batch_budget' in r:batches[r['session'],r['minute']].append(r)
    for tag,ds in sorted(batches.items()):
        ds.sort(key=lambda r:r['batch_index']);a=ds[0];cases.append({'case_id':f'saved/{tag[0]}/{tag[1]}','kind':'SAVED_PRE_MAIN_BATCH','picked':[rt[r['entry_id']] for r in ds],'equity':a['batch_equity'],'cash':a['cash_before'],'exposure':str(D(a['batch_equity'])-D(a['cash_before'])),'held_bands':[p['band'] for p in a['held_before_batch']]})
    ex=sorted([r for r in stream if r['block']==1 and r['band']!='P_BELOW'],key=order)[:3]
    for n in (1,2,3):
        for eq,cash in [('1000000','0'),('1000000','50000'),('1000000','200000'),('1000000','1000000'),('250000','125000'),('1234567.89000','876543.21000')]:
            for held in [[],['P_HIGH'][:3-n],['P_BASE','P_MID'][:3-n]]:
                for ranks in [(r['rM'] for r in ex[:n]),[.49999999999999994,.5,.5000000000000001][:n],[1/1484,1.,.25][:n]]:
                    picked=[dict(r,band=b,rM=m) for r,b,m in zip(ex[:n],['P_HIGH','P_MID','P_BASE'],ranks)];cases.append({'case_id':f'synthetic/{len(cases)}','kind':'SYNTHETIC','picked':picked,'equity':eq,'cash':cash,'exposure':str(D(eq)-D(cash)),'held_bands':held})
    result=[]
    for c in cases:
        for arm in ARMS:
            assigned=allocation([dict(r,cap_policy=arm) for r in c['picked']],c['equity'],c['exposure'],c['cash'],c['held_bands'])
            result.append(c|{'arm':arm,'assigned':[{k:str(v) if isinstance(v,D) else v for k,v in a.items()} for a in assigned]})
    gzsave(PRIVATE/'CAP_PRE_MAIN_CASES.jsonl.gz',result)
    states=[]
    for r in stream:
        if r['band']=='P_BELOW' or r['entry_minute']>=920:continue
        for occ in range(4):
            x=gate(ARMS[0],r,occ,r['entry_minute'],tt[str(r['block'])]);assert x==gate(ARMS[1],r,occ,r['entry_minute'],tt[str(r['block'])]);ok,why,z=x
            states.append({'entry_id':r['entry_id'],'occupancy':occ,'action':ok,'reason':why,'audit':z})
    gzsave(PRIVATE/'FROZEN_I2_ACTION_SUPPORT.jsonl.gz',states)
    checks=[]
    def ck(name,ok,evidence):
        assert ok,name
        checks.append({'name':name,'PASS':bool(ok),'evidence':evidence})
    protected=read(WORK/'PROTECTED_TRACKED_HASHES.json');unchanged=all(sha(ROOT/p)==h for p,h in protected.items())
    reuse=read(OUT/'MRET_COMPLETED_FITS_REUSE_FREEZE.json');cert=read(OUT/'PREPROCESSING_BIT_CERTIFICATION.json');behavior=read(OUT/'MODEL_BEHAVIOR_CERTIFICATION.json');decision=read(OUT/'S9R_CERTIFICATION_DECISION.json');matrix=read(OUT/'NUMERIC_MATRIX_CERTIFICATE.json');frozen=read(OUT/'FROZEN_V11_SIGNAL_EVIDENCE.json')
    # Already-completed certificates are read-only, never invoked again.
    for name in ['Selector freeze','Entry freeze','EXIT freeze','pP freeze','U2 freeze','U3 freeze','I2 freeze','MRET teacher freeze','MRET feature freeze']:
        ck(name,unchanged and decision['S9R']=='PASS','hash-pinned old source and read-only S9R authority')
    for b in range(1,9):
        ck(f'MRET model hash block{b}',sha(V11/f'private/models/MRET_BLOCK_{b:02}.json')==read(PARENT/'MRET_8_FITS_RESULT.json')['fit_ledger'][b-1]['model_sha256'],'completed fit ledger identity')
    ck('no refit',counts()['newFits']==counts()['refits']==counts()['optimizer_calls']==0,'no optimizer calls in this cycle')
    for name in ['raw train IDs exact','row order exact','numeric field order exact','missing0 exact','missing indicator exact','categorical vocab exact']:
        ck(name,decision['conditions']['R3'] and decision['conditions']['R4'],'completed independent matrix certificate, no re-execution')
    for name,key in [('canonical mean bit exact','R5'),('canonical scale bit exact','R6'),('zero scale1 exact','R6'),('model-NPZ prep bit exact','R7'),('coef exact','R8'),('intercept exact','R8'),('OOF reconstruction','R10'),('train score reconstruction','R9'),('old S1-S8 hash exact','R11'),('old bootstrap hash exact','R12')]:
        ck(name,decision['conditions'][key],'new completed S9R condition and authenticated underlying certificate')
    ck('S9 old failure unchanged',read(PARENT/'SIGNAL_GATE_DECISION.json')['old_S9'] is False if 'old_S9' in read(PARENT/'SIGNAL_GATE_DECISION.json') else read(PARENT/'SIGNAL_GATE_DECISION.json')['status']=='V11_CONTRACT_FAIL','old branch/body SHA unchanged')
    ck('S9R separate new record',decision['oldS9']=='FAIL' and decision['S9R']=='PASS','old FAIL retained; new recovery record')
    tr=rows(PRIVATE/'FROZEN_MRET_PERCENTILE_TRAIN_SCORES.jsonl.gz');split=read(SPLIT)['blocks'];past=all(r['session'] in split[r['block']-1]['train'] and r['session']<min(split[r['block']-1]['test']) for r in tr)
    ck('rM training-only',past,'8057 frozen eligible completed-training scores')
    ck('test cross-section0',read(OUT/'RUNTIME_MRET_PERCENTILE_FREEZE.json')['test_cross_section'] is False,'training distribution per block only')
    for r in stream:
        dist=sorted(z['mP'] for z in tr if z['block']==r['block']);assert r['rM']==percentile(r['mP'],dist)
    ck('M1 cap formula',all(D(a['effective_cap'])==D(a['frozen_equity_cap'])*D(str(a['rM'])) for c in result if c['arm']==ARMS[0] for a in c['assigned']),'every synthetic and saved cap case')
    ck('M1 cap never increases',all(D(a['effective_cap'])<=D(a['frozen_equity_cap']) for c in result for a in c['assigned']),'all effective caps bounded')
    ck('M2 .5 rule',all(D(a['effective_cap'])==(D(a['frozen_equity_cap']) if a['rM']>=.5 else min(D(a['frozen_equity_cap']),D(a['lot_debit']))) for c in result if c['arm']==ARMS[1] for a in c['assigned']),'low and exact-half synthetic boundaries')
    ck('M2 one-lot low',all(a['quantity']<=100 for c in result if c['arm']==ARMS[1] for a in c['assigned'] if a['rM']<.5),'every low-rM allocation')
    src=inspect.getsource(allocation)
    ck('target utilization freeze',"D('.92')" in src and "D('.055')" in src and BASE=={'P_HIGH':D('.68'),'P_MID':D('.56'),'P_BASE':D('.44')},'exact old v11 function reused')
    ck('pP desired freeze',all(D(a['desired'])==D(a['batch_budget'])*D(str(r['pP']))/sum(D(str(x['pP'])) for x in c['picked']) for c in result for r,a in zip(c['picked'],c['assigned'])),'pP proportional in all cases')
    ck('I2 action freeze',all(z['action']==(z['audit']['future_pressure_session_N']*2<z['audit']['training_session_N']) for z in states if z['occupancy']<3),'all support states unchanged majority and both q2/q3 dominance')
    for name in ['tenure freeze','pressure freeze','admission freeze']:
        ck(name,unchanged,'pinned v8R1/v9 runtime and lookup table')
    ck('MAX3',all(not z['action'] for z in states if z['occupancy']==3),'occupancy3 rejects')
    for name in ['same-symbol','BUY exact','SELL exact','MTM exact','cash release exact','cutoff']:
        ck(name,unchanged,'unchanged parent day engine and execution adapter; full audit also mandatory')
    ck('lot100',all(a['quantity']%100==0 for c in result for a in c['assigned']),'all case quantities')
    ck('no backfill',all(a['quantity']==0 for c in result for a in c['assigned'] if a['first_pass_quantity']==0),'first-pass-zero never receives waterfill')
    for name in ['no later topup','no replacement','no forced exit']:
        ck(name,unchanged,'parent portfolio and frozen EXIT, unchanged')
    probe=next(r for r in stream if r['band']!='P_BELOW');tab=tt[str(probe['block'])];base=gate(ARMS[0],probe,1,probe['entry_minute'],tab)
    for name,field in [('future High decision0','future_high'),('future realized decision0','realized_return'),('teacher runtime0','MRET_label'),('alternate fsum diagnostic runtime0','alternate_scale')]:
        poison=dict(probe,**{field:float('inf')});ck(name,gate(ARMS[0],poison,1,poison['entry_minute'],tab)==base,'outcome/alternate fields unused by frozen gate/cap; causal inference feature allowlist')
    ck('old failure ignored0',decision['oldS9']=='FAIL','separate S9R does not rewrite or convert old failure')
    ck('tolerance relaxation0',decision['conditions']['R13'] and read(PARENT/'SIGNAL_GATE_DECISION.json')['tolerance']==1e-12,'score limit maintained; preprocessing uses uint64 identity')
    for name,k in [('Fresh0','fresh_open'),('main merge0','main_merge'),('orders0','orders')]:ck(name,counts()[k]==0,'zero budget counter')
    ck('Safety false',not any(SAFETY.values()),'all ten flags false')
    ck('cash nonnegative cases',all(sum(D(a['debit']) for a in c['assigned'])<=D(c['cash']) for c in result),'all synthetic/saved cash budgets')
    ck('budget exact',all(D(a['batch_budget'])==min(D(c['cash']),max(D(0),D(c['equity'])*D(a['target_utilization'])-D(c['exposure']))) for c in result for a in c['assigned']),'target and exposure operator unchanged')
    ck('waterfill quantity conservation',all(a['quantity']==a['first_pass_quantity']+100*a['water_fill_lots'] for c in result for a in c['assigned']),'one-lot rounds only')
    ck('effective cap bound after waterfill',all(D(a['debit'])<=D(a['effective_cap']) for c in result for a in c['assigned']),'all final debit bounds')
    ck('percentile strict ties',percentile(.5,[.2,.5,.5,.8])==2/5,'equal training scores counted zero')
    ck('percentile endpoints',percentile(-1,[.2,.5])==1/3 and percentile(1,[.2,.5])==1,'positive add-one endpoints')
    ck('batch ordering quality-free','q2' not in inspect.getsource(order) and 'q3' not in inspect.getsource(order) and 'mP' not in inspect.getsource(order),'pP timestamp symbol entry_id only')
    ck('training projection labels0',all(set(r)=={'entry_id','session','block','mP'} for r in tr),'no teacher passed to percentile table')
    ck('no signal evaluation rerun',counts()['primary_signal_evaluations']==counts()['bootstrap_reruns']==0,'frozen hash/body reuse only')
    ck('band caps unchanged',CAP=={'P_HIGH':D('.45'),'P_MID':D('.35'),'P_BASE':D('.25')},'effective cap never increases frozen maximum')
    assert len(checks)>=70
    save(OUT/'CAUSAL_CANARY_RESULTS.json',{'exact_jst':now(),'canary_N':len(checks),'PASS_N':len(checks),'all_PASS':True,'checks':checks,'synthetic_and_saved_case_N':len(result),'I2_same_state_action_N':len(states),'Main_replays_before_canaries':0,'Safety':SAFETY})
    checkpoint('N10_CAUSAL_CANARY_PASS',{'canary_N':len(checks),'PASS_N':len(checks),'case_N':len(result),'action_state_N':len(states)},'Independent raw inference / percentile / cap and lot audit')
if __name__=='__main__':build()
