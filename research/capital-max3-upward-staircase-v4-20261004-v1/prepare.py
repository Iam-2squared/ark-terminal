"""Isolated prefit aggregate census and immutable source/model identity audit."""
from common import *
from core_features import NUMERIC,CATEGORICAL
import shutil
def freeze():
 manifest=json.loads((OUT/'CORE_FEATURE_MANIFEST.json').read_text());assert manifest=={'numeric':NUMERIC,'categorical':CATEGORICAL}
 assert sha(OUT/'CORE_FEATURE_MANIFEST.json')=='3aa3abd322e239d27776dfde896d93e38c4e84602ddbf0f9d6a6451865ba55f2'
 paths=['capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz','capital_quality_v3_private/NEW_HEAD_OOF_PREDICTIONS.jsonl.gz','capital_quality_v3_private/MODEL_HASHES.json','capital_v2_private/CORE_P5_SCORE_STREAM.jsonl.gz','capital_v2_private/TEACHERS_EVALUATION.jsonl.gz','bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz','capital_liquidity_off_private/OLD_REJECT52_LEDGER.jsonl.gz','work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz','work_inputs/exit_v3/REPLAY_ROWS.jsonl.gz']
 paths += [f'capital_liquidity_off_private/LIQUIDITY_OFF_MAX3_{n}' for n in ('RESULT.json','DECISIONS.jsonl.gz','TRADES.jsonl.gz','CURVE.jsonl.gz','INTENTS.jsonl.gz')]
 paths += [f'capital_quality_v3_private/QUALITY_V3_MAX3_{n}' for n in ('RESULT.json','TRADES.jsonl.gz')]
 expected=json.loads((SRC/'capital_quality_v3_private/SOURCE_MANIFEST.json').read_text())
 source={p:sha(SRC/p) for p in paths}
 for p,d in source.items():
  if p in expected:assert expected[p]==d,('SOURCE_HASH_MISMATCH',p)
 assert source['capital_v2_private/CORE_P5_SCORE_STREAM.jsonl.gz']=='a34f2c4a090a589d4e80858b65f01f3dc95a7849a57aece7e815213d20429731'
 save(OUT/'SOURCE_HASHES.json',source)
 control=json.loads((SRC/'capital_liquidity_off_private/LIQUIDITY_OFF_MAX3_RESULT.json').read_text());v3=json.loads((SRC/'capital_quality_v3_private/QUALITY_V3_MAX3_RESULT.json').read_text())
 assert control['funded_N']==167 and control['geometric_mean_daily_return']==.010959626199879651 and control['rolling20_median']==1.1419155854580427
 ct=rows(SRC/'capital_liquidity_off_private/LIQUIDITY_OFF_MAX3_TRADES.jsonl.gz')
 assert (sum(t['net_return']>=.01 for t in ct),sum(t['net_return']<=0 for t in ct),sum(t['net_return']<=-.01 for t in ct))==(54,89,58)
 save(OUT/'CONTROL_AND_V3_NEGATIVE_FREEZE.json',{'JST':now(),'formal_policy':'CAPITAL_MAX_CONCURRENT_3_RESEARCH_POLICY_V1','v3_final_HEAD':'f196722f96347ca5f324d478f98ff8dedd24b6c9','v3_status':['TOP3_SELECTION_WORSE','CAPITAL_QUALITY_V3_WORSE'],'v3_saved_result':v3,'v3_overwrite_rescue_reclassify':0,'control_saved_result':control,'control_replay_count':0,'Frozen_FIRST_ENTRY_v2_P1_Q70':'4a2d6f35946b16820a13449a9288a6685a5c283c','Frozen_EXIT_v3':'c7a5e5c25eb19cbd58b45c3e4ffff977f4648fad','formal_EXIT_receipt':'1ecbcc43f75279fa302f19fd896add2aac15b537','Frozen_change_N':0,'exposure':EXPOSURE,'Safety':SAFETY})
 checkpoint('U1_V3_NEGATIVE_AND_CONTROL_FREEZE','V3_NEGATIVE_CONTROL_FROZEN',{'Control_replays':0,'v3_status':'FORMAL_NEGATIVE_FIXED'})
