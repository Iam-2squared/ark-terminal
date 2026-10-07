"""Accounting diagnostics after sealed portfolio paths; no runtime policy inputs."""
from io_utils import *
import collections
from statistics import median

BANDS=['L5_PLUS','L4_5','L3_4','L2_3','L1_2','L0_1','ZERO','P0_1','P1_2','P2_3','P3_4','P4_5','P5_PLUS','R_UNKNOWN']
def path(w,a,base=PRI/'runs'):
 p=base/w/a
 if not (p/'RESULT.json').exists():return None
 return {'result':json.loads((p/'RESULT.json').read_text()),**{n:rows(p/(n+'.jsonl.gz')) for n in ['DECISIONS','TRADES','CURVE','INTENTS']}}
def stats(v):
 if not v:return {k:None for k in ['min','mean','median','max']}
 return {k:fmt(x) for k,x in [('min',min(v)),('mean',sum(v,D(0))/len(v)),('median',median(v)),('max',max(v))]}
def dd(values):
 peak=D(1000000);worst=D(0)
 for v in values:
  peak=max(peak,v);worst=max(worst,(peak-v)/peak)
 return worst*100
def enriched(data):
 trades={t['entry_id']:dict(t) for t in data['TRADES']};funded=[]
 for d in data['DECISIONS']:
  if d['reason']!='FUNDED':continue
  t=trades.get(d['entry_id']);r=native_pct(D(t['pnl']),D(t['debit'])) if t else None
  funded.append({'entry_id':d['entry_id'],'session':d['session'],'quantity':d['quantity'],'entry_minute':d['minute'],'debit':D(d['debit']),'R':r,'bucket':bucket(r),'trade':t,'pnl':D(t['pnl']) if t else None,'cash_minutes':D(t['debit'])*(t['release_minute']-t['entry_minute']) if t else None})
 return funded
def loss_metrics(data,funded):
 known=[r for r in funded if r['R'] is not None];minus=[r for r in known if r['R']<0]
 vals=[D(d['ending_cash'])-D(d['starting_cash']) for d in data['result']['daily_series'] if d['status']=='COMPLETE']
 metric={'funded_N':len(funded),'known_R_N':len(known),'unknown_R_N':len(funded)-len(known),'ALL_MINUS_N':len(minus),'ALL_MINUS_pct_funded':fmt(F(len(minus))*100/len(funded)) if funded else None,'gross_loss_jpy':fmt(-sum((r['pnl'] for r in minus),D(0))),'gross_positive_jpy':fmt(sum((r['pnl'] for r in known if r['pnl']>0),D(0))),'realized_PnL_jpy':fmt(sum((r['pnl'] for r in known),D(0))),'worst_trade_loss_jpy':fmt(-min([r['pnl'] for r in minus],default=D(0))),'worst_trade_R_pct':fmt(min([r['R'] for r in known],default=None)),'negative_day_N':sum(v<0 for v in vals),'worst_daily_PnL_jpy':fmt(min(vals)) if vals else None,'minute_MTM_MaxDD_pct':fmt(dd([D(c['equity']) for c in data['CURVE']])),'EOD_MaxDD_pct':fmt(dd([D(d['ending_cash']) for d in data['result']['daily_series'] if d['status']=='COMPLETE']))}
 for k in range(1,6):
  l=[r for r in known if r['R']<=-k];p=[r for r in known if r['R']>=k]
  metric.update({f'R_LE_MINUS{k}_N':len(l),f'R_LE_MINUS{k}_gross_loss_jpy':fmt(-sum((r['pnl'] for r in l),D(0))),f'R_GE_PLUS{k}_N':len(p),f'R_GE_PLUS{k}_PnL_jpy':fmt(sum((r['pnl'] for r in p),D(0)))})
 return metric
