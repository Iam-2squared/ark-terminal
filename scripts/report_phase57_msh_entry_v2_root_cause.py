"""Render saved root-cause diagnostics. No fit, prediction, replay or new policy."""
import collections
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-msh-entry-long-v2-root-cause'


def read(path):
    b = path.read_bytes()
    return json.loads(gzip.decompress(b) if path.suffix == '.gz' else b)


def number(v, digits=4):
    return 'N/A' if v is None else f'{v:,.{digits}f}'


def pct(v):
    return 'N/A' if v is None else f'{100*v:.2f}%'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(str(v) for v in r) + ' |' for r in rows])


def main():
    x = read(BASE / 'review.json.gz'); decision = read(BASE / 'root-cause-decision.json')
    scope = read(BASE / 'analysis-scope.json'); chrono = x['units'][:4]
    lines = ['# MSH-Entry LONG v2 — Root Cause Review', '',
      '**MSH_ENTRY_LONG_V2_ROOT_CAUSE_REVIEW_COMPLETE**', '',
      '**Primary: RC9 MULTIPLE。次の設計判断: D — SEPARATE_OPPORTUNITY_AND_RISK_AXES。**', '',
      '中心問題は、D30だけの採用条件でv1のOpportunity品質判定を置き換え、低Opportunityの候補を大量に追加したこと。局所的なwinnerの誤棄却と、早いENTERによる後続判断のlatchも併存する。D30が無意味とは断定しないが、平均D30のv1比改善だけでRisk modelの有効性が証明されたとも扱わない。', '',
      'COMPLETEは保存された採用集合の不成立理由と次の設計要件の整理完了を意味する。個々のfeatureの因果効果、D30予測の銘柄横断性能、Portfolio改善は未証明。', '',
      '## Identity / scope', '',
      table(['Item', 'Value'], [
        ['Branch', '`research/phase57-long-only-cash-equity`'],
        ['PR', '[#587](https://github.com/Iam-2squared/ark-terminal/pull/587), Draft / unmerged'],
        ['Source Development head', '`' + scope['sourceHead'] + '`'],
        ['Latest main at direct start audit', '`d00af22145f624dc16eb7d9e625a0f7c2f5eb1e1`'],
        ['Final head / final CI', 'Publication後にWork最終報告へ記載。自己参照commit hashはこの文書へ埋め込まない。'],
        ['Contract SHA', '`' + scope['contractSHA'] + '`'],
        ['Development Evidence SHA', '`' + scope['developmentEvidenceSHA'] + '`'],
        ['Root Cause Evidence SHA', '[manifest.sha256](manifest.sha256)'],
        ['Previous run', '24 successful inner fits / 10,000 calibration rows / 96 threshold evaluations'],
        ['Reconfirmed', '24 NONE / outer OOF 0 / selected v2 Portfolioなし'],
        ['This review', 'new fit=0 / new prediction=0 / new OOF=0 / new Portfolio replay=0']]), '',
      'Historical / Development / IN-SAMPLE / Outcome-exposedの76-session conditional universeのみ。Frozen Selector、v1、EXIT、Equal、cash ledger、5入力、Target、λ、CV、missing、weighting、thresholds、Gatesを一切変更していない。前Evidenceの82ファイルのSHAを照合した。', '',
      '## 保存不足と解析方法', '',
      '**前回の保存不足:** innerモデルとENTER ID・集計値は保存されているが、10,000行のrawPrediction / predictedD30自体は未保存。今回の新prediction禁止に従い再生成していない。連続予測値との相関・残差・数値calibrationはN/A。', '',
      '保存ENTER IDと固定state・入力有効性から、ENTER前のRISK_REJECTと、ENTER後のSTATE_ALREADY_ENTEREDを分離した。後者をリスク棄却に数えない。全入力が有効でmissing stateも既存modelに対応することを確認した上での論理的なstate復元であり、予測値や新しい判断の生成ではない。', '',
      '入力寄与は保存係数・scale・medianを使用した各入力単独の加算項の分布。5項とinterceptを足し合わせず、個別予測値を復元していない。Feature ablation、因果効果の推定、新しいEntry ruleは行っていない。', '',
      '## 1. 全thresholdの不成立再確認', '',
      '各fold/groupの完全な理由は [threshold-failure-reproduction.csv](threshold-failure-reproduction.csv)。保存された96組の全ENTER集合から主要metricを再集計し、全Gate判定を独立に照合した。', '',
      table(['τ', '+1 Precision FAIL', '+2 Precision FAIL', 'Mean D30 FAIL', 'Coverage FAIL', 'Throughput FAIL'], [
        [t, x['failureSummaryByThreshold'][str(t)].get('precision1RatioMin:FAIL', 0),
         x['failureSummaryByThreshold'][str(t)].get('precision2RatioMin:FAIL', 0),
         x['failureSummaryByThreshold'][str(t)].get('adverseMeanRatioMax:FAIL', 0),
         x['failureSummaryByThreshold'][str(t)].get('absoluteStrictLabelCoverageGapMax:FAIL', 0),
         x['failureSummaryByThreshold'][str(t)].get('throughputRatioMin:FAIL', 0)] for t in (1, 2, 5, 10)]), '',
      '分母は各24組。FAIL以外にも未定義のINCONCLUSIVEがあり、残りをPASSとみなさない。τ1はthroughput FAIL23組、+5 Preservation FAIL23組。τ2/5/10は+1 Precisionが24/24 FAIL、+2は23/24 FAIL。全24組で全条件を満たす候補なし。Gateが厳しすぎたという後付け判断はしない。', '',
      '## 2. Threshold2 — chronological inner結果', '',
      table(['Fold', 'v1→v2 ENTER', 'Mean D30 v1→v2', 'D30改善', '+1 Precision v1→v2', '+2 Precision v1→v2', '+3/+5 Preservation v2', 'Throughput比'], [
        [u['fold'], f"{u['v1']['enterCount']}→{u['threshold2']['enterCount']}",
         f"{number(u['v1']['meanD30'])}→{number(u['threshold2']['meanD30'])}",
         pct(1-u['threshold2']['meanD30']/u['v1']['meanD30']),
         pct(u['v1']['precision']['1']['rate'])+'→'+pct(u['threshold2']['precision']['1']['rate']),
         pct(u['v1']['precision']['2']['rate'])+'→'+pct(u['threshold2']['precision']['2']['rate']),
         pct(u['threshold2']['preservation']['3']['rate'])+' / '+pct(u['threshold2']['preservation']['5']['rate']),
         number(u['threshold2']['enterCount']/u['v1']['enterCount'],2)+'×'] for u in chrono]), '',
      '全24組の+1/+2/+3/+5 Precision・Preservation、ENTER/strict数、棄却数は [threshold2-by-unit.csv](threshold2-by-unit.csv)。ここはinner calibrationでありouter OOFではない。PreservationはFrozen Contractのfirst Top5 anchorから元の30分endpointまでのremaining opportunity定義。v1比で+3/+5 Preservationはchronological4/4を満たすが、Precisionは満たさない。', '',
      '## 3. SKIP理由 / A–F cohort', '',
      table(['Fold', 'ENTER', 'Risk rejection', '既ENTERのstate SKIP', 'A risk棄却', 'B +1/+2未満3棄却', 'C +3/+5棄却', 'D adverse採用', 'E good accept', 'F censor全候補'], [
        [u['fold'],u['stateCounts'].get('ENTER',0),u['stateCounts'].get('RISK_REJECT',0),u['stateCounts'].get('STATE_ALREADY_ENTERED',0),
         *[u['cohorts']['overlappingFlags'].get(k,0) for k in ['A_CORRECT_RISK_REJECTION','B_FALSE_REJECTION_LOW_OPPORTUNITY','C_FALSE_REJECTION_HIGH_OPPORTUNITY','D_FALSE_ACCEPT_RISK','E_GOOD_ACCEPT','F_CENSORED_UNKNOWN']]] for u in chrono]), '',
      'A=D30>=2の直接棄却、B=1<=MFE<3の直接棄却、C=MFE>=3の直接棄却、D=ENTERかつD30>=2、E=ENTERかつD30<2・MFE>=1。AとB/Cは重複する。低risk・低Opportunityの採用/棄却はOTHERとして保存し、無理にgood/badにしない。Fは全候補のlabel未観測で、0や負例へ変換しない。全候補の排他的分類も [candidate-attribution.ndjson.gz](candidate-attribution.ndjson.gz) に保存。', '',
      '## 4. Opportunity sacrifice / risk benefit', '',
      table(['Fold', 'Risk棄却 known / censored', '棄却+1', '棄却+2', '棄却+3', '棄却+5', '棄却D30>=2/5/10', '採用D30>=2/5/10'], [
        [u['fold'],f"{u['stateOutcomes']['RISK_REJECT']['known']} / {u['stateOutcomes']['RISK_REJECT']['censored']}",
         *[f"{u['rejectedWinners'][str(k)]['count']} ({pct(u['rejectedWinners'][str(k)]['fractionOfActiveWinners'])})" for k in (1,2,3,5)],
         '/'.join(str(u['rejectedTails'][str(k)]['count']) for k in (2,5,10)),
         '/'.join(str(u['stateOutcomes']['ENTER']['adverse'][str(k)]['count']) for k in (2,5,10))] for u in chrono]), '',
      '括弧内はそのfoldのactive decisionに存在する評価可能winnerを分母とする棄却率。stateで既にlatchされた後続行を分母に足さない。', '',
      table(['Fold', 'State', 'N', 'Mean D30', 'Median', 'p90', 'p95'], [
        [u['fold'], s, *[number(u['stateOutcomes'][s]['D30'][k],0 if k=='n' else 4) for k in ['n','mean','median','p90','p95']]] for u in chrono for s in ('ENTER','RISK_REJECT')]), '',
      '直接棄却の評価可能21 memberships（unique20）中、+1は20、+2は15、+3は11、+5は6。D30>=2は7、>=5は3、>=10は0。採用側には>=10が5 memberships残った。後半2foldは棄却側のmean D30が採用側より低く、棄却が安定して高riskを分離できたとは言えない。', '',
      table(['Fold', '既存τ5のMean D30', 'τ2−τ5 D30差', 'τ5比改善率'], [
        [u['fold'], number(u['savedThreshold5ContrastDiagnostic']['tau5MeanD30']), number(u['savedThreshold5ContrastDiagnostic']['tau2MinusTau5MeanD30']), number(u['savedThreshold5ContrastDiagnostic']['percentImprovementOverTau5'],2)+'%'] for u in chrono]), '',
      '既に保存されたτ5との差は小さく、fold3では悪化。v1比11.62〜37.11%のmean D30改善の全てを「Risk Vetoが悪いEntryを落とした効果」とは帰属できない。採用母集団と時刻の変化を含む。新control・新thresholdは作っていない。', '',
      '## 5. Rejected Risk × Opportunity matrix', '',
      '行=実現D30、列=strict30m MFE。P0の既存境界をdiagnosticに使用。highRisk>=2、highOpportunity>=3。']
    for u in chrono:
        lines += ['', f"Fold {u['fold']}（censored {u['riskOpportunityMatrices']['riskRejected']['censored']}件は表外）", '',
                  table(['D30 \\ MFE','<1','1–<2','2–<3','3–<5','>=5'], [[name,*values] for name,values in zip(['<1','1–<2','2–<5','5–<10','>=10'],u['riskOpportunityMatrices']['riskRejected']['cells'])])]
    lines += ['', '計21 known membershipsではHighRisk/HighOpp3、HighRisk/LowOpp4、LowRisk/HighOpp8、LowRisk/LowOpp6。HighRisk/HighOppの重なりはあるが、unique8件のLowRisk/HighOpp棄却もあるため、winner sacrificeの全てが不可避なintrinsic overlapではない。同一bar内順序・執行可能性は判定していない。', '',
      '## 6. Precision guardrailの分解', '',
      table(['Fold','共通ENTER known','v1のみ known','v2追加 known','追加群+1 Precision','追加群+2 Precision','v1のみの理由 Risk / latch'], [
        [u['fold'],u['precisionDecomposition']['groups']['common']['known'],u['precisionDecomposition']['groups']['v1Only']['known'],u['precisionDecomposition']['groups']['v2Only']['known'],
         pct(u['precisionDecomposition']['groups']['v2Only']['opportunity']['1']['rate']),pct(u['precisionDecomposition']['groups']['v2Only']['opportunity']['2']['rate']),
         str(u['precisionDecomposition']['v1OnlyReasons'].get('RISK_REJECT',0))+' / '+str(u['precisionDecomposition']['v1OnlyReasons'].get('STATE_ALREADY_ENTERED',0))] for u in chrono]), '',
      table(['Fold','Level','v1除去効果 pt','追加効果 pt','総Precision差 pt'], [
        [u['fold'],'+'+str(k),*[number(100*u['precisionDecomposition']['precisionChange'][str(k)][f],2) for f in ['removalEffect','additionEffect','totalChange']]] for u in chrono for k in (1,2)]), '',
      '除去効果=P(common)−P(v1)、追加効果=P(v2)−P(common)の順序固定の会計分解。因果ablationではない。Fold1はcommon knownが1件だけでwinner removalの影響が大きく、不安定。Fold2–4は+1/+2低下の大半を追加群が説明する。v2先行ENTERによるlatchを、後続v1 winnerのrisk rejectionとして誤認しない。', '',
      'Coverage v1→v2は41.67→45.11%、64.00→43.43%、69.23→48.21%、73.02→51.08%。後半3foldは5ポイント差guardrailに違反。観測済みPrecisionの希薄化は直接確認できるが、未観測部分の真の精度は不明。全censoredを成功/不成功と置いた上下限だけをJSONへ保存し、補完はしていない。', '',
      '## 7. 五入力の係数・scale・寄与', '',
      table(['Fold','Input','coefficient','scale','ENTER平均加算項','Risk棄却平均加算項'], [
        [u['fold'],n,number(a['coefficient'],6),number(a['scale'],6),number(a['additiveTermDistribution']['mean'],6),number(b['additiveTermDistribution']['mean'],6)]
        for u in chrono for n in ['frozenSelectorRidgeScore','directionalMomentum3Pct','directionalPullback6Pct','momentum3Missing','pullback6Missing']
        for a in [next(v for v in u['inputAttribution']['marginalTerms'] if v['group']=='ENTER' and v['input']==n)]
        for b in [next(v for v in u['inputAttribution']['marginalTerms'] if v['group']=='RISK_REJECT' and v['input']==n)]]), '',
      '全24組のcenter、median、raw-unit slope、群別分布は [input-attribution.csv](input-attribution.csv)。Momentum/Pullback係数は24/24で負。より深い直近下落/pullbackを大きいD30へ結びつけ、直接棄却群の正の加算項が大きい。winnerの反発局面も含むため、係数の方向だけで判定品質は認定できない。', '',
      'Ridge Score係数は19/24で正、5/24で負。chronologicalでは−0.013756→+0.008464→+0.041994→+0.056149。Ridge ScoreとMFEの相関は+0.279〜+0.534、actual D30とは+0.043〜+0.147。Opportunity signalをrisk軸へ混ぜるtrade-offは示唆されるが、これが主因との因果証明はない。連続predicted D30との相関は未保存のためN/A。', '',
      '## 8. Missingness', '',
      '全24組の直接リスク棄却138 membershipsは全てMomentum/Pullback両方available。missing indicatorでwinnerを直接大量棄却した、という説明は支持されない。chronological missing係数の大きさは概ね0.006〜0.025で、Momentum/Pullbackの棄却群加算項より小さい。一方、欠損medianへの縮小が採用側でどの程度リスクを隠したかはcounterfactualなしでは未確定。', '',
      table(['Fold','Missing pattern','Rows','ENTER','Risk拒否','Mean D30 known','MFE median known'], [
        [u['fold'],p,v['outcomes']['rows'],v['states'].get('ENTER',0),v['states'].get('RISK_REJECT',0),number(v['outcomes']['D30']['mean']),number(v['outcomes']['MFE']['median'])]
        for u in chrono for p,v in u['inputAttribution']['missingPatterns'].items()]), '',
      'Momentum-only missingの群はこのデータに存在しない。群間差はavailability/session依存を含む記述値。新しいmissing対処、0埋め、median変更は行っていない。', '',
      '## 9. Symbol attribution', '',
      table(['Fold','D30改善の正寄与 Top1 / Top3','最大正寄与symbol','false reject +1 Top1 / Top3','false accept D30>=2 Top1 / Top3'], [
        [u['fold'],pct(u['symbolAttribution']['meanD30ImprovementComposition']['top1ShareOfPositiveMass'])+' / '+pct(u['symbolAttribution']['meanD30ImprovementComposition']['top3ShareOfPositiveMass']),
         u['symbolAttribution']['meanD30ImprovementComposition']['orderedPositive'][0][0],
         pct(u['symbolAttribution']['falseRejectedOpportunityConcentration']['top1ShareOfPositiveMass'])+' / '+pct(u['symbolAttribution']['falseRejectedOpportunityConcentration']['top3ShareOfPositiveMass']),
         pct(u['symbolAttribution']['falseAcceptedRiskConcentration']['top1ShareOfPositiveMass'])+' / '+pct(u['symbolAttribution']['falseAcceptedRiskConcentration']['top3ShareOfPositiveMass'])] for u in chrono]), '',
      'D30寄与はsymbolごとの sum(v1 D30)/N_v1 − sum(v2 D30)/N_v2。総和が全体のmean改善と一致するが、採用集合の構成差でありsymbol固有のmodel効果ではない。表のshare分母は正寄与の合計。負寄与と相殺するnet改善とは別。全symbol値はreview.json.gzへ保存。', '',
      'Chronologicalの棄却+5は6 memberships中5が89180、1が76150（89180は4 distinct sessionsの5 observations）。+3棄却11中5が89180。+5損失機会の集中は大きいが、89180の+12.5/+14.29%は1円刻みのhigh-touchであり実現利益ではない。57590はfold4のD30>=2採用83件中8件。両symbolはsupporting diagnosticのみで、blacklist/price filter/weight変更は作らない。', '',
      '## 10. Chronological / symbol-complement stability', '',
      table(['Scope','Units','D30 10%改善','+1 Precision PASS','+2 PASS','+3 Pres PASS','+5 Pres PASS','Throughput PASS','Coverage PASS','棄却mean D30>採用'], [
        [name,*[s[k] for k in ['units','D30ImprovementAtLeast10Pct','precision1Pass','precision2Pass','preservation3Pass','preservation5Pass','throughputPass','coveragePass','rejectedKnownD30HigherThanAccepted']]] for name,s in x['stability'].items()]), '',
      '**20組はheld symbolを除外した学習と、その補集合のinner calibration。held-symbol outer OOFではない。** +1 Precision低下は20/20で再現するが、未知銘柄への汎化性能は測れていない。Mean D30は13/20で10%以上改善、19/20で非悪化。Risk棄却側のD30が高いのは12/20。', '',
      '時系列は2,000 memberships / unique1,950 candidate events。symbol側8,000 membershipsは重複した補集合。独立した10,000データとして数えない。棄却のknown21もunique20で、70740の同一eventがfold3/4に重複する。', '',
      '## 11. Target / Architecture / Root Cause判定', '',
      '**D30 Target Diagnosis: E INCONCLUSIVE。** D30自体の安定した予測価値を、採用母集団の変化から切り離して認定するEvidenceが足りない。A「signalはあるがdecisionが失敗」は部分的な仮説として残す。新fit・score復元・ablationで救済しない。', '',
      '**Architecture Diagnosis: B RISK_AND_OPPORTUNITY_NEED_SEPARATE_DECISION_AXES。** A「Risk Vetoが強すぎる」は局所的なwinner棄却に当てはまるが、全体のτ2採用は広い。Feature不足やLinear capacity不足はINCONCLUSIVE。Risk Veto全般を廃棄する根拠もない。', '',
      table(['Root code','判定','Evidence / limit'], [[r['code'],r['status'],r['qualification']] for r in decision['secondaryRootCauses']+decision['otherRootCauseDispositions']]), '',
      'Primary RC9 MULTIPLEの内訳は、D30単独のEntry判断と複合品質目的の不一致、採用母集団・時刻の変化、局所的な低risk winner誤棄却。RC2/RC7は部分的な補助説明で、因果確定や例外ruleの根拠ではない。', '',
      '## 12. 独立したPortfolio coverage問題', '',
      table(['Item','Saved value'], [
        ['v1 eval60 ENTER / accepted / closed / unresolved','232 / 6 / 5 / 1'],
        ['Locked positions / purchase notional','1 / 335,300 JPY'],
        ['Position','89180, 2024-10-15 10:30 JST, 47,900 shares'],
        ['Reason','MISSING_BEFORE_EXIT; 2024-10-15 10:50 JST'],
        ['Cash balance','671,699.925 JPY（最終資産ではない）'],
        ['Final Equity / MaxDD','N/A / N/A'],
        ['後続拒否','CURRENT_EQUITY_UNKNOWN175 / SYMBOL_ALREADY_OPEN40 / NO_REMAINING_REGULAR_BAR11'],
        ['Recorded cash releases','5'],
        ['今回のPortfolio replay / engine変更','0 / 0']]), '',
      '未解決1件の記録理由はmissing-before-exit。session-end0、explicit no-trade0、auction0、other0は記録上の分類であり、missingの起源がno-tradeかprovider gapかを判定できたという意味ではない。11件のNO_REMAINING_REGULAR_BARはEntry拒否で、locked positionの原因へ合算しない。以前の+23.05%は173 complete-case subset、今回のfull causal streamとは範囲が異なる。', '',
      '**Problem1＝Entryのrisk/Opportunity品質、Problem2＝未解決positionによるcash lock。両者を混同しない。** 売却・価格補完・cash releaseを捏造せず、ledgerを変更していない。', '',
      '## 13. 次工程とSTOP', '',
      '**Recommendation D: SEPARATE_OPPORTUNITY_AND_RISK_AXES。** 別指示のPre-Development Contractで、Frozen Selectorを保持したまま最低限のOpportunity品質とadverse-risk controlの役割・Entry eligibilityを明確にする。D30を維持するかは未確定のまま別判断に残す。', '',
      'Two-Head/第二model、v1 ENTER限定学習、Opportunity×Risk product、WAIT、XGBoost、追加feature、追加threshold、Gate緩和を自動採用しない。今回の実装はRoot Causeの集計と監査のみ。将来別途許可されたrunでは、per-candidate予測値・missing mask・decision reasonの保存を要件にする。今回の欠落値は再生成しない。', '',
      '## Tests / Safety / counters', '',
      'Root Cause用8 testsを追加: latchとrisk棄却の分離、risk/opportunity重複、censor、Gate境界、Precision分解、単入力寄与、model/runtime呼出禁止、Evidence chain。結果とfinal-head CIはWork最終報告へ記載。既存契約・実装はsource hashesで保護し、CIでもProject fit/predictionを実行しない。', '',
      'new fit / new prediction / new OOF / threshold search / Contract change / Fresh / OOS / Prospective / J-Quants / Yahoo / other provider / SHORT evaluation = 全て0。価格データは追加取得せず、前Development Evidenceを再利用。', '',
      'executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed / liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted = 全9項目false。現物LONG-only、main未merge。', '',
      '**STOP。** 次は別指示のv2.1/Alternative Architecture Contract。今回v2.1を作らず、Gateを緩めず、Freshを開かない。', '']
    (BASE / 'README.md').write_text('\n'.join(lines))
    print(json.dumps({'report': str(BASE / 'README.md'), 'lines': len(lines), 'newFit': 0, 'newPrediction': 0}))


if __name__ == '__main__':
    main()
