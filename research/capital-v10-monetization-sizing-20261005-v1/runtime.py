"""Only picked-candidate weights change; frozen I2 gate and sizing operations."""
from control import ROOT,ARMS,I2
from decimal import Decimal as D,ROUND_FLOOR
from bisect import bisect_left
import importlib.util
PATH=ROOT/'research/capital-v9-quality-aware-max3-integration-20261005-v1/runtime.py'
SPEC=importlib.util.spec_from_file_location('v10_frozen_I2',PATH)
FROZEN=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FROZEN)
order=FROZEN.order
predicted_release=FROZEN.predicted_release
CAP={'P_HIGH':D('.45'),'P_MID':D('.35'),'P_BASE':D('.25')}
BASE={'P_HIGH':D('.68'),'P_MID':D('.56'),'P_BASE':D('.44')}
def percentile(score,training):return (1+bisect_left(training,score))/(len(training)+1)
def consensus(r,sorted_train):
    rank={name:percentile(r[field],sorted_train[field]) for name,field in [('rp','pP'),('r2','q2'),('r3','q3')]}
    assert all(0<v<=1 for v in rank.values())
    return rank|min_weight(rank)
def min_weight(rank):return {'consensus_weight':min(rank.values())}
def gate(arm,r,occupancy,minute,table):
    assert arm in ARMS
    # Parent's module ARMS sees v10 control, so call its I2 position; semantics
    # remain q2 AND q3 regardless of sizing arm.
    return FROZEN.gate(FROZEN.ARMS[1],r,occupancy,minute,table)
def allocation(picked,equity,exposure,cash,existing_bands):
    # Exact v7 allocation operation sequence. Replace only weight lookup.
    eq=D(str(equity));cash=D(str(cash));exposure=D(str(exposure))
    bands=list(existing_bands)+[r['band'] for r in picked];assert bands and all(b in CAP for b in bands)
    best=min(bands,key=lambda b:('P_HIGH','P_MID','P_BASE').index(b))
    target=min(D('.92'),BASE[best]+D('.055')*(len(bands)-1));budget=min(cash,max(D(0),eq*target-exposure))
    weights=sum(D(str(r['sizing_weight'])) for r in picked);remaining=cash;unspent=budget;assigned=[]
    for r in picked:
        weight=D(str(r['sizing_weight']));assert weight>0
        bb=r['band'];lot=D(r['raw_reference'])*D('1.0005')*100
        cap=eq*CAP[bb];desired=budget*weight/weights;limit=min(desired,cap,remaining)
        lots=max(0,int((limit/lot).to_integral_value(rounding=ROUND_FLOOR)));debit=lots*lot;remaining-=debit;unspent-=debit
        assigned.append({'entry_id':r['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'desired':desired,'band':bb,'target_utilization':target,'batch_equity':eq,'batch_budget':budget,'sizing_weight':weight,'rp':r['rp'],'r2':r['r2'],'r3':r['r3'],'cap_hit':debit+lot>cap})
    rounds=0
    while True:
        changed=False
        for a in assigned:
            if a['first_pass_quantity']<100:continue
            lot=a['lot_debit']
            if lot>remaining or lot>unspent or a['debit']+lot>a['equity_cap']:continue
            a['quantity']+=100;a['water_fill_lots']+=1;a['debit']+=lot;remaining-=lot;unspent-=lot;changed=True
        if not changed:break
        rounds+=1
    assert all(a['quantity']%100==0 and a['debit']<=a['equity_cap'] for a in assigned)
    assert remaining>=0 and unspent>=0
    for a in assigned:a.update(water_fill_rounds=rounds,budget_unspent=unspent,cap_hit=a['debit']+a['lot_debit']>a['equity_cap'])
    return assigned
