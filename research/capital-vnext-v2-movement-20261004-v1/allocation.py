"""Outcome-blind continuous-score funding and deterministic lot water-fill."""
from decimal import Decimal,ROUND_FLOOR
from statistics import median
import math
from execution import BUY
from movement import complete,activity

D=Decimal
CAP={'HIGH':D('.45'),'MID':D('.35'),'BASE':D('.25')}
BASE={'HIGH':D('.68'),'MID':D('.56'),'BASE':D('.44')}

def band(score):
 if score is None or not math.isfinite(score) or score<1:return None
 return 'HIGH' if score>=2 else 'MID' if score>=1.5 else 'BASE'

def liquidity(core,cal,history):
 day=core['session'];symbol=core['symbol'];raw=D(core['raw_reference'])
 prior=[d for d in cal if d<day][-20:];valid=[]
 for date in prior:
  r=history.get((date,symbol))
  if not complete(r) or not r.get('daily'):continue
  assert r['session']<day
  try:value=D(str(r['daily']['Va']))
  except Exception:continue
  if not value.is_finite() or value<0:continue
  a=activity(r['active_minute_bitmap_hex'])
  valid.append({'session':date,'value':value,'coverage':D(a['active_5m_N'])/D(65),
   'actual_minutes':a['actual_trade_minute_N'],'max_no_trade':a['max_consecutive_no_trade_minutes']})
 out={'support':len(valid),'lookback_dates':prior,'support_dates':[r['session'] for r in valid],
  'eligible':False,'reason':'LIQUIDITY_UNKNOWN','minimum_lot_notional':str(raw*100),
  'median_value':None,'median_coverage':None,'capacity':None,
  'median_actual_trade_minute_count':median(r['actual_minutes'] for r in valid) if valid else None,
  'median_max_consecutive_no_trade_minutes':median(r['max_no_trade'] for r in valid) if valid else None}
 if len(valid)<10:return out
 value=median(r['value'] for r in valid);coverage=median(r['coverage'] for r in valid)
 value_ok=raw*100<=value*D('.05');coverage_ok=coverage>=D('.20')
 out.update(median_value=str(value),median_coverage=str(coverage),capacity=str(value*D('.05')),
  lot_gate_pass=value_ok,coverage_gate_pass=coverage_ok,eligible=value_ok and coverage_ok,
  reason='LIQUIDITY_ELIGIBLE' if value_ok and coverage_ok else 'EXTREME_ILLIQUIDITY_REJECT')
 return out

def allocation(picked,equity,exposure,cash,existing_bands):
 """Rows already pass cutoff, extreme veto, fixed score1, identity/MAX rules."""
 eq=D(str(equity));cash=D(str(cash));exposure=D(str(exposure))
 bands=list(existing_bands)+[band(r['capital_score']) for r in picked]
 assert bands and all(b in CAP for b in bands)
 best=min(bands,key=lambda b:('HIGH','MID','BASE').index(b))
 target=min(D('.92'),BASE[best]+D('.055')*(len(bands)-1))
 budget=min(cash,max(D(0),eq*target-exposure))
 weights=sum(D(str(r['capital_score'])) for r in picked)
 remaining=cash;unspent=budget;assigned=[]
 for r in picked:
  weight=D(str(r['capital_score']));bb=band(r['capital_score']);lot=D(r['raw_reference'])*BUY*100
  cap=eq*CAP[bb];liq=D(r['liquidity']['capacity']);desired=budget*weight/weights
  limit=min(desired,cap,liq,remaining)
  lots=max(0,int((limit/lot).to_integral_value(rounding=ROUND_FLOOR)))
  debit=lots*lot;remaining-=debit;unspent-=debit
  assigned.append({'entry_id':r['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,
   'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'liquidity_cap':liq,
   'desired':desired,'band':bb,'target_utilization':target,'batch_equity':eq,'batch_budget':budget})
 # Only initially funded candidates; fixed score-descending rounds of one lot.
 rounds=0
 while True:
  changed=False
  for a in assigned:
   if a['first_pass_quantity']<100:continue
   lot=a['lot_debit']
   if lot>remaining or lot>unspent or a['debit']+lot>min(a['equity_cap'],a['liquidity_cap']):continue
   a['quantity']+=100;a['water_fill_lots']+=1;a['debit']+=lot
   remaining-=lot;unspent-=lot;changed=True
  if not changed:break
  rounds+=1
 assert all(a['quantity']%100==0 and a['debit']<=min(a['equity_cap'],a['liquidity_cap']) for a in assigned)
 assert remaining>=0 and unspent>=0
 for a in assigned:a['water_fill_rounds']=rounds;a['budget_unspent']=unspent
 return assigned
