"""Capital outcomes only, after both finite Main chains. Frozen signal metrics reused."""
from control import *
from attribution import group,exposure,fine,coarse,decile
from decimal import Decimal as D
from collections import Counter
SPEC=read(PARENT/'M1_M2_CAPITAL_POLICY_PRECOMMIT.json')
def gates(q,integrity):
    a=SPEC['quality_retention'];b=SPEC['secondary_v5_floor']
    g={'Q1':q['U5']>=a['U5_min'],'Q2':q['U10']>=a['U10_min'],'Q3':q['Medium']>=a['Medium_min'],'Q4':q['below2_rate']<=a['weak_rate_max'],'Q5':q['below3_rate']<=a['below3_rate_max'],'Q6':all(v==0 for v in integrity.values()),'Q7':'PENDING'}
    floor={'U5':q['U5']>=b['U5_min'],'U10':q['U10']>=b['U10_min'],'Medium':q['Medium']>=b['Medium_min'],'Weak':q['below2_rate']<=b['weak_rate_max'],'below3':q['below3_rate']<=b['below3_rate_max']}
    return g,floor
def empty(r,t,d):
    buy=t.get('buy_effective');sell=t.get('sell_effective');u=str((D(sell)-D(buy))*100) if buy and sell else None
    return {k:r[k] for k in ('entry_id','session','symbol','entry_minute','band','pP','q2','q3','mP','rM')}|{'slot':d.get('funded_slot',0),'potential_return':t['potential_return'],'potential_bucket':fine(t['potential_return']),'coarse_bucket':coarse(t['potential_return']),'realized_net_return':t['realized_net_return'],'quantity':0,'lots':0,'buy_debit':'0','sell_proceeds':'0','actual_PnL':'0','unit_100share_PnL':u,'evaluation_only':True}
