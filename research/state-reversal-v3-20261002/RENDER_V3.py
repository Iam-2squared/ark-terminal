"""Twelve CSV-grounded PNG/SVG research figures; no model or label generation."""
from pathlib import Path
import json,hashlib,math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent;OUT=R/'CHARTS';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})
MODELS=['R0','R1','R2','R3','R4'];COLORS=['#94a3b8','#334155','#0284c7','#d97706','#059669'];MANIFEST=[]
def read(n):return pd.read_csv(R/n)
def write(fig,name,sources,note):
    fig.suptitle(note,fontsize=15,fontweight='bold',y=.995);fig.tight_layout(rect=[0,0,1,.97])
    fig.savefig(OUT/(name+'.png'),dpi=170,bbox_inches='tight');fig.savefig(OUT/(name+'.svg'),bbox_inches='tight');plt.close(fig)
    MANIFEST.append({'figure':name,'PNG':'CHARTS/'+name+'.png','SVG':'CHARTS/'+name+'.svg','source_CSVs':{s:hashlib.sha256((R/s).read_bytes()).hexdigest() for s in sources},'description':note})
def real(df):return df[(df.control=='REAL')&(df.calibrated==True)]
def main():
    agg=read('REVERSAL_METRICS_AGGREGATE.csv');pc=read('REVERSAL_PER_CLASS_METRICS.csv');risk=read('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv');inc=read('R0_R1_R2_R3_R4_INCREMENTAL.csv')
    context=real(agg);context=context[context.task=='CONTEXT_REVERSAL'].set_index('model').loc[MODELS]
    classes=['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30'];fig,axs=plt.subplots(2,2,figsize=(12,8))
    for ax,c in zip(axs.flat,classes):
        sub=real(pc);sub=sub[(sub.task=='CONTEXT_REVERSAL')&(sub['class']==c)].set_index('model').loc[MODELS]
        x=np.arange(5);ax.bar(x-.16,sub.Precision*100,.32,label='Precision',color='#0284c7');ax.bar(x+.16,sub.Recall*100,.32,label='Recall',color='#d97706')
        ax.set(xticks=x,xticklabels=MODELS,ylim=(0,108),ylabel='Percent',title=c)
        for i,r in enumerate(sub.itertuples()):ax.text(i,102,f'pred {r.Predicted_N}\ntrue {r.Actual_N}',ha='center',va='top',fontsize=8)
        ax.legend(loc='upper left',fontsize=8)
    write(fig,'01_reversal_class_precision_recall',['REVERSAL_PER_CLASS_METRICS.csv'],'Context target: 597 anchors / 6 dates / 3 folds; zero denominators = NA')
    allrisk=risk[risk.group_kind=='ALL'].set_index('model').loc[MODELS];fig,ax=plt.subplots(figsize=(9,5));x=np.arange(5);values=allrisk.rate.to_numpy()*100
    ax.bar(x,values,color=COLORS);ax.errorbar(x,values,yerr=np.vstack([values-allrisk.CI95_low.to_numpy()*100,allrisk.CI95_high.to_numpy()*100-values]),fmt='none',color='#334155',capsize=5)
    for i,r in enumerate(allrisk.itertuples()):ax.text(i,r.rate*100+1,f'{r.opposite_actual_N}/{r.predicted_N}',ha='center',fontsize=9)
    ax.set(xticks=x,xticklabels=MODELS,ylabel='Actual DOWN among predicted UP (%)',ylim=(0,45));ax.grid(axis='y',alpha=.15)
    write(fig,'02_up_to_down_dangerous_error',['UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv'],'Dangerous error: point estimates and saved date-cluster 95% intervals')
    fig,axs=plt.subplots(1,2,figsize=(12,4.8))
    for k,label in [('accuracy','Accuracy'),('balanced_accuracy','Balanced accuracy'),('macro_F1','Macro F1')]:axs[0].plot(MODELS,context[k]*100,'o-',label=label)
    axs[0].set(ylabel='Percent',ylim=(0,100));axs[0].legend(fontsize=9);axs[0].grid(alpha=.15)
    axs[1].bar(MODELS,context.date_equal_log_loss,color=COLORS);axs[1].set(ylabel='Date-equal log loss (lower better)');axs[1].grid(axis='y',alpha=.15)
    write(fig,'03_r0_r4_incremental_performance',['REVERSAL_METRICS_AGGREGATE.csv','R0_R1_R2_R3_R4_INCREMENTAL.csv'],'Accuracy gains do not establish probability quality or promotion')
    fig,axs=plt.subplots(1,2,figsize=(12,4.8));x=np.arange(5)
    for ax,k in zip(axs,['log_loss','date_equal_log_loss']):
        raw=agg[(agg.task=='CONTEXT_REVERSAL')&(agg.control=='REAL')&(agg.calibrated==False)].set_index('model').loc[MODELS]
        ax.bar(x-.16,raw[k],.32,label='Uncalibrated',color='#94a3b8');ax.bar(x+.16,context[k],.32,label='Train-only calibrated',color='#0284c7');ax.set(xticks=x,xticklabels=MODELS,ylabel=k+' (lower better)');ax.legend(fontsize=9)
    write(fig,'04_calibrated_vs_uncalibrated_log_loss',['REVERSAL_METRICS_AGGREGATE.csv'],'Temperature chosen on the last training date; test folds never tune it')
    buckets=read('CALIBRATION_BUCKETS.csv');fig,ax=plt.subplots(figsize=(8,6))
    for model,color in zip(MODELS,COLORS):
        sub=real(buckets);sub=sub[(sub.task=='CONTEXT_REVERSAL')&(sub.model==model)&(sub.kind=='DOWN_REVERSAL')&(sub.N>0)]
        ax.plot(sub.mean_predicted_probability,sub.empirical_rate,'o-',label=model,color=color)
    ax.plot([0,1],[0,1],'--',color='#94a3b8',label='Ideal');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted DOWN probability',ylabel='Observed DOWN frequency');ax.legend();ax.grid(alpha=.15)
    write(fig,'05_down_reversal_calibration',['CALIBRATION_BUCKETS.csv'],'DOWN probability calibration; empirical bins can have small support')
    folds=real(read('REVERSAL_METRICS_BY_FOLD.csv'));folds=folds[folds.task=='CONTEXT_REVERSAL'];fig,axs=plt.subplots(1,3,figsize=(15,4.8))
    for model,color in zip(MODELS,COLORS):
        sub=folds[folds.model==model].sort_values('fold');axs[0].plot(sub.fold,sub.accuracy*100,'o-',color=color,label=model);axs[1].plot(sub.fold,sub.date_equal_log_loss,'o-',color=color,label=model)
        rr=risk[(risk.model==model)&(risk.group_kind=='FOLD')].sort_values('group');axs[2].plot(rr.group.astype(int),rr.rate*100,'o-',color=color,label=model)
    for ax,label in zip(axs,['Accuracy (%)','Date-equal log loss','UP to DOWN error (%)']):ax.set(xticks=[1,2,3],xlabel='Fixed outer fold',ylabel=label);ax.grid(alpha=.15)
    axs[0].legend(fontsize=8,ncol=2)
    write(fig,'06_fold_stability',['REVERSAL_METRICS_BY_FOLD.csv','UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv'],'All three folds retained; core target still spans only six dates')
    fig,axs=plt.subplots(2,1,figsize=(12,8))
    for ax,kind in zip(axs,['DATE','SECURITY']):
        sub=risk[(risk.group_kind==kind)&risk.model.isin(['R1','R2','R4'])];keys=sorted(sub.group.unique());x=np.arange(len(keys))
        for j,(model,color) in enumerate(zip(['R1','R2','R4'],[COLORS[1],COLORS[2],COLORS[4]])):
            vals=sub[sub.model==model].set_index('group').reindex(keys).opposite_actual_N.fillna(0);total=vals.sum();ax.bar(x+(j-1)*.24,vals/total*100 if total else vals,.24,label=f'{model}, DOWN errors N={int(total)}',color=color)
        ax.set(xticks=x,xticklabels=keys,ylabel='Share of dangerous error count (%)',title=kind);ax.tick_params(axis='x',rotation=30);ax.legend(fontsize=8)
    write(fig,'07_date_security_concentration',['UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv'],'Error concentration; separate promotion CSV records positive-gain concentration')
    fig,axs=plt.subplots(2,2,figsize=(12,8))
    for length,ax in enumerate(axs.flat,1):
        tab=read(f'REVERSAL_PATH_ANATOMY_LENGTH{length}.csv');yes=tab.history_complete==True
        ax.scatter(tab.loc[yes,'N'],tab.loc[yes,'DOWN_REVERSAL_rate']*100,color='#0284c7',alpha=.7,label='Complete history');ax.scatter(tab.loc[~yes,'N'],tab.loc[~yes,'DOWN_REVERSAL_rate']*100,color='#94a3b8',marker='x',label='Missing history')
        ax.set(title=f'History length {length}: {len(tab)} sequences',xlabel='Anchor support N',ylabel='DOWN rate (%)',ylim=(-3,103));ax.axvline(100,ls='--',color='#94a3b8');ax.legend(fontsize=8)
    write(fig,'08_path_length_support_vs_reversal_rate',[f'REVERSAL_PATH_ANATOMY_LENGTH{i}.csv' for i in range(1,5)],'No sequence meets N>=100, dates>=8, securities>=3; small-N rates are descriptive')
    for outcome,num in [('DOWN_REVERSAL','09'),('UP_CONTINUE','10')]:
        fig,axs=plt.subplots(3,1,figsize=(13,12))
        for length,ax in zip([2,3,4],axs):
            tab=read(f'REVERSAL_PATH_ANATOMY_LENGTH{length}.csv');tab=tab[(tab.history_complete==True)&(tab[outcome+'_N']>0)].sort_values(['N','sequence'],ascending=[False,True]).head(8).iloc[::-1]
            y=np.arange(len(tab));val=tab[outcome+'_rate'].to_numpy()*100;ax.barh(y,val,color='#0284c7' if outcome=='DOWN_REVERSAL' else '#059669')
            ax.errorbar(val,y,xerr=np.vstack([val-tab[outcome+'_CI95_low'].to_numpy()*100,tab[outcome+'_CI95_high'].to_numpy()*100-val]),fmt='none',color='#334155',capsize=3)
            labels=[f"{r.sequence}   N={r.N}, days={r.date_N}" for r in tab.itertuples()];ax.set(yticks=y,yticklabels=labels,xlim=(0,104),xlabel=outcome+' rate (%)',title=f'Length {length}; ranked by total support')
        write(fig,num+'_highest_support_'+outcome.lower()+'_paths',[f'REVERSAL_PATH_ANATOMY_LENGTH{i}.csv' for i in [2,3,4]],'Highest-support observed paths; none passes the descriptive support gate')
    v2=pd.read_csv(R/'INHERITED_V2/PER_STATE_PRECISION_RECALL_F1.csv');v3=read('PER_STATE_PRECISION_RECALL_F1_V3.csv');states=json.loads((R/'REVERSAL_TARGET_SCHEMA.json').read_text())['classes']['NEXT_DISTINCT_PRIMARY'];short=['RS','R','SR','PB','RG','RB','SD','D','DS'];fig,axs=plt.subplots(2,2,figsize=(14,8))
    for row,task in enumerate(['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']):
        for col,(tab,models,version) in enumerate([(v2,['B0','B1','B2','B3'],'V2'),(v3,MODELS,'V3')]):
            sub=tab[(tab.task==task)&(tab.control=='REAL')]
            if version=='V3':sub=sub[sub.calibrated==True]
            data=sub.pivot(index='model',columns='State',values='Precision').reindex(index=models,columns=states).to_numpy();ax=axs[row,col];im=ax.imshow(data,vmin=0,vmax=1,cmap='Blues',aspect='auto');ax.set(xticks=range(9),xticklabels=short,yticks=range(len(models)),yticklabels=models,title=f'{version}: {task}')
            for i in range(len(models)):
                for j in range(9):ax.text(j,i,'NA' if np.isnan(data[i,j]) else f'{data[i,j]*100:.0f}',ha='center',va='center',fontsize=8,color='white' if data[i,j]>.7 else 'black')
            fig.colorbar(im,ax=ax,fraction=.025,pad=.02)
    write(fig,'11_nine_state_precision_v2_vs_v3',['INHERITED_V2/PER_STATE_PRECISION_RECALL_F1.csv','PER_STATE_PRECISION_RECALL_F1_V3.csv'],'Different evaluation dates: V2 vs V3 is a cohort comparison, not a controlled gain')
    matrix=read('CONFUSION_MATRIX_9STATE_V3.csv');matrix=real(matrix);fig,axs=plt.subplots(5,2,figsize=(15,22))
    for i,model in enumerate(MODELS):
        for j,task in enumerate(['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']):
            sub=matrix[(matrix.model==model)&(matrix.task==task)];data=sub.pivot(index='actual_class',columns='predicted_class',values='N').reindex(index=states,columns=states).to_numpy();ax=axs[i,j];ax.imshow(data,cmap='Blues',aspect='auto');ax.set(xticks=range(9),xticklabels=short,yticks=range(9),yticklabels=short,title=model+' '+task,xlabel='Predicted',ylabel='Actual')
            for a in range(9):
                for b in range(9):ax.text(b,a,str(int(data[a,b])),ha='center',va='center',fontsize=7,color='white' if data[a,b]>.6*data.max() and data.max()>0 else 'black')
    write(fig,'12_nine_by_nine_confusion_all_models',['CONFUSION_MATRIX_9STATE_V3.csv'],'Every registered State retained, including zero-support classes')
    (R/'CHART_MANIFEST.json').write_text(json.dumps({'unique_figures':len(MANIFEST),'new_fits':0,'new_draws':0,'figures':MANIFEST},indent=2)+'\n');print(json.dumps({'figures':len(MANIFEST),'formats':['PNG','SVG']}))
if __name__=='__main__':main()
