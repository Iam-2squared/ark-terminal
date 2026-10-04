"""Fixed9-run preservation, Movement increment and realizability diagnostics."""
import json,math
from collections import Counter
from statistics import mean,median
from sklearn.metrics import roc_auc_score
from checkpoint import ROOT,OUT,PRIVATE,save,sha,now
from io_data import rows
from movement import quantile

ARMS=('CORE_P5','MOVE_P5','MOVE_DUAL')

def rank_metrics(stream,teacher,liquidity_only=False):
 rr=[r for r in stream if r['entry_minute']<920 and teacher[r['entry_id']]['label_bigwinner5'] is not None
  and (not liquidity_only or r['liquidity']['eligible'])]
 ranked=sorted(rr,key=lambda r:(-r['capital_score'],r['entry_timestamp'],r['symbol']));top=ranked[:math.ceil(.2*len(ranked))]
 positives=sum(teacher[r['entry_id']]['label_bigwinner5'] for r in rr);base=positives/len(rr) if rr else None
 rate=sum(teacher[r['entry_id']]['label_bigwinner5'] for r in top)/len(top) if top else None
 y=[teacher[r['entry_id']]['label_bigwinner5'] for r in rr]
 return {'N':len(rr),'Winner5_N':positives,'baseline_rate':base,
  'P_OOF_AUC':float(roc_auc_score(y,[r['pP'] for r in rr])) if len(set(y))==2 else None,
  'score_OOF_AUC':float(roc_auc_score(y,[r['capital_score'] for r in rr])) if len(set(y))==2 else None,
  'top20_N':len(top),'top20_Winner5_N':sum(teacher[r['entry_id']]['label_bigwinner5'] for r in top),
  'top20_winner_rate':rate,'top20_enrichment':rate/base if base else None,
  'score_ge1_N':sum(r['capital_score']>=1 for r in rr),
  'score_ge1_Winner5_N':sum(r['capital_score']>=1 and teacher[r['entry_id']]['label_bigwinner5']==1 for r in rr)}

def reason_family(reason):
 if reason in ('EXTREME_ILLIQUIDITY_REJECT','LIQUIDITY_UNKNOWN','LIQUIDITY_LOT_CAP_REJECT'):return 'extreme_liquidity'
 if reason=='BELOW_CAPITAL_BASELINE':return 'score_lt1'
 if reason=='MAX_POSITION_CAP':return 'MAX'
 if reason=='CASH_OR_LOT_CONSTRAINED':return 'cash_lot'
 if reason=='CAPITAL_EOD_ENTRY_CUTOFF':return 'EOD_cutoff'
 return 'other'

