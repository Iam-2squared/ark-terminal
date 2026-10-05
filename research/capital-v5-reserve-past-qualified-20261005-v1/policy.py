"""The single fixed Reserve exception. Causal current inputs only; no outcomes/books/IDs."""
from decimal import Decimal
import math, sys
from context import NATIVE_ROOT

sys.path.insert(0,str(NATIVE_ROOT))
from allocation import allocation as native_allocation, band as native_band
from slot_policy import gate as native_gate
from staircase import candidate_order

D=Decimal
RESERVE=frozenset(('SLOT2_RESERVE_FOR_FUTURE_QUALITY','SLOT3_RESERVE_FOR_FUTURE_QUALITY'))
HEADS=('pP','MOVE_U2','MOVE_U3')

def scalar(o):
    if isinstance(o,D):return str(o)
    if isinstance(o,list):return [scalar(x) for x in o]
    if isinstance(o,dict):return {k:scalar(v) for k,v in o.items()}
    return o

def project_packet(record):
    """Explicit allowlist excludes MRET, outcomes, future-source lists and protected identities."""
    return {'entry_id':record['entry_id'],'session':record['session'],'symbol':record['symbol'],
        'minute':record['entry_minute'],'block':record['native_block'],
        'scores':{h:{k:record['heads'][h][k] for k in ('raw_score','numerator','denominator','available',
            'score_asof','feature_max_source_minute','prediction_origin','model_hash','training_reference_hash')}
            for h in HEADS}}

def score_check(packet):
    for h in HEADS:
        q=packet['scores'].get(h)
        if not q or not q.get('available') or not isinstance(q.get('raw_score'),(int,float)) or not math.isfinite(q['raw_score']):
            return False,'SCORE_UNKNOWN_ABSTAIN'
        n=q.get('numerator');d=q.get('denominator')
        if not isinstance(n,int) or not isinstance(d,int) or not 1<=n<=d:
            return False,'REFERENCE_UNKNOWN_ABSTAIN'
    p,q2,q3=(packet['scores'][h] for h in HEADS)
    if 4*p['numerator']<3*p['denominator']:return False,'WINNER_RANK_BELOW_3_4'
    if 2*q2['numerator']<q2['denominator'] and 2*q3['numerator']<q3['denominator']:
        return False,'BOTH_QUALITY_LOW'
    return True,'SCORE_PASS'

def native_wrapper(candidates,snapshot,session,minute,table):
    """Pure native current batch. OFF saved-case comparison does not generate a market path."""
    positions=snapshot['positions'];picked=[];decisions=[]
    for r in sorted(candidates,key=candidate_order):
        assert r['session']==session and r['entry_minute']==minute
        d={'entry_id':r['entry_id'],'reason':None}
        decisions.append(d)
        if minute>=920:d['reason']='CAPITAL_EOD_ENTRY_CUTOFF';continue
        if not r['admission']:d['reason']='UPWARD_BELOW_BASELINE';continue
        if native_band(r['capital_score']) is None:d['reason']='SCORE_INPUT_UNKNOWN';continue
        if any(p['symbol']==r['symbol'] for p in positions.values()):d['reason']='SYMBOL_ALREADY_OPEN';continue
        allowed,why,audit=native_gate(r,len(positions)+len(picked),minute,table)
        d.update(audit,slot_gate_reason=why,slot_gate_action='ADMIT' if allowed else 'REJECT')
        if not allowed:
            d['reason']='SLOT_RESERVE_REJECT' if why in RESERVE else why
            continue
        d['slot_admission_index']=len(positions)+len(picked)+1;picked.append(r)
    assigned=[]
    if picked:
        assigned=native_allocation(picked,snapshot['equity'],snapshot['exposure'],snapshot['cash'],
            [p['band'] for p in positions.values()])
    return {'picked_ids':[r['entry_id'] for r in picked],'gate_decisions':decisions,'assigned':scalar(assigned)}

