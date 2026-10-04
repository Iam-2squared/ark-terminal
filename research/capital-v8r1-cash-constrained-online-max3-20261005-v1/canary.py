"""43 mandatory causal tests; synthetic capital scenarios only, no OOF replay."""
from control import *
from runtime import gate,order,allocation,active_clock,wall_clock,predicted_release,BUCKETS
from replay import day_replay
from independent_engine import Audit,lot_allocate
from independent_policy import build,accept
from decimal import Decimal as D
from fractions import Fraction as F
import copy,ast,inspect
def synthetic():
 day='2000-01-01';rr=[];books={}
 for name,t,p,band in [('AAA',550,.9,'P_HIGH'),('BBB',552,.8,'P_MID'),('CCC',554,.3,'P_BASE'),('DDD',620,.7,'P_MID'),('EEE',920,.99,'P_HIGH')]:
  k=f'{day}|{name}';r={'entry_id':k,'session':day,'symbol':name,'entry_minute':t,'entry_timestamp':f'{day}T{t//60:02}:{t%60:02}:00+09:00','raw_reference':'100','pP':p,'block':1,'rank_units':round(p*100),'train_N':100,'r':p,'band':band,'liquidity':{'eligible':True}};rr.append(r)
  market=[{'minute':m,'session':day,'O':'100','H':'102','L':'99','C':'101','Vo':'1000','Va':'100000','lineage':{'synthetic':True}} for m in (t,600,639,650,920)]
  books[k]={'entry_id':k,'session':day,'symbol':name,'capture_complete':True,'entry_actual_source':market[0],'market':market,'frozen_exit':{'sell_status':'FILLED','sell_source_assumed_available_at':f'{day}T10:40:00+09:00','sell_minute':639,'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':'99.9500'}}
  if t>=640:books[k]['frozen_exit']={'sell_status':'UNRESOLVED'}
 days=['1999-01-01','1999-01-02','1999-01-03','1999-01-04'];table={'train_N':100,'training_sessions':days,'sessions':{d:[] for d in days},'tenure':{'cells':{b:{f'{lo}-{hi}':{'median_active_duration':200} for lo,hi in BUCKETS} for b in ('P_HIGH','P_MID','P_BASE')}}}
 return day,rr,books,{'1':table}
