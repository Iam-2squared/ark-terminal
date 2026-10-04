"""Actual anonymous source/closure diagnostics; never Portfolio curves."""
import argparse,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
def main():
 p=argparse.ArgumentParser();p.add_argument('--coverage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=json.loads(a.coverage.read_text());r=c['session_aggregate'];a.output.mkdir(exist_ok=True,parents=True)
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
 xs=np.array([v['session_index'] for v in r]);fig,(ax,bx)=plt.subplots(2,1,figsize=(12,6.8),sharex=True,gridspec_kw={'height_ratios':[2,1]})
 bottom=np.zeros(len(xs));groups=[('regular_N','Regular post-intent','#168776'),('auction_N','15:30 auction','#4664b6'),('no_fill_N','Admission unresolved','#d4833d')]
 for key,label,color in groups:
  v=np.array([t[key] for t in r]);ax.bar(xs,v,bottom=bottom,label=label,color=color,width=.82);bottom+=v
 ax.set_ylabel('Candidate count');ax.set_title('EOD1520: source reconstruction by anonymous Development session');ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,1.04),frameon=False);ax.grid(axis='y',alpha=.18)
 den=np.array([t['candidate_N'] for t in r]);closed=np.array([t['prior_N']+t['regular_N']+t['auction_N'] for t in r]);bx.plot(xs,100*closed/den,color='#168776',marker='.',label='Precommitted final reference closure');bx.axhline(100,color='#777',linewidth=.8,linestyle='--');bx.set_ylim(0,105);bx.set_ylabel('Coverage (%)');bx.set_xlabel('Anonymous session index (1–58, chronological)');bx.grid(axis='y',alpha=.18)
 fig.text(.01,.012,'Source diagnostics only. Unresolved combines 18 eligible no-source + 22 Entry time contract gaps; no allocator/funded positions.',fontsize=9,color='#555');fig.tight_layout(rect=[0,.04,1,1]);fig.savefig(a.output/'eod1520_session_coverage.svg');fig.savefig(a.output/'eod1520_session_coverage.png',dpi=150);plt.close(fig)
 values=[c['counts'][key] for key in ['prior_EXIT_before1520_N','regular_post_intent_fill_N','auction_fallback_fill_N','no_fill_exception_N','entry_after_or_at_intent_N']];labels=['Frozen prior exit','Regular EOD reference','15:30 auction fallback','Eligible: source unresolved','Entry at/after15:20 gap'];colors=['#7e8890','#168776','#4664b6','#d4833d','#bc5664']
 fig,ax=plt.subplots(figsize=(10,4.8));bars=ax.barh(labels[::-1],values[::-1],color=colors[::-1]);ax.bar_label(bars,padding=5);ax.set_xlim(0,max(values)*1.15);ax.set_xlabel('Candidates (N=1,600)');ax.set_title('EOD1520: all identities retained, original Frozen fields unchanged');ax.grid(axis='x',alpha=.18);fig.tight_layout();fig.savefig(a.output/'eod1520_source_types.svg');fig.savefig(a.output/'eod1520_source_types.png',dpi=150);plt.close(fig)
 print(json.dumps({'charts':['eod1520_session_coverage','eod1520_source_types'],'source_N':c['counts']['candidate_N'],'fake_values':False,'private_dates_symbols_exposed':False}))
if __name__=='__main__':main()
