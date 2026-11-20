"""Outcome-blind continuous-score funding and deterministic lot water-fill."""
from decimal import Decimal,ROUND_FLOOR
from statistics import median
import math
from execution import BUY

D=Decimal
CAP={'S':D('.45'),'A':D('.35'),'B':D('.25')}
BASE={'S':D('.68'),'A':D('.56'),'B':D('.44')}

def band(score):
 if score is None or not math.isfinite(score) or score<1:return None
 return 'S' if score>=2 else 'A' if score>=1.5 else 'B'


def allocation(picked,equity,exposure,cash,existing_bands):
 """Rows pass cutoff, fixed score1, identity/MAX rules. Liquidity is diagnostic-only."""
 eq=D(str(equity));cash=D(str(cash));exposure=D(str(exposure))
 bands=list(existing_bands)+[band(r['capital_score']) for r in picked]
 assert bands and all(b in CAP for b in bands)
 best=min(bands,key=lambda b:('S','A','B').index(b))
 target=min(D('.92'),BASE[best]+D('.055')*(len(bands)-1))
 budget=min(cash,max(D(0),eq*target-exposure))
 weights=sum(D(str(r['capital_score'])) for r in picked)
 remaining=cash;unspent=budget;assigned=[]
 for r in picked:
  weight=D(str(r['capital_score']));bb=band(r['capital_score']);lot=D(r['raw_reference'])*BUY*100
  cap=eq*CAP[bb];desired=budget*weight/weights
  limit=min(desired,cap,remaining)
  lots=max(0,int((limit/lot).to_integral_value(rounding=ROUND_FLOOR)))
  debit=lots*lot;remaining-=debit;unspent-=debit
  assigned.append({'entry_id':r['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,
   'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'liquidity_cap':None,
   'desired':desired,'band':bb,'target_utilization':target,'batch_equity':eq,'batch_budget':budget})
 # Only initially funded candidates; fixed score-descending rounds of one lot.
 rounds=0
 while True:
  changed=False
  for a in assigned:
   if a['first_pass_quantity']<100:continue
   lot=a['lot_debit']
   if lot>remaining or lot>unspent or a['debit']+lot>a['equity_cap']:continue
   a['quantity']+=100;a['water_fill_lots']+=1;a['debit']+=lot
   remaining-=lot;unspent-=lot;changed=True
  if not changed:break
  rounds+=1
 assert all(a['quantity']%100==0 and a['debit']<=a['equity_cap'] for a in assigned)
 assert remaining>=0 and unspent>=0
 for a in assigned:a['water_fill_rounds']=rounds;a['budget_unspent']=unspent
 return assigned
