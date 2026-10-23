"""Close the finite diagnostic with explicit invalid-run and censoring status."""
from __future__ import annotations

import collections
import hashlib
import html
import json
from pathlib import Path

from scripts.phase57_profit_target_precommit import ROOT, OUT, ARM, TARGETS, canonical, digest, jst, check
from scripts.phase57_profit_target_diagnostic import read_gz


def load(name):return json.loads((OUT/name).read_text())


def write(name,obj):
    p=OUT/name
    check(not p.exists(),'FINAL_FILE_EXISTS:'+name)
    p.write_bytes(canonical(obj))


def md(name,text):
    p=OUT/name
    check(not p.exists(),'FINAL_FILE_EXISTS:'+name)
    p.write_text(text,encoding='utf-8')


def num(v,unit='',digits=0):
    return '不明' if v is None else (f'{v:,.{digits}f}{unit}' if isinstance(v,(int,float)) else str(v))


def svg(name,title,subtitle,body,legend=''):
    path=OUT/'figures'/name
    check(not path.exists(),'FIGURE_EXISTS:'+name)
    (OUT/'figures').mkdir(exist_ok=True)
    xml=f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="450" viewBox="0 0 900 450">
<rect width="900" height="450" fill="#fbfbf8"/>
<text x="36" y="38" font-family="sans-serif" font-size="22" font-weight="bold" fill="#16253b">{html.escape(title)}</text>
<text x="36" y="63" font-family="sans-serif" font-size="12" fill="#516072">{html.escape(subtitle)}</text>
{body}
<text x="36" y="431" font-family="sans-serif" font-size="11" fill="#516072">{html.escape(legend)}</text>
</svg>'''
    path.write_text(xml,encoding='utf-8')


def figures(results,reach,ci,hazard,avail,tail):
    xs=TARGETS
    colors={'IM':'#2563a9','R1':'#cc694b'}
    lines=[]
    for a in ARM:
        for typ,dy,stroke in [('high',0,colors[a]),('close',8,colors[a])]:
            vals=[(reach[f'{a}:{x}']['R50_FUNDED_ACTUAL']['lowerPct'] if typ=='high'
                  else 100*results[f'{a}:{x}']['R50_FUNDED_ACTUAL']['targetSpecific']
                             ['targetIntentN']/results[f'{a}:{x}']['R50_FUNDED_ACTUAL']
                             ['targetSpecific']['totalN']) for x in xs]
            pts=' '.join(f'{105+i*105},{350-v*2.6+dy:.1f}' for i,v in enumerate(vals))
            lines.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" stroke-width="{3 if typ=="high" else 2}" stroke-dasharray="{"" if typ=="high" else "6 4"}"/>')
            for i,v in enumerate(vals):
                lines.append(f'<circle cx="{105+i*105}" cy="{350-v*2.6+dy:.1f}" r="3" fill="{stroke}"/>')
    for i,x in enumerate(xs):lines.append(f'<text x="{95+i*105}" y="375" font-size="13">+{x}%</text>')
    for y in (0,25,50,75,100):
        yy=350-y*2.6
        lines.append(f'<line x1="80" x2="780" y1="{yy}" y2="{yy}" stroke="#e1e4e8"/>')
        lines.append(f'<text x="38" y="{yy+4}" font-size="12">{y}%</text>')
    svg('01_到達と判断.svg','旧fundedの到達下限とTarget判断','24 session / 観測Highは事後値、破線はclosed Target intent / IM 79、R1 32',
        ''.join(lines),'青 IM / 橙 R1；実線 観測High下限 / 破線 R50先行前のTarget判断。非到達欠測の上限は本文参照。')
    body=[]
    labels=['High確認','closed判断','intent','参照解決','paired既知']
    for j,a in enumerate(ARM):
        r=results[f'{a}:3']['R50_FUNDED_ACTUAL']['targetSpecific']
        h=reach[f'{a}:3']['R50_FUNDED_ACTUAL']['confirmedReachN']
        values=[h,r['targetIntentN'],r['targetIntentN'],r['targetResolvedN'],r['pairedKnownN']]
        for i,v in enumerate(values):
            xx=100+i*155; yy=140+j*125
            body.append(f'<rect x="{xx}" y="{yy}" width="{130*v/79:.1f}" height="34" fill="{colors[a]}"/>')
            body.append(f'<text x="{xx}" y="{yy-8}" font-size="12">{html.escape(labels[i])}: {v}</text>')
        body.append(f'<text x="35" y="{155+j*125}" font-size="16">{a}</text>')
    svg('02_参照ファネル.svg','+3% Targetの観測・参照ファネル','24 session / 旧funded、研究用closed→次OPEN参照、実注文fillの証明ではない',
        ''.join(body),'棒幅は共通79件スケール。paired既知はR50委譲を含む。')
    for typ in ('absolute','delta'):
        body=[]
        for j,a in enumerate(ARM):
            for i,x in enumerate(xs):
                v=results[f'{a}:{x}']['R50_FUNDED_ACTUAL']['targetSpecific']
                value=(v['candidatePnlJpySameMask'] if typ=='absolute' else v['deltaJpySameMask'])
                yy=110+j*130+i*14
                width=abs(value)/1200
                x0=440 if value>=0 else 440-width
                body.append(f'<rect x="{x0:.1f}" y="{yy}" width="{width:.1f}" height="9" fill="{colors[a]}"/>')
                body.append(f'<text x="70" y="{yy+9}" font-size="11">{a} +{x}% (N={v["pairedKnownN"]})</text>')
                body.append(f'<text x="{(x0+width+8 if value>=0 else x0-95):.1f}" y="{yy+9}" font-size="11">{round(value):,}円</text>')
        body.append('<line x1="440" x2="440" y1="95" y2="370" stroke="#222"/>')
        label='同一maskの候補絶対損益' if typ=='absolute' else 'R50との差（候補−R50）'
        svg('03_絶対損益.svg' if typ=='absolute' else '04_R50差.svg',label,
            '旧funded実quantity / xごとに既知maskが異なる / 24 session / 円、確定参照のみ',
            ''.join(body),'0円の縦線。差の95% session cluster CIは本文の表を参照。')
    body=[]
    for j,a in enumerate(ARM):
        t=tail[f'{a}:3']['R50_FUNDED_ACTUAL']['grossDelta']['entryId']
        for i,side in enumerate(('positive','negative')):
            share=t[side]['topSharesPct']['5'] or 0
            y=140+j*110+i*35
            body.append(f'<text x="70" y="{y+15}" font-size="13">{a} {"正" if side=="positive" else "負"} Top5</text>')
            body.append(f'<rect x="230" y="{y}" width="{share*5:.1f}" height="22" fill="{colors[a] if side=="positive" else "#7952a0"}"/>')
            body.append(f'<text x="{min(760,240+share*5):.1f}" y="{y+16}" font-size="12">{share:.1f}%</text>')
    svg('05_差のtail.svg','+3% R50差の正負tail寄与','24 session / 旧funded実quantity / 正負それぞれのgross絶対額を分母にしたTop5',
        ''.join(body),'net差を分母にしない。全session・symbolの対称LOOはTAIL_AND_LOO.json。')
    body=[]
    for j,a in enumerate(ARM):
        z=hazard[f'{a}:3']['categoryCounts'];y=145+j*125
        vals=[('CCMG先行',z.get('CCMG_INTENT_BEFORE_TARGET_OBSERVATION',0)),
              ('後にHigh≥5',z.get('BEFORE_LATER_OBSERVED_HIGH_GE5',0)),
              ('後にHigh≥10',z.get('BEFORE_LATER_OBSERVED_HIGH_GE10',0))]
        for i,(lab,v) in enumerate(vals):
            xx=95+i*245
            body.append(f'<text x="{xx}" y="{y-12}" font-size="12">{a} {lab}: {v}</text>')
            body.append(f'<rect x="{xx}" y="{y}" width="{v*2.5}" height="30" fill="{colors[a]}"/>')
    svg('06_CCMG先行.svg','Target前CCMGの早売りリスク','24 session / ALL_ENTRY_100 / +3% closed Targetとの時刻順、後のHighは評価専用',
        ''.join(body),'CCMG再走行・新hybrid Replay 0。後のHighをrouting入力にしない。')
    body=[]
    for j,a in enumerate(ARM):
        z=avail['countsByArm'][a]
        for i,(lab,key) in enumerate([('価格/経過','currentReturnPct'),('出来高','currentBarVolume'),
                                      ('VWAP距離','observedVWAPDistancePct'),('State','existingState'),
                                      ('6 Signal','signal.CONTINUATION')]):
            xx=95+i*155;y=150+j*125;v=z.get(key,0)
            body.append(f'<text x="{xx}" y="{y-9}" font-size="12">{a} {lab}: {v}</text>')
            body.append(f'<rect x="{xx}" y="{y}" width="{v*0.35:.1f}" height="30" fill="{colors[a]}"/>')
    svg('07_入力可用性.svg','+3%判断時点の入力可用性','24 session / closed TargetがR50先行前の行 IM 264、R1 241 / 値本体のみ数える',
        ''.join(body),'State/Signalの保存値joinは未証明。VWAPは観測80%以上で算定した値。')


def run():
    check(not (OUT/'CLOSURE.json').exists(),'ALREADY_FINALIZED')
    check(load('INDEPENDENT_AUDIT.json')['mismatchN']==0,'INDEPENDENT_AUDIT_FAIL')
    check(load('RUN_INVALID.json')['status']=='INVALID_RUN_POSTPROCESS_EXCEPTION',
          'FAILED_INVOCATION_NOT_RETAINED')
    check(load('CAUSALITY_TESTS_SUPPLEMENT.json')['status']=='SYNTHETIC_CAUSALITY_PASS',
          'CAUSALITY_NOT_TESTED')
    pre=load('MEASUREMENT_PRECOMMIT.json');s=load('FIXED_TARGET_RESULTS.json')
    reach=load('TARGET_REACH_SUMMARY_CORRECTED.json');ci=load('CLUSTER_CI_RESULTS.json')
    hazard=load('PRETARGET_CCMG_HAZARD.json');avail=load('STATE_SIGNAL_VOLUME_AVAILABILITY.json')
    tail=load('TAIL_AND_LOO.json');winner=load('LEGACY_WINNER_GATE_AUDIT.json')
    rows=read_gz(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz')
    high=read_gz(OUT/'TARGET_REACH_ROWS_CORRECTED.jsonl.gz')
    source_hash=load('SOURCE_MANIFEST.json')['pins']['rawPath']['sha256']
    # Same timestamp contest is an overlapping risk set. Publish the disjoint
    # nonfunded contender cut as well, without a new policy evaluation.
    risk={}
    for a in ARM:
        scope=[r for r in high if r['arm']==a and r['sameTimestampRiskset'] and not r['funded']]
        for x in TARGETS:
            n=len(scope);hit=sum(r[f'ge{x}']=='CONFIRMED_REACH' for r in scope)
            unknown=sum(r[f'ge{x}']=='UNKNOWN' for r in scope)
            risk[f'{a}:{x}']={'N':n,'confirmedReachN':hit,'unknownN':unknown,
                'lowerPct':100*hit/n if n else None,
                'upperPct':100*(hit+unknown)/n if n else None}
    write('RISKSET_NONFUNDED_COMPARISON.json',risk)
    prior=load('PRIOR_CYCLE_TRANSITION.json')
    write('EXPOSURE_LEDGER.json',{'priorExposure':['Phase A','Phase A+','Capital v3 and integrated R50'],
          'optionB':prior,'cycle':'PROFIT_TARGET_EXTENSION_V1_DIAGNOSTIC',
          'firstBatchInvocations':1,'firstBatchStatus':'INVALID_RUN_POSTPROCESS_EXCEPTION',
          'mainUniquePolicyArmsCalculated':14,'mainPolicyArmRecalculationsAfterFailure':0,
          'independentIdenticalPolicyArmsRecalculated':14,
          'totalUniqueFamilyArmEvaluationsWithAudit':28,
          'savedControlAccountingArmChecks':2,'costRepricesNotNewPolicyArms':3,
          'newFits':0,'ccmgHybridReplays':0,'extensionReplays':0,
          'integratedCapitalReplays':0,'newProviderRequests':0,
          'protectedOpens':0,'externalLlmRequests':0,'orders':0})
    write('BUDGET_LEDGER_FINAL.json',{'mainMax':14,'mainUsed':14,'mainRemaining':0,
          'independentMax':14,'independentUsed':14,'independentRemaining':0,
          'savedControlChecksMax':2,'savedControlChecksUsed':2,
          'fits':0,'newProviderRequests':0,'protectedOpens':0,
          'mainInvocations':1,'initialMainInvalid':True,
          'subsequentPostprocessingNoPolicyArmReevaluation':True})
    write('UNRESOLVED_DECISIONS.json',{'selectedDevelopment':None,
          'productionReady':False,'fixedTargetSelection':None,
          'blockers':['初回batch後処理の失敗はINVALID_RUNとして保持',
             'fixed Targetのfirst exact OPEN欠測とR1終端auction欠測',
             '非到達側の完全path欠測、observed Highの上限が広い',
             'target時点の既存State/6 Signal保存値または許可済みprevious-session prefix未join',
             '出来高/売買代金の単位とlive knownAt、VWAP分母の運用適合未証明',
             'Capital v3保存scoreの旧prediction byte不一致とstage2 nested lineage',
             '延長gate/continuation出口/閾値/許容リスク未固定',
             '旧Winner Gateの変更数値承認なし'],
          'nextResearchApprovalNeeded':True})
    write('MISSING_EVIDENCE_REQUEST.json',{'status':'DEPENDENCY_SPECIFIC',
          'requestedNotAcquired':['同じ24 session/Entry IDにjoinするState/Signal値本体、producer version/hash、barEnd/knownAt、previous-session許可済みprefix',
              'target判断時刻のvolume/value単位とsource venue/adjustment、零/欠測、VWAP input provenance',
              '欠損したexact next OPENの既存原本の有無とsession/Entry ID別の欠測理由',
              'R1 2025-08-04|36700|602の15:30 auction原本又は正式な未解決証跡',
              'Capital v3 score prediction bytes のlocal/CI差とnormalizer train lineage'],
          'newProviderRequestsThisCycle':0,'protectedOpeningsThisCycle':0,
          'futureUse':'new finite authorization before another policy or integrated Replay'})
    md('EXTENSION_DESIGN_DRAFT.md','''# 🚀 Exceptional Extension 設計草案

