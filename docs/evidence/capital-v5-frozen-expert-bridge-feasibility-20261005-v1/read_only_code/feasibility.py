"""Saved-prefix census only. Does not call V5 state machine, gate, allocator or market replay."""
import collections,itertools,json,pathlib
from fractions import Fraction
from adapter import ROOT,BASE,OUT,PRIVATE,HEADS,read,rows,save,sha,digest,now,support
def main():
 assert (OUT/'F5_CHECKPOINT.json').exists() and not (OUT/'F6_CHECKPOINT.json').exists()
 packet={r['entry_id']:r for r in rows(PRIVATE/'FROZEN_EXPERT_PACKET.jsonl.gz')};data={r['entry_id']:r for r in rows(PRIVATE/'V5_SCORE_OUTCOME_ROWS.jsonl.gz')};masks=read(PRIVATE/'COHORT_MASKS.json');rp=set(masks['C3']);d={r['entry_id']:r for r in rows(ROOT/'r1_work/runs/OFF_PRIMARY/DECISIONS.jsonl.gz')};snap={r['entry_id']:r for r in rows(PRIVATE/'SAVED_OUTCOME_FREE_SNAPSHOTS.jsonl.gz')};proposals=rows(ROOT/'r1_work/runs/OFF_PRIMARY/NATIVE_PROPOSALS.jsonl.gz')
 assert rp==set(read(ROOT/'r1_work/metrics/evaluation_only/RANK_PASS_IDS.json'))
 members=collections.defaultdict(list);asof_rows=[];batchledger=[];regret=[]
 for b in proposals:
  assert len(b['snapshot']['positions'])==b['existing_open_N']
  assigned={r['entry_id']:r for r in b['assigned']};prior_success=[];candidateIDs=[c['entry_id'] for c in b['candidates'] if c['entry_id'] in rp]
  if len(candidateIDs)>1:
   batchledger.append({'session':b['session'],'minute':b['minute'],'candidate_ids':candidateIDs,'native_picked_ids':b['picked_ids'],'assigned_quantities':{k:assigned[k]['quantity'] for k in b['picked_ids']},'existing_position_ids':sorted(b['snapshot']['positions']),'same_timestamp':True,'outcome_used_for_grouping':False,'pP_rank':sorted(candidateIDs,key=lambda k:(-packet[k]['heads']['pP']['raw_score'],packet[k]['frozen_entry_time'],packet[k]['symbol'],k)),'new_selection_actions':0})
  for c in b['candidates']:
   k=c['entry_id'];p=packet[k];a=assigned.get(k);q=a['quantity'] if a else None;sn=snap[k];existing=b['existing_open_N'];prefixN=existing+len(prior_success)
   assert p['frozen_entry_time']==c['entry_timestamp'] and p['entry_minute']==b['minute']
   lot=Fraction(c['raw_reference'])*100*Fraction(10005,10000);cash=Fraction(b['snapshot']['cash']);knownheld=all(i in packet for i in b['snapshot']['positions'])
   tags=[]
   if k in rp and len(candidateIDs)>1:tags.append('CH1_PRE_BUY_SAME_BATCH')
   if a and q>=100:tags.append('CH2_PRE_BUY_DEFENSE');assert sn['planned_slot']==prefixN+1 and d[k]['funded_slot']==prefixN+1
   if d[k]['reason']=='SLOT_RESERVE_REJECT' and prefixN<3:tags.append('CH3_VACANT_SLOT_RESERVE')
   if d[k]['reason']=='MAX_POSITION_CAP' and existing==3:tags.append('CH4_FULL_MAX3')
   if d[k]['reason']=='CASH_OR_LOT_CONSTRAINED':tags.append('CH5_CASH_OR_LOT')
   if k not in rp:tags.append('CH6_RANK_REJECT_OTHER')
   row={'entry_id':k,'session':b['session'],'block':p['native_block'],'minute':b['minute'],'raw_reason':d[k]['reason'],'slot_gate_reason':d[k].get('slot_gate_reason'),'snapshot_existing_N':existing,'prior_successful_assigned_N':len(prior_success),'existing_plus_prior_successful':prefixN,'actual_planned_slot':sn['planned_slot'],'slot_admission_index':d[k].get('slot_admission_index'),'native_quantity':q,'tags':tags,'score_known':all(p['heads'][h]['available'] for h in HEADS),'comparison_known':all(i in packet for i in candidateIDs) and knownheld,'current_cash_lot_known':True,'hypothetical100_lot_debit_exact':str(lot),'snapshot_cash_ge100lot':cash>=lot,'after_all_native_picks_cash_ge100lot':cash-sum((Fraction(z['debit']) for z in b['assigned'] if z['quantity']>=100),Fraction(0))>=lot,'other_native_picked_empty':not b['picked_ids'],'new_Reserve_actual_frozen_allocation_quantity':'NOT_EVALUATED','selection_actions':0}
   asof_rows.append(row)
   for t in tags:members[t].append(row)
   if 'CH4_FULL_MAX3' in tags:
    for held in sorted(b['snapshot']['positions']):
     hp=packet.get(held);assert hp is not None
     signs={h:(p['heads'][h]['raw_score']>hp['heads'][h]['raw_score'])-(p['heads'][h]['raw_score']<hp['heads'][h]['raw_score']) for h in HEADS}
     regret.append({'session':b['session'],'arrival_entry_id':k,'arrival_entry_time':p['frozen_entry_time'],'held_entry_id':held,'held_original_entry_time':hp['frozen_entry_time'],'entry_score_signs':signs,'held_original_entry_score_not_remaining_return_prediction':True,'horizon':'different Entry-time origins; no residual-value retargeting','new_SELL_BUY_actions':0})
   if a and q>=100:prior_success.append(k)
 # Precheck-only rows absent from proposal candidates stay visible, never inferred eligible.
 seen={r['entry_id'] for r in asof_rows}
 for k in set(packet)-seen:
  assert k not in rp
  members['CH6_RANK_REJECT_OTHER'].append({'entry_id':k,'session':packet[k]['session'],'block':packet[k]['native_block'],'raw_reason':d[k]['reason'],'score_known':True,'comparison_known':False,'current_cash_lot_known':False,'snapshot_existing_N':None,'other_native_picked_empty':None,'selection_actions':0})
 census={}
 names=['CH1_PRE_BUY_SAME_BATCH','CH2_PRE_BUY_DEFENSE','CH3_VACANT_SLOT_RESERVE','CH4_FULL_MAX3','CH5_CASH_OR_LOT','CH6_RANK_REJECT_OTHER']
 for name in names:
  rr=members[name];keys=[r['entry_id'] for r in rr];assert len(keys)==len(set(keys))
  selectable=sum(r['score_known'] and r['comparison_known'] and r['current_cash_lot_known'] for r in rr) if name in names[:3] else 0
  raw=collections.Counter(r['raw_reason'] for r in rr);census[name]={'population_N':len(rr),'asof_score_known_N':sum(r['score_known'] for r in rr),'comparison_known_N':sum(r['score_known'] and r['comparison_known'] for r in rr),'required_current_constraints_known_N':sum(r['score_known'] and r['comparison_known'] and r['current_cash_lot_known'] for r in rr),'structural_selection_discretion_N':selectable,'distinct_sessions':len({r['session'] for r in rr}),'blocks':len({r['block'] for r in rr}),'mask_hash':digest(keys),'raw_reason_counts':dict(raw),'unknown_reasons':{'NO_SAVED_PRECHECK_SNAPSHOT':sum(not r['current_cash_lot_known'] for r in rr)},'U5_N_evaluation_only':sum(data[k]['U5']==1 for k in keys),'U10_N_evaluation_only':sum(data[k]['U10']==1 for k in keys),'Medium_N_evaluation_only':sum(data[k]['Medium']==1 for k in keys),'Loser_N_evaluation_only':sum(data[k]['Loser']==1 for k in keys),'outcome_unknown_N':sum(data[k]['realized'] is None or data[k]['potential'] is None for k in keys),'actual_additional_recovery':'NOT_EVALUATED','actions_emitted':0}
  if name=='CH3_VACANT_SLOT_RESERVE':
   census[name].update({'native_picked_empty_N':sum(r['other_native_picked_empty'] for r in rr),'native_picked_nonempty_N':sum(not r['other_native_picked_empty'] for r in rr),'cash_lot_known_N':len(rr),'snapshot_cash_ge100lot_N':sum(r['snapshot_cash_ge100lot'] for r in rr),'after_all_native_picks_cash_ge100lot_N':sum(r['after_all_native_picks_cash_ge100lot'] for r in rr),'fundability_by_frozen_allocation_N':None,'fundability_status':'UNMEASURABLE_WITHOUT_SEPARATE_COUNTERFACTUAL_ALLOCATION_EVALUATION','independent_of_defense_token':True,'raw_reserve_reasons':dict(collections.Counter(r['slot_gate_reason'] for r in rr))})
  if name=='CH2_PRE_BUY_DEFENSE':census[name]['actual_planned_slots']=dict(collections.Counter(r['actual_planned_slot'] for r in rr))
  if name=='CH4_FULL_MAX3':census[name]['support_reason']='CONTRACT_BLOCKED_FOR_REPLACEMENT_EXIT_FROZEN'
 maxreason=[r for r in asof_rows if r['raw_reason']=='MAX_POSITION_CAP'];pending=[r for r in maxreason if r['snapshot_existing_N']<3]
 miss={}
 for u in ['U5','U10']:
  ww=[k for k in rp if data[k][u]==1];cc=collections.Counter(d[k]['reason'] for k in ww);expected={'FUNDED':50 if u=='U5' else 26,'SLOT_RESERVE_REJECT':30 if u=='U5' else 10,'MAX_POSITION_CAP':28 if u=='U5' else 9,'CASH_OR_LOT_CONSTRAINED':5 if u=='U5' else 2};assert dict(cc)==expected
  miss[u]={'legacy_rankpass_total_N':len(ww),'raw_reason_counts':dict(cc),'funded_N':cc['FUNDED'],'missed_N':len(ww)-cc['FUNDED'],'denominator':'same legacy rank-pass494, not ALL170/67 or Oracle','actual_fullMAX3_N':sum(data[r['entry_id']][u]==1 for r in members['CH4_FULL_MAX3']),'same_batch_pending_MAX3_N':sum(data[r['entry_id']][u]==1 for r in pending)}
 save('CHANNEL_CENSUS.json',{'channels':census,'channel_tags_overlap':'CH1 may overlap CH2/CH3; not additive recovery counts','rankpass_N':494,'rankpass_missed_N':344,'terminal_MAX3_N':len(maxreason),'actual_full_before_batch_N':len(members['CH4_FULL_MAX3']),'pending_same_batch_MAX3_N':len(pending),'MAX3_terminal_not_all_existing_full':True,'no_provider_or_runner_called':True,'held_entry_scores_not_current_remaining_return':True,'actual_additional_funded_N':None,'Capital':'NOT_EVALUATED'})
 save('MISSED_ALL_RANKPASS_ANATOMY.json',{'rankpass_N':494,'terminal_reason_counts':dict(collections.Counter(d[k]['reason'] for k in rp)),'all_missed_N':344,'winner_conservation':miss,'unknown_realized_rankpass_N':sum(data[k]['realized'] is None for k in rp),'cohort_fixed_before_winner_join':True})
 save('CHANNEL_ELIGIBILITY_ROWS.jsonl.gz',asof_rows,True);save('SAME_BATCH_CONFLICTS.jsonl.gz',batchledger,True);save('ENTRY_SCORE_PRIORITY_REGRET.jsonl.gz',regret,True)
 save('FIRST_DIVERGENCE_CHECKER_SPEC.json',{'status':'SPECIFICATION_ONLY_NOT_EXECUTED','input':['frozen label-free packet','saved event-prefix snapshots','separately approved deterministic frozen policy','same initial native and extended state','all current decision inputs'], 'algorithm':['synthetic branch coverage and contract contradiction tests','support and independent sessions from completed training or genuine past OOF; not current outcome selection','iterate saved prefix; reconstruct native and extended state; compare full action identity and relevant pending/order/cash/counter state','no differing action across all events plus identical inputs/state implies identical path by induction','extended state or input reconstruction unavailable -> UNMEASURABLE','first nonzero divergence -> support only; subsequent counterfactual state and economics require separately authorized replay'], 'NO_REPLAY_REQUIRED_only_if':'fully reconstructed deterministic policy all actions equal on saved prefix; or synthetic hypothetical zero-support diagnostic, not real policy certification','current_policy_selected':None,'new_runtime_adapter_implemented':False,'current_first_divergence_result':'NOT_EVALUATED_NO_NEW_POLICY','zero_support_no_condition_relaxation':True,'initial_warmup':'NO_PAST_OOF_SUPPORT -> frozen abstain, not refit or cohort dropping'})
 save('F6_CHECKPOINT.json',{'exact_jst':now(),'complete':True,'stage':'F6','code_hash':sha(pathlib.Path(__file__)),'input_packet_hash':sha(PRIVATE/'FROZEN_EXPERT_PACKET.jsonl.gz'),'primaryDiagnosticBatch':1,'newFits':0,'CapitalReplays':0,'ControlReplays':0,'result':'saved legal opportunities separated from full-held and unmeasured funding','next':'separate independent diagnostics and18 synthetic cases'})
 print(json.dumps({'channels':{k:v['population_N'] for k,v in census.items()},'existing_fullMAX3_N':len(members['CH4_FULL_MAX3']),'pending_MAX3_N':len(pending),'stage':'F6','exact_jst':now()}))
if __name__=='__main__':main()
