"""Render the completed fixed evidence; never choose an arm."""
import argparse, collections
from exit_common import *

def fmt(x,n=6):return 'unknown' if x is None else f'{x:.{n}f}'
def run(basis):
    d=read(HERE/'TWO_ARM_EVALUATION.json');audit=read(HERE/'INDEPENDENT_EXIT_AUDIT.json');assert audit['status']=='PASS' and audit['mismatch_N']==0
    p=d['paired_primary'];a=p['STATE_EXIT'];b=p['STATE_EXIT_HARD1'];hard=d['Hard1'];ledger=read(HERE/'FIT_LEDGER.json')
    out=[f'# State-aware EXIT v1 FastTrack — 2-arm OOF Evidence', '',f'saved_at_jst: {now()}  ',f'basis_head: `{basis}`  ',f'Document ID: `{DOC}`', '', '**新EXITの2-arm Evidenceを生成してSTOP。どちらのarmも正式採用・Freeze・production promotionしていない。**', '',
         f'Frozen FIRST ENTRY v2 — P1_Q70 / HEAD `{ENTRY_HEAD}` / 1,600 filled Entries / 58 Development sessionsをREAD ONLYで使用。Entry再fit・Q再選択・Selector変更は0。最新RC2 State9 current、同じRC2 past-only State Path/Transition history、price/volume/Selector contextを使った新モデル1 head ×5 chronological foldsを実際に学習した。Hard1追加fit=0。', '',
         '継続価値teacherは、今のnext available regular raw openで売る価格に対する、strictly later available regular raw opensと予定closing auction closeの平均価格の差（%）。将来Highを最大化するteacherではない。raw targetを−10..10へclip。これはポジションに依存しない市場contextの継続価値なので、過去train sessionsのselected-watch minute contextsで学習し、Replayは既存Frozen Entry後だけで行った。学習時に新Entryを生成していない。', '',
         '固定HistGradientBoostingRegressor: depth3 / learning_rate0.05 / max_iter100 / max_leaf_nodes31 / min_samples_leaf20 / L2=0 / early_stopping=false / random_state570926。元Entryと同じ5 chronological session foldsを使用。finite-label training rowsだけでmedian・missing indicator・one-hotをfitし、未知categoryはunknown bucket。OOF223,940 rows。Legacy State feature=0、V6 R2 score/probability/rank=0。', '',
         '通常EXITはclosed1mの予測継続価値が2回連続で0以下になった最初の時刻でintentを固定。positive、raw minute gap、AM/PM切替でcounterをreset。next available regular raw openでLONG売却し、引けまで残れば予定closing auctionで売る。Entry後だけdecisionし、EXIT後decision=0。', '',
         'Hard1は同じ予測と通常EXITにstanding stopを追加しただけ。raw line=Frozen Entry fill×0.99。observed eligible regular1mのopen<=lineならopen、そうでなければLow<=lineならlineで約定するOHLC proxy。同時刻の通常market sellは先に執行。mixed opening540/750とterminal auctionsをstop監視に含めない。sell price=raw reference×0.9995、commission0。Entryの+5bpsは既にfillに含まれ、二重計上しない。line touchのnet returnは約−1.0495%、gapではさらに下回る。', '',
         'canonical LONG sellの符号・cost計算はFrozen HEADの`predict/trading/backtest-cost-model.js`で確認し、今回のresearch costをFrozen Entryと整合する5bps/sideに固定した。generic moduleのdefault presetを使用した成績ではない。closing liquidationは今回の新EXIT contractの予定動作。足内tick順序・約定保証・capacityを仮定した実運用Evidenceではない。', '',
         f'全Entryのうち通常arm sell-filled={d["single_arm"]["STATE_EXIT"]["sell_filled_N"]}、unresolved={d["single_arm"]["STATE_EXIT"]["unresolved_N"]}。Hard1 arm sell-filled={d["single_arm"]["STATE_EXIT_HARD1"]["sell_filled_N"]}、unresolved={d["single_arm"]["STATE_EXIT_HARD1"]["unresolved_N"]}。Primary paired N={p["paired_N"]}。通常armのclosing source未取得で、Hard1だけ先にfilledとなった7件をPrimaryから除外し、single-arm panelに残した。source不足にlast-observed closeを代用していない。', '',
         '| Primary paired metric | STATE_EXIT | STATE_EXIT_HARD1 |', '|---|---:|---:|']
    for label,k in [('実現return mean (%)','realized_return_pct'),('MFE Realization mean (%)','MFE_realization_pct'),('Held Peak Giveback mean (pp)','Peak_Giveback_pp'),('Full-session opportunity giveback mean (pp)','opportunity_giveback_pp'),('holding active minutes mean','holding_active_min')]:
        out.append(f'| {label} | {fmt(a["metrics"][k]["mean"])} | {fmt(b["metrics"][k]["mean"])} |')
        out.append(f'| {label.replace("mean","median")} | {fmt(a["metrics"][k]["median"])} | {fmt(b["metrics"][k]["median"])} |')
    out+=['', f'同一Entryのpaired Δ（Hard1 − normal）return mean={fmt(p["delta_HARD1_minus_STATE_EXIT"]["realized_return_pct"]["mean"])}pp、median={fmt(p["delta_HARD1_minus_STATE_EXIT"]["realized_return_pct"]["median"])}pp。改善191 / 悪化240 / 同値1,133。metric meanの差と、各Entryのpaired Δ medianを混同しない。', '',
          'MFE Realizationはrealized return / positive observed same-session Entry→High ×100。PrimaryではN=1,397、比率はclipせず、小さいMFE分母の影響を受ける。負の実現returnでは負になる。Held Peak Givebackは売却barより前のclosed source Highで観測した保有中MFEから実現returnを引いたppで、fill-barとstop-barのHighを含めない。未来の売却後Highはfull-session opportunity givebackとして別表示する。gap up sellが保有中observed peakを超える場合はgivebackが負になり得る。全returnはEntry等重みの個別取引値であり、Capital/session/portfolio returnではない。', '',
          '| Entry-relative observed Winner | denominator / paired | STATE_EXIT return mean / median (%) | HARD1 return mean / median (%) | STATE_EXIT MFE realization mean / median (%) | HARD1 MFE realization mean / median (%) |', '|---|---:|---:|---:|---:|---:|']
    for level in ('3','5'):
        w=d['winners'][level];wm=w['STATE_EXIT']['metrics'];hm=w['STATE_EXIT_HARD1']['metrics']
        out.append(f'| ≥{level}% | {w["winner_denominator"]} / {w["paired_N"]} | {fmt(wm["realized_return_pct"]["mean"])} / {fmt(wm["realized_return_pct"]["median"])} | {fmt(hm["realized_return_pct"]["mean"])} / {fmt(hm["realized_return_pct"]["median"])} | {fmt(wm["MFE_realization_pct"]["mean"])} / {fmt(wm["MFE_realization_pct"]["median"])} | {fmt(hm["MFE_realization_pct"]["mean"])} / {fmt(hm["MFE_realization_pct"]["median"])} |')
    out+=['', 'WinnerはSelector MFE bucketではなく、Frozen Entry後strictly-later observed HighをEntry価格で割った分母。source missing下のHighは下限なので、完全なsession pathとは扱わない。≥3% Winnerのfull remaining source completeは14件、≥5%は7件。旧EXITとの比較は0。', '',
          '| Negative loss containment — paired N=1,564 | STATE_EXIT | STATE_EXIT_HARD1 |', '|---|---:|---:|']
    for label,key in [('negative return N','loss_N'),('net return <−1% N','below_minus1_N'),('net return <−2% N','below_minus2_N'),('worst return (%)','worst_return_pct')]:out.append(f'| {label} | {fmt(a["negative_loss_containment"][key])} | {fmt(b["negative_loss_containment"][key])} |')
    out.append(f'| negative return mean / median (%) | {fmt(a["negative_loss_containment"]["negative_return"]["mean"])} / {fmt(a["negative_loss_containment"]["negative_return"]["median"])} | {fmt(b["negative_loss_containment"]["negative_return"]["mean"])} / {fmt(b["negative_loss_containment"]["negative_return"]["median"])} |')
    out+=['', 'Hard1のraw lineはnet −1%上限ではないので、−1%未満Nは増える。−2%未満Nと最悪損失は別に表示した。missing barsがある区間では、未観測のstop touchが無かったとは証明できない。', '',
          '| Hard1 observed event | N |', '|---|---:|', f'| 発火 total / paired-known | {hard["trigger_N"]} / {hard["trigger_paired_known_N"]} |', f'| gap open / intrabar line touch | {hard["gap_open_N"]} / {hard["intrabar_line_touch_N"]} |', f'| 通常armのnegative returnを縮小 | {hard["saved_negative_loss_N"]} |', f'| Hard1発火によるpaired return改善 / 悪化 | {hard["trigger_return_improved_N"]} / {hard["trigger_return_worsened_N"]} |']
    for level in ('3','5'):
        x=hard['later_winners_cut'][level];out.append(f'| stop後strictly-later ≥{level}% Winnerを切った confirmed | {x["confirmed_strictly_after_stop_N"]} |');out.append(f'| stop後≥{level}% hitの有無がsource missingでunknown | {x["unknown_incomplete_source_N"]} |')
    out+=['', f'損失縮小191件の縮小幅mean={fmt(hard["negative_loss_saved_pp"]["mean"])}pp、median={fmt(hard["negative_loss_saved_pp"]["median"])}pp。stop-bar Highの順序不明だけでWinner cutを数えていない。confirmed ≥5は≥3のsubsetであり、99+61を別件数として合算しない。', '',
          f'raw eligible execution pathが両armでcompleteのpaired subsetは{d["complete_paired_execution_subset"]["paired_N"]}件。return meanはnormal={fmt(d["complete_paired_execution_subset"]["STATE_EXIT"]["metrics"]["realized_return_pct"]["mean"])}%、Hard1={fmt(d["complete_paired_execution_subset"]["STATE_EXIT_HARD1"]["metrics"]["realized_return_pct"]["mean"])}%、paired Δ mean={fmt(d["complete_paired_execution_subset"]["delta_return_pp"]["mean"])}pp。これは早いEXITほどcompleteに残りやすい選別されたsubsetで、1,564件の代替populationではない。', '',
          '今回の新EXITでは、≥5% Winnerの通常armのholding medianが2 active minutes、MFE Realization medianが2.233488%で、大Winnerの保有継続は明確な弱点として測定された。Hard1は大きいnegative lossを減らす一方、stop後に上昇したWinnerを切り、Primary paired mean returnも低下した。これらは2-arm内部の測定結果であり、旧EXITとの優劣判定や正式arm選定ではない。結果を見たteacher/threshold/model/policy追加は0。', '',
          f'独立別実装audit: {audit["status"]} / mismatch={audit["mismatch_N"]} / checks={audit["checks_total"]} / future causal leakage={audit["future_causal_leakage_N"]} / audit fit=0。全teacher rows、train/test eligibility、train-only median/one-hot、全OOF予測、1,600件のfirst-exit/next-open/Hard1優先順位とreturn/Winnerを別経路で確認した。歴史的actual known_atはUNKNOWNで、Frozen RC2のbar-end availability仮定を継承する。prospective evidenceではない。', '',
          '実行予算: new EXIT fits5/5、Hard1 fit0、search0、Entry fit0、old EXIT body read/replay/comparison0、provider0、Protected/Fresh/Validation/OOS/Prospective0、Re-entry0、Capital0、Portfolio Replay0、orders0、main merge0。sellはresearch replayの模擬記録だけで、executionAllowedなど全safety flags=false、productionReady=false。', '',
          '最終status: `STATE_AWARE_EXIT_V1_TWO_ARM_OOF_EVIDENCE_READY`。STOP。人間確認後の別Workがなければ、arm Freeze・修正実験・Re-entry・Capitalへ進まない。', '']
    (HERE/'REPORT-ja.md').write_text('\n'.join(out))
    handoff=f'''# State-aware EXIT v1 FastTrack handoff

saved_at_jst: {now()}
basis_head: `{basis}`
status: `STATE_AWARE_EXIT_V1_TWO_ARM_OOF_EVIDENCE_READY`

Frozen P1_Q70 Entry HEAD `{ENTRY_HEAD}` remains unchanged. Exactly 5 new EXIT fits, Hard1 additional fits 0. Two actual saved-source OOF replay arms only. No arm has been officially selected or frozen. Production ready=false; all safety flags=false.

1600 frozen Entries /58 sessions. Normal filled1564/unresolved36; Hard1 filled1571/unresolved29. Primary paired N1564. Mean realized returns normal0.060180% /Hard1 0.000919%; paired Δ−0.059261pp. Hard1 observed triggers449; negative losses improved191. Confirmed subsequent ≥3/≥5 Winners cut99/61; unknown missing-source cases340/374. Winners overlap and must not be added.

Independent audit PASS/mismatch0/future causal leakage0/audit fit0. Detailed definitions, denominator scope and source limitations are in REPORT-ja.md and EVALUATION_PRECOMMIT.json. A small observed MFE denominator can make MFE realization ratios extreme. No tick-level stop guarantee or net −1% loss bound is claimed.

The learner is a position-independent signed continuation-value head fitted on selected-watch context rows in the existing earlier chronological train sessions; it does not generate training Entries. Runtime is only post-fill for the immutable 1600 Entries. Exact RC2 State9 and past-only path/history are reused without logic changes; Legacy State0. No old EXIT logic, thresholds, routes or results are included.

STOP: human decision remains pending. New policy/search, Entry refit, old EXIT comparison, Re-entry, Capital/Portfolio replay, provider requests, protected opens, orders and main merge are all0.
'''
    (HERE/'FINAL_HANDOFF.md').write_text(handoff)
    write(HERE/'FINAL_STATUS.json',{'saved_at_jst':now(),'basis_head':basis,'current_status':'STATE_AWARE_EXIT_V1_TWO_ARM_OOF_EVIDENCE_READY','Frozen_Entry_HEAD':ENTRY_HEAD,'Frozen_Entry_N':1600,'primary_paired_N':p['paired_N'],'new_EXIT_fits':5,'Hard1_additional_fit':0,'independent_audit_status':'PASS','audit_mismatch_N':0,'future_causal_leakage_N':0,'Legacy_State':0,'arm_selection':0,'ExitFrozen':False,'human_review_pending':True,'STOP':True,'Entry_refit':0,'Selector_change':0,'old_EXIT_body_read':0,'old_EXIT_replay':0,'historical_EXIT_comparison':0,'R50_replay':0,'R54_replay':0,'WPSD_replay':0,'Guard_replay':0,'CCMG_replay':0,'PRR_replay':0,'Reentry':0,'Capital':0,'Portfolio_Replay':0,'provider':0,'protected':0,'orders':0,'main_merge':0,'safety':SAFETY,'productionReady':False})
    print(json.dumps({'report_saved':True,'status':'STATE_AWARE_EXIT_V1_TWO_ARM_OOF_EVIDENCE_READY','new_policy_after_results':0}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--basis',required=True);run(p.parse_args().basis)
