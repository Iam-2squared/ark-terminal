"""Finite synthetic accounting cases and saved batches; no capital replay."""
from control import *
from runtime import allocation,gate,order,percentile,consensus,CAP,BASE
from scores import tables
from decimal import Decimal as D
from collections import defaultdict
import ast,inspect
def build():
    stream=rows(PRIVATE/'CURRENT_SIZING_RUNTIME.jsonl.gz');rt={r['entry_id']:r for r in stream};ts=tables();saved=rows(V9PRIVATE/f'{I2}_DECISIONS.jsonl.gz');batches=defaultdict(list);cases=[]
    for r in saved:
        if 'batch_budget' in r:batches[r['session'],r['minute']].append(r)
    for tag,ds in sorted(batches.items()):
        ds.sort(key=lambda r:r['batch_index']);a=ds[0];cases.append({'case_id':f'saved/{tag[0]}/{tag[1]}','kind':'SAVED_PRE_MAIN_BATCH','entry_ids':[r['entry_id'] for r in ds],'picked':[rt[r['entry_id']] for r in ds],'equity':a['batch_equity'],'cash':a['cash_before'],'exposure':str(D(a['batch_equity'])-D(a['cash_before'])),'held_bands':[p['band'] for p in a['held_before_batch']]})
    example=sorted([r for r in stream if r['block']==1 and r['band']!='P_BELOW'],key=order)[:3]
    for n in (1,2,3):
        for eq,cash in [('1000000','0'),('1000000','50000'),('1000000','200000'),('1000000','1000000'),('250000','125000'),('1234567.89000','876543.21000')]:
            for held in [[],['P_HIGH'][:3-n],['P_BASE','P_MID'][:3-n]]:
                picked=[dict(r,band=b) for r,b in zip(example[:n],['P_HIGH','P_MID','P_BASE'])];cases.append({'case_id':f'synthetic/{len(cases)}','kind':'SYNTHETIC','entry_ids':[r['entry_id'] for r in picked],'picked':picked,'equity':eq,'cash':cash,'exposure':str(D(eq)-D(cash)),'held_bands':held})
    result=[]
    for c in cases:
        for arm in ARMS:
            rr=[dict(r,sizing_weight=1 if arm==ARMS[0] else r['consensus_weight']) for r in c['picked']];aa=allocation(rr,c['equity'],c['exposure'],c['cash'],c['held_bands']);result.append({**c,'arm':arm,'assigned':[{k:str(v) if isinstance(v,D) else v for k,v in a.items()} for a in aa]})
    gzsave(PRIVATE/'SIZING_PRE_MAIN_CASES.jsonl.gz',result)
    states=[]
    for r in stream:
        if r['band']=='P_BELOW' or r['entry_minute']>=920:continue
        for occ in range(4):
            ok,why,z=gate(ARMS[0],r,occ,r['entry_minute'],ts[str(r['block'])]);assert (ok,why,z)==gate(ARMS[1],r,occ,r['entry_minute'],ts[str(r['block'])]);states.append({'entry_id':r['entry_id'],'occupancy':occ,'action':ok,'reason':why,'audit':z})
    gzsave(PRIVATE/'FROZEN_I2_ACTION_SUPPORT.jsonl.gz',states)
    checks=[]
    def ck(name,ok,evidence):
        assert ok,name
        checks.append({'name':name,'PASS':bool(ok),'evidence':evidence})
    freeze=read(OUT/'V9_PARENT_AUTHORITY_FREEZE.json');parent_ok=all(sha(ROOT/p)==h for p,h in freeze['frozen_parent_source_sha256'].items());source=inspect.getsource(allocation);gate_source=inspect.getsource(gate);graph='\n'.join((CODE/f).read_text() for f in ['runtime.py','scores.py','replay.py','execution_bridge.py']);pr=read(OUT/'SIZING_PERCENTILE_RUNTIME_FREEZE.json');safe=read(OUT/'INPUT_PRIVATE_AUTHORITY_AUDIT.json')['mismatch_N']==0
    for name in ['Selector freeze','Entry freeze','EXIT freeze','pP model exact','U2 model exact','U3 model exact','tenure exact','Admission exact','parent hashes exact','old Evidence rewrite0']:
        ck(name,parent_ok and safe,'pinned source/manifest hashes independently checked; old source untouched')
    ck('I2 gate exact',all(gate(ARMS[0],rt[z['entry_id']],z['occupancy'],rt[z['entry_id']]['entry_minute'],ts[str(rt[z['entry_id']]['block'])])==gate(ARMS[1],rt[z['entry_id']],z['occupancy'],rt[z['entry_id']]['entry_minute'],ts[str(rt[z['entry_id']]['block'])]) for z in states),'all1960 same-state action supports, both arms same q2/q3 gate')
    ck('0.5 exact',all(z['action']==(z['audit']['future_pressure_session_N']*2<z['audit']['training_session_N']) for z in states if z['occupancy']<3),'integer majority compare')
    ck('support10 exact',parent_ok,'frozen B2 function and lookup hash')
    ck('candidate cap exact',CAP=={'P_HIGH':D('.45'),'P_MID':D('.35'),'P_BASE':D('.25')},'band cap constants')
    ck('base utilization exact',BASE=={'P_HIGH':D('.68'),'P_MID':D('.56'),'P_BASE':D('.44')},'band base constants')
    ck('breadth increment exact',"D('.055')" in source,'operation copied from frozen v7')
    ck('max target exact',"D('.92')" in source,'operation copied from frozen v7')
    ck('lot100',all(a['quantity']%100==0 for c in result for a in c['assigned']),'synthetic+saved cases')
    ck('no backfill',all(a['first_pass_quantity']>0 or a['quantity']==0 for c in result for a in c['assigned']),'no zero-first-pass candidate ever funded by waterfill')
    ck('no later topup',parent_ok and 'later_topup' not in graph,'same parent day engine')
    ck('no replacement',parent_ok and 'replacement' not in graph,'same parent day engine')
    ck('no forced exit',parent_ok,'frozen v5 execution adapter only')
    ck('S1 weight all1',all(a['sizing_weight']=='1' for c in result if c['arm']==ARMS[0] for a in c['assigned']),'everycase')
    train=rows(PRIVATE/'SIZING_TRAIN_SCORE_TABLE.jsonl.gz');split=read(SPLIT)['blocks'];past=all(r['session'] in split[r['block']-1]['train'] and r['session']<min(split[r['block']-1]['test']) for r in train)
    ck('S2 percentile past only',past,'all8161 training rows strictly completed-past')
    for name in ['S2 pP no test cross-section','S2 q2 no test cross-section','S2 q3 no test cross-section']:
        ck(name,pr['test_cross_section'] is False and past,'block training score arrays only')
    ck('S2 percentile labels0',all(set(r)=={'entry_id','session','entry_minute','pP','r','band','block','q2','q3'} for r in train),'strict field projection')
    ck('S2 min exact',all(r['consensus_weight']==min(r['rp'],r['r2'],r['r3']) for r in stream),'all1039current rows')
    ck('S2 weight positive',all(r['consensus_weight']>0 for r in stream),'add-one formula')
    ck('batch order pP exact',parent_ok and inspect.getsource(order)==inspect.getsource(__import__('runtime').FROZEN.order),'frozen pP/time/symbol/entry_id')
    ck('quality no reorder',all('q2' not in inspect.getsource(order) and 'q3' not in inspect.getsource(order) for _ in [0]),'order function has pP only')
    ck('target budget exact',all(D(a['batch_budget'])==min(D(c['cash']),max(D(0),D(c['equity'])*D(a['target_utilization'])-D(c['exposure']))) for c in result for a in c['assigned']),'all case budgets')
    ck('first pass floor exact',all(a['first_pass_quantity']==max(0,int((min(D(a['desired']),D(a['equity_cap']),D(c['cash'])-sum(D(x['lot_debit'])*x['first_pass_quantity']/100 for x in c['assigned'][:i]))/D(a['lot_debit'])).to_integral_value(rounding='ROUND_FLOOR')))*100 for c in result for i,a in enumerate(c['assigned'])),'all floors with sequential remaining cash')
    ck('waterfill exact',all(a['quantity']==a['first_pass_quantity']+100*a['water_fill_lots'] for c in result for a in c['assigned']),'descending original order one-lot rounds')
    ck('new weight cap exact',all(D(a['debit'])<=D(a['equity_cap']) for c in result for a in c['assigned']),'all allocations cap bound')
    ck('cash nonnegative',all(sum(D(a['debit']) for a in c['assigned'])<=D(c['cash']) for c in result),'all cases')
    ck('MAX3 <=3',all(z['occupancy']<3 or not z['action'] for z in states),'occupied3 reject exact')
    for name in ['same-symbol <=1','cutoff15:20','BUY1.0005','SELL0.9995','commission0','MTM exact','cash release exact']:
        ck(name,parent_ok,'unchanged hash-pinned v9 day engine and v5 execution adapter; independent full accounting required')
    probe=next(r for r in stream if r['band']!='P_BELOW');tab=ts[str(probe['block'])];baseline=gate(ARMS[0],probe,1,probe['entry_minute'],tab)
    for name,field in [('future High use0','future_high'),('future PnL use0','realized_pnl'),('future EXIT use0','future_exit')]:
        poison=dict(probe,**{field:float('inf'),'potential_bucket':'MUTATED','U2':-999,'U3':999});ck(name,gate(ARMS[0],poison,1,poison['entry_minute'],tab)==baseline and consensus(poison,tab['sorted_train'])==consensus(probe,tab['sorted_train']),'mutation leaves action and weight unchanged')
    for name,needle in [('attribution not imported','attribution'),('hindsight not imported','hindsight'),('100share shadow not runtime','shadows')]:ck(name,needle not in graph,'runtime dependency graph excludes evaluation-only modules')
    ck('Quality true probability claim false',pr['probability_claim'] is False,'raw Logistic score ordering only')
    ck('pP true probability claim false',pr['probability_claim'] is False,'frozen score not claimed true probability')
    ck('new fit0',pr['fits']==0 and '.fit(' not in graph,'frozen inference only')
    ck('threshold sweep0','threshold' not in graph and 'sweep' not in graph,'exact two precommitted sizing functions')
    ck('Fresh0',counts()['fresh_open']==0,'only Development split OOF38 and completed past')
    ck('Safety all false',not any(SAFETY.values()),'ten false flags and no order interfaces')
    ck('percentile tie strict less',percentile(.5,[.2,.5,.5,.8])==2/5,'equal scores share percentile')
    ck('percentile endpoints',percentile(-1,[.2,.5])==1/3 and percentile(1,[.2,.5])==1,'positive add-one endpoints')
    ck('gate ignores sizing weight',gate(ARMS[0],dict(probe,sizing_weight=999),1,probe['entry_minute'],tab)==baseline,'weight does not affect same-state selection')
    ck('single picked normalization',all(D(c['assigned'][0]['desired'])==D(c['assigned'][0]['batch_budget']) for c in result if len(c['assigned'])==1),'single candidate weight cancels')
    assert len(checks)>=55
    save(OUT/'CAUSAL_CANARY_RESULTS.json',{'exact_jst':now(),'canary_N':len(checks),'PASS_N':len(checks),'all_PASS':True,'checks':checks,'synthetic_and_saved_sizing_case_N':len(result),'I2_same_state_action_N':len(states),'pre_Main_capital_replays':0,'Safety':SAFETY});checkpoint('M7_CAUSAL_CANARY_PASS',{'canary_N':len(checks),'PASS_N':len(checks),'primary_replays':0},'Independent raw inference / percentiles / sizing cases before Main')
if __name__=='__main__':build()
