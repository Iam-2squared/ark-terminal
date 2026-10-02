"""Report immutable measured results and final gate, never refit or change scope."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone,timedelta
import json,csv,hashlib
R=Path(__file__).resolve().parent;P=R/'PARENT_V4'
def read(n):return json.loads((R/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def num(x,d=4):return 'NA（未評価）' if x is None else f'{x:.{d}f}'
def pct(x):return 'NA（未評価）' if x is None else f'{100*x:.2f}%'
def save(n,x):(R/n).write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def main():
 gate=read('FRESH_GATE_MEASUREMENTS_V5.json');audit=read('INDEPENDENT_AUDIT_V5.json');manifest=read('FRESH_DATA_MANIFEST_V5.json');scope=read('FRESH_DATA_SCOPE_V5.json');forensic=read('V4_CONTROL_FORENSICS_RECEIPT.json');mfreeze=read('V5_CALIBRATION_METHOD_FREEZE.json');budget0=read('BUDGET_START_V5.json');fits=list(map(json.loads,(R/'MODEL_EXECUTION_LEDGER_V5.jsonl').open()));acq=[];http=steps=0
 for mode in ['RECOVERY','EXTENSION']:
  if (R/mode).exists():
   x=read(mode+'/RUNNER_FINAL_RECEIPT.json');http+=x['actual_provider_HTTP'];steps+=x['new_steps'];acq.append({'mode':mode,'receipt':x,'SHA256':sha(R/mode/'RUNNER_FINAL_RECEIPT.json')})
 usage=read('GITHUB_REQUEST_USAGE_V5.json');caps=budget0['finite_caps'];delta={'research_fits':sum(r['lane']=='research' for r in fits),'fresh_fits':sum(r['lane']=='fresh' for r in fits),'total_fits':len(fits),'new_provider_HTTP':http,'frozen_current_slot_steps':steps,'fixed_retry_proposals':109,'bounded_acquisition_passes':1,'Actions_runs':len(acq),'fanout':1,'global_fresh_bootstrap_vectors':read('BOOTSTRAP_GLOBAL_1000_RECEIPT_V5.json')['generated_vector_N'],'bootstrap_generations':read('BOOTSTRAP_GLOBAL_1000_RECEIPT_V5.json')['generation_invocation_N'],'GitHub_GET':usage['GET_invocations'],'GitHub_writes':usage['write_invocations']};compliant=all(delta[k]<=v for k,v in caps.items());direct=audit['status']=='PASS' and audit['mismatch_N']==0 and compliant and forensic['audit_status']=='PASS'
 if not direct:status='BLOCKED_V5_DIRECT_INTEGRITY'
 elif gate['R2_TRUE_NULL']=='FAIL':status='BLOCKED_V5_R2_CONTROL'
 elif not gate['sample_PASS']:status='STATE_R2_CONFIRMATION_LIMITED_SAMPLE'
 elif not (gate['dangerous_hard_PASS'] and gate['major_reversal_PASS'] and gate['concentration_PASS']):status='STATE_R2_MEASURED_NO_PROMOTABLE_SIGNAL'
 elif not gate['calibration_PASS']:status='STATE_R2_HARD_SIGNAL_CONFIRMED_CALIBRATION_NOT_READY'
 else:status='STATE_R2_REVERSAL_INTELLIGENCE_CONFIRMED_FOR_HYBRID_ENTRY_RESEARCH'
 advance=status=='STATE_R2_REVERSAL_INTELLIGENCE_CONFIRMED_FOR_HYBRID_ENTRY_RESEARCH';recovery=read('RECOVERY/RUNNER_FINAL_RECEIPT.json');r1=gate['R1_calibrated'];r2=gate['R2_calibrated'];raw=gate['R2_uncalibrated'];imp=gate['dangerous_improvement'];jst=datetime.now(timezone(timedelta(hours=9))).isoformat()
 save('BUDGET_FINAL_V5.json',{'JST':jst,'finite_caps_unchanged':caps,'delta_at_final_report':delta,'finite_budget_compliant':compliant,'provider_guard_remaining':900-http,'cumulative_known_provider_HTTP':1852+http,'cumulative_known_frozen_steps':112209+steps,'cumulative_known_bootstrap_vectors':6000+delta['global_fresh_bootstrap_vectors'],'independent_new_fits_draws':[0,0],'bounded_acquisition_passes_unit':'original109 one bounded retry, conditional disjoint24 inventory extension not a repeated109 pass','disjoint_extension_passes':int((R/'EXTENSION').exists()),'inherited_budget_complete':budget0['inherited_V4_budget'],'inherited_V1_3000_cap1000_breach_retained':True,'inherited_V2_four_fit_ledger_gap_retained':True,'old16FAIL_retained':16,'old88workflow_incident_retained':88,'GitHub_delivery_tail_usage_receipt':'GITHUB_REQUEST_USAGE_AT_DELIVERY_V5.json; invocation counts do not invent connector-internal HTTP fanout'})
 rawsources=[]
 for item in acq:
  for x in read(item['mode']+'/SOURCE_RECEIPTS.json'):
   if x['endpoint'].endswith('/minute') and x.get('row_N',0)>0:rawsources.append({'lane':item['mode'],'date':x['scope']['date'],'code':x['scope'].get('code'),'row_N':x['row_N'],'raw_response_SHA256':x['raw_response_SHA256']})
 save('EXPOSURE_APPEND_ONLY_DELTA_V5.json',{'JST':jst,'parent_delta_file':'PARENT_V4/EXPOSURE_APPEND_ONLY_DELTA.json','parent_delta_SHA256':sha(P/'EXPOSURE_APPEND_ONLY_DELTA.json'),'prior_exposure_unknown_nonzero_and_failures_retained':True,'V4_exposed_research_only':True,'V4_status_unchanged':'BLOCKED_V4_INTEGRITY','new_Development_raw_reads':rawsources,'new_Development_labels':[{'date':p['date'],'security_id':p['security_id'],'session_id':p['session_id'],'pair_id':p['pair_id']} for p in manifest['pairs']],'raw_returned_but_unlabelled_is_not_future_fresh':True,'fresh_pool_dates':scope['acquired_fresh_dates'],'fresh_scope_fixed_before_labels':True,'Holdout':0,'Protected':0,'Fresh_validation_reserve':0,'OOS':0,'Prospective':0,'Entry':0,'EXIT':0,'profit':0,'Capital':0,'Portfolio':0,'orders':0,'broker_write':0,'external_AI':0,'main_merge':0,'force_push':0,'State9_changes':0,'Path_changes':0,'profile_changes':0,'M0_changes':0,'target_changes':0,'family_mapping_changes':0})
 final={'JST':jst,'status':status,'direct_integrity':'PASS' if direct else 'FAIL','independent_audit':audit['status'],'mismatch_N':audit['mismatch_N'],'R2_candidate_local_control':gate['R2_TRUE_NULL'],'sample_PASS':gate['sample_PASS'],'hard_signal_PASS':gate['dangerous_hard_PASS'] and gate['major_reversal_PASS'],'calibration_PASS':gate['calibration_PASS'],'concentration_PASS':gate['concentration_PASS'],'Hybrid_Entry_research_authorized':advance,'promoted_representation':'R2 Full State9 frozen tuple' if advance else None,'V4_status_unchanged':'BLOCKED_V4_INTEGRITY','forensic_classification':forensic['classification'],'new_fits':len(fits),'fresh_fits':delta['fresh_fits'],'new_bootstrap_vectors':delta['global_fresh_bootstrap_vectors'],'precommit_SHA256':sha(R/'PREDICTIVENESS_V5_PRECOMMIT.json'),'contract_SHA256':sha(R/'PREDICTIVENESS_V5_CONTRACT.md'),'scope_SHA256':sha(R/'FRESH_DATA_SCOPE_V5.json'),'OOF_SHA256':sha(R/'R1_R2_FRESH_OOF_V5.jsonl'),'GitHub_final_receipt':'CHECKPOINTS/C7_POST_GET.json'};save('FINAL_RECEIPT_V5.json',final)
 summary={'JST':jst,'original109_acquired':recovery['acquired_pairs'],'original109_fresh_export':recovery['fresh_export_pairs'],'original109_remaining_unavailable':109-recovery['acquired_pairs'],'original109_status_counts':dict(Counter(x['status'] for x in read('RECOVERY/FRESH_REACQUISITION_LEDGER.json'))),'additional_scope_dates':24 if (R/'EXTENSION').exists() else 0,'acquisition_receipts':acq,'fresh_dates':manifest['fresh_date_N'],'fresh_securities':manifest['fresh_security_N'],'fresh_pairs':manifest['fresh_pair_N'],'post_label_scope_expansion':0};save('FRESH_RECOVERY_SUMMARY_V5.json',summary)
 answers=[
 ('V4 R3 failure分類',forensic['classification']+'。較正前の僅かな全体優位が、同じT0.5によるREALスコアのより大きいLL悪化で逆転。Path分布／alpha差は副次候補、因果断定しない。'),
 ('direct future leakage','保存prefix・timestamp・partition・coefficients・whole-label provenance監査で未検出。全State/Path kernelの再auditやhistorical known_atの全面証明ではない。'),
 ('calibration前にもR3 failureがあったか','全体では無い。raw REAL1.080486 < NULL1.097922。ただしfold3ではrawからREALがNULLより悪い。calibrated全体REAL1.493967 > NULL1.313498。'),
 ('R3をcandidateから外すか','はい。V5 primaryから外しdiagnostic-only。救済fit／feature tuning0。R4もdescriptive／nonpromotable。'),
 ('fresh Development確保',f"{manifest['fresh_date_N']}日／{manifest['fresh_security_N']}security／{manifest['fresh_pair_N']}security-session。追加scopeはmetadata上24日で固定、未取得日もsplit calendarに保持。"),
 ('V4 unavailable109件の回収',f"{recovery['acquired_pairs']}件、fresh eligible export{recovery['fresh_export_pairs']}件。原順序の1回pass、差し替え0。U58／raw24／HTTP400 provider27のまま。"),
 ('fresh OOF日数',str(gate['OOF_dates'])),('fresh evaluable fold数',str(gate['evaluable_folds'])),('DOWN support',str(gate['DOWN_support'])),('UP support',str(gate['UP_support'])),
 ('R1 dangerous FP',f"{r1['dangerous_numerator']}/{r1['dangerous_denominator']} = {pct(r1['dangerous_rate'])}"),
 ('R2 dangerous FP',f"{r2['dangerous_numerator']}/{r2['dangerous_denominator']} = {pct(r2['dangerous_rate'])}"),
 ('R1→R2改善pp・95%CI',f"{num(imp['improvement_pp'])} pp、95%CI [{num(imp['improvement_CI_low_pp'])}, {num(imp['improvement_CI_high_pp'])}] pp。日cluster1000 exactly once。単日subset CIはinformative扱いしない。" if gate['OOF_dates'] else 'NA。evaluable fresh test dates0のためbootstrap未起動、draw0。'),
 ('R2 DOWN Precision／Recall／F1',' / '.join(pct(r2.get('DOWN_REVERSAL_'+k)) for k in ['Precision','Recall','F1'])),
 ('R2 UP Precision／Recall／F1',' / '.join(pct(r2.get('UP_CONTINUE_'+k)) for k in ['Precision','Recall','F1'])),
 ('未較正LL／Brier／ECE',f"row LL {num(raw.get('row_LL'),6)}、date-equal LL {num(raw.get('date_equal_LL'),6)}、row Brier {num(raw.get('Brier'),6)}、ECE {num(raw.get('ECE'),6)}"),
 ('較正LL／Brier／ECE',f"row LL {num(r2.get('row_LL'),6)}、date-equal LL {num(r2.get('date_equal_LL'),6)}、row Brier {num(r2.get('Brier'),6)}、ECE {num(r2.get('ECE'),6)}"),
 ('新calibrationはouterで悪化したか',('date LL '+num(r2['date_equal_LL']/raw['date_equal_LL']-1,6)+'、row Brier '+num(r2['Brier']/raw['Brier']-1,6)+' の相対変化。5%非致命的悪化gate '+('PASS' if gate['calibration_PASS'] else 'FAIL')+'。ECEも保存。Tはouterの結果で選び直さない。') if r2['N'] else 'fresh outer未評価。exposed researchではdate LL+6.43%、row Brier+5.90%、ECE悪化。そのまま保存し方法を追加探索しない。'),
 ('R2 TRUE_NULL PASSか',gate['R2_TRUE_NULL']+'。candidate-local calibrated LLと事前固定90% positive-gain equivalence。rawも保存。R3の過去failureによる自動BLOCKなし。'),
 ('concentration PASSか',('PASS' if gate['concentration_PASS'] else 'FAIL／未確認')+'。gross dangerous-error reduction／class correctness gain各々の最大1日・1security share<=0.5。詳細CSV、fold／current Stateも保存。'),
 ('independent mismatch0か',f"{audit['mismatch_N']}、audit {audit['status']}。別logic、候補helper import0、fit0、新bootstrap0。"),
 ('State9／Path／target／family changes','各0。profile／M0も0。V4原本status／Contract／Precommit／scope／OOFのhashを保持。'),
 ('Holdout／Protected／Entry／EXIT／profit exposure','V5 delta各0。Fresh-validation reserve／OOS／Prospective／orders／broker write／Capital／Portfolio／externalAIも0。過去unknown/nonzero exposure履歴は消さない。'),
 ('Hybrid Entryへ進めるか','はい、次WorkのHybrid Entry研究のみ。自動Entry／EXIT／注文ではない。' if advance else 'いいえ。今回のfinal gateを満たしていない。V4やexposed researchをfresh確認として救済利用しない。'),
 ('渡すState representation','R2 Full State9の固定tupleとR2 calibrated probability／class/rank Evidence。R3/R4はcandidateとして渡さない。' if advance else 'promotion representationなし。Bならclass/rank Evidenceのみ保持し、probabilityを信頼できる確率として渡さない。C/D/F/Eなら確認済みcandidateと呼ばない。')]
 table='\n'.join(f'| {i} | {q} | {answer} |' for i,(q,answer) in enumerate(answers,1))
 overview=f"fresh Core {gate['fresh_OOF_anchors']} anchors／{gate['OOF_dates']} OOF日／{gate['evaluable_folds']}fold、DOWN {gate['DOWN_support']}／UP {gate['UP_support']}。R1 {pct(r1['dangerous_rate'])} → R2 {pct(r2['dangerous_rate'])}。改善 {num(imp['improvement_pp'])} pp。"
 limitation=('V5の全条件がPASS。State研究を固定し、次はHybrid Entry Intelligenceで因果feature familyを1つずつ追加する。' if advance else 'この結果からEntry／EXITのルール、threshold、利益・取引成績を推論しない。測定不足／失敗を保持し、結果を見たscope追加や再fitは行わない。')
 text=f'''# Ark Terminal — State Predictiveness V5

Final status: `{status}`。JST {jst}。

{overview}

direct integrity {'PASS' if direct else 'FAIL'}／independent {audit['status']}（mismatch {audit['mismatch_N']}）／R2 control {gate['R2_TRUE_NULL']}。{limitation}

## V4を救済しない

V4は `BLOCKED_V4_INTEGRITY / FAIL_CONTROL` のまま。R2のV4改善18.53%→15.38%（+3.15pp、95%CI+1.19〜+6.32pp）は過去exposedの観測であり、このWorkのfresh確認ではない。R3分類は `{forensic['classification']}`。V4原本2784 manifest entriesと4指定hashを照合し、原本上書き0。

## Calibration researchとfresh確認を分ける

exposed-only research36fits、実装独立PASS/mismatch0。ROLLING_INNER_OOF_TEMPERATURE_V1のみ。R2 raw date LL0.765198→cal0.814415（+6.43%）、row Brier0.474282→0.502249（+5.90%）、ECE0.099226→0.181768。悪化を保持し追加family／結果後変更0。これはpromotion Evidenceではない。alpha1/T1.5がexposedの両foldで選ばれた事実はfreshの固定alpha/Tではなく、fresh outer train内で同じ有限methodを対称に適用する。

## Mandatory25 answers

| # | 問い | 結果 |
| ---: | --- | --- |
{table}

## Gateと不確実性

sample {'PASS' if gate['sample_PASS'] else 'FAIL'}、dangerous hard signal {'PASS' if gate['dangerous_hard_PASS'] else 'FAIL'}、major reversal {'PASS' if gate['major_reversal_PASS'] else 'FAIL'}、calibration {'PASS' if gate['calibration_PASS'] else 'FAIL'}、concentration {'PASS' if gate['concentration_PASS'] else 'FAIL'}。固定priorityに従う。statistical control failureはdirect leakageと同義ではない。9State secondaryは今回任意未実施、V4/V3の保存表はParentに保持。Path anatomyもdescriptive既存Evidenceのみで新規rule化0。

historical known_atはUNKNOWNを維持し、bar-endでcausal availabilityが成立するという仮定を別記する。このresearchは実運用／約定／profit検証ではない。DOWNを見逃すRecallと、UP予測がDOWNだったdangerous rateは別指標。hard classificationとprobability qualityも分ける。

## Recoveryとfinite budget

109件回収0、U58／RAW24／provider HTTP400 27。追加24日はmetadataで事前固定、最大72security-session、原SHA順first3 factor-compatible。成功入力だけをfreshへ入れ、失敗security/dateの差し替え0。scope／split／precommitをfresh labelsより前に固定。新provider {http}/900 HTTP、kernel {steps}/40000 slots、research {delta['research_fits']}/80 fits、fresh {delta['fresh_fits']}/160 fits、total {delta['total_fits']}/240、Actions {len(acq)}/2、bootstrap {delta['global_fresh_bootstrap_vectors']}/1000 once。独立新fit/draw0。V1の3000/cap1000 breach、V2 ledger gap、old16FAIL／88workflow incidentを継承しresetしない。

GitHub専用branch state-predictiveness-v5-r2-confirmation-20261002-v1。C0〜C7のpost-commit GETはCHECKPOINTSを参照。main merge0／force push0。最終HEAD・code location index・delivery hashは各receiptを参照。

## 後でEXIT研究へ再利用可能なEvidence

UP_CONTEXT continuationとDOWN reversalのevent-order target、PULLBACK／RISE_STOP／DROP_STOP／RANGEを区別する固定State family、保存済みPath anatomy length1〜4、gap/reset/segment・causal timestamp・support/concentrationの証跡。これはEXIT/HOLD判断やprofitルールではなく、将来の別事前固定研究へのdescriptive入力候補のみ。

## Delivery

2〜3個の通常ZIPを同じdirectoryへ展開。完全なCSV／JSON／OOF／fits／labels／features／trace／raw hash receipts／Parent V4／元V3 ZIPを保持。再取得／再fit／label再生成／bootstrap再生成は禁止。DELIVERY_MANIFEST.json／SPLIT_PACKAGE_MANIFEST_V5.jsonで全memberのhashとZIP配置を照合できる。Git-backed sourceはSOURCE_CODE_LOCATION_INDEX_V5.jsonのexact commit/path/SHAを使用。
'''
 (R/'REPORT-ja.md').write_text(text)
 next_action='HYBRID ENTRY INTELLIGENCE: frozen R2 baseline, causal feature families one at a time; no trading execution.' if advance else 'New independently authorized, genuinely unexposed Development scope is required for any further confirmation; no extra acquisition or reinterpretation in this completed V5.' if not gate['sample_PASS'] else 'Preserve this failed gate; use a separately precommitted work if any further research is requested. Do not reopen fresh validation or retune State/Path.'
 (R/'NEXT_STAGE_HANDOFF.md').write_text(f"# V5 handoff\n\nStatus: {status}\n\n{overview}\n\nNext: {next_action}\n\nV4 remains BLOCKED_V4_INTEGRITY forever. R3 diagnostic-only; R4 nonpromotable. No automatic Entry/EXIT/orders. Read Contract/Precommit/scope/identity/selection/raw and calibrated OOF/controls/concentration/independent audit/budget/exposure/report/manifests/checkpoint receipts first. All V5 returned raw and generated labels are now exposed Development and cannot be called future fresh. No successful refit or bootstrap regeneration. Keep historical breaches/unknown exposure.\n")
 (R/'00_README.txt').write_text(f"Ark Terminal — State Predictiveness V5 COMPLETE\nStatus: {status}\n{overview}\nV4 unchanged BLOCKED_V4_INTEGRITY. R3 forensic {forensic['classification']}; direct audit {audit['status']}, mismatch{audit['mismatch_N']}.\nRead REPORT-ja.md / REPORT-ja.html / FINAL_RECEIPT_V5.json / NEXT_STAGE_HANDOFF.md.\nDelivery2–3 ordinary ZIPs: extract all into one directory; no .z01 / spanning archive. Use DELIVERY_MANIFEST and SPLIT_PACKAGE_MANIFEST_V5.\nAll machine-readable evidence and immutable Parent V4/V3 included. No rerun, no exposed-as-fresh rescue, no trading decisions. Git-backed code is hash-pinned by SOURCE_CODE_LOCATION_INDEX_V5.json.\n")
 print(json.dumps({'status':status,'direct_integrity':direct,'sample':gate['sample_PASS'],'calibration':gate['calibration_PASS'],'Hybrid_Entry':advance,'new_provider_HTTP':http,'model_fits':len(fits),'mandatory_answers':len(answers)}))
if __name__=='__main__':main()
