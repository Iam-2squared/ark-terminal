"""Append-only terminal contract failure; never rescues scores, fits or gates."""
from control import *

NEXT_POLICY='Wait until independent Main Allocation Work is closed; integrate only in a new precommitted cycle.'

def main():
    audit=read(OUT/'INDEPENDENT_AUDIT.json');fit=read(OUT/'FITS_COMPLETE.json')
    assert audit['final_mismatch_N']==1 and audit['qualityStatus']=='QUALITY_CONTRACT_FAIL'
    assert counts()['total_fits']==16 and not (OUT/'PRIMARY_QUALITY_EVAL.json').exists()
    assert not (OUT/'P_P_CONDITIONAL_INCREMENTAL.json').exists() and not (OUT/'BIG_WINNER_PRESERVATION.json').exists()
    event={'exact_jst':now(),'event':'BASELINE_INTEGRITY_FAILURE','qualityStatus':'QUALITY_CONTRACT_FAIL',
        'baseline_frozen_sha256':read(OUT/'ZERO_FIT_BASELINE_FREEZE.json')['baseline_sha256'],
        'baseline_current_sha256':sha(OUT/'ZERO_FIT_BASELINE.json'),'baseline_current_size':(OUT/'ZERO_FIT_BASELINE.json').stat().st_size,
        'baseline_parse_error':audit['baseline']['parse_error'],'baseline_full_hash_recovery':False,
        'mechanism':'Not established; original artifact is an incomplete JSON prefix. No external cause claimed.',
        'implementation_defect':'Q5 fit claim captured current baseline hash but did not check it against Q4 frozen hash or validate complete JSON.',
        'original_evidence_overwrite':0,'result_rescue':0,'baseline_regeneration_for_acceptance':0,
        'completed_fits':16,'fit_rerun':0,'new_head_quality_performance_results_read':0,
        'independent_audit_probability_reconstruction_only':True,
        'freeze_input_changes':0,'source_hash_mismatch_N':0,'permanent_FREEZE_changes':0,
        'stopped_before':'new-head AUC/PR/TopK/conditional/pairwise/bootstrap/preservation',
        'remediation_for_future_separate_cycle_only':['Validate JSON completeness and Q4 frozen byte hash before Q5 claim',
            'Actual GET and verify artifact body hash after every publication',
            'Use compact summaries and hashed compressed private full artifacts',
            'Reuse completed unique fit artifacts if a future authorized contract permits; do not repeat identical fits'],
        'Safety':SAFETY}
    save(OUT/'BASELINE_INTEGRITY_INCIDENT.json',event)
    blocked=[('Q7_PRIMARY_QUALITY_EVAL','U2/U3 quality metrics and paired bootstrap'),
        ('Q8_P_P_CONDITIONAL_INCREMENTAL','pP-conditional and same-session discrimination'),
        ('Q9_BIG_WINNER_PRESERVATION','Big/Mega preservation diagnostic')]
    for name,scope in blocked:
        checkpoint(name,'BLOCKED_CONTRACT_FAIL',['Evaluation entry hash check failed before new-head quality outcomes were read'],
            {'scope':scope,'performance_evaluation_status':'NOT_RUN_CONTRACT_STOP','baseline_integrity_failure_N':1},'No quality promotion; terminal contract failure only')
    checkpoint('Q10_INDEPENDENT_AUDIT','COMPLETE_AUDIT_FAILED',['Standalone auditor imports trainer/evaluator/metrics0',
        'Raw source labels, mask, split, preprocessing, fitted-state coefficient snapshots and OOF independently checked'],
        {'structural_mismatch_N':0,'max_abs_float_difference':audit['max_abs_float_difference'],
            'baseline_integrity_failure_N':1,'final_mismatch_N':1,'full_quality_metric_audit':'NOT_RUN_CONTRACT_STOP'},'Q11 QUALITY_CONTRACT_FAIL, auxiliary heads empty')
    decision={'exact_jst':now(),'selectedBigWinnerRank':'EXISTING_MOVE_P5','selectedAuxiliaryHeads':[],
        'qualityStatus':'QUALITY_CONTRACT_FAIL','reason':'Q4 frozen baseline byte hash does not match current incomplete baseline; exact recovery failed.',
        'AntiWeak':'NOT_EVALUATED_CONTRACT_STOP','MediumPlus':'NOT_EVALUATED_CONTRACT_STOP',
        'BigMegaGuard':'NOT_EVALUATED_CONTRACT_STOP','A8_integrity':False,'M8_integrity':False,
        'point_pass_claim':False,'statistical_success_claim':False,'mismatch0_claim':False,
        'completed_fits_preserved':16,'fit_repetition_prohibited':True,'CapitalReplay':0,'MAX3Replay':0,
        'fresh_OOS_claim':False,'productionReady':False,'NEXT_POLICY':NEXT_POLICY,'Safety':SAFETY}
    save(OUT/'QUALITY_DECISION.json',decision)
    checkpoint('Q11_QUALITY_DECISION','COMPLETE_CONTRACT_FAIL',['Failure status fixed without retuning or result rescue',
        'Frozen Big-Winner Rank retained; no auxiliary heads selected'],decision,'Q12 CLOSURE_FIXED_STOP')
    report=f'''# Capital Quality Intelligence v1 — Final Report

作成: {now()} / branch: `capital-quality-vnext-20261005`

**QUALITY_CONTRACT_FAIL。Q12で固定停止。**

固定base: `def427ab1b8fdf464e675d0c8f299059902ff028`。
Main Allocationのv8/v8R1研究内容は参照していない。

## A. Executive

| Head | Control | New fits | delta / CI | status |
|---|---|---:|---|---|
| MOVE_U2 | saved CORE_H2 p2 | 8 | 未実施 | CONTRACT_STOP |
| MOVE_U3 | saved CORE_H3 p3 | 8 | 未実施 | CONTRACT_STOP |

16 fitsは各1回で完了、ConvergenceWarningは0。Quality評価の開始時にQ4 baselineのhash不一致とJSON欠損を検出し、成功判定を停止した。Q5 claimがQ4 hashとの一致とJSON完全性を確認していなかったため、不完全なbaselineの現hashをclaimへ固定してしまった。元baselineを完全hashまで復元できず、救済はしていない。

## B. Fixed Budget Quality

共通supported OOF: 1,028件。母集団はWeak<2:596、Low2–<3:135、Medium3–<5:127、Big5–<10:103、Mega>=10:67。
Top20/30/40のselected構成・<2/<3・Medium・U5/U10・captureは**NOT_RUN_CONTRACT_STOP**。母集団件数を選択後の成果と扱わない。

## C. Anti-Weak

MOVE_U2の8 fitsを保存。WeakはU2 complement、別Weak modelは0。
A1–A7の成果判定は未実施、A8 integrityはFAIL。STRONG/PROMISING/有効性の主張は0。

## D. Medium+

MOVE_U3の8 fitsを保存。M1–M7の成果判定は未実施、M8 integrityはFAIL。
realized loser/positive teacher、追加teacher、別C・family・feature・thresholdは0。

## E. pP Conditional Incremental

pPは各supported test blockのoutcome-free equal-count decileへ固定済み。
新headのconditional discriminationとsession bootstrap deltaは未実施。追加情報ありという主張は0。

## F. Same-Session

新headのsame-session pairwise、same-session/decile conditional、bootstrapは未実施。
pairsを独立sample Nとして使用した解析は0。

## G. 5-Bucket Ordinal

上記5 bucketの件数とteacher整合性は監査済み。新headのmean/median percentile、Top20/30 density、NDCGは未実施。結果後blendは0。

## H. Big/Mega Guard

MOVE_U2/U3のTop30 U5/U10 capture診断は未実施。既存pPはそのままFreeze。BIG_WINNER_PRESERVINGという判定は行わない。

## I. Prior No-Repeat

GitHub metadata検索12語は該当0。固定baseの既存head/manifestを確認し、同一Movement U2/U3完成artifactを確認できなかったため最大16 fitsをclaimした。
CORE H2/H3/H5、pP/MOVE_P5、MOVE_R、HF1/HL0、LSAFE/Q1–Q8、PRR566の再fitは0。今回完了した16 fitsも再実行しない。

## J. Firewall / Integrity / Fits / Safety

独立監査はtrainer/evaluator/metrics import0、audit refit0。
labels/mask/split/preprocessing/係数・intercept保存snapshot/OOF再構成mismatch0。
最大float差: `{audit['max_abs_float_difference']}`、許容`1e-12`以下。
係数は独立optimizer再fitではなく、別保存したfitted-stateとの比較で検証した。

**baseline integrity root failure1、final mismatch1。mismatch0の最終監査PASSではない。**
Canary31項目: PASS29、FAIL1(hash)、NOT_RUN1(bootstrap)。全項目PASSという主張はしない。

v8研究read0、v8R1研究read0、Main B1/B2 outcome imported0、Quality途中結果のMainへの差し込み0。
Safetyは全false。orders/main merge/force push/provider/Claude/Capital replay/MAX3 replay/allocator変更/Fresh openはすべて0。

```text
selectedBigWinnerRank = EXISTING_MOVE_P5
selectedAuxiliaryHeads = []
qualityStatus = QUALITY_CONTRACT_FAIL
CapitalReplay = 0
MAX3Replay = 0
fresh_OOS_claim = false
productionReady = false
NEXT_POLICY = "{NEXT_POLICY}"
```

Q12後のfit・model/teacher/gate変更・combined score・threshold・MAX3/Capital・Fresh・main merge・ordersは実行しない。
'''
    with (OUT/'REPORT-ja.md').open('x') as f:f.write(report)
    closure={'exact_jst':now(),'status':'CLOSURE_FIXED_STOP','terminal_checkpoint':'Q12_CLOSURE_FIXED_STOP',
        'qualityStatus':'QUALITY_CONTRACT_FAIL','selectedBigWinnerRank':'EXISTING_MOVE_P5','selectedAuxiliaryHeads':[],
        'fit_counts':counts(),'final_audit_mismatch_N':1,'baseline_exact_byte_recovery':False,
        'research_after_closure':0,'Safety':SAFETY,'fresh_OOS_claim':False,'productionReady':False,
        'NEXT_POLICY':NEXT_POLICY,'report_sha256':sha(OUT/'REPORT-ja.md'),
        'audit_sha256':sha(OUT/'INDEPENDENT_AUDIT.json'),'completed_fit_repeat':0}
    save(OUT/'CLOSURE.json',closure)
    checkpoint('Q12_CLOSURE_FIXED_STOP','CLOSURE_FIXED_STOP',[
        'Quality contract failure and empty auxiliary selection permanently fixed',
        'Final report and independent audit failure preserved append-only',
        '16 completed fits preserved; all research now stopped'],closure,NEXT_POLICY)
    print(json.dumps({'terminal':'Q12_CLOSURE_FIXED_STOP','qualityStatus':'QUALITY_CONTRACT_FAIL','selectedAuxiliaryHeads':[],'fits':16,'mismatch':1}))

if __name__=='__main__':main()