def census_and_design():
 runtime=rows(SRC/'capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz');days=sorted({r['session'] for r in runtime});assert len(days)==58
 tt={t['entry_id']:t for t in rows(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz')};out={}
 for name,rr,exp in [('All58',runtime,[1600,654,448,244,90]),('OOF38',[r for r in runtime if r['session'] in days[20:]],[1039,432,297,170,67])]:
  count=[len(rr)]+[sum(tt[r['entry_id']]['potential_return']>=v for r in rr) for v in (.02,.03,.05,.10)]
  assert count==exp,('TEACHER_CENSUS_MISMATCH',name,count,exp)
  out[name]=dict(zip(('N','H2','H3','H5','H10'),count))
 save(OUT/'TEACHER_CENSUS.json',{'JST':now(),'counts':out,'teacher_source_hash':sha(SRC/'capital_v2_private/TEACHERS_EVALUATION.jsonl.gz'),'isolated_aggregate_evaluation_process':True,'teacher':'max strictly-later actual High before15:20 / raw Entry reference -1','labels_runtime_visible':False,'census_mismatch_N':0})
 pava={'algorithm':'unweighted least-squares decreasing PAVA','raw_order':['p2','p3','p5'],'constraint':'1>=m2>=m3>=m5>=0','weight':[1,1,1],'outcome_reads':0}
 save(OUT/'PAVA_CONFIG.json',pava)
 design={'JST':now(),'profile':PROFILE,'new_head':'H2','H2_fits':8,'H3_H5_exact_reuse':True,'HF1_HL0_fit_use':0,'H10_fit':0,'CORE_exact_reuse':True,'split':{'total_sessions':58,'warmup_sessions':20,'OOF_sessions':38,'origin':'5-session expanding-origin; last test block3 sessions'},'logistic':{'penalty':'l2','C':1.0,'solver':'lbfgs','max_iter':2000,'class_weight':None,'random_state':57},'preprocessing':'exact CORE; constant-zero missing plus indicator, training numeric mean/std and category vocab','M':'m2+m3+m5','B':'base2+base3+base5','ML':'M/B','admission':'ML>=1.0 only','ordering':['ML descending','m5 descending','m3 descending','m2 descending','Entry timestamp ascending','symbol stable ascending'],'ranks':{'S':'ML>=2','A':'1.5<=ML<2','B':'1<=ML<1.5','C':'ML<1; funded0'},'allocation':{'max_concurrent':3,'cap':{'S':.45,'A':.35,'B':.25},'base_target':{'S':.68,'A':.56,'B':.44},'breadth_increment':.055,'max_target':.92,'breadth_basis':'existing held bands plus eligible selected batch candidates, exact saved Control convention','weight':'ML proportional','water_fill':'same Entry batch initially funded candidates only; deterministic score-desc one lot rounds','lot':100,'forced_backfill':False,'later_topup':False},'liquidity_hard_gate':False,'liquidity_size_cap':False,'liquidity':'diagnostic only; historic statuses retained','execution':'exact unchanged Control execution.py; Frozen EXIT then15:20 SOR regular920<=minute<925 then exact930 auction; fail closed','MTM':'MTM_LAST_ACTUAL_TRADE_SAME_SESSION_V1','BUY_factor':'1.0005','SELL_factor':'0.9995','commission':0,'legacy_fee':0,'Entry_cutoff_JST':'15:20','only_LONG_cash_equity':True,'main_replays':1,'control_replays':0,'MAX4_MAX5_replays':0,'rank_diagnostic_reruns':0,'sweeps':0,'result_based_retune':0,'Exposure':EXPOSURE,'productionReady':False,'stop_after':'main v4 + audit + report; decisions return to user'}
 save(OUT/'DESIGN_PRECOMMIT.json',design)
 save(OUT/'SESSION_SPLIT.json',{'all58':days,'warmup20':days[:20],'OOF38':days[20:],'blocks':[{'block':i,'train':days[:s],'test':days[s:s+5]} for i,s in enumerate(range(20,58,5),1)]})
 checkpoint('U2_TEACHER_CENSUS_AND_DESIGN_PRECOMMIT','TEACHER_CENSUS_MATCH_DESIGN_FIXED',out)
def identity():
 expected=json.loads((SRC/'capital_quality_v3_private/MODEL_HASHES.json').read_text());source_expected=json.loads((SRC/'capital_quality_v3_private/SOURCE_MANIFEST.json').read_text());models={};report=[]
 for block in range(1,9):
  for head,rel,want in [('H3',f'capital_quality_v3_private/models/H3_BLOCK_{block:02d}.json',expected[f'H3_BLOCK_{block:02d}.json']),('H5',f'capital_v2_private/models/CORE_P_BLOCK_{block:02d}.json',source_expected[f'capital_v2_private/models/CORE_P_BLOCK_{block:02d}.json'])]:
   assert sha(SRC/rel)==want,('ARTIFACT_HASH_MISMATCH',rel)
   artifact=json.loads((SRC/rel).read_text());assert artifact['preprocessing']['numeric_fields']==NUMERIC and artifact['preprocessing']['categorical_fields']==CATEGORICAL
   dest=PRIVATE/'models'/f'{head}_BLOCK_{block:02d}.json';dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copyfile(SRC/rel,dest);assert sha(dest)==want
   models[dest.name]=want;report.append({'head':head,'block':block,'source':rel,'sha256':want,'exact_byte_identity':True,'new_fit':0})
  h3=json.loads((PRIVATE/'models'/f'H3_BLOCK_{block:02d}.json').read_text());h5=json.loads((PRIVATE/'models'/f'H5_BLOCK_{block:02d}.json').read_text());assert h3['preprocessing']==h5['preprocessing'] and h3['train_entry_ids']==h5['train_entry_ids'] and h3['test_dates']==h5['test_dates']
 save(PRIVATE/'REUSED_MODEL_HASHES.json',models)
 codehash={p.name:sha(p) for p in CODE.glob('*.py')}
 save(OUT/'MODEL_PRECOMMIT_CODE_PIN.json',{'JST':now(),'reused_models':report,'H3_H5_identity_mismatch_N':0,'CORE_feature_hash':sha(OUT/'CORE_FEATURE_MANIFEST.json'),'preprocessing_sha256':sha(CODE/'preprocessing.py'),'research_code_hashes':codehash,'H2_config':json.loads((OUT/'DESIGN_PRECOMMIT.json').read_text())['logistic'],'H2_fit_planned':8,'fits_so_far':0,'H3_reproduction_required':False,'main_replay_so_far':0,'Safety':SAFETY})
 checkpoint('U3_H3_H5_IDENTITY_AND_H2_MODEL_PRECOMMIT','H3_H5_EXACT_REUSE_H2_CODE_PINNED',{'reuse':models,'H2_fits_planned':8})
if __name__=='__main__':
 import sys
 {'freeze':freeze,'census':census_and_design,'identity':identity}[sys.argv[1]]()
