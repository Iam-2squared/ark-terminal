"""Close the finite cycle from immutable outputs; no fit or market replay."""
import sys, csv, copy, subprocess
from collections import defaultdict
from decimal import Decimal as D
from fractions import Fraction as F
from statistics import mean
from rneg_io import *


def money_reference(trades, stream, actions, scope):
    groups=defaultdict(list)
    for t in trades:
        r=stream[t['entry_id']]
        groups[(r['block'],r['rank'])].append(t)
    detail=[]
    for (block,rank),tt in sorted(groups.items()):
        rejected=[t for t in tt if actions[t['entry_id']]['action']=='VETO_THIS_ENTRY']
        k=len(rejected); f=D(k)/D(len(tt))
        detail.append({'block':block,'native_rank':rank,'saved_purchase_N':len(tt),'same_veto_N':k,
            'expected_negative_N':float(F(k,len(tt))*sum(D(t['pnl'])<0 for t in tt)),
            'actual_negative_N':sum(D(t['pnl'])<0 for t in rejected),
            'expected_static_loss_jpy':str(f*sum((-min(D(t['pnl']),0) for t in tt),D(0))),
            'actual_static_loss_jpy':str(sum((-min(D(t['pnl']),0) for t in rejected),D(0))),
            'expected_static_positive_jpy':str(f*sum((max(D(t['pnl']),0) for t in tt),D(0))),
            'actual_static_positive_jpy':str(sum((max(D(t['pnl']),0) for t in rejected),D(0)))})
    total={'purchase_N':len(trades),'same_veto_N':sum(x['same_veto_N'] for x in detail)}
    for k in ['expected_negative_N','actual_negative_N']:
        total[k]=sum(x[k] for x in detail)
    for k in ['expected_static_loss_jpy','actual_static_loss_jpy','expected_static_positive_jpy','actual_static_positive_jpy']:
        total[k]=str(sum((D(x[k]) for x in detail),D(0)))
    return {'scope':scope,'total':total,'groups':detail}