def main():
 runtime=rows(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz');teacher={r['entry_id']:r for r in rows(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz')}
 streams={arm:rows(PRIVATE/(arm+'_SCORE_STREAM.jsonl.gz')) for arm in ARMS}
 oof=streams['CORE_P5'];allwin=[r for r in runtime if teacher[r['entry_id']]['label_bigwinner5']==1]
 winners=[r for r in oof if teacher[r['entry_id']]['label_bigwinner5']==1]
 def gate_report(ww):
  rejected=[r for r in ww if not r['liquidity']['eligible']];potential=[teacher[r['entry_id']]['potential_return'] for r in rejected]
  return {'Winner5_total_N':len(ww),'extreme_liquidity_eligible_N':sum(r['liquidity']['eligible'] for r in ww),
   'extreme_liquidity_rejected_N':len(rejected),'extreme_liquidity_reject_rate':len(rejected)/len(ww) if ww else None,
   'reject_reasons':dict(Counter(r['liquidity']['reason'] for r in rejected)),
   'rejected_potential_median':median(potential) if potential else None,'rejected_potential_mean':mean(potential) if potential else None,
   'rejected_potential_max':max(potential) if potential else None}
 profiles=[];closed={};fundsets={};results={}
 for arm in ARMS:
  for n in (3,4,5):
   label=f'{arm}_MAX{n}';result=json.loads((PRIVATE/(label+'_RESULT.json')).read_text());results[label]=result
   ds=rows(PRIVATE/(label+'_DECISIONS.jsonl.gz'));tt=rows(PRIVATE/(label+'_TRADES.jsonl.gz'));closed[label]=tt
   funded={d['entry_id'] for d in ds if d['reason']=='FUNDED'};fundsets[label]=funded
   funded_win=[k for k in funded if teacher[k]['label_bigwinner5']==1]
   missed=[d for d in ds if teacher[d['entry_id']]['label_bigwinner5']==1 and d['reason']!='FUNDED']
   families=Counter(reason_family(d['reason']) for d in missed)
   potential10=sum(teacher[k]['label_bigwinner10']==1 for k in funded)
   rr={'profile':label,'arm':arm,'MAX':n,'funded_N':len(funded),'funded_Winner5_N':len(funded_win),
    'funded_capture_rate':len(funded_win)/len(winners),'funded_Winner10_N':potential10,
    'missed':{key:families[key] for key in ('extreme_liquidity','score_lt1','MAX','cash_lot','EOD_cutoff','other')},
    'missed_exact_reasons':dict(Counter(d['reason'] for d in missed)),
    'funded_primary_chain_N':sum(d['reason']=='FUNDED' and d['primary_chain'] for d in ds),
    'capture_includes_post_block_diagnostic_runs':result['primary_origin_unknown_day_N']>0}
   assert rr['funded_Winner5_N']+sum(rr['missed'].values())==len(winners)
   profiles.append(rr)
 preservation={'jst':now(),'ALL58':gate_report(allwin),'OOF38':gate_report(winners),'profiles':profiles,
  'rank_enrichment':{arm:{'all_pre_cutoff':rank_metrics(streams[arm],teacher),'extreme_liquidity_eligible':rank_metrics(streams[arm],teacher,True)} for arm in ARMS},
  'v1_benchmark':{'Winner5_N':170,'liquidity_rejected_Winner5_N':111,'liquidity_reject_rate':111/170,'MAX4_funded_capture_rate':30/170},
  'future_source_filter':False,'same_cycle_liquidity_rescue':False,'productionReady':False}
 save(OUT/'BIGWINNER_PRESERVATION.json',preservation)
 for r in profiles:results[r['profile']]['BigWinner5_funded_capture_rate']=r['funded_capture_rate']
 anatomy=json.loads((OUT/'MOVEMENT_ANATOMY.json').read_text())['stats']['ALL58']['label_bigwinner5']
 movement=[r for r in anatomy if r['feature'].startswith('movement/M') and int(r['feature'].split('/M')[-1])<=12]
 supporting=[r['feature'] for r in movement if r['standardized_difference'] is not None and r['standardized_difference']>=.2 and r['univariate_AUC'] is not None and r['univariate_AUC']>=.55]
 m2=next(r for r in anatomy if r['feature']=='movement/M2')
 effect=bool(m2['standardized_difference'] is not None and m2['standardized_difference']>=.2 and m2['univariate_AUC']>=.55 and len(supporting)>=4)
 A=preservation['rank_enrichment']['CORE_P5']['all_pre_cutoff'];B=preservation['rank_enrichment']['MOVE_P5']['all_pre_cutoff']
 auc_delta=B['P_OOF_AUC']-A['P_OOF_AUC'];enrichment_delta=B['top20_enrichment']-A['top20_enrichment']
 def avg(arm,key):
  values=[results[f'{arm}_MAX{n}'][key] for n in (3,4,5)]
  return mean(values) if all(v is not None for v in values) else None
 delta={key:(avg('MOVE_P5',key)-avg('CORE_P5',key)) if avg('MOVE_P5',key) is not None and avg('CORE_P5',key) is not None else None
  for key in ('BigWinner5_funded_capture_rate','geometric_mean_daily_return','rolling20_median')}
 supported=effect and auc_delta>=.01 and enrichment_delta>=0 and all(v is not None and v>=0 for v in delta.values()) and any(v is not None and v>0 for v in delta.values())
 weak=bool(supporting) and (auc_delta>0 or any(v is not None and v>0 for v in delta.values()))
 signal='SUPPORTED' if supported else 'WEAK' if weak else 'NOT_SUPPORTED'
 incremental=[]
 for n in (3,4,5):
  a=results[f'CORE_P5_MAX{n}'];b=results[f'MOVE_P5_MAX{n}']
  incremental.append({'MAX':n,'ARM_A':{key:a[key] for key in ('geometric_mean_daily_return','rolling20_median','rolling20_maximum','BigWinner5_funded_capture_rate','utilization_mean','blocked_execution_day_N')},
   'ARM_B':{key:b[key] for key in ('geometric_mean_daily_return','rolling20_median','rolling20_maximum','BigWinner5_funded_capture_rate','utilization_mean','blocked_execution_day_N')}})
 save(OUT/'MOVEMENT_HYPOTHESIS_REPORT.json',{'MOVEMENT_CAPACITY_SIGNAL':signal,'effect_supporting_M1_M12':supporting,
  'strict_effect_rule_pass':effect,'M2_effect':m2,'fixed_rule':json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())['movement_signal_rule'],
  'Anatomy':anatomy,'OOF_P_AUC_A':A['P_OOF_AUC'],'OOF_P_AUC_B':B['P_OOF_AUC'],'OOF_P_AUC_delta_B_A':auc_delta,
  'OOF_top20_enrichment_A':A['top20_enrichment'],'OOF_top20_enrichment_B':B['top20_enrichment'],'top20_enrichment_delta':enrichment_delta,
  'mean3MAX_incremental_B_A':delta,'incremental_profiles':incremental,
  'in_sample_only_supported':False,'feature_search':0,'same_cycle_tuning':0,'productionReady':False})
 dual=[]
 for n in (3,4,5):
  entry={}
  for arm in ('MOVE_P5','MOVE_DUAL'):
   label=f'{arm}_MAX{n}';tt=closed[label];ret=[t['net_return'] for t in tt]
   known=[k for k in fundsets[label] if teacher[k]['label_realized_positive'] is not None]
   entry[arm]={'funded_Winner5_N':sum(teacher[k]['label_bigwinner5']==1 for k in fundsets[label]),
    'BigWinner5_capture':results[label]['BigWinner5_funded_capture_rate'],'closed_trade_N':len(tt),
    'closed_realized_positive_N':sum(v>0 for v in ret),'realized_positive_rate':sum(v>0 for v in ret)/len(ret) if ret else None,
    'average_realized_return':mean(ret) if ret else None,'negative_tail_p05':quantile(ret,.05),'minimum_realized_return':min(ret) if ret else None,
    'funded_teacher_R_known_N':len(known),'funded_teacher_R_unknown_N':len(fundsets[label])-len(known),
    **{key:results[label][key] for key in ('geometric_mean_daily_return','rolling20_median','rolling20_maximum','blocked_execution_day_N')}}
  b=fundsets[f'MOVE_P5_MAX{n}'];c=fundsets[f'MOVE_DUAL_MAX{n}']
  dropped=[k for k in b-c if teacher[k]['label_bigwinner5']==1]
  gained=[k for k in c-b if teacher[k]['label_bigwinner5']==1]
  cs={r['entry_id']:r['capital_score'] for r in streams['MOVE_DUAL']}
  dual.append({'MAX':n,**entry,'B_funded_Winners_lost_in_C_N':len(dropped),'C_gained_Winners_N':len(gained),
   'B_Winners_lost_due_C_score_lt1_N':sum(cs[k]<1 for k in dropped),
   'Potential_capture_reduced':entry['MOVE_DUAL']['BigWinner5_capture']<entry['MOVE_P5']['BigWinner5_capture']})
 C=streams['MOVE_DUAL'];known=[r for r in C if r['entry_minute']<920 and teacher[r['entry_id']]['label_realized_positive'] is not None]
 ry=[teacher[r['entry_id']]['label_realized_positive'] for r in known]
 save(OUT/'REALIZABILITY_HEAD_REPORT.json',{'OOF_R_known_N':len(known),'OOF_R_positive_rate':sum(ry)/len(ry),
  'OOF_R_AUC':float(roc_auc_score(ry,[r['pR'] for r in known])),'paired_MAX_comparisons':dual,
  'Head_R_unknown_omitted_from_completed_past_training_only':True,'future_source_availability_runtime_filter':False,
  'returns_scope':'Actual closed trades; unexecuted outcomes remain UNKNOWN. Profile equity/windows obey fail-closed chain rules.',
  'same_cycle_head_rescue':0,'productionReady':False})
 # No authority =>UNKNOWN. Do not relabel future High as limit-up.
 limits=[]
 for arm in ARMS:
  for n in (3,4,5):
   label=f'{arm}_MAX{n}';its=rows(PRIVATE/(label+'_INTENTS.jsonl.gz'));tt=closed[label]
   confirmed={i['entry_id'] for i in its if i['limit_up_status']=='LIMIT_UP_CONFIRMED'}
   cohort=[t for t in tt if t['entry_id'] in confirmed]
   limits.append({'profile':label,'LIMIT_UP_CONFIRMED_N':len(confirmed),'funded_positions_reaching_limit_up_N':len(confirmed),
    'Frozen_EXIT_before_EOD_N':0,'EOD_1520_intent_N':len(confirmed),
    'regular_fill_N':sum(t['exit_kind']=='EOD_REGULAR' for t in cohort),'auction_fill_N':sum(t['exit_kind']=='EOD_EXACT_1530_AUCTION' for t in cohort),
    'unexecuted_N':len(confirmed)-len(cohort),'realized_return':mean(t['net_return'] for t in cohort) if cohort else None,
    'BigWinner5_overlap_N':sum(teacher[k]['label_bigwinner5']==1 for k in confirmed),
    'LIMIT_UP_UNKNOWN_funded_N':results[label]['funded_N']})
 save(OUT/'LIMIT_UP_REPORT.json',{'cohorts':limits,'authority_available_N':0,
  'interpretation':'All limit-up status UNKNOWN. Confirmed0 is not actual limit-up0. No work stop; same ordinary15:20 intent and source-specific fill route.',
  'future_high_classification':False,'liquidity_exception':False,'productionReady':False})
 save(OUT/'ANALYSIS_COMPLETION.json',{'jst':now(),'fixed_runs':9,'Movement_signal':signal,'OOF_BigWinner5_N':len(winners),
  'v2_extreme_Winner_reject_rate':preservation['OOF38']['extreme_liquidity_reject_rate'],
  'result_based_retuning':0,'fits_added':0,'arm_changes':0,'productionReady':False})
 print(json.dumps({'Movement_signal':signal,'OOF_Winner5_N':len(winners),'extreme_Winner_reject_N':preservation['OOF38']['extreme_liquidity_rejected_N'],
  'P_AUC_delta_B_A':auc_delta,'mean3MAX_incremental':delta}))

if __name__=='__main__':main()
