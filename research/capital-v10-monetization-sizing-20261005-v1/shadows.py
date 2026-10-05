"""Fixed identity diagnostics only; no policy replay or feedback optimization."""
from control import *
from decimal import Decimal as D
from fractions import Fraction as F
from collections import defaultdict
from statistics import mean,median
import math
def algebra():
    rr=rows(PRIVATE/'I2_MONETIZATION_TRADE_LEDGER.jsonl.gz');out=[];a=F(0);e=F(0);c=F(0);unit=F(0)
    for day in read(SPLIT)['OOF38']:
        z=[r for r in rr if r['session']==day];n=len(z);lots=sum(r['lots'] for r in z);bar=F(lots,n) if n else F(0);actual=sum((r['lots']*F(r['unit_100share_PnL']) for r in z),F(0));u=sum((F(r['unit_100share_PnL']) for r in z),F(0));equal=bar*u;cov=sum(((r['lots']-bar)*F(r['unit_100share_PnL']) for r in z),F(0));assert actual==equal+cov
        a+=actual;e+=equal;c+=cov;unit+=u;out.append({'session':day,'funded_N':n,'total_lots':lots,'Lbar_fraction':str(bar),'actual_PnL_exact':str(actual),'equal_lot_algebraic_PnL_fraction':str(equal),'sizing_covariance_contribution_fraction':str(cov),'identity_unit_lot_edge_exact':str(u)})
    save(OUT/'SIZING_ALGEBRAIC_ATTRIBUTION.json',{'exact_jst':now(),'sessions':out,'totals':{'actual_PnL_exact':str(a),'equal_lot_algebraic_PnL_fraction':str(e),'sizing_covariance_contribution_fraction':str(c),'identity_unit_lot_edge_exact':str(unit),'actual_PnL_jpy':float(a),'equal_lot_algebraic_PnL_jpy':float(e),'sizing_covariance_contribution_jpy':float(c),'identity_unit_lot_edge_jpy':float(unit)},'exact_conservation':True,'fractional_equal_lot_not_executable':True,'evaluation_only':True})
def shadow():
    rr=rows(PRIVATE/'I2_MONETIZATION_TRADE_LEDGER.jsonl.gz');cash=D(1000000);cashmin=cash;daily=[];ledger=[];peak=0;violations=0
    for day in read(SPLIT)['OOF38']:
        z=[r for r in rr if r['session']==day];start=cash;buy=defaultdict(list);sell=defaultdict(list);hold=set()
        for r in z:buy[r['entry_minute']].append(r);sell[r['release_minute']].append(r)
        for t in range(540,932):
            for r in sorted(sell[t],key=lambda r:r['entry_id']):
                assert r['entry_id'] in hold;credit=D(r['sell_effective'])*100;cash+=credit;hold.remove(r['entry_id']);ledger.append({'session':day,'minute':t,'entry_id':r['entry_id'],'side':'SELL','quantity':100,'amount':str(credit),'cash':str(cash)})
            for r in sorted(buy[t],key=lambda r:(-r['pP'],r['entry_id'])):
                debit=D(r['buy_effective'])*100;assert debit<=D(r['buy_debit']) and debit<=cash;cash-=debit;cashmin=min(cashmin,cash);hold.add(r['entry_id']);peak=max(peak,len(hold));assert len(hold)<=3;ledger.append({'session':day,'minute':t,'entry_id':r['entry_id'],'side':'BUY','quantity':100,'amount':str(debit),'cash':str(cash)})
        assert not hold
        pnl=cash-start;daily.append({'session':day,'starting_cash':str(start),'ending_cash':str(cash),'PnL':str(pnl),'daily_return_based_on_1m':float(pnl/D(1000000)),'actual_shadow_chain_daily_return':float(cash/start-1)})
    rolling=[]
    for i in range(19):
        w=daily[i:i+20];rolling.append({'start_session':w[0]['session'],'end_session':w[-1]['session'],'actual_fixed_identity_chain_multiple':float(D(w[-1]['ending_cash'])/D(w[0]['starting_cash'])),'fixed_1m_additive_multiple':float(1+sum((D(r['PnL']) for r in w),D(0))/D(1000000))})
    mm=[r['actual_fixed_identity_chain_multiple'] for r in rolling];gzsave(PRIVATE/'I2_FIXED_100SHARE_SHADOW_LEDGER.jsonl.gz',ledger)
    save(OUT/'FIXED_IDENTITY_100SHARE_SHADOW.json',{'exact_jst':now(),'identity_N':len(rr),'quantity':100,'total_PnL':str(cash-D(1000000)),'Final38':str(cash),'cash_min':str(cashmin),'max_concurrent':peak,'violations':violations,'daily':daily,'rolling20':rolling,'rolling20_summary':{'min':min(mm),'mean':mean(mm),'median':median(mm),'max':max(mm),'2x_N':sum(x>=2 for x in mm)},'selection_only_shadow':True,'not_official_capital_benchmark_policy':True,'low_utilization':True})
