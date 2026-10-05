"""Finite score and cash/lot diagnostics, never used by live decision code."""
from collections import defaultdict,Counter
from decimal import Decimal as D
from statistics import mean,median
import math
from io_utils import *

HEADS={'pP/MOVE_P5':'pP','MOVE_U2':'q2','MOVE_U3':'q3','MRET':'mP'}
def auc(pairs):
    n1=sum(y for s,y in pairs);n0=len(pairs)-n1
    if not n1 or not n0:return None
    groups=defaultdict(lambda:[0,0])
    for score,y in pairs:groups[score][int(y)]+=1
    lower0=0;area=0
    for score,(zero,one) in sorted(groups.items()):area+=one*(lower0+zero/2);lower0+=zero
    return area/(n0*n1)

def score_stats(ls,scores,field):
    good=[r for r in ls if r['known'] and r['entry_id'] in scores and math.isfinite(scores[r['entry_id']][field])]
    x={}
    for label in ['R5','R10']:
        pairs=[(scores[r['entry_id']][field],r[label]) for r in good]
        blocks=[];sessions=[]
        for key,values in [('block',blocks),('session',sessions)]:
            for group in sorted({r[key] for r in good}):
                rr=[r for r in good if r[key]==group];ap=auc([(scores[r['entry_id']][field],r[label]) for r in rr])
                values.append({key:group,'N':len(rr),'positive_N':sum(r[label] for r in rr),'rate':sum(r[label] for r in rr)/len(rr),'AUROC':ap})
        x[label]={'N':len(good),'positive_N':sum(r[label] for r in good),'AUROC':auc(pairs),'by_block':blocks,'by_session':sessions,'mean_defined_session_AUROC':mean(r['AUROC'] for r in sessions if r['AUROC'] is not None) if any(r['AUROC'] is not None for r in sessions) else None,'session_defined_N':sum(r['AUROC'] is not None for r in sessions)}
    return x

def capture(ls,ds,ts):
    funded={d['entry_id'] for d in ds if d['reason']=='FUNDED'};lm={r['entry_id']:r for r in ls}
    out={}
    for mask,rr in [('all',ls),('rankpass',[r for r in ls if r['rank_pass']]),('eligible',[r for r in ls if r['execution_eligible']]),('eligible_rankpass',[r for r in ls if r['execution_eligible'] and r['rank_pass']])]:
        fs=[r for r in rr if r['entry_id'] in funded];nf=[r for r in rr if r['entry_id'] not in funded];known=[r for r in fs if r['known']]
        tab={'N':len(rr),'known_N':sum(r['known'] for r in rr),'unknown_N':sum(not r['known'] for r in rr),'funded_N':len(fs),'funded_known_N':len(known),'funded_unknown_N':len(fs)-len(known),'nonfunded_N':len(nf),'nonfunded_known_N':sum(r['known'] for r in nf),'nonfunded_unknown_N':sum(not r['known'] for r in nf)}
        for label in ['R5','R10']:
            n=sum(r[label] is True for r in fs);total=sum(r[label] is True for r in rr)
            tab[label]={'funded_true_N':n,'population_true_N':total,'funded_precision':n/len(known) if known else None,'capture_recall':n/total if total else None}
        out[mask]=tab
    bins={}
    for name in ['LE0','GT0_LT5','GE5_LT10','GE10','UNKNOWN']:
        rr=[t for t in ts if lm[t['entry_id']]['net_bin']==name]
        bins[name]={'closed_trade_N':len(rr),'buy_debit_jpy':str(sum((D(t['debit']) for t in rr),D(0))),'net_pnl_jpy':str(sum((D(t['pnl']) for t in rr),D(0))),'holding_minutes':sum(t['release_minute']-t['entry_minute'] for t in rr),'capital_minutes_jpy':str(sum((D(t['debit'])*(t['release_minute']-t['entry_minute']) for t in rr),D(0)))}
    reasons={}
    for label in ['R5','R10']:
        misses=[d for d in ds if d['reason']!='FUNDED' and lm[d['entry_id']]['execution_eligible'] and lm[d['entry_id']][label] is True]
        reasons[label]=dict(Counter(d['reason'] for d in misses))
    cross={u:{r:sum(lm[k][u] is True and lm[k][r] is True for k in funded) for r in ['R5','R10','Loser']} for u in ['U5','U10','Weak']}
    return {'census':out,'funded_cross':cross,'net_bins':bins,'eligible_miss_reasons':reasons}

