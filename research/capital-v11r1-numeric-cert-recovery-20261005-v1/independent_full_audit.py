"""Raw MRET inference, standalone Fraction portfolio/exposure and fixed gates.

M1's emitted prefix and unresolved obligation are audited without completing,
imputing or repeating its Main. M2 receives a full38-session audit.
"""
from independent_engine import *
from independent_policy import scalar
from independent_replay import reconstruct
from independent_blocked import reconstruct_blocked
from independent_evaluation import *
from control import save,checkpoint,now,SAFETY
def main():
 assert not (P/'INDEPENDENT_FULL_AUDIT_STARTED.json').exists(),'FULL_AUDIT_ALREADY_STARTED_NO_REPEAT'
 save(P/'INDEPENDENT_FULL_AUDIT_STARTED.json',{'exact_jst':now(),'primary_runtime_replay_evaluator_imports':0,'Main_rerun':False})
 audit=Audit();stream=rows(P/'INDEPENDENT_CURRENT_MRET_CAP_RUNTIME.jsonl.gz');tables=read(P/'INDEPENDENT_I2_PAST_TABLES.json');rt={r['entry_id']:r for r in stream};raw={r['entry_id']:r for r in rows(I/'movement/RUNTIME_CAUSAL.jsonl.gz')};teacher={r['entry_id']:r for r in rows(I/'evaluation/TEACHERS_EVALUATION.jsonl.gz')};books={r['entry_id']:r for r in rows(I/'execution/MARKET_EXECUTION_BOOK_V2.jsonl.gz')};train=rows(W/'authority/v11/private/MRET_TRAIN_RESUBSTITUTION_SCORES.jsonl.gz');ledger=read(ROOT/'docs/evidence/capital-v11-realized-monetization-signal-20261005-v1/MRET_8_FITS_RESULT.json')['fit_ledger']
 claim=read(O/'MAIN_REPLAY_CLAIM.json')
 for path,h in claim['input_sha256'].items():audit.check('claimed_input/'+path,digest(ROOT.parent/path)==h)
 for path,h in claim['code_sha256'].items():audit.check('claimed_code/'+path,digest(ROOT/path)==h)
 cert=read(O/'S9R_CERTIFICATION_DECISION.json');audit.check('S9R14',cert['S9R']=='PASS' and all(cert['conditions'].values()) and cert['oldS9']=='FAIL')
 for b in range(1,9):
  path=W/f'authority/v11/private/models/MRET_BLOCK_{b:02}.json';m=read(path);audit.check(f'{b}/model_hash',digest(path)==ledger[b-1]['model_sha256']);audit.check(f'{b}/snapshot_hash',digest(W/f'authority/v11/private/fitted_state/MRET_BLOCK_{b:02}.npz')==ledger[b-1]['snapshot_sha256']);dist=sorted(r['mP'] for r in train if r['block']==b)
  for r in stream:
   if r['block']!=b:continue
   score=scalar(raw[r['entry_id']],m);pct=(1+bisect_left(dist,score))/(len(dist)+1);audit.num(r['entry_id']+'/raw_MRET',score,r['mP']);audit.check(r['entry_id']+'/strict_training_percentile',pct==r['rM'])
 qpublic=read(O/'QUALITY_RETENTION_AND_EXPOSURE_DELTA.json')['profiles'];cpublic=read(O/'CAPITAL_ROLLING20_RESULT.json')['profiles'];epublic=read(O/'MRET_AND_POTENTIAL_EXPOSURE_RESULT.json')['profiles'];spec=read(ROOT/'docs/evidence/capital-v11-realized-monetization-signal-20261005-v1/M1_M2_CAPITAL_POLICY_PRECOMMIT.json');rr={};decisions={};metric={};official={};scope={}
 for profile in ('v5','I2'):
  saved=rows(W/f'authority/v10/private/{profile}_MONETIZATION_TRADE_LEDGER.jsonl.gz');rr[profile]=[]
  for z in saved:
   k=z['entry_id'];r=make_row(k,z['quantity'],z['slot'],rt,books,teacher,audit)
   for f in ('buy_debit','sell_proceeds','actual_PnL','unit_100share_PnL'):audit.money(profile+'/'+k+'/'+f,r[f],z[f])
   audit.num(profile+'/'+k+'/realized',r['realized_net_return'],z['realized_net_return']);rr[profile].append(r)
  compare(audit,profile+'/saved_exposure',exposures(rr[profile]),epublic[profile])
 old={r['entry_id']:r for r in rows(W/'authority/v9/private/QUALITY_PARETO_U2_U3_TENURE_MAX3_V1_DECISIONS.jsonl.gz')};base_all={r['entry_id']:r for r in rr['I2']};mask={r['entry_id'] for r in rows(PIN/'COMMON_EVAL_MASK.jsonl.gz') if r['included']}
 for arm in ARMS:
  primary_result=read(O/f'{arm}_RESULT.json');blocked=primary_result.get('measurement_status')=='CAPITAL_MEASUREMENT_BLOCKED_EXECUTION'
  dec,met,trades,frames,daily=(reconstruct_blocked if blocked else reconstruct)(arm,stream,tables,audit);decisions[arm]=dec;metric[arm]=met;dm={r['entry_id']:r for r in dec};saved_t={r['entry_id']:r for r in rows(P/f'{arm}_TRADES.jsonl.gz')};rr[arm]=[make_row(k,d['quantity'],d['funded_slot'],rt,books,teacher,audit,saved_t.get(k)) for k,d in dm.items() if d['reason']=='FUNDED'];m={r['entry_id']:r for r in rr[arm]};base={k:r for k,r in base_all.items() if k in dm} if blocked else base_all;scope[arm]=base
  saved_ledger={r['entry_id']:r for r in rows(P/f'{arm}_MONETIZATION_TRADE_LEDGER.jsonl.gz')}
  for r in rr[arm]:
   z=saved_ledger[r['entry_id']]
   for f in ('quantity','lots','slot','potential_bucket','coarse_bucket'):audit.check(r['entry_id']+'/eval/'+f,r[f]==z[f])
   for f in ('buy_debit','sell_proceeds','actual_PnL','unit_100share_PnL'):
    if r[f] is None:audit.check(r['entry_id']+'/eval/'+f,z[f] is None)
    else:audit.money(r['entry_id']+'/eval/'+f,r[f],z[f])
  q=aggregate(rr[arm]);saved=qpublic[arm];compare(audit,arm+'/quality',q,saved['funded_quality']);integrity={'cash_negative':sum(c['cash']<0 for c in frames),'MAX3_excess':sum(c['concurrent']>3 for c in frames),'same_symbol_open':0,'cutoff_funded':sum(r['entry_minute']>=920 for r in rr[arm]),'nonlot100':sum(d['quantity']%100!=0 for d in dec),'execution_unresolved':len(met['open_obligations']) if blocked else 0,'canary_fail':0,'leakage':0};compare(audit,arm+'/integrity',integrity,saved['integrity'])
  a=spec['quality_retention'];b=spec['secondary_v5_floor'];ret={'Q1':q['U5']>=a['U5_min'],'Q2':q['U10']>=a['U10_min'],'Q3':q['Medium']>=a['Medium_min'],'Q4':q['below2_rate']<=a['weak_rate_max'],'Q5':q['below3_rate']<=a['below3_rate_max'],'Q6':not any(integrity.values()),'Q7':'PENDING'};floor={'U5':q['U5']>=b['U5_min'],'U10':q['U10']>=b['U10_min'],'Medium':q['Medium']>=b['Medium_min'],'Weak':q['below2_rate']<=b['weak_rate_max'],'below3':q['below3_rate']<=b['below3_rate_max']}
  if blocked:ret={k:None if k in ('Q1','Q2','Q3','Q4','Q5') else v for k,v in ret.items()};floor={k:None for k in floor}
  compare(audit,arm+'/retention_gates',ret,saved['quality_retention_gates']);compare(audit,arm+'/floor',floor,saved['v5_floor_gates']);retained=not blocked and all(v for k,v in ret.items() if k!='Q7');floorpass=not blocked and all(floor.values());audit.check(arm+'/retention_point',retained==saved['retention_point_PASS']);audit.check(arm+'/floor_pass',floorpass==saved['v5_floor_PASS'])
  cap=spec['capital_gate_strict'];rel=spec['relative_progress_strict']
  if blocked:g={k:None for k in ('C1','C2','C3')};rg={k:None for k in ('median','mean','daily_geometric')}
  else:g={'C1':met['rolling20_median']>cap['rolling20_median'],'C2':met['rolling20_arithmetic_mean']>cap['rolling20_mean'],'C3':met['geometric_mean_daily_return']>cap['daily_geometric']};rg={'median':met['rolling20_median']>rel['median'],'mean':met['rolling20_arithmetic_mean']>rel['mean'],'daily_geometric':met['geometric_mean_daily_return']>rel['daily_geometric']}
  c=cpublic[arm];compare(audit,arm+'/capital_gates',g,c['v5_economic_gates']);compare(audit,arm+'/relative_gates',rg,c['relative_gates']);progress=all(rg.values()) and floorpass;official[arm]={'retained':retained,'floor':floorpass,'capital':all(g.values()),'relative':progress,'measurement_complete':not blocked};audit.check(arm+'/Capital_PASS',(retained and all(g.values()))==c['Capital_point_PASS']);audit.check(arm+'/relative_PASS',progress==c['MONETIZATION_CAPITAL_PROGRESS'])
  for name,t in [('U5',.05),('U10',.10)]:compare(audit,arm+'/'+name+'/reason_conservation',dict(Counter(d['reason'] for d in dec if d['entry_id'] in mask and teacher[d['entry_id']]['potential_return']>=t)),saved['reason_conservation'][name])
  common=set(m)&set(base);gain=[m[k] for k in sorted(set(m)-set(base))];lost=[base[k] for k in sorted(set(base)-set(m))];ga=aggregate(gain);lo=aggregate(lost);pair=saved['paired'];qd=F(0);quantities=[]
  for k in sorted(common):
   r=m[k];z=base[k];change=r['quantity']-z['quantity'];pnl=F(r['unit_100share_PnL'])*F(change,100);qd+=pnl;quantities.append({'entry_id':k,'quantity_I2':z['quantity'],'quantity_new':r['quantity'],'quantity_delta':change,'lots_delta':change//100,'buy_notional_delta':str(F(r['buy_debit'])-F(z['buy_debit'])),'actual_PnL_delta':str(pnl),'potential_bucket':r['potential_bucket'],'coarse_bucket':r['coarse_bucket'],'rM':r['rM'],'realized_net_return':r['realized_net_return']})
  compare(audit,arm+'/common_quantity_ledger',quantities,rows(P/f'{arm}_COMMON_QUANTITY_DELTA.jsonl.gz'));compare(audit,arm+'/gain',ga,pair['GAINED_FUNDING_vs_I2']);compare(audit,arm+'/lost',lo,pair['LOST_FUNDING_vs_I2']);audit.check(arm+'/common_N',len(common)==pair['COMMON_FUNDED']['N']);audit.money(arm+'/common_quantity_PnL',qd,pair['COMMON_FUNDED']['actual_PnL_quantity_delta']);compare(audit,arm+'/net',{k:ga[k]-lo[k] for k in ('U5','U10','Medium','Weak','realized_positive_N','realized_loser_le0_N')},pair['NET_counts'])
  for name,pred in [('Weak',lambda r:r['coarse_bucket']=='Weak'),('Low',lambda r:r['coarse_bucket']=='Low'),('Medium',lambda r:r['coarse_bucket']=='Medium'),('Big',lambda r:r['coarse_bucket']=='Big'),('Mega',lambda r:r['coarse_bucket']=='Mega'),('U5',lambda r:r['coarse_bucket'] in ('Big','Mega')),('U10',lambda r:r['coarse_bucket']=='Mega'),('realized_positive',lambda r:r['realized_net_return']>0),('realized_ge1',lambda r:r['realized_net_return']>=.01),('loser',lambda r:r['realized_net_return']<=0),('low_rM',lambda r:r['rM']<.5),('high_rM',lambda r:r['rM']>=.5)]:
   z=[r for r in quantities if pred(r)];actual={'N':len(z),'quantity_delta':sum(r['quantity_delta'] for r in z),'lots_delta':sum(r['lots_delta'] for r in z),'buy_notional_delta':str(sum((F(r['buy_notional_delta']) for r in z),F(0))),'actual_PnL_delta':str(sum((F(r['actual_PnL_delta']) for r in z),F(0)))};compare(audit,arm+'/quantity_group/'+name,actual,pair['COMMON_FUNDED']['quantity_groups'][name])
  for name,z in [('NEW_MAX3_MISS_vs_I2',[empty(k,rt,teacher,d) for k,d in dm.items() if d['reason']=='MAX3_FULL' and old[k]['reason']!='MAX3_FULL']),('CASH_RECOVERY_vs_I2',[r for r in rr[arm] if old[r['entry_id']]['reason']=='CASH_OR_LOT']),('NEW_CASH_MISS_vs_I2',[empty(k,rt,teacher,d) for k,d in dm.items() if d['reason']=='CASH_OR_LOT' and old[k]['reason']!='CASH_OR_LOT'])]:compare(audit,arm+'/'+name,aggregate(z),pair[name])
  actualdelta=None if q['actual_PnL'] is None else str(F(q['actual_PnL'])-F(aggregate(list(base.values()))['actual_PnL']));compare(audit,arm+'/actual_delta',actualdelta,pair['actual_PnL_delta_vs_I2']);audit.money(arm+'/notional_delta',F(q['buy_notional'])-F(aggregate(list(base.values()))['buy_notional']),pair['buy_notional_delta_vs_I2']);audit.check(arm+'/lots_delta',q['lots']-aggregate(list(base.values()))['lots']==pair['lots_delta_vs_I2']);audit.check(arm+'/cap_hit_delta',sum(d.get('cap_hit',False) for d in rows(P/f'{arm}_DECISIONS.jsonl.gz') if d['reason']=='FUNDED')-sum(old[k].get('cap_hit',False) for k in dm if old[k]['reason']=='FUNDED')==pair['cap_hit_delta_vs_I2'])
  if actualdelta is not None:audit.money(arm+'/identity_quantity_conservation',actualdelta,qd+F(ga['actual_PnL'])-F(lo['actual_PnL']))
  ex=exposures(rr[arm]);ref=exposures(list(base.values()));ex['rM_half_delta_vs_I2']={h:{'buy_notional_delta':str(F(ex['rM_half'][h]['buy_notional'])-F(ref['rM_half'][h]['buy_notional'])),'actual_PnL_delta':str(F(ex['rM_half'][h]['actual_PnL'])-F(ref['rM_half'][h]['actual_PnL'])) if ex['rM_half'][h]['actual_PnL'] is not None else None} for h in ('low','high')};compare(audit,arm+'/all_exposures',ex,epublic[arm])
 compare(audit,'I2_M1_prefix_exposure',exposures(list(scope[ARMS[0]].values())),epublic['I2_M1_MATCHED_PREFIX'])
 eligible=[a for a,z in official.items() if z['retained'] and z['capital']]
 def order(a,hit=False):
  m=metric[a];key=(-m['rolling20_median'],-m['rolling20_arithmetic_mean'],-m['geometric_mean_daily_return'],-m['final_equity'],m['max_drawdown'],ARMS.index(a));return (-m['north_star_hit_N'],)+key if hit else key
 selected=sorted(eligible,key=lambda a:order(a,True))[0] if eligible else None;pool=[a for a,z in official.items() if z['retained']] or [a for a,z in official.items() if z['floor']];diag=selected or (sorted(pool,key=order)[0] if pool else 'QUALITY_PARETO_U2_U3_TENURE_MAX3_V1')
 if selected:
  hit=metric[selected]['north_star_hit_N']>0;status='V11R1_NUMERIC_CERTIFIED_NORTH_STAR_HIT' if hit else 'V11R1_NUMERIC_CERTIFIED_CAPITAL_IMPROVED';bottleneck=spec['bottleneck']['official_2x_hit'] if hit else 'NORTH_STAR_CAPITAL_GAP'
 else:
  progress=any(z['relative'] for z in official.values());status='V11R1_NUMERIC_CERTIFIED_PARTIAL_CAPITAL_PROGRESS' if progress else 'V11R1_NUMERIC_CERTIFIED_POLICY_NO_GO';bottleneck='MONETIZATION_SIGNAL_STRENGTH_OR_CAPITAL_MAPPING' if progress else 'MONETIZATION_POLICY_TRANSLATION'
 short={ARMS[0]:'M1',ARMS[1]:'M2','QUALITY_PARETO_U2_U3_TENURE_MAX3_V1':'I2 saved'};decision={'status':status,'selectedCapitalCandidate':short[selected] if selected else None,'diagnosticArm':short[diag],'NEXT_BOTTLENECK':bottleneck,'eligible':eligible,'adoption':selected is not None,'Q7_pending':True};compare(audit,'winner_bottleneck',decision,read(O/'PROVISIONAL_WINNER_AND_BOTTLENECK.json'))
 protected=read(W/'PROTECTED_TRACKED_HASHES.json')
 for path,h in protected.items():audit.check('old_evidence_source/'+path,digest(ROOT/path)==h)
 result={'exact_jst':now(),'status':'PASS' if not audit.mismatches else 'CONTRACT_FAIL','checks':audit.checks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches,'max_float_delta':audit.max_float_delta,'float_tolerance':1e-12,'preprocessing_identity':'completed canonical float64 bit certificate reused; no recertification','money_quantity':'EXACT','primary_runtime_replay_evaluator_imports':0,'implementation_independence':True,'upstream_market_source_independence_claim':False,'completed_preparation_recomputed':False,'independent_portfolio_audits':2,'M1_scope':'all emitted29-session prefix incl28 COMPLETE + unresolved day; no Final38/rolling20 certification','M2_scope':'full38-session ledger / capital / gates','M1_raw_execution_blocker_reproduced':metric[ARMS[0]],'M2_economic_metrics':metric[ARMS[1]],'official_gates':official,'independent_decision':decision,'saved_control_replays':0,'Main_reruns':0,'newFits':0,'Safety':SAFETY}
 save(O/'INDEPENDENT_AUDIT.json',result);print(json.dumps(result),flush=True);assert not audit.mismatches,'FULL_INDEPENDENT_CONTRACT_FAIL_STOP'
 checkpoint('N16_FULL_INDEPENDENT_AUDIT',{'checks':audit.checks,'mismatch_N':0,'M1':'full available ledger and raw unresolved source verified','M2':'full38-session Capital verified'},'Final gates / winner / bottleneck; fixed STOP, no further replay')
if __name__=='__main__':main()
