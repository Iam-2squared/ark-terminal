"""Render already audited research evidence; no position decision or new policy."""
import collections
from settings import HERE, PRIVATE, SAFETY, load, now, rows, save

def number(value, digits=3):
    return '—' if value is None else f'{value:,.{digits}f}'

def pair(group, metric, digits=3):
    s=group['metrics'][metric]
    return f"{number(s['mean'],digits)} / {number(s['median'],digits)}"

def table(headers, data):
    return '\n'.join(['| '+' | '.join(headers)+' |',
        '| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str,row))+' |' for row in data])+'\n'

def main():
    identity=load(HERE/'IDENTITY_RECEIPT.json')
    trace=load(HERE/'FULL_TRACE_RECONSTRUCTION_RECEIPT.json')
    audit=load(HERE/'INDEPENDENT_AUDIT.json')
    coverage=load(HERE/'LIFECYCLE_COVERAGE.json')
    all_entry=load(HERE/'ALL_ENTRY_ECONOMICS.json')[0]
    cum=load(HERE/'WINNER_CUMULATIVE.json')
    exclusive=load(HERE/'WINNER_EXCLUSIVE.json')
    armed=load(HERE/'ARMED_VS_NEVER_ARMED.json')
    reasons=load(HERE/'EXIT_REASON_DECOMPOSITION.json')
    facets=load(HERE/'ENTRY_PRIMARY_CONTEXT.json')
    records=list(rows(PRIVATE/'ECONOMICS_ROWS.jsonl.gz'))
    assert audit['mismatch_N']==audit['future_causal_leakage_N']==0
    assert len(records)==1600 and all_entry['denominator_N']==1600
    count=audit['check_counts']
    mapping=[
        (1,'Frozen Entry identity',['frozen_entry_exact_bytes','frozen_entry_N','Entry_fill_unchanged','all_1600_identity_set']),
        (2,'RC2/profile/M0/Path hashes',['frozen_RC2_profile_M0_Path_hash']),
        (3,'full State9 trace reconstruction',['full_dated_slot_coverage','trace_hash','full_trace_all_independent_RC2_parity']),
        (4,'saved overlap parity',['full_trace_saved_overlap_parity']),
        (5,'causal cutoff',['causal_cutoff_all_trace_slots','M0_previous_only','strictly_later_high_timestamp']),
        (6,'segment continuity',['independent_Path_segment','continuity_suspension']),
        (7,'observed/null distinction',['observed_null_distinction','null_has_no_run']),
        (8,'UP arm timestamp',['UP_arm_timestamp']),
        (9,'PULLBACK単独SELL=0',['PULLBACK_alone_SELL_zero']),
        (10,'RISE_STOP単独SELL=0',['RISE_STOP_alone_SELL_zero']),
        (11,'protected tighten単独SELL=0',['tighten_alone_SELL_zero']),
        (12,'UP→DOWN structural protection',['context_reversal_protected_break','first_valid_structural_EXIT']),
        (13,'independent Range retirement',['independent_range_retirement']),
        (14,'gap/reset跨ぎtransition=0',['no_gap_reset_synthetic_transition']),
        (15,'first valid EXIT trigger',['first_valid_structural_EXIT','independent_Path_event_order']),
        (16,'next-open sell5bps',['next_open_5bps_or_exact_session_close']),
        (17,'exact session-close source / explicit unresolved',['next_open_5bps_or_exact_session_close']),
        (18,'post-exit decision=0',['post_exit_decision_zero']),
        (19,'MFE / Giveback / later missed upside',['independent_economics_MFE_realization_pct','independent_economics_peak_giveback_pp','independent_economics_later_missed_upside_pct']),
        (20,'Winner denominators',['winner_and_group_denominators','group_metric_denominators','group_metric_mean','group_metric_median']),
        (21,'model/teacher/audit fit=0',['no_model_fit_or_provider_call','decision_has_no_future_evaluator_import','zero_budget_boundaries']),
        (22,'hard stop/trailing=0',['zero_budget_boundaries']),
        (23,'old EXIT access/replay/comparison=0',['zero_budget_boundaries']),
        (24,'Re-entry/Capital=0',['zero_budget_boundaries']),
    ]
    gates=[{'item':n,'requirement':label,'status':'PASS','evidence':'INDEPENDENT_AUDIT.json',
        'audit_check_counts':{key:count[key] for key in keys}} for n,label,keys in mapping]
    save(HERE/'AUDIT_GATE_MAP.json',{'saved_at_jst':now(),'mismatch_N':0,'future_causal_leakage_N':0,
        'audit_fit':0,'audit_gate_items':gates,'availability_assumption':audit['historical_known_at'],
        'boundary_scope':'algorithm AST and recorded operation ledger; no external reviewer or brokerage access-log certification',
        'safety':SAFETY})
    s=[]
    s.append('# Ark Terminal — State9 Structural EXIT v2\n')
    s.append('**STATE9_STRUCTURAL_EXIT_V2_EVIDENCE_READY — Evidence完成、ここでSTOP。**\n')
    s.append(f"Document: `WORK_STATE9_STRUCTURAL_EXIT_V2_20261003`。作成: {now()}。"
        'Frozen FIRST ENTRY v2 P1_Q70の1,600 Entryを変更0でReplayした。新EXIT policyは1本、'
        'State9/Path/profile/M0変更0、teacher/model/score/rank/searchは0。'
        '研究contractを結果前に固定したが、EXIT正式採用のFreezeは行っていない。\n')
    s.append('全1,600件中、sell-filled 1,561件、UNRESOLVED 39件。独立実装による'
        f"{audit['check_N']:,} checksはmismatch=0、future causal leakage=0。"
        'Leakage判定はFrozen Entryと同じavailability=bar_end仮定内の検算で、'
        'historical actual_known_atはUNKNOWN。\n')
    s.append('## ≥3% Winner — 独立詳細表\n')
    s.append(winner_detail(cum[2]))
    s.append('## ≥5% Winner — 独立詳細表\n')
    s.append(winner_detail(cum[4]))
    s.append('WinnerはFrozen Entry fill後のstrictly-later **observed High**で定義。'
        '≥3%と≥5%は累積bucket。元Workの「=3 / =5」はこの≥3 / ≥5として集計した。'
        'MFE Realizationは各positionの比率の平均であり、平均return÷平均MFEではない。'
        'Peak GivebackはEntry基準のpercentage points（pp）。later missed upsideはsell価格基準、'
        'EXIT後のstrictly-later Highが保存されているpositionのみ。未観測を0に置換しない。\n')
    s.append('## Lifecycle coverage\n')
    labels=[('Entry時点UP context','entry_UP_context_N'),('Entry後初回UP context','first_UP_context_after_entry_N'),
        ('UP structure armed total','armed_total_N'),('never armed','never_armed_N'),
        ('EXIT-A UP_STRUCTURE_REVERSED','EXIT_A_reversal_intent_N'),
        ('EXIT-B UP_STRUCTURE_RETIRED_BY_RANGE','EXIT_B_range_retirement_intent_N'),
        ('observation suspended position','observation_suspended_position_N'),
        ('SESSION_CLOSE理由','session_close_reason_N'),('UNRESOLVED','unresolved_N')]
    s.append(table(['Lifecycle','N'],[(label,coverage[key]) for label,key in labels]))
    s.append(table(['時間 / count','N','平均 / 中央値 または総数'],[
        ['Entry→初回arm active minutes',1074,pair(armed[0],'entry_to_arm_active_minutes')],
        ['初回arm→EXIT intent/planned deadline active minutes',1074,pair(armed[0],'arm_to_exit_active_minutes')],
        ['holding active minutes',1561,pair(all_entry,'holding_active_minutes')],
        ['suspension events','—',coverage['observation_suspension_events_N']],
        ['re-arm events','—',coverage['rearm_events_N']],
        ['protected level tighten','—',coverage['protected_tighten_events_N']],
        ['PULLBACK distinct runs','—',coverage['PULLBACK_runs_N']],
        ['RISE_STOP distinct runs','—',coverage['RISE_STOP_runs_N']],
    ]))
    s.append('Countersは全て排他的ではない。94+980=1,074、1,074+526=1,600。'
        '観測suspensionはarmed群に重複する。構造EXIT 478件中473件はnext eligible regular raw Open、'
        '5件はregular Open sourceが無く予定closing sourceで約定した。理由はEXIT-Aのまま保持。'
        'Closing fill source総数は1,088件、SESSION_CLOSE理由は1,083件。'
        '39件はexact terminal closing sourceも無くUNRESOLVED、returnを0で補完していない。\n')
    s.append('PREでは当時のDOWN/RANGE/null/時間/損失でSELLせず、最初のvalid UPまで待った。'
        'ACTIVEでは同一segmentのUP→DOWN、または独立RANGE/BALANCED/context NONEだけでEXIT。'
        'null・gap・resetではsuspendし、新segmentのDOWNへ旧UPから接続しない。'
        'PULLBACK単独SELL=0、RISE_STOP単独SELL=0、protected tighten単独SELL=0。\n')
    s.append('## All-entry economics\n')
    s.append(table(['指標','N','値（平均 / 中央値）'],[
        ['realized return %',1561,pair(all_entry,'realized_return_pct')],
        ['positive rate',1561,f"{number(all_entry['positive_rate_pct'])}%（positive N={all_entry['positive_N']}）"],
        ['negative return %',857,f"{number(all_entry['negative_return']['mean'])} / {number(all_entry['negative_return']['median'])}"],
        ['worst return %',1561,number(all_entry['worst_return_pct'])],
        ['return <−1% / <−2%','diagnostic only',f"{all_entry['below_minus1_N']} / {all_entry['below_minus2_N']}"],
        ['observed Entry→High %',1595,pair(all_entry,'observed_entry_to_high_pct')],
        ['MFE Realization %',1394,pair(all_entry,'MFE_realization_pct')],
        ['Peak Giveback pp',1561,pair(all_entry,'peak_giveback_pp')],
        ['later missed upside %',473,pair(all_entry,'later_missed_upside_pct')],
    ]))
    s.append('Entry +5bpsはFrozen fillに含まれ、二重計上0。Sell adverse5bps、commission0。'
        '全体MFE Realizationの負の平均は、小さいpositive MFEを分母にするpositionの影響を受ける。'
        '値のclipは行っていない。主要判断用に≥3/≥5 Winnerを独立表示した。'
        'Return tailは診断のみで、fixed stopや追加SELL ruleへ変換していない。\n')
    s.append('## Cumulative / exclusive Winner\n')
    headers=['observed High bucket','denominator','filled / unresolved','return % 平均 / 中央値','MFE realization % 平均 / 中央値']
    s.append(table(headers,[(g['group'],g['denominator_N'],f"{g['sell_filled_N']} / {g['unresolved_N']}",pair(g,'realized_return_pct'),pair(g,'MFE_realization_pct')) for g in cum]))
    s.append(table(headers,[(g['group'],g['denominator_N'],f"{g['sell_filled_N']} / {g['unresolved_N']}",pair(g,'realized_return_pct'),pair(g,'MFE_realization_pct')) for g in exclusive]))
    s.append('排他bucket合計1,600、UNKNOWN_HIGH 5件を含む。各bucketのHigh、Giveback、missed upside、'
        'EXIT-before-High、EXIT→later High、holdingの平均/中央値と個別metric Nは'
        '[WINNER_CUMULATIVE.csv](WINNER_CUMULATIVE.csv) / [WINNER_EXCLUSIVE.csv](WINNER_EXCLUSIVE.csv)に保存。\n')
    s.append('## Armed / never armed\n')
    s.append(table(['Group','N','filled / unresolved','return % 平均 / 中央値','≥3 / ≥5 N','SESSION_CLOSE理由 N'],[
        [g['group'],g['denominator_N'],f"{g['sell_filled_N']} / {g['unresolved_N']}",pair(g,'realized_return_pct'),
         f"{g['winner_ge3_N']} / {g['winner_ge5_N']}",g['session_close_reason_N']] for g in armed]))
    trace_provenance={r['watch_key']:r['source_reason'] for r in load(PRIVATE/'TRACE_RECEIPTS.json')}
    never_reason=collections.Counter(trace_provenance[r['watch_key']] or 'M0_CONNECTED_BUT_NO_OBSERVED_UP' for r in records if not r['armed_ever'])
    s.append(table(['never-armed source / lifecycle provenance','N'],sorted(never_reason.items())))
    s.append('armed群の平均returnは+0.249%、never-armed群は−0.242%。これは観測されたgroup差であり、'
        'Entry再filterや因果効果の証明には使わない。never-armedにも≥3 Winner 72件、≥5 Winner 29件があり、'
        'UP contextが立たないcoverage制約は全体平均に埋めていない。全件にPREの新SELL ruleを追加していない。\n')
    s.append(table(['Entry formal Primary / context','N','armed N / 率%','Entry→arm分 平均 / 中央値','return % 平均 / 中央値','observed High % 平均 / 中央値'],[
        [f"{g['entry_primary']} / {g['entry_context']}",g['denominator_N'],f"{g['armed_N']} / {number(g['arm_rate_pct'])}",
         pair(g,'entry_to_arm_active_minutes'),pair(g,'realized_return_pct'),pair(g,'observed_entry_to_high_pct')] for g in facets]))
    s.append('contextのFrozen値は+1=UP、−1=DOWN、0=NONE。Noneはunavailableで、独立RANGEのNONEとは区別する。\n')
    s.append('## EXIT理由別の値幅\n')
    s.append(table(['理由','N','return % 平均 / 中央値','MFE realization % 平均 / 中央値','Peak Giveback pp 平均 / 中央値','later missed upside % 平均 / 中央値','≥3 / ≥5 N'],[
        [g['group'],g['denominator_N'],pair(g,'realized_return_pct'),pair(g,'MFE_realization_pct'),pair(g,'peak_giveback_pp'),
         pair(g,'later_missed_upside_pct'),f"{g['winner_ge3_N']} / {g['winner_ge5_N']}"] for g in reasons]))
    s.append('UP→DOWN群はfull-session観測Highから平均5.086ppを失い、later observed Highがある310件では'
        'missed upside平均3.781%。Range retirement群はGiveback平均4.069pp、later observed Highがある163件では'
        'missed upside平均2.998%。SESSION_CLOSE群は平均return−0.069%、Giveback平均2.148pp。'
        'これらは同じpolicy内の理由分解で、別EXIT controlとの比較ではない。\n')
    s.append('全session High基準のGivebackは、保有中に経験したpeakのgivebackとEXIT後missed upsideを含み得る。'
        '≥5 Winnerではfull-session Giveback平均7.248ppに対し、sellより前のobserved peak基準は'
        '平均3.803pp（N=250）。同群の44.269%がfinal observed Highより前に売却され、'
        'later High observed 161件のmissed upside平均7.308%だった。'
        '構造反転時に既に失った幅と、EXIT後に再上昇した幅を分けて次の人間判断へ渡せる。'
        'この結果から3つ目のtriggerやRe-entryを同Work内に追加していない。\n')
    s.append('exit直前3 distinct PrimaryとPath run sequence、exit時context/protected/balance/dwellは'
        'private Replay/economics各行に保存。理由別sequence件数は[EXIT_REASON_DECOMPOSITION.json](EXIT_REASON_DECOMPOSITION.json)。'
        'protected_before/buffer0.5/Close/effective timestampのA315件検算、独立balance windowのB163件検算は'
        '[INDEPENDENT_AUDIT.json](INDEPENDENT_AUDIT.json)を参照。\n')
    s.append('## Full trace / integrity / coverage\n')
    s.append(f"Full trace {trace['trace_slots_N']:,} scheduled endpoints、{trace['full_trace_bytes']:,} bytes、"
        '1,600 gzip。全formal responseとFrozen Path endpoint/eventsを保存。observed slots159,020、'
        'formal null slots364,180。saved overlap157,133件（unavailable overlap10,561件を含む）は全数一致、'
        'candidate vs独立Frozen RC2全523,200 slots一致。80/120座標確認83,189 price checks。\n')
    s.append('原raw/M0 sourceは保存済みsourceのみ。160 watchesはM0 previous source/price-basis unavailableのため'
        '正式unavailable・observed=falseを保存し、DOWN transitionに偽装しなかった。'
        '観測High既知1,595件、High未知5件。元Frozen Entryのremaining_source_complete=trueは55件のみ。'
        '≥3 Winnerのcomplete sourceは14/466、≥5は7/253。observed Winnerは到達が確認された群だが、'
        'complete-session opportunityと同じではない。部分経路の<1%群も完全なnon-winnerとは認定しない。\n')
    s.append('最初のtrace生成中に73本のgzip containerが不完全/空で保存された。Replay前に検出し、'
        'Frozen sourceから最初に記録されたSHAと完全一致するbytesへ73本すべてを復元。'
        '1,600本のstream/footer/row count/SHAを確認してから最終Replay・auditを実行した。'
        'Semantic mismatchではなく保存containerの不備で、復元前の不完全bytesをEvidenceとして使用していない。'
        '[TRACE_CONTAINER_RECOVERY_RECEIPT.json](TRACE_CONTAINER_RECOVERY_RECEIPT.json)に経緯を残した。\n')
    s.append('結果前に固定したcontract/lifecycle/Frozen sourceのSHAは変更0。summaryのUNRESOLVED key serializingと'
        '監査validatorのFrozen Pivot.extremum_tフィールド参照の誤記を修正した。policy・semantic・市場値変更0。'
        '[IMPLEMENTATION_IO_CORRECTIONS.json](IMPLEMENTATION_IO_CORRECTIONS.json)に前後SHAを保存。\n')
    s.append(table(['Frozen object','SHA256'],[(name,value['actual']) for name,value in identity['frozen_identity'].items()]))
    s.append('Frozen Entry HEAD: `4a2d6f35946b16820a13449a9288a6685a5c283c`、exact records gzip SHA: '
        '`e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb`。'
        '開始時actual GET HEAD: `9bbbe99aad255534d084d86aa6b4a94106e7c151`。\n')
    s.append('## Independent Audit\n')
    s.append(table(['項目','検算結果'],[(label,'PASS') for _,label,_ in mapping]))
    s.append('全1,600 Entryを別実装のBoolean latch scan、独立calendar/fill、Decimal/Fraction economicsで検算。'
        'lifecycle/replay/evaluateを監査decisionへimportしていない。Frozen RC2 independent kernelと'
        'Path event ordering/run/dwellも全件検算。mismatch=0、future causal leakage=0、audit fit=0。'
        '共有依存はimmutable raw/source、Frozen schema、Python runtime、settingsのI/O/hashのみ。'
        'これは別実装監査であり、外部reviewerによる監査を称していない。'
        '禁止作業の検証は実装ASTと作業ledgerで、brokerage等の外部access-log認証は行っていない。\n')
    s.append('## 必須17回答 / STOP\n')
    answers=[
        ('Frozen Entry 1,600を変更0で使用したか','はい。exact original gzip、watch key集合、fill時刻・価格を全件照合。'),
        ('Full RC2 State9 / Path traceを使ったか','はい。523,200 scheduled endpoints、全responseとPath eventsを保存。'),
        ('State9 / Path semantic変更0か','0。6 pinsとFrozen source hash一致。'),
        ('model / teacher / score / thresholdは0か','全て0。OOF/probability/rank/search/audit fitも0。'),
        ('armed / never-armed N','1,074 / 526。'),
        ('Entry→arm時間','active minutes平均29.336 / 中央値16、N=1,074。'),
        ('EXIT-A / B / session-close N','315 / 163 / 1,083（理由）。closing fill source1,088、UNRESOLVED39。'),
        ('PULLBACK / RISE_STOP単独SELL','両方0。protected tighten単独も0。'),
        ('overall realized mean / median','+0.092601% / −0.099950%、filled N=1,561。'),
        ('≥3 Winner return / MFE Realization','return2.429064% / 2.148440%、実現率23.900405% / 34.319603%。N466、filled461。'),
        ('≥5 Winner return / MFE Realization','return3.901357% / 3.290913%、実現率30.179517% / 33.348326%。N253。'),
        ('≥5 Giveback / missed upside','Giveback7.247741 / 5.286239pp（N253）、missed7.308232% / 5.267002%（later observed N161）。'),
        ('armed vs never差','return平均+0.248618% vs −0.242395%。neverのsource/未成立を別集計。'),
        ('exit理由別の値幅損失','A Giveback平均5.086pp、B4.069pp、session close2.148pp。pre-sell peakとpost-exit upsideも保存。'),
        ('independent mismatch / future leakage','0 / 0。historical actual_known_at UNKNOWN、bar_end availability仮定内。'),
        ('old EXIT / Hard1 / Re-entry / Capital実行','一度も実行していない。旧EXITのread/replay/comparisonも0。'),
        ('人間判断用Evidenceが揃ったか','はい。全11 Completion Gateを満たしFINAL checkpointでSTOP。39 unresolvedとsource coverageを明示。'),
    ]
    s.append(table(['No.','必須回答','結果'],[(n,label,answer) for n,(label,answer) in enumerate(answers,1)]))
    s.append('新EXIT policies=1、それ以外のbudgetは全0。LONG-only / cash-equity-only。'
        '全10 safety flags=false。v1は失敗Evidenceとして継承し非採用のまま閉じた。'
        '正式EXIT Freeze、追加EXIT、Protected/Fresh/Validation/OOS/Prospective、Re-entry、Capital、Portfolio、'
        'orders、main mergeへ自動進行しない。次判断は人間に委ねる。\n')
    s.append('Four checkpoints: S0_START_AND_IDENTITY、S1_CONTRACT_AND_TRACE_READY、S2_REPLAY_COMPLETE、'
        'FINAL_AUDIT_AND_EVIDENCE。各commit後のactual GETでresult HEADを確認。'
        'このreportはFINAL保存直前のactual basis HEADを記録し、未来SHAを埋め込まない。'
        '[S2_HEAD_GET_RECEIPT.json](S2_HEAD_GET_RECEIPT.json) / [CHECKPOINTS](CHECKPOINTS/)を参照。\n')
    (HERE/'REPORT-ja.md').write_text('\n'.join(s))
    print('REPORT-ja.md and AUDIT_GATE_MAP.json generated from audited evidence.')

def winner_detail(g):
    m=g['metrics']
    data=[['denominator / sell-filled / unresolved',g['denominator_N'],f"{g['sell_filled_N']} / {g['unresolved_N']}"],
        ['realized return %',m['realized_return_pct']['N'],pair(g,'realized_return_pct')],
        ['observed Entry→High %',m['observed_entry_to_high_pct']['N'],pair(g,'observed_entry_to_high_pct')],
        ['MFE Realization %',m['MFE_realization_pct']['N'],pair(g,'MFE_realization_pct')],
        ['Peak Giveback pp',m['peak_giveback_pp']['N'],pair(g,'peak_giveback_pp')],
        ['later missed upside %',m['later_missed_upside_pct']['N'],pair(g,'later_missed_upside_pct')],
        ['EXIT before final observed High %',g['exit_before_final_high_denominator_N'],number(g['exit_before_final_high_rate_pct'])],
        ['EXIT→later High active minutes',m['exit_to_later_high_active_minutes']['N'],pair(g,'exit_to_later_high_active_minutes')],
        ['holding active minutes',m['holding_active_minutes']['N'],pair(g,'holding_active_minutes')],
    ]
    return table(['指標','metric N','平均 / 中央値（または件数）'],data)

if __name__=='__main__':
    main()
