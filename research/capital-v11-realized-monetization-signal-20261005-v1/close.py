"""Append-only failure closure from completed receipts; no fit/evaluation/audit rerun."""
from control import *
import sys,zipfile
def decision():
    audit=read(OUT/'INDEPENDENT_SIGNAL_AUDIT.json');point=read(OUT/'MRET_POINT_GATE_PENDING_INDEPENDENT_AUDIT.json')
    gates=point['conditions_before_independent_audit']|{'S9':audit['status']=='PASS' and audit['mismatch_N']==0}
    ci=read(OUT/'SESSION_BOOTSTRAP_RESULT.json')['deltas']['MRET_AUC_delta']['CI95']
    strong=all(gates.values());promising=all(gates[k] for k in gates if k!='S8') and ci[0]<=0<=ci[1]
    signal='MRET_STRONG' if strong else ('MRET_PROMISING' if promising else 'MRET_NO_GO')
    assert not strong and audit['mismatch_N']>0,'This closure handles observed contract failure only'
    assert counts()['newFits']==8 and counts()['CapitalReplays']==0
    o={'exact_jst':now(),'monetizationSignal':signal,'status':'V11_CONTRACT_FAIL','gate':gates,'failed_conditions':[k for k,v in gates.items() if not v],'point_conditions_PASS_N':sum(point['conditions_before_independent_audit'].values()),'best_existing_control':point['best_existing_control'],'block_improved_N':point['block_improved_N'],'independent_mismatch_N':audit['mismatch_N'],'independent_max_abs_difference':audit['float_max_abs_difference'],'tolerance':1e-12,'capitalReplayAllowed':False,'CapitalReplays':0,'selectedCapitalCandidate':None,'NEXT_BOTTLENECK':'REALIZED_MONETIZATION_INFORMATION_GAP','bottleneck_rule':'Precommitted not-STRONG rule; contract failure prevents certification, not statistical proof of absent information','interpretation_blocked':'Point signal conditions all pass. One independent preprocessing numeric check invalidates S9. Do not interpret this as certified MRET statistical NO_GO or as EXIT failure.','same_cycle_retry':False,'Safety':SAFETY}
    save(OUT/'SIGNAL_GATE_DECISION.json',o)
    save(OUT/'NUMERIC_CONTRACT_FAILURE_RECEIPT.json',{'exact_jst':now(),'scope':'Existing completed audit receipt only; no recomputation','audit_sha256':sha(OUT/'INDEPENDENT_SIGNAL_AUDIT.json'),'checks':audit['checks'],'mismatch_N':audit['mismatch_N'],'failures':audit['failures'],'maximum_absolute_difference':audit['float_max_abs_difference'],'fixed_tolerance':1e-12,'location_field':'numeric scale index5, selector/first_clock; failure receipt did not record block in check name','primary_algorithm':'NumPy population standard deviation of zero-imputed numeric plus missing indicators, per frozen Movement algorithm','independent_algorithm':'math.fsum central squared deviations with independently computed mean','OOF_and_metric_checks':'All score/metric/bootstrap comparisons passed the same tolerance; only listed scale check failed','refit':0,'re_evaluation':0,'independent_audit_rerun':0,'tolerance_change':0,'contract_failure_honored':True,'CapitalReplays':0,'Safety':SAFETY})
    checkpoint('R9_SIGNAL_GATE_DECISION',o,'R10 fixed STOP; Capital replay0; no repair/refit/re-evaluation in this cycle')
    print(json.dumps({'status':o['status'],'signal':signal,'failed_conditions':o['failed_conditions'],'newFits':8,'CapitalReplays':0}))
