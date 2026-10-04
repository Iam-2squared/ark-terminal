"""D8/D9 evaluation of saved bytes. No policy/runtime/teacher imports or reruns."""
import csv, gzip, json, math, sys
from collections import Counter, defaultdict
from decimal import Decimal as D
from statistics import mean, median
from control import ROOT, WORK, OUT, now, save, sha

PROFILE = 'COUNTERFACTUAL_SLOT_VALUE_V6_MAX3'
PRIVATE = WORK / 'capital_v6_slot_private'
FROZEN = WORK / 'source_main/capital_staircase_v4_private'

def rows(path):
    return [json.loads(line) for line in gzip.open(path, 'rt')]

def csvsave(path, values):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        w = csv.DictWriter(f, list(values[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(values)

def quality(ids, scores, labels, trades):
    ids = sorted(ids)
    values = [labels[i]['potential_return'] for i in ids]
    net = [float(D(trades[i]['credit']) / D(trades[i]['debit']) - 1) for i in ids if i in trades]
    n = len(ids)
    result = {'N':n, 'rank_counts':dict(Counter(scores[i]['rank'] for i in ids)),
              'realized_resolved_N':len(net), 'realized_unresolved_N':n-len(net),
              'realized_mean':mean(net) if net else None,
              'realized_median':median(net) if net else None}
    for key, count in {
        'U2':sum(v>=.02 for v in values), 'U3':sum(v>=.03 for v in values),
        'Medium':sum(.03<=v<.05 for v in values), 'U5':sum(v>=.05 for v in values),
        'U10':sum(v>=.10 for v in values), 'below2':sum(v<.02 for v in values),
        'below3':sum(v<.03 for v in values)}.items():
        result[key+'_N'] = count
        result[key+'_rate'] = count/n if n else None
    for key, count in {'PF1':sum(v>=.01 for v in net), 'positive':sum(v>0 for v in net), 'loser':sum(v<=0 for v in net)}.items():
        result[key+'_N'] = count
        result[key+'_rate'] = count/len(net) if net else None
    result['actual_pnl_jpy'] = float(sum((D(trades[i]['credit'])-D(trades[i]['debit']) for i in ids if i in trades),D(0)))
    return result

def inputs():
    scores = {r['entry_id']:r for r in rows(FROZEN/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')}
    labels = {r['entry_id']:r for r in rows(WORK/'source_main/inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')}
    ds = rows(PRIVATE/f'{PROFILE}_DECISIONS.jsonl.gz')
    ts = {r['entry_id']:r for r in rows(PRIVATE/f'{PROFILE}_TRADES.jsonl.gz')}
    return scores, labels, ds, ts

def d8():
    scores, labels, ds, trades = inputs()
    original = json.loads((OUT/'V5_CONTROL_ORACLE_FREEZE.json').read_text())
    funded = {d['entry_id'] for d in ds if d['reason']=='FUNDED'}
    assert funded == set(trades)
    metrics = {}
    opportunities = []
    false_rows = []
    pairs = []
    fundable = {}
    bad_unique = {}
    for k, expected in [(5,113),(10,47)]:
        ids = {i for i,r in scores.items() if r['admission'] and labels[i]['potential_return']>=k/100}
        assert len(ids)==expected
        counts = Counter(d['reason'] for d in ds if d['entry_id'] in ids)
        f, cap, reserve, cash = [counts.get(key,0) for key in ['FUNDED','MAX_POSITION_CAP','SLOT_RESERVE_REJECT','CASH_OR_LOT_CONSTRAINED']]
        assert f+cap+reserve+cash == expected, counts
        old = original['cohorts'][f'U{k}']
        ceiling = original['oracle']['maximum_feasible_U5'] if k==5 else original['oracle']['maximum_U10_conditional_on_max_U5']
        metrics[f'U{k}'] = {'rank_pass':expected,'funded':f,'conversion':f/expected,'Oracle_feasible':ceiling,
            'Oracle_recovery':f/ceiling,'Oracle_gap':ceiling-f,'MAX3_miss':cap,'reserve_rejected':reserve,
            'Net_Slot_Miss':cap+reserve,'cash_lot':cash,'conservation':f+cap+reserve+cash,
            'v5':old,'delta_vs_v5':{'funded':f-old['funded'],'MAX3_miss':cap-old['MAX3_miss'],
            'reserve_rejected':reserve-old['reserve_reject'],'Net_Slot_Miss':cap+reserve-old['Net_Slot_Miss'],'cash_lot':cash-old['cash_lot']}}
        false_fundable = set()
        bad_funded = set()
        bad_overlap = set()
        for d in ds:
            i = d['entry_id']
            if i not in ids:
                continue
            state = d.get('causal_slot_state')
            occupants = list(state['held'])+state['pending_ids'] if state else d['held_before_batch']
            opportunities.append({'entry_id':i,'session':d['session'],'minute':d['minute'],'cohort':f'U{k}',
                'rank':d['rank'],'reason':d['reason'],'p_accept':d.get('p_accept'),
                'occupancy':d.get('pre_decision_occupancy'),'occupant_ids':occupants,
                'potential_return_evaluation_only':labels[i]['potential_return']})
            if d['reason']=='SLOT_RESERVE_REJECT':
                pending = state['pending_ids']
                min_debit = sum((D(scores[j]['raw_reference'])*D('1.0005')*100 for j in pending+[i]),D(0))
                physical = min_debit <= D(state['cash'])
                if physical:
                    false_fundable.add(i)
                if k==5:
                    false_rows.append({'entry_id':i,'session':d['session'],'minute':d['minute'],'rank':d['rank'],
                        'p_accept':d['p_accept'],'occupancy':d['pre_decision_occupancy'],
                        'cash':state['cash'],'pending_ids':pending,'minimum_joint_one_lot_debit':str(min_debit),
                        'one_lot_physical_fundable':physical,'U5':True,'U10':labels[i]['potential_return']>=.10,
                        'potential_return_evaluation_only':labels[i]['potential_return']})
            if d['reason']=='MAX_POSITION_CAP':
                for j in occupants:
                    potential = labels[j]['potential_return']
                    actual = j in funded
                    if potential<.02:
                        bad_overlap.add(i)
                        if actual:
                            bad_funded.add(i)
                    if k==5 and potential<.05:
                        trade = trades.get(j)
                        net = float(D(trade['credit'])/D(trade['debit'])-1) if trade else None
                        pairs.append({'blocked_U5_entry_id':i,'blocking_entry_id':j,'session':d['session'],
                            'blocked_minute':d['minute'],'held_prior_batch':j in state['held'],
                            'pending_same_batch':j in state['pending_ids'],'blocking_funded':actual,
                            'blocking_below2':potential<.02,'blocking_below5':potential<.05,
                            'blocking_potential_return_evaluation_only':potential,'blocking_realized_net':net,
                            'blocking_realized_loser':net is not None and net<=0,
                            'blocking_entry_minute':scores[j]['entry_minute'],
                            'blocking_release_minute':trade['release_minute'] if trade else None})
        fundable[f'U{k}'] = len(false_fundable)
        bad_unique[f'U{k}'] = {'below2_actual_funded_blocked_unique':len(bad_funded),
            'below2_actual_or_pending_overlap_unique':len(bad_overlap)}
    slots = {str(s):quality({d['entry_id'] for d in ds if d['reason']=='FUNDED' and d['funded_slot']==s},scores,labels,trades) for s in (1,2,3)}
    ranks = {}
    for rank in ('S','A','B','C'):
        candidates = {i for i,r in scores.items() if r['rank']==rank}
        ranks[rank] = {'candidate_N':len(candidates),'actions':dict(Counter(d['reason'] for d in ds if d['rank']==rank)),
                      'funded_quality':quality(funded & candidates,scores,labels,trades)}
    q = quality(funded,scores,labels,trades)
    summary = {'exact_jst':now(),'metrics':metrics,'quality':q,'slot_quality':slots,'rank_actions':ranks,
        'FALSE_RESERVE_U5':metrics['U5']['reserve_rejected'],'FALSE_RESERVE_U5_ONE_LOT_FUNDABLE':fundable['U5'],
        'FALSE_RESERVE_U10_ONE_LOT_FUNDABLE':fundable['U10'],
        'BAD_FILL_BLOCKED_U5':bad_unique['U5']['below2_actual_or_pending_overlap_unique'],
        'BAD_FILL_BLOCKED_U5_ACTUAL_FUNDED':bad_unique['U5']['below2_actual_funded_blocked_unique'],
        'bad_fill_diagnostics':bad_unique,
        'bad_fill_below5_blocked_U5_unique':len({p['blocked_U5_entry_id'] for p in pairs}),
        'realized_loser_blocked_U5_unique':len({p['blocked_U5_entry_id'] for p in pairs if p['blocking_realized_loser']}),
        'oracle':original['oracle'],'Oracle_unavoidable_U5_overlap':9,
        'evaluator_only':True,'test_teacher_generated':0,'new_Oracle_solve':0,'Control_replay':0,'retune':0,
        'definitions_precommit_sha256':sha(OUT/'RECOVERY_EVALUATION_DEFINITIONS_PRECOMMIT.json'),
        'limitations':['False Reserve is a descriptive missed-winner label; no test continuation teacher is generated.',
            'Bad Fill is observed temporal overlap, not unique counterfactual blame. Pending admissions are separated from actual funded occupants.',
            'Frozen Oracle104 relaxes runtime allocation caps/utilization; it is a physical ceiling, not a deployable trading result.']}
    save(OUT/'FALSE_RESERVE_BAD_FILL_ORACLE_GAP.json',summary)
    save(OUT/'SLOT_RANK_QUALITY.json',{'exact_jst':now(),'quality':q,'slots':slots,'ranks':ranks})
    save(OUT/'U5_U10_OPPORTUNITY_LEDGER.json',{'exact_jst':now(),'evaluator_only':True,'rows':opportunities})
    save(OUT/'FALSE_RESERVE_U5_LEDGER.json',{'exact_jst':now(),'evaluator_only':True,'rows':false_rows})
    save(OUT/'BAD_FILL_BLOCKED_U5_PAIRS.json',{'exact_jst':now(),'evaluator_only':True,'rows':pairs})
    print(json.dumps({k:summary[k] for k in ['metrics','quality','FALSE_RESERVE_U5','FALSE_RESERVE_U5_ONE_LOT_FUNDABLE','BAD_FILL_BLOCKED_U5','BAD_FILL_BLOCKED_U5_ACTUAL_FUNDED']}))

def d9():
    result = json.loads((OUT/'MAIN_REPLAY_RESULT.json').read_text())
    control = json.loads((OUT/'V5_CONTROL_ORACLE_FREEZE.json').read_text())['Control']
    daily = result['daily_series']
    assert len(daily)==38 and all(d['status']=='COMPLETE' and d['daily_return'] is not None for d in daily)
    returns = [float(D(d['ending_cash'])/D(d['starting_cash'])-1) for d in daily]
    rolls = [float(D(daily[i+19]['ending_cash'])/D(daily[i]['starting_cash'])) for i in range(19)]
    curves = rows(PRIVATE/f'{PROFILE}_CURVE.jsonl.gz')
    peak = D(1000000)
    dd = D(0)
    for c in curves:
        eq = D(c['equity']);peak = max(peak,eq);dd=max(dd,(peak-eq)/peak)
    economics = {k:result[k] for k in ['utilization_mean','utilization_median','mean_idle_cash_fraction','cash_minimum',
        'turnover_cash_jpy','capital_recycling_used_jpy','capital_recycling_closed_N','funded_N','avg_funded_per_session']}
    economics.update(N=38,daily_geometric=math.expm1(mean(math.log1p(r) for r in returns)),
        daily_arithmetic=mean(returns),daily_median=median(returns),rolling20_N=19,
        rolling20_min=min(rolls),rolling20_mean=mean(rolls),rolling20_median=median(rolls),rolling20_max=max(rolls),
        rolling20_2x_N=sum(r>=2 for r in rolls),final_equity=float(D(daily[-1]['ending_cash'])),
        final_return=float(D(daily[-1]['ending_cash'])/D(1000000)-1),max_drawdown=float(dd),two_x='YES' if any(r>=2 for r in rolls) else 'NO')
    paired = []
    by_day = {d['session']:d for d in control['daily_series']}
    for i,d in enumerate(daily):
        v5 = by_day[d['session']]
        paired.append({'session':d['session'],'starting_equity':d['starting_cash'],'ending_equity':d['ending_cash'],
            'v6_daily_return':returns[i],'v5_daily_return':v5['daily_return'],'paired_daily_delta':returns[i]-v5['daily_return'],
            'v5_ending_equity':v5['ending_cash'],'equity_difference_jpy':float(D(d['ending_cash'])-D(v5['ending_cash'])),
            'cash_minimum':d['cash_min'],'max_concurrent':d['max_concurrent'],'recycled_cash_used':d['recycled_cash_used']})
    csvsave(OUT/'ASSET_CURVE_DAILY.csv',paired)
    csvsave(OUT/'ROLLING20.csv',[dict(result['rolling20_windows'][i],v5_multiple=control['rolling20_windows'][i]['growth_multiple'],
        paired_multiple_delta=rolls[i]-control['rolling20_windows'][i]['growth_multiple']) for i in range(19)])
    deltas = [r['paired_daily_delta'] for r in paired]
    economics['paired_v5'] = {'N':38,'daily_delta_mean':mean(deltas),'daily_delta_median':median(deltas),
        'positive_delta_days':sum(d>0 for d in deltas),'negative_delta_days':sum(d<0 for d in deltas),'equal_delta_days':sum(d==0 for d in deltas),
        'final_equity_delta_jpy':economics['final_equity']-control['final_equity']}
    comparison = {'v5_daily_geometric':control['geometric_mean_daily_return'],'v5_rolling20_median':control['rolling20_median'],
        'v5_rolling20_max':control['rolling20_maximum'],'v5_final_equity':control['final_equity'],'v5_max_drawdown':control['max_drawdown'],
        'historical_best_CORE_P5_MAX3_Liquidity_OFF_daily_geometric':.010959626199879651,'historical_best_final_equity_approx':1513160}
    save(OUT/'ECONOMIC_RESULT.json',{'exact_jst':now(),'economics':economics,'comparison':comparison,'development_only':True,'main_replay':1,'retune':0})
    print(json.dumps(economics))

if __name__ == '__main__':
    {'D8':d8,'D9':d9}[sys.argv[1]]()
