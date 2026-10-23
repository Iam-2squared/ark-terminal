"""Export fixed descriptive CCMG figures; never choose thresholds from them."""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/phase57-checkpoint-certified-guard-exit'
FIG=OUT/'figures'


def js(name):return json.loads((OUT/name).read_bytes())


def save(name,title):
    plt.title(title);plt.grid(alpha=.2,axis='y');plt.tight_layout()
    FIG.mkdir(exist_ok=True)
    plt.savefig(FIG/name,dpi=135);plt.close()


def run():
    r=js('CHECKPOINT_READINESS.json');a=js('CHECKPOINT_ANATOMY.json')
    l=js('LAYER_A_RESULT.json');m=js('MECHANISM_DIAGNOSTICS.json');p=js('POTENTIAL_RESULT.json')
    keys=['1','2','3','5','10'];x=list(range(len(keys)))
    plt.figure(figsize=(7,4));plt.bar([v-.18 for v in x],[r['primary']['combined']['certified'][k] for k in keys],width=.36,label='Primary 111')
    plt.bar([v+.18 for v in x],[r['allEntry']['combined']['certified'][k] for k in keys],width=.36,label='All 1,614')
    plt.xticks(x,['+'+k+'%' for k in keys]);plt.ylabel('Entry count');plt.legend()
    save('01_certified_reach.png','Fresh-close certification; missing 5,127 / 65,526 checkpoints')
    plt.figure(figsize=(7,4));parts=['EARLY','MID','LATE']
    for j,arm in enumerate(('IM','R1')):
        fresh=[r['byTiming'][arm][part]['fresh'] for part in parts]
        missing=[r['byTiming'][arm][part]['missing'] for part in parts]
        plt.bar([i+j*.36 for i in range(3)],fresh,width=.36,label=arm+' fresh')
        plt.bar([i+j*.36 for i in range(3)],missing,width=.36,bottom=fresh,label=arm+' missing')
    plt.xticks([i+.18 for i in range(3)],parts);plt.ylabel('Scheduled checkpoints');plt.legend(fontsize=8)
    save('02_fresh_missing.png','All 1,614; unknown is retained as missing')
    alerts=[];events={}
    with gzip.open(OUT/'CHECKPOINT_DRY_TRACE.jsonl.gz','rt') as f:
        for line in f:
            e=json.loads(line)
            if e['event']=='BREACH_1' and e['distanceToNextMilestonePp'] is not None:
                alerts.append(e)
            events[e['event']]=events.get(e['event'],0)+1
    fig,ax=plt.subplots(figsize=(7,4))
    for arm,color in [('IM','#156082'),('R1','#e48122')]:
        v=[e for e in alerts if e['arm']==arm]
        ax.scatter([e['distanceToNextMilestonePp'] for e in v],
                   [e['floorMarginPp'] for e in v],s=5,alpha=.18,color=color,label=arm+f' alerts N={len(v)}')
    ax.axhline(0,color='black',linewidth=.7);ax.set_xlabel('Distance to next milestone (pp)');ax.set_ylabel('Floor margin (pp)');ax.legend()
    save('03_progress_floor_margin.png','Observed ALERT checkpoints only; missing excluded')
    plt.figure(figsize=(7,4));labels=['BREACH_1','RECOVERY','BREACH_2','DATA_GAP_RESET']
    plt.bar(labels,[events.get(k,0) for k in labels],color=['#ca9b34','#3f9a78','#b64f49','#677186']);plt.xticks(rotation=16)
    save('04_breach_recovery.png',f'All 1,614; missing checkpoints 65,526')
    fig,ax=plt.subplots(figsize=(8,4));buckets=['<1','1-3','3-5','5-10','>=10']
    for j,arm in enumerate(('IM','R1')):
        data=[l['allEntryStandalone'][arm+':'+b] for b in buckets]
        ax.bar([i+j*.36 for i in range(5)],[d['candidateFirst']/d['entryN'] for d in data],width=.36,label=arm)
        for i,d in enumerate(data):ax.text(i+j*.36,d['candidateFirst']/d['entryN']+.015,f"{d['candidateFirst']}/{d['entryN']}",ha='center',fontsize=7,rotation=90)
    ax.set_xticks([i+.18 for i in range(5)],buckets);ax.set_ylim(0,1.12);ax.set_ylabel('Candidate-first rate');ax.legend()
    save('05_bucket_trigger.png','All-entry standalone; 100 shares, not portfolio')
    for k,th in enumerate((5,10),6):
        fig,ax=plt.subplots(figsize=(7,4));names=[];ctrl=[];old=[];candidate=[]
        for arm in ('IM','R1'):
            d=l['winner'][f'{arm}>={th}'];names.append(f"{arm}\nknown {d['knownPairedN']}/{d['entryN']}")
            ctrl.append(float(d['controlPnlJpy']));old.append(float(d['r54PnlJpy']));candidate.append(float(d['candidatePnlJpy']))
        for offset,values,label in ((-.23,ctrl,'Control'),(0,old,'R54'),(.23,candidate,'CCMG')):
            ax.bar([j+offset for j in range(2)],values,width=.23,label=label)
        ax.axhline(0,color='black',linewidth=.6);ax.set_xticks(range(2),names);ax.set_ylabel('Aggregate JPY, known paired');ax.legend()
        save(f'{k:02d}_winner_{th}.png',f'Winner >= {th}% ; unresolved fills excluded')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,th in zip(axes,(5,10)):
        with gzip.open(OUT/'WINNER_MECHANISM_ROWS.jsonl.gz','rt') as f:
            vals=[json.loads(t) for t in f]
        rows=[v for v in vals if v['upsidePct'] is not None and v['upsidePct']>=th]
        data=[[v[name] for v in rows if v[name] is not None] for name in ('controlFillGivebackPp','r54FillGivebackPp','candidateFillGivebackPp')]
        ax.boxplot(data,tick_labels=['Control','R54','CCMG'],showfliers=False)
        ax.set_title(f'>={th}% ; known '+ '/'.join(str(len(d)) for d in data)+f' / {len(rows)}');ax.set_ylabel('Checkpoint close HWM to fill (pp)')
    save('08_certified_giveback.png','Policy-specific observed HWM; no future peak')
    for head in ('5','10'):
        d=p['heads'][head];cal=d['calibration'];centers=[(v['lo']+v['hi'])/2 for v in cal if v['n']]
        truth=[v['observed'] for v in cal if v['n']];size=[v['n'] for v in cal if v['n']]
        fig,ax=plt.subplots(figsize=(6,5));ax.plot([0,1],[0,1],ls=':',color='black')
        ax.scatter(centers,truth,s=[max(25,n*1.3) for n in size],alpha=.65)
        for x,y,n in zip(centers,truth,size):ax.annotate(str(n),(x,y),xytext=(3,3),textcoords='offset points',fontsize=7)
        ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xlabel('Predicted probability');ax.set_ylabel('Observed rate')
        save(f'{9+int(head=="10"):02d}_potential_reliability_{head}.png',f'Potential >= {head}%, OOF N={d["n"]}; size/label N')
    print(sorted(p.name for p in FIG.glob('*.png')))


if __name__=='__main__':run()
