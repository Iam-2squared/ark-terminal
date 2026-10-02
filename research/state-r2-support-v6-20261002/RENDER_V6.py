"""Presentation only from fixed saved CSV/gates; no model/label/bootstrap calls."""
from pathlib import Path
import json,csv,base64,hashlib,html
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
def readcsv(n):return list(csv.DictReader((R/n).open()))
def val(x):return np.nan if x in ['',None,'None'] else float(x)
def main():
 g=json.loads((R/'V6_GATE_MEASUREMENTS.json').read_text());final=json.loads((R/'FINAL_RECEIPT_V6.json').read_text());figdir=R/'FIGURES';figdir.mkdir(exist_ok=False);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'#fbfaf7','axes.facecolor':'#fbfaf7','axes.titleweight':'bold','savefig.facecolor':'#fbfaf7'});files=[];colors=['#777c82','#177987']
 def finish(fig,name,title,caption):
  fig.tight_layout(pad=1.5);p=figdir/name;fig.savefig(p,dpi=150,bbox_inches='tight');plt.close(fig);files.append({'path':str(p.relative_to(R)),'title':title,'caption':caption,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()})
 fig,ax=plt.subplots(figsize=(9.7,4.7));pops=['V5_ONLY','V6_ONLY','V5_V6_POOLED'];x=np.arange(3)
 for j,m in enumerate(['R1','R2']):
  rates=[100*g['R1_R2_summary'][p][m]['dangerous_rate'] for p in pops];bars=ax.bar(x+(j-.5)*.3,rates,width=.28,label=m,color=colors[j]);ax.bar_label(bars,labels=[f'{r:.2f}%' for r in rates],padding=4)
 ax.set_xticks(x,['V5 fixed','V6 only','V5 + V6 registered']);ax.set_ylabel('Actual DOWN among predicted UP (%)');ax.set_title('Dangerous UP-to-DOWN error: matched R1 vs R2');ax.set_ylim(0,max(ax.get_ylim()[1]*1.16,1));ax.legend(frameon=False);finish(fig,'01_DANGEROUS_RATES.png','Dangerous UP-to-DOWN rate','Compare R1 vs R2 within each population. Absolute changes between V5 and V6 are not matched treatment effects.')
 fig,ax=plt.subplots(figsize=(9.7,4.2));rows=[g['dangerous_improvement_by_population'][p] for p in ['V6_ONLY','V5_V6_POOLED']];pt=np.array([r['improvement_pp'] for r in rows]);lo=np.array([r['improvement_CI_low_pp'] for r in rows]);hi=np.array([r['improvement_CI_high_pp'] for r in rows]);y=np.arange(2);ax.errorbar(pt,y,xerr=np.stack([np.maximum(pt-lo,0),np.maximum(hi-pt,0)]),fmt='o',color=colors[1],capsize=5,markersize=8);ax.axvline(0,color='#ba6041',lw=1);ax.set_yticks(y,['V6 only','V5 + V6 registered']);ax.set_xlabel('R1 minus R2 dangerous-rate improvement (pp)');ax.set_title('Date-cluster 95% intervals');ax.invert_yaxis();finish(fig,'02_IMPROVEMENT_CI.png','Improvement and cluster CI','Exactly1000 V6-only vectors and1000 pooled vectors, each generated once. Shared dates are single pooled clusters.')
 fig,axs=plt.subplots(1,2,figsize=(11.4,4.4))
 for ax,cls in zip(axs,['DOWN_REVERSAL','UP_CONTINUE']):
  x=np.arange(3)
  for j,p in enumerate(['V6_ONLY','V5_V6_POOLED']):
   vals=[100*g['R1_R2_summary'][p]['R2'][cls+'_'+m] for m in ['Precision','Recall','F1']];bars=ax.bar(x+(j-.5)*.31,vals,width=.29,color=colors[j],label='V6 only' if j==0 else 'Pooled');ax.bar_label(bars,labels=[f'{v:.1f}' for v in vals],padding=3,fontsize=9)
  ax.set_xticks(x,['Precision','Recall','F1']);ax.set_ylim(0,106);ax.set_ylabel('%');ax.set_title('R2 '+cls.replace('_',' '));ax.legend(frameon=False,fontsize=9)
 finish(fig,'03_CLASS_METRICS.png','DOWN and UP detection','DOWN recall and dangerous UP-to-DOWN rate have different denominators. Class support is saved separately.')
 buckets=readcsv('CALIBRATION_BUCKETS_V6.csv');fig,axs=plt.subplots(1,2,figsize=(11.4,4.6))
 for ax,kind in zip(axs,['TOP_LABEL','DOWN_REVERSAL']):
  ax.plot([0,1],[0,1],ls='--',color='#9fa4a8',lw=1)
  for j,cal in enumerate(['False','True']):
   rr=[r for r in buckets if r['population']=='V6_ONLY' and r['control']=='REAL' and r['model']=='R2' and r['calibrated']==cal and r['kind']==kind and int(r['N'])>0];ax.plot([float(r['mean_predicted_probability']) for r in rr],[float(r['actual_rate']) for r in rr],marker='o',color=colors[j],label='Raw' if j==0 else 'Calibrated')
  ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Mean score in bucket');ax.set_ylabel('Actual frequency');ax.set_title('R2 '+('top-label reliability' if kind=='TOP_LABEL' else 'DOWN score buckets'));ax.legend(frameon=False)
 finish(fig,'04_PROBABILITY_RELIABILITY.png','Calibration reliability','Prediction scores are measured values, not automatically trusted probabilities. Bucket counts and support are preserved in CSV.')
 risk=readcsv('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE_V6.csv');rr=[r for r in risk if r['population']=='V6_ONLY' and r['calibrated']=='False' and r['group_kind']=='fold' and r['model']=='R1_MINUS_R2'];fig,ax=plt.subplots(figsize=(9.7,4.4));xx=np.arange(len(rr));yy=np.array([val(r['improvement_pp']) for r in rr]);lo=np.array([val(r['improvement_CI_low_pp']) for r in rr]);hi=np.array([val(r['improvement_CI_high_pp']) for r in rr]);ax.bar(xx,yy,color=colors[1],width=.5);ax.errorbar(xx,yy,yerr=np.stack([np.maximum(yy-lo,0),np.maximum(hi-yy,0)]),fmt='none',ecolor='#23434b',capsize=5);ax.axhline(0,color='#ba6041',lw=1);ax.set_xticks(xx,[r['group'] for r in rr]);ax.set_ylabel('R1 minus R2 dangerous rate (pp)');ax.set_title('V6 evaluable-fold stability');finish(fig,'05_FOLD_STABILITY.png','Fold stability','All evaluable folds retained. Empty folds and fixed-date scope are recorded in split/fixation receipts.')
 cc=readcsv('STABILITY_AND_CONCENTRATION_V6.csv');fig,axs=plt.subplots(1,2,figsize=(11.4,4.5))
 for ax,pop in zip(axs,['V6_ONLY','V5_V6_POOLED']):
  rows=[r for r in cc if r['population']==pop and r['group']=='MAXIMUM' and r['group_kind'] in ['date','security']];labels=[('Dangerous' if r['gain']=='dangerous_error_reduction' else 'Correctness')+'\n'+r['group_kind'] for r in rows];values=[100*val(r['share']) for r in rows];ax.bar(np.arange(len(rows)),values,color=colors[1]);ax.axhline(50,ls='--',color='#ba6041',label='50% fixed cap');ax.set_xticks(np.arange(len(rows)),labels,fontsize=9);ax.set_ylim(0,max(60,max(values,default=0)*1.1));ax.set_ylabel('Max single-cluster share (%)');ax.set_title(pop.replace('_',' '));ax.legend(frameon=False,fontsize=9)
 finish(fig,'06_CONCENTRATION.png','Date and security concentration','Shares use gross positive dangerous-error reductions and correctness gains, not net gains.')
 cm=readcsv('CONFUSION_MATRIX_V6.csv');fig,ax=plt.subplots(figsize=(7.8,6));classes=['UP_CONTINUE','DOWN_REVERSAL','RANGE_OR_STOP','NO_DECISION_WITHIN30'];z=np.array([[sum(int(r['N']) for r in cm if r['population']=='V6_ONLY' and r['model']=='R2' and r['fold']=='ALL' and r['actual']==a and r['predicted']==b) for b in classes] for a in classes]);im=ax.imshow(z,cmap='Blues');ax.set_xticks(range(4),['UP','DOWN','RANGE/STOP','NO DECISION'],rotation=20,ha='right');ax.set_yticks(range(4),['UP','DOWN','RANGE/STOP','NO DECISION']);ax.set_xlabel('Predicted class');ax.set_ylabel('Actual class');ax.set_title('R2 V6-only confusion (counts)')
 for i in range(4):
  for j in range(4):ax.text(j,i,str(z[i,j]),ha='center',va='center',color='white' if z[i,j]>z.max()/2 else '#1b2732')
 fig.colorbar(im,ax=ax,fraction=.045,pad=.03);finish(fig,'07_CONFUSION.png','R2 confusion matrix','Available target rows only; UNAVAILABLE is censored, not counted as an available class.')
 (R/'FIGURE_MANIFEST_V6.json').write_text(json.dumps({'status':final['status'],'files':files,'source_metrics_fixed':True,'new_fits_labels_draws':0},indent=2)+'\n')
 text=(R/'REPORT-ja.md').read_text();body=[];lines=text.splitlines();i=0
 while i<len(lines):
  line=lines[i]
  if line.startswith('|'):
   table=[]
   while i<len(lines) and lines[i].startswith('|'):table.append(lines[i]);i+=1
   body.append('<div class="scroll"><table>')
   for j,t in enumerate(table):
    if j==1 and '---' in t:continue
    tag='th' if j==0 else 'td';body.append('<tr>'+''.join('<'+tag+'>'+html.escape(x.strip()).replace('`','')+'</'+tag+'>' for x in t.strip('|').split('|'))+'</tr>')
   body.append('</table></div>');continue
  if line.startswith('#'):n=len(line)-len(line.lstrip('#'));body.append(f'<h{min(n,3)}>'+html.escape(line[n:].strip())+f'</h{min(n,3)}>')
  elif line.strip():body.append('<p>'+html.escape(line).replace('`','')+'</p>')
  i+=1
 pictures=[]
 for row in files:pictures.append('<section><h2>'+html.escape(row['title'])+'</h2><img alt="'+html.escape(row['title'])+'" src="data:image/png;base64,'+base64.b64encode((R/row['path']).read_bytes()).decode()+'"><p>'+html.escape(row['caption'])+'</p></section>')
 (R/'REPORT-ja.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>Ark Terminal V6</title><style>body{font:15px/1.65 system-ui,sans-serif;max-width:1250px;margin:40px auto;padding:0 28px;background:#fbfaf7;color:#1f2d36}h1,h2,h3{line-height:1.3}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px;margin:20px 0}th{text-align:left;background:#23434b;color:white}th,td{padding:9px;border-bottom:1px solid #d4dcdf;vertical-align:top}img{width:100%;max-width:1100px;height:auto}section{margin-top:45px}p{overflow-wrap:anywhere}</style>'+''.join(body)+''.join(pictures)+'</html>')
 print(json.dumps({'figures':len(files),'report_html':True,'new_fits_labels_draws':0}))
if __name__=='__main__':main()
