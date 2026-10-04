"""Fixed post-audit selection and Japanese handoff; no solver/replay/fit imports."""
from control import *


def fixed_selection(preservation, capital, independent):
    assert independent['status'] == 'PASS' and independent['mismatch_N'] == 0
    profiles = {}
    for arm in ARMS:
        q = preservation['profiles'][arm]
        e = capital['profiles'][arm]['economics']
        gates = dict(q['preservation_gates'])
        gates['P6_independent_mismatch0'] = True
        preservation_pass = all(gates.values())
        economic_gates = dict(capital['profiles'][arm]['economic_point_gates'])
        profiles[arm] = {
            'Preservation_gates': gates,
            'Preservation_PASS': preservation_pass,
            'Preservation_status': 'PRESERVATION_IMPROVED' if preservation_pass else 'PRESERVATION_MIXED',
            'Capital_point_gates': economic_gates,
            'Capital_PASS': preservation_pass and all(economic_gates.values()),
            'NORTH_STAR_HIT_DEVELOPMENT': e['north_star_hit_N'] > 0,
        }

    def winner_key(a):
        q = preservation['profiles'][a]
        e = capital['profiles'][a]['economics']
        return (-e['north_star_hit_N'], -e['rolling20_median'], -e['rolling20_arithmetic_mean'],
                -e['geometric_mean_daily_return'], -q['U5_funded'], -q['U10_funded'],
                q['funded_quality']['below2_rate'], e['max_drawdown'], ARMS.index(a))

    eligible = [a for a in ARMS if profiles[a]['Preservation_PASS'] and profiles[a]['Capital_PASS']]
    winner = min(eligible, key=winner_key) if eligible else None

    def diagnostic_key(a):
        q = preservation['profiles'][a]
        e = capital['profiles'][a]['economics']
        return (-q['U5_funded'], -q['U10_funded'], q['funded_quality']['below2_rate'],
                -e['rolling20_median'], ARMS.index(a))

    diagnostic = winner or min(ARMS, key=diagnostic_key)
    c = preservation['profiles'][diagnostic]['conservation']['U5']
    gaps = {'RANK_ADMISSION': c['RANK_BASE_REJECT'], 'CAPACITY_RESERVE': c['CAPACITY_RESERVE_REJECT'],
            'MAX3_ONLINE_OCCUPANCY': c['MAX3_FULL'], 'CASH_SIZING': c['CASH_OR_LOT']}
    priority = ['RANK_ADMISSION', 'MAX3_ONLINE_OCCUPANCY', 'CAPACITY_RESERVE', 'CASH_SIZING']
    bottleneck = min(gaps, key=lambda k: (-gaps[k], priority.index(k)))
    status = ('V8R1_NORTH_STAR_HIT' if winner and profiles[winner]['NORTH_STAR_HIT_DEVELOPMENT'] else
              'V8R1_CAPITAL_IMPROVED' if winner else
              'V8R1_PRESERVATION_ONLY' if any(p['Preservation_PASS'] for p in profiles.values()) else 'V8R1_NO_GO')
    selection = {'status': status, 'selectedCapitalCandidate': winner, 'diagnosticArm': diagnostic,
                 'NEXT_BOTTLENECK': bottleneck, 'observed_U5_exclusive_gaps': gaps,
                 'physical_unavoidable': 21, 'admission_ceiling_loss': 33,
                 'Admission_Oracle_to_runtime_gap': 116 - preservation['profiles'][diagnostic]['U5_funded']}
    assert selection == independent['independent_selection'], 'FINAL_SELECTION_MISMATCH_STOP'
    return selection, profiles


def table(head, rows_):
    return '\n'.join(['|' + '|'.join(head) + '|', '|' + '|'.join(['---'] * len(head)) + '|'] +
                     ['|' + '|'.join(map(str, row)) + '|' for row in rows_])


def pct(x):
    return f'{x * 100:.6f}%'


def yn(x):
    return 'PASS' if x else 'FAIL'


