"""Exact saved-data figures/HTML. No model fits, labels, or bootstrap creation."""
from pathlib import Path
import json,csv,base64,html
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;F=R/'FIGURES'
BLUE='#245B9A';ORANGE='#CD7026';GREY='#657382';RED='#B54545';GREEN='#277A62'
plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.16,'figure.facecolor':'white','axes.facecolor':'white','font.size':10})
def rows(n):return list(csv.DictReader((R/n).open()))
def number(s):return None if s in [None,'','None'] else float(s)
def finish(fig,n):fig.tight_layout();fig.savefig(F/n,dpi=160,bbox_inches='tight');plt.close(fig)
def main():
 F.mkdir(exist_ok=True);g=json.loads((R/'FRESH_GATE_MEASUREMENTS_V5.json').read_text());final=json.loads((R/'FINAL_RECEIPT_V5.json').read_text());figures=[]
 data=rows('V4_R3_REAL_TRUE_NULL_DECOMPOSITION.csv');fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
 for ax,cal in zip(axes,['False','True']):
  rs=[r for r in data if r['calibrated']==cal];x=np.arange(len(rs));a=[float(r['REAL_date_equal_LL']) for r in rs];b=[float(r['TRUE_NULL_date_equal_LL']) for r in rs];ax.bar(x-.18,a,.36,label='REAL',color=BLUE);ax.bar(x+.18,b,.36,label='TRUE_NULL',color=GREY);ax.set_xticks(x,[r['model'] for r in rs]);ax.set_title('V4 saved '+('calibrated' if cal=='True' else 'uncalibrated'));ax.set_ylabel('Date-equal log loss (lower is better)');ax.set_ylim(0,1.7)
  for xx,v in zip(x-.18,a):ax.text(xx,v+.025,f'{v:.3f}',ha='center',fontsize=8)
  for xx,v in zip(x+.18,b):ax.text(xx,v+.025,f'{v:.3f}',ha='center',fontsize=8)
 axes[1].legend(loc='upper left');fig.suptitle('V4 remains BLOCKED: R3 global control reversal after calibration',fontsize=12);finish(fig,'01_V4_control_forensics.png');figures.append('01_V4_control_forensics.png')
 research=[r for r in rows('V5_CALIBRATION_RESEARCH_EXPOSED_ONLY.csv') if r['fold']=='ALL'];fig,axes=plt.subplots(1,2,figsize=(10,4))
 for ax,key,title in zip(axes,['date_equal_LL','Brier'],['Date-equal log loss','Row-weighted Brier']):
  x=np.arange(2)
  for cal,offset,color in [('False',-.18,BLUE),('True',.18,ORANGE)]:
   vals=[float(next(r for r in research if r['model']==m and r['calibrated']==cal)[key]) for m in ['R1','R2']];ax.bar(x+offset,vals,.36,color=color,label='raw' if cal=='False' else 'rolling-calibrated')
   for xx,v in zip(x+offset,vals):ax.text(xx,v+.01,f'{v:.3f}',ha='center',fontsize=8)
  ax.set_xticks(x,['R1','R2']);ax.set_title(title+' (lower better)');ax.set_ylim(0,max(float(r[key]) for r in research)*1.2)
 axes[0].legend(fontsize=8);fig.suptitle('V4 exposed-only method research: NOT fresh promotion evidence',fontsize=12);finish(fig,'02_exposed_calibration_research.png');figures.append('02_exposed_calibration_research.png')
 if g['fresh_OOF_anchors'] and g['R1_calibrated']['dangerous_rate'] is not None and g['R2_calibrated']['dangerous_rate'] is not None:
  risk=rows('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V5.csv');main=[next(r for r in risk if r['calibrated']=='True' and r['group_kind']=='ALL' and r['model']==m) for m in ['R1','R2']];fig,ax=plt.subplots(figsize=(8,4));v=np.array([float(r['rate'])*100 for r in main]);low=np.array([number(r['rate_CI_low'])*100 if number(r['rate_CI_low']) is not None else v[i] for i,r in enumerate(main)]);high=np.array([number(r['rate_CI_high'])*100 if number(r['rate_CI_high']) is not None else v[i] for i,r in enumerate(main)]);ax.bar([0,1],v,color=[GREY,BLUE],width=.6);ax.errorbar([0,1],v,yerr=np.vstack([np.maximum(v-low,0),np.maximum(high-v,0)]),fmt='none',color='#20252B',capsize=5);ax.set_xticks([0,1],['R1 current Primary','R2 Full State9']);ax.set_ylabel('Actual DOWN among predicted UP (%)');ax.set_title(f"V5 fresh dangerous rate — {g['OOF_dates']} dates / {g['evaluable_folds']} folds")
  for i,r in enumerate(main):ax.text(i,high[i]+.6,f"{r['numerator']}/{r['denominator']}\n{v[i]:.2f}%",ha='center',fontsize=9)
  ax.set_ylim(0,max(high)*1.35+1);finish(fig,'03_fresh_dangerous_rate.png');figures.append('03_fresh_dangerous_rate.png')
  ms=[r for r in rows('R1_R2_REVERSAL_METRICS_V5.csv') if r['control']=='REAL' and r['calibrated']=='True' and r['fold']=='ALL'];fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
  for ax,state in zip(axes,['DOWN_REVERSAL','UP_CONTINUE']):
   for model,offset,color in [('R1',-.18,GREY),('R2',.18,BLUE)]:
    row=next(r for r in ms if r['model']==model);val=[float(row[state+'_'+k])*100 for k in ['Precision','Recall','F1']];ax.bar(np.arange(3)+offset,val,.36,color=color,label=model)
   ax.set_xticks(range(3),['Precision','Recall','F1']);ax.set_ylim(0,110);ax.set_title(state);ax.set_ylabel('%');ax.legend()
  fig.suptitle('Fresh hard classification: reversal recall != dangerous UP-to-DOWN rate',fontsize=11);finish(fig,'04_fresh_reversal_metrics.png');figures.append('04_fresh_reversal_metrics.png')
  bs=[r for r in rows('CALIBRATION_BUCKETS_V5.csv') if r['control']=='REAL' and int(r['N'])>0];fig,axes=plt.subplots(1,2,figsize=(11,4.3))
  for ax,kind in zip(axes,['TOP_LABEL','DOWN_REVERSAL']):
   ax.plot([0,1],[0,1],':',color=GREY,label='ideal')
   for model,color in [('R1',GREY),('R2',BLUE)]:
    for cal,style in [('False','--'),('True','-')]:
     rr=[r for r in bs if r['kind']==kind and r['model']==model and r['calibrated']==cal];ax.plot([float(r['mean_predicted_probability']) for r in rr],[float(r['actual_rate']) for r in rr],style,marker='o',ms=4,color=color,label=model+(' calibrated' if cal=='True' else ' raw'))
   ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Mean predicted probability in fixed bucket');ax.set_ylabel('Actual rate');ax.set_title(kind+' reliability');ax.legend(fontsize=8)
  fig.suptitle('Untouched fresh outer-test probability quality',fontsize=12);finish(fig,'05_fresh_calibration_curves.png');figures.append('05_fresh_calibration_curves.png')
  fold=[r for r in risk if r['calibrated']=='True' and r['group_kind']=='fold' and r['model']=='R1_MINUS_R2' and number(r['improvement_pp']) is not None];fig,ax=plt.subplots(figsize=(8,4));x=np.arange(len(fold));v=np.array([float(r['improvement_pp']) for r in fold]);lo=[number(r['improvement_CI_low_pp']) for r in fold];hi=[number(r['improvement_CI_high_pp']) for r in fold];ax.axhline(0,color=GREY,lw=1);ax.bar(x,v,color=[GREEN if z>0 else RED for z in v],width=.6)
  for i,(l,h) in enumerate(zip(lo,hi)):
   if l is not None and h is not None:ax.plot([i,i],[l,h],color='#20252B');ax.plot([i-.08,i+.08],[l,l],color='#20252B');ax.plot([i-.08,i+.08],[h,h],color='#20252B')
  ax.set_xticks(x,[f"Fold {r['group']}\n{r['dates']} dates" for r in fold]);ax.set_ylabel('R1 minus R2 dangerous rate (pp)');ax.set_title('Fresh fold stability; shared date-cluster vectors');finish(fig,'06_fold_stability.png');figures.append('06_fold_stability.png')
  cs=[r for r in rows('CONCENTRATION_V5.csv') if r['group']=='MAXIMUM' and r['group_kind'] in ['date','security']];fig,ax=plt.subplots(figsize=(9,4));labels=[];vals=[]
  for r in cs:labels.append(('Danger reduction' if r['gain']=='dangerous_error_reduction' else 'Correctness gain')+'\nmax '+r['group_kind']);vals.append(number(r['share']) if number(r['share']) is not None else np.nan)
  ax.bar(np.arange(len(vals)),vals,color=[BLUE,GREY,BLUE,GREY][:len(vals)]);ax.axhline(.5,color=RED,ls='--',label='fixed maximum .5');ax.set_xticks(range(len(vals)),labels);ax.set_ylim(0,1);ax.set_ylabel('Share of positive gross gain');ax.set_title('Fresh improvement concentration (no zero-gain rescue)');ax.legend();finish(fig,'07_concentration.png');figures.append('07_concentration.png')
 (R/'FIGURE_MANIFEST_V5.json').write_text(json.dumps({'figures':figures,'source':'saved CSV/JSON only','new_fit':0,'new_label':0,'new_bootstrap':0,'fresh_figures_not_created_if_no_evaluable_sample':True},indent=2)+'\n')
 md=(R/'REPORT-ja.md').read_text();images=''.join(f'<figure><img src="data:image/png;base64,{base64.b64encode((F/n).read_bytes()).decode()}" alt="{html.escape(n)}"><figcaption>{html.escape(n)}</figcaption></figure>' for n in figures)
 page='<!doctype html><html lang="ja"><meta charset="utf-8"><title>Ark Terminal V5</title><style>body{font:16px/1.7 system-ui,sans-serif;max-width:1120px;margin:32px auto;padding:0 24px;color:#172536}pre{white-space:pre-wrap;word-wrap:break-word;background:#f4f6f8;padding:24px;font:14px/1.7 system-ui}img{width:100%;height:auto}figcaption{font-size:12px;color:#657382}figure{margin:32px 0}.status{padding:18px;border-left:5px solid #245B9A;background:#eef3f8}</style><body><h1>Ark Terminal — V5</h1><p class="status">'+html.escape(final['status'])+'</p>'+images+'<h2>Japanese complete report</h2><pre>'+html.escape(md)+'</pre></body></html>'
 (R/'REPORT-ja.html').write_text(page);print(json.dumps({'figures':len(figures),'no_new_measurements':True}))
if __name__=='__main__':main()
