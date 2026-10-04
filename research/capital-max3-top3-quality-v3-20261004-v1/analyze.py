"""Post-fit evaluation-only selection/slot/head/thin diagnostics; no design edits."""
from collections import Counter,defaultdict
from decimal import Decimal as D
from statistics import mean,median
import math,json,csv
import numpy as np
from sklearn.metrics import roc_auc_score,brier_score_loss
from checkpoint import *
from io_data import rows,books,gzwrite
from quality import PROFILES
from execution import valid_market

def quantile(v,p):
 v=sorted(v)
 if not v:return None
 pt=(len(v)-1)*p;i=math.floor(pt);j=math.ceil(pt);return v[i]+(v[j]-v[i])*(pt-i)
def stats(v):
 vv=[float(x) for x in v if x is not None]
 return {'N':len(vv),'missing_N':len(v)-len(vv),'mean':mean(vv) if vv else None,'median':median(vv) if vv else None,'p05':quantile(vv,.05),'min':min(vv) if vv else None,'max':max(vv) if vv else None}
def bucket(value):
 if value is None:return 'UNKNOWN'
 for threshold,name in [(.01,'<1'),(.02,'1-<2'),(.03,'2-<3'),(.04,'3-<4'),(.05,'4-<5'),(.10,'5-<10')]:
  if value<threshold:return name
 return '>=10'