def finish():
    gate=read(OUT/'SIGNAL_GATE_DECISION.json');audit=read(OUT/'INDEPENDENT_SIGNAL_AUDIT.json');teacher=read(OUT/'MRET_TEACHER_RESULT.json');result=read(OUT/'MRET_PRIMARY_RESULT.json');boot=read(OUT/'SESSION_BOOTSTRAP_RESULT.json');diag=read(OUT/'FROZEN_EXIT_REALIZED_DIAGNOSTICS.json');negative=read(OUT/'HF1_HL0_NEGATIVE_HISTORY_FREEZE.json')
    assert gate['status']=='V11_CONTRACT_FAIL' and counts()['CapitalReplays']==0
    protected=read(WORK/'PROTECTED_TRACKED_HASHES.json');assert all(sha(ROOT/p)==h for p,h in protected.items()),'OLD_EVIDENCE_CHANGED'
    claim=read(OUT/'MRET_FIT_CLAIM.json');assert all(sha(ROOT/p)==h for p,h in claim['code_sha256'].items()),'FIT_CODE_CHANGED'
    save(OUT/'FINAL_STATIC_SCOPE_AUDIT.json',{'exact_jst':now(),'old_tracked_files_checked':len(protected),'old_rewrite_N':0,'claimed_fit_code_changed_N':0,'newFits':8,'optimizer_calls':8,'performance_eval_N':1,'independent_signal_audit_N':1,'independent_mismatch_N':audit['mismatch_N'],'CapitalReplays':0,'M1_M2_started_N':0,'R10_percentile_R11_canary_R12_pre_main_cap_audit':'not reached because no STRONG certification','fit_or_evaluation_reexecution':0,'Safety':SAFETY})
    scores=result['scores'];best=result['best_existing_control']
    lines=['# Capital v11 Realized Monetization Signal — Final Report','',
      '## A. Executive / v10 authority','',
      '**V11_CONTRACT_FAIL。8 fitsを完了し、Capital replay0で固定STOP。** MRETの統計条件S1–S8は全てPASSしたが、独立監査でtraining scaleの差1件が固定許容1e-12を超えた（最大1.5774048733874224e-12）。S9 FAILのためMRET_STRONGを認証せず、M1/M2を実行しない。失敗receiptを保持し、refit・再評価・監査再実行・許容拡張による救済0。','',
      f'v10 actual terminal HEAD `{PARENT_SHA}`。CURRENT_STATE=CAPITAL_V10_M15_CLOSURE_FIXED_STOP / V10_REALIZED_MONETIZATION_LIMIT / diagnosticArm=S1 / NEXT_BOTTLENECK=REALIZED_MONETIZATION_SIGNAL。private SHA256 `{PACK_SHA}` を含むnested Main/Quality manifest全一致。v10 canonical close timeはM15 checkpointの2026-10-05T11:42:18.983693+09:00。旧cycleはread-only。','',
      'Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。同じ58 Development sessions（warmup20、OOF38）を再利用。Fresh/OOS成功、将来収益、production readinessの主張なし。','',
      '## B. Quality-v3 HF1/HL0 negative history','',
      f"HF1（realized>=1%）AUC={negative['HF1']['ROC_AUC']:.6f}、HL0（realized<=0）AUC={negative['HL0']['ROC_AUC']:.6f}、OOF各1016、CORE27+7。旧composite QはTOP3_SELECTION_WORSE / CAPITAL_QUALITY_V3_WORSE。HF1/HL0/LSAFE/Q1–Q8再実行0。今回はabsolute thresholdをteacherにせず、Potential bucket内のcompleted-train中央値を基準にする。Xはraw pre-entry Movement46+7、pP/q2/q3のstackingなし、I2 selectionは永久Freeze。",'',
      '## C. MRET Teacher','',
      'Label=1 iff Frozen EXIT realized > block completed-past bucket median。exact tie=0。通常のempirical median（偶数supportは中央2値の平均）。bucket support>=10、backoff/merge0。missing realized / incomplete potentialを除外し、0-imputeしない。trainは既存Movementのpre15:20 candidate universe、heldout teacherをtrainerに渡さない。','',
      f"OOF common-supportedかつMRET評価可能N={teacher['OOF_evaluable_N']}、positive={teacher['OOF_positive_N']}、exact tie={teacher['OOF_exact_tie_N']}、current1039からの除外={teacher['OOF_excluded_N']}。全56 block×bucket cellの最小support={teacher['minimum_support']}。",'',
      '|Block|Train N|Positive|Missing realized excluded|Potential incomplete excluded|','|---|---:|---:|---:|---:|']
    for t in teacher['blocks']:lines.append(f"|{t['block']}|{t['train_N']}|{t['train_positive_N']}|{t['missing_realized_excluded_N']}|{t['potential_incomplete_excluded_N']}|")
    lines+=['','各cellは `median realized% / support / exact ties`。','', '|Bucket|'+'|'.join('B'+str(b) for b in range(1,9))+'|','|---|'+'---:|'*8]
    names=['<1','1–<2','2–<3','3–<4','4–<5','5–<10','>=10']
    for k,name in enumerate(names):
        cells=[t['buckets'][str(k)] for t in teacher['blocks']]
        lines.append('|'+name+'|'+'|'.join(f"{c['median_realized']*100:.6f}% / {c['support']} / {c['exact_tie_N']}" for c in cells)+'|')
    lines+=['','## D. MRET Signal Result','',
      f'BEST_EXISTING_CONTROL={best}：C0–C3のMRET-target AUC最大というprecommitted rule。全scoreを同じ1016 identitiesで比較。raw Logistic scoreはordering用途でありtrue probabilityとは呼ばない。PR-AUCはaverage precision。','',
      '|Score|MRET AUC|PR-AUC|Brier|realized>0 AUC|>=1 AUC|bucket concordance|block improved vs best|','|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in ['pP','q2','q3','consensus','mP']:
        r=scores[s];improved=sum(r['blocks'][str(b)]['AUC']>scores[best]['blocks'][str(b)]['AUC'] for b in range(1,9))
        lines.append(f"|{s}|{r['MRET']['AUC']:.6f}|{r['MRET']['PR_AUC']:.6f}|{r['MRET']['Brier']:.6f}|{r['realized']['positive_AUC']:.6f}|{r['realized']['ge1_AUC']:.6f}|{r['conditional']['concordance']:.6f}|{improved}/8|")
    lines+=['','|Block|mP MRET AUC|q3 control AUC|Delta|','|---|---:|---:|---:|']
    for b in range(1,9):
        a=scores['mP']['blocks'][str(b)]['AUC'];c=scores[best]['blocks'][str(b)]['AUC'];lines.append(f'|{b}|{a:.6f}|{c:.6f}|{a-c:+.6f}|')
    lines+=['','Top enrichmentと全score decileはMRET_PRIMARY_RESULT.jsonに保存。','',
      '## E. Session Bootstrap','',
      'seed5701105 / 1999 resamples / OOF38 session clusters / PCG64 / 2.5–97.5 linear CI。best q3を全resampleで固定。session multiplicityを行・pairへ適用。pairや19 rolling windowsを独立標本とは呼ばない。','',
      '|Delta mP − q3|Valid N|95% CI|','|---|---:|---|']
    for k,r in boot['deltas'].items():lines.append(f"|{k}|{r['valid_N']}|[{r['CI95'][0]:+.6f}, {r['CI95'][1]:+.6f}]|")
    lines+=['','realized>0 AUC delta CIは0を跨ぐ。MRET-targetとpotential-conditional orderingのpoint改善から、Frozen EXIT全体の実現利益識別やCapital成功までを主張しない。','',
      '## F. Potential-bucket conditional realized ordering','',
      '|Score|Bucket×block concordance|Valid pairs|Same-session×bucket concordance|Valid pairs|','|---|---:|---:|---:|---:|']
    for s,r in scores.items():lines.append(f"|{s}|{r['conditional']['concordance']:.6f}|{r['conditional']['valid_pairs']}|{r['same_session_conditional']['concordance']:.6f}|{r['same_session_conditional']['valid_pairs']}|")
    lines+=['','realizedが異なるunique unordered pairのみ。score tie credit0.5。aggregateはvalid pair weighted、bootstrap unit=session。pair countは独立sample Nではない。','',
      '## G. I2 funded/admission realized diagnostics','',
      '|Subset|N|Score|>0 AUC|>=1 AUC|<=0 AUC|Spearman|','|---|---:|---|---:|---:|---:|---:|']
    for group,z in diag.items():
        for s,r in z['scores'].items():lines.append(f"|{group}|{z['N']}|{s}|{r['positive_AUC']:.6f}|{r['ge1_AUC']:.6f}|{r['loser_AUC']:.6f}|{r['Spearman']:.6f}|")
    lines+=['','<=0 AUCはraw scoreの方向を反転せず表示。Secondary diagnosticsでありMRET teacherと別target。','',
      '## H. Signal Gate / Independent Audit','',
      '|Condition|Result|','|---|---|']
    for k,v in gate['gate'].items():lines.append(f"|{k}|{'PASS' if v else 'FAIL'}|")
    lines+=['',f"Independent signal audit: {audit['checks']:,} checks、mismatch={audit['mismatch_N']}、最大float差={audit['float_max_abs_difference']:.17g}、固定許容1e-12。Trainer/evaluator imports0、optimizer refit0。coef/intercept NPZ snapshot exact。OOF score/metrics/bootstrap比較は許容内だが、numeric scale index5（selector/first_clock）の比較1件が許容を超えた。audit check名にblock番号は保存されていない。",'',
      'Primaryはfrozen MovementのNumPy population std、Independentはmath.fsumによる中心偏差和を使った。reductionの丸め差であっても、固定contractを緩和しない。失敗したR8 receiptは書き換えない。再監査・refit・再評価0。','',
      '## I. Closure / certification blocker','',
      'monetizationSignal=MRET_NO_GOはS9を含む固定Gateの結果。**統計条件は8/8 PASSであり、情報不足が統計的に確定したという結論ではない。** status=V11_CONTRACT_FAILをcontrolling resultとする。NEXT_BOTTLENECK=REALIZED_MONETIZATION_INFORMATION_GAPはprecommitted not-STRONG taxonomyをそのまま保持し、実務上のblockerは独立preprocessing numeric認証。次の独立Workでcontractを整理するまではsignal/capital adoption不可。EXIT bottleneckとは命名しない。','',
      'R10 runtime percentile、R11 65-canary、R12 cap audit、M1/M2 Main claim/replay、Capital full auditはSTRONG条件を満たさず未実行。Capital metricやquality-retention PASSを捏造しない。control replay0、M1=0、M2=0、orders0、main merge0、force push0、provider0、Claude0。Safety10全false。','',
      '```text','selectedBigWinnerRank = EXISTING_MOVE_P5','selectedAuxiliaryHeads = ["MOVE_U2","MOVE_U3"]',f'selectionPolicy = {I2}','monetizationSignal = MRET_NO_GO','status = V11_CONTRACT_FAIL','selectedCapitalCandidate = null','diagnosticArm = I2 saved reference (Capital not executed)','NEXT_BOTTLENECK = REALIZED_MONETIZATION_INFORMATION_GAP','newFits = 8','CapitalReplays = 0','fresh_OOS_claim = false','productionReady = false','CURRENT_STATE = CAPITAL_V11_R10_SIGNAL_NO_GO_CLOSURE_FIXED_STOP','```','']
    report=OUT/'REPORT_FINAL-ja.md'
    with report.open('x') as f:f.write('\n'.join(lines))
    pack=ROOT.parent/'Ark_Capital_v11_Realized_Monetization_Signal_20261005_PRIVATE_CONTRACT_FAIL.zip'
    files=[(PACK,'authority/'+PACK.name)]+[(p,'private/'+str(p.relative_to(PRIVATE))) for p in sorted(PRIVATE.rglob('*')) if p.is_file()]
    manifest={'schema':'CAPITAL_V11_PRIVATE_DELIVERY_V1','exact_jst':now(),'branch':BRANCH,'GitHub_basis':read(WORK/'latest_basis.json'),'v10_parent_SHA':PARENT_SHA,'v10_private_sha256':PACK_SHA,'status':gate['status'],'monetizationSignal':gate['monetizationSignal'],'newFits':8,'CapitalReplays':0,'independent_mismatch_N':audit['mismatch_N'],'NEXT_BOTTLENECK':gate['NEXT_BOTTLENECK'],'bottleneck_interpretation':'contract blocked, not certified statistical information gap','new_repository_backed_code_and_reports_included':False,'immutable_parent_archives_may_include_historical_snapshots':True,'files':[{'path':name,'sha256':sha(p),'bytes':p.stat().st_size} for p,name in files],'fresh_OOS_claim':False,'Safety':SAFETY}
    with zipfile.ZipFile(pack,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('MANIFEST.json',json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
        for p,name in files:z.write(p,name)
    with zipfile.ZipFile(pack) as z:
        for rec in manifest['files']:assert hashlib.sha256(z.read(rec['path'])).hexdigest()==rec['sha256']
    save(OUT/'PRIVATE_PACK_MANIFEST.json',{'exact_jst':now(),'private_file':pack.name,'private_sha256':sha(pack),'bytes':pack.stat().st_size,'manifest_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False).encode()+b'\n').hexdigest(),'files':manifest['files'],'status':gate['status'],'newFits':8,'CapitalReplays':0,'new_code_reports_included':False,'Safety':SAFETY})
    endtime=now();closure={'exact_jst':endtime,'CURRENT_STATE':'CAPITAL_V11_R10_SIGNAL_NO_GO_CLOSURE_FIXED_STOP','status':gate['status'],'monetizationSignal':gate['monetizationSignal'],'NEXT_BOTTLENECK':gate['NEXT_BOTTLENECK'],'bottleneck_interpretation':manifest['bottleneck_interpretation'],'selectedCapitalCandidate':None,'diagnosticArm':'I2_SAVED_REFERENCE','selectedBigWinnerRank':'EXISTING_MOVE_P5','selectedAuxiliaryHeads':['MOVE_U2','MOVE_U3'],'selectionPolicy':I2,'newFits':8,'CapitalReplays':0,'independent_mismatch_N':audit['mismatch_N'],'counts':counts(),'closed':True,'fixed_stop':True,'same_cycle_retry_allowed':False,'additional_research_allowed':False,'adoption':False,'v10_parent_SHA':PARENT_SHA,'private_sha256':sha(pack),'report_sha256':sha(report),'fresh_OOS_claim':False,'productionReady':False,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','Safety':SAFETY}
    save(OUT/'CLOSURE.json',closure)
    save(OUT/'NEXT_WORK_HANDOFF.json',closure|{'same_cycle_next_action':'STOP','next_independent_action':'Resolve exact preprocessing numeric certificate before interpreting signal. No current-cycle refit, eval/audit retry, tolerance relaxation or Capital replay.','permanent_freeze':['Selector','Entry','EXIT'],'no_automatic_next_work':True})
    checkpoint('R10_SIGNAL_NO_GO_CLOSURE_FIXED_STOP',closure,'STOP; static GET/hash/private-delivery receipts only')
    print(json.dumps({'status':closure['status'],'CURRENT_STATE':closure['CURRENT_STATE'],'newFits':8,'CapitalReplays':0,'private_file':str(pack),'private_sha256':sha(pack),'bytes':pack.stat().st_size}))
if __name__=='__main__':{'decision':decision,'finish':finish}[sys.argv[1]]()
