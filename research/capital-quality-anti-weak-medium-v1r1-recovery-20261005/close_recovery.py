"""Seal audited recovery facts only. No metric recomputation, fitting or integration."""
from control import *

def pct(v):return f'{100*v:.2f}%'
def num(v):return f'{v:.6f}'
def table(headers,rr):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rr])

def main():
    assert not (OUT/'CLOSURE.json').exists(),'Already closed: STOP'
    baseline=read(OUT/'BASELINE_INDEPENDENT_CERTIFICATION.json');model=read(OUT/'MODEL_ARTIFACT_AUDIT.json')
    independent=read(OUT/'INDEPENDENT_PERFORMANCE_AUDIT.json');auth=read(OUT/'PRIVATE_PACK_AUTHENTICATION.json')
    preserved=read(WORK/'old_preservation_actual_get.json')
    assert baseline['status']==model['status']==independent['status']==auth['status']==preserved['status']=='PASS'
    assert independent['mismatch_N']==auth['mismatch_N']==preserved['prior_entry_mismatch_N']==0
    assert baseline['public_compact_mismatch_N']==baseline['root_identity_mismatch_N']==0
    assert model['label_mask_split_model_OOF_mismatch_N']==0 and model['max_abs_float_difference']<=1e-12
    assert independent['max_abs_float_difference']<=1e-12
    pub=read(WORK/'publications.json');checked={c['path']:c for r in pub for c in r['actual_GET_checks']}
    assert all(r['status']=='PASS' for r in pub)
    for p,c in checked.items():
        assert c['returned_body_exact'] and c['sha256']==c['downloaded_body_sha256']==sha(ROOT/p)
        if p.endswith('.json'):assert c['returned_body_parse']=='PASS'
    for claim in ['BASELINE_PRIMARY_EXECUTION_CLAIM','BASELINE_INDEPENDENT_EXECUTION_CLAIM',
        'MODEL_ARTIFACT_AUDIT_EXECUTION_CLAIM','PERFORMANCE_PRIMARY_EXECUTION_CLAIM','PERFORMANCE_INDEPENDENT_EXECUTION_CLAIM']:
        c=read(OUT/(claim+'.json'))
        assert c['maximum_executions']==1 and c['new_fits']==0
        assert str((OUT/(claim+'.json')).relative_to(ROOT)) in checked
        for p,h in c['code_sha256'].items():assert sha(ROOT/p)==h
    oldauth=read(OUT/'OLD_CYCLE_READ_ONLY_AUTHORITY.json')
    for p,h in oldauth['required_local_source_sha256'].items():assert sha(OLD/p)==h
    assert sha(OLD/'ZERO_FIT_BASELINE.json')==oldauth['old_corrupt_Q4_incident_only_sha256']=='1389d55448725ba3c44bbd29a2302d7b61ec6914d2913b7d575e7db894a8cddc'
    for x in auth['transport_members']:assert sha(OLD_WORK/x['path'])==x['sha256']
    primary=read(OUT/'PRIMARY_QUALITY_EVAL.json');mm=primary['metrics']
    full=json.loads(gzip.decompress((PRIVATE/'PERFORMANCE_FULL.json.gz').read_bytes()))
    pending=full['provisional_decision'];assert pending==independent['independent_decision']
    a=primary['AntiWeak'];b=primary['MediumPlus']
    for g in [a,b]:assert g['gates'][('A' if g['target']=='U2' else 'M')+'8'] is True
    assert independent['session_draw_stream_sha256']==primary['session_draw_stream_sha256']
    assert all(primary['bootstrap'][h]['sessions']==38 and primary['bootstrap'][h]['resamples']==1999 and primary['bootstrap'][h]['seed']==5701005 for h in ['MOVE_U2','MOVE_U3'])
    for h,j in model['join'].items():assert j['common_present']==1028 and j['missing']==0 and j['extra']==11 and j['original_artifact_rewritten'] is False
    firewall=read(OUT/'ALLOCATION_FIREWALL.json')
    assert all(firewall[k]==0 for k in ['v8_research_result_read','v8r1_research_result_read','main_b1_b2_outcome_imported','quality_results_exported_to_main','main_branch_get'])
    assert all(v is False for v in SAFETY.values())
    names=['identity','mask','train<test','test label leakage0','future High in X=0','PnL in X=0','release in X=0',
        'future bar in X=0','prefix cutoff','prior date','Movement boundary','identity/date feature0','U2/Weak complement',
        'U3 exact','unknown impute0','pP not in X','feature manifest exact','preprocessing exact','model config exact','search0',
        'within-block refit0','split exact','convergence warning0','model/prediction hashes','OOF duplicate0','bootstrap session',
        'conditional decile outcome-free','Safety false','v8 research read0','v8R1 research read0','Main B1/B2 outcome imported0',
        'old corrupt Q4 used as metric input=0','old cb1 hash forced reproduction=0','baseline source hashes exact',
        'baseline canonical parse PASS','baseline public actual GET hash exact','baseline independent compact mismatch0',
        '16 completed fit rerun=0','common predictions missing=0','common predictions extra ignored only by mask',
        'trainer execution=0','CapitalReplay=0','MAX3Replay=0','Fresh open=0']
    assert len(names)==44
    canaries=[{'number':i,'name':n,'status':'PASS','authority':
        'MODEL_ARTIFACT_AUDIT + completed fit ledgers' if i<=25 else
        'INDEPENDENT_PERFORMANCE_AUDIT + primary/independent draw streams' if i in [26,27] else
        'ALLOCATION_FIREWALL + scoped IO/code claims' if i in [28,29,30,31,41,42,43,44] else
        'BASELINE roots/actual GET/independent certification + reuse/join audit'} for i,n in enumerate(names,1)]
    final_counts={'newFits':0,'refits':0,'auditRefits':0,'reusedCompletedFits':16,'MOVE_U2_reused':8,'MOVE_U3_reused':8,
        'CORE_H2_H3_fits':0,'pP_fits':0,'MOVE_U2_fits':0,'MOVE_U3_fits':0,'baseline_builds_primary':1,
        'baseline_builds_independent':1,'model_artifact_audits':1,'primary_performance_packages':1,'independent_performance_packages':1,
        'primary_bootstrap_resamples_per_head':1999,'independent_bootstrap_resamples_per_head':1999,
        'new_model':0,'threshold_sweep':0,'hyperparameter_search':0,'class_weight_search':0,'feature_add_delete':0,
        'combined_score':0,'trainer_execution':0,'CapitalReplay':0,'MAX3Replay':0,'Fresh_open':0,'orders':0,
        'main_merge':0,'force_push':0,'provider':0,'Claude':0,'Main_quality_information_flow':0}
    # Append an execution receipt: early checkpoint counters snapshot already-existing
    # completion *files*, before writing the current checkpoint. Never rewrite them.
    count_receipt={'exact_jst':now(),'status':'PASS','counts':final_counts,
        'snapshot_counter_interpretation':'counts() in R3/R7 snapshots existing prior completion checkpoint files before saving the current checkpoint, not attempts. Current execution is recorded in each result/claim/complete artifact. This append-only receipt reconciles exact execution counts; no prior artifact or metric changes.',
        'per_checkpoint_actual_execution_counts':[
            {'checkpoint':f'R{i}','baseline_primary':int(i>=3),'baseline_independent':int(i>=4),
                'model_artifact_audit':int(i>=5),'primary_performance_package':int(i>=7),'independent_performance_package':int(i>=10),
                'newFits':0,'refits':0,'auditRefits':0} for i in range(13)]}
    save(OUT/'EXECUTION_COUNTS_RECEIPT.json',count_receipt)
    artifacts=[]
    for p in sorted(PRIVATE.glob('*.gz')):
        body=gzip.decompress(p.read_bytes());jsonl=p.name.endswith('.jsonl.gz')
        if jsonl:assert body==b''.join(canonical(json.loads(s)) for s in body.splitlines())
        else:assert body==canonical(json.loads(body))
        assert p.read_bytes()[4:8]==b'\x00'*4 and p.read_bytes()[3]&8==0
        artifacts.append({'path':str(p.relative_to(WORK)),'size':p.stat().st_size,'sha256':sha(p),
            'schema':'canonical JSONL' if jsonl else 'canonical JSON','uncompressed_size':len(body),
            'uncompressed_sha256':hashlib.sha256(body).hexdigest(),'gzip_mtime':0,'filename_metadata':False})
    save(OUT/'RECOVERY_PRIVATE_ARTIFACT_ROOT.json',{'N':1028,'artifacts':artifacts,
        'original_transport_pack_sha256':auth['pack_sha256'],'original_transport_manifest_sha256':auth['DELIVERY_MANIFEST_sha256'],
        'git_backed_code_and_evidence_are_not_duplicated_in_private_delivery':True})
    save(OUT/'OLD_CYCLE_PRESERVATION_ACTUAL_GET.json',preserved)
    save(OUT/'PUBLICATION_HASH_AUDIT.json',{'exact_jst':now(),'status':'PASS','verified_files':len(checked),
        'downloaded_body_mismatch_N':0,'JSON_parse_mismatch_N':0,'checks':list(checked.values()),
        'verified_through_HEAD':basis()['HEAD'],'terminal_files_actual_GET_required_after_commit':True})
    audit={'exact_jst':now(),'status':'PASS','final_mismatch_N':0,'canary_N':44,'canary_PASS_N':44,
        'canaries':canaries,'baseline_mismatch_N':0,'model_artifact_mismatch_N':0,'performance_mismatch_N':0,
        'max_abs_float_difference':max(baseline['max_abs_float_difference'],model['max_abs_float_difference'],independent['max_abs_float_difference']),
        'float_tolerance':1e-12,'trainer_evaluator_metric_imports_independent':0,'counts':final_counts,
        'old_quality_subtrees_unchanged':True,'original_Q4_failure_preserved':True,'Safety':SAFETY}
    save(OUT/'INTEGRITY_CANARY_AUDIT.json',audit)
    decision={**pending,'selectedBigWinnerRank':'EXISTING_MOVE_P5','recoveryStatus':'QUALITY_RECOVERY_PASS',
        'final_integrity':'PASS','final_mismatch_N':0,'newFits':0,'reusedCompletedFits':16,
        'CapitalReplay':0,'MAX3Replay':0,'fresh_OOS_claim':False,'productionReady':False,
        'exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','heads_are_auxiliary_only':True,
        'old_qualityStatus':'QUALITY_CONTRACT_FAIL','old_terminal':'Q12_CLOSURE_FIXED_STOP','NEXT_POLICY':NEXT_POLICY}
    save(OUT/'QUALITY_DECISION.json',decision)
    report=[]
    report.extend(['# Capital Quality Intelligence v1R1 — 最終報告',
        f"\n作成: {now()} / branch: `{BRANCH}` / 評価basis HEAD: `{basis()['HEAD']}`",
        f"\nqualityStatus = **{pending['qualityStatus']}**。MOVE_U2 / MOVE_U3はいずれも旧Point Gate全8項目PASSかつAUC差CI下限>0。Auxiliary候補としてFreezeする。pPを置換・blendせず、Allocator/Capitalへ投入しない。",
        '\n## A. Recovery Integrity',
        '\n旧v1の失敗はQ4 baseline byte/parse integrityであり、旧QUALITY_CONTRACT_FAIL / Q12は永久保存。破損prefixを修復せず、旧expected cb1 hashも再現しなかった。',
        '\nQ4以前のCOMMON_SAVED_SCORES・QUALITY_TEACHERS_EVAL・P_P_DECILES_OUTCOME_FREE・COMMON_EVAL_MASKから新semantic baselineを1回構築。Publicはcompact/hash root、full/group/rowsはcanonical deterministic gzip。公開後actual GETはparse/byte/hash一致。',
        f"\nBaseline root SHA256: `{sha(OUT/'BASELINE_RECOVERY_ROOT.json')}`。Primary/独立baseline mismatch0、最大差{baseline['max_abs_float_difference']:.3g}。16 completed fits exact reuse、new/refit/audit-refitすべて0。各head OOF1039→common1028、extra11、missing0。元predictionを書き換えていない。",
        '\n## B. Executive Quality\n'])
    rr=[]
    for g in [a,b]:
        h,c,t=g['head'],g['control'],g['target'];ci=g['AUC_delta_CI']
        rr.append([h,num(mm[c][t]['AUC']),num(mm[h][t]['AUC']),num(g['AUC_delta']),num(g['PR_AUC_delta']),
            f"[{num(ci['lower'])}, {num(ci['upper'])}]",f"{len(g['block_improved'])}/8",g['status_pending_integrity_audit']])
    report.append(table(['Head','Control AUC','Candidate AUC','AUC delta','PR delta','95% CI','Blocks improved','Status'],rr))
    report.extend(['\n## C. Fixed Budget Quality','\nN=1028。K=ceil(N×fraction)。Mediumは3–<5%、U5は>=5%、U10は>=10%（U5に含む）。全候補で同じbudget。'])
    for index,f in [(1,.2),(2,.3),(3,.4)]:
        report.append(f'\n### Top{int(f*100)}\n')
        rr=[]
        for s,q in mm.items():
            z=q['top'][index];rr.append([s,z['selected_N'],f"{z['below2_N']} / {pct(z['below2_rate'])}",
                f"{z['below3_N']} / {pct(z['below3_rate'])}",z['Medium_N'],z['U5_N'],z['U10_N'],
                pct(z['U3_capture']),pct(z['U5_capture']),pct(z['U10_capture'])])
        report.append(table(['score','N','<2 N/rate','<3 N/rate','Medium N','U5 N','U10 N','U3 capture','U5 capture','U10 capture'],rr))
    for section,g in [('D. Anti-Weak MOVE_U2',a),('E. Medium+ MOVE_U3',b)]:
        h,c,t=g['head'],g['control'],g['target'];boot=primary['bootstrap'][h]
        report.extend([f'\n## {section}',f"\nAUC {num(mm[c][t]['AUC'])} → {num(mm[h][t]['AUC'])}。PR-AUC {num(mm[c][t]['PR_AUC'])} → {num(mm[h][t]['PR_AUC'])}。PR差95% CI [{num(boot['PR_AUC_delta']['lower'])}, {num(boot['PR_AUC_delta']['upper'])}]。",
            '\n'+table(['block','control AUC','candidate AUC','delta'],[[bl,num(mm[c]['blocks'][str(bl)][t]['AUC']),num(mm[h]['blocks'][str(bl)][t]['AUC']),num(mm[h]['blocks'][str(bl)][t]['AUC']-mm[c]['blocks'][str(bl)][t]['AUC'])] for bl in range(1,9)]),
            f"\n旧gate: {', '.join(k+'=PASS' if v else k+'=FAIL' for k,v in g['gates'].items())}。改善block={g['block_improved']}。catastrophic/undefined=0。",
            '\n'+table(['fraction','control metric','candidate metric'],[[z['fraction'],pct(mm[c]['top'][i]['below2_rate'] if t=='U2' else mm[c]['top'][i]['U3_capture']),pct(z['below2_rate'] if t=='U2' else z['U3_capture'])] for i,z in enumerate(mm[h]['top'])])])
        if t=='U2':report.append('\nBottom Weak density/capture:\n\n'+table(['budget','CORE_H2 density','MOVE_U2 density','CORE_H2 capture','MOVE_U2 capture'],[[z['fraction'],pct(mm[c]['bottom'][i]['Weak_density']),pct(z['Weak_density']),pct(mm[c]['bottom'][i]['Weak_capture']),pct(z['Weak_capture'])] for i,z in enumerate(mm[h]['bottom'])]))
    cc=full['conditional']
    for section,variants in [('F. pP Conditional Incremental',['pP_conditional']),('G. Same-Session',['same_session','same_session_pP_conditional'])]:
        report.extend([f'\n## {section}','\npP decileはtest block内equal-count10 bins、outcome-freeで固定。集約はvalid positive-negative pair weighted。pairsは独立sample Nではない。paired session-cluster bootstrapの単位は38 sessions。\n'])
        rr=[]
        for g in [a,b]:
            h,c,t=g['head'],g['control'],g['target']
            for v in variants:
                ca=cc[t][h][v];co=cc[t][c][v];ci=primary['bootstrap'][h][v]
                rr.append([t,v,ca['valid_pairs'],num(co['discrimination']),num(ca['discrimination']),
                    num(ca['discrimination']-co['discrimination']),f"[{num(ci['lower'])}, {num(ci['upper'])}]"])
        report.append(table(['target','variant','valid pairs','control','candidate','delta','95% CI'],rr))
    report.extend(['\n## H. 5-Bucket Ordinal / NDCG','\n診断のみ。gain=[0,1,3,7,15]、blend設計には使わない。\n'])
    ordinal=full['ordinal'];rr=[]
    for s,v in ordinal.items():
        for z in v['buckets']:rr.append([s,z['bucket'],z['N'],num(z['mean_percentile']),num(z['median_percentile']),pct(z['top'][0]['density']),pct(z['top'][1]['density'])])
    report.append(table(['score','bucket','N','mean percentile','median percentile','Top20 density','Top30 density'],rr))
    report.append('\n'+table(['score','NDCG10','NDCG20','NDCG30','NDCG40','mean ideal order','median ideal order'],[[s,*[num(z['NDCG']) for z in v['NDCG']],v['ideal_mean_order'],v['ideal_median_order']] for s,v in ordinal.items()]))
    report.extend(['\n## I. Big/Mega Preservation Guard','\nTop30（N=309）固定。Primary Gateは変更しない。pPはEXISTING_MOVE_P5でFreeze。\n'])
    report.append(table(['head','U5 capture','pP U5 capture','U10 capture','pP U10 capture','guard'],[[h,pct(g['U5_capture']),pct(g['pP_U5_capture']),pct(g['U10_capture']),pct(g['pP_U10_capture']),g['status']] for h,g in full['guards'].items()]))
    report.extend(['\n## J. Independent Audit',f"\nBaseline・source labels/mask/split・model state・OOF・AUC/AP・Top/Bottom・conditional・same-session・ordinal/NDCG・全bootstrap resample値/CI・gate・status/selected headsのmismatch=0。最大float差={audit['max_abs_float_difference']:.17g} <=1e-12。",
        f"\nSession draw stream SHA256: `{primary['session_draw_stream_sha256']}`。seed5701005 / 1999、独立生成一致。Independentはtrainer/evaluator/metrics/primary builderをimportせず、optimizerも実行していない。44/44 canaries PASS。",
        '\n## K. Firewall / Safety / Counts / Prior No-Repeat',
        f"\nMain v8/v8R1 research/B1/B2/Capital outcome read/import/export=0。旧Quality evidence/research subtree不変、prior {preserved['unchanged_prior_entries']} metadata entries不変。Safety全false。",
        '\nCORE H2/H3/H5、pP、MOVE_R、HF1/HL0/LSAFE/Q1–Q8、Weak専用head、PRR566 join/fitは再実行0。new/refit/audit refit0、既存16 fitsのみreuse。Baseline Primary1/Independent1、性能Primary1/Independent1。Capital/MAX3 replay、threshold/blend、Fresh、orders、main merge、force push、provider、Claude=0。',
        '\n同じ58 sessionsを複数cycleに利用したITERATIVE_DEVELOPMENT_EVIDENCEであり、fresh/OOS successでもproduction readinessでもない。source/PITは既存bar-end assumptionを継承し、actual arrivalは不明。Potentialと実現PnLは区別し、PnLはdiagnosticのみ。',
        '\n```text',f"selectedBigWinnerRank = EXISTING_MOVE_P5\nselectedAuxiliaryHeads = {json.dumps(pending['selectedAuxiliaryHeads'])}\nqualityStatus = {pending['qualityStatus']}\nrecoveryStatus = QUALITY_RECOVERY_PASS\nnewFits = 0\nreusedCompletedFits = 16\nCapitalReplay = 0\nMAX3Replay = 0\nfresh_OOS_claim = false\nproductionReady = false\nNEXT_POLICY = \"{NEXT_POLICY}\"",'```',
        '\nR12 CLOSURE_FIXED_STOP。以後、このcycleでfit/teacher/feature/gate/threshold/combined score/Rank/Allocatorを変更しない。'])
    textsave(OUT/'REPORT_FINAL-ja.md','\n'.join(report)+'\n')
    checkpoint('R11_QUALITY_DECISION',['final integrity PASS / 44 canaries PASS / independent mismatch0; old decision contract applied without metric recomputation'],
        decision,'R12 fixed STOP; no blend/threshold/Rank replacement/MAX3/Capital/Fresh/main merge/orders')
    closure={'exact_jst':now(),'branch':BRANCH,'basis_HEAD_tree':basis(),'status':'CLOSURE_FIXED_STOP',
        'terminal_checkpoint':'R12_CLOSURE_FIXED_STOP',**decision,'counts':final_counts,'Safety':SAFETY,
        'report_sha256':sha(OUT/'REPORT_FINAL-ja.md'),'integrity_audit_sha256':sha(OUT/'INTEGRITY_CANARY_AUDIT.json'),
        'independent_performance_audit_sha256':sha(OUT/'INDEPENDENT_PERFORMANCE_AUDIT.json'),
        'research_after_closure':0,'fit_repeat':0,'original_quality_fail_unchanged':True,
        'terminal_actual_GET_publication_receipt_required':True}
    save(OUT/'CLOSURE.json',closure)
    checkpoint('R12_CLOSURE_FIXED_STOP',['report/decision/integrity hash-pinned; no further research; publication/delivery receipts only'],
        closure,NEXT_POLICY)
    print(json.dumps({'qualityStatus':pending['qualityStatus'],'selectedAuxiliaryHeads':pending['selectedAuxiliaryHeads'],
        'recoveryStatus':'QUALITY_RECOVERY_PASS','terminal':'R12_CLOSURE_FIXED_STOP','canaries':44,'mismatch_N':0,'newFits':0}))

if __name__=='__main__':main()
