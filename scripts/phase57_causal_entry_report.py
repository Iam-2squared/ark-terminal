"""Deterministic descriptive report; never chooses thresholds or a winning policy."""
import argparse
import collections
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts import phase57_causal_entry_anatomy as a
from scripts.phase57_entry_timing_report import table,fmt


def run(source,output):
    src,out=Path(source),Path(output);out.mkdir(parents=True,exist_ok=False)
    for n,h in a.c.read(src/'manifest.json').items():assert a.c.sha(src/n)==h
    audit=a.c.read(src/'audit.json');m=a.c.read(src/'metrics.json');p=a.c.read(src/'paired-summary.json');diag=a.c.read(src/'diagnostic.json');strata=a.c.read(src/'strata.json')
    records=a.c.read(src/'records.json.gz');trades=a.c.read(src/'trades.json.gz')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'phase57-causal-entry-state-v1'})
    def save(fig,name):
        fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=150,bbox_inches='tight',metadata={'Software':'Phase57 State v1'});fig.savefig(out/(name+'.svg'),bbox_inches='tight',metadata={'Date':None,'Creator':'Phase57 State v1'});plt.close(fig)
    arms=list(a.ARMS);fig,axes=plt.subplots(1,3,figsize=(14,4))
    axes[0].barh(a.PATHS,[audit['pathCounts'].get(k,0) for k in a.PATHS]);axes[0].set_title('Evaluator-only future paths | all 2,155')
    x=np.arange(4);axes[1].bar(x-.18,[m[k]['capture']['3']['rate'] for k in arms],.36,label='+3%');axes[1].bar(x+.18,[m[k]['capture']['5']['rate'] for k in arms],.36,label='+5%');axes[1].set_xticks(x,arms);axes[1].set_ylim(0,100);axes[1].legend();axes[1].set_title('Opportunity Capture | fixed denominator')
    axes[2].bar(arms,[m[k]['fills'] for k in arms]);axes[2].axhline(2155,ls='--',c='gray');axes[2].set_ylim(0,2250);axes[2].set_title('Historical fill proxy throughput');save(fig,'01-paths-and-timing')
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for variant in ('INTRADAY','PLUS_DAILY'):
        fits=[r for r in diag['fits'] if r['variant']==variant]
        axes[0].plot([r['checkpoint'] for r in fits],[r['accuracy']*100 for r in fits],marker='o',label=variant)
        axes[1].plot([r['checkpoint'] for r in fits],[r['balancedAccuracy']*100 for r in fits],marker='o',label=variant)
    for ax,title in zip(axes,['Diagnostic accuracy','Diagnostic balanced accuracy']):ax.set_title(title);ax.set_xlabel('Active minutes after Selector');ax.set_ylabel('%');ax.legend();ax.set_xticks(a.CHECKPOINTS)
    save(fig,'02-daily-ablation')
    state_names=sorted(audit['state0Counts']);fig,axes=plt.subplots(1,2,figsize=(12,5));mat=np.array([[audit['stateTransitions'].get(x+'|'+y,0) for y in state_names] for x in state_names]);den=mat.sum(1,keepdims=True);norm=np.divide(mat,den,out=np.zeros_like(mat,dtype=float),where=den>0)
    im=axes[0].imshow(norm,vmin=0,vmax=1,cmap='Blues');axes[0].set_xticks(range(len(state_names)),state_names,rotation=65);axes[0].set_yticks(range(len(state_names)),state_names);axes[0].set_title('Adjacent observed state transitions');fig.colorbar(im,ax=axes[0])
    for arm in ['B','C','F']:
        rr=[next((r for r in strata if r['kind']=='state' and r['group']==n and r['arm']==arm),None) for n in state_names]
        axes[1].plot(state_names,[r['paired']['priceImprovementPct']['mean'] if r and r['paired']['priceImprovementPct']['mean'] is not None else np.nan for r in rr],marker='o',label=arm)
    axes[1].axhline(0,c='gray');axes[1].set_xticks(range(len(state_names)),state_names,rotation=65);axes[1].set_ylabel('% positive = cheaper than Immediate');axes[1].set_title('Paired price improvement by T0 state');axes[1].legend();save(fig,'03-transitions-state-price')
    fig,axes=plt.subplots(1,2,figsize=(12,4))
    for arm in arms:
        rr=[t['lowProximity']['distancePct'] for t in trades[arm] if t['lowProximity']['distancePct'] is not None]
        axes[0].scatter([arm]*len(rr),rr,alpha=.08,s=8)
    axes[0].set_title('Low distance | eligible cases only');axes[0].set_ylabel('% above oracle low; edge counts in report')
    axes[1].bar(arms,[m[k]['rangeRetention']['median'] if m[k]['rangeRetention']['median'] is not None else np.nan for k in arms]);axes[1].set_title('Same-oracle-high range retention median');axes[1].set_ylabel('% | not realized profit');save(fig,'04-low-retention')
    lines=['# Phase57 Causal Entry State / Path Anatomy v1','',
           '固定2,155 Opportunities。Development内の記述研究。A=Immediate、B=State-aware early、C=State適合Signal、F=10 active-minute fallback。Entryモデルの学習・Freeze・自動昇格は行わない。','',
           '## 3つの問いは別','',
           '1. 値幅の存在: Future Path / ordered Low→later Highはoracle anatomyのみ。既存+3%の値幅1,143件は実現利益ではない。',
           '2. 因果的認識: 日足D-5〜D-1、前日1m、当日closed-prefixでStateとSignalを測定。履歴再構築であり独立knownAt認証ではない。',
           '3. Timing改善: 下表の同一母集団・paired買値・Capture・throughputで検証。条件付きMAEだけを改善成功と扱わない。','',
           '## Future Path 5+1','']
    lines+=table(['Path','N','全2,155比%'],[[k,audit['pathCounts'].get(k,0),100*audit['pathCounts'].get(k,0)/2155] for k in a.PATHS])
    lines+=['','Path6は定義を変更せず理由別に保存。0件のクラスも隠さない。','']+table(['Path6 reason','N'],sorted(audit['path6Reasons'].items()))
    lines+=['','## Recent Daily / Path識別','',f"D-5〜D-1全5日利用可能: {audit['dailyComplete']}/2,155。残りも母集団に保持。returnOCnはn営業日の始値→終値、returnCCnはD-6も必要な通常close-to-close。混同しない。",'',
            '日足理由は6本分（補助D-6含む）の延べ数でOpportunity件数ではない。','']+table(['Reason','延べ日足数'],sorted(audit['dailyReasons'].items()))
    lines+=['','最初の29評価sessionで固定nearest-centroidをfit、後半29で診断。Entry政策学習ではなく、独立OOSでもない。後刻チェックポイントはラベルの一部を既に観測しているので、早期予測性能と混同しない。','']
    lines+=table(['T+active min','Inputs','Fit N','Test N','Accuracy%','Balanced%'],[[r['checkpoint'],r['variant'],r['fitN'],r['testN'],100*r['accuracy'],100*r['balancedAccuracy']] for r in diag['fits']])
    lines+=['','confusion・fit median/SD/centroid・session/month/time安定性はdiagnostic.json、全Path別feature分布とeffect sizeはfeature-separation.json.gzに保存。閾値を選ぶ材料として再最適化していない。','',
            '## Fixed-population Timing comparison','']
    headers=['Arm','N','Fill','+3 Capture%','+5 Capture%','Paired買値改善mean%','MAE30 median%','WAIT median','Range retained median%']
    rows=[[k,2155,m[k]['fills'],m[k]['capture']['3']['rate'],m[k]['capture']['5']['rate'],p[k]['priceImprovementPct']['mean'],m[k]['30']['MAE']['median'],m[k]['delay']['median'],m[k]['rangeRetention']['median']] for k in arms]
    lines+=table(headers,rows)
    with (out/'comparison.csv').open('w',newline='') as f:w=csv.writer(f);w.writerow(headers);w.writerows(rows)
    lines+=['','## T0 State別 paired comparison','', 'StateはEntry後のラベルで分けず、Selector時点で固定。Fill時Stateはtradesに別保存。','']
    lines+=table(['State','Arm','N','Fill','Price改善mean%','Low distance median%','Retention median%','+3 Capture%','+5 Capture%','MFE30 median%','MAE30 median%','WAIT median'],
                 [[r['group'],r['arm'],r['metrics']['opportunities'],r['metrics']['fills'],r['paired']['priceImprovementPct']['mean'],r['lowDistance']['median'],r['metrics']['rangeRetention']['median'],r['metrics']['capture']['3']['rate'],r['metrics']['capture']['5']['rate'],r['metrics']['30']['MFE']['median'],r['metrics']['30']['MAE']['median'],r['metrics']['delay']['median']] for r in strata if r['kind']=='state'])
    lines+=['','## State × Signal','', '以下はminute observationsの延べ数で、独立したOpportunity数ではない。first-signalsは各Opportunityの最初の認識時刻・delay・Stateを保存。','']
    lines+=table(['State / Signal','True','False','Unknown'],[[k,v.get('true',0),v.get('false',0),v.get('unknown',0)] for k,v in sorted(audit['signalsByState'].items()) if '|CO|' not in k])
    lines+=['','## Failure / Success anatomy','', 'フラグは重複可能。安く買えたがupsideを失ったケース、MAEとの交換条件を分離。','']
    lines+=table(['Arm','Flag','N'],[[k,f,n] for k in arms for f,n in sorted(p[k]['failureSuccessFlags'].items())])
    lines+=['','## Low proximity / retentionのedge cases','', 'Direct Continuationに底距離を強制しない。Lowより前・同一barを有効な底距離へ変換しない。Retentionは同一oracle HighがEntryより厳密に後の場合のみ。別Highを使う指標はrawで分離。','']
    lines+=table(['Arm','Low status','N'],[[k,f,n] for k in arms for f,n in sorted(m[k]['lowReasons'].items())])
    lines+=['']+table(['Arm','Retention status','N'],[[k,f,n] for k in arms for f,n in sorted(m[k]['rangeRetentionReasons'].items())])
    lines+=['','## Execution / observation audit','']+table(['Arm','BUY attempts','Retry','Fallback intents','Unfilled','理由'],[[k,m[k]['BUYAttemptCount'],m[k]['retryCount'],m[k]['fallbackIntentCount'],2155-m[k]['fills'],str(m[k]['reasons'])] for k in arms])
    lines+=['','30/60m legacy COMPLETEは全1m観測保証ではない。strictCoverage、WAIT中観測数、unavailable理由をrawへ保存。30/60/end MFE/MAE、MaxDD bounds、+1〜+5 remaining hit、session/time/path別比較はmetrics.jsonとstrata.json。no-trade/haltはソースで識別できずUNKNOWNのまま。架空約定なし。','',
            '## Interpretation / feature handoff / STOP','']
    for k in ['B','C']:
        lines.append(f"- {k}: Immediate差 +3 Capture {m[k]['capture']['3']['rate']-m['A']['capture']['3']['rate']:+.3f}pp、+5 {m[k]['capture']['5']['rate']-m['A']['capture']['5']['rate']:+.3f}pp、fill {m[k]['fills']-m['A']['fills']:+d}件、paired買値改善mean {p[k]['priceImprovementPct']['mean']:+.4f}%。")
    lines+=['', 'Immediate超えの総合Evidenceを条件付き改善のみで主張しない。State別の差は記述的関連であり、Stateの因果的効用・独立した予測能力を確定しない。Signal確認の遅さと欠測の寄与はfirst timestamp / WAIT rise / availabilityで併記する。',
            '', 'Entry vNextへ渡す研究feature候補: Daily return/trajectory/HH-HL/LH-LL/range/volume/valueと欠測mask、intraday trend efficiency・drawdown/depth/age・recovery progress・compression ratios/duration・reversal count・VWAP位置/slope/滞在比、6 SignalのEvent/State/Context、relative volume/valueと加速度。Future Path/oracle Low/High/outcomesは渡さない。',
            '', 'この再利用Development診断だけでvNextを学習・FreezeするEvidenceが十分とは判定しない。モデル・閾値探索、Dictionary追加、Holdout開封、NEW EXIT、Selector変更、Paper/Live、注文送信は未実施。Safety9 flags全false。STOP。',
            '', '## Plots','', '![Path and timing](01-paths-and-timing.png)','![Daily ablation](02-daily-ablation.png)','![Transitions](03-transitions-state-price.png)','![Low retention](04-low-retention.png)','']
    (out/'REPORT-ja.md').write_text('\n'.join(lines))
    a.c.write(out/'manifest.json',{f.name:a.c.sha(f) for f in sorted(out.iterdir()) if f.is_file()})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);x=p.parse_args();run(x.source,x.output)
