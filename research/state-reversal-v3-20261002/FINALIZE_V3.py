"""Finish evidence and Japanese report from fixed CSVs and passing audits."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone,timedelta
import json,csv,hashlib,math
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def now():return datetime.now(timezone(timedelta(hours=9))).isoformat()
def read(n):return list(csv.DictReader((R/n).open()))
def load(n):return json.loads((R/n).read_text())
def save(n,v):(R/n).write_text(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
def number(v):return None if v in [None,''] else float(v)
def percent(v):return 'NA' if number(v) is None else f'{float(v)*100:.2f}%'
def fmt(v):return 'NA' if number(v) is None else f'{float(v):.5g}'
def table(headers,rows):
    clean=lambda x:str(x).replace('|','\\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(clean(x) for x in row)+' |' for row in rows])+'\n'
def main():
    audit=load('INDEPENDENT_AUDIT_V3.json');supp=load('INDEPENDENT_SUPPLEMENT_V3.json');assert audit['status']==supp['status']=='PASS','CORE_AUDIT_MUST_PASS'
    gate=load('GATE_ASSESSMENT_V3.json');status=gate['status_pending_integrity_PASS'];stamp=now()
    aggregate=read('REVERSAL_METRICS_AGGREGATE.csv');pcs=read('REVERSAL_PER_CLASS_METRICS.csv');danger=read('UP_TO_DOWN_DANGEROUS_FALSE_POSITIVE.csv');inverse=read('DOWN_TO_UP_FALSE_NEGATIVE.csv')
    get=lambda task,model,cal=True:next(x for x in aggregate if x['task']==task and x['control']=='REAL' and x['model']==model and (x['calibrated']=='True')==cal)
    pc=lambda model,c:next(x for x in pcs if x['task']=='CONTEXT_REVERSAL' and x['control']=='REAL' and x['model']==model and x['calibrated']=='True' and x['class']==c)
    risks={x['model']:x for x in danger if x['group_kind']=='ALL'};reverses={x['model']:x for x in inverse if x['group_kind']=='ALL'}
    models=['R0','R1','R2','R3','R4'];manifest=load('DATASET_MANIFEST.json');runner=load('NEW_DEVELOPMENT/RUNNER_FINAL_RECEIPT.json');source=load('NEW_DEVELOPMENT/SOURCE_RECEIPTS.json');ledger=read('DEVELOPMENT_COMPLETION_LEDGER.csv')
    budget=load('BUDGET_START_V3.json');caps=budget['V3_caps'];executions=list(map(json.loads,(R/'MODEL_EXECUTION_LEDGER.jsonl').read_text().splitlines()));classes=load('REVERSAL_TARGET_SCHEMA.json')['classes']
    actual={'provider_HTTP_requests':runner['provider_requests'],'isolated_Actions_runs':1,'Actions_fanout':1,'pending_proposals_processed':33,'completed_pairs':len(manifest['pairs']),
        'new_frozen_steps':runner['new_steps'],'old_saved_endpoint_reuse':19495,'fit_operations':len(executions),'final_fitted_artifacts':180,'inner_fitted_artifacts':396,
        'bootstrap_generated_vectors':1000,'independent_new_draws':0,'independent_new_fits':0,'independent_new_kernel_steps':0,
        'resume_new_provider_requests':0,'resume_new_fits':0,'resume_new_label_generation':0,'resume_new_bootstrap_draws':0,
        'independent_main_launches':3,'independent_main_completed_passes':1,'independent_supplement_launches':1,'render_launches':1,'unique_figures':12,
        'main_merge':0,'force_push':0,'external_AI':0,'new_target_split_family_threshold_model_changes':0}
    save('BUDGET_FINAL_V3.json',{'JST':stamp,'V3_caps_unchanged':caps,'delta':actual,'V3_finite_budget_compliant':True,
        'inherited_budget':budget['inherited_V2_budget'],'inherited_V1_bootstrap_breach_retained':True,'old16FAIL':16,'old88workflow_incident':88,
        'cumulative_known_provider_HTTP':485,'cumulative_known_frozen_steps':42652,'cumulative_known_generated_bootstrap_vectors':5000,
        'GitHub_invocations':'GITHUB_REQUEST_USAGE_AT_DELIVERY.json; connector invocations separated from unknown wrapper HTTP fanout'})
    exposed=sorted(set(load('V1_V2_EXPOSED_DEV.json')['dates'] if 'dates' in load('V1_V2_EXPOSED_DEV.json') else load('DATA_SCOPE_V3.json')['V1_V2_exposed_dates']))
    save('EXPOSURE_APPEND_ONLY_DELTA.json',{'JST':stamp,'parent_exposure_ledger':'Original V2 EXPOSED ledger in original bundle; unchanged',
        'V1_V2_exposed_dates_retained':exposed,'V3_price_attempted_dates':load('V3_NEW_DEV_EVAL.json').get('dates',load('SPLIT_PLAN_V3.json')['fixed_three_blocks'][0]),
        'V3_acquired_dates':manifest['new_eligible_dates'],'V3_new_scope_dates_are_now_exposed':True,'provider_price_rows_returned':sum(x['row_N'] for x in source),
        'reversal_label_available_rows':gate['core_rows'],'OOF_prediction_records_reused':105090,
        'Common_Holdout':0,'Protected':0,'Fresh':0,'OOS':0,'Prospective':0,'Entry':0,'EXIT':0,'profit':0,'Capital':0,'Portfolio':0,'broker_orders':0,
        'future_classifier_input':0,'raw_pages_exported':0,'secret_values_exported':0,'prior_outside_exposure_unknown_nonzero_retained':True})
    save('ROUTINE_REPAIR_RECEIPT.json',{'JST':stamp,'C5_JSONL_restore':'C5_RESTORE_RECEIPT.json; exact original SHA from complete CSVs, truncated prefix retained',
        'independent_checker_early_launch':'Stopped on independent primitive counter attribute mismatch; fixed module integration, no candidate changes',
        'independent_checker_second_launch':'Interrupted to hoist invariant max(train_date) out of per-row comprehensions; equivalent checks',
        'independent_checker_third_launch':'Completed PASS','new_fits':0,'new_draws':0,'Frozen_changes':0,'model_target_split_threshold_changes':0})
    save('FINAL_RECEIPT.json',{'JST':stamp,'document_id':'WORK_STATE_PREDICTIVENESS_V3_REVERSAL_MAX_THROUGHPUT_20261002_V1','status':status,'integrity':'PASS',
        'V2_status_retained':'STATE_NEXTSTATE_PREDICTIVENESS_MEASURED_NO_PROMOTABLE_STATE','V1_BLOCK_retained':True,
        'Contract_SHA256':sha(R/'PREDICTIVENESS_V3_REVERSAL_CONTRACT.md'),'data_scope_SHA256':sha(R/'DATA_SCOPE_V3.json'),
        'OOF_SHA256':sha(R/'OOF_ALL.jsonl'),'primary_OOF_rows':gate['core_rows'],'primary_OOF_dates':gate['core_dates'],'primary_OOF_folds':gate['core_folds'],
        'class_support':gate['class_support'],'promoted_reversal_features':[],'promoted_paths':[],'independent_assertion_N':audit['assertion_N']+supp['assertion_N'],
        'mismatch_N':0,'new_bootstrap_draws_this_resume':0,'new_fits_this_resume':0,'acquisition_completed':30,'acquisition_skipped':3,
        'original72_proposals_acquired':65,'original72_proposals_unavailable':7,'remaining_unclassified_original_proposals':0,
        'State9_Path_profile_M0_changes':0,'Holdout_Protected_Entry_EXIT_profit_delta':[0,0,0,0,0],
        'next_action':'New precommitted Development/calibration experiment required; no current promotion or automatic Holdout/Entry.'})
    summary=[]
    for m in models:
        metric=get('CONTEXT_REVERSAL',m);up=pc(m,'UP_CONTINUE');down=pc(m,'DOWN_REVERSAL');risk=risks[m]
        summary.append([m,percent(metric['accuracy']),percent(up['Precision']),percent(down['Precision']),percent(down['Recall']),
            f"{risk['opposite_actual_N']}/{risk['predicted_N']} = {percent(risk['rate'])}",fmt(metric['date_equal_log_loss'])])
    report=[f'# Ark Terminal — State Predictiveness V3 最終報告\n\n作成JST：{stamp}\n\n**{status}**。Integrity PASS、独立核心不一致0、採用するReversal／Pathは0件。',
        '現在StateだけのR1に対し、full State9のR2は危険誤予測の点推定を17.70%から12.78%へ下げた。しかしCoreは597 anchor・6評価日・3foldで、下降反転は98件。固定した8日・actual support100件の基準を満たさない。Path追加のR3/R4はR2より危険誤予測が多く、較正後の確率log lossもbaselineより悪い。サンプル不足をintegrity BLOCKへ読み替えず、今回の測定をCで固定する。',
        '## 主要結果\n\n'+table(['model','accuracy','UP precision','DOWN precision','DOWN recall','UP予測→DOWN実現','date-equal log loss'],summary),
        'R0=全体prior、R1=current Primary、R2=State9全tuple、R3=State9＋従来Path、R4=State9＋反転用Path Anatomy。DOWNは価格損失の定義ではなく、Frozen context=-1を伴う最初の確認済みState遷移。REBOUNDもcontextがDOWNなら含む。UP継続はgenuine transitionによるRISE／SHARP_RISEかつcontext/local=+1で、単なるHOLDは含めない。',
        '![危険誤予測と95%日cluster区間](CHARTS/02_up_to_down_dangerous_error.png)',
        table(['model','危険誤予測率','95% cluster区間','DOWN予測→UP実現'],[[m,percent(risks[m]['rate']),percent(risks[m]['CI95_low'])+'–'+percent(risks[m]['CI95_high']),f"{reverses[m]['opposite_actual_N']}/{reverses[m]['predicted_N']} = {percent(reverses[m]['rate'])}"] for m in models]),
        '分母はUPを予測したanchorであり、DOWNの全実例98件に対するRecallとは別。30slot窓とminute anchorは重複する。95%区間は保存済みの同じ1000 date-cluster vectorsから計算した記述的区間で、独立した売買試行の精度ではない。6日で区間は広い。',
        '![class別precisionとrecall](CHARTS/01_reversal_class_precision_recall.png)',
        '## 取得・評価母数\n\n'+table(['項目','結果'],[['固定72候補','ACQUIRED 65 / U_UNAVAILABLE 4 / RAW_UNAVAILABLE 3'],['今回の残り33候補','30取得 / 3 U_UNAVAILABLE / 未分類0'],['総データ','34日 / 90 security-session / 29,305 endpoint'],['全observed / null','6,289 / 23,016'],['新しいFrozen生成','9,810 endpoint; 原本19,495 endpointは再利用'],['新規固定日','11日、全日で最低1 session取得'],['Core OOF','597 rows / 6日 / 11 security-session / 3fold'],['Core actual labels','UP 458 / DOWN 98 / RANGE_OR_STOP 41 / NO_DECISION 0'],['Motion OOF','677 rows / 9日 / 16 security-session / 3fold'],['次distinct 9State OOF','1,490 rows / 10日 / 17 security-session / 3fold'],['次observed 9State OOF','1,791 rows / 11日 / 23 security-session / 3fold']]),
        '全145日／142 currentリンクを取得したとは主張しない。72候補の選定順と銘柄を維持し、結果後の補充0。N039の過去U_UNAVAILABLE中断と旧3skipも元Evidenceに保持し、V3で欠けた3件も次銘柄へ置換しなかった。11取得日でもgap・null・session境界などによりCoreの有効日は6日に減る。Coreの8日ゲートをsecondary 9Stateの10／11日で救済しない。',
        '## Fold・確率品質\n\n'+table(['fold','rows','dates','R1 accuracy','R2 accuracy','R4 accuracy','R2 date-equal LL','R4 date-equal LL'],[[str(f),*(lambda z:[z['row_N'],z['date_N']])(next(x for x in read('REVERSAL_METRICS_BY_FOLD.csv') if x['task']=='CONTEXT_REVERSAL' and x['control']=='REAL' and x['model']=='R0' and x['calibrated']=='True' and x['fold']==str(f))),*[(percent if k=='accuracy' else fmt)(next(x for x in read('REVERSAL_METRICS_BY_FOLD.csv') if x['task']=='CONTEXT_REVERSAL' and x['control']=='REAL' and x['model']==m and x['calibrated']=='True' and x['fold']==str(f))[k]) for m,k in [('R1','accuracy'),('R2','accuracy'),('R4','accuracy'),('R2','date_equal_log_loss'),('R4','date_equal_log_loss')]]] for f in [1,2,3]]),
        '![fold安定性](CHARTS/06_fold_stability.png)',
        table(['model','未較正date-equal LL','較正後date-equal LL','較正後date-equal Brier'],[[m,fmt(get('CONTEXT_REVERSAL',m,False)['date_equal_log_loss']),fmt(get('CONTEXT_REVERSAL',m)['date_equal_log_loss']),fmt(get('CONTEXT_REVERSAL',m)['date_equal_Brier'])] for m in models]),
        'temperatureは各foldの最後のtraining日だけで固定し、testで再選択していない。今回、R1–R4のouter probability log lossは較正によって悪化した。R2はFold2で特に大きく悪化した。ridge scoreのclip→normalizeと温度調整の組合せで、誤ったclassへ極小確率を割り当てるリスクが残ったという結果を保持する。良かった未較正版へ結果後に選び直してpromotionしない。温度調整はargmaxを維持し、accuracy／危険誤予測率は変えない。',
        '![較正前後log loss](CHARTS/04_calibrated_vs_uncalibrated_log_loss.png)\n\n![DOWN確率の較正](CHARTS/05_down_reversal_calibration.png)',
        '## Pathの追加効果・集中\n\nR2→R3でaccuracyは80.07%→76.88%、危険誤予測は12.78%→14.26%。R3→R4でaccuracyは76.88%→77.05%、危険誤予測は14.26%→13.86%、date-equal LLは2.9031→2.2638へ改善したが、R2よりaccuracy／DOWN recallが低く、R1よりlog lossが悪い。反転用Anatomyの有用性を認証する条件は満たさない。',
        '![R0–R4比較](CHARTS/03_r0_r4_incremental_performance.png)\n\n![日・銘柄への集中](CHARTS/07_date_security_concentration.png)',
        '危険誤予測の件数シェアと、promotionに使うgross positive correctness gainの集中は別集計。PROMOTION_GATE_V3.csvに全モデル／UP・DOWN候補／R1・R2比較のprecision調整CI・calibration・recall・risk・集中gateを保存した。1日／1銘柄へ改善が集中するcaseもある。今回deltaのR4 gainだけで将来の個別feature効果を因果認証しない。',
        '## 反転前Pathの記述\n\n'+table(['current State','N','日','UP継続','DOWN反転','Range/Stop'],[[x['sequence'],x['N'],x['date_N'],f"{x['UP_CONTINUE_N']} / {percent(x['UP_CONTINUE_rate'])}",f"{x['DOWN_REVERSAL_N']} / {percent(x['DOWN_REVERSAL_rate'])}",f"{x['RANGE_OR_STOP_N']} / {percent(x['RANGE_OR_STOP_rate'])}"] for x in read('REVERSAL_PATH_ANATOMY_LENGTH1.csv')]),
        table(['history長','sequence数','完全history anchor','最大N','支持基準合格sequence'],[[x['length'],x['sequence_N'],x['complete_history_anchor_N'],x['largest_sequence_N'],x['supported_sequence_N']] for x in read('PATH_ANATOMY_SUPPORT_SUMMARY.csv')]),
        'history長1=currentのみ、長2=current＋直前1 run、長3=直前2、長4=直前3。R4のpredictor自体は直前1–4 completed runを使う。dwellはanchor時点で既知の値だけで、未来のrun最終長を読まない。未形成historyはMISSINGのまま出す。',
        table(['3-State sequence','N','日','DOWN / rate','UP / rate'],[[x['sequence'],x['N'],x['date_N'],f"{x['DOWN_REVERSAL_N']} / {percent(x['DOWN_REVERSAL_rate'])}",f"{x['UP_CONTINUE_N']} / {percent(x['UP_CONTINUE_rate'])}"] for x in read('REVERSAL_PATH_ANATOMY_LENGTH3.csv') if x['history_complete']=='True'][:8]),
        'RISE>PULLBACK>RISEは193 anchorでUP164、DOWN25だが6日。RISE>DROP>RISEは41 anchorでUP11、DOWN15、Range15。SHARP_RISEは4 anchor・1日だけでDOWN0、RISE_STOPは22 anchorでUP8／DOWN8／Range6。支持不足の100%や小Nの反転率を高精度パターンとは呼ばない。全sequenceの支持基準はN>=100・日>=8・銘柄>=3で、合格0。',
        '![長さ別supportと反転率](CHARTS/08_path_length_support_vs_reversal_rate.png)\n\n![反転を含む高支持Path](CHARTS/09_highest_support_down_reversal_paths.png)\n\n![継続を含む高支持Path](CHARTS/10_highest_support_up_continue_paths.png)',
        '## Controls・9State secondary\n\n'+table(['control','model','matched N','日','REAL date-equal LL','control date-equal LL','warning'],[[x['control'],x['model'],x['matched_row_N'],x['date_N'],fmt(x['REAL_date_equal_log_loss']),fmt(x['control_date_equal_log_loss']),x['warning']] for x in read('NEGATIVE_CONTROL_V3.csv') if x['task']=='CONTEXT_REVERSAL' and x['calibrated']=='True' and x['model'] in ['R2','R3','R4']]),
        'TRUE_NULLのCore R2は固定したdate-equal LL規約でwarning。R3/R4はこのwarningなしでも他gateを通らない。TRUE_NULLは同日・同security-sessionでlabel/provenanceを一緒に置換するため、group marginal priorは残る。SHIFT60 Coreは131 matched rows・3日・3fold、R2–R4に同等性能warningなし。強弱はregime/dependence stressの結果で、actual leakageの証明とは扱わない。timestamp／partitionは直接照合した。',
        table(['task','V3 R1','V3 R2','V3 R3','V3 R4'],[[task,*[percent(get(task,m)['accuracy']) for m in ['R1','R2','R3','R4']]] for task in ['NEXT_DISTINCT_PRIMARY','NEXT_OBSERVED_PRIMARY']]),
        'V2の次distinct B3 accuracy60.44%に対し、V3 R3は70.13%。ただし別の評価日・母集団であり、制御された改善証明とはしない。V3次distinctのSHARP_RISE actual supportは2件、次observedは4件。9State全class、分母0のNA、支持不足を除外していない。rare Stateのsupportが一様に増えたとは言えない。全modelのPrecision／Recall／F1・支持数・9×9はCSVを正とする。',
        '![V2とV3のState precision](CHARTS/11_nine_state_precision_v2_vs_v3.png)\n\n![V3全modelの9×9](CHARTS/12_nine_by_nine_confusion_all_models.png)',
        '図の略号：RS=RISE_STOP、R=RISE、SR=SHARP_RISE、PB=PULLBACK、RG=RANGE、RB=REBOUND、SD=SHARP_DROP、D=DROP、DS=DROP_STOP。',
        '## 監査・保存・境界\n\n'+table(['項目','実数／状態'],[['独立main照合',audit['assertion_N']],['独立補助照合',supp['assertion_N']],['核心不一致','0 / PASS'],['fit / cap','576 / 1200（final180＋inner396）'],['provider HTTP / cap','66 / 900'],['Frozen generation / cap','9810 / 18000'],['global bootstrap','1000一度生成、全集計で再利用'],['今回resumeでfit / label / draw / provider','各0'],['図','12種類×PNG/SVG、CSV hash照合PASS'],['State9 / Path / profile / M0変更','各0'],['Common Holdout / Protected / Fresh / OOS / Prospective','各0'],['Entry / EXIT / profit / Capital / Portfolio / orders','各0'],['main merge / force push / external AI','各0']]),
        '独立照合は別コードで、同じassistantが実施したものであり、外部の独立人間レビューではない。Frozen原本hash、保存traceからの63 primitive feature、causal prefix Anatomy、event order、censoring、donor/fold purge、全final／inner係数のnormal equation、inner-grid／temperature選択、固定OOF、class混同行列、risk、保存bootstrap CI、calibration bucket、promotion、図CSVを照合した。再fit／kernel／provider／bootstrap新drawは0。purge済みのAPI full raw responseを取得し直した監査ではない。historical known_at UNKNOWNと研究assumed bar_endの区別を保持する。',
        'C5 JSONLは74,885行で途切れていたが、完全な4 CSVから105,090行を復元し、元C5 SHA `2b13dd18c80723dc2ab4838e62c6804d4e999b94f3019c8a54d71e0f7d4b87fe` とbyte一致。切れた原本も保持した。checkerのmodule接続修復と同値の計算効率修復はROUTINE_REPAIR_RECEIPTに記録し、結果・target・split・thresholdを変えていない。',
        'V1の正式BLOCK・3000/cap1000の過去超過・旧RC1 16FAIL・88workflow incident・V2のno promotion・4行append ledger欠落を保存し、過去budget／outside exposure unknown/nonzeroを0へリセットしない。GitHubは専用branchのcode／Contract／aggregateのみ。row-level features／traces／labels／OOF／fitsはユーザー用Evidence ZIPへ保存する。',
        '## 次の方針\n\n今回の33候補は全件分類済み。既存V3を結果に合わせて拡張・再較正しない。次に進める場合は、承認済み145日metadata inventoryから未使用Developmentを日付順・metadataだけで選ぶ追加取得計画を、新しいscope／有限budget／precommitに固定する。Coreの有効日8以上とDOWN support100以上を取得件数とは別に満たす必要がある。結果駆動の銘柄補充は行わない。',
        'ridgeの確率品質と単日inner selectionの不安定さが残った。次の別Contractで、適切なprobability modelやcalibration法・固定小gridを先に決め、既存V3をexposedとして扱って測る。現在のEntry／EXITへ渡せる採用featureは0。再利用できるのはFrozen schema、prefix処理、危険誤予測の定義・Evidenceと失敗知見。Holdout準備は未達で開封0。']
    answers=[
        ['1–2','DOWN / UP予測','R2 DOWN P64.29%・R27.55%、UP P81.67%・R96.29%。R4 DOWN P57.50%・R23.47%、UP P79.67%・R94.10%。'],
        ['3–4','危険誤予測・baseline比較','R1 86/486=17.70%、R2 69/540=12.78%、R4 75/541=13.86%。点推定は改善、採用認証なし。'],
        ['5','R1→R2','accuracy／DOWN precision改善、較正後date-equal LL悪化・support不足。'],['6','R2→R3','危険誤予測・accuracy・DOWN recall悪化、Path採用なし。'],['7','R3→R4','一部改善があるがR2／R1追加gate不成立。'],
        ['8','較正','R1–R4のouter LL悪化。未較正版へ事後切替しない。'],['9','current State','RISE／PULLBACKは記述的比較可能。全classの8日support不足。'],['10','RISE前Path','上記高支持tableと全長1–4 CSV。独立予測パターンとしては未認証。'],['11','SHARP_RISE前Path','4 anchor・1日。DOWN0でも読みやすいとは主張できない。'],['12','RISE_STOP後','UP8／DOWN8／Range6、全22件。'],['13','PULLBACK','UP198／DOWN14／Range4、全216件。継続の高い記述率はあるが採用gate未達。'],
        ['14–15','history長・支持sequence','長さ1–4を保存。長くするとhistory不足・small N増。支持基準合格sequence0。'],['16','日／銘柄依存','6評価日。集中CSV・図・promotion gain shareを保存し、依存なしとは認証しない。'],['17','TRUE NULL','Core R2 warningあり。R3/R4もcalibration/support等で採用不可。'],['18','SHIFT60','Core131 matched rows、R2–R4同等warningなし。regime stressでありleak証明ではない。'],
        ['19','9State比較','V3 R3 next-distinct70.13%。V2とは別日・別母集団。controlled improvement未認証。'],['20','rare State','全9Stateを保存。SHARP_RISE support等が少なく、一様増加なし。'],['21','第3fold','確保。ただしCore Fold3は1評価日。'],['22','残り取得','33候補=30取得・3skip。固定72候補の未分類0。'],['23–24','Entry／EXIT再利用','採用feature0。schema・危険誤予測定義・prefix実装・Evidenceのみ研究再利用可。'],['25','Holdout準備','未達、開封0。'],['26','State9／Path意味変更','各0、profile／M0も0。'],['27','禁止exposure','Holdout／Protected／Entry／EXIT／profitの今回delta各0。過去unknown/nonzeroは保持。']]
    report.append('## 必須27問への対応\n\n'+table(['番号','問い','回答'],answers))
    (R/'REPORT-ja.md').write_text('\n\n'.join(report)+'\n')
    (R/'00_README.txt').write_text('Ark Terminal State Predictiveness V3 — full fixed evidence\nStatus: '+status+'\nIntegrity PASS, promoted Reversal/Path = 0.\n597 core anchors / 6 OOF dates / 3 folds; DOWN actual 98.\nRead REPORT-ja.md, FINAL_RECEIPT.json, NEXT_STAGE_HANDOFF.md first.\nV1/V2 originals and weak results retained. No model/target/split/bootstrap rerun on resume.\nOOF JSONL restored byte-identically to original C5 receipt; truncated prefix preserved.\nIndependent helper-free audit and supplement PASS; no fits/draws/kernel/provider.\nPrivate rows and fitted artifacts in this ZIP; public code/contracts/aggregate in dedicated GitHub branch.\nSOURCE_CODE_LOCATION_INDEX.json identifies code retrieval; no duplicate repository upload.\nDATASET_MANIFEST.json is exact original. DATASET_MANIFEST_PORTABLE.json and INPUT_LOCATION_INDEX_V3.csv give archive-relative file paths.\nOriginal V2 bundle is included unchanged; purged full provider pages and secrets are absent.\nDELIVERY_MANIFEST.json hashes every package member except itself; outer archive SHA is separate.\nDo not open Holdout/Protected/Fresh/OOS/Prospective or start Entry/EXIT/profit automatically.\n')
    (R/'NEXT_STAGE_HANDOFF.md').write_text('# V3 next-stage handoff\n\nFinal: '+status+'; integrity PASS; promotions0.\n\nRead README, FINAL_RECEIPT, REPORT-ja, Contract/precommit, scope/budget, DATASET manifests, C4/C5 receipts, C5 restore receipt, both independent audits, promotion/risk/control CSVs.\n\nFixed corpus90 sessions/29305 endpoints; original72 proposals all classified65 acquired7 unavailable; V3 pending33 processed30 acquired3 U_UNAVAILABLE. FrozenState9/Path/profile/M0 unchanged.\n\nCore597 anchors/6 OOF dates/3 folds (fold dates2/3/1), DOWN98. R1 dangerous86/486=17.70%; R2=69/540=12.78%; R4=75/541=13.86%. Calibration outer LL worsened; R4 not an incremental certified improvement over R2. No sequence reaches8-date support.\n\nNo rerun of labels/fits/draws/acquisition under current V3. 576 fits,1000 vectors generated once,66 provider requests,9810 new Frozen steps,1 Actions run; independent refits/draws0. OOF restores original C5 SHA exactly; prefix original retained.\n\nNext only a new precommitted Development acquisition/probability-calibration experiment from authorized metadata, no outcome replacement. Current V3 dates are now exposed. Keep V1 BLOCK, old16FAIL/88incident, V2 no-promotion and ledger gap, outside-exposure unknown/nonzero.\n\nNo current Entry/EXIT feature promotion, Holdout opening, profit, orders, external AI, main merge, force push.\n')
    print(json.dumps({'status':status,'integrity':'PASS','report_bytes':(R/'REPORT-ja.md').stat().st_size,'assertions':audit['assertion_N']+supp['assertion_N']}))
if __name__=='__main__':main()
