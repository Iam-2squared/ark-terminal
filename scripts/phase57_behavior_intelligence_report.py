"""Audited static plots and partial-research closeout; never automatic promotion."""
import argparse,csv,os,re
from pathlib import Path
import numpy as np
from scripts import phase57_behavior_intelligence as b

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
    axs[1].axis('off');axs[1].text(.02,.85,'Reliable WHO value effect: INCONCLUSIVE\n\nFormal temporal judgment unavailable at\nall exact-cohort historical decisions.\n\nUnavailable is not zero.\nS1 retains these candidates.\nS4 can use past-only state information.\n\nNo current 234-symbol whitelist backfill.',va='top',fontsize=13)
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
    for ax,title in zip(axs,['Session downside <= -2%','Session +3% preservation']):ax.set(title=title,ylabel='%');ax.tick_params(axis='x',rotation=60);ax.legend(ncol=5)
    save(fig,'07-stability')
    fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    bar(axs[0],[main[v]['retainedCommonN'] for v in variants],'Usable common labels','Candidate count');bar(axs[1],[main[v]['symbolConcentration']['HHI'] for v in variants],'Symbol concentration HHI','HHI');bar(axs[2],[main[v]['symbolConcentration']['symbols'] for v in variants],'Unique symbols','Symbols');save(fig,'08-sample-concentration')
    tests_n=int(tests[-1]);receipt={'executionHead':os.environ.get('GITHUB_SHA'),'runId':os.environ.get('GITHUB_RUN_ID'),'focusedTests':tests_n,'regression':reg,'substrateRegeneration':True,'measurementRegeneration':True,'safety':b.SAFETY,'pr':587,'draft':True,'merged':False}
    # Whole requested research gate remains blocked; partial exact-cohort results must not masquerade as complete144.
    gate={'status':'PARTIAL_RESEARCH_COMPLETE_ENTRY_DEVELOPMENT_BLOCKED','scope':'55 saved-candidate sessions inside authorized144','reasons':['WHO reliable trait value information is not identifiable before formal judgment availability','89 additional Development sessions require a separately pinned exact Frozen Selector inference cohort; no claim of full144 completion'],'automaticPromotionAllowed':False,'nextEntryDevelopmentAllowed':False,'newDataRequiredForS2S3':False,'dictionaryAdditionalDataNeed':'Not quantified; fixed future-valid support, not Holdout access, is required'}
    b.write(root/'completion-gate.json',gate);b.write(root/'ci-receipt.json',receipt)
    def f(x):return 'N/A' if x is None else f'{x:.3f}' if isinstance(x,float) else str(x)
    metrics=[('Candidates',lambda q:q['retainedAllCandidates']),('Usable common samples',lambda q:q['retainedCommonN']),('MAE30 median %',lambda q:q['metrics']['mae30']['median']),('MAE30 p05 %',lambda q:q['metrics']['mae30']['p05']),('-1% downside rate %',lambda q:q['downside1']),('-2% downside rate %',lambda q:q['downside2']),('-3% downside rate %',lambda q:q['downside3']),*[(f'+{t}% preservation / winner retention %',lambda q,t=t:q['preservation'][str(t)]['pct']) for t in [1,2,3,5]],*[(f'LOW_THEN_HIGH +{t}% retention %',lambda q,t=t:q['lowThenHighRetention'][str(t)]['pct']) for t in [3,5]],('Return30 mean %',lambda q:q['metrics']['return30']['mean']),('Return30 median %',lambda q:q['metrics']['return30']['median']),('Return30 positive %',lambda q:q['positiveRate']),('MAE60 median %',lambda q:q['metrics']['mae60']['median']),('Session MAE median %',lambda q:q['metrics']['maeEnd']['median']),('Session return mean %',lambda q:q['metrics']['returnEnd']['mean']),('Downside adjusted utility %',lambda q:q['utilityMean'])]
    lines=['# Frozen Selector × Behavior Intelligence — Development diagnostic','',f"**{gate['status']}**",'', 'S0〜S4の固定候補55日で比較を実行。許可144日全体の完了とは扱わない。WHOの正式trait値が過去decision時点で利用不可のため、Dictionaryの追加価値はINCONCLUSIVE。Entry/EXITは開始しない。','',f"候補 {cohort['candidateCount']}件。fit {len(p['fitSessions'])}日・{cohort['fitCandidates']}件 → embargo5日 → evaluation {len(p['evaluationSessions'])}日・{cohort['evaluationCandidates']}件。fit終端 {p['fitSessions'][-1]}、evaluation {p['evaluationSessions'][0]}〜{p['evaluationSessions'][-1]}。",'', '## 比較条件','', 'Frozen台帳を同一identity・score・decisionPriceのまま再利用。結果を見たcohort/window/feature/model/threshold変更なし。主保持率80%（各時刻ceil(n×0.8)）、補助40/60/100%。S0は全候補。S1はDictionary利用不能を理由にDROPしないため全候補を保持。S1と他Variantの保持件数差を効果と解釈しない。','', 'Risk: -MAE30の固定Ridge、quality: session MFEの別Ridge。lambda10、学習時中央値補完＋欠測indicator、標準化はfitのみ。raw payloadのnullを数値0へ変換しない。品質scoreは保存のみで主ランキングに不使用。勝者選び直しなし。','', '主評価は30分＋session-endが共に評価可能なcommon complete-case cohort。選択自体は全候補に適用してから評価可否を判定。Outcome欠測候補も台帳に保存。MAE60は追加の観測可能性条件があり、サンプル数を別保存。30/60分はwall-clock・昼休み跨ぎ不可・連続5分スロット必要。session-endは旧anatomyの全regular slots必須、同一5分足内の高安順序はUNKNOWN。High touchは約定・利益ではない。','', '## S0〜S4 主比較','', '| Metric | S0 | S1 WHO | S2 RECENT | S3 NOW | S4 ALL |','|---|---:|---:|---:|---:|---:|']
    csvrows=[]
    for name,fn in metrics:
        vals=[fn(main[k]) for k in variants];lines.append('| '+name+' | '+' | '.join(f(x) for x in vals)+' |');csvrows.append([name,*vals])
    with (root/'comparison.csv').open('w',newline='') as file:
        w=csv.writer(file);w.writerow(['Metric',*variants]);w.writerows(csvrows)
    lines+=['','![Downside](01-downside.png)','','![Preservation](02-preservation.png)','','![Tradeoff](03-tradeoff.png)','','## 固定判定・対照','', '意味ある追加情報の事前条件: 同件数Frozen score対照に対し-2%下落率を2pp以上改善、session block5 bootstrap95%下限>0、+3/+5 preservation各90%以上。bootstrapは再利用Developmentの記述的感度分析であり、confirmatory significance・多重検定済み保証ではない。S4 incrementalはS2/S3/A23すべてに同条件を要求。','', '| Variant | 判定 | 理由 |','|---|---|---|']
    for k,d in decisions.items():lines.append(f"| {k} | {d['status']} | {d['reason']} |")
    lines+=['','| Comparison | Paired sessions | -2% downside reduction pp | Block95% CI |','|---|---:|---:|---|']
    for k,d in effects.items():lines.append(f"| {k} | {d['sessions']} | {f(d['meanReductionPp'])} | {d['movingBlock5CI95']} |")
    lines+=['','| Matched budget control | Common N | -2% downside % | +3% retention % | +5% retention % |','|---|---:|---:|---:|---:|']
    for k,q in controls.items():lines.append(f"| {k} | {q['retainedCommonN']} | {f(q['downside2'])} | {f(q['preservation']['3']['pct'])} | {f(q['preservation']['5']['pct'])} |")
    lines+=['','![Ablation](04-ablation.png)','','## WHO coverage / PIT','', '日別profile/peer/uncertainty/confidenceはdecision前日のmatrix prefixだけで再生成。最終234銘柄・293traitのホワイトリストは使用しない。Temporal判定は2025-08-21終了後にしか利用できず、今回の55日（2024年）ではMISSING_NOT_YET_AVAILABLE。LOW・INSUFFICIENT・Temporal FAIL・MISSINGは別表現を保持し、未判明のFAIL/PASSを過去へ戻さない。値の効果は検証不可。S4やA12/A13に差が出ても、それは過去時点の標本/不確実性状態の効果であり、信頼できる性格値の効果とは言わない。','', 'Coverage-conditioned空群はN/A。欠測の候補をcommon cohortから除外しない。LOW/INSUFFICIENT等は重複可能で合算しない。','', '![Coverage](05-coverage.png)','','![Distributions](06-distributions.png)','','![Stability](07-stability.png)','','![Samples](08-sample-concentration.png)','','## 検証と残課題','', f"Focused {tests_n} PASS。全回帰PASS（詳細ci-receipt.json）。特徴量substrateと測定それぞれ2回再生成manifest完全一致。未来matrix suffix変更不変・future/stale Reader拒否・previous-day-only・欠測と0・共通母集団・fit-only前処理をテスト。",'', 'Common Holdout244/その他sealedの追加開封0。既存暗号化rawは55許可日だけ選択復元し、input-ledgerに記録。保存済みmatrix全体は許可Developmentのみで構成、日別特徴量はprefixに制限。過去exposure台帳不変。Frozen Selector/registry/Gate/Capital/実売買系は不変。安全9フラグは全false。','', 'この診断では追加89日のFrozen候補再推論を未実施。144日全体の比較・WHO正式値効果・ALLの正式値によるincremental効果は未完了。結果を理由に既存Dictionary windowを変更しない。全144への拡張は、固定Selectorの再推論台帳とその価格/causal契約の同一性を別途固定・監査する必要がある。','', '全体のno-future-leakageは独立OOS認定ではない。ここで検証したのは追加特徴量・下流fit/evaluationの時間境界。上流Frozen Selector/Dictionary定義はDevelopmentを既に利用済み、取得時刻のPIT証明もない。性能主張を将来収益に拡張しない。','',f"Execution HEAD `{receipt['executionHead']}` / PR587 Draft未merge / CI {receipt['runId']}。保存HEADは実行commitの子孫。",'', 'STOP。NEW Entry/EXIT本格学習は開始しない。','']
    (root/'REPORT-ja.md').write_text('\n'.join(lines))
    b.write(root/'report-manifest.json',{x.name:b.sha(x) for x in sorted(root.iterdir()) if x.is_file() and x.name!='report-manifest.json'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--replay',required=True);p.add_argument('--substrate-replay',required=True);a=p.parse_args();report(a.evidence,a.replay,a.substrate_replay)
