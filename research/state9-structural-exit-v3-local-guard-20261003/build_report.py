"""Human review report from saved audited tables. No decision, fitting or policy variants."""
import collections
from settings import HERE,V2,PRIVATE,SAFETY,BUDGET,load,rows,now,save

def num(x,d=4):return '—' if x is None else f'{x:,.{d}f}'
def pair(g,version,metric,d=4):
    s=g[version]['metrics'][metric];return num(s['mean'],d)+' / '+num(s['median'],d)
def delta(g,metric,d=4):
    s=g['paired_delta'][metric];return num(s['mean'],d)+' / '+num(s['median'],d)
def table(headers,records):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in records])+'\n'

def quality_table(g):
    names=[('realized return %','realized_return_pct'),('MFE Realization %','MFE_realization_pct'),('pre-sell observed peak giveback pp','pre_sell_observed_peak_giveback_pp'),('full-session observed Peak Giveback pp','peak_giveback_pp'),('later missed upside %','later_missed_upside_pct'),('holding active minutes','holding_active_minutes'),('EXIT→later High active minutes','exit_to_later_high_active_minutes')]
    return table(['metric','v2 N','v2 平均 / 中央値','v3 N','v3 平均 / 中央値','共通N','paired Δ 平均 / 中央値'],[
        [label,g['v2']['metrics'][m]['N'],pair(g,'v2',m),g['v3']['metrics'][m]['N'],pair(g,'v3',m),g['paired_delta'][m]['N'],delta(g,m)] for label,m in names])

