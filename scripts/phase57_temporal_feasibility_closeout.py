"""Close availability-only feasibility; preserve formal Gate and old Evidence."""
import argparse,json,os,re,subprocess
from pathlib import Path
from scripts import phase57_temporal_feasibility as f
s=f.s;d=f.d

def run(root,replay):
 root=Path(root);result=root/'measurement';replay=Path(replay)
 manifest=s.read(result/'manifest.json');assert manifest==s.read(replay/'manifest.json')
 for name,h in manifest.items():assert d.hashfile(result/name)==d.hashfile(replay/name)==h
 assert d.verify_sources()==s.read(result/'06_boundary.json')['sourceHashes']
 reg=s.read(root/'regression/regression.json');assert reg['status']=='PASS'
 log=(root/'focused.log').read_text();assert re.search(r'\nOK\s*$',log) and 'FAILED' not in log
 verdict=s.read(result/'03_verdict.json');rows=s.read(result/'02_trait_support.json');schedule=s.read(result/'01_calendar_schedule.json')
 usable=[r for r in rows if r['globalStatus']=='USABLE'];watch=[r for r in rows if r['globalStatus']=='WATCH']
 assert len(usable)==9 and len(watch)==23
 receipt={'status':'PASS','executionHead':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'runId':os.environ.get('GITHUB_RUN_ID'),'focusedTests':int(re.search(r'Ran (\d+) tests',log)[1]),'regressionTests':sum(x['counts']['tests'] for x in reg['suites']),'deterministicRegeneration':'TWO_MANIFESTS_IDENTICAL','oldEvidenceUnchanged':True,'formalGate':'BLOCKED_UNCHANGED','temporalReliabilityScored':False,'entryExitTraining':False,'sourceMatrixArtifactId':10597435745,'sourceMatrixRun':35484934096,'safety':s.read(f.BASE/'protocol.json')['safety']}
 s.write(root/'ci-receipt.json',receipt)
 lines=['# 144日Development Temporal Reliability Feasibility','', '**成立性診断のみ。旧GateはBLOCKED維持。時間再現性のPASS/FAIL、補正成績、収益性は測っていない。**','',
 f"比較可能な旧USABLE cohort: **{verdict['usableThreePeriodComparableSymbols']}銘柄**。そのうち最新H/M候補にも含まれる銘柄: **{verdict['currentHMUsableThreePeriodComparableSymbols']}銘柄**。",
 f"この比較可能cohortを成立させる最小追加Development日数: **{verdict['minimumAdditionalDevelopmentDaysForDemonstratedComparableCohort']}**。全銘柄・全traitの成立やGate通過を保証しない。",'',
 '## 分割（実数値を見る前に日付だけで固定）','',
 '|役割|source開始|computedThrough日|prediction origin日|評価開始|評価終了|許可日数|calendar上の適格日上限|','|---|---|---|---|---|---|---:|---:|']
 for r in schedule['rows']:lines.append(f"|{r['name']}|{r['trainStart']}|{r['computedThrough'][:10]}|{r['predictionOrigin'][:10]}|{r['testStart']}|{r['testEnd']}|{r['targetAllowedSessions']}|{r['targetPotentialEligible']}|")
 lines+=['','144日全体（2024-09-19〜2025-08-25）を利用可能範囲とし、必要な日足履歴は既存許可済みDevelopmentのみ。144日が連続日であるとは扱わず、sealed日・欠測はNaN、履歴resetとwarm-upを維持。source60取引所日、H/M coverage>=0.5、target20適格日、peer100など旧条件を保持。',
 '最初のcalibration targetは空白を含み108取引所日にまたがる。検証targetは非重複だがiidや相場局面の独立を保証しない。後のsourceはその時点までに観測した前のtargetの一部を含み得る。calibration mappingは最初のtarget終了後に固定する設計であり、今回はfitしていない。',
 'カレンダー規則は全144日の許可日メタデータのみを使用。成績の最大化、window再選択、Gate緩和、最低N緩和は実施していない。旧固定windowの正式結果は書き換えない。','',
 '## 旧USABLE 9件の比較成立数','',
 '|lane/trait|Calibration|Validation1|Validation2|全3期間共通|うち最新H/M|','|---|---:|---:|---:|---:|---:|']
 for r in usable:lines.append('|'+r['lane']+'/'+r['trait']+'|'+'|'.join(str(a['comparablePairs']) for a in r['periods'])+f"|{r['threePeriodComparableSymbols']}|{r['currentHMThreePeriodComparableSymbols']}|")
 lines+=['','symbol×trait別の証拠はmeasurement/04_comparable_cells.json.gz。各期間のminimum・nEff・peer人数・除外理由は02_trait_support.json。最新H/M cohortは説明用で、過去の適格銘柄選定には使わない。','',
 '## WATCH23','',
 '|lane/trait|Calibration fit pair候補|Validation1 pair候補|Validation2 pair候補|各期間100以上|','|---|---:|---:|---:|---|']
 for r in watch:lines.append('|'+r['lane']+'/'+r['trait']+'|'+'|'.join(str(a['mappingPairs']) for a in r['periods'])+f"|{r['calibrationPairSupportAtLeast100AllPeriods']}|")
 lines+=['','時間順序とpair数のみ。実mapping作成・補正の安定性評価・WATCH昇格は行っていない。','',
 '## 判定と次工程','',verdict['decision'],
 '0より多い比較可能cohortがあれば、現在のDevelopmentで事前固定した再測定へ進む根拠になる。ただし本工程は正式再測定ではない。measurement/05_validation_spec_proposal.jsonを別工程で採用・固定してから採点する。',
 '比較cohortが0なら本規則での成立は未証明。別windowを成績で選ばない。全設計に対する不可能性や追加日数は断定しない。','',
 '## Entry / EXITへの144日再利用契約','',
 '同じ144日は将来のEntry/EXIT Developmentとして再利用可。各decisionのDictionary・peer prior・normalization・confidence・temporal reliability artifactは全てcomputedThrough < decisionTimeかつavailableAt <= decisionTimeを満たすpast-only再生成が必要。最終snapshotや最終H/M判定の過去行へのコピーは禁止。未成立・未利用可能はUNAVAILABLEのままとする。',
 '今回の全期間診断や最終registry/Gate判断は事後の研究結果であり、過去に利用できたartifactとは認定しない。Development再利用は独立な評価ではない。学習・比較を行うfoldごとに学習済みartifactとtrait選択も過去側だけで固定する。採点対象より後のデータ・labelで作った辞書を特徴として使わない。',
 '詳細はprecommitのentry-exit-past-only-contract.md。今回はEntry/EXIT学習・設計へ進まない。','',
 '## 検証・境界','',
 f"Focused {receipt['focusedTests']} PASS / regression {receipt['regressionTests']} PASS / 2回再生成manifest一致。旧Evidence hash不変。",
 '原本再取得なし。既存144日の検証済みmatrix checkpointを使用し、元input ledgerと完全一致。Common Holdout244・REPORT19/Validation/OOS/Fresh追加開封0。過去Exposure Ledger維持。安全フラグ9項目は全false。',
 f"Execution HEAD {receipt['executionHead']} / CI {receipt['runId']} / PR587 Draft・未merge。STOP。",'']
 (root/'REPORT-ja.md').write_text('\n'.join(lines))
 (root/'HANDOFF.md').write_text('# Handoff\n\n'+verdict['decision']+'\n\nRead REPORT-ja.md and measurement/05_validation_spec_proposal.json. Gate BLOCKED; no remeasurement or Entry/EXIT yet.\n')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--replay',required=True);a=p.parse_args();run(a.evidence,a.replay)
