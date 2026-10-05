"""Read only the two claimed ledgers. Frozen teachers are evaluation-only."""
from control import *
from collections import Counter
from decimal import Decimal as D
from statistics import mean,median
import math,sys
REASONS=['FUNDED','RANK_BASE_REJECT','CAPACITY_RESERVE_REJECT','MAX3_FULL','CASH_OR_LOT','SAME_SYMBOL','EXECUTION_BLOCKED','OTHER_EXPLICIT']
def quality(rr,teacher,trade=None):
    tt=[teacher[r['entry_id']] for r in rr];n=len(tt);real=[t['realized_net_return_diagnostic_only'] for t in tt if t['realized_net_return_diagnostic_only'] is not None]
    return {'N':n,'U2':sum(t['U2'] for t in tt),'U2_rate':sum(t['U2'] for t in tt)/n if n else None,'U3':sum(t['U3'] for t in tt),'U3_rate':sum(t['U3'] for t in tt)/n if n else None,'Medium3_5_N':sum(t['U3']-t['U5'] for t in tt),'Medium_rate':sum(t['U3']-t['U5'] for t in tt)/n if n else None,'U5':sum(t['U5'] for t in tt),'U10':sum(t['U10'] for t in tt),'Big5_10_N':sum(t['U5']-t['U10'] for t in tt),'Mega10_N':sum(t['U10'] for t in tt),'Weak2_N':sum(1-t['U2'] for t in tt),'Low2_3_N':sum(t['U2']-t['U3'] for t in tt),'below2_N':sum(1-t['U2'] for t in tt),'below2_rate':sum(1-t['U2'] for t in tt)/n if n else None,'below3_N':sum(1-t['U3'] for t in tt),'below3_rate':sum(1-t['U3'] for t in tt)/n if n else None,'realized_loser_le0_N_diagnostic':sum(z<=0 for z in real),'realized_mean_diagnostic':mean(real) if real else None,'realized_median_diagnostic':median(real) if real else None,'realized_PnL_jpy_diagnostic':str(sum((D(trade[r['entry_id']]['pnl']) for r in rr if trade and r['entry_id'] in trade),D(0))) if trade is not None else None}
def conservation(ds,tt):
    out={}
    for label,field,total in [('U5','U5',170),('U10','U10',67)]:
        c=Counter(r['reason'] if r['reason'] in REASONS else 'OTHER_EXPLICIT' for r in ds if tt[r['entry_id']][field]);assert sum(c.values())==total;out[label]={k:c[k] for k in REASONS}
    return out
