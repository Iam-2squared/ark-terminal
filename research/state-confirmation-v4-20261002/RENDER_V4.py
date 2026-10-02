"""Exactly twelve static, hash-grounded scientific figures; no inference."""
from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;O=R/'CHARTS';O.mkdir(exist_ok=True);M=['R1','R2','R3','R4'];C=['#475569','#0284c7','#d97706','#059669'];MAN=[]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
def read(n):return pd.read_csv(R/n)
def real(d):return d[(d.control=='REAL')&(d.calibrated==True)]
def write(fig,name,sources,title):
 fig.suptitle(title,fontsize=14,y=.995);fig.tight_layout(rect=[0,0,1,.965]);fig.savefig(O/(name+'.png'),dpi=160,bbox_inches='tight');fig.savefig(O/(name+'.svg'),bbox_inches='tight');plt.close(fig)
 MAN.append({'figure':name,'PNG':'CHARTS/'+name+'.png','SVG':'CHARTS/'+name+'.svg','source_CSVs':{s:hashlib.sha256((R/s).read_bytes()).hexdigest() for s in sources},'description':title})
def main():
 a=read('REVERSAL_METRICS_V4.csv');p=real(read('REVERSAL_PER_CLASS_METRICS_V4.csv'));p=p[p.task=='CONTEXT_REVERSAL'];ctx=real(a);ctx=ctx[ctx.task=='CONTEXT_REVERSAL'].set_index('model').reindex(M);risk=read('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv');allr=risk[risk.group_kind=='ALL'].set_index('model').reindex(M);old=read('INHERITED_V3/UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv');old=old[old.group_kind=='ALL'].set_index('model').reindex(M);g=json.loads((R/'GATE_ASSESSMENT_V4.json').read_text());cohort=f"V4: {g['core_rows']:,} anchors / {g['core_dates']} dates / {g['core_folds']} folds"
 fig,ax=plt.subplots(figsize=(10,5));x=np.arange(4);ax.bar(x-.18,old.rate*100,.36,label='V3 (6 dates)',color='#cbd5e1');ax.bar(x+.18,allr.rate*100,.36,label=f"V4 ({g['core_dates']} dates)",color=C)
 for i,r in enumerate(allr.itertuples()):
  if np.isfinite(r.CI95_low):ax.vlines(i+.18,r.CI95_low*100,r.CI95_high*100,color='#0f172a');ax.plot([i+.13,i+.23],[r.CI95_low*100]*2,color='#0f172a');ax.plot([i+.13,i+.23],[r.CI95_high*100]*2,color='#0f172a')
  if np.isfinite(r.rate):ax.text(i+.18,r.rate*100+1.2,f'{int(r.opposite_actual_N)}/{int(r.predicted_N)}',ha='center',fontsize=8)
 ax.set(xticks=x,xticklabels=M,ylabel='Actual DOWN among predicted UP (%)');ax.set_ylim(0,max(40,np.nanmax(allr.CI95_high)*100+10) if allr.CI95_high.notna().any() else 40);ax.legend();ax.grid(axis='y',alpha=.15)
 write(fig,'01_v3_vs_v4_dangerous_rate',['INHERITED_V3/UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv'],'V3 vs V4 dangerous UP-to-DOWN error; different Development cohorts')
 fig,axs=plt.subplots(1,3,figsize=(15,4.8))
 for name in ['accuracy','balanced_accuracy','macro_F1']:axs[0].plot(M,ctx[name]*100,'o-',label=name)
 axs[0].set(ylabel='Percent',ylim=(0,100));axs[0].legend(fontsize=8)
 for ax,name in zip(axs[1:],['date_equal_log_loss','date_equal_Brier']):
  raw=a[(a.task=='CONTEXT_REVERSAL')&(a.control=='REAL')&(a.calibrated==False)].set_index('model').reindex(M);ax.bar(x-.18,raw[name],.36,color='#cbd5e1',label='Uncalibrated');ax.bar(x+.18,ctx[name],.36,color=C,label='Train-only calibrated');ax.set(xticks=x,xticklabels=M,ylabel=name+' (lower better)');ax.legend(fontsize=8)
 write(fig,'02_r1_r4_reversal_metrics',['REVERSAL_METRICS_V4.csv'],cohort+'; classification and probability quality are separate')
 fig,axs=plt.subplots(1,2,figsize=(12,5))
 for ax,state in zip(axs,['DOWN_REVERSAL','UP_CONTINUE']):
  sub=p[p['class']==state].set_index('model').reindex(M)
  for j,(k,color) in enumerate(zip(['Precision','Recall','F1'],['#0284c7','#d97706','#059669'])):ax.bar(x+(j-1)*.24,sub[k]*100,.24,label=k,color=color)
  ax.set(xticks=x,xticklabels=M,ylabel='Percent',ylim=(0,108),title=state);ax.legend(fontsize=8)
  for i,r in enumerate(sub.itertuples()):ax.text(i,103,f'actual {int(r.Actual_N)}\npred {int(r.Predicted_N)}',va='top',ha='center',fontsize=8)
 write(fig,'03_down_up_precision_recall_f1',['REVERSAL_PER_CLASS_METRICS_V4.csv'],'DOWN recall measures missed reversals; dangerous error uses predicted UP denominator')
 buckets=real(read('CALIBRATION_BUCKETS_V4.csv'));buckets=buckets[buckets.task=='CONTEXT_REVERSAL'];fig,ax=plt.subplots(figsize=(8,6))
 for model,color in zip(M,C):
  sub=buckets[(buckets.model==model)&(buckets.kind=='TOP_LABEL')&(buckets.N>0)];ax.plot(sub.mean_predicted_probability,sub.empirical_rate,'o-',label=model,color=color)
 ax.plot([0,1],[0,1],'--',color='#94a3b8');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean top-label confidence',ylabel='Actual top-label correctness');ax.legend();ax.grid(alpha=.15)
 write(fig,'04_calibration_curve',['CALIBRATION_BUCKETS_V4.csv'],'Fixed reliability buckets; temperature selected on train-only inner date')
 fig,axs=plt.subplots(1,2,figsize=(12,5))
 for model,color in zip(M,C):
  sub=buckets[(buckets.model==model)&(buckets.kind=='DOWN_REVERSAL')];yes=sub.N>0;axs[0].plot(sub.loc[yes,'mean_predicted_probability'],sub.loc[yes,'empirical_rate'],'o-',label=model,color=color);axs[1].plot(sub.lower+.05,sub.N,'o-',label=model,color=color)
 axs[0].plot([0,1],[0,1],'--',color='#94a3b8');axs[0].set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted DOWN probability',ylabel='Actual DOWN rate');axs[1].set(xlabel='Fixed DOWN probability bucket center',ylabel='Anchor support N',xlim=(0,1));axs[0].legend();axs[1].legend();axs[0].grid(alpha=.15)
 write(fig,'05_down_probability_vs_actual',['CALIBRATION_BUCKETS_V4.csv'],'DOWN probability vs actual rate, with bucket support; empty buckets are not zero rates')
 folds=real(read('REVERSAL_METRICS_BY_FOLD_V4.csv'));folds=folds[folds.task=='CONTEXT_REVERSAL'];fig,axs=plt.subplots(1,3,figsize=(15,4.8))
 for model,color in zip(M,C):
  s=folds[folds.model==model].sort_values('fold');axs[0].plot(s.fold,s.macro_F1*100,'o-',label=model,color=color);axs[1].plot(s.fold,s.date_equal_log_loss,'o-',color=color);r=risk[(risk.model==model)&(risk.group_kind=='FOLD')].sort_values('group');axs[2].plot(r.group.astype(int),r.rate*100,'o-',color=color)
 for ax,label in zip(axs,['Macro F1 (%)','Date-equal log loss','UP-to-DOWN error (%)']):ax.set(xticks=[1,2,3],xlabel='Fixed chronological fold',ylabel=label);ax.grid(alpha=.15)
 axs[0].legend();write(fig,'06_fold_stability',['REVERSAL_METRICS_BY_FOLD_V4.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv'],'Fixed folds retain missing dates; no availability-driven refolding')
 fig,axs=plt.subplots(2,1,figsize=(13,8))
 for ax,kind in zip(axs,['DATE','SECURITY']):
  sub=risk[(risk.group_kind==kind)&risk.model.isin(M)];r2=sub[sub.model=='R2'].set_index('group');keys=list(r2.sort_values('row_N',ascending=False).head(18).index);xx=np.arange(len(keys))
  for j,(model,color) in enumerate(zip(M,C)):
   s=sub[sub.model==model].set_index('group').reindex(keys);ax.bar(xx+(j-1.5)*.2,s.rate*100,.2,label=model,color=color)
  ax.set(xticks=xx,xticklabels=keys,ylabel='Dangerous rate (%)',title=kind+' (top18 by anchor support, not by outcome)');ax.tick_params(axis='x',rotation=35);ax.legend(fontsize=8)
 write(fig,'07_date_security_concentration',['UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V4.csv','PROMOTION_GATE_V4.csv'],'Stability across dates/securities; full positive-gain concentration gates saved in CSV')
 paths=[f'PATH_ANATOMY_LENGTH{k}_V4.csv' for k in range(1,5)];fig,axs=plt.subplots(2,2,figsize=(12,8));supported=0
 for length,ax in enumerate(axs.flat,1):
  tab=read(paths[length-1]);yes=tab.history_complete==True;supported+=int(tab.supported_descriptive_sequence.sum());ax.scatter(tab.loc[yes,'N'],tab.loc[yes,'DOWN_REVERSAL_rate']*100,alpha=.7,color='#0284c7',label='Complete history');ax.scatter(tab.loc[~yes,'N'],tab.loc[~yes,'DOWN_REVERSAL_rate']*100,color='#94a3b8',marker='x',label='Missing history');ax.axvline(100,ls='--',color='#94a3b8');ax.set(title=f'Length{length}: {len(tab)} sequences',xlabel='Anchor support N',ylabel='DOWN rate (%)',ylim=(-3,103));ax.legend(fontsize=8)
 write(fig,'08_path_length_reversal_support',paths,f'Path lengths1–4: {supported} sequences meet N100 / dates8 / securities3')
 for outcome,num in [('DOWN_REVERSAL','09'),('UP_CONTINUE','10')]:
  fig,axs=plt.subplots(3,1,figsize=(13,12));any_supported=False
  for length,ax in zip([2,3,4],axs):
   tab=read(paths[length-1]);good=tab[(tab.supported_descriptive_sequence==True)&(tab[outcome+'_N']>0)];any_supported |=len(good)>0
   if good.empty:good=tab[(tab.history_complete==True)&(tab[outcome+'_N']>0)]
   t=good.sort_values(['N','sequence'],ascending=[False,True]).head(8).iloc[::-1];y=np.arange(len(t));v=t[outcome+'_rate']*100;ax.barh(y,v,color='#0284c7' if num=='09' else '#059669');ax.hlines(y,t[outcome+'_CI95_low']*100,t[outcome+'_CI95_high']*100,color='#334155')
   labels=[f'{r.sequence}  N={int(r.N)}, days={int(r.date_N)}, sec={int(r.security_N)}' for r in t.itertuples()];ax.set(yticks=y,yticklabels=labels,xlim=(0,104),xlabel=outcome+' rate (%)',title=f'Length{length}: ranked by support, not rate')
  write(fig,num+'_top_'+outcome.lower()+'_paths',paths[1:],'Supported descriptive paths' if any_supported else 'No supported path: highest observed supports shown, NOT promoted rules')
 v2src=Path('/workspace/scratch/a1e749e0bd6c/state_predictiveness_v2_nextstate_20261002_v1/PER_STATE_PRECISION_RECALL_F1.csv');dst=R/'INHERITED_V2/PER_STATE_PRECISION_RECALL_F1.csv';dst.parent.mkdir(exist_ok=True);shutil.copyfile(v2src,dst)
 v3src=Path('/workspace/scratch/a1e749e0bd6c/state_predictiveness_v3_reversal_20261002_v1/PER_STATE_PRECISION_RECALL_F1_V3.csv');shutil.copyfile(v3src,R/'INHERITED_V3/PER_STATE_PRECISION_RECALL_F1_V3.csv')
 v2=read(str(dst.relative_to(R)));v3=read('INHERITED_V3/PER_STATE_PRECISION_RECALL_F1_V3.csv');v4=read('PER_STATE_PRECISION_RECALL_F1_V4.csv');states=json.loads((R/'REVERSAL_TARGET_SCHEMA.json').read_text())['classes']['NEXT_DISTINCT_PRIMARY'];short=['RS','R','SR','PB','RG','RB','SD','D','DS'];fig,axs=plt.subplots(2,3,figsize=(17,8))
 for i,task in enumerate(['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']):
  for j,(tab,models,version) in enumerate([(v2,['B0','B1','B2','B3'],'V2'),(v3,['R0']+M,'V3'),(v4,['R0']+M,'V4')]):
   t=tab[(tab.task==task)&(tab.control=='REAL')]
   if 'calibrated' in t.columns:t=t[t.calibrated==True]
   z=t.pivot(index='model',columns='State',values='Precision').reindex(index=models,columns=states).to_numpy();ax=axs[i,j];im=ax.imshow(z,vmin=0,vmax=1,cmap='Blues',aspect='auto');ax.set(xticks=range(9),xticklabels=short,yticks=range(len(models)),yticklabels=models,title=version+' '+task)
   for k in range(len(models)):
    for l in range(9):ax.text(l,k,'NA' if np.isnan(z[k,l]) else f'{z[k,l]*100:.0f}',ha='center',va='center',fontsize=8,color='white' if z[k,l]>.7 else 'black')
   fig.colorbar(im,ax=ax,fraction=.024,pad=.015)
 write(fig,'11_nine_state_precision_v2_v3_v4',['INHERITED_V2/PER_STATE_PRECISION_RECALL_F1.csv','INHERITED_V3/PER_STATE_PRECISION_RECALL_F1_V3.csv','PER_STATE_PRECISION_RECALL_F1_V4.csv'],'V2 / V3 / V4 nine-State precision (%): different cohorts, not controlled causal gains')
 mat=real(read('CONFUSION_MATRIX_9STATE_V4.csv'));fig,axs=plt.subplots(4,2,figsize=(14,17))
 for i,model in enumerate(M):
  for j,task in enumerate(['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']):
   t=mat[(mat.model==model)&(mat.task==task)];z=t.pivot(index='actual_class',columns='predicted_class',values='N').reindex(index=states,columns=states).to_numpy();ax=axs[i,j];ax.imshow(z,cmap='Blues',aspect='auto');ax.set(xticks=range(9),xticklabels=short,yticks=range(9),yticklabels=short,title=model+' '+task,xlabel='Predicted',ylabel='Actual')
   for k in range(9):
    for l in range(9):ax.text(l,k,str(int(z[k,l])),ha='center',va='center',fontsize=7,color='white' if z[k,l]>.6*z.max() and z.max()>0 else 'black')
 write(fig,'12_nine_by_nine_confusion',['CONFUSION_MATRIX_9STATE_V4.csv'],'All nine States retained, including zero support; R0 also saved in full CSV')
 assert len(MAN)==12,'TWELVE_FIGURES'
 (R/'CHART_MANIFEST.json').write_text(json.dumps({'unique_figures':12,'new_fits':0,'new_draws':0,'figures':MAN},indent=2)+'\n');print(json.dumps({'unique_figures':12,'formats':['PNG','SVG']}))
if __name__=='__main__':main()