def close_audit():
    failures=[]; checks={}
    target=rows(PRIVATE/'RNEG_TARGETS_EVALUATION_ONLY.jsonl.gz')
    for r in target:
        if r['known']:
            assert r['y_neg']==int(D(r['sell_credit'])<D(r['buy_debit']))
        else:
            assert all(r[k] is None for k in ['buy_debit','sell_credit','r_original','y_neg'])
    checks['target_known_N']=sum(r['known'] for r in target)
    checks['target_unknown_N']=sum(not r['known'] for r in target)
    checks['target_exact_zero_N']=sum(r['known'] and D(r['sell_credit'])==D(r['buy_debit']) for r in target)
    checks['actual_HL0_le_zero_vs_RNEG_lt_zero_difference_N']=checks['target_exact_zero_N']
    cases=[]
    for credit,label in [('99.999999999999',1),('100',0),('100.000000000001',0)]:
        debit=D('100'); y=int(D(credit)<debit)
        assert y==label
        cases.append({'buy_debit':'100','sell_credit':credit,'RNEG_lt_zero':y,'HL0_le_zero':int(D(credit)<=debit)})
    debit=D('100')*D('1.0005');credit=D('100')*D('0.9995')
    assert credit/debit-1==D('0.9995')/D('1.0005')-1
    checks['synthetic_strict_zero_and_sign_cases']=cases
    checks['synthetic_effective_cost_once']={'raw_buy':'100','raw_sell':'100','buy_debit':str(debit),'sell_credit':str(credit),'commission':0,'return':str(credit/debit-1)}
    binding=read(OUT/'SOURCE_BINDING.json')
    for rel,want in binding['source_hashes'].items():
        assert sha(WORK/rel)==want,rel
    checks['unchanged_source_hash_N']=len(binding['source_hashes'])
    pre=read(OUT/'MODEL_AND_POLICY_PRECOMMIT.json')
    for name,want in pre['code_hashes'].items():assert sha(CODE/name)==want,name
    checks['unchanged_precommitted_code_N']=len(pre['code_hashes'])
    replay=read(OUT/'REPLAY_SOURCE_BINDING.json')
    for name,want in replay['native_V5_code_hashes'].items():assert sha(V5/name)==want,name
    checks['unchanged_native_V5_code_N']=len(replay['native_V5_code_hashes'])
    changes=subprocess.check_output(['git','diff','--name-only',binding['basis_head']],cwd=REPO,text=True).splitlines()
    assert all(p.startswith('docs/evidence/'+NAME+'/') or p.startswith('research/'+NAME+'/') for p in changes)
    checks['tracked_upstream_file_changes']=0
    # One saved actual trace: future nested payloads must never be read by CORE.
    sys.path.insert(0,str(V5))
    import core_features
    trace=rows(DATA/'hl0/work_inputs/exit_v2/FULL_TRACE/2025-05-30_17580.jsonl.gz')
    entry=next(e for e in rows(Q/'FROZEN_ENTRY.jsonl.gz') if e.get('watch_key')=='2025-05-30|17580' and e['entry_status']=='FIRST_ENTRY')
    changed=copy.deepcopy(trace);future_N=0
    for r in changed:
        if r['bar_end_minute']>entry['fill_minute']:
            r.update(state=None,path=None,path_events=None);future_N+=1
    assert future_N>0
    assert core_features.project(entry,trace)==core_features.project(entry,changed)
    checks['actual_CORE_future_suffix_nested_payload_mutation']={'trace_N':len(trace),'future_rows_mutated_N':future_N,'feature_and_provenance_equal':True}
    for p in ['OOF_POLICY_ASOF_AUDIT.json','DEFENSE_INDEPENDENT_ACCOUNTING.json','OFF_NATIVE_COMPATIBILITY.json']:
        a=read(OUT/p);assert a['status']=='PASS',p
    ledger=read(OUT/'FIT_LEDGER.json');assert ledger['fits']==16 and ledger['by_recipe']=={'D1':8,'D2':8} and ledger['technical_retries']==0
    assert len(list((PRIVATE/'models').glob('*.pkl')))==16
    checks['new_fits']=16;checks['audit_refits']=0;checks['market_replays']=0
    save(OUT/'FINAL_TARGET_SOURCE_FREEZE_AUDIT.json',{'status':'PASS','exact_jst':now(),'checks':checks,'mismatch_N':0,'mismatches':failures,'historical_actual_arrival':'UNKNOWN; HISTORICAL_ASSUMED_AVAILABILITY only'})


