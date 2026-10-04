"""Paired reports from fixed outputs; no replay, fit, feature or gate changes."""
import csv,json
from statistics import mean,median
from checkpoint import ROOT,OUT,PRIVATE,V2,save,sha,now,git,EXPOSURE,SAFETY

def main():
 control=json.loads((V2/'CORE_P5_MAX3_RESULT.json').read_text())
 off=json.loads((PRIVATE/'LIQUIDITY_OFF_MAX3_RESULT.json').read_text())
 cohort=json.loads((OUT/'NEWLY_FUNDED_THIN_COHORT.json').read_text())
 preservation=json.loads((OUT/'BIGWINNER_PRESERVATION.json').read_text())
 independent=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())
 tests=json.loads((OUT/'FOCUSED_TEST_RESULTS.json').read_text())
 assert independent['status']==tests['status']=='PASS'
 same_sessions=[d['session'] for d in control['daily_series']]==[d['session'] for d in off['daily_series']]
 assert same_sessions and len(off['daily_series'])==38
 complete=off['valid_primary_day_N']==38 and control['valid_primary_day_N']==38
 if not complete:status='CAPITAL_MAX3_LIQUIDITY_OFF_MEASUREMENT_BLOCKED'
 else:
  improve_day=off['geometric_mean_daily_return']>control['geometric_mean_daily_return']
  improve_month=off['rolling20_median']>control['rolling20_median']
  suffix='IMPROVES' if improve_day and improve_month else 'MIXED' if improve_day or improve_month else 'WORSE'
  status='CAPITAL_MAX3_LIQUIDITY_OFF_'+suffix
 values={
  'daily_geometric':(control['geometric_mean_daily_return'],off['geometric_mean_daily_return']),
  'rolling20_median':(control['rolling20_median'],off['rolling20_median']),
  'rolling20_maximum':(control['rolling20_maximum'],off['rolling20_maximum']),
  '2x_hit_rate':(control['north_star_hit_rate'],off['north_star_hit_rate']),
  'final_equity_jpy':(control['final_equity'],off['final_equity']),
  'MaxDD':(control['max_drawdown'],off['max_drawdown']),
  'utilization':(control['utilization_mean'],off['utilization_mean']),
  'BigWinner5_capture':(42/170,preservation['BigWinner5_capture_rate']),
  'liquidity_Winner_reject':(52/170,0.0)}
 paired={k:{'control':a,'liquidity_OFF':b,'delta':b-a if a is not None and b is not None else None} for k,(a,b) in values.items()}
 daily=[]
 for a,b in zip(control['daily_series'],off['daily_series']):
  delta=b['daily_return']-a['daily_return'] if a['daily_return'] is not None and b['daily_return'] is not None else None
  daily.append({'session':a['session'],'control_daily_return':a['daily_return'],'OFF_daily_return':b['daily_return'],
   'delta_day':delta,'OFF_status':b['status'],'OFF_primary_chain':b['primary_chain']})
 deltas=[d['delta_day'] for d in daily if d['delta_day'] is not None]
 delta_stats={'valid_paired_day_N':len(deltas),'positive_day_N':sum(x>0 for x in deltas),'negative_day_N':sum(x<0 for x in deltas),
  'equal_day_N':sum(x==0 for x in deltas),'median_delta':median(deltas) if deltas else None,
  'mean_delta':mean(deltas) if deltas else None,'maximum_gain':max(deltas) if deltas else None,'maximum_deterioration':min(deltas) if deltas else None}
 thin=cohort['newly_funded_historical_liquidity_reject_or_unknown'];new=cohort['LIQUIDITY_OFF_NEWLY_FUNDED'];old52=preservation['old_reject52_funded']
 report={'jst':now(),'repo':'Iam-2squared/ark-terminal','branch':git('branch','--show-current'),'basis_head':git('rev-parse','HEAD'),
  'status':status,'NORTH_STAR_HIT':off['north_star_hit_any'],'north_star_hit_N':off['north_star_hit_N'],'north_star_hit_rate':off['north_star_hit_rate'],
  'earliest_2x':off['earliest_2x_hit'],'control':'CORE_P5_MAX3','control_head':'c27413bd681ce2cb5587fa4e692526ca97590a0a',
  'counterfactual':'LIQUIDITY_OFF_MAX3','paired38_complete':complete,'comparison':paired,'paired_daily_delta':delta_stats,
  'OFF_daily_arithmetic_mean':off['arithmetic_mean_daily_return'],'OFF_daily_median':off['median_daily_return'],
  'rolling20':{k:off[k] for k in ('valid_rolling20_window_N','rolling20_minimum','rolling20_arithmetic_mean','rolling20_median','rolling20_maximum','maximum_20_session_amount')},
  'median20_amount_jpy':1000000*off['rolling20_median'] if off['rolling20_median'] is not None else None,
  'maximum20_window':max(off['rolling20_windows'],key=lambda w:w['growth_multiple']) if off['rolling20_windows'] else None,
  'BigWinner5_funded_N':preservation['BigWinner5_funded_N'],'BigWinner5_capture_rate':preservation['BigWinner5_capture_rate'],
  'old_reject52_score_eligible_N':preservation['old_reject52_score_eligible_N'],'old_reject52_funded_Winner5_N':old52['BigWinner5_N'],
  'old_reject52_realized_mean':old52['realized_return_mean'],'old_reject52_realized_pnl_jpy':old52['actual_realized_pnl_jpy'],
  'newly_funded_all_N':new['N'],'newly_funded_all_realized_mean':new['realized_return_mean'],
  'new_historical_thin_or_unknown_N':thin['N'],'new_thin_realized_mean':thin['realized_return_mean'],
  'new_thin_EOD_unexecuted_N':thin['EOD_unexecuted_N'],'all_EOD_unexecuted_N':off['execution_source_unresolved_N'],
  'blocked_day_N':off['blocked_execution_day_N'],'independent_checks':independent['checks_N'],'independent_mismatch':independent['mismatch_N'],
  'canaries_passed':tests['passed_N'],'new_fits':0,'measurement_replays':1,'deterministic_verifications':1,'independent_verifications':1,
  'control_replays':0,'MAX4_MAX5_replays':0,'new_provider_requests':0,'result_based_retuning':0,
  'score_hash':off['score_stream_sha256'],'exposure':EXPOSURE,'safety':SAFETY,'orders':0,
  'calendar_caution':'rolling20 is20 supplied Development evaluation sessions; no opening or0% imputation of noncohort2025-07-11/07-14. The19 overlapping windows are not independent samples.',
  'execution_size_limit':'Historical prints support reference price/time under the unchanged v2 execution contract; removing liquidity capacity does not establish executable depth for uncapped position quantities.',
  'next_direction':'Freeze this counterfactual result and STOP. MAX3 ONLY remains routine research policy. No new gate, rescue, model, promotion or Protected/OOS access.'}
 save(OUT/'PAIRED_COMPARISON.json',{'jst':report['jst'],'status':status,'paired38_complete':complete,'comparison':paired,'daily_delta':delta_stats,'days':daily})
 save(OUT/'NORTH_STAR_REPORT.json',report)
 with (OUT/'PAIRED_DAILY_RETURNS.csv').open('x',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(daily[0]));writer.writeheader();writer.writerows(daily)
 with (OUT/'ROLLING20_WINDOWS.csv').open('x',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=('profile','start_session','end_session','growth_multiple','amount_from_1m','hit'));writer.writeheader()
  for profile,result in (('CONTROL_CORE_P5_MAX3',control),('LIQUIDITY_OFF_MAX3',off)):
   for window in result['rolling20_windows']:writer.writerow({'profile':profile,**window})
 def pct(x):return 'UNAVAILABLE' if x is None else f'{100*x:+.4f}%'
 def val(x,mode):
  if x is None:return 'UNAVAILABLE'
  return f'¥{x:,.0f}' if mode=='JPY' else f'{x:.6f}x' if mode=='x' else f'{100*x:.4f}%'
 def delta(x,mode):
  if x is None:return 'UNAVAILABLE'
  return f'{x:+,.0f}円' if mode=='JPY' else f'{x:+.6f}x' if mode=='x' else f'{100*x:+.4f}pp'
 lines=['# MAX3 Liquidity OFF Result','','| Metric | Control | Liquidity OFF | Delta |','|---|---:|---:|---:|']
 modes={'rolling20_median':'x','rolling20_maximum':'x','final_equity_jpy':'JPY'}
 for key,v in paired.items():
  mode=modes.get(key,'%');lines.append(f"| {key} | {val(v['control'],mode)} | {val(v['liquidity_OFF'],mode)} | {delta(v['delta'],mode)} |")
 lines+=['',f"1日幾何平均: **{pct(off['geometric_mean_daily_return'])}**",'',
  f"100万円 → 20日中央値: **{val(report['median20_amount_jpy'],'JPY')}**",'',
  f"100万円 → 20日最大: **{val(off['maximum_20_session_amount'],'JPY')}**",'',
  f"200万円到達: **{'YES' if off['north_star_hit_any'] else 'NO' if off['north_star_hit_any'] is False else 'MEASUREMENT_BLOCKED'}**。hit {off['north_star_hit_N']}/{off['valid_rolling20_window_N']}。",'',
  f"BigWinner5 capture: **{preservation['BigWinner5_funded_N']}/170 = {100*preservation['BigWinner5_capture_rate']:.4f}%**",'',
  f"旧Liquidity reject52件: score eligible **{preservation['old_reject52_score_eligible_N']}件**、実際に回収したWinner **{old52['N']}件**。",'',
  f"薄商い新規funded（historical veto/unknown）**{thin['N']}件**、平均実現return **{pct(thin['realized_return_mean'])}**。",'',
  f"EOD unexecuted: **{off['execution_source_unresolved_N']}**。判断: **{status.rsplit('_',1)[-1] if complete else 'MEASUREMENT_BLOCKED'}**。",'',
  f"終了status: `{status}` / `NORTH_STAR_HIT={off['north_star_hit_any']}`。JST: {report['jst']}。",'',
  '指定38 sessionsのpaired比較。rolling20は指定Development評価sessionsであり、連続する全TSE営業日とは呼ばない。cohort外2025-07-11/07-14を開封・0%補完していない。19区間は重複する。', '',
  '| OFF measurement | value |','|---|---:|',
  f"| valid days / blocked | {off['valid_primary_day_N']} / {off['blocked_execution_day_N']} |",
  f"| daily arithmetic mean / median | {pct(off['arithmetic_mean_daily_return'])} / {pct(off['median_daily_return'])} |",
  f"| rolling20 valid N | {off['valid_rolling20_window_N']} |",
  f"| rolling20 min / mean / median / max | {val(off['rolling20_minimum'],'x')} / {val(off['rolling20_arithmetic_mean'],'x')} / {val(off['rolling20_median'],'x')} / {val(off['rolling20_maximum'],'x')} |",
  f"| 2x N / rate / earliest | {off['north_star_hit_N']} / {val(off['north_star_hit_rate'],'%')} / {off['earliest_2x_hit']} |",
  f"| max20 window | {report['maximum20_window']} |",'',
  '| paired daily delta | value |','|---|---:|']
 for k,v in delta_stats.items():lines.append(f'| {k} | {v if k.endswith("_N") else delta(v,"%")} |')
 lines+=['','Liquidity理由のcandidate/lot-cap rejectは0。score>=1 threshold、candidate equity caps、dynamic target utilization、water-fill、100-share lot、MAX3、MTM/EXIT/EOD/accountingは固定。', '',
  '| Winner preservation | Control | OFF |','|---|---:|---:|',
  f"| Winner5 funded/capture | 42 / {100*42/170:.4f}% | {preservation['BigWinner5_funded_N']} / {100*preservation['BigWinner5_capture_rate']:.4f}% |",
  f"| Winner10 funded | 17 | {preservation['BigWinner10_funded_N']} |",
  f"| Liquidity Winner reject | 52 | 0 |",
  f"| score<1 missed | 34 | {preservation['missed_score_lt1_N']} |",
  f"| MAX missed | 38 | {preservation['missed_MAX3_N']} |",
  f"| cash/lot missed | 4 | {preservation['missed_cash_lot_N']} |",
  f"| Entry cutoff missed | 0 | {preservation['missed_Entry_cutoff_N']} |",'',
  f"新規funded Winner5は{preservation['newly_funded_Winner5_N']}件、Control funded Winner5のdropは{preservation['control_Winner5_dropped_N']}件。回収11件をそのままnet capture改善とはしない。",'',
  '| old Liquidity-rejected Winner52 cohort | N | score eligible | funded Winner5 | funded Winner10 | realized mean | realized median | actual PnL |','|---|---:|---:|---:|---:|---:|---:|---:|']
 for label,item in [('TOTAL',{'N':52,'score_eligible_N':preservation['old_reject52_score_eligible_N'],'funded':old52}),*preservation['old_reject52_by_historical_status'].items()]:
  f=item['funded'];lines.append(f"| {label} | {item['N']} | {item['score_eligible_N']} | {f['BigWinner5_N']} | {f['BigWinner10_N']} | {pct(f['realized_return_mean'])} | {pct(f['realized_return_median'])} | {val(f['actual_realized_pnl_jpy'],'JPY')} |")
 lines+=['',f"未回収52 cohortのreasons: {preservation['old_reject52_missed_reasons']}。潜在Winnerラベルはevaluation専用。",'',
  '| newly-funded cohort | N | mean | median | positive rate | Winner5/10 | worst / p05 | Frozen / EOD regular / auction / unexecuted | no-trade5m | min historical coverage | prior median Va min / p25 / median / p75 / max |',
  '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
 groups=[('ALL newly funded',new),('Historical veto/unknown',thin),*cohort['newly_funded_status_cohorts'].items()]
 for label,c in groups:
  va=c['prior_daily_trading_value_jpy'];lines.append(f"| {label} | {c['N']} | {pct(c['realized_return_mean'])} | {pct(c['realized_return_median'])} | {val(c['positive_rate'],'%')} | {c['BigWinner5_N']}/{c['BigWinner10_N']} | {pct(c['worst_realized_return'])} / {pct(c['p05_realized_return'])} | {c['Frozen_EXIT_N']} / {c['EOD_regular_N']} / {c['EOD_auction_N']} / {c['EOD_unexecuted_N']} | {c['no_trade_MTM_event_N']} | {val(c['minimum_historical_active_coverage'],'%')} | {' / '.join(val(va[k],'JPY') for k in ('min','p25','median','p75','max'))} |")
 lines+=['',f"funded entry identity: {cohort['funded_entry_identity_counts']}。ALL newly fundedのうちhistorical liquidity eligibleも含まれるため、薄商いsubsetを別表にした。",'',
  'no-trade MTMはEntry後の完了5m windowにactual printがなく、Positionが残る場合のvaluation保持回数。fill/cash releaseではない。cohortごとのminute snapshotとsource lineageはprivate ledgerへ保存。', '',
  f"独立監査: {independent['checks_N']:,}項目、mismatch={independent['mismatch_N']}。canary {tests['passed_N']}/{tests['tests_N']} PASS。score hash `{off['score_stream_sha256']}`。新fit0、model/feature追加0、Control replay0、MAX4/MAX5 replay0、provider requests0、retune0。",'',
  'Frozen Entry/EXITおよび旧v1/v2 Evidenceは変更0。新MAX3 policyは`docs/policies/CAPITAL_MAX_CONCURRENT_3_RESEARCH_POLICY_V1.md`。MAX3は最大同時保有3銘柄で、3等分ではない。', '',
  '独立実装はPrimary ranking/allocation/replayをimportしない。固定score/models・Frozen upstream・保存source IOは共有しており、外部市場sourceによる独立検証ではない。actual-arrival metadataはUNKNOWNで、v2のcompleted-minute availability仮定を維持。limit-up authorityもUNKNOWNのまま通常EOD routeを使用。', '',
  'Liquidity capを外した数量について、historical printのprice/time Evidenceは市場depthや実数量の約定保証を示さない。Development counterfactualであり、production安全性や外部OOSを示さない。', '',
  cohort['attribution_limit'], '',
  'Safety全false。orders=0、main merge=0、force push=0。このsingle resultを固定してSTOP。Liquidity threshold/capを同cycle内で作り直さない。']
 with (OUT/'REPORT-ja.md').open('x') as f:f.write('\n'.join(lines)+'\n')
 print(json.dumps({'status':status,'NORTH_STAR_HIT':off['north_star_hit_any'],'paired_daily_delta':delta_stats,
  'daily_geometric':off['geometric_mean_daily_return'],'median20_amount':report['median20_amount_jpy'],'max20_amount':off['maximum_20_session_amount']}),flush=True)

if __name__=='__main__':main()
