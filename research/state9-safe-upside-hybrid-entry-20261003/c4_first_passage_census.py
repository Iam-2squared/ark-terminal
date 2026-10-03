"""One descriptive census. Evaluator-only labels never become model features."""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
STATUS=('UP_FIRST','DOWN_FIRST','NEITHER','ORDER_UNKNOWN','DATA_UNAVAILABLE')
def read(p):
    b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bucket(x,edges,labels):
    if x is None:return '__UNKNOWN__'
    return labels[int(np.searchsorted(edges,x,side='right'))]
def group_stat(rows):
    c=collections.Counter(x['primary_status'] for x in rows);n=len(rows);known=sum(c[s] for s in STATUS[:3])
    ups=[x for x in rows if x['primary_status']=='UP_FIRST']
    def med(key):
        a=[x[key] for x in ups if x.get(key) is not None];return float(np.median(a)) if a else None
    return dict(N=n,opportunities=len({x['opportunity'] for x in rows}),sessions=len({x['session'] for x in rows}),
        **{s:c[s] for s in STATUS},evaluable_N=known,unknown_N=n-known,
        UP_FIRST_rate=c['UP_FIRST']/known if known else None,DOWN_FIRST_rate=c['DOWN_FIRST']/known if known else None,
        conservative_UP_FIRST_rate=c['UP_FIRST']/n if n else None,
        median_time_to_up_active_lower_bound=med('time_to_up'),
        median_MAE_before_up_exact=med('mae_exact'),MAE_before_up_exact_known_N=sum(x.get('mae_exact') is not None for x in ups),
        median_MAE_before_up_optimistic_bound=med('mae_optimistic'),median_MAE_before_up_adverse_bound=med('mae_adverse'))

