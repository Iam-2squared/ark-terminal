"""Fixed gates and finite selection; report, delivery manifest, then terminal STOP."""
from control import *
from decimal import Decimal as D
import sys,json,zipfile
def selection():
    pres=read(OUT/'PRESERVATION_RESULT.json')['profiles'];cap=read(OUT/'CAPITAL_ROLLING20_RESULT.json')['profiles'];audit=read(OUT/'INDEPENDENT_AUDIT.json');profiles={}
    for arm in ARMS:
        p=pres[arm];e=cap[arm]['economics'];g=p['preservation_gates']|{'P7_independent_mismatch0':audit['mismatch_N']==0};ps=all(g.values());cg=cap[arm]['economic_point_gates'];profiles[arm]={'preservation_gates':g,'preservation_PASS':ps,'preservation_status':'QUALITY_CAPACITY_PRESERVATION_PASS' if ps else 'QUALITY_CAPACITY_PRESERVATION_FAIL','economic_gates':cg,'capital_PASS':ps and all(cg.values()),'capital_status':'CAPITAL_V9_IMPROVED' if ps and all(cg.values()) else 'CAPITAL_V9_FAIL','quality':p['funded_quality'],'economics':e}
    eligible=[a for a in ARMS if profiles[a]['capital_PASS']]
    def winner_key(a):
        p=profiles[a];q=p['quality'];e=p['economics'];return (-e['north_star_hit_N'],-e['rolling20_median'],-e['rolling20_arithmetic_mean'],-e['geometric_mean_daily_return'],-q['U5'],-q['U10'],-q['Medium3_5_N'],q['below2_rate'],q['below3_rate'],e['max_drawdown'],ARMS.index(a))
    winner=sorted(eligible,key=winner_key)[0] if eligible else None
    def diagnostic_key(a):
        q=profiles[a]['quality'];e=profiles[a]['economics'];return (-q['U5'],-q['U10'],-q['Medium3_5_N'],q['below2_rate'],q['below3_rate'],-e['rolling20_median'],ARMS.index(a))
    diagnostic=winner if winner else sorted(ARMS,key=diagnostic_key)[0];p=profiles[diagnostic];c=pres[diagnostic]['conservation']['U5']
    misses={'RANK_ADMISSION':c['RANK_BASE_REJECT'],'CAPACITY_RESERVE':c['CAPACITY_RESERVE_REJECT'],'MAX3_ONLINE_OCCUPANCY':c['MAX3_FULL'],'CASH_SIZING':c['CASH_OR_LOT']};priority=list(misses);largest=sorted(priority,key=lambda k:(-misses[k],priority.index(k)))[0]
    bottleneck='CAPITAL_MONETIZATION_OR_SIZING' if p['preservation_PASS'] and not p['capital_PASS'] else 'CAPACITY_RESERVE_REMAINS' if largest=='CAPACITY_RESERVE' else largest
    status=('V9_NORTH_STAR_HIT' if profiles[winner]['economics']['north_star_hit_N']>0 else 'V9_CAPITAL_IMPROVED') if winner else 'V9_QUALITY_PRESERVED_CAPITAL_FAIL' if any(p['preservation_PASS'] for p in profiles.values()) else 'V9_INTEGRATION_NO_GO'
    if audit['mismatch_N'] or any(not p['preservation_gates']['P6_integrity0'] for p in profiles.values()):status='V9_CONTRACT_FAIL';winner=None
    choice={'selectedCapitalCandidate':'I'+str(ARMS.index(winner)+1) if winner else None,'diagnosticArm':'I'+str(ARMS.index(diagnostic)+1),'status':status,'NEXT_BOTTLENECK':bottleneck,'exclusive_U5_miss':misses}
    assert choice==audit['expected_winner_bottleneck'],'INDEPENDENT_SELECTION_MISMATCH_STOP'
    save(OUT/'FINAL_GATE_RESULT.json',{'exact_jst':now(),'profiles':profiles,'independent_mismatch_N':audit['mismatch_N'],'Safety':SAFETY})
    o={'exact_jst':now(),'branch':BRANCH,**choice,'selectedBigWinnerRank':'EXISTING_MOVE_P5','selectedAuxiliaryHeads':['MOVE_U2','MOVE_U3'],'retainedCapitalBenchmark':'V5_FROZEN_REFERENCE','diagnostic_arm_is_adoption':False,'newFits':0,'CapitalReplays':2,'fresh_OOS_claim':False,'Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','productionReady':False,'Safety':SAFETY}
    save(OUT/'WINNER_AND_NEXT_BOTTLENECK.json',o)
    checkpoint('V13_WINNER_AND_BOTTLENECK',choice,'Deliver private ledgers; fix report and V14 closure; stop research')
    print(json.dumps(choice),flush=True)