def money_paths(ds,ts,lm):
    picked=[d for d in ds if 'first_pass_quantity' in d]
    zero=[d for d in picked if d['quantity']==0]
    late_rescue=[d for d in zero if D(d['budget_unspent'])>=D(d['lot_debit']) and D(d['equity_cap'])>=D(d['lot_debit'])]
    capfloor=[d for d in zero if D(d['equity_cap'])<D(d['lot_debit'])<=D(d['batch_budget']) and D(d['cash_before'])>=D(d['lot_debit'])]
    capbound=[d for d in picked if d['quantity']>0 and D(d['debit'])+D(d['lot_debit'])>D(d['equity_cap']) and D(d['budget_unspent'])>=D(d['lot_debit'])]
    blockers=Counter()
    for d in zero:
        lot=D(d['lot_debit'])
        if D(d['equity_cap'])<lot:blockers['BAND_CAP_BELOW_ONE_LOT']+=1
        if D(d['batch_budget'])<lot:blockers['TARGET_BUDGET_BELOW_ONE_LOT']+=1
        if D(d['desired'])<lot:blockers['PROPORTIONAL_INITIAL_SHARE_BELOW_ONE_LOT']+=1
        if D(d['cash_before'])<lot:blockers['CASH_BELOW_ONE_LOT']+=1
    cases=[]
    for d in capfloor:
        l=lm[d['entry_id']]
        cases.append({'entry_id':d['entry_id'],'session':d['session'],'minute':d['minute'],'rank':d['rank'],'native_quantity':d['quantity'],'lot_debit':d['lot_debit'],'band_cap':d['equity_cap'],'target_budget':d['batch_budget'],'cash_before':d['cash_before'],'held_ids':d['held_before_batch'],'local_new_lot_feasible':True,'realized_label_diagnostic_only':{'R5':l['R5'],'R10':l['R10'],'Loser':l['Loser'],'known':l['known']},'counterfactual_status':'LOCAL_CONSTRAINT_CHECK_ONLY_NOT_PORTFOLIO_RECOVERY'})
    hold_competition=Counter();donor_comp=0;samebatch=0
    batches=defaultdict(list)
    for d in ds:batches[(d['session'],d['minute'])].append(d)
    for d in ds:
        if d['reason']=='FUNDED' or not lm[d['entry_id']]['execution_eligible'] or lm[d['entry_id']]['R5'] is not True:continue
        hold_competition[d['reason']]+=len(d['held_before_batch'])
        donor_comp+=sum(lm[k]['Loser'] is True for k in d['held_before_batch'])
        samebatch+=any(x['reason']=='FUNDED' for x in batches[(d['session'],d['minute'])])
    return {'admitted_allocation_N':len(picked),'quantity_zero_N':len(zero),'overlapping_constraints':dict(blockers),'initial_zero_exclusion_with_existing_residual_rescuable_N':len(late_rescue),'band_cap_blocks_target_cash_feasible_minlot_N':len(capfloor),'band_cap_floor_local_cases':cases,'funded_next_lot_cap_bound_with_target_residual_N':len(capbound),'R5_miss_held_position_incidents':dict(hold_competition),'R5_miss_held_Loser_incidents':donor_comp,'R5_miss_same_batch_with_funded_peer_N':samebatch,'causal_recovery_claim':False,'meaning':'Shrinking a100+share donor releases cash, no slot; no buyback/topup. Receiver must be a current or later new Frozen Entry; current lot<cap, target, cash and admission jointly constrain quantity.'}

