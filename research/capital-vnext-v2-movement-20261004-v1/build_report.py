"""Final North-Star/selection readout, exact-series exports and Japanese report."""
import csv,json
from statistics import mean
from pathlib import Path
from checkpoint import ROOT,OUT,PRIVATE,save,sha,now,SAFETY,EXPOSURE,git

ARMS=('CORE_P5','MOVE_P5','MOVE_DUAL')
def pct(v,d=4):return 'UNKNOWN' if v is None else f'{v*100:+.{d}f}%'
def percent(v,d=2):return 'UNKNOWN' if v is None else f'{v*100:.{d}f}%'
def multiple(v):return 'UNKNOWN' if v is None else f'{v:.6f}x'
def yen(v):return 'UNKNOWN' if v is None else f'¥{v:,.0f}'
def delta_pct(a,b,d=4):return 'UNKNOWN' if a is None or b is None else f'{(b-a)*100:+.{d}f}pp'

def selection(p):
 return (-p['north_star_hit_rate'],-p['rolling20_median'],-p['geometric_mean_daily_return'],p['max_drawdown'],
  -p['BigWinner5_funded_capture_rate'],-p['utilization_mean'],p['max_positions'],ARMS.index(p['arm']))

def main():
 independent=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text());canary=json.loads((OUT/'FOCUSED_TEST_RESULTS.json').read_text())
 integrity=independent['mismatch_N']==0 and independent['status']=='PASS' and canary['fail_N']==0
 preservation=json.loads((OUT/'BIGWINNER_PRESERVATION.json').read_text());capture={r['profile']:r for r in preservation['profiles']}
 movement=json.loads((OUT/'MOVEMENT_HYPOTHESIS_REPORT.json').read_text());dual=json.loads((OUT/'REALIZABILITY_HEAD_REPORT.json').read_text())
 profiles=json.loads((OUT/'NINE_PORTFOLIO_REPLAYS.json').read_text())['profiles']
 for p in profiles:p['BigWinner5_funded_capture_rate']=capture[p['profile']]['funded_capture_rate']
 candidates=sorted((p for p in profiles if p['valid_rolling20_window_N']>0),key=selection);best=candidates[0] if candidates else None
 v1report=json.loads((ROOT/'docs/evidence/capital-bigwinner-one-shot-20261004-v1/NORTH_STAR_REPORT.json').read_text())
 v1=next(p for p in v1report['profiles'] if p['profile']==v1report['BEST_DEVELOPMENT_PROFILE'])
 hit=any(p['north_star_hit_any'] is True for p in profiles) if best else None
 if not integrity:status='CAPITAL_VNEXT_V2_CONTRACT_FAIL'
 elif best is None:status='CAPITAL_VNEXT_V2_MEASUREMENT_BLOCKED'
 elif hit:status='CAPITAL_VNEXT_V2_DEV_NORTHSTAR_HIT'
 else:
  old=(v1['north_star_hit_rate'],v1['rolling20_median'],v1['geometric_mean_daily_return'])
  new=(best['north_star_hit_rate'],best['rolling20_median'],best['geometric_mean_daily_return'])
  status='CAPITAL_VNEXT_V2_DEV_IMPROVED_BUT_MISS' if new>old else 'CAPITAL_VNEXT_V2_DEV_NO_IMPROVEMENT'
 overall=max((p for p in profiles if p['rolling20_maximum'] is not None),key=lambda p:p['rolling20_maximum'],default=None)
 comparison={
  'daily_geometric':{'v1':v1['geometric_mean_daily_return'],'v2':best['geometric_mean_daily_return'] if best else None},
  'rolling20_median':{'v1':v1['rolling20_median'],'v2':best['rolling20_median'] if best else None},
  'rolling20_maximum':{'v1':v1['rolling20_maximum'],'v2':best['rolling20_maximum'] if best else None},
  '2x_hit_rate':{'v1':v1['north_star_hit_rate'],'v2':best['north_star_hit_rate'] if best else None},
  'utilization':{'v1':v1['utilization_mean'],'v2':best['utilization_mean'] if best else None},
  'BigWinner_capture':{'v1':30/170,'v2':best['BigWinner5_funded_capture_rate'] if best else None},
  'Liquidity_Winner_reject':{'v1':111/170,'v2':preservation['OOF38']['extreme_liquidity_reject_rate']}}
 for row in comparison.values():row['delta']=row['v2']-row['v1'] if row['v2'] is not None else None
 report={'jst':now(),'basis_head':git('rev-parse','HEAD'),'status':status,'BEST_V2':best['profile'] if best else None,
  'scope':'Session21-58 of fixed58 Development sessions;20 supplied evaluation-session rolling windows; warmup1-20 excluded.',
  'initial_cash':1000000,'profiles':profiles,'selection_order':[p['profile'] for p in candidates],
  'selection_rule':json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())['selection'],
  'selected_profile_daily_geometric':best['geometric_mean_daily_return'] if best else None,
  'selected_profile_median_amount':1000000*best['rolling20_median'] if best else None,
  'selected_profile_maximum_amount':best['maximum_20_session_amount'] if best else None,
  'North_star_hit':hit,'North_star_hit_rate':best['north_star_hit_rate'] if best else None,
  'earliest_2x_hit':min((w for p in profiles for w in p['rolling20_windows'] if w['hit']),key=lambda w:(w['end_session'],w['start_session']),default=None),
  'overall_highest_20_session_amount':overall['maximum_20_session_amount'] if overall else None,
  'overall_highest_profile':overall['profile'] if overall else None,
  'v1_comparison':comparison,'Movement_capacity_signal':movement['MOVEMENT_CAPACITY_SIGNAL'],
  'model_fits':24,'unique_primary_portfolio_runs':9,'deterministic_verification_runs':9,'independent_portfolio_runs':9,
  'profile_refits':0,'within_block_refits':0,'sweeps':0,'result_based_retuning':0,'v1_replays':0,
  'blocked_execution_days_by_profile':{p['profile']:p['blocked_execution_day_N'] for p in profiles},
  'independent_checks':independent['checks_N'],'independent_mismatch':independent['mismatch_N'],
  'canaries_passed':canary['passed_N'],'exposure':EXPOSURE,'orders':0,'safety':SAFETY,'productionReady':False,
  'calendar_caution':'This is20 supplied Development evaluation sessions. Noncohort2025-07-11/07-14 are not filled with0% or opened; no all-consecutive-exchange-session claim.',
  'candidate_ceiling':'Development feasibility only; no automatic promotion or production claim.'}
 save(OUT/'NORTH_STAR_REPORT.json',report)
 save(OUT/'V1_V2_COMPARISON.json',{'v1_best':v1['profile'],'v2_best':report['BEST_V2'],'comparison':comparison,
  'v1_evidence_head':'a56b5d1762c602be415c600550ffc8e5c98711bf','v1_replay':0,
  'same38_sessions_and19_windows':all(p['valid_primary_day_N']==38 and p['valid_rolling20_window_N']==19 for p in profiles),
  'matched_MAX4_CORE_capture':capture['CORE_P5_MAX4']['funded_capture_rate'],'v1_MAX4_capture':30/170,
  'causal_attribution_limit':'CORE vs v1 combines Extreme Veto,5% capacity and water-fill. No water-fill-OFF arm; individual component contribution is not isolated.',
  'same_cycle_tuning':0})
 with (OUT/'DAILY_RETURN_SERIES.csv').open('x',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['profile','session','starting_cash','ending_cash','daily_return','status','primary_chain']);writer.writeheader()
  for p in profiles:
   for d in p['daily_series']:writer.writerow({'profile':p['profile'],**{k:d[k] for k in writer.fieldnames if k!='profile'}})
 with (OUT/'ROLLING20_WINDOWS.csv').open('x',encoding='utf-8-sig',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=['profile','start_session','end_session','growth_multiple','amount_from_1m','hit']);writer.writeheader()
  for p in profiles:
   for w in p['rolling20_windows']:writer.writerow({'profile':p['profile'],**w})
 lines=['| Arm / Profile | 1日幾何平均 | 20日中央値 | 20日最大 | 200万円 hit N/rate |',
  '|---|---:|---:|---:|---:|']
 for p in profiles:lines.append(f"| {p['profile']} | {pct(p['geometric_mean_daily_return'])} | {multiple(p['rolling20_median'])} | {multiple(p['rolling20_maximum'])} | {p['north_star_hit_N']}/{p['valid_rolling20_window_N']} / {percent(p['north_star_hit_rate'])} |")
 lines+=['',f"**BEST V2: {report['BEST_V2'] or 'MEASUREMENT_BLOCKED'}**",'',
  f"1日幾何平均: **{pct(report['selected_profile_daily_geometric'])}**",'',
  f"100万円 → 20日中央値: **{yen(report['selected_profile_median_amount'])}**",'',
  f"100万円 → 20日最大: **{yen(report['selected_profile_maximum_amount'])}**",'',
  f"2倍達成: **{'YES' if hit else 'NO' if hit is False else 'UNKNOWN'}**。2倍hit rate: **{percent(report['North_star_hit_rate'])}**。",'',
  f"終了status: `{status}`。JST: {report['jst']}。",'',
  f"v1比: 1日幾何平均 {delta_pct(comparison['daily_geometric']['v1'],comparison['daily_geometric']['v2'])}、rolling20中央値 {comparison['rolling20_median']['delta']:+.6f}x。" if best else 'v1比: measurement blockedのためUNKNOWN。', '',
  '| Metric | v1 best MAX4 | v2 best | delta |','|---|---:|---:|---:|']
 for key,label in [('daily_geometric','daily geometric'),('rolling20_median','rolling20 median'),('rolling20_maximum','rolling20 max'),('2x_hit_rate','2x hit rate'),('utilization','utilization'),('BigWinner_capture','BigWinner capture'),('Liquidity_Winner_reject','Liquidity Winner reject')]:
  a,b=comparison[key]['v1'],comparison[key]['v2']
  if key.startswith('rolling20'):
   av,bv=multiple(a),multiple(b);dv='UNKNOWN' if b is None else f'{b-a:+.6f}x'
  else:av,bv=percent(a,4),percent(b,4);dv=delta_pct(a,b)
  lines.append(f'| {label} | {av} | {bv} | {dv} |')
 lines+=['',f"指定58 Development sessions、最初20 warm-up、次38を5-session rolling-originで評価。全9 runsのvalid days={','.join(str(p['valid_primary_day_N']) for p in profiles)}、valid rolling windows={','.join(str(p['valid_rolling20_window_N']) for p in profiles)}、blocked={','.join(str(p['blocked_execution_day_N']) for p in profiles)}。",'',
  'rolling20は指定Developmentの20評価sessions。cohort外の2025-07-11/07-14は未評価で、0%へ補完していない。全ての連続TSE営業日や外部OOSの成績とは呼ばない。重複する19区間は独立標本ではない。', '',
  'v1の正式negative Evidenceは変更0・再Replay0。v1→COREの差にはExtreme Veto・5% capacity・water-fillが同時に入るため、個々の寄与は分離していない。', '',
  '| Profile | rolling20 N | min | mean | median | max | 2x N/rate | earliest2x | max amount |',
  '|---|---:|---:|---:|---:|---:|---:|---|---:|']
 for p in profiles:lines.append(f"| {p['profile']} | {p['valid_rolling20_window_N']} | {multiple(p['rolling20_minimum'])} | {multiple(p['rolling20_arithmetic_mean'])} | {multiple(p['rolling20_median'])} | {multiple(p['rolling20_maximum'])} | {p['north_star_hit_N']} / {percent(p['north_star_hit_rate'])} | {p['earliest_2x_hit'] or 'NONE'} | {yen(p['maximum_20_session_amount'])} |")
 lines+=['','**BigWinner Preservation**','',
  '| Scope | BigWinner5 | Liquidity eligible | Extreme/UNKNOWN reject | reject rate | reject潜在 median / mean / max |',
  '|---|---:|---:|---:|---:|---:|']
 for name in ('ALL58','OOF38'):
  g=preservation[name];lines.append(f"| {name} | {g['Winner5_total_N']} | {g['extreme_liquidity_eligible_N']} | {g['extreme_liquidity_rejected_N']} | {percent(g['extreme_liquidity_reject_rate'])} | {pct(g['rejected_potential_median'],2)} / {pct(g['rejected_potential_mean'],2)} / {pct(g['rejected_potential_max'],2)} |")
 lines+=['','| Profile | funded Winner5 / capture | extreme liquidity | score<1 | MAX | cash/lot | EOD cutoff | Winner10 diagnostic |',
  '|---|---:|---:|---:|---:|---:|---:|---:|']
 for p in preservation['profiles']:
  m=p['missed'];lines.append(f"| {p['profile']} | {p['funded_Winner5_N']} / {percent(p['funded_capture_rate'])} | {m['extreme_liquidity']} | {m['score_lt1']} | {m['MAX']} | {m['cash_lot']} | {m['EOD_cutoff']} | {p['funded_Winner10_N']} |")
 lines+=['','潜在値幅はstrictly-later/pre15:20 actual High/raw Entry比。約定可能な最大利益やrealized PnLではない。Liquidity v2の20%/5%/5% capは変更0。OOF reject52件はExtreme Veto51件とsupport UNKNOWN1件。', '',
  '**Movement Hypothesis**','',f"MOVEMENT_CAPACITY_SIGNAL: **{movement['MOVEMENT_CAPACITY_SIGNAL']}**",'',
  '| Feature | Winner5 N / mean / median | non-Winner5 N / mean / median | p25/p75 Winner | p25/p75 non | standardized difference | AUC |',
  '|---|---:|---:|---:|---:|---:|---:|']
 names=json.loads((OUT/'FEATURE_MANIFEST.json').read_text())['movement_numeric']
 for m in movement['Anatomy']:
  key=m['feature'].split('/')[-1]
  if key not in names:continue
  a,b=m['positive'],m['negative']
  def value(x):return 'UNKNOWN' if x is None else f'{x:.4f}'
  lines.append(f"| {key} {names[key]} | {a['N']} / {value(a['mean'])} / {value(a['median'])} | {b['N']} / {value(b['mean'])} / {value(b['median'])} | {value(a['p25'])}/{value(a['p75'])} | {value(b['p25'])}/{value(b['p75'])} | {value(m['standardized_difference'])} | {value(m['univariate_AUC'])} |")
 lines+=['',f"OOF P-AUC: CORE={movement['OOF_P_AUC_A']:.6f}、MOVE={movement['OOF_P_AUC_B']:.6f}、差={movement['OOF_P_AUC_delta_B_A']:+.6f}。top20% enrichment: CORE={movement['OOF_top20_enrichment_A']:.4f}x、MOVE={movement['OOF_top20_enrichment_B']:.4f}x。",'',
  'モデルはAnatomy前に固定した27 core numeric+M1–M16/I1–I3・7 categoricalのまま。UNKNOWN indicatorを残し、Anatomy後のfield追加/削除0。全featureのN/mean/median/p25/p75/標準化差/AUC/5 quantile bins、Winner10及びOOF38診断はMOVEMENT_ANATOMY.jsonに保存。', '',
  '| MAX | ARM-A capture / daily geom / median20 | ARM-B capture / daily geom / median20 |',
  '|---|---:|---:|']
 for row in movement['incremental_profiles']:
  a,b=row['ARM_A'],row['ARM_B'];lines.append(f"| {row['MAX']} | {percent(a['BigWinner5_funded_capture_rate'])} / {pct(a['geometric_mean_daily_return'])} / {multiple(a['rolling20_median'])} | {percent(b['BigWinner5_funded_capture_rate'])} / {pct(b['geometric_mean_daily_return'])} / {multiple(b['rolling20_median'])} |")
 lines+=['','Movement追加はOOF potentialの判別と平均captureを改善したが、同じMAXのdaily/rolling20をCOREより下げた。事前のSUPPORTED条件を満たさず、WEAKで固定した。', '',
  '**Realizability Head**','',f"OOF Head R: known N={dual['OOF_R_known_N']}、positive rate={percent(dual['OOF_R_positive_rate'])}、AUC={dual['OOF_R_AUC']:.6f}。",'',
  '| MAX / arm | Winner5 capture | realized positive rate | avg realized return | p05 / min return | daily geom | median20 / max20 |',
  '|---|---:|---:|---:|---:|---:|---:|']
 for row in dual['paired_MAX_comparisons']:
  for arm in ('MOVE_P5','MOVE_DUAL'):
   r=row[arm];lines.append(f"| MAX{row['MAX']} / {arm} | {percent(r['BigWinner5_capture'])} | {percent(r['realized_positive_rate'])} | {pct(r['average_realized_return'])} | {pct(r['negative_tail_p05'],2)} / {pct(r['minimum_realized_return'],2)} | {pct(r['geometric_mean_daily_return'])} | {multiple(r['rolling20_median'])} / {multiple(r['rolling20_maximum'])} |")
 lines+=['','| MAX | BでfundしたWinnerをCで失ったN | Cで新たにfundしたWinner N | lossのうちC score<1 |', '|---|---:|---:|---:|']
 for r in dual['paired_MAX_comparisons']:lines.append(f"| {r['MAX']} | {r['B_funded_Winners_lost_in_C_N']} | {r['C_gained_Winners_N']} | {r['B_Winners_lost_due_C_score_lt1_N']} |")
 lines+=['','Head R追加は各MAXのdaily geomとrolling20中央値をMOVE_P5比で改善したが、potential Winner5 captureを全MAXで減らした。MAX4/5ではrolling20最大も低下。単純なpositive rate/平均trade returnの改善とPortfolio改善は同義ではない。funded R unknownは全profile0、全候補のR unknown40件（cutoff22、valid EOD fill無し18）はUNKNOWNを維持し、runtime filterへ使っていない。', '',
  '**Secondary Audit**','',
  '| Profile | daily arithmetic / median | Final Equity | total return | MaxDD | util mean / median | time>=80 / >=90 | cash min | max concurrent |',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
 for p in profiles:lines.append(f"| {p['profile']} | {pct(p['arithmetic_mean_daily_return'])} / {pct(p['median_daily_return'])} | {yen(p['final_equity'])} | {pct(p['total_return'],2)} | {percent(p['max_drawdown'])} | {percent(p['utilization_mean'])} / {percent(p['utilization_median'])} | {percent(p['time_utilization_ge80'])} / {percent(p['time_utilization_ge90'])} | {yen(p['cash_minimum'])} | {p['max_concurrent_actual']} |")
 lines+=['','| Profile | funded/rejected | Frozen EXIT | EOD regular/auction/unresolved | water-fill lots / funded positions | turnover | recycled cash used | idle cash |',
  '|---|---:|---:|---:|---:|---:|---:|---:|']
 for p in profiles:lines.append(f"| {p['profile']} | {p['funded_N']}/{p['rejected_N']} | {p['Frozen_exit_N']} | {p['EOD_regular_N']}/{p['EOD_auction_N']}/{p['execution_source_unresolved_N']} | {p['water_fill_lots_N']} / {p['water_fill_funded_N']} | {yen(p['turnover_cash_jpy'])} | {yen(p['capital_recycling_used_jpy'])} | {percent(p['mean_idle_cash_fraction'])} |")
 lines+=['','**Limit-Up Cohort**','',
  '| Profile | confirmed/reaching | Frozen before EOD | 15:20 intent | regular/auction/unexecuted | realized return | Winner overlap | UNKNOWN funded |',
  '|---|---:|---:|---:|---:|---:|---:|---:|']
 limit=json.loads((OUT/'LIMIT_UP_REPORT.json').read_text())
 for p in limit['cohorts']:lines.append(f"| {p['profile']} | {p['LIMIT_UP_CONFIRMED_N']}/{p['funded_positions_reaching_limit_up_N']} | {p['Frozen_EXIT_before_EOD_N']} | {p['EOD_1520_intent_N']} | {p['regular_fill_N']}/{p['auction_fill_N']}/{p['unexecuted_N']} | UNKNOWN | {p['BigWinner5_overlap_N']} | {p['LIMIT_UP_UNKNOWN_funded_N']} |")
 lines+=['','authoritative price-limit/base/statusが既存sourceに無いため全funded positionはLIMIT_UP_UNKNOWN。confirmed0は実際のストップ高0を意味しない。UNKNOWNでも通常の15:20 SOR MARKET DAY intent→最初の15:20–15:25 actual trade→valid exact15:30 auction→fail-closedを維持した。未来Highによる認定0、Liquidity exception0。', '',
  f"Independent: **{independent['checks_N']:,} checks、mismatch {independent['mismatch_N']}**。Primary ranking/allocation/model/Movement実装をimportせず、Fractionで9 runsのcash/equity/BUY/SELL/marks/quantityを再計算。scalar score最大差={independent['max_scalar_probability_abs_difference']:.3e}。canary **{canary['passed_N']}/{canary['tests_N']} PASS**（要求30件を含む）。",'',
  '共有provider aggregate/Frozen upstream/fitted coefficientsのI/O依存は残る。実装一致を独立外部source検証やproduction certificationとは呼ばない。actual source arrivalはUNKNOWNで、closed-minute bar_endという継承済みhistorical availability仮定を使用。', '',
  'BUY raw×1.0005、SELL valid source×0.9995を各1回、commission0、旧roundtrip fee追加0、100-share lot、LONG cash-only。no-tradeではsame-session last actual markを保持し、SELL fill/cash releaseへ流用0。candidate/liquidity capsはBUY費用込みcash debitへ保守的に適用。', '',
  '24 unique rolling fits、3 fixed arms×3 MAX=9測定runs。検証として同じ9 runsをdeterministic再実行し、別実装でも9 runsを照合した。追加model fit・profile refit・新arm・hyperparameter/feature/threshold sweep・result-based rescueはすべて0。v1及びFrozen Entry/EXIT変更0、Re-entry統合0、EXIT v4はRejected。', '',
  'Source recoveryは既存79 Development datesのみ、新provider要求0・Protected body open0。Daily Va=NoneはUNKNOWNのまま扱い、価格/feature proxy作成0。初回materializationのnull parser停止はsource等値audit前段で修正し、attempt Evidenceをappend-only保存。policy/manifestは変更していない。', '',
  'Safety全10項目false、orders0、main merge0、force push0、Claude0。North-Star未達を固定して終了し、このwork内で再調整や自動昇格を行わない。', '',
  '全342 daily rowsと171 rolling-window rowsはDAILY_RETURN_SERIES.csv / ROLLING20_WINDOWS.csv。model hashes / source hashes / checkpoint actual receipts及びprivate replay記録を保持。']
 with (OUT/'REPORT-ja.md').open('x') as f:f.write('\n'.join(lines)+'\n')
 print(json.dumps({'status':status,'BEST_V2':report['BEST_V2'],'daily_geometric':report['selected_profile_daily_geometric'],
  'median_amount':report['selected_profile_median_amount'],'maximum_amount':report['selected_profile_maximum_amount'],
  'hit_any':hit,'hit_rate':report['North_star_hit_rate'],'v1_daily_delta_pp':comparison['daily_geometric']['delta']*100 if best else None}))

if __name__=='__main__':main()