def spectrum(w,a,funded):
 known=[r for r in funded if r['R'] is not None];out=[]
 for b in BANDS:
  r=[r for r in funded if r['bucket']==b];k=[x for x in r if x['R'] is not None]
  out.append({'window_id':w,'arm':a,'count_scope':'OVERLAPPING_PORTFOLIO_TRADES_WITHIN_WINDOW','band':b,'funded_N':len(r),'pct_known_R':fmt(F(len(k))*100/len(known)) if known else None,'pct_all_funded':fmt(F(len(r))*100/len(funded)) if funded else None,'quantity':sum(x['quantity'] for x in r),'lots':sum(x['quantity'] for x in r)//100,'BUY_debit_jpy':fmt(sum((x['debit'] for x in r),D(0))),'realized_PnL_jpy':fmt(sum((x['pnl'] for x in k),D(0))) if k or not r else None,'positive_PnL_jpy':fmt(sum((x['pnl'] for x in k if x['pnl']>0),D(0))),'negative_PnL_abs_jpy':fmt(-sum((x['pnl'] for x in k if x['pnl']<0),D(0))),'R_median_pct':fmt(median([x['R'] for x in k])) if k else None,'pp_sum_auxiliary_only':fmt(sum((x['R'] for x in k),F(0))) if k or not r else None,'capital_lock_jpy_minutes':fmt(sum((x['cash_minutes'] for x in k),D(0))) if k or not r else None})
 return out
def transition(w,fc,fe):
 c={r['entry_id']:r for r in fc};e={r['entry_id']:r for r in fe};out=[];decomp=[];tail=[]
 for key,r in sorted(c.items()):
  s=e.get(key);diff=s['R']-r['R'] if s and s['R'] is not None and r['R'] is not None else None
  out.append({'window_id':w,'entry_id':key,'session':r['session'],'C_fixed_band':r['bucket'],'C_R_pct':fmt(r['R']),'E_purchased':s is not None,'E_R_pct':fmt(s['R']) if s else None,'same_ID_EXIT_effect':'E_NOT_PURCHASED' if not s else 'R_UNKNOWN' if diff is None else 'IMPROVED' if diff>0 else 'EQUAL' if diff==0 else 'WORSENED','R_damage_even_if_band_retained':diff is not None and diff<0,'C_positive_E_negative':bool(r['R'] is not None and r['R']>0 and s and s['R'] is not None and s['R']<0),'C_quantity':r['quantity'],'E_quantity':s['quantity'] if s else 0,'C_PnL_jpy':fmt(r['pnl']),'E_PnL_jpy':fmt(s['pnl']) if s else None,'funding_set':'COMMON' if s else 'C_ONLY','C_fixed_winner':r['R'] is not None and r['R']>0,'C_fixed_loser':r['R'] is not None and r['R']<0,**{f'C_tail_LE_MINUS{k}_E_escape':bool(r['R'] is not None and r['R']<=-k and s and s['R'] is not None and s['R']>-k) for k in range(1,6)}})
 for key in sorted(set(c)|set(e)):
  cr=c.get(key);er=e.get(key);common=cr is not None and er is not None
  direct=qty=None
  if common and cr['trade'] and er['trade']:
   assert D(cr['trade']['buy_effective'])==D(er['trade']['buy_effective']),key
   uc=D(cr['trade']['sell_effective'])-D(cr['trade']['buy_effective']);ue=D(er['trade']['sell_effective'])-D(er['trade']['buy_effective'])
   direct=cr['quantity']*(ue-uc);qty=(er['quantity']-cr['quantity'])*ue
   assert direct+qty==er['pnl']-cr['pnl']
  delta=er['pnl']-cr['pnl'] if common and cr['pnl'] is not None and er['pnl'] is not None else er['pnl'] if er and not cr else -cr['pnl'] if cr and not er and cr['pnl'] is not None else None
  decomp.append({'window_id':w,'entry_id':key,'set':'COMMON' if common else 'C_ONLY' if cr else 'E_ONLY','C_quantity':cr['quantity'] if cr else 0,'E_quantity':er['quantity'] if er else 0,'COMMON_direct_EXIT_jpy':fmt(direct),'COMMON_quantity_jpy':fmt(qty),'E_ONLY_PnL_jpy':fmt(er['pnl']) if er and not cr else None,'C_ONLY_PnL_jpy':fmt(cr['pnl']) if cr and not er else None,'paired_PnL_delta_jpy':fmt(delta),'R_C_pct':fmt(cr['R']) if cr else None,'R_E_pct':fmt(er['R']) if er else None})
  if er and er['R'] is not None:
   for k in [1,2,3,4,5]:
    if er['R']<=-k and (cr is None or cr['R'] is not None and cr['R']>-k):tail.append({'window_id':w,'entry_id':key,'session':er['session'],'tail_threshold':-k,'set':'E_ONLY' if cr is None else 'COMMON_C_OUTSIDE_TAIL','E_R_pct':fmt(er['R']),'E_PnL_jpy':fmt(er['pnl']),'C_R_pct':fmt(cr['R']) if cr else None})
 return out,decomp,tail

def analyze_primary():
 planned=json.loads((ROOT/'inputs/S6_COVERAGE_AND_WINDOWS.json').read_text())['windows'];table=[];spectra=[];loss=[];trans=[];decomps=[];tails=[];decomp_window=[];state=[];unknown=[];unique={'C':set(),'E':set()};all_funded={'C':0,'E':0}
 plans={r['entry_id']:r['plan'] for r in rows(PRI/'immutable/EXIT_PLANS.jsonl.gz')} if (PRI/'immutable/EXIT_PLANS.jsonl.gz').exists() else {}
 for w in planned:
  wi=w['window_id'];rec={'window_id':wi,'start_session':w['start_session'],'end_session':w['end_session'],'business_day_N':20,'calendar_span_inclusive_days':(__import__('datetime').date.fromisoformat(w['end_session'])-__import__('datetime').date.fromisoformat(w['start_session'])).days+1,'coverage_status':'SOURCE_FIXED_COVERAGE_COMPLETE' if w['coverage_complete'] else 'OLD_COVERAGE_UNKNOWN','initial_cash_jpy':'1000000'}
  pair={a:path(wi,a) for a in ['C','E']};funded={}
  for a in ['C','E']:
   p=pair[a];rec[a+'_status']=p['result']['status'] if p else 'NOT_STARTED' if w['coverage_complete'] else 'UNMEASURED_OLD_COVERAGE'
   for key in ['final_equity','profit','return_pct','unsettled_N','funded_N','SHARP_DROP_intent_N','SHARP_DROP_fill_N']:rec[a+'_'+key]=p['result'][key] if p else None
   final=D(p['result']['final_equity']) if p and p['result']['final_equity'] is not None else None
   rec[a+'_deficit']=final<D(1000000) if final is not None else None;rec[a+'_hit_2m']=final>=D(2000000) if final is not None else None
   if p:
    ff=enriched(p);funded[a]=ff;met=loss_metrics(p,ff);loss.append({'window_id':wi,'arm':a,'result_status':p['result']['status'],**met});rec[a+'_minute_MTM_MaxDD_pct']=met['minute_MTM_MaxDD_pct'];rec[a+'_EOD_MaxDD_pct']=met['EOD_MaxDD_pct'];spectra+=spectrum(wi,a,ff)
    unique[a]|={r['entry_id'] for r in ff};all_funded[a]+=len(ff)
    covered=[plans.get(r['entry_id'],{}) for r in ff];s={'window_id':wi,'arm':a,'funded_N':len(ff),'State_source_ID_covered_N':sum(r['entry_id'] in plans for r in ff),'checkpoint_N':sum(x.get('checkpoint_N',0) for x in covered),'usable_checkpoint_N':sum(x.get('usable_checkpoint_N',0) for x in covered),'State_gap_funded_N':sum(x.get('action')=='EVIDENCE_GAP' for x in covered),'State_kernel_runs':0,'historical_receive_time':'UNKNOWN'};state.append(s);rec[a+'_State_source_covered_N']=s['State_source_ID_covered_N']
    for d in p['result']['daily_series']:
     for b in d['blockers']:unknown.append({'window_id':wi,'arm':a,'session':d['session'],**b})
  both=all(pair[a] and pair[a]['result']['status']=='COMPLETE' for a in ['C','E']);rec['paired_complete']=both
  rec['E_minus_C_final_equity_jpy']=fmt(D(rec['E_final_equity'])-D(rec['C_final_equity'])) if both else None
  if all(a in funded for a in ['C','E']):
   t,dc,tt=transition(wi,funded['C'],funded['E']);trans+=t;decomps+=dc;tails+=tt
   common_direct=sum((D(x['COMMON_direct_EXIT_jpy']) for x in dc if x['COMMON_direct_EXIT_jpy'] is not None),D(0));common_quantity=sum((D(x['COMMON_quantity_jpy']) for x in dc if x['COMMON_quantity_jpy'] is not None),D(0));onlyE=sum((D(x['E_ONLY_PnL_jpy']) for x in dc if x['E_ONLY_PnL_jpy'] is not None),D(0));onlyC=sum((D(x['C_ONLY_PnL_jpy']) for x in dc if x['C_ONLY_PnL_jpy'] is not None),D(0));total=common_direct+common_quantity+onlyE-onlyC
   decomp_window.append({'window_id':wi,'eligible_exact_identity':both,'COMMON_N':sum(x['set']=='COMMON' for x in dc),'C_ONLY_N':sum(x['set']=='C_ONLY' for x in dc),'E_ONLY_N':sum(x['set']=='E_ONLY' for x in dc),'COMMON_direct_EXIT_jpy':fmt(common_direct),'COMMON_quantity_jpy':fmt(common_quantity),'E_ONLY_PnL_jpy':fmt(onlyE),'C_ONLY_PnL_jpy':fmt(onlyC),'decomposed_delta_jpy':fmt(total) if both else None,'actual_final_delta_jpy':rec['E_minus_C_final_equity_jpy'],'exact_match':total==D(rec['E_minus_C_final_equity_jpy']) if both else None})
   if both:assert total==D(rec['E_minus_C_final_equity_jpy']),wi
  table.append(rec)
 complete=[r for r in table if r['paired_complete']];summary={'planned21':21,'fixed_primary9':9,'C_complete':sum(r['C_status']=='COMPLETE' for r in table),'E_complete':sum(r['E_status']=='COMPLETE' for r in table),'both_complete':len(complete),'unknown_fixed9':9-len(complete),'old_coverage_unknown12':12,'mask':[r['window_id'] for r in complete],'overlapping_windows_not_independent_months':True,'initial_cash':'1000000'}
 for a in ['C','E']:
  amounts=[D(r[a+'_final_equity']) for r in complete];profits=[v-D(1000000) for v in amounts];summary[a+'_final_equity_stats']=stats(amounts);summary[a+'_profit_stats']=stats(profits);summary[a+'_deficit_windows']=sum(v<D(1000000) for v in amounts);summary[a+'_hit_2m_windows']=sum(v>=D(2000000) for v in amounts);summary[a+'_worst_window_loss_jpy']=fmt(max([D(1000000)-v for v in amounts]+[D(0)]));summary[a+'_unique_market_Entry_N']=len(unique[a]);summary[a+'_overlapping_account_trade_N']=all_funded[a]
  lm=[r for r in loss if r['arm']==a and r['window_id'] in summary['mask']];summary[a+'_gross_loss_jpy_overlapping_accounts']=fmt(sum((D(r['gross_loss_jpy']) for r in lm),D(0)));summary[a+'_gross_positive_jpy_overlapping_accounts']=fmt(sum((D(r['gross_positive_jpy']) for r in lm),D(0)));summary[a+'_ALL_MINUS_N_overlapping_accounts']=sum(r['ALL_MINUS_N'] for r in lm);summary[a+'_negative_day_N_overlapping_accounts']=sum(r['negative_day_N'] for r in lm);summary[a+'_worst_daily_PnL_jpy']=min([D(r['worst_daily_PnL_jpy']) for r in lm],default=None);summary[a+'_max_minute_MTM_MaxDD_pct']=max([D(r['minute_MTM_MaxDD_pct']) for r in lm],default=None)
  for k in [3,4,5]:summary[a+'_tail_LE_MINUS'+str(k)+'_N']=sum(r['R_LE_MINUS'+str(k)+'_N'] for r in lm);summary[a+'_tail_LE_MINUS'+str(k)+'_gross_loss_jpy']=fmt(sum((D(r['R_LE_MINUS'+str(k)+'_gross_loss_jpy']) for r in lm),D(0)))
  summary[a+'_worst_daily_PnL_jpy']=fmt(summary[a+'_worst_daily_PnL_jpy']);summary[a+'_max_minute_MTM_MaxDD_pct']=fmt(summary[a+'_max_minute_MTM_MaxDD_pct'])
 delta=[D(r['E_minus_C_final_equity_jpy']) for r in complete];summary['paired_delta_stats']=stats(delta);summary['difference_of_medians_jpy']=fmt(median([D(r['E_final_equity']) for r in complete])-median([D(r['C_final_equity']) for r in complete])) if complete else None;summary['median_of_paired_differences_jpy']=fmt(median(delta)) if delta else None;summary['improved_N']=sum(x>0 for x in delta);summary['equal_N']=sum(x==0 for x in delta);summary['worsened_N']=sum(x<0 for x in delta)
 csvsave(PUB/'RESET20_WINDOW_RESULTS.csv',table);save(PUB/'RESET20_SUMMARY.json',summary);csvsave(PUB/'RETURN_SPECTRUM_BY_WINDOW.csv',spectra);csvsave(PUB/'TAIL_AND_LOSS_METRICS.csv',loss);csvsave(PRI/'ORIGINAL_C_WINNER_LOSER_TRANSITIONS.csv',trans);csvsave(PRI/'FUNDING_AND_PNL_DECOMPOSITION.csv',decomps);csvsave(PRI/'NEW_TAIL_ENTRANTS.csv',tails);csvsave(PUB/'FUNDING_AND_PNL_DECOMPOSITION.csv',decomp_window)
 aggregate=[]
 for w in sorted({r['window_id'] for r in trans}):
  for b in BANDS:
   rr=[r for r in trans if r['window_id']==w and r['C_fixed_band']==b]
   aggregate.append({'window_id':w,'C_fixed_band':b,'C_N':len(rr),'E_purchased_N':sum(r['E_purchased'] for r in rr),'E_not_purchased_N':sum(not r['E_purchased'] for r in rr),'improved_N':sum(r['same_ID_EXIT_effect']=='IMPROVED' for r in rr),'equal_N':sum(r['same_ID_EXIT_effect']=='EQUAL' for r in rr),'worsened_N':sum(r['same_ID_EXIT_effect']=='WORSENED' for r in rr),'positive_to_negative_N':sum(r['C_positive_E_negative'] for r in rr),'R_unknown_N':sum(r['same_ID_EXIT_effect']=='R_UNKNOWN' for r in rr),'worsened_even_if_band_retained_counted':True})
 csvsave(PUB/'ORIGINAL_C_WINNER_LOSER_TRANSITIONS.csv',aggregate);save(PUB/'STATE_EVIDENCE_COVERAGE.json',{'per_window':state,'cache_binding':json.loads((PUB/'STATE_CACHE_BINDING.json').read_text()),'quality_B_not_imputed_from_evidence_C':True});save(PRI/'UNRESOLVED_LEDGER.json',unknown);save(PUB/'UNRESOLVED_LEDGER.json',{'unresolved_N':len(unknown),'affected_windows':sorted({r['window_id'] for r in unknown}),'old_coverage_blocked_windows':['W%02d'%i for i in range(1,13)],'old_coverage_blocked_sessions':['2025-07-11','2025-07-14'],'fixed9_not_started_or_blocked':[r['window_id'] for r in table if r['window_id'] in ['W%02d'%i for i in range(13,22)] and not r['paired_complete']]});save(PRI/'UNIQUE_FUNDED_ID_LISTS.json',{a:sorted(unique[a]) for a in ['C','E']})
 return summary
if __name__=='__main__':print(json.dumps(analyze_primary(),ensure_ascii=False))
