"""Final precommitted decision and Japanese handoff, no policy creation."""
from control import *
from decimal import Decimal as D
import sys
ARMS=['RANK_NATIVE_GREEDY_MAX3','RANK_NATIVE_LAST_SLOT_OPTION_MAX3']
SHORT={ARMS[0]:'A1 Greedy',ARMS[1]:'A2 Last-slot'}
def decision():
 audit=read(OUT/'INDEPENDENT_AUDIT.json');assert audit['mismatch_N']==0
 p=read(OUT/'PRESERVATION_RESULT.json')['profiles'];e=read(OUT/'CAPITAL_ROLLING20_RESULT.json')['profiles'];profiles={}
 for arm in ARMS:
  gate=dict(p[arm]['preservation_gate']);gate['P5_independent']=True;passed=all(gate.values());capital=e[arm]['Capital_gates'];metrics=e[arm]['economics'];status='NORTH_STAR_HIT' if passed and metrics['north_star_hit_N']>0 else 'CAPITAL_V7_IMPROVES' if passed and all(capital.values()) else 'SLOT_IMPROVED_CAPITAL_MIXED' if passed else 'CAPITAL_ONLY_MIXED' if any(capital.values()) else 'NO_GO'
  profiles[arm]={'preservation_gate':gate,'preservation_PASS':passed,'Capital_gates':capital,'status':status}
 def key(a):
  m=e[a]['economics'];q=p[a];return (-m['north_star_hit_N'],-m['rolling20_median'],-m['rolling20_arithmetic_mean'],-m['geometric_mean_daily_return'],-q['U5_funded'],-q['U10_funded'],q['funded_quality']['below2_rate'],m['max_drawdown'],ARMS.index(a))
 eligible=[a for a in ARMS if profiles[a]['preservation_PASS']];winner=min(eligible,key=key) if eligible else None;diag=winner or min(ARMS,key=key);selected=winner if winner and profiles[winner]['status'] in ('CAPITAL_V7_IMPROVES','NORTH_STAR_HIT') else None
 c=p[diag]['conservation']['U5'];gaps={'RANK_ADMISSION':c['RANK_BASE_REJECT'],'LAST_SLOT_RESERVE':c['LAST_SLOT_RESERVE_REJECT'],'MAX3_PHYSICAL_OCCUPANCY':c['MAX3_FULL'],'CASH_SIZING':c['CASH_OR_LOT']};best=max(gaps.values());names=[k for k,v in gaps.items() if v==best];bottleneck=names[0] if len(names)==1 and best>0 else 'NO_CLEAR_SINGLE_BOTTLENECK';selection={'eligible_winner':winner,'diagnostic_arm':diag,'selectedCapitalCandidate':selected,'NEXT_BOTTLENECK':bottleneck,'reason_gaps':gaps};assert selection==audit['independent_selection'],'INDEPENDENT_FINAL_SELECTION_MISMATCH'
 oracles=read(OUT/'ORACLE_RESULT.json')['solves'];n5=oracles['ALL_U5']['maximum_U5'];ad5=oracles['ADMISSION_U5']['maximum_U5'];counts={a:{'G1_RANK_ADMISSION_GAP':p[a]['conservation']['U5']['RANK_BASE_REJECT'],'G2_LAST_SLOT_POLICY_GAP':p[a]['conservation']['U5']['LAST_SLOT_RESERVE_REJECT'],'G3_OCCUPANCY_GAP':p[a]['conservation']['U5']['MAX3_FULL'],'G4_CASH_LOT_GAP':p[a]['conservation']['U5']['CASH_OR_LOT'],'G5_PHYSICAL_UNAVOIDABLE':170-n5,'G6_RUNTIME_TO_ORACLE_GAP':n5-p[a]['U5_funded'],'admission_ceiling_loss':n5-ad5,'allocator_to_admission_ceiling_gap':ad5-p[a]['U5_funded'],'funded':p[a]['U5_funded']} for a in ARMS}
 for a,g in counts.items():assert sum(g[k] for k in ('G1_RANK_ADMISSION_GAP','G2_LAST_SLOT_POLICY_GAP','G3_OCCUPANCY_GAP','G4_CASH_LOT_GAP','funded'))==170 and g['G5_PHYSICAL_UNAVOIDABLE']+g['admission_ceiling_loss']+g['allocator_to_admission_ceiling_gap']+g['funded']==170
 out={'exact_jst':now(),'final_status':profiles[winner]['status'] if winner else 'NO_GO','profiles':profiles,'selection':selection,'selectedCapitalCandidate':selected,'selectedSlotDiagnosticCandidate':winner if winner and selected is None else None,'retainedCapitalBenchmark':'V5_FROZEN_REFERENCE' if selected is None else None,'selectedRankCandidate':'EXISTING_MOVE_P5','NEXT_BOTTLENECK':bottleneck,'gaps':counts,'independent_final_selection_mismatch_N':0,'ceiling_gap_partition_note':'G5/G6 are a separate counterfactual telescoping decomposition, not additive with observed reason G1..G4. No individual miss is claimed physically unavoidable solely from reason.','higher_pP_blocked_by_lower_pP_holding_U5':p[diag]['HIGHER_RANK_WINNER_BLOCKED_BY_LOWER_RANK_HOLDING_U5'],'policy_retune':0,'fresh_OOS_claim':False,'productionReady':False,'Safety':SAFETY}
 save(OUT/'WINNER_AND_BOTTLENECK.json',out)
 save(OUT/'NEXT_WORK_HANDOFF.json',{'exact_jst':now(),'state':'CAPITAL_V7_NO_GO_FIXED_STOP' if winner is None else out['final_status'],'selectedCapitalCandidate':selected,'retainedCapitalBenchmark':out['retainedCapitalBenchmark'],'selectedRankCandidate':'EXISTING_MOVE_P5','frozenRankOrder':['pP DESC','Frozen Entry timestamp ASC','stable symbol ASC'],'NEXT_BOTTLENECK':bottleneck,'diagnostic_arm_not_adopted':diag,'diagnosis':'Observed MAX3 blockers include early lower-pP holdings; physical unavoidable count is separately bounded. This does not authorize replacement, EXIT change or any new policy.','permanentFreeze':['Selector','Entry','EXIT'],'rank_refit_or_calibration':0,'same_cycle_additional_policy':False,'do_not':['rerun primary replays','rerun completed Oracle solves','retune thresholds','A3','change Rank/features/preprocessing','open protected/fresh','MAX4/MAX5','position replacement','forced EXIT','main merge','orders'],'next_work_requires_independent_instruction':True,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False,'productionReady':False,'Safety':SAFETY})
 checkpoint('D14_WINNER_AND_BOTTLENECK','NO_GO_AND_BOTTLENECK_FIXED',['Preservation/Capital gates','precommitted winner order','independent final selection match','non-overlapping ceiling gaps'],out,'Generate final report and private recovery pack; D15 closure STOP, no further policy',{'oracle_solves':4,'primary_replays':2,'independent_recalculations':2,'independent_oracle_solves':4})
 print(json.dumps({'status':out['final_status'],'selectedCapitalCandidate':selected,'NEXT_BOTTLENECK':bottleneck}),flush=True)
