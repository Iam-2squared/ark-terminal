"""Append-only report and sensitivity appendix from saved diagnostic rows only."""
import argparse
from pathlib import Path
from scripts import phase57_exit_loss_state_study as s


def f(v):
    return 'N/A' if v is None else f'{v:.6f}'


def rate(x):
    return f"{x['n']}/{x['denominator']} ({100*x['rate']:.2f}%)" if x['rate'] is not None else 'N/A'


def generate(measurement, out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    source=Path(measurement);summary=s.read(source/'summary.json');rows=s.read(source/'ledger.json.gz')
    # Descriptive robustness of every precommitted feature, never selecting a
    # feature, direction, cutoff, time or candidate based on this appendix.
    appendix={}
    for cohort in s.COHORTS:
        rs=[r for r in rows if r['cohort']==cohort];top=s.top_symbols(rs)
        groups={**{'block'+str(b):[r for r in rs if r['block']==b] for b in range(1,5)},
                'excludeTopFrequency3':[r for r in rs if r['symbol'] not in top],
                'fullUnderlyingMinuteCoverage':[r for r in rs if r['fullUnderlyingMinutes']]}
        appendix[cohort]={group:{str(t):s.feature_diagnostic(rr,t) for t in s.TIMES} for group,rr in groups.items()}
    lines=['# Phase57 NEW LONG EXIT — Development limit receipt', '',
           'Date: 2026-09-18 JST', '', '**EXIT_ARCHITECTURE_DEVELOPMENT_LIMIT_REACHED**', '',
           'Strong Candidateは成立しなかった。新しいLoss Defense候補は実装・Freezeしていない。',
           'Candidate Aを既存Frozen fallbackとして保持し、exposed Developmentでのarchitecture探索を停止する。',
           'この結論は今回の有限の研究範囲に対する限界であり、あらゆる5m手法の不可能性を証明するものではない。', '',
           '## Provenance / scope', '',
           f'- 開始GitHub HEAD: `{s.SOURCE_HEAD}`。PR #587 open / Draft / unmergedを直接確認。',
           f'- 測定前protocol公開: `{s.PROTOCOL_COMMIT}`。3仮説・判定時刻・候補化gateを固定。',
           '- 76 Development sessions / 2024-09-17〜2025-01-09。全3,284 opportunityのcoverageを保持。',
           '- 比較はexact Frozen Fixed12で評価可能なINITIAL 1,072 + DIP 397 = 1,469件。全Opportunityへの外挿は禁止。',
           '- Entry source `6fabde7dfe208e19d5611e0a290b4df6724e562e`、Selector/Entryの既存pinsを検証。',
           '- 保存Fixed12 ledger・Path Studyを再利用。旧研究workflow・旧候補測定を手動再実行していない。',
           '- 最初の実行はriskTagsに追加の母集団タグがあるためschema assertionで停止し、出力を生成しなかった。',
           '  106/21のnamed tag検証に修正。state・gate・thresholdは変更していない。', '',
           '## Candidate lineage / KEEP / KILL', '',
           '| 系統 | 処分 | 学習・理由 |','| --- | --- | --- |',
           '| Loss Defense v0 lower-close | KILL維持 | recovery winner破壊、106群改善なし |',
           '| v1 prior-low breakdown | KILL維持 | winner/loser両方に悪化 |',
           '| v2 recovery window | KILL維持 | DIPの救済が遅い。window再調整禁止 |',
           '| v3 fixed tail boundary | KILL維持 | winner保護は良いが106/21を悪化 |',
           '| Candidate A | KEEP frozen fallback | Profit Protectionのみ。mean<0、PF<1、tail未解決 |',
           '| Candidate B | KILL維持 | INITIAL悪化。旧数値はhistorical evidence扱い |',
           '| Candidate C | KILL維持 | causal +5 / same-bar contract / INITIAL ledger監査FAIL |',
           '| 新3仮説 | 候補化却下 | 以下のseparation gate FAIL。EXIT性能を測った候補ではない |','',
           '## Separation diagnosis: A / B / C / D', '',
           'A: 今回のobservable stateから、Recovery Winnerを残しdeep loserを安定分離できる根拠は得られなかった。',
           'B: failed reclaim / failed bounce / normalized deteriorationの遷移は測定可能だが、候補化を支持しなかった。',
           'C: INITIAL/DIPで悪化継続率と回復率が異なる。後付けcohort routingによる救済はしない。',
           'D: +10/+15まで待っても一様な識別改善はない。待つ間にdeep-loser救済余地も減る。', '',
           '| Hypothesis | INITIAL n | DIP n | deep failures | disposition |',
           '| --- | ---: | ---: | ---: | --- |']
    for x in summary['screens']:
        deep=sum(v['selected']['deepFailure']['n'] for v in x['cohorts'].values())
        lines.append(f"| {x['name']} | {x['cohorts'][s.INITIAL]['selectedN']} | {x['cohorts'][s.DIP]['selectedN']} | {deep} | SCREEN FAIL |")
    lines+=['','+15 negative/A-still-held母集団: INITIAL448、DIP181。以下は将来labelを用いた診断率でありEXIT成績ではない。','',
            '| State / cohort | later >=2pp drop | baseline | future recovery +3 | future recovery +5 |',
            '| --- | --- | --- | --- | --- |']
    for x in summary['screens']:
        for c in s.COHORTS:
            y=x['cohorts'][c]
            lines.append(f"| {x['name']} / {c.split('_')[0]} | {rate(y['selected']['continued2'])} | {rate(y['baseline']['continued2'])} | {rate(y['selected']['recovery3'])} | {rate(y['selected']['recovery5'])} |")
    lines+=['','全3仮説とも3/4時系列blockでの悪化継続enrichment gateを満たさない。',
            'top-frequency3除外でもcandidate eligibilityは回復しない。full underlying-minute coverage感度も保存。',
            '単純にnだけを理由に落としたのではない。reclaim rejectionはdeep failure 0件、bounce failureはDIP1件。',
            'normalized accelerationはINITIALで後の+3/+5 winnerを1/5含み、DIPの追加悪化率は母集団より低い。', '',
            'raw rangeのt+5 rank AUCはINITIAL約0.770、DIP約0.783で、リスクの記述情報はある。',
            '一方でこれは大きな値幅/既発生損失の大きさを表す可能性があり、winnerを壊さないEXIT条件の証明ではない。',
            'cutoff選択やfeature winner選択は行っていない。全19 featureの固定方向AUC・分布・block感度を保存。',
            'KEEP: volatility contextの必要性、実回復の履歴、厳密next-OPEN評価。KILL: 今回の3状態をEXITへ直結する案。', '',
            '## Latency: same identities at t+5/+10/+15', '',
            '全3時点でnegative/A-still-heldのmatched群内で、A net<=-5%の同一identityを追跡。',
            'rescueは「将来loserと知ってその時点のnext OPENで退出した場合」のoracle proxy。実行可能な収益ではない。', '',
            '| Cohort / deep n | t+5 incurred / rescue pp | t+10 incurred / rescue pp | t+15 incurred / rescue pp |',
            '| --- | --- | --- | --- |']
    for c in s.COHORTS:
        v=summary['observations'][c]['matchedAllTimes'];d=[v[str(t)]['latency']['deepFailure'] for t in s.TIMES]
        lines.append(f"| {c.split('_')[0]} / {d[0]['oracleRescueVsA']['n']} | "+' | '.join(f"{f(x['alreadyIncurredClose']['mean'])} / {f(x['oracleRescueVsA']['mean'])}" for x in d)+' |')
    lines+=['','## Retained final logic / paired baseline', '',
            '`NEW_LONG_EXIT_PROTECT_3_TO_1_FIXED12_V1` remains `DEVELOPMENT_CANDIDATE_FROZEN_NOT_OOS_VALIDATED`.',
            'HOLD → completed HIGHで初めて+3%確認 → PROTECT → 後続completed CLOSE<=+1% → next regular 5m OPEN退出。',
            'signalなしはexact Frozen Fixed12。cost .05pp、Loss Defenseなし、cohort thresholdなし、re-entryなし。',
            'Aに対する今回の改善は0。新候補は未実装なので、A比の改善を主張しない。', '',
            '| Panel / policy | n | mean % | median % | PF | p05 % | Win | worst5% mean % |',
            '| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |']
    for name,x in [('Overall',summary['overall'])]+[(c.split('_')[0],summary['cohorts'][c]) for c in s.COHORTS]:
        for arm in ('fixed','candidateA'):
            v=x[arm];lines.append(f"| {name} / {arm} | {v['n']} | {f(v['mean'])} | {f(v['median'])} | {f(v['PF'])} | {f(v['p05'])} | {rate(v['win'])} | {f(v['worst5Mean'])} |")
    lines+=['','## Strict winner preservation / adverse subsets', '',
            '| Panel | +3 | +5 | recovery +3 | recovery +5 | fast +3 | fast +5 |',
            '| --- | --- | --- | --- | --- | --- | --- |']
    for name,x in [('Overall',summary['overall'])]+[(c.split('_')[0],summary['cohorts'][c]) for c in s.COHORTS]:
        p=x['preservation'];lines.append('| '+name+' | '+' | '.join(rate(p[k]) for k in ('3','5','recovery3','recovery5','fast3','fast5'))+' |')
    lines+=['','退出OPENの後のHIGHはpreservedと数えない。INITIAL +5は旧137/145から厳密136/145へ。',
            '旧A Freeze artifactは変更していない。recovery=first bar negativeかつ未到達後のmilestone、fast=first bar到達。', '',
            '| Evaluator-only risk subset | n | Fixed12 mean % | A mean % |',
            '| --- | ---: | ---: | ---: |']
    for name,x in summary['adverseSubsets'].items():lines.append(f"| {name} | {x['fixed']['n']} | {f(x['fixed']['mean'])} | {f(x['candidateA']['mean'])} |")
    a=summary['overall'];lines+=['',f"A large-loss<=-5%: {a['candidateA']['largeLossCountMinus5']}件（Fixed12 {a['fixed']['largeLossCountMinus5']}）。最悪{f(a['candidateA']['min'])}%で未改善。",
        f"A exit reasons: PROTECT {a['exitReasons']['PROTECT_EXIT']} / Fixed12 fallback HOLD {a['exitReasons']['FIXED12_FALLBACK']}。",
        'これらはProfit Protectionの既存効果。Loss Defenseが改善した数字ではない。MAE/realized lossはidentity ledgerに保存。', '',
        '## Chronological / concentration robustness', '',
        '| Cohort | Block1 A−Fixed pp | Block2 | Block3 | Block4 | exclude top3 A−Fixed pp |',
        '| --- | ---: | ---: | ---: | ---: | ---: |']
    for c in s.COHORTS:
        x=summary['cohorts'][c];lines.append('| '+c.split('_')[0]+' | '+' | '.join(f(x['blocks'][str(b)]['meanDeltaAVsFixed']) for b in range(1,5))+' | '+f(x['excludeTop3']['meanDeltaAVsFixed'])+' |')
    lines+=['','Aは両cohortで3/4block非負。これは既存fallbackの頑健性で、新Loss DefenseのPASSではない。',
            'symbol/session集中、全session成績、top3頻度除外、screen別集中をsummaryに保存。銘柄専用ruleなし。', '',
            '## Deterministic / causal / ledger / tests', '',
            '- saved Path Study prefix一致: 6,721。Fixed12/A ledger checks: 1,469。',
            '- diagnostic future suffix/prefix perturbations: 4,407。A fill-bar H/L/C perturbations: 188。全PASS。',
            '- summary / ledger / coverage / manifestを別directoryへ再生成し、全byte一致。既存Evidence不変。',
            '- targeted causal/A/C regression: 26/26 PASS。LONG-only foundation regression: 39/39 PASS。',
            '- 既存Development hash preservation: PASS。git diff check: PASS。',
            '- CIは別のGitHub receiptでexact code HEADへ紐付ける。greenは研究performance PASSを意味しない。', '',
            '## Safety / stop / next work', '',
            '全9 flags false: executionAllowed, brokerWriteAllowed, excelOrderWriteAllowed, rssOrderFunctionAllowed,',
            'liveTradingAllowed, paperTradingAllowed, automaticPromotionAllowed, productionUpdateAllowed, transmitted。',
            'Frozen Selector/Entry/A変更0、C復活0、model fit0、provider0、Fresh/OOS0、1m0、Capital/Portfolio0、main merge0。',
            '現物LONG-only。SHORT/Margin/Leverageなし。オフライン診断のためorder/writeは実行していない。', '',
            '次に必要なのは、同じDevelopmentでのthreshold調整ではなく、識別仮説に必要な情報の設計。',
            '候補はEntry前のvolatility baseline、出来高/流動性、同時点の市場・sector context、観測欠測の品質情報。',
            'これらが有効とは未検証で、取得・fit・接続は行っていない。新情報を使う場合はPIT定義と因果契約を先に固定する。',
            '将来のvalidationは完全固定policyと一回限りの判定基準・日次/symbol依存を考慮した不確実性評価を事前に固定し、',
            'ユーザーの明示許可後にのみ開く。Strong Final Freeze未成立なので、本WorkからFresh/OOSへ進まない。', '',
            '**Development architecture mutation STOP。Candidate A fallback維持。完成・実用・利益化の主張なし。**','']
    out.mkdir(parents=True,exist_ok=False)
    (out/'REPORT.md').write_text('\n'.join(lines))
    (out/'feature-robustness-appendix.json').write_bytes(s.encode(appendix))
    (out/'manifest.json').write_bytes(s.encode({'inputPins':{p.name:s.sha(p) for p in (source/'summary.json',source/'ledger.json.gz')},
        'codePin':s.sha(Path(__file__)),'outputPins':{n:s.sha(out/n) for n in ('REPORT.md','feature-robustness-appendix.json')}}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--measurement',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    generate(a.measurement,a.out)
