"""Preserve zero-eligibility diagnosis without changing the frozen research result."""
import argparse,json,os,re,subprocess
from pathlib import Path
from scripts import phase57_temporal_zero_diagnostic as d
s=d.s

def finalize(root,replay):
    root=Path(root);m=root/'diagnostic';replay=Path(replay)
    assert (m/'manifest.json').read_bytes()==(replay/'manifest.json').read_bytes()
    for name,h in s.read(m/'manifest.json').items():assert d.hashfile(m/name)==d.hashfile(replay/name)==h
    regression=s.read(root/'regression/regression.json');assert regression['status']=='PASS'
    focused=(root/'focused.log').read_text();assert re.search(r'\nOK\s*$',focused) and 'FAILED' not in focused
    f=s.read(m/'01_funnel.json');u=s.read(m/'02_usable9.json');w=s.read(m/'03_watch23.json');period=s.read(m/'04_period_reasons.json');cf=s.read(m/'05_counterfactual_support_only.json');cal=s.read(m/'06_calendar.json');boundary=s.read(m/'07_boundary.json')
    assert len(u)==9 and len(w)==23 and f['candidateSymbols']==2533
    assert not boundary['commonHoldoutIntersection'] and not boundary['excludedIntersection']
    frozen=d.verify_sources();assert frozen==boundary['sourceHashes']
    passing=sum(x['pairSupport'] for x in cf if (x['lane'],x['trait']) in {(a['lane'],a['trait']) for a in u})
    cause='TEMPORAL_RELIABILITY_BLOCKED_BY_MIXED_CAUSES'
    audit={'sameAsOfJoin':'PASS: old synchronized records share 2025-08-25 asOf; this is a historical reconstruction, not PIT proof','symbolJoinMiss':0,'identity':'Dated master code, not guaranteed permanent issuer identity; current cohort is descriptive, not a historical entry selection','computedThrough':'Source artifact through anchor close < descriptive prediction timestamp close+1min < test start; prior work snapshot guards unchanged','calibration':'fold1 target ends 2025-05-29, fold2 origin2025-05-22 is too early; actual fold1 mapping absent because fit-pair count0','sessionOrdering':'Asserted unique sorted session grid, no date compression. Original collector rejects duplicate minute timestamps/daily code duplicates','missing':'Excluded calendar slots remain NaN, rolling histories reset. That warm-up consumes permitted sessions. Null is not zero.','HMPropagation':'Original classification called directly per source snapshot. Current H/M is not propagated backward; correct but results in a different historical cohort','temporalEligibility':'Original snapshot reused on target: >=20 eligible sessions and >=100 peer symbols, then finite target posterior required, in addition to explicit target nEff/n>=8. This is an implementation/design contract ambiguity, not silently repaired','softwareBugDisposition':'No unambiguous specification-preserving repair applied. Hidden target constraints reproduced on synthetic19-day case. Resolve target8 vs snapshot20 and reference requirement under new precommit; old result retained.','reader':'No Reader remeasurement in this diagnosis; prior contract tests retained. Empty personality prevented simultaneous connection previously.'}
    s.write(root/'implementation-audit.json',audit)
    receipt={'status':'PASS','executionHead':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'runId':os.environ.get('GITHUB_RUN_ID'),'focusedTests':int(re.search(r'Ran (\d+) tests',focused)[1]),'regressionTests':sum(x['counts']['tests'] for x in regression['suites']),'deterministicRegeneration':'TWO_MANIFESTS_IDENTICAL','oldEvidenceUnchanged':True,'providerRequests':0,'protectedPayloadReads':0,'newResearchGate':False,'softwareRepairApplied':False,'cause':cause,'safety':boundary['safety']}
    s.write(root/'ci-receipt.json',receipt)
    nextspec={'status':'PROPOSAL_ONLY_NOT_ADOPTED','cause':cause,'entryExitAllowed':False,'mustResolve':['Before any remeasurement: validate all source/target calendar support and warm-up purely from availability; impossible folds must be caught at preflight, not counted as evidence against traits.','Specify target estimator explicitly: protocol minimum8 versus inherited20 eligible-session and100-peer-cohort requirements. Decide whether target posterior stability requires refit or frozen-source-prior posterior. This changes research specification, not a silent software fix.','Fix source rolling/expanding calendar semantics and ensure H/M coverage feasibility without lowering its threshold. No selecting dates based on the best reliability outcome.','Calibration mapping must be frozen after its fit-target completion and before each of at least2 independent validation origins; current fold1 mapping is not constructible.','State reliability artifact computedThrough/availableAt in per-cell output, independent from profile computedThrough; historical candidate cohort based on latest H/M is diagnostic only.','Prove three-fold feasibility with actual per-symbol nEff/episode and cross-sectional peer support; only then fix a new schedule and run separately.'],'additionalData':'No new acquisition authorized or performed. A later valid pair, if present, disproves blanket no-data conclusion but does not prove3-fold feasibility. Exact required additional sessions UNKNOWN until estimator/window contract resolved.','counterfactualUsablePairSupport':passing,'calendarLowerBound':cal}
    s.write(root/'next-validation-spec-proposal.json',nextspec)
    lines=['# Temporal Reliability Zero-Eligibility Diagnostic','',f'**最終判定 D: {cause}**','',
      '旧GateはBLOCKEDのまま。今回は原因診断であり、新たなPASS認定・window選択・Entry/EXIT設計は行わない。','',
      '## 1. Funnel（現在のUSABLE H/M候補コホート）','',
      '| stage | symbols | symbol×lane-traits | dropped cells | candidate symbols % |','|---|---:|---:|---:|---:|']
    for r in f['sequential']:lines.append(f"| {r['stage']} | {r['symbols']} | {r['symbolTraits']} | {r.get('droppedCells','—')} | {r['pctOfCandidateSymbols']:.2f} |")
    lines += ['',f"最初に0となる段階は **{f['firstZeroStage']}**。候補{f['candidateSymbols']}銘柄 / {f['candidateSymbolTraits']}セルは、最初のfoldのeligibilityで全て落ちる。PASS0、FAIL0、INSUFFICIENTは候補全セル。Period2単独とPeriod3も別集計した。",'','## 2. 根本原因','',
      '1. 第1fold（anchor2025-04-21）の60取引所calendar-position内に許可されたDevelopment日は5日しかない。source最低20日も、H/Mのcoverage>=0.5（60中30日）も数学的に不可能。history resetとscale warm-upで実有効日はさらに減る。',
      '2. 第2fold（anchor2025-05-22）は60中25日。仮に全日有効でも25/60<0.5なのでH/M不能。実Profileのpeer fitも成立しない。',
      '3. 第3foldは60中45許可日。実source confidence、target support、posterior条件のどれが落としたかを下表/CSVに記録した。数値を見て条件を緩めない。',
      '4. target明示条件nEff>=8/観測>=8のほか、共通snapshot()は適格session>=20・peer cohort>=100を要求し、有限target posteriorが比較条件に追加される。19有効日・110銘柄の合成例で「観測8を満たすがposteriorなし」を再現。研究仕様に曖昧さがあるため修正せず別specへの提案とした。','',
      '## 3. USABLE9の個別診断','',
      '| lane/trait | available sessions | observed symbols | H/M current | P1 eligible | P2 eligible | P3 eligible | all3 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in u:lines.append(f"| {r['lane']}/{r['trait']} | {r['availableSessions']} | {r['anyObservedSymbols']} | {r['currentHighMedium']} | "+' | '.join(str(x['eligibleSymbols']) for x in r['folds'])+f" | {r['comparableAllThree']} |")
    lines+=['','必要minimum・実min/max/p10/median/p90、最初/最後の日、source/target日数・nEff・coverage・peer人数、prediction origin/computedThroughはdiagnostic/02_usable9.json。銘柄別の正確なtimestampと理由はsymbol-trait-fold.csv.gz。','',
      '| lane/trait/fold | source base-mask | peer fit | source H/M | target explicit8 | target posterior finite | first drop reasons |','|---|---:|---|---:|---:|---:|---|']
    for r in period:
      if (r['lane'],r['trait']) not in {(a['lane'],a['trait']) for a in u}:continue
      hm=sum(r['sourceConfidence'].get(c,0) for c in ['HIGH','MEDIUM'])
      lines.append(f"| {r['lane']}/{r['trait']}/{r['fold']} | {r['sourceBaseMaskCount']} | {r['sourcePeerFit']} | {hm} | {r['targetExplicit8Count']} | {r['targetPosteriorFinite']} | {json.dumps(r['deepFirstFailureExclusive'],sort_keys=True)} |")
    lines += ['','first dropは排他的件数、全不成立conjunctは重複件数。混同しない。全32判定/全3foldの詳細は04_period_reasons.json。','',
      '## 4. WATCH23の時間順序','',
      '| lane/trait | actual mapping | nominal completion | validation2 origin | later authorized sessions | current design |','|---|---|---|---|---:|---|']
    for r in w:lines.append(f"| {r['lane']}/{r['trait']} | {r['actualMappingConstructed']} | {r['nominalCalibrationCompletion']} | {r['validationOrigins'][0]} | {r['remainingAuthorizedIndependentSessions']} | 不成立 |")
    lines += ['','5/29 closeにfold1 targetを知ってから5/22起点へmappingを遡及適用できない。さらにfold1のfit pairsが0で、mappingそのものが未作成。5/29後の日付順序が成立する最初の時点と残存独立session数は03_watch23.json。trait別に補正可能性を確認したことにはならない。旧WATCHは不変。','',
      '## 5. Counterfactual（件数のみ・新Gateなし）','',
      '| lane/trait | fixed latest origin | source H/M | comparison support |','|---|---|---:|---:|']
    for r in cf:
      if (r['lane'],r['trait']) in {(a['lane'],a['trait']) for a in u}:lines.append(f"| {r['lane']}/{r['trait']} | {r['anchor']} | {sum(r['sourceConfidence'].get(c,0) for c in ['HIGH','MEDIUM'])} | {r['pairSupport']} |")
    lines += ['',f'固定した末尾1期間のUSABLE比較support総セル数: {passing}。正式時間再現性PASSではなく、3fold成立や収益性も示さない。1条件ずつ除外するsupport診断も保存した。window探索・勝者選択なし。',
      f"連続許可分足日数の最長は{cal['longestConsecutiveIntradayAuthorizedRun']}。理想的な60+5+20×3設計のcalendar下限は125日だが、warm-up・nEff・event頻度・peer人数を保証しない。最小追加データ量は現時点UNKNOWN。まず既存データで成立可能な仕様を確定し、再測定前に凍結する。",'',
      '## 6. 実装監査と判定','',
      'DATA: 許可日間の穴・warm-up・条件付きevent不足がある。WINDOW: 60-position sourceと固定anchorsがcoverage不可能な期間を選んでいた。IMPLEMENTATION/ELIGIBILITY: target snapshot20/peer100/finite posteriorという追加条件が明示target8と重なる。よってMIXED。明白な仕様不変のsoftware repairは今回は実施していない。',
      'symbol joinの欠落は0、session順序・重複・欠測・因果時刻は監査。永久的security identityやPIT availabilityを新たに認定していない。implementation-audit.json参照。',
      '次工程はnext-validation-spec-proposal.jsonの論点を解消して新specを実測前に固定する工程。今回の診断からそのまま再測定やEntry/EXITへ進まない。','',
      '## 7. 境界・検証・停止','',
      f"Focused {receipt['focusedTests']} tests、既存回帰{receipt['regressionTests']} PASS。診断2回manifest一致、旧Evidence hash不変。rawは取得済み許可Developmentだけ復元、保護日との交差0、新規provider request0。過去Exposure LedgerのREPORT19派生閲覧事故は維持し、完全未閲覧と表現しない。",
      f"Execution HEAD {receipt['executionHead']} / PR587 Draft・未merge。Safety9項目は全false。CI run {receipt['runId']}。保存commitは実行HEADの子孫。",
      'STOP. Handoff Gate BLOCKED維持。NEW Selector/Entry/EXIT/Capital変更なし。','']
    (root/'REPORT-ja.md').write_text('\n'.join(lines))
    (root/'HANDOFF.md').write_text('# Final handoff\n\n'+cause+'\n\nSTOP. Read REPORT-ja.md and next-validation-spec-proposal.json. Old Gate BLOCKED unchanged. New validation spec must be separately fixed before remeasurement. No Entry/EXIT work.\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--replay',required=True);a=p.parse_args();finalize(a.evidence,a.replay)