def report():
 dec=read(OUT/'WINNER_AND_BOTTLENECK.json');p=read(OUT/'PRESERVATION_RESULT.json');pr=p['profiles'];rr=read(OUT/'CAPITAL_ROLLING20_RESULT.json');a=read(OUT/'INDEPENDENT_AUDIT.json');oracle=read(OUT/'ORACLE_RESULT.json')['solves'];v5=rr['v5_saved_reference'];economics={'v5':v5,**{SHORT[k]:rr['profiles'][k]['economics'] for k in ARMS}}
 lines=[]
 def line(s=''):lines.append(s)
 def table(header,body):
  line('|'+ '|'.join(header)+'|');line('|'+'|'.join('---' for _ in header)+'|')
  for row in body:line('|'+ '|'.join(str(v) for v in row)+'|')
  line()
 def pct(x):return f'{100*x:.6f}%'
 line('## A. North Star / rolling 20 sessions');line()
 table(['Profile','20d min','20d mean','20d median','20d max','2x hit'],[[name]+[f'{r[k]:.10f}x' for k in ('rolling20_minimum','rolling20_arithmetic_mean','rolling20_median','rolling20_maximum')]+[f'{r["north_star_hit_N"]}/19'] for name,r in economics.items()])
 line('結論: **NO_GO**。A1/A2ともPreservation GateとCapital Gate未達。selectedCapitalCandidate=null。保存済みv5をCapital benchmarkとして保持し、D15で固定STOPする。Rank vNext=EXISTING_MOVE_P5 / pP DESCは変更しない。');line()
 line('North Starは¥1,000,000→¥2,000,000 / 20 sessions。19 rolling windowsは重複し、独立19標本ではない。同じDevelopmentの反復利用Evidenceであり、fresh/OOS成功、production-ready、将来市場収益の保証ではない。');line()
 line('## B. U5/U10 preservation');line()
 table(['Profile','U5 funded /170','U10 funded /67','Oracle recovery U5 / U10','<2','Reserve miss U5/U10','MAX3 miss U5/U10','Rank reject U5/U10'],[['v5','50 /170','26 /67',f'{50/149:.4%} / {26/67:.4%}','38.666667%','30 /10','28 /9','57 /20']]+[[SHORT[arm],f'{r["U5_funded"]} /170 ({r["U5_capture"]:.4%})',f'{r["U10_funded"]} /67 ({r["U10_capture"]:.4%})',f'{r["Oracle_ALL_U5_recovery"]:.4%} / {r["Oracle_ALL_U10_recovery"]:.4%}',pct(r['funded_quality']['below2_rate']),f'{r["conservation"]["U5"]["LAST_SLOT_RESERVE_REJECT"]} /{r["conservation"]["U10"]["LAST_SLOT_RESERVE_REJECT"]}',f'{r["conservation"]["U5"]["MAX3_FULL"]} /{r["conservation"]["U10"]["MAX3_FULL"]}',f'{r["conservation"]["U5"]["RANK_BASE_REJECT"]} /{r["conservation"]["U10"]["RANK_BASE_REJECT"]}'] for arm,r in pr.items()])
 line('Oracle recoveryは新ALL ceiling U5=149/U10=67を分母とする。v5の57/20 Rank rejectは、固定primary170/67から保存済み旧rank-pass113/47を引いた診断値であり、Control replayは0。旧104/47 ceilingは新母集団へ流用していない。');line()
 table(['Gate','v5 benchmark','A1','A2'],[['P1 U5','>50',dec['profiles'][ARMS[0]]['preservation_gate']['P1_U5_gt50'],dec['profiles'][ARMS[1]]['preservation_gate']['P1_U5_gt50']],['P2 U10','>=26',dec['profiles'][ARMS[0]]['preservation_gate']['P2_U10_ge26'],dec['profiles'][ARMS[1]]['preservation_gate']['P2_U10_ge26']],['P3 <2','<=38.666667%',False,False],['P4 integrity','違反0',True,True],['P5 independent','mismatch0',True,True]])
 line('A1はU5が50で増加せず、<2混入が悪化。A2はU5+1だがU10−1、<2混入も悪化。採用可能armは0。A2のU5 MAX3 miss減少41件はReserve miss41件で相殺され、Net Slot MissはA1/A2とも67。');line()
 line('## C. v5比較');line()
 keys=[('U5 funded',50,pr[ARMS[0]]['U5_funded'],pr[ARMS[1]]['U5_funded']),('U10 funded',26,pr[ARMS[0]]['U10_funded'],pr[ARMS[1]]['U10_funded']),('Funded N',v5['funded_N'],pr[ARMS[0]]['funded_quality']['N'],pr[ARMS[1]]['funded_quality']['N']),('<2 contamination','38.666667%',pct(pr[ARMS[0]]['funded_quality']['below2_rate']),pct(pr[ARMS[1]]['funded_quality']['below2_rate'])),('rolling20 median',f'{v5["rolling20_median"]:.10f}',f'{economics[SHORT[ARMS[0]]]["rolling20_median"]:.10f}',f'{economics[SHORT[ARMS[1]]]["rolling20_median"]:.10f}'),('rolling20 mean',f'{v5["rolling20_arithmetic_mean"]:.10f}',f'{economics[SHORT[ARMS[0]]]["rolling20_arithmetic_mean"]:.10f}',f'{economics[SHORT[ARMS[1]]]["rolling20_arithmetic_mean"]:.10f}'),('daily geometric',pct(v5['geometric_mean_daily_return']),pct(economics[SHORT[ARMS[0]]]['geometric_mean_daily_return']),pct(economics[SHORT[ARMS[1]]]['geometric_mean_daily_return']))]
 table(['Metric','v5','A1','A2','Winner'],[[name,v,x,y,'none; v5保持'] for name,v,x,y in keys])
 table(['Arm','Preservation','Capital median/mean/geom','Final status'],[[SHORT[arm],'FAIL',' / '.join('PASS' if v else 'FAIL' for v in dec['profiles'][arm]['Capital_gates'].values()),dec['profiles'][arm]['status']] for arm in ARMS])
 line('## D. Oracle gap waterfall');line()
 table(['Profile','U5 funded','U10 funded','新admission Oracle U5/U10','新ALL Oracle U5/U10'],[['v5',50,26,'参考のみ: 116 /55','149 /67']]+[[SHORT[arm],pr[arm]['U5_funded'],pr[arm]['U10_funded'],'116 /55','149 /67'] for arm in ARMS])
 table(['Oracle','原母集団','Executable N','U5 maximum','U10 maximum','Exact min cash witness'],[[name,1028 if name.startswith('ALL') else '新percentile admission',r['candidate_N'],r['maximum_U5'] if name.endswith('U5') else 'U10-only目的',r['maximum_U10'],r['minimum_lot_witness_cash_min']] for name,r in oracle.items()])
 line('ALL_U5はU5最大149の下でU10=67も保存。ALL_U10は別目的で最大67。ADMISSION_U5はU5最大116の下でU10=55、ADMISSION_U10の別最大も55。Cash-relaxed interval upper boundに100株のexact cash/MAX3 witnessが到達し、無制限整数lotを含むphysical count最適性を証明した。独立binary occupancy MILPでも上限一致。Oracleはevaluation-onlyでruntimeへ渡していない。');line()
 line('12候補はFrozen EXIT/EOD source unavailable（全てU5/U10=0）。original1028 identityは維持し、Oracleではexact execution availabilityによりfund不能。runtimeにはこの未来availability gateを追加せず、実際に12件はいずれもfundされず、両armのexecution unresolvedは0。');line()
 for target,total in [('U5',170),('U10',67)]:
  line(f'### {target}: 排他的reason waterfall');line()
  body=[]
  for arm in ARMS:
   c=pr[arm]['conservation'][target];after_rank=total-c['RANK_BASE_REJECT'];after_reserve=after_rank-c['LAST_SLOT_RESERVE_REJECT'];after_max=after_reserve-c['MAX3_FULL'];body.append([SHORT[arm],total,after_rank,after_reserve,after_max,c['FUNDED'],f'{c["CASH_OR_LOT"]} cash/lot; same-symbol/execution/other=0'])
  table(['Profile','All','After admission','After reserve','After MAX3','Funded','Other misses'],body)
  line('これは排他的reasonを順に引く表示であり、candidateの時系列を集約順に入れ替えてreplayしたものではない。');line()
 table(['Profile','Physical unavoidable','Admission ceiling loss','Runtime-to-admission gap','Funded','Total'],[[SHORT[arm],dec['gaps'][arm]['G5_PHYSICAL_UNAVOIDABLE'],dec['gaps'][arm]['admission_ceiling_loss'],dec['gaps'][arm]['allocator_to_admission_ceiling_gap'],pr[arm]['U5_funded'],170] for arm in ARMS])
 line('U5 ceiling waterfall: 170 → ALL149 → ADMISSION116 → A1 funded50 / A2 funded51。21+33+66+50=170、21+33+65+51=170。これは別のcounterfactual telescoping分解であり、observed Rank/Reserve/MAX3/cash reasonと重複加算しない。個々のmissにunavoidableとの因果ラベルを付けていない。');line()
 table(['Profile','G1 Rank','G2 Reserve','G3 MAX3','G4 cash/lot','G5 unavoidable (別分解)','G6 ALL−funded (別分解)'],[[SHORT[arm]]+[dec['gaps'][arm][k] for k in ('G1_RANK_ADMISSION_GAP','G2_LAST_SLOT_POLICY_GAP','G3_OCCUPANCY_GAP','G4_CASH_LOT_GAP','G5_PHYSICAL_UNAVOIDABLE','G6_RUNTIME_TO_ORACLE_GAP')] for arm in ARMS])
 line('## E. Slot1/2/3 quality');line()
 table(['Profile','Slot','Funded N','U5 N','U10 N','<2 N/rate','<3 N/rate','Medium3-<5'],[[SHORT[arm],s,q['N'],q['U5'],q['U10'],f'{q["below2_N"]} / {q["below2_rate"]:.4%}',f'{q["below3_N"]} / {q["below3_rate"]:.4%}',q['Medium3_5_N']] for arm in ARMS for s,q in pr[arm]['slot_quality'].items()])
 line('slotはFrozen v5と同じfund時のconcurrent+1定義。後日slot品質の結果からReserve閾値は変更していない。A2はoccupancy0/1ではReserve0。');line()
 line('## F. Rank-regret / higher-pP blocked winner');line()
 table(['Profile','Higher-pP U5 blocked by lower-pP holding','U10 same diagnostic'],[[SHORT[arm],pr[arm]['HIGHER_RANK_WINNER_BLOCKED_BY_LOWER_RANK_HOLDING_U5'],pr[arm]['HIGHER_RANK_WINNER_BLOCKED_BY_LOWER_RANK_HOLDING_U10']] for arm in ARMS])
 line('A1の67 MAX3-missed U5中51件は、held最小pPよりmissed pPが高い。held count、score、Entry/arrival、実際のoverlap duration、reasonはprivate RANK_REGRET_LEDGERに保存。これはreplacementやEXIT変更を正当化しない。');line()
 line('### Legacy comparable subset: 旧rank-pass U5=113 / U10=47');line()
 table(['Profile/target','Funded','New rank reject','Reserve','MAX3','cash/lot','Total'],[['v5 /U5',50,0,30,28,5,113],['v5 /U10',26,0,10,9,2,47]]+[[SHORT[arm]+'/'+target]+[pr[arm]['legacy_rank_pass_comparable'][target][k] for k in ('FUNDED','RANK_BASE_REJECT','LAST_SLOT_RESERVE_REJECT','MAX3_FULL','CASH_OR_LOT')]+[113 if target=='U5' else 47] for arm in ARMS for target in ('U5','U10')])
 line('## G. Daily / Final38 / MaxDD / utilization — Secondary');line()
 fields=[('Daily geometric','geometric_mean_daily_return','pct'),('Daily arithmetic','arithmetic_mean_daily_return','pct'),('Daily median','median_daily_return','pct'),('38-session Final Equity','final_equity','money'),('Total return','total_return','pct'),('Minute MTM MaxDD','max_drawdown','pct'),('Mean utilization','utilization_mean','pct'),('Median utilization','utilization_median','pct'),('Mean idle fraction','mean_idle_cash_fraction','pct'),('Turnover JPY','turnover_cash_jpy','money'),('Recycled cash used JPY','capital_recycling_used_jpy','money'),('Funded/session','avg_funded_per_session','num')]
 body=[]
 for label,k,fmt in fields:
  vals=[]
  for r in economics.values():v=r[k];vals.append(pct(v) if fmt=='pct' else f'¥{v:,.2f}' if fmt=='money' else f'{v:.6f}')
  body.append([label]+vals)
 table(['Metric','v5 saved','A1','A2'],body)
 table(['Profile','Mean idle cash JPY'],[[SHORT[arm],f'¥{economics[SHORT[arm]]["idle_cash_mean_jpy"]:,.2f}'] for arm in ARMS])
 line('38 OOF sessionsの連結Final Equityであり「1か月成績」ではない。start=¥1,000,000。BUY1.0005、SELL0.9995、commission0、MTMのbar-close availability、cash release、15:20 cutoff、lot100、MAX3、cash LONG-onlyを維持。Liquidityはv5と同じdiagnostic-onlyでhard gate追加0。');line()
 line('## H. Integrity / counts / Safety / lineage');line()
 table(['Item','Result'],[['Canaries','28/28 PASS; synthetic only, Main前'],['Independent checks',a['check_N']],['Independent mismatches',a['mismatch_N']],['Money/quantity tolerance',0],['Score/probability tolerance',1e-12],['Observed max scalar float delta',a['max_float_delta']],['Primary replay','A1=1, A2=1, total2'],['Control/v6 replay',0],['Oracle solves','4; separate independent upper-bound audit4'],['New / Rank / Slot fits',0],['Teacher regeneration',0],['Rank/model/preprocessing/score change',0],['Orders/main merge/force push/provider/Claude',0],['Protected/fresh/holdout/validation/OOS/prospective open',0],['Selector/Entry/EXIT changes',0],['MAX3/cash/same-symbol/replacement violations',0],['Both arms COMPLETE','38/38; execution unresolved0'],['11 post-cutoff identities','retained in runtime, funded0']])
 table(['Authority','SHA256'],[['Rank contract','6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518'],['Frozen pP stream','14c48e61554bd58c6d5289b410d6a8c859cb37efd0dbc5d98987fcb440aac2ed'],['Common mask',sha(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz')],['Band map',sha(OUT/'RANK_NATIVE_BAND_MAP.json')],['Future max rank table',sha(OUT/'FUTURE_MAX_RANK_TABLE.json')],['Main claim',sha(OUT/'MAIN_REPLAY_CLAIM.json')],['Independent audit',sha(OUT/'INDEPENDENT_AUDIT.json')]])
 line('全input/model/score/ledger hashはINPUT_BYTE_AND_SOURCE_FREEZE、BAND_VOLUME_IDENTITY_AUDIT、MAIN_REPLAY_RESULTに保存。8 rolling-originのsame completed train IDsを利用し、test volumeは強制しない。pPはordering authority / Rank Research Candidateであり、calibrated true probabilityとは呼ばない。training-only future tableにU5/U10 labelやtest未来arrivalはない。');line()
 line('Historical actual arrivalはUNKNOWNのまま、継承したclosed-bar availability/source/PIT boundaryを維持。独立実装は同じmarket sourceを利用するため、外部market source独立性は意味しない。teacher support contractのknown/unknown、empty future complete-captureの旧契約は変更・再生成していない。');line()
 line('Safety: '+', '.join(k+'=false' for k in SAFETY)+'.');line()
 line('## I. Next Bottleneck');line()
 line('NEXT_BOTTLENECK = **MAX3_PHYSICAL_OCCUPANCY**。採用可能arm0のため、事前固定winner順でdiagnostic arm=A1を選んだだけで、A1を採用していない。A1の排他的missはRank46、Reserve0、MAX3 67、cash/lot7。最大reason67が該当する。');line()
 line('真にcount上限上unavoidableなU5は21であり、67全てが不可避ではない。51件のhigher-pP winnerがlower-pP holdingに塞がれ、ADMISSION Oracle116−funded50=66のruntime gapが残る。次の独立Workではこのoccupancy/early-fill構造を診断する境界をhandoffするが、本cycleで新policy・threshold・modelを足さない。Selector/Entry/EXITは永久Freeze。');line()
 line('### pP decile別funding（全primaryのpP DESCを10分割、診断のみ）');line()
 table(['Decile 1=highest','Candidate U5/U10','A1 funded U5/U10','A2 funded U5/U10'],[[j,f'{pr[ARMS[0]]["pP_deciles"][str(j)]["candidate_quality"]["U5"]}/{pr[ARMS[0]]["pP_deciles"][str(j)]["candidate_quality"]["U10"]}',f'{pr[ARMS[0]]["pP_deciles"][str(j)]["funded_quality"]["U5"]}/{pr[ARMS[0]]["pP_deciles"][str(j)]["funded_quality"]["U10"]}',f'{pr[ARMS[1]]["pP_deciles"][str(j)]["funded_quality"]["U5"]}/{pr[ARMS[1]]["pP_deciles"][str(j)]["funded_quality"]["U10"]}'] for j in range(1,11)])
 line('### Entry時刻別funding（hourは診断表示のみ、runtime time bucketは追加0）');line()
 table(['Entry hour JST','Candidate U5/U10','A1 funded U5/U10','A2 funded U5/U10'],[[f'{h:02}:00',f'{pr[ARMS[0]]["entry_hour_quality"][str(h)]["candidate_quality"]["U5"]}/{pr[ARMS[0]]["entry_hour_quality"][str(h)]["candidate_quality"]["U10"]}',f'{pr[ARMS[0]]["entry_hour_quality"][str(h)]["funded_quality"]["U5"]}/{pr[ARMS[0]]["entry_hour_quality"][str(h)]["funded_quality"]["U10"]}',f'{pr[ARMS[1]]["entry_hour_quality"][str(h)]["funded_quality"]["U5"]}/{pr[ARMS[1]]["entry_hour_quality"][str(h)]["funded_quality"]["U10"]}'] for h in range(9,16)])
 line('selectedCapitalCandidate = null');line('selectedRankCandidate = EXISTING_MOVE_P5');line('NEXT_BOTTLENECK = MAX3_PHYSICAL_OCCUPANCY');line('fresh_OOS_claim = false');line('productionReady = false');line()
 line('Rank vNextは固定したまま。新Allocator/Capital候補はNO_GOで、v5を保持。D15 CLOSURE_FIXED_STOP。')
 with (OUT/'REPORT_FINAL-ja.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
 save(OUT/'REPORT_FACTS.json',{'exact_jst':now(),'report_sha256':sha(OUT/'REPORT_FINAL-ja.md'),'final_status':'NO_GO','selectedCapitalCandidate':None,'selectedRankCandidate':'EXISTING_MOVE_P5','NEXT_BOTTLENECK':dec['NEXT_BOTTLENECK'],'audit_mismatch_N':0,'report_figures_from_saved_ledgers_only':True,'all_primary_replay_receipts_preserved':True,'Safety':SAFETY})
 print('Report written',sha(OUT/'REPORT_FINAL-ja.md'),flush=True)
def pack():
 import zipfile
 target=ROOT.parent/'deliverables/Ark_Capital_v7_Rank_Native_MAX3_20261005_PRIVATE.zip';assert not target.exists()
 allow=[]
 for folder in (INPUT,PRIVATE):
  for path in sorted(folder.rglob('*')):
   if path.is_file():allow.append(path)
 manifest={'exact_jst':now(),'reference_GitHub':f'https://github.com/Iam-2squared/ark-terminal/tree/{read(WORK/"latest_basis.json")["HEAD"]}/docs/evidence/capital-v7-rank-native-max3-20261005-v1','reference_basis':read(WORK/'latest_basis.json'),'final_status':'NO_GO','selectedCapitalCandidate':None,'selectedRankCandidate':'EXISTING_MOVE_P5','NEXT_BOTTLENECK':'MAX3_PHYSICAL_OCCUPANCY','fits':0,'primary_replays':2,'Oracle_solves':4,'teacher_regeneration':0,'rerun_completed_replay_or_Oracle':False,'source_scope':'Existing Development bytes only, protected/fresh unopened','repository_backed_code_report':'GitHub authority, intentionally not duplicated','files':{str(p.relative_to(WORK)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in allow}}
 with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in allow:z.write(p,str(p.relative_to(WORK)))
  z.writestr('MANIFEST.json',json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
 with zipfile.ZipFile(target) as z:
  assert z.testzip() is None
  for name,pin in manifest['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==pin['sha256']
 save(OUT/'PRIVATE_PACK_MANIFEST.json',{'exact_jst':now(),'filename':target.name,'bytes':target.stat().st_size,'sha256':sha(target),'members_N':len(allow)+1,'member_hash_verification_mismatch_N':0,'GitHub_reference':manifest['reference_GitHub'],'manifest':manifest,'contains_repository_code_report':False})
 print(json.dumps({'path':str(target),'bytes':target.stat().st_size,'sha256':sha(target),'members':len(allow)+1}),flush=True)
if __name__=='__main__':globals()[sys.argv[1]]()
