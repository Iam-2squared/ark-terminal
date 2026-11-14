#!/usr/bin/env python3
"""Frozen descriptive summaries and export plots. Reads joined saved evidence only."""
import collections, gzip, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parents[1]
CONTRACT=json.loads((P/'METRIC_CONTRACT.json').read_text())
with gzip.open(P/'GEOMETRY_ROWS.jsonl.gz','rt') as f: ROWS=[json.loads(x) for x in f]
ARMS=['IMMEDIATE','R1']; COLORS={'IMMEDIATE':'#3978ad','R1':'#dc7c2e'}
GROUP={a:[r for r in ROWS if r['arm']==a] for a in ARMS}
METRICS=list(CONTRACT['formulas'])
PLOTS=P/'FIGURES';PLOTS.mkdir(exist_ok=True)

def write(name,value):
 (P/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def stats_values(values):
 a=np.asarray([x for x in values if x is not None],dtype=float)
 q=np.quantile(a,[.05,.25,.5,.75,.9,.95],method='linear') if len(a) else [None]*6
 return dict(N=len(values),known_N=len(a),unknown_N=len(values)-len(a),mean=float(np.mean(a)) if len(a) else None,
             median=float(q[2]) if len(a) else None,p5=float(q[0]) if len(a) else None,p25=float(q[1]) if len(a) else None,
             p75=float(q[3]) if len(a) else None,p90=float(q[4]) if len(a) else None,p95=float(q[5]) if len(a) else None,
             min=float(np.min(a)) if len(a) else None,max=float(np.max(a)) if len(a) else None)
def stats(rows,key):return stats_values([r[key] for r in rows])
def counts(rows,key):return dict(sorted(collections.Counter(r[key] if r[key] is not None else 'NONE' for r in rows).items(),key=lambda x:str(x[0])))
def distributions(key):
 return {a:dict(summary=stats(GROUP[a],key),bucket_counts={b:counts(GROUP[a],key+'_bucket').get(b,0) for b in CONTRACT['buckets'][key]['labels']+['UNKNOWN']}) for a in ARMS}
def cohort(rows):
 known=sum(r['entry_to_later_high_pct'] is not None for r in rows)
 ns={str(t):sum(r['entry_to_later_high_pct'] is not None and r['entry_to_later_high_pct']>=t for r in rows) for t in [1,2,3,5]}
 return dict(total_N=len(rows),fill_N=sum(r['entry_id'] is not None for r in rows),
             geometry={k:stats(rows,k) for k in ['entry_to_later_high_pct','upside_retention_pct','entry_mae_end_pct','low_to_entry_pct','entry_to_future_low_pct','selector_to_entry_active_minutes','entry_to_high_active_minutes']},
             remaining_at_least_counts=ns,remaining_at_least_pct_of_known={t:100*n/known if known else None for t,n in ns.items()})
def grouped(key,labels):return {a:{b:cohort([r for r in GROUP[a] if r[key]==b]) for b in labels} for a in ARMS}
def capture_table(arm,strict=False):
 rows=GROUP[arm];key='strict_later_capture' if strict else 'canonical_capture';ans={}
 for level in [1,2,3,5]:
  c=collections.Counter(r[key][str(level)] for r in rows)
  labels=['CAPTURED','NO_ENTRY','ENTERED_BUT_BELOW_THRESHOLD','OUTCOME_UNKNOWN']
  winners=sum(c[x] for x in labels);known_missed=c['NO_ENTRY']+c['ENTERED_BUT_BELOW_THRESHOLD'];known=winners-c['OUTCOME_UNKNOWN']
  ans[str(level)]=dict(total_N=len(rows),selector_unknown_N=c['SELECTOR_UNKNOWN'],nonwinner_N=c['NOT_SELECTOR_WINNER'],selector_winner_N=winners,
   counts={x:c[x] for x in labels},known_outcome_N=known,known_missed_N=known_missed,
   capture_pct_of_all_winners=100*c['CAPTURED']/winners if winners else None,
   capture_pct_of_known_winners=100*c['CAPTURED']/known if known else None,
   known_missed_pct_of_all_winners=100*known_missed/winners if winners else None,
   unknown_pct_of_all_winners=100*c['OUTCOME_UNKNOWN']/winners if winners else None,
   legacy_not_captured_including_unknown_N=known_missed+c['OUTCOME_UNKNOWN'])
 return ans

table1={a:dict(population_N=len(GROUP[a]),unique_opportunity_N=len({r['opportunity'] for r in GROUP[a]}),sessions=58,symbols=950,
 fill_N=sum(r['entry_id'] is not None for r in GROUP[a]),no_entry_N=sum(r['entry_id'] is None for r in GROUP[a]),
 canonical_full_session_evaluable_N=sum(r['canonical_full_session_evaluable'] for r in GROUP[a]),
 selector_outcome_known_N=sum(r['selector_to_high_pct'] is not None for r in GROUP[a]),
 strict_later_high_known_N=sum(r['entry_to_later_high_pct'] is not None for r in GROUP[a]),
 saved_entry_outcome_known_N=sum(r['saved_entry_mfe_end_pct'] is not None for r in GROUP[a]),
 remaining_unknown_reason_counts=counts(GROUP[a],'remaining_upside_unknown_reason'),
 unfilled_reason_counts=counts([r for r in GROUP[a] if r['entry_id'] is None],'unfilled_reason')) for a in ARMS}
table5={a:dict(ordering_counts=counts(GROUP[a],'ordering_status'),same_entry_bar_low_unknown_N=sum(r['same_entry_bar_low_order_unknown'] for r in GROUP[a]),
 eligible_summary=stats([r for r in GROUP[a] if r['ordering_status']=='LOW_AT_OR_BEFORE_ENTRY'],'low_to_entry_pct'),
 bucket_counts={b:sum(r['low_to_entry_pct_bucket']==b for r in GROUP[a]) for b in CONTRACT['buckets']['low_to_entry_pct']['labels']},
 full_population_summary=stats(GROUP[a],'low_to_entry_pct')) for a in ARMS}
table6={a:cohort([r for r in GROUP[a] if r['ordering_status']=='LOW_AFTER_ENTRY']) for a in ARMS}
table4={a:dict(summary=stats(GROUP[a],'upside_retention_pct'),negative_N=sum(r['upside_retention_pct'] is not None and r['upside_retention_pct']<0 for r in GROUP[a]),
 greater_than_100_N=sum(r['upside_retention_pct'] is not None and r['upside_retention_pct']>100 for r in GROUP[a]),
 unknown_reason_counts=counts([r for r in GROUP[a] if r['upside_retention_pct'] is None],'retention_unknown_reason')) for a in ARMS}
canonical={a:capture_table(a) for a in ARMS};strict={a:capture_table(a,True) for a in ARMS}
miss=dict(status='DESCRIPTIVE',canonical_capture=canonical,strict_later_sensitivity=strict,
 interpretation='NO_ENTRY and entered-below are observed classifications. Global-high-before-entry is chronology association, not causal attribution.',
 canonical_vs_strict_disagreement_N={a:{str(t):sum(r['canonical_capture'][str(t)]!=r['strict_later_capture'][str(t)] for r in GROUP[a]) for t in [1,2,3,5]} for a in ARMS},
 entered_below_threshold_chronology={},no_entry_winner_reason_counts={},winner_geometry={})
for a in ARMS:
 miss['entered_below_threshold_chronology'][a]={};miss['no_entry_winner_reason_counts'][a]={};miss['winner_geometry'][a]={}
 for t in [1,2,3,5]:
  below=[r for r in GROUP[a] if r['canonical_capture'][str(t)]=='ENTERED_BUT_BELOW_THRESHOLD']
  after=sum(r['selector_global_high_minute'] is not None and r['selector_global_high_minute']<=r['entry_minute'] for r in below)
  minute_unknown=sum(r['selector_global_high_minute'] is None for r in below)
  miss['entered_below_threshold_chronology'][a][str(t)]=dict(entered_below_N=len(below),global_high_at_or_before_entry_N=after,global_high_after_entry_N=len(below)-after-minute_unknown,global_high_time_unknown_N=minute_unknown)
  no=[r for r in GROUP[a] if r['canonical_capture'][str(t)]=='NO_ENTRY']
  miss['no_entry_winner_reason_counts'][a][str(t)]=counts(no,'unfilled_reason')
  miss['winner_geometry'][a][str(t)]=cohort([r for r in GROUP[a] if r['selector_to_high_pct'] is not None and r['selector_to_high_pct']>=t])
write('MISS_WINNER_ANALYSIS.json',miss)
selector_buckets=CONTRACT['buckets']['selector_to_high_pct']['labels']+['UNKNOWN']
delay_buckets=CONTRACT['buckets']['selector_to_entry_active_minutes']['labels']+['UNKNOWN']
time=dict(delay_buckets=grouped('selector_to_entry_active_minutes_bucket',delay_buckets),
 selector_time_of_day=grouped('selector_time_band',list(CONTRACT['time_of_day_bands'])+['UNKNOWN']),
 entry_time_of_day=grouped('entry_time_band',list(CONTRACT['time_of_day_bands'])+['UNKNOWN']),
 clock_summaries={a:{k:stats(GROUP[a],k) for k in ['selector_to_entry_active_minutes','selector_to_entry_wall_minutes','entry_to_high_active_minutes','entry_to_high_wall_minutes']} for a in ARMS},
 lunch_crossing={a:dict(selector_to_entry_N=sum(r['entry_id'] is not None and r['selector_minute']<=690 and r['entry_minute']>=750 for r in GROUP[a]),
 entry_to_high_N=sum(r['later_high_minute'] is not None and r['entry_minute']<=690 and r['later_high_minute']>=750 for r in GROUP[a])) for a in ARMS})
write('TIME_GEOMETRY.json',time)
paired={}
for key in ['entry_to_later_high_pct','upside_retention_pct','entry_mae_end_pct','selector_to_entry_active_minutes']:
 im={r['opportunity']:r for r in GROUP['IMMEDIATE']};rr={r['opportunity']:r for r in GROUP['R1']}
 common=[i for i in im if im[i][key] is not None and rr[i][key] is not None]
 paired[key]=dict(common_known_N=len(common),IMMEDIATE=stats([im[i] for i in common],key),R1=stats([rr[i] for i in common],key),
  R1_minus_IMMEDIATE=stats_values([rr[i][key]-im[i][key] for i in common]))

def rank(v):
 order=np.argsort(v,kind='stable');r=np.zeros(len(v),dtype=float);i=0
 while i<len(order):
  j=i+1
  while j<len(order) and v[order[j]]==v[order[i]]:j+=1
  r[order[i:j]]=(i+j-1)/2;i=j
 return r
associations={}
for a in ARMS:
 associations[a]={}
 for x,y in [('low_to_entry_pct','entry_to_later_high_pct'),('selector_to_entry_active_minutes','entry_to_later_high_pct'),('selector_to_entry_active_minutes','entry_mae_end_pct')]:
  rs=[r for r in GROUP[a] if r[x] is not None and r[y] is not None];v=np.array([[r[x],r[y]] for r in rs])
  rho=float(np.corrcoef(rank(v[:,0]),rank(v[:,1]))[0,1]) if len(rs)>1 and len(np.unique(v[:,0]))>1 and len(np.unique(v[:,1]))>1 else None
  associations[a][x+'__'+y]=dict(known_pair_N=len(rs),spearman=rho,causal_claim=False)
low_groups={a:{b:cohort([r for r in GROUP[a] if r['low_to_entry_pct_bucket']==b]) for b in CONTRACT['buckets']['low_to_entry_pct']['labels']} for a in ARMS}
concentration={};population=GROUP['IMMEDIATE']
for key in ['session','symbol']:
 groups=[]
 for value in sorted({r[key] for r in population}):
  base=[r for r in population if r[key]==value]
  rec=dict(value=value,opportunity_N=len(base),share_pct=100*len(base)/2155,arms={})
  for a in ARMS:
   rs=[r for r in GROUP[a] if r[key]==value]
   rec['arms'][a]=dict(fill_N=sum(r['entry_id'] is not None for r in rs),remaining_known_N=sum(r['entry_to_later_high_pct'] is not None for r in rs),
    remaining_mean=stats(rs,'entry_to_later_high_pct')['mean'],remaining_median=stats(rs,'entry_to_later_high_pct')['median'],
    winner5_N=sum(r['selector_to_high_pct'] is not None and r['selector_to_high_pct']>=5 for r in rs),capture5_N=sum(r['canonical_capture']['5']=='CAPTURED' for r in rs))
  groups.append(rec)
 sorted_groups=sorted(groups,key=lambda r:(-r['opportunity_N'],r['value']))
 concentration[key]=dict(unique_N=len(groups),top1_share_pct=sorted_groups[0]['share_pct'],top5_share_pct=sum(x['share_pct'] for x in sorted_groups[:5]),
  top10_share_pct=sum(x['share_pct'] for x in sorted_groups[:10]),HHI=sum((r['opportunity_N']/2155)**2 for r in groups),
  population_counts=stats_values([r['opportunity_N'] for r in groups]),groups=groups,top20=sorted_groups[:20])
write('CONCENTRATION.json',concentration)
summary=dict(status='C4_GEOMETRY_COMPLETE_DESCRIPTIVE',population_N=2155,arm_rows=4310,sessions=58,symbols=950,
 evaluator_only=True,future_outcome_used=True,future_decision_use=False,
 continuous={a:{k:stats(GROUP[a],k) for k in METRICS} for a in ARMS},
 fill_conditioned_continuous={a:{k:stats([r for r in GROUP[a] if r['entry_id'] is not None],k) for k in METRICS} for a in ARMS},
 tables={'01_population':table1,'02_selector_to_high':distributions('selector_to_high_pct'),'03_entry_to_later_high':distributions('entry_to_later_high_pct'),
 '04_upside_retention':table4,'05_low_to_entry':table5,'06_low_after_entry':table6,'07_selector_to_entry_delay':distributions('selector_to_entry_active_minutes'),
 '08_entry_to_high_time':distributions('entry_to_high_active_minutes'),'09_winner_capture':canonical,
 '10_selector_upside_bucket':grouped('selector_to_high_pct_bucket',selector_buckets),'11_time_of_day':time['selector_time_of_day'],
 '12_state9':json.loads((P/'STATE9_GEOMETRY_NOT_AVAILABLE.json').read_text()),
 '13_concentration':{k:{x:v for x,v in concentration[k].items() if x!='groups'} for k in concentration}},
 paired_common_known=paired,associations=associations,low_distance_buckets=low_groups,
 saved_short_horizon_status={a:{str(t):dict(collections.Counter((r['saved_entry_labels'].get(str(t)) or {}).get('status','NOT_AVAILABLE') for r in GROUP[a])) for t in [30,60]} for a in ARMS},
 caveats=['Arms share opportunity identities; not independent sample duplication.','Known-only means have different selection and missingness; paired common-known statistics are also provided.',
 'Canonical saved Selector MFE and Entry MFE labels preserve inherited clipping and entry-bar semantics. Strict-later geometry is untruncated.',
 'Low and High are evaluator-only observed outcomes. Same-bar Low ordering is unknown intrabar.','No significance, fit, optimized threshold, realized P&L or causal delay-effect claim.'])
write('GEOMETRY_SUMMARY.json',summary)

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','axes.grid':True,'grid.alpha':.15})
def footer(fig,metrics,extra=''):
 text='; '.join(a+': total N=2155, known '+', '.join(k+'='+str(stats(GROUP[a],m)['known_N']) for k,m in metrics) for a in ARMS)
 fig.text(.02,.022,text+'\nEvaluator-only / future-outcome-used. '+extra,fontsize=8,ha='left')
def save(fig,name):
 fig.savefig(PLOTS/(name+'.png'),dpi=165,bbox_inches='tight');plt.close(fig)
def ecdf(ax,a,key):
 v=sorted(r[key] for r in GROUP[a] if r[key] is not None)
 if v:ax.step(v,np.arange(1,len(v)+1)/len(v)*100,where='post',label=a+' (known N='+str(len(v))+')',color=COLORS[a])
fig,ax=plt.subplots(figsize=(10,5));labels=CONTRACT['buckets']['entry_to_later_high_pct']['labels'];x=np.arange(len(labels))
for i,a in enumerate(ARMS):
 c=summary['tables']['03_entry_to_later_high'][a]['bucket_counts'];known=summary['continuous'][a]['entry_to_later_high_pct']['known_N']
 ax.bar(x+(i-.5)*.35,[100*c[b]/known for b in labels],.35,color=COLORS[a],label=a)
ax.set(xticks=x,xticklabels=labels,ylabel='Share of known entries (%)',xlabel='Strictly later High return (%)',title='Entry -> strictly later High: frozen buckets');ax.legend()
footer(fig,[('remaining','entry_to_later_high_pct')]);fig.subplots_adjust(bottom=.23);save(fig,'01_remaining_upside_distribution')
fig,ax=plt.subplots(figsize=(10,5))
for a in ARMS:ecdf(ax,a,'upside_retention_pct')
ax.set_xscale('symlog',linthresh=100)
ax.set(xlabel='Upside retention (%) — symmetric log axis; no clipping',ylabel='Cumulative share of known (%)',title='Upside retention: full observed range');ax.legend()
footer(fig,[('retention','upside_retention_pct')]);fig.subplots_adjust(bottom=.23);save(fig,'02_retention_distribution')
fig,axes=plt.subplots(1,2,figsize=(11,5),sharey=True)
for a,ax in zip(ARMS,axes):
 rs=[r for r in GROUP[a] if r['low_to_entry_pct'] is not None and r['entry_to_later_high_pct'] is not None]
 if rs:ax.scatter([r['low_to_entry_pct'] for r in rs],[r['entry_to_later_high_pct'] for r in rs],s=12,alpha=.45,color=COLORS[a])
 ax.set(xlabel='Low -> Entry distance (%)',title=a+'; joint known N='+str(len(rs)))
axes[0].set_ylabel('Entry -> strictly later High (%)');fig.suptitle('Only LOW_AT_OR_BEFORE_ENTRY; same-bar ordering flagged')
footer(fig,[('Low-distance','low_to_entry_pct'),('remaining','entry_to_later_high_pct')]);fig.subplots_adjust(bottom=.22,top=.84);save(fig,'03_low_distance_vs_remaining')
fig,axes=plt.subplots(1,2,figsize=(11,5));bs=CONTRACT['buckets']['selector_to_high_pct']['labels'];x=np.arange(len(bs))
for ax,m,label in zip(axes,['entry_to_later_high_pct','upside_retention_pct'],['Median remaining upside (%)','Median retention (%)']):
 for a in ARMS:
  vals=[summary['tables']['10_selector_upside_bucket'][a][b]['geometry'][m]['median'] for b in bs]
  ax.plot(x,[np.nan if v is None else v for v in vals],marker='o',color=COLORS[a],label=a)
 ax.set(xticks=x,xticklabels=bs,xlabel='Selector -> High bucket (%)',ylabel=label);ax.legend()
fig.suptitle('Selector opportunity size and Entry geometry; conditional known medians')
footer(fig,[('remaining','entry_to_later_high_pct'),('retention','upside_retention_pct')]);fig.subplots_adjust(bottom=.24,top=.86);save(fig,'04_selector_bucket_geometry')
fig,axes=plt.subplots(1,2,figsize=(11,5));bs=CONTRACT['buckets']['selector_to_entry_active_minutes']['labels'];x=np.arange(len(bs))
for ax,m,label in zip(axes,['entry_to_later_high_pct','entry_mae_end_pct'],['Median remaining upside (%)','Median saved session-end MAE (%)']):
 for a in ARMS:
  vals=[time['delay_buckets'][a][b]['geometry'][m]['median'] for b in bs]
  ax.plot(x,[np.nan if v is None else v for v in vals],marker='o',color=COLORS[a],label=a)
 ax.set(xticks=x,xticklabels=bs,xlabel='Selector -> Entry active delay (minutes)',ylabel=label);ax.legend()
fig.suptitle('Delay and Entry geometry; empty bucket/arm points omitted')
footer(fig,[('remaining','entry_to_later_high_pct'),('MAE','entry_mae_end_pct')],'Lunch recess excluded from active minutes.');fig.subplots_adjust(bottom=.24,top=.86);save(fig,'05_delay_geometry')
fig,axes=plt.subplots(1,2,figsize=(11,5),sharey=True);levels=['1','2','3','5'];classes=['CAPTURED','NO_ENTRY','ENTERED_BUT_BELOW_THRESHOLD','OUTCOME_UNKNOWN'];cc=['#2a9b73','#8797a4','#db9b4b','#c86a78']
for a,ax in zip(ARMS,axes):
 bottom=np.zeros(4)
 for cls,col in zip(classes,cc):
  values=np.array([100*canonical[a][t]['counts'][cls]/canonical[a][t]['selector_winner_N'] for t in levels]);ax.bar(levels,values,bottom=bottom,color=col,label=cls);bottom+=values
 ax.set(xlabel='Selector Winner threshold (%)',title=a,ylabel='Share of Selector Winners (%)')
 ax.set_xticks(range(4),['+'+t+'%\nN='+str(canonical[a][t]['selector_winner_N']) for t in levels],fontsize=9)
axes[1].legend(loc='upper left',bbox_to_anchor=(1.02,1),fontsize=8)
fig.suptitle('Canonical saved Entry MFE Capture; UNKNOWN separate from missed')
footer(fig,[('saved Entry MFE','saved_entry_mfe_end_pct')], 'Capture uses saved MFE, including Entry-bar High.');fig.subplots_adjust(bottom=.25,top=.85,right=.76);save(fig,'06_winner_capture')
fig,axes=plt.subplots(1,2,figsize=(11,5));bs=list(CONTRACT['time_of_day_bands']);x=np.arange(len(bs))
for ax,m,label in zip(axes,['entry_to_later_high_pct','entry_mae_end_pct'],['Median remaining upside (%)','Median saved session-end MAE (%)']):
 for a in ARMS:
  vals=[time['selector_time_of_day'][a][b]['geometry'][m]['median'] for b in bs]
  ax.plot(x,[np.nan if v is None else v for v in vals],marker='o',color=COLORS[a],label=a)
 ax.set(xticks=x,xticklabels=[b.replace('–','\n') for b in bs],xlabel='Selector time of day (JST)',ylabel=label);ax.legend()
fig.suptitle('Time of day and Entry geometry; no-entry population remains in source groups')
footer(fig,[('remaining','entry_to_later_high_pct'),('MAE','entry_mae_end_pct')]);fig.subplots_adjust(bottom=.24,top=.86);save(fig,'07_time_of_day_geometry')
write('FIGURE_INDEX.json',dict(figures=[dict(path='FIGURES/'+f.name,unit='pct / active minutes / JST as axis-labeled',arms=ARMS,total_N_per_arm=2155,evaluator_only=True,future_outcome_used=True) for f in sorted(PLOTS.glob('*.png'))],
 state9_plot='NOT_CREATED: exact final RC2 join not certified',known_N_authority='figure footer and corresponding frozen table'))
print(json.dumps(dict(status=summary['status'],table1=table1,headline={a:{k:summary['continuous'][a][k] for k in ['entry_to_later_high_pct','upside_retention_pct','entry_mae_end_pct','selector_to_entry_active_minutes']} for a in ARMS},paired_common_known=paired,canonical_capture=canonical,associations=associations),indent=2))
