"""Outcome-blind finite A1/A2 policy and frozen v5 lot-waterfill semantics."""
from decimal import Decimal as D,ROUND_FLOOR
from fractions import Fraction
CAP={'P_HIGH':D('.45'),'P_MID':D('.35'),'P_BASE':D('.25')}
BASE={'P_HIGH':D('.68'),'P_MID':D('.56'),'P_BASE':D('.44')}
ARMS=['RANK_NATIVE_GREEDY_MAX3','RANK_NATIVE_LAST_SLOT_OPTION_MAX3']
def order(r):return (-r['pP'],r['entry_timestamp'],r['symbol'])
def gate(arm,r,occupancy,minute,table):
 assert arm in ARMS and 0<=occupancy<=3
 if occupancy==3:return False,'MAX3_FULL',{'occupancy':3,'future_better_N':None,'training_session_N':None,'P_future_better':None}
 if arm==ARMS[0] or occupancy<2:return True,'ACCEPT_NO_RESERVE',{'occupancy':occupancy,'future_better_N':None,'training_session_N':None,'P_future_better':None}
 assert table['train_N']==r['train_N']
 maxima=table['minutes'][str(minute)];n=len(maxima);better=sum(z is not None and z>r['rank_units'] for z in maxima)
 allowed=better*2<n
 return allowed,'ACCEPT_LAST_SLOT' if allowed else 'LAST_SLOT_RESERVE_REJECT',{'occupancy':occupancy,'future_better_N':better,'training_session_N':n,'P_future_better':better/n}
def allocation(picked,equity,exposure,cash,existing_bands):
 # Only band and weight changes; operations/order inherited exactly from v5.
 eq=D(str(equity));cash=D(str(cash));exposure=D(str(exposure))
 bands=list(existing_bands)+[r['band'] for r in picked];assert bands and all(b in CAP for b in bands)
 best=min(bands,key=lambda b:('P_HIGH','P_MID','P_BASE').index(b))
 target=min(D('.92'),BASE[best]+D('.055')*(len(bands)-1));budget=min(cash,max(D(0),eq*target-exposure))
 weights=sum(D(str(r['pP'])) for r in picked);remaining=cash;unspent=budget;assigned=[]
 for r in picked:
  weight=D(str(r['pP']));bb=r['band'];lot=D(r['raw_reference'])*D('1.0005')*100
  cap=eq*CAP[bb];desired=budget*weight/weights;limit=min(desired,cap,remaining)
  lots=max(0,int((limit/lot).to_integral_value(rounding=ROUND_FLOOR)));debit=lots*lot;remaining-=debit;unspent-=debit
  assigned.append({'entry_id':r['entry_id'],'quantity':lots*100,'first_pass_quantity':lots*100,'water_fill_lots':0,'debit':debit,'lot_debit':lot,'equity_cap':cap,'desired':desired,'band':bb,'target_utilization':target,'batch_equity':eq,'batch_budget':budget})
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
 for a in assigned:a['water_fill_rounds']=rounds;a['budget_unspent']=unspent
 return assigned
