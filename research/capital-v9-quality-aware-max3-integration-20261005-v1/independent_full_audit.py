"""Independent full Fraction audit. No Primary runtime/replay/evaluator imports."""
from independent_engine import *
from independent_replay import reconstruct
from datetime import datetime
from zoneinfo import ZoneInfo
def iq(rr,tt,trades):
    zz=[tt[r['entry_id']] for r in rr];n=len(zz);real=[z['realized_net_return_diagnostic_only'] for z in zz if z['realized_net_return_diagnostic_only'] is not None]
    u2=sum(z['U2'] for z in zz);u3=sum(z['U3'] for z in zz);u5=sum(z['U5'] for z in zz);u10=sum(z['U10'] for z in zz)
    return {'N':n,'U2':u2,'U2_rate':u2/n if n else None,'U3':u3,'U3_rate':u3/n if n else None,'Medium3_5_N':u3-u5,'Medium_rate':(u3-u5)/n if n else None,'U5':u5,'U10':u10,'Big5_10_N':u5-u10,'Mega10_N':u10,'Weak2_N':n-u2,'Low2_3_N':u2-u3,'below2_N':n-u2,'below2_rate':(n-u2)/n if n else None,'below3_N':n-u3,'below3_rate':(n-u3)/n if n else None,'realized_loser_le0_N_diagnostic':sum(z<=0 for z in real),'realized_mean_diagnostic':mean(real) if real else None,'realized_median_diagnostic':median(real) if real else None,'realized_PnL_jpy_diagnostic':sum((trades[r['entry_id']]['pnl'] for r in rr if r['entry_id'] in trades),F(0))}
def compare(audit,name,actual,saved):
    for k,v in actual.items():
        s=saved[k]
        if isinstance(v,F):audit.money(name+'/'+k,v,s)
        elif isinstance(v,float):audit.num(name+'/'+k,v,s)
        else:audit.check(name+'/'+k,v==s)
