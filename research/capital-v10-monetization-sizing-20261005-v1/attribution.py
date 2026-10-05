"""Read-only evaluation. Never imported by runtime, sizing or replay."""
from control import *
from decimal import Decimal as D
from fractions import Fraction as F
from collections import Counter,defaultdict
from statistics import mean,median,quantiles
import math
FINE=['<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10']
COARSE=['Weak','Low','Medium','Big','Mega']
def fine(x):return next((k for t,k in zip((.01,.02,.03,.04,.05,.10),FINE) if x<t),FINE[-1])
def coarse(x):return next((k for t,k in zip((.02,.03,.05,.10),COARSE) if x<t),COARSE[-1])
def qtile(a,p):
    if not a:return None
    x=sorted(a);i=(len(x)-1)*p;lo=int(i);hi=min(lo+1,len(x)-1);return x[lo]+(x[hi]-x[lo])*(i-lo)
def runtime():return {r['entry_id']:r for r in rows(PRIVATE/'CURRENT_SIZING_RUNTIME.jsonl.gz')}
def teachers():return {r['entry_id']:r for r in rows(MAIN/'inputs/evaluation/TEACHERS_EVALUATION.jsonl.gz')}
def profiles():
    v5=Path(read(WORK/'v5_saved_paths.json')['private'])
    return {'v5':(v5,'CAPITAL_MAX3_SLOT_RESERVE_V1'),'I2':(V9PRIVATE,I2)}