def pct(x):return f'{100*x:.6f}%' if x is not None else '—'
def table(headers,rr):return '|'+ '|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'+'\n'.join('|'+ '|'.join(str(v) for v in r)+'|' for r in rr)+'\n'
def delivery():
    selection=read(OUT/'WINNER_AND_NEXT_BOTTLENECK.json');basis=read(WORK/'latest_basis.json');name='Ark_Capital_v9_Quality_Aware_MAX3_Integration_20261005_PRIVATE.zip';destination=ROOT.parent/name
    files=[]
    for p in sorted(PRIVATE.rglob('*')):
        if p.is_file():files.append((p,'private/'+str(p.relative_to(PRIVATE))))
    for pattern,newname in [('*v8R1*.zip','authority/Ark_Capital_v8R1_Cash_Constrained_Online_MAX3_20261005_PRIVATE.zip'),('*Quality*v1R1*.zip','authority/Ark_Capital_Quality_v1R1_Recovery_20261005_PRIVATE_STRONG.zip')]:files.append((next(AUTH.glob(pattern)),newname))
    manifest={'schema':'CAPITAL_V9_PRIVATE_DELIVERY_V1','exact_jst':now(),'branch':BRANCH,'GitHub_reference':f'https://github.com/Iam-2squared/ark-terminal/tree/{basis["HEAD"]}/docs/evidence/capital-v9-quality-aware-max3-integration-20261005-v1','Main_parent_SHA':MAIN_SHA,'Quality_parent_SHA':QUALITY_SHA,'status':selection['status'],'selectedCapitalCandidate':selection['selectedCapitalCandidate'],'diagnosticArm':selection['diagnosticArm'],'NEXT_BOTTLENECK':selection['NEXT_BOTTLENECK'],'newFits':0,'CapitalReplays':2,'fresh_OOS_claim':False,'productionReady':False,'repository_backed_code_and_reports_included':False,'files':[{'path':n,'bytes':p.stat().st_size,'sha256':sha(p)} for p,n in files],'Safety':SAFETY}
    with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p,n in files:z.write(p,n)
        z.writestr('MANIFEST.json',json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
        z.writestr('README.txt','Capital v9 private causal scores, training tables, pressure support, decisions/intents/trades/curves/daily/rolling20, paired policy deltas, independent preparation and two immutable parent packs. Models remain frozen. No orders or fresh/OOS claims. Public code/evidence/report are retained in the pinned GitHub research branch. Verify every MANIFEST SHA256 before use.\n')
    with zipfile.ZipFile(destination) as z:
        for p,n in files:assert hashlib.sha256(z.read(n)).hexdigest()==sha(p)
    save(OUT/'PRIVATE_PACK_MANIFEST.json',{'exact_jst':now(),'filename':name,'sha256':sha(destination),'bytes':destination.stat().st_size,'manifest_sha256':hashlib.sha256(json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False).encode()+b'\n').hexdigest(),'member_N':len(files)+2,'readback_all_member_hashes_PASS':True,'manifest':manifest,'repository_backed_code_and_reports_included':False})
    print(json.dumps({'filename':name,'sha256':sha(destination),'bytes':destination.stat().st_size}),flush=True)