def report(selection, gates, preservation, capital, independent):
    saved = read(OUT / 'SAVED_REFERENCE_FREEZE.json')
    diagnostic = read(OUT / 'PPRANK_CASH_DIAGNOSTIC_RESULT.json')
    anatomy = read(V8 / 'BLOCKED_WINNER_ANATOMY.json')['aggregate']
    policy_freeze = read(OUT / 'B1_B2_SEMANTIC_FREEZE.json')
    names = ['v5 saved', 'v7 A1 saved', 'v7 A2 saved', 'B1', 'B2']
    all_economics = [saved['v5_benchmark']] + list(saved['v7_saved_profiles'].values()) + [capital['profiles'][a]['economics'] for a in ARMS]
    q = [preservation['profiles'][a] for a in ARMS]
    e = [capital['profiles'][a]['economics'] for a in ARMS]
    parts = ['# Capital v8R1 最終Report', '', '## A. North Star / rolling20', '',
             table(['Profile', '20d min', '20d mean', '20d median', '20d max', '2x hit'],
                   [[n] + [f'{x[k]:.10f}x' for k in ['rolling20_minimum', 'rolling20_arithmetic_mean', 'rolling20_median', 'rolling20_maximum']] +
                    [f"{x['north_star_hit_N']}/19 (0%)"] for n, x in zip(names, all_economics)]), '',
             f"最終status={selection['status']}。selectedCapitalCandidate=null。v5をCapital benchmarkとして保持する。",
             'North Starは¥1,000,000→¥2,000,000 / rolling20。全profileで2x=0/19。38 OOF Development sessionsを連結し、新B1/B2は各1回のみ実行した。',
             'これはITERATIVE_DEVELOPMENT_EVIDENCEであり、fresh/OOS成功ではない。19 rolling windowsは重複し、独立19標本ではない。', '',
             '## B. U5/U10 preservation', '',
             table(['Profile', 'U5/170', 'U10/67', 'Admission recovery U5/U10', 'Physical recovery U5/U10', '<2', 'Reserve U5', 'MAX3 U5', 'Rank reject U5'],
                   [['v5 saved', '50/170', '26/67', f'{pct(50/116)} / {pct(26/55)}', f'{pct(50/149)} / {pct(26/67)}', '38.666667%', '30', '28', '57'],
                    ['v7 A1 saved', '50/170', '27/67', f'{pct(50/116)} / {pct(27/55)}', f'{pct(50/149)} / {pct(27/67)}', '43.274854%', '0', '67', '46'],
                    ['v7 A2 saved', '51/170', '25/67', f'{pct(51/116)} / {pct(25/55)}', f'{pct(51/149)} / {pct(25/67)}', '41.875000%', '41', '26', '46']] +
                   [[n, f"{x['U5_funded']}/170", f"{x['U10_funded']}/67", f"{pct(x['Admission_U5_recovery'])} / {pct(x['Admission_U10_recovery'])}",
                     f"{pct(x['Physical_U5_recovery'])} / {pct(x['Physical_U10_recovery'])}", pct(x['funded_quality']['below2_rate']),
                     x['conservation']['U5']['CAPACITY_RESERVE_REJECT'], x['conservation']['U5']['MAX3_FULL'], x['conservation']['U5']['RANK_BASE_REJECT']]
                    for n, x in zip(['B1', 'B2'], q)]), '',
             'v5のRank reject 57は旧rank-pass U5=113からの差であり、新rank-native admissionの46とは別lineage。v5は保存済み結果のみで再replayしていない。', '',
             table(['Arm / target', 'FUNDED', 'RANK_BASE_REJECT', 'CAPACITY_RESERVE_REJECT', 'MAX3_FULL', 'CASH_OR_LOT', 'SAME_SYMBOL', 'EXECUTION_BLOCKED', 'OTHER', 'Total'],
                   [[n + ' ' + target] + list(x['conservation'][target][r] for r in
                    ['FUNDED', 'RANK_BASE_REJECT', 'CAPACITY_RESERVE_REJECT', 'MAX3_FULL', 'CASH_OR_LOT', 'SAME_SYMBOL', 'EXECUTION_BLOCKED', 'OTHER_EXPLICIT']) +
                    [sum(x['conservation'][target].values())] for n, x in zip(['B1', 'B2'], q) for target in ['U5', 'U10']]), '',
             table(['Arm / admission target', 'FUNDED', 'Reserve', 'MAX3', 'Cash/lot', 'Others', 'Total'],
                   [[n + ' ' + target, x['admission_conservation'][target]['FUNDED'], x['admission_conservation'][target]['CAPACITY_RESERVE_REJECT'],
                     x['admission_conservation'][target]['MAX3_FULL'], x['admission_conservation'][target]['CASH_OR_LOT'],
                     sum(x['admission_conservation'][target][k] for k in ['RANK_BASE_REJECT', 'SAME_SYMBOL', 'EXECUTION_BLOCKED', 'OTHER_EXPLICIT']),
                     sum(x['admission_conservation'][target].values())] for n, x in zip(['B1', 'B2'], q) for target in ['U5', 'U10']]), '',
             table(['Arm', 'Funded N', 'U5 capture', 'U10 capture', '<3', 'Medium3–<5', 'Funded/session'],
                   [[n, x['funded_quality']['N'], pct(x['U5_capture']), pct(x['U10_capture']), pct(x['funded_quality']['below3_rate']),
                     x['funded_quality']['Medium3_5_N'], f"{x['funded_per_session']:.6f}"] for n, x in zip(['B1', 'B2'], q)]), '',
             '## C. Cash-constrained pP diagnostic', '',
             f"{diagnostic['name']} = CERTIFIED / {diagnostic['canonical_status']}。", '',
             table(['Metric', 'Result'], [['Executable / runtime admission', '488 / 490'], ['Stage1 integer utility', diagnostic['stage1_utility']],
                   ['Stage2 selected N', diagnostic['stage2_selected_N']], ['Stage3 stable ordinal sum', diagnostic['stage3_stable_ordinal_sum']],
                   ['U5 / U10 / <2 N', f"{diagnostic['U5']} / {diagnostic['U10']} / {diagnostic['below2_N']}"],
                   ['<2 selected density', pct(diagnostic['below2_N']/diagnostic['stage2_selected_N'])], ['Exact minimum cash', '¥15,747.85'],
                   ['Integerization', 'scale=100; exact ticks; rounding=0'], ['MAX3 / same-symbol violations', '0 / 0'],
                   ['Primary stages', '3/3 OPTIMAL'], ['Optional NO-GOOD', '1; alternative Stage3-optimal identity infeasible'], ['Independent objective / cash / identity mismatch', '0']]), '',
             '未来pP arrivalsとFrozen releaseを知るminimum-lot 100株scheduleの診断であり、U5 upper boundではない。U5/U10/realized PnLはobjectiveに使っていない。売却価格はcash feasibilityにのみ使う。結果・selected identity・diagnostic statusはruntimeとB1/B2 tableへ一切渡していない。',
             'cash-relaxed optimumの後付けwitnessではなく、累積cash、MAX3、same-symbolを最初からMILP hard constraintへ入れた。全38 sessionを連結し、same-minute confirmed exits→Entry buysの順序でDecimal exact certificationを行った。', '',
             table(['Profile', 'Selected/funded N', 'sum r', 'pP utility efficiency', 'U5', 'U10', '<2 N'],
                   [['Clairvoyant diagnostic', 234, f"{diagnostic['sum_r']:.12f}", '100%', 81, 38, 92]] +
                   [[n, x['funded_quality']['N'], f"{x['sum_r']:.12f}", pct(x['runtime_rank_utility_efficiency']), x['U5_funded'], x['U10_funded'], x['funded_quality']['below2_N']]
                    for n, x in zip(['B1', 'B2'], q)]), '',
             'Diagnostic training-r decile（10が最高）: 10=93、9=58、8=39、7=23、6=21。後述のcommon-cohort raw-pP decile（1が最高）とは定義を混同しない。', '',
             '## D. Preservation Gate', '',
             table(['Arm', 'P1 U5>50', 'P2 U10≥26', 'P3 <2≤38.666667%', 'P4 U5/116>50/116', 'P5 integrity', 'P6 independent', 'All'],
                   [[n] + [yn(v) for v in gates[a]['Preservation_gates'].values()] + [yn(gates[a]['Preservation_PASS'])]
                    for n, a in zip(['B1', 'B2'], ARMS)]), '',
             'R11のP6=PENDING recordは上書きせず、R13独立監査PASSをFINAL_GATE_RESULT.jsonで追記解決した。両armはP1–P4がFAIL、P5/P6がPASSで採用不可。', '',
             '## E. Capital Gate', '',
             table(['Arm', 'Preservation', '20d median>1.1991541915', '20d mean>1.1906460126', 'Daily geom>1.032420041%', 'Capital'],
                   [[n, yn(gates[a]['Preservation_PASS'])] + [yn(gates[a]['Capital_point_gates'][k]) for k in ['rolling20_median', 'rolling20_mean', 'daily_geometric']] + [yn(gates[a]['Capital_PASS'])]
                    for n, a in zip(['B1', 'B2'], ARMS)]), '',
             '両armともCapital3条件も全FAIL。診断solverの修正成功はpolicy成功を意味しない。旧v8はV8_CONTRACT_FAILの固定STOPを維持し、旧v8でB1/B2は未評価だった事実を0成績に置換しない。', '',
             '## F. Physical / Admission / Runtime waterfall', '',
             table(['Stage', 'U5', 'Difference'], [['Primary potential winners', 170, '—'], ['Saved Physical Oracle', 149, 'Physical unavoidable=21'],
                   ['Saved Admission Oracle', 116, 'Admission ceiling loss=33'], ['B1 runtime funded', 42, 'Admission Oracle→runtime=74'],
                   ['B2 diagnostic arm runtime funded', 47, 'Admission Oracle→runtime=69']]), '',
             'Counterfactual waterfall: B2は170 = 21 + 33 + 69 + 47。保存済みv7 Oracleは再solveしていない。',
             'Observed exclusive waterfall: B2は170 = Rank reject46 + Reserve55 + MAX3 13 + cash/lot9 + funded47。counterfactual21/33とobserved46/55/13/9を足してはならない。',
             'Admission実候補U5=124とAdmission Oracle116の差8はadmission内部のphysical overlap等による。Admission実候補からのmiss77とOracle→runtime gap69も別定義。U10は67→67 Physical→55 Admission→24 B2 funded。', '',
             '## G. False Reserve / Bad Fill', '',
             table(['Arm', 'False Reserve U5', 'False Reserve U10', 'Bad Fill blocked U5/U10', 'Higher-pP blocked by lower held U5/U10'],
                   [[n, x['FALSE_RESERVE_U5'], x['FALSE_RESERVE_U10'], f"{x['BAD_FILL_BLOCKED_U5_unique_missed']} / {x['BAD_FILL_BLOCKED_U10_unique_missed']}",
                     f"{x['HIGHER_P5_BLOCKED_BY_LOWER_HELD_U5']} / {x['HIGHER_P5_BLOCKED_BY_LOWER_HELD_U10']}"] for n, x in zip(['B1', 'B2'], q)]), '',
             'Bad Fillは<2 holdingがhigher-pP winnerのMAX3_FULL missと重なったunique missed candidate数。単一の因果責任、replacement利益、EXIT変更の正当化を意味しない。',
             'B2はB1よりReserve U5を59→55へ4件減らしfunded U5を42→47へ増やしたが、v5の50/26とcontamination guardを超えなかった。', '',
             '### 保存済み51 higher-pP blocked U5 anatomy（再生成0）', '',
             table(['Metric', 'Saved result'], [['Events / blocked U10', '51 / 16'], ['Lowest-pP blocker <2 / U5 / U10 event N', '25 / 14 / 6'],
                   ['Lowest-pP blocker unique N', 31], ['Blocker age median wall minutes', anatomy['blocker_age_wall_minutes']['median']],
                   ['Actual overlap median wall minutes', anatomy['actual_overlap_wall_minutes']['median']], ['pP gap median', f"{anatomy['pP_gap']['median']:.12f}"],
                   ['Miss hour09/10/11/12/13/14', '2 / 21 / 5 / 12 / 8 / 3']]), '',
             '旧v8のBLOCKED_WINNER_ANATOMY.json/.csvをread-only authorityとして再利用。anatomy結果からB1/B2仕様は変更していない。', '',
             '## H. Slot quality', '',
             table(['Arm', 'Slot', 'N', 'U5', 'U10', '<2 N / rate', '<3 N / rate', 'Medium3–<5'],
                   [[n, slot, v['N'], v['U5'], v['U10'], f"{v['below2_N']} / {pct(v['below2_rate'])}",
                     f"{v['below3_N']} / {pct(v['below3_rate'])}", v['Medium3_5_N']]
                    for n, x in zip(['B1', 'B2'], q) for slot, v in x['slot_quality'].items()]), '',
             '## I. pP decile / Entry hour', '',
             'Common supported 1028候補をfrozen raw pP DESC / Entry timestamp ASC / symbol ASCへ並べたdecile。1が最高。各cellはfunded N / U5 / U10。runtime thresholdには使わない。', '',
             table(['pP decile', 'B1 N / U5 / U10', 'B2 N / U5 / U10'],
                   [[i] + [' / '.join(str(x['pP_deciles'][str(i)]['funded'][k]) for k in ['N', 'U5', 'U10']) for x in q] for i in range(1, 11)]), '',
             table(['Entry hour JST', 'B1 N / U5 / U10', 'B2 N / U5 / U10'],
                   [[h] + [' / '.join(str(x['Entry_hours'][str(h)]['funded'][k]) for k in ['N', 'U5', 'U10']) for x in q] for h in range(9, 16)]), '',
             table(['Arm', 'Funded r mean / median', 'Missed-U5 r mean / median'],
                   [[n, f"{x['mean_funded_r']:.12f} / {x['median_funded_r']:.12f}", f"{x['mean_missed_U5_r']:.12f} / {x['median_missed_U5_r']:.12f}"]
                    for n, x in zip(['B1', 'B2'], q)]), '',
             '## J. Final38 / MaxDD / utilization（Secondary）', '',
             table(['Metric', 'v5 saved', 'v7 A1 saved', 'v7 A2 saved', 'B1', 'B2'],
                   [[label] + [fmt(x[k]) if k in x else '—（saved benchmark概要に未収録）' for x in all_economics]
                    for label, k, fmt in [('Daily geometric', 'geometric_mean_daily_return', pct), ('Daily arithmetic', 'arithmetic_mean_daily_return', pct),
                       ('Daily median', 'median_daily_return', pct), ('Final38', 'final_equity', lambda v: f'¥{v:,.2f}'),
                       ('Total return', 'total_return', pct), ('Minute MTM MaxDD', 'max_drawdown', pct), ('Utilization mean', 'utilization_mean', pct),
                       ('Utilization median', 'utilization_median', pct), ('Idle fraction mean', 'mean_idle_cash_fraction', pct),
                       ('Idle cash mean', 'idle_cash_mean_jpy', lambda v: f'¥{v:,.2f}'), ('Turnover BUY+SELL', 'turnover_cash_jpy', lambda v: f'¥{v:,.2f}'),
                       ('Recycled cash used', 'capital_recycling_used_jpy', lambda v: f'¥{v:,.2f}'), ('Funded/session', 'avg_funded_per_session', lambda v: f'{v:.6f}')]]), '',
             'Final38は38 Development sessionsの連結結果であり「1か月成績」ではない。全38 day COMPLETE / execution unresolved=0。daily38・rolling20の19全windowは各arm RESULT.jsonへ保存し、同一ledgerから計算した。MaxDDはminute MTMを使用し、hard gateには追加していない。', '',
             '## K. Independent Audit / count / Safety', '',
             table(['Check', 'Result'], [['Synthetic diagnostic preflight', '12/12 PASS'], ['Causal canary', '43/43 PASS'],
                   ['Pre-main independent policy audit', '37,458 checks / 3,920 action cases / mismatch=0'], ['Full independent audit', f"{independent['check_N']:,} checks / mismatch=0"],
                   ['Money / quantity tolerance', '0 (exact)'], ['Score/r/pressure tolerance', '≤1e-12; observed maximum delta=0'],
                   ['New Rank / Slot ML fits; teacher regeneration', '0 / 0 / 0'], ['Primary cash diagnostic packages / independent', '1 / 1'],
                   ['Optional uniqueness NO-GOOD', '1'], ['B1 / B2 primary replays', '1 / 1'], ['Independent full recalculations', '2'],
                   ['v5/v6/v7/old-v8 replay; old Oracle solve', '0; 0'], ['Threshold sweep / grid / B3 / retune / rescue', '0 / 0 / 0 / 0 / 0'],
                   ['Orders / provider requests / Claude / main merge / force push', '0 / 0 / 0 / 0 / 0'], ['Protected/Holdout/Fresh/Validation/OOS/Prospective open', '0'],
                   ['Cash negative / MAX3 / same-symbol / after15:20 funded violations', '0 / 0 / 0 / 0'], ['Leakage / future test access / identity mismatch', '0 / 0 / 0']]), '',
             '独立実装はPrimary runtime/replay/evaluatorをimportせずraw sourceからpolicy、quantity、Fraction cash、MTM、preservation、rolling20、selectionを再計算した。同じmarket source/Scipy backendを使うため外部source truthの独立証明ではない。',
             'Safety: executionAllowed=false; brokerWriteAllowed=false; excelOrderWriteAllowed=false; rssOrderFunctionAllowed=false; liveTradingAllowed=false; paperTradingAllowed=false; automaticPromotionAllowed=false; productionUpdateAllowed=false; transmitted=false; productionReady=false。',
             '本新cycleの未完了table buildで欠損release fieldはUNKNOWN/非completeとして除外するinput parserを修正した。既存teacherを書換えずtenureのknown-release contractを維持し、完成済みtable/diagnostic/replayを再生成していない。',
             'Rank contract SHA256=6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518。',
             'pP score stream SHA256=14c48e61554bd58c6d5289b410d6a8c859cb37efd0dbc5d98987fcb440aac2ed。',
             'Band map SHA256=bbe73fd89a4f045fff7de768877aed670c8d343c026ac94557af151e643eef1d。',
             'Frozen B1/B2 runtime.py SHA256=f9232d8d501832c15344f7f5f125dab929814c5285406c3a932a027c498aa32e（旧v8とbyte exact）。POLICY_B1_B2_PRECOMMIT source/hashはB1_B2_SEMANTIC_FREEZE.jsonへ保存済み。',
             'Main前claimはR9のcommit→actual GET→single executionで管理し、各checkpointのHEAD/tree/JST/actual GET receiptをappend-onlyで保存した。old branchとold Evidenceはread-only。', '',
             '## L. Next Bottleneck / fixed handoff', '',
             table(['Diagnostic arm B2: observed exclusive actionable U5 miss', 'Count'], [[k, v] for k, v in selection['observed_U5_exclusive_gaps'].items()]), '',
             'NEXT_BOTTLENECK=CAPACITY_RESERVE（55）。事前固定ruleでobserved exclusive miss最大countを選んだ。Physical unavoidable21 / Admission ceiling loss33 / Admission Oracle→runtime gap69は別counterfactualとして併記する。',
             'pP clairvoyantのU5=81は解釈補助のみでbottleneck選定には使用していない。新Rankを戻す根拠でもない。RankはEXISTING_MOVE_P5のまま保持し、Capitalはv5 benchmarkを保持する。',
             'このcycleでB3、0.5/support10/median/bucket、Admission、Rank、Selector/Entry/EXITを変更しない。次Workは独立した新指示が必要。Fresh開封、MAX4/MAX5、replacement、main merge、ordersは行わない。R15で固定STOP。', '',
             '```text', 'selectedRankCandidate = EXISTING_MOVE_P5', 'selectedCapitalCandidate = null',
             'diagnosticArm = TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1', 'NEXT_BOTTLENECK = CAPACITY_RESERVE',
             'fresh_OOS_claim = false', 'productionReady = false', 'CURRENT_STATE = CAPITAL_V8R1_R15_CLOSURE_FIXED_STOP', '```', '']
    return '\n'.join(parts)


