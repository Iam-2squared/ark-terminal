"""Render saved Development evidence only. No fit, prediction, policy or replay."""
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-msh-entry-long-v2-development'


def read(path):
    return json.loads(gzip.decompress(path.read_bytes())) if path.suffix=='.gz' else json.loads(path.read_text())


def fmt(value, digits=4):
    if value is None:return 'N/A'
    return f'{value:.{digits}f}' if isinstance(value,float) else str(value)


def pct(value):
    return 'N/A' if value is None else f'{value*100:.2f}%'


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(str(x) for x in row)+' |' for row in rows])+'\n'


def write_csv(name,rows):
    with (BASE/name).open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)


def main():
    r=read(BASE/'run/development.json.gz')
    c=read(ROOT/'predict/research/phase57-msh-entry-long-v2-predevelopment-contract-v1.json')
    threshold_rows=[]
    for stream,replicas in [('CHRONOLOGICAL_INNER_CALIBRATION',r['chronological']),('SYMBOL_DISJOINT_INNER_CALIBRATION',r['symbolDisjoint'])]:
        for f in replicas:
            for t in (1,2,5,10):
                row=f['innerThresholdResults'].get(str(t))
                if row is None:continue
                m=row['metrics'];b=f['innerBaseline']
                flat={'scope':stream,'fold':f['fold'],'heldGroup':f['heldGroup'],
                    'threshold':t,'selectedThreshold':f['selection']['threshold'],
                    'candidateRows':m['candidateRows'],'sessions':m['sessions'],
                    'enterCount':m['enterCount'],'enterRate':m['enterRate'],'enterPerSession':m['enterPerSession'],
                    'uniqueSymbols':m['uniqueSymbols'],'strict30mCount':m['strict30mCount'],'coverageRate':m['coverageRate'],
                    'baselineEnterCount':b['enterCount'],'baselineMeanD30':b['meanD30'],
                    'meanD30':m['meanD30'],'meanD30ImprovementPct':(1-m['meanD30']/b['meanD30'])*100 if m['meanD30'] is not None and b['meanD30'] else None,
                    'ES95D30':m['ES95D30'],'MAEMedian':m['MAE']['median'],'MAEP05':m['MAE']['p05'],'MAEWorst':m['MAE']['worst'],
                    'MFEMean':m['MFE']['mean'],'MFEMedian':m['MFE']['median']}
                for k in (1,2,3,5):
                    for key in ['hits','n','rate']:flat[f'precision{k}_{key}']=m['precision'][str(k)][key]
                    for key in ['anchors','hits','unknownNumerators','rate']:flat[f'preservation{k}_{key}']=m['preservation'][str(k)][key]
                for k in (2,5,10):
                    flat[f'MAE_minus{k}_count']=m['adverseCounts'][str(k)]
                    flat[f'MAE_minus{k}_rate']=m['adverseRates'][str(k)]
                flat['failedGates']=';'.join(g['name']+':'+g['status'] for g in row['gates'] if g['status']!='PASS')
                threshold_rows.append(flat)
    write_csv('all-threshold-metrics.csv',threshold_rows)
    model_rows=[]
    for x in r['fitRecords']:
        t=x['training']
        model_rows.append({'model':x['name'],'candidateTrainingRows':t['candidateRows'],'eligibleRows':t['eligibleRows'],
            'excludedLabelRows':t['excludedLabelRows'],'trainingSymbols':len(t['symbols']),
            'momentumMissing':t['missingCounts'][0],'pullbackMissing':t['missingCounts'][1],
            'momentumWeightedMedian':x['medians'][0],'pullbackWeightedMedian':x['medians'][1],
            'means':json.dumps(x['means']),'stds':json.dumps(x['stds']),
            'modelPayloadSHA':x['artifactSHA'],'modelFileSHA':x['fileSHA'],
            'trainingWeightsSHA':t['weightsSHA'],'weightSum':t['weightSum'],
            'lambda':1,'normalEquationResidualInf':t['normalEquationResidualInf']})
    write_csv('fold-models-and-medians.csv',model_rows)
    limits={**c['numericGates']['primary'],**c['numericGates']['guardrails']}
    write_csv('all-frozen-gates.csv',[{'gate':g['name'],'limit':limits[g['name'].split(':')[-1]],'status':g['status'],'reason':g.get('reason','')} for g in r['allFrozenGates']])
    lines=['# MSH-Entry LONG v2 — Development result','',f"**{r['status']}**",'',
        '**Selected threshold: NONE。** 時系列4foldとsymbol-disjoint 5群×4foldの全24組で、固定候補1/2/5/10のいずれもinner calibrationの全条件を満たさなかった。',
        '契約の `SELECTION_INCONCLUSIVE_NO_CANDIDATE` に従い、該当foldのouter refit / predictionを停止した。Formal OOFと選定済みv2 Portfolioは未成立。未生成行をSKIPや損益0にしていない。',
        '', '**学習は実施済み:** inner model fit 24、inner calibration predictions 10,000行、固定閾値の評価96組。10,000行は重複期間・別modelの評価を含み、独立した10,000候補やOOFではない。',
        '**実装・配線:** 同じ5入力、fold内weighted median/scaling、全symbol共通weight、λ=1、保存・reload、state、score不要Equal adapterを実装した。元の277件のEqual weights/pathが一致。Frozen Selector/v1/EXIT/Allocation/cash ledgerは変更していない。',
        '', '## Git / identity', '',
        '| Item | Value |','|---|---|',
        '| Branch | `research/phase57-long-only-cash-equity` |',
        '| PR | [#587](https://github.com/Iam-2squared/ark-terminal/pull/587), Draft / unmerged |',
        '| Contract freeze head | `b7fb91c495858881c913e83bafb0ed0027f013c0` |',
        '| Development data head | `4114f49bc30dbf133061a718e5a1ff3fa8aed611` |',
        '| Latest main at task-start audit | `d00af22145f624dc16eb7d9e625a0f7c2f5eb1e1` |',
        '| Final head / latest main / final CI | Exact final values are returned in the Work completion report after publication; this file does not contain its own enclosing commit hash. |',
        f"| Contract SHA | `{r['contractSHA']}` |",
        f"| Selector commit | `{c['identity']['selectorFreezeCommit']}` |",
        f"| Selector payload SHA | `{c['identity']['selectorPayloadSHA']}` |",
        f"| Selector Ridge SHA | `{c['identity']['selectorRidgeSHA']}` |",
        f"| v1 candidate SHA | `{c['identity']['v1CandidateSHA']}` |",
        f"| v1 model SHA | `{c['identity']['v1ModelSHA']}` |",
        f"| v1 scaler SHA | `{c['identity']['v1ScalerSHA']}` |",
        f"| Frozen277 identity | `{c['identity']['v1EnterIdentitySHA']}` |",
        '| v2 identity | `MSH_ENTRY_LONG_V2_D30_RIDGE_V1`; 24 inner models, no final selected model |',
        f"| Global Budget SHA | `{c['dataProtection']['globalBudgetSHA']}` |",
        f"| All3800 path SHA | `{r['pathSHA']}` |",'',
        'modelごとのpayload/file SHA、weight SHA、weighted medians、欠損数は [fold-models-and-medians.csv](fold-models-and-medians.csv)。実装SHAは [prefit-tests.json](prefit-tests.json)。詳細モデルは `run/models/`、全結果は [development.json.gz](run/development.json.gz)。',
        '', '## Target / data / feature / model', '',
        'D30=max(0,−strict30m MAE)、percentage points、6 completed 5m bars、30 wall-clock minutes。future D30は教師labelのみ。1828 labelable / 3800 candidates。訓練対象は旧277/181に限定しない。2024-09-17–2025-01-09の76 sessions / 760 timestamps / 934 symbolsを再利用。',
        'Selection Event単位。fit内のeligible rowsについて `w_i=1/(S*d_s*n_sd)` を全symbol共通で使用。同symbolの反復行を独立証拠にしない。モデルのexcluded rowsは全てlabel censoringで、表に件数とIDを保存。評価Entryからfuture labelabilityで行を落としていない。',
        '入力順序は `frozenSelectorRidgeScore, directionalMomentum3Pct, directionalPullback6Pct, momentum3Missing, pullback6Missing`。全3800でraw missing数は0 / 1324 / 1590。必須score、既存PIT prefix情報、original statusだけで入力を構築。',
        'Momentum/Pullback欠損をfit内weighted medianとmissing indicatorsで扱い、3 raw inputsだけをfit内weighted mean/population stdで標準化。flagsは0/1。global median、0埋め、forward-fill、future-fill、別session補完はない。',
        'モデルはweighted L2 linear Ridge 1 family、λ=1、unpenalized intercept、NumPy2.3.5 / Python3.12 / float64 / threads=1、numpy.linalg.solve。出力max(0, rawLinear)。ENTER/SKIPのみ、最初のENTER signalで同symbol-sessionをlatch。score sizingなし。',
        '', '### 時系列inner fitの実績', '',
        table(['Fold','eligible rows','excluded labels','symbols','Momentum missing / median','Pullback missing / median'],[
            [i+1,x['training']['eligibleRows'],x['training']['excludedLabelRows'],len(x['training']['symbols']),
             f"{x['training']['missingCounts'][0]} / {fmt(x['medians'][0])}",
             f"{x['training']['missingCounts'][1]} / {fmt(x['medians'][1])}"] for i,x in enumerate(r['fitRecords'][:4])]),
        '## CV / threshold selection', '',
        'Outer train/eval ordinals: 1–16→17–31、1–31→32–46、1–46→47–61、1–61→62–76。各train prefixの先頭floor(3n/4)をinner fit、残りをcalibrationとした。評価期間のfeatures/labelsをfit statisticsへ渡していない。',
        'symbol groupは固定SHA256 mod5。対象groupをinner fit・calibration・outer refitから除外する設計とテストを実施した。今回20組ともinner selectionで停止したため、held-symbol outer性能は未測定。',
        'session overlap=0 / held-symbol overlap=0 / OOF duplicate=0。ただし **OOF生成行数はchronological 0/3000、symbol-disjoint 0/3000**。duplicate0を完走の証拠にしない。最初の16 warmup sessionsと後半60評価sessionsを混ぜない。',
        '', '### 全chronological候補（inner calibrationのみ）', '',
        '各foldでbaselineの期間・candidate集合・Preservation定義を一致させた。calibration期間は重複するため、この16行を合算した独立成績は出さない。残り80組を含む全96組と全要求metricは [all-threshold-metrics.csv](all-threshold-metrics.csv)。', '',
        table(['Fold','τ','v1 ENTER','v2 ENTER','strict N','mean D30','改善率','+1 Precision','+2 Precision','+3 Preservation','+5 Preservation'],[
            [x['fold'],x['threshold'],x['baselineEnterCount'],x['enterCount'],x['strict30mCount'],fmt(x['meanD30']),
             'N/A' if x['meanD30ImprovementPct'] is None else fmt(x['meanD30ImprovementPct'],2)+'%',
             pct(x['precision1_rate']),pct(x['precision2_rate']),pct(x['preservation3_rate']),pct(x['preservation5_rate'])]
             for x in threshold_rows if x['scope']=='CHRONOLOGICAL_INNER_CALIBRATION']),
        'τ=1はENTERが1 / 2 / 0 / 0でthroughput等を満たさない。τ=2はmean D30を各foldで11.62% / 37.11% / 17.54% / 11.90%改善した一方、+1/+2 Precision guardrailsを全4foldで下回り、ES95とcoverageにも不成立がある。τ=5/10でも精度条件を満たさなかった。',
        'この結果は「平均逆行幅が小さい候補を多く通すこと」と「上昇OpportunityのあるEntryを高精度で通すこと」が同じではないことを示すinner診断。Portfolio改善やcross-symbol generalizationの成立は示していない。',
        '閾値選択は契約の8つのEntry側条件を全て満たす候補→mean D30最小→Preservation→throughput→最大τ。全24組で候補0のためNONE。閾値・lambda・features・weights・Gatesを変更していない。',
        '', '## Entry comparison / coverage', '',
        table(['Item','Frozen v1 full76','v1 shared evaluation60','selected v2'],[
            ['ENTER',r['baselineFull76']['enterCount'],r['baselineGate60']['enterCount'],'N/A'],
            ['ENTER/session',fmt(r['baselineFull76']['enterPerSession']),fmt(r['baselineGate60']['enterPerSession']),'N/A'],
            ['strict30m',r['baselineFull76']['strict30mCount'],r['baselineGate60']['strict30mCount'],'N/A'],
            ['unique symbols',r['baselineFull76']['uniqueSymbols'],r['baselineGate60']['uniqueSymbols'],'N/A'],
            ['mean D30',fmt(r['baselineFull76']['meanD30']),fmt(r['baselineGate60']['meanD30']),'N/A'],
            ['MAE median',fmt(r['baselineFull76']['MAE']['median']),fmt(r['baselineGate60']['MAE']['median']),'N/A'],
            ['MAE p05',fmt(r['baselineFull76']['MAE']['p05']),fmt(r['baselineGate60']['MAE']['p05']),'N/A'],
            ['MAE worst',fmt(r['baselineFull76']['MAE']['worst']),fmt(r['baselineGate60']['MAE']['worst']),'N/A'],
            ['MFE median',fmt(r['baselineFull76']['MFE']['median']),fmt(r['baselineGate60']['MFE']['median']),'N/A']]),
        table(['Level','v1 full76 Precision','v1 eval60 Precision','v1 eval60 Preservation','selected v2'],[
            [k,pct(r['baselineFull76']['precision'][str(k)]['rate']),pct(r['baselineGate60']['precision'][str(k)]['rate']),
             pct(r['baselineGate60']['preservation'][str(k)]['rate']),'N/A'] for k in (1,2,3,5)]),
        'eval60のMAE<=−2 / −5 / −10は66 / 23 / 10件（159 strict paths）。Preservationはfirst Top5の元の30分endpointまでにEntry価格から残る上昇幅を測る契約定義。既存の別定義のPreservation値を混ぜない。',
        f"全3800のchosen EXIT-resolvableは{r['coverage']['allCandidatesExitResolvable']}。v1 eval60は232 ENTER→159 strict30m→171 EXIT-resolvable→Portfolio accepted6。v2はselected streamが存在せず、ENTER/strict/EXIT-resolvable/acceptedはN/Aであり0ではない。",
        '', '## Same-downstream cash replay', '',
        'Frozen Selector→各Entry→LONG_EXIT_BAR5_TWO_LOWER_CLOSES_V1→Equal/EQUAL_MAX3→同じledger。100万円、100株、max concurrent10、budget divisor3、round-trip cost0.05% on entry notional、EXIT後に同時刻Entry。',
        '3,800候補のpathを既存Development checkpointsから復元し、raw/normalized SHAと旧277 pathの完全一致を確認。旧v1 E[L]を要求するCLIへdummy scoreを渡さず、score-free connectorから同じallocateV3(V3_0_EQUAL)を呼ぶ。既存replay logicの変更なし。',
        '**Baseline全streamもFinal Equity / Return / MaxDDが未確定。** 2024-10-15 10:30の89180が10:50のbar欠損で未解決となり、335,300円の購入資金が拘束された。cash 671,699.925円を最終資産とは扱わない。',
        'v1 eval60: accepted6 / rejected226 / closed5 / unresolved1。reject理由はCURRENT_EQUITY_UNKNOWN175、SYMBOL_ALREADY_OPEN40、NO_REMAINING_REGULAR_BAR11。v2には選定済みEntryがないため、比較Portfolioを捏造しない。',
        'closed5件だけの参考値: net PnL +7,083.75円、PF1.1676、Win20%、Median−2.1777%、worst−4.9580%、p05−4.7206%。全Portfolio成績ではない。average utilization / Final Equity / Return / MaxDDはN/A。',
        '旧173 complete-caseの+23.05%は今回のfull causal streamに置き換えられない。この研究ではunknown positionの価格を補完せず、その後のequity-based allocationも元の拒否条件を維持した。',
        '', '### Concentration / exclusion', '',
        'v1 closed-only参考: profitable1 / losing3 / unique4 symbols。positive HHI1.0000、effective contributors1、Top1/Top3 share100%。negative HHI0.40655、effective2.45975、Top1 share55.19%、Top3 share100%。median symbol contribution−6,560.375円、標準偏差20,363.43649円。',
        'closed-only Top1 contributorは39360。profit contributorが1symbolしかないためTop3除外も同じ1symbolを除いた診断で、十分なTop3 sampleではない。両除外replayとも未解決positionが残り、Final Equity/Return/MaxDDはN/A。選定v2のHHI・contribution・除外結果もN/A。89180をblacklistにしていない。',
        '', '## Every Frozen Gate / Guardrail', '',
        'inner calibrationの各候補のPASS/FAIL/INCONCLUSIVEはCSVと原本に全件保存した。以下は**選定済みOOF streamに対するFormal gates**で、未生成のため全てINCONCLUSIVE。innerのFAILをOOF成績として転記しない。', '',
        table(['Gate','Frozen limit','Formal status'],[[g['name'],limits[g['name'].split(':')[-1]],g['status']] for g in r['allFrozenGates']]),
        'Frozen ContractのINCONCLUSIVEを今回指定の最終status **BLOCKED** へ対応づけた。BORDERLINE用のgate緩和はない。選定済みcandidateが存在しないことが主blockerであり、coverageによるPortfolio未確定も独立した制約。',
        '', '## Tests / integrity / data budget', '',
        'Project fit前にPython45 tests＋path projection4 tests PASS。D30/feature order/missing/weighting/λ/objective/determinism/serialization/state、CV/symbol leakage、NONE時のouter停止、同じcash ledgerとのparityをsynthetic/contract testsで確認した。',
        '追加のEvidence integrity testsと最終head CIはpublish前後に確認し、Work最終報告へ記載。CIではProject modelを再fitせずsynthetic testsと保存済みEvidence監査だけを実行する。',
        'Contract deviations=0 / feature changes=0 / model tuning=0 / threshold additions=0。モデルfitとpredictionの実装SHAはpre-fit receiptから変更していない。',
        'Fresh / Entry OOS / EXIT OOS / Prospective / J-Quants / Yahoo / other provider price requests = 全て0。価格データは76-session既存cacheの再利用のみ。checkpoint artifactのGitHub転送は価格provider再取得ではない。Fresh195 sessionsを温存。SHORT evaluation=0。',
        'executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted = 全9項目false。main mergeなし。',
        'Historical Conditional Universe: Frozen Selectorにはfuture-label availabilityによるmembership制約が残る。full live-universe PIT、Fresh/OOS、Production Readyを主張しない。89180の低価格・1円刻みのexecution uncertaintyも残し、price/tick/spread proxyやsymbol filterを追加していない。',
        '', '## Exact next action', '',
        '**STOP。** 別指示で、固定候補が全foldでNONEになった原因をレビューする。τ1でthroughputが失われ、τ2以上で平均逆行改善とOpportunity precision維持が両立しないこと、coverage guardrailの違反を根拠に、次の契約判断を行う。今回の場でv2.1・別target・別features・別gateを作らない。Fresh/OOSへ進まない。','']
    (BASE/'README.md').write_text('\n'.join(lines))
    print(json.dumps({'thresholdRows':len(threshold_rows),'models':len(model_rows),'formalGates':len(r['allFrozenGates']),'fitOrPrediction':0}))


if __name__=='__main__':main()