Status: `PROPOSED_NOT_AUTHORIZED`。本cycleで延長policy実データ評価 0。

最初の有効な +3% closed Target 判断時刻で、旧R50判断が先行・pendingでなければ一度だけ gate を問う。FALSE/UNKNOWN は同じ固定Target売却へ進む。TRUE なら最小の continuation comparator は `DEFER_TO_FROZEN_R50` とし、同じ日のR50 ceiling と正確な終端を守る。Target後にもう一度gateを問わず、部分利確や再購入はしない。

延長の採否は `Net_R50Continuation − Net_TargetSale` の同一Entry/quantity・両枝既知集合で検討する。R50がTarget時点より前に判断する行は比較対象外。今回のState/6 Signal値はtarget時点joinできず、量・VWAP入力も部分的である。TRUE条件、構造崩れEXIT、floor/giveback、queue/retry、support/Gate/Replay予算は未固定のまま。最終Highを売却価格にしない。

CCMG pretarget は初期familyでOFF。追加するなら固定Targetとcontinuationを同条件にしたOFF/ON ablationを別の有限実験にする。未来Winner bandで当時のroutingを選ばない。
''')
    write('NEXT_FINITE_EXPERIMENT_DRAFT.json',{'status':'PROPOSED_NOT_AUTHORIZED',
          'priority':'verify missing as-of State/Signal and exact OPEN coverage; freeze a new finite confirmation',
          'focalTargetPct':3,'observedTargets':TARGETS,'newTargetSelection':None,
          'comparator':['fixed target','all R50 delegation','one-time conditional extension'],
          'ccmgAblation':['OFF','ON only under separately frozen identical policy'],
          'continuation':'DEFER_TO_FROZEN_R50 initially',
          'gateRule':None,'fitBudget':None,'replayBudget':None,
          'stage2NestedLineageRequired':True,'sessionForwardAndPurgeRequired':True,
          'protectedEvaluationAuthorized':False,'capitalReplayAuthorized':False,
          'productionAuthorized':False})
    md('INTEGRATED_REPLAY_SPEC_DRAFT.md','''# 🏦 将来のCapital統合 Replay 仕様草案

