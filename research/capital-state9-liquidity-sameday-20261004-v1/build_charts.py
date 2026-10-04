"""Only measured aggregate coverage/diagnostics; never a fake Portfolio curve."""
from collections import defaultdict
import gzip, json, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    root=Path(sys.argv[1]);data=root/'svnext_private'
    dst=root/'ark-terminal/docs/evidence/phase57-capital-state9-liquidity-sameday-20261004-v1/charts';dst.mkdir(parents=True,exist_ok=True)
    diag=json.loads((data/'STATE9_INCREMENTAL_RESULTS.json').read_text())
    opp=json.loads((data/'OPPORTUNITY_AUDIT.json').read_text())
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.titlepad':14,
        'figure.facecolor':'white','savefig.facecolor':'white','svg.fonttype':'none','svg.hashsalt':'capital-svnext-20261004'})
    blue='#2463a6';orange='#d17b25';grey='#aeb9c5';red='#b54347';green='#3a8c75'
    chartdata={}
    def save(fig,name):
        fig.tight_layout();fig.savefig(dst/(name+'.svg'),metadata={'Date':None});fig.savefig(dst/(name+'.png'),dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.6));labels=['Prior20 liquidity','Observed current State9'];known=[1037,558];unknown=[563,1042]
    ax.barh(labels,known,color=blue,label='Admissible input');ax.barh(labels,unknown,left=known,color=grey,label='Unavailable / not fresh current')
    for i,(a,b) in enumerate(zip(known,unknown)):
        ax.text(a/2,i,f'{a:,} ({a/16:.3f}%)',ha='center',va='center',color='white');ax.text(a+b/2,i,f'{b:,}',ha='center',va='center')
    ax.set_xlim(0,1600);ax.set_xlabel('Frozen candidates (N=1,600)');ax.set_title('Causal input coverage — missing is not a normal value');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.23),ncol=2)
    save(fig,'causal_input_coverage');chartdata['causal_input_coverage']=[{'input':a,'known_N':b,'unknown_N':c} for a,b,c in zip(labels,known,unknown)]
    fig,ax=plt.subplots(figsize=(10,4.8));labels=['EXIT v3 before 15:20','Regular EOD reference','Exact closing auction','Execution UNKNOWN','Late-entry cutoff'];values=[473,931,156,18,22]
    bars=ax.barh(labels,values,color=[blue,green,orange,grey,red]);ax.bar_label(bars,labels=[f'{v:,}' for v in values],padding=5)
    ax.invert_yaxis();ax.set_xlim(0,1050);ax.set_xlabel('Candidate-level source classification, not funded fills');ax.set_title('Immutable parent EOD evidence (all 1,600 identities retained)');save(fig,'eod_source_coverage')
    chartdata['eod_source_coverage']=[{'class':a,'N':b} for a,b in zip(labels,values)]
    fig,ax=plt.subplots(figsize=(10,5));x=np.arange(4);labels=['≥5 Winner','Exact pre-peak MAE','Frozen v3 return','Active hold time']
    b=np.array([t['relative_improvement'] for t in diag['State9_current_vs_A']['targets']])*100;c=np.array([t['relative_improvement'] for t in diag['StatePath_vs_B']['targets']])*100
    ax.bar(x-.17,b,.34,color=blue,label='B vs A: current State9');ax.bar(x+.17,c,.34,color=orange,label='C vs B: causal Path');ax.axhline(0,color='#495260',lw=1)
    ax.set_xticks(x,labels);ax.set_ylabel('Relative MSE improvement (%)');ax.set_title('Finite Development diagnostic — positive means lower error');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.17),ncol=2)
    save(fig,'incremental_teacher_comparison');chartdata['incremental_teacher_comparison']=[{'teacher':a,'B_vs_A_pct':float(bb),'C_vs_B_pct':float(cc)} for a,bb,cc in zip(labels,b,c)]
    fig,ax=plt.subplots(figsize=(8,4.8));labels=['B vs A: current','C vs B: Path'];share=[diag['State9_current_vs_A']['max_positive_session_lift_share']*100,diag['StatePath_vs_B']['max_positive_session_lift_share']*100]
    bars=ax.bar(labels,share,color=[blue,orange]);ax.bar_label(bars,labels=[f'{v:.2f}%' for v in share],padding=5)
    ax.axhline(40,color=red,ls='--',label='Precommitted maximum 40%');ax.set_ylim(0,100);ax.set_ylabel('Largest session / total positive lift (%)');ax.set_title('Path improvement fails the concentration gate');ax.legend();save(fig,'session_lift_concentration')
    chartdata['session_lift_concentration']=[{'comparison':a,'largest_positive_session_pct':b} for a,b in zip(labels,share)]
    fig,ax=plt.subplots(figsize=(9,4.5));labels=['Capacity fits ≥100 shares','Capacity below100 shares','Prior20 input UNKNOWN'];values=[727,310,563]
    bars=ax.barh(labels,values,color=[green,orange,grey]);ax.bar_label(bars,labels=[f'{v:,}' for v in values],padding=5);ax.set_xlim(0,820);ax.invert_yaxis()
    ax.set_xlabel('Potential capacity predicate, not completed replay rejections');ax.set_title('Fixed 1% liquidity capacity: 39 confirmed ≥5 Winners below one lot');save(fig,'liquidity_capacity_predicate')
    chartdata['liquidity_capacity_predicate']=[{'capacity_class':a,'N':b} for a,b in zip(labels,values)]
    fig,ax=plt.subplots(figsize=(9,4.7));labels=['≥5 Winner','Exact MAE','Frozen v3 return','Hold time'];full=[301,317,1561,1561];oof=[166,180,1058,1058];x=np.arange(4)
    ax.bar(x-.17,full,.34,color=blue,label='Saved teacher complete');ax.bar(x+.17,oof,.34,color=orange,label='OOF comparable support');ax.set_xticks(x,labels);ax.set_ylim(0,1700)
    ax.set_ylabel('Candidates with valid teacher');ax.set_title('Outcome-source censoring: UNKNOWN teachers are never zero-filled');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.15),ncol=2);save(fig,'teacher_support')
    chartdata['teacher_support']=[{'teacher':a,'full_known_N':b,'OOF_N':c} for a,b,c in zip(labels,full,oof)]
    states=[json.loads(s) for s in gzip.open(data/'STATE9_ENTRY_ROWS.jsonl.gz','rt') if s.strip()]
    entries=[e for e in map(json.loads,gzip.open(root/'eod_private/primary/entry.jsonl.gz','rt')) if e['entry_status']=='FIRST_ENTRY'];caps=json.loads((data/'CAPACITIES_PRIVATE.json').read_text());byday=defaultdict(list)
    state_byid={s['entry_id']:s for s in states}
    for e in entries:byday[e['session']].append(e)
    points=[]
    for i,day in enumerate(sorted(byday),1):
        es=byday[day];n=len(es);points.append({'session_ordinal':i,'candidates_N':n,'liquidity_known_pct':100*sum(caps[e['watch_key']] is not None for e in es)/n,'current_State9_observed_pct':100*sum(state_byid[e['watch_key']]['observed'] for e in es)/n})
    fig,ax=plt.subplots(figsize=(10,4.8));ax.plot([p['session_ordinal'] for p in points],[p['liquidity_known_pct'] for p in points],color=blue,label='Exact prior20 available',lw=2)
    ax.plot([p['session_ordinal'] for p in points],[p['current_State9_observed_pct'] for p in points],color=orange,label='Fresh current State9 observed',lw=1.8)
    ax.set_ylim(0,105);ax.set_xlim(1,58);ax.set_xlabel('Development session ordinal (all58 shown; no private date/symbol rows)');ax.set_ylabel('Candidates in that session (%)');ax.set_title('Measurement/input availability across the fixed Development cohort');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.19),ncol=2);save(fig,'session_input_coverage')
    chartdata['session_input_coverage']=points
    (dst/'CHART_DATA.json').write_text(json.dumps(chartdata,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'charts_N':7,'full_Portfolio_charts_created':0,'all_values':'measured aggregate only','output_directory':str(dst)}))

if __name__=='__main__':main()