def main():
 ss=rows(PRIVATE/'QUALITY_V3_SCORE_STREAM.jsonl.gz');sm={r['entry_id']:r for r in ss};tt={r['entry_id']:r for r in rows(V2/'TEACHERS_EVALUATION.jsonl.gz')};bb=books()
 ups={k:{r['entry_id'] for r in ss if tt[r['entry_id']][lab]==1} for k,lab in [('U3','label_bigwinner3'),('U5','label_bigwinner5'),('U10','label_bigwinner10')]};ups['Medium']=ups['U3']-ups['U5']
 assert [len(ups[k]) for k in ('U3','U5','U10','Medium')]==[297,170,67,127]
 old52={r['entry_id'] for r in rows(ROOT.parent/'capital_liquidity_off_private/OLD_REJECT52_LEDGER.jsonl.gz')};assert len(old52)==52
 buckets={k:{r['entry_id'] for r in ss if bucket(tt[r['entry_id']]['potential_return'])==k} for k in ('<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10','UNKNOWN')}
 below2=buckets['<1']|buckets['1-<2'];below3=below2|buckets['2-<3'];all_report={}
 def evaluate(profile,p,diagnostic=False):
  ds=rows(p/(profile+'_DECISIONS.jsonl.gz'));ts=rows(p/(profile+'_TRADES.jsonl.gz'));cs=rows(p/(profile+'_CURVE.jsonl.gz'));it=rows(p/(profile+'_INTENTS.jsonl.gz'));result=json.loads((p/(profile+'_RESULT.json')).read_text())
  dm={r['entry_id']:r for r in ds};tm={r['entry_id']:r for r in ts};im={r['entry_id']:r for r in it};funded={r['entry_id'] for r in ds if r['reason']=='FUNDED'}
  real=[t['net_return'] for t in ts];n=len(real)
  quality={'funded_N':len(funded),'realized_resolved_N':n,'realized_missing_N':len(funded)-n,'realized_mean':mean(real) if real else None,'realized_median':median(real) if real else None,'worst_realized_return':min(real) if real else None,'p05_realized_return':quantile(real,.05)}
  for name,cond in [('PF1',lambda v:v>=.01),('positive',lambda v:v>0),('loss0',lambda v:v<=0),('tail1',lambda v:v<=-.01),('tail3',lambda v:v<=-.03)]:
   count=sum(cond(v) for v in real);quality[name+'_N']=count;quality[name+'_rate']=count/n if n else None
  quality.update(PF1_gap_to_100pct=1-quality['PF1_rate'] if n else None,below2_N=len(funded&below2),below2_rate=len(funded&below2)/len(funded) if funded else None,below3_N=len(funded&below3),below3_rate=len(funded&below3)/len(funded) if funded else None)
  capture={k:{'total_N':len(ids),'funded_N':len(funded&ids),'capture_rate':len(funded&ids)/len(ids)} for k,ids in ups.items()}
  no_trade=Counter();stale=Counter();boundaries=set(range(545,691,5))|set(range(755,926,5));minutes={key:{r['minute'] for r in bb[key]['market'] if r.get('session')==sm[key]['session'] and valid_market(r)} for key in funded}
  for f in cs:
   t=f['minute']
   for key,known in f['known_marks'].items():
    if (540<=t<690 or 750<=t<930) and known<t:stale[key]+=1
    if t in boundaries and sm[key]['entry_minute']<=t-5 and not any(m in minutes[key] for m in range(t-5,t)):no_trade[key]+=1
  def cohort(keys):
   keys=set(keys);closed=[tm[k] for k in sorted(keys) if k in tm];vv=[t['net_return'] for t in closed];n=len(vv)
   q={'N':len(keys),'resolved_N':n,'unresolved_N':len(keys)-n,'realized_mean':mean(vv) if vv else None,'realized_median':median(vv) if vv else None,'worst':min(vv) if vv else None,'p05':quantile(vv,.05),'actual_pnl_jpy':float(sum((D(t['pnl']) for t in closed),D(0))),'PF1_N':sum(v>=.01 for v in vv),'loss0_N':sum(v<=0 for v in vv),'tail1_N':sum(v<=-.01 for v in vv),'U3_N':len(keys&ups['U3']),'U5_N':len(keys&ups['U5']),'U10_N':len(keys&ups['U10']),'no_trade_MTM_N':sum(no_trade[k] for k in keys),'stale_mark_minute_snapshots':sum(stale[k] for k in keys),'Frozen_EXIT_N':sum(t['exit_kind']=='FROZEN_EXIT_V3' for t in closed),'EOD_regular_N':sum(t['exit_kind']=='EOD_REGULAR' for t in closed),'EOD_auction_N':sum(t['exit_kind']=='EOD_EXACT_1530_AUCTION' for t in closed),'EOD_unexecuted_N':sum(k in im and k not in tm for k in keys),'historical_coverage':stats([sm[k]['liquidity']['median_coverage'] for k in keys]),'historical_trading_value':stats([sm[k]['liquidity']['median_value'] for k in keys])}
   for k in ('PF1','loss0','tail1'):q[k+'_rate']=q[k+'_N']/n if n else None
   return q
  br={}
  for name,ids in buckets.items():
   closed=[tm[k]['net_return'] for k in funded&ids if k in tm];cn=len(closed)
   br[name]={'candidate_N':len(ids),'funded_N':len(funded&ids),'funded_rate':len(funded&ids)/len(ids) if ids else None,'realized_resolved_N':cn,'realized_mean':mean(closed) if cn else None,'realized_median':median(closed) if cn else None,'PF1_rate':sum(v>=.01 for v in closed)/cn if cn else None,'loss0_rate':sum(v<=0 for v in closed)/cn if cn else None}
  groups={status:cohort({k for k in funded if sm[k]['liquidity']['reason']==status}) for status in ('LIQUIDITY_ELIGIBLE','EXTREME_ILLIQUIDITY_REJECT','LIQUIDITY_UNKNOWN')}
  reasons={k:dict(Counter(dm[i]['reason'] for i in ids-funded)) for k,ids in ups.items()}
  gate_reasons={k:dict(Counter(f for i in ids if not sm[i]['quality_gate_pass'] for f in sm[i]['gate_failures'])) for k,ids in ups.items()}
  batch=defaultdict(list)
  for d in ds:batch[d['session'],d['minute']].append(d)
  binding=0;regret=Counter();pairs=[]
  for (day,minute),dd in batch.items():
   selected=[d for d in dd if d['reason']=='FUNDED'];missed=[d for d in dd if d['reason']=='MAX_POSITION_CAP']
   if missed:binding+=1
   for category,fn in [('selected_loser_missed_PF1',lambda a,b:a is not None and b is not None and a<=0 and b>=.01),('selected_lower_realized_better_missed',lambda a,b:a is not None and b is not None and b>a)]:
    pp=[(a['entry_id'],b['entry_id']) for a in selected for b in missed if fn(tt[a['entry_id']]['realized_net_return'],tt[b['entry_id']]['realized_net_return'])]
    if pp:regret[category+'_batch_N']+=1;regret[category+'_selected_N']+=len({a for a,b in pp});regret[category+'_missed_N']+=len({b for a,b in pp});regret[category+'_pair_N']+=len(pp)
    pairs.extend({'category':category,'session':day,'minute':minute,'selected_entry_id':a,'missed_entry_id':b} for a,b in pp)
   pp=[(a['entry_id'],b['entry_id']) for a in selected for b in missed if a['entry_id'] in below3 and b['entry_id'] in ups['U5']]
   if pp:regret['selected_below3_missed_U5_batch_N']+=1;regret['selected_below3_missed_U5_selected_N']+=len({a for a,b in pp});regret['selected_below3_missed_U5_missed_N']+=len({b for a,b in pp});regret['selected_below3_missed_U5_pair_N']+=len(pp)
   pairs.extend({'category':'selected_below3_missed_U5','session':day,'minute':minute,'selected_entry_id':a,'missed_entry_id':b} for a,b in pp)
  for cat in ('selected_loser_missed_PF1','selected_lower_realized_better_missed','selected_below3_missed_U5'):
   for suffix in ('batch_N','selected_N','missed_N','pair_N'):regret.setdefault(cat+'_'+suffix,0)
  regret.update(MAX3_binding_entry_batch_N=binding,missed_U5_due_MAX3_N=reasons['U5'].get('MAX_POSITION_CAP',0),missed_U10_due_MAX3_N=reasons['U10'].get('MAX_POSITION_CAP',0))
  if p==PRIVATE:
   gzwrite(PRIVATE/(profile+'_SLOT_REGRET_PAIRS.jsonl.gz'),pairs)
   gzwrite(PRIVATE/(profile+'_FUNDED_QUALITY_LEDGER.jsonl.gz'),[{'entry_id':k,'session':sm[k]['session'],'decision':dm[k],'trade':tm.get(k),'teacher':tt[k],'historical_liquidity':sm[k]['liquidity'],'no_trade_MTM_N':no_trade[k],'quality_gate':sm[k]['quality_gate_pass'],'Q':sm[k]['Q'],'rank':sm[k]['rank']} for k in sorted(funded)])
  limit={v:cohort({k for k in funded if im.get(k,{}).get('limit_up_status','LIMIT_UP_UNKNOWN')==v}) for v in ('LIMIT_UP_CONFIRMED','LIMIT_UP_UNKNOWN')}
  return {'profile':profile,'diagnostic_only':diagnostic,'quality':quality,'capture':capture,'potential_buckets':br,'liquidity_cohorts':groups,'old_reject52':{'cohort_N':52,'admission_pre1520_eligible_N':sum(sm[k]['quality_gate_pass'] and sm[k]['entry_minute']<920 for k in old52),'funded':cohort(old52&funded),'missed_reasons':dict(Counter(dm[k]['reason'] for k in old52-funded))},'missed_reasons':reasons,'gate_failure_reasons':gate_reasons,'slot_regret':dict(regret),'limit_up':limit,'economic':result,'liquidity_reason_reject_N':sum(d['reason'] in ('EXTREME_ILLIQUIDITY_REJECT','LIQUIDITY_UNKNOWN','LIQUIDITY_LOT_CAP_REJECT') for d in ds)}
 for profile in PROFILES:all_report[profile]=evaluate(profile,PRIVATE,profile!=PROFILES[0])
 control=evaluate('LIQUIDITY_OFF_MAX3',ROOT.parent/'capital_liquidity_off_private')
 assert control['quality']['funded_N']==167 and control['quality']['PF1_N']==54 and control['quality']['loss0_N']==89
 main=all_report[PROFILES[0]];q=main['quality'];c=control['quality'];cap=main['capture'];ccap=control['capture']
 scoreboard={'Q1':q['PF1_rate']>c['PF1_rate'],'Q2':q['loss0_rate']<c['loss0_rate'],'Q3':q['tail1_rate']<c['tail1_rate'],'Q4':cap['U5']['capture_rate']>ccap['U5']['capture_rate'],'Q5':cap['Medium']['capture_rate']>ccap['Medium']['capture_rate'],'Q6':cap['U3']['capture_rate']>ccap['U3']['capture_rate'],'Q7':q['below2_rate']<c['below2_rate'],'Q8':q['below3_rate']<c['below3_rate']}
 four=[scoreboard[k] for k in ('Q1','Q2','Q4','Q5')];selection='TOP3_SELECTION_IMPROVED' if all(four) else 'TOP3_SELECTION_WORSE' if not any(four) else 'TOP3_SELECTION_MIXED'
 m=main['economic'];co=control['economic'];both=[m['geometric_mean_daily_return']>co['geometric_mean_daily_return'],m['rolling20_median']>co['rolling20_median']];economic='CAPITAL_QUALITY_V3_IMPROVES' if all(both) else 'CAPITAL_QUALITY_V3_WORSE' if not any(both) else 'CAPITAL_QUALITY_V3_MIXED'
 paired=[]
 for a,b in zip(m['daily_series'],co['daily_series']):
  assert a['session']==b['session'];delta=a['daily_return']-b['daily_return'] if a['daily_return'] is not None and b['daily_return'] is not None else None;paired.append({'session':a['session'],'control':b['daily_return'],'Main':a['daily_return'],'delta':delta})
 dd=[r['delta'] for r in paired if r['delta'] is not None];pd={'valid_N':len(dd),'positive_day_N':sum(v>0 for v in dd),'negative_day_N':sum(v<0 for v in dd),'equal_day_N':sum(v==0 for v in dd),'mean':mean(dd) if dd else None,'median':median(dd) if dd else None,'max_gain':max(dd) if dd else None,'max_deterioration':min(dd) if dd else None}
 save(OUT/'SELECTION_ANALYSIS.json',{'jst':now(),'profiles':all_report,'control_read_only':control,'scoreboard':{k:'PASS' if v else 'FAIL' for k,v in scoreboard.items()},'PF1_gap_to_100pct':q['PF1_gap_to_100pct'],'selection_status':selection,'economic_status':economic,'NORTH_STAR_HIT':m['north_star_hit_any'],'paired_daily_delta':pd,'slot_regret_scope':json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())['slot_regret'],'no_trade_definition':'Open-position regular completed5m full window after Entry with zero valid actual trades. No cash release.','control_replays':0,'evaluation_only':True,'safety':SAFETY})
 with (OUT/'PAIRED_DAILY_RETURNS.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['session','control','Main','delta']);w.writeheader();w.writerows(paired)
 # Head quality diagnostic labels are read only after all24 fits and fixed score stream.
 heads={}
 for head,pcol,bcol in [('H5','p5','base5'),('H3','p3','base3'),('HF1','p_floor1','base_floor1'),('HL0','p_loss0','base_loss0')]:
  records=[]
  for r in ss:
   t=tt[r['entry_id']];ret=t['realized_net_return'];label=t['label_bigwinner5'] if head=='H5' else t['label_bigwinner3'] if head=='H3' else None if ret is None else int(ret>=.01) if head=='HF1' else int(ret<=0)
   if label is not None:records.append({'id':r['entry_id'],'p':r[pcol],'base':r[bcol],'y':label,'block':r['block']})
  def diagnose(vv):
   y=[r['y'] for r in vv];p=[r['p'] for r in vv];base=mean(y) if y else None;sort=sorted(vv,key=lambda r:(-r['p'],r['id']));top=sort[:math.ceil(len(vv)*.2)]
   return {'N':len(y),'positive_N':sum(y),'observed_positive_base_rate':base,'training_base_rate_mean':mean(r['base'] for r in vv) if vv else None,'ROC_AUC':float(roc_auc_score(y,p)) if len(set(y))==2 else None,'Brier':float(brier_score_loss(y,p)) if y else None,'top20_N':len(top),'top20_observed_rate':mean(r['y'] for r in top) if top else None,'top20_enrichment':mean(r['y'] for r in top)/base if top and base else None}
  ordered=sorted(records,key=lambda r:(-r['p'],r['id']));dec=[]
  for d in range(10):
   vv=ordered[len(ordered)*d//10:len(ordered)*(d+1)//10];dec.append({'decile':d+1,'order':'highest probabilities first','N':len(vv),'mean_probability':mean(r['p'] for r in vv) if vv else None,'observed_rate':mean(r['y'] for r in vv) if vv else None})
  heads[head]={**diagnose(records),'deciles':dec,'blocks':{str(b):diagnose([r for r in records if r['block']==b]) for b in range(1,9)},'missing_label_excluded_N':len(ss)-len(records)}
 save(OUT/'HEAD_QUALITY_DIAGNOSTICS.json',{'jst':now(),'heads':heads,'fit_count':24,'H5_new_fits':0,'selection_changes_after_diagnostics':0,'safety':SAFETY})
 print(json.dumps({'selection_status':selection,'economic_status':economic,'scoreboard':scoreboard,'Main_funded':q['funded_N'],'PF1_rate':q['PF1_rate'],'loss0_rate':q['loss0_rate'],'U5':cap['U5'],'Medium':cap['Medium'],'paired_delta':pd}),flush=True)
if __name__=='__main__':main()
