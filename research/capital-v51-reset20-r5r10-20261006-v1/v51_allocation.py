"""V5.1: integer minimum lots then frozen pP-prioritized additional lots.
Only current price/score/account state is read. No labels or execution suffix.
"""
from decimal import Decimal as D,ROUND_FLOOR
import math
from allocation import allocation as native_allocation,band,CAP,BASE
from execution import BUY
from staircase import candidate_order

def allocation(picked,equity,exposure,cash,existing_bands):
    # Unknown current frozen score abstains for the complete allocation batch.
    if any(r.get('lot_priority_pP') is None or not math.isfinite(r['lot_priority_pP']) for r in picked):
        return native_allocation(picked,equity,exposure,cash,existing_bands)
    eq=D(str(equity));cash=D(str(cash));exposure=D(str(exposure))
    bands=list(existing_bands)+[band(r['capital_score']) for r in picked]
    assert bands and all(b in CAP for b in bands)
    best=min(bands,key=lambda b:('S','A','B').index(b))
    target=min(D('.92'),BASE[best]+D('.055')*(len(bands)-1))
    budget=min(cash,max(D(0),eq*target-exposure))
    remaining=cash;unspent=budget
    assigned=[{'entry_id':r['entry_id'],'quantity':0,'first_pass_quantity':0,'water_fill_lots':0,'debit':D(0),'lot_debit':D(r['raw_reference'])*BUY*100,'equity_cap':eq*CAP[band(r['capital_score'])],'liquidity_cap':None,'desired':None,'band':band(r['capital_score']),'target_utilization':target,'batch_equity':eq,'batch_budget':budget,'lot_priority_pP':r['lot_priority_pP']} for r in picked]
    order=sorted(range(len(picked)),key=lambda i:(-picked[i]['lot_priority_pP'],candidate_order(picked[i]),picked[i]['entry_id']))
    # Initial grant is exactly one affordable/cap-legal lot per admitted Entry.
    for i in order:
        a=assigned[i];lot=a['lot_debit']
        if lot<=unspent and lot<=remaining and lot<=a['equity_cap']:
            a.update(quantity=100,first_pass_quantity=100,debit=lot);unspent-=lot;remaining-=lot
    # All further lots go to the highest pP until its inherited band cap binds,
    # then to the next currently admitted Entry. No weight or threshold added.
    for i in order:
        a=assigned[i]
        if a['first_pass_quantity']<100:continue
        lots=max(0,int((min(unspent,remaining,a['equity_cap']-a['debit'])/a['lot_debit']).to_integral_value(rounding=ROUND_FLOOR)))
        debit=lots*a['lot_debit'];a['quantity']+=lots*100;a['water_fill_lots']=lots;a['debit']+=debit;unspent-=debit;remaining-=debit
    assert remaining>=0 and unspent>=0
    assert all(a['quantity']%100==0 and a['debit']<=a['equity_cap'] for a in assigned)
    for a in assigned:a.update(water_fill_rounds=None,budget_unspent=unspent)
    return assigned
