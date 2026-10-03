"""Audited static plots and partial-research closeout; never automatic promotion."""
import argparse,csv,os,re,subprocess,json
from pathlib import Path
import numpy as np
from scripts import phase57_behavior_full144 as b

def report(evidence,replay,substrate_replay):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    root=Path(evidence);m=root/'measurement';p=b.verify()
    assert b.read(m/'manifest.json')==b.read(Path(replay)/'manifest.json'),'MEASUREMENT_REGEN'
    assert b.read(root/'substrate/manifest.json')==b.read(Path(substrate_replay)/'manifest.json'),'SUBSTRATE_REGEN'
    for d in [m,root/'substrate']:
        for name,h in b.read(d/'manifest.json').items():assert b.sha(d/name)==h
    reg=b.read(root/'regression/regression.json');assert reg['status']=='PASS',reg
    log=(root/'focused.log').read_text();tests=re.findall(r'Ran (\d+) tests?',log);assert tests and '\nOK' in log
    data=b.read(m/'comparison.json');cov=b.read(m/'coverage.json');effects=b.read(m/'effects.json');session=b.read(m/'session-panels.json');ledger=b.read(m/'evaluation-ledger.json.gz');decisions=b.read(m/'decisions.json');cohort=b.read(m/'cohort.json');audit=b.read(m/'audit.json');controls=b.read(m/'controls.json')
    variants=['S0','S1','S2','S3','S4'];colors=['#607080','#8B6BB1','#187F87','#DC9041','#2968B2'];main={k:data[k]['0.8'] for k in variants}
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titlelocation':'left','figure.facecolor':'white','savefig.facecolor':'white','svg.hashsalt':'phase57-behavior-intelligence-v1'})
    def save(fig,name):
        fig.savefig(root/(name+'.png'),dpi=160,bbox_inches='tight',metadata={'Software':'Ark Terminal Research'});fig.savefig(root/(name+'.svg'),bbox_inches='tight',metadata={'Date':None});plt.close(fig)
    def bar(ax,ys,title,ylabel):
        vals=[np.nan if y is None else y for y in ys];ax.bar(variants,vals,color=colors);ax.set(title=title,ylabel=ylabel);ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
    fig,axs=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    for ax,k,title in zip(axs.flat,['downside1','downside2','downside3'],['MAE30 <= -1%','MAE30 <= -2%','MAE30 <= -3%']):bar(ax,[main[v][k] for v in variants],title,'Rate (%)')
    for ax,metric,title in zip(axs.flat[3:],['median','p05','worst5Mean'],['MAE30 median','MAE30 5th percentile','MAE30 worst5% mean']):bar(ax,[main[v]['metrics']['mae30'][metric] for v in variants],title,'Return (%)')
    fig.suptitle('Downside | common labeled cohort | S1 unavailable traits retained');save(fig,'01-downside')
    fig,axs=plt.subplots(2,3,figsize=(14,8),layout='constrained')
    for ax,k in zip(axs.flat,[1,2,3,5]):bar(ax,[main[v]['preservation'][str(k)]['pct'] for v in variants],f'+{k}% opportunity preservation','Baseline winners retained (%)');ax.set_ylim(0,105)
    for ax,k in zip(axs.flat[4:],[3,5]):bar(ax,[main[v]['lowThenHighRetention'][str(k)]['pct'] for v in variants],f'LOW_THEN_HIGH +{k}% winners','Retained (%)');ax.set_ylim(0,105)
    save(fig,'02-preservation')
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for ax,t in zip(axs,[3,5]):
        for name,color in zip(variants,colors):
            for f in p['retentionFractions']:
                q=data[name][str(f)];xx=q['preservation'][str(t)]['pct'];yy=main['S0']['downside2']-q['downside2'] if q['downside2'] is not None else None
                if xx is None or yy is None:continue
                ax.scatter(xx,yy,c=color,s=80 if f==.8 else 22,label=name if f==.8 else None)
                if f==.8:ax.annotate(name,(xx,yy),xytext=(4,5),textcoords='offset points')
        ax.axhline(0,c='#888888',lw=.7);ax.axvline(90,c='#888888',lw=.7,ls='--');ax.set(title=f'Downside reduction vs +{t}% preservation',xlabel='Winners retained (%)',ylabel='MAE30 <= -2% reduction (pp)');ax.legend(fontsize=8)
    save(fig,'03-tradeoff')
    fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained');names=list(b.VARIANTS)
    for ax,metric,title in zip(axs,['downside2','p3','p5'],['Downside rate','+3% preservation','+5% preservation']):
        ys=[data[k]['0.8']['downside2'] if metric=='downside2' else data[k]['0.8']['preservation'][metric[1:]]['pct'] for k in names]
        ax.barh(names,[np.nan if v is None else v for v in ys],color='#2968B2');ax.invert_yaxis();ax.set(title=title,xlabel='%')
    save(fig,'04-ablation')
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    states=list(cov);axs[0].barh(states,[cov[k]['n'] for k in states],color='#607080');axs[0].invert_yaxis();axs[0].set(title='WHO states | categories can overlap',xlabel='Evaluation candidates')
    axs[1].axis('off');axs[1].text(.02,.85,'Reliable WHO value effect: INCONCLUSIVE\n\nFormal judgment available only near\nthe end of Development; no fit support.\n\nUnavailable is not zero.\nS1 retains these candidates.\nS4 can use past-only state information.\n\nNo current 234-symbol whitelist backfill.',va='top',fontsize=13)
    save(fig,'05-coverage')
    fig,axs=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for name,color in zip(variants,colors):
        for ax,key in zip(axs,['mae30','mfeEnd']):
            xs=sorted(x['labels'][key] for x in ledger if x['retained80'][name] and x['labels']['mae30'] is not None and x['labels']['mfeEnd'] is not None)
            if xs:ax.plot(xs,np.arange(1,len(xs)+1)/len(xs),label=name,color=color)
    for ax,key in zip(axs,['MAE30','Session MFE']):ax.set(title=key+' empirical CDF',xlabel='Return (%)',ylabel='Cumulative fraction');ax.legend()
    save(fig,'06-distributions')
    fig,axs=plt.subplots(2,1,figsize=(13,8),layout='constrained');days=p['evaluationSessions']
    for name,color in zip(variants,colors):
        axs[0].plot(days,[session[name][d]['downside2'] for d in days],label=name,color=color,marker='.',lw=1)
        axs[1].plot(days,[session[name][d]['preservation']['3']['pct'] for d in days],label=name,color=color,marker='.',lw=1)
    for ax,title in zip(axs,['Session downside <= -2%','Session +3% preservation']):ax.set(title=title,ylabel='%');ax.set_xticks(days[::6]);ax.tick_params(axis='x',rotation=60);ax.legend(ncol=5)
    save(fig,'07-stability')
    fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    bar(axs[0],[main[v]['retainedCommonN'] for v in variants],'Usable common labels','Candidate count');bar(axs[1],[main[v]['symbolConcentration']['HHI'] for v in variants],'Symbol concentration HHI','HHI');bar(axs[2],[main[v]['symbolConcentration']['symbols'] for v in variants],'Unique symbols','Symbols');save(fig,'08-sample-concentration')
    funnel=b.read(m/'full144-funnel.json');inv=b.read(root/'substrate/session-inventory.json');horizons=b.read(m/'independent-horizon-panels.json')
    fig,axs=plt.subplots(1,2,figsize=(13,5),layout='constrained');names=[k for k,v in funnel.items() if isinstance(v,dict)]
    for ax,key in zip(axs,['sessions','events']):
        ax.barh(names,[funnel[k][key] for k in names]);ax.invert_yaxis();ax.set(title=f'Full144 input audit | {key}',xlabel='Count (availability, not exclusion)')
    save(fig,'09-full144-funnel')
    fig,axs=plt.subplots(2,1,figsize=(13,7),layout='constrained');xs=np.arange(len(inv))
    for key in ['WHO_AVAILABLE','RECENT_AVAILABLE','NOW_AVAILABLE']:axs[0].plot(xs,[x[key] for x in inv],label=key)
    for key in ['OUTCOME_30M_AVAILABLE','OUTCOME_SESSION_END_AVAILABLE','COMMON_EVALUABLE']:axs[1].plot(xs,[x[key] for x in inv],label=key)
    for ax in axs:ax.set(xlabel='Manifest session index (all144)',ylabel='Available events');ax.legend()
    save(fig,'10-all-session-availability')
    assert funnel['inputSessions']==144 and len(inv)==144 and main['S0']['commonCohortN']>0,'FULL144_COMMON_COMPARISON_NOT_ESTABLISHED'
    assert len({q['commonCohortSHA256'] for q in main.values()})==1
    receipt={'executionHead':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'runId':os.environ.get('GITHUB_RUN_ID'),'focusedTests':int(tests[-1]),'regression':reg,'substrateRegeneration':True,'measurementRegeneration':True,'safety':b.SAFETY}
    gate={'status':'FULL144_INPUT_COMPARISON_COMPLETE_WITH_EXPLICIT_AVAILABILITY_LIMITS','all144Audited':True,'commonComparisonEstablished':True,'noFutureLeakageAdditionalInputs':True,'dictionaryPastOnly':True,'recentPreviousDayOnly':True,'intradayClosedBarOnly':True,'upstreamLimitation':'Frozen historical model and L0 admission are inherited/reused Development, not independently prospective PIT-certified','dictionaryValueEffect':'INCONCLUSIVE_NO_CAUSAL_FIT_SUPPORT','commonHoldoutOpened':0,'sealedOpened':0,'nextEntryDevelopmentAllowed':False,'automaticPromotionAllowed':False,'safety':b.SAFETY}
    b.write(root/'completion-gate.json',gate);b.write(root/'ci-receipt.json',receipt)
    def fmt(x):return 'N/A' if x is None else f'{x:.3f}' if isinstance(x,float) else str(x)
    metrics=[('Candidate population',lambda q:q['allCandidates']),('Retained candidates',lambda q:q['retainedAllCandidates']),('Common evaluable population',lambda q:q['commonCohortN']),('Retained common evaluable',lambda q:q['retainedCommonN']),('MAE30 median %',lambda q:q['metrics']['mae30']['median']),('MAE30 p05 %',lambda q:q['metrics']['mae30']['p05']),('MAE30 worst5 mean %',lambda q:q['metrics']['mae30']['worst5Mean']),*[(f'-{t}% downside rate %',lambda q,t=t:q['downside'+str(t)]) for t in [1,2,3]],*[(f'+{t}% preservation / winner retention %',lambda q,t=t:q['preservation'][str(t)]['pct']) for t in [1,2,3,5]],*[(f'LOW_THEN_HIGH +{t}% retention %',lambda q,t=t:q['lowThenHighRetention'][str(t)]['pct']) for t in [3,5]],('MFE session median %',lambda q:q['metrics']['mfeEnd']['median']),('MAE session median %',lambda q:q['metrics']['maeEnd']['median']),('MAE60 median %',lambda q:q['metrics']['mae60']['median']),('Return30 mean %',lambda q:q['metrics']['return30']['mean']),('Return30 median %',lambda q:q['metrics']['return30']['median']),('Session return mean %',lambda q:q['metrics']['returnEnd']['mean']),('Session return median %',lambda q:q['metrics']['returnEnd']['median']),('Positive30 rate %',lambda q:q['positiveRate']),('Downside utility mean %',lambda q:q['utilityMean'])]
    lines=['# Phase57 Full144 Development Remeasurement','',gate['status'],'',f"144日すべてを入力監査。候補生成 {funnel['candidates']['sessions']}日 / {funnel['candidates']['events']}件、全期間の共通outcome {funnel['COMMON_EVALUABLE']['sessions']}日 / {funnel['COMMON_EVALUABLE']['events']}件。",'',f"時系列分割は事前固定: fit80日（〜{p['fitSessions'][-1]}）・embargo5日・evaluation59日（{p['evaluationSessions'][0]}〜{p['evaluationSessions'][-1]}）。下表はevaluation候補{cohort['evaluationCandidates']}件を母集団とする。全144日のin-sample性能との混同を避け、fit期間の成績は合算しない。",'', '## 原因と修正','', '55日制限は144日manifestではなく既存76日candidate ledgerとのintersectionを採用したため。保存55日のidentity/score/priceはそのまま継承し、追加日は既存Frozenモジュールを呼び出して推論。直前の正確な営業日が許可データにない日は、欠測理由を台帳に保存して候補生成UNAVAILABLEとする。sealed前日や古い終値で補完しない。','', '元分足の全144日response hashとTime分布をsource-only auditで先に固定。15:25〜15:29は通常の取引バーがないプレ・クロージングであり、15:30引けは独立約定。存在しない5分足は作らない。実1分足からのOHLCV集約は既存仕様のまま。','', '[JPX売買成立方法](https://www.jpx.co.jp/equities/trading/domestic/04.html) / [J-Quants分足仕様](https://jpx-jquants.com/ja/spec/eq-bars-minute)','', '修正評価は通常立会終了（旧15:00、新15:25）と引け板寄せ（旧15:00、新15:30）を分離。session-endは元minuteのvolume合計・high/lowとdailyの一致、実引け約定、decision後pathを必須とする。全取引sourceが整合する場合の取引なし区間は補間せず、観測約定だけからextremaを測る。30/60分はwall-clock、昼休み跨ぎ不可、必要5分slot・endpointの実観測を要求。独立horizon集計も保存し、引け欠測が30分集計を消さない。','', '## 共通比較','', '主保持率80%、補助40/60/100%は前回から不変。全Variantに同じ候補・fit/eval・特徴・ridge lambda10・判定閾値。S1はWHO利用不能を理由に削除しないため実保持率が異なりうる。S4はWHO coverageで母集団を絞らない。risk=-MAE30で順位付け、quality=MFEは別保存。high touchは収益・約定ではない。','', '| Metric | S0 Selector | S1 WHO | S2 RECENT | S3 NOW | S4 ALL |','|---|---:|---:|---:|---:|---:|']
    csvrows=[]
    for name,fn in metrics:
        vals=[fn(main[k]) for k in variants];lines.append('| '+name+' | '+' | '.join(fmt(x) for x in vals)+' |');csvrows.append([name,*vals])
    with (root/'comparison.csv').open('w',newline='') as file:
        w=csv.writer(file);w.writerow(['Metric',*variants]);w.writerows(csvrows)
    for name in ['01-downside','02-preservation','03-tradeoff']:lines+=['',f'![{name}]({name}.png)']
    lines+=['','## 判定 / ablation','', '| Variant | 判定 | 理由 |','|---|---|---|']
    for k,x in decisions.items():lines.append(f"| {k} | {x['status']} | {x['reason']} |")
    lines+=['', '事前条件: 同保持予算Frozen順位対照比、-2%下落率改善2pp以上、session block5 bootstrap95%下限>0、+3/+5保持率各90%以上。S4 incrementalはS2/S3/A23比も必要。Development再利用の記述的比較であり独立OOS検定ではない。','', '| Arm | Reduction vs matched Frozen pp | Block95% CI |','|---|---:|---|']
    for k,x in effects.items():lines.append(f"| {k} | {fmt(x['meanReductionPp'])} | {x['movingBlock5CI95']} |")
    lines+=['','![ablation](04-ablation.png)','','## 144日funnel・availability','', '下表の入力availabilityは並列条件であり、WHOなし→候補除外という連続filterではない。正式比較からの除外は共通outcome可用性のみ。日別・event別の理由はmeasurement/availability-reasons.jsonに全件保存。','', '| Stage | Sessions with events | Events |','|---|---:|---:|','| Development input | 144 | — |']
    for k in names:lines.append(f"| {k} | {funnel[k]['sessions']} | {funnel[k]['events']} |")
    lines+=['','![funnel](09-full144-funnel.png)','','![availability](10-all-session-availability.png)','','## WHO coverageと制約','', '正式Temporal状態は2025-08-21終了後にのみ利用可能。traitValue・confidence・uncertainty・nEffは毎decision前日のprefixから再計算。最終profileの値や234銘柄whitelistはbackfillしない。LOW/FAIL/INSUFFICIENT/MISSINGは保持、信頼できる数値入力valueはHIGH/MEDIUM+PASSに限定。fit期間に正式数値がないため、WHOの信頼できるtrait値の追加効果はINCONCLUSIVE。WHO状態を使うS4等の差と、正式trait値の効果を混同しない。','', '| WHO group (overlap possible) | Eval candidates | Symbols |','|---|---:|---:|']
    for k,x in cov.items():lines.append(f"| {k} | {x['n']} | {x['symbols']} |")
    for name in ['05-coverage','06-distributions','07-stability','08-sample-concentration']:lines+=['',f'![{name}]({name}.png)']
    lines+=['','## 検証・境界','',f"Focused tests {receipt['focusedTests']} PASS、全regression PASS。substrate・measurementを各2回生成しmanifest完全一致。144日を全件監査、common cohort同一hash、因果的追加入力、no synthetic/forward fill、Frozen資産不変を確認。",'', 'Common Holdout244とその他sealedの追加開封0。Safety9フラグ全false。追加provider取得0。Frozen Selector本体・Dictionary Gate/Temporal thresholdは変更なし。','', '限界: Frozenモデル/特徴定義はDevelopmentで既に研究済み。既存Frozen L0 admissionは同日Dailyの有効性・corporate action・adjustment情報を使う既存仕様を継承しており、上流全体の独立PIT認証を新たに主張しない。今回のno-future監査はWHO/RECENT/NOW追加入力と下流fit/eval境界。取得時点PITも未認証。', '',f"実行HEAD `{receipt['executionHead']}` / [CI](https://github.com/Iam-2squared/ark-terminal/actions/runs/{receipt['runId']})。PR587 Draft・未merge。",'', 'STOP。NEW Entry / NEW EXIT学習・自動昇格は実施しない。WHO不足や期待した保持率を満たさない場合も、結果に合わせた再調整は行わない。','']
    (root/'REPORT-ja.md').write_text('\n'.join(lines))
    b.write(root/'report-manifest.json',{x.name:b.sha(x) for x in sorted(root.iterdir()) if x.is_file() and x.name!='report-manifest.json'})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--replay',required=True);p.add_argument('--substrate-replay',required=True);a=p.parse_args();report(a.evidence,a.replay,a.substrate_replay)
