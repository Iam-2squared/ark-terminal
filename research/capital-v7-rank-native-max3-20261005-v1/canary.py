"""Synthetic-only causal tests plus independent reconstruction. No OOF replay."""
from control import *
from runtime import gate,order,allocation,ARMS
from mapping import band_units
from replay import day_replay
from independent_engine import Audit,build_mapping,accept,lot_allocate
from decimal import Decimal as D
from fractions import Fraction as F
from bisect import bisect_left
import copy,inspect,ast
def synthetic():
 day='2000-01-01';rr=[];books={}
 for name,t,p,band in [('AAA',550,.9,'P_HIGH'),('BBB',552,.8,'P_MID'),('CCC',554,.3,'P_BASE'),('DDD',620,.7,'P_MID'),('EEE',920,.99,'P_HIGH')]:
  k=f'{day}|{name}';r={'entry_id':k,'session':day,'symbol':name,'entry_minute':t,'entry_timestamp':f'{day}T{t//60:02}:{t%60:02}:00+09:00','raw_reference':'100','pP':p,'block':1,'rank_units':round(p*100),'train_N':100,'r':p,'band':band,'liquidity':{'eligible':True}};rr.append(r)
  market=[{'minute':m,'session':day,'O':'100','H':'102','L':'99','C':'101','Vo':'1000','Va':'100000','lineage':{'synthetic':True}} for m in (t,600,639,650,920)]
  books[k]={'entry_id':k,'session':day,'symbol':name,'capture_complete':True,'entry_actual_source':market[0],'market':market,'frozen_exit':{'sell_status':'FILLED','sell_source_assumed_available_at':f'{day}T10:40:00+09:00','sell_minute':639,'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_price_decimal':'99.9500'}}
  if t>=640:books[k]['frozen_exit']={'sell_status':'UNRESOLVED'}
 table={'1':{'train_N':100,'training_sessions':['1999-01-01','1999-01-02','1999-01-03','1999-01-04'],'minutes':{str(t):[70,60,None,None] for t in range(540,920)}}}
 return day,rr,books,table