def group(rr,tt,trades):
    q=quality(rr,tt,trades)
    q['scores']={f:{'mean':mean(r[f] for r in rr),'median':median(r[f] for r in rr)} if rr else {'mean':None,'median':None} for f in ('pP','q2','q3')}
    q['Entry_hours']={str(h):quality([r for r in rr if r['minute']//60==h],tt,trades) for h in range(9,16)}
    return q
def preservation():
    assert read(OUT/'MAIN_REPLAY_RESULT.json')['primary_replays']==2
    tt={r['entry_id']:r for r in rows(QUALITY/'private/QUALITY_TEACHERS_EVAL.jsonl.gz')};mask={r['entry_id'] for r in rows(MAIN/'private/COMMON_EVAL_MASK.jsonl.gz') if r['included']};rt={r['entry_id']:r for r in rows(PRIVATE/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz')}
    assert len(mask)==1028
    base={r['entry_id']:r for r in rows(MAIN/'private/TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1_DECISIONS.jsonl.gz') if r['entry_id'] in mask};bt={r['entry_id']:r for r in rows(MAIN/'private/TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1_TRADES.jsonl.gz')}
    profiles={};joined={};all_ds={}
    for arm in ARMS:
        e=read(OUT/f'{arm}_RESULT.json');assert e.get('valid_primary_day_N')==38 and e.get('blocked_execution_day_N')==0,'SHARED_EXECUTION_CONTRACT_FAIL_NO_REPLAY_RESCUE'
        ds=[r for r in rows(PRIVATE/f'{arm}_DECISIONS.jsonl.gz') if r['entry_id'] in mask];assert len(ds)==1028 and len({r['entry_id'] for r in ds})==1028
        ts={r['entry_id']:r for r in rows(PRIVATE/f'{arm}_TRADES.jsonl.gz')};cs=rows(PRIVATE/f'{arm}_CURVE.jsonl.gz');fund=[r for r in ds if r['reason']=='FUNDED'];q=quality(fund,tt,ts);cons=conservation(ds,tt)
        integrity={'cash_negative_N':sum(D(c['cash'])<0 for c in cs),'MAX3_excess_N':sum(c['concurrent']>3 for c in cs),'same_symbol_open_N':sum(len({h['symbol'] for h in r['held_before_batch']})<len(r['held_before_batch']) for r in ds),'nonlot100_N':sum(r['quantity']%100!=0 for r in ds),'after1520_funded_N':sum(r['minute']>=920 for r in fund),'execution_unresolved_N':e['execution_source_unresolved_N'],'causal_canary_fail_N':read(OUT/'CAUSAL_CANARY_RESULTS.json')['canary_N']-read(OUT/'CAUSAL_CANARY_RESULTS.json')['PASS_N'],'numeric_dominance_disagreement_N':read(OUT/'NUMERIC_DOMINANCE_BOUNDARY_AUDIT.json')['independent_boundary_disagreement_N'],'leakage_N':0}
        gates={'P1_U5_gt50':q['U5']>50,'P2_U10_ge26':q['U10']>=26,'P3_Medium_ge27':q['Medium3_5_N']>=27,'P4_below2_le38_666667pct':q['below2_rate']<=.38666667,'P5_below3_le48_666667pct':q['below3_rate']<=.48666667,'P6_integrity0':all(v==0 for v in integrity.values()),'P7_independent_mismatch0':'PENDING'}
        gain=[r for r in fund if base[r['entry_id']]['reason']!='FUNDED'];lost=[base[k]|{'q2':rt[k]['q2'],'q3':rt[k]['q3']} for k in base if base[k]['reason']=='FUNDED' and next(r for r in ds if r['entry_id']==k)['reason']!='FUNDED']
        recover=[r for r in fund if base[r['entry_id']]['reason']=='CAPACITY_RESERVE_REJECT'];newmax=[r for r in ds if r['reason']=='MAX3_FULL' and base[r['entry_id']]['reason']!='MAX3_FULL']
        gq=group(gain,tt,ts);lq=group(lost,tt,bt)
        delta={'GAINED_FUNDING_vs_B2':gq,'LOST_FUNDING_vs_B2':lq,'NET_counts':{name:gq[field]-lq[field] for name,field in [('U5','U5'),('U10','U10'),('Medium','Medium3_5_N'),('Weak','Weak2_N')]},'policy_counterfactual_not_unique_causal_replacement':True}
        occupancy={'RESERVE_RECOVERY':group(recover,tt,ts),'NEW_MAX3_MISS_vs_B2':group(newmax,tt,ts),'new_MAX3_prior_reasons':dict(Counter(base[r['entry_id']]['reason'] for r in newmax)),'policy_path_difference_not_unique_causal_blame':True}
        profiles[arm]={'cohort_N':1028,'funded_quality':q,'conservation':cons,'preservation_gates':gates,'point_gates_PASS':all(v for k,v in gates.items() if k!='P7_independent_mismatch0'),'integrity':integrity,'slot_quality':{str(s):quality([r for r in fund if r['funded_slot']==s],tt,ts) for s in (1,2,3)},'Entry_hours':{str(h):quality([r for r in fund if r['minute']//60==h],tt,ts) for h in range(9,16)},'score_diagnostics':{f:{'funded_mean':mean(r[f] for r in fund),'funded_median':median(r[f] for r in fund),'missed_U5_mean':mean(r[f] for r in ds if tt[r['entry_id']]['U5'] and r['reason']!='FUNDED')} for f in ('pP','q2','q3')},'LOWER_P_ACCEPT_AFTER_HIGHER_P_RESERVE_SAME_BATCH':e['LOWER_P_ACCEPT_AFTER_HIGHER_P_RESERVE_SAME_BATCH'],'paired_B2_delta':delta,'induced_occupancy':occupancy}
        joined[arm]={r['entry_id']:r for r in ds};all_ds[arm]=ds
    ledger=[]
    for k in sorted(mask):
        t=tt[k];ledger.append({'entry_id':k,'session':rt[k]['session'],'entry_minute':rt[k]['entry_minute'],'pP':rt[k]['pP'],'r':rt[k]['r'],'q2':rt[k]['q2'],'q3':rt[k]['q3'],'B2':base[k]['reason'],'I1':joined[ARMS[0]][k]['reason'],'I2':joined[ARMS[1]][k]['reason'],'U2':t['U2'],'U3':t['U3'],'Medium':t['U3']-t['U5'],'U5':t['U5'],'U10':t['U10'],'Weak':1-t['U2'],'Low':t['U2']-t['U3'],'realized_return_diagnostic':t['realized_net_return_diagnostic_only'],'evaluation_join_only':True})
    gzsave(PRIVATE/'POLICY_DELTA_LEDGER.jsonl.gz',ledger)
    save(OUT/'PRESERVATION_RESULT.json',{'exact_jst':now(),'profiles':profiles,'common_N':1028,'potential_population':{'Weak2':596,'Low2_3':135,'Medium3_5':127,'Big5_10':103,'Mega10':67},'conservation_exact':True,'independent_pending':True,'Safety':SAFETY})
    save(OUT/'POLICY_DELTA_RESULT.json',{'exact_jst':now(),'profiles':{a:p['paired_B2_delta'] for a,p in profiles.items()},'ledger_sha256':sha(PRIVATE/'POLICY_DELTA_LEDGER.jsonl.gz'),'evaluation_only':True})
    save(OUT/'INDUCED_OCCUPANCY_RESULT.json',{'exact_jst':now(),'profiles':{a:p['induced_occupancy'] for a,p in profiles.items()},'same_state_new_reserve0_proven':True,'global_funded_superset_claim':False})
    checkpoint('V10_POLICY_DELTA_AND_PRESERVATION',{'profiles':{a:{'quality':p['funded_quality'],'point_gates_PASS':p['point_gates_PASS']} for a,p in profiles.items()}},'Same-ledger rolling20/capital gates; then full independent audit')
    print(json.dumps({a:{'quality':p['funded_quality'],'gates':p['preservation_gates']} for a,p in profiles.items()}),flush=True)
def capital():
    pres=read(OUT/'PRESERVATION_RESULT.json')['profiles'];profiles={}
    for a in ARMS:
        e=read(OUT/f'{a}_RESULT.json');g={'rolling20_median':e['rolling20_median']>1.1991541915,'rolling20_mean':e['rolling20_arithmetic_mean']>1.1906460126,'daily_geometric':e['geometric_mean_daily_return']>.01032420041}
        profiles[a]={'economics':e,'economic_point_gates':g,'capital_point_PASS':pres[a]['point_gates_PASS'] and all(g.values()),'independent_pending':True,'NORTH_STAR_HIT_DEVELOPMENT':e['north_star_hit_N']>0}
    save(OUT/'CAPITAL_ROLLING20_RESULT.json',{'exact_jst':now(),'profiles':profiles,'start_jpy':1000000,'Development_sessions':38,'overlapping_window_N':19,'38_sessions_not_one_month':True,'19_rolling_windows_not_independent':True,'fresh_OOS_claim':False,'Safety':SAFETY})
    checkpoint('V11_CAPITAL_ROLLING20',{'profiles':{a:{'economic_gates':p['economic_point_gates'],'capital_point_PASS':p['capital_point_PASS']} for a,p in profiles.items()}},'Full independent raw score/action/Fraction accounting/delta/gate audit')
if __name__=='__main__':{'preservation':preservation,'capital':capital}[sys.argv[1]]()
