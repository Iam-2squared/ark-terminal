"""Evaluation join after two one-shot sizing chains; no runtime feedback."""
from control import *
from attribution import group,fine,coarse,FINE,COARSE
from decimal import Decimal as D
from collections import Counter
def evalrow(r,t,d=None):
    p=t['potential_return'];buy=t['buy_effective'];sell=t['sell_effective'];u=(D(sell)-D(buy))*100 if buy and sell else D(0)
    return {'entry_id':r['entry_id'],'session':r['session'],'symbol':r['symbol'],'entry_minute':r['entry_minute'],'slot':d.get('funded_slot',0) if d else 0,'band':r['band'],'pP':r['pP'],'q2':r['q2'],'q3':r['q3'],'consensus_minrank':r['consensus_weight'],'potential_return':p,'potential_bucket':fine(p),'coarse_bucket':coarse(p),'realized_net_return':t['realized_net_return'] if t['realized_net_return'] is not None else 0.,'quantity':0,'lots':0,'buy_debit':'0','sell_proceeds':'0','actual_PnL':'0','unit_100share_PnL':str(u),'evaluation_only':True}
def economic(e):return {'C1_median_gt_v5':e['rolling20_median']>1.1991541915,'C2_mean_gt_v5':e['rolling20_arithmetic_mean']>1.1906460126,'C3_daily_geo_gt_v5':e['geometric_mean_daily_return']>.01032420041}
def gates(q,integrity):return {'Q1_U5_ge53':q['U5']>=53,'Q2_U10_ge26':q['U10']>=26,'Q3_Medium_ge32':q['Medium']>=32,'Q4_Weak_le36_024845pct':q['below2_rate']<=.36024845,'Q5_below3_le47_204969pct':q['below3_rate']<=.47204969,'Q6_integrity0':all(x==0 for x in integrity.values()),'Q7_independent_mismatch0':'PENDING'}
def floor(q):return {'U5_ge50':q['U5']>=50,'U10_ge26':q['U10']>=26,'Medium_ge27':q['Medium']>=27,'Weak_le38_666667pct':q['below2_rate']<=.38666667,'below3_le48_666667pct':q['below3_rate']<=.48666667}
def quality():
    assert read(OUT/'MAIN_REPLAY_RESULT.json')['primary_replays']==2
    tt={r['entry_id']:r for r in rows(MAIN/'inputs/evaluation/TEACHERS_EVALUATION.jsonl.gz')};rt={r['entry_id']:r for r in rows(PRIVATE/'CURRENT_SIZING_RUNTIME.jsonl.gz')};mask={r['entry_id'] for r in rows(MAIN/'private/COMMON_EVAL_MASK.jsonl.gz') if r['included']};base={r['entry_id']:r for r in rows(V9PRIVATE/f'{I2}_DECISIONS.jsonl.gz')};bt={r['entry_id']:r for r in rows(PRIVATE/'I2_MONETIZATION_TRADE_LEDGER.jsonl.gz')};profiles={};pairs={};ledger=[]
    for arm in ARMS:
        ds=rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz');dm={r['entry_id']:r for r in ds};tr={r['entry_id']:r for r in rows(PRIVATE/f'{arm}_TRADES.jsonl.gz')};cs=rows(PRIVATE/f'{arm}_CURVE.jsonl.gz');rr=[]
        for k,t in tr.items():
            r=evalrow(rt[k],tt[k],dm[k]);r.update(quantity=t['quantity'],lots=t['quantity']//100,buy_debit=t['debit'],sell_proceeds=t['credit'],actual_PnL=t['pnl'],realized_net_return=t['net_return'],unit_100share_PnL=str((D(t['sell_effective'])-D(t['buy_effective']))*100));rr.append(r)
        assert all(r['entry_id'] in mask for r in rr),'UNSUPPORTED_FUNDED_QUALITY_SOURCE_FAIL_STOP'
        gzsave(PRIVATE/f'{arm}_MONETIZATION_TRADE_LEDGER.jsonl.gz',rr);q=group(rr);fund=set(tr);bfund=set(bt);common=fund&bfund;gain=[r for r in rr if r['entry_id'] not in bfund];lost=[bt[k] for k in sorted(bfund-fund)];cg=[];qd=D(0)
        for k in sorted(common):
            a=bt[k];b=next(r for r in rr if r['entry_id']==k);unit=D(b['unit_100share_PnL']);assert unit==D(a['unit_100share_PnL']);change=unit*((b['quantity']-a['quantity'])//100);qd+=change;cg.append({'entry_id':k,'q_I2':a['quantity'],'q_new':b['quantity'],'quantity_delta':b['quantity']-a['quantity'],'potential_bucket':b['potential_bucket'],'coarse_bucket':b['coarse_bucket'],'realized_net_return':b['realized_net_return'],'unit_100share_PnL':str(unit),'common_quantity_PnL_delta':str(change)})
        g=group(gain);l=group(lost);total=D(q['actual_PnL'])-sum((D(z['actual_PnL']) for z in bt.values()),D(0));assert total==qd+D(g['actual_PnL'])-D(l['actual_PnL'])
        newmax=[evalrow(rt[k],tt[k],d) for k,d in dm.items() if d['reason']=='MAX3_FULL' and base[k]['reason']!='MAX3_FULL'];cashrecover=[r for r in rr if base[r['entry_id']]['reason']=='CASH_OR_LOT'];newcash=[evalrow(rt[k],tt[k],d) for k,d in dm.items() if d['reason']=='CASH_OR_LOT' and base[k]['reason']!='CASH_OR_LOT']
        integrity={'cash_negative':sum(D(r['cash'])<0 for r in cs),'MAX3_excess':sum(r['concurrent']>3 for r in cs),'same_symbol_open':sum(len({p['symbol'] for p in r['held_before_batch']})!=len(r['held_before_batch']) for r in ds),'cutoff_funded':sum(r['entry_minute']>=920 for r in rr),'nonlot100':sum(r['quantity']%100!=0 for r in ds),'execution_unresolved':read(OUT/f'{arm}_RESULT.json')['execution_source_unresolved_N'],'causal_canary_fail':read(OUT/'CAUSAL_CANARY_RESULTS.json')['canary_N']-read(OUT/'CAUSAL_CANARY_RESULTS.json')['PASS_N'],'leakage':0}
        gg=gates(q,integrity);ff=floor(q);total_notional=q['buy_notional'];cons={}
        for label,threshold,totalN in [('U5',.05,170),('U10',.10,67)]:
            cc=Counter(d['reason'] for d in ds if d['entry_id'] in mask and tt[d['entry_id']]['potential_return']>=threshold);assert sum(cc.values())==totalN;cons[label]=dict(cc)
        net={f:g[f]-l[f] for f in ('U5','U10','Medium','Weak','realized_positive_N','realized_loser_le0_N')}
        quantitygroup={name:{'N':sum(test(z) for z in cg),'quantity_delta':sum(z['quantity_delta'] for z in cg if test(z)),'exact_common_quantity_PnL_delta':str(sum((D(z['common_quantity_PnL_delta']) for z in cg if test(z)),D(0)))} for name,test in [('Weak',lambda z:z['coarse_bucket']=='Weak'),('Low',lambda z:z['coarse_bucket']=='Low'),('Medium',lambda z:z['coarse_bucket']=='Medium'),('Big',lambda z:z['coarse_bucket']=='Big'),('Mega',lambda z:z['coarse_bucket']=='Mega'),('U5',lambda z:z['coarse_bucket'] in ('Big','Mega')),('U10',lambda z:z['coarse_bucket']=='Mega'),('realized_le0',lambda z:z['realized_net_return']<=0),('realized_ge1pct',lambda z:z['realized_net_return']>=.01)]}
        paired={'COMMON_FUNDED':{'N':len(common),'common_quantity_PnL_delta':str(qd),'quantity_groups':quantitygroup},'GAINED_FUNDING_vs_I2':g,'LOST_FUNDING_vs_I2':l,'NET_counts':net,'NEW_MAX3_MISS_vs_I2':group(newmax),'CASH_RECOVERY_vs_I2':group(cashrecover),'NEW_CASH_MISS_vs_I2':group(newcash),'actual_PnL_delta_vs_I2':str(total),'exact_identity_quantity_conservation':True,'individual_replacement_causal_claim':False};pairs[arm]=paired;gzsave(PRIVATE/f'{arm}_COMMON_QUANTITY_DELTA.jsonl.gz',cg)
        allocationdiag={'slot':{str(s):group([r for r in rr if r['slot']==s],total_notional) for s in (1,2,3)},'band':{b:group([r for r in rr if r['band']==b],total_notional) for b in ('P_HIGH','P_MID','P_BASE')},'Entry_hour':{str(h):group([r for r in rr if r['entry_minute']//60==h],total_notional) for h in range(9,16)},'potential_bucket':{b:group([r for r in rr if r['potential_bucket']==b],total_notional) for b in FINE},'exposure':{name:group([r for r in rr if predicate(r)],total_notional) for name,predicate in [('Weak',lambda r:r['potential_return']<.02),('Medium+',lambda r:r['potential_return']>=.03),('U5',lambda r:r['potential_return']>=.05),('U10',lambda r:r['potential_return']>=.10)]},'quantity':{'mean_lots':q['mean_lots'],'median_lots':q['median_lots'],'candidate_cap_hit_N':sum(d.get('cap_hit',False) for d in ds if d['reason']=='FUNDED'),'candidate_cap_hit_definition':'next one lot would exceed frozen band equity cap','waterfill_lot_N':sum(d.get('water_fill_lots',0) for d in ds),'first_pass_zero_N':sum(d.get('first_pass_quantity')==0 for d in ds if 'first_pass_quantity' in d)}}
        profiles[arm]={'funded_quality':q,'quality_retention_gates':gg,'retention_point_PASS':all(v for k,v in gg.items() if not k.startswith('Q7')),'v5_floor_gates':ff,'v5_floor_PASS':all(ff.values()),'integrity':integrity,'U5_U10_reason_conservation':cons,'paired_delta':paired,'allocation_diagnostics':allocationdiag}
        ledger += [{'entry_id':k,'arm':arm,'I2':base[k]['reason'],'new':dm[k]['reason'],'quantity_I2':base[k]['quantity'],'quantity_new':dm[k]['quantity'],'evaluation_only':True} for k in sorted(dm)]
    gzsave(PRIVATE/'PAIRED_SIZING_OUTCOME_LEDGER.jsonl.gz',ledger);save(OUT/'QUALITY_RETENTION_AND_PAIRED_DELTA.json',{'exact_jst':now(),'profiles':profiles,'Q7_pending':True,'Safety':SAFETY});save(OUT/'PAIRED_SIZING_DELTA.json',{'exact_jst':now(),'profiles':pairs,'evaluation_only':True});checkpoint('M11_QUALITY_RETENTION_AND_PAIRED_DELTA',{'profiles':{a:{'quality':p['funded_quality'],'retention_point_PASS':p['retention_point_PASS'],'v5_floor_PASS':p['v5_floor_PASS']} for a,p in profiles.items()}},'Same-ledger capital / rolling20 and fixed relative progress')
def capital():
    pp=read(OUT/'QUALITY_RETENTION_AND_PAIRED_DELTA.json')['profiles'];base=read(PARENT/f'{I2}_RESULT.json');profiles={}
    for a in ARMS:
        e=read(OUT/f'{a}_RESULT.json');g=economic(e);rel={'median':e['rolling20_median']>base['rolling20_median'],'mean':e['rolling20_arithmetic_mean']>base['rolling20_arithmetic_mean'],'daily_geometric':e['geometric_mean_daily_return']>base['geometric_mean_daily_return']}
        profiles[a]={'economics':e,'v5_economic_gates':g,'v5_economics_PASS':all(g.values()),'Capital_point_PASS':pp[a]['retention_point_PASS'] and all(g.values()),'I2_relative_gates':rel,'I2_three_direction_PASS':all(rel.values()),'RELATIVE_CAPITAL_PROGRESS':all(rel.values()) and pp[a]['v5_floor_PASS'],'Q7_pending':True}
    save(OUT/'CAPITAL_ROLLING20_RESULT.json',{'exact_jst':now(),'profiles':profiles,'start_jpy':1000000,'Development_sessions':38,'overlapping_windows':19,'rolling_windows_not_independent':True,'Final38_not_monthly':True,'fresh_OOS_claim':False,'Safety':SAFETY});save(OUT/'PROVISIONAL_WINNER_AND_BOTTLENECK.json',choose(pp,profiles));checkpoint('M12_CAPITAL_ROLLING20',{'profiles':{a:{'v5_economics_PASS':p['v5_economics_PASS'],'relative_progress':p['RELATIVE_CAPITAL_PROGRESS']} for a,p in profiles.items()}},'Full independent raw/Fraction attribution, replay, shadow, integer solve and final gates')
def choose(profiles,cap):
    eligible=[a for a in ARMS if profiles[a]['retention_point_PASS'] and cap[a]['v5_economics_PASS']]
    def official(a):
        e=cap[a]['economics'];return (-e['north_star_hit_N'],-e['rolling20_median'],-e['rolling20_arithmetic_mean'],-e['geometric_mean_daily_return'],-e['final_equity'],e['max_drawdown'],ARMS.index(a))
    def diag(a):return official(a)[1:]
    selected=min(eligible,key=official) if eligible else None
    pool=[a for a in ARMS if profiles[a]['retention_point_PASS']] or [a for a in ARMS if profiles[a]['v5_floor_PASS']]
    diagnostic=selected or (min(pool,key=diag) if pool else I2)
    if selected:
        status='V10_NORTH_STAR_HIT' if cap[selected]['economics']['north_star_hit_N'] else 'V10_CAPITAL_IMPROVED';bottleneck=None if status=='V10_NORTH_STAR_HIT' else 'NORTH_STAR_CAPITAL_GAP'
    else:
        if diagnostic in ARMS and profiles[diagnostic]['retention_point_PASS'] and cap[diagnostic]['RELATIVE_CAPITAL_PROGRESS']:bottleneck='SIZING_REMAINS'
        elif all(not p['v5_economics_PASS'] for p in cap.values()) and all(not p['I2_three_direction_PASS'] for p in cap.values()):bottleneck='REALIZED_MONETIZATION_SIGNAL'
        else:bottleneck='SIZING_INDUCED_FUNDING_DISTORTION'
        if any(p['RELATIVE_CAPITAL_PROGRESS'] for p in cap.values()):status='V10_PARTIAL_SIZING_PROGRESS'
        elif all(not p['v5_economics_PASS'] for p in cap.values()) and all(not p['I2_three_direction_PASS'] for p in cap.values()):status='V10_REALIZED_MONETIZATION_LIMIT'
        elif any(not p['retention_point_PASS'] for p in profiles.values()):status='V10_SIZING_QUALITY_REGRESSION'
        else:status='V10_NO_GO'
    short={ARMS[0]:'S1',ARMS[1]:'S2',I2:'I2 saved'}
    return {'status':status,'selectedCapitalCandidate':short[selected] if selected else None,'diagnosticArm':short[diagnostic],'NEXT_BOTTLENECK':bottleneck,'eligible':eligible,'adoption':selected is not None}
if __name__=='__main__':
    import sys
    {'quality':quality,'capital':capital}[sys.argv[1]]()
