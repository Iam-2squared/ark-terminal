"""Evaluation after fixed scoring/replay. Outcomes never enter decision code."""
from common import *
from collections import Counter,defaultdict
from decimal import Decimal as D
from statistics import mean,median
import math,csv
from sklearn.metrics import roc_auc_score,brier_score_loss
from execution import valid_market
BUCKETS=('<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10')
def bucket(v):
 for threshold,label in zip((.01,.02,.03,.04,.05,.10),BUCKETS):
  if v<threshold:return label
 return '>=10'
def q05(v):
 v=sorted(v)
 if not v:return None
 x=(len(v)-1)*.05;i=math.floor(x);j=math.ceil(x);return v[i]+(v[j]-v[i])*(x-i)
def quality(trades):
 r=[t['net_return'] for t in trades];n=len(r)
 out={'realized_resolved_N':n,'realized_mean':mean(r) if r else None,'realized_median':median(r) if r else None,'worst':min(r) if r else None,'p05':q05(r),'actual_pnl_jpy':float(sum((D(t['pnl']) for t in trades),D(0)))}
 for name,fn in [('PF1',lambda x:x>=.01),('positive',lambda x:x>0),('exact_zero',lambda x:x==0),('loss0',lambda x:x<=0),('tail1',lambda x:x<=-.01),('tail3',lambda x:x<=-.03)]:
  count=sum(fn(x) for x in r);out[name+'_N']=count;out[name+'_rate']=count/n if n else None
 return out