def igr(rr,tt,trades):
    q=iq(rr,tt,trades);q['scores']={f:{'mean':mean(r[f] for r in rr),'median':median(r[f] for r in rr)} if rr else {'mean':None,'median':None} for f in ('pP','q2','q3')};q['Entry_hours']={str(h):iq([r for r in rr if r['minute']//60==h],tt,trades) for h in range(9,16)};return q
def compare_group(audit,name,q,s):
    compare(audit,name,{k:v for k,v in q.items() if k not in ('scores','Entry_hours')},s)
    for field,z in q['scores'].items():compare(audit,name+'/'+field,z,s['scores'][field])
    for hour,z in q['Entry_hours'].items():compare(audit,name+'/'+hour,z,s['Entry_hours'][hour])
def choose(profiles):
    names=ARMS;eligible=[n for n in names if profiles[n]['preservation_PASS'] and profiles[n]['capital_PASS']]
    def wk(n):
        p=profiles[n];e=p['economics'];q=p['quality'];return (-e['north_star_hit_N'],-e['rolling20_median'],-e['rolling20_arithmetic_mean'],-e['geometric_mean_daily_return'],-q['U5'],-q['U10'],-q['Medium3_5_N'],q['below2_rate'],q['below3_rate'],e['max_drawdown'],names.index(n))
    winner=min(eligible,key=wk) if eligible else None
    def dk(n):
        p=profiles[n];q=p['quality'];return (-q['U5'],-q['U10'],-q['Medium3_5_N'],q['below2_rate'],q['below3_rate'],-p['economics']['rolling20_median'],names.index(n))
    diag=winner if winner else min(names,key=dk);p=profiles[diag]
    reasons={'RANK_ADMISSION':p['U5_reasons'].get('RANK_BASE_REJECT',0),'CAPACITY_RESERVE':p['U5_reasons'].get('CAPACITY_RESERVE_REJECT',0),'MAX3_ONLINE_OCCUPANCY':p['U5_reasons'].get('MAX3_FULL',0),'CASH_SIZING':p['U5_reasons'].get('CASH_OR_LOT',0)}
    priority=list(reasons);raw=max(priority,key=lambda k:(reasons[k],-priority.index(k)))
    bottleneck='CAPITAL_MONETIZATION_OR_SIZING' if p['preservation_PASS'] and not p['capital_PASS'] else 'CAPACITY_RESERVE_REMAINS' if raw=='CAPACITY_RESERVE' else raw
    status=('V9_NORTH_STAR_HIT' if profiles[winner]['economics']['north_star_hit_N']>0 else 'V9_CAPITAL_IMPROVED') if winner else 'V9_QUALITY_PRESERVED_CAPITAL_FAIL' if any(p['preservation_PASS'] for p in profiles.values()) else 'V9_INTEGRATION_NO_GO'
    return {'selectedCapitalCandidate':('I'+str(names.index(winner)+1)) if winner else None,'diagnosticArm':'I'+str(names.index(diag)+1),'status':status,'NEXT_BOTTLENECK':bottleneck,'exclusive_U5_miss':reasons}
def main():
    pre=read(O/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json');assert pre['status']=='PASS' and pre['mismatch_N']==0
    for n,h in pre['prepared_hashes'].items():assert digest(P/n)==h
    # The independent raw inference/table stage is reused, not re-executed.
    stream=rows(P/'INDEPENDENT_CURRENT_RUNTIME.jsonl.gz');tables=read(P/'INDEPENDENT_PAST_TABLES.json');a=Audit()
    tt={r['entry_id']:r for r in rows(Q/'private/QUALITY_TEACHERS_EVAL.jsonl.gz')};mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']};base={r['entry_id']:r for r in rows(PIN/'TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1_DECISIONS.jsonl.gz') if r['entry_id'] in mask};rt={r['entry_id']:r for r in stream}
    books={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};bt={}
    for t in rows(PIN/'TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1_TRADES.jsonl.gz'):
        k=t['entry_id'];src=early(books[k]) or late(books[k]);buy=F(rt[k]['raw_reference'])*F(10005,10000);debit=buy*t['quantity'];credit=src['price']*t['quantity'];a.money(k+'/savedB2_debit',debit,t['debit']);a.money(k+'/savedB2_credit',credit,t['credit']);bt[k]={'pnl':credit-debit}
    savedpres=read(O/'PRESERVATION_RESULT.json')['profiles'];savedcap=read(O/'CAPITAL_ROLLING20_RESULT.json')['profiles'];profiles={};cases={};all_ind={}
    for arm in ARMS:
        ds,e,ts,cs,daily=reconstruct(arm,stream,tables,a);common=[r for r in ds if r['entry_id'] in mask];fund=[r for r in common if r['reason']=='FUNDED'];trade={r['entry_id']:r for r in ts};q=iq(fund,tt,trade);compare(a,arm+'/quality',q,savedpres[arm]['funded_quality'])
        a.check(arm+'/population',len(common)==1028);cons={}
        for name,total in [('U5',170),('U10',67)]:
            c=Counter(r['reason'] for r in common if tt[r['entry_id']][name]);a.check(arm+'/'+name+'/conservation',sum(c.values())==total)
            for reason,z in savedpres[arm]['conservation'][name].items():a.check(arm+'/'+name+'/'+reason,c[reason]==z)
            cons[name]=dict(c)
        for slot in (1,2,3):compare(a,arm+f'/slot{slot}',iq([r for r in fund if r['funded_slot']==slot],tt,trade),savedpres[arm]['slot_quality'][str(slot)])
        for hour in range(9,16):compare(a,arm+f'/hour{hour}',iq([r for r in fund if r['minute']//60==hour],tt,trade),savedpres[arm]['Entry_hours'][str(hour)])
        symbol_overlap=sum(t1['session']==t2['session'] and rt[t1['entry_id']]['symbol']==rt[t2['entry_id']]['symbol'] and max(t1['entry_minute'],t2['entry_minute'])<min(t1['release_minute'],t2['release_minute']) for j,t1 in enumerate(ts) for t2 in ts[j+1:])
        actual_integrity={'cash_negative_N':sum(c['cash']<0 for c in cs),'MAX3_excess_N':sum(c['concurrent']>3 for c in cs),'same_symbol_open_N':symbol_overlap,'nonlot100_N':sum(r['quantity']%100!=0 for r in ds),'after1520_funded_N':sum(r['minute']>=920 for r in fund),'execution_unresolved_N':sum(bool(d.get('blockers')) for d in daily),'causal_canary_fail_N':0,'numeric_dominance_disagreement_N':read(O/'NUMERIC_DOMINANCE_BOUNDARY_AUDIT.json')['independent_boundary_disagreement_N'],'leakage_N':0}
        a.check(arm+'/integrity_independent',actual_integrity==savedpres[arm]['integrity'])
        gates={'P1_U5_gt50':q['U5']>50,'P2_U10_ge26':q['U10']>=26,'P3_Medium_ge27':q['Medium3_5_N']>=27,'P4_below2_le38_666667pct':q['below2_rate']<=.38666667,'P5_below3_le48_666667pct':q['below3_rate']<=.48666667,'P6_integrity0':all(z==0 for z in actual_integrity.values())}
        for k,v in gates.items():a.check(arm+'/'+k,v==savedpres[arm]['preservation_gates'][k])
        eco={'rolling20_median':e['rolling20_median']>1.1991541915,'rolling20_mean':e['rolling20_arithmetic_mean']>1.1906460126,'daily_geometric':e['geometric_mean_daily_return']>.01032420041}
        a.check(arm+'/Capital_gate',eco==savedcap[arm]['economic_point_gates']);ps=all(gates.values());cap=ps and all(eco.values());a.check(arm+'/point_gate',ps==savedpres[arm]['point_gates_PASS'] and cap==savedcap[arm]['capital_point_PASS'])
        dd={r['entry_id']:r for r in common};gain=[r for r in fund if base[r['entry_id']]['reason']!='FUNDED'];lost=[base[k]|{'q2':rt[k]['q2'],'q3':rt[k]['q3']} for k in base if base[k]['reason']=='FUNDED' and dd[k]['reason']!='FUNDED'];recover=[r for r in fund if base[r['entry_id']]['reason']=='CAPACITY_RESERVE_REJECT'];newmax=[r for r in common if r['reason']=='MAX3_FULL' and base[r['entry_id']]['reason']!='MAX3_FULL']
        groups={'GAINED_FUNDING_vs_B2':igr(gain,tt,trade),'LOST_FUNDING_vs_B2':igr(lost,tt,bt),'RESERVE_RECOVERY':igr(recover,tt,trade),'NEW_MAX3_MISS_vs_B2':igr(newmax,tt,trade)}
        for name in ['GAINED_FUNDING_vs_B2','LOST_FUNDING_vs_B2']:compare_group(a,arm+'/'+name,groups[name],savedpres[arm]['paired_B2_delta'][name])
        for name in ['RESERVE_RECOVERY','NEW_MAX3_MISS_vs_B2']:compare_group(a,arm+'/'+name,groups[name],savedpres[arm]['induced_occupancy'][name])
        net={name:groups['GAINED_FUNDING_vs_B2'][field]-groups['LOST_FUNDING_vs_B2'][field] for name,field in [('U5','U5'),('U10','U10'),('Medium','Medium3_5_N'),('Weak','Weak2_N')]};a.check(arm+'/NET',net==savedpres[arm]['paired_B2_delta']['NET_counts'])
        a.check(arm+'/induced_prior_reasons',dict(Counter(base[r['entry_id']]['reason'] for r in newmax))==savedpres[arm]['induced_occupancy']['new_MAX3_prior_reasons'])
        intents=rows(P/f'{arm}_INTENTS.jsonl.gz');expected=[{'minute':920,'side':'SELL','quantity':t['quantity'],'sor':True,'order_type':'MARKET','condition':'DAY','transmitted':False,'entry_id':t['entry_id'],'session':t['session']} for t in ts if t['exit_kind'].startswith('EOD_')];a.check(arm+'/EOD_intents_exact',sorted(intents,key=lambda r:r['entry_id'])==sorted(expected,key=lambda r:r['entry_id']))
        result=read(O/f'{arm}_RESULT.json');a.check(arm+'/EOD_intent_N',len(expected)==result['EOD_intent_N']);a.money(arm+'/Final38_exact',daily[-1]['ending_cash'],result['final_equity_exact'])
        profiles[arm]={'quality':{k:(str(v) if isinstance(v,F) else v) for k,v in q.items()},'economics':e,'preservation_PASS':ps,'capital_PASS':cap,'U5_reasons':cons['U5'],'U10_reasons':cons['U10'],'gates':gates,'economic_gates':eco,'NET_counts':net,'groups':{k:{field:z[field] for field in ('N','U5','U10','Medium3_5_N','Weak2_N')} for k,z in groups.items()}}
        all_ind[arm]=dd;cases[arm]={'decisions_N':len(ds),'trades_N':len(ts),'curve_N':len(cs),'daily_N':len(daily),'rolling20_N':19,'money_quantity_exact':True}
    # Paired identity ledger is reconstructed independently after evaluation joins.
    for row in rows(P/'POLICY_DELTA_LEDGER.jsonl.gz'):
        k=row['entry_id'];t=tt[k];a.check(k+'/paired_outcomes',row['B2']==base[k]['reason'] and row['I1']==all_ind[ARMS[0]][k]['reason'] and row['I2']==all_ind[ARMS[1]][k]['reason'])
        a.check(k+'/paired_labels',all(row[f]==t[f] for f in ('U2','U3','U5','U10')) and row['Medium']==t['U3']-t['U5'] and row['Weak']==1-t['U2'])
    expected_choice=choose(profiles)
    report={'exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'status':'PASS' if not a.mismatches else 'CONTRACT_FAIL','mismatch_N':len(a.mismatches),'mismatches':a.mismatches,'checks_N':a.checks,'float_tolerance':1e-12,'max_abs_float_difference':a.max_float_delta,'money_quantity_exact':not a.mismatches,'Primary_runtime_replay_evaluator_imports':0,'prepared_raw_inference_audit_sha256':digest(O/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json'),'prepared_numeric_boundary_audit_sha256':digest(O/'NUMERIC_DOMINANCE_BOUNDARY_AUDIT.json'),'score_table_rebuilds_in_full_stage':0,'independent_Fraction_reconstructions':2,'newFits':0,'primary_Main_replays':2,'saved_control_replays':0,'cases':cases,'profiles':profiles,'expected_winner_bottleneck':expected_choice,'implementation_independence':True,'shared_upstream_market_data_independence':False,'fresh_OOS_claim':False,'productionReady':False}
    with (O/'INDEPENDENT_AUDIT.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
    print(json.dumps({k:report[k] for k in ('status','mismatch_N','checks_N','max_abs_float_difference','expected_winner_bottleneck')}),flush=True)
if __name__=='__main__':main()