def main():
    close_audit()
    diag=read(OUT/'LOSS_DEFENSE_DIAGNOSTIC.json'); comp=read(OUT/'RESET20_COMPARISON.json')
    stream={r['entry_id']:r for r in rows(SPECTRUM/'source/candidate_stream.jsonl.gz')}
    actions={r['entry_id']:r for r in rows(PRIVATE/'DEFENSE_ACTIONS.jsonl.gz')}
    refs=[money_reference(rows(SPECTRUM/'source/native_trades.jsonl.gz'),stream,actions,'OLD_V5_CHAIN')]
    for w in comp['all_windows']:
        if w['paired_complete']:refs.append(money_reference(rows(RESET/'runs/V5_RESET20'/w['window_id']/'TRADES.jsonl.gz'),stream,actions,w['window_id']))
    save(OUT/'STATIC_MONEY_UNINFORMATIVE_REFERENCE.json',{'exact_jst':now(),'method':'analytic expectation for same veto N per block x native rank, saved original quantities; no random replay','references':refs,'static_is_not_actual_Portfolio_saving':True})
    sessions=rows(PRIVATE/'SESSION_DIAGNOSTICS.jsonl.gz');loo=rows(PRIVATE/'ALL_SYMBOL_LEAVE_ONE_OUT.jsonl.gz')
    ss=[]
    for s in sessions:
        row={'session':s['session'],**{k:v for k,v in s['defense'].items() if not isinstance(v,dict)}}
        for recipe,m in s['metrics'].items():row[recipe+'_AUROC']=m['AUROC']
        ss.append(row)
    with (OUT/'SESSION_DIAGNOSTICS.csv').open('w') as f:
        wr=csv.DictWriter(f,list(ss[0]));wr.writeheader();wr.writerows(ss)
    dependency={'exact_jst':now(),'scope':'RANK_PASS, saved unit returns; all symbols symmetric; not portfolio PnL',
        'session_N':len(ss),'veto_session_N':sum(s['veto_all_N']>0 for s in ss),
        'session_unit_net_min':min(s['unit_static_net'] for s in ss),'session_unit_net_max':max(s['unit_static_net'] for s in ss),
        'all_symbol_N':len(loo),'leave_one_symbol_out_net_min':min(s['remaining_unit_net'] for s in loo),
        'leave_one_symbol_out_net_max':max(s['remaining_unit_net'] for s in loo),
        'leave_one_symbol_out_positive_net_N':sum(s['remaining_unit_net']>0 for s in loo),
        'full_symbol_table':'PRIVATE/ALL_SYMBOL_LEAVE_ONE_OUT.jsonl.gz','full_session_table':'SESSION_DIAGNOSTICS.csv'}
    save(OUT/'DEPENDENCY_DIAGNOSTIC.json',dependency)
    plot(diag,comp,refs)
    report(diag,comp,refs,dependency)
    counts={**ZERO_COUNTS,'D1_fits':8,'D2_fits':8,'scheduled_fits':16,'technical_fit_retries':0,
        'new_Capital_candidates':1,'new_Capital_batches':1,'formal_replay_restarts':0,'feature_regeneration_batches':0,
        'new_Control_diagnostic_days':1,'candidate_window_attempts':21,'candidate_complete_windows':9,'candidate_session_days':180,'audit_refits':0}
    state=read(OUT/'CURRENT_STATE.json')
    state.update(not_executed=['Production deployment','Coverage repair for unresolved 2025-07-11/2025-07-14','Independent fresh-period confirmation'],
        unverified=['Actual historical provider arrival timestamps','Independent Fresh/OOS performance','Missing coverage in 12 windows'],
        new_performance_claim=True,selectedCapitalCandidate=None,investigatedCapitalCandidate='V5_RNEG_DEFENSE_V1',
        decision='REJECTED; preserve V5 Control',result_summary={k:v for k,v in comp.items() if k not in ['all_windows']})
    save(OUT/'CURRENT_STATE.json',state)
    checkpoint('REPLAY_AND_ACCOUNTING_COMPLETE',comp['status'],counts,
        ['Sources and exact pre-buy join audited','HL0 8 saved models reused, zero refits','Fixed D1/D2 16 initial OOF fits complete','All 8 past-only policy snapshots locked and GitHub read back','One Defense RESET20 batch: 9 complete, 12 coverage unknown','Independent accounting PASS, zero mismatches','Negative economic result retained, V5 Control preserved','Report and all planned-window comparison written'],
        'Save replay/accounting checkpoint and final report to GitHub; actual GET body/blob/tree/HEAD; durable private handoff. Finite cycle ends with Defense rejected, no third recipe or threshold rescue.',
        ['Inherited missing coverage in 12/21 windows; historical actual arrival UNKNOWN'])
    print(json.dumps({'exact_jst':now(),'status':comp['status'],'final_target_source_freeze_audit':'PASS','private_symbol_dependency_N':len(loo),'report_written':True,'reference_old_V5':refs[0]['total']},ensure_ascii=False))


