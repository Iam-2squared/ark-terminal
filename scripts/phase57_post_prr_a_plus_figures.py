"""Figures of observed saved rows; blocked data are never plotted as zero effects."""
from __future__ import annotations
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.phase57_post_prr_a_plus import OUT,D
F=OUT/'figures';F.mkdir(exist_ok=True)
HEAD='c70b981f | ALL_100 | saved CCMG-R50 | Development 24 sessions'
def J(n):
 p=OUT/n
 if p.exists():return json.loads(p.read_text())
 import gzip
 with gzip.open(str(p)+'.gz','rt') as f:return json.load(f)
def save(fig,name,note):
 fig.text(.02,.008,HEAD+' | '+note,fontsize=7,color='#444')
 fig.savefig(F/name,dpi=150,bbox_inches='tight');plt.close(fig)
def main():
 census=J('INTENT_CENSUS.json')['arms'];g=J('FINE_BUCKET_ROUTE_RESULTS.json')['rows'];t=J('TAIL_AND_LOO.json');rank=J('RANK_DELTA_ANATOMY.json')['armsScopesRoutesHeads'];fill=J('INTENT_FILL_ANATOMY.json')['groups']
 fig,ax=plt.subplots(figsize=(8,4));x=np.arange(2);w=.18
 for j,(label,k) in enumerate([('All','allN'),('First intent','I'),('Provisional E','E_provisional'),('E known','E_intersect_K')]):
  v=[census[a][k] for a in ('IM','R1')];ax.bar(x+(j-1.5)*w,v,w,label=label)
 ax.set_xticks(x,['IM','R1']);ax.set_ylabel('Entries');ax.legend(ncol=4,fontsize=8);ax.set_title('First-intent risk set and observed outcomes')
 for i,a in enumerate(('IM','R1')):ax.text(i,805 if a=='IM' else 780,f"I unknown = {census[a]['I']-census[a]['I_intersect_K']}",ha='center',fontsize=8)
 save(fig,'01_intent_coverage.png','N_total IM819/R1795; E conditional on guard as-of; 80 unknown per arm')
 bands=['<1','[1,3)','[3,5)','[5,10)','[10,inf)'];fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True)
 for i,arm in enumerate(('IM','R1')):
  component=[float(D(g[f'{arm}|ALL_100|ALL|ALL|{b}']['component']['sumDeltaJpy']))/1000 for b in bands]
  route=[float(D(g[f'{arm}|ALL_100|ALL|ALL|{b}']['frozenRouteOnPairedMask']['sumDeltaJpy']))/1000 for b in bands]
  pp=[float(D(g[f'{arm}|ALL_100|ALL|ALL|{b}']['component']['meanDeltaNetPp'])) for b in bands]
  xx=np.arange(5);axes[i,0].bar(xx-.18,component,.36,label='CCMG component');axes[i,0].bar(xx+.18,route,.36,label='Frozen route');axes[i,0].axhline(0,color='k',lw=.7);axes[i,0].set_ylabel(arm+' JPY thousands')
  axes[i,1].bar(xx,pp,color='#9b5555');axes[i,1].axhline(0,color='k',lw=.7);axes[i,1].set_ylabel(arm+' component mean ΔNetPP')
  for col in (0,1):axes[i,col].set_xticks(xx,bands)
 axes[0,0].legend(fontsize=8);fig.suptitle('Exclusive evaluator-only future-upside bands')
 save(fig,'02_bands_yen_pp.png','paired K per band; yen and percentage points shown on separate axes')
 fig,axes=plt.subplots(1,2,figsize=(10,4))
 for ax,arm in zip(axes,('IM','R1')):
  z=t['tail'][f'{arm}|ALL_100|ALL|component']['sides']
  for side in ('gain','loss'):
   y=[float(D(r['fraction'])) for r in z[side]['curve']];ax.plot(range(1,len(y)+1),y,label=side)
  ax.axhline(.5,color='gray',lw=.7);ax.set(xlabel='Sorted contributing entries',ylabel='Fraction of own gross side',title=arm);ax.legend()
 save(fig,'03_gross_tail.png','paired K; gain and loss each divided by own gross, not net')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for ax,arm in zip(axes,('IM','R1')):
  z=t['allLeaveOneOut'][f'{arm}|ALL_100|ALL|component'];s=[float(D(r['remaining']['sumDeltaJpy']))/1000 for r in z if r['axis']=='session'];y=[float(D(r['remaining']['sumDeltaJpy']))/1000 for r in z if r['axis']=='symbol']
  ax.boxplot([s,y],tick_labels=['all session LOO','all symbol LOO']);ax.axhline(0,color='k',lw=.8);ax.set(title=arm,ylabel='Remaining paired ΔJPY, thousands')
 save(fig,'04_symmetric_loo.png','all 24 session and all observed symbols; known subset with unknown retained')
 fig,axes=plt.subplots(1,2,figsize=(11,4))
 for ax,arm in zip(axes,('IM','R1')):
  z=rank[f'{arm}|I|ALL|5'];means=[z['deciles'][f'5|{i}']['meanDeltaNetPp'] for i in range(1,11)];miss=[z['missingByDecile'][str(i)] for i in range(1,11)]
  ax.plot(range(1,11),[float(D(x)) if x is not None else np.nan for x in means],marker='o',label='known mean ΔNetPP');ax2=ax.twinx();ax2.bar(range(1,11),[v['unknown']/v['N'] if v['N'] else np.nan for v in miss],alpha=.18,color='gray',label='unknown rate');ax.set(title=arm,xlabel='Frozen head5 fold-local decile',ylabel='Mean ΔNetPP');ax2.set_ylabel('Unknown fraction');ax.axhline(0,color='k',lw=.5)
 save(fig,'05_intent_rank_missing.png','I all first intents; mean conditional on K, unknown is separate')
 fig,ax=plt.subplots(figsize=(8,4))
 for arm,offset in [('IM',-.15),('R1',.15)]:
  z=fill[arm+'|I']['ccmgFillDelayClockN'];keys=sorted((int(k),v) for k,v in z.items() if k!='UNKNOWN');ax.bar([k+offset for k,v in keys],[v for k,v in keys],.28,label=arm)
 ax.set(xlabel='Wall minutes: first intent to saved CCMG fill reference',ylabel='Known count',title='Decision time and fill reference differ');ax.legend()
 save(fig,'06_intent_fill_lag.png','80 unknown CCMG fill per arm omitted from bars and stated separately')
 fig,ax=plt.subplots(figsize=(7,4));x=np.arange(2)
 ax.bar(x-.17,[376,343],.34,label='Guard trace presence flag')
 ax.bar(x+.17,[0,0],.34,label='Row-level State/Signal values at τ')
 ax.set_xticks(x,['IM','R1']);ax.set_ylabel('First-intent rows with saved evidence');ax.set_title('Feature availability in retrieved saved rows');ax.legend()
 save(fig,'07_feature_availability.png','0 means none in retrieved Phase A rows; historical signal absence is unproven')
 print('FIGURES',len(list(F.glob('*.png'))))
if __name__=='__main__':main()
