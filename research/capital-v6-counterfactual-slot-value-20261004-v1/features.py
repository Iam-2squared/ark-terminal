"""Causal slot features: explicit allowlist, no label/book/identity access."""
from statistics import mean
from decimal import Decimal
NUMERIC=['active_minute','active_minutes_remaining','m2','m3','m5','ML','batch_size','batch_order_index','minimum_lot_equity_ratio','cash_equity_ratio','open_count','free_slots']+[f'held_{field}_{stat}' for field in ('ML','m5','age') for stat in ('min','mean','max')]+[f'held_{rank}_count' for rank in ('S','A','B')]+[f'{kind}_last{window}' for kind in ('admitted','Aplus','B') for window in (15,30,60)]+['cumulative_admitted','cumulative_Aplus','minutes_since_admitted','minutes_since_Aplus','expected_remaining_Aplus','P_remaining_Aplus_ge1','P_remaining_Aplus_ge2','expected_remaining_admission_pass','B_median_ML','B_p75_ML']
CATEGORICAL=['rank']
def active(t):return t-540-min(60,max(0,t-690))
def make(row,positions,pending,cash,equity,history,batch_size,order_index,table):
 t=row['entry_minute'];held=list(positions.values())+pending;occ=len(held)
 x={'active_minute':active(t),'active_minutes_remaining':active(920)-active(t),'m2':row['m2'],'m3':row['m3'],'m5':row['m5'],'ML':row['ML'],'batch_size':batch_size,'batch_order_index':order_index,'minimum_lot_equity_ratio':float(Decimal(row['raw_reference'])*Decimal('1.0005')*100/Decimal(equity)),'cash_equity_ratio':float(Decimal(cash)/Decimal(equity)),'open_count':occ,'free_slots':3-occ}
 for field in ('ML','m5','age'):
  values=[active(t)-active(p['entry_minute']) if field=='age' else p[field] for p in held]
  for stat in ('min','mean','max'):x[f'held_{field}_{stat}']=(min(values) if stat=='min' else max(values) if stat=='max' else mean(values)) if values else None
 for rank in ('S','A','B'):x[f'held_{rank}_count']=sum(p['rank']==rank for p in held)
 for kind in ('admitted','Aplus','B'):
  hs=[r for r in history if r['admission'] and (kind=='admitted' or r['rank'] in ('S','A') if kind=='Aplus' else r['rank']=='B' if kind=='B' else True)]
  for window in (15,30,60):x[f'{kind}_last{window}']=sum(0<=active(t)-active(r['entry_minute'])<=window for r in hs)
  if kind in ('admitted','Aplus'):
   x[f'cumulative_{kind}']=len(hs);x[f'minutes_since_{kind}']=active(t)-active(hs[-1]['entry_minute']) if hs else None
 counts=table['minute_counts'][str(t)];n=table['training_session_N']
 x.update(expected_remaining_Aplus=counts[2]/n,P_remaining_Aplus_ge1=counts[0]/n,P_remaining_Aplus_ge2=counts[1]/n,expected_remaining_admission_pass=counts[3]/n,B_median_ML=table['B_median'],B_p75_ML=table['B_p75'])
 assert set(x)==set(NUMERIC) and len(held)<=3
 return {'numeric':x,'categorical':{'rank':row['rank']}}
