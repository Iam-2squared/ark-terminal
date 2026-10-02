"""Evidence/report only. Does not fit, draw, fetch, generate kernels or change precommit."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv,hashlib,datetime,sys
R=Path(__file__).resolve().parent;V=R.parent/'state_predictiveness_20261002_v1'
def load(n):return json.loads((R/n).read_text())
def save(n,v):(R/n).write_text(json.dumps(v,sort_keys=True,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return list(csv.DictReader((R/n).open()))
def csvout(n,rows):
 with (R/n).open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def pct(v):return 'NA' if v in ['',None] else f'{float(v)*100:.2f}%'
def num(v):return 'NA' if v in ['',None] else f'{float(v):.6g}'
def table(headers,rows):return '\n'+'| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,r))+' |' for r in rows)+'\n'
def main():
 pre=load('PREDICTIVENESS_V2_PRECOMMIT.json')
 for n,h in pre['hashes'].items():assert sha(R/n)==h
 audit=load('INDEPENDENT_AUDIT_V2.json');supp=load('INDEPENDENT_SUPPLEMENT_V2.json');assert audit['status']==supp['status']=='PASS'
 gate=load('GATE_ASSESSMENT_V2.json');status=gate['provisional_status_pending_independent_audit'];manifest=load('DATASET_MANIFEST.json');pairs=manifest['pairs'];ag=read('MODEL_METRICS_AGGREGATE.csv');states=read('PER_STATE_PRECISION_RECALL_F1.csv');folds=read('MODEL_METRICS_BY_FOLD.csv');motion=read('MOTION_FAMILY_METRICS.csv');context=read('TREND_CONTEXT_FAMILY_METRICS.csv');controls=read('NEGATIVE_CONTROL_V2.csv');price=read('PRICE_SECONDARY_V2.csv');promotion=read('STATE_PROMOTION_ASSESSMENT.csv');path=read('PATH_INCREMENTAL_ASSESSMENT_V2.csv');ts=load('TARGET_SCHEMA_V2.json');classes=ts['class_order'];now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat();start=load('BUDGET_START_V2.json');runner=load('NEW_DEVELOPMENT/RUNNER_FINAL_RECEIPT.json');proposal=load('NEW_DEVELOPMENT/ACQUISITION_UNIVERSE_PRECOMMIT.json')['proposals'];skips=load('NEW_DEVELOPMENT/SKIPS.json');source=load('NEW_DEVELOPMENT/SOURCE_RECEIPTS.json')
 get=lambda task,model:next(x for x in ag if (x['task'],x['control'],x['model'])==(task,'REAL',model))
 core=get('NEXT_DISTINCT_PRIMARY','B3');secondary=get('NEXT_OBSERVED_PRIMARY','B3');binary=get('TRANSITION_WITHIN30','B3')
 ledger=list(map(json.loads,(R/'MODEL_EXECUTION_LEDGER.jsonl').read_text().splitlines()));arts=[json.loads(p.read_text()) for p in (R/'FITTED').glob('*.json')];required=sum(1+len(x['validation_grid']) for x in arts);assert required==load('FIT_INDEX_V2.json')['fit_operations']==load('C4_OOF_FIXATION_RECEIPT.json')['fit_operations']==210
 assert all(x['fit_N']==i+1 for i,x in enumerate(ledger)) and len(ledger)<=210
 save('FIT_LEDGER_COMPLETENESS_FINDING.json',{'status':'NONBLOCKING_LEDGER_PROVENANCE_GAP' if len(ledger)!=required else 'PASS','append_ledger_rows':len(ledger),'receipt_fit_counter':210,'independently_recounted_artifacts':len(arts),'independently_recounted_inner_fits':sum(len(x['validation_grid']) for x in arts),'required_total_fits_from_saved_artifacts':required,'charged_fit_operations':210,'unrecorded_append_rows':required-len(ledger),'cause':'UNKNOWN; original append ledger retained unchanged; no fabricated repair rows','budget_cap':648,'budget_breach':False,'numerical_audit_mismatch':0})
 assert load('BOOTSTRAP_GLOBAL_1000_RECEIPT.json')['bootstrap_total_generated_draws']==1000
 for p in (R/'NEW_DEVELOPMENT').rglob('MANIFEST.json'):
  for x in json.loads(p.read_text())['files']:assert sha(p.parent/x['path'])==x['SHA256']
 complete={(p['date'],p['code']) for p in pairs if p['exposure']=='V2_NEW_DEV_EVAL'};skip={(x['date'],x['code']):x['reason'] for x in skips};failed_ordinal=runner['provider_requests']//2;coverage=[]
 for i,p in enumerate(proposal,1):
  key=(p['date'],p['code']);st='COMPLETE' if key in complete else 'INPUT_INELIGIBLE' if key in skip else 'U_UNAVAILABLE_EXPORT_ABORT' if i==failed_ordinal else 'NOT_ATTEMPTED_AFTER_EXPORT_ABORT';coverage.append({'proposal_ordinal':i,'date':p['date'],'security_id':p['security_id'],'session_id':p['session_id'],'status':st,'reason':skip.get(key,runner['error']['code'] if i==failed_ordinal else ''),'scope_fixed_before_raw':True,'reselection':0})
 csvout('DEVELOPMENT_ACQUISITION_COMPLETENESS.csv',coverage);cc=Counter(r['status'] for r in coverage);assert cc['COMPLETE']==35 and sum(cc.values())==72
 newpairs=[p for p in pairs if p['exposure']=='V2_NEW_DEV_EVAL'];observed=sum(p['observed_semantic_N'] for p in newpairs);newnull=sum(p['formal_null_N'] for p in newpairs);allobserved=observed+2138
 oldf=load('V1_FOLD0TARGET_FORENSIC.json')['reason_counts'];fr=defaultdict(Counter)
 for x in oldf:fr[x['horizon']][x['reason']]+=x['N']
 budget={'JST':now,'V1_consumption':start['V1_consumption'],'V1_budget_SHA256':start['V1_budget_SHA256'],'V1_budget_breach_preserved':True,'V2_caps_unchanged':start['V2_caps'],'delta':{'Actions_runs':2,'Actions_failed_runs_retained':2,'Actions_fanout':1,'provider_HTTP_requests':251,'first_requests':173,'second_requests':78,'new_fixed_proposals':72,'completed_new_pairs':35,'new_frozen_kernel_steps':11445,'old_frozen_endpoint_reuse_N':8050,'State9_Path_semantic_suite_reruns':0,'new_feature_snapshots_N':11445,'old_pair_reruns':0,'fit_operations':210,'fit_family_counts_reconstructed':{'B0':21,'B1':21,'ridge':168},'fit_append_ledger_rows':len(ledger),'fit_ledger_finding':'FIT_LEDGER_COMPLETENESS_FINDING.json','walk_forward_fitter_launches':1,'label_builder_launches':1,'bootstrap_generated_draw_vectors':1000,'independent_new_bootstrap_draws':0,'independent_kernel_reruns':0,'independent_model_refits':0,'independent_checker_launches':1,'independent_supplement_launches':1,'independent_assertions':audit['assertion_N']+supp['assertion_N'],'independent_mismatches':0,'synthetic_target_probes':10,'synthetic_target_assertions':20,'render_launches':1,'unique_charts':11,'future_classifier_input':0,'protected_requests':0,'raw_provider_pages_exported':0,'secret_values_exported':0,'main_merge':0,'force_push':0,'external_AI':0,'broker_orders':0},'V2_finite_budget_compliant':True,'all_historical_budgets_compliant':False,'old_RC1_FAIL_N':16,'old_workflow_incident_N':88,'prior_outside_exposure_unknown_nonzero_preserved':True,'cumulative_known_market_kernel_steps':start['V1_consumption']['cumulative_known_market_kernel_steps_including_new_feature_generation']+11445,'cumulative_known_bootstrap_vectors_V1_V2':4000,'cumulative_known_provider_requests':419,'provider_prior_known_requests':168,'no_reset':True,'GitHub_usage':'GITHUB_REQUEST_USAGE_AT_DELIVERY.json; final actual connector counts, not planned calls'}
 save('BUDGET_FINAL_V2.json',budget)
 exposure={'JST':now,'append_only':True,'V1_EXPOSED_DEV_preserved':'V1_EXPOSED_DEV.json','V1_BLOCK_preserved':True,'old44_and_667_state_identity_exclusions_preserved':True,'legacy_strategy_outcome_exposure_separate':True,'new_metadata_only_proposals_N':72,'new_raw_attempted_proposals_N':failed_ordinal,'new_completed_feature_security_sessions':[{'security_id':p['security_id'],'session_id':p['session_id'],'date':p['date'],'pair_id':p['pair_id']} for p in newpairs],'V2_NEW_DEV_future_label_exposure_dates':sorted({p['date'] for p in newpairs}),'V2_NEW_DEV_not_Fresh_or_OOS':True,'old_feature_endpoint_reuse':8050,'new_future_label_generation_endpoint_universe':11445,'future_label_USE_authorized_Development_only':True,'future_classifier_input':0,'Common_Holdout':0,'Protected':0,'Fresh_OOS':0,'Prospective':0,'Entry':0,'EXIT':0,'profit':0,'Capital_Portfolio':0,'external_AI':0,'raw_temporary_purged':True,'old_outside_exposure':'UNKNOWN_NONZERO_INHERITED, never reset to zero'}
 save('EXPOSURE_APPEND_ONLY_DELTA.json',exposure)
 locations=[]
 for p in pairs:locations.append({'pair_id':p['pair_id'],'exposure':p['exposure'],'security_id':p['security_id'],'session_id':p['session_id'],'features_member':('REUSED_DEVELOPMENT' if p['exposure']=='V1_EXPOSED_DEV' else 'NEW_DEVELOPMENT')+'/FEATURES/'+p['pair_id']+'.jsonl','feature_SHA256':p['feature_SHA256'],'trace_member':('REUSED_DEVELOPMENT' if p['exposure']=='V1_EXPOSED_DEV' else 'NEW_DEVELOPMENT')+'/STATE9_TRACES/'+p['pair_id']+'.jsonl','trace_SHA256':p['state_trace_SHA256'],'labels_member':'LABELS/'+p['pair_id']+'.jsonl'})
 csvout('INPUT_LOCATION_INDEX_V2.csv',locations)
 finalgate={**gate,'independent_audit_pending':False,'final_status':status,'integrity':'PASS','independent_main_assertion_N':audit['assertion_N'],'independent_supplement_assertion_N':supp['assertion_N'],'independent_mismatch_N':0,'acquisition_incomplete':True,'empty_planned_third_fold_retained':True,'Path_incremental_promoted_states':[x['State'] for x in path if x['task']=='NEXT_DISTINCT_PRIMARY' and x['Path_incremental_evidence']=='True'],'State9_Path_profile_M0_changes':0,'Entry_handoff_eligible':False,'Holdout_ready':False};save('GATE_FINAL_V2.json',finalgate)
 receipt={'JST':now,'document_id':'WORK_STATE_PREDICTIVENESS_V2_NEXTSTATE_MAX_THROUGHPUT_20261002_V1','status':status,'integrity':'PASS','Contract_SHA256':sha(R/'PREDICTIVENESS_V2_CONTRACT.md'),'scope_SHA256':sha(R/'DATA_SCOPE_V2.json'),'V1_HEAD':'7e3ce89cb2928d46f66d4606e1010ba3a3a1896f','V1_status':'BLOCKED_LEAKAGE_OR_SEMANTIC_INTEGRITY','V2_branch':'state-predictiveness-v2-nextstate-20261002-v1','final_HEAD_receipt':'CHECKPOINTS/C6_POST_COMMIT_RECEIPT.json','core':core,'secondary':secondary,'binary':binary,'independent_assertion_N':audit['assertion_N']+supp['assertion_N'],'mismatch_N':0,'promoted_states':[],'Path_incremental_states':[],'V2_bootstrap_vectors':1000,'independent_new_draws':0,'acquisition_completed_pairs':35,'acquisition_incomplete':True,'OOF_date_N':13,'evaluable_folds':2,'planned_folds':3,'post_result_contract_scope_target_feature_split_metric_changes':0,'protected_Holdout_Entry_EXIT_profit':[0,0,0,0,0],'next_action':'No automatic Entry or Holdout. Decide a new Development/precommitted acquisition-and-calibration experiment (V3) from saved evidence.'};save('FINAL_RECEIPT.json',receipt)
 intro=f'''# Ark Terminal — State Predictiveness V2 最終報告

作成JST：{now}  
文書ID：WORK_STATE_PREDICTIVENESS_V2_NEXTSTATE_MAX_THROUGHPUT_20261002_V1

## 🏁 結論

**{status}**（B：測定完了・昇格可能Stateなし）。独立照合PASS、核心不一致0。次の異なるStateのB3正解率は{pct(core['accuracy'])}、RISE予測のPrecisionは60.00%。ただしB2/B3の確率log lossはB1より悪く、固定された昇格条件を満たすStateはない。弱い結果をintegrity BLOCKへ読み替えていない。Entry、EXIT、利益、Holdoutには進まない。

新規取得は72候補中35銘柄sessionまで完了し、U_UNAVAILABLEでexportが中断した。13日・2評価foldで測定可能だが、予定第3foldと残り取得は未完了。この限界は消さず、再選定・fold組み替え・Actions上限増加は0。全Developmentを取得できたとは主張しない。

## 🔒 Frozen identity・事前固定

V1 final HEAD `7e3ce89cb2928d46f66d4606e1010ba3a3a1896f` は開始時実GET一致。V1正式BLOCK、bootstrap超過、旧RC1 16FAIL・88workflow incident・既存Exposure/予算を保持した。
'''
 report=intro+table(['対象','SHA256／結果'],[[x['kind'],x['SHA256']+' / MATCH'] for x in load('FROZEN_IDENTITY_RECEIPT.json')['checks']]+[['V1 Contract','393de497cd2218f546ec01d2b0cf24f1d2791332c3f5400069d102ccb5e9fe41'],['V2 Contract',sha(R/'PREDICTIVENESS_V2_CONTRACT.md')],['V2 Data scope',sha(R/'DATA_SCOPE_V2.json')],['State9 / Path / profile / M0変更','各0']])
 report+='''\n事前固定はC2/C3でV2 labels・fitより前にGitHub保存。事後の意味・target・split・class/family・閾値・モデル変更は0。補助的なPath比較・図・集計は固定Contractの決定論的適用で、再fit・再drawはない。

## 🧪 V1局所forensic

V1 registered STOPは正しく発火した記録として維持し、actual leakage provenへは置き換えない。1,170 available SHIFT60 targetのsource/target時刻・連続区間・segment/fold・matched keysを直接監査して違反0。完全な60+h区間が必要なため疎なrawが多く落ち、OOF matchedはH5=81、H15=51、H30=20件、いずれも2日／1foldへ集中した。current/shift Primary一致率やPearsonは記述的で、regime依存の因果証明ではない。

V1 bootstrapはhorizon loop内で1000ずつ生成し計3000、cap1000から2000超過。V1 nonconformanceを永久保持。V2はglobal1000 vectorsを一度だけ生成し、全model/target/class/familyで再利用、独立checker新draw0。

V1 Fold2の2025-04-30／2025-06-02は5銘柄session・各horizon分母1635 endpoint。raw session自体が不在ではなく、開始点欠損・厳密horizon欠損・中間gap等で全targetが落ちた。security×date×horizonのexact countsはV1_FOLD0TARGET_REASON_COUNTS.csvを保存。
'''
 report+=table(['V1 horizon','reason','N'],[[h,k,n] for h,c in sorted(fr.items()) for k,n in sorted(c.items())])
 report+='\n## 🗃️ Development入力と実行範囲\n\n'
 report+=table(['項目','N／状態'],[['承認済みmetadata inventory','145日 / 142 currentリンク'],['新規固定対象','24日 / 72 metadata候補 / 日最大3銘柄'],['新規完了','13日 / 35 security-session'],['入力不適格skip',cc['INPUT_INELIGIBLE']],['U算定不可で中断',cc['U_UNAVAILABLE_EXPORT_ABORT']],['以後未取得',cc['NOT_ATTEMPTED_AFTER_EXPORT_ABORT']],['旧特徴量再利用','10日 / 25 security-session / 8050 endpoint'],['総入力',f"{len({p['date'] for p in pairs})}日 / {len(pairs)} security-session / {manifest['endpoint_N']} endpoint"],['新規observed/null',f'{observed} / {newnull}'],['全observed/null',f'{allobserved} / {manifest["endpoint_N"]-allobserved}'],['Primary OOF',f"{core['row_N']}件 / {core['date_N']}日 / {core['security_session_N']} security-session / {core['fold_N']}fold"],['予定fold','3（第3fold=0件を保持）'],['core日数区分','GOOD（13日）。全9State support充足の意味ではない']])
 report+='''\n全145日をmetadataで固定したうえで有限計算予算により、V1最後の再利用日より後の未使用Development24日を日付順、dated masterのhash順位で各最大3銘柄と事前固定した。価格・targetによる補充0。旧データはtrain/diagnostic、新規日をprimary OOFに使用。V2_NEW_DEV_EVALは「V1未使用」という研究内区分であり、既存strategy exposureがないFresh/OOSとは認証しない。

正規J-Quants binding・既存Development許可の継承だけを使用。追加provider request251（初回173＋修復78）、secret値の取得／表示／保存0。dated masterと当日・前日factor=1、既知State露出除外を適用。provider条件の新認証はしていない。元JSON数値lexeme→plain strへの型修復のみ行い、数値lexeme・Frozen M0は変更0。失敗run2件と消費量を保持。

一時rawは削除済みで、original response SHA・row pointer・取得時刻・exact派生Close/U・traceを保存。historical actual known_atはUNKNOWN、研究用assumed available_at=bar_endとの分離を維持。受信時刻の実証や完全provider rawの第三者再検証は本成果からはできない。

## 🎯 Targetと評価母数

NEXT_DISTINCT_PRIMARYは30 scheduled tradable slots以内に実際に生じた最初のgenuine transitionの行だけで9class評価する**条件付き**問題。先にgap/null/resetが来ればunavailable。イベント後のgapはこの条件付きdestination labelを無効にしない。NO_TRANSITIONは第10Stateにしない。

NEXT_OBSERVED_PRIMARYは隣接するcausally connected observed endpointで、同State継続を含む。これはpersistence込みで別評価。TRANSITION_WITHIN30はイベント後を含め全30slots観測可能な窓だけでbinary評価。

## 📈 Overall・9class指標（REAL OOF）

B0=prior、B1=current Primary Markov、B2=State9 tuple、B3=State9+Path。モデル選択を結果から追加していない。
'''
 report+=table(['target','model','N','accuracy','balanced','macro P','macro R','macro F1','Brier','log loss','date-equal log loss'],[[x['task'],x['model'],x['row_N'],pct(x['accuracy']),pct(x['balanced_accuracy']),pct(x['macro_precision']),pct(x['macro_recall']),pct(x['macro_F1']),num(x['Brier']),num(x['log_loss']),num(x['date_equal_log_loss'])] for x in ag if x['control']=='REAL' and x['task']!='TRANSITION_WITHIN30'])
 report+='\n## 🎯 予測State別Precision・Recall・F1\n\n全9Stateを除外せず掲載する。NAはpredicted N=0等の分母0で定義できない率。実数の支持数0を記録し、偽の0%へ置き換えない。F1のNA規約とmacroのみのzero division規約は事前固定済み。\n'
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']:
  report+='\n### '+task+' — B3\n\n'
  report+=table(['predicted State','predicted N','correct N','precision','actual N','recalled N','recall','F1','Precision 95% CI'],[[x['State'],x['Predicted_N'],x['Correct_N'],pct(x['Precision']),x['Actual_N'],x['Recalled_N'],pct(x['Recall']),pct(x['F1']),pct(x['precision_CI95_low'])+' – '+pct(x['precision_CI95_high'])] for x in states if (x['task'],x['control'],x['model'])==(task,'REAL','B3')])
 report+='\n### 全modelのState別Precision（NEXT_DISTINCT_PRIMARY）\n\n'
 report+=table(['State','B0','B1','B2','B3'],[[s]+[pct(next(x['Precision'] for x in states if (x['task'],x['control'],x['model'],x['State'])==('NEXT_DISTINCT_PRIMARY','REAL',m,s))) for m in ['B0','B1','B2','B3']] for s in classes])
 report+='\n### 全modelの9State support／Recall／F1\n\n両target×B0/B1/B2/B3の全数値、FP実destination内訳・FN predicted-as内訳はPER_STATE_PRECISION_RECALL_F1.csv。支持数専用2CSVも同梱。SHARP_RISE次distinctはB3 0/4、DROP_STOP次observedは2/2であり、後者100%を十分なEvidenceとは呼ばない。\n'
 cm=read('CONFUSION_MATRIX_9STATE.csv')
 for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']:
  lookup={(x['actual_State'],x['predicted_State']):x['N'] for x in cm if (x['task'],x['control'],x['model'])==(task,'REAL','B3')};report+='\n### '+task+' 9×9（B3、行=actual／列=predicted）\n\n';report+=table(['actual \\ predicted']+classes,[[s]+[lookup[(s,t)] for t in classes] for s in classes])
 report+='\n全model/両target/両controlsの完全matrixはCONFUSION_MATRIX_9STATE.csvと03_confusion_all_models.png/SVGに保存。\n\n## ↗️ Motion / Trend-context family\n\n「上昇」は価格利益ではなく、固定State groupに合ったという意味。UP_MOVEとUP_CONTEXTを混同しない。\n'
 report+=table(['target','family（B3）','predicted N','correct N','Precision','actual N','Recall'],[[x['task'],x['family'],x['Predicted_N'],x['Correct_N'],pct(x['Precision']),x['Actual_N'],pct(x['Recall'])] for x in motion+context if (x['control'],x['model'])==('REAL','B3')])
 report+='\nNEXT_DISTINCTのUP_MOVEは504/734＝68.66%、UP_CONTEXTは486/714＝68.07%。全model・family混同行列は専用CSV。family予測は9class argmaxの固定mappingで、family確率の再argmaxではない。\n\n## 🧭 B1→B2→B3、fold再現性、集中\n\n'
 report+=table(['target','比較','accuracy差(pp)','macro F1差(pp)','date-equal LL改善','date-equal Brier改善'],[[x['task'],x['baseline']+'→'+x['candidate'],f"{float(x['accuracy_difference'])*100:+.2f}" if x['accuracy_difference'] else 'NA',f"{float(x['macro_F1_difference'])*100:+.2f}",num(x['date_equal_log_loss_reduction']),num(x['date_equal_Brier_reduction'])] for x in read('B1_B2_B3_INCREMENTAL.csv') if x['task']!='TRANSITION_WITHIN30'])
 report+='\nNEXT_DISTINCTはB2/B3のaccuracy・macro F1がB1を上回るが、確率log lossはB1より悪い。B3はB2よりaccuracy −2.87pp、macro F1 −2.99pp、log loss改善、Brier悪化という混在で、Pathの安定したincremental valueは認証できない。NEXT_OBSERVEDはB1の67.85%がB3の63.62%より高く、persistence baselineを超えていない。\n'
 report+=table(['Primary fold','model','N','date N','accuracy','macro F1','date-equal LL'],[[x['fold'],x['model'],x['row_N'],x['date_N'],pct(x['accuracy']),pct(x['macro_F1']),num(x['date_equal_log_loss'])] for x in folds if x['task']=='NEXT_DISTINCT_PRIMARY' and x['control']=='REAL'])
 report+='\nB2/B3 accuracy改善は2foldで同方向でも、それだけでは昇格できない。State別・確率品質・集中制約は維持。B3 RISEのPrecision差CIは正でも、gross positive correctness gainは1日／1銘柄へ100%集中。PULLBACKの新規correctness gainは71.43%集中。REBOUNDはPrecisionのB1比較が改善したfoldは1つ。B3 DROPの調整CIは0を含む。B2もglobal calibration gateを通らない。PATH_INCREMENTAL_ASSESSMENT_V2.csvはB3対B2の同じ固定gateを適用し、合格0。18候補の多重比較CI tail1/720を結果後に緩めていない。\n\n## 🧪 Controls・binary imbalance\n\n'
 report+=table(['task','control','model','matched N','date N','fold N','REAL log loss','control log loss','判定'],[[x['task'],x['control'],x['model'],x['matched_row_N'],x['date_N'],x['fold_N'],num(x['REAL_log_loss']),num(x['control_log_loss']),x['status']] for x in controls if x['model'] in ['B1','B2','B3']])
 report+='\nTRUE_NULL warning0。within-date/securityのmarginal class priorを残すため理想的global iid nullではない。B0 equalityは予期されたものとして除外し、B1/B2/B3は固定control判定に従った。V1 STOP ruleの撤回はしていない。V2 SHIFT60 warning3セルはbinaryの68件・1日／1foldで、全control labelsがTRANSITIONという偏り。REGIME_PERSISTENCE_OR_SHIFT_CONTROL_WARNINGとして保存し、actual leakageとはしない。直接時刻／partition audit違反0。\n\nBinary REAL OOFは347件・4日、TRANSITION345／NO_TRANSITION2。B0/B1/B2は全TRANSITION予測で99.42% accuracyでもbalanced accuracy50%にすぎない。B3は98.27%、balanced49.42%。NO_TRANSITIONの支持数不足を保持し、発生予測が完成したとは主張しない。\n\n## 💹 V1価格negativeの継承・V2 secondary\n\n価格targetはV1どおり（future raw Close−current raw Close）/U、単位JPY/Uであり%、return、利益、Entry/EXITではない。異なる銘柄価格scaleの影響が大きい。この定義を有利な尺度へ修正していない。V1とV2は別母集団で、absolute MSEを市場性能の改善と直結しない。\n'
 report+=table(['version','horizon','model','N','date N','MSE','date-equal MSE'],[[x['version'],x['horizon'],x['model'],x['row_N'],x['date_N'],num(x['MSE']),num(x['date_equal_MSE'])] for x in price])
 report+='\nV1はB2/B3全horizonでB0よりMSE悪化を保持。V2ではrow-weighted MSEのB3 H5/H30に微小改善があるが、H15は悪化、date-equal MSEはB2/B3とも5/15/30でB0より悪い。価格secondaryでnext-State gateを救済しない。\n\n## 🔍 独立監査・予算・境界\n\n'
 report+=table(['項目','実数／結果'],[['独立main checks',audit['assertion_N']],['独立supplement checks',supp['assertion_N']],['独立不一致','0 / PASS'],['Synthetic target probes','10 paths / 20 assertions / 0 mismatch'],['V2 fit operations','210 / cap648'],['global bootstrap draws','1000 / cap1000'],['independent新draw／refit／kernel','各0'],['State9旧8050 endpoint','reuse、再kernel0'],['新規Frozen generation','11445 steps / cap36864'],['provider requests','251 / cap900'],['isolated Actions','2 / cap2、fanout1'],['V1予算','超過3000保持、V2は0超過'],['State9 / Path / profile / M0変更','各0'],['Common Holdout / Protected','各0'],['Fresh / OOS / Prospective','各0'],['Entry / EXIT / profit','各0'],['Capital / Portfolio / orders / external AI','各0'],['future classifier input','0（Development future labelsのみ許可）'],['raw / secret export','各0'],['main merge / force push','各0'],['graphs','11種類×PNG/SVG、CSV根拠あり']])
 report+='''\n独立監査はV2 candidate helperをimportせず、保存traceから63featuresのprimitive再構成、endpoint tupleからtransition/null/censoring、exact Close/U price、fold/donor purge、混同行列、family、matched control、保存1000indicesのCI、ridge最終normal equation／OOF predictionを直接再計算。State9/Path kernel全再audit0、モデル再fit0。inner-grid losses自体は別fitせず、保存lossからの選択を照合したという限界を明示する。

## 📋 必須27問への回答

1. NEXT_DISTINCT overall：B0 24.49%、B1 45.59%、B2 63.31%、B3 60.44%。
2. NEXT_OBSERVED overall：B0 28.04%、B1 67.85%、B2 63.05%、B3 63.62%。
3–7. 全9State Precision／Recall／F1／predicted・actual support／9×9：上表・全model CSV・heatmap。
8. RISE次distinct：B3 327/545＝60.00%、B2 63.23%。
9. SHARP_RISE次distinct：B3 0/4＝0.00%、support不足。
10. REBOUND次distinct：B3 125/185＝67.57%。
11. UP_MOVE次distinct：B3 504/734＝68.66%。
12. UP_CONTEXT次distinct：B3 486/714＝68.07%。
13. B1→B2：Primary accuracy＋17.72pp、macro F1＋17.25pp、date-equal LL悪化。
14. B2→B3：Primary accuracy−2.87pp、macro F1−2.99pp。確率品質はLL改善／Brier悪化の混在。
15. Path incremental value：固定昇格gateで認証できない（合格0）。
16. fold再現：2評価fold、Primary accuracy改善はB1比較で両foldだがState・calibration gate全通過なし。第3fold0は保持。
17. 集中：上記gross positive shareはStateにより1日／1銘柄依存あり。多銘柄支持数だけでは否定しない。
18. TRUE_NULL：matched log loss比較でwarning0。これ単独でpredictive promotionにはならない。
19. SHIFT60：regime stress warning、actual leakageは直接監査で未証明。V1正式STOP維持。
20. Bootstrap：V2は1000一度生成、checker0新drawで解消。V1超過は取り消さない。
21. V1 Fold2=0：開始点欠損、exact horizon欠損、中間unknown/rejected等のexact counts表。
22. V2 Primary OOF：13日／2評価fold／1360行。secondaryは13日／2fold／1751行、binary4日／2fold／347行。
23. Price：V1negative保持。V2 date-equal MSEもB2/B3全horizonでB0より悪い。
24. Entryへ渡せるもの：研究用Frozen特徴schema・失敗/支持数Evidenceのみ。昇格State／採用Path featureは0、Entry設計自動開始なし。
25. Holdout準備：未達。開封0。新しいDevelopment/calibration計画を別Contract化して判断。
26. State9／Path意味変更：各0、profile／M0変更も0。
27. Holdout／Protected／Entry／EXIT／profit exposure：今回delta各0。過去unknown/nonzero exposureは継承し0へリセットしない。

## 📦 保存と次工程

REPORT、CSV、11種graphs、OOF・fits・labels、new/old特徴trace、原本V1 ZIP、hash manifestを単一ZIPへ保存。Public GitHubはContract・source・aggregate/receiptsのみ。row-level private evidenceや原価格・秘密値をGitHubに追加していない。

最終status B。次工程は自動Entryではない。取得未完了33候補とU_UNAVAILABLEを明示した新規Development計画／V3の可否を判断する。V2結果を見て同じV2で日・銘柄を追加／補充／calibration改良することはしない。
'''
 report+='\n### 非blockingなfit記録finding\n\n実行append ledgerは206行までで、receiptの210と4行差がある。84 final fitted artifacts＋保存された42×3 inner-grid評価から必要fit210を別に再集計し、実行counter／OOF固定receiptの210と一致した。予算は210を計上、648以内。欠けた行を捏造して追記せず、元ledgerを保持。欠落原因はUNKNOWN、数値／予測の独立再現不一致は0。このprovenance限界をFIT_LEDGER_COMPLETENESS_FINDING.jsonに明示した。\n'
 (R/'REPORT-ja.md').write_text(report)
 (R/'REPRESENTATION_LIMITATIONS_V2.md').write_text('''# V2 representation / evidence limitations

- NEXT_DISTINCT_PRIMARY is conditional on an observed genuine transition within 30 scheduled tradable slots. Its precision is not unconditional success or price-return accuracy.
- NEXT_OBSERVED_PRIMARY includes persistence. Binary TRANSITION_WITHIN30 requires the full observed window and has 345:2 imbalance on 4 OOF dates.
- 13 core OOF dates, 2 evaluable folds; planned fold3 is empty because acquisition stopped before its inputs. 72 metadata proposals / 35 completed; no post-outcome refill.
- All9 classes remain. Zero predicted support => undefined precision (NA), not fabricated 0%. Tiny support such as2/2 cannot certify a100% reliable classifier.
- V2_NEW_DEV_EVAL is V1-unused Development, not certified Fresh/OOS. Legacy strategy exposure is inherited separately.
- Exact derived Close/U, canonical inputs and responsehash/rowpointers are retained. Provider raw pages were temporary and purged; actual historical known_at UNKNOWN versus assumed_available_at=bar_end. Entitlement is inherited historical operation, not a new terms certification.
- Price target retains V1 JPY/U formula, cross-security price-scale dependence; not a percent return or profit.
- Ridge clipped score normalization is not a calibrated multinomial model. Worse log loss is preserved, not repaired after results.
- Independent primitive/aggregation/model replay audit imports0V2 candidate helpers. Saved inner-loss selection is checked without independent inner refits; normal equations and final predictions directly checked.
- Date-cluster1000 bootstrap indices are shared, including empty fixed dates; unavailable draw metrics are not redrawn. Within-session label dependence,13days and2folds limit interval interpretation. Full9-class macro convention uses0onlyinside macro for undefined per-class values.
- Permutation retains within-date/security class priors, not a theoretical iid globalnull. SHIFT60 stress warning is not proof of leakage; direct timestamp/partition audits are separate.
- No Entry/EXIT/profit/Holdout validation, no causal or live trading claim. No Frozen semantic change.
''')
 (R/'NEXT_STAGE_HANDOFF.md').write_text(f'''# V2 next-stage handoff

Final status: {status}; integrity PASS; no promoted State or Path.

Read00_README.txt, FINAL_RECEIPT.json, REPORT-ja.md, PREDICTIVENESS_V2_CONTRACT.md/PRECOMMIT, GATE_FINAL_V2.json, INDEPENDENT_AUDIT_V2.json/SUPPLEMENT, BUDGET_FINAL_V2.json, EXPOSURE_APPEND_ONLY_DELTA.json and CHECKPOINTS/C6_POST_COMMIT_RECEIPT.json first.

V1 remains BLOCKED_LEAKAGE_OR_SEMANTIC_INTEGRITY at7e3ce89cb2928d46f66d4606e1010ba3a3a1896f. V1 bootstrap3000vs1000/SHIFT60STOP/zero-target fold are not cancelled. Old16FAIL/88workflow incident and unknown outside exposures remain.

Core result: B3 NEXT_DISTINCT accuracy60.44%; RISE327/545=60.00%; UP_MOVE504/734=68.66%. B2accuracy63.31%. Both have worse logloss than B1. B3Path has no stable certifiedincrement beyond B2. No Entry Timing automatic start, no Holdout opening.

Acquisition receipt: fixed72proposals,35complete,3inputqualityskips,1U_UNAVAILABLE abort,33notattempted. TwoActions consumed(cap2),251requests; newkernel11445,oldreuse8050. Do not launchmore acquisition under V2 budget. Original3blocks retained,13OOFdates/2folds; thirdfoldempty. Do not draw/select/fit/bootstrap again on resume.

If user requests continuation, define a NEW experiment (V3) before any new targets. Separate acquisition robustness/input-quality skips from semantic edits; preserve V2. Any calibrated model or expansion requires new scope/models/precommit, never revise V2 from results. All completed newdates now V2_EXPOSED_DEV. Remaining proposals are metadata-only, except39price-attempted rows shown in completeness table. Holdout/Protected/Fresh/OOS/Prospective stay sealed absent a separate explicit one-shot Contract.

INPUT_LOCATION_INDEX_V2.csv maps portable feature/trace members and hashes. Public code exists in research/state-nextstate-v2-20261002 on dedicatedbranch, pinnedfinalHEAD in C6receipt. REUSED_DEVELOPMENT contains exact25old feature/trace/M0 files, NEW_DEVELOPMENT contains35new; LABELS/FITTED/OOF are fixed private Evidence. Temporary fullproviderpages are not included and cannot be reconstructed from responsehashes alone. V1_ORIGINAL/State_Predictiveness_ALL_20261002.zip is exact inherited delivery, not newly executed.

GitHub finalwrites use evidence-only [skip ci],mainmerge0/force0. Requestcounts are append-only and reported separately from runnerartifactGETs. Use saved global1000indexvectors, checkernewdraw0. Library/signeddownload URLs are not reusable provenance.
''')
 (R/'00_README.txt').write_text(f'''Ark Terminal State Predictiveness V2 — single full Evidence bundle
Status: {status}
Read REPORT-ja.md / FINAL_RECEIPT.json / NEXT_STAGE_HANDOFF.md first.
Integrity PASS; no State/Path promoted; no automatic Entry or Holdout.
13 primary OOF days / 2 evaluable folds; acquisition incomplete, thirdfold0 retained.
V1_BLOCK and old16FAIL/88incident preserved. No scope/target/model/metric changes afterresults.
Private research data: LABELS / FITTED / OOF / REUSED_DEVELOPMENT / NEW_DEVELOPMENT.
GitHub only code/contracts/aggregate. No providerraw pages orsecretvalues.
All11PNG/SVG charts have sourceCSV. All9State models/targets remain, NA meansundefinedzero denominator.
Globalbootstrap1000generatedonce, checkernewdraw0.
V1_ORIGINAL contains exact old singleZIP. Originalcurrent-stagecode pinned inGitHub; SOURCE_CODE_LOCATION_INDEX.json providespaths/hash. Do notrerunthese to readresults.
DELIVERY_MANIFEST.json hashes everyzipmember exceptitself. DELIVERY_PACKAGE_RECEIPT.json outsidezip hashesarchive itself (avoidsrecursivehash).
''')
 save('PUBLIC_PRIVATE_SEPARATION_V2.json',{'status':'PASS','public_policy':'Code/contracts/aggregate/receipts only on dedicatedGitHubbranch','private_policy':'Row-levelOHLC-derived/features/traces/targets/OOF/trainkeys/fits remain userdelivery only','provider_response_pages':0,'secret_values':0,'no_public_row_level_upload':True,'V1_exact_archive_preserved':True})
 print(json.dumps({'status':status,'checks':audit['assertion_N']+supp['assertion_N'],'coverage':dict(cc),'observed':allobserved,'new_observed':observed,'report_bytes':(R/'REPORT-ja.md').stat().st_size,'post_result_changes':0}))
if __name__=='__main__':main()
