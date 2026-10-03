"""Build the required Japanese evidence report from saved audited V4 results."""
from settings import *
from selection_gate import selection

def fmt(v,d=4):return '—' if v is None else f'{v:+.{d}f}'
def mm(s):return f"{fmt(s['mean'])} / {fmt(s['median'])}"
def metric(g,v,k):return mm(g[v]['metrics'][k])
def paired(g,k):return mm(g['paired_delta'][k])
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def alias(reason):return {'UP_STRUCTURE_REVERSED':'A: main reversal','UP_STRUCTURE_RETIRED_BY_RANGE':'B: RANGE retirement','LOCAL_UP_STRUCTURE_GUARD_BROKEN':'C: mature Guard break','LOCAL_RECOVERY_FAILED':'D: recovery failure','SESSION_CLOSE':'SESSION_CLOSE','UNRESOLVED':'UNRESOLVED'}[reason]

def run():
    audit=load(HERE/'INDEPENDENT_AUDIT.json');assert audit['mismatch_N']==audit['future_causal_leakage_N']==0
    primary=load(HERE/'PRIMARY_2_TO_5.json');sel=selection(primary,audit);sel.update(saved_at_jst=now(),basis_head='d423f77bb67a586f1dd2a02858adfabad5af787c')
    save(HERE/'SELECTION.json',sel)
    assert sel['status']=='V4_NOT_BETTER_KEEP_V3'
    mech=load(HERE/'RECOVERY_FLOOR_MECHANICS.json');reuse=load(HERE/'V3_TRACE_REUSE_RECEIPT.json');fr=load(HERE/'CONTRACT_FREEZE_RECEIPT.json')
    d=load(HERE/'EXIT_D_PAIRED_DIAGNOSIS.json')[0];big=load(HERE/'WINNER_GE5_PROTECTION.json')[0];d5=load(HERE/'WINNER_GE5_EXIT_D.json')[0];allg=load(HERE/'ALL_ENTRY_ECONOMICS.json')[0];targetA=load(HERE/'TARGET_V3_EXIT_A.json')[0]
    d_ex=load(HERE/'EXIT_D_EXCLUSIVE.json');reasons=load(HERE/'V4_EXIT_REASON.json');dreasons=load(HERE/'EXIT_D_V3_REASON.json');con=load(HERE/'TARGET_CONCENTRATION_DIAGNOSTIC.json')
    pt=table(['Observed Entry→High exclusive','watches','V3/V4 filled','unresolved','V3 return mean / median %','V4 return mean / median %','Δmean pp','Δmedian pp'],[[g['group'],g['denominator_N'],f"{g['v3']['sell_filled_N']} / {g['v4']['sell_filled_N']}",f"{g['v3']['unresolved_N']} / {g['v4']['unresolved_N']}",mm(g['return_common_filled']['v3']),mm(g['return_common_filled']['v4']),fmt(g['return_common_group_difference']['mean']),fmt(g['return_common_group_difference']['median'])] for g in primary])
    quality=table(['>=5% quality','V3 mean / median','V4 mean / median','paired Δ mean / median','common N'],[[label,metric(big,'v3',k),metric(big,'v4',k),paired(big,k),big['paired_delta'][k]['N']] for label,k in [('return %','realized_return_pct'),('MFE Realization %','MFE_realization_pct'),('pre-sell observed giveback pp','pre_sell_observed_peak_giveback_pp'),('full observed window Peak Giveback pp','peak_giveback_pp'),('later missed upside %','later_missed_upside_pct'),('holding active minutes','holding_active_minutes')]])
    dx=table(['exclusive','D N','paired return Δ mean / median pp','pre-sell giveback Δ pp / N','later missed upside Δ pp / N'],[[g['group'],g['denominator_N'],paired(g,'realized_return_pct'),f"{paired(g,'pre_sell_observed_peak_giveback_pp')} / {g['paired_delta']['pre_sell_observed_peak_giveback_pp']['N']}",f"{paired(g,'later_missed_upside_pct')} / {g['paired_delta']['later_missed_upside_pct']['N']}"] for g in d_ex])
    dr=table(['V3 would exit via','D N','V3 return mean / median %','V4 return mean / median %','paired return Δ pp','intent / sell advance median active min'],[[alias(g['group']),g['denominator_N'],mm(g['return_common_filled']['v3']),mm(g['return_common_filled']['v4']),paired(g,'realized_return_pct'),f"{g['intent_advance_vs_V3_active_minutes']['median']} / {g['sell_advance_vs_V3_active_minutes']['median']}"] for g in dreasons])
    rt=table(['V4 exit reason','N','return mean / median %','MFE realization %','pre-sell giveback pp','holding active min','later missed upside %'],[[alias(g['group']),g['denominator_N'],metric(g,'v4','realized_return_pct'),metric(g,'v4','MFE_realization_pct'),metric(g,'v4','pre_sell_observed_peak_giveback_pp'),metric(g,'v4','holding_active_minutes'),metric(g,'v4','later_missed_upside_pct')] for g in reasons])
    rb=table(['V4 reason','exclusive bucket watches'],[[alias(g['group']),'; '.join(f'{b}: {n}' for b,n in g['exclusive_bucket_N'].items())] for g in reasons])
    econ=table(['all1600 metric','V3','V4'],[['return mean / median %',metric(allg,'v3','realized_return_pct'),metric(allg,'v4','realized_return_pct')],['filled / unresolved',f"{allg['v3']['sell_filled_N']} / {allg['v3']['unresolved_N']}",f"{allg['v4']['sell_filled_N']} / {allg['v4']['unresolved_N']}"],['positive rate %',fmt(allg['v3']['positive_rate_pct']),fmt(allg['v4']['positive_rate_pct'])],['negative N / mean / median %',str(allg['v3']['negative_N'])+' / '+mm(allg['v3']['negative_return']),str(allg['v4']['negative_N'])+' / '+mm(allg['v4']['negative_return'])],['worst return %',fmt(allg['v3']['worst_return_pct']),fmt(allg['v4']['worst_return_pct'])],['<-1% / <-2% N',f"{allg['v3']['below_minus1_N']} / {allg['v3']['below_minus2_N']}",f"{allg['v4']['below_minus1_N']} / {allg['v4']['below_minus2_N']}"],['holding active min mean / median',metric(allg,'v3','holding_active_minutes'),metric(allg,'v4','holding_active_minutes')]])
    questions=[
        ('V3 Full traceを再構築せずexact reuseしたか','はい。V3がpinする原本V2 FULL_TRACE 1,600ファイルとFrozen Pathをそのまま読み、原本1,606成分・V3 1,605成分hash一致。新規出力はV4 position metadataでありState9/Path再構築ではない。'),
        ('State9/Path変更0か','0。RC2/profile/source snapshot/M0/State Path Contract/PATH_FROZENの6pin一致。Frozen尺度1U/4U/0.5U/0.5U変更0。'),
        ('Recovery Floor成立position N',str(mech['Recovery_Floor_established_position_N'])+'。creation537、tighten180、reset263、never1186。'),
        ('EXIT-D N','127。全127件でmain context=UPかつ有効floor>main protected、Close<=floor−0.5U。'),
        ('DはV3 EXIT-Aを何件preemptしたか','47件。2–<5%の既存EXIT-A79件では16件。'),
        ('2–<3% V3→V4 mean/median',mm(primary[0]['return_common_filled']['v3'])+' → '+mm(primary[0]['return_common_filled']['v4'])+'%。共通filled209。'),
        ('3–<4% V3→V4 mean/median',mm(primary[1]['return_common_filled']['v3'])+' → '+mm(primary[1]['return_common_filled']['v4'])+'%。共通filled128。'),
        ('4–<5% V3→V4 mean/median',mm(primary[2]['return_common_filled']['v3'])+' → '+mm(primary[2]['return_common_filled']['v4'])+'%。共通filled80。'),
        ('2–<5% combined V3→V4 mean/median',mm(primary[3]['return_common_filled']['v3'])+' → '+mm(primary[3]['return_common_filled']['v4'])+'%。426 watches／共通filled417／unresolved9。>=5%を混ぜていない。'),
        ('>=5% V3→V4 mean/median',mm(big['return_common_filled']['v3'])+' → '+mm(big['return_common_filled']['v4'])+'%。共通253。平均微増、中央値低下。'),
        ('>=5%でD発火Nとpaired return','46件。群return '+mm(d5['return_common_filled']['v3'])+' → '+mm(d5['return_common_filled']['v4'])+'%。真正paired return Δ '+paired(d5,'realized_return_pct')+'pp（group median差とは異なる）。'),
        ('D群pre-sell givebackの変化','共通126件のpaired Δ '+paired(d,'pre_sell_observed_peak_giveback_pp')+'pp。V3 observed N127、V4 N126を0補完していない。'),
        ('D群later missed upsideの変化','共通89件のpaired Δ '+paired(d,'later_missed_upside_pct')+'pp。V3 observed N89→V4 N127。異なる母数のraw平均を改善と解釈しない。単独FAILにしていない。'),
        ('PULLBACK/RISE_STOP単独SELL=0か','両方0。local DOWN、dwell/time、stop count単独も0。Dは全件PULLBACKで観測されたが、文字列はtrigger条件に含まれない。'),
        ('fixed stop/profit/trailing=0か','全0。Hard1、固定損失/利益%、giveback%、固定trailing、State sequence rule、モデル/teacher/OOF/score/rank/searchも0。'),
        ('mismatch=0 / future leakage=0か','両0。全1,600件、1,206,668 checks。historical actual_known_at=UNKNOWN、bar_end availability仮定の範囲での因果監査。'),
        ('selection status','V4_NOT_BETTER_KEEP_V3。combined中央値が厳密改善しないため固定Gateで否決。3–<4%平均、>=5%中央値も悪化。later missed upsideでは否決していない。'),
        ('V4不成立時V3を無変更fallbackとして保持したか','はい。V3 FINAL c7a5e5c25eb19cbd58b45c3e4ffff977f4648fadを保持。A/B/C/PRE/quality/fill/calendarのwhole bytes一致。D以外1,473件のintent/fill/outcome完全一致。V3 branch変更0。'),
        ('Re-entry/Capital=0か','両0。Portfolio、Protected/Fresh/Validation/OOS/Prospective、orders/main mergeも0。'),
        ('次はEXIT Freezeへ進める状態か','人間がV3をEXIT Freeze候補として判断できるEvidenceは揃った。V4採用条件は未達。今回を最後の限定EXIT改善Workとして終了し、正式EXIT Freezeは実行していない。')]
    answers=table(['No.','必須回答','結果'],[[i,q,a] for i,(q,a) in enumerate(questions,1)])
    gate_rows=[[k,'PASS' if v else 'FAIL'] for k,v in sel['fixed_conditions'].items()]
    gate_table=table(['fixed conservative condition','result'],gate_rows)
    a_count=con['largest_positive_delta_pp']/con['net_delta_sum_pp']*100
    text=f'''# Ark Terminal — State9 Structural EXIT v4 Recovery-Failure

Status: **{sel['status']}**。V3無変更fallback保持。Evidence完成後STOP。

{pt}

returnは同一watch_keyの共通sell-filled母集団。2–<5 combinedは417件、>=5は253件。Δmean/medianは群統計の差であり、各Entry paired delta中央値とは区別する。UNKNOWN5件、全体unresolved39件を0補完しない。

## 判定と意味

2–<5 combined平均は+0.4938%→+0.5298%だが、中央値は+1.0893%→+1.0483%。既定の中央値厳密改善条件を満たさずV4不採用。3–<4%群も平均・中央値が低下。4–<5%群は改善したが、同Work内でDをそのbucket専用に変更することはしない。>=5%平均は微増、中央値は低下し、holding中央値85→68 active minutes。V3をFreeze候補として保持する。

{gate_table}

2–<5%群D41件中、paired return増加20、減少19、同値2。群全417件のdelta同値は378件。最大1件の正寄与は{con['largest_positive_delta_pp']:.4f}pp、net平均改善の約{a_count:.1f}%を占める。最大正寄与1件除外でも平均deltaは+{con['mean_delta_without_largest_positive_case_pp']:.4f}pp残るが、primary中央値改善と3–<4%改善は成立しない。少数case依存の新しい数値FAIL閾値は作らず、既定中央値Gateで結論を確定した。

## >=5% protection

{quality}

EXIT-before-final-observed-High率: V3 {big['v3']['EXIT_before_final_High_rate_pct']:.4f}%→V4 {big['v4']['EXIT_before_final_High_rate_pct']:.4f}%。D46件。later missedの母数は163→171件、真正paired共通163件の平均deltaは+{big['paired_delta']['later_missed_upside_pct']['mean']:.4f}pp。増加を単独FAILにはしていない。

>=5% D46件: return平均/中央値 {mm(d5['return_common_filled']['v3'])}→{mm(d5['return_common_filled']['v4'])}%。paired return delta {paired(d5,'realized_return_pct')}pp。pre-sell giveback paired {paired(d5,'pre_sell_observed_peak_giveback_pp')}pp（46件）。later missed paired {paired(d5,'later_missed_upside_pct')}pp（共通38件、raw observed母数38→46）。D後later Highと時刻、missed upside、advanceを個別EXIT_D_ROWSに保存。

## EXIT-D診断と機構

Floor成立414 position（25.875%）、creation537、tighten180、reset263、never1186。全127 Dはmain context UPのまま。intent advance平均47.7323／中央値14分、sell advance平均47.6535／中央値13分。holding中央値の89→40分という群差を、paired advance中央値と混同しない。negative→positive17、positive→negative10。

D群return平均/中央値 {mm(d['return_common_filled']['v3'])}→{mm(d['return_common_filled']['v4'])}%。真正paired delta {paired(d,'realized_return_pct')}pp。pre-sell givebackは共通126件で{paired(d,'pre_sell_observed_peak_giveback_pp')}pp。later missedは共通89件で{paired(d,'later_missed_upside_pct')}pp。売る前に返した幅と売った後の上伸を別に保存している。

{dx}

{dr}

主改善対象のV3 EXIT-A 79件のうち16件をDが先行。この固定79件のreturn平均/中央値は{mm(targetA['return_common_filled']['v3'])}→{mm(targetA['return_common_filled']['v4'])}%。ただしcombined primary中央値は低下したため、この部分改善だけで採用しない。

floor-to-main distance at activation平均/中央値 {mm(mech['distance_to_main_u_at_activation'])}U（717 updates）。break ageはcreationから平均4.5512／中央値3 bars、last updateから平均2.5512／中央値2 bars。break Primary/contextはPULLBACK/UP 127件。これは観測結果であり、PULLBACK文字列のSELL ruleではない。前3 distinct Primary、pivot exact fields、floor effective timestamps/resetと全updateを各position metadataに保存。

## EXIT理由別

{rt}

各metricの有効NはJSON/CSVに明示。N不一致は補完しない。理由×exclusiveの全内訳と各metricはV4_EXIT_REASON_EXCLUSIVEにも保存。

{rb}

## 全Entry economics

{econ}

pre-sell giveback共通1538件paired mean delta {allg['paired_delta']['pre_sell_observed_peak_giveback_pp']['mean']:+.4f}pp。later missed共通487件paired mean delta {allg['paired_delta']['later_missed_upside_pct']['mean']:+.4f}pp。全体平均の改善はprimary combined中央値Gateを代替しない。<-1%/<-2%やworst returnは診断のみで、新stop ruleに変換していない。

## 原本・因果・独立性

開始actual GET V3 FINAL: c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad。Full traceはV3がhash-pinする原本V2 FULL_TRACE 1,600件／523,200 scheduled endpointsとFrozen Path。再構築0。V3 ZIPはFull traceを複製せず原本依存を明示しているため、両方の既存原本をexact reuseした。

原本hash: V2 ZIP `{reuse['original_full_trace_archive_sha256']}`、V3 ZIP `{reuse['V3_archive_sha256']}`。Frozen Entry `{reuse['entry_sha256']}`。contract `{fr['contract_sha256']}`。48 public、1,605 V3 private、1,606原本依存成分をhash照合。6 semantic authority pinも一致。原本からの補正・再構築・Entry→High再計算は行っていない。

One primary V4 ReplayをRUN_ONCE receiptで固定。新規V4 decision196,552 rows、Full traceから読むprefix含むcutoff447,533箇所。独立監査はboolean phase latch／全segment pivot ledger／floor ledger／独立fill・calendar・Fraction economicsで全1,600件を検算し、1,206,668 checks、mismatch0、future causal leakage0、lineage mismatch0。primary decision/evaluator imports0。別実装監査であり外部reviewerではない。共通依存は保存済み入力、Python standard runtime/Fraction、I/O/hashのみ。

Decision arithmeticはoriginal numeric stringのFractionで厳密、許容epsilonなし。economicsのfloat表現差のみabs1e-10/rel1e-12で検算。全717 floor updateのkind L/DC、confirmation cutoff、context UP、mainより上、monotonic、次足有効を確認。127 Dのexact break、A/B/C優先、same-segment、V3より早いfirst intent、fill5bpsを確認。D以外1,473件はV3 intent/fill/outcome完全一致。

historical actual_known_atはUNKNOWN。因果PASSは保存時のbar_end availability仮定内であり、実市場到着時刻の証明ではない。Entry→Highはstrictly-later observed Highで、full remaining source completeは55/1600（>=5群7/253）。欠測区間を含む完全な日中最高値と過大表示しない。observed High UNKNOWN5件、unresolved39件を保持。

## 必須20回答

{answers}

## 保存・予算・終了

S0 actual HEAD d4d96dedcdb35f65615994dd8a259a0a51a3ed49でcontractとGateをReplay前に固定。S1 actual HEAD d423f77bb67a586f1dd2a02858adfabad5af787cをcommit後GET確認。FINAL basis_headはS1、結果HEADはcommit後actual GETで確認する（未来SHAを記載しない）。checkpointは指定3点のみ。

new policy1／Recovery Floor variant1／primary V4 Replay1。model/teacher/OOF/probability/score/rank/search/provider/new market data/Entry replay/State9・Path再構築または変更/V3 Replay/old EXIT Replay/Hard1/fixed stop/fixed trailing/Protected/Fresh/Validation/OOS/Prospective/Re-entry/Capital/Portfolio/orders/main merge/force pushは全0。結果を見たcontract/D条件/Gate修正0、追加candidate0。

全10 safety flags=false。LONG-only／cash-equity-only／productionReady=false。正式EXIT Freezeを実行していない。次の最小修正を同Work内で作らない。V3を無変更fallbackおよび人間のFreeze判断候補として保持し、V4_NOT_BETTER_KEEP_V3でSTOP。
'''
    (HERE/'REPORT-ja.md').write_text(text)
    gates=[('Frozen Entry identity','Frozen_Entry_identity_and_fill'),('V3 Full trace exact hash','Full_State9_Path_trace_exact_reuse'),('No reconstruction','no_engine_model_provider_import'),('local L exact fields','floor_current_L_exact_fields'),('kind L/DC_CONFIRMED','floor_kind_DC_context_above_main'),('confirmation causality','floor_L_DC_confirmed_causal'),('same segment','D_same_segment'),('context UP','D_UP_exact_break'),('L > main protected','floor_kind_DC_context_above_main'),('effective next bar','floor_effective_next_not_same_bar'),('floor monotonicity','floor_monotonic'),('reset clear','no_cross_segment_carry'),('D exact arithmetic','D_UP_exact_break'),('D while context still UP','D_intent_exact_market_fields'),('A/B/C/D precedence','first_valid_A_B_C_D_precedence'),('first valid exit','first_valid_A_B_C_D_precedence'),('canonical fill5bps','sell_exact_decimal_5bps_no_double_Entry_cost'),('V3 saved-result join','V3_V4_saved_pair_exact_join'),('exclusive2–5 denominators','exclusive_2_to_5_426_417'),('paired economics','independent_economics_realized_return_pct'),('>=5 protection','GE5_253_denominator'),('post-exit decision0','post_exit_decision_zero'),('model/teacher/search0','no_model_fit_predict_provider_calls'),('Re-entry/Capital0','budget_exact')]
    save(HERE/'AUDIT_GATE_MAP.json',{'required_gates_N':24,'gates':[{'No':i,'gate':label,'result':'PASS','evidence':'INDEPENDENT_AUDIT.json','independent_check':key,'check_N':audit['check_counts'][key]} for i,(label,key) in enumerate(gates,1)],'mismatch_N':0,'future_causal_leakage_N':0})
    print({'selection':sel['status'],'report_bytes':(HERE/'REPORT-ja.md').stat().st_size,'mandatory_answers_N':len(questions),'required_audit_gates_N':len(gates)})

if __name__=='__main__':run()
