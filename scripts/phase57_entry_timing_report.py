"""Read-only census tables/plots; never tunes or selects a timing rule."""
import argparse
import collections
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts import phase57_entry_timing_census as c

NAMES={'A':'Immediate + retry','B':'Continuation','C':'Breakout / expansion',
       'D':'Pullback / recovery','E':'State-aware combination','F':'Fallback at 10m'}
COLORS=['#6b7280','#2563eb','#0891b2','#a855f7','#059669','#ea580c']


def fmt(x,dec=3):
    if x is None:
        return '—'
    if isinstance(x,(int,np.integer)):
        return f'{x:,}'
    return f'{x:,.{dec}f}' if isinstance(x,(float,np.floating)) else str(x)


def table(headers,rows):
    return ['| '+' | '.join(headers)+' |','|'+'---|'*len(headers)]+['| '+' | '.join(fmt(x) for x in row)+' |' for row in rows]


def run(source,output):
    src,out=Path(source),Path(output)
    out.mkdir(parents=True,exist_ok=False)
    manifest=c.read(src/'manifest.json')
    for path,digest in manifest.items():
        assert c.sha(src/path)==digest,path
    m=c.read(src/'metrics.json');p=c.read(src/'paired-summary.json');sg=c.read(src/'signal-summary.json')
    anatomy=c.read(src/'oracle-anatomy.json');co=c.read(src/'cooccurrence.json');cohort=c.read(src/'cohort.json')
    paired=c.read(src/'paired.json.gz');records=c.read(src/'opportunity-records.json.gz');trades=c.read(src/'trades.json.gz')
    paths=c.read(src/'path-stability.json');volume=c.read(src/'volume-context.json')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.titleweight':'bold','figure.facecolor':'white','axes.facecolor':'#f8fafc',
                         'savefig.facecolor':'white','svg.hashsalt':'phase57-entry-timing-census-v1'})
    def save(fig,name):
        fig.savefig(out/(name+'.png'),dpi=160,bbox_inches='tight',metadata={'Software':'Phase57 Census v1'})
        fig.savefig(out/(name+'.svg'),bbox_inches='tight',metadata={'Date':None,'Creator':'Phase57 Census v1'})
        plt.close(fig)
    arms=list(NAMES)
    fig,axes=plt.subplots(2,2,figsize=(13,8))
    fig.suptitle('Entry Timing Census v1 | Same 2,155 Opportunities',fontsize=17,fontweight='bold')
    ax=axes[0,0];values=[m[k]['fills'] for k in arms]
    ax.bar(arms,values,color=COLORS);ax.axhline(2155,color='#334155',ls='--',lw=1)
    ax.set_ylim(0,2350);ax.set_title('Historical fill proxy throughput');ax.set_ylabel('Opportunities')
    for i,v in enumerate(values):ax.text(i,v+25,str(v),ha='center')
    ax=axes[0,1];x=np.arange(6)
    ax.bar(x-.18,[m[k]['capture']['3']['rate'] for k in arms],.36,label='+3%',color='#2563eb')
    ax.bar(x+.18,[m[k]['capture']['5']['rate'] for k in arms],.36,label='+5%',color='#059669')
    ax.set_xticks(x,arms);ax.set_ylim(0,100);ax.set_title('Capture | fixed Selector winner denominator');ax.set_ylabel('%');ax.legend(frameon=False)
    ax=axes[1,0]
    ax.bar(arms,[p[k]['priceImprovementPct']['mean'] for k in arms],color=COLORS)
    ax.axhline(0,color='#334155',lw=.8);ax.set_title('Paired entry price improvement | mean');ax.set_ylabel('% | positive = cheaper than A')
    ax=axes[1,1]
    ax.bar(arms,[p[k]['30']['MAE']['mean'] for k in arms],color=COLORS)
    ax.axhline(0,color='#334155',lw=.8);ax.set_title('Paired 30m MAE change | mean');ax.set_ylabel('percentage points | positive = less adverse')
    fig.text(.5,.015,'A Immediate   B Continuation   C Breakout/expansion   D Recovery   E Combined   F Fallback',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.04,1,.95]);save(fig,'01-paired-comparison')
    fam=list(c.s.FAMILIES);labels=['Continuation','Breakout','Compression /\nexpansion','Higher low','Lower wick','Reclaim']
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    x=np.arange(6)
    axes[0].barh(x-.18,[sg[f]['comparisonWindow']['occurrenceRatePct'] for f in fam],.36,label='Comparison window <=30m',color='#2563eb')
    axes[0].barh(x+.18,[sg[f]['fullCensus']['occurrenceRatePct'] for f in fam],.36,label='Through session end',color='#94a3b8')
    axes[0].set_yticks(x,labels);axes[0].set_xlim(0,105);axes[0].set_xlabel('% of all 2,155');axes[0].legend(fontsize=8,frameon=False);axes[0].set_title('Causal trigger occurrence')
    axes[1].barh(x,[100*sg[f]['comparisonWindow']['unknownBars']/max(1,sg[f]['comparisonWindow']['scheduledBars']) for f in fam],color='#ea580c')
    axes[1].set_yticks(x,labels);axes[1].set_xlim(0,100);axes[1].set_title('Unknown trigger observations');axes[1].set_xlabel('% of scheduled comparison observations')
    fig.tight_layout();save(fig,'02-signal-availability')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    mat=np.array(co['opportunityJaccard'],float);im=axes[0].imshow(mat,vmin=0,vmax=1,cmap='Blues')
    axes[0].set_xticks(range(6),['CONT','BREAK','COMP','HL','WICK','RECL'],rotation=45)
    axes[0].set_yticks(range(6),['CONT','BREAK','COMP','HL','WICK','RECL']);axes[0].set_title('Signal overlap | opportunity Jaccard')
    for i in range(6):
        for j in range(6):axes[0].text(j,i,f'{mat[i,j]:.2f}',ha='center',va='center',color='white' if mat[i,j]>.6 else '#172554')
    fig.colorbar(im,ax=axes[0],fraction=.046)
    vals=[]
    for k in arms:vals.append([t['rangeRetention']['valuePct'] for t in trades[k] if t['rangeRetention']['valuePct'] is not None])
    axes[1].boxplot(vals,tick_labels=arms,showfliers=False)
    axes[1].axhline(100,ls='--',color='#94a3b8');axes[1].axhline(0,color='#334155',lw=.7)
    axes[1].set_title('Oracle range retained | same later high');axes[1].set_ylabel('% | valid-case distribution only')
    axes[1].text(.5,-.14,'No clipping in saved data. Edge-case counts in REPORT.',transform=axes[1].transAxes,ha='center',fontsize=8)
    fig.tight_layout();save(fig,'03-overlap-retention')
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    levels=['1','2','3','4','5','10'];xx=np.arange(6)
    axes[0].bar(xx-.18,[anatomy['thresholds'][v]['selectorToHigh'] for v in levels],.36,label='Selector -> high',color='#6b7280')
    axes[0].bar(xx+.18,[anatomy['thresholds'][v]['orderedLowLaterHigh'] for v in levels],.36,label='Oracle low -> strictly later high',color='#0891b2')
    axes[0].set_xticks(xx,['+'+v+'%' for v in levels]);axes[0].set_ylabel('Opportunities / 2,155');axes[0].set_title('Range existed | hindsight only');axes[0].legend(fontsize=8,frameon=False)
    axes[1].bar(arms,[m[k]['waitMaxRiseVsImmediatePct']['median'] for k in arms],color=COLORS)
    axes[1].set_title('Observed rise while waiting | median');axes[1].set_ylabel('% above Immediate fill price')
    fig.tight_layout();save(fig,'04-range-wait-tradeoff')
    lines=['# Entry Timing Signal Census v1 — 結果','',
           '**固定2,155 OpportunityのDevelopment診断。Entry vNextの学習・採用・Freezeは行わない。**','',
           f"144 Development sessionsの既存入力を再利用。評価manifestは59日、Opportunityあり58日。全日評価可能{anatomy['fullSessionAvailable']:,}件、評価不能{anatomy['unknownFullSession']}件。Selector→Highが+1%未満の{anatomy['selectorBelow1']}件と評価不能は別集計。",'',
           '## 1. 値幅が存在した — oracle / hindsight','',
           *table(['水準','Selector→High','Low→strictly later High','固定母数'],[[f'+{v}%',anatomy['thresholds'][v]['selectorToHigh'],anatomy['thresholds'][v]['orderedLowLaterHigh'],2155] for v in levels]),'',
           'LowとHighは異なる1m barに限定。同一bar内の順序は推定しない。これは実現利益・Entry精度ではない。','',
           '![Oracle range and waiting](04-range-wait-tradeoff.png)','',
           '## 2. Signalを因果的に認識できた','',
           *table(['系統','比較window発生','発生率%','全日発生','最初delay中央値','unknown bar率%'],[[f,sg[f]['comparisonWindow']['occurrenceCount'],sg[f]['comparisonWindow']['occurrenceRatePct'],sg[f]['fullCensus']['occurrenceCount'],sg[f]['comparisonWindow']['firstDelay']['median'],100*sg[f]['comparisonWindow']['unknownBars']/max(1,sg[f]['comparisonWindow']['scheduledBars'])] for f in fam]),'',
           'CONTINUATIONはState、他5系統はEventがtrigger。bar-start mはm+1に利用可能。pivot時刻へ遡らない。全日時刻と比較windowの最初の時刻を各Opportunity recordに保存。','',
           'Signal未観測は確認済み不発と観測不足を区別。以下のSignalなしにはpartial観測も含むため、完全な不発を意味しない。','',
           *table(['系統','Signal+成功','Signal+失敗','未観測+成功','未観測+失敗','未来評価不能','Signal未観測・観測不足'],[[f]+[sg[f]['comparisonWindow']['contingencies']['3'].get(k,0) for k in ['SIGNAL_SUCCESS','SIGNAL_FAILURE','NO_OBSERVED_SIGNAL_SUCCESS','NO_OBSERVED_SIGNAL_FAILURE']]+[sum(sg[f]['comparisonWindow']['contingencies']['3'].get(k,0) for k in ['SIGNAL_UNKNOWN_OUTCOME','NO_OBSERVED_SIGNAL_UNKNOWN_OUTCOME']),sg[f]['comparisonWindow']['absenceStatus'].get('OBSERVATION_INSUFFICIENT',0)] for f in fam]),'',
           '成功/失敗は将来Selector→High +3%のanatomyラベルのみ。各行の最初5列の件数合計は2,155。最後の観測不足は重複する内訳。','',
           '![Signal availability](02-signal-availability.png)','',
           '## 3. その時点でEntryした場合に改善したか — 同一Opportunity paired比較','',
           'A Immediate+retry / B Continuation / C Breakout・Expansion / D Pullback・Recovery / E Combination / F 固定10 active minutes Fallback。B-FはSignalなしでもFallback。BUY意図は一度立つと失効させず共通30 active minutesまでretry。全て歴史的next observed Open+5bps約定proxy。','',
           *table(['方法','BUY intent件数','BUY attempt回数','fill','fill率%','retry','Fallback intent','delay中央値'],[[k,m[k]['BUYIntentOpportunities'],m[k]['BUYAttemptCount'],m[k]['fills'],m[k]['fillThroughputPct'],m[k]['retryCount'],m[k]['fallbackIntentCount'],m[k]['delay']['median']] for k in arms]),'',
           *table(['方法','+1 Capture%','+2','+3','+4','+5','paired価格改善中央値%','paired N'],[[k]+[m[k]['capture'][str(v)]['rate'] for v in range(1,6)]+[p[k]['priceImprovementPct']['median'],p[k]['priceImprovementPct']['count']] for k in arms]),'',
           'Captureの母数は元のSelector winner集合で固定。価格改善は両方式fillのpaired subsetのみ。未約定・欠測を価格改善0と代入しない。条件付きReturn改善だけでEntry成功とはしない。','',
           *table(['方法','Both fill','Aのみ','候補のみ','両方なし','平均価格改善%','session-equal平均%','session bootstrap 95%'],[[k]+[p[k]['pairStatus'].get(v,0) for v in ['BOTH_FILLED','BASE_ONLY','CANDIDATE_ONLY','NEITHER_FILLED']]+[p[k]['priceImprovementPct']['mean'],p[k]['sessionEqualPriceBootstrap']['mean'] if p[k]['sessionEqualPriceBootstrap'] else None,str(p[k]['sessionEqualPriceBootstrap']['percentile95']) if p[k]['sessionEqualPriceBootstrap'] else None] for k in arms]),'',
           'Bootstrapは既に見たDevelopmentのsession単位記述統計。独立検証・多重比較補正済み有意性の証明ではない。','',
           '![Paired comparison](01-paired-comparison.png)','']
    for h in ('30','60'):
        lines += [f'## {h} active minutes — coverageとpath','',
                  *table(['方法','legacy評価N','strict全1m N','MFE med%','MAE med%','MaxDD med%','adverse bound med%','net平均%','paired MAE差pp','paired return差pp'],[[k,m[k][h]['MFE']['count'],m[k][h]['strict1mCoverage'].get('ALL_1M_OBSERVED',0),m[k][h]['MFE']['median'],m[k][h]['MAE']['median'],m[k][h]['MaxDD']['median'],m[k][h]['MaxDDAdverseBound']['median'],m[k][h]['returnNet']['mean'],p[k][h]['MAE']['mean'],p[k][h]['returnNet']['mean']] for k in arms]),'',
                  *table(['方法','remaining +1 observed hit%','+2','+3','+4','+5','coverage'],[[k]+[m[k][h]['hits'][str(v)]['rate'] for v in range(1,6)]+[json.dumps(m[k][h]['coverage'])] for k in arms]),'',
                  'legacy評価可能は既存の5分slot観測契約。strict全1m観測とは異なる。Hit率はfill母数のobserved lower bound、unknownとupper boundはmetrics.json。MaxDDは同一bar high→low順序を仮定しないconfirmed値とadverse boundを別保存。30m/60mはEntryから測るため、WAIT方式では終了時刻も遅くなる。','']
    lines += ['## Entry→session end / Range Retention','',
              *table(['方法','end MFE med%','end MAE med%','end +1 hits','+2','+3','+4','+5','Range Retention med%','Retention N'],[[k,m[k]['mfeEnd']['median'],m[k]['maeEnd']['median']]+[m[k]['endHits'][str(v)]['hits'] for v in range(1,6)]+[m[k]['rangeRetention']['median'],m[k]['rangeRetention']['count']] for k in arms]),'',
              'Range Retention=100×(同じoracle later High/actual Entry−1)/(同High/oracle Low−1)。評価専用、clippingなし。Entry前のHighや同時刻Highは無効。Entryがoracle Lowより前でも独立statusで残す。別Highを使ったalternative値はrawに分離。','',
              *table(['方法','No fill','観測不足','非正分母','High≦Entry','Entry<Low','Entry≧Low'],[[k]+[m[k]['rangeRetentionReasons'].get(v,0) for v in ['NO_FILL','FULL_SESSION_OBSERVATION_INSUFFICIENT','NONPOSITIVE_DENOMINATOR','ORACLE_HIGH_AT_OR_BEFORE_ENTRY','ENTRY_BEFORE_ORACLE_LOW','ENTRY_AT_OR_AFTER_ORACLE_LOW']] for k in arms]),'',
              '![Overlap and retention](03-overlap-retention.png)','',
              '## Direct Continuationを取り逃したか','',
              '将来anatomy定義: Selector価格から+3%到達が−0.5%押しより先。同一barならAMBIGUOUS。未来pathは当日decisionへ渡さない。','',
              *table(['方法','Direct件数','fill','+3 Capture%','delay中央値','paired価格改善中央値%'],[[v['arm'],v['opportunities'],v['fills'],v['capture']['3']['rate'],v['delay']['median'],v['paired']['priceImprovementPct']['median']] for v in paths if v['bucket']=='DIRECT_CONTINUATION']),'',
              '## WAITの買値改善とupside消費','',
              *table(['方法','paired価格改善med%','WAIT最大上昇med%','WAIT最大上昇p95%','Range Retention paired平均差pp'],[[k,p[k]['priceImprovementPct']['median'],m[k]['waitMaxRiseVsImmediatePct']['median'],m[k]['waitMaxRiseVsImmediatePct']['p95'],p[k]['rangeRetentionDeltaPp']['mean']] for k in arms]),'',
              'WAIT最大上昇はImmediate fillから実Entry直前までの観測High。欠測区間がある場合は下限的な観測値。positiveな買値改善と、失った上昇・未約定増加を同時に読む。','',
              '## Volume / Trading Value context','',
              '1/3/5/10m sums、直前同長window比、前営業日同clock slot比、compression contraction/expansion、wick confirmation比を全系統共通で保存。欠測はnull、observed count付き。Volume増加によるBUY gateはない。','',
              *table(['系統','3m relative Value bucket','signal件数','評価30m N','first signal net平均%'],[[v['family'],v['bucket'],v['n'],v['firstSignal30Return']['count'],v['firstSignal30Return']['mean']] for v in volume if v['field']=='3/valueRelativePreviousDay']),'',
              'この表はSignal発生subsetの補助診断でありPrimaryではない。前日同時刻比は1日proxy、歴史的な通常量とは言わない。session/time別の全方式集計はsession-stability.json / time-stability.jsonに保存。','',
              '## 未約定・入力制約','',
              *table(['方法','terminal reasons','attempt results'],[[k,json.dumps(m[k]['reasons']),json.dumps(m[k]['attemptResults'])] for k in arms]),'',
              '- historical knownAtを独立証明したデータではない。閉じたbar-prefixに対する因果的再構成。Frozen upstreamの同日metadata制約を継承。',
              '- missing sourceからHALT/NO_TRADEを捏造せずMISSING_SOURCE_UNCLASSIFIEDと記録。注文・Paper・Liveは行わない。',
              '- 全2,155件を残した。59日manifestの候補0日もsession集計に残す。全144日で再学習した結果ではない。',
              '- Fallbackは全件のBUYを保証しない。WAIT後に価格観測がなくなる可能性をthroughputとpaired statusに明示。',
              '- Common Holdout244未開封。Dictionary追加、Selector変更、NEW EXIT、Entry vNext学習・Freezeなし。9 safety flagsすべてfalse。','',
              '## Reproduction / files','',
              '`python -m unittest -v scripts.test_phase57_entry_timing_census`','',
              '`python -m scripts.phase57_entry_timing_census --output <new-directory>`','',
              '`python -m scripts.phase57_entry_timing_report --source <measurement-directory> --output <new-report-directory>`','',
              'protocol.json / PROTOCOL.md / protocol-lock.json は事前固定。measurement/manifest.jsonがraw全ファイルをhash固定。minute-census/*.json.gzは全時刻のEvent/State/ContextとVolume、opportunity-records.json.gzはfirst timestamps・oracle・全Opportunity、trades/pairedは失敗・Signalなし・欠測も保持。','']
    (out/'REPORT-ja.md').write_text('\n'.join(lines)+'\n')
    with (out/'comparison.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['arm','name','opportunities','fills','capture3Pct','capture5Pct','pairedPriceMedianPct','pairedN','delayMedian','rangeRetentionMedianPct'])
        for k in arms:w.writerow([k,NAMES[k],2155,m[k]['fills'],m[k]['capture']['3']['rate'],m[k]['capture']['5']['rate'],p[k]['priceImprovementPct']['median'],p[k]['priceImprovementPct']['count'],m[k]['delay']['median'],m[k]['rangeRetention']['median']])
    c.write(out/'manifest.json',{f.name:c.sha(f) for f in sorted(out.iterdir())})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
    x=parser.parse_args();run(x.source,x.output)
