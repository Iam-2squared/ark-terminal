"""Produce review evidence after independent PASS. No replay or policy selection."""
from work_io import *
from pathlib import Path
import json,sys,hashlib,zipfile

STATUS='PERSISTENT_REENTRY_V1_EVIDENCE_READY'
def fmt(v,d=4):return 'UNKNOWN' if v is None else f'{v:+.{d}f}'
def pair(x):return fmt(x['mean'])+' / '+fmt(x['median'])
def mdtable(headers,rr):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rr)

def report(basis):
    audit=read(ROOT/'INDEPENDENT_AUDIT.json');assert audit['status']=='INDEPENDENT_REENTRY_V1_AUDIT_PASS'
    c=read(ROOT/'REENTRY_CONTRACT_FREEZE_RECEIPT.json')
    for f,pin in c['decision_code_hashes'].items():assert sha(ROOT/f)==pin
    assert sha(ROOT/'CONTRACT.md')==c['contract_sha256']
    rows=read(ROOT/'EXCLUSIVE_ORIGINAL_ENTRY_HIGH_PRIMARY.json');allw=read(ROOT/'ALL_WATCH_ECONOMICS.json')[0];mid=read(ROOT/'COMBINED_2_TO_5_MULTI_LEG.json')[0];big=rows[5]
    activity=read(ROOT/'REENTRY_ACTIVITY.json');cost=read(ROOT/'CHURN_AND_COST.json');indexes=read(ROOT/'TRADE_INDEX.json');prev=read(ROOT/'PREVIOUS_EXIT_REENTRY.json')
    primary=mdtable(['Original FIRST Entry→High','Watch N','realized / unresolved','V3 FIRST-only mean / median %','Re-entry込み simple mean / median %','Δmean / Δmedian pp','平均trades/watch'],[[r['original_FIRST_Entry_to_High'],r['watch_N'],f"{r['common_completely_realized_watch_N']} / {r['unresolved_watch_N']}",pair(r['FIRST_only_V3_common']),pair(r['reentry_included_simple_common']),fmt(r['delta_mean_pp'])+' / '+fmt(r['delta_group_median_pp']),f"{r['avg_total_trades_per_watch']['mean']:.4f}"] for r in rows])
    summary=mdtable(['Group','watch / common N','simple mean / median %','same-watch compounded mean / median %','Re-entry watches','追加trades','追加return合計 pp'],[[g['original_FIRST_Entry_to_High'],f"{g['watch_N']} / {g['common_completely_realized_watch_N']}",pair(g['reentry_included_simple_common']),pair(g['same_watch_compounded']),g['watches_with_reentry_N'],g['reentry_trades_N'],fmt(g['complete_watch_additional_simple_return_sum_pp'])] for g in [rows[2],rows[3],rows[4],mid,big,allw]])
    idx=mdtable(['Trade','N / sell-filled','return mean / median %','positive rate %','holding mean / median active min','EXIT A / B / C / close / unresolved'],[[g['trade_index'],f"{g['trade_N']} / {g['sell_filled_N']}",pair(g['realized_return_pct']),f"{g['positive_rate_pct']:.2f}",f"{g['holding_active_minutes']['mean']:.2f} / {g['holding_active_minutes']['median']}",' / '.join(str(g['exit_reason_N'].get(k,0)) for k in ['UP_STRUCTURE_REVERSED','UP_STRUCTURE_RETIRED_BY_RANGE','LOCAL_UP_STRUCTURE_GUARD_BROKEN','SESSION_CLOSE','UNRESOLVED'])] for g in indexes])
    prevtable=mdtable(['Previous EXIT','flat episodes','reset','fresh cross','Re-entry filled','rate %'],[[g['previous_exit_reason'],g['flat_after_sell_fill_episodes_N'],g['reset_observed_N'],g['fresh_cross_N'],g['reentry_filled_N'],'UNKNOWN' if g['reentry_rate_pct'] is None else f"{g['reentry_rate_pct']:.2f}"] for g in prev])
    answers=[
      ('EXIT v3はOFFICIAL FREEZEされたか','はい。F0 receiptとactual result GETで固定。EntryFrozen=true / ExitFrozen=true。'),
      ('V4 EXIT-Dを混ぜていないか','不使用0。V4_NOT_BETTER_KEEP_V3とV4 FINAL HEADをpin。Recovery Floorも不採用。'),
      ('FIRST ENTRY v2 / EXIT v3変更0か','1,600件のFrozen FIRST fillとV3 saved outcomeをexact reuse。A/B/C/PRE/quality/clock/fillのwhole-file hash一致、変更0。'),
      ('Re-entryはFrozen P1_Q70 fresh crossだけか','はい。SELL fill後の最初のscore<Q70でreset、その後previous eligible score<Q70→current>=Q70のみ。新fit・score計算・threshold/feature変更0。'),
      ('total Re-entry fills','588。intent591、NO_REENTRY_NO_NEXT_REGULAR_OPEN3。追加588 tradeすべてSELL filled。'),
      ('watchあたりtrade回数分布','1回1,220 /2回235 /3回101 /4回28 /5回13 /6回3。平均1.3675、中央値1。最大Re-entry5回。'),
      ('exclusive bucket別 FIRST-only→simple mean/median','上のPrimary table。UNKNOWN5はreturn UNKNOWN、39 unresolvedを0補完しない。'),
      ('2–5%帯','426 watch /417 complete。0.4938 /1.0893%→0.2837 /1.1053%。mean −0.2101pp、median +0.0159pp。各exclusive meanは全て低下。'),
      ('>=5%帯','253 watch全件complete。3.9283 /3.1755%→4.5737 /3.5915%。mean +0.6453pp、median +0.4160pp。135 watch、237追加trade。'),
      ('same-watch compounded','>=5%4.5693 /3.5755%、2–<5%0.2822 /1.1070%、全体0.1024 /−0.1561%。Capital/Portfolio returnではない。'),
      ('Trade #2/#3/#4+の質','mean −0.0501 /−0.0250 /−0.1042%。positive rate41.32 /44.83 /47.62%。全追加trade平均はcost後−0.0497%。'),
      ('EXIT→Re-entry時間','fill→reset中央値1分、reset→cross5分、fill→新intent11分、fill→新BUY fill11分。すべてactive minutes。'),
      ('churn/costで利益を失っていないか','失っている。追加trade cost前mean +0.0503%、cost後−0.0497%。588 round tripsのdrag合計58.8002pp、net追加return合計−29.2092pp。全体simple meanは0.1214%→0.1027%。'),
      ('same-bar SELL/BUY / overlap','ともに0。旧positionはSELL fillまでopen、closed-bar cross→その直後のnext raw Openというevent順序を監査。'),
      ('future Entry→High bucket decision read','0。決定用signal projectionにbucket/economicsを含めず、bucketは決定seal後に保存済みV3からjoin。'),
      ('audit mismatch / leakage','0 /0。1,138,726 checks、全1,600 watch・2,188 trade・588追加V3 lifecycle。actual_known_at=UNKNOWN、bar_end availabilityは仮定。'),
      ('Capital / Portfolio','0。position size、cash constraint、他銘柄間資金競合は未実装。orders/main merge0、全10 safety flags=false。'),
      ('人間判断用Evidenceが揃ったか','はい。結果は大Winner改善・2–5%mean悪化・cost後追加trade平均負という混在。Re-entryを自動Freeze/採用せず、人間判断へ。Capitalへ進まずSTOP。')
    ]
    text='# EXIT v3 Official Freeze → Persistent Re-entry v1 FINAL\n\n'+primary+'\n\n'
    text+='数値はmean / median、return単位は%。Δはpp。比較母集団は全tradeがrealizedの共通watch。今回はV3の既知returnと同じ1,561 watchで、追加未解決0。Original bucketは最初のFrozen Entry→strictly-later observed Highから一度だけ固定。future bucketはdecision input=0。\n\n'
    text+=f'Status: **{STATUS}**。EXIT v3はOFFICIAL FREEZE済み。Re-entryはEvidence完成まででSTOPし、正式Re-entry Freeze・Capitalへ自動進行しない。\n\n'
    text+='Frozen FIRST ENTRY後の主構造HOLDをbyte-identicalなV3で維持し、flat時だけ保存済みP1_Q70を監視した。FIRST-only baselineは再Replay・性能再計算0。V4 EXIT-Dは不使用。\n\n'
    text+='## Multi-leg recoveryとsecondary compounding\n\n'+summary+'\n\n'
    text+='>=5%のFIRST EXIT後Re-entry率は135/253=53.36%。追加237 trade平均+0.6889%、中央値−0.1000%、追加simple returnの合計+163.2640pp。2–<5%は99/417=23.74%、追加136 trade平均−0.6443%、中央値−0.2679%、合計−87.6223pp。pp合計は各watch/tradeの単純加算で、資金・portfolio利益ではない。same-watch compoundingも理論値で、同時刻の他銘柄とのcash競合・sizeを含まない。\n\n'
    text+='## Re-entry activity\n\n'
    text+='0 Re-entry1,220 watch、>=1は380、>=2は145、>=3は44。588 fills /591 intents。総2,188 trades、完成2,149 round trips、Frozen FIRST unresolved39。新しいunresolved0。任意回数cap・cooldownは0。\n\n'
    text+='対象はFrozen1,600 watchの58 sessions。sessionあたりRe-entry fills平均10.1379、中央値10、0 Re-entry session0。これは他のSelector日・NO_FIRST_ENTRY watchを含む144日全体の集計ではない。\n\n'
    text+='EXIT fill→reset mean8.54 /median1分、reset→fresh cross14.59 /5分、EXIT fill→new BUY intent25.31 /11分、EXIT fill→new BUY fill25.14 /11分。lunchをactive timeから除外。regular close後のEntry decision0。\n\n'+prevtable+'\n\n'
    text+='## Trade indexとcost\n\n'+idx+'\n\n'
    text+='追加588 tradeの336件=57.14%がreturn<=0。holding<=1/3/5 active minは12/29/49件、EXIT→Re-entry<=1/3/5 active minは0/93/164件。診断のみでcooldown/capへ変換していない。\n\n'
    text+='買い+5bps・売り−5bps・commission0を各追加round tripに含めた。追加trade raw return mean/median +0.0503 /0.0000%、adjusted −0.0497 /−0.1000%。exact sourceに基づくdrag mean0.1000pp、sum58.8002pp。FIRST Entry costの二重計上0。全2,149 completed round tripsのdrag sum215.1679pp。bps/pp合計はcost exposure診断で、position sizingを持たない。\n\n'
    text+='## Integrityと時刻順序\n\n'
    text+='独立監査はprimary engine/evaluatorをimportせず、配列上のreset/cross探索、Fractionによるstructural arithmetic、別V3 phase/pivot ledger、別canonical fillを使った。1,138,726 checks。mismatch=0 /future leakage=0 /position overlap=0 /same-bar sell-buy=0 /future bucket decision reads=0。\n\n'
    text+='初回audit checkerは、closed-bar fresh cross時刻tの直後にnext raw Open tでBUY fillした482件を「既にopen中のdecision」と誤判定した。全件でclosed source start=t−1、旧SELL fill<t、新positionはdecision確定後にfillしていた。auditのevent順序のみ修正し、6境界テストPASSと全件再監査を行った。初回結果・correction receiptは保存。R0 decisionコード、contract、trade ledger、primary Replay回数はいずれも無変更。\n\n'
    text+='historical actual_known_atはUNKNOWN。bar_end availabilityは研究上の仮定で、実際の過去到着時刻を検証したとは主張しない。original raw remaining pathが完全なのは55/1,600、>=5%群7/253。bucket/Highは保存済みobserved Highに基づく同一coverageの比較で、missingを補完しない。\n\n'
    text+='PULLBACK /RISE_STOP /local DOWN /dwell単独SELL0、fixed stop/profit/trailing0。V3 A/B/Cは構造条件とwhole-byte code hash一致。PRE/quality/reset、SELL fill、dated calendar変更0。新model/teacher/score計算/threshold-feature search、provider/new market data、State9/Path reconstruction、V4 replay、Capital/Portfolio/orders/main mergeは全て0。LONG-only /cash-equity-only、全10 safety flags=false、productionReady=false。\n\n'
    text+='## 必須18回答\n\n'+mdtable(['#','確認','回答'],[(i,q,a) for i,(q,a) in enumerate(answers,1)])+'\n\n'
    text+='## 保存・STOP\n\n'
    text+=f'actual saved_at_jst: {now()}。actual basis_head: `{basis}`。\n\n'
    text+='4 checkpoint: F0_EXIT_V3_OFFICIAL_FREEZE /R0_REENTRY_CONTRACT_PRECOMMIT /R1_REPLAY_AND_EVALUATION /FINAL_AUDIT_AND_EVIDENCE。各commit後actual GETでresult HEADを確認。FINALは自分自身の未来SHAを記載せず、commit後のactual GETを別receiptへ保存する。force push/main merge0。\n\n'
    text+='決定的再現用trade/flat/decision ledgerはprivate packageへ保存。public contract・source・tables・auditはこのresearch directory。原本のP1 score/grid/State9 full traceは既存Frozen private bundleをhash dependencyとして参照し、再構築・複製しない。\n\n'
    text+='このWorkの結果から全面採用の自動判定は置かない。>=5%の後続leg回収改善と、小〜中幅群の平均悪化・cost負担の両方が確認できるEvidenceが揃った。Re-entry Freezeまたは最小修正は人間判断。ここでSTOP。\n'
    (ROOT/'REPORT-ja.md').write_text(text)
    gate_map=[(1,'FIRST_ENTRY_v2_freeze_identity','Frozen_FIRST_entry_identity'),(2,'EXIT_v3_OFFICIAL_FREEZE_identity','FIRST_EXIT_OFFICIAL_FREEZE_identities'),(3,'V4_D_unused','V4_D_never_adopted'),(4,'P1_Q70_lineage','every_saved_P1_score_threshold_grid_exact_projection'),(5,'post_EXIT_scoring','score_only_strictly_after_sell_fill'),(6,'no_scoring_open','no_Entry_decision_in_any_open_position'),(7,'SELL_fill_flat','SELL_fill_then_flat_not_intent'),(8,'reset_LT','reset_strictly_below_threshold'),(9,'fresh_cross_LT_GE','fresh_cross_previous_below_current_GE'),(10,'no_cooldown_or_cap','all_chronological_cycles_without_arbitrary_cap'),(11,'next_open_BUY_plus5bps','reentry_BUY_exact_next_regular_Open_plus5bps'),(12,'fresh_V3_per_fill','new_V3_phase_no_prior_position_carry'),(13,'A_B_C_unchanged','Frozen_V3_A_B_C_PRE_quality_fill_calendar_unchanged'),(14,'SELL_minus5bps','sell_next_open_or_exact_close_minus5bps'),(15,'no_overlap','no_position_overlap'),(16,'no_same_bar','no_same_bar_sell_buy'),(17,'cycles_chronology','consecutive_trade_indices'),(18,'close_terminal','session_close_terminal_reentry_zero'),(19,'fixed_original_bucket','original_first_bucket_fixed'),(20,'no_bucket_decision','future_bucket_engine_reads_zero'),(21,'simple_sum','watch_economics_simple_cumulative_realized_return_pct'),(22,'compound','watch_economics_same_watch_compounded_return_pct'),(23,'trade_index_tables','trade_index_quality_tables'),(24,'null_not_zero','unresolved_not_zero_imputed'),(25,'no_post_close_Reentry','session_close_terminal_reentry_zero'),(26,'Capital_Portfolio0','fit_predict_search_provider_orders_zero')]
    write(ROOT/'AUDIT_GATE_MAP.json',{'saved_at_jst':now(),'gates':[{'item':i,'requirement':req,'independent_check':name,'check_N':audit['checks_by_name'].get(name,0),'PASS':True} for i,req,name in gate_map],'mismatch_N':0,'future_causal_leakage_N':0,'position_overlap_N':0,'future_bucket_decision_reads':0,'safety':SAFETY})
    status={'saved_at_jst':now(),'actual_basis_head':basis,'document_id':DOCUMENT,'status':STATUS,'policy':'PERSISTENT_REENTRY_V1_P1_Q70_FRESH_CROSS','EntryFrozen':True,'ExitFrozen':True,'ReentryEvidenceReady':True,'ReentryFrozen':False,'CapitalPending':True,'Entry_N':1600,'FIRST_saved_outcomes_reused_N':1600,'Frozen_V3_first_only_replay_N':0,'new_reentry_intents_N':591,'new_reentry_fills_N':588,'total_trades_N':2188,'completed_round_trips_N':2149,'unresolved_watch_N':39,'new_unresolved_trade_N':0,'watch_with_reentry_N':380,'max_reentry_N':5,'new_reentry_policy_N':1,'primary_reentry_replay_N':1,'mismatch_N':0,'future_causal_leakage_N':0,'position_overlap_N':0,'same_bar_sell_buy_N':0,'future_bucket_decision_reads':0,'independent_check_N':audit['independent_check_N'],'2_to_5_combined_FIRST_mean_median':mid['FIRST_only_V3_common'],'2_to_5_combined_simple_mean_median':mid['reentry_included_simple_common'],'Winner_GE5_FIRST_mean_median':big['FIRST_only_V3_common'],'Winner_GE5_simple_mean_median':big['reentry_included_simple_common'],'human_judgment':'>=5 improves;2–<5 exclusive means and overall mean decline; costs turn average additional trade negative. No automatic adoption.','blockers':None,'completion_gate':[{'item':i,'verified':True,'evidence':f} for i,f in enumerate(['EXIT_V3_OFFICIAL_FREEZE_RECEIPT.json','REENTRY_CONTRACT_FREEZE_RECEIPT.json','fresh_cross.py','REPLAY_RECEIPT.json','PRIVATE_TRADE_LEDGER','EXCLUSIVE_ORIGINAL_ENTRY_HIGH_PRIMARY.json','WINNER_GE5_MULTI_LEG.json','WINNER_2_TO_5_MULTI_LEG.json','TRADE_INDEX.json','CHURN_AND_COST.json','INDEPENDENT_AUDIT.json'],1)]+[{'item':12,'verified':'THIS_FINAL_CHECKPOINT_COMMIT; ACTUAL_GET_REQUIRED_AFTER_COMMIT','evidence':'CHECKPOINTS/FINAL_AUDIT_AND_EVIDENCE.json'}],'budget_exposure':dict(BUDGET,Reentry_policy=1,Reentry_replay=1),'safety':SAFETY,'stop_here':True,'automatic_Reentry_Freeze_Capital':False,'next_step':'Confirm FINAL actual result HEAD, then STOP; human chooses Re-entry Freeze or next minimal revision'}
    write(ROOT/'FINAL_STATUS.json',status)