def singleton(row,snapshot):
    """Native source function once per saved selected case; no forced minlot or backfill."""
    assigned=native_allocation([row],snapshot['equity'],snapshot['exposure'],snapshot['cash'],
        [p['band'] for p in snapshot['positions'].values()])[0]
    if assigned['quantity']>=100:why='FUNDABLE'
    else:
        lot=assigned['lot_debit']
        if D(snapshot['cash'])<lot:why='CASH_BELOW_1LOT'
        elif assigned['batch_budget']<lot:why='CASH_AVAILABLE_TARGET_BUDGET_BELOW_1LOT'
        elif assigned['equity_cap']<lot:why='CAP_BELOW_1LOT'
        else:why='ALLOCATION_QUANTITY_ZERO'
    assert assigned['debit']<=D(snapshot['cash']) and assigned['debit']<=assigned['batch_budget']
    assert assigned['debit']<=assigned['equity_cap']
    return scalar(assigned)|{'fundability_reason':why}

def proposal(candidates,native,snapshot,packets,session,minute,recovered=False,qualified=True,pending_symbols=()):
    """Outcome-blind decision. The qualified Boolean is a pinned past-only artifact value."""
    if native['picked_ids']:return {'reason':'NATIVE_PICKED_NONEMPTY','candidate':None}
    if not qualified:return {'reason':'PAST_UNQUALIFIED_ABSTAIN','candidate':None}
    if recovered:return {'reason':'SESSION_RECOVERY_ALREADY_USED','candidate':None}
    if len(snapshot['positions']) not in (1,2):return {'reason':'ACTUAL_OPEN_NOT_1_OR_2','candidate':None}
    if minute>=920:return {'reason':'ENTRY_CUTOFF','candidate':None}
    decisions={x['entry_id']:x for x in native['gate_decisions']}
    pool=[r for r in sorted(candidates,key=candidate_order) if r['rank']=='B' and r['admission'] and r['ML']>=1
        and decisions[r['entry_id']].get('slot_gate_reason') in RESERVE]
    if not pool:return {'reason':'NO_STRUCTURAL_RESERVE_POOL','candidate':None}
    for r in pool:
        p=packets.get(r['entry_id']);s=p['scores']['pP'] if p else None
        if not s or not s['available'] or not math.isfinite(s['raw_score']):
            return {'reason':'POOL_PP_UNKNOWN_ABSTAIN','candidate':None,'pool_ids':[r['entry_id'] for r in pool]}
    # Stable sort retains V5's native stable order for raw-pP equality.
    row=sorted(pool,key=lambda r:-packets[r['entry_id']]['scores']['pP']['raw_score'])[0]
    key=row['entry_id'];p=packets[key]
    result={'candidate':key,'pool_ids':[r['entry_id'] for r in pool],
        'session':session,'minute':minute,'block':row['block'],'native_reason':decisions[key]['slot_gate_reason']}
    if row['symbol'] in pending_symbols or any(x['symbol']==row['symbol'] for x in snapshot['positions'].values()):
        return result|{'reason':'SAME_SYMBOL_OR_PENDING_ABSTAIN'}
    if row['session']!=session or row['entry_minute']!=minute or p['session']!=session or p['minute']!=minute:
        return result|{'reason':'ENTRY_IDENTITY_ASOF_ABSTAIN'}
    for h in HEADS:
        q=p['scores'][h]
        if q['score_asof']!=row['entry_timestamp'] or q['feature_max_source_minute']>=minute or q['prediction_origin']['train_through']>=session:
            return result|{'reason':'SCORE_ASOF_ABSTAIN'}
    passed,why=score_check(p)
    if not passed:return result|{'reason':why}
    a=singleton(row,snapshot)
    return result|{'reason':a['fundability_reason'],'allocation':a,'scores':p['scores']}

def success_counter(previous,quantity):
    return previous or quantity>=100