def main():
    preservation = read(OUT / 'PRESERVATION_RESULT.json')
    capital = read(OUT / 'CAPITAL_ROLLING20_RESULT.json')
    independent = read(OUT / 'INDEPENDENT_AUDIT.json')
    selection, gates = fixed_selection(preservation, capital, independent)
    counts = {'B1_replay': 1, 'B2_replay': 1, 'primary_pP_diagnostic_solve': 1,
              'independent_pP_diagnostic_solve': 1, 'uniqueness_no_good_solve': 1, 'independent_full_recalculations': 2}
    save(OUT / 'FINAL_GATE_RESULT.json', {'exact_jst': now(), 'prior_P6_PENDING_preserved': True,
         'independent_audit_sha256': sha(OUT / 'INDEPENDENT_AUDIT.json'), 'profiles': gates, 'Safety': SAFETY})
    save(OUT / 'WINNER_AND_NEXT_BOTTLENECK.json', {'exact_jst': now(), **selection,
         'selectedRankCandidate': 'EXISTING_MOVE_P5', 'retainedCapitalBenchmark': 'V5_FROZEN_REFERENCE',
         'source_rule_sha256': sha(OUT / 'FINAL_SELECTION_RULE_PRECOMMIT.json'),
         'final_gate_sha256': sha(OUT / 'FINAL_GATE_RESULT.json'), 'independent_selection_mismatch': 0,
         'fresh_OOS_claim': False, 'productionReady': False, 'Exposure': 'ITERATIVE_DEVELOPMENT_EVIDENCE',
         'counts': COUNTS | counts, 'Safety': SAFETY})
    with (OUT / 'REPORT_FINAL-ja.md').open('x', encoding='utf-8') as f:
        f.write(report(selection, gates, preservation, capital, independent))
    checkpoint('R14_WINNER_AND_BOTTLENECK', 'CAPITAL_V8R1_R14_WINNER_AND_BOTTLENECK',
               ['R0–R13', 'final gates resolved append-only', 'fixed winner/bottleneck', 'REPORT_FINAL-ja.md'],
               selection, 'Private delivery / closure only; no further research; R15 fixed STOP', counts)
    print(json.dumps(selection))


if __name__ == '__main__':
    main()
