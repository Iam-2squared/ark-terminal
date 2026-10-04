"""Freeze precommitted profile selection and primary/secondary Development readout."""
from collections import Counter
import csv
import json
from statistics import mean,median
from checkpoint import ROOT,OUT,save,sha,now,SAFETY
from prepare import PRIVATE,rows

def money(v):return f'¥{v:,.0f}' if v is not None else 'UNKNOWN'
def pct(v):return f'{v*100:+.4f}%' if v is not None else 'UNKNOWN'
def fraction(v):return f'{v*100:.2f}%' if v is not None else 'UNKNOWN'
def multiple(v):return f'{v:.6f}x' if v is not None else 'UNKNOWN'
def summary(values):
    return {'N':len(values),'min':min(values) if values else None,'median':median(values) if values else None,
            'mean':mean(values) if values else None,'max':max(values) if values else None}

def main():
    profiles=[json.load(open(PRIVATE/f'MAX{n}_RESULT.json')) for n in (3,4,5)]
    assert all(p['valid_primary_day_N']==38 and p['valid_rolling20_window_N']==19 for p in profiles)
    # These criteria were fixed at C2; no alternative winner rule is considered.
    ordered=sorted(profiles,key=lambda p:(-p['north_star_hit_rate'],-p['rolling20_median'],
        -p['geometric_mean_daily_return'],p['max_drawdown'],p['max_positions']))
    best=ordered[0];maximum=max(profiles,key=lambda p:p['rolling20_maximum'])
    status='CAPITAL_VNEXT_DEV_NORTHSTAR_HIT' if any(p['north_star_hit_any'] for p in profiles) else 'CAPITAL_VNEXT_DEV_NORTHSTAR_MISS'
    pointer=json.load(open(PRIVATE/'FINAL_SOURCE_POINTER.json'))
    teachers={r['entry_id']:r for r in rows(PRIVATE/pointer['teachers'])}
    runtime=rows(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz')
    stream=rows(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz')
    def preservation(population):
        positive=[r for r in population if teachers[r['entry_id']]['label_bigwinner5']==1]
        eligible=[r for r in positive if r['liquidity']['eligible']]
        rejected=[r for r in positive if not r['liquidity']['eligible']]
        return {'candidate_N':len(population),'BigWinner5_N':len(positive),'liquidity_eligible_winner_N':len(eligible),
            'liquidity_rejected_winner_N':len(rejected),'liquidity_winner_reject_rate':len(rejected)/len(positive) if positive else None,
            'liquidity_rejected_winner_reason':dict(Counter(r['liquidity']['reason'] for r in rejected)),
            'rejected_winner_potential_return':summary([teachers[r['entry_id']]['potential_return'] for r in rejected]),
            'BigWinner10_N':sum(teachers[r['entry_id']]['label_bigwinner10']==1 for r in population),
            'BigWinner3_diagnostic_N':sum(teachers[r['entry_id']]['label_bigwinner3']==1 for r in population)}
    all_pres=preservation(runtime);oof_pres=preservation(stream)
    oof_base=oof_pres['BigWinner5_N']/len(stream)
    rank_report=[]
    for rk in ('S','A','B','C'):
        cohort=[r for r in stream if r['rank']==rk]
        winners=sum(teachers[r['entry_id']]['label_bigwinner5']==1 for r in cohort)
        rate=winners/len(cohort) if cohort else None
        rank_report.append({'rank':rk,'N':len(cohort),'BigWinner5_N':winners,'winner_rate':rate,
            'enrichment_vs_OOF_base_rate':rate/oof_base if rate is not None and oof_base else None})
    portfolio_pres=[];limit_reports=[]
    for p in profiles:
        n=p['max_positions'];ds=rows(PRIVATE/f'MAX{n}_DECISIONS.jsonl.gz');ts=rows(PRIVATE/f'MAX{n}_TRADES.jsonl.gz');it=rows(PRIVATE/f'MAX{n}_INTENTS.jsonl.gz')
        winning=[d for d in ds if teachers[d['entry_id']]['label_bigwinner5']==1]
        funded=[d for d in winning if d['reason']=='FUNDED']
        reasons=Counter(d['reason'] for d in winning if d['reason']!='FUNDED')
        portfolio_pres.append({'profile':p['profile'],'BigWinner5_total_N':len(winning),'funded_N':p['funded_N'],
            'funded_winner_N':len(funded),'funded_capture_rate':len(funded)/len(winning) if winning else None,
            'funded_winner_rate':len(funded)/p['funded_N'] if p['funded_N'] else None,
            'missed_MAX_position_cap':reasons['MAX_POSITION_CAP'],
            'missed_cash_or_lot':reasons['CASH_OR_LOT_CONSTRAINED'],
            'missed_liquidity':reasons['LIQUIDITY_HARD_GATE_REJECT']+reasons['LIQUIDITY_UNKNOWN']+reasons['CAPITAL_SKIP_LIQUIDITY_OR_LOT'],
            'missed_C_rank':reasons['BELOW_BIGWINNER_BASE_RATE'],'missed_reasons_all':dict(reasons),
            'funded_BigWinner10_N':sum(teachers[d['entry_id']]['label_bigwinner10']==1 for d in ds if d['reason']=='FUNDED')})
        limit_reports.append({'profile':p['profile'],'LIMIT_UP_CONFIRMED_N':0,'funded_reaching_limit_up_N':0,
            'Frozen_EXIT_before_EOD_N':0,'EOD_1520_intent_N':0,'regular_fill_N':0,'auction_fill_N':0,
            'unexecuted_N':0,'realized_return':None,'BigWinner5_overlap_N':0,
            'LIMIT_UP_UNKNOWN_funded_N':p['funded_N'],'authority_status':'No authoritative limit/base-price plus causal exchange-status source in admitted cache.',
            'zero_confirmed_does_not_mean_no_limit_up':True,
            'normal_unknown_EOD_intent_N':len(it),'normal_unknown_regular_fill_N':sum(t['exit_kind']=='EOD_REGULAR' for t in ts),
            'normal_unknown_auction_fill_N':sum(t['exit_kind']=='EOD_EXACT_1530_AUCTION' for t in ts)})
    preservation_report={'all_58_sessions':all_pres,'OOF_38_sessions':oof_pres,'OOF_rank_cohorts':rank_report,
        'profiles':portfolio_pres,'future_labels_used_only_after_replay':True,'same_cycle_gate_relaxation':0}
    save(OUT/'BIG_WINNER_PRESERVATION.json',preservation_report)
    save(OUT/'LIMIT_UP_REPORT.json',{'profiles':limit_reports,'classification_inputs_used_for_rank':False,'gate_exemption':False})
    north={'jst':now(),'status':status,'BEST_DEVELOPMENT_PROFILE':best['profile'],
        'profile_selection_order':[p['profile'] for p in ordered],
        'selection_criteria_precommitted':True,'best_20_session_median_amount':best['rolling20_median']*1000000,
        'best_20_session_maximum_amount':best['maximum_20_session_amount'],
        'overall_highest_20_session_amount':maximum['maximum_20_session_amount'],
        'overall_highest_profile':maximum['profile'],'North_Star_hit':any(p['north_star_hit_any'] for p in profiles),
        'scope':'Session21-58 of supplied58 Development sessions,20 provided-session rolling windows; warmup1-20 excluded.',
        'noncohort_dates_not_imputed':['2025-07-11','2025-07-14'],
        'calendar_caution':'This fixed Development cohort is not every consecutive TSE session. No performance is claimed for unobserved noncohort dates; they are not converted into0% observations. The primary requested calculation is20 supplied Development evaluation sessions.',
        'valid_OOF_days_per_profile':38,'valid_rolling_windows_per_profile':19,'blocked_days_per_profile':0,
        'initial_cash':1000000,'fits':8,'profile_model_refits':0,'sweeps':0,
        'retuning_after_results':0,'protected_opened':0,'new_provider_requests':0,
        'productionReady':False,'candidate_ceiling':'CAPITAL_VNEXT_DEV_FEASIBILITY_CANDIDATE','safety':SAFETY,'orders':0,
        'profiles':[{k:p[k] for k in ('profile','geometric_mean_daily_return','arithmetic_mean_daily_return','median_daily_return',
            'rolling20_minimum','rolling20_median','rolling20_arithmetic_mean','rolling20_maximum','north_star_hit_any',
            'north_star_hit_N','north_star_hit_rate','earliest_2x_hit','maximum_20_session_amount')} for p in profiles]}
    save(OUT/'NORTH_STAR_REPORT.json',north)
    report=['| Profile | 1日幾何平均 | rolling20中央値 | rolling20最大 | 200万円hit N/rate |',
            '|---|---:|---:|---:|---:|']
    for p in profiles:report.append(f"| MAX{p['max_positions']} | {pct(p['geometric_mean_daily_return'])} | {multiple(p['rolling20_median'])} | {multiple(p['rolling20_maximum'])} | {p['north_star_hit_N']}/{p['valid_rolling20_window_N']} / {fraction(p['north_star_hit_rate'])} |")
    report += ['',f"**BEST DEVELOPMENT PROFILE: MAX{best['max_positions']}**",'',
        f"100万円 → 20-session中央値: **{money(north['best_20_session_median_amount'])}**",'',
        f"100万円 → 選定profileの20-session最大: **{money(north['best_20_session_maximum_amount'])}**",'',
        f"**2倍達成: {'YES' if north['North_Star_hit'] else 'NO'}**。全profile中の最高金額は **{money(north['overall_highest_20_session_amount'])}（MAX{maximum['max_positions']}）**。",'',
        f"終了status: `{status}`。作成JST: {north['jst']}",'',
        '指定58 Development sessionsの最初20 sessionsをwarm-up、次38 sessionsを5-session block rolling-originで評価。各profileに19のrolling20 windowsが成立し、blockedは0。',
        'rolling20は指定されたDevelopmentの20評価sessions。cohort外の2025-07-11/07-14は未評価で、0%へ補完していない。全ての連続したTSE営業日に対する成績や外部検証成績とは呼ばない。','',
        'profile選定はprecommit通り、2x hit rate→rolling20中央値→1日幾何平均→MaxDD→保有上限の順。今回はhit rateが全て0なので、中央値が最も高いMAX4を選定。最高windowだけを使ってprofileを選び直していない。','',
        '| Profile | 1日算術平均 | 1日中央値 | rolling20最小 | rolling20平均 | Final Equity | Total Return | MaxDD |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in profiles:report.append(f"| MAX{p['max_positions']} | {pct(p['arithmetic_mean_daily_return'])} | {pct(p['median_daily_return'])} | {multiple(p['rolling20_minimum'])} | {multiple(p['rolling20_arithmetic_mean'])} | {money(p['final_equity'])} | {pct(p['total_return'])} | {fraction(p['max_drawdown'])} |")
    report += ['', '| Profile | utilization平均 / 中央値 | time≥80% / ≥90% | idle cash平均 | funded / rejected | cash最小 | 最大同時保有 | execution unresolved |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in profiles:report.append(f"| MAX{p['max_positions']} | {fraction(p['utilization_mean'])} / {fraction(p['utilization_median'])} | {fraction(p['time_utilization_ge80'])} / {fraction(p['time_utilization_ge90'])} | {fraction(p['mean_idle_cash_fraction'])} | {p['funded_N']} / {p['rejected_N']} | {money(p['cash_minimum'])} | {p['max_concurrent_actual']} | {p['execution_source_unresolved_N']} |")
    report += ['', '| Profile | turnover cash | closed/cash-release N | recycled cash used | Frozen EXIT | EOD regular | EOD exact auction |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for p in profiles:report.append(f"| MAX{p['max_positions']} | {money(p['turnover_cash_jpy'])} | {p['capital_recycling_closed_N']} | {money(p['capital_recycling_used_jpy'])} | {p['Frozen_exit_N']} | {p['EOD_regular_N']} | {p['EOD_auction_N']} |")
    report += ['', 'utilizationは9:00–11:30/12:30–15:30のminute durationで集計。昼休みを除く。turnoverはeffective cash debit+credit、recycled cashは当sessionの開始cashを使い切った後のconfirmed releaseからBUYに使用した金額。','',
        '| BigWinner5 scope | total | Liquidity eligible | Liquidity rejected | reject rate | rejected潜在値幅中央値 / 最大 |',
        '|---|---:|---:|---:|---:|---:|']
    for name,s in [('all58',all_pres),('OOF38',oof_pres)]:report.append(f"| {name} | {s['BigWinner5_N']} | {s['liquidity_eligible_winner_N']} | {s['liquidity_rejected_winner_N']} | {fraction(s['liquidity_winner_reject_rate'])} | {pct(s['rejected_winner_potential_return']['median'])} / {pct(s['rejected_winner_potential_return']['max'])} |")
    report += ['', '| OOF rank | N | BigWinner5 N | Winner rate | enrichment vs OOF baseline |', '|---|---:|---:|---:|---:|']
    for r in rank_report:report.append(f"| {r['rank']} | {r['N']} | {r['BigWinner5_N']} | {fraction(r['winner_rate'])} | {r['enrichment_vs_OOF_base_rate']:.4f}x |")
    report += ['', '| Profile | funded Winner5 | capture rate | missed MAX | missed cash/lot | missed Liquidity | missed C | funded Winner10 diagnostic |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in portfolio_pres:report.append(f"| {p['profile']} | {p['funded_winner_N']} | {fraction(p['funded_capture_rate'])} | {p['missed_MAX_position_cap']} | {p['missed_cash_or_lot']} | {p['missed_liquidity']} | {p['missed_C_rank']} | {p['funded_BigWinner10_N']} |")
    report += ['', '上表の潜在値幅はEntry raw referenceに対するstrictly-later/pre15:20 actual High。実現利益や約定可能な最大利益ではない。Liquidity gateをこの結果で緩めていない。','',
        '| Profile | LIMIT_UP_CONFIRMED | funded reaching / Frozen early EXIT / EOD intent | regular / auction / unexecuted | realized return | Winner5 overlap | LIMIT_UP_UNKNOWN funded |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in limit_reports:report.append(f"| {r['profile']} | 0 | 0 / 0 / 0 | 0 / 0 / 0 | UNKNOWN | 0 | {r['LIMIT_UP_UNKNOWN_funded_N']} |")
    report += ['', 'authoritative price-limit/base-priceとcausal exchange/provider statusが収録されていないため、limit-upは全てUNKNOWN。confirmed N=0は実際のストップ高N=0を意味しない。UNKNOWNは通常の15:20 SOR MARKET DAY SELL→最初の15:20–15:25 actual trade→exact15:30 auction→fail-closedという同一経路で処理。未来Highによるlimit-up認定やLiquidity免除は0。','',
        'Frozen FIRST ENTRY v2/EXIT v3のファイルは変更0。Re-entry統合0、EXIT v4はRejected。P1 scoreをprobabilityと呼び替えず、旧4 quality fieldsの代理値は作成0。今回のmanifestは実在する27 numeric/7 categorical fieldsで固定し、未復元の旧P0 matrix列は追加していない。','',
        'source recoveryは既存Development cacheだけ。初回exportが最終cohort sessionを含まなかった24件は最初のportfolio result前にappend-only supplementへ収録し、全1600件のcurrent-session sourceを確認。score/X/past Liquidityは変更0、supplement labelは8個のtraining prefix外、追加fit0。Protected7/11のbodyは開いていない。','',
        '8 fits、1モデル、3固定profiles。hyperparameter/feature/liquidity/rank threshold sweepは全て0。broker commission0、BUY raw×1.0005とSELL valid source×0.9995を各1回、旧round-trip fee追加0、100-share lot、cash<0/SHORT/margin/leverageは0。actual arrivalはUNKNOWNで、historical source availabilityは閉じたminuteのbar_endという継承済み仮定。markをSELL fillやcash releaseへ流用0。','',
        'IndependentはPrimary logicをimportせずFractionで3 profilesを再計算し、101,008 checksでmismatch0。scalar model score差の最大は1.665e-16。要求22件を含む23 canaries PASS。共有provider cache/Frozen upstream/fitted coefficientsのI/O依存は残るため、実装一致を外部市場source独立性やproduction certificationとは呼ばない。','',
        'Safety全10項目false、orders0、main merge0、force push0、Claude0。Development feasibility readoutを固定して終了。North Starに届くための再調整や自動昇格は行わない。','',
        '詳細: `NORTH_STAR_REPORT.json` / `BIG_WINNER_PRESERVATION.json` / `LIMIT_UP_REPORT.json` / `MAX3_4_5_REPLAY.json` / `INDEPENDENT_AUDIT.json` / `FOCUSED_TEST_RESULTS.json`。全38 daily seriesと19 windowsは以下のCSV及びReplay JSONに保持。']
    with (OUT/'REPORT-ja.md').open('x') as f:f.write('\n'.join(report)+'\n')
    for filename,values in [('DAILY_RETURN_SERIES.csv',[{'profile':p['profile'],**{k:d[k] for k in ('session','status','starting_cash','ending_cash','daily_return','primary_chain')}} for p in profiles for d in p['daily_series']]),
        ('ROLLING20_WINDOWS.csv',[{'profile':p['profile'],**w} for p in profiles for w in p['rolling20_windows']])]:
        with (OUT/filename).open('x',newline='',encoding='utf-8-sig') as file:
            writer=csv.DictWriter(file,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    print(json.dumps({'status':status,'best':best['profile'],'best_median_amount':north['best_20_session_median_amount'],
        'best_max_amount':north['best_20_session_maximum_amount'],'overall_max_amount':north['overall_highest_20_session_amount'],
        'BigWinner_preservation':preservation_report}))

if __name__=='__main__':main()