def main():
    primary=load(HERE/'EXCLUSIVE_ENTRY_HIGH_PRIMARY.json')
    g5=load(HERE/'WINNER_GE5_PROTECTION.json')[0];c=load(HERE/'EXIT_C_PAIRED_DIAGNOSIS.json')[0]
    c5=load(HERE/'WINNER_GE5_EXIT_C.json')[0];cx=load(HERE/'EXIT_C_EXCLUSIVE.json');allg=load(HERE/'ALL_ENTRY_ECONOMICS.json')[0]
    mech=load(HERE/'LOCAL_GUARD_MECHANICS.json');audit=load(HERE/'INDEPENDENT_AUDIT.json')
    assert audit['mismatch_N']==audit['future_causal_leakage_N']==0
    old=list(rows(V2/'ECONOMICS_ROWS.jsonl.gz'))
    counts=audit['check_counts']
    gates=[
        (1,'Frozen Entry identity',['Frozen_Entry_exact_bytes','Entry_immutable_fill']),
        (2,'v2 Full trace exact hash reuse',['full_trace_exact_reuse']),
        (3,'no State9/Path reconstruction',['no_engine_model_provider_import','budget_exact']),
        (4,'local pivot exact source bytes/fields',['local_pivot_exact_original_field','pivot_exact_bytes_reused']),
        (5,'pivot confirmed_at causality',['source_local_pivot_causality']),
        (6,'L0/H0/L1 ordering',['LHL_confirmation_order']),
        (7,'same segment',['C_same_segment','decision_metadata_exact']),
        (8,'confirmed_at<t',['LHL_confirmed_before_t']),
        (9,'higher-low condition',['guard_higher_low_and_progress']),
        (10,'H0+delta progress',['guard_higher_low_and_progress']),
        (11,'guard effective next bar',['guard_next_bar_not_current','C_effective_next_bar']),
        (12,'guard monotonicity',['guard_monotonicity']),
        (13,'no cross-segment carry',['no_cross_segment_carry']),
        (14,'EXIT-C exact break arithmetic',['C_requires_UP_and_exact_break']),
        (15,'EXIT-C requires context still UP',['C_requires_UP_and_exact_break']),
        (16,'A/B/C precedence',['first_valid_A_B_C_precedence']),
        (17,'first valid intent only',['first_valid_A_B_C_precedence','post_exit_decision_zero']),
        (18,'canonical next-open sell5bps',['canonical_next_open_5bps_session_close']),
        (19,'v2 saved-result join identity',['saved_v2_join_exact_identity']),
        (20,'exclusive High denominators',['exclusive_and_subgroup_denominators']),
        (21,'paired return delta',['paired_delta_N','paired_delta_mean','paired_delta_median']),
        (22,'giveback/missed upside',['independent_pre_sell_observed_peak_giveback_pp','independent_peak_giveback_pp','independent_later_missed_upside_pct']),
        (23,'post-exit decision0',['post_exit_decision_zero']),
        (24,'model/teacher/search0',['no_model_fit_predict_call','budget_exact']),
        (25,'Re-entry/Capital0',['budget_exact']),
    ]
    save(HERE/'AUDIT_GATE_MAP.json',{'saved_at_jst':now(),'status':audit['status'],'mismatch_N':0,'future_causal_leakage_N':0,'audit_fit':0,'items':[{'item':n,'requirement':label,'status':'PASS','evidence':'INDEPENDENT_AUDIT.json','check_counts':{k:counts[k] for k in checks}} for n,label,checks in gates],'availability_assumption':audit['availability_assumption'],'safety':SAFETY})
    s=['# Ark Terminal — State9 Structural EXIT v3 Local Guard\n',
       '**STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_READY — Evidence完成、ここでSTOP。**\n',
       '## Primary — Frozen exclusive Entry→High\n']
    s.append(table(['Entry→High exclusive','N','約定 / unresolved（両v同数）','v2 return % 平均 / 中央値','v3 return % 平均 / 中央値','Δmean pp','Δmedian pp'],[
        [g['group'],g['denominator_N'],f"{g['v3']['sell_filled_N']} / {g['v3']['unresolved_N']}",pair(g,'v2','realized_return_pct'),pair(g,'v3','realized_return_pct'),num(g['group_difference']['realized_return_pct']['mean']),num(g['group_difference']['realized_return_pct']['median'])] for g in primary]))
    s.append('PrimaryのΔmean/Δmedianは **v3群平均/中央値−v2群平均/中央値**。Entryごとのpaired差分の中央値とは異なる。'
        '全paired Δとmetric-specific Nは[EXCLUSIVE_ENTRY_HIGH_PRIMARY.json](EXCLUSIVE_ENTRY_HIGH_PRIMARY.json) / '
        '[CSV](EXCLUSIVE_ENTRY_HIGH_PRIMARY.csv)に保存。Unknown5件を含むbucket合計1,600で、Entryやopportunityを再選別していない。\n')
    s.append('3–<4%群は平均+0.0988pp、中央値+0.1217pp改善した。ただし変わったのはC2件で、'
        'そのpaired return改善平均は+6.3213pp。群全体への一般化を証明した結果ではない。'
        '4–<5%群は平均−0.0061pp、中央値変化0で、C3件のpaired return平均は−0.1639pp。'
        '狙った3–5%群の改善は一様ではなかった。\n')
    s.append('≥5%全253件は平均return3.9014→3.9283%で微増、中央値3.2909→3.1755%で低下。'
        'holding中央値87→85 active minutes、MFE Realization中央値33.3483→32.8053%。'
        '平均を保ちつつ中央値と取り逃しに悪化があり、v2 HOLD能力を全面維持したとは判定しない。'
        '自動PASS thresholdは置かず、v2維持 / v3採用 / 次の最小修正は人間判断へ渡す。\n')
    s.append('Document: `WORK_STATE9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_FASTTRACK_20261003`。作成: '+now()+
        '。開始actual GETはv2 FINAL `823fe3a7203e58fbc20fa73acab1d77e1da62c8e` と一致。'
        'Frozen Entry1,600変更0、v2 Full trace/Path exact reuse。v3 position Replayのみ1回、'
        'v2 Replay / Entry refit / State9・Path reconstructionは0。\n')
    s.append('## ≥5% Winner protection — 全253件\n')
    s.append(quality_table(g5))
    s.append(table(['指標','v2','v3'],[
        ['sell-filled / unresolved','253 / 0','253 / 0'],
        ['EXIT-before-final-observed-High rate %',num(g5['v2']['EXIT_before_final_High_rate_pct']),num(g5['v3']['EXIT_before_final_High_rate_pct'])],
        ['EXIT-C N','—',17],
    ]))
    s.append('≥5%群のpre-sell givebackは平均3.8026→3.7011pp（平均改善、中央値は2.3193→2.3641pp）。'
        'Full-session Givebackは平均7.2477→7.2208pp。later missed upsideは観測Nが161→163へ増えるため、'
        '単純群平均の+0.0865ppと共通161 Entryのpaired平均+0.1466ppを区別する。'
        'EXIT-before-final-High率は44.2688→46.2451%へ増えた。\n')
    s.append('## EXIT-C専用 — 43件\n')
    s.append(quality_table(c))
    s.append(table(['指標','N','平均 / 中央値'],[
        ['v2 intent/planned closeより早い active minutes',43,f"{num(c['intent_advance_vs_v2_active_minutes']['mean'])} / {num(c['intent_advance_vs_v2_active_minutes']['median'])}"],
        ['v2 sell fillより早い active minutes',43,f"{num(c['sell_advance_vs_v2_active_minutes']['mean'])} / {num(c['sell_advance_vs_v2_active_minutes']['median'])}"],
        ['paired return Δ pp',43,delta(c,'realized_return_pct')],
        ['paired pre-sell giveback Δ pp',43,delta(c,'pre_sell_observed_peak_giveback_pp')],
        ['paired later missed upside Δ pp',29,delta(c,'later_missed_upside_pct')],
    ]))
    s.append(table(['v2保存済みならintent理由','C N'],sorted(mech['EXIT_C_v2_saved_intent_reason_N'].items())))
    s.append('C43件はmain context=UPのまま、effective guard>main protected、Close<=guard−0.5Uを満たした。'
        'break時Primaryは43件ともPULLBACKだが、Primary文字列をSELL条件には使っていない。'
        '1,557件のnon-Cではv2保存済みintent・fillと全件同一。'
        'Cはv2より早いintentを持つが、Cが必ず利益を保証するわけではない。C群v3 return中央値は+0.1151%、negative19件。\n')
    s.append('C群のpre-sell giveback paired平均−1.6120ppは「売るまでに返した利益」の減少。'
        '一方、later High共通観測29件のmissed upside paired平均は+0.5878pp。'
        '単純later-missed群平均3.0767→2.9391%だけを見ると改善に見えるが、分母は29→43件で異なる。'
        '売却後に伸びた幅を減ったgivebackへ混ぜていない。\n')
    s.append(table(['exclusive bucket','C N','paired return Δ pp 平均 / 中央値','pre-sell giveback paired Δmean pp','missed upside 共通N','missed upside paired Δmean pp'],[
        [g['group'],g['denominator_N'],delta(g,'realized_return_pct'),num(g['paired_delta']['pre_sell_observed_peak_giveback_pp']['mean']),g['paired_delta']['later_missed_upside_pct']['N'],num(g['paired_delta']['later_missed_upside_pct']['mean'])] for g in cx]))
    s.append('## ≥5% WinnerのEXIT-C subgroup — 17件\n')
    s.append(quality_table(c5))
    s.append(table(['指標','v2','v3 / paired'],[
        ['return group中央値 %',num(c5['v2']['metrics']['realized_return_pct']['median']),num(c5['v3']['metrics']['realized_return_pct']['median'])],
        ['paired return Δ mean / median pp','—',delta(c5,'realized_return_pct')],
        ['intent advance active minutes 平均 / 中央値','—',f"{num(c5['intent_advance_vs_v2_active_minutes']['mean'])} / {num(c5['intent_advance_vs_v2_active_minutes']['median'])}"],
        ['EXIT-before-final-High rate %',num(c5['v2']['EXIT_before_final_High_rate_pct']),num(c5['v3']['EXIT_before_final_High_rate_pct'])],
    ]))
    s.append('この17件のreturn平均5.1314→5.5330%、中央値4.9934→4.2781%。'
        'paired return平均+0.4016pp / 中央値0で、群中央値差−0.7153ppとは別の値。'
        'pre-sell giveback paired平均−1.4919ppに対して、later High共通15件のmissed upside paired平均+1.5733pp。'
        'C後later Highの価格・時刻・active minutesはprivate `EXIT_C_ROWS.jsonl.gz` の全17個別行に保存。\n')
    s.append('## Local Guard mechanics\n')
    keys=[('Entry後local pivot observed','local_pivot_observed_after_Entry_N'),('既知prefix local pivot','prefix_local_pivot_observed_N'),('LHL eligible unique suffix','LHL_eligible_unique_sequence_N'),('higher-low unique suffix','LHL_higher_low_unique_sequence_N'),('guard creation events','local_guard_creation_N'),('guard tighten events','local_guard_tighten_N'),('unique positions with guard','unique_positions_with_guard_N'),('guard never established','guard_never_established_N'),('guard reset with level','guard_reset_with_level_N'),('guard break','guard_break_N')]
    s.append(table(['Mechanic','N'],[(label,mech[key]) for label,key in keys]))
    s.append(table(['metric','N','平均 / 中央値'],[
        [label,mech[key]['N'],num(mech[key]['mean'])+' / '+num(mech[key]['median'])]
        for label,key in [('guard−main distance at activation U','guard_to_main_distance_u_at_activation'),('guard age since creation at break bars','guard_age_since_creation_bars_at_break'),('guard age since last update at break bars','guard_age_since_last_update_bars_at_break')]]))
    s.append(table(['break preceding3 distinct Primary','N'],sorted(mech['break_preceding3_distinct_Primary_N'].items())))
    s.append('Guard成立245 position（15.3125%）、C43 position（2.6875%）。Guard未成立1,355件。'
        'LHL eligibleはsame-segment・previous-bar suffixのunique組、higher-low適格組を別count。'
        'creation291はreset/re-arm後の再成立を含み、unique positions245と異なる。'
        '現在足のconfirmationは判定後にappendし、guardはt+1有効。guardを下げず、gap/reset/null時に持ち越さない。'
        '既知same-segmentのEntry/arm前pivotはinput-historyとして利用し、Entry時guardはunset。'
        '同時A/Bがあればv2理由を優先し、予定closing clockと同足のCへ付け替えない。\n')
    s.append('## All-entry economics\n')
    s.append(quality_table(allg))
    s.append(table(['指標','v2','v3'],[
        ['Entry / filled / unresolved','1600 / 1561 / 39','1600 / 1561 / 39'],
        ['positive rate %',num(allg['v2']['positive_rate_pct']),num(allg['v3']['positive_rate_pct'])],
        ['negative N',allg['v2']['negative_N'],allg['v3']['negative_N']],
        ['negative return mean / median %',num(allg['v2']['negative_return']['mean'])+' / '+num(allg['v2']['negative_return']['median']),num(allg['v3']['negative_return']['mean'])+' / '+num(allg['v3']['negative_return']['median'])],
        ['worst return %',num(allg['v2']['worst_return_pct']),num(allg['v3']['worst_return_pct'])],
        ['<−1% N / <−2% N (診断のみ)',str(allg['v2']['below_minus1_N'])+' / '+str(allg['v2']['below_minus2_N']),str(allg['v3']['below_minus1_N'])+' / '+str(allg['v3']['below_minus2_N'])],
    ]))
    s.append('v3 reasons: EXIT-A294、EXIT-B155、EXIT-C43、SESSION_CLOSE1069、UNRESOLVED39。'
        'Entry +5bps二重計上0、sell adverse5bps、commission0。Closing source欠落39件は既存のままUNRESOLVED、last-observed Close補完0。'
        'Entry→arm timestampは全1,600件でv2と一致し、PREで新しいSELLやEntry再filterを追加していない。\n')
    s.append('## Exact reuse / audit / limitations\n')
    s.append('v2 saved ZIP SHA: `31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89`。'
        '1,606 components、Full trace1,600本 / 523,200 scheduled endpoints、Frozen Entry原本gzip、v2 saved outcomes全てhash一致。'
        '6 Frozen pins一致、v2 base lifecycle byte SHA=`6cf642d3d8d7b00422245d1308d3b07cbf507b7fbd9859e61aba596c0b5bcdb5`。'
        'State9/Path semantic変更0、Full reconstruction0、v2 Replay0、Frozen Entry opportunity evaluator rerun0。\n')
    s.append(f"別logic全件監査: **{audit['check_N']:,} checks、mismatch=0、future causal leakage=0、lineage mismatch=0**。"
        'Primaryのguard/base/fill/evaluatorをimportせず、Boolean latch、segment内pivot ledger、Fraction arithmetic、calendar/fill/economicsを別実装。'
        '共通依存は保存済みimmutable trace/raw/opportunity、Python runtime、I/O/hashのみ。外部reviewer監査を称していない。'
        'Historical actual_known_atはUNKNOWN、因果検算はv2と同じbar_end availability仮定内に限る。\n')
    s.append(table(['Audit No.','要求','結果'],[(n,label,'PASS') for n,label,_ in gates]))
    s.append('Full-session source completenessはv2からread-onlyで引き継ぎ、complete55/1600、observed High既知1595、UNKNOWN5。'
        '≥5%群のcompleteは7/253。observed Highに到達したWinnerであり、欠測部分を含むcomplete-session opportunityへ読み替えない。'
        '未観測later Highのnullは0に変えず、missed upsideのpaired共通Nを必ず併記した。\n')
    s.append('初回public source保存で末尾空行を落としたローカルcopyを、取得済みGitの完全なtext bytesから修正し、'
        '19 public source/result filesをmanifest hashへ一致させてからS0を固定した。Frozen objects自体の変更0。'
        '監査table selectorのSESSION_CLOSE intent=None参照を修正し、全件監査を完了した。'
        'S0 contract/decision codeは結果後も変更0、primary Replay再実行0、追加candidate0。'
        '[AUDIT_VALIDATOR_CORRECTION.json](AUDIT_VALIDATOR_CORRECTION.json)参照。\n')
    s.append('## 必須17回答 / STOP\n')
    answers=[
        ('v2 Full trace再構築なしexact reuse','はい。Full trace1,600本のexact hash照合。State9/Path reconstruction0。'),
        ('State9/Path semantics変更','0。Frozen6 pins、main A/B/PRE/quality byte identity。'),
        ('LOCAL_GUARD成立','245 unique positions、creation291、tighten78。'),
        ('EXIT-C発火','43件。全件context=UP、exact guard break。'),
        ('v2より中央値何分早い','intent・fillとも26 active minutes（N43）。>=5 C群は14分（N17）。'),
        ('exclusive各bucket v2→v3 return差','Primary表に全6群+UNKNOWNを保存。Δmean pp: +0.0049,+0.0637,+0.0217,+0.0988,−0.0061,+0.0270。'),
        ('3–<4%改善','平均+0.0988pp、群中央値+0.1217pp。C2件の効果。'),
        ('4–<5%改善','平均−0.0061pp、中央値変化0。C3件の平均delta−0.1639pp。'),
        ('>=5% return維持/改善か','平均3.9014→3.9283%は微増、中央値3.2909→3.1755%は低下。holding87→85分。全面維持とは判定しない。'),
        ('>=5% C件数・paired損益','17件。return5.1314/4.9934→5.5330/4.2781%、pairedΔmean+0.4016pp / median0。'),
        ('pre-sell giveback変化','全体paired平均−0.0450pp、C43件−1.6120pp、>=5 C17件−1.4919pp。'),
        ('later missed upside変化','共通knownで全体+0.0360pp（N473）、C+0.5878pp（N29）、>=5 C+1.5733pp（N15）。'),
        ('PULLBACK/RISE_STOP単独SELL','0。C全件の独立structural条件を検算。State文字列/stop count/dwell単独も0。'),
        ('fixed% stop/profit/trailing','全て0。唯一bufferはFrozen0.5Uで、variants0。'),
        ('audit mismatch / future leakage','0 / 0。historical actual_known_at UNKNOWN、bar_end仮定内。'),
        ('Re-entry/Capital','0。Portfolio/orders/main mergeも0。'),
        ('人間判断用Evidence','全10 Completion Gateまで完成。三checkpointのFINALでSTOP。正式採用Freezeへ進まない。'),
    ]
    s.append(table(['No.','必須回答','結果'],[(n,label,answer) for n,(label,answer) in enumerate(answers,1)]))
    s.append('New EXIT policies=1、local guard variants=1。それ以外のfit/teacher/score/rank/OOF/search/provider/new market data/Entry replay/refit/'
        'State/Path reconstruction/v2 Replay/old EXIT Replay/Hard1/fixed stop/trailing/Protected/Fresh/Validation/OOS/Prospective/Re-entry/Capital/Portfolio/orders/main merge/force pushは0。'
        '全10 safety flags=false、LONG-only / cash-equity-only、productionReady=false。\n')
    s.append('Git checkpointsはV3_S0_START_AND_CONTRACT、V3_S1_REPLAY_AND_EVALUATION、V3_FINAL_AUDIT_AND_EVIDENCEのみ。'
        '保存はactual saved_at_jst / actual basis_headを記録し、commit後actual GETでresult HEADを確認。未来SHAを埋め込まない。'
        '個別Evidenceは[PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json](PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json)、保存成功は'
        '[PRIVATE_EVIDENCE_SAVE_RECEIPT.json](PRIVATE_EVIDENCE_SAVE_RECEIPT.json)。**ここでSTOP。**\n')
    (HERE/'REPORT-ja.md').write_text('\n'.join(s));print('17-answer report and 25-item audit map complete.')

if __name__=='__main__':main()