Status: `PROPOSED_NOT_AUTHORIZED`。今回の新統合Replayは0。

旧funded集合固定のEXIT帰属比較からPortfolio final equityを作らない。次回は全凍結Entry streamを一度だけ時刻順に流し、確定約定時刻でcash/slotを解放する。未解決EXITはcash/slotを維持し、以前rejectされた同一Entryを復活させない。新しい別の凍結Entry eventだけをその時刻で判断する。

Capital v3-B saved score、R37 1/3 equity sizing、100株、¥1,000,000、MAX3同時保有を固定。候補同時刻の順位・EXIT fill→cash→mark→Entry→sizeの順序を維持。R1の旧未解決終端は0円扱いせず旧full equity=nullを保持し、新policyで回避した場合に理由を示す。全24 sessionのEOD連続・end-flat、未解決、mark、絶対/相対PnL、intraday/EOD MaxDD、turnoverを認証する。個人口座保有と研究ledgerは混ぜない。
''')
    figures(s,reach,ci,hazard,avail,tail)
    report=report_text(s,reach,ci,hazard,avail,tail,winner,risk,pre)
    md('REPORT-ja.md',report)
    closure={'cycle':'PROFIT_TARGET_EXTENSION_V1_DIAGNOSTIC','savedJst':jst(),
       'basisHead':pre['basisHead'],'sourceIntegrityStatus':'PASS_PINNED_SOURCES',
       'capitalContractStatus':'PASS_SAVED_SCORE_AND_FUNDED_IDENTITY_WITH_PREDICTION_BYTE_CAVEAT',
       'targetPathMeasurabilityStatus':'PARTIAL_CENSORED; corrected auction endpoint',
       'fixedTargetDiagnosticStatus':'INVALID_RUN_POSTPROCESS_EXCEPTION; saved 14-arm rows independently matched; no clean first-batch completion',
       'pretargetCcmgHazardStatus':'DESCRIPTIVE_RISK_FOUND_CCMG_OPTIONAL_UNPROVEN',
       'stateSignalVolumeStatus':'PARTIAL_VOLUME_B; STATE_SIGNAL_C_SOURCE',
       'extensionDesignStatus':'DRAFT_ONLY_NO_POLICY_REPLAY',
       'independentAuditStatus':'PASS_SAVED_ROWS_INDEPENDENT_RECALCULATION_WITH_SHARED_SOURCE_PROJECTION',
       'operatorScopeComplianceStatus':'PASS_ZERO_FITS_PROVIDER_PROTECTED_LLM_ORDERS_MERGES',
       'selectedDevelopment':None,'productionReady':False,
       'automaticPromotionAllowed':False,'mainPolicyArmEvaluations':14,
       'independentIdenticalPolicyArmRecalculations':14,
       'newIntegratedCapitalReplays':0,'mainInvalidReceipt':'RUN_INVALID.json',
       'next':'NEXT_EXPERIMENT_DRAFT_READY_NOT_AUTHORIZED; no target selected'}
    write('CLOSURE.json',closure)
    handoff=f'''# 🔒 Profit Target + Exceptional Extension 引き継ぎ