def main():
 assert (OUT/'SCORE_FREEZE.json').exists() and (OUT/'MAIN_REPLAY_RESULT.json').exists()
 stream=rows(PRIVATE/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz');sm={r['entry_id']:r for r in stream};tt={r['entry_id']:r for r in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')};book=source_books()
 sets={f'U{k}':{key for key in sm if tt[key]['potential_return']>=k/100} for k in (2,3,5,10)};sets['Medium']=sets['U3']-sets['U5'];assert [len(sets[k]) for k in ('U2','U3','Medium','U5','U10')]==[432,297,127,170,67]
 buckets={label:{key for key in sm if bucket(tt[key]['potential_return'])==label} for label in BUCKETS};low2=buckets['<1']|buckets['1-<2'];low3=low2|buckets['2-<3'];old52={r['entry_id'] for r in rows(SRC/'capital_liquidity_off_private/OLD_REJECT52_LEDGER.jsonl.gz')};assert len(old52)==52
 def evaluate(path,profile):
  ds=rows(path/f'{profile}_DECISIONS.jsonl.gz');ts=rows(path/f'{profile}_TRADES.jsonl.gz');cs=rows(path/f'{profile}_CURVE.jsonl.gz');it=rows(path/f'{profile}_INTENTS.jsonl.gz');econ=json.loads((path/f'{profile}_RESULT.json').read_text())
  dm={d['entry_id']:d for d in ds};tm={t['entry_id']:t for t in ts};funded={d['entry_id'] for d in ds if d['reason']=='FUNDED'};n=len(funded)
  q=quality(ts);q.update(funded_N=n,realized_missing_N=n-len(ts))
  for label,ids in [('below1',buckets['<1']),('one_to_below2',buckets['1-<2']),('below2',low2),('below3',low3)]:q[label+'_N']=len(ids&funded);q[label+'_rate']=len(ids&funded)/n if n else None
  cap={k:{'total_N':len(ids),'funded_N':len(ids&funded),'capture_rate':len(ids&funded)/len(ids)} for k,ids in sets.items()}
  br={label:{'total_candidate_N':len(ids),'funded_N':len(ids&funded),'capture_rate':len(ids&funded)/len(ids) if ids else None,**quality([tm[k] for k in ids&funded if k in tm])} for label,ids in buckets.items()}
  no_trade=Counter();stale=Counter();bounds=set(range(545,691,5))|set(range(755,926,5));actual_minutes={key:{r['minute'] for r in book[key]['market'] if r.get('session')==sm[key]['session'] and valid_market(r)} for key in funded}
  for f in cs:
   t=f['minute']
   for key,known in f['known_marks'].items():
    if (540<=t<690 or 750<=t<930) and known<t:stale[key]+=1
    if t in bounds and sm[key]['entry_minute']<=t-5 and not any(m in actual_minutes[key] for m in range(t-5,t)):no_trade[key]+=1
  def cohort(ids):
   ids=ids&funded;tr=[tm[k] for k in ids if k in tm]
   return {'funded_N':len(ids),'unresolved_N':len(ids)-len(tr),**quality(tr),'U3_N':len(ids&sets['U3']),'U5_N':len(ids&sets['U5']),'U10_N':len(ids&sets['U10']),'no_trade_MTM_windows_N':sum(no_trade[k] for k in ids),'stale_mark_minute_snapshots_N':sum(stale[k] for k in ids),'frozen_EXIT_N':sum(t['exit_kind']=='FROZEN_EXIT_V3' for t in tr),'EOD_regular_N':sum(t['exit_kind']=='EOD_REGULAR' for t in tr),'EOD_auction_N':sum(t['exit_kind']=='EOD_EXACT_1530_AUCTION' for t in tr)}
  liquid={s:cohort({key for key in sm if sm[key]['liquidity']['reason']==s}) for s in ('LIQUIDITY_ELIGIBLE','EXTREME_ILLIQUIDITY_REJECT','LIQUIDITY_UNKNOWN')}
  reasons={k:dict(Counter(dm[key]['reason'] for key in ids-funded)) for k,ids in sets.items()}
  if path==PRIVATE:gzwrite(PRIVATE/'FUNDED_QUALITY_LEDGER.jsonl.gz',[{'entry_id':key,'teacher':tt[key],'decision':dm[key],'trade':tm.get(key),'historical_liquidity':sm[key]['liquidity'],'no_trade_MTM_windows_N':no_trade[key]} for key in sorted(funded)])
  return {'economic':econ,'quality':q,'capture':cap,'buckets':br,'missed_reasons':reasons,'liquidity_cohorts':liquid,'old_reject52':{'total_N':52,'v4_admission_eligible_pre1520_N':sum(sm[k]['admission'] and sm[k]['entry_minute']<920 for k in old52),'funded':cohort(old52),'missed_reasons':dict(Counter(dm[k]['reason'] for k in old52-funded))},'liquidity_reason_reject_N':sum('LIQUIDITY' in d['reason'] for d in ds)},ds
 mainr,ds=evaluate(PRIVATE,PROFILE);control,_=evaluate(SRC/'capital_liquidity_off_private','LIQUIDITY_OFF_MAX3')
 assert control['quality']['funded_N']==167 and control['capture']['U5']['funded_N']==45 and control['capture']['Medium']['funded_N']==28 and control['capture']['U10']['funded_N']==26 and control['quality']['below2_N']==70 and control['quality']['below3_N']==94
 q,c=mainr['quality'],control['quality'];a,b=mainr['capture'],control['capture'];scores={'S1':a['U5']['capture_rate']>b['U5']['capture_rate'],'S2':a['Medium']['capture_rate']>b['Medium']['capture_rate'],'S3':q['below2_rate']<c['below2_rate'],'S4':q['below3_rate']<c['below3_rate'],'S5':q['loss0_rate']<c['loss0_rate'],'S6':q['PF1_rate']>c['PF1_rate']}
 selection='UPWARD_SELECTION_IMPROVED' if all(scores[k] for k in ('S1','S2','S3')) else 'UPWARD_SELECTION_WORSE' if not any(scores[k] for k in ('S1','S2','S3')) else 'UPWARD_SELECTION_MIXED'
 em,ec=mainr['economic'],control['economic'];eb=[em['geometric_mean_daily_return']>ec['geometric_mean_daily_return'],em['rolling20_median']>ec['rolling20_median']];economic='CAPITAL_V4_IMPROVES' if all(eb) else 'CAPITAL_V4_WORSE' if not any(eb) else 'CAPITAL_V4_MIXED'
 paired=[]
 for x,y in zip(em['daily_series'],ec['daily_series']):
  assert x['session']==y['session'];paired.append({'session':x['session'],'control':y['daily_return'],'v4':x['daily_return'],'delta':x['daily_return']-y['daily_return']})
 dd=[r['delta'] for r in paired];pd={'positive':sum(v>0 for v in dd),'negative':sum(v<0 for v in dd),'equal':sum(v==0 for v in dd),'mean':mean(dd),'median':median(dd),'max_gain':max(dd),'max_deterioration':min(dd)}
 batches=defaultdict(list)
 for d in ds:batches[d['session'],d['minute']].append(d)
 regret={};pairs=[];heldledger=[]
 conditions={'selected_below2_missed_U3':lambda x,y:x<.02 and y>=.03,'selected_below2_missed_U5':lambda x,y:x<.02 and y>=.05,'selected_below3_missed_U5':lambda x,y:x<.03 and y>=.05,'selected_lower_bucket_higher_missed':lambda x,y:BUCKETS.index(bucket(x))<BUCKETS.index(bucket(y))}
 for scope in ('all_missed','eligible_MAX3_only'):
  for name,condition in conditions.items():
   pp=[];batchN=0
   for (day,minute),batch in batches.items():
    selected=[d for d in batch if d['reason']=='FUNDED'];missed=[d for d in batch if d['reason']!='FUNDED' and (scope=='all_missed' or d['reason']=='MAX_POSITION_CAP')]
    match=[{'category':name,'scope':scope,'session':day,'minute':minute,'selected_entry_id':x['entry_id'],'missed_entry_id':y['entry_id'],'missed_reason':y['reason']} for x in selected for y in missed if condition(tt[x['entry_id']]['potential_return'],tt[y['entry_id']]['potential_return'])]
    batchN+=bool(match);pp+=match
   regret[f'{scope}/{name}']={'batch_N':batchN,'selected_N':len({r['selected_entry_id'] for r in pp}),'missed_N':len({r['missed_entry_id'] for r in pp}),'pair_N':len(pp)};pairs+=pp
 for (day,minute),batch in batches.items():
  eligible=[d for d in batch if d['reason'] in ('FUNDED','CASH_OR_LOT_CONSTRAINED','MAX_POSITION_CAP')]
  for ordinal,d in enumerate(eligible):
   if d['reason']=='MAX_POSITION_CAP' and d.get('held_before_batch') and ordinal<3 and d['entry_id'] in sets['U3']:
    heldledger.append({'entry_id':d['entry_id'],'session':day,'minute':minute,'held_entry_ids':d['held_before_batch'],'batch_eligible_ordinal':ordinal+1,'U5':d['entry_id'] in sets['U5'],'U10':d['entry_id'] in sets['U10'],'reason':'HELD_SLOT_BLOCKED_WINNER'})
 regret.update(missed_U5_due_MAX3_N=mainr['missed_reasons']['U5'].get('MAX_POSITION_CAP',0),missed_U10_due_MAX3_N=mainr['missed_reasons']['U10'].get('MAX_POSITION_CAP',0),HELD_SLOT_BLOCKED_WINNER={'U3_N':len(heldledger),'U5_N':sum(r['U5'] for r in heldledger),'U10_N':sum(r['U10'] for r in heldledger),'definition':'MAX3-rejected U3 within first3 eligible batch candidates when older positions occupied slots; removing held slots would permit capacity selection, without modeling fills/replacement.'})
 gzwrite(PRIVATE/'SLOT_REGRET_PAIRS.jsonl.gz',pairs);gzwrite(PRIVATE/'HELD_SLOT_BLOCKED_WINNER.jsonl.gz',heldledger)
 report={'JST':now(),'main':mainr,'control_read_only':control,'scoreboard':{k:'PASS' if v else 'FAIL' for k,v in scores.items()},'selection_status':selection,'economic_status':economic,'NORTH_STAR_HIT':em['north_star_hit_any'],'paired_daily_delta':pd,'slot_regret':regret,'control_replays':0,'evaluation_only':True,'Exposure':EXPOSURE,'productionReady':False,'Safety':SAFETY}
 save(OUT/'SELECTION_ANALYSIS.json',report)
 with (OUT/'PAIRED_DAILY_RETURNS.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(paired[0]));w.writeheader();w.writerows(paired)
 with (OUT/'ROLLING20.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['profile','start_session','end_session','growth_multiple','amount_from_1m','hit']);w.writeheader()
  for p,result in [('Control',ec),('v4',em)]:w.writerows({'profile':p,**r} for r in result['rolling20_windows'])
 heads={}
 for h in ('H2','H3','H5'):
  threshold=int(h[1:])/100;records=[{'id':r['entry_id'],'p':r['p'+h[1:]],'base':r['base'+h[1:]],'block':r['block'],'y':int(tt[r['entry_id']]['potential_return']>=threshold)} for r in stream]
  def diagnose(v):
   y=[r['y'] for r in v];p=[r['p'] for r in v];rate=mean(y);top=sorted(v,key=lambda r:(-r['p'],r['id']))[:math.ceil(len(v)*.2)];tr=mean(r['y'] for r in top)
   return {'N':len(v),'ROC_AUC':float(roc_auc_score(y,p)) if len(set(y))==2 else None,'Brier':float(brier_score_loss(y,p)),'observed_base_rate':rate,'training_base_rate_mean':mean(r['base'] for r in v),'top20_N':len(top),'top20_observed_rate':tr,'top20_enrichment':tr/rate if rate else None}
  ordered=sorted(records,key=lambda r:(-r['p'],r['id']));dec=[]
  for i in range(10):
   v=ordered[len(ordered)*i//10:len(ordered)*(i+1)//10];dec.append({'decile':i+1,'highest_first':True,'N':len(v),'mean_probability':mean(r['p'] for r in v),'observed_rate':mean(r['y'] for r in v)})
  cross={f'U{k}':float(roc_auc_score([int(r['entry_id'] in sets[f'U{k}']) for r in stream],[r['p'+h[1:]] for r in stream])) for k in (2,3,5,10)}
  heads[h]={**diagnose(records),'deciles':dec,'blocks':{str(i):diagnose([r for r in records if r['block']==i]) for i in range(1,9)},'cross_target_AUC':cross}
 ordered=sorted(stream,key=lambda r:(-r['ML'],r['entry_id']));top=ordered[:math.ceil(len(stream)*.2)];topids={r['entry_id'] for r in top}
 ml={'cross_target_AUC':{f'U{k}':float(roc_auc_score([int(r['entry_id'] in sets[f'U{k}']) for r in stream],[r['ML'] for r in stream])) for k in (2,3,5,10)},'top20_N':len(top),'top20_rates':{k:len(topids&ids)/len(topids) for k,ids in sets.items()},'top20_below2_contamination':len(topids&low2)/len(topids)}
 save(OUT/'HEAD_DIAGNOSTICS.json',{'JST':now(),'heads':heads,'ML':ml,'new_H2_fits':8,'H3_H5_new_fits':0,'same_cycle_changes_after_results':0})
 checkpoint('U7_SELECTION_BUCKET_AND_SLOT_REGRET','SELECTION_ECONOMIC_RESULTS_FIXED',{'selection_status':selection,'economic_status':economic,'scoreboard':report['scoreboard'],'main_quality':q,'capture':a,'slot_regret':regret})
 print(json.dumps({'selection_status':selection,'economic_status':economic,'scoreboard':report['scoreboard'],'funded_N':q['funded_N'],'capture':a,'below2':q['below2_rate'],'loser':q['loss0_rate']}),flush=True)
if __name__=='__main__':main()