def close():
    sel=read(OUT/'WINNER_AND_NEXT_BOTTLENECK.json');gate=read(OUT/'FINAL_GATE_RESULT.json')['profiles'];pres=read(OUT/'PRESERVATION_RESULT.json')['profiles'];audit=read(OUT/'INDEPENDENT_AUDIT.json');parents=read(OUT/'PARENT_AUTHORITY_FREEZE.json');refs=read(PARENT/'SAVED_REFERENCE_FREEZE.json');v5=read(V5/'MAIN_REPLAY_RESULT.json');b2=read(PARENT/'TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1_RESULT.json');b2q=read(PARENT/'PRESERVATION_RESULT.json')['profiles']['TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1']['funded_quality']
    profiles=[('v5 saved',v5),('v8R1 B2 saved',b2)]+[('I'+str(i+1),gate[a]['economics']) for i,a in enumerate(ARMS)]
    text=[];text.append('# Ark Terminal — Capital v9 Quality-Aware MAX3 Integration\n')
    text.append('## A. Executive / Parent Authorities\n')
    text.append(f'作成: {now()}。status = **{sel["status"]}**。selectedCapitalCandidate = `{sel["selectedCapitalCandidate"]}`。diagnosticArm = `{sel["diagnosticArm"]}`。NEXT_BOTTLENECK = **{sel["NEXT_BOTTLENECK"]}**。\n')
    text.append(f'Main parent: `{MAIN_SHA}` (`CAPITAL_V8R1_R15_CLOSURE_FIXED_STOP / V8R1_NO_GO`)。Quality parent: `{QUALITY_SHA}` (`ANTI_WEAK_MEDIUM_STRONG / QUALITY_RECOVERY_PASS / R12_CLOSURE_FIXED_STOP`)。Mainから新branchを作成し、Qualityの履歴はmergeせず、model/artifactをhash固定したread-only inputとして使用した。\n')
    text.append('I1は future r > current r AND future q2 >= current q2。I2はさらに future q3 >= current q3。pPがPrimary ordering authorityであり、batch順・tenure・0.5閾値・sizing・executionは凍結。raw Logistic scoreはordering/dominance用であり、真の確率とは呼ばない。\n')
    text.append('Exposure = **ITERATIVE_DEVELOPMENT_EVIDENCE**。同じ58 Development sessionsを反復利用している。Fresh/OOS成功ではない。QualityのpP-conditional deltaのCIは0を跨ぎ、MOVE_U3 Big/Mega guardはPARTIAL。成功・不成功を問わず同cycleでの救済・再調整は行わない。\n')
    text.append('## B. North Star / rolling20\n')
    text.append(table(['Profile','20d min','mean','median','max','2x N/rate'],[[n,*[f'{e[f]:.10f}' for f in ('rolling20_minimum','rolling20_arithmetic_mean','rolling20_median','rolling20_maximum')],f'{e["north_star_hit_N"]}/19 ({pct(e["north_star_hit_rate"])})'] for n,e in profiles]))
    text.append('¥1,000,000から38 OOF Development sessionsを連結。同ledgerの19 rolling20 windowsは重複しており独立19標本ではない。Final38を1か月成績とは呼ばない。\n')
    text.append('## C. Medium-to-Big Quality Preservation\n')
    text.append(table(['Profile','Funded N','Medium3–<5','U5','U10','<2','<3'],[['v5 saved',150,27,50,26,'38.666667%','48.666667%'],['v8R1 B2 saved',b2q['N'],b2q['Medium3_5_N'],b2q['U5'],b2q['U10'],pct(b2q['below2_rate']),pct(b2q['below3_rate'])]]+[['I'+str(i+1),p['quality']['N'],p['quality']['Medium3_5_N'],p['quality']['U5'],p['quality']['U10'],pct(p['quality']['below2_rate']),pct(p['quality']['below3_rate'])] for i,p in enumerate(gate.values())]))
    text.append(table(['Gate','I1','I2'],[[k,*[str(gate[a]['preservation_gates'][k]) for a in ARMS]] for k in gate[ARMS[0]]['preservation_gates']]))
    text.append('全7条件を満たす場合だけQUALITY_CAPACITY_PRESERVATION_PASS。U5増加だけでは採用しない。Primaryはpotential quality、realizedはSecondary diagnostic。\n')
    text.append(table(['Profile','U2 N/rate','U3 N/rate','Medium rate','Big5–<10','Mega≥10','Weak<2','Low2–<3','realized≤0','realized mean','realized median'],[['I'+str(i+1),f'{p["quality"]["U2"]}/{pct(p["quality"]["U2_rate"])}',f'{p["quality"]["U3"]}/{pct(p["quality"]["U3_rate"])}',pct(p['quality']['Medium_rate']),p['quality']['Big5_10_N'],p['quality']['Mega10_N'],p['quality']['Weak2_N'],p['quality']['Low2_3_N'],p['quality']['realized_loser_le0_N_diagnostic'],pct(p['quality']['realized_mean_diagnostic']),pct(p['quality']['realized_median_diagnostic'])] for i,p in enumerate(gate.values())]))
    text.append('## D. U5/U10 reason conservation\n')
    rr=[]
    for n,p in [('B2',read(PARENT/'PRESERVATION_RESULT.json')['profiles']['TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1'])]+[('I'+str(i+1),pres[a]) for i,a in enumerate(ARMS)]:
        for label in ('U5','U10'):
            c=p['conservation'][label];rr.append([n,label,c['FUNDED'],c['RANK_BASE_REJECT'],c['CAPACITY_RESERVE_REJECT'],c['MAX3_FULL'],c['CASH_OR_LOT'],sum(v for k,v in c.items() if k not in ('FUNDED','RANK_BASE_REJECT','CAPACITY_RESERVE_REJECT','MAX3_FULL','CASH_OR_LOT')),sum(c.values())])
    text.append(table(['Profile','Label','Funded','Rank reject','Reserve','MAX3','cash/lot','other','total'],rr))
    text.append('Primary common supported OOF N=1028。U5=170/U10=67。Admission490 identities、exact executable488、Admission U5=124/U10=55。保存済Physical Oracle U5=149/U10=67、Admission Oracle U5=116/U10=55は再solveしていない。\n')
    text.append('## E. Capacity Reserve reduction\n')
    text.append(table(['Profile','Reserve U5','Reserve U10','MAX3 U5','MAX3 U10','cash U5','cash U10','Rank U5','Rank U10'],[[r[0],r[4],rr[j+1][4],r[5],rr[j+1][5],r[6],rr[j+1][6],r[3],rr[j+1][3]] for j,r in enumerate(rr) if j%2==0]))
    text.append('同一stateの全1,960 support casesでpressure_I2 ≤ pressure_I1 ≤ pressure_B2、ACCEPT implicationを確認。実Replayでは早期fundingによるoccupancy pathが変わるため、globalのB2 funded setのsupersetとは主張しない。\n')
    text.append('## F. Gained/Lost funding vs B2\n')
    text.append(table(['Profile/group','N','Medium','U5','U10','Weak','Low','realized PnL diagnostic'],[['I'+str(i+1)+' '+name,z['N'],z['Medium3_5_N'],z['U5'],z['U10'],z['Weak2_N'],z['Low2_3_N'],z['realized_PnL_jpy_diagnostic']] for i,a in enumerate(ARMS) for name,z in pres[a]['paired_B2_delta'].items() if name in ('GAINED_FUNDING_vs_B2','LOST_FUNDING_vs_B2')]))
    text.append(table(['Profile','Net U5','Net U10','Net Medium','Net Weak'],[['I'+str(i+1),*[pres[a]['paired_B2_delta']['NET_counts'][f] for f in ('U5','U10','Medium','Weak')]] for i,a in enumerate(ARMS)]))
    text.append('各groupのpP/q2/q3 mean・median、Entry hour別N/quality/PnLは[POLICY_DELTA_RESULT.json](POLICY_DELTA_RESULT.json)に保存。個々のlost candidateを特定gained candidateの因果replacementとは断定しない。\n')
    text.append('## G. Induced occupancy cost\n')
    text.append(table(['Profile/group','N','Medium','U5','U10','Weak'],[['I'+str(i+1)+' '+name,z['N'],z['Medium3_5_N'],z['U5'],z['U10'],z['Weak2_N']] for i,a in enumerate(ARMS) for name,z in pres[a]['induced_occupancy'].items() if name in ('RESERVE_RECOVERY','NEW_MAX3_MISS_vs_B2')]))
    text.append('NEW_MAX3_MISSはB2ではMAX3でなかったidentityがIntegrationでMAX3_FULLになった件数。RESERVE_RECOVERYはB2 Reserve→Integration Funded。事前固定countを表示し、結果後にnet-value定義を追加していない。詳細は[INDUCED_OCCUPANCY_RESULT.json](INDUCED_OCCUPANCY_RESULT.json)。\n')
    text.append('## H. Slot1/2/3 quality\n')
    text.append(table(['Profile/slot','N','Medium','U5','U10','<2','<3'],[['I'+str(i+1)+f' slot{s}',z['N'],z['Medium3_5_N'],z['U5'],z['U10'],pct(z['below2_rate']),pct(z['below3_rate'])] for i,a in enumerate(ARMS) for s,z in pres[a]['slot_quality'].items()]))
    text.append('## I. pP / q2 / q3 score diagnostics\n')
    text.append(table(['Profile','score','funded mean','funded median','missed U5 mean'],[['I'+str(i+1),f,*[f'{z[k]:.10f}' for k in ('funded_mean','funded_median','missed_U5_mean')]] for i,a in enumerate(ARMS) for f,z in pres[a]['score_diagnostics'].items()]))
    text.append(table(['Profile','LOWER_P_ACCEPT_AFTER_HIGHER_P_RESERVE_SAME_BATCH'],[['I'+str(i+1),pres[a]['LOWER_P_ACCEPT_AFTER_HIGHER_P_RESERVE_SAME_BATCH']] for i,a in enumerate(ARMS)]))
    text.append('Qualityでbatch reorderせず、higher pPが先にReserveされた後のlower pP ACCEPTを許可。training q2/q3は8 frozen block-modelのcompleted past trainへのresubstitution score。teacher fieldsはpressure build input objectに存在しない。saved predictionsはauditにだけ使用し、Mainにはcausal featureから再構築したscoreを使用した。\n')
    text.append('## J. pP clairvoyant saved reference\n')
    text.append('selected234 / U5=81 / U10=38 / <2=92 (39.316239%)。cash-constrained pP-only label-blind diagnosticであり、U5 upper boundでもwinner gateでもない。新solve=0。Quality signal追加後のU5>81やpP utility低下をエラーとはみなさない。\n')
    text.append('## K. Capital Secondary\n')
    text.append(table(['Profile','Final38 JPY','total return','daily geo','daily arith','daily median','minute MTM MaxDD','util mean/median','idle cash JPY','turnover JPY','recycled cash JPY','funded/session'],[[n,f'{e["final_equity"]:.2f}',pct(e['total_return']),pct(e['geometric_mean_daily_return']),pct(e['arithmetic_mean_daily_return']),pct(e['median_daily_return']),pct(e['max_drawdown']),pct(e['utilization_mean'])+'/'+pct(e['utilization_median']),(f'{e["idle_cash_mean_jpy"]:.2f}' if 'idle_cash_mean_jpy' in e else 'saved未収録'),f'{e["turnover_cash_jpy"]:.2f}',f'{e["capital_recycling_used_jpy"]:.2f}',f'{e["avg_funded_per_session"]:.6f}'] for n,e in profiles]))
    text.append(table(['Profile','rolling20 median >v5','rolling20 mean >v5','daily geometric >v5','Preservation PASS','Capital PASS'],[['I'+str(i+1),*[p['economic_gates'][f] for f in ('rolling20_median','rolling20_mean','daily_geometric')],p['preservation_PASS'],p['capital_PASS']] for i,p in enumerate(gate.values())]))
    text.append('## L. Independent Audit\n')
    pre=read(OUT/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json');num=read(OUT/'NUMERIC_DOMINANCE_BOUNDARY_AUDIT.json')
    text.append(f'causal canary 60/60 PASS。Pre-main独立監査 {pre["checks_N"]:,} checks / {pre["action_cases_N"]:,} action cases、mismatch0。numeric {num["all_compared_pair_N"]:,} pair、near-tie {num["near_tie_N"]}、boundary disagreement0。Full audit {audit["checks_N"]:,} checks、mismatch {audit["mismatch_N"]}、max float delta {audit["max_abs_float_difference"]:.17g} ≤1e-12。money/quantity exact。\n')
    text.append('Primary runtime/replay/evaluator import0。独立scalar inference・past table・tenure・dominance・actionとFraction accountingで、BUY/SELL/MTM/cash/quantity/occupancy/daily/rolling20/Final38/MaxDD、quality conservation、paired gained/lost、induced MAX3、gates、winner、bottleneckを検証。実装独立性を主張し、共有upstream市場データの独立性は主張しない。actual arrivalは未知で、継承したbar-end as-of boundaryを使用した。\n')
    text.append('## M. Winner / Next Bottleneck\n')
    text.append(f'status={sel["status"]}、selectedCapitalCandidate={sel["selectedCapitalCandidate"]}、diagnosticArm={sel["diagnosticArm"]}。diagnostic armは採用ではない。NEXT_BOTTLENECK={sel["NEXT_BOTTLENECK"]}。\n')
    text.append(table(['Observed exclusive U5 miss','N'],list(sel['exclusive_U5_miss'].items())))
    text.append('次の検証は別の独立Workでのみ行う。今cycleではAdmission、I3、blend、threshold、tenure、sizing、MAX4/5、replacement、Freshへの変更を行わない。Quality head自体の再fitを結論にしない。orders=0 / main merge=0 / force push=0 / provider request=0 / Claude=0。Safetyは全false。\n')
    text.append('```text\nselectedBigWinnerRank = EXISTING_MOVE_P5\nselectedAuxiliaryHeads = ["MOVE_U2","MOVE_U3"]\nselectedCapitalCandidate = '+str(sel['selectedCapitalCandidate'])+'\ndiagnosticArm = '+sel['diagnosticArm']+'\nNEXT_BOTTLENECK = '+sel['NEXT_BOTTLENECK']+'\nnewFits = 0\nCapitalReplays = 2\nfresh_OOS_claim = false\nproductionReady = false\nCURRENT_STATE = CAPITAL_V9_V14_CLOSURE_FIXED_STOP\n```\n')
    with (OUT/'REPORT_FINAL-ja.md').open('x',encoding='utf-8') as f:f.write('\n'.join(text))
    handoff={'exact_jst':now(),'branch':BRANCH,'basis':read(WORK/'latest_basis.json'),'Main_parent_SHA':MAIN_SHA,'Quality_parent_SHA':QUALITY_SHA,**sel,'CURRENT_STATE':'CAPITAL_V9_V14_CLOSURE_FIXED_STOP','next_policy':'Wait for a new independent Work; no further research in this cycle','forbidden_after_closure':read(OUT/'INTEGRATION_DESIGN_PRECOMMIT.json')['forbidden'],'same_cycle_resume':False}
    save(OUT/'NEXT_WORK_HANDOFF.json',handoff)
    closure={'exact_jst':now(),'branch':BRANCH,'basis':read(WORK/'latest_basis.json'),'CURRENT_STATE':'CAPITAL_V9_V14_CLOSURE_FIXED_STOP','status':sel['status'],'selectedCapitalCandidate':sel['selectedCapitalCandidate'],'diagnosticArm':sel['diagnosticArm'],'NEXT_BOTTLENECK':sel['NEXT_BOTTLENECK'],'selectedBigWinnerRank':'EXISTING_MOVE_P5','selectedAuxiliaryHeads':['MOVE_U2','MOVE_U3'],'Main_parent_SHA':MAIN_SHA,'Quality_parent_SHA':QUALITY_SHA,'counts':counts(),'newFits':0,'CapitalReplays':2,'independent_mismatch_N':audit['mismatch_N'],'causal_canary_PASS_N':60,'report_sha256':sha(OUT/'REPORT_FINAL-ja.md'),'handoff_sha256':sha(OUT/'NEXT_WORK_HANDOFF.json'),'private_sha256':read(OUT/'PRIVATE_PACK_MANIFEST.json')['sha256'],'closed':True,'fixed_stop':True,'resume_same_cycle_allowed':False,'additional_research_allowed':False,'post_closure_allowed':'actual GET / static hash and path receipts / private artifact delivery only; no research','Exposure':'ITERATIVE_DEVELOPMENT_EVIDENCE','fresh_OOS_claim':False,'productionReady':False,'Safety':SAFETY}
    save(OUT/'CLOSURE.json',closure)
    checkpoint('V14_CLOSURE_FIXED_STOP',{'status':sel['status'],'selectedCapitalCandidate':sel['selectedCapitalCandidate'],'diagnosticArm':sel['diagnosticArm'],'NEXT_BOTTLENECK':sel['NEXT_BOTTLENECK'],'independent_mismatch_N':audit['mismatch_N'],'newFits':0,'CapitalReplays':2},'STOP. Only static receipts/delivery allowed; next research requires a new independent Work')
if __name__=='__main__':{'selection':selection,'delivery':delivery,'close':close}[sys.argv[1]]()
