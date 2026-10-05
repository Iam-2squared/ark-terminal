"""Frozen I2 decisions and pP desired sizing; only effective absolute caps change."""
from control import ROOT,ARMS
from decimal import Decimal as D,ROUND_FLOOR
from bisect import bisect_left
import importlib.util
spec=importlib.util.spec_from_file_location('v11_frozen_I2',ROOT/'research/capital-v9-quality-aware-max3-integration-20261005-v1/runtime.py')
FROZEN=importlib.util.module_from_spec(spec);spec.loader.exec_module(FROZEN)
order=FROZEN.order;predicted_release=FROZEN.predicted_release
CAP={'P_HIGH':D('.45'),'P_MID':D('.35'),'P_BASE':D('.25')}
BASE={'P_HIGH':D('.68'),'P_MID':D('.56'),'P_BASE':D('.44')}
def percentile(score,training):return (1+bisect_left(training,score))/(len(training)+1)
def gate(arm,r,occupancy,minute,table):
    assert arm in ARMS
    return FROZEN.gate(FROZEN.ARMS[1],r,occupancy,minute,table)
def effective_cap(arm,band,equity,rM,lot_debit):
    assert arm in ARMS and 0<rM<=1
    frozen=D(str(equity))*CAP[band]
    return frozen*D(str(rM)) if arm==ARMS[0] else (frozen if rM>=.5 else min(frozen,D(str(lot_debit))))
def allocation(picked,equity,exposure,cash,existing_bands):
    eq=D(str(equity));cash=D(str(cash));exposure=D(str(exposure))
    bands=list(existing_bands)+[r['band'] for r in picked];assert bands and all(b in CAP for b in bands)
    best=min(bands,key=lambda b:('P_HIGH','P_MID','P_BASE').index(b))
    target=min(D('.92'),BASE[best]+D('.055')*(len(bands)-1));budget=min(cash,max(D(0),eq*target-exposure))
    weights=sum(D(str(r['pP'])) for r in picked);remaining=cash;unspent=budget;assigned=[]
    for r in picked:
        lot=D(r['raw_reference'])*D('1.0005')*100;frozen=eq*CAP[r['band']]
        cap=effective_cap(r['cap_policy'],r['band'],eq,r['rM'],lot)
        desired=budget*D(str(r['pP']))/weights;limit=min(desired,cap,remaining)
        lots=max(0,int((limit/lot).to_integral_value(rounding=ROUND_FLOOR)));debit=lots*lot;remaining-=debit;unspent-=debit
        assigned.append({'entry_id':r['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'effective_cap':cap,'frozen_equity_cap':frozen,'desired':desired,'band':r['band'],'target_utilization':target,'batch_equity':eq,'batch_budget':budget,'mP':r['mP'],'rM':r['rM'],'cap_policy':r['cap_policy']})
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
    assert remaining>=0 and unspent>=0
    for a in assigned:
        assert a['quantity']%100==0 and a['debit']<=a['effective_cap']<=a['frozen_equity_cap']
        a.update(water_fill_rounds=rounds,budget_unspent=unspent,cap_hit=a['debit']+a['lot_debit']>a['effective_cap'])
    return assigned