def funded(profile):
    folder,arm=profiles()[profile];ds={r['entry_id']:r for r in rows(folder/f'{arm}_DECISIONS.jsonl.gz')};rt=runtime();tt=teachers();out=[]
    for t in rows(folder/f'{arm}_TRADES.jsonl.gz'):
        k=t['entry_id'];r=rt[k];d=ds[k];u=(D(t['sell_effective'])-D(t['buy_effective']))*100
        assert D(t['pnl'])==u*(t['quantity']//100) and D(t['debit'])==D(t['buy_effective'])*t['quantity'];potential=tt[k]['potential_return']
        assert potential is not None
        out.append({'entry_id':k,'session':r['session'],'symbol':r['symbol'],'entry_minute':r['entry_minute'],'release_minute':t['release_minute'],'slot':d['funded_slot'],'band':r['band'],'original_band':d['band'],'pP':r['pP'],'q2':r['q2'],'q3':r['q3'],'consensus_minrank':r['consensus_weight'],'potential_bucket':fine(potential),'coarse_bucket':coarse(potential),'potential_return':potential,'realized_net_return':t['net_return'],'quantity':t['quantity'],'lots':t['quantity']//100,'buy_debit':t['debit'],'sell_proceeds':t['credit'],'actual_PnL':t['pnl'],'unit_100share_PnL':str(u),'buy_effective':t['buy_effective'],'sell_effective':t['sell_effective'],'evaluation_only':True})
    return out
def group(rr,total_notional=None):
    n=len(rr);real=[r['realized_net_return'] for r in rr];potential=[r['potential_return'] for r in rr];c=Counter(r['coarse_bucket'] for r in rr);pn=sum((D(r['actual_PnL']) for r in rr),D(0));buy=sum((D(r['buy_debit']) for r in rr),D(0));unit=sum((D(r['unit_100share_PnL']) for r in rr),D(0));ratio=[r['realized_net_return']/r['potential_return'] for r in rr if r['potential_return']>0]
    return {'N':n,'Medium':c['Medium'],'U5':c['Big']+c['Mega'],'U10':c['Mega'],'Weak':c['Weak'],'Low':c['Low'],'Big':c['Big'],'Mega':c['Mega'],'U2':n-c['Weak'],'U3':c['Medium']+c['Big']+c['Mega'],'below2_rate':c['Weak']/n if n else None,'below3_rate':(c['Weak']+c['Low'])/n if n else None,'realized_positive_N':sum(x>0 for x in real),'realized_ge1pct_N':sum(x>=.01 for x in real),'realized_loser_le0_N':sum(x<=0 for x in real),'realized_positive_rate':sum(x>0 for x in real)/n if n else None,'realized_ge1pct_rate':sum(x>=.01 for x in real)/n if n else None,'loser_rate':sum(x<=0 for x in real)/n if n else None,'realized_mean':mean(real) if n else None,'realized_median':median(real) if n else None,'potential_mean':mean(potential) if n else None,'giveback_mean':mean(r['potential_return']-r['realized_net_return'] for r in rr) if n else None,'giveback_median':median(r['potential_return']-r['realized_net_return'] for r in rr) if n else None,'monetization_ratio_potential_positive_N':len(ratio),'monetization_ratio_median':qtile(ratio,.5),'monetization_ratio_Q25':qtile(ratio,.25),'monetization_ratio_Q75':qtile(ratio,.75),'lots':sum(r['lots'] for r in rr),'mean_lots':mean(r['lots'] for r in rr) if n else None,'median_lots':median(r['lots'] for r in rr) if n else None,'buy_notional':str(buy),'notional_share':float(buy/D(total_notional)) if total_notional and D(total_notional)>0 else None,'actual_PnL':str(pn),'unit_lot_PnL':str(unit),'return_on_deployed_notional':float(pn/buy) if buy else None,'scores':{f:{'mean':mean(r[f] for r in rr) if n else None,'median':median(r[f] for r in rr) if n else None} for f in ('pP','q2','q3','consensus_minrank')},'Entry_hour_N':{str(h):sum(r['entry_minute']//60==h for r in rr) for h in range(9,16)},'slot_N':{str(s):sum(r['slot']==s for r in rr) for s in (1,2,3)}}
def identity():
    rr={p:funded(p) for p in profiles()};assert len(rr['v5'])==150 and len(rr['I2'])==161
    a,b=[{r['entry_id']:r for r in rr[p]} for p in ('v5','I2')];common=set(a)&set(b);onlya=set(a)-set(b);onlyb=set(b)-set(a);ledger=[];delta=D(0)
    for k in sorted(common):
        assert a[k]['unit_100share_PnL']==b[k]['unit_100share_PnL'];z=D(b[k]['unit_100share_PnL'])*((b[k]['quantity']-a[k]['quantity'])//100);delta+=z
        ledger.append({'entry_id':k,'group':'COMMON_FUNDED','q_v5':a[k]['quantity'],'q_I2':b[k]['quantity'],'quantity_delta':b[k]['quantity']-a[k]['quantity'],'unit_100share_PnL':b[k]['unit_100share_PnL'],'COMMON_QUANTITY_PNL_DELTA':str(z),'v5':a[k],'I2':b[k]})
    ledger += [{'entry_id':k,'group':'V5_ONLY_FUNDED','v5':a[k]} for k in sorted(onlya)]+[{'entry_id':k,'group':'I2_ONLY_FUNDED','I2':b[k]} for k in sorted(onlyb)]
    ga=group([a[k] for k in onlya]);gb=group([b[k] for k in onlyb]);totaldelta=D(group(rr['I2'])['actual_PnL'])-D(group(rr['v5'])['actual_PnL']);selection=D(gb['actual_PnL'])-D(ga['actual_PnL']);assert totaldelta==delta+selection
    for p in rr:gzsave(PRIVATE/f'{p}_MONETIZATION_TRADE_LEDGER.jsonl.gz',rr[p])
    gzsave(PRIVATE/'V5_I2_IDENTITY_QUANTITY_LEDGER.jsonl.gz',ledger)
    result={'exact_jst':now(),'COMMON_FUNDED':{'v5':group([a[k] for k in common]),'I2':group([b[k] for k in common]),'COMMON_QUANTITY_PNL_DELTA':str(delta)},'V5_ONLY_FUNDED':ga,'I2_ONLY_FUNDED':gb,'total_actual_PnL_delta_I2_minus_v5':str(totaldelta),'identity_side_actual_PnL_delta':str(selection),'exact_conservation':True,'unique_causal_decomposition_claim':False,'saved_control_replay':0}
    save(OUT/'V5_VS_I2_IDENTITY_QUANTITY_ATTRIBUTION.json',result);checkpoint('M3_V5_VS_I2_IDENTITY_QUANTITY_ATTRIBUTION',{'common_N':len(common),'v5_only_N':len(onlya),'I2_only_N':len(onlyb),'common_quantity_PnL_delta':str(delta)},'Potential/realized matrix without runtime feedback')
def matrix():
    out={}
    for p in profiles():
        rr=rows(PRIVATE/f'{p}_MONETIZATION_TRADE_LEDGER.jsonl.gz');total=sum((D(r['buy_debit']) for r in rr),D(0));out[p]={'all':group(rr,total),'fine':{b:group([r for r in rr if r['potential_bucket']==b],total) for b in FINE},'coarse':{b:group([r for r in rr if r['coarse_bucket']==b],total) for b in COARSE},'exposure':{b:group([r for r in rr if r['potential_return']>=t] if t is not None else [r for r in rr if r['potential_return']<.02],total) for b,t in [('Weak',None),('Medium+',.03),('U5',.05),('U10',.10)]}}
    save(OUT/'POTENTIAL_REALIZED_MONETIZATION_MATRIX.json',{'exact_jst':now(),'profiles':out,'potential_primary_realized_diagnostic':True,'monetization_ratio_mean_not_used':True});checkpoint('M4_POTENTIAL_REALIZED_MONETIZATION_MATRIX',{'profiles':list(out),'buckets':7},'Signal/realized diagnostics; fits0')
def rank(x):
    out=[0.]*len(x);ix=sorted(range(len(x)),key=lambda i:x[i]);lo=0
    while lo<len(ix):
        hi=lo+1
        while hi<len(ix) and x[ix[hi]]==x[ix[lo]]:hi+=1
        for j in ix[lo:hi]:out[j]=(lo+1+hi)/2
        lo=hi
    return out
def auc(score,y):
    p=sum(y);n=len(y)-p
    return (sum(r for r,z in zip(rank(score),y) if z)-p*(p+1)/2)/(p*n) if p and n else None
def correlation(x,y):
    x=rank(x);y=rank(y);a=mean(x);b=mean(y);den=math.sqrt(sum((v-a)**2 for v in x)*sum((v-b)**2 for v in y))
    return sum((v-a)*(w-b) for v,w in zip(x,y))/den if den else None
def signal():
    rt=runtime();tt=teachers();fundedrows=rows(PRIVATE/'I2_MONETIZATION_TRADE_LEDGER.jsonl.gz');admission=[r for r in rt.values() if r['band']!='P_BELOW' and r['entry_minute']<920];supported=[r|{'realized_net_return':tt[r['entry_id']]['realized_net_return'],'consensus_minrank':r['consensus_weight']} for r in admission if tt[r['entry_id']]['realized_net_return'] is not None];out={}
    for name,rr in [('I2_funded',fundedrows),('I2_rank_native_admission',supported)]:
        out[name]={'N':len(rr),'admission_identity_N':len(admission) if name.endswith('admission') else None,'unsupported_realized_N':len(admission)-len(supported) if name.endswith('admission') else 0,'scores':{}}
        for f in ('pP','q2','q3','consensus_minrank'):
            x=[r[f] for r in rr];y=[r['realized_net_return'] for r in rr];ordered=sorted(rr,key=lambda r:(r[f],r['entry_id']));bins={}
            for decile in range(10):
                z=[r for i,r in enumerate(ordered) if i*10//len(ordered)==decile];v=[r['realized_net_return'] for r in z];bins[str(decile+1)]={'N':len(z),'score_min':min(r[f] for r in z),'score_max':max(r[f] for r in z),'realized_mean':mean(v),'realized_median':median(v),'loser_rate':sum(t<=0 for t in v)/len(v)}
            out[name]['scores'][f]={'AUC_realized_gt0':auc(x,[z>0 for z in y]),'AUC_realized_ge1pct':auc(x,[z>=.01 for z in y]),'AUC_realized_le0':auc(x,[z<=0 for z in y]),'Spearman_realized_return':correlation(x,y),'deciles':bins}
    save(OUT/'SIGNAL_FROZEN_EXIT_MONETIZATION_DIAGNOSTIC.json',{'exact_jst':now(),'populations':out,'diagnostic_only':True,'model_fit':0,'runtime_feedback':False});checkpoint('M5_SIGNAL_MONETIZATION_DIAGNOSTIC',{'fits':0,'funded_N':len(fundedrows),'admission_supported_N':len(supported)},'Fixed-identity shadow / algebraic / static hindsight diagnostics')
if __name__=='__main__':
    import sys
    {'identity':identity,'matrix':matrix,'signal':signal}[sys.argv[1]]()