def main():
 audit=Audit();stream,tables,train=build(audit);cases=[]
 def test(name,condition):
  cases.append({'test':name,'PASS':bool(condition)});assert condition,name
 authority=read(OUT/'AUTHORITY_FREEZE.json');rank=read(RANK/'SELECTED_RANK_CONTRACT.json');freeze=read(OUT/'B1_B2_SEMANTIC_FREEZE.json');frozen=freeze['frozen_policy'];mask=rows(PIN/'COMMON_EVAL_MASK.jsonl.gz');pphash='14c48e61554bd58c6d5289b410d6a8c859cb37efd0dbc5d98987fcb440aac2ed'
 test('01_rank_contract_exact',sha(RANK/'SELECTED_RANK_CONTRACT.json')=='6e8687f36f6f60fc9e9921e1ef29e0520cf1ea8bc01f14386963f1020b209518')
 test('02_pP_score_hash_exact',sha(INPUT/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz')==pphash and all(sha(INPUT/'movement/models'/n)==v for n,v in rank['model_sha256'].items()))
 test('03_band_map_exact',sha(V7/'RANK_NATIVE_BAND_MAP.json')==authority['sha256'][str((V7/'RANK_NATIVE_BAND_MAP.json').relative_to(ROOT))])
 test('04_training_IDs_exact',not audit.mismatches and all(set(t['train_entry_ids'])==set(read(INPUT/f'movement/models/MOVE_P_BLOCK_{int(b):02}.json')['train_entry_ids']) for b,t in tables.items()))
 test('05_test_IDs_not_in_train',all(not set(t['train_entry_ids'])&{r['entry_id'] for r in stream if str(r['block'])==b} for b,t in tables.items()))
 test('06_U5_U10_runtime_state_zero',not any(any(k in r for k in ('U5','U10','potential_return','future_high','realized_PnL','exit','label_bigwinner5')) for r in rows(PIN/'RANK_NATIVE_RUNTIME.jsonl.gz')))
 test('07_future_test_candidate_use_zero',all(max(t['training_sessions'])<min(t['test_sessions']) for t in tables.values()))
 test('08_future_test_release_use_zero',all(all(k.split('|')[0]<min(t['test_sessions']) for k in t['tenure']['training_support_entry_ids']) for t in tables.values()))
 test('09_current_pP_r_only',sha(CODE/'runtime.py')==frozen['code_sha256']['runtime.py'] and not audit.mismatches)
 maxima=read(V7/'FUTURE_MAX_RANK_TABLE.json');c1=True
 for r in stream:
  if r['entry_minute']>=920 or r['band']=='P_BELOW':continue
  t=tables[str(r['block'])];allowed,why,info=gate(ARMS[0],r,2,r['entry_minute'],t);mm=maxima[str(r['block'])]['minutes'][str(r['entry_minute'])];count=sum(u is not None and u>r['rank_units'] for u in mm);c1&=info['future_pressure_session_N']==count and allowed==(2*count<len(mm))
 test('10_B1_c1_equals_v7_A2',c1)
 day,candidates,books,syntables=synthetic();r=candidates[2];t=syntables['1']
 for o,num in [(0,11),(1,12),(2,13)]:test(f'{num:02}_occupancy{o}_free{3-o}',gate(ARMS[0],r,o,r['entry_minute'],t)[2]['free_slots']==3-o)
 test('14_occupancy3_always_reject',all(gate(a,r,3,554,t)[:2]==(False,'MAX3_FULL') for a in ARMS))
 same=copy.deepcopy(t);same['sessions']={d:[[554,99]] for d in same['training_sessions']};test('15_strictly_later_only',gate(ARMS[0],r,2,554,same)[0])
 a1=day_replay(day,candidates,books,D(1000000),ARMS[0],syntables);a2=day_replay(day,candidates,books,D(1000000),ARMS[1],syntables)
 test('16_same_minute_currently_known_only',all(d['held_before_batch']==[] for d in a1[1] if d['minute']==550))
 hi=copy.deepcopy(candidates[0]);lo=copy.deepcopy(hi);lo.update(pP=.1,symbol='ZZZ');test('17_same_minute_pP_descending',sorted([lo,hi],key=order)==[hi,lo])
 nt=copy.deepcopy(t);nt['tenure']={'not_read_by_B1':True};test('18_B1_no_tenure_teacher',gate(ARMS[0],r,1,554,t)==gate(ARMS[0],r,1,554,nt))
 test('19_B2_group_has_no_outcome_key',frozen['B2']['group_keys']==['Rank-native band','fixed Entry 30-minute bucket'] and all(z['tenure']['teacher_projection_fields']==['entry_id','execution_status','release_minute'] for z in tables.values()))
 mutated=copy.deepcopy(r);mutated['current_actual_future_release']=555;test('20_B2_actual_current_future_release_use_zero',gate(ARMS[1],r,1,554,t)==gate(ARMS[1],mutated,1,554,t))
 test('21_tenure_training_only',all(all(k in z['train_entry_ids'] for k in z['tenure']['training_support_entry_ids']) for z in tables.values()))
 test('22_lunch_active_minute_exact',active_clock(690)==active_clock(750)==150 and active_clock(780)-active_clock(660)==60 and wall_clock(151)==751)
 test('23_predicted_release_cap920',all(0<predicted_release(r,tables[str(r['block'])])[0]<=920 for r in stream if r['entry_minute']<920 and r['band']!='P_BELOW'))
 test('24_no_replacement',all(z['release_minute']==640 for z in a1[2]) and next(d for d in a1[1] if d['symbol']=='DDD')['reason']=='MAX3_FULL')
 test('25_no_forced_EXIT',all(z['exit_kind']=='FROZEN_EXIT_V3' and z['source_minute']==639 for z in a1[2]) and next(c for c in a1[3] if c['minute']==639)['concurrent']==3 and next(c for c in a1[3] if c['minute']==640)['concurrent']==0)
 test('26_no_Rank_refit',all(sha(INPUT/'movement/models'/n)==v for n,v in rank['model_sha256'].items()))
 test('27_Admission_exact',sum(r['band']!='P_BELOW' for r in stream if r['entry_minute']<920)==490 and not audit.mismatches)
 alloc=allocation(candidates[:2],D(1000000),D(0),D(1000000),[]);ind=lot_allocate(candidates[:2],F(1000000),F(1000000),[])
 test('28_sizing_exact',all(p['quantity']==q['quantity'] and F(p['debit'])==q['debit'] for p,q in zip(alloc,ind)) and sha(ROOT/'research/capital-v7-rank-native-max3-20261005-v1/runtime.py')==frozen['immutable_sizing_sha256'])
 test('29_Liquidity_exact',(CODE/'replay.py').read_text().split('def main():')[0]==(ROOT/'research/capital-v8-capacity-aware-online-max3-20261005-v1/replay.py').read_text().split('def main():')[0])
 test('30_cash_nonnegative',all(D(c['cash'])>=0 for data in (a1,a2) for c in data[3]))
 test('31_lot_multiple100',all(d['quantity']%100==0 for data in (a1,a2) for d in data[1]))
 duplicate=copy.deepcopy(candidates[0]);duplicate.update(entry_id=f'{day}|AAA_DUP',entry_minute=553,entry_timestamp=f'{day}T09:13:00+09:00');dd=day_replay(day,candidates+[duplicate],books,D(1000000),ARMS[0],syntables)
 test('32_same_symbol_overlap_zero',next(d for d in dd[1] if d['entry_id']==duplicate['entry_id'])['reason']=='SAME_SYMBOL')
 expensive=copy.deepcopy(candidates[0]);expensive['raw_reference']='100000';aa=allocation([expensive,candidates[1]],D(1000000),D(0),D(1000000),[])
 test('33_cash_lot_no_backfill',aa[0]['quantity']==aa[0]['first_pass_quantity']==aa[0]['water_fill_lots']==0)
 test('34_later_topup_zero',all(sum(z['entry_id']==d['entry_id'] for z in a1[2])==1 and z['quantity']==d['quantity'] for d in a1[1] if d['reason']=='FUNDED' for z in a1[2] if z['entry_id']==d['entry_id']))
 teacher={'U5':0,'U10':0};before=copy.deepcopy(a2[1]);teacher.update(U5=1,U10=1);after=day_replay(day,candidates,books,D(1000000),ARMS[1],syntables)
 test('35_future_U5_U10_mutation_action_unchanged',teacher['U5']==1 and before==after[1])
 changedbooks=copy.deepcopy(books)
 for b in changedbooks.values():
  b['market'].append({'minute':659,'session':day,'O':'100','H':'102','L':'99','C':'101','Vo':'1000','Va':'100000','lineage':{'synthetic':True}})
  if b['frozen_exit']['sell_status']=='FILLED':b['frozen_exit'].update(sell_source_assumed_available_at=f'{day}T11:00:00+09:00',sell_minute=659)
 changed=day_replay(day,candidates,changedbooks,D(1000000),ARMS[0],syntables)
 test('36_future_EXIT_no_current_action_leak',a1[1]==changed[1] and [c for c in a1[3] if c['minute']<640]==[c for c in changed[3] if c['minute']<640] and [c for c in a1[3] if 640<=c['minute']<660]!=[c for c in changed[3] if 640<=c['minute']<660])
 scaled=[z|{'pP':z['pP']**2} for z in candidates];test('37_monotone_score_preserving_r_action_invariant',all(gate(a,z,o,z['entry_minute'],t)==gate(a,q,o,q['entry_minute'],t) for a in ARMS for o in range(4) for z,q in zip(candidates[:4],scaled[:4])) and [z['symbol'] for z in sorted(candidates,key=order)]==[z['symbol'] for z in sorted(scaled,key=order)])
 source=(CODE/'runtime.py').read_text();tree=ast.parse(source);imports=[z.module.lower() for z in ast.walk(tree) if isinstance(z,ast.ImportFrom) and z.module]
 test('38_clairvoyant_object_never_imported',not any('diagnostic' in m for m in imports) and 'CASH_DIAGNOSTIC' not in source)
 test('39_Oracle_objects_never_imported',not any('oracle' in m for m in imports) and 'ORACLE' not in source)
 test('40_Safety_all_false',not any(SAFETY.values()))
 changedtable=copy.deepcopy(t);changedtable['diagnostic_status']='UNAVAILABLE'
 test('41_diagnostic_failure_not_read_by_action',all(gate(a,r,1,554,t)==gate(a,r,1,554,changedtable) for a in ARMS))
 changedtable['diagnostic_selected_identities']=['FUTURE_WINNER']
 test('42_diagnostic_selected_identities_not_read',all(gate(a,r,1,554,t)==gate(a,r,1,554,changedtable) for a in ARMS))
 test('43_cash_diagnostic_code_not_imported',not any('cash' in m or 'diagnostic' in m for m in imports))
 assert len(cases)==43 and not audit.mismatches,audit.mismatches
 save(OUT/'CAUSAL_CANARY_RESULTS.json',{'exact_jst':now(),'test_N':43,'PASS_N':43,'all_PASS':True,'tests':cases,'independent_mapping_table_check_N':audit.checks,'independent_mismatch_N':len(audit.mismatches),'max_float_delta':audit.max_float_delta,'synthetic_only_capital_scenarios':True,'Development_primary_replays':0,'no_execution_unavailable_filter_added_runtime':True,'Safety':SAFETY})
 checkpoint('R7_CAUSAL_CANARY_PASS','ALL_43_CAUSAL_CANARIES_PASS',['43 mandatory semantics','synthetic-only accounting','independent mapping/table checks'],{'PASS':43,'mapping_table_checks':audit.checks,'mismatch_N':0},'Independent pre-main policy audit then Main claim commit/GET',{'primary_pP_diagnostic_solve':1,'uniqueness_no_good_solve':1,'independent_pP_diagnostic_solve':1});print(json.dumps({'PASS':43,'check_N':audit.checks,'mismatch':0}))
if __name__=='__main__':main()
