"""Render saved first-measurement evidence only. Never fit/evaluate a candidate."""
import argparse
import json
from pathlib import Path
from scripts import phase57_integrated_long_entry_v1 as z


def fmt(x,d=3):
    if x is None:return 'UNKNOWN / n=0'
    if isinstance(x,bool):return 'PASS' if x else 'FAIL'
    if isinstance(x,int):return str(x)
    return f'{x:.{d}f}' if isinstance(x,float) else str(x)


def pct(x):return 'UNKNOWN' if x is None else f'{100*x:.2f}%'


def build(audit):
    p=z.protocol();base=z.BASE;tr=z.m.read(base/'train/summary.json');va=z.m.read(base/'validation/summary.json');tm=z.m.read(base/'train/manifest.json');vm=z.m.read(base/'validation/manifest.json');s=va['overall'];lines=[]
    def para(t):lines.extend([t,''])
    def table(headers,rows):
        lines.append('| '+' | '.join(headers)+' |');lines.append('| '+' | '.join(['---']*len(headers))+' |')
        lines.extend('| '+' | '.join(str(v).replace('|',' / ') for v in row)+' |' for row in rows);lines.append('')
    para('# COMPREHENSIVE INTEGRATED LONG ENTRY v1 — First Measurement')
    para('Decision: **FIRST_INTEGRATED_MEASUREMENT_COMPLETE**  \nOVERALL_STATUS: **'+va['classification']['overallStatus']+'**  \nCandidate status: **INTEGRATED_LONG_ENTRY_V1_VALIDATION_'+va['classification']['overallStatus']+'_NOT_FROZEN**')
    para('今回は統合候補1本の初回性能測定。結果後の修正・再学習は0。CandidateのFreeze/KILL判断を自動化せず、結果を固定してSTOP。DEV TEST / Fresh / OOSは評価していない。')
    para('## Git・固定契約・上流')
    table(['項目','固定値'],[['開始HEAD',p['sourceHead']],['Protocol precommit',z.PROTOCOL_COMMIT],['Protocol SHA256',z.PROTOCOL_SHA],['Feature manifest SHA256',p['featureManifestSHA256']],['Model SHA256',tm['modelSHA256']],['Training manifest SHA256',z.m.sha(base/'train/manifest.json')],['Validation ledger SHA256',z.m.sha(base/'validation/ledger.json.gz')],['PR','Iam-2squared/ark-terminal #587 / Open / Draft / unmerged at start'],['Branch','research/phase57-long-only-cash-equity'],['Final checked HEAD','GitHub Actions final-ci-receipt.json; exact SHA in final user report']])
    para('¥75 Selector、Frozen NEW Opportunity Generator、INITIAL/DIP identity、Candidate A、Fixed12 fallback・cost0.05ppはsource pinsと既存freeze pinsで照合。変更なし。v1/v2/v3の失敗Evidenceは保存したまま。')
    para('## 単一Architectureと情報制約')
    para('DecisionTreeRegressorの3出力共有木。max_depth=4、min_samples_leaf=100、criterion=squared_error、random_state=57。最大16葉、TRAINのみ1 fit、calibration0、sweep0。出力はurgent/viable/failureの葉内重み付き比率であり、校正済み確率とは扱わない。TRAIN中央値補完＋全入力missing indicator、scalingはidentity。各Opportunityの学習weight合計1。')
    para('既存Inventory66項目 = AVAILABLE_PIT16 / DERIVABLE_PIT27 / MISSING15 / FUTURE_ONLY_FORBIDDEN8。モデル入力66は別の数え方で、利用可能な従来43入力＋既存v3状態記述23。欠損15・禁止8を投入していない。66という数の一致は偶然。')
    table(['入力family','入力数'],[[k,len(v)] for k,v in z.m.read(base/'feature-manifest.json')['families'].items()])
    para('Selector / time / breadth、trend・range・momentum、path・volatility、anchorのrelativeVolume/VWAP等、post-opportunity Pullback/Stabilization/Reclaim/Reversal/Continuationを統合。動的volume・VWAP・market/sector・order-bookは利用不能。anchor情報を最新値に見せかけていない。provider publication latencyは保存sourceから独立検証できず、completed-bar availabilityの研究上の意味に限定。')
    table(['Route','固定意味'],[['A','t0: urgent>=.25 OR viable>=.40 & failure<.50 →即時BUY'],['B','delay>0: observed pullback＋support/reclaim/turn＋viable>=.20 & failure<.50 →BUY'],['C','5分ずつWAIT、最大15分。途中のurgent/continuation、またはcapのviable contextでBUY'],['D','failure>=.75 & viable<.10でSKIP。cap非適格、missing、boundaryでEXPIRE']])
    para('優先順はProtocol exact。Pullback単体ではBUYしない。Route A/B/C/D terminal attributionは互いに排他的だが、WAIT membershipはA/B/C/D terminalと別の集計。NO_EVENTから一律SKIPする規則はない。同じOpportunityに複数Entryしない。')
    para('## Datasetと分母')
    table(['partition','sessions','全Opportunity','common60完全評価','実際のcounterfactual ENTER','完全評価ENTER'],[['TRAIN',38,tr['overall']['emitted'],tr['overall']['commonComplete'],tr['overall']['enteredAll'],tr['overall']['enteredCommon']],['VALIDATION',19,s['emitted'],s['commonComplete'],s['enteredAll'],s['enteredCommon']],['DEV TEST',19,885,'未評価','未評価','未評価']])
    para(f"TRAIN fitは{tm['trainingEpisodes']} episodes / {tm['trainingStates']} states。全76 Developmentのsource bundleをidentity確認後、対象partitionへ絞ってからPIT・label・outcome処理。DEV TESTはintegrated candidateの推論・outcome評価0。過去の一般Development exposureと区別し、Freshとは呼ばない。今回Validation19は明示的にexposedと記録。")
    para('性能主分母はoriginal opportunity+60 clock minutesを同一segment内で完全評価できた機会。Entry側も同じ終点。MAEは自分のEntry後30分のstrict30もpaired比較し、短い残存期間だけによる改善を区別する。全発行機会は欠損・打切りを含め全件ledgerに残す。価格・MFE・MAEのpaired指標はEntryしたsubsetであり、逃したwinnerを含むpreservation指標と必ず同時に読む。')
    para('## Target / Observed / Gap / Status')
    table(['metric','target','observed','gap','unit','status'],[[k,fmt(v['target']),fmt(v['observed']),fmt(v['gap']),v['unit'],v['status']] for k,v in va['classification']['metrics'].items()])
    table(['Composite gate','status'],[[k,fmt(v)] for k,v in va['classification']['compositeGates'].items()])
    para('Near-Miss幅はfraction0.05 / pp0.05 / count10を事前固定。全PASSだけPASS。非定義分母はHARD_FAIL。CompositeはPASS/FAIL、Integrity不成立はHARD_FAIL。Near-Missは修正許可を意味しない。')
    para('## B0 Immediateとの比較')
    table(['metric','B0 Immediate','Integrated'],[['Opportunity n',s['emitted'],s['emitted']],['Reference outcome evaluable',s['referenceEvaluable'],s['referenceEvaluable']],['Complete n',s['commonComplete'],s['commonComplete']],['Actual ENTER on complete',s['commonComplete'],s['enteredCommon']],['Entry coverage on complete','100%',pct(s['entryCoverage'])],['ENTER all emitted','参考: reference evaluable '+str(s['referenceEvaluable']),s['enteredAll']],['Coverage all emitted','baseline reference '+pct(z.fraction(s['referenceEvaluable'],s['emitted'])),pct(s['eventualEntryRateAll'])],['Mean delay minutes',0,fmt(s['delay']['mean'])],['Median delay minutes',0,fmt(s['delay']['median'])],['Mean Entry price on same entered pairs',fmt(s['baselineEntryPrice']['mean']),fmt(s['entryPrice']['mean'])],['Mean price improvement pp',0,fmt(s['priceImprovement']['mean'])],['Common MAE mean paired',fmt(s['baselinePairedMAE']['mean']),fmt(s['entryPairedMAE']['mean'])],['Common MAE median paired',fmt(s['baselinePairedMAE']['median']),fmt(s['entryPairedMAE']['median'])],['Common MAE p10 paired',fmt(s['baselinePairedMAE']['p10']),fmt(s['entryPairedMAE']['p10'])],['Common MAE p05 paired',fmt(s['baselinePairedMAE']['p05']),fmt(s['entryPairedMAE']['p05'])],['Worst common MAE paired',fmt(s['baselinePairedMAE']['min']),fmt(s['entryPairedMAE']['min'])],['Strict30 MAE median paired',fmt(s['baselineStrict30MAE']['median']),fmt(s['entryStrict30MAE']['median'])],['Strict30 MAE p05 paired',fmt(s['baselineStrict30MAE']['p05']),fmt(s['entryStrict30MAE']['p05'])],['Mean remaining MFE paired',fmt(s['baselinePairedMFE']['mean']),fmt(s['entryPairedMFE']['mean'])],['Remaining MFE ratio paired','100%',pct(s['remainingMFERatio'])]])
    table(['Entry improvement distribution','pp/rate'],[[k,fmt(v)] for k,v in s['priceImprovement'].items()]+[['favorableRate',pct(s['favorableRate'])],['worseRate',pct(s['worseRate'])]])
    table(['delay min','ENTER count'],[[k,n] for k,n in s['delayBins'].items()]+[['SKIP',s['skip']],['EXPIRE',s['expire']]])
    table(['Threshold','Baseline winner n','entered','remaining preserved','preservation','missed','no-entry winner','winner before Entry'],[[k,v['baseline'],v['entered'],v['preserved'],pct(v['rate']),v['missed'],s['noEntryWinner'][k],s['winnerBeforeEntry'][k]] for k,v in s['preservation'].items()])
    table(['Class','n','entered','remaining +3','rate +3'],[[k,v['n'],v['entered'],v['preserved3'],pct(v['rate3'])] for k,v in s['classes'].items()])
    para('## Risk attribution')
    table(['tail','B0 all','B0 same entered','Integrated entered','BETTER_ENTRY_LOCATION reduction','SKIP_AVOIDANCE reduction','strict30 same-pair reduction'],[[k,t['baselineAll'],t['baselineEnteredPair'],t['entryPair'],s['riskAttribution'][k]['BETTER_ENTRY_LOCATION'],s['riskAttribution'][k]['SKIP_AVOIDANCE'],s['riskAttribution'][k]['strict30_BETTER_ENTRY_LOCATION']] for k,t in s['tails'].items()])
    para('SKIP_AVOIDANCEは実際のMODEL_SKIPに加え、WAIT cap / boundary / missingによる非Entryも含む会計上の名称。理由別件数は以下。総件数減少だけを良いEntry Locationの証明に使わない。')
    table(['tail','非Entry理由別'],[[k,json.dumps(v['nonEntryByReason'],sort_keys=True)] for k,v in s['riskAttribution'].items()])
    para('## Routes・WAIT・Path classes')
    table(['terminal route','全発行n','割合','BUY0','delayed BUY','WAIT経験','SKIP','EXPIRE','price pp','MAE median strict30差','MFE ratio','+3 rate','+5 rate'],[[k,v['emitted'],pct(s['routeShares'][k]),v['buyNow'],v['delayedBuy'],v['waitStarted'],v['skip'],v['expire'],fmt(v['priceImprovement']['mean']),fmt(v['strict30MedianImprovementPP']),pct(v['remainingMFERatio']),pct(v['preservation']['3']['rate']),pct(v['preservation']['5']['rate'])] for k,v in va['routes'].items()])
    wait=va['waitMembership'];wa=audit['partitions']['VALIDATION']['actualWaitElapsedIncludingTerminalMissing']
    table(['WAIT membership','value'],[['開始',wait['emitted']],['eventual BUY',wait['enteredAll']],['eventual SKIP',wait['skip']],['eventual EXPIRE',wait['expire']],['WAIT mean actual elapsed',fmt(wa['mean'])],['WAIT median actual elapsed',fmt(wa['median'])],['WAIT max actual elapsed',fmt(wa['max'])],['price improvement pp',fmt(wait['priceImprovement']['mean'])],['remaining MFE ratio',pct(wait['remainingMFERatio'])],['missed +3',wait['preservation']['3']['missed']],['missed +5',wait['preservation']['5']['missed']]])
    para('WAITが最後にmissing stateへ進んだ場合、保存summaryのwaitDurationAllは最後のscored timestampを示す。上表はintegrity auditで最後のattempted5分も含めた実経過時間。policy/evidenceの変更はしていない。')
    table(['Path class','完全評価n','BUY0','delayed BUY','WAIT経験','SKIP','EXPIRE','Entry coverage','price pp','MAE median差','MFE ratio','+3 preserve','+5 preserve'],[[k,v['commonComplete'],v['buyNow'],v['delayedBuy'],v['waitStarted'],v['skip'],v['expire'],pct(v['entryCoverage']),fmt(v['priceImprovement']['mean']),fmt(v['strict30MedianImprovementPP']),pct(v['remainingMFERatio']),pct(v['preservation']['3']['rate']),pct(v['preservation']['5']['rate'])] for k,v in va['classes'].items()])
    para('PULLBACK_THEN_WINNERとDEEP_PULLBACK_THEN_WINNERは別行で示す。上昇前に押し目があったというEvaluator classはruntime入力ではない。INCONCLUSIVEは不完全期間を含むため、その行のactionsは全発行、完全評価nは別分母。')
    table(['Route','Immediate n/entered/+3','Fast n/entered/+3','Pullback n/entered/+3','ContinuedFailure n/entered'],[[k,' / '.join(str(v['classes']['IMMEDIATE_WINNER'][x]) for x in ['n','entered','preserved3']),' / '.join(str(v['classes']['FAST_WINNER'][x]) for x in ['n','entered','preserved3']),' / '.join(str(v['classes']['PULLBACK_WINNER'][x]) for x in ['n','entered','preserved3']),' / '.join(str(v['classes']['CONTINUED_FAILURE'][x]) for x in ['n','entered'])] for k,v in va['routes'].items()])
    para('## Exact Candidate A economic counterfactual')
    para('Entry Gateが不成立でも、今回の明示指示に従って経済比較を実施。資本配分・Portfolioではない。Entry後のexact Fixed12はregular bars基準であり、昼休みを挟む場合のclock HOLDは120分となり得る。Entry WAITはoriginal segmentを越えない。EXIT semanticsは変更していない。')
    e=va['economic']['overall'];ea=va['economicAudit']
    table(['比較母集団','n'],[['common baseline',s['commonComplete']],['economic paired incl cash',e['pairedN']],['両側Entry outcome paired',e['enteredN']],['UNKNOWN excluded',len(ea['unknownIdentities'])]])
    table(['metric','B0 all evaluable','Integrated incl cash0','B0 entered same-pairs','Integrated entered same-pairs'],[[k,fmt(e['baseline']['net'][k]),fmt(e['policyCashIncluded'][k]),fmt(e['enteredBaseline']['net'][k]),fmt(e['enteredPolicy']['net'][k])] for k in ['n','mean','median','PF','winRate','p05','min']])
    table(['metric','B0 entered same-pairs','Integrated entered same-pairs'],[[metric+' '+stat,fmt(e['enteredBaseline'][metric][stat]),fmt(e['enteredPolicy'][metric][stat])] for metric in ['MFE','MAE','HOLD'] for stat in ['mean','median','p05','min','max']])
    table(['economic delta attribution','pp'],[[k,fmt(v)] for k,v in e['decomposition'].items() if k!='interpretation']+[['paired mean net delta',fmt(e['delta']['mean'])]])
    para('enteredTimingはlocationに加えてEntry開始時刻変更に伴うEXIT評価期間差も含む。非Entry寄与はcoverage/cash effect。両者を厳密な因果帰属と断定しない。Candidate A比改善と、絶対net正/PF>1/実運用収益成立は別。')
    table(['Economic Gate','PASS'],[[k,fmt(v)] for k,v in ea['gates'].items()])
    for label,group in [('routes',va['economic']['routes']),('INITIAL/DIP',va['economic']['cohorts']),('chronological blocks',va['economic']['blocks'])]:
        para('Economic: '+label)
        table(['group','paired n','entered n','B0 mean','Integrated cash mean','delta','PF','p05','entered HOLD mean'],[[k,v['pairedN'],v['enteredN'],fmt(v['baseline']['net']['mean']),fmt(v['policyCashIncluded']['mean']),fmt(v['delta']['mean']),fmt(v['policyCashIncluded']['PF']),fmt(v['policyCashIncluded']['p05']),fmt(v['enteredPolicy']['HOLD']['mean'])] for k,v in group.items()])
    para('## Robustness — 悪いcohort/blockも保持')
    for label,group in [('INITIAL/DIP',va['cohorts']),('Validation chronology',va['blocks']),('TRAIN chronology',tr['blocks']),('candidate breadth',va['breadth']),('session time',va['sessionPart']),('volatility context',va['volatility'])]:
        para(label)
        table(['group','emitted','complete','entered','coverage','routes A/B/C/D','+3','+5','price pp','strict30 median差','strict30 p05差','MFE ratio'],[[k,v['emitted'],v['commonComplete'],v['enteredCommon'],pct(v['entryCoverage']),'/'.join(str(v['terminalRoutes'].get(rt,0)) for rt in 'ABCD'),pct(v['preservation']['3']['rate']),pct(v['preservation']['5']['rate']),fmt(v['priceImprovement']['mean']),fmt(v['strict30MedianImprovementPP']),fmt(v['strict30P05ImprovementPP']),pct(v['remainingMFERatio'])] for k,v in group.items()])
    para('Chronological dates: `'+json.dumps(p['evaluation']['chronologicalBlocks']['VALIDATION'])+'`')
    para('Concentration: `'+json.dumps(va['concentration'],sort_keys=True)+'`')
    ex=va['top3Excluded'];ee=va['economic']['top3Excluded']
    table(['TRAIN-top3除外診断','value'],[['complete n',ex['commonComplete']],['coverage',pct(ex['entryCoverage'])],['+3',pct(ex['preservation']['3']['rate'])],['+5',pct(ex['preservation']['5']['rate'])],['price pp',fmt(ex['priceImprovement']['mean'])],['MAE median差',fmt(ex['strict30MedianImprovementPP'])],['economic mean delta',fmt(ee['delta']['mean'])]])
    para('TRAIN頻度top3のみ事前ルールで除外した診断。再fitやsymbol ruleなし。全session別指標はvalidation/summary.jsonのsessions。volatility区分はTRAIN t0 rangeMean中央値 '+fmt(tm['volatilityMedian'])+' を固定し、欠損も別群に保持。')
    para('## Missingness')
    miss=z.m.read(base/'validation/missingness.json')
    table(['feature','t0 available/n','t0 missing rate','all available states missing rate'],[[k,f"{v['available']}/{v['n']}",pct(v['missingRate']),pct(miss['allAvailableStates'][k]['missingRate'])] for k,v in miss['t0'].items()])
    para('route別・Entry/non-Entry別のvisited-state missingnessはvalidation/missingness.json。未観測のpost-opportunity stateはt0で欠損するのが因果上正しい。missing indicatorはPIT欠損のみ。将来のoutcome可否をindicatorにしていない。')
    para('## Integrity・Tests・CI')
    para('PIT state regeneration、独立Route evaluator、tree各nodeのweighted momentsとeligible split impurity、ledger ID、Entry価格、risk/economic attribution加法整合をPASS。学習再実行0。TRAIN/Validation artifact hash固定。no future-low/MFE/MAE/outcome feature、UNKNOWN_INTRABAR_ORDER、missing fail-closed、session boundary、no duplicate Entryはtargeted testsで確認。')
    table(['partition','state/policy regeneration episodes','independent route decisions'],[[k,v['policyDecisionsRegenerated'],v['independentRouteChecks']] for k,v in audit['partitions'].items()])
    para('Targeted tests30件。Offline predict regression結果はverification/regression.json。最新HEADのCI確認はGitHub Actions final-ci-receipt.jsonと最終報告に記録。全PRの既存EXIT CC Freeze Auditの失敗は、新Entryの性能判定と区別する。CIがGREENでも性能PASSにはしない。')
    table(['Safety','value'],[[k,str(v).lower()] for k,v in p['safety'].items()])
    para('## Final decision')
    para('**FIRST_INTEGRATED_MEASUREMENT_COMPLETE / '+va['classification']['overallStatus']+'**。CandidateはNOT_FROZEN。Validation後のthreshold/feature/model/objective/routing/waitCap/gate/symbolRule/timeRule変更は全0。学習1回、候補1本、Validation初回測定1回。DEV TEST / Fresh / OOS未評価。')
    para('今回の実測範囲で、価格位置・同一Entry機会のMAE改善と、upside Opportunityの高率維持を同時に満たせなかった。WAITは実際に発生したが、非Entry・winner lossが大きい。これは今回固定した統合版の結果であり、Entry Timing一般の不可能性とはしない。次候補、再学習、新データ、Capital/Portfolio、EXIT研究、main mergeへ進まずSTOP。')
    return '\n'.join(lines)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--audit',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out)
    if out.exists():raise FileExistsError(out)
    out.write_text(build(z.m.read(a.audit)))
    print('Saved report:',out)
