"""Independent Fraction attribution/statistics/integer diagnostics; no Primary imports."""
from independent_engine import *
from itertools import product
FINE=['<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10'];COARSE=['Weak','Low','Medium','Big','Mega']
def avg(x):return math.fsum(x)/len(x) if x else None
def qt(x,p):
 if not x:return None
 s=sorted(x);j=(len(s)-1)*p;i=int(j);return (1-(j-i))*s[i]+(j-i)*s[min(i+1,len(s)-1)]
def fine(x):return FINE[sum(x>=t for t in (.01,.02,.03,.04,.05,.10))]
def coarse(x):return COARSE[sum(x>=t for t in (.02,.03,.05,.10))]
def aggregate(rr,total=None):
 n=len(rr);cc=Counter(coarse(r['potential_return']) for r in rr);real=[r['realized_net_return'] for r in rr];pot=[r['potential_return'] for r in rr];rat=[a/b for a,b in zip(real,pot) if b>0];buy=sum((F(r['buy_debit']) for r in rr),F(0));pnl=sum((F(r['actual_PnL']) for r in rr),F(0));unit=sum((F(r['unit_100share_PnL']) for r in rr),F(0));pos=sum(v>0 for v in real);ge1=sum(v>=.01 for v in real);loser=sum(v<=0 for v in real);lots=[r['lots'] for r in rr]
 return {'N':n,'Medium':cc['Medium'],'U5':cc['Big']+cc['Mega'],'U10':cc['Mega'],'Weak':cc['Weak'],'Low':cc['Low'],'Big':cc['Big'],'Mega':cc['Mega'],'U2':n-cc['Weak'],'U3':cc['Medium']+cc['Big']+cc['Mega'],'below2_rate':cc['Weak']/n if n else None,'below3_rate':(cc['Weak']+cc['Low'])/n if n else None,'realized_positive_N':pos,'realized_ge1pct_N':ge1,'realized_loser_le0_N':loser,'realized_positive_rate':pos/n if n else None,'realized_ge1pct_rate':ge1/n if n else None,'loser_rate':loser/n if n else None,'realized_mean':avg(real),'realized_median':median(real) if n else None,'potential_mean':avg(pot),'giveback_mean':avg([a-b for a,b in zip(pot,real)]),'giveback_median':median(a-b for a,b in zip(pot,real)) if n else None,'monetization_ratio_potential_positive_N':len(rat),'monetization_ratio_median':qt(rat,.5),'monetization_ratio_Q25':qt(rat,.25),'monetization_ratio_Q75':qt(rat,.75),'lots':sum(lots),'mean_lots':avg(lots),'median_lots':median(lots) if n else None,'buy_notional':str(buy),'notional_share':float(buy/F(total)) if total and F(total)>0 else None,'actual_PnL':str(pnl),'unit_lot_PnL':str(unit),'return_on_deployed_notional':float(pnl/buy) if buy else None,'scores':{f:{'mean':avg([r[f] for r in rr]),'median':median(r[f] for r in rr) if n else None} for f in ('pP','q2','q3','consensus_minrank')},'Entry_hour_N':{str(h):sum(r['entry_minute']//60==h for r in rr) for h in range(9,16)},'slot_N':{str(s):sum(r['slot']==s for r in rr) for s in (1,2,3)}}
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
def make_rows(folder,arm,rt,books,teachers,audit):
 ds={r['entry_id']:r for r in rows(folder/f'{arm}_DECISIONS.jsonl.gz')};out=[]
 for t in rows(folder/f'{arm}_TRADES.jsonl.gz'):
  k=t['entry_id'];r=rt[k];src=early(books[k]) or late(books[k]);buy=F(r['raw_reference'])*F(10005,10000);sell=src['price'];q=t['quantity'];debit=buy*q;credit=sell*q;pnl=credit-debit;unit=(sell-buy)*100
  for f,v in [('debit',debit),('credit',credit),('pnl',pnl),('buy_effective',buy),('sell_effective',sell)]:audit.money(arm+'/'+k+'/'+f,v,t[f])
  audit.check(arm+'/'+k+'/release',src['release']==t['release_minute']);audit.num(arm+'/'+k+'/return',float(sell/buy-1),t['net_return']);potential=teachers[k]['potential_return'];out.append({'entry_id':k,'session':r['session'],'symbol':r['symbol'],'entry_minute':r['entry_minute'],'release_minute':src['release'],'slot':ds[k]['funded_slot'],'band':r['band'],'pP':r['pP'],'q2':r['q2'],'q3':r['q3'],'consensus_minrank':r['consensus_weight'],'potential_return':potential,'potential_bucket':fine(potential),'coarse_bucket':coarse(potential),'realized_net_return':float(sell/buy-1),'quantity':q,'lots':q//100,'buy_debit':str(debit),'sell_proceeds':str(credit),'actual_PnL':str(pnl),'unit_100share_PnL':str(unit),'buy_effective':str(buy),'sell_effective':str(sell)})
 return out,ds
def identity_audit(rr,audit):
 a,b=[{r['entry_id']:r for r in rr[p]} for p in ('v5','I2')];common=set(a)&set(b);onlya=set(a)-set(b);onlyb=set(b)-set(a);dq=sum(((b[k]['quantity']-a[k]['quantity'])//100*F(b[k]['unit_100share_PnL']) for k in common),F(0));ga=aggregate([a[k] for k in onlya]);gb=aggregate([b[k] for k in onlyb]);selection=F(gb['actual_PnL'])-F(ga['actual_PnL']);total=F(aggregate(rr['I2'])['actual_PnL'])-F(aggregate(rr['v5'])['actual_PnL']);actual={'COMMON_FUNDED':{'v5':aggregate([a[k] for k in common]),'I2':aggregate([b[k] for k in common]),'COMMON_QUANTITY_PNL_DELTA':str(dq)},'V5_ONLY_FUNDED':ga,'I2_ONLY_FUNDED':gb,'identity_side_actual_PnL_delta':str(selection),'total_actual_PnL_delta_I2_minus_v5':str(total),'exact_conservation':total==dq+selection,'unique_causal_decomposition_claim':False,'saved_control_replay':0};compare(audit,'v5_I2_identity',actual,read(O/'V5_VS_I2_IDENTITY_QUANTITY_ATTRIBUTION.json'))
def matrix_audit(rr,audit):
 pp={}
 for p,z in rr.items():
  total=sum((F(r['buy_debit']) for r in z),F(0));pp[p]={'all':aggregate(z,total),'fine':{b:aggregate([r for r in z if fine(r['potential_return'])==b],total) for b in FINE},'coarse':{b:aggregate([r for r in z if coarse(r['potential_return'])==b],total) for b in COARSE},'exposure':{name:aggregate([r for r in z if r['potential_return']>=t] if t is not None else [r for r in z if r['potential_return']<.02],total) for name,t in [('Weak',None),('Medium+',.03),('U5',.05),('U10',.10)]}}
 compare(audit,'matrix',{'profiles':pp,'potential_primary_realized_diagnostic':True,'monetization_ratio_mean_not_used':True},read(O/'POTENTIAL_REALIZED_MONETIZATION_MATRIX.json'))
def signal_audit(rr,rt,teacher,audit):
 supported=[r|{'realized_net_return':teacher[r['entry_id']]['realized_net_return'],'consensus_minrank':r['consensus_weight']} for r in rt.values() if r['band']!='P_BELOW' and r['entry_minute']<920 and teacher[r['entry_id']]['realized_net_return'] is not None];admissionN=sum(r['band']!='P_BELOW' and r['entry_minute']<920 for r in rt.values());pp={}
 for name,z in [('I2_funded',rr['I2']),('I2_rank_native_admission',supported)]:
  pp[name]={'N':len(z),'admission_identity_N':admissionN if name.endswith('admission') else None,'unsupported_realized_N':admissionN-len(z) if name.endswith('admission') else 0,'scores':{}}
  for f in ('pP','q2','q3','consensus_minrank'):
   def auc(pred):
    pos=[r[f] for r in z if pred(r['realized_net_return'])];neg=[r[f] for r in z if not pred(r['realized_net_return'])];return sum((a>b)+.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg)) if pos and neg else None
   xx=[r[f] for r in z];yy=[r['realized_net_return'] for r in z]
   def ranks(x):return [1+sum(v<a for v in x)+(sum(v==a for v in x)-1)/2 for a in x]
   x=ranks(xx);y=ranks(yy);xm=avg(x);ym=avg(y);den=math.sqrt(math.fsum((v-xm)**2 for v in x)*math.fsum((v-ym)**2 for v in y));rho=math.fsum((v-xm)*(w-ym) for v,w in zip(x,y))/den if den else None;ordered=sorted(z,key=lambda r:(r[f],r['entry_id']));bins={}
   for k in range(10):
    vv=[r for i,r in enumerate(ordered) if i*10//len(ordered)==k];real=[r['realized_net_return'] for r in vv];bins[str(k+1)]={'N':len(vv),'score_min':min(r[f] for r in vv),'score_max':max(r[f] for r in vv),'realized_mean':avg(real),'realized_median':median(real),'loser_rate':sum(v<=0 for v in real)/len(real)}
   pp[name]['scores'][f]={'AUC_realized_gt0':auc(lambda x:x>0),'AUC_realized_ge1pct':auc(lambda x:x>=.01),'AUC_realized_le0':auc(lambda x:x<=0),'Spearman_realized_return':rho,'deciles':bins}
 compare(audit,'signal',{'populations':pp,'diagnostic_only':True,'model_fit':0,'runtime_feedback':False},read(O/'SIGNAL_FROZEN_EXIT_MONETIZATION_DIAGNOSTIC.json'))
def algebra_audit(rr,audit):
 saved=read(O/'SIZING_ALGEBRAIC_ATTRIBUTION.json');actual=F(0);equal=F(0);cov=F(0);unit=F(0)
 for day,z in zip(read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')['OOF38'],saved['sessions']):
  r=[r for r in rr if r['session']==day];n=len(r);lots=sum(r['lots'] for r in r);bar=F(lots,n) if n else F(0);a=sum((r['lots']*F(r['unit_100share_PnL']) for r in r),F(0));u=sum((F(r['unit_100share_PnL']) for r in r),F(0));e=bar*u;c=a-e;actual+=a;equal+=e;cov+=c;unit+=u
  compare(audit,'algebra/'+day,{'session':day,'funded_N':n,'total_lots':lots,'Lbar_fraction':str(bar),'actual_PnL_exact':str(a),'equal_lot_algebraic_PnL_fraction':str(e),'sizing_covariance_contribution_fraction':str(c),'identity_unit_lot_edge_exact':str(u)},z)
 totals={'actual_PnL_exact':str(actual),'equal_lot_algebraic_PnL_fraction':str(equal),'sizing_covariance_contribution_fraction':str(cov),'identity_unit_lot_edge_exact':str(unit),'actual_PnL_jpy':float(actual),'equal_lot_algebraic_PnL_jpy':float(equal),'sizing_covariance_contribution_jpy':float(cov),'identity_unit_lot_edge_jpy':float(unit)};compare(audit,'algebra/totals',totals,saved['totals']);audit.check('algebra/conservation',actual==equal+cov)
def shadow_audit(rr,audit):
 saved=read(O/'FIXED_IDENTITY_100SHARE_SHADOW.json');cash=F(1000000);minimum=cash;peak=0;daily=[]
 for s in saved['daily']:
  day=s['session'];start=cash;events=[]
  for r in rr:
   if r['session']==day:events.extend([(r['release_minute'],0,r['entry_id'],F(r['sell_effective'])*100),(r['entry_minute'],1,r['entry_id'],-F(r['buy_effective'])*100)])
  occupied=set()
  for t,side,k,value in sorted(events):
   if side==0:audit.check(k+'/shadow_sell_once',k in occupied);occupied.remove(k)
   else:audit.check(k+'/shadow_buy_once',k not in occupied);occupied.add(k)
   cash+=value;minimum=min(minimum,cash);peak=max(peak,len(occupied));audit.check(k+'/shadow_cash',cash>=0)
  pnl=cash-start;actual={'session':day,'starting_cash':str(start),'ending_cash':str(cash),'PnL':str(pnl),'daily_return_based_on_1m':float(pnl/F(1000000)),'actual_shadow_chain_daily_return':float(cash/start-1)};compare(audit,'shadow/'+day,actual,s);daily.append((start,cash,pnl));audit.check(day+'/shadow_closed',not occupied)
 compare(audit,'shadow/summary',{'identity_N':len(rr),'quantity':100,'total_PnL':str(cash-F(1000000)),'Final38':str(cash),'cash_min':str(minimum),'max_concurrent':peak,'violations':0,'selection_only_shadow':True,'not_official_capital_benchmark_policy':True,'low_utilization':True},{k:v for k,v in saved.items() if k not in ('exact_jst','daily','rolling20','rolling20_summary')})
 mm=[]
 for i,s in enumerate(saved['rolling20']):
  m=float(daily[i+19][1]/daily[i][0]);mm.append(m);audit.num('shadow/rolling_chain',m,s['actual_fixed_identity_chain_multiple']);audit.num('shadow/rolling1m',float(1+sum((d[2] for d in daily[i:i+20]),F(0))/F(1000000)),s['fixed_1m_additive_multiple'])
 compare(audit,'shadow/rolling_summary',{'min':min(mm),'mean':avg(mm),'median':median(mm),'max':max(mm),'2x_N':sum(x>=2 for x in mm)},saved['rolling20_summary'])
def hindsight_audit(audit):
 rows_=rows(P/'STATIC_BATCH_HINDSIGHT_LEDGER.jsonl.gz');total=F(0);actualtotal=F(0);checks=0
 for z in rows_:
  costs=list(map(F,z['lot_debits']));caps=list(map(F,z['caps']));unit=list(map(F,z['realized_unit_PnL']));budget=F(z['saved_batch_budget']);bounds=[int(c//l) for c,l in zip(caps,costs)];last=max(range(len(costs)),key=lambda i:bounds[i]);others=[i for i in range(len(costs)) if i!=last];best=None
  for values in product(*(range(1,bounds[i]+1) for i in others)):
   cost=sum((costs[i]*k for i,k in zip(others,values)),F(0));remaining=min(bounds[last],int((budget-cost)//costs[last]));checks+=1
   if remaining<1:continue
   k=remaining if unit[last]>0 else 1;val=sum((unit[i]*q for i,q in zip(others,values)),F(0))+k*unit[last]
   if best is None or val>best:best=val
  audit.check(str(z['entry_ids'])+'/integer_feasible',best is not None);audit.money(str(z['entry_ids'])+'/integer_optimum',best,z['hindsight_local_optimum_PnL']);actual=sum((u*l for u,l in zip(unit,z['actual_lots'])),F(0));audit.money(str(z['entry_ids'])+'/actual_batch',actual,z['actual_PnL']);audit.money(str(z['entry_ids'])+'/headroom',best-actual,z['headroom']);total+=best;actualtotal+=actual
 saved=read(O/'STATIC_BATCH_HINDSIGHT_SIZING_DIAGNOSTIC.json');audit.money('hindsight/total',total,saved['sum_hindsight_local_optimum_PnL']);audit.money('hindsight/actual',actualtotal,saved['sum_actual_batch_PnL']);audit.money('hindsight/difference',total-actualtotal,saved['difference']);return {'batch_N':len(rows_),'independent_exact_integer_cases':checks,'independent_optimum_PnL_fraction':str(total),'mismatch_N':0 if not audit.mismatches else len(audit.mismatches),'runtime_feedback':False}