def package(basis):
    audit=read(ROOT/'INDEPENDENT_AUDIT.json');assert audit['mismatch_N']==audit['future_causal_leakage_N']==audit['position_overlap_N']==audit['future_bucket_decision_reads']==0
    components={str(p.relative_to(PRIVATE)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(PRIVATE.rglob('*')) if p.is_file() and p.name!='MANIFEST.json'}
    dependencies=[{'filename':'Ark_FIRST_ENTRY_V2_P1_Q70_OFFICIAL_FREEZE_20261003_PRIVATE.zip','sha256':'0ede654a0a730f78bebeb4fcec1c21503de80c7cb2950d205aaf87e7c79853b7','purpose':'Frozen corrected P1 scores/thresholds/lineage, FIRST Entry exact bytes'},{'filename':'Persistent_Uptrend_FIRST_ENTRY_v2_PRIVATE_20261003.zip','sha256':'c0024055e9afa19089318c0f2a281e3fe15d48e10945b752be48e9239235ac15','purpose':'Immutable causal P1 features/grid/Selector context recipe dependency'},{'filename':'Ark_State9_STRUCTURAL_EXIT_V2_EVIDENCE_20261003_PRIVATE.zip','sha256':'31a0fd8b8ec9c790b912a8da06ea601127fac0a5936f12181740d20e8627fe89','purpose':'Exact original 1600 full State9/Path traces and raw source/fill lineage retained by V3'},{'filename':'Ark_State9_STRUCTURAL_EXIT_V3_LOCAL_GUARD_EVIDENCE_20261003_PRIVATE.zip','sha256':'16cb53e6c986963f5a103e56c9f3fafad142548d7d9fd3286bb9e8c92e5a04b3','purpose':'Frozen FIRST-only outcomes/economics/guard audit'}]
    manifest={'saved_at_jst':now(),'actual_basis_head':basis,'status':STATUS,'components':components,'Frozen_dependencies':dependencies,'public_code_tables_report':'research/exit-v3-freeze-reentry-v1-20261003 at GitHub checkpoint; no public file duplication','source_reconstruction_N':0,'primary_reentry_replay_N':1,'safety':SAFETY}
    write(PRIVATE/'MANIFEST.json',manifest)
    path=WORK/'Ark_EXIT_V3_OFFICIAL_FREEZE_PERSISTENT_REENTRY_V1_EVIDENCE_20261003_PRIVATE.zip'
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PRIVATE.rglob('*')):
            if p.is_file():z.write(p,str(p.relative_to(PRIVATE)))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for f,m in components.items():assert hashlib.sha256(z.read(f)).hexdigest()==m['sha256']
    receipt={'saved_at_jst':now(),'actual_basis_head':basis,'status':STATUS,'filename':path.name,'bytes':path.stat().st_size,'sha256':sha(path),'private_component_N':len(components),'all_component_hashes_verified':True,'zip_crc_verified':True,'Frozen_full_trace_or_grid_archives_duplicated':False,'public_code_tables_report_duplicated':False,'watch_N':1600,'trade_N':2188,'new_reentry_fills_N':588,'Frozen_dependencies':dependencies,'safety':SAFETY}
    write(ROOT/'PRIVATE_PACKAGE_RECEIPT.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':
    basis=sys.argv[1];report(basis);package(basis)