def main():
    ls=rows(PRIVATE/'evaluation-only/R_LABELS.jsonl.gz');lm={r['entry_id']:r for r in ls};native_ds=rows(INPUTS/'native_decisions');native_ts=rows(INPUTS/'native_trades')
    scores={r['entry_id']:r for r in rows(INPUTS/'c7e10944822c_CURRENT_MRET_CAP_RUNTIME.jsonl.gz')};cert={r['entry_id']:r for r in rows(INPUTS/'90f4dc118b1a_CERTIFIED_INDEPENDENT_MRET_OOF_SCORES.jsonl.gz')};quality={r['entry_id']:r for r in rows(INPUTS/'57759e748e8f_CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz')}
    assert set(scores)==set(lm)==set(cert)==set(quality)
    assert all(all(scores[k][f]==quality[k][f] for f in ['pP','q2','q3','r','rank_units','train_N','block','session','entry_minute']) for k in scores)
    mdelta=max(abs(scores[k]['mP']-cert[k]['mP']) for k in scores)
    assert mdelta<1e-12
    support={}
    for mask,rr in [('all',[r for r in ls]),('eligible',[r for r in ls if r['execution_eligible']]),('eligible_rankpass',[r for r in ls if r['execution_eligible'] and r['rank_pass']])]:
        support[mask]={head:score_stats(rr,scores,col) for head,col in HEADS.items()}
    groups={}
    for kind in ['v5_rank','pP_training_rank_half','MRET_training_rank_half']:
        by=defaultdict(list)
        for r in ls:
            s=scores[r['entry_id']];key=r['rank'] if kind=='v5_rank' else 'HIGH' if s['r' if kind.startswith('pP') else 'rM']>=.5 else 'LOW'
            by[key].append(r)
        groups[kind]=[]
        for key,rr in sorted(by.items()):
            known=[r for r in rr if r['known']]
            groups[kind].append({'bucket':key,'N':len(rr),'known_N':len(known),'known_rate':len(known)/len(rr),'R5_N':sum(r['R5'] is True for r in known),'R5_rate':sum(r['R5'] is True for r in known)/len(known) if known else None,'R10_N':sum(r['R10'] is True for r in known),'R10_rate':sum(r['R10'] is True for r in known)/len(known) if known else None,'mean_net_return_ratio':str(mean(D(r['r_net_ratio_decimal']) for r in known)) if known else None})
    result=read(OUT/'V5_RESET20_RESULT.json');wins=[];paths=[];private=[]
    for w in result['windows']:
        if not w['coverage_complete']:continue
        dest=PRIVATE/'runs/V5_RESET20'/w['window_id'];ds=rows(dest/'DECISIONS.jsonl.gz');ts=rows(dest/'TRADES.jsonl.gz');pool=[r for r in ls if r['session'] in w['sessions']]
        caps=capture(pool,ds,ts);money=money_paths(ds,ts,lm)
        wins.append({'window_id':w['window_id'],'status':w['status'],'final_cash':w['final_cash_for_primary'],**caps,'money_paths':{k:v for k,v in money.items() if k!='band_cap_floor_local_cases'}});paths+=money['band_cap_floor_local_cases']
        for d in ds:private.append({'window_id':w['window_id'],**d,'label_evaluation_only':lm[d['entry_id']]})
    write_rows(PRIVATE/'evaluation-only/V5_JOINED_DECISIONS.jsonl.gz',private)
    orig=money_paths(native_ds,native_ts,lm)
    save(OUT/'CAPITAL_DIAGNOSTIC.json',{'schema':'ARK_CAPITAL_DIAGNOSTIC_V1','exact_jst':now(),'unit_note':'Census unique entry; legacy capture reused chain; each reset window reported separately; repeated-window counts are account occurrences not independent market opportunities','original_chain_reused':capture(ls,native_ds,native_ts),'original_money_paths':{k:v for k,v in orig.items() if k!='band_cap_floor_local_cases'},'score_lineage':{'OOF_identity_and_block_verified':True,'primary_quality_raw_score_exact_match':True,'MRET_original_primary_vs_certified_max_delta':mdelta,'MRET_absolute_loss_defense':'INCONCLUSIVE','refit_N':0,'original_AUC_recertifications':0},'new_R_score_support':support,'fixed_buckets':groups,'reset_windows':wins,'local_cap_floor_occurrence_N':len(paths),'local_cap_floor_unique_entry_N':len({r['entry_id'] for r in paths}),'local_cap_floor_labels':{'R5':sum(r['realized_label_diagnostic_only']['R5'] is True for r in {x['entry_id']:x for x in paths}.values()),'R10':sum(r['realized_label_diagnostic_only']['R10'] is True for r in {x['entry_id']:x for x in paths}.values()),'Loser':sum(r['realized_label_diagnostic_only']['Loser'] is True for r in {x['entry_id']:x for x in paths}.values())},'private_money_case_path':'capital_v51_private/evaluation-only/LOCAL_MONEY_PATHS.json','hypothetical_missed_PnL_sum':'NOT_COMPUTED_NOT_RECOVERABLE_WEALTH','candidate_decision':'PENDING_ROOT_ASSESSMENT'})
    save(PRIVATE/'evaluation-only/LOCAL_MONEY_PATHS.json',{'original':orig['band_cap_floor_local_cases'],'reset':paths})
    print({'legacy_capture':capture(ls,native_ds,native_ts)['census']['eligible_rankpass'],'score_AUC':{h:{r:support['eligible'][h][r]['AUROC'] for r in ['R5','R10']} for h in HEADS},'local_cap_floor_unique':len({r['entry_id'] for r in paths})})

if __name__=='__main__':main()