def plot(diag,comp,refs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':160})
    fig,ax=plt.subplots(1,2,figsize=(12,4.4),layout='constrained')
    t=refs[0]['total']; labels=['Saved loss removed','Saved profit sacrificed']
    x=np.arange(2)
    ax[0].bar(x-.17,[float(t['actual_static_loss_jpy']),float(t['actual_static_positive_jpy'])],.34,label='Defense')
    ax[0].bar(x+.17,[float(t['expected_static_loss_jpy']),float(t['expected_static_positive_jpy'])],.34,label='Same-count no-info expectation',color='#9ca3af')
    ax[0].set_xticks(x,labels);ax[0].set_ylabel('JPY (old V5 quantities)');ax[0].set_title('Static old V5 chain: 5 vetoes');ax[0].legend(fontsize=8)
    a=comp['V5_trades_overlapping_accounts'];b=comp['Defense_trades_overlapping_accounts']
    ax[1].bar(x-.17,[float(a['negative_pnl_abs_jpy']),float(a['positive_pnl_jpy'])],.34,label='V5')
    ax[1].bar(x+.17,[float(b['negative_pnl_abs_jpy']),float(b['positive_pnl_jpy'])],.34,label='Defense',color='#e07a5f')
    ax[1].set_xticks(x,['Actual negative PnL (abs)','Actual positive PnL']);ax[1].set_ylabel('JPY (sum of 9 overlapping accounts)');ax[1].set_title('Full RESET20 account path');ax[1].legend()
    fig.savefig(OUT/'RNEG_LOSS_AND_PROFIT.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained')
    blocks=diag['masks']['RANK_PASS']['block_metrics']
    for recipe,color in [('B0','#a0aec0'),('HL0','#805ad5'),('D1','#187f9e'),('D2','#e07a5f')]:
        ax.plot([r['block'] for r in blocks],[r['metrics'][recipe]['AUROC'] for r in blocks],marker='o',label=recipe,color=color)
    ax.axhline(.5,color='#555',ls=':',lw=1);ax.set_xlabel('Original outer block');ax.set_ylabel('RNEG AUROC (rank-pass known rows)');ax.set_title('Fixed recipes, initial forward OOF / repeated Development');ax.legend(ncol=4)
    fig.savefig(OUT/'BLOCK_INCREMENTAL_SKILL.png');plt.close(fig)
    windows=[w for w in comp['all_windows'] if w['paired_complete']];x=np.arange(len(windows))
    fig,(ax,bx)=plt.subplots(2,1,figsize=(10,6),height_ratios=[2,1],sharex=True,layout='constrained')
    ax.plot(x,[float(w['V5_final_jpy']) for w in windows],'-o',label='V5');ax.plot(x,[float(w['Defense_final_jpy']) for w in windows],'-o',label='Defense',color='#e07a5f')
    ax.set_ylabel('Final assets (JPY)');ax.set_title('RESET20: same 9 completed windows / initial JPY 1,000,000');ax.legend()
    diff=[float(w['delta_jpy']) for w in windows];bx.bar(x,diff,color=['#328a60' if d>0 else '#c45f50' for d in diff]);bx.axhline(0,color='#555',lw=.8);bx.set_ylabel('Defense - V5 (JPY)');bx.set_xticks(x,[w['start_session'] for w in windows],rotation=30,ha='right');bx.set_xlabel('Start session (12 blocked windows retained in all-21 table)')
    fig.savefig(OUT/'RESET20_START_ASSETS.png');plt.close(fig)


def report(diag,c,refs,dependency):
    def yen(v):return f'{D(str(v)):,.2f}'
    def pct(v):return f'{v*100:.2f}%'
    lines=['# 🛡️ RNEG Defense 有限実験の結果', '', f'実時計JST: `{now()}`  /  判定: **`{c["status"]}`**  /  Control: **V5を保持**', '',
        '旧HL0は保存済み8モデルとOOFを再利用し、再fitは0。新規変更は同じState9/Path入力の非線形interaction（D1）と、凍結P0の購入前context108列追加（D2）の固定2構成だけ。各8fitを実施した。', '',
        '購入前の全1,039 Entryでは45件のRNEGを見送り対象にし、正R26件も巻き込んだ。実行適格・rank通過集合では負21件／正15件、旧V5の150購入では負4件／正1件（保存数量で正利益913円）を見送り対象にした。後者の静的損失除去19,463.40円を新口座利益へ読み替えない。', '',
        f'過去OOFだけで有効になったDefenseを最大1候補として接続し、RESET20を1正式batch測定した。9完了窓の口座全経路では負PnL絶対額が{yen(-D(c["actual_loss_reduction_jpy"]))}円増え、正PnLは{yen(-D(c["actual_positive_pnl_difference_jpy"]))}円減った。最終資産中央値は{yen(-D(c["wealth_median_difference_jpy"]))}円、平均は{yen(D(c["V5_wealth"]["mean"])-D(c["Defense_wealth"]["mean"]))}円低下。**Defense不採用で有限終了する。**', '',
        '## 🧠 入力・識別・校正', '',
        'State9/Pathは既存COREから継承し、ID・gap・segment・pivotの意味は変更していない。CORE 1,600行／58sessions、warmup20／OOF38／8blockを維持。D2はP0 numeric110からclockMinuteとactiveMinutesSinceSelectorの2重複をmetadataで除外した108列。正確なFrozen first-intent row_id・row_indexへ接続し、全8blockの適格行で接続100%。追加feature生成は0batch。', '',
        '購入判断は元fill時刻、SELL/cash解放と元admissionの後、V5のoccupancy・数量決定より前。閉じたState prefixとfirst-intent snapshotのみを使う。fill raw open quoteの可用性は元V5の仮定を継承し、fill barのH/L/C/volumeを使用しない。**HISTORICAL_ASSUMED_AVAILABILITY**で、actual arrivalはUNKNOWN。学習済みEntry score依存のtrain ID・cutoffを確認し、外側test教師混入0。既存定義・モデル選定のDevelopment exposureは残る。', '',
        '| 母集団 | 全行 | R既知 | R不明 | 負 | 正 |', '|---|---:|---:|---:|---:|---:|']
    for name,m in diag['masks'].items():
        d=m['defense'];lines.append(f'| {name} | {d["total_N"]} | {d["known_N"]} | {d["unknown_N"]} | {d["negative_N"]} | {d["positive_N"]} |')
    lines+=['','known target全1,560行（warmup544＋OOF1,016）、unknown40行はruntimeから削除せず教師／採点から分離。厳密r=0はwarmupを含め0行。HL0の<=0と今回<0の実データラベル差0。原debit/creditから費用1回、EXIT＋EODの原Rをreuseし、新しいR materializationは0。', '',
        '| 母集団 | predictor | N | AUROC | AP | Brier | log loss |', '|---|---|---:|---:|---:|---:|---:|']
    for name,m in diag['masks'].items():
        for recipe,metrics in m['metrics'].items():
            lines.append(f'| {name} | {recipe} | {metrics["N"]} | {metrics["AUROC"]:.6f} | {metrics["average_precision"]:.6f} | {metrics["Brier"]:.6f} | {metrics["log_loss"]:.6f} |')
    lines+=['','全既知RのAUROCはD1がHL0より0.026689高いが、Brier/log lossではD1/D2とも過去率B0を上回らない。D2もD1を上回らない。出力を校正済み損失確率と認定せず、全期間AUROCで配備modelを選び直していない。','','## 🚫 過去だけで固定した見送り', '',
        '各block開始時のCAL_PASTは、それ以前の初回OOFがある成熟・適格・rank通過行だけ。warmup in-sampleと現在／未来blockは0。指示書のsupport、正件数10%／正unit利益10%、precision、純価値、任意1session除外を適用。同score一括のdistinct tau、recall→precision→tau→D1/D2順という1手続きを使用。各blockのmodel/tauはGitHubへ保存・読み戻し後にCapitalを測定した。', '',
        '| block | 状態 | model | tau | 過去CAL行 | 過去CAL負 | 過去CAL非負 |', '|---:|---|---|---:|---:|---:|---:|']
    for b in range(1,9):
        p=read(OUT/'policy_snapshots'/f'BLOCK_{b:02}.json');q=p.get('selection') or {}
        s=q.get('CAL_PAST') or (p['past_qualification'][0]['support'] if p['past_qualification'] else {})
        lines.append(f'| {b} | {p["status"]} | {q.get("recipe") or "—"} | {q.get("tau") if q.get("tau") is not None else "—"} | {s.get("N",0)} | {s.get("negative_N",0)} | {s.get("nonnegative_N",0)} |')
    lines+=['','第1〜3blockと第8blockはOFF、4〜7はD1でACTIVE。第8blockを結果を見て救済しなかった。全OFF期間も分母と口座経路に残した。','','| 母集団 | 見送り負／正 | precision | 負回避recall | 正件数誤拒否率 | 正unit利益巻込み | non-veto coverage |', '|---|---:|---:|---:|---:|---:|---:|']
    for name,m in diag['masks'].items():
        d=m['defense'];lines.append(f'| {name} | {d["veto_negative_N"]} / {d["veto_positive_N"]} | {pct(d["veto_precision"])} | {pct(d["negative_veto_recall"])} | {pct(d["positive_false_veto_rate"])} | {pct(d["positive_unit_profit_removed_rate"])} | {pct(d["non_veto_coverage"])} |')
    rank=diag['masks']['RANK_PASS']['defense']
    lines+=['','未来rank-passのunit純価値は−0.201560。正利益8.11%以内でも金額の大きな正Rを失う問題が残った。残した群のRNEG率55.26%。', '', '| rank-pass tail | 母数 | 見送り |', '|---|---:|---:|']
    for k,d in rank['tails'].items():lines.append(f'| {k} | {d["population_N"]} | {d["veto_N"]} |')
    lines+=['','| 正Rの帯域（%） | 母数 | 見送り |','|---|---:|---:|']
    for label,key in [('0超〜1未満','GT0_LT1'),('1〜3未満','GE1_LT3'),('3〜5未満','GE3_LT5'),('5〜10未満','GE5_LT10'),('10以上','GE10')]:
        d=rank['positive_bins'][key];lines.append(f'| {label} | {d["population_N"]} | {d["veto_N"]} |')
    lines+=['','## 📊 同数の無情報見送り・依存度', '', '| 集合 | 見送りN | 実負見送り | 無情報の期待負 | 実損失除去 | 期待損失除去 | 実正利益巻込み | 期待正利益巻込み |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in refs:
        t=r['total'];lines.append(f'| {r["scope"]} | {t["same_veto_N"]} | {t["actual_negative_N"]} | {t["expected_negative_N"]:.3f} | {yen(t["actual_static_loss_jpy"])}円 | {yen(t["expected_static_loss_jpy"])}円 | {yen(t["actual_static_positive_jpy"])}円 | {yen(t["expected_static_positive_jpy"])}円 |')
    u=diag['masks']['RANK_PASS']['uninformative']['total']
    lines+=['',f'block×native rankごとに同数を無情報に除く保存台帳のanalytic expectation。無作為Portfolio Replayは0。rank-passでは実負見送り{u["actual_negative_N"]}件／期待{u["expected_negative_N"]:.3f}件、unit損失実{u["actual_unit_loss"]:.6f}／期待{u["expected_unit_loss"]:.6f}、unit正利益実{u["actual_unit_profit"]:.6f}／期待{u["expected_unit_profit"]:.6f}。件数だけでは改善を認定しない。', '',
        f'38sessionを全件評価。session別見送りunit純価値は{dependency["session_unit_net_min"]:.6f}〜{dependency["session_unit_net_max"]:.6f}。rank-pass全310symbolを対称に1つずつ除外した残り純価値は{dependency["leave_one_symbol_out_net_min"]:.6f}〜{dependency["leave_one_symbol_out_net_max"]:.6f}、正になるのは{dependency["leave_one_symbol_out_positive_net_N"]}/310。全symbol表はprivate、全38session表と全8block診断は保存済み。都合の良いsubsetの再選択は0。', '', '![Block別skill](BLOCK_INCREMENTAL_SKILL.png)', '', '![損失と利益](RNEG_LOSS_AND_PROFIT.png)', '', '## 💴 RESET20：口座全経路の比較', '',
        '各口座100万円・保有0、20sessions。歴史時点のmodel・policyはresetしない。全予定21窓を保持し、W01〜W12は7/11・7/14の既存coverage不足でBLOCKED_COVERAGE。0-return補完は0、片側未完了0。W13〜W21の9完了窓・180口座session-daysだけをpaired比較する。窓は重複したDevelopmentで、独立した9か月や全期間の成績ではない。', '',
        '| 指標 | V5 | Defense | Defense − V5 |', '|---|---:|---:|---:|']
    a=c['V5_trades_overlapping_accounts'];b=c['Defense_trades_overlapping_accounts']
    for label,key in [('購入数','purchase_N'),('負取引数','negative_N'),('正取引数','positive_N')]:lines.append(f'| {label} | {a[key]} | {b[key]} | {b[key]-a[key]:+d} |')
    lines.append(f'| 負率 | {pct(a["negative_rate"])} | {pct(b["negative_rate"])} | {(b["negative_rate"]-a["negative_rate"])*100:+.4f}pt |')
    for label,key in [('負PnL絶対額','negative_pnl_abs_jpy'),('正PnL総額','positive_pnl_jpy'),('純PnL総額','net_pnl_jpy')]:lines.append(f'| {label} | {yen(a[key])}円 | {yen(b[key])}円 | {yen(D(b[key])-D(a[key]))}円 |')
    for label,key in [('最終資産 Min','min'),('Mean','mean'),('Median','median'),('Max','max')]:lines.append(f'| {label} | {yen(c["V5_wealth"][key])}円 | {yen(c["Defense_wealth"][key])}円 | {yen(D(c["Defense_wealth"][key])-D(c["V5_wealth"][key]))}円 |')
    lines.append(f'| 200万円到達口座 | {c["V5_wealth"]["two_x_N"]}/9 | {c["Defense_wealth"]["two_x_N"]}/9 | 0 |')
    lines.append(f'| worst MaxDD | {pct(float(c["worst_maxDD_V5"]))} | {pct(float(c["worst_maxDD_Defense"]))} | {(float(c["worst_maxDD_Defense"])-float(c["worst_maxDD_V5"]))*100:+.4f}pt |')
    ws=[w for w in c['all_windows'] if w['paired_complete']]
    for label,key in [('平均cash資金利用','utilization'),('平均slot占有','occupancy')]:
        av=mean(w['V5_'+key] for w in ws);bv=mean(w['Defense_'+key] for w in ws);lines.append(f'| {label} | {av:.6f} | {bv:.6f} | {bv-av:+.6f} |')
    lines+=['',f'中央値同士の差 **{yen(c["wealth_median_difference_jpy"])}円** と、paired差の中央値 **{yen(c["paired_difference_median_jpy"])}円** は別の値。改善{c["paired_win_N"]}／同額{c["paired_tie_N"]}／悪化{c["paired_loss_N"]}口座。', '', '| RN tail | V5件数／損失額 | Defense件数／損失額 |', '|---|---:|---:|']
    for k in ['RN1','RN3','RN5','RN10']:
        x=a['RN_tail_loss'][k];y=b['RN_tail_loss'][k];lines.append(f'| {k} | {x["N"]} / {yen(x["loss_jpy"])}円 | {y["N"]} / {yen(y["loss_jpy"])}円 |')
    exp=c['explicit_veto_saved_quantities']
    lines+=['',f'9口座の旧数量上の明示VETOは延べ{exp["N"]}件（負{exp["negative_N"]}／正{exp["positive_N"]}）。静的損失除去{yen(exp["static_removed_loss_jpy"])}円／正利益巻込み{yen(exp["static_removed_positive_pnl_jpy"])}円。これは重複口座の静的金額であり、実損失削減ではない。', '', '| 取引・数量差分 | 延べ件数 | 純PnL差寄与 |', '|---|---:|---:|']
    for k,d in c['transaction_delta_decomposition'].items():lines.append(f'| {k} | {d["N"]} | {yen(d["net_pnl_difference_jpy"])}円 |')
    lines+=['','V5-onlyの減少効果を、共通購入の数量差とDefense-onlyの損失が打ち消した。VETOは仮slotから除外し、後続の合法Entryにも同じDefenseを適用。旧150購入IDをwhitelistにせず、EXIT・Reserve・allocationは凍結コードをそのまま利用した。', '', '![開始日別最終資産](RESET20_START_ASSETS.png)', '', '| 窓 | 開始〜終了 | V5状態 | Defense状態 | V5最終 | Defense最終 | 差 |', '|---|---|---|---|---:|---:|---:|']
    for w in c['all_windows']:
        fmt=lambda v:yen(v)+'円' if v is not None else 'UNKNOWN'
        lines.append(f'| {w["window_id"]} | {w["start_session"]}〜{w["end_session"]} | {w["V5_status"]} | {w["Defense_status"]} | {fmt(w["V5_final_jpy"])} | {fmt(w["Defense_final_jpy"])} | {fmt(w["delta_jpy"])} |')
    lines+=['','## 🔍 監査・予算・現在地', '',
        '独立原BUY/SELL会計は9口座ともPASS、差分0。各ending_cash = 1,000,000 + sum(actual_trade_pnl)、全EOD決済、費用1回、同時刻SELL先行、MAX3、100株lot、cash・同銘柄制約を検算した。OOFモデル再推論／train-only前処理／成熟ラベル／過去だけの独立tau選定／予測とVETOの不変性はPASS。合成12テストと元最初の1日だけのDefense OFF互換性もPASS。r=0／微小正負／unknown／元COREの実future suffixを破壊した不変性も確認。', '',
        '| 処理 | 実績 |', '|---|---:|', '| D1 / D2新fit | 8 / 8（合計16） |', '| HL0、旧State／Entry／EXIT refit | 0 |', '| full-data最終fit／calibration fit／探索 | 0 |', '| fit技術再試行／Replay再起動 | 0 / 0 |', '| 新Capital候補／正式batch | 1 / 1 |', '| 全Control Replay | 0（互換性診断のみ1日） |', '| 新R materialization／凍結feature補足生成 | 0 / 0 |', '| provider価格／protected／注文／main merge／force push／Claude | 全て0 |', '',
        '**方針:** V5をControlとして保持。V5.1や旧負結果も上書きしない。この固定2recipe＋過去選択手続きはDefense改善を確認できず不採用。第三recipe・別target・tau救済・EXIT改変へ進まない。新しい判断の前に必要なのは、既存12窓のcoverageを解消する原sourceと、この反復Development期間から独立した確認データ。今回の9完了窓をproductionReadyや全期間成功へ昇格しない。最上位の100万円→約200万円／20sessions目標は未達。', '',
        'GitHubには開始、fit前の入力・recipe固定、全8policyのReplay前固定を保存し、actual GET本文・blob・tree・branch HEADを照合済み。今回のReplay/会計・最終reportも同じ研究branchへ保存しactual GETで照合する。privateのEntry/symbol別入力、初回予測、16モデル、全口座ledger・数量差は公開GitHubへ置かず、private handoffへ収録する。', '',
        '再利用原本とハッシュはSOURCE_BINDING／REUSE_MATRIX／RNEG_TARGET_BINDING、全診断はLOSS_DEFENSE_DIAGNOSTIC、全21窓はRESET20_ALL21_WINDOWS.csv、会計はDEFENSE_INDEPENDENT_ACCOUNTINGを参照。既存Full R Spectrum一式は再生成していない。']
    (OUT/'REPORT-ja.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