保存JST: {closure['savedJst']}。開始basis HEAD `{pre['basisHead']}`。Draft PR #587、研究branchのみ。

14 main policy-arm行は計算・保存されたが、初回batchは後処理 NameError で `INVALID_RUN_POSTPROCESS_EXCEPTION`。保存行からの後処理を追加し、別コードで14 arm / 11,298行を照合して不一致0。失敗記録と暫定High表を消さず、auctionを含むHigh訂正表を追加。mainや本番へは採用しない。

旧funded +3%同一既知mask: IM 75/79、候補−R50 +¥127,600、候補絶対 −¥13,537。R1 30/32、差 −¥73,200、候補絶対 +¥67,379。欠測と広いCI、資金配分固定比較を伴う記述値。High到達はIM44/79、R1 18/32で旧報告と一致。Target時点State/Signalの値joinは未証明。旧案Bは `DEPRIORITIZED_BY_OPERATOR / NOT_EXPERIMENTALLY_REJECTED`。旧 `DESIGN_ONLY_EXPERIMENT_BLOCKED`を保持。

次は `MISSING_EVIDENCE_REQUEST.json` と `NEXT_FINITE_EXPERIMENT_DRAFT.json`。precommit/保存行を再実行しない。main予算0、独立照合予算0。新しい確認・延長・統合には別の有限仕様と承認が必要。結果commit後の保存receiptに本commitを記す。
'''
    md('CONTROLLING_HANDOFF.md',handoff)
    requirement_matrix()
    manifest={'schema':'profit-target-extension-result-manifest-v1',
      'basisHead':pre['basisHead'],'createdJst':jst(),'precommitSha256':
      digest(OUT/'MEASUREMENT_PRECOMMIT.json'), 'policyRowsSha256':
      digest(OUT/'FIXED_TARGET_OUTCOME_ROWS.jsonl.gz'),
      'filesSha256':{str(p.relative_to(OUT)):digest(p) for p in sorted(OUT.rglob('*'))
                     if p.is_file() and p.name not in ('MANIFEST.json','SAVED_RESULT_RECEIPT.json')},
      'receiptOutsideManifest':True,'initialRunInvalid':True,
      'safety':dict.fromkeys(('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
        'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed',
        'automaticPromotionAllowed','productionUpdateAllowed','transmitted'),False)}
    write('MANIFEST.json',manifest)
    print(json.dumps({'status':'CLOSURE_SAVED_LOCALLY','cycle':str(OUT),
          'files':len(manifest['filesSha256']),'savedJst':closure['savedJst']}))


def requirement_matrix():
    groups={
      '開始/切替':['START_AUDIT.json','PRIOR_CYCLE_TRANSITION.json','SOURCE_MANIFEST.json','EXPOSURE_LEDGER.json'],
      '固定':['MEASUREMENT_PRECOMMIT.json','POLICY_SPEC.json','BUDGET_LEDGER.json','BOOTSTRAP_SPEC.json','TARGET_FEATURE_REGISTRY.json'],
      'Capital':['CAPITAL_CONTRACT_AUDIT.json','FUNDING_UNIVERSE_ROWS.jsonl.gz','CAPITAL_ENRICHMENT_CORRECTED.json'],
      '到達':['TARGET_REACH_ROWS_CORRECTED.jsonl.gz','TARGET_REACH_SUMMARY_CORRECTED.json','TARGET_EVENT_CENSUS.json','EXECUTION_COVERAGE.json'],
      '固定利確':['FIXED_TARGET_OUTCOME_ROWS.jsonl.gz','FIXED_TARGET_RESULTS.json','ABSOLUTE_AND_DELTA_METRICS.json','LEGACY_WINNER_GATE_AUDIT.json'],
      '頑健性':['TAIL_AND_LOO.json','CLUSTER_CI_RESULTS.json','COST_REPRICE_RESULTS.json','SESSION_DRAWS.npz'],
      '前段防御':['PRETARGET_CCMG_HAZARD_ROWS.jsonl.gz','PRETARGET_CCMG_HAZARD.json'],
      '特徴':['STATE_SIGNAL_VOLUME_AVAILABILITY.json','TARGET_ASOF_FEATURE_ROWS.jsonl.gz','CAUSALITY_TESTS_SUPPLEMENT.json','FOCAL_TARGET_ASSOCIATION.json'],
      '延長/将来':['EXTENSION_DESIGN_DRAFT.md','NEXT_FINITE_EXPERIMENT_DRAFT.json','INTEGRATED_REPLAY_SPEC_DRAFT.md','UNRESOLVED_DECISIONS.json'],
      '終了':['INDEPENDENT_AUDIT.json','MISSING_EVIDENCE_REQUEST.json','CLOSURE.json','CONTROLLING_HANDOFF.md','REPORT-ja.md']}
    h=load('SOURCE_MANIFEST.json')['pins']['rawPath']['sha256']
    items=[]
    for stage,names in groups.items():
        for name in names:
            check((OUT/name).is_file(),'MATRIX_FILE_MISSING:'+name)
            status=('PARTIAL_C_SOURCE' if name in ('STATE_SIGNAL_VOLUME_AVAILABILITY.json',
                           'TARGET_ASOF_FEATURE_ROWS.jsonl.gz','FOCAL_TARGET_ASSOCIATION.json')
                    else 'INVALID_MAIN_RUN_INDEPENDENT_SAVED_ROW_PASS'
                      if name in ('FIXED_TARGET_OUTCOME_ROWS.jsonl.gz','FIXED_TARGET_RESULTS.json',
                                  'ABSOLUTE_AND_DELTA_METRICS.json') else 'COMPLETE_WITH_LIMITS')
            items.append({'requirement':stage,'path':str((OUT/name).relative_to(ROOT)),
                          'status':status,'sourceSha256':h,
                          'N':11298 if name=='FIXED_TARGET_OUTCOME_ROWS.jsonl.gz' else None,
                          'blocker':('State/Signal target as-of values missing' if status=='PARTIAL_C_SOURCE'
                                     else 'initial main postprocess exception' if status.startswith('INVALID')
                                     else None)})
    for name,status in [('REQUIREMENTS_MATRIX.json','GENERATED_THIS_STEP'),
                        ('MANIFEST.json','GENERATED_AFTER_MATRIX'),
                        ('SAVED_RESULT_RECEIPT.json','PENDING_RESULT_COMMIT')]:
        items.append({'requirement':'終了/保存後','path':str((OUT/name).relative_to(ROOT)),
                      'status':status,'sourceSha256':h,'N':None,
                      'blocker':'result commit SHA does not exist yet' if name.startswith('SAVED') else None})
    write('REQUIREMENTS_MATRIX.json',{'schema':'profit-target-extension-requirements-v1',
          'items':items,'savedReceipt':'PENDING_RESULT_COMMIT_OUTSIDE_MANIFEST',
          'legacyHighProvisionalRetained':True})


def report_text(s,reach,ci,hazard,avail,tail,winner,risk,pre):
    lines=['# 🎯 Ark Terminal Phase57 — Profit Target + Exceptional Extension',
      '',f'保存JST：{jst()}。対象：2025-07-22〜2025-08-25 / 24 session / 許可済みDevelopment。basis HEAD `{pre["basisHead"]}`。',
      '', '> **結論**：固定Targetは採用しない。初回batchは後処理例外でINVALID_RUN。保存済みpolicy行11,298件は別コードで全件一致したが、正式な成功runや独立市場validationではない。State/Signalのtarget時点値も未証明。',
      '', '## 🔒 範囲と実施量', '',
      '|項目|今回|', '|---|---:|',
      '|母集団|IM 819 / R1 795（代替Entry世界）|',
      '|旧R50 funded|IM 79 / R1 32|',
      '|固定family|7 target × 2 arm = 14 main arm、別コード14照合|',
      '|新fit / CCMG hybrid / 延長policy / Capital統合Replay|0 / 0 / 0 / 0|',
      '|provider / protected / 外部LLM / 発注 / main merge|各0|',
      '|実行状態|初回INVALID_RUN、保存行の後処理回復、独立照合11,298行不一致0|',
      '', '旧案Bは研究の優先度を変更した。`DESIGN_ONLY_EXPERIMENT_BLOCKED`を保持し、`DEPRIORITIZED_BY_OPERATOR / NOT_EXPERIMENTALLY_REJECTED`。Phase A/A+を再走行していない。',
      '', '## 💰 CapitalとHigh到達', '',
      'Capital v3-Bは、train foldで保存されたRidge score（訓練targetはpost-Entry観測上昇を0〜20%にclip）で同時刻候補を順位付けし、R37の1/3 equity目標、現金、100株単位、MAX3同時保有に従った。saved score bytesは固定、旧CI/local予測bytes差は残る。PRR score5/10とは別系列。資金解放と未解決cash lockはfunded集合を変える。',
      '', '|arm / 集合|N|+3% High確認|到達下限|到達上限|完全path|', '|---|---:|---:|---:|---:|---:|']
    for a in ARM:
        for scope,label in [('R50_FUNDED_ACTUAL','旧funded'),('R50_NOT_FUNDED_100','nonfunded'),
                            ('SAME_TIMESTAMP_ELIGIBLE_RISKSET','同時刻riskset')]:
            z=reach[f'{a}:3'][scope]
            lines.append(f'|{a} {label}|{z["totalN"]}|{z["confirmedReachN"]}|{z["lowerPct"]:.1f}%|{z["upperPct"]:.1f}%|{z["completePathN"]}|')
        z=risk[f'{a}:3']
        lines.append(f'|{a} 同時刻riskset内nonfunded|{z["N"]}|{z["confirmedReachN"]}|{z["lowerPct"]:.1f}%|{z["upperPct"]:.1f}%|—|')
    lines+=['', 'HighはEntry OPEN足を含む同日連続足と、存在する15:30 auctionの観測値。非到達を証明するには全予定足とauctionが必要。旧strictly-later表を原本と照合し不一致0。+3%旧funded確認はIM 44/79、R1 18/32で既存報告と一致するが、Highは約定価格ではない。risksetはfundedを含む重複集合であり、上表に非funded内数も示す。',
      '', '![到達とTarget判断](figures/01_到達と判断.svg)',
      '', '## ⏱️ Target判断から参照まで', '',
      '|arm / x|High確認|R50先行前のTarget intent|正確な次OPENあり|Target参照欠測|paired既知 / funded|',
      '|---|---:|---:|---:|---:|---:|']
    for a in ARM:
        for x in TARGETS:
            z=s[f'{a}:{x}']['R50_FUNDED_ACTUAL']['targetSpecific'];h=reach[f'{a}:{x}']['R50_FUNDED_ACTUAL']
            lines.append(f'|{a} +{x}%|{h["confirmedReachN"]}|{z["targetIntentN"]}|{z["targetResolvedN"]}|{z["targetFirstReferenceUnresolvedN"]}|{z["pairedKnownN"]}/{z["totalN"]}|')
    lines+=['', 'closed 1mの判断後、正確な次の予定OPENを研究用参照にした。Highだけの閾値超過はTarget intentにならない。参照欠測ではR50や次に見えたOPENで埋めない。15:30 auctionはHigh解剖の終端観測とR50保存約定参照であり、足中Highの指値fill証明ではない。',
      '', '![参照ファネル](figures/02_参照ファネル.svg)',
      '', '## 📊 固定利確の同一mask比較（旧funded実quantity）', '',
      '|arm / x|paired/全件|候補絶対PnL|R50同mask PnL|差 JPY|平均Net%|平均差pp|差の95% cluster CI JPY|全x共通mask N|',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for a in ARM:
        for x in TARGETS:
            k=f'{a}:{x}';z=s[k]['R50_FUNDED_ACTUAL']['targetSpecific']
            c=ci[k]['R50_FUNDED_ACTUAL']['targetSpecific']['deltaTotalJpyCI95']
            cm=s[k]['R50_FUNDED_ACTUAL']['allTargetCommonMask']['pairedKnownN']
            lines.append(f'|{a} +{x}%|{z["pairedKnownN"]}/{z["totalN"]}|{num(z["candidatePnlJpySameMask"],"円")}|{num(z["r50PnlJpySameMask"],"円")}|{num(z["deltaJpySameMask"],"円")}|{num(z["candidateMeanNetPct"],"%",2)}|{num(z["deltaMeanNetPp"],"pp",2)}|{num(c[0],"円") if c else "不明"}〜{num(c[1],"円") if c else "不明"}|{cm}|')
    lines+=['', '同一target内でもunknownは比較から除外し、件数を併記。絶対JPY合計とEntry平均Net%はquantity・原価が違うため符号が一致するとは限らない。全x共通maskは欠測を隠さない補助表としてJSONに保持。session bootstrapは10,000回、24 cluster、seed 20260929。14比較から良いtargetを選ばない。',
      '', '![候補絶対損益](figures/03_絶対損益.svg)', '',
      '![R50差](figures/04_R50差.svg)',
      '', '## ⚖️ 未前倒し損失・Winner・tail', '',
      '|arm +3%|target前倒し既知|前倒し差|R50委譲既知の絶対損失合計|旧≥5 Winner帯の差|正のTop5寄与|負のTop5寄与|',
      '|---|---:|---:|---:|---:|---:|---:|']
    for a in ARM:
        z=s[f'{a}:3']['R50_FUNDED_ACTUAL']['targetSpecific']
        w=winner[f'{a}:3']['>=5']
        t=tail[f'{a}:3']['R50_FUNDED_ACTUAL']['grossDelta']['entryId']
        lines.append(f'|{a}|{z["changedKnownN"]}|{num(z["targetEarlierDeltaJpy"],"円")}|{num(z["nonAdvancedLossTotalJpy"],"円")}|{num(w["deltaJpy"],"円")} / N={w["sameMaskN"]}|{num(t["positive"]["topSharesPct"]["5"],"%",1)}|{num(t["negative"]["topSharesPct"]["5"],"%",1)}|')
    lines+=['', '旧Winner Gateの5–10/≥10/≥5のJPY・平均Net%非劣化結果は `LEGACY_WINNER_GATE_AUDIT.json` に元基準のまま保存。全session・全symbolの対称LOO、候補絶対損失tailと差のtailは `TAIL_AND_LOO.json`。費用総率0.05/0.10/0.20ppの再価格では同一quantityの差は恒等的に不変であり、約定頑健性は証明しない。',
      '', '![差のtail](figures/05_差のtail.svg)',
      '', '## 🛡️ Target前CCMGと時点入力', '',
      '|arm +3% ALL_ENTRY_100|CCMGがclosed Targetより先|その後High≥5|その後High≥10|順序/path不明|',
      '|---|---:|---:|---:|---:|']
    for a in ARM:
        z=hazard[f'{a}:3']['categoryCounts']
        lines.append(f'|{a}|{z.get("CCMG_INTENT_BEFORE_TARGET_OBSERVATION",0)}|{z.get("BEFORE_LATER_OBSERVED_HIGH_GE5",0)}|{z.get("BEFORE_LATER_OBSERVED_HIGH_GE10",0)}|{z.get("ORDER_OR_PATH_UNKNOWN",0)}|')
    lines+=['', 'その後のWinnerは事後評価だけに使用。CCMGは今回再走行せず、旧結果の先行intentを比較した。Target前に後の上昇を切り得るため `CCMG_OPTIONAL_UNPROVEN` を維持。最初のmilestone前はBASELINEで、一般的な損切り能力を保証しない。',
      '', '![CCMG先行](figures/06_CCMG先行.svg)',
      '', '|arm +3% focal|R50前closed Target|価格/経過|bar出来高・売買代金|VWAP距離|既存State値|既存6 Signal値|',
      '|---|---:|---:|---:|---:|---:|---:|']
    for a in ARM:
        z=avail['countsByArm'][a];n=z['currentReturnPct']
        lines.append(f'|{a}|{n}|{n}|{z["currentBarVolume"]}|{z["observedVWAPDistancePct"]}|0|0|')
    lines+=['', 'State/Signalの過去利用とtarget時点値の存在は別。既存producerの名前だけで実際のsnapshotが使えたとは言わない。bar volume/valueは累積値とみなさず0・欠測を分けた。VWAPは当時までのvalue/volumeで観測率80%以上の場合のみ算定。売買代金の単位、previous-session入力、実配信knownAtは未証明。',
      '', '![入力可用性](figures/07_入力可用性.svg)',
      '', '## 🚦 判定と次工程', '',
      '|Gate|状態|', '|---|---|',
      '|source / Capital|hash・R50/資金配分IDと保存score契約PASS。予測byte差は未解決|',
      '|High / execution|観測到達は照合、完全pathは少数。exact OPEN欠測はUNKNOWN|',
      '|固定Target|初回 `INVALID_RUN`、保存行の独立照合PASS。選定なし|',
      '|State / Signal / Volume|State/Signal target値BLOCKED_SOURCE、volume/VWAP部分的|',
      '|Extension / Capital統合|設計草案のみ、実データpolicy/Portfolio Replay 0|',
      '|Production|false、発注0、main merge0|',
      '', '1. **Capitalは何を優先したか。** saved v3-B OOF scoreで同時刻候補を順位付けし、R37のcash/lot/slot制約で配分した。旧fundedのHigh≥3はIM44/79、R1 18/32で旧報告と整合。将来選別性能の証明ではない。',
      '2. **Highと売却参照の差は。** +3% HighはIM44、R1 18。R50先行前のclosed Target intentはIM43、R1 16、正確な次OPEN既知はIM39、R1 15。Highそのものでは売らない。',
      '3. **利益はどう見えるか。** 上の7 target全件表の通り。+3%旧funded同maskの差はIM +¥127,600、R1 −¥73,200だが、候補絶対はIM −¥13,537、R1 +¥67,379。未前倒し損失、Winner早売り、unknown、CI、試行露出を含めると採用できない。',
      '4. **CCMGとState/Volumeは。** CCMGが先に出て後に+10% Highを観測した行はIM24、R1 17。State/6 Signalのtarget時点値は0件証明、出来高bar値は一部因果的に読めるが単位・運用knownAtは未証明。',
      '5. **次は。** まずState/Signal値と正確なOPEN・auction欠測の原本を回収し、新しい有限確認仕様を固定する。単純Targetの結果だけから延長を否定せず、今回のbudgetを再使用しない。Capital統合と本番化は別Gate。',
      '', '実行条件：新provider0、保護partition0、外部LLM0、注文0。旧North Star ¥1,000,000→約¥2,000,000/24 sessionは目標であり、この固定funded帰属比較からPortfolio達成率は算出しない。']
    return '\n'.join(lines)+'\n'


if __name__=='__main__':run()