def quality():
    assert read(OUT/'MAIN_REPLAY_RESULT.json')['primary_replays']==2
    rt={r['entry_id']:r for r in rows(PRIVATE/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz')};tt={r['entry_id']:r for r in rows(MAIN/'inputs/evaluation/TEACHERS_EVALUATION.jsonl.gz')};mask={r['entry_id'] for r in rows(MAIN/'private/COMMON_EVAL_MASK.jsonl.gz') if r['included']};bd={r['entry_id']:r for r in rows(V9/f'private/{I2}_DECISIONS.jsonl.gz')};saved={p:[dict(r,mP=rt[r['entry_id']]['mP'],rM=rt[r['entry_id']]['rM']) for r in rows(V10/f'private/{p}_MONETIZATION_TRADE_LEDGER.jsonl.gz')] for p in ('v5','I2')};base={r['entry_id']:r for r in saved['I2']};profiles={};exposures={p:exposure(v) for p,v in saved.items()};pairs={};outcomes=[]
    for arm in ARMS:
        ds=rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz');dm={r['entry_id']:r for r in ds};tr=rows(PRIVATE/f'{arm}_TRADES.jsonl.gz');curves=rows(PRIVATE/f'{arm}_CURVE.jsonl.gz');result=read(OUT/f'{arm}_RESULT.json');rr=[]
        for t in tr:
            k=t['entry_id'];r=empty(rt[k],tt[k],dm[k]);assert k in mask and r['potential_return'] is not None
            r.update(quantity=t['quantity'],lots=t['quantity']//100,buy_debit=t['debit'],sell_proceeds=t['credit'],actual_PnL=t['pnl'],realized_net_return=t['net_return'],unit_100share_PnL=str((D(t['sell_effective'])-D(t['buy_effective']))*100));rr.append(r)
        gzsave(PRIVATE/f'{arm}_MONETIZATION_TRADE_LEDGER.jsonl.gz',rr);q=group(rr);new={r['entry_id']:r for r in rr};common=set(new)&set(base);gained=[new[k] for k in sorted(set(new)-set(base))];lost=[base[k] for k in sorted(set(base)-set(new))];quantity=[];qd=D(0)
        for k in sorted(common):
            a=base[k];z=new[k];assert D(a['unit_100share_PnL'])==D(z['unit_100share_PnL']);delta=z['quantity']-a['quantity'];pnl=D(z['unit_100share_PnL'])*(delta//100);qd+=pnl
            quantity.append({'entry_id':k,'quantity_I2':a['quantity'],'quantity_new':z['quantity'],'quantity_delta':delta,'lots_delta':delta//100,'buy_notional_delta':str(D(z['buy_debit'])-D(a['buy_debit'])),'actual_PnL_delta':str(pnl),'potential_bucket':z['potential_bucket'],'coarse_bucket':z['coarse_bucket'],'rM':z['rM'],'realized_net_return':z['realized_net_return']})
        gzsave(PRIVATE/f'{arm}_COMMON_QUANTITY_DELTA.jsonl.gz',quantity)
        gm=group(gained);lm=group(lost);delta=D(q['actual_PnL'])-D(group(saved['I2'])['actual_PnL']);assert delta==qd+D(gm['actual_PnL'])-D(lm['actual_PnL'])
        changes={name:group(v) for name,v in [('NEW_MAX3_MISS_vs_I2',[empty(rt[k],tt[k],d) for k,d in dm.items() if d['reason']=='MAX3_FULL' and bd[k]['reason']!='MAX3_FULL']),('CASH_RECOVERY_vs_I2',[r for r in rr if bd[r['entry_id']]['reason']=='CASH_OR_LOT']),('NEW_CASH_MISS_vs_I2',[empty(rt[k],tt[k],d) for k,d in dm.items() if d['reason']=='CASH_OR_LOT' and bd[k]['reason']!='CASH_OR_LOT'])]}
        qtygroups={name:{'N':len(z),'quantity_delta':sum(r['quantity_delta'] for r in z),'lots_delta':sum(r['lots_delta'] for r in z),'buy_notional_delta':str(sum((D(r['buy_notional_delta']) for r in z),D(0))),'actual_PnL_delta':str(sum((D(r['actual_PnL_delta']) for r in z),D(0)))} for name,z in [(name,[r for r in quantity if pred(r)]) for name,pred in [('Weak',lambda r:r['coarse_bucket']=='Weak'),('Low',lambda r:r['coarse_bucket']=='Low'),('Medium',lambda r:r['coarse_bucket']=='Medium'),('Big',lambda r:r['coarse_bucket']=='Big'),('Mega',lambda r:r['coarse_bucket']=='Mega'),('U5',lambda r:r['coarse_bucket'] in ('Big','Mega')),('U10',lambda r:r['coarse_bucket']=='Mega'),('realized_positive',lambda r:r['realized_net_return']>0),('realized_ge1',lambda r:r['realized_net_return']>=.01),('loser',lambda r:r['realized_net_return']<=0),('low_rM',lambda r:r['rM']<.5),('high_rM',lambda r:r['rM']>=.5)]]}
        cap0=sum(d.get('cap_hit',False) for d in bd.values() if d['reason']=='FUNDED');cap1=sum(d.get('cap_hit',False) for d in ds if d['reason']=='FUNDED')
        pairs[arm]={'COMMON_FUNDED':{'N':len(common),'actual_PnL_quantity_delta':str(qd),'quantity_groups':qtygroups},'GAINED_FUNDING_vs_I2':gm,'LOST_FUNDING_vs_I2':lm,'NET_counts':{k:gm[k]-lm[k] for k in ('U5','U10','Medium','Weak','realized_positive_N','realized_loser_le0_N')},'actual_PnL_delta_vs_I2':str(delta),'buy_notional_delta_vs_I2':str(D(q['buy_notional'])-D(group(saved['I2'])['buy_notional'])),'lots_delta_vs_I2':q['lots']-group(saved['I2'])['lots'],'cap_hit_delta_vs_I2':cap1-cap0,'exact_identity_quantity_conservation':True,'individual_replacement_causal_claim':False,**changes}
        integrity={'cash_negative':sum(D(c['cash'])<0 for c in curves),'MAX3_excess':sum(c['concurrent']>3 for c in curves),'same_symbol_open':sum(len({p['symbol'] for p in d['held_before_batch']})!=len(d['held_before_batch']) for d in ds),'cutoff_funded':sum(r['entry_minute']>=920 for r in rr),'nonlot100':sum(d['quantity']%100!=0 for d in ds),'execution_unresolved':result['execution_source_unresolved_N'],'canary_fail':read(OUT/'CAUSAL_CANARY_RESULTS.json')['canary_N']-read(OUT/'CAUSAL_CANARY_RESULTS.json')['PASS_N'],'leakage':0}
        g,f=gates(q,integrity);reason={}
        for name,t,total in [('U5',.05,170),('U10',.10,67)]:
            c=Counter(d['reason'] for d in ds if d['entry_id'] in mask and tt[d['entry_id']]['potential_return']>=t);assert sum(c.values())==total;reason[name]=dict(c)
        profiles[arm]={'funded_quality':q,'quality_retention_gates':g,'retention_point_PASS':all(v for k,v in g.items() if k!='Q7'),'v5_floor_gates':f,'v5_floor_PASS':all(f.values()),'integrity':integrity,'reason_conservation':reason,'quantity':{'mean_lots':q['mean_lots'],'median_lots':q['median_lots'],'cap_hit_N':cap1,'waterfill_lots':sum(d.get('water_fill_lots',0) for d in ds),'first_pass_zero_N':sum(d.get('first_pass_quantity')==0 for d in ds if 'first_pass_quantity' in d)},'paired':pairs[arm]};exposures[arm]=exposure(rr)
        outcomes.extend({'entry_id':k,'arm':arm,'I2':bd[k]['reason'],'new':d['reason'],'quantity_I2':bd[k]['quantity'],'quantity_new':d['quantity'],'evaluation_only':True} for k,d in dm.items())
    for a in ARMS:
        exposures[a]['rM_half_delta_vs_I2']={h:{'buy_notional_delta':str(D(exposures[a]['rM_half'][h]['buy_notional'])-D(exposures['I2']['rM_half'][h]['buy_notional'])),'actual_PnL_delta':str(D(exposures[a]['rM_half'][h]['actual_PnL'])-D(exposures['I2']['rM_half'][h]['actual_PnL']))} for h in ('low','high')}
    gzsave(PRIVATE/'PAIRED_EXPOSURE_OUTCOME_LEDGER.jsonl.gz',outcomes)
    save(OUT/'QUALITY_RETENTION_AND_EXPOSURE_DELTA.json',{'exact_jst':now(),'profiles':profiles,'Q7_pending':True,'Safety':SAFETY});save(OUT/'PAIRED_EXPOSURE_DELTA.json',{'exact_jst':now(),'profiles':pairs,'evaluation_only':True});save(OUT/'MRET_AND_POTENTIAL_EXPOSURE_RESULT.json',{'exact_jst':now(),'profiles':exposures,'MRET_decile_semantics':'training percentile [0,.1),...,[.9,1]; exact1 in10; no test cross-section','saved_controls_replayed':0,'missing_realized_imputation':False,'Safety':SAFETY})
    checkpoint('N14_QUALITY_RETENTION_AND_EXPOSURE_DELTA',{'profiles':{a:{'funded_N':p['funded_quality']['N'],'retention_point_PASS':p['retention_point_PASS'],'v5_floor_PASS':p['v5_floor_PASS']} for a,p in profiles.items()}},'Capital / rolling20 from same Main ledgers, frozen gates')
def capital():
    q=read(OUT/'QUALITY_RETENTION_AND_EXPOSURE_DELTA.json')['profiles'];pp={};gate=SPEC['capital_gate_strict'];ref=SPEC['relative_progress_strict']
    for a in ARMS:
        e=read(OUT/f'{a}_RESULT.json');g={'C1':e['rolling20_median']>gate['rolling20_median'],'C2':e['rolling20_arithmetic_mean']>gate['rolling20_mean'],'C3':e['geometric_mean_daily_return']>gate['daily_geometric']};rel={'median':e['rolling20_median']>ref['median'],'mean':e['rolling20_arithmetic_mean']>ref['mean'],'daily_geometric':e['geometric_mean_daily_return']>ref['daily_geometric']}
        pp[a]={'economics':e,'v5_economic_gates':g,'v5_economics_PASS':all(g.values()),'Capital_point_PASS':q[a]['retention_point_PASS'] and all(g.values()),'relative_gates':rel,'relative_three_direction_PASS':all(rel.values()),'MONETIZATION_CAPITAL_PROGRESS':all(rel.values()) and q[a]['v5_floor_PASS'],'Q7_pending':True}
    save(OUT/'CAPITAL_ROLLING20_RESULT.json',{'exact_jst':now(),'profiles':pp,'start_jpy':1000000,'Development_sessions':38,'overlapping_rolling20_windows':19,'windows_independent_claim':False,'Final38_monthly_claim':False,'fresh_OOS_claim':False,'Safety':SAFETY});save(OUT/'PROVISIONAL_WINNER_AND_BOTTLENECK.json',choose(q,pp))
    checkpoint('N15_CAPITAL_ROLLING20',{'profiles':{a:{'v5_economics_PASS':p['v5_economics_PASS'],'relative_progress':p['MONETIZATION_CAPITAL_PROGRESS']} for a,p in pp.items()}},'Independent full cap/accounting/evaluation audit')
def choose(q,c):
    eligible=[a for a in ARMS if q[a]['retention_point_PASS'] and c[a]['v5_economics_PASS']]
    def rank(a):
        e=c[a]['economics'];return (-e['north_star_hit_N'],-e['rolling20_median'],-e['rolling20_arithmetic_mean'],-e['geometric_mean_daily_return'],-e['final_equity'],e['max_drawdown'],ARMS.index(a))
    selected=min(eligible,key=rank) if eligible else None;pool=[a for a in ARMS if q[a]['retention_point_PASS']] or [a for a in ARMS if q[a]['v5_floor_PASS']];diag=selected or (min(pool,key=lambda a:rank(a)[1:]) if pool else I2)
    if selected:
        hit=c[selected]['economics']['north_star_hit_N']>0;status='V11R1_NUMERIC_CERTIFIED_NORTH_STAR_HIT' if hit else 'V11R1_NUMERIC_CERTIFIED_CAPITAL_IMPROVED';bottleneck=SPEC['bottleneck']['official_2x_hit'] if hit else 'NORTH_STAR_CAPITAL_GAP'
    else:
        progress=any(p['MONETIZATION_CAPITAL_PROGRESS'] for p in c.values());status='V11R1_NUMERIC_CERTIFIED_PARTIAL_CAPITAL_PROGRESS' if progress else 'V11R1_NUMERIC_CERTIFIED_POLICY_NO_GO';bottleneck='MONETIZATION_SIGNAL_STRENGTH_OR_CAPITAL_MAPPING' if progress else 'MONETIZATION_POLICY_TRANSLATION'
    short={ARMS[0]:'M1',ARMS[1]:'M2',I2:'I2 saved'}
    return {'status':status,'selectedCapitalCandidate':short[selected] if selected else None,'diagnosticArm':short[diag],'NEXT_BOTTLENECK':bottleneck,'eligible':eligible,'adoption':selected is not None,'Q7_pending':True}
if __name__=='__main__':
    import sys
    {'quality':quality,'capital':capital}[sys.argv[1]]()
