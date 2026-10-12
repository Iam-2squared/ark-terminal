"""Six descriptive Phase 0 figures; no candidate replay or predictive fit."""
from __future__ import annotations

import collections
import gzip
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_execution_contract_v1 as clock


ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-milestone-guard-exit'
OUT=BASE/'figures'
OUT.mkdir(exist_ok=True)
COLORS={'IM':'#1764a2','R1':'#da6b2b'}


def save(name):
    plt.tight_layout()
    plt.savefig(OUT/name,dpi=155,bbox_inches='tight')
    plt.close()


def run():
    a=json.loads((BASE/'PHASE0_A.json').read_text())
    b=json.loads((BASE/'PHASE0_B.json').read_text())
    with gzip.open(BASE/'PHASE0_B_ENTRY_ROWS.jsonl.gz','rt') as f:
        rows=[json.loads(line) for line in f]
    ms=[1,2,3,5,10]
    plt.figure(figsize=(8,4.5))
    for arm in ('IM','R1'):
        n=a['counts'][arm]['entries']
        plt.plot(ms,[a['counts'][arm]['ge'+str(k)]/n for k in ms],marker='o',color=COLORS[arm],label=f'{arm}: final high, N={n}')
        plt.plot(ms,[a['milestones'][arm][str(k)].get('REACHED',0)/n for k in ms],marker='x',linestyle='--',color=COLORS[arm],label=f'{arm}: exact Control prefix')
    plt.xticks(ms,[f'+{x}%' for x in ms]);plt.ylim(bottom=0)
    plt.ylabel('Entry fraction');plt.title('01  Entry to milestone reach')
    plt.legend(fontsize=8);plt.grid(alpha=.2)
    save('01_entry_to_milestone_reach.png')

    buckets=['<1','1-2','2-3','3-5','5-10','>=10']
    im=[b['buckets'][x]['IM'] for x in buckets];r1=[b['buckets'][x]['R1'] for x in buckets]
    fig,ax=plt.subplots(figsize=(8,4.5))
    x=np.arange(len(buckets));ax.bar(x-.18,im,.36,label='IM',color=COLORS['IM'])
    ax.bar(x+.18,r1,.36,label='R1',color=COLORS['R1'])
    ax.set_xticks(x,buckets);ax.set_ylabel('Entries');ax.set_xlabel('Final upside bucket (%)')
    ax.set_title('02  Final high buckets, 1,614 Entries');ax.legend();ax.grid(axis='y',alpha=.2)
    save('02_milestone_bucket_counts.png')

    transitions=['1->2','2->3','3->5','5->10']
    statuses=[('UPPER_FIRST','#3f9e69'),('FLOOR_FIRST','#be574b'),
              ('AMBIGUOUS_SAME_BAR','#bb9b44'),('MISSING','#999999'),
              ('MISSING_PRIOR','#777777'),('CONTROL_TERMINAL_FIRST','#5972a9')]
    fig,ax=plt.subplots(figsize=(9,4.5));bottom=np.zeros(len(transitions))
    for key,color in statuses:
        v=np.array([a['transitions']['combined'][t].get(key,0) for t in transitions])
        ax.bar(transitions,v,bottom=bottom,label=key.replace('_',' ').title(),color=color)
        bottom+=v
    ax.set_ylabel('Entries');ax.set_title('03  Next milestone vs prior floor; missing kept separate')
    ax.legend(fontsize=7,ncol=3);ax.grid(axis='y',alpha=.15)
    save('03_first_passage_status.png')

    for cutoff,idx in [(5,4),(10,5)]:
        fig,ax=plt.subplots(figsize=(8,4.5))
        for arm in ('IM','R1'):
            values=[r['controlPrefixGivebackPp'] for r in rows if r['arm']==arm and
                    r['upsidePct'] is not None and r['upsidePct']>=cutoff and
                    r['controlPrefixGivebackPp'] is not None]
            if values:ax.hist(values,bins=20,alpha=.55,label=f'{arm} known N={len(values)}',color=COLORS[arm])
        ax.set_xlabel('Observed Control-prefix high minus last close (pp)')
        ax.set_ylabel('Entries');ax.set_title(f'0{idx}  Winner >={cutoff}% descriptive giveback')
        ax.legend();ax.grid(axis='y',alpha=.2)
        save(f'0{idx}_winner_ge{cutoff}_control_prefix_giveback.png')

    # Full deterministic raw projection is used only for the recovery curve.
    entries=r52.all_frozen_entries()
    allowed={entries[('IMMEDIATE' if r['arm']=='IM' else
                      'ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF',r['entryId'])]['opportunity']
             for r in rows}
    from scripts import phase57_development_integrated_v0 as v0
    raw,_=v0.allowlisted_raw_paths(r52.RAW,allowed)
    horizons=[1,2,5,10,30]
    numer=collections.Counter();denom=collections.Counter();unknown=collections.Counter()
    floor={1:0,2:1,3:2,5:3,10:5}
    for r in rows:
        arm=v0.IM if r['arm']=='IM' else v0.R1
        e=entries[(arm,r['entryId'])]
        path=raw[e['opportunity']]
        minutes=[m for m in clock.continuous_minutes(e['session'])
                 if m>=e['entryMinute']][:r['observedBars']]
        price=e['effectiveEntryPrice']
        for name,from_step in [('1->2',1),('2->3',2),('3->5',3),('5->10',5),('10->floor5',10)]:
            item=r['transitions'][name]
            if item['status']!='FLOOR_FIRST':continue
            origin=item['at'];level=price*(1+floor[from_step]/100)
            for h in horizons:
                recovered=False;complete=True
                for m in minutes[origin+1:origin+1+h]:
                    row=path.get(m)
                    if row is None or len(row)!=7 or not isinstance(row[4],(int,float)) or not math.isfinite(row[4]) or row[4]<=0:
                        complete=False;break
                    if row[4]>=level:recovered=True;break
                if not recovered and len(minutes[origin+1:origin+1+h])<h:complete=False
                if recovered or complete:
                    denom[h]+=1;numer[h]+=int(recovered)
                else:unknown[h]+=1
    receipt={'schema':'phase57-mg-recovery-curve-v1',
             'horizonsActiveCheckpoints':horizons,
             'recovered':[numer[x] for x in horizons],
             'known':[denom[x] for x in horizons],
             'unknown':[unknown[x] for x in horizons],
             'definition':'first FLOOR_FIRST raw transition, subsequent exact closed checkpoint return >= floor; missing/short prefix unknown; entries may contribute multiple milestones; descriptive only'}
    (BASE/'RECOVERY_CURVE.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    fig,ax=plt.subplots(figsize=(8,4.5))
    rates=[numer[x]/denom[x] if denom[x] else np.nan for x in horizons]
    positions=np.arange(len(horizons))
    ax.plot(positions,rates,marker='o',color='#3f9e69')
    for i,(h,y) in enumerate(zip(horizons,rates)):
        ax.annotate(f'N={denom[h]}  unknown={unknown[h]}',(i,y),
                    xytext=(0,10 if i%2==0 else -22),textcoords='offset points',
                    fontsize=7,ha='left' if i==0 else 'right' if i==len(horizons)-1 else 'center')
    ax.set_ylim(0,1.07);ax.set_xlim(-.45,len(horizons)-.55)
    ax.set_xticks(positions,[str(h) for h in horizons]);ax.grid(alpha=.2)
    ax.set_xlabel('Active closed checkpoints after breach');ax.set_ylabel('Recovery among known')
    ax.set_title('06  Floor recovery after a known first breach')
    save('06_breach_recovery_curve.png')
    print(json.dumps(receipt,sort_keys=True))


if __name__=='__main__':run()