def run():
    assert read(HERE/'FEATURE_FAMILY_FREEZE.json')['status']=='FROZEN_BEFORE_LABEL_RESULTS'
    pops=read(HERE.parents[1]/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/opportunity-records.json.gz')
    pop={x['opportunity']:x for x in pops};current=[];secondary={};all_counts=collections.Counter()
    joined=0
    with gzip.open(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz','rt') as ll,gzip.open(HERE/'CAUSAL_STATE_CANDIDATE_ROWS.jsonl.gz','rt') as ss:
        for left,right in zip(ll,ss,strict=True):
            a,b=json.loads(left),json.loads(right);joined+=1
            assert a['row_id']==b['row_id'] and a['opportunity']==b['opportunity']
            assert a['intent_minute']==b['intent_minute']
            all_counts[a['primary_status']]+=1
            if a['opportunity'] not in pop:continue
            oracle=pop[a['opportunity']]['selectorOutcome'];mfe=oracle.get('mfeEnd') if oracle.get('fullStatus')=='AVAILABLE' else None
            g=a['grid']['+2/-1'];mae=g.get('MAE_before_up') or {}
            formal='__SOURCE_UNAVAILABLE__' if b['source_status']=='SOURCE_UNAVAILABLE' else '__SEMANTIC_NULL__' if b['formal_primary'] is None else b['formal_primary']
            h=b['H2'];x=dict(row_id=a['row_id'],opportunity=a['opportunity'],session=a['session'],primary_status=a['primary_status'],
                formal_primary=formal,display_primary='__SOURCE_UNAVAILABLE__' if b['source_status']=='SOURCE_UNAVAILABLE' else b['display_primary'] or '__NULL_DISPLAY__',
                transition=h['previous_to_current_pair'],last3=h['last3_distinct_primary_sequence'],
                dwell_bucket=bucket(h['current_state_active_dwell'],[1,6,16,31],['0m','1-5m','6-15m','16-30m','>30m']),
                delay_bucket=bucket(a['active_delay'],[1,6,11,21,31],['0m','1-5m','6-10m','11-20m','21-30m','>30m']),
                time_of_day=f"{a['intent_minute']//60:02d}:00",selector_future_MFE_bucket=bucket(mfe,[1,2,3,4,5],['<1%','1-<2%','2-<3%','3-<4%','4-<5%','>=5%']),
                time_to_up=g.get('time_to_up_active'),mae_exact=mae.get('exact_pct'),mae_optimistic=mae.get('optimistic_pct'),mae_adverse=mae.get('adverse_pct'))
            current.append(x)
            for k,v in a['grid'].items():
                secondary.setdefault(k,collections.Counter())[v['status']]+=1
    assert joined==149900 and len(current)==65312 and len({x['opportunity'] for x in current})==2155
    dimensions=('formal_primary','display_primary','transition','last3','dwell_bucket','delay_bucket','time_of_day','selector_future_MFE_bucket')
    groups={}
    for field in dimensions:
        by=collections.defaultdict(list)
        for r in current:by[r[field]].append(r)
        groups[field]={k:group_stat(v) for k,v in sorted(by.items())}
    sec={}
    for k,c in secondary.items():
        ev=sum(c[s] for s in STATUS[:3]);sec[k]=dict(N=len(current),evaluable_N=ev,unknown_N=len(current)-ev,**{s:c[s] for s in STATUS},UP_FIRST_rate=c['UP_FIRST']/ev if ev else None,DOWN_FIRST_rate=c['DOWN_FIRST']/ev if ev else None)
    result=dict(status='C4_DESCRIPTIVE_CENSUS_COMPLETE_PENDING_INDEPENDENT_LABEL_AUDIT',primary='SAFE_UP_2_BEFORE_DOWN_1',
        current=group_stat(current),groups=groups,secondary_grid=sec,total_prefit_rows=joined,prefit_primary_counts=dict(all_counts),
        unit='candidate rows, not independent trades; repeated rows share Opportunities',evaluator_only=True,future_outcomes_used=True,
        manual_State_rules_created=0,selected_secondary_pair=False,Primary_changed=False,new_model_fits=0,
        source_labels_sha256=sha(HERE/'FIRST_PASSAGE_LABELS.jsonl.gz'),source_State_rows_sha256=sha(HERE/'CAUSAL_STATE_CANDIDATE_ROWS.jsonl.gz'))
    (HERE/'STATE9_FIRST_PASSAGE_CENSUS.json').write_text(json.dumps(result,indent=2)+'\n')
    out=HERE/'FIGURES';out.mkdir(exist_ok=True)
    totals=result['current'];foot=f"CANDIDATE_GRID | total rows N={totals['N']:,}; known N={totals['evaluable_N']:,}; Opportunities=2,155 | evaluator-only / future-outcome-used"
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(11,5));ax.bar(STATUS,[totals[s] for s in STATUS],color=['#337cb4','#c44e52','#999999','#8462a6','#cdd2d9']);ax.set_ylabel('Candidate rows (count)');ax.set_title('Fill-anchored +2% before -1%: all five statuses');ax.tick_params(axis='x',rotation=12);fig.text(.01,.02,foot,fontsize=8);fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(out/'C4_PRIMARY_STATUS.png',dpi=160);plt.close(fig)
    gs=groups['formal_primary'];keys=list(gs);colors=['#337cb4','#c44e52','#999999','#8462a6','#cdd2d9'];fig,ax=plt.subplots(figsize=(12,7));base=np.zeros(len(keys))
    for s,c in zip(STATUS,colors):
        vals=np.array([100*gs[k][s]/gs[k]['N'] for k in keys]);ax.barh(keys,vals,left=base,label=s,color=c);base+=vals
    ax.set_xlabel('Percent of all candidate rows (%)');ax.set_xlim(0,100);ax.set_title('RC2 formal State: first passage including unknown coverage');ax.legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.10));fig.text(.01,.01,foot,fontsize=8);fig.tight_layout(rect=[0,.11,1,1]);fig.savefig(out/'C4_STATE_FIRST_PASSAGE.png',dpi=160);plt.close(fig)
    order=['0m','1-5m','6-10m','11-20m','21-30m'];d=groups['delay_bucket'];fig,ax=plt.subplots(figsize=(10,5))
    for s,col in [('UP_FIRST_rate','#337cb4'),('DOWN_FIRST_rate','#c44e52')]:ax.plot(order,[100*d[k][s] if d[k][s] is not None else np.nan for k in order],marker='o',label=s,color=col)
    ax.set_ylabel('Rate among evaluable rows (%)');ax.set_xlabel('Active delay from Selector (minutes)');ax.set_title('Primary first passage by active delay; descriptive, no rule selection');ax.legend();fig.text(.01,.02,foot,fontsize=8);fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(out/'C4_DELAY_FIRST_PASSAGE.png',dpi=160);plt.close(fig)
    lines=['# 📊 RC2 State × fill起点 First-Passage Census','',f"Primary: +2% before −1%。N={len(current):,} candidate rows / 2,155 Opportunity / 58 sessions。",'',
        '候補行は独立取引ではない。全てevaluator-only / future-outcome-used。このcensusから手作業のBUY/除外ruleを作らない。','',
        '|項目|N|','|---|---:|']+[f'|{s}|{totals[s]:,}|' for s in STATUS]+['',f"evaluable UP_FIRST rate: {totals['UP_FIRST_rate']:.4%}" if totals['UP_FIRST_rate'] is not None else 'evaluableなし','',
        '![Primary statuses](FIGURES/C4_PRIMARY_STATUS.png)','', '![State first passage](FIGURES/C4_STATE_FIRST_PASSAGE.png)','', '![Delay](FIGURES/C4_DELAY_FIRST_PASSAGE.png)','',
        '## ⚠️ 解釈境界','', 'Source不足・semantic null・同bar順序不明を分離。touch時刻はbar-start lower-bound proxy。MAE-before-UPはintrabar順序不明ならexact UNKNOWNと上下boundを併記。','']
    for field in dimensions:
        lines += ['## 🔎 '+field,'','|Group|Rows N|Opportunity N|Known N|UP_FIRST|DOWN_FIRST|NEITHER|ORDER_UNKNOWN|DATA_UNAVAILABLE|UP / known|DOWN / known|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for k,v in groups[field].items():
            ur='UNKNOWN' if v['UP_FIRST_rate'] is None else f"{v['UP_FIRST_rate']:.2%}";dr='UNKNOWN' if v['DOWN_FIRST_rate'] is None else f"{v['DOWN_FIRST_rate']:.2%}"
            lines.append('|'+str(k)+'|'+'|'.join(str(v[c]) for c in ('N','opportunities','evaluable_N')+STATUS)+'|'+ur+'|'+dr+'|')
        lines += ['']
    (HERE/'STATE9_FIRST_PASSAGE_CENSUS.md').write_text('\n'.join(lines))
    print(json.dumps({k:v for k,v in result.items() if k not in ('groups','secondary_grid')}))

if __name__=='__main__':run()
