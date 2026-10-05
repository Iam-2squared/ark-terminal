"""Independent exact Fraction exposure joins; no Primary evaluator imports."""
from independent_engine import *
FINE=['<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10'];COARSE=['Weak','Low','Medium','Big','Mega']
def fine(x):return 'MISSING' if x is None else FINE[sum(x>=t for t in (.01,.02,.03,.04,.05,.10))]
def coarse(x):return 'MISSING' if x is None else COARSE[sum(x>=t for t in (.02,.03,.05,.10))]
def avg(x):return math.fsum(x)/len(x) if x else None
def aggregate(rr,total=None):
 n=len(rr);c=Counter(coarse(r['potential_return']) for r in rr);supported=sum(c[x] for x in COARSE);real=[r['realized_net_return'] for r in rr if r['realized_net_return'] is not None];pos=sum(x>0 for x in real);ge1=sum(x>=.01 for x in real);lose=sum(x<=0 for x in real);buy=sum((F(r['buy_debit']) for r in rr),F(0));pnl=sum((F(r['actual_PnL']) for r in rr if r['actual_PnL'] is not None),F(0));unit=sum((F(r['unit_100share_PnL']) for r in rr if r['unit_100share_PnL'] is not None),F(0));unknown=sum(r['actual_PnL'] is None for r in rr);lots=[r['lots'] for r in rr]
 return {'N':n,'supported_quality_N':supported,'Medium':c['Medium'],'U5':c['Big']+c['Mega'],'U10':c['Mega'],'Weak':c['Weak'],'Low':c['Low'],'Big':c['Big'],'Mega':c['Mega'],'U2':supported-c['Weak'],'U3':c['Medium']+c['Big']+c['Mega'],'below2_rate':c['Weak']/supported if supported else None,'below3_rate':(c['Weak']+c['Low'])/supported if supported else None,'realized_supported_N':len(real),'realized_missing_N':n-len(real),'realized_positive_N':pos,'realized_ge1pct_N':ge1,'realized_loser_le0_N':lose,'realized_positive_rate':pos/len(real) if real else None,'realized_ge1pct_rate':ge1/len(real) if real else None,'loser_rate':lose/len(real) if real else None,'realized_mean':avg(real),'realized_median':median(real) if real else None,'lots':sum(lots),'mean_lots':avg(lots),'median_lots':median(lots) if lots else None,'buy_notional':str(buy),'notional_share':float(buy/F(total)) if total and F(total)>0 else None,'actual_PnL':str(pnl) if unknown==0 else None,'resolved_actual_PnL':str(pnl),'unresolved_PnL_N':unknown,'unit_lot_PnL':str(unit),'return_on_deployed_notional':float(pnl/buy) if buy and unknown==0 else None,'scores':{f:{'mean':avg([r[f] for r in rr]),'median':median(r[f] for r in rr) if rr else None} for f in ('pP','q2','q3','mP','rM')},'Entry_hour_N':{str(h):sum(r['entry_minute']//60==h for r in rr) for h in range(9,16)},'slot_N':{str(s):sum(r['slot']==s for r in rr) for s in (1,2,3)}}
def compare(audit,name,actual,expected):
 if isinstance(expected,dict):
  for k,v in expected.items():
   if k=='exact_jst':continue
   if k not in actual:audit.check(name+'/'+k+'/exists',False);continue
   compare(audit,name+'/'+k,actual[k],v)
 elif isinstance(expected,list):
  audit.check(name+'/length',len(actual)==len(expected))
  for i,(a,b) in enumerate(zip(actual,expected)):compare(audit,name+'/'+str(i),a,b)
 elif isinstance(expected,bool) or expected is None:audit.check(name,actual==expected)
 elif isinstance(expected,float):audit.num(name,float(actual),expected)
 elif isinstance(expected,int):audit.check(name,actual==expected)
 elif isinstance(expected,str):
  try:audit.money(name,str(actual),expected)
  except (ValueError,ZeroDivisionError):audit.check(name,actual==expected)
 else:audit.check(name,actual==expected)
def exposures(rr):
 total=aggregate(rr)['buy_notional'];dec={str(k):[] for k in range(1,11)}
 for r in rr:
  index=min(9,int(r['rM']*10));dec[str(index+1)].append(r)
 return {'all':aggregate(rr,total),'MRET_percentile_decile':{k:aggregate(z,total) for k,z in dec.items()},'potential_bucket':{b:aggregate([r for r in rr if fine(r['potential_return'])==b],total) for b in FINE},'coarse_bucket':{b:aggregate([r for r in rr if coarse(r['potential_return'])==b],total) for b in COARSE},'rM_half':{h:aggregate([r for r in rr if (r['rM']<.5)==(h=='low')],total) for h in ('low','high')},'slot':{str(s):aggregate([r for r in rr if r['slot']==s],total) for s in (1,2,3)},'band':{b:aggregate([r for r in rr if r['band']==b],total) for b in BANDS[:3]},'Entry_hour':{str(h):aggregate([r for r in rr if r['entry_minute']//60==h],total) for h in range(9,16)},'notional_quality':{name:aggregate([r for r in rr if pred(r)],total) for name,pred in [('Weak',lambda r:r['potential_return']<.02),('Medium+',lambda r:r['potential_return']>=.03),('U5',lambda r:r['potential_return']>=.05),('U10',lambda r:r['potential_return']>=.10)]}}
def make_row(k,q,slot,rt,books,teacher,audit,saved_trade=None):
 r=rt[k];b=books[k];source=early(b) or late(b);buy=F(r['raw_reference'])*F(10005,10000);debit=buy*q
 if source:
  sell=source['price'];credit=sell*q;pnl=credit-debit;unit=(sell-buy)*100;real=float(sell/buy-1)
  if saved_trade:
   for f,v in [('debit',debit),('credit',credit),('pnl',pnl),('buy_effective',buy),('sell_effective',sell)]:audit.money(k+'/raw_execution/'+f,v,saved_trade[f])
   audit.check(k+'/raw_release',source['release']==saved_trade['release_minute']);audit.num(k+'/raw_return',real,saved_trade['net_return'])
 else:
  credit=pnl=unit=real=None;audit.check(k+'/unresolved_not_imputed',saved_trade is None)
 potential=teacher[k]['potential_return']
 return {f:r[f] for f in ('entry_id','session','symbol','entry_minute','band','pP','q2','q3','mP','rM')}|{'slot':slot,'potential_return':potential,'potential_bucket':fine(potential),'coarse_bucket':coarse(potential),'quantity':q,'lots':q//100,'buy_debit':str(debit),'sell_proceeds':str(credit) if credit is not None else None,'actual_PnL':str(pnl) if pnl is not None else None,'unit_100share_PnL':str(unit) if unit is not None else None,'realized_net_return':real,'evaluation_only':True}
def empty(k,rt,teacher,decision):
 r=rt[k];t=teacher[k];buy=t.get('buy_effective');sell=t.get('sell_effective');unit=(F(sell)-F(buy))*100 if buy and sell else None
 return {f:r[f] for f in ('entry_id','session','symbol','entry_minute','band','pP','q2','q3','mP','rM')}|{'slot':decision.get('funded_slot',0),'potential_return':t['potential_return'],'potential_bucket':fine(t['potential_return']),'coarse_bucket':coarse(t['potential_return']),'realized_net_return':t['realized_net_return'],'lots':0,'buy_debit':'0','actual_PnL':'0','unit_100share_PnL':str(unit) if unit is not None else None}
