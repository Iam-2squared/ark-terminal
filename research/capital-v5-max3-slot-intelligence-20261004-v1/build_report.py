"""Final development readout; findings never feed back into policy."""
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from statistics import mean
def pct(v,places=4):return '—' if v is None else f'{v*100:.{places}f}%'
def money(v):return '—' if v is None else f'¥{v:,.2f}'
def table(headers,rows):
 return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(str(x) for x in row)+' |' for row in rows)+'\n'
def main():
 C=json.loads((FROZEN/'UPWARD_STAIRCASE_V4_MAX3_RESULT.json').read_text());V=json.loads((PRIVATE/f'{PROFILE}_RESULT.json').read_text());A=json.loads((OUT/'SLOT_QUALITY_AND_RESERVATION.json').read_text());O=json.loads((OUT/'ORACLE_UPPER_BOUND.json').read_text());G=json.loads((OUT/'OPPORTUNITY_AND_ORACLE_GAP.json').read_text());crit=json.loads((OUT/'SUCCESS_CRITERIA.json').read_text());paired=json.loads((OUT/'PAIRED_DAILY_DELTA_SUMMARY.json').read_text());audit=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text());supp=json.loads((OUT/'INDEPENDENT_SUPPLEMENT.json').read_text());oracle_audit=json.loads((OUT/'INDEPENDENT_ORACLE_AUDIT.json').read_text());canary=json.loads((OUT/'CAUSAL_CANARY_RESULTS.json').read_text());cfg=json.loads((OUT/'POLICY_PRECOMMIT.json').read_text());T=json.loads((OUT/'ARRIVAL_TABLE.json').read_text())
 assert audit['mismatch_N']==supp['mismatch_N']==oracle_audit['mismatch_N']==0
 qC=A['Control']['quality'];qV=A['v5']['quality'];mC=A['Control']['metrics'];mV=A['v5']['metrics']
 rows_=[('Daily geometric',pct(C['geometric_mean_daily_return']),pct(V['geometric_mean_daily_return'])),('rolling20 median',f'{C["rolling20_median"]:.8f}x',f'{V["rolling20_median"]:.8f}x'),('rolling20 max',f'{C["rolling20_maximum"]:.8f}x',f'{V["rolling20_maximum"]:.8f}x'),('Final Equity',money(C['final_equity']),money(V['final_equity'])),('MaxDD（分足MTM）',pct(C['max_drawdown']),pct(V['max_drawdown']))]
 for name in ('U5','U10'):
  c=mC[name];v=mV[name];rows_ += [(f'{name} funded',c['funded'],v['funded']),(f'rank-pass {name} conversion',f'{c["funded"]}/{c["denominator"]} = {pct(c["conversion"])}',f'{v["funded"]}/{v["denominator"]} = {pct(v["conversion"])}'),(f'{name} MAX3 missed',c['MAX3_miss'],v['MAX3_miss']),(f'{name} reserve-rejected',c['reserve_rejected'],v['reserve_rejected']),(f'{name} Net Slot Miss',c['Net_Slot_Miss'],v['Net_Slot_Miss']),(f'{name} cash/lot missed',c['cash_lot_miss'],v['cash_lot_miss'])]
 rows_ += [('Medium（3–<5%）',qC['Medium_N'],qV['Medium_N']),('<2% funded N / rate',f'{qC["below2_N"]} / {pct(qC["below2_rate"])}',f'{qV["below2_N"]} / {pct(qV["below2_rate"])}'),('<3% funded N / rate',f'{qC["below3_N"]} / {pct(qC["below3_rate"])}',f'{qV["below3_N"]} / {pct(qV["below3_rate"])}'),('Loser（realized<=0）',f'{qC["loser_N"]} / {pct(qC["loser_rate"])}',f'{qV["loser_N"]} / {pct(qV["loser_rate"])}'),('Mean utilization',pct(C['utilization_mean']),pct(V['utilization_mean'])),('Total funded',C['funded_N'],V['funded_N'])]
 report=f'Capital v5 MAX3 Slot Intelligence — CLOSED / STOP\n\n作成: {now()}。Repo: Iam-2squared/ark-terminal。Branch: capital-state9-vnext-20261004。instruction basis: `{BASIS}`。Policy: `CAPITAL_MAX_CONCURRENT_3_RESEARCH_POLICY_V1` / `{PROFILE}`。\n\n'
 report+=table(['指標','保存済みControl v4 Main/B_PLUS','v5 one-shot'],rows_)+'\n'
 report+=table(['Oracle / recovery','結果'],[('Oracle max feasible rank-pass U5',f'{O["maximum_feasible_U5"]}/113'),('Oracle U10 at maximum U5',f'{O["maximum_U10_conditional_on_max_U5"]}/47'),('Oracle Medium at maximum U5/U10',O['maximum_Medium_conditional_on_max_U5_U10']),('Control recovery',f'42/104 = {pct(G["Control_recovery"])}'),('v5 recovery',f'50/104 = {pct(G["v5_recovery"])}'),('remaining oracle gap',G['remaining_oracle_gap'])])+'\n'
 report+='**判定はSLOT_INTELLIGENCE_IMPROVED、CAPITAL_V5_IMPROVES。P1–P7、E1–E3はすべてPASS。North Starのrolling20 2倍は未達。** MAX3 blockerを減らしただけではなく、reserve reject込みのNet Slot MissもU5 66→58、U10 21→19に減った。U5のMAX3 miss38件減のうち30件はreserve rejectへ移り、差し引き8件が実際のfunded増となった。cash/lot U5は5件のまま。U10はMAX3 miss12件減、reserve10件増、Net改善2件とcash/lot改善1件によりfundedが3件増えた。\n\n'
 report+='Oracleはevaluation-onlyの物理上限。Entry/EXIT時刻、MAX3、現金、100株単位、same-symbol、15:20 cutoff、実行sourceを守る。v4のrank別capital capとutilizationは実戦policyの制約として緩和しているため、104件がそのまま実戦policyで達成可能という意味ではない。全38日を100万円から現金で連結し、U5→U10→Medium→turnoverのlexicographic最適化を行った。物理上限ではU5の9件が保有重なりで不可避、U5/U10のcount上限への追加cash missは0。Mediumも最大52件、最小turnoverは¥38,951,252.65。Oracle資産成績をPrimary成績に使わず、閾値選びにも使っていない。\n\n'
 report+='Oracle v1は100株固定でU5=104/U10=47を確認したが、Mediumがcash-relaxed52件に対して50件だったため全lexicographic目的の認証を停止した。履歴を残したうえで、oracle_v2の整数lot数量で104/47/52を認証した。独立実装は3-unit min-cost flowと別の整数計画で同じ上限・最小turnoverを再確認した。無効実行2 candidateは<2% cohortであり、113 U5/47 U10の母数に影響しない。\n\n'
 report+='**A. slot1 / slot2 / slot3品質**\n\nslot番号はBUY成功時の実際の1st/2nd/3rd位置で、再利用後もその時点の空き順で付与する。Control ledgerも同じ定義でread-only分析した。\n\n'
 slotrows=[]
 for arm in ('Control','v5'):
  for s in ('1','2','3'):
   q=A[arm]['slot_quality'][s];r=q['rank_counts'];slotrows.append((arm,s,q['N'],f'{r.get("S",0)}/{r.get("A",0)}/{r.get("B",0)}',q['U3_N'],q['Medium_N'],f'{q["U5_N"]} ({pct(q["U5_rate"],2)})',f'{q["U10_N"]} ({pct(q["U10_rate"],2)})',f'{q["below2_N"]} ({pct(q["below2_rate"],2)})',q['PF1_N'],f'{q["loser_N"]} ({pct(q["loser_rate"],2)})',pct(q['realized_mean']),pct(q['realized_median']),money(q['actual_pnl_jpy'])))
 report+=table(['arm','slot','N','S/A/B','U3','Medium','U5','U10','<2','realized>=+1%','loser','mean','median','actual PnL'],slotrows)+'\n'
 report+='3rd-slotはfunded85→50、U5件数16→16、U5率18.82%→32.00%、U10 6→7、PnL −¥67,528.55→−¥27,626.55。**3rd-slot品質はMIXED**：<2%率48.24%→52.00%、loser58.82%→68.00%、中央値−0.1000%→−0.5731%は悪化し、PnLも依然マイナス。slot2でU5が13→21へ増えたことが全体改善に寄与する。slotごとの異なる取引集合であり、効果を一意に因果帰属できない。\n\n'
 report+='**B. B reservation — funded vs reserve rejected**\n\n'
 rr=[]
 for arm,target,label in [('Control','B_funded','Control B funded'),('v5','B_funded','v5 B funded'),('v5','B_reserve_rejected','v5 B reserve rejected')]:
  q=A[arm][target];rr.append((label,q['N'],q['U3_N'],q['Medium_N'],f'{q["U5_N"]} / {pct(q["U5_rate"])}',f'{q["U10_N"]} / {pct(q["U10_rate"])}',f'{q["below2_N"]} / {pct(q["below2_rate"])}',pct(q['realized_mean']),pct(q['realized_median']),pct(q['loser_rate']),money(q.get('actual_pnl_jpy'))))
 report+=table(['B群','N','U3','Medium','U5','U10','<2','realized mean','median','loser','actual PnL'],rr)+'\n'
 report+='reserve181件の理由はSLOT2_RESERVE_FOR_FUTURE_QUALITY=76、SLOT3_RESERVE_FOR_FUTURE_QUALITY=105。Rejected BにはU5 30件、U10 10件、Medium22件を含む。rejectedのrealizedはFrozen EXITの評価専用returnであり、実際の投資PnLではない。全B297件のtimestamp/ML/rank/occupancy/quantiles/remaining probabilities/decision/reasonを保存し、U3/U5/U10/bucket/realizedは判断後にjoinした。MAX3/cash/lotによるB拒否はreserve拒否と分けて保存した。\n\n'
 report+='実装上の事前固定した解釈：同時Entry batchはv4順序を維持し、slot admission時のoccupancyは「既存position + 先にslot admissionを通過した同batch候補」。その後、v4の同時ML proportional allocation / water-fillをそのまま適用する。cash/lot不足でも後続候補をbackfillしない。BUY成功による実occupancyも別に記録する。これによりv4のbatch配分とno forced backfillを維持した。\n\n'
 report+='training-only arrivalは各blockの保存済みH2/H3/H5でそのblockの過去training candidateだけを再scoreした推論で、新規fitは0。これはtraining内のresubstitution推定であり、到来推定そのもののfresh/OOS精度を示さない。全training日を含め、残存0日も母数に算入した。固定30分bucketの表示分布は下端時刻をanchorにするが、判断では実際の現在分tから15:20未満までの残存curveを用いた。同時刻を含む `t<=arrival<920` として事前固定し、test-sessionの実際の後続arrivalは見ていない。A+はS/A（ML>=1.5）、B quantileはprecutoffの1<=ML<1.5をlinear type7で算出した。\n\n'
 report+=table(['block','train sessions','train candidate N','B N','B median ML','B p75 ML'],[(b,z['training_session_N'],z['training_candidate_N'],z['training_B_N'],f'{z["B_median"]:.8f}',f'{z["B_p75"]:.8f}') for b,z in T.items()])+'\n'
 report+='**C. opportunity cost / Oracle gap**\n\n'
 opprows=[]
 for arm in ('Control','v5'):
  for winner,z in G['opportunity'][arm].items():opp_rows=(arm,winner,z['all_rank_pass_arrivals_N'],z['arrived_slot_free_N'],z['arrived_slot_occupied_N'],z['later_arrived_slot_free_N'],z['later_arrived_slot_occupied_N'],z['HELD_SLOT_BLOCKED_N'],z['RESERVE_REJECTED_N'],z['cash_lot_missed_N']);opprows.append(opp_rows)
 report+=table(['arm','cohort','rank-pass N','arrived free','arrived occupied','later free','later occupied','HELD_SLOT_BLOCKED','reserve reject','cash/lot'],opprows)+'\n'
 report+='laterは同sessionの最初のfunded Entryより後の時刻。HELD_SLOT_BLOCKEDは、MAX3拒否・前batchからのpositionあり・当該batchのrank-pass上位3候補という固定診断定義。実際のheld IDも保存する。Oracle gapはControl62件→v5 54件。score未達U5 57件、U10 20件の救済は行っていない。\n\n'
 report+='**D. Entry→High buckets（funded）**\n\n'
 br=[]
 for b in ('<1','1-<2','2-<3','3-<4','4-<5','5-<10','>=10'):
  c=A['Control']['entry_high_buckets'][b];v=A['v5']['entry_high_buckets'][b];br.append((b,c['candidate_N'],c['N'],v['N'],pct(c['realized_mean']),pct(v['realized_mean']),money(c['actual_pnl_jpy']),money(v['actual_pnl_jpy'])))
 report+=table(['Entry→High %','all OOF candidate N','Control funded','v5 funded','Control mean realized','v5 mean realized','Control actual PnL','v5 actual PnL'],br)+'\n'
 report+='U3=297件、Medium=127件、U5=170件、U10=67件という全OOF母数を維持。評価teacherとHigh定義はv4原本のまま。strictly later actual Highなしのfallback0など、既存のteacher support制限も変更していない。\n\n'
 report+='**E. daily / rolling20 / asset curve**\n\n'
 erows=[('有効日数',C['valid_primary_day_N'],V['valid_primary_day_N']),('daily arithmetic',pct(C['arithmetic_mean_daily_return']),pct(V['arithmetic_mean_daily_return'])),('daily median',pct(C['median_daily_return']),pct(V['median_daily_return'])),('rolling20 valid',C['valid_rolling20_window_N'],V['valid_rolling20_window_N'])]
 for label,key in [('rolling20 min','rolling20_minimum'),('rolling20 mean','rolling20_arithmetic_mean')]:erows.append((label,f'{C[key]:.8f}x',f'{V[key]:.8f}x'))
 erows += [('rolling20 2x N/rate',f'{C["north_star_hit_N"]}/19 / {pct(C["north_star_hit_rate"])}',f'{V["north_star_hit_N"]}/19 / {pct(V["north_star_hit_rate"])}'),('earliest 2x','なし','なし'),('¥1m rolling20 median',money(C['rolling20_median']*1e6),money(V['rolling20_median']*1e6)),('¥1m rolling20 max',money(C['maximum_20_session_amount']),money(V['maximum_20_session_amount'])),('Final return',pct(C['total_return']),pct(V['total_return'])),('median utilization',pct(C['utilization_median']),pct(V['utilization_median'])),('time utilization>=80%',pct(C['time_utilization_ge80']),pct(V['time_utilization_ge80'])),('time utilization>=90%',pct(C['time_utilization_ge90']),pct(V['time_utilization_ge90'])),('minimum cash',money(C['cash_minimum']),money(V['cash_minimum'])),('turnover',money(C['turnover_cash_jpy']),money(V['turnover_cash_jpy'])),('recycled cash used',money(C['capital_recycling_used_jpy']),money(V['capital_recycling_used_jpy'])),('funded/session',f'{C["avg_funded_per_session"]:.6f}',f'{V["avg_funded_per_session"]:.6f}'),('max concurrent',C['max_concurrent_actual'],V['max_concurrent_actual']),('Frozen EXIT sells',C['Frozen_exit_N'],V['Frozen_exit_N']),('EOD regular/auction',f'{C["EOD_regular_N"]}/{C["EOD_auction_N"]}',f'{V["EOD_regular_N"]}/{V["EOD_auction_N"]}')]
 report+=table(['経済指標','Control','v5'],erows)+'\n'
 report+=f'paired daily delta：38日、平均{paired["mean_delta"]*100:.4f}pp、中央値{paired["median_delta"]*100:.4f}pp、v5優位{paired["positive_delta_days"]}日／劣位{paired["negative_delta_days"]}日／同値{paired["equal_delta_days"]}日。Final差は{money(V["final_equity"]-C["final_equity"])}。全38日の資産・returnと全19 rolling窓はPAIRED_DAILY.csv / PAIRED_ROLLING20.csvに保存。daily medianは小幅低下し、平均稼働率は7.17pp低下。Mediumは4件減（31→27）、全体loser率は0.60pp悪化した。これらは今回の改善判定と併記する代償であり、結果を受けた再調整は行わない。\n\n'
 plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
 fig,ax=plt.subplots(2,2,figsize=(13,8),layout='constrained');colors=('#3864d9','#e67e22');x=np.arange(39)
 for label,r,col in [('Control v4',C,colors[0]),('v5 slot reserve',V,colors[1])]:
  ax[0,0].plot(x,[1]+[float(d['ending_cash'])/1e6 for d in r['daily_series']],label=label,color=col,linewidth=2)
  ax[0,1].plot(np.arange(1,20),[d['growth_multiple'] for d in r['rolling20_windows']],label=label,color=col,linewidth=2)
 ax[0,0].set(title='Asset curve (38 Development sessions)',xlabel='Session',ylabel='Equity (million JPY)');ax[0,0].legend()
 ax[0,1].set(title='Rolling 20-session growth',xlabel='Window',ylabel='Multiple');ax[0,1].axhline(2,color='#bbb',linestyle='--');ax[0,1].set_ylim(1.0,2.03)
 delta=[(v['daily_return']-c['daily_return'])*100 for c,v in zip(C['daily_series'],V['daily_series'])];ax[1,0].bar(np.arange(1,39),delta,color=[colors[1] if d>=0 else colors[0] for d in delta]);ax[1,0].axhline(0,color='#555',linewidth=.7);ax[1,0].set(title='Paired daily return delta: v5 - Control',xlabel='Session',ylabel='Percentage points')
 idx=np.arange(2);ax[1,1].bar(idx-.18,[mC['U5']['Net_Slot_Miss'],mC['U10']['Net_Slot_Miss']],.36,label='Control',color=colors[0]);ax[1,1].bar(idx+.18,[mV['U5']['Net_Slot_Miss'],mV['U10']['Net_Slot_Miss']],.36,label='v5',color=colors[1]);ax[1,1].set(xticks=idx,xticklabels=['U5','U10'],ylabel='MAX3 + reserve missed N',title='Net Slot Miss (fixed rank-pass cohorts)');ax[1,1].legend()
 for z in ax.ravel():z.grid(axis='y',alpha=.18);z.set_axisbelow(True)
 fig.suptitle('Capital v5 | fixed model/rank | MAX3 | Development evidence',fontsize=15)
 fig.savefig(PRIVATE/'CAPITAL_V5_ECONOMIC_AND_SLOT_CURVES.png',dpi=170);fig.savefig(OUT/'ECONOMIC_AND_SLOT_CURVES.svg');plt.close(fig)
 report+='![Asset, rolling20, paired daily delta and Net Slot Miss](ECONOMIC_AND_SLOT_CURVES.svg)\n\n'
 report+='**F. integrity / exposure / safety**\n\n'
 report+=f'独立監査：core {audit["check_N"]:,}項目、supplement {supp["check_N"]:,}項目、合計{audit["check_N"]+supp["check_N"]:,}項目でmismatch0。Oracle別実装もmismatch0。Primary policy/replay codeのimport0。training8,161行とOOF1,039行をscalar inference、別PAVA projection、linear quantileで確認し、slot判断、ordering、quantity、allocation、BUY/SELL、MTM、cash recycling、daily/rolling20、conversion、MAX3/reserve/Net missを照合した。Controlは保存済みledgerのread-only再集計のみでreplay0。金額ledger/quantity/decisionの差は0、floating summary許容1e-12、desired/金額summary許容1e-8。\n\n'
 report+=f'因果Canary {canary["PASS_N"]} PASS / FAIL0。test future arrival、未来teacher/High、未来EXIT、未来State/Path suffix、same-batch outcomes、Liquidity mutationで現在判断不変。コード・source・model・score・precommit identityを確認。全stream deterministic rerunは結果・decisions・trades・frames・intentsともbyte identity。no forced backfill、MTMでequityだけ変化しcash不変、valid EOD SELLだけcash解放、duplicate sell0をsynthetic executionで検査した。Primary one-shot replay1、Independent replay1、deterministic full canary rerun1、causal/synthetic day mini-replay6。verificationは同一policyの照合であり、新policyやretuneを含まない。\n\n'
 report+='H2/H3/H5・PAVA・ML・S/A/B・feature manifest・Liquidity OFF・Entry/EXIT/MTM/EOD/cost・100-share・LONG cash-only・MAX3は固定。new fit0 / rank変更0 / Movement0 / HF1-HL0 use0 / MAX4-MAX5 0 / position replacement0 / provider取得0 / retune0 / Claude0。BUY raw×1.0005、SELL valid source×0.9995、commission0、15:20 Entry funding0、later topup0。旧Evidence上書き0。GitHub checkpoint V0–V10と各postcommit actual GET receiptは別ファイルに保存する。未来SHAは予測しない。\n\n'
 report+='ExposureはITERATIVE_DEVELOPMENT_EVIDENCE。58 Development sessionsは反復利用済みで、38 OOF daysをfresh/OOSと呼ばない。Protected/Holdout/Fresh/Validation/OOS/Prospective開封0。Safety全false、orders0 / main merge0 / force push0 / productionReady=false。\n\n'
 report+=table(['criterion','結果'],[(k,'PASS' if v else 'FAIL') for k,v in (crit['P']|crit['E']).items()])+'\n'
 report+='**結果固定・STOP。** Oracle + precommitted policy1本 + audit + reportで終了する。MAX3 blockerを減らしただけでなくreserve reject込みのNet Slot Missも減った。ただしoracle gap54件、3rd-slot contamination/loser悪化、Medium減、低稼働率、North Star未達が残る。同cycleでarrival threshold/time boundary/B quantile/Winner model/rank/Movement/Liquidity/MAX/replacement/Entry/EXIT/result rescueを変更しない。\n'
 save(OUT/'REPORT_RESULT_FACTS.json',{'JST':now(),'criteria':crit,'Third_slot_quality':'MIXED','medium_change':-4,'Loser_rate_change_pp':(qV['loser_rate']-qC['loser_rate'])*100,'Oracle_gap':G['remaining_oracle_gap'],'Final_equity_delta':V['final_equity']-C['final_equity']})
 with (OUT/'REPORT_FINAL-ja.md').open('x',encoding='utf8') as f:f.write(report)
 checkpoint('V9_NORTH_STAR_AND_FINAL_REPORT','REPORT_FIXED_NORTH_STAR_NOT_REACHED',{'SLOT_INTELLIGENCE':crit['SLOT_INTELLIGENCE'],'CAPITAL_V5':crit['CAPITAL_V5'],'North_Star':'NOT_REACHED','report_sha256':sha(OUT/'REPORT_FINAL-ja.md'),'third_slot_quality':'MIXED'},next_direction='Publish closure receipts, deliver the fixed private package, STOP; no retune.')
 print(json.dumps({'report_bytes':len(report.encode()),'figure':str(PRIVATE/'CAPITAL_V5_ECONOMIC_AND_SLOT_CURVES.png'),'criteria':crit['SLOT_INTELLIGENCE']}))
if __name__=='__main__':main()