def optimum(lot,unit,cap,budget):
    # Exact bounded integer enumeration; eliminate final variable analytically.
    n=len(lot);best=None;bestlots=None;cases=0
    def visit(i,cost,value,chosen):
        nonlocal best,bestlots,cases
        remminimum=sum(lot[i+1:],D(0));bound=min(int(cap[i]//lot[i]),int((budget-cost-remminimum)//lot[i]))
        if i==n-1:
            if bound<1:return
            choices=[bound] if unit[i]>0 else [1]
        else:choices=range(1,bound+1)
        for k in choices:
            total=value+k*unit[i];cc=cost+k*lot[i];zz=chosen+[k]
            if i<n-1:visit(i+1,cc,total,zz)
            else:
                cases+=1
                if best is None or total>best or (total==best and tuple(zz)<tuple(bestlots)):best,bestlots=total,zz
    visit(0,D(0),D(0),[]);assert best is not None
    return best,bestlots,cases
def hindsight():
    rr={r['entry_id']:r for r in rows(PRIVATE/'I2_MONETIZATION_TRADE_LEDGER.jsonl.gz')};ds=[r for r in rows(V9PRIVATE/f'{I2}_DECISIONS.jsonl.gz') if r['reason']=='FUNDED'];batches=defaultdict(list)
    for d in ds:batches[d['session'],d['minute']].append(d)
    out=[];actual=D(0);optimal=D(0)
    for (day,t),z in sorted(batches.items()):
        z.sort(key=lambda r:r['batch_index']);budget=D(z[0]['batch_budget']);assert all(D(r['batch_budget'])==budget for r in z)
        lot=[D(r['lot_debit']) for r in z];cap=[D(r['equity_cap']) for r in z];unit=[D(rr[r['entry_id']]['unit_100share_PnL']) for r in z];a=sum((D(rr[r['entry_id']]['actual_PnL']) for r in z),D(0));v,k,n=optimum(lot,unit,cap,budget);assert v>=a and sum((q*l for q,l in zip(k,lot)),D(0))<=budget
        actual+=a;optimal+=v;out.append({'session':day,'minute':t,'entry_ids':[r['entry_id'] for r in z],'saved_batch_equity':z[0]['batch_equity'],'saved_batch_budget':str(budget),'lot_debits':[str(x) for x in lot],'caps':[str(x) for x in cap],'realized_unit_PnL':[str(x) for x in unit],'actual_lots':[r['quantity']//100 for r in z],'optimal_lots':k,'actual_PnL':str(a),'hindsight_local_optimum_PnL':str(v),'headroom':str(v-a),'enumerated_terminal_cases':n})
    gzsave(PRIVATE/'STATIC_BATCH_HINDSIGHT_LEDGER.jsonl.gz',out)
    save(OUT/'STATIC_BATCH_HINDSIGHT_SIZING_DIAGNOSTIC.json',{'exact_jst':now(),'status':'HINDSIGHT_DIAGNOSTIC_ONLY','batch_N':len(out),'funded_identity_N':len(ds),'sum_actual_batch_PnL':str(actual),'sum_hindsight_local_optimum_PnL':str(optimal),'difference':str(optimal-actual),'future_realized_used':True,'runtime_feedback':False,'independent_solve_status':'PENDING','full_chain_oracle_claim':False,'rolling20_upper_bound_claim':False})
def main():
    algebra();shadow();hindsight();checkpoint('M6_SHADOW_AND_STATIC_HINDSIGHT_DIAGNOSTICS',{'fixed_shadow_identity_N':161,'static_hindsight':'evaluation-only, independent pending'},'At least55 canaries and independent pre-main sizing audit')
if __name__=='__main__':main()