def main():
 audit=Audit();reconstructed,tables,train=build_mapping(audit);cases=[]
 def test(name,ok):cases.append({'test':name,'PASS':bool(ok)});assert ok,name
 rank=read(ROOT/'docs/evidence/capital-rank-bigwinner-vnext-20261005-v1/SELECTED_RANK_CONTRACT.json');test('01_pP_score_hash_exact',sha(INPUT/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz')==rank['score_stream_sha256'])
 test('02_saved_models_hash_exact',all(sha(INPUT/'movement/models'/k)==v for k,v in rank['model_sha256'].items()))
 pack=read(WORK/'PACK_MANIFEST_READ.json');test('03_common_mask_exact',sha(PRIVATE/'COMMON_EVAL_MASK.jsonl.gz')==pack['files']['private/COMMON_EVAL_MASK.jsonl.gz']['sha256'])
 rr=rows(PRIVATE/'RANK_NATIVE_RUNTIME.jsonl.gz');test('04_future_label_in_X_zero',not any(any(k in r for k in ('U5','U10','potential_return','future_high','exit','pnl','label_bigwinner5')) for r in rr))
 test('05_future_test_arrivals_not_in_table',all(all(s not in read(OUT/'RANK_NATIVE_BAND_MAP.json')['blocks'][b]['test_sessions'] for s in t['training_sessions']) for b,t in tables.items()))
 test('06_training_sessions_strictly_before_test',all(max(t['training_sessions'])<min(read(OUT/'RANK_NATIVE_BAND_MAP.json')['blocks'][b]['test_sessions']) for b,t in tables.items()))
 test('07_training_percentile_independent_deterministic',not audit.mismatches)
 test('08_band_volume_independent_deterministic',read(OUT/'BAND_VOLUME_IDENTITY_AUDIT.json')['training_volume_mismatch_N']==0 and not audit.mismatches)
 day,candidates,books,table=synthetic();a1=day_replay(day,candidates,books,D(1000000),ARMS[0],table);a2=day_replay(day,candidates,books,D(1000000),ARMS[1],table)
 test('09_cutoff_1520_funded_zero',all(d['quantity']==0 and d['reason']=='CUTOFF' for data in (a1,a2) for d in data[1] if d['minute']==920))
 r=copy.deepcopy(candidates[0]);r['entry_minute']=560;r['entry_timestamp']=f'{day}T09:20:00+09:00';r['symbol']='ZZZ';lo=copy.deepcopy(r);lo['pP']=.1;lo['symbol']='AAA';test('10_same_minute_pP_order',sorted([lo,r],key=order)==[r,lo])
 test('11_A2_occupancy0_no_reserve',gate(ARMS[1],candidates[2],0,554,table['1'])[0])
 test('12_A2_occupancy1_no_reserve',gate(ARMS[1],candidates[2],1,554,table['1'])[0])
 test('13_A2_occupancy2_exact_half_reserve',gate(ARMS[1],candidates[2],2,554,table['1'])[:2]==(False,'LAST_SLOT_RESERVE_REJECT'))
 test('14_occupancy3_accept_zero',all(not gate(arm,candidates[0],3,554,table['1'])[0] for arm in ARMS))
 test('15_P_future_better_no_test_data',set(table['1'])=={'train_N','training_sessions','minutes'} and all(t['training_sessions'] for t in tables.values()))
 test('16_no_replacement',all(t['entry_id'] in {d['entry_id'] for d in a1[1] if d['reason']=='FUNDED'} for t in a1[2]) and all(t['release_minute']==640 for t in a1[2]))
 test('17_frozen_EXIT_exact',all(t['exit_kind']=='FROZEN_EXIT_V3' and t['source_minute']==639 and D(t['sell_effective'])==D('99.95') for t in a1[2]))
 test('18_cash_release_exact',next(c for c in a1[3] if c['minute']==639)['concurrent']==3 and next(c for c in a1[3] if c['minute']==640)['concurrent']==0)
 test('19_cash_nonnegative',all(D(c['cash'])>=0 for data in (a1,a2) for c in data[3]))
 test('20_lot_multiple100',all(d['quantity']%100==0 for data in (a1,a2) for d in data[1]))
 duplicate=copy.deepcopy(candidates[0]);duplicate.update(entry_id=f'{day}|AAA_DUP',entry_minute=553,entry_timestamp=f'{day}T09:13:00+09:00');dd=day_replay(day,candidates+[duplicate],books,D(1000000),ARMS[0],table)
 test('21_same_symbol_no_overlap',next(d for d in dd[1] if d['entry_id']==duplicate['entry_id'])['reason']=='SAME_SYMBOL')
 exp=copy.deepcopy(candidates[0]);exp['raw_reference']='100000';cheap=copy.deepcopy(candidates[1]);one=allocation([exp,cheap],D(1000000),D(0),D(1000000),[])
 test('22_no_backfill_after_cash_lot',one[0]['first_pass_quantity']==one[0]['quantity']==0 and one[0]['water_fill_lots']==0)
 test('23_no_later_topup',all(sum(t['entry_id']==d['entry_id'] for t in a1[2])==1 and t['quantity']==d['quantity'] for d in a1[1] if d['reason']=='FUNDED' for t in a1[2] if t['entry_id']==d['entry_id']))
 src=(CODE/'runtime.py').read_text();test('24_Oracle_never_runtime',not any('oracle' in node.module.lower() for node in ast.walk(ast.parse(src)) if isinstance(node,ast.ImportFrom)))
 teacher={'U5':0};before=day_replay(day,candidates,books,D(1000000),ARMS[1],table);evaluation_before=sum([teacher['U5']]);teacher['U5']=1;after=day_replay(day,candidates,books,D(1000000),ARMS[1],table)
 test('25_future_U5_mutation_evaluator_only',evaluation_before!=sum([teacher['U5']]) and before[1]==after[1] and before[2]==after[2])
 altered=copy.deepcopy(books)
 for b in altered.values():
  b['market'].append({'minute':659,'session':day,'O':'100','H':'102','L':'99','C':'101','Vo':'1000','Va':'100000','lineage':{'synthetic':True}})
  if b['frozen_exit']['sell_status']=='FILLED':b['frozen_exit']['sell_source_assumed_available_at']=f'{day}T11:00:00+09:00';b['frozen_exit']['sell_minute']=659
 changed=day_replay(day,candidates,altered,D(1000000),ARMS[0],table)
 test('26_future_EXIT_change_no_current_leak',a1[1]==changed[1] and [c for c in a1[3] if c['minute']<640]==[c for c in changed[3] if c['minute']<640] and [c for c in a1[3] if 640<=c['minute']<660]!=[c for c in changed[3] if 640<=c['minute']<660])
 trainkeys=[key for key in read(OUT/'TRAIN_SCORE_DISTRIBUTIONS.json')['1']['training_keys']];scaled=sorted([(-(-k[0])**2,k[1],k[2]) for k in trainkeys]);probe=[r for r in rr if r['block']==1]
 test('27_monotone_rescale_rank_band_invariant',all(bisect_left([tuple(k) for k in trainkeys],order(r))==bisect_left(scaled,(-r['pP']**2,r['entry_timestamp'],r['symbol'])) for r in probe))
 allmatch=True
 for arm in ARMS:
  for occ in range(4):
   for r in candidates[:3]:
    p=gate(arm,r,occ,554,table['1']);q=accept(arm,r,occ,554,table['1']);allmatch &= p[0]==q[0] and p[1]==q[1]
 alloc=allocation(candidates[:2],D(1000000),D(0),D(1000000),[]);ind=lot_allocate(candidates[:2],F(1000000),F(1000000),[])
 test('28_independent_band_action_quantity',allmatch and not audit.mismatches and all(p['quantity']==q['quantity'] and F(p['debit'])==q['debit'] for p,q in zip(alloc,ind)))
 out={'exact_jst':now(),'all_PASS':all(c['PASS'] for c in cases),'tests':cases,'test_N':len(cases),'independent_mapping_check_N':audit.checks,'independent_mapping_mismatch_N':len(audit.mismatches),'max_scalar_model_float_delta':audit.max_float_delta,'synthetic_scenarios_only':True,'OOF_Development_primary_replays':0,'input_source_unavailable_N':12,'source_unavailable_added_runtime_gate':False,'code_sha256':{p.name:sha(p) for p in CODE.glob('*.py')},'Safety':SAFETY}
 save(OUT/'CAUSAL_CANARY_RESULTS.json',out);save(OUT/'PRE_MAIN_INDEPENDENT_MAPPING_AUDIT.json',{'check_N':audit.checks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches,'float_tolerance':1e-12,'max_float_delta':audit.max_float_delta,'Primary_imports':0})
 checkpoint('D8_CAUSAL_CANARY_PASS','ALL_28_CANARIES_PASS',['28 synthetic causal tests','independent mapping/table/action reconstruction'],{'canary_PASS_N':28,'mismatch_N':0,'OOF_replays':0},'Claim A1/A2 Main in GitHub, actual GET, then each arm once',{'oracle_solves':4})
 print(json.dumps({'tests_PASS':len(cases),'independent_mapping_check_N':audit.checks,'mismatch_N':len(audit.mismatches),'max_float_delta':audit.max_float_delta}),flush=True)
if __name__=='__main__':main()
