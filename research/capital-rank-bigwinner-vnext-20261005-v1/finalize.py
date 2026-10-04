"""Publish audited research decision/report. No further candidate evaluation."""
import json
from pathlib import Path
from control import ROOT, OUT, PRIVATE, INPUTS, now, save, sha, checkpoint, SAFETY, COUNTS

def decision():
    r=json.loads((OUT/'STAGE_A_RESULT.json').read_text())
    a=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())
    assert a['mismatch_N']==0 and a['independently_selected_status']=='RANK_VNEXT_STRONG'
    prior=ROOT/'docs/evidence/capital-vnext-v2-movement-20261004-v1'
    prior_model=json.loads((prior/'MODEL_PRECOMMIT.json').read_text())
    prior_fits=json.loads((prior/'ROLLING_ORIGIN_HEAD_FITS.json').read_text())
    contract={'exact_jst':now(),'status':'RANK_VNEXT_STRONG','selectedRankCandidate':'EXISTING_MOVE_P5',
        'authority':'RANK_RESEARCH_CANDIDATE_ONLY','score_field':'pP',
        'score_description':'Saved direct U5 probability output used only for ordering; no new fit or calibration authority',
        'frozen_order':['pP DESC','Frozen Entry timestamp ASC','stable symbol ASC'],
        'score_stream_sha256':sha(INPUTS/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz'),
        'source_evidence':'docs/evidence/capital-vnext-v2-movement-20261004-v1/FIXED_ARMS_SCORE_STREAMS.json',
        'model_sha256':{f'MOVE_P_BLOCK_{b:02d}.json':prior_fits['model_hashes'][f'MOVE_P_BLOCK_{b:02d}.json'] for b in range(1,9)},
        'numeric_matrix_order':prior_model['numeric_matrix_order']['MOVE_P'],
        'categorical_matrix_order':prior_model['categorical_matrix_order'],
        'parameters':prior_model['parameters'],'preprocessing':prior_model['preprocessing'],
        'feature_manifest_sha256':sha(prior/'FEATURE_MANIFEST.json'),
        'original_8_temporal_models_reused':True,'new_fits':0,'MOVE_P10_fits':0,'dual_generated_N':0,
        'new_rank_bands_or_admission_thresholds':0,'future_U10_feature':0,'current_ML_baseline_changed':0,
        'gates':{k:r['gates'][k] for k in ['A','B','C','D']},
        'E':{'leakage_N':0,'asof_violation_N':0,'identity_mismatch_N':0,'independent_audit_mismatch_N':0},
        'independent_audit_sha256':sha(OUT/'INDEPENDENT_AUDIT.json'),
        'mask_manifest_sha256':sha(OUT/'COMMON_EVAL_MASK_FREEZE.json'),
        'bootstrap_U5_delta_CI95':r['bootstrap']['delta_candidate_minus_current']['U5_AUC']['CI95'],
        'permanent_freeze':['Selector','Entry','EXIT'],
        'capital_value':'NOT_EVALUATED_THIS_WORK','rolling20_calculation_N':0,'final38_equity_calculation_N':0,
        'promotion_or_runtime_update':False,'fresh_OOS_claim':False,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE',
        'Safety':SAFETY,'counts':COUNTS}
    save(OUT/'SELECTED_RANK_CONTRACT.json',contract)
    save(OUT/'RANK_DECISION.json',{'exact_jst':now(),'status':contract['status'],
        'selectedRankCandidate':contract['selectedRankCandidate'],'contract_sha256':sha(OUT/'SELECTED_RANK_CONTRACT.json'),
        'fit_N':0,'capital_replay_N':0,'stage_B':'SKIPPED_CLEAR_STAGE_A_WINNER',
        'reason':'All A/B/C/D/E pass;6/8 U5 blocks improved; session-cluster U5 ROC-AUC delta CI lower>0',
        'next_policy':'STOP; next separate Work may evaluate Frozen Rank Allocation for MAX3, with permanent Selector/Entry/EXIT freeze'})
    checkpoint('R10_RANK_DECISION','RANK_VNEXT_STRONG_EXISTING_MOVE_P5_FIXED_STOP',
        ['Audited saved MOVE_P5 direct pP ranking fixed as Research Candidate','Optional MOVE_P10/dual skipped,0 new fits',
         'Current legacy and supported controls preserved'],
        {'status':'RANK_VNEXT_STRONG','selectedRankCandidate':'EXISTING_MOVE_P5','independent_mismatch_N':0,'new_fits':0,'replays':0},
        'Write REPORT-ja/capture curves/handoff and final closure; do not enter Allocation/Capital work')

def report_close():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    r=json.loads((OUT/'STAGE_A_RESULT.json').read_text())
    a=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())
    contract=json.loads((OUT/'SELECTED_RANK_CONTRACT.json').read_text())
    prior=json.loads((OUT/'PRIOR_WORK_MATRIX.json').read_text())['matrix']
    support=json.loads((OUT/'TEACHER_CONTRACT_AUDIT.json').read_text())
    mask=json.loads((OUT/'COMMON_EVAL_MASK_FREEZE.json').read_text())
    c=r['rank_metrics']['CURRENT_V4_ML'];m=r['rank_metrics']['EXISTING_MOVE_P5'];l=r['LEGACY_CURRENT']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.hashsalt':'ark-rank-vnext-20261005'})
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    for ax,head,title in zip(axes,['U5_capture','U10_capture'],['U5: at least 5% future upside','U10: at least 10% future upside']):
        for metric,label,color in [(c,'Current V4 ML','#64748b'),(m,'Existing MOVE P5 (pP)','#2563eb')]:
            curve=metric['capture_curve'];ax.plot([100*p['K']/metric['N'] for p in curve],[100*p[head] for p in curve],label=label,color=color,lw=2)
            p=metric['top']['20'];ax.scatter([100*p['K']/metric['N']],[100*p[head]],color=color,s=35,zorder=3)
        ax.plot([0,100],[0,100],color='#cbd5e1',linestyle='--',lw=1,label='Random ranking')
        ax.set(xlim=(0,100),ylim=(0,100),xlabel='Selected top fraction (%)',ylabel='Winner capture (%)',title=title)
        ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
    axes[0].legend(loc='lower right',fontsize=9)
    fig.suptitle('Frozen Rank tournament | supported common OOF',fontsize=15,y=.98)
    fig.text(.5,.01,'N = 1,028 | 38 sessions | repeated Development research | fit 0 | Capital replay 0',ha='center',fontsize=10,color='#475569')
    fig.tight_layout(rect=[0,.04,1,.95])
    fig.savefig(OUT/'CAPTURE_CURVES.svg',metadata={'Date':None})
    fig.savefig(OUT/'CAPTURE_CURVES.png',dpi=180,metadata={'Description':'Exact frozen supported-common Rank capture metrics; no Capital projection'})
    plt.close(fig)
    def pct(v):return f'{100*v:.4f}%'
    def auc(v):return f'{v:.10f}'
    report=['| Rank | U5 AUC | U5 PR-AUC | U10 AUC | U10 PR-AUC | Top20 U5 | Top20 U10 | Top20 <2 | Status |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for name,v,status in [('LEGACY_CURRENT (N=1039)',l,'原値固定'),('SUPPORTED_ONLY_CURRENT (N=1028)',c,'Control保持'),('EXISTING_MOVE_P5 / pP (N=1028)',m,'RANK_VNEXT_STRONG')]:
        top=v['top']['20'];report.append(f'| {name} | {auc(v["U5_AUC"])} | {auc(v["U5_PR_AUC"])} | {auc(v["U10_AUC"])} | {auc(v["U10_PR_AUC"])} | {pct(top["U5_density"])} | {pct(top["U10_density"])} | {pct(top["below2_contamination"])} | {status} |')
    report+=['| PRR_HEAD5 | — | — | — | — | — | — | — | NOT_COMPARABLE |','| PRR_HEAD10 | — | — | — | — | — | — | — | NOT_COMPARABLE |','',
        '最終statusは **RANK_VNEXT_STRONG**。`selectedRankCandidate = EXISTING_MOVE_P5`。保存済みU5モデルの`pP`順をRank Research Candidateとして固定した。新fit **0/8**、Capital / Control / MAX3 replay **0**。Stage BのMOVE_P10とBIGWIN_DUAL_RANKは生成していない。','',
        f'作成: {now()}。既存58 Development sessionsの20 warmup /38 OOFを再利用したITERATIVE_DEVELOPMENT_EVIDENCEであり、fresh/OOSの成功は主張しない。Selector / Entry / EXITは永久Freeze、変更0。','',
        '同一identity・同一teacher・同一maskで比較した。Current1039件のlegacy値は完全再現した。Primaryはpre15:20の1,028件（U5=170件、U10=67件）。全pre-cutoff候補1,578件のうち550件はwarmupで、score未保存のためOOF比較対象ではない。旧ML<1、C、Liquidity rejectは除いていない。','',
        'A1は保存済み`pP`（直接U5 score）を使う。既存MovementのP-AUCが使ったfieldに対応する。以前のCapital score `pP/baseP`や既存Top20 enrichmentの並びを、この比較へ置き換えていない。pPは順位付け専用で、確率校正・Capital sizing・admission・新rank-bandの権限は与えない。','',
        'U5/U10の全point gate、low-upside guard、6/8 block改善、catastrophic block failure 0、integrity gateを通過した。block1/2のU5は小幅悪化を維持し、結果救済を行っていない。','',
        '| Block | N | Current U5 AUC | MOVE U5 AUC | ΔU5 | Current U10 AUC | MOVE U10 AUC |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for b in r['blocks']:
        report.append(f'| {b["block"]} | {b["CURRENT_V4_ML"]["N"]} | {b["CURRENT_V4_ML"]["U5_AUC"]:.6f} | {b["EXISTING_MOVE_P5"]["U5_AUC"]:.6f} | {b["delta_U5_AUC"]:+.6f} | {b["CURRENT_V4_ML"]["U10_AUC"]:.6f} | {b["EXISTING_MOVE_P5"]["U10_AUC"]:.6f} |')
    report+=['','catastrophicの事前定義: U5またはU10のblock AUCがCurrent>=0.5からcandidate<0.5へ落ち、delta<=−0.10。定義はR4で固定した。','',
        '| Session-cluster bootstrap delta (MOVE−Current) | Point | 95% CI | Positive replicates |',
        '|---|---:|---|---:|']
    for metric,value in r['bootstrap']['delta_candidate_minus_current'].items():
        lo,hi=value['CI95'];report.append(f'| {metric} | {m[metric]-c[metric]:+.6f} | [{lo:+.6f}, {hi:+.6f}] | {pct(value["positive_replicate_fraction"])} |')
    report+=['','38 session単位のpaired bootstrap、seed=5701005、1999/1999 valid。U5 AUC CI下限>0で指定のSTRONG条件を満たす。U10のCIは0を跨ぐため、U10の改善はpoint比較として報告する。これは新しい独立データでの検証ではない。','',
        '| Rank | Top fraction / K | U5 density | U10 density | <2 contamination | U5 capture | U10 capture | NDCG |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for name,v in [('Current',c),('MOVE P5',m)]:
        for f in ['10','20','30']:
            t=v['top'][f];report.append(f'| {name} | {f}% / {t["K"]} | {pct(t["U5_density"])} | {pct(t["U10_density"])} | {pct(t["below2_contamination"])} | {pct(t["U5_capture"])} | {pct(t["U10_capture"])} | {v["NDCG"][f]:.6f} |')
    report+=['','Top K=ceil(fraction×N)。NDCGはordinal gain=0,1,3,7,15、discount=1/log2(rank+1)。診断指標であり、winner priorityの変更には使っていない。','',
        '![U5 and U10 capture curves](CAPTURE_CURVES.svg)','',
        '| Ordinal bucket | Population N | Current Top20 density | MOVE Top20 density | Current mean rank percentile | MOVE mean rank percentile |',
        '|---|---:|---:|---:|---:|---:|']
    for bc,bm in zip(c['ordinal_buckets'],m['ordinal_buckets']):
        o=str(bc['ordinal']);report.append(f'| {bc["bucket"]} | {bc["N"]} | {pct(c["top"]["20"]["ordinal_bucket_N"][o]/c["top"]["20"]["K"])} | {pct(m["top"]["20"]["ordinal_bucket_N"][o]/m["top"]["20"]["K"])} | {bc["mean_rank_percentile"]:.6f} | {bm["mean_rank_percentile"]:.6f} |')
    report+=['','両scoreの平均rank percentileは >=10 > 5–<10 > 3–<5 > 2–<3 > <2。個々の候補が完全にこの順序へ分離するという意味ではない。','',
        '| Rank | Session Top K | Selected N | U5 density | U10 density |',
        '|---|---:|---:|---:|---:|']
    for name,v in [('Current',c),('MOVE P5',m)]:
        for k in ['3','5']:
            t=v['session_top3_top5'][k];report.append(f'| {name} | {k} | {t["selected_N"]} | {pct(t["U5_density"])} | {pct(t["U10_density"])} |')
    report+=['','Session top3/top5は全日候補を順位付けしたdiagnostic only。時刻順のMAX3競合、cash/lot、Allocation、Capital returnは評価していない。','',
        '| Teacher support | U5 | U10 |', '|---|---:|---:|']
    for status in support['support_statuses']:
        report.append(f'| OOF1039: {status} | {support["support_counts"]["OOF1039_U5"][status]} | {support["support_counts"]["OOF1039_U10"][status]} |')
    report+=['','Strictly-later actual Highのない54件は全てcomplete capture・terminal pagination・Entry sourceを持つ。32件のpre-cutoffは原本契約のempty-future complete-capture規則でKNOWN_NEGATIVE_COMPLETE_CAPTURE、22件のcutoff以降はNOT_MATUREとしてPrimaryから除いた。OOF内の該当29件は18件の確認済みnegativeを保持し、11件を除外した。UNKNOWN→0補完0、teacher上書き0。','',
        'Entry boundaryはFrozen fill timestampのまま。first intentより遅いEntryは608件あるが、Rankを過去のfirst intentへbackdateしていない。Core bar_end<=Entry、Movement source minute<Entry、prior session<Entry sessionを監査した。historical actual arrivalはUNKNOWNのままで、継承済みbar_end availability仮定のもとでの因果監査である。live as-of実証は行っていない。','',
        'PRR canonical 1614件のうちCurrent1028件とsession/symbol/minuteだけが一致する候補は260件（90件は複数arm row）。しかしteacher分母がeffective Entry、今回はraw Entryであり、policy/fold lineageも異なる。両headは全Current候補についてNOT_COMPARABLE。無理なjoin・target変換・PRR再fit0。既存POTENTIAL_SKILL_FAILを維持する。','',
        '| Calibration diagnostic (associated U5 head only) | Brier | Logloss |', '|---|---:|---:|',
        f'| Current saved p5 | {c["calibration"]["U5_Brier"]:.8f} | {c["calibration"]["U5_logloss"]:.8f} |',
        f'| MOVE saved pP | {m["calibration"]["U5_Brier"]:.8f} | {m["calibration"]["U5_logloss"]:.8f} |','',
        'MLは確率ではないためML自体にBrier/loglossを当てていない。U10学習headは作っていないためU10 Brier/loglossはnull。CalibrationをRank選定Primaryへ使っていない。','',
        '| Prior work | Existing Evidence | This Work policy |','|---|---|---|']
    for p in prior:report.append(f'| {p["prior_work"]} | {p["existing_result"]} | {p["reuse_or_prohibition"]}; fit/replay0 |')
    report+=['','| Lineage | SHA256 |','|---|---|']
    for label,value in [('Current frozen score',mask['current_saved_score_sha256']),('MOVE frozen score',contract['score_stream_sha256']),('Frozen teacher',mask['teacher_sha256']),('Common mask',mask['mask_sha256']),('Ordered common identity',mask['ordered_identity_sha256']),('Feature manifest',contract['feature_manifest_sha256']),('Selected Rank contract',sha(OUT/'SELECTED_RANK_CONTRACT.json')),('Independent audit',sha(OUT/'INDEPENDENT_AUDIT.json'))]:
        report.append(f'| {label} | `{value}` |')
    for name,digest in contract['model_sha256'].items():report.append(f'| {name} | `{digest}` |')
    report+=['',f'別経路Fraction/scalar audit: **{a["checks_N"]:,} checks、mismatch 0**。Primary evaluatorをimportせず、identity、known/unknown、OOF、保存score hash、順序/tie、ROC/AP、Top10/20/30、contamination、NDCG、capture curve、block、bootstrap input/CI、statusを再計算した。float tolerance=1e−12、count/order/identity tolerance=0。train-percentile/dualはStage B未実行のためNOT_APPLICABLE。','',
        '共有されたFrozen source・fitted artifacts・RNG APIのI/O依存は残る。独立計算一致は外部source真実性やproduction certificationの保証ではない。','',
        '| Budget / Safety | Result |','|---|---|',
        '| Existing MOVE_P5 fits | 8 historical artifacts reused; refit 0 |',
        '| New fits / MOVE_P10 / search / retune | 0 / 0 / 0 / 0 |',
        '| Capital / Control / MAX3 / MAX4–5 replay | 0 / 0 / 0 / 0 |',
        '| Selector / Entry / EXIT changes | 0 / 0 / 0 |',
        '| Provider / Claude / protected / fresh / holdout / validation / OOS / prospective open | all 0 |',
        '| Orders / main merge / force push | 0 / 0 / 0 |',
        '| executionAllowed / brokerWriteAllowed / excelOrderWriteAllowed / rssOrderFunctionAllowed | all false |',
        '| liveTradingAllowed / paperTradingAllowed / automaticPromotionAllowed / productionUpdateAllowed / transmitted / productionReady | all false |','',
        '次Workテーマは「Frozen Rank vNextを使い、MAX3で大Winnerを落とさないAllocation」。その別Workで初めてcurrent/later candidate、slot opportunity cost、U5/U10 preservation、MAX3 conflict、rolling20を評価する。ここで固定したpP順・feature/model/split/teacherとSelector / Entry / EXITは変更しない。Rankからadmission/slot reserveの閾値は新設していない。次Workはlatest GET、既存Evidence監査、Allocation policyのprecommitから開始する。','',
        'このWorkのNorth Starは維持したが、100万円→20 sessionsや38-session Final Equityを新candidateで計算していない。','',
        '**Rankだけ固定した。Allocator/Capitalの価値はまだ未評価**','']
    with (OUT/'REPORT-ja.md').open('x',encoding='utf-8') as f:f.write('\n'.join(report))
    save(OUT/'NEXT_WORK_HANDOFF.json',{'exact_jst':now(),'topic':'Frozen Rank vNextを使い、MAX3で大Winnerを落とさないAllocation',
        'selectedRankCandidate':'EXISTING_MOVE_P5','ordering_field':'pP','rank_contract_sha256':sha(OUT/'SELECTED_RANK_CONTRACT.json'),
        'rank_new_fit_or_retune':0,'permanent_freeze':['Selector','Entry','EXIT'],
        'next_work_only':['current vs later candidate','slot opportunity cost','U5/U10 preservation','MAX3 conflict','rolling20'],
        'this_work_capital_value':'NOT_EVALUATED','current_work_state':'RANK_VNEXT_STRONG_CLOSED_FIXED_STOP','Safety':SAFETY})
    save(OUT/'CLOSURE.json',{'exact_jst':now(),'status':'RANK_VNEXT_STRONG','current_state':'RANK_VNEXT_STRONG_CLOSED_FIXED_STOP',
        'selectedRankCandidate':'EXISTING_MOVE_P5','report_sha256':sha(OUT/'REPORT-ja.md'),
        'rank_contract_sha256':sha(OUT/'SELECTED_RANK_CONTRACT.json'),'independent_mismatch_N':0,
        'completed_checkpoints':['R0','R1','R2','R3','R4','R5','R9','R10','R11'],'optional_skipped':['R6','R7','R8'],
        'counts':COUNTS,'Safety':SAFETY,'productionReady':False,'fresh_OOS_claim':False,
        'next_policy':'STOP. No additional models/weights/bands/retuning or Capital/Allocation work in same cycle',
        'report_final_sentence':'Rankだけ固定した。Allocator/Capitalの価値はまだ未評価',
        'actual_result_HEAD_tree':'Recorded in postcommit actual GET receipts; no future SHA guessed'})
    checkpoint('R11_CLOSURE_HANDOFF','RANK_VNEXT_STRONG_CLOSED_FIXED_STOP',
        ['REPORT-ja, capture curves, frozen score lineage and handoff complete','Stage A winner fixed with new fits0; no Allocation/Capital evaluation'],
        {'status':'RANK_VNEXT_STRONG','selectedRankCandidate':'EXISTING_MOVE_P5','report_sha256':sha(OUT/'REPORT-ja.md'),
         'independent_checks':a['checks_N'],'mismatch_N':0,'new_fits':0,'Capital_replay':0},
        'STOP. Preserve append-only Evidence. Next distinct Work is Frozen Rank Allocation for MAX3')
    print(json.dumps({'status':'RANK_VNEXT_STRONG','report':str(OUT/'REPORT-ja.md'),'curves':str(OUT/'CAPTURE_CURVES.png'),'fits':0,'replays':0}))

if __name__=='__main__':
    import sys
    {'decision':decision,'report_close':report_close}[sys.argv[1]]()
