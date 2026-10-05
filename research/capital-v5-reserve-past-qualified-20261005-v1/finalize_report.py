"""Report the fixed no-Replay branch from retained ledgers; no inference or market path."""
from context import *
from decimal import Decimal
from fractions import Fraction
from collections import Counter
import csv

STATUS='PAST_SUPPORT_NOT_ESTABLISHED'
REASON='All8 PAST_QUALIFIED blocks false; R primary Replay and independent R reconstruction NOT_EXECUTED.'

def private_rows(name):
    with gzip.open(PRIVATE/name,'rt',encoding='utf-8') as f:return [json.loads(s) for s in f]
def f(x):return Fraction(Decimal(str(x)))
def rf(x):return Fraction(x['numerator'],x['denominator'])
def fraction_record(x):return {'numerator':x.numerator,'denominator':x.denominator,'decision_domain':'EXACT_RATIONAL'}
def size(rows):return {'N':len(rows),'sessions':len({r['session'] for r in rows}),'blocks':len({r['block'] for r in rows})}
def pct(x):return '—' if x is None else f'{100*x:.6f}%'
def unavailable(reason=REASON):return {'status':'NOT_EVALUATED','value':None,'reason':reason}

def main():
    q=json.loads((OUT/'PAST_QUALIFICATION_BY_BLOCK.json').read_text());tables=q['tables']
    assert len(tables)==8 and q['PAST_QUALIFIED_block_N']==0
    decision=json.loads((OUT/'EXECUTION_DECISION.json').read_text());assert not decision['candidate_primary_replay_allowed']
    audit=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text());assert audit['status']=='PASS' and audit['mismatch_N']==0
    authority=read('native_authority');v=authority['capital'];quality=authority['quality']
    assert v['status']=='EVALUATED' and len(v['windows'])==19 and len(v['session_ids'])==38
    paired=[]
    for w in v['windows']:
        growth=f(w['window_end_EOD_equity_cell'])/f(w['pre_window_EOD_equity_cell'])
        assert growth==rf(w['growth']) and 1000000*growth==rf(w['amount_from_1m'])
        paired.append({'window_index':w['window_index'],'start_session':w['start_session'],'end_session':w['end_session'],
            'V5':w,'R':{'status':'NOT_EXECUTED','reason':REASON,'growth':None,'amount_from_1m':None,'maxdd':None},
            'R_minus_V5':unavailable(),'comparison':unavailable()})
    save('PAIRED20_EXACT.json',{'schema':'V5_R_PAIRED20_EXACT_V1','status':'R_NOT_EXECUTED','reason':REASON,
        'V5_exact_authority_sha256':sha(INPUT/ROLES['native_authority']),'window_N':19,'R_evaluated_window_N':0,
        'capital_decision_domain':'Decimal source cell -> Fraction -> exact cross-product, no loss tolerance',
        'V5_statistics':v['statistics'],'R_statistics':unavailable(),'better_equal_worse':unavailable(),
        'worst_window_delta':unavailable(),'V5_full_maxdd':v['full_maxdd'],'R_full_maxdd':unavailable(),'windows':paired})
    path=OUT/'PAIRED20_EXACT.csv';assert not path.exists()
    with path.open('w',encoding='utf-8',newline='') as stream:
        fields=['window_index','start_session','end_session','V5_growth_numerator','V5_growth_denominator',
            'V5_amount_decimal_display','V5_MaxDD_numerator','V5_MaxDD_denominator','R_status','R_growth',
            'R_amount','R_MaxDD','R_minus_V5','comparison','reason']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for p in paired:
            w=p['V5'];dd=w['maxdd']['maxdd'];g=w['growth']
            writer.writerow({'window_index':w['window_index'],'start_session':w['start_session'],'end_session':w['end_session'],
                'V5_growth_numerator':g['numerator'],'V5_growth_denominator':g['denominator'],
                'V5_amount_decimal_display':w['amount_from_1m']['decimal_display'],
                'V5_MaxDD_numerator':dd['numerator'],'V5_MaxDD_denominator':dd['denominator'],
                'R_status':'NOT_EXECUTED','reason':REASON})
    # Evaluation-only outcome joins begin after immutable table and execution decision.
    packets={r['entry_id']:r for r in read('packet')};outcomes=read('outcomes');proposals=read('proposals')
    probes=private_rows('SHADOW_NATIVE_SNAPSHOT_PROBES.jsonl.gz');S=private_rows('PAST_PROPOSALS_OUTCOME_BLIND.jsonl.gz')
    probe_byindex={r['snapshot_index']:r for r in probes};stages={};excluded=[];structural=[];empty=[];notempty=[];lower=[]
    def identity(key,reason=None):
        p=packets[key];r={'entry_id':key,'session':p['session'],'block':p['native_block']}
        if reason:r['reason']=reason
        return r
    for index,p in enumerate(proposals):
        reserve=[d for d in p['gate_decisions'] if d.get('slot_gate_reason') in ('SLOT2_RESERVE_FOR_FUTURE_QUALITY','SLOT3_RESERVE_FOR_FUTURE_QUALITY')]
        structural += [identity(d['entry_id'],d['slot_gate_reason']) for d in reserve]
        if not reserve:continue
        if p['picked_ids']:
            notempty += [identity(d['entry_id'],'NATIVE_PICKED_NONEMPTY') for d in reserve]
        else:
            empty += [identity(d['entry_id']) for d in reserve]
            first=probe_byindex[index]['candidate']
            lower += [identity(d['entry_id'],'RAW_PP_NOT_FIRST_NO_BACKFILL') for d in reserve if d['entry_id']!=first]
    first=[identity(r['candidate'],r['reason']) for r in probes]
    passed=[identity(r['candidate']) for r in probes if r['score_pass']]
    failed=[identity(r['candidate'],r['reason']) for r in probes if not r['score_pass']]
    funded=[identity(r['candidate']) for r in probes if r['score_pass'] and r['allocation']['quantity']>=100]
    zeroqty=[identity(r['candidate'],r['allocation']['fundability_reason']) for r in probes if r['score_pass'] and r['allocation']['quantity']==0]
    later=[identity(r['candidate'],'SESSION_PROPOSAL_COLLECTION_ALREADY_ENDED') for r in probes if r['score_pass'] and r['allocation']['quantity']>=100 and r['collection_already_ended']]
    assert len(structural)==181 and len(empty)==167 and len(first)==158 and len(passed)==52 and len(funded)==41 and len(S)==24
    stages={'structural_Reserve_rows':size(structural),'native_picked_empty_rows':size(empty),'raw_pP_first':size(first),
        'score_pass':size(passed),'past_qualified':{'N':0,'sessions':0,'blocks':0},
        'native_qty100_after_qualification':{'N':0,'sessions':0,'blocks':0,'reason':'No qualified blocks'},
        'first_divergence':{'N':None,'sessions':None,'blocks':None,'status':'NOT_EXECUTED','scan_N':0},
        'actual_exception_funded':{'N':0,'sessions':0,'blocks':0,'status':'NOT_EXECUTED','Replay_N':0},
        'complete_R_settlement':{'N':None,'sessions':None,'blocks':None,'status':'NOT_EXECUTED'},
        'diagnostic_score_pass_snapshot_qty100':size(funded),'outcome_blind_first_fundable_S':size(S)}
    def quality_summary(rows):
        known=[];unknown=[];details=[]
        for row in rows:
            key=row['entry_id'];o=outcomes.get(key)
            if not o or o.get('potential_pct') is None or o.get('frozen_realized_net_return_cell') is None:
                unknown.append(key);continue
            potential=f(o['potential_pct']);net=f(o['frozen_realized_net_return_cell'])
            targets={'U5':potential>=5,'U10':potential>=10,'Medium':3<=potential<5,'U3':potential>=3,
                'Weak':potential<2,'below3':potential<3,'realized_nonpositive':net<=0,'realized_positive':net>0}
            known.append((potential,net,targets));details.append(row|{'evaluation_only':True,'potential_pct_exact':fraction_record(potential),
                'standalone_net_return_exact':fraction_record(net),'targets':targets,'actual_R_trade':False})
        return {'population':size(rows),'known_N':len(known),'unknown_N':len(unknown),'unknown_ids':unknown,
            'counts':{t:sum(x[2][t] for x in known) for t in ('U5','U10','Medium','U3','Weak','below3','realized_nonpositive','realized_positive')},
            'mean_standalone_net_return_exact':fraction_record(sum((x[1] for x in known),Fraction(0))/len(known)) if known else None},details
    diagnostics={};detail_rows=[]
    for name,rows in [('structural181',structural),('native_picked_nonempty',notempty),('raw_PP_not_first',lower),
        ('first158',first),('score52',passed),('score_rejected106',failed),('score_pass_qty0',zeroqty),
        ('score_and_snapshot_qty100_41',funded),('later_fundable_not_added_to_S',later),('first_per_session_S24',S)]:
        result,details=quality_summary(rows);diagnostics[name]=result
        detail_rows += [{'diagnostic_cohort':name,**r} for r in details]
    detail_path=gzsave('EVALUATION_ONLY_FILTER_AND_SUPPORT_DETAILS.jsonl.gz',detail_rows)
    allq0=[identity(r['candidate'],r['allocation']['fundability_reason']) for r in probes if r['allocation']['quantity']==0]
    abstain={'native_picked_nonempty':size(notempty),'raw_pP_not_first_no_backfill':size(lower),
        'WINNER_RANK_BELOW_3_4':size([r for r in failed if r['reason']=='WINNER_RANK_BELOW_3_4']),
        'BOTH_QUALITY_LOW':size([r for r in failed if r['reason']=='BOTH_QUALITY_LOW']),
        'score_pass_quantity0':size(zeroqty),'later_fundable_session_collection_closed':size(later),
        'PAST_UNQUALIFIED_score_pass':size(passed),'packet_or_reference_unknown':{'N':0,'sessions':0,'blocks':0},
        'label_unknown_in_required_past_S_F':{'N':0,'sessions':0,'blocks':0}}
    diagnostic_qty0={why:size([r for r in allq0 if r['reason']==why]) for why in sorted({r['reason'] for r in allq0})}
    notrun={'status':'NOT_EXECUTED','N':None,'quantity':None,'PnL':None,'reason':REASON}
    impact={'V5_COMMON':notrun.copy(),'V5_ONLY':notrun.copy(),'R_ONLY':notrun.copy(),
        'lost_native_trade_N_quantity_PnL':unavailable(),'additional_Medium_U5_U10_Weak_realized_PnL':unavailable(),
        'new_later_MAX3_cash_Reserve_misses':unavailable(),'net_Winner_gain_minus_existing_Winner_loss':unavailable(),
        'actual_R_intervention_effect':unavailable('No actual R ledger; standalone label contribution is not unique causal effect.')}
    save('QUALITY_AND_DISPLACEMENT.json',{'schema':'V5_R_QUALITY_DISPLACEMENT_V1','status':'R_NOT_EXECUTED',
        'activity_waterfall':stages,'abstain_reasons':abstain,'diagnostic_quantity0_reasons':diagnostic_qty0,
        'diagnostic_population_quality':diagnostics,'detail_artifact':'private/EVALUATION_ONLY_FILTER_AND_SUPPORT_DETAILS.jsonl.gz',
        'detail_sha256':sha(detail_path),'all_excluded_U5_U10_Medium_rows_reported_in_private_detail':True,
        'actual_R_quality':unavailable(),'impact':impact,'V5_saved_quality_reference':quality,
        'full_S24_not_used_as_block8_support':True,'block8_support_S_N':21,'current_future_block_outcomes_in_qualification':0,
        'standalone_support_not_historical_policy_replay_or_actual_recovered_PnL':True,
        'evaluation_ids_not_used_in_runtime':True,'filter_retargeting_N':0})
    gates={g:{'status':'NOT_EVALUATED','reason':REASON} for g in ('E0','E1','E2','E3','E4','Q1','Q2','Q3','Q4','Q5','Q6','R1')}
    save('FINAL_GATES.json',{'schema':'V5_R_FINAL_GATES_V1','exact_jst':now(),'terminal_status':STATUS,
        'gate_results':gates,'candidate_primary_replay_status':'NOT_EXECUTED','formal_38_complete_R_sessions':None,
        'formal_19_complete_R_windows':None,'North_Star_hit':False,'North_Star_evaluation_status':'NOT_EVALUATED',
        'candidate_improvement_claim':False,'loss_defense_success_claim':False,'research_candidate_proposed':False,
        'pre_main_causal_saved_case_audit':'PASS','independent_pre_main_mismatch_N':0,
        'activeCapitalChampion':'V5','selectedCapitalCandidate':None,'selectedResearchCandidate':None,'championUpdated':False,
        'Safety':SAFETY,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS':False,
        'future_noninferiority_guarantee':False,'future_zero_loss_guarantee':False})
    for kind in ('DECISIONS','TRADES','MTM','EOD'):
        save('NOT_EXECUTED/'+kind+'.json',{'artifact_kind':kind,'status':'NOT_EXECUTED','reason':REASON,
            'ledger_rows_created':False,'V5_future_state_substitution':False,'missing_result_imputed_as_zero':False})
    missing=SCRATCH/'project_sources/21-Ark_Capital_v5_MAX3_Slot_Intelligence_20261004_Curves-1-.png'
    save('DISPLAY_ATTACHMENT_RECEIPT.json',{'requested_display_path':str(missing),'exists':missing.exists(),
        'classification':'OPTIONAL_DISPLAY_ATTACHMENT','does_not_block_certified_native_MTM_source':True,
        'native_MTM_actual_path':str(INPUT/ROLES['native_curve']),'native_MTM_sha256':sha(INPUT/ROLES['native_curve']),
        'new_R_chart':'NOT_EXECUTED','reason':'No R Replay; do not fabricate a curve.'})
    report=[]
    report += ['| 100万円→20 sessions | V5 | R | R−V5 |','|---|---:|---:|---:|',
        '| Min | 1,082,366円 | 未実行 | 未評価 |','| Mean | 1,190,646円 | 未実行 | 未評価 |',
        '| Median | 1,199,154円 | 未実行 | 未評価 |','| Max | 1,297,031円 | 未実行 | 未評価 |',
        '| 2x hit | 0/19 | 未実行 | 未評価 |','',
        '## 🛑 判定：PAST_SUPPORT_NOT_ESTABLISHED','',
        '元OOFの8 blockすべてで過去適格性が不成立でした。Rのprimary Replay、実行claim、独立R再構築は実施せず、固定STOPしました。V5を保持します。研究候補の提案・Capital候補選択・Champion更新・注文・main適用はありません。','',
        '上表のV5は保存原19窓の表示参考値です。R未実行を0円・0勝・V5同値へ補完していません。38 session連結系列の対応する20-session正規化窓であり、独立reset試験・完全calendar月・全市場営業日の成績ではありません。','',
        '| 対応比較 | 結果 |','|---|---|','| better / equal / worse（19窓） | 未評価 / 未評価 / 未評価 |',
        '| 最悪のR−V5差 | 未評価 |',f'| V5全系列 minute-MTM MaxDD | {pct(float(rf(v["full_maxdd"]["maxdd"])))} |',
        '| R全系列・各20窓 MaxDD | 未評価 |','',
        '## 📋 全E/Q/R1 Gate','', '| Gate | R判定 | 理由 |','|---|---|---|']
    report += [f'| {g} | NOT_EVALUATED | 過去支援不成立によりR未実行 |' for g in gates]
    report += ['', '事前の因果接続・保存case照合はPASSですが、R最終Q6 PASSやCapital改善とは扱いません。NO_EFFECT_PROVENも主張しません。全prefix同値走査を実施していないためです。','',
        '## 🕰️ 過去だけの8適格表','',
        '| block | 先行OOF session | S N/session/block | F N/session | S U5/U10 | S平均net return | session proxy CI95% | 不成立Hi | 適格 |',
        '|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for t in tables:
        sc=t['S'];fc=t['F'];ci=t['metrics']['bootstrap_CI95'];interval='未評価（COLD）' if ci is None else f'[{pct(ci[0])}, {pct(ci[1])}]'
        report.append(f'| {t["block"]} | {len(t["frame_sessions"])} | {sc["total_N"]}/{sc["distinct_sessions"]}/{sc["distinct_blocks"]} | {fc["total_N"]}/{fc["distinct_sessions"]} | {sc["target_counts"]["U5"]}/{sc["target_counts"]["U10"]} | {pct(t["metrics"]["mean_S_net_return"])} | {interval} | {", ".join(t["failed_Hi"])} | false |')
    report += ['',
        'block8はSの件数条件H1を通りましたが、H2/H3/H4/H5/H6を通りませんでした。先行blockのSのみを利用し、当blockの3件を加えた全S24件で判定していません。block2–8の必要S/F outcome unknownは全て0、block1はCOLD_ABSTAINです。','',
        '| block | 不足S N | 不足S session | 不足S block | 不足F N | 不足F session | 不足U5 | 不足U10 |','|---:|---:|---:|---:|---:|---:|---:|---:|']
    for t in tables:
        n=t['support_shortfalls'];report.append('| '+str(t['block'])+' | '+' | '.join(str(n[k]) for k in ('S_N','S_sessions','S_blocks','F_N','F_sessions','S_U5','S_U10'))+' |')
    report += ['', '各Sは当時の原head・原参照・V5 native snapshotから、score条件を満たし元singleton allocationで初めて実数量が出るproposalをsessionあたり1件だけ固定したものです。台帳へ介入せず、outcome join前にhash/manifestをcommitしactual GETしました。Sはstandalone proposal supportであり、historical policy Replay・実際の回収PnLではありません。','',
        'label成熟は保存teacherのpotential horizon/capture complete、Frozen EXIT/EODのCOMPLETE・source/release上限から、元session15:31を保守的な境界として後続block09:00と比較しました。既存のclosed-bar assumed availability契約に基づく証明です。実際の過去provider配信時刻はUNKNOWNで、そこまでの保証へ拡張していません。warmup・training resubstitution・同block・後続block outcomeは資格判定へ使用していません。','',
        '## 🔍 block8の品質比較（過去S21対過去F134）','',
        '| target | 過去S | 過去F | 条件 | 結果 |','|---|---:|---:|---|---|']
    last=tables[-1]
    for k in ('U5','U10','U3','Weak','realized_nonpositive'):
        group='H5_details' if k in ('U5','U10','U3') else 'H6_details';d=last['metrics'][group][k]
        report.append(f'| {k} | {d["S_positive_N"]}/{d["S_den"]} | {d["F_positive_N"]}/{d["F_den"]} | S率'+('≥F率' if group=='H5_details' else '≤F率')+' | '+('PASS' if d['pass'] else 'FAIL')+' |')
    report += ['', 'S平均returnはS件数を分母とし、bootstrapのsession proxyは先行OOF session全体を分母として空sessionを0にしています。両者は分母が異なります。PCG64、seed=571005310+b、1999回、linear percentileを固定し、保存countsから独立再集計しました。新たな抽出・閾値探索は行っていません。','',
        '## 🌊 activity waterfall','', '| 段階 | N | session | block | 補足 |','|---|---:|---:|---:|---|']
    for label,key in [('構造Reserve','structural_Reserve_rows'),('native picked空','native_picked_empty_rows'),('raw pP先頭','raw_pP_first'),('score条件','score_pass'),('過去適格block','past_qualified'),('適格状態のnative数量≥100','native_qty100_after_qualification')]:
        n=stages[key];report.append(f'| {label} | {n["N"]} | {n["sessions"]} | {n["blocks"]} | '+('保存snapshot、state mutationなし' if key not in ('past_qualified','native_qty100_after_qualification') else '適格blockなし')+' |')
    report += ['| 初回差分 | 未実行 | 未実行 | 未実行 | prefix走査0 |','| actual例外funded | 0 | 0 | 0 | R Replay未実行 |',
        '| 完全決済 | 未実行 | 未実行 | 未実行 | R台帳なし |',
        f'| 診断：score条件＋snapshot数量≥100 | {stages["diagnostic_score_pass_snapshot_qty100"]["N"]} | {stages["diagnostic_score_pass_snapshot_qty100"]["sessions"]} | 8 | actual BUYではない |',
        '| 過去Sの固定集合 | 24 | 24 | 8 | 最初のfundable proposalだけ |','',
        '構造Reserveは181行/170 batch、picked空は167行/158 batchです。選んだ158 snapshotのうち、score条件を無視した単なる数量診断では126件がfundable、32件がquantity0でした。score通過52件のうち41件は数量が出ますが、過去支援不成立のため実行へ進みません。','',
        '| abstain・非選択理由 | N | session | block |','|---|---:|---:|---:|']
    for k,n in abstain.items():report.append(f'| {k} | {n["N"]} | {n["sessions"]} | {n["blocks"]} |')
    report += ['', '理由は段階ごとの分母を持ち、session数も重なります。PAST_UNQUALIFIEDはscore通過52件すべてに適用されます。quantity診断の失敗理由は別に示します。','',
        '| snapshot数量0の診断理由 | N | session | block |','|---|---:|---:|---:|']
    for k,n in diagnostic_qty0.items():report.append(f'| {k} | {n["N"]} | {n["sessions"]} | {n["blocks"]} |')
    report += ['', '「cashで100株を払える」と「target/cap/budgetを満たして元allocationで数量が出る」を分けました。先頭score失敗から下位へ乗換え、quantity0後の同batch backfill、強制1lotはありません。','',
        '## 🧪 原score接続・誤排除の診断','',
        '| 母集団 | N | known/unknown | U5 | U10 | Medium3–<5 | Weak<2 | realized≤0 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for k in diagnostics:
        d=diagnostics[k];c=d['counts'];report.append(f'| {k} | {d["population"]["N"]} | {d["known_N"]}/{d["unknown_N"]} | {c["U5"]} | {c["U10"]} | {c["Medium"]} | {c["Weak"]} | {c["realized_nonpositive"]} |')
    report += ['', '新score条件で除外された106件にはU5が16件、U10が3件、Mediumが10件含まれます。全対象ID・原潜在値・費用込みreturn・理由はPRIVATE内の評価専用明細へ保存しました。これらは実際に失われたR取引や回収の因果効果ではありません。原1028、V5 funded150、Reserve181のmaskは異なり、原AUC/原bootstrapは再計算せず既存certificateをhash/body reuseしました。','',
        '## ↔️ impact table','', '| 分類・項目 | 件数 | 数量 | PnL | 判定 |','|---|---|---|---|---|']
    for label in ('V5_COMMON','V5_ONLY','R_ONLY','元native取引の失われた件数/数量/PnL','追加Medium/U5/U10/Weak/realized損益','後続の新MAX3/cash/Reserve miss','追加Winner−既存Winner loss'):
        report.append(f'| {label} | 未評価 | 未評価 | 未評価 | R未実行 |')
    report += ['', '元V5の保存取引150件・Loser82件はR新成績へ転記していません。単なる追加でLoser82件を残す場合Q3はFAILになる契約をsynthetic25で確認しました。「回収だけでLoserを消した」「損失防御成功」「総合採用」とは報告しません。','',
        '## 📉 保存V5の各20窓DDと未実行R','', '| 窓 | start→end | V5 MaxDD | R MaxDD |','|---:|---|---:|---|']
    for w in v['windows']:report.append(f'| {w["window_index"]+1} | {w["start_session"]}→{w["end_session"]} | {pct(float(rf(w["maxdd"]["maxdd"])))} | 未評価 |')
    report += ['', 'V5の厳密19窓growth/amount/DD分数はPAIRED20_EXACT.json・CSVへ保存しました。R値はnull/空欄とNOT_EXECUTED理由を持ちます。未実行R曲線や台帳は生成していません。','',
        '## ✅ 独立監査・実施量・修復','',
        '| 項目 | 結果 |','|---|---:|',f'| 独立pre-main検査 | {audit["check_N"]:,} checks / mismatch0 |',
        '| 保存native batch / 全入力行 | 907 / 1,039 |','| native gate行 / filter-only行 | 494 / 545 |',
        '| singleton primary診断 / 独立照合 | 158 / 158 |','| 過去proposal S / 適格表 | 24 / 8 |',
        '| 保存bootstrap統計の独立再集計 | 13,993 |','| 必須synthetic | 28/28 PASS |',
        '| first-divergence 主/独立走査 | 0 / 0（条件で未実行） |','| R primary市場Replay / 独立R再構築 | 0 / 0 |',
        '| V5/OFF/control/旧arm市場Replay | 0 |','| new fit/refit/current inference/教師再生成 | 0 |',
        '| 原AUC/原bootstrap/Bridge診断再計算 | 0 |','| provider/Fresh/Claude/注文/main merge/force push/自動昇格 | 0 |',
        '| dispatch/cancel | 0 / 0 |','',
        '独立側はPrimary gate/allocation/evaluatorをimportしていません。同じ研究者が別実装し、元score・参照・source・Decimal28を共有するため、完全盲検の外部監査ではありません。R未実行なのでBUY–SELL/cash/MTM/日次/19窓の独立R再構築も存在しません。','',
        '技術修復は3件です。P2のnp.bool_ JSON serializationは保存countsから書出しを復旧し、乱数再抽出・新しい資格表実験をしませんでした。P3では保存gate_decisionsにfilter-only行がないschemaを検知し、P1のzip照合不足を保存DECISIONSのidentity joinで補完しました。synthetic case12のDecimal import欠落は失敗code/receiptを保存後、期待値を保ちcase12以後だけ再開しました。全失敗receiptと原code hashを残し、policy・母集団・閾値・Gate・許容差を変更していません。','',
        '## 🔒 Authority・復旧・Safety','',
        f'作成時刻：{now()}。branch：{BRANCH}。strategy parent：{PARENT}。Bridge最新actual GETは0bb1173854217e5533d01dff13d1d9e1db98312b、F9 closureは保持しました。新branchはV5 parentから作り、旧cycleを再開していません。既存の有効なR execution claim/closureは開始時にありませんでした。','',
        '正本DIRECTIVEはGitHubから全文をactual GETし、34,119 bytes、SHA256=1df3aea1ebadacff7b0a329ddfb580cfcc1f24e33f50a17885b89a99e27688c3、git blob=fa81b475448fe577583d3e1b0ee150ed8165e661を照合しました。Bridge PRIVATEは28,110,631 bytes、SHA256=a31eae5a5aea92bcd96bcc093e8379f588d801faee7858b2265a1de150401686、ZIP CRC・全298 payload hashを検証しました。packet1039とhead別32参照、native snapshots・原決済source・旧OFFreceiptを再利用しています。','',
        'workflow treeは既存監査と同一で、新branch/pathのpush適合0を検査しました。[skip ci]だけを証明にしていません。workflow dispatch/cancelや無関係job操作はありません。','',
        '| Safety flag | value |','|---|---|']
    report += [f'| {k} | false |' for k in SAFETY]
    report += ['', 'activeCapitalChampion=V5、selectedCapitalCandidate=null、selectedResearchCandidate=null、championUpdated=false。Exposure=ITERATIVE_DEVELOPMENT_EVIDENCE。past-onlyの二段目decision artifactであり、既視DevelopmentをFreshへ戻しません。新head fit0でも適応・過学習がないと主張しません。将来非劣化・無損失保証はfalseです。','',
        'CLOSURE.jsonと全checkpoint/WORK_STATUS_LOGをappend-only保存しました。P0–P3は実測検証済み、P4は固定STOP判断、P5/P6は条件により未実行、P7は報告・PRIVATE保存です。このcycleでthreshold変更・別arm・Replay再試行へ移らないDO_NOT_REPEATを保存します。','',
        '添付表示用PNGはローカルに存在しませんでしたが、必須のnative MTM源は実ファイル・hashで認証できています。未取得PNGのhash一致やRグラフは推測していません。']
    rp=OUT/'REPORT_FINAL-ja.md';assert not rp.exists();rp.write_text('\n'.join(report)+'\n',encoding='utf-8',newline='\n')
    save('DO_NOT_REPEAT.json',{'schema':'V5_R_DO_NOT_REPEAT_V1','exact_jst':now(),'terminal_status':STATUS,
        'fixed_STOP':True,'experiment_profile':PROFILE,'primary_R_replay_N':0,'reason':REASON,
        'not_authorized_same_cycle':['threshold/support/confidence/scope changes','extra arms','new fit/inference',
            'V5/OFF/control/old arm replay','R primary replay','first-divergence scan after fixed STOP'],
        'completed_sources_scores_tables_probes_not_to_be_recreated':True,'ambiguous_claim_rule':'AMBIGUOUS_STOP, never duplicate execution'})
    save('CLOSURE.json',{'schema':'V5_R_FIXED_CLOSURE_V1','exact_jst':now(),'status':STATUS,'FIXED_STOP':True,
        'reason':REASON,'qualified_block_N':0,'past_qualification_table_generation_N':8,'S_collection_N':24,
        'native_singleton_primary_probe_N':158,'primary_R_market_replay_N':0,'independent_R_reconstruction_N':0,
        'primary_prefix_scan_N':0,'independent_prefix_scan_N':0,'independent_pre_main_mismatch_N':0,'synthetic_pass_N':28,
        'report_sha256':sha(rp),'qualification_sha256':sha(OUT/'PAST_QUALIFICATION_BY_BLOCK.json'),
        'execution_decision_sha256':sha(OUT/'EXECUTION_DECISION.json'),'directive_sha256':sha(OUT/'DIRECTIVE.txt'),
        'candidate_new_performance':'NOT_EXECUTED','capital_gates':'NOT_EVALUATED','quality_gates':'NOT_EVALUATED',
        'NO_EFFECT_PROVEN':False,'improvement_claim':False,'loss_defense_success_claim':False,
        'activeCapitalChampion':'V5','selectedCapitalCandidate':None,'selectedResearchCandidate':None,'championUpdated':False,
        'source_exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','future_noninferiority_guarantee':False,'future_zero_loss_guarantee':False,
        'counts':ZERO_COUNTS|{'pastQualificationTableGeneration':8,'nativeSingletonPrimaryProbes':158,'syntheticCasesPassed':28},
        'Safety':SAFETY,'delivery_state':'Research closed; archive hash/retention receipt recorded separately after delivery. No research resume.'})
    checkpoint('P7','FINAL_REPORT_FIXED_STOP',{'status':STATUS,'report_sha256':sha(rp),'Gate_E_Q_R1':'NOT_EVALUATED',
        'private_payload_manifest_pending_packaging':True},'Package retained artifacts, actual GET closure, archive delivery receipt only; no research resume',
        {'pastQualificationTableGeneration':8,'nativeSingletonPrimaryProbes':158,'syntheticCasesPassed':28})
    print(json.dumps({'status':STATUS,'report':str(rp),'R_replay_N':0,'block8_mean':tables[-1]['metrics']['mean_S_net_return'],
        'score_excluded_winners':diagnostics['score_rejected106']['counts']}))

if __name__=='__main__':main()
