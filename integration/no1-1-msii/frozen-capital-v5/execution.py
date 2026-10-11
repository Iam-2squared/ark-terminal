"""Inherited audited v1 execution/MTM functions only; v1 gate and rank not reused."""
from decimal import Decimal
from datetime import datetime
D=Decimal
BUY=D("1.0005")
SELL=D("0.9995")

def valid_market(r,auction=False):
    try:
        if not r.get('lineage'):return False
        v={k:D(str(r[k])) for k in ('O','H','L','C','Vo','Va')}
        if not all(x.is_finite() and x>0 for x in v.values()):return False
        if not v['L']<=min(v['O'],v['C'])<=max(v['O'],v['C'])<=v['H']:return False
        return not auction or v['O']==v['H']==v['L']==v['C']
    except (KeyError,ValueError,TypeError):return False

def last_actual_mark(rows,entry_minute,t,anchor,session):
    candidates=[r for r in rows if r.get('session')==session and entry_minute<=r['minute'] and r['minute']+1<=t and valid_market(r)]
    if candidates:
        row=max(candidates,key=lambda r:r['minute'])
        return D(str(row['C'])),row['minute']+1
    return D(str(anchor)),entry_minute

def limit_up_confirmed(record,day,t):
    return bool(record and record.get('status')=='LIMIT_UP_CONFIRMED'
                and record.get('authoritative_price_limit_source') and record.get('causal_exchange_status')
                and record.get('session')==day and record.get('known_minute',9999)<=t
                and record.get('observed_minute',9999)<=t)

def eod_intent(position,t=920):
    if t!=920 or position.get('closed') or position['quantity']<=0 or position.get('intent_issued'):return None
    assert position.get('side','LONG')=='LONG' and not position.get('margin',False)
    return {'minute':920,'side':'SELL','quantity':position['quantity'],'sor':True,
            'order_type':'MARKET','condition':'DAY','transmitted':False}

def eod_source(rows,session):
    regular=sorted([r for r in rows if r.get('session')==session and 920<=r['minute']<925 and valid_market(r)],key=lambda r:r['minute'])
    auction=[r for r in rows if r.get('session')==session and r['minute']==930 and valid_market(r,True)]
    selected=regular[0] if regular else auction[0] if auction else None
    if selected is None:return None
    kind='EOD_REGULAR' if regular else 'EOD_EXACT_1530_AUCTION'
    p=D(str(selected['O'] if regular else selected['C']))*SELL
    return {'kind':kind,'source_minute':selected['minute'],'release_minute':selected['minute']+1,
            'price':str(p),'lineage':selected['lineage']}

def clock(value):
    t=datetime.fromisoformat(value)
    return t.hour*60+t.minute

def frozen_execution(book):
    x=book['frozen_exit']
    if x['sell_status']!='FILLED':return None
    available=clock(x['sell_source_assumed_available_at'])
    # The confirmed fill event precedes15:20 overlay only if source already available.
    if available>920:return None
    source=next((r for r in book['market'] if r['minute']==x['sell_minute']),None)
    if source is None or not valid_market(source):return {'blocked':'FROZEN_EXIT_SOURCE_LINEAGE_BLOCKED','release_minute':available}
    reference=source['O'] if x['sell_source']=='NEXT_ELIGIBLE_REGULAR_RAW_OPEN' else source['C']
    price=D(str(reference))*SELL
    assert price==D(x['sell_price_decimal']),'FROZEN_EXIT_SOURCE_PRICE_MISMATCH'
    return {'kind':'FROZEN_EXIT_V3','source_minute':x['sell_minute'],'release_minute':available,
            'price':str(price),'lineage':source['lineage']}
